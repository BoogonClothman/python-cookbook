# 附录 A 线性代数速查

> **定位**：这是卷 2 的线性代数**急救卡**。`ds-00` 0.2 负责从零教（每个概念配代码与自测），本附录负责**当场查**——一个概念一张卡，给出「什么时候用 / 函数入口 / 最短可跑代码 / 坑」。
>
> **用法**：不要通读。遇到具体问题时按下面的索引翻到对应卡片；卡片末尾的 `§` 是回链，指向推导与实测证据所在的位置。
>
> **符号**：$A$ 是 $m \times n$ 矩阵，$x$ 是长度为 $n$ 的向量，$b$ 是长度为 $m$ 的向量。**报规模时一律写 "$m \times n$"**，两个数都要给。$\epsilon = 2.22\times10^{-16}$ 是双精度机器精度，`cond` 是条件数。
>
> **验证环境**：Python 3.14.4 + NumPy 2.5.3 + SciPy 1.18.1。本附录所有代码都在该环境跑过。

## 卡片索引

| 我想做的事 | 去 |
|-----------|-----|
| 判断数组的形状、维度、轴 | A.1 |
| 逐元素运算、广播为什么报错 | A.2 |
| 算长度、距离、相似度 | A.3 |
| 加权求和、批量乘法 | A.4 |
| 转置、单位阵、求逆 | A.5 |
| 判断方程组有没有解 | A.6 |
| 选哪种矩阵分解 | A.7 |
| 解出来不知道准不准 | A.8 |
| 判断矩阵的定性（碗还是鞍） | A.9 |
| 求导、给优化器梯度 | A.10 |
| 方程数不等于未知数 | A.11 |
| 未知数上万、矩阵几乎全零 | A.12 |
| 该用 NumPy 还是 SciPy | A.13 |
| 报错了 / 结果不对，先看这里 | A.14 |
| 符号不认识 | A.15 |

---

## A.1 形状语言：维度就是方括号的嵌套层数

```python
import numpy as np
a = np.array(85)                    # 0 维：标量      a.ndim=0, a.shape=()
v = np.array([85, 90, 78])          # 1 维：向量      v.ndim=1, v.shape=(3,)
M = np.array([[85, 90], [92, 88]])  # 2 维：矩阵      M.ndim=2, M.shape=(2, 2)
T = np.zeros((2, 3, 4))             # 3 维：张量      T.ndim=3, T.shape=(2, 3, 4)
```

| 操作 | 含义 |
|------|------|
| `a.shape` | 各维长度，**永远先看它** |
| `a.ndim` | 维数 = `len(a.shape)` |
| `a.size` | 元素总数 = `prod(a.shape)` |
| `axis=0` | 沿"第 0 维"聚合（行方向压缩，**结果长度 = 列数**） |
| `axis=1` | 沿第 1 维聚合（结果长度 = 行数） |
| `keepdims=True` | 保留被压缩的那一维（长度变 1），便于后续广播 |

**轴的记忆法**：`axis=k` 表示"把第 $k$ 维消掉"。所以 `M.sum(axis=0)` 得到的是**逐列**的和，长度等于列数。§`ds-00` 0.2.1

---

## A.2 逐元素运算与广播：三条规则

```python
A * B            # 逐元素乘（形状相同，或能广播）
A @ B            # 矩阵乘法（不是逐元素！）
A / B, A ** 2    # 逐元素
```

**广播三规则**（从右往左逐维比较）：

1. 维数不同时，在**左边**补 1；
2. 某一维长度为 1 时，沿该维复制；
3. 长度既不相等又都不是 1 → `ValueError`。

```python
(3, 1) 与 (1, 4)  ->  (3, 4)         # 两维都广播
(3, 4) 与 (4,)    ->  (3, 4)         # 右边补 1
(3, 4) 与 (3,)    ->  ValueError     # 右对齐：4 vs 3
```

> **⚠️ 坑**：报错信息里的形状是**右对齐比较**的结果，与实际书写顺序不同。把两个 shape 写进注释再核对。§`ds-00` 0.2.2、`ds-01` 1.7

---

## A.3 范数与距离

```python
np.linalg.norm(v)                    # L2 范数（默认）
np.linalg.norm(v, 1)                 # L1：绝对值之和
np.linalg.norm(v, np.inf)            # L∞：最大绝对值
np.linalg.norm(A)                    # 矩阵的谱范数（最大奇异值）
np.linalg.norm(A, "fro")             # Frobenius：所有元素平方和的根
```

