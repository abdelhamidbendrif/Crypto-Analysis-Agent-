"""Design system for Crypto Research AI: tokens, base styles and layout rules.

Injected after `theme_css`, so it overrides it without removing any class the
existing components rely on. Everything visual lives here: change a token and
both the sidebar and the chat follow.

Selector policy
- Layout hooks use `.st-key-<name>`, which Streamlit generates from
  `st.container(key=...)`. This is the documented, stable route.
- Native widgets are styled through `data-testid` attributes only where no
  keyed hook exists. These are the parts to re-check after a Streamlit upgrade.
"""

from string import Template

TOKENS = {
    "Light": {
        "bg": "#F4F6F7", "surface": "#FFFFFF", "sunken": "#EDF1F2", "line": "#DEE4E7",
        "ink": "#0F1B20", "muted": "#566870", "accent": "#09766F", "accent_ink": "#FFFFFF",
        "accent_soft": "#E0F1EF", "up": "#0C8559", "down": "#BE3737",
        "lift": "0 1px 2px rgba(15,27,32,.06), 0 14px 32px -16px rgba(15,27,32,.18)",
        "scheme": "light",
    },
    "Dark": {
        "bg": "#0C1316", "surface": "#121B1F", "sunken": "#0E1619", "line": "#223037",
        "ink": "#E7EEF0", "muted": "#8FA3AB", "accent": "#38CDBD", "accent_ink": "#06201D",
        "accent_soft": "#12302F", "up": "#3CD39A", "down": "#FF7676",
        "lift": "0 1px 2px rgba(0,0,0,.45), 0 16px 36px -18px rgba(0,0,0,.7)",
        "scheme": "dark",
    },
}

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Hanken+Grotesk:wght@400;500;600;700&display=swap');"
)

