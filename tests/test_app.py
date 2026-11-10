"""Offline regression tests for source-grounded crypto reports."""

import json
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# Avoid loading real credentials or making network requests during import.
with (
    patch.dict(os.environ, {
        "GROQ_API_KEY": "gsk-offline-test-placeholder",
        "FREECRYPTO_TOKEN": "offline-test-placeholder",
        "NEWSAPI_KEY": "offline-test-placeholder",
    }),
    patch("dotenv.load_dotenv", return_value=False),
    patch("httpx.Client.send", side_effect=AssertionError("Unexpected network request")),
):
    from crypto_agent import graph as agent_graph
    from crypto_agent.reporting import build_grounded_report


def market_payload(symbol="BTC", price="76062.01"):
    """Return a representative quote without currency or period metadata."""
    return {
        "status": "success",
        "symbols": [{
            "symbol": symbol,
            "last": price,
            "last_btc": "1" if symbol == "BTC" else "0.04",
            "lowest": "75606.23" if symbol == "BTC" else "2900",
            "highest": "76188" if symbol == "BTC" else "3100",
            "date": "2026-11-08 19:26:10",
            "daily_change_percentage": "0.48048641521493",
            "source_exchange": "binance",
        }],
        "field_context": {
            "quote_currency": "not specified in this API response",
            "timestamp_timezone": "not specified in this API response",
            "lowest_highest_period": "not specified in this API response",
            "percentage_change_baseline": "not specified in this API response",
        },
    }


def article_payload(title="Ethereum update", url="https://example.com/ethereum"):
    """Return a compact NewsAPI result with source metadata."""
    return {
        "status": "ok",
        "totalResults": 42,
        "returned": 1,
        "articles": [{
            "title": title,
            "source": "Example News",
            "url": url,
            "publishedAt": "2026-11-07T09:10:11Z",
        }],
    }


def tool_turn(name, payload, args=None, call_id="test-call"):
    """Build a real message sequence for a single tool execution."""
    content = payload if isinstance(payload, str) else json.dumps(payload)
    return [
        HumanMessage(content="Fetch the requested information."),
        AIMessage(content="", tool_calls=[{
            "name": name,
            "args": args or {},
            "id": call_id,
            "type": "tool_call",
        }]),
        ToolMessage(content=content, name=name, tool_call_id=call_id),
    ]


