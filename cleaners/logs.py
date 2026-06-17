"""日志文件清理：删除家目录下所有 .log 文件

删的是日志文件（用户数据），函数内单独二次确认。
范围固定为 $HOME，命令静态，不需要 `*_existing()`。
"""

import os
import shlex

from rich.prompt import Confirm

from ._common import console, run

HOME = os.path.expanduser("~")


def _log_cmds() -> list[str]:
    # 递归删除家目录下所有 .log 常规文件；find 默认不跟随符号链接
    return [f"find {shlex.quote(HOME)} -type f -name '*.log' -delete"]


def clean_logs() -> None:
    # 删除的是日志文件（用户数据），单独二次确认
    if not Confirm.ask(
        f"将递归删除 {HOME} 下所有 .log 日志文件，确认继续？",
        default=False,
    ):
        console.print("[yellow]已跳过日志文件清理[/yellow]")
        return
    for cmd in _log_cmds():
        run(cmd)
