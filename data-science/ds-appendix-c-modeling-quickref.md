# 附录 C 建模竞赛速查卡：问题类型 → 函数 → 最短代码

> **用法**：这是一张**照着抄**的表，不是教材。每张卡片给三样东西——**什么时候用**、**函数入口**、**能直接跑的最短代码**。原理、陷阱与实测依据全在第 5 章对应小节，卡片末尾的"§"就是回链。
>
> **配套**：`ds-05-scipy-modeling.md`（第 5 章，原理与陷阱）、`ds-05b-scipy-numerics-internals.md`（数值内核，引用写作 `§S<n>`）。本卡片只覆盖 scipy/numpy 能做的事；**做不到的**集中在最后一节，避免在赛场上临时找库。
>
> **验证环境**：Python 3.14.4 + SciPy 1.18.1 + NumPy 2.5.3。所有代码片段都在该环境跑过；数字来自第 5 章的实测。

---

## C.1 解多元线性方程组

**什么时候用**：关系已经写成 $Ax = b$（投入产出、电路、结构、流量平衡、稳态分布）。

```python
import numpy as np
from scipy import linalg as la

A = np.array([[3., 1., 1.],
              [1., 4., 2.],
              [2., 1., 5.]])
b = np.array([10., 15., 18.])

# ① 体检（必做）
cond = np.linalg.cond(A)
if cond > 1e10:
    print(f"警告 cond={cond:.1e}，只剩 {15 - np.log10(cond):.1f} 位有效数字")

# ② 按结构选入口（快慢差可达 500 倍）
if np.allclose(A, A.T) and np.all(np.linalg.eigvalsh(A) > 0):
    x = la.cho_solve(la.cho_factor(A), b)          # 对称正定，快一倍
else:
    x = la.solve(A, b)                             # 一般方阵

# ③ 验证（必做）
assert np.abs(A @ x - b).max() < 1e-8 * max(np.abs(b).max(), 1), "残差过大"
```

**结构化的三个更快入口**（§5.2.1）：

```python
x = la.solve_banded((1, 1), ab, b)                 # 三对角/带形：O(n)，实测快 506 倍
x = la.solve_triangular(L, b, lower=True)          # 已知三角
x = la.solve(A, b, assume_a="pos")                 # 声明对称正定
```

**不要用** `np.linalg.inv(A) @ b`——慢 1.8 倍，残差还大 $10^{9}$ 倍（§5.2.1）。

---

## C.2 超定 / 欠定 / 秩亏

```python
from scipy import linalg as la
from scipy.optimize import lsq_linear, nnls

# 超定最小二乘（m > n）
x, residues, rank, sv = la.lstsq(A, b)             # 返回普通 4 元组！
if rank < A.shape[1]:
    print("⚠️ 秩亏：residues 是 nan，不是报错")

# 系数必须非负
x, rnorm = nnls(A, b)

# 系数带上下界
res = lsq_linear(A, b, bounds=([0, 0], [np.inf, np.inf]))
x = res.x                                          # 返回 OptimizeResult，有命名属性
```

**三条纪律**（§5.2.5）：

1. **永远不要用正规方程** `np.linalg.solve(A.T@A, A.T@b)`——$\mathrm{cond}$ 被平方，实测在 $\mathrm{cond}(A) = 10^{8}$ 时误差差 **64 亿倍**。
2. 病态时**加岭正则化**比换算法有效：
   ```python
   lam = 1e-4                                       # 实测把系数误差降到 1/445，残差只涨 4.7%
   x = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ b)
   ```
3. 秩亏时先查 `rank`，再决定要不要截断 SVD：
   ```python
   U, s, Vt = la.svd(A, full_matrices=False)
   keep = s > 1e-10 * s[0]                          # 显式容差，不要用默认值
   x = (Vt[keep].T / s[keep]) @ (U[:, keep].T @ b)
   ```

---

## C.3 大规模稀疏方程组

