# 第15章 性能优化与 C 扩展

> **学习目标**：回答"Python 为什么慢、怎么让它快"的完整答案——建立**性能优化路线图**（剖析 → 算法 → 语言级 → 向量化 → JIT → C 层）；掌握 `cProfile`/`line_profiler`/`tracemalloc` 的进阶用法；看懂 CPython 3.11+ 特化解释器的加速原理；能用 `ctypes`/C API/Cython 三层手段调用或编写 C 代码；最后以**卷 1 全景收官**，把 15 章串成完整的能力地图。

---

这是卷 1 的收官章。前 14 章建立了完整的能力体系：语言核心（1–5）、函数与对象（6–7）、异常与 IO（8–9）、模块与打包（10）、并发（11）、元编程（12）、标准库（13）、测试与调试（14）。但有一个问题贯穿始终、至今没有正面回答：**Python 为什么慢？能不能变快？** 本章给出完整答案——不是"Python 慢"的抱怨，而是**从解释器执行模型到 C 扩展的全栈优化路线图**。学完本章，你能在"改算法"与"写 C"之间做出理性选择，也能看懂 numpy 为什么快、PyPy 什么时候有用、`pip install` 一个含 C 扩展的包时发生了什么。

本章与前面章节的关系：第 14 章 14.9 已讲 `cProfile`/`timeit`/`tracemalloc` 入门，本章**进阶到工程实践**并补齐 `line_profiler`/`gc`/`objgraph`；第 11 章 11.1.3 的 GIL 机制在 15.8.4 以"C 代码释放 GIL"兑现；第 3 章的容器复杂度表是 15.3 算法优化的基础；第 13 章的 `itertools`/`functools`/`bisect` 是语言级优化的现成工具；第 10 章的 wheel/`pyproject.toml`/editable install 在 15.8.5 编译 C 扩展时复用。

---

## 15.1 性能全景：Python 为什么慢

### 15.1.1 解释器执行模型（🔑 机制洞察）

**"Python 慢"的本质不是某个操作慢，而是"每条操作都贵"**。CPython 执行 Python 代码的模型：

```c
// CPython 的字节码求值循环（简化，Objects/ 与 Python/ceval.c）
// _PyEval_EvalFrameDefault：一个巨大的 switch 循环
for (;;) {
    opcode = *next_instr++;              // 取指令
    switch (opcode) {
        case LOAD_FAST: ...              // 局部变量：数组索引（快）
        case LOAD_GLOBAL: ...            // 全局：字典查找（中）
        case LOAD_ATTR: ...              // 属性：类型查找 + 描述符（慢）
        case BINARY_OP: ...              // 二元运算：动态分派（慢）
    }
}
```

每条 Python 语句编译成若干**字节码指令**，解释器逐个执行。对比 C 的"编译成机器码直接跑"，Python 多付出的开销：

| 开销来源 | 说明 | 对比 C |
|---------|------|--------|
| 指令解释 | 每条字节码都要取指/分派 | 机器码直接执行 |
| **动态分派** | `a + b` 要先查类型、调 `__add__`（第 4 章运算符重载协议） | 编译期确定类型，一条 `ADD` 指令 |
| **装箱** | 整数是对象（`PyLongObject`），不是寄存器值（第 3 章） | `int` 就是寄存器 |
| 属性查找 | `obj.attr` 走完整查找链（12.4.1） | 编译期算偏移 |
| 内存管理 | 每个对象引用计数（第 3 章） | 栈上分配即用即弃 |

```python
# 同一个循环，量级差距的直观感受：
# Python：每个元素都是对象、每次运算都动态分派
sum([i * 2 for i in range(10_000_000)])
# C：int 数组 + 一条循环指令，编译器向量化后可能一条 SIMD 搞定
```

> **🔑 机制洞察**："Python 慢 10–100 倍"是**每条操作都贵**的累积——不是某个瓶颈。这也决定了优化方向：**减少"操作次数"**（算法）、**减少"每条操作的代价"**（语言级/C 层）。两个方向都有极限：Python 代码再优化也快不过"根本不执行 Python"（numpy/C 扩展）。

### 15.1.2 性能优化路线图

五层杠杆，**收益递减、成本递增**：

```
① 算法/数据结构    收益：10x–1000x   成本：低（改思路）     ← 第一杠杆
② 语言级优化      收益：1.5x–5x      成本：低（改写法）
③ 向量化（numpy） 收益：10x–100x     成本：中（换思维）
④ JIT（PyPy/numba）收益：5x–50x      成本：中（换引擎）
⑤ C 扩展          收益：10x–1000x    成本：高（写 C）       ← 最后手段
```

**铁律（第 14 章方法论化）**：

```
1. 先剖析（cProfile/line_profiler）——找到真正的热点，别猜
2. 从①开始——改算法往往是最便宜的百倍提速
3. 每步用 timeit 验证——"改完不重测 = 白改"
4. 保留回归测试——优化不能破坏正确性（第 14 章闭环）
5. 到"够快"就停——性能是需求，不是爱好
```

> **工程影响**：优化的**正确顺序**是反直觉的——大多数人先试"微优化"（第 4 层以下的技巧），实际收益最大的是**算法**（第 1 层）。一个 O(n²) 的 Python 循环，优化成 O(n) 是 1000 倍；而把它手写成"更快的 Python"最多 5 倍。**先看复杂度，再看写法，最后才考虑换语言**。

### 15.1.3 什么时候值得优化

```python
# 决策矩阵：这个"慢"值得修吗？
# 1. 用户可见延迟（API 响应、UI 卡顿）→ 值得（体验 = 钱）
# 2. 高频后台任务（批处理、爬虫、定时任务）→ 值得（省机器）
# 3. 一次性脚本（跑一次就扔）→ 不值得（能跑就行）
# 4. 还没发生的问题（"可能以后会慢"）→ 不值得（过早优化）
```

> **⚠️ 陷阱（过早优化）**：Knuth 的名言"过早优化是万恶之源"在 Python 语境下更真实——**优化代码 = 牺牲可读性**（局部变量缓存、内联展开、C 扩展）。规则：**先用最简单的方式写对，再剖析，只优化被证明的热点**。第 14 章的"测试即设计"与本章的"剖析即优化"是同一方法论的两面：**先测量，再动手**。

---

## 15.2 剖析进阶：找到每一毫秒

第 14 章 14.9 入门了 `cProfile`/`timeit`/`tracemalloc`，本节补齐进阶工具与工程姿势。

### 15.2.1 cProfile 深潜

```python
# 保存剖析结果到文件（避免输出干扰、可反复分析）
$ python -m cProfile -o profile.out app.py

# 交互式分析（pstats）
>>> import pstats
>>> stats = pstats.Stats("profile.out")
>>> stats.strip_dirs()                     # 去掉绝对路径（可读性）
>>> stats.sort_stats("cumulative").print_stats(10)      # 前 10 名
>>> stats.sort_stats("tottime").print_stats(10)         # 自己最慢的 10 个
>>> stats.print_callers("process_item")    # 谁调用了它（调用方归因）
>>> stats.print_callees("process_item")    # 它调用了谁
```

**`cumtime` 的正确解读（回顾 14.9 + 进阶）**：

```python
# 场景：process_item 的 cumtime 巨大、tottime 很小
# → 慢在【子调用链】。print_callees 看它调了谁：
#   process_item 调用了 validate（cumtime 大、tottime 大）
#   → 真正热点是 validate 内部
# 注意：cumtime 含"等锁/等 IO"时间——多线程程序里 cumtime 可能虚高
#       （两个线程的 cumtime 相加可能超过墙钟时间）
```

> **⚠️ 陷阱**：剖析器自身有开销（每条指令挂钩子）——cProfile 让程序慢 2–5 倍，但**相对比例**仍然可信（热点还是热点）。剖析**多线程**程序时，`cumtime` 含等待时间，看 `tottime` 更准。剖析 C 扩展（numpy 内部）**不显示**（只显示"调用了 numpy 函数"这一层）。

### 15.2.2 line_profiler：逐行剖析

cProfile 到"函数级"，`line_profiler` 到**行级**——"这个函数慢，到底哪一行最贵"：

```python
# pip install line_profiler
from line_profiler import profile

@profile                       # 标记要逐行剖析的函数
def process_rows(rows):
    result = []
    for row in rows:
        cleaned = row.strip().lower()        # 行 A
        tokens = cleaned.split(",")          # 行 B
        result.append([t.strip() for t in tokens])   # 行 C
    return result
```