class GroundedReportTests(unittest.TestCase):
    def setUp(self):
        # Any missed mock must fail rather than contact an external API.
        self.requests_guard = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Unexpected network request"),
        )
        self.httpx_guard = patch(
            "httpx.Client.send",
            side_effect=AssertionError("Unexpected network request"),
        )
        self.requests_guard.start()
        self.httpx_guard.start()
        self.addCleanup(self.requests_guard.stop)
        self.addCleanup(self.httpx_guard.stop)

    def test_market_report_preserves_values_without_invented_metadata(self):
        report = build_grounded_report(tool_turn(
            "crypto_data_tool", market_payload(), {"symbol": "BTC"},
        ))

        self.assertIsInstance(report, str)
        for value in ("BTC", "76062.01", "75606.23", "76188", "binance",
                      "0.48048641521493", "2026-11-08 19:26:10"):
            self.assertIn(value, report)
        self.assertNotIn("$", report)
        self.assertNotIn("USD", report)
        self.assertNotIn("UTC", report)
        self.assertNotIn("24-hour", report)
        self.assertIn("quote currency", report.lower())
        self.assertIn("timezone", report.lower())
        self.assertIn("period", report.lower())
        self.assertIn("baseline", report.lower())
        self.assertIn("not specified", report.lower())

    def test_coin_list_keeps_missing_names_missing(self):
        report = build_grounded_report(tool_turn(
            "crypto_list_tool",
            {"status": True, "coins": [
                {"symbol": "BTC", "name": ""},
                {"symbol": "ETH", "name": ""},
            ]},
            {"limit": 2},
        ))

        self.assertIn("BTC", report)
        self.assertIn("ETH", report)
        self.assertNotIn("Bitcoin", report)
        self.assertNotIn("Ethereum", report)

    def test_news_report_preserves_article_attribution(self):
        report = build_grounded_report(tool_turn(
            "crypto_news_tool", article_payload(),
            {"query": "ethereum", "max_items": 1},
        ))

        for value in ("Ethereum update", "Example News",
                      "https://example.com/ethereum", "2026-11-07T09:10:11Z"):
            self.assertIn(value, report)

    def test_combined_report_includes_every_current_tool_result(self):
        specifications = [
            ("crypto_data_tool", {"symbol": "BTC"}, market_payload()),
            ("crypto_data_tool", {"symbol": "ETH"}, market_payload("ETH", "3000.00")),
            ("crypto_news_tool", {"query": "bitcoin"}, article_payload(
                "Bitcoin source article", "https://example.com/bitcoin")),
            ("crypto_news_tool", {"query": "ethereum"}, article_payload()),
        ]
        calls = [{"name": name, "args": args, "id": f"call-{index}",
                  "type": "tool_call"}
                 for index, (name, args, _) in enumerate(specifications)]
        messages = [HumanMessage(content="Compare BTC and ETH."),
                    AIMessage(content="", tool_calls=calls)]
        messages.extend(
            ToolMessage(content=json.dumps(payload), name=name,
                        tool_call_id=f"call-{index}")
            for index, (name, _, payload) in enumerate(specifications)
        )

        report = build_grounded_report(messages)

        for value in ("BTC", "ETH", "76062.01", "3000.00",
                      "Bitcoin source article", "Ethereum update",
                      "https://example.com/bitcoin", "https://example.com/ethereum"):
            self.assertIn(value, report)
        self.assertNotIn("$", report)

    def test_api_error_is_reported_instead_of_fabricated_data(self):
        report = build_grounded_report(tool_turn(
            "crypto_data_tool", {"status": False, "error": "DNS unavailable"},
            {"symbol": "BTC"},
        ))

        self.assertIn("DNS unavailable", report)
        self.assertNotIn("76062.01", report)

    def test_malformed_tool_json_is_reported(self):
        report = build_grounded_report(tool_turn(
            "crypto_data_tool", "not valid JSON", {"symbol": "BTC"},
        ))

        self.assertIsInstance(report, str)
        self.assertRegex(report.lower(), r"invalid|unreadable|malformed|could not|error")

    def test_invalid_records_are_not_counted_as_valid_evidence(self):
        for name, field in (
            ("crypto_list_tool", "coins"),
            ("crypto_data_tool", "symbols"),
            ("crypto_news_tool", "articles"),
        ):
            with self.subTest(tool=name):
                report = build_grounded_report(tool_turn(
                    name, {"status": "ok", field: [None, {}]},
                ))
                self.assertIn("Data unavailable", report)

        payload = article_payload()
        payload["articles"].append(None)
        report = build_grounded_report(tool_turn("crypto_news_tool", payload))
        self.assertIn("Articles returned: 1", report)
        self.assertNotIn("Articles returned: 2", report)

    def test_new_turn_does_not_reuse_old_tool_results(self):
        history = tool_turn("crypto_data_tool", market_payload(), {"symbol": "BTC"})
        history.append(AIMessage(content="Previous answer."))
        history.append(HumanMessage(content="Hello."))

        self.assertIsNone(build_grounded_report(history))

        new_turn = tool_turn("crypto_news_tool", article_payload(),
                             {"query": "ethereum"}, call_id="new-call")
        report = build_grounded_report(history + new_turn)
        self.assertIn("Ethereum update", report)
        self.assertNotIn("76062.01", report)

    def test_assistant_replaces_unsupported_final_answer(self):
        messages = tool_turn("crypto_data_tool", market_payload(), {"symbol": "BTC"})
        fabricated = AIMessage(content="BTC is $76062.01 UTC with high liquidity.",
                               id="final-message")
        model = Mock()
        model.invoke.return_value = fabricated

        with patch.object(agent_graph, "llm_with_tools", model):
            result = agent_graph.assistant({"messages": messages})

        final = result["messages"][0]
        self.assertIsInstance(final, AIMessage)
        self.assertEqual(final.id, fabricated.id)
        self.assertNotIn("$", final.content)
        self.assertNotIn("UTC", final.content)
        self.assertIn("76062.01", final.content)
        self.assertIs(model.invoke.call_args.args[0][0], agent_graph.system_message)

    def test_assistant_preserves_tool_call_requests(self):
        requested = AIMessage(content="", tool_calls=[{
            "name": "crypto_data_tool", "args": {"symbol": "BTC"},
            "id": "pending-call", "type": "tool_call",
        }])
        model = Mock()
        model.invoke.return_value = requested

        with patch.object(agent_graph, "llm_with_tools", model):
            result = agent_graph.assistant({"messages": [HumanMessage(content="Fetch BTC.")]})

        self.assertIs(result["messages"][0], requested)

    def test_compiled_graph_executes_tool_and_returns_grounded_final_answer(self):
        model = Mock()
        model.invoke.side_effect = [
            AIMessage(content="", tool_calls=[{
                "name": "crypto_data_tool", "args": {"symbol": "BTC"},
                "id": "graph-call", "type": "tool_call",
            }]),
            AIMessage(content="Unsupported $76062.01 UTC answer."),
        ]
        response = Mock()
        response.json.return_value = market_payload()

        with (patch.object(agent_graph, "llm_with_tools", model),
              patch("crypto_agent.tools.requests.get", return_value=response) as request):
            result = agent_graph.react_graph.invoke({"messages": [HumanMessage(content="Fetch BTC.")]})

        self.assertEqual(model.invoke.call_count, 2)
        self.assertEqual(request.call_count, 1)
        self.assertTrue(any(isinstance(message, ToolMessage)
                            for message in result["messages"]))
        final = result["messages"][-1].content
        self.assertIn("76062.01", final)
        self.assertNotIn("$", final)
        self.assertNotIn("UTC", final)

    def test_checkpoint_graph_keeps_history_without_leaking_old_quotes(self):
        model = Mock()
        model.invoke.side_effect = [
            AIMessage(content="", tool_calls=[{
                "name": "crypto_data_tool", "args": {"symbol": "BTC"},
                "id": "memory-btc", "type": "tool_call",
            }]),
            AIMessage(content="Unsupported BTC answer."),
            AIMessage(content="", tool_calls=[{
                "name": "crypto_data_tool", "args": {"symbol": "ETH"},
                "id": "memory-eth", "type": "tool_call",
            }]),
            AIMessage(content="Unsupported ETH answer."),
        ]
        btc_response = Mock()
        btc_response.json.return_value = market_payload()
        eth_response = Mock()
        eth_response.json.return_value = market_payload("ETH", "3000.00")
        config = {"configurable": {"thread_id": f"offline-{uuid4()}"}}

        with (patch.object(agent_graph, "llm_with_tools", model),
              patch("crypto_agent.tools.requests.get", side_effect=[btc_response, eth_response])):
            agent_graph.react_graph_with_memory.invoke(
                {"messages": [HumanMessage(content="Fetch BTC.")]}, config)
            result = agent_graph.react_graph_with_memory.invoke(
                {"messages": [HumanMessage(content="Fetch ETH.")]}, config)

        final = result["messages"][-1].content
        self.assertIn("ETH", final)
        self.assertIn("3000.00", final)
        self.assertNotIn("76062.01", final)
        sent_history = model.invoke.call_args_list[2].args[0]
        self.assertTrue(any(isinstance(message, HumanMessage)
                            and message.content == "Fetch BTC."
                            for message in sent_history))


if __name__ == "__main__":
    unittest.main()
