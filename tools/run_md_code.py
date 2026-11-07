"""python-cookbook Markdown 代码块体检：把"代码逐段实跑"的口径落成可自动执行的检验。

为什么需要它：教案的写作约定是"概念演示用 REPL 会话（>>> 提示符）、完整脚本用
注释标注预期输出"。代码与输出分居两处，库版本一升级（如 NumPy 2.x 把标量 repr
包成 `np.float64(6.0)`）、或作者手一抖，输出就会与代码悄然脱节——而读者照着敲
一遍却"得到不一样的结果"是最伤教案可信度的事。本工具按文档顺序执行每个
```python 块：REPL 块逐行比对期望输出；脚本块执行并捕获运行错误。

用法：
    python tools/run_md_code.py machine-learning/ml-00-math-primer.md   # 验证一章
    python tools/run_md_code.py machine-learning                        # 验证一卷
    python tools/run_md_code.py                                        # 扫全仓库（慢）
    python tools/run_md_code.py data-science/ds-00-math-primer.md --show # 脚本块实际输出也打出来

块内标记（写在代码块第一行，井号注释，正文代码之前）：
    # no-run              跳过本块（平台特定、交互式、或不应在 CI 执行的片段）
    # expect-error        本块必须抛错（"找 bug"练习题）；可用冒号限定异常类型，
                          如 `# expect-error: IndentationError`

自动跳过（无需标记）：含 `input(`/`getpass(`/`breakpoint(`/`pdb.set_trace(`/`
code.interact(` 等交互入口的块（会挂住读 stdin）；以及以 `$ ` 或 `In [n]:`
开头的非 Python 会话块。

约定与口径：
- 每个文件共享**一个**命名空间（后文的块可用前文定义的变量），逐块按文档顺序执行。
- 执行期间把工作目录切到独立临时目录：块里写相对路径也不会污染仓库；需要读仓库
  里的文件时，用 `Path(__file__).parent / ...` 取代相对路径（命名空间里 `__file__`
  已设为该 Markdown 文件的路径）。
- REPL 块中任何不以 `>>>` / `...` 开头的非空行都视为期望输出；行尾允许带
  ` # 注释`（比对前剥离）。若条目产生了输出但块内**没有**期望输出行（旧章节
  常把输出塞进提示符行尾注释里），单独报告为"块内产生了 N 行输出但没有期望
  输出行"——这与"输出值错了"是两类问题。
- 脚本块只执行与报错——预期输出以注释形式存在、格式不统一，`--show` 打印实际输出
  供人工对照。
- "语句; 表达式" 的单行写法（如 `>>> x = x - 0.1 * (2 * x); x`）会被拆开执行，
  尾部表达式的结果计入输出。

退出码：输出不符或运行错误（含"本应抛错却没抛"）为 1，全部通过为 0。
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 与 build_pdf.py 的卷发现规则保持一致：工具、产物、依赖、CI 目录不是内容卷。
SKIP_DIRS = {"tools", "target", ".venv", ".git", ".github", "node_modules", "__pycache__", ".uv-cache"}

PROMPT_RE = re.compile(r"^>>> ?")
CONT_RE = re.compile(r"^\.\.\. ?")
TRAIL_COMMENT_RE = re.compile(r"\s+#.*$")
NO_RUN_RE = re.compile(r"#\s*no-run\b")
EXPECT_ERROR_RE = re.compile(r"#\s*expect-error(?::\s*([A-Za-z_][\w.]*))?\s*$")
INTERACTIVE_RE = re.compile(
    r"\b(?:input|getpass|breakpoint)\s*\(|\bpdb\.set_trace\s*\(|\bcode\.interact\s*\("
)
SHELLISH_RE = re.compile(r"^\$ |^In \[\d+\]:")


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


def iter_code_blocks(lines: list[str]):
    """扫描行，产出 (块起始行号, 代码行列表)；起始行号指向 ```python 的下一行。"""
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("```python"):
            start = i + 2  # ```python 那行算第 i+1 行，代码从第 i+2 行开始
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # 跳过收尾 ```
            if code:
                yield start, code
        else:
            i += 1


def strip_trailing_comment(line: str) -> str:
    """剥离期望输出行尾的 ' # 注释'；井号在字符串里的行原样返回。"""
    m = TRAIL_COMMENT_RE.search(line)
    if m and line[: m.start()].strip():
        return line[: m.start()].rstrip()
    return line


