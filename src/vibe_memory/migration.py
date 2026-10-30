"""Offline migration from the embedded Kuzu/SQLite layout to PostgreSQL."""

import json
import sqlite3
from pathlib import Path

import kuzu
from psycopg import sql
from psycopg.types.json import Jsonb

from .postgres import PostgresDatabase, vector_literal

AUTH_TABLES = {
    "users": ("id", "email", "name", "salt", "password_hash", "created_at"),
    "sessions": ("hash", "user_id", "expires_at"),
    "api_keys": (
        "id",
        "user_id",
        "hash",
        "name",
        "prefix",
        "created_at",
        "vault_access",
    ),
    "device_logins": (
        "device_hash",
        "user_hash",
        "name",
        "expires_at",
        "state",
        "user_id",
        "polled_at",
        "vault_access",
    ),
    "auth_attempts": ("key", "count", "resets_at"),
    "user_totp": ("user_id", "nonce", "ciphertext", "enabled_at", "last_counter"),
    "totp_setups": ("user_id", "nonce", "ciphertext", "expires_at"),
    "recovery_codes": ("user_id", "hash", "created_at"),
    "login_challenges": ("hash", "user_id", "expires_at", "attempts"),
    "oauth_clients": ("client_id", "client_name", "redirect_uris", "created_at"),
    "oauth_codes": (
        "hash",
        "client_id",
        "user_id",
        "redirect_uri",
        "scope",
        "resource",
        "code_challenge",
        "expires_at",
    ),
    "oauth_access_tokens": (
        "hash",
        "client_id",
        "user_id",
        "scope",
        "resource",
        "created_at",
        "expires_at",
    ),
    "oauth_refresh_tokens": (
        "hash",
        "client_id",
        "user_id",
        "scope",
        "resource",
        "created_at",
        "expires_at",
    ),
    "oauth_connections": (
        "client_id",
        "user_id",
        "scope",
        "created_at",
        "last_used_at",
    ),
    "oauth_permission_events": (
        "id",
        "user_id",
        "client_id",
        "client_name",
        "changed_at",
        "before_scope",
        "after_scope",
        "source",
    ),
}

VAULT_COLUMNS = (
    "user_id",
    "name",
    "description",
    "nonce",
    "ciphertext",
    "created_at",
    "updated_at",
    "last_accessed_at",
    "access_count",
)

DESTINATION_TABLES = (
    *AUTH_TABLES,
    "records",
    "keyword_embeddings",
    "relations",
    "batch_operations",
    "change_events",
    "feature_requests",
    "agents",
    "agent_messages",
    "vault_secrets",
)


def _sqlite_rows(path: Path, table: str, columns: tuple[str, ...]):
    if not path.is_file():
        return []
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            return []
        names = ",".join(columns)
        return [dict(row) for row in connection.execute(f"SELECT {names} FROM {table}")]


def _kuzu_rows(connection, statement):
    result = connection.execute(statement)
    try:
        names = result.get_column_names()
        rows = []
        while result.has_next():
            rows.append(dict(zip(names, result.get_next(), strict=True)))
        return rows
    finally:
        result.close()


