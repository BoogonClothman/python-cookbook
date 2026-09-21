# NumPy 深水 I：内存、strides 与所有权

> **定位**：这是 `ds-01` 第 1 章的配套深水文件，不是独立章节。主章把 ndarray 当"一块内存 + 三张说明"来用；本文件拆开这块内存，看它在 CPython 里究竟长什么样。
>
> **学习目标**：
> - **算得清**：能算出任意索引的字节偏移，能用 `memoryview` 验证
> - **判得准**：能说清一次操作是视图还是拷贝，以及谁拥有那块内存
> - **看得见**：能把"为什么慢了 5 倍"归因到缓存行与访问步长
> - **知道边界**：知道哪些 API（`as_strided`）能绕过安全检查，以及为什么不该用
>
> **阅读前提**：主章 1.1–1.7、1.14、1.15。正文中的"延伸阅读"从主章这些位置指过来：1.1.4 → M1、M2；1.2.6 → M3–M6；1.4.3 → M1、M6；1.5.3 → M5；1.6.6 → M5、M2；1.14.3 → M2、M6。
>
> **验证环境**：所有输出在 Linux 上的 Python 3.14 + NumPy 2.5 实跑得到。涉及地址、耗时、越界读到的"内存垃圾"的数字随运行变化，文中已标注。

---

## M1 CPython 对象开销与数组布局

### M1.1 一个 Python 对象要花多少字节

```python
>>> import sys
>>> sys.getsizeof(None), sys.getsizeof(True), sys.getsizeof(1), sys.getsizeof(1.0)
(16, 28, 28, 24)
>>> sys.getsizeof('abc')
44
>>> sys.getsizeof(2 ** 70)          # 超出 30 位的整数要额外分配
36
>>> sys.getsizeof([]), sys.getsizeof(())
(56, 48)
>>> sys.getsizeof([1, 2, 3])
88
```

读法：**每个 Python 对象都带一个引用计数与类型指针的头**（CPython 在 64 位上是 16 字节），再放具体数据。`float` 24 字节 = 16 头 + 8 值；`int` 28 字节 = 16 头 + 4 位宽字段 + 至少 1 个 30 位数字位；`list` 56 字节是"指针数组"的头，元素本身另行分配。

所以 `[1.0, 2.0, 3.0]` 这类列表的真实成本是"列表头 + 每元素 8 字节指针 + 每元素 24 字节对象"：

```python
>>> values = [float(i) for i in range(1000)]
>>> sys.getsizeof(values)
8856
>>> sum(map(sys.getsizeof, values))
24000
>>> sys.getsizeof(values) + sum(map(sys.getsizeof, values))
32856
>>> import numpy as np
>>> np.arange(1000, dtype=np.float64).nbytes
8000
```

32856 字节对 8000 字节，约 4 倍。注意 8856 而不是 56 + 8×1000 = 8056：CPython 的列表会**预留容量**（这里预分到 1100 个槽）。这个预留在 `append` 时才体现价值，也让"列表占用"的精确计算变得不可能——只能估算。

### M1.2 ndarray 自身的开销

ndarray 的 `sys.getsizeof` 会**把拥有的数据算进去**：

```python
>>> sys.getsizeof(np.zeros(0)), sys.getsizeof(np.zeros(1000)), sys.getsizeof(np.zeros(10 ** 6))
(112, 8112, 8000112)
```

差值正好是 `nbytes`：ndarray 对象头 112 字节（含 shape/strides 的指针、dtype 引用、维度信息），数据缓冲区跟在后面。但视图不吃这一套：

```python
>>> owner = np.zeros(1000)
>>> sys.getsizeof(owner), sys.getsizeof(owner[:10])
(8112, 112)
```

切片只报告对象头——**它不拥有数据**。这与 M5 的 `OWNDATA` 是同一件事的两个视角。

### M1.3 小整数缓存与引用计数

CPython 缓存 −5..256 的整数，所以同一数值可能是同一个对象，也可能不是：

```python
>>> int('256') is int('256')
True
>>> int('257') is int('257')
False
```

这就是"永远用 `==` 比较数值、不要用 `is`"的底层原因。用 `int(...)` 构造是为了避开编译期常量折叠，否则同一个代码对象里的字面量会被复用，看不出差别。

