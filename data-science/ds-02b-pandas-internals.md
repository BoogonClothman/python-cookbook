# Pandas 深水：存储、对齐与分组的内部实现

> **定位**：这是 `ds-02` 第 2 章的配套深水文件，不是独立章节。主章把 DataFrame 当"列式存储 + 标签 + 对齐规则"来用；本文件拆开这台机器，看它在 CPython 里究竟长什么样、为什么 pandas 3 的行为与 pandas 2 不同。
>
> **学习目标**：
> - **看得见**：能把 `_mgr`、CoW、索引引擎、哈希分组这些名词对应到可复现的实验
> - **算得清**：能预判一次操作的拷贝次数与查找成本（冷/热、单点/批量）
> - **判得准**：能解释"为什么这里慢了"，并判断该 category/Arrow 还是该换引擎
> - **知道边界**：知道私有 API（`_mgr` 等）只用于只读取证，不进生产代码
>
> **阅读前提**：主章 2.1–2.15。正文中的"延伸阅读"从主章这些位置指过来：2.1.3 → B1；2.2.7 → B3；2.3 → B2；2.4/2.6 → B7；2.5/2.7/2.9 → B4；2.8 → B5；2.10 → B6；2.13 → B1、B2、B8。
>
> **验证环境**：所有输出在 Linux（x86_64）上的 Python 3.14.4 + pandas 3.0.6 + NumPy 2.5.3 实跑得到；B7、B8 额外用到 pyarrow 25.0.1、polars 1.44.2、duckdb 1.5.5。计时为本机数字，随负载波动，文中只保证量级与相对关系；凡涉及 `_mgr`、`_engine` 的行都标注了"仅取证"。

---

## B1 BlockManager 与列式存储：DataFrame 的内存真相

### B1.1 一个 DataFrame 有几块

主章说"每列一个 dtype"，实现层面这句话要修正成"**每种 dtype 一个块**"——`df._mgr` 把真相直接打印出来（只读取证，不建议在生产代码里碰私有属性）：

```python
>>> import pandas as pd, numpy as np
>>> df = pd.DataFrame({"i": [1,2,3], "j": [4,5,6], "f": [1.5,2.5,3.5], "s": ["a","b","c"]})
>>> df._mgr
BlockManager
Items: Index(['i', 'j', 'f', 's'], dtype='str')
Axis 1: RangeIndex(start=0, stop=3, step=1)
NumpyBlock: slice(0, 2, 1), 2 x 3, dtype: int64
NumpyBlock: slice(2, 3, 1), 1 x 3, dtype: float64
ExtensionBlock: slice(3, 4, 1), 1 x 3, dtype: str
>>> len(df._mgr.blocks)
3
```

四个列、三种 dtype、**三个块**：`i` 和 `j` 挤进同一个 `2 x 3` 的 int64 块——同 dtype 的列在内存里是**挨着的一整段**。这个动作叫**合并（consolidation）**，收益有二：

1. **一次分配、一次释放**：四列不必四次走分配器，`copy()` 也是按块整段 `memcpy`；
2. **逐行访问局部性**：按行读取时（`itertuples`、`df.values` 的行迭代）同一行的 `i`、`j` 在内存里相邻，缓存行一次抓两个值——这正是"pandas 按行消费时仍然快"的底层原因。

但"按列存储"与"按行消费"的矛盾也由此定型：块是**按列的**（同 dtype 连排），行访问靠**跨步**完成——和 `ds-01` B4 的缓存局部性问题是同一枚硬币的两面。

### B1.2 内存账本：deep 与浅的区别

```python
>>> df.memory_usage(deep=True).to_string()
Index    132
i         24
j         24
f         24
s         27
```

`memory_usage()` 默认只数**块里的紧凑部分**（每列 3 个元素 × 8 字节 + 少量头），`deep=True` 才深入到底座对象。真正该记住的是这个结构：**`Index` 单独一行**（标签不混进列数据）、**数值列 deep ≈ 浅**（本来就是紧排）、**文本列 deep 才见真章**。主章 2.13 里"13.2 MB 里 10 MB 是文本列"的判断，就是靠这一行分解出来的。再看按列深浅的极端对照（主章 2.4.5 同款数据）：

```python
>>> vals = pd.Series([f"c{i%10}" for i in range(10000)])
>>> vals.memory_usage(deep=True), vals.astype("category").memory_usage(deep=True)
(510132, 10642)
```

`str`（python/Arrow 存储的紧凑头部之外还有字符数据）与 `category`（每行 1 字节码 + 10 条类别表）的 48 倍差，就是"字符 vs 整数码"的差——`ds-01` 的"指针/对象 vs 紧凑数组"论题在 pandas 里换了个衣服重演。

### B1.3 `values` 的拷贝路径与可见性

```python
>>> v = df.values                     # 混合类型 → object 数组，必然拷贝
>>> v.dtype
dtype('O')
>>> np.shares_memory(df["i"].to_numpy(), df["i"].to_numpy())
True
```

两件事对比着看。`df.values` 在混合类型上**构造一个新的 object 数组**（把各列的对象装箱进指针数组，主章 2.1.4 的性能悬崖）。而同一列连续两次 `to_numpy()` **共享内存**——因为数值列在无需转型时直接交出块内数组的视图，块里那份数据只有一份。这条性质就是 CoW 的物理基础：**整列数据全局唯一，谁想写谁先拷**。

### B1.4 copy 的成本

```python
>>> big = pd.DataFrame(np.random.default_rng(0).normal(size=(200_000, 4)), columns=list("abcd"))
>>> len(big._mgr.blocks)               # 从单个二维数组构造 → 天然一块
1
>>> import timeit; timeit.timeit(lambda: big.copy(), number=5)/5
0.00047                                # 0.47 ms，数据 6.4 MB
```

20 万行 × 4 列 6.4 MB，深拷贝 0.47 ms——**拷贝贵不贵取决于你拷多少次，不取决于单次多贵**。`copy()` 与块的形状也相关：一块的大数组 `memcpy` 是带宽受限的匀速运动（`ds-01` 1.15.1 的量级：内存带宽 GB/s 级，6.4 MB 理论下限约 1–2 ms 同量级），而 200 个零散小块会退化成 200 次分配器调用。**碎片化（频繁增删列 + 局部写入）的 DataFrame 连 `info()` 都会变慢**，重排一次 `df = df.copy()` 即可重新压实。

