"""EchoMate 配置读取。

所有密钥只从环境变量/.env 读取，绝不写入代码或 UI。
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - requirements 中已包含
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def _env_text(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = _env_text(name, str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = _env_text(name, str(default))
    try:
        value = float(raw)
    except ValueError:
        return default
    return min(max(value, minimum), maximum)


def _resolve_path(raw: str, default: str) -> Path:
    value = Path(raw.strip() or default)
    if not value.is_absolute():
        value = PROJECT_ROOT / value
    return value.resolve()


@dataclass(frozen=True)
class Settings:
    """应用配置。"""

    project_root: Path
    data_dir: Path
    database_path: Path
    chroma_dir: Path
    upload_dir: Path
    temp_dir: Path
    hf_home: Path
    deepseek_api_key: str = field(repr=False)
    deepseek_base_url: str
    deepseek_model: str
    embedding_model: str
    embedding_backend: str
    vector_backend: str
    deepseek_timeout: float
    deepseek_max_retries: int
    profile_batch_messages: int
    profile_batch_chars: int
    profile_max_batches: int
    profile_max_tokens: int
    chat_max_tokens: int
    chat_temperature: float
    chat_history_messages: int
    rag_top_k: int
    rag_context_chars: int
    rag_min_score: float
    chunk_size_messages: int
    chunk_overlap_messages: int
    max_upload_mb: int

    @property
    def is_llm_configured(self) -> bool:
        return bool(self.deepseek_api_key and self.deepseek_model)

    @property
    def api_key_hint(self) -> str:
        # 前端只显示是否配置，不暴露 Key 的任何字符。
        return "已配置" if self.deepseek_api_key else "未配置"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # 当前 Windows 环境的用户 TEMP 目录可能不可写，Chroma/编译工具
        # 会因此报 "unable to open database file"。把本进程的临时目录
        # 定向到项目 data/tmp，避免污染系统目录并保证本地服务可启动。
        temp_path = str(self.temp_dir)
        os.environ["TEMP"] = temp_path
        os.environ["TMP"] = temp_path
        os.environ["TMPDIR"] = temp_path
        tempfile.tempdir = temp_path
        # 模型缓存放在项目 data 目录，避免 Windows 用户目录权限问题。
        self.hf_home.mkdir(parents=True, exist_ok=True)
        os.environ["HF_HOME"] = str(self.hf_home)
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    def public_summary(self) -> dict:
        """可安全显示在 UI 的配置摘要，不包含 API Key。"""
        return {
            "deepseek_configured": self.is_llm_configured,
            "api_key": self.api_key_hint,
            "base_url": self.deepseek_base_url,
            "model": self.deepseek_model or "未配置",
            "embedding_model": self.embedding_model,
            "embedding_backend": self.embedding_backend,
            "vector_backend": self.vector_backend,
        }


def build_settings() -> Settings:
    data_dir = _resolve_path(_env_text("ECHOMATE_DATA_DIR", "data"), "data")
    database_path = _resolve_path(
        _env_text("ECHOMATE_DB_PATH", str(data_dir / "echomate.db")),
        str(data_dir / "echomate.db"),
    )
    chroma_dir = _resolve_path(
        _env_text("ECHOMATE_CHROMA_DIR", str(data_dir / "chroma")),
        str(data_dir / "chroma"),
    )
    upload_dir = _resolve_path(
        _env_text("ECHOMATE_UPLOAD_DIR", str(data_dir / "uploads")),
        str(data_dir / "uploads"),
    )
    temp_dir = _resolve_path(
        _env_text("ECHOMATE_TEMP_DIR", str(data_dir / "tmp")),
        str(data_dir / "tmp"),
    )
    hf_home = _resolve_path(
        _env_text("HF_HOME", str(data_dir / "hf_cache")),
        str(data_dir / "hf_cache"),
    )

    embedding_backend = _env_text("EMBEDDING_BACKEND", "auto").lower()
    if embedding_backend not in {"auto", "sentence_transformers", "hash"}:
        embedding_backend = "auto"
    vector_backend = _env_text("VECTOR_BACKEND", "auto").lower()
    if vector_backend not in {"auto", "chroma", "sqlite"}:
        vector_backend = "auto"

    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        database_path=database_path,
        chroma_dir=chroma_dir,
        upload_dir=upload_dir,
        temp_dir=temp_dir,
        hf_home=hf_home,
        deepseek_api_key=_env_text("DEEPSEEK_API_KEY"),
        deepseek_base_url=_env_text(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        ).rstrip("/"),
        deepseek_model=_env_text("DEEPSEEK_MODEL"),
        embedding_model=_env_text(
            "EMBEDDING_MODEL",
            "paraphrase-multilingual-MiniLM-L12-v2",
        ),
        embedding_backend=embedding_backend,
        vector_backend=vector_backend,
        deepseek_timeout=_env_float("DEEPSEEK_TIMEOUT", 60.0, 5.0, 300.0),
        deepseek_max_retries=_env_int("DEEPSEEK_MAX_RETRIES", 2, 0, 5),
        profile_batch_messages=_env_int("PROFILE_BATCH_MESSAGES", 80, 10, 300),
        profile_batch_chars=_env_int("PROFILE_BATCH_CHARS", 9_000, 1_000, 30_000),
        profile_max_batches=_env_int("PROFILE_MAX_BATCHES", 6, 1, 20),
        profile_max_tokens=_env_int("PROFILE_MAX_TOKENS", 1_800, 400, 8_000),
        chat_max_tokens=_env_int("CHAT_MAX_TOKENS", 900, 100, 4_000),
        chat_temperature=_env_float("CHAT_TEMPERATURE", 0.8, 0.0, 1.5),
        chat_history_messages=_env_int("CHAT_HISTORY_MESSAGES", 12, 2, 60),
        rag_top_k=_env_int("RAG_TOP_K", 5, 1, 20),
        rag_context_chars=_env_int("RAG_CONTEXT_CHARS", 4_500, 500, 20_000),
        rag_min_score=_env_float("RAG_MIN_SCORE", 0.08, -1.0, 1.0),
        chunk_size_messages=_env_int("CHUNK_SIZE_MESSAGES", 8, 2, 50),
        chunk_overlap_messages=_env_int("CHUNK_OVERLAP_MESSAGES", 2, 0, 20),
        max_upload_mb=_env_int("MAX_UPLOAD_MB", 10, 1, 100),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = build_settings()
    settings.ensure_directories()
    return settings


def clear_settings_cache() -> None:
    """供测试或修改 .env 后重新加载。"""
    get_settings.cache_clear()


def get_api_key_display(settings: Optional[Settings] = None) -> str:
    settings = settings or get_settings()
    return settings.api_key_hint
