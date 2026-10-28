"""EchoMate 首页。"""

from __future__ import annotations

import streamlit as st

from ui.common import (
    render_action_grid,
    render_footer,
    render_home_hero,
    render_privacy_panel,
    render_quick_links,
    render_quote_card,
    render_recent_imports,
    render_section_heading,
    render_sidebar,
    render_stat_cards,
    render_status_panel,
    setup_page,
)
from ui.runtime import get_runtime


def main() -> None:
    setup_page("首页", "🫧")
    try:
        runtime = get_runtime()
    except Exception as exc:
        st.error(
            "服务初始化失败。请检查 .env、依赖安装与 data/ 目录权限。"
            f"\n\n错误：{type(exc).__name__}: {exc}"
        )
        st.stop()
    render_sidebar(runtime, "首页")

    render_home_hero()
    stats = runtime.repository.global_stats()
    render_stat_cards(stats)

    left, right = st.columns([1.62, 0.88], gap="large")
    with left:
        render_section_heading("功能入口", "spark", "选择你需要的功能")
        render_action_grid()
        st.markdown(
            """
            <div class="em-action-note">
                <strong>推荐路径</strong>　导入聊天记录 → 建立人物画像 → 在记忆管理中检查提取内容 → 开始专属聊天。
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_recent_imports(runtime.repository)
    with right:
        render_status_panel(runtime)
        render_privacy_panel()
        render_quick_links()
        render_quote_card()

    render_footer()


if __name__ == "__main__":
    main()