> **机制洞察**：pandas 的存储可以用一句话总结——**"按列打包的紧凑块 + 一个按名字找列的轴"**。行不是一等公民：所有"按行"的体验都是跨块拼出来的。理解这一点，就能解释为什么列操作快、为什么混合 `.values` 慢、为什么增删列要动轴、为什么 copy 是按块整搬。

> **⚠️ 陷阱（仅取证）**：`_mgr` 是私有 API，pandas 3 没有承诺其稳定（2.0→3.0 之间块类名从 `Block` 变成了 `NumpyBlock`/`ExtensionBlock`）。本文件所有 `_mgr` 输出只用于"看见结构"，**生产代码请用 `memory_usage(deep=True)` + `dtypes` + `info()` 这三个公开窗口**。

> **延伸阅读**：块合并与 `as_array` 的取数路径见 `pandas/core/internals/`（`managers.py` 的 `interleaved_dtype` 与 `as_array`）；与 `ds-01` 内存模型的对应关系见 `ds-01b` M1、M4。

---

## B2 Copy-on-Write（PDEP-7）：读是引用，写是新对象

主章 2.3 只给了契约，这里给机制与证据。CoW 的一句话定义：**任何 pandas 对象持有的数据都可能被别的引用看见，因此第一次写入前必须把数据复制成"独占"的**——写时拷贝（copy on write），名字就是行为。

### B2.1 三条可复现的证据

```python
# 证据一：链式写被拦截（主章 2.3.3）
>>> df2 = pd.DataFrame({"a": [1,2,3,4]})
>>> df2["a"][df2.index[0]] = 999
<stdin>:1: ChainedAssignmentError:
A value is being set on a copy of a DataFrame or Series through chained assignment.
Such chained assignment never works to update the original DataFrame or Series...
>>> df2["a"].tolist()
[1, 2, 3, 4]

# 证据二：子对象双向隔离（主章 2.3.4 同款）
>>> src = pd.DataFrame({"x": [1, 2, 3]})
>>> sub = src.head(2)
>>> np.shares_memory(sub["x"].to_numpy(), src["x"].to_numpy())
False
>>> src.loc[0, "x"] = 99                 # 改原件
>>> sub["x"].tolist(), src["x"].tolist() # 子表纹丝不动
([1, 2], [99, 2, 3])
```

证据二值得多看一眼：`sub = src.head(2)` 之后，`sub` 的列与 `src` 的列**不共享可写内存**——`head` 交出的是对原件的引用（元数据层面），而**取值物化（`to_numpy`）时按需拷贝**，绝不把可能被别人改写的内存暴露给你。方向是刻意的：**拷贝永远发生在"需要隔离"的那一刻，而不是"可能发生"的那一刻**。

### B2.2 引用传播与惰性拷贝

pandas 3 的实现（PDEP-7）可以概括成两条规则：

1. **引用传播**：`sub` 不只是引用了 `src` 的数据，还把"我是一份未拷贝的视图"这件事登记进共同的管理层（块对象上的共享引用计数）。此后 `src` 的任何写入都会看到"还有别人在看"，于是先拷贝自己再写——`sub` 持有的原数据原封不动；
2. **写入前唯一化**：反过来，`sub` 的写入同样先拷贝它那一份。两个方向合起来就是**双端惰性隔离**：读操作零拷贝，写操作一次性拷贝，谁也不污染谁。

这解释了主章 2.3.4 的"赋值给名字才生效"：`view["c"] = 0` 在 `view` 自己的管理层上完成拷贝与落笔，`df3` 的管理层里根本没有这个新列——**pandas 不再做任何"把我的改动传回原件"的尝试，也就不再需要猜你想要哪一种语义**。

### B2.3 与 `ds-01` 视图语义的对照

| | NumPy（`ds-01`） | pandas 3（CoW） |
|---|---|---|
| 切片/取子集 | 视图，**双向可见** | 引用，**双向隔离**（物化时拷贝） |
| `b = a` | 同一块内存，同上 | 同一个管理层，同上 |
| 写入一个别名 | 所有别名立即看见 | **只有写入者自己看见**（写前拷贝） |
| `copy()` | 深拷贝，隔离边界 | 深拷贝，隔离边界（两者一致） |
| 判据 | `np.shares_memory` | `ChainedAssignmentError` 警告 + 行为隔离 |

注意差异只在**写入后**：NumPy 的视图写入会传播（`ds-01` 1.6 的全部陷阱），pandas 3 的引用写入不会。这不是"更宽松"而是"更严格"——它消灭了 `ds-01` 1.6 那类"改了 A 怎么 B 也变了"的跨对象污染，代价是**`df` 的写入不再能通过 `sub` 观察**，调试时别再用"打印子表"验证"原件改没改"。

### B2.4 迁移的代价：`SettingWithCopyWarning` 的时代

pandas 2 及以前没有 CoW，取子集**可能**是视图**可能**是拷贝（取决于块是否合并、是否发生写时合并），于是有了著名的 `SettingWithCopyWarning`——一个**猜出来的**警告：它只能在"你刚刚链式写了"时提醒，不能保证提醒到位，也不能告诉你哪次赋值已经生效。PDEP-7 的动机原文即在此：**与其警告"可能没生效"，不如让"从来没生效"成为定理**。迁移账单因此是单向的：

- 老代码里"碰巧生效"的链式写 → 变成静默不生效（2.0 版本注意 ①），需改成单层 `.loc`；
- 老代码里 `copy()` 满天飞的防御性写法 → 变成无害但多余的开销（单次 0.47 ms/6.4 MB，B1.4）；
- 换来的是**函数式风格的确定性**：`return df.dropna()` 永远安全，副作用只能通过返回值发生。