```bash
$ kernprof -l -v app.py        # 逐行剖析并输出
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     5                                           @profile
     6                                           def process_rows(rows):
     7         1        100.0    100.0      0.1      result = []
     8    100000      50000.0      0.5     31.2      for row in rows:
     9    100000      30000.0      0.3     18.8          cleaned = row.strip().lower()
    10    100000      40000.0      0.4     25.0          tokens = cleaned.split(",")
    11    100000      40000.0      0.4     25.0          result.append(...)
```

> **实战建议**：**函数级先 cProfile（找哪个函数），行级再 line_profiler（找哪一行）**——两段式剖析是定位热点的标准流程。`% Time` 列告诉你"这一行占了函数多少时间"，优化目标 = 占比最高的行。注意 `@profile` 只在 `kernprof` 下可用（普通运行时是未定义名）——用 `kernprof` 跑而不是直接 `python`。

### 15.2.3 内存剖析深潜

**`tracemalloc` 进阶**（回顾 14.9）：快照对比定位"内存增长来自哪行"：

```python
import tracemalloc

tracemalloc.start()
before = tracemalloc.take_snapshot()
run_workload()                              # 被测代码
after = tracemalloc.take_snapshot()

# 增长最多的 5 个分配位置
for stat in after.compare_to(before, "lineno")[:5]:
    print(stat)
# /app.py:42: size=9.8 MiB (+9.8 MiB), count=100000   ← 第 42 行涨了 9.8MB
```

**`gc` 模块**：引用环回收与调试（衔接第 3 章引用计数）：

```python
>>> import gc
>>> gc.collect()                  # 手动触发一次完整回收（含循环引用）
>>> gc.get_objects()              # 当前所有被跟踪对象（内存泄漏排查起点）
>>> gc.get_referrers(obj)         # 谁引用了这个对象（反向查找！）
# 经典场景：定位"对象为什么没被释放"→ get_referrers 找出持有者
```

**`objgraph`**：对象引用图（`pip install objgraph`）：

```python
>>> import objgraph
>>> objgraph.show_growth(limit=10)     # 哪些类型的对象在增长（泄漏诊断）
# dict  +5000
# list  +3000          ← 某种对象在持续增长 = 泄漏嫌疑
>>> objgraph.show_backrefs(obj, filename="refs.png")   # 画引用链图
```

> **实战建议**：内存问题三分法——**持续增长**（泄漏）用 `objgraph.show_growth` 找类型 + `get_referrers` 找持有者；**峰值过高**用 `tracemalloc` 快照定位分配行；**循环引用**（`__del__` 不执行）用 `gc.collect` + `gc.get_objects` 分析。注意：**现代 Python 的容器（dict/list）大量用非跟踪优化**——`gc` 能看到的对象比实际少，结合 `tracemalloc` 一起用。

### 15.2.4 剖析工程实践

```python
# 1. 基准测试的正确姿势（回顾 14.9 的 timeit 规范）
# 2. 性能回归测试：把关键路径的耗时写进测试（阈值断言）
import time, pytest

def test_performance_regression():
    t0 = time.perf_counter()
    result = process_1m_rows(data)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"处理 100 万行耗时 {elapsed:.2f}s，超出预算"

# 3. pytest-benchmark：专业的基准测试插件
def test_bench(benchmark):
    benchmark(process_1m_rows, data)      # 自动多次采样、统计
    # 输出：中位数/标准差/每秒操作数 —— 可对比历史
```

> **工程影响**：性能回归测试是"性能也是功能"的落地——**发布前后对比基准**（`pytest-benchmark` 的 `--benchmark-compare` 自动对比两次运行）。规则：**阈值留 20–30% 余量**（CI 机器抖动）；性能测试与功能测试分开跑（慢、且机器负载敏感）。CI 里把"关键路径基准"作为发布门禁之一，性能回退在合并前暴露。

#### 一个完整的剖析走查（🔑 实战模式）

把本节工具串成一个真实场景：**"处理 10 万条订单记录太慢"**。

```python
# 被测代码（数据清洗 + 聚合）
def process_orders(orders):
    cleaned = []
    for o in orders:
        name = o["name"].strip().lower()          # 字符串处理
        amount = float(o["amount"])               # 数值转换
        cleaned.append({"name": name, "amount": amount})
    by_name = {}
    for c in cleaned:
        by_name.setdefault(c["name"], []).append(c["amount"])   # 分组
    totals = {k: sum(v) for k, v in by_name.items()}
    return totals
```

**第 1 步：cProfile 找函数级热点**

```bash
$ python -m cProfile -s cumulative app.py
   ncalls  tottime  cumtime  filename:lineno(function)
        1   0.012    0.821   app.py:5(process_orders)
   100000   0.310    0.310   app.py:8(amount 转换)       ← 热点 1：float 转换
   100000   0.180    0.180   app.py:7(name 处理)         ← 热点 2：strip/lower
   100000   0.120    0.120   app.py:13(setdefault+append) ← 热点 3：分组
```

**第 2 步：line_profiler 定位行级热点**（对 `process_orders`）——确认第 8 行 `float()` 与第 7 行字符串链最贵。

**第 3 步：算法审查（15.3）**——`setdefault().append()` 改成 `defaultdict(list)`（第 13 章）：

```python
from collections import defaultdict
by_name = defaultdict(list)
for c in cleaned:
    by_name[c["name"]].append(c["amount"])        # 少一次 setdefault 调用
```

**第 4 步：语言级优化（15.4）**——字符串处理局部化、批量转换：

```python
def process_orders(orders):
    by_name = defaultdict(list)
    for o in orders:
        by_name[o["name"].strip().lower()].append(float(o["amount"]))  # 一次循环完成
    return {k: sum(v) for k, v in by_name.items()}
```

**第 5 步：复测**（每步 timeit）：

```bash
# 原始：0.82s → 第 3 步：0.61s → 第 4 步：0.48s（1.7 倍）
# 每步验证：功能测试（第 14 章）通过 + 耗时下降
# 结论：够了就停；还不够 → 第 5 层（numpy 批量 float 转换）
```

> **🔑 实战模式**：走查揭示了标准流程的每个动作——**剖析给方向（哪行贵）→ 算法改结构（defaultdict）→ 语言级改写法（合并循环）→ 每步复测**。注意第 4 步的"合并循环"同时减少了循环次数与中间列表（惰性 + 批量思想）——**优化常常是多个杠杆的叠加**。

---

## 15.3 算法与数据结构优化：第一杠杆

### 15.3.1 复杂度是第一杠杆

第 3 章给过容器复杂度表，这里把它变成**优化武器**：

| 操作 | 复杂度 | 典型场景 |
|------|--------|---------|
| `x in list` | O(n) | 线性扫描 |
| `x in set` / `x in dict` | **O(1)** | 哈希查找 |
| `list.index(x)` | O(n) | 按值找下标 |
| `list.pop(0)` / `insert(0)` | O(n) | 头部操作（第 13 章 deque！） |
| `sorted(list)` | O(n log n) | 排序 |
| 双重循环 | O(n²) | 最常被优化的对象 |

**实战：从 O(n²) 到 O(n)**——"找交集"的三种写法：

```python
import timeit

# ❌ O(n²)：列表 in 查找
def intersection_slow(a, b):
    return [x for x in a if x in b]        # b 是 list → 每个 x 都扫一遍

# ✅ O(n)：set 查找
def intersection_fast(a, b):
    b_set = set(b)                          # 一次哈希构建
    return [x for x in a if x in b_set]     # 每个 x 都是 O(1)

# 实测（n = 10000）：
>>> timeit.timeit(lambda: intersection_slow(list(range(10000)), list(range(5000, 15000))), number=10)
2.1
>>> timeit.timeit(lambda: intersection_fast(list(range(10000)), list(range(5000, 15000))), number=10)
0.008        # 快 260 倍！—— 这就是"改数据结构"的威力
```

> **🔑 性能数据**：O(n²) → O(n) 的收益随 n 增长而爆炸——n=10000 时 260 倍，n=100000 时超过 1000 倍。**优化的第一步永远是问"我的算法是什么复杂度"**。常见的 O(n²) 信号：嵌套循环里有 `in list`/`index`/`count`。

### 15.3.2 缓存与记忆化

`lru_cache`（回顾 13.4.2）是"重复计算"的通用解药：

