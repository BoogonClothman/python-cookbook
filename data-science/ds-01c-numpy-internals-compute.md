# NumPy 深水 II：计算内核、浮点与后端

> **定位**：这是 `ds-01` 第 1 章的配套深水文件之二。主章回答"怎么用对"，`ds-01b` 回答"内存在哪"，本文件回答"算的时候究竟发生了什么"——为什么同样的循环有时快两个数量级，为什么 `optimize=True` 能快 200 倍，为什么 `np.sum` 比顺序累加准得多。
>
> **学习目标**：
> - **看清循环**：知道 ufunc 的类型签名、循环选择与 CPU 分派是怎么发生的
> - **接进生态**：能实现 `__array_ufunc__` / `__array_function__`，让自己的类型保留身份
> - **算准浮点**：能解释成对求和为什么比顺序累加准，并知道它仍不精确
> - **选对后端**：知道 `@` 走 BLAS、`einsum` 要 `optimize`，以及何时该离开 NumPy
>
> **阅读前提**：主章 1.3、1.7、1.9、1.10、1.12、1.13、1.15、1.16。主章的延伸阅读从这些位置指过来：1.3.6 → C5；1.7.5 → C7；1.7.7 → C6；1.9.5 → C1、C2；1.10.5 → C3；1.12.3 → C6；1.13.3 → C8；1.15.5 → C7、C9；1.16.2 → C2。
>
> **验证环境**：Linux（WSL2，x86_64）上的 Python 3.14 + NumPy 2.5，BLAS 为 scipy-openblas 0.3.34。耗时与 GFLOPS 随机器变化，文中只保证数量级；C9 的 Numba 示例需要额外安装 `numba`。

---

## C1 ufunc 的循环选择与 CPU 分派

### C1.1 ufunc 是一组"类型循环"

`np.add` 不是一个函数，而是一个**带若干类型循环（loops）的对象**。每个循环对应一组具体的输入输出 dtype：

```python
>>> import numpy as np
>>> (np.add.ntypes, np.add.nin, np.add.nout, np.add.identity)
(22, 2, 1, 0)
>>> np.add.types[:8]
['??->?', 'bb->b', 'BB->B', 'hh->h', 'HH->H', 'ii->i', 'II->I', 'll->l']
```

签名读法：`bb->b` 表示"两个 `int8` 进、一个 `int8` 出"；`??->?` 是布尔版。`nin/nout` 是输入输出个数，`identity` 是归约的单位元——这个属性决定了 `reduce` 在空数组上的行为：

```python
>>> (np.add.identity, np.multiply.identity, np.maximum.identity)
(0, 1, None)
```

`np.add` 的单位元是 0（空数组求和得 0），`np.multiply` 是 1，而 `np.maximum` 没有单位元（空数组求最大无定义，所以是 `None`）。

**"ufunc 调用"的完整过程**是：解析输入 dtype → 按提升规则选出目标类型 → 在该类型的循环表里找匹配的循环 → 按内存布局选一个具体的迭代内核 → 跑 C 循环。主章 1.3.4 讲的提升规则，在这里就是"选哪个循环"。

### C1.2 运行时 CPU 分派

NumPy 在编译时确定一个**基线**指令集，在运行时检测 CPU 支持哪些**分派**指令集，并为不同实现生成多个版本的内核：

```python
>>> from numpy._core import _multiarray_umath as mu
>>> mu.__cpu_baseline__, mu.__cpu_dispatch__
(['X86_V2'], ['X86_V3', 'X86_V4', 'AVX512_ICL', 'AVX512_SPR'])
>>> mu.__cpu_features__['AVX2']
True
```

这台机器基线是 `X86_V2`（SSE4.2 级别），编译时分派准备了 `X86_V3`（AVX2）、`X86_V4`（AVX-512）等版本，运行时检测到 CPU 支持 AVX2，于是启用 `X86_V3` 内核。官方入口是：

```
>>> np.show_runtime()
{'simd_extensions': {'baseline': ['X86_V2'],
                     'found': ['X86_V3'],
                     'not_found': ['X86_V4', 'AVX512_ICL', 'AVX512_SPR']}}
```

