"""DeepSeek（OpenAI 兼容）调用与 JSON 解析。"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from core.config import Settings
from core.errors import LLMConfigurationError, LLMError, LLMResponseError


def extract_json_object(text: str) -> dict:
    """从模型输出中提取第一个 JSON 对象。"""
    if not text or not str(text).strip():
        raise LLMResponseError("模型返回了空内容。")
    cleaned = str(text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(cleaned[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError as exc:
            raise LLMResponseError("模型返回的 JSON 无法解析。") from exc
    raise LLMResponseError("模型没有返回可用的 JSON 对象。")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                part = item.get("text") or item.get("content")
                if part:
                    parts.append(str(part))
            elif item:
                parts.append(str(item))
        return "".join(parts)
    return "" if content is None else str(content)


class LLMClient:
    """对 OpenAI 兼容 SDK 的薄封装。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None

    @property
    def is_configured(self) -> bool:
        return self.settings.is_llm_configured

    def _ensure_configured(self) -> None:
        if not self.settings.deepseek_api_key:
            raise LLMConfigurationError(
                "未配置 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填写，"
                "或在页面启用离线演示模式。"
            )
        if not self.settings.deepseek_model:
            raise LLMConfigurationError(
                "未配置 DEEPSEEK_MODEL。请在 .env 中填写当前可用的模型名，"
                "例如 .env.example 中的默认值。"
            )

    def _get_client(self):
        if self._client is not None:
            return self._client
        self._ensure_configured()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "未安装 openai SDK，请执行 pip install -r requirements.txt。"
            ) from exc
        try:
            self._client = OpenAI(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
                timeout=self.settings.deepseek_timeout,
                max_retries=self.settings.deepseek_max_retries,
            )
        except Exception as exc:
            raise LLMConfigurationError(
                "DeepSeek 客户端初始化失败，请检查 .env 中的 Base URL 与 Key。"
            ) from exc
        return self._client

    def _sanitize_error(self, exc: Exception) -> str:
        message = str(exc)
        key = self.settings.deepseek_api_key
        if key:
            message = message.replace(key, "***")
        message = re.sub(r"(sk-[A-Za-z0-9_-]{8,})", "sk-***", message)
        if len(message) > 260:
            message = message[:260] + "…"
        return message

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        """调用 DeepSeek 对话补全。"""
        client = self._get_client()
        kwargs = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": (
                self.settings.chat_temperature
                if temperature is None
                else float(temperature)
            ),
            "max_tokens": int(max_tokens or self.settings.chat_max_tokens),
            "stream": False,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise LLMError(
                f"DeepSeek 调用失败（{type(exc).__name__}）："
                f"{self._sanitize_error(exc)}"
            ) from exc

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise LLMResponseError("DeepSeek 没有返回候选回复。")
        message = choices[0].message
        text = _content_to_text(getattr(message, "content", ""))
        if not text.strip():
            raise LLMResponseError("DeepSeek 返回了空回复。")
        return text

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """要求模型输出 JSON，并在空内容/非法 JSON 时重试一次。"""
        if "json" not in (system_prompt + user_prompt).lower():
            system_prompt = system_prompt + "\n必须只输出合法 JSON 对象。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                text = self.chat(
                    messages,
                    temperature=0.2 if attempt == 0 else 0.0,
                    max_tokens=max_tokens or self.settings.profile_max_tokens,
                    json_mode=True,
                )
                return extract_json_object(text)
            except LLMResponseError as exc:
                last_error = exc
                messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            user_prompt
                            + "\n\n上一次响应不是合法 JSON 或为空。"
                            "请严格只返回一个完整 JSON 对象，不要 Markdown 代码块。"
                        ),
                    },
                ]
            except LLMError:
                raise
        raise LLMResponseError(
            "DeepSeek 连续两次返回空内容或非法 JSON。请稍后重试或降低单批长度。"
        ) from last_error


def build_llm_client(settings: Settings) -> LLMClient:
    return LLMClient(settings)
