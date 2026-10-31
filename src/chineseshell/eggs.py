from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
import unicodedata

from .errors import ChineseShellError


@dataclass(frozen=True)
class Egg:
    name: str
    aliases: tuple[str, ...]
    summary: str
    commands: tuple[tuple[str, ...], ...]
    requirements: tuple[str, ...] = ()
    install_hint: str = ""


EGGS: tuple[Egg, ...] = (
    Egg(
        "牛",
        ("哞", "moo", "奶牛叫"),
        "APT 的小奶牛（apt-get moo）",
        (("apt-get", "moo"), ("apt", "moo")),
        install_hint="附加软件管理器 安装 apt",
    ),
    Egg(
        "禅",
        ("python", "巨蟒", "Python之禅"),
        "Python 之禅（import this）",
        ((sys.executable, "-c", "import this"),),
    ),
    Egg(
        "火车",
        ("sl", "机车", "蒸汽火车"),
        "呼啸而过的蒸汽火车（sl）",
        (("sl",),),
        install_hint="附加软件管理器 安装 sl",
    ),
    Egg(
        "奶牛",
        ("cowsay", "牛说"),
        "会说话的 ASCII 奶牛（cowsay）",
        (("cowsay", "哞～ 今天也要好好写代码哦"),),
        install_hint="附加软件管理器 安装 cowsay",
    ),
    Egg(
        "黑客",
        ("cmatrix", "矩阵", "代码雨"),
        "黑客帝国代码雨（cmatrix）",
        (("cmatrix",),),
        install_hint="附加软件管理器 安装 cmatrix",
    ),
    Egg(
        "彩虹",
        ("lolcat", "彩色"),
        "彩虹色文字（lolcat）",
        (
            (
                "bash",
                "-c",
                "printf '%s\\n' '彩虹出现：愿你的代码没有 bug' | lolcat",
            ),
        ),
        requirements=("lolcat",),
        install_hint="附加软件管理器 安装 lolcat",
    ),
)


def _available(tool: str) -> bool:
    if os.sep in tool:
        return Path(tool).is_file()
    return shutil.which(tool) is not None


def find_egg(name: str) -> Egg:
    target = name.strip().casefold()
    for egg in EGGS:
        if target == egg.name.casefold():
            return egg
        if any(target == alias.casefold() for alias in egg.aliases):
            return egg

    names = [egg.name for egg in EGGS]
    suggestions = [
        candidate
        for candidate in names
        if target and (target in candidate.casefold() or candidate.casefold() in target)
    ][:3]
    hint = "运行“彩蛋”查看彩蛋菜单。"
    if suggestions:
        hint = f"你是不是想用：{'、'.join(suggestions)}？"
    raise ChineseShellError(f"未知彩蛋：{name}\n{hint}")


def egg_missing(egg: Egg) -> list[str]:
    missing: list[str] = []
    if not any(_available(command[0]) for command in egg.commands):
        binaries: list[str] = []
        for command in egg.commands:
            if command[0] not in binaries:
                binaries.append(command[0])
        missing.append(" / ".join(binaries))
    for requirement in egg.requirements:
        if not _available(requirement) and requirement not in missing:
            missing.append(requirement)
    return missing


def egg_available(egg: Egg) -> bool:
    return not egg_missing(egg)


def egg_command(egg: Egg) -> list[str]:
    missing = egg_missing(egg)
    if missing:
        detail = f"缺少：{'、'.join(missing)}。"
        if egg.install_hint:
            detail += f"\n安装方式：{egg.install_hint}"
        raise ChineseShellError(f"彩蛋“{egg.name}”暂不可用。\n{detail}")

    for command in egg.commands:
        if _available(command[0]):
            return list(command)
    raise ChineseShellError(f"彩蛋“{egg.name}”暂不可用。")


def _width(text: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        for char in text
    )


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def render_egg_menu() -> str:
    labels = [f"彩蛋 {egg.name}" for egg in EGGS]
    label_width = max(_width(label) for label in labels) + 2
    summary_width = max(_width(egg.summary) for egg in EGGS) + 2

    lines = [
        "ChineseShell 彩蛋菜单",
        "",
    ]
    for egg, label in zip(EGGS, labels):
        if egg_available(egg):
            status = "可用"
        elif egg.install_hint:
            status = f"未安装（{egg.install_hint}）"
        else:
            status = "未安装"
        lines.append(
            f"  {_pad(label, label_width)}"
            f"{_pad(egg.summary, summary_width)}{status}"
        )

    lines.extend(
        [
            "",
            "用法：彩蛋 <名称>，例如：彩蛋 牛",
            "别名同样可用，例如：彩蛋 哞、彩蛋 代码雨。",
            "输入“帮助 彩蛋”也可以再次打开本页。",
        ]
    )
    return "\n".join(lines)
