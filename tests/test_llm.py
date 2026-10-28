"""LLM JSON 解析与缺配置错误测试。"""

from __future__ import annotations

import pytest

from core.errors import LLMConfigurationError, LLMResponseError
from core.llm_client import LLMClient, extract_json_object


def test_extract_json_plain_and_fenced():
    assert extract_json_object('{"a": 1}') == {"a": 1}
    assert extract_json_object('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json_object('前缀 {"a": 3} 后缀') == {"a": 3}


def test_extract_json_rejects_invalid():
    with pytest.raises(LLMResponseError):
        extract_json_object("")
    with pytest.raises(LLMResponseError):
        extract_json_object("not json at all")


def test_llm_missing_configuration(settings):
    client = LLMClient(settings)
    with pytest.raises(LLMConfigurationError) as exc:
        client.chat([{"role": "user", "content": "hello"}])
    assert "DEEPSEEK_API_KEY" in str(exc.value)
    assert settings.deepseek_api_key == ""


def test_complete_json_retries_empty_response(settings):
    client = LLMClient(settings)
    responses = iter(["", '{"ok": true}'])
    client.chat = lambda *args, **kwargs: next(responses)
    result = client.complete_json("return json", "give json")
    assert result == {"ok": True}


def test_complete_json_fails_after_two_bad_outputs(settings):
    client = LLMClient(settings)
    client.chat = lambda *args, **kwargs: "not json"
    with pytest.raises(LLMResponseError):
        client.complete_json("return json", "give json")
