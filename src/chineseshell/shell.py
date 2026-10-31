from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import sys
from pathlib import Path

from .errors import ChineseShellError
from .registry import all_commands


MARK_BEGIN = "# >>> ChineseShell >>>"
MARK_END = "# <<< ChineseShell <<<"


def launcher_path() -> Path:
    argv0 = Path(sys.argv[0]).resolve()
    if argv0.is_file() and argv0.name == "chineseshell":
        _ensure_executable(argv0)
        return argv0

    source = Path(__file__).resolve().parents[2] / "chineseshell"
    if source.is_file():
        _ensure_executable(source)
        return source.resolve()

    found = shutil.which("chineseshell")
    if found:
        return Path(found).resolve()

    raise ChineseShellError(
        "无法定位 chineseshell 可执行文件。\n"
        "请直接运行项目目录中的 ./chineseshell --install。"
    )


def _ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass


def render_shell_init(bin_path: Path | None = None) -> str:
    executable = bin_path or launcher_path()
    lines = [
        f"_CHINESESHELL_BIN={shlex.quote(str(executable))}",
        "_chineseshell_run() {",
        "  local _chineseshell_cmd",
        '  _chineseshell_cmd=$("$_CHINESESHELL_BIN" --emit "$@") || return $?',
        '  eval "$_chineseshell_cmd"',
        "}",
    ]

    for command in all_commands():
        for name in (command.name, *command.aliases):
            lines.append(f'{name}() {{ _chineseshell_run {name} "$@"; }}')

    lines.extend(
        [
            f"帮助() {{ \"$_CHINESESHELL_BIN\" --help-zh \"$@\"; }}",
            f"彩蛋() {{ \"$_CHINESESHELL_BIN\" --eggs \"$@\"; }}",
            "_chineseshell_dispatch() {",
            "  case \"$1\" in",
            "    ''|-h|--help|--help-zh|--version|--shell-init|--install|--uninstall|--emit|--eggs|帮助|彩蛋)",
            "      \"$_CHINESESHELL_BIN\" \"$@\"",
            "      ;;",
            "    *)",
            "      _chineseshell_run \"$@\"",
            "      ;;",
            "  esac",
            "}",
            "中文() { _chineseshell_dispatch \"$@\"; }",
            "中壳() { _chineseshell_dispatch \"$@\"; }",
            "",
        ]
    )
    return "\n".join(lines)


def config_file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "chineseshell" / "init.sh"


def default_rc_file() -> Path:
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return home / ".zshrc"
    if shell.endswith("bash"):
        return home / ".bashrc"
    if (home / ".zshrc").exists():
        return home / ".zshrc"
    return home / ".bashrc"


def _rc_file(rc_path: str | Path | None) -> Path:
    if rc_path is None:
        return default_rc_file()
    return Path(rc_path).expanduser()


def _block(init_file: Path) -> str:
    quoted = shlex.quote(str(init_file))
    return "\n".join(
        [
            MARK_BEGIN,
            f"[ -f {quoted} ] && . {quoted}",
            MARK_END,
        ]
    )


def _replace_block(content: str, block: str) -> str:
    if MARK_BEGIN not in content:
        if content and not content.endswith("\n"):
            content += "\n"
        if content:
            content += "\n"
        return content + block + "\n"

    if MARK_END not in content:
        raise ChineseShellError(
            "启动文件中的 ChineseShell 标记不完整，请先手动删除相关行。"
        )

    pattern = re.compile(
        rf"{re.escape(MARK_BEGIN)}.*?{re.escape(MARK_END)}",
        re.DOTALL,
    )
    return pattern.sub(lambda _match: block, content)


def install(rc_path: str | Path | None = None) -> tuple[Path, Path]:
    init_file = config_file()
    init_file.parent.mkdir(parents=True, exist_ok=True)
    init_file.write_text(render_shell_init(), encoding="utf-8")

    rc_file = _rc_file(rc_path)
    rc_file.parent.mkdir(parents=True, exist_ok=True)
    content = rc_file.read_text(encoding="utf-8") if rc_file.exists() else ""
    rc_file.write_text(_replace_block(content, _block(init_file)), encoding="utf-8")
    return init_file, rc_file


def uninstall(rc_path: str | Path | None = None) -> tuple[Path, bool]:
    rc_file = _rc_file(rc_path)
    removed = False
    if rc_file.exists():
        content = rc_file.read_text(encoding="utf-8")
        if MARK_BEGIN in content:
            if MARK_END not in content:
                raise ChineseShellError(
                    "启动文件中的 ChineseShell 标记不完整，请先手动删除相关行。"
                )
            pattern = re.compile(
                rf"\n*{re.escape(MARK_BEGIN)}.*?{re.escape(MARK_END)}\n?",
                re.DOTALL,
            )
            new_content = pattern.sub("\n", content).strip()
            if new_content:
                new_content += "\n"
            rc_file.write_text(new_content, encoding="utf-8")
            removed = True

    init_file = config_file()
    if init_file.exists():
        init_file.unlink()
        try:
            init_file.parent.rmdir()
        except OSError:
            pass
    return rc_file, removed
