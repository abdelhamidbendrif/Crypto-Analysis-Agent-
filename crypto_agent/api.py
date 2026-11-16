"""FastAPI transport for the original crypto analysis agent. No keys reach the UI."""

import os
from math import isfinite
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal
from uuid import UUID

import requests as _requests
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from dotenv import load_dotenv

from crypto_agent.api_service import SessionStore, source_views
from crypto_agent.workspace import current_evidence, demo_turn


Owner = Annotated[UUID, Header(alias="X-Workspace-ID")]
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ---------------------------------------------------------------------------
# CoinGecko chart helpers
# ---------------------------------------------------------------------------

# Supported symbols for the chart route (demo tier only validates these two)
_CG_ID = {"BTC": "bitcoin", "ETH": "ethereum"}

# ---------------------------------------------------------------------------
# Deterministic FICTIONAL fixture data for demo mode.
# These prices are NOT real historical data — clearly labelled fictional.
# BTC: 30 daily closes, 2025-12-03 → 2026-01-01, gentle upward curve 73500→75000.
# ---------------------------------------------------------------------------
_DEMO_BTC_PRICES = [
    73500.0, 73620.0, 73780.0, 73900.0, 74020.0, 74150.0, 74200.0, 74310.0,
    74380.0, 74450.0, 74520.0, 74580.0, 74620.0, 74650.0, 74700.0, 74730.0,
    74760.0, 74790.0, 74810.0, 74840.0, 74860.0, 74880.0, 74900.0, 74920.0,
    74940.0, 74960.0, 74975.0, 74985.0, 74995.0, 75000.0,
]
_DEMO_ETH_PRICES = [
    2420.0, 2426.0, 2432.0, 2437.0, 2441.0, 2445.0, 2448.0, 2451.0,
    2454.0, 2457.0, 2459.0, 2461.0, 2463.0, 2465.0, 2466.0, 2468.0,
    2469.0, 2470.0, 2472.0, 2474.0, 2476.0, 2478.0, 2480.0, 2482.0,
    2484.0, 2487.0, 2490.0, 2493.0, 2497.0, 2500.0,
]
# End date for demo fixture (exclusive upper bound, so last point is 2026-01-01T00:00:00Z)
_DEMO_END_TS = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
_DEMO_DAY_SECS = 86400


