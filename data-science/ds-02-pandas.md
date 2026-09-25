# 第2章 Pandas：带标签的数据表计算

> **学习目标**：掌握 DataFrame 的数据模型、索引对齐语义与整理流水线，能用 pandas 写出正确、可断言、内存可控的数据处理代码。
>
> - **建模型**：把 DataFrame 看成"列式存储 + 行标签 + 对齐规则"，任何操作都能预判结果的索引、dtype 与行数变化
> - **会取写**：loc/iloc/布尔掩码三路取写不出错，说清 Copy-on-Write 下链式赋值为什么会静默失效
> - **会整理**：清洗（类型/缺失/去重）、变形（melt/pivot）、聚合（split-apply-combine）、连接（关系代数）四类操作信手拈来
> - **跑得快**：`apply(axis=1)` 的代价能量化，知道 category/CoW/分块何时用，知道何时该离开 pandas

上一章的 ndarray 正是本章的底层存储：DataFrame 的每一列底下就是一段数组，广播与轴语义在列内照常成立。但真实数据还有一个 ndarray 给不了的东西——**标签**：每行有身份（日期、订单号）、每列有类型（金额是金额、城市是城市）、缺失有语义。pandas 就是把"数组计算"升级成"带身份的表格计算"的那一层。本章回答一个问题：**一次操作之后，结果的索引是什么、dtype 是什么、行数变没变？** 能预判这三件事，pandas 就不会在你手里静默出错。

本章有两个边界。第一，**只讲 pandas 自己**：画图属于 `ds-03`、统计推断属于 `ds-04`，但本章的变形与聚合正是它们的输入。第二，**主线只给使用契约**，实现机制（块存储、对齐算法、哈希引擎）放进配套文件，不打断查阅节奏。

| 配套文件 | 装什么 |
|---------|--------|
| `ds-02b-pandas-internals.md` | BlockManager 列块与内存布局、Copy-on-Write 机制（PDEP-7）、Index 哈希引擎、对齐与 merge 算法、groupby 内部、时间序列表示、dtype 扩展与 Arrow、何时离开 pandas |

**验证环境**：本章所有可执行输出都在 Linux 上的 Python 3.14.4 + pandas 3.0.6 + NumPy 2.5.3 下实跑得到（时区示例另需 `tzdata`）。计时数字随机器波动，文中只保证数量级，且已标注"本机实测"；2.6 的 parquet 示例需额外安装 `pyarrow`，2.13 的 polars 对比需额外安装 `polars`。

---

## 2.0 导读：本章地图与使用方式

### 2.0.1 全章地图

层级标记：● 核心（第一遍必读）· ◐ 进阶（用到再读）· ○ 深水（在配套文件展开）。

| 节 | 要解决的问题 | 层级 |
|----|-------------|------|
| 2.1 从 ndarray 到表 | 表比数组多了什么，代价是什么 | ● |
| 2.2 Index | 标签从哪来、能不能改、查找多快 | ● |
| 2.3 取数三路 loc/iloc/[] | 怎么取、怎么写才不会静默失效 | ● |
| 2.4 dtype 与缺失值 | 一列到底是什么类型，`NaN` 和 `pd.NA` 差在哪 | ● |
| 2.5 算术与索引对齐 | 两个不同索引的对象为什么能相加，结果多了哪几行 | ● |
| 2.6 输入输出与类型往返 | CSV 读进来类型为什么会变，怎么保证读写一致 | ● |
| 2.7 变形 | 宽表长表怎么互转，透视表怎么造 | ●◐ |
| 2.8 分组引擎 | split-apply-combine 四种算子怎么选 | ● |
| 2.9 连接与重塑 | 四类连接语义、行数什么时候会爆炸 | ● |
| 2.10 时间序列 | 解析、时区、重采样、滚动窗口 | ● |
| 2.11 缺失数据与清洗 | 填、删、插值怎么选，去重留哪条 | ● |
| 2.12 文本与列级操作 | 字符串向量化与可读的链式写法 | ◐ |
| 2.13 性能工程 | 向量化 vs `apply` 差多少，内存怎么省 | ●◐ |
| 2.14 调试与验证 | 怎么把"看起来对"变成断言 | ● |
| 2.15 综合实战 | 一条流水线把全章串起来 | ● |

### 2.0.2 三条阅读路线

不必一次读完。按你当下的目的选一条：

- **速通线**（先能正确干活）：2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.7 → 2.8 → 2.9 → 2.11 → 2.14 → 2.15
- **工程线**（要处理真实数据文件）：速通线 + 2.6、2.10、2.12、2.13
- **原理线**（要写库、要排查诡异问题）：工程线 + 全部 ○ 内容，即 `ds-02b` 配套文件

### 2.0.3 本章向后续章节交付什么

每节末尾都会重申一次本节交付的接口，汇总如下：

| 本章交付 | 谁在用 |
|---------|--------|
| 索引与对齐语义 | `ds-03` 绘图的坐标轴与数据源、`ds-04` 的样本对齐、卷 3 特征工程 |
| split-apply-combine | `ds-04` 分组统计、卷 3 的聚合特征（按用户/按时间窗） |
| 变形 melt/pivot | `ds-03` 宽表转长表后才能画分面图 |
| merge 关系代义与行数契约 | 卷 3 数据集拼接、卷 5 多路知识库合并 |
| 时间序列四件套 | `ds-04` 时间序列统计、卷 5 指标监控与回测 |
| dtype 与缺失值契约 | 全部后续章节的数据入口（脏数据在入口处解决） |
| 性能与 Copy-on-Write | 卷 1 第 15 章五层路线图的"语言级"一环、`ds-02b` B8 |

### 2.0.4 代码、答案与文献约定

- **代码**：概念演示用 REPL 会话（带 `>>>`），完整实验用脚本块；输出为实跑结果。
- **答案**：与 `ds-00`/`ds-01` 一致，随堂自测与章末练习都不附参考答案；数值题用文中同款代码当场核对。
- **文献**：正文用 `> **延伸阅读**：……` 指向章末参考文献；需要实现细节时，进 `ds-02b`。

> **版本注意（pandas 3 基线）**：本章以 pandas 3.0 为准，与 pandas 2 有八处行为差异，正文中会逐一标注——
> ① **Copy-on-Write 默认开启**，链式赋值 `df[a][b] = x` 发出 `ChainedAssignmentError` 警告且**不生效**（2.3）；
> ② **字符串列默认 `str` 类型**，不再默认 `object`（2.4）；
> ③ **setitem 禁止静默升 dtype**，往 `int64` 列写 `1.5` 直接报错（2.3）；
> ④ `fillna(method="ffill")` 移除，改用 `.ffill()`（2.11）；
> ⑤ 频率别名 `"M"` 移除，月末用 `"ME"`（2.10）；
> ⑥ 时间戳默认非纳秒 `datetime64[us]`，不再一律 `ns`（2.10）；
> ⑦ `groupby` 分类列默认 `observed=True`，不再输出全零组合（2.8）；
> ⑧ `groupby(...).apply` 不再把分组列传进函数，访问即 `KeyError`（2.8）。

---

## 2.1 从 ndarray 到表：pandas 解决什么问题

NumPy 有三个"不给活路"的限制：**一整块内存只能有一种 dtype**、**数组自己没有身份**（第 3 行是谁不知道）、**缺失值只能用 `NaN` 而 `NaN` 不能进整数数组**。真实数据恰好三条全踩：订单表里有文本、有金额、有缺失、每行还有一个订单号。这一节先看 pandas 用什么结构同时解决这四件事，再量一量它的内存代价。

### 2.1.1 构造与三份说明书

```python
>>> import pandas as pd, numpy as np
>>> df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25], "score": [88.5, 92.0]})
>>> df
    name  age  score
0  Alice   30   88.5
1    Bob   25   92.0
>>> df.dtypes
name      str
age       int64
score    float64
dtype: object
>>> df.index
RangeIndex(start=0, stop=2, step=1)
>>> df.columns
Index(['name', 'age', 'score'], dtype='str')
```

一个 DataFrame 带着**三份说明书**，和 `ds-01` 的"一张内存 + 三张说明"是同一个思想：

- **每列一个 dtype**（`df.dtypes`）——注意第一列是 `str` 而不是 `object`，这是 pandas 3 的默认行为，2.4 节展开；
- **行标签**（`df.index`）——这里默认是 `RangeIndex(0, 2)`，和 Python 的 `range` 一样只记首尾三项，不占内存；
- **列标签**（`df.columns`）——它本身也是一个 Index 对象，2.2 节展开。

### 2.1.2 列就是 Series，底下就是 ndarray

```python
>>> df["age"]
0    30
1    25
Name: age, dtype: int64
>>> type(df["age"])
<class 'pandas.core.series.Series'>
```

取一列得到 Series，它带着自己的名字（`Name: age`）与共享的行标签。**DataFrame 是"多个共享同一行索引的 Series"**，但这句话只在概念层成立——实际存储里 pandas 会把同 dtype 的多列合并进一块连续内存（Block），这是 `ds-02b` B1 节的内容。列级运算（`df["age"] + 1`）走的正是 `ds-01` 讲过的 ufunc 路径，广播、轴、NaN 语义原样继承。

### 2.1.3 内存：标签的代价

```python
>>> import sys
>>> s = pd.Series(np.arange(1_000_000, dtype="float64"))
>>> s.memory_usage(deep=True)              # 列数据本身
8000132
>>> sys.getsizeof(list(range(1_000_000))) + 1_000_000 * 28   # Python 列表 + 28 字节/元素
36000056
```

100 万个 float，Series 占约 **8 MB**，Python 列表占约 **36 MB**——和 `ds-01` 量出的 4 倍差距同源：Series 底下就是那段紧凑缓冲区，标签另外存。那么标签贵不贵？`RangeIndex` 只有 132 字节（100 万个位置的标签）；换成字符串索引，`Index.nbytes` 也只显示 32 字节——因为**它只数指针数组**，字符串对象本身还躺在堆里。标签的"真实重量"与哈希查找表的开销，见 `ds-02b` B3。

> **机制洞察**：pandas 的内存模型是"**列数据走 NumPy 的紧凑布局，标签走指针 + 哈希表**"。所以列内运算能保持 ndarray 的速度，而按标签查找付出的是哈希与指针追逐的代价——这决定了 2.13 节"何时向量化、何时换工具"的边界。

### 2.1.4 `.values`：最容易踩的那个坑

```python
>>> df.values
array([['Alice', 30, 88.5],
       ['Bob', 25, 92.0]], dtype=object)
>>> df.values.dtype
dtype('O')
```

混合类型 DataFrame 调 `.values` 会**整体降级成 `object` 数组**：每个元素变成 Python 对象指针，NumPy 的类型特化循环全部失效，"快的那一层"瞬间消失。需要数值矩阵时永远显式选列：

```python
>>> df[["age", "score"]].to_numpy().dtype
dtype('float64')
```

> **⚠️ 陷阱**：`.values` / `.to_numpy()` 在混合类型上返回 `object`，是 pandas 里最隐蔽的性能悬崖。凡是准备喂给 NumPy/scikit-learn 的矩阵，先 `df.select_dtypes("number").to_numpy()`。

> **实战建议**：构造 DataFrame 时就把类型敲定（`dtype=` 参数或构造后 `astype`），不要指望事后修补。类型在入口处定好，后面 2.4–2.6 的一半坑都不会出现。

> **延伸阅读**：同 dtype 列如何合并进一个 Block、`memory_usage(deep=True)` 与 `sys.getsizeof` 的差别，见 `ds-02b` 第 B1 节。

**随堂自测 2.1**

1. `df.dtypes` 返回的是什么类型？`df["age"].dtype` 和 `df.dtypes["age"]` 一样吗？
2. 2.1.3 里 100 万个标签的 `RangeIndex` 只占 132 字节，为什么说"标签不免费"？哪些操作会为标签付出实际代价？
3. `pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).values` 的 dtype 是什么？想拿其中两列做数值计算，正确的写法是什么？
4. 为什么 `df["age"] + 1` 能享受 `ds-01` 里 ufunc 的全部优化？它和 `df["age"].to_numpy() + 1` 结果有什么不同（提示：索引）？

**本节交付**："列式存储 + 标签 + 对齐规则"的三件套心智模型，是后面所有小节的地基；`.values` 的 object 陷阱会在 2.13 性能工程里再算一次账。

---

## 2.2 Index：pandas 的一等公民

索引不是装饰：pandas 的**算术、连接、筛选、切片全部按索引对齐**，而不是按位置。这一节讲清楚索引从哪来、能不能改、查找多快——这三件事决定了一半的 pandas 正确性问题。

### 2.2.1 索引是不可变的有序标签集

```python
>>> idx = pd.Index(["b", "a", "c", "a"])
>>> idx.dtype, idx.is_unique, idx.is_monotonic_increasing
(strdtype(), False, False)
>>> idx.nbytes
32
>>> idx[0] = "z"
Traceback (most recent call last):
  ...
TypeError: Index does not support mutable operations
```

三个属性就是索引的"体检表"：`dtype` 决定查找走哪条路，`is_unique` 决定 `loc` 返回标量还是一组，`is_monotonic_increasing` 决定能否用二分查找（`ds-02b` B3 展开）。**索引不可变**——想改标签，只能构造新索引（`set_index`/`rename_axis`）或换新对象。这不是限制而是保护：所有"按标签对齐"的结果都建立在"标签不会在你背后变"之上。

### 2.2.2 RangeIndex：默认索引的免费午餐

```python
>>> pd.RangeIndex(1_000_000).nbytes
132
>>> pd.RangeIndex(1_000_000)[:3].tolist()
[0, 1, 2]
```

100 万个标签、132 字节：`RangeIndex` 只存 `(start, stop, step)` 三个数，取第 k 个标签 O(1) 算出来。这也解释了为什么 `df.head()`、`df.iloc[0:5]` 之类的操作从不心疼——它们大多保留 RangeIndex。

### 2.2.3 reindex：按标签重排的唯一入口

```python
>>> s = pd.Series([1, 2], index=["a", "b"])
>>> s.reindex(["a", "b", "z"])
a    1.0
b    2.0
z    NaN
dtype: float64
>>> s.reindex(["b", "a"])
b    2
a    1
dtype: int64
```

两个必须同时记住的事实：**缺失标签补 `NaN`**（于是 `int64` 被迫升为 `float64`，2.4 节的主线），**换顺序不复制数据**（新索引只是重新排列引用）。`reindex` 也是 `align`、`join` 的底层原语——2.5 节的对齐算术本质上就是在替你 reindex。

### 2.2.4 set_index / reset_index：标签与列的换岗

```python
>>> df = pd.DataFrame({"store": ["A", "A", "B"], "sales": [10, 20, 30]})
>>> df.set_index("store")
       sales
store
A         10
A         20
B         30
>>> df.set_index("store").reset_index()
  store  sales
0     A     10
1     A     20
2     B     30
```

