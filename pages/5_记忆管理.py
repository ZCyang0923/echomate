"""记忆管理页面。"""

from __future__ import annotations

import html

import streamlit as st

from core.import_service import (
    clear_person_content,
    delete_person_completely,
    profile_is_outdated,
)
from ui.common import (
    clear_person_widget_state,
    format_timestamp,
    render_footer,
    render_page_header,
    select_person,
    start_page,
)

MEMORY_KINDS = ["共同经历", "事实", "兴趣", "其他"]


def _flash() -> None:
    message = st.session_state.pop("memory_flash", "")
    if message:
        st.success(message)


def _render_profile_summary(runtime, person: dict) -> None:
    record = runtime.repository.get_profile_record(person["id"])
    if not record:
        st.info("这个人物还没有画像，记忆库可能为空。")
        st.page_link("pages/3_人物画像.py", label="去生成画像", icon="🪞")
        return
    profile = record["data"]
    style = profile.get("language_style", {})
    with st.container(border=True):
        st.markdown("### 当前画像摘要")
        if profile_is_outdated(runtime.repository, person["id"]):
            st.warning("画像生成后又有新消息导入，建议重新生成画像。")
        st.write(
            f"**语气：** {style.get('tone') or '记录不足'}　"
            f"**句子长度：** {style.get('sentence_length') or '记录不足'}"
        )
        if profile.get("catchphrases"):
            tags = "".join(
                f'<span class="em-badge">{html.escape(str(item))}</span>'
                for item in profile.get("catchphrases", [])
            )
            st.markdown(tags, unsafe_allow_html=True)
        st.caption(
            f"版本 {record['version']} · 更新 {format_timestamp(record['updated_at'])} · "
            f"来源消息 {record['source_message_count']}"
        )
        st.page_link("pages/3_人物画像.py", label="查看/编辑完整画像", icon="🪞")


def _render_index(runtime, person: dict) -> None:
    health = runtime.rag.index_health(person["id"])
    with st.container(border=True):
        st.markdown("### 本地索引")
        columns = st.columns(4)
        columns[0].metric("对话分块", health["chunk_count"])
        columns[1].metric("向量数量", health["vector_count"])
        columns[2].metric("索引状态", "正常" if health["healthy"] else "不一致")
        columns[3].metric("后端", health["backend"])
        if not health["healthy"]:
            st.warning(
                "分块数量与向量数量不一致，可能由 Embedding 后端切换或写入中断导致。"
                "请重建索引。"
            )
        if runtime.embedding.is_fallback:
            st.caption(
                "当前使用离线哈希向量降级，检索效果弱于 sentence-transformers 语义模型。"
            )
        if runtime.vector_store.is_fallback:
            st.caption(runtime.vector_store.info.note or "当前使用 SQLite 向量降级。")
        if st.button("重建此人物索引", key=f"rebuild_index_{person['id']}"):
            try:
                with st.spinner("正在重新分块、计算向量并写入本地索引…"):
                    report = runtime.rag.index_person(person["id"])
                st.success(
                    f"索引重建完成：{report.chunk_count} 个分块，"
                    f"{report.vector_count} 个向量。"
                )
            except Exception as exc:
                st.error(f"索引重建失败：{type(exc).__name__}: {exc}")


def _render_memories(runtime, person: dict) -> None:
    memories = runtime.repository.list_memories(person["id"])
    header_left, header_right = st.columns([2.2, 1])
    with header_left:
        st.markdown("### 已提取记忆")
        st.caption(
            "聊天时事实与共同经历以当前记忆库为准。删除错误的记忆可以避免它继续进入提示词。"
        )
    with header_right:
        if st.button(
            "从画像同步记忆",
            width="stretch",
            key=f"sync_from_profile_{person['id']}",
        ):
            record = runtime.repository.get_profile_record(person["id"])
            if not record:
                st.error("还没有人物画像，无法同步。")
            else:
                try:
                    count = runtime.memory.sync_from_profile(
                        person["id"], record["data"]
                    )
                    st.session_state.memory_flash = (
                        f"已根据画像重建 {count} 条记忆。"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"同步失败：{exc}")

    if not memories:
        st.info("暂无记忆。生成人物画像后会自动提取，或点击上方按钮同步。")
        return

    for memory in memories:
        updated = format_timestamp(memory.get("updated_at", ""))
        with st.expander(
            f"{memory.get('kind', '记忆')} · {memory.get('title', '')[:70]}",
            expanded=False,
        ):
            st.write(memory.get("content", ""))
            if memory.get("evidence"):
                st.caption(f"原文/证据：{memory.get('evidence')}")
            st.caption(
                f"来源：{memory.get('source', '')} · 更新时间：{updated} · "
                f"置信度：{float(memory.get('confidence', 0.5)):.2f}"
            )

            source_columns = st.columns([1, 1])
            with source_columns[0]:
                if st.button(
                    "查看相关历史原文",
                    key=f"memory_sources_button_{memory['id']}",
                ):
                    try:
                        with st.spinner("正在本地检索相关片段…"):
                            hits = runtime.memory.find_sources(
                                person["id"], memory, top_k=3
                            )
                    except Exception as exc:
                        st.error(f"检索失败：{exc}")
                        hits = []
                    if not hits:
                        st.info("没有检索到相关历史片段。")
                    for index, hit in enumerate(hits, start=1):
                        with st.container(border=True):
                            st.caption(
                                f"片段 {index} · 相似度 {hit.score:.3f}"
                            )
                            st.text(hit.text[:700])
            with source_columns[1]:
                st.caption("相关片段只来自导入的原始消息，不包含 AI 回复。")

            kind = st.selectbox(
                "类型",
                MEMORY_KINDS,
                index=(
                    MEMORY_KINDS.index(memory.get("kind"))
                    if memory.get("kind") in MEMORY_KINDS
                    else MEMORY_KINDS[-1]
                ),
                key=f"edit_memory_kind_{memory['id']}",
            )
            title = st.text_input(
                "标题",
                value=memory.get("title", ""),
                key=f"edit_memory_title_{memory['id']}",
            )
            content = st.text_area(
                "内容",
                value=memory.get("content", ""),
                height=90,
                key=f"edit_memory_content_{memory['id']}",
            )
            evidence = st.text_area(
                "原文证据",
                value=memory.get("evidence", ""),
                height=80,
                key=f"edit_memory_evidence_{memory['id']}",
            )
            if st.button(
                "保存记忆修改",
                key=f"save_memory_{memory['id']}",
            ):
                try:
                    runtime.memory.update_memory(
                        person_id=person["id"],
                        memory_id=memory["id"],
                        kind=kind,
                        title=title,
                        content=content,
                        evidence=evidence,
                    )
                    st.session_state.memory_flash = "记忆已更新，后续聊天会使用新内容。"
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存失败：{exc}")

            confirm = st.checkbox(
                "确认删除这条记忆",
                key=f"delete_memory_confirm_{memory['id']}",
            )
            if st.button(
                "删除记忆",
                disabled=not confirm,
                key=f"delete_memory_button_{memory['id']}",
            ):
                try:
                    runtime.memory.delete_memory(person["id"], memory["id"])
                    st.session_state.memory_flash = "记忆已删除。"
                    st.rerun()
                except Exception as exc:
                    st.error(f"删除失败：{exc}")