（实际输出还包含 Python 版本、平台、BLAS 等信息。）

> **注意**：`numpy._core._multiarray_umath` 是**私有模块**，字段名随时可能变。用它做实验、做诊断都可以，但不要写进生产代码。公开接口是 `np.show_runtime()`。

### C1.3 分派不等于更快

知道"我的机器启用了 AVX2"并不等于"我的代码快了 2 倍"。原因写在 C7：**大数组上的逐元素运算几乎都是内存带宽受限的**，指令宽度再翻倍，数据供不上也没用。分派在计算密集的循环（如 `np.exp`、`np.sin`）上收益明显，在 `a + b` 这种"每元素只做一次加法、却要搬 24 字节"的场景上收益有限。

> **实战建议**：不要为了"吃到 SIMD"去改写算法。先把算法、dtype、内存布局做对（主章 1.15 的顺序），SIMD 是编译器与运行时的责任。

---

## C2 数组协议：`__array_ufunc__` 与 `__array_function__`

主章 1.16 说"pandas 主动接管了 NumPy 调用"。这里把接管的方式写出来。

### C2.1 `__array_ufunc__`：接管逐元素运算

```python
>>> class Tracked:
...     def __init__(self, x):
...         self.x = np.asarray(x)
...     def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
...         print(f"  __array_ufunc__: {ufunc.__name__} (method={method})")
...         ins = [i.x if isinstance(i, Tracked) else i for i in inputs]
...         out = kwargs.get('out', None)
...         if out is not None:
...             kwargs['out'] = tuple(o.x if isinstance(o, Tracked) else o for o in out)
...         res = getattr(ufunc, method)(*ins, **kwargs)
...         if out is None:
...             return Tracked(res)
...         return out[0] if len(out) == 1 else out
...     def __repr__(self):
...         return f"Tracked({self.x.tolist()})"
>>> np.array([1, 2]) + Tracked([3, 4])
  __array_ufunc__: add (method=__call__)
Tracked([4, 6])
>>> np.sqrt(Tracked([4, 9]))
  __array_ufunc__: sqrt (method=__call__)
Tracked([2.0, 3.0])
```

要点三条：

1. **触发条件是 NumPy 的 ufunc 机制被调用**——只要有一个操作数是 ndarray（或显式调用 `np.add`），协议就生效。`method` 参数区分 `__call__` / `reduce` / `accumulate` / `at`，同一个方法要能处理这几种。
2. `out=` 会以**元组**形式传进来（`(array,)`），标准做法是把它转换后原样传给 ufunc，再返回 `out[0]`。
3. **左边不是 ndarray 时协议不会被触发**：
   ```python
   >>> Tracked([1, 2]) + 10
   TypeError: unsupported operand type(s) for +: 'Tracked' and 'int'
   ```
   因为 Python 先找 `Tracked.__add__`，找不到就找 `int.__radd__`，都不会走到 NumPy。要让自定义类型支持 `obj + 10`，得自己实现 `__add__`，或者**继承 `np.ndarray`**（子类会继承这套机制）。这是写库时最容易踩的一个坑。

### C2.2 `__array_function__`：接管高级函数

ufunc 协议管逐元素运算，函数级 API（`concatenate`、`mean`、`stack`……）由 NEP 18 的 `__array_function__` 接管：

```python
>>> class MyArray:
...     def __init__(self, x):
...         self.x = np.asarray(x)
...     def __array_function__(self, func, types, args, kwargs):
...         print(f"  __array_function__: {func.__name__} types={[t.__name__ for t in types]}")
...         if func is np.concatenate:
...             arrs = [a.x if isinstance(a, MyArray) else a for a in args[0]]
...             return MyArray(np.concatenate(arrs, **kwargs))
...         return NotImplemented
...     def __repr__(self):
...         return f"MyArray({self.x.tolist()})"
>>> np.concatenate([MyArray([1, 2]), MyArray([3, 4])])
  __array_function__: concatenate types=['MyArray']
MyArray([1, 2, 3, 4])
```

