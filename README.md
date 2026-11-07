# Python 教案系列

面向教学的 Python 系统化教案，**即查即用、一针见血**。

## 系列总览

本仓库以 **5 卷**组织。卷 1 是 Python 语言核心（所有方向的共同地基）；卷 2–5 面向数据科学与 AI 方向。

| 卷 | 主题 | 目录 | 状态 |
|----|------|------|------|
| 卷 1 | Python 语言核心 | `python-core/` | ✅ 完成（1–15章 + 3专题 + 1附录） |
| 卷 2 | 科学计算与数据分析 | `data-science/` | ✅ 完成（第0–5章 + 6 本深水配套 + 3 附录） |
| 卷 3 | 机器学习 | `machine-learning/` | 🚧 进行中（第0章完成） |
| 卷 4 | 深度学习 | `deep-learning/` | ⚪ 规划中  |
| 卷 5 | 大模型与 AI 应用 | `llm/` | ⚪ 规划中  |

## 卷 1：Python 语言核心

> 按语言特性线性铺开，深入 CPython 底层（字节码、内存布局、协议机制）。

### 已完成

| 章 | 内容 |
|----|------|
| [第1章 环境搭建](python-core/py-01-environment-setup.md) | 编程语言的分类、Python 的发展史、设计哲学、安装部署、pip/venv/uv、PEP 8 |
| [第2章 基础语法](python-core/py-02-basic-syntax.md) | 语句/表达式、缩进/代码块、注释/docstring、标识符/关键字/命名、变量/对象/引用语义、赋值全解、运算符/短路/比较链、print/input/assert|
| [第3章 标准数据类型](python-core/py-03-standard-types.md) | 数字、字符串、序列、映射与集合|
| [第4章 运算符](python-core/py-04-operators.md) | 算术/比较/身份/逻辑/位/成员、赋值全解、优先级、运算符重载协议 |
| [第5章 条件语句 & 循环语句 & 推导式](python-core/py-05-control-flow.md) | 真值协议、if/elif/else、match/case、while/for、迭代器协议、推导式、生成器表达式 |
| [第6章 函数：从调用约定到函数式编程](python-core/py-06-functions.md) | 函数对象与一等公民、传参语义、封包解包、LEGB 与闭包、lambda 与高阶函数、生成器函数  |
| [第7章 面向对象编程](python-core/py-07-oop.md) | 类与实例、方法绑定、抽象/封装/继承/多态、封装协议、MRO 与 super、鸭子类型/ABC/Protocol、特殊方法协议与对象生命周期、dataclass/enum/`__slots__`、设计模式|
| [第7章配套：设计模式详解](python-core/py-07-design-patterns.md)  | 创建型/结构型/行为型模式、SOLID 原则、模式"消亡"对照表、反模式与实战 |
| [第8章 异常处理与上下文管理器](python-core/py-08-exceptions-context.md) | 异常对象模型与类层次、try/except/else/finally、异常链、ExceptionGroup/`except*`、EAFP vs LBYL、with 协议与 contextlib、事务式资源管理 |
| [第9章 文件 I/O 与序列化](python-core/py-09-file-io-serialization.md) | 分层 IO 体系（RawIO、缓冲、TextIO）、open() 全参数、编码/换行/缓冲、性能基准、随机访问、struct/mmap、pathlib/tempfile、pickle/json 序列化、原子写 |
| [第10章 模块与包管理](python-core/py-10-modules-packages.md) | import 执行语义与字节码、importlib 流水线（PEP 451）、`__pycache__` 与 PEP 552、自定义 import 钩子、包/相对导入/命名空间包（PEP 420）、循环导入、venv 机制、pyproject.toml 打包（PEP 517/518/621）、wheel/editable（PEP 427/660）、pip/uv 与锁文件、zipapp/PEP 723 部署 |
| [第11章 并发与异步编程](python-core/py-11-concurrency-async.md)  | 进程/线程/协程三抽象与切换成本、Amdahl 定律、GIL 机制（PEP 703 自由线程）、线程锁/同步原语/`threading.local`、死锁四条件、queue 生产者-消费者、ThreadPoolExecutor/Future、multiprocessing、async/await 与事件循环（PEP 342/380/492）、asyncio 实战、选型矩阵、并发陷阱与确定性测试 |
| [第12章 元编程](python-core/py-12-metaprogramming.md) | 装饰器深入、描述符协议、属性访问完整路径、元类（type 即类、class 创建流程、`__prepare__`/`__init_subclass__`、注册表/单例元类）、`__call__`/`__new__`/`__reduce__` 协议、mini-dataclass/插件注册/声明式字段实战、元编程使用边界 |
| [第13章 标准库精选](python-core/py-13-stdlib.md) | 标准库全景与选型哲学、collections、itertools（惰性组合）、functools、datetime/zoneinfo（PEP 615）、math/decimal/random/secrets/statistics、subprocess/shutil/glob、sqlite3/csv/configparser/argparse、logging、typing（PEP 484/585/604）、隐藏宝石速查 |
| [第14章 测试与调试](python-core/py-14-testing-debugging.md) | 测试哲学与金字塔、TDD、可测试性设计、unittest、pytest、mock、覆盖率与 CI 门禁、pdb 断点调试（breakpoint/post-mortem/faulthandler）、traceback 解读、cProfile/timeit、doctest |
| [第15章 性能优化与 C 扩展](python-core/py-15-performance-cext.md)  | 解释器执行模型、五层优化路线图、cProfile/line\_profiler/tracemalloc 进阶、复杂度优化、字节码视角、3.11+ 特化解释器（PEP 659）、numpy 向量化预告、PyPy/numba、ctypes 调 C 库、Python C API、Cython 类型化、性能回归与 CI、卷 1 全景收官 |
| [专题：深浅拷贝](python-core/py-topic-deep-shallow-copy.md) | 引用语义、is vs ==、浅/深拷贝、`__copy__`/`__deepcopy__` 协议、CPython 内存布局、七大陷阱 |
| [专题：正则表达式](python-core/py-topic-regex.md) | 正则与自动机理论、re 模块 API、编译与缓存机制、贪婪/惰性/回溯、环视/分组/标志、灾难性回溯与性能 |
| [专题：反射机制](python-core/py-topic-reflection.md) | 内省基础、属性访问协议、`inspect` 工具箱、动态调用与创建、反射驱动架构、元数据反射、代价与边界 |
| [附录A：Python 3 版本演进](python-core/py-appendix-a-python3-version-evolution.md) | 3.0→3.14 核心 PEP 与 CPython 实现 |

