from __future__ import annotations

import os
import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "chineseshell"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = os.environ.copy()
        self.env["CHINESESHELL_NO_SUDO"] = "1"
        self.env["CHINESESHELL_PKG_MANAGER"] = "apt-get"

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(LAUNCHER), *args],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

    def test_emit(self) -> None:
        result = self.run_cli("--emit", "复制", "甲", "乙")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), shlex.join(["cp", "--", "甲", "乙"]))

    def test_emit_package(self) -> None:
        result = self.run_cli("--emit", "附加软件管理器", "下载", "curl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "apt-get install curl")

    def test_enter_cannot_persist_without_shell_integration(self) -> None:
        result = self.run_cli("进入", "/tmp")
        self.assertEqual(result.returncode, 2)
        self.assertIn("shell 集成", result.stderr)

    def test_help_and_version(self) -> None:
        help_result = self.run_cli("--help-zh")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("ChineseShell", help_result.stdout)
        self.assertIn("附加软件管理器", help_result.stdout)
        self.assertIn("彩蛋", help_result.stdout)

        egg_help = self.run_cli("--help-zh", "彩蛋")
        self.assertEqual(egg_help.returncode, 0)
        self.assertIn("彩蛋菜单", egg_help.stdout)

        version_result = self.run_cli("--version")
        self.assertEqual(version_result.returncode, 0)
        self.assertIn("ChineseShell", version_result.stdout)

    def test_command_help(self) -> None:
        result = self.run_cli("--help-zh", "拷贝")
        self.assertEqual(result.returncode, 0)
        self.assertIn("复制", result.stdout)
        self.assertIn("cp", result.stdout)

    def test_shell_init(self) -> None:
        result = self.run_cli("--shell-init")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("复制() {", result.stdout)
        self.assertIn("帮助() {", result.stdout)

    def test_direct_execution(self) -> None:
        result = self.run_cli("输出", "你好")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "你好\n")

    def test_unknown_command(self) -> None:
        result = self.run_cli("不存在的命令")
        self.assertEqual(result.returncode, 2)
        self.assertIn("未知命令", result.stderr)

    def test_debug_command(self) -> None:
        self.env["CHINESESHELL_DEBUG"] = "1"
        result = self.run_cli("--emit", "输出", "你好")
        self.assertEqual(result.returncode, 0)
        self.assertIn("[ChineseShell] echo", result.stderr)