> **机制洞察**：CoW 的本质是**把"别名语义"从运行时的猜测变成构造期的登记**。NumPy 时代"视图还是拷贝"取决于历史路径，pandas 3 让答案永远是"读共享、写独占"——代价是写入路径上多了一次引用计数检查与潜在拷贝，收益是这类 bug 从"概率出现"变成"结构上不可能"。

> **⚠️ 陷阱**：CoW 不豁免**逻辑别名**：`b = a` 后 `b` 是 `a` 的另一个名字，你往 `b` 写值时 `b` 确实独立了，但"我以为 `b = a` 拷贝了一份"的代码意图依然落空——**要拷贝就说 `copy()`**。同理，把 DataFrame 塞进函数后修改，函数内必须显式 `df = df.copy()`，否则返回值与入参的关系只剩返回值可言。

> **延伸阅读**：PDEP-7 全文（参考文献 [3]）；块对象上的引用计数与 `_mgr` 的共享检查见 `pandas/core/internals/`；与 `ds-01` 视图模型的对照见 `ds-01b` M5。

---
## B3 Index 引擎：标签查找的真实成本

主章 2.2.7 给了数字，这里给归因。索引查找的开销**不是一个数，是三个数**：冷启动（建引擎）、热后单点、批量对齐——混在一起测就会得到"似线性非线性"的错觉。

### B3.1 冷启动：一次性 O(n)

```python
>>> n = 1_000_000
>>> idx_mono = pd.Index([f"id{i:07d}" for i in range(n)])          # 字典序单调
>>> idx_rand = pd.Index(list(np.random.default_rng(0).permutation(
...                 [f"id{i:07d}" for i in range(n)])))            # 乱序
>>> type(idx_mono._engine).__name__                                # 仅取证
'StringObjectEngine'
>>> # 首次 get_loc 的单次耗时（含引擎准备）
... mono str 冷启动  40.0 ms | 乱序 str 冷启动 108.7 ms | int 冷启动 0.7 ms
```

三种索引的冷启动差出两个数量级，原因是**两条不同的准备路径**：

- **单调索引**：引擎先验证 `is_monotonic`（一次性 O(n)，逐对比较相邻标签——字符串比较有成本，所以 40 ms），之后走**二分查找**；
- **乱序索引**：验证失败后转而**构建哈希表**（O(n) 次哈希 + 插入，108.7 ms），之后走**哈希查找**；
- **整数单调索引**：O(n) 的整型比较便宜得多（0.7 ms），之后同样是二分。

关键在**这些成本只付一次**：引擎登记在 Index 对象上，后续查找直接复用。主章 2.2.7 里"乱序 1M 索引首次 `get_loc` 慢到 45 μs"的假象，正是把这一次性的 100 ms 摊进了 2000 次计时的均值——**测 pandas 的查找性能必须先热身**。

### B3.2 热后：单点亚微秒

```python
热后单次:  mono str 0.360 us | 乱序 str 0.144 us | int 0.664 us
缺失键:    乱序 miss 1.110 us | mono miss 0.910 us（都走完路径后抛 KeyError）
Series.loc ≈ 2 us | Series.iloc ≈ 1.4 us
```

三个值得琢磨的事实：

1. **热后全部亚微秒**——二分 O(log n)（1M 约 20 次比较）与哈希 O(1) 在这个量级上打平，甚至哈希更快（一次散列 vs 二十次带分支的比较）；
2. **缺失键略贵**——要走完全路径才能确认"没有"（哈希查空桶 / 二分越界），然后还要把内部位置翻译成用户能看懂的 `KeyError`；
3. **`Series.loc` 比 `Index.get_loc` 贵约 6 倍**——多出来的是 `Series` 层的协议分派（标量/切片/掩码判别、标签到位置的翻译、结果装箱），不是查找本身。

所以主章 2.13"循环里别 `loc`"的理由不是查找慢，而是**每行都要重付这层 2 μs 的封装**：100 万次单点 ≈ 2 秒，同样的数据 `reindex` 批量做完只要几十毫秒。

### B3.3 批量对齐：摊销后的主成本

```python
>>> idx2 = pd.Index([f"id{i:07d}" for i in range(n)])
>>> s = pd.Series(np.arange(n), index=idx2)
>>> # 首次 reindex(1 万行) 冷 120.1 ms（建引擎），此后平均 0.73 ms/次
```

`reindex`、`merge`、对齐算术全都建在 `get_indexer`（"把右边每个标签翻成左边的位置"）之上，而 `get_indexer` 复用同一套引擎——**冷 120 ms / 热 0.73 ms（每万行）**的结构与单点完全一致。这条曲线解释了两个工程现象：

- **长驻进程里"第一次查询慢"**：服务启动后第一批请求付的是建引擎的账；
- **索引要一次性建好反复用**：每造一个新索引就重新付一次冷启动，别在循环里 `set_index`。

### B3.4 什么时候引擎选错路径

引擎是**按索引形状自动选路**的，用户只能影响形状：

| 索引形状 | 冷启动 | 热后路径 | 提示 |
|---------|--------|---------|------|
| 单调整数（RangeIndex） | O(1)（三元组） | 直接算术 | 默认索引免费 |
| 单调任意类型 | O(n) 验证 | 二分 | 日期索引的常态 |
| 乱序 | O(n) 建哈希 | 哈希 | 一次性付清 |
| 重复标签 | O(n) + 校验 | 哈希 → 多值 | `is_unique=False`，见主章 2.2.5 |

结论对应用者只有两条：**让索引尽量唯一且单调**（排序索引把冷启动变便宜、查找变二分），**让索引活得久一点**（建一次、用多次）。至于哈希还是二分谁快——亚微秒级别上**不值得优化**，真正的优化永远是"少查、批查"。

> **机制洞察**：索引查找的成本结构（冷 O(n)、热 O(1)/O(log n)、批量摊销）与数据库的"建索引 / 走索引"完全同构。pandas 没有把索引持久化，所以**每次进程启动、每个新索引对象，都是一次隐式的 `CREATE INDEX`**——这是"pandas 交互式快、循环里慢"的底层注脚之一。

> **⚠️ 陷阱**：`is_monotonic` / `is_unique` 本身也是**缓存的首次计算**（O(n)）。在循环里对一个新造的索引反复问这两个问题，等于把 O(n) 检查变成 O(n²)——先问一次存变量。

