"""人物管理页面。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.import_service import delete_person_completely, profile_is_outdated
from ui.common import (
    format_timestamp,
    render_footer,
    render_page_header,
    select_person,
    start_page,
)


def _create_person(runtime) -> None:
    st.markdown("### 新建人物")
    with st.form("create_person_form", clear_on_submit=True):
        name = st.text_input("人物昵称 *", placeholder="例如：小满")
        alias = st.text_input("聊天中的昵称 / 别名", placeholder="可选")
        target_sender = st.text_input(
            "聊天记录中的发送者名",
            placeholder="可选；导入聊天记录时也可自动识别",
        )
        description = st.text_area(
            "备注",
            placeholder="这份档案代表谁？记录来源是什么？",
            height=90,
        )
        submitted = st.form_submit_button("创建人物", type="primary")
    if submitted:
        try:
            person = runtime.repository.create_person(
                name,
                alias,
                description,
                target_sender=target_sender,
            )
            st.session_state.active_person_id = person["id"]
            st.session_state["global_person_selector"] = person["id"]
            st.session_state.person_flash = "人物档案已创建。下一步可以导入聊天记录。"
            st.rerun()
        except Exception as exc:
            st.error(f"创建失败：{exc}")


def _edit_person(runtime, person: dict) -> None:
    st.markdown("#### 编辑档案")
    with st.form(f"edit_person_{person['id']}"):
        name = st.text_input(
            "人物昵称",
            value=person["name"],
            key=f"edit_name_{person['id']}",
        )
        alias = st.text_input(
            "聊天中的昵称 / 别名",
            value=person.get("alias", ""),
            key=f"edit_alias_{person['id']}",
        )
        description = st.text_area(
            "备注",
            value=person.get("description", ""),
            height=90,
            key=f"edit_desc_{person['id']}",
        )
        saved = st.form_submit_button("保存修改")
    if saved:
        try:
            runtime.repository.update_person(person["id"], name, alias, description)
            st.session_state.person_flash = "人物资料已更新。"
            st.rerun()
        except Exception as exc:
            st.error(f"保存失败：{exc}")


def _delete_person(runtime, person: dict) -> None:
    with st.expander("危险操作：删除人物及全部本地数据", expanded=False):
        st.warning(
            "将永久删除该人物的 SQLite 画像、导入消息、会话、记忆，"
            "以及对应的本地向量索引。此操作不可撤销。",
            icon="⚠️",
        )
        confirm = st.checkbox(
            "我理解上述数据会被永久删除",
            key=f"delete_check_{person['id']}",
        )
        typed = st.text_input(
            f"请输入人物昵称「{person['name']}」以确认",
            key=f"delete_name_{person['id']}",
        )
        if st.button(
            "永久删除人物",
            type="primary",
            disabled=not (confirm and typed.strip() == person["name"]),
            key=f"delete_button_{person['id']}",
        ):
            try:
                delete_person_completely(runtime.repository, runtime.rag, person["id"])
                st.session_state.active_person_id = None
                st.session_state.chat_session_id = None
                st.session_state.person_flash = (
                    "人物及其 SQLite 数据、会话和本地向量索引已删除。"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"删除失败：{exc}")


def main() -> None:
    runtime = start_page("人物管理", "👤")
    render_page_header(
        "人物管理",
        "一个聊天对象对应一个稳定的人物 ID。画像、会话、记忆与向量索引都按该 ID 隔离。",
    )
    flash = st.session_state.pop("person_flash", "")
    if flash:
        st.success(flash)

    with st.expander("新建人物档案", expanded=runtime.repository.global_stats().get("person_count", 0) == 0):
        _create_person(runtime)

    persons = runtime.repository.list_persons()
    if not persons:
        st.info("还没有人物。请先新建人物，或到「导入聊天记录」从聊天文件创建。")
        st.page_link("pages/2_导入聊天记录.py", label="去导入聊天记录", icon="📥")
        render_footer()
        return

    st.markdown("### 全部人物")
    table_rows = []
    for person in persons:
        stats = runtime.repository.person_stats(person["id"])
        table_rows.append(
            {
                "昵称": person["name"],
                "聊天别名": person.get("alias", ""),
                "聊天对象": person.get("target_sender", ""),
                "导入消息": int(stats.get("message_count", 0)),
                "画像": "已有" if person.get("has_profile") else "未生成",
                "记忆": int(stats.get("memory_count", 0)),
                "会话": int(stats.get("session_count", 0)),
                "最后导入": format_timestamp(stats.get("last_import_at", "")),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")

    selected = select_person(runtime.repository, label="选择要查看/编辑的人物")
    if not selected:
        render_footer()
        return
    stats = runtime.repository.person_stats(selected["id"])
    if profile_is_outdated(runtime.repository, selected["id"]):
        st.warning("导入消息数量与画像生成时的来源数量不一致，建议重新生成画像。")

    columns = st.columns(4)
    columns[0].metric("导入消息", int(stats.get("message_count", 0)))
    columns[1].metric("对话分块", int(stats.get("chunk_count", 0)))
    columns[2].metric("记忆条目", int(stats.get("memory_count", 0)))
    columns[3].metric("聊天会话", int(stats.get("session_count", 0)))

    edit_column, info_column = st.columns([1.35, 1], gap="large")
    with edit_column:
        _edit_person(runtime, selected)
    with info_column:
        st.markdown("#### 档案信息")
        st.write(f"**人物 ID：** `{selected['id']}`")
        st.write(f"**聊天对象：** {selected.get('target_sender') or '未绑定'}")
        st.write(f"**创建时间：** {format_timestamp(selected.get('created_at', ''))}")
        st.write(f"**更新时间：** {format_timestamp(selected.get('updated_at', ''))}")
        st.write(
            "**画像更新时间：** "
            + (
                format_timestamp(stats.get("profile_updated_at", ""))
                if stats.get("profile_updated_at")
                else "尚未生成"
            )
        )
        st.page_link(
            "pages/3_人物画像.py",
            label="查看/生成人物画像",
            icon="🪞",
        )
        st.page_link(
            "pages/4_专属聊天.py",
            label="进入专属聊天",
            icon="💬",
        )

    st.divider()
    with st.container(key="danger_zone"):
        _delete_person(runtime, selected)
    render_footer()


if __name__ == "__main__":
    main()