## 卷 2：科学计算与数据分析

### 已完成

| 章 | 内容 |
|----|------|
| [第0章 数学前置](data-science/ds-00-math-primer.md) | 记号与函数工具箱、可复现随机数约定、线代形状语言（点积/矩阵乘/转置/单位阵）、概率基础（频率/条件概率/PMF-PDF-CDF/期望方差/协方差/常见分布）、统计推断地基（大数定律/CLT与标准误/蒙特卡洛）、迷你数据分析实战 |
| [第1章 NumPy 数组](data-science/ds-01-numpy.md) | 数组为什么快（量化）、数据模型（buffer/dtype/shape/strides）、dtype 与 NEP 50、创建、索引四式、视图与拷贝、广播完整规则、轴语义、ufunc（`out=`/`where=`/`at`）、聚合排序与 NaN、形状代数、线代最小集与 `einsum`、随机数 Generator、I/O、性能工程、互操作协议、调试与验证、综合实战；每节配随堂自测与"本节交付"接口说明 |
| [第1章配套：内存深水](data-science/ds-01b-numpy-internals-memory.md) | CPython 对象开销与数组布局、缓冲区协议（PEP 3118）与 memoryview、strides 完全解析（含 `sliding_window_view` 与 `as_strided` 警戒）、缓存与规模效应、所有权与别名（`.base`/`OWNDATA`/生命周期）、分配器与惰性页、memmap、`.npy` 文件格式 |
| [第1章配套：计算深水](data-science/ds-01c-numpy-internals-compute.md) | ufunc 循环与 CPU/SIMD 分派、`__array_ufunc__`/`__array_function__` 协议、成对求和 vs 顺序累加、排序稳定性、类型提升全表与 dtype 扩展、BLAS 后端与 `einsum` 路径、nditer/内存带宽/roofline、随机数内核、何时离开 NumPy（Numba/SciPy） |
| [第2章 Pandas](data-science/ds-02-pandas.md) | DataFrame 数据模型、Index 与查找成本、loc/iloc 取写与 Copy-on-Write 契约、dtype 与两种缺失值（`NaN`/`pd.NA`）、索引对齐算术、CSV 类型往返、变形（melt/pivot/stack）、split-apply-combine 四算子、merge 行数契约与笛卡尔爆炸、时间序列（解析/时区/重采样/滚动）、清洗工作流、文本与链式写法、性能工程（向量化 1700 倍账）、调试与契约断言、八步综合实战；每节配随堂自测与"本节交付"接口说明 |
| [第2章配套：内部实现深水](data-science/ds-02b-pandas-internals.md) | BlockManager 块与合并、CoW（PDEP-7）机制与 NumPy 视图对照、Index 引擎冷/热/批量三层成本、对齐与 hash merge 算法（含保险丝成本实测）、groupby 分桶与开关代价、时区 UTC 内核与 rolling 递推、Arrow 与两种字符串阵营、何时离开 pandas（pandas/duckdb/polars 三方实测） |
| [第3章 Matplotlib](data-science/ds-03-matplotlib.md) | 生态定位（命令式 vs 声明式）、pyplot 状态机 vs OO、Artist 对象树与延迟渲染、Figure/Axes 解剖与方法动物园、transform 四段链、类别轴/`c` 语义/zorder 三陷阱、统计图族容器总表、多面板与 dpi 换算（`_original_dpi` 陷阱）、色彩管线（clim 第二自由度）与 colorbar、Locator/Formatter 与图例锚定、rc 与 `.mplstyle` 模板、输出与后端（SVG 字形转 path）、pandas/seaborn 两级 API 桥接、渲染性能三本账、静默错误清单与 `check_figure` 图形契约、八步综合实战；每节配随堂自测与"本节交付"接口说明 |
| [第3章配套：渲染内核深水](data-science/ds-03b-matplotlib-internals.md) | draw 全流水线与 stale 三级回调（`savefig` 结束反而变脏）、pyplot figure manager 与 `gca` 栈、别名表与 `remove()` 解链、dataLim/viewLim/autoscale 懒状态机（读属性即兑现）、图型容器的批量构造、rcParams 校验器与样式分层；transform 四段链的括号与矩阵、换标度只换 `_child`、GridSpec/SubplotParams 解算链、constrained 求解器、`apply_aspect` 活动框、Grouper 弱引用共享；单位注册表（随模块加载增长）与 `_converter`/`units` 双槽位、自定义类型接入、字符串↔数值三种静默错误、Locator/Formatter 分界、pandas 的"临时换表"；后端注册表、`buffer_rgba` 零拷贝可写视图、格式矩阵与产物可复现性（PNG 稳 / PDF-EPS 需 `SOURCE_DATE_EPOCH` / SVG 还需 `svg.hashsalt`）、无 pyplot 嵌入；色彩管线（Normalize 家族、`_lut` 的 N+3 行、colorbar 是"拥有一根轴"的对象）；渲染成本实测三杠杆（简化 37×、分块 2.2×、对象合并 6× 产物）与光栅化救护（85×）；`animated` 的两副面孔与 blitting（49×）；离开 matplotlib 的量化边界 |
| [第4章 SciPy 与统计推断](data-science/ds-04-scipy-stats.md) | scipy 定位与推断四步骨架；随机变量对象（`rvs/pdf/cdf/ppf/sf` 六方法、冻结分布、131 个分布、逆变换）；描述统计与抽样分布（ddof 三库口径、CLT 收敛实测、抗离群）；估计与区间（$t$ 区间、Wilson/exact 比例区间、bootstrap 的 percentile/basic/BCa、覆盖率实测）；假设检验全解（p 值均匀性实测、Welch vs Student 膨胀 66.6%、秩检验功效、离群点三种偏差、ANOVA 与 `tukey_hsd`/`dunnett`、FWER 63.7% 与 BH-FDR、`stats.power` 功效曲线）；相关与回归（三种相关系数、`linregress` 全字段、Theil-Sen 稳健回归、辛普森悖论）；分布拟合与正态性（四检验对照、**Lilliefors 陷阱实测**、`stats.fit`、QQ 定量诊断、Box-Cox/Yeo-Johnson、`ecdf`）；重采样三件套（三种 `permutation_type` 与误用陷阱、bootstrap、`monte_carlo_test`、分辨率与可交换性实测）；八步 A/B 流水线 + 17 条陷阱总表 + 断言化口径；每节配随堂自测与"本节交付"接口说明 |
| [第4章配套：统计推断深水](data-science/ds-04b-scipy-internals.md) | 零分布的血统（t/F/χ² 都是正态样本的二次型，实测 KS p 值 0.37–0.93；用 z=1.96 代替 t 时 n=3 的第一类错误 18.86%）；自由度 = 二次型的秩；p 值均匀性的概率积分变换证明；非中心 t 功效解析式（nc = d√(n/2)）与 Satterthwaite 小数自由度；效应量族与换算；置换检验的精确性（穷举 2/20）与蒙特卡洛误差（p 的标准误 ∝ 1/√B）；可交换性失效的定量机制（零分布方差比 3.23 → 保守 / 0.29 → 膨胀）；BCa 三步手算完全复现 scipy；bootstrap 三个失效场景（重尾 88.1%、极值 0.0%、依赖 45.2%）；FWER 精确值与相关性影响（ρ=0.9 时校正当到 1.35%）；BH 在 FDR 4% 下真阳性率是 Bonferroni 的两倍；样本量三档公式精度（392/63/25 对精确 394/64/26）；事后功效是 p 值的复读机；MLE 的对数似然必要性、似然脊线（相关 −0.93）、**`stats.fit` 不给 bounds 的静默失败**、渐近 SE 低估 25–33%、拟合优度的参数自助校准 |
| [第5章 SciPy 数值方法与建模](data-science/ds-05-scipy-modeling.md) | 四步骨架（写下来/问可解/求解/验证）与三本账；线性方程组与矩阵分解（`solve` 而非 `inv`、结构矩阵快 506×、**条件数静默失准区 $10^{6}$–$10^{15}$**、残差 ≠ 误差）；稀疏与大系统（填充决定成本、`permc_spec` 差 2.88×、**CG 竟是直接法的 42–77 倍慢**）；非线性优化（10 个方法精度差 15 个数量级、解析梯度省 3× 调用、**字典式约束符号写反仍返回 success=True**、Rastrigin 上 50 次多起点 0/50）；线性与整数规划（四个改写动作、影子价格、五个建模套路、big-M 连锁约束系数写反）；曲线拟合与反问题（`pcov` 三种含义、稳健损失好 10.5× 而 `arctan` 15.4% 失败、**SIR 参数化写错导致不可辨识且零报错**）；插值平滑与补全（龙格现象 21 点误差 59.8、PCHIP 保形、凸包外静默 `nan`）；数值积分（Simpson 比梯形高 6 个数量级）；微分方程（刚性代价 26×、事件精度由容差决定、守恒量验证）；随机模拟（Sobol 比 MC 精确 396×、OAT 看不到交互、分层抽样 61×）；图与网络（最短路四法、**`reconstruct_path` 返回的是树**）；空间/聚类/信号；综合实战（应急物资调度 + 疫情需求预测，含「不确定度改变最优决策」）；26 条陷阱总清单 + 断言化验证模板 |
| [第5章配套：数值内核深水](data-science/ds-05b-scipy-numerics-internals.md) | S1 浮点物理（灾难性抵消让方差公式在 $c=10^{8}$ 时 100% 错）与前后向误差不等式；S2 分解（选主元防的是什么、Householder vs MGS 在 $n=200$ 时差 2000×、SVD 四子空间、BLAS 按 dtype 分派）；S3 稀疏与 Krylov（`indptr` 语义、填充是图的消元问题、CG 迭代次数实测恰为 $0.785\sqrt{\kappa}$）；S4 优化内核（KKT 乘子符号为 $\nabla f = \lambda\nabla g$、线搜索 vs 信赖域、BFGS 逆 Hessian 误差 0.3%、差分导数 $h^*=\epsilon^{1/3}$ 的 U 形）；S5 ODE 稳定域（**RK45 实测步长 2.802e-3 vs 理论 $2.785/\lvert\lambda\rvert$**、A-稳定 ≠ 准确）；S6 插值病态（Lebesgue 常数等距 $2^n$ vs Chebyshev $\log n$，$n=20$ 差 2076×）；S7 积分与 FFT（Gauss–Kronrod 自适应、素数长度慢 14.7×）；S8 低差异序列（van der Corput/Halton/Sobol 的构造、QMC 加速只对期望型估计量成立） |
| [附录A 线性代数速查](data-science/ds-appendix-a-linear-algebra-quickref.md) | 15 张急救卡：形状与轴语义 / 广播三规则 / 范数与距离 / 点积与矩阵乘 / 转置与逆 / 行列式秩与可解性 / 四种分解选择表 / 条件数读法与体检模板 / 特征值与二次型（碗还是鞍）/ 梯度雅可比 Hessian 与差分步长 U 形 / 最小二乘与伪正则 / 稀疏矩阵两判据 / **NumPy 与 SciPy 六个同名函数的约定差异**（`cholesky` 默认上/下三角相反、`qr` 的 mode 名不同且 numpy 对非法值不报错）/ 常见错误速查 14 条 / 符号总表；代码逐段实跑 |
| [附录B 概率与数理统计速查](data-science/ds-appendix-b-prob-stats-quickref.md) | 19 张急救卡：SciPy 1.18 六处版本差异 / 概率与条件概率 / PMF-PDF-CDF 六方法 / ddof 三库口径 / 协方差与三种相关系数 / 12 个分布参数表 / LLN 与 CLT 代码版 / 标准误 / 区间估计（t 区间、Wilson 比例区间、bootstrap BCa）/ 检验选型决策表与常用写法（**`ttest_ind` 默认 Student 必须显式 Welch**）/ 多重比较 FWER 与 FDR / 功效与样本量（**scipy 无分析式求解器，给非中心 t 的十行实现**）/ 相关回归与稳健拟合 / 正态性四检验（**Lilliefors 陷阱、`anderson` 三种写法、`stats.fit` 不给 bounds 静默返回初值**）/ 重采样三件套 / 效应量 / 常见错误速查 14 条 / 报告模板 / 符号总表；代码逐段实跑 |
| [附录C 建模竞赛速查卡](data-science/ds-appendix-c-modeling-quickref.md) | 19 张卡片按「问题类型 → 函数 → 最短可复制代码」组织：方程组 / 最小二乘 / 稀疏 / 线性规划 / 整数规划 / 五个建模套路 / 非线性与全局优化 / 求根 / 拟合与反问题 / 插值补全 / 积分 / 微分方程 / 随机模拟与敏感性 / 图与网络 / 聚类几何 / 信号频谱 / 性能速查 / 结果报告清单 / 该换什么库；全部代码逐段实跑通过 |

