# 第1章 Python 环境搭建

> **学习目标**：理解编程语言的本质与分类，掌握 Python 的设计哲学与核心特性，独立完成 Python 开发环境的搭建，并建立正确的工程习惯。

---

## 1.1 认识编程语言

在你写下第一行 Python 代码之前，有一个问题值得先回答：**编程语言到底是什么？**

### 1.1.1 什么是编程语言

编程语言是人与计算机之间的**通信协议**——人类用它可以描述计算逻辑，计算机将它翻译为机器指令并执行。这个"翻译"机制，将编程语言分为两大阵营。

#### 从机器语言到高级语言

```
第一代：机器语言
  10110000 01100001          ← CPU 直接执行，但人类几乎不可读

第二代：汇编语言
  MOV AL, 61h               ← 助记符替代二进制，但仍是面向硬件的

第三代：高级语言（C, Pascal, BASIC）
  printf("hello");           ← 接近人类思维方式，需要编译器翻译

第四代：声明式/领域语言（SQL, MATLAB）
  SELECT * FROM users;       ← 描述"做什么"，而非"怎么做"
```

**Python 属于第三代高级语言**，但它在设计上大量吸收了第四代语言的声明式思想——这让它读起来像"可执行的伪代码"。

#### 编译型 vs 解释型

这是编程语言最根本的分类维度之一：

| 特性 | 编译型（C, Rust, Go） | 解释型（Python, Ruby, JS*） |
|------|---------------------|---------------------------|
| 翻译方式 | 一次性全量编译为机器码 | 逐行解释执行 |
| 执行前步骤 | `源代码 → 编译器 → 可执行文件` | `源代码 → 解释器 → 即时执行` |
| 运行速度 | 快（直接执行机器码） | 慢（解释器有开销） |
| 开发速度 | 慢（编译-运行-调试循环） | 快（改完就跑） |
| 跨平台 | 需要为每个平台编译 | 一次编写，到处运行（只要有解释器） |
| 典型场景 | 操作系统、游戏引擎、嵌入式 | Web 后端、数据科学、脚本自动化 |

> \* 现代 JavaScript 引擎（V8、SpiderMonkey）使用 JIT 编译，实际上已非纯解释执行，这里按传统分类简化处理。

**Python 的实际情况比"解释型"这个标签更复杂**：CPython 先将源码编译为字节码（`.pyc`），再由虚拟机执行字节码。这是一种"半编译-半解释"的混合模型——接近 Java 的 JVM 架构，但省去了显式编译步骤。

```
Python 执行流程：
  .py 源码 → [编译器] → .pyc 字节码 → [PVM (Python 虚拟机)] → 机器执行
```

> **工程现实**：对新手而言，"Python 是解释型语言"这句话够用。但当你开始关注性能时，你需要知道 PyPy（JIT 编译）、Cython（编译为 C 扩展）、Numba（LLVM JIT）等工具让 Python 可以在特定场景下接近甚至达到编译型语言的性能。

#### 静态类型 vs 动态类型

另一个关键分类维度：

```python
# Python：动态类型 + 强类型
x = 42           # x 的类型是 int，但不需要声明
x = "hello"      # x 现在可以是 str——类型随值而变（动态类型）
x + 1            # TypeError: str + int 不允许（强类型——不会隐式"转换"）

# C：静态类型 + 弱类型
int x = 42;      // x 的类型在编译时确定，不可改变
char* y = "hi";
x + *y;          // 可以！指针被隐式转为整数（弱类型）
```

| 类型系统 | 示例语言 | 含义 |
|---------|---------|------|
| 静态 + 强 | Rust, Java, Haskell | 编译时确定类型，禁止不安全转换 |
| 静态 + 弱 | C, C++ | 编译时确定类型，允许隐式转换 |
| 动态 + 强 | **Python**, Ruby, Elixir | 运行时确定类型，禁止不安全转换 |
| 动态 + 弱 | JavaScript, PHP | 运行时确定类型，允许隐式转换 |

Python 的**动态 + 强类型**组合意味着：你不需要声明类型（开发快），但类型错误不会悄悄发生（安全）。

### 1.1.2 Python 的起源与发展

#### 创世纪：1989 年的圣诞节项目

**Guido van Rossum**，荷兰程序员，在 1989 年圣诞节期间开始开发 Python。当时他在荷兰国家数学与计算机科学研究中心（CWI）工作，参与 ABC 语言项目——一种面向教学设计的编程语言。ABC 虽然优雅，但缺乏文件 I/O、异常处理等实用功能。Guido 的目标是：**保 ABC 的可读性，加 C 的实用能力。**

"Python"这个命名来自英国喜剧团体 Monty Python（蒙提·派森），而非蟒蛇——这就是为什么 Python 文档和社区中经常出现蒙提·派森的彩蛋（如 `spam` 和 `eggs` 作为示例变量名）。

#### 关键里程碑