> **延伸阅读**：引擎的 C 层实现见 `pandas/_libs/index.pyx`（分派逻辑）与 `pandas/_libs/hashtable*.pyx`（哈希表）；主章 2.2 的对外语义见参考文献 [7]。

---

## B4 对齐与连接的算法：reindex、union 与 hash merge

主章 2.5/2.9 的所有现象——补 NaN、行数变多、外连接升位——背后是同一组原语。这一节把它们的算法与成本一次量清。

### B4.1 对齐 = 两次 get_indexer + 一次补缺

```python
>>> a = pd.Series(np.arange(500_000, dtype="float64"), index=pd.Index(np.arange(500_000)))
>>> b_same = a.copy()
>>> b_half = pd.Series(np.arange(500_000, dtype="float64"), index=np.arange(250_000, 750_000))
>>> # a + b_same（同索引）0.3 ms；a + b_half（50% 重叠 → 并集 750k）4.3 ms
```

同一个加法，索引相同 0.3 ms、重叠一半 4.3 ms——**差的 4 ms 全是对齐**：pandas 检测到索引相同（`Index.equals` 快路径）就零成本跳过；否则走 `get_indexer` 把两边翻成位置、构造并集、给缺失位置留 `NaN` 槽，最后才做算术。这给出一条实用推论：**让频繁配对的对象共享同一个索引对象**（同一次 `set_index` 的产物），对齐开销直接归零——批量特征相加、时间序列配对都吃这个红利。

`union` 本身在单调整数索引上有专门的 numpy 合并快路径：

```python
>>> x = pd.Index(np.arange(500_000)); y = pd.Index(np.arange(400_000, 900_000))
>>> # x.union(y) -> 900 000 个标签，1.8 ms（双调 → 归并），get_indexer 1.3 ms
```

1.8 ms 拼出 90 万标签的并集——对齐"变慢"的感受不来自 union 本身，而来自**补缺后 dtype 升位与结果物化**（主章 2.5 陷阱里"行数变多、int→float"的两个静默后果）。

### B4.2 hash merge：先建表，再探查

`merge` 的主流路径是**哈希连接**：对较小的一侧建键哈希表，另一侧逐行探查，命中即配对。实测（50 万行事实表 ← 10 万行维表）：

```python
>>> # merge(left 500k, right 100k, on="k", how="left")  20.4 ms -> 500000 行
>>> # merge(left 500k, right 100k, on="k", how="inner") 19.9 ms -> 499396 行
```

20 ms 摘定 50 万 × 10 万的键匹配，靠的是"O(n+m) 的探查而不是 O(n·m) 的比较"。但**配对阶段的输出规模不受此保护**：当两侧同一键各有 k、m 条记录，该键贡献 k×m 行——主章 2.9.3 的笛卡尔爆炸在算法层就是"哈希桶里做了一次嵌套循环"。左右两侧的重复率共同决定输出（19.9 ms 那次输出 499396 行：不匹配的键丢行、重复键多出行，两个效应刚好抵消了大半——**行数不变 ≠ 没出事**，这正是 `validate` 存在的理由）。

### B4.3 保险丝的实测成本

```python
>>> # 同一个 merge：加 indicator=True 25.6 ms（+5.2 ms）
>>> #              加 validate="m:1" 34.4 ms（+14.0 ms）
```

`indicator` 多一列分类值的回填（+25%），`validate` 多一次两侧键的唯一性/基数校验（+69%）。**保险丝不免费，但绝对成本是十几毫秒**——对一次 20 ms 的 merge，多花 14 ms 买到"基数假设当场证伪"，在任何非玩具规模上都是稳赚的交易。反过来也说明它们为什么适合写进**流水线与测试**而不是每行热路径：一次性校验的价值与频率成反比。

### B4.4 四种 how 与 concat 的统一图景

把主章 2.9.1/2.9.5 的行为放进同一张算法表：

| 操作 | 需要配对的键 | 对不上的 | 行数 | dtype |
|------|------------|---------|------|-------|
| `inner` | 两侧键交集 | 丢弃 | ≤ min | 通常稳定 |
| `left/right` | 一侧全保 | 另一侧补 `NaN` | ≥ 保的那侧 | 被补缺列升位 |
| `outer` | 并集 | 双侧补 `NaN` | ≥ max | 补缺列升位 |
| `concat(axis=0)` | 无（按列名并集） | 缺列补 `NaN` | 相加 | 缺行的列升位 |
| `concat(axis=1)` | 行索引 | 按 join 取交/并 | 看 join | 缺行的列升位 |

三条规律统领全部：**"对不上"的唯一处理是补 `NaN`**；**补 `NaN` 必然可能升位**；**行数由"键集合的运算"决定而不是由输入决定**。所以主章 2.14 的行数断言与 `validate` 不是仪式，而是对这三条规律的直接看守——`merge` 的结果形状在算法上就不是"两数相加"那种可口算的东西。

> **机制洞察**：pandas 的"对齐家族"（reindex / align / merge / concat）共享同一个内核：**把标签翻译成位置（`get_indexer`），把位置差异翻译成 `NaN`**。掌握了"键集合做的是哪种集合运算"，就能在写代码之前口算出结果的行数与升位位置。

> **⚠️ 陷阱**：`concat(axis=1)` 在列名撞车时不报错地产出重复列名（主章 2.9.5），根因是它的对齐只看**行索引**、列仅做字面拼接——下游 `df["x"]` 会得到两列的 DataFrame 而不是报错。左右拼接前 `set(a.columns) & set(b.columns)` 应当成为习惯。

> **延伸阅读**：`_MergeOperation` 的多路径分派（哈希/排序/单键特化）见 `pandas/core/reshape/merge.py`；`get_indexer` 的引擎入口见 `pandas/core/indexes/base.py`。

---

## B5 groupby 内部：哈希分组、开关代价与广播回填

### B5.1 split 是一次哈希分桶

split-apply-combine 的 split 阶段与 B3、B4 同源：**按组键哈希，把行号分进桶里**（`pandas/_libs/groupby` 的 C 循环），每桶独立 apply，最后按结果形状拼回。这决定三件可观测的事：

