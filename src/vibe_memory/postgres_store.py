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

    def run_idempotent(
        self,
        owner,
        agent_id,
        operation,
        client_request_id,
        request_hash,
        callback,
    ):
        with self.transaction(), self._connection() as connection:
            lock_key = "\x1f".join((owner, agent_id, operation, client_request_id))
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                (lock_key,),
            )
            row = connection.execute(
                """SELECT request_hash,result FROM batch_operations
                WHERE owner=%s AND agent_id=%s AND operation=%s
                AND client_request_id=%s FOR UPDATE""",
                (owner, agent_id, operation, client_request_id),
            ).fetchone()
            if row:
                if row["request_hash"] != request_hash:
                    raise DuplicateRequestConflict()
                return row["result"], False
            result = callback()
            connection.execute(
                """INSERT INTO batch_operations(
                    owner,agent_id,operation,client_request_id,request_hash,result
                ) VALUES(%s,%s,%s,%s,%s,%s)""",
                (
                    owner,
                    agent_id,
                    operation,
                    client_request_id,
                    request_hash,
                    Jsonb(result),
                ),
            )
            return result, True

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
        result["creator_agent_id"] = result.get("creator_agent_id") or "unknown"
        result["creator_agent_name"] = result.get("creator_agent_name") or "Unknown agent"
        result["writer_history"] = result.get("writer_history") or []
        result.pop("owner", None)
        result.pop("archived_at", None)
        return result

    @staticmethod
    def _relation(row):
        result = dict(row)
        result.pop("owner", None)
        result["created_at"] = iso(result["created_at"])
        result["history"] = result.get("history") or []
        result["creator_agent_id"] = result.get("creator_agent_id") or "unknown"
        result["creator_agent_name"] = result.get("creator_agent_name") or "Unknown agent"
        result["evidence_record_ids"] = result.get("evidence_record_ids") or []
        result["evidence"] = result.get("evidence") or []
        result["evidence_coverage"] = result.get("evidence_coverage") or "unknown"
        result["input_manifest_id"] = result.get("input_manifest_id") or ""
        result["extraction_method"] = result.get("extraction_method") or ""
        result["extraction_version"] = result.get("extraction_version") or ""
        result["correction_scope"] = result.get("correction_scope") or "unknown"
        result["claim_group"] = f"{result['source_id']}:{result['target_id']}"
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

    def recent_events(self, owner, limit=20):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT id,event,payload FROM change_events
                WHERE owner=%s ORDER BY id DESC LIMIT %s""",
                (owner, limit),
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
    def _audit_log(row):
        result = dict(row)
        result.pop("owner", None)
        result.pop("request_payload", None)
        result["occurred_at"] = iso(result["occurred_at"])
        result["received_at"] = iso(result["received_at"])
        result["metadata"] = result.get("metadata") or {}
        return result

    def add_agent_audit_log(self, owner, agent_id, agent_name, transport, data):
        payload = data.model_dump(mode="json")
        received_at = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            if data.client_request_id:
                existing = connection.execute(
                    """SELECT * FROM agent_audit_logs WHERE owner=%s AND agent_id=%s
                    AND client_request_id=%s FOR UPDATE""",
                    (owner, agent_id, data.client_request_id),
                ).fetchone()
                if existing:
                    if existing["request_payload"] != payload:
                        raise DuplicateRequestConflict()
                    return self._audit_log(existing), False
            row = connection.execute(
                """INSERT INTO agent_audit_logs(
                    owner,id,agent_id,agent_name,transport,action,outcome,summary,
                    resource_type,resource_id,metadata,occurred_at,received_at,
                    client_request_id,request_payload
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *""",
                (
                    owner,
                    uid(),
                    agent_id,
                    agent_name,
                    transport,
                    data.action,
                    data.outcome,
                    data.summary,
                    data.resource_type,
                    data.resource_id,
                    Jsonb(data.metadata),
                    data.occurred_at or received_at,
                    received_at,
                    data.client_request_id,
                    Jsonb(payload),
                ),
            ).fetchone()
            self._event(
                owner,
                "agent_audit_log.created",
                {
                    "audit_log_id": row["id"],
                    "agent_id": agent_id,
                    "action": data.action,
                },
            )
        return self._audit_log(row), True

    def list_agent_audit_logs(
        self, owner, agent_id, limit=50, offset=0, allow_owner=False,
        filter_agent_id="", action="", outcome=""
    ):
        filters, parameters = ["owner=%s"], [owner]
        if not allow_owner:
            filters.append("agent_id=%s")
            parameters.append(agent_id)
        elif filter_agent_id:
            filters.append("agent_id=%s")
            parameters.append(filter_agent_id)
        if action:
            filters.append("action=%s")
            parameters.append(action)
        if outcome:
            filters.append("outcome=%s")
            parameters.append(outcome)
        parameters.extend((offset, limit))
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM agent_audit_logs WHERE {' AND '.join(filters)} "
                "ORDER BY sequence DESC OFFSET %s LIMIT %s",
                tuple(parameters),
            ).fetchall()
        return [self._audit_log(row) for row in rows]

    def get_agent_audit_log(self, owner, agent_id, id, allow_owner=False):
        with self._connection() as connection:
            row = connection.execute(
                """SELECT * FROM agent_audit_logs WHERE owner=%s AND id=%s
                AND (%s OR agent_id=%s)""",
                (owner, id, allow_owner, agent_id),
            ).fetchone()
        if not row:
            raise NotFound()
        return self._audit_log(row)

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
                    {parent["sender_agent_id"], parent["recipient_agent_id"]} if parent else set()
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
                        ranks[status],
                        stamp,
                        ranks[status],
                        stamp,
                        ranks[status],
                        stamp,
                        owner,
                        id,
                    ),
                )
        return self.get_message(owner, agent_id, id)

    @staticmethod
    def _room(row):
        result = dict(row)
        result.pop("owner", None)
        result.pop("request_payload", None)
        for field in ("created_at", "updated_at", "archived_at"):
            result[field] = iso(result[field]) if result.get(field) else None
        result["member_count"] = int(result.get("member_count") or 0)
        result["last_sequence"] = int(result.get("last_sequence") or 0)
        result["last_read_sequence"] = int(result.get("last_read_sequence") or 0)
        result["unread_count"] = int(result.get("unread_count") or 0)
        return result

    @staticmethod
    def _room_member(row):
        result = dict(row)
        result.pop("owner", None)
        for field in ("joined_at", "left_at"):
            result[field] = iso(result[field]) if result.get(field) else None
        result["last_read_sequence"] = int(result.get("last_read_sequence") or 0)
        return result

    @staticmethod
    def _room_message(row):
        result = dict(row)
        result.pop("owner", None)
        result.pop("request_payload", None)
        result["created_at"] = iso(result["created_at"])
        result["metadata"] = result.get("metadata") or {}
        result["reply_to"] = result.get("reply_to") or None
        result["client_request_id"] = result.get("client_request_id") or None
        return result

    @staticmethod
    def _room_query(allow_owner):
        membership = "TRUE" if allow_owner else "me.left_at IS NULL"
        return f"""SELECT r.*,
            (SELECT COUNT(*) FROM agent_room_members members
             WHERE members.owner=r.owner AND members.room_id=r.id
             AND members.left_at IS NULL) AS member_count,
            (SELECT COALESCE(MAX(messages.sequence),0) FROM agent_room_messages messages
             WHERE messages.owner=r.owner AND messages.room_id=r.id) AS last_sequence,
            COALESCE(me.last_read_sequence,0) AS last_read_sequence,
            (SELECT COUNT(*) FROM agent_room_messages unread
             WHERE unread.owner=r.owner AND unread.room_id=r.id
             AND unread.sequence>COALESCE(me.last_read_sequence,0)
             AND unread.sender_agent_id<>%s) AS unread_count
            FROM agent_rooms r
            LEFT JOIN agent_room_members me ON me.owner=r.owner AND me.room_id=r.id
                AND me.agent_id=%s
            WHERE r.owner=%s AND r.archived_at IS NULL AND {membership}"""

    def list_rooms(self, owner, agent_id, limit=50, offset=0, allow_owner=False):
        with self._connection() as connection:
            rows = connection.execute(
                self._room_query(allow_owner)
                + " ORDER BY r.updated_at DESC,r.id OFFSET %s LIMIT %s",
                (agent_id, agent_id, owner, offset, limit),
            ).fetchall()
        return [self._room(row) for row in rows]

    def get_room(self, owner, agent_id, id, allow_owner=False):
        with self._connection() as connection:
            row = connection.execute(
                self._room_query(allow_owner) + " AND r.id=%s",
                (agent_id, agent_id, owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            members = connection.execute(
                """SELECT owner,room_id,agent_id,agent_name,role,joined_at,
                last_read_sequence,left_at FROM agent_room_members
                WHERE owner=%s AND room_id=%s AND left_at IS NULL
                ORDER BY CASE role WHEN 'creator' THEN 0 ELSE 1 END,joined_at,agent_id""",
                (owner, id),
            ).fetchall()
        room = self._room(row)
        room["members"] = [self._room_member(member) for member in members]
        return room

    def create_room(self, owner, creator_agent_id, creator_name, data):
        payload = data.model_dump(mode="json")
        created = datetime.now(UTC)
        member_ids = list(dict.fromkeys([creator_agent_id, *data.member_agent_ids]))
        with self.transaction(), self._connection() as connection:
            if data.client_request_id:
                existing = connection.execute(
                    """SELECT * FROM agent_rooms WHERE owner=%s AND created_by_agent_id=%s
                    AND client_request_id=%s FOR UPDATE""",
                    (owner, creator_agent_id, data.client_request_id),
                ).fetchone()
                if existing:
                    if existing["request_payload"] != payload:
                        raise DuplicateRequestConflict()
                    return self.get_room(owner, creator_agent_id, existing["id"], True), False
            agents = connection.execute(
                """SELECT id,name FROM agents WHERE owner=%s AND active AND id=ANY(%s)""",
                (owner, member_ids),
            ).fetchall()
            by_id = {agent["id"]: agent for agent in agents}
            if set(by_id) != set(member_ids):
                raise NotFound()
            room_id = uid()
            connection.execute(
                """INSERT INTO agent_rooms(owner,id,name,description,created_by_agent_id,
                created_by_name,client_request_id,request_payload,created_at,updated_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    owner,
                    room_id,
                    data.name,
                    data.description,
                    creator_agent_id,
                    creator_name,
                    data.client_request_id,
                    Jsonb(payload),
                    created,
                    created,
                ),
            )
            for member_id in member_ids:
                connection.execute(
                    """INSERT INTO agent_room_members(owner,room_id,agent_id,agent_name,role,
                    joined_at) VALUES(%s,%s,%s,%s,%s,%s)""",
                    (
                        owner,
                        room_id,
                        member_id,
                        by_id[member_id]["name"],
                        "creator" if member_id == creator_agent_id else "member",
                        created,
                    ),
                )
        return self.get_room(owner, creator_agent_id, room_id, True), True

    def update_room(self, owner, actor_agent_id, id, data, allow_owner=False):
        stamp = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            room = connection.execute(
                "SELECT * FROM agent_rooms WHERE owner=%s AND id=%s AND archived_at IS NULL FOR UPDATE",
                (owner, id),
            ).fetchone()
            if not room or not (allow_owner or room["created_by_agent_id"] == actor_agent_id):
                raise NotFound()
            fields, values = [], []
            if "name" in data.model_fields_set:
                fields.append("name=%s")
                values.append(data.name)
            if "description" in data.model_fields_set:
                fields.append("description=%s")
                values.append(data.description)
            values.extend([stamp, owner, id])
            connection.execute(
                f"UPDATE agent_rooms SET {','.join(fields)},updated_at=%s WHERE owner=%s AND id=%s",
                tuple(values),
            )
        return self.get_room(owner, actor_agent_id, id, allow_owner)

    def add_room_members(self, owner, actor_agent_id, id, agent_ids, allow_owner=False):
        stamp = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            room = connection.execute(
                "SELECT * FROM agent_rooms WHERE owner=%s AND id=%s AND archived_at IS NULL FOR UPDATE",
                (owner, id),
            ).fetchone()
            if not room or not (allow_owner or room["created_by_agent_id"] == actor_agent_id):
                raise NotFound()
            agents = connection.execute(
                "SELECT id,name FROM agents WHERE owner=%s AND active AND id=ANY(%s)",
                (owner, agent_ids),
            ).fetchall()
            if {agent["id"] for agent in agents} != set(agent_ids):
                raise NotFound()
            for agent in agents:
                connection.execute(
                    """INSERT INTO agent_room_members(owner,room_id,agent_id,agent_name,role,joined_at)
                    VALUES(%s,%s,%s,%s,'member',%s)
                    ON CONFLICT(owner,room_id,agent_id) DO UPDATE SET
                    agent_name=EXCLUDED.agent_name,left_at=NULL,joined_at=EXCLUDED.joined_at""",
                    (owner, id, agent["id"], agent["name"], stamp),
                )
            connection.execute(
                "UPDATE agent_rooms SET updated_at=%s WHERE owner=%s AND id=%s",
                (stamp, owner, id),
            )
        return self.get_room(owner, actor_agent_id, id, allow_owner)

    def remove_room_member(self, owner, actor_agent_id, id, agent_id, allow_owner=False):
        stamp = datetime.now(UTC)
        self_leaving = False
        with self.transaction(), self._connection() as connection:
            room = connection.execute(
                "SELECT * FROM agent_rooms WHERE owner=%s AND id=%s AND archived_at IS NULL FOR UPDATE",
                (owner, id),
            ).fetchone()
            if not room or agent_id == room["created_by_agent_id"]:
                raise NotFound()
            if not (
                allow_owner
                or room["created_by_agent_id"] == actor_agent_id
                or actor_agent_id == agent_id
            ):
                raise NotFound()
            self_leaving = actor_agent_id == agent_id and not allow_owner
            changed = connection.execute(
                """UPDATE agent_room_members SET left_at=%s WHERE owner=%s AND room_id=%s
                AND agent_id=%s AND left_at IS NULL""",
                (stamp, owner, id, agent_id),
            ).rowcount
            if not changed:
                raise NotFound()
            connection.execute(
                "UPDATE agent_rooms SET updated_at=%s WHERE owner=%s AND id=%s",
                (stamp, owner, id),
            )
        if self_leaving:
            return {"id": id, "left": True}
        return self.get_room(owner, actor_agent_id, id, allow_owner)

    def send_room_message(
        self, owner, sender_agent_id, sender_name, room_id, data, allow_owner=False
    ):
        payload = data.model_dump(mode="json")
        created = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            room = connection.execute(
                "SELECT * FROM agent_rooms WHERE owner=%s AND id=%s AND archived_at IS NULL FOR UPDATE",
                (owner, room_id),
            ).fetchone()
            member = connection.execute(
                """SELECT * FROM agent_room_members WHERE owner=%s AND room_id=%s
                AND agent_id=%s AND left_at IS NULL""",
                (owner, room_id, sender_agent_id),
            ).fetchone()
            if not room or (not member and not allow_owner):
                raise NotFound()
            if not member:
                connection.execute(
                    """INSERT INTO agent_room_members(owner,room_id,agent_id,agent_name,role,joined_at)
                    VALUES(%s,%s,%s,%s,'member',%s)
                    ON CONFLICT(owner,room_id,agent_id) DO UPDATE SET
                    agent_name=EXCLUDED.agent_name,left_at=NULL,joined_at=EXCLUDED.joined_at""",
                    (owner, room_id, sender_agent_id, sender_name, created),
                )
            if data.client_request_id:
                existing = connection.execute(
                    """SELECT * FROM agent_room_messages WHERE owner=%s AND sender_agent_id=%s
                    AND client_request_id=%s FOR UPDATE""",
                    (owner, sender_agent_id, data.client_request_id),
                ).fetchone()
                if existing:
                    if existing["request_payload"] != payload:
                        raise DuplicateRequestConflict()
                    return self._room_message(existing), False
            if data.reply_to:
                parent = connection.execute(
                    "SELECT 1 FROM agent_room_messages WHERE owner=%s AND room_id=%s AND id=%s",
                    (owner, room_id, data.reply_to),
                ).fetchone()
                if not parent:
                    raise NotFound()
            message_id = uid()
            row = connection.execute(
                """INSERT INTO agent_room_messages(owner,id,room_id,sender_agent_id,
                sender_name,body,metadata,reply_to,client_request_id,request_payload,created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (
                    owner,
                    message_id,
                    room_id,
                    sender_agent_id,
                    sender_name,
                    data.body,
                    Jsonb(data.metadata),
                    data.reply_to,
                    data.client_request_id,
                    Jsonb(payload),
                    created,
                ),
            ).fetchone()
            connection.execute(
                "UPDATE agent_rooms SET updated_at=%s WHERE owner=%s AND id=%s",
                (created, owner, room_id),
            )
            connection.execute(
                """UPDATE agent_room_members SET last_read_sequence=GREATEST(last_read_sequence,%s)
                WHERE owner=%s AND room_id=%s AND agent_id=%s""",
                (row["sequence"], owner, room_id, sender_agent_id),
            )
        return self._room_message(row), True

    def room_messages(
        self, owner, agent_id, room_id, after=0, limit=100, allow_owner=False, before=None
    ):
        self.get_room(owner, agent_id, room_id, allow_owner)
        with self._connection() as connection:
            if before is None:
                rows = connection.execute(
                    """SELECT * FROM agent_room_messages WHERE owner=%s AND room_id=%s
                    AND sequence>%s ORDER BY sequence LIMIT %s""",
                    (owner, room_id, after, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM agent_room_messages WHERE owner=%s AND room_id=%s
                    AND sequence<%s ORDER BY sequence DESC LIMIT %s""",
                    (owner, room_id, before, limit),
                ).fetchall()[::-1]
        return [self._room_message(row) for row in rows]

    def accessible_room_messages(self, owner, agent_id, after=0, limit=100, allow_owner=False):
        membership = "TRUE" if allow_owner else "member.left_at IS NULL"
        with self._connection() as connection:
            rows = connection.execute(
                f"""SELECT DISTINCT messages.* FROM agent_room_messages messages
                JOIN agent_rooms room ON room.owner=messages.owner AND room.id=messages.room_id
                LEFT JOIN agent_room_members member ON member.owner=messages.owner
                    AND member.room_id=messages.room_id AND member.agent_id=%s
                WHERE messages.owner=%s AND room.archived_at IS NULL
                AND messages.sequence>%s AND {membership}
                ORDER BY messages.sequence LIMIT %s""",
                (agent_id, owner, after, limit),
            ).fetchall()
        return [self._room_message(row) for row in rows]

    def mark_room_read(self, owner, agent_id, agent_name, room_id, sequence, allow_owner=False):
        stamp = datetime.now(UTC)
        with self.transaction(), self._connection() as connection:
            room = connection.execute(
                "SELECT 1 FROM agent_rooms WHERE owner=%s AND id=%s AND archived_at IS NULL",
                (owner, room_id),
            ).fetchone()
            member = connection.execute(
                """SELECT 1 FROM agent_room_members WHERE owner=%s AND room_id=%s
                AND agent_id=%s AND left_at IS NULL""",
                (owner, room_id, agent_id),
            ).fetchone()
            if not room or (not member and not allow_owner):
                raise NotFound()
            maximum = connection.execute(
                "SELECT COALESCE(MAX(sequence),0) AS value FROM agent_room_messages WHERE owner=%s AND room_id=%s",
                (owner, room_id),
            ).fetchone()["value"]
            target = min(sequence, maximum)
            connection.execute(
                """INSERT INTO agent_room_members(owner,room_id,agent_id,agent_name,role,
                joined_at,last_read_sequence) VALUES(%s,%s,%s,%s,'member',%s,%s)
                ON CONFLICT(owner,room_id,agent_id) DO UPDATE SET
                agent_name=EXCLUDED.agent_name,left_at=NULL,
                last_read_sequence=GREATEST(agent_room_members.last_read_sequence,EXCLUDED.last_read_sequence)""",
                (owner, room_id, agent_id, agent_name, stamp, target),
            )
        return self.get_room(owner, agent_id, room_id, allow_owner)

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
        creator_agent_id="unknown",
        creator_agent_name="Unknown agent",
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
                    security_history,creator_agent_id,creator_agent_name,writer_history
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
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
                    creator_agent_id,
                    creator_agent_name,
                    Jsonb(
                        [
                            {
                                "at": created,
                                "version": 1,
                                "operation": "created",
                                "writer_agent_id": creator_agent_id,
                                "writer_agent_name": creator_agent_name,
                            }
                        ]
                    ),
                ),
            )
            self._index(owner, record_id, keywords, vectors)
            self._event(owner, kind + ".created", {"record_id": record_id, "kind": kind})
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

    def update_keywords(
        self,
        owner,
        id,
        keywords,
        vectors,
        writer_agent_id="unknown",
        writer_agent_name="Unknown agent",
    ):
        if len(vectors) != len(keywords):
            raise ValueError("Embedding count does not match keyword count")
        with self.transaction(), self._connection() as connection:
            record = self.get(owner, id)
            connection.execute(
                "DELETE FROM keyword_embeddings WHERE owner=%s AND record_id=%s", (owner, id)
            )
            history = [
                *record.get("writer_history", []),
                {
                    "at": now(),
                    "version": record["version"] + 1,
                    "operation": "keywords_updated",
                    "writer_agent_id": writer_agent_id,
                    "writer_agent_name": writer_agent_name,
                },
            ]
            connection.execute(
                "UPDATE records SET keywords=%s,writer_history=%s,version=version+1 WHERE owner=%s AND id=%s",
                (keywords, Jsonb(history), owner, id),
            )
            self._index(owner, id, keywords, vectors)
            self._event(
                owner,
                record["kind"] + ".updated",
                {"record_id": id, "kind": record["kind"], "change": "keywords"},
            )
        return self.get(owner, id)

    def update_record(
        self,
        owner,
        id,
        data,
        vectors=None,
        writer_agent_id="unknown",
        writer_agent_name="Unknown agent",
    ):
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
            security = reassess_record_security(previous, title, content, row["version"] + 1)
            security_changed = (
                security["security_state"] != previous["security_state"]
                or security["trust_level"] != previous["trust_level"]
                or security["security_warnings"] != previous["security_warnings"]
            )
            writer_history = [
                *previous.get("writer_history", []),
                {
                    "at": now(),
                    "version": row["version"] + 1,
                    "operation": "record_updated",
                    "writer_agent_id": writer_agent_id,
                    "writer_agent_name": writer_agent_name,
                },
            ]
            connection.execute(
                """UPDATE records SET
                content=COALESCE(%s,content),title=COALESCE(%s,title),
                subtype=COALESCE(%s,subtype),source=COALESCE(%s,source),
                tags=COALESCE(%s::text[],tags),keywords=COALESCE(%s::text[],keywords),
                metadata=COALESCE(%s,metadata),trust_level=%s,security_state=%s,
                provenance=%s,content_hash=%s,security_warnings=%s,
                security_history=%s,writer_history=%s,version=version+1
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
                    Jsonb(writer_history),
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

    def update_security(
        self, owner, id, data, writer_agent_id="unknown", writer_agent_name="Unknown agent"
    ):
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
            writer_history = [
                *record.get("writer_history", []),
                {
                    "at": now(),
                    "version": row["version"] + 1,
                    "operation": "security_updated",
                    "writer_agent_id": writer_agent_id,
                    "writer_agent_name": writer_agent_name,
                },
            ]
            connection.execute(
                """UPDATE records SET trust_level=%s,security_state=%s,provenance=%s,
                content_hash=%s,security_warnings=%s,security_history=%s,
                writer_history=%s,version=version+1
                WHERE owner=%s AND id=%s""",
                (
                    security["trust_level"],
                    security["security_state"],
                    Jsonb(security["provenance"]),
                    security["content_hash"],
                    security["security_warnings"],
                    Jsonb(security["security_history"]),
                    Jsonb(writer_history),
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
            if any(records[id]["version"] != data.expected_versions[id] for id in ids):
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

    def link(
        self,
        owner,
        data,
        creator_agent_id="unknown",
        creator_agent_name="Unknown agent",
    ):
        with self.transaction(), self._connection() as connection:
            self.get(owner, data.source_id)
            self.get(owner, data.target_id)
            for evidence_id in data.evidence_record_ids:
                self.get(owner, evidence_id)
            for reference in data.evidence:
                current = self.get(owner, reference.record_id)
                if reference.version > current["version"]:
                    raise ValueError("evidence version is newer than the current record")
                if (
                    reference.version == current["version"]
                    and reference.content_hash != current["content_hash"]
                ):
                    raise ValueError("evidence content_hash does not match the record version")
            if data.input_manifest_id:
                manifest = self.get(owner, data.input_manifest_id)
                if manifest["kind"] not in {"memory", "document", "entity"}:
                    raise ValueError("input_manifest_id must reference a normal memory record")
            if data.source_id == data.target_id:
                raise ValueError("A relationship must connect two distinct records")
            id, created = uid(), now()
            history = [
                dict(
                    status="active",
                    reason=data.reason,
                    at=created,
                    version=1,
                    creator_agent_id=creator_agent_id,
                    confidence=data.confidence,
                )
            ]
            connection.execute(
                """INSERT INTO relations(
                    owner,id,source_id,target_id,relation,reason,status,version,created_at,history,
                    creator_agent_id,creator_agent_name,confidence,evidence_record_ids,
                    evidence,evidence_coverage,input_manifest_id,extraction_method,extraction_version
                    ,correction_scope
                ) VALUES(%s,%s,%s,%s,%s,%s,'active',1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    owner,
                    id,
                    data.source_id,
                    data.target_id,
                    data.relation,
                    data.reason,
                    created,
                    Jsonb(history),
                    creator_agent_id,
                    creator_agent_name,
                    data.confidence,
                    data.evidence_record_ids,
                    Jsonb([reference.model_dump(mode="json") for reference in data.evidence]),
                    data.evidence_coverage,
                    data.input_manifest_id,
                    data.extraction_method,
                    data.extraction_version,
                    data.correction_scope,
                ),
            )
            self._event(
                owner,
                "relation.created",
                {
                    "relation_id": id,
                    "source_id": data.source_id,
                    "target_id": data.target_id,
                    "creator_agent_id": creator_agent_id,
                    "confidence": data.confidence,
                    "version": 1,
                },
            )
        return self.relation_get(owner, id)

    def relation_get(self, owner, id):
        with self._connection() as connection:
            row = connection.execute(
                """SELECT e.source_id,e.target_id,e.id,e.relation,e.reason,e.status,
                e.version,e.created_at,e.history,e.creator_agent_id,e.creator_agent_name,
                e.confidence,e.evidence_record_ids,e.evidence,e.evidence_coverage,
                e.input_manifest_id,e.extraction_method,e.extraction_version
                ,e.correction_scope
                FROM relations e
                JOIN records a ON a.owner=e.owner AND a.id=e.source_id
                JOIN records b ON b.owner=e.owner AND b.id=e.target_id
                WHERE e.owner=%s AND e.id=%s
                AND a.archived_at IS NULL AND b.archived_at IS NULL""",
                (owner, id),
            ).fetchone()
        if not row:
            raise NotFound()
        result = self._relation(row)
        self._attach_evidence_status(owner, [result])
        result["parallel_claim_ids"] = [
            edge["id"]
            for edge in self.relations(
                owner,
                "all",
                source_id=result["source_id"],
                target_id=result["target_id"],
            )
            if edge["id"] != id
        ]
        return result

    def _attach_evidence_status(self, owner, edges):
        evidence_ids = list(
            dict.fromkeys(
                reference["record_id"] for edge in edges for reference in edge.get("evidence", [])
            )
        )
        current = {}
        if evidence_ids:
            with self._connection() as connection:
                rows = connection.execute(
                    """SELECT id,version,content_hash,archived_at FROM records
                    WHERE owner=%s AND id=ANY(%s)""",
                    (owner, evidence_ids),
                ).fetchall()
            current = {row["id"]: row for row in rows}
        for edge in edges:
            statuses = []
            for reference in edge.get("evidence", []):
                record = current.get(reference["record_id"])
                lifecycle = (
                    "deleted"
                    if record is None
                    else "archived"
                    if record.get("archived_at")
                    else "active"
                )
                same = bool(
                    record
                    and record["version"] == reference["version"]
                    and record.get("content_hash") == reference["content_hash"]
                )
                statuses.append(
                    {
                        "record_id": reference["record_id"],
                        "observed_version": reference["version"],
                        "observed_content_hash": reference["content_hash"],
                        "current_version": record["version"] if record else None,
                        "current_content_hash": record.get("content_hash") if record else None,
                        "lifecycle": lifecycle,
                        "comparison": "current" if same else "changed" if record else "unavailable",
                    }
                )
            edge["evidence_status"] = statuses
        return edges

    def relations(
        self,
        owner,
        status="active",
        creator_agent_id="",
        min_confidence=None,
        extraction_method="",
        relation="",
        source_id="",
        target_id="",
        limit=None,
        cursor=0,
    ):
        page = "" if limit is None else " LIMIT %s OFFSET %s"
        parameters = [
            owner,
            status,
            status,
            creator_agent_id,
            creator_agent_id,
            min_confidence,
            min_confidence,
            extraction_method,
            extraction_method,
            relation,
            relation,
            source_id,
            source_id,
            target_id,
            target_id,
        ]
        if limit is not None:
            parameters.extend((limit, cursor))
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT e.source_id,e.target_id,e.id,e.relation,e.reason,e.status,
                e.version,e.created_at,e.history,e.creator_agent_id,e.creator_agent_name,
                e.confidence,e.evidence_record_ids,e.evidence,e.evidence_coverage,
                e.input_manifest_id,e.extraction_method,e.extraction_version
                ,e.correction_scope
                FROM relations e
                JOIN records a ON a.owner=e.owner AND a.id=e.source_id
                JOIN records b ON b.owner=e.owner AND b.id=e.target_id
                WHERE e.owner=%s AND a.archived_at IS NULL AND b.archived_at IS NULL
                AND (%s='all' OR e.status=%s)
                AND (%s='' OR e.creator_agent_id=%s)
                AND (%s::double precision IS NULL OR e.confidence >= %s)
                AND (%s='' OR e.extraction_method=%s)
                AND (%s='' OR e.relation=%s)
                AND (%s='' OR e.source_id=%s)
                AND (%s='' OR e.target_id=%s)
                ORDER BY e.created_at,e.id"""
                + page,
                parameters,
            ).fetchall()
        result = self._attach_evidence_status(owner, [self._relation(row) for row in rows])
        groups = {}
        for edge in result:
            groups.setdefault(edge["claim_group"], []).append(edge["id"])
        for edge in result:
            edge["parallel_claim_ids"] = [
                claim_id for claim_id in groups[edge["claim_group"]] if claim_id != edge["id"]
            ]
        return result

    def correction_relations(self, owner, record_ids, limit=None):
        page = "" if limit is None else " LIMIT %s"
        parameters = [owner, list(record_ids), list(record_ids)]
        if limit is not None:
            parameters.append(limit)
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT e.*,a.archived_at AS source_archived_at,
                b.archived_at AS target_archived_at
                FROM relations e
                JOIN records a ON a.owner=e.owner AND a.id=e.source_id
                JOIN records b ON b.owner=e.owner AND b.id=e.target_id
                WHERE e.owner=%s AND e.relation IN ('SUPERSEDES','CORRECTS')
                AND (e.source_id=ANY(%s) OR e.target_id=ANY(%s))
                ORDER BY e.created_at,e.id"""
                + page,
                parameters,
            ).fetchall()
        result = []
        for row in rows:
            edge = self._relation(row)
            edge["source_lifecycle"] = (
                "archived" if edge.pop("source_archived_at", None) else "active"
            )
            edge["target_lifecycle"] = (
                "archived" if edge.pop("target_archived_at", None) else "active"
            )
            result.append(edge)
        return result

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
            next_status = data.status or edge["status"]
            next_scope = data.correction_scope or edge["correction_scope"]
            if edge["status"] == next_status and edge["correction_scope"] == next_scope:
                return edge
            version = edge["version"] + 1
            history = edge["history"] + [
                dict(
                    status=next_status,
                    correction_scope=next_scope,
                    reason=data.reason,
                    at=now(),
                    version=version,
                )
            ]
            connection.execute(
                """UPDATE relations SET status=%s,correction_scope=%s,reason=%s,version=%s,history=%s
                WHERE owner=%s AND id=%s""",
                (next_status, next_scope, data.reason, version, Jsonb(history), owner, id),
            )
            self._event(
                owner,
                "relation.updated",
                {
                    "relation_id": id,
                    "source_id": edge["source_id"],
                    "target_id": edge["target_id"],
                    "version": version,
                    "correction_scope": next_scope,
                },
            )
            return {
                **edge,
                "status": next_status,
                "correction_scope": next_scope,
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
        creator_agent_id="",
        min_confidence=None,
        extraction_method="",
        relation="",
    ):
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
        result["updated_at"] = iso(result.get("updated_at") or result["created_at"])
        result["resolved_at"] = (
            iso(result.get("resolved_at")) if result.get("resolved_at") else None
        )
        result["result"] = result.get("result") or ""
        result["result_url"] = result.get("result_url") or ""
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

    def admin_feature_requests(self, status="", limit=50, offset=0):
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT * FROM feature_requests WHERE (%s='' OR status=%s)
                ORDER BY updated_at DESC,created_at DESC,id OFFSET %s LIMIT %s""",
                (status, status, offset, limit),
            ).fetchall()
        items = []
        for row in rows:
            record = self._feature(row)
            record["owner_id"] = row["owner"]
            items.append(record)
        return items

    def feature_request_status_counts(self):
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT status,count(*) AS count FROM feature_requests GROUP BY status"
            ).fetchall()
        return {row["status"]: row["count"] for row in rows}

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
                "result": "",
                "result_url": "",
                "created_at": now(),
            }
            record["updated_at"] = record["created_at"]
            record["resolved_at"] = None
            connection.execute(
                """INSERT INTO feature_requests(
                    owner,id,title,description,agent_name,use_case,priority,source,
                    client_request_id,status,result,result_url,created_at,updated_at,resolved_at
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
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
                        "result",
                        "result_url",
                        "created_at",
                        "updated_at",
                        "resolved_at",
                    )
                ),
            )
        return self.get_feature_request(owner, record["id"]), True

    def update_feature_request(self, owner, id, data):
        with self.transaction(), self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM feature_requests WHERE owner=%s AND id=%s FOR UPDATE",
                (owner, id),
            ).fetchone()
            if not row:
                raise NotFound()
            current = self._feature(row)
            changes = data.model_dump(exclude_unset=True)
            status = changes.get("status", current["status"])
            updated_at = now()
            if status in {"completed", "declined"}:
                resolved_at = current.get("resolved_at") or updated_at
            else:
                resolved_at = None
            result = changes.get("result", current["result"])
            result_url = changes.get("result_url", current["result_url"])
            title = changes.get("title", current["title"])
            description = changes.get("description", current["description"])
            use_case = changes.get("use_case", current["use_case"])
            priority = changes.get("priority", current["priority"])
            connection.execute(
                """UPDATE feature_requests SET title=%s,description=%s,use_case=%s,
                priority=%s,status=%s,result=%s,result_url=%s,updated_at=%s,
                resolved_at=%s WHERE owner=%s AND id=%s""",
                (
                    title,
                    description,
                    use_case,
                    priority,
                    status,
                    result,
                    result_url,
                    updated_at,
                    resolved_at,
                    owner,
                    id,
                ),
            )
            self._event(
                owner,
                "feature_request.updated",
                {"feature_request_id": id, "status": status, "updated_at": updated_at},
            )
        return self.get_feature_request(owner, id)

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
                    + octet_length(creator_agent_id) + octet_length(creator_agent_name)
                    + octet_length(writer_history::text)
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
                    + octet_length(history::text) + octet_length(creator_agent_id)
                    + octet_length(creator_agent_name)
                    + octet_length(COALESCE(confidence::text,''))
                    + octet_length(to_jsonb(evidence_record_ids)::text)
                    + octet_length(evidence::text) + octet_length(evidence_coverage)
                    + octet_length(COALESCE(input_manifest_id,''))
                    + octet_length(extraction_method) + octet_length(extraction_version)
                    + octet_length(correction_scope)
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
