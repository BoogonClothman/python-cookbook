# 附录 B 概率与数理统计速查

> **定位**：这是卷 2 的概率统计**急救卡**。`ds-00` 0.3–0.4 负责从零教（概率、分布、期望方差、大数定律、CLT、蒙特卡洛），`ds-04` 负责推断全流程（区间、检验、功效、多重比较、重采样、分布拟合）。本附录负责**当场查**——一个概念或一个决策一张卡。
>
> **用法**：不要通读。先用下面的索引定位，再看卡片的「什么时候用 / 函数 / 最短代码 / 坑」。卡片末尾的 `§` 是回链。
>
> **符号**：$\mu$ 总体均值，$\sigma$ 总体标准差，$\bar x$ 样本均值，$s$ 样本标准差，$n$ 样本量，$\mathrm{SE}$ 标准误，$H_0/H_1$ 原/备择假设，$p$ 是 p 值，$\alpha$ 显著性水平（默认 0.05），$d$ 是 Cohen's $d$。
>
> **验证环境**：Python 3.14.4 + NumPy 2.5.3 + SciPy 1.18.1 + pandas 3.0.6。本附录所有代码都在该环境跑过。**SciPy 1.18 与网上旧教程有六处显著差异**（见 B.0）。

## 卡片索引

| 我想做的事 | 去 |
|-----------|-----|
| SciPy 1.18 与旧教程的六处差异 | B.0 |
| 概率、条件概率、独立性 | B.1 |
| PMF / PDF / CDF 怎么写、怎么用 | B.2 |
| 算均值、方差、标准差（口径要对齐） | B.3 |
| 判断两个变量是否相关 | B.4 |
| 该用哪个分布 | B.5 |
| 样本量为什么重要 | B.6 |
| 算标准误、理解抽样分布 | B.7 |
| 算置信区间（均值 / 比例 / 任意统计量） | B.8 |
| 用哪个检验 | B.9 |
| 常用检验的写法 | B.10 |
| 多个指标一起看，怕假阳性 | B.11 |
| 算"需要多少样本" | B.12 |
| 相关与回归 | B.13 |
| 数据不像正态怎么办 | B.14 |
| 统计量没有现成公式 | B.15 |
| 报效应量 | B.16 |
| 结果不对 / 报错，先看这里 | B.17 |
| 结果怎么报 | B.18 |
| 符号不认识 | B.19 |

---

## B.0 SciPy 1.18 的六处差异

**先看这张表**——它能让网上大量 1.x 教程的代码直接失效。

| # | 差异 | 后果 | 卡片 |
|---|------|------|------|
| ① | **`stats.multicomp` 模块已整体移除**（`pairwise_tukeyhsd` 不可用） | 事后比较改用 `tukey_hsd` / `dunnett` / `false_discovery_control` | B.10、B.11 |
| ② | **`stats.power` 是函数不是类**（`TTestPower` 不存在），它做的是**模拟**而非解析计算；且**默认 `significance=0.01`** 而不是 0.05 | 忘了传 0.05 会得到偏低的功效估计；**scipy 没有分析式样本量求解器**，要自己用非中心 $t$ 算 | B.12 |
| ③ | **`stats.anderson` 必须显式给 `method=`**（`"interpolate"` 或 `MonteCarloMethod(...)`），否则发 `FutureWarning` | 不给 `method` 时返回**旧结构**（靠 `.critical_values` 逐档比较）；给了 `method` 返回只有 `.pvalue` 的新结构。旧的 `.critical_values` / `.significance_level` 将在 1.19 移除 | B.14 |
| ④ | **`proportion_ci` 是 `BinomTestResult` 的方法，不是顶层函数**；只有 `exact`/`wilson`/`wilsoncc`（`normal` 抛 `ValueError`） | 必须写 `stats.binomtest(k, n).proportion_ci(...)` | B.8 |
| ⑤ | **`kstest(x, "norm", args=(loc, scale))` 直接抛 `TypeError`** | 改传冻结分布的 `.cdf`，或用 `fit` 先估参数 | B.14 |
| ⑥ | **`monte_carlo_test` 没有 `rng` 参数** | 只能用全局 `np.random.seed` 复现——与全卷"只用 `default_rng`"的纪律冲突 | B.15 |

**另外**：`stats.ttest_ind` 的 `equal_var` **默认仍是 `True`**（Student），要 Welch 必须写 `equal_var=False`。§`ds-04` 章首、§`ds-04` 4.5.3

---

## B.1 概率基础

```python
P = 有利结果数 / 总试验数                     # 频率定义
P(A | B) = P(A ∩ B) / P(B)                    # 条件概率
独立 <=> P(A ∩ B) = P(A) · P(B)
```

| 概念 | 一句话 | 常见错误 |
|------|--------|---------|
| 互斥 | 不能同时发生（$A \cap B = \varnothing$） | **互斥 ≠ 独立**（互斥时独立意味着 $P(A)=0$） |
| 独立 | 一个发生不改变另一个的概率 | 把"看不出关系"当成独立 |
| 条件概率 | 缩小样本空间后重新计数 | 把 $P(A\mid B)$ 与 $P(B\mid A)$ 混为一谈（检察官谬误） |

> **报告纪律**：比例必须同时报 $n$。"转化率 5%"与"10000 次里 500 次"是同一件事，但只有后者能算不确定性。§`ds-00` 0.3.1–0.3.2

---

## B.2 随机变量与三种写法

离散看 **PMF**（某点概率），连续看 **PDF**（密度，**面积**才是概率，单点概率为 0），两者都由 **CDF** 统一（$F(x) = P(X \le x)$）。

scipy 把三者做成**同一个对象上的方法**：