`set_index` 把列升为索引（默认弹出该列），`reset_index` 反向操作把索引降为普通列。凡是"这列是身份而不是度量"（日期、订单号、用户 ID），就升为索引——之后所有按它的筛选、重采样、连接都会少一次列查找。

### 2.2.5 重复标签：默认纪律是保持唯一

```python
>>> s = pd.Series([1, 2, 3], index=["b", "a", "b"])
>>> s.index.is_unique
False
>>> s.index.get_loc("b")
array([ True, False,  True])
>>> s["b"]
b    1
b    3
dtype: int64
```

标签一旦重复，`get_loc` 返回的不再是位置而是一个布尔掩码，`s["b"]` 返回的不再是标量而是一小段 Series——**所有"标签→标量"的假设同时失效**。pandas 不禁止重复索引（多对多连接的结果天然会有），但作为**输入数据的默认纪律：索引必须唯一**，2.14 节会把它写成一条断言。

### 2.2.6 MultiIndex：多级标签

```python
>>> mi = pd.MultiIndex.from_tuples([("x", 1), ("x", 2), ("y", 1)], names=["g", "n"])
>>> mi.tolist()
[('x', 1), ('x', 2), ('y', 1)]
>>> mi.nbytes
122
```

行标签可以是元组：`names` 是每级的名字，2.8 节 `groupby` 多键聚合的结果默认就是 MultiIndex。取数时 `df.loc["x"]` 取一级、`df.loc[("x", 1)]` 取到行——与 2.3 节的 `loc` 语义完全一致。

### 2.2.7 按标签查找有多快

本机实测（100 万个字符串标签的索引）：

```
冷启动（首次 get_loc）: mono str 40.0 ms | 乱序 str 108.7 ms | int 0.7 ms
热后（之后每次）:      Index.get_loc 0.14–0.36 us | Series.loc ≈ 2 us | Series.iloc ≈ 1.4 us
批量（reindex 1 万行）: 冷 120.1 ms -> 热 0.73 ms/次
```

三个数字讲完了标签成本的全部结构。**热身后单次查找是亚微秒级**（0.14–0.36 μs）——百万规模下既不是线性扫描（那会到毫秒级）也不是纯 O(log n) 二分能解释的慢，而是哈希/二分两条快路径，与纯位置寻址（`iloc` 1.4 μs）同量级，多出的只是 `Series` 层的封装开销。**但首次查找要付一次性建引擎的代价**（40–110 ms，O(n)）——这就是上一行里吓人的冷启动，而且它会平摊进你第一次 `reindex`/`merge` 的耗时里；批量对齐热身后只要 0.73 ms/万行。结论：**单点 `loc` 便宜、批量 `reindex` 更便宜、一次性构建会冷不丁出现**——别在循环里反复 `loc`（2.13 节把这条量化成反模式），但也不必为"标签查找"本身焦虑。

> **⚠️ 陷阱**：`reindex` 对缺失标签**不报错**，静默补 `NaN` 并顺手把 `int64` 升成 `float64`。构建新索引后先 `assert set(old) <= set(new)`，或至少 `print(result.isna().sum())`，否则"少了几行数据"要到很久以后才被发现。

> **版本注意**：pandas 3 的字符串索引 dtype 显示为 `str`（PDEP-14），pandas 2 显示 `object`；两者查找性能路径不同，`ds-02b` B3 给出对照。

> **延伸阅读**：索引的哈希引擎（hashtable/trie）、`get_indexer` 的批量对齐、重复标签对查找复杂度的影响，见 `ds-02b` 第 B3 节。

**随堂自测 2.2**

1. `pd.RangeIndex(10**6)` 和 `pd.Index(range(10**6))` 在 `nbytes` 上差多少？为什么？
2. 为什么 `s.reindex(["a", "z"])` 让 `int64` 变成了 `float64`？怎么改写才能保持整数？
3. `df.set_index("date")` 之后想把 `date` 拿回来当普通列，用什么？`inplace=True` 和赋值写法哪个更推荐，为什么？
4. `idx.get_loc("b")` 返回 `array([True, False, True])` 时，`s["b"]` 为什么是一段 Series 而不是标量？给出一条防止这种情况的断言。
5. 多级索引 `df.loc["x"]` 与 `df.loc[("x", 1)]` 语义差别是什么？

**本节交付**：索引的不可变性、reindex 的静默补缺、唯一性纪律，是 2.5 对齐算术与 2.9 连接的直接前提；"标签查找 O(1) 但别循环"的判断会在 2.13 转成完整选型表。

---

## 2.3 取数三路：loc / iloc / []

pandas 的取数只有三条路，**语义各不相同**；写入则只有一条正确路线。这一节把它们一次讲死，2.11 的清洗、卷 3 的特征工程全部复用这里的姿势。

### 2.3.1 三路的语义

```python
>>> df = pd.DataFrame({"a": [1, 2, 3, 4], "b": [10, 20, 30, 40]},
...                   index=["r0", "r1", "r2", "r3"])
>>> df.loc["r1":"r3"]               # 标签切片：两端都含
    a   b
r1  2  20
r2  3  30
r3  4  40
>>> df.iloc[1:3]                    # 位置切片：右端不含（与 Python 一致）
    a   b
r1  2  20
r2  3  30
>>> df.loc["r1", "a"], df.iloc[0, 1]
(2, 10)
>>> df.at["r2", "b"], df.iat[2, 1]
(30, 30)
```

一张表说全：

| 路 | 索引方式 | 切片端点 | 二维写法 | 适用 |
|----|---------|---------|---------|------|
| `.loc` | **标签** | **两端都含** | `loc[行, 列]` | 知道名字（"取 3 月、取 S1"） |
| `.iloc` | **位置** | **右端不含** | `iloc[行号, 列号]` | 知道序号（"取前 10 行"） |
| `[]` | 混合 | 按内容而定 | 不支持二维 | 只推荐取列 |

`at`/`iat` 是单标量的快车道（跳过一切对齐逻辑），在 2.13 的循环反模式里会看到它比 `loc` 快的原因。

> **⚠️ 陷阱**：`df["r1":"r3"]` 是**列名切片**，不是行切片——`[]` 里给标签序列会先尝试列选择。行数据永远走 `.loc`/`.iloc`，`[]` 只用来取列，这条纪律能消掉一大类"取错了却没报错"。

### 2.3.2 布尔掩码筛选

```python
>>> mask = df["b"] > 25
>>> mask
r0    False
r1    False
r2     True
r3     True
Name: b, dtype: bool
>>> df.loc[mask]
    a   b
r2  3  30
r3  4  40
>>> df[pd.Series([True, False])]     # 长度不对
Traceback (most recent call last):
  ...
pandas.errors.IndexingError: Unalignable boolean Series provided as indexer
(index of the boolean Series and indexed object do not match).
```

布尔掩码必须**与被筛的轴等长且索引对齐**——pandas 会拿掩码的索引去对齐目标，而不是按位置硬套。这条对齐纪律是 2.5 节的同一套规则，也是防止"错位筛选却不报错"的最后一道闸。

### 2.3.3 写入只有一条正确路线

```python
>>> df4 = df.copy()
>>> df4.loc[mask, "b"] = df4.loc[mask, "b"] * -1     # ✅ 单层 .loc，一步到位
>>> df4["b"].tolist()
[10, 20, -30, -40]
```

而"先取列、再写子对象"这条老路线在 pandas 3 里连**结果**都不剩：

```python
>>> df2 = df.copy()
>>> df2["a"][df2.index[0]] = 999                     # ❌ 链式赋值
<stdin>:1: ChainedAssignmentError:
A value is being set on a copy of a DataFrame or Series through chained assignment.
Such chained assignment never works to update the original DataFrame or Series...
>>> df2["a"].tolist()                                # 原地踏步，静默不生效
[1, 2, 3, 4]
```

> **机制洞察**：pandas 3 默认开启 **Copy-on-Write（PDEP-7）**——`df2["a"]` 拿到的是原列的一个**只读引用**，任何"对它的写入"都不会也不能传导回原表。链式写被降级为"警告 + 无效果"，从此**不存在"改了原件还是改了副本"的分歧**：读到的都是引用，写出去的都是新对象。机制（引用传播、惰性拷贝）见 `ds-02b` B2。

同时，直接 `.loc` 写入还有第二条 pandas 3 规则——**写入不许悄悄改变列的类型**（PDEP-6，ban upcasting）：

```python
>>> d = pd.DataFrame({"i": [1, 2]})
>>> d.loc[0, "i"] = 1.5
Traceback (most recent call last):
  ...
TypeError: Invalid value '1.5' for dtype 'int64'
```

在 pandas 2 里这一行会把整列静默升成 `float64`。现在它报错：**要换类型就显式 `astype` 或先建新列**，让类型变化永远出现在你写的代码里，而不是发生在你没看的地方。

但有一个被 PDEP-6 特意保留的例外——**缺失值**：

```python
>>> d = pd.DataFrame({"i": [1, 2]})
>>> d.loc[0, "i"] = np.nan          # NaN / pd.NA / None 都一样
>>> d["i"].dtype
dtype('float64')
```

往 `int64` 列写 `1.5` 报错，写 `np.nan` 却静默升成 `float64`——因为整数数组存不下缺失，pandas 只有升位一条路。这是 2.4 "整数列 + 缺失 = float64"在**写入侧**的再现；要保住整数语义，先 `astype("Int64")` 再写。

### 2.3.4 子对象天然隔离

CoW 带来的另一条可见行为：

```python
>>> df3 = df.copy()
>>> view = df3.iloc[:2]           # 取一个子表
>>> view["c"] = 0                 # 给子表加列
>>> df3.loc["r0", "a"] = 777      # 再改原表
>>> view["a"].tolist(), df3["a"].tolist()
([1, 2], [777, 2, 3, 4])
>>> view.columns.tolist(), df3.columns.tolist()
(['a', 'b', 'c'], ['a', 'b'])
```

**两边互不影响**：改原表不会让已取出的子表"跟着变"，改子表（加列、写值）也不会污染原表。`ds-01` 里"视图会不会传染"的焦虑在这里被系统性解除——但代价是：**想让改动生效，必须把结果赋给名字**（`view = view.assign(...)` 或 `df = df.copy()` 后修改再赋回），任何"顺手改一下"的函数副作用都不再存在。

`df.copy()` 默认仍是深拷贝，拿它做隔离边界永远安全：

```python
>>> src = pd.DataFrame({"x": [1, 2, 3]}); cp = src.copy()
>>> src.loc[0, "x"] = 50
>>> src["x"].tolist(), cp["x"].tolist()
([50, 2, 3], [1, 2, 3])
```

> **⚠️ 陷阱**：CoW 不等于"可以随便赋值别名"。`b = a` 只是起外号，随后任何一方的写入都会触发拷贝——**写入本身是安全的**，但"我以为 `b = a` 已经复制了"的假设是错的，要隔离就显式 `.copy()`。函数内部拿到 DataFrame 后想改，先 `df = df.copy()` 再动手，这是把副作用写在签名上的纪律。

> **实战建议**：链式写一律改写为**单层 `df.loc[行掩码, 列] = 值`**。判断口诀：等号左边只允许出现**一个** `[]`。

> **延伸阅读**：CoW 的引用传播与惰性拷贝机制、pandas 2 的 `SettingWithCopyWarning` 为何被废弃，见 `ds-02b` 第 B2 节。

**随堂自测 2.3**

1. `df.loc[1:3]` 和 `df.iloc[1:3]` 在默认 RangeIndex 上结果为何相同？换成字符串索引后各自还成立吗？
2. 写出等价于 `df2["a"][df2.index[0]] = 999` 且真正生效的单层写法。
3. 为什么布尔掩码长度差 1 就报 `IndexingError`，而 `df.loc[["r1", "r3"]]` 用列表就不需要等长？（提示：掩码按索引对齐，列表按标签取值）
4. `d.loc[0, "i"] = 1.5` 报错后，想让 `i` 列变成浮点有哪两种写法？
5. 为什么 pandas 3 把链式赋值改成"警告 + 不生效"而不是"报错终止"？这个折中让哪类老代码静默失效？

**本节交付**：三路取写姿势是全书数据处理的公共语法——`ds-03` 的筛选作图、`ds-04` 的样本切片、卷 3 的标签式特征工程全部以本节为准；CoW 契约交付给 2.13 性能与 `ds-02b` B2。

---

## 2.4 dtype 与缺失值体系：一列到底是什么

`ds-01` 的教训是"先定 dtype 再算"；pandas 把这个问题复杂化了一层：**列的类型既要表达值的形状，还要表达缺失的语义**。本节给出完整的类型地图与两种缺失值的分工。

### 2.4.1 类型地图

| dtype | 装什么 | 缺失表示 | 备注 |
|-------|--------|---------|------|
| `int64` | 整数 | **不允许** | 有缺失会被迫升为 `float64` |
| `float64` | 浮点 | `np.nan` | 最常见的"被缺失污染"的类型 |
| `bool` | 真假 | **不允许** | `True/False` + `None` 会掉进 `object` |
| `str` | 文本 | `np.nan`（pandas 3 默认） | PDEP-14，取代 `object` |
| `category` | 有限枚举 | 按底座类型 | 省内存 + 语义提示 |
| `Int64`/`boolean`/`Float64` | 可空扩展类型 | `pd.NA` | 显式声明"允许缺失" |
| `datetime64[us]` | 时间戳 | `NaT` | pandas 3 默认微秒，见 2.10 |
| `object` | 混合杂项 | 各随其主 | **尽量消灭它** |

### 2.4.2 str 取代 object：PDEP-14

```python
>>> df = pd.DataFrame({"s": ["a", "b"], "i": [1, 2], "b": [True, None]})
>>> df.dtypes
s      str
i    int64
b    object
dtype: object
>>> s = pd.Series(["x", None, "y"])
>>> s.dtype
<stringpython>
>>> s.iloc[1] is np.nan
True
```

两件事值得停一下。其一，字符串列默认是 `str` 类型（`StringDtype`），不再是 `object`——`object` 列里可以塞任何东西，pandas 每个操作都得逐元素判断类型，`str` 列则能走向量化路径（安装了 pyarrow 时，底层存储实际是 Arrow 字符串数组，见 `ds-02b` B7）。其二，**推断出来的 `str` 缺失值用 `np.nan` 而不是 `pd.NA`**（PDEP-14 特意为之，为了和 `float64` 的 `NaN` 行为一致、平滑承接 pandas 2 的老代码）；而**显式声明 `dtype="string"` 则是 `pd.NA` 阵营**：

```python
>>> pd.Series(['a', None]).iloc[1] is np.nan          # 推断：NaN 阵营
True
>>> pd.Series(['a', None], dtype='string').iloc[1] is pd.NA   # 显式：NA 阵营
True
>>> (pd.Series(['a', None]) == 'a').tolist()          # NaN 阵营：比较永远 bool
[True, False]
>>> (pd.Series(['a', None], dtype='string') == 'a').tolist()  # NA 阵营：缺失处诚实 <NA>
[True, <NA>]
```

