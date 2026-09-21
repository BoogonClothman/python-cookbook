# 第1章 NumPy 数组：数据科学的计算引擎

> **学习目标**：掌握 ndarray 的数据模型、寻址规则与计算模型，能用纯 NumPy 写出正确、可读、内存可控的数据处理代码。
>
> - **建模型**：用"一块内存 + 三张说明"解释视图、广播、轴归约与性能现象，而不是背 API
> - **会寻址**：预判一次操作得到的是视图还是拷贝，以及赋值会不会污染原数组
> - **算得对**：能在任意维度上沿正确的轴归约，能预判广播结果的形状与 dtype
> - **跑得快**：能定位临时数组与内存序问题，把 Python 循环改写成向量化并量化收益

上一章 `ds-00` 给了"形状语言"的直觉：`shape` 是元数据，`@` 是批量点积，`reshape(-1, 1)` 能把一维数组变成列方向。本章兑现那些预告，并回答一个更底层的问题：**为什么同样的数据，装进 ndarray 之后就快，而且能以任意形状被解释？**

本章有两个边界。第一，**只讲纯 NumPy**：pandas 的表结构、matplotlib 的图形、scipy 的统计分布分别属于 `ds-02`、`ds-03`、`ds-04`。第二，**深度分层**：主线保证你能正确干活，原理与实现细节放进两本配套文件，不打断阅读节奏。

| 配套文件 | 装什么 |
|---------|--------|
| `ds-01b-numpy-internals-memory.md` | 内存布局、strides 完全解析、所有权与别名、缓冲区协议、memmap |
| `ds-01c-numpy-internals-compute.md` | ufunc 内核与 SIMD、浮点求和、排序算法、BLAS 后端、内存带宽、随机数内核 |

**验证环境**：本章所有可执行输出都在 Linux 上的 Python 3.14 + NumPy 2.5 下实跑得到。涉及计时的数字随机器与运行时波动，文中只保证数量级；**平台相关的输出会单独标注**（典型例子：默认整数在 Windows 上是 `int32`，在 Linux/macOS 上是 `int64`）。

---

## 1.0 导读：本章地图与使用方式

### 1.0.1 全章地图

层级标记：● 核心（第一遍必读）· ◐ 进阶（用到再读）· ○ 深水（在配套文件展开）。

| 节 | 要解决的问题 | 层级 |
|----|-------------|------|
| 1.1 从列表到 ndarray | 数组到底为什么快 | ● |
| 1.2 数据模型 | 一段内存如何被解释成任意形状 | ● |
| 1.3 dtype 与类型提升 | 一个数占几字节、混合运算的结果是什么类型 | ●◐ |
| 1.4 创建与初始化 | 怎么把数据正确地放进数组 | ● |
| 1.5 索引四式 | 取数有哪四种方式、各自的语义是什么 | ● |
| 1.6 视图、拷贝与赋值 | 一次操作动的是原件还是副本 | ● |
| 1.7 广播 | 形状不同为什么有时能算、结果形状是什么 | ● |
| 1.8 轴（axis） | 到底沿哪个方向归约 | ● |
| 1.9 ufunc | 逐元素运算的引擎与协议 | ●◐ |
| 1.10 聚合、排序与统计 | 求和、分位、排序与 NaN 处理 | ● |
| 1.11 形状代数 | 变形、拼接、拆分 | ● |
| 1.12 线性代数与 einsum | 批量矩阵运算与一般化收缩 | ◐ |
| 1.13 随机数 Generator | 可复现抽样与打乱 | ● |
| 1.14 I/O 与数据边界 | 读写文件、结构化数组与缺失值 | ◐ |
| 1.15 性能工程 | 临时数组、内存序与反模式 | ● |
| 1.16 互操作协议 | 与 pandas、torch 及第三方库的接口 | ◐ |
| 1.17 调试与验证 | 形状、dtype、数值三类错误怎么查 | ● |
| 1.18 综合实战 | 用纯 NumPy 走完一条流水线 | ● |

### 1.0.2 三条阅读路线

不必一次读完。按你当下的目的选一条：

- **速通线**（先能正确干活）：1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 1.9 → 1.10 → 1.11 → 1.13 → 1.17 → 1.18
- **工程线**（要写库、要调优）：速通线 + 1.12、1.14、1.15、1.16
- **原理线**（要读源码、读论文）：工程线 + 全部 ○ 内容，即 `ds-01b` 与 `ds-01c` 两本配套文件

### 1.0.3 本章向后续章节交付什么

每节末尾都会重申一次本节交付的接口，汇总如下：

| 本章交付 | 谁在用 |
|---------|--------|
| 内存模型与 strides | 1.6 视图、1.7 广播、1.15 性能；卷 4 的张量与显存布局 |
| 广播规则 | 兑现 `ds-00` 的预告；卷 3、卷 4 的批量维度运算 |
| 轴归约语义 | `ds-02` `groupby` 的方向直觉、`ds-04` 的抽样统计 |
| dtype 与 NaN 处理 | `ds-02` 缺失值、卷 4 的 float32 精度取舍 |
| 随机数 Generator | `ds-04` 的置换检验与 bootstrap |
| `__array__` 系列协议 | `ds-02`/`ds-03`/`ds-04` 与卷 3、卷 4 的数据交换 |

### 1.0.4 代码、答案与文献约定

- **代码**：概念演示用 REPL 会话（带 `>>>`），完整实验用脚本块；输出为实跑结果。
- **答案**：与 `ds-00` 一致，随堂自测与章末练习都不附参考答案；数值题用文中同款代码当场核对。
- **文献**：正文用 `> **延伸阅读**：……` 指向章末参考文献；需要推导与实现细节时，进 `ds-01b` / `ds-01c`。

---

## 1.1 从列表到 ndarray：数组引擎解决什么问题

先把任务说具体：对 100 万个测量值求平方和。Python 列表写起来只有一行，但慢；ndarray 也只需要一行，却快出一个数量级。这一节先把这个差距**量化**，再解释它来自哪里——这是理解本章所有机制（strides、视图、广播、内存序）的动机来源。

### 1.1.1 把差距量出来

```python
import timeit
import numpy as np

n = 1_000_000
py_list = list(range(n))
arr = np.arange(n)

t_sum_py = timeit.timeit(lambda: sum(py_list), number=20) / 20
t_sum_np = timeit.timeit(lambda: arr.sum(), number=200) / 200
t_sq_py = timeit.timeit(lambda: [x * x for x in py_list], number=5) / 5
t_sq_np = timeit.timeit(lambda: arr * arr, number=200) / 200

print(f"求和     Python {t_sum_py*1000:7.2f} ms   NumPy {t_sum_np*1000:7.4f} ms   {t_sum_py/t_sum_np:5.1f}x")
print(f"逐元素平方 Python {t_sq_py*1000:7.2f} ms   NumPy {t_sq_np*1000:7.4f} ms   {t_sq_py/t_sq_np:5.1f}x")
```

本机一次实测：

```
求和     Python    2.52 ms   NumPy  0.1261 ms    20.0x
逐元素平方 Python   21.80 ms   NumPy  0.3151 ms    69.2x
```

两个差距都很大，但**不是同一个数量级**：求和约 20 倍，逐元素平方约 70 倍。这个差别本身就藏着线索——`sum()` 的循环也在 C 里，而列表推导式的循环在 Python 字节码里。先把"内存"这一层看清楚，再回到这个疑问。

### 1.1.2 内存：每个元素花了多少字节

```python
>>> import sys
>>> values = [float(i) for i in range(1000)]        # 1000 个测量值
>>> sys.getsizeof(values) + sum(map(sys.getsizeof, values))
32856
>>> np.arange(1000, dtype=np.float64).nbytes
8000
```

同样 1000 个 float，列表占 32856 字节，数组占 8000 字节，约 **4 倍**。原因是可以逐步算清的：

- 列表本身只是一个**指针数组**：每个槽位 8 字节，指向堆上的一个对象；
- 每个 Python `float` 对象带 24 字节对象头与值，合计约 **32 字节/元素**（实测 32856 / 1000 ≈ 33，列表自身还有少量预留容量）；
- ndarray 把 8 字节的 `float64` **紧挨着**放在一块缓冲区里，即 **8 字节/元素**。

数据越密，从内存搬到 CPU 的次数越少；CPU 还有缓存，连续访问的命中率远高于"指针追着对象跑"。这是数组快的第一层原因：**布局紧凑**。

### 1.1.3 为什么快：把循环下沉到 C

第二层原因是**循环的执行者**。列表推导式对每个元素都要走一遍 Python 字节码：取对象、判断类型、查乘法实现、创建新对象。NumPy 把这些活交给自己编译好的 C 循环，并且因为 dtype 固定，循环可以为具体类型特化，不必每个元素重新判断类型。

三层展开的最后一层，把上面两段压缩成一句：

> **机制洞察**：ndarray 把数据类型固定下来，从而让 C 循环可以批量处理一段连续内存。**固定类型**换来**紧凑布局**，**紧凑布局**换来**可特化的批量循环**。

这也解释了 1.1.1 留下的疑问。`sum()` 的迭代在 C 层完成，Python 只发起一次调用，因此它与 `arr.sum()` 的差距相对小；列表推导式的**每个元素**都要走一轮字节码分派（迭代、取数、乘法、追加），代价自然高得多。NumPy 的两种写法都只跑一个 C 循环，其中 `arr * arr` 还要额外分配一个同样大的结果数组，所以它比 `arr.sum()` 略慢——这正是 1.15 节要处理的"临时数组"问题。

### 1.1.4 数组不是容器，是"内存 + 解释规则"

`np.frombuffer` 最能说明 ndarray 的本质——它直接在一块**已经存在的内存**上建立数组，一个字节都不复制：

```python
>>> np.frombuffer(bytes(8), dtype=np.uint8)         # 零拷贝：不复制数据
array([0, 0, 0, 0, 0, 0, 0, 0], dtype=uint8)
```

`bytes(8)` 是 8 个零字节，`frombuffer` 把这段内存"看成"长度为 8 的 `uint8` 数组。换一个 dtype，同一段内存就是另一种东西。这正是下一节的主题：**ndarray 不是数据的容器，而是一段内存加一套解释规则。**

> **⚠️ 陷阱**：向量化不等于"把 `for` 写成一行"。`arr * arr` 会分配一个和 `arr` 同样大的**临时数组**；数据大到放不下时（10^8 个 `float64` 就是 800 MB），必须改为分块计算或用 `out=` 原地写回，见 1.15 节。

> **版本注意**：`np.float_`、`np.int0`、`np.unicode_` 等别名已在 NumPy 2.0 移除，本章统一使用 `np.float64`、`np.int32` 这类显式名称。

> **实战建议**：先写清楚、可读的 Python 版本，**量到**瓶颈之后再向量化。向量化是优化手段，不是风格问题。

> **延伸阅读**：CPython 对象开销、缓存局部性与缓冲区协议的完整推演见 `ds-01b` 第 M1、M2 节；"紧凑缓冲区 + 类型特化循环"的设计动机出自 van der Walt 等（2011）与 Harris 等（2020），见本章参考文献。

**随堂自测 1.1**

1. 为什么 `sum(py_list)` 只慢约 20 倍，而列表推导式慢约 70 倍？两者的循环各在哪里执行、各自还要做哪些额外工作？
2. 100 万个 `float64` 的 ndarray 占多少 MB？同样数据放进 Python 列表大约占多少 MB？
3. `np.frombuffer(bytes(8), dtype=np.uint8)` 为什么被称为"零拷贝"？如果改成 `dtype=np.float64`，数组长度变成多少？

**本节交付**："紧凑缓冲区 + 编译循环"的直觉，是 1.2 节 strides 解释与 1.15 节内存带宽分析的地基；也是卷 4 理解"为什么张量要求连续布局"的前置。

---

## 1.2 数据模型：一块内存 + 三张说明

核心问题：同一段 24 字节的内存，为什么能同时被当成"长度 6 的一维数组""2×3 的矩阵""3×2 的转置"？答案是 ndarray 把这段内存和一个三元组绑定在一起：

| 元数据 | 回答的问题 |
|--------|-----------|
| `dtype` | 每个元素占几个字节、这些字节怎么解释 |
| `shape` | 每个维度有多长 |
| `strides` | 沿某个维度前进一格，字节地址要跳多少 |

### 1.2.1 三张说明长什么样

```python
>>> import numpy as np
>>> a = np.arange(6, dtype=np.int32)
>>> a
array([0, 1, 2, 3, 4, 5], dtype=int32)
>>> a.dtype, a.itemsize, a.nbytes
(dtype('int32'), 4, 24)
>>> a.ndim, a.shape, a.strides
(1, (6,), (4,))
```

`strides=(4,)` 的含义：下标每加 1，字节地址加 4（`int32` 的宽度）。所以 `a[k]` 位于缓冲区偏移 `k*4` 处。换成二维只是多一项：

```python
>>> m = a.reshape(2, 3)
>>> m.shape, m.strides
((2, 3), (12, 4))
```

`strides=(12, 4)` 的含义：行下标加 1 跳 12 字节（一整行 3 个 `int32`），列下标加 1 跳 4 字节。于是元素 `[i, j]` 的字节偏移是：

$$i \times 12 + j \times 4$$

### 1.2.2 用字节验证这个公式

公式不能只写在纸上。把同一段内存重新看成字节，直接数一数：

```python
>>> m[1, 2]                                   # 第 2 行第 3 列
np.int32(5)
>>> mv = memoryview(a).cast('B')              # 同一段内存的字节视角
>>> mv.shape
(24,)
>>> bytes(mv[20:24])                          # 1*12 + 2*4 = 20
b'\x05\x00\x00\x00'
```

`m[1, 2]` 与"偏移 20 处的 4 个字节"对上了。`05 00 00 00` 是 `int32` 的 5 在小端机器上的字节序。（NumPy 2.0 起，从数组里取出的标量显示为 `np.int32(5)` 这种形式，1.x 只显示 `5`；原因见 1.3.6 节的版本注意。）**注意 `memoryview` 的切片是按元素而不是按字节的**：`memoryview(a)` 的 `format` 是 `'i'`、`itemsize` 是 4，`mv[20:24]` 会按第 20~23 个**元素**切片而返回空；必须先 `.cast('B')` 才能按字节寻址。这个坑值得记住。

### 1.2.3 转置不搬数据，只改说明

```python
>>> t = m.T
>>> t.shape, t.strides
((3, 2), (4, 12))
```

`t` 与 `m` 指向同一段内存，只是把两个 stride 交换了位置。验证方式不是看形状，而是看它们是否共享内存、以及改一个另一个是否跟着变：

```python
>>> np.shares_memory(t, a)
True
>>> t[0, 0] = 99
>>> a[0]                                     # 改的是同一块内存
np.int32(99)
```

切片同理，也只改说明：

```python
>>> m[:, ::2].strides
(12, 8)
```

### 1.2.4 dtype 也是解释规则

同一段字节，`dtype` 变了，值就变了。下面这 4 个字节按 `uint8` 是 `[0, 0, 128, 63]`，按 IEEE 754 单精度就是 `1.0`：

```python
>>> raw = np.array([0, 0, 128, 63], dtype=np.uint8)
>>> raw.view(np.float32)
array([1.], dtype=float32)
```

要区分两个动作：**`view` 重新解释位模式，`astype` 按数值做转换**。

```python
>>> ints = np.array([1, 2, 3], dtype=np.int32)
>>> ints.view(np.float32)                     # 位模式没变，含义变了
array([1.e-45, 3.e-45, 4.e-45], dtype=float32)
>>> ints.astype(np.float32)                   # 逐个元素做数值转换
array([1., 2., 3.], dtype=float32)
```

`1` 的位模式被当成浮点数读出来，是一个极小的非规格化数，这就是 `view` 与 `astype` 差别的直观证据。

### 1.2.5 内存序：C 连续与 F 连续

同样 `(2, 3)` 的形状，可以有两种摆放顺序：

```python
>>> np.arange(6).reshape(2, 3, order='F')
array([[0, 2, 4],
       [1, 3, 5]])
>>> np.arange(6).reshape(2, 3, order='F').strides
(8, 16)
```