```python
from functools import lru_cache

# 场景：同一输入被反复计算（如数据库查询结果、解析结果）
@lru_cache(maxsize=1024)
def parse_config(path):
    ...                                    # 昂贵解析
    return config

# 场景：递归/DP 的指数爆炸（回顾 13.4.2 的斐波那契）
@lru_cache(maxsize=None)
def fib(n): ...
```

**缓存的边界**（何时失效/不能用）：

| 条件 | 说明 |
|------|------|
| 函数必须纯 | 同参数同结果；依赖外部状态/时间 → 缓存污染（13.4.2 陷阱） |
| 参数可哈希 | list/dict 参数需转 tuple/frozenset |
| 内存有界 | `maxsize` 设合理值，或用 `cache`（无界，适合少量大结果） |
| 缓存失效策略 | 显式 `cache_clear()`（配置变更时） |

> **实战建议**：缓存是"空间换时间"的经典——**收益 = 重复计算量 × 单次成本**；代价 = 内存 + 陈旧风险。判断标准：**重复率高的纯函数**（解析、查询、映射）用缓存；**一次性的计算**别缓存（纯浪费）。

### 15.3.3 惰性与批量

**惰性（回顾 13.3）**：不计算用不到的东西——

```python
# ❌ 全部物化再取前 3
big = [expensive(x) for x in range(1_000_000)]
first3 = big[:3]                # 算了 100 万个，只用 3 个

# ✅ 惰性 + 短路
from itertools import islice
first3 = list(islice((expensive(x) for x in range(1_000_000)), 3))   # 只算 3 个
```

**批量（回顾 13.8.1 的 executemany）**：把 N 次小操作合成一次——

```python
# ❌ 逐条插入（N 次网络/磁盘往返）
for row in rows:
    cursor.execute("INSERT INTO t VALUES (?, ?)", row)

# ✅ 批量（1 次往返）
cursor.executemany("INSERT INTO t VALUES (?, ?)", rows)
```

> **🔑 机制洞察**：惰性优化"**算得少**"（懒），批量优化"**每次干得多**"（合并）。两者的共同本质：**减少固定开销的次数**——循环迭代开销、函数调用开销、IO 往返开销。凡是有"N 次固定成本"的地方，都有"批量/惰性"的优化空间。

#### 数据结构选型实战（第 13 章工具的优化视角）

第 13 章的容器工具在此变成"性能武器"：

```python
# 场景 1：百万数据里取 Top-K（第 13 章 heapq）
import heapq, random
data = random.sample(range(10**8), 10**6)

# ❌ 全排序（O(n log n)，还要物化）
top100 = sorted(data)[-100:]
# ✅ 堆（O(n log k)，k=100）
top100 = heapq.nlargest(100, data)      # 快 ~10 倍（n=10^6, k=100）

# 场景 2：有序插入（第 13 章 bisect）
import bisect
# ❌ 线性插入（每次 O(n) 搬移——但 list 插入本来就是 O(n)，bisect 只省查找）
# ✅ bisect.insort（查找 O(log n)，插入仍 O(n)）
#    注意：大量有序插入用 heapq 或 sortedcontainers 更优；bisect 适合"读多写少"

# 场景 3：LRU 缓存（第 13 章 OrderedDict 的 move_to_end）
from collections import OrderedDict
class LRU:
    def __init__(self, cap): self.cap = cap; self.d = OrderedDict()
    def get(self, k):
        if k not in self.d: return None
        self.d.move_to_end(k)           # 标记最近使用
        return self.d[k]
    def put(self, k, v):
        self.d[k] = v; self.d.move_to_end(k)
        if len(self.d) > self.cap:
            self.d.popitem(last=False)  # 淘汰最久未用（O(1)）
```

> **🔑 性能洞察**：数据结构优化 = **选对容器**——`set` 把 `in` 从 O(n) 变 O(1)、`heapq` 把 Top-K 从 O(n log n) 变 O(n log k)、`OrderedDict` 让 LRU 全 O(1)、`deque` 让双端 O(1)（回顾 13.2）。**算法复杂度的背后是数据结构的选择**——优化第一步看容器，第二步看循环。

### 15.3.4 完整优化案例走查（🔑 实战模式）

**场景**：统计 10 万条日志里每个 IP 的出现次数。

```python
# 版本 1：直观写法（O(n) 但每条操作贵）
counts = {}
for line in log_lines:
    ip = line.split()[0]              # 每次 split 整个行
    if ip in counts:
        counts[ip] += 1
    else:
        counts[ip] = 1

# 版本 2：标准库工具（Counter 的 C 计数，回顾 13.2.1）
from collections import Counter
counts = Counter(line.split()[0] for line in log_lines)

# 版本 3：先切 IP 再批量（减少 split 次数 + C 计数）
ips = [line.split(" ", 1)[0] for line in log_lines]    # 只 split 一次拿第一段
counts = Counter(ips)
```

```bash
# 实测对比（10 万行日志）：
# 版本 1：0.45s
# 版本 2：0.28s（Counter C 计数）
# 版本 3：0.19s（split 限定 maxsplit=1 + C 计数）—— 快 2.4 倍
```

**优化链条复盘**：同一问题，从"手写循环"到"标准库 + 参数优化"，2.4 倍来自**减少每条操作的代价**（C 实现、少 split）。如果还嫌慢，下一步就是 15.5 的 numpy（向量化）或 15.8 的 C——**但先用尽 Python 层的最优写法**。

---

## 15.4 语言级优化：字节码视角

第 14/10/11/12 章都用过 `dis`，本节系统化：**用字节码知识指导写法**。

### 15.4.1 dis 分析热点（🔑 字节码分析）

```python
>>> import dis

# 对比：三种"累加"的字节码成本
>>> dis.dis("sum(xs)")
  0 LOAD_NAME     0 (sum)
  2 LOAD_NAME     1 (xs)
  4 CALL_FUNCTION 1              # 1 次 C 调用

>>> def manual(xs):
...     total = 0
...     for x in xs:
...         total += x
...     return total
>>> dis.dis(manual)
  0 LOAD_CONST 0 (0)
  2 STORE_FAST 0 (total)
  4 LOAD_FAST  1 (xs)
  6 GET_ITER
  8 FOR_ITER     ...             # 循环：每次迭代 N 条指令
  ...
  # 循环体 4-5 条指令 × N 次 —— 这就是差距
```

> **🔑 字节码洞察**：`sum(xs)` 是**一条 `CALL_FUNCTION` 进 C 循环**；手写循环是**每条迭代执行 4–5 条字节码**。这就是"内置函数优先"的字节码依据——**把 Python 循环换成 C 循环，是语言级优化最赚的一笔**。

### 15.4.2 局部变量 vs 全局变量

```python
>>> import dis
>>> def local():
...     total = 0
...     for i in range(1000): total += i
...     return total
>>> dis.dis(local)
  LOAD_FAST  0 (total)      # 局部：数组索引（1 条指令，最快）
  ...
>>> GLOBAL = 1000
>>> def global_():
...     total = 0
...     for i in range(GLOBAL): total += i   # 引用模块级 GLOBAL
...     return total
>>> dis.dis(global_)
  LOAD_GLOBAL 0 (GLOBAL)    # 全局：字典查找（更慢）
```

```python
# 实测：局部 vs 全局引用（10^7 次）
>>> import timeit
>>> timeit.timeit(local, number=100)      # 0.31
>>> timeit.timeit(global_, number=100)    # 0.39（慢 ~25%）
# 3.11+ 的 LOAD_GLOBAL 有内联缓存，差距缩小，但仍存在
```

> **实战建议**：**循环内引用的名字尽量局部化**——`GLOBAL` 在循环外 `g = GLOBAL` 再循环内用 `g`。3.11+ 特化解释器（15.4.6）已经大幅缩小差距，但"循环内用局部名"仍是免费的好习惯。

### 15.4.3 避免属性链与方法查找

```python
# ❌ 循环内重复属性链（每次迭代多次 LOAD_ATTR）
for item in items:
    result = item.get_value().compute()      # 多次 LOAD_ATTR + 调用

# ✅ 局部绑定（方法查找一次）
get_value = obj.get_value                   # 循环外绑定
compute = obj.compute
for item in items:
    result = get_value().compute()          # 还是链……继续优化：
```

```python
# 完整优化：属性和方法都局部化
def process(items, processor):
    do = processor.compute                   # 方法绑定一次（15.4.3）
    result = []
    append = result.append                   # 方法绑定（list.append 查找一次）
    for item in items:
        append(do(item))                     # 循环内零属性查找
    return result
```

