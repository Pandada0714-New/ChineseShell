from __future__ import annotations

import os
import shlex
import shutil
from collections.abc import Callable, Sequence

from .errors import TranslationError
from .packages import package_command
from .registry import Command, register


COPY_OPTIONS = (
    ("递归", "-r"),
    ("强制", "-f"),
    ("详细", "-v"),
    ("保留", "-p"),
    ("交互", "-i"),
)
MOVE_OPTIONS = (
    ("强制", "-f"),
    ("详细", "-v"),
    ("交互", "-i"),
    ("不覆盖", "-n"),
)
REMOVE_OPTIONS = (
    ("递归", "-r"),
    ("强制", "-f"),
    ("交互", "-i"),
    ("详细", "-v"),
)
LIST_OPTIONS = (
    ("详细", "-l"),
    ("全部", "-a"),
    ("隐藏", "-a"),
    ("人性", "-h"),
    ("递归", "-R"),
    ("时间", "-t"),
    ("大小", "-S"),
    ("一列", "-1"),
)
CAT_OPTIONS = (("编号", "-n"),)
MKDIR_OPTIONS = (("父目录", "-p"), ("详细", "-v"))
FILE_OPTIONS = (("递归", "-R"),)
SEARCH_OPTIONS = (
    ("忽略大小写", "-i"),
    ("仅文件名", "-l"),
    ("单词", "-w"),
    ("反向", "-v"),
    ("固定字符串", "-F"),
)
WC_OPTIONS = (
    ("行", "-l"),
    ("词", "-w"),
    ("字节", "-c"),
    ("字符", "-m"),
    ("最长行", "-L"),
)
SORT_OPTIONS = (
    ("反向", "-r"),
    ("数字", "-n"),
    ("去重", "-u"),
    ("月份", "-M"),
    ("版本", "-V"),
)
UNIQ_OPTIONS = (("计数", "-c"), ("重复", "-d"), ("唯一", "-u"))
KILL_OPTIONS = (("强制", "-9"), ("全部", "-a"))
DF_OPTIONS = (("全部", "-a"), ("类型", "-T"))
DOWNLOAD_OPTIONS = (("静默", "-s"), ("详细", "-v"))
REQUEST_OPTIONS = (
    ("静默", "-s"),
    ("详细", "-v"),
    ("仅头", "-I"),
    ("失败", "-f"),
)
ARCHIVE_OPTIONS = (("详细", "-v"),)


def _system(name: str):
    def mark(build):
        setattr(build, "system", name)
        return build

    return mark


def _split_options(
    args: Sequence[str],
    options: dict[str, str],
) -> tuple[list[str], list[str]]:
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
        if arg in options:
            flags.append(options[arg])
            continue
        if arg.startswith("-") and arg != "-":
            flags.append(arg)
            continue
        operands.append(arg)
    return flags, operands


def _external(
    base: Sequence[str],
    options: dict[str, str] | None = None,
    *,
    separator: str | None = "--",
    min_args: int = 0,
    max_args: int | None = None,
) -> Callable[[Sequence[str]], list[str]]:
    def build(args: Sequence[str]) -> list[str]:
        flags, operands = _split_options(args, options or {})
        if len(operands) < min_args:
            raise TranslationError(f"参数不足，至少需要 {min_args} 个参数。")
        if max_args is not None and len(operands) > max_args:
            raise TranslationError(f"参数过多，最多接受 {max_args} 个参数。")
        command = [*base, *flags]
        if separator is not None and operands:
            command.append(separator)
        command.extend(operands)
        return command

    build.system = " ".join(base)
    return build


@_system("cd（shell 内建）")
def _build_enter(args: Sequence[str]) -> list[str]:
    if len(args) > 1:
        raise TranslationError("进入目录只需要一个路径。")
    if not args:
        return ["cd"]
    return ["cd", "--", args[0]]


@_system("pwd")
def _build_current_dir(args: Sequence[str]) -> list[str]:
    return ["pwd", *args]


@_system("bash")
def _build_shell(args: Sequence[str]) -> list[str]:
    return ["bash", *args]


@_system("exit（shell 内建）")
def _build_exit(args: Sequence[str]) -> list[str]:
    return ["exit", *args]


@_system("history（shell 内建）")
def _build_history(args: Sequence[str]) -> list[str]:
    return ["history", *args]


@_system("clear")
def _build_clear(args: Sequence[str]) -> list[str]:
    return ["clear", *args]


@_system("echo")
def _build_echo(args: Sequence[str]) -> list[str]:
    return ["echo", *args]