```python
from scipy.sparse import diags_array, coo_array, csr_array
from scipy.sparse.linalg import spsolve, splu, cg, gmres

# 从三元组（边列表）构造
A = coo_array((vals, (rows, cols)), shape=(n, n)).tocsr()

# 从对角构造（长度 = 该偏移的真实长度，不含填充）
A = diags_array([-np.ones(n-1), 2*np.ones(n), -np.ones(n-1)],
                offsets=[-1, 0, 1], shape=(n, n), format="csc")

x = spsolve(A, b)                                  # 只解一次

lu = splu(A)                                       # 同一矩阵多次解：复用分解，实测 29×
x1, x2 = lu.solve(b1), lu.solve(b2)

x, info = cg(A, b, rtol=1e-10)                     # 迭代法：必须检查 info
assert info == 0, f"CG 未收敛 (info={info})"
```

**选直接法还是迭代法**（§5.3.3）：先算填充比，再决定。

```python
lu = splu(A)
fill_ratio = (lu.L.nnz + lu.U.nnz) / A.nnz
# < 10 → 直接法；> 50 → 试迭代法；> 200 → 往往别无选择
```

| 情形 | 入口 |
|------|------|
| 对称正定 | `cg` |
| 一般非对称 | `gmres(A, b, restart=50)` |
| 最小二乘（长方形） | `lsqr` / `lsmr` |
| 少数特征值 | `eigsh(A, k, which="SM")` |
| 少数奇异值 | `svds(M, k)` |

**注意**：`spsolve` 遇奇异矩阵返回 `nan` 只发警告，`splu` 抛 `RuntimeError`——两者行为不一致（§5.3.3）。

---

## C.4 线性规划

```python
from scipy.optimize import linprog

# 标准型：min c'x  s.t.  A_ub x <= b_ub,  A_eq x = b_eq,  l <= x <= u
res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
              bounds=(0, None), method="highs")

assert res.status == 0, f"status={res.status}: {res.message}"
print(res.fun, res.x)

# 影子价格（灵敏度分析免费拿）
print(res.ineqlin.marginals)                       # 每个 <= 约束的边际价值
print(res.eqlin.marginals)                         # 等式约束
print(res.lower.marginals, res.upper.marginals)    # 变量界
```

**四个改写动作**（§5.5.1）：

| 要做的 | 怎么写 |
|--------|--------|
| $\max f$ | `c = -c`，结果 `-res.fun` |
| $\ge$ 约束 | 两边乘 $-1$ 放进 `A_ub`/`b_ub` |
| 等式 | 放 `A_eq`/`b_eq` |
| 自由变量 | 拆成 $x^+ - x^-$，`bounds` 给 `(0, None)` |

**状态码**：`0` 最优 · `1` 达上限 · `2` 不可行 · `3` 无界 · `4` 数值困难。

---

## C.5 整数 / 0-1 规划

```python
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np

# 变量顺序：y(决策 0-1) + x(连续)
c = np.concatenate([open_cost, ship_cost.ravel()])
integrality = np.concatenate([np.ones(n_y), np.zeros(n_x)])   # 1=整数, 0=连续, 2=半连续, 3=半整数
bounds = Bounds(np.zeros(n), np.concatenate([np.ones(n_y), np.full(n_x, np.inf)]))

res = milp(c=c, constraints=LinearConstraint(A_ub, -np.inf, b_ub),
           integrality=integrality, bounds=bounds)

assert res.status == 0
print(f"成本 {res.fun:,.0f}  mip_gap {res.mip_gap}  开仓 {res.x[:n_y].astype(int)}")
```

**报告 MILP 结果必须带 `mip_gap`**——间隙 5% 与 0% 是两种可信度（§5.5.3）。

---

## C.6 五个建模套路

**① 运输问题**（$m$ 产地、$n$ 销地、供需平衡）：

```python
sup = np.array([20., 30.]); dem = np.array([10., 25., 15.])
C = np.array([[8., 6., 10.], [9., 12., 13.]])
n, m = C.shape
A_eq = np.zeros((n + m, n * m))
for i in range(n): A_eq[i, i*m:(i+1)*m] = 1        # 行和 = 供应量
for j in range(m): A_eq[n + j, j::m] = 1           # 列和 = 需求量  ← 关键一行
r = linprog(C.ravel(), A_eq=A_eq, b_eq=np.r_[sup, dem], bounds=(0, None))
flow = r.x.reshape(n, m)
```

