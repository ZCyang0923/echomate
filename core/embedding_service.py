"""本地 Embedding 服务。

优先使用 sentence-transformers 的多语言模型；在依赖或模型不可用时，
降级为确定性的中文字符 n-gram 哈希向量，保证 MVP 仍可离线演示。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from core.config import Settings
from core.errors import EmbeddingError


@dataclass
class EmbeddingInfo:
    backend: str
    model_name: str
    dimension: int
    is_fallback: bool = False
    note: str = ""

    @property
    def backend_key(self) -> str:
        return f"{self.backend}:{self.model_name}:{self.dimension}"


class HashEmbeddingBackend:
    """无外部模型依赖的字符 n-gram 哈希向量。

    这不是语义模型，只用于依赖缺失时的离线演示和自动化测试。
    """

    backend = "hash"
    model_name = "hash-char-ngram-v1"
    dimension = 384

    _TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]")

    def _vector(self, text: str) -> np.ndarray:
        normalized = str(text or "").lower().strip()
        vector = np.zeros(self.dimension, dtype=np.float32)
        if not normalized:
            return vector

        # 中文字符 1/2/3-gram 与拉丁词共同构成轻量特征
        tokens = self._TOKEN_PATTERN.findall(normalized)
        compact = re.sub(r"\s+", "", normalized)
        for size in (2, 3):
            if len(compact) >= size:
                for index in range(len(compact) - size + 1):
                    tokens.append(compact[index : index + size])

        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"), digest_size=8
            ).digest()
            number = int.from_bytes(digest, "little")
            position = number % self.dimension
            sign = 1.0 if (number >> 17) & 1 else -1.0
            vector[position] += sign

        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text).tolist() for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text).tolist()


class SentenceTransformerEmbeddingBackend:
    """使用本地 sentence-transformers 模型。"""

    backend = "sentence_transformers"

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(
                "未安装 sentence-transformers。请安装 requirements.txt；"
                "也可以将 EMBEDDING_BACKEND 设为 hash 使用离线降级向量。"
            ) from exc

        try:
            self.model = SentenceTransformer(model_name, device="cpu")
        except Exception as exc:
            raise EmbeddingError(
                "本地 Embedding 模型加载失败。首次运行需要下载模型；"
                "如果当前环境离线，可改用 EMBEDDING_BACKEND=hash。"
                f"（{type(exc).__name__}）"
            ) from exc
        self.model_name = model_name
        try:
            dimension = self.model.get_embedding_dimension()
        except AttributeError:
            dimension = self.model.get_sentence_embedding_dimension()
        self.dimension = int(dimension)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32).tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            [str(text or "")],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return np.asarray(vector, dtype=np.float32).tolist()


class EmbeddingService:
    """统一的 Embedding 接口。"""

    def __init__(self, backend, info: EmbeddingInfo):
        self._backend = backend
        self.info = info

    @property
    def backend_name(self) -> str:
        return self.info.backend

    @property
    def dimension(self) -> int:
        return self.info.dimension

    @property
    def model_name(self) -> str:
        return self.info.model_name

    @property
    def is_fallback(self) -> bool:
        return self.info.is_fallback

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._backend.embed_documents(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return self._backend.embed_query(str(text or ""))

    def status_label(self) -> str:
        if self.is_fallback:
            return "离线哈希向量（降级）"
        return f"sentence-transformers · {self.model_name}"


def create_embedding_service(
    settings: Settings,
    force_backend: str | None = None,
) -> EmbeddingService:
    """创建 Embedding 服务。

    force_backend 便于测试和显式切换；auto 模式下缺少依赖会降级。
    """
    backend = (force_backend or settings.embedding_backend).lower()

    if backend == "hash":
        instance = HashEmbeddingBackend()
        return EmbeddingService(
            instance,
            EmbeddingInfo(
                backend="hash",
                model_name=instance.model_name,
                dimension=instance.dimension,
                is_fallback=True,
                note="使用离线哈希向量；检索质量低于语义模型。",
            ),
        )

    if backend in {"auto", "sentence_transformers"}:
        try:
            instance = SentenceTransformerEmbeddingBackend(
                settings.embedding_model
            )
            return EmbeddingService(
                instance,
                EmbeddingInfo(
                    backend="sentence_transformers",
                    model_name=settings.embedding_model,
                    dimension=instance.dimension,
                    is_fallback=False,
                ),
            )
        except EmbeddingError as exc:
            if backend == "sentence_transformers":
                raise
            fallback = HashEmbeddingBackend()
            return EmbeddingService(
                fallback,
                EmbeddingInfo(
                    backend="hash",
                    model_name=fallback.model_name,
                    dimension=fallback.dimension,
                    is_fallback=True,
                    note=str(exc),
                ),
            )

    raise EmbeddingError(f"未知的 EMBEDDING_BACKEND：{backend}")
