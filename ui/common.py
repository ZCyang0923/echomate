"""共享 UI 组件、导航、状态与样式。"""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Optional

import streamlit as st

from core.config import get_settings
from database.repositories import Repository
from ui.runtime import Runtime, get_runtime
from ui.theme import THEME_CSS

APP_NAME = "EchoMate"
APP_TAGLINE = "基于聊天记录的人格风格模拟与情感陪伴"

CSS = """
<style>
    :root {
        --ink: #16213B;
        --muted: #66748C;
        --line: #E4EAF3;
        --blue: #4F6BED;
        --teal: #1A9C91;
    }
    html, body, [class*="css"] {
        font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
                     "Segoe UI", Arial, sans-serif;
    }
    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(79,107,237,.07), transparent 28rem),
            radial-gradient(circle at 98% 12%, rgba(26,156,145,.06), transparent 26rem),
            #F6F8FC;
    }
    .block-container {
        max-width: 1360px;
        padding-top: 1.8rem;
        padding-bottom: 4rem;
    }
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 1.3rem;
    }
    .em-brand {
        display: flex;
        align-items: center;
        gap: .7rem;
        padding: .2rem 0 1rem;
    }
    .em-mark {
        display: grid;
        place-items: center;
        width: 2.5rem;
        height: 2.5rem;
        border-radius: 14px;
        background: linear-gradient(145deg, #4F6BED, #2F48B6);
        color: #fff;
        box-shadow: 0 8px 18px rgba(79,107,237,.25);
        font-size: 1.2rem;
    }
    .em-brand strong { display: block; color: var(--ink); font-size: 1.02rem; }
    .em-brand small {
        color: var(--muted);
        font-size: .68rem;
        letter-spacing: .06em;
    }
    .em-status {
        margin: .5rem 0 .8rem;
        padding: .85rem .95rem;
        border: 1px solid var(--line);
        border-radius: 13px;
        background: linear-gradient(155deg, #F8FAFF, #FFFFFF);
    }
    .em-status-label {
        color: var(--muted);
        font-size: .68rem;
        font-weight: 700;
        letter-spacing: .08em;
        text-transform: uppercase;
    }
    .em-status-main {
        margin-top: .25rem;
        color: var(--ink);
        font-size: .85rem;
        font-weight: 700;
        line-height: 1.45;
    }
    .em-status-meta {
        margin-top: .25rem;
        color: var(--muted);
        font-size: .72rem;
        line-height: 1.5;
        word-break: break-all;
    }
    .em-page-head {
        margin: .2rem 0 1.25rem;
        padding: 1.4rem 1.6rem;
        border: 1px solid #E4EAF3;
        border-radius: 18px;
        background:
            radial-gradient(circle at 92% 10%, rgba(79,107,237,.09), transparent 16rem),
            #FFFFFF;
        box-shadow: 0 8px 24px rgba(24,43,89,.045);
    }
    .em-page-head .eyebrow {
        color: var(--blue);
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    .em-page-head h1 {
        margin: .25rem 0 .35rem;
        color: var(--ink);
        font-size: clamp(1.55rem, 2.4vw, 2.05rem);
        letter-spacing: -.025em;
    }
    .em-page-head p {
        margin: 0;
        max-width: 55rem;
        color: var(--muted);
        font-size: .9rem;
        line-height: 1.65;
    }
    .em-hero {
        position: relative;
        overflow: hidden;
        margin-bottom: 1.35rem;
        padding: 2.5rem 2.5rem;
        border-radius: 22px;
        color: #fff;
        background:
            radial-gradient(circle at 86% 16%, rgba(91,220,204,.26), transparent 17rem),
            linear-gradient(120deg, #111C39 0%, #213363 55%, #3D5BCC 100%);
        box-shadow: 0 18px 44px rgba(26,43,91,.18);
    }
    .em-hero::after {
        content: "";
        position: absolute;
        right: -4rem;
        bottom: -9rem;
        width: 18rem;
        height: 18rem;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 50%;
    }
    .em-hero .kicker {
        color: #9FE3DB;
        font-size: .7rem;
        font-weight: 800;
        letter-spacing: .15em;
        text-transform: uppercase;
    }
    .em-hero h1 {
        margin: .55rem 0 .65rem;
        color: #fff;
        font-size: clamp(2rem, 3.4vw, 3.1rem);
        letter-spacing: -.04em;
        line-height: 1.12;
    }
    .em-hero h1 span { color: #B9C8FF; font-weight: 500; }
    .em-hero p {
        margin: 0;
        max-width: 49rem;
        color: #D9E3FF;
        line-height: 1.8;
        font-size: .96rem;
    }
    .em-tags { display: flex; gap: .45rem; flex-wrap: wrap; margin-top: 1.2rem; }
    .em-tags span {
        padding: .25rem .6rem;
        border: 1px solid rgba(255,255,255,.18);
        border-radius: 999px;
        background: rgba(255,255,255,.08);
        color: #EEF3FF;
        font-size: .7rem;
    }
    .em-card {
        height: 100%;
        padding: 1.15rem 1.2rem;
        border: 1px solid var(--line);
        border-radius: 15px;
        background: #FFFFFF;
        box-shadow: 0 7px 20px rgba(24,43,89,.035);
    }
    .em-card .num {
        color: var(--blue);
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .1em;
    }
    .em-card h3 { margin: .35rem 0 .3rem; color: var(--ink); font-size: 1rem; }
    .em-card p { margin: 0; color: var(--muted); font-size: .8rem; line-height: 1.65; }
    .em-disclaimer {
        padding: .85rem 1rem;
        border: 1px solid #F0DDA9;
        border-radius: 12px;
        background: #FFF9E9;
        color: #70551F;
        font-size: .8rem;
        line-height: 1.65;
    }
    .em-privacy {
        padding: .8rem .9rem;
        border: 1px solid #DDE7E5;
        border-radius: 12px;
        background: #F3FAF8;
        color: #3C615D;
        font-size: .74rem;
        line-height: 1.65;
    }
    .em-badge {
        display: inline-block;
        margin: 0 .2rem .25rem 0;
        padding: .16rem .5rem;
        border-radius: 999px;
        background: #EEF2FF;
        color: #4056B4;
        font-size: .68rem;
        font-weight: 700;
    }
    .em-muted { color: var(--muted); font-size: .8rem; line-height: 1.65; }
    [data-testid="stMetric"] {
        padding: .85rem 1rem;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #FFFFFF;
        box-shadow: 0 6px 17px rgba(24,43,89,.035);
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line) !important;
        border-radius: 15px;
    }
    .stButton > button, .stDownloadButton > button {
        border-radius: 9px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4F6BED, #3B55CF);
        border: none;
        box-shadow: 0 7px 16px rgba(79,107,237,.2);
    }
    [data-testid="stChatMessage"] {
        border-radius: 14px;
    }
    .app-footer {
        margin-top: 2.2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--line);
        color: #95A1B4;
        font-size: .72rem;
        text-align: center;
        line-height: 1.7;
    }
    @media (max-width: 760px) {
        .em-hero { padding: 1.5rem 1.25rem; border-radius: 18px; }
        .block-container { padding-top: 1rem; }
    }
</style>
"""