默认是 C 序（最后一维最快变化）；`order='F'` 让第一维最快变化。用 `flags` 可以直接问数组：

```python
>>> m.flags['C_CONTIGUOUS'], t.flags['C_CONTIGUOUS']
(True, False)
```

C 连续意味着"按行优先铺得整整齐齐"。它重要是因为**很多操作只在连续内存上才能零拷贝完成**——这正是下面那个陷阱的根源。

### 1.2.6 视图还是拷贝：唯一可靠的判据

非连续数组上的 `reshape` / `ravel` 必须重新排列数据，因此只能返回拷贝：

```python
>>> flat = t.reshape(-1)                      # t 非 C 连续
>>> np.shares_memory(flat, a)
False
>>> flat[0] = -1
>>> a[0]                                      # 原数组不受影响 → flat 是拷贝
np.int32(99)
```

问题在于，**很多资料教你用 `.base` 或 `.flags['OWNDATA']` 判断视图**，而它们在这里都会给出误导性的答案：

```python
>>> flat.base is None, flat.flags['OWNDATA']
(False, False)
```

`flat` 既不拥有数据（`OWNDATA` 为 `False`），`.base` 也不为 `None`，但它和 `a` **没有任何共享内存**。原因是经过视图链之后，`.base` 指向的是最近的缓冲所有者，而不是你最初那个数组。

> **⚠️ 陷阱**：判断"是不是共享内存"只有两个可靠办法——`np.shares_memory(a, b)`，或者改一个看另一个是否变。`.base` 与 `OWNDATA` 只描述"谁拥有这块缓冲"，不描述"是否与你手上的数组共享"。布尔掩码、花式索引的结果同理，都是拷贝。

> **版本注意**：`arr.view(dtype)` 要求新旧 dtype 的 itemsize 兼容（或在最后一维上整除），跨宽度转换要用 `astype`。不要把 `view` 当作数值转换工具。

> **实战建议**：拿到陌生的数组，先打印 `a.shape, a.dtype, a.strides` 三件套。多数"结果不对"在第一步就能看出端倪；再加一句 `np.shares_memory(a, b)`，就能避免"改了副本还以为改了原数据"。

> **延伸阅读**：strides 的完全解析（任意索引、负步长、只读视图）、所有权链与引用计数、memmap 见 `ds-01b` 第 M3–M6 节。

**随堂自测 1.2**

1. `np.arange(12, dtype=np.int32).reshape(3, 4)` 的 `strides` 是多少？元素 `[2, 1]` 的字节偏移是多少？
2. 同一段内存能同时被解释成 `(6,)`、`(2, 3)`、`(3, 2)`，靠的是哪三样元数据？
3. `t = m.T` 之后，`m` 的形状变了吗？数据被搬动了吗？用哪一行代码能可靠验证？
4. `x.view(np.float32)` 与 `x.astype(np.float32)` 有什么区别？各自适用什么场景？

**本节交付**：内存模型与 strides 是 1.6 节视图/拷贝判定、1.7 节广播对齐、1.15 节内存序优化的共同地基；dtype 作为"解释规则"的视角，会在 1.3 节展开为完整的类型系统，并被 `ds-02` 的缺失值与卷 4 的 float32 取舍复用。

---

## 1.3 dtype 与类型提升：一个数占几字节，混合运算听谁的

`dtype` 决定三件事：每个元素占几字节、这些字节怎么解释、以及**参与混合运算时结果是什么类型**。前两件在 1.2 节已经见过（同一段内存按不同 dtype 读出不同的值），这一节补齐第三件。它是最容易静默出错的地方：整数溢出、浮点误差、类型提升陷阱都不报错，只是悄悄给出一个错答案。

### 1.3.1 dtype 家族与容量

| 家族 | 常用类型 | 每元素字节 |
|------|---------|-----------|
| 有符号整数 | `int8` / `int16` / `int32` / `int64` | 1 / 2 / 4 / 8 |
| 无符号整数 | `uint8` / `uint16` / `uint32` / `uint64` | 1 / 2 / 4 / 8 |
| 浮点 | `float16` / `float32` / `float64` | 2 / 4 / 8 |
| 复数 | `complex64` / `complex128` | 8 / 16 |
| 布尔 | `bool` | 1 |
| 定宽字符串 | `<U`*n* | 4*n* |
| 日期时间 | `datetime64[单位]` / `timedelta64[单位]` | 8 |

默认规则要记住两条：混入浮点的序列（如 `np.array([1, 2, 3.0])`）得到 `float64`；而**纯整数序列的默认宽度是平台相关的**——`np.array([1, 2, 3])` 在 Linux/macOS 上是 `int64`，在 Windows 上是 `int32`。原因是 NumPy 的默认整数跟随 C 的 `long`，而 Windows 上的 `long` 是 32 位。本书的输出若无特别说明，均在 Linux 上采集。

> **工程影响**：默认整数宽度跨平台不一致，是"本地能跑、同事机器上结果不同"的常见来源——同一段累加代码，Windows 上的 `int32` 可能溢出，Linux 上的 `int64` 不会。**凡是要跨平台、跨文件格式或长期保存的数组，都在创建时写死 dtype。**

取值范围不用背，问 NumPy：

```python
>>> np.iinfo(np.int8)
iinfo(min=-128, max=127, dtype=int8)
>>> np.iinfo(np.int8).min, np.iinfo(np.int8).max
(-128, 127)
>>> np.finfo(np.float32).eps
np.float32(1.1920929e-07)
>>> np.finfo(np.float32).max
np.float32(3.4028235e+38)
```

`iinfo` 给整数边界，`finfo` 给浮点的机器精度 `eps` 与最大值。选 dtype 时先问"数据范围装得下吗"，再问"精度够吗"。

### 1.3.2 整数溢出：数组静默回绕，标量才告警

固定宽度的整数会**回绕**（wrap around），而且数组运算不回绕告警：

```python
>>> np.array([120, 127], dtype=np.int8) + np.int8(10)
array([-126, -119], dtype=int8)
```

`120 + 10 = 130` 超出了 `int8` 的上限 127，结果变成 `130 - 256 = -126`；`127 + 10 = 137` 变成 `-119`。没有异常、没有警告。无符号整数的下溢同样静默：`np.array([1], dtype=np.uint8) - 2` 得到 `255`。

标量运算会发一个 `RuntimeWarning`，但结果照样回绕：

```python
>>> np.int8(127) + np.int8(1)
RuntimeWarning: overflow encountered in scalar add
np.int8(-128)
```

> **⚠️ 陷阱**：整数溢出是"合法的错答案"。当 dtype 来自文件或推断（比如 `uint8` 的像素、`int16` 的传感器读数），一次**逐元素加法或原地更新**（`a + b`、`a += b`）就会静默回绕，而且 dtype 不会自动变宽。防线有三条：先用 `np.iinfo` 核对范围；运算前显式提升到够宽的 dtype（`a.astype(np.int64) + b.astype(np.int64)`）；对关键结果做事后范围断言。特别注意：**`np.errstate(over='raise')` 拦不住数组的整数溢出**——它只对标量运算的告警生效，而数组版本来就没有告警可拦。

> **机制洞察**：归约函数（`.sum()`、`.cumsum()`、`np.add.reduce`）对窄整数会**先提升到平台默认整数再累加**，所以 `np.array([120, 120, 120], dtype=np.int8).sum()` 得到的是 `np.int64(360)`，而不是回绕值；危险发生在逐元素运算上。但"平台默认整数"本身跨平台不一致（见 1.3.1），所以真正跨平台的代码仍应显式写出累加 dtype。

### 1.3.3 浮点精度：float32 的代价

浮点数不是实数，两个现象要心里有数。第一，**大数吃小数**：

```python
>>> np.float32(1e8) + np.float32(1)
np.float32(1e+08)
```

`float32` 只有 23 位有效位（约 7 位十进制数字），`1e8` 加上 1 之后，1 落在表示精度之外，被直接吞掉。第二，**十进制小数存不精确**，`float32` 的 0.1 不是 0.1：

```python
>>> float(np.float32(0.1))
0.10000000149011612
```

把这两个现象放进累加实验，会看到一个反直觉的结果：

```python
>>> x = np.full(10, 0.1, dtype=np.float32)
>>> x.sum()
np.float32(1.0)
>>> x.sum(dtype=np.float64)
np.float64(1.0000000149011612)
```

看起来"低精度反而更准"，其实不是：`float32` 的 0.1 本身就带着约 `1.5e-9` 的表示误差，用 `float64` 累加会把这 10 份误差**如实累加出来**（`1.0000000149011612`）；而 `float32` 在累加过程中不断四舍五入，最后又落回 `1.0`。

> **机制洞察**：`x.sum(dtype=np.float64)` 得到的不是"更准的答案"，而是"误差更诚实的答案"。**误差的来源在输入，不在累加器。** 想真正减小误差，要先决定数据该用哪种精度存，而不是最后换一个高精度求和。

> **实战建议**：`float64` 是 NumPy 的默认，也是数据分析的默认。只有两种情形值得换 `float32`：显存受限的深度学习（卷 4 主角），以及内存放不下必须减半的数据。换之前先算清楚：`float32` 的 7 位有效数字对你的业务够不够。

### 1.3.4 类型提升：NEP 50 之后的规则

两个不同类型的数组运算，结果类型由 `np.result_type` 给出。整数之间的规则符合直觉，浮点与整数的混合也符合直觉：

```python
>>> np.result_type(np.int8, np.float32)
dtype('float32')
```

但有两个反直觉的地方。第一，**两个整数相加可能得到浮点**：

```python
>>> np.result_type(np.uint64, np.int64)
dtype('float64')
>>> np.uint64(1) + np.int64(1)
np.float64(2.0)
```

原因是 `uint64` 和 `int64` 谁也无法无损容纳对方（`uint64` 的最大值超过 `int64`），NumPy 只能退到能同时覆盖两个范围的 `float64`。**代价是 64 位整数在超过 2^53 之后开始丢精度**。混用无符号与有符号整数时，先显式 `astype` 到同一类型。

第二，**Python 标量是"弱类型"**，不参与提升（NEP 50，NumPy 2.0 起的规则）：

```python
>>> np.array([1], dtype=np.int8) + 1
array([2], dtype=int8)
>>> np.array([1], dtype=np.float32) + 1.5
array([2.5], dtype=float32)
```

Python 的 `1` 不会把 `int8` 抬高成 `int64`，`1.5` 也不会把 `float32` 抬高成 `float64`。规则可以总结成三句：

| 组合 | 结果 |
|------|------|
| Python 整数 + 整数数组 | 数组的 dtype；放不下则 `OverflowError` |
| Python 浮点 + 浮点数组 | 数组的 dtype |
| Python 浮点 + 整数数组 | `float64`（默认浮点） |

第三条容易记错，验证一下：`np.array([1], dtype=np.int32) + 2.5` 得到 `float64`，而 `np.array([1], dtype=np.float32) + 1.5` 得到 `float32`。区别在于数组本身是不是浮点。

放不下的 Python 整数不再静默降级，而是直接报错——这是 NEP 50 带来的安全改进：

```python
>>> np.array([1], dtype=np.int8) + 1000
OverflowError: Python integer 1000 out of bounds for int8
```

> **版本注意**：NEP 50 是 NumPy 2.0 的破坏性变更。在 1.x 里，`np.array([1], dtype=np.int8) + 1000` 会按"值的大小"提升成 `int16` 并算出结果；2.x 改为报 `OverflowError`。如果你在迁移旧代码时遇到这类报错，正确做法通常是显式 `astype` 到目标宽度，而不是退回 1.x 行为。

### 1.3.5 显式转换：astype 与 casting

`astype` 做**数值转换**，默认规则是"不安全也照转"。浮点转整数是**向零截断**，不是四舍五入：

```python
>>> np.array([1.7, -1.7]).astype(np.int64)
array([ 1, -1])
```

想禁止有损转换，把 `casting` 收紧：

```python
>>> np.array([1.7]).astype(np.int64, casting='safe')
TypeError: Cannot cast array data from dtype('float64') to dtype('int64') according to the rule 'safe'
>>> (np.can_cast(np.float64, np.int64), np.can_cast(np.int32, np.int64, casting='safe'))
(False, True)
```

`np.can_cast` 让你在转换之前先问一句"这个方向安全吗"，适合写在数据校验里。NaN 转整数直接报错，这比转换出一个垃圾值好：

```python
>>> np.array([1, np.nan], dtype=np.int64)
ValueError: cannot convert float NaN to integer
```

### 1.3.6 字符串与日期类型

定宽字符串的宽度是 dtype 的一部分，**超长内容会被静默截断**：

```python
>>> np.array(['ab', 'abcdef'], dtype='<U3')
array(['ab', 'abc'], dtype='<U3')
```

`'abcdef'` 变成 `'abc'`，没有警告。字符串列在 NumPy 里本来就是弱势场景（变长文本属于 `ds-02` 的 pandas，或者干脆留在 Python 列表里），需要用时把宽度算足。

日期时间用 `datetime64` 与 `timedelta64`，单位写在方括号里，两个时间相减得到时间差：

```python
>>> s = np.array(['2026-01-01', '2026-02-01'], dtype='datetime64[D]')
>>> s
array(['2026-01-01', '2026-02-01'], dtype='datetime64[D]')
>>> s[1] - s[0]
np.timedelta64(31,'D')
>>> (s[1] - s[0]) / np.timedelta64(1, 'D')
np.float64(31.0)
```

除以一个同单位的时间差可以把 `timedelta64` 变成普通浮点数，这是时间序列特征工程里的常用手法。完整的时间序列处理属于 `ds-02`。

> **版本注意**：NumPy 2.0 起，标量的 `repr` 变成 `np.float32(1.0)`、`np.float64(0.9)` 这种形式（1.x 只显示 `1.0`、`0.9`）。这不是类型变了，而是把"这是 NumPy 标量而不是 Python 标量"显式画出来了。同一版本还改了 `copy` 关键字的语义：`copy=False` 现在表示"绝不拷贝，做不到就报错"，要"能免则免"应改用 `np.asarray` 或 `copy=None`。

> **实战建议**：先按默认 dtype 把流程跑通，再在**读取数据的那一步**统一指定 dtype。把 `astype` 散落在流程中间，既费内存（每次转换都拷贝）又难排查（你永远不确定某一步之后类型是什么）。1.4 节会给出创建时指定 dtype 的写法。

> **延伸阅读**：类型提升的完整矩阵与优势规则、dtype 扩展机制（NEP 42）见 `ds-01c` 第 C5 节；浮点表示与舍入误差的经典长文是 Goldberg（1991），见本章参考文献。

**随堂自测 1.3**

1. `np.array([200], dtype=np.uint8) + 100` 的结果是什么？会报错吗？
2. `np.array([1], dtype=np.int32) + 2.5` 与 `np.array([1], dtype=np.float32) + 1.5` 的结果 dtype 分别是什么？为什么不同？
3. `float(np.float32(0.1)) == 0.1` 是真还是假？为什么？
4. `np.array(['ab', 'abcdef'], dtype='<U3')` 得到什么？数据有没有被改动？

**本节交付**：dtype 与提升规则是 `ds-02` 缺失值语义（整数列不能放 `NaN`）、`ds-04` 数值稳定性、卷 4 float32/混合精度训练的共同前提；"先定 dtype 再算"的纪律会在 1.4 与 1.14 落地。

---

## 1.4 创建与初始化：把数据正确地放进数组

创建数组只有三个来源：**已有数据**（列表、其他数组、二进制缓冲）、**范围与等距序列**（`arange`、`linspace`）、**预分配与填充**（`zeros`、`full`）。这一节按这三个来源组织，重点是每个函数在 dtype、形状、拷贝语义上的默认行为。

### 1.4.1 从已有数据创建

`np.array` 会复制数据，并从内容推断 dtype：

```python
>>> np.array([1, 2, 3])
array([1, 2, 3])
>>> np.array([1, 2, 3]).dtype          # Linux/macOS: int64；Windows: int32
dtype('int64')
>>> np.array([1, 2, 3.0])
array([1., 2., 3.])
>>> np.array([1, 2, 3.0]).dtype
dtype('float64')
>>> np.array([1, 2, 3], dtype=np.int32).dtype     # 要跨平台就显式写死
dtype('int32')
```

