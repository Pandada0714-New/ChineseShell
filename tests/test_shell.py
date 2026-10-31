from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chineseshell import commands as _commands
from chineseshell.registry import all_commands
from chineseshell.shell import MARK_BEGIN, MARK_END, install, render_shell_init, uninstall


class ShellInitTests(unittest.TestCase):
    def test_every_command_gets_a_function(self) -> None:
        script = render_shell_init(Path("/tmp/chineseshell"))
        for command in all_commands():
            self.assertIn(f"{command.name}() {{", script)
            for alias in command.aliases:
                self.assertIn(f"{alias}() {{", script)
        self.assertIn('帮助() {', script)
        self.assertIn('彩蛋() {', script)
        self.assertIn('中文() {', script)

    def test_generated_script_runs_in_bash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workdir = Path(directory)
            init_file = workdir / "init.sh"
            init_file.write_text(
                render_shell_init(ROOT / "chineseshell"),
                encoding="utf-8",
            )
            script = f"""
source {init_file}
输出 你好 > 原始.txt
复制 原始.txt 副本.txt
查看 副本.txt
创建目录 子目录
移动 副本.txt 子目录/
进入 子目录
当前目录
"""
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", script],
                cwd=workdir,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("你好", result.stdout)
            self.assertTrue(result.stdout.rstrip().endswith("/子目录"))
            self.assertTrue((workdir / "子目录").is_dir())
            self.assertTrue((workdir / "子目录" / "副本.txt").exists())

    def test_dispatcher_keeps_directory_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            init_file = Path(directory) / "init.sh"
            init_file.write_text(
                render_shell_init(ROOT / "chineseshell"),
                encoding="utf-8",
            )
            script = f"source {init_file}\n中文 进入 /tmp\n中壳 当前目录\n"
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-c", script],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "/tmp")


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.home = Path(self._temp.name)
        self._previous = {
            "HOME": os.environ.get("HOME"),
            "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME"),
        }
        os.environ["HOME"] = str(self.home)
        os.environ["XDG_CONFIG_HOME"] = str(self.home / ".config")

    def tearDown(self) -> None:
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._temp.cleanup()

    def test_install_is_idempotent_and_uninstall_restores_rc(self) -> None:
        rc_file = self.home / ".bashrc"
        rc_file.write_text("export KEEP=1\n", encoding="utf-8")

        init_file, written_rc = install(rc_file)
        self.assertEqual(written_rc, rc_file)
        self.assertTrue(init_file.exists())
        content = rc_file.read_text(encoding="utf-8")
        self.assertEqual(content.count(MARK_BEGIN), 1)
        self.assertIn("export KEEP=1", content)

        install(rc_file)
        content = rc_file.read_text(encoding="utf-8")
        self.assertEqual(content.count(MARK_BEGIN), 1)

        _, removed = uninstall(rc_file)
        self.assertTrue(removed)
        content = rc_file.read_text(encoding="utf-8")
        self.assertNotIn(MARK_BEGIN, content)
        self.assertNotIn(MARK_END, content)
        self.assertIn("export KEEP=1", content)
        self.assertFalse(init_file.exists())