```python
>>> n = 1_000_000
>>> df = pd.DataFrame({"g": np.random.default_rng(0).integers(0, 1000, n),
...                    "v": np.random.default_rng(1).normal(size=n)})
>>> # groupby sort=True  11.9 ms | sort=False 8.7 ms   （100 万行、1000 组）
```

1. **split 是 O(n)**：分组的代价随行数线性、与组数弱相关——1000 组和 100 组几乎一样快，100 万组（每行一组）才是量变点；
2. **`sort=True` 值 3.2 ms（约 34%）**：分桶之后还要把 1000 个组按键序排一遍再输出。对一次性分析这 34% 无关紧要；对每秒几十次的在线聚合，`sort=False` 是白捡的三成；
3. **`observed` / `group_keys` 是零成本布尔**：它们只改变"输出里要不要空组/组键层"，不改分桶。

### B5.2 agg 与 transform：同一次分桶，两种回填

```python
>>> # agg(mean) 10.0 ms | transform(mean) 12.8 ms（1.3 倍）
```

两者**共享完全相同的分桶与归约**，全部差距在最后一步：`agg` 把每桶压成一个标量（1000 个结果），`transform` 还要把 1000 个标量**按桶广播回 100 万行**（一次取行号列表 + 赋值）。1.3 倍的差距就是广播回填的价格——所以主章 2.8 的选型口诀"能 agg 不 apply"在 transform 上要修正为"agg 与 transform 都很便宜，apply 才是分水岭"：

| 算子 | 分桶 | 归约 | 回填 | Python 回调 |
|------|------|------|------|------------|
| `agg`/`sum` | 同 | C 循环 | 不需要 | 否 |
| `transform` | 同 | C 循环 | 广播（+30%） | 否 |
| `filter` | 同 | 组级判定 | 保留整组行 | 每组一次 |
| `apply` | 同 | **每组进 Python** | 任意 | **每组一次** |

`apply` 的真实代价等于"组数 × 回调开销"——组数少（1000 组）时无所谓，组数多（`groupby` 每行一组再 `apply`）时退化为主章 2.13 那张 `apply(axis=1)` 的 1700 倍表。**决定代价的是组数，不是行数**——这是比"少用 apply"更有用的判断依据。

### B5.3 transform 广播为什么不会错位

`transform` 的回填靠**分桶时记下的行号**（每个桶保存"哪些行属于我"），按行号写回而不是按标签对齐——所以它**天然保持原行序**，也不触发 B4 的 union 对齐。这条内部实现解释了主章 2.8 的两个外在保证：

- `transform` 结果**行数恒等于原行数**、顺序不变（行号回填）；
- 单成员组的 `transform("std")` 得 `NaN`（桶里只有一个样本，方差无定义）——回填忠实于桶内计算，不做任何全局补救。

### B5.4 Grouper、resample 与 groupby 是同一台机器

主章 2.8.4/2.10.3 看似三套 API，内部共用分桶机：`groupby(pd.Grouper(freq=))` 先**把时间戳翻译成桶边界标签**（B6.3 的分桶规则），剩下的哈希分组与 `groupby("city")` 完全一致；`resample` 则是时间专用包装（利用时间轴单调性走排序切桶而非哈希）。所以：

- 有聚合、按时间 → `resample().sum()`（排序切桶，比哈希还快）；
- 要拼其他列一起分组 → `groupby(Grouper(...))`（哈希分桶）；
- 行为差异只在**标签与闭开区间约定**（B6.3），不在引擎。

> **机制洞察**：groupby 的全部性能秘密就一句——**分桶一次、算子共享、代价看组数**。sort、transform、apply 的差别都发生在分桶之后：排序是给桶排座次，广播是把桶结果撒回行，apply 是每个桶请一次 Python。

> **⚠️ 陷阱**：`sort=False` 只保证**组键的输出顺序**按出现序，不保证**组内行序**——组内行序本来就是原序（行号回填）。别把"结果的行序"与"键的排座次"混为一谈，主章 2.8.2 的两条契约管的是后者。

> **延伸阅读**：分桶 C 循环与 `transform` 的回填见 `pandas/_libs/groupby.pyx`、`pandas/core/groupby/ops.py`；主章 2.8 的对外语义见参考文献 [8]。

---
## B6 时间序列内部：UTC 内核、分桶边界与 O(1) 窗口

### B6.1 时区 = UTC 内核 + 展示偏移

```python
>>> idx = pd.date_range("2024-07-01", periods=2, freq="D", tz="US/Eastern")
>>> idx.asi8                                    # 仅取证：底层数组（本索引单位为微秒）
[1719806400000000, 1719892800000000]
>>> pd.Timestamp("2024-07-01", tz="UTC").value   # 同一时刻的纳秒纪元值
1719792000000000000
```

`asi8` 揭示 tz-aware 索引的真实存储：**自 Unix 纪元起的整数**（单位跟随索引分辨率——这里是微秒），而且是 **UTC 时间**：`1719806400000000 μs = 2024-07-01 04:00 UTC`，正是美东夏令时的午夜 00:00。时区**不占存储**，它只是换算时刻成人类标签时查的那张偏移表——这就是主章 2.10.2 "存储与计算统一 UTC、展示才转换" 的物理依据：换 `tz_convert` 只换标签、不动底层数组（O(1)），所以永远安全。

夏令时在内核视角下的行为因此变得平凡：

```python
>>> dst = pd.date_range("2024-03-10 00:00", periods=4, freq="h", tz="US/Eastern")
>>> # 本地标签: 00:00(-0500) 01:00(-0500) 03:00(-0400) 04:00(-0400)   ← 02:00 不存在
>>> # 底层 UTC 相邻差:  [1.0, 1.0, 1.0] 小时                        ← 恒定 1 小时
```

**底层永远匀速，标签才会跳变**。所有 DST 事故都发生在"把本地标签做算术"的代码里（01:30 + 2h ≠ 03:30 的两小时），而按 UTC 内核计算则恒定正确——这句口诀的两端现在都有了证据。

