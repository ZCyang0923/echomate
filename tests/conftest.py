"""pytest fixtures。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.chat_parser import parse_txt
from core.chat_service import ChatService
from core.config import build_settings
from core.embedding_service import create_embedding_service
from core.import_service import compute_file_hash, import_chat
from core.llm_client import LLMClient
from core.memory_service import MemoryService
from core.rag_service import RAGService
from core.vector_store import create_vector_store
from database.db import Database
from database.repositories import Repository


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ECHOMATE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("VECTOR_BACKEND", "sqlite")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_MODEL", "")
    value = build_settings()
    value.ensure_directories()
    return value


@pytest.fixture()
def services(settings):
    database = Database(settings.database_path)
    database.init_schema()
    repository = Repository(database)
    embedding = create_embedding_service(settings, force_backend="hash")
    vector_store = create_vector_store(
        settings, embedding.info, database, force_backend="sqlite"
    )
    rag = RAGService(repository, embedding, vector_store, settings)
    llm = LLMClient(settings)
    return {
        "settings": settings,
        "db": database,
        "repo": repository,
        "embedding": embedding,
        "vector": vector_store,
        "rag": rag,
        "llm": llm,
        "chat": ChatService(repository, rag, llm, settings),
        "memory": MemoryService(repository, rag),
    }


@pytest.fixture()
def sample_txt_bytes() -> bytes:
    return (ROOT / "sample_data" / "demo_chat.txt").read_bytes()


@pytest.fixture()
def sample_csv_bytes() -> bytes:
    return (ROOT / "sample_data" / "demo_chat.csv").read_bytes()


@pytest.fixture()
def imported_person(services, sample_txt_bytes):
    parsed = parse_txt(sample_txt_bytes)
    outcome = import_chat(
        repository=services["repo"],
        rag_service=services["rag"],
        parsed=parsed,
        target_sender="小满",
        new_person_name="小满",
        file_name="demo_chat.txt",
        file_hash=compute_file_hash(sample_txt_bytes),
    )
    person = services["repo"].get_person(outcome.person_id)
    return person, parsed, outcome
