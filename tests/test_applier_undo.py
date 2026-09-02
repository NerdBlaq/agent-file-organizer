import tempfile
import unittest
from pathlib import Path

from file_organizer.core.applier import apply_plan
from file_organizer.core.undo import execute_undo


class TestApplierAndUndo(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.log_dir = self.root / ".file-organizer" / "logs"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_apply_and_undo(self):
        src_dir = self.root / "Downloads"
        src_dir.mkdir()
        test_file = src_dir / "sample.pdf"
        test_file.write_text("sample content")

        dest_base = self.root / "Home"
        dest_base.mkdir()

        plan = {
            "moves": [
                {
                    "src": str(test_file),
                    "action": "move",
                    "dest_dir": "Documents",
                    "reason": "pdf test",
                    "confidence": "high"
                }
            ]
        }

        # Apply plan
        result = apply_plan(plan, base_dir=dest_base, dry_run=False, log_dir=self.log_dir)
        self.assertEqual(result["moved"], 1)
        self.assertFalse(test_file.exists())
        moved_file = dest_base / "Documents" / "sample.pdf"
        self.assertTrue(moved_file.exists())

        # Undo
        log_path = result["log_path"]
        undo_result = execute_undo(log_path, dry_run=False)
        self.assertEqual(undo_result["reverted_count"], 1)
        self.assertTrue(test_file.exists())
        self.assertFalse(moved_file.exists())

    def test_collision_suffixing(self):
        src_dir = self.root / "Downloads"
        src_dir.mkdir()
        f1 = src_dir / "invoice.pdf"
        f1.write_text("new invoice")

        dest_base = self.root / "Home"
        doc_dir = dest_base / "Documents"
        doc_dir.mkdir(parents=True)
        existing = doc_dir / "invoice.pdf"
        existing.write_text("old invoice")

        plan = {
            "moves": [
                {
                    "src": str(f1),
                    "action": "move",
                    "dest_dir": "Documents",
                    "reason": "pdf test",
                    "confidence": "high"
                }
            ]
        }

        result = apply_plan(plan, base_dir=dest_base, dry_run=False, log_dir=self.log_dir)
        self.assertEqual(result["moved"], 1)
        self.assertTrue(existing.exists())
        self.assertEqual(existing.read_text(), "old invoice")

        suffixed = doc_dir / "invoice (1).pdf"
        self.assertTrue(suffixed.exists())
        self.assertEqual(suffixed.read_text(), "new invoice")


if __name__ == "__main__":
    unittest.main()