产销不平衡时补一个虚拟产地/销地（运费 0）把等式凑齐（§5.5.4）。

**② 指派问题**：

```python
from scipy.optimize import linear_sum_assignment
rows, cols = linear_sum_assignment(C)              # 最小化
rows, cols = linear_sum_assignment(C, maximize=True)  # 最大化（1.4+）
total = C[rows, cols].sum()
```

`np.inf` 表示"不允许这个指派"；长方形矩阵只指派 $\min(m,n)$ 对（§5.5.4）。

**③ 背包**：`milp(c=-v, constraints=LinearConstraint(w, -np.inf, W), integrality=np.ones(n), bounds=Bounds(0, 1))`

**④ 选址-分配**：三条约束——需求满足、连锁 $x_{kj} \le M y_k$、容量 $\sum_j x_{kj} \le c_k y_k$。

```python
# ⚠️ 块切片必须以 3 为基准偏移，否则容量约束只覆盖一部分变量
row[3+k*6 : 3+(k+1)*6] = 1.0
row[k] = -cap[k]
```

**⑤ 排班**：整数变量 = 各天开始上班的人数，约束矩阵是 0-1 轮转矩阵。

```python
A = np.zeros((7, 7))
for d in range(7):
    for s in range(7):
        if (d - s) % 7 < 5: A[d, s] = 1            # 连续工作 5 天
r = milp(c=np.ones(7), constraints=LinearConstraint(A, needs, np.inf),
         integrality=np.ones(7), bounds=Bounds(0, np.inf))
```

---

## C.7 非线性 / 全局优化

```python
from scipy.optimize import minimize, differential_evolution, Bounds, LinearConstraint, NonlinearConstraint

# ① 无约束（有解析梯度就一定要给）
res = minimize(f, x0, jac=grad_f, method="BFGS", tol=1e-10)

# ② 有界
res = minimize(f, x0, jac=grad_f, bounds=Bounds(lb, ub), method="L-BFGS-B")

# ③ 约束（优先用 NonlinearConstraint，方向写死在 lb/ub，不会搞反）
con = NonlinearConstraint(lambda v: v[0]**2 + v[1], -np.inf, 1.0)   # <= 1
res = minimize(f, x0, jac=grad_f, constraints=[con], method="SLSQP")

# ④ 多局部极小 → 全局
res = differential_evolution(f, bounds=[(-5, 5)]*2, rng=np.random.default_rng(42))
```

**四条纪律**（§5.4）：

1. **显式写 `method=`**，不要依赖默认值。
2. **能写解析梯度就写**：实测 `nfev` 从 117 降到 39，精度提高 6 个数量级。
3. **字典式 `{"type": "ineq"}` 要求 $g(x) \ge 0$**，写反会返回无约束最优解**且 `success=True`**。
4. **`success=True` 不表示找到最优**：可能精度不足、可能违反约束、可能落在局部极小。

**验证模板**：

```python
assert res.success, res.message
if not constraints:
    assert np.linalg.norm(grad_f(res.x)) < 1e-3, "未到驻点"
for c in constraints:
    assert max(0.0, -c["fun"](res.x)) < 1e-6, "约束被违反"
```

---

## C.8 求根

```python
from scipy.optimize import brentq, root_scalar, root, fsolve

# ① 已知括号（有异号）→ 最稳，必收敛
x = brentq(f, a, b)                                # f(a)*f(b) < 0 才能用

# ② 只有初值（更快但不保证收敛）
r = root_scalar(f, x0=1.0, fprime=df, method="newton")
assert r.converged, "Newton 未收敛"                 # 必须检查！

# ③ 多元方程组
r = root(sys_f, x0, jac=jac_f)                     # 给 jac 能省函数调用
assert r.success, r.message
```

**先画图或网格扫一遍**，看清符号变化在哪，再决定括号或初值（§5.4.5）。

---

## C.9 曲线拟合与参数反演