引用计数可以直接观察：

```python
>>> import sys
>>> a = np.arange(3)
>>> sys.getrefcount(a)              # 局部变量 a + getrefcount 的实参
2
>>> b = a
>>> sys.getrefcount(a)
3
```

`b = a` 只是让两个名字指向同一个对象，没有复制任何数据——主章 1.6.1 的"起外号"在 CPython 层的解释。

### M1.4 小结：紧凑布局的收益与代价

收益已经量化（4 倍内存、两个数量级速度）。代价是**失去灵活性**：数组一旦创建，dtype 与 shape 就固定了，改类型要 `astype`（整块拷贝），改形状要 `reshape`（必要时也拷贝）。列表则相反：灵活但昂贵。

> **延伸阅读**：分配本身为什么几乎免费，见 M6.2；内存带宽为什么是瓶颈，见主章 1.15.3 与本文件 M4。

---

## M2 缓冲区协议：PEP 3118 与 memoryview

### M2.1 memoryview 的元数据

`memoryview` 是 Python 对缓冲区协议（PEP 3118）的标准封装。它对一段内存的描述，恰好就是 ndarray 的那三张说明：

```python
>>> import numpy as np
>>> a = np.arange(6, dtype=np.int32)
>>> mv = memoryview(a)
>>> mv.format, mv.itemsize, mv.ndim
('i', 4, 1)
>>> mv.shape, mv.strides
((6,), (4,))
>>> mv.readonly, mv.c_contiguous
(False, True)
>>> mv.tolist()
[0, 1, 2, 3, 4, 5]
>>> len(bytes(mv))
24
```

`format='i'`（C 的 `int`）、`itemsize=4`、`shape=(6,)`、`strides=(4,)`——和 ndarray 的 `dtype/shape/strides` 一一对应。**缓冲区协议就是把"这块内存怎么解释"标准化，让任何库都能零拷贝地接上**。Fortran 序的数组在协议里同样如实呈现：

```python
>>> F = np.asfortranarray(np.arange(6).reshape(2, 3))
>>> memoryview(F).strides, memoryview(F).c_contiguous, memoryview(F).f_contiguous
((8, 16), False, True)
```

### M2.2 按元素 vs 按字节

这是主章 1.2.2 那个坑的完整解释。`memoryview(a)` 的索引**按元素**计数：

```python
>>> mv[1]
1
>>> mv[1:3].tolist()
[1, 2]
>>> mv.cast('B').shape          # 转成字节视图后，索引才按字节
(24,)
>>> bytes(mv.cast('B')[20:24])
b'\x05\x00\x00\x00'
```

`mv[20:24]` 若直接用在元素视图上，是"第 20 到第 23 个 **int32**"，早已越界，返回空；必须 `.cast('B')` 才按字节寻址。偏移 20 处的 4 个字节 `05 00 00 00` 是小端序的 5，与 M3 的偏移公式吻合。

### M2.3 零拷贝写穿

memoryview 与 ndarray 指向同一段内存，两个方向的修改都互相可见：

```python
>>> v = memoryview(a)
>>> v[0] = 99
>>> a[0]
np.int32(99)
>>> a[1] = 77
>>> v[1]
77
```

这不是"同步"，而是**根本没有第二份数据**。C 扩展、`struct`、`socket`、`mmap` 都通过这个协议与 NumPy 交换数据。

### M2.4 np.frombuffer 与只读边界

```python
>>> buf = bytearray(8)
>>> arr = np.frombuffer(buf, dtype=np.uint8)
>>> arr[:] = [1, 2, 3, 4, 5, 6, 7, 8]
>>> bytes(buf)
b'\x01\x02\x03\x04\x05\x06\x07\x08'
>>> np.frombuffer(b'\x01\x00\x00\x00', dtype=np.int32)
array([1], dtype=int32)
>>> np.frombuffer(b'\x01\x00\x00\x00', dtype=np.int32).flags.writeable
False
```

`bytearray` 可写，所以 `frombuffer` 得到的数组可写，且改动直接落到 `buf` 上；`bytes` 不可变，得到的数组自动**只读**。

