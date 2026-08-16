# 第13章 标准库精选

> **学习目标**：建立"标准库即兵器库"的心智地图——知道**什么场景该翻哪个模块**；吃透最常用的十个工具箱（容器/迭代器/函数/时间/数字/进程/持久化/日志/类型）的底层实现与陷阱；能区分"用标准库"与"上第三方库"的边界，并学会直接阅读 `Lib/` 源码。

---

前 10 章把 Python 语言本身讲透了：对象模型、控制流、函数、类、IO、模块。但"会语言"不等于"会干活"——真正让你写程序快的是**标准库**。Python 的杀手锏之一就是"自带电池"（batteries included）：`tar` 解压、Excel 读取、数据库、HTTP 服务器……系统该配的都配齐了。本章不是 API 字典，而是**兵器库导览**：每个模块讲清"它解决什么问题、底层怎么实现、坑在哪、什么时候该换第三方"。

本章与前面章节的关系：第 3 章讲了 `dict`/`list`/`tuple` 等内置容器，13.2 的 `collections` 是它们的**专业变体**；第 5 章的迭代器协议与生成器，在 13.3 的 `itertools` 里被用到极致；第 6 章的函数式编程（`lambda`/高阶函数/闭包），13.4 的 `functools` 是它的标准库化；第 9 章的 `json`/`pathlib`/`tempfile`/`struct` 与第 7 章的 `dataclass`/`enum`、第 8 章的 `contextlib`、正则专题的 `re`，本章**均不重复**，只在需要时交叉引用；`queue`/`threading` 等并发工具点到为止，第 11 章细讲。

---

## 13.1 标准库全景与选择哲学

### 13.1.1 "自带电池"：标准库的规模与组织

Python 标准库有 **300+ 个模块条目**（`sys.stdlib_module_names` 数到 313），从 `abc`（抽象基类）到 `zoneinfo`（时区），大部分是**纯 Python**（在 `Lib/` 目录），少部分是 **C 实现**（在 `Modules/` 目录，编译进解释器或作为内置扩展）。

```python
# 标准库全量清单（3.10+ 提供）
>>> import sys
>>> len(sys.stdlib_module_names)
313
>>> "collections" in sys.stdlib_module_names
True
>>> "requests" in sys.stdlib_module_names      # 第三方不在其中
False
```

`sys.stdlib_module_names`（PEP 594 时代的配套设施）是"标准库模块的权威清单"。注意：`os.path` 这类子模块不算独立条目，且清单**不含** `__main__` 等运行时伪模块。

按领域把常用模块画成"六象限地图"：

| 领域 | 代表模块 | 本章位置 |
|------|---------|---------|
| **数据与容器** | `collections`、`itertools`、`functools`、`array`、`bisect`、`heapq` | 13.2–13.4 |
| **文本与时间** | `string`、`datetime`、`zoneinfo`、`calendar`、`unicodedata` | 13.5 |
| **数字与随机** | `math`、`decimal`、`fractions`、`random`、`statistics` | 13.6 |
| **系统与进程** | `os`、`sys`、`subprocess`、`shutil`、`glob`、`platform` | 13.7 |
| **持久化与配置** | `sqlite3`、`csv`、`configparser`、`argparse`、`json`（第9章） | 13.8 |
| **工程工具** | `logging`、`typing`、`dataclasses`（第7章）、`contextlib`（第8章） | 13.9–13.10 |

> **实战建议**：不要背清单——**按问题找模块**：遇到"去重计数"查 `collections.Counter`，遇到"嵌套循环"想 `itertools.product`，遇到"进程调用"用 `subprocess.run`。本章给你的就是这个"问题 → 模块"的索引。

#### 文本象限快速导览：string / unicodedata / textwrap

六象限地图里"文本与时间"横跨第 13.5 与这里。除 `str` 方法（第 3 章）与 `re`（专题）外，三个高频文本工具：

```python
>>> import string
>>> string.ascii_letters, string.digits           # 字符常量集
('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', '0123456789')
>>> string.Template("$name is $age").substitute(name="Alice", age=30)   # 模板替换
'Alice is 30'
>>> # Template 的 $ 语法与 str.format 的 {} 语法对比：模板适合"非程序员编辑"的场景

>>> import unicodedata
>>> unicodedata.name("汉")                        # 码点 → 名称
'CJK UNIFIED IDEOGRAPH-6C49'
>>> unicodedata.normalize("NFKC", "ｆｕｌｌｗｉｄｔｈ")   # Unicode 规范化（全角→半角）
'fullwidth'

>>> import textwrap
>>> textwrap.wrap("很长的文本……", width=20)       # 按宽度折行
['很长的文本……', ...]
>>> textwrap.dedent("""\
...     indent 对齐
...     dedent 移除公共前导空白""")
'  indent 对齐\ndedent 移除公共前导空白'
```

> **实战建议**：`string.Template` 用于"用户可编辑的模板"（`$var` 语法比 `{}` 更不易出错）；`unicodedata.normalize` 是**文本清洗**的起点（全半角、组合字符）；`textwrap.dedent` 搭配多行字符串写"缩进安全的 docstring/代码生成"。`codecs`/`bytes` 解码细节已在第 9 章覆盖。

### 13.1.2 选型哲学：标准库 vs 第三方

"标准库一定够用"和"标准库一定落后"都是错的。决策矩阵：

| 维度 | 标准库 | 第三方 |
|------|--------|--------|
| 稳定性 | ★★★★★（版本演进极其保守） | 参差（看维护状况） |
| 依赖成本 | 零（自带） | 要装、要锁、要升级 |
| 性能 | 核心模块是 C 实现，够快 | 优化空间大（如 `orjson`） |
| 功能覆盖 | 通用，不追新 | 领域专用、迭代快 |
| 风险 | 演进慢（想换 API 要等大版本） | 供应链、停止维护、API 漂移 |

**经典案例：`urllib` vs `requests`**

```python
# 标准库 urllib：能用，但 API 反人类
import urllib.request
with urllib.request.urlopen("https://api.example.com/data", timeout=10) as resp:
    data = resp.read()

# 第三方 requests：20 行变 1 行，且自动处理连接池/重试/编码
import requests
resp = requests.get("https://api.example.com/data", timeout=10)
data = resp.json()
```

`urllib` 是标准库，`requests` 是第三方——但**工程上几乎总是选 `requests`**。为什么？因为 HTTP 客户端的痛点不在"能不能发请求"，而在连接池、重试、超时、编码探测、会话 cookie 这些**工程细节**，标准库的定位是"协议实现"而非"好用客户端"。

> **设计哲学**：标准库承诺的是"**正确的基础能力**"而不是"**最好的体验**"。判断标准：你的场景是"偶尔用一次的系统能力"（标准库够）还是"天天用的核心路径"（值得上成熟的第三方）？另一个信号：**标准库新版本也会吸收社区最佳实践**——`zoneinfo`（PEP 615）吸收 `pytz` 的教训、`importlib.metadata` 吸收 `pkg_resources` 的教训、`dataclasses` 吸收 `attrs` 的教训。**每 2–3 年回看一次标准库，新版本可能已经替你升级了。**

### 13.1.3 读标准库源码的方法

"读标准库源码"是 Python 工程师的最高效成长路径——它代表官方认可的写法，且**多数模块就是普通 Python**。

```python
# 方法 1：inspect 直接看源码（无需找路径）
>>> import inspect, collections
>>> print(inspect.getsource(collections.Counter.most_common))
    def most_common(self, n=None):
        '''List the n most common elements...'''
        if n is None:
            return sorted(self.items(), key=_itemgetter(1), reverse=True)
        return heapq.nlargest(n, self.items(), key=_itemgetter(1))
```

```bash
# 方法 2：直接翻 Lib/ 目录（Windows 上在解释器目录下）
$ python -c "import sysconfig; print(sysconfig.get_path('stdlib'))"
C:\Python314\Lib
```

```python
# 方法 3：区分"纯 Python 实现"与"C 实现"
>>> import collections, json
>>> collections.Counter.__module__      # 顶层类是 C 实现
'_collections'                          # ← C 加速部分在 _collections
>>> json.JSONDecoder.__module__         # 纯 Python
'json.decoder'
```

> **🔑 机制洞察**：标准库的常见模式是"**C 加速 + Python 兜底**"——`collections` 的 `_collections`（C）与纯 Python 版本并存，导入时优先 C（`_collections` 存在则用，否则退回 `_collections_abc` 的纯 Python 实现）。`import collections; collections.Counter.__module__` 显示 `_collections` 正是这个机制的证据。读源码时先问一句"这是 C 还是 Python 实现"，能避免把"实现细节"当成"语言特性"。

---

## 13.2 collections：容器工具箱

第 3 章的内置容器（`dict`/`list`/`tuple`/`set`）是地基，`collections` 是"专业变体"——每个都是为解决一个具体痛点而生的。

### 13.2.1 defaultdict 与 Counter

#### `defaultdict`：`__missing__` 协议的第一个实战

```python
>>> from collections import defaultdict
>>> d = defaultdict(list)
>>> d["key"]                    # 访问不存在的键 → 不抛 KeyError，调用 list() 生成默认值
[]
>>> d["key"].append(1)          # 经典场景：分组收集
>>> d
defaultdict(<class 'list'>, {'key': [1]})
```

机制：`defaultdict` 是 `dict` 子类，重写了 `__missing__(key)`——`dict.__getitem__` 在键不存在时会调用它（第 7 章 7.6 的属性查找是另一处 `__missing__` 之外的钩子，这里才是 `__missing__` 的正主）：

```python
# defaultdict 的核心逻辑（collections/__init__.py 中的简化版）
class defaultdict(dict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = self.default_factory()   # 生成默认值并写入
        return self[key]
```

```python
# ❌ 反模式：手动检查键存在性（啰嗦且容易漏）
d = {}
if "key" not in d:
    d["key"] = []
d["key"].append(1)

# ✅ defaultdict：一行
d = defaultdict(list)
d["key"].append(1)
```

> **⚠️ 陷阱**：`defaultdict` 的"默认值"只在 `d[key]` 访问时触发——`d.get(key)`、`key in d`、`d.setdefault(key)` **不触发** `__missing__`。`setdefault` 与 `defaultdict` 的差异要分清：前者每次调用都执行默认值工厂（即使键已存在），后者只在缺失时执行一次。

#### `Counter`：计数即字典

```python
>>> from collections import Counter
>>> c = Counter("abracadabra")
>>> c
Counter({'a': 5, 'b': 2, 'r': 2, 'd': 1, 'c': 1})
>>> c.most_common(2)
[('a', 5), ('b', 2)]
```

`Counter` 是 `dict` 子类（键 → 计数），但附加了**计数的算术语义**：

```python
>>> Counter("aab") + Counter("abb")      # 加法：计数相加
Counter({'a': 2, 'b': 3})
>>> Counter("aab") - Counter("abb")      # 减法：非负裁剪
Counter({'a': 1})
>>> Counter("aab") & Counter("abb")      # 交集：取较小计数
Counter({'a': 1, 'b': 2})
>>> Counter("aab") | Counter("abb")      # 并集：取较大计数
Counter({'a': 2, 'b': 2})
```

底层加速：`Counter.update`/`Counter.__iadd__` 在 CPython 里走 `_count_elements`（`Modules/_collectionsmodule.c`）——一个专门优化的 C 循环，比"`for` 循环手动数"快一个量级：

```python
# timeit 对比：手动计数 vs Counter（10^6 个元素的列表）
>>> from collections import Counter
>>> import timeit
>>> data = list(range(1000)) * 1000
>>> timeit.timeit(lambda: Counter(data), number=10)
0.042
>>> def manual():
...     d = {}
...     for x in data:
...         d[x] = d.get(x, 0) + 1
...     return d
>>> timeit.timeit(manual, number=10)
0.61            # Counter 快约 15 倍（C 循环 vs Python 循环）
```

> **🔑 性能洞察**："能用 `Counter` 的计数"与"手写 `for` 计数"的差距来自 C 层 `_count_elements` 对 dict 操作的批量优化。规则：**标准库里已有数据结构的场景，先查 `collections` 再手写**——你手写的 Python 循环几乎不可能比 C 加速版本快。

### 13.2.2 OrderedDict 与 dict 保序

#### 3.7 之前：dict 无序，OrderedDict 救场

Python 3.6 之前，`dict` 的迭代顺序是"未定义的"（实际是哈希表槽位顺序，随插入/删除剧烈变化）。`OrderedDict`（PEP 372，2.7/3.1）用**双向链表**记录插入顺序。

