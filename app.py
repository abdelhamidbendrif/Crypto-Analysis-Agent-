import argparse
import os
import json
import sys
from pathlib import Path

import requests

from dotenv import load_dotenv
from newsapi import NewsApiClient
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from newsapi.newsapi_exception import NewsAPIException

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.checkpoint.memory import InMemorySaver
load_dotenv(Path(__file__).with_name(".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
FREECRYPTO_TOKEN = os.getenv("FREECRYPTO_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

required_keys = {
    "GROQ_API_KEY": GROQ_API_KEY,
    "FREECRYPTO_TOKEN": FREECRYPTO_TOKEN,
    "NEWSAPI_KEY": NEWSAPI_KEY,
}

for name, value in required_keys.items():
    if not value:
        raise ValueError(f"Missing API key: {name}")

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    temperature=0,
    timeout=30,
    max_retries=1,
)

@tool
def crypto_list_tool(limit: int = 25) -> str:
    """Return available cryptocurrency symbols and names.

    Args:
        limit: Maximum number of coins to return, between 1 and 100.

    Returns:
        A JSON string containing the cryptocurrency list.
    """
    limit = max(1, min(limit, 100))
    url = "https://api.freecryptoapi.com/v1/getCryptoList"

    headers = {
        "Authorization": f"Bearer {FREECRYPTO_TOKEN}"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return json.dumps({
            "status": False,
            "error": str(error),
        })

    try:
        data = response.json()
    except ValueError:
        return json.dumps({
            "status": False,
            "error": "Invalid JSON from API",
        })

    if isinstance(data, dict) and isinstance(data.get("result"), list):
        data = data["result"]

    if isinstance(data, list):
        coins = []

        for item in data[:limit]:
            coins.append({
                "symbol": (
                    item.get("symbol")
                    or item.get("Symbol")
                    or item.get("ticker")
                ),
                "name": item.get("name") or item.get("Name") or "",
            })

        return json.dumps({
            "status": True,
            "coins": coins,
        }, indent=2)

    # Preserve error responses and unexpected payloads for inspection.
    return json.dumps(data, indent=2)

    
@tool
def crypto_data_tool(symbol: str) -> str:
    """Fetch current market data for one cryptocurrency.

    Args:
        symbol: Cryptocurrency symbol, such as BTC or ETH.

    Returns:
        A JSON string containing market data or an error.
    """
    url = "https://api.freecryptoapi.com/v1/getData"
    headers = {
        "Authorization": f"Bearer {FREECRYPTO_TOKEN}"
    }
    params = {"symbol": symbol.strip().upper()}

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        return json.dumps({
            "status": False,
            "error": str(error),
        })

    try:
        data = response.json()
    except ValueError:
        return json.dumps({
            "status": False,
            "error": "Invalid JSON from API",
        })
    # Describe metadata that is absent from the API response.
    if isinstance(data, dict) and data.get("status") == "success":
        data["field_context"] = {
            "quote_currency": "not specified in this API response",
            "timestamp_timezone": "not specified in this API response",
            "lowest_highest_period": "not specified in this API response",
            "percentage_change_baseline": "not specified in this API response",
        }

    return json.dumps(data, indent=2)
@tool
def crypto_news_tool(query: str, max_items: int = 5) -> str:
    """Fetch recent English-language news matching a query.

    Args:
        query: Search keywords, such as bitcoin or ethereum.
        max_items: Maximum articles to return, between 1 and 100.

    Returns:
        A JSON string containing condensed articles or an error.
    """
    max_items = max(1, min(max_items, 100))

    try:
        client = NewsApiClient(api_key=NEWSAPI_KEY)

        data = client.get_everything(
            q=query,
            language="en",
            sort_by="publishedAt",
            page=1,
            page_size=max_items,
        )
    except (NewsAPIException, requests.RequestException) as error:
        return json.dumps({
            "status": False,
            "error": str(error),
        })

    articles = []

    for article in (data.get("articles") or [])[:max_items]:
        source = article.get("source") or {}

        articles.append({
            "title": article.get("title"),
            "source": source.get("name"),
            "url": article.get("url"),
            "publishedAt": article.get("publishedAt"),
        })

    result = {
        "status": data.get("status"),
        "totalResults": data.get("totalResults", 0),
        "returned": len(articles),
        "articles": articles,
    }

    return json.dumps(result, indent=2)
# Register the available tools
tools = [
    crypto_list_tool,
    crypto_data_tool,
    crypto_news_tool,
]

# Prepare the node responsible for executing tool calls
tool_node = ToolNode(tools=tools)

  
# Bind tool definitions to the model
llm_with_tools = llm.bind_tools(tools)

# Define the agent's role and operating rules
system_message = SystemMessage(
    content="""
You are a Crypto Market Analyst.

Use tools whenever current cryptocurrency data or news is needed:
- crypto_list_tool: discover supported cryptocurrency symbols.
- crypto_data_tool: retrieve market data for a specific symbol.
- crypto_news_tool: search for relevant cryptocurrency news.

For comparisons, retrieve data for every requested coin and search for
each coin's news when requested. Keep tool results compact.
Use the conversation history to understand follow-up questions, and
retrieve a fresh snapshot when the user asks for current data.

Never invent prices, article details, currency, timezone, range period,
percentage-change baseline, liquidity, or future performance.
Treat field_context as metadata describing what the response does not specify.
Explain tool failures honestly. Never treat a news headline as proof of causation.

The application renders tool-backed final reports directly from the returned
data in English. Focus on gathering the evidence required for the question.
For conversational replies without tool results, match the user's language
and keep internal function names out of the answer.
"""
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


def assistant(state: MessagesState):
    """Call the tool-enabled model with the conversation history."""
    response = llm_with_tools.invoke(
        [system_message] + state["messages"]
    )

    # Finish collecting tools before rendering source-grounded final content.
    if not response.tool_calls:
        report = build_grounded_report(state["messages"])
        if report is not None:
            response = response.model_copy(update={"content": report})

    return {"messages": [response]}
# Create the graph and register its nodes
builder = StateGraph(MessagesState)

builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)

# Start with the assistant
builder.add_edge(START, "assistant")

# Route to tools when requested; otherwise, finish
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)

# Return tool results to the assistant
builder.add_edge("tools", "assistant")

# Compile a graph without conversation persistence
react_graph = builder.compile()

# Compile a graph with in-memory conversation persistence
memory = InMemorySaver()
react_graph_with_memory = builder.compile(checkpointer=memory)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run a crypto analysis test query.")
    parser.add_argument(
        "query",
        nargs="?",
        default="Give me current market data for BTC and explain the key metrics in bullets.",
    )
    args = parser.parse_args()

    # Create the user's test message
    messages = [HumanMessage(content=args.query)]

    # Run the complete agent workflow
    out = react_graph.invoke({"messages": messages})

    # Display the conversation, tool calls, and tool results
    for message in out["messages"]:
        message.pretty_print()