> **⚠️ 陷阱**：`np.frombuffer` 不复制数据，所以**必须自己保证源对象在被使用期间存活**。传一个临时 `bytes` 对象进去，数组可能指向已经释放的内存。
>
> ```python
> >>> arr = np.frombuffer(bytes(8), dtype=np.uint8)   # ✅ 这里安全：bytes 被 arr 引用
> ```
> 真正危险的是把缓冲区交给别的对象管理后又让它被回收；`np.frombuffer` 会持有对缓冲区的引用，但 `mmap` 手动关闭这类操作仍需自己保证顺序。

只读属性在协议层是"单向"的：把它设成只读不会影响原数组（M5.5）。

---

## M3 strides 完全解析

### M3.1 任意索引的字节偏移

对任意维度的数组，元素 `idx` 的字节偏移是各维下标与对应 stride 的点积：

$$\text{offset}(\text{idx}) = \sum_k \text{idx}_k \times \text{strides}_k$$

这正是主章 1.2.4 的点积在内存寻址上的应用：

```python
>>> m = np.arange(24, dtype=np.int32).reshape(2, 3, 4)
>>> m.shape, m.strides
((2, 3, 4), (48, 16, 4))
>>> def offset(a, idx):
...     return sum(i * s for i, s in zip(idx, a.strides))
>>> offset(m, (1, 2, 3))
92
>>> m[1, 2, 3]
np.int32(23)
>>> mv = memoryview(m).cast('B')
>>> bytes(mv[92:96])
b'\x17\x00\x00\x00'
```

`1×48 + 2×16 + 3×4 = 92`，偏移 92 处的 4 字节确实是 23（`0x17`）。**NumPy 取元素时做的就是这个乘法加法**——没有"第几行第几列"的查找表，只有 strides。

### M3.2 负步长

反转不搬数据，只是把 stride 变成负数、把起始指针挪到末尾：

```python
>>> r = np.arange(5)[::-1]
>>> r
array([4, 3, 2, 1, 0])
>>> r.strides
(-8,)
>>> r.base is not None
True
```

`strides=(-8,)` 表示"下标每加 1，地址**减** 8 字节"。所以 `r` 是一个从原数组末尾向前走的视图，仍然零拷贝。

### M3.3 零步长

`broadcast_to` 把被拉伸的维度 stride 设为 0（主章 1.7.5）：

```python
>>> b = np.broadcast_to(np.arange(4), (3, 4))
>>> b.strides, b.nbytes, b.base.nbytes
((0, 8), 96, 32)
```

`strides=(0, 8)`：行下标怎么变地址都不动。`b.nbytes` 报 96（逻辑大小），但底层只有 32 字节——**`nbytes` 是逻辑大小，不是分配量**。因为多行共享内存，广播结果被强制只读。

### M3.4 sliding_window_view：安全的重叠视图

重叠窗口（移动平均、卷积、N-gram）可以完全零拷贝地表示：

```python
>>> x = np.arange(10)
>>> sw = np.lib.stride_tricks.sliding_window_view(x, 4)
>>> sw.shape, sw.strides
((7, 4), (8, 8))
>>> sw[:3]
array([[0, 1, 2, 3],
       [1, 2, 3, 4],
       [2, 3, 4, 5]])
>>> np.shares_memory(sw, x)
True
```

注意 `strides=(8, 8)`：**两个维度共享同一个 step**，所以相邻窗口相差一个元素——重叠就是这么来的。窗口数 7 = 10 − 4 + 1。这是 `sliding_window_view`（NumPy 1.20+）的推荐用法，它替你做了边界检查。

### M3.5 as_strided：不要用的那个

`as_strided` 让你直接指定 shape 与 strides，**NumPy 不做任何边界检查**：

```python
>>> from numpy.lib.stride_tricks import as_strided
>>> x = np.arange(5)
>>> bad = as_strided(x, shape=(4, 3), strides=(8, 8))
>>> bad.shape, bad.nbytes          # 声称 12 个元素 / 96 字节
((4, 3), 96)
>>> x.nbytes                       # 而 x 只有 5 个元素 / 40 字节
40
```