**PEP 468**（3.6）让 `dict` 保持插入顺序（CPython 实现细节，3.7 起成为语言规范，PEP 567 确认）。从此 `OrderedDict` 的"保序"价值消失，但它的**专门 API** 依然有用：

```python
>>> from collections import OrderedDict
>>> od = OrderedDict([("a", 1), ("b", 2), ("c", 3)])
>>> od.move_to_end("a")             # 把 a 移到末尾（LRU 缓存的核心操作！）
>>> od
OrderedDict([('b', 2), ('c', 3), ('a', 1)])
>>> od.popitem(last=False)          # 从头部弹出（FIFO 队列语义）
('b', 2)
```

> **版本注意**：3.7+ 后，**新代码用普通 `dict`**（保序是语言规范）；只有需要 `move_to_end`/`popitem(last=...)` 这类**位置操作**时才用 `OrderedDict`。`functools.lru_cache` 内部至今仍用 `OrderedDict`——因为它需要"最近使用项移到末尾"，这正是 `move_to_end` 的看家本领（见 13.4.2）。

### 13.2.3 deque：双端队列的 C 实现

`deque`（double-ended queue）是**双向链表**（block 数组链表）的 C 实现：两端增删都是 O(1)，但中间索引是 O(n)。

```python
>>> from collections import deque
>>> dq = deque([1, 2, 3])
>>> dq.append(4)            # 右端 O(1)
>>> dq.appendleft(0)        # 左端 O(1)
>>> dq
deque([0, 1, 2, 3, 4])
>>> dq.popleft()            # 左端弹出 O(1)
0
```

底层结构（`Modules/_collectionsmodule.c` 的 `dequeobject`）：由 `block` 组成的链表，每个 block 是一个固定大小的数组（默认 64 元素），`leftblock/rightblock` 指针 + 左右索引维护两端。**满则新开 block，空则回收**——这就是"两端 O(1)"的来源（对比 `list` 的头部插入要整体搬移 O(n)）。

```python
# 经典场景：有界滑动窗口
>>> from collections import deque
>>> history = deque(maxlen=3)      # 满 3 个自动丢最旧的
>>> for i in range(10):
...     history.append(i)
>>> history
deque([7, 8, 9], maxlen=3)         # 永远只保留最近 3 个
```

| 操作 | `list` | `deque` |
|------|--------|---------|
| 尾部 append/pop | O(1) | O(1) |
| **头部 insert/pop** | **O(n)**（整体搬移） | **O(1)** |
| 中间索引 `d[i]` | O(1) | O(n)（链表遍历） |
| 内存 | 连续数组（紧凑） | block 链表（有开销） |

> **⚠️ 陷阱**：`deque` 的随机访问是 O(n)——`dq[500_000]` 要从头遍历。如果你"主要随机访问 + 偶尔两端增删"，`list` 反而更好。`deque` 的正确用途是**队列/栈/滑动窗口**（两端口操作密集）。`threading` 的 `queue.Queue` 内部就是 `deque` + 锁（第 11 章展开）。

### 13.2.4 ChainMap 与 namedtuple

#### `ChainMap`：多个映射的"叠加视图"

```python
>>> from collections import ChainMap
>>> defaults = {"theme": "dark", "lang": "en"}
>>> user = {"lang": "zh"}
>>> merged = ChainMap(user, defaults)     # 前面的优先
>>> merged["lang"]                        # 命中 user
'zh'
>>> merged["theme"]                       # user 没有 → 落到 defaults
'dark'
```

查找语义：**从前到后**扫描各映射，第一个命中即返回。写入语义：**只写第一个映射**（`merged["x"] = 1` 只改 `user`，不改 `defaults`）。

```python
>>> merged["new_key"] = "v"               # 写进最前面的映射
>>> "new_key" in defaults
False
```

经典场景：**配置覆盖链**（命令行 > 用户配置 > 默认配置）。与"浅合并字典"（`{**user, **defaults}`）的区别：`ChainMap` 是**视图**，底层字典改动立即可见；浅合并是**快照**，改底层不会反映。

> **实战建议**：需要"多层配置、可叠加、可动态增删层"用 `ChainMap`；只需要"一次性合并快照"用 `dict` 解包。`ChainMap` 的 `new_child()` 还能优雅地实现"上下文压栈"（类似第 8 章 `contextlib` 的栈式管理）。

#### `namedtuple`：带名字的元组

```python
>>> from collections import namedtuple
>>> Point = namedtuple("Point", ["x", "y"])
>>> p = Point(1, 2)
>>> p.x, p.y                # 属性访问
(1, 2)
>>> p[0], p[1]              # 仍是元组，可索引
(1, 2)
>>> p._replace(x=10)        # 返回新实例（不可变）
Point(x=10, y=2)
>>> p._asdict()
{'x': 1, 'y': 2}
```

机制：`namedtuple` 用**元类**动态生成一个新类（第 12 章元编程的温和示例）——生成的类继承 `tuple`，把字段名编译进 `__slots__` 或属性描述符，同时生成 `_replace`/`_asdict`/`_make` 等工具方法。

> **⚠️ 陷阱**：
> - 字段名不能是关键字/以下划线开头（`_replace` 冲突），非法名在**创建时**抛 `ValueError`；
> - `namedtuple` 的默认值用 `defaults` 参数（3.7+）从**右侧**开始填充；
> - 需要**可变**的带名字结构？用 `dataclass`（第 7 章）——`namedtuple` 是"不可变 + 轻量"场景的正解，`dataclass` 是"可变 + 完整类型"场景的正解。

### 13.2.5 UserDict / UserList / UserString：何时真的需要

```python
>>> from collections import UserDict
>>> class MyDict(UserDict):       # 把 dict 当"成员"而非"父类"
...     def __setitem__(self, key, value):
...         super().__setitem__(key, str(value).upper())
>>> d = MyDict(a=1)
>>> d["a"]
'1'
```

`UserDict`/`UserList`/`UserString` 是"**以组合方式包装内置容器**"的基类。为什么不用直接继承 `dict`？

```python
# 直接继承 dict 的经典翻车：__setitem__ 与 update 不一致
class UpperDict(dict):
    def __setitem__(self, k, v):
        super().__setitem__(k, str(v).upper())

d = UpperDict()
d["a"] = 1                 # 走 __setitem__ → '1'
d.update(b=2)              # ⚠️ update 是 C 实现，绕过 __setitem__ → 2（小写！）
d["b"]                     # 2，不是 '2'
```

`dict` 的 `update`/`setdefault` 等方法是 **C 层直接操作**，不会回调 Python 的 `__setitem__`；`UserDict` 则把 `update` 等所有方法都**重新实现为调用 `self.data` 的 `__setitem__`**，保证子类重写处处生效。

> **🔑 机制洞察**：继承 C 实现的容器（`dict`/`list`/`str`）时，**重写的方法可能被内部 C 路径绕过**（`update`、`__init__`、`__getitem__` 链）。`UserDict` 的存在就是为了让你"安全地子类化"。规则：**只要你的子类要重写行为（不只是加方法），就用 `UserDict`/`UserList`/`UserString`**；只是加方法则直接继承内置容器即可。

### 13.2.6 三件低调的算法工具：bisect / heapq / array

大纲 13.1.1 的"数据与容器"象限里还有三个**算法型**模块——它们解决的是"容器 + 特定算法"的组合问题。

#### `bisect`：有序列表的二分查找

```python
>>> import bisect
>>> data = [1, 3, 5, 7, 9]
>>> bisect.bisect_left(data, 6)      # 插入点（保持有序）：6 应该插在索引 3（7 之前）
3
>>> bisect.bisect_right(data, 5)     # 5 的右侧插入点：索引 3
3
>>> bisect.insort(data, 6)           # 插入并保持有序
>>> data
[1, 3, 5, 6, 7, 9]
```

`bisect` 在**有序序列**上做二分查找——O(log n) 对比线性扫描的 O(n)：

```python
>>> import timeit, random, bisect
>>> data = sorted(random.sample(range(10**7), 10**6))
>>> timeit.timeit(lambda: 5_000_000 in data, number=100)      # 线性 in
0.35
>>> timeit.timeit(lambda: bisect.bisect_left(data, 5_000_000), number=100)
0.006           # 二分快约 60 倍
```

> **⚠️ 陷阱**：`bisect` **要求列表已有序**（升序）——无序列表上结果无意义。`bisect_left` 与 `bisect_right` 的区别在**重复元素**：前者返回第一个 ≥ x 的位置，后者返回第一个 > x 的位置（`left` 用于"找第一个"，`right` 用于"找插入到相同元素之后"）。判断存在性用 `i = bisect_left(...); i < len(data) and data[i] == x`。

#### `heapq`：堆（优先队列）

`heapq` 把**列表原地变成堆**（min-heap），实现优先队列：

```python
>>> import heapq
>>> heap = []
>>> heapq.heappush(heap, 5)
>>> heapq.heappush(heap, 1)
>>> heapq.heappush(heap, 3)
>>> heap                        # 堆序：heap[0] 永远最小
[1, 5, 3]
>>> heapq.heappop(heap)         # 弹出最小元素（O(log n)）
1
>>> heapq.nlargest(2, [3, 1, 4, 1, 5])    # 前 N 大（不排序整个列表）
[5, 4]
>>> heapq.nsmallest(3, [3, 1, 4, 1, 5])
[1, 1, 3]
```

机制：`heapq` 操作普通 `list`，内部维持**堆性质**（父 ≤ 子）——`heappush`/`heappop` 都是 O(log n)，`heap[0]` 恒为最小元素。`heapify(list)` 可在 O(n) 内把任意列表堆化。

```python
# 经典场景：Top-K 问题（100 万个数里最大的 100 个）
>>> data = random.sample(range(10**8), 10**6)
>>> heapq.nlargest(100, data)      # O(n log k)，远优于全排序 O(n log n)
# 任务调度：按优先级取任务
>>> tasks = []
>>> heapq.heappush(tasks, (3, "low"))      # (优先级, 任务)
>>> heapq.heappush(tasks, (1, "urgent"))
>>> heapq.heappush(tasks, (2, "normal"))
>>> heapq.heappop(tasks)
(1, 'urgent')                                # 永远先取优先级最小的
```

> **🔑 机制洞察**：`heapq` 是"**用数组实现树**"的经典数据结构——堆节点 `i` 的父节点是 `(i-1)//2`，子节点是 `2i+1`/`2i+2`，**完全不需要指针**。`lru_cache` 的淘汰、`Counter.most_common`（13.2.1 源码里见过 `heapq.nlargest`）、调度器全都依赖它。

#### `array`：紧凑的同质数组

```python
>>> from array import array
>>> arr = array("i", [1, 2, 3])     # 'i' = signed int（类型码）
>>> arr.append(4)
>>> arr[0] = 10
>>> arr.tobytes()                   # 直接导出内存字节
b'\n\x00\x00\x00\x02\x00\x00\x00...'
```

`array` 是**固定类型**的紧凑数组：`array('i', [1,2,3])` 每个元素 4 字节，而 `list` 的每个元素是**指向 Python 对象的指针（8 字节）+ 对象本身的开销**。

| 维度 | `list` | `array('d')` | `numpy.ndarray`（卷 2） |
|------|--------|-------------|------------------------|
| 元素类型 | 任意 | 单一（类型码） | 单一（dtype） |
| 内存 | 指针数组 + 对象 | 连续原始字节 | 连续原始字节 |
| 数值运算 | 无（要循环） | 无 | **向量化** |
| 适用 | 通用 | 大文件二进制缓冲（第 9 章 `struct` 配合） | 数值计算 |

> **实战建议**：`array` 的定位是"**二进制数据缓冲**"——与 `struct`/`memoryview`/`mmap`（第 9 章）配合做二进制协议、读大二进制文件。要**数值计算**（数学运算、广播）直接用卷 2 的 `numpy`——`array` 没有向量化，纯 Python 循环仍是瓶颈。

---

## 13.3 itertools：迭代器工具箱

第 5 章建立了迭代器协议（`__iter__`/`__next__`）与生成器心智，`itertools` 是把"迭代"这件事做到极致的模块：**全部惰性、全部组合、大部分有 C 加速**。它适合"把循环写成数据流"的声明式风格。

### 13.3.1 无限迭代器：count / cycle / repeat

