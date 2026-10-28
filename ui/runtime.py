"""应用运行时服务装配。"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from core.chat_service import ChatService
from core.config import Settings, get_settings
from core.embedding_service import EmbeddingService, create_embedding_service
from core.llm_client import LLMClient
from core.memory_service import MemoryService
from core.rag_service import RAGService
from core.vector_store import VectorStoreService, create_vector_store
from database.db import Database
from database.repositories import Repository


@dataclass
class Runtime:
    settings: Settings
    database: Database
    repository: Repository
    embedding: EmbeddingService
    vector_store: VectorStoreService
    rag: RAGService
    llm: LLMClient
    chat: ChatService
    memory: MemoryService

    @property
    def mock_default(self) -> bool:
        return not self.settings.is_llm_configured


@st.cache_resource(show_spinner="正在初始化本地服务…")
def get_runtime() -> Runtime:
    settings = get_settings()
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.init_schema()
    repository = Repository(database)
    embedding = create_embedding_service(settings)
    vector_store = create_vector_store(
        settings,
        embedding.info,
        database,
    )
    rag = RAGService(repository, embedding, vector_store, settings)
    llm = LLMClient(settings)
    chat = ChatService(repository, rag, llm, settings)
    memory = MemoryService(repository, rag)
    return Runtime(
        settings=settings,
        database=database,
        repository=repository,
        embedding=embedding,
        vector_store=vector_store,
        rag=rag,
        llm=llm,
        chat=chat,
        memory=memory,
    )