`x` 只有 5 个元素，`bad` 却声称有 12 个。读取 `bad` 会返回内存垃圾（**具体数值每次运行都不同**，因此这里不给出示例值）；越界**写**则直接破坏别的对象的内存——而且不会当场崩溃，只在很久以后以诡异的方式表现出来。

> **一条铁律**：能用 `sliding_window_view` / `reshape` / `transpose` / `broadcast_to` 表达的，绝不手写 `as_strided`。只有在写库、且能自己证明边界安全时才考虑它，并配单元测试。

---

## M4 内存序、缓存与规模效应

### M4.1 C 序与 F 序的 strides

```python
>>> c = np.ascontiguousarray(np.arange(6).reshape(2, 3))
>>> f = np.asfortranarray(c)
>>> c.strides, c.flags['C_CONTIGUOUS'], c.flags['F_CONTIGUOUS']
((24, 8), True, False)
>>> f.strides, f.flags['C_CONTIGUOUS'], f.flags['F_CONTIGUOUS']
((8, 16), False, True)
```

C 序（行优先）最后一维步长最小；F 序（列优先）第一维步长最小。`ravel` 的默认顺序是 C 序，所以对 F 序数组会触发拷贝：

```python
>>> np.shares_memory(c.ravel(), c), np.shares_memory(f.ravel(), f)
(True, False)
```

### M4.2 规模效应：缓存什么时候开始起作用

主章 1.15.3 用 `C + C.T` 展示了跨步访问的代价。这里做一次规模扫描，看它**什么时候**出现：

| N | `C + C` | `C + C.T` | 倍数 |
|---|---------|-----------|------|
| 500 | 0.138 ms | 0.202 ms | 1.5× |
| 1000 | 0.490 ms | 0.999 ms | 2.0× |
| 2000 | 2.998 ms | 15.455 ms | 5.2× |
| 4000 | 18.461 ms | 103.599 ms | 5.6× |

小矩阵时两者差不多（数据全在缓存里，怎么访问都命中）；一旦超出缓存容量，跨步访问的缓存行浪费就暴露出来，倍数稳定在 5–6 倍。**这就是"缓存局部性"从一个术语变成可测量现象的过程**，也是 1.15.3 那条结论的完整证据。

### M4.3 什么时候值得 ascontiguousarray

直觉会告诉你"先转成连续的内存更快"，但转换本身要拷贝整块：

| 方案 | 耗时（N=2000） |
|------|---------------|
| 每次跨步 `C + C.T` | 15.549 ms |
| 每次都转换 `C + ascontiguousarray(C.T)` | 15.500 ms |
| 先转换一次、之后复用连续副本 | 3.356 ms |
| （单次转换成本） | 13.332 ms |

结论很具体：**只算一次时转换毫无收益**（15.5 ms 对 15.5 ms）；单次转换 13.3 ms 的成本要靠后续多次复用摊薄——复用两次就回本，复用三次以上明显划算。判断依据是"这个非连续数组会被用几次"，而不是"连续是不是更好"。

> **⚠️ 陷阱**：`ascontiguousarray` 在输入已经连续时**不拷贝**（返回原数组或视图）。所以它在循环里是否昂贵，取决于输入的实际布局，不能靠读代码判断——要测量。

### M4.4 归约不受同样影响

一个反直觉的实测：C 序矩阵按不同轴归约，差距很小。

```
sum(axis=0)    5.965 ms
sum(axis=1)    6.298 ms
```

只有 1.06 倍，而逐元素运算的跨步代价是 5.6 倍。原因：**归约的访问顺序是可重排的**——求和与顺序无关，NumPy 的归约迭代器可以按缓存友好的顺序遍历并缓冲中间结果；而 `C + C.T` 必须按元素配对，没法重排。

> **机制洞察**：不能把"逐元素运算的缓存结论"直接搬到归约上。判断某类操作受不受内存序影响，最可靠的办法是**先测量再下结论**。主章 1.15 的三条纪律在这里再次生效。

---

## M5 所有权、别名与拷贝时机

### M5.1 .base 链

```python
>>> import numpy as np
>>> a = np.arange(6)
>>> a.base
>>> (lambda v: v.base is a)(a[1:4])
True
>>> m = a.reshape(2, 3)
>>> m.base is a
True
>>> t = m.T
>>> t.base is a, t.base is m
(True, False)
```

