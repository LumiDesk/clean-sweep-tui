"""用户目录清理：Desktop / Documents / Downloads / Music / Pictures / Videos"""

import os
import shlex

from rich.prompt import Confirm

from ._common import console, run


def clean_user_dirs() -> None:
    home = os.path.expanduser("~")
    targets = ["Desktop", "Documents", "Downloads", "Music", "Pictures", "Videos"]
    # 这一步删除的是用户数据而非缓存，单独二次确认
    if not Confirm.ask(
        f"将清空 {home} 下的 {', '.join(targets)} 内容（保留文件夹本身），确认继续？",
        default=False,
    ):
        console.print("[yellow]已跳过用户目录清理[/yellow]")
        return
    for name in targets:
        path = os.path.join(home, name)
        if not os.path.isdir(path):
            console.print(f"[yellow]未找到 {path}，跳过[/yellow]")
            continue
        # -mindepth 1 保证不会删掉文件夹本身
        run(f"find {shlex.quote(path)} -mindepth 1 -delete")