def parse_markers(code_lines: list[str]):
    """读块首标记。返回 (no_run, expect_error 名异常名或 True 或 None)。"""
    if not code_lines:
        return False, None
    first = code_lines[0].strip()
    if NO_RUN_RE.search(first):
        return True, None
    m = EXPECT_ERROR_RE.search(first)
    if m:
        return False, m.group(1) or True
    return False, None


class Runner:
    """单文件级命名空间的 REPL 模拟器 + 脚本执行器。"""

    def __init__(self, md_path: Path):
        self.ns = {"__name__": "__main__", "__file__": str(md_path)}

    def run_entry(self, code: str):
        """执行一个 REPL 输入项，返回 (输出行列表, 错误或 None)。"""
        out: list[str] = []
        err: BaseException | None = None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handled = False
            try:
                r = eval(code, self.ns)
                if r is not None:
                    out = repr(r).split("\n")
                handled = True
            except SyntaxError:
                pass
            except (Exception, SystemExit) as e:
                err = e
            if not handled and err is None:
                # "语句; 表达式"：尾部能编译为表达式时分开执行
                parts = code.split(";")
                if len(parts) > 1:
                    head = ";".join(parts[:-1])
                    # 注意必须去掉前导空格：compile(' x', mode='eval') 也会因缩进报错
                    tail = strip_trailing_comment(parts[-1]).strip()
                    if tail:
                        try:
                            compile(tail, "<repl>", "eval")
                        except SyntaxError:
                            tail = ""
                        if tail:
                            try:
                                exec(head, self.ns)
                                r = eval(tail, self.ns)
                                if r is not None:
                                    out = repr(r).split("\n")
                                handled = True
                            except (Exception, SystemExit) as e:
                                err = e
            if not handled and err is None:
                try:
                    exec(compile(code, "<repl>", "exec"), self.ns)
                except (Exception, SystemExit) as e:
                    err = e
        return buf.getvalue().splitlines() + out, err

    def run_script(self, code: str):
        """执行脚本块，返回 (输出行列表, 错误或 None)。"""
        buf = io.StringIO()
        err: BaseException | None = None
        with contextlib.redirect_stdout(buf):
            try:
                exec(compile(code, "<script>", "exec"), self.ns)
            except (Exception, SystemExit) as e:
                err = e
        return buf.getvalue().splitlines(), err


def run_repl_block(runner: Runner, code_lines: list[str], start_lineno: int):
    """执行 REPL 块并比对输出。返回 (问题列表, 实际输出)。问题为 (行号, 说明)。"""
    problems: list[tuple[int, str]] = []
    expects: list[tuple[int, str, str]] = []  # (序号, 行号, 期望文本)
    group: list[str] = []
    group_start: int | None = None

    def flush():
        nonlocal group, group_start
        if group:
            out, err = runner.run_entry("\n".join(group))
            if err is not None:
                problems.append(
                    (group_start or start_lineno, f"运行错误 {type(err).__name__}: {err}")
                )
            actual.extend(out)
        group = []
        group_start = None

    actual: list[str] = []
    for offset, line in enumerate(code_lines):
        lineno = start_lineno + offset
        if PROMPT_RE.match(line):
            if group:
                flush()
            group_start = lineno
            group.append(PROMPT_RE.sub("", line, count=1))
        elif CONT_RE.match(line):
            group.append(CONT_RE.sub("", line, count=1))
        else:
            flush()
            if line.strip():
                expects.append((len(expects), lineno, strip_trailing_comment(line)))
    flush()

    expected = [text for _, _, text in expects]
    for idx, (a, e) in enumerate(zip(actual, expected)):
        if a != e:
            lineno = expects[idx][1] if idx < len(expects) else start_lineno
            problems.append(
                (
                    lineno,
                    f"输出不符（第 {idx + 1} 行）：期望 {e!r}，实际 {a!r}",
                )
            )
            break
    else:
        if len(actual) != len(expected):
            if not expected:
                problems.append(
                    (start_lineno, f"块内产生了 {len(actual)} 行输出但没有期望输出行（期望输出需独占一行，或标 # no-run）")
                )
            elif len(actual) < len(expected):
                lineno = expects[len(actual)][1]
                problems.append((lineno, f"输出缺行：期望 {len(expected)} 行，实际 {len(actual)} 行"))
            else:
                problems.append(
                    (start_lineno, f"输出多行：期望 {len(expected)} 行，实际 {len(actual)} 行")
                )
    return problems, actual


