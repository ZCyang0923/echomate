# -*- coding: utf-8 -*-
"""EchoMate 的统一视觉主题。

只负责 CSS 与少量语义化样式，不包含业务逻辑。
"""

THEME_CSS = """
<style>
:root {
    --em-bg: #f3f8fe;
    --em-bg-deep: #eaf3fc;
    --em-card: rgba(255, 255, 255, 0.94);
    --em-card-solid: #ffffff;
    --em-ink: #1c2d4d;
    --em-ink-soft: #4e607a;
    --em-muted: #8391a6;
    --em-line: #e2ebf6;
    --em-line-strong: #d3e1f2;
    --em-blue: #5d7cf6;
    --em-blue-deep: #4263db;
    --em-lavender: #8a88f5;
    --em-mint: #48b9ad;
    --em-pink: #ee9fba;
    --em-warm: #f6b86b;
    --em-danger: #d95c70;
    --em-radius-xl: 22px;
    --em-radius-lg: 17px;
    --em-radius: 13px;
    --em-radius-sm: 10px;
    --em-shadow: 0 12px 32px rgba(45, 78, 126, 0.06);
    --em-shadow-hover: 0 18px 40px rgba(45, 78, 126, 0.12);
    --em-transition: 180ms cubic-bezier(.2, .8, .2, 1);
    --em-font: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC",
               "Source Han Sans SC", "Segoe UI", Arial, sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--em-font);
}

.stApp {
    background:
        radial-gradient(1100px 540px at 14% -12%, rgba(164, 203, 255, .28), transparent 62%),
        radial-gradient(900px 520px at 96% 4%, rgba(189, 195, 255, .18), transparent 56%),
        var(--em-bg);
    color: var(--em-ink);
}

[data-testid="stAppViewContainer"] { background: transparent; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stDecoration"] { display: none; }

.block-container {
    max-width: 1420px;
    padding: 2rem 2.35rem 4.5rem;
}

.stMarkdown h3 {
    margin: 1rem 0 .65rem;
    color: var(--em-ink);
    font-size: 1.02rem;
    font-weight: 800;
    letter-spacing: -.02em;
}
.stMarkdown h4 {
    margin: .8rem 0 .5rem;
    color: #4c6380;
    font-size: .9rem;
    font-weight: 700;
}

p, li { color: var(--em-ink-soft); }

[data-testid="stCaptionContainer"] p {
    color: var(--em-muted);
    line-height: 1.65;
}

a { color: var(--em-blue-deep); }

/* ------------------------------------------------------------------
   Sidebar
   ------------------------------------------------------------------ */
[data-testid="stSidebar"] {
    width: 256px !important;
    min-width: 256px !important;
    max-width: 256px !important;
    background: rgba(255, 255, 255, .86);
    border-right: 1px solid var(--em-line);
    box-shadow: 6px 0 30px rgba(45, 78, 126, .025);
    backdrop-filter: blur(18px);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    width: 256px;
}
[data-testid="stSidebar"] .block-container {
    width: 100%;
    padding: 1.15rem .85rem 1.35rem;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: .18rem;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    margin: 0;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
    display: flex;
    align-items: center;
    gap: .62rem;
    min-height: 40px;
    padding: .58rem .72rem;
    border-radius: 11px;
    color: #596b82;
    text-decoration: none;
    transition: background var(--em-transition), color var(--em-transition);
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]::before {
    font-size: 1.08rem;
    line-height: 1;
    color: #8796aa;
    width: 1.25rem;
    text-align: center;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
    margin: 0;
    color: inherit;
    font-size: .89rem;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
    background: #f1f6fc;
    color: var(--em-blue-deep);
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover::before {
    color: var(--em-blue);
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:focus-visible {
    outline: 2px solid #a9c2fb;
    outline-offset: 1px;
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p {
    letter-spacing: .01em;
}

/* 由 render_sidebar 注入，按当前页面高亮 */
.em-nav-home [data-testid="stPageLink-NavLink"]::before { content: "⌂"; }
.em-nav-people [data-testid="stPageLink-NavLink"]::before { content: "◎"; }
.em-nav-import [data-testid="stPageLink-NavLink"]::before { content: "⇩"; }
.em-nav-profile [data-testid="stPageLink-NavLink"]::before { content: "◇"; }
.em-nav-chat [data-testid="stPageLink-NavLink"]::before { content: "◌"; }
.em-nav-memory [data-testid="stPageLink-NavLink"]::before { content: "▤"; }

[data-testid="stSidebar"] .em-nav-active [data-testid="stPageLink-NavLink"] {
    background: linear-gradient(95deg, #eaf3ff, #f2f8ff);
    color: var(--em-blue-deep);
    box-shadow: inset 0 0 0 1px rgba(93, 124, 246, .06);
}
[data-testid="stSidebar"] .em-nav-active [data-testid="stPageLink-NavLink"]::before {
    color: var(--em-blue);
    font-weight: 700;
}
[data-testid="stSidebar"] .em-nav-active [data-testid="stPageLink-NavLink"] p {
    font-weight: 700;
}
[data-testid="stSidebar"] hr {
    margin: .85rem 0;
    border-color: var(--em-line);
}

.em-brand {
    display: flex;
    align-items: center;
    gap: .72rem;
    padding: .25rem .45rem 1.15rem;
}
.em-brand-mark {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    flex: 0 0 42px;
    border-radius: 14px;
    color: #fff;
    background:
        radial-gradient(circle at 30% 18%, rgba(255,255,255,.65), transparent 30%),
        linear-gradient(145deg, #8f9cff 0%, #627df9 52%, #4b64d7 100%);
    box-shadow: 0 9px 20px rgba(93, 124, 246, .25);
}
.em-brand-mark svg { width: 27px; height: 27px; }
.em-brand strong {
    display: block;
    color: var(--em-ink);
    font-size: 1.02rem;
    line-height: 1.25;
    letter-spacing: -.015em;
}
.em-brand small {
    display: block;
    margin-top: .12rem;
    color: var(--em-muted);
    font-size: .64rem;
    line-height: 1.35;
    letter-spacing: .055em;
}
.em-side-section-label {
    margin: .2rem .55rem .45rem;
    color: #a0adc0;
    font-size: .62rem;
    font-weight: 800;
    letter-spacing: .13em;
    text-transform: uppercase;
}
.em-side-kicker {
    padding: .1rem .55rem .55rem;
    color: var(--em-muted);
    font-size: .68rem;
    line-height: 1.5;
}

.em-status-card {
    margin: .45rem 0 .8rem;
    padding: .9rem .82rem .8rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background:
        radial-gradient(circle at 90% 8%, rgba(152, 196, 255, .2), transparent 7rem),
        rgba(255, 255, 255, .8);
    box-shadow: var(--em-shadow);
}
.em-status-title {
    display: flex;
    align-items: center;
    gap: .38rem;
    color: var(--em-ink);
    font-size: .77rem;
    font-weight: 800;
}
.em-status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--em-mint);
    box-shadow: 0 0 0 4px rgba(72, 185, 173, .12);
}
.em-status-dot.offline { background: var(--em-warm); box-shadow: 0 0 0 4px rgba(246,184,107,.12); }
.em-status-pill {
    margin-left: auto;
    padding: .14rem .42rem;
    border-radius: 999px;
    background: #ecfaf7;
    color: #2f8d82;
    font-size: .61rem;
    font-weight: 700;
}
.em-status-pill.offline { background: #fff7e8; color: #ad7b2c; }
.em-status-line {
    display: flex;
    gap: .45rem;
    margin-top: .6rem;
    color: var(--em-muted);
    font-size: .68rem;
    line-height: 1.5;
}
.em-status-line span:first-child { flex: 0 0 3.45rem; color: #98a6b8; }
.em-status-line span:last-child {
    color: #4f6380;
    word-break: break-word;
}
.em-side-note {
    margin-top: .8rem;
    padding: .75rem .7rem;
    border: 1px solid #e4eef4;
    border-radius: var(--em-radius);
    background: #f7fbfd;
    color: #66808b;
    font-size: .68rem;
    line-height: 1.65;
}
.em-side-note strong { color: #3d6570; }

/* ------------------------------------------------------------------
   Shared surfaces
   ------------------------------------------------------------------ */
.em-page-head {
    position: relative;
    overflow: hidden;
    margin: .15rem 0 1.35rem;
    padding: 1.45rem 1.6rem 1.4rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-xl);
    background:
        radial-gradient(circle at 94% 5%, rgba(143, 183, 255, .19), transparent 18rem),
        linear-gradient(112deg, rgba(255,255,255,.98), rgba(247,251,255,.94));
    box-shadow: var(--em-shadow);
}
.em-page-head .eyebrow {
    color: var(--em-blue);
    font-size: .63rem;
    font-weight: 800;
    letter-spacing: .15em;
    text-transform: uppercase;
}
.em-page-head h1, .em-page-title {
    margin: .3rem 0 .35rem;
    color: var(--em-ink);
    font-size: clamp(1.55rem, 2.35vw, 2.05rem);
    line-height: 1.2;
}
.em-page-head p, .em-page-subtitle {
    max-width: 57rem;
    margin: 0;
    color: var(--em-ink-soft);
    font-size: .88rem;
    line-height: 1.7;
}

.em-panel {
    margin-bottom: .9rem;
    padding: 1rem 1rem .92rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background: var(--em-card);
    box-shadow: var(--em-shadow);
}
.em-panel-head {
    display: flex;
    align-items: center;
    gap: .55rem;
    margin-bottom: .65rem;
}
.em-panel-icon {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 9px;
    background: #eef4ff;
    color: var(--em-blue);
}
.em-panel-icon svg { width: 15px; height: 15px; }
.em-panel-title {
    color: var(--em-ink);
    font-size: .84rem;
    font-weight: 800;
    letter-spacing: -.01em;
}
.em-panel-sub {
    margin-left: auto;
    color: var(--em-muted);
    font-size: .64rem;
}
.em-panel-body {
    color: var(--em-ink-soft);
    font-size: .77rem;
    line-height: 1.72;
}
.em-panel-body strong { color: var(--em-ink); }

.em-info-grid {
    display: grid;
    gap: .55rem;
}
.em-info-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: .8rem;
    padding-bottom: .48rem;
    border-bottom: 1px dashed #ebf1f8;
    color: var(--em-muted);
    font-size: .7rem;
}
.em-info-row:last-child { border-bottom: 0; padding-bottom: 0; }
.em-info-row span:first-child { flex: 0 0 5.3rem; color: #96a4b6; }
.em-info-row span:last-child {
    color: #465a76;
    text-align: right;
    word-break: break-word;
}
.em-info-row .ok { color: #2e8e83; font-weight: 700; }
.em-info-row .warn { color: #b47a28; font-weight: 700; }

.em-empty {
    padding: 1.3rem 1.1rem;
    border: 1px dashed var(--em-line-strong);
    border-radius: var(--em-radius);
    background: rgba(249, 252, 255, .7);
    color: var(--em-muted);
    font-size: .8rem;
    line-height: 1.7;
    text-align: center;
}

.em-details {
    margin-top: .7rem;
    border-top: 1px solid var(--em-line);
    padding-top: .55rem;
}
.em-details summary {
    cursor: pointer;
    color: var(--em-blue-deep);
    font-size: .72rem;
    font-weight: 700;
}
.em-details p {
    margin: .5rem 0 0;
    color: var(--em-muted);
    font-size: .7rem;
    line-height: 1.7;
}

/* ------------------------------------------------------------------
   Home hero
   ------------------------------------------------------------------ */
.em-hero {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    min-height: 252px;
    margin: .15rem 0 1rem;
    padding: 2.1rem 2.25rem;
    border: 1px solid rgba(196, 219, 244, .8);
    border-radius: 25px;
    background:
        linear-gradient(180deg, rgba(211, 235, 255, .95) 0%, rgba(226, 244, 255, .92) 48%, rgba(238, 250, 246, .96) 100%);
    box-shadow: 0 18px 46px rgba(59, 107, 160, .10);
}
.em-hero::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -2;
    background:
        radial-gradient(ellipse at 82% 16%, rgba(255,255,255,.8) 0 8%, transparent 8.5%),
        radial-gradient(ellipse at 89% 13%, rgba(255,255,255,.6) 0 6%, transparent 6.5%),
        radial-gradient(ellipse at 13% 20%, rgba(255,255,255,.35) 0 10%, transparent 10.5%),
        linear-gradient(160deg, transparent 54%, rgba(181, 224, 206, .55) 54.5%, rgba(214, 241, 222, .55) 70%, transparent 70.5%);
}
.em-hero::after {
    content: "";
    position: absolute;
    z-index: -1;
    right: -4%;
    bottom: -58%;
    width: 58%;
    height: 105%;
    border-radius: 50% 50% 0 0;
    background:
        radial-gradient(ellipse at 45% 15%, rgba(255,255,255,.8) 0 4%, transparent 4.8%),
        linear-gradient(150deg, rgba(150, 201, 190, .32), rgba(211, 238, 222, .72));
    filter: blur(.2px);
}
.em-hero-copy {
    position: relative;
    z-index: 3;
    max-width: 58%;
}
.em-hero-kicker {
    color: #4e7098;
    font-size: .65rem;
    font-weight: 800;
    letter-spacing: .16em;
    text-transform: uppercase;
}
.em-hero h1,
.em-hero-title {
    margin: .55rem 0 .6rem;
    color: #18345c;
    font-size: clamp(2.05rem, 3.55vw, 3.15rem);
    font-weight: 800;
    line-height: 1.16;
    letter-spacing: -.045em;
}
.em-hero h1 span,
.em-hero-title span {
    display: block;
    color: #506b91;
    font-size: .66em;
    font-weight: 600;
    letter-spacing: -.025em;
}
.em-hero p,
.em-hero-desc {
    max-width: 43rem;
    margin: 0;
    color: #456586;
    font-size: .91rem;
    line-height: 1.8;
}
.em-hero-chips {
    display: flex;
    flex-wrap: wrap;
    gap: .45rem;
    margin-top: 1.15rem;
}
.em-hero-chips a {
    display: inline-flex;
    align-items: center;
    gap: .32rem;
    padding: .35rem .68rem;
    border: 1px solid rgba(117, 158, 199, .22);
    border-radius: 999px;
    background: rgba(255, 255, 255, .62);
    color: #4e6e91;
    font-size: .69rem;
    font-weight: 600;
    line-height: 1.2;
    text-decoration: none;
    transition: background var(--em-transition), transform var(--em-transition), border-color var(--em-transition);
}
.em-hero-chips a:hover {
    background: rgba(255, 255, 255, .92);
    border-color: rgba(93, 124, 246, .35);
    color: var(--em-blue-deep);
    transform: translateY(-1px);
}
.em-hero-chips a::before {
    content: "·";
    color: #8eb6d4;
    font-size: 1rem;
    line-height: .7;
}

.em-hero-art {
    position: absolute;
    z-index: 1;
    inset: 0;
    pointer-events: none;
}
.em-land {
    position: absolute;
    bottom: -18%;
    width: 58%;
    height: 54%;
    border-radius: 50% 50% 0 0;
    background: linear-gradient(155deg, rgba(166, 211, 191, .78), rgba(220, 242, 219, .35));
}
.em-land.one { right: -4%; transform: rotate(-7deg); }
.em-land.two {
    right: 16%;
    bottom: -26%;
    width: 45%;
    height: 48%;
    background: linear-gradient(160deg, rgba(155, 203, 191, .48), rgba(226, 245, 228, .25));
    transform: rotate(5deg);
}
.em-sun {
    position: absolute;
    top: 15%;
    right: 13%;
    width: 38px;
    height: 38px;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 35%, #fffdf5, #f8e9b5 72%);
    box-shadow: 0 0 0 14px rgba(255, 250, 219, .22), 0 0 36px rgba(255, 242, 187, .55);
}
.em-cloud {
    position: absolute;
    height: 14px;
    border-radius: 999px;
    background: rgba(255, 255, 255, .72);
    filter: blur(.1px);
}
.em-cloud::before, .em-cloud::after {
    content: "";
    position: absolute;
    bottom: 0;
    border-radius: 50%;
    background: inherit;
}
.em-cloud::before { width: 25px; height: 25px; left: 8px; }
.em-cloud::after { width: 17px; height: 17px; right: 9px; bottom: 2px; }
.em-cloud.c1 { top: 21%; left: 47%; width: 58px; opacity: .75; }
.em-cloud.c2 { top: 33%; right: 3%; width: 42px; opacity: .55; transform: scale(.8); }
.em-bot {
    position: absolute;
    right: 16%;
    bottom: 9%;
    width: 82px;
    height: 104px;
}
.em-bot-head {
    position: absolute;
    left: 12px;
    top: 16px;
    width: 58px;
    height: 52px;
    border-radius: 22px 22px 18px 18px;
    background: linear-gradient(155deg, #edf8ff, #b8d9f2);
    border: 1px solid rgba(111, 157, 195, .35);
    box-shadow: 0 12px 26px rgba(53, 106, 145, .16);
}
.em-bot-head::before, .em-bot-head::after {
    content: "";
    position: absolute;
    top: 23px;
    width: 5px;
    height: 7px;
    border-radius: 999px;
    background: #54728d;
}
.em-bot-head::before { left: 17px; }
.em-bot-head::after { right: 17px; }
.em-bot-body {
    position: absolute;
    left: 22px;
    bottom: 3px;
    width: 38px;
    height: 47px;
    border-radius: 15px 15px 20px 20px;
    background: linear-gradient(160deg, #d9f0fb, #aacde8);
    border: 1px solid rgba(111, 157, 195, .3);
}
.em-bot-antenna {
    position: absolute;
    left: 40px;
    top: 7px;
    width: 2px;
    height: 12px;
    background: #7da7c4;
}
.em-bot-antenna::before {
    content: "";
    position: absolute;
    top: -3px;
    left: -2px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #f3c89f;
}
.em-better {
    position: absolute;
    right: 4.5%;
    top: 20%;
    color: rgba(73, 105, 139, .58);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.05rem;
    font-style: italic;
    line-height: 1.2;
    transform: rotate(-6deg);
}
.em-better span { display: block; padding-left: 1.2rem; font-size: .8rem; }

/* ------------------------------------------------------------------
   Stat and action cards
   ------------------------------------------------------------------ */
.em-stat-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: .85rem;
    margin: .25rem 0 1.35rem;
}
.em-stat-card {
    display: flex;
    align-items: flex-start;
    gap: .72rem;
    min-height: 94px;
    padding: 1rem .95rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background: var(--em-card);
    box-shadow: var(--em-shadow);
}
.em-stat-icon {
    display: grid;
    place-items: center;
    flex: 0 0 34px;
    width: 34px;
    height: 34px;
    border-radius: 10px;
}
.em-stat-icon svg { width: 18px; height: 18px; }
.em-tone-violet { background: #f0efff; color: #7b7af0; }
.em-tone-blue { background: #edf4ff; color: #5d7cf6; }
.em-tone-mint { background: #ebfaf6; color: #3cae9c; }
.em-tone-pink { background: #fff0f4; color: #d88aa6; }
.em-stat-copy { min-width: 0; }
.em-stat-label {
    margin-top: .06rem;
    color: var(--em-muted);
    font-size: .7rem;
    line-height: 1.35;
}
.em-stat-value {
    margin-top: .12rem;
    color: var(--em-ink);
    font-size: 1.62rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -.055em;
}
.em-stat-note {
    margin-top: .22rem;
    color: #9aa8ba;
    font-size: .62rem;
    line-height: 1.35;
}

.em-section-heading {
    display: flex;
    align-items: center;
    gap: .5rem;
    margin: .4rem 0 .72rem;
}
.em-section-heading .em-section-icon {
    display: grid;
    place-items: center;
    width: 22px;
    height: 22px;
    border-radius: 7px;
    background: #eef4ff;
    color: var(--em-blue);
}
.em-section-heading svg { width: 13px; height: 13px; }
.em-section-heading h2,
.em-section-title {
    margin: 0;
    color: var(--em-ink);
    font-size: .98rem;
    font-weight: 800;
    letter-spacing: -.02em;
}
.em-section-heading span {
    color: var(--em-muted);
    font-size: .65rem;
}
.em-section-heading > span:last-child {
    margin-left: auto;
}

.em-action-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: .8rem;
}
.em-action-card {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: .7rem;
    min-height: 104px;
    padding: .95rem .95rem;
    border: 1px solid rgba(224, 235, 247, .95);
    border-radius: var(--em-radius-lg);
    background: rgba(255, 255, 255, .72);
    color: var(--em-ink);
    text-decoration: none !important;
    box-shadow: 0 5px 18px rgba(45, 78, 126, .025);
    transition: transform var(--em-transition), box-shadow var(--em-transition), border-color var(--em-transition), background var(--em-transition);
}
.em-action-card:hover {
    transform: translateY(-2px);
    border-color: #c8d9ef;
    background: #fff;
    box-shadow: var(--em-shadow-hover);
}
.em-action-icon {
    display: grid;
    place-items: center;
    flex: 0 0 38px;
    width: 38px;
    height: 38px;
    border-radius: 12px;
}
.em-action-icon svg { width: 19px; height: 19px; }
.em-action-copy { min-width: 0; padding-right: .75rem; }
.em-action-copy h3,
.em-action-title {
    margin: .03rem 0 .25rem;
    color: var(--em-ink);
    font-size: .84rem;
    font-weight: 800;
    line-height: 1.35;
}
.em-action-copy p,
.em-action-desc {
    margin: 0;
    color: #7b8ba1;
    font-size: .7rem;
    line-height: 1.55;
}
.em-action-arrow {
    position: absolute;
    right: .78rem;
    top: .82rem;
    color: #aab7c8;
    font-size: 1rem;
    line-height: 1;
    transition: color var(--em-transition), transform var(--em-transition);
}
.em-action-card:hover .em-action-arrow {
    color: var(--em-blue);
    transform: translateX(2px);
}
.em-action-note {
    margin: .8rem 0 0;
    padding: .7rem .85rem;
    border: 1px solid #e9f0f8;
    border-radius: 12px;
    background: #fbfdff;
    color: #7b8ba1;
    font-size: .7rem;
    line-height: 1.65;
}
.em-action-note strong { color: #536b8a; }

.em-quick-list { display: grid; gap: .18rem; }
.em-quick-link {
    display: flex;
    align-items: center;
    gap: .55rem;
    padding: .54rem .4rem;
    border-radius: 9px;
    color: #536a87 !important;
    font-size: .73rem;
    text-decoration: none !important;
    transition: background var(--em-transition), color var(--em-transition);
}
.em-quick-link:hover { background: #f3f8ff; color: var(--em-blue-deep) !important; }
.em-quick-link svg { width: 14px; height: 14px; color: #8aa2c0; }
.em-quick-link .arrow { margin-left: auto; color: #b3c0cf; font-size: .9rem; }
.em-quick-link:hover .arrow { color: var(--em-blue); }

.em-activity-list { display: grid; gap: .08rem; }
.em-activity-item {
    display: flex;
    align-items: flex-start;
    gap: .55rem;
    padding: .6rem .25rem;
    border-bottom: 1px solid #eef3f9;
}
.em-activity-item:last-child { border-bottom: 0; }
.em-activity-icon {
    display: grid;
    place-items: center;
    flex: 0 0 25px;
    width: 25px;
    height: 25px;
    border-radius: 8px;
    background: #f0f5fc;
    color: #8ba4c1;
}
.em-activity-icon svg { width: 13px; height: 13px; }
.em-activity-main { min-width: 0; }
.em-activity-title {
    color: #506783;
    font-size: .7rem;
    font-weight: 600;
    line-height: 1.45;
}
.em-activity-meta {
    margin-top: .1rem;
    color: #9aa8ba;
    font-size: .62rem;
    line-height: 1.4;
}
.em-activity-time {
    margin-left: auto;
    flex: 0 0 auto;
    color: #a7b3c3;
    font-size: .6rem;
}

.em-quote-card {
    position: relative;
    overflow: hidden;
    min-height: 92px;
    margin-top: .85rem;
    padding: .9rem .85rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background:
        linear-gradient(125deg, rgba(219, 239, 235, .75), rgba(245, 250, 255, .85)),
        #fff;
}
.em-quote-card::after {
    content: "";
    position: absolute;
    right: -35px;
    bottom: -35px;
    width: 130px;
    height: 90px;
    border-radius: 50% 50% 0 0;
    background: rgba(160, 208, 194, .3);
}
.em-quote-card p {
    position: relative;
    z-index: 1;
    margin: 0;
    color: #587a85;
    font-family: Georgia, "Times New Roman", serif;
    font-size: .78rem;
    font-style: italic;
    line-height: 1.65;
}
.em-quote-card small {
    position: relative;
    z-index: 1;
    display: block;
    margin-top: .35rem;
    color: #8aa6aa;
    font-size: .6rem;
    text-align: right;
}

/* ------------------------------------------------------------------
   Streamlit controls
   ------------------------------------------------------------------ */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    min-height: 39px;
    padding: .38rem .85rem;
    border: 1px solid var(--em-line-strong);
    border-radius: 10px;
    background: #fff;
    color: #4d6280;
    font-size: .8rem;
    font-weight: 600;
    box-shadow: none;
    transition: background var(--em-transition), border-color var(--em-transition), color var(--em-transition), transform var(--em-transition);
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    border-color: #b9cdf0;
    background: #f7faff;
    color: var(--em-blue-deep);
}
.stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(1px); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    border: 0;
    background: linear-gradient(135deg, #6a86fb, #4c68df);
    color: #fff;
    box-shadow: 0 8px 18px rgba(93, 124, 246, .18);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #7690ff, #4160d5);
    color: #fff;
}
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 2px solid #a9c2fb;
    outline-offset: 2px;
}

[data-testid="stForm"] {
    padding: 1.05rem 1.1rem .95rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background: rgba(255, 255, 255, .72);
    box-shadow: 0 7px 22px rgba(45, 78, 126, .025);
}
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputRootElement"],
[data-testid="stTextAreaRootElement"],
[data-testid="stDateInputRootElement"],
[data-baseweb="input"],
[data-baseweb="textarea"] {
    border: 1px solid var(--em-line-strong) !important;
    border-radius: 10px !important;
    background: #fbfdff !important;
    box-shadow: none !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputRootElement"]:focus-within,
[data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stDateInputRootElement"]:focus-within {
    border-color: #a9c2fb !important;
    box-shadow: 0 0 0 3px rgba(93, 124, 246, .09) !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input {
    min-height: 40px;
    border: 0 !important;
    border-radius: 10px;
    background: transparent !important;
    color: var(--em-ink);
    font-size: .82rem;
}
[data-testid="stTextArea"] textarea { padding: .65rem .7rem; }
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stDateInput"] input:focus {
    border-color: #a9c2fb !important;
    box-shadow: 0 0 0 3px rgba(93, 124, 246, .09);
    background: #fff;
}
[data-baseweb="select"] > div {
    min-height: 40px;
    border-radius: 10px !important;
    border-color: var(--em-line-strong) !important;
    background: #fbfdff !important;
    font-size: .82rem;
}
[data-testid="stCheckbox"] label, [data-testid="stToggle"] label {
    color: #5e728d;
    font-size: .78rem;
    line-height: 1.55;
}
[data-testid="stToggle"] [data-baseweb="checkbox"] { transform: scale(.88); transform-origin: left center; }
[data-testid="stFileUploaderDropzone"] {
    padding: 1.1rem 1rem;
    border: 1.5px dashed #c9dbf1;
    border-radius: var(--em-radius-lg);
    background: linear-gradient(145deg, #fbfdff, #f6faff);
    transition: border-color var(--em-transition), background var(--em-transition);
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #a8c4ef;
    background: #f9fcff;
}
[data-testid="stFileUploaderDropzone"] button {
    border-radius: 9px;
    border-color: #c9dbf1;
    background: #fff;
}

[data-testid="stMetric"] {
    min-height: 80px;
    padding: .8rem .88rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius);
    background: var(--em-card);
    box-shadow: 0 5px 16px rgba(45, 78, 126, .025);
}
[data-testid="stMetricLabel"] p { color: var(--em-muted); font-size: .7rem; }
[data-testid="stMetricValue"] {
    color: var(--em-ink);
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -.04em;
}
[data-testid="stMetricDelta"] { font-size: .68rem; }

[data-testid="stExpander"] details {
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius);
    background: rgba(255, 255, 255, .78);
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    min-height: 42px;
    padding: .5rem .75rem;
    color: #4f6685;
    font-size: .78rem;
    font-weight: 600;
}
[data-testid="stExpander"] summary:hover { background: #f8fbff; }
[data-testid="stExpanderDetails"] { padding: .2rem .85rem .85rem; }

[data-testid="stAlert"] {
    border-radius: var(--em-radius);
    border: 1px solid #e6eef8;
    background: #fbfdff;
}
[data-testid="stAlertContainer"] { padding: .7rem .8rem; }
[data-testid="stAlertContentInfo"] p { font-size: .78rem; line-height: 1.65; }

[data-testid="stDataFrame"] {
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius);
    overflow: hidden;
    background: #fff;
    box-shadow: 0 5px 18px rgba(45, 78, 126, .025);
}
[data-testid="stDataFrame"] [role="columnheader"] {
    background: #f7faff !important;
    color: #627893 !important;
    font-size: .72rem;
}
[data-testid="stDataFrame"] [role="gridcell"] { font-size: .76rem; color: #526986; }

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: .25rem;
    border-bottom: 1px solid var(--em-line);
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    height: 38px;
    padding: 0 .8rem;
    color: var(--em-muted);
    font-size: .8rem;
}
[data-testid="stTabs"] [aria-selected="true"] { color: var(--em-blue-deep); font-weight: 700; }

[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #86a1ff, #5d7cf6); }

[data-testid="stChatMessage"] {
    margin: .2rem 0 .65rem;
    padding: .8rem .95rem;
    border: 1px solid var(--em-line);
    border-radius: var(--em-radius-lg);
    background: #fff;
    box-shadow: 0 5px 17px rgba(45, 78, 126, .025);
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
    margin-left: 12%;
    border-color: #dce9fb;
    background: linear-gradient(135deg, #f2f7ff, #fbfdff);
}
[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) {
    margin-right: 7%;
    border-color: #e4edf6;
    background: #fff;
}
[data-testid="stChatMessageContent"] { color: #3f5774; font-size: .86rem; line-height: 1.75; }
[data-testid="stChatMessageContent"] p { color: #3f5774; }
[data-testid="stChatMessageContent"] [data-testid="stCaptionContainer"] p { color: #8c9aad; font-size: .66rem; }

[data-testid="stChatInput"] {
    border: 1px solid #d8e5f3 !important;
    border-radius: 15px !important;
    background: rgba(255, 255, 255, .96) !important;
    box-shadow: 0 12px 30px rgba(45, 78, 126, .09);
}
[data-testid="stChatInputTextArea"] {
    color: var(--em-ink) !important;
    font-family: var(--em-font) !important;
    font-size: .85rem !important;
}
[data-testid="stChatInputSubmitButton"] { color: var(--em-blue) !important; }

[data-testid="stPopover"] button {
    border-radius: 10px;
    border: 1px solid var(--em-line-strong);
    background: #fff;
    color: #536986;
    font-size: .78rem;
}

[data-testid="stDivider"] { border-color: var(--em-line) !important; margin: 1rem 0; }

.app-footer {
    margin-top: 2.4rem;
    padding-top: 1rem;
    border-top: 1px solid var(--em-line);
    color: #a0adbd;
    font-size: .68rem;
    line-height: 1.7;
    text-align: center;
}

.em-disclaimer {
    padding: .8rem .9rem;
    border: 1px solid #e8e2fa;
    border-radius: var(--em-radius);
    background: linear-gradient(135deg, #faf8ff, #f7fbff);
    color: #716589;
    font-size: .73rem;
    line-height: 1.65;
}
.em-privacy {
    padding: .8rem .9rem;
    border: 1px solid #dcefe9;
    border-radius: var(--em-radius);
    background: linear-gradient(135deg, #f4fbf9, #fbfdff);
    color: #52766f;
    font-size: .72rem;
    line-height: 1.65;
}
.em-badge {
    display: inline-block;
    margin: 0 .2rem .28rem 0;
    padding: .17rem .48rem;
    border-radius: 999px;
    background: #eff4ff;
    color: #5b70b4;
    font-size: .66rem;
    font-weight: 600;
}
.em-muted { color: var(--em-muted); font-size: .78rem; line-height: 1.65; }

.st-key-danger_zone .stButton > button {
    border-color: #f0d3d9;
    background: #fff9fa;
    color: var(--em-danger);
}
.st-key-danger_zone .stButton > button:hover {
    border-color: #e7b9c4;
    background: #fff3f6;
    color: #bd4057;
}
.st-key-danger_zone .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #e47a8c, #cb5068);
    color: #fff;
    border: 0;
}

@media (max-width: 1180px) {
    .em-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .em-hero-copy { max-width: 66%; }
    .em-hero-art { opacity: .7; }
}
@media (max-width: 900px) {
    [data-testid="stAppViewContainer"] > div:has([data-testid="stMain"]) {
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
    }
    [data-testid="stMain"] {
        position: absolute !important;
        inset: 0 !important;
        left: 0 !important;
        right: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        transform: none !important;
    }
    [data-testid="stSidebar"] {
        width: 230px !important;
        min-width: 230px !important;
        max-width: 230px !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] { width: 230px; }
    .block-container { padding: 1.4rem 1.2rem 3.5rem; }
    .em-hero { padding: 1.7rem 1.5rem; }
    .em-hero-copy { max-width: 74%; }
    .em-better { display: none; }
    [data-testid="stHorizontalBlock"]:has(.em-panel) {
        flex-direction: column !important;
        gap: .7rem !important;
    }
    [data-testid="stHorizontalBlock"]:has(.em-panel) > [data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
}
@media (max-width: 700px) {
    .em-hero { min-height: 0; padding: 1.45rem 1.2rem 1.55rem; }
    .em-hero-copy { max-width: 100%; }
    .em-hero-art { opacity: .32; }
    .em-hero h1 { font-size: 2rem; }
    .em-hero p { font-size: .84rem; }
    .em-action-grid { grid-template-columns: 1fr; }
    .em-stat-grid { gap: .6rem; }
    .em-page-head { padding: 1.15rem 1.15rem; border-radius: var(--em-radius-lg); }
    .em-action-card { min-height: 92px; }
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) { margin-left: 3%; }
    [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) { margin-right: 0; }
}
@media (max-width: 480px) {
    .em-stat-grid { grid-template-columns: 1fr; }
    .em-hero-chips { gap: .3rem; }
    .em-hero-chips a { font-size: .64rem; padding: .3rem .55rem; }
    .em-hero-art { opacity: .18; }
    .em-brand { padding-left: .2rem; padding-right: .2rem; }
    .em-panel { padding: .85rem .8rem; }
    [data-testid="stChatMessage"] { padding: .7rem .75rem; }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: .01ms !important;
        animation-duration: .01ms !important;
    }
}
</style>
"""
