# Python 教案系列

面向教学的 Python 系统化教案，**即查即用、一针见血**。核心理念：**"肘后备急"**——一本随时翻查的救急手册。

注重**底层原理 > 最佳实践 > 实战练习**。拒绝"见名知意"的浅层认知。

## 系列总览

本仓库以 **5 卷**组织。卷 1 是 Python 语言核心（所有方向的共同地基）；卷 2–5 面向数据科学与 AI 方向，各自独立可查、交叉引用回卷 1。

| 卷   | 主题               | 目录                | 状态                              |
|------|--------------------|---------------------|-----------------------------------|
| 卷 1 | Python 语言核心    | `python-core/`      | ✅ 完成（1–15章 + 3专题 + 1附录） |
| 卷 2 | 科学计算与数据分析 | `data-science/`     | 🚧 进行中（第0–4章完成 + 5 本深水配套） |
| 卷 3 | 机器学习           | `machine-learning/` | ⚪ 规划中                         |
| 卷 4 | 深度学习           | `deep-learning/`    | ⚪ 规划中                         |
| 卷 5 | 大模型与 AI 应用   | `llm/`              | ⚪ 规划中                         |

## 卷 1：Python 语言核心

> 按语言特性线性铺开，深入 CPython 底层（字节码、内存布局、协议机制）。

### 已完成

