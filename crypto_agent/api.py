"""FastAPI transport for the original crypto analysis agent. No keys reach the UI."""

import os
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from dotenv import load_dotenv

from crypto_agent.api_service import SessionStore, source_views
from crypto_agent.workspace import current_evidence, demo_turn


Owner = Annotated[UUID, Header(alias="X-Workspace-ID")]
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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

    return app


app = create_app()
