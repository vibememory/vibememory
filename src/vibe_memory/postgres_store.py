"""PostgreSQL/pgvector implementation of the owner-scoped memory store."""

import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from psycopg.types.json import Jsonb

from .clock import utc_now_iso
from .postgres import vector_from_text, vector_literal
from .retrieval import record_matches_filters
from .security import (
    apply_security_update,
    prepare_record_security,
    reassess_record_security,
    record_fingerprint,
    record_is_retrievable,
)
from .store import Conflict, DuplicateRequestConflict, FileInUse, NotFound


def uid():
    return str(uuid4())


def now():
    return utc_now_iso()


def iso(value):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value


class PostgresStore:
    """Transactional relational graph with pgvector keyword embeddings."""

    def __init__(self, database):
        self.database = database
        self.model = database.model
        self.lock = threading.RLock()
        self._local = threading.local()

    @contextmanager
    def _connection(self):
        existing = getattr(self._local, "connection", None)
        if existing is not None:
            yield existing
            return
        with self.database.connection() as connection:
            yield connection

    @contextmanager
    def transaction(self):
        existing = getattr(self._local, "connection", None)
        if existing is not None:
            yield
            return
        with self.database.connection() as connection, connection.transaction():
            self._local.connection = connection
            try:
                yield
            finally:
                self._local.connection = None

    def close(self):
        # The shared database pool is closed by the application lifespan.
        return None

    @staticmethod
    def _record(row):
        if not row:
            return None
        result = dict(row)
        result["created_at"] = iso(result["created_at"])
        result["metadata"] = result.get("metadata") or {}
        result["tags"] = result.get("tags") or []
        result["keywords"] = result.get("keywords") or []
        result["file_id"] = result.get("file_id") or ""
        result["trust_level"] = result.get("trust_level") or "trusted"
        result["security_state"] = result.get("security_state") or "active"
        result["provenance"] = result.get("provenance") or {}
        result["content_hash"] = result.get("content_hash") or record_fingerprint(
            result.get("title", ""), result.get("content", "")
        )
        result["security_warnings"] = result.get("security_warnings") or []
        result["security_history"] = result.get("security_history") or []
        result.pop("owner", None)
        result.pop("archived_at", None)
        return result

    @staticmethod
    def _relation(row):
        result = dict(row)
        result.pop("owner", None)
        result["created_at"] = iso(result["created_at"])
        result["history"] = result.get("history") or []
        return result

    def _event(self, owner, event, payload):
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO change_events(owner,event,payload) VALUES(%s,%s,%s)",
                (owner, event, Jsonb(payload)),
            )

    def events(self, owner, after=0, limit=100):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id,event,payload FROM change_events
                WHERE owner=%s AND id>%s ORDER BY id LIMIT %s""",
                (owner, after, limit),
            ).fetchall()
        return [dict(id=row["id"], event=row["event"], data=row["payload"]) for row in rows]

    @staticmethod
    def _agent(row):
        result = dict(row)
        result.pop("owner", None)
        result["created_at"] = iso(result["created_at"])
        result["last_seen_at"] = iso(result["last_seen_at"])
        return result

    def register_agent(self, owner, agent_id, name, transport):
        seen = datetime.now(UTC)
        with self._connection() as connection:
            row = connection.execute(
                """INSERT INTO agents(owner,id,name,transport,active,created_at,last_seen_at)
                VALUES(%s,%s,%s,%s,TRUE,%s,%s)
                ON CONFLICT(owner,id) DO UPDATE SET
                    name=excluded.name,transport=excluded.transport,active=TRUE,
                    last_seen_at=excluded.last_seen_at
                RETURNING *""",
                (owner, agent_id, name, transport, seen, seen),
            ).fetchone()
        return self._agent(row)

    def list_agents(self, owner):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM agents WHERE owner=%s AND transport<>'browser' AND active
                ORDER BY last_seen_at DESC,id""",
                (owner,),
            ).fetchall()
        return [self._agent(row) for row in rows]

    def deactivate_agent(self, owner, agent_id):
        with self._connection() as connection:
            connection.execute(
                "UPDATE agents SET active=FALSE WHERE owner=%s AND id=%s",
                (owner, agent_id),
            )

    @staticmethod
    def _message(row):
        result = dict(row)
        result.pop("owner", None)
        result.pop("request_payload", None)
        for field in (
            "created_at",
            "expires_at",
            "delivered_at",
            "read_at",
            "acked_at",
        ):
            result[field] = iso(result[field]) if result.get(field) else None
        result["metadata"] = result.get("metadata") or {}
        return result

    def get_message(self, owner, agent_id, id):
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM agent_messages WHERE owner=%s AND id=%s
                AND (sender_agent_id=%s OR recipient_agent_id=%s)""",
                (owner, id, agent_id, agent_id),
            ).fetchone()
        if not row:
            raise NotFound()
        return self._message(row)

    def send_message(self, owner, sender_agent_id, sender_name, data):
        payload = data.model_dump(mode="json")
        created = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            recipient = connection.execute(
                "SELECT 1 FROM agents WHERE owner=%s AND id=%s AND active",
                (owner, data.recipient_agent_id),
            ).fetchone()
            if not recipient:
                raise NotFound()
            if data.client_request_id:
                existing = connection.execute(
                    """SELECT * FROM agent_messages WHERE owner=%s AND sender_agent_id=%s
                    AND client_request_id=%s FOR UPDATE""",
                    (owner, sender_agent_id, data.client_request_id),
                ).fetchone()
                if existing:
                    if existing["request_payload"] != payload:
                        raise DuplicateRequestConflict()
                    return self._message(existing), False
            thread_id = data.thread_id or uid()
            if data.reply_to:
                parent = connection.execute(
                    """SELECT * FROM agent_messages WHERE owner=%s AND id=%s
                    AND (sender_agent_id=%s OR recipient_agent_id=%s)""",
                    (owner, data.reply_to, sender_agent_id, sender_agent_id),
                ).fetchone()
                participants = (
                    {parent["sender_agent_id"], parent["recipient_agent_id"]}
                    if parent else set()
                )
                if (
                    data.recipient_agent_id not in participants
                    or len(participants) > 1
                    and data.recipient_agent_id == sender_agent_id
                ):
                    raise NotFound()
                if data.thread_id and data.thread_id != parent["thread_id"]:
                    raise ValueError("thread_id must match the replied-to message")
                thread_id = parent["thread_id"]
            message_id = uid()
            row = connection.execute(
                """INSERT INTO agent_messages(
                    owner,id,sender_agent_id,sender_name,recipient_agent_id,kind,subject,body,
                    metadata,thread_id,reply_to,client_request_id,request_payload,status,
                    created_at,expires_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued',%s,%s)
                RETURNING *""",
                (
                    owner,
                    message_id,
                    sender_agent_id,
                    sender_name,
                    data.recipient_agent_id,
                    data.kind,
                    data.subject,
                    data.body,
                    Jsonb(data.metadata),
                    thread_id,
                    data.reply_to,
                    data.client_request_id,
                    Jsonb(payload),
                    created,
                    created + timedelta(seconds=data.expires_in_seconds),
                ),
            ).fetchone()
        return self._message(row), True

    def inbox_messages(self, owner, agent_id, after=0, limit=50, status=None):
        filters = [
            "owner=%s",
            "recipient_agent_id=%s",
            "sequence>%s",
            "expires_at>CURRENT_TIMESTAMP",
        ]
        params = [owner, agent_id, after]
        if status:
            filters.append("status=%s")
            params.append(status)
        params.append(limit)
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM agent_messages WHERE {' AND '.join(filters)} "
                "ORDER BY sequence LIMIT %s",
                tuple(params),
            ).fetchall()
        return [self._message(row) for row in rows]

    def sent_messages(self, owner, agent_id, limit=50, offset=0):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM agent_messages WHERE owner=%s AND sender_agent_id=%s
                ORDER BY sequence DESC OFFSET %s LIMIT %s""",
                (owner, agent_id, offset, limit),
            ).fetchall()
        return [self._message(row) for row in rows]

    def ack_message(self, owner, agent_id, id, status):
        ranks = {"queued": 0, "delivered": 1, "read": 2, "acked": 3}
        stamp = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM agent_messages WHERE owner=%s AND id=%s
                AND recipient_agent_id=%s FOR UPDATE""",
                (owner, id, agent_id),
            ).fetchone()
            if not row:
                raise NotFound()
            if ranks[status] > ranks[row["status"]]:
                connection.execute(
                    """UPDATE agent_messages SET status=%s,
                    delivered_at=CASE WHEN %s>=1 THEN COALESCE(delivered_at,%s) ELSE delivered_at END,
                    read_at=CASE WHEN %s>=2 THEN COALESCE(read_at,%s) ELSE read_at END,
                    acked_at=CASE WHEN %s>=3 THEN COALESCE(acked_at,%s) ELSE acked_at END
                    WHERE owner=%s AND id=%s""",
                    (
                        status,
                        ranks[status], stamp,
                        ranks[status], stamp,
                        ranks[status], stamp,
                        owner, id,
                    ),
                )
        return self.get_message(owner, agent_id, id)

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
        if len(vectors) != len(keywords):
            raise ValueError("Embedding count does not match keyword count")
        record_id, created = record_id or uid(), now()
        security = security or prepare_record_security(title, content, None)
        with self.transaction(), self._connection() as connection:
            if file_id and self.get(owner, file_id)["kind"] != "file":
                raise NotFound()
            connection.execute(
                """INSERT INTO records(
                    owner,id,kind,subtype,title,content,source,tags,created_at,keywords,metadata,file_id,
                    trust_level,security_state,provenance,content_hash,security_warnings,
                    security_history
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    owner,
                    record_id,
                    kind,
                    subtype,
                    title,
                    content,
                    source,
                    tags,
                    created,
                    keywords,
                    Jsonb(metadata),
                    file_id or None,
                    security["trust_level"],
                    security["security_state"],
                    Jsonb(security["provenance"]),
                    security["content_hash"],
                    security["security_warnings"],
                    Jsonb(security["security_history"]),
                ),
            )
            self._index(owner, record_id, keywords, vectors)
            self._event(
                owner, kind + ".created", {"record_id": record_id, "kind": kind}
            )
            if security["security_state"] != "active" or security["security_warnings"]:
                self._event(
                    owner,
                    kind + ".security_updated",
                    {
                        "record_id": record_id,
                        "kind": kind,
                        "trust_level": security["trust_level"],
                        "security_state": security["security_state"],
                        "warnings": security["security_warnings"],
                        "version": 1,
                    },
                )
        return self.get(owner, record_id)

    def _index(self, owner, record_id, keywords, vectors):
        with self._connection() as connection:
            for keyword, vector in zip(keywords, vectors, strict=True):
                connection.execute(
                    """INSERT INTO keyword_embeddings(
                        owner,record_id,keyword,normalized_keyword,embedding
                    ) VALUES(%s,%s,%s,%s,%s::vector)""",
                    (owner, record_id, keyword, keyword.casefold(), vector_literal(vector)),
                )

    def update_keywords(self, owner, id, keywords, vectors):
        if len(vectors) != len(keywords):
            raise ValueError("Embedding count does not match keyword count")
        with self.transaction(), self._connection() as connection:
            record = self.get(owner, id)
            connection.execute(
                "DELETE FROM keyword_embeddings WHERE owner=%s AND record_id=%s", (owner, id)
            )
            connection.execute(
                "UPDATE records SET keywords=%s,version=version+1 WHERE owner=%s AND id=%s",
                (keywords, owner, id),
            )
            self._index(owner, id, keywords, vectors)
            self._event(
                owner,
                record["kind"] + ".updated",
                {"record_id": id, "kind": record["kind"], "change": "keywords"},
            )
        return self.get(owner, id)

    def update_record(self, owner, id, data, vectors=None):
        if data.keywords is not None and (vectors is None or len(vectors) != len(data.keywords)):
            raise ValueError("Embedding count does not match keyword count")
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND id=%s
                AND archived_at IS NULL FOR UPDATE""",
                (owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            if row["version"] != data.expected_version:
                raise Conflict()
            previous = self._record(row)
            title = data.title if data.title is not None else row["title"]
            content = data.content if data.content is not None else row["content"]
            security = reassess_record_security(
                previous, title, content, row["version"] + 1
            )
            security_changed = (
                security["security_state"] != previous["security_state"]
                or security["trust_level"] != previous["trust_level"]
                or security["security_warnings"] != previous["security_warnings"]
            )
            connection.execute(
                """UPDATE records SET
                content=COALESCE(%s,content),title=COALESCE(%s,title),
                subtype=COALESCE(%s,subtype),source=COALESCE(%s,source),
                tags=COALESCE(%s::text[],tags),keywords=COALESCE(%s::text[],keywords),
                metadata=COALESCE(%s,metadata),trust_level=%s,security_state=%s,
                provenance=%s,content_hash=%s,security_warnings=%s,
                security_history=%s,version=version+1
                WHERE owner=%s AND id=%s""",
                (
                    data.content,
                    data.title,
                    data.subtype,
                    data.source,
                    data.tags,
                    data.keywords,
                    Jsonb(data.metadata) if data.metadata is not None else None,
                    security["trust_level"],
                    security["security_state"],
                    Jsonb(security["provenance"]),
                    security["content_hash"],
                    security["security_warnings"],
                    Jsonb(security["security_history"]),
                    owner,
                    id,
                ),
            )
            if data.keywords is not None:
                connection.execute(
                    "DELETE FROM keyword_embeddings WHERE owner=%s AND record_id=%s",
                    (owner, id),
                )
                self._index(owner, id, data.keywords, vectors)
            self._event(
                owner,
                row["kind"] + ".updated",
                {
                    "record_id": id,
                    "kind": row["kind"],
                    "change": "record",
                    "version": row["version"] + 1,
                },
            )
            if security_changed:
                self._event(
                    owner,
                    row["kind"] + ".security_updated",
                    {
                        "record_id": id,
                        "kind": row["kind"],
                        "trust_level": security["trust_level"],
                        "security_state": security["security_state"],
                        "warnings": security["security_warnings"],
                        "version": row["version"] + 1,
                    },
                )
        return self.get(owner, id)

    def update_security(self, owner, id, data):
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND id=%s
                AND archived_at IS NULL FOR UPDATE""",
                (owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            if row["version"] != data.expected_version:
                raise Conflict()
            record = self._record(row)
            security = apply_security_update(record, data)
            connection.execute(
                """UPDATE records SET trust_level=%s,security_state=%s,provenance=%s,
                content_hash=%s,security_warnings=%s,security_history=%s,version=version+1
                WHERE owner=%s AND id=%s""",
                (
                    security["trust_level"],
                    security["security_state"],
                    Jsonb(security["provenance"]),
                    security["content_hash"],
                    security["security_warnings"],
                    Jsonb(security["security_history"]),
                    owner,
                    id,
                ),
            )
            self._event(
                owner,
                row["kind"] + ".security_updated",
                {
                    "record_id": id,
                    "kind": row["kind"],
                    "trust_level": security["trust_level"],
                    "security_state": security["security_state"],
                    "warnings": security["security_warnings"],
                    "reason": data.reason,
                    "version": row["version"] + 1,
                },
            )
        return self.get(owner, id)

    def get(self, owner, id, internal=False):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM records WHERE owner=%s AND id=%s AND archived_at IS NULL",
                (owner, id),
            ).fetchone()
        if not row:
            raise NotFound()
        result = self._record(row)
        if internal:
            result["embedding"] = []
            result["owner"] = owner
            result["parent_id"] = ""
            result["start_offset"] = 0
            result["end_offset"] = 0
        return result

    def archived(self, owner, limit=50, offset=0):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND archived_at IS NOT NULL
                ORDER BY archived_at DESC,id OFFSET %s LIMIT %s""",
                (owner, offset, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = self._record(row)
            item["archived_at"] = iso(row["archived_at"])
            result.append(item)
        return result

    def list(
        self,
        owner,
        kind=None,
        limit=50,
        offset=0,
        include_untrusted=False,
        include_quarantined=False,
    ):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND archived_at IS NULL
                AND (%s='' OR kind=%s)
                AND (%s OR trust_level='trusted')
                AND (%s OR security_state='active')
                ORDER BY created_at DESC,id OFFSET %s LIMIT %s""",
                (
                    owner,
                    kind or "",
                    kind or "",
                    include_untrusted,
                    include_quarantined,
                    offset,
                    limit,
                ),
            ).fetchall()
        return [self._record(row) for row in rows]

    def quarantined(self, owner, limit=50, offset=0):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND archived_at IS NULL
                AND security_state='quarantined'
                ORDER BY created_at DESC,id OFFSET %s LIMIT %s""",
                (owner, offset, limit),
            ).fetchall()
        return [self._record(row) for row in rows]

    def delete(self, owner, id):
        with self.transaction(), self._connection() as connection:
            record = self.get(owner, id)
            if record["kind"] == "file":
                referenced = connection.execute(
                    """SELECT 1 FROM records WHERE owner=%s AND file_id=%s
                    AND archived_at IS NULL LIMIT 1""",
                    (owner, id),
                ).fetchone()
                if referenced:
                    raise FileInUse()
            connection.execute("DELETE FROM records WHERE owner=%s AND id=%s", (owner, id))
            self._event(
                owner,
                record["kind"] + ".deleted",
                {
                    "record_id": id,
                    "kind": record["kind"],
                    "incident_relations_removed": True,
                },
            )

    def archive(self, owner, id, expected_version, reason):
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND id=%s
                AND archived_at IS NULL FOR UPDATE""",
                (owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            if row["version"] != expected_version:
                raise Conflict()
            if row["kind"] == "file":
                referenced = connection.execute(
                    """SELECT 1 FROM records WHERE owner=%s AND file_id=%s
                    AND archived_at IS NULL LIMIT 1""",
                    (owner, id),
                ).fetchone()
                if referenced:
                    raise FileInUse()
            archived_at = now()
            connection.execute(
                """UPDATE records SET archived_at=%s,version=version+1
                WHERE owner=%s AND id=%s""",
                (archived_at, owner, id),
            )
            self._event(
                owner,
                row["kind"] + ".archived",
                {
                    "record_id": id,
                    "kind": row["kind"],
                    "reason": reason,
                    "version": row["version"] + 1,
                    "recoverable": True,
                },
            )
        return {"id": id, "archived_at": archived_at, "version": row["version"] + 1}

    def restore(self, owner, id, expected_version, reason):
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND id=%s
                AND archived_at IS NOT NULL FOR UPDATE""",
                (owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            if row["version"] != expected_version:
                raise Conflict()
            if row["kind"] == "document" and row["file_id"]:
                file_row = connection.execute(
                    """SELECT 1 FROM records WHERE owner=%s AND id=%s
                    AND kind='file' AND archived_at IS NULL""",
                    (owner, row["file_id"]),
                ).fetchone()
                if not file_row:
                    raise NotFound()
            connection.execute(
                """UPDATE records SET archived_at=NULL,version=version+1
                WHERE owner=%s AND id=%s""",
                (owner, id),
            )
            self._event(
                owner,
                row["kind"] + ".restored",
                {
                    "record_id": id,
                    "kind": row["kind"],
                    "reason": reason,
                    "version": row["version"] + 1,
                },
            )
        return self.get(owner, id)

    def merge(self, owner, data):
        ids = [data.canonical_id, *data.duplicate_ids]
        duplicates = set(data.duplicate_ids)
        with self.transaction(), self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM records WHERE owner=%s AND id=ANY(%s)
                AND archived_at IS NULL FOR UPDATE""",
                (owner, ids),
            ).fetchall()
            records = {row["id"]: row for row in rows}
            if set(records) != set(ids):
                raise NotFound()
            if any(
                records[id]["version"] != data.expected_versions[id] for id in ids
            ):
                raise Conflict()
            kinds = {records[id]["kind"] for id in ids}
            if len(kinds) != 1 or "file" in kinds:
                raise ValueError("Only records of the same non-file kind can be merged")
            edges = connection.execute(
                """SELECT * FROM relations WHERE owner=%s
                AND (source_id=ANY(%s) OR target_id=ANY(%s)) FOR UPDATE""",
                (owner, data.duplicate_ids, data.duplicate_ids),
            ).fetchall()
            rewired = retracted = 0
            for edge in edges:
                source = data.canonical_id if edge["source_id"] in duplicates else edge["source_id"]
                target = data.canonical_id if edge["target_id"] in duplicates else edge["target_id"]
                version = edge["version"] + 1
                change_reason = "Record merge: " + data.reason
                if source == target:
                    history = edge["history"] + [
                        dict(status="retracted", reason=change_reason, at=now(), version=version)
                    ]
                    connection.execute(
                        """UPDATE relations SET status='retracted',reason=%s,version=%s,history=%s
                        WHERE owner=%s AND id=%s""",
                        (change_reason, version, Jsonb(history), owner, edge["id"]),
                    )
                    retracted += 1
                else:
                    history = edge["history"] + [
                        dict(status=edge["status"], reason=change_reason, at=now(), version=version)
                    ]
                    connection.execute(
                        """UPDATE relations SET source_id=%s,target_id=%s,reason=%s,
                        version=%s,history=%s WHERE owner=%s AND id=%s""",
                        (
                            source,
                            target,
                            change_reason,
                            version,
                            Jsonb(history),
                            owner,
                            edge["id"],
                        ),
                    )
                    rewired += 1
            archived_at = now()
            connection.execute(
                """UPDATE records SET archived_at=%s,version=version+1
                WHERE owner=%s AND id=ANY(%s)""",
                (archived_at, owner, data.duplicate_ids),
            )
            connection.execute(
                """UPDATE records SET version=version+1 WHERE owner=%s AND id=%s""",
                (owner, data.canonical_id),
            )
            self._event(
                owner,
                "record.merged",
                {
                    "canonical_id": data.canonical_id,
                    "archived_ids": data.duplicate_ids,
                    "reason": data.reason,
                    "relations_rewired": rewired,
                    "relations_retracted": retracted,
                },
            )
        return {
            "canonical": self.get(owner, data.canonical_id),
            "archived_ids": data.duplicate_ids,
            "archived_at": archived_at,
            "relations_rewired": rewired,
            "relations_retracted": retracted,
            "archived_records_recoverable": True,
        }

    def link(self, owner, data):
        with self.transaction(), self._connection() as connection:
            self.get(owner, data.source_id)
            self.get(owner, data.target_id)
            if data.source_id == data.target_id:
                raise ValueError("A relationship must connect two distinct records")
            id, created = uid(), now()
            history = [dict(status="active", reason=data.reason, at=created, version=1)]
            connection.execute(
                """INSERT INTO relations(
                    owner,id,source_id,target_id,relation,reason,status,version,created_at,history
                ) VALUES(%s,%s,%s,%s,%s,%s,'active',1,%s,%s)""",
                (
                    owner,
                    id,
                    data.source_id,
                    data.target_id,
                    data.relation,
                    data.reason,
                    created,
                    Jsonb(history),
                ),
            )
            self._event(
                owner,
                "relation.created",
                {
                    "relation_id": id,
                    "source_id": data.source_id,
                    "target_id": data.target_id,
                    "version": 1,
                },
            )
        return next(row for row in self.relations(owner, "all") if row["id"] == id)

    def relations(self, owner, status="active"):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT e.source_id,e.target_id,e.id,e.relation,e.reason,e.status,
                e.version,e.created_at,e.history
                FROM relations e
                JOIN records a ON a.owner=e.owner AND a.id=e.source_id
                JOIN records b ON b.owner=e.owner AND b.id=e.target_id
                WHERE e.owner=%s AND a.archived_at IS NULL AND b.archived_at IS NULL
                AND (%s='all' OR e.status=%s)
                ORDER BY e.created_at,e.id""",
                (owner, status, status),
            ).fetchall()
        return [self._relation(row) for row in rows]

    def update_link(self, owner, id, data):
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM relations WHERE owner=%s AND id=%s FOR UPDATE", (owner, id)
            ).fetchone()
            if not row:
                raise NotFound()
            edge = self._relation(row)
            if edge["version"] != data.expected_version:
                raise Conflict()
            if edge["status"] == data.status:
                return edge
            version = edge["version"] + 1
            history = edge["history"] + [
                dict(status=data.status, reason=data.reason, at=now(), version=version)
            ]
            connection.execute(
                """UPDATE relations SET status=%s,reason=%s,version=%s,history=%s
                WHERE owner=%s AND id=%s""",
                (data.status, data.reason, version, Jsonb(history), owner, id),
            )
            self._event(
                owner,
                "relation.updated",
                {
                    "relation_id": id,
                    "source_id": edge["source_id"],
                    "target_id": edge["target_id"],
                    "version": version,
                },
            )
            return {
                **edge,
                "status": data.status,
                "reason": data.reason,
                "version": version,
                "history": history,
            }

    def vector_search(self, owner, request, query_vectors, model_name):
        """Run an exact, owner-scoped cosine search with pgvector.

        Query text never reaches this method. The caller embeds only the keywords
        already extracted by the connected agent.
        """
        kind = {"memories": "memory", "documents": "document", "entities": "entity"}.get(
            request.scope, request.scope
        )
        records = {}
        with self._connection() as connection:
            for index, term in enumerate(request.keywords):
                if request.match_mode == "exact":
                    rows = connection.execute(
                        """SELECT r.*,k.keyword AS stored_keyword,NULL AS cosine_distance
                        FROM keyword_embeddings k JOIN records r
                        ON r.owner=k.owner AND r.id=k.record_id
                        WHERE k.owner=%s AND r.archived_at IS NULL
                        AND k.normalized_keyword=%s
                        AND (%s='all' OR r.kind=%s)
                        AND (cardinality(%s::text[])=0 OR r.tags @> %s::text[])
                        ORDER BY r.id,k.id""",
                        (owner, term.casefold(), kind, kind, request.tags, request.tags),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        """SELECT r.*,k.keyword AS stored_keyword,
                        (k.embedding <=> %s::vector) AS cosine_distance
                        FROM keyword_embeddings k JOIN records r
                        ON r.owner=k.owner AND r.id=k.record_id
                        WHERE k.owner=%s AND r.archived_at IS NULL
                        AND (%s='all' OR r.kind=%s)
                        AND (cardinality(%s::text[])=0 OR r.tags @> %s::text[])
                        ORDER BY cosine_distance,r.id,k.id""",
                        (
                            vector_literal(query_vectors[index]),
                            owner,
                            kind,
                            kind,
                            request.tags,
                            request.tags,
                        ),
                    ).fetchall()
                for row in rows:
                    entry = records.setdefault(
                        row["id"], {"record": self._record(row), "matches": {}}
                    )
                    exact = row["stored_keyword"].casefold() == term.casefold()
                    similarity = (
                        1.0
                        if exact and request.match_mode in {"exact", "hybrid"}
                        else 1.0 - float(row["cosine_distance"])
                    )
                    best = entry["matches"].get(term)
                    if best is None or similarity > best["similarity"]:
                        entry["matches"][term] = {
                            "query_keyword": term,
                            "stored_keyword": row["stored_keyword"],
                            "similarity": similarity,
                        }
        hits = []
        for entry in records.values():
            record = entry["record"]
            matches = list(entry["matches"].values())
            if not matches or not record_matches_filters(record, record["keywords"], request):
                continue
            score = sum(match["similarity"] for match in matches) / len(request.keywords)
            if score < request.min_score:
                continue
            hits.append(
                {
                    "id": record["id"],
                    "kind": record["kind"],
                    "title": record["title"],
                    "source": record["source"],
                    "keywords": record["keywords"],
                    "metadata": record["metadata"],
                    "trust_level": record["trust_level"],
                    "security_state": record["security_state"],
                    "security_warnings": record["security_warnings"],
                    "provenance": record["provenance"],
                    "matched_keywords": matches,
                    "score": score,
                }
            )
        hits.sort(key=lambda hit: (-hit["score"], hit["id"]))
        return {
            "mode": "keyword_vector",
            "match_mode": request.match_mode,
            "embedding_model": model_name,
            "keywords": request.keywords,
            "hits": hits[: request.limit],
        }

    def candidates(self, owner, scope, tags):
        kind = {"memories": "memory", "documents": "document", "entities": "entity"}.get(
            scope, scope
        )
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT k.keyword,k.embedding::text AS embedding,r.*
                FROM keyword_embeddings k JOIN records r
                ON r.owner=k.owner AND r.id=k.record_id
                WHERE k.owner=%s AND r.archived_at IS NULL AND (%s='all' OR r.kind=%s)
                AND (%s::text[]='{}'::text[] OR r.tags @> %s::text[])""",
                (owner, kind, kind, tags, tags),
            ).fetchall()
        result = []
        for row in rows:
            parent = self._record(row)
            parent.pop("keyword", None)
            parent.pop("embedding", None)
            keyword = {
                "content": row["keyword"],
                "title": row["keyword"],
                "embedding": vector_from_text(row["embedding"]),
                "kind": "keyword",
            }
            result.append((keyword, parent))
        return result

    def neighborhood(
        self,
        owner,
        seeds,
        depth,
        include_untrusted=False,
        include_quarantined=False,
    ):
        edges = self.relations(owner)
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
                source, target = edge["source_id"], edge["target_id"]
                if (
                    (source in frontier or target in frontier)
                    and can_retrieve(source)
                    and can_retrieve(target)
                ):
                    selected[edge["id"]] = edge
                    following.update((source, target))
            frontier = following - visited
            visited.update(following)
        return {
            "nodes": [self.get(owner, id) for id in sorted(visited - set(seeds))],
            "relations": list(selected.values()),
        }

    @staticmethod
    def _feature(row):
        result = dict(row)
        result.pop("owner", None)
        result["created_at"] = iso(result["created_at"])
        return result

    def get_feature_request(self, owner, id):
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM feature_requests WHERE owner=%s AND id=%s", (owner, id)
            ).fetchone()
        if not row:
            raise NotFound()
        return self._feature(row)

    def list_feature_requests(self, owner, limit=50, offset=0):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM feature_requests WHERE owner=%s
                ORDER BY created_at DESC,id OFFSET %s LIMIT %s""",
                (owner, offset, limit),
            ).fetchall()
        return [self._feature(row) for row in rows]

    def add_feature_request(self, owner, data):
        payload = data.model_dump()
        with self.transaction(), self._connection() as connection:
            if data.client_request_id:
                existing = connection.execute(
                    """SELECT * FROM feature_requests
                    WHERE owner=%s AND client_request_id=%s FOR UPDATE""",
                    (owner, data.client_request_id),
                ).fetchone()
                if existing:
                    record = self._feature(existing)
                    if any(record[key] != value for key, value in payload.items()):
                        raise DuplicateRequestConflict()
                    return record, False
            record = {
                **payload,
                "id": uid(),
                "owner": owner,
                "status": "received",
                "created_at": now(),
            }
            connection.execute(
                """INSERT INTO feature_requests(
                    owner,id,title,description,agent_name,use_case,priority,source,
                    client_request_id,status,created_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                tuple(
                    record[key]
                    for key in (
                        "owner",
                        "id",
                        "title",
                        "description",
                        "agent_name",
                        "use_case",
                        "priority",
                        "source",
                        "client_request_id",
                        "status",
                        "created_at",
                    )
                ),
            )
        return self.get_feature_request(owner, record["id"]), True

    def stats(self, owner):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT kind,count(*) AS count FROM records
                WHERE owner=%s AND archived_at IS NULL GROUP BY kind""",
                (owner,),
            ).fetchall()
            relation_count = connection.execute(
                "SELECT count(*) AS count FROM relations WHERE owner=%s AND status='active'",
                (owner,),
            ).fetchone()["count"]
            usage = connection.execute(
                """SELECT COALESCE(sum(
                    octet_length(subtype) + octet_length(title) + octet_length(content)
                    + octet_length(source) + octet_length(to_jsonb(tags)::text)
                    + octet_length(to_jsonb(keywords)::text) + octet_length(metadata::text)
                    + octet_length(COALESCE(file_id,'')) + octet_length(provenance::text)
                    + octet_length(to_jsonb(security_warnings)::text)
                    + octet_length(security_history::text)
                ),0)::bigint AS memory_bytes,
                COALESCE(sum(CASE
                    WHEN kind='file' AND metadata->>'size_bytes' ~ '^[0-9]+$'
                    THEN (metadata->>'size_bytes')::numeric ELSE 0
                END),0)::bigint AS file_bytes
                FROM records WHERE owner=%s""",
                (owner,),
            ).fetchone()
            relation_bytes = connection.execute(
                """SELECT COALESCE(sum(
                    octet_length(source_id) + octet_length(target_id)
                    + octet_length(relation) + octet_length(reason) + octet_length(status)
                    + octet_length(history::text)
                ),0)::bigint AS bytes FROM relations WHERE owner=%s""",
                (owner,),
            ).fetchone()["bytes"]
        result = {"memory": 0, "document": 0, "entity": 0, "file": 0}
        result.update({row["kind"]: row["count"] for row in rows})
        result["relations"] = relation_count
        memory_bytes = usage["memory_bytes"] + relation_bytes
        file_bytes = usage["file_bytes"]
        result["memory_bytes"] = memory_bytes
        result["file_bytes"] = file_bytes
        result["storage_bytes"] = memory_bytes + file_bytes
        return result