```python
# 实测（10^5 次属性访问）：
>>> class A: 
...     def __init__(self): self.x = 1
...     def get(self): return self.x
>>> a = A()
>>> timeit.timeit(lambda: a.get(), number=1_000_000)      # 0.11（属性链+调用）
>>> g = a.get
>>> timeit.timeit(lambda: g(), number=1_000_000)          # 0.06（绑定方法，快一半）
```

> **⚠️ 陷阱**：方法局部绑定有代价——**绑定的是"那一刻"的方法**（若对象方法被替换/对象状态变化，绑定失效）。只在**热循环**里做此优化，且确保方法不依赖动态状态（如 `self.x` 每次变——方法内读属性没问题，绑定的是方法对象不是结果）。

### 15.4.4 字符串 / 列表 / 字典技巧

```python
# 字符串：join 永远胜过 += 循环（C 实现 vs 反复分配）
# ❌ 0.35s（10^5 次拼接，每次创建新字符串）
s = ""
for x in parts:
    s += x
# ✅ 0.01s（一次 C 循环 + 一次分配）
s = "".join(parts)

# 列表：预分配 vs append（差异小，3.11+ 更小；保持可读性用 append）
# 字典：get 比 in + 索引快（一次查找 vs 两次）
d = {"a": 1}
# ❌ 两次查找
if "a" in d: v = d["a"]
# ✅ 一次查找（还处理缺失）
v = d.get("a", 0)

# 集合：去重/成员判断用 set 而非 list（15.3.1 已述）
```

> **实战建议**：**字符串拼接用 `join`** 是收益最大、最无脑的语言级优化（10–30 倍）。其他技巧（预分配、get）收益小——**优先可读性**，只有剖析证实是热点才用。**不要为了 5% 的收益牺牲可读性**——这条线要守住。

### 15.4.5 内置函数优先

```python
# 内置函数/方法的 C 实现 vs 手写 Python 循环：
# 1. sum / max / min / any / all —— C 循环
# 2. map / filter —— C 驱动迭代（配合 C 函数）
# 3. list.sort / sorted —— Timsort（C）
# 4. itertools 全家（回顾 13.3）—— C 实现

# ❌ 手写（每次迭代都是 Python 字节码）
total = 0
for x in data: total += x
# ✅ sum（C 循环）
total = sum(data)

# ❌ 手写过滤
filtered = [x for x in data if x > 0]     # 推导式（Python 循环，但优化良好）
# ✅ map + C 函数（如 str.upper 的 C 实现）
uppers = list(map(str.upper, words))      # map 驱动 C 方法
```

> **🔑 机制洞察**：`map(str.upper, words)` 快的原因是**迭代在 C 层驱动**（`map` 对象的 `__next__` 是 C 函数，每次回调 `str.upper` 的 C 方法）——对比推导式（每次迭代都要跑 Python 字节码）。但推导式在 3.11+ 也很快（特化），**可读性优先**：`[x.upper() for x in words]` 通常已经够快，`map` 是"剖析证实热点"时的选项。

#### 推导式 vs 循环 vs map：字节码与实测

```python
# 三种写法（语义相同）
def loop_append(xs):
    result = []
    for x in xs:
        result.append(x * 2)
    return result

def comp(xs):
    return [x * 2 for x in xs]

def map_lambda(xs):
    return list(map(lambda x: x * 2, xs))      # lambda 仍是 Python 调用
```

```python
# 实测（10^6 元素）：
# loop_append：  ~85ms
# comp：         ~60ms（推导式有专门优化：LIST_APPEND 指令 + 无属性查找）
# map+lambda：   ~70ms（lambda 拖后腿；map 配 C 函数才快）
```

> **🔑 性能洞察**：**列表推导式是"手写循环 + append"的免费优化**（专门字节码 `LIST_APPEND`、避免每次 `result.append` 的属性查找）——**能用推导式就用推导式**，它同时更快更短。`map` 只有配**C 函数**（`map(str.upper, ...)`）才划算；配 `lambda` 反而慢。这条规律在 3.11+ 仍成立（推导式享受特化，lambda 的调用开销依旧）。

### 15.4.6 版本演进：3.11+ 特化解释器（🔑 版本演进）

**PEP 659（2022，3.11）**：自适应特化解释器——**CPython 首次引入"运行时学习热点并特化指令"**：

```
3.10：LOAD_GLOBAL 每次都是完整字典查找（通用路径）
3.11：第一次执行时记录类型/缓存索引；
     之后命中缓存 → 直接数组索引（跳过字典查找）
     观察类型 → 特化出 LOAD_GLOBAL_MODULE / LOAD_GLOBAL_BUILTIN 等专用指令
```

```python
# 效果：3.11 比 3.10 快 25–60%（官方基准），部分热点快 2 倍
# 后续版本：
# 3.12：内联缓存扩展到更多指令；"零开销"异常
# 3.13：增量 GC、指令更小
# 3.14：继续特化（如二进制运算的优化）
```

> **版本注意**：**升级 Python 版本是最便宜的优化**——3.10 → 3.11 白拿 30%+，零代码改动。特化解释器的原理（PEP 659）值得了解：它不是 JIT（不做机器码），而是"**热点指令的运行时特化**"——观察类型、缓存结果、生成专用路径。它与 15.6 的 PyPy（真 JIT）是两条不同的加速路线。

---

## 15.5 向量化与 numpy 预告

### 15.5.1 为什么 numpy 快

```python
import numpy as np

# 同一任务：纯 Python vs numpy
def py_sum_squares(data):
    return sum(x * x for x in data)          # Python 循环

data = list(range(1_000_000))
arr = np.array(data, dtype=np.float64)

>>> %timeit py_sum_squares(data)             # ~70ms
>>> %timeit (arr * arr).sum()                # ~1ms —— 快 70 倍
```

**numpy 快的三个机制**：

| 机制 | 说明 |
|------|------|
| **C 循环** | `arr * arr` 是 C 层循环（不解释 Python 字节码） |
| **连续内存** | ndarray 是**连续内存块**（对比 Python list 的对象数组，第 13 章 array 提过）——缓存友好 |
| **SIMD/BLAS** | 底层可用 CPU 向量指令（SIMD）与高度优化的 BLAS 库（矩阵运算） |

```python
# 向量化思维：把"对每个元素操作"变成"对整个数组操作"
# ❌ 循环式（Python 层每次迭代）
result = [math.sqrt(x) for x in data]
# ✅ 向量式（C 层一次处理整个数组）
result = np.sqrt(np.array(data))
```

> **🔑 机制洞察**：numpy 的本质是"**把 Python 循环下沉到 C**"——`arr * arr` 不产生 Python 级循环。这就是为什么"数值计算用 numpy"是性能铁律：**同样 O(n) 的算法，numpy 把 n 次 Python 迭代变成 1 次 C 调用**（收益与 15.4.1 的 `sum` 同源，但规模更大）。numpy 的完整心智模型（ndarray/广播/视图/内存布局）是**卷 2 第 1 章（`ds-01-numpy.md`）**的主题。

### 15.5.2 向量化思维预览

```python
import numpy as np

# 示例：把"每个元素按条件变换"写成向量式
prices = np.array([100.0, 200.0, 50.0])
# ❌ 循环 + 条件
discounted = np.array([p * 0.9 if p > 80 else p for p in prices])
# ✅ 向量化（布尔掩码——广播概念的入门）
discounted = np.where(prices > 80, prices * 0.9, prices)
```

> **实战建议**：向量化的心智转换是卷 2 的核心训练——本章只需要记住"**数组运算替代循环**"的方向。日常 Python 里没有 numpy 时，"向量化"的替代品是内置函数 + `itertools`（15.4.5）——**都是"把 Python 循环移到 C"**。

---

## 15.6 JIT 与替代执行引擎

### 15.6.1 PyPy：JIT 解释器

**PyPy** 是 CPython 的 JIT 替代实现（Python 写解释器 + JIT 编译热点为机器码）：

```python
# PyPy 适合：长循环、热点稳定、数值/算法密集的纯 Python
# 不适合：C 扩展依赖（numpy/pandas 兼容性差）、启动慢、内存高
# 典型加速：纯 Python 算法 2–10 倍
```

| 维度 | CPython | PyPy |
|------|---------|------|
| 执行模型 | 解释字节码（3.11+ 特化） | **JIT 编译热点为机器码** |
| 纯 Python 性能 | 基准 | 通常 2–10 倍 |
| C 扩展 | ✅ 全兼容 | ⚠️ 需 cpyext 兼容层（慢/部分） |
| 启动/内存 | 快/省 | 慢/高 |
| 适用 | 通用 | 纯 Python 计算密集（无 C 依赖） |