def read_legacy(data_dir: Path):
    payload = {
        table: _sqlite_rows(data_dir / "auth.sqlite", table, columns)
        for table, columns in AUTH_TABLES.items()
    }
    payload["vault_secrets"] = _sqlite_rows(
        data_dir / "vault.sqlite", "vault_secrets", VAULT_COLUMNS
    )
    payload.update(
        records=[],
        keyword_embeddings=[],
        relations=[],
        batch_operations=[],
        change_events=[],
        feature_requests=[],
        agents=[],
        agent_messages=[],
        meta={},
    )
    graph = data_dir / "graph"
    if not graph.exists():
        return payload
    try:
        database = kuzu.Database(str(graph), read_only=True, max_num_threads=1)
    except RuntimeError as error:
        raise RuntimeError(
            "Legacy graph is locked. Stop every Vibe Memory API process before migration."
        ) from error
    connection = kuzu.Connection(database)
    try:
        graph_tables = {
            row["name"] for row in _kuzu_rows(connection, "CALL show_tables() RETURN *")
        }
        for row in _kuzu_rows(
            connection,
            "MATCH (n:Item) WHERE n.kind <> 'keyword' AND n.kind <> 'chunk' RETURN n",
        ):
            node = row["n"]
            payload["records"].append(
                {
                    "owner": node.get("owner", ""),
                    "id": node["id"],
                    "kind": node["kind"],
                    "subtype": node.get("subtype") or "",
                    "title": node.get("title") or "",
                    "content": node.get("content") or "",
                    "source": node.get("source") or "",
                    "tags": node.get("tags") or [],
                    "created_at": node.get("created_at"),
                    "keywords": node.get("keywords") or [],
                    "metadata": json.loads(node.get("metadata") or "{}"),
                    "file_id": node.get("file_id") or None,
                    "version": node.get("version") or 1,
                    "archived_at": node.get("archived_at") or None,
                    "creator_agent_id": node.get("creator_agent_id") or "unknown",
                    "creator_agent_name": node.get("creator_agent_name") or "Unknown agent",
                    "writer_history": json.loads(node.get("writer_history") or "[]"),
                }
            )
        for row in _kuzu_rows(connection, "MATCH (n:Item {kind: 'keyword'}) RETURN n"):
            node = row["n"]
            payload["keyword_embeddings"].append(
                {
                    "owner": node.get("owner", ""),
                    "record_id": node.get("parent_id", ""),
                    "keyword": node.get("content") or node.get("title") or "",
                    "embedding": node.get("embedding") or [],
                    "created_at": node.get("created_at"),
                }
            )
        for row in _kuzu_rows(
            connection,
            """MATCH (a:Item)-[r:Link]->(b:Item)
            WHERE r.relation <> 'KEYWORD_OF' AND r.relation <> 'CHUNK_OF'
            RETURN a.owner AS owner,a.id AS source_id,b.id AS target_id,r""",
        ):
            relation = row["r"]
            payload["relations"].append(
                {
                    "owner": row["owner"],
                    "id": relation["id"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "relation": relation["relation"],
                    "reason": relation["reason"],
                    "status": relation["status"],
                    "version": relation["version"],
                    "created_at": relation["created_at"],
                    "history": json.loads(relation["history"]),
                    "creator_agent_id": relation.get("creator_agent_id") or "unknown",
                    "creator_agent_name": relation.get("creator_agent_name") or "Unknown agent",
                    "confidence": relation.get("confidence"),
                    "evidence_record_ids": relation.get("evidence_record_ids") or [],
                    "evidence": json.loads(relation.get("evidence") or "[]"),
                    "evidence_coverage": relation.get("evidence_coverage") or "unknown",
                    "input_manifest_id": relation.get("input_manifest_id") or None,
                    "extraction_method": relation.get("extraction_method") or "",
                    "extraction_version": relation.get("extraction_version") or "",
                    "correction_scope": relation.get("correction_scope") or "unknown",
                }
            )
        for row in _kuzu_rows(connection, "MATCH (e:ChangeEvent) RETURN e ORDER BY e.id"):
            event = row["e"]
            payload["change_events"].append(
                {
                    "id": event["id"],
                    "owner": event["owner"],
                    "event": event["event"],
                    "payload": json.loads(event["payload"]),
                }
            )
        for row in _kuzu_rows(connection, "MATCH (r:FeatureRequest) RETURN r"):
            request = row["r"]
            payload["feature_requests"].append(
                {key: value for key, value in request.items() if not key.startswith("_")}
            )
        if "Agent" in graph_tables:
            for row in _kuzu_rows(connection, "MATCH (a:Agent) RETURN a"):
                payload["agents"].append(
                    {key: value for key, value in row["a"].items() if not key.startswith("_")}
                )
        if "AgentMessage" in graph_tables:
            for row in _kuzu_rows(
                connection, "MATCH (m:AgentMessage) RETURN m ORDER BY m.sequence"
            ):
                message = {key: value for key, value in row["m"].items() if not key.startswith("_")}
                message["metadata"] = json.loads(message.get("metadata") or "{}")
                message["request_payload"] = json.loads(message.get("request_payload") or "{}")
                for field in (
                    "reply_to",
                    "client_request_id",
                    "delivered_at",
                    "read_at",
                    "acked_at",
                ):
                    message[field] = message.get(field) or None
                payload["agent_messages"].append(message)
        if "BatchOperation" in graph_tables:
            for row in _kuzu_rows(connection, "MATCH (b:BatchOperation) RETURN b"):
                operation = {
                    key: value
                    for key, value in row["b"].items()
                    if not key.startswith("_") and key != "id"
                }
                operation["result"] = json.loads(operation.get("result") or "{}")
                payload["batch_operations"].append(operation)
        payload["meta"] = {
            row["key"]: row["value"]
            for row in _kuzu_rows(connection, "MATCH (m:Meta) RETURN m.key AS key,m.value AS value")
        }
    finally:
        connection.close()
        database.close()
    return payload


def summary(payload):
    return {table: len(payload.get(table, [])) for table in DESTINATION_TABLES}


def _insert_rows(connection, table, columns, rows):
    if not rows:
        return
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(sql.Placeholder() for _ in columns),
    )
    values = []
    for row in rows:
        record = []
        for column in columns:
            value = row[column]
            if column == "vault_access":
                value = bool(value)
            record.append(value)
        values.append(record)
    with connection.cursor() as cursor:
        cursor.executemany(statement, values)