BASE_CSS = Template("""
:root {
  --bg:${bg}; --surface:${surface}; --sunken:${sunken}; --line:${line};
  --ink:${ink}; --muted:${muted}; --accent:${accent}; --accent-ink:${accent_ink};
  --accent-soft:${accent_soft}; --up:${up}; --down:${down}; --lift:${lift};
  /* Keep existing source-aware components on the same palette. */
  --page:var(--bg); --subtle:var(--sunken); --border:var(--line);
  --action:var(--accent); --action-text:var(--accent-ink);
  --positive:var(--up); --negative:var(--down); --user:var(--accent-soft); --focus:var(--accent);
  --r-panel:16px; --r-control:10px; --r-pill:999px;
  --font:'Hanken Grotesk', system-ui, -apple-system, 'Segoe UI', sans-serif;
  color-scheme:${scheme};
}

/* ---- Page ---------------------------------------------------------- */
.stApp, [data-testid="stAppViewContainer"] { background:var(--bg) !important; color:var(--ink) !important; font-family:var(--font) !important; }
[data-testid="stHeader"] { background:transparent !important; }
[data-testid="stDecoration"], footer { display:none !important; }
.block-container { max-width:1360px; padding:3.75rem 2rem 2.5rem !important; }
h1, h2, h3, h4, p, label, li, span:not([data-testid="stIconMaterial"]), button, input, textarea { font-family:var(--font) !important; }
h1 { font-size:1.7rem !important; font-weight:700 !important; letter-spacing:-.02em; line-height:1.15 !important; padding:0 !important; color:var(--ink) !important; }
h2, h3 { font-weight:650 !important; letter-spacing:-.01em; color:var(--ink) !important; }
[data-testid="stSubheader"], h3 { font-size:1.05rem !important; }
[data-testid="stCaptionContainer"], .stCaption, small { color:var(--muted) !important; }
[data-testid="stMarkdownContainer"] p { line-height:1.55; }
a { color:var(--accent) !important; }
:focus-visible { outline:2px solid var(--accent) !important; outline-offset:2px !important; }

/* ---- Sidebar ------------------------------------------------------- */
[data-testid="stSidebar"] { background:var(--surface) !important; border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top:.5rem; }
.brand { display:flex; align-items:center; gap:.6rem; padding:.25rem 0 .1rem; }
.brand-mark { display:grid; place-items:center; width:30px; height:30px; border-radius:9px; background:var(--accent); color:var(--accent-ink); font-size:1rem; }
.brand-name { font-weight:700; font-size:1.02rem; letter-spacing:-.01em; color:var(--ink); }
.brand-name em { font-style:normal; color:var(--accent); }
.st-key-sidebar_nav { gap:.15rem; }
.st-key-sidebar_nav button { justify-content:flex-start !important; border:0 !important; box-shadow:none !important; border-radius:var(--r-control) !important; padding:.5rem .7rem !important; font-weight:500 !important; }
.st-key-sidebar_nav button[kind="tertiary"], .st-key-sidebar_nav [data-testid="stBaseButton-tertiary"] { background:transparent !important; color:var(--muted) !important; }
.st-key-sidebar_nav button[kind="tertiary"]:hover, .st-key-sidebar_nav [data-testid="stBaseButton-tertiary"]:hover { background:var(--sunken) !important; color:var(--ink) !important; }
.st-key-sidebar_nav button[kind="primary"], .st-key-sidebar_nav [data-testid="stBaseButton-primary"] { background:var(--accent-soft) !important; color:var(--accent) !important; font-weight:650 !important; }

/* ---- Controls ------------------------------------------------------ */
.stButton > button, .stDownloadButton > button { border-radius:var(--r-control) !important; border:1px solid var(--line) !important; background:var(--surface) !important; color:var(--ink) !important; font-weight:550 !important; box-shadow:none !important; transition:border-color .12s, background .12s; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--accent) !important; color:var(--accent) !important; }
.stButton > button:disabled, .stDownloadButton > button:disabled { opacity:.45; }
.stButton > [data-testid="stBaseButton-primary"] { background:var(--accent) !important; color:var(--accent-ink) !important; border-color:var(--accent) !important; }
.st-key-sidebar_nav .stButton > [data-testid="stBaseButton-primary"] { background:var(--accent-soft) !important; color:var(--accent) !important; }
[data-testid="stBaseButton-primary"]:hover { filter:brightness(1.06); color:var(--accent-ink) !important; }
[data-testid="stBaseButton-tertiary"] { border:0 !important; background:transparent !important; color:var(--accent) !important; }
[data-testid="stBaseButton-tertiary"]:hover { background:var(--accent-soft) !important; }

/* Radios become segmented controls (Data mode, Appearance) */
[data-testid="stRadio"] [role="radiogroup"] { gap:0 !important; background:var(--sunken); border:1px solid var(--line); border-radius:var(--r-pill); padding:3px; width:fit-content; flex-wrap:nowrap; }
[data-testid="stRadio"] label { margin:0 !important; padding:.28rem .85rem; border-radius:var(--r-pill); cursor:pointer; }
[data-testid="stRadio"] label > div:first-child { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
[data-testid="stRadio"] label p { font-size:.85rem; font-weight:550; color:var(--muted); }
[data-testid="stRadio"] label:has(input:checked) { background:var(--surface); box-shadow:0 1px 2px rgba(0,0,0,.14); }
[data-testid="stRadio"] label:has(input:checked) p { color:var(--ink); font-weight:650; }
[data-testid="stRadio"] label:has(input:focus-visible) { outline:2px solid var(--accent); outline-offset:1px; }

/* Text inputs and selects */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, textarea { background:var(--surface) !important; color:var(--ink) !important; border-color:var(--line) !important; border-radius:var(--r-control) !important; }
input, textarea { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background:var(--surface) !important; color:var(--ink) !important; }
[data-baseweb="select"] svg { fill:var(--muted) !important; }

/* ---- Panels -------------------------------------------------------- */
.st-key-analyst_panel, .st-key-context_panel, .st-key-page_panel { background:var(--surface) !important; border:1px solid var(--line) !important; border-radius:var(--r-panel) !important; padding:1.1rem 1.2rem !important; }
.st-key-analyst_panel { box-shadow:var(--lift); }
[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:var(--r-panel) !important; background:var(--surface); }
[data-testid="stMetric"] { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:.8rem 1rem; }
[data-testid="stMetricValue"] { font-weight:700; font-variant-numeric:tabular-nums; letter-spacing:-.01em; }
[data-testid="stExpander"] details, [data-testid="stStatus"] { border:1px solid var(--line) !important; border-radius:12px !important; background:var(--surface) !important; }

/* ---- Tabs ---------------------------------------------------------- */
[data-baseweb="tab-list"] { gap:.25rem; border-bottom:1px solid var(--line); }
[data-baseweb="tab"] { color:var(--muted) !important; font-weight:550 !important; padding:.5rem .8rem !important; background:transparent !important; }
[data-baseweb="tab"][aria-selected="true"] { color:var(--ink) !important; font-weight:650 !important; }
[data-baseweb="tab-highlight"] { background:var(--accent) !important; height:2px !important; }
[data-baseweb="tab-border"] { display:none !important; }

/* ---- Conversation -------------------------------------------------- */
[data-testid="stChatMessage"] { background:transparent !important; padding:.35rem 0 !important; gap:.7rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { flex-direction:row-reverse; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] { background:var(--accent-soft); border-radius:14px 14px 4px 14px; padding:.65rem .95rem; max-width:80%; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] { background:var(--surface); border:1px solid var(--line); border-radius:14px 14px 14px 4px; padding:.85rem 1.05rem; max-width:100%; }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] { background:var(--sunken) !important; color:var(--accent) !important; }
[data-testid="stChatInput"] { background:var(--surface) !important; border:1px solid var(--line) !important; border-radius:14px !important; }
[data-testid="stChatInput"] textarea { background:transparent !important; }
[data-testid="stChatInput"]:focus-within { border-color:var(--accent) !important; }

/* ---- Custom elements emitted by the app ----------------------------- */
.pill { display:inline-flex; align-items:center; gap:.4rem; padding:.18rem .65rem; border-radius:var(--r-pill); font-size:.78rem; font-weight:600; border:1px solid var(--line); background:var(--sunken); color:var(--muted); }
.pill::before { content:""; width:7px; height:7px; border-radius:50%; background:var(--muted); }
.pill-live { color:var(--accent); background:var(--accent-soft); border-color:transparent; }
.pill-live::before { background:var(--up); }
.welcome { padding:1.6rem .25rem .6rem; max-width:34rem; }
.welcome h3 { margin:0 0 .35rem !important; font-size:1.25rem !important; }
.welcome p { margin:0; color:var(--muted); }
.panel-head { display:flex; align-items:baseline; justify-content:space-between; gap:1rem; margin-bottom:.4rem; }
.panel-head strong { font-size:1.05rem; font-weight:650; letter-spacing:-.01em; }
.panel-head span { color:var(--muted); font-size:.85rem; }

/* ---- Small screens and motion --------------------------------------- */
@media (max-width: 900px) {
  .block-container { padding:3.75rem .9rem 2rem !important; }
  h1 { font-size:1.4rem !important; }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] { max-width:92%; }
}
@media (prefers-reduced-motion: reduce) { * { transition:none !important; animation:none !important; scroll-behavior:auto !important; } }
""")


def design_css(appearance):
    """Return the <style> block for 'Light' or 'Dark' (unknown values fall back to Light)."""
    tokens = TOKENS.get(appearance, TOKENS["Light"])
    return f"<style>{FONT_IMPORT}{BASE_CSS.substitute(tokens)}</style>"