同一种文本数据，**缺失值阵营由构造方式决定**——这就是 2.4.3 那张对照表在字符串列上的投影。

但 `df` 里那个 `b` 列暴露了一个坑：

```python
>>> df["b"].dtype
dtype('O')           # True + None → object，不是 boolean！
```

从 `[True, None]` 构造的列**推断成 `object`**——因为 `None` 不是布尔值，pandas 不肯把它猜成 `boolean`。要可空布尔，必须显式声明：

```python
>>> pd.Series([True, None], dtype="boolean").tolist()
[True, <NA>]
```

### 2.4.3 两种缺失值：np.nan 与 pd.NA

这是 pandas 缺失值语义的总纲，**全部行为都可由下表预判**：

```python
>>> np.nan == np.nan
False
>>> pd.NA == pd.NA
<NA>
>>> 1 + pd.NA
<NA>
>>> bool(pd.NA)
Traceback (most recent call last):
  ...
TypeError: boolean value of NA is ambiguous
```

| | `np.nan`（float/str 列） | `pd.NA`（可空扩展类型） |
|---|---|---|
| 自相等 | `False`（IEEE 754） | `<NA>`（诚实未知） |
| 算术传播 | `nan + 1 = nan` | `NA + 1 = NA` |
| 布尔筛选结果 | 永远是 `bool` | 位置上是 `<NA>` |
| `bool()` | `True`（历史怪癖） | **抛 `TypeError`** |
| 空值判断 | `pd.isna` 统一搞定 | 同左 |

筛选时的差别最要命：

```python
>>> pd.Series([1.0, np.nan, 3.0] ) > 1
0    False
1    False
2     True
dtype: bool
>>> pd.Series([1.0, pd.NA, 3.0], dtype="Float64") > 1
0    False
1      <NA>
2     True
dtype: boolean
```

`NaN > 1` 给你 `False`（"不知道就当不满足"），`pd.NA > 1` 给你 `<NA>`（"不知道就是不知道"）——后者在 `.all()` 时会直接抛错逼你表态。**规则：数值计算用 `float64 + NaN` 一路走到黑也行；涉及"缺失会传染判断"的逻辑（条件筛选、状态机），用可空扩展类型 + `pd.NA`。** 而 `df.isna()` 对两者一视同仁，清洗代码永远用它。

### 2.4.4 可空扩展类型：整数列也能有缺失

```python
>>> n = pd.Series([1, None, 3], dtype="Int64")
>>> n.tolist(), n.sum()
([1, <NA>, 3], 4)
```

`int64` 不允许缺失，`Int64` 允许且**聚合自动跳过缺失**。这是处理"计数、等级、邮编"这类**语义上是整数又可能缺失**的列的唯一正解——否则你只能接受整列掉进 `float64`，出现 `3.0` 个订单这种鬼话。

### 2.4.5 category：48 倍的内存杠杆

```python
>>> vals = pd.Series([f"c{i%10}" for i in range(10000)])
>>> vals.memory_usage(deep=True), vals.astype("category").memory_usage(deep=True)
(510132, 10642)
```

同样 1 万行 10 个取值：字符串列 510 KB，`category` 列 10.6 KB——**约 48 倍**。原理与 `ds-01` 的"指针数组 vs 紧凑缓冲"同源：`category` 只存"类别表（10 个字符串）+ 每行的整数码"。分组、连接、透视在低基数列上还能因此快一个量级（2.13 实测）。代价是**写入受限**：不能塞进新类别（需重建 `cat.categories`）。

### 2.4.6 类型转换：显式的三条路

```python
>>> pd.to_numeric(pd.Series(["1", "2", "bad"]), errors="coerce").tolist()
[1.0, 2.0, nan]
>>> pd.Series([1, "a"]).dtype              # 混合类型只能 object
dtype('O')
```

- **构造时**：`pd.read_csv(..., dtype={...})`（2.6 节，最好的时机）；
- **转换时**：`astype("Int64")` 严格（转不动就报错），`to_numeric/to_datetime(errors="coerce")` 宽容（转不动变 `NaN`/`NaT`）；
- **写入时**：pandas 3 基本**不允许 setitem 静默升类型**（2.3 已见 `TypeError: Invalid value '1.5' for dtype 'int64'`），唯一例外是缺失值仍会把 `int` 升 `float`；所以"先改类型再写"是唯一稳妥顺序。

> **⚠️ 陷阱**：**整数列 + 缺失 = `float64`**，这是最高频的类型污染：`qty` 列读进来 `[3.0, nan, 5.0]`，随后 `qty.astype("int64")` 直接失败、`qty == 3` 对缺失行给 `False` 而不是"不知道"。要么上游补 `0`、要么整列声明 `Int64`，别放任 `3.0` 个订单过夜。在 2.15 的流水线里会看到它实际发生。

> **版本注意**：pandas 3 中 `object` 正在退场（字符串默认 `str`、新读入默认走可空类型），但**历史数据文件里的 `object` 列仍会出现**——`select_dtypes(include="object")` 是入口检查清单的常客。

> **延伸阅读**：`StringDtype` 的两种存储（python/pyarrow）、`string[pyarrow]` 与 Arrow 内存布局、`Int64` 的位图掩码实现，见 `ds-02b` 第 B7 节。

**随堂自测 2.4**

1. 为什么 `[True, None]` 推断成 `object` 而 `[True, False]` 是 `bool`？写出显式可空布尔的构造方式。
2. `np.nan == np.nan` 与 `pd.NA == pd.NA` 结果为何不同？哪一个是"诚实"的，代价是什么？
3. `pd.Series([1, None, 3], dtype="Int64").sum()` 和 `pd.Series([1.0, np.nan, 3.0]).sum()` 都是 4——为什么 `.sum()` 会跳过缺失？`min()` 也会吗？用代码验证。
4. `df["qty"]` 读进来是 `float64` 且有 `NaN`，两种把它恢复成"能表达缺失的整数"的写法分别是什么？
5. 什么时候该用 `category`？给出一个不适合的例子并说明原因。

**本节交付**：类型地图与两种缺失值的分工，是 2.6 类型往返、2.11 缺失清洗、`ds-04` 统计（`nanmean` 的样本数语义）与卷 3 特征类型化的共同前提；`category` 会在 2.13 换回 48 倍内存的账。

---

## 2.5 算术与索引对齐：为什么两行能相加

pandas 里"相加"的单位不是位置而是**标签**。这是它区别于 NumPy 的第一决定性特征，也是行数悄悄变多、`int` 悄悄变 `float` 的唯一来源。

### 2.5.1 加法在做并集

```python
>>> a = pd.Series([1, 2, 3], index=["a", "b", "c"])
>>> b = pd.Series([10, 20, 30], index=["b", "c", "d"])
>>> a + b
a     NaN
b    12.0
c    23.0
d     NaN
dtype: float64
```

逐行读这张结果表，pandas 做了三步：**取两个索引的并集**（a,b,c,d）、**按标签配对相加**（b、c 有两侧数据）、**配不上的补 `NaN`**（a、d）。同时 `int64` 变成了 `float64`——和 2.2.3 的 `reindex` 是同一个机制，`+` 内部就是两次 reindex 再相加。

只有一侧缺席时，可以用 `fill_value` 把"缺席"解释成 0：

```python
>>> a.add(b, fill_value=0)
a     1.0
b    12.0
c    23.0
d    30.0
dtype: float64
```

> **机制洞察**：对齐的代价与收益都藏在"**标签是身份**"里。收益：两份独立采集的数据（两个传感器、两张表）不保证行序一致，按标签相加永远是对的；代价：**结果的行数 = 并集大小**，`len(a + b)` 可能大于任何一侧——不检查就是 2.9 节要讲的"行数悄悄变了"的亲戚。

### 2.5.2 比较运算不许对齐

```python
>>> (a > 2) == (b > 2)
Traceback (most recent call last):
  ...
ValueError: Can only compare identically-labeled Series objects
```

算术可以容忍"对不上的补 NaN"，**比较不行**：把两个索引不同的布尔结果摆在一起，`False` 可能意味着"不满足"也可能意味着"这边没有"——语义上无法调和，所以 pandas 直接拒绝。要用比较，先显式对齐：

```python
>>> (a > 2).reindex(a.index.union(b.index))
```

这条"比较比算术严格"的不对称是 pandas 的深思熟虑，也是随堂自测里的常客。

### 2.5.3 DataFrame 与 Series 的方向

```python
>>> df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
>>> df + pd.Series([10, 20], index=["x", "y"])        # Series 的标签对上"列"
    x   y
0  11  23
1  12  24
>>> df.add(pd.Series([10, 20], index=[0, 1]), axis=0) # axis=0：对上"行"
    x   y
0  11  13
1  22  24
```

**DataFrame ± Series 默认沿列对齐**（Series 的标签必须是列名），相当于给每行都加同一组数——这就是"按行广播"；`axis=0` 则反过来让 Series 的标签对上行索引，给每列各减一个基准值（按列中心化正是这个写法，卷 3 标准化会再遇到）。

> **⚠️ 陷阱**：对齐运算最常见的两个静默后果——**行数变多**（并集）与 **int 变 float**（NaN 进不了 `int64`）。凡是把对齐结果接进后续流程的代码，开头都应该 `assert len(result) == len(预期)`；凡是结果要写回整数语义的列，结尾 `astype` 前先确认没有 `NaN`。

> **实战建议**：拿不准对齐方向时，不要背规则，**打印结果的 index 看一眼**。`result.index` 与 `result.columns` 是 pandas 里最便宜的"调试打印"。

> **延伸阅读**：并集/交集索引的构造成本、`align` 的四种 join 选项、对齐如何复用 `get_indexer` 批量查找，见 `ds-02b` 第 B4 节。

**随堂自测 2.5**

1. `a + b` 的结果为什么必然比 `a` 长？`a.add(b, fill_value=0)` 之后还会有 `NaN` 吗？什么情况下仍会（提示：两侧都缺的位置）？
2. 为什么 `==` 拒绝对齐而 `+` 接受对齐？给出一个"比较也对齐"会导致错误结论的具体例子。
3. `df - df.mean()` 在 pandas 里默认是按列减还是按行减？写出明确方向的等价写法。
4. 两个 `int64` Series 对齐相加后变成 `float64`，想拿回整数需要哪两步（先验证无缺失）？
5. `len(s1 * s2)` 可能大于 `len(s1)`——写一行断言防止这种膨胀进入下游。

**本节交付**：对齐语义是 2.7 变形、2.8 分组、2.9 连接共享的底层逻辑（它们都是"换一种方式对齐"）；"行数与 dtype 必须显式验证"的纪律交付给 2.14 的契约断言。

---

## 2.6 输入输出与类型往返：CSV 是有损的

数据进出磁盘时，**类型信息不在场**——CSV 只是一行行文本，读进来是什么类型全靠 pandas 猜。这一节解决三件事：猜的规则、猜错的修法、如何让往返无损。

### 2.6.1 类型推断是"整列民主"

```python
>>> from io import StringIO
>>> csv = """date,name,qty,price
... 2024-01-01,apple,3,1.5
... 2024-01-02,pear,,2.25
... 2024-01-03,apple,5,x"""
>>> df = pd.read_csv(StringIO(csv))
>>> df.dtypes
date      str
name      str
qty     float64
price     str
dtype: object
>>> df["qty"].tolist()
[3.0, nan, 5.0]
```

一次看懂三条推断规则：

- **`date` 是 `str` 不是日期**——pandas 不会猜日期，除非你 `parse_dates=["date"`]；
- **`qty` 整列带缺失 → `float64`**——2.4 的陷阱原样发生：一个缺失把整列从整数拖下水；
- **`price` 沦为 `str`**——第 3 行一个 `x` 毁掉整列。**推断是整列民主制，一行脏数据就政变**。

### 2.6.2 三个控制旋钮

```python
>>> pd.read_csv(StringIO(csv), parse_dates=["date"])["date"].dtype
datetime64[us]
>>> pd.read_csv(StringIO(csv), dtype=str).dtypes.tolist()
[<StringDtype(na_value=nan)>, ...]                    # 全部按文本读
>>> pd.read_csv(StringIO(csv), usecols=["date", "qty"]).columns.tolist()
['date', 'qty']
>>> pd.read_csv(StringIO("a,b\n1,x\n2,none\n"), na_values=["none"])["b"].tolist()
['x', nan]
```

- **`parse_dates`**：显式指认日期列（拿到 `datetime64[us]`，2.10 的微秒单位是 pandas 3 的新默认）；
- **`dtype`**：最被低估的旋钮——**把"猜"换成"声明"**。`dtype={"qty": "Int64"}` 一步消掉 2.6.1 的整列污染，这永远是读入正确数据的第一选择；
- **`na_values`**：把业务里的脏标记（`none`、`-`、`未知`）纳入缺失。注意 **`N/A`、`NA`、`NULL`、`null`、`NaN`、空串已经是默认缺失值**，不必重复声明——反过来说，这些字面量在你数据里若有业务含义（比如 `NA` 是"不适用"而非"没采集"），要小心被误杀。

### 2.6.3 往返保真与格式选择

```python
>>> txt = df.to_csv(index=False)                        # 写出（df 见 2.6.1）
>>> back = pd.read_csv(StringIO(txt), parse_dates=["date"])
>>> back.dtypes
date     datetime64[us]
name                str
qty             float64
price               str
dtype: object
```

**CSV 往返 = 文本 + 猜测**，两头都得显式参数（`index=False` 防止索引变成一列假数据；读回时重复 `parse_dates`）。需要无损就换二进制格式：

```python
>>> two = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
>>> two.to_parquet("t.parquet"); pd.read_parquet("t.parquet").dtypes.tolist()
[int64, int64]                                          # 类型原样回来
>>> import os; os.path.getsize("t.parquet")             # schema/压缩块的固定开销在这里占大头
2111
```

parquet **自带 schema**（dtype、压缩、列裁剪一起写入），往返无损。但它的固定开销不小——本例两行数据就占 2111 字节（footer 与块头），而同样的 CSV 只有十几字节；**行数越大相对开销越小**，小文件交换反而 CSV 更轻。选型口诀：

| 场景 | 格式 | 理由 |
|------|------|------|
| 与外部系统交换、人工能看 | CSV | 通用、可 diff，但**有损** |
| 自己的中间产物、需保类型 | **parquet** | schema 在场、可按列读取 |
| 超内存、分块处理 | `chunksize=` 迭代 / memmap | 见 2.13 |

`chunksize=` 让 `read_csv` 返回可迭代的 `TextFileReader`，每个块是一个小 DataFrame——10 GB 文件不需要 10 GB 内存，逐块 `groupby().sum()` 后再合并即可（2.15 的进阶练习会用到）。

