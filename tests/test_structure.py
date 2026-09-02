import tempfile
import unittest
from pathlib import Path

from file_organizer.core.structure import scan_directory, classify_scheme, detect_structure


class TestStructure(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_flat_directory(self):
        target = self.root / "flat_test"
        target.mkdir()
        (target / "file1.txt").touch()
        (target / "file2.jpg").touch()

        info = scan_directory(target)
        self.assertIsNotNone(info)
        self.assertEqual(info["loose_file_count"], 2)
        self.assertEqual(info["subdirs"], [])

        scheme, detail = classify_scheme(info["subdirs"])
        self.assertEqual(scheme, "flat")

    def test_by_year_directory(self):
        target = self.root / "year_test"
        target.mkdir()
        (target / "2023").mkdir()
        (target / "2024").mkdir()
        (target / "2025").mkdir()

        info = scan_directory(target)
        self.assertIsNotNone(info)
        scheme, detail = classify_scheme(info["subdirs"])
        self.assertEqual(scheme, "by-year")
        self.assertEqual(detail["year_folders"], ["2023", "2024", "2025"])

    def test_default_taxonomy_directory(self):
        target = self.root / "default_test"
        target.mkdir()
        (target / "screenshots").mkdir()
        (target / "camera").mkdir()

        info = scan_directory(target)
        self.assertIsNotNone(info)
        scheme, detail = classify_scheme(info["subdirs"])
        self.assertEqual(scheme, "matches-default-taxonomy")

    def test_detect_structure_overall(self):
        t1 = self.root / "t1"
        t1.mkdir()
        (t1 / "2024").mkdir()

        report = detect_structure([t1])
        self.assertTrue(report["any_existing_structure"])
        self.assertIn(str(t1), report["directories"])


if __name__ == "__main__":
    unittest.main()