**距离**（两点之间）：

| 名称 | 公式 | NumPy / SciPy |
|------|------|--------------|
| 欧氏 | $\sqrt{\sum (a_i-b_i)^2}$ | `np.linalg.norm(a-b)` |
| 曼哈顿 | $\sum\lvert a_i-b_i\rvert$ | `np.linalg.norm(a-b, 1)` |
| 余弦距离 | $1 - \frac{a\cdot b}{\lVert a\rVert\lVert b\rVert}$ | `scipy.spatial.distance.cosine` |
| 马氏 | 考虑协方差的距离 | `scipy.spatial.distance.mahalanobis` |

批量距离用 **`scipy.spatial.distance`**：`cdist(A, B)` 给两组点之间的 $m \times n$ 距离矩阵，`pdist(X)` 给一组点内部的压缩距离（$n(n-1)/2$ 个值，用 `squareform` 展开）。**点数上万时不要算距离矩阵，用 `cKDTree`。** §`ds-00` 0.2.3、`ds-05` 5.12.1

---

## A.4 点积与矩阵乘法

```python
a @ b                                # 点积（1 维时就是内积）
A @ B                                # 矩阵乘法：(m,n) @ (n,k) -> (m,k)
A @ v                                # (m,n) @ (n,) -> (m,)
M.sum(axis=1)                        # 逐行和（等价于 M @ ones(n)）
```

**记忆口诀**：`(m, n) @ (n, k) → (m, k)`，**内维相等，外维成形**。

一维数组参与乘法时，NumPy 把它当成"临时补 1 再加回"，所以 `(m,n) @ (n,)` 的结果是 `(m,)` 而不是 `(m,1)`。需要列向量就显式 `reshape(-1, 1)`。

| 任务 | 写法 |
|------|------|
| 加权总分 | `scores @ weights` |
| 批量点积（每行与向量） | `M @ v` |
| 外积 | `np.outer(u, v)` 或 `u[:, None] * v[None, :]` |
| 批量矩阵乘 | `np.einsum("ij,jk->ik", A, B)` |

> **⚠️ 坑**：`*` 与 `@` 混淆**不报错**，只会静默给出错误结果（`*` 是逐元素，形状不变）。这是最难发现的一类错误。§`ds-00` 0.2.5

---

## A.5 转置、单位阵、逆矩阵

```python
A.T                                  # 转置（1 维数组的 .T 是空操作！）
np.eye(3)                            # 3×3 单位阵
np.linalg.inv(A)                     # 逆矩阵 —— 解方程时不要用，见 A.8
```

**一维数组没有行列之分**，`v.T` 原样返回。要列方向用 `v.reshape(-1, 1)`。

**解 $Ax=b$ 永远不要写 `inv(A) @ b`**（§`ds-05` 5.2.1）：

| 做法 | 耗时（相对） | 残差（cond=1e12 时） |
|------|------------|-------------------|
| `la.solve(A, b)` | 1.0 | 2.4e-04 |
| `la.inv(A) @ b` | **1.8×** | **1.6e+06** |

慢 1.8 倍，残差大 **10 个数量级**。需要伪逆用 `np.linalg.pinv`（A.11）。

---

## A.6 行列式、秩与可解性

```python
np.linalg.det(A)                     # 行列式
np.linalg.matrix_rank(A)             # 秩（用默认容差，见下面的坑）
np.linalg.matrix_rank(A, tol=1e-10)  # 显式容差
```

| 情形 | 秩条件 | 解的个数 | 入口 |
|------|--------|---------|------|
| 恰定满秩 | $\mathrm{rank}(A) = n$ | 唯一解 | `la.solve` |
| 欠定（$m < n$） | — | 无穷多解 | `la.lstsq`（给最小范数解） |
| 超定（$m > n$） | — | 一般无精确解 | `la.lstsq`（最小二乘解） |
| 秩亏 | $\mathrm{rank}(A) < n$ | 无穷多解 | `la.lstsq` + 检查 `rank` |

```python
np.linalg.solve(np.array([[1., 2.], [2., 4.]]), [3., 6.])
# LinAlgError: Singular matrix          ← 奇异矩阵直接拒绝
np.linalg.lstsq(np.array([[1., 2.], [2., 4.]]), [3., 6.], rcond=None)[0]
# array([0.6, 1.2])                     ← 最小范数解
```