`types` 参数告诉你"这次调用牵涉到哪些实现该协议的类"——多类型混合时要由它们协商决定谁处理（通常按子类优先，未实现的一方返回 `NotImplemented`）。不处理的函数返回 `NotImplemented` 会得到一个明确的报错，而不是悄悄降级：

```python
>>> np.mean(MyArray([1, 2]))
  __array_function__: mean types=['MyArray']
TypeError: no implementation found for 'numpy.mean' on types that implement __array_function__: [<class 'MyArray'>]
```

> **设计意义**：这两个协议是 NumPy 从"唯一的数组库"变成"数组生态的接口层"的关键。cuPy、Dask、xarray、pandas 都是靠它们让 `np.xxx` 无缝作用在自己的对象上，并保留自己的类型与惰性求值语义。Array API 标准（NEP 47/56）把这套思路推广成跨库规范；`__array_namespace__` 是它的入口。

---

## C3 浮点求和：成对求和与顺序累加

主章 1.10.5 给了结论，这里给完整证据。三种求法：

- `x.sum()`：NumPy 用**成对求和**（pairwise / 分治：两两相加，层层合并），误差 O(log *n*)；
- `np.cumsum(x)[-1]`：`cumsum` 天然是顺序的（每个结果依赖前一个），等价于从左到右累加，误差 O(*n*)；
- `math.fsum(x)`：精确（内部用扩展精度累加器）。

```python
>>> import math
>>> x = np.full(1_000_000, 0.1)
>>> exact = math.fsum(x)
>>> np.sum(x), np.sum(x) - exact
(np.float64(100000.00000000003), np.float64(2.9103830456733704e-11))
>>> np.cumsum(x)[-1], np.cumsum(x)[-1] - exact
(np.float64(100000.00000133288), np.float64(1.3328826753422618e-06))
```

同一个数组，成对求和的误差比顺序累加小约 **45000 倍**。误差随规模的增长也不一样：

| *n* | 成对求和误差 | 顺序累加误差 |
|-----|-------------|-------------|
| 10³ | +1.421e-14 | −1.407e-12 |
| 10⁵ | +0.000e+00 | +1.885e-08 |
| 10⁶ | +2.910e-11 | +1.333e-06 |
| 10⁷ | +0.000e+00 | −1.610e-04 |

顺序误差随 *n* 线性增长，成对求和则在 0 与几个 1e-11 之间游走。但**成对求和仍然不精确**——它能减轻误差，不能消除：

```python
>>> y = np.array([1e16, 1.0, 1.0, 1.0, -1e16])
>>> np.sum(y)
np.float64(0.0)
>>> np.cumsum(y)[-1]
np.float64(0.0)
>>> math.fsum(y)
3.0
```

这里 `1e16 + 1.0` 就把 1.0 吞掉了，无论怎么分组都救不回来。**误差来自表示与量级差，不来自求和顺序。**

> **实战建议**：判断要不要上 `math.fsum`，看"数量级差是否巨大"而不是"元素多不多"。金额、长时间序列累加、有正负抵消的物理量，用 `fsum` 或先排序再求和（把小数排在前）；普通统计量用 `np.sum` 就够。

---

## C4 排序算法与稳定性

### C4.1 四种 kind

`np.sort` / `np.argsort` 的 `kind` 参数选择算法：`'quicksort'`（默认，实际是 introsort）、`'mergesort'`（稳定）、`'heapsort'`、`'stable'`（等价于 mergesort，语义更明确）。**只有 mergesort/stable 保证稳定性。**

用 20 万个只有 3 种取值的键来检验"并列项是否保持原顺序"：

| `kind` | 并列项保持原序 |
|--------|---------------|
| `quicksort` | **False** |
| `stable` | True |
| `heapsort` | **False** |
| `mergesort` | True |

小数组上 quicksort 会退化成插入排序，看起来"稳定"；元素一多就露出真面目。所以**不要用"跑一次看着对"来判断稳定性**。

