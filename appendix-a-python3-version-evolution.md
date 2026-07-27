# 附录A Python 3 版本演进宝典

> 各版本新增特性的深度解析、生产环境迁移指南与 CPython 实现揭秘。
>
> 本章（和第一章的版本演化表不同）不只列时间线，而是逐个版本深入核心新增特性，让你在日常编写代码时能明确分辨"这个语法是哪个版本引入的""那个特性有哪些坑""我的代码能用哪个版本的 API"。

---

## A.1 版本脉络总览

Python 3 自 2008 年发布至今，演进可以划分为四个阶段：

| 阶段 | 版本范围 | 核心主题 |
|------|---------|---------|
| **奠基时期** | 3.0 – 3.4 | 消化 2→3 断裂代价，补齐基础设施（并发、解析、路径处理） |
| **类型与异步** | 3.5 – 3.7 | 类型注解体系建立、原生协程、f-string 生态爆发 |
| **语法革命** | 3.8 – 3.10 | 海象运算符、模式匹配、位置参数、字典合并 |
| **性能与底层** | 3.11 – 3.14 | Faster CPython（25% 提速）、自由线程（去 GIL）、JIT 编译 |

---

## A.2 奠基时期（3.0 – 3.4）

### A.2.1 Python 3.0（2008-12-03）——"不兼容重写"

Python 3.0 是 Guido 在 Python 2 积累十年设计债之后的一次**有控制的断裂**。它不是渐进式升级，而是"明知会分裂社区也要做"的硬决策。

#### 不兼容变更速览

| 变更 | 2.x 写法 | 3.0 写法 | 影响面 |
|------|---------|---------|-------|
| `print` 语句→函数 | `print "hello"` | `print("hello")` | 每个 Python 文件 |
| 整数除法 | `3 / 2 → 1` | `3 / 2 → 1.5`，`3 // 2 → 1` | 数值计算全局 |
| `str` vs `unicode` | `str = bytes`, `unicode` 为 Unicode | `str = Unicode`, `bytes` 为二进制 | 所有文本处理 |
| `raw_input()` | `raw_input()` 返回 str | 更名为 `input()` | 交互脚本 |
| 异常语法 | `except Exception, e` | `except Exception as e` | 异常处理 |
| 比较语义 | `None < 0` 可通过 | `TypeError` 抛出 | 排序代码 |
| `xrange()` | 旧版 | 不再存在，`range` 替代 | 循环性能 |

#### 💡 要点速查：Python 3.0 的生产力迁移要点

> - **`print` 加括号**：这是最容易被忽略的变更。`print("hello", "world")` 在 3.x 是正确调用；在 2.x 则是打印一个元组。
> - **真除法 `3 / 2 = 1.5`**：混合了 float 和 int 的 C/C++ 程序员需要特别警惕——Python 3 不会再向你隐瞒精度损失。
> - **`range()` 惰性求值**：它在 3.x 返回可迭代对象而非完整列表。显式 `list(range(1000000))` 才消耗内存。对于大范围循环，3.x 天然原地运行。
> - **`str` = Unicode**：这消除了"中文编码"曾经占比 60% 以上的 Python 新人问题。现在你的字符串天然是 Unicode，只管 `len()` 使用即可（除非你遇到的是 UTF-8 代理对/组合字符，这时需要 unicodedata）。

#### 生存周期

Python 3.0 本身生命周期极短，**直接升到 3.1 或 3.2** 更好。3.0 的 bug 修复在 2009 年 6 月即终止。**生产环境永远不要用 3.0**——它只是过渡版本。

---

### A.2.2 Python 3.1（2009-06-27）——"OrderedDict 诞生"

3.1 体积小，但有两个影响深远的特性：

#### `collections.OrderedDict`（PEP 372）

```python
from collections import OrderedDict

od = OrderedDict()
od['z'] = 1
od['a'] = 2
od['b'] = 3
for k, v in od.items():
    print(k, v)
# z → a → b  （插入顺序保持）
```

> **深水区**：普通 `dict` 在 CPython 3.6 之前竟**不保证**迭代顺序！这意味着 `dict.keys()` 的结果在不同实现（CPython/PyPy/Jython）或同一实现不同运行时（hash randomization）都会不同。`OrderedDict` 是 3.1–3.6 之间唯一保序方案。**Python 3.7 起 `dict` 正式保序**，使 `OrderedDict` 降级为仅用于"重排序"（如 `move_to_end()`）场景。

#### `str.format_map()`

```python
class Default(dict):
    def __missing__(self, key):
        return f"{{{key}}}"

print("{name} is {age}".format_map(Default(name="Alice")))
# Alice is {age}   ← 不会 KeyError，而是在缺失时保留占位符
```

**实用场景**：模板渲染中的容错。比 `str.format(**kwargs)` 更优雅，也更安全（不污染局部变量空间）。

---

### A.2.3 Python 3.2（2011-02-20）——"精品发布"

3.2 被 Python 社区普遍认为是最成熟的 3.x 早期版本。

#### `functools.lru_cache`

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

# 第一次 fib(40) 需要数百毫秒，第二次微秒级别
```

> **CPython 实现揭秘**：`lru_cache` 在底层使用**双向链表（doubly linked list）+ 哈希表**的组合——哈希表提供 O(1) 查找，链表维护最近最少使用（LRU）淘汰顺序。对函数参数计算哈希时，它要求所有参数都是可哈希的。

#### `concurrent.futures`

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import urllib.request

URLS = ['https://python.org', 'https://docs.python.org']

def fetch(url: str) -> tuple[str, int]:
    with urllib.request.urlopen(url) as resp:
        return url, len(resp.read())

# 线程池并行获取
with ThreadPoolExecutor(max_workers=4) as pool:
    results = pool.map(fetch, URLS)
for url, size in results:
    print(f"{url}: {size} bytes")
```

> **为什么它重要**：此前的多线程/多进程代码需要手工管理 `threading.Thread` 和 `multiprocessing.Process` 的生命周期。`concurrent.futures` 抽象了**提交-等待-收集结果**模式，等价于 Java 的 `ExecutorService`。你不再需要显式 `.join()` 和结果队列。这是 Python 并发编程的第一次"高层抽象标准化"。

#### `argparse` 替代 `optparse`

```python
import argparse

parser = argparse.ArgumentParser(description='计算斐波那契数列')
parser.add_argument('n', type=int, help='第 N 项')
parser.add_argument('--verbose', '-v', action='store_true')
args = parser.parse_args()
```

