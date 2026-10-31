from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .errors import TranslationError


@dataclass(frozen=True)
class Action:
    args: tuple[str, ...]
    root: bool = False
    binary: str = ""


@dataclass(frozen=True)
class Manager:
    actions: dict[str, Action]
    flags: dict[str, str]


ACTION_ALIASES = {
    "安装": "install",
    "下载": "install",
    "添加": "install",
    "卸载": "remove",
    "删除": "remove",
    "移除": "remove",
    "更新": "refresh",
    "刷新": "refresh",
    "升级": "upgrade",
    "搜索": "search",
    "查找": "search",
    "信息": "info",
    "详情": "info",
    "清理": "clean",
    "清理缓存": "clean",
    "自动清理": "autoremove",
    "已安装": "list",
    "列表": "list",
}

ACTION_LABELS = {
    "install": "安装（下载）",
    "remove": "卸载",
    "refresh": "更新",
    "upgrade": "升级",
    "search": "搜索",
    "info": "信息",
    "clean": "清理",
    "autoremove": "自动清理",
    "list": "已安装",
}

ACTION_ORDER = (
    "install",
    "remove",
    "refresh",
    "upgrade",
    "search",
    "info",
    "clean",
    "autoremove",
    "list",
)

PACKAGE_FLAG_NAMES = {"确认", "静默", "详细"}

MANAGERS = {
    "apt-get": Manager(
        actions={
            "install": Action(("install",), True),
            "remove": Action(("remove",), True),
            "refresh": Action(("update",), True),
            "upgrade": Action(("upgrade",), True),
            "search": Action(("search",), binary="apt-cache"),
            "info": Action(("show",), binary="apt-cache"),
            "clean": Action(("clean",), True),
            "autoremove": Action(("autoremove",), True),
            "list": Action(
                ("-W", "-f=${binary:Package}\\t${Version}\\n"),
                binary="dpkg-query",
            ),
        },
        flags={"确认": "-y", "静默": "-q"},
    ),
    "dnf": Manager(
        actions={
            "install": Action(("install",), True),
            "remove": Action(("remove",), True),
            "refresh": Action(("makecache",), True),
            "upgrade": Action(("upgrade",), True),
            "search": Action(("search",)),
            "info": Action(("info",)),
            "clean": Action(("clean", "all"), True),
            "autoremove": Action(("autoremove",), True),
            "list": Action(("list", "installed")),
        },
        flags={"确认": "-y", "静默": "-q", "详细": "-v"},
    ),
    "yum": Manager(
        actions={
            "install": Action(("install",), True),
            "remove": Action(("remove",), True),
            "refresh": Action(("makecache",), True),
            "upgrade": Action(("update",), True),
            "search": Action(("search",)),
            "info": Action(("info",)),
            "clean": Action(("clean", "all"), True),
            "autoremove": Action(("autoremove",), True),
            "list": Action(("list", "installed")),
        },
        flags={"确认": "-y", "静默": "-q", "详细": "-v"},
    ),
    "pacman": Manager(
        actions={
            "install": Action(("-S",), True),
            "remove": Action(("-R",), True),
            "refresh": Action(("-Sy",), True),
            "upgrade": Action(("-Syu",), True),
            "search": Action(("-Ss",)),
            "info": Action(("-Si",)),
            "clean": Action(("-Sc",), True),
            "list": Action(("-Q",)),
        },
        flags={"确认": "--noconfirm", "静默": "--quiet", "详细": "--verbose"},
    ),
    "zypper": Manager(
        actions={
            "install": Action(("install",), True),
            "remove": Action(("remove",), True),
            "refresh": Action(("refresh",), True),
            "upgrade": Action(("update",), True),
            "search": Action(("search",)),
            "info": Action(("info",)),
            "clean": Action(("clean",), True),
            "list": Action(("search", "--installed-only")),
        },
        flags={"确认": "-y", "静默": "-q", "详细": "-v"},
    ),
    "apk": Manager(
        actions={
            "install": Action(("add",), True),
            "remove": Action(("del",), True),
            "refresh": Action(("update",), True),
            "upgrade": Action(("upgrade",), True),
            "search": Action(("search",)),
            "info": Action(("info",)),
            "clean": Action(("cache", "clean"), True),
            "list": Action(("info",)),
        },
        flags={"静默": "-q", "详细": "-v"},
    ),
}

