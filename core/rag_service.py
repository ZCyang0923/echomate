"""对话分块、向量索引与历史片段检索。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional
from uuid import uuid4

from core.config import Settings
from core.embedding_service import EmbeddingService
from core.vector_store import SearchHit, VectorStoreService
from database.repositories import Repository


@dataclass
class IndexReport:
    person_id: str
    chunk_count: int
    vector_count: int
    message_count: int


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[一-鿿]")


def _lexical_tokens(text: str) -> set[str]:
    """生成轻量中文 2-gram 与拉丁词，用于哈希向量的词面补充。"""
    compact = re.sub(r"\s+", "", str(text or "").lower())
    if not compact:
        return set()
    tokens = set(_TOKEN_RE.findall(compact))
    for size in (2, 3):
        if len(compact) >= size:
            for index in range(len(compact) - size + 1):
                tokens.add(compact[index : index + size])
    return tokens


def _lexical_similarity(query: str, document: str) -> float:
    query_tokens = _lexical_tokens(query)
    if not query_tokens:
        return 0.0
    document_tokens = _lexical_tokens(document)
    if not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)


def build_conversation_chunks(
    person_id: str,
    messages: list[dict],
    chunk_size: int = 8,
    overlap: int = 2,
) -> list[dict]:
    """把连续消息切成带元数据的对话窗口。"""
    if not messages or chunk_size < 2:
        return []
    chunk_size = max(2, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size - 1))
    step = max(1, chunk_size - overlap)
    chunks: list[dict] = []
    total = len(messages)

    for start in range(0, total, step):
        window = messages[start : start + chunk_size]
        if not window:
            continue
        lines = []
        for message in window:
            sender = str(message.get("sender") or "")
            marker = "（模拟对象）" if message.get("is_target") else ""
            timestamp = str(message.get("timestamp") or "")
            prefix = f"[{timestamp}] " if timestamp else ""
            content = str(message.get("content") or "")
            lines.append(f"{prefix}{sender}{marker}: {content}")
        text = "\n".join(lines).strip()
        if not text:
            continue
        first = window[0]
        last = window[-1]
        chunks.append(
            {
                "id": f"chunk_{uuid4().hex}",
                "person_id": person_id,
                "text": text,
                "start_index": start + 1,
                "end_index": start + len(window),
                "timestamp_start": str(first.get("timestamp") or ""),
                "timestamp_end": str(last.get("timestamp") or ""),
                "message_ids": [str(message.get("id")) for message in window],
            }
        )
        if start + chunk_size >= total:
            break
    return chunks


class RAGService:
    """本地 RAG：使用本地 Embedding + Chroma/SQLite 向量存储。"""

    def __init__(
        self,
        repository: Repository,
        embedding: EmbeddingService,
        vector_store: VectorStoreService,
        settings: Settings,
    ):
        self.repository = repository
        self.embedding = embedding
        self.vector_store = vector_store
        self.settings = settings

    def index_person(self, person_id: str, batch_size: int = 64) -> IndexReport:
        messages = self.repository.list_imported_messages(person_id)
        chunks = build_conversation_chunks(
            person_id,
            messages,
            chunk_size=self.settings.chunk_size_messages,
            overlap=self.settings.chunk_overlap_messages,
        )
        if not chunks:
            self.repository.replace_chunks(person_id, [])
            self.vector_store.delete_person(person_id)
            return IndexReport(person_id, 0, 0, len(messages))

        # 先计算全部向量，再替换旧索引，避免失败时留下半套索引。
        embeddings: list[list[float]] = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            embeddings.extend(
                self.embedding.embed_documents([chunk["text"] for chunk in batch])
            )
        if len(embeddings) != len(chunks):
            raise RuntimeError("Embedding 数量与对话分块数量不一致。")

        self.repository.replace_chunks(person_id, chunks)
        self.vector_store.delete_person(person_id)
        metadata = []
        for chunk in chunks:
            metadata.append(
                {
                    "person_id": person_id,
                    "chunk_id": chunk["id"],
                    "start_index": chunk["start_index"],
                    "end_index": chunk["end_index"],
                    "timestamp_start": chunk["timestamp_start"],
                    "timestamp_end": chunk["timestamp_end"],
                    "message_ids": json.dumps(
                        chunk["message_ids"], ensure_ascii=False
                    ),
                }
            )
        inserted = self.vector_store.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=[chunk["text"] for chunk in chunks],
            embeddings=embeddings,
            metadatas=metadata,
        )
        return IndexReport(person_id, len(chunks), inserted, len(messages))

    def search(
        self,
        person_id: str,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[SearchHit]:
        query = str(query or "").strip()
        if not query:
            return []
        limit = int(top_k or self.settings.rag_top_k)
        embedding = self.embedding.embed_query(query)
        candidate_limit = max(limit * 8, 24) if self.embedding.is_fallback else limit
        hits = self.vector_store.search(
            embedding, person_id, top_k=candidate_limit
        )
        if self.embedding.is_fallback:
            # 哈希向量不是语义模型，使用简单词面重合度重排，避免明显跑题。
            reranked = []
            for hit in hits:
                if not hit.text.strip():
                    continue
                lexical = _lexical_similarity(query, hit.text)
                if lexical <= 0:
                    continue
                hit.score = 0.15 * max(0.0, hit.score) + 0.85 * lexical
                if hit.score >= 0.06:
                    reranked.append(hit)
            hits = sorted(reranked, key=lambda item: item.score, reverse=True)
            return hits[:limit]
        return [
            hit
            for hit in hits
            if hit.text.strip() and hit.score >= self.settings.rag_min_score
        ][:limit]

    def format_context(
        self,
        hits: Iterable[SearchHit],
        max_chars: Optional[int] = None,
    ) -> str:
        limit = int(max_chars or self.settings.rag_context_chars)
        sections: list[str] = []
        used = 0
        for index, hit in enumerate(hits, start=1):
            metadata = hit.metadata or {}
            time_start = str(metadata.get("timestamp_start") or "")
            time_end = str(metadata.get("timestamp_end") or "")
            time_label = time_start if not time_end or time_end == time_start else f"{time_start} → {time_end}"
            header = f"[历史片段 {index} | 相似度 {hit.score:.3f}"
            if time_label:
                header += f" | {time_label}"
            header += "]"
            block = f"{header}\n{hit.text.strip()}"
            if used + len(block) > limit and sections:
                break
            sections.append(block[: max(0, limit - used)])
            used += len(sections[-1])
            if used >= limit:
                break
        return "\n\n".join(sections)

    def sources_for_display(
        self,
        hits: Iterable[SearchHit],
        max_snippet_chars: int = 420,
    ) -> list[dict]:
        result = []
        for hit in hits:
            metadata = hit.metadata or {}
            result.append(
                {
                    "chunk_id": hit.chunk_id,
                    "score": round(float(hit.score), 4),
                    "timestamp_start": metadata.get("timestamp_start", ""),
                    "timestamp_end": metadata.get("timestamp_end", ""),
                    "snippet": hit.text[:max_snippet_chars],
                }
            )
        return result

    def rebuild_all(self) -> list[IndexReport]:
        reports = []
        for person in self.repository.list_persons():
            reports.append(self.index_person(person["id"]))
        return reports

    def index_health(self, person_id: str) -> dict:
        chunk_count = self.repository.count_chunks(person_id)
        vector_count = self.vector_store.count(person_id)
        return {
            "chunk_count": chunk_count,
            "vector_count": vector_count,
            "healthy": chunk_count == vector_count,
            "backend": self.vector_store.info.label,
        }