> **⚠️ 坑一：行列式小不等于病态。** `np.diag([1e-8]*3)` 的 `det` 是 $10^{-24}$，而 `cond` 是 **1.0**（完全良态）。判断"解可不可信"看条件数（A.8），不看行列式。§`ds-00` 0.2.8
>
> **⚠️ 坑二：秩在浮点里不是良定义的整数。** `matrix_rank` 的默认容差是 $\max(m,n)\cdot\epsilon\cdot\sigma_1$。实测一个矩阵的容差是 $5.92\times10^{-14}$ 而最小奇异值是 $7.48\times10^{-14}$——**只差 26%，判定成了掷硬币**。凡是"秩决定下一步"的逻辑，都要显式给 `tol` 并说明理由。§`ds-05` 5.2.4

---

## A.7 矩阵分解：四种拆法各答一个问题

| 分解 | 数学 | 回答什么 | 前提 | NumPy | SciPy |
|------|------|---------|------|-------|-------|
| LU | $A = PLU$ | 一般方阵求解 | 需要选主元 | 无 | `la.lu` / `la.lu_factor` |
| Cholesky | $A = LL^{\top}$ | 对称正定系统（快一半） | **对称正定** | `np.linalg.cholesky` | `la.cholesky` / `la.cho_factor` |
| QR | $A = QR$ | 最小二乘、正交化 | 任何矩阵 | `np.linalg.qr` | `la.qr` |
| SVD | $A = U\Sigma V^{\top}$ | 秩、条件数、伪逆、降维 | 任何矩阵 | `np.linalg.svd` | `la.svd` |

```python
Q, R = np.linalg.qr(A, mode="reduced")      # numpy：只留前 n 列 Q（scipy 里叫 "economic"）
L = np.linalg.cholesky(S)                   # ⚠️ numpy 默认【下】三角；scipy 默认【上】三角，见 A.13
U, s, Vt = np.linalg.svd(A)                 # s 是奇异值（降序）
P, L, U = la.lu(A)                          # 满足 P @ L @ U == A
```

> **⚠️ 坑**：`np.linalg.qr` 的合法 `mode` 是 `'reduced'` / `'complete'` / `'r'` / `'raw'`，而 `scipy.linalg.qr` 用的是 `'full'` / `'economic'`。更糟的是 **numpy 对非法 mode 不报错**——`np.linalg.qr(A, mode="economic")` 会静默返回**一个**数组（约化后的 Q）而不是 `(Q, R)`，于是 `Q, R = ...` 报的是一句令人费解的 `too many values to unpack`。

**SVD 一次给出四个基本子空间**（$m \times n$、秩 $r$）：$U$ 的前 $r$ 列是列空间、后 $m-r$ 列是左零空间；$V$ 的前 $r$ 列是行空间、后 $n-r$ 列是零空间。且 $\lVert Av_i\rVert = \sigma_i$。

**Cholesky 是最好的诊断器**：它只对对称正定矩阵成立，报错就是结论。

```python
>>> la.cholesky(np.array([[1., 2.], [2., 1.]]))
LinAlgError: Internal potrf return info = [2] for slices [0].
```

`potrf` 是 LAPACK 例程名，`info=[2]` 表示"第 2 个主元非正"。**看到这个报错该修的是模型前提，不是换求解器。** §`ds-00` 0.2.9、`ds-05` 5.2.4、`ds-05b` S2

---

## A.8 条件数：解还剩几位可信

```python
cond = np.linalg.cond(A)             # ⚠️ scipy.linalg 没有 cond！
```

**读法一句话**：$\log_{10}\mathrm{cond}$ **约等于求解过程中丢掉的十进制位数**。双精度有约 16 位（`np.finfo(float).precision` 给 15），所以

$$\text{还剩几位} \approx 15 - \log_{10}\mathrm{cond}(A)$$

| $\mathrm{cond}$ | 还剩 | 实战含义 |
|-----------------|------|---------|
| $10^{2}$ | 13 位 | 完全放心 |
| $10^{6}$ | 9 位 | 正常 |
| $10^{10}$ | 5 位 | **该警觉** |
| $10^{13}$ | 2 位 | 只能给量级 |
| $\ge 10^{16}$ | 0 位 | 结果由舍入误差决定 |

**体检模板**（照抄）：