`.base` 指向的是**最近的缓冲所有者**，不是"上一层视图"。`m.T` 的 base 直接是 `a`，跳过了 `m`。这就是主章 1.2.6 说"`.base` 不可靠"的原因：视图链越长，它离你手上的对象越远。

花式索引与布尔索引不产生视图，`base` 是 `None`：

```python
>>> a[[0, 1]].base
>>> a[a > 2].base
```

`None` 表示"它自己拥有数据"，也就是说——**是拷贝**。

### M5.2 OWNDATA 与 sys.getsizeof

```python
>>> a.flags['OWNDATA'], m.flags['OWNDATA'], t.flags['OWNDATA']
(True, False, False)
```

`OWNDATA=False` 只说明"不拥有数据"，**不说明"与你手上的数组共享数据"**。最反直觉的案例是非连续数组上的 `reshape`：

```python
>>> flat = t.reshape(-1)
>>> flat.base is None, flat.base is t, np.shares_memory(a, flat)
(False, False, False)
```

`flat` 不拥有数据、`base` 也不是 `t`，却和 `a` 毫无共享内存——它是一次**拷贝**，`base` 指向内部临时缓冲。这与 M1.2 的 `sys.getsizeof` 互相印证：

```python
>>> sys.getsizeof(np.zeros(1000)), sys.getsizeof(np.zeros(1000)[:10])
(8112, 112)
```

要判断共享，只有 `np.shares_memory`（精确）与 `np.may_share_memory`（保守）两个可靠工具。

### M5.3 谁拷贝：判定表

| 操作 | 结果 | 依据 |
|------|------|------|
| `a[1:4]`、`a[::2]` | 视图 | 基本切片只改 strides |
| `a.reshape(...)`（可视图化） | 视图 | 只改 strides |
| `a.T`、`transpose`、`swapaxes` | 视图 | 交换 strides |
| `a.ravel()`（C 连续） | 视图 | 同上 |
| `a.view(dtype)` | 视图 | 重新解释 dtype |
| `np.broadcast_to(...)` | 只读视图 | 零步长 |
| `a[a > 3]`、`a[[0, 2]]` | 拷贝 | `__getitem__` 的整数数组分支 |
| `a.reshape(-1)`（非连续） | 拷贝 | 无法用 strides 表达 |
| `a.ravel(order='F')`（C 连续） | 拷贝 | 换遍历顺序 |
| `a.flatten()` | 总是拷贝 | 显式语义 |
| `a.astype(...)` | 总是拷贝 | 数值转换 |
| `a.copy()` | 总是拷贝 | 显式语义 |
| `a[1:4] = v` | 原地写 | `__setitem__` |

### M5.4 视图让基数组存活

`del` 只是删掉名字，视图持有对基数组的引用，基数组不会消失：

```python
>>> import sys
>>> a2 = np.arange(5); v2 = a2[1:4]
>>> sys.getrefcount(a2)
3
>>> del a2
>>> v2.base is not None
True
>>> v2
array([1, 2, 3])
```

引用计数是 3：局部名 `a2`、`v2.base`、`getrefcount` 的实参。`del a2` 后仍有 1 个引用（来自 `v2.base`），所以数据存活。**这意味着一个很小的视图可能让一大块内存无法释放**——切片保存到全局、缓存里放着不用的大数组视图，都是常见的内存泄漏形态。

### M5.5 只读不反向传播

把视图设成只读，不会影响原数组：

```python
>>> a3 = np.arange(6); v3 = a3[1:4]
>>> v3.flags.writeable = False
>>> v3.flags.writeable, a3.flags.writeable
(False, True)
```

只读是**这个视图的属性**，不是内存的属性。这既是限制也是工具：把内部缓冲区以只读视图暴露出去，调用者就不能通过这条路径改坏它（M2.4 的 `np.frombuffer(bytes)` 是同一机制的自然结果）。

---

## M6 分配、memmap 与 .npy 文件格式

### M6.1 分配器的行为

释放后立刻申请同尺寸，通常会拿回同一块地址：

```python
>>> a = np.empty(10, dtype=np.int8); a[:] = 7
>>> addr = a.ctypes.data
>>> del a
>>> b = np.empty(10, dtype=np.int8)
>>> b.ctypes.data == addr
True
```