```python
from scipy import stats
stats.norm.pdf(0)        # 密度：0.3989
stats.norm.cdf(1.96)     # 左尾面积：0.9750
stats.norm.ppf(0.975)    # CDF 的反函数（给概率要分位点）：1.95996
stats.norm.sf(1.96)      # 右尾面积 = 1 - cdf：0.02500
stats.norm.isf(0.025)    # sf 的反函数：1.95996
stats.norm.rvs(size=5, random_state=0)   # 采样
```

| 方法 | 给什么、要什么 | 干什么用 |
|------|--------------|---------|
| `pdf` / `pmf` | 给 $x$ 要密度/概率 | 画分布图；离散分布算概率 |
| `cdf` | 给 $x$ 要 $P(X\le x)$ | p 值、区间 |
| `ppf` | 给概率要 $x$ | 临界值、分位数 |
| `sf` | 给 $x$ 要 $P(X>x)$ | **右尾更准**（避免 $1-\text{cdf}$ 的抵消） |
| `isf` | 给概率要 $x$（右尾） | 上侧临界值 |
| `rvs` | 要样本 | 模拟 |

**参数化**：`loc` 是位置（平移），`scale` 是尺度。正态是 `norm(loc=μ, scale=σ)`（**scale 是标准差不是方差**），但 `rng.normal(μ, σ, n)` 也一样。

```python
stats.norm(loc=100, scale=15).cdf(115)          # 冻结分布：一次给参数，多次调用
frozen = stats.norm(100, 15)
frozen.ppf([0.025, 0.975])                      # array([ 70.6, 129.4])
```

> **⚠️ 坑**：`rng.normal(mu, sigma, n)` 的第二个参数是**标准差**；但 `rng.standard_normal()` 与 `stats.norm(scale=)` 也是标准差；而 **`np.random.RandomState.normal` 之外**，很多地方用**方差**（如 `multivariate_normal` 的 `cov`）。写注释标清。§`ds-00` 0.3.4、§`ds-04` 4.2

---

## B.3 期望、方差与口径对齐

```python
x = np.array([1., 2., 3., 4., 5.])
np.mean(x)          # 2.0
np.var(x)           # 2.0       ← ddof=0（总体）
np.var(x, ddof=1)   # 2.5       ← 样本方差
np.std(x)           # 1.4142    ← ddof=0
np.std(x, ddof=1)   # 1.5811    ← ddof=1
```

**`ddof` 是三库最容易对不上的地方**：

| 入口 | 默认 | 要另一个口径 |
|------|------|------------|
| `np.std` / `np.var` | **ddof=0**（总体） | 显式 `ddof=1` |
| `pd.Series.std` / `.var()` | **ddof=1**（样本） | 显式 `ddof=0` |
| `stats.tstd` | ddof=1 | 没有总体版（`stats.pstd` **不存在**） |
| `stats.sem` | ddof=1 | — |
| `stats.describe(x).variance` | **ddof=1**（实测 2.5） | 自己算 |

> **⚠️ 坑**：同一列数据 `np.std(x)` 与 `pd.Series(x).std()` 会给出**不同的数**（本例 1.4142 vs 1.5811），差 $\sqrt{n/(n-1)}$。$n$ 小时这个差别有 5%（$n=10$）——**对比三库结果前先对齐 ddof**。§`ds-00` 0.3.5、§`ds-04` 4.3.2

**期望的加权平均视角**：`E[X] = sum(p_i * x_i)`，用点积实现 `probs @ values`。§`ds-00` 0.2.4、0.3.5

---

## B.4 协方差与相关系数

```python
np.cov(x, y, ddof=1)             # 协方差矩阵（默认 ddof=1）
np.corrcoef(x, y)[0, 1]          # 皮尔逊相关系数
stats.pearsonr(x, y)             # 返回 (r, p)，r 是线性相关
stats.spearmanr(x, y)            # 秩相关（单调关系，抗离群）
stats.kendalltau(x, y)           # 秩相关（小样本、多并列时更稳）
```

| 系数 | 衡量什么 | 对离群 |
|------|---------|--------|
| `pearsonr` | **线性**关系强度 | 极敏感 |
| `spearmanr` | **单调**关系强度 | 稳健 |
| `kendalltau` | 一致对比例 | 稳健，小样本首选 |

**读法**：符号看方向，$\lvert r\rvert$ 看强度；$r \in [-1,1]$。**相关不等于因果**——混杂变量会让 $\lvert r\rvert$ 虚高（辛普森悖论）。

> **⚠️ 坑**：`np.corrcoef` 默认 `ddof` 不影响相关系数（它被约掉了），但 `np.cov` 的默认 `ddof=1` 与 `np.var` 的 `ddof=0` **不一致**——`np.cov(x,x)[0,0] != np.var(x)`。§`ds-00` 0.3.6、§`ds-04` 4.6.1

**相关矩阵的多重比较**：一次算 $k$ 个相关系数就有 $\binom{k}{2}$ 次检验，要按 B.11 校正。§`ds-04` 4.6.5

---

## B.5 常见分布参数表