### B6.2 非纳秒分辨率：单位跟着数据走

```python
>>> pd.date_range("2024-01-01", periods=3, freq="D").nbytes / 3
8.0                       # 微秒与纳秒每元素都是 8 字节（int64 宽度）
>>> pd.Timestamp.min, pd.Timestamp.max          # 纳秒的可表示区间
(Timestamp('1677-09-21 00:12:43.145224193'), Timestamp('2262-04-11 23:47:16.854775807'))
```

pandas 3 不再强制纳秒，`datetime64[us]/[s]/[ns]` 都是一等公民（`unit=` 选）。注意**分辨率不省内存**（都是 8 字节）——它换的是**范围与互操作**：纳秒纪元只能覆盖 1677–2262（主章 2.10 的版本注意），而微秒/秒与数据库、Arrow、Unix 时间戳天然对齐，跨库时少一层换算。混合分辨率相减/比较时 pandas 自动统一到较细的单位，代价 O(n) 的重标定——**同一批时间序列保持同一分辨率**是省心的工程习惯。

### B6.3 resample 的分桶边：边界点归谁

```python
>>> ts = pd.Series([1.,2.,3.,4.], index=pd.to_datetime(
...     ["2024-01-01 00:30", "2024-01-01 01:00", "2024-01-01 01:30", "2024-01-01 02:00"]))
>>> ts.resample("1h", label="left", closed="left").sum()
2024-01-01 00:00:00    1.0
2024-01-01 01:00:00    5.0
2024-01-01 02:00:00    4.0
>>> ts.resample("1h", label="right", closed="right").sum()
2024-01-01 01:00:00    3.0
2024-01-01 02:00:00    7.0
```

整点戳 `01:00` 在两个设置里进了不同的桶：`closed="left"`（左闭右开，pandas 默认）它属于 01:00 桶，`closed="right"` 它属于以 01:00 结尾的前一桶。**分桶归属由 `closed` 决定、标签位置由 `label` 决定**——两者独立可调。默认的"左闭右开 + 标签在左"与数据库窗口、日历分页的惯例一致；做"每小时最后一笔"这类业务口径时才需要改。边界差 1 的事故不在算法里，**在没人读过的默认值里**。

### B6.4 rolling 的 O(1) 递推

```python
>>> s = pd.Series(np.arange(1_000_000, dtype="float64"))
>>> # rolling(100).mean()              8.4 ms
>>> # rolling(100).apply(np.mean, raw=True)  1355.9 ms   ← 161 倍
```

同是"100 窗口的均值"，两者差 161 倍，因为算法根本不同：`rolling().mean()` 用**滑动和递推**（新窗 = 旧和 + 进 - 出，每步 O(1)，全程与窗口宽度无关），而 `apply(np.mean)` 每个窗口**重新进一次 Python、重新扫 100 个元素**（O(n·w)）。这给主章 2.10.4 补上量化依据：**窗口方法优先用内置聚合**（`mean/sum/min/max/std/quantile` 都有递推实现），`apply` 是"窗口里没有现成函数"时的最后手段，且窗口越大差距越大。`ewm` 同理（指数加权天然递推）——它们快不是因为向量化，而是因为**问题结构允许增量更新**，和 `ds-01` 15 章"算法层优化先于语言层优化"的次序完全一致。

> **机制洞察**：时间序列工具的性能全部来自两条结构红利——**有序**（时间轴单调 → 排序切桶、二分定位、递推更新）与**局部性**（窗口只进不出 → 增量维护）。这两条也是 `ds-04` 里时间序列统计快、`ds-03` 里折线图不卡的根本原因。

> **⚠️ 陷阱**：`asi8`/`.value` 的单位**跟随分辨率**（微秒索引给微秒整数），跨单位比较前必须换算——这是"看起来都是大整数"的隐坑。公开等价物：`idx.asi8` 的语义在文档中承诺为"该单位的整数"，拿去做跨系统 epoch 转换时先 `unit=` 对齐。

> **延伸阅读**：UTC 内核与偏移表见 `pandas/_libs/tslibs/timezones.pyx`、`tzconversion.pyx`；分桶的 `closed/label` 语义见参考文献 [8] 的 Timeseries 章；滑动窗口的递推实现见 `pandas/_libs/window/aggregations.pyx`。

---

## B7 dtype 扩展与 Arrow：两种缺失值阵营

### B7.1 同一种文本，两个阵营

主章 2.4.2 留了一个悬念：pandas 3 的字符串列**底座都是 Arrow**（装了 pyarrow 时；没装则退 python 存储），但缺失值分两派——由**构造方式**决定：

```python
>>> import pandas as pd
>>> pd.Series(['a', None]).dtype.storage                    # 推断
'pyarrow'
>>> pd.Series(['a', None]).dtype.na_value
nan
>>> pd.Series(['a', None], dtype='string').dtype.na_value   # 显式声明
<NA>
>>> pd.StringDtype()                                        # 类的默认 = NA 阵营
<StringDtype(na_value=<NA>)>
```

| 阵营 | 谁产生 | `==` 缺失处 | 与 float 列对齐 | 迁移自 pandas 2 |
|------|--------|------------|----------------|----------------|
| `na_value=nan` | 推断、`dtype=str`、`read_csv` | `False`（总是 bool） | 行为像老 `object` | 无痛 |
| `na_value=pd.NA` | `dtype="string"`、`pd.StringDtype()` | `<NA>`（传播、`bool()` 报错） | 与 `Int64` 语义一致 | 需改判空写法 |

PDEP-14 的设计意图是"推断默认走 `nan` 以兼容老代码、显式声明走 `NA` 以获得严格语义"。**应用侧的纪律是二选一并说清楚**：混合使用时，`pd.isna()`（两派通吃）与 `fillna` 依然安全，但**逐值比较与 `bool()` 转换必须知道手里是哪一派**——这正是主章 2.4.3 那张对照表的字符串版本。

### B7.2 内存：Arrow 打 `object`，category 打 Arrow

