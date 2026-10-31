from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chineseshell import commands as _commands
from chineseshell.errors import TranslationError
from chineseshell.registry import all_commands, resolve, translate


class TranslationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = {
            key: os.environ.get(key)
            for key in (
                "CHINESESHELL_NO_SUDO",
                "CHINESESHELL_PKG_MANAGER",
            )
        }
        os.environ["CHINESESHELL_NO_SUDO"] = "1"
        os.environ["CHINESESHELL_PKG_MANAGER"] = "apt-get"

    def tearDown(self) -> None:
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def argv(self, *args: str) -> tuple[str, ...]:
        return translate(args).argv


class FileCommandTests(TranslationTestCase):
    def test_copy_with_alias(self) -> None:
        self.assertEqual(self.argv("复制", "甲", "乙"), ("cp", "--", "甲", "乙"))
        self.assertEqual(self.argv("拷贝", "甲", "乙"), ("cp", "--", "甲", "乙"))

    def test_copy_options(self) -> None:
        self.assertEqual(
            self.argv("拷贝", "递归", "源", "目标"),
            ("cp", "-r", "--", "源", "目标"),
        )
        self.assertEqual(
            self.argv("复制", "-f", "源", "目标"),
            ("cp", "-f", "--", "源", "目标"),
        )

    def test_literal_file_name_after_double_dash(self) -> None:
        self.assertEqual(
            self.argv("复制", "--", "递归", "目标"),
            ("cp", "--", "递归", "目标"),
        )

    def test_remove_options(self) -> None:
        self.assertEqual(
            self.argv("删除", "递归", "强制", "目录"),
            ("rm", "-r", "-f", "--", "目录"),
        )

    def test_listing(self) -> None:
        self.assertEqual(
            self.argv("列出", "详细", "全部", "/tmp"),
            ("ls", "-l", "-a", "--", "/tmp"),
        )

    def test_view_file(self) -> None:
        self.assertEqual(self.argv("查看", "编号", "文件"), ("cat", "-n", "--", "文件"))

    def test_chmod(self) -> None:
        self.assertEqual(
            self.argv("权限", "递归", "+x", "脚本.sh"),
            ("chmod", "-R", "--", "+x", "脚本.sh"),
        )

    def test_find(self) -> None:
        self.assertEqual(
            self.argv("查找", "*.py", "/tmp"),
            ("find", "/tmp", "-name", "*.py"),
        )
        self.assertEqual(
            self.argv("查找", "*.py"),
            ("find", ".", "-name", "*.py"),
        )

    def test_search(self) -> None:
        self.assertEqual(
            self.argv("搜索", "忽略大小写", "你好"),
            ("grep", "-rn", "-i", "--", "你好", "."),
        )
        self.assertEqual(
            self.argv("搜索", "你好", "/tmp"),
            ("grep", "-rn", "--", "你好", "/tmp"),
        )

    def test_compress(self) -> None:
        self.assertEqual(
            self.argv("压缩", "备份.tar.gz", "资料"),
            ("tar", "-czf", "备份.tar.gz", "资料"),
        )
        self.assertEqual(
            self.argv("压缩", "备份.tar.xz", "资料"),
            ("tar", "-cJf", "备份.tar.xz", "资料"),
        )
        self.assertEqual(
            self.argv("压缩", "备份.zip", "资料"),
            ("zip", "-r", "备份.zip", "资料"),
        )

    def test_extract(self) -> None:
        self.assertEqual(
            self.argv("解压", "备份.tar.gz", "目标"),
            ("tar", "-xf", "备份.tar.gz", "--one-top-level=目标"),
        )
        self.assertEqual(
            self.argv("解压", "备份.zip", "目标"),
            ("unzip", "备份.zip", "-d", "目标"),
        )

    def test_download(self) -> None:
        self.assertEqual(
            self.argv("下载", "https://example.com/a.txt"),
            ("curl", "-fLO", "--", "https://example.com/a.txt"),
        )
        self.assertEqual(
            self.argv("下载", "https://example.com/a.txt", "本地.txt"),
            ("curl", "-fL", "-o", "本地.txt", "--", "https://example.com/a.txt"),
        )


class ShellCommandTests(TranslationTestCase):
    def test_enter_is_shell_builtin(self) -> None:
        translation = translate(["进入", "/tmp"])
        self.assertEqual(translation.argv, ("cd", "--", "/tmp"))
        self.assertTrue(translation.command.needs_shell)

    def test_enter_home(self) -> None:
        self.assertEqual(self.argv("进入"), ("cd",))

    def test_exit_and_history_are_shell_builtins(self) -> None:
        self.assertTrue(translate(["退出"]).command.needs_shell)
        self.assertTrue(translate(["历史"]).command.needs_shell)

    def test_bash_and_echo(self) -> None:
        self.assertEqual(self.argv("命令行", "-c", "echo hi"), ("bash", "-c", "echo hi"))
        self.assertEqual(self.argv("输出", "你好", "世界"), ("echo", "你好", "世界"))


class PackageCommandTests(TranslationTestCase):
    def test_apt_install(self) -> None:
        self.assertEqual(
            self.argv("附加软件管理器", "下载", "curl"),
            ("apt-get", "install", "curl"),
        )

    def test_apt_flags(self) -> None:
        self.assertEqual(
            self.argv("包管理器", "安装", "确认", "curl"),
            ("apt-get", "install", "-y", "curl"),
        )

    def test_apt_actions(self) -> None:
        self.assertEqual(
            self.argv("软件管理器", "更新"),
            ("apt-get", "update"),
        )
        self.assertEqual(
            self.argv("软件管理器", "已安装"),
            (
                "dpkg-query",
                "-W",
                "-f=${binary:Package}\\t${Version}\\n",
            ),
        )
        self.assertEqual(
            self.argv("软件管理器", "搜索", "curl"),
            ("apt-cache", "search", "curl"),
        )
        self.assertEqual(
            self.argv("软件管理器", "信息", "curl"),
            ("apt-cache", "show", "curl"),
        )

    def test_pacman(self) -> None:
        os.environ["CHINESESHELL_PKG_MANAGER"] = "pacman"
        self.assertEqual(
            self.argv("软件包管理器", "安装", "curl"),
            ("pacman", "-S", "curl"),
        )
        self.assertEqual(
            self.argv("软件包管理器", "已安装"),
            ("pacman", "-Q"),
        )

    def test_unsupported_action(self) -> None:
        os.environ["CHINESESHELL_PKG_MANAGER"] = "pacman"
        with self.assertRaises(TranslationError):
            self.argv("软件包管理器", "自动清理")

    def test_missing_package(self) -> None:
        with self.assertRaises(TranslationError):
            self.argv("附加软件管理器", "安装")

    def test_unknown_action(self) -> None:
        with self.assertRaises(TranslationError):
            self.argv("附加软件管理器", "跳舞", "curl")


class RegistryTests(TranslationTestCase):
    def test_aliases_resolve_to_canonical(self) -> None:
        self.assertEqual(resolve("拷贝").name, "复制")
        self.assertEqual(resolve("IP地址").name, "网络")
        self.assertIn("复制", [command.name for command in all_commands()])

    def test_unknown_command(self) -> None:
        with self.assertRaises(TranslationError) as context:
            self.argv("不存在命令")
        self.assertIn("未知命令", str(context.exception))

    def test_help_topic_alias(self) -> None:
        self.assertEqual(resolve("拷贝").usage, "复制 [递归] [强制] 源... 目标")