嵌套列表会推断成多维。但**参差的嵌套序列不再被默默接受**（早期 NumPy 会造出 `object` 数组，现在直接报错）：

```python
>>> np.array([[1, 2], [3]])
ValueError: setting an array element with a sequence. The requested array has an inhomogeneous shape after 1 dimensions. The detected shape was (2,) + inhomogeneous part.
```

`np.asarray` 与 `np.array` 的区别只有一条：**输入已经是 ndarray 时不复制**。

```python
>>> base = np.array([1, 2, 3])
>>> np.asarray(base) is base
True
```

> **⚠️ 陷阱**：`np.asarray` 的"不复制"意味着你拿到的是**同一个数组**，改它会污染来源。在函数里接收数组参数、又需要修改时，标准做法是先 `np.array(x)` 或 `x.copy()`。这条规则在 1.6 节展开。

### 1.4.2 范围与等距序列

`arange` 按步长生成，**不含终点**，且浮点步长下元素个数不保证符合直觉：

```python
>>> np.arange(0, 1, 0.1)
array([0. , 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
>>> np.arange(0, 1, 0.1).size, np.arange(0, 1, 0.1)[-1]
(10, np.float64(0.9))
```

想要"包含终点的 n 个等距点"，用 `linspace`——点数由你指定，终点可选，还能量出步长：

```python
>>> np.linspace(0, 1, 5)
array([0.  , 0.25, 0.5 , 0.75, 1.  ])
>>> np.linspace(0, 1, 5, retstep=True)
(array([0.  , 0.25, 0.5 , 0.75, 1.  ]), np.float64(0.25))
```

`logspace` 生成等比序列，画对数坐标轴、设置学习率网格时常用：

```python
>>> np.logspace(0, 2, 3)
array([  1.,  10., 100.])
>>> np.logspace(0, 3, 4, base=2)
array([1., 2., 4., 8.])
```

> **⚠️ 陷阱**：**整数步长用 `arange`，浮点步长用 `linspace`。** `arange` 的浮点步长会累积表示误差，"应该有 10 个还是 11 个"依赖具体数值和平台；`linspace` 直接按点数内部计算，不累积。需要精确点数时不要和 `arange` 较劲。

### 1.4.3 预分配与填充

写循环之前先想清楚结果形状，然后一次性分配：

```python
>>> np.zeros(3)
array([0., 0., 0.])
>>> np.zeros(3, dtype=np.float32)
array([0., 0., 0.], dtype=float32)
>>> np.full((2, 2), 7, dtype=np.int8)
array([[7, 7],
       [7, 7]], dtype=int8)
```

`*_like` 系列从另一个数组继承形状与 dtype，是"照着别人的形状来一份"的写法：

```python
>>> np.zeros_like(np.array([1, 2], dtype=np.int16))
array([0, 0], dtype=int16)
>>> np.full_like(np.array([1.5, 2.5]), 0)
array([0., 0.])
```

`np.ones(3)` 得到 `array([1., 1., 1.])`，需要整数时要显式写 `dtype=np.int8` 之类。

`np.empty` 只分配内存、**不初始化**，内容是不可预测的残留数据：

```python
>>> np.empty(4)                                  # 内容是内存残留，你的结果必然不同
array([6.24123786e-310, 6.24123786e-310, 3.20764099e-308, 8.12155682e-114])
```

> **⚠️ 陷阱**：不要因为 `np.empty` 快就用它。它的快只是省掉了清零；只要你的代码**完整覆盖**每一个元素（例如循环逐格写入、或原地 ufunc），用 `empty` 是正当优化；一旦有格子没写到，残留值就直接进入结果，而且这种 bug 在测试里常常"碰巧通过"。

> **实战建议**：**先分配，再原地填**，不要在循环里 `np.append`/`np.concatenate`。后者每次都会重新分配并复制整块数据，n 次追加是 O(n²) 的拷贝量。反模式的量化对比在 1.15 节。

### 1.4.4 特殊结构

三个构造型函数在本卷后续会反复出现：

```python
>>> np.eye(3, dtype=np.int8)
array([[1, 0, 0],
       [0, 1, 0],
       [0, 0, 1]], dtype=int8)
>>> np.diag([1, 2, 3])
array([[1, 0, 0],
       [0, 2, 0],
       [0, 0, 3]])
```

`np.eye` 生成单位阵（`ds-00` 提过它与数字 1 的对应关系），`np.diag` 由一维向量生成对角阵，也可以反过来取对角线。`np.meshgrid` 把两个一维坐标轴展开成网格，是画等高线、热力图之前的准备工作（`ds-03` 用）：

```python
>>> gx, gy = np.meshgrid(np.arange(3), np.arange(2))
>>> gx
array([[0, 1, 2],
       [0, 1, 2]])
>>> gy
array([[0, 0, 0],
       [1, 1, 1]])
```

最后用字节数把"创建时指定 dtype"的价值量化：

```python
>>> np.zeros(3).nbytes, np.zeros(3, dtype=np.float32).nbytes
(24, 12)
```

同样 3 个数，`float32` 省一半内存。数据量到千万级时，这一步决定你能不能把它放进内存。

> **延伸阅读**：`np.empty` 背后的分配器行为与内存页错误见 `ds-01b` 第 M1、M6 节；`meshgrid` 在可视化中的用法属于 `ds-03`。

**随堂自测 1.4**

1. `np.arange(0, 1, 0.1)` 有多少个元素？最后一个是多少？要得到包含 1.0 在内的 11 个等距点，该用哪个函数？
2. `np.array([1, 2, 3]).dtype` 与 `np.array([1, 2, 3.0]).dtype` 分别是什么？为什么？
3. `np.zeros_like(np.array([1, 2], dtype=np.int16))` 的 dtype 是什么？
4. `np.empty(3)` 的元素是什么？为什么不能依赖它？
5. `np.asarray(base) is base` 为 `True` 意味着什么风险？在函数里应该怎么处理传入的数组？

**本节交付**：创建函数的 dtype/形状/拷贝语义是后续所有小节的前置；"先分配再原地填"是 1.15 节性能工程的第一条纪律；`meshgrid` 与 `eye`/`diag` 分别交付给 `ds-03` 与 1.12 节。

---

## 1.5 索引四式：取数的四种语义

NumPy 的索引不是一种操作，而是四种：**基本切片、布尔掩码、花式索引、条件选择**。它们的差别不止写法，更在于结果是视图还是拷贝、形状怎么变。这是数据分析里最高频的动作，也是陷阱最密的地方。

### 1.5.1 基本索引与切片：视图

```python
>>> import numpy as np
>>> a = np.arange(10)
>>> a[2]
np.int64(2)
>>> a[1:4]
array([1, 2, 3])
>>> a[::3]                    # 每 3 个取一个
array([0, 3, 6, 9])
>>> a[::-1]                   # 反转
array([9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
```

二维用逗号分隔各维下标，`...` 表示"其余维度全要"：

```python
>>> m = np.arange(12).reshape(3, 4)
>>> m[1]                      # 一行，shape (4,)
array([4, 5, 6, 7])
>>> m[:, 1]                   # 一列，shape (3,)
array([1, 5, 9])
>>> m[0:2, 1:3]               # 子块，shape (2, 2)
array([[1, 2],
       [5, 6]])
>>> m[..., 0]                 # 等价于 m[:, 0]
array([0, 4, 8])
```

关键性质：**基本切片返回视图**，它与原数组共享内存。

```python
>>> np.shares_memory(a[2:5], a)
True
>>> s = a[2:5]
>>> s[0] = 99
>>> a                         # 改切片等于改原数组
array([ 0,  1, 99,  3,  4,  5,  6,  7,  8,  9])
```

这个性质让批量赋值非常高效，也让它非常危险：

```python
>>> a = np.arange(10)
>>> a[1:4] = 0                # 原地写入，不新建数组
>>> a
array([0, 0, 0, 0, 4, 5, 6, 7, 8, 9])
```

> **⚠️ 陷阱**：`b = a[1:4]` 不是拷贝，是给原数组开了一扇窗。想要独立副本必须写 `b = a[1:4].copy()`。这条规则在 1.6 节系统化。

### 1.5.2 布尔掩码：读取是拷贝，赋值是原地写

```python
>>> a = np.array([1, 5, 3, 8, 2])
>>> mask = a > 3
>>> mask
array([False,  True, False,  True, False])
>>> a[a > 3]
array([5, 8])
```

多个条件要用 `&`、`|`、`~`，并且**每个条件都要加括号**：

```python
>>> a[(a > 1) & (a < 5)]
array([3, 2])
>>> a[(a > 1) and (a < 5)]
ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
```

> **⚠️ 陷阱**：Python 的 `and`/`or` 不能用于数组——它们要问"整个数组的真值"，而多元素数组没有唯一的真值。必须用位运算符，且括号不能省：`a > 1 & a < 5` 会被解析成 `a > (1 & a) < 5`，结果完全不对。

布尔索引的**读取**结果是拷贝：

```python
>>> np.shares_memory(a[a > 3], a)
False
>>> np.count_nonzero(a > 3)
np.int64(2)
>>> np.any(a > 7), np.all(a > 0)
(np.True_, np.True_)
```

但**掩码赋值**写回原数组：

```python
>>> a[a > 3] = 0              # 这是 __setitem__，原地写入
>>> a
array([1, 0, 3, 0, 2])
```

### 1.5.3 花式索引：按位置挑，结果也是拷贝

```python
>>> x = np.array([10, 20, 30, 40, 50])
>>> x[[3, 1, 0]]              # 按给定顺序挑
array([40, 20, 10])
>>> np.shares_memory(x[[3, 1, 0]], x)
False
```

二维花式索引最容易误解：**多个索引数组是按位置配对，不是取子块**。

```python
>>> m = np.arange(12).reshape(3, 4)
>>> m[[0, 2]]                 # 取第 0、2 行
array([[ 0,  1,  2,  3],
       [ 8,  9, 10, 11]])
>>> m[[0, 1], [0, 1]]         # 配对：(0,0) 与 (1,1)，结果是一维
array([0, 5])
>>> m[[0, 1]][:, [0, 1]]      # 想要左上角 2×2 子块，要分两步
array([[0, 1],
       [4, 5]])
```

`np.take` 与花式索引等价，但可以显式指定轴：

```python
>>> np.take(m, [0, 2], axis=0)
array([[ 0,  1,  2,  3],
       [ 8,  9, 10, 11]])
```

### 1.5.4 条件选择：where / clip / select

前三式是"取出"数据，这一组是"逐元素做选择"：

```python
>>> y = np.array([1, -2, 3, -4])
>>> np.where(y > 0, y, 0)     # 条件 ? A : B
array([1, 0, 3, 0])
>>> np.clip(y, 0, None)       # 小于 0 的截到 0
array([1, 0, 3, 0])
>>> np.select([y < 0, y > 2], [-1, 1], default=0)   # 多分支
array([ 0, -1,  1, -1])
```

`np.where` 只给一个条件参数时返回满足条件的**下标**，可以配合赋值使用；`np.putmask` 则是原地按掩码替换。

### 1.5.5 四式对照

| 写法 | 读取结果 | 读取形状 | 写回语义 |
|------|---------|---------|---------|
| `a[1:4]` | 视图 | 切片形状 | `a[1:4] = v` 原地写 |
| `a[a > 3]` | 拷贝 | 一维（展平后） | `a[a > 3] = v` 原地写 |
| `a[[3, 1, 0]]` | 拷贝 | 索引数组的形状 | `a[[3, 1, 0]] = v` 原地写 |
| `np.where(c, x, y)` | 新数组 | 广播后的形状 | 不写回，需自己赋值 |

一句话记忆：**读取时只有基本切片是视图；写入时前三种都作用于原数组。**

> **延伸阅读**：布尔与花式索引的底层路径、拷贝发生的准确时机见 `ds-01b` 第 M5 节。

**随堂自测 1.5**

1. `a = np.arange(10)`、`b = a[3:7]`，改 `b[0]` 会影响 `a` 吗？怎么避免？
2. 为什么 `a[(a > 1) and (a < 5)]` 报错，而 `a[(a > 1) & (a < 5)]` 正常？
3. `m = np.arange(12).reshape(3, 4)`，`m[[0, 1], [0, 1]]` 的结果是什么？与 `m[[0, 1]][:, [0, 1]]` 有何区别？
4. `np.where(y > 0, y, 0)` 与 `y[y < 0] = 0` 的结果一样吗？各自改动了谁？

**本节交付**：四式的视图/拷贝差异是 1.6 节一般理论、`ds-02` 筛选与赋值语义、`ds-03` 数据清洗的前提；布尔掩码是 `ds-02` 缺失值处理的底层动作。

---

## 1.6 视图、拷贝与赋值语义：一次操作动的是谁

1.2 节给了"内存 + 说明"的模型，1.5 节给了四种索引。这一节把"动的是原件还是副本"变成可以事先预判的规则。

### 1.6.1 别名、视图、拷贝

```python
>>> a = np.arange(6)
>>> b = a                     # 别名：同一个对象
>>> c = a[:]                  # 视图：同一块内存，另一套"说明"
>>> d = a.copy()              # 拷贝：独立内存
>>> (b is a, np.shares_memory(a, b), np.shares_memory(a, c), np.shares_memory(a, d))
(True, True, True, False)
```

三者的区别只在改动时才暴露：

```python
>>> b[0] = 100
>>> a
array([100,   1,   2,   3,   4,   5])
```

```python
>>> a = np.arange(6); c = a[:]; c[1] = 200
>>> a
array([  0, 200,   2,   3,   4,   5])
```

```python
>>> a = np.arange(6); d = a.copy(); d[2] = 300
>>> a
array([0, 1, 2, 3, 4, 5])
```

> **口诀**：`b = a` 是起外号，`b = a[:]` 是开窗户，`b = a.copy()` 才是搬家。

常见操作的视图/拷贝归属：

| 操作 | 结果 | 说明 |
|------|------|------|
| `a[1:4]` | 视图 | 基本切片 |
| `a.reshape(...)`（连续时） | 视图 | 只改 shape/strides |
| `a.T`、`a.transpose()` | 视图 | 交换 strides |
| `a.ravel()`（连续时） | 视图 | 展平 |
| `a.view(dtype)` | 视图 | 重新解释字节 |
| `a[a > 3]` | 拷贝 | 布尔掩码 |
| `a[[0, 2]]` | 拷贝 | 花式索引 |
| `a.flatten()` | 拷贝 | 强制展平 |
| `a.astype(...)` | 拷贝 | 数值转换 |
| `a.copy()` | 拷贝 | 显式拷贝 |

### 1.6.2 函数里的重新绑定 vs 原地修改

这是 Python 使用者在 NumPy 上最容易踩的坑：`x = x + 1` 与 `x += 1` 在函数里的行为完全不同。

```python
def rebind(x):
    x = x + 1        # 只让局部名字指向新数组

def inplace(x):
    x += 1           # 原地改，调用者的数组跟着变

def pure(x):
    return x + 1     # 不碰输入，返回新数组
```

```python
>>> a = np.arange(3)
>>> rebind(a)
>>> a                         # 原数组没变
array([0, 1, 2])
>>> a = np.arange(3)
>>> inplace(a)
>>> a                         # 原数组被改了
array([1, 2, 3])
>>> a = np.arange(3)
>>> r = pure(a)
>>> (a, r)                    # 输入不变，返回新数组
(array([0, 1, 2]), array([1, 2, 3]))
```

> **实战建议**：函数改不改输入，必须写进 docstring。NumPy 自己的约定值得照抄：默认返回新数组（`pure`），需要原地写时用 `out=` 显式表达（1.9 节）。不要写"有时原地、有时不原地"的函数。

### 1.6.3 原地运算的 dtype 约束

原地运算要把结果写回原有 dtype，因此**不允许隐式拓宽类型**：

```python
>>> x = np.array([1, 2], dtype=np.int32)
>>> x += 1.5
UFuncTypeError: Cannot cast ufunc 'add' output from dtype('float64') to dtype('int32') with casting rule 'same_kind'
>>> x = x + 1.5               # 换成新数组就没问题，结果是 float64
```

