import json

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
def _report_cell(value) -> str:
    """Display source values without allowing them to break Markdown tables."""
    if value is None or value == "":
        return "Not provided"
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def build_grounded_report(messages: list[BaseMessage]) -> str | None:
    """Render only the latest user turn's tool evidence, without model paraphrases.

    English labels match the current course tests. Missing currency, time-zone,
    period, and baseline metadata remain unknown rather than being inferred.
    """
    start = 0
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            start = index + 1

    calls = {}
    sections = []
    kinds = set()
    market_snapshots = {}
    news_counts = []
    coin_count = 0
    for message in messages[start:]:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                calls[call["id"]] = call
            continue
        if not isinstance(message, ToolMessage):
            continue

        call = calls.get(message.tool_call_id, {})
        name = message.name or call.get("name", "")
        args = call.get("args", {})
        title = {
            "crypto_list_tool": "Available cryptocurrencies",
            "crypto_data_tool": "Market data",
            "crypto_news_tool": "News",
        }.get(name, "Source result")
        query = args.get("query") or args.get("symbol")
        if query:
            title += f" - {_report_cell(query)}"

        try:
            data = json.loads(message.content)
        except (TypeError, ValueError):
            sections.append(f"### {title}\nData unavailable: invalid JSON from the source.")
            continue
        if not isinstance(data, dict):
            sections.append(f"### {title}\nData unavailable: unexpected response structure.")
            continue
        if message.status == "error" or data.get("status") in (False, "error", "failed"):
            error = _report_cell(data.get("error") or data.get("message") or "Source request failed")
            sections.append(f"### {title}\nData unavailable: {error}")
            continue

        lines = [f"### {title}"]
        if isinstance(data.get("provider"), str):
            lines.append(f"Data provider: {_report_cell(data['provider'])}")
        if isinstance(data.get("fetched_at"), str):
            lines.append(f"Retrieved at: {_report_cell(data['fetched_at'])}")
        if isinstance(data.get("warnings"), list):
            for warning in data["warnings"]:
                if isinstance(warning, str):
                    lines.append(f"- Data quality note: {_report_cell(warning)}")
        if name == "crypto_list_tool" and isinstance(data.get("coins"), list):
            coins = [coin for coin in data["coins"] if isinstance(coin, dict) and coin.get("symbol")]
            if data["coins"] and not coins:
                sections.append(f"### {title}\nData unavailable: invalid coin records.")
                continue
            kinds.add("coins")
            coin_count += len(coins)
            lines += ["| Symbol | Name |", "|---|---|"]
            for coin in coins:
                lines.append(f"| {_report_cell(coin.get('symbol'))} | {_report_cell(coin.get('name'))} |")
            if not coins:
                lines.append("No coins were returned.")
        elif name == "crypto_data_tool" and isinstance(data.get("symbols"), list):
            snapshots = [coin for coin in data["symbols"] if isinstance(coin, dict) and coin.get("symbol")]
            if data["symbols"] and not snapshots:
                sections.append(f"### {title}\nData unavailable: invalid market records.")
                continue
            kinds.add("market")
            context = data.get("field_context") or {}
            if not isinstance(context, dict):
                context = {}
            for coin in snapshots:
                market_snapshots[str(coin["symbol"])] = coin
                lines += [
                    f"\n**{_report_cell(coin.get('symbol'))}**",
                    "| Metric | Reported value |",
                    "|---|---|",
                ]
                for field, label in (
                    ("last", "Last reported price"),
                    ("last_btc", "Reported BTC-relative value"),
                    ("lowest", "Reported low"),
                    ("highest", "Reported high"),
                    ("daily_change_percentage", "Reported percentage change (%)"),
                    ("date", "Source timestamp"),
                    ("source_exchange", "Source exchange"),
                ):
                    lines.append(f"| {label} | {_report_cell(coin.get(field))} |")
            for field, label in (
                ("quote_currency", "Quote currency"),
                ("timestamp_timezone", "Timestamp timezone"),
                ("lowest_highest_period", "Low/high period"),
                ("percentage_change_baseline", "Percentage-change baseline"),
            ):
                value = context.get(field) or "not specified in this API response"
                lines.append(f"\n- {label}: {_report_cell(value)}")
            if not snapshots:
                lines.append("No market snapshots were returned.")
        elif name == "crypto_news_tool" and isinstance(data.get("articles"), list):
            articles = [article for article in data["articles"] if isinstance(article, dict) and article.get("title")]
            if data["articles"] and not articles:
                sections.append(f"### {title}\nData unavailable: invalid article records.")
                continue
            kinds.add("news")
            news_counts.append(f"{_report_cell(query or 'requested topic')}: {len(articles)}")
            lines.append(f"Articles returned: {len(articles)}; total search matches: {_report_cell(data.get('totalResults'))}.")
            for index, article in enumerate(articles, 1):
                lines += [
                    f"\n{index}. **{_report_cell(article.get('title'))}**",
                    f"   - Source: {_report_cell(article.get('source'))}",
                    f"   - Published: {_report_cell(article.get('publishedAt'))}",
                    f"   - URL: {_report_cell(article.get('url'))}",
                ]
            if not articles:
                lines.append("No articles were returned for this query.")
        else:
            lines.append("Data unavailable: the response does not contain the expected records.")
        sections.append("\n".join(lines))

    if not sections:
        return None

    meaning = []
    if "market" in kinds:
        if len(market_snapshots) > 1:
            changes = "; ".join(
                f"{_report_cell(symbol)}: {_report_cell(coin.get('daily_change_percentage'))}%"
                for symbol, coin in market_snapshots.items()
                if coin.get("daily_change_percentage") is not None
            )
            if changes:
                meaning.append(
                    f"Reported percentage changes: {changes}. "
                    "Without confirmed comparison baselines, these figures do not establish a performance ranking."
                )
        meaning.append(
            "These are source-reported snapshots. Unspecified units, periods, and "
            "comparison baselines remain unknown. These fields alone do not establish "
            "liquidity, measured volatility, support/resistance, or future performance."
        )
    if "news" in kinds:
        meaning.append("Headlines and publication times are copied from the news results; they do not prove why a price moved.")
    if "coins" in kinds:
        meaning.append("Only symbols and names supplied by the data source are listed.")
    if not meaning:
        meaning.append("The requested evidence was unavailable; no market conclusion can be drawn from these results.")

    summary = []
    if market_snapshots:
        summary.append("Market snapshots: " + ", ".join(_report_cell(symbol) for symbol in market_snapshots) + ".")
    if news_counts:
        summary.append("News articles returned - " + "; ".join(news_counts) + ".")
    if "coins" in kinds:
        summary.append(f"Supported coin records returned: {coin_count}.")
    if not summary:
        summary.append("No usable source records were returned. See the source errors below.")

    return (
        "## Summary\n" + " ".join(summary) + "\n\n"
        "## Data\n" + "\n\n".join(sections)
        + "\n\n## What it means\n" + "\n\n".join(meaning)
        + "\n\n## Next steps\nAsk for another supported coin's market snapshot, "
        "relevant news, or the list of supported symbols."
    )