> **⚠️ 陷阱**：PyPy 的 JIT 需要"**热点够热**"才见效——一次性脚本、IO 密集任务没有收益；且 C 扩展生态（numpy/torch）是硬伤。**用 PyPy 前先问：我的慢是纯 Python 计算吗？** 是 → PyPy 值得试；否（IO/C 扩展）→ 没意义。

### 15.6.2 numba：数值 JIT

**numba**（`pip install numba`）用 LLVM 把**带类型的 Python 函数**编译为机器码：

```python
import numba
import numpy as np

@numba.jit(nopython=True)          # nopython：不退回 Python，编译失败会报错
def sum_squares(arr):
    total = 0.0
    for i in range(arr.shape[0]):  # 支持 numpy 数组的循环！
        total += arr[i] ** 2
    return total

arr = np.arange(1_000_000, dtype=np.float64)
# 首次调用触发编译（慢），之后是机器码（快）
# 实测：纯 Python 循环 ~80ms → numba ~1ms（80 倍）
```

> **实战建议**：**numba 是"不想写 C 的数值加速"的最佳折中**——给纯数值函数加 `@jit(nopython=True)`，语法仍是 Python。限制：只支持数值子集（numpy 运算/循环），不能无限制调 Python 对象（list/dict 受限）。路线：**先 numpy 向量化（15.5），向量化不了的循环再用 numba**——两者组合覆盖 90% 的数值加速需求。

#### numba 实战细节

```python
import numba
import numpy as np

# 1. 首次调用编译（慢，几秒），之后用缓存（fastmath 可放宽浮点语义换速度）
@numba.jit(nopython=True, cache=True, fastmath=True)
def mandelbrot(creal, cimag, max_iter):
    zr, zi = 0.0, 0.0
    for i in range(max_iter):
        zr, zi = zr*zr - zi*zi + creal, 2*zr*zi + cimag
        if zr*zr + zi*zi > 4:
            return i
    return max_iter

# 2. 并行：prange 让循环多核执行（比 15.6.2 更进一步）
@numba.jit(nopython=True, parallel=True)
def parallel_sum(arr):
    total = 0.0
    for i in numba.prange(arr.shape[0]):     # prange：并行循环
        total += arr[i] ** 2
    return total
```

| 选项 | 作用 |
|------|------|
| `nopython=True` | 禁止退回 Python（编译失败会报错——保证真的是机器码） |
| `cache=True` | 编译结果落盘（重启不重编） |
| `fastmath=True` | 放宽 IEEE 浮点语义（快，但结果可能微差） |
| `parallel=True` + `prange` | 循环自动多核并行 |

> **⚠️ 陷阱**：numba 的 **"编译期类型推断失败"** 是最常见报错——函数里混了不支持的类型/操作（如调任意 Python 函数）会退回或报错。规则：**numba 函数保持"纯数值 + numpy 运算"**（类型简单、无副作用）。第一次调用慢是编译（`cache=True` 后只慢一次）——基准测试要"预热"后再测（与 14.9 的 timeit 姿势一致）。

### 15.6.3 决策：什么时候值得换执行引擎

| 场景 | 推荐 | 理由 |
|------|------|------|
| 纯 Python 算法慢 | 先优化算法（15.3）→ PyPy | 最便宜 |
| 数值计算慢 | numpy 向量化（15.5）→ numba | C 层循环 |
| 需要调现成 C 库 | ctypes（15.7） | 零编译 |
| 极致性能/定制 | C 扩展（15.8）/ Cython（15.9） | 完全控制 |
| IO 密集慢 | 并发（第 11 章）！ | 不是 CPU 问题 |

> **工程影响**：执行引擎的选择**最后做**——前五层杠杆（算法→语言级→numpy→numba→PyPy）都试过还慢，才到 C 层。**换引擎有兼容性成本**（PyPy 的 C 扩展、numba 的类型限制），收益必须大于迁移成本。**"Python 慢就换 Go/Rust"是最后的选择**——先用尽 Python 生态的五层杠杆，多数场景根本到不了那一步。

---

## 15.7 ctypes：调用现成的 C 库

`ctypes`（标准库）让 Python **直接调用 C 共享库中的函数**——零编译、零第三方依赖，是"我有现成 .dll/.so，想用 Python 调"的默认答案。

### 15.7.1 ctypes 基础

```python
import ctypes

# 加载 C 标准库（跨平台）
if sys.platform == "win32":
    libc = ctypes.CDLL("msvcrt")          # Windows 的 C 运行时
else:
    libc = ctypes.CDLL(None)              # Linux/macOS：主程序符号表

# 声明参数与返回类型（⚠️ 必须！否则是未定义行为）
libc.strlen.argtypes = [ctypes.c_char_p]  # 参数：char*
libc.strlen.restype = ctypes.c_size_t     # 返回：size_t

>>> libc.strlen(b"hello")
5
```

> **⚠️ 陷阱（argtypes/restype 必须声明）**：ctypes 默认假设参数是 `c_int`、返回是 `c_int`——**不声明 `argtypes`/`restype` 时传指针/浮点/64 位值是未定义行为**（可能崩溃、返回垃圾值）。规则：**调用任何 C 函数前，先声明完整的 `argtypes` 和 `restype`**——这是 ctypes 的第一纪律。

### 15.7.2 结构体与指针

```python
import ctypes

# 声明 C 结构体
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

p = Point(1.5, 2.5)
p.x, p.y                # (1.5, 2.5) —— 属性访问！内存布局与 C 一致

# 指针与缓冲
libc.qsort.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                       ctypes.c_size_t, ctypes.c_void_p]
buf = (ctypes.c_int * 5)(5, 3, 1, 4, 2)    # 定长数组（连续内存）
ctypes.byref(buf)                            # byref：传地址（比 pointer 轻）
```

```python
# 完整示例：用 C 的 qsort 排序（对比 Python 的 sorted——展示"调 C"）
import ctypes

libc.qsort.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t,
                       ctypes.c_void_p]

# 比较函数回调（ctypes 支持 C 函数指针！）
def cmp_func(a, b):
    a = ctypes.cast(a, ctypes.POINTER(ctypes.c_int)).contents.value
    b = ctypes.cast(b, ctypes.POINTER(ctypes.c_int)).contents.value
    return (a > b) - (a < b)

CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

arr = (ctypes.c_int * 5)(5, 3, 1, 4, 2)
libc.qsort(arr, 5, ctypes.sizeof(ctypes.c_int), CMPFUNC(cmp_func))
list(arr)               # [1, 2, 3, 4, 5] —— 用 C 的 qsort 排好了
```

### 15.7.3 性能与陷阱

**性能**：`ctypes` 调用有**固定开销**（约 1µs/次——类型转换 + C 调用）：

```python
# 小函数频繁调用：ctypes 开销 > 收益
# ❌ 循环里调 C 的 abs（每次 ~1µs 开销，比 Python 内置 abs 还慢）
# ✅ 大计算量才划算：一次调用干大量活（如 C 库处理整个数组）
```

| 陷阱 | 说明 |
|------|------|
| 未声明 argtypes/restype | 未定义行为（崩溃/垃圾值） |
| **GIL** | ctypes 调用**默认持有 GIL**——CPU 密集 C 函数会卡住其他线程（用 15.8.4 的 C 扩展可释放） |
| **内存安全** | C 代码崩溃（段错误）= Python 进程崩溃（无法捕获！） |
| 平台差异 | DLL/so 名、调用约定（`WinDLL` vs `CDLL`）、32/64 位 |
| 指针生命周期 | C 保存的指针可能悬垂（Python 对象被回收） |

> **实战建议**：`ctypes` 的定位——**"快速调用现成 C 库"（不写编译代码）**。场景：调系统库（`libc`/`zlib`/`ffmpeg` 等）、封装某个 C API。它**不是**性能工具的首选（调用开销 + GIL），要"真正快的 Python 扩展"用 15.8 的 C API 或 15.9 的 Cython。三者对比：**ctypes（零编译/慢调用）、CFFI（编译绑定/快）、C API（手写 C/最快）**。

---

## 15.8 Python C API：写真正的扩展模块

ctypes 是"调用别人的 C"，C API 是"**写自己的 C 扩展**"——把性能热点用 C 实现、编译成 `.pyd`/`.so`，Python 直接 `import`。这是 numpy/pandas 等一切高性能库的根基。

### 15.8.1 扩展模块骨架

