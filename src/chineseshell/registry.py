from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .errors import TranslationError


@dataclass(frozen=True)
class Command:
    name: str
    summary: str
    usage: str
    build: Callable[[Sequence[str]], list[str]]
    aliases: tuple[str, ...] = ()
    category: str = "其他"
    options: tuple[tuple[str, str], ...] = ()
    needs_shell: bool = False
    system: str = ""


@dataclass(frozen=True)
class Translation:
    argv: tuple[str, ...]
    command: Command


_COMMANDS: dict[str, Command] = {}
_ALIASES: dict[str, str] = {}


def register(command: Command) -> Command:
    if command.name in _COMMANDS or command.name in _ALIASES:
        raise RuntimeError(f"命令名重复：{command.name}")
    _COMMANDS[command.name] = command
    for alias in command.aliases:
        if alias in _COMMANDS or alias in _ALIASES:
            raise RuntimeError(f"命令别名重复：{alias}")
        _ALIASES[alias] = command.name
    return command


def all_commands() -> list[Command]:
    return list(_COMMANDS.values())


def all_names() -> list[str]:
    return [*_COMMANDS, *_ALIASES]


def resolve(name: str) -> Command:
    canonical = _ALIASES.get(name, name)
    command = _COMMANDS.get(canonical)
    if command is not None:
        return command

    names = all_names()
    suggestions = [
        candidate
        for candidate in names
        if name in candidate or candidate in name
    ]
    for candidate in names:
        if candidate not in suggestions and _similar(name, candidate):
            suggestions.append(candidate)
    suggestions = suggestions[:3]

    hint = "运行“中文 --help-zh”查看全部命令。"
    if suggestions:
        hint = f"你是不是想用：{'、'.join(suggestions)}？"
    raise TranslationError(f"未知命令：{name}\n{hint}")


def _similar(left: str, right: str) -> bool:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, left, right).ratio() >= 0.6


def translate(argv: Sequence[str]) -> Translation:
    if not argv:
        raise TranslationError("缺少中文命令。")

    command = resolve(argv[0])
    try:
        built = command.build(list(argv[1:]))
    except TranslationError as exc:
        message = str(exc)
        if "用法：" not in message:
            message = f"{message}\n用法：{command.usage}"
        raise TranslationError(message) from exc
    except ValueError as exc:
        raise TranslationError(f"{exc}\n用法：{command.usage}") from exc

    if not built:
        raise TranslationError(f"“{command.name}”没有生成可执行命令。")

    return Translation(tuple(built), command)