> **⚠️ 陷阱**：`np.argsort` 默认不稳定。做"先按 A 排、并列时保持 B 的顺序"这类需求时，要么显式 `kind='stable'`，要么直接用 `np.lexsort`（多键排序，最后一个键是主键）：
>
> ```python
> >>> grp = np.array([2, 1, 2, 1]); score = np.array([10, 30, 20, 40])
> >>> np.lexsort((score, grp))          # 先按 grp，组内按 score
> array([1, 3, 0, 2])
> ```

### C4.2 sort 与 partition 的取舍

只要 top-k 时，`partition` 是 O(*n*)、`sort` 是 O(*n* log *n*)：

| 操作 | 200 万元素耗时 |
|------|---------------|
| `np.sort` | 14.75 ms |
| `np.partition` | 3.21 ms（快 4.6 倍） |

主章 1.10.3 的 `argpartition` 取 top-k 就是靠这个。元素越多、k 越小时优势越大。

---

## C5 类型提升矩阵与 dtype 扩展

### C5.1 完整提升矩阵

主章给了规则，这里给全表（`np.result_type`）：

|  | int8 | int32 | int64 | uint8 | uint64 | float32 | float64 | complex64 | bool |
|--|------|-------|-------|-------|--------|---------|---------|-----------|------|
| **int8** | int8 | int32 | int64 | int16 | float64 | float32 | float64 | complex64 | int8 |
| **int32** | int32 | int32 | int64 | int32 | float64 | float64 | float64 | complex128 | int32 |
| **int64** | int64 | int64 | int64 | int64 | float64 | float64 | float64 | complex128 | int64 |
| **uint8** | int16 | int32 | int64 | uint8 | uint64 | float32 | float64 | complex64 | uint8 |
| **uint64** | float64 | float64 | float64 | uint64 | uint64 | float64 | float64 | complex128 | uint64 |
| **float32** | float32 | float64 | float64 | float32 | float64 | float32 | float64 | complex64 | float32 |
| **float64** | float64 | float64 | float64 | float64 | float64 | float64 | float64 | complex128 | float64 |
| **complex64** | complex64 | complex128 | complex128 | complex64 | complex128 | complex64 | complex128 | complex64 | complex64 |
| **bool** | int8 | int32 | int64 | uint8 | uint64 | float32 | float64 | complex64 | bool |

三条要从表里读出来的结论：

- `uint64 + int64 → float64`（唯一一个"两个整数变浮点"的格子），大整数会掉精度；
- `int8 + uint8 → int16`（整数之间会升宽以容纳两边的范围）；
- `bool` 与任何数值类型混合都会**被提升**，不参与"弱类型"待遇。

### C5.2 NEP 50 的"弱标量"

Python 标量不参与上表，它们跟随数组：

```python
>>> np.array([1], dtype=np.float32) + 1.5
array([2.5], dtype=float32)
>>> np.array([1], dtype=np.int8) + 1
array([2], dtype=int8)
>>> np.uint8(200) + 100
RuntimeWarning: overflow encountered in scalar add
np.uint8(44)
```

最后一行值得停一下：`np.uint8(200)` 是**NumPy 标量**（不是 Python 标量），`100` 是 Python 标量。按 NEP 50，Python 标量弱、跟随 `uint8`，于是 300 回绕成 44。**"弱"是相对 Python 标量而言；两个 NumPy 值参与运算时仍按上表提升。**

### C5.3 dtype 扩展

NumPy 2.0 起 dtype 本身是对象，`np.dtypes` 模块列出全部内置类型（`Int8DType`、`Float64DType`、`StringDType`……）。新增的 `StringDType` 是**变长**字符串，绕开了 `'<U4'` 的定宽截断：

```python
>>> S = np.dtypes.StringDType()
>>> arr = np.array(['a', 'bb', 'ccc'], dtype=S)
>>> arr
array(['a', 'bb', 'ccc'], dtype=StringDType())
>>> (arr.dtype, arr.dtype.itemsize, arr.nbytes)
(StringDType(), 16, 48)
```

