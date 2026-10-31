from __future__ import annotations

import os
import shlex
import subprocess
import sys

from . import __version__, commands as _commands
from .eggs import egg_command, find_egg, render_egg_menu
from .errors import ChineseShellError, TranslationError
from .help import render_help
from .registry import translate
from .shell import install, render_shell_init, uninstall


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on", "是"}


def _print_help(topic: str | None = None) -> int:
    try:
        print(render_help(topic))
    except TranslationError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 0


def _parse_rc_option(args: list[str]) -> str | None:
    rc_path: str | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--rc":
            if index + 1 >= len(args):
                raise ChineseShellError("--rc 需要一个启动文件路径。")
            rc_path = args[index + 1]
            index += 2
            continue
        if arg.startswith("--rc="):
            rc_path = arg[5:]
            index += 1
            continue
        raise ChineseShellError(f"未知参数：{arg}")
    return rc_path


def _execute(command: list[str]) -> int:
    if _truthy(os.environ.get("CHINESESHELL_DEBUG")):
        print(f"[ChineseShell] {shlex.join(command)}", file=sys.stderr)
    try:
        return subprocess.call(command)
    except FileNotFoundError:
        print(
            f"找不到系统命令：{command[0]}\n"
            "请确认它已经安装，并且位于 PATH 中。",
            file=sys.stderr,
        )
        return 127
    except PermissionError:
        print(f"没有权限执行：{command[0]}", file=sys.stderr)
        return 126
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        return 1


def _run_egg(args: list[str]) -> int:
    if not args or args[0].casefold() in {"菜单", "列表", "帮助", "?", "help", "menu"}:
        print(render_egg_menu())
        return 0

    if len(args) > 1:
        print(f"错误：彩蛋“{args[0]}”不接受额外参数。", file=sys.stderr)
        return 2

    try:
        egg = find_egg(args[0])
    except ChineseShellError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    try:
        command = egg_command(egg)
    except ChineseShellError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 127

    return _execute(command)


def _run_install(args: list[str]) -> int:
    try:
        rc_path = _parse_rc_option(args)
        init_file, rc_file = install(rc_path)
    except (ChineseShellError, OSError) as exc:
        print(f"安装失败：{exc}", file=sys.stderr)
        return 1

    print("已安装 ChineseShell shell 集成。")
    print(f"初始化脚本：{init_file}")
    print(f"启动文件：{rc_file}")
    print(f"激活方式：source {shlex.quote(str(rc_file))}，或重新打开终端。")
    print("示例：复制 源 目标；删除 递归 目录；附加软件管理器 下载 curl")
    return 0


def _run_uninstall(args: list[str]) -> int:
    try:
        rc_path = _parse_rc_option(args)
        rc_file, removed = uninstall(rc_path)
    except (ChineseShellError, OSError) as exc:
        print(f"卸载失败：{exc}", file=sys.stderr)
        return 1

    print("已移除 ChineseShell shell 集成。")
    if removed:
        print(f"已清理启动文件：{rc_file}")
    else:
        print(f"启动文件中没有 ChineseShell 配置：{rc_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        return _print_help()

    first = args[0]
    if first in {"--help", "-h", "帮助"}:
        topic = args[1] if len(args) > 1 else None
        return _print_help(topic)
    if first == "--help-zh":
        topic = args[1] if len(args) > 1 else None
        return _print_help(topic)
    if first in {"--version", "-V"}:
        print(f"ChineseShell {__version__}")
        return 0

    if first == "--shell-init":
        if len(args) > 1:
            print("错误：--shell-init 不接受参数。", file=sys.stderr)
            return 2
        try:
            sys.stdout.write(render_shell_init())
        except ChineseShellError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        return 0

    if first == "--install":
        return _run_install(args[1:])
    if first == "--uninstall":
        return _run_uninstall(args[1:])
    if first in {"--eggs", "彩蛋"}:
        return _run_egg(args[1:])

    emit = False
    if first == "--emit":
        emit = True
        args = args[1:]
        if not args:
            print("错误：--emit 后面需要中文命令。", file=sys.stderr)
            return 2

    if args[0] == "帮助":
        topic = args[1] if len(args) > 1 else None
        return _print_help(topic)

    if args[0].startswith("--"):
        print(f"错误：未知选项：{args[0]}", file=sys.stderr)
        return 2

    try:
        translation = translate(args)
    except TranslationError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    command = list(translation.argv)
    if emit:
        if _truthy(os.environ.get("CHINESESHELL_DEBUG")):
            print(f"[ChineseShell] {shlex.join(command)}", file=sys.stderr)
        print(shlex.join(command))
        return 0

    if translation.command.needs_shell:
        print(
            f"“{translation.command.name}”需要作用于当前终端。\n"
            "请先安装 shell 集成：./chineseshell --install\n"
            "安装后重新打开终端，或 source 对应的启动文件。",
            file=sys.stderr,
        )
        return 2

    return _execute(command)


if __name__ == "__main__":
    raise SystemExit(main())