| 分布 | scipy | 参数 | 均值 | 方差 | 典型场景 |
|------|-------|------|------|------|---------|
| 均匀 | `uniform(loc, scale)` | 下界、宽度 | $loc+\frac{scale}{2}$ | $\frac{scale^2}{12}$ | 无信息先验、随机抽样 |
| 伯努利 | `bernoulli(p)` | $p$ | $p$ | $p(1-p)$ | 单次成败 |
| 二项 | `binom(n, p)` | 次数、成功率 | $np$ | $np(1-p)$ | $n$ 次成败计数 |
| 正态 | `norm(loc, scale)` | $\mu$、$\sigma$ | $loc$ | $scale^2$ | 误差、测量值、CLT 极限 |
| 泊松 | `poisson(mu)` | 均值 | $\mu$ | $\mu$ | 单位时间事件数 |
| $t$ | `t(df)` | 自由度 | $0$ | $\frac{df}{df-2}$ | 小样本均值 |
| $\chi^2$ | `chi2(df)` | 自由度 | $df$ | $2df$ | 方差、列联表、拟合优度 |
| $F$ | `f(dfn, dfd)` | 两个自由度 | $\frac{dfd}{dfd-2}$ | 见文档 | 方差比、ANOVA |
| 指数 | `expon(scale)` | 均值 $1/\lambda$ | $scale$ | $scale^2$ | 等待时间 |
| 对数正态 | `lognorm(s, scale)` | 对数标准差 | $e^{\mu+\sigma^2/2}$ | — | 收入、尺寸、偏态正值 |
| Beta | `beta(a, b)` | 两个形状 | $\frac{a}{a+b}$ | — | 比例的先验 |
| 伽马 | `gamma(a, scale)` | 形状、尺度 | $a\cdot scale$ | $a\cdot scale^2$ | 保险赔付、降雨量 |

**识别口诀**：计数看二项/泊松，等待时间看指数/伽马，正偏正值看对数正态/伽马，对称误差看正态。

```python
stats.poisson(mu=3).pmf(2)          # 离散用 pmf
stats.norm(0, 1).pdf(0)             # 连续用 pdf
stats.t(df=9).ppf(0.975)            # t(9) 的双侧 95% 临界值：2.2622
stats.chi2(df=3).mean(), stats.chi2(df=3).var()   # (3.0, 6.0)
```

**分布对象自带 `mean()` / `var()` / `std()`**，不用背公式。§`ds-00` 0.3.7、§`ds-04` 4.2.3

---

## B.6 大数定律与中心极限定理

```python
rng = np.random.default_rng(0)
x = rng.exponential(scale=1.0, size=(5000, 30))    # 5000 组，每组 30 个
means = x.mean(axis=1)                              # 5000 个样本均值
means.std(), 1.0/np.sqrt(30)                        # ≈ 0.1825 vs 理论 SE 0.1826
```

| 定理 | 说什么 | 代码验证 |
|------|--------|---------|
| **大数定律** | $\bar x \to \mu$（样本均值收敛到期望） | 增大 $n$，看 $\bar x$ 是否稳定 |
| **中心极限定理** | $\bar x$ 近似正态，且 $\mathrm{SE} = \sigma/\sqrt{n}$ | 看 `means` 的直方图与 `.std()` |

**关键点**：CLT 说的是**样本均值**的分布，不是原始数据的分布。原始数据可以极度偏态（指数、对数正态），样本均值仍然近似正态——**只要 $n$ 够大**。

$\mathrm{SE} = \sigma/\sqrt{n}$ 里 $\sqrt{n}$ 是全部威力的来源：**要让精度翻倍，样本量要翻 4 倍**。§`ds-00` 0.4.1–0.4.2

**蒙特卡洛**：解析不动就模拟。设计试验单元 → 大量重复 → 用频率或均值逼近。误差量级约 $1/\sqrt{N}$（$N$ 是重复次数），**这个误差必须报出来**。§`ds-00` 0.4.3、§`ds-04` 4.8.5

---

## B.7 标准误与抽样分布

```python
stats.sem(x)                          # 均值的标准误，= s/√n（ddof=1）
scipy.stats.bootstrap((x,), np.mean).standard_error   # 任意统计量的 SE
```

| 统计量 | 标准误 | 备注 |
|--------|--------|------|
| 均值 | $\frac{s}{\sqrt n}$ | 最常用 |
| 比例 | $\sqrt{\frac{p(1-p)}{n}}$ | 小样本别用（见 B.8） |
| 均值之差（独立） | $\sqrt{\frac{s_1^2}{n_1}+\frac{s_2^2}{n_2}}$ | Welch |
| 中位数、$R^2$、任意统计量 | 没有简单公式 | 用 bootstrap（B.15） |

**标准误 vs 标准差**：标准差描述**个体**的离散程度（不随 $n$ 变），标准误描述**估计量**的不确定性（随 $n$ 缩小）。报告均值时给 SE，报告数据分布时给 SD。§`ds-00` 0.4.2、§`ds-04` 4.3.3

---

## B.8 点估计与置信区间

### 均值的区间

```python
x = np.random.default_rng(0).normal(100, 15, 30)
n, m, s = x.size, x.mean(), x.std(ddof=1)
crit = stats.t.ppf(0.975, df=n-1)                 # 用 t 不用 z
lo, hi = m - crit*s/np.sqrt(n), m + crit*s/np.sqrt(n)
print(f"{m:.2f} [{lo:.2f}, {hi:.2f}]，t 95%，n={n}")
```

**小样本必须用 $t$**：$n = 3$ 时用 $z = 1.96$ 代替 $t$ 会让第一类错误从 5% 涨到 **18.86%**。§`ds-04b` S1.2

### 比例的区间（**别用 Wald**）

```python
ci = stats.binomtest(3, 20).proportion_ci(0.95, method="wilson")   # ← 方法形式，不是顶层函数
float(ci.low), float(ci.high)          # (0.0524, 0.3604)
```

| 样本 | Wald（手工，不推荐） | Wilson | Wilson+cc | exact |
|------|-------------------|--------|-----------|-------|
| 3/20 | **(−0.0065, 0.3065)** ← 越界 | (0.0524, 0.3604) | (0.0396, 0.3886) | (0.0321, 0.3789) |
| 300/1000 | (0.2716, 0.3284) | (0.2724, 0.3291) | (0.2719, 0.3296) | (0.2717, 0.3295) |

