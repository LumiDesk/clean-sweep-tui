"""应用配置清理：当前包含 Claude (~/.claude, ~/.claude.json)"""

import os
import shlex

from rich.prompt import Confirm

from ._common import console, run

HOME = os.path.expanduser("~")
CLAUDE_TARGETS = [
    os.path.join(HOME, ".claude"),
    os.path.join(HOME, ".claude.json"),
]


def claude_existing() -> list[str]:
    return [p for p in CLAUDE_TARGETS if os.path.exists(p)]


def _claude_cmds() -> list[str]:
    return [f"rm -rf {shlex.quote(path)}" for path in claude_existing()]


def clean_claude() -> None:
    existing = claude_existing()
    if not existing:
        console.print("[yellow]未找到 Claude 相关文件，跳过[/yellow]")
        return
    # Claude 的配置 / 历史 / 项目记录都在 .claude 里，单独二次确认
    if not Confirm.ask(
        f"将删除：{', '.join(existing)}，确认继续？",
        default=False,
    ):
        console.print("[yellow]已跳过 Claude 清理[/yellow]")
        return
    for cmd in _claude_cmds():
        run(cmd)
