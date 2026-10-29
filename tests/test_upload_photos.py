import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "upload-photos.py"
spec = importlib.util.spec_from_file_location("upload_photos", SCRIPT)
upload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upload)


class PhotoUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "site"
        self.root.mkdir()
        self.sources = self.base / "originals"
        self.sources.mkdir()

    def photo(self, name="Photo one.JPG", content=b"photo bytes"):
        path = self.sources / name
        path.write_bytes(content)
        return path

    def test_spaces_uppercase_and_original_bytes_survive(self):
        source = self.photo()
        copied = upload.copy_photos(self.root, [source])
        self.assertEqual(copied, ["photos/Photo one.JPG"])
        self.assertEqual((self.root / copied[0]).read_bytes(), source.read_bytes())

    def test_repeated_upload_is_idempotent(self):
        source = self.photo()
        upload.copy_photos(self.root, [source])
        self.assertEqual(upload.copy_photos(self.root, [source, source]), [])

    def test_case_insensitive_collision_does_not_overwrite(self):
        source = self.photo("Photo.JPG", b"first")
        upload.copy_photos(self.root, [source])
        other = self.photo("photo.jpg", b"second")
        with self.assertRaises(ValueError):
            upload.copy_photos(self.root, [other])
        self.assertEqual((self.root / "photos/Photo.JPG").read_bytes(), b"first")

    def test_invalid_batch_copies_nothing(self):
        valid = self.photo()
        invalid = self.photo("not-a-photo.txt")
        with self.assertRaises(ValueError):
            upload.copy_photos(self.root, [valid, invalid])
        self.assertEqual(list((self.root / "photos").iterdir()), [])

    def test_missing_file_copies_nothing(self):
        valid = self.photo()
        with self.assertRaises(FileNotFoundError):
            upload.copy_photos(self.root, [valid, self.sources / "missing.jpg"])
        self.assertEqual(list((self.root / "photos").iterdir()), [])

    def test_hidden_jekyll_names_are_rejected(self):
        with self.assertRaises(ValueError):
            upload.copy_photos(self.root, [self.photo("_hidden.jpg")])

    def test_copy_mode_does_not_invoke_git(self):
        with patch.object(upload, "ROOT", self.root), patch.object(upload, "git") as git:
            self.assertEqual(upload.main([str(self.photo())]), 0)
            git.assert_not_called()

    def run_git(self, root, *args):
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()

    def initialize_git(self):
        remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        self.run_git(self.root, "init", "-b", "main")
        self.run_git(self.root, "config", "user.name", "Gallery test")
        self.run_git(self.root, "config", "user.email", "gallery@example.invalid")
        self.run_git(self.root, "commit", "--allow-empty", "-m", "Initial")
        self.run_git(self.root, "remote", "add", "origin", str(remote))
        self.run_git(self.root, "push", "-u", "origin", "main")
        return remote

    def test_push_commits_only_new_photos_and_updates_upstream(self):
        remote = self.initialize_git()
        # Brackets are literal filenames, not Git pathspec wildcards.
        source = self.photo("Photo [one].JPG")
        with patch.object(upload, "ROOT", self.root):
            self.assertEqual(upload.main(["--push", str(source)]), 0)
        self.assertEqual(self.run_git(self.root, "status", "--porcelain"), "")
        self.assertEqual(self.run_git(remote, "show", "main:photos/Photo [one].JPG"), "photo bytes")
        self.assertEqual(self.run_git(self.root, "rev-parse", "HEAD"), self.run_git(remote, "rev-parse", "main"))

    def test_dirty_clone_refuses_before_copying(self):
        self.initialize_git()
        (self.root / "unrelated.txt").write_text("keep this uncommitted")
        with patch.object(upload, "ROOT", self.root):
            self.assertEqual(upload.main(["--push", str(self.photo())]), 1)
        self.assertFalse((self.root / "photos").exists())

    def test_push_failure_keeps_local_commit_for_retry(self):
        remote = self.initialize_git()
        old_head = self.run_git(remote, "rev-parse", "main")
        self.run_git(self.root, "remote", "set-url", "--push", "origin", str(self.base / "missing.git"))
        with patch.object(upload, "ROOT", self.root):
            self.assertEqual(upload.main(["--push", str(self.photo())]), 1)
        self.assertNotEqual(old_head, self.run_git(self.root, "rev-parse", "HEAD"))
        self.assertEqual(old_head, self.run_git(remote, "rev-parse", "main"))
        self.assertEqual(self.run_git(self.root, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