**大样本时四者几乎重合，小样本时 Wald 会越界。默认用 Wilson。**`method=` 只接受 `"exact"` / `"wilson"` / `"wilsoncc"`。§`ds-04` 4.4.2

### 任意统计量的区间（没有公式时）

```python
res = stats.bootstrap((x,), np.median, n_resamples=9999, confidence_level=0.95,
                      method="BCa", rng=np.random.default_rng(0))
res.confidence_interval.low, res.confidence_interval.high
res.standard_error
```

| `method` | 覆盖率（实测，偏态数据） | 什么时候用 |
|----------|---------------------|-----------|
| `"percentile"` | 93.5% | 最快，对称分布可用 |
| `"basic"` | — | percentile 的镜像 |
| `"BCa"` | **93.8%** | **默认首选**（偏差校正 + 加速度） |

> **⚠️ 坑**：`BootstrapResult` **不是 namedtuple**（没有 `_fields`、没有 `keys()`）。取区间必须走 `res.confidence_interval.low/high`（`ConfidenceInterval` 才有 `_fields = ('low','high')`）。§`ds-04` 4.4.3–4.4.4

---

## B.9 假设检验：用哪个

**p 值的定义**：在 $H_0$ 成立的前提下，观测到**至少这么极端**的结果的概率。它**不是**"$H_0$ 为真的概率"，也**不是**"效应有多大"。

### 选型决策表

| 情形 | 检验 | 代码 |
|------|------|------|
| 一组 vs 已知值 | 单样本 t | `ttest_1samp(x, popmean)` |
| 两组独立、近似正态 | **Welch t** | `ttest_ind(a, b, equal_var=False)` |
| 两组配对 | 配对 t | `ttest_rel(before, after)` |
| 两组、偏态/有序/小样本 | Mann-Whitney U | `mannwhitneyu(a, b)` |
| 配对、偏态 | Wilcoxon | `wilcoxon(before, after)` |
| 三组及以上 | 单因素 ANOVA | `f_oneway(*groups)` |
| 三组及以上、非参数 | Kruskal-Wallis | `kruskal(*groups)` |
| 两个分类变量 | 卡方 | `chi2_contingency(tab)` |
| 2×2 且样本小 | Fisher 精确 | `fisher_exact(tab)` |
| 方差齐性 | Levene / Bartlett | `levene(*g)`（稳健）/ `bartlett(*g)`（正态时更强） |
| 正态性 | 见 B.14 | — |

```python
stats.ttest_ind(a, b, equal_var=False)     # ⚠️ 必须显式 False 才是 Welch
stats.mannwhitneyu(a, b, alternative="two-sided")
stats.f_oneway(g1, g2, g3)
stats.chi2_contingency(tab, correction=False)   # 返回 (chi2, p, dof, expected)
```

> **⚠️ 头号陷阱：`ttest_ind` 的 `equal_var` 默认是 `True`（Student）。** 两组样本量或方差不等时，Student 的第一类错误会**严重膨胀**——实测 $n=(10,50)$、方差比 25 时达到 **35.84%**，$n=(5,100)$ 时 **66.63%**（名义 5%）。**默认写 Welch。** §`ds-04` 4.5.3
>
> **卡方的前提**：所有格子**期望频数 $\ge 5$**（用返回的 `expected.min()` 检查）。不满足就换 `fisher_exact`。§`ds-04` 4.5.6

**p 值在 $H_0$ 下是均匀的**：实测 5000 次重复，$\alpha$ 处拒绝率 5.05%、p 值均值 0.5009、KS 检验 p = 0.6916。**p 值不是"越小越显著"，它是校准过的。** §`ds-04b` S2.2

---

## B.10 常用检验写法

```python
import numpy as np
from scipy import stats

rng = np.random.default_rng(0)

# 单样本 t
stats.ttest_1samp(rng.normal(102, 15, 30), popmean=100)

# 两样本 Welch（默认推荐）
r = stats.ttest_ind(rng.normal(0, 1, 30), rng.normal(0.5, 1.4, 30), equal_var=False)
r.statistic, r.pvalue, r.df          # Welch 的 df 是小数

# ANOVA（三组及以上）
groups = [rng.normal(0, 1, 25), rng.normal(0.3, 1, 25), rng.normal(0.6, 1, 25)]
stats.f_oneway(*groups)

# 事后比较（⚠️ 不是 tukeyhsd，那个在 1.18 已移除）
tk = stats.tukey_hsd(*groups)
tk.pvalue[np.triu_indices(3, 1)]     # 3 组 → 3 个两两比较
stats.dunnett(*groups[1:], control=groups[0]).pvalue   # 都跟第 1 组比

# 列联表
tab = np.array([[360, 9640], [463, 9537]])
chi2, p, dof, expected = stats.chi2_contingency(tab, correction=False)
expected.min()                        # 前提检查：应 >= 5（本例 411.5）

# 2×2 小样本
stats.fisher_exact([[3, 7], [8, 2]])
```

**事后检验的选择**：`tukey_hsd` 是**所有两两比较**（控制 FWER），`dunnett` 是**只跟对照比**（更省功效）。**不要直接跑多次 t 检验**（那是 FWER 失控的经典做法）。§`ds-04` 4.5.5

---

## B.11 多重比较：FWER 与 FDR

**问题有多大**：20 个独立检验、真值全为 $H_0$，重复 5000 次的实测——

