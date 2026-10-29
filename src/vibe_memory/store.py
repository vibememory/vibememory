import json
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import kuzu

from .clock import utc_now_iso
from .security import (
    apply_security_update,
    prepare_record_security,
    reassess_record_security,
    record_fingerprint,
    record_is_retrievable,
)
from .storage_usage import RECORD_FIELDS, RELATION_FIELDS, file_payload_bytes, payload_bytes


def now():
    return utc_now_iso()


def uid():
    return str(uuid4())


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


class DuplicateRequestConflict(Exception):
    pass


class FileInUse(Exception):
    pass


class Store:
    """Single-process graph store. All traversal and mutation is scoped to the authenticated owner."""

    def __init__(self, path, model):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = kuzu.Database(str(path), buffer_pool_size=128 * 1024 * 1024, max_num_threads=2)
        self.conn = kuzu.Connection(self.db)
        self.query("""CREATE NODE TABLE IF NOT EXISTS Item(
            id STRING PRIMARY KEY, owner STRING, kind STRING, subtype STRING,
            title STRING, content STRING, source STRING, tags STRING[], created_at STRING,
            embedding DOUBLE[], parent_id STRING, start_offset INT64, end_offset INT64)""")
        self.query("""CREATE REL TABLE IF NOT EXISTS Link(FROM Item TO Item,
            id STRING, relation STRING, reason STRING, status STRING, version INT64,
            created_at STRING, history STRING, creator_agent_id STRING,
            creator_agent_name STRING, confidence DOUBLE, evidence_record_ids STRING[],
            extraction_method STRING, extraction_version STRING)""")
        self.query("CREATE NODE TABLE IF NOT EXISTS Meta(key STRING PRIMARY KEY, value STRING)")
        self.query("""CREATE NODE TABLE IF NOT EXISTS FeatureRequest(
            id STRING PRIMARY KEY, owner STRING, title STRING, description STRING,
            agent_name STRING, use_case STRING, priority STRING, source STRING,
            client_request_id STRING, status STRING, result STRING, result_url STRING,
            created_at STRING, updated_at STRING, resolved_at STRING)""")
        self.query("""CREATE NODE TABLE IF NOT EXISTS ChangeEvent(
            id INT64 PRIMARY KEY, owner STRING, event STRING, payload STRING)""")
        self.query("""CREATE NODE TABLE IF NOT EXISTS Agent(
            id STRING PRIMARY KEY, owner STRING, name STRING, transport STRING,
            active BOOLEAN, created_at STRING, last_seen_at STRING)""")
        self.query("""CREATE NODE TABLE IF NOT EXISTS AgentMessage(
            id STRING PRIMARY KEY, sequence INT64, owner STRING, sender_agent_id STRING,
            sender_name STRING, recipient_agent_id STRING, kind STRING, subject STRING,
            body STRING, metadata STRING, thread_id STRING, reply_to STRING,
            client_request_id STRING, request_payload STRING, status STRING,
            created_at STRING, expires_at STRING, delivered_at STRING, read_at STRING,
            acked_at STRING)""")
        self.event_sequence = self.query(
            "MATCH (e:ChangeEvent) RETURN max(e.id) AS latest"
        )[0]["latest"] or 0
        self.message_sequence = self.query(
            "MATCH (m:AgentMessage) RETURN max(m.sequence) AS latest"
        )[0]["latest"] or 0
        rows = self.query("MATCH (m:Meta {key: 'embedding_model'}) RETURN m.value AS value")
        if rows and rows[0]["value"] != model:
            self.close()
            raise ValueError("Embedding model differs from stored model; use a new data directory")
        if not rows:
            self.query("CREATE (:Meta {key: 'embedding_model', value: $model})", {"model": model})

        columns = {row["name"] for row in self.query("CALL table_info('Item') RETURN *")}
        if "keywords" not in columns:
            self.query("ALTER TABLE Item ADD keywords STRING[] DEFAULT []")
        if "metadata" not in columns:
            self.query("ALTER TABLE Item ADD metadata STRING DEFAULT '{}'")
        if "file_id" not in columns:
            self.query("ALTER TABLE Item ADD file_id STRING DEFAULT ''")
        if "version" not in columns:
            self.query("ALTER TABLE Item ADD version INT64 DEFAULT 1")
        if "archived_at" not in columns:
            self.query("ALTER TABLE Item ADD archived_at STRING DEFAULT ''")
        if "trust_level" not in columns:
            self.query("ALTER TABLE Item ADD trust_level STRING DEFAULT 'trusted'")
        if "security_state" not in columns:
            self.query("ALTER TABLE Item ADD security_state STRING DEFAULT 'active'")
        if "provenance" not in columns:
            self.query("ALTER TABLE Item ADD provenance STRING DEFAULT '{}'")
        if "content_hash" not in columns:
            self.query("ALTER TABLE Item ADD content_hash STRING DEFAULT ''")
        if "security_warnings" not in columns:
            self.query("ALTER TABLE Item ADD security_warnings STRING[] DEFAULT []")
        if "security_history" not in columns:
            self.query("ALTER TABLE Item ADD security_history STRING DEFAULT '[]'")
        feature_columns = {
            row["name"] for row in self.query("CALL table_info('FeatureRequest') RETURN *")
        }
        for name in ("result", "result_url", "updated_at", "resolved_at"):
            if name not in feature_columns:
                self.query(f"ALTER TABLE FeatureRequest ADD {name} STRING DEFAULT ''")
        relation_columns = {
            row["name"] for row in self.query("CALL table_info('Link') RETURN *")
        }
        relation_defaults = {
            "creator_agent_id": ("STRING", "'unknown'"),
            "creator_agent_name": ("STRING", "'Unknown agent'"),
            "confidence": ("DOUBLE", "NULL"),
            "evidence_record_ids": ("STRING[]", "[]"),
            "extraction_method": ("STRING", "''"),
            "extraction_version": ("STRING", "''"),
        }
        for name, (kind, default) in relation_defaults.items():
            if name not in relation_columns:
                self.query(f"ALTER TABLE Link ADD {name} {kind} DEFAULT {default}")
        # Old full-text/chunk vectors cannot be repurposed as agent keyword vectors.
        # Preserve source records and semantic relationships, but leave them unindexed.
        with self.transaction():
            self.query("MATCH (n:Item) WHERE n.kind = 'chunk' DETACH DELETE n")
            self.query("MATCH (n:Item) WHERE n.kind <> 'keyword' SET n.embedding = []")

    def _event(self, owner, event, payload):
        # Called inside the mutation transaction: rollback removes its event as well.
        self.event_sequence += 1
        self.query(
            "CREATE (:ChangeEvent {id: $id, owner: $owner, event: $event, payload: $payload})",
            dict(id=self.event_sequence, owner=owner, event=event,
                 payload=json.dumps(payload, ensure_ascii=False)),
        )

    def events(self, owner, after=0, limit=100):
        rows = self.query(
            """MATCH (e:ChangeEvent {owner: $owner}) WHERE e.id > $after
            RETURN e.id AS id, e.event AS event, e.payload AS payload
            ORDER BY e.id LIMIT $limit""",
            dict(owner=owner, after=after, limit=limit),
        )
        return [dict(id=row["id"], event=row["event"], data=json.loads(row["payload"]))
                for row in rows]

    @staticmethod
    def agent_record(node):
        return {key: value for key, value in node.items() if key != "owner"}

    def register_agent(self, owner, agent_id, name, transport):
        seen = now()
        with self.transaction():
            rows = self.query(
                "MATCH (a:Agent {id: $id, owner: $owner}) RETURN a",
                {"id": agent_id, "owner": owner},
            )
            if rows:
                self.query(
                    """MATCH (a:Agent {id: $id, owner: $owner})
                    SET a.name=$name,a.transport=$transport,a.active=true,
                    a.last_seen_at=$seen""",
                    {"id": agent_id, "owner": owner, "name": name,
                     "transport": transport, "seen": seen},
                )
            else:
                self.query(
                    """CREATE (:Agent {id: $id, owner: $owner, name: $name,
                    transport: $transport, active: true, created_at: $seen,
                    last_seen_at: $seen})""",
                    {"id": agent_id, "owner": owner, "name": name,
                     "transport": transport, "seen": seen},
                )
        rows = self.query(
            "MATCH (a:Agent {id: $id, owner: $owner}) RETURN a",
            {"id": agent_id, "owner": owner},
        )
        return self.agent_record(rows[0]["a"])

    def list_agents(self, owner):
        rows = self.query(
            """MATCH (a:Agent {owner: $owner})
            WHERE a.transport <> 'browser' AND a.active=true
            RETURN a ORDER BY a.last_seen_at DESC,a.id""",
            {"owner": owner},
        )
        return [self.agent_record(row["a"]) for row in rows]

    def deactivate_agent(self, owner, agent_id):
        self.query(
            "MATCH (a:Agent {owner: $owner, id: $id}) SET a.active=false",
            {"owner": owner, "id": agent_id},
        )

    @staticmethod
    def message_record(node):
        result = {
            key: value
            for key, value in node.items()
            if key not in {"owner", "request_payload"}
        }
        result["metadata"] = json.loads(result.get("metadata") or "{}")
        for field in ("reply_to", "client_request_id", "delivered_at", "read_at", "acked_at"):
            result[field] = result.get(field) or None
        return result

    def get_message(self, owner, agent_id, id):
        rows = self.query(
            """MATCH (m:AgentMessage {owner: $owner, id: $id})
            WHERE m.sender_agent_id=$agent_id OR m.recipient_agent_id=$agent_id RETURN m""",
            {"owner": owner, "id": id, "agent_id": agent_id},
        )
        if not rows:
            raise NotFound()
        return self.message_record(rows[0]["m"])

    def send_message(self, owner, sender_agent_id, sender_name, data):
        payload = data.model_dump(mode="json")
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.transaction():
            recipients = self.query(
                """MATCH (a:Agent {owner: $owner, id: $id})
                WHERE a.active=true RETURN a.id AS id""",
                {"owner": owner, "id": data.recipient_agent_id},
            )
            if not recipients:
                raise NotFound()
            if data.client_request_id:
                rows = self.query(
                    """MATCH (m:AgentMessage {owner: $owner,
                    sender_agent_id: $sender, client_request_id: $request_id}) RETURN m""",
                    {"owner": owner, "sender": sender_agent_id,
                     "request_id": data.client_request_id},
                )
                if rows:
                    if rows[0]["m"]["request_payload"] != payload_json:
                        raise DuplicateRequestConflict()
                    return self.message_record(rows[0]["m"]), False
            thread_id = data.thread_id or uid()
            if data.reply_to:
                rows = self.query(
                    """MATCH (m:AgentMessage {owner: $owner, id: $id})
                    WHERE m.sender_agent_id=$sender OR m.recipient_agent_id=$sender RETURN m""",
                    {"owner": owner, "id": data.reply_to, "sender": sender_agent_id},
                )
                participants = (
                    {rows[0]["m"]["sender_agent_id"], rows[0]["m"]["recipient_agent_id"]}
                    if rows else set()
                )
                if (
                    data.recipient_agent_id not in participants
                    or len(participants) > 1
                    and data.recipient_agent_id == sender_agent_id
                ):
                    raise NotFound()
                if data.thread_id and data.thread_id != rows[0]["m"]["thread_id"]:
                    raise ValueError("thread_id must match the replied-to message")
                thread_id = rows[0]["m"]["thread_id"]
            created = datetime.now(UTC)
            self.message_sequence += 1
            record = {
                "id": uid(),
                "sequence": self.message_sequence,
                "owner": owner,
                "sender_agent_id": sender_agent_id,
                "sender_name": sender_name,
                "recipient_agent_id": data.recipient_agent_id,
                "kind": data.kind,
                "subject": data.subject,
                "body": data.body,
                "metadata": json.dumps(data.metadata, ensure_ascii=False),
                "thread_id": thread_id,
                "reply_to": data.reply_to or "",
                "client_request_id": data.client_request_id or "",
                "request_payload": payload_json,
                "status": "queued",
                "created_at": created.isoformat(),
                "expires_at": (created + timedelta(seconds=data.expires_in_seconds)).isoformat(),
                "delivered_at": "",
                "read_at": "",
                "acked_at": "",
            }
            self.query(
                """CREATE (:AgentMessage {id: $id, sequence: $sequence, owner: $owner,
                sender_agent_id: $sender_agent_id, sender_name: $sender_name,
                recipient_agent_id: $recipient_agent_id, kind: $kind, subject: $subject,
                body: $body, metadata: $metadata, thread_id: $thread_id, reply_to: $reply_to,
                client_request_id: $client_request_id, request_payload: $request_payload,
                status: $status, created_at: $created_at, expires_at: $expires_at,
                delivered_at: $delivered_at, read_at: $read_at, acked_at: $acked_at})""",
                record,
            )
        return self.get_message(owner, sender_agent_id, record["id"]), True

    def inbox_messages(self, owner, agent_id, after=0, limit=50, status=None):
        status_filter = " AND m.status=$status" if status else ""
        parameters = {
            "owner": owner,
            "agent_id": agent_id,
            "after": after,
            "now": now(),
            "limit": limit,
        }
        if status:
            parameters["status"] = status
        rows = self.query(
            """MATCH (m:AgentMessage {owner: $owner, recipient_agent_id: $agent_id})
            WHERE m.sequence>$after AND m.expires_at>$now""" + status_filter +
            " RETURN m ORDER BY m.sequence LIMIT $limit",
            parameters,
        )
        return [self.message_record(row["m"]) for row in rows]

    def sent_messages(self, owner, agent_id, limit=50, offset=0):
        rows = self.query(
            """MATCH (m:AgentMessage {owner: $owner, sender_agent_id: $agent_id})
            RETURN m ORDER BY m.sequence DESC SKIP $offset LIMIT $limit""",
            {"owner": owner, "agent_id": agent_id, "offset": offset, "limit": limit},
        )
        return [self.message_record(row["m"]) for row in rows]

    def ack_message(self, owner, agent_id, id, status):
        ranks = {"queued": 0, "delivered": 1, "read": 2, "acked": 3}
        with self.transaction():
            rows = self.query(
                """MATCH (m:AgentMessage {owner: $owner, id: $id,
                recipient_agent_id: $agent_id}) RETURN m""",
                {"owner": owner, "id": id, "agent_id": agent_id},
            )
            if not rows:
                raise NotFound()
            current = rows[0]["m"]
            if ranks[status] > ranks[current["status"]]:
                stamp = now()
                delivered = current["delivered_at"] or (stamp if ranks[status] >= 1 else "")
                read = current["read_at"] or (stamp if ranks[status] >= 2 else "")
                acked = current["acked_at"] or (stamp if ranks[status] >= 3 else "")
                self.query(
                    """MATCH (m:AgentMessage {owner: $owner, id: $id})
                    SET m.status=$status,m.delivered_at=$delivered,m.read_at=$read,
                    m.acked_at=$acked""",
                    {"owner": owner, "id": id, "status": status,
                     "delivered": delivered, "read": read, "acked": acked},
                )
        return self.get_message(owner, agent_id, id)

    def close(self):
        self.conn.close()
        self.db.close()

    def query(self, statement, parameters=None):
        with self.lock:
            result = self.conn.execute(statement, parameters or {})
            try:
                names = result.get_column_names()
                rows = []
                while result.has_next():
                    rows.append(dict(zip(names, result.get_next(), strict=True)))
                return rows
            finally:
                result.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.query("BEGIN TRANSACTION")
            try:
                yield
                self.query("COMMIT")
            except BaseException:
                self.query("ROLLBACK")
                raise

    @staticmethod
    def clean(node, internal=False):
        result = {k: v for k, v in node.items() if not k.startswith("_")}
        if not internal:
            for key in ("embedding", "owner", "parent_id", "start_offset", "end_offset"):
                result.pop(key, None)
            result.pop("archived_at", None)
        result["metadata"] = json.loads(result.get("metadata") or "{}")
        result["trust_level"] = result.get("trust_level") or "trusted"
        result["security_state"] = result.get("security_state") or "active"
        result["provenance"] = json.loads(result.get("provenance") or "{}")
        result["content_hash"] = result.get("content_hash") or record_fingerprint(
            result.get("title", ""), result.get("content", "")
        )
        result["security_warnings"] = result.get("security_warnings") or []
        result["security_history"] = json.loads(result.get("security_history") or "[]")
        return result

    def _node(self, item):
        item.setdefault("file_id", "")
        item.setdefault("version", 1)
        item.setdefault("archived_at", "")
        item.setdefault("trust_level", "trusted")
        item.setdefault("security_state", "active")
        item.setdefault("provenance", "{}")
        item.setdefault("content_hash", "")
        item.setdefault("security_warnings", [])
        item.setdefault("security_history", "[]")
        self.query(
            """CREATE (:Item {id: $id, owner: $owner, kind: $kind, subtype: $subtype,
            title: $title, content: $content, source: $source, tags: $tags, created_at: $created_at,
            embedding: $embedding, parent_id: $parent_id, start_offset: $start_offset,
            end_offset: $end_offset, keywords: $keywords, metadata: $metadata, file_id: $file_id,
            version: $version, archived_at: $archived_at, trust_level: $trust_level,
            security_state: $security_state, provenance: $provenance,
            content_hash: $content_hash, security_warnings: $security_warnings,
            security_history: $security_history})""",
            item,
        )

    def insert(
        self,
        owner,
        kind,
        content,
        title,
        source,
        tags,
        subtype,
        keywords,
        metadata,
        vectors,
        file_id="",
        record_id=None,
        security=None,
    ):
        id, created = record_id or uid(), now()
        security = security or prepare_record_security(title, content, None)
        with self.transaction():
            if file_id and self.get(owner, file_id)["kind"] != "file":
                raise NotFound()
            self._node(
                dict(
                    id=id,
                    owner=owner,
                    kind=kind,
                    subtype=subtype,
                    title=title,
                    content=content,
                    source=source,
                    tags=tags,
                    created_at=created,
                    embedding=[],
                    parent_id="",
                    start_offset=0,
                    end_offset=0,
                    keywords=keywords,
                    file_id=file_id,
                    metadata=json.dumps(metadata, ensure_ascii=False),
                    trust_level=security["trust_level"],
                    security_state=security["security_state"],
                    provenance=json.dumps(security["provenance"], ensure_ascii=False),
                    content_hash=security["content_hash"],
                    security_warnings=security["security_warnings"],
                    security_history=json.dumps(
                        security["security_history"], ensure_ascii=False
                    ),
                )
            )
            self._index(owner, id, keywords, vectors)
            self._event(owner, kind + ".created", {"record_id": id, "kind": kind})
            if security["security_state"] != "active" or security["security_warnings"]:
                self._event(
                    owner,
                    kind + ".security_updated",
                    {
                        "record_id": id,
                        "kind": kind,
                        "trust_level": security["trust_level"],
                        "security_state": security["security_state"],
                        "warnings": security["security_warnings"],
                        "version": 1,
                    },
                )
            return self.get(owner, id)

    def _index(self, owner, parent_id, keywords, vectors):
        if len(vectors) != len(keywords):
            raise ValueError("Embedding count does not match keyword count")
        for keyword, vector in zip(keywords, vectors, strict=True):
            id = uid()
            self._node(
                dict(
                    id=id,
                    owner=owner,
                    kind="keyword",
                    subtype="",
                    title=keyword,
                    content=keyword,
                    source="",
                    tags=[],
                    created_at=now(),
                    embedding=vector,
                    parent_id=parent_id,
                    start_offset=0,
                    end_offset=0,
                    keywords=[],
                    metadata="{}",
                )
            )
            self._link(owner, id, parent_id, "KEYWORD_OF", "agent-supplied keyword")

    def update_keywords(self, owner, id, keywords, vectors):
        with self.transaction():
            record = self.get(owner, id)
            self.query(
                "MATCH (n:Item {owner: $owner, parent_id: $id}) DETACH DELETE n",
                {"owner": owner, "id": id},
            )
            self.query(
                """MATCH (n:Item {owner: $owner, id: $id})
                SET n.keywords = $keywords, n.version = n.version + 1""",
                {"owner": owner, "id": id, "keywords": keywords},
            )
            self._index(owner, id, keywords, vectors)
            self._event(owner, record["kind"] + ".updated",
                        {"record_id": id, "kind": record["kind"], "change": "keywords",
                         "version": record["version"] + 1})
            return self.get(owner, id)

    def update_record(self, owner, id, data, vectors=None):
        with self.transaction():
            record = self.get(owner, id)
            if record["version"] != data.expected_version:
                raise Conflict()
            fields = {
                key: getattr(data, key)
                for key in ("content", "title", "subtype", "source", "tags", "keywords")
                if getattr(data, key) is not None
            }
            if data.metadata is not None:
                fields["metadata"] = json.dumps(data.metadata, ensure_ascii=False)
            title = data.title if data.title is not None else record["title"]
            content = data.content if data.content is not None else record["content"]
            security = reassess_record_security(
                record, title, content, record["version"] + 1
            )
            security_changed = (
                security["security_state"] != record["security_state"]
                or security["trust_level"] != record["trust_level"]
                or security["security_warnings"] != record["security_warnings"]
            )
            fields.update(
                {
                    "trust_level": security["trust_level"],
                    "security_state": security["security_state"],
                    "provenance": json.dumps(security["provenance"], ensure_ascii=False),
                    "content_hash": security["content_hash"],
                    "security_warnings": security["security_warnings"],
                    "security_history": json.dumps(
                        security["security_history"], ensure_ascii=False
                    ),
                }
            )
            assignments = [f"n.{key} = ${key}" for key in fields]
            assignments.append("n.version = n.version + 1")
            self.query(
                "MATCH (n:Item {owner: $owner, id: $id}) SET " + ", ".join(assignments),
                {"owner": owner, "id": id, **fields},
            )
            if data.keywords is not None:
                if vectors is None or len(vectors) != len(data.keywords):
                    raise ValueError("Embedding count does not match keyword count")
                self.query(
                    "MATCH (n:Item {owner: $owner, parent_id: $id}) DETACH DELETE n",
                    {"owner": owner, "id": id},
                )
                self._index(owner, id, data.keywords, vectors)
            self._event(
                owner,
                record["kind"] + ".updated",
                {"record_id": id, "kind": record["kind"], "change": "record",
                 "version": record["version"] + 1},
            )
            if security_changed:
                self._event(
                    owner,
                    record["kind"] + ".security_updated",
                    {
                        "record_id": id,
                        "kind": record["kind"],
                        "trust_level": security["trust_level"],
                        "security_state": security["security_state"],
                        "warnings": security["security_warnings"],
                        "version": record["version"] + 1,
                    },
                )
            return self.get(owner, id)

    def update_security(self, owner, id, data):
        with self.transaction():
            record = self.get(owner, id)
            if record["version"] != data.expected_version:
                raise Conflict()
            security = apply_security_update(record, data)
            self.query(
                """MATCH (n:Item {owner: $owner, id: $id}) SET
                n.trust_level = $trust_level, n.security_state = $security_state,
                n.provenance = $provenance, n.content_hash = $content_hash,
                n.security_warnings = $security_warnings,
                n.security_history = $security_history, n.version = n.version + 1""",
                {
                    "owner": owner,
                    "id": id,
                    "trust_level": security["trust_level"],
                    "security_state": security["security_state"],
                    "provenance": json.dumps(security["provenance"], ensure_ascii=False),
                    "content_hash": security["content_hash"],
                    "security_warnings": security["security_warnings"],
                    "security_history": json.dumps(
                        security["security_history"], ensure_ascii=False
                    ),
                },
            )
            self._event(
                owner,
                record["kind"] + ".security_updated",
                {
                    "record_id": id,
                    "kind": record["kind"],
                    "trust_level": security["trust_level"],
                    "security_state": security["security_state"],
                    "warnings": security["security_warnings"],
                    "reason": data.reason,
                    "version": record["version"] + 1,
                },
            )
            return self.get(owner, id)

    def get(self, owner, id, internal=False):
        rows = self.query(
            """MATCH (n:Item {owner: $owner, id: $id})
            WHERE n.archived_at = '' RETURN n""", {"owner": owner, "id": id}
        )
        if not rows or (not internal and rows[0]["n"]["kind"] in {"chunk", "keyword"}):
            raise NotFound()
        return self.clean(rows[0]["n"], internal)

    def list(
        self,
        owner,
        kind=None,
        limit=50,
        offset=0,
        include_untrusted=False,
        include_quarantined=False,
    ):
        rows = self.query(
            """MATCH (n:Item {owner: $owner})
            WHERE n.kind <> 'chunk' AND n.kind <> 'keyword' AND n.archived_at = ''
            AND ($kind = '' OR n.kind = $kind)
            AND ($include_untrusted OR n.trust_level = 'trusted')
            AND ($include_quarantined OR n.security_state = 'active')
            RETURN n ORDER BY n.created_at DESC, n.id SKIP $offset LIMIT $limit""",
            {
                "owner": owner,
                "kind": kind or "",
                "limit": limit,
                "offset": offset,
                "include_untrusted": include_untrusted,
                "include_quarantined": include_quarantined,
            },
        )
        return [self.clean(row["n"]) for row in rows]

    def quarantined(self, owner, limit=50, offset=0):
        rows = self.query(
            """MATCH (n:Item {owner: $owner})
            WHERE n.kind <> 'chunk' AND n.kind <> 'keyword' AND n.archived_at = ''
            AND n.security_state = 'quarantined'
            RETURN n ORDER BY n.created_at DESC, n.id SKIP $offset LIMIT $limit""",
            {"owner": owner, "limit": limit, "offset": offset},
        )
        return [self.clean(row["n"]) for row in rows]

    def archived(self, owner, limit=50, offset=0):
        rows = self.query(
            """MATCH (n:Item {owner: $owner})
            WHERE n.kind <> 'chunk' AND n.kind <> 'keyword' AND n.archived_at <> ''
            RETURN n ORDER BY n.archived_at DESC, n.id SKIP $offset LIMIT $limit""",
            {"owner": owner, "limit": limit, "offset": offset},
        )
        result = []
        for row in rows:
            record = self.clean(row["n"])
            record["archived_at"] = row["n"]["archived_at"]
            result.append(record)
        return result

    def delete(self, owner, id):
        with self.transaction():
            record = self.get(owner, id)
            if record["kind"] == "file" and self.query(
                "MATCH (n:Item {owner: $owner, file_id: $id}) RETURN n.id",
                {"owner": owner, "id": id},
            ):
                raise FileInUse()
            self.query(
                """MATCH (n:Item {owner: $owner}) WHERE n.id = $id OR n.parent_id = $id
                DETACH DELETE n""",
                {"owner": owner, "id": id},
            )
            self._event(owner, record["kind"] + ".deleted",
                        {"record_id": id, "kind": record["kind"],
                         "incident_relations_removed": True})

    def archive(self, owner, id, expected_version, reason):
        with self.transaction():
            record = self.get(owner, id)
            if record["version"] != expected_version:
                raise Conflict()
            if record["kind"] == "file" and self.query(
                """MATCH (n:Item {owner: $owner, file_id: $id})
                WHERE n.archived_at = '' RETURN n.id""",
                {"owner": owner, "id": id},
            ):
                raise FileInUse()
            archived_at = now()
            self.query(
                """MATCH (n:Item {owner: $owner, id: $id})
                SET n.archived_at = $archived_at, n.version = n.version + 1""",
                {"owner": owner, "id": id, "archived_at": archived_at},
            )
            self._event(
                owner,
                record["kind"] + ".archived",
                {"record_id": id, "kind": record["kind"], "reason": reason,
                 "version": record["version"] + 1, "recoverable": True},
            )
            return {"id": id, "archived_at": archived_at, "version": record["version"] + 1}

    def restore(self, owner, id, expected_version, reason):
        with self.transaction():
            rows = self.query(
                """MATCH (n:Item {owner: $owner, id: $id})
                WHERE n.archived_at <> '' RETURN n""",
                {"owner": owner, "id": id},
            )
            if not rows:
                raise NotFound()
            record = self.clean(rows[0]["n"])
            if record["version"] != expected_version:
                raise Conflict()
            if record["kind"] == "document" and record["file_id"]:
                if self.get(owner, record["file_id"])["kind"] != "file":
                    raise NotFound()
            self.query(
                """MATCH (n:Item {owner: $owner, id: $id})
                SET n.archived_at = '', n.version = n.version + 1""",
                {"owner": owner, "id": id},
            )
            self._event(
                owner,
                record["kind"] + ".restored",
                {"record_id": id, "kind": record["kind"], "reason": reason,
                 "version": record["version"] + 1},
            )
            return self.get(owner, id)

    def merge(self, owner, data):
        ids = [data.canonical_id, *data.duplicate_ids]
        duplicates = set(data.duplicate_ids)
        with self.transaction():
            records = {id: self.get(owner, id) for id in ids}
            if any(records[id]["version"] != data.expected_versions[id] for id in ids):
                raise Conflict()
            kinds = {records[id]["kind"] for id in ids}
            if len(kinds) != 1 or "file" in kinds:
                raise ValueError("Only records of the same non-file kind can be merged")
            edges = [
                edge
                for edge in self.relations(owner, "all")
                if edge["source_id"] in duplicates or edge["target_id"] in duplicates
            ]
            rewired = retracted = 0
            relation_id_map = {}
            for edge in edges:
                source = data.canonical_id if edge["source_id"] in duplicates else edge["source_id"]
                target = data.canonical_id if edge["target_id"] in duplicates else edge["target_id"]
                version = edge["version"] + 1
                change_reason = "Record merge: " + data.reason
                history = edge["history"] + [
                    dict(
                        status="retracted" if source == target else edge["status"],
                        reason=change_reason,
                        at=now(),
                        version=version,
                    )
                ]
                if source == target:
                    self.query(
                        """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
                        WHERE r.id = $id SET r.status = 'retracted', r.reason = $reason,
                        r.version = $version, r.history = $history""",
                        {"owner": owner, "id": edge["id"], "reason": change_reason,
                         "version": version, "history": json.dumps(history)},
                    )
                    retracted += 1
                    continue
                self.query(
                    """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
                    WHERE r.id = $id DELETE r""",
                    {"owner": owner, "id": edge["id"]},
                )
                new_id = self._link(
                    owner,
                    source,
                    target,
                    edge["relation"],
                    change_reason,
                    creator_agent_id=edge["creator_agent_id"],
                    creator_agent_name=edge["creator_agent_name"],
                    confidence=edge["confidence"],
                    evidence_record_ids=edge["evidence_record_ids"],
                    extraction_method=edge["extraction_method"],
                    extraction_version=edge["extraction_version"],
                )
                self.query(
                    """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
                    WHERE r.id = $id SET r.status = $status, r.version = $version,
                    r.history = $history""",
                    {"owner": owner, "id": new_id, "status": edge["status"],
                     "version": version, "history": json.dumps(history)},
                )
                relation_id_map[edge["id"]] = new_id
                rewired += 1
            archived_at = now()
            self.query(
                """MATCH (n:Item {owner: $owner}) WHERE n.id IN $ids
                SET n.archived_at = $archived_at, n.version = n.version + 1""",
                {"owner": owner, "ids": data.duplicate_ids, "archived_at": archived_at},
            )
            self.query(
                """MATCH (n:Item {owner: $owner, id: $id}) SET n.version = n.version + 1""",
                {"owner": owner, "id": data.canonical_id},
            )
            self._event(
                owner,
                "record.merged",
                {"canonical_id": data.canonical_id, "archived_ids": data.duplicate_ids,
                 "reason": data.reason, "relations_rewired": rewired,
                 "relations_retracted": retracted},
            )
            return {
                "canonical": self.get(owner, data.canonical_id),
                "archived_ids": data.duplicate_ids,
                "archived_at": archived_at,
                "relations_rewired": rewired,
                "relations_retracted": retracted,
                "relation_id_map": relation_id_map,
                "archived_records_recoverable": True,
            }

    def _link(
        self,
        owner,
        source,
        target,
        relation,
        reason,
        creator_agent_id="unknown",
        creator_agent_name="Unknown agent",
        confidence=None,
        evidence_record_ids=None,
        extraction_method="",
        extraction_version="",
    ):
        id, created = uid(), now()
        history = json.dumps(
            [
                dict(
                    status="active",
                    reason=reason,
                    at=created,
                    version=1,
                    creator_agent_id=creator_agent_id,
                    confidence=confidence,
                )
            ]
        )
        self.query(
            """MATCH (a:Item {owner: $owner, id: $source}),
            (b:Item {owner: $owner, id: $target})
            CREATE (a)-[:Link {id: $id, relation: $relation, reason: $reason, status: 'active',
                version: 1, created_at: $created, history: $history,
                creator_agent_id: $creator_agent_id, creator_agent_name: $creator_agent_name,
                confidence: $confidence, evidence_record_ids: $evidence_record_ids,
                extraction_method: $extraction_method,
                extraction_version: $extraction_version}]->(b)""",
            dict(
                owner=owner,
                source=source,
                target=target,
                id=id,
                relation=relation,
                reason=reason,
                created=created,
                history=history,
                creator_agent_id=creator_agent_id,
                creator_agent_name=creator_agent_name,
                confidence=confidence,
                evidence_record_ids=evidence_record_ids or [],
                extraction_method=extraction_method,
                extraction_version=extraction_version,
            ),
        )
        return id

    def link(
        self,
        owner,
        data,
        creator_agent_id="unknown",
        creator_agent_name="Unknown agent",
    ):
        with self.transaction():
            self.get(owner, data.source_id)
            self.get(owner, data.target_id)
            for evidence_id in data.evidence_record_ids:
                self.get(owner, evidence_id)
            if data.source_id == data.target_id:
                raise ValueError("A relationship must connect two distinct records")
            id = self._link(
                owner,
                data.source_id,
                data.target_id,
                data.relation,
                data.reason,
                creator_agent_id,
                creator_agent_name,
                data.confidence,
                data.evidence_record_ids,
                data.extraction_method,
                data.extraction_version,
            )
            self._event(owner, "relation.created", {"relation_id": id,
                        "source_id": data.source_id, "target_id": data.target_id,
                        "creator_agent_id": creator_agent_id,
                        "confidence": data.confidence, "version": 1})
            return next(r for r in self.relations(owner, "all") if r["id"] == id)

    def relations(
        self,
        owner,
        status="active",
        creator_agent_id="",
        min_confidence=None,
        extraction_method="",
        relation="",
    ):
        rows = self.query(
            """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
            WHERE r.relation <> 'CHUNK_OF' AND r.relation <> 'KEYWORD_OF' AND ($status = 'all' OR r.status = $status)
            AND a.archived_at = '' AND b.archived_at = ''
            RETURN a.id AS source_id, b.id AS target_id, r.id AS id, r.relation AS relation,
                r.reason AS reason, r.status AS status, r.version AS version,
                r.created_at AS created_at, r.history AS history,
                r.creator_agent_id AS creator_agent_id,
                r.creator_agent_name AS creator_agent_name,
                r.confidence AS confidence,
                r.evidence_record_ids AS evidence_record_ids,
                r.extraction_method AS extraction_method,
                r.extraction_version AS extraction_version""",
            {"owner": owner, "status": status},
        )
        result = []
        for row in rows:
            row["history"] = json.loads(row["history"])
            row["creator_agent_id"] = row.get("creator_agent_id") or "unknown"
            row["creator_agent_name"] = row.get("creator_agent_name") or "Unknown agent"
            row["evidence_record_ids"] = row.get("evidence_record_ids") or []
            row["extraction_method"] = row.get("extraction_method") or ""
            row["extraction_version"] = row.get("extraction_version") or ""
            if creator_agent_id and row["creator_agent_id"] != creator_agent_id:
                continue
            if min_confidence is not None and (
                row["confidence"] is None or row["confidence"] < min_confidence
            ):
                continue
            if extraction_method and row["extraction_method"] != extraction_method:
                continue
            if relation and row["relation"] != relation:
                continue
            row["claim_group"] = f"{row['source_id']}:{row['target_id']}"
            result.append(row)
        groups = {}
        for edge in result:
            groups.setdefault(edge["claim_group"], []).append(edge["id"])
        for edge in result:
            edge["parallel_claim_ids"] = [
                claim_id for claim_id in groups[edge["claim_group"]] if claim_id != edge["id"]
            ]
        return result

    def update_link(self, owner, id, data):
        with self.transaction():
            edge = next((e for e in self.relations(owner, "all") if e["id"] == id), None)
            if not edge:
                raise NotFound()
            if edge["version"] != data.expected_version:
                raise Conflict()
            if edge["status"] == data.status:
                return edge
            version = edge["version"] + 1
            history = edge["history"] + [
                dict(status=data.status, reason=data.reason, at=now(), version=version)
            ]
            self.query(
                """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
                WHERE r.id = $id SET r.status = $status, r.reason = $reason,
                r.version = $version, r.history = $history""",
                dict(
                    owner=owner,
                    id=id,
                    status=data.status,
                    reason=data.reason,
                    version=version,
                    history=json.dumps(history),
                ),
            )
            self._event(owner, "relation.updated", {"relation_id": id,
                        "source_id": edge["source_id"], "target_id": edge["target_id"],
                        "version": version})
            return {
                **edge,
                "status": data.status,
                "reason": data.reason,
                "version": version,
                "history": history,
            }

    def candidates(self, owner, scope, tags):
        rows = self.query(
            """MATCH (n:Item {owner: $owner})-[:Link]->(p:Item {owner: $owner})
            WHERE n.kind = 'keyword' AND p.archived_at = ''
            AND ($scope = 'all' OR p.kind = $scope)
            RETURN n, p""",
            {
                "owner": owner,
                "scope": {"memories": "memory", "documents": "document", "entities": "entity"}.get(
                    scope, scope
                ),
            },
        )
        return [
            (self.clean(r["n"], True), self.clean(r["p"]))
            for r in rows
            if not tags or all(tag in r["p"]["tags"] for tag in tags)
        ]

    def neighborhood(
        self,
        owner,
        seeds,
        depth,
        include_untrusted=False,
        include_quarantined=False,
        creator_agent_id="",
        min_confidence=None,
        extraction_method="",
        relation="",
    ):
        # Bounded BFS over real stored graph edges; retracted links never enter retrieval.
        edges = self.relations(
            owner,
            creator_agent_id=creator_agent_id,
            min_confidence=min_confidence,
            extraction_method=extraction_method,
            relation=relation,
        )
        visited, frontier, selected = set(seeds), set(seeds), {}
        allowed = {id: True for id in seeds}

        def can_retrieve(id):
            if id not in allowed:
                allowed[id] = record_is_retrievable(
                    self.get(owner, id),
                    include_untrusted=include_untrusted,
                    include_quarantined=include_quarantined,
                )
            return allowed[id]

        for _ in range(depth):
            following = set()
            for edge in edges:
                a, b = edge["source_id"], edge["target_id"]
                if (a in frontier or b in frontier) and can_retrieve(a) and can_retrieve(b):
                    selected[edge["id"]] = edge
                    following.update((a, b))
            frontier = following - visited
            visited.update(following)
        return {
            "nodes": [self.get(owner, id) for id in sorted(visited - set(seeds))],
            "relations": list(selected.values()),
        }

    @staticmethod
    def feature_request_record(node):
        record = {
            key: value for key, value in node.items() if not key.startswith("_") and key != "owner"
        }
        record["result"] = record.get("result") or ""
        record["result_url"] = record.get("result_url") or ""
        record["updated_at"] = record.get("updated_at") or record["created_at"]
        record["resolved_at"] = record.get("resolved_at") or None
        return record

    def get_feature_request(self, owner, id):
        rows = self.query(
            "MATCH (r:FeatureRequest {owner: $owner, id: $id}) RETURN r", {"owner": owner, "id": id}
        )
        if not rows:
            raise NotFound()
        return self.feature_request_record(rows[0]["r"])

    def list_feature_requests(self, owner, limit=50, offset=0):
        rows = self.query(
            """MATCH (r:FeatureRequest {owner: $owner}) RETURN r
            ORDER BY r.created_at DESC, r.id SKIP $offset LIMIT $limit""",
            {"owner": owner, "limit": limit, "offset": offset},
        )
        return [self.feature_request_record(row["r"]) for row in rows]

    def admin_feature_requests(self, status="", limit=50, offset=0):
        rows = self.query(
            """MATCH (r:FeatureRequest)
            WHERE $status = '' OR r.status = $status
            RETURN r ORDER BY r.updated_at DESC, r.created_at DESC, r.id
            SKIP $offset LIMIT $limit""",
            {"status": status, "limit": limit, "offset": offset},
        )
        items = []
        for row in rows:
            record = self.feature_request_record(row["r"])
            record["owner_id"] = row["r"]["owner"]
            items.append(record)
        return items

    def feature_request_status_counts(self):
        rows = self.query(
            "MATCH (r:FeatureRequest) RETURN r.status AS status, count(*) AS count"
        )
        return {row["status"]: row["count"] for row in rows}

    def add_feature_request(self, owner, data):
        payload = data.model_dump()
        with self.transaction():
            if data.client_request_id:
                rows = self.query(
                    """MATCH (r:FeatureRequest {owner: $owner,
                    client_request_id: $client_request_id}) RETURN r""",
                    {"owner": owner, "client_request_id": data.client_request_id},
                )
                if rows:
                    existing = self.feature_request_record(rows[0]["r"])
                    if any(existing[key] != value for key, value in payload.items()):
                        raise DuplicateRequestConflict()
                    return existing, False
            record = {
                **payload,
                "id": uid(),
                "owner": owner,
                "status": "received",
                "result": "",
                "result_url": "",
                "created_at": now(),
            }
            record["updated_at"] = record["created_at"]
            record["resolved_at"] = ""
            self.query(
                """CREATE (:FeatureRequest {id: $id, owner: $owner, title: $title,
                description: $description, agent_name: $agent_name, use_case: $use_case,
                priority: $priority, source: $source, client_request_id: $client_request_id,
                status: $status, result: $result, result_url: $result_url,
                created_at: $created_at, updated_at: $updated_at,
                resolved_at: $resolved_at})""",
                record,
            )
            return self.get_feature_request(owner, record["id"]), True

    def update_feature_request(self, owner, id, data):
        with self.transaction():
            current = self.get_feature_request(owner, id)
            changes = data.model_dump(exclude_unset=True)
            status = changes.get("status", current["status"])
            updated_at = now()
            if status in {"completed", "declined"}:
                resolved_at = current.get("resolved_at") or updated_at
            else:
                resolved_at = ""
            result = changes.get("result", current["result"])
            result_url = changes.get("result_url", current["result_url"])
            self.query(
                """MATCH (r:FeatureRequest {owner: $owner, id: $id})
                SET r.status = $status, r.result = $result, r.result_url = $result_url,
                    r.updated_at = $updated_at, r.resolved_at = $resolved_at""",
                {
                    "owner": owner,
                    "id": id,
                    "status": status,
                    "result": result,
                    "result_url": result_url,
                    "updated_at": updated_at,
                    "resolved_at": resolved_at,
                },
            )
            self._event(
                owner,
                "feature_request.updated",
                {"feature_request_id": id, "status": status, "updated_at": updated_at},
            )
            return self.get_feature_request(owner, id)

    def stats(self, owner):
        with self.transaction():
            counts = self.query(
                """MATCH (n:Item {owner: $owner})
                WHERE n.kind <> 'keyword' AND n.kind <> 'chunk' AND n.archived_at = ''
                RETURN n.kind AS kind, count(*) AS count""",
                {"owner": owner},
            )
            result = {"memory": 0, "document": 0, "entity": 0, "file": 0}
            result.update({row["kind"]: row["count"] for row in counts})
            result["relations"] = len(self.relations(owner))
            records = self.query(
                """MATCH (n:Item {owner: $owner})
                WHERE n.kind <> 'keyword' AND n.kind <> 'chunk' RETURN n""",
                {"owner": owner},
            )
            relation_payloads = self.query(
                """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
                WHERE r.relation <> 'CHUNK_OF' AND r.relation <> 'KEYWORD_OF'
                RETURN a.id AS source_id, b.id AS target_id, r.relation AS relation,
                    r.reason AS reason, r.status AS status, r.history AS history,
                    r.creator_agent_id AS creator_agent_id,
                    r.creator_agent_name AS creator_agent_name,
                    r.confidence AS confidence,
                    r.evidence_record_ids AS evidence_record_ids,
                    r.extraction_method AS extraction_method,
                    r.extraction_version AS extraction_version""",
                {"owner": owner},
            )
            memory_bytes = sum(payload_bytes(row["n"], RECORD_FIELDS) for row in records)
            memory_bytes += sum(
                payload_bytes(row, RELATION_FIELDS) for row in relation_payloads
            )
            file_bytes = sum(
                file_payload_bytes(row["n"].get("metadata"))
                for row in records
                if row["n"].get("kind") == "file"
            )
            result["memory_bytes"] = memory_bytes
            result["file_bytes"] = file_bytes
            result["storage_bytes"] = memory_bytes + file_bytes
            return result
