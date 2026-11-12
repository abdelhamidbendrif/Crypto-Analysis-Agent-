"""Centralized, session-local design tokens and scoped Streamlit styling."""

THEMES = {
    "Light": {
        "page": "#F5F7FB", "surface": "#FFFFFF", "subtle": "#F0F4F8",
        "ink": "#18263D", "muted": "#5D6C80", "border": "#DCE3EC",
        "accent": "#08736D", "accent_soft": "#E6F4F1", "action": "#08736D",
        "action_text": "#FFFFFF", "positive": "#08704D", "negative": "#B43343",
        "user": "#EDF3FE", "focus": "#2563EB",
    },
    "Dark": {
        "page": "#0D1522", "surface": "#131F30", "subtle": "#1B2A3E",
        "ink": "#E8EEF7", "muted": "#A5B4C8", "border": "#304158",
        "accent": "#72DCC9", "accent_soft": "#193D3D", "action": "#72DCC9",
        "action_text": "#0D1522", "positive": "#7FDFB8", "negative": "#FFA6B2",
        "user": "#1C304C", "focus": "#8DB5FF",
    },
}


def theme_css(appearance):
    """Style each browser independently without mutating Streamlit's global config."""
    tokens = THEMES[appearance]
    variables = ";".join(f"--{name.replace('_', '-')}: {value}" for name, value in tokens.items())
    scheme = appearance.lower()
    return "<style>:root{" + variables + f";color-scheme:{scheme}" + "}" + r"""
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
        background: var(--page); color: var(--ink);
        --primary-color: var(--accent); --text-color: var(--ink);
        --background-color: var(--surface); --secondary-background-color: var(--subtle);
    }
    [data-testid="stHeader"] {background: var(--page);}
    .block-container {max-width: 1536px; padding: 3.8rem 2rem 1.6rem;}
    h1 {font-size: 1.85rem !important; font-weight: 700 !important; letter-spacing: -.045em;
        line-height: 1.25 !important; padding: 0 0 .4rem !important; color: var(--ink);}
    h2 {font-size: 1.25rem !important; letter-spacing: -.025em; color: var(--ink);}
    h3 {font-size: 1.05rem !important; letter-spacing: -.02em; color: var(--ink);}
    p, li {line-height: 1.6;}
    [data-testid="stMarkdownContainer"], [data-testid="stText"],
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p {
        color: var(--ink);
    }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        color: var(--muted) !important; font-size: .79rem;
    }
    [data-testid="stSidebar"] {background: var(--surface); border-right: 1px solid var(--border);}
    [data-testid="stSidebar"] > div:first-child {padding-top: 1.5rem;}
    [data-testid="stVerticalBlockBorderWrapper"] > div,
    [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {border-color: var(--border);}
    .st-key-analyst_panel, .st-key-context_panel, .st-key-page_panel {
        background: var(--surface); border: 1px solid var(--border) !important;
        border-radius: 16px; box-shadow: 0 2px 8px #10274404;
    }
    [data-testid="stChatMessage"] {background: var(--subtle); border: 0;
        border-radius: 12px; padding: .9rem; color: var(--ink);}
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background: var(--user);}
    [data-testid="stChatMessage"] h2 {font-size: 1.05rem !important;}
    [data-testid="stChatMessage"] h3 {font-size: .95rem !important;}
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] table {font-size: .88rem;}
    [data-testid="stChatInput"], [data-testid="stChatInput"] > div {
        background: var(--surface); color: var(--ink); border-color: var(--border);
    }
    textarea, input, [data-baseweb="input"], [data-baseweb="textarea"],
    [data-baseweb="select"] > div {background: var(--surface) !important;
        color: var(--ink) !important; -webkit-text-fill-color: var(--ink); border-color: var(--border) !important;}
    textarea::placeholder, input::placeholder {color: var(--muted) !important; opacity: 1;}
    [data-baseweb="popover"] *, [role="listbox"], [role="option"] {
        background-color: var(--surface); color: var(--ink);
    }
    [role="option"]:hover {background: var(--subtle);}
    button, [data-testid="stDownloadButton"] a {border-radius: 9px !important;}
    button p {color: inherit !important;}
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-tertiary"],
    [data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stLinkButton"] a,
    [data-testid="stDownloadButton"] button {
        background: var(--surface); color: var(--ink); border-color: var(--border);
    }
    [data-testid="stBaseButton-primary"] {background: var(--action); color: var(--action-text);
        border-color: var(--action);}
    button:hover:not(:disabled), [data-testid="stLinkButton"] a:hover {
        border-color: var(--accent); color: var(--accent);
    }
    [data-testid="stBaseButton-primary"]:hover {background: var(--action); color: var(--action-text);}
    button:disabled {opacity: .55; color: var(--muted);}
    :is(button, a, input, textarea, [role="tab"], [role="combobox"]):focus-visible {
        outline: 2px solid var(--focus) !important; outline-offset: 3px;
    }
    .st-key-sidebar_nav button {justify-content: flex-start; border: 0;
        background: transparent; padding: .7rem .85rem; font-weight: 500;}
    .st-key-sidebar_nav [data-testid="stBaseButton-primary"] {
        background: var(--accent-soft); color: var(--accent); font-weight: 650;
    }
    .st-key-sidebar_nav button:hover {background: var(--subtle);}
    [data-testid="stRadio"] label {color: var(--ink);}
    [data-testid="stRadio"] label:has(input:checked) {color: var(--accent);}
    [data-testid="stTabs"] [role="tablist"] {border-bottom: 1px solid var(--border); gap: 1rem;}
    [data-testid="stTabs"] button[role="tab"] {color: var(--muted); border-radius: 0 !important; font-weight: 600;}
    [data-testid="stTabs"] button[aria-selected="true"] {color: var(--accent);}
    [data-baseweb="tab-highlight"] {background: var(--accent);}
    details, [data-testid="stExpander"] {background: var(--surface); color: var(--ink); border-color: var(--border);}
    details summary {color: var(--muted); font-size: .8rem;}
    table {color: var(--ink); width: 100%;}
    th, td {border-color: var(--border) !important; padding: .55rem !important;}
    th {background: var(--subtle); color: var(--muted); font-weight: 600;}
    a {color: var(--accent);}
    hr {border-color: var(--border); margin: .6rem 0;}
    [data-testid="stAlert"] {background: var(--subtle); color: var(--ink);}
    [data-testid="stAlert"] p {color: var(--ink);}
    [data-testid="stJson"] {background: var(--subtle); color: var(--ink); border-radius: 8px;}
    [data-testid="stJson"] span {color: var(--ink) !important;}
    .brand {display: flex; align-items: center; gap: .65rem; margin-bottom: .5rem;}
    .brand-mark, .welcome-mark {display: inline-grid; place-items: center; background: var(--accent-soft);
        color: var(--accent); border-radius: 10px; width: 38px; height: 38px; font-size: 1.5rem;}
    .brand-name {font-size: 1rem; font-weight: 750; letter-spacing: -.035em; color: var(--ink);}
    .brand-name em {color: var(--accent); font-style: normal;}
    .eyebrow {color: var(--accent); letter-spacing: .12em; font-size: .65rem; font-weight: 700; margin-bottom: .4rem;}
    .mode-note {font-size: .76rem; color: var(--muted); margin: .15rem 0 1rem; line-height: 1.5;}
    .mode-tag {display: inline-block; font-size: .68rem; font-weight: 650; color: var(--accent);
        border: 1px solid var(--border); background: var(--accent-soft); border-radius: 6px; padding: .12rem .42rem; margin-right: .4rem;}
    .snapshot-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; margin:.2rem 0 .9rem;}
    .snapshot {background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:14px 16px;}
    .snapshot-top {display:flex; align-items:center; gap:9px; margin-bottom:7px;}
    .coin-mark {display:inline-grid; place-items:center; width:29px; height:29px; border-radius:50%;
        background:var(--accent-soft); color:var(--accent); font-size:.72rem; font-weight:700;}
    .coin-label {font-weight:650; font-size:.86rem; color:var(--ink);}
    .quote-label {font-size:.7rem; color:var(--muted); margin-left:auto;}
    .quote-value {color:var(--ink); font-size:1.48rem; font-weight:680; letter-spacing:-.035em; font-variant-numeric:tabular-nums;}
    .quote-change {font-size:.74rem; margin-top:4px; color:var(--muted);}
    .positive {color:var(--positive);} .negative {color:var(--negative);}
    .welcome {padding:2.6rem 1rem; text-align:center; max-width:470px; margin:auto;}
    .welcome h3 {margin-top:1rem; font-size:1.3rem !important;}
    .welcome p {font-size:.87rem; color:var(--muted);}
    .news-item {padding:13px 0; border-bottom:1px solid var(--border);}
    .news-item:last-child {border:0;}
    .news-title {color:var(--ink); font-weight:600; text-decoration:none; font-size:.86rem; line-height:1.5; display:block;}
    .news-title:hover {color:var(--accent); text-decoration:underline;}
    .news-meta {font-size:.7rem; color:var(--muted); margin-top:6px; line-height:1.5;}
    .empty-note {padding:1.2rem .3rem; color:var(--muted); font-size:.84rem; line-height:1.7;}
    .source-chip {display:inline-block; color:var(--accent); background:var(--accent-soft);
        border:1px solid var(--border); border-radius:6px; padding:3px 7px; margin:0 5px 6px 0; font-size:.72rem;}
    @media (max-width: 900px) {
        .block-container {padding-left:1rem; padding-right:1rem;}
        h1 {font-size:1.55rem !important;}
    }
    @media (max-width: 760px) {
        [data-testid="stHorizontalBlock"] {flex-wrap:wrap;}
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:100%; flex:1 1 100%;}
        .st-key-header_controls [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width:0; flex:1 1 0;}
        .snapshot-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
        .snapshot {padding:12px;}
        .quote-value {font-size:1.2rem; overflow-wrap:anywhere;}
        .quote-label {display:none;}
    }
    @media (prefers-reduced-motion: reduce) {*, *::before, *::after {animation:none !important; transition:none !important;}}
    </style>
    """