```python
def solve_checked(A, b, name="A"):
    """解 Ax=b 并给出可信度诊断。"""
    from scipy import linalg as la
    A = np.asarray(A, dtype=float); b = np.asarray(b, dtype=float)
    cond = np.linalg.cond(A)
    digits = np.finfo(float).precision - np.log10(max(cond, 1.0))
    x = la.solve(A, b)
    res = np.abs(A @ x - b).max()
    brel = res / max(np.abs(b).max(), 1.0)
    if cond > 1e10:
        print(f"[{name}] cond={cond:.1e}，只剩 {digits:.1f} 位；"
              f"相对误差上界 ≈ {cond * brel:.1e}")
    return x, {"cond": cond, "digits_left": digits, "residual": res}
```

**两条必须记住的事实**：

1. **残差小 ≠ 误差小。** 有严格不等式

$$\frac{\lVert \hat{x} - x \rVert}{\lVert x \rVert} \le \mathrm{cond}(A)\cdot\frac{\lVert b - A\hat{x} \rVert}{\lVert b \rVert}$$

   实测 Hilbert $n = 12$：$\mathrm{cond} = 1.8\times10^{16}$、**误差 0.39、残差 4.4e-16**，误差/残差 ≈ cond。

2. **`la.solve` 只在 $\mathrm{rcond} < \epsilon$（$\mathrm{cond}\gtrsim5\times10^{15}$）时才警告。** $\mathrm{cond}$ 在 $10^{6}$–$10^{15}$ 之间是**一整片静默失准区**——指望警告兜底等于放弃了绝大多数真实病态问题。§`ds-05` 5.2.3、`ds-05b` S1.4

---

## A.9 特征值与二次型：碗还是鞍

```python
w, V = np.linalg.eigh(F)             # 对称矩阵专用：实数特征值、正交特征向量、按升序
w = np.linalg.eigvalsh(F)            # 只要特征值
w, V = np.linalg.eig(G)              # 一般矩阵（结果可能是复数）
```

> **⚠️ 坑**：数据科学里的协方差矩阵、Hessian、图拉普拉斯**都是对称的**，一律用 `eigh`/`eigvalsh`——更快，且保证实数与正交。§`ds-00` 0.2.10

**二次型 $x^{\top}Ax$ 的定性判据**（$A$ 对称）：

| 特征值符号 | $x^{\top}Ax$ | 称 | 曲面 | 可用方法 |
|-----------|-------------|----|------|---------|
| 全正 | 恒 $>0$ | 正定 | 碗，唯一最小 | Cholesky、共轭梯度 |
| 全负 | 恒 $<0$ | 负定 | 倒扣碗 | 取负后当正定 |
| 有正有负 | 可正可负 | 不定 | **鞍** | 换方法 |

```python
F = np.array([[2., 1.], [1., 2.]]); np.linalg.eigvalsh(F)
# array([1., 3.])          → 全正，碗形
G = np.array([[2., 3.], [3., 2.]]); np.linalg.eigvalsh(G)
# array([-1.,  5.])         → 不定，鞍形：任何从原点出发的优化器都会立刻"收敛"
```

**对称正定时条件数有解析式**：$\mathrm{cond}(A) = \lambda_{\max}/\lambda_{\min}$。一般矩阵用 $\sigma_{\max}/\sigma_{\min}$。§`ds-00` 0.2.10

---

## A.10 导数、梯度、雅可比、Hessian

| 对象 | 数学 | 代码 | 回答什么 |
|------|------|------|---------|
| 梯度 $\nabla f$ | 一阶导（多输入单输出） | 解析式或 `approx_fprime` | 往哪走 |
| 雅可比 $J$ | 一阶导（多输入多输出） | 解析式或逐列差分 | 小扰动怎么传播 |
| Hessian $H$ | 二阶导（对称） | 解析式或差分 | 谷底还是鞍点 |

```python
from scipy.optimize import approx_fprime, check_grad

grad = approx_fprime(x0, f, epsilon=1e-6)     # 差分梯度（省事但有精度上限）
err = check_grad(f, grad_f, x0)               # 核对解析梯度，>1e-2 说明写错了
```

**中心差分**：

```python
h = 1e-6                                      # 最优步长 ≈ ε^(1/3) ≈ 6e-6
g_i = (f(x + h*e_i) - f(x - h*e_i)) / (2*h)
```

**差分步长不是越小越好**（实测 $f = e^x\sin x$ 在 $x=1$，真导数 3.756049）：

