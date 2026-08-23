from __future__ import annotations

import unittest

from operations.scripts.documents.metadata import parse_front_matter


class FrontMatterParsingTests(unittest.TestCase):
    def test_duplicate_key_is_rejected_instead_of_silently_overwritten(self) -> None:
        text = "---\nid: BR_001\nid: BR_999\ndocument_state: current\n---\n# Title\n"
        with self.assertRaises(ValueError) as ctx:
            parse_front_matter(text)
        self.assertIn("id", str(ctx.exception))

    def test_duplicate_list_key_is_rejected(self) -> None:
        text = "---\ntags:\n  - a\ntags:\n  - b\n---\n# Title\n"
        with self.assertRaises(ValueError):
            parse_front_matter(text)

    def test_inline_list_splits_on_top_level_commas_only(self) -> None:
        text = '---\nid: BR_002\ntags: ["a, b", "c"]\n---\n# Title\n'
        metadata, _ = parse_front_matter(text)
        self.assertEqual(metadata["tags"], ["a, b", "c"])

    def test_inline_list_with_unclosed_quote_is_rejected(self) -> None:
        text = '---\nid: BR_003\ntags: ["a, b]\n---\n# Title\n'
        with self.assertRaises(ValueError):
            parse_front_matter(text)

    def test_empty_inline_list_still_parses(self) -> None:
        metadata, _ = parse_front_matter("---\nid: BR_004\ntags: []\n---\n# Title\n")
        self.assertEqual(metadata["tags"], [])


if __name__ == "__main__":
    unittest.main()
