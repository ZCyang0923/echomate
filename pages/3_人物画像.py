"""人物画像页面。"""

from __future__ import annotations

import html
import json

import streamlit as st

from core.config import get_api_key_display
from core.errors import ProfileBuildError
from core.import_service import profile_is_outdated
from core.profile_builder import (
    build_profile,
    estimate_profile_batches,
    validate_profile,
)
from ui.common import (
    format_timestamp,
    is_mock_mode,
    render_footer,
    render_page_header,
    select_person,
    start_page,
)


def _flash() -> None:
    message = st.session_state.pop("profile_flash", "")
    if message:
        st.success(message)


def _render_profile_generator(runtime, person: dict, record: dict | None) -> dict | None:
    messages = runtime.repository.list_imported_messages(person["id"])
    target_count = runtime.repository.count_target_messages(person["id"])
    mock = is_mock_mode()
    estimate = estimate_profile_batches(messages, runtime.settings)

    with st.container(border=True):
        st.markdown("### 生成人物画像")
        if not messages:
            st.warning("这个人物还没有导入聊天记录，无法生成画像。")
            st.page_link(
                "pages/2_导入聊天记录.py",
                label="去导入聊天记录",
                icon="📥",
            )
            return record

        columns = st.columns(4)
        columns[0].metric("来源消息", len(messages))
        columns[1].metric("目标人物消息", target_count)
        columns[2].metric("预计批次数", estimate["batch_count"])
        columns[3].metric("实际发送批次", estimate["batch_count"] if not mock else 0)
        if estimate["sampled"]:
            st.warning(
                f"聊天记录较长，将按对话跨度均匀抽取 {estimate['message_count']} / "
                f"{estimate['total_messages']} 条消息，分 {estimate['batch_count']} 批生成。"
            )
        if mock:
            st.info(
                "当前离线演示模式：仅使用本地词面规则生成画像，不调用 DeepSeek API。",
                icon="🧪",
            )
        else:
            st.caption(
                f"API：{get_api_key_display(runtime.settings)} · "
                f"模型：{runtime.settings.deepseek_model}。"
                "生成画像会把分批次的目标人物聊天上下文发送给 DeepSeek。"
            )

        consent = True
        if not mock:
            consent = st.checkbox(
                "我理解生成画像会把上述聊天片段发送给 DeepSeek API，并确认有权处理这些内容。",
                value=False,
                key=f"profile_api_consent_{person['id']}",
            )

        if st.button(
            "重新生成画像" if record else "生成人物画像",
            type="primary",
            key=f"generate_profile_{person['id']}",
            disabled=not consent,
        ):
            if not mock and not runtime.settings.is_llm_configured:
                st.error(
                    "DeepSeek 未配置。请在 .env 中设置 Key 与模型，"
                    "或在侧边栏开启离线演示模式。"
                )
                return record
            progress_bar = st.progress(0.0, text="准备分批分析…")

            def on_progress(step: int, total: int, label: str) -> None:
                progress_bar.progress(
                    min(1.0, step / max(total, 1)),
                    text=label,
                )

            try:
                target_sender = (
                    str(person.get("target_sender") or "").strip()
                    or str(person.get("alias") or "").strip()
                    or person["name"]
                )
                profile, meta = build_profile(
                    messages=messages,
                    target_sender=target_sender,
                    settings=runtime.settings,
                    llm_client=runtime.llm,
                    mock=mock,
                    progress=on_progress,
                )
                saved = runtime.repository.save_profile(
                    person["id"],
                    profile,
                    provider=meta.get("provider", ""),
                    source_message_count=int(meta.get("total_messages", len(messages))),
                )
                record = saved
                memory_count = 0
                try:
                    memory_count = runtime.memory.sync_from_profile(
                        person["id"], profile
                    )
                except Exception as sync_exc:
                    st.warning(f"画像已保存，但同步记忆失败：{sync_exc}")
                progress_bar.progress(1.0, text="画像已保存")
                st.success(
                    f"画像已生成并保存（版本 {saved['version']}），"
                    f"同步 {memory_count} 条记忆。"
                )
                for warning in meta.get("warnings", []):
                    st.warning(warning)
            except ProfileBuildError as exc:
                st.error(f"画像生成失败：{exc}")
            except Exception as exc:
                st.error(f"画像生成失败：{type(exc).__name__}: {exc}")
    return record


def _chips(items: list[str]) -> None:
    if not items:
        st.caption("记录中未找到明确证据。")
        return
    tags = "".join(
        f'<span class="em-badge">{html.escape(str(item))}</span>'
        for item in items
    )
    st.markdown(tags, unsafe_allow_html=True)


