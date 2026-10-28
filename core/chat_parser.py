"""TXT / CSV 聊天记录解析。

解析只负责把记录转换为 timestamp/sender/content 结构，不会把聊天内容当成
可执行指令。无法可靠识别的行会统计并提示，不做静默丢弃。
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from core.errors import ParserError

_INVISIBLE_CHARS = dict.fromkeys(
    map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None
)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class TxtRule:
    key: str
    label: str
    pattern: str
    description: str


TXT_RULES: tuple[TxtRule, ...] = (
    TxtRule(
        key="bracket_datetime",
        label="方括号时间 + 发送者",
        pattern=(
            r"^\[(?P<timestamp>[^\]]{4,40})\]\s*"
            r"(?P<sender>[^:：]{1,40})[:：]\s*(?P<content>.*)$"
        ),
        description="示例：[2024-05-01 20:15] 小满: 晚上好",
    ),
    TxtRule(
        key="datetime_sender",
        label="日期时间 + 发送者",
        pattern=(
            r"^(?P<timestamp>\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?"
            r"\s+\d{1,2}:\d{2}(?::\d{2})?)\s+"
            r"(?P<sender>[^:：]{1,40})[:：]\s*(?P<content>.*)$"
        ),
        description="示例：2024-05-01 20:15 小满: 晚上好",
    ),
    TxtRule(
        key="sender_only",
        label="仅发送者冒号",
        pattern=r"^(?P<sender>[^:：]{1,40})[:：]\s*(?P<content>.*)$",
        description="示例：小满: 晚上好（无时间戳）",
    ),
)

_RULE_BY_KEY = {rule.key: rule for rule in TXT_RULES}


@dataclass
class ParseResult:
    messages: pd.DataFrame
    stats: dict
    warnings: list[str] = field(default_factory=list)
    encoding: str = "utf-8"
    source_format: str = ""
    rule_label: str = ""


def decode_text(payload: bytes) -> tuple[str, str]:
    """按常见中文编码尝试解码，返回文本和实际编码。"""
    if not payload:
        raise ParserError("文件为空，未找到可解析内容。")
    errors: list[str] = []
    encodings = (
        ("utf-8-sig", "utf-8", "gb18030", "big5")
        if payload.startswith(bytes([0xEF, 0xBB, 0xBF]))
        else ("utf-8", "utf-8-sig", "gb18030", "big5")
    )
    for encoding in encodings:
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            errors.append(encoding)
            continue
        if not text.strip():
            raise ParserError("文件只有空白内容，未找到聊天消息。")
        return text, encoding
    raise ParserError(
        "无法识别文件编码，请另存为 UTF-8 或 GB18030 后再试。"
        f"（尝试过：{', '.join(errors)}）"
    )


def validate_file_size(payload: bytes, max_bytes: int) -> None:
    if len(payload) > max_bytes:
        raise ParserError(
            f"文件超过大小限制（{len(payload) / 1024 / 1024:.1f} MB > "
            f"{max_bytes / 1024 / 1024:.1f} MB）。"
        )


def _clean_text(value: object) -> str:
    text = str(value if value is not None else "").translate(_INVISIBLE_CHARS)
    text = _CONTROL_CHARS.sub("", text)
    return text.strip()


def _text_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["timestamp", "sender", "content"])
    if frame.empty:
        return frame
    frame["message_index"] = range(1, len(frame) + 1)
    return frame[["message_index", "timestamp", "sender", "content"]]


def _base_stats() -> dict:
    return {
        "total_input_rows": 0,
        "parsed_count": 0,
        "invalid_count": 0,
        "dropped_empty": 0,
        "unmatched_lines": 0,
        "continuation_lines": 0,
        "timestamp_parse_failures": 0,
        "encoding": "",
        "format": "",
        "rule": "",
        "sender_counts": {},
        "success_ratio": 0.0,
    }


def _read_csv_dataframe(
    text: str,
    nrows: Optional[int] = None,
) -> pd.DataFrame:
    """自动嗅探分隔符并读取 CSV；单列时回退到逗号。"""
    try:
        return pd.read_csv(
            io.StringIO(text),
            sep=None,
            engine="python",
            nrows=nrows,
            dtype=str,
            keep_default_na=False,
        )
    except (pd.errors.ParserError, csv.Error):
        return pd.read_csv(
            io.StringIO(text),
            sep=",",
            engine="python",
            nrows=nrows,
            dtype=str,
            keep_default_na=False,
        )


def read_csv_preview(payload: bytes, max_rows: int = 100) -> tuple[pd.DataFrame, str]:
    """读取 CSV 前若干行，用于字段映射预览。"""
    text, encoding = decode_text(payload)
    try:
        frame = _read_csv_dataframe(text, nrows=max_rows)
    except pd.errors.EmptyDataError as exc:
        raise ParserError("CSV 文件为空。") from exc
    except Exception as exc:
        raise ParserError(f"CSV 读取失败：{exc}") from exc
    if len(frame.columns) == 0:
        raise ParserError("CSV 中没有可用列。")
    return frame, encoding


def parse_csv(
    payload: bytes,
    sender_column: str,
    content_column: str,
    timestamp_column: Optional[str] = None,
) -> ParseResult:
    """按用户确认的字段映射解析 CSV。"""
    if not sender_column or not content_column:
        raise ParserError("请选择发送者字段和消息内容字段。")
    if sender_column == content_column:
        raise ParserError("发送者字段和消息内容字段不能相同。")
    if timestamp_column and timestamp_column in {sender_column, content_column}:
        raise ParserError("时间字段不能与发送者或内容字段相同。")

    preview, encoding = read_csv_preview(payload, max_rows=1)
    columns = list(preview.columns)
    for column, label in (
        (sender_column, "发送者"),
        (content_column, "消息内容"),
    ):
        if column not in columns:
            raise ParserError(f"CSV 中找不到{label}字段「{column}」。")
    if timestamp_column and timestamp_column not in columns:
        raise ParserError(f"CSV 中找不到时间字段「{timestamp_column}」。")

    text, encoding = decode_text(payload)
    try:
        raw = _read_csv_dataframe(text)
    except pd.errors.EmptyDataError as exc:
        raise ParserError("CSV 文件为空。") from exc
    except Exception as exc:
        raise ParserError(f"CSV 读取失败：{exc}") from exc

    total_rows = int(len(raw))
    rows: list[dict] = []
    invalid = 0
    timestamp_failures = 0
    for _, source in raw.iterrows():
        sender = _clean_text(source.get(sender_column, ""))
        content = _clean_text(source.get(content_column, ""))
        timestamp = _clean_text(
            source.get(timestamp_column, "") if timestamp_column else ""
        )
        if not sender or not content:
            invalid += 1
            continue
        if timestamp:
            parsed_time = pd.to_datetime(timestamp, errors="coerce")
            if pd.isna(parsed_time):
                timestamp_failures += 1
        rows.append(
            {
                "timestamp": timestamp,
                "sender": sender,
                "content": content,
            }
        )

    messages = _text_frame(rows)
    if messages.empty:
        raise ParserError(
            "CSV 中没有可用的聊天消息。请检查字段映射以及空消息。"
        )

    sender_counts = (
        messages["sender"].value_counts().astype(int).to_dict()
        if not messages.empty
        else {}
    )
    stats = _base_stats()
    stats.update(
        {
            "total_input_rows": total_rows,
            "parsed_count": int(len(messages)),
            "invalid_count": invalid,
            "dropped_empty": invalid,
            "timestamp_parse_failures": timestamp_failures,
            "encoding": encoding,
            "format": "CSV",
            "rule": "字段映射",
            "sender_counts": sender_counts,
            "success_ratio": len(messages) / total_rows if total_rows else 0.0,
        }
    )
    warnings: list[str] = []
    if invalid:
        warnings.append(f"有 {invalid} 行缺少发送者或内容，已在解析结果中排除。")
    if timestamp_failures:
        warnings.append(
            f"有 {timestamp_failures} 个时间值无法识别，将按原文本保留。"
        )
    if len(sender_counts) > 2:
        warnings.append(
            f"检测到 {len(sender_counts)} 个发送者，请确认要模拟的对象。"
        )
    if total_rows and len(messages) < total_rows * 0.5:
        warnings.append(
            "有效消息不足原始行数的一半，请重点检查字段映射与文件格式。"
        )
    return ParseResult(
        messages=messages,
        stats=stats,
        warnings=warnings,
        encoding=encoding,
        source_format="CSV",
        rule_label="字段映射",
    )


def preview_txt(payload: bytes, max_lines: int = 40) -> tuple[str, str]:
    text, encoding = decode_text(payload)
    lines = text.splitlines()[:max_lines]
    return "\n".join(lines), encoding


def _compile_pattern(pattern: str) -> re.Pattern:
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise ParserError(f"自定义 TXT 正则无法编译：{exc}") from exc
    if "sender" not in compiled.groupindex:
        raise ParserError("自定义正则必须包含命名分组 (?P<sender>...)。")
    if "content" not in compiled.groupindex:
        raise ParserError("自定义正则必须包含命名分组 (?P<content>...)。")
    return compiled


def _detect_rule(text: str) -> TxtRule:
    sample_lines = [
        line for line in text.splitlines()[:120] if line.strip()
    ]
    if not sample_lines:
        raise ParserError("TXT 文件没有可解析的非空行。")
    best_rule: Optional[TxtRule] = None
    best_score = 0.0
    for rule in TXT_RULES:
        pattern = re.compile(rule.pattern)
        matched = sum(1 for line in sample_lines if pattern.match(line))
        score = matched / len(sample_lines)
        if score > best_score:
            best_rule = rule
            best_score = score
    if best_rule is None or best_score < 0.2:
        raise ParserError(
            "未能可靠识别 TXT 格式。请选择手动格式规则，或改用 CSV 上传。"
        )
    return best_rule


def parse_txt(
    payload: bytes,
    rule_key: str = "auto",
    custom_regex: str = "",
) -> ParseResult:
    """解析 TXT 聊天记录。

    未匹配到新消息格式的非空行会作为上一条消息的续行附加，并计入
    continuation_lines，避免静默丢失。
    """
    text, encoding = decode_text(payload)
    if rule_key == "custom":
        if not custom_regex.strip():
            raise ParserError("请输入自定义正则表达式。")
        pattern = _compile_pattern(custom_regex.strip())
        rule_label = "自定义正则"
    elif rule_key == "auto":
        if custom_regex.strip():
            pattern = _compile_pattern(custom_regex.strip())
            rule_label = "自定义正则"
        else:
            rule = _detect_rule(text)
            pattern = re.compile(rule.pattern)
            rule_label = rule.label
    else:
        rule = _RULE_BY_KEY.get(rule_key)
        if not rule:
            raise ParserError("未知的 TXT 格式规则。")
        pattern = re.compile(rule.pattern)
        rule_label = rule.label

    raw_lines = text.splitlines()
    nonempty_lines = [line for line in raw_lines if line.strip()]
    rows: list[dict] = []
    unmatched = 0
    continuation = 0
    invalid = 0

    for line in raw_lines:
        if not line.strip():
            continue
        match = pattern.match(line)
        if match:
            groups = match.groupdict()
            sender = _clean_text(groups.get("sender", ""))
            content = _clean_text(groups.get("content", ""))
            timestamp = _clean_text(groups.get("timestamp", "") or "")
            if not sender or not content:
                invalid += 1
                continue
            rows.append(
                {
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                }
            )
            continue

        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if rows:
            previous = rows[-1]
            previous["content"] = f"{previous['content']}\n{cleaned}".strip()
            continuation += 1
        else:
            unmatched += 1

    messages = _text_frame(rows)
    if messages.empty:
        raise ParserError(
            "没有识别到聊天消息。请检查发送者与内容格式，或选择自定义正则。"
        )

    sender_counts = messages["sender"].value_counts().astype(int).to_dict()
    parsed_count = int(len(messages))
    stats = _base_stats()
    stats.update(
        {
            "total_input_rows": len(nonempty_lines),
            "parsed_count": parsed_count,
            "invalid_count": invalid,
            "dropped_empty": invalid,
            "unmatched_lines": unmatched,
            "continuation_lines": continuation,
            "timestamp_parse_failures": 0,
            "encoding": encoding,
            "format": "TXT",
            "rule": rule_label,
            "sender_counts": sender_counts,
            "success_ratio": (
                parsed_count / len(nonempty_lines) if nonempty_lines else 0.0
            ),
        }
    )

    warnings: list[str] = []
    if unmatched:
        warnings.append(
            f"有 {unmatched} 行在第一条消息之前无法识别，已忽略；"
            "建议检查格式或改用 CSV。"
        )
    if continuation:
        ratio = continuation / len(nonempty_lines) if nonempty_lines else 0.0
        warnings.append(
            f"有 {continuation} 行按续行合并到上一条消息（占非空行 {ratio:.0%}）。"
        )
        if ratio > 0.4:
            warnings.append(
                "续行比例较高，可能格式与所选规则不完全匹配，请先预览解析结果。"
            )
    if invalid:
        warnings.append(f"有 {invalid} 条消息发送者或内容为空，已清理。")
    if len(sender_counts) > 2:
        warnings.append(
            f"检测到 {len(sender_counts)} 个发送者，请确认要模拟的对象。"
        )
    if len(nonempty_lines) and parsed_count < len(nonempty_lines) * 0.3:
        warnings.append(
            "识别出的消息数偏少，可能只匹配了部分格式。请确认预览后再建立索引。"
        )
    return ParseResult(
        messages=messages,
        stats=stats,
        warnings=warnings,
        encoding=encoding,
        source_format="TXT",
        rule_label=rule_label,
    )


def target_message_count(parsed: ParseResult, target_sender: str) -> int:
    if parsed.messages.empty:
        return 0
    return int((parsed.messages["sender"] == target_sender).sum())


def make_import_records(
    messages: pd.DataFrame,
    target_sender: str,
) -> list[dict]:
    """把解析结果转换为入库记录，标记目标人物消息。"""
    if messages.empty:
        return []
    records: list[dict] = []
    for _, row in messages.iterrows():
        records.append(
            {
                "message_index": int(row["message_index"]),
                "timestamp": str(row.get("timestamp") or ""),
                "sender": str(row["sender"]),
                "content": str(row["content"]),
                "is_target": str(row["sender"]) == target_sender,
            }
        )
    return records
