"""Streamlit research workspace for the Crypto Analysis Agent."""

from time import perf_counter
from uuid import uuid4

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from crypto_agent.workspace import (
    build_live_graph, current_evidence, demo_turn, market_rows, sample_market_payload,
)


st.set_page_config(page_title="Crypto Research | Analysis Agent", page_icon="◈", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1440px; padding-top: 4rem; padding-bottom: 2rem;}
h1 {font-size: 2.8rem !important; letter-spacing: -.06em; font-weight: 700 !important;}
h2 {letter-spacing: -.035em;}
.eyebrow {color: #49d9b0; font-size: .75rem; letter-spacing: .18em; font-weight: 700;}
.subtitle {color: #9baec4; max-width: 780px; font-size: 1.05rem; line-height: 1.65;}
[data-testid="stMetric"] {background: #131e2d; border: 1px solid #26364a;
    padding: 1.15rem; border-radius: 12px; min-height: 145px;}
[data-testid="stMetricValue"] {font-size: 1.9rem;}
[data-testid="stChatMessage"] {border: 1px solid #26364a; border-radius: 12px;}
[data-testid="stSidebar"] {border-right: 1px solid #26364a;}
div[data-testid="stTabs"] button {font-weight: 600;}
</style>
""", unsafe_allow_html=True)


def reset_session():
    """Drop prior context, including the session's private checkpoint graph."""
    for key in ("history", "chat", "evidence", "last_report", "elapsed", "live_graph", "notice"):
        st.session_state.pop(key, None)
    st.session_state.thread_id = str(uuid4())


if "thread_id" not in st.session_state:
    reset_session()
for key, default in (("history", []), ("chat", []), ("evidence", []),
                     ("last_report", ""), ("elapsed", None)):
    st.session_state.setdefault(key, default)

with st.sidebar:
    st.markdown("### ◈ CRYPTO RESEARCH")
    st.caption("A research workspace, powered by tools.")
    st.divider()
    mode = st.radio("Data mode", ["Demo", "Live APIs"], key="mode", on_change=reset_session,
                    help="Demo is scripted and fictional. Live APIs uses Groq, FreeCryptoAPI and NewsAPI.")
    if mode == "Demo":
        st.caption("No API keys needed. No model calls. BTC and ETH sample scenarios only.")
    else:
        st.caption("Uses server-side .env credentials. Each request may consume your API quota.")
    st.button("New conversation", on_click=reset_session, width="stretch")
    st.divider()
    st.markdown("**How it works**")
    st.caption("01 · Ask a research question\n\n02 · The agent selects its tools\n\n03 · Inspect the results and sources")
    st.divider()
    st.caption("Memory lasts within this browser session. New conversation or changing modes clears it.")
    st.caption("Built with LangGraph · Groq · Streamlit")

st.markdown('<div class="eyebrow">MARKET INTELLIGENCE / RESEARCH DESK</div>', unsafe_allow_html=True)
st.title("A clearer view of crypto.")
st.markdown('<p class="subtitle">Explore market snapshots, compare assets, and follow the news. '
            'Ask a question, then inspect the evidence behind the answer.</p>', unsafe_allow_html=True)
if mode == "Demo":
    st.info("DEMO · All prices, dates and headlines below are fictional examples. This scripted preview makes no API or model calls.")
else:
    st.info("LIVE APIs · Data is fetched only when you send a request. Source timestamps may differ from retrieval time.")
if st.session_state.get("notice"):
    st.warning(st.session_state.pop("notice"))


def run_turn(query):
    """Execute one turn, then replace displayed evidence with that turn's results."""
    started = perf_counter()
    try:
        with st.spinner("Loading sample scenario…" if mode == "Demo" else "Researching with tools…"):
            if mode == "Demo":
                result = demo_turn(query, st.session_state.history)
            else:
                if "live_graph" not in st.session_state:
                    st.session_state.live_graph = build_live_graph()
                result = st.session_state.live_graph.invoke(
                    {"messages": [HumanMessage(content=query)]},
                    config={"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 20},
                )
        final = next((message for message in reversed(result["messages"])
                      if isinstance(message, AIMessage) and not message.tool_calls), None)
        if final is None or not isinstance(final.content, str) or not final.content.strip():
            raise ValueError("No final text response")
        st.session_state.history = result["messages"]
        st.session_state.chat.extend([{"role": "user", "content": query},
                                      {"role": "assistant", "content": final.content}])
        st.session_state.evidence = current_evidence(result["messages"])
        st.session_state.last_report = final.content
        st.session_state.elapsed = perf_counter() - started
    except Exception:
        # Discard a potentially incomplete tool-call checkpoint before retrying.
        reset_session()
        st.session_state.notice = ("The request could not be completed. Check your connection, API keys and quotas. "
                                   "The conversation was reset so you can retry safely.")
    st.rerun()


research, compare, sources = st.tabs(["Research desk", "Compare assets", "Sources & activity"])
with research:
    evidence = st.session_state.evidence
    preview = mode == "Demo" and not st.session_state.chat
    display_evidence = ([{"tool": "crypto_data_tool", "failed": False, "data": sample_market_payload(symbol)}
                         for symbol in ("BTC", "ETH")] if preview else evidence)
    rows = market_rows(display_evidence)
    st.subheader("Market snapshots")
    st.caption("Fictional sample snapshots" if preview else "Results from the latest request only · no automatic refresh")
    if rows:
        columns = st.columns(min(len(rows), 4))
        for index, row in enumerate(rows):
            with columns[index % len(columns)]:
                st.metric(row["Symbol"], row["Last reported"] or "Unavailable")
                st.caption(f"Quote: {row['Quote currency']} · Reported change: {row['Reported change (%)']}%")
                st.caption(f"Source time: {row['Source timestamp']}")
    else:
        st.caption("Ask for a market snapshot to populate the cards. News-only requests do not reuse earlier quotes.")
    st.divider()
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.subheader("Ask the analyst")
        quick = st.columns(2)
        if quick[0].button("BTC snapshot", width="stretch"):
            run_turn("Give me current market data for BTC.")
        if quick[1].button("Compare BTC / ETH", width="stretch"):
            run_turn("Compare current market data for BTC and ETH. Preserve source units and timestamps.")
        if not st.session_state.chat:
            st.caption("Start with a snapshot. Then ask ‘Give me three news articles about the same cryptocurrency.’")
        if st.session_state.chat:
            with st.container(height=520, border=False, autoscroll=True):
                for entry in st.session_state.chat:
                    with st.chat_message(entry["role"]):
                        st.markdown(entry["content"])
        query = st.chat_input("Ask about a coin, a comparison, or recent news…", key="question", max_chars=2000,
                              submit_mode="disable")
        if query and query.strip():
            run_turn(query.strip())
    with right:
        st.subheader("News watch")
        found_news = False
        for result in evidence:
            if result["tool"] != "crypto_news_tool" or result["failed"]:
                continue
            for article in result["data"].get("articles", []):
                found_news = True
                with st.container(border=True):
                    st.markdown(f"**{article.get('title', 'Untitled')}**")
                    st.caption(f"{article.get('source') or 'Source not provided'} · {article.get('publishedAt') or 'Date not provided'}")
                    url = article.get("url", "")
                    if isinstance(url, str) and url.startswith(("https://", "http://")):
                        st.link_button("Read source ↗", url)
        if not found_news:
            st.caption("Headlines from your latest news request appear here, with publication times and original links.")
            if st.button("Get BTC news", width="stretch"):
                run_turn("Give me three recent news articles about Bitcoin.")
        st.divider()
        st.markdown("**Read the numbers with context**")
        st.caption("Missing units, timezones and measurement periods stay unspecified. A headline alone does not explain a price move.")

with compare:
    st.subheader("Side by side. Same request.")
    st.caption("Fetch both assets in one turn. Quotes may come from different source timestamps; this is not a synchronized feed.")
    c1, c2, c3 = st.columns([1, 1, 1.2], vertical_alignment="bottom")
    first = c1.selectbox("First asset", ["BTC", "ETH", "LTC", "BNB"], key="first_asset")
    second = c2.selectbox("Second asset", ["ETH", "BTC", "LTC", "BNB"], key="second_asset")
    if c3.button("Fetch comparison", type="primary", width="stretch", disabled=first == second):
        if mode == "Demo" and {first, second} != {"BTC", "ETH"}:
            st.warning("The scripted demo supports BTC and ETH only. Use Live APIs for other assets.")
        else:
            run_turn(f"Compare current market data for {first} and {second}. Preserve source units and timestamps.")
    actual_rows = market_rows(st.session_state.evidence)
    if actual_rows:
        comparison = [{"Metric": metric, **{row["Symbol"]: row[metric] for row in actual_rows}}
                      for metric in actual_rows[0] if metric != "Symbol"]
        st.dataframe(comparison, hide_index=True, width="stretch", height="auto")
        if len({row["Symbol"] for row in actual_rows}) < 2:
            st.caption("One asset is available. Fetch a comparison to request both assets.")
    else:
        st.caption("Your latest market results will appear here. Fetch a comparison to begin.")
    st.caption("Percent changes are comparable only when their baselines and periods match. Missing metadata is not inferred.")

with sources:
    st.subheader("Evidence you can inspect")
    st.caption("Tool requests and source results from the latest turn. This view shows tool activity, not private model reasoning.")
    if st.session_state.elapsed is not None:
        st.caption(f"Completed in {st.session_state.elapsed:.1f}s · {len(st.session_state.evidence)} tool result(s)")
    for index, result in enumerate(st.session_state.evidence, 1):
        status = "Failed" if result["failed"] else "Returned"
        with st.expander(f"{index:02d} · {result['tool']} · {status}"):
            st.markdown("**Requested arguments**")
            st.json(result["args"])
            st.markdown("**Source response**")
            st.json(result["data"])
    if not st.session_state.evidence:
        st.caption("No tool results for the latest turn. Send a research request to inspect its sources.")
    if st.session_state.last_report:
        prefix = "DEMO — FICTIONAL SAMPLE DATA\n\n" if mode == "Demo" else "Crypto research report\n\n"
        st.download_button("Download latest report", data=prefix + st.session_state.last_report,
                           file_name="crypto-research-report.md", mime="text/markdown")

st.divider()
st.caption("CRYPTO RESEARCH · Source-aware analysis · Educational research, not investment advice")