| 策略 | 至少一次假阳性的比例 |
|------|-------------------|
| 不校正 | **63.7%**（理论 $1-0.95^{20} = 64.2\%$） |
| Bonferroni（$\alpha/m$） | 5.1% |
| Holm | 5.1% |
| **BH-FDR** | 见下表 |

**代价对照**（100 个检验、20 个真效应、30 样本/组、2000 次重复）：

| 策略 | 平均拒绝数 | 假阳性 | 真阳性（共 20） | 假发现比例 |
|------|-----------|--------|---------------|-----------|
| 不校正 | 23.9 | 4.02 | 19.9 | **0.17** |
| Bonferroni | 16.5 | 0.04 | 16.4 | 0.00 |
| **BH-FDR** | 20.3 | 0.87 | **19.5** | **0.04** |

```python
stats.false_discovery_control(pvals, method="bh")      # 返回校正后的 p 值
```

**选择口诀**：

| 你在乎什么 | 用 | 校正谁 |
|-----------|-----|-------|
| "一次都不能错"（确证性研究） | Bonferroni / Holm | FWER |
| "错的比例不超过 5%"（探索性研究） | **BH** | FDR |
| 只跟对照组比 | Dunnett | FWER |
| 全部两两比 | Tukey HSD | FWER |

**BH 在同样 FDR 下真阳性率是 Bonferroni 的两倍多**，探索性研究里它是更好的默认。§`ds-04` 4.5.7

---

## B.12 功效与样本量

**先明确一件事：`scipy.stats` 没有分析式样本量求解器。** 1.18 的 `stats.power` 是一个**模拟**函数——把检验跑很多遍来估计功效。

### 模拟法：`stats.power`

```
stats.power(test, rvs, n_observations, *, significance=0.01,
            vectorized=None, n_resamples=10000, batch=None, kwargs=None)
```

| 参数 | 含义 |
|------|------|
| `test` | 检验函数（如 `stats.ttest_ind`） |
| `rvs` | 生成器或生成器列表，签名 `f(size=..., rng=...)` |
| `n_observations` | 每组的样本量（列表） |
| `significance` | **默认 0.01，不是 0.05**（版本注意②） |
| `kwargs` | 传给 `rvs` 的额外参数——**随机源走这里**：`kwargs={"rng": ...}` |

```python
rvs = [lambda size, rng: rng.normal(0, 1, size),
       lambda size, rng: rng.normal(0.5, 1, size)]           # d = 0.5
r = stats.power(stats.ttest_ind, rvs, n_observations=[30, 30], significance=0.05,
                n_resamples=3000, batch=1000, kwargs={"rng": np.random.default_rng(3)})
r.power          # 0.461
```

返回 `PowerResult`，只有两个属性：`power` 与 `pvalues`（**不是 namedtuple，没有 `.keys()`**）。

模拟扫描（1200 次重采样）——$d = 0.5$：

| $n$/组 | 20 | 40 | **64** | 90 |
|--------|----|----|-------|-----|
| 模拟功效 | 0.360 | 0.579 | **0.825** | 0.908 |

### 要算"需要多少样本"，用非中心 $t$ 自写

二分搜索非中心 $t$ 的分布函数，十行就够（这也是 `statsmodels` / `pingouin` 内部做的事）：

```python
from scipy.optimize import brentq
def n_ttest(d, alpha=0.05, power=0.8):
    """两独立组 t 检验的精确样本量（每组）。d 是 Cohen's d。"""
    def gap(n):
        df = 2*n - 2
        nc = d * np.sqrt(n / 2.0)                 # 非中心参数
        crit = stats.t.ppf(1 - alpha/2, df)
        return stats.nct.sf(crit, df, nc) - power
    lo, hi = 2, 200000
    while gap(hi) < 0: hi *= 2
    return brentq(gap, lo, hi)
```

| 效应量 | 近似式 $2(z_{1-\alpha/2}+z_{\text{power}})^2/d^2$ | 精确（非中心 $t$） | 取整后实际功效 |
|--------|--------------------------------|-----------------|-------------|
| $d = 0.2$ | 392.4 | 393.4 | 394（0.8006） |
| $d = 0.5$ | 62.8 | 63.8 | **64（0.8015）** |
| $d = 0.8$ | 24.5 | 25.5 | 26（0.8075） |
| $d = 1.0$ | 15.7 | 16.7 | 17（0.8070） |

**近似式系统性偏小约 1 例**，因为它在正态的世界里算、忽略了 $t$ 的厚尾。工程做法：**先用近似式得初值，再用非中心 $t$ 精算一遍**（不到一秒）。

### 外部库（本环境未安装，只作指路）

| 需求 | 去哪 |
|------|------|
| 经典功效公式族（t / F / 比例 / ANOVA / 相关） | `statsmodels.stats.power` |
| 带便捷接口的功效分析 | `pingouin` |
| 任意检验（含自写统计量）的功效 | `stats.power` 模拟 ✅ 内置 |

> **⚠️ 陷阱：事后功效不提供任何信息。** 实测 p ≈ 0.1 时事后功效 0.395、p ≈ 0.5 时 0.103——它是 p 值的单调函数，等于复读机。**功效要在实验前算。** §`ds-04` 4.5.8、§`ds-04b` S5.5

> **"显著 ≠ 重要"最直观的一张表**：固定一个**微小**效应（真实均值差 0.75 分、标准差 15 分、$d = 0.05$）——
>
> | $n$/组 | 25 | 100 | 400 | 1600 | 6400 |
> |--------|----|-----|-----|------|------|
> | 检出率 | 5.0% | 5.8% | 11.6% | 28.0% | **79.3%** |
>
> 同一个差异，$n = 25$ 时几乎检不出，$n = 6400$ 时接近必检出。**p 值是"效应大小 × 样本量"的函数**，所以永远要配着效应量一起报。

