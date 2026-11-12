"""Conversation-first Streamlit workspace for Crypto Research AI."""

from time import perf_counter
from html import escape

import streamlit as st
from langchain_core.messages import AIMessage

from crypto_agent.workspace import (
    build_live_graph, current_evidence, demo_turn, sample_market_payload,
)
from crypto_agent.ui.activity import invoke_with_activity
from crypto_agent.ui.components import (
    comparison_panel, market_cards, news_panel, report_text, response_sources,
)
from crypto_agent.ui.design import design_css
from crypto_agent.ui.state import (
    change_mode, initialize, keep_selection, new_conversation, open_conversation,
    save_conversation, set_view,
)
from crypto_agent.ui.theme import theme_css

ASSETS = ["BTC", "ETH", "LTC", "BNB"]
NAV = (("Research Desk", "space_dashboard"), ("Conversations", "forum"),
       ("Compare Assets", "compare_arrows"), ("News", "newspaper"), ("Reports", "description"))
TITLES = {"Research Desk": "Crypto Research AI", "Conversations": "Your conversations",
          "Compare Assets": "Compare assets", "News": "News watch", "Reports": "Research reports"}
SUBTITLES = {
    "Research Desk": "Ask about a coin, compare two assets or read the news. Every answer shows its sources.",
    "Conversations": "Pick up a past question where you left it.",
    "Compare Assets": "Two assets, side by side, from one request.",
    "News": "Recent headlines on any topic, with links to the originals.",
    "Reports": "Download any answer from this conversation.",
}
STARTERS = (
    ("BTC snapshot", ":material/trending_up:", "Give me current market data for BTC."),
    ("Compare BTC and ETH", ":material/compare_arrows:",
     "Compare current market data for BTC and ETH. Preserve source units and timestamps."),
    ("BTC news", ":material/newspaper:", "Give me three recent news articles about Bitcoin."),
)

st.set_page_config(page_title="Crypto Research AI", page_icon="◈", layout="wide")
initialize(st.session_state)
st.markdown(theme_css(st.session_state.appearance), unsafe_allow_html=True)
st.markdown(design_css(st.session_state.appearance), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Agent turn (backend contract unchanged)
# --------------------------------------------------------------------------
def run_turn(query):
    """Use the existing agent, retaining evidence beside the corresponding reply."""
    started = perf_counter()
    try:
        with st.status("Researching your question…", expanded=True) as status:
            progress = st.empty()
            if st.session_state.mode == "Demo":
                progress.caption("Loading fictional samples. No model or API calls.")
                result = demo_turn(query, st.session_state.history)
            else:
                progress.caption("Analyst connected. Selecting research tools.")
                if "live_graph" not in st.session_state:
                    st.session_state.live_graph = build_live_graph()
                result = invoke_with_activity(
                    st.session_state.live_graph, query, st.session_state.thread_id,
                    lambda steps: progress.markdown("\n\n".join(f"{name} · **{state}**" for name, state in steps)),
                )
            final = next((message for message in reversed(result["messages"])
                          if isinstance(message, AIMessage) and not message.tool_calls), None)
            if final is None or not isinstance(final.content, str) or not final.content.strip():
                raise ValueError("No final text response")
            status.update(label="Research complete", state="complete", expanded=False)
        elapsed = perf_counter() - started
        evidence = current_evidence(result["messages"])
        st.session_state.history = result["messages"]
        st.session_state.chat.extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": final.content, "evidence": evidence, "elapsed": elapsed},
        ])
        st.session_state.evidence = evidence
        st.session_state.last_report = final.content
        st.session_state.elapsed = elapsed
        save_conversation(st.session_state)
    except Exception:
        # Incomplete tool-call checkpoints must not be restored or retried.
        new_conversation(st.session_state, archive=False)
        st.session_state.notice = (
            "The request could not be completed. Check your connection, API keys and quotas. "
            "The conversation was reset so you can retry safely."
        )
    st.rerun()


# --------------------------------------------------------------------------
# Shared pieces
# --------------------------------------------------------------------------
def compare_controls():
    """Keep asset selections across navigation, theme changes and reruns."""
    st.session_state._first_asset = st.session_state.first_asset
    st.session_state._second_asset = st.session_state.second_asset
    first, second = st.columns(2)
    first.selectbox("First asset", ASSETS, key="_first_asset", on_change=keep_selection,
                    args=(st.session_state, "first_asset"))
    second.selectbox("Second asset", ASSETS, key="_second_asset", on_change=keep_selection,
                     args=(st.session_state, "second_asset"))
    same = st.session_state.first_asset == st.session_state.second_asset
    if st.button("Compare", type="primary", width="stretch", disabled=same, key="fetch_comparison",
                 help="Choose two different assets." if same else None):
        assets = {st.session_state.first_asset, st.session_state.second_asset}
        if st.session_state.mode == "Demo" and assets != {"BTC", "ETH"}:
            st.warning("Demo mode has fictional BTC and ETH samples only. Switch to Live APIs for other assets.")
        else:
            run_turn(f"Compare current market data for {st.session_state.first_asset} and "
                     f"{st.session_state.second_asset}. Preserve source units and timestamps.")