三个字符串长度不同、彼此不截断（对照主章 1.3.6 的 `'<U3'` 会截成 `'abc'`）。`itemsize=16` 是**对象头大小**，真正的字符数据另行存放，所以 `nbytes` 不再是"元素数 × itemsize"。配套的 `np.strings` 模块提供向量化字符串操作。

NEP 42 把 dtype 做成了可扩展点：第三方库能注册自己的 dtype 并参与提升规则（`np.dtypes.register_dlpack_dtype` 就是一个入口）。这是"NumPy 作为协议层"在类型系统上的体现。

---

## C6 BLAS 后端、`@` 与 `einsum` 的路径

### C6.1 `@` 走的是 BLAS

```python
>>> cfg = np.show_config(mode='dicts')
>>> cfg['Build Dependencies']['blas']['name'], cfg['Build Dependencies']['blas']['version']
('scipy-openblas', '0.3.34.106.0')
>>> cfg['Build Dependencies']['lapack']['name']
'scipy-openblas'
```

`A @ B` 最终调用 BLAS 的 GEMM。吞吐随规模上升，因为 BLAS 会做分块（cache blocking）：

| n | 耗时 | 吞吐 |
|---|------|------|
| 500 | 1.65 ms | 151 GFLOPS |
| 1000 | 6.91 ms | 290 GFLOPS |
| 2000 | 33.22 ms | 482 GFLOPS |

矩阵越大、数据复用越充分，越接近机器的峰值浮点能力。**这解释了两件事**：手写三重循环毫无竞争力（差几个数量级），以及"矩阵乘不是内存受限的"（对照 C7）。

### C6.2 `einsum` 必须 `optimize`

`einsum` 的默认行为是"按你写的顺序收缩"，不做路径优化。三个矩阵连乘时，顺序决定中间结果大小：

```
Complete contraction:  ij,jk,kl->il
     Naive scaling:  4
 Optimized scaling:  3
  Naive FLOP count:  4.800e+09
  Optimized FLOP count:  3.200e+07
  Theoretical speedup:  150.000
```

实测代价比理论更夸张：

| 写法 | 耗时 |
|------|------|
| `einsum(..., optimize=False)` | 772.974 ms |
| `einsum(..., optimize=True)` | 3.855 ms（快约 200 倍） |
| 链式 `(A @ B) @ C` | 0.266 ms（再快 14 倍） |

三档差距是三件事：`optimize=False` 先算出一个 200×200×200 的巨大中间量；`optimize=True` 把它压成 200×200；而链式 `@` 直接交给 BLAS 做两次 GEMM，比通用收缩内核更快。

> **实战建议**：`einsum` 的可读性优势来自"公式即代码"，但**默认它不优化**。链式矩阵乘用 `@`，通用收缩（转置、对角、双向求和混合）用 `einsum(..., optimize=True)`。`np.einsum_path` 可以先看它选了哪条路径再决定。

---

## C7 迭代器、内存带宽与 roofline

### C7.1 nditer：NumPy 内部的统一迭代器

所有 ufunc 与归约都由 `nditer` 驱动，它把"任意 shape、任意 strides、任意 dtype"的数组摊平成一个线性遍历，并负责广播：

```python
>>> a = np.arange(6).reshape(2, 3)
>>> it = np.nditer(a, flags=['multi_index'])
>>> for v in it:
...     print(f"  multi_index={it.multi_index}  value={v}")
  multi_index=(0, 0)  value=0
  multi_index=(0, 1)  value=1
  multi_index=(0, 2)  value=2
  multi_index=(1, 0)  value=3
  multi_index=(1, 1)  value=4
  multi_index=(1, 2)  value=5
```

广播就是靠 0 步长在同一个迭代器里实现的——`(4,)` 不用复制就能喂给 `(3, 4)` 的输出（主章 1.7.5 的零步长视图，`ds-01b` M3.3 的 stride=0）。

`flags=['external_loop', 'buffered']` 让迭代器一次交出一整段连续数据（"外部循环"），这正是 SIMD 内核能逐块处理的原因。主章 1.13 的 `where=`、`out=` 也都是通过迭代器的操作数机制传递的。

### C7.2 实测内存带宽

