"""python-cookbook 表格体检：抓出会让 PDF 静默丢格的 Markdown 表格缺陷。

为什么需要它：表格是**先按行切单元格、再做行内解析**的。裸竖线一旦出现在单元格
内容里，就成了列分隔符，而两种渲染器都不会报错——

1. 单元格内的裸竖线（本工具主打）。多出来的单元格，GFM（GitHub）与 build 用的
   markdown-it 会**直接丢弃**，于是该行从那个竖线起整段消失；宽松渲染器（部分
   编辑器预览）则补成多余列，还会把跨格的 `**粗体**` 劈成两半。两种结果都是烂的。
   转义写法：代码段与正文用 `\\|`；数学环境（$...$）里 `\\|` 会变成 ‖，应改用
   `\\vert`/`\\lvert`（如 $2.785/\\lvert\\lambda\\rvert$）。
2. 表格被空行截断：表头与后续行之间插了空行，后半段成了没有分隔行的孤立行，
   渲染时退化为一段带竖线的纯文本。

用法：
    python tools/check_tables.py                  # 扫全仓库
    python tools/check_tables.py python-core      # 只扫某个目录
    python tools/check_tables.py README.md        # 只扫某个文件

退出码：发现问题为 1，干净为 0。注意本脚本只看结构，不校订内容。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 与 build_pdf.py 的卷发现规则保持一致：工具、产物、依赖、CI 目录不是内容卷。
SKIP_DIRS = {"tools", "target", ".venv", ".git", ".github", "node_modules", "__pycache__"}

FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
DELIM_RE = re.compile(r"^\|[\s:|-]+\|$")
PIPE_RE = re.compile(r"(?<!\\)\|")

HINT_PIPE = r"单元格内的竖线要转义：正文/代码段写 \|，数学环境用 \vert 或 \lvert"
HINT_SPLIT = "表格被空行截断：表头与后续行之间不要留空行"


def iter_markdown(targets: list[Path]):
    """产出待检查的 .md 文件；目录递归时跳过 SKIP_DIRS（避免走进 .venv 数万个文件）。"""
    for target in targets:
        target = target.resolve()
        if target.is_file():
            if target.suffix == ".md":
                yield target
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if name.endswith(".md"):
                    yield Path(root) / name


def check_block(block: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """检查一个连续的表格行块，返回 (行号, 问题, 修法)。"""
    issues: list[tuple[int, str, str]] = []
    header_lineno, header = block[0]
    width = len(PIPE_RE.findall(header))

    # 表块第二行必须是分隔行，否则整块其实不是表格（常见于被空行截断的后半段）。
    if len(block) < 2 or not DELIM_RE.match(block[1][1]):
        issues.append((header_lineno, "缺少分隔行（表格被空行截断？）", HINT_SPLIT))
        return issues

    for lineno, text in block[1:]:
        if DELIM_RE.match(text):
            continue
        n = len(PIPE_RE.findall(text))
        if n != width:
            issues.append(
                (lineno, f"列数不符：表头 {width - 1} 列，本行 {n - 1} 列", HINT_PIPE)
            )
    return issues


def check_file(path: Path) -> list[tuple[int, str, str]]:
    issues: list[tuple[int, str, str]] = []
    lines = path.read_text(encoding="utf-8").split("\n")
    fence: str | None = None
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        fence_match = FENCE_RE.match(stripped)
        if fence_match:  # 代码块内的竖线不算表格语法
            if fence is None:
                fence = fence_match.group(1)[0]
            elif stripped.startswith(fence):
                fence = None
            i += 1
            continue
        if fence is not None or not stripped.startswith("|"):
            i += 1
            continue

        block: list[tuple[int, str]] = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            block.append((i + 1, lines[i].strip()))
            i += 1
        issues.extend(check_block(block))
    return issues


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:  # 目标在仓库之外（例如临时文件）
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Markdown 表格体检：抓出裸竖线丢格与被空行截断的表格"
    )
    parser.add_argument(
        "targets", nargs="*", type=Path, help="要检查的文件或目录，缺省扫全仓库"
    )
    args = parser.parse_args()

    files = list(iter_markdown(args.targets or [REPO_ROOT]))
    found = 0
    for path in files:
        for lineno, message, hint in check_file(path):
            found += 1
            snippet = ""
            lines = path.read_text(encoding="utf-8").split("\n")
            if 0 < lineno <= len(lines):
                snippet = lines[lineno - 1].strip()[:96]
            print(f"{display_path(path)}:{lineno}: {message}")
            if snippet:
                print(f"    {snippet}")
            print(f"    → {hint}")

    print(f"\n扫描 {len(files)} 个 Markdown 文件，发现 {found} 处表格问题。")
    if found:
        sys.exit(1)


if __name__ == "__main__":
    main()
