class ChineseShellError(Exception):
    """ChineseShell 的基础异常。"""


class TranslationError(ChineseShellError):
    """无法把中文命令翻译成系统命令。"""