这看起来麻烦，其实是一道保护：如果 `x += 1.5` 被放行，`int32` 数组会"原地降级写回"，小数部分被悄悄截断。**要改变类型就必须显式 `astype` 或重新赋值。**

### 1.6.4 转置视图上的原地操作

转置是视图，所以对它做原地运算等于对整个原数组做运算：

```python
>>> m = np.arange(6).reshape(2, 3)
>>> t = m.T
>>> np.shares_memory(m, t)
True
>>> t += 1
>>> m
array([[1, 2, 3],
       [4, 5, 6]])
```

`t += 1` 不是"给转置加 1"，而是**遍历这批元素、各自加 1**——元素归属与形状无关。

### 1.6.5 只读视图

可以把视图设成只读，保护它指向的内存不被这条路径修改：

```python
>>> a = np.arange(6)
>>> v = a[1:4]
>>> v.flags.writeable = False
>>> v[0] = 9
ValueError: assignment destination is read-only
>>> a.flags.writeable
True
```

只读是**针对这个视图**的：原数组仍然可写。这是共享内存时的显式声明，常用于把内部缓冲区安全地暴露出去。

### 1.6.6 shares_memory 与 may_share_memory

`np.shares_memory` 给出精确答案；`np.may_share_memory` 是**保守估计**，宁可误报：

```python
>>> a = np.arange(10)
>>> (np.shares_memory(a[::2], a[1::2]), np.may_share_memory(a[::2], a[1::2]))
(False, True)
```

`a[::2]` 与 `a[1::2]` 交错取值，实际不重叠；但两者的地址范围重叠，`may_share_memory` 会报 `True`。需要精确判断用 `shares_memory`，需要快速排除用 `may_share_memory`。

> **延伸阅读**：`.base` 链、`OWNDATA`、引用计数与内存生命周期见 `ds-01b` 第 M5 节；只读视图在缓冲区协议中的语义见第 M2 节。

**随堂自测 1.6**

1. 三种"复制" `b = a`、`b = a[:]`、`b = a.copy()`，改 `b` 分别会不会影响 `a`？
2. 下面的函数会改变调用者的数组吗？为什么？
   ```python
   def scale(x, k):
       x = x * k
   ```
3. 为什么 `x = np.array([1, 2], dtype=np.int32)` 之后 `x += 1.5` 报错，而 `x = x + 1.5` 不报错？
4. `np.shares_memory` 与 `np.may_share_memory` 在什么场景下结论不同？各适合用在哪里？

**本节交付**：视图/拷贝判定与函数副作用约定，是 1.7 节广播、1.15 节性能、`ds-02` 链式赋值警报、卷 3 特征工程里"别改坏原始数据"的共同纪律。

---

## 1.7 广播：形状对齐的完整规则

`ds-00` 只给了保守结论"同形才安全"，并承诺在此展开。广播（broadcasting）是 NumPy 最省内存、也最容易静默出错的机制，规则只有三条。

### 1.7.1 三条规则

1. **右对齐**：把两个 shape 从**最右边**开始逐位比较；
2. **补 1**：谁的维度少，就在左边补 `1`；
3. **拉伸**：某一维上若一方是 `1`、另一方是 *n*，则 `1` 被拉伸成 *n*；若两者都不为 1 且不相等，报错。

把规则写成代码，比背结论可靠：

```python
def broadcast_shapes(*shapes):
    """按 NumPy 规则推算广播结果的 shape；不能广播则抛错。"""
    ndim = max(len(s) for s in shapes)
    padded = [(1,) * (ndim - len(s)) + tuple(s) for s in shapes]
    out = []
    for dims in zip(*padded):
        if len(set(dims)) == 1:
            out.append(dims[0])
        elif 1 in dims:
            out.append(max(dims))
        else:
            raise ValueError(f"cannot broadcast {shapes}")
    return tuple(out)
```

用几个 shape 验证：

```
broadcast_shapes((3, 4), (4,)) = (3, 4)
broadcast_shapes((3, 1), (1, 4)) = (3, 4)
broadcast_shapes((3,), (3, 1)) = (3, 3)
broadcast_shapes((2, 1, 4), (3, 1)) = (2, 3, 4)
broadcast_shapes((3,), (4,)) -> ValueError: cannot broadcast ((3,), (4,))
```

### 1.7.2 结果形状推演

```python
>>> x = np.arange(3).reshape(3, 1)
>>> y = np.arange(4).reshape(1, 4)
>>> (x + y).shape
(3, 4)
>>> x + y
array([[0, 1, 2, 3],
       [1, 2, 3, 4],
       [2, 3, 4, 5]])
```

`(3, 1)` 与 `(1, 4)` 各自把长度为 1 的那一维拉伸，得到 `(3, 4)`。不能对齐的组合直接报错：

```python
>>> np.arange(3) + np.arange(4)
ValueError: operands could not be broadcast together with shapes (3,) (4,)
```

> **⚠️ 陷阱**：`(3,)` 与 `(3, 1)` 只差一个括号，语义却从"逐元素相加"变成"3×3 外积"。这是 NumPy 最常见的静默错误：
> ```python
> >>> (np.arange(3) + np.arange(3).reshape(3, 1)).shape
> (3, 3)
> ```
> 一边是 `(3,)`、另一边是 `(3, 1)` 时，运算照做、不报错，但结果形状变了。按 1.2 节的建议把 shape 写进注释，能挡住大部分这类错误。

### 1.7.3 一维数组参与矩阵乘法的精确规则

`ds-00` 提到"一维数组参与乘法的精确规则属于广播话题"，现在补齐。`@` 对一维数组有两条特殊约定：

- 一维数组在**右侧**：先当成 `(n, 1)` 的列向量；
- 一维数组在**左侧**：先当成 `(1, n)` 的行向量；
- 两个一维数组相乘：退化成点积，得到标量。

乘法做完后，**补上的那个维度会被去掉**：

```python
>>> M = np.arange(6).reshape(2, 3)
>>> v = np.arange(3)
>>> (M @ v).shape            # (2,3) @ (3,) → (2,)
(2,)
>>> (v @ M.T).shape          # (3,) @ (3,2) → (2,)
(2,)
>>> v @ v                    # (3,) @ (3,) → 标量
np.int64(5)
```

注意这里的措辞：`ds-00` 说"把一维权重视为 `(3, 1)` 参与乘法，结果为 `(3, 1)`"，前半句对、后半句不对——补上的维度会在乘法后去掉，所以 `(3, 3) @ (3,)` 的结果是 `(3,)`，不是 `(3, 1)`。`ds-00` 对应段落已按此修正。

### 1.7.4 插入轴：newaxis

`None`（等价于 `np.newaxis`）在指定位置插入一个长度为 1 的维度，这是手工控制广播方向的标准手段：

```python
>>> a = np.array([1, 2, 3])
>>> b = np.array([10, 20])
>>> (a[:, None] * b).shape
(3, 2)
>>> a[:, None] * b           # 等价于 np.outer(a, b)
array([[10, 20],
       [20, 40],
       [30, 60]])
>>> np.outer(a, b)
array([[10, 20],
       [20, 40],
       [30, 60]])
```

### 1.7.5 broadcast_to：广播是"零步长视图"

广播不复制数据，实现方式是**把被拉伸那一维的 stride 设为 0**：

```python
>>> c = np.arange(4)
>>> bb = np.broadcast_to(c, (3, 4))
>>> bb.shape, bb.strides
((3, 4), (0, 8))
>>> bb.flags.writeable
False
>>> np.shares_memory(bb, c)
True
```

`strides=(0, 8)` 的含义：行下标怎么变，地址都不动——三行指向同一份数据。正因为多行共享内存，`broadcast_to` 的结果**只读**，防止"以为在改第 2 行、实际改了全部"。

> **注意**：`bb.nbytes` 会显示 `96`（3×4×8），但实际分配的内存仍只有 `c` 的 32 字节。`nbytes` 是**逻辑大小**，不是分配量；想测真实占用要用 `tracemalloc`（1.15 节）。

### 1.7.6 keepdims：让归约结果重新可广播

归约会**删掉**被归约的维度，于是结果常常不能再与原数组广播：

```python
>>> m = np.arange(6).reshape(2, 3)
>>> m.mean(axis=1)
array([1., 4.])
>>> (m - m.mean(axis=1)).shape
ValueError: operands could not be broadcast together with shapes (2,3) (2,)
```

保留长度为 1 的维度就能对齐：

```python
>>> m.mean(axis=1, keepdims=True)
array([[1.],
       [4.]])
>>> m - m.mean(axis=1, keepdims=True)
array([[-1.,  0.,  1.],
       [-1.,  0.,  1.]])
```

"减去行均值"这类中心化操作，`keepdims=True` 是最干净的写法。轴（axis）的完整语义是 1.8 节的主题。

### 1.7.7 广播的内存代价

广播本身不复制数据，但**运算结果会物化**：

```python
>>> p = np.ones((1000, 1))
>>> q = np.ones((1, 1000))
>>> (p + q).nbytes
8000000
```

`p` 与 `q` 各只有 8 KB，相加的结果却是 8 MB。数据量大时，一个广播表达式就能瞬间造出巨大的临时数组。

> **实战建议**：广播表达式写得越短，越要问一句"中间结果多大"。需要复用这块内存时用 `out=`（1.9 节）；想避免中间数组时考虑 `np.einsum`（1.12 节）或分块处理（1.15 节）。

> **延伸阅读**：广播在 C 层的实现（零步长迭代器、`nditer`）见 `ds-01c` 第 C7 节；`einsum` 如何避免物化中间结果见第 C6 节。

**随堂自测 1.7**

1. `(3, 1, 4)` 与 `(2, 1)` 能否广播？结果 shape 是多少？先用三条规则手推，再写代码验证。
2. `M` 的 shape 是 `(4, 5)`、`v` 的 shape 是 `(5,)`，`M @ v` 与 `v @ M.T` 分别是什么 shape？
3. `a` 的 shape 是 `(3,)`，要得到 `(3, 1)` 应该怎么写？要得到 `(1, 3)` 呢？
4. `np.broadcast_to(c, (1000, 4))` 之后 `bb.nbytes` 是多少？实际新分配了多少内存？为什么结果不可写？
5. 为什么 `m - m.mean(axis=1)` 会报错，加上 `keepdims=True` 就好了？

**本节交付**：广播规则兑现了 `ds-00` 的承诺，是 1.8 节轴归约、1.11 节形状代数、卷 3 特征标准化与卷 4 批量张量运算的直接前提；`broadcast_to` 的零步长机制与只读约定交付给 `ds-01b`。

---

## 1.8 轴（axis）：归约的方向

如果只允许保留一个 NumPy 概念，很多老手会选 `axis`。它出现的频率太高（`sum`、`mean`、`max`、`sort`、`concatenate`、`stack`……），而理解门槛只有一个：**axis 不是方向，是"要消掉的那一维"。**

### 1.8.1 一句话：axis 是"要消掉的那一维"

```python
>>> import numpy as np
>>> m = np.arange(6).reshape(2, 3)
>>> m
array([[0, 1, 2],
       [3, 4, 5]])
>>> m.sum()
np.int64(15)
>>> m.sum(axis=0)             # 消掉第 0 维（行）→ 每列一个和
array([3, 5, 7])
>>> m.sum(axis=1)             # 消掉第 1 维（列）→ 每行一个和
array([ 3, 12])
>>> (m.sum(axis=0).shape, m.sum(axis=1).shape, m.sum().shape)
((3,), (2,), ())
```

`axis=0` 的结果是 `(3,)`——长度等于列数，因为被消掉的是行。把"沿 axis=0 求和"理解成"对每一行求和"是最常见的误读；正确的读法是"**沿第 0 维把元素压到一起，结果里不再有这一维**"。

> **记忆口诀**：`axis=k` ⇒ 结果的 shape 等于原 shape 去掉第 *k* 项。用这一条自检，比记"横着加还是竖着加"可靠得多。

### 1.8.2 高维与负数轴

```python
>>> t = np.arange(24).reshape(2, 3, 4)
>>> t.shape
(2, 3, 4)
>>> t.sum(axis=0).shape       # 去掉第 0 维
(3, 4)
>>> t.sum(axis=(0, 2)).shape  # 一次去掉两维
(3,)
>>> t.sum(axis=-1).shape      # 负号从右往左数，-1 是最后一维
(2, 3)
```

`axis=-1` 与 `axis=ndim-1` 等价。高维数组里负数轴更可读：写 `axis=-1` 的人想表达的是"每个样本的最后一维"，不必关心它是第几维。

### 1.8.3 argmax / argmin 返回的是下标，不是值

```python
>>> m.argmax()                # 展平之后的全局下标
np.int64(5)
>>> m.argmax(axis=0)          # 每列最大值所在的行号
array([1, 1, 1])
>>> m.argmax(axis=1)          # 每行最大值所在的列号
array([2, 2])
>>> np.unravel_index(m.argmax(), m.shape)   # 全局下标还原成坐标
(np.int64(1), np.int64(2))
```

不带 `axis` 时 `argmax` 把数组当一维看，返回的是**展平下标**；要拿回多维坐标，用 `np.unravel_index`。

> **⚠️ 陷阱**：`argmax(axis=...)` 返回的是**下标**，想取值还要 `np.take_along_axis` 或花式索引。而且遇到并列最大值时返回的是**第一个**出现的位置，这是规则不是巧合。

### 1.8.4 所有"沿轴"操作共享同一套语义

`sum`、`mean`、`max`、`cumsum`、`sort`、`diff` 的 `axis` 含义完全一致，学会一个就学会了全部：

```python
>>> np.cumsum(m, axis=0)
array([[0, 1, 2],
       [3, 5, 7]])
>>> np.cumsum(m, axis=1)
array([[ 0,  1,  3],
       [ 3,  7, 12]])
>>> np.diff(m, axis=1)        # 相邻差，长度减少 1
array([[1, 1],
       [1, 1]])
```

> **⚠️ 陷阱**：`np.apply_along_axis` 看起来能"沿轴套用任意函数"，但它在 Python 层循环，速度与写 `for` 循环同级。它属于万不得已的逃生口，且本章之后的所有"沿轴"需求都应优先用向量化原语解决（1.15 节）。

**随堂自测 1.8**

1. `a` 的 shape 是 `(4, 3, 2)`。`a.sum(axis=1)` 与 `a.sum(axis=(0, 2))` 的 shape 分别是什么？
2. `m.argmax(axis=0)` 返回的每个数字代表什么？为什么它的长度等于列数？
3. `np.sum(t, axis=None)` 与 `np.sum(t)` 有区别吗？结果 shape 是什么？
4. `axis=-1` 在三维数组里等价于哪个正数轴？

**本节交付**：轴语义是 1.10 节全部聚合函数、`ds-02` `groupby` 方向直觉、`ds-04` 按样本/按特征统计的分界线（"沿哪个轴归约"决定了统计量是 per-feature 还是 per-sample）。

---

## 1.9 ufunc：逐元素计算的引擎

### 1.9.1 ufunc 与运算符是一回事

NumPy 的逐元素函数叫 **ufunc**（universal function），运算符只是它的语法糖：

```python
>>> a = np.array([1., 4., 9.])
>>> np.sqrt(a)
array([1., 2., 3.])
>>> np.add(a, 1)              # 与 a + 1 完全等价
array([ 2.,  5., 10.])
>>> a + 1
array([ 2.,  5., 10.])
>>> (np.add.nin, np.add.nout)
(2, 1)
```

`nin` / `nout` 是输入输出个数：`np.add` 收两个、出一个。常见 ufunc 覆盖算术、三角、指数对数、比较、位运算；运算符到 ufunc 的映射是固定的（`+` → `np.add`，`**` → `np.power`，`//` → `np.floor_divide`，`%` → `np.remainder`）。

### 1.9.2 out=：把结果写回已有内存

默认情况下每次运算都分配新数组。`out=` 让你把结果写进预先分配的内存，循环里能省下大量分配与回收：