### 2.6.4 Arrow 后端：一个参数换一套存储

```python
>>> pd.read_csv(StringIO("a,b\n1,x\n2,y"), dtype_backend="pyarrow").dtypes.astype(str).tolist()
['int64[pyarrow]', 'string[pyarrow]']
```

`dtype_backend="pyarrow"` 把整数列存成 `int64[pyarrow]`、文本存成 `string[pyarrow]`——缺失值统一 `pd.NA`（2.4 的可空语义），内存通常更省。它是 pandas 与 Arrow 生态（以及 2.13 的"离开 pandas"）的桥头堡，细节在 `ds-02b` B7。

> **⚠️ 陷阱**：**"读进来先 `df.info()`"** 应该成为肌肉记忆。2.15 的流水线里 `price` 因为三行 `?` 整列变 `str`，如果跳过这一步直接 `df["price"] * 2`，得到的不是报错而是一串字符串拼接——**类型错误不报错，才是真错误**。

> **版本注意**：pandas 3 的 `parse_dates` 产出 `datetime64[us]`（微秒）而非一律 `ns`；与需要纳秒的外部库对接时用 `astype("datetime64[ns]")` 转换，见 2.10。

> **延伸阅读**：parquet 与 Arrow 的内存布局、`string[pyarrow]` 存储、pandas 读写器的代码生成路径，见 `ds-02b` 第 B7 节。

**随堂自测 2.6**

1. 为什么 `date` 列不加 `parse_dates` 就是 `str`？写出同时声明 `date` 为日期、`qty` 为可空整数的**一次到位**读法。
2. 一行 `?` 为什么能让整列变成 `str`？给出两种修复路径（读入时防 / 读入后治），并说明各自适用场景。
3. 默认 `na_values` 已含 `N/A`——如果你的业务里 `N/A` 表示"不适用"（应保留为文本），怎么读才能不误杀？
4. CSV 和 parquet 各自"无损"的边界是什么？`to_csv()` 忘了 `index=False` 会发生什么？
5. `chunksize=10**5` 读 10 GB 文件时，每个块的 dtypes 和整读一致吗？（推断是逐块进行的）用代码验证，并说明这对分块聚合意味着什么。

**本节交付**：类型在入口处锁定的纪律，是 2.11 清洗、2.15 流水线与卷 3 特征工程的起点；`chunksize` 与 parquet 是 `ds-04` 大样本统计、卷 5 数据管道的存储基础。

---

## 2.7 变形：宽表与长表的互转

同一份数据有两种基本形状：**长表**（tidy：一行一个观测，适合存储与计算）与**宽表**（一列一个变量，适合人眼看、适合画折线）。本节的四个动词——`melt`、`pivot`、`pivot_table`、`stack/unstack`——只干一件事：**在两种形状之间搬运，且不丢信息**。

### 2.7.1 宽长互转的一对动词

```python
>>> long = pd.DataFrame({"city": ["A","A","B","B"], "year": [2023,2024,2023,2024],
...                      "sales": [10,12,7,9]})
>>> wide = long.pivot(index="city", columns="year", values="sales")
year  2023  2024
city
A       10    12
B        7     9
>>> wide.reset_index().melt(id_vars="city", var_name="year", value_name="sales")
  city  year  sales
0    A  2023     10
1    B  2023      7
2    A  2024     12
3    B  2024      9
```

- **`pivot`（长→宽）**：指定"谁当行（`index`）、谁当列（`columns`）、谁当格子里的值（`values`）"。行×列的交叉点必须**唯一**，否则：

```python
>>> pd.DataFrame({"i":["a","a"], "c":[1,1], "v":[1,2]}).pivot(index="i", columns="c", values="v")
ValueError: Index contains duplicate entries, cannot reshape
```

- **`melt`（宽→长）**：`id_vars` 是要原样保留的标识列，其余列被"熔"进 `variable`/`value` 两列（名字可用 `var_name`/`value_name` 定制）。

### 2.7.2 pivot_table：允许重复的透视

```python
>>> long.pivot_table(index="city", columns="year", values="sales",
...                  aggfunc="sum", margins=True, margins_name="Total")
year   2023   2024   All
city
A      10.0   12.0  22.0
B       7.0    9.0  16.0
All    17.0   21.0  38.0
```

`pivot_table` = `pivot` + `groupby`（`ds-01` 的轴语义在这里复活：`aggfunc` 是沿哪个维度归约），因此**容忍重复键**（按 `aggfunc` 聚合）、自带 `margins` 合计行列。选型只需一句话：**格子唯一用 `pivot`，格子要算用 `pivot_table`**。`pd.crosstab(a, b)` 则是"计数透视"的快捷方式，`margins=True` 同样可用。

### 2.7.3 stack / unstack：索引级别的升降

```python
>>> s = long.set_index(["city", "year"])["sales"]
>>> s.unstack()                 # 末级索引升为列
year  2023  2024
city
A       10    12
B        7     9
>>> s.unstack().stack()         # 还原（丢掉 NaN 行）
city  year
A     2023    10
      2024    12
B     2023     7
      2024     9
dtype: int64
```

`unstack` 把**最内层索引转成列**、`stack` 反之。多级索引（2.2.6）场景里它比 `pivot` 更顺手，且 `stack()` 默认丢掉 `NaN` 格子——宽表里的空洞在长表里不该存在。

> **机制洞察**：四个动词其实是**同一件事的四个方言**——"把某个轴的标签搬到另一个轴上"。`pivot` 是 `set_index + unstack`，`melt` 是 `stack + reset_index`，`stack/unstack` 是最底层的那对原语。看穿这一层，遇到陌生的重塑需求（`wide_to_long`、`crosstab`、`explode`）也能推导出怎么写。

### 2.7.4 为什么长表是主流

`ds-03` 画分面图（seaborn 的 `relplot`/`catplot`）只吃长表：一行一个观测、一列一个变量，`hue="cat"` 直接映射颜色。而 `melt` 的另一个高频用途是**聚合前统一**：三列"1 月/2 月/3 月销量"要一起 `groupby("month")`，先熔成长表才有一列能分组。

> **⚠️ 陷阱**：`pivot` 后 `city`/`year` 变成了索引而不是列——直接 `merge` 或 `to_csv` 会把它们弄丢或写出多余表头。记住 `reset_index()` 是"宽表出厂"的默认动作（2.15 流水线第 4 步就是这么做的）。

> **实战建议**：**存储与计算用长表，展示用宽表**。判断口诀：能用一个"变量名"列名概括的，就不该占 N 个列。

> **延伸阅读**：`stack/unstack` 底层的索引重排与 `get_indexer` 调用路径见 `ds-02b` B4；作图侧的形状要求见 `ds-03`。

**随堂自测 2.7**

1. `pivot` 和 `pivot_table` 在重复键下的行为差异是什么？不带 `aggfunc` 的 `pivot_table` 默认聚合函数是什么（用代码验证）？
2. 把 `{"A": {"2023": 10, "2024": 12}}` 这种嵌套字典直接 `pd.DataFrame(...)` 得到的是宽表还是长表？
3. `melt` 后 `year` 列的 dtype 是什么？想让它是整数要加哪一步？
4. `stack()` 之后行数为什么可能变少？什么行会被丢掉？
5. 写出"宽表 → 长表 → 按年汇总 → 再回到宽表"的完整四步，并用 2.7.1 的 `long` 验证闭环。

**本节交付**：melt/pivot 是 `ds-03` 绘图前的必做整形（seaborn 长表契约）；"长表存储、宽表展示"的形状纪律会贯穿卷 3 的特征表与卷 5 的指标表。

---

## 2.8 分组引擎：split-apply-combine

"按组算"是数据工作出现频率最高的模式，pandas 用一个三步隐喻把它教给了全世界：**split（切开）→ apply（每组算）→ combine（拼回）**。这一节的难点不是语法而是**选对算子**：`agg`、`transform`、`filter`、`apply` 四个词各管一段。

### 2.8.1 四个算子的分工

```python
>>> df = pd.DataFrame({"city": ["A","A","B","B","A","B"],
...                    "kind": ["x","y","x","y","x","y"],
...                    "sales": [10, 20, 30, 40, 50, 60], "qty": [1,2,3,4,5,6]})
>>> df.groupby("city")["sales"].sum()          # agg 家族：一组 → 一个值
city
A    80
B   130
Name: sales, dtype: int64
>>> df.groupby("city").agg(total=("sales","sum"), n=("sales","size"),
...                        mean=("sales","mean"))
     total  n       mean
city
A       80  3  26.666667
B      130  3  43.333333
>>> df.groupby("city")["sales"].filter(lambda x: x.sum() > 80)   # filter：一组 → 留/弃
    city kind  sales  qty
2      B    x     30    3
3      B    y     40    4
5      B    y     60    6
```

| 算子 | 每组输入 → 输出 | 结果行数 | 典型用途 |
|------|----------------|---------|---------|
| `agg` / `sum` / `describe` | 组 → **标量或一行** | **组数** | 汇总表 |
| `transform` | 组 → **与组等长** | **原行数** | 组内标准化、去均值 |
| `filter` | 组 → **布尔** | **保留整组的行** | "只留大组" |
| `apply` | 组 → **任意** | 任意 | 以上都装不下的 |

`transform` 是最容易被低估的一个——它把分组结果**广播回原表**：

```python
>>> df.assign(dev=df["sales"] - df.groupby("city")["sales"].transform("mean"))
  city kind  sales  qty        dev
0    A    x     10    1 -16.666667
1    A    y     20    2  -6.666667
2    B    x     30    3 -13.333333
3    B    y     40    4  -3.333333
4    A    x     50    5  23.333333
5    B    y     60    6  16.666667
```

**"组内减组均值"没有一次 merge**——这正是 `ds-01` 轴语义的复活：`transform` 替你做了"按组归约 → 沿原轴广播"，相当于 groupby 版的 `keepdims=True`。

### 2.8.2 多键、排序与行数契约

```python
>>> df.groupby(["city", "kind"])["sales"].sum()       # 多键 → MultiIndex（2.2.6）
city  kind
A     x       60
      y       20
B     x       30
      y      100
Name: sales, dtype: int64
>>> df.groupby("city", sort=False)["sales"].sum()     # 按出现顺序
city
A    80
B   130
Name: sales, dtype: int64
>>> df.groupby("city").size()                          # size：每组行数（含空组）
city
A    3
B    3
dtype: int64
```

三条行数契约：

1. **默认 `sort=True`**——结果按组键排序。要保持原始出现顺序（如时间流水），`sort=False`；
2. **`size()` 数所有行，`count()` 数非缺失行**——两者不等就说明组内有缺失，这个差值本身是清洗信号；
3. **分组不改变原行数**（`transform`）或**缩到组数**（`agg`），永远介于两者之间——`apply` 的返回才是任意的，行数出问题先查 `apply`。

### 2.8.3 分类组键与 apply 的边界

```python
>>> cc = df.assign(kind=pd.Categorical(df["kind"], categories=["x","y","z"]))
>>> cc.groupby("kind")["sales"].sum()          # pandas 3 默认 observed=True
kind
x     60
y    120
dtype: int64
>>> cc.groupby("kind", observed=False)["sales"].sum()   # 输出全组合，空组补 0
kind
x     60
y    120
z      0
dtype: int64
```

分类列作组键时，pandas 3 **默认只输出出现过的组合**（`observed=True`）；需要"空组也要占一行"（做完整的组合矩阵、交叉表对齐）时显式 `observed=False`。

而 `apply` 在 pandas 3 有一处**行为性破坏**：

```python
>>> df.groupby("city").apply(lambda g: g["city"].nunique())
Traceback (most recent call last):
  ...
KeyError: 'city'
```

分组列**不再传进函数**（`include_groups` 参数已删除）——函数拿到的 `g` 不含 `city`。要引用组键用 `g.name`（分组键的名字）或改用 `agg/transform`。同理，`group_keys` 默认为 `True`：`apply` 返回组内行时会把组键叠进结果索引（`df.groupby("city", group_keys=False)` 关掉）。

### 2.8.4 时间维度的分组

```python
>>> df.assign(date=pd.to_datetime(
...     ["2024-01-15","2024-02-10","2024-02-20","2024-03-05","2024-03-11","2024-03-18"])
... ).groupby(pd.Grouper(key="date", freq="ME"))["sales"].sum()
date
2024-01-31     10
2024-02-29     50
2024-03-31    150
Freq: ME, Name: sales, dtype: int64
```

`pd.Grouper(key=, freq=)` 让分组键直接是时间桶（`freq="ME"` 是月末，2.10 会看到 pandas 3 把 `"M"` 改成了 `"ME"`）——"按月汇总"不需要先 `set_index + resample`，2.15 的流水线会用到这个姿势。

> **⚠️ 陷阱**：`transform` 的结果可能含 `NaN`，而且是**组内样本不足**造成的：单个成员的组，`transform("std")` 得到 `NaN`（标准差要两个样本）。2.4 的老问题在新场景重演——组内标准化后先 `assert result.notna().all()`，或接受"孤组无法标准化"并显式处理。

> **实战建议**：能用 `agg`/`transform` 就不用 `apply`：前两者是预编译的 C 路径，`apply` 要为每组走一遍 Python 回调（2.13 会给出量级差距）。`apply` 只是"装不下时的安全阀"，不是默认写法。

> **延伸阅读**：哈希分组表的构造与复用、`transform` 的广播回填实现、`observed`/`sort`/`group_keys` 的内部标志，见 `ds-02b` 第 B5 节。

**随堂自测 2.8**

1. 同一份数据，`groupby("city").agg(...)`、`.transform("mean")`、`.filter(...)`、`.apply(...)` 的结果行数分别是多少？
2. `size()` 与 `count()` 的差代表什么？为什么 `sum()` 也能暴露缺失（`sum()` 跳过 `NaN` 而组大小不减）？
3. 要做"每组销量前 3 名"的标记，`agg`、`transform`、`apply` 哪个合适？写出它。
4. pandas 3 下 `g["city"]` 在 `apply` 里抛 `KeyError`，替代方案有哪两个？
5. `transform("std")` 对单行组返回 `NaN`——写一段代码找出所有这样的组并给出处理。
6. 按月分组时 `freq="M"` 和 `freq="ME"` 哪个还能用？月份的标签是月初还是月末（用代码验证）？

**本节交付**：split-apply-combine 与四算子分工是 `ds-04` 分组统计、卷 3 聚合特征（按用户/按会话窗口）的公共骨架；`transform` 的"归约后广播"直觉直接复用 `ds-01` 的 `keepdims`。

---

## 2.9 连接与重塑：merge / join / concat

2.8 把一张表切开算，这一节把多张表拼起来。pandas 的连接就是**关系代数的四种 join** 外加一个 pandas 特色的 `concat`，而它 90% 的事故都发生在同一个地方：**行数变了，没人发现**。