## B.13 相关与回归

```python
lr = stats.linregress(x, y)
lr.slope, lr.intercept, lr.rvalue, lr.pvalue, lr.stderr, lr.intercept_stderr
```

> **⚠️ 坑**：`LinregressResult._fields` 是 `('slope','intercept','rvalue','pvalue','stderr')`——**`intercept_stderr` 是额外属性，不在 `_fields` 里**。用 `tuple(lr)` 展开会丢掉它。

**稳健回归**（有离群点时）：

```python
from scipy.optimize import least_squares
r = least_squares(lambda p: p[0] + p[1]*x - y, [0, 0], loss="soft_l1", f_scale=0.3)
```

实测（10% 粗差、500 次蒙特卡洛）：`loss="linear"` 的参数误差 0.432，`soft_l1`/`huber`/`cauchy` 都在 0.041——**好 10.5 倍**。而 `"arctan"` 中位数最好却**失败率 15.4%**，不要用。§`ds-05` 5.6.2

**相关 ≠ 因果**：辛普森悖论——分组看每个子群都是正相关，合起来却是负相关。**遇到悖论先找混杂变量。** §`ds-04` 4.6.4

---

## B.14 分布拟合与正态性

```python
stats.shapiro(x)          # 样本量 < 5000 时最推荐
stats.normaltest(x)       # 基于偏度+峰度，大样本友好
stats.anderson(x, method="interpolate")   # ⚠️ 必须给 method=
stats.kstest(x, "norm")   # 参数已知时才正确，见下面的坑
```

| 检验 | 前提 / 特点 |
|------|-----------|
| `shapiro` | $n$ 小时功效最好；$n > 5000$ 会警告 |
| `normaltest` | 大样本；对偏度峰度敏感 |
| `anderson` | 必须显式 `method=`；`"interpolate"` 从一张小表插值，`MonteCarloMethod` 模拟 |
| `kstest` | **参数必须已知**，否则失效 |

> **⚠️ 头号陷阱（Lilliefors）：用估计出来的参数做 KS 检验会彻底失效。** 同一份 $N(0,1)$ 数据：
>
> | 情形 | 假阳性率（名义 5%） |
> |------|------------------|
> | 参数**已知** | 5.38% ✓ |
> | 参数**估计**（Kolmogorov 版 KS） | **0.04%** ← 几乎永远不会拒绝 |
>
> 所以 `stats.kstest(x, "norm")` 在没给参数时**不是一个有效的正态性检验**——它太保守，会让真偏态的数据通过。用 `shapiro`/`normaltest`/`anderson`，或改用 Lilliefors 校正。§`ds-04` 4.7.2
>
> **另一个坑**：`stats.kstest(x, "norm", args=(loc, scale))` 在 1.18 **直接抛 `TypeError`**（`ndtr() takes from 1 to 2 positional arguments but 3 were given`）。要指定参数就传冻结分布：

```python
stats.kstest(x, stats.norm(loc=x.mean(), scale=x.std(ddof=1)).cdf)
```

**带参数的 MLE 拟合**：

```python
res = stats.fit(stats.norm, data, bounds={"loc": (-10, 10), "scale": (1e-3, 10)})
```

> **⚠️ 陷阱：`stats.fit` 不给 `bounds` 会静默返回初值。** 用 $N(50, 10)$ 的 500 个样本实测：
>
> | 写法 | `loc` | `scale` | `nllf` | `success` |
> |------|-------|---------|--------|-----------|
> | `stats.fit(stats.norm, data)` | **0.0000** | **1.0000** | **644439.67** | `True` |
> | `stats.fit(stats.norm, data, bounds={...})` | 49.7311 | 10.1360 | **1867.52** | `True` |
>
> 负对数似然差了 **345 倍**，而 `success` 两次都是 `True`。不给 `bounds` 时它停在初值 $(0, 1)$ 上（样本均值 49.73、样本标准差 10.15 就在旁边）。**`bounds` 不是可选项。**
>
> 但**不能偷懒写 `±np.inf`**——那会直接报错：
>
> ```
> ValueError: The intersection of user-provided bounds for `loc` and the domain
> of the distribution is not finite.
> ```
>
> 要给它一个**物理上说得通的有限区间**（例如 `{"loc": (0, 200), "scale": (1e-3, 50)}`）。有形状参数的分布（`gamma`、`beta`、`lognorm`……）不给 `bounds` 同样直接 `ValueError`。
>
> **这个比值取决于初值离真值有多远。** 换成 $N(0,1)$ 的数据，初值 $(0,1)$ 本身就是 MLE，`nllf` 之比是 **1.00**，完全看不出异常——**所以不能靠"结果看起来合理"来发现这个陷阱，只能靠"我给了 bounds 吗"这个习惯。** §`ds-04` 4.7.4、§`ds-04b` S6.3

**`anderson` 的三种写法给出三种结果结构**（实测同一份 $N(0,1)$ 数据、统计量都是 0.4494）：

| 写法 | 返回类型 | p 值 |
|------|---------|------|
| `stats.anderson(x)` | `AndersonResult`（旧，带 `critical_values`） | 无 |
| `stats.anderson(x, method="interpolate")` | `SignificanceResult` | 0.1500 |
| `stats.anderson(x, method=stats.MonteCarloMethod(n_resamples=999, rng=...))` | `SignificanceResult` | 0.2900 |

**`"interpolate"` 是从一张很小的临界值表插值出来的，精度有限**；要对得起"p 值"这个称呼，用 `MonteCarloMethod`。注意 `MonteCarloMethod` 的 `rvs=` 与 `rng=` **互斥**，模拟随机性用 `rng=`。