```python
>>> x = np.arange(4.0); y = np.arange(4.0); dest = np.empty(4)
>>> np.add(x, y, out=dest) is dest
True
>>> dest
array([0., 2., 4., 6.])
```

`out=` 返回的就是传入的那个数组本身。`x += 1` 本质上就是 `np.add(x, 1, out=x)`。

### 1.9.3 where=：只在掩码为真的位置计算

`where=` 把掩码交给 ufunc，只计算被选中的位置，其余位置保留 `out=` 里的原值：

```python
>>> np.sqrt(np.array([4., -1., 9.]), where=np.array([4., -1., 9.]) >= 0, out=np.full(3, -1.))
array([ 2., -1.,  3.])
```

负数位置没有被计算，`out` 里的 `-1.` 原样保留。这样既避免了 `np.sqrt(-1)` 的警告，也避免了先算再筛的浪费。

> **⚠️ 陷阱**：`where=` 必须配合 `out=` 才可靠。不给 `out` 时，未计算的位置内容是**未初始化内存**，你会读到随机值。

### 1.9.4 reduce / accumulate / outer / at

ufunc 自带四个方法，把逐元素函数变成聚合工具：

```python
>>> v = np.arange(1, 5)
>>> np.add.reduce(v)          # 归约：等价于 v.sum()
np.int64(10)
>>> np.add.accumulate(v)      # 累积：等价于 v.cumsum()
array([ 1,  3,  6, 10])
>>> np.multiply.outer(v, v)   # 外积：等价于 np.outer(v, v)
array([[ 1,  2,  3,  4],
       [ 2,  4,  6,  8],
       [ 3,  6,  9, 12],
       [ 4,  8, 12, 16]])
```

`np.add.at` 解决一个特殊问题：**带重复下标的原地累加**。

```python
>>> z = np.zeros(3, dtype=int)
>>> np.add.at(z, [0, 0, 1], 1)
>>> z
array([2, 1, 0])
>>> z2 = np.zeros(3, dtype=int)
>>> z2[[0, 0, 1]] += 1        # 重复下标只生效一次
>>> z2
array([1, 1, 0])
```

原因是 `z2[[0,0,1]] += 1` 会先把 `z2[[0,0,1]]` **读出来**（拷贝），加 1 后再写回；两次写回下标 0 的后一次覆盖前一次。`np.add.at` 是"无缓冲"的原地累加，每次都会真的加到内存上。做计数统计、词频累加、梯度累加时，这是必踩的坑。

### 1.9.5 自定义 ufunc 的真相

`np.vectorize` 名字很唬人，它**不做任何性能优化**，只是让一个 Python 函数能按数组语法调用：

```python
>>> vf = np.vectorize(lambda s: s.upper())
>>> type(vf)
<class 'numpy.vectorize'>
```

本机实测（100 万元素）：`np.vectorize` 约 85 ms，等价的 Python 列表推导外推约 92 ms，而原生向量化 `arr * 2 + 1` 只有 0.5 ms——**两个数量级**的差距。原因很简单：`vectorize` 内部仍然是 Python 层逐元素调用。

> **实战建议**：`np.vectorize` 只用来提升**可读性**，永远不要指望它提性能。真需要给任意 Python 函数加速时，走 1.15 节的路子（Numba / Cython，或先想办法向量化）。

> **延伸阅读**：ufunc 的循环选择、类型解析与 SIMD 调度见 `ds-01c` 第 C1、C2 节。

**随堂自测 1.9**

1. `a + b`、`np.add(a, b)`、`np.add(a, b, out=dest)` 三者在内存分配上有什么区别？
2. `np.sqrt(x, where=x >= 0)` 不给 `out=` 会有什么风险？
3. 为什么 `z[[0, 0, 1]] += 1` 只让 `z[0]` 增加了 1？正确的写法是什么？
4. `np.vectorize` 能让一个纯 Python 函数快多少倍？为什么？

**本节交付**：`out=` / `where=` 是 1.15 节性能优化的主要手段；`np.add.at` 是 `ds-02` 分组计数与卷 3 梯度累加的底层原语；ufunc 协议本身交付给 1.16 节。

---

## 1.10 聚合、排序与统计原语

### 1.10.1 常用聚合与 ddof

```python
>>> a = np.array([3, 1, 4, 1, 5, 9, 2, 6])
>>> a.sum()
np.int64(31)
>>> a.mean()
np.float64(3.875)
>>> a.std()
np.float64(2.5708704751503917)
>>> a.var(ddof=1)
np.float64(7.553571428571429)
>>> a.min(), a.max()
(np.int64(1), np.int64(9))
>>> np.ptp(a)                 # 极差 = max - min
np.int64(8)
>>> np.median(a)
np.float64(3.5)
>>> np.percentile(a, [25, 50, 75])
array([1.75, 3.5 , 5.25])
>>> a.argmin(), a.argmax()
(np.int64(1), np.int64(5))
```

`ddof` 的口径问题在 `ds-00` 已经讲过（NumPy 默认除 *n*，pandas 默认除 *n-1*），这里只强调：**`std`/`var` 的 `ddof` 默认值是 0，和 pandas 不一致，混用时先对齐。**

### 1.10.2 NaN 家族

普通聚合遇到 `NaN` 会"污染"整个结果；`nan*` 家族会跳过它们：

```python
>>> b = np.array([1.0, np.nan, 3.0])
>>> b.mean()
np.float64(nan)
>>> np.nanmean(b)
np.float64(2.0)
>>> b.sum()
np.float64(nan)
>>> np.nansum(b)
np.float64(4.0)
>>> np.isnan(b)
array([False,  True, False])
>>> np.isfinite([1.0, np.inf, np.nan])
array([ True, False, False])
```

> **⚠️ 陷阱**：`np.nansum([np.nan])` 返回 `0.0`。原因是"把 NaN 当成 0 再求和"，而"全是 NaN"和"真正的 0"在这里无法区分。做缺失率统计时要单独用 `np.isnan` 计数，不要从 `nansum` 反推。另一个坑：整段都是 NaN 时 `np.nanmean` 会发 `RuntimeWarning` 并返回 `nan`，批处理中要显式处理。

### 1.10.3 排序与 top-k

```python
>>> c = np.array([3, 1, 4, 1, 5])
>>> np.sort(c)
array([1, 1, 3, 4, 5])
>>> np.argsort(c)             # 排序后的下标
array([1, 3, 0, 2, 4])
>>> np.partition(c, 2)        # 第 2 小的位置对了，两侧无序
array([1, 1, 3, 4, 5])
>>> c[np.argpartition(c, -2)[-2:]]   # 最大的两个（无序）
array([4, 5])
```

`partition` 是 O(*n*)，`sort` 是 O(*n* log *n*)；**只要 top-k、不要完整排序时用 `argpartition`**，大数组上差距明显。

计数与分箱：

```python
>>> np.unique(np.array([3, 1, 3, 2]), return_counts=True)
(array([1, 2, 3]), array([1, 1, 2]))
>>> np.bincount(np.array([0, 1, 1, 3]))   # 非负整数计数，下标即取值
array([1, 2, 0, 1])
>>> np.histogram(a, bins=3)
(array([4, 3, 1]), array([1.        , 3.66666667, 6.33333333, 9.        ]))
```

> **⚠️ 陷阱**：`np.sort` 默认用 quicksort，**不稳定**——相等元素的相对顺序不保证。需要稳定排序时显式写 `kind='stable'`（或 `'mergesort'`）。按多列排序、或"排序后还要保持原始次序"的场景，必须指定。

### 1.10.4 分位数的插值方法

分位数落在两个数据点之间时怎么取值，由 `method` 决定，默认是 `'linear'`：

| `method` | `np.percentile([1,2,3,4], 25, method=...)` |
|----------|-------------------------------------------|
| `'linear'`（默认） | 1.75 |
| `'lower'` | 1 |
| `'higher'` | 2 |
| `'midpoint'` | 1.5 |
| `'nearest'` | 2 |

同一份数据，不同工具默认方法不同（Excel、pandas、R 各有口径），**对外的统计口径必须写明用的是哪一种**。

### 1.10.5 浮点求和的非结合性

浮点加法不满足结合律，求和顺序会影响结果：

```python
>>> import math
>>> x = np.array([1e16, 1.0, -1e16])
>>> x.sum()
np.float64(0.0)
>>> math.fsum(x)
1.0
```

`1e16 + 1.0` 在双精度下等于 `1e16`（1.0 被吸收），再减 `1e16` 就得到 0；而 `math.fsum` 做精确累加，得到正确的 1.0。

> **机制洞察**：NumPy 的归约使用**成对求和**（pairwise summation），把误差从 O(*n*) 降到 O(log *n*)，所以它比手写左到右累加准得多；但它仍然不精确。对精度敏感的场景（金额、长时间序列累加），要么用 `math.fsum`，要么在算法层面避免大数吞小数。完整推导见 `ds-01c` 第 C3 节。

**随堂自测 1.10**

1. `np.median` 与 `np.percentile(a, 50)` 有区别吗？`np.ptp` 算的是什么？
2. `np.nanmean` 会跳过 `NaN`，那 `np.nansum([np.nan, np.nan])` 返回什么？为什么这个结果危险？
3. 要从 100 万个数里取最大的 10 个，用 `np.sort` 还是 `np.argpartition`？为什么？
4. `np.percentile([1,2,3,4], 25)` 为什么是 1.75 而不是 1 或 2？换 `method='lower'` 会怎样？

**本节交付**：聚合与排序原语是 `ds-02` `describe`/`groupby` 的计算内核、`ds-04` 分位数与置换检验的构件；NaN 家族直接决定 `ds-02` 缺失值策略的写法。

---

## 1.11 形状代数：变形、拼接、拆分

### 1.11.1 变形：reshape / ravel / flatten

```python
>>> m = np.arange(6).reshape(2, 3)
>>> m.reshape(3, 2)
array([[0, 1],
       [2, 3],
       [4, 5]])
>>> m.reshape(-1)             # -1 表示"这一维自动推算"
array([0, 1, 2, 3, 4, 5])
>>> m.reshape(-1).shape
(6,)
```

`reshape` 只在内存布局允许时返回视图；`ravel` 同理，`flatten` 则**总是拷贝**：

```python
>>> np.shares_memory(m.ravel(), m)
True
>>> np.shares_memory(m.T.ravel(), m)   # 非连续 → 只能拷贝
False
```

> **⚠️ 陷阱**：`m.ravel() is m.reshape(-1)` 是 `False`，但它们共享内存——**判断共享内存不能用 `is`**（1.2.6、1.6.6 已说明）。另外 `reshape` 需要拷贝时不会告诉你，只会静默多分配一块内存；大数组上要知道自己在做什么。

### 1.11.2 轴重排：transpose / swapaxes / moveaxis

```python
>>> t = np.arange(24).reshape(2, 3, 4)
>>> t.transpose(1, 0, 2).shape   # 完全指定新顺序
(3, 2, 4)
>>> np.swapaxes(t, 0, 2).shape   # 交换两维
(4, 3, 2)
>>> np.moveaxis(t, 0, -1).shape  # 把某一维挪到某处
(3, 4, 2)
```

三者都只改 strides、不搬数据。**可读性排序：`moveaxis` > `swapaxes` > `transpose`**——前两者的意图一眼可见，`transpose` 的数字串容易写错。

### 1.11.3 拼接与拆分

```python
>>> p = np.array([1, 2]); q = np.array([3, 4])
>>> np.concatenate([p, q])    # 沿已有轴接起来
array([1, 2, 3, 4])
>>> np.stack([p, q])          # 新增一个轴
array([[1, 2],
       [3, 4]])
>>> np.stack([p, q], axis=1)
array([[1, 3],
       [2, 4]])
>>> np.column_stack([p, q])
array([[1, 3],
       [2, 4]])
```

```python
>>> np.split(np.arange(6), 3)
[array([0, 1]), array([2, 3]), array([4, 5])]
>>> np.array_split(np.arange(7), 3)   # 不能等分时也拆得开
[array([0, 1, 2]), array([3, 4]), array([5, 6])]
```

`concatenate` 要求**除拼接轴以外的所有维度都相同**，否则报错：

```python
>>> np.concatenate([np.zeros((2, 3)), np.zeros((2, 4))], axis=1).shape
(2, 7)
```

> **⚠️ 陷阱**：`stack` 与 `concatenate` 的区别是"要不要新增维度"。`np.stack([p, q])` 得到 `(2, 2)`，`np.concatenate([p, q])` 得到 `(4,)`。用错不会报错，只会悄悄改变后续运算的广播行为。另外：**不要在循环里反复 `concatenate`**，每次都会重新分配并复制全部已有数据，n 次循环是 O(*n²*) 的拷贝量；正确做法是先算总长度、一次性分配、按位置写入（1.15 节）。

### 1.11.4 重复与填充

```python
>>> np.tile(np.array([1, 2]), 3)      # 整块重复
array([1, 2, 1, 2, 1, 2])
>>> np.repeat(np.array([1, 2]), 3)    # 逐元素重复
array([1, 1, 1, 2, 2, 2])
>>> np.pad(np.array([1, 2, 3]), 1)    # 两侧各补 1 个 0
array([0, 1, 2, 3, 0])
```

`tile` 与 `repeat` 的区别是高频混淆点：`tile` 重复**整个数组**，`repeat` 重复**每个元素**。`np.pad` 支持多种模式（`'edge'`、`'reflect'`、`'constant'` 等），是信号处理与卷积前处理的标准工具。

**随堂自测 1.11**

1. `m` 的 shape 是 `(2, 3)`，`m.reshape(-1)` 与 `m.T.reshape(-1)` 的结果一样吗？为什么？
2. `np.concatenate([p, q])` 与 `np.stack([p, q])` 的结果 shape 分别是什么？什么时候该用哪个？
3. `np.tile(a, 3)` 与 `np.repeat(a, 3)` 对 `a = [1, 2]` 分别得到什么？
4. 要把 1000 个长度相同的一维数组拼成矩阵，为什么不应在循环里 `np.concatenate`？替代方案是什么？

**本节交付**：形状代数是卷 3 特征矩阵组装、卷 4 张量 reshape/permute 的直接原型；"先算总长再一次性分配"的拼接纪律交付给 1.15 节。

---

## 1.12 线性代数最小集与 einsum

### 1.12.1 `@` / `matmul` / `dot` 的分工

二维情形三者一致，三维以上 `dot` 与 `@` 的规则不同：

```python
>>> A = np.arange(6).reshape(2, 3); B = np.arange(12).reshape(3, 4)
>>> (A @ B).shape
(2, 4)
>>> (np.dot(A, B) == A @ B).all()
np.True_
>>> X = np.arange(24).reshape(2, 3, 4); Y = np.arange(40).reshape(2, 4, 5)
>>> (X @ Y).shape             # @ 是批量矩阵乘：最后两维做矩阵乘
(2, 3, 5)
>>> np.dot(X, Y).shape        # dot 的规则完全不同！
(2, 3, 2, 5)
```

`@`（即 `np.matmul`）把最后两维当矩阵、前面所有维当**批次**；`np.dot` 则是"左操作数最后一维 × 右操作数倒数第二维"的通用收缩。**新代码统一用 `@`**，`np.dot` 只在明确需要它的旧行为时使用。

### 1.12.2 np.linalg 最小集

```python
>>> M = np.array([[3., 1.], [1., 2.]]); b = np.array([9., 8.])
>>> np.linalg.solve(M, b)
array([2., 3.])
>>> np.linalg.inv(M) @ b      # 结果一样，但不该这么写
array([2., 3.])
>>> np.linalg.det(M)
np.float64(5.000000000000001)
>>> np.linalg.norm(b)
np.float64(12.041594578792296)
>>> np.linalg.matrix_rank(M)
np.int64(2)
```

> **⚠️ 陷阱**：解线性方程组要用 `np.linalg.solve`，**不要写 `inv(M) @ b`**。求逆再相乘既慢（多做一次矩阵求逆）又更不稳定。`det` 的结果是 `5.000000000000001` 而不是 `5`——这正是"别用行列式判断奇异性"的理由，判断奇异性用 `matrix_rank` 或条件数。

