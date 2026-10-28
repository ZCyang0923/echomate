"""向量存储适配层。

默认优先使用 ChromaDB；当前环境未安装 Chroma 时，自动降级到 SQLite
向量表。两种后端都按 person_id 强隔离，并支持删除与重建。
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from core.config import Settings
from core.embedding_service import EmbeddingInfo
from core.errors import VectorStoreError
from database.db import Database


@dataclass
class SearchHit:
    chunk_id: str
    text: str
    score: float
    metadata: dict


class SQLiteVectorStore:
    backend_name = "sqlite"

    def __init__(self, db: Database, backend_key: str):
        self.db = db
        self.backend_key = backend_key

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[dict],
    ) -> int:
        if not ids:
            return 0
        from database.repositories import utc_now

        now = utc_now()
        rows = []
        for chunk_id, document, embedding, metadata in zip(
            ids, documents, embeddings, metadatas
        ):
            vector = np.asarray(embedding, dtype=np.float32)
            vector /= max(float(np.linalg.norm(vector)), 1e-12)
            payload = dict(metadata)
            payload["_backend_key"] = self.backend_key
            rows.append(
                (
                    str(chunk_id),
                    str(payload.get("person_id", "")),
                    str(document),
                    json.dumps(payload, ensure_ascii=False),
                    sqlite3.Binary(vector.tobytes()),
                    int(vector.shape[0]),
                    now,
                )
            )
        with self.db.session() as connection:
            connection.executemany(
                """
                INSERT INTO vector_entries(
                    chunk_id, person_id, document, metadata_json,
                    embedding, dimension, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    person_id = excluded.person_id,
                    document = excluded.document,
                    metadata_json = excluded.metadata_json,
                    embedding = excluded.embedding,
                    dimension = excluded.dimension,
                    created_at = excluded.created_at
                """,
                rows,
            )
        return len(rows)

    def search(
        self,
        query_embedding: Sequence[float],
        person_id: str,
        top_k: int = 5,
    ) -> list[SearchHit]:
        query = np.asarray(query_embedding, dtype=np.float32)
        if query.size == 0:
            return []
        query /= max(float(np.linalg.norm(query)), 1e-12)
        rows = self.db.fetch_all(
            """
            SELECT chunk_id, document, metadata_json, embedding, dimension
            FROM vector_entries
            WHERE person_id = ?
            """,
            (person_id,),
        )
        hits: list[SearchHit] = []
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                metadata = {}
            if metadata.get("_backend_key") != self.backend_key:
                continue
            if int(row["dimension"]) != int(query.shape[0]):
                continue
            vector = np.frombuffer(row["embedding"], dtype=np.float32)
            if vector.shape[0] != query.shape[0]:
                continue
            score = float(np.dot(query, vector))
            hits.append(
                SearchHit(
                    chunk_id=row["chunk_id"],
                    text=row["document"],
                    score=score,
                    metadata=metadata,
                )
            )
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: int(top_k)]

    def delete_person(self, person_id: str) -> None:
        self.db.execute(
            "DELETE FROM vector_entries WHERE person_id = ?",
            (person_id,),
        )

    def delete_chunk_ids(self, chunk_ids: Iterable[str]) -> None:
        ids = [str(item) for item in chunk_ids if item]
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        self.db.execute(
            f"DELETE FROM vector_entries WHERE chunk_id IN ({placeholders})",
            tuple(ids),
        )

    def count(self, person_id: str) -> int:
        rows = self.db.fetch_all(
            "SELECT metadata_json FROM vector_entries WHERE person_id = ?",
            (person_id,),
        )
        count = 0
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if metadata.get("_backend_key") == self.backend_key:
                count += 1
        return count


class ChromaVectorStore:
    backend_name = "chroma"

    def __init__(
        self,
        path: Path,
        backend_key: str,
        collection_prefix: str = "echomate",
    ):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError as exc:
            raise VectorStoreError(
                "未安装 chromadb。可在 requirements.txt 中安装，"
                "或使用 SQLite 向量降级模式。"
            ) from exc

        digest = hashlib.sha1(backend_key.encode("utf-8")).hexdigest()[:10]
        self.collection_name = f"{collection_prefix}_{digest}"
        self.backend_key = backend_key
        path.mkdir(parents=True, exist_ok=True)
        try:
            self.client = chromadb.PersistentClient(
                path=str(path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            try:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    configuration={"hnsw": {"space": "cosine"}},
                )
            except Exception:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as exc:
            raise VectorStoreError(
                f"ChromaDB 初始化失败：{type(exc).__name__}"
            ) from exc

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[dict],
    ) -> int:
        if not ids:
            return 0
        clean_metadatas = []
        for metadata in metadatas:
            clean = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean[str(key)] = value
                elif value is None:
                    clean[str(key)] = ""
                else:
                    clean[str(key)] = json.dumps(value, ensure_ascii=False)
            clean["_backend_key"] = self.backend_key
            clean_metadatas.append(clean)
        try:
            self.collection.upsert(
                ids=[str(item) for item in ids],
                documents=[str(document) for document in documents],
                embeddings=[list(map(float, vector)) for vector in embeddings],
                metadatas=clean_metadatas,
            )
        except Exception as exc:
            raise VectorStoreError(
                f"ChromaDB 写入失败：{type(exc).__name__}"
            ) from exc
        return len(ids)

    def search(
        self,
        query_embedding: Sequence[float],
        person_id: str,
        top_k: int = 5,
    ) -> list[SearchHit]:
        try:
            result = self.collection.query(
                query_embeddings=[list(map(float, query_embedding))],
                n_results=int(top_k),
                where={"person_id": str(person_id)},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(
                f"ChromaDB 检索失败：{type(exc).__name__}"
            ) from exc

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        hits: list[SearchHit] = []
        for index, chunk_id in enumerate(ids):
            distance = float(distances[index]) if index < len(distances) else 1.0
            metadata = dict(metadatas[index] or {}) if index < len(metadatas) else {}
            hits.append(
                SearchHit(
                    chunk_id=str(chunk_id),
                    text=str(documents[index]) if index < len(documents) else "",
                    score=1.0 - distance,
                    metadata=metadata,
                )
            )
        return hits

    def delete_person(self, person_id: str) -> None:
        try:
            self.collection.delete(where={"person_id": str(person_id)})
        except Exception as exc:
            raise VectorStoreError(
                f"ChromaDB 删除失败：{type(exc).__name__}"
            ) from exc

    def delete_chunk_ids(self, chunk_ids: Iterable[str]) -> None:
        ids = [str(item) for item in chunk_ids if item]
        if not ids:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception as exc:
            raise VectorStoreError(
                f"ChromaDB 删除失败：{type(exc).__name__}"
            ) from exc

    def count(self, person_id: str) -> int:
        try:
            result = self.collection.get(
                where={"person_id": str(person_id)},
                include=["metadatas"],
            )
            return len(result.get("ids") or [])
        except Exception:
            return 0


@dataclass
class VectorStoreInfo:
    backend: str
    backend_key: str
    is_fallback: bool = False
    note: str = ""

    @property
    def label(self) -> str:
        if self.backend == "chroma":
            return "ChromaDB"
        return "SQLite 向量表（降级）"


class VectorStoreService:
    def __init__(self, store, info: VectorStoreInfo):
        self._store = store
        self.info = info

    @property
    def backend_name(self) -> str:
        return self.info.backend

    @property
    def is_fallback(self) -> bool:
        return self.info.is_fallback

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[dict],
    ) -> int:
        return self._store.upsert(ids, documents, embeddings, metadatas)

    def search(
        self,
        query_embedding: Sequence[float],
        person_id: str,
        top_k: int = 5,
    ) -> list[SearchHit]:
        return self._store.search(query_embedding, person_id, top_k)

    def delete_person(self, person_id: str) -> None:
        self._store.delete_person(person_id)

    def delete_chunk_ids(self, chunk_ids: Iterable[str]) -> None:
        self._store.delete_chunk_ids(chunk_ids)

    def count(self, person_id: str) -> int:
        return self._store.count(person_id)


def create_vector_store(
    settings: Settings,
    embedding_info: EmbeddingInfo,
    db: Database,
    force_backend: str | None = None,
) -> VectorStoreService:
    """创建向量存储；auto 模式在 Chroma 不可用时降级为 SQLite。"""
    backend = (force_backend or settings.vector_backend).lower()
    backend_key = embedding_info.backend_key
    if backend in {"auto", "chroma"}:
        try:
            chroma = ChromaVectorStore(
                settings.chroma_dir,
                backend_key=backend_key,
            )
            return VectorStoreService(
                chroma,
                VectorStoreInfo(
                    backend="chroma",
                    backend_key=backend_key,
                ),
            )
        except Exception as exc:
            if backend == "chroma":
                # 明确选择 Chroma 时也回退，但必须向界面暴露原因。
                note = f"ChromaDB 不可用：{type(exc).__name__}。已使用 SQLite 降级。"
            else:
                note = "ChromaDB 未安装或初始化失败，已使用 SQLite 向量表。"
            sqlite_store = SQLiteVectorStore(db, backend_key=backend_key)
            return VectorStoreService(
                sqlite_store,
                VectorStoreInfo(
                    backend="sqlite",
                    backend_key=backend_key,
                    is_fallback=True,
                    note=note,
                ),
            )
    if backend == "sqlite":
        return VectorStoreService(
            SQLiteVectorStore(db, backend_key=backend_key),
            VectorStoreInfo(
                backend="sqlite",
                backend_key=backend_key,
                is_fallback=True,
                note="已按配置使用 SQLite 向量表。",
            ),
        )
    raise VectorStoreError(f"未知的 VECTOR_BACKEND：{backend}")