```python
from scipy.optimize import curve_fit, least_squares

# ① 已知模型形式
def model(t, a, b, c): return a * np.exp(-b*t) + c
sigma = np.full(t.size, 0.15)                      # 已知测量误差（不知道就省略 sigma）
popt, pcov = curve_fit(model, t, y, p0=[5, 1, 0], sigma=sigma, absolute_sigma=True)
perr = np.sqrt(np.diag(pcov))                      # 参数标准误
print(np.round(popt, 4), "±", np.round(perr, 4))

# ② 数据有粗差 → 稳健损失（f_scale 应当取噪声水平）
r0 = least_squares(lambda p: model(t, *p) - y, p0, loss="linear")
mad = 1.4826 * np.median(np.abs(r0.fun - np.median(r0.fun)))
res = least_squares(lambda p: model(t, *p) - y, p0, loss="soft_l1", f_scale=mad)
# loss 选 "soft_l1"/"huber"/"cauchy"；不要用 "arctan"（实测 15.4% 失败率）
```

**反问题**（参数藏在一个求解器里，如 SIR、ODE、MILP）：

```python
from scipy.integrate import solve_ivp

def resid(p):
    s = solve_ivp(ode, t_span, y0, args=tuple(p), t_eval=t_eval, rtol=1e-6)
    return s.y[1] - obs if s.success else np.full(t_eval.size, 1e12)   # 失败要给巨大残差

r = least_squares(resid, p0, bounds=(lb, ub))
```

**四道检查（缺一不可）**（§5.6.3）：

1. **残差随参数是不是 V 形**——平的就说明参数不可辨识，调求解器没用。
2. **换几个初值是否收敛到同一点**。
3. **参数相关系数**（从 `r.jac` 算协方差）接近 ±1 是预警。
4. **残差量级是否与噪声相符**——远大于噪声说明模型结构不对。

---

## C.10 插值、平滑与数据补全

```python
import scipy.interpolate as si

# ① 要穿过每个点、且不能越界 → PCHIP
f = si.PchipInterpolator(x, y)

# ② 要光滑（C²）→ 三次样条（可能过冲）
f = si.CubicSpline(x, y)

# ③ 数据带噪声 → 平滑样条（自动选参数）
f = si.make_smoothing_spline(x, y)                 # 返回 BSpline，结点是 f.t（不是 get_knots）

# ④ 规则网格多维插值
f = si.RegularGridInterpolator((gx, gy), V, method="cubic", bounds_error=True)

# ⑤ 散点插值
f = si.RBFInterpolator(pts, vals, kernel="thin_plate_spline")
pred = f(query)
assert np.isfinite(pred).all(), "⚠️ 凸包外会静默返回 nan"
```

**缺失值填补**（§5.7.5）：三次样条误差比线性插值小 **18 倍**，前向填充在有趋势的数据上必然出错。

```python
mask = np.isnan(y); idx = np.arange(len(y))
y_filled = si.CubicSpline(idx[~mask], y[~mask])(idx)   # 或 PchipInterpolator 保形
```

**三条禁令**：等距高次多项式（21 点误差 59.8）；`interp1d`（legacy）；`fill_value=None`（线性外推，实测错 170%）。

---

## C.11 数值积分

```python
from scipy.integrate import quad, dblquad, nquad, trapezoid, simpson, cumulative_trapezoid

# ① 有可调用的函数 → 自适应（端点奇点、无穷区间都能处理）
val, err = quad(f, a, b)
val, err = quad(f, -np.inf, np.inf)

# ② 只有采样点 → Simpson（O(h⁴)，比梯形快 6 个数量级）
val = simpson(y, x)                                # 需要奇数个等距点最好
val = trapezoid(y, x)                              # 数据有跳变时用它

# ③ 累积积分
cum = cumulative_trapezoid(y, x, initial=0)

# ④ 多重积分（维数 ≤ 3）
val, err = dblquad(lambda yy, xx: f(xx, yy), x0, x1, y0, y1)   # ⚠️ 参数顺序是反的
val, err = nquad(f, [[0,1]]*3)                                  # 写法更自然
```

**维数 > 3 转蒙特卡洛**（§5.8.3）。**版本注意**：`simps` / `trapz` / `cumtrapz` / `romberg` / `quadrature` 与 `np.trapz` 在 1.18 全部已移除。

---

## C.12 微分方程

