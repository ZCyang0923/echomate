"""导入、SQLite、RAG 与索引删除测试。"""

from __future__ import annotations

from core.chat_parser import parse_txt
from core.errors import DuplicateImportError, IngestionError
from core.import_service import (
    clear_person_content,
    compute_file_hash,
    delete_person_completely,
    import_chat,
    profile_is_outdated,
)


def test_import_person_and_index(imported_person, services):
    person, parsed, outcome = imported_person
    assert person["target_sender"] == "小满"
    assert outcome.index_error == ""
    assert outcome.message_count == 45
    stats = services["repo"].person_stats(person["id"])
    assert stats["message_count"] == 45
    assert stats["chunk_count"] > 0
    health = services["rag"].index_health(person["id"])
    assert health["healthy"] is True
    assert health["vector_count"] == stats["chunk_count"]


def test_duplicate_file_rejected(imported_person, services, sample_txt_bytes):
    person, parsed, outcome = imported_person
    try:
        import_chat(
            repository=services["repo"],
            rag_service=services["rag"],
            parsed=parsed,
            target_sender="小满",
            person_id=person["id"],
            file_name="demo_chat.txt",
            file_hash=compute_file_hash(sample_txt_bytes),
        )
    except DuplicateImportError:
        pass
    else:
        raise AssertionError("重复文件应当被拒绝")
    assert services["repo"].count_imported_messages(person["id"]) == 45


def test_related_retrieval(imported_person, services):
    person, _, _ = imported_person
    hits = services["rag"].search(person["id"], "上次一起看的电影叫什么", top_k=5)
    assert hits
    assert any("海上钢琴师" in hit.text for hit in hits)
    context = services["rag"].format_context(hits)
    assert "历史片段" in context
    assert "海上钢琴师" in context


def test_person_vectors_are_isolated(imported_person, services):
    person_a, _, _ = imported_person
    parsed_b = parse_txt(
        "[2024-05-01 10:00] 阿哲: 今天在整理房间\n".encode("utf-8")
    )
    outcome_b = import_chat(
        repository=services["repo"],
        rag_service=services["rag"],
        parsed=parsed_b,
        target_sender="阿哲",
        new_person_name="阿哲",
        file_name="b.txt",
        file_hash="b-hash",
    )
    hits = services["rag"].search(outcome_b.person_id, "电影 海上钢琴师", top_k=5)
    assert all("海上钢琴师" not in hit.text for hit in hits)
    # 原人物的检索不受影响
    hits_a = services["rag"].search(person_a["id"], "电影 海上钢琴师", top_k=5)
    assert any("海上钢琴师" in hit.text for hit in hits_a)


def test_delete_person_clears_sqlite_and_vectors(imported_person, services):
    person, _, _ = imported_person
    repo = services["repo"]
    rag = services["rag"]
    record = repo.save_profile(
        person["id"],
        {
            "nickname": "小满",
            "language_style": {"tone": "温和"},
            "catchphrases": ["嗯嗯"],
            "punctuation_habits": "",
            "emoji_habits": "",
            "emotional_expression": "",
            "interaction_habits": [],
            "interests_and_topics": [],
            "shared_experiences": [],
            "supported_facts": [],
            "uncertainties": [],
            "safety_notes": "",
        },
        provider="test",
        source_message_count=45,
    )
    assert record
    repo.replace_profile_memories(
        person["id"],
        [
            {
                "kind": "事实",
                "title": "测试记忆",
                "content": "测试",
                "evidence": "原文",
            }
        ],
    )
    repo.create_session(person["id"], "测试会话")
    assert services["vector"].count(person["id"]) > 0
    delete_person_completely(repo, rag, person["id"])
    assert repo.get_person(person["id"]) is None
    assert repo.count_imported_messages(person["id"]) == 0
    assert repo.count_chunks(person["id"]) == 0
    assert repo.list_memories(person["id"]) == []
    assert services["vector"].count(person["id"]) == 0


def test_clear_content_keeps_person(imported_person, services):
    person, _, _ = imported_person
    clear_person_content(services["repo"], services["rag"], person["id"])
    refreshed = services["repo"].get_person(person["id"])
    assert refreshed is not None
    assert refreshed["target_sender"] == ""
    stats = services["repo"].person_stats(person["id"])
    assert stats["message_count"] == 0
    assert stats["chunk_count"] == 0
    assert stats["session_count"] == 0
    assert services["vector"].count(person["id"]) == 0


def test_profile_outdated(imported_person, services):
    person, _, _ = imported_person
    assert profile_is_outdated(services["repo"], person["id"]) is False
    services["repo"].save_profile(
        person["id"],
        {
            "nickname": "小满",
            "language_style": {"tone": "温和"},
            "catchphrases": [],
            "punctuation_habits": "",
            "emoji_habits": "",
            "emotional_expression": "",
            "interaction_habits": [],
            "interests_and_topics": [],
            "shared_experiences": [],
            "supported_facts": [],
            "uncertainties": [],
            "safety_notes": "",
        },
        source_message_count=10,
    )
    assert profile_is_outdated(services["repo"], person["id"]) is True


def test_existing_person_cannot_mix_different_target(imported_person, services):
    person, _, _ = imported_person
    parsed = parse_txt(
        "[2024-05-01 10:00] 阿远: 今天在整理房间\n".encode("utf-8")
    )
    try:
        import_chat(
            repository=services["repo"],
            rag_service=services["rag"],
            parsed=parsed,
            target_sender="阿远",
            person_id=person["id"],
            file_name="other-target.txt",
            file_hash="other-target-hash",
        )
    except IngestionError:
        pass
    else:
        raise AssertionError("不能把不同目标人物混入同一档案")
    assert services["repo"].count_imported_messages(person["id"]) == 45
