import sys

from rich.panel import Panel
from rich.prompt import Confirm

from cleaners._common import console
from cleaners.apps import clean_claude
from cleaners.dev import (
    clean_docker,
    clean_go,
    clean_npm,
    clean_pnpm,
    clean_rust,
    clean_sdkman,
)
from cleaners.user import clean_user_dirs

# 输出大标题
console.print(
    Panel(
        """   ____   _       _____      _      _   _   ____    _   _
  / ___| | |     | ____|    / \\    | \\ | | / ___|  | | | |
 | |     | |     |  _|     / _ \\   |  \\| | \\___ \\  | |_| |
 | |___  | |___  | |___   / ___ \\  | |\\  |  ___) | |  _  |
  \\____| |_____| |_____| /_/   \\_\\ |_| \\_| |____/  |_| |_|
""",
        title="Kaede Shimizu",
        subtitle="0.0.1",
    )
)

if not Confirm.ask("确认要删除所有的开发缓存吗？此操作无法撤销？", default=True):
    sys.exit(0)

console.rule("Step 01: Docker")
clean_docker()

console.rule("Step 02: pnpm")
clean_pnpm()

console.rule("Step 03: npm")
clean_npm()

console.rule("Step 04: Go")
clean_go()

console.rule("Step 05: Rust")
clean_rust()

console.rule("Step 06: SDKMAN")
clean_sdkman()

console.rule("Step 07: 用户目录")
clean_user_dirs()

console.rule("Step 08: Claude")
clean_claude()

console.rule("[green]全部完成[/green]")