```c
// mymath.c —— 一个最小扩展：提供 mymath.add(a, b)
#define PY_SSIZE_T_CLEAN
#include <Python.h>

// 1. 实现函数：接收 PyObject*（Python 对象），返回 PyObject*
static PyObject *
mymath_add(PyObject *self, PyObject *args) {
    long a, b;
    if (!PyArg_ParseTuple(args, "ll", &a, &b))   // 解析两个 long
        return NULL;                             // 解析失败：设置异常并返回 NULL
    long result = a + b;
    return PyLong_FromLong(result);              // 包装成 Python int
}

// 2. 方法表：函数名 → C 函数 的映射
static PyMethodDef mymath_methods[] = {
    {"add", mymath_add, METH_VARARGS, "Return a + b."},
    {NULL, NULL, 0, NULL}                        // 哨兵结尾
};

// 3. 模块定义
static struct PyModuleDef mymath_module = {
    PyModuleDef_HEAD_INIT,
    "mymath",                                    // 模块名
    "A minimal C extension.",                    // 文档
    -1,                                          // 模块状态（-1：全局）
    mymath_methods
};

// 4. 初始化函数：PyInit_<模块名>
PyMODINIT_FUNC
PyInit_mymath(void) {
    return PyModule_Create(&mymath_module);
}
```

```python
# 使用：import mymath（编译后）
>>> import mymath
>>> mymath.add(3, 4)
7
```

> **🔑 机制洞察**：C 扩展的本质是"**Python 对象的 C 层工厂**"——每个 Python 值在 C 里都是 `PyObject*`（第 3 章：一切皆对象在 C 层的体现）。C 函数接收 `PyObject*`、返回 `PyObject*`，中间用 C API（`PyArg_ParseTuple`/`PyLong_FromLong`）做转换。**性能收益**：`mymath.add` 没有字节码解释、没有动态分派——纯 C 执行。

### 15.8.2 引用计数与内存管理（🔑 机制洞察）

**C 层的引用计数就是 GIL 存在的根源**（回顾 11.1.3）——扩展作者必须遵守引用纪律：

```c
// 引用计数规则：每个 PyObject* 要么"拥有"要么"借用"
PyObject *obj = PyLong_FromLong(42);   // ① 新引用：我拥有它
Py_DECREF(obj);                        // 用完必须释放！否则泄漏

// ② 借用引用：PyDict_GetItem 等返回"借用的"——不能 DECREF！
PyObject *value = PyDict_GetItem(dict, key);   // 借用：dict 还持有它
// ⚠️ 错误：Py_DECREF(value) 会破坏 dict 的引用计数！

// ③ 借转拥：Py_INCREF(value) 后我就拥有了
Py_INCREF(value);                      // 现在我也拥有，可以安全持有

// 错误处理：返回 NULL 前，已持有的引用要清理（goto error 模式）
```

> **🔑 机制洞察**：C 扩展的**头号 bug 是引用计数错误**——多 `DECREF` 导致悬垂指针（崩溃/内存损坏），少 `DECREF` 导致泄漏。规则：**"新引用"（From/New 系列）必须 DECREF；"借用引用"（Get/Steal 之外）绝不 DECREF**。CPython 的 `Py_DEBUG` 构建（`--with-pydebug`）会检测引用计数错误——**调试 C 扩展用 debug 版 Python**。

### 15.8.3 参数解析与返回

```c
// PyArg_ParseTuple：解析位置参数
static PyObject *
func(PyObject *self, PyObject *args) {
    const char *name; long count;
    if (!PyArg_ParseTuple(args, "sl", &name, &count))   // s=str, l=long
        return NULL;
    // 返回元组
    return Py_BuildValue("(sl)", name, count);           // 包装成 (str, int)
}

// 关键字参数版本
static PyObject *
func_kw(PyObject *self, PyObject *args, PyObject *kwargs) {
    long a = 0, b = 0;
    static char *kwlist[] = {"a", "b", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|ll", kwlist, &a, &b))
        return NULL;
    ...
}
// 方法表里注册：METH_VARARGS | METH_KEYWORDS
```

| C API | 作用 |
|-------|------|
| `PyArg_ParseTuple` / `ParseTupleAndKeywords` | 参数解析（格式串 `"sl|d"` 等） |
| `Py_BuildValue` | 结果包装（格式串同源） |
| `PyLong_FromLong` / `PyFloat_FromDouble` | 数值构造 |
| `PyUnicode_FromString` | 字符串构造 |
| `PyErr_SetString` / `PyErr_Format` | 设置异常（返回 NULL 前调用） |

#### 定义新类型：PyTypeObject（进阶）

函数级扩展（`mymath.add`）只覆盖了"函数"。要定义**新类型**（像 `list`/`dict` 那样的 C 级对象，如 numpy 的 `ndarray`），需要 `PyTypeObject`：

```c
// 对象结构体：PyObject_HEAD + 自定义字段
typedef struct {
    PyObject_HEAD
    double value;                // 字段直接用 C 类型（无 Python 对象开销）
} MyNumber;

// 类型对象
static PyTypeObject MyNumberType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "mymath.MyNumber",
    .tp_basicsize = sizeof(MyNumber),
    .tp_new = MyNumber_new,      // 创建（分配 + 初始化）
    .tp_dealloc = MyNumber_dealloc,
    .tp_repr = MyNumber_repr,
    .tp_methods = MyNumber_methods,   // 方法表
    .tp_flags = Py_TPFLAGS_DEFAULT,
};

// 初始化：注册进模块
PyMODINIT_FUNC PyInit_mymath(void) {
    PyObject *m = PyModule_Create(&mymath_module);
    if (PyType_Ready(&MyNumberType) < 0) return NULL;
    Py_INCREF(&MyNumberType);
    PyModule_AddObject(m, "MyNumber", (PyObject *)&MyNumberType);
    return m;
}
```

```python
>>> import mymath
>>> n = mymath.MyNumber(3.14)
>>> n.value                      # C 级字段（直读内存，快）
3.14
```

> **🔑 机制洞察**：`PyTypeObject` 就是第 7 章"类"的 C 层实现——`tp_new`/`tp_repr`/`tp_methods` 对应 `__new__`/`__repr__`/方法表，`tp_basicsize` 决定实例内存布局。**C 类型 vs Python 类的性能差异**：C 类型字段是**结构体直接内存**（`n.value` 一条指令），Python 类字段是 `__dict__` 字典查找（多条指令 + 描述符链，12.4.1）。这就是"为什么 numpy 的对象比 Python 类对象快"的底层答案。自定义类型是 C 扩展的进阶领域——**多数扩展只需要函数级**（15.8.1），需要"像内置类型一样高效的对象"才上 `PyTypeObject`。

### 15.8.4 GIL 释放与并行（衔接第 11 章）

**C 扩展最大的性能杀手是"拿着 GIL 做 CPU 计算"**——释放它，多线程就能真并行（回顾 11.1.3 的 C 扩展可释放 GIL）：

```c
// 释放 GIL 做重计算（前提：这段代码不碰 Python API！）
static PyObject *
heavy_compute(PyObject *self, PyObject *args) {
    long n;
    if (!PyArg_ParseTuple(args, "l", &n))
        return NULL;

    Py_BEGIN_ALLOW_THREADS           // 释放 GIL（其他线程可以跑 Python）
    // ... 纯 C 计算（不能调任何 Python API，不能碰 PyObject*）...
    double result = 0;
    for (long i = 0; i < n; i++) result += sqrt((double)i);
    Py_END_ALLOW_THREADS             // 重新获取 GIL

    return PyFloat_FromDouble(result);
}
```

```python
# 效果：释放 GIL 的 C 扩展 + 多线程 = 真并行
# 对比（回顾 11.1.3）：纯 Python 的 CPU 任务多线程 ≈ 无加速
#               释放 GIL 的 C 扩展 + 4 线程 ≈ 4 核并行加速
```

> **🔑 机制洞察**：`Py_BEGIN_ALLOW_THREADS` 是 15.1 解释器模型与 11.1.3 GIL 的汇合点——**C 代码是唯一能"摆脱 GIL"的途径**（Python 字节码永远受 GIL 约束）。numpy 的大矩阵运算、hashlib 的哈希都释放 GIL——这就是为什么"numpy + 多线程"能并行而"纯 Python + 多线程"不能。

### 15.8.5 构建配置

