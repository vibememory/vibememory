import json
import threading
from contextlib import contextmanager
from uuid import uuid4

import kuzu

from .clock import utc_now_iso


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
            created_at STRING, history STRING)""")
        self.query("CREATE NODE TABLE IF NOT EXISTS Meta(key STRING PRIMARY KEY, value STRING)")
        self.query("""CREATE NODE TABLE IF NOT EXISTS FeatureRequest(
            id STRING PRIMARY KEY, owner STRING, title STRING, description STRING,
            agent_name STRING, use_case STRING, priority STRING, source STRING,
            client_request_id STRING, status STRING, created_at STRING)""")
        self.query("""CREATE NODE TABLE IF NOT EXISTS ChangeEvent(
            id INT64 PRIMARY KEY, owner STRING, event STRING, payload STRING)""")
        self.event_sequence = self.query(
            "MATCH (e:ChangeEvent) RETURN max(e.id) AS latest"
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
        return result

    def _node(self, item):
        item.setdefault("file_id", "")
        item.setdefault("version", 1)
        item.setdefault("archived_at", "")
        self.query(
            """CREATE (:Item {id: $id, owner: $owner, kind: $kind, subtype: $subtype,
            title: $title, content: $content, source: $source, tags: $tags, created_at: $created_at,
            embedding: $embedding, parent_id: $parent_id, start_offset: $start_offset,
            end_offset: $end_offset, keywords: $keywords, metadata: $metadata, file_id: $file_id,
            version: $version, archived_at: $archived_at})""",
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
    ):
        id, created = record_id or uid(), now()
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
                )
            )
            self._index(owner, id, keywords, vectors)
            self._event(owner, kind + ".created", {"record_id": id, "kind": kind})
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
            return self.get(owner, id)

    def get(self, owner, id, internal=False):
        rows = self.query(
            """MATCH (n:Item {owner: $owner, id: $id})
            WHERE n.archived_at = '' RETURN n""", {"owner": owner, "id": id}
        )
        if not rows or (not internal and rows[0]["n"]["kind"] in {"chunk", "keyword"}):
            raise NotFound()
        return self.clean(rows[0]["n"], internal)

    def list(self, owner, kind=None, limit=50, offset=0):
        rows = self.query(
            """MATCH (n:Item {owner: $owner})
            WHERE n.kind <> 'chunk' AND n.kind <> 'keyword' AND n.archived_at = ''
            AND ($kind = '' OR n.kind = $kind)
            RETURN n ORDER BY n.created_at DESC, n.id SKIP $offset LIMIT $limit""",
            {"owner": owner, "kind": kind or "", "limit": limit, "offset": offset},
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
                new_id = self._link(owner, source, target, edge["relation"], change_reason)
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

    def _link(self, owner, source, target, relation, reason):
        id, created = uid(), now()
        history = json.dumps([dict(status="active", reason=reason, at=created, version=1)])
        self.query(
            """MATCH (a:Item {owner: $owner, id: $source}),
            (b:Item {owner: $owner, id: $target})
            CREATE (a)-[:Link {id: $id, relation: $relation, reason: $reason, status: 'active',
                version: 1, created_at: $created, history: $history}]->(b)""",
            dict(
                owner=owner,
                source=source,
                target=target,
                id=id,
                relation=relation,
                reason=reason,
                created=created,
                history=history,
            ),
        )
        return id

    def link(self, owner, data):
        with self.transaction():
            self.get(owner, data.source_id)
            self.get(owner, data.target_id)
            if data.source_id == data.target_id:
                raise ValueError("A relationship must connect two distinct records")
            id = self._link(owner, data.source_id, data.target_id, data.relation, data.reason)
            self._event(owner, "relation.created", {"relation_id": id,
                        "source_id": data.source_id, "target_id": data.target_id, "version": 1})
            return next(r for r in self.relations(owner, "all") if r["id"] == id)

    def relations(self, owner, status="active"):
        rows = self.query(
            """MATCH (a:Item {owner: $owner})-[r:Link]->(b:Item {owner: $owner})
            WHERE r.relation <> 'CHUNK_OF' AND r.relation <> 'KEYWORD_OF' AND ($status = 'all' OR r.status = $status)
            AND a.archived_at = '' AND b.archived_at = ''
            RETURN a.id AS source_id, b.id AS target_id, r.id AS id, r.relation AS relation,
                r.reason AS reason, r.status AS status, r.version AS version,
                r.created_at AS created_at, r.history AS history""",
            {"owner": owner, "status": status},
        )
        for row in rows:
            row["history"] = json.loads(row["history"])
        return rows

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

    def neighborhood(self, owner, seeds, depth):
        # Bounded BFS over real stored graph edges; retracted links never enter retrieval.
        edges = self.relations(owner)
        visited, frontier, selected = set(seeds), set(seeds), {}
        for _ in range(depth):
            following = set()
            for edge in edges:
                a, b = edge["source_id"], edge["target_id"]
                if a in frontier or b in frontier:
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
        return {
            key: value for key, value in node.items() if not key.startswith("_") and key != "owner"
        }

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
                "created_at": now(),
            }
            self.query(
                """CREATE (:FeatureRequest {id: $id, owner: $owner, title: $title,
                description: $description, agent_name: $agent_name, use_case: $use_case,
                priority: $priority, source: $source, client_request_id: $client_request_id,
                status: $status, created_at: $created_at})""",
                record,
            )
            return self.get_feature_request(owner, record["id"]), True

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
            return result
