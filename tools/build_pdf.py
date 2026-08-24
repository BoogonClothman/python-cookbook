"""python-cookbook 单章 PDF 构建器（ubuntu-cream 主题移植版）。

将各卷（python-core/、data-science/、machine-learning/、deep-learning/、llm/ …）
下的 Markdown 教案渲染为 PDF，观感对齐 Typora 的 ubuntu-cream 主题，打印保留
奶油底色。产物按卷分目录写入 target/<卷名>/。

卷由仓库根目录下的子目录自动发现：凡含 *.md 的顶层子目录（排除 tools/、target/、
.venv/、.git 等非内容目录）即视为一卷。各卷内部章节从第 1 章重新编号，靠目录
前缀（chapter-/ds-/ml-/dl-/llm-）消歧，符合"每卷独立可查"的定位。

用法（仓库根目录执行）：
    uv run python tools/build_pdf.py all                  # 全部卷的全部章节与专题
    uv run python tools/build_pdf.py 1                    # 各卷的第 1 章
    uv run python tools/build_pdf.py topic-regex          # 按文件名片段指定
    uv run python tools/build_pdf.py 7 12 --force         # 多目标 + 忽略缓存
    uv run python tools/build_pdf.py -v python-core all   # 仅构建某一卷
    uv run python tools/build_pdf.py -v data-science 1 2  # 某卷的指定章节

增量策略：对 md + 主题 css + 模板整体取 sha256，未变更且产物存在则跳过。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "target"
TOOLS_DIR = Path(__file__).resolve().parent
THEME_DIR = TOOLS_DIR / "theme"
CACHE_PATH = OUT_DIR / ".build-cache.json"

# 自动发现卷：根目录下含 *.md 的顶层子目录，排除工具/产物/依赖/CI 目录。
VOLUME_EXCLUDE = {"tools", "target", ".venv", ".git", ".github"}

from markdown_it import MarkdownIt
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

# ---------------------------------------------------------------- callout 识别

# blockquote 首个 inline 以 **<标签>** 开头时，按下表注入语义 class。
# 键为子串匹配（key in label）；未命中的标签保持基础金色引用块，
# 与 Typora 现状一致，属预期降级。
CALLOUT_RULES: list[tuple[str, str]] = [
    # warning：错误示范与强警告
    ("陷阱", "callout-warning"),
    ("常见误解", "callout-warning"),
    ("重要声明", "callout-warning"),
    # insight：原理/机制/推论类深度内容
    ("机制洞察", "callout-insight"),
    ("关键认知", "callout-insight"),
    ("概念辨析", "callout-insight"),
    ("核心问题", "callout-insight"),
    ("核心结论", "callout-insight"),
    ("关键推论", "callout-insight"),
    ("理论意义", "callout-insight"),
    ("设计哲学", "callout-insight"),
    ("一条铁律", "callout-insight"),
    # tip：实操指引
    ("实战建议", "callout-tip"),
    ("记忆口诀", "callout-tip"),
    ("下一步建议", "callout-tip"),
    # impact / version / note
    ("工程影响", "callout-impact"),
    ("版本注意", "callout-version"),
    ("注意", "callout-note"),
]

CALLOUT_RE = re.compile(r"\*\*([^*\n]{1,12})\*\*")


def classify_callout(content: str) -> str | None:
    m = CALLOUT_RE.match(content)
    if not m:
        return None
    label = m.group(1)
    for key, cls in CALLOUT_RULES:
        if key in label:
            return cls
    return None


def decorate_callouts(tokens: list) -> None:
    """给以 **标签** 开头的 blockquote_open 打上语义 class，供 CSS 上色。"""
    for i, tok in enumerate(tokens):
        if tok.type != "blockquote_open":
            continue
        for j in range(i + 1, min(i + 6, len(tokens))):
            nxt = tokens[j]
            if nxt.type == "inline":
                cls = classify_callout(nxt.content)
                if cls:
                    tok.attrJoin("class", cls)
                break
            if nxt.type == "blockquote_open":
                break


# ---------------------------------------------------------------- 代码高亮

# REPL 风格探测：含 >>> / ... 提示符的 python 块改用 pycon 词法器，
# 否则 python 词法器会把 >>> 切成 error token。
PROMPT_RE = re.compile(r"^\s*(>>> |\.\.\. )", re.MULTILINE)

LANG_ALIASES = {
    "py": "python",
    "python3": "python",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "console": "pycon",
}

_formatter = HtmlFormatter(nowrap=True)


def highlight_code(source: str, lang: str, attrs: str = "") -> str:
    """markdown-it highlight 回调：返回插入 <pre><code> 内部的 HTML。"""
    lang = LANG_ALIASES.get(lang.strip().lower(), lang.strip().lower())
    if lang == "python" and PROMPT_RE.search(source):
        lang = "pycon"
    try:
        lexer = get_lexer_by_name(lang or "text")
    except ClassNotFound:
        lexer = get_lexer_by_name("text")
    return pygments_highlight(source, lexer, _formatter)


# ---------------------------------------------------------------- 渲染管线


def make_renderer() -> MarkdownIt:
    options = {"html": True, "highlight": highlight_code}
    for preset in ("gfm-like2", "gfm-like"):  # gfm-like2 为较新预设，逐级回退
        try:
            return MarkdownIt(preset, options)
        except KeyError:
            continue
    return MarkdownIt("commonmark", options).enable(["table", "strikethrough"])


RENDERER = make_renderer()


def extract_title(markdown_text: str) -> str:
    m = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def render_markdown(markdown_text: str) -> str:
    env: dict = {}
    tokens = RENDERER.parse(markdown_text, env)
    decorate_callouts(tokens)
    return RENDERER.renderer.render(tokens, RENDERER.options, env)


def build_html(title: str, body_html: str) -> str:
    template = (TOOLS_DIR / "template.html").read_text(encoding="utf-8")
    # 用占位符替换而非 str.format：正文里满是花括号的代码会炸 format
    css_base = os.path.relpath(THEME_DIR, OUT_DIR).replace(os.sep, "/")
    return (
        template.replace("__CSS_BASE__", css_base)
        .replace("__TITLE__", title)
        .replace("__CONTENT__", body_html)
    )


# ---------------------------------------------------------------- Playwright 打印

# 页面内断页修正：高于一页可用版心的代码块/引用块允许跨页，
# 其余保持防腰斩，对应 CSS 中 .allow-break 规则。
# 必须在 print 媒体仿真下量测：打印布局比屏幕窄（688px vs 860px），
# 长行折行更多、实际更高；用屏幕高度量测会漏标，漏标的长块被迫
# 跨页时 Chromium 会直接裁切内容（表现为半行文字被削掉）。
FIXUP_JS = """
() => {
  const LIMIT = 900;   // A4 内容区约 994px @96dpi，留安全余量
  document.querySelectorAll('#write pre, #write blockquote').forEach(el => {
    if (el.scrollHeight > LIMIT) el.classList.add('allow-break');
  });
}
"""

# 页眉/页脚模板运行在页面边距区、不继承文档 CSS，必须自带内联样式。
# 模板内铺背景不可靠（height:100% 在模板容器中不生效，实测漆不上去），
# 奶油底色改由 PyMuPDF 后处理整页铺满，模板只负责页码文字。
_FOOT_FONT = (
    "font-family:'Ubuntu Mono','Consolas','Microsoft YaHei',monospace;"
    "font-size:9px;color:#6b6052;"
)
FOOTER_TEMPLATE = (
    f'<div style="width:100%;{_FOOT_FONT}'
    'display:flex;align-items:center;justify-content:center;">'
    '第 <span class="pageNumber"></span> 页 · 共 <span class="totalPages"></span> 页</div>'
)
# 传空字符串会启用 Chromium 内置默认页眉（日期+标题），必须给一个
# 渲染为空的非空模板才能真正关闭页眉。
HEADER_TEMPLATE = "<span></span>"


def print_to_pdf(page, html_path: Path, out_path: Path) -> None:
    page.goto(html_path.as_uri())
    page.emulate_media(media="print")  # 量测与打印布局保持一致，见 FIXUP_JS 注释
    page.evaluate("document.fonts.ready")  # 等待 @font-face 加载完成再打印
    page.evaluate(FIXUP_JS)
    page.pdf(
        path=str(out_path),
        format="A4",
        print_background=True,
        display_header_footer=True,
        header_template=HEADER_TEMPLATE,
        footer_template=FOOTER_TEMPLATE,
        margin={"top": "15mm", "bottom": "16mm", "left": "13mm", "right": "13mm"},
        outline=True,
        tagged=True,
    )


# Chromium 只在内容区绘制背景色，页边距区始终留白；模板铺背景又不可靠。
# 用 PyMuPDF 把全页奶油矩形垫到内容层之下（overlay=False），实现满版奶油底。
CREAM_RGB = (254 / 255, 250 / 255, 243 / 255)  # #fefaf3


def paint_cream_underlay(pdf_path: Path) -> None:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    for page in doc:
        page.draw_rect(page.rect, color=None, fill=CREAM_RGB, overlay=False)
    tmp = pdf_path.with_suffix(".tmp.pdf")
    doc.save(str(tmp), garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf_path)


# ---------------------------------------------------------------- 编排与缓存


def fingerprint(paths: list[Path], markdown_bytes: bytes) -> str:
    sha = hashlib.sha256()
    for p in paths:
        sha.update(p.read_bytes())
    sha.update(markdown_bytes)
    return sha.hexdigest()


# ---------------------------------------------------------------- 卷发现与目标解析


def discover_volumes() -> dict[str, Path]:
    """自动发现根目录下的卷：含 *.md 的顶层子目录（排除工具/产物/依赖目录）。"""
    vols: dict[str, Path] = {}
    for d in sorted(REPO_ROOT.iterdir()):
        if not d.is_dir() or d.name in VOLUME_EXCLUDE:
            continue
        if any(d.glob("*.md")):
            vols[d.name] = d
    return vols


def chapter_number(stem: str) -> str | None:
    """从文件名 stem 提取章号（2 位补零）：chapter-07-oop → '07'，无编号返回 None。"""
    m = re.search(r"-(\d{1,2})(?=-|$)", stem)
    return m.group(1).zfill(2) if m else None


def resolve_targets(volumes: dict[str, Path], specs: list[str]) -> list[tuple[str, Path]]:
    """把命令行目标规格解析为 (卷名, 源文件路径) 列表。

    规格语义：'all' 展开为选中卷内的全部 md；纯数字 N 匹配各卷的第 N 章
    （靠文件名中的 -NN- 定位，自动适配 chapter-/ds-/ml-/dl-/llm- 等前缀，
    同一章号下的多个文件如 oop 与 design-patterns 会一并命中）；其余按文件名
    片段子串匹配。未命中任何文件则报错退出。
    """
    chosen: dict[tuple[str, str], tuple[str, Path]] = {}
    for vol_name, vol_dir in volumes.items():
        stems = {p.stem: p for p in sorted(vol_dir.glob("*.md"))}
        for spec in specs:
            if spec == "all":
                for s, p in stems.items():
                    chosen[(vol_name, s)] = (vol_name, p)
                continue
            if spec in stems:
                # 精确文件名：唯一快速通道
                candidates = [spec]
            elif spec.isdigit():
                # 数字 N：匹配该章号下的全部文件（如第 7 章含 oop 与 design-patterns）
                want = f"{int(spec):02d}"
                candidates = [s for s in stems if chapter_number(s) == want]
            else:
                lowered = spec.lower()
                candidates = [s for s in stems if lowered in s.lower()]
            if not candidates:
                listing = ", ".join(sorted(stems)) or f"({vol_name}/ 下没有 md)"
                sys.exit(
                    f"[build_pdf] 在卷 {vol_name}/ 未找到匹配目标 {spec!r}；"
                    f"可选：{listing}"
                )
            for c in candidates:
                chosen[(vol_name, c)] = (vol_name, stems[c])
    return sorted(chosen.values(), key=lambda t: (t[0], t[1].name))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Markdown 教案 → ubuntu-cream PDF（多卷）")
    parser.add_argument("targets", nargs="+", help="章节序号 / 文件名片段 / all")
    parser.add_argument(
        "-v", "--volume", action="append", metavar="NAME",
        help="限定构建的卷（目录名，可重复 -v 多次指定）；默认全部卷",
    )
    parser.add_argument("--force", action="store_true", help="忽略缓存强制重建")
    args = parser.parse_args()

    volumes_all = discover_volumes()
    if not volumes_all:
        sys.exit("[build_pdf] 未发现任何卷（根目录下无含 *.md 的子目录）")
    if args.volume:
        unknown = [v for v in args.volume if v not in volumes_all]
        if unknown:
            sys.exit(f"[build_pdf] 未知卷 {unknown}；可选：{sorted(volumes_all)}")
        volumes = {v: volumes_all[v] for v in args.volume}
    else:
        volumes = volumes_all

    targets = resolve_targets(volumes, args.targets)
    OUT_DIR.mkdir(exist_ok=True)

    css_files = [THEME_DIR / "ubuntu-cream-print.css", THEME_DIR / "pygments.css"]
    template_file = TOOLS_DIR / "template.html"

    cache: dict[str, str] = {}
    if CACHE_PATH.exists():
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    from playwright.sync_api import sync_playwright

    built = skipped = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        tmp_html = OUT_DIR / ".tmp-build.html"
        try:
            for vol_name, src in targets:
                md_bytes = src.read_bytes()
                digest = fingerprint([*css_files, template_file], md_bytes)
                cache_key = f"{vol_name}/{src.stem}"
                out_dir = OUT_DIR / vol_name
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{src.stem}.pdf"
                if not args.force and out_path.exists() and cache.get(cache_key) == digest:
                    print(f"  跳过（未变更）：{vol_name}/{src.name}")
                    skipped += 1
                    continue
                text = md_bytes.decode("utf-8")
                html = build_html(extract_title(text), render_markdown(text))
                tmp_html.write_text(html, encoding="utf-8")
                print_to_pdf(page, tmp_html, out_path)
                paint_cream_underlay(out_path)
                cache[cache_key] = digest
                CACHE_PATH.write_text(
                    json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                print(f"  已构建：{vol_name}/{src.name} → {out_path.relative_to(REPO_ROOT)}")
                built += 1
        finally:
            browser.close()
            tmp_html.unlink(missing_ok=True)

    print(f"\n完成：新建/更新 {built} 个，跳过 {skipped} 个。产物在 target/<卷名>/")


if __name__ == "__main__":
    main()
