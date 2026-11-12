"""Offline HTTP contract tests for the React-facing FastAPI layer."""

from unittest import TestCase
from unittest.mock import Mock, patch
import os
from uuid import uuid4

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from crypto_agent.api import create_app
from crypto_agent.api_service import SessionStore


class APITests(TestCase):
    def setUp(self):
        self.factory = Mock(side_effect=AssertionError("Unexpected live graph initialization"))
        self.store = SessionStore(graph_factory=self.factory)
        self.client = TestClient(create_app(self.store))
        self.headers = {"X-Workspace-ID": str(uuid4())}
        self.guard = patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected external API call"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def create(self, mode="demo"):
        response = self.client.post("/api/sessions", headers=self.headers, json={"mode": mode})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def post(self, session, action="chat", body=None):
        return self.client.post(f"/api/sessions/{session['id']}/{action}", headers=self.headers,
                                json=body if body is not None else {"message": "BTC snapshot"})

    def test_health_and_demo_preview_need_no_credentials_or_live_graph(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        preview = self.client.get("/api/demo/preview").json()
        self.assertTrue(preview["fictional"])
        self.assertEqual({item["symbol"] for item in preview["snapshots"]}, {"BTC", "ETH"})
        self.assertTrue(all("fictional" in item["quote_currency"] for item in preview["snapshots"]))
        self.factory.assert_not_called()

    def test_http_chat_preserves_followup_context_and_response_sources(self):
        session = self.create()
        self.assertFalse(session["busy"])
        first = self.post(session).json()
        followup = self.post(session, body={"message": "Three news articles about the same cryptocurrency"}).json()
        self.assertEqual(len(followup["turns"]), 2)
        self.assertEqual(followup["latest"]["articles"][0]["query"], "bitcoin")
        self.assertEqual(followup["latest"]["snapshots"], [])
        self.assertEqual(first["turns"][0]["evidence"][0]["tool"], "crypto_data_tool")
        self.assertEqual(followup["turns"][0]["reply"], first["turns"][0]["reply"])
        self.assertFalse(followup["busy"])

    def test_comparison_and_market_endpoints_reuse_current_report_logic(self):
        session = self.create()
        compared = self.post(session, "compare", {"symbols": ["btc", "ETH"]}).json()
        self.assertEqual({row["symbol"] for row in compared["latest"]["snapshots"]}, {"BTC", "ETH"})
        self.assertIn("Market snapshots: BTC, ETH", compared["turns"][-1]["reply"])
        market = self.post(session, "market", {"symbols": ["eth"]}).json()
        self.assertEqual([row["symbol"] for row in market["latest"]["snapshots"]], ["ETH"])

    def test_news_and_asset_endpoints_return_original_attribution(self):
        session = self.create()
        result = self.post(session, "news", {"query": "Ethereum", "max_items": 3}).json()
        article = result["latest"]["articles"][0]
        self.assertEqual(article["source"], "Sample publisher")
        self.assertTrue(article["url"].startswith("https://example.com/demo/eth/"))
        assets = self.post(session, "assets", {}).json()
        self.assertEqual({coin["symbol"] for coin in assets["latest"]["coins"]}, {"BTC", "ETH"})

    def test_reports_export_exact_existing_reply_with_demo_label(self):
        session = self.create()
        result = self.post(session).json()
        turn = result["turns"][0]
        response = self.client.get(f"/api/sessions/{session['id']}/reports/{turn['id']}", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("FICTIONAL SAMPLE DATA", response.text)
        self.assertIn(turn["reply"], response.text)
        self.assertIn("attachment", response.headers["content-disposition"])
        self.assertIn("text/markdown", response.headers["content-type"])

    def test_new_and_cross_mode_sessions_have_independent_context(self):
        first = self.create()
        self.post(first)
        second = self.create()
        live = self.create("live")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(second["turns"], [])
        self.assertEqual(live["latest"]["snapshots"], [])
        self.factory.assert_not_called()

    def test_workspace_isolation_and_missing_workspace_header(self):
        session = self.create()
        stranger = {"X-Workspace-ID": str(uuid4())}
        self.assertEqual(self.client.get(f"/api/sessions/{session['id']}", headers=stranger).status_code, 404)
        self.assertEqual(self.client.get("/api/sessions", headers=stranger).json(), [])
        self.assertEqual(self.client.get("/api/sessions").status_code, 422)
        self.assertEqual(self.client.get("/api/sessions", headers=self.headers).json()[0]["id"], session["id"])

    def test_validation_rejects_empty_duplicate_or_unsupported_requests(self):
        session = self.create()
        for action, body in (("chat", {"message": "   "}), ("compare", {"symbols": ["BTC", "BTC"]}),
                             ("market", {"symbols": ["LTC"]}), ("market", {"symbols": ["../BTC"]}),
                             ("news", {"query": "BTC", "max_items": 101}),
                             ("chat", {"message": "BTC", "mode": "live"})):
            self.assertEqual(self.post(session, action, body).status_code, 422, body)

    def test_busy_session_returns_conflict_without_resetting_history(self):
        session = self.create()
        self.post(session)
        record = self.store.get(self.headers["X-Workspace-ID"], session["id"])
        record.lock.acquire()
        try:
            self.assertEqual(self.post(session).status_code, 409)
            self.assertEqual(len(record.turns), 1)
        finally:
            record.lock.release()

    def test_live_adapter_uses_existing_graph_with_only_new_user_input(self):
        graph = Mock()
        graph.invoke.return_value = {"messages": [HumanMessage(content="Hello"), AIMessage(content="A live model reply")]}
        self.factory.side_effect = None
        self.factory.return_value = graph
        session = self.create("live")
        result = self.post(session, body={"message": "Hello"}).json()
        args, kwargs = graph.invoke.call_args
        self.assertEqual(len(args[0]["messages"]), 1)
        self.assertEqual(kwargs["config"]["configurable"]["thread_id"], session["id"])
        self.assertEqual(result["turns"][0]["reply"], "A live model reply")
        self.assertEqual(result["latest"]["snapshots"], [])
        self.factory.assert_called_once()

    def test_structured_live_news_honors_requested_limit_and_checkpoints_sources(self):
        graph = Mock()
        self.factory.side_effect = None
        self.factory.return_value = graph
        self.store.tool_runner = Mock(return_value={"status": "ok", "provider": "NewsAPI", "returned": 0,
                                                   "totalResults": 0, "articles": []})
        session = self.create("live")
        response = self.post(session, "news", {"query": "Ethereum", "max_items": 3})
        self.assertEqual(response.status_code, 200)
        self.store.tool_runner.assert_called_once_with("crypto_news_tool", {"query": "Ethereum", "max_items": 3})
        graph.invoke.assert_not_called()
        self.assertEqual(graph.update_state.call_args.kwargs["as_node"], "assistant")
        self.assertEqual(response.json()["turns"][0]["evidence"][0]["args"]["max_items"], 3)

    def test_actual_checkpoint_keeps_structured_results_for_agent_followup(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "offline-key", "FREECRYPTO_TOKEN": "offline", "NEWSAPI_KEY": "offline"}), patch("dotenv.load_dotenv", return_value=False):
            from crypto_agent import graph as agent_graph
        from langgraph.checkpoint.memory import InMemorySaver

        self.store.graph_factory = lambda: agent_graph.builder.compile(checkpointer=InMemorySaver())
        self.store.tool_runner = Mock(return_value={"status": "success", "provider": "FreeCryptoAPI",
                                                   "symbols": [{"symbol": "BTC", "last": "123.4567"}]})
        session = self.create("live")
        response = self.post(session, "market", {"symbols": ["BTC"]})
        self.assertEqual(response.status_code, 200)
        seen = []
        def model(messages):
            seen.extend(messages)
            return AIMessage(content="We discussed BTC.")
        with patch.object(agent_graph, "llm_with_tools", Mock(invoke=model)):
            followup = self.post(session, body={"message": "Which asset did we discuss?"})
        self.assertEqual(followup.status_code, 200)
        self.assertEqual(followup.json()["turns"][-1]["reply"], "We discussed BTC.")
        self.assertTrue(any('123.4567' in str(message.content) for message in seen))
        self.assertEqual(followup.json()["latest"]["snapshots"], [])

    def test_live_failure_discards_checkpoint_and_never_leaks_secrets(self):
        self.factory.side_effect = RuntimeError("private-api-key-do-not-expose")
        session = self.create("live")
        response = self.post(session)
        self.assertEqual(response.status_code, 502)
        self.assertTrue(response.json()["detail"]["context_reset"])
        self.assertNotIn("private-api-key", response.text)
        record = self.store.get(self.headers["X-Workspace-ID"], session["id"])
        self.assertEqual(record.history, [])
        self.assertIsNone(record.graph)

    def test_cors_accepts_only_configured_origins_and_workspace_header(self):
        headers = {"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST",
                   "Access-Control-Request-Headers": "content-type,x-workspace-id"}
        response = self.client.options("/api/sessions", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], headers["Origin"])
        headers["Origin"] = "https://untrusted.example"
        denied = self.client.options("/api/sessions", headers=headers)
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_expired_sessions_and_missing_reports_are_not_returned(self):
        session = self.create()
        missing = self.client.get(f"/api/sessions/{session['id']}/reports/{uuid4()}", headers=self.headers)
        self.assertEqual(missing.status_code, 404)
        self.store.records[session["id"]].touched -= self.store.ttl + 1
        self.assertEqual(self.client.get(f"/api/sessions/{session['id']}", headers=self.headers).status_code, 404)