```python
>>> n = 100_000; vals = [f"val{i%100:03d}xxxx" for i in range(n)]
>>> pd.Series(vals, dtype=object).memory_usage(deep=True)     # 5900132
5900132
>>> pd.Series(vals, dtype="string").memory_usage(deep=True)   # 1800132
1800132
```

同样 10 万条 10 字符文本：`object` 5.9 MB（每条一个独立 Python str 对象：50 字节头 + 数据），Arrow 字符串 1.8 MB（连续的偏移数组 + 字符缓冲，`ds-01` 的"紧凑缓冲"在字符串上的重演）——**3.3 倍**。而低基数列再上 `category` 还能再压一个数量级（主章 2.4.5 的 48 倍）。三层存储的取舍由此清晰：

| 存储 | 每元素成本 | 适合 | 不适合 |
|------|-----------|------|--------|
| `object` | ~50+ 字节 | 历史数据、混装容器 | 一切新代码 |
| `str`（Arrow） | 偏移+字符，连续 | 文本主力 | 高频 `==` 分组 |
| `category` | 1–4 字节码 | 低基数重复值 | 会增长的开放集合 |

### B7.3 Int64 的位图账本

```python
>>> i64 = pd.Series(np.arange(n), dtype="Int64"); i64[::10] = pd.NA
>>> i64.memory_usage(deep=True), pd.Series(np.arange(n)).memory_usage(deep=True), \
... pd.Series(np.arange(n, dtype="float64")).memory_usage(deep=True)
(900132, 800132, 800132)
>>> i64.head(3).tolist()
[<NA>, 1, 2]
```

可空整数 = **8 字节值数组 + 一份缺失掩码**（实测掩码按布尔数组计，约 1 字节/元素 → 900132 对 800132）。对照三行数字，`Int64` 与"被缺失污染的 `float64`"**同价**——省的不是内存而是**语义**：`3` 而不是 `3.0`、`sum` 跳过 `NA` 而不是把 `NaN` 撒得到处都是。位图掩码的机制（哪一位 = 哪行缺失、`NA` 与 `NaN` 在算术里如何分流）与 Arrow 的 validity bitmap 同构，`pd.NA` 阵营的全部行为（主章 2.4.3）都从这份掩码来。

### B7.4 dtype_backend 与互操作

```python
>>> import pyarrow as pa
>>> tbl = pa.table({"a": np.arange(1000)})
>>> tbl.to_pandas().dtypes.tolist()                       # Arrow -> pandas
[int64]
>>> pd.read_csv(..., dtype_backend="pyarrow").dtypes      # 读入即 Arrow 底座（主章 2.6.4）
['int64[pyarrow]', 'string[pyarrow]']
```

`dtype_backend="pyarrow"` 让数值列也换 Arrow 底座（整数带原生缺失能力、可空不再是 float 的特权）。互操作走三条路：**Arrow 往返**（`pa.table` ↔ `DataFrame`，零拷贝窗口最宽）、**dataframe 交换协议**（`__dataframe__`，主章 2.1 的跨库无损交换，牺牲 dtype 细节换通用）、**numpy 取数**（`.to_numpy()`，拷贝但万无一失）。判断口诀：**与 Arrow 生态（duckdb、polars、parquet）对接多就开 `pyarrow` 后端；与 sklearn/numpy 对接多就留在 numpy 底座**——边界上总会过一次 `.to_numpy()`，那笔拷贝是生态税，早规划早知道。

> **机制洞察**：pandas 3 的 dtype 体系是"**numpy 承载数值、扩展数组承载语义**"的双层结构：数值留在 ndarray 吃 ufunc 红利，而 `str`/`Int64`/`category`/`datetime64[us, tz]` 全是带掩码或带查找表的扩展数组。`dtypes` 列表里每个名字，都对应"值数组 + 附属结构（掩码/类别表/偏移）"的组合——这解释了为什么它们能表达 numpy 表达不了的东西，也解释了为什么混装列只能退回 `object`。

> **⚠️ 陷阱**：扩展数组与 numpy 的边界上，`.to_numpy()` 会**物化并可能降级**（`Int64` 含 `NA` 时降成 `float64`、`category` 展开成字符串）。喂给只认 numpy 的库之前，先想清楚"缺失怎么办"——否则答案就是被悄悄替换成 `nan` 的那一刻决定的。

> **延伸阅读**：PDEP-14（参考文献 [5]）；扩展数组基类与 Arrow 桥接见 `pandas/core/arrays/`、`pandas/core/arrays/masked.py`；Arrow 内存格式见参考文献 [9]。

---

## B8 何时离开 pandas：把决策量化

### B8.1 同题三方实测

200 万行（1000 个组键 + 两列数值），本机取 3–5 次最小值：

```
加载 CSV          pandas 327.6 ms | duckdb 203.5 ms | polars  10.9 ms
内存态 groupby    pandas  35.5 ms | duckdb  92.8 ms | polars  23.2 ms   （duckdb 含结果转 DataFrame）
内存态过滤求和    pandas  11.4 ms | duckdb  72.0 ms | polars   4.0 ms
```

三行数字各自的故事：

- **加载差 30 倍**：polars 的 CSV 解析多线程分片 + Arrow 零拷贝落地；pandas 的解析器是单线程且要逐列物化成 numpy/Arrow——**IO 与解析是 pandas 最真实的短板**（主章 2.13.5 同款结论，此处数据更极端）；
- **内存态小计算 pandas 不慢**：35.5 ms 对 23.2 ms 只差 1.5 倍——pandas 的分桶与归约是 C 循环，与 polars 同一量级；duckdb 在"结果要转回 DataFrame"的口径下反而最慢（SQL 执行 + 结果转换两段成本，且其强项在**直查文件/parquet、并行扫描**而非驱动一个已加载的表）；
- **过滤求和 11.4 ms**：单列掩码 + 归约已经贴着内存带宽走，任何引擎都省不了多少——**这类操作不该成为换库理由**。

### B8.2 换库的三个真信号

结合主章 2.13.5 与卷 1 第 15 章的五层路线图，"离开 pandas"应当由信号触发，而不是由新鲜感触发：

