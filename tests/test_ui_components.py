"""Design-token contrast and safe source presentation checks."""

from unittest import TestCase

from crypto_agent.ui.components import price_text, report_text, safe_url
from crypto_agent.ui.state import (
    change_mode, initialize, new_conversation, open_conversation, save_conversation,
)
from crypto_agent.ui.theme import THEMES
from crypto_agent.ui.design import TOKENS


def luminance(hex_color):
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))


class PresentationTests(TestCase):
    def test_imported_design_palette_has_readable_text_and_actions(self):
        for name, tokens in TOKENS.items():
            for foreground, background in (("ink", "surface"), ("muted", "surface"),
                                          ("muted", "bg"), ("accent", "accent_soft"),
                                          ("accent_ink", "accent"), ("up", "surface"),
                                          ("down", "surface")):
                values = sorted((luminance(tokens[foreground]), luminance(tokens[background])))
                self.assertGreaterEqual((values[1] + .05) / (values[0] + .05), 4.5,
                                        f"Imported {name}: {foreground} on {background}")

    def test_both_themes_have_readable_text_and_actions(self):
        for name, tokens in THEMES.items():
            for foreground, background in (("ink", "surface"), ("muted", "surface"),
                                          ("muted", "page"), ("accent", "accent_soft"),
                                          ("action_text", "action"), ("positive", "surface"),
                                          ("negative", "surface")):
                values = sorted((luminance(tokens[foreground]), luminance(tokens[background])))
                self.assertGreaterEqual((values[1] + .05) / (values[0] + .05), 4.5,
                                        f"{name}: {foreground} on {background}")

    def test_source_links_exclude_unsafe_protocols_and_credentials(self):
        for url in ("javascript:alert(1)", "data:text/html,unsafe", "https://user:pass@example.com", "https://[broken"):
            self.assertIsNone(safe_url(url))
        self.assertEqual(safe_url("https://example.com/story?x=1"), "https://example.com/story?x=1")

    def test_prices_keep_precision_and_do_not_infer_currency(self):
        self.assertEqual(price_text("75000.01234567"), "75,000.01234567")
        self.assertEqual(price_text("NaN"), "Unavailable")
        self.assertNotIn("$", price_text("75000"))

    def test_export_marks_demo_and_keeps_original_report(self):
        self.assertIn("FICTIONAL", report_text("original content", "Demo"))
        self.assertTrue(report_text("original content", "Live APIs").endswith("original content"))


class ConversationStateTests(TestCase):
    def test_resuming_live_graph_preserves_the_original_checkpoint_object(self):
        state = {"mode": "Live APIs"}
        initialize(state)
        original = state["thread_id"]
        graph = object()
        state.update(chat=[{"role": "user", "content": "BTC"}], live_graph=graph)
        new_conversation(state)
        self.assertNotIn("live_graph", state)
        open_conversation(state, original)
        self.assertIs(state["live_graph"], graph)

    def test_failed_checkpoint_cannot_be_restored(self):
        state = {}
        initialize(state)
        original = state["thread_id"]
        state["chat"] = [{"role": "user", "content": "BTC"}]
        save_conversation(state)
        new_conversation(state, archive=False)
        self.assertNotIn(original, state["conversations"])

    def test_cross_mode_restore_is_rejected(self):
        state = {}
        initialize(state)
        original = state["thread_id"]
        state["chat"] = [{"role": "user", "content": "BTC"}]
        state["mode"] = "Live APIs"
        change_mode(state)
        self.assertEqual(state["conversations"][original]["mode"], "Demo")
        with self.assertRaises(ValueError):
            open_conversation(state, original)