> **迁移提示**：`optparse` 在 3.2 已被弃用。如果你的脚本还在用 `optparse`，迁移到 `argparse` 可以获得更好的错误信息、子命令支持（`add_subparsers`）、类型自动解析等功能。

---

### A.2.4 Python 3.3（2012-09-29）——"yield from"

#### `yield from`——生成器委派（PEP 380）

```python
def reader():
    """读取三页数据"""
    yield 'page1'
    yield from page_data(1)  # 委派给子生成器
    yield 'page2'
    yield from page_data(2)

def page_data(n):
    for i in range(3):
        yield f"  item-{n}-{i}"
```

> **深水区**：在 `yield from` 出现之前，从生成器内部调用另一个生成器需要显式循环 `for x in subgen: yield x`。这不仅是啰嗦的问题——更重要的是**双向通道**：`yield from` 建立了调用者与子生成器的**透明双向连接**。调用者可以通过 `.send()` 向子生成器发送值、通过 `.throw()` 注入异常。显式的 `for` 循环无法做到这一点。这也是 `asyncio` 能在 3.4–3.5 实现的基础。

#### `u"..."` 字符串前缀回归

```python
s = u"你好"  # 在 3.3+ 中合法（但在 3.x 是纯装饰，因为 str 已经是 Unicode）
s2 = "你好"  # 完全等效
```

> **为什么设计者又加回来了？** 为了**向前兼容**：大量 Python 2 代码迁移工具（如 `2to3`）在输出中保留了 `u` 前缀。让 Python 3 silently accept `u"…"` 降低了 2→3 迁移的总成本。

#### `venv` 成为标准库（PEP 405）

```bash
python -m venv myenv     # 替代了以前的第三方工具 virtualenv
```

```python
# 虚拟环境本质是一个轻量化的 Python 安装：
# myenv/
# ├── pyvenv.cfg          # 指向宿主 Python 解释器的路径
# ├── bin/                # 激活脚本和独立的 python 可执行文件
# └── lib/pythonX.Y/site-packages/  # 独立包目录
```

> **CPython 实现揭秘**：`venv` 的核心机制极其简单：它不复制 Python 解释器，而是在 `pyvenv.cfg` 中记录宿主 Python 路径。激活后，虚拟环境的 `bin/python` 读取 `pyvenv.cfg` 中的 `home` 键，然后修改 `sys.path` 使 `site-packages` 指向虚拟环境的独立目录。这意味着**激活的本质是 PATH 和环境变量的替换**，而非真正的 "Python 安装"。

#### 💡 要点速查：3.3 的隐性大版本

> `yield from` 为 asyncio 铺路，`venv` 成为标准库函数，并且 `u"..."` 的回归是 Python 2→3 迁移中最聪明的向后兼容决策。**如果你在 2026 年仍然看到用 `virtualenv`（而非 `venv`）的教程，那它已经过时。** 只需要 `python -m venv .venv`。

---

### A.2.5 Python 3.4（2014-03-16）——"asyncio 初临"

#### `asyncio` —— 临时模块（PEP 3156）

```python
import asyncio

@asyncio.coroutine
def fetch_data(url):
    # 模拟异步请求
    yield from asyncio.sleep(1)
    return f"Data from {url}"

loop = asyncio.get_event_loop()
result = loop.run_until_complete(fetch_data('https://example.com'))
print(result)
```

> **为什么说是"临时模块"**：3.4 的 `asyncio` 基于 `yield from` 实现协程。Python 3.5 引入 `async`/`await` 后，旧的 `@asyncio.coroutine` + `yield from` 语法被标记为弃用，但在 **Python 3.12 中才彻底移除**。如果你在维护旧代码，要识别这两种风格。

#### `pathlib`（PEP 428）

```python
from pathlib import Path

data_dir = Path('data') / 'subfolder'  # 用 / 连接路径！✓
config = data_dir / 'config.yaml'

# 彻底告别 os.path.join 字符串拼接
if config.exists():
    text = config.read_text(encoding='utf-8')
    config.write_text(text.replace('old', 'new'), encoding='utf-8')

# 递归遍历目录
for py_file in Path('src').rglob('*.py'):
    print(py_file.stat().st_size)
```

> **工程现实**：Python 标准库中 `os.path` 相关的路径操作（`os.path.join`、`os.path.exists`、`os.listdir`）共约 20 个函数，全部以字符串为输入输出。`pathlib` 将它们封装为**面向对象**的接口，路径对象自动处理跨平台分隔符（Windows `\` vs POSIX `/`）。3.6+ 版本中 `os` 模块的函数已可接受 `Path` 对象。

#### `enum` 枚举类（PEP 435）

```python
from enum import Enum, auto, IntEnum

class Color(Enum):
    RED = 1
    GREEN = auto()  # 自动分配 2
    BLUE = 3