def starter_buttons(prefix):
    """One-click research prompts. Same three actions in the empty and active states."""
    columns = st.columns(len(STARTERS))
    for index, (column, (label, icon, query)) in enumerate(zip(columns, STARTERS)):
        if column.button(label, icon=icon, width="stretch", key=f"{prefix}_{index}"):
            run_turn(query)


def panel_head(title, note=""):
    st.markdown(f'<div class="panel-head"><strong>{escape(title)}</strong><span>{escape(note)}</span></div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Chrome: sidebar and page header
# --------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark" aria-hidden="true">◈</span>'
                    '<span class="brand-name">Crypto Research <em>AI</em></span></div>', unsafe_allow_html=True)
        st.button("New conversation", icon=":material/add:", width="stretch",
                  on_click=new_conversation, args=(st.session_state,))
        with st.container(key="sidebar_nav"):
            for label, icon in NAV:
                st.button(label, icon=f":material/{icon}:", width="stretch",
                          type="primary" if st.session_state.view == label else "tertiary",
                          on_click=set_view, args=(st.session_state, label))
        st.divider()
        st.caption("Data mode")
        st.radio("Data mode", ["Demo", "Live APIs"], key="mode", horizontal=True,
                 label_visibility="collapsed", on_change=change_mode, args=(st.session_state,),
                 help="Demo uses fictional samples. Live APIs uses Groq, FreeCryptoAPI and NewsAPI.")
        st.caption("Fictional samples, no API calls." if st.session_state.mode == "Demo"
                   else "Live requests use your API quota.")
        st.divider()
        st.caption("Conversations stay in this browser session. Demo and Live histories are kept apart.")


def render_header():
    view = st.session_state.view
    live = st.session_state.mode != "Demo"
    heading, controls = st.columns([2.2, 1.4], vertical_alignment="center")
    with heading:
        st.title(TITLES[view], anchor=False)
        pill = ('<span class="pill pill-live">Live APIs</span>' if live
                else '<span class="pill">Demo, fictional data</span>')
        st.markdown(f'{pill}&nbsp;&nbsp;<span style="color:var(--muted)">{SUBTITLES[view]}</span>',
                    unsafe_allow_html=True)
    with controls:
        with st.container(key="header_controls"):
            appearance, export = st.columns([1, 1.1], vertical_alignment="center")
            appearance.radio("Appearance", ["Light", "Dark"], horizontal=True, key="appearance",
                             label_visibility="collapsed",
                             help="Switch the workspace theme. Your conversation is preserved.")
            export.download_button("Export report", icon=":material/download:", width="stretch",
                                   data=report_text(st.session_state.last_report, st.session_state.mode),
                                   file_name="crypto-research-report.md", mime="text/markdown",
                                   key="header_export", disabled=not bool(st.session_state.last_report))
    if st.session_state.get("notice"):
        st.warning(st.session_state.pop("notice"))


# --------------------------------------------------------------------------
# Views
# --------------------------------------------------------------------------
def render_analyst():
    """The conversation. Largest element on the page, one surface, one input."""
    with st.container(border=True, key="analyst_panel"):
        panel_head("AI analyst", "Answers cite the data they used")
        empty = not st.session_state.chat
        with st.container(height=520, border=False, autoscroll=True):
            if empty:
                st.markdown('<div class="welcome"><h3>What would you like to research?</h3>'
                            '<p>Start with one of these, or type your own question below. '
                            'Follow-up questions keep the context.</p></div>', unsafe_allow_html=True)
                starter_buttons("starter")
            for entry in st.session_state.chat:
                is_user = entry["role"] == "user"
                with st.chat_message(entry["role"],
                                     avatar=":material/person:" if is_user else ":material/auto_awesome:"):
                    st.markdown(entry["content"])
                    if not is_user:
                        response_sources(entry.get("evidence", []), entry.get("elapsed"))
        if not empty:
            starter_buttons("chip")
        query = st.chat_input("Ask about a coin, compare assets, or explore recent news…", key="question",
                              max_chars=2000, submit_mode="disable")
        if query and query.strip():
            run_turn(query.strip())