## 卷 3：机器学习

> 从数学前置出发，沿 sklearn 生态线性铺开，最后收口到工程化流水线。

### 已完成

| 章 | 内容 |
|----|------|
| [第0章 机器学习前置](machine-learning/ml-00-math-primer.md) | 兑现 ds-00 留给卷 3 的两张欠条——链式法则与反向传播（计算图、两层网络四条梯度、梯度核对）、梯度下降家族（学习率三种命运、BGD/SGD/mini-batch、梯度方差 ∝1/√B、鞍点）；外加模型评估数学口径（训练目标 vs 评估口径、回归四指标、混淆矩阵四指标、交叉熵=最大似然、偏差-方差 U 曲线、训练/验证/测试三分天下）；综合实战：从零训一个逻辑回归；每节配随堂自测与关键节"本节交付"落点说明 |

### 规划

| 章 | 计划内容 |
|----|------|
| 第1章 sklearn API | estimator 三件套 `fit/predict/score`、`(n, d)` 数据契约、检查器与版本速查 |
| 第2章 特征工程 | 缺失值、编码（one-hot/序号/目标）、缩放与分箱、特征选择 |
| 第3章 线性模型 | 线性/逻辑回归、正则化三兄弟、solver 选型与梯度行为 |
| 第4章 分类 | 概率输出与校准、阈值与不平衡处理 |
| 第5章 模型评估 | 交叉验证、超参数搜索、指标体系与报告规范 |
| 第6章 树与集成 | 决策树、随机森林、梯度提升 |
| 第7章 无监督 | 聚类、降维与异常检测 |
| 第8章 流水线工程化 | `Pipeline`/`ColumnTransformer`、可复现训练与部署 |
| 深水配套 | `ml-XXb` 系列（同卷 2 体例） |