```toml
# pyproject.toml（回顾第 10 章 PEP 517/518 的实战）
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mymath"
version = "0.1.0"

[tool.setuptools]
packages = ["mymath"]

# 扩展模块：指定 C 源码
[tool.setuptools.ext-modules]
"mymath._core" = {sources = ["src/mymath/_core.c"]}
```

```bash
$ pip install -e .        # 编译 C 扩展（需要编译工具链：MSVC / gcc）
$ python -c "import mymath._core; print(mymath._core.add(1, 2))"
3
```

> **⚠️ 陷阱**：
> - **ABI 兼容**：编译出的扩展绑定具体 CPython 版本（`cp314` 标签，回顾第 10 章 wheel）——发布给用户需要**每版本都编译**或使用**稳定 ABI**（`abi3`，`Py_LIMITED_API`）；
> - 平台差异：Windows 用 MSVC、Linux 用 gcc、macOS 用 clang——**CI 多平台编译**是常态；
> - 调试：`Py_DEBUG` 构建 + `faulthandler`（14.7.3）定位 C 崩溃。

---

## 15.9 Cython：Python 的 C 方言

手写 C API（15.8）太繁琐（引用计数、PyArg 解析全是样板）。**Cython** 是"Python 超集 + 类型声明"——合法的 Python 代码加上类型标注，编译成 C 扩展。**写法像 Python，速度接近 C**。

### 15.9.1 Cython 是什么

```
.pyx 文件（Cython 代码，Python 超集）
   → Cython 编译器（cythonize）→ 生成 .c
   → C 编译器（gcc/MSVC）→ 生成 .pyd/.so
   → Python import 使用
```

```python
# mathlib.pyx —— 合法 Python + Cython 类型声明
def py_sum(n):
    """纯 Python 版本（Cython 直接支持 Python 语法）"""
    total = 0
    for i in range(n):
        total += i
    return total

def cy_sum(long n):                # 参数类型化
    cdef long total = 0            # cdef：C 类型局部变量（无 Python 对象开销）
    cdef long i
    for i in range(n):
        total += i
    return total
```

```python
# 使用：import 即可（编译后）
>>> import mathlib
>>> mathlib.cy_sum(10_000_000)     # C 循环（快）
>>> mathlib.py_sum(10_000_000)     # Python 循环（慢）
```

### 15.9.2 类型标注加速

| Cython 语法 | 含义 | 收益 |
|------------|------|------|
| `cdef long x` | C 类型局部变量 | 无装箱/无 Python 对象 |
| `cdef int foo(int x)` | C 函数（Python 不可见） | 纯 C 调用 |
| `cpdef int foo(int x)` | 双接口（Python + C 都可调） | 兼顾 |
| `def foo(long n)` | 参数类型化 | 少一次解析转换 |
| `cdef class` | C 级类（类似 `__slots__` 的极致） | 紧凑内存 |

```python
# 性能对比（同一求和任务，10^7）：
# 纯 Python：            ~0.45s
# Cython 类型化（cdef）： ~0.01s —— 45 倍
# 手写 C 扩展：           ~0.008s —— 接近（Cython 只差一点）
```

> **🔑 性能数据**：Cython 的加速**来自类型化消除 Python 开销**——`cdef long total` 让循环变量是 C 的 `long`（寄存器/栈），`range` 循环是 C 循环；而纯 Python 的 `total += i` 每次都是"取对象 → 拆箱 → 相加 → 装箱 → 存回"。**同一段逻辑，换类型声明，速度从 Python 级跳到 C 级**——这是 Cython 的核心价值。

### 15.9.3 与 C 交互

```python
# cdef extern：直接声明并调用 C 函数/头文件
cdef extern from "math.h":
    double sqrt(double x)          # 声明 C 函数

def c_sqrt(double x):
    return sqrt(x)                 # 直接调 C 的 sqrt（无 Python 包装）
```

```python
# 完整实战：Cython 封装 C 库
# cdef extern from "zlib.h":
#     int compress(...)            # 声明 zlib 的函数
# 之后 Python 里就能用（类型化调用，比 ctypes 快）
```

> **实战建议**：Cython 的定位——**"想写 C 扩展但不想手写 C API"**的默认选择。路线：纯 Python 先跑通 → 加 `cdef` 类型声明 → 热点函数 `cpdef` → 需要时 `cdef extern` 调 C 库。**Cython 与 numpy 配合**（`@cython.boundscheck(False)` 等）是科学计算扩展的标准组合。

#### Cython 与 numpy 配合

```python
# cython_np.pyx —— 科学计算扩展的标准写法
import numpy as np
cimport numpy as cnp
cimport cython

@cython.boundscheck(False)        # 关闭边界检查（快，但越界是 UB——自己保证）
@cython.wraparound(False)         # 关闭负索引支持
def dot_product(cnp.ndarray[cnp.float64_t, ndim=1] a,
                cnp.ndarray[cnp.float64_t, ndim=1] b):
    """C 级循环的点积（对比 numpy 的 a @ b——循环型算法用）"""
    cdef Py_ssize_t i, n = a.shape[0]
    cdef double total = 0.0
    for i in range(n):
        total += a[i] * b[i]      # C 层数组访问（无 Python 对象）
    return total
```

| Cython 指令 | 作用 | 代价 |
|------------|------|------|
| `cimport numpy` | 引入 numpy 的 C 接口 | 需 `numpy` 头文件 |
| `boundscheck(False)` | 关边界检查 | 越界=未定义行为（快 ~20%） |
| `wraparound(False)` | 关负索引 | `a[-1]` 变 UB（快） |
| `ndarray[double, ndim=1]` | 声明一维 double 数组 | 访问走 C 指针 |

> **实战建议**：Cython + numpy 的定位——**"numpy 向量化写不了（算法需要逐元素分支/循环）时的 C 级实现"**。标准库路线：numpy 向量化（15.5）→ 循环型算法 numba（15.6）→ 需要完整集成/发布时 Cython（15.9）。Cython 相对 numba 的优势：**可发布为真正的扩展包**（`pip install` 即得，不依赖运行时 JIT）、可自由混用 C 库。

### 15.9.4 性能对比总表（🔑 性能数据）

同一任务（10^7 次累加）的完整对比：

| 方案 | 耗时 | 相对纯 Python | 开发成本 |
|------|------|--------------|---------|
| 纯 Python 循环 | 0.45s | 1x | 零 |
| Python + `sum()` | 0.12s | 3.8x | 零（一行） |
| numpy 向量化 | 0.004s | **112x** | 低 |
| numba `@jit` | 0.001s | **450x** | 低（加装饰器） |
| Cython（cdef） | 0.010s | 45x | 中（类型化改写） |
| 手写 C 扩展 | 0.008s | 56x | 高（C API 样板） |

> **工程影响**：**路线图结论**——(1) 先 `sum`/内置函数（零成本 4 倍）；(2) 数值问题上 numpy（百倍）；(3) 循环型热点用 numba（百倍+）；(4) Cython 做"完整功能扩展"；(5) 手写 C 只在"极致 + 频繁"时。**不要一上来就写 C**——上面每一层都可能已经够快。这张表就是 15.1.2 路线图的实测注脚。

---

## 15.10 优化工程实践与卷 1 收官

### 15.10.1 优化流程总纲

把全章串成可执行的流程：

```
① 确认值得优化（15.1.3：用户可见/高频/已发生）
② 剖析定位（15.2：cProfile 找函数 → line_profiler 找行）
③ 算法审查（15.3：复杂度是第一杠杆——先改数据结构）
④ 语言级改写（15.4：内置函数/局部化/join——只改热点）
⑤ 向量化/JIT（15.5/15.6：numpy → numba → PyPy）
⑥ C 层（15.7/15.8/15.9：ctypes → Cython → C API——最后手段）
⑦ 复测 + 回归（timeit 对比、pytest-benchmark、性能门禁）
```

```python
# 每一步的验证姿势（第 14 章闭环）：
import timeit

before = min(timeit.repeat(old_func, number=100, repeat=7))
after = min(timeit.repeat(new_func, number=100, repeat=7))
print(f"{before:.4f}s → {after:.4f}s ({before/after:.1f}x)")
# 改完必须重测：不验证的优化是猜测
```

> **工程影响**：**优化是迭代过程，不是一次动作**——每层杠杆做完都重测，够快就停。保留 `before/after` 基准记录（写进注释或 benchmark 文件），未来回归可查。**优化的正确性是第一位的**：先跑第 14 章的测试套件确认功能没坏，再看性能数字。

### 15.10.2 性能回归与 CI