@_system("ps")
def _build_process(args: Sequence[str]) -> list[str]:
    if args:
        return ["ps", *args]
    return ["ps", "aux"]


@_system("uname -a")
def _build_system_info(args: Sequence[str]) -> list[str]:
    return ["uname", "-a", *args]


@_system("free -h")
def _build_memory(args: Sequence[str]) -> list[str]:
    return ["free", "-h", *args]


@_system("env")
def _build_environment(args: Sequence[str]) -> list[str]:
    return ["env", *args]


@_system("ss -tuln")
def _build_port(args: Sequence[str]) -> list[str]:
    return ["ss", "-tuln", *args]


@_system("ip addr")
def _build_network(args: Sequence[str]) -> list[str]:
    return ["ip", "addr", *args]


@_system("find")
def _build_find(args: Sequence[str]) -> list[str]:
    if len(args) not in {1, 2}:
        raise TranslationError("查找需要一个文件名模式，可选一个路径。")
    pattern = args[0]
    path = args[1] if len(args) == 2 else "."
    return ["find", path, "-name", pattern]


@_system("grep -rn")
def _build_search(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, dict(SEARCH_OPTIONS))
    if not operands:
        raise TranslationError("搜索需要至少一个文本或模式。")
    pattern = operands[0]
    paths = operands[1:] or ["."]
    return ["grep", "-rn", *flags, "--", pattern, *paths]


def _archive_create_flag(output: str) -> str:
    lower = output.lower()
    if lower.endswith((".tar.gz", ".tgz")):
        return "-czf"
    if lower.endswith((".tar.bz2", ".tbz2", ".tbz")):
        return "-cjf"
    if lower.endswith((".tar.xz", ".txz")):
        return "-cJf"
    if lower.endswith(".tar"):
        return "-cf"
    return "-czf"


@_system("tar / zip")
def _build_compress(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, dict(ARCHIVE_OPTIONS))
    if len(operands) < 2:
        raise TranslationError("压缩需要输出文件名和至少一个源文件。")
    output = operands[0]
    sources = operands[1:]
    if output.lower().endswith(".zip"):
        return ["zip", "-r", output, *sources]
    return ["tar", _archive_create_flag(output), output, *sources, *flags]


@_system("tar / unzip")
def _build_extract(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, dict(ARCHIVE_OPTIONS))
    if len(operands) not in {1, 2}:
        raise TranslationError("解压需要一个压缩包，可选一个目标目录。")
    archive = operands[0]
    target = operands[1] if len(operands) == 2 else None
    if archive.lower().endswith(".zip"):
        command = ["unzip", archive]
        if target:
            command.extend(["-d", target])
        return command
    command = ["tar", "-xf", archive]
    if target:
        command.append(f"--one-top-level={target}")
    command.extend(flags)
    return command


@_system("curl")
def _build_download(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, dict(DOWNLOAD_OPTIONS))
    if len(operands) not in {1, 2}:
        raise TranslationError("下载需要一个网址，可选一个保存文件名。")
    url = operands[0]
    if len(operands) == 2:
        return ["curl", "-fL", *flags, "-o", operands[1], "--", url]
    return ["curl", "-fLO", *flags, "--", url]


@_system("curl")
def _build_request(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, dict(REQUEST_OPTIONS))
    if not operands:
        raise TranslationError("请求需要至少一个网址。")
    return ["curl", "-L", *flags, "--", *operands]


@_system("ping -c 4")
def _build_ping(args: Sequence[str]) -> list[str]:
    flags, operands = _split_options(args, {})
    if len(operands) != 1:
        raise TranslationError("测网需要一个主机名或 IP 地址。")
    return ["ping", "-c", "4", *flags, operands[0]]


@_system("默认编辑器")
def _build_edit(args: Sequence[str]) -> list[str]:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        command = shlex.split(editor)
    else:
        command = []
        for candidate in ("nano", "vim", "vi"):
            if shutil.which(candidate):
                command = [candidate]
                break
        if not command:
            raise TranslationError("没有找到可用编辑器，请设置 EDITOR 环境变量。")
    return [*command, *args]


@_system("apt-get / dnf / yum / pacman / zypper / apk")
def _build_package(args: Sequence[str]) -> list[str]:
    if not args:
        raise TranslationError(
            "需要软件包子命令，例如：附加软件管理器 安装 curl"
        )
    return package_command(args[0], list(args[1:]))


def _register(
    name: str,
    summary: str,
    usage: str,
    build: Callable[[Sequence[str]], list[str]],
    *,
    aliases: tuple[str, ...] = (),
    category: str = "文件",
    options: tuple[tuple[str, str], ...] = (),
    needs_shell: bool = False,
    system: str = "",
) -> None:
    register(
        Command(
            name=name,
            summary=summary,
            usage=usage,
            build=build,
            aliases=aliases,
            category=category,
            options=options,
            needs_shell=needs_shell,
            system=system or getattr(build, "system", ""),
        )
    )