| $h$ | $10^{-2}$ | $10^{-6}$ | $10^{-10}$ | $10^{-14}$ |
|-----|-----------|-----------|------------|------------|
| 误差 | 2.7e-05 | **1.05e-10** | 4.2e-07 | 1.87e-02 |

**U 形**：$h$ 大时截断误差 $\propto h^2$ 占优，$h$ 小时舍入误差 $\propto\epsilon/h$ 占优。

> **实战建议**：**能写解析梯度就必须写。** 实测在 Rosenbrock 上 `nfev` 从 117 降到 39，精度提高 6 个数量级（$n=100$ 时差分成本是解析的 101 倍）。§`ds-00` 0.2.11、`ds-05` 5.4.2、`ds-05b` S4.6

---

## A.11 最小二乘与伪逆

```python
from scipy import linalg as la
from scipy.optimize import lsq_linear, nnls

x, residues, rank, sv = la.lstsq(A, b)        # ⚠️ 普通 4 元组，没有 .x/.rank/.s
x, rnorm = nnls(A, b)                         # 系数非负
res = lsq_linear(A, b, bounds=(lb, ub))       # 任意上下界，res.x 有命名属性
x = np.linalg.pinv(A) @ b                     # 伪逆（矩阵形式）
```

**`la.lstsq` 返回值的两种陷阱**（§`ds-05` 5.2.5）：

| 情形 | `residues` |
|------|-----------|
| $m>n$ 满秩、`b` 一维 | **0 维数组**（`res[0]` 会 `IndexError`），用 `float(res)` |
| 秩亏（`gelsd`/`gelss`） | **`nan`**（不是报错！`if residues > tol` 会静默失效） |
| `gelsy` 或 $m\le n$ | 空数组 `(0,)` |

**先看 `rank`，再看 `residues`。**

> **⚠️ 头号禁忌：永远不要用正规方程。** $\mathrm{cond}(A^{\top}A) = \mathrm{cond}(A)^2$。实测在 $\mathrm{cond}(A) = 10^{8}$ 时，`lstsq` 的误差是 $4.7\times10^{-11}$、正规方程是 **0.299**——**差 64 亿倍**。
>
> **病态时加岭正则化比换算法有效**：
> ```python
> lam = 1e-4                                  # 实测把系数误差降到 1/445，残差只涨 4.7%
> x = np.linalg.solve(A.T @ A + lam*np.eye(A.shape[1]), A.T @ b)
> ```

---

## A.12 稀疏矩阵

```python
from scipy.sparse import coo_array, csr_array, csc_array, diags_array, eye, kron
from scipy.sparse.linalg import spsolve, splu, cg, gmres, eigsh, svds

A = coo_array((vals, (rows, cols)), shape=(n, n)).tocsr()   # 从三元组构造
A = diags_array([-np.ones(n-1), 2*np.ones(n), -np.ones(n-1)],
                offsets=[-1, 0, 1], shape=(n, n), format="csc")
```

| 格式 | 擅长 | 什么时候用 |
|------|------|-----------|
| `coo_array` | 快速组装（三元组） | **组装阶段** |
| `csr_array` | 行切片、矩阵向量乘 | 迭代法、`csgraph` |
| `csc_array` | 列切片、**多数直接分解** | `spsolve` / `splu` |
| `dia_array` | 对角结构 | 带形矩阵 |
| `lil_array` | 逐个元素赋值 | 少量增量修改 |

**先看两个数再决定用不用稀疏**：

```python
sparsity = A.nnz / (A.shape[0] * A.shape[1])    # > 20% 基本不用考虑稀疏
lu = splu(A.tocsc())
fill_ratio = (lu.L.nnz + lu.U.nnz) / A.nnz      # < 10 直接法；> 50 试迭代法
```

**解一次用 `spsolve`，解多次用 `splu` 复用**（实测 29 倍加速）。**同一矩阵只分解一次、回代多次**是稀疏直接法最重要的用法。

> **⚠️ 三条坑**：`spsolve` 遇奇异矩阵返回 `nan` 只发警告，`splu` 抛 `RuntimeError`；非 CSC 输入会发 `SparseEfficiencyWarning` 并偷偷转换；`csr_matrix` 的 `*` 是矩阵乘而 `csr_array` 的 `*` 是逐元素乘——**新代码一律用 `*_array`**。§`ds-05` 5.3、`ds-05b` S3

---

## A.13 该用 NumPy 还是 SciPy：六个同名函数的差异

