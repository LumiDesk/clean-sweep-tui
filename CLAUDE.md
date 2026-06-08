# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`CleanSweep` 是一个一键清空各类开发缓存（以及部分用户目录、应用配置）的工具，仅面向 Linux。Python 3.14，uv 管理依赖。第三方库：CLI 用 `rich`，GUI 用 `pyside6`（Qt）。

提供两个平级入口（都在模块顶层直接执行，不要加 `if __name__ == "__main__"`）：
- `main.py`：命令行界面，终端里逐步二次确认。
- `gui.py`：图形界面（PySide6），多选要清理的项后点按钮执行；需要提权的项用 `pkexec` 弹系统密码框。

## Commands

- 运行 CLI：`uv run main.py`
- 运行 GUI：`uv run gui.py`
- 同步依赖：`uv sync`
- 新增依赖：`uv add <pkg>`

没有测试套件，没有 linter 配置。VSCode 会跑 Ruff 类型的诊断（PostToolUse 会回传 `ide_diagnostics`），别忽略警告。

## Architecture

```
main.py              # CLI 入口：banner + 顶层 Confirm + 按 Step 顺序调用每个 cleaner
gui.py               # GUI 入口：PySide6 多选界面 + 后台线程执行 + 日志回显
cleaners/
├── _common.py       # 共享 console / run / has / skip（CLI 用）
├── dev.py           # 开发工具缓存：docker, pnpm, npm, go, rust, sdkman
├── system.py        # 系统级：dnf, apt, systemd journal, ~/.cache, /var/cache
├── user.py          # 用户数据目录：Documents/Downloads/Music/Pictures/Videos + 回收站
├── apps.py          # 应用配置：Claude (.claude 文件夹 + .claude.json)
├── custom.py        # 自定义：读项目根目录 custom.json 的 paths 列表
├── registry.py      # 清理任务注册表：把各 Step 声明为 Task 数据，供 GUI 消费
└── executor.py      # GUI 执行层：Popen 流式输出 + pkexec 提权
```

模块按 **删除对象的性质** 分组，不是按工具分组：
- `dev.py` 里的清理只动缓存，最坏后果是下次构建变慢——共用顶层 Confirm 即可。`system.py` 里的 `clean_user_cache`（`~/.cache`）性质上也是缓存，同样不加二次确认。
- `user.py` / `apps.py` / `custom.py`，以及 `system.py` 里涉及 `sudo` / 卸载包 / 删日志的清理，删的是用户数据、配置或系统状态，**每个函数内部必须再加一层 `Confirm.ask(default=False)`**，并且只在用户确认后才执行 `run(...)`。这是这个项目最重要的安全约定，新增同类清理时要遵守。

### 命令规格与两套入口的复用

每个 cleaner 模块里，要执行的 shell 命令抽成模块级的 `_<thing>_cmds() -> list[str]`（**不带 `sudo`/`pkexec` 前缀**，是否提权交给执行层）。这一份命令字符串是单一来源：
- CLI 的 `clean_*()`：保留终端的检测/跳过提示 + 二次确认，确认后对每条命令 `run(...)`（需提权的自己拼 `sudo `）。
- GUI：经 `registry.py` 的 `Task` 读取 `detect()`（能否勾选）和 `plan()`（要跑的命令），用 `executor.run_task` 执行；需提权的由 `executor` 包成 `pkexec bash -c '...'`，polkit 弹系统密码框（依赖桌面 polkit agent）。勾选本身即“确认”，但执行前 GUI 仍弹一次汇总确认。
- `var_cache` / `user_dirs` / `claude` / `custom` 这类目标随系统状态变化的，命令按当前真实存在的路径动态生成，对应模块导出 `*_existing()` 辅助函数同时给 CLI、registry 用。

### 共用约定（来自 `_common.py`）

- `run(cmd)`：所有 shell 操作都走它——它会先 `console.print` 出命令本身（青色），再 `subprocess.run(..., check=False)`。**不要绕开它直接调 `subprocess` / `os.system`**，否则用户看不到执行的是什么。
- `has(name)` + `skip(tool)`：检测可执行文件是否存在；不存在就 `skip(...)` 然后 `return`，不要报错退出。整体流程必须能跨环境跑通（缺哪个工具就跳哪步）。
- 路径里有用户输入或可能含特殊字符时用 `shlex.quote`（参考 `user.py` / `apps.py`）。`dev.py` 里硬编码的工具命令可以不用。

### 增加一个新的 cleaner

1. 判断它属于哪类（开发缓存 / 系统级 / 用户数据 / 应用配置 / 自定义），写到对应文件里；性质不同就新开一个模块。
2. 把命令抽成模块级 `_<thing>_cmds() -> list[str]`（不带 `sudo`/`pkexec`）。目标随系统状态变化的，再导出一个 `*_existing()` 给检测/动态生成用。
3. 命名 `clean_<thing>()`，无参数无返回值；入口先用 `has(...)` 或 `os.path.exists(...)` 探测，缺失就提示并 return。
4. 若涉及用户数据 / 配置 / 系统状态（`sudo`、卸载包、删日志等），函数内必须 `Confirm.ask(..., default=False)`，拒绝时打印跳过提示并 return；提权命令自己拼 `sudo `。
5. 在 `main.py` 里 import 并加一条 `console.rule("Step NN: <name>")` + 调用，顺序追加在末尾。
6. 在 `cleaners/registry.py` 的 `TASKS` 里追加一条 `Task`，填好 `detect` / `plan`（即 `_<thing>_cmds`）/ `privileged` / `sensitive` / `detail`，GUI 会自动显示并执行。

## 文档同步

每次实现新功能或修改既有功能后，**必须查看 `README.md` 是否需要同步更新**（清理项列表、使用说明、架构描述等）。需要更新就直接改，不要等用户提醒。