print(Color.RED.name)   # 'RED'  ← Enum 成员的名
print(Color.RED.value)  # 1      ← Enum 成员的值
print(Color(1))         # Color.RED  ← 通过值反向查找
print(Color['RED'])     # Color.RED  ← 通过名反向查找
```

> **深水区**：Python 在 3.4 之前没有枚举类型。社区常见的替代方案包括：全局常量（`RED = 1`，缺点是可变且无命名空间）、`collections.namedtuple`、或者 Django/Flask 中自定义的类属性枚举。第三方库 `enum34` 曾是主流。3.4 原生 `enum` 最重要的特性是**成员唯一性**和**反向查找**，此外还提供了 `IntEnum`（与整数兼容的枚举，可用作列表索引）。

---

## A.3 类型与异步时代（3.5 – 3.7）

### A.3.1 Python 3.5（2015-09-13）——"类型与协程双线启动"

3.5 是 Python 3 系列的第二个转折点。两个 PEP 分别定义了未来十年 Python 的"类型安全"和"异步编程"路线。

#### `async`/`await`——原生协程（PEP 492）

```python
async def fetch_user(user_id: int) -> dict:
    """使用 async/await 的协程"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f'/api/user/{user_id}') as resp:
            return await resp.json()
```

> **CPython 实现揭秘**：`async def` 定义的函数返回的不是 `dict`，而是一个**协程对象**（`coroutine object`）。该对象在底层是一个**生成器的包装**，但其附加了 `__await__` 方法。当 CPython 调用 `await coro` 时，PVM 执行以下步骤：① 检查对象是否有 `__await__` 方法；② 调用 `__await__()` 返回迭代器；③ `await` 表达式挂起当前协程，将执行权让渡给事件循环（event loop）。这被称为"显式的协作式多任务"——当前协程**主动让出**控制权，而非被操作系统抢占。

#### 类型注解（Type Hints）正式化（PEP 484）

PEP 484 不是引入"类型系统"，而是引入**注解的语法规范**：

```python
from typing import List, Optional, Tuple, Callable

def process_users(
    users: List[str],
    callback: Callable[[str], bool],
    limit: Optional[int] = None
) -> Tuple[int, int]:
    """处理用户列表，返回 (成功数, 失败数)。"""
    ...
```

> **工程真相**：Python 运行时**完全忽略类型注解**。它们存储在函数的 `__annotations__` 字典中，但 PV M 从不检查它们是否匹配。静态类型检查由第三方工具（`mypy`、`pyright`、`pytype`）在**开发阶段**完成。这是 Python "可选类型"哲学的核心：类型是开发期的安全网，不是运行期的枷锁。

#### @ 矩阵乘法中缀运算符（PEP 465）

```python
import numpy as np

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

C = A @ B  # 等价于 np.matmul(A, B)，不是 A * B（逐元素乘法）
```

> **为什么引入一个新符号？** NumPy 社区长期面临 `*` 运算符的语义冲突：对 np.ndarray，`*` 是**逐元素乘法**（pointwise multiplication），而数学上的矩阵乘法需要显式调用 `np.matmul()` 或 `.dot()`。PEP 465 引入了 `@` 作为中缀矩阵乘法运算符，使 Python 的数值代码更接近数学记号。这被 PEP 572（海象运算符）的作者誉为"最小化新运算符引入门槛的典范"。

#### 💡 要点速查：3.5 的双重变革

> - **`async`/`await`** 改变了 Python 的 I/O 编程方式。如果你写网络应用，3.5 是生产力分水岭。
> - **类型注解**的引入使大型 Python 项目的可维护性提升了一个量级。但记住：类型注解在**运行时完全不可见**。你可以在 `.py` 文件的类中添加 `def add(self, x: int, y: int) -> int:`，然后从 jar 包中调用——不会报错。
> - 自 3.5 起，**最低推荐版本**的基准线从 3.4 移到 3.5。
> - **`@` 运算符只在含 `__matmul__` 方法的类型上有效**，不要尝试在普通 `list` 上使用——Python 列表不是数学矩阵。

---

### A.3.2 Python 3.6（2016-12-23）——"Python 的成年礼"

3.6 被普遍认为是 Python 3 的第一个"舒服版本"——它在不引入巨大语法变动的前提下，大量提升了日常开发体验。

#### f-string（PEP 498）

```python
name = "Alice"
age = 30
score = 92.56789

# 最简洁的字符串格式化
print(f"Hello, {name}! You are {age} years old.")
print(f"Score: {score:.2f}")   # Score: 92.57
print(f"Binary: {age:#010b}")  # Binary: 0b00011110

# 表达式内嵌
print(f"{2 ** 10}")            # 1024
print(f"{name.upper()}")       # ALICE
# 3.8+ 调试模式：print(f"{name=}") → name='Alice'
```

> **CPython 实现揭秘**：f-string 的编译过程分做两步。第一步（AST 解析阶段）：CPython 将 f-string 表达式解析为一个**表达式节点序列**（literal + expression），存储在字符串代码对象的 `co_constants` 中以备后期展开；第二步（字节码生成阶段）：CPython 将 literal 部分转换为 `LOAD_CONST` 指令，将表达式部分转换为对应的取值/格式化指令，最后通过 `FORMAT_VALUE` 指令合并。f-string 的核心设计是**编译时决定"哪些部分需要取值"**，然后只在运行时评估表达式部分。这比 `%` 格式化和 `str.format()` 快得多，因为后两者都需要在运行时解析格式字符串。

#### 变量注解（PEP 526）

```python
# Python 3.6 允许注解变量而不依赖类型注释
x: int = 42
name: str = "hello"

# 甚至可以不赋值——只声明类型
results: list[int]  # 类型检查器知道 results 是列表，但运行时是 None
```

> **与 PEP 484 的区别**：PEP 484 专注函数参数/返回值的注解；PEP 526 将注解扩展到**变量**层次。两者在运行时都存储在 `__annotations__` 中，但 PEP 526 允许标注局部变量和类属性，而非仅限函数签名。

#### 字典保序（CPython 实现细节 → 3.7 成为语言规范）

```python
d = {'z': 1, 'a': 2, 'b': 3}
print(list(d.keys()))   # ['z', 'a', 'b'] — 插入顺序（CPython 3.6+）

# 在 3.6 之前，键的顺序是未定义的！
```

> **CPython 实现揭秘**：CPython 3.6 对 `dict` 的底层实现做了根本性改造。旧实现（3.5 及之前）的 dict 使用一个**稀疏表**（`PyDictEntry` 数组），所有键值对混合存储在一个表中。新实现采用**分离式**结构：一个**稀疏索引表**（indices，存储哈希索引）和一个**密集条目数组**（entries，按插入顺序存储键值对）。这两者分离后，迭代时只需线性扫描密集条目数组，自然得到插入顺序。这是"顺带实现"（free lunch）——内存占用降低约 30% 的同时，获得了保序特性。

#### `secrets` 模块（PEP 506）

```python
import secrets

# 安全的随机令牌生成（不要用 random 模块做安全用途！）
token = secrets.token_hex(32)      # 64 个十六进制字符
url_safe = secrets.token_urlsafe(32)  # 43 个 Base64 URL-safe 字符

# 安全密码比较（防止时序攻击）
if secrets.compare_digest(input_pass, stored_pass):
    pass  # compare_digest 恒定时间比较，不对短匹配提前返回
```

> **安全警告**：`random` 模块使用**梅森旋转算法（Mersenne Twister）**——它是一种可预测的伪随机数生成器。如果你用 `random.choice()` 或 `random.randint()` 生成令牌、密码或密钥，攻击者可以通过观察少量输出值预测后续值。`secrets` 模块使用操作系统的**真随机源**（`/dev/urandom` 或 Windows `CryptGenRandom`），不可预测。

#### 💡 要点速查：3.6——最保值版本

> 3.6 引入的 f-string 和变量注解在之后每个版本中**只会增强、不会破坏**。3.6 是许多生产环境组织选择落脚的版本。**如果问 3.0–3.14 中哪个版本的"新增特性密度"最高，3.6 是前 3 名。** f-string 极大地改变了 Python 字符串格式化的使用占比——通常一个 Python 项目在引入 f-string 后，`%` 和 `.format()` 的调用量会下降 80% 以上。

---

### A.3.3 Python 3.7（2018-06-27）——"数据类与和谐"

#### `dataclasses`（PEP 557）

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class User:
    """一个简单的数据容器——完全不必写 __init__、__repr__、__eq__"""
    name: str
    email: str
    age: int = 18  # 默认值
    tags: List[str] = field(default_factory=list)
```

> **Python 之前有什么**：Python 长期以来缺少聚合数据的轻量级方式。社区方案包括：`namedtuple`（不可变、无类型注解）、纯 `dict`（无 IDE 提示）、自定义类（模板代码过多）。`dataclasses` 在编译时自动生成 `__init__`、`__repr__`、`__eq__`、`__hash__`、`__lt__` 等魔术方法。这本质上是**语法糖之于类生成器（class decorator）**，而非新的类模型。

`dataclasses` 的等效手工代码：

```python
class User:
    def __init__(self, name: str, email: str, age: int = 18):
        self.name = name
        self.email = email
        self.age = age

    def __repr__(self):
        return f"User(name={self.name!r}, email={self.email!r}, age={self.age!r})"

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return (self.name, self.email, self.age) == (other.name, other.email, other.age)
```

#### 字典保序成为语言规范

```python
# 在 3.6 中是 CPython 实现特性，在 3.7 中是语言规范：
# 所有 Python 实现（CPython、PyPy、Jython、IronPython）都必须保证 dict 按插入顺序迭代
d = {'b': 1, 'a': 2}
assert list(d.keys()) == ['b', 'a']  # 3.7+ 保证通过
```

#### 延迟评估的类型注解（PEP 563）——`from __future__ import annotations`

```python
from __future__ import annotations

class Node:
    def link(self, other: Node) -> None:  # Node 尚在定义中，但不报错
        ...

# 本质：注解被存储为字符串，而非类型对象
print(Node.link.__annotations__)
# {'other': 'Node', 'return': 'None'}   ← 注意是字符串，不是 <class 'Node'>
```

> **深水区**：PEP 563 解决的核心问题是"前向引用"：当一个方法注解中使用自身类 `Node`，而该类尚未定义完毕时，CPython 会抛出 `NameError`。PEP 563 将注解的求值推迟到运行时（或通过 `typing.get_type_hints()` 显式触发），使之成为字符串。但 PEP 563 在 Python 3.14 中已被 PEP 649（更彻底的延迟求值）取代。参见 A.6.4 节。

#### `breakpoint()` 内置函数（PEP 553）

```python
def complex_algorithm(data):
    result = []
    for item in data:
        breakpoint()  # 停在这里，打开 pdb（或自定义调试器）
        result.append(process(item))
    return result
```

> **跟 `import pdb; pdb.set_trace()` 相比**：`breakpoint()` 不硬编码调试器。它读取 `PYTHONBREAKPOINT` 环境变量（默认是 `pdb.set_trace`），可以指向任何兼容的调试器。设置 `export PYTHONBREAKPOINT=ipdb.set_trace` 即切换到 IPython 调试器。设置 `export PYTHONBREAKPOINT=0` 则完全禁用断点。

#### 💡 要点速查：3.7——平静而强大

> - `dataclasses` 合并了 `__init__` + `__repr__` + `__eq__`，彻底改变了 Python 的数据建模方式。小型类写 2 行而非 20 行。
> - 字典保序正式化意味着**不应再在日常代码中使用 `OrderedDict`**，除非你需要 `move_to_end()` 等功能。
> - `breakpoint()` 应成为你写入代码的默认断点方式。
> - 3.7 是"最终修复了 Python 2→3 迁移的重大体验差异"的版本。

---

## A.4 语法革命（3.8 – 3.10）

### A.4.1 Python 3.8（2019-10-14）——"海象运算符与位置参数"

#### 海象运算符 `:=`（PEP 572）

```python
# 传统写法——重复了 len(n) 调用
n = len(data)
if n > 10:
    print(f"有 {n} 条数据")

# 海象运算符——表达式内赋值并取值
if (n := len(data)) > 10:
    print(f"有 {n} 条数据")

# while 循环中的正则匹配
while (match := pattern.search(text)) is not None:
    print(f"找到匹配: {match.group()}")

# 列表推导中的海象
results = [y for x in data if (y := transform(x)) is not None]
```

> **为什么海象运算符充满争议**：PEP 572 在 Python 社区引发了前所未有的大争论，甚至导致了 Guido van Rossum 辞去 BDFL 职务。核心争议在于：**赋值到底应该是一个语句（statement）还是也可以是一个表达式（expression）**？C 系列语言中 `if (x = get_value())` 是常见的 bug 来源（误将 `=` 写成 `==`）。Python 用 `:=`（与 `=` 不同的符号）解决了歧义——`=` 永远是语句，`:=` 是表达式内的赋值。

> **什么时候用 `:=`**：① 循环条件中需要复用表达式结果；② 列表推导中避免重复计算；③ 大条件中的中间结果复用。**不要**在简单赋值中用 `:=` 替代 `=`——那不是它的目的。

#### 仅限位置参数 `/`（PEP 570）

```python
def create_user(name: str, /, age: int, *, admin: bool = False) -> str:
    """name 只能用位置参数传，admin 只能用关键字传"""
    ...

# ✅ 正确
create_user("Alice", 30, admin=True)
create_user("Bob", 25)

# ❌ 错误
create_user(name="Alice", 30, admin=True)  # name: positional-only
create_user("Alice", 30, True)             # admin: keyword-only
```

> **工程现实**：位置参数的主要用途是**保持 API 向后兼容**。当你把 `name` 设为仅限位置时，将来可以在它后面**添加更多位置参数而不破坏现有调用代码**。标准库中大量函数（如 `print`、`range`、`divmod`）都使用了此模式。

#### f-string 调试模式

```python
x = 42
y = "hello"
print(f"{x=}, {y=}")  # x=42, y='hello'   ← 等于 f"x={x}, y={y}"
print(f"{x = }")       # x = 42          ← 空格被保留
print(f"{x=:.2f}")     # x=42.00         ← 格式说明符也可用
```

#### 💡 要点速查：3.8——语法爆炸的开端

> - `:=` 三年后与 `match/case` 配合，成为 Python 3.10 结构化模式匹配中的重要组成部分。
> - 位置参数 `/` 的引入完成了 Python 参数传递系统的最后一块拼图：`/`（仅限位置）-普通参数-`*`（仅限关键字）。
> - 不要在海象运算符中使用 `:= 0` 或 `:= []` 作为默认值——它会在赋值时在括号内持有一个临时引用。
> - **f-string `=` 调试模式**是调试时的快捷键。`print(f"{x=}")` 直接代替 `print(f"x={x!r}")`。

---

### A.4.2 Python 3.9（2020-10-05）——"字典合并与类型系统简化"

#### 字典合并运算符 `|` 和 `|=`（PEP 584）

```python
base_config = {"host": "localhost", "port": 8080}
user_config = {"port": 9090, "debug": True}

# 合并（右侧覆盖左侧同名键）——产生新字典
merged = base_config | user_config
# {"host": "localhost", "port": 9090, "debug": True}

# 原地合并
base_config |= user_config
```

> **与 `{**d1, **d2}` 的区别**：语法等效。`d1 | d2` 在语义上等价于 `{**d1, **d2}`，但 `|=` 的原地语义（不创建新字典）在合并大量配置时内存更友好。此外，`|` 运算符支持 `dict` 子类（如 `defaultdict`），而 `{**d1, **d2}` 会产生普通 `dict`。

#### `str.removeprefix()` 和 `str.removesuffix()`（PEP 616）

```python
filename = "prefix_report.txt"

# 旧写法——容易出错的切片
cleaned = filename[len("prefix_"):] if filename.startswith("prefix_") else filename

# 新写法
cleaned = filename.removeprefix("prefix_")  # "report.txt"
trimmed = filename.removesuffix(".txt")     # "prefix_report"
```

> **为什么到 3.9 才加？** `str.removeprefix` 是 Python 社区最长时间的被请求特性之一（约 2010 年起）。此前推荐的做法是 `s[len(prefix):]`（不检查是否存在），或者 `s[5:] if s.startswith('prefix') else s`（啰嗦）。3.9 的这两个方法看起来微小，但让许多文件路径处理的代码从 5 行变为 1 行。

#### 类型提示泛型简化（PEP 585）

```python
# Python 3.8 及之前——需要从 typing 导入
from typing import List, Dict, Optional

def process(items: List[str]) -> Optional[Dict[str, int]]:
    ...

# Python 3.9+——直接用内置类型
def process(items: list[str]) -> dict[str, int] | None:
    ...
```

> **为什么重要**：这终结了 `typing` 模块和内置类型之间的平行宇宙。`list[str]`、`dict[str, int]`、`set[bytes]` 现在是第一类语言特性。对大型代码库的迁移，只需要查找替换 `List[` → `list[` 等。**PEP 585 配合 PEP 604（3.10）的 `X | Y` 联合类型，可以让 90% 的 `typing` 模块引用消失。**

#### `zoneinfo` 时区模块（PEP 615）

```python
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

# 替代了第三方库 pytz 和 dateutil
dt = datetime(2024, 10, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
print(dt)               # 2024-10-01 00:00:00+08:00
print(dt.tzname())      # 'CST'
```

> **工程真相**：`pytz` 库长期存在一个讨厌的陷阱：`datetime(2024, 10, 1, tzinfo=pytz.timezone('Asia/Shanghai'))` 会给出**错误的时区偏移**，因为 `pytz` 要求在本地化时间之前调用 `localize()` 方法。`zoneinfo` 完全避免了这个问题，直接支持 IANA 时区数据库。

#### 💡 要点速查：3.9——类型系统的清理

> - 字典 `|` 运算符使配置合并变得直观。
> - `str.removeprefix/removesuffix` 是"微小但让代码质量显著提升"的方法。
> - 如果你从 3.7 迁移到 3.9，最大的收益来自**去掉所有 `typing.List`、`typing.Dict` 等冗余导入**。
> - `zoneinfo` 为 Python 提供了第一方时区支持——**不要再在新项目中用 `pytz`**。

---

### A.4.3 Python 3.10（2021-10-04）——"模式匹配之年"

#### 结构化模式匹配 `match`/`case`（PEP 634–636）

这是 Python 历史上影响力最大的语法新增之一：

```python
# 基本情况——替代复杂的 if/elif 链
def describe(value):
    match value:
        case 0:
            return "zero"
        case 1 | 2:              # 组合模式——匹配 1 或 2
            return "small"
        case int(n) if n > 100:  # 守卫条件
            return "big number"
        case str(s):              # 类型匹配 + 解构
            return f"string: {s}"
        case [x, y]:              # 序列解构
            return f"list of 2: {x}, {y}"
        case {"key": k}:          # 字典解构
            return f"dict with key={k}"
        case _:                   # 通配符
            return "something else"
```

```python
# 数据类的模式匹配
@dataclass
class Point:
    x: int
    y: int

def locate(point):
    match point:
        case Point(0, 0):
            return "origin"
        case Point(0, y):
            return f"on Y axis at {y}"
        case Point(x, y):
            return f"at ({x}, {y})"
```

> **深水区**：`match` 不是简单的 `switch` 升级。它的设计借鉴自 Haskell、Rust 和 Elixir 的模式匹配。表达式在 `match` 被求值一次，然后以**结构性**匹配进入 `case` 分支——它检查的是"值的形状"（type + structure），而非简单等号比较。核心机制：`case [x, y]` 中的 `x` 和 `y` 是**模式变量**（pattern variables），它们在匹配成功时从被匹配对象中解构出来**绑定到新变量**。如果一个字面量（如 `0`、`"hello"`）出现在 `case` 中，它等同于常量比较。

**另一种观察方式**——拆解 `match` 的执行过程：

```
match [1, 2, 3]:
    case [a, *rest]:
        print(a, rest)

# 等价于：
subject = [1, 2, 3]
# CPython 生成字节码执行：
# 1. 检查 subject 是否序列（__iter__ 协议）
# 2. 尝试匹配头部 a = subject[0]
# 3. 将剩余元素绑定到 rest = subject[1:]
# 4. 如果成功，进入 case 分支
```

#### 更好的错误信息

```python
# Python 3.10 起，语法错误会包含更精确的位置提示：

# ❌ `x = 1 +` 缺少操作数
#     File "test.py", line 1
#       x = 1 +
#             ^
#     SyntaxError: invalid syntax. Perhaps you forgot a comma?

# ❌ 不匹配的括号
#     File "test.py", line 1
#       func(x, y(z]
#                 ^
#     SyntaxError: closing parenthesis ']' does not match opening parenthesis '('
```

#### 联合类型 `X | Y`（PEP 604）

```python
# 3.10+ 可以用 | 表示联合类型
def process(value: int | str) -> int | str | None:
    ...

# 替代旧写法：
from typing import Union, Optional
def process(value: Union[int, str]) -> Union[int, str, None]:
    ...
```

#### 💡 要点速查：3.10——学习 curve 最大的版本

> - `match/case` 是所有 Python 版本中学习曲线最陡的特性。推荐用以下顺序掌握：① 字面量匹配 → ② 通配符 `_` → ③ 类型匹配 → ④ 守卫条件 → ⑤ 序列/字典解构 → ⑥ 类模式 + 数据类。
> - `|` 联合类型让类型注解更为简洁。完整的迁移方式：`Union[X, Y]` → `X | Y`，`Optional[X]` → `X | None`。
> - 在 Python 版本升级中，3.10 的开发者体验改进（更好的错误信息）是最被低估的特性。

---

## A.5 性能与底层革命（3.11 – 3.14）

### A.5.1 Python 3.11（2022-10-24）——"Faster CPython 落地"

3.11 的标志性成就是实现 CPython 平均 **25%** 的性能提升——这是自 Python 3.0 以来最显著的性能改进。项目代号"Faster CPython"，由微软资助。

#### 性能改进架构

```
Python 3.10 执行流程：
  .py → AST → 字节码 → PVM 逐条执行

Python 3.11 执行流程：
  .py → AST → 字节码 → 特化（Adaptive）→ PVM 带缓存执行
                     ↓
                内联缓存（Inline Cache）优化常见操作
```

> **CPython 实现揭秘**：3.11 的加速核心是**自适应字节码特化（Adaptive Bytecode Specialization）**。CPython 在执行普通字节码（如 `LOAD_GLOBAL`、`BINARY_OP`）时，改用了**自适应指令**。这些指令在首次执行时以通用方式工作（类似 3.10），同时记录操作数类型。后续执行时，如果操作数类型和之前一致，直接走"特化路径"——由特殊用途（specialized）的快捷指令处理，跳过通用逻辑中的类型检查和分支。对于类型稳定的代码（如循环内的 `for item in list`），这接近于 JIT 编译的"热点检测"效果。

#### 异常组 `ExceptionGroup` 和 `except*`（PEP 654）

```python
# 同时抛出多个不相关异常
def validate(data):
    errors = ExceptionGroup("validation errors",
        [ValueError("age < 0"),
         TypeError("name must be str")])
    raise errors

# 分别捕获：
try:
    validate(data)
except* ValueError as e:
    print(f"Value errors: {e.exceptions}")
except* TypeError as e:
    print(f"Type errors: {e.exceptions}")
```

> **实用场景**：并发编程中，`asyncio.gather()` 可能同时有多个协程失败。此前只能用一个 `Exception` 包含它们，或者使用 `return_exceptions=True` 然后手动过滤。`ExceptionGroup` 允许异常以**树形结构**传播和捕获。注意：`except*` 只能用在 `ExceptionGroup` 上，不能替代普通的 `except`。

#### 零成本异常处理（Zero-Cost Exception Handling）

```python
def compute(value):
    # 3.11 之前：每条 try 语句都在栈上预留异常处理信息，有运行时开销
    # 3.11 之后：try 的正常路径零开销——异常信息只在 throw 时才查找
    try:
        return 100 / value
    except ZeroDivisionError:
        return float('inf')
```

> **实现机制**：CPython 3.11 将异常处理信息从执行时的栈帧元数据移入**字节码对象的附加数据**（`co_exceptiontable`）。正常执行路径完全不接触异常表；当异常抛出时才通过字节码偏移量查找对应处理器的位置。这消除了零成本抽象的最后瓶颈。

#### `Self` 类型（PEP 673）

```python
from typing import Self

class Shape:
    def set_color(self, color: str) -> Self:
        self.color = color
        return self

class Circle(Shape):
    ...

c = Circle().set_color("red")  # c 的类型是 Circle，不是 Shape！
```

> **工程意义**：此前的类型注解 `-> "Shape"` 会阻止子类链式调用时类型信息的传递。`Self` 正确地追踪到 `Circle`。

#### 💡 要点速查：3.11——性能里程碑

> - 从 3.10 升级到 3.11 可以获得 **25% 的免费性能提升**。这是 Python 历史上投入产出比最高的版本升级。
> - **自适应特化**机制意味着运行时间越长的进程，3.11 的优势越大（因为热点路径会被反复特化）。短脚本（<1s）的加速比不明显。
> - `ExceptionGroup` 在异步/并发代码中广泛使用。
> - `Self` 类型是类层次结构设计者等待已久的特性——现在子类的链式 API 终于能在 mypy 检查中正确工作了。

---

### A.5.2 Python 3.12（2023-10-02）——"子解释器与隔离"

#### 子解释器（Sub-Interpreters）——每个解释器独立 GIL（PEP 684）

```python
# 3.12 的 PEP 684 允许多个独立的 Python 解释器运行在同一个进程内
# 每个解释器都有自己的 GIL！

# 使用场景：CPU 密集型的纯 Python 代码可以真正并行
from concurrent.futures import ThreadPoolExecutor
# 3.12+ 允许在不同子解释器上运行的任务并行获取 GIL
```

> **深水区**：在 3.11 及之前，即使使用多线程，CPython 的 GIL 也保证同一时间只有一个线程执行 Python 字节码。这是 CPython 与生俱来的限制。PEP 684（通过 `Py_NewInterpreter` 底层 API）允许多个各自持有独立 GIL 的 CPython 解释器存在于同一进程。但此功能主要面向底层库作者（如嵌入 Python 的 C 应用），并非普通的 `threading.Thread` 用户可以**直接**感知。高层的多线程环境（如 Jupyter、WSGI 服务器）需要显式适配才能利用。

#### `itertools.batched()`（Python 3.12 新函数）

```python
from itertools import batched

data = [1, 2, 3, 4, 5, 6, 7, 8]

# 每 3 个元素分一批
for batch in batched(data, 3):
    print(batch)
# (1, 2, 3)
# (4, 5, 6)
# (7, 8)

# 此前需要自己写：
# for i in range(0, len(data), 3):
#     batch = data[i:i+3]
```

#### f-string 语法统一（PEP 701）

```python
# 3.12 之前，f-string 内不能使用外部 f-string 引用的字符串
s = "world"
# f"hello {f"deep {s}"}"  # 语法错误

# 3.12+ —— f-string 可以任意嵌套！
print(f"hello {f"deep {s}"}")  # "hello deep world"

# 也允许在 f-string 内使用多行表达式
result = f"""{
    ', '.join(str(i) for i in range(10))
}"""
```

> **工程意义**：PEP 701 修复了一个长达 7 年的 f-string 设计缺陷——之前 f-string 不允许嵌套使用同类型引号。这使得在模板生成、SQL 构建、动态代码生成时极为不便。

#### 💡 要点速查：3.12——底层架构的分水岭

> - 子解释器是 Python 自 3.0 以来最底层的架构革新。它对普通 Python 开发者**暂时透明**，但它提供了 CPython 在进程中实现 CPU 并行执行的基础设施。
> - `itertools.batched()` 是标准库中第一个分批次迭代的方法——在此之前你需要自己用 `range` 切片。
> - f-string 嵌套的语法统一让复杂的模板生成场景变得可用——这是**f-string 自 3.6 以来的最大语法改进**。

---

### A.5.3 Python 3.13（2024-10-01）——"自由线程与 JIT"

3.13 是 Python 32 年历史上最激进的版本。**它在一个版本中同时推出"去 GIL"和"JIT 编译器"两个重大变革**（均为实验性功能）。

#### 自由线程（Free-Threaded Python，PEP 703）

```python
# 编译时通过 --disable-gil 启用无 GIL 模式
# 运行时验证 GIL 是否禁用：
import sys
print(sys._is_gil_enabled())  # False 表示自由线程模式

# 现在多线程纯 Python 代码可以真正并行：
import threading
import time

results = []
def work(n):
    time.sleep(0.1)
    results.append(n)

threads = [threading.Thread(target=work, args=(i,)) for i in range(100)]
for t in threads: t.start()
for t in threads: t.join()
# 在自由线程模式下，这 100 线程的工作不是被 GIL 串行化的
```

> **为什么这是革命性的**：GIL（全局解释器锁）自 1992 年 CPython 第一个版本就存在。它简化了内存管理（引用计数不需要每个对象加锁），但使得多线程 Python 代码在多核 CPU 上**无法利用多于一个核**。PEP 703 的基本策略是：① 将全局引用计数改为**每个对象的细粒度锁**或**偏序引用计数（biased reference counting）**——大部分引用变化只更新线程本地计数，减少锁争用；② 将全局 GC 状态改为线程本地状态。这是 CPython 发展史上对核心架构改动最大的 PEP。

> **⚠️ 当前状态**（Python 3.13）：自由线程是**实验性**的。默认安装仍然是带 GIL 的实现。需要通过 `--disable-gil` 编译选项或使用专门的二进制发行版来启用。此外，C 扩展（如 NumPy、pandas）在自由线程模式下**不完全支持**——3.13 的主要意义是为 C 扩展库作者提供迁移缓冲期。**Python 3.14 继续完善，预计到 3.15–3.16 才能成为生产环境选项。**

#### 实验性 JIT 编译器（PEP 744）

```
3.13 JIT 采用的"copy-and-patch"策略（而非传统的 tracing JIT）：
  字节码序列 → 预编译的模板副本 → 替换操作数为实际值 → 生成机器码

优点：开发工作量低（不需完整的 JIT 后端），编译速度快
目前效果：特定热点场景加速 5–10%，但编译时间增加了 5–15%
```

> **需要注意**：这不是类似 PyPy 的完整 JIT（后者能提速 4–10 倍）。CPython 3.13 JIT 的主要目标不是大幅提速，而是**构建 JIT 基础设施**，使其能在后续版本中逐步强化。这也是 CPython 官方从纯解释器转向"可选 JIT"的重要一步。

#### 改进的交互式 REPL（PEP 705）

```python
# 3.13 的 REPL 支持多行编辑、语法高亮、颜色输出、tab 补全
# 输入多行函数时，REPL 会自动缩进

# 之前（3.12 及之前）：
>>> def greet(name):
...     print("Hello")
...     print(name)
...                     # 必须手动空行结束

# 3.13+：
>>> def greet(name):    # REPL 自动识别已完毕，不需空行
...     print("Hello")
...     print(name)
>>>
```

#### 💡 要点速查：3.13——值得记住的"实验版本"

> - **需要理解**：3.13 是"基建版本"。自由线程和 JIT 两项功能都是实验性的，主要面向开发和测试，**不推荐在生产环境启用**。
> - 如果你在 PyPI 上使用 C 扩展（如 NumPy、Pandas、scikit-learn），直到该扩展发布适配自由线程的版本前，你在带 GIL 模式下运行 3.13 与 3.12 没有区别。
> - REPL 改进是实际可用且默认开启的。
> - 3.13 的改进 REPL 不依赖 `pip install` 任何第三方包——这是一个纯标准库的提升。

---

### A.5.4 Python 3.14（2025-05-20）——"注解延迟求值终章"

3.14 是撰写本章时的**最新稳定版**。最大的特性是 PEP 649，它完成了类型注解延迟求值的最终形态。

#### 注解的延迟求值（PEP 649）——**替代 PEP 563**

```python
# PEP 649：注解的真正的"延期求值"
# 之前（3.14 之前）：
class Box:
    def pack(self, item: list[int]) -> list[int]:  # ← 运行时求值 list[int]
        return item

print(Box.pack.__annotations__)
# 不带 PEP 563/649：{'item': list[int], 'return': list[int]}  ← 类型对象
# 带 PEP 649：{'item': 'list[int]', 'return': 'list[int]'}     ← 字符串

# 区别在于 PEP 563 将注解无差别转为字符串（即使不需要）；
# PEP 649 则使用描述符（descriptor）——仅在显式访问 __annotations__ 时才求值
```

> **为什么 PEP 649 优于 PEP 563**：PEP 563（3.7 中的 `from __future__ import annotations`）有一个严重问题——它将所有注解都**无条件地**转为字符串。这意味着：
> ```
> from __future__ import annotations
> from typing import Any
> x: Any = 42   # 这里的 'Any' 被转为字符串，类型检查器需要在运行时重新解析
> ```
> PEP 649 使用**惰性描述符**（lazy descriptor）替代无条件字符串化——注解的编码在函数的 `__annotations__` 字典中作为描述符对象存在，只在**显式访问**时才求值。这避免了 PEP 563 的所有已知问题：类型检查器不需要字符串解析、装饰器不需要兼容调整、序列化（`pickle`）正常工作。

#### 性能持续改进

```python
# 3.14 在 3.13 基础上继续优化：
# - 针对 f-string 的字节码改进（f-string 的编译更高效）
# - 更快的 list/dict 推导式
# - 内联缓存的扩展，覆盖更多常见操作
```

#### 错误信息进一步改进

```python
# Python 3.14 的语法错误提示更加精准：
# 输入: x = [1, 2, 3,}
# 输出:
#   File "test.py", line 1
#     x = [1, 2, 3,}
#                ^^^^
#   SyntaxError: mismatched bracket: '}' does not match '[' (opened at column 4)
#   Did you mean to close with ']' instead?
```

#### 💡 要点速查：3.14——当前最新，稳定推荐

> - **`PEP 649` 是类型注解历史中最重要的一次实现变更**。如果过去你因为 PEP 563 的已知问题而未使用 `from __future__ import annotations`，3.14 是你重新启用注解延迟求值的时机。
> - 与 3.13 不同，3.14 的**延迟求值是默认关闭的**（需要通过 `from __future__ import annotations` 启用），而非默认启用。PEP 649 按计划逐步实施。
> - 如果你是新项目，**从 3.14 开始是正确选择**。
> - 整体性能（带 GIL 默认模式）相比于 3.13 进一步小幅提升，主要来自编译器和运行时优化。

---

## A.6 跨越版本的最佳实践

### A.6.1 版本兼容性速查表

当你编写需要兼容多个版本 Python 的代码时，下面的表可以作为快速决策参考：

| 你想用的特性 | 引入版本 | 降级替代方案 |
|------------|---------|-------------|
| f-string `f"..."` | **3.6** | `.format()` / `%` 格式化 |
| `dataclasses` | **3.7** | `namedtuple` / 手动编写 `__init__` |
| 海象运算符 `:=` | **3.8** | 提前赋值，或嵌套 `if` |
| 位置参数 `/` | **3.8** | 文档约定（无法语法强制执行） |
| 字典合并 `\|` | **3.9** | `{**d1, **d2}` |
| `str.removeprefix/removesuffix` | **3.9** | `s[len(prefix):]` + `startswith` 检查 |
| `match/case` | **3.10** | `if/elif` 链 |
| 联合类型 `X \| Y` | **3.10** | `Union[X, Y]`（从 `typing` 导入） |
| `ExceptionGroup` / `except*` | **3.11** | 手动包装和过滤异常 |
| `Self` 类型 | **3.11** | `-> "ClassName"` 字符串注解 |
| `itertools.batched()` | **3.12** | `zip(*[iter(data)]*n)` 或 `range` 切片 |
| f-string 嵌套（同引号） | **3.12** | `eval()` / 区分单双引号 |
| 自由线程（去 GIL） | **3.13 实验** | 用 `multiprocessing` 替代 `threading` |
| JIT 编译器 | **3.13 实验** | 标准模式无影响 |
| PEP 649 延迟注解 | **3.14** | PEP 563 `from __future__ import annotations` |

### A.6.2 `__future__` 导入清单

`__future__` 允许在**当前版本**使用将来版本的特性：

```python
# 常见的 __future__ 导入：

# 3.7+： PEP 563 延迟注解（已被 PEP 649 取代方向，但在 3.14 仍可用）
from __future__ import annotations

# 3.0+：真除法
from __future__ import division
# 在 3.x 中已是默认，主要用于 2→3 过渡

# 3.10+：PEP 604 联合类型 | 的旧兼容（3.10+ 已默认）
# 无需 __future__ 导入——X | Y 从 3.10 开始就是语法的一部分
# 但 typing.Union 等价写法在所有版本都可用

# 3.12+：annotation 的字符串化已在 3.14 被 PEP 649 替代
# 3.14 中 from __future__ import annotations 仍工作，
# 但推荐关注 PEP 649 的演进
```

### A.6.3 Python 版本选择建议

| 使用场景 | 推荐版本 | 原因 |
|---------|---------|------|
| **学习 Python（2026 年）** | **3.14** | 最新稳定，可获得最好的错误信息、最新特性、安全修复 |
| **新项目（生产环境）** | **3.14** 或 **3.13** | 3.14 是最新稳定；3.13 生态更成熟（第三方包充分测试） |
| **需要 C 扩展兼容** | **3.12** 或 **3.13** | 3.13+ 的 C 扩展 ABI 变更（去 GIL 实验），部分库尚在适配 |
| **最大性能需求（单核）** | **3.13/3.14** | Faster CPython + 实验性 JIT，单线程碾压 3.12 |
| **最大性能需求（多核）** | **3.13+（自由线程实验）** | 或继续用 `multiprocessing`（更稳妥） |
| **遗留项目维护** | **3.8 – 3.11** | 视第三方依赖锁定版本 |

### A.6.4 版本升级注意事项

**3.6 → 3.7**：字典顺序从"CPython 实现特性"变为"语言保证"。如果你的代码或库依赖于随机化字典顺序（极少数情况），需要修复。

**3.7 → 3.8**：海象运算符 `:=` 不破坏现有代码。但 `pickle` 协议版本变更需要注意。

**3.8 → 3.9**：`typing` 中的泛型（`List`、`Dict` 等）没有立即移除，无破坏性变更。

**3.9 → 3.10**：`match/case` 是软关键字——旧代码中 `match` 作为变量名的不会报错。**最大的破坏性变更来自 `distutils` 的移除**（已在 3.10 中弃用，3.12 完全移除）。

**3.10 → 3.11**：**无明显破坏性变更**。这是 Python 历史上最平滑的主版本升级之一。

**3.11 → 3.12**：`distutils` 完全移除。移除 `imp` 模块。`asyncio.iscoroutine()` 等标记弃用。

**3.12 → 3.13**：C 扩展 ABI 不兼容（自由线程/不允许静态 GIL 依赖）。**大多数纯 Python 代码不受影响。**

**3.13 → 3.14**：PEP 649 注解延迟求值。如果你使用 `from __future__ import annotations` 且依赖注解在运行时的字符串化行为，需要验证。

---

## A.7 结语：32 年演进路线图

从 1991 年的 0.9.0 到 2025 年的 3.14，Python 走过了 34 年。从附录的角度回看 3.x 的演进，可以总结为三条主线的不断加深：

1. **语法现代化**：从 `print` 语句 → f-string → 海象运算符 → `match/case`
2. **类型安全**：从 PEP 484（函数注解）→ PEP 526（变量注解）→ PEP 585（内置泛型）→ PEP 649（延迟求值）
3. **性能突破**：从纯解释器 → Faster CPython（自适应特化）→ JIT 编译器 → 自由线程

**三条主线分别呼应现代编程语言的三个趋势**：更好的开发者体验、更安全的工程实践、更强的运行时表现。

对于学生而言，这张版本演变图回答了两个核心问题：① "我学到的这个语法/API 是哪个版本引入的，我的代码是否依赖这个版本？" ② "不同版本的具体差异在哪里，当我在 GitHub 上看到一段用 `:=` 的代码，它是多大范围内的产物？"

**这份版本演进宝典正是为此存在的。**

---

> **附录 A 版本信息**：覆盖 Python 3.0（2008）至 Python 3.14（2025）。本章中的代码示例基于 CPython 3.14 验证。PEP 编号和版本对应关系可在 https://peps.python.org 查询。