def _granularity(days: int) -> str:
    if days == 1:
        return "5-minute"
    if days <= 90:
        return "hourly"
    return "daily"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_demo_fixture(symbol: str, days: int) -> dict:
    """Return daily fictional observations within the available sample range."""
    days = min(days, 30)
    prices = (_DEMO_BTC_PRICES if symbol == "BTC" else _DEMO_ETH_PRICES)[-days:]
    # Align timestamps: last point == _DEMO_END_TS, one per day
    n = len(prices)
    points = []
    for i, price in enumerate(prices):
        ts_unix = _DEMO_END_TS - (n - 1 - i) * _DEMO_DAY_SECS
        ts_iso = datetime.fromtimestamp(ts_unix, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        points.append({"timestamp": ts_iso, "price": price})
    return {
        "symbol": symbol,
        "pair": f"{symbol}/USD",
        "provider": "Demo fixtures",
        "range_days": days,
        "granularity": "daily",
        "refresh_seconds": None,
        "points": points,
        "fetched_at": _now_iso(),
        # IMPORTANT: fictional = True — this data is NOT real
        "fictional": True,
    }


def _fetch_coingecko(symbol: str, days: int) -> dict:
    """Fetch real market-chart data from CoinGecko and return a normalised dict."""
    cg_id = _CG_ID[symbol]
    url = (
        f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart"
        f"?vs_currency=usd&days={days}"
    )
    headers = {}
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    if key:
        headers["x-cg-demo-api-key"] = key

    try:
        resp = _requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        points_by_time = {}
        for timestamp_ms, value in raw["prices"]:
            price = float(value)
            if not isfinite(price) or price <= 0:
                raise ValueError("Invalid price")
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            points_by_time[timestamp] = price
        if not points_by_time:
            raise ValueError("No price observations")
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (401, 403):
            message = "CoinGecko denied access. Check the backend Demo API key and the selected range."
        elif status == 429:
            message = "CoinGecko rate limit reached. Wait before refreshing."
        else:
            message = "CoinGecko data is temporarily unavailable. Try again later."
        return {"_error": True, "message": message, "provider": "CoinGecko"}

    points = [
        {"timestamp": timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"), "price": price}
        for timestamp, price in sorted(points_by_time.items())
    ]
    return {
        "symbol": symbol,
        "pair": f"{symbol}/USD",
        "provider": "CoinGecko",
        "range_days": days,
        "granularity": _granularity(days),
        "points": points,
        "fetched_at": _now_iso(),
        "fictional": False,
        "refresh_seconds": 300 if key else None,
    }


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SessionInput(Input):
    mode: Literal["demo", "live"] = "demo"


class ChatInput(Input):
    message: str = Field(min_length=1, max_length=2000)


class MarketInput(Input):
    symbols: list[str] = Field(min_length=1, max_length=4)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, values):
        values = [value.strip().upper() for value in values]
        if any(not value or len(value) > 100 or any(ord(char) < 32 for char in value) for value in values):
            raise ValueError("Use nonempty cryptocurrency symbols of at most 100 characters")
        return list(dict.fromkeys(values))


class ComparisonInput(MarketInput):
    @field_validator("symbols")
    @classmethod
    def require_two(cls, values):
        if len(values) < 2:
            raise ValueError("Choose at least two different assets")
        return values


class NewsInput(Input):
    query: str = Field(min_length=1, max_length=150)
    max_items: int = Field(default=3, ge=1, le=10)


def create_app(store=None):
    app = FastAPI(title="Crypto Research AI", version="0.1.0")
    app.state.sessions = store if store is not None else SessionStore()
    # Thread-safe chart cache: keyed "{SYMBOL}_{days}" → (payload_dict, perf_counter_timestamp)
    app.state.chart_cache: dict = {}
    app.state.chart_lock: Lock = Lock()
    default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    origins = [value.strip() for value in os.getenv("API_CORS_ORIGINS", default_origins).split(",") if value.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Workspace-ID"],
                       expose_headers=["Content-Disposition"])

    def check_demo_symbols(owner, session_id, symbols):
        record = app.state.sessions.get(str(owner), str(session_id))
        if record.mode == "demo" and any(symbol not in ("BTC", "ETH") for symbol in symbols):
            raise HTTPException(422, "The scripted demo supports BTC and ETH only. Use Live APIs for other assets.")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/demo/preview")
    def preview():
        # Reuse the existing fixtures without creating a conversation or calling APIs.
        market = demo_turn("Compare BTC and ETH", [])
        news = demo_turn("Three news articles about Bitcoin", [])
        return {"mode": "demo", "fictional": True,
                **source_views(current_evidence(market["messages"]) + current_evidence(news["messages"]))}

    @app.post("/api/sessions", status_code=201)
    def new_session(body: SessionInput, x_workspace_id: Owner):
        return app.state.sessions.create(str(x_workspace_id), body.mode)

    @app.get("/api/sessions")
    def sessions(x_workspace_id: Owner):
        return app.state.sessions.list(str(x_workspace_id))

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: UUID, x_workspace_id: Owner):
        record = app.state.sessions.get(str(x_workspace_id), str(session_id))
        return app.state.sessions.present(record)

    @app.post("/api/sessions/{session_id}/chat")
    def chat(session_id: UUID, body: ChatInput, x_workspace_id: Owner):
        return app.state.sessions.execute(str(x_workspace_id), str(session_id), body.message)

    @app.post("/api/sessions/{session_id}/market")
    def market(session_id: UUID, body: MarketInput, x_workspace_id: Owner):
        check_demo_symbols(x_workspace_id, session_id, body.symbols)
        query = f"Give me current market data for {', '.join(body.symbols)}. Preserve source units and timestamps."
        return app.state.sessions.execute(str(x_workspace_id), str(session_id), query,
                                           [("crypto_data_tool", {"symbol": symbol}) for symbol in body.symbols])

    @app.post("/api/sessions/{session_id}/compare")
    def comparison(session_id: UUID, body: ComparisonInput, x_workspace_id: Owner):
        check_demo_symbols(x_workspace_id, session_id, body.symbols)
        query = f"Compare current market data for {' and '.join(body.symbols)}. Preserve source units and timestamps."
        return app.state.sessions.execute(str(x_workspace_id), str(session_id), query,
                                           [("crypto_data_tool", {"symbol": symbol}) for symbol in body.symbols])

    @app.post("/api/sessions/{session_id}/news")
    def news(session_id: UUID, body: NewsInput, x_workspace_id: Owner):
        query = f"Give me {body.max_items} recent news articles about {body.query}."
        return app.state.sessions.execute(str(x_workspace_id), str(session_id), query,
                                           [("crypto_news_tool", {"query": body.query, "max_items": body.max_items})])

    @app.post("/api/sessions/{session_id}/assets")
    def assets(session_id: UUID, x_workspace_id: Owner):
        return app.state.sessions.execute(str(x_workspace_id), str(session_id), "List 25 available cryptocurrencies and their symbols.",
                                           [("crypto_list_tool", {"limit": 25})])

    @app.get("/api/sessions/{session_id}/reports/{turn_id}")
    def report(session_id: UUID, turn_id: UUID, x_workspace_id: Owner):
        content = app.state.sessions.export(str(x_workspace_id), str(session_id), str(turn_id))
        return PlainTextResponse(content, media_type="text/markdown",
                                 headers={"Content-Disposition": 'attachment; filename="crypto-research-report.md"'})

    # -----------------------------------------------------------------------
    # Chart / price-history routes — no workspace authentication required.
    # -----------------------------------------------------------------------

    def _chart_response(symbol: str, days: int, demo: bool) -> dict:
        """Core chart logic: cache lookup → demo fixture or CoinGecko fetch."""
        symbol = symbol.upper()
        if symbol not in _CG_ID:
            raise HTTPException(422, f"Unsupported symbol '{symbol}'. Supported: {', '.join(_CG_ID)}.")
        if not (1 <= days <= 365):
            raise HTTPException(422, "Query parameter 'days' must be between 1 and 365.")

        if demo:
            return _build_demo_fixture(symbol, days)

        cache_key = f"{symbol}_{days}"
        with app.state.chart_lock:
            entry = app.state.chart_cache.get(cache_key)
            if entry is not None:
                payload, cached_at = entry
                if time.perf_counter() - cached_at < (60 if payload.get("_error") else payload["refresh_seconds"] or 300):
                    if payload.get("_error"):
                        raise HTTPException(503, detail=payload)
                    return payload
            result = _fetch_coingecko(symbol, days)
            app.state.chart_cache[cache_key] = (result, time.perf_counter())
            if result.get("_error"):
                raise HTTPException(503, detail=result)
            return result

    @app.get("/api/chart/{symbol}")
    def chart_live(
        symbol: str,
        days: int = Query(default=30, ge=1, le=365),
        demo: bool = Query(default=False),
    ):
        """Live (or demo) chart data for the given symbol.

        * ``demo=false`` (default): fetches real data from CoinGecko with a
          five-minute in-memory cache.
        * ``demo=true``: returns deterministic FICTIONAL fixture data clearly
          labelled with ``fictional: true``.  No external call is made.
        No workspace authentication is required (chart data is not sensitive).
        """
        return _chart_response(symbol, days, demo)

    @app.get("/api/chart/demo/{symbol}")
    def chart_demo(
        symbol: str,
        days: int = Query(default=30, ge=1, le=365),
    ):
        """Dedicated demo chart route — always returns FICTIONAL fixture data.

        Provided as a convenience so the frontend can call a stable path that
        never touches CoinGecko and requires no workspace session.
        """
        return _chart_response(symbol, days, demo=True)

    return app


app = create_app()
