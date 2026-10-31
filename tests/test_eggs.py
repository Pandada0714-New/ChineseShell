from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chineseshell.eggs import (
    egg_command,
    egg_missing,
    find_egg,
    render_egg_menu,
)
from chineseshell.errors import ChineseShellError


class EggTests(unittest.TestCase):
    def test_menu_lists_eggs(self) -> None:
        menu = render_egg_menu()
        for name in ("牛", "禅", "火车", "奶牛", "黑客", "彩虹"):
            self.assertIn(f"彩蛋 {name}", menu)
        self.assertIn("彩蛋菜单", menu)
        self.assertIn("彩蛋 牛", menu)

    def test_find_by_alias(self) -> None:
        self.assertEqual(find_egg("牛").name, "牛")
        self.assertEqual(find_egg("哞").name, "牛")
        self.assertEqual(find_egg("moo").name, "牛")
        self.assertEqual(find_egg("代码雨").name, "黑客")
        self.assertEqual(find_egg("Python之禅").name, "禅")

    def test_unknown_egg(self) -> None:
        with self.assertRaises(ChineseShellError):
            find_egg("没有这个彩蛋")

    def test_python_egg(self) -> None:
        egg = find_egg("禅")
        command = egg_command(egg)
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1:], ["-c", "import this"])

    def test_missing_tools_are_reported(self) -> None:
        with patch(
            "chineseshell.eggs._available",
            side_effect=lambda tool: tool not in {"apt-get", "apt", "sl"},
        ):
            self.assertEqual(egg_missing(find_egg("牛")), ["apt-get / apt"])
            self.assertEqual(egg_missing(find_egg("火车")), ["sl"])
            with self.assertRaises(ChineseShellError) as context:
                egg_command(find_egg("火车"))
            self.assertIn("附加软件管理器 安装 sl", str(context.exception))

    @unittest.skipUnless(
        any(shutil.which(tool) for tool in ("apt-get", "apt")),
        "需要 APT",
    )
    def test_apt_moo(self) -> None:
        command = egg_command(find_egg("牛"))
        self.assertIn(command[0], {"apt-get", "apt"})
        self.assertEqual(command[1], "moo")


class EggCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = os.environ.copy()
        self.launcher = Path(__file__).resolve().parents[1] / "chineseshell"

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.launcher), *args],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

    def test_menu(self) -> None:
        result = self.run_cli("彩蛋")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("彩蛋菜单", result.stdout)
        self.assertIn("彩蛋 牛", result.stdout)

    def test_python_egg(self) -> None:
        result = self.run_cli("--eggs", "禅")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("The Zen of Python", result.stdout)

    def test_unknown_egg(self) -> None:
        result = self.run_cli("彩蛋", "不存在")
        self.assertEqual(result.returncode, 2)
        self.assertIn("未知彩蛋", result.stderr)

    @unittest.skipUnless(
        any(shutil.which(tool) for tool in ("apt-get", "apt")),
        "需要 APT",
    )
    def test_apt_cow(self) -> None:
        result = self.run_cli("彩蛋", "牛")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Have you mooed today", result.stdout)
