"""Small in-memory HTTP session adapter around the existing LangGraph workflow."""

from dataclasses import dataclass, field
import json
from datetime import datetime, timezone
from threading import Lock, RLock
from time import monotonic, perf_counter
from uuid import uuid4

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from crypto_agent.workspace import build_live_graph, current_evidence, demo_turn, market_rows
from crypto_agent.reporting import build_grounded_report


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def source_views(evidence):
    """Expose source strings and missing metadata without inferring new metrics."""
    snapshots = [{
        "symbol": row["Symbol"], "last": row["Last reported"],
        "change": row["Reported change (%)"], "low": row["Reported low"], "high": row["Reported high"],
        "quote_currency": row["Quote currency"], "source_timestamp": row["Source timestamp"],
        "timezone": row["Timestamp timezone"], "period": row["Low/high period"],
        "change_baseline": row["Change baseline"], "exchange": row["Exchange"],
        "provider": row["Provider"], "fetched_at": row["Retrieved at"],
    } for row in market_rows(evidence)]
    articles, coins = [], []
    for result in evidence:
        if result["failed"]:
            continue
        data = result["data"]
        if result["tool"] == "crypto_news_tool":
            articles.extend({**article, "query": result["args"].get("query", ""),
                             "provider": data.get("provider"), "fetched_at": data.get("fetched_at")}
                            for article in data.get("articles", []))
        if result["tool"] == "crypto_list_tool":
            coins.extend(data.get("coins", []))
    return {"snapshots": snapshots, "articles": articles, "coins": coins, "evidence": evidence}


@dataclass
class Conversation:
    owner: str
    mode: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)
    touched: float = field(default_factory=monotonic)
    history: list = field(default_factory=list)
    turns: list = field(default_factory=list)
    graph: object = None
    lock: Lock = field(default_factory=Lock)


class SessionStore:
    """Local single-process sessions, with per-conversation invocation exclusion."""

    def __init__(self, graph_factory=None, ttl_seconds=14400, max_sessions=100, tool_runner=None):
        self.graph_factory = graph_factory or build_live_graph
        self.ttl = ttl_seconds
        self.max_sessions = max_sessions
        self.records = {}
        self.guard = RLock()
        self.tool_runner = tool_runner

    def _expire(self):
        expired = [key for key, value in self.records.items()
                   if monotonic() - value.touched > self.ttl and not value.lock.locked()]
        for key in expired:
            del self.records[key]

    def create(self, owner, mode):
        with self.guard:
            self._expire()
            if len(self.records) >= self.max_sessions:
                raise HTTPException(429, "Session capacity reached. Restart the local backend or try later.")
            record = Conversation(owner=owner, mode=mode)
            self.records[record.id] = record
            return self.present(record)

    def get(self, owner, session_id):
        with self.guard:
            self._expire()
            record = self.records.get(session_id)
            if record is None or record.owner != owner:
                raise HTTPException(404, "Conversation not found or expired. Start a new conversation.")
            record.touched = monotonic()
            return record

    @staticmethod
    def summary(record):
        return {"id": record.id, "mode": record.mode, "created_at": record.created_at,
                "updated_at": record.updated_at, "turn_count": len(record.turns),
                "title": record.turns[0]["query"][:80] if record.turns else "New conversation"}

    def present(self, record):
        return {**self.summary(record), "turns": record.turns,
                "busy": record.lock.locked(),
                "latest": source_views(record.turns[-1]["evidence"] if record.turns else [])}

    def list(self, owner):
        with self.guard:
            self._expire()
            return sorted([self.summary(record) for record in self.records.values() if record.owner == owner],
                          key=lambda item: item["updated_at"], reverse=True)

    def _tool_turn(self, record, query, operations):
        """Honor structured controls using original tools and checkpoint the evidence."""
        runner = self.tool_runner
        if runner is None:
            from crypto_agent.tools import crypto_data_tool, crypto_list_tool, crypto_news_tool
            tools = {tool.name: tool for tool in (crypto_data_tool, crypto_list_tool, crypto_news_tool)}
            runner = lambda name, args: tools[name].invoke(args)
        calls = [{"name": name, "args": args, "id": str(uuid4()), "type": "tool_call"}
                 for name, args in operations]
        fresh = [HumanMessage(content=query), AIMessage(content="", tool_calls=calls)]
        for call in calls:
            payload = runner(call["name"], call["args"])
            fresh.append(ToolMessage(content=payload if isinstance(payload, str) else json.dumps(payload),
                                     tool_call_id=call["id"], name=call["name"]))
        fresh.append(AIMessage(content=build_grounded_report(fresh)))
        record.graph.update_state({"configurable": {"thread_id": record.id}},
                                  {"messages": fresh}, as_node="assistant")
        return {"messages": [*record.history, *fresh]}

    def execute(self, owner, session_id, query, operations=None):
        record = self.get(owner, session_id)
        if not record.lock.acquire(blocking=False):
            raise HTTPException(409, "This conversation is still researching. Wait for the current request.")
        started = perf_counter()
        try:
            if len(record.turns) >= 100:
                raise HTTPException(409, "Conversation limit reached. Start a new conversation.")
            try:
                if record.mode == "demo":
                    result = demo_turn(query, record.history)
                else:
                    if record.graph is None:
                        record.graph = self.graph_factory()
                    if operations:
                        result = self._tool_turn(record, query, operations)
                    else:
                        result = record.graph.invoke(
                            {"messages": [HumanMessage(content=query)]},
                            config={"configurable": {"thread_id": record.id}, "recursion_limit": 20},
                        )
                final = next((message for message in reversed(result["messages"])
                              if isinstance(message, AIMessage) and not message.tool_calls), None)
                if final is None or not isinstance(final.content, str) or not final.content.strip():
                    raise ValueError("Missing final response")
                evidence = current_evidence(result["messages"])
                turn = {"id": str(uuid4()), "query": query, "reply": final.content,
                        "evidence": evidence, "elapsed": round(perf_counter() - started, 3), "created_at": now()}
                record.history = result["messages"]
                record.turns = [*record.turns, turn]
                record.updated_at = now()
            except Exception:
                # Drop an incomplete checkpoint; never expose provider exception text.
                record.graph = None
                record.history = []
                record.turns = []
                record.updated_at = now()
                raise HTTPException(502, detail={
                    "message": "Research could not be completed. Check the backend API keys, connection and quotas. Conversation context was reset; please retry.",
                    "context_reset": True,
                }) from None
        finally:
            record.touched = monotonic()
            record.lock.release()
        return self.present(record)

    def export(self, owner, session_id, turn_id):
        record = self.get(owner, session_id)
        turn = next((item for item in record.turns if item["id"] == turn_id), None)
        if turn is None:
            raise HTTPException(404, "Report not found.")
        title = "DEMO — FICTIONAL SAMPLE DATA" if record.mode == "demo" else "Crypto Research AI"
        return f"# {title}\n\n{turn['reply']}\n"