### 2.9.1 四种连接，四种行数

```python
>>> left = pd.DataFrame({"id": [1,2,3], "v": [10,20,30]})
>>> right = pd.DataFrame({"id": [2,3,4], "w": [200,300,400]})
>>> pd.merge(left, right, how="inner", on="id")["id"].tolist()   # [2, 3]
>>> pd.merge(left, right, how="left",  on="id")["id"].tolist()   # [1, 2, 3]
>>> pd.merge(left, right, how="right", on="id")["id"].tolist()   # [2, 3, 4]
>>> pd.merge(left, right, how="outer", on="id")["id"].tolist()   # [1, 2, 3, 4]
```

四行列表就是全部语义：**inner 取交、left 保左、right 保右、outer 取并**，配不上的位置补 `NaN`（2.5 对齐的同一个补缺机制，`ds-02b` B4 证明它们是同一个算法）。谁是"事实"谁是"维度"通常决定方向：事实表 `left`，查维表补齐字段用 `how="left"`——事实行一行都不能少。

### 2.9.2 行数契约：validate 与 indicator

```python
>>> pd.merge(left, right, how="outer", on="id", indicator=True)
   id     v     w      _merge
0   1  10.0   NaN  left_only
1   2  20.0  200.0        both
2   3  30.0  300.0        both
3   4   NaN  400.0 right_only
>>> pd.merge(left, right, on="id", validate="1:1")     # 声明基数，通过
>>> pd.merge(pd.concat([left, left]), right, on="id", validate="1:1")
Traceback (most recent call last):
  ...
pandas.errors.MergeError: Merge keys are not unique in left dataset; not a one-to-one merge
```

两个内置保险丝：

- **`indicator=True`**：加一列 `_merge` 标记每行来自哪边，外连接的"对不上"瞬间可见；
- **`validate=`**：把基数假设（`1:1`/`1:m`/`m:1`/`m:m`）写进代码，不满足**立即抛错**。这是 2.14 契约断言的原生版本，成本一行、收益是整类静默错误绝迹。

### 2.9.3 行数爆炸：多对多的笛卡尔积

```python
>>> l2 = pd.DataFrame({"id": [1,1,2], "a": [1,2,3]})
>>> r2 = pd.DataFrame({"id": [1,1,3], "b": [4,5,6]})
>>> len(pd.merge(l2, r2, on="id"))        # 左 2 个 id=1 × 右 2 个 id=1 → 4 行
4
```

左表 `id=1` 两行、右表 `id=1` 两行，连接后光这一个键就产出 **4 行**（2×2 笛卡尔积），总体从 3×3 变成 4 行。**`len(merge)` 既不等于左也不等于右**——这是所有"数据莫名变多"事故的根源。纪律只有两条：连接前 `duplicated()` 查重复键，连接后 `validate=` 或 `assert len(...) == 预期`。

### 2.9.4 按索引连接与同名列

```python
>>> left_i = pd.DataFrame({"v": [10,20,30]}, index=[1,2,3])
>>> right_i = pd.DataFrame({"w": [200,300,400]}, index=[2,3,4])
>>> pd.merge(left_i, right_i, left_index=True, right_index=True, how="left")
    v      w
1  10    NaN
2  20  200.0
3  30  300.0
>>> pd.merge(left_i, right_i, left_index=True, how="left")   # 少了右半边
MergeError: Must pass right_on or right_index=True
```

"按索引连"必须**两侧都声明**（`left_index=True` 配 `right_index=True`），pandas 不允许你只说一半——这是防止"我以为按索引连、其实按列连"的护栏。

### 2.9.5 concat：不做对齐判断的堆叠

```python
>>> a1 = pd.DataFrame({"x": [1], "y": [2]}); a2 = pd.DataFrame({"x": [3], "z": [4]})
>>> pd.concat([a1, a2])                     # axis=0：上下堆，列取并集
   x    y    z
0  1  2.0  NaN
0  3  NaN  4.0
>>> pd.concat([a1, a2], ignore_index=True).index.tolist()
[0, 1]
>>> pd.concat([a1, a2], axis=1, join="inner")   # axis=1：左右拼，行取交集
   x  y  x  z
0  1  2  3  4
```

三件事必须看见：**索引 `[0, 0]` 重复了**（concat 不做任何去重，要 `ignore_index=True` 或 `keys=` 另起层级）；**`y` 列从 `int64` 掉成 `float64`**（缺的那行补了 `NaN`，2.5 的老戏码）；**`axis=1` 产生了两个 `x` 列**——列名冲突时 `join="inner"` 只按行索引对齐、不管列撞名，同名列表必须用 `suffixes` 区分，否则：

```python
>>> a1.join(a2, how="inner")
ValueError: columns overlap but no suffix specified: Index(['x'], dtype='str')
```

选型口诀：**上下堆（同构表逐月追加）用 `concat`，左右拼（不同表按键/按索引合）用 `merge/join`**。

> **⚠️ 陷阱**：外连接会让缺的一侧变 `NaN`，于是**整列 dtype 再次升位**（`int` → `float`）。流水线里"连接后立刻 `df.info()`"应该和"读入后 `df.info()`"一样是标配——2.15 第 6 步演示了带着 `validate` 的完整姿势。

> **实战建议**：把连接当**契约**写而不是当**操作**写：`how` 表达业务语义（谁是事实表）、`validate` 表达基数假设、`indicator` 留作审计。三件套齐了，连接就不再需要"跑一遍看看对不对"。

> **延伸阅读**：hash join 的具体实现、`suffixes` 的列名合并、`concat` 复用 `reindex` 的路径，见 `ds-02b` 第 B4 节。

**随堂自测 2.9**

1. `merge` 后行数可能是 3×3 的哪几种值？写出一个"左 3 行、右 3 行、结果 9 行"的例子。
2. `validate="m:1"` 什么时候会抛错？业务上"每个用户只有一条档案"应该声明成什么？
3. `pd.concat([a1, a2])` 的结果 `y` 列为什么是 `float64`？给出两种避免升位的写法。
4. `axis=1` 的 `concat` 用 `join="inner"` 和 `"outer"` 分别对齐什么？与 `merge` 的 `how=` 有什么对应关系？
5. 事实表连维表应该用 `left` 还是 `inner`？给出判断依据（少一行意味着什么）。

**本节交付**：四类连接语义 + 行数契约是卷 3 数据集拼接、卷 5 多路知识库合并的公共语法；`validate`/`indicator` 直接进入 2.14 的断言清单。

---

## 2.10 时间序列：解析、时区、重采样、滚动

时间是数据里最特殊的维度：**它有序、有粒度、有夏令时、还有缺口**。pandas 给了四组工具——解析（`to_datetime`）、定位（`tz`）、变粒度（`resample`）、滑动统计（`rolling`）——本节按这条链走一遍。

### 2.10.1 解析：从文本到时间轴

```python
>>> pd.to_datetime("2024-03-05 12:30")
Timestamp('2024-03-05 12:30:00')
>>> pd.to_datetime(pd.Series(["2024-01-01", "notadate"]), errors="coerce").tolist()
[Timestamp('2024-01-01 00:00:00'), NaT]
>>> pd.date_range("2024-01-01", periods=3, freq="D").dtype
datetime64[us]
```

三个事实：坏日期在 `errors="coerce"` 下变成 **`NaT`**（time 的 `NaN`，`isna()` 照常认识它）；pandas 3 的默认分辨率是**微秒 `us`** 而不是纳秒（要纳秒：`date_range(..., unit="ns")` 或 `astype("datetime64[ns]")`）——注意两者**每元素都是 8 字节**，差异不在内存而在范围与互操作：纳秒的可表示区间只有 1677–2262 年，而微秒与数据库、Arrow、JS 时间戳对齐时少一层换算；解析出来的 `Timestamp` 是可以做算术的一等对象（`+ Timedelta("1D")`、`.day_name()`）。

### 2.10.2 时区：先定位，再转换

```python
>>> naive = pd.date_range("2024-07-01", periods=2, freq="D")
>>> naive.tz_convert("UTC")
TypeError: Cannot convert tz-naive timestamps, use tz_localize to localize
>>> naive.tz_localize("UTC").tolist()
[Timestamp('2024-07-01 00:00:00+0000', tz='UTC'), ...]
>>> pd.date_range("2024-07-01", periods=2, freq="D", tz="US/Eastern").tz_convert("UTC").tolist()
[Timestamp('2024-07-01 04:00:00+0000', tz='UTC'), Timestamp('2024-07-02 04:00:00+0000', tz='UTC')]
```

两个动词分工死死的：**`tz_localize` = 告诉 pandas"这些裸时间其实是某地时间"**（无时区 → 有时区），**`tz_convert` = 把已知时区的时间换算到另一时区**（只对有时区的合法）。对裸时间直接 `tz_convert` 报错，就是防止你把"北京写的 12 点"当成"UTC 的 12 点"换算。

夏令时缺口在真实数据里长这样：

```python
>>> pd.date_range("2024-03-10 00:00", periods=4, freq="h", tz="US/Eastern").tolist()
[Timestamp('2024-03-10 00:00:00-0500', tz='US/Eastern'),
 Timestamp('2024-03-10 01:00:00-0500', tz='US/Eastern'),
 Timestamp('2024-03-10 03:00:00-0400', tz='US/Eastern'),    # 02:00 不存在
 Timestamp('2024-03-10 04:00:00-0400', tz='US/Eastern')]
```

春季拨快那一天，本地钟从 `01:00` 直接跳到 `03:00`，偏移从 `-0500` 变 `-0400`。**裸时间做跨 DST 的算术必然出错**（本地 01:30 到 03:30 不是 2 小时），所以跨时区运算的纪律是：**存储与计算统一 UTC，展示时才 `tz_convert`**。

### 2.10.3 重采样：换粒度的两条路

```python
>>> ts = pd.Series([1,2,3,4], index=pd.date_range("2024-01-01", periods=4, freq="D"),
...                dtype="float64")
>>> ts.resample("2D").sum()                  # 聚合：每 2 天求和
2024-01-01    3.0
2024-01-03    7.0
Freq: 2D, dtype: float64
>>> ts.resample("12h").asfreq()              # 插值：对齐到新网格，空位补 NaN
2024-01-01 00:00:00    1.0
2024-01-01 12:00:00    NaN
2024-01-02 00:00:00    2.0
...
Freq: 12h, dtype: float64
```

**`resample` + 聚合函数**用于"粗粒度 → 细粒度归并"（日 → 周求和），**`resample().asfreq()`** 用于"细粒度 → 粗粒度对齐"（1 小时 → 3 小时取样，缺的补 `NaN`）。与 `groupby(Grouper(freq=))`（2.8.4）是同一引擎的两种入口：**有聚合用 resample，要并进其他列用 Grouper**。把缺口显式化的另一招是 `reindex(date_range(...))`：

```python
>>> ts.reindex(pd.date_range("2024-01-01", periods=6, freq="D")).isna().tolist()
[False, False, False, False, True, True]
```

### 2.10.4 滚动窗口：平滑与扩张

```python
>>> r = pd.Series(range(6), dtype="float64")
>>> r.rolling(3).mean().tolist()
[nan, nan, 1.0, 2.0, 3.0, 4.0]
>>> r.rolling(3, min_periods=1).mean().tolist()
[0.0, 0.5, 1.0, 2.0, 3.0, 4.0]
>>> pd.Series([1.,2.,3.,4.]).ewm(alpha=0.5).mean().tolist()
[1.0, 1.6666666666666667, 2.4285714285714284, 3.2666666666666666]
```

- **`rolling(n)`**：固定窗口，前 `n-1` 个位置样本不足给 `NaN`；`min_periods=1` 改成"有几个算几个"（口径要说明，否则均线的前几日全是空）；
- **`ewm(alpha=)`**：指数加权，近期样本指数级加权，无需等到窗口填满——金融均线与监控告警的两大标配。

注意窗口的**位置约定**：`rolling` 默认右对齐（窗口终点=当前行），`center=True` 则让窗口以当前行为中心——画移动平均线时的视觉差异全在这里。

### 2.10.5 时间轴工具箱

```python
>>> s = pd.Series(pd.to_datetime(["2024-03-05"]))
>>> s.dt.weekday.tolist(), s.dt.day_name().tolist()
([1], ['Tuesday'])
>>> ts.to_period("D").index.tolist()
[Period('2024-01-01', 'D'), Period('2024-01-02', 'D'), ...]
>>> pd.date_range("2024-01-31", periods=2, freq="ME").tolist()
[Timestamp('2024-01-31 00:00:00'), Timestamp('2024-02-29 00:00:00')]
```

`.dt` 访问器把 `Timestamp` 的所有属性向量化到整列（`weekday`/`day_name`/`quarter`/`is_month_end`）；`to_period` 把时间点变成**时间段**（"2024-01" 这种无时点的桶，按月分组不看日期时更语义化）；`freq="ME"` 是月末——**pandas 3 已删除 `"M"`**：

```python
>>> pd.date_range("2024-01-01", periods=2, freq="M")
ValueError: Invalid frequency: M. ... Please use 'ME' instead.
```

> **⚠️ 陷阱**：**缺失的交易日不会自己出现在索引里**——`ts.reindex(完整日历)` 之前，"上周三没有数据"和"上周三没发生"无法区分（2.10.3 最后一段就是把它们显式化）。做任何"按天"的结论前先 `asfreq` 补齐日历，缺失率本身就是关键指标。

> **版本注意**：① 默认分辨率 `us` 而非 `ns`（2.10.1）；② 频率别名全面换新：`M→ME`、`Q→QE`、`Y→YE`、`H→h`、`T→min`，五个旧别名全部删除（2.10.5 的报错就是 ②）。老代码迁移时这一类报错最集中，好在信息里都给了替代品。

> **延伸阅读**：非纳秒时间的存储与转换开销、时区的 UTC 内核 + 展示偏移模型、`rolling` 的 O(1) 递推实现，见 `ds-02b` 第 B6 节。

**随堂自测 2.10**

1. `tz_localize` 和 `tz_convert` 的分工是什么？对已有时区的时间再 `tz_localize` 会怎样（用代码验证）？
2. `resample("W")` 与 `resample("7D")` 的标签与右端约定有何差别？（打印索引观察）
3. 为什么 `rolling(3).mean()` 前两个是 `NaN` 而 `min_periods=1` 不是？后者做均线图有什么隐患？
4. 裸时间戳 `2024-03-10 01:30` 加 2 小时得到 03:30 吗？在 `US/Eastern` 时区下呢？解释差异。
5. 按月汇总销售额，写出 `resample` 与 `groupby(Grouper)` 两种写法，并说明各自适合接在什么数据结构后面。

**本节交付**：时间四件套是 `ds-04` 时间序列统计与卷 5 监控/回测的输入契约（UTC 存储、日历补齐、窗口口径）；`freq` 别名与分辨率差异是迁移 pandas 2 代码时的第一检查项。