## 卷 4–5：规划中

| 卷                      | 计划章节                                                                                                           |
|-------------------------|--------------------------------------------------------------------------------------------------------------------|
| 卷 4 深度学习           | PyTorch 张量、autograd/GPU、Dataset/Dataloader、训练循环、CNN/RNN、Transformer 架构                                |
| 卷 5 大模型应用         | tokenization/embedding、提示工程、RAG、Agent 工具调用、评估、部署与成本                                            |

## 学习路径

| 目标             | 路径                                        |
|------------------|---------------------------------------------|
| 纯 Python 开发者 | 卷 1 必读核心 → 进阶选修                    |
| 数据分析师       | 卷 1 必读核心 → `ds-00` → 第1–4章（统计推断收口）→ 附录 B 速查 |
| 数学建模 / 工程计算 | 卷 1 必读核心 → `ds-00`（含 0.2.8–0.2.11 数值数学）→ 第5章 → 附录 C 速查；线代记不住翻附录 A |
| 机器学习工程师   | 卷 1 必读核心 → 卷 2 → 卷 3                 |
| 深度学习研究者   | 卷 1 必读核心 → 卷 2 → 卷 3 → 卷 4          |
| LLM 应用开发者   | 卷 1 必读核心 → 卷 2 → 卷 5（深挖可加卷 4） |


