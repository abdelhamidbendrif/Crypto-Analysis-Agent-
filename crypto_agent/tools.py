"""Tools that fetch, validate, and label cryptocurrency source data."""

import json
from datetime import datetime, timezone

import requests
from langchain_core.tools import tool

from crypto_agent.config import FREECRYPTO_TOKEN, NEWSAPI_KEY
from crypto_agent.data_quality import (
    news_search_query,
    normalize_coins,
    normalize_market_data,
    normalize_news,
)


def _error(provider: str, error_type: str, message: str) -> dict:
    """Return a consistent failure without exposing configured credentials."""
    message = str(message)
    for secret in (FREECRYPTO_TOKEN, NEWSAPI_KEY):
        if secret:
            message = message.replace(secret, "[redacted]")
    return {
        "status": False,
        "provider": provider,
        "error_type": error_type,
        "error": message[:500],
    }


def _fetch_json(provider: str, url: str, headers: dict, params=None):
    """Handle transport, HTTP, JSON, and provider-level failures uniformly."""
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        return None, _error(provider, "timeout", "The source request timed out. Please retry later.")
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        return None, _error(provider, "http_error", f"The source returned HTTP {status}.")
    except requests.RequestException:
        return None, _error(provider, "connection_error", "Could not connect to the data source. Please retry later.")

    try:
        payload = response.json()
    except ValueError:
        return None, _error(provider, "invalid_json", "The source returned invalid JSON.")
    if isinstance(payload, dict) and (
        payload.get("status") in (False, "error", "failed") or payload.get("error")
    ):
        message = payload.get("error") or payload.get("message") or "The source reported an error."
        return None, _error(provider, "provider_error", message)
    return payload, None


def _success(result: dict, provider: str) -> str:
    """Label retrieval time separately from the source's own timestamps."""
    result["provider"] = provider
    result["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return json.dumps(result, indent=2, allow_nan=False)


@tool
def crypto_list_tool(limit: int = 25) -> str:
    """Return unique available cryptocurrency symbols and source-provided names.

    Args:
        limit: Maximum number of coins to return, between 1 and 100.

    Returns:
        A JSON string with records, provenance, warnings, or a source error.
    """
    limit = max(1, min(limit, 100))
    provider = "FreeCryptoAPI"
    payload, error = _fetch_json(
        provider,
        "https://api.freecryptoapi.com/v1/getCryptoList",
        {"Authorization": f"Bearer {FREECRYPTO_TOKEN}"},
    )
    if error:
        return json.dumps(error)
    try:
        result = normalize_coins(payload, limit)
    except ValueError as error:
        return json.dumps(_error(provider, "invalid_response", str(error)))
    return _success(result, provider)


@tool
def crypto_data_tool(symbol: str) -> str:
    """Fetch a validated market snapshot for one cryptocurrency symbol.

    Args:
        symbol: Cryptocurrency symbol, such as BTC or ETH.

    Returns:
        Source values with explicit missing metadata and retrieval provenance.
        Quote currency, periods, and timezone remain unknown unless provided.
    """
    provider = "FreeCryptoAPI"
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 100:
        return json.dumps(_error(provider, "invalid_input", "Provide a nonempty cryptocurrency symbol of at most 100 characters."))
    payload, error = _fetch_json(
        provider,
        "https://api.freecryptoapi.com/v1/getData",
        {"Authorization": f"Bearer {FREECRYPTO_TOKEN}"},
        params={"symbol": symbol},
    )
    if error:
        return json.dumps(error)
    try:
        result = normalize_market_data(payload, symbol)
    except ValueError as error:
        return json.dumps(_error(provider, "invalid_response", str(error)))
    return _success(result, provider)


@tool
def crypto_news_tool(query: str, max_items: int = 5) -> str:
    """Fetch unique recent English-language news matching article titles.

    Args:
        query: Search keywords or a supported ticker, such as bitcoin or ETH.
        max_items: Maximum articles to return, between 1 and 100.

    Returns:
        A JSON string with original attribution, retrieval time, and filtering
        counts. Fewer articles may remain after validation and deduplication.
    """
    provider = "NewsAPI"
    query = query.strip()
    max_items = max(1, min(max_items, 100))
    if not query or len(query) > 500:
        return json.dumps(_error(provider, "invalid_input", "Provide search keywords between 1 and 500 characters."))

    # Direct HTTP supports searchIn, which the installed SDK does not expose.
    payload, error = _fetch_json(
        provider,
        "https://newsapi.org/v2/everything",
        {"X-Api-Key": NEWSAPI_KEY},
        params={
            "q": news_search_query(query),
            "searchIn": "title",
            "language": "en",
            "sortBy": "publishedAt",
            "page": 1,
            "pageSize": min(100, max(20, max_items * 3)),
        },
    )
    if error:
        return json.dumps(error)
    try:
        result = normalize_news(payload, query, max_items)
    except ValueError as error:
        return json.dumps(_error(provider, "invalid_response", str(error)))
    result["query"] = query
    return _success(result, provider)
