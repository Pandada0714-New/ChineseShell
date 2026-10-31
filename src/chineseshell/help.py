from __future__ import annotations

from . import __version__
from .eggs import EGGS, render_egg_menu
from .packages import ACTION_LABELS, ACTION_ORDER
from .registry import all_commands, resolve


CATEGORY_ORDER = ("文件", "系统", "网络", "软件包", "Shell", "其他")


def render_help(topic: str | None = None) -> str:
    if topic:
        if topic.casefold() in {"彩蛋", "彩蛋菜单", "egg", "eggs"}:
            return render_egg_menu()
        return _render_command_help(topic)

    lines = [
        f"ChineseShell {__version__} · 用中文执行常用命令",
        "",
        "用法示例：",
        "  复制 源文件 目标文件",
        "  删除 递归 目录名",
        '  查找 "*.py" .',
        "  附加软件管理器 下载 curl",
        "  进入 /tmp",
        "",
        "全部命令：",
    ]

    commands = all_commands()
    for category in CATEGORY_ORDER:
        grouped = [command for command in commands if command.category == category]
        if not grouped:
            continue
        lines.append("")
        lines.append(category)
        for command in grouped:
            label = command.name
            if command.aliases:
                label += f"（{'、'.join(command.aliases)}）"
            lines.append(f"  {label}  {command.summary}")

    lines.extend(
        [
            "",
            "彩蛋",
            f"  彩蛋  打开彩蛋菜单（{'、'.join(egg.name for egg in EGGS)}）",
            "",
            "说明：",
            "  - 括号内的别名同样可以使用。",
            "  - 标准参数可以直接使用，例如：复制 -r 源 目标。",
            "  - 文件名和中文选项冲突时，可以用 -- 结束选项解析。",
            "  - 软件包管理器会自动识别 apt/dnf/yum/pacman/zypper/apk，并按需调用 sudo。",
            "  - 进入、退出、历史等命令需要安装 shell 集成后才会作用于当前终端。",
            "",
            "安装 shell 集成：",
            "  ./chineseshell --install",
            "",
            "查看帮助：",
            "  帮助",
            "  帮助 复制",
            "  中文 --help-zh 复制",
        ]
    )
    return "\n".join(lines)


def _render_command_help(topic: str) -> str:
    command = resolve(topic)
    lines = [
        f"{command.name} · {command.summary}",
    ]
    if command.aliases:
        lines.append(f"别名：{'、'.join(command.aliases)}")
    lines.extend(
        [
            f"用法：{command.usage}",
        ]
    )
    if command.system:
        lines.append(f"等价命令：{command.system}")

    if command.options:
        lines.append("")
        lines.append("中文选项：")
        for name, flag in command.options:
            lines.append(f"  {name}  →  {flag}")

    if command.name == "附加软件管理器":
        labels = "、".join(
            ACTION_LABELS[action] for action in ACTION_ORDER
        )
        lines.extend(
            [
                "",
                f"可用子命令：{labels}",
                "",
                "示例：",
                "  附加软件管理器 下载 curl",
                "  附加软件管理器 更新",
                "  附加软件管理器 搜索 编辑器",
                "",
                "说明：自动识别当前发行版的包管理器；修改系统时按需使用 sudo。",
                "环境变量：CHINESESHELL_PKG_MANAGER 可指定包管理器，CHINESESHELL_NO_SUDO=1 可禁用自动 sudo。",
            ]
        )

    if command.needs_shell:
        lines.extend(
            [
                "",
                "提示：该命令需要作用于当前终端，请先运行 ./chineseshell --install。",
            ]
        )

    return "\n".join(lines)
