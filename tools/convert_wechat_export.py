# -*- coding: utf-8 -*-
"""把 wechat-chat-export 的 TXT 导出转换为 EchoMate 支持的方括号格式。

这是一个独立工具，不读取微信数据库，也不上传任何内容。
输入格式（wechat-chat-export v1.4.0）：
    2025-08-30 13:18:07 | 周雨莎：瓦
输出格式（EchoMate 的 bracket_datetime 规则）：
    [2025-08-30 13:18] 周雨莎: 瓦
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

HEADER_PREFIX = "WeChat Chat Export for LLM"
MESSAGE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) \| (.*)$"
)
DATE_HEADER_RE = re.compile(r"^=+\s*(\d{4}-\d{2}-\d{2})\s*=+$")
TOTAL_RE = re.compile(r"^消息总数[：:]\s*(\d+)\s*$")
CONTINUATION_MARKER = " ⏎ "


@dataclass
class RawMessage:
    timestamp: datetime
    sender: str
    content: str
    source_line: int
    continuation_lines: int = 0


@dataclass
class ParsedExport:
    messages: list[RawMessage] = field(default_factory=list)
    declared_total: int | None = None
    metadata_lines: int = 0
    date_headers: int = 0
    blank_lines: int = 0
    continuation_lines: int = 0
    quote_lines: int = 0
    forwarded_lines: int = 0
    unattached: list[tuple[int, str]] = field(default_factory=list)
    malformed: list[tuple[int, str]] = field(default_factory=list)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_sender(body: str) -> tuple[str, str] | None:
    positions = [pos for pos in (body.find("："), body.find(":")) if pos >= 0]
    if not positions:
        return None
    pos = min(positions)
    sender = body[:pos].strip()
    if not sender:
        return None
    return sender, body[pos + 1 :]


def parse_export(path: Path) -> ParsedExport:
    text = path.read_bytes().decode("utf-8-sig")
    lines = text.splitlines()
    result = ParsedExport()
    current: RawMessage | None = None
    before_first_message = True

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            result.blank_lines += 1
            continue

        if DATE_HEADER_RE.match(stripped):
            result.date_headers += 1
            current = None
            before_first_message = False
            continue

        match = MESSAGE_RE.match(line)
        if match:
            before_first_message = False
            try:
                stamp = datetime.strptime(
                    f"{match.group(1)} {match.group(2)}", "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                result.malformed.append((lineno, "invalid timestamp"))
                current = None
                continue
            split = split_sender(match.group(3))
            if split is None:
                result.malformed.append((lineno, "missing sender separator"))
                current = None
                continue
            sender, content = split
            current = RawMessage(stamp, sender, content, lineno)
            result.messages.append(current)
            continue

        if before_first_message:
            # The upstream TXT starts with a five-line metadata header.
            result.metadata_lines += 1
            total = TOTAL_RE.match(stripped)
            if total:
                result.declared_total = int(total.group(1))
            continue

        if current is None:
            result.unattached.append((lineno, line[:80]))
            continue

        current.content += CONTINUATION_MARKER + line
        current.continuation_lines += 1
        result.continuation_lines += 1
        if line.startswith("    ↳ 引用"):
            result.quote_lines += 1
        else:
            result.forwarded_lines += 1

    return result


def choose_output_dir(parent: Path) -> Path:
    if not parent.exists():
        return parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = parent.parent / f"{parent.name}_{stamp}"
    suffix = 1
    while candidate.exists():
        candidate = parent.parent / f"{parent.name}_{stamp}_{suffix}"
        suffix += 1
    return candidate


def convert(input_path: Path, output_parent: Path) -> Path:
    if not input_path.is_file():
        raise FileNotFoundError(f"输入文件不存在：{input_path}")
    before = sha256(input_path)
    parsed = parse_export(input_path)
    if parsed.malformed or parsed.unattached:
        raise ValueError(
            "存在无法可靠解析的记录，已停止转换："
            f"malformed={len(parsed.malformed)}, unattached={len(parsed.unattached)}"
        )
    if parsed.declared_total is not None and parsed.declared_total != len(parsed.messages):
        raise ValueError(
            f"消息数量不一致：声明 {parsed.declared_total}，解析 {len(parsed.messages)}"
        )

    output_dir = choose_output_dir(output_parent)
    output_dir.mkdir(parents=True, exist_ok=False)
    output_path = output_dir / "chat_for_website.txt"
    with output_path.open("w", encoding="utf-8", newline="\n") as fh:
        for message in parsed.messages:
            fh.write(
                f"[{message.timestamp:%Y-%m-%d %H:%M}] "
                f"{message.sender}: {message.content}\n"
            )

    after = sha256(input_path)
    if before != after:
        raise RuntimeError("原始文件 SHA-256 在转换过程中发生变化")

    duplicates = 0
    seen = set()
    for m in parsed.messages:
        key = (m.timestamp.strftime("%Y-%m-%d %H:%M"), m.sender, m.content)
        if key in seen:
            duplicates += 1
        seen.add(key)

    report = f"""微信聊天记录转换报告
输入文件: {input_path}
输入 SHA-256（转换前）: {before}
输入 SHA-256（转换后）: {after}
原始文件未修改: {before == after}
输出文件: {output_path}
成功转换消息数: {len(parsed.messages)}
声明消息数: {parsed.declared_total}
忽略表头行: {parsed.metadata_lines}
日期分隔标题: {parsed.date_headers}
空行: {parsed.blank_lines}
无时间戳续行: {parsed.continuation_lines}
引用续行: {parsed.quote_lines}
转发卡片续行: {parsed.forwarded_lines}
异常/未转换消息: {len(parsed.malformed) + len(parsed.unattached)}
重复消息（按分钟/发送者/正文）: {duplicates}
换行处理: 原始续行用 {CONTINUATION_MARKER!r} 连接，保证一条消息一行
"""
    (output_dir / "conversion_report.txt").write_text(report, encoding="utf-8")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="转换 wechat-chat-export 的 TXT 为 EchoMate 方括号格式"
    )
    parser.add_argument("--input", required=True, help="外部工具导出的 chat_full_for_llm.txt")
    parser.add_argument(
        "--output-dir",
        default="converted_for_website",
        help="输出目录；已存在时自动追加时间戳，不覆盖",
    )
    args = parser.parse_args()
    output = convert(Path(args.input), Path(args.output_dir))
    print(f"输出目录: {output}")
    print(f"TXT: {output / 'chat_for_website.txt'}")
    print(f"报告: {output / 'conversion_report.txt'}")


if __name__ == "__main__":
    main()
