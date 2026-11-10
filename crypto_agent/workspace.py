"""Session helpers and an explicitly simulated, network-free showcase."""

import json
import re
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from crypto_agent.reporting import build_grounded_report


SAMPLE_TIME = "2026-01-01T12:00:00+00:00"
SAMPLE_MARKETS = {
    "BTC": {"symbol": "BTC", "last": "75000.00", "last_btc": "1",
            "lowest": "73500.00", "highest": "75800.00",
            "daily_change_percentage": "1.25", "date": SAMPLE_TIME,
            "source_exchange": "Simulated exchange"},
    "ETH": {"symbol": "ETH", "last": "2500.00", "last_btc": "0.03333333",
            "lowest": "2420.00", "highest": "2540.00",
            "daily_change_percentage": "0.80", "date": SAMPLE_TIME,
            "source_exchange": "Simulated exchange"},
}
SAMPLE_CONTEXT = {
    "quote_currency": "USD (fictional sample)",
    "timestamp_timezone": "UTC (fictional sample)",
    "lowest_highest_period": "24 hours (fictional sample)",
    "percentage_change_baseline": "24 hours earlier (fictional sample)",
}


def sample_market_payload(symbol):
    """Return isolated sample data, never a live quote."""
    return {"status": "success", "provider": "Demo fixtures — fictional data",
            "fetched_at": SAMPLE_TIME, "symbols": [dict(SAMPLE_MARKETS[symbol])],
            "field_context": dict(SAMPLE_CONTEXT),
            "warnings": ["Simulated showcase data. Not a current market quote."]}


def current_evidence(messages):
    """Extract current-turn tool results without reusing older market quotes."""
    start = 0
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            start = index + 1
    calls, evidence = {}, []
    for message in messages[start:]:
        if isinstance(message, AIMessage):
            calls.update({call["id"]: call for call in message.tool_calls})
        elif isinstance(message, ToolMessage):
            call = calls.get(message.tool_call_id, {})
            try:
                payload = json.loads(message.content)
            except (ValueError, TypeError):
                payload = {"status": False, "error": "Invalid source response"}
            if not isinstance(payload, dict):
                payload = {"status": False, "error": "Unexpected source response"}
            evidence.append({"tool": message.name or call.get("name", "Unknown tool"),
                             "args": call.get("args", {}), "data": payload,
                             "failed": message.status == "error" or
                             payload.get("status") in (False, "error", "failed")})
    return evidence


def market_rows(evidence):
    """Keep source values and provenance together for display and export."""
    rows = []
    for result in evidence:
        if result["tool"] != "crypto_data_tool" or result["failed"]:
            continue
        data = result["data"]
        context = data.get("field_context", {})
        for coin in data.get("symbols", []):
            rows.append({"Symbol": coin.get("symbol"), "Last reported": coin.get("last"),
                         "Reported change (%)": coin.get("daily_change_percentage"),
                         "Reported low": coin.get("lowest"), "Reported high": coin.get("highest"),
                         "Quote currency": context.get("quote_currency", "Not specified"),
                         "Source timestamp": coin.get("date", "Not provided"),
                         "Timestamp timezone": context.get("timestamp_timezone", "Not specified"),
                         "Low/high period": context.get("lowest_highest_period", "Not specified"),
                         "Change baseline": context.get("percentage_change_baseline", "Not specified"),
                         "Exchange": coin.get("source_exchange", "Not provided"),
                         "Provider": data.get("provider", "Not provided"),
                         "Retrieved at": data.get("fetched_at", "Not provided")})
    return rows


def build_live_graph():
    """Initialize credentials and a private in-memory graph only in live mode."""
    from langgraph.checkpoint.memory import InMemorySaver
    from crypto_agent.graph import builder

    return builder.compile(checkpointer=InMemorySaver())


def demo_turn(query, history):
    """Simulate supported tools; no LLM, network, or credentials are used."""
    lower = query.lower()
    symbols = [symbol for symbol, pattern in
               (("BTC", r"\b(btc|bitcoin)\b"), ("ETH", r"\b(eth|ethereum|ether)\b"))
               if re.search(pattern, lower)]
    previous = current_evidence(history)
    if not symbols and re.search(r"\b(same|its|it|that cryptocurrency)\b", lower):
        for result in reversed(previous):
            args = result["args"]
            topic = str(args.get("symbol") or args.get("query") or "").lower()
            if topic in ("btc", "bitcoin", "eth", "ethereum"):
                symbols = ["BTC" if topic in ("btc", "bitcoin") else "ETH"]
                break
    wants_news = any(word in lower for word in ("news", "article", "headline"))
    # A short asset-only follow-up keeps the previous request's intent.
    if not wants_news and re.fullmatch(r"\s*(and |what about )?(eth|ethereum|btc|bitcoin)[?.! ]*", lower):
        wants_news = bool(previous and previous[-1]["tool"] == "crypto_news_tool")
    messages = [*history, HumanMessage(content=query)]
    operations = []
    if any(word in lower for word in ("list", "available", "symbols")) and not symbols:
        operations.append(("crypto_list_tool", {"limit": 2}, {
            "status": True, "provider": "Demo fixtures — fictional data",
            "coins": [{"symbol": "BTC", "name": "Bitcoin"},
                      {"symbol": "ETH", "name": "Ethereum"}]}))
    elif symbols:
        for symbol in symbols:
            if wants_news:
                name = "Bitcoin" if symbol == "BTC" else "Ethereum"
                articles = [{"title": f"Sample {name} headline {index}: fictional market research",
                             "source": "Sample publisher", "publishedAt": SAMPLE_TIME,
                             "url": f"https://example.com/demo/{symbol.lower()}/{index}"}
                            for index in range(1, 4)]
                operations.append(("crypto_news_tool", {"query": name.lower(), "max_items": 3},
                                   {"status": "ok", "provider": "Demo fixtures — fictional data",
                                    "returned": 3, "totalResults": 3, "articles": articles,
                                    "warnings": ["Fictional headlines and example.com links for UI demonstration."]}))
            else:
                operations.append(("crypto_data_tool", {"symbol": symbol}, sample_market_payload(symbol)))
    if operations:
        calls = [{"name": name, "args": args, "id": str(uuid4()), "type": "tool_call"}
                 for name, args, _ in operations]
        messages.append(AIMessage(content="", tool_calls=calls))
        messages.extend(ToolMessage(content=json.dumps(payload), name=name, tool_call_id=call["id"])
                        for (name, _, payload), call in zip(operations, calls))
        reply = build_grounded_report(messages)
    else:
        reply = ("This is a scripted demo, with fictional BTC and ETH data. "
                 "Try a market snapshot, compare BTC and ETH, request three sample news articles, "
                 "or list available symbols. Switch to Live APIs for the real agent.")
    messages.append(AIMessage(content=reply))
    return {"messages": messages}