| 年份 | 版本 | 里程碑 |
|------|------|--------|
| 1991 | 0.9.0 | 首次公开发布（alt.sources Usenet 新闻组） |
| 1994 | 1.0 | 函数式编程工具（lambda, map, filter, reduce） |
| 2000 | 2.0 | 列表推导式、垃圾回收（循环检测）、Unicode 支持 |
| 2001 | 2.2 | 新式类（统一类型/类体系）、迭代器、生成器 |
| 2008 | 3.0 | **不兼容重写**——解决长期积累的设计缺陷 |
| 2015 | 3.5 | `async`/`await` 异步编程、函数类型注解（PEP 484） |
| 2016 | 3.6 | f-string、变量注解（PEP 526）、`secrets` 模块、字典保序（实现层面） |
| 2018 | 3.7 | 数据类、字典保序正式成为语言规范 |
| 2019 | 3.8 | 海象运算符 `:=`、位置参数 `/` |
| 2020 | 3.9 | 字典合并运算符 `|`、`str.removeprefix/removesuffix` |
| 2021 | 3.10 | 结构化模式匹配（`match/case`） |
| 2022 | 3.11 | 平均 25% 提速（Faster CPython 项目） |
| 2023 | 3.12 | 子解释器（PEP 684）、每个解释器独立 GIL |
| 2024 | 3.13 | **自由线程**（无 GIL 实验性）、**JIT 编译器**（实验性）、改进 REPL |
| 2025 | 3.14 | 注解的延迟求值（PEP 649）、性能持续提升、错误信息改进 |

> **Python 3.13（2024）引入两个历史性变更**：可选的自由线程模式去掉 GIL（全局解释器锁），以及基于 copy-and-patch 的 JIT 编译器。这是 Python 诞生三十余年来最激进的变化。**Python 3.14（2025）是当前最新稳定版**，带来了注解的延迟求值（PEP 649）等改进——如果你学习 Python，3.14 是推荐的起点。

#### Python Software Foundation (PSF)

Python 的知识产权归属于 **Python Software Foundation**（Python 软件基金会），一个成立于 2001 年的非营利组织。PSF 持有 Python 商标，管理社区基础设施（PyPI、python.org），主办 PyCon 大会，并通过赞助和拨款支持 Python 生态发展。

**Guido 的角色变迁**：
- 1990–2018：**BDFL**（Benevolent Dictator For Life，终身仁慈独裁者）——拥有最终决策权
- 2018 年 7 月：宣布退出 BDFL 角色（因 PEP 572 海象运算符争论），Python 转入**指导委员会**治理模式
- 2019–至今：指导委员会由 5 名核心开发者组成，每届选举产生

### 1.1.3 Python 的设计哲学

Guido 将 Python 的设计原则浓缩为 `import this`——在任意 Python 解释器中输入即可查看。

```python
>>> import this
The Zen of Python, by Tim Peters

Beautiful is better than ugly.
Explicit is better than implicit.         # 显式优于隐式
Simple is better than complex.            # 简单优于复杂
Complex is better than complicated.       # 复杂优于杂乱
Flat is better than nested.               # 扁平优于嵌套
Sparse is better than dense.              # 稀疏优于密集
Readability counts.                       # 可读性至上
Special cases aren't special enough to break the rules.
Although practicality beats purity.       # 务实胜过纯粹
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
```

这 19 条原则可以提炼为三个核心：

**1. 可读性至上（Readability counts）**

Python 用**缩进定义代码块**——这不是为了省 `{}`，而是强迫代码结构和视觉结构一致。没有缩进的 Python 代码是语法错误，这使得 Python 代码天然比其他语言更整洁。

```python
# 这是合法的 Python——视觉结构和逻辑结构完全一致
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
else:
    grade = 'C'
```

**2. 只有一种显而易见的方法（One obvious way）**

这与 Perl 的 TIMTOWTDI（There Is More Than One Way To Do It）形成鲜明对比。Python 社区偏好收敛到最佳实践，而非提供无穷多种等价写法。这也是 Python 代码在不同开发者之间高度一致的原因。

```python
# 判断是否为空序列——只有一种推荐写法
if not items:           # Pythonic ✓
    ...

if len(items) == 0:     # Unpythonic ✗——虽然也工作
    ...
```

**3. Batteries Included（自带电池）**

Python 标准库极其丰富——HTTP 客户端、JSON 解析、正则表达式、电子邮件、SQLite 数据库、XML 处理、日志系统……无需安装任何第三方包就能完成大量实际工作。这降低了新手的学习门槛，因为你不需要在学语言的同时学包管理。

### 1.1.4 Python 的核心特性

#### 动态类型 + 强类型

前面已经示例。这里补充一个重要的工程后果：

```python
def greet(name):
    return f"Hello, {name}"

# 你可以传入任何类型——运行时才检查
greet("Alice")      # 正常
greet(42)           # 也正常——f-string 接受任何对象
greet(None)         # 正常——变成 "Hello, None"

# 但如果函数内部做了字符串操作：
def shout(name):
    return name.upper() + "!"

shout("Alice")      # "ALICE!"
shout(42)           # AttributeError: 'int' object has no attribute 'upper'
```

这种"运行时才暴露类型错误"的特性，推动了 Python 3.5 引入**类型注解**（PEP 484）和 `mypy`/`pyright` 等静态类型检查器的兴起——在不改变动态类型本质的前提下，获得静态检查的安全网。

```python
def greet(name: str) -> str:          # 类型注解（运行时完全忽略）
    return f"Hello, {name}"

greet(42)  # mypy 会在不执行代码的情况下报错：Argument 1 has incompatible type "int"
```

#### 一切皆对象

在 Python 中，**一切都是对象**——包括整数、字符串、函数、类、模块、甚至类型本身。

```python
>>> isinstance(42, object)
True
>>> isinstance("hello", object)
True
>>> isinstance(print, object)
True
>>> isinstance(int, object)     # 类型本身也是对象
True
>>> type(int)
<class 'type'>                   # 类型的类型是 type（元类）
```