_OS_FAMILIES = (
    ({"debian", "ubuntu", "linuxmint", "pop", "deepin", "kali", "raspbian"}, "apt-get"),
    ({"fedora", "rhel", "centos", "rocky", "almalinux", "ol"}, "dnf"),
    ({"arch", "manjaro", "endeavouros", "artix"}, "pacman"),
    ({"opensuse", "opensuse-leap", "opensuse-tumbleweed", "sles", "sled"}, "zypper"),
    ({"alpine"}, "apk"),
)


def _read_os_release() -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        content = Path("/etc/os-release").read_text(encoding="utf-8")
    except OSError:
        return result
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key] = value
    return result


def detect_manager() -> str:
    override = os.environ.get("CHINESESHELL_PKG_MANAGER", "").strip()
    if override:
        name = Path(override).name
        if name == "apt":
            name = "apt-get"
        if name not in MANAGERS:
            supported = "、".join(MANAGERS)
            raise TranslationError(
                f"未知的软件包管理器：{override}\n可用值：{supported}"
            )
        return name

    release = _read_os_release()
    identifiers = {release.get("ID", "")}
    identifiers.update(release.get("ID_LIKE", "").split())
    identifiers.discard("")

    for family, manager in _OS_FAMILIES:
        if identifiers & family and shutil.which(manager):
            return manager

    for candidate in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk"):
        if shutil.which(candidate):
            return candidate

    raise TranslationError(
        "没有找到可用的软件包管理器。\n"
        "支持 apt-get、dnf、yum、pacman、zypper 和 apk。"
    )


def _is_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)


def _sudo_prefix() -> list[str]:
    disabled = os.environ.get("CHINESESHELL_NO_SUDO", "").strip().lower()
    if disabled in {"1", "true", "yes", "on", "是"}:
        return []
    if _is_root():
        return []
    for tool in ("sudo", "doas"):
        if shutil.which(tool):
            return [tool]
    return []


def _supported(manager: Manager) -> str:
    labels = [
        ACTION_LABELS[action]
        for action in ACTION_ORDER
        if action in manager.actions
    ]
    return "、".join(labels)


def package_command(action_name: str, args: list[str]) -> list[str]:
    action_key = ACTION_ALIASES.get(action_name)
    if action_key is None:
        all_actions = "、".join(ACTION_LABELS[action] for action in ACTION_ORDER)
        raise TranslationError(
            f"未知的软件包子命令：{action_name}\n可用子命令：{all_actions}"
        )

    manager_name = detect_manager()
    manager = MANAGERS[manager_name]
    action = manager.actions.get(action_key)
    if action is None:
        raise TranslationError(
            f"当前软件包管理器“{manager_name}”不支持“{ACTION_LABELS[action_key]}”。\n"
            f"支持：{_supported(manager)}"
        )

    flags: list[str] = []
    operands: list[str] = []
    literal = False
    for arg in args:
        if literal:
            operands.append(arg)
            continue
        if arg == "--":
            literal = True
            continue
        if arg in manager.flags:
            flags.append(manager.flags[arg])
            continue
        if arg in PACKAGE_FLAG_NAMES:
            raise TranslationError(
                f"当前软件包管理器“{manager_name}”不支持中文选项“{arg}”。"
            )
        if arg.startswith("-") and arg != "-":
            flags.append(arg)
            continue
        operands.append(arg)

    if action_key in {"install", "remove", "search", "info"} and not operands:
        raise TranslationError(
            f"“{ACTION_LABELS[action_key]}”需要至少一个软件包名。"
        )

    command: list[str] = []
    if action.root:
        command.extend(_sudo_prefix())
    command.append(action.binary or manager_name)
    command.extend(action.args)
    command.extend(flags)
    command.extend(operands)
    return command
