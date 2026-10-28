"""SQLite 数据访问层。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from uuid import uuid4

from core.errors import DuplicateImportError
from database.db import Database


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _loads_list(raw: Any) -> list:
    if not raw:
        return []
    try:
        value = json.loads(str(raw))
        return value if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


class Repository:
    """EchoMate 的业务数据仓储。"""

    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------------
    # 人物
    # ------------------------------------------------------------------
    def create_person(
        self,
        name: str,
        alias: str = "",
        description: str = "",
        target_sender: str = "",
    ) -> dict:
        cleaned_name = str(name).strip()
        if not cleaned_name:
            raise ValueError("人物昵称不能为空。")
        now = utc_now()
        person_id = new_id("person")
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO persons(
                    id, name, alias, target_sender, description, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    person_id,
                    cleaned_name,
                    str(alias).strip(),
                    str(target_sender).strip(),
                    str(description).strip(),
                    now,
                    now,
                ),
            )
        person = self.get_person(person_id)
        assert person is not None
        return person

    def get_person(self, person_id: str) -> Optional[dict]:
        return self.db.fetch_one(
            "SELECT * FROM persons WHERE id = ?",
            (person_id,),
        )

    def list_persons(self) -> list[dict]:
        rows = self.db.fetch_all(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM imported_messages m WHERE m.person_id = p.id)
                       AS message_count,
                   (SELECT COUNT(*) FROM memories mem WHERE mem.person_id = p.id)
                       AS memory_count,
                   (SELECT COUNT(*) FROM chat_sessions s WHERE s.person_id = p.id)
                       AS session_count,
                   CASE WHEN pr.person_id IS NULL THEN 0 ELSE 1 END AS has_profile
            FROM persons p
            LEFT JOIN profiles pr ON pr.person_id = p.id
            ORDER BY p.updated_at DESC, p.name ASC
            """
        )
        return rows

    def set_target_sender(self, person_id: str, sender: str) -> None:
        self.db.execute(
            "UPDATE persons SET target_sender = ?, updated_at = ? WHERE id = ?",
            (str(sender).strip(), utc_now(), person_id),
        )

    def update_person(
        self,
        person_id: str,
        name: str,
        alias: str = "",
        description: str = "",
    ) -> Optional[dict]:
        cleaned_name = str(name).strip()
        if not cleaned_name:
            raise ValueError("人物昵称不能为空。")
        count = self.db.execute(
            """
            UPDATE persons
            SET name = ?, alias = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cleaned_name,
                str(alias).strip(),
                str(description).strip(),
                utc_now(),
                person_id,
            ),
        )
        return self.get_person(person_id) if count else None

    def delete_person(self, person_id: str) -> bool:
        return bool(
            self.db.execute("DELETE FROM persons WHERE id = ?", (person_id,))
        )

    def person_stats(self, person_id: str) -> dict:
        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT
                  p.id, p.name,
                  (SELECT COUNT(*) FROM imported_messages WHERE person_id = p.id)
                    AS message_count,
                  (SELECT COUNT(*) FROM conversation_chunks WHERE person_id = p.id)
                    AS chunk_count,
                  (SELECT COUNT(*) FROM chat_sessions WHERE person_id = p.id)
                    AS session_count,
                  (SELECT COUNT(*) FROM chat_messages cm
                     JOIN chat_sessions cs ON cs.id = cm.session_id
                     WHERE cs.person_id = p.id) AS chat_message_count,
                  (SELECT COUNT(*) FROM memories WHERE person_id = p.id)
                    AS memory_count,
                  (SELECT MAX(imported_at) FROM import_batches WHERE person_id = p.id)
                    AS last_import_at,
                  (SELECT updated_at FROM profiles WHERE person_id = p.id)
                    AS profile_updated_at,
                  (SELECT source_message_count FROM profiles WHERE person_id = p.id)
                    AS profile_source_message_count
                FROM persons p
                WHERE p.id = ?
                """,
                (person_id,),
            ).fetchone()
        return dict(row) if row else {}

    def global_stats(self) -> dict:
        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM persons) AS person_count,
                  (SELECT COUNT(*) FROM imported_messages) AS message_count,
                  (SELECT COUNT(*) FROM memories) AS memory_count,
                  (SELECT COUNT(*) FROM chat_sessions) AS session_count,
                  (SELECT COUNT(*) FROM profiles) AS profile_count
                """
            ).fetchone()
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # 人物画像
    # ------------------------------------------------------------------
    def save_profile(
        self,
        person_id: str,
        profile: dict,
        provider: str = "",
        source_message_count: int = 0,
    ) -> dict:
        now = utc_now()
        with self.db.session() as connection:
            current = connection.execute(
                "SELECT version FROM profiles WHERE person_id = ?",
                (person_id,),
            ).fetchone()
            version = int(current["version"]) + 1 if current else 1
            connection.execute(
                """
                INSERT INTO profiles(
                    person_id, data_json, provider, source_message_count,
                    version, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(person_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    provider = excluded.provider,
                    source_message_count = excluded.source_message_count,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    person_id,
                    json.dumps(profile, ensure_ascii=False, indent=2),
                    provider,
                    int(source_message_count),
                    version,
                    now,
                ),
            )
            connection.execute(
                "UPDATE persons SET updated_at = ? WHERE id = ?",
                (now, person_id),
            )
        record = self.get_profile_record(person_id)
        assert record is not None
        return record

    def get_profile_record(self, person_id: str) -> Optional[dict]:
        row = self.db.fetch_one(
            "SELECT * FROM profiles WHERE person_id = ?",
            (person_id,),
        )
        if not row:
            return None
        try:
            data = json.loads(row["data_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            data = {}
        return {
            "person_id": row["person_id"],
            "data": data,
            "provider": row["provider"],
            "source_message_count": int(row["source_message_count"]),
            "version": int(row["version"]),
            "updated_at": row["updated_at"],
        }

    def get_profile(self, person_id: str) -> Optional[dict]:
        record = self.get_profile_record(person_id)
        return record["data"] if record else None

    def delete_profile(self, person_id: str) -> None:
        self.db.execute("DELETE FROM profiles WHERE person_id = ?", (person_id,))

    # ------------------------------------------------------------------
    # 聊天记录导入
    # ------------------------------------------------------------------
    def find_import_by_hash(self, person_id: str, file_hash: str) -> Optional[dict]:
        return self.db.fetch_one(
            """
            SELECT * FROM import_batches
            WHERE person_id = ? AND file_hash = ?
            """,
            (person_id, file_hash),
        )

    def create_import_batch(
        self,
        person_id: str,
        file_name: str,
        file_hash: str,
        message_count: int,
    ) -> dict:
        batch_id = new_id("batch")
        now = utc_now()
        try:
            with self.db.session() as connection:
                connection.execute(
                    """
                    INSERT INTO import_batches(
                        id, person_id, file_name, file_hash, message_count, imported_at
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        person_id,
                        file_name,
                        file_hash,
                        int(message_count),
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateImportError(
                "这个人物已经导入过内容完全相同的文件。"
            ) from exc
        batch = self.db.fetch_one(
            "SELECT * FROM import_batches WHERE id = ?",
            (batch_id,),
        )
        assert batch is not None
        return batch

    def create_import(
        self,
        person_id: str,
        file_name: str,
        file_hash: str,
        messages: Iterable[dict],
    ) -> dict:
        """原子地创建导入批次和消息记录。"""
        message_list = list(messages)
        batch_id = new_id("batch")
        now = utc_now()
        rows = []
        for message in message_list:
            rows.append(
                (
                    new_id("src"),
                    person_id,
                    batch_id,
                    int(message["message_index"]),
                    str(message.get("timestamp") or ""),
                    str(message["sender"]),
                    str(message["content"]),
                    1 if message.get("is_target") else 0,
                    now,
                )
            )
        try:
            with self.db.session() as connection:
                connection.execute(
                    """
                    INSERT INTO import_batches(
                        id, person_id, file_name, file_hash, message_count, imported_at
                    ) VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        person_id,
                        file_name,
                        file_hash,
                        len(rows),
                        now,
                    ),
                )
                if rows:
                    connection.executemany(
                        """
                        INSERT INTO imported_messages(
                            id, person_id, batch_id, message_index, timestamp,
                            sender, content, is_target, created_at
                        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                connection.execute(
                    "UPDATE persons SET updated_at = ? WHERE id = ?",
                    (now, person_id),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateImportError(
                "这个人物已经导入过内容完全相同的文件。"
            ) from exc
        batch = self.db.fetch_one(
            "SELECT * FROM import_batches WHERE id = ?",
            (batch_id,),
        )
        assert batch is not None
        return batch

    def insert_imported_messages(
        self,
        person_id: str,
        batch_id: str,
        messages: Iterable[dict],
    ) -> int:
        now = utc_now()
        rows = []
        for message in messages:
            rows.append(
                (
                    new_id("src"),
                    person_id,
                    batch_id,
                    int(message["message_index"]),
                    str(message.get("timestamp") or ""),
                    str(message["sender"]),
                    str(message["content"]),
                    1 if message.get("is_target") else 0,
                    now,
                )
            )
        if not rows:
            return 0
        with self.db.session() as connection:
            connection.executemany(
                """
                INSERT INTO imported_messages(
                    id, person_id, batch_id, message_index, timestamp,
                    sender, content, is_target, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def list_imported_messages(self, person_id: str) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT m.*
            FROM imported_messages m
            JOIN import_batches b ON b.id = m.batch_id
            WHERE m.person_id = ?
            ORDER BY b.imported_at ASC, m.message_index ASC, m.rowid ASC
            """,
            (person_id,),
        )

    def count_imported_messages(self, person_id: str) -> int:
        value = self.db.scalar(
            "SELECT COUNT(*) FROM imported_messages WHERE person_id = ?",
            (person_id,),
        )
        return int(value or 0)

    def count_target_messages(self, person_id: str) -> int:
        value = self.db.scalar(
            """
            SELECT COUNT(*) FROM imported_messages
            WHERE person_id = ? AND is_target = 1
            """,
            (person_id,),
        )
        return int(value or 0)

    def imported_sender_counts(self, person_id: str) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT sender, COUNT(*) AS message_count
            FROM imported_messages
            WHERE person_id = ?
            GROUP BY sender
            ORDER BY message_count DESC
            """,
            (person_id,),
        )

    def list_import_batches(self, person_id: str) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT * FROM import_batches
            WHERE person_id = ?
            ORDER BY imported_at DESC
            """,
            (person_id,),
        )

    def delete_import_batch(self, batch_id: str) -> None:
        self.db.execute("DELETE FROM import_batches WHERE id = ?", (batch_id,))

    # ------------------------------------------------------------------
    # 对话分块
    # ------------------------------------------------------------------
    def replace_chunks(self, person_id: str, chunks: Iterable[dict]) -> int:
        now = utc_now()
        rows = [
            (
                chunk["id"],
                person_id,
                chunk["text"],
                int(chunk["start_index"]),
                int(chunk["end_index"]),
                str(chunk.get("timestamp_start") or ""),
                str(chunk.get("timestamp_end") or ""),
                json.dumps(chunk.get("message_ids", []), ensure_ascii=False),
                now,
            )
            for chunk in chunks
        ]
        with self.db.session() as connection:
            connection.execute(
                "DELETE FROM conversation_chunks WHERE person_id = ?",
                (person_id,),
            )
            if rows:
                connection.executemany(
                    """
                    INSERT INTO conversation_chunks(
                        id, person_id, text, start_index, end_index,
                        timestamp_start, timestamp_end, message_ids_json, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        return len(rows)

    def list_chunks(self, person_id: str) -> list[dict]:
        rows = self.db.fetch_all(
            """
            SELECT * FROM conversation_chunks
            WHERE person_id = ?
            ORDER BY start_index ASC
            """,
            (person_id,),
        )
        for row in rows:
            row["message_ids"] = _loads_list(row.get("message_ids_json"))
        return rows

    def get_chunks_by_ids(self, chunk_ids: Iterable[str]) -> list[dict]:
        ids = list(dict.fromkeys(str(item) for item in chunk_ids if item))
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self.db.fetch_all(
            f"SELECT * FROM conversation_chunks WHERE id IN ({placeholders})",
            tuple(ids),
        )
        for row in rows:
            row["message_ids"] = _loads_list(row.get("message_ids_json"))
        return rows

    def count_chunks(self, person_id: str) -> int:
        value = self.db.scalar(
            "SELECT COUNT(*) FROM conversation_chunks WHERE person_id = ?",
            (person_id,),
        )
        return int(value or 0)

    def delete_chunks(self, person_id: str) -> None:
        self.db.execute(
            "DELETE FROM conversation_chunks WHERE person_id = ?",
            (person_id,),
        )

    # ------------------------------------------------------------------
    # 会话与聊天消息
    # ------------------------------------------------------------------
    def create_session(self, person_id: str, title: str = "新的对话") -> dict:
        session_id = new_id("session")
        now = utc_now()
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO chat_sessions(id, person_id, title, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (session_id, person_id, str(title).strip() or "新的对话", now, now),
            )
            connection.execute(
                "UPDATE persons SET updated_at = ? WHERE id = ?",
                (now, person_id),
            )
        session = self.get_session(session_id)
        assert session is not None
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.db.fetch_one(
            "SELECT * FROM chat_sessions WHERE id = ?",
            (session_id,),
        )

    def list_sessions(self, person_id: str) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT s.*,
                   (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id)
                       AS message_count
            FROM chat_sessions s
            WHERE s.person_id = ?
            ORDER BY s.updated_at DESC, s.created_at DESC
            """,
            (person_id,),
        )

    def latest_session(self, person_id: str) -> Optional[dict]:
        return self.db.fetch_one(
            """
            SELECT * FROM chat_sessions
            WHERE person_id = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (person_id,),
        )

    def update_session_title(self, session_id: str, title: str) -> None:
        self.db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (str(title).strip() or "新的对话", utc_now(), session_id),
        )

    def touch_session(self, session_id: str) -> None:
        self.db.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (utc_now(), session_id),
        )

    def delete_session(self, session_id: str) -> None:
        self.db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))

    def clear_session_messages(self, session_id: str) -> None:
        with self.db.session() as connection:
            connection.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (session_id,),
            )
            connection.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (utc_now(), session_id),
            )

    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[list[dict]] = None,
        is_mock: bool = False,
    ) -> dict:
        if role not in {"user", "assistant"}:
            raise ValueError("消息角色必须是 user 或 assistant。")
        message_id = new_id("msg")
        now = utc_now()
        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages(
                    id, session_id, role, content, sources_json, is_mock, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    str(content),
                    json.dumps(sources or [], ensure_ascii=False),
                    1 if is_mock else 0,
                    now,
                ),
            )
            connection.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        row = self.db.fetch_one(
            "SELECT * FROM chat_messages WHERE id = ?",
            (message_id,),
        )
        assert row is not None
        row["sources"] = _loads_list(row.get("sources_json"))
        return row

    def list_chat_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        if limit:
            rows = self.db.fetch_all(
                """
                SELECT * FROM (
                    SELECT *, rowid AS _seq FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY created_at DESC, rowid DESC
                    LIMIT ?
                ) ORDER BY created_at ASC, _seq ASC
                """,
                (session_id, int(limit)),
            )
        else:
            rows = self.db.fetch_all(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (session_id,),
            )
        for row in rows:
            row["sources"] = _loads_list(row.get("sources_json"))
        return rows

    def count_chat_messages(self, session_id: str) -> int:
        value = self.db.scalar(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
            (session_id,),
        )
        return int(value or 0)

    # ------------------------------------------------------------------
    # 记忆
    # ------------------------------------------------------------------
    def replace_profile_memories(
        self,
        person_id: str,
        memories: Iterable[dict],
    ) -> int:
        now = utc_now()
        rows = []
        for item in memories:
            rows.append(
                (
                    new_id("memory"),
                    person_id,
                    str(item.get("kind") or "事实"),
                    str(item.get("title") or "").strip()[:120],
                    str(item.get("content") or "").strip(),
                    str(item.get("evidence") or "").strip(),
                    "profile",
                    json.dumps(item.get("source_chunk_ids", []), ensure_ascii=False),
                    float(item.get("confidence", 0.5)),
                    now,
                    now,
                )
            )
        with self.db.session() as connection:
            connection.execute(
                "DELETE FROM memories WHERE person_id = ? AND source = 'profile'",
                (person_id,),
            )
            if rows:
                connection.executemany(
                    """
                    INSERT INTO memories(
                        id, person_id, kind, title, content, evidence, source,
                        source_chunk_ids_json, confidence, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
        return len(rows)

    def list_memories(self, person_id: str) -> list[dict]:
        rows = self.db.fetch_all(
            """
            SELECT * FROM memories
            WHERE person_id = ?
            ORDER BY
              CASE kind WHEN '共同经历' THEN 0 WHEN '事实' THEN 1 ELSE 2 END,
              updated_at DESC
            """,
            (person_id,),
        )
        for row in rows:
            row["source_chunk_ids"] = _loads_list(
                row.get("source_chunk_ids_json")
            )
        return rows

    def get_memory(self, memory_id: str) -> Optional[dict]:
        row = self.db.fetch_one(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,),
        )
        if not row:
            return None
        row["source_chunk_ids"] = _loads_list(row.get("source_chunk_ids_json"))
        return row

    def update_memory(
        self,
        memory_id: str,
        kind: str,
        title: str,
        content: str,
        evidence: str,
        confidence: float = 0.5,
    ) -> Optional[dict]:
        count = self.db.execute(
            """
            UPDATE memories
            SET kind = ?, title = ?, content = ?, evidence = ?,
                confidence = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(kind).strip() or "事实",
                str(title).strip()[:120],
                str(content).strip(),
                str(evidence).strip(),
                float(confidence),
                utc_now(),
                memory_id,
            ),
        )
        return self.get_memory(memory_id) if count else None

    def delete_memory(self, memory_id: str) -> bool:
        return bool(
            self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        )

    def count_memories(self, person_id: str) -> int:
        value = self.db.scalar(
            "SELECT COUNT(*) FROM memories WHERE person_id = ?",
            (person_id,),
        )
        return int(value or 0)

    # ------------------------------------------------------------------
    # 其他
    # ------------------------------------------------------------------
    def set_meta(self, key: str, value: str) -> None:
        self.db.execute(
            """
            INSERT INTO app_meta(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(key), str(value)),
        )

    def get_meta(self, key: str) -> Optional[str]:
        value = self.db.scalar(
            "SELECT value FROM app_meta WHERE key = ?",
            (str(key),),
        )
        return str(value) if value is not None else None