## 特点

* **深入底层**：不仅讲 API，更解释实现细节（CPython 哈希表/内存布局/字节码、numpy 内存布局/广播、matplotlib 对象树/坐标变换、autograd 计算图）
* **避开陷阱**：标注常见坑点（浮点精度、浅拷贝、可变默认参数、广播尺寸不匹配等）
* **配套练习**：每章末尾附验证/编程练习
* **版本跟进**：Python 核心内容更新至 3.14，第1章已同步 Python 3.15 与 Python Install Manager（PEP 773）；各卷自带版本速查

## 进度

**卷 1**
* [x] 卷1 第1章 Python 环境搭建
* [x] 卷1 第2章 Python 基础语法
* [x] 卷1 第3章 标准数据类型
* [x] 卷1 第4章 运算符
* [x] 卷1 第5章 条件语句 & 循环语句 & 推导式
* [x] 卷1 第6章 函数：从调用约定到函数式编程
* [x] 卷1 第7章 面向对象编程
* [x] 卷1 第7章配套：设计模式
* [x] 卷1 第8章 异常处理与上下文管理器
* [x] 卷1 第9章 文件 I/O 与序列化
* [x] 卷1 第10章 模块与包管理
* [x] 卷1 第11章 并发与异步编程
* [x] 卷1 第12章 元编程
* [x] 卷1 第13章 标准库精选
* [x] 卷1 第14章 测试与调试
* [x] 卷1 第15章 性能优化与 C 扩展
* [x] 卷1 专题：深浅拷贝
* [x] 卷1 专题：正则表达式
* [x] 卷1 专题：反射机制
* [x] 卷1 附录A Python 3 版本演进宝典