预热过的数组（页已触碰），搬运吞吐：

| 操作 | 耗时 | 等效带宽 | 搬运量 |
|------|------|---------|--------|
| `copyto(dst, src)` | 36.2 ms | 22.1 GB/s | 800 MB（读+写） |
| `add(src, other, out=dst)` | 43.6 ms | 27.5 GB/s | 1200 MB（读+读+写） |

这台机器（WSL2 虚拟机）的实测带宽约 **25–30 GB/s**。这是逐元素运算的物理上限。

### C7.3 roofline：为什么 matmul 快而 add 慢

把 C6 与 C7.2 的数字放在一起，就得到 roofline 模型的实证：

| 操作 | 计算强度（FLOP/字节） | 达到的性能 |
|------|---------------------|-----------|
| `a + b`（n=5000 万） | ≈ 1/24 = 0.042 | ≈ 1.1 GFLOPS（受带宽限制） |
| `A @ B`（n=2000） | ≈ 2n³/(3n²·8) ≈ 167 | 482 GFLOPS（受计算限制） |

计算强度差 4000 倍，性能差 400 倍。**`a + b` 的瓶颈是"把数据搬进 CPU"，`A @ B` 的瓶颈是"浮点单元跑多快"**。这就是 roofline：一个操作能跑多快，由"计算强度"和两条硬件上限（峰值算力、峰值带宽）共同决定。

对日常工作的直接含义：逐元素运算在 NumPy 里已经贴着硬件上限了，**再优化算法也没用**——唯一的出路是减少数据搬运（用 `out=` 复用缓冲、用更小的 dtype、分块让中间结果留在缓存里）。而矩阵运算还有 BLAS 帮你贴着算力上限。主章 1.15 的三条纪律，到这里有了物理依据。

### C7.4 缺页成本：把 M6 的悬念收掉

`ds-01b` M6.2 里 `np.ones(400MB)` 要 60 ms，而这里 `fill` 只要 25 ms。差别是**缺页**：

| 写法 | 耗时 | 等效带宽 |
|------|------|---------|
| 新分配 `np.ones(n)` | 59.6 ms | 6.71 GB/s（含缺页） |
| 预热后 `dst.fill(1.0)` | 24.8 ms | 16.15 GB/s（纯写入） |
| 差值（缺页成本） | 34.9 ms | — |

**第一次触碰 400 MB 要付约 35 ms 的缺页代价**，比写入本身还贵。这解释了为什么"复用缓冲区"在长循环里能省大量时间——主章 1.15.2 的 `out=` 省内存，顺带也省了反复分配带来的缺页。

---

## C8 随机数内核：BitGenerator 与 SeedSequence

### C8.1 五种 BitGenerator 的速度

| 内核 | 生成 100 万随机数 | 备注 |
|------|------------------|------|
| `SFC64` | 1.465 ms | 最快，非加密安全 |
| `PCG64DXSM` | 1.616 ms | PCG64 的加强版，正在成为默认候选 |
| `PCG64` | 1.879 ms | `default_rng()` 当前默认 |
| `MT19937` | 2.923 ms | 经典 Mersenne Twister，旧接口的内核 |
| `Philox` | 3.050 ms | 支持并行跳跃，适合大规模仿真 |

速度差不到 2 倍，所以**默认选 PCG64 是对的**：统计性质与流并行性比那点速度重要。需要长周期与可跳跃子流（GPU 仿真、上千个并行实验）时才考虑 Philox。

### C8.2 状态可以保存与恢复

```python
>>> rng = np.random.default_rng(42)
>>> state = rng.bit_generator.state
>>> first = rng.random(3)
>>> rng.bit_generator.state = state
>>> np.array_equal(rng.random(3), first)
True
```

把 `state` 存下来就能在任意时刻冻结/恢复随机流——做检查点、断点续跑、并行分片时比"换种子"更精确。状态结构是 `{'bit_generator': str, 'state': dict, 'has_uint32': int, 'uinteger': int}`。

### C8.3 SeedSequence 内部

