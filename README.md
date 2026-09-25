# Python 教案系列

面向教学的 Python 系统化教案，**即查即用、一针见血**。核心理念：**"肘后备急"**——一本随时翻查的救急手册。

注重**底层原理 > 最佳实践 > 实战练习**。拒绝"见名知意"的浅层认知。

## 系列总览

本仓库以 **5 卷**组织。卷 1 是 Python 语言核心（所有方向的共同地基）；卷 2–5 面向数据科学与 AI 方向，各自独立可查、交叉引用回卷 1。

| 卷   | 主题               | 目录                | 状态                              |
|------|--------------------|---------------------|-----------------------------------|
| 卷 1 | Python 语言核心    | `python-core/`      | ✅ 完成（1–15章 + 3专题 + 1附录） |
| 卷 2 | 科学计算与数据分析 | `data-science/`     | 🚧 进行中（第0–2章完成 + 3 本深水配套） |
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

**卷 2**：进行中（下一步：`ds-03-matplotlib.md`）。**卷 3–5**：见下方规划。

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

### 待写

| 章 | 内容 |
|----|------|
| `ds-03-matplotlib.md` | figure/axes 模型、统计图、seaborn |
| `ds-04-scipy-stats.md` | 概率分布、假设检验、优化 |
| `ds-appendix-a` / `ds-appendix-b` | 线代 / 概率统计急救卡（回链 ds-00） |

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
| 数据分析师       | 卷 1 必读核心 → 卷 2                        |
| 机器学习工程师   | 卷 1 必读核心 → 卷 2 → 卷 3                 |
| 深度学习研究者   | 卷 1 必读核心 → 卷 2 → 卷 3 → 卷 4          |
| LLM 应用开发者   | 卷 1 必读核心 → 卷 2 → 卷 5（深挖可加卷 4） |

> 缺乏数学基础？从卷 2 的 `ds-00-math-primer.md`（数学前置章）起步即可。

## 特点

* **深入底层**：不仅讲 API，更解释实现细节（CPython 哈希表/内存布局/字节码、numpy 内存布局/广播、autograd 计算图）
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
* [ ] 卷2 第3章 Matplotlib（ds-03-matplotlib.md）
* [ ] 卷2 第4章 SciPy 与统计（ds-04-scipy-stats.md）
* [ ] 卷2 附录A 线性代数速查
* [ ] 卷2 附录B 概率与数理统计速查

**卷 3**
* [ ] 卷3 机器学习

**卷 4**
* [ ] 卷4 深度学习

**卷 5**
* [ ] 卷5 大模型与 AI 应用