| 章                                                                              | 内容                                                                                                                                                                                                                                                                                                                                                                                                   |
|---------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [第1章 环境搭建](python-core/py-01-environment-setup.md)                   | 编程语言分类、Python 发展史、设计哲学、安装部署、pip/venv/uv、PEP 8                                                                                                                                                                                                                                                                                                                                    |
| [第2章 基础语法](python-core/py-02-basic-syntax.md)                        | 语句/表达式、缩进/代码块、注释/docstring、标识符/关键字/命名、变量/对象/引用语义、赋值全解、运算符/短路/比较链、print/input/assert                                                                                                                                                                                                                                                                     |
| [第3章 标准数据类型](python-core/py-03-standard-types.md)                  | 数字（int/float/complex/bool）、字符串、序列（list/tuple/range/bytes）、映射与集合（dict/set/frozenset）                                                                                                                                                                                                                                                                                               |
| [第4章 运算符](python-core/py-04-operators.md)                             | 算术/比较/身份/逻辑/位/成员、赋值全解、优先级、运算符重载协议                                                                                                                                                                                                                                                                                                                                          |
| [第5章 条件语句 & 循环语句 & 推导式](python-core/py-05-control-flow.md)    | 真值协议、if/elif/else、match/case、while/for、迭代器协议、推导式、生成器表达式                                                                                                                                                                                                                                                                                                                        |
| [第6章 函数：从调用约定到函数式编程](python-core/py-06-functions.md)       | 函数对象与一等公民、传参语义（call-by-sharing）、封包解包、LEGB 与闭包（含装饰器示例）、lambda 与高阶函数、生成器函数                                                                                                                                                                                                                                                                                  |
| [第7章 面向对象编程](python-core/py-07-oop.md)                             | 类与实例、方法绑定、四大特性（抽象/封装/继承/多态）、封装协议、MRO 与 super、鸭子类型/ABC/Protocol、特殊方法协议与对象生命周期、dataclass/enum/`__slots__`、设计模式（7.9 精简）                                                                                                                                                                                                                       |
| [第7章配套：设计模式全景](python-core/py-07-design-patterns.md)            | GoF 创建型/结构型/行为型模式、SOLID 原则、模式"消亡"对照表、反模式与实战                                                                                                                                                                                                                                                                                                                               |
| [第8章 异常处理与上下文管理器](python-core/py-08-exceptions-context.md)    | 异常对象模型与类层次、try/except/else/finally、异常链、ExceptionGroup/`except*`、EAFP vs LBYL、with 协议与 contextlib、事务式资源管理                                                                                                                                                                                                                                                                  |
| [第9章 文件 I/O 与序列化](python-core/py-09-file-io-serialization.md)      | 分层 IO 体系（RawIO→缓冲→TextIO）、open() 全参数、编码/换行/缓冲、性能基准、随机访问、struct/mmap、pathlib/tempfile、pickle/json 序列化、原子写                                                                                                                                                                                                                                                        |
| [第10章 模块与包管理](python-core/py-10-modules-packages.md)               | import 执行语义与字节码、importlib 流水线（PEP 451）、`__pycache__` 与 PEP 552、自定义 import 钩子、包/相对导入/命名空间包（PEP 420）、循环导入、venv 机制、pyproject.toml 打包（PEP 517/518/621）、wheel/editable（PEP 427/660）、pip/uv 与锁文件、zipapp/PEP 723 部署                                                                                                                                |
| [第11章 并发与异步编程](python-core/py-11-concurrency-async.md)            | 进程/线程/协程三抽象与切换成本、Amdahl 定律、GIL 机制（PEP 703 自由线程）、线程锁/同步原语/`threading.local`、死锁四条件、queue 生产者-消费者、ThreadPoolExecutor/Future、multiprocessing（Pool/spawn/共享内存）、async/await 与事件循环（PEP 342/380/492）、asyncio 实战（gather/超时/Semaphore/Queue/to\_thread）、选型矩阵、并发陷阱与确定性测试                                                    |
| [第12章 元编程](python-core/py-12-metaprogramming.md)                      | 装饰器深潜（语法糖展开/工厂/wraps/类装饰器/栈）、描述符协议（数据 vs 非数据描述符、property/classmethod/staticmethod/`__slots__` 实现）、属性访问完整路径（`__getattr__`/`__getattribute__`）、元类（type 即类、class 创建流程、`__prepare__`/`__init_subclass__`、注册表/单例元类）、`__call__`/`__new__`/`__reduce__` 协议、mini-dataclass/插件注册/声明式字段实战、元编程使用边界                   |
| [第13章 标准库精选](python-core/py-13-stdlib.md)                           | 标准库全景与选型哲学、collections（defaultdict/Counter/deque/ChainMap/bisect/heapq/array）、itertools（惰性组合）、functools（lru\_cache/singledispatch）、datetime/zoneinfo（PEP 615）、math/decimal/random/secrets/statistics、subprocess（shell=False 安全）/shutil/glob、sqlite3（参数化防注入）/csv/configparser/argparse、logging（四件套/轮转/结构化）、typing（PEP 484/585/604）、隐藏宝石速查 |
| [第14章 测试与调试](python-core/py-14-testing-debugging.md)                | 测试哲学与金字塔、TDD、可测试性设计、unittest（断言/生命周期/subTest）、pytest（fixture 注入/parametrize/AST 断言重写）、mock（patch 使用方语义/autospec）、覆盖率与 CI 门禁、pdb 断点调试（breakpoint/post-mortem/faulthandler）、traceback 解读、cProfile/timeit、doctest                                                                                                                            |
| [第15章 性能优化与 C 扩展](python-core/py-15-performance-cext.md)          | 解释器执行模型、五层优化路线图（算法→语言级→向量化→JIT→C）、cProfile/line\_profiler/tracemalloc 进阶、复杂度优化、字节码视角（局部变量/方法绑定/join/内置函数）、3.11+ 特化解释器（PEP 659）、numpy 向量化预告、PyPy/numba、ctypes 调 C 库、Python C API（引用计数/GIL 释放/PyTypeObject）、Cython 类型化、性能回归与 CI、卷 1 全景收官                                                                |
| [专题：深浅拷贝](python-core/py-topic-deep-shallow-copy.md)                        | 引用语义、is vs ==、浅/深拷贝、`__copy__`/`__deepcopy__` 协议、CPython 内存布局、七大陷阱                                                                                                                                                                                                                                                                                                              |
| [专题：正则表达式](python-core/py-topic-regex.md)                                  | 正则与自动机理论、re 模块 API、编译与缓存机制、贪婪/惰性/回溯、环视/分组/标志、灾难性回溯与性能                                                                                                                                                                                                                                                                                                        |
| [专题：反射机制](python-core/py-topic-reflection.md)                                | 内省基础（`type`/`dir`/`isinstance`）、属性访问协议（`getattr` 三剑客/`hasattr` 陷阱/完整查找路径/字节码证据）、`inspect` 工具箱（`signature`/`getsource`/`getmro`/谓词/栈帧）、动态调用与创建（`getattr` 分发/`type` 建类/`importlib`/`eval` 危险区）、反射驱动架构（插件/ORM/序列化/CLI/DI）、元数据反射、代价与边界                                                                                                                              |
| [附录A：Python 3 版本演进](python-core/py-appendix-a-python3-version-evolution.md) | 3.0→3.14 核心 PEP 与 CPython 实现揭秘                                                                                                                                                                                                                                                                                                                                                                  |