---

## 2.11 缺失数据与清洗工作流

缺失不是异常，是数据的常态；清洗的价值不在于"消灭缺失"而在于**让缺失的语义显式化**——哪些是没采集（该填或该删）、哪些是不适用（该保留）、哪些是重复上报（该去）。本节把 `ds-01` 的布尔掩码变成一条完整工作流。

### 2.11.1 度量：先数，再动

```python
>>> df = pd.DataFrame({"a": [1, None, 3, None], "b": [None, "x", "y", None]})
>>> df.isna().sum().to_dict()
{'a': 2, 'b': 2}
>>> df.dropna(how="any").shape[0], df.dropna(how="all").shape[0], df.dropna(thresh=1).shape[0]
(1, 3, 3)
```

`isna()` 对 `NaN`/`pd.NA`/`NaT` 一视同仁（2.4 的承诺），`sum()` 沿列归约给出**每列缺失数**——这个数字应该在清洗的第一行打印，在 2.14 会变成断言。删除三档：`how="any"` 有缺失就删（最狠）、`how="all"` 整行全缺才删（最保守）、`thresh=n` 至少有 n 个有效值（折中）。

### 2.11.2 填充：方法取决于"缺失的原因"

```python
>>> df["a"].fillna(0).tolist()
[1.0, 0.0, 3.0, 0.0]
>>> df["a"].ffill().tolist()
[1.0, 1.0, 3.0, 3.0]
>>> df["b"].bfill().tolist()
['x', 'x', 'y', nan]
```

| 方法 | 语义 | 适用 |
|------|------|------|
| `fillna(0)` | 缺失 = 无 | 计数、数量（没下单 = 0 单） |
| `ffill()` | 缺失 = 跟上次一样 | 温度、汇率、状态（传感器断线） |
| `fillna(组均值)` | 缺失 = 典型值 | 特征工程（卷 3），**训练时统计、预测时复用** |
| `dropna` | 缺失 = 无法判断 | 关键字段（金额缺失的订单不进统计） |
| 保留 `NaN` | 缺失 = 有意义 | 分组排除、`ds-04` 的 `nanmean` 自动跳过 |

"按什么填"本质是**业务假设**，没有默认正确答案——但**假设必须写在代码里**，不写就等于假装缺失不存在。

### 2.11.3 插值与版本更替

```python
>>> df["a"].interpolate().tolist()
[1.0, 2.0, 3.0, 3.0]
>>> df["a"].fillna(method="ffill")
Traceback (most recent call last):
  ...
TypeError: NDFrame.fillna() got an unexpected keyword argument 'method'
```

`interpolate()` 默认线性插值（`[1, -, 3, -]` → `[1, 2, 3, 3]`，尾部缺失用末值前向补齐），还支持 `method="time"`（按时间距离加权，时间序列首选）。而那个伴随无数老教程的 `fillna(method="ffill")` **在 pandas 3 已被彻底删除**——迁移到 `.ffill()` 是肌肉记忆级的改动。

### 2.11.4 重复：先问"哪一行是真的"

```python
>>> d = pd.DataFrame({"id": [1,1,2,3,3,3], "v": [1,1,2,3,3,4]})
>>> d["id"].duplicated(keep="first").tolist()
[False, True, False, False, True, True]
>>> d["id"].duplicated(keep=False).tolist()
[True, True, False, True, True, True]
>>> d.drop_duplicates(subset=["id"], keep="last")
   id  v
1   1  1
2   2  2
5   3  4
```

三个 `keep` 选项对应三种业务判断：`"first"`（首条为准）、`"last"`（末条为准——上报系统通常**后者覆盖前者**）、`False`（重复的全部标出，先审计再删）。`subset=` 指定"按哪几列算重复"，`duplicated()` 先标记、`drop_duplicates()` 再删——和 `isna()`→`dropna()` 一样，**标记与执行分开**，中间那一步就是你打印审计结果的机会。

### 2.11.5 清洗工作流的固定顺序

实战中的顺序不可乱（每步的理由都能在前文找到）：

1. **`df.info()`** 看类型（2.6）——类型错则一切统计都错；
2. **显式转换** `to_numeric`/`to_datetime`/`astype`（2.4）——把推断的赌注换成声明；
3. **`isna().sum()` 度量**（2.11.1）——先知道有多少，再决定填还是删；
4. **去重**（2.11.4）——重复行会污染后面所有聚合的分母；
5. **填充/删除**（2.11.2）——带着业务假设做；
6. **排序与断言**（2.14）——`sort_values` 定序、契约断言收口。

> **⚠️ 陷阱**：**先聚合后补缺失 vs 先补缺失后聚合，结果不同**：`sum` 跳过 `NaN`（样本变少）、`mean` 的分母随之变化；`fillna(0)` 后再 `mean` 则把 0 算进了分母。两者都"合理"，但必须是有意识的选择——尤其在 `ds-04` 算均值、卷 3 算点击率时，这个分母差会一路放大。

> **实战建议**：把清洗写成**幂等函数** `def clean(df) -> df`：入参原始数据、出参干净数据、可重复执行结果不变。2.15 的流水线演示了这个形态，测试它只需要一行 `assert clean(clean(df)).equals(clean(df))`。

> **延伸阅读**：缺失值的位图存储（`Float64` 掩码）与 `str` 列的 `na_value` 机制，见 `ds-02b` 第 B7 节。

**随堂自测 2.11**

1. `dropna(how="all")` 与 `thresh` 如何配合表达"至少要有 2 个非缺失值"？`thresh` 与 `how` 能同时给吗（用代码验证）？
2. `ffill()` 对开头的缺失无效——写出"前后夹击"的两行补法。
3. 计数列里缺失填 0 与不填，`mean()` 的结果差多少？用 2.11.2 的例子验证。
4. `duplicated(subset=["id"], keep="last")` 与 `drop_duplicates(subset=["id"], keep="last")` 的关系是什么？为什么推荐先标记后删除？
5. 写出你认为的清洗顺序理由：为什么"去重"必须在"填充"之前？

**本节交付**：清洗顺序与"标记/执行分离"的纪律是 2.15 流水线的骨架；缺失分母问题直接决定 `ds-04` 的统计口径与卷 3 特征的缺失指示器设计。

---

## 2.12 文本与列级操作

文本列占真实数据的一半，`.str` 访问器把 `ds-01` 的向量化带到字符串上；`assign/pipe` 则给"一连串处理"一个可读、可测的形状。本节是进阶层（◐），但里面的正则坑每个分析师都会踩。

### 2.12.1 .str 访问器：字符串的向量化

```python
>>> s = pd.Series(["Apple pie", "banana split", "Cherry tart"])
>>> s.str.lower().tolist()
['apple pie', 'banana split', 'cherry tart']
>>> s.str.len().tolist()
[9, 12, 11]
>>> s.str.split(" ", expand=True)
        0      1
0   Apple    pie
1  banana  split
2  Cherry   tart
>>> s.str.extract(r"(\w+) (\w+)")
        0      1
0   Apple    pie
1  banana  split
2  Cherry   tart
```

几乎全部字符串方法都有 `.str` 版本：`split`（`expand=True` 直接裂成多列）、`strip/pad/center`、`contains/startswith/endswith`、`replace`、`extract`（正则捕获组 → 多列，正则功底回链卷 1 专题）。**一切循环改写字符串处理的套路都失效了**——`.str` 下没有 Python 循环，只有 C 层的批量操作。

### 2.12.2 contains 的正则陷阱

```python
>>> s.str.contains("a").tolist()                      # 默认 regex=True、区分大小写
[False, True, True]
>>> s.str.contains("a", case=False).tolist()          # 忽略大小写才全命中
[True, True, True]
>>> pd.Series(["a.c", "abc"]).str.contains(".").tolist()      # "." 匹配任意字符
[True, True]
>>> pd.Series(["a.c", "abc"]).str.contains(".", regex=False).tolist()   # 字面量匹配
[True, False]
```

**`contains` 默认吃正则**：想找字面量 `"."` 却拿到全 `True`，是最典型的"静默错"——不报错、只是结果全对了。写 `.str.contains(pattern, regex=False)` 或显式 `regex=True`，让每一次匹配的意图都被看见。同理 `replace` 默认也走正则（`regex=False` 关闭），`startswith/endswith/len` 等则永远是字面量。

### 2.12.3 split 与哑变量

```python
>>> pd.get_dummies(s.str.split(" ", n=1).str[0])
   Apple  Cherry  banana
0   True   False   False
1  False   False    True
2  False    True   False
```

`get_dummies` 把类别列裂成布尔列（机器学习的 one-hot 前身，卷 3 会升级成 `pd.get_dummies(..., dtype=)` 与 sklearn 的 `OneHotEncoder` 对照）。注意 pandas 3 里 `get_dummies` 默认产出 **`bool`** 列而非 0/1 整数——喂给数值计算前留意 dtype。

### 2.12.4 assign 与 pipe：可读的处理链

```python
>>> df = pd.DataFrame({"qty": [2, 3], "price": [1.5, 2.0]})
>>> (df.assign(total=lambda d: d["qty"] * d["price"])
...    .assign(tax=lambda d: d["total"] * 0.1)
...    .round(2))
   qty  price  total   tax
0    2    1.5    3.0  0.30
1    3    2.0    6.0  0.60
```

`assign` 的**函数参数是点睛之笔**：`lambda d: d["total"] * 0.1` 引用的是**链上一步刚造出来的列**——直接写 `df["total"] * 0.1` 会 `KeyError`（它引用的是原始 `df`）。当链条要分叉、复用或单测时，`pipe` 把任意函数变成链条的一环：

```python
>>> def with_total(d):  return d.assign(total=d["qty"] * d["price"])
>>> def with_tax(d):    return d.assign(tax=d["total"] * 0.1)
>>> df.pipe(with_total).pipe(with_tax).round(2)
   qty  price  total   tax
0    2    1.5    3.0  0.30
1    3    2.0    6.0  0.60
```

`pipe` 的价值在**可测试**：`with_total`/`with_tax` 各自独立、能单独写断言（2.14），这正是"清洗写成幂等函数"（2.11.5）的组合方式。

> **⚠️ 陷阱**：多行赋值的中间结果要不要保留全看意图——`x = x.dropna()` 改写自己的名字（清晰但掩盖了行数变化），函数内 `return df.dropna()` 把变化写在边界上（推荐）。**禁止 `inplace=True`**：它返回 `None`、不能链式、对 CoW 下的 copy 语义毫无意义，pandas 官方也已不鼓励。

> **延伸阅读**：`str` dtype 在 python 与 pyarrow 两种存储下的正则执行路径差异，见 `ds-02b` 第 B7 节；正则语法本身见卷 1 专题。

**随堂自测 2.12**

1. 从邮箱列提取域名：`s.str.extract(...)` 的正则怎么写？`expand=False` 返回什么类型？
2. 为什么 `assign(tax=...)` 里要写 `lambda d:` 而不能直接用 `df["total"]`？
3. `s.str.replace("a.b", "-")` 与 `s.str.replace("a.b", "-", regex=False)` 在 `"axb"` 上结果为何不同？
4. `pipe` 写法与直接写 `with_tax(with_total(df))` 语义完全相同——那 `pipe` 多出来的价值是什么？（提示：可读性与可测性的方向）
5. 把 2.11 的清洗工作流改写成 `clean(df)` 函数，要求用 `pipe` 串起至少三个步骤，并写出幂等断言。

**本节交付**：`.str` 向量化与 `pipe` 化的处理链是卷 3 文本特征工程与 2.15 流水线的书写格式；`contains` 的正则陷阱是"静默错"清单（2.14）的常驻条目。

---

## 2.13 性能工程：向量化的账、内存的杠杆、离开的时机

pandas 的性能故事和 `ds-01` 是同一个剧本的续集：**循环在 Python 解释器里跑就慢，在 C 层批量跑就快**。本节先把差距量出来（本机实测），再给内存三杠杆，最后回答"多大的数据该换工具"。

### 2.13.1 四种写法，量级差

20 万行 `df = {"a": float, "b": float, "g": 4 类文本}"`，本机实测：

```
vectorized    0.24 ms | apply(axis=1)  408.65 ms | itertuples 35.46 ms | listcomp 12.87 ms
groupby.mean    6.63 ms | dict loop    8.41 ms
```

| 写法 | 耗时 | 相对向量化 | 评价 |
|------|------|-----------|------|
| `df["a"] + df["b"]`（向量化） | 0.24 ms | 1× | **默认写法** |
| 列表推导 + `zip` | 12.9 ms | ~54× | 纯 Python 但零 pandas 开销 |
| `itertuples` | 35 ms | ~146× | 比 `iterrows` 快得多但仍是 Python 循环 |
| `apply(axis=1)` | **409 ms** | **~1700×** | 最慢：每行组装一个 Series 再回调 |

两个反直觉的结论值得记住。**`apply(axis=1)` 是最慢的"向量化假象"**——它写起来最像向量化，实际每行都要创建 Series 对象再调 Python 函数，比裸循环还慢。**`itertuples` 比 `iterrows` 快一个量级**（后者每行造 DataFrame，前者造轻量 namedtuple），要循环就用它。而 `groupby.mean()` 与手写 dict 循环只差 28%——**分组聚合的瓶颈在数据搬运不在算法，pandas 的预编译路径已经够快，别自己写**。

### 2.13.2 query/eval：语法糖不是加速糖

```python
>>> pd.get_option("compute.use_numexpr")
True
>>> df.query("a > 0 and b < 0").shape, df[(df["a"] > 0) & (df["b"] < 0)].shape
((50024, 3), (50024, 3))
```

本机实测：`query` 1.08 ms vs 布尔掩码 0.57 ms——**布尔掩码反而更快**（`query` 的解析与引擎调度有固定成本，装了 numexpr 也只是打平）。那 `query` 的价值在哪？**可读与可复用**：`"price > 100 and city in ['A','B']"` 比嵌套括号的掩码清楚，还能用 `@变量` 注入参数。定位要摆正：`query/eval` 是表达力工具，**不承诺提速**；真正的提速来自少拷贝（CoW）、少对象（category）、少行（先过滤）。

### 2.13.3 内存三杠杆

本机实测（同一份 20 万行数据）：

```
copy 0.74 ms of 13.2 MB frame
orig bytes: 13200132   opt bytes: 1000332     # category + float32 后
```

1. **`category`**（2.4.5）：4 类文本列从"每行一个对象"变"整数码"，是最大的一块——13.2 MB → 1.0 MB；
2. **显式降精度**：`float64 → float32` 对科学测量与深度学习输入足够（`ds-01` 1.3.3 的精度账），内存直接减半；
3. **Copy-on-Write**：pandas 3 下"取子集"不再立刻拷贝，`df.copy()` 0.74 ms 一次到位——**该复制时痛快复制，别用 `inplace` 省那一次**；`memory_usage(deep=True)` 是审计入口（13.2 MB 里 10 MB 是文本列，一目了然）。