def setup_page(title: str, icon: str = "🫧") -> None:
    """所有页面统一入口。每个页面脚本必须先调用。"""
    st.set_page_config(
        page_title=f"{title} · {APP_NAME}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    settings = get_settings()
    defaults = {
        "active_person_id": None,
        "chat_session_id": None,
        "mock_mode": not settings.is_llm_configured,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not settings.is_llm_configured:
        st.session_state.mock_mode = True


def start_page(title: str, icon: str = "🫧") -> Runtime:
    """页面标准启动：配置、样式、运行时和侧边栏。"""
    setup_page(title, icon)
    try:
        runtime = get_runtime()
    except Exception as exc:
        st.error(
            "本地服务初始化失败。请检查依赖安装、.env 配置与 data/ 目录权限。"
            f"\n\n错误：{type(exc).__name__}: {exc}"
        )
        st.stop()
    render_sidebar(runtime, title)
    return runtime


def is_mock_mode() -> bool:
    return bool(st.session_state.get("mock_mode", True))


NAV_ITEMS = (
    ("home", "app.py", "首页", "⌂"),
    ("people", "pages/1_人物管理.py", "人物管理", "◎"),
    ("import", "pages/2_导入聊天记录.py", "导入聊天记录", "⇩"),
    ("profile", "pages/3_人物画像.py", "人物画像", "◇"),
    ("chat", "pages/4_专属聊天.py", "专属聊天", "◌"),
    ("memory", "pages/5_记忆管理.py", "记忆管理", "▤"),
)


def _active_nav_key(title: str) -> str:
    for key, _, label, _ in NAV_ITEMS:
        if title == label:
            return key
    return "home"


def _nav_style(active_key: str) -> str:
    rules = []
    for key, _, _, glyph in NAV_ITEMS:
        rules.append(
            f"[data-testid='stSidebar'] .st-key-em_nav_{key} "
            f"[data-testid='stPageLink-NavLink']::before {{ content: '{glyph}'; }}"
        )
    rules.append(
        f"[data-testid='stSidebar'] .st-key-em_nav_{active_key} "
        "[data-testid='stPageLink-NavLink'] {"
        " background: linear-gradient(95deg, #eaf3ff, #f2f8ff);"
        " color: var(--em-blue-deep);"
        " box-shadow: inset 0 0 0 1px rgba(93,124,246,.06);"
        " }"
    )
    rules.append(
        f"[data-testid='stSidebar'] .st-key-em_nav_{active_key} "
        "[data-testid='stPageLink-NavLink']::before { color: var(--em-blue); }"
    )
    rules.append(
        f"[data-testid='stSidebar'] .st-key-em_nav_{active_key} "
        "[data-testid='stPageLink-NavLink'] p { font-weight: 700; }"
    )
    return "<style>" + "".join(rules) + "</style>"


def render_sidebar(runtime: Runtime, active_title: str = "首页") -> None:
    settings = runtime.settings
    active_key = _active_nav_key(active_title)
    api_connected = settings.is_llm_configured
    api_state = "已连接" if api_connected else "未配置"
    api_class = "" if api_connected else " offline"
    model_line = settings.deepseek_model or "未设置模型"
    embedding_line = runtime.embedding.status_label()
    vector_line = runtime.vector_store.info.label

    with st.sidebar:
        st.markdown(
            """
            <div class="em-brand">
                <div class="em-brand-mark" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.65"
                         stroke-linecap="round" stroke-linejoin="round">
                        <rect x="4" y="6.5" width="16" height="12.5" rx="5"></rect>
                        <path d="M9 11.2h.01M15 11.2h.01"></path>
                        <path d="M9.5 15h5"></path>
                        <path d="M12 3.5v3"></path>
                        <circle cx="12" cy="3" r="1"></circle>
                    </svg>
                </div>
                <div>
                    <strong>EchoMate</strong>
                    <small>PERSONAL STYLE COMPANION</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="em-side-section-label">Workspace</div>', unsafe_allow_html=True)
        st.markdown(_nav_style(active_key), unsafe_allow_html=True)
        for key, page, label, _ in NAV_ITEMS:
            with st.container(key=f"em_nav_{key}"):
                st.page_link(page, label=label)

        st.divider()
        st.markdown('<div class="em-side-section-label">Runtime</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="em-status-card">
                <div class="em-status-title">
                    <span class="em-status-dot{api_class}"></span>
                    <span>DeepSeek</span>
                    <span class="em-status-pill{api_class}">{html.escape(api_state)}</span>
                </div>
                <div class="em-status-line"><span>模型</span><span>{html.escape(model_line)}</span></div>
                <div class="em-status-line"><span>Embedding</span><span>{html.escape(embedding_line)}</span></div>
                <div class="em-status-line"><span>向量库</span><span>{html.escape(vector_line)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if api_connected:
            if "mock_mode" not in st.session_state:
                st.session_state.mock_mode = False
            st.toggle(
                "离线演示模式",
                key="mock_mode",
                help="开启后不调用 DeepSeek，仅使用本地规则生成画像与回复。",
            )
        else:
            st.session_state.mock_mode = True
            st.toggle(
                "离线演示模式",
                value=True,
                disabled=True,
                key="mock_mode_disabled_display",
                help="缺少 API Key 时自动启用离线演示。",
            )
            st.caption("在 .env 中填写 Key 后重启，即可启用真实模型。")

        if runtime.embedding.is_fallback:
            st.caption("向量降级中：检索质量低于本地语义模型。")
        if runtime.vector_store.is_fallback:
            st.caption(runtime.vector_store.info.note or "当前使用 SQLite 向量降级。")

        st.divider()
        st.markdown(
            """
            <div class="em-side-note">
                <strong>本地优先</strong><br>
                聊天文件在本地解析；SQLite 与向量索引保存在 data/。
                调用 DeepSeek 时，画像、记忆和相关片段会发送到模型服务。
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("AI 模拟角色，不是真实人物本人。")


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        _clean_html(
            f"""
            <div class="em-page-head">
                <div class="eyebrow">EchoMate · private workspace</div>
                <div class="em-page-title">{html.escape(title)}</div>
                <div class="em-page-subtitle">{html.escape(subtitle)}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        """
        <div class="app-footer">
            EchoMate · 基于聊天记录的风格模拟与情感陪伴<br>
            AI 生成内容不构成对真实人物的复现。请妥善保管聊天数据与 API Key。
        </div>
        """,
        unsafe_allow_html=True,
    )


def select_person(
    repository: Repository,
    label: str = "当前人物",
    key: str = "global_person_selector",
) -> Optional[dict]:
    persons = repository.list_persons()
    if not persons:
        st.info("还没有人物档案。请先到「导入聊天记录」创建人物，或到「人物管理」手动创建。")
        st.session_state.active_person_id = None
        return None

    person_ids = [person["id"] for person in persons]
    if key in st.session_state and st.session_state[key] not in person_ids:
        del st.session_state[key]
    if key not in st.session_state:
        active = st.session_state.get("active_person_id")
        st.session_state[key] = active if active in person_ids else person_ids[0]

    previous = st.session_state.get("active_person_id")
    person_map = {person["id"]: person for person in persons}
    person_id = st.selectbox(
        label,
        options=person_ids,
        format_func=lambda value: _person_option_label(person_map[value]),
        key=key,
    )
    if previous and previous != person_id:
        st.session_state.chat_session_id = None
    st.session_state.active_person_id = person_id
    return person_map[person_id]


def _person_option_label(person: dict) -> str:
    suffix = []
    if person.get("message_count"):
        suffix.append(f"{person['message_count']} 条消息")
    if person.get("has_profile"):
        suffix.append("已有画像")
    return person["name"] + (f"（{' · '.join(suffix)}）" if suffix else "")


def format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def clear_person_widget_state(person_id: str) -> None:
    """删除人物后清理非组件状态；失效的 selector 会在下次渲染前被清理。"""
    if st.session_state.get("active_person_id") == person_id:
        st.session_state.active_person_id = None
    st.session_state.chat_session_id = None


def _clean_html(block: str) -> str:
    """Remove source indentation so Streamlit Markdown does not treat it as code."""
    return re.sub(r"(?m)^[ \t]+", "", block).strip()


def show_disclaimer() -> None:
    st.markdown(
        _clean_html(
            """
            <div class="em-disclaimer">
                <strong>重要边界：</strong>EchoMate 生成的是基于有限聊天记录的 AI 模拟角色，
                不是真实人物本人，也不代表对方的真实想法、意识或情感。请勿用它替代现实沟通。
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


_ICON_PATHS: dict[str, str] = {
    "home": (
        '<path d="M3.5 10.5 12 3.5l8.5 7"/>'
        '<path d="M5.5 9.4V20h13V9.4"/>'
        '<path d="M9.5 20v-5.2h5V20"/>'
    ),
    "people": (
        '<circle cx="9" cy="8" r="2.7"/>'
        '<path d="M3.8 19c.4-3.1 2.3-5 5.2-5s4.8 1.9 5.2 5"/>'
        '<path d="M16 5.5a2.4 2.4 0 0 1 0 4.7"/>'
        '<path d="M16.2 14.4c2.2.3 3.6 1.8 4 4.6"/>'
    ),
    "import": (
        '<path d="M12 3.5v10.2"/>'
        '<path d="m8.2 10 3.8 3.8 3.8-3.8"/>'
        '<path d="M4.5 15.5v4h15v-4"/>'
    ),
    "profile": (
        '<rect x="4" y="4" width="16" height="16" rx="3"/>'
        '<circle cx="12" cy="10" r="2.2"/>'
        '<path d="M8.3 17c.4-2.2 1.8-3.4 3.7-3.4s3.3 1.2 3.7 3.4"/>'
    ),
    "chat": (
        '<path d="M5 5.5h14v9.8H9.4L5 19z"/>'
        '<path d="M8.2 9.2h7.6M8.2 12h5.2"/>'
    ),
    "memory": (
        '<path d="M7 4.5h10a2 2 0 0 1 2 2v13H9a2 2 0 0 1-2-2z"/>'
        '<path d="M9.5 4.5v15M13 8h3.2M13 11h3.2"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5.5" rx="7" ry="3"/>'
        '<path d="M5 5.5v13c0 1.7 3.1 3 7 3s7-1.3 7-3v-13"/>'
        '<path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>'
    ),
    "shield": (
        '<path d="M12 3.5 19 6v5.4c0 4.2-2.8 7.6-7 9.1-4.2-1.5-7-4.9-7-9.1V6z"/>'
        '<path d="m9.3 12 1.8 1.8 3.6-3.8"/>'
    ),
    "spark": (
        '<path d="m12 3 1.5 5.1L19 9.5l-5.5 1.4L12 16l-1.5-5.1L5 9.5l5.5-1.4z"/>'
        '<path d="m18.5 15 .7 2.2 2.3.8-2.3.8-.7 2.2-.7-2.2-2.3-.8 2.3-.8z"/>'
    ),
    "arrow": '<path d="M5 12h13M13 6l6 6-6 6"/>',
    "page": '<path d="M5 4h9l5 5v11H5z"/><path d="M14 4v5h5"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 10.8v5M12 7.8h.01"/>',
    "lock": (
        '<rect x="5" y="10" width="14" height="10" rx="2.5"/>'
        '<path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10"/>'
    ),
    "chat_small": (
        '<path d="M5 6h14v9H9l-4 3.5z"/><path d="M8 9h8M8 12h5"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="2.7"/>'
        '<path d="M12 3.5v2M12 18.5v2M20.5 12h-2M5.5 12h-2'
        'M18 6l-1.4 1.4M7.4 16.6 6 18M18 18l-1.4-1.4M7.4 7.4 6 6"/>'
    ),
}


def icon_svg(name: str, size: int = 18) -> str:
    paths = _ICON_PATHS.get(name, _ICON_PATHS["spark"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.65" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def render_home_hero() -> None:
    st.markdown(
        _clean_html(
            """
            <section class="em-hero">
                <div class="em-hero-copy">
                    <div class="em-hero-kicker">EchoMate · Personal Style Companion</div>
                    <div class="em-hero-title">你好，<span>这是你的 AI 记忆空间</span></div>
                    <div class="em-hero-desc">
                        在这里，你可以导入聊天记录、构建人物画像、发现对话中的情绪与兴趣，
                        让每一次交流都更有意义。
                    </div>
                    <div class="em-hero-chips">
                        <a href="导入聊天记录">聊天记录分析</a>
                        <a href="人物画像">人物画像</a>
                        <a href="人物画像">情绪表达</a>
                        <a href="记忆管理">记忆管理</a>
                        <a href="专属聊天">专属聊天</a>
                    </div>
                </div>
                <div class="em-hero-art" aria-hidden="true">
                    <div class="em-sun"></div>
                    <div class="em-cloud c1"></div>
                    <div class="em-cloud c2"></div>
                    <div class="em-land one"></div>
                    <div class="em-land two"></div>
                    <div class="em-bot">
                        <div class="em-bot-antenna"></div>
                        <div class="em-bot-head"></div>
                        <div class="em-bot-body"></div>
                    </div>
                    <div class="em-better">Better<span>Together</span></div>
                </div>
            </section>
            """
        ),
        unsafe_allow_html=True,
    )


def render_stat_cards(stats: dict) -> None:
    items = (
        ("people", "人物档案", _safe_int(stats.get("person_count")), "已创建的人物", "violet"),
        ("chat", "已导入消息", _safe_int(stats.get("message_count")), "条聊天记录", "blue"),
        ("profile", "人物画像", _safe_int(stats.get("profile_count")), "已生成画像", "mint"),
        ("memory", "记忆条目", _safe_int(stats.get("memory_count")), "条可追溯记忆", "pink"),
    )
    cards = []
    for icon, label, value, note, tone in items:
        cards.append(
            _clean_html(
                f"""
                <div class="em-stat-card">
                    <div class="em-stat-icon em-tone-{tone}">{icon_svg(icon)}</div>
                    <div class="em-stat-copy">
                        <div class="em-stat-label">{html.escape(label)}</div>
                        <div class="em-stat-value">{value:,}</div>
                        <div class="em-stat-note">{html.escape(note)}</div>
                    </div>
                </div>
                """
            )
        )
    st.markdown(f'<div class="em-stat-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_section_heading(title: str, icon: str = "spark", note: str = "") -> None:
    note_html = f"<span>{html.escape(note)}</span>" if note else ""
    st.markdown(
        _clean_html(
            f"""
            <div class="em-section-heading">
                <span class="em-section-icon">{icon_svg(icon, 13)}</span>
                <div class="em-section-title">{html.escape(title)}</div>
                {note_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_action_grid() -> None:
    actions = (
        (
            "导入聊天记录",
            "上传 TXT / CSV，预览解析结果并建立档案",
            "导入聊天记录",
            "import",
            "violet",
        ),
        (
            "建立人物画像",
            "从聊天记录中提取语言风格与共同记忆",
            "人物画像",
            "profile",
            "mint",
        ),
        (
            "本地向量索引",
            "管理对话分块与语义检索，支持重建索引",
            "记忆管理",
            "database",
            "pink",
        ),
        (
            "开始专属聊天",
            "结合画像、记忆与历史片段开始对话",
            "专属聊天",
            "chat",
            "blue",
        ),
    )
    cards = []
    for title, desc, href, icon, tone in actions:
        cards.append(
            _clean_html(
                f"""
                <a class="em-action-card" href="{html.escape(href)}">
                    <span class="em-action-icon em-tone-{tone}">{icon_svg(icon)}</span>
                    <span class="em-action-copy">
                        <div class="em-action-title">{html.escape(title)}</div>
                        <div class="em-action-desc">{html.escape(desc)}</div>
                    </span>
                    <span class="em-action-arrow">›</span>
                </a>
                """
            )
        )
    st.markdown(f'<div class="em-action-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_status_panel(runtime: Runtime) -> None:
    connected = runtime.settings.is_llm_configured
    status_text = "已连接" if connected else "未配置"
    status_class = "ok" if connected else "warn"
    fallback_notes = []
    if runtime.embedding.is_fallback:
        fallback_notes.append("Embedding 正在使用降级路径。")
    if runtime.vector_store.is_fallback:
        fallback_notes.append("向量库正在使用 SQLite 降级。")
    fallback_html = (
        f'<div class="em-panel-sub" style="margin-top:.55rem;color:#b07d32">'
        f'{html.escape(" ".join(fallback_notes))}</div>'
        if fallback_notes
        else ""
    )
    st.markdown(
        f"""
        <div class="em-panel">
            <div class="em-panel-head">
                <span class="em-panel-icon">{icon_svg("settings", 15)}</span>
                <span class="em-panel-title">当前运行状态</span>
            </div>
            <div class="em-info-grid">
                <div class="em-info-row"><span>DeepSeek</span><span class="{status_class}">{status_text}</span></div>
                <div class="em-info-row"><span>模型</span><span>{html.escape(runtime.settings.deepseek_model or "未设置")}</span></div>
                <div class="em-info-row"><span>Embedding</span><span>{html.escape(runtime.embedding.status_label())}</span></div>
                <div class="em-info-row"><span>向量库</span><span>{html.escape(runtime.vector_store.info.label)}</span></div>
            </div>
            {fallback_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_privacy_panel() -> None:
    st.markdown(
        f"""
        <div class="em-panel">
            <div class="em-panel-head">
                <span class="em-panel-icon">{icon_svg("shield", 15)}</span>
                <span class="em-panel-title">数据安全与隐私</span>
            </div>
            <div class="em-panel-body">
                聊天档案与向量索引保存在本地 data/。调用 DeepSeek 时，
                仅发送当前问题、画像、记忆和检索到的相关片段。
            </div>
            <details class="em-details">
                <summary>了解更多</summary>
                <p>
                    原始聊天不会在每次聊天时整包发送；SQLite、Chroma 与上传文件
                    保存在本机 data/。删除人物会清空该人物的当前本地数据与索引。
                </p>
            </details>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quick_links() -> None:
    links = (
        ("人物画像", "查看人物画像", "profile"),
        ("记忆管理", "记忆条目管理", "memory"),
        ("导入聊天记录", "导入聊天记录", "import"),
        ("专属聊天", "开始专属聊天", "chat"),
    )
    rows = "".join(
        f'<a class="em-quick-link" href="{html.escape(href)}">'
        f'{icon_svg(icon, 14)}<span>{html.escape(label)}</span>'
        f'<span class="arrow">›</span></a>'
        for href, label, icon in links
    )
    st.markdown(
        f"""
        <div class="em-panel">
            <div class="em-panel-head">
                <span class="em-panel-icon">{icon_svg("spark", 15)}</span>
                <span class="em-panel-title">快速入口</span>
            </div>
            <div class="em-quick-list">{rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _recent_import_events(repository: Repository, limit: int = 3) -> list[dict]:
    events: list[dict] = []
    for person in repository.list_persons():
        for batch in repository.list_import_batches(person["id"]):
            events.append(
                {
                    "person": person["name"],
                    "count": _safe_int(batch.get("message_count")),
                    "file_name": str(batch.get("file_name") or ""),
                    "imported_at": str(batch.get("imported_at") or ""),
                }
            )
    events.sort(key=lambda item: item["imported_at"], reverse=True)
    return events[:limit]


def render_recent_imports(repository: Repository) -> None:
    events = _recent_import_events(repository)
    if not events:
        body = (
            '<div class="em-empty">还没有导入记录。'
            '<a href="导入聊天记录">导入第一份聊天记录</a>，开始建立记忆空间。</div>'
        )
    else:
        rows = []
        for event in events:
            rows.append(
                _clean_html(
                    f"""
                    <div class="em-activity-item">
                        <div class="em-activity-icon">{icon_svg("page", 13)}</div>
                        <div class="em-activity-main">
                            <div class="em-activity-title">{html.escape(event["person"])} · 导入 {event["count"]:,} 条</div>
                            <div class="em-activity-meta">{html.escape(event["file_name"] or "聊天记录")}</div>
                        </div>
                        <div class="em-activity-time">{html.escape(format_timestamp(event["imported_at"]))}</div>
                    </div>
                    """
                )
            )
        body = f'<div class="em-activity-list">{"".join(rows)}</div>'
    st.markdown(
        f"""
        <div class="em-panel">
            <div class="em-panel-head">
                <span class="em-panel-icon">{icon_svg("clock", 15)}</span>
                <span class="em-panel-title">最近动态</span>
                <span class="em-panel-sub">真实导入记录</span>
            </div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_quote_card() -> None:
    st.markdown(
        """
        <div class="em-quote-card">
            <p>“有些对话，<br>值得被记住。”</p>
            <small>— EchoMate</small>
        </div>
        """,
        unsafe_allow_html=True,
    )