_register(
    "复制",
    "复制文件或目录",
    "复制 [递归] [强制] 源... 目标",
    _external(("cp",), dict(COPY_OPTIONS), min_args=2),
    aliases=("拷贝", "拷贝文件"),
    options=COPY_OPTIONS,
)
_register(
    "移动",
    "移动文件或目录",
    "移动 [强制] 源... 目标",
    _external(("mv",), dict(MOVE_OPTIONS), min_args=2),
    aliases=("移动文件",),
    options=MOVE_OPTIONS,
)
_register(
    "重命名",
    "重命名文件或目录",
    "重命名 [强制] 旧名 新名",
    _external(("mv",), dict(MOVE_OPTIONS), min_args=2, max_args=2),
    aliases=("改名",),
    options=MOVE_OPTIONS,
)
_register(
    "删除",
    "删除文件或目录",
    "删除 [递归] [强制] 文件...",
    _external(("rm",), dict(REMOVE_OPTIONS), min_args=1),
    aliases=("删", "删除文件"),
    options=REMOVE_OPTIONS,
)
_register(
    "列出",
    "列出目录内容",
    "列出 [详细] [全部] [路径...]",
    _external(("ls",), dict(LIST_OPTIONS)),
    aliases=("列表", "列目录"),
    options=LIST_OPTIONS,
)
_register(
    "查看",
    "查看文件内容",
    "查看 [编号] 文件...",
    _external(("cat",), dict(CAT_OPTIONS), min_args=1),
    aliases=("显示文件", "读取文件"),
    options=CAT_OPTIONS,
)
_register(
    "创建目录",
    "创建目录",
    "创建目录 [父目录] 目录...",
    _external(("mkdir",), dict(MKDIR_OPTIONS), min_args=1),
    aliases=("新建目录", "建目录"),
    options=MKDIR_OPTIONS,
)
_register(
    "创建文件",
    "创建空文件或更新时间戳",
    "创建文件 文件...",
    _external(("touch",), {}, min_args=1),
    aliases=("新建文件", "建文件", "触摸"),
)
_register(
    "编辑",
    "使用默认编辑器打开文件",
    "编辑 文件...",
    _build_edit,
    aliases=("修改文件",),
)
_register(
    "查找",
    "按名称查找文件",
    "查找 模式 [路径]",
    _build_find,
    aliases=("查找文件", "找文件"),
)
_register(
    "搜索",
    "在文件内容中搜索文本",
    "搜索 [忽略大小写] 文本 [路径...]",
    _build_search,
    aliases=("搜", "搜索内容", "查找内容"),
    options=SEARCH_OPTIONS,
)
_register(
    "压缩",
    "压缩文件（tar 或 zip）",
    "压缩 输出文件 源...",
    _build_compress,
    aliases=("打包", "压缩文件"),
    options=ARCHIVE_OPTIONS,
)
_register(
    "解压",
    "解压 tar 或 zip 文件",
    "解压 压缩包 [目标目录]",
    _build_extract,
    aliases=("解压缩", "提取"),
    options=ARCHIVE_OPTIONS,
)
_register(
    "权限",
    "修改文件权限",
    "权限 [递归] 模式 文件...",
    _external(("chmod",), dict(FILE_OPTIONS), min_args=2),
    aliases=("改权限", "修改权限"),
    options=FILE_OPTIONS,
)
_register(
    "归属",
    "修改文件所有者",
    "归属 [递归] 用户[:组] 文件...",
    _external(("chown",), dict(FILE_OPTIONS), min_args=2),
    aliases=("改归属", "改所有者"),
    options=FILE_OPTIONS,
)
_register(
    "文件类型",
    "识别文件类型",
    "文件类型 文件...",
    _external(("file",), {}, min_args=1),
    aliases=("类型",),
)
_register(
    "统计",
    "统计行数、词数或字节数",
    "统计 [行] [词] 文件...",
    _external(("wc",), dict(WC_OPTIONS)),
    aliases=("计数",),
    options=WC_OPTIONS,
)
_register(
    "排序",
    "对文本文件排序",
    "排序 [反向] [数字] 文件...",
    _external(("sort",), dict(SORT_OPTIONS)),
    aliases=("排序文件",),
    options=SORT_OPTIONS,
)
_register(
    "去重",
    "去除相邻重复行",
    "去重 [计数] 文件",
    _external(("uniq",), dict(UNIQ_OPTIONS), max_args=2),
    aliases=("去除重复",),
    options=UNIQ_OPTIONS,
)
_register(
    "进入",
    "切换到另一个目录",
    "进入 [目录]",
    _build_enter,
    aliases=("切换目录", "进入目录"),
    category="Shell",
    needs_shell=True,
)
_register(
    "当前目录",
    "显示当前所在目录",
    "当前目录",
    _build_current_dir,
    aliases=("显示路径", "我在哪"),
    category="Shell",
)
_register(
    "进程",
    "查看系统进程",
    "进程 [参数...]",
    _build_process,
    aliases=("查看进程", "进程列表"),
    category="系统",
)
_register(
    "结束进程",
    "结束指定进程",
    "结束进程 [强制] 进程号...",
    _external(("kill",), dict(KILL_OPTIONS), separator=None, min_args=1),
    aliases=("杀进程", "终止进程"),
    category="系统",
    options=KILL_OPTIONS,
)
_register(
    "系统信息",
    "显示内核和系统信息",
    "系统信息 [选项...]",
    _build_system_info,
    aliases=("系统", "版本信息"),
    category="系统",
)
_register(
    "磁盘空间",
    "查看磁盘使用情况",
    "磁盘空间 [路径...]",
    _external(("df", "-h"), dict(DF_OPTIONS)),
    aliases=("磁盘", "硬盘空间"),
    category="系统",
    options=DF_OPTIONS,
)
_register(
    "内存",
    "查看内存使用情况",
    "内存 [选项...]",
    _build_memory,
    aliases=("内存使用",),
    category="系统",
)
_register(
    "用户",
    "显示当前用户名",
    "用户",
    _external(("whoami",), {}, separator=None, max_args=0),
    aliases=("当前用户", "我是谁"),
    category="系统",
)
_register(
    "时间",
    "显示当前时间",
    "时间 [选项...]",
    lambda args: ["date", *args],
    aliases=("现在时间",),
    category="系统",
    system="date",
)
_register(
    "日期",
    "显示当前日期",
    "日期 [选项...]",
    lambda args: ["date", *args],
    aliases=("今天日期",),
    category="系统",
    system="date",
)
_register(
    "环境",
    "显示环境变量或临时设置后执行命令",
    "环境 [变量=值...] [命令...]",
    _build_environment,
    aliases=("环境变量",),
    category="系统",
)
_register(
    "端口",
    "查看正在监听的端口",
    "端口 [参数...]",
    _build_port,
    aliases=("监听端口", "端口占用"),
    category="网络",
)
_register(
    "网络",
    "查看网络接口和 IP 地址",
    "网络 [参数...]",
    _build_network,
    aliases=("网络信息", "IP地址"),
    category="网络",
)
_register(
    "清屏",
    "清空终端屏幕",
    "清屏",
    _build_clear,
    aliases=("清除屏幕", "清空屏幕"),
    category="Shell",
)
_register(
    "历史",
    "查看命令历史",
    "历史 [数量]",
    _build_history,
    aliases=("命令历史", "历史命令"),
    category="Shell",
    needs_shell=True,
)
_register(
    "退出",
    "退出当前终端",
    "退出 [状态码]",
    _build_exit,
    aliases=("退出终端", "离开"),
    category="Shell",
    needs_shell=True,
)
_register(
    "命令行",
    "启动 Bash 命令行",
    "命令行 [参数...]",
    _build_shell,
    aliases=("终端", "交互命令行"),
    category="Shell",
)
_register(
    "输出",
    "输出一段文本",
    "输出 内容...",
    _build_echo,
    aliases=("回显", "打印"),
    category="Shell",
)
_register(
    "下载",
    "用 curl 下载文件",
    "下载 网址 [保存为]",
    _build_download,
    aliases=("下载文件", "获取文件"),
    category="网络",
    options=DOWNLOAD_OPTIONS,
)
_register(
    "请求",
    "发送 HTTP 请求",
    "请求 [选项] 网址",
    _build_request,
    aliases=("网络请求", "抓取网页"),
    category="网络",
    options=REQUEST_OPTIONS,
)
_register(
    "测网",
    "用 ping 测试网络连通性",
    "测网 主机",
    _build_ping,
    aliases=("网络测试", "测试网络"),
    category="网络",
)
_register(
    "附加软件管理器",
    "安装、卸载、更新软件包（自动适配发行版）",
    "附加软件管理器 子命令 [软件包...]",
    _build_package,
    aliases=("包管理器", "软件管理器", "软件包管理器", "高级软件包工具"),
    category="软件包",
)
