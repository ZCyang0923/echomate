"""聊天记录导入编排：人物、消息、分块与向量索引。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from core.chat_parser import ParseResult, make_import_records
from core.errors import DuplicateImportError, IngestionError
from core.rag_service import IndexReport, RAGService
from database.repositories import Repository, utc_now


@dataclass
class ImportOutcome:
    person_id: str
    person_name: str
    message_count: int
    target_message_count: int
    batch_id: str
    index_report: Optional[IndexReport]
    index_error: str = ""


def compute_file_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def import_chat(
    repository: Repository,
    rag_service: RAGService,
    parsed: ParseResult,
    target_sender: str,
    person_id: Optional[str] = None,
    new_person_name: str = "",
    alias: str = "",
    description: str = "",
    file_name: str = "chat.txt",
    file_hash: str = "",
) -> ImportOutcome:
    """确认导入后写入消息并重建该人物的本地索引。

    导入失败时：若本次刚创建人物且没有任何消息写入，则清理空人物。
    """
    messages = parsed.messages
    if messages.empty:
        raise IngestionError("解析结果为空，无法导入。")
    senders = set(messages["sender"].astype(str).tolist())
    if target_sender not in senders:
        raise IngestionError("要模拟的人物不在当前解析出的发送者列表中。")

    target_count = int((messages["sender"] == target_sender).sum())
    if target_count == 0:
        raise IngestionError("目标人物没有任何消息，无法建立风格画像。")

    created_new = False
    if person_id:
        person = repository.get_person(person_id)
        if not person:
            raise IngestionError("选择的人物档案不存在，可能已被删除。")
        existing_target = str(person.get("target_sender") or "").strip()
        if existing_target and existing_target != target_sender:
            raise IngestionError(
                f"该人物档案已绑定聊天对象「{existing_target}」，"
                f"不能追加目标为「{target_sender}」的记录。请新建人物档案。"
            )
        if not existing_target:
            repository.set_target_sender(person_id, target_sender)
        person_name = person["name"]
    else:
        person_name = (new_person_name or target_sender).strip()
        if not person_name:
            raise IngestionError("新人物昵称不能为空。")
        person = repository.create_person(
            name=person_name,
            alias=alias or target_sender,
            description=description,
            target_sender=target_sender,
        )
        person_id = person["id"]
        created_new = True

    if not file_hash:
        raise IngestionError("缺少文件指纹，无法检查重复导入。")

    records = make_import_records(messages, target_sender)
    try:
        batch = repository.create_import(
            person_id=person_id,
            file_name=file_name,
            file_hash=file_hash,
            messages=records,
        )
    except Exception:
        if created_new:
            repository.delete_person(person_id)
        raise

    index_report: Optional[IndexReport] = None
    index_error = ""
    try:
        index_report = rag_service.index_person(person_id)
    except Exception as exc:
        # 索引失败不回滚原始消息；页面会提示使用“重建索引”。
        index_error = f"{type(exc).__name__}: {exc}"

    return ImportOutcome(
        person_id=person_id,
        person_name=person_name,
        message_count=len(records),
        target_message_count=target_count,
        batch_id=batch["id"],
        index_report=index_report,
        index_error=index_error,
    )


def profile_is_outdated(repository: Repository, person_id: str) -> bool:
    record = repository.get_profile_record(person_id)
    if not record:
        return False
    current_messages = repository.count_imported_messages(person_id)
    return int(record.get("source_message_count") or 0) != current_messages


def delete_person_completely(
    repository: Repository,
    rag_service: RAGService,
    person_id: str,
) -> None:
    """先删除向量索引，再删除 SQLite 人物（级联删除其余数据）。"""
    rag_service.vector_store.delete_person(person_id)
    if not repository.delete_person(person_id):
        raise IngestionError("人物不存在或已经被删除。")


def clear_person_content(
    repository: Repository,
    rag_service: RAGService,
    person_id: str,
) -> None:
    """清空一个人物的所有聊天数据、索引、画像和会话，保留人物本身。"""
    rag_service.vector_store.delete_person(person_id)
    with repository.db.session() as connection:
        connection.execute(
            "DELETE FROM imported_messages WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            "DELETE FROM import_batches WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            "DELETE FROM conversation_chunks WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            "DELETE FROM chat_sessions WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            "DELETE FROM memories WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            "DELETE FROM profiles WHERE person_id = ?", (person_id,)
        )
        connection.execute(
            """
            UPDATE persons
            SET target_sender = '', updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), person_id),
        )


__all__ = [
    "DuplicateImportError",
    "ImportOutcome",
    "clear_person_content",
    "compute_file_hash",
    "delete_person_completely",
    "import_chat",
    "profile_is_outdated",
]
