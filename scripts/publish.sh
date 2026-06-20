#!/usr/bin/env bash
#
# 发布 clean-sweep-tui 到 PyPI：升版本 → 构建 → 上传 → 打 tag → push。
#
# 用法：
#   scripts/publish.sh [patch|minor|major|X.Y.Z]   # 默认 patch
#   scripts/publish.sh minor          # 0.1.2 → 0.2.0
#   scripts/publish.sh 1.0.0          # 直接指定版本号
#   scripts/publish.sh patch -y       # 跳过确认
#
# token 从仓库根目录的 .env 读取（UV_PUBLISH_TOKEN，见 .env.example）；
# 也可以直接在环境里 export UV_PUBLISH_TOKEN 覆盖。

set -euo pipefail

# 切到仓库根目录（脚本在 scripts/ 下）。
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUMP="patch"
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    patch|minor|major) BUMP="$arg" ;;
    *.*.*) BUMP="$arg" ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

die() { echo "✗ $*" >&2; exit 1; }

# 1) 加载 .env 里的 token（不覆盖已 export 的环境变量）。
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
[[ -n "${UV_PUBLISH_TOKEN:-}" ]] || die "缺少 UV_PUBLISH_TOKEN：复制 .env.example 为 .env 并填入 token。"

# 2) 工作区必须干净，保证发版提交只含版本号改动。
[[ -z "$(git status --porcelain)" ]] || die "工作区有未提交改动，请先提交或 stash。"

# 3) 读当前版本，算出新版本。
CURRENT="$(grep -m1 '^version = ' pyproject.toml | sed -E 's/version = "(.*)"/\1/')"
[[ "$CURRENT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "pyproject.toml 里的版本号格式异常：$CURRENT"
IFS=. read -r MA MI PA <<< "$CURRENT"
case "$BUMP" in
  major) NEW="$((MA+1)).0.0" ;;
  minor) NEW="${MA}.$((MI+1)).0" ;;
  patch) NEW="${MA}.${MI}.$((PA+1))" ;;
  *)
    [[ "$BUMP" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "版本号必须是 X.Y.Z 或 patch/minor/major：$BUMP"
    NEW="$BUMP" ;;
esac
[[ "$NEW" != "$CURRENT" ]] || die "新版本与当前版本相同：$NEW"

# 4) 确认（发布不可撤销）。
echo "  仓库：    $ROOT"
echo "  版本：    $CURRENT  →  $NEW"
echo "  目标：    PyPI (https://pypi.org/project/clean-sweep-tui/)"
if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -r -p "确认发布？版本号一旦上传无法重用 [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "已取消。"
fi

# 5) 同步两处版本号 + 刷新 lock。
sed -i -E "s/^version = \".*\"/version = \"$NEW\"/" pyproject.toml
sed -i -E "s/^__version__ = \".*\"/__version__ = \"$NEW\"/" clean_sweep_tui/__init__.py
uv lock --quiet

# 6) 构建并上传（uv publish 读 UV_PUBLISH_TOKEN）。
rm -rf dist
uv build
uv publish

# 7) 上传成功后再落 git：提交、打 tag、push。
git add pyproject.toml clean_sweep_tui/__init__.py uv.lock
git commit -q -m "release: $NEW"
git tag "v$NEW"
git push origin HEAD --follow-tags

echo "✓ 已发布 clean-sweep-tui $NEW，并打 tag v$NEW 推送完成。"