```python
>>> ss = np.random.SeedSequence(2026)
>>> (ss.entropy, ss.spawn_key, ss.n_children_spawned)
(2026, (), 0)
>>> len(ss.pool)
4
```

`entropy` 是你给的种子（也可以是熵源列表），`pool` 是哈希扩展出的内部状态池（4 个 32 位字），`spawn_key` 是这棵树里的路径，`n_children_spawned` 是已派生的子代数。主章 1.13.2 那个"`spawn` 会推进计数"的现象，来源就是这里的 `n_children_spawned`。

> **⚠️ 陷阱**：**相邻整数种子不保证独立**。`default_rng(1)` 与 `default_rng(2)` 的输出看起来毫不相关，但这不能证明统计独立——旧式"给每个实验编个号当种子"的做法出过真实事故。要独立性，用 `SeedSequence.spawn` 从同一个父熵源派生，让库负责扩展。

---

## C9 何时离开 NumPy：Numba / Cython / 专用库

有些计算**无法向量化**——最典型的是带顺序依赖的递推。指数移动平均（EMA）就是例子：

$$y_i = \alpha x_i + (1-\alpha) y_{i-1}$$

每个 $y_i$ 依赖 $y_{i-1}$，不能拆成独立元素，NumPy 没有对应原语。三种实现（200 万元素，α = 0.1）：

| 实现 | 耗时 | 相对 Python |
|------|------|------------|
| 纯 Python 循环 | 298.61 ms | 1× |
| `numba.njit` | 2.91 ms | **102.5×** |
| `scipy.signal.lfilter` | 6.21 ms | 48.1× |

三种实现的结果**逐位一致**（`np.allclose(..., rtol=1e-12)` 为 `True`，lfilter 的最大差是 0.0）。

这张表给出的次序很清楚：

1. **先找专用库**。`lfilter` 一行、比手写快 48 倍、久经考验，是 IIR 滤波的标准答案。数值计算的正确顺序永远是"标准库 → 领域库 → 自己写"。
2. **再考虑 JIT**。没有现成库时，Numba 只加一个装饰器就能拿到接近 C 的速度，且不需要改算法结构。
3. **最后才是 Cython / C 扩展**。需要发布二进制包、需要精细控制内存时才上，成本最高（编译链、平台 wheel）。

```python
from numba import njit

@njit
def ema(x, alpha):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc = alpha * x[i] + (1.0 - alpha) * acc
        y[i] = acc
    return y
```

**决策表**：

| 情形 | 选择 |
|------|------|
| 逐元素、归约、矩阵乘 | 留在 NumPy（已贴着硬件上限） |
| 表格语义（分组、连接、缺失值） | pandas（`ds-02`） |
| 有标准算法（滤波、优化、统计分布） | SciPy（`ds-04`） |
| 顺序依赖 / 复杂控制流 / 自定义内核 | Numba |
| 需要发布 C 扩展、要精确控制内存 | Cython / C API（卷 1 第 15 章） |
| 需要自动微分 / GPU | PyTorch、JAX（卷 4） |

> **一条铁律**：离开 NumPy 之前，先确认你已经做完了主章 1.15 的前三步（算法、dtype、向量化）。**给一个本不该存在的循环上 Numba，是最常见的南辕北辙。**

---

## 本文件小结

