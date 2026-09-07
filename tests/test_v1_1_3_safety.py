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
        drive = self.root / "external" / "Backups"
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

    def test_self_nesting_is_skipped_not_created(self):
        """v1.1.3: confirmed against two real incident logs — scanning a
        folder literally named 'Documents' whose own files classify into
        a 'Documents' bucket must not create Documents/Documents."""
        drive = self.root / "external" / "Documents"
        drive.mkdir(parents=True)
        f = drive / "notes.pdf"
        f.write_text("x")

        plan = {
            "targets": [str(drive)],
            "moves": [{"src": str(f), "dest_dir": "Documents", "confidence": "high"}],
        }
        result = apply_plan(plan, base_dir=None, log_dir=self.root / "logs")

        self.assertEqual(result["moved"], 0)
        self.assertEqual(result["skipped_noop"], 1)
        self.assertTrue(f.exists())  # left exactly where it was
        self.assertFalse((drive / "Documents").exists())  # no nested duplicate created

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

    def test_top_level_scanned_target_is_never_self_protected(self):
        """Regression: a --recursive scan of a target that merely CONTAINS a
        game folder somewhere inside it must not flag the whole target as
        protected — only the actual game subdirectory."""
        downloads = self.root / "Downloads"
        game = downloads / "SomeGame"
        game.mkdir(parents=True)
        (game / "game.exe").write_text("x")
        (downloads / "report.pdf").write_text("x")

        plan = build_plan(
            targets=[str(downloads)], recursive=True, structure_mode="reorganize",
            log_dir=self.root / "logs",
        )
        self.assertNotIn(str(downloads), plan["protected_dirs"])
        self.assertIn(str(game), plan["protected_dirs"])
        self.assertEqual(len(plan["moves"]), 1)  # report.pdf, still classified normally

    def test_folder_name_protects_content_with_no_binaries_at_all(self):
        """v1.1.3: confirmed against real incident logs — a 'My Games' save
        folder and a 'GAMES' folder of .rar archives contain no .exe/.dll
        anywhere, so only a name-based signal catches them."""
        docroot = self.root / "Documents"
        docroot.mkdir()
        games = docroot / "GAMES"
        games.mkdir()
        (games / "Call Of Duty (Modern Warfare).rar").write_text("x")
        mygames = docroot / "My Games" / "Terraria"
        mygames.mkdir(parents=True)
        (mygames / "config.json").write_text("x")
        (mygames / "achievements.dat").write_text("x")

        plan = build_plan(
            targets=[str(docroot)], recursive=True, structure_mode="reorganize",
            log_dir=self.root / "logs",
        )
        self.assertIn(str(games), plan["protected_dirs"])
        self.assertIn(str(mygames.parent), plan["protected_dirs"])
        self.assertEqual(len(plan["moves"]), 0)

    def test_config_can_extend_protected_folder_names(self):
        docroot = self.root / "Documents"
        docroot.mkdir()
        franca = docroot / "FRANCA"
        franca.mkdir()
        (franca / "notes.pdf").write_text("x")

        plan = build_plan(
            targets=[str(docroot)], recursive=True, structure_mode="reorganize",
            config={"protected_folder_names": ["franca"]},
            log_dir=self.root / "logs",
        )
        self.assertIn(str(franca), plan["protected_dirs"])


class TestSessionLog(unittest.TestCase):
    """v1.1.3: the moves log records WHAT moved; this records WHY — what
    was asked, what was chosen, what was confirmed. Added because every
    incident review of this project had to be reconstructed by hand from
    chat transcripts rather than read off a structured record."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_log_and_read_roundtrip(self):
        from file_organizer.core.session_log import log_session, read_sessions
        log_session(event="run_started", log_dir=self.root, user_request="organize Downloads", mode="quick")
        log_session(event="confirmed", log_dir=self.root, confirmation="yes do it")

        entries = read_sessions(self.root)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["event"], "run_started")
        self.assertEqual(entries[0]["user_request"], "organize Downloads")
        self.assertEqual(entries[1]["confirmation"], "yes do it")

    def test_read_sessions_empty_when_no_log_exists(self):
        from file_organizer.core.session_log import read_sessions
        self.assertEqual(read_sessions(self.root), [])

    def test_none_fields_are_omitted_not_stored_as_null(self):
        from file_organizer.core.session_log import log_session, read_sessions
        log_session(event="mode_chosen", log_dir=self.root, mode="autonomous")
        entries = read_sessions(self.root)
        self.assertNotIn("user_request", entries[0])
        self.assertEqual(entries[0]["mode"], "autonomous")


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