按 `ds-00` 的约定，本卷只收最小集；`svd`、`eigh`、`lstsq` 属于卷 3 的场景，届时随用随讲。

### 1.12.3 einsum：一种写法覆盖所有收缩

`np.einsum` 用爱因斯坦求和约定描述任意维度的乘法与求和，规则是"**输入里出现、输出里没有的下标，就被求和掉**"：

```python
>>> np.einsum('ij,jk->ik', A, B)      # 矩阵乘
array([[20, 23, 26, 29],
       [56, 68, 80, 92]])
>>> np.allclose(np.einsum('ij,jk->ik', A, B), A @ B)
True
```

同一套语法能表达点积、外积、对角线、迹、转置、Frobenius 范数：

| 写法 | 含义 | 等价 API |
|------|------|---------|
| `'i,i->'` | 点积 | `v @ w` |
| `'i,j->ij'` | 外积 | `np.outer(v, w)` |
| `'ii->i'` | 对角线 | `np.diag(E)` |
| `'ii->'` | 迹 | `np.trace(E)` |
| `'ij->ji'` | 转置 | `A.T` |
| `'ij,ij->'` | Frobenius 内积 | `(A * A).sum()` |
| `'ik,jk->ij'` | Gram 矩阵 | `A @ A.T` |

```python
>>> v = np.arange(3); w = np.arange(3)
>>> np.einsum('i,i->', v, w)
np.int64(5)
>>> np.einsum('i,j->ij', v, w)
array([[0, 0, 0],
       [0, 1, 2],
       [0, 2, 4]])
>>> E = np.eye(3)
>>> np.einsum('ii->i', E)
array([1., 1., 1.])
>>> np.einsum('ij->ji', A)
array([[0, 3],
       [1, 4],
       [2, 5]])
>>> np.einsum('ik,jk->ij', A, A)
array([[ 5, 14],
       [14, 50]])
```

`einsum` 的价值有两个：一是**一个写法覆盖所有收缩**，不用记 `dot`/`tensordot`/`inner`/`outer` 各自的规则；二是**可以避免中间数组**——比如 `'ik,jk->ij'` 不必先构造 `A.T`。数据量大时加 `optimize=True` 让 NumPy 选择收缩顺序。

> **实战建议**：`einsum` 可读性取决于你对约定的熟悉度。团队代码里第一次出现时，在注释里写出它等价于哪个 `@` 或 `sum` 表达式。对链式收缩（如注意力里的 `QK^T` 再乘 `V`），`einsum` 往往比嵌套 `@` 更接近论文公式——这是它在卷 4 会反复出现的原因。

> **延伸阅读**：`@` 真实走的是 BLAS 后端、`einsum` 的路径选择与 `optimize` 策略见 `ds-01c` 第 C6 节。

**随堂自测 1.12**

1. `X` 的 shape 是 `(8, 4, 5)`、`Y` 的 shape 是 `(8, 5, 3)`，`X @ Y` 与 `np.dot(X, Y)` 的 shape 分别是什么？
2. 解 `Mx = b` 为什么该用 `np.linalg.solve(M, b)` 而不是 `np.linalg.inv(M) @ b`？
3. 用 `einsum` 写出"对 A 的每一行求和的平方"这一类收缩，并说明下标里哪些被求和掉了。
4. `np.einsum('ik,jk->ij', A, A)` 与 `A @ A.T` 等价吗？前者省掉了什么？

**本节交付**：`@` 的批量语义与 `einsum` 是卷 3 线性模型、卷 4 注意力矩阵运算的语法基础；`np.linalg` 最小集在卷 3 扩展为完整数值线性代数。

---

## 1.13 随机数：Generator 系统

`ds-00` 的 0.1.5 节只定了种子契约（"同一个种子生成完全相同的随机序列"）。本节补上完整的 API：有哪些方法、怎么生成互相独立的实验、内核能不能换。

### 1.13.1 方法族

```python
>>> import numpy as np
>>> rng = np.random.default_rng(42)
>>> rng.random(3)                              # [0, 1) 均匀浮点
array([0.77395605, 0.43887844, 0.85859792])
>>> rng.integers(0, 10, size=5)                # [0, 10) 均匀整数
array([0, 6, 2, 0, 5])
>>> rng.integers(0, 10, size=5, endpoint=True) # 含上界
array([10,  8,  8,  7,  8])
>>> rng.normal(0, 1, 3)                        # 均值、标准差
array([-0.01680116, -0.85304393,  0.87939797])
>>> rng.uniform(2.0, 5.0, 3)
array([4.78029497, 3.93159536, 4.46828484])
>>> rng.choice(np.array([10, 20, 30]), size=5) # 有放回抽样
array([20, 20, 20, 10, 10])
>>> rng.choice(np.array([10, 20, 30]), size=3, replace=False)
array([30, 20, 10])
>>> rng.permutation(5)                         # 0..4 的一个排列
array([2, 1, 3, 4, 0])
>>> rng.random(3, dtype=np.float32)            # 直接产出目标精度
array([0.7580877 , 0.70052296, 0.35452592], dtype=float32)
```

> **⚠️ 陷阱**：`integers` 的上界默认**不含**，要含上界得写 `endpoint=True`；这和 Python 的 `range` 一致，但旧接口 `np.random.randint` 同样是上界不含，很容易和"抽到 10 的概率"这类业务假设对不上。另外 `choice` 默认 `replace=True`（有放回），做**不重复抽样时必须显式写 `replace=False`**，否则你会抽出重复样本而不自知。

`shuffle` 与 `permutation` 的区别是原地与返回副本：

```python
>>> rng = np.random.default_rng(42)
>>> a = np.array([1, 2, 3, 4])
>>> rng.shuffle(a)                             # 原地打乱
>>> a
array([4, 3, 2, 1])
```

> **⚠️ 陷阱**：`rng.shuffle` **原地修改**传入的数组。传给函数、或传的是某个数组的切片/视图时，被打乱的是原数据。要保留原顺序就先 `.copy()`，或者改用返回新数组的 `rng.permutation`。

### 1.13.2 SeedSequence：生成互相独立的实验

`ds-00` 的实战建议说"每个独立实验各自 `default_rng(seed)`"。手工挑选不同数字当种子并不能保证实验之间独立；正规做法是用 `SeedSequence` **派生**子种子：

```
spawn_keys: [(0,), (1,), (2,)]
streams   : [[497, 916, 581], [74, 467, 182], [703, 71, 771]]
再次 spawn: [(3,), (4,), (5,)]
```

第二次运行会得到**完全相同**的前两行——子种子由父种子的熵确定性地派生，同时彼此独立。这正是多次重复实验、并行训练、交叉验证分折所需要的。

> **⚠️ 陷阱**：`SeedSequence.spawn` 会**推进内部计数**，重复调用会派生出不同的子序列（上面第三行就是证据）。要可复现，必须**只 spawn 一次并把结果存下来**；在循环里反复 `ss.spawn(1)` 会让你每次拿到新种子，"可复现"当场失效。

### 1.13.3 BitGenerator：可替换的随机数内核

`default_rng()` 默认使用 **PCG64** 内核；需要别的统计性质时可以替换，而 Generator 的 API 不变：

```python
>>> type(np.random.default_rng().bit_generator).__name__
'PCG64'
>>> type(np.random.Generator(np.random.Philox(42)).bit_generator).__name__
'Philox'
```

日常分析用默认的 PCG64 就好。需要长周期、可并行跳跃的流（大规模仿真）时才考虑 Philox / SFC64，取舍见 `ds-01c` 第 C8 节。

### 1.13.4 给 ds-04 准备的两个原语

`ds-04` 的 bootstrap 与置换检验都建立在这两个动作上：

**重抽样（bootstrap）**——按有放回的方式重抽样本，得到"统计量的分布"：

```python
>>> data = np.array([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
>>> rng = np.random.default_rng(0)
>>> idx = rng.integers(0, len(data), size=(4, len(data)))   # 4 组重抽的下标
>>> data[idx].mean(axis=1)                                   # 每组一个均值
array([3.875, 6.125, 5.25 , 5.125])
```

**置换（permutation test）**——打乱标签重新计算，看原结果有多极端：核心动作就是 `rng.permutation(labels)`。`ds-04` 会给出完整流程。

**随堂自测 1.13**

1. `rng.integers(0, 10, size=100)` 会抽到 10 吗？要抽到 10 该怎么写？
2. `rng.choice(a, size=5)` 与 `rng.choice(a, size=5, replace=False)` 有什么区别？分别适合什么场景？
3. `rng.shuffle(a)` 与 `rng.permutation(a)` 哪个会改动 `a`？
4. 为什么"给每个实验随便挑一个不同的整数当种子"不如 `SeedSequence.spawn`？`spawn` 本身有什么使用禁忌？

**本节交付**：Generator API 与 bootstrap/置换原语直接交付给 `ds-04`；`ss.spawn` 是卷 3 交叉验证分折与卷 4 训练可复现性的种子管理基础。

---

## 1.14 I/O 与数据边界

NumPy 既能存自己的二进制格式，也能读写文本、内存映射和大文件。选择标准只有一条：**数据接下来要给谁用**。

### 1.14.1 二进制：save / load / savez

```python
>>> a = np.arange(5, dtype=np.int32)
>>> np.save('a.npy', a)
>>> np.load('a.npy')
array([0, 1, 2, 3, 4], dtype=int32)
>>> np.load('a.npy').dtype
dtype('int32')
>>> open('a.npy', 'rb').read(8)                # .npy 是带格式头的二进制
b'\x93NUMPY\x01\x00'
```

`.npy` 自带 dtype 与 shape，**读回来类型完全一致**——这是它比 CSV 强的关键点。多个数组打包用 `savez`：

```python
>>> np.savez('pack.npz', x=np.arange(3), y=np.arange(2))
>>> z = np.load('pack.npz')
>>> list(z.keys())
['x', 'y']
>>> z['x']
array([0, 1, 2])
```

`np.savez` 不压缩，`np.savez_compressed` 会压缩（省磁盘、慢一点）。

### 1.14.2 文本：loadtxt / genfromtxt / savetxt

```python
>>> np.savetxt('scores.csv', np.array([[85.0, 90.0], [70.0, 75.0]]), delimiter=',', fmt='%.1f')
>>> np.loadtxt('scores.csv', delimiter=',')
array([[85., 90.],
       [70., 75.]])
```

两者的差别在**缺失值**：`loadtxt` 遇到空字段直接报错，`genfromtxt` 会填成 `nan`。先造一个含空字段的文件：

```python
>>> open('missing.csv', 'w').write('1,2\n3,\n5,6\n')
11
>>> np.genfromtxt('missing.csv', delimiter=',')
array([[ 1.,  2.],
       [ 3., nan],
       [ 5.,  6.]])
>>> np.loadtxt('missing.csv', delimiter=',')
ValueError: could not convert string '' to float64 at row 1, column 2.
```

> **实战建议**：纯数值、格式规整的小文件用 `loadtxt`；带缺失、带表头、带混合类型的真实数据，**直接上 `ds-02` 的 `pd.read_csv`**。NumPy 的文本 IO 是"够用"，不是"好用"。

### 1.14.3 memmap：比内存大的数组

`np.memmap` 把磁盘文件当成数组来索引，只有访问到的页会被读进内存：

```python
>>> mm = np.memmap('big.dat', dtype=np.float64, mode='w+', shape=(4, 3))
>>> mm[:] = np.arange(12).reshape(4, 3)        # 写入磁盘文件
>>> mm.flush()
>>> np.memmap('big.dat', dtype=np.float64, mode='r', shape=(4, 3))
memmap([[ 0.,  1.,  2.],
        [ 3.,  4.,  5.],
        [ 6.,  7.,  8.],
        [ 9., 10., 11.]])
```

`np.load(..., mmap_mode='r')` 也能把 `.npy` 以内存映射方式打开，适合"数组比内存大但只需要逐块处理"的场景。

> **⚠️ 陷阱**：memmap 的读写受操作系统页缓存调度，性能特征是"顺序访问快、随机访问慢"，和内存数组完全不同。**不要**用 memmap 来规避"先想清楚数据布局"这件事；它适合流式/分块算法，不适合当通用数组使。

### 1.14.4 结构化数组：一张"表"

NumPy 可以表示带字段的记录，适合从 CSV 读进来的异构小表：

```python
>>> dt = np.dtype([('name', 'U4'), ('age', 'i4'), ('score', 'f8')])
>>> s = np.array([('Ann', 20, 88.5), ('Bob', 22, 75.0)], dtype=dt)
>>> s['age']
array([20, 22], dtype=int32)
>>> s[s['score'] > 80]                         # 字段也能参与布尔筛选
array([('Ann', 20, 88.5)],
      dtype=[('name', '<U4'), ('age', '<i4'), ('score', '<f8')])
>>> s.dtype.names
('name', 'age', 'score')
```

字段名让"第几列是什么"变成自文档的代码。但注意：`'U4'` 是**定宽**字符串，超过 4 个字符会被静默截断（1.3.6 的陷阱）。而且结构化数组的表达力和缺失值支持都远不如 DataFrame——**真正做表分析请用 `ds-02`**，这里只需认得它。

> **延伸阅读**：memmap 与页缓存、缓冲区协议、`.npy` 格式头的字节布局见 `ds-01b` 第 M2、M6 节。

**随堂自测 1.14**

1. `np.save` 与 `np.savetxt` 存同一份数据，读回来在 dtype 和形状上有什么差别？
2. `np.loadtxt` 与 `np.genfromtxt` 遇到缺失值时行为差在哪？
3. `np.memmap` 适合什么场景？为什么它不能替代内存数组？
4. 结构化数组的 `'U4'` 字段遇到 5 个字符的字符串会怎样？

**本节交付**：`save/load` 与 `.npy` 是卷 2 内部中间结果的通用载体；"文本 IO 交给 pandas"的边界直接移交给 `ds-02`。

---

## 1.15 性能工程：临时数组、内存序与反模式

NumPy 的性能问题几乎都能归到三件事上：**算了不该算的、建了不该建的数组、访问内存的方式不友好**。这一节把它们变成可测量的结论。

### 1.15.1 先测量，再优化

```python
import timeit
import numpy as np

rng = np.random.default_rng(0)
x = rng.random(200_000)

def loop(v):
    out = np.empty_like(v)
    for i in range(v.size):
        out[i] = v[i] * 2 + 1
    return out

t_loop = timeit.timeit(lambda: loop(x), number=3) / 3
t_vec = timeit.timeit(lambda: x * 2 + 1, number=200) / 200
print(f"Python 循环 {t_loop*1000:7.2f} ms  向量化 {t_vec*1000:7.3f} ms  {t_loop/t_vec:.0f}x")
```

本机实测：`Python 循环 23.75 ms  向量化 0.079 ms  300x`。**先写对、再测量、最后才向量化**——300 倍的差距值得优化，而 1.1 倍的差距不值得牺牲可读性。

### 1.15.2 out=：省的是内存，不一定是时间

```python
import numpy as np, timeit, tracemalloc
rng = np.random.default_rng(0)
n = 2_000_000
a = rng.random(n); b = rng.random(n); tmp = np.empty(n)

def peak(fn):
    tracemalloc.start(); fn(); _, pk = tracemalloc.get_traced_memory(); tracemalloc.stop()
    return pk / 1e6

print("峰值新增内存")
print("  a*b + a   ", round(peak(lambda: a * b + a), 1), "MB")
print("  out=      ", round(peak(lambda: (np.multiply(a, b, out=tmp), np.add(tmp, a, out=tmp))), 1), "MB")
print("耗时")
print("  a*b + a   ", round(timeit.timeit(lambda: a * b + a, number=20) / 20 * 1000, 2), "ms")
print("  out=      ", round(timeit.timeit(lambda: (np.multiply(a, b, out=tmp), np.add(tmp, a, out=tmp)), number=20) / 20 * 1000, 2), "ms")
```

本机实测：

```
峰值新增内存
  a*b + a    16.0 MB
  out=        0.0 MB
耗时
  a*b + a    2.60 ms
  out=       2.50 ms
```

**时间只差 4%，峰值内存却从 16 MB 降到 0。**这是一条常被讲反的结论：`out=` 的价值主要在内存，不在速度——现代分配器让"多申请一块再释放"很便宜，但**峰值内存**降不下来就会 OOM。