| 主题 | 核心结论 |
|------|---------|
| ufunc | 是一组类型循环（`np.add.ntypes = 22`），调用过程 = 解析 dtype → 选循环 → 选迭代内核 |
| CPU 分派 | 基线 + 运行时分派（本机基线 X86_V2，启用 X86_V3/AVX2）；公开入口 `np.show_runtime()` |
| 数组协议 | `__array_ufunc__` 管逐元素、`__array_function__` 管函数级；左边不是 ndarray 时不触发 |
| 浮点求和 | 成对求和误差 O(log *n*)、顺序累加 O(*n*)，实测差 45000 倍；但量级差导致的吞没无解 |
| 排序 | 只有 mergesort/stable 稳定；小数组看不出 quicksort 不稳定；partition 比 sort 快 4.6 倍 |
| 类型提升 | 全表可查；`uint64+int64 → float64` 是唯一"整数变浮点"；NEP 50 弱标量只对 Python 标量生效 |
| dtype 扩展 | `np.dtypes.StringDType` 变长字符串；NEP 42 让第三方 dtype 参与提升 |
| BLAS | `@` 走 GEMM，2000³ 达 482 GFLOPS；`einsum` 默认不优化，`optimize=True` 快约 200 倍 |
| 迭代器与带宽 | 广播靠零步长迭代；实测带宽 25–30 GB/s；缺页成本可达写入本身的 1.5 倍 |
| roofline | `a + b` 计算强度 0.042、受带宽限；`A @ B` 强度 167、受算力限 |
| 随机数内核 | PCG64 是默认且合理；状态可保存恢复；相邻整数种子不保证独立，用 `spawn` |
| 离开 NumPy | 先专用库（lfilter 48×），再 Numba（102×），最后 Cython；顺序依赖是典型信号 |

**回到主章**：C1 → 1.9；C2 → 1.16；C3 → 1.10.5；C4 → 1.10.3；C5 → 1.3；C6 → 1.12；C7 → 1.7.5、1.15；C8 → 1.13；C9 → 1.15.5。

**两本深水文件的分工**：`ds-01b` 讲"数据放在哪、谁拥有它"，本文件讲"算的时候发生了什么"。两者在 C7.4（缺页）与 M6.2（分配 ≠ 触碰）处交汇。

---

## 参考文献

1. Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020). *Array programming with NumPy.* Nature, 585(7825), 357–362. DOI: [10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2) —— ufunc、数组协议、生态定位的综述。
2. van der Walt, S., Colbert, S. C., & Varoquaux, G. (2011). *The NumPy Array: A Structure for Efficient Numerical Computation.* Computing in Science & Engineering, 13(2), 22–30. DOI: [10.1109/MCSE.2011.37](https://doi.org/10.1109/MCSE.2011.37) —— ufunc 与迭代器设计。
3. [NEP 13 — A mechanism for overriding Ufuncs](https://numpy.org/neps/nep-0013-ufunc-overrides.html)、[NEP 18 — A dispatch mechanism for NumPy's high level array functions](https://numpy.org/neps/nep-0018-array-function-protocol.html) —— C2 的规范。
4. [NEP 50 — Promotion rules for Python scalars](https://numpy.org/neps/nep-0050-scalar-promotion.html)、[NEP 42 — New and extensible DTypes](https://numpy.org/neps/nep-0042-new-dtypes.html) —— C5 的规范。
5. Goldberg, D. (1991). *What Every Computer Scientist Should Know About Floating-Point Arithmetic.* ACM Computing Surveys, 23(1), 5–48. DOI: [10.1145/103162.103163](https://doi.org/10.1145/103162.103163) —— C3 的背景。
6. O'Neill, M. E. (2014). *PCG: A Family of Simple Fast Space-Efficient Statistically Good Algorithms for Random Number Generation.* Harvey Mudd College Technical Report HMC-CS-2014-0905. [pcg-random.org/paper.html](https://www.pcg-random.org/paper.html) —— C8 的内核出处。
7. Lam, S. K., Pitrou, A., & Seibert, S. (2015). *Numba: a LLVM-based Python JIT compiler.* Proc. Second Workshop on the LLVM Compiler Infrastructure in HPC. DOI: [10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162) —— C9。
8. [NEP 47 — Adopting the array API standard](https://numpy.org/neps/nep-0047-array-api-standard.html)、[NEP 56 — Array API standard support in NumPy's main namespace](https://numpy.org/neps/nep-0056-array-api-main-namespace.html) —— C2 末尾提到的跨库规范。
9. [NumPy 文档：Universal functions (ufunc) basics](https://numpy.org/doc/stable/user/basics.ufuncs.html)、[Standard array subclasses](https://numpy.org/doc/stable/reference/arrays.classes.html)、[CPU/SIMD optimizations](https://numpy.org/doc/stable/reference/simd/index.html) —— C1、C2 的官方说明。
