"""导入聊天记录页面。"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from core.chat_parser import (
    TXT_RULES,
    ParseResult,
    parse_csv,
    parse_txt,
    preview_txt,
    read_csv_preview,
    target_message_count,
    validate_file_size,
)
from core.errors import DuplicateImportError, ParserError
from core.import_service import compute_file_hash, import_chat
from ui.common import (
    render_footer,
    render_page_header,
    start_page,
)

SAMPLE_TXT = Path(__file__).resolve().parents[1] / "sample_data" / "demo_chat.txt"
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "sample_data" / "demo_chat.csv"


def _guess_column(columns: list[str], candidates: list[str], fallback: int = 0) -> str:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
        for column in columns:
            if candidate in column:
                return column
    return columns[min(fallback, len(columns) - 1)]


def _guess_optional_column(columns: list[str], candidates: list[str]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]
        for column in columns:
            if candidate in column:
                return column
    return None


def _reset_import_state() -> None:
    for key in (
        "import_parsed",
        "import_parsed_fingerprint",
        "import_payload",
        "import_file_name",
        "import_file_hash",
        "import_target_sender",
    ):
        st.session_state.pop(key, None)


def _render_parse_stats(parsed: ParseResult) -> None:
    stats = parsed.stats
    failed = int(stats.get("invalid_count", 0)) + int(
        stats.get("unmatched_lines", 0)
    )
    columns = st.columns(5)
    columns[0].metric("有效消息", int(stats.get("parsed_count", 0)))
    columns[1].metric("发送者", len(stats.get("sender_counts", {})))
    columns[2].metric("解析失败/未识别", failed)
    columns[3].metric("续行合并", int(stats.get("continuation_lines", 0)))
    columns[4].metric("编码", stats.get("encoding", parsed.encoding))
    st.caption(
        f"格式：{parsed.source_format} · 规则：{parsed.rule_label} · "
        f"原始非空行：{stats.get('total_input_rows', 0)} · "
        f"时间解析失败：{stats.get('timestamp_parse_failures', 0)}"
    )
    for warning in parsed.warnings:
        st.warning(warning)
    sender_rows = [
        {"发送者": sender, "消息数": int(count)}
        for sender, count in (stats.get("sender_counts") or {}).items()
    ]
    if sender_rows:
        st.dataframe(pd.DataFrame(sender_rows), hide_index=True, width="stretch")
    st.caption("解析结果预览（前 20 条）")
    st.dataframe(parsed.messages.head(20), hide_index=True, width="stretch")


def _render_import_result() -> bool:
    result = st.session_state.get("import_last_result")
    if not result:
        return False
    st.success(
        f"已导入 {result.message_count:,} 条消息，其中目标人物 "
        f"{result.target_message_count:,} 条。人物：{result.person_name}"
    )
    if result.index_error:
        st.warning(
            "消息已保存，但本地向量索引建立失败。请在「记忆管理」或人物页重建索引。"
            f"\n\n原因：{result.index_error}"
        )
    else:
        report = result.index_report
        st.caption(
            f"本地索引已建立：{report.chunk_count if report else 0} 个对话分块 · "
            f"{report.vector_count if report else 0} 个向量。"
        )
    columns = st.columns(3)
    columns[0].page_link(
        "pages/3_人物画像.py", label="下一步：生成画像", icon="🪞"
    )
    columns[1].page_link(
        "pages/4_专属聊天.py", label="查看专属聊天", icon="💬"
    )
    columns[2].page_link(
        "pages/5_记忆管理.py", label="检查记忆与索引", icon="🗂️"
    )
    if st.button("继续导入另一份记录", key="clear_import_result"):
        st.session_state.import_last_result = None
        st.rerun()
    st.divider()
    return True


def _current_file(consent: bool) -> tuple[bytes | None, str | None]:
    source = st.radio(
        "数据来源",
        ["上传文件", "内置示例 TXT", "内置示例 CSV"],
        horizontal=True,
        key="import_source",
        help="内置示例只包含虚构聊天，不包含任何真实私人记录。",
    )
    if source.startswith("内置示例"):
        sample_path = SAMPLE_TXT if source.endswith("TXT") else SAMPLE_CSV
        if not sample_path.exists():
            st.error(f"内置示例文件缺失，请检查 {sample_path.name}。")
            return None, None
        payload = sample_path.read_bytes()
        st.caption(f"已选择：`{sample_path.name}`（虚构演示数据）")
        return payload, sample_path.name

    uploaded = st.file_uploader(
        "上传 TXT / CSV",
        type=["txt", "csv"],
        disabled=not consent,
        help="第一版支持 UTF-8/GB18030 TXT 与 CSV，不解析微信/QQ 专有导出格式。",
    )
    if uploaded is None:
        st.info("请选择 TXT 或 CSV 文件。")
        return None, None
    return uploaded.getvalue(), uploaded.name


def _parse_fingerprint(file_hash: str, config: dict) -> str:
    raw = file_hash + "::" + repr(sorted(config.items()))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_preview(
    payload: bytes,
    file_name: str,
    consent: bool,
) -> None:
    extension = Path(file_name).suffix.lower()
    if extension == ".txt":
        text_preview, encoding = preview_txt(payload)
        with st.expander("原始 TXT 预览（前 40 行）", expanded=False):
            st.code(text_preview, language="text")
            st.caption(f"识别编码：{encoding}")

        rule_labels = {"auto": "自动识别"} | {
            rule.key: rule.label for rule in TXT_RULES
        }
        rule_labels["custom"] = "自定义正则"
        rule_key = st.selectbox(
            "TXT 解析规则",
            options=list(rule_labels.keys()),
            format_func=lambda value: rule_labels[value],
            help="无法自动识别时，请选择与导出格式匹配的规则或使用 CSV。",
        )
        custom_regex = ""
        if rule_key == "custom":
            custom_regex = st.text_area(
                "自定义正则",
                placeholder=r"^(?P<timestamp>.*?)\s+(?P<sender>[^:：]+)[:：]\s*(?P<content>.*)$",
                height=90,
                help="必须包含 (?P<sender>...) 与 (?P<content>...)，timestamp 可选。",
            )
        for rule in TXT_RULES:
            st.caption(f"· {rule.label}：{rule.description}")
        config = {"rule": rule_key, "regex": custom_regex}
        fingerprint = _parse_fingerprint(compute_file_hash(payload), config)
        if st.button("解析并预览", type="primary", key="parse_txt_button"):
            if not consent:
                st.error("请先确认你有权使用该聊天记录。")
                return
            try:
                parsed = parse_txt(payload, rule_key, custom_regex)
                st.session_state.import_parsed = parsed
                st.session_state.import_parsed_fingerprint = fingerprint
                st.rerun()
            except ParserError as exc:
                st.error(f"TXT 解析失败：{exc}")
            except Exception as exc:
                st.error(f"TXT 解析异常：{type(exc).__name__}: {exc}")
        return

    if extension == ".csv":
        try:
            preview, encoding = read_csv_preview(payload)
        except ParserError as exc:
            st.error(f"CSV 预览失败：{exc}")
            return
        with st.expander("原始 CSV 预览（前 100 行）", expanded=False):
            st.dataframe(preview, hide_index=True, width="stretch")
            st.caption(f"识别编码：{encoding} · 列数：{len(preview.columns)}")

        columns = list(preview.columns)
        if not columns:
            st.error("CSV 没有可用列。")
            return
        guessed_sender = _guess_column(
            columns, ["sender", "发送者", "昵称", "speaker", "from", "用户"]
        )
        guessed_content = _guess_column(
            columns, ["content", "消息内容", "内容", "message", "text", "消息"], 1
        )
        guessed_timestamp = _guess_optional_column(
            columns, ["timestamp", "时间", "time", "date", "日期"]
        )
        file_hash = compute_file_hash(payload)
        sender_key = f"csv_sender_{file_hash[:10]}"
        content_key = f"csv_content_{file_hash[:10]}"
        timestamp_key = f"csv_timestamp_{file_hash[:10]}"
        if sender_key not in st.session_state:
            st.session_state[sender_key] = guessed_sender
        if content_key not in st.session_state:
            st.session_state[content_key] = guessed_content
        if (
            sender_key in st.session_state
            and st.session_state[sender_key] not in columns
        ):
            del st.session_state[sender_key]
        if (
            content_key in st.session_state
            and st.session_state[content_key] not in columns
        ):
            del st.session_state[content_key]
        if (
            timestamp_key in st.session_state
            and st.session_state[timestamp_key] not in columns + ["__none__"]
        ):
            del st.session_state[timestamp_key]
        field_columns = st.columns(3)
        sender_column = field_columns[0].selectbox(
            "发送者字段",
            options=columns,
            key=sender_key,
        )
        content_column = field_columns[1].selectbox(
            "消息内容字段",
            options=columns,
            key=content_key,
        )
        timestamp_options = ["__none__"] + columns
        if timestamp_key not in st.session_state:
            st.session_state[timestamp_key] = (
                guessed_timestamp if guessed_timestamp else "__none__"
            )
        timestamp_column = field_columns[2].selectbox(
            "时间字段（可选）",
            options=timestamp_options,
            format_func=lambda value: "无时间字段" if value == "__none__" else value,
            key=timestamp_key,
        )
        config = {
            "sender": sender_column,
            "content": content_column,
            "timestamp": timestamp_column,
        }
        fingerprint = _parse_fingerprint(file_hash, config)
        if st.button("解析并预览", type="primary", key="parse_csv_button"):
            if not consent:
                st.error("请先确认你有权使用该聊天记录。")
                return
            try:
                parsed = parse_csv(
                    payload,
                    sender_column,
                    content_column,
                    None if timestamp_column == "__none__" else timestamp_column,
                )
                st.session_state.import_parsed = parsed
                st.session_state.import_parsed_fingerprint = fingerprint
                st.rerun()
            except ParserError as exc:
                st.error(f"CSV 解析失败：{exc}")
            except Exception as exc:
                st.error(f"CSV 解析异常：{type(exc).__name__}: {exc}")
        return

    st.error("仅支持 .txt 和 .csv 文件。")


def _render_destination(
    runtime,
    parsed: ParseResult,
    consent: bool,
) -> None:
    st.markdown("### 3. 选择模拟对象并确认导入")
    senders = list((parsed.stats.get("sender_counts") or {}).keys())
    if not senders:
        st.error("没有可选择的发送者。")
        return

    if (
        "import_target_sender" in st.session_state
        and st.session_state["import_target_sender"] not in senders
    ):
        del st.session_state["import_target_sender"]
    target_sender = st.selectbox(
        "要模拟的聊天对象",
        options=senders,
        format_func=lambda value: (
            f"{value} · {int((parsed.stats.get('sender_counts') or {}).get(value, 0))} 条"
        ),
        key="import_target_sender",
    )
    target_count = target_message_count(parsed, target_sender)
    if target_count < 3:
        st.warning(
            f"目标人物只有 {target_count} 条消息，生成画像和风格模拟可能不稳定。"
        )

    mode = st.radio(
        "写入哪个人物档案？",
        ["新建人物", "追加到已有"],
        horizontal=True,
        key="import_destination_mode",
    )
    persons = runtime.repository.list_persons()
    person_id = None
    person_name = target_sender
    alias = target_sender
    description = ""
    if mode == "新建人物":
        person_name = st.text_input(
            "新人物昵称",
            value=target_sender,
            key="import_new_person_name",
        )
        alias = st.text_input(
            "聊天别名",
            value=target_sender,
            key="import_new_person_alias",
        )
        description = st.text_input(
            "备注（可选）",
            placeholder="记录来源、关系等",
            key="import_new_person_desc",
        )
    else:
        if not persons:
            st.warning("目前没有可追加的人物档案，请选择“新建人物”。")
        else:
            person_map = {person["id"]: person for person in persons}
            if (
                "import_existing_person" in st.session_state
                and st.session_state["import_existing_person"] not in person_map
            ):
                del st.session_state["import_existing_person"]
            person_id = st.selectbox(
                "选择已有档案",
                options=list(person_map.keys()),
                format_func=lambda value: person_map[value]["name"],
                key="import_existing_person",
            )

    st.markdown(
        """
        <div class="em-privacy">
            <strong>确认后会发生什么：</strong>原始消息写入本机 SQLite；
            按连续对话窗口切分后建立本地向量索引。此步骤不会调用 DeepSeek API。
            只有后续生成人物画像或聊天时，才可能把相关片段发送给模型服务。
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("确认导入并建立索引", type="primary", key="confirm_import"):
        if not consent:
            st.error("请先确认你有权使用该聊天记录。")
            return
        if mode == "追加到已有" and not person_id:
            st.error("请选择一个已有的人物档案，或改为新建人物。")
            return
        payload = st.session_state.get("import_payload", b"")
        file_name = st.session_state.get("import_file_name", "chat.txt")
        file_hash = compute_file_hash(payload) if payload else ""
        try:
            with st.spinner("正在写入本地数据库并建立向量索引…"):
                result = import_chat(
                    repository=runtime.repository,
                    rag_service=runtime.rag,
                    parsed=parsed,
                    target_sender=target_sender,
                    person_id=person_id,
                    new_person_name=person_name,
                    alias=alias,
                    description=description,
                    file_name=file_name,
                    file_hash=file_hash,
                )
            st.session_state.import_last_result = result
            st.session_state.active_person_id = result.person_id
            st.session_state["global_person_selector"] = result.person_id
            st.session_state.import_parsed = None
            st.session_state.import_parsed_fingerprint = None
            st.rerun()
        except DuplicateImportError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"导入失败：{type(exc).__name__}: {exc}")