**卷 2**
* [x] 卷2 第0章 数学前置（ds-00-math-primer.md）
* [x] 卷2 第1章 NumPy 数组（ds-01-numpy.md）
* [x] 卷2 第1章配套深水：内存与所有权（ds-01b-numpy-internals-memory.md）
* [x] 卷2 第1章配套深水：计算与后端（ds-01c-numpy-internals-compute.md）
* [x] 卷2 第2章 Pandas（ds-02-pandas.md）
* [x] 卷2 第2章配套深水：存储、对齐与分组的内部实现（ds-02b-pandas-internals.md）
* [x] 卷2 第3章 Matplotlib（ds-03-matplotlib.md）
* [x] 卷2 第3章配套深水：draw 流水线、坐标变换与渲染内核（ds-03b-matplotlib-internals.md）
* [x] 卷2 第4章 SciPy 与统计推断（ds-04-scipy-stats.md）
* [x] 卷2 第4章配套深水：统计推断的内核（ds-04b-scipy-internals.md）
* [x] 卷2 第5章 SciPy 数值方法与建模（ds-05-scipy-modeling.md）
* [x] 卷2 第5章配套深水：数值内核（ds-05b-scipy-numerics-internals.md）
* [x] 卷2 附录A 线性代数速查（ds-appendix-a-linear-algebra-quickref.md）
* [x] 卷2 附录B 概率与数理统计速查（ds-appendix-b-prob-stats-quickref.md）
* [x] 卷2 附录C 建模竞赛速查卡（ds-appendix-c-modeling-quickref.md）

**卷 3**
* [x] 卷3 第0章 机器学习前置（ml-00-math-primer.md）
* [ ] 卷3 第1章 sklearn API 总览
* [ ] 卷3 第2章 特征工程
* [ ] 卷3 第3章 线性模型
* [ ] 卷3 第4章 分类
* [ ] 卷3 第5章 模型评估
* [ ] 卷3 第6章 树与集成
* [ ] 卷3 第7章 无监督
* [ ] 卷3 第8章 流水线工程化
* [ ] 卷3 深水配套册（ml-XXb）

**卷 4**
* [ ] 卷4 深度学习

**卷 5**
* [ ] 卷5 大模型与 AI 应用