```python
>>> from itertools import count, cycle, repeat, takewhile
>>> list(takewhile(lambda n: n < 5, count(1)))     # 无限计数 + 限界
[1, 2, 3, 4]
>>> list(takewhile(lambda c: c != "c", cycle("abc")))   # 无限循环
['a', 'b']
>>> list(repeat("x", 3))                           # 重复 n 次
['x', 'x', 'x']
```

`count` 的 `start`/`step` 支持浮点（`count(0, 0.5)`），但注意浮点累计误差（`count(0.1, 0.1)` 到 1.0 可能不精确）。`cycle` 无限复用可迭代对象（内部会缓存整个序列！）。

> **⚠️ 陷阱**：无限迭代器**必须**配 `takewhile`/`islice`/`break` 使用，否则程序永不结束。这是 `itertools` 与列表最大的心智差异——**列表是有限的，迭代器可能无限**。

### 13.3.2 组合与排列：product / permutations / combinations

这三个函数把组合数学（第 5 章练习里提过概念）直接变成一行：

```python
>>> from itertools import product, permutations, combinations, combinations_with_replacement
>>> list(product("AB", [1, 2]))                    # 笛卡尔积：|A|×|B| 个
[('A', 1), ('A', 2), ('B', 1), ('B', 2)]
>>> list(permutations("ABC", 2))                   # 排列：P(3,2)=6 个（有序、不重复取）
[('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B')]
>>> list(combinations("ABC", 2))                   # 组合：C(3,2)=3 个（无序）
[('A', 'B'), ('A', 'C'), ('B', 'C')]
>>> list(combinations_with_replacement("AB", 2))   # 有放回组合：C(2+2-1,2)=3 个
[('A', 'A'), ('A', 'B'), ('B', 'B')]
```

**数学定义速查**：

| 函数 | 计数公式 | 有序？ | 可重复取？ |
|------|---------|--------|-----------|
| `product(a, b)` | \|a\| × \|b\| | ✅ | ✅（跨集合） |
| `permutations(s, r)` | n!/(n−r)! | ✅ | ❌ |
| `combinations(s, r)` | n!/(r!(n−r)!) | ❌ | ❌ |
| `combinations_with_replacement(s, r)` | (n+r−1)!/(r!(n−1)!) | ❌ | ✅ |

```python
# 实战：三层嵌套循环 → 一行笛卡尔积
# ❌ 三层 for（缩进地狱 + 中间列表）
result = []
for a in xs:
    for b in ys:
        for c in zs:
            result.append(process(a, b, c))

# ✅ product：一个迭代器搞定
from itertools import product
result = [process(a, b, c) for a, b, c in product(xs, ys, zs)]
```

> **🔑 性能洞察**：`product` 等函数返回**惰性迭代器**——`product(xs, ys, zs)` 本身几乎零开销，元素按需生成。对比"先生成所有组合存列表"（内存 O(n³)），`product` 的内存是 O(1)。组合爆炸时这是唯一的活路。

### 13.3.3 分组与切片：groupby / islice / takewhile / dropwhile

```python
>>> from itertools import groupby
>>> data = [("a", 1), ("a", 2), ("b", 3), ("a", 4)]
>>> for key, group in groupby(data, key=lambda t: t[0]):
...     print(key, list(group))
a [('a', 1), ('a', 2)]     # 只对【相邻】的 a 分组！
b [('b', 3)]
a [('a', 4)]               # 第三个 a 因为不与前一个 a 相邻，成了新组
```

> **⚠️ 陷阱**：`groupby` **只对相邻的同键元素分组**——它基于"迭代顺序中键连续变化"的假设。要按键全局分组，必须先排序：`groupby(sorted(data, key=key), key=key)`。这个"必须先排序"是最常见的 `groupby` 误用。

```python
>>> from itertools import islice, takewhile, dropwhile
>>> list(islice(range(100), 10, 20))       # 等价 range(100)[10:20]，但惰性
[10, 11, ..., 19]
>>> list(takewhile(lambda x: x < 3, [1, 2, 3, 1]))   # 取"直到不满足"为止
[1, 2]
>>> list(dropwhile(lambda x: x < 3, [1, 2, 3, 1]))   # 丢弃"直到满足"为止
[3, 1]
```

`islice(it, start, stop)` 与切片 `it[start:stop]` 的关键差异：**列表切片是立即物化的新列表（O(n) 内存），`islice` 是惰性消费（O(1) 内存）**——对大文件/大流只能 `islice`。

### 13.3.4 优雅链式：chain / tee / zip_longest / accumulate

```python
>>> from itertools import chain, tee, zip_longest, accumulate
>>> list(chain([1, 2], [3], "ab"))          # 拼接多个可迭代对象
[1, 2, 3, 'a', 'b']
>>> list(accumulate([1, 2, 3, 4]))          # 前缀和（默认加法）
[1, 3, 6, 10]
>>> list(accumulate([1, 2, 3], max))        # 前缀最大值（任意二元函数）
[1, 2, 3]
>>> list(zip_longest("ab", [1, 2, 3], fillvalue="-"))   # 不等长 zip
[('a', 1), ('b', 2), ('-', 3)]
```

`tee(it, n)` 把**一个迭代器复制成 n 个独立迭代器**——机制是"每个 tee 副本共享一个内部缓存队列"：

```python
>>> it1, it2 = tee(range(5))
>>> list(it1), list(it2)      # 两个都能完整迭代
([0, 1, 2, 3, 4], [0, 1, 2, 3, 4])
```

> **⚠️ 陷阱**：`tee` 的代价是**缓存**——如果一个副本被完全消费而另一个还没开始，缓存要装下整个序列。`tee` 适用于"两个消费者进度接近"的场景；若两个消费者进度差异巨大，内存会爆炸，不如直接两次生成。

### 13.3.5 性能与心智模型：惰性 vs 物化

```python
# 对比：链式迭代 vs 中间列表（10^6 元素）
>>> import timeit
>>> data = range(1_000_000)
>>> def lazy():
...     from itertools import islice, chain
...     return sum(islice(chain(data, data), 100_000))
>>> def eager():
...     return sum(list(chain(list(data), list(data)))[:100_000])
>>> timeit.timeit(lazy, number=10)
0.11
>>> timeit.timeit(eager, number=10)
1.83            # 惰性快 ~16 倍 + 内存几乎为零
```

| 维度 | 惰性（itertools/生成器） | 物化（列表） |
|------|------------------------|-------------|
| 内存 | O(1)（流式） | O(n)（全量） |
| 速度 | 快（省去中间结构） | 慢（反复分配/拷贝） |
| 可读性 | 链式声明式 | 命令式循环 |
| 调试 | 难（看不到中间值） | 易（`list(...)` 即得） |

> **实战建议**：**管道式数据处理**（过滤 → 映射 → 取前 N）优先 `itertools` + 生成器表达式；数据量小且要反复使用，直接列表更简单。调试惰性链时，用 `list(itertools.islice(chain, 5))` 取前几个元素"快照"查看——不要 `list()` 整个无限迭代器。

---

## 13.4 functools：函数工具箱

第 6 章讲了函数是一等公民、闭包、装饰器，`functools` 把这些能力的**标准用法**沉淀成模块——"高阶函数的工具箱"。

### 13.4.1 partial 与 partialmethod

`functools.partial(func, *args, **kwargs)` 返回一个"**参数预填的函数**"：

```python
>>> from functools import partial
>>> def power(base, exp): return base ** exp
>>> square = partial(power, exp=2)
>>> square(5)
25
>>> square(5, exp=3)          # 调用时还能覆盖预填参数
125
```

机制：`partial` 对象内部存 `func`/`args`/`keywords` 三元组，`__call__` 时合并参数再调用——本质是**闭包的显式封装**（第 6 章）：

```python
# partial 等价的手写闭包
def square(base): return power(base, exp=2)
```

| 方式 | 特点 |
|------|------|
| `lambda x: power(x, 2)` | 每次创建新函数对象，repr 难读 |
| `functools.partial(power, exp=2)` | 可 picklable（部分情况）、repr 清晰、属性可查 |

```python
>>> square.func, square.keywords
(<function power at 0x...>, {'exp': 2})
```

经典用途：**回调参数预填**（GUI/事件回调传参）、**适配 API**（把"多参函数"变成"少参函数"喂给排序/映射等高阶函数）。`partialmethod` 是给类方法用的变体（把 `self` 之外的参数预填进方法）。

> **实战建议**：能用 `partial` 就别用 `lambda`——`partial` 的对象有 `func`/`args`/`keywords` 属性可调试、可序列化（`pickle` 支持部分情况），`lambda` 则是个黑盒。唯一例外：需要在调用时**求值默认参数**的场景（`lambda x: power(x, n)` 里 `n` 是调用时闭包变量）才用 `lambda`。

### 13.4.2 lru_cache 与 cache：记忆化的一行式

```python
>>> from functools import lru_cache
>>> @lru_cache(maxsize=128)
... def fib(n):
...     if n < 2: return n
...     return fib(n-1) + fib(n-2)
>>> fib(100)                        # 没有缓存会指数爆炸，这里秒回
354224848179261915075
>>> fib.cache_info()
CacheInfo(hits=98, misses=101, maxsize=128, currsize=101)
```

机制（`_lru_cache_wrapper`，`Modules/_functoolsmodule.c`）：**有序字典（`OrderedDict`）+ 双向链表**实现 LRU——命中则把键移到末尾（`move_to_end`，13.2.2 提到过！），容量满则淘汰头部的"最久未用"项。`maxsize=None` 时退化为**无限缓存**（`functools.cache`，3.9+，无 LRU 淘汰）。

```python
# 性能实测：递归斐波那契 n=35
# 无缓存：约 1.5 秒（指数级 2^35 次调用）
# lru_cache：微秒级（35 次调用）
```

**适用条件**：函数**纯**（相同参数 → 相同结果）、**无副作用**、参数**可哈希**。

> **⚠️ 陷阱**：
> 1. **可变参数不可哈希**：`@lru_cache` 函数不能接收 `list`/`dict` 参数（需转 `tuple`/`frozenset`）；
> 2. **缓存污染**：如果"同样的参数"在不同时间应返回不同结果（如读文件、查时间、依赖全局状态），缓存会返回**旧值**——这是最隐蔽的 bug；
> 3. **`typed=True`**（3.2+）区分 `1` 与 `1.0`（默认视为相同键）；
> 4. **内存**：`maxsize` 不设或太大，缓存会永久驻留（见第 10 章 `sys.modules` 的"永不淘汰"类比）；
> 5. `lru_cache` 装饰的函数不能被部分清缓存——用 `fib.cache_clear()` 全清，或升级到 3.9 的 `cache` 无淘汰版。

### 13.4.3 singledispatch：运行时多态的"注册表"形态

`singledispatch` 实现**泛型函数**（generic function）——根据**第一个参数的类型**分派到不同实现：

```python
>>> from functools import singledispatch
>>> @singledispatch
... def to_str(x):                       # 默认实现
...     return f"unknown: {type(x)}"
>>> @to_str.register(int)
... def _(x):
...     return f"int: {x}"
>>> @to_str.register(list)
... def _(x):
...     return f"list of {len(x)}"
>>> to_str(42)
'int: 42'
>>> to_str([1, 2])
'list of 2'
>>> to_str(3.14)
'unknown: <class 'float'>'      # 未注册类型 → 默认实现
```

机制：`singledispatch` 维护一个**类型 → 实现**的注册表（`registry` 字典），调用时按 `type(arg)` 查表，未命中则沿 MRO 找"最近的已注册父类型"：

```python
>>> to_str.registry
{<class 'object'>: <function to_str at ...>, <class 'int'>: <function _ at ...>, <class 'list'>: <function _ at ...>}
```

与第 7 章多态的对比：**继承多态**是"调用者不知道类型，由对象自己决定行为"；**singledispatch** 是"调用者知道类型，由注册表决定行为"——后者**不需要修改原类**就能扩展行为，特别适合"给第三方库的类型添加自己的处理"。

> **实战建议**：`singledispatch` 是"**开放-封闭原则**"的标准实现（新增类型 → 新增 `register`，不改动已有代码）。`singledispatchmethod`（3.8+）是类方法版本。注意：它只按**第一个**参数分派（所以叫 single）；多参数分派需要第三方库（如 `multipledispatch`）。

### 13.4.4 其他工具：reduce / cmp_to_key / wraps

```python
>>> from functools import reduce
>>> reduce(lambda a, b: a + b, [1, 2, 3, 4])      # 累计归约 = 10
10
>>> reduce(max, [3, 1, 4, 1, 5])                  # 归约成最大值
5
```