def render_context(evidence, display_evidence, preview):
    """Supporting material next to the chat: headlines, comparison, sources."""
    with st.container(border=True, key="context_panel"):
        news, comparison, sources = st.tabs(["News", "Compare", "Sources"])
        with news:
            panel_head("Latest headlines",
                       "Fictional examples" if preview else "Latest news request")
            news_panel(display_evidence)
            st.button("All news", icon=":material/arrow_forward:", type="tertiary",
                      on_click=set_view, args=(st.session_state, "News"))
        with comparison:
            panel_head("Side by side")
            compare_controls()
            comparison_panel(display_evidence, compact=True)
        with sources:
            panel_head("Research activity", f"{len(evidence)} tool result(s) in the latest turn")
            response_sources(evidence, st.session_state.elapsed)


def render_desk(evidence, display_evidence, preview):
    st.caption("Market snapshot, fictional examples" if preview
               else "Market snapshot from your latest request. Not a streaming feed, so check each timestamp.")
    market_cards(display_evidence)
    analyst, context = st.columns([2, 1], gap="medium")
    with analyst:
        render_analyst()
    with context:
        render_context(evidence, display_evidence, preview)


def render_compare(evidence):
    with st.container(border=True, key="page_panel"):
        st.caption("Source timestamps may differ. No historical prices or synchronized feed are inferred.")
        compare_controls()
        comparison_panel(evidence)


def render_news(display_evidence):
    with st.container(border=True, key="page_panel"):
        st.caption("Headlines give context. They do not prove why a price moved.")
        st.session_state._news_topic = st.session_state.news_topic
        topic = st.text_input("News topic", key="_news_topic", max_chars=150,
                              on_change=keep_selection, args=(st.session_state, "news_topic"))
        if st.button("Search news", type="primary", disabled=not topic.strip()):
            run_turn(f"Give me five recent news articles about {topic.strip()}.")
        news_panel(display_evidence, limit=10)


def render_conversations():
    save_conversation(st.session_state)
    records = [(key, record) for key, record in st.session_state.conversations.items()
               if record["mode"] == st.session_state.mode]
    if not records:
        st.info("No conversations in this mode yet. Ask a question on the Research Desk to start one.")
    for thread_id, record in reversed(records):
        title = next((entry["content"] for entry in record["chat"] if entry["role"] == "user"), "Conversation")
        with st.container(border=True):
            label = title[:85] + ("…" if len(title) > 85 else "")
            st.markdown(f"**{label}**")
            current = " · Current" if thread_id == st.session_state.thread_id else ""
            st.caption(f"{record['mode']} · {len(record['chat']) // 2} turn(s){current}")
            st.button("Continue conversation", key=f"resume_{thread_id}",
                      on_click=open_conversation, args=(st.session_state, thread_id))


def render_reports():
    reports = [entry for entry in st.session_state.chat if entry["role"] == "assistant"]
    if not reports:
        st.info("Reports appear here after the analyst answers a question. "
                "To open reports from another conversation, continue it from Conversations.")
        return
    chosen = st.selectbox("Choose a report", list(range(len(reports))),
                          format_func=lambda index: f"Response {index + 1}",
                          key=f"report_{st.session_state.thread_id}")
    report = reports[chosen]
    st.download_button("Download selected report", icon=":material/download:",
                       data=report_text(report["content"], st.session_state.mode),
                       file_name="crypto-research-report.md", mime="text/markdown", key="selected_export")
    with st.container(border=True, key="page_panel"):
        st.markdown(report["content"])
        response_sources(report.get("evidence", []), report.get("elapsed"))


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
render_sidebar()
render_header()

evidence = st.session_state.evidence
preview = st.session_state.mode == "Demo" and not st.session_state.chat
display_evidence = evidence
if preview:
    display_evidence = [{"tool": "crypto_data_tool", "failed": False, "args": {"symbol": symbol},
                         "data": sample_market_payload(symbol)} for symbol in ("BTC", "ETH")]
    display_evidence += current_evidence(demo_turn("Three news articles about Bitcoin", [])["messages"])

view = st.session_state.view
if view == "Research Desk":
    render_desk(evidence, display_evidence, preview)
elif view == "Compare Assets":
    render_compare(evidence)
elif view == "News":
    render_news(display_evidence)
elif view == "Conversations":
    render_conversations()
elif view == "Reports":
    render_reports()

st.caption("Source-aware research. Educational use only, not investment advice.")