这意味着：

```python
# 函数可以作为参数传递
sorted(words, key=str.lower)

# 函数可以嵌套定义（闭包）
def make_multiplier(n):
    def multiplier(x):
        return x * n
    return multiplier

# 类可以在运行时动态创建
MyClass = type('MyClass', (object,), {'x': 42})
```

#### 自动内存管理

Python 使用**引用计数 + 标记清除（循环检测）**实现垃圾回收：

```python
import sys

a = [1, 2, 3]
sys.getrefcount(a)      # 2（a 变量 + getrefcount 参数）

b = a
sys.getrefcount(a)      # 3

del b
sys.getrefcount(a)      # 2

# 循环引用——引用计数无法处理的场景
lst = []
lst.append(lst)         # lst 指向自身
del lst                 # 引用计数仍是 1（自己引用自己）→ 由 GC 的循环检测器回收
```

> **工程知识**：CPython 的 `del` 不直接调用析构函数——它只是减少引用计数。对象在引用计数归零时才被回收（`__del__` 被调用）。"循环引用导致内存泄漏"是 Python 新手到中级的第一个认知升级点。

#### 鸭子类型

> "If it looks like a duck, swims like a duck, and quacks like a duck, then it probably is a duck."
> —— James Whitcomb Riley

Python 不关心对象的类型是什么，只关心它**能做**什么：

```python
def read_data(source):
    return source.read()    # 只要 source 有 read() 方法，就能工作

# 这些都可以传入 read_data()：
import io
data_file = open("data.txt")        # 文件对象有 read()
data_stream = io.StringIO("hello")  # 内存流也有 read()
data_bytes = b"world"               # bytes 对象……没有 read() → AttributeError
```

这与 Java/C++ 等需要声明接口或基类的语言形成对比：Python 依赖**运行时行为**而非**编译时类型**来保证兼容性。优点是灵活（不需要为了复用而引入复杂的类型层级），缺点是在大型项目中可能导致难以追踪的运行时错误——这正是类型注解和静态检查器试图弥补的。

#### 缩进即语法

Python 可能是唯一将缩进作为语法规则的工业级语言。这引发过大量争议，但最终被证明是设计上的成功——它消除了 `{ }` 风格争论（K&R vs Allman vs ...），让所有 Python 代码看起来像同一个人写的。

**缩进规则**：
- 必须使用**一致的**缩进（全空格或全制表符，推荐 4 个空格）
- PEP 8 强制：**空格优先**，如果用制表符也要保持与空格等价
- 同一代码块的缩进量必须严格一致
- 缩进量可以是 1～N 个空格（但必须保持一致），PEP 8 建议 4

> **实际教训**：混用 Tab 和空格是 Python 最常见的隐形 bug 来源——代码"看起来"对齐了，但解释器认为缩进不一致。用编辑器的"显示空白字符"功能可以避免这类问题。

### 1.1.5 Python 的应用生态

Python 不是"什么都能做"的银弹，但它的应用广度在通用语言中无出其右：

| 领域 | 代表性库/框架 | Python 的地位 |
|------|-------------|--------------|
| **数据科学 / AI** | NumPy, Pandas, PyTorch, TensorFlow, scikit-learn | 🏆 绝对霸主 |
| **Web 后端** | Django, FastAPI, Flask | 🥈 与 JS/Go/Java 并列 |
| **自动化 / DevOps** | Ansible, SaltStack, Fabric | 🏆 第一选择 |
| **科学计算** | SciPy, SymPy, AstroPy, BioPython | 🏆 替代 MATLAB |
| **桌面 GUI** | PyQt/PySide, Tkinter, wxPython | 可用但不主流 |
| **游戏开发** | Pygame, Godot (GDScript) | 入门/原型，非工业级 |
| **嵌入式 / IoT** | MicroPython, CircuitPython | 快速增长 |
| **教育** | 全球高校首选入门语言 | 🏆 无可争议 |

**Python 的边界**：
- ❌ **不适合**：操作系统内核、高性能游戏引擎、实时硬约束系统、移动端原生开发
- ⚠️ **勉强可用**：大型桌面应用、移动 App（Kivy / BeeWare 可用但不成熟）
- ✅ **最佳选择**：数据分析、机器学习、Web API、自动化脚本、科学计算

### 1.1.6 Python 2 vs Python 3

这是一个绕不开的历史话题。2008 年发布的 Python 3.0 **故意不兼容** Python 2——这在编程语言史上是极其罕见且痛苦的决策。

**为什么必须不兼容？**

Python 2 积累了大量设计债务：
1. `print` 是语句而非函数——不灵活
2. `str` 是字节串，`unicode` 是字符——混乱且是 bug 温床
3. `range()` 返回列表，`xrange()` 返回迭代器——不一致
4. 整数除法 `1/2` 返回 `0`——违反直觉
5. `class` 语法和新式类/旧式类分裂
6. `input()` 存在代码注入安全漏洞（`eval` 用户输入）

**关键差异速览**：

