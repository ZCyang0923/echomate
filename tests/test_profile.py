"""人物画像生成测试。"""

from __future__ import annotations

from dataclasses import replace

import pytest

from core.errors import ProfileBuildError
from core.profile_builder import (
    build_profile,
    estimate_profile_batches,
    validate_profile,
)


class FakeProfileLLM:
    is_configured = True

    def __init__(self, response=None, fail_times: int = 0):
        self.response = response or {
            "nickname": "小满",
            "language_style": {
                "sentence_length": "短句",
                "formality": "随意",
                "tone": "温和",
                "vocabulary": "嗯嗯、好呀",
            },
            "catchphrases": ["嗯嗯", "好呀"],
            "punctuation_habits": "常用问号",
            "emoji_habits": "偶尔用 😂",
            "emotional_expression": "会用简短句子关心人",
            "interaction_habits": ["先回应情绪再给建议"],
            "interests_and_topics": ["电影", "咖啡"],
            "shared_experiences": [
                {"summary": "一起看电影", "evidence": "上次一起看的那部电影"}
            ],
            "supported_facts": [
                {"fact": "喜欢咖啡", "evidence": "桥边那家咖啡店"}
            ],
            "uncertainties": ["不能确认更多私人信息"],
            "safety_notes": "仅用于风格模拟。",
        }
        self.fail_times = fail_times
        self.calls = 0

    def complete_json(self, system_prompt, user_prompt, *, max_tokens=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("mock failure")
        return dict(self.response)


def _messages():
    return [
        {
            "message_index": 1,
            "timestamp": "2024-01-01 10:00",
            "sender": "小满",
            "content": "嗯嗯，今天有点累。",
            "is_target": True,
        },
        {
            "message_index": 2,
            "timestamp": "2024-01-01 10:01",
            "sender": "阿远",
            "content": "那先休息。",
            "is_target": False,
        },
    ]


def test_mock_profile_is_valid(settings):
    profile, meta = build_profile(
        _messages(), "小满", settings, mock=True
    )
    assert profile["nickname"] == "小满"
    assert meta["provider"] == "mock"
    assert profile["language_style"]["tone"]
    assert profile["safety_notes"]


def test_empty_target_raises(settings):
    with pytest.raises(ProfileBuildError):
        build_profile(_messages(), "不存在", settings, mock=True)


def test_fake_llm_profile_and_batch_plan(settings):
    small = replace(
        settings,
        profile_batch_messages=10,
        profile_batch_chars=5000,
        profile_max_batches=2,
    )
    messages = []
    for index in range(45):
        messages.append(
            {
                "message_index": index + 1,
                "timestamp": f"2024-01-01 10:{index % 60:02d}",
                "sender": "小满" if index % 2 == 0 else "阿远",
                "content": f"第 {index} 条测试消息，今天聊电影。",
                "is_target": index % 2 == 0,
            }
        )
    fake = FakeProfileLLM()
    profile, meta = build_profile(
        messages,
        "小满",
        small,
        llm_client=fake,
        mock=False,
    )
    assert fake.calls == 2
    assert meta["batch_count"] == 2
    assert meta["sampled"] is True
    assert profile["catchphrases"]
    assert meta["used_messages"] <= 20


def test_partial_batch_failure_is_tolerated(settings):
    fake = FakeProfileLLM(fail_times=1)
    messages = []
    for index in range(20):
        messages.append(
            {
                "message_index": index + 1,
                "timestamp": f"2024-01-01 10:{index:02d}",
                "sender": "小满" if index % 2 == 0 else "阿远",
                "content": f"第 {index} 条消息，在聊电影和咖啡。",
                "is_target": index % 2 == 0,
            }
        )
    small = replace(
        settings,
        profile_batch_messages=10,
        profile_batch_chars=5000,
        profile_max_batches=2,
    )
    profile, meta = build_profile(
        messages,
        "小满",
        small,
        llm_client=fake,
        mock=False,
    )
    assert profile["nickname"] == "小满"
    assert fake.calls == 2
    assert meta["warnings"]


def test_invalid_profile_structure():
    with pytest.raises(ProfileBuildError):
        validate_profile({"nickname": "小满"}, "小满")
    normalized = validate_profile(
        {
            "nickname": "小满",
            "language_style": {"tone": "温和"},
            "shared_experiences": ["一起看过电影"],
        },
        "小满",
    )
    assert normalized["shared_experiences"][0]["summary"] == "一起看过电影"


def test_estimate_batches(settings):
    messages = _messages()
    estimate = estimate_profile_batches(messages, settings)
    assert estimate["batch_count"] == 1
    assert estimate["total_messages"] == 2
