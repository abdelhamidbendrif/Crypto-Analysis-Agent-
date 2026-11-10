import argparse
import os
import json
import sys
from pathlib import Path
from crypto_agent.reporting import build_grounded_report

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

from crypto_agent.config import (
    GROQ_API_KEY,
    FREECRYPTO_TOKEN,
    NEWSAPI_KEY,
)


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