def _render_danger_zone(runtime, person: dict) -> None:
    st.markdown("### 危险操作")
    st.caption("以下操作会实际删除本地数据。请先阅读确认条件。")
    clear_col, delete_col = st.columns(2, gap="large")

    with clear_col:
        with st.container(border=True):
            st.markdown("#### 清空聊天数据（保留人物）")
            st.write(
                "删除该人物的导入消息、分块、向量、画像、全部会话和记忆，"
                "保留人物档案本身。"
            )
            clear_confirm = st.checkbox(
                "我理解该人物的聊天、画像和记忆将被清空",
                key=f"clear_content_confirm_{person['id']}",
            )
            clear_name = st.text_input(
                f"输入「{person['name']}」确认",
                key=f"clear_content_name_{person['id']}",
            )
            if st.button(
                "清空聊天与画像数据",
                type="primary",
                disabled=not (
                    clear_confirm and clear_name.strip() == person["name"]
                ),
                key=f"clear_content_button_{person['id']}",
            ):
                try:
                    clear_person_content(runtime.repository, runtime.rag, person["id"])
                    st.session_state.chat_session_id = None
                    st.session_state.memory_flash = "聊天、索引、画像、会话和记忆已清空。"
                    st.rerun()
                except Exception as exc:
                    st.error(f"清空失败：{exc}")

    with delete_col:
        with st.container(border=True):
            st.markdown("#### 删除人物及全部本地数据")
            st.write(
                "删除人物档案，并级联删除 SQLite 中的聊天、画像、会话、记忆，"
                "同时删除本地向量索引。不可恢复。"
            )
            delete_confirm = st.checkbox(
                "我理解人物档案及全部数据将被永久删除",
                key=f"delete_person_confirm_{person['id']}",
            )
            delete_name = st.text_input(
                f"再次输入「{person['name']}」确认",
                key=f"delete_person_name_{person['id']}",
            )
            if st.button(
                "永久删除人物",
                type="primary",
                disabled=not (
                    delete_confirm and delete_name.strip() == person["name"]
                ),
                key=f"delete_person_button_{person['id']}",
            ):
                try:
                    delete_person_completely(runtime.repository, runtime.rag, person["id"])
                    st.session_state.memory_flash = (
                        "人物及其全部本地数据已永久删除。"
                    )
                    clear_person_widget_state(person["id"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"删除失败：{exc}")


def main() -> None:
    runtime = start_page("记忆管理", "🗂️")
    render_page_header(
        "记忆管理",
        "查看画像、共同经历与事实来源；修正或删除错误记忆，并处理本地索引与人物数据。",
    )
    _flash()

    person = select_person(runtime.repository)
    if not person:
        render_footer()
        return

    stats = runtime.repository.person_stats(person["id"])
    columns = st.columns(4)
    columns[0].metric("导入消息", int(stats.get("message_count", 0)))
    columns[1].metric("记忆条目", int(stats.get("memory_count", 0)))
    columns[2].metric("会话", int(stats.get("session_count", 0)))
    columns[3].metric("画像", "已有" if stats.get("profile_updated_at") else "未生成")

    _render_profile_summary(runtime, person)
    _render_index(runtime, person)
    st.divider()
    _render_memories(runtime, person)
    st.divider()
    with st.container(key="danger_zone"):
        _render_danger_zone(runtime, person)

    st.caption("AI 回复不会自动写回记忆库；记忆只来自人物画像或用户编辑。")
    render_footer()


if __name__ == "__main__":
    main()