`reduce` 把"二元运算折叠整个序列"写成一行——但 Python 社区**慎用**它（Guido 本人曾想从内置函数移除 `reduce`，理由是"显式 `for` 循环更可读"）。可用 `sum`/`max`/`min` 的场景优先内置函数。

```python
>>> from functools import cmp_to_key
>>> # Python 3 移除 cmp 参数后，老式比较函数要用 cmp_to_key 适配
>>> sorted(["banana", "apple", "Cherry"], key=cmp_to_key(
...     lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower())))
['apple', 'banana', 'Cherry']
```

```python
>>> from functools import wraps
>>> def logged(func):
...     @wraps(func)                    # 复制 __name__/__doc__/__module__ 等元信息
...     def wrapper(*args, **kwargs):
...         print(f"calling {func.__name__}")
...         return func(*args, **kwargs)
...     return wrapper
>>> @logged
... def hello(): "says hello"; return "hi"
>>> hello.__name__                      # 没有 wraps 会是 'wrapper'
'hello'
```

> **🔑 机制洞察**：`wraps` 本质是 `update_wrapper(wrapper, func)`——把 `func` 的 `__name__`/`__doc__`/`__module__`/`__dict__` 拷到 `wrapper` 上。没有它，装饰后的函数会"丢失身份"（调试、`help()`、`pickle`、文档生成都会出错）。**写装饰器必加 `@wraps`**——这是第 6 章装饰器的规范补全，第 12 章元编程会从描述符层面再深挖。

---

## 13.5 时间与日期：datetime / zoneinfo

时间处理是**最容易出错**的标准库领域之一——错误通常不是立即崩溃，而是"夏令时差一小时""跨时区差一天"这类**静默错误**。本节把机制讲透，让错误无从发生。

### 13.5.1 datetime 对象模型

`datetime` 模块的核心是三个不可变类（全部 C 实现，`Modules/_datetimemodule.c`）：

```python
>>> from datetime import date, time, datetime
>>> date(2026, 8, 16)                  # 日期：年/月/日
datetime.date(2026, 8, 16)
>>> time(14, 30, 45)                   # 时间：时/分/秒/微秒
datetime.time(14, 30, 45)
>>> datetime(2026, 8, 16, 14, 30)      # 日期 + 时间（最常用）
datetime.datetime(2026, 8, 16, 14, 30)
```

C 层结构（`PyDateTime_DateTime`）把字段压缩打包：`date` 用 `fold` 位 + 天数；`time` 用位域存时分秒微秒；`datetime` 组合两者并附 `tzinfo` 指针。**不可变 + 可哈希**——所以 `datetime` 能当 dict 键、能进 `set`、能被 `lru_cache` 缓存。

```python
>>> d = date(2026, 8, 16)
>>> d.weekday()            # 周一=0 ... 周日=6
6
>>> d.isoformat()          # ISO 8601
'2026-08-16'
>>> d.toordinal()          # 儒略日序号（与 date.fromordinal 互逆）
740012
```

> **设计哲学**：`datetime` 类的不可变性不是偶然——时间值被到处传递、比较、哈希，**可变的时间对象会导致灾难性的共享状态 bug**（类似第 7 章字符串的不可变设计）。"改时间"只能产生新对象：`d.replace(day=1)`。

### 13.5.2 timedelta 与时间运算

`timedelta` 表示**时间差**，内部只存三个字段：`days`/`seconds`/`microseconds`，其余单位（周、时、分）在构造时**归一化**进去：

```python
>>> from datetime import timedelta
>>> td = timedelta(weeks=1, days=2, hours=3)
>>> td.days, td.seconds       # 7+2 天；3 小时 = 10800 秒
(9, 10800)
>>> td.total_seconds()        # 总秒数（浮点）
790200.0
>>> datetime(2026, 8, 16) + timedelta(days=10)   # 日期运算
datetime.datetime(2026, 8, 16, 0, 0) + 10 天 → 2026-08-26
```

`timedelta` 只精确到**微秒**（`microseconds` 字段）——`total_seconds()` 返回浮点会引入舍入误差（第 3 章浮点陷阱的又一现场）。纳秒级需求（如性能计时）用 `time.perf_counter_ns()` 返回整数纳秒。

> **⚠️ 陷阱**：`timedelta` 的归一化是**有符号的**——`timedelta(days=-1, seconds=1)` 是 `-1 天 + 1 秒 = -86399 秒`，`days=-1` 但 `seconds=86399`。涉及负数时 `days`/`seconds` 的绝对值关系反直觉，用 `total_seconds()` 判断正负更稳。

### 13.5.3 时区：timezone 与 zoneinfo（PEP 615）

#### naive vs aware：所有时区错误的根源

```python
>>> from datetime import datetime, timezone, timedelta
>>> naive = datetime(2026, 8, 16, 14, 30)        # 无时区信息
>>> naive.tzinfo is None
True
>>> aware = datetime(2026, 8, 16, 14, 30, tzinfo=timezone.utc)   # 带时区
>>> aware.tzinfo
datetime.timezone.utc
```

**naive（裸时间）与 aware（带时区）不能混比**——比较/相减会抛 `TypeError`：

```python
>>> naive - aware
Traceback (most recent call last):
  ...
TypeError: can't subtract offset-naive and offset-aware datetimes
```

#### `zoneinfo`（PEP 615，3.9+）：IANA 时区数据库

```python
>>> from zoneinfo import ZoneInfo
>>> sh = datetime(2026, 8, 16, 14, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
>>> sh.utcoffset()
datetime.timedelta(seconds=28800)      # UTC+8
>>> sh.astimezone(timezone.utc)        # 转换到 UTC
datetime.datetime(2026, 8, 16, 6, 30, tzinfo=datetime.timezone.utc)
```

`zoneinfo` 直接读取系统/打包的 **IANA 时区数据库**（`tzdata` 包提供），**自动处理 DST（夏令时）**——这是 `pytz` 时代最大的痛点：

```python
# ❌ pytz 反模式（老代码常见）：pytz 的 tzinfo 对象不能直接当 tzinfo 用
import pytz
dt = datetime(2026, 1, 1, tzinfo=pytz.timezone("Asia/Shanghai"))   # 错误！
dt = pytz.timezone("Asia/Shanghai").localize(datetime(2026, 1, 1)) # 必须 localize

# ✅ zoneinfo：tzinfo 就是正经 tzinfo，直接用
from zoneinfo import ZoneInfo
dt = datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
```

> **版本注意**：`zoneinfo` 是 Python 3.9+（PEP 615）。系统没有 IANA 数据库时（Windows 部分环境），装 `tzdata` 包即可。新代码**一律 `zoneinfo`，不要再引入 `pytz`**。

#### DST 的折叠与间隙

夏令时切换日有"两个 01:30"（秋季回拨，fold=0/1）或"没有 02:30"（春季前拨）：

```python
>>> from zoneinfo import ZoneInfo
>>> ny = ZoneInfo("America/New_York")
>>> dt = datetime(2026, 11, 1, 1, 30, tzinfo=ny)   # 秋季回拨日
>>> dt.fold                                     # fold=0：第一次 1:30
0
>>> dt.replace(fold=1)                          # fold=1：第二次 1:30（DST 后）
datetime.datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=ZoneInfo(key='America/New_York'))
```

> **⚠️ 陷阱**：**不要自己实现 DST 逻辑**（"UTC+8 就加 8 小时"在 UTC 无 DST 的时区成立，但在纽约/欧洲会错半年）。`zoneinfo` 已封装全部规则；你唯一要遵守的铁律是：**内部一律用 UTC（aware），展示时才转本地时区**。

### 13.5.4 解析与格式化

```python
>>> from datetime import datetime
>>> # 格式化：strftime（datetime → str）
>>> datetime(2026, 8, 16, 14, 30).strftime("%Y-%m-%d %H:%M:%S")
'2026-08-16 14:30:00'
>>> # 解析：strptime（str → datetime）
>>> datetime.strptime("2026-08-16 14:30:00", "%Y-%m-%d %H:%M:%S")
datetime.datetime(2026, 8, 16, 14, 30)
```

| 格式码 | 含义 | 示例 |
|--------|------|------|
| `%Y` / `%y` | 四位 / 两位年 | `2026` / `26` |
| `%m` / `%d` | 零填充月 / 日 | `08` / `16` |
| `%H` / `%M` / `%S` | 时 / 分 / 秒 | `14` / `30` / `00` |
| `%z` / `%Z` | UTC 偏移 / 时区名 | `+0800` / `CST` |
| `%A` / `%a` | 星期全名 / 缩写 | `Sunday` / `Sun` |
| `%B` / `%b` | 月全名 / 缩写 | `August` / `Aug` |
| `%f` | 微秒 | `000000` |

```python
# 性能对比：strptime vs fromisoformat（10^5 次）
>>> import timeit
>>> s = "2026-08-16T14:30:00"
>>> timeit.timeit(lambda: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S"), number=100_000)
0.38
>>> timeit.timeit(lambda: datetime.fromisoformat(s), number=100_000)
0.11        # fromisoformat 快 ~3.5 倍（专用 C 解析路径）
```

> **实战建议**：能交换 ISO 8601 格式（`2026-08-16T14:30:00`）就**只用 ISO**——`fromisoformat` 快、且 `isoformat()` 是标准交换格式（JSON API、数据库、跨语言）。`strptime` 留给非标准格式（日志、用户输入）。3.11+ 的 `fromisoformat` 支持更多格式（含时区后缀）。

### 13.5.5 工程陷阱清单

1. **`date.today()` 用本地时区**：`date.today()` 等价 `datetime.now().date()`——服务器时区不是 UTC 时，与 UTC 日期比对会差一天。规则：**跨机器/跨时区一律 `datetime.now(timezone.utc)`**。
2. **aware 一致性**：同一逻辑里要么全 naive（且明确是 UTC），要么全 aware——混用必出 `TypeError` 或静默错值。
3. **`timestamp()` 的往返**：`datetime(2026,8,16, tzinfo=timezone.utc).timestamp()` 返回 POSIX 秒；naive datetime 的 `timestamp()` 会**假设本地时区**——同样的 `datetime` 对象在不同时区的机器上 `timestamp()` 不同。
4. **性能**：`datetime` 对象创建是 C 级，快；但 `strptime`/`strftime` 按格式解析较慢——高频路径缓存格式化结果。
5. **`timedelta` 精度**：微秒级；需要纳秒计时用 `time.perf_counter_ns()`（第 15 章性能基准的标准工具）。

#### 补充：calendar —— 日历的"查询即用"

`calendar` 模块是"日历计算"的现成工具箱（农历之外的公历）：

```python
>>> import calendar
>>> calendar.isleap(2024)            # 闰年判断
True
>>> calendar.weekday(2026, 8, 16)    # 星期几（周一=0）
6
>>> calendar.monthrange(2026, 2)     # (该月第一天是周几, 该月天数)
(6, 28)                              # 2026-02-01 是周日，2 月 28 天
>>> calendar.month(2026, 8)          # 文本日历
'    August 2026\nMo Tu We Th Fr Sa Su\n...'
```

实用场景：`monthrange` 做"当月的天数/第一天星期"计算（排班、报表按月分页）；`TextCalendar`/`HTMLCalendar` 生成日历视图。**注意**：`calendar.weekday` 的星期约定是**周一=0**，与 `date.weekday()` 一致（周日常见的"周日=0"约定在 ISO 体系里不同，见 `date.isoweekday()` 周日=7）。

---

## 13.6 数字与随机：math / decimal / random / statistics

第 3 章讲过 `int`/`float` 的表示与浮点精度问题，本节是"数字的工程工具箱"——**在浮点不够精确、随机不安全、统计要可靠**时怎么选。

### 13.6.1 math 与 cmath：C 库函数的薄包装

`math` 是 C 标准库 `<math.h>` 的 Python 包装，**纯计算、无状态**：

```python
>>> import math
>>> math.sqrt(2), math.log(100, 10), math.exp(1)
(1.4142135623730951, 2.0, 2.718281828459045)
>>> math.floor(3.7), math.ceil(3.2), math.trunc(-3.7)
(3, 4, -3)
>>> math.gcd(12, 18), math.lcm(4, 6)          # 3.9+ 有 lcm
(6, 12)
>>> math.comb(5, 2), math.perm(5, 2)          # 组合数/排列数（13.3.2 的公式实现）
(10, 20)
```

**浮点比较的正确姿势**（第 3 章陷阱的标准解药）：