| 特性 | Python 2 | Python 3 |
|------|--------|--------|
| `print` | 语句：`print "hello"` | 函数：`print("hello")` |
| 整数除法 | `5 / 2 = 2` | `5 / 2 = 2.5` |
| `range` | 返回 `list`（内存占用大） | 返回不可变序列对象（惰性） |
| 字符串 | ASCII 字节串 | Unicode 字符串 |
| 异常 | `except ValueError, e:` | `except ValueError as e:` |
| `input` | `eval(raw_input())`（危险！） | `str(input())`（安全） |
| `exec` | 语句 | 函数 |
| `xrange` | 存在 | 被 `range` 取代 |
| 元类 | `__metaclass__` | `metaclass=...` |

**当前状态（2024）**：Python 2.7 已于 2020 年 1 月 1 日正式停止维护。除非维护遗留系统，否则绝不应该使用 Python 2。现在学习 Python，默认就是 Python 3。

### 1.1.7 Python 的实现

"Python"指的首先是**语言规范**，而非特定的解释器。多个团队实现了兼容该规范的解释器：

```
CPython     ← 参考实现，用 C 写成，你下载的 python.org 上的那个
  ├── 最广泛使用，生态保证
  ├── 全局解释器锁（GIL）——多线程受限（3.13 开始实验性去除）
  └── 3.13 新增实验性 JIT

PyPy        ← 用 RPython 写成的 JIT 编译器
  ├── 长运行脚本/服务可快 4-7 倍
  ├── 内存占用更低
  └── 缺点：C 扩展兼容性有限，冷启动慢

Jython      ← 运行在 JVM 上
  └── 与 Java 生态无缝互操作，适合 Java 企业环境

IronPython  ← 运行在 .NET CLR 上
  └── 与 C#/.NET 生态互操作

MicroPython ← 用于微控制器（ESP32、RP2040 等）
  └── 精简实现，可用在 256KB Flash 的芯片上

Pyodide     ← 编译到 WebAssembly
  └── 在浏览器中运行 Python（JupyterLite 的基础）
```

> **学习建议**：从 CPython 开始。99% 的教材、教程和第三方库都基于 CPython。当你遇到性能瓶颈时，再考虑 PyPy 或 Cython，而不是一开始就追逐替代实现。

---

## 1.2 Python 环境及开发工具的安装与使用

### 1.2.1 Python 的安装

#### Windows

**方法一：从 python.org 下载安装包（推荐）**

1. 访问 https://www.python.org/downloads/，下载最新稳定版（如 Python 3.14.x）
2. **运行安装程序时，务必勾选 "Add python.exe to PATH"**（默认未勾选！）
3. 选择 "Install Now" 或 "Customize installation"
4. 如果自定义安装，建议勾选 `pip`、`tcl/tk and IDLE`、`Python test suite`、`py launcher`

**安装后验证**（在命令提示符或 PowerShell 中）：

```powershell
python --version
# Python 3.14.0
pip --version
# pip 24.x from C:\Users\...\AppData\...
```

**方法二：Microsoft Store**

微软商店提供受控安装，自动加入 PATH 且自动更新。但 Store 版偶有权限限制（如 `pip install --user` 行为略有不同），开发中不如官网安装灵活。

> **Windows 多版本管理**：如需在多个 Python 版本间切换，使用 `py` 启动器（随官网安装包自带）：
>
> ```powershell
> py -3.13 --version        # 指定 3.13
> py -3.14 --version        # 指定 3.14
> py -0                     # 列出所有已安装版本
> ```

#### macOS

**方法一：官网安装包**

同 Windows，访问 python.org 下载 `.pkg` 安装程序，按照向导操作。

**方法二：Homebrew（开发者推荐）**

```bash
brew install python@3.14
brew link python@3.14    # 设为默认
```

Homebrew 的优势在于可以用 `brew upgrade` 统一管理所有工具链的版本。

> **macOS 注意事项**：系统自带的 `/usr/bin/python3` 是 Xcode Command Line Tools 提供的存根（stub），用于触发安装。请**不要删除或替换它**，也不要依赖它做实际开发。始终使用你显式安装的 Python。

#### Linux

大多数 Linux 发行版已预装 Python 3（通常不是最新版）。

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip

# 源码编译（当你需要特定版本或自定义编译选项）
wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
tar xzf Python-3.14.0.tgz
cd Python-3.14.0
./configure --enable-optimizations --prefix=/usr/local
make -j$(nproc)
sudo make altinstall     # 用 altinstall 而非 install——避免覆盖系统 python3
```

> ⚠️ **绝不要替换系统 Python**：Linux 系统的很多工具（包管理器、系统脚本）依赖特定版本的 Python。使用 `make altinstall` 或将其装到 `/usr/local` 以避免破坏系统。

#### 多版本管理工具详析

当项目需要不同 Python 版本时，多版本管理器让版本切换零摩擦：

| 工具 | 平台 | 特点 |
|------|------|------|
| **pyenv** | macOS/Linux (Windows 用 pyenv-win) | 最成熟，按目录自动切换版本 |
| **uv** | 全平台 | Rust 写成，极快，Python 版本管理 + 包管理一体 |
| **conda** | 全平台 | 不仅管理 Python 版本，还管理非 Python 依赖（C 库等） |
| **asdf** | macOS/Linux | 通用多语言版本管理器（通过插件支持 Python） |

**uv 入门**（2024 年爆火的新秀——由 Ruff 作者打造）：

```bash
# 安装 uv
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows:
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 安装指定 Python 版本
uv python install 3.14
uv python install 3.12

# 用指定版本创建虚拟环境
uv venv --python 3.12
```

**pyenv 入门**：

```bash
# 安装 pyenv 后
pyenv install 3.14.0
pyenv install 3.12.7