def check_file(path: Path, show: bool = False):
    """检查一个 Markdown 文件，返回 (问题列表, 统计字典)。"""
    problems: list[tuple[int, str]] = []
    lines = path.read_text(encoding="utf-8").split("\n")
    blocks = list(iter_code_blocks(lines))
    stats = {"blocks": len(blocks), "skipped": 0, "errors": 0, "mismatch": 0, "repl": 0, "script": 0}
    if not blocks:
        return problems, stats

    runner = Runner(path)
    prev_cwd = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="run_md_code-"))
    os.chdir(tmp)
    try:
        for start, code_lines in blocks:
            text = "\n".join(code_lines)
            no_run, expect_error = parse_markers(code_lines)
            is_repl = any(PROMPT_RE.match(l) for l in code_lines)
            stats["repl" if is_repl else "script"] += 1
            if no_run:
                stats["skipped"] += 1
                continue
            if INTERACTIVE_RE.search(text) or any(SHELLISH_RE.match(l) for l in code_lines):
                stats["skipped"] += 1
                problems.append((start, "自动跳过：交互式/非 Python 会话，需要时加 # no-run 消音"))
                continue
            if is_repl:
                block_problems, _ = run_repl_block(runner, code_lines, start)
            else:
                out, err = runner.run_script(text)
                block_problems = []
                if err is not None:
                    block_problems = [
                        (start, f"运行错误 {type(err).__name__}: {str(err)[:200]}")
                    ]
                if show and out:
                    print(f"--- {display_path(path)} 块（第 {start} 行起）实际输出 ---")
                    for line in out:
                        print("    " + line)
            # expect-error 口径：必须抛错，类型可选
            real_err = any("运行错误" in p[1] for p in block_problems)
            if expect_error is not None and not real_err:
                block_problems = [(start, f"标记了 # expect-error 但本块未抛错（{expect_error}）")]
                problems.extend(block_problems)
            elif expect_error is None and block_problems:
                problems.extend(block_problems)
                for _, msg in block_problems:
                    stats["errors" if "运行错误" in msg else "mismatch"] += 1
            else:
                # 本块确实抛了错且标记了 expect-error：核对异常类型
                if expect_error not in (None, True):
                    got = next(m for _, m in block_problems if "运行错误" in m)
                    got_type = got.split("运行错误 ")[1].split(":")[0].strip()
                    if got_type != expect_error and not got_type.endswith(expect_error.split(".")[-1]):
                        problems.append((start, f"抛了 {got_type}，但标记的是 {expect_error}"))
    finally:
        os.chdir(prev_cwd)
        if str(tmp).startswith(tempfile.gettempdir()):  # 只删自己刚建的临时目录
            shutil.rmtree(tmp, ignore_errors=True)
    return problems, stats


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:  # 目标在仓库之外（例如临时文件）
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Markdown 代码块体检：按文档顺序实跑 python 块并核对期望输出"
    )
    parser.add_argument(
        "targets", nargs="*", type=Path, help="要检查的文件或目录，缺省扫全仓库"
    )
    parser.add_argument(
        "--show", action="store_true", help="把脚本块的实际 print 输出也打出来"
    )
    args = parser.parse_args()

    files = list(iter_markdown(args.targets or [REPO_ROOT]))
    total = {"blocks": 0, "skipped": 0, "errors": 0, "mismatch": 0, "repl": 0, "script": 0}
    found = 0
    for path in files:
        print(f"checking {display_path(path)} ...", file=sys.stderr)
        problems, stats = check_file(path, show=args.show)
        for key in total:
            total[key] += stats[key]
        for lineno, message in problems:
            found += 1
            print(f"{display_path(path)}:{lineno}: {message}")

    print(
        f"\n扫描 {len(files)} 个 Markdown 文件（{total['blocks']} 个代码块："
        f"REPL {total['repl']} / 脚本 {total['script']}）；"
        f"输出不符 {total['mismatch']} 处，运行错误 {total['errors']} 处，"
        f"跳过 {total['skipped']} 块。"
    )
    if found:
        sys.exit(1)


if __name__ == "__main__":
    main()
