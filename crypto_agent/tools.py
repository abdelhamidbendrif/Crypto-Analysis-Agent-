import json

import requests
from langchain_core.tools import tool
from newsapi import NewsApiClient
from newsapi.newsapi_exception import NewsAPIException

from crypto_agent.config import FREECRYPTO_TOKEN, NEWSAPI_KEY


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
