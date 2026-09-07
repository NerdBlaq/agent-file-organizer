import tempfile
import unittest
from pathlib import Path

from file_organizer.core.scanner import build_plan, classify, find_duplicates


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_basic_classification(self):
        downloads = self.root / "Downloads"
        downloads.mkdir()

        (downloads / "document.pdf").touch()
        (downloads / "Screenshot_2026.png").touch()
        (downloads / "video_sample.mp4").touch()
        (downloads / "fabric-api-1.20.jar").touch()
        (downloads / "unknown_binary.xyz").touch()

        plan = build_plan(targets=[downloads], quick=True)
        self.assertIn("moves", plan)
        moves = plan["moves"]

        move_map = {Path(m["src"]).name: m["dest_dir"] for m in moves}

        self.assertEqual(move_map.get("document.pdf"), "Documents")
        self.assertEqual(move_map.get("Screenshot_2026.png"), "Pictures/Screenshots")
        self.assertEqual(move_map.get("video_sample.mp4"), "Videos")
        self.assertEqual(move_map.get("fabric-api-1.20.jar"), "Downloads/Mods")
        self.assertEqual(move_map.get("unknown_binary.xyz"), "Downloads/Unsorted")

    def test_duplicates_detection(self):
        folder = self.root / "dups"
        folder.mkdir()

        content = b"identical duplicate content for hashing"
        f1 = folder / "f1.txt"
        f2 = folder / "f2.txt"
        f1.write_bytes(content)
        f2.write_bytes(content)

        dups = find_duplicates([f1, f2])
        self.assertEqual(len(dups), 1)
        self.assertEqual(len(dups[0]), 2)


if __name__ == "__main__":
    unittest.main()
