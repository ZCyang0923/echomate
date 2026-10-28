"""专属聊天页面。"""

from __future__ import annotations

import streamlit as st

from core.import_service import profile_is_outdated
from ui.common import (
    format_timestamp,
    is_mock_mode,
    render_footer,
    render_page_header,
    select_person,
    show_disclaimer,
    start_page,
)


def _session_controls(runtime, person: dict) -> dict:
    sessions = runtime.repository.list_sessions(person["id"])
    if not sessions:
        runtime.repository.create_session(person["id"], "新的对话")
        sessions = runtime.repository.list_sessions(person["id"])
    valid_ids = [item["id"] for item in sessions]
    if st.session_state.get("chat_session_id") not in valid_ids:
        st.session_state.chat_session_id = sessions[0]["id"]
    select_key = f"chat_session_selector_{person['id']}"
    if select_key in st.session_state and st.session_state[select_key] not in valid_ids:
        del st.session_state[select_key]
    if select_key not in st.session_state:
        st.session_state[select_key] = st.session_state.chat_session_id

    selector_col, new_col, clear_col = st.columns([2.2, 0.9, 0.9])
    with selector_col:
        selected_id = st.selectbox(
            "会话",
            options=valid_ids,
            format_func=lambda value: _session_label(
                next(item for item in sessions if item["id"] == value)
            ),
            key=select_key,
        )
    st.session_state.chat_session_id = selected_id

    def _create_new_session() -> None:
        session = runtime.repository.create_session(person["id"], "新的对话")
        st.session_state.chat_session_id = session["id"]
        st.session_state[select_key] = session["id"]

    with new_col:
        st.button(
            "新建会话",
            icon="➕",
            width="stretch",
            key="new_chat_session",
            on_click=_create_new_session,
        )
    with clear_col:
        with st.popover("清空会话", icon="🧹", width="stretch"):
            st.warning("将删除当前会话内的所有用户消息与 AI 回复，不删除人物或历史记忆。")
            confirm = st.checkbox("确认清空", key=f"clear_chat_confirm_{selected_id}")
            if st.button(
                "执行清空",
                type="primary",
                disabled=not confirm,
                key=f"clear_chat_button_{selected_id}",
            ):
                runtime.repository.clear_session_messages(selected_id)
                st.session_state.chat_error = None
                st.rerun()

    return next(item for item in sessions if item["id"] == selected_id)


def _session_label(session: dict) -> str:
    title = str(session.get("title") or "新的对话")
    count = int(session.get("message_count") or 0)
    updated = format_timestamp(session.get("updated_at", ""))
    return f"{title} · {count} 条 · {updated}"


def _render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"本次参考的历史片段（{len(sources)} 段）", expanded=False):
        st.caption("以下内容来自导入的聊天记录，不是 AI 生成内容。")
        for index, source in enumerate(sources, start=1):
            score = float(source.get("score", 0.0))
            start = source.get("timestamp_start", "")
            end = source.get("timestamp_end", "")
            time_label = start if end in {"", start} else f"{start} → {end}"
            st.markdown(f"**片段 {index}** · 相似度 `{score:.3f}`")
            if time_label:
                st.caption(f"时间：{time_label}")
            st.text(source.get("snippet", ""))


def _render_messages(runtime, person: dict, session: dict) -> None:
    messages = runtime.repository.list_chat_messages(session["id"])
    if not messages:
        st.markdown(
            """
            <div class="em-privacy">
                <strong>这是 AI 模拟角色，不是真实人物本人。</strong><br>
                你发送的内容会结合人物画像、已确认记忆和相关的历史聊天片段。
                没有证据的事情，系统不应替你补全。
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("可以先说一句：今天有点累，想和你聊聊。")
        return

    for message in messages:
        role = message.get("role")
        with st.chat_message(role):
            if role == "assistant":
                label = f"{person['name']} · AI 模拟"
                if message.get("is_mock"):
                    label += " · 离线演示"
                st.caption(label)
            st.markdown(str(message.get("content") or ""))
            if role == "assistant":
                _render_sources(message.get("sources") or [])


def main() -> None:
    runtime = start_page("专属聊天", "💬")
    render_page_header(
        "专属聊天",
        "每次回复只携带人物画像、已确认记忆、与当前话题相关的历史片段和最近的当前会话。",
    )
    show_disclaimer()

    person = select_person(runtime.repository)
    if not person:
        render_footer()
        return

    profile_record = runtime.repository.get_profile_record(person["id"])
    if not profile_record:
        st.warning("这个人物还没有画像，无法进行风格化聊天。")
        st.page_link("pages/3_人物画像.py", label="先去生成画像", icon="🪞")
        render_footer()
        return

    if profile_is_outdated(runtime.repository, person["id"]):
        st.warning(
            "人物有新导入的聊天记录，当前画像可能未覆盖最新内容。"
            "可以继续聊天，或先重新生成画像。",
        )

    session = _session_controls(runtime, person)
    health = runtime.rag.index_health(person["id"])
    info_columns = st.columns(3)
    info_columns[0].metric("目标人物消息", runtime.repository.count_target_messages(person["id"]))
    info_columns[1].metric("已确认记忆", runtime.repository.count_memories(person["id"]))
    info_columns[2].metric("历史片段索引", health["vector_count"])

    if is_mock_mode():
        st.info(
            "当前离线演示模式：回复由本地规则生成，不调用 DeepSeek API。"
            "开启真实模型需要配置 .env 并在侧边栏关闭演示模式。",
            icon="🧪",
        )
    else:
        st.caption(
            f"当前模型：`{runtime.settings.deepseek_model}`。"
            "仅发送人物画像、当前记忆和检索到的片段，不发送完整原始文件。"
        )

    if not health["healthy"]:
        st.warning(
            "当前人物的分块数量与向量数量不一致，检索可能不完整。"
            "请到「记忆管理」重建索引。"
        )

    error = st.session_state.pop("chat_error", "")
    if error:
        st.error(error)
    notice = st.session_state.pop("chat_notice", "")
    if notice:
        st.warning(notice)

    _render_messages(runtime, person, session)

    prompt = st.chat_input(
        f"和「{person['name']}」的 AI 模拟角色说点什么…",
        key=f"chat_input_{session['id']}",
    )
    if prompt:
        before_count = runtime.repository.count_chat_messages(session["id"])
        try:
            with st.spinner("正在检索历史并生成回复…"):
                reply = runtime.chat.send_message(
                    person_id=person["id"],
                    session_id=session["id"],
                    user_message=prompt,
                    mock=is_mock_mode(),
                )
            if before_count == 0 and str(session.get("title")) == "新的对话":
                title = prompt.strip().replace("\n", " ")[:24] or "新的对话"
                runtime.repository.update_session_title(session["id"], title)
            if reply.retrieval_error:
                st.session_state.chat_notice = (
                    "本轮历史检索失败，回复未使用历史片段："
                    + reply.retrieval_error
                )
            st.rerun()
        except Exception as exc:
            st.session_state.chat_error = (
                "回复生成失败，但你的消息已保存。"
                f"（{type(exc).__name__}: {exc}）"
            )
            st.rerun()

    render_footer()


if __name__ == "__main__":
    main()