```python
>>> 0.1 + 0.2 == 0.3
False
>>> math.isclose(0.1 + 0.2, 0.3)              # 相对容差比较
True
>>> math.isclose(1e10 + 1, 1e10, rel_tol=1e-9)  # 相对容差 1e-9 时"相等"
True
>>> math.isfinite(1e308 * 10)                 # 溢出检测（∞ 不是错误，是值）
False
```

`cmath` 是复数版（`cmath.sqrt(-1)` → `1j`）。`math` 的 C 包装意味着**快**（无 Python 层循环），但**慢路径**（如 `math.sin` 的高精度实现）仍受 C 库精度影响——`math` 保证"结果正确舍入到 1 ulp 内"级别的精度承诺。

> **实战建议**：判断"两个浮点是否相等"永远用 `math.isclose`（指定 `rel_tol`）；判断"数字是否异常"用 `isfinite` 而非 `== float('inf')`（`nan` 与任何值都不相等，`x == x` 对 `nan` 是 False）。

### 13.6.2 decimal：十进制浮点的定点语义

#### 为什么货币计算必须用 decimal

```python
>>> 0.1 + 0.2
0.30000000000000004          # 二进制浮点无法精确表示 0.1
>>> from decimal import Decimal
>>> Decimal("0.1") + Decimal("0.2")
Decimal('0.3')               # 十进制精确
```

`float` 是**二进制**浮点（`0.1` 是无限循环二进制小数）；`Decimal` 是**十进制**浮点——对"人类十进制记账"（货币、税率、百分比）精确。**财务/金额计算必须用 `Decimal`**，这是行业铁律。

```python
>>> Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
True
>>> # ⚠️ 从字符串构造！从 float 构造会继承二进制误差
>>> Decimal(0.1)              # ❌ 这不是"精确的 0.1"
Decimal('0.1000000000000000055511151231257827021181583404541015625')
>>> Decimal("0.1")            # ✅ 精确
Decimal('0.1')
```

#### 上下文：精度与舍入

```python
>>> from decimal import getcontext
>>> getcontext().prec = 28                    # 默认 28 位有效数字
>>> getcontext().rounding                     # 默认 ROUND_HALF_EVEN（银行家舍入）
'ROUND_HALF_EVEN'
>>> Decimal("1") / Decimal("3")
Decimal('0.3333333333333333333333333333')     # 28 位
>>> getcontext().prec = 4
>>> Decimal("1") / Decimal("3")
Decimal('0.3333')
```

`getcontext()` 是**线程局部**的（`threading.local` 实现）——每个线程有自己的精度上下文。`localcontext()` 上下文管理器可以临时改精度（第 8 章的 `with` 协议又一实例）。

> **⚠️ 陷阱**：
> - **性能**：`Decimal` 是纯 Python 实现（`_decimal` 的 C 版本 3.3+ 是加速版），比 `float` 慢 **10–100 倍**——只用于"必须精确"的值，不要给性能热路径用；
> - **上下文敏感**：同样表达式在不同 `prec` 下结果不同——**不要全局改 `getcontext().prec`**，用 `localcontext()` 局部改；
> - **与 float 混算**：`Decimal("0.1") + 0.2` 抛 `TypeError`（不允许隐式混算），需显式 `Decimal("0.2")`；
> - `ROUND_HALF_EVEN`（银行家舍入）与直觉的"四舍五入"（`ROUND_HALF_UP`）不同：`Decimal("0.5").quantize(Decimal("1"))` 得 `0`（偶数），`0.5` 四舍五入直觉是 `1`。财务系统要确认舍入模式。

### 13.6.3 fractions：精确有理数

```python
>>> from fractions import Fraction
>>> Fraction(1, 3) + Fraction(1, 6)
Fraction(1, 2)               # 精确的 1/2，不是 0.5 的浮点近似
>>> Fraction("0.25")
Fraction(1, 4)
>>> Fraction(0.1)            # ⚠️ 从 float 构造得到的是"0.1 的精确二进制值"
Fraction(3602879701896397, 36028797018963968)
```

`Fraction` 内部存 `(numerator, denominator)` 且**自动约分**。适用：需要精确有理运算的数学/科学场景（概率论、线性代数推导）。与 `Decimal` 的取舍：`Fraction` 是"精确的有理数"，`Decimal` 是"精确的十进制数"——前者适合数学推导，后者适合记账。

> **实战建议**：概率/组合计算（如 `Fraction(1, 6) ** 2`）用 `Fraction` 避免浮点误差累积；结果需要浮点时再 `float(fr)`。`Fraction` 也能当 dict 键（可哈希、不可变）。

### 13.6.4 random：种子、分布与安全性

```python
>>> import random
>>> random.seed(42)              # 固定种子 → 可复现
>>> random.random()              # [0, 1) 均匀分布
0.6394267984578837
>>> random.randint(1, 6)         # [1, 6] 整数
2
>>> random.choice(["a", "b", "c"])
'b'
>>> random.sample(range(100), 5) # 不重复抽样
[81, 14, 3, 94, 35]
>>> random.shuffle(["a", "b", "c"])  # 原地洗牌
```

机制：`random` 默认用 **Mersenne Twister**（梅森旋转）——一个伪随机数生成器（PRNG）：**给定种子，序列完全确定**。`seed(42)` 让实验可复现（科学计算、测试的黄金习惯）。

**分布**：`random.gauss(mu, sigma)`（正态）、`random.expovariate(lambd)`（指数）、`random.betavariate` 等——内部用 Box-Muller 等算法从均匀分布变换而来。

> **⚠️ 安全红线**：`random` 是**伪随机**，**绝不能用于密码学**（token、密码、密钥、验证码）——Mersenne Twister 的 624 个输出即可预测整个序列。安全随机用 `secrets`：

```python
>>> import secrets
>>> secrets.token_hex(16)          # 加密安全随机 token
'3f2a8c...'
>>> secrets.choice(["a", "b"])     # 安全选择（如密码重置码）
```

| 场景 | 模块 | 原因 |
|------|------|------|
| 测试/模拟/游戏 | `random` | 可复现（seed） |
| 抽样统计 | `random.sample` | 伪随机足够 |
| **token/密码/密钥** | **`secrets`** | 加密安全（`os.urandom` 后端） |
| 数值实验 | `numpy.random`（卷 2） | 批量 + 可复现 |

### 13.6.5 statistics：均值/方差/中位数

```python
>>> import statistics
>>> statistics.mean([1, 2, 3, 4, 5])
3
>>> statistics.median([1, 2, 3, 4, 100])     # 中位数抗离群值
3
>>> statistics.stdev([1, 2, 3, 4, 5])        # 样本标准差（n-1 分母）
1.5811388300841898
>>> statistics.pstdev([1, 2, 3, 4, 5])       # 总体标准差（n 分母）
1.4142135623730951
```

> **⚠️ 陷阱**：
> - `mean` 对超大数求和可能溢出/精度损失——3.8+ 的 **`fmean`** 用 `math.fsum` 做**精确累加**（Neumaier 算法），大数据集用 `fmean`；
> - `stdev`（样本）与 `pstdev`（总体）分母不同（n−1 vs n）——**别混用**，样本推断用 `stdev`；
> - 空输入抛 `StatisticsError`（不是 `ValueError`）——异常类型要接对；
> - 数据量级差异大时，`statistics` 的简单实现可能精度不足——正式统计用卷 2 的 `numpy`/`scipy.stats`。

---

## 13.7 系统与进程：subprocess / shutil / glob / platform

第 9 章讲了"文件字节流"的底层 IO，本节是**系统层的高阶工具**：调外部程序、批量文件操作、路径通配、平台识别。

### 13.7.1 subprocess：进程管理的正确姿势

调外部命令是 Python 工程的高频需求（git、ffmpeg、系统工具），`subprocess` 是唯一正解（`os.system` 早已是反模式）。

```python
>>> import subprocess
>>> # 高阶 API：run() 一步到位
>>> result = subprocess.run(
...     ["git", "status", "--short"],      # ✅ 参数列表，不用 shell 拼接
...     capture_output=True,               # 捕获 stdout/stderr
...     text=True,                         # 解码为文本（3.7+）
...     timeout=10,                        # 超时保护
... )
>>> result.returncode
0
>>> result.stdout
' M python-core/chapter-13-stdlib.md\n'
```

```python
# 失败即报错：check=True
>>> subprocess.run(["false"], check=True)
Traceback (most recent call last):
  ...
subprocess.CalledProcessError: Command '['false']' returned non-zero exit status 1.

# 需要交互/流式：Popen（底层 API）
>>> proc = subprocess.Popen(
...     ["python", "-c", "import sys; print(sys.version)"],
...     stdout=subprocess.PIPE, text=True,
... )
>>> out, err = proc.communicate(timeout=5)   # 等待并读取
```

#### ⚠️ shell=True：注入漏洞的根源

```python
# ❌ 危险：shell 拼接字符串 = 命令注入
import subprocess
user_input = "1; rm -rf /"          # 恶意输入
subprocess.run(f"echo {user_input}", shell=True)   # 执行了 rm -rf /！
# ✅ 安全：参数列表 + shell=False（默认）
subprocess.run(["echo", user_input])               # 当作参数，不解析
```

`shell=True` 会把命令交给系统 shell 解析——**任何未转义的用户输入都可能变成新命令**（`;`、`&&`、`|`、反引号、`$()`）。铁律：

1. **默认 `shell=False`**（`run` 的默认），传**参数列表**；
2. 需要管道/重定向等 shell 特性时，用 Python 侧实现（`stdout=PIPE` 链式）而非 shell 语法；
3. 真的必须 `shell=True`（如调用 shell 内建），**绝不拼接用户输入**。

```python
# ✅ 用 Python 实现"管道"：cmd1 | cmd2
p1 = subprocess.Popen(["dir"], stdout=subprocess.PIPE, text=True)
p2 = subprocess.Popen(["findstr", "py"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
p1.stdout.close()                    # 关键：关闭父进程的管道副本，避免死锁
out, _ = p2.communicate()
```

> **⚠️ 陷阱**：
> - 子进程**继承环境变量**——敏感信息（密钥）别放环境变量传给不可信子进程；
> - `capture_output=True` 时 stdout/stderr 是**内存缓冲**——子进程输出巨大（>64KB 管道缓冲）可能死锁，此时用 `Popen` + `communicate` 或写文件；
> - `timeout` 超时后 `run` 抛 `TimeoutExpired`，但**子进程可能还在运行**（`kill` 由你负责，`Popen` 场景用 `proc.kill()`）。

### 13.7.2 shutil：高层文件操作

第 9 章的 `open()`/`pathlib` 解决"单个文件的读写"，`shutil` 解决"**文件集合的操作**"：复制、移动、删除目录树、归档。

```python
>>> import shutil
>>> shutil.copy("a.txt", "b.txt")          # 复制内容（不保留元数据）
'b.txt'
>>> shutil.copy2("a.txt", "c.txt")         # 复制内容 + 元数据（时间戳等）
'c.txt'
>>> shutil.move("c.txt", "sub/")           # 移动（跨文件系统也能用）
'sub/c.txt'
>>> shutil.rmtree("old_dir")               # 递归删除目录（⚠️ 不可恢复）
>>> shutil.copytree("src", "dst")          # 递归复制目录
>>> shutil.disk_usage("C:\\")              # 磁盘用量
usage(total=..., used=..., free=...)
>>> shutil.make_archive("backup", "zip", "mydir")   # 打包为 zip/tar
'backup.zip'
```

| 函数 | 保留内容 | 保留元数据 | 备注 |
|------|---------|-----------|------|
| `copy` | ✅ | ❌ | 内容复制 |
| `copy2` | ✅ | ✅ | 尽可能保留元数据 |
| `copytree` | ✅ | 可选（`copy_function` 参数） | 目录递归 |
| `move` | ✅ | ✅ | 同文件系统是 `rename`，跨系统是复制+删 |

> **⚠️ 陷阱**：
> - `shutil.copy` vs `copy2`：**默认 `copyfile` 不保留时间戳**——备份场景要用 `copy2`；
> - `rmtree` 对**只读文件**在 Windows 上会失败（3.8+ 有 `onexc` 回调处理）——删不掉时检查文件属性；
> - `copytree` 默认**目标不存在才复制**，`dirs_exist_ok=True`（3.8+）允许合并到已有目录；
> - `make_archive` 的根目录行为：`root_dir`/`base_dir` 参数控制归档内路径结构，细节见文档——"打包出来多一层目录"是经典困惑。

### 13.7.3 glob 与 fnmatch：文件通配

