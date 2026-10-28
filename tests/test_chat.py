"""多轮聊天、会话隔离与 Mock 测试。"""

from __future__ import annotations

import pytest

from core.chat_service import ChatService
from core.errors import ChatError
from core.profile_builder import build_profile


class FakeChatLLM:
    is_configured = True

    def __init__(self):
        self.calls = []

    def chat(self, messages, *, temperature=None, max_tokens=None, json_mode=False):
        self.calls.append(messages)
        return "我在呢，你慢慢说。"


def _setup_chat(imported_person, services):
    person, parsed, _ = imported_person
    messages = services["repo"].list_imported_messages(person["id"])
    profile, _ = build_profile(
        messages, "小满", services["settings"], mock=True
    )
    services["repo"].save_profile(
        person["id"],
        profile,
        provider="mock",
        source_message_count=len(messages),
    )
    services["memory"].sync_from_profile(person["id"], profile)
    session = services["repo"].create_session(person["id"], "测试会话")
    return person, profile, session


def test_mock_multiturn_chat(imported_person, services):
    person, profile, session = _setup_chat(imported_person, services)
    reply = services["chat"].send_message(
        person["id"], session["id"], "今天有点累", mock=True
    )
    assert reply.text
    assert reply.is_mock is True
    assert reply.user_message_id and reply.assistant_message_id
    messages = services["repo"].list_chat_messages(session["id"])
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "今天有点累"

    second = services["chat"].send_message(
        person["id"], session["id"], "你还记得上次看的电影吗", mock=True
    )
    assert second.retrieval_count >= 1
    assert len(services["repo"].list_chat_messages(session["id"])) == 4


def test_sessions_are_isolated(imported_person, services):
    person, profile, session_a = _setup_chat(imported_person, services)
    session_b = services["repo"].create_session(person["id"], "另一个会话")
    services["chat"].send_message(person["id"], session_a["id"], "会话 A", mock=True)
    services["chat"].send_message(person["id"], session_b["id"], "会话 B", mock=True)
    a_messages = services["repo"].list_chat_messages(session_a["id"])
    b_messages = services["repo"].list_chat_messages(session_b["id"])
    assert [item["content"] for item in a_messages if item["role"] == "user"] == ["会话 A"]
    assert [item["content"] for item in b_messages if item["role"] == "user"] == ["会话 B"]


def test_person_sessions_isolated(imported_person, services):
    person_a, profile, session_a = _setup_chat(imported_person, services)
    person_b = services["repo"].create_person("阿远", target_sender="阿远")
    profile_b = dict(profile)
    profile_b["nickname"] = "阿远"
    services["repo"].save_profile(
        person_b["id"], profile_b, provider="mock", source_message_count=0
    )
    session_b = services["repo"].create_session(person_b["id"], "B 会话")
    services["chat"].send_message(person_a["id"], session_a["id"], "A 的消息", mock=True)
    services["chat"].send_message(person_b["id"], session_b["id"], "B 的消息", mock=True)
    assert services["repo"].count_chat_messages(session_a["id"]) == 2
    assert services["repo"].count_chat_messages(session_b["id"]) == 2


def test_chat_rejects_session_from_other_person(imported_person, services):
    person_a, profile, session_a = _setup_chat(imported_person, services)
    person_b = services["repo"].create_person("阿远", target_sender="阿远")
    services["repo"].save_profile(
        person_b["id"], profile, provider="mock", source_message_count=0
    )
    with pytest.raises(ChatError):
        services["chat"].send_message(
            person_b["id"], session_a["id"], "污染测试", mock=True
        )


def test_chat_requires_profile(imported_person, services):
    person, _, _ = imported_person
    session = services["repo"].create_session(person["id"], "无画像")
    with pytest.raises(ChatError):
        services["chat"].send_message(
            person["id"], session["id"], "你好", mock=True
        )


def test_real_llm_path_uses_api_messages(imported_person, services):
    person, profile, session = _setup_chat(imported_person, services)
    fake = FakeChatLLM()
    service = ChatService(
        services["repo"], services["rag"], fake, services["settings"]
    )
    reply = service.send_message(
        person["id"], session["id"], "上次看的电影是什么？", mock=False
    )
    assert reply.text == "我在呢，你慢慢说。"
    assert reply.is_mock is False
    assert fake.calls
    system_prompt = fake.calls[0][0]["content"]
    assert "AI 模拟聊天角色" in system_prompt
    assert "<PROFILE_JSON>" in system_prompt
    assert "<RETRIEVED_HISTORY>" in system_prompt
