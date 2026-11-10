"""Offline checks for provider failures, record validation, and news quality."""

import json
import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import requests
from langchain_core.messages import HumanMessage, ToolMessage


with (
    patch.dict(os.environ, {
        "GROQ_API_KEY": "gsk-offline-test-placeholder",
        "FREECRYPTO_TOKEN": "offline-crypto-placeholder",
        "NEWSAPI_KEY": "offline-news-placeholder",
    }),
    patch("dotenv.load_dotenv", return_value=False),
):
    from crypto_agent import tools as api_tools
    from crypto_agent.reporting import build_grounded_report


def quote(**updates):
    """Provide a source quote with deliberately unspecified units and periods."""
    record = {
        "symbol": "BTC",
        "last": "76062.010000000000001",
        "last_btc": "1",
        "lowest": "75606.23",
        "highest": "76188",
        "date": "2026-11-10 10:00:00",
        "daily_change_percentage": "-0.48048641521493",
        "source_exchange": "binance",
    }
    record.update(updates)
    return {"status": "success", "symbols": [record]}


def article(title, url, **updates):
    """Provide the raw NewsAPI shape, including its nested source."""
    record = {
        "title": title,
        "url": url,
        "source": {"name": "Example News"},
        "publishedAt": "2026-11-09T10:00:00Z",
    }
    record.update(updates)
    return record


class ProviderToolTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Unexpected network request"),
        )
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def invoke(self, tool, payload, arguments):
        response = Mock()
        response.json.return_value = payload
        with patch("crypto_agent.tools.requests.get", return_value=response) as request:
            result = json.loads(tool.invoke(arguments))
        return result, request

    def test_coin_validation_and_deduplication_precede_limit(self):
        payload = {"status": True, "result": [
            None, {}, {"symbol": "btc", "name": ""},
            {"symbol": "BTC", "name": ""}, {"symbol": "ETH", "name": "Ethereum"},
        ]}
        result, _ = self.invoke(api_tools.crypto_list_tool, payload, {"limit": 2})
        self.assertEqual([coin["symbol"] for coin in result["coins"]], ["BTC", "ETH"])
        self.assertIsNone(result["coins"][0]["name"])
        self.assertEqual(result["coins"][1]["name"], "Ethereum")
        self.assertTrue(result["warnings"])

    def test_bare_coin_list_remains_supported(self):
        result, _ = self.invoke(
            api_tools.crypto_list_tool, [{"Symbol": "BTC", "Name": "Bitcoin"}], {"limit": 1},
        )
        self.assertEqual(result["coins"], [{"symbol": "BTC", "name": "Bitcoin"}])

    def test_malformed_coin_payload_is_an_error(self):
        for payload in ({"result": "not a list"}, {"result": [None, {}]}):
            with self.subTest(payload=payload):
                result, _ = self.invoke(api_tools.crypto_list_tool, payload, {"limit": 5})
                self.assertIs(result["status"], False)
                self.assertEqual(result["error_type"], "invalid_response")

    def test_provider_failure_is_not_converted_into_success(self):
        result, _ = self.invoke(
            api_tools.crypto_list_tool,
            {"status": False, "result": [], "error": "No access"},
            {"limit": 5},
        )
        self.assertIs(result["status"], False)
        self.assertEqual(result["error_type"], "provider_error")
        self.assertIn("No access", result["error"])

    def test_provider_errors_redact_configured_tokens(self):
        result, _ = self.invoke(
            api_tools.crypto_list_tool,
            {"status": False, "error": f"Invalid token {api_tools.FREECRYPTO_TOKEN}"},
            {"limit": 5},
        )
        self.assertNotIn(api_tools.FREECRYPTO_TOKEN, result["error"])
        self.assertIn("[redacted]", result["error"])

    def test_quote_preserves_precision_and_distinguishes_retrieval_time(self):
        result, request = self.invoke(api_tools.crypto_data_tool, quote(), {"symbol": " btc "})
        self.assertEqual(result["symbols"][0]["last"], "76062.010000000000001")
        self.assertEqual(result["symbols"][0]["date"], "2026-11-10 10:00:00")
        self.assertEqual(request.call_args.kwargs["params"], {"symbol": "BTC"})
        self.assertEqual(result["provider"], "FreeCryptoAPI")
        self.assertIsNotNone(datetime.fromisoformat(result["fetched_at"]).tzinfo)
        for value in result["field_context"].values():
            self.assertIn("not specified", value)

    def test_invalid_or_nonpositive_prices_are_rejected(self):
        for price in ("NaN", "Infinity", "-Infinity", True, None, "0", "-1"):
            with self.subTest(price=price):
                result, _ = self.invoke(api_tools.crypto_data_tool, quote(last=price), {"symbol": "BTC"})
                self.assertIs(result["status"], False)
                self.assertEqual(result["error_type"], "invalid_response")

    def test_invalid_optional_metrics_become_missing_with_warning(self):
        result, _ = self.invoke(
            api_tools.crypto_data_tool,
            quote(lowest="-1", highest="NaN", daily_change_percentage=True),
            {"symbol": "BTC"},
        )
        self.assertEqual(result["status"], "success")
        for field in ("lowest", "highest", "daily_change_percentage"):
            self.assertIsNone(result["symbols"][0][field])
        self.assertEqual(len(result["warnings"]), 3)

    def test_wrong_symbol_cannot_be_presented_as_requested_coin(self):
        result, _ = self.invoke(api_tools.crypto_data_tool, quote(symbol="ETH"), {"symbol": "BTC"})
        self.assertIs(result["status"], False)
        self.assertIn("BTC", result["error"])

    def test_explicit_metadata_is_preserved_instead_of_overwritten(self):
        payload = quote(quote_currency="USD", timestamp_timezone="UTC")
        payload["lowest_highest_period"] = "24 hours"
        payload["percentage_change_baseline"] = "source-documented baseline"
        result, _ = self.invoke(api_tools.crypto_data_tool, payload, {"symbol": "BTC"})
        self.assertEqual(result["field_context"]["quote_currency"], "USD")
        self.assertEqual(result["field_context"]["timestamp_timezone"], "UTC")
        self.assertEqual(result["field_context"]["lowest_highest_period"], "24 hours")

    def test_empty_or_oversized_inputs_do_not_contact_providers(self):
        cases = [
            (api_tools.crypto_data_tool, {"symbol": " "}),
            (api_tools.crypto_news_tool, {"query": " "}),
            (api_tools.crypto_news_tool, {"query": "x" * 501}),
        ]
        for tool, arguments in cases:
            with self.subTest(arguments=arguments), patch("crypto_agent.tools.requests.get") as request:
                result = json.loads(tool.invoke(arguments))
                self.assertIs(result["status"], False)
                self.assertEqual(result["error_type"], "invalid_input")
                request.assert_not_called()

    def test_news_uses_title_search_and_ticker_aliases(self):
        result, request = self.invoke(
            api_tools.crypto_news_tool,
            {"status": "ok", "totalResults": 1, "articles": [
                article("Ethereum network update", "https://example.com/eth"),
            ]},
            {"query": "ETH", "max_items": 1},
        )
        parameters = request.call_args.kwargs["params"]
        self.assertEqual(parameters["searchIn"], "title")
        self.assertIn("ethereum", parameters["q"])
        self.assertEqual(parameters["sortBy"], "publishedAt")
        self.assertIn("X-Api-Key", request.call_args.kwargs["headers"])
        self.assertNotIn("apiKey", parameters)
        self.assertEqual(result["returned"], 1)

    def test_news_filters_duplicates_removed_invalid_and_off_topic_records(self):
        records = [
            article("Bitcoin update", "https://example.com/a?utm_source=one"),
            article("Another Bitcoin headline", "https://example.com/a?utm_source=two#top"),
            article(" Bitcoin   update ", "https://example.org/duplicate-title"),
            article("Tether network update", "https://example.com/tether"),
            article("[Removed]", "https://example.com/removed"),
            article("Bitcoin invalid link", "javascript:alert(1)"),
            None,
            article("BTC market report", "https://example.com/b"),
        ]
        result, _ = self.invoke(
            api_tools.crypto_news_tool, {"status": "ok", "totalResults": 100, "articles": records},
            {"query": "bitcoin", "max_items": 3},
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["filtered_out"], 6)
        self.assertEqual(result["scanned"], 8)
        self.assertEqual(result["totalResults"], 100)
        self.assertEqual(result["articles"][0]["url"], "https://example.com/a?utm_source=one")
        self.assertTrue(result["warnings"])

    def test_ether_alias_does_not_match_tether(self):
        payload = {"status": "ok", "totalResults": 2, "articles": [
            article("Tether rises", "https://example.com/tether"),
            article("Ether protocol update", "https://example.com/ether"),
        ]}
        result, _ = self.invoke(api_tools.crypto_news_tool, payload, {"query": "ETH", "max_items": 5})
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["articles"][0]["title"], "Ether protocol update")

    def test_compound_news_query_keeps_provider_query_semantics(self):
        payload = {"status": "ok", "totalResults": 2, "articles": [
            article("Bitcoin update", "https://example.com/btc"),
            article("Ethereum update", "https://example.com/eth"),
        ]}
        result, request = self.invoke(
            api_tools.crypto_news_tool, payload, {"query": "bitcoin OR ethereum", "max_items": 2},
        )
        self.assertEqual(request.call_args.kwargs["params"]["q"], "bitcoin OR ethereum")
        self.assertEqual(result["returned"], 2)

    def test_partial_news_attribution_is_not_fabricated(self):
        payload = {"status": "ok", "totalResults": 1, "articles": [
            article("Bitcoin update", "https://example.com/btc", source=None, publishedAt=None),
        ]}
        result, _ = self.invoke(api_tools.crypto_news_tool, payload, {"query": "BTC", "max_items": 1})
        self.assertIsNone(result["articles"][0]["source"])
        self.assertIsNone(result["articles"][0]["publishedAt"])

    def test_timeout_and_http_errors_are_structured(self):
        http_response = Mock(status_code=429)
        cases = [
            (requests.Timeout(), "timeout"),
            (requests.HTTPError(response=http_response), "http_error"),
            (requests.ConnectionError(), "connection_error"),
        ]
        for error, expected in cases:
            with self.subTest(error=expected), patch("crypto_agent.tools.requests.get", side_effect=error):
                result = json.loads(api_tools.crypto_data_tool.invoke({"symbol": "BTC"}))
                self.assertIs(result["status"], False)
                self.assertEqual(result["error_type"], expected)

    def test_invalid_json_and_news_shape_are_structured_errors(self):
        response = Mock()
        response.json.side_effect = ValueError("invalid JSON")
        with patch("crypto_agent.tools.requests.get", return_value=response):
            result = json.loads(api_tools.crypto_news_tool.invoke({"query": "BTC"}))
        self.assertEqual(result["error_type"], "invalid_json")
        result, _ = self.invoke(api_tools.crypto_news_tool, {"status": "ok", "articles": None}, {"query": "BTC"})
        self.assertEqual(result["error_type"], "invalid_response")

    def test_report_displays_provider_and_quality_notes(self):
        result, _ = self.invoke(
            api_tools.crypto_data_tool, quote(highest="NaN"), {"symbol": "BTC"},
        )
        report = build_grounded_report([
            HumanMessage(content="Fetch BTC."),
            ToolMessage(name="crypto_data_tool", tool_call_id="test", content=json.dumps(result)),
        ])
        self.assertIn("FreeCryptoAPI", report)
        self.assertIn(result["fetched_at"], report)
        self.assertIn("Data quality note", report)
        self.assertNotIn("$", report)
        self.assertNotIn("24-hour", report)


if __name__ == "__main__":
    unittest.main()
