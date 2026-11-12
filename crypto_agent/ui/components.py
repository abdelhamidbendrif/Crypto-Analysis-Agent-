"""Reusable, source-aware presentation components for the research workspace."""

from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlsplit

import streamlit as st

from crypto_agent.workspace import market_rows


def safe_url(value):
    """Allow source links only for ordinary HTTP(S) destinations."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username:
            return value
    except ValueError:
        pass
    return None


def price_text(value):
    """Add grouping separators without rounding the source's decimal precision."""
    try:
        number = Decimal(str(value))
        if number.is_finite():
            return format(number, ",f")
    except InvalidOperation:
        pass
    return "Unavailable"


def market_cards(evidence):
    rows = market_rows(evidence)
    if not rows:
        st.caption("No market snapshot in the latest request. Ask the analyst to fetch a coin's data.")
        return
    cards = []
    for row in rows[:4]:
        symbol = escape(str(row["Symbol"]))
        currency = row["Quote currency"]
        quote = "USD · sample" if currency == "USD (fictional sample)" else currency
        if not quote or "not specified" in quote.lower():
            quote = "Quote unspecified"
        change = row["Reported change (%)"]
        color, display_change = "", "Not provided"
        try:
            number = Decimal(str(change))
            if number.is_finite():
                rounded = format(number, "+.2f")
                approximation = "≈ " if Decimal(rounded) != number else ""
                display_change = f"{approximation}{rounded}%"
                color = "positive" if number >= 0 else "negative"
        except InvalidOperation:
            pass
        cards.append(f'<article class="snapshot" aria-label="{symbol} market snapshot">'
                     f'<div class="snapshot-top"><span class="coin-mark" aria-hidden="true">{symbol[:1]}</span>'
                     f'<span class="coin-label">{symbol}</span><span class="quote-label">{escape(quote)}</span></div>'
                     f'<div class="quote-value">{escape(price_text(row["Last reported"]))}</div>'
                     f'<div class="quote-change"><span class="{color}">{escape(display_change)}</span> · reported change</div></article>')
    st.markdown('<div class="snapshot-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    with st.expander("Snapshot source details"):
        for row in rows:
            st.caption(f"{row['Symbol']} · {row['Provider']} · {row['Exchange']} · Source time: {row['Source timestamp']}")
            st.caption(f"Quote: {row['Quote currency']} · Timezone: {row['Timestamp timezone']} · Retrieved: {row['Retrieved at']}")


def news_panel(evidence, limit=3):
    articles = []
    for result in evidence:
        if result["tool"] == "crypto_news_tool" and not result["failed"]:
            articles.extend(result["data"].get("articles", []))
    if not articles:
        st.markdown('<div class="empty-note">Your research, in context.<br>Request news to see headlines with publishers, dates and original links.</div>', unsafe_allow_html=True)
        return False
    for article in articles[:limit]:
        title = escape(str(article.get("title") or "Untitled"))
        url = safe_url(article.get("url"))
        title_html = (f'<a class="news-title" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title} ↗</a>'
                      if url else f'<span class="news-title">{title}</span>')
        source = escape(str(article.get("source") or "Publisher not provided"))
        published = escape(str(article.get("publishedAt") or "Publication time not provided"))
        st.markdown(f'<article class="news-item">{title_html}<div class="news-meta">{source}<br>{published}</div></article>', unsafe_allow_html=True)
    return True


def comparison_panel(evidence, compact=False):
    rows = market_rows(evidence)
    if not rows:
        st.caption("Fetch two assets to inspect their reported metrics side by side.")
        return
    fields = ["Last reported", "Reported change (%)", "Reported low", "Reported high", "Quote currency"]
    table = [{"Metric": metric, **{row["Symbol"]: row[metric] or "Not provided" for row in rows}}
             for metric in fields]
    st.table(table)
    if len({row["Symbol"] for row in rows}) < 2:
        st.caption("One snapshot returned. Fetch a comparison to request both assets.")
    st.caption("Units, periods and change baselines must match before comparing performance.")
    if not compact:
        with st.expander("Timestamps, periods & provenance"):
            details = [{"Metric": metric, **{row["Symbol"]: row[metric] or "Not provided" for row in rows}}
                       for metric in rows[0] if metric not in ["Symbol", *fields]]
            st.table(details)


def response_sources(evidence, elapsed=None):
    """Associate actual tool provenance and original links with one AI response."""
    if not evidence:
        st.caption("Conversational reply · no tools used for this turn")
        return
    with st.expander(f"Sources & tools · {len(evidence)} result(s)"):
        providers = sorted({str(item["data"].get("provider")) for item in evidence if item["data"].get("provider")})
        st.markdown("".join(f'<span class="source-chip">{escape(provider)}</span>' for provider in providers), unsafe_allow_html=True)
        if elapsed is not None:
            st.caption(f"Completed in {elapsed:.1f}s")
        for item in evidence:
            status = "Failed" if item["failed"] else "Returned"
            st.caption(f"{item['tool']} · {status}")
            for article in item["data"].get("articles", []):
                url = safe_url(article.get("url"))
                if url:
                    st.link_button(str(article.get("title") or "Original article"), url)
            st.json({"arguments": item["args"], "response": item["data"]}, expanded=False)


def report_text(content, mode):
    prefix = "DEMO — FICTIONAL SAMPLE DATA" if mode == "Demo" else "Crypto Research AI"
    return f"# {prefix}\n\n{content}"
