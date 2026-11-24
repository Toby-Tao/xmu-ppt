"""Installed-skill portability: repo-root detection and dependency bootstrap."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/xmu-ppt/scripts"
sys.path.insert(0, str(SCRIPTS))

import config  # noqa: E402


class RepoRootTests(unittest.TestCase):
    def test_source_checkout_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "scripts").mkdir(parents=True)
            (repo / "scripts" / "pack_release.py").write_text("", encoding="utf-8")
            skill = repo / "skills" / "xmu-ppt"
            skill.mkdir(parents=True)
            self.assertEqual(config._detect_repo_root(skill).resolve(), repo.resolve())

    def test_installed_skill_falls_back_to_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "proj" / ".agents" / "skills" / "xmu-ppt"
            skill.mkdir(parents=True)
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                self.assertEqual(
                    config._detect_repo_root(skill).resolve(), Path(tmp).resolve()
                )
            finally:
                os.chdir(previous)


class BootstrapTests(unittest.TestCase):
    def test_check_reports_a_usable_interpreter(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "bootstrap_env.py"), "--check"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(Path(payload["python"]).is_file())


class DocsPortabilityTests(unittest.TestCase):
    def test_workflows_and_references_use_skill_dir_paths(self):
        files = list((ROOT / "skills/xmu-ppt/workflows").glob("*.md"))
        files += list((ROOT / "skills/xmu-ppt/references").glob("*.md"))
        self.assertTrue(files)
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("skills/xmu-ppt/scripts/", text, path)
            self.assertNotIn(".venv/Scripts/python.exe", text, path)
            self.assertNotIn(".venv/bin/python", text, path)

    def test_skill_md_explains_portable_paths(self):
        text = (ROOT / "skills/xmu-ppt/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("bootstrap_env.py", text)
        self.assertIn("不要运行 `skills/xmu-ppt/scripts/...`", text)
        self.assertEqual(text.count("skills/xmu-ppt/scripts/"), 1)


if __name__ == "__main__":
    unittest.main()