```python
>>> import glob
>>> glob.glob("python-core/*.md")          # 单层通配
['python-core/chapter-01-environment-setup.md', ...]
>>> glob.glob("**/*.md", recursive=True)   # 递归（** 需要 recursive=True）
['README.md', 'python-core/chapter-01-...md', ...]
>>> glob.iglob("*.py")                     # 惰性版本（大目录省内存）
```

`glob` 的通配语法（`*`/`?`/`[...]`）与正则**不是一回事**——它是"文件路径通配"，比正则简单，也别混用：

| 语法 | glob（路径通配） | 正则（re） |
|------|-----------------|-----------|
| 任意字符 | `*` | `.*` |
| 单字符 | `?` | `.` |
| 字符集 | `[abc]` | `[abc]` |
| 任意数量（含 0） | `*` | `*` |

`fnmatch` 提供单名字匹配（`fnmatch.fnmatch("a.py", "*.py")`）；`pathlib` 的 `Path.glob()`（第 9 章讲过）是面向对象版本，**优先用它**。

> **实战建议**：现代代码用 `pathlib.Path.glob()`（返回 `Path` 对象，天然跨平台）；`glob` 模块适合"只要字符串路径"或需要 `recursive` 深层扫描的场景。注意 `glob` 不排序（`sorted()` 包一层）。

### 13.7.4 platform 与 os 信息：跨平台判断的正确姿势

"检测操作系统"有三个 API，**含义完全不同**：

```python
>>> import platform, sys, os
>>> platform.system()       # 人类可读：'Windows' / 'Linux' / 'Darwin'
'Windows'
>>> sys.platform            # 技术标识：'win32' / 'linux' / 'darwin'
'win32'
>>> os.name                 # 最粗粒度：'nt' / 'posix'
'nt'
```

| API | 值示例 | 粒度 | 用途 |
|-----|--------|------|------|
| `platform.system()` | `Windows`/`Linux` | 展示/日志 | 报告给用户看 |
| `sys.platform` | `win32`/`linux`/`darwin` | 技术判断 | **代码分支的首选** |
| `os.name` | `nt`/`posix` | 家族级 | 判断 POSIX 语义（路径、信号） |

```python
# ✅ 正确的跨平台分支
if sys.platform == "win32":
    exe = "where"
elif sys.platform == "darwin":       # macOS
    exe = "which"
else:                                # linux 等
    exe = "which"

# ❌ 反模式：用 platform.system() 做代码分支（值不稳定，且大小写混乱）
```

> **⚠️ 陷阱**：`sys.platform` 是**技术标识**（分支用它），`platform.system()` 是**展示名**（日志/UI 用它）——别反着用。更精细的信息：`platform.machine()`（CPU 架构，wheel 标签里见过）、`platform.python_version()`、`sys.maxsize`（判断 32/64 位）。路径处理永远用 `pathlib`（第 9 章），不要手写 `os.sep` 拼接。

---

## 13.8 数据持久化与配置：sqlite3 / csv / configparser / argparse

第 9 章的 `json`/`pickle` 解决"对象 → 字节"，本节解决"**数据怎么存、参数怎么进**"——数据库、表格文件、配置文件、命令行参数。

### 13.8.1 sqlite3：嵌入式数据库

`sqlite3` 是 Python 内置的**嵌入式 SQL 数据库**（C 库，零配置、单文件）——不需要数据库服务器，一个 `.db` 文件即数据库。它是"中小规模结构化数据的默认答案"。

```python
>>> import sqlite3
>>> conn = sqlite3.connect("app.db")          # 不存在则创建
>>> cur = conn.execute("""
...     CREATE TABLE IF NOT EXISTS users (
...         id INTEGER PRIMARY KEY,
...         name TEXT NOT NULL,
...         age INTEGER
...     )
... """)
>>> conn.execute("INSERT INTO users (name, age) VALUES (?, ?)", ("Alice", 30))
>>> conn.commit()                             # 事务提交（见下）
>>> rows = conn.execute("SELECT * FROM users WHERE age > ?", (25,)).fetchall()
>>> rows
[(1, 'Alice', 30)]
```

#### 参数化查询：防注入的唯一正确姿势

```python
# ❌ 字符串拼接 = SQL 注入
name = "'; DROP TABLE users; --"
conn.execute(f"SELECT * FROM users WHERE name = '{name}'")   # 灾难

# ✅ 参数化：? 占位符，值由驱动转义
conn.execute("SELECT * FROM users WHERE name = ?", (name,))
```

**SQL 注入是 web 安全第一大漏洞**（OWASP Top 10 常年榜首）——`sqlite3` 的 `?` 占位符把值交给 C 库安全绑定，**永远不要用 `f-string`/`%` 拼 SQL**。

#### 事务语义

```python
>>> conn = sqlite3.connect("app.db")
>>> conn.isolation_level        # 默认 ''（开启隐式事务）
''
>>> # 默认行为：DML 语句自动开启事务，commit/rollback 结束
>>> conn.execute("INSERT ...")
>>> conn.commit()               # 提交
# 或者
>>> conn.rollback()             # 回滚
```

```python
# 推荐：with 块管理事务（3.12+ 真正支持）
with sqlite3.connect("app.db") as conn:      # 3.12 前：with 只管理连接关闭，不自动提交！
    conn.execute("INSERT INTO users ...")    # 成功自动 commit，异常自动 rollback
```

> **版本注意**：3.12 之前 `with sqlite3.connect(...)` **只负责关闭连接，不自动提交事务**——旧代码里 `with` 块内必须手动 `commit()`，否则数据丢失（这是 sqlite3 经典大坑）。3.12+ 的 `with` 才真正按事务语义工作。

> **⚠️ 陷阱**：
> - **线程**：默认同一连接跨线程共享需 `check_same_thread=False`（有风险）——多线程用**每线程一个连接**；
> - `executemany` 批量插入比循环 `execute` 快一个量级（C 层批量绑定）；
> - `row_factory = sqlite3.Row` 让行支持**列名访问**（`row["name"]`）——比默认元组好用；
> - 并发写冲突抛 `sqlite3.OperationalError: database is locked`——写多读多的场景该考虑服务器数据库（PostgreSQL 等）。

### 13.8.2 csv：读写与方言

```python
>>> import csv
>>> with open("data.csv", "w", newline="", encoding="utf-8") as f:   # ⚠️ newline='' 铁律
...     writer = csv.writer(f)
...     writer.writerow(["name", "age"])
...     writer.writerow(["Alice", 30])
>>> with open("data.csv", newline="", encoding="utf-8") as f:
...     for row in csv.reader(f):
...         print(row)
['name', 'age']
['Alice', '30']              # ⚠️ 全是字符串，需自行转换类型
```

> **⚠️ 陷阱**：
> 1. **`newline=''` 是铁律**（官方文档明确要求）：否则 Windows 上会写出 `\r\r\n` 双换行（CSV 规范本身用 `\r\n`，`newline=''` 让 Python 不做额外转换）；
> 2. **CSV 无类型**：读出来全是 `str`——数值要自己 `int(row[1])`；
> 3. 编码：**必须显式 `encoding=`**（第 9 章 PEP 686 之后默认 UTF-8，老文件可能是 GBK）——用 `utf-8-sig` 兼容带 BOM 的 Excel 导出文件；
> 4. 复杂 CSV（嵌套引号、换行字段）用 `csv.DictReader`/`DictWriter` 或第三方 `pandas`（卷 2）；脏数据（多表头、非标准转义）直接上 `pandas`。

### 13.8.3 configparser：INI 配置

```python
# config.ini
[DEFAULT]                        # DEFAULT 段对所有段可见（继承语义）
debug = false

[database]
host = localhost
port = 5432

[logging]
level = INFO
```

```python
>>> import configparser
>>> cfg = configparser.ConfigParser()
>>> cfg.read("config.ini", encoding="utf-8")
>>> cfg["database"]["host"]          # 段 + 键
'localhost'
>>> cfg.getint("database", "port")   # 类型转换
5432
>>> cfg.getboolean("DEFAULT", "debug")   # 布尔解析（true/false/yes/no/on/off/1/0）
False
>>> cfg["database"]["debug"]         # DEFAULT 的值对子段可见
'false'
```

机制要点：

- **`DEFAULT` 段的继承**：`DEFAULT` 里的键对所有段可见（`cfg["database"]["debug"]` 能读到）；
- **插值**：默认开启 `%(key)s` 引用——`host = %(base_host)s` 会展开，**配置里含字面 `%` 需写 `%%`**（3.5+ 可用 `ConfigParser(interpolation=None)` 关闭）；
- **大小写**：默认**保留大小写**，但键查找大小写不敏感（`cfg["DATABASE"]` 也行）；
- 写回：`cfg.set(...)` + `with open("config.ini","w") as f: cfg.write(f)`。

> **实战建议**：INI 适合"人类手写、层级浅"的配置；复杂配置（嵌套、列表、环境变量替换）用 `tomllib`（3.11+，读取 TOML）+ `pyproject.toml` 或 `dotenv`。**不要用 JSON 当配置文件**（无注释、难手写）——这是常见反模式。

#### 补充：tomllib —— 现代配置格式的读取器（3.11+）

`tomllib`（PEP 680，3.11+）是 TOML 配置的**只读**解析器——`pyproject.toml`（第 10 章）的标准读取方式：

```python
>>> import tomllib
>>> with open("config.toml", "rb") as f:          # ⚠️ 必须以二进制模式打开
...     cfg = tomllib.load(f)
>>> cfg["database"]["host"]
'localhost'
>>> tomllib.loads('title = "demo"')               # 从字符串解析
{'title': 'demo'}
```

```toml
# config.toml —— 比 INI 表达力强：嵌套、数组、类型
[database]
host = "localhost"
port = 5432                  # 真实类型（INI 全是字符串）
timeouts = [1, 2, 3]         # 数组

[logging.level]              # 嵌套表
app = "INFO"
```

对比 `configparser`：TOML **自带类型**（数字/布尔/数组/嵌套表），无需 `getint`/`getboolean` 转换；格式规范（`pyproject.toml` 同款）。注意 `tomllib` **只读**——要写 TOML 用第三方 `tomli_w`/`tomlkit`。

> **版本注意**：`tomllib` 是 3.11+（PEP 680）；3.10 及更早用第三方 `tomli`（API 一致，`pip install tomli`）。新项目的"人类可读配置"首选 TOML + `tomllib`，INI 留给遗留系统。

### 13.8.4 argparse：命令行参数解析实战

```python
>>> import argparse
>>> parser = argparse.ArgumentParser(prog="mytool", description="Demo CLI")
>>> parser.add_argument("input", help="输入文件")            # 位置参数（必填）
>>> parser.add_argument("-o", "--output", default="out.txt")  # 可选参数
>>> parser.add_argument("-v", "--verbose", action="store_true")  # 布尔开关
>>> parser.add_argument("--limit", type=int, default=10)     # 类型转换
>>> args = parser.parse_args(["--limit", "5", "data.csv"])   # 测试时传 argv
>>> args.input, args.output, args.verbose, args.limit
('data.csv', 'out.txt', False, 5)
```

| 参数形态 | 写法 | 语义 |
|---------|------|------|
| 位置参数 | `parser.add_argument("input")` | 按顺序必填 |
| 可选参数 | `-o` / `--output` | 带值选项 |
| 布尔开关 | `action="store_true"` | 出现即 True |
| 类型转换 | `type=int` | 自动转换（非法值报错） |
| 多值 | `nargs="+"` | 收集为列表 |
| 选择 | `choices=["a","b"]` | 限定取值 |
| 子命令 | `add_subparsers()` | `git commit` / `git push` 式 |

```python
# 子命令：git 风格工具
parser = argparse.ArgumentParser(prog="tool")
sub = parser.add_subparsers(dest="command", required=True)
run_p = sub.add_parser("run")
run_p.add_argument("--config")
build_p = sub.add_parser("build")
build_p.add_argument("--clean", action="store_true")

args = parser.parse_args(["run", "--config", "dev.toml"])
>>> args.command, args.config
('run', 'dev.toml')
```

> **实战模式**：与第 10 章 10.8.3 的完整组合——`argparse` 解析 + `[project.scripts]` 入口点 + `__main__.py` 转发，就是现代 Python CLI 工具的标准骨架。`argparse` 自动生成 `--help`/`--version`（`action="version"`）与错误信息，零样板。需要更现代/更花哨的 CLI（颜色、进度条、补全）再看第三方 `click`/`typer`——但 `argparse` 零依赖，多数场景够用。

---

## 13.9 logging：日志系统