def _render_profile_view(runtime, person: dict, record: dict) -> None:
    profile = record["data"]
    st.markdown("### 当前人物画像")
    meta_columns = st.columns(4)
    meta_columns[0].metric("画像版本", record["version"])
    meta_columns[1].caption(f"来源消息：{record['source_message_count']}")
    meta_columns[2].caption(f"生成方式：{record['provider'] or '未知'}")
    meta_columns[3].caption(f"更新：{format_timestamp(record['updated_at'])}")

    if profile_is_outdated(runtime.repository, person["id"]):
        st.warning(
            "导入的聊天数量与画像生成时不一致，建议重新生成画像以覆盖新增记录。",
            icon="⚠️",
        )

    st.markdown("#### 语言风格")
    style = profile.get("language_style", {})
    style_rows = [
        ("句子长度", style.get("sentence_length", "")),
        ("正式程度", style.get("formality", "")),
        ("语气", style.get("tone", "")),
        ("词汇习惯", style.get("vocabulary", "")),
    ]
    style_columns = st.columns(2)
    for index, (label, value) in enumerate(style_rows):
        with style_columns[index % 2]:
            st.markdown(f"**{label}**")
            st.write(value or "记录不足")

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown("**常用表达 / 口头禅**")
        _chips(profile.get("catchphrases", []))
        st.markdown("**标点习惯**")
        st.write(profile.get("punctuation_habits") or "记录不足")
        st.markdown("**Emoji 习惯**")
        st.write(profile.get("emoji_habits") or "记录不足")
    with detail_right:
        st.markdown("**情绪表达**")
        st.write(profile.get("emotional_expression") or "记录不足")
        st.markdown("**互动习惯**")
        _chips(profile.get("interaction_habits", []))
        st.markdown("**兴趣与话题**")
        _chips(profile.get("interests_and_topics", []))

    st.markdown("#### 共同经历（有原文证据）")
    experiences = profile.get("shared_experiences", [])
    if not experiences:
        st.caption("当前记录没有提取到有依据的共同经历。")
    for entry in experiences:
        with st.expander(f"· {entry.get('summary', '')[:80]}"):
            st.write(entry.get("summary", ""))
            st.caption(f"依据：{entry.get('evidence') or '模型未提供明确原文'}")

    st.markdown("#### 有原文支持的事实")
    facts = profile.get("supported_facts", [])
    if not facts:
        st.caption("当前记录没有提取到明确事实。")
    for entry in facts:
        with st.expander(f"· {entry.get('fact', '')[:80]}"):
            st.write(entry.get("fact", ""))
            st.caption(f"依据：{entry.get('evidence') or '模型未提供明确原文'}")

    uncertainties = profile.get("uncertainties", [])
    if uncertainties:
        st.markdown("#### 尚不确定的信息")
        for item in uncertainties:
            st.warning(item)

    st.info(profile.get("safety_notes") or "画像只是有限的风格总结，不代表真实人格。")

    with st.expander("编辑画像 JSON（高级）", expanded=False):
        st.caption(
            "保存后会校验结构，并自动用画像中的共同经历/事实重建“记忆库”。"
            "后续聊天会使用最新版本。"
        )
        current_json = json.dumps(profile, ensure_ascii=False, indent=2)
        editor_key = f"profile_json_text_{person['id']}_{record['version']}"
        if editor_key not in st.session_state:
            st.session_state[editor_key] = current_json
        edited = st.text_area(
            "画像 JSON",
            height=440,
            key=editor_key,
        )
        if st.button(
            "校验并保存画像",
            key=f"save_profile_json_{person['id']}_{record['version']}",
        ):
            try:
                parsed_json = json.loads(edited)
                nickname = str(parsed_json.get("nickname") or person["name"])
                normalized = validate_profile(parsed_json, nickname)
                saved = runtime.repository.save_profile(
                    person["id"],
                    normalized,
                    provider=record["provider"],
                    source_message_count=record["source_message_count"],
                )
                memory_count = runtime.memory.sync_from_profile(
                    person["id"], normalized
                )
                st.session_state.profile_flash = (
                    f"画像已保存（版本 {saved['version']}），"
                    f"同步 {memory_count} 条记忆。"
                )
                st.rerun()
            except json.JSONDecodeError as exc:
                st.error(f"JSON 格式错误：{exc}")
            except ProfileBuildError as exc:
                st.error(f"画像结构无效：{exc}")
            except Exception as exc:
                st.error(f"保存失败：{type(exc).__name__}: {exc}")

    action_left, action_right = st.columns([1, 1])
    with action_left:
        if st.button(
            "从当前画像同步记忆",
            key=f"sync_memories_{person['id']}",
        ):
            try:
                count = runtime.memory.sync_from_profile(person["id"], profile)
                st.success(f"已同步 {count} 条记忆。")
            except Exception as exc:
                st.error(f"同步失败：{exc}")
    with action_right:
        st.page_link("pages/4_专属聊天.py", label="进入专属聊天", icon="💬")
        st.page_link("pages/5_记忆管理.py", label="检查记忆", icon="🗂️")


def main() -> None:
    runtime = start_page("人物画像", "🪞")
    render_page_header(
        "人物画像",
        "画像只提取有证据支持的语言风格、互动习惯和共同经历。它不用于推断心理疾病、隐私或真实人格。",
    )
    _flash()

    person = select_person(runtime.repository)
    if not person:
        render_footer()
        return

    record = runtime.repository.get_profile_record(person["id"])
    record = _render_profile_generator(runtime, person, record)
    st.divider()
    if record:
        _render_profile_view(runtime, person, record)
    else:
        st.info(
            "这个人物还没有画像。生成后可以在此查看、编辑 JSON 并重新生成。"
        )
    render_footer()


if __name__ == "__main__":
    main()