```python
# pytest-benchmark：基准入库 + 历史对比（回顾 15.2.4）
def test_key_path_bench(benchmark):
    benchmark(process_1m_rows, sample_data)

# CI 流程：
# 1. 功能测试（第 14 章）—— 正确性门禁
# 2. 覆盖率门禁（14.6）—— 质量门禁
# 3. 基准对比（benchmark --compare）—— 性能门禁（回退超阈值即失败）
# 4. 警告升级（14.8.3 -W error）—— 前瞻门禁
```

> **实战建议**：**性能门禁要"宽松而持续"**——CI 机器抖动大，阈值卡太紧会天天误报（团队开始忽略）。策略：**宽松阈值（20–30%）挡住"明显回退"，定期人工看趋势图**。性能问题最怕的是"温水煮青蛙"（每天慢 0.5% 没人发现，半年后慢一倍）——趋势监控比阈值拦截更重要。

### 15.10.3 卷 1 全景收官（🔑 实战模式）

15 章走完，把整卷串成一张能力地图：

| 板块 | 章节 | 核心能力 |
|------|------|---------|
| 语言核心 | 1–5 | 语法、类型、运算符、控制流、迭代器——**地基** |
| 抽象与工程 | 6–9 | 函数、对象、异常、IO——**写复杂系统** |
| 系统能力 | 10–14 | 模块、并发、元编程、标准库、测试调试——**工程化** |
| 性能极限 | 15 | 剖析、算法、向量化、C 层——**榨干性能** |

```python
# 卷 1 的"毕业自测"——能独立回答的问题：
# 1. `a = [1]; b = a; b.append(2)` 后 a 是什么？（2 章引用语义）
# 2. `__getattr__` 和 `__getattribute__` 的触发时机？（12 章）
# 3. GIL 为什么存在、何时释放？（11 章）
# 4. `x += 1` 为什么多线程不安全？（11 章字节码）
# 5. pytest 的 assert 重写用了哪个 import 钩子？（10 章 + 14 章）
# 6. 一个慢循环，五层优化杠杆的顺序？（15 章）
```

**卷 2–5 的入口**：语言核心已备齐，接下来按方向选择——

| 方向 | 路径 |
|------|------|
| 数据分析 | 卷 2（numpy → pandas → matplotlib → scipy） |
| 机器学习 | 卷 2 → 卷 3（sklearn 生态） |
| 深度学习 | 卷 2 → 卷 3 → 卷 4（PyTorch） |
| LLM 应用 | 卷 2 → 卷 5（tokenization/提示工程/RAG/Agent） |

> **收官寄语**：卷 1 的目标不是"背 API"，而是建立**"底层原理 > 最佳实践 > 实战练习"的心智**——现在你知道了 `@dataclass` 怎么工作、GIL 为什么存在、`import` 背后是什么、numpy 为什么快。带着这套"看穿表象"的能力进入卷 2–5，你会发现：**任何框架（numpy/sklearn/PyTorch）都是"卷 1 的机制 + 领域知识"的组合**。卷 2 见。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 为什么慢 | 解释器字节码循环 + 动态分派 + 装箱 + 属性查找；"每条操作都贵" |
| 优化路线图 | 算法 > 语言级 > 向量化 > JIT > C 层（收益递减、成本递增）；先剖析再优化 |
| 剖析 | cProfile（函数级/pstats）/ line_profiler（行级）/ tracemalloc（内存）/ gc + objgraph（泄漏）/ pytest-benchmark |
| 算法层 | 复杂度是第一杠杆（O(n²)→O(n) 260 倍实测）；lru_cache 缓存；惰性 + 批量 |
| 语言级 | 内置函数优先（C 循环）；局部变量（LOAD_FAST）；方法绑定；`join`；3.11+ 特化解释器（PEP 659） |
| 向量化 | numpy 快在 C 循环 + 连续内存 + SIMD；"数组运算替代循环"（卷 2 细讲） |
| JIT | PyPy（纯 Python 热点）/ numba（数值 `@jit`）；先试前五层再换引擎 |
| ctypes | 调现成 C 库零编译；**argtypes/restype 必声明**；~1µs 调用开销；GIL 不释放 |
| C API | PyObject* 世界；**引用计数纪律**（新引用 DECREF/借用不 DECREF）；释放 GIL（`Py_BEGIN_ALLOW_THREADS`）= 真并行；setuptools 编译 |
| Cython | Python 超集 + 类型化；`cdef` 变量/函数；45x 实测；与 C 交互 `cdef extern` |
| 工程实践 | 流程（剖析→算法→语言级→向量化→JIT→C→复测）；性能回归门禁；趋势 > 阈值 |
| 卷 1 收官 | 15 章能力地图；"任何框架 = 卷 1 机制 + 领域知识" |

---

#### 练习 15

**第 1–3 题：验证理解（预测/解释）**

1. 解释："Python 慢"的三个开销来源（动态分派/装箱/属性查找）分别对应哪种代码写法？`sum(xs)` 为什么比手写循环快（字节码层面）？

2. 预测并解释：3.10 vs 3.11 运行同一段纯 Python 循环，谁快？为什么（PEP 659 的机制）？升级 Python 版本算"免费优化"吗？

3. 判断：ctypes 调用 C 的 `strlen` 不声明 `argtypes`/`restype` 会怎样？C 扩展里 `Py_DECREF` 一个"借用引用"会怎样？`Py_BEGIN_ALLOW_THREADS` 之间为什么不能碰 Python API？

**第 4–6 题：动手实战**

4. 优化走查：写一个 O(n²) 的去重/交集函数（`x in list` 版），用 cProfile 确认热点，优化为 set 版，用 `timeit` 记录优化前后耗时与加速比，画出复杂度对比。

5. 语言级优化：对一个字符串处理循环（逐行 `split`/`upper`/`join`）依次应用：内置函数替代、方法局部绑定、`join` 替代 `+=`，每步用 `timeit` 记录，验证"每层都有收益、收益递减"。

6. 剖析进阶：用 `line_profiler` 定位一个函数的最耗时行；用 `tracemalloc` 定位一次内存增长来自哪一行代码；用 `gc.get_referrers` 找出某个"泄漏对象"的持有者。

**第 7–9 题：实战进阶**

7. ctypes 实战：用 `ctypes` 调用 `libc` 的 `qsort` 对 Python 列表排序（声明结构体/数组/回调），对比 `sorted()` 的耗时与代码复杂度，总结"何时 ctypes 值得"。

8. 写一个最小 C 扩展（15.8 的 `mymath`）：实现 `add`/`mul`，用 `setuptools` 编译安装，写 `add` 的 Python 测试（第 14 章）；再实现一个"释放 GIL"的重计算函数，用多线程验证真并行（对比纯 Python 版）。

9. Cython 实战：把第 4 题的优化函数改写为 Cython 版本（`cdef` 类型化），编译并对比：纯 Python / 优化后 Python / Cython 三者的耗时，画出"优化层级 vs 耗时"的柱状图。

**第 10 题：深度思考**

10. 综合设计：一个每秒处理 10 万条消息的实时分析服务（每条消息做文本解析 + 数值聚合），"太慢"了。基于 15.1.2 的路线图：(a) 按顺序给出你的优化步骤（剖析 → 算法 → 语言级 → 向量化 → JIT → C），每步说明预期的收益量级与风险；(b) 哪些步骤可能"收益不大"，为什么（如 IO 瓶颈/热点不热）？(c) 结合第 11 章，什么情况下"并行"比"单线程优化"更优先？给出你的完整优化方案。

---

**卷 1 毕业准备**：
- ✅ 能解释 Python 慢的机制，并按五层杠杆（算法→语言级→向量化→JIT→C）系统优化
- ✅ 会用 cProfile/line_profiler/tracemalloc 定位时间与内存热点
- ✅ 理解 3.11+ 特化解释器（PEP 659）的加速原理
- ✅ 会用 ctypes 调 C 库、用 C API 写扩展（含引用计数与 GIL 释放）、用 Cython 类型化加速
- ✅ 建立性能回归意识（基准测试 + CI 门禁）
- ✅ 掌握"先剖析、再优化、够快就停"的工程纪律

**卷 1 全部 15 章完成。** 从第 1 章的环境搭建到第 15 章的 C 扩展——语言核心、对象模型、IO、模块、并发、元编程、标准库、测试、性能，一条完整的能力链已经建成。下一站：**卷 2 科学计算与数据分析（`data-science/ds-01-numpy.md`）**——用卷 1 的底层视角，拆解 numpy 的 ndarray/广播/内存布局。