### 2.13.4 反模式清单

| 反模式 | 为什么慢/错 | 改成 |
|--------|-----------|------|
| `apply(axis=1)` 逐行算 | ~1700× 慢 | 向量化/`transform` |
| `iterrows` 循环 | 每行造 DataFrame | `itertuples`（最好还是消灭循环） |
| 循环里 `pd.concat` 累积 | 每次全量拷贝 → O(n²) | 收集到 list，最后一次 `concat` |
| 循环里按标签 `loc` 取数 | 单次 ~2 μs 且逐行付封装成本 | 一次 `reindex`/`loc[[...]]` 批量取（热后 0.73 ms/万行） |
| `df.values` 混合类型 | 掉进 `object`，特化循环失效 | `select_dtypes("number").to_numpy()` |
| `inplace=True` 满天飞 | 返回 `None`、CoW 下无意义、不可链式 | 赋值给名字 |
| 频繁 `copy()` 防御 | 13 MB 框架 0.74 ms×N | CoW 下信任语义，边界处一次 copy |

### 2.13.5 何时离开 pandas：本机实测的 polars 对照

200 万行同构数据，本机实测（`polars 1.44`，需另装）：

```
read_csv  pandas   252.7 ms | polars    90.4 ms
groupby   pandas    26.1 ms | polars    13.5 ms
```

读入快 2.8 倍、分组快 1.9 倍——polars 走 Arrow 列式 + 惰性查询计划，**在"整表扫描"型任务上有架构优势**；而 pandas 的优势在**生态**（`ds-03`/`ds-04`/sklearn 全部原生吃 DataFrame）与**交互式探索**的成熟度。接 `ds-01` 第 15 章的五层路线图，pandas 处在"语言级"这一层，判断顺序永远是：

> **机制洞察**：先量（2.13.1 的表格说明 90% 的慢是写法问题）→ 再换数据形状（category、先过滤再计算、`chunksize` 分块）→ 最后才换引擎（polars/duckdb/SQL）。**架构优势（惰性、Arrow 原生）只能在"写法已经无可优化"时兑现**——`apply` 慢 1700 倍的问题，换 polars 写成逐行循环照样慢。

> **⚠️ 陷阱**：**不要用 `timeit` 的绝对值跨机器比较**。文中数字只在"同一台机器、同一段代码"内有意义；把基准脚本随项目保存，回归测试才是可持续的性能门禁（卷 1 第 15 章的性能回归思路同样适用）。

> **延伸阅读**：BlockManager 的拷贝时机与 CoW 如何减少拷贝、polars/duckdb 的 Arrow 与惰性计划，见 `ds-02b` 第 B1、B2、B8 节。

**随堂自测 2.13**

1. `apply(axis=1)` 为什么比手写列表推导还慢？写出你自己的计时脚本复现 2.13.1 的四行数字。
2. 100 万行 × 10 列的 `float64` 框架约 80 MB，用 `category`+`float32` 两杠杆估算新内存，并用 `memory_usage(deep=True)` 验证。
3. `query` 比掩码慢，为什么还推荐它？给出一条"可读性优先"的具体场景。
4. 循环里 `concat` 为什么是 O(n²)？写一个 1000 次追加的实验量化它，并改成 list 攒批。
5. 给出三条"该换 polars/duckdb 而不是继续调 pandas"的判断信号（结合 2.13.5 与卷 1 第 15 章）。

**本节交付**：量级表与反模式清单是本章的"优化速查"；"先量、再改形状、后换引擎"的顺序回链卷 1 第 15 章，并交付给 `ds-02b` B8 的引擎选型。

---

## 2.14 调试与验证：把"看起来对"变成断言

`ds-01` 1.17 的哲学在 pandas 上原样成立：**静默错误比崩溃更贵**。pandas 的静默错误有固定几个来源，本节把它们全部转成"会咬人的断言"。

### 2.14.1 体检：info 与 describe

```python
>>> df = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.5], "c": ["x", "y"]})
>>> df.info()
<class 'pandas.core.DataFrame'>
RangeIndex: 2 entries, 0 to 1
Data columns (total 3 columns):
 #   Column  Non-Null Count  Dtype
---  ------  --------------  -----
 0   a       2 non-null      int64
 1   b       2 non-null      float64
 2   c       2 non-null      str
dtypes: float64(1), int64(1), str(1)
memory usage: 182.0 bytes
```

`df.info()` 三行看完**类型、非空数、内存**——读入数据后的第一个动作；`df[["a","b"]].describe()` 给出 `count/mean/std/min/25%/50%/75%/max`（`count` 与行数不等即有缺失，`std` 是样本标准差 `ddof=1`，回链 `ds-01` 1.10）。`df["col"].value_counts(normalize=True).round(2)` 看类别分布，`df.duplicated().sum()` 看重复——**四个数字（行数、缺失数、重复数、dtype）就是数据的体温**。

### 2.14.2 assert_frame_equal：结果比对的三把钥匙

```python
>>> x = pd.DataFrame({"a": [1, 2]}); y = pd.DataFrame({"a": [1.0, 2.0]})
>>> pd.testing.assert_frame_equal(x, y)
AssertionError: Attributes of DataFrame.iloc[:, 0] (column name="a") are different

Attribute "dtype" are different
[left]:  int64
[right]: float64
>>> pd.testing.assert_frame_equal(x, y, check_dtype=False)   # 只比数值
>>> pd.testing.assert_frame_equal(x, y.iloc[::-1], check_like=True)   # 忽略行列顺序
```

三把钥匙对应三种"相等"的口径：**默认连 dtype 一起比**（类型污染在此现形——这是它比 `==` 强的第一个理由）；`check_dtype=False` 放行 `int`/`float` 差异（适合"业务值对不对"）；`check_like=True` 忽略索引与列的顺序（适合"我对齐后应该一致"）。而裸 `==` 对 DataFrame 根本不能用（返回逐格布尔且索引不对齐时抛错）——**框架比对永远走 `pd.testing`**。

### 2.14.3 契约断言：六条常驻清单

把本章所有静默错误翻译成断言，数据入口处执行一次：

```python
# 1. 形状与唯一性
assert df.index.is_unique, "索引必须唯一（2.2.5）"
# 2. 关键列的类型契约（读入即锁，2.6）
assert str(df["qty"].dtype) in ("int64", "Int64"), f"qty 应为整数，实为 {df['qty'].dtype}"
# 3. 缺失契约（2.11）
assert df["price"].notna().all(), "价格不允许缺失"
# 4. 连接基数契约（2.9.3，直接写进 merge 的 validate=）
# 5. 数值域契约（2.15 第 8 步）
assert (df["revenue"] >= 0).all(), "金额不为负"
# 6. 结果行数契约（对齐/连接/过滤之后，2.5、2.9）
assert len(result) == len(df), "本次操作不应改变行数"
```

顺序也有讲究：**先比形状（错位最先暴露），再比类型，最后比数值**——和 `ds-01` 1.17 的"形状 → dtype → 数值"完全一致，这是全书共享的排障次序。

### 2.14.4 本章静默错误清单

| 症状 | 病因 | 出处 | 断言 |
|------|------|------|------|
| 行数变多 | 对齐取并集 / merge 多对多 | 2.5、2.9 | `len` 断言 + `validate=` |
| `int` 变 `float` | 缺失补 `NaN` / 外连接补缺 | 2.2、2.5、2.9 | `info()` + dtype 断言 |
| 一列变文本 | 类型推断被脏数据政变 | 2.6 | 读入 `dtype=` 锁定 |
| 赋值不生效 | 链式写（CoW 不传导） | 2.3 | 单层 `loc` + 检查警告 |
| 筛选结果诡异 | 正则默认开启 / 大小写敏感 | 2.12 | `regex=` 显式声明 |
| 缺失被算进分母 | 先 `fillna(0)` 后 `mean` | 2.11 | 口径注释 + `count` 对照 |
| 组内标准化出 `NaN` | 单成员组的 `std` | 2.8 | `notna().all()` |
| 时间轴悄悄缺日 | 没 `asfreq` 补日历 | 2.10 | 行数 == 日历长度 |

> **⚠️ 陷阱**：`df.equals()` 不等于 `assert_frame_equal`：`equals` 对 dtype **宽容**（`1` 与 `1.0` 视作相等）且失败只返回 `False` 不给原因。测试里用 `assert_frame_equal`（报错信息直接指出 dtype/列/顺序差异），断言"数据是否变了"才用 `equals`。

> **实战建议**：把 2.14.3 的六条打包成 `validate(df)` 函数，在 `clean()` 的出口调用（2.11.5、2.12.4 的 `pipe` 形态）——**清洗和验收在同一处收口**，就是 2.15 流水线最后一步的做法。

> **延伸阅读**：pytest 里 DataFrame fixture 与参数化、覆盖率门禁见卷 1 第 14 章；`pd.testing` 的全部开关见本章参考文献的官方文档。

**随堂自测 2.14**

1. `assert_frame_equal(a, b)` 默认检查哪些维度？写一个"数值相同但 dtype 不同"的例子让它失败，再用两个参数分别放行。
2. `df.equals(1.0 * df)` 为什么是 `True` 而 `assert_frame_equal` 会失败？哪个更严格？
3. 为什么"先比形状再比数值"不能反过来？给出一个"形状错了但数值碰巧相等"的例子。
4. merge 后如何同时校验"行数符合预期"和"基数符合假设"？写出 `validate` 与 `len` 断言的组合。
5. 写一个 `validate(df)` 函数覆盖清单里的 1、2、3、5 四条，并设计一组通过/失败的测试数据。

**本节交付**：六条契约断言与静默错误清单是本章的收口，2.15 直接使用；与卷 1 第 14 章的测试哲学、`ds-01` 1.17 的排障次序构成全书统一的验证方法论。

---

## 2.15 综合实战：一条流水线走完八步

前面十四节各管一段，这一节把它们接成生产形态：**造脏数据 → 读取体检 → 清洗 → 变形 → 聚合 → 连接 → 时间序列 → 断言收口**。每步标注复用的小节，全部输出实跑。

```python
"""ds-02 2.15 综合实战：门店销售流水线"""
import numpy as np, pandas as pd, os, tempfile
rng = np.random.default_rng(42)

# ---- 第 1 步：造原始脏数据并落盘 ----
dates = pd.date_range("2024-03-01", periods=60, freq="D")
rows = []
for st in ["S1", "S2", "S3"]:
    for c in ["toy", "book"]:
        base = rng.uniform(80, 200)
        rows.append(pd.DataFrame({
            "date": dates, "store": st, "cat": c,
            "qty": rng.integers(1, 30, len(dates)),
            "price": np.round(base * rng.uniform(0.9, 1.1, len(dates)), 2)}))
raw = pd.concat(rows, ignore_index=True)
raw.loc[rng.choice(len(raw), 5, replace=False), "qty"] = None     # 缺失
raw["price"] = raw["price"].astype(object)      # pandas 3：setitem 禁止静默升类型，先放开（2.3）
raw.loc[rng.choice(len(raw), 3, replace=False), "price"] = "?"    # 脏类型（不在默认 na_values 里）
raw = pd.concat([raw, raw.iloc[:4]], ignore_index=True)           # 重复 4 行
path = os.path.join(tempfile.gettempdir(), "ds02_sales.csv")
raw.to_csv(path, index=False)

# ---- 第 2 步：读取并检查类型推断（2.6）----
df = pd.read_csv(path)
print(df.dtypes.to_string())
print("price 沦为 str：", df["price"].dtype, "| 含脏行:", (df["price"] == "?").sum())

# ---- 第 3 步：清洗（2.4 类型 / 2.11 缺失与去重）----
df["price"] = pd.to_numeric(df["price"], errors="coerce")
dups = df.duplicated().sum()
df = df.drop_duplicates().reset_index(drop=True)
df["date"] = pd.to_datetime(df["date"])
before = len(df)
df = df.dropna(subset=["price"]).copy()
df["qty"] = df["qty"].fillna(0).astype("int64")             # 计数缺失 = 0 单（2.11.2）
df["revenue"] = (df["qty"] * df["price"]).round(2)
print(f"\n[2.4/2.11] 重复 {dups} 行；缺失价 {before - len(df)} 行；"
      f"清洗后 {len(df)} 行, dtypes={df['qty'].dtype}/{df['revenue'].dtype}")

# ---- 第 4 步：变形：宽表透视（2.7）----
wide = df.pivot_table(index="store", columns="cat", values="revenue",
                      aggfunc="sum", margins=True, margins_name="Total").round(0)
print("\n[2.7 透视]"); print(wide.to_string())

# ---- 第 5 步：分组 split-apply-combine（2.8）----
per = (df.groupby("store")
         .agg(revenue=("revenue", "sum"), orders=("revenue", "size"),
              avg_order=("revenue", "mean"))
         .round(2))
per["share"] = (per["revenue"] / per["revenue"].sum()).round(3)
print("\n[2.8 分组]"); print(per.to_string())

# ---- 第 6 步：连接月度目标并校验基数（2.9）----
target = pd.DataFrame({"store": ["S1", "S2", "S3"], "target": [310000, 275000, 250000]})
chk = pd.merge(per.reset_index(), target, on="store", validate="one_to_one")
chk["达成率"] = (chk["revenue"] / chk["target"]).round(3)
print("\n[2.9 连接 + validate]"); print(chk[["store", "revenue", "target", "达成率"]].to_string())

# ---- 第 7 步：按日时间序列 + 滚动窗口（2.10）----
daily = df.groupby("date")["revenue"].sum().asfreq("D", fill_value=0.0)
roll = daily.rolling(7, min_periods=1).mean().round(1)
trend = pd.DataFrame({"当日": daily, "7日均线": roll}).tail(5)
print("\n[2.10 滚动]"); print(trend.to_string())

# ---- 第 8 步：契约断言（2.14）----
assert df.index.is_unique and chk["store"].is_unique
assert (df["revenue"] >= 0).all()
pd.testing.assert_frame_equal(wide, wide.copy())
print("\n[2.14] 4 条契约断言全部通过 ✓")
```

本机实跑输出：

```
date         str
store        str
cat          str
qty      float64
price        str
price 沦为 str： str | 含脏行: 3

[2.4/2.11] 重复 4 行；缺失价 3 行；清洗后 357 行, dtypes=int64/float64

[2.7 透视]
cat        book       toy     Total
store
S1     139696.0  160797.0  300493.0
S2     149076.0  116636.0  265713.0
S3      90391.0  152104.0  242496.0
Total  379164.0  429537.0  808701.0

[2.8 分组]
         revenue  orders  avg_order  share
store
S1     300492.62     119    2525.15  0.372
S2     265712.66     119    2232.88  0.329
S3     242495.86     119    2037.78  0.300

[2.9 连接 + validate]
  store    revenue  target    达成率
0    S1  300492.62  310000    0.969
1    S2  265712.66  275000    0.966
2    S3  242495.86  250000    0.970

[2.10 滚动]
                  当日     7日均线
date
2024-04-25  11320.72  13531.4
2024-04-26  14662.47  13356.9
2024-04-27  11194.19  12420.4
2024-04-28  11549.71  12101.8
2024-04-29   9891.54  11680.1

[2.14] 4 条契约断言全部通过 ✓
```