> **机制洞察**：`a*b + a` 要同时持有一个中间结果和新结果，峰值是数据量的 2 倍；分块/原地写法把峰值压到 1 倍。判断要不要优化时问"这块数组会有多大"，而不是"能快几个毫秒"。

### 1.15.3 内存序：非连续访问的代价

真正明显的性能差异来自**内存访问模式**。让一个操作数和自己的转置相加，访问步长立刻变得不友好：

```python
import numpy as np, timeit
rng = np.random.default_rng(0)
C = np.ascontiguousarray(rng.random((2000, 2000)))
print("C + C    ", round(timeit.timeit(lambda: C + C,   number=30) / 30 * 1000, 3), "ms")
print("C + C.T  ", round(timeit.timeit(lambda: C + C.T, number=30) / 30 * 1000, 3), "ms")
```

本机实测：`C + C 2.546 ms`，`C + C.T 14.115 ms`——**慢了 5.5 倍**。（4000×4000 时是 18.2 ms 对 106.2 ms，约 5.8 倍。）两者做的是同样多的加法，差别只在内存访问是否连续。

需要反复使用某个非连续数组时，先 `np.ascontiguousarray(x)` 把它拷成连续布局，往往比每次跨步访问更划算。

> **机制洞察**：CPU 一次读一整条缓存行（通常 64 字节），连续访问能把这条缓存行用满；跨步访问则每次只用几个字节，其余白读。这就是 `C + C.T` 慢 5 倍的全部原因，也是"为什么数组要紧凑"（1.1 节）在真实硬件上的复现。

### 1.15.4 反模式清单

| 反模式 | 问题 | 替代 |
|--------|------|------|
| 循环里 `np.append` / `np.concatenate` | 每次重新分配复制，O(*n²*) | 先算总长，一次性分配后按位置写 |
| `np.vectorize` / `np.apply_along_axis` | Python 层逐元素循环，不提速 | 真正的向量化，或 Numba/Cython |
| 反复 `astype` | 每次转换都整块拷贝 | 在读取数据时定好 dtype |
| `for i in range(n): a[i] = ...` | 每轮 Python 字节码开销 | 切片、掩码、ufunc |
| 对非连续数组反复运算 | 跨步访问，缓存命中差 | `ascontiguousarray` 一次 |
| 大数组上先算再筛 | 中间结果按最大形状分配 | `where=` / 掩码后计算 |

用追加与预分配对比一下第一条：

```
循环 append(3000 次)   3.1 ms
一次性分配             0.009 ms   346x
```

### 1.15.5 什么时候离开 NumPy

NumPy 只做"逐元素 + 归约 + 线性代数"这三类事做得好。以下情况应考虑别的工具：

- 需要**算法级加速**（递归、动态规划、复杂控制流）→ Numba、Cython（卷 1 第 15 章已铺垫）；
- 需要**惰性计算图 / 自动微分**→ PyTorch、JAX（卷 4）；
- 需要**懒求值避免中间数组**→ `numexpr`、`einsum(optimize=True)`；
- 数据是**表格语义**（分组、连接、缺失值）→ `ds-02` 的 pandas。

> **实战建议**：优化的顺序永远是 **算法 → 数据结构/dtype → 向量化 → 内存布局 → 编译扩展**。跳过前三步直接上 Numba，通常是在给一个本不该存在的循环加速。

> **延伸阅读**：缓存层次、内存带宽与 roofline 模型、Numba/Cython 的边界见 `ds-01c` 第 C7、C9 节；与卷 1 第 15 章的五层优化路线图可以对照阅读。

**随堂自测 1.15**

1. `out=` 参数主要省的是时间还是内存？用 1.15.2 的实验说明。
2. 为什么 `C + C.T` 比 `C + C` 慢好几倍？两者计算量一样吗？
3. "在循环里 `np.append`"的问题是什么？正确写法分几步？
4. 向量化的收益一定是 300 倍吗？什么时候不值得向量化？

**本节交付**：三件套（先测量、少建临时数组、照顾内存序）是卷 4 数据加载与训练循环的性能基本功；反模式清单可直接作为代码评审检查表。

---

## 1.16 互操作协议：NumPy 是数组生态的接口

NumPy 不只是"一个库"，它同时是 Python 数组生态的**协议标准**。理解这几个协议，才知道 pandas、matplotlib、PyTorch 是怎么和 NumPy 打通的。

### 1.16.1 `__array__`：把任意对象喂给 NumPy

任何实现了 `__array__` 的对象都能被 `np.asarray` 接受：

```python
>>> import numpy as np
>>> class Box:
...     def __init__(self, values):
...         self.values = list(values)
...     def __array__(self, dtype=None):
...         return np.asarray(self.values, dtype=dtype)
>>> b = Box([1, 2, 3])
>>> np.asarray(b)
array([1, 2, 3])
>>> np.asarray(b) + 10
array([11, 12, 13])
```

这是最基础的互操作入口，也是 `np.asarray(list)`、`np.asarray(tuple)` 的实现方式。写库时提供 `__array__` 就能让用户零成本地把你的类型接进 NumPy 流水线。

### 1.16.2 `__array_ufunc__` / `__array_function__`

只实现 `__array__` 的话，操作会先被转成普通 ndarray，结果就"变回 NumPy"了。要让第三方类型**保留自己的身份**，需要实现 ufunc 协议：

```python
>>> import pandas as pd
>>> s = pd.Series([0.0, np.pi / 2])
>>> type(np.sin(s)).__name__
'Series'
>>> type(np.add(s, 1)).__name__
'Series'
```

`np.sin(s)` 返回的仍是 `Series`，因为 pandas 实现了 `__array_ufunc__`（NEP 13）；`np.mean(df)` 这类函数级调用则由 `__array_function__`（NEP 18）接管。**这解释了"为什么 NumPy 函数能无缝作用在 pandas 对象上，还保留索引"**——不是 NumPy 认识 pandas，而是 pandas 主动接管了这些调用。

### 1.16.3 零拷贝边界与只读保护

几个常见容器与 NumPy 之间可以零拷贝互转：

```python
>>> import array as pyarray
>>> np.asarray(pyarray.array('d', [1.0, 2.0]))
array([1., 2.])
>>> np.frombuffer(bytearray(4), dtype=np.uint8)
array([0, 0, 0, 0], dtype=uint8)
```

**共享内存意味着改一处会影响另一处**——这是前面反复出现的主题在生态里的重演。以 pandas 为例（需要 pandas，`ds-02` 的主角）：

```python
>>> df = pd.DataFrame({"x": np.arange(4.0), "y": np.arange(4.0) * 10})
>>> arr = df.to_numpy()
>>> np.shares_memory(arr, df['x'].to_numpy())
True
>>> arr.flags.writeable
False
```

`to_numpy()` 与 DataFrame 共享内存，但返回的是**只读**数组：直接写会报 `ValueError: assignment destination is read-only`。这是保护而非限制——想改就先 `.copy()`。

> **⚠️ 陷阱**：不同库、不同版本的"是否共享内存、是否可写"并不一致。跨库传递数组时，**要么显式 `.copy()` 切断共享，要么用 `np.shares_memory` 确认**，不要凭"它应该会拷贝一份吧"来假设。

> **延伸阅读**：`__array_ufunc__` / `__array_function__` 的完整分派规则（NEP 13/18）、`__array_namespace__` 与 Array API 标准见 `ds-01c` 第 C2 节；到卷 4 会用到 `torch.from_numpy` 的共享内存语义。

**随堂自测 1.16**

1. 一个类要实现哪个方法，才能被 `np.asarray` 接受？
2. `np.sin(pd.Series)` 返回 `Series` 而不是 ndarray，靠的是哪个协议？
3. `df.to_numpy()` 与 `df` 共享内存吗？为什么不能直接改它的元素？
4. 跨库传数组时，怎么确认两个对象是否共享内存？

**本节交付**：三个协议是 `ds-02`（pandas）、`ds-03`（matplotlib 数据输入）、`ds-04` 与卷 3/卷 4 张量互转的共同接口层；"共享内存 + 只读保护"的判据回链 1.6 节。

---

## 1.17 调试与验证：把静默错误变成显式失败

NumPy 的错有三类，**排查顺序是固定的：先看形状，再看 dtype，最后才怀疑数值**。反过来查会浪费大量时间。

### 1.17.1 形状错误：报错信息已经把答案写好了

```python
>>> np.arange(6).reshape(2, 3) + np.arange(4)
ValueError: operands could not be broadcast together with shapes (2,3) (4,)
```

NumPy 的广播报错会**原样打印两边的 shape**。看到这类信息先按 1.7 节的三条规则对一遍，不要急着去改代码。函数入口处加一行断言，能把定位成本从"翻遍调用栈"降到"看一眼堆栈"：

```python
def standardize(x):
    x = np.asarray(x)
    assert x.ndim == 2, f"expected 2-D, got shape {x.shape}"
    return (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
```

### 1.17.2 dtype 错误：三类静默陷阱

回顾前文出现过的、**不报错但结果错**的情况：

| 现象 | 位置 |
|------|------|
| 整数溢出静默回绕 | 1.3.2 |
| 定宽字符串静默截断 | 1.3.6 |
| `(3,)` 与 `(3,1)` 广播出外积 | 1.7.2 |
| `z[[0,0,1]] += 1` 重复下标只生效一次 | 1.9.4 |
| `np.nansum([nan]) == 0.0` | 1.10.2 |

对这类错误的防线是**断言**：进入关键计算前断言 dtype 与 shape，计算后断言范围。

### 1.17.3 浮点比较：永远不要用 `==`

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> 0.1 + 0.2 == 0.3
False
>>> np.isclose(0.1 + 0.2, 0.3)
np.True_
```

`np.isclose` / `np.allclose` 的默认容差是 `rtol=1e-05, atol=1e-08`：

```python
>>> np.isclose(1.0, 1.0 + 1e-9)
np.True_
>>> np.isclose(1.0, 1.0001)
np.False_
>>> np.isclose(1.0, 1.0001, rtol=1e-3)
np.True_
```

判断尺度变了，合适的容差也要跟着变：比较"米"和比较"纳米"用同一个 `rtol` 是不合理的，必要时同时指定 `atol`。

### 1.17.4 NaN 让所有比较失效

```python
>>> np.nan == np.nan
False
>>> np.isnan(np.nan)
np.True_
>>> np.array_equal([1.0, np.nan], [1.0, np.nan])
False
```

`NaN` 不等于自身，所以含 NaN 的数组用 `==`、`array_equal`、甚至 `np.allclose` 都会失败。注意两套 API 的默认值**不一致**：

| API | `equal_nan` 默认 | 容差默认 |
|-----|-----------------|---------|
| `np.allclose` | `False` | `rtol=1e-05, atol=1e-08` |
| `np.testing.assert_allclose` | `True` | `rtol=1e-07, atol=0` |

所以 `np.testing.assert_allclose([1.0, np.nan], [1.0, np.nan])` 会通过，而 `np.allclose` 同样两个输入返回 `False`。**选错了 API，要么漏掉真错误，要么在 NaN 上误报。**

### 1.17.5 用断言表达"数值契约"

```python
>>> np.testing.assert_allclose(0.1 + 0.2, 0.3)     # 通过，无输出
>>> np.testing.assert_array_equal(0.1 + 0.2, 0.3)  # 失败
AssertionError: 
Arrays are not equal

Mismatched elements: 1 / 1 (100%)
Max absolute difference among violations: 5.55111512e-17
Max relative difference among violations: 1.85037171e-16
 ACTUAL: array(0.3)
 DESIRED: array(0.3)
```

`assert_array_equal` 要求**逐位相等**，`assert_allclose` 允许容差。数值计算一律用后者；报错信息里的 "Mismatched elements" 和最大差值都能直接定位问题。

### 1.17.6 用 errstate 把静默警告变成异常

浮点异常默认只发 `RuntimeWarning` 然后继续算：

```python
>>> np.sqrt(-2.0)
np.float64(nan)
>>> with np.errstate(invalid='raise'):
...     np.sqrt(-2.0)
FloatingPointError: invalid value encountered in sqrt
```

`np.errstate` 是上下文管理器，只影响 `with` 块内的浮点错误处理，比全局的 `np.seterr` 安全。可用的开关有 `divide`、`over`、`under`、`invalid`，每个都能设成 `'ignore'` / `'warn'` / `'raise'` / `'call'` / `'print'`。

> **⚠️ 陷阱**：`np.errstate` 只管**浮点**错误。整数溢出是另一套机制，且数组版整数溢出根本不会告警（1.3.2 已实测），`errstate(over='raise')` 也拦不住。别把两者的适用范围搞混。

### 1.17.7 可复现性检查清单

交付分析结果前，逐条确认：

- [ ] 所有随机过程都用 `default_rng(seed)`，种子写进代码或配置；
- [ ] 独立实验用 `SeedSequence.spawn` 派生，且 `spawn` 只调用一次；
- [ ] 关键中间结果断言过 `shape` 与 `dtype`；
- [ ] 浮点比较用 `isclose` / `assert_allclose`，不用 `==`；
- [ ] 记录 NumPy 与 Python 版本（`np.__version__`）——提升规则与默认 dtype 都随版本变（1.3 节）。

**随堂自测 1.17**

1. 看到 `operands could not be broadcast together with shapes (2,3) (4,)`，你的第一步做什么？
2. 为什么 `np.allclose([1.0, nan], [1.0, nan])` 是 `False`，而 `np.testing.assert_allclose` 同样输入却通过？
3. `np.isclose(1.0, 1.0001)` 为什么是 `False`？要让它通过可以调什么参数？
4. `np.errstate(over='raise')` 能不能拦住 `int8` 数组的溢出？为什么？

**本节交付**：三类错误的排查顺序与数值契约写法，是 `ds-02`–`ds-04` 数据校验、卷 1 第 14 章测试纪律在数组场景的延续；可复现性清单直接作为分析交付的自检表。

---

## 1.18 综合实战：一次纯 NumPy 数据分析

前面十七节各讲一个机制，这一节把它们串成一条完整流水线：**造数据 → 存读 → 清洗 → 标准化 → 找关系 → 估不确定度**。每一步都标注它用到的机制在哪一节，读代码就是复习。

场景：8 个传感器、2000 个时间步。其中两个传感器（1 和 4）共用一个隐藏信号，我们要在不知道这件事的前提下把它找出来。

```python
import numpy as np

# ---- 第 1 步：可复现地造数据（1.13 Generator / SeedSequence）----
ss = np.random.SeedSequence(2026)
rng = np.random.default_rng(ss)
n_sensors, n_steps = 8, 2000
baseline = rng.normal(50, 5, size=(n_sensors, 1))     # 每个传感器一个基准（广播用，1.7）
drift = np.linspace(0, 3, n_steps)                    # 全局缓慢漂移（1.4 linspace）
noise = rng.normal(0, 1.5, size=(n_sensors, n_steps))
readings = baseline + drift + noise                   # (8, 2000)
shared = rng.normal(0, 1.0, size=n_steps)             # 隐藏信号
readings[1] += 2.0 * shared                           # 传感器 1 与 4 共享它
readings[4] += 2.0 * shared

# ---- 第 2 步：存盘与读取（1.14 .npy）----
np.save('readings.npy', readings.astype(np.float32))  # 选 float32 省一半内存（1.3）
data = np.load('readings.npy')
assert data.shape == (n_sensors, n_steps) and data.dtype == np.float32
print("数据:", data.shape, data.dtype, f"{data.nbytes/1000:.1f} KB")

# ---- 第 3 步：离群点检测与清洗（1.5 掩码 / 1.8 轴 / 1.10 nan 家族）----
z = (data - data.mean(axis=1, keepdims=True)) / data.std(axis=1, keepdims=True)
bad = np.abs(z) > 3                                   # 布尔掩码
print("离群点数量:", np.count_nonzero(bad))
clean = data.copy()                                   # 复制再改，不动原始数据（1.6）
clean[bad] = np.nan                                   # 掩码赋值是原地写（1.5.2）
print("清洗后各传感器均值:", np.round(np.nanmean(clean, axis=1), 2))