| 任务 | NumPy | SciPy |
|------|-------|-------|
| `solve` / `inv` / `det` / `eig` / `svd` / `qr` / `cholesky` / `lstsq` / `pinv` / `norm` / `cond` | ✅ | ✅（更全） |
| `lu`（含 `lu_factor`/`lu_solve`） | ❌ | ✅ |
| `solve_triangular` / `solve_banded` / `cho_factor` / `cho_solve` | ❌ | ✅ |
| `sqrtm` / `expm` / `logm` / `funm`（矩阵函数） | ❌ | ✅ |
| `ordqz` / `schur` / `hessenberg` / `null_space` / `subspace_angles` | ❌ | ✅ |
| **`cond`** | ✅ | **❌ 不存在** |
| 稀疏矩阵、稀疏特征值 | ❌ | ✅ |

**选择规则**：需要**分解复用**、**结构矩阵**（三角/带形/正定）、**矩阵函数**、**稀疏**时用 SciPy；只做一次普通求解时两者等价，NumPy 少一个依赖。

### 但同名函数的约定并不一致

这是最容易踩的一类坑：**函数名一样、参数名不同、甚至默认语义相反。**

| 函数 | NumPy | SciPy | 危险度 |
|------|-------|-------|--------|
| `cholesky` | 默认**下三角** $L$（$LL^{\top}=S$），`upper=False` | 默认**上三角** $U$（$U^{\top}U=S$），`lower=False` | ★★★ **静默给出错误矩阵** |
| `qr` 的 `mode` | `'reduced'` / `'complete'` | `'full'` / `'economic'` | ★★★ **numpy 对非法值不报错** |
| `lstsq` 的容差 | `rcond=` | `cond=` | ☆ 会报 `TypeError` |
| `pinv` 的容差 | `rcond=` / `rtol=` | `atol=` / `rtol=` | ☆ 会报 `TypeError` |
| `solve` 的结构提示 | 无 | `assume_a=` / `transposed=` | — |
| `eig` 的广义特征值 | 无 | `b=`（解 $Ax=\lambda Bx$） | — |

**`cholesky` 的实测对照**（$S = \begin{bmatrix}4&1\\1&3\end{bmatrix}$）：

```python
>>> np.linalg.cholesky(S)                 # 下三角
array([[2.       , 0.       ],
       [0.5      , 1.6583124]])
>>> la.cholesky(S)                        # 上三角！
array([[2.       , 0.5      ],
       [0.       , 1.6583124]])
>>> la.cholesky(S, lower=True)            # 要下三角必须显式说
array([[2.       , 0.       ],
       [0.5      , 1.6583124]])
```

拿错方向的后果是**静默的**：把 scipy 的上三角当 numpy 的下三角用，`L @ L.T` 得到的是 $\begin{bmatrix}4.25&0.83\\0.83&2.75\end{bmatrix}$——**不是 $S$**，但不报错。

**三条防身规则**：

1. **同一段代码里只用一个库的线性代数**。混用是这些差异伤人的唯一途径。
2. **`cholesky` 永远显式写 `lower=`/`upper=`**，不要依赖默认值。
3. **`la.cho_solve` 必须配对 `la.cho_factor` 的返回值**：`la.cho_solve(la.cho_factor(S), b)`——`cho_factor` 返回的 `(c, lower)` 元组里带着方向信息，不要把 `c` 拆出来单独用。

> **⚠️ 末位不同**：同一个 Hilbert 系统，`numpy.linalg.solve` 与 `scipy.linalg.solve` 会给出**不同的末几位**（调用的 LAPACK 例程不同）。$n=12$ 时一个给 0.70、另一个给 0.39——两者都"对"，因为真值附近没有可信位数了。**病态问题不要比较末位。** §`ds-00` 0.2.9、`ds-05b` S2.6

---

## A.14 常见错误速查