# 全局切换
pyenv global 3.12.7

# 项目级切换（写入 .python-version 文件）
cd my-project
pyenv local 3.14.0       # 生成 .python-version 文件，进入该目录自动切换
```

### 1.2.2 Python 解释器的工作方式

#### 交互模式（REPL）

REPL = Read-Eval-Print Loop（读取-求值-打印-循环）。在终端输入 `python` 即可进入：

```python
$ python
Python 3.14.0 (main, Oct  7 2024, 10:00:00) [GCC 14.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> 2 + 3
5
>>> name = "Python"
>>> f"Hello, {name}!"
'Hello, Python!'
>>> import math
>>> math.sqrt(144)
12.0
>>> exit()           # 或 Ctrl+D (macOS/Linux) / Ctrl+Z+Enter (Windows)
```

REPL 是 Python 的**超级能力**——你可以在不创建文件的情况下立即测试任何代码片段。这在调试、探索 API、学习新库时价值巨大。

> **Python 3.14 的新 REPL**：支持多行编辑、语法高亮、括号匹配、命令历史搜索等——更像 IPython 了。

**`python -i`：运行脚本后进入交互模式**

```bash
$ python -i script.py
# 脚本执行完毕后，所有变量、函数都留在命名空间中，可以交互式检查
>>> dir()        # 查看当前所有名字
>>> type(x)      # 查看变量类型
```

这是调试时极其有用的技巧。

#### 脚本模式

将代码写入 `.py` 文件，然后执行：

```bash
$ python hello.py
Hello, World!
$ python -m http.server 8000     # 运行标准库模块
$ python -c "print(2 ** 100)"    # 从命令行执行单行代码
```

**Python 常用命令行参数**：

| 参数 | 含义 |
|------|------|
| `-c <code>` | 执行命令行中的代码 |
| `-m <module>` | 以脚本方式运行模块（如 `-m pip`, `-m venv`） |
| `-i` | 执行脚本后进入交互模式 |
| `-v` | 详细输出（显示模块导入过程） |
| `-O` | 优化模式（去除 `assert` 和 `__debug__`） |
| `-B` | 禁止写入 `.pyc` 文件 |
| `-u` | 无缓冲的 stdout/stderr（调试时有用） |
| `-h` / `--help` | 查看帮助 |
| `-V` / `--version` | 打印版本号 |

#### Shebang（Unix）

在脚本第一行标注解释器路径，使脚本可以直接执行：

```python
#!/usr/bin/env python3
"""My script."""

import sys

def main():
    print(f"Arguments: {sys.argv[1:]}")

if __name__ == "__main__":
    main()
```

```bash
$ chmod +x script.py
$ ./script.py arg1 arg2
Arguments: ['arg1', 'arg2']
```

`#!/usr/bin/env python3` 比 `#!/usr/bin/python3` 更好——因为它通过 `env` 在 `PATH` 中查找 `python3`，兼容 pyenv/virtualenv 等环境管理工具。

### 1.2.3 包管理：pip

`pip`（"Pip Installs Packages"）是 Python 官方包管理工具。它从 **PyPI**（Python Package Index，`pypi.org`）下载和安装第三方包。

#### 核心命令

```bash
# 安装包
pip install requests            # 安装最新版
pip install requests==2.31.0    # 安装精确版本
pip install 'requests>=2.28'    # 安装满足版本约束的版本
pip install requests django     # 一次安装多个包

# 卸载
pip uninstall requests          # 卸载（需确认）

# 升级
pip install --upgrade requests  # 升级到最新
pip install -U pip              # pip 自升级

# 信息查看
pip list                        # 列出已安装的包
pip show requests               # 显示某个包的详细信息
pip freeze                      # 输出精确版本列表（用于 requirements.txt）

# 从文件安装
pip install -r requirements.txt  # 批量安装

# 缓存管理
pip cache list                  # 列出下载缓存
pip cache purge                 # 清除缓存（释放磁盘空间）
```

#### `requirements.txt`

这是 Python 项目最传统的依赖声明方式：

```
# requirements.txt
requests>=2.28,<3.0
django==5.0.0
numpy>=1.26
# 开发依赖（在 dev-requirements.txt 中单独管理）
pytest>=8.0
black>=24.0
```

```bash
pip install -r requirements.txt
```

**`pip freeze` vs `pip list` 的工程含义**：

- `pip freeze`：输出 `包名==精确版本`，适合生成 `requirements.txt`
- `pip list`：输出已安装包和版本，适合人类查看

```bash
$ pip freeze
certifi==2024.8.30
charset-normalizer==3.4.0
idna==3.10
requests==2.32.3
urllib3==2.2.3
```

#### PyPI 与镜像

**PyPI**（https://pypi.org）是 Python 官方包仓库。`pip` 默认从 PyPI 下载。

**国内镜像**（加速下载）：

| 镜像源 | URL |
|--------|-----|
| 清华大学 | `https://pypi.tuna.tsinghua.edu.cn/simple/` |
| 阿里云 | `https://mirrors.aliyun.com/pypi/simple/` |
| 中科大 | `https://pypi.mirrors.ustc.edu.cn/simple/` |
| 华为云 | `https://mirrors.huaweicloud.com/repository/pypi/simple/` |

```bash
# 临时使用镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ requests

# 永久配置镜像（Linux/macOS: ~/.pip/pip.conf，Windows: %APPDATA%\pip\pip.ini）
# [global]
# index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 1.2.4 虚拟环境

#### 为什么需要虚拟环境？

Python 的 `pip install` 默认将包安装到**全局** site-packages 目录。这意味着：

```
项目 A 需要 requests==2.28.0
项目 B 需要 requests==2.31.0
       ↓
全局冲突！两个项目共享同一个 Python 环境。
```

虚拟环境是**每个项目专用的隔离 Python 环境**——每个环境有自己的 site-packages，互不干扰。

#### venv（Python 标准库，3.3+）

`venv` 是 Python 的内置工具，零依赖，推荐作为默认选择。

```bash
# 创建虚拟环境
python -m venv myenv

# 目录结构
myenv/
├── bin/ (或 Scripts/ on Windows)
│   ├── python          # 该环境的 Python 解释器（软链接/copy）
│   ├── pip
│   └── activate        # 激活脚本
├── lib/
│   └── python3.14/
│       └── site-packages/  # 该环境专属的包安装位置
└── pyvenv.cfg           # 配置文件

# 激活虚拟环境
# Linux/macOS:
source myenv/bin/activate

# Windows (cmd):
myenv\Scripts\activate.bat

# Windows (PowerShell):
myenv\Scripts\Activate.ps1

# git-bash (Windows):
source myenv/Scripts/activate

# 激活后，提示符会显示环境名
(myenv) $ python --version
(myenv) $ pip list          # 只看到这个环境安装的包
(myenv) $ deactivate        # 退出虚拟环境
```

**激活后的实际变化**：
- `PATH` 被修改：`myenv/bin`（或 `Scripts`）插到最前面
- `VIRTUAL_ENV` 环境变量被设置为虚拟环境路径
- `python` 和 `pip` 命令指向该环境内的版本
- `pip install` 安装到该环境而非全局

#### pipx：全局隔离安装 CLI 工具

如果你需要全局使用某个 Python CLI 工具（如 `black`、`ruff`、`httpie`），但不想污染全局 Python 环境：

```bash
pipx install black       # 为 black 创建独立环境，把 entry point 暴露到全局 PATH
pipx install ruff
```

`pipx` 为每个工具创建专属的隔离虚拟环境，避免依赖冲突。

#### conda / Miniconda

conda 是 Anaconda 公司的跨语言包管理器，广泛应用于数据科学领域：

```bash
conda create -n myenv python=3.12     # 创建环境（指定 Python 版本）
conda activate myenv                  # 激活
conda install numpy pandas            # 安装包（conda 会自动处理非 Python 依赖）
conda env export > environment.yml    # 导出环境
conda deactivate                      # 退出
```

**conda vs pip/venv**：
- conda 同时管理 Python 版本和非 Python 的二进制依赖（如 BLAS、CUDA、ffmpeg）
- conda 的包来自 conda-forge（而非 PyPI），由维护者预先编译
- 如果你的工作涉及 NumPy/PyTorch/TensorFlow 等有 C 扩展的科学计算库，conda 的二进制依赖管理是很大的优势

#### 现代工程实践：uv（2024 推荐关注）

`uv` 是一个用 Rust 写成的 Python 包和项目管理器，一个工具统一 `pip`、`pip-tools`、`pipx`、`pyenv`、`venv`：

```bash
# 创建项目（生成 pyproject.toml + .venv）
uv init my-project
cd my-project

# 添加依赖
uv add requests          # 安装 + 写入 pyproject.toml + 锁定 uv.lock

# 运行脚本（自动使用 .venv）
uv run python app.py

# 同步环境（根据 uv.lock 精确还原）
uv sync

# 安装 CLI 工具（类似 pipx）
uv tool install ruff
```

> **权衡**：`uv` 的速度远超 pip（10-100x），但生态尚在快速演进中。如果你是学习阶段，从 `venv + pip` 开始完全可以；当你需要管理多个项目、或对安装速度有要求时，`uv` 值得投入。

#### 虚拟环境的最佳实践

1. **每个项目一个虚拟环境**——绝不全局安装项目依赖
2. **虚拟环境放在项目目录外**（普通 venv）或项目目录内的 `.venv` 目录中（`.venv/` 约定，`uv` 默认）
3. **将虚拟环境路径加入 `.gitignore`**——不提交虚拟环境本身
4. **提交依赖描述文件**（`requirements.txt` 或 `pyproject.toml` / `uv.lock`）
5. **锁定版本**——`pip freeze > requirements.txt` 或 `uv.lock` 确保团队和部署环境依赖一致

### 1.2.5 开发工具

#### VS Code（强烈推荐）

VS Code 加上 Python 扩展是目前最流行的 Python 开发环境——免费、跨平台、启动快、生态丰富。

**安装与配置**：

1. 从 https://code.visualstudio.com 下载安装 VS Code
2. 打开 VS Code，按 `Ctrl+Shift+X` 打开扩展市场
3. 搜索并安装 **Python**（Microsoft 官方，标识为 ms-python.python）
4. 搜索并安装 **Pylance**（语言服务器——提供类型检查、自动补全、跳转定义等）
5. （可选）安装 **Ruff** 扩展（极速 linting + 格式化）

**核心功能**：

| 功能 | 快捷键 | 说明 |
|------|--------|------|
| 命令面板 | `Ctrl+Shift+P` | 搜索和执行任何 VS Code 命令 |
| 运行 Python 文件 | `Ctrl+F5` | 运行当前文件（不调试） |
| 调试 | `F5` | 启动调试（在 `.vscode/launch.json` 中配置） |
| 格式化文档 | `Shift+Alt+F` | 用配置的 formatter 格式化代码 |
| 转到定义 | `F12` | 跳转到函数/类/变量的定义 |
| 查找引用 | `Shift+F12` | 查找所有引用位置 |
| 重命名符号 | `F2` | 安全地重命名（更新所有引用） |
| 集成终端 | `` Ctrl+` `` | 打开内置终端 |

**.vscode/settings.json**（项目级推荐配置）：

```json
{
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit"
        }
    },
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

#### PyCharm（重型 IDE）

JetBrains 开发的 PyCharm 是功能最完整的 Python IDE：

- **Community Edition**（免费）：支持纯 Python 开发、调试、测试
- **Professional Edition**（付费）：额外支持 Web 框架（Django/Flask）、数据库工具、远程开发、科学工具

**适用场景**：如果你来自 Java/C# 世界、需要重量级重构工具、或开发大型 Django 项目——PyCharm 的深度功能优于 VS Code。对于大多数学习和小中型项目，VS Code 足够且更轻量。

#### Jupyter Notebook / JupyterLab

Jupyter 是**交互式文学编程**（literate programming）环境——将代码、输出、Markdown 文档、图表混合在同一个文档中。它是数据科学和数据探索的事实标准。

```bash
pip install jupyterlab
jupyter lab      # 在浏览器中打开 JupyterLab
```

或使用 VS Code 中的 Jupyter 扩展——在 `.ipynb` 文件中直接编辑。

> **何时用 Jupyter 而非 .py 文件**：当你需要探索未知数据、可视化每一步的计算结果、编写数据分析报告时，Jupyter 是正确选择。当你在写一个需要版本控制、自动化部署、复用的生产代码时，`.py` 文件是正确选择。

#### IDLE（Python 内置）

IDLE 是 Python 自带的简易 IDE——不需要任何安装，打开 `python -m idlelib` 或从开始菜单启动。它适合**最初级的练习**，但不适合真实项目开发。

### 1.2.6 第一个 Python 程序

#### Hello, World!

创建 `hello.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""My first Python program — the ritual."""

def main():
    """Entry point."""
    name = input("What's your name? ")
    print(f"Hello, {name}! Welcome to Python.")

if __name__ == "__main__":
    main()
```

#### 运行它的三种方式

```bash
# 方式 1：通过 Python 解释器
$ python hello.py

# 方式 2：作为模块运行（无需 .py 后缀，用 . 代替 /）
$ python -m hello

# 方式 3：直接执行（需要 shebang + chmod +x，仅 Unix）
$ ./hello.py
```

#### 逐行解析

```python
#!/usr/bin/env python3
```
Shebang——Unix 系统用它定位解释器。Windows 忽略但无害。

```python
# -*- coding: utf-8 -*-
```
编码声明——Python 3 默认 UTF-8，此行可选（Python 2 兼容时有用）。

```python
"""My first Python program — the ritual."""
```
文档字符串（docstring）——模块、函数、类的首个字符串字面量，被 `help()` 使用。

```python
if __name__ == "__main__":
    main()
```
这是 Python 的惯用写法：当此文件**被直接运行**时，`__name__` 是 `"__main__"`，执行 `main()`；当它**被 import 导入**时，`__name__` 是模块名，`main()` 不执行。这让每个 Python 文件同时是"可导入的库"和"可运行的脚本"。

### 1.2.7 编码规范基础（PEP 8）

PEP 8 是 Python 官方风格指南（Style Guide for Python Code）。它解决的不是"对错"，而是"一致性"——当所有 Python 代码遵循同一套格式规则，阅读陌生代码的认知负担大幅降低。

#### 命名约定

```python
# 变量、函数、方法：snake_case（全小写，下划线分隔）
user_name = "Alice"
def calculate_average(numbers):
    pass

# 类：PascalCase（每个单词首字母大写）
class UserProfile:
    pass

# 常量：ALL_CAPS（全大写，下划线分隔）
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# 内部/私有（约定）：前置单下划线
_internal_value = 42         # "这是内部实现，别直接访问"
def _helper_function():      # 同上的语义
    pass

# 名称修饰（Name Mangling）：前置双下划线
class MyClass:
    def __really_private(self):  # 被 Python 自动重命名防止无意覆盖
        pass

# 避免与内置名冲突：后置单下划线
class_ = MyClass()            # class 是关键字，class_ 是名字
type_ = "user"                # type 是内置函数
```

#### 缩进与空白

```python
# 4 个空格缩进
if condition:
    do_something()
    if nested:
        do_other()

# 运算符两侧各一个空格
x = a + b * (c - d)

# 逗号后一个空格
items = [1, 2, 3, 4]

# 函数参数默认值的等号两侧不加空格
def greet(name: str = "World"):
    pass

# 顶级定义（函数、类）之间空两行
def first():
    pass


def second():
    pass

# 类内方法间空一行
class MyClass:
    def first(self):
        pass

    def second(self):
        pass
```

#### 行长与续行

```python
# 每行最多 79 字符（文档字符串/注释 72 字符）
# 对于长行，使用括号隐含续行（推荐）：
result = function_with_many_args(
    arg1, arg2, arg3,
    arg4, arg5, arg6
)

# 或使用反斜杠显式续行（不得已时才用）：
long_string = "this is a very long string that " \
              "needs to be broken into pieces"

# 长的 if 条件：
if (condition_one
    and condition_two
    and condition_three):
    do_something()
```

#### 导入规范

```python
# 导入顺序：标准库 → 第三方 → 本地
import os
import sys
from datetime import datetime

import numpy as np
import requests

from myproject.utils import helper

# 禁止：import *（除非模块明确设计了 __all__）
from module import *          # ❌ 污染命名空间

# 过长的模块名可用 as 简化
import matplotlib.pyplot as plt
```

#### 注释与文档字符串

```python
# 行内注释：与代码同级，说明"为什么"而非"做什么"
count = count + 1  # 补偿 0-index 偏移（这是有效的注释）

count = count + 1  # 计数器加 1（这是废话——代码已经说了）

# 文档字符串（docstring）：描述模块/函数/类的用途和使用方式
def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers.

    Args:
        n: Number of Fibonacci numbers to generate.

    Returns:
        A list of the first n Fibonacci numbers.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(5)
        [0, 1, 1, 2, 3]
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    # 实现细节……
```

### 1.2.8 获取帮助

学会"自己找答案"是程序员的核心能力。

#### 内置帮助系统

```python
help(print)          # 查看内置函数的文档
help(str)            # 查看类/类型的文档
help(str.lower)      # 查看方法的文档
help('modules')      # 列出所有已加载的模块

dir(42)              # 列出整数对象的所有属性和方法
dir(str)             # 列出 str 类的所有属性和方法
```

#### 官方文档

- **主文档**: https://docs.python.org/3/
- **标准库参考**: https://docs.python.org/3/library/index.html
- **语言参考**: https://docs.python.org/3/reference/index.html
- **教程（Official Tutorial）**: https://docs.python.org/3/tutorial/index.html

> **学习建议**：至少通读一遍官方教程（The Python Tutorial）的前 7 章。它是最好的入门材料，远超大多数第三方教程的信息密度和准确性。

#### 社区与资源

| 资源 | 用途 |
|------|------|
| [Python docs](https://docs.python.org) | 官方文档——最权威的参考 |
| [Stack Overflow](https://stackoverflow.com/questions/tagged/python) | 遇到具体错误时搜索 |
| [PyPI](https://pypi.org) | 查找 Python 包 |
| [PEP Index](https://peps.python.org) | 了解某项特性的动机和设计 |
| [Real Python](https://realpython.com) | 高质量深度教程 |
| [Python Discord](https://discord.gg/python) | 在线讨论 |
| `/r/learnpython` | Reddit 上的 Python 学习社区 |

#### 练习 1：环境验证与实践

1. 在终端中运行 `python --version` 和 `pip --version`，确认 Python 和 pip 已正确安装。
2. 创建一个虚拟环境（命名为 `practice_env`），激活它，然后在其中用 `pip install requests` 安装第三方包，最后用 `pip list` 查看已安装的包。
3. 编写一个 `hello.py` 脚本，要求：
   - 包含 shebang 行和文档字符串
   - 使用 `input()` 获取用户姓名
   - 用 f-string 输出 `"Hello, {姓名}! Welcome to Python."`
   - 包含 `if __name__ == "__main__"` 保护
   - 分别用 `python hello.py` 和 `python -m hello` 两种方式运行
4. 在交互模式（REPL）中依次执行：
   - `import this`，阅读 Zen of Python
   - `help(print)`，查看 print 的文档
   - `dir(str)`，列出字符串类型的所有方法
5. 使用 `py` 启动器（Windows）或 `pyenv`（macOS/Linux）查看你系统上所有可用的 Python 版本。
6. 将你编写的 `hello.py` 按照 PEP 8 规范检查一遍：命名是否 snake_case？缩进是否 4 空格？导入顺序是否正确？

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 编程语言分类 | 编译 vs 解释、静态 vs 动态、强类型 vs 弱类型——Python 是动态强类型解释型语言 |
| Python 设计哲学 | 可读性至上、一种明显的方法、自带电池、显式优于隐式 |
| Python 历史 | Guido van Rossum 1989 开始 → Python 3 2008 → 3.14 最新稳定版 2025 |
| 解释器 | CPython 是参考实现，PyPy 更快（JIT），MicroPython 在微控制器上跑 |
| 安装 | python.org 下载 → 勾选 Add to PATH → 验证 `python --version` |
| 包管理 | `pip install` 从 PyPI 下载 → `pip freeze` 锁定版本 → 国内用清华/阿里镜像 |
| 虚拟环境 | `python -m venv env` → `source env/bin/activate` → 每个项目独立隔离 |
| 开发工具 | VS Code + Python 扩展（首选），Jupyter（数据探索），PyCharm（大型项目） |
| PEP 8 | 命名、缩进、空白、导入——一致性 > 个人偏好 |
| 第一个程序 | `print("Hello, World!")` → 三种运行方式 → `if __name__ == "__main__"` |

**进入下一章的准备**：
- ✅ Python 已安装且可从终端访问
- ✅ 已配置好 VS Code（或你选择的编辑器）
- ✅ 已理解并创建了第一个虚拟环境
- ✅ 已运行过 `hello.py`，确认一切正常

如果你在这些步骤中遇到任何问题，**现在解决**——不要带着环境问题开始下一章的学习。