这解释了两件事：`np.empty` 的内容为什么是"上一次的残留"，以及为什么它不应该被依赖。它也说明**分配/释放小数组通常不涉及系统调用**——CPython 与 NumPy 都在用户态缓存内存。

### M6.2 惰性页：为什么 empty 和 zeros 一样快

对一个 400 MB 的数组（5000 万个 float64）：

```
np.empty(n)          0.038 ms   （只映射地址空间）
np.zeros(n)          0.032 ms   （calloc：也是惰性零页）
np.ones(n)          60.531 ms   （必须写满 400 MB）
empty + 逐页触碰     29.317 ms
```

`np.empty` 与 `np.zeros` 都快得离谱——**它们都没有真正碰内存**。`np.empty` 只是向操作系统要一段地址空间；`np.zeros` 走 `calloc`，Linux 会给它一批"读时为零"的页，同样不写。只有 `np.ones`（或任何真正写入）才付出内存带宽的代价，60 ms 对应约 6.7 GB/s，正是这台机器的实际带宽量级。

> **机制洞察**：**分配 ≠ 触碰**。所以"用 `np.empty` 比 `np.zeros` 快"这个常见说法，在大数组上并不成立（实测 0.038 ms 对 0.032 ms，差异是噪声）。真正的成本发生在第一次写。选 `empty` 还是 `zeros`，应该由"我会不会写满每个格子"决定，而不是由速度决定。

对照小数组（8 KB，完全在缓存里），本机实测 `np.empty(1000)` 约 0.28 µs、`np.ones(1000)` 约 0.69 µs，差 2.5 倍——因为对象创建与少量写入的相对占比变大了。（小数组计时对调用次数与缓存状态很敏感，不同运行间波动明显，这里只取量级。）

### M6.3 memmap

`np.memmap` 把文件的页映射进地址空间，索引到哪读到哪：

```python
>>> import os
>>> mm = np.memmap('big.dat', dtype=np.float64, mode='w+', shape=(1000, 100))
>>> mm[:] = np.arange(100000).reshape(1000, 100)
>>> mm.flush()
>>> del mm
>>> r = np.memmap('big.dat', dtype=np.float64, mode='r', shape=(1000, 100))
>>> r.shape, r.ravel()[:3], os.path.getsize('big.dat')
((1000, 100), memmap([0., 1., 2.]), 800000)
```

`mode='w+'` 创建/覆盖，`'r'` 只读，`'r+'` 可读写；`shape` 只是**解释方式**，同一个文件可以按不同 shape 打开（文件字节数不变）。分块求和与整体求和一致：

```python
>>> total = 0.0
>>> for start in range(0, 1000, 250):
...     total += r[start:start + 250].sum()
>>> total
np.float64(4999950000.0)
>>> r.sum()
np.float64(4999950000.0)
```

`np.load(..., mmap_mode='r')` 能把 `.npy` 直接映射成 memmap：

```python
>>> np.save('big2.npy', np.arange(10, dtype=np.int64))
>>> m2 = np.load('big2.npy', mmap_mode='r')
>>> type(m2).__name__, m2[3]
('memmap', np.int64(3))
```

> **⚠️ 陷阱**：memmap 的性能取决于内核页缓存与访问模式，**顺序访问友好、随机访问昂贵**。它适合流式/分块算法（逐块扫一遍大文件），不适合当通用数组替代品。用它之前先问：我的访问模式是顺序的吗？

### M6.4 .npy 文件格式

`.npy` 就是一个头部加一段裸数据。手工解析：

```python
>>> import struct
>>> np.save('x.npy', np.arange(6, dtype=np.int16))
>>> with open('x.npy', 'rb') as f:
...     magic = f.read(6); ver = f.read(2)
...     hl = struct.unpack('<H', f.read(2))[0]
...     header = f.read(hl)
>>> magic
b'\x93NUMPY'
>>> ver
b'\x01\x00'
>>> hl
118
>>> header.decode().strip()
"{'descr': '<i2', 'fortran_order': False, 'shape': (6,), }"
```

