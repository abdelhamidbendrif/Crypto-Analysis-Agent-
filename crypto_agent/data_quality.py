"""Validate provider records without inventing missing market information."""

import re
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


NEWS_ALIASES = {
    "btc": ("bitcoin", "btc"),
    "bitcoin": ("bitcoin", "btc"),
    "eth": ("ethereum", "ether", "eth"),
    "ethereum": ("ethereum", "ether", "eth"),
    "ether": ("ethereum", "ether", "eth"),
}

UNKNOWN_CONTEXT = {
    "quote_currency": "not specified in this API response",
    "timestamp_timezone": "not specified in this API response",
    "lowest_highest_period": "not specified in this API response",
    "percentage_change_baseline": "not specified in this API response",
}


def clean_text(value) -> str | None:
    """Accept nonempty strings while leaving missing text missing."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def finite_number(value):
    """Preserve numeric precision and reject booleans, NaN, and infinity."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not number.is_finite():
        return None
    return value.strip() if isinstance(value, str) else value


def normalize_coins(payload, limit: int) -> dict:
    """Accept both supported list formats and remove unusable duplicates."""
    records = payload.get("result") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("The source did not return a cryptocurrency list.")

    coins = []
    seen = set()
    skipped = 0
    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue
        symbol = clean_text(record.get("symbol") or record.get("Symbol") or record.get("ticker"))
        if not symbol or symbol.upper() in seen:
            skipped += 1
            continue
        seen.add(symbol.upper())
        coins.append({
            "symbol": symbol.upper(),
            "name": clean_text(record.get("name") or record.get("Name")),
        })
    if records and not coins:
        raise ValueError("The source returned no usable cryptocurrency records.")
    return {
        "status": True,
        "coins": coins[:limit],
        "returned": len(coins[:limit]),
        "warnings": [f"Skipped {skipped} invalid or duplicate coin records."] if skipped else [],
    }


def normalize_market_data(payload, symbol: str) -> dict:
    """Validate a single requested quote and retain source field meanings."""
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list):
        raise ValueError("The source did not return market snapshots.")
    warnings = []
    for record in payload["symbols"]:
        if not isinstance(record, dict):
            continue
        returned_symbol = clean_text(record.get("symbol"))
        if not returned_symbol or returned_symbol.upper() != symbol:
            continue
        price = finite_number(record.get("last"))
        if price is None or Decimal(str(price)) <= 0:
            continue
        snapshot = {"symbol": returned_symbol.upper(), "last": price}
        for field in ("last_btc", "lowest", "highest", "daily_change_percentage"):
            value = finite_number(record.get(field))
            if value is not None and field != "daily_change_percentage" and Decimal(str(value)) < 0:
                value = None
            if value is None and record.get(field) not in (None, ""):
                warnings.append(f"The source's {field} value was invalid and is shown as missing.")
            snapshot[field] = value
        snapshot["date"] = clean_text(record.get("date"))
        snapshot["source_exchange"] = clean_text(record.get("source_exchange"))
        context = payload.get("field_context")
        context = context if isinstance(context, dict) else {}
        return {
            "status": "success",
            "symbols": [snapshot],
            "field_context": {
                field: clean_text(context.get(field)) or clean_text(record.get(field))
                or clean_text(payload.get(field)) or unknown
                for field, unknown in UNKNOWN_CONTEXT.items()
            },
            "warnings": warnings,
        }
    raise ValueError(f"No usable market quote was returned for {symbol}.")


def news_search_query(query: str) -> str:
    """Expand common ticker searches without changing compound query syntax."""
    terms = NEWS_ALIASES.get(query.casefold())
    return "(" + " OR ".join(terms) + ")" if terms else query


def _canonical_url(url: str) -> str | None:
    """Build a duplicate key while preserving meaningful query parameters."""
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        parameters = [
            (key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}
        ]
        return urlunsplit((
            parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"),
            urlencode(sorted(parameters)), "",
        ))
    except ValueError:
        return None


def normalize_news(payload, query: str, max_items: int) -> dict:
    """Keep usable, unique articles and enforce known coin-title matches."""
    if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
        raise ValueError("The news source did not return an article list.")
    terms = NEWS_ALIASES.get(query.casefold())
    pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, terms)) + r")\b", re.I) if terms else None
    articles = []
    seen_urls = set()
    seen_titles = set()
    for record in payload["articles"]:
        if not isinstance(record, dict):
            continue
        title = clean_text(record.get("title"))
        url = clean_text(record.get("url"))
        canonical_url = _canonical_url(url) if url else None
        if not title or title.casefold() == "[removed]" or not canonical_url:
            continue
        if pattern and not pattern.search(title):
            continue
        title_key = " ".join(title.casefold().split())
        if canonical_url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(canonical_url)
        seen_titles.add(title_key)
        source = record.get("source")
        source = source.get("name") if isinstance(source, dict) else source
        articles.append({
            "title": title,
            "source": clean_text(source),
            "url": url,
            "publishedAt": clean_text(record.get("publishedAt")),
        })
    filtered_out = len(payload["articles"]) - len(articles)
    warnings = []
    if filtered_out:
        warnings.append(f"Removed {filtered_out} invalid, duplicate, or off-topic records from this response.")
    selected = articles[:max_items]
    if len(selected) < max_items:
        warnings.append(f"Found {len(selected)} qualifying unique articles in the fetched batch; requested {max_items}.")
    total = payload.get("totalResults")
    return {
        "status": "ok",
        "totalResults": total if type(total) is int and total >= 0 else None,
        "returned": len(selected),
        "scanned": len(payload["articles"]),
        "filtered_out": filtered_out,
        "articles": selected,
        "warnings": warnings,
    }