```python
from scipy.integrate import solve_ivp

def ode(t, y, p1, p2):
    S, I, R = y
    return [-p1*S*I/N, p1*S*I/N - p2*I, p2*I]      # 一阶方程组

sol = solve_ivp(ode, [0, 120], y0, args=(0.42, 0.14),
                t_eval=np.linspace(0, 120, 121),
                method="LSODA", rtol=1e-8, atol=1e-10,
                dense_output=True)

assert sol.success and np.isfinite(sol.y).all()

# 事件（什么时候发生）
def hit(t, y): return y[0]
hit.terminal = True                                # 触发后停止
hit.direction = -1                                 # 只抓下降方向
sol = solve_ivp(ode, t_span, y0, events=hit)
t_event = sol.t_events[0][0]
```

**方法选择**（§5.9.2）：**先用 `LSODA`**（自动检测刚性）。确定性质后：非刚性用 `DOP853`/`RK45`，刚性用 `Radau`（准）/`BDF`（快）。刚性比 $> 10^{3}$ 直接上隐式。

**过零问题必须显式给 `atol`**（`rtol` 在零点附近没有意义）。

---

## C.13 随机模拟与不确定性

```python
from scipy.stats import qmc

# ① 低差异采样（点数取 2 的幂！）
sampler = qmc.Sobol(d=6, scramble=True, rng=1)
U = sampler.random(4096)                           # 4096 = 2^12

# ② 不确定度传播：参数协方差 → 参数样本 → 重跑模型
L = np.linalg.cholesky(cov)
params = p_hat[None, :] + qmc.Sobol(len(p_hat), scramble=True, rng=2).random(256) @ L.T
results = [run_model(p) for p in params]
lo, hi = np.percentile(results, [5, 95])

# ③ 全局敏感性（Saltelli 估计量）
A_ = qmc.Sobol(k, scramble=True, rng=3).random(N)
B_ = qmc.Sobol(k, scramble=True, rng=4).random(N)
YA, YB = f(A_), f(B_); V = np.var(np.r_[YA, YB])
S1 = [np.mean(YB * (f(np.column_stack([B_[:, i] if j == i else A_[:, j] for j in range(k)])) - YA)) / V
      for i in range(k)]
```

**Sobol 比朴素 MC 精确 396 倍**（$N = 16384$，§5.10.1）。**方差缩减**：分层抽样 61×、对偶变量 4.4×、重要性抽样 13–15×（§5.10.3）。

**OAT 会骗人**：它给的是局部斜率，不是方差贡献。参数有交互时 OAT 可能给出定性错误的答案（§5.10.2）。

---

## C.14 图与网络

```python
import numpy as np
from scipy.sparse import csr_array
from scipy.sparse.csgraph import (shortest_path, dijkstra, minimum_spanning_tree,
                                  maximum_flow, connected_components,
                                  maximum_bipartite_matching)

W = csr_array(adj_matrix)                          # 邻接矩阵（0 = 无边，对角线为 0）

# ① 最短路（"D" Dijkstra / "BF" Bellman-Ford / "J" Johnson / "FW" Floyd-Warshall）
D = shortest_path(W, method="D", directed=False)                 # 全源
d, pred = shortest_path(W, method="D", directed=False, indices=[0],
                        return_predecessors=True)                # 单源 + 前驱

# ② 从 pred 回溯路径（reconstruct_path 返回的是树，不是路径！）
def path_from_pred(pred, src, dst):
    if src == dst: return [src]
    p = [dst]
    while p[-1] != src:
        nxt = int(pred[p[-1]])
        if nxt < 0 or len(p) > len(pred): return None
        p.append(nxt)
    return p[::-1]

# ③ K 短路（默认只给代价）
costs, preds = yen(W, 0, 5, K=3, directed=False, return_predecessors=True)

# ④ 其他
n_comp = connected_components(W, directed=False)[0]
mst = minimum_spanning_tree(W)
mf = maximum_flow(G, 0, sink); mf.flow_value, mf.flow.toarray()
matching = maximum_bipartite_matching(B, perm_type="column")
```

**`csgraph` 把 0 当作"无边"**——带权匹配里权重恰为 0 的边会被忽略（§5.11.4）。

---

## C.15 聚类、距离与几何