| 症状 | 原因 | 修法 |
|------|------|------|
| `ValueError: shapes ... not aligned` | 矩阵乘法内维不等 | 写 shape 注释，用 `.T` 或 `reshape` 调一边（A.2、A.4） |
| 结果"差不多对"但差很多 | `*` 与 `@` 混用 | 逐元素用 `*`，矩阵乘用 `@`（A.4） |
| `LinAlgError: Singular matrix` | 矩阵奇异 | 换 `lstsq` 求最小范数解；查秩（A.6） |
| `LinAlgError: Internal potrf ...` | 矩阵不正定 | 检查模型前提，或加对角正则化 `A + εI`（A.7） |
| 解的代回残差极小但解很离谱 | **病态**（静默失准） | 看 `cond`，加正则化或换参数化（A.8） |
| 结果由舍入误差决定 | $\mathrm{cond}\ge10^{16}$ | 换模型；提高精度只是把崩塌点推后（A.8） |
| 优化器"立刻收敛" | 落在**鞍点** | 查 Hessian 特征值符号（A.9） |
| `res[0]` 报 `IndexError` | `la.lstsq` 的 `residues` 是 0 维数组 | 用 `float(res)`（A.11） |
| 秩亏但没报错 | `residues` 是 `nan` | 先看 `rank`（A.11） |
| 稀疏求解特别慢 | 填充爆炸 or 格式不对 | 算 `fill_ratio`，试 `permc_spec`（A.12） |
| `v.T` 没变化 | 一维数组无行列之分 | `v.reshape(-1, 1)`（A.5） |
| `too many values to unpack`（配 `qr` 时） | 用了 scipy 的 `mode="economic"` 调 numpy | numpy 用 `mode="reduced"`；非法 mode 不报错（A.13） |
| Cholesky 重构出的矩阵不等于原矩阵 | scipy 默认给上三角、numpy 默认给下三角 | 显式写 `lower=`/`upper=`（A.13） |
| `AttributeError: module 'scipy.linalg' has no attribute 'cond'` | scipy 没有 `cond` | 用 `np.linalg.cond`（A.13） |

---

## A.15 符号速查总表

| 符号 | 名称 | 含义 | Python |
|------|------|------|--------|
| $\lVert x\rVert$ | L2 范数 | 向量长度 | `np.linalg.norm(x)` |
| $\lVert x\rVert_1$ / $\lVert x\rVert_\infty$ | L1 / L∞ | 绝对值和 / 最大绝对值 | `norm(x, 1)` / `norm(x, np.inf)` |
| $A^{\top}$ | 转置 | 行列互换 | `A.T` |
| $\det(A)$ | 行列式 | 体积放大倍数 | `np.linalg.det(A)` |
| $\mathrm{rank}(A)$ | 秩 | 独立方向数 | `np.linalg.matrix_rank(A)` |
| $\mathrm{cond}(A)$ | 条件数 | 约等于丢掉的十进制位数 | `np.linalg.cond(A)` |
| $\sigma_i$ | 奇异值 | SVD 的放大倍数 | `np.linalg.svd(A)[1]` |
| $\lambda$ | 特征值 | 特征方向上的拉伸倍数（可为负） | `np.linalg.eigvalsh(A)` |
| $x^{\top}Ax$ | 二次型 | 特征值全正即正定（碗） | `x @ A @ x` |
| $A^{+}$ | 伪逆 | 最小二乘意义下的"逆" | `np.linalg.pinv(A)` |
| $\nabla f$ | 梯度 | 上升最快方向 | 解析式或 `approx_fprime` |
| $\partial f/\partial x$ | 偏导 | 只对一个变量求导 | 中心差分 |
| $J$ | 雅可比 | 多输出的一阶导矩阵 | 逐列差分 |
| $H$ | Hessian | 二阶导对称矩阵 | 解析式或差分 |
| $\epsilon$ | 机器精度 | $2.22\times10^{-16}$ | `np.finfo(float).eps` |
| $\mathrm{nnz}$ | 非零元个数 | 稀疏矩阵的规模 | `A.nnz` |

---

## 与其它文件的对应

| 想深入 | 去哪 |
|--------|------|
| 形状、广播、点积、矩阵乘的完整教学 | `ds-00` 0.2.1–0.2.7 |
| 行列式/秩/分解/条件数/特征值/梯度的教学与自测 | `ds-00` 0.2.8–0.2.11 |
| 数组的内存布局与 stride | `ds-01b` |
| `np.linalg` 最小集与 `einsum` | `ds-01` 1.13 |
| 线性方程组的工程用法与陷阱 | `ds-05` 5.2 |
| 稀疏与迭代法 | `ds-05` 5.3 |
| 误差从哪来（浮点、前向/后向误差、选主元、Householder） | `ds-05b` S1、S2 |
| 填充与 Krylov 子空间 | `ds-05b` S3 |
| 建模现场的速查（连代码一起抄） | 附录 C |