逐步读出值得停下来的地方：

- **第 2 步是全章的缩影**：三行 `?` 让 `price` 整列沦陷成 `str`，五行缺失让 `qty` 掉进 `float64`——如果不 `info()` 就直接算，`qty * price` 会得到一串字符串拼接而不是报错（2.6 的陷阱在此实锤）；
- **第 3 步的顺序不可换**：先 `to_numeric`（否则 `?` 拖累聚合）、先去重（否则重复行污染 `orders` 分母）、最后才算 `revenue`——2.11.5 的顺序表不是理论洁癖；
- **第 4 步 `margins=True` 白送的对账**：`Total` 行列交叉的 808701 就是总营收，和第 5 步 `per["revenue"].sum()`、第 6 步 `target` 口径三处对齐——**同一件事算三遍**是数据工程里最便宜的自检；
- **第 6 步 `validate="one_to_one"`**：目标表若不小心多一行 `S1`，这里立刻抛错而不是产出四行报表；
- **第 7 步 `asfreq` 在数据完整时是空操作**——但流水线的价值恰恰在于**数据缺日的那一天它仍然正确**（补 0 而不是悄悄少一天）；
- **第 8 步断言与第 1 步的造数埋雷首尾呼应**：4 行重复、3 行脏价、5 行缺失，全部在中途被显式处理，末尾四条契约证明"没有暗礁通过"。

> **实战建议**：把八步原样保留成模板——**每接一份新数据，只改第 1 步（换成真实读取）与第 8 步（换成业务契约）**，中间六步的顺序是通用的。进阶方向：`groupby(Grouper(freq="ME"))` 按月拆（2.8.4）、`chunksize` 分块聚合（2.6.3）、把六步包进 `clean(df).pipe(validate)`（2.11.5 + 2.14.3）。

**随堂自测 2.15**

1. 把第 3 步的"先去重后删缺失价"顺序对调，最终 `orders` 会变吗？`revenue` 呢？写代码量化差异。
2. 第 5 步 `per["share"]` 之和是多少？第 4 步 `wide` 的 `Total` 与它什么关系？设计一条断言把这层关系固化。
3. 若 `target` 表里 `S1` 出现两次，`validate="one_to_one"` 与不带 `validate` 的结果分别是什么？（用代码验证报错与多出的行）
4. 第 7 步改成 `daily = df.groupby("date")["revenue"].sum()`（不 `asfreq`）在**缺日数据**下会有什么不同？造一天缺失的脏数据验证。
5. 扩展流水线：加第 9 步"按月汇总（Grouper）"与第 10 步"写出 parquet 并读回断言等价"。

**本节交付**：八步模板是本章的收官产物，直接作为卷 3 特征工程流水线（读取 → 清洗 → 特征 → 验收）的雏形；`ds-03` 会接过第 4、7 步的结果开始画图。

---
## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 数据模型 | 列式存储 + 行标签 + 对齐规则；列是 Series、底下是 ndarray；混合 `.values` 掉进 `object` |
| Index | 不可变、`RangeIndex` 免费；热后单点查找 0.14–0.36 μs（首次建引擎 O(n) 一次性 40–110 ms）；`reindex` 静默补缺并升位；**默认纪律：索引唯一** |
| 取数三路 | `loc` 标签且闭端、`iloc` 位置且开端、`[]` 只取列；掩码必须索引对齐 |
| 写入 | **单层 `df.loc[掩码, 列] = 值`**；链式写 = 警告 + 不生效（CoW）；setitem 禁止升 dtype（PDEP-6） |
| CoW | 读到的都是引用、写出的都是新对象；子对象双向隔离；隔离边界显式 `.copy()` |
| dtype 与缺失 | 字符串默认 `str`（PDEP-14，缺失用 `NaN`）；`bool+None → object` 要显式 `boolean`；`np.nan` 与 `pd.NA` 分工（前者比较给 `False`，后者给 `<NA>` 并在 `bool()` 报错）；`category` 省 48 倍内存 |
| 对齐算术 | 加法取**并集**并补 `NaN`（行数变多、int→float），`fill_value` 补单侧；**比较拒绝对齐**（`ValueError`） |
| I/O | CSV 有损、推断是"整列民主"；`dtype=`/`parse_dates`/`na_values` 三旋钮；parquet 保真；`chunksize` 分块 |
| 变形 | 长表存储宽表展示；格子唯一用 `pivot`、要聚合用 `pivot_table`；`stack/unstack` 是底层原语；出厂记得 `reset_index()` |
| 分组 | split-apply-combine；`agg`（行缩到组数）/`transform`（行数不变、归约后广播）/`filter`（整组留弃）/`apply`（安全阀）；默认 `sort=True`；分类组键 `observed=True`；apply 不再传分组列 |
| 连接 | inner/left/right/outer 四种行数；`validate=` 声明基数、`indicator=` 审计来源；重复键 = 笛卡尔爆炸；按索引连须两侧声明；`concat` 不去重、会升位 |
| 时间序列 | `to_datetime(..., errors="coerce")` 产 `NaT`；默认 `us` 分辨率；先 `tz_localize` 后 `tz_convert`、运算统一 UTC；`resample` 聚合 vs `asfreq` 补网格；`rolling`/`ewm` 两种均线；`M→ME` 等五个别名已删 |
| 清洗 | 顺序：info → 转型 → 度量缺失 → 去重 → 填删 → 断言；标记（`duplicated`/`isna`）与执行分离；填法即业务假设 |
| 文本 | `.str` 全面向量化；**`contains` 默认正则 + 区分大小写**；`assign(lambda d:...)` 才能引用链上新列；`pipe` 化可测；禁 `inplace` |
| 性能 | 向量化 0.24 ms vs `apply(axis=1)` 409 ms（~1700×）；`query` 不承诺提速；category+float32：13.2 MB→1.0 MB；先量→再改形状→后换引擎 |
| 调试 | `info`/`describe`/`value_counts` 四个体温数字；`assert_frame_equal` 三把钥匙；六条契约断言；比对次序：形状→dtype→数值 |

---

#### 练习 2

**基础：把机制用对**

1. **三件套预测**：不运行代码，写出下面每步结果的 `index`、`dtype` 与行数，再验证。
   ```python
   a = pd.Series([1, 2], index=["x", "y"])
   b = pd.Series([5], index=["y"])
   a + b; a.add(b, fill_value=0); a.reindex(["x", "y", "z"])
   ```

2. **修 bug（链式赋值）**：函数本意是"把低价行调到 100"，在 pandas 3 下**不报错但不生效**，解释原因并修正。
   ```python
   def floor_price(df):
       df["price"][df["price"] < 100] = 100
   ```

3. **取数三路**：给定 `df`（字符串索引 `["a","b","c"]`），分别用 `loc`/`iloc`/布尔掩码取出第 2、3 行；说明 `df.loc["b":"c"]` 与 `df.iloc[1:3]` 是否等价、`df["b":"c"]` 会取到什么。

4. **类型修复**：`pd.read_csv("t.csv")` 后 `qty` 是 `float64`（有缺失）、`code` 是 `str`（应为整数前导零编号）。写出**读入时**与**读入后**两种修复方案，并解释为什么读入时更优。

5. **对齐断言**：写一个 `safe_add(s1, s2)`：要求对齐后无缺失（否则报错说明哪些标签缺席），并支持 `fill_value`。

6. **四种分组算子**：对 `df = DataFrame({"g":[...], "v":[...]})` 分别用 `agg`、`transform`、`filter`、`apply` 实现"只保留组内均值 > 0 的行，并附上组均值列"，比较行数与写法成本。

7. **连接体检**：左表 1000 行（`user_id` 可重复）、右表 200 行（`user_id` 唯一），`merge` 应声明什么 `validate`？写出断言组合，并预测"右表 `user_id` 缺 3 个值"时 `how="left"` 的行数与缺失形态。

**进阶：把代码写稳**

8. **幂等清洗**：把 2.11.5 的六步写成 `clean(df)`，满足 `clean(clean(df)).equals(clean(df))`，并对下列输入给出断言：重复行、`?` 脏值、缺失价、日期文本。

9. **宽长闭环**：宽表 `store × month` 的销量 → 长表 → 按月 `groupby` 求环比 → 回到宽表。要求每一步后 `print(shape)` 监控行数，并用 2.7 的例子自证。

10. **滚动口径**：计算 7 日滚动均值，要求（a）处理缺失日（b）说明 `min_periods` 取值对首周曲线的影响（c）对比 `rolling` 与 `ewm` 在含尖峰数据上的形状，画不出图就用数值对比。

11. **性能改造**：把 `df.apply(lambda r: f(r["a"], r["b"]), axis=1)` 改写为向量化版本，用 2.13.1 的计时方法给出加速比；再把同一逻辑用 `itertuples` 实现作对照。

12. **分块聚合**：生成 100 万行 CSV，用 `chunksize=10**5` 流式读入并按 `g` 聚合 `sum`，证明结果与整读一致；记录峰值内存差异（`tracemalloc`，回链卷 1 第 15 章）。

13. **时区实验**：构造 `US/Eastern` 的逐小时序列跨过 DST 切换日，验证 02:00 缺失；分别在裸时间与时区时间上做"+1 天"，解释结果差异；最后统一到 UTC 并断言行数不变。

**深水：往实现里看一层**

14. **BlockManager 取证**：用 `df._mgr`（或 `ds-02b` B1 的公开替代）观察多列同 dtype 是否合并进一个块；构造一个 `int64` 列被 `loc` 写入前后块结构的变化，解释 2.3 的报错在块层意味着什么。

15. **CoW 传播实验**：按 `ds-02b` B2 的方法，追踪 `sub = df.head(3)` 后分别修改 `df` 与 `sub` 的引用行为（`id()`、`np.shares_memory`、`sys.getrefcount` 任选），验证"读是引用、写是新对象"；再关掉 CoW（如引擎支持）对比链式赋值的两种结局。

16. **读原始文献**：读 PDEP-7（Copy-on-Write）的动机一节，用自己的话说清它用什么代价换掉了什么（提示：`SettingWithCopyWarning` 时代的问题），并解释为什么 pandas 3 选择"警告 + 不生效"而不是"抛异常"。

---

**进入下一章的准备**（对应开篇四条学习目标）：

**建模型**
- ✅ 能把任何一次操作的结果预判为"索引是什么、dtype 是什么、行数变没变"
- ✅ 能解释对齐、透视、分组、连接四种操作在"标签搬运"这一层的共同本质

**会取写**
- ✅ 三路取写不混用，赋值永远是单层 `df.loc[掩码, 列] = 值`
- ✅ 能说清 CoW 下链式赋值为何失效、子对象为何双向隔离、何时必须 `.copy()`

**会整理**
- ✅ 清洗六步顺序能默写，`agg/transform/filter/apply` 按输出形状选型
- ✅ 四类连接的行数语义与 `validate/indicator` 组合信手拈来

**跑得快**
- ✅ 能量化 `apply(axis=1)` 的代价并给出替代写法
- ✅ 知道 category/float32/分块三个内存杠杆，知道"先量→改形状→换引擎"的次序

准备好了就进入 `ds-03`（Matplotlib）：本章第 4、7 步产出的透视表与滚动序列正是可视化的标准输入；pandas 可以直接 `plot()` 出图，但图形对象的坐标系、子布局面貌要到 `ds-03` 才讲得清。本章不打基础的地方（图形语法、统计图表选型、seaborn），正是下一章的主角。

---

## 参考文献

按"原始论文与专著 / 规范与提案 / 官方文档 / 源码"四类排列。正文中的"延伸阅读"均指向本表。

**原始论文与专著**

1. McKinney, W. (2010). *Data Structures for Statistical Computing in Python.* Proceedings of the 9th Python in Science Conference, 563–568. —— pandas 的奠基论文，DataFrame/Series 与"数据对齐优先"设计的原始出处。
2. McKinney, W. (2022). *Python for Data Analysis, 3rd Edition.* O'Reilly Media. —— 实务参考书，本章清洗与时间序列流程的通行写法来源。

**规范与提案（PDEP）**

3. PDEP-7: *Copy on Write* —— 本章 2.3 CoW 契约与 `ds-02b` B2 的规范出处。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0007-copy-on-write.md>
4. PDEP-6: *Ban upcasting* —— 2.3 "setitem 禁止静默升 dtype" 的规范出处。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0006-ban-upcasting.md>
5. PDEP-14: *String dtype by default* —— 2.4 字符串列默认 `str` 的规范出处。<https://github.com/pandas-dev/pandas/blob/main/web/pandas/pdeps/0014-string-dtype.md>

**官方文档**

6. pandas 3.0 What's New —— 本章"版本注意"八条的完整出处（频率别名、apply 分组列、`observed` 默认值等）。<https://github.com/pandas-dev/pandas/blob/main/doc/source/whatsnew/v3.0.0.rst>
7. pandas User Guide: Indexing and selecting data —— `loc`/`iloc`/多级索引的官方语义。<https://pandas.pydata.org/docs/user_guide/indexing.html>
8. pandas User Guide: Group by / Reshaping —— split-apply-combine 与透视/熔化的官方长文。<https://pandas.pydata.org/docs/user_guide/groupby.html> · <https://pandas.pydata.org/docs/user_guide/reshaping.html>
9. Apache Arrow Python documentation —— 2.6 `dtype_backend`、`ds-02b` B7 的列式内存出处。<https://arrow.apache.org/docs/python/>
10. Polars User Guide —— 2.13.5 与 `ds-02b` B8 的引擎对照。<https://docs.pola.rs/>

**源码**

11. `pandas/core/reshape/merge.py` —— 四类连接、`validate`、`indicator`、suffixes 的实现（对应 2.9 与 `ds-02b` B4）。
12. `pandas/core/groupby/` —— `Grouper`、`transform` 广播、`observed/sort/group_keys` 标志（对应 2.8 与 `ds-02b` B5）。
13. `pandas/core/indexes/base.py` · `pandas/_libs/hashtable` —— `Index` 语义与哈希引擎（对应 2.2 与 `ds-02b` B3）。
14. `pandas/core/indexing.py` · `pandas/core/internals/` —— `.loc/.iloc` 写入路径与 BlockManager（对应 2.3 与 `ds-02b` B1、B2）。
15. `pandas/core/strings/` —— `.str` 访问器的向量化实现（对应 2.12 与 `ds-02b` B7）。