```python
from scipy.spatial import cKDTree, distance, ConvexHull, Delaunay
from scipy.cluster import hierarchy
from scipy.cluster.vq import kmeans2

# ① 距离（点数大时不要算距离矩阵！）
D = distance.cdist(pts_a, pts_b, "euclidean")      # 两组点
dm = distance.pdist(pts)                           # 组内，只算一半（n(n-1)/2）
tree = cKDTree(pts)                                # 百万点找邻居用这个
d, idx = tree.query(query_pts, k=5)
ball = tree.query_ball_point(center, r)            # 半径内所有点
pairs = tree.query_pairs(r)                        # 距离 < r 的点对

# ② 几何
hull = ConvexHull(pts); hull.vertices, hull.volume  # ⚠️ 2D 下 volume 是面积
tri = Delaunay(pts)

# ③ 层次聚类（不用预设簇数）
Z = hierarchy.linkage(X, method="ward")
lab = hierarchy.fcluster(Z, 3, criterion="maxclust")
quality = hierarchy.cophenet(Z, distance.pdist(X))[0]   # 越接近 1 越好
# 一定要画 dendrogram 看局部结构

# ④ k 均值（必须多起点验证）
from collections import Counter
inertias = []
for seed in range(20):
    c, l = kmeans2(X, k, minit="++", seed=seed)
    inertias.append(np.sum((X - c[l])**2))
print(Counter(np.round(inertias, 4)))              # 结果的分散程度 = 数据是否支持 k 个簇
```

---

## C.16 信号、频谱与图像

```python
from scipy import signal, fft, ndimage

fs = 200.0                                          # 采样率

# ① 频谱（实数用 rfft，幅值乘 2/n）
F = fft.rfft(x); freq = fft.rfftfreq(x.size, 1/fs); mag = np.abs(F)*2/x.size

# ② 功率谱（噪声大用 welch，要看精确频率用 periodogram）
f_w, P_w = signal.welch(x, fs=fs, nperseg=256)

# ③ 零相位滤波（用 SOS，不要用 b/a）
sos = signal.butter(4, 20, btype="low", fs=fs, output="sos")   # ⚠️ 必须给 fs=
y = signal.sosfiltfilt(sos, x)                                 # ⚠️ 短信号会报 padlen 错

# ④ 峰值检测
pk, props = signal.find_peaks(x, height=0.5, distance=20, prominence=0.5)
widths = signal.peak_widths(x, pk, rel_height=0.5)[0]

# ⑤ 快速卷积 / 重采样
y = signal.fftconvolve(a, b, mode="same")
y = signal.resample_poly(x, up=3, down=2)

# ⑥ 二维：连通域、距离变换、平滑
lab, n = ndimage.label(binary_img)
dist = ndimage.distance_transform_edt(binary_img)
smooth = ndimage.gaussian_filter(img, sigma=2)
```

**版本注意**：`signal.cwt` / `morlet2` / `ricker` / `lsim2` 已移除（小波用 PyWavelets）。

---

## C.17 性能与内存速查

| 问题 | 做法 | 预期收益 |
|------|------|---------|
| 三对角/带形矩阵 | `solve_banded` | 比稠密快 **506×**（§5.2.1） |
| 同一矩阵多次求解 | `lu_factor` / `splu` 复用 | **29×**（§5.3.3） |
| 稀疏矩阵的重排 | 试 `permc_spec="MMD_AT_PLUS_A"` | 填充少 **2.9×**（§5.3.3） |
| 大点数找近邻 | `cKDTree` 代替距离矩阵 | 内存从 GB 降到 MB（§5.12.1） |
| 实数 FFT | `rfft` 而非 `fft` | 1.5×（§S7.4） |
| 非合数长度 FFT | `fft.next_fast_len(n)` 补齐 | 素数长度快 **14.7×**（§S7.5） |
| 采样点积分 | `simpson` 而非 `trapezoid` | 精度高 6 个数量级（§5.8.2） |
| 高维积分 | 蒙特卡洛 / QMC | 误差与维数无关（§5.8.3） |
| 低差异采样 | `qmc.Sobol` | 比 MC 精确 **396×**（§5.10.1） |
| 重复的 ODE 积分 | 解析梯度 + `LSODA` | 比 RK45 少 **26×** 调用（§5.9.2） |
| 矩阵乘法 | 保持 `float64` 单一 dtype | 避免降精度（§S2.6） |