旧结构的用法是逐档比较：

```python
r = stats.anderson(x)                # 会发 FutureWarning
r.statistic, r.critical_values, r.significance_level
# (0.4494, array([0.557, 0.626, 0.746, 0.866, 1.027]), array([15. , 10. ,  5. ,  2.5,  1. ]))
# 统计量小于 5% 的临界值 0.746 → 不拒绝正态性
```

**变换到正态**：`stats.boxcox`（正数据）/ `stats.yeojohnson`（含零与负）。

---

## B.15 重采样三件套

```python
# ① 置换检验：检验"两组是否来自同一分布"
r = stats.permutation_test((g1, g2), statistic=lambda a, b: a.mean() - b.mean(),
                           permutation_type="independent", n_resamples=9999,
                           rng=np.random.default_rng(0))
r.pvalue, r.statistic, r.null_distribution

# ② bootstrap：给任意统计量配区间
r = stats.bootstrap((x,), np.median, n_resamples=9999, method="BCa",
                    rng=np.random.default_rng(0))
r.confidence_interval.low, r.confidence_interval.high, r.standard_error

# ③ 蒙特卡洛检验：自定义统计量的零分布
r = stats.monte_carlo_test(x, rng.normal, np.mean, n_resamples=9999)
r.pvalue
```

| 入口 | 回答什么 | 关键参数 |
|------|---------|---------|
| `permutation_test` | 两组/配对/独立性 | **`permutation_type`**：`"independent"` / `"samples"` / `"pairings"` |
| `bootstrap` | 任意统计量的区间与 SE | `method="BCa"`、`confidence_level` |
| `monte_carlo_test` | 任意统计量的 p 值 | **没有 `rng`**（版本注意⑥） |

**三种 `permutation_type` 对应三种假设**：`"independent"` 打乱组标签（两组独立）、`"samples"` 打乱组内（同分布检验）、`"pairings"` 打乱配对（配对设计）。**用错会检验一个你没想问的假设。** §`ds-04` 4.8.1

**必须报两个数字**：**重复次数 $B$** 与 **分辨率** $1/(B+1)$。$B = 999$ 时 p 值只能取到 0.001 的倍数——**p = 0.0001 与 p = 0.001 在这种分辨率下无法区分**。§`ds-04` 4.8.5

**bootstrap 的三个失效场景**（实测）：重尾 $t(2)$ 下 BCa 覆盖率只有 **88.1%**；极值统计量覆盖真上界 **0.0%**；依赖数据的 AR(1) 下 iid 重抽样覆盖率 **45.2%**。**前两个换方法无效，要换思路；第三个要用块 bootstrap。** §`ds-04b` S3.6

---

## B.16 效应量

| 场景 | 效应量 | 公式 | 经验阈值（小/中/大） |
|------|--------|------|-------------------|
| 两组均值 | Cohen's $d$ | $\frac{\bar x_1-\bar x_2}{s_p}$ | 0.2 / 0.5 / 0.8 |
| 相关 | $r$ | 直接 | 0.1 / 0.3 / 0.5 |
| 比例 | Cohen's $h$ | $2\arcsin\sqrt{p_1}-2\arcsin\sqrt{p_2}$ | 0.2 / 0.5 / 0.8 |
| ANOVA | $\eta^2$ | $\frac{SS_{\text{组间}}}{SS_{\text{总}}}$ | 0.01 / 0.06 / 0.14 |
| 列联表 | Cramér's $V$ | $\sqrt{\frac{\chi^2}{n\min(r-1,c-1)}}$ | 0.1 / 0.3 / 0.5 |

```python
def cohens_d(a, b):
    na, nb = len(a), len(b)
    sp = np.sqrt(((na-1)*a.var(ddof=1) + (nb-1)*b.var(ddof=1)) / (na+nb-2))
    return (a.mean() - b.mean()) / sp
```

**换算**：$r \leftrightarrow d$ 用 $d = 2r/\sqrt{1-r^2}$；$\eta^2$ 与 $f$ 用 $f = \sqrt{\eta^2/(1-\eta^2)}$。

> **报告纪律**：**p 值说"有没有"，效应量说"有多大"，区间说"有多准"。三者缺一不可。** 只看 p 值会把"样本量大到把微小差异变显著"当成重要发现。§`ds-04` 4.5.9

---

## B.17 常见错误速查

| 症状 / 想法 | 错在哪 | 修法 |
|------------|--------|------|
| `np.std(x)` 与 `pd.Series(x).std()` 不一致 | ddof 默认不同（0 vs 1） | 显式写 ddof（B.3） |
| 两组比较结果过于显著 | `ttest_ind` 默认 Student，方差不等时膨胀 | `equal_var=False`（B.9） |
| 比例区间下限是负数 | 用了 Wald | 换 Wilson（B.8） |
| `stats.proportion_ci` 报 `AttributeError` | 它是方法不是函数 | `stats.binomtest(k, n).proportion_ci(...)`（B.0④） |
| `pairwise_tukeyhsd` 找不到 | `stats.multicomp` 已移除 | `stats.tukey_hsd`（B.0①） |
| 找不到算样本量的函数 | **scipy 没有分析式求解器** | 用非中心 $t$ 自写，或 `statsmodels.stats.power`（B.12） |
| 模拟功效偏低 | `stats.power` 默认 `significance=0.01` | 显式传 `significance=0.05`（B.0②） |
| `kstest(x, "norm", args=(...))` 抛 `TypeError` | 1.18 不接受 `args` | 传冻结分布的 `.cdf`（B.14） |
| `anderson` 不给 `method` 就报 `FutureWarning` | 旧属性 1.19 将移除 | 显式给 `method="interpolate"`（B.14） |
| 正态性检验从不拒绝 | 用了估计参数的 KS（Lilliefors） | 换 `shapiro`/`normaltest`（B.14） |
| `stats.fit` 结果明显不对但 `success=True` | 没给 `bounds`，静默返回初值 | 显式给 `bounds`（B.14） |
| `res.confidence_interval` 取不到 | `BootstrapResult` 不是 namedtuple | 用 `.confidence_interval.low/high`（B.8） |
| `r.intercept_stderr` 在解包时丢了 | 它不在 `_fields` 里 | 按属性取，别 `tuple(lr)`（B.13） |
| `monte_carlo_test` 结果不可复现 | 它没有 `rng` 参数 | 用全局 `np.random.seed`（B.15） |
| 事后功效"看起来不错" | 它是 p 值的复读机 | 实验前算（B.12） |
| 20 个指标里有一个显著就当真 | 不校正时 FWER 达 63.7% | 按 B.11 校正 |