### 待写

**卷 1**：✅ 全部完成（必读核心 + 进阶选修 + 3 专题 + 附录A）

**卷 2**：进行中（下一步：第5章 `ds-05-scipy-modeling.md`）。**卷 3–5**：见下方规划。

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

### 待写

| 章 | 内容 |
|----|------|
| `ds-05-scipy-modeling.md` | 第5章 SciPy 数值方法与建模：线性方程组与病态诊断、线性/整数/非线性优化、曲线拟合、插值与数据补全、积分与微分方程、随机模拟与敏感性、图网络与聚类、信号与频域、建模综合实战 |
| `ds-05b-scipy-numerics-internals.md` | 第5章配套深水：LU/QR/SVD 与条件数几何、BLAS/LAPACK 分派、HiGHS 单纯形与内点、KKT、ODE 稳定域与刚性、稀疏存储与迭代法、QMC 序列构造、FFT |
| `ds-appendix-a` / `ds-appendix-b` | 线代 / 概率统计急救卡（回链 ds-00） |
| `ds-appendix-c-modeling-quickref.md` | 建模竞赛速查卡：按"问题类型 → 函数 → 最短可复制代码"（LP/MILP/指派/最短路/最大流/聚类/滤波/FFT/拟合/ODE） |

## 卷 3–5：规划中

| 卷                      | 计划章节                                                                                                           |
|-------------------------|--------------------------------------------------------------------------------------------------------------------|
| 卷 3 机器学习           | sklearn 生态、特征工程、分类/回归/聚类/集成、pipeline 与模型评估                                                   |
| 卷 4 深度学习           | PyTorch 张量、autograd/GPU、Dataset/Dataloader、训练循环、CNN/RNN、Transformer 架构                                |
| 卷 5 大模型应用         | tokenization/embedding、提示工程、RAG、Agent 工具调用、评估、部署与成本                                            |

## 学习路径

| 目标             | 路径                                        |
|------------------|---------------------------------------------|
| 纯 Python 开发者 | 卷 1 必读核心 → 进阶选修                    |
| 数据分析师       | 卷 1 必读核心 → 卷 2（到第4章收口）         |
| 数学建模 / 工程计算 | 卷 1 必读核心 → 卷 2 第0–2章 → 第5章（附录C 速查） |
| 机器学习工程师   | 卷 1 必读核心 → 卷 2 → 卷 3                 |
| 深度学习研究者   | 卷 1 必读核心 → 卷 2 → 卷 3 → 卷 4          |
| LLM 应用开发者   | 卷 1 必读核心 → 卷 2 → 卷 5（深挖可加卷 4） |

> 缺乏数学基础？从卷 2 的 `ds-00-math-primer.md`（数学前置章）起步即可。

## 特点

* **深入底层**：不仅讲 API，更解释实现细节（CPython 哈希表/内存布局/字节码、numpy 内存布局/广播、matplotlib 对象树/坐标变换、autograd 计算图）
* **避开陷阱**：标注常见坑点（浮点精度、浅拷贝、可变默认参数、广播尺寸不匹配等）
* **配套练习**：每章末尾附验证/编程练习
* **版本跟进**：Python 核心更新至 3.14；各卷自带版本速查

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
* [ ] 卷2 第5章 SciPy 数值方法与建模（ds-05-scipy-modeling.md）
* [ ] 卷2 第5章配套深水：数值内核（ds-05b-scipy-numerics-internals.md）
* [ ] 卷2 附录A 线性代数速查
* [ ] 卷2 附录B 概率与数理统计速查
* [ ] 卷2 附录C 建模竞赛速查卡

**卷 3**
* [ ] 卷3 机器学习

**卷 4**
* [ ] 卷4 深度学习

**卷 5**
* [ ] 卷5 大模型与 AI 应用