def migrate_legacy(data_dir, database_url, model, dimension, pool_size=4):
    payload = read_legacy(Path(data_dir))
    source_model = payload["meta"].get("embedding_model")
    if source_model and source_model != model:
        raise ValueError(
            f"Legacy embedding model is {source_model!r}, configured model is {model!r}"
        )
    database = PostgresDatabase(database_url, model, dimension, pool_size)
    try:
        with database.connection() as connection, connection.transaction():
            existing = {
                table: connection.execute(
                    sql.SQL("SELECT count(*) AS count FROM {}").format(sql.Identifier(table))
                ).fetchone()["count"]
                for table in DESTINATION_TABLES
            }
            occupied = {table: count for table, count in existing.items() if count}
            if occupied:
                raise RuntimeError(f"PostgreSQL destination is not empty: {occupied}")

            for table, columns in AUTH_TABLES.items():
                _insert_rows(connection, table, columns, payload[table])

            for record in payload["records"]:
                connection.execute(
                    """INSERT INTO records(
                        owner,id,kind,subtype,title,content,source,tags,created_at,
                        keywords,metadata,file_id,version,archived_at,
                        creator_agent_id,creator_agent_name,writer_history
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        record["owner"],
                        record["id"],
                        record["kind"],
                        record["subtype"],
                        record["title"],
                        record["content"],
                        record["source"],
                        record["tags"],
                        record["created_at"],
                        record["keywords"],
                        Jsonb(record["metadata"]),
                        record["file_id"],
                        record["version"],
                        record["archived_at"],
                        record.get("creator_agent_id") or "unknown",
                        record.get("creator_agent_name") or "Unknown agent",
                        Jsonb(record.get("writer_history") or []),
                    ),
                )
            for keyword in payload["keyword_embeddings"]:
                if len(keyword["embedding"]) != dimension:
                    raise ValueError(
                        f"Keyword {keyword['keyword']!r} has {len(keyword['embedding'])} dimensions; expected {dimension}"
                    )
                connection.execute(
                    """INSERT INTO keyword_embeddings(
                        owner,record_id,keyword,normalized_keyword,embedding,created_at
                    ) VALUES(%s,%s,%s,%s,%s::vector,%s)""",
                    (
                        keyword["owner"],
                        keyword["record_id"],
                        keyword["keyword"],
                        keyword["keyword"].casefold(),
                        vector_literal(keyword["embedding"]),
                        keyword["created_at"],
                    ),
                )
            for relation in payload["relations"]:
                connection.execute(
                    """INSERT INTO relations(
                        owner,id,source_id,target_id,relation,reason,status,version,created_at,history,
                        creator_agent_id,creator_agent_name,confidence,evidence_record_ids,evidence,
                        evidence_coverage,input_manifest_id,extraction_method,extraction_version,
                        correction_scope
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        relation["owner"],
                        relation["id"],
                        relation["source_id"],
                        relation["target_id"],
                        relation["relation"],
                        relation["reason"],
                        relation["status"],
                        relation["version"],
                        relation["created_at"],
                        Jsonb(relation["history"]),
                        relation.get("creator_agent_id") or "unknown",
                        relation.get("creator_agent_name") or "Unknown agent",
                        relation.get("confidence"),
                        relation.get("evidence_record_ids") or [],
                        Jsonb(relation.get("evidence") or []),
                        relation.get("evidence_coverage") or "unknown",
                        relation.get("input_manifest_id") or None,
                        relation.get("extraction_method") or "",
                        relation.get("extraction_version") or "",
                        relation.get("correction_scope") or "unknown",
                    ),
                )
            for operation in payload["batch_operations"]:
                connection.execute(
                    """INSERT INTO batch_operations(
                        owner,agent_id,operation,client_request_id,request_hash,result,created_at
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        operation["owner"],
                        operation["agent_id"],
                        operation["operation"],
                        operation["client_request_id"],
                        operation["request_hash"],
                        Jsonb(operation["result"]),
                        operation["created_at"],
                    ),
                )
            for request in payload["feature_requests"]:
                connection.execute(
                    """INSERT INTO feature_requests(
                        owner,id,title,description,agent_name,use_case,priority,source,
                        client_request_id,status,result,result_url,created_at,updated_at,resolved_at
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    tuple(
                        (
                            request.get("created_at")
                            if key == "updated_at" and not request.get("updated_at")
                            else ""
                            if key in {"result", "result_url"} and not request.get(key)
                            else request.get(key)
                        )
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
                            "result",
                            "result_url",
                            "created_at",
                            "updated_at",
                            "resolved_at",
                        )
                    ),
                )
            for agent in payload["agents"]:
                connection.execute(
                    """INSERT INTO agents(
                        owner,id,name,transport,active,created_at,last_seen_at
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    tuple(
                        agent[key]
                        for key in (
                            "owner",
                            "id",
                            "name",
                            "transport",
                            "active",
                            "created_at",
                            "last_seen_at",
                        )
                    ),
                )
            for message in payload["agent_messages"]:
                connection.execute(
                    """INSERT INTO agent_messages(
                        sequence,owner,id,sender_agent_id,sender_name,recipient_agent_id,kind,
                        subject,body,metadata,thread_id,reply_to,client_request_id,request_payload,
                        status,created_at,expires_at,delivered_at,read_at,acked_at
                    ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        message["sequence"],
                        message["owner"],
                        message["id"],
                        message["sender_agent_id"],
                        message["sender_name"],
                        message["recipient_agent_id"],
                        message["kind"],
                        message["subject"],
                        message["body"],
                        Jsonb(message["metadata"]),
                        message["thread_id"],
                        message["reply_to"],
                        message["client_request_id"],
                        Jsonb(message["request_payload"]),
                        message["status"],
                        message["created_at"],
                        message["expires_at"],
                        message["delivered_at"],
                        message["read_at"],
                        message["acked_at"],
                    ),
                )
            if payload["agent_messages"]:
                connection.execute(
                    "SELECT setval(pg_get_serial_sequence('agent_messages','sequence'),%s,true)",
                    (max(message["sequence"] for message in payload["agent_messages"]),),
                )
            for event in payload["change_events"]:
                connection.execute(
                    "INSERT INTO change_events(id,owner,event,payload) VALUES(%s,%s,%s,%s)",
                    (event["id"], event["owner"], event["event"], Jsonb(event["payload"])),
                )
            if payload["change_events"]:
                connection.execute(
                    "SELECT setval(pg_get_serial_sequence('change_events','id'),%s,true)",
                    (max(event["id"] for event in payload["change_events"]),),
                )
            _insert_rows(connection, "vault_secrets", VAULT_COLUMNS, payload["vault_secrets"])

            expected = summary(payload)
            actual = {
                table: connection.execute(
                    sql.SQL("SELECT count(*) AS count FROM {}").format(sql.Identifier(table))
                ).fetchone()["count"]
                for table in DESTINATION_TABLES
            }
            if actual != expected:
                raise RuntimeError(
                    f"Migration verification failed: expected {expected}, got {actual}"
                )
        return summary(payload)
    finally:
        database.close()