结构一目了然：6 字节魔数 `\x93NUMPY`、2 字节版本、2 字节小端头部长度、然后是头部字典（描述 dtype、是否 F 序、shape），之后就是连续的裸数据。**这解释了 1.14.1 的核心结论：`.npy` 读回来 dtype 与 shape 完全一致**——它们就写在文件头里。

也解释了为什么 `.npy` 比 CSV 小且快：没有文本转换，没有精度损失，读它就是 `fromfile` 加一次头部解析。

### M6.5 分块处理大数组

把 M6.2、M6.3 的结论合起来，处理大于内存的数据有固定套路：

```python
def chunked_mean(path, shape, chunk_rows, dtype=np.float64):
    """对 memmap 逐块求均值，峰值内存只与 chunk_rows 有关。"""
    arr = np.memmap(path, dtype=dtype, mode='r', shape=shape)
    total, count = 0.0, 0
    for start in range(0, shape[0], chunk_rows):
        block = arr[start:start + chunk_rows]
        total += block.sum()
        count += block.size
    return total / count
```

要点三条：用 memmap 而不是 `np.load`（不把整个文件读进内存）、按行分块让每块在内存里连续、累加与计数分开以便处理不等长的最后一块。这与主章 1.15 的 `out=` 是同一思路的两个层面：**一个控制单次运算的临时数组，一个控制整个流程的常驻内存。**

---

## 本文件小结

| 主题 | 核心结论 |
|------|---------|
| 对象开销 | Python 对象带头（16 字节起）；float 24、int 28、list 头 56；紧凑数组省约 4 倍 |
| ndarray 开销 | 对象头 112 字节 + `nbytes`（视图只算 112） |
| 缓冲区协议 | `format/itemsize/shape/strides` 就是那三张说明；零拷贝双向写穿；`frombuffer` 不复制 |
| strides | 偏移 = Σ 下标×stride；负步长反转、零步长广播；`sliding_window_view` 安全重叠 |
| as_strided | 无边界检查，越界读写不报错；能用别的方式表达就别用它 |
| 缓存 | 小矩阵无差别，超缓存后跨步慢 5–6 倍；归约因可重排顺序而几乎不受影响 |
| 所有权 | `.base` 指向最近所有者；`OWNDATA` 与 `shares_memory` 是两回事 |
| 生命周期 | 视图持有基数组引用；小视图可让大数组无法释放 |
| 分配 | 分配 ≠ 触碰；大数组上 `empty`/`zeros` 都近乎免费，成本在首次写入 |
| 文件 | `.npy` = 魔数 + 版本 + 头部字典 + 裸数据；memmap 适合顺序/分块访问 |

**回到主章**：本文件解释的现象，在 `ds-01` 里的落点是——M1/M2 → 1.1、1.2；M3 → 1.2.2、1.7.5；M4 → 1.15.3；M5 → 1.2.6、1.6；M6 → 1.4.3、1.14。

**继续深入**：计算内核（ufunc 循环与 SIMD、浮点求和、排序算法、BLAS 后端、内存带宽模型、随机数内核）见配套文件 `ds-01c-numpy-internals-compute.md`。

---

## 参考文献

1. van der Walt, S., Colbert, S. C., & Varoquaux, G. (2011). *The NumPy Array: A Structure for Efficient Numerical Computation.* Computing in Science & Engineering, 13(2), 22–30. DOI: [10.1109/MCSE.2011.37](https://doi.org/10.1109/MCSE.2011.37) —— M1–M5 的主要出处。
2. [PEP 3118 — Revising the buffer protocol](https://peps.python.org/pep-3118/) —— M2 的规范。
3. [NEP 1 — A simple file format for NumPy arrays](https://numpy.org/neps/nep-0001-npy-format.html) —— M6.4 的 `.npy` 格式规范。
4. [NumPy 文档：Memory-mapped files](https://numpy.org/doc/stable/reference/generated/numpy.memmap.html)、[Internal organization of NumPy arrays](https://numpy.org/doc/stable/dev/internals.html) —— M3、M4、M6。
5. Goldberg, D. (1991). *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* ACM Computing Surveys, 23(1), 5–48. DOI: [10.1145/103162.103163](https://doi.org/10.1145/103162.103163) —— M4.4 归约精度的背景。
