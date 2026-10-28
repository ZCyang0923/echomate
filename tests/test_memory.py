"""记忆提取、编辑、删除与人物隔离测试。"""

from __future__ import annotations

from core.memory_service import profile_to_memory_items
from core.profile_builder import build_profile


def _make_profile(settings, messages, target="小满"):
    return build_profile(messages, target, settings, mock=True)[0]


def test_profile_to_memories_and_sync(imported_person, services):
    person, parsed, _ = imported_person
    messages = services["repo"].list_imported_messages(person["id"])
    profile = _make_profile(services["settings"], messages)
    items = profile_to_memory_items(profile)
    assert all(item["content"] for item in items)
    count = services["memory"].sync_from_profile(person["id"], profile)
    memories = services["repo"].list_memories(person["id"])
    assert count == len(memories)
    assert count > 0


def test_edit_and_delete_memory(imported_person, services):
    person, parsed, _ = imported_person
    messages = services["repo"].list_imported_messages(person["id"])
    profile = _make_profile(services["settings"], messages)
    services["memory"].sync_from_profile(person["id"], profile)
    memories = services["repo"].list_memories(person["id"])
    memory = memories[0]
    updated = services["memory"].update_memory(
        person["id"],
        memory["id"],
        "事实",
        "修正后的标题",
        "修正后的内容",
        "用户提供的证据",
    )
    assert updated["content"] == "修正后的内容"
    services["memory"].delete_memory(person["id"], memory["id"])
    assert services["repo"].get_memory(memory["id"]) is None


def test_memory_sources_come_from_imported_chat(imported_person, services):
    person, parsed, _ = imported_person
    message = {
        "id": "memory-test",
        "kind": "共同经历",
        "title": "电影",
        "content": "一起看《海上钢琴师》",
    }
    hits = services["memory"].find_sources(person["id"], message, top_k=5)
    assert any("海上钢琴师" in hit.text for hit in hits)


def test_memory_person_isolation(imported_person, services):
    person_a, _, _ = imported_person
    person_b = services["repo"].create_person("阿远")
    profile = {
        "nickname": "阿远",
        "shared_experiences": [
            {"summary": "打篮球", "evidence": "周末打球"}
        ],
        "supported_facts": [],
    }
    services["memory"].sync_from_profile(person_b["id"], profile)
    assert services["repo"].count_memories(person_b["id"]) == 1
    assert services["repo"].count_memories(person_a["id"]) == 0
