import tempfile
import unittest
from pathlib import Path

from file_organizer.core.applier import apply_plan, derive_base_from_targets, filesystem_id
from file_organizer.core.scanner import build_plan
from file_organizer.core.verify import verify_recovery
from file_organizer.core.undo import execute_undo
import file_organizer.core.applier as applier_mod


class TestPathIsolation(unittest.TestCase):
    """v1.1.2: fix for a real incident where a scan of an external drive,
    applied with no --base, moved files onto the OS home directory because
    base_dir defaulted to '~' unconditionally."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_base_auto_derived_from_plan_targets(self):
        drive = self.root / "external" / "Documents"
        drive.mkdir(parents=True)
        f = drive / "notes.pdf"
        f.write_text("x")

        plan = {
            "targets": [str(drive)],
            "moves": [{"src": str(f), "dest_dir": "Documents", "confidence": "high"}],
        }
        result = apply_plan(plan, base_dir=None, log_dir=self.root / "logs")

        self.assertEqual(result["base"], str(drive))
        self.assertTrue((drive / "Documents" / "notes.pdf").exists())
        self.assertFalse((self.root / "Documents").exists())  # never touched home-style path

    def test_derive_base_falls_back_to_home_with_no_targets(self):
        base = derive_base_from_targets({"targets": []})
        self.assertEqual(base, Path("~").expanduser())

    def test_cross_filesystem_move_aborts_before_moving_anything(self):
        real_fs = applier_mod.filesystem_id
        def fake_fs(path):
            return 999 if "external" in str(path) else real_fs(path)
        applier_mod.filesystem_id = fake_fs
        try:
            ext = self.root / "external"
            ext.mkdir()
            f = ext / "file.txt"
            f.write_text("x")
            home = self.root / "home"
            home.mkdir()

            plan = {"targets": [str(ext)], "moves": [{"src": str(f), "dest_dir": "Documents", "confidence": "high"}]}
            result = apply_plan(plan, base_dir=home, log_dir=self.root / "logs")

            self.assertTrue(result["aborted"])
            self.assertEqual(result["moved"], 0)
            self.assertTrue(f.exists())  # untouched
            self.assertFalse((home / "Documents").exists())
        finally:
            applier_mod.filesystem_id = real_fs

    def test_allow_cross_filesystem_overrides_the_abort(self):
        real_fs = applier_mod.filesystem_id
        def fake_fs(path):
            return 999 if "external" in str(path) else real_fs(path)
        applier_mod.filesystem_id = fake_fs
        try:
            ext = self.root / "external"
            ext.mkdir()
            f = ext / "file.txt"
            f.write_text("x")
            home = self.root / "home"
            home.mkdir()

            plan = {"targets": [str(ext)], "moves": [{"src": str(f), "dest_dir": "Documents", "confidence": "high"}]}
            result = apply_plan(plan, base_dir=home, log_dir=self.root / "logs", allow_cross_filesystem=True)

            self.assertFalse(result["aborted"])
            self.assertEqual(result["moved"], 1)
            self.assertTrue((home / "Documents" / "file.txt").exists())
        finally:
            applier_mod.filesystem_id = real_fs


class TestIntegrityGuard(unittest.TestCase):
    """v1.1.2: a directory containing a binary/library is never reached into,
    in ANY structure mode including reorganize — added after reorganize mode
    flattened curated folders in a real incident; the same behavior against
    a game/software install would break it, not just misfile something."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_reorganize_mode_still_protects_a_game_directory(self):
        downloads = self.root / "Downloads"
        game = downloads / "SomeGame"
        game.mkdir(parents=True)
        (game / "game.exe").write_text("x")
        (game / "engine.dll").write_text("x")
        (game / "readme.txt").write_text("x")
        (game / "assets").mkdir()
        (game / "assets" / "texture.png").write_text("x")

        plan = build_plan(
            targets=[str(downloads)], recursive=True, structure_mode="reorganize",
            log_dir=self.root / "logs",
        )

        self.assertEqual(len(plan["moves"]), 0)
        self.assertIn(str(game), plan["protected_dirs"])

    def test_ordinary_directory_without_binaries_is_not_protected(self):
        downloads = self.root / "Downloads"
        docs = downloads / "MyDocs"
        docs.mkdir(parents=True)
        (docs / "report.pdf").write_text("x")

        plan = build_plan(
            targets=[str(downloads)], recursive=True, structure_mode="reorganize",
            log_dir=self.root / "logs",
        )

        self.assertEqual(len(plan["protected_dirs"]), 0)
        self.assertEqual(len(plan["moves"]), 1)


class TestVerifyRecovery(unittest.TestCase):
    """v1.1.2: added after an agent declared a recovery complete on the
    strength of one incomplete search. This checks real filesystem state."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _make_log(self, src, dest):
        log_dir = self.root / "logs"
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / "moves-test.log"
        log_path.write_text(f"{src}\t{dest}\n")
        return log_path

    def test_incomplete_recovery_is_flagged(self):
        src, dest = self.root / "src.txt", self.root / "dest.txt"
        dest.write_text("x")  # file still at moved location, not reverted
        log_path = self._make_log(src, dest)

        result = verify_recovery(log_path)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["not_reverted"]), 1)

    def test_complete_recovery_is_confirmed(self):
        src, dest = self.root / "src.txt", self.root / "dest.txt"
        src.write_text("x")  # file back at original location
        log_path = self._make_log(src, dest)

        result = verify_recovery(log_path)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["reverted"]), 1)

    def test_file_gone_from_both_locations_is_unaccounted_for_not_silently_ok(self):
        src, dest = self.root / "src.txt", self.root / "dest.txt"
        # neither exists — simulates something else happening to the file
        log_path = self._make_log(src, dest)

        result = verify_recovery(log_path)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["unaccounted_for"]), 1)

    def test_verify_after_real_undo_confirms_completion(self):
        src_dir = self.root / "Downloads"
        src_dir.mkdir()
        f = src_dir / "a.pdf"
        f.write_text("x")
        plan = {"targets": [str(src_dir)], "moves": [{"src": str(f), "dest_dir": "Documents", "confidence": "high"}]}

        result = apply_plan(plan, base_dir=self.root, log_dir=self.root / "logs")
        pre = verify_recovery(result["log_path"])
        self.assertFalse(pre["complete"])

        execute_undo(result["log_path"], dry_run=False)
        post = verify_recovery(result["log_path"])
        self.assertTrue(post["complete"])


if __name__ == "__main__":
    unittest.main()