日志是生产系统的**眼睛**——`print` 在脚本里够用，在服务里是灾难（无级别、无时间戳、无法配置输出位置）。`logging` 是标准库的完整日志框架，理解它的四件套架构后，配置只是拼积木。

### 13.9.1 四件套架构：Logger / Handler / Formatter / Filter

```python
import logging

# 1. Logger：日志入口（你代码里用的）
logger = logging.getLogger("myapp")          # 名字即层级（见 13.9.2）
logger.info("starting up")

# 2. Handler：日志去哪（控制台/文件/网络...）
handler = logging.StreamHandler()            # 输出到 stderr

# 3. Formatter：日志长什么样
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)

# 4. Filter：要不要记（按条件过滤）
class SensitiveFilter(logging.Filter):
    def filter(self, record):
        return "password" not in record.getMessage()

# 组装
logger.addHandler(handler)
logger.addFilter(SensitiveFilter())
logger.setLevel(logging.INFO)
```

**记录流程**（一条日志的旅程）：

```
logger.debug/info/warning/error(...)
  → 检查级别：record.levelno >= logger 有效级别？ 否 → 丢弃
  → 创建 LogRecord（时间、文件名、行号、消息...）
  → 传给本 logger 的 Handlers
  → 若 propagate=True（默认）→ 传给父 logger 的 Handlers（递归到 root）
  → 每个 Handler 检查自己的级别 → Formatter 格式化 → 输出
```

> **🔑 机制洞察**：`LogRecord` 的 `%(filename)s`/`%(lineno)d` 来自**栈回溯**（`sys._getframe`）——日志语句**调用点**的信息，不是 logger 定义处。所以日志慢的根源之一是"每次都要爬栈"；高频日志（每秒上万条）用 `logger.isEnabledFor(level)` 预检查，或直接让 `if logger.isEnabledFor(logging.DEBUG): logger.debug(...)` 短路。

### 13.9.2 层级与传播

```python
>>> logging.getLogger("myapp") is logging.getLogger("myapp")     # 同名同对象
True
>>> logging.getLogger("myapp.database")
<Logger myapp.database (WARNING)>
```

**`getLogger` 是单例注册表**（与第 10 章 `sys.modules`、13.2 的注册表模式同构）：名字用点分层级 `myapp.database`，与**模块名天然对应**——`logging.getLogger(__name__)` 是库的标准写法（第 10 章讲过模块名 `mypkg.db` → logger 名 `mypkg.db`，层级自动成立）。

```python
>>> logger = logging.getLogger("myapp")
>>> logger.getEffectiveLevel()          # 未显式设置时，向上找父级/root 的级别
20                                      # WARNING（root 默认 WARNING）
```

**传播（propagate）**：logger 处理完自己的 Handler 后，若 `propagate=True`，LogRecord 继续**冒泡给父 logger 的 Handler**——这就是"`import 第三方库` 后它打日志你也能看到"的原因（库 logger 默认 propagate 到 root）。

> **⚠️ 陷阱**：
> - **重复日志**：父 logger 和子 logger 都挂了 Handler 时，一条日志会被记两次（子处理一次 + 冒泡到父再处理一次）。解决：子 logger 设 `propagate = False`，或只在 root 挂 Handler；
> - **库的规范**：写库时**只用 `logging.getLogger(__name__)`，不要加 Handler**（加 Handler 会污染使用方的输出）——库应加 `logging.NullHandler`（防止 "No handlers" 警告），由使用方统一配置；
> - `getLogger("x")` 与 `getLogger("x.y")` 是父子关系（名字前缀），但 `getLogger` 不检查名字合法性——拼错名会静默创建新 logger（看不到日志的常见原因：`getLogger("myapp")` 配置了，代码里写成 `getLogger("my_app")`）。

### 13.9.3 配置方式：basicConfig / dictConfig

```python
# 方式 1：basicConfig（脚本/小工具够用）
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    filename="app.log",          # 不写则输出到 stderr
)
```

```python
# 方式 2：dictConfig（应用级标准，可 JSON 化）
import logging.config
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "app.log",
            "maxBytes": 1_000_000,          # 1MB 轮转
            "backupCount": 3,
            "formatter": "default",
        },
    },
    "root": {"level": "INFO", "handlers": ["console", "file"]},
}
logging.config.dictConfig(LOGGING_CONFIG)
```

`dictConfig` 的优势：**配置是数据结构**——可以从 JSON/YAML 文件加载、可以由环境变量覆盖、可以测试。`fileConfig` 读 INI 是旧方案（不支持层级结构，新代码用 `dictConfig`）。

### 13.9.4 实战：结构化日志、轮转与 print 的取舍

#### 结构化日志：extra 与 JSON 输出

```python
logger.info("user logged in", extra={"user_id": 42, "ip": "1.2.3.4"})

# Formatter 里引用 extra 字段（用 %(user_id)s）
# 生产推荐：JSON 结构化输出（可被日志平台解析）
class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json
        data = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        data.update(getattr(record, "extra_fields", {}))
        return json.dumps(data, ensure_ascii=False)
```

#### 轮转：文件无限增长的解药

```python
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
# RotatingFileHandler：按大小轮转（maxBytes + backupCount）
# TimedRotatingFileHandler：按时间轮转（when="midnight" 每天一个文件）
```

#### ⚠️ 陷阱与最佳实践

1. **日志吞异常**：`logger.exception("msg")` 在 `except` 块里自动附带堆栈（等价 `error(..., exc_info=True)`）；`logging.exception` 只能在 except 块内调用，否则 `exc_info` 无效；
2. **格式化惰性**：`logger.debug(f"x={x}")` 的 `f-string` **无论级别是否启用都会求值**——性能关键路径用 `logger.debug("x=%s", x)`（`%` 延迟格式化，级别不满足时零开销）：
   ```python
   # ❌ 总是格式化（即使 DEBUG 未启用）
   logger.debug(f"expensive={compute_expensive()}")
   # ✅ 惰性：compute_expensive() 只在启用时被调用
   logger.debug("expensive=%s", compute_expensive())
   ```
3. **`print` vs `logging` 的取舍**：脚本/教学代码用 `print`（简单直接）；**任何"要排查问题"的程序用 `logging`**——时间戳、级别、调用点、输出重定向、轮转，全是 `print` 给不了的；
4. **不要全局改 root 级别**：库和应用的日志级别在配置层管理（`dictConfig`），代码里不写 `logging.basicConfig(level=...)`（它会覆盖使用方的配置）。

> **实战模式**：生产日志四要素——(1) `dictConfig` 集中配置；(2) JSON 结构化输出；(3) 轮转防无限增长；(4) 敏感字段脱敏（`Filter`，如密码/token）。这套组合让日志从"调试工具"变成"可检索的审计数据"。

#### 进阶：异步日志与请求关联 ID

**`QueueHandler` + `QueueListener`**：把日志写入内存队列，后台线程批量落盘——**让"打日志"不阻塞主业务线程**（日志 I/O 慢时的高性能方案）：

```python
import logging, logging.handlers, queue

q = queue.Queue(-1)                          # 无界队列
queue_handler = logging.handlers.QueueHandler(q)
file_handler = logging.FileHandler("app.log")
listener = logging.handlers.QueueListener(q, file_handler)

root = logging.getLogger()
root.addHandler(queue_handler)
root.setLevel(logging.INFO)
listener.start()                             # 后台线程消费队列写文件
# 业务代码 logging.info(...) 只做"入队"（微秒级），I/O 由监听线程完成
```

**请求关联 ID（correlation ID）**：一条请求的日志散落在多个模块里，用 `contextvars`（第 11 章的线程/协程本地变量）贯穿：

```python
import contextvars
request_id = contextvars.ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id.get()     # 注入每条日志记录
        return True

# 请求入口：request_id.set(uuid4().hex)
# 之后任何模块的日志都自动带 request_id 字段（结构化日志可直接检索）
```

> **🔑 机制洞察**：`contextvars` 是"**线程/协程局部变量**"的标准机制（`threading.local` 的升级版，异步场景可用）——它让"请求上下文"跨函数传递而不必显式传参。日志关联 ID 只是第一个应用，第 11 章并发与第 14 章测试都会用到它。`QueueHandler` + 关联 ID + JSON 结构化 = 高吞吐服务的日志三件套。

---

## 13.10 typing：类型标注基础（衔接第 12 章元编程）

类型标注（type hints）是 Python 3 最重要的"工程化"特性——它不改变运行时行为（默认），但让**静态检查、IDE 智能、接口文档**成为可能。

### 13.10.1 为什么需要类型标注（PEP 484 / 483）

Python 是动态语言——类型错误在运行时才暴露。类型标注（PEP 484，3.5+）把"**预期的类型**"写进代码，由**外部工具**（mypy/pyright/pytype）静态检查：

```python
def add(a: int, b: int) -> int:      # 参数类型 + 返回类型
    return a + b

add(1, "2")                          # 运行时：TypeError（字符串不能和 int 加）
# mypy 静态检查：error: Unsupported operand types for + ("int" and "str")
```

```bash
$ mypy app.py          # 静态检查，不运行代码
Success: no issues found in 1 source file
```

| 价值 | 说明 |
|------|------|
| 静态检查 | mypy/pyright 在**运行前**抓住类型 bug（大型重构的安全网） |
| IDE 智能 | 补全、跳转、重构都基于类型信息 |
| 接口文档 | 签名自带"参数是什么、返回什么" |
| 运行时校验 | 结合 `pydantic`/`dataclass`（第 7 章）在边界处校验 |

> **设计哲学**：Python 的取舍是"**动态语言的运行时 + 静态语言的检查器**"——类型标注**默认不改变运行时行为**（除非你主动用 `pydantic`/`typeguard` 做运行时校验）。这让团队可以渐进采纳：先注释式标注，再上 mypy，最后在边界做运行时校验。

### 13.10.2 常用类型速查

```python
from typing import Optional, Union, Any, Literal

# Optional[X] == Union[X, None]（X 或 None）
def find(name: str) -> Optional[int]: ...       # 可能返回 None

# Union：多种可能
def parse(s: str) -> Union[int, float]: ...

# Any：任意（放弃检查——尽量少用）
def passthrough(x: Any) -> Any: ...

# Literal：字面值约束
def set_mode(mode: Literal["fast", "safe"]) -> None: ...   # 只接受这两个字符串
```

**3.9+ 内置泛型（PEP 585）**——`typing.List` 等旧写法让位给内置类型：

| 旧写法（3.8-） | 新写法（3.9+） |
|----------------|----------------|
| `List[int]` | `list[int]` |
| `Dict[str, int]` | `dict[str, int]` |
| `Tuple[int, str]` | `tuple[int, str]` |
| `Set[str]` | `set[str]` |
| `Optional[int]` | `int \| None`（3.10+，PEP 604） |
| `Union[int, float]` | `int \| float`（3.10+） |

```python
def process(items: list[int]) -> dict[str, int]: ...
def maybe() -> int | None: ...          # 3.10+ 的 Union 简写
```

> **版本注意**：`list[int]` 是 3.9+（PEP 585），`int | None` 是 3.10+（PEP 604）。需要兼容老版本时用 `from __future__ import annotations`（3.7+）让标注惰性求值（见 13.10.4），或继续用 `typing.Optional`/`Union`。

### 13.10.3 泛型与 TypeVar

函数级泛型："对任意类型 T，函数行为一致"：

```python
from typing import TypeVar, Sequence

T = TypeVar("T")                       # 类型变量

def first(items: Sequence[T]) -> T:    # 返回与元素同类型
    return items[0]

first([1, 2, 3])    # T = int → int
first(["a"])        # T = str → str
```

`TypeVar` 的约束与协变：

```python
T = TypeVar("T", bound=Animal)         # 约束：T 必须是 Animal 或其子类
def make(proto: type[T]) -> T: ...     # type[T]：返回 T 的实例

# 协变/逆变（Covariant/Contravariant）——"List[Cat] 是不是 List[Animal]？"
# 规则：只读容器协变（List[Cat] 可当 List[Animal] 用——但可变容器不行！）
# ❌ def f(xs: list[Animal]) 不能传 list[Cat]（list 可变，可往里塞 Dog）
# ✅ def f(xs: Sequence[Animal]) 可以（Sequence 只读，协变）
```

> **🔑 机制洞察**：**可变容器不可协变**是类型系统的核心安全规则——`list[Dog]` 不能当作 `list[Animal]`，否则你能 `append` 一只猫进"狗列表"。只读接口（`Sequence`/`Mapping`）协变安全。写泛型函数时：参数用**只读类型**（`Sequence`/`Mapping`）而非可变类型（`list`/`dict`），是"类型正确的泛型"的关键习惯。

