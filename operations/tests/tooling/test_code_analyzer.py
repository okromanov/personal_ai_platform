from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.quality.code_analyzer import analyze_file


class UnusedImportDetectionTests(unittest.TestCase):
    def test_future_annotations_import_is_not_flagged_as_unused(self) -> None:
        # `from __future__ import annotations` is a compiler directive: it
        # never appears as a used Name/Attribute, so a naive unused-import
        # check flags it in nearly every file in the repo.
        source = "from __future__ import annotations\n\nx = 1\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(source, encoding="utf-8")

            result = analyze_file(path)

        self.assertEqual(result["unused"], [])

    def test_genuinely_unused_import_is_still_flagged(self) -> None:
        source = "from __future__ import annotations\n\nimport os\n\nx = 1\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(source, encoding="utf-8")

            result = analyze_file(path)

        unused_names = [item["name"] for item in result["unused"]]
        self.assertEqual(unused_names, ["os"])


if __name__ == "__main__":
    unittest.main()