---

## B.18 报告模板

**区间报告**（任何"提升了 X%"都套这个）：

```
<点估计> [<下限>, <上限>]，<方法> <置信水平>，n=<样本量>
例：4.63% [4.24%, 5.06%]，Wilson 95%，n=10000
```

**检验报告**（四件套缺一不可）：

```
<检验名>：统计量 = <值>，p = <值>，效应量 = <值> [<区间>]
说明前提检查：<正态性/方差齐性/期望频数>；多重比较用 <方法> 校正
例：Welch t(48.3) = 2.31, p = 0.025, Cohen's d = 0.58 [0.08, 1.08]；
     Shapiro p = 0.31（未拒绝正态），未做多重比较校正（单指标预注册）
```

**四条纪律**：

1. **口径先定**：分析前写死指标定义、$\alpha$、最小可检测效应、剔除规则。**事后调整口径等于重新抛硬币。**
2. **假设先写**：$H_0$ 是什么、单侧还是双侧、独立性成不成立。
3. **区间优于点**：任何提升都要带区间与 $n$。
4. **报告校正**：多个指标/多组比较时说明用了哪个校正方法。

§`ds-04` 4.1.3、4.5.9、4.9.3

---

## B.19 符号速查总表

| 符号 | 名称 | 含义 | Python |
|------|------|------|--------|
| $P(A)$ | 概率 | 事件发生的可能性 | 频率估计 `count / n` |
| $P(A\mid B)$ | 条件概率 | 已知 $B$ 时 $A$ 的概率 | 缩小样本后重新计数 |
| $E[X]$ | 期望 | 以概率为权的加权平均 | `np.mean(x)` |
| $\mathrm{Var}(X)$ | 方差 | 波动程度 | `np.var(x, ddof=1)` |
| $\sigma$ / $s$ | 总体 / 样本标准差 | 方差的平方根 | `np.std(x, ddof=0/1)` |
| $\mathrm{SE}$ | 标准误 | 估计量的标准差 | `stats.sem(x)` |
| $\mu$ / $\bar x$ | 总体 / 样本均值 | 位置 | `np.mean(x)` |
| $n$ | 样本量 | — | `x.size` |
| $\rho$ / $r$ | 总体 / 样本相关系数 | 线性关系强度 | `stats.pearsonr` |
| $\mathrm{N}(\mu,\sigma^2)$ | 正态分布 | 钟形 | `stats.norm(mu, sigma)` |
| $\sim$ | 服从 | $X \sim \mathrm{N}(\mu,\sigma^2)$ | 由采样器生成 |
| i.i.d. | 独立同分布 | 样本彼此独立且同分布 | `rng.normal(mu, sigma, n)` |
| $H_0$ / $H_1$ | 原 / 备择假设 | — | — |
| $p$ | p 值 | $H_0$ 下观测到至少这么极端的概率 | `test(...).pvalue` |
| $\alpha$ | 显著性水平 | 第一类错误的上限（默认 0.05） | 写进代码常量 |
| $\beta$ | 第二类错误率 | $1-\beta$ 是功效 | `stats.power`（模拟）或非中心 $t$ |
| $d$ | Cohen's $d$ | 标准化均值差 | 手算（B.16） |
| $\mathrm{ddof}$ | 自由度修正 | 分母用 $n$ 还是 $n-1$ | `np.var(x, ddof=1)` |
| $\mathrm{FWER}$ | 族错误率 | 至少一次假阳性的概率 | 校正方法选型（B.11） |
| $\mathrm{FDR}$ | 假发现率 | 被拒绝中错误的比例 | `false_discovery_control` |

---

## 与其它文件的对应

| 想深入 | 去哪 |
|--------|------|
| 概率、条件概率、PMF/PDF/CDF 的教学 | `ds-00` 0.3.1–0.3.4 |
| 期望、方差、协方差、五个分布的教学 | `ds-00` 0.3.5–0.3.7 |
| 大数定律、CLT、蒙特卡洛 | `ds-00` 0.4.1–0.4.3 |
| 重抽样原语（手工 bootstrap） | `ds-01` 1.13.4–1.13.5 |
| 随机变量对象、区间、检验、功效、多重比较 | `ds-04` 4.2、4.4、4.5 |
| 相关回归、分布拟合、正态性、重采样 | `ds-04` 4.6–4.8 |
| 统计工作流与陷阱总表 | `ds-04` 4.9 |
| 零分布从哪来、BCa 推导、bootstrap 失效场景 | `ds-04b` S1、S3 |
| 功效解析式、样本量精度、MLE 数值问题 | `ds-04b` S5、S6 |
| 建模现场的速查（含参数反演与不确定度传播） | 附录 C |
| 线代部分 | 附录 A |