def main() -> None:
    runtime = start_page("导入聊天记录", "📥")
    render_page_header(
        "导入聊天记录",
        "只导入你有权使用的记录。先预览解析结果，再确认建立本地档案和索引。",
    )

    if _render_import_result():
        render_footer()
        return

    st.markdown("### 1. 使用授权")
    consent = st.checkbox(
        "我确认自己有权使用这份聊天记录，并理解生成画像/聊天时相关片段可能发送给 DeepSeek API。",
        value=False,
        key="import_consent",
    )
    if not consent:
        st.info("请先阅读并勾选使用授权，再开始上传。")
        render_footer()
        return

    st.markdown("### 2. 上传并解析")
    st.caption(
        f"单文件最大 {runtime.settings.max_upload_mb} MB。"
        "支持 UTF-8/GB18030 TXT 与 CSV。"
    )
    payload, file_name = _current_file(consent)
    if payload is None or file_name is None:
        render_footer()
        return

    try:
        validate_file_size(payload, runtime.settings.max_upload_bytes)
    except ParserError as exc:
        st.error(str(exc))
        render_footer()
        return

    file_hash = compute_file_hash(payload)
    if st.session_state.get("import_file_hash") != file_hash:
        st.session_state.import_file_hash = file_hash
        st.session_state.import_parsed = None
        st.session_state.import_parsed_fingerprint = None
        st.session_state.import_target_sender = None
    st.session_state.import_payload = payload
    st.session_state.import_file_name = file_name
    st.caption(f"文件：`{file_name}` · {len(payload) / 1024:.1f} KB")

    parsed = st.session_state.get("import_parsed")
    if parsed is None:
        _source_preview(payload, file_name, consent)
        parsed = st.session_state.get("import_parsed")
        if parsed is None:
            render_footer()
            return

    if st.button("清除解析结果并重新选择文件", key="reset_import_parse"):
        _reset_import_state()
        st.rerun()

    st.markdown("### 解析统计")
    _render_parse_stats(parsed)
    _render_destination(runtime, parsed, consent)
    render_footer()


if __name__ == "__main__":
    main()
