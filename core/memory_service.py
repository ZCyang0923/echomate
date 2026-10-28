"""人物记忆的提取、编辑、来源检索和删除。"""

from __future__ import annotations

from typing import Iterable

from core.errors import MemoryError
from core.rag_service import RAGService
from core.vector_store import SearchHit
from database.repositories import Repository


def profile_to_memory_items(profile: dict) -> list[dict]:
    """把画像中的经历与事实转成可管理的记忆条目。"""
    items: list[dict] = []
    for entry in profile.get("shared_experiences", []) or []:
        if isinstance(entry, dict):
            summary = str(entry.get("summary") or "").strip()
            evidence = str(entry.get("evidence") or "").strip()
        else:
            summary = str(entry).strip()
            evidence = ""
        if summary:
            items.append(
                {
                    "kind": "共同经历",
                    "title": summary[:60],
                    "content": summary,
                    "evidence": evidence,
                    "confidence": 0.8 if evidence else 0.5,
                    "source_chunk_ids": [],
                }
            )
    for entry in profile.get("supported_facts", []) or []:
        if isinstance(entry, dict):
            fact = str(entry.get("fact") or "").strip()
            evidence = str(entry.get("evidence") or "").strip()
        else:
            fact = str(entry).strip()
            evidence = ""
        if fact:
            items.append(
                {
                    "kind": "事实",
                    "title": fact[:60],
                    "content": fact,
                    "evidence": evidence,
                    "confidence": 0.8 if evidence else 0.5,
                    "source_chunk_ids": [],
                }
            )
    # 去重，避免模型在不同批次重复同一条经历。
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["kind"], item["content"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


class MemoryService:
    def __init__(self, repository: Repository, rag_service: RAGService):
        self.repository = repository
        self.rag_service = rag_service

    def sync_from_profile(self, person_id: str, profile: dict) -> int:
        items = profile_to_memory_items(profile)
        return self.repository.replace_profile_memories(person_id, items)

    def list_memories(self, person_id: str) -> list[dict]:
        return self.repository.list_memories(person_id)

    def update_memory(
        self,
        person_id: str,
        memory_id: str,
        kind: str,
        title: str,
        content: str,
        evidence: str,
    ) -> dict:
        memory = self.repository.get_memory(memory_id)
        if not memory or memory["person_id"] != person_id:
            raise MemoryError("记忆不存在或不属于当前人物。")
        if not content.strip():
            raise MemoryError("记忆内容不能为空。")
        updated = self.repository.update_memory(
            memory_id=memory_id,
            kind=kind,
            title=title,
            content=content,
            evidence=evidence,
            confidence=float(memory.get("confidence", 0.5)),
        )
        if not updated:
            raise MemoryError("记忆更新失败。")
        return updated

    def delete_memory(self, person_id: str, memory_id: str) -> None:
        memory = self.repository.get_memory(memory_id)
        if not memory or memory["person_id"] != person_id:
            raise MemoryError("记忆不存在或不属于当前人物。")
        if not self.repository.delete_memory(memory_id):
            raise MemoryError("记忆删除失败。")

    def find_sources(
        self,
        person_id: str,
        memory: dict,
        top_k: int = 3,
    ) -> list[SearchHit]:
        query = f"{memory.get('title', '')}\n{memory.get('content', '')}".strip()
        if not query:
            return []
        return self.rag_service.search(person_id, query, top_k=top_k)

    def delete_all(self, person_id: str) -> None:
        with self.repository.db.session() as connection:
            connection.execute(
                "DELETE FROM memories WHERE person_id = ?", (person_id,)
            )


def memory_counts(memories: Iterable[dict]) -> dict:
    counts = {"共同经历": 0, "事实": 0, "其他": 0}
    for memory in memories:
        kind = memory.get("kind", "")
        counts[kind if kind in counts else "其他"] += 1
    return counts


__all__ = [
    "MemoryService",
    "memory_counts",
    "profile_to_memory_items",
]
