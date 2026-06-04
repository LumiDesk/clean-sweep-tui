"""GUI 执行层：把任务的命令规格跑起来，流式回传输出。

与 CLI 的 `run()` 不同，这里不依赖 rich/终端，而是用 Popen 边跑边把每行输出
通过回调送回 GUI 线程。需要提权的命令用 `pkexec` 包一层——polkit 会弹出系统
密码框（依赖桌面环境的 polkit agent），不需要终端。
"""

import shlex
import subprocess
from collections.abc import Callable

from .registry import Task


def has_pkexec() -> bool:
    import shutil

    return shutil.which("pkexec") is not None


def _wrap(cmd: str, privileged: bool) -> str:
    if not privileged:
        return cmd
    # pkexec 单次只能起一个程序，这里交给 root 的 bash 去解析整条命令
    return f"pkexec bash -c {shlex.quote(cmd)}"


def run_task(task: Task, emit: Callable[[str], None]) -> None:
    """执行单个任务的所有命令；每产生一行输出（或一条提示）调用一次 emit。"""
    cmds = task.plan()
    if not cmds:
        emit("（无可执行项，跳过）")
        return
    for cmd in cmds:
        full = _wrap(cmd, task.privileged)
        emit(f"$ {full}")
        try:
            proc = subprocess.Popen(
                full,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:  # noqa: BLE001 - 启动失败也要回传给界面
            emit(f"执行失败: {e}")
            continue
        assert proc.stdout is not None
        for line in proc.stdout:
            emit(line.rstrip("\n"))
        proc.wait()
        if proc.returncode not in (0, None):
            emit(f"（退出码 {proc.returncode}）")