---

## C.18 结果报告清单

给出任何数值结果时，固定写这四项（§5.13.2）：

| 项 | 例子 |
|----|------|
| **方法名与关键参数** | `linprog(method="highs")`、`solve_ivp(method="Radau", rtol=1e-8)`、`splu(permc_spec="COLAMD")` |
| **残差 / 违背量** | `‖Ax−b‖∞ = 1.4e-14`、`约束最大违反 2.4e-07`、`KKT 平稳性 9.4e-07` |
| **规模与条件数** | `n = 2000, nnz = 5998`、`cond = 1.6e+13`、`fill_ratio = 5.62`、`mip_gap = 0` |
| **迭代 / 调用次数** | `nit = 32, nfev = 39`、`CG 1000 次迭代, info = 0`、`nfev = 7` |

**再加一条**：涉及随机性时报**种子**；涉及计时时报**机器与版本**。

---

## C.19 赛题里 scipy 做不了的

这一节只做指路，**不给代码**——本环境未安装这些库，凭记忆写代码是错误来源。

| 需求 | 该去哪里 | 说明 |
|------|---------|------|
| 符号推导、解析求导、公式化简 | **sympy** | 需要闭式解、解析 Jacobian/Hessian 时 |
| 图算法全集：中心性、PageRank、社区发现 | **networkx** | `csgraph` 只有最短路/流/匹配/MST |
| 凸优化建模语言（锥规划、半正定、SDP） | **cvxpy** | 约束写起来更接近数学，底层调多个求解器 |
| 统计模型（回归诊断、混合效应、时间序列 ARIMA） | **statsmodels** | `ds-04` 只覆盖到假设检验与分布拟合 |
| 机器学习（分类、聚类集成、降维、交叉验证） | **scikit-learn** | 卷 3 的内容 |
| 连续小波变换 | **PyWavelets** | `signal.cwt` 已在 1.15 移除 |
| 两轴都带误差的回归（正交距离回归） | **odrpack** | `scipy.odr` 自 1.17 弃用、1.19 移除 |
| 大规模整数规划（百万变量） | **Gurobi / CPLEX / HiGHS 命令行** | `milp` 适合中等规模 |
| 评价方法：AHP、TOPSIS、熵权法、模糊综合评价 | 无标准库，**自己实现** | 都是十几行矩阵运算，但要自己写清楚 |
| 数据读取（Excel、CSV、数据库） | **pandas**（卷 2 `ds-02`）、`openpyxl` | 不在 scipy 范围 |
| 可视化与出版级图 | **matplotlib**（卷 2 `ds-03`） | 不要用求解器的自带输出当成品图 |

> **一条策略建议**：竞赛环境中装库有时间成本与失败风险。**先用本章覆盖的 12 个模块把能做的做完**，确有必要再引入新依赖；而且要在报告里注明依赖版本——数值结果对版本敏感（第 5 章章首列了 8 条版本差异，每一条都会让旧教程的代码失效）。

---

## 速查索引

| 我想做的事 | 去 |
|-----------|-----|
| 解方程组 | C.1 |
| 最小二乘 / 秩亏 / 岭回归 | C.2 |
| 稀疏与迭代法 | C.3 |
| 线性规划与影子价格 | C.4 |
| 整数 / 0-1 规划 | C.5 |
| 运输 / 指派 / 背包 / 选址 / 排班 | C.6 |
| 非线性与全局优化 | C.7 |
| 求根 | C.8 |
| 曲线拟合、稳健拟合、反问题 | C.9 |
| 插值、平滑、缺失值 | C.10 |
| 定积分与多重积分 | C.11 |
| 微分方程与事件 | C.12 |
| 随机模拟、不确定度、敏感性 | C.13 |
| 最短路、最大流、匹配 | C.14 |
| 聚类、距离、几何 | C.15 |
| 频谱、滤波、峰值、图像 | C.16 |
| 性能与内存优化 | C.17 |
| 结果怎么报 | C.18 |
| 该换什么库 | C.19 |
