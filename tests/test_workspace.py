"""Offline coverage for the browser workspace and its demo boundary."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage
from streamlit.testing.v1 import AppTest

from crypto_agent.workspace import current_evidence, demo_turn, market_rows


APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class WorkspaceEvidenceTests(TestCase):
    def test_demo_followup_uses_same_coin_without_old_quotes(self):
        first = demo_turn("Market data for BTC", [])
        second = demo_turn("Three news articles about the same cryptocurrency", first["messages"])
        evidence = current_evidence(second["messages"])
        self.assertEqual([item["tool"] for item in evidence], ["crypto_news_tool"])
        self.assertEqual(evidence[0]["args"]["query"], "bitcoin")
        self.assertEqual(market_rows(evidence), [])
        third = demo_turn("And Ethereum?", second["messages"])
        self.assertEqual(current_evidence(third["messages"])[0]["args"]["query"], "ethereum")

    def test_demo_comparison_is_explicitly_fictional(self):
        result = demo_turn("Compare BTC and ETH", [])
        rows = market_rows(current_evidence(result["messages"]))
        self.assertEqual({row["Symbol"] for row in rows}, {"BTC", "ETH"})
        self.assertTrue(all("fictional" in row["Quote currency"] for row in rows))
        self.assertIn("fictional", result["messages"][-1].content)

    def test_unsupported_demo_prompt_does_not_reuse_a_prior_asset(self):
        first = demo_turn("BTC snapshot", [])
        result = demo_turn("Give me data for SOL", first["messages"])
        self.assertEqual(current_evidence(result["messages"]), [])
        self.assertIn("scripted demo", result["messages"][-1].content)


class WorkspaceUITests(TestCase):
    def setUp(self):
        # A UI test must not make model or provider calls, even after a regression.
        self.network = patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected network"))
        self.httpx = patch("httpx.Client.send", side_effect=AssertionError("Unexpected model call"))
        self.network.start()
        self.httpx.start()
        self.addCleanup(self.network.stop)
        self.addCleanup(self.httpx.stop)
        self.live = patch("crypto_agent.workspace.build_live_graph", side_effect=AssertionError("Unexpected live initialization"))
        self.build_live = self.live.start()
        self.addCleanup(self.live.stop)

    def open_app(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        self.assertEqual(list(app.exception), [])
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertEqual(list(app.exception), [])

    def test_demo_loads_without_credentials_and_comparison_has_both_assets(self):
        app = self.open_app()
        self.assertEqual(app.radio[0].value, "Demo")
        self.assertIn("fictional", app.info[0].value)
        self.assertEqual(len(app.metric), 2)
        self.click(app, "Fetch comparison")
        self.assertEqual(list(app.dataframe[0].value.columns), ["Metric", "BTC", "ETH"])
        self.assertEqual(len(app.chat_message), 2)
        self.build_live.assert_not_called()

    def test_chat_followup_and_new_conversation(self):
        app = self.open_app()
        self.click(app, "BTC snapshot")
        thread = app.session_state["thread_id"]
        app.chat_input[0].set_value("Three news articles about the same cryptocurrency").run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.chat_message), 4)
        self.assertEqual(len(app.metric), 0)
        self.assertEqual(app.session_state["evidence"][0]["args"]["query"], "bitcoin")
        self.click(app, "New conversation")
        self.assertEqual(app.session_state["chat"], [])
        self.assertNotEqual(app.session_state["thread_id"], thread)

    def test_live_is_lazy_and_mode_switch_clears_demo_context(self):
        app = self.open_app()
        self.click(app, "BTC snapshot")
        thread = app.session_state["thread_id"]
        app.radio[0].set_value("Live APIs").run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["chat"], [])
        self.assertEqual(app.session_state["evidence"], [])
        self.assertNotEqual(app.session_state["thread_id"], thread)
        self.build_live.assert_not_called()

    def test_live_turn_receives_only_new_input_and_private_thread(self):
        fake_graph = Mock()
        fake_graph.invoke.return_value = {"messages": [HumanMessage(content="Hi"), AIMessage(content="Hello") ]}
        self.build_live.side_effect = None
        self.build_live.return_value = fake_graph
        app = self.open_app()
        app.radio[0].set_value("Live APIs").run()
        thread = app.session_state["thread_id"]
        app.chat_input[0].set_value("Hi").run()
        self.assertEqual(list(app.exception), [])
        args, kwargs = fake_graph.invoke.call_args
        self.assertEqual(len(args[0]["messages"]), 1)
        self.assertEqual(kwargs["config"]["configurable"]["thread_id"], thread)
        self.assertEqual(app.session_state["last_report"], "Hello")
        self.click(app, "New conversation")
        self.assertNotIn("live_graph", app.session_state)

    def test_failed_invocation_resets_context_and_hides_exception_details(self):
        self.build_live.side_effect = RuntimeError("secret-token-must-not-appear")
        app = self.open_app()
        app.radio[0].set_value("Live APIs").run()
        thread = app.session_state["thread_id"]
        app.chat_input[0].set_value("BTC snapshot").run()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["history"], [])
        self.assertEqual(app.session_state["evidence"], [])
        self.assertNotEqual(app.session_state["thread_id"], thread)
        self.assertIn("conversation was reset", app.warning[0].value)
        self.assertNotIn("secret-token", app.warning[0].value)
