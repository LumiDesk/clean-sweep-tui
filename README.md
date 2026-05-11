# cleansh

一键清空各类开发缓存，以及部分用户目录、应用配置的命令行小工具。

> ⚠️ **这是自用脚本，未必适合所有人。** 它会按作者本人的工作习惯做删除（缓存、用户家目录下的常见文件夹、Claude 配置等），里面的目录和清理范围都是写死的。请先读完源码、确认每一步要删什么，再决定是否使用。

## 它会做什么

按顺序执行：

| Step | 目标 | 性质 |
| --- | --- | --- |
| 01 | Docker：容器 / 镜像 / volume / 构建缓存 | 缓存 |
| 02 | pnpm store | 缓存 |
| 03 | npm cache | 缓存 |
| 04 | Go build / module / test / fuzz 缓存 | 缓存 |
| 05 | Rust：registry 与 git 缓存（保留 `~/.cargo/bin`） | 缓存 |
| 06 | SDKMAN：`sdk flush` | 缓存 |
| 07 | 清空 `~/Desktop`、`~/Documents`、`~/Downloads`、`~/Music`、`~/Pictures`、`~/Videos` 的内容（保留文件夹本身） | **用户数据** |
| 08 | 删除 `~/.claude` 文件夹和 `~/.claude.json` | **应用配置** |

- 缺失的工具会自动跳过（比如没装 Docker 就跳 Step 01）。
- Step 07、08 删的不是缓存，每步都有**单独的二次确认**，默认 No。

## 使用

需要 Python 3.14 和 [uv](https://docs.astral.sh/uv/)。

```bash
uv sync
uv run main.py
```

启动时会有一次总确认；遇到 Step 07 / 08 还会再问一遍——想跳过就在那两步回车（默认 No）即可。

## 不会做什么

- 不会动 `~/.cargo/bin`（保留已安装的 cargo 命令）。
- 不会删用户家目录下除上述清单之外的任何东西。
- 没有 dry-run 模式。要看每条命令长什么样，直接读 [cleaners/](cleaners/) 下的源码——一共一百多行，很短。

## License

见 [LICENSE](LICENSE)。
