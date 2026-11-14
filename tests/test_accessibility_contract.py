"""Static accessibility regression tests for the single-page site.

These tests use only Python's standard library so they can run in CI without
installing a browser or third-party parser.
"""
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML_FILE = ROOT / "index.html"


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.ids = {}
        self.label_targets = set()
        self.script_parts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        element_id = attributes.get("id")
        if element_id:
            self.ids[element_id] = (tag, attributes)
        if tag == "label" and attributes.get("for"):
            self.label_targets.add(attributes["for"])
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.script_parts.append(data)


class AccessibilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = HTML_FILE.read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)
        cls.script = "\n".join(cls.parser.script_parts)

    def test_mobile_menu_toggle_is_a_named_button(self):
        tag, attrs = self.parser.ids["mobileBtn"]
        self.assertEqual(tag, "button")
        self.assertEqual(attrs.get("type"), "button")
        self.assertEqual(attrs.get("aria-controls"), "menu")
        self.assertEqual(attrs.get("aria-expanded"), "false")
        self.assertEqual(attrs.get("aria-label"), "Open navigation menu")

    def test_apply_now_cta_links_to_admissions(self):
        tag, attrs = self.parser.ids["applyNow"]
        self.assertEqual(tag, "a")
        self.assertEqual(attrs.get("href"), "#contact")

    def test_primary_navigation_has_an_accessible_name(self):
        tag, attrs = self.parser.ids["menu"]
        self.assertEqual(tag, "nav")
        self.assertTrue(attrs.get("aria-label"))

    def test_every_form_control_has_a_label_and_name(self):
        controls = [
            attrs
            for tag, attrs in self.parser.elements
            if tag in {"input", "textarea"}
        ]
        self.assertGreater(len(controls), 0)
        for attrs in controls:
            with self.subTest(control=attrs.get("id")):
                self.assertTrue(attrs.get("id"))
                self.assertTrue(attrs.get("name"))
                self.assertIn(attrs["id"], self.parser.label_targets)

    def test_form_feedback_is_announced_and_does_not_claim_submission(self):
        tag, attrs = self.parser.ids["formStatus"]
        self.assertEqual(tag, "p")
        self.assertEqual(attrs.get("role"), "status")
        self.assertEqual(attrs.get("aria-live"), "polite")
        self.assertIn("No application was sent", self.html)
        self.assertNotIn("Application submitted successfully", self.html)

    def test_mobile_menu_state_tracks_aria_and_supports_escape(self):
        self.assertIn('setAttribute("aria-expanded",String(isOpen))', self.script)
        self.assertIn('event.key==="Escape"', self.script)
        self.assertIn("mobileBtn.focus()", self.script)
        self.assertIn("setMenuOpen(false)", self.script)

    def test_reduced_motion_and_hidden_menu_state_are_supported(self):
        self.assertIn("@media(prefers-reduced-motion:reduce)", self.html)
        self.assertIn("visibility:hidden", self.html)
        self.assertIn("visibility:visible", self.html)


if __name__ == "__main__":
    unittest.main()