| 信号 | 证据 | 优先级 |
|------|------|--------|
| **加载即瓶颈**（读 5 秒、算 100 毫秒） | B8.1 第一行的 30 倍 | 先换**读取层**：parquet + `chunksize`，或 duckdb 直查文件，pandas 留作计算层 |
| **数据放不进内存 / 多表管道** | 单机内存与临时文件膨胀 | duckdb（SQL 直查磁盘）；它不与 pandas 竞争交互层，它换掉你的 `read_csv` 链 |
| **写法已无可优化**（apply 已消灭、category 已上、分块已用） | 主章 2.13.1 的四行计时已归位 | polars 惰性计划 / Arrow compute，按批迁移**最热的那条管道** |

反过来说，**换库治不了写法病**：`apply(axis=1)` 慢 1700 倍（主章 2.13.1）的问题，换任何引擎写成逐行循环照样慢——所以次序永远是**先量（B8.1 这张表）→ 再改写法（主章反模式清单）→ 再改形状（category/分块）→ 最后才换引擎**。这与 `ds-01` 15 章的五层路线图逐字对应，pandas 深水讲到这里，整本书的方法论闭环了：**性能问题先归因到层，再在层内解决**。

### B8.3 生态税：迁移不是免费的

三个不能只看毫秒数的代价：**生态**（`ds-03`/`ds-04`/sklearn 的 API 全部吃 DataFrame，出图与建模前总要转回一次）、**语义差异**（pandas 的对齐/NaN/CoW 与 polars 的 strict、duckdb 的 SQL NULL 逐条不同，静默错会搬家重来）、**团队成本**（可读性与可维护性是工程的一半）。结论不是"谁更快"，而是**"在哪一层用谁"**：多数团队的稳态是 **duckdb/polars 干 IO 与批处理，pandas 干交互与特征，sklearn/torch 干建模**——三种数据形状（Arrow 管道、DataFrame、ndarray）各就各位，边界上付一次显式的转换税。

> **机制洞察**：引擎选型的本质是**在"加载、计算、生态"三个维度上各自取最优，然后为边界付账**。B8.1 告诉你差距在哪一维，主章 2.13 告诉你差距能被写法抹掉多少——两个合起来，才是完整的技术决策依据。

> **延伸阅读**：polars 的惰性计划与 Arrow 内存见参考文献 [10]；duckdb 的向量化执行与列存储见参考文献 [11]；迁移决策框架见参考文献 [2] 第 12 章与卷 1 第 15 章。

---

## 本文件小结

| 节 | 核心结论 |
|----|---------|
| B1 | 同 dtype 列合并为块（`_mgr` 可见 4 列 3 块）；`copy` 按块整搬（6.4 MB/0.47 ms）；混合 `.values` 必拷贝且降级 `object`，单列 `to_numpy` 共享内存 |
| B2 | CoW（PDEP-7）= 读共享、写独占：链式写不生效、子对象双向隔离、`head` 取值物化时才拷贝；与 NumPy 视图的差异只在"写入后" |
| B3 | 查找成本三分：冷启动 O(n)（单调验证 40 ms / 建哈希 109 ms）→ 热后亚微秒 → 批量摊销（reindex 冷 120 ms / 热 0.73 ms 每万行）；测性能先热身 |
| B4 | 对齐 = 两次 `get_indexer` + 补 `NaN`（同索引 0.3 ms vs 重叠 50% 4.3 ms）；merge 走哈希连接（20 ms/50 万行），爆炸在配对不在查找；`indicator +5 ms`、`validate +14 ms` 是便宜的保险丝 |
| B5 | 分桶一次 O(n)、算子共享；`sort` 值 34%、`transform` 广播值 30%、`apply` 按组数付 Python；Grouper/resample/groupby 共用分桶机 |
| B6 | tz-aware 存 UTC 纪元整数（换标签 O(1)）；底层匀速、本地标签才跳 DST；分辨率不省内存只换范围；`closed/label` 决定边界点归属；`rolling` 递推比 `apply` 快 161 倍 |
| B7 | 字符串底座是 Arrow，缺失值分 `nan`（推断）与 `<NA>`（显式）两派；Arrow 比 `object` 省 3.3 倍；`Int64` 与 `float64` 同价换语义 |
| B8 | 加载差 30 倍、内存小计算只差 1.5 倍；换库信号 = IO 瓶颈 / 放不下 / 写法已无可优化；次序：量 → 写法 → 形状 → 引擎 |

---

## 参考文献

**规范与提案（PDEP）**

1. PDEP-7: *Copy on Write* —— B2 的规范出处。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0007-copy-on-write.md>
2. PDEP-6: *Ban upcasting* —— 主章 2.3 升位禁令与 B7.3 的对照。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0006-ban-upcasting.md>
3. PDEP-14: *String dtype by default* —— B7.1 两派阵营的设计出处。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0014-string-dtype.md>

**官方文档**

4. pandas 3.0 What's New —— 全部"版本注意"的原始清单。<https://github.com/pandas-dev/pandas/blob/main/doc/source/whatsnew/v3.0.0.rst>
5. pandas User Guide: Indexing / Group by / Timeseries —— 主章语义的权威长文。<https://pandas.pydata.org/docs/user_guide/indexing.html>
6. Apache Arrow Python documentation —— B7 的内存格式与桥接。<https://arrow.apache.org/docs/python/>
7. Polars User Guide —— B8 的惰性计划与并行 IO。<https://docs.pola.rs/>
8. DuckDB documentation —— B8 的直查文件与 SQL 层。<https://duckdb.org/docs/>

**源码**

9. `pandas/core/internals/` —— B1 块管理器（`managers.py` 的块合并与 `as_array`）。
10. `pandas/core/indexes/base.py` · `pandas/_libs/index.pyx` · `pandas/_libs/hashtable*.pyx` —— B3 引擎分派与哈希表。
11. `pandas/core/reshape/merge.py` · `pandas/core/groupby/ops.py` —— B4 连接与 B5 分桶。
12. `pandas/_libs/tslibs/` · `pandas/_libs/window/aggregations.pyx` —— B6 时区内核与递推窗口。
13. `pandas/core/arrays/`（`masked.py`、`string_.py`、`arrow_` 系列）—— B7 扩展数组与掩码。