#### 高级标注：Protocol / NewType / overload

**`Protocol`（PEP 544，3.8+）**——**结构子类型**：不要求继承，只要"有这些方法"就算满足（第 7 章讲过的鸭子类型的静态化）：

```python
from typing import Protocol

class SupportsClose(Protocol):        # 结构协议：有 close() 就行
    def close(self) -> None: ...

def cleanup(obj: SupportsClose) -> None:   # 任何有 close() 的对象都接受
    obj.close()

class File:                            # 不需要继承 SupportsClose！
    def close(self) -> None: ...
class DB:                              # 也不需要
    def close(self) -> None: ...

cleanup(File()); cleanup(DB())         # ✅ 类型检查通过（结构匹配）
```

与第 7 章 `abc.ABC` 的对比：`ABC` 是**运行时**强制（`isinstance` 检查 + 抽象方法）；`Protocol` 是**静态检查**的（`isinstance` 需 `@runtime_checkable` 装饰才可用，且只检查方法存在性）。

**`NewType`**——"**名义上的新类型**"（防止"用户名"和"ID"混用）：

```python
from typing import NewType
UserId = NewType("UserId", int)        # 运行时就是 int

def get_user(uid: UserId) -> str: ...
get_user(123)                          # ❌ mypy 报错：int 不是 UserId
get_user(UserId(123))                  # ✅ 显式包装
```

**`@overload`**——同一函数"不同参数类型 → 不同返回类型"的声明（运行时只有最后一个实现）：

```python
from typing import overload

@overload
def parse(s: str) -> dict: ...         # str → dict
@overload
def parse(b: bytes) -> list: ...       # bytes → list
def parse(x):                           # 实际实现（无类型标注或 Any）
    return json.loads(x) if isinstance(x, str) else list(x)

# 调用方视角：parse("{}") 的类型被推断为 dict，parse(b"") 为 list
```

> **实战建议**：团队引入 `typing` 的进阶路线——先用基础标注（13.10.2）跑通 mypy → 加 `TypeVar` 泛型（13.10.3）→ 需要"鸭子类型静态化"时用 `Protocol` → 需要"防混用"时用 `NewType`。`overload` 是库作者优化 API 类型体验的工具，应用代码很少用。

### 13.10.4 运行时 vs 静态：get_type_hints 与标注开销

```python
>>> from typing import get_type_hints
>>> def f(x: int) -> str: return str(x)
>>> f.__annotations__                    # 标注存在函数属性里
{'x': <class 'int'>, 'return': <class 'str'>}
>>> get_type_hints(f)                    # 解析字符串形式（如 "list[int]"）为真实对象
{'x': <class 'int'>, 'return': <class 'str'>}
```

```python
# from __future__ import annotations（3.7+）：标注变成字符串，惰性求值
# 好处 1：3.9 之前也能写 list[int]
# 好处 2：避免"类还没定义完就求值"（自引用标注）
# 代价：get_type_hints 需要运行时解析（慢、且字符串环境缺失时失败）
```

> **⚠️ 陷阱**：
> - **性能**：`get_type_hints` 是**运行时解析**，调用有开销（毫秒级）——不要在热路径反复调用；需要时缓存结果；
> - 标注是普通属性：`f.__annotations__` 可被修改（元编程玩具，第 12 章）；
> - 不加 `from __future__ import annotations` 时，**函数定义处就求值**标注——`def f(x: Undefined)` 会在**定义时**抛 `NameError`（不是调用时）；
> - `Any` 是"放弃检查"——过度使用等于没有类型标注；`object` 才是"运行时是真的对象"（`Any` 与 `object` 的语义差异：`Any` 允许任意操作不报错，`object` 只允许对象基础操作）。

---

## 13.11 更多即查即用：隐藏宝石速查

本章精选了十大工具箱，但标准库还有一批"小而美"的模块——它们解决单点问题，**即查即用**（本系列"肘后备急"理念的集中体现）：

| 模块 | 一句话定位 | 常用 API | 典型场景 |
|------|-----------|---------|---------|
| `hashlib` | 哈希摘要 | `hashlib.sha256(data).hexdigest()` | 文件指纹、密码哈希（配 `secrets`） |
| `base64` | 二进制 ↔ 文本编码 | `base64.b64encode(b"...")` | 传输二进制（URL、邮件） |
| `uuid` | 通用唯一标识 | `uuid.uuid4().hex` | 请求 ID、主键、幂等键 |
| `zipfile` / `tarfile` | 归档文件 | `zipfile.ZipFile(...).extractall()` | 解压/打包（第 9 章 `shutil` 也有封装） |
| `pprint` | 美化打印 | `pprint.pprint(obj)` | 调试复杂嵌套结构 |
| `difflib` | 序列差异 | `difflib.SequenceMatcher` / `unified_diff` | 文本 diff、相似度匹配 |
| `webbrowser` | 打开浏览器 | `webbrowser.open(url)` | 脚本"自动打开结果页" |
| `tempfile` | 临时文件 | `tempfile.NamedTemporaryFile`（第 9 章讲过） | 安全临时文件 |
| `warnings` | 弃用警告 | `warnings.warn("...", DeprecationWarning)` | 库 API 演进（第 10 章 10.4.1 用过） |
| `inspect` | 对象内省 | `inspect.getsource`/`signature`/`isfunction` | 调试、框架、13.1.3 读源码 |
| `functools.reduce` | 归约 | 见 13.4.4 | 聚合计算 |
| `contextlib` | 上下文工具 | 第 8 章已细讲 | — |
| `dataclasses` | 数据类 | 第 7 章已细讲 | — |

```python
# 三个最高频的即查即用示例
>>> import hashlib, uuid, base64
>>> hashlib.sha256(b"data").hexdigest()[:16]
'3a6eb079...'
>>> uuid.uuid4()
UUID('7f9c2e8a-...')
>>> base64.b64encode(b"hello")          # b'hello' → 文本
b'aGVsbG8='
>>> import difflib
>>> "".join(difflib.unified_diff(["a\n", "b\n"], ["a\n", "c\n"], lineterm=""))
'- b\n+ c\n'
```

> **实战模式**：新项目起步时的标准库"默认组合"——配置 `tomllib` + 日志 `logging` + 参数 `argparse` + 存储 `sqlite3`/`json` + 哈希 `hashlib` + ID `uuid` + 进程 `subprocess`。这套组合能覆盖大多数中小工具的全部需求，**依赖面为零**（第 10 章锁文件/供应链视角的隐含红利）。等需求确实超出标准库（性能、领域功能）再引入第三方——13.1.2 的选型哲学在此落地。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 标准库全景 | 313 个模块（`sys.stdlib_module_names`）；六象限地图；选型：基础能力用标准库、核心路径可上第三方 |
| 读源码 | `inspect.getsource()`；"C 加速 + Python 兜底"的双实现模式（`_collections`） |
| `collections` | `defaultdict`（`__missing__`）、`Counter`（C 计数）、`OrderedDict`（3.7+ 新定位）、`deque`（双端 O(1)）、`ChainMap`、`namedtuple`、`UserDict`（安全子类化） |
| `itertools` | 全部惰性；`product` 替嵌套循环、`groupby` 只认相邻、`islice` 惰性切片、`tee` 有缓存代价 |
| `functools` | `partial`（闭包显式化）、`lru_cache`（OrderedDict LRU）、`singledispatch`（注册表多态）、`wraps`（装饰器必加） |
| `datetime` | 不可变 + 可哈希；`timedelta` 三字段归一化；**内部 UTC、展示转本地**；`zoneinfo` 替代 `pytz`（PEP 615）；DST 折叠用 `fold` |
| 数字 | `math.isclose` 判浮点相等；**货币用 `Decimal`**（字符串构造 + `localcontext`）；`Fraction` 精确有理数；**安全随机用 `secrets`**；`fmean` 精确累加 |
| 系统 | `subprocess.run` + `shell=False` 防注入；`shutil.copy2` 保留元数据；`pathlib.glob` 优先；`sys.platform` 做分支 |
| 持久化 | `sqlite3` 参数化防注入 + 3.12 with 事务；`csv` 必写 `newline=''`；`configparser` 的 `DEFAULT` 继承；`argparse` 完整 CLI |
| `logging` | Logger/Handler/Formatter/Filter 四件套；`getLogger(__name__)` 层级；库只加 `NullHandler`；`dictConfig` + JSON 结构化 + 轮转 |
| `typing` | PEP 484 静态检查；3.9+ 内置泛型、3.10+ `\|` 语法；`TypeVar` 泛型；只读容器协变安全；`get_type_hints` 有解析开销 |

---

#### 练习 13

**第 1–3 题：验证理解（预测/解释）**

1. 预测输出：`Counter("aab") + Counter("abc")`、`Counter("aab") - Counter("abc")`、`Counter("aab") & Counter("abc")` 各是多少？`defaultdict` 的 `d.get("missing")` 会触发默认值吗？为什么？

2. 解释 `groupby` 的行为：`list(groupby([1, 1, 2, 1, 2]))` 分成了几组？为什么不是"两个 1 一组、两个 2 一组"？要按全局键分组必须先做什么？

3. 解释 `lru_cache` 装饰 `def load_config(path: str) -> dict` 会有什么隐患？`Decimal(0.1)` 与 `Decimal("0.1")` 的区别是什么？为什么财务代码必须用后者？

**第 4–6 题：动手实战**

4. 用 `itertools.product` 重写一个三层嵌套循环（如生成所有 `(r, g, b)` 颜色组合），再用 `timeit` 对比嵌套循环版本与 `product` 版本的内存/耗时差异。

5. 写一个"最近 N 条命令历史"的数据结构：用 `deque(maxlen=N)` 实现；再对比 `list` + `pop(0)` 的实现，解释为什么 `deque` 更好。

6. 用 `zoneinfo` 写一个函数 `convert_time(iso_str, from_tz, to_tz) -> str`：解析 ISO 时间戳 → 转目标时区 → 输出 ISO 格式。分别测试 `Asia/Shanghai` → `UTC` 和跨越 DST 的 `America/New_York` 日期。

**第 7–9 题：实战进阶**

7. 用 `argparse` + `sqlite3` 做一个迷你任务清单 CLI（`add`/`list`/`done` 三个子命令），参数全部参数化查询，验证 `--help` 输出，并用 `[project.scripts]`（第 10 章）把它装成命令。

8. 用 `logging` 搭一个应用级日志：`dictConfig` 配置（控制台 + `RotatingFileHandler` 轮转 + JSON 结构化），子模块用 `getLogger(__name__)`，验证 propagate 行为，并演示"敏感字段脱敏"的 `Filter`。

9. 用 `functools.lru_cache` 加速一个递归函数（如爬楼梯/组合数），打印 `cache_info()` 对比加速前后耗时；再用 `functools.singledispatch` 为 `int`/`str`/`list` 各写一个 `summarize(x)` 实现。

**第 10 题：深度思考**

10. 假设你要为一个数据处理服务做技术选型：日志（标准库 `logging` vs 第三方 `loguru`）、配置（`configparser` vs `tomllib` vs `pydantic`）、CLI（`argparse` vs `click`）。基于 13.1.2 的选型矩阵，逐项给出你的决策与理由；再回答：标准库"自带电池"对项目的**依赖面**（第 10 章锁文件、供应链安全）有什么隐含价值？

---

**进入下一章的准备**：
- ✅ 能按"问题 → 模块"索引：计数用 `Counter`、组合用 `itertools`、记忆化用 `lru_cache`、时间用 `zoneinfo`、金额用 `Decimal`、进程用 `subprocess.run`、参数用 `argparse`、日志用 `logging`
- ✅ 能解释 `collections` 双实现模式、`deque` 的 O(1) 两端、`groupby` 的相邻性、`lru_cache` 的 LRU 机制
- ✅ 牢记安全红线：`shell=False`、SQL 参数化、`secrets` 而非 `random`、日志脱敏
- ✅ 会读标准库源码（`inspect.getsource`），知道"先查标准库再手写"
- ✅ 能用 `typing` + mypy 做静态检查，理解"标注默认不影响运行时"

下一章（第 14 章 测试与调试）将进入"如何证明你的代码是对的"——届时 `logging` 的调试价值、`datetime` 的可复现性（固定时间）、`random.seed` 的确定性，都是测试设计的关键工具，我们会回来引用本章。