# ---- 第 4 步：逐传感器标准化（1.7 广播 / 1.8 轴）----
zscore = (clean - np.nanmean(clean, axis=1, keepdims=True)) / np.nanstd(clean, axis=1, keepdims=True)
print("标准化后均值(≈0):", np.round(np.nanmean(zscore, axis=1), 6))

# ---- 第 5 步：找关系（1.12 相关矩阵）----
corr = np.corrcoef(np.nan_to_num(zscore))             # 相关矩阵，对角线为 1
off = corr - np.eye(n_sensors)                        # 抹掉对角线（1.2.7 单位阵）
i, j = np.unravel_index(np.nanargmax(off), off.shape) # 最大非对角元素（1.8.3）
print(f"最相关传感器对: {i} 与 {j}, r = {corr[i, j]:.3f}")

# ---- 第 6 步：bootstrap 置信区间（1.13 重抽样 / 1.10 分位数）----
rng = np.random.default_rng(7)                        # 独立实验，各用各的种子（0.1.5）
series = clean[0][~np.isnan(clean[0])]                # 去掉缺失（1.5 布尔掩码）
idx = rng.integers(0, series.size, size=(2000, series.size))
boot = series[idx].mean(axis=1)                       # 2000 个重抽均值（1.8）
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"传感器 0 均值 95% bootstrap 区间: [{lo:.2f}, {hi:.2f}]  (直接均值 {series.mean():.2f}, n={series.size})")
```

一次实跑的输出：

```
数据: (8, 2000) float32 64.0 KB
离群点数量: 37
清洗后各传感器均值: [47.48 52.77 42.07 58.48 54.73 50.03 49.92 53.  ]
标准化后均值(≈0): [-0.e+00 -1.e-06 -2.e-06 -0.e+00 -1.e-06  2.e-06  0.e+00 -1.e-06]
最相关传感器对: 1 与 4, r = 0.654
传感器 0 均值 95% bootstrap 区间: [47.41, 47.56]  (直接均值 47.48, n=1994)
```

逐条解读：

**第 3 步抓出 37 个离群点**。`bad` 是布尔掩码，`clean[bad] = np.nan` 原地把这些位置置空——注意**读取 `data[bad]` 得到的是拷贝，但赋值写回的是原数组**（1.5.2 的四式对照）。`nanmean` 随后跳过它们。

**第 4 步的均值回到 0 附近**（量级 1e-6，是浮点误差）。这一步同时用了三条机制：`keepdims=True` 保留可广播的形状（1.7.6）、`axis=1` 表示沿传感器维度归约（1.8）、`nanstd` 跳过缺失（1.10.2）。

**第 5 步找到了传感器 1 与 4，r = 0.654**。作为对照，不相干的 1 与 2 只有 0.167。这正是我们在第 1 步埋进去的隐藏信号。`np.eye` 抹对角线、`nanargmax` + `unravel_index` 把一维下标还原成坐标，都是前面小节的原语。

**第 6 步给出区间 [47.41, 47.56]**，直接均值 47.48 落在中间。bootstrap 的逻辑是"把样本当成总体，反复有放回重抽，看统计量怎么波动"——它给出的区间宽度正比于 `ds-00` 讲过的标准误。`ds-04` 会把这个过程严格化，并说明它和解析公式的关系。

> **工程影响**：注意第 1 步与第 6 步各建了一个 `rng`：前者用 `SeedSequence`，后者用固定整数种子。**两个实验的随机性互不干扰**，这是 0.1.5 与 1.13 反复强调的纪律。如果它们共用一个全局 `np.random`，第 6 步的结果会随第 1 步消耗的随机数数量漂移。

**随堂自测 1.18**

1. 把第 3 步的 `z` 改成 `data - data.mean(axis=1)`（去掉 `keepdims`）会怎样？报什么错？
2. 第 5 步为什么要用 `corr - np.eye(n_sensors)` 抹掉对角线，而不是直接 `corr.max()`？
3. 第 2 步存成 `float32` 而不是 `float64`，对本例的结论有影响吗？什么情况下会有影响？
4. 如果第 1 步与第 6 步误用了同一个 `rng` 对象，第 6 步的结果还可复现吗？为什么？

**本节交付**：这条流水线是 `ds-02`（同样的流程换成 DataFrame）与 `ds-04`（把 bootstrap 换成严格推断）的共同骨架；对照阅读能看清"换工具不换思路"。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 数组为什么快 | 紧凑缓冲区 + 固定 dtype + 编译循环；内存省约 4 倍，逐元素运算快两个数量级 |
| 数据模型 | `buffer + dtype + shape + strides`；转置/切片只改说明，不搬数据 |
| dtype | 默认整数宽度**平台相关**（Windows `int32` / Linux `int64`）；整数溢出静默回绕；`view` 重解释、`astype` 转换 |
| 类型提升 | NEP 50：Python 标量是弱类型；`uint64 + int64 → float64`；放不下的整数报 `OverflowError` |
| 创建 | `array` 拷贝、`asarray` 不拷贝；浮点步长用 `linspace`；`empty` 不初始化 |
| 索引四式 | 基本切片=视图；布尔/花式索引读取是拷贝、赋值是原地写；`m[[0,1],[0,1]]` 是配对不是子块 |
| 视图与拷贝 | `b=a` 起外号、`b=a[:]` 开窗户、`b=a.copy()` 搬家；判共享用 `shares_memory`，别信 `.base`/`OWNDATA` |
| 广播 | 右对齐、补 1、拉伸；`broadcast_to` 用零步长实现且只读；`keepdims` 让归约结果可再广播 |
| 轴 | `axis=k` ⇒ 结果 shape 去掉第 k 项；`argmax` 返回下标；负数轴从右数 |
| ufunc | `out=` 写回已有内存、`where=` 掩码计算；`np.add.at` 处理重复下标；`np.vectorize` 不提速 |
| 聚合与排序 | `nan*` 家族跳过缺失（`nansum([nan]) == 0` 是坑）；top-k 用 `argpartition`；分位数有五种插值口径 |
| 浮点求和 | 加法不满足结合律；NumPy 用成对求和，`math.fsum` 精确 |
| 形状代数 | `reshape`/`ravel` 视情况拷贝、`flatten` 总是拷贝；`stack` 加维、`concatenate` 接维；循环里拼接是 O(n²) |
| 线代与 einsum | `@` 是批量矩阵乘、`np.dot` 规则不同；解方程用 `solve` 不用 `inv`；`einsum` 一种写法覆盖所有收缩 |
| 随机数 | `default_rng(seed)`；`SeedSequence.spawn` 派生独立实验且**只能 spawn 一次**；`shuffle` 原地 |
| I/O | `.npy` 自带 dtype/shape；文本 IO 交给 pandas；memmap 适合流式而非通用 |
| 性能 | 先测量；`out=` 省的是**内存**（峰值 16 MB→0）不是时间；非连续访问慢 5 倍以上；反模式清单 |
| 互操作 | `__array__` 进 NumPy，`__array_ufunc__`/`__array_function__` 保留身份；跨库共享内存要确认可写性 |
| 调试 | 形状 → dtype → 数值；浮点比较用 `isclose`；`np.allclose` 与 `assert_allclose` 的 NaN/容差默认值不同 |

---

#### 练习 1

**基础：把机制用对**

1. **三件套预测**：不运行代码，写出下面每一行的输出 shape 与 dtype，再验证。
   ```python
   x = np.arange(6).reshape(2, 3)
   x.sum(axis=0); x.sum(axis=1, keepdims=True); x.reshape(3, 2).T
   x[:, :2] @ np.ones(2); np.broadcast_to(x[0], (4, 3))
   ```

2. **修 bug（广播）**：下面的函数本意是"每列减去该列均值"，但**对方阵不报错却算错**（结果的列均值不是 0），对非方阵才直接报错。解释原因并修正。
   ```python
   def center_cols(x):
       return x - x.mean(axis=1)
   ```

3. **视图还是拷贝**：对 `a = np.arange(10)`，判断下面每个 `b` 是否与 `a` 共享内存，并说明理由；最后用 `np.shares_memory` 验证。
   ```python
   b1 = a[2:5]; b2 = a[a > 5]; b3 = a[[1, 3]]; b4 = a.reshape(2, 5); b5 = a.T
   ```

4. **索引四式**：给定 `a = np.array([5, 3, 8, 1, 9, 2])`，分别用基本切片、布尔掩码、花式索引取出 `[8, 1, 9]`，并说明哪一种改 `a` 会互相影响。

5. **dtype 陷阱**：`x = np.array([200], dtype=np.uint8)`，`x + 100` 的结果是什么？怎样写才能得到数学上的 300？

6. **沿轴归约**：`t` 的 shape 是 `(2, 3, 4)`。`t.mean(axis=-1)`、`t.mean(axis=(0, 2))`、`t.mean(axis=None)` 的 shape 分别是什么？

**进阶：把代码写稳**

7. **手写 `broadcast_shapes`**：不看 1.7.1，自己实现一版，并让它在 `(3, 1, 4)` 与 `(2, 1)` 上返回正确结果、在 `(3,)` 与 `(4,)` 上抛错。

8. **可断言的标准化**：写一个 `standardize(x)`，要求：输入必须是二维浮点数组、按列标准化（`ddof=1`）、返回前断言输入 shape 与 dtype，并对结果断言"列均值≈0、列标准差≈1"。

9. **top-k 不用排序**：从 1000 万个随机数里取出最大的 10 个及其下标。要求用 `argpartition`，并用 `timeit` 与 `np.sort` 对比耗时。

10. **einsum 实战**：给定 `Q` 的 shape `(8, 4, 16)`、`K` 的 shape `(8, 4, 16)`（8 个批次、4 个位置、16 维），用 `einsum` 算出每个批次的 `(4, 4)` 注意力打分矩阵，并说明下标里哪些被求和掉了。

11. **向量化改造**：把下面的双重循环改成向量化写法，并用 `timeit` 量化加速比。
    ```python
    def pairwise_diff(a):
        n = len(a); out = np.empty((n, n))
        for i in range(n):
            for j in range(n):
                out[i, j] = a[i] - a[j]
        return out
    ```

12. **可复现的 5 折**：用 `SeedSequence.spawn(5)` 为 5 折交叉验证各派生一个独立生成器，并打印每折的洗牌结果。要求把 `spawn` 的结果存下来，保证两次运行完全一致。

**深水：往实现里看一层**

13. **strides 手推**：取 `m = np.arange(24, dtype=np.int32).reshape(2, 3, 4)`，手算 `m[1, 2, 3]` 的字节偏移，并用 `memoryview(...).cast('B')` 验证。然后取 `m[:, ::2, :]`，写出它的 strides 并解释。

14. **峰值内存对比**：用 `tracemalloc` 比较 `a * b + c` 与全部 `out=` 写法在 500 万元素上的峰值内存与耗时，解释结果（参考 1.15.2）。

15. **读原始文献**：读 van der Walt 等（2011）的数组结构一节（参考文献 [1]），用自己的话解释 `buffer / dtype / shape / strides` 四者如何共同决定"一个数组"，并举一个"改变说明而不改变数据"的例子。

---

**进入下一章的准备**（对应开篇四条学习目标）：

**建模型**
- ✅ 能用"一块内存 + 三张说明"解释视图、广播、轴归约与性能现象
- ✅ 能说清 `reshape`/`ravel`/`flatten` 何时是视图、何时是拷贝

**会寻址**
- ✅ 能预判一次索引得到的是视图还是拷贝，以及赋值会不会污染原数组
- ✅ 能说出四类索引各自的读取形状与写回语义

**算得对**
- ✅ 给定两个 shape 能判断能否广播/相乘，并报出结果 shape
- ✅ 能在任意维度上沿正确的轴归约，能预判混合运算的结果 dtype
- ✅ 知道静默错误的五个高发点（整数溢出、定宽字符串截断、`(3,)` vs `(3,1)`、重复下标 `+=`、`nansum([nan])`）

**跑得快**
- ✅ 能把 Python 循环改写成向量化并量化收益
- ✅ 能用 `out=` 控制峰值内存、用 `ascontiguousarray` 处理内存序
- ✅ 能用 `default_rng` / `SeedSequence` 设计可复现的模拟实验

准备好了就进入 `ds-02`（Pandas）：本章的 ndarray 是 DataFrame 的底层存储，轴语义会变成 `groupby` 的方向直觉，布尔掩码会变成筛选与缺失值处理。本章不打基础的地方（表连接、索引对齐、时间序列），正是下一章的主角。

---

## 参考文献

按"原始论文 / 规范与 NEP / 官方文档 / 源码"四类排列。正文中的"延伸阅读"均指向本表。

**原始论文**

1. van der Walt, S., Colbert, S. C., & Varoquaux, G. (2011). *The NumPy Array: A Structure for Efficient Numerical Computation.* Computing in Science & Engineering, 13(2), 22–30. DOI: [10.1109/MCSE.2011.37](https://doi.org/10.1109/MCSE.2011.37) —— 1.2 内存模型、`ds-01b` 全篇的主要出处。
2. Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020). *Array programming with NumPy.* Nature, 585(7825), 357–362. DOI: [10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2) —— 数组编程范式与生态互操作的综述。
3. Oliphant, T. E. (2007). *Python for Scientific Computing.* Computing in Science & Engineering, 9(3), 10–20. DOI: [10.1109/MCSE.2007.58](https://doi.org/10.1109/MCSE.2007.58) —— NumPy 的设计动因与早期历史。
4. Goldberg, D. (1991). *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* ACM Computing Surveys, 23(1), 5–48. DOI: [10.1145/103162.103163](https://doi.org/10.1145/103162.103163) —— 1.3 精度、1.10.5 求和误差的经典长文。
5. O'Neill, M. E. (2014). *PCG: A Family of Simple Fast Space-Efficient Statistically Good Algorithms for Random Number Generation.* Harvey Mudd College Technical Report HMC-CS-2014-0905. [pcg-random.org/paper.html](https://www.pcg-random.org/paper.html) —— `default_rng` 默认内核 PCG64 的出处。

**规范与 NEP**

6. [NEP 50 — Promotion rules for Python scalars](https://numpy.org/neps/nep-0050-scalar-promotion.html) —— 1.3.4 弱标量提升规则。
7. [NEP 42 — New and extensible DTypes](https://numpy.org/neps/nep-0042-new-dtypes.html) —— `ds-01c` C5 节。
8. [NEP 13 — A mechanism for overriding Ufuncs](https://numpy.org/neps/nep-0013-ufunc-overrides.html) 与 [NEP 18 — A dispatch mechanism for NumPy's high level array functions](https://numpy.org/neps/nep-0018-array-function-protocol.html) —— 1.16 互操作协议。
9. [NEP 51 — Changing the representation of NumPy scalars](https://numpy.org/neps/nep-0051-scalar-representation.html) —— `np.int32(5)` 这类标量 repr 的由来。
10. [NEP 1 — A simple file format for NumPy arrays](https://numpy.org/neps/nep-0001-npy-format.html) —— 1.14.1 的 `.npy` 格式。
11. [NEP 19 — Random number generator policy](https://numpy.org/neps/nep-0019-rng-policy.html) 与 [NEP 34 — Disallow inferring `dtype=object` from sequences](https://numpy.org/neps/nep-0034-infer-dtype-is-object.html) —— 1.13 与 1.4.1。
12. NumPy 2.0 Migration Guide —— `copy=False` 语义、别名移除、标量 repr。<https://numpy.org/doc/stable/numpy_2_0_migration_guide.html>

**官方文档**

13. NumPy User Guide：*Broadcasting*、*Indexing on ndarrays*、*Data types*、*Structured arrays*、*Memory-mapped files*。<https://numpy.org/doc/stable/user/>
14. NumPy Reference：`numpy.random.Generator`、`numpy.einsum`、`numpy.linalg`。<https://numpy.org/doc/stable/reference/>

**源码与实现**

15. CPython `Lib/` 与 NumPy 的 `numpy/_core/`（ufunc 循环、`nditer`、dtype 实现）—— 读法见 `ds-01b`、`ds-01c` 各节标注。
