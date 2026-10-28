# -*- coding: utf-8 -*-
from pathlib import Path

from tools.convert_wechat_export import convert


def test_convert_wechat_export_preserves_messages_and_hash(tmp_path: Path) -> None:
    source = tmp_path / "chat_full_for_llm.txt"
    source.write_text(
        "\n".join(
            [
                "WeChat Chat Export for LLM v1.4.0",
                "会话类型：私聊",
                "会话名称：测试对象",
                "消息总数：3",
                "==================================================",
                "",
                "========== 2025-08-30 ==========",
                "",
                "2025-08-30 13:18:07 | 小满：瓦",
                "2025-08-30 13:18:42 | 我：打工",
                "2025-08-30 13:18:49 | 小满：[动画表情]",
                "    ↳ 引用 小满：瓦",
                "阿远: [图片]",
                "",
            ]
        ),
        encoding="utf-8-sig",
    )
    before = source.read_bytes()

    output_dir = convert(source, tmp_path / "converted_for_website")
    output = output_dir / "chat_for_website.txt"
    lines = output.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 3
    assert lines[0] == "[2025-08-30 13:18] 小满: 瓦"
    assert lines[-1].startswith("[2025-08-30 13:18] 小满: [动画表情]")
    assert "↳ 引用 小满：瓦" in lines[-1]
    assert "阿远: [图片]" in lines[-1]
    assert "⏎" in output.read_text(encoding="utf-8")
    assert "==========" not in output.read_text(encoding="utf-8")
    assert not output.read_bytes().startswith(b"\xef\xbb\xbf")
    assert source.read_bytes() == before
    assert (output_dir / "conversion_report.txt").is_file()
