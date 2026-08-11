# Python 教案系列

面向教学的 Python 系统化教案，**即查即用、一针见血**。核心理念：**"肘后备急"**——一本随时翻查的救急手册。

注重**底层原理 > 最佳实践 > 实战练习**。拒绝"见名知意"的浅层认知。

## 系列总览

本仓库以 **5 卷**组织。卷 1 是 Python 语言核心（所有方向的共同地基）；卷 2–5 面向数据科学与 AI 方向，各自独立可查、交叉引用回卷 1。

| 卷 | 主题 | 目录 | 状态 |
|----|------|------|------|
| 卷 1 | Python 语言核心 | `python-core/` | 🔵 进行中（1–7 章完成） |
| 卷 2 | 科学计算与数据分析 | `data-science/` | ⚪ 规划中 |
| 卷 3 | 机器学习 | `machine-learning/` | ⚪ 规划中 |
| 卷 4 | 深度学习 | `deep-learning/` | ⚪ 规划中 |
| 卷 5 | 大模型与 AI 应用 | `llm/` | ⚪ 规划中 |

## 卷 1：Python 语言核心

> 按语言特性线性铺开，深入 CPython 底层（字节码、内存布局、协议机制）。

### 已完成

| 章 | 内容 |
|----|------|
| [第1章 环境搭建](python-core/chapter-01-environment-setup.md) | 编程语言分类、Python 发展史、设计哲学、安装部署、pip/venv/uv、PEP 8 |
| [第2章 基础语法](python-core/chapter-02-basic-syntax.md) | 语句/表达式、缩进/代码块、注释/docstring、标识符/关键字/命名、变量/对象/引用语义、赋值全解、运算符/短路/比较链、print/input/assert |
| [第3章 标准数据类型](python-core/chapter-03-standard-types.md) | 数字（int/float/complex/bool）、字符串、序列（list/tuple/range/bytes）、映射与集合（dict/set/frozenset） |
| [第4章 运算符](python-core/chapter-04-operators.md) | 算术/比较/身份/逻辑/位/成员、赋值全解、优先级、运算符重载协议 |
| [第5章 条件语句 & 循环语句 & 推导式](python-core/chapter-05-control-flow.md) | 真值协议、if/elif/else、match/case、while/for、迭代器协议、推导式、生成器表达式 |
| [第6章 函数：从调用约定到函数式编程](python-core/chapter-06-functions.md) | 函数对象与一等公民、传参语义（call-by-sharing）、封包解包、LEGB 与闭包、lambda 与高阶函数、生成器函数 |
| [第7章 面向对象编程](python-core/chapter-07-oop.md) | 类与实例、方法绑定、四大特性（抽象/封装/继承/多态）、封装协议、MRO 与 super、鸭子类型/ABC/Protocol、特殊方法协议、dataclass/enum/`__slots__` |
| [专题：深浅拷贝](python-core/topic-deep-shallow-copy.md) | 引用语义、is vs ==、浅/深拷贝、`__copy__`/`__deepcopy__` 协议、CPython 内存布局、七大陷阱 |
| [附录A：Python 3 版本演进](python-core/appendix-a-python3-version-evolution.md) | 3.0→3.14 核心 PEP 与 CPython 实现揭秘 |

### 待写

**必读核心**（所有方向必修）：第8章 异常处理与上下文管理器 · 第9章 文件 I/O 与序列化 · 第10章 模块与包管理 · 第13章 标准库精选 · 第14章 测试与调试

**进阶选修**（软件工程向重点，数据/AI 向可缩短）：第11章 并发与异步编程 · 第12章 元编程 · 第15章 性能优化与 C 扩展

## 卷 2–5：规划中

| 卷 | 计划章节 |
|----|---------|
| 卷 2 科学计算与数据分析 | NumPy（数组心智模型/广播/内存布局）、Pandas、Matplotlib、SciPy 与统计、**数学速查附录**（线代/概率/微积分/信息论） |
| 卷 3 机器学习 | sklearn 生态、特征工程、分类/回归/聚类/集成、pipeline 与模型评估 |
| 卷 4 深度学习 | PyTorch 张量、autograd/GPU、Dataset/Dataloader、训练循环、CNN/RNN、Transformer 架构 |
| 卷 5 大模型应用 | tokenization/embedding、提示工程、RAG、Agent 工具调用、评估、部署与成本 |

## 学习路径

| 目标 | 路径 |
|------|------|
| 纯 Python 开发者 | 卷 1 必读核心 → 进阶选修 |
| 数据分析师 | 卷 1 必读核心 → 卷 2 |
| 机器学习工程师 | 卷 1 必读核心 → 卷 2 → 卷 3 |
| 深度学习研究者 | 卷 1 必读核心 → 卷 2 → 卷 3 → 卷 4 |
| LLM 应用开发者 | 卷 1 必读核心 → 卷 2 → 卷 5（深挖可加卷 4） |

## 特点

- **深入底层**：不仅讲 API，更解释实现细节（CPython 哈希表/内存布局/字节码、numpy 内存布局/广播、autograd 计算图）
- **避开陷阱**：标注常见坑点（浮点精度、浅拷贝、可变默认参数、广播尺寸不匹配等）
- **配套练习**：每章末尾附验证/编程练习
- **版本跟进**：Python 核心更新至 3.14；各卷自带版本速查

## 进度

- [x] 卷1 第1章 Python 环境搭建
- [x] 卷1 第2章 Python 基础语法
- [x] 卷1 第3章 标准数据类型
- [x] 卷1 第4章 运算符
- [x] 卷1 第5章 条件语句 & 循环语句 & 推导式
- [x] 卷1 附录A Python 3 版本演进宝典
- [x] 卷1 第6章 函数：从调用约定到函数式编程
- [x] 卷1 第7章 面向对象编程
- [ ] 卷1 第8–15章（必读核心 → 进阶选修）
- [ ] 卷2 科学计算与数据分析
- [ ] 卷3 机器学习
- [ ] 卷4 深度学习
- [ ] 卷5 大模型与 AI 应用
