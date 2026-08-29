# 第10章 模块与包管理

> **学习目标**：彻底理解 `import` 不是"读一个文件"，而是"查找 → 编译 → 执行 → 缓存"四步流水线；掌握模块、包、命名空间包三者的本质区别；能读懂 `sys.path` 的每一段从哪来；会设计合理的包布局、管理依赖、搭建可复现环境，并把代码打包成可安装的 wheel。

---

第 2 章 2.4 节第一次写下 `import`，第 9 章用 `pathlib` 操作文件——但 `import` 一直被当成黑盒：它"就是能拿到别人的代码"。本章掀开盒盖。你会看到：`import` 是一条**有副作用的执行语句**，背后是一套由 `importlib` 驱动的、可被用户代码劫持的流水线；模块是"只执行一次"的命名空间对象；包是带层次结构的命名空间；而"虚拟环境""打包""依赖管理"这些工程设施，全部建立在这套机制之上。

本章与前面章节的关系：第 6 章的 LEGB 规则里，模块命名空间就是那个"G"——本章回答"模块命名空间到底是什么、怎么被创建"；第 7 章讲了类命名空间与 `__dict__`，模块命名空间是同一个机制的更简单形态（无继承、无属性查找链）；第 8 章的 `ImportError`/`ModuleNotFoundError` 只在 import 失败时出现，本章讲清它们各自何时被抛出；第 9 章讲过"写文件要小心缓冲与原子性"，本章的 `__pycache__` 缓存复用同样的"版本校验"思想；正则专题里 `re.compile` 的 `_MAXCACHE` 缓存与 `sys.modules` 缓存是同一个"空间换时间"模式——本章把它讲到机制层。

---

## 10.1 模块的本质：一个文件，一个命名空间

### 10.1.1 import 语句到底做了什么

先做一个直觉测试：`import` 之后，Python 到底执行了什么？

```python
# 一个空模块
# mymod.py 内容为空

>>> import mymod
>>> type(mymod)
<class 'module'>
>>> mymod.__dict__          # 空模块也有自己的命名空间
{'__name__': 'mymod', '__doc__': None, '__package__': None, ...}
```

`import mymod` 完成三件事，缺一不可：

1. **查找（find）**：在 `sys.path` 上找到 `mymod` 对应的"源"——通常是一个 `mymod.py` 文件，也可能是内置模块、扩展模块（`.pyd`/`.so`）甚至是一个**命名空间**（见 10.3.3）。
2. **加载（load）**：创建模块对象，然后**执行模块文件里的全部代码**，把顶层名字写进模块的命名空间。
3. **绑定（bind）**：把模块对象绑定到当前作用域的局部/全局名字上，之后 `mymod` 这个标识符就指向那个模块对象。

> **关键认知**：`import` 是**执行语句**，不是"声明"。`import mymod` 会真的运行 `mymod.py` 里的每一行顶层代码（函数体/类体不会执行，但 `def`/`class` 语句本身会执行——它们负责把函数/类对象注册进命名空间）。这就是为什么"导入有副作用"：被导入的模块可能在导入时打印、连接数据库、写文件。

#### 为什么 `import` 是语句而不是表达式

这是 Guido 深思熟虑的设计决定，值得停下来理解。Python 中 `import` 是语句，而 JavaScript（ES Modules）、Ruby 中的 `require` 是表达式/函数调用。差异不是语法口味，而是语义立场：

| 语言 | 形式 | 本质 |
|------|------|------|
| Python | `import a`（语句） | 编译期可识别、有副作用、绑定名字 |
| JavaScript | `import a from "a"`（声明） / `require("a")`（表达式） | 声明是静态的、被 hoist；`require` 是运行时函数 |
| C | `#include <a.h>`（预处理指令） | 文本粘贴，无命名空间概念 |
| Rust | `use a::b;`（声明） | 编译期解析，模块是编译单元 |

Guido 在《The History of Python》中解释过：`import` 保持语句形态，一是因为**可读性**——导入是代码最需要被一眼看清的部分，语句比表达式醒目；二是因为**它有副作用**，而 Python 的哲学是"有副作用的事用语句，纯计算用表达式"（`=` 赋值同理）；三是因为编译器可以在编译期识别 `import`，从而做出优化（例如把模块内循环中的 `import` 提升，见下文 10.1.3 的字节码）。

> **设计哲学**：Python 区分"语句"与"表达式"——语句做**有副作用的事**（赋值、导入、控制流），表达式产出**值**。`import` 有副作用（执行模块代码），所以是语句。`__import__()` 和 `importlib.import_module()` 是它的"表达式形态"，留给需要动态导入的少数场景。

#### import 系统演进史：从 rexec 到 PEP 451

`import` 的机制不是一天建成的，理解演进能解释"为什么代码长这样"：

| 时代 | 里程碑 | 内容 |
|------|--------|------|
| ~1.5 | `rexec` / `ihooks` | 最早的 import 钩子实验（受限执行环境），后废弃 |
| 2.1 | `__import__` 公开 | import 的表达式形态；`imp` 模块提供底层 API |
| **2.3（2003）** | **PEP 302** | 正式定义 finder/loader 协议：`find_module`/`load_module` |
| **2.5（2006）** | **PEP 328** | 绝对/相对导入统一语法（`from . import x`） |
| 3.0 | — | `imp` 逐步让位 `importlib`；`reload` 移入 `importlib` |
| **3.3（2012）** | **PEP 420** | 隐式命名空间包（`__init__.py` 不再必需） |
| **3.4（2014）** | **PEP 451** | `ModuleSpec` 模型：finder 返回 spec，加载统一驱动 |
| 3.5 | — | `importlib.util.module_from_spec` 成为标准创建方式 |
| **3.7（2018）** | **PEP 552** | hash-based pyc；PEP 562 模块级 `__getattr__` |
| 3.11 | — | `PYTHONSAFEPATH`；PEP 660 editable 全面落地 |

> **设计哲学**：演进主线是"**把协议变简单、把扩展点变标准**"——PEP 302 首次把"import 钩子"从 `rexec` 的黑魔法变成公开协议；PEP 451 又把"finder 边找边载"的副作用协议改为"先 spec 后加载"的纯函数式模型。每次重构都让 import 系统更可审计、更可扩展——这正是 10.2.4 自定义钩子能安全存在的前提。

### 10.1.2 模块对象与模块命名空间

#### 模块就是"一个装着名字的 `__dict__`"

在 CPython 里，模块对象是 `PyModuleObject`，核心就是一个字典 `md_dict`。你可以把它想象成"一个没有继承、没有魔术方法的极简对象"——比第 7 章的实例对象还简单：

```python
>>> import mymod
>>> mymod.__dict__ is vars(mymod)
True                      # vars() 直接取出模块的命名空间字典
```

模块对象上有几个关键属性，全部来自 `PyModuleObject` 的字段：

| 属性 | 含义 |
|------|------|
| `__name__` | 模块全名（`sys.modules` 里的键） |
| `__file__` | 模块源码路径（内置模块没有；命名空间包为 `None`） |
| `__package__` | 所属包名（顶层模块为 `''`，3.3+ 由 `__spec__.parent` 计算） |
| `__spec__` | `ModuleSpec` 对象（PEP 451，见 10.2.2） |
| `__loader__` | 加载器（`SourceFileLoader` 等，遗留属性） |
| `__dict__` | 命名空间本体，`vars(module)` 就是它 |

#### `import a.b.c` 绑定的为什么是 `a`

这是新手最容易困惑的一点：

```python
>>> import os.path
>>> os            # ✅ 可用
<module 'os' from '.../os.py'>
>>> os.path       # ✅ 可用——因为 os 模块内部也 import 了 path
<module 'posixpath' from '.../posixpath.py'>
>>> path          # ❌ NameError——没有名为 path 的绑定
```

`import a.b.c` 的绑定规则：**只把最顶层名字 `a` 绑定到当前命名空间**。原因在 CPython 的导入流水线里：`a.b.c` 的加载过程会依次创建并缓存 `a`、`a.b`、`a.b.c` 三个模块对象（都进 `sys.modules`），但当前命名空间只写一个名字 `a`。后续 `a.b`、`a.b.c` 的访问靠**属性链**：`a` 模块的命名空间里有 `b`（因为导入 `a.b` 时会把 `b` 作为属性挂在 `a` 上），`a.b` 的命名空间里有 `c`。

> **注意**：`import a.b.c` 保证 `a.b` 一定可作为属性访问（导入 `a.b.c` 必须先完整加载 `a.b`），但**不保证** `a.b` 在当前命名空间可见——你只能拿到 `a`。

#### `from x import y` 的绑定语义：拷贝引用，而非引用模块

```python
>>> from math import sqrt
>>> sqrt(4)
2.0
```

`from x import y` 等价于：导入 `x`，然后执行 `y = x.y`——把 `x` 命名空间里 `y` 的名字**绑定到当前命名空间**。这带来两个重要推论：

1. **它是"引用拷贝"，不是"引用模块"**：`from x import y` 之后，`y` 指向 `x.y` 当时的对象。如果之后 `x` 内部重新绑定了 `y`（例如 `x` 被 reload，或 `x` 在别处做了 `y = new_value`），当前命名空间的 `y` 不会跟着变。
2. **可变对象是共享的**：若 `y` 是可变对象（列表、字典、类），`from` 和 `import` 拿到的都是同一对象，修改会互相可见。

```python
# config.py
settings = {"theme": "dark"}

# main.py
from config import settings

# 某处修改了 config.settings
import config
config.settings["theme"] = "light"

>>> settings["theme"]        # ✅ 'light'——可变对象共享
'light'
```

```python
# ❌ 误解：以为 from import 是"把模块里的名字复制一份，之后互不相干"
from config import settings
config.settings = {"theme": "light"}   # 重新绑定（不修改原对象）
>>> settings["theme"]                  # 仍是 'dark'——但这是因为"重新绑定"而非"复制"
'dark'
```

> **⚠️ 陷阱**：`from module import name` 的名字**不会**因为模块后续重新绑定而更新。如果需要"始终跟随模块最新状态"，用 `import module` + `module.name` 访问。

#### `from x import *` 与 `__all__`

```python
>>> from math import *
>>> sqrt, pi, sin          # 全进来了
```

`from x import *` 导入 `x.__all__`（若定义了）列出的名字；若没有 `__all__`，则导入所有**不以 `_` 开头**的顶层名字。这就是为什么模块内"私有"名字用 `_` 前缀约定——`*` 导入会尊重它。

> **实战建议**：库模块**显式定义 `__all__`**，把公共 API 收口。这不仅控制 `*` 导入，还能帮助 IDE 提示和 `help()` 展示，并且是"包的公开接口"的文档化声明。

#### CPython 视角：PyModuleObject 的内存布局

模块对象的 C 层结构（`Include/cpython/moduleobject.h`）比类对象简单得多：

```c
typedef struct _module {
    PyObject_HEAD
    PyObject *md_dict;           // 命名空间字典 —— 模块的 __dict__
    struct PyModuleDef *md_def;  // C 扩展模块定义（纯 Python 模块为 NULL）
    void *md_state;              // C 扩展的模块状态（PEP 573 前为全局单例）
    PyObject *md_weaklist;       // 弱引用列表
    PyObject *md_name;           // 模块名（新近版本单独缓存，避免反复散列）
} PyModuleObject;
```

`md_dict` 是绝对核心：**模块的一切属性——包括 `__name__`、`__file__`、甚至 `__dict__` 本身——都作为键值存在这个字典里**。`module.name` 的属性访问最终就是一次字典查找 `md_dict["name"]`，由 `_PyObject_GenericGetAttr` 完成。

与第 7 章的对象模型对比，模块的"属性查找链"短得可怜：

| 对象 | 查找链 | 缺失时的兜底 |
|------|--------|-------------|
| 实例 | type → MRO → 实例 `__dict__` → 数据描述符... | 实例 `__getattr__`（若定义） |
| 类 | MRO 逐级找 | 元类 `__getattr__` |
| **模块** | `md_dict`（就一层） | 模块级 `__getattr__`（PEP 562，3.7+） |

> **🔑 机制洞察**：模块"无继承、无描述符、无元类"——它是 Python 对象模型里最朴素的一等公民。这也解释了为什么模块级 `__getattr__`（PEP 562）那么晚才出现：在此之前，模块的属性查找失败就是纯粹的 `AttributeError`，没有任何钩子。

#### 模块 dict 与普通字典的差异

```python
>>> vars(mymod) is mymod.__dict__
True
>>> type(mymod.__dict__)
<class 'dict'>          # 就是普通 dict，没有魔法
```

模块命名空间就是普通 `dict`，但它有两条不成文的纪律：

1. **键必须是字符串**（`module.x = 1` 的语法保证）；
2. **`__name__` 等 dunder 只是普通键**——你可以手动改它们（后果自负）：

```python
>>> mymod.__name__ = "fake"
>>> mymod.__name__
'fake'                  # 危险：sys.modules 里的键还是 "mymod"，但对象自称 "fake"
```

> **⚠️ 陷阱**：直接改 `__name__`/`__package__` 会让 `pickle`、`importlib.reload`、调试器产生错乱（它们以这些属性定位模块）。模块属性要改请走 `importlib.util.module_from_spec` 等正规流程。

#### __main__ 模块特写

`sys.modules["__main__"]` 是"当前入口"的模块对象——无论入口是脚本、`-c` 代码还是 REPL：

```python
# 脚本模式：__main__ 就是脚本文件对应的模块
$ cat demo.py
import sys
print(sys.modules["__main__"].__file__)   # demo.py 的路径

$ python demo.py
demo.py

# REPL / -c：__main__ 没有 __file__
>>> import sys
>>> sys.modules["__main__"].__file__
Traceback (most recent call last):
  ...
AttributeError: module '__main__' has no attribute '__file__'
```

由此诞生一个经典技巧——**在 REPL 或脚本里访问"入口上下文"的变量**：

```python
# 库代码里"拿到调用者"的环境
import sys
caller_ns = vars(sys.modules["__main__"])   # 入口脚本/REPL 的命名空间
```

```python
# 应用场景：调试脚本的全局配置、REPL 里定义的变量
>>> import __main__
>>> __main__.my_var = 42      # REPL 中定义的变量
>>> import sys
>>> sys.modules["__main__"].my_var
42
```

> **注意**：`python -m mypkg` 时 `sys.modules["__main__"]` 是 `mypkg/__main__.py` 对应的模块对象——`__main__` 并不总是"你的脚本文件"。这就是为什么 `if __name__ == "__main__":` 在 `-m` 下也成立（`__name__` 被设为 `"__main__"`），但它指向的模块**不是** `sys.modules["mypkg"]`——两者是不同对象。

### 10.1.3 字节码视角：import 的编译结果

把 `import` 语句反汇编，能直接看到它和普通函数调用完全不同：

```python
>>> import dis
>>> def f():
...     import os.path
...     from math import sqrt
...     import sys
>>> dis.dis(f)
  2           0 LOAD_CONST      1 (0)            # 元组 (0, 'os', 'path') 表示要导入的层次
              2 LOAD_CONST      2 (('os', 'path'))
              4 IMPORT_NAME     0 (os.path)      # 执行完整导入流水线，压栈 a.b.c 的最顶层模块 a
              6 STORE_NAME      1 (os)           # 绑定到名字 os
  3           8 LOAD_CONST      3 (0)
             10 LOAD_CONST      4 (('sqrt',))
             12 IMPORT_NAME     2 (math)         # 先导入 math
             14 IMPORT_FROM     3 (sqrt)         # 从栈顶模块取属性 sqrt 压栈
             16 STORE_NAME      4 (sqrt)         # 绑定到当前命名空间
             18 POP_TOP                           # 弹出多余的模块引用（from 导入残留）
  4          20 LOAD_CONST      5 (0)
             22 LOAD_CONST      6 (None)
             24 IMPORT_NAME     5 (sys)
             26 STORE_NAME      6 (sys)
             28 LOAD_CONST      7 (None)
             30 RETURN_VALUE
```

解码这张指令表：

- `IMPORT_NAME` 是**一条指令完成三步**：它调用 `__import__()`（内部走 `importlib` 流水线），返回最顶层模块（`import a.b.c` 时返回 `a`）。操作数不是"模块名"，而是**名字元组**——`('os', 'path')` 让编译器把"模块名 + 逗号分隔的后续名字"打包，`import os.path` 与 `import os, path` 被区分开来。
- `from math import sqrt` 编译为 `IMPORT_NAME` + **`IMPORT_FROM`**：`IMPORT_FROM` 从栈顶模块对象取属性——这证明 `from x import y` 本质是"导入 x，然后 `x.y` 属性访问"，与第 7 章的属性查找是同一机制。
- `STORE_NAME` 把结果绑到局部/全局命名空间，与 `x = 1` 的赋值用同一指令——`import` 就是"一次特殊的赋值"。

> **🔑 字节码洞察**：`import` 在字节码层面就是"`IMPORT_NAME` 指令 + `STORE_NAME` 赋值"。这解释了为什么"import 是语句"：编译器必须静态识别它（指令里内嵌名字元组），而函数调用 `__import__()` 做不到这种编译期识别。

#### 一个编译器的隐藏优化：模块内的 import 提升

```python
def outer():
    for i in range(1000):
        import math          # 循环内 import
        math.sqrt(i)
```

字节码层面，`import math` 在循环体内每次迭代都会执行 `IMPORT_NAME`。但 `IMPORT_NAME` 本身开销极小——它先查 `sys.modules`，命中就直接返回，不重新执行 `math.py`。**真正被优化的不是指令，而是 `sys.modules` 缓存**（见 10.1.4）。CPython 3.12 的 `LOAD_IMPORT` 实验性优化曾尝试把它提升出循环（PEP 709 相关工作的副产品，最终未合并）。工程上：**把 import 放模块顶层是惯例**，但偶尔在函数内 import 也是合法模式（见 10.4.3 延迟导入）。

### 10.1.4 sys.modules 缓存：模块只执行一次

#### 键值语义

`sys.modules` 是一个字典：**键是模块全名（含点），值是模块对象**。

```python
>>> import sys, os.path
>>> "os" in sys.modules
True
>>> "os.path" in sys.modules
True
>>> sys.modules["os"] is os
True
```

重复 `import` 的完整路径：

```
import os.path
  → 查 sys.modules 命中 "os"？ 命中 → 直接返回，不再执行 os.py
  → 查 sys.modules 命中 "os.path"？ 命中 → 直接返回
```

**模块代码只执行一次**——即使你在 100 个文件里 `import os`，`os.py` 的顶层代码只运行一次。这是"空间换时间"的缓存：省去重复的磁盘读取、编译、执行。

> **与正则专题的类比**：`re.compile` 的缓存（`_MAXCACHE = 512`，满时整体 `clear()`）与 `sys.modules` 是同一模式，但策略不同——`sys.modules` **永不淘汰**（模块通常小、导入频率高、且模块对象可能被外部引用），而正则缓存有界。正因 `sys.modules` 无界且长期驻留，**顶层 import 大量大模块会永久占用内存**——这是"为什么不在函数里 import 重量级库"的理由之一。

#### `importlib.reload()` 与缓存一致性风险

```python
>>> import importlib, mymod
>>> importlib.reload(mymod)      # 重新执行 mymod.py，覆盖 sys.modules 里的模块对象内容
```

`reload()` 在**原模块对象的命名空间里重新执行代码**：它不创建新对象，而是复用 `sys.modules["mymod"]` 那个对象，清空后重新执行。这带来一系列一致性陷阱：

```python
# ❌ reload 后旧引用指向"已清空重建"的同一对象，但名字可能已消失
from mymod import helper        # 先导入
import importlib, mymod
importlib.reload(mymod)         # mymod.py 新版删除了 helper
>>> helper                      # 旧名字还在，指向旧函数对象——reload 不会撤销 from 导入的绑定
<function helper at 0x...>
```

- 其他模块 `from mymod import X` 拿到的 `X` 不会更新；
- `reload` 后模块里 `class A` 是新类对象，但已有实例仍属于旧类（`isinstance` 会失败）；
- 依赖 `mymod` 的模块不会跟着重载。

> **工程影响**：`importlib.reload` 适合 REPL 调试，**不适合生产代码热更新**。生产热更新要么走进程重启，要么用成熟的插件/热加载框架（它们会管理依赖图和引用重建，见 10.2.4）。"改代码 → reload → 接着跑"在 REPL 里很爽，但一旦涉及跨模块 `from` 导入就会漏更新。

#### 手动操作 sys.modules：伪造模块与移除模块

因为 `sys.modules` 就是普通字典，你可以直接操作它：

```python
# 伪造模块：测试时注入假实现
>>> import sys, types
>>> fake = types.ModuleType("hardware")
>>> fake.read_sensor = lambda: 42
>>> sys.modules["hardware"] = fake
>>> import hardware            # 命中缓存，拿到假模块！
>>> hardware.read_sensor()
42
```

```python
# 移除模块：强制下次 import 重新加载
>>> import sys, mymod
>>> del sys.modules["mymod"]
>>> import mymod               # 重新执行 mymod.py，得到新对象
```

> **⚠️ 陷阱**：手动往 `sys.modules` 塞对象时，必须同时处理"部分初始化"状态——`import a.b` 时若 `a` 在 `sys.modules` 里但 `a.b` 不在，且 `a` 是命名空间包，`PathFinder` 会继续查找 `a.b`。删除模块时若只删 `a.b` 不删 `a`，`import a.b` 可能拿到"幽灵模块"。测试框架（如 pytest 的 monkeypatch）封装了这些边界，优先用它们。

#### importlib 工具函数速查

标准库 `importlib` 是"导入系统的用户面 API"，几个高频函数值得专门记忆：

| 函数 | 作用 | 典型场景 |
|------|------|---------|
| `importlib.import_module(name)` | 动态导入（表达式形态的 `import`） | 插件加载、按配置导入 |
| `importlib.reload(module)` | 重新执行模块代码 | REPL 调试（10.1.4） |
| `importlib.invalidate_caches()` | 清空 finder 的目录缓存 | 运行时新增了模块文件后 |
| `importlib.util.find_spec(name)` | 查找但不加载，返回 `ModuleSpec` | 探测模块存在性（10.2.1 调试） |
| `importlib.util.module_from_spec(spec)` | 按 spec 创建模块对象 | 自定义加载流程 |
| `importlib.util.resolve_name(name, package)` | 把相对名解析为绝对名 | `resolve_name(".sub", "pkg")` → `pkg.sub` |
| `importlib.util.spec_from_loader(name, loader)` | 手工构造 spec | 自定义 finder 的兜底 |

```python
# 运行时新增模块文件的经典问题：Finder 缓存了目录内容
>>> import mypkg
# （往 mypkg/ 里新放了一个 util.py）
>>> import importlib.util
>>> importlib.util.find_spec("mypkg.util")      # 可能找不到！
>>> importlib.invalidate_caches()               # 清缓存
>>> importlib.util.find_spec("mypkg.util")      # ✅ 找到了
ModuleSpec(name='mypkg.util', ...)
```

> **⚠️ 陷阱**：`FileFinder` 会缓存目录列表（避免每次 import 都读目录）。**运行时往包里新增/删除 `.py` 文件后，必须 `importlib.invalidate_caches()`**，否则 import 会"看不到新文件"。这个坑在"插件动态安装"和"测试夹具动态生成模块"时最常踩。

---

## 10.2 导入机制全链路：从路径查找到字节码加载

10.1 节回答了"import 是什么"，本节回答"import 怎么找到你的代码"。这是 `importlib` 的领域——一套被 PEP 451（2013）重构过的、**对用户代码完全开放**的协议。

### 10.2.1 sys.path：导入路径的构成

`sys.path` 是一个字符串列表，`PathFinder` 按顺序扫描它寻找模块。它的每一段都有明确来源：

```python
>>> import sys
>>> sys.path
['', '/usr/local/lib/python314.zip',
 '/usr/local/lib/python3.14',
 '/usr/local/lib/python3.14/lib-dynload',
 '/usr/local/lib/python3.14/site-packages']
```

| 段 | 来源 | 说明 |
|----|------|------|
| `''`（空串，即 cwd） | 启动时自动添加 | 脚本模式：脚本所在目录；交互模式/`-c`/`-m`：当前工作目录 |
| `python314.zip` | 标准库压缩包（可选） | 存在时才加入 |
| 标准库目录 | 解释器编译时写死 | `sys.prefix` + `lib/pythonX.Y` |
| `lib-dynload` | 扩展模块目录 | `.so`/`.pyd` 所在 |
| `site-packages` | `site` 模块启动时添加 | 第三方包；还会读 `.pth` 文件 |

`sys.path` 的构建顺序（`site` 模块文档中的 `sys.path` 构造流程）：

1. 启动时：`''`（脚本目录或 cwd）+ `PYTHONPATH` 中的路径；
2. 解释器把标准库路径加进来；
3. `site` 模块启动：追加 `site-packages`、读取 `.pth` 文件、处理 user site（`~/.local/lib/python3.14/site-packages`，`--user` 安装的目标）。

```python
# PYTHONPATH 环境变量的作用：在脚本目录之后、标准库之前插入
$ PYTHONPATH=/opt/mycode python -c "import sys; print(sys.path)"
['', '/opt/mycode', '/usr/local/lib/python314.zip', ...]
```

> **注意**：`PYTHONPATH` 里的路径排在**标准库之前**。这意味着同名文件会遮蔽标准库——`PYTHONPATH` 里放一个 `json.py` 就会让全世界的 `import json` 都用到它。这既是灵活性（开发期覆盖），也是安全隐患。

#### PYTHONSAFEPATH：3.11+ 的安全开关

Python 3.11 引入 `PYTHONSAFEPATH`（对应 `-P` 命令行选项）：**不把脚本目录/cwd 和 `PYTHONPATH` 加入 `sys.path`**，防止"当前目录下的恶意 `json.py`"等名字遮蔽攻击。

```bash
$ python -P app.py          # sys.path 里不再有脚本目录和 PYTHONPATH
```

> **版本注意**：`PYTHONSAFEPATH` / `-P` 是 Python 3.11 新增（对应 gh-issue 提出的"安全路径"方案）。生产部署、运行不可信目录下的脚本时强烈建议开启。

#### 调试技巧：我的 import 到底命中了哪个文件

"导入的模块和我想的不是同一个"是最常见的模块问题，三个工具一次定位：

```python
# 工具 1：问模块自己
>>> import json
>>> json.__file__                    # 源码文件
'C:\\Python314\\Lib\\json\\__init__.py'
>>> json.__spec__.origin             # 更权威的"来源"
'C:\\Python314\\Lib\\json\\__init__.py'

# 工具 2：不导入就能查（importlib.util.find_spec）
>>> import importlib.util
>>> spec = importlib.util.find_spec("requests")
>>> spec.origin
'C:\\proj\\.venv\\Lib\\site-packages\\requests\\__init__.py'

# 工具 3：让解释器唠叨（python -v）
$ python -v -c "import json" 2>&1 | Select-String "json"
import 'json' # <frozen importlib._bootstrap>
import 'json' # from 'C:\\Python314\\Lib\\json\\__init__.py'
```

`python -v` 打印**每次 import 的命中路径**——当"明明装在了 A 环境，代码却用的是 B 环境的包"时，它一针见血。配合 10.5.1 的 `sys.prefix`/`sys.path` 检查，五分钟内定位环境错位。

> **⚠️ 陷阱**：`python` 与 `python3` 可能指向不同解释器（Windows 上 `py` 启动器更是多版本并存）。"`pip install` 装好了但 `import` 报 ModuleNotFoundError"的第一排查项永远是：**安装用的解释器 ≠ 运行用的解释器**。铁律：`python -m pip install ...`（用同一解释器调 pip），而非裸 `pip install`。

#### site 模块与 .pth 文件

`site-packages` 目录下可以放 `.pth` 文件（每行一个路径或一条 `import` 语句），`site` 启动时会逐行处理：

```python
# site-packages/mypkg.pth
C:\tools\mypkg\src          # 把该路径追加到 sys.path
import mypkg._bootstrap     # 以 import 开头的行会被执行！
```

`.pth` 的两种用途：**追加路径**（老的 editable install 方案的核心，见 10.6.3）和**导入时执行代码**（有安全风险——任何能写 `site-packages` 的人都能在每次 Python 启动时执行任意代码）。

### 10.2.2 finder 与 loader 协议（PEP 451）

#### 历史：PEP 302 → PEP 451

- **PEP 302**（2003）定义了 `find_module()` / `load_module()` 的 finder-loader 接口；
- **PEP 451**（2013）重构为 `ModuleSpec` 为中心的模型：finder 不再"边找边载"，而是先返回一个**规范（spec）**，再由 `importlib` 统一驱动加载。动机：旧协议中 finder 要"假装加载"来判断模块是否存在（副作用、性能差），且 `__package__`/`__loader__` 等属性在加载后才补，互相依赖难缠。

现在的流水线（`importlib._bootstrap._find_and_load` 的简化）：

```
import a.b
 1. 查 sys.modules → 命中则返回
 2. 依次调用 sys.meta_path 中每个 finder 的 find_spec("a.b", ...)
    → 某 finder 返回 ModuleSpec，或返回 None（继续下一个）
 3. 由 spec 创建模块对象（spec.loader.create_module 或默认）
 4. 设置模块属性（__name__、__file__、__spec__...）
 5. 执行模块代码（spec.loader.exec_module）
 6. 递归处理父包 a（先加载 a 再加载 a.b）
 7. 存入 sys.modules，绑定名字
```

#### 三个角色

**`MetaPathFinder`**——全局级查找器，`sys.meta_path` 里的元素：

```python
import sys
>>> sys.meta_path
[<class '_frozen_importlib.BuiltinImporter'>,
 <class '_frozen_importlib.FrozenImporter'>,
 <class '_frozen_importlib_external.PathFinder'>]
```

接口（PEP 451 后）：

```python
class MetaPathFinder:
    def find_spec(self, fullname, path, target=None):
        """fullname: 'a.b'；path: 父包的 __path__（顶层为 None）
           返回 ModuleSpec 或 None"""
        ...
```

**`PathEntryFinder`**——`PathFinder` 为 `sys.path` 上每个条目（目录/zip 等）创建的查找器，接口同样以 `find_spec(fullname, path_entry, target=None)` 为主。

**`Loader`**——真正干活的：

```python
class Loader:
    def create_module(self, spec):   # 可选：返回自定义模块对象；返回 None 用默认创建
        ...
    def exec_module(self, module):   # 必须：执行模块代码，填充 module.__dict__
        ...
```

#### 内置三巨头

| Finder | 负责 | 典型模块 |
|--------|------|---------|
| `BuiltinImporter` | 编译进解释器的模块 | `sys`、`builtins`、`_io`（`sys.builtin_module_names` 可查全表） |
| `FrozenImporter` | 冻结模块（编译期序列化的字节码） | `_frozen_importlib`（导入系统自身！） |
| `PathFinder` | 扫描 `sys.path` 的 `PathEntryFinder` | 一切磁盘上的 `.py`/`.so`/zip 包 |

> **🔑 递归之美**：`import` 系统自身也是用 `import` 系统加载的——`_frozen_importlib` 是**冻结模块**，它的字节码在解释器启动时直接可用，不需要再走文件查找，从而避免了"导入系统需要导入系统来启动"的鸡生蛋问题。启动后的完整 `importlib` 源码仍在 `Lib/importlib/`。

#### 模块规范（ModuleSpec）的字段

```python
>>> import os.path
>>> spec = os.path.__spec__
>>> spec.name          # 'os.path'
>>> spec.origin        # '/usr/local/lib/python3.14/posixpath.py'
>>> spec.loader        # <class '_frozen_importlib_external.SourceFileLoader'>
>>> spec.submodule_search_locations   # 包的 __path__（模块为 None）
```

`__spec__` 从 3.4 起成为每个模块的标准属性，`__package__`/`__loader__`/`__path__` 等属性都从 spec 推导或由加载流程设置。

#### sys.path_hooks 与 sys.path_importer_cache：PathEntryFinder 从哪来

`PathFinder` 扫描 `sys.path` 时，对每个条目都要决定"用哪个 `PathEntryFinder` 处理它"。这个过程有两层缓存：

```python
>>> sys.path_hooks
[<class 'zipimporter'>,                       # 处理 .zip/.pyz 条目
 <function FileFinder.path_hook.<locals>.path_hook_for_FileFinder at 0x...>]  # 处理目录条目
```

算法（`importlib._bootstrap_external._get_spec` 的路径解析部分）：

```
对 sys.path 中的每个条目 path：
  1. 查 sys.path_importer_cache：path → finder（或 None 表示"不可导入"）
  2. 未命中：逐个调用 sys.path_hooks 里的 hook
     → 第一个不抛 ImportError 的 hook 返回 finder，缓存之
     → 全部抛 ImportError → 缓存 None（该条目不可导入）
  3. 用该 finder 的 find_spec(fullname, path) 查找
```

```python
>>> import zipimport
>>> zi = zipimport.zipimporter("myapp.pyz")   # zip 条目 → zipimporter
>>> zi.find_spec("mypkg")                     # 直接从 zip 里找模块
ModuleSpec(name='mypkg', loader=<zipimport.zipimporter object at ...>, origin='myapp.pyz/mypkg/__init__.py')
```

关键推论：

- **`.pyz`/zip 是合法导入源**：`sys.path` 里放一个 `.pyz`，里面的模块就能被 `import`——10.8.1 的 `zipapp` 正是基于此；
- **目录条目 → `FileFinder`**：默认 hook 把目录变成 `FileFinder`（内部按扩展名注册 `SourceFileLoader`/`ExtensionFileLoader`/`SourcelessFileLoader`）；
- **`sys.path_importer_cache` 不自动失效**：删掉某目录后，缓存里的 finder 仍指向旧位置。调试"改了目录结构但 import 没变"时，`sys.path_importer_cache.clear()` 强制重建。

> **实战建议**：临时给 `sys.path` 加 zip/目录而不想污染环境时，手动构造 finder 并塞进 `sys.path_importer_cache` 是干净做法——比改 `sys.path` 更精确（10.2.4 的钩子哲学一致）。

### 10.2.3 编译与字节码缓存：__pycache__ 的秘密

#### .py → .pyc：导入时的隐藏编译

`SourceFileLoader.exec_module` 并不直接执行源码——它先**编译**：

```
mymod.py →（tokenize → AST → 字节码）→ 存入 __pycache__/mymod.cpython-314.pyc → 执行字节码
```

```python
>>> import mymod
>>> mymod.__cached__            # 编译产物的位置
'/path/to/__pycache__/mymod.cpython-314.pyc'
```

`__pycache__` 命名规则：`模块名.cpython-<版本号>.pyc`。版本号是"magic number"的一部分——**Python 小版本之间字节码格式可能不同**，magic number 就是格式版本标识。这就是为什么 `3.13` 的 pyc 不会被 `3.14` 复用。

> **⚠️ 陷阱**：pyc 文件**不是跨平台/跨版本可移植的**。它绑定：解释器 magic（字节码格式）+ 源码时间戳或 hash。把 `__pycache__` 拷到另一台机器上，只要 Python 版本或源码变了，就会失效重编译——这是正常机制，不是 bug。

#### pyc 文件头：magic + 校验

`.pyc` 的前 16 字节是文件头：

| 偏移 | 内容 | 说明 |
|------|------|------|
| 0–3 | magic number | 字节码格式版本标识 |
| 4–7 | flags | 位 0：hash-based（PEP 552） |
| 8–15 | 时间戳 + 源文件大小，或源码 hash | 校验"pyc 是否过期" |

**PEP 552**（2017，3.7）引入 **hash-based pyc**：以源码内容 hash 代替时间戳+大小做校验。时间戳方案在"源码内容没变但 mtime 被改动"（如 git checkout、打包解压）时会**误判过期**而重编译；hash 方案精确但每次启动要读源码算 hash。`PYTHONHASHSEED` 不参与（用的是 `blake2b`/`sha256` 等稳定算法）。

```bash
# 与 pyc 缓存相关的实用开关
$ python -B app.py                     # 不写 __pycache__（仍编译，只是不落盘）
$ PYTHONDONTWRITEBYTECODE=1 python app.py    # 同上，环境变量形式
$ PYTHONPYCACHEPREFIX=/var/cache/pyc python app.py   # pyc 集中写到指定目录（只读部署用）
$ python -X importtime -c "import app" # import 耗时分析（见下节）
```

hash-based pyc 的**生成**通常由构建/打包工具完成（如 `compileall` 的 `--invalidation-mode=unchecked-hash`），运行时解释器按文件头 flags 识别并校验——普通开发不需要手动生成，理解"时间戳校验可能误判、hash 校验精确"即可。

> **版本注意**：时间戳校验的"mtime 未变"场景在**版本管理工具还原、容器镜像层合并、文件同步**中最常见——源码看起来没问题，但运行的是旧字节码。解法：启用 hash-based pyc（构建时用 `compileall --invalidation-mode=unchecked-hash` 统一生成），或接受"删掉 `__pycache__` 再跑"的运维铁律。

#### 性能数据：编译到底占多少启动时间

在 CPython 3.14 下实测（同一台机器、同一模块）：

```
$ python -X importtime -c "import pandas" 2>&1 | tail -1
import time: 452 ms  (pandas 及其依赖)
```

对 `pandas` 这类大依赖，**冷启动（无 pyc）比热启动（有 pyc）慢 20%–50%**——差异几乎全部来自编译。对策：

1. 保留 `__pycache__`（默认行为），部署时不要清掉；
2. 用 `PYTHONPYCACHEPREFIX` 把缓存放到快速存储；
3. 真正追求启动速度的部署（CLI 工具、serverless）用 **freeze**（`PyInstaller`/`Nuitka` 等把字节码打包进可执行文件，跳过"按需编译 + 文件查找"）。

> **🔑 性能洞察**：`import` 的热路径是"查 `sys.modules` → 命中返回"，纳秒级；冷路径是"磁盘读 → 编译（或读 pyc）→ 执行"，毫秒级。因此"启动慢"的真相通常不是 import 机制慢，而是**被导入的模块代码本身在导入时执行了重量级初始化**（如 `pandas` 的 C 扩展导入、大模块的顶层计算）。分析工具：`python -X importtime -c "import 你的入口"`。

#### 为什么 import 比直接执行 .py 快

```bash
$ python mymod.py      # 脚本模式：每次启动都重新编译 mymod.py（不写缓存）
$ python -c "import mymod"   # 导入模式：mymod 被编译并缓存到 __pycache__
```

顶层脚本（`python file.py`）本身的编译结果**不写入 `__pycache__`**——它是"一次性"的。但它 import 的每个模块都会走缓存。所以"慢"只发生在脚本自身那一层，模块层已被缓存拯救。

#### 冷启动性能实测：timeit 与 -X importtime 实战

`-X importtime` 是官方性能工具，逐模块打印导入耗时树：

```bash
$ python -X importtime -c "import json" 2>&1
import time: self [us] | cumulative | imported package
import time:      1159 |       1159 |   _json
import time:       199 |      11649 | json
```

`self` = 该模块自身导入耗时（编译+执行），`cumulative` = 含其依赖的累计值。两个判断口径：

- **`cumulative` 大而 `self` 小** → 慢在依赖链上，别怪这个模块；
- **`self` 大** → 模块顶层代码本身重（大常量表、`__init__.py` 里做 I/O、C 扩展初始化）。

```python
# timeit 验证 pyc 缓存对重复 import 的影响
>>> import timeit
>>> timeit.timeit("import json", number=100_000)
0.1394          # 每次约 1.4µs —— 命中 sys.modules 的热路径，纳秒级
>>> import json; timeit.timeit("import json", number=100_000)
0.1143          # 已经导入过 → 只剩缓存查找
```

对比"首次导入 vs 重复导入"的量级差距，就能理解为什么"循环里 import"不可怕、而"启动时 import 大模块"才需要优化。

> **工程影响**：启动优化三板斧——(1) 用 `-X importtime` 找出 `self` 最大的模块；(2) 把重量级导入延迟（`__init__.py` 薄壳 + 模块级 `__getattr__` 懒加载，见 10.4.1）；(3) 实在绕不开（如 `pandas`/`torch` 的 C 扩展）则接受成本或换更轻的替代实现。

#### pyc 失效与重建的完整场景表

| 场景 | 校验依据 | 结果 |
|------|---------|------|
| 源码内容修改，mtime 更新 | 时间戳 | 重编译 ✅ |
| 源码内容修改，mtime 未变（git checkout 常发生） | 时间戳 | ❌ **误用旧 pyc**（PEP 552 hash 方案解决） |
| 源码 hash 变化 | hash（`-X` 相关策略或 PEP 552 配置） | 重编译 ✅ |
| Python 小版本升级（3.13 → 3.14） | magic number | 重编译 ✅（格式变了） |
| 同一版本跨机器拷贝 | 时间戳/hash | 校验通过则复用 |
| `PYTHONHASHSEED` 变化 | 无关 | 无影响（hash 用稳定算法） |

> **⚠️ 陷阱**：时间戳校验的"mtime 未变"场景在**版本管理工具还原、容器镜像层合并、文件同步**中最常见——源码看起来没问题，但运行的是旧字节码。解法：启用 hash-based pyc（`PYTHONPYCACHEPREFIX` 之外，可在部署脚本里先 `compileall` 或在构建时统一 touch），或接受"删掉 `__pycache__` 再跑"的运维铁律。

### 10.2.4 自定义 import 钩子

`sys.meta_path` 是公开列表——把自定义 `MetaPathFinder` 插到最前面，就能**劫持导入**。这是 Python 生态最强大的扩展点之一。

#### 最小示例：从字符串导入模块

```python
import sys, types
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec

SOURCE = """
def greet():
    return "hello from virtual module"
"""

class StringLoader(Loader):
    def create_module(self, spec):
        return None                       # 用默认模块创建
    def exec_module(self, module):
        exec(compile(SOURCE, module.__spec__.origin, "exec"), module.__dict__)

class StringFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "virtual_mod":
            return ModuleSpec(fullname, StringLoader(), origin="<virtual>")
        return None

sys.meta_path.insert(0, StringFinder())

>>> import virtual_mod
>>> virtual_mod.greet()
'hello from virtual module'
```

要点：

- `find_spec` 返回 `ModuleSpec` 即宣告"我能提供这个模块"；返回 `None` 则让位给下一个 finder；
- `exec_module` 负责把名字填进 `module.__dict__`——和 `SourceFileLoader` 执行 `.py` 文件是同一职责，只是"源代码"来自字符串；
- 插入 `sys.meta_path` **最前**，优先级最高；不匹配时**必须返回 `None`**，否则会阻断其他 finder。

#### 实战应用

| 场景 | 机制 |
|------|------|
| 插件系统 | 自定义 finder 按插件注册表动态合成模块 |
| 热加载 | finder + 缓存失效（移除 `sys.modules` 条目后重新 find） |
| pytest 的 `assert` 重写 | pytest 插入 `AssertionRewritingHook`（`MetaPathFinder`），在 `exec_module` 前用 AST 改写断言字节码 |
| 远程/虚拟模块 | 从数据库、URL、内存导入（`importlib` 官方文档的经典示例） |
| `import hook` 安全审计 | 监控 `sys.meta_path` 可发现恶意 import 劫持（见下方陷阱） |

> **⚠️ 陷阱**：`sys.meta_path` 是**全局**的，任何第三方库都能往里面插 finder——这正是"import 劫持攻击"的载体（`sitecustomize`/`.pth`/`PYTHONPATH` 都是投放点）。编写 import 钩子时：永远在 `find_spec` 里精确匹配模块名、其余情况返回 `None`；生产环境开启 `-P`（10.2.1）并审计 `sys.meta_path`。

#### 跨语言对比：模块加载钩子

"导入时可劫持"是 Python 独有还是通用能力？看其他语言怎么做：

| 语言 | 机制 | 可劫持性 |
|------|------|---------|
| Python | `sys.meta_path` 自定义 finder | ★★★ 完全开放，运行时动态 |
| Node.js | `require.cache` 操作、`Module._load` 覆写、`--require` 预加载钩子 | ★★ 可 hack，非官方 API |
| Java | `ServiceLoader`（SPI）、自定义 `ClassLoader` | ★★ 官方扩展点（`ClassLoader`），但复杂 |
| Go | `//go:linkname` 等 | ★ 编译期静态，无运行时钩子 |
| Rust | `#[cfg]` + feature | ☆ 编译期，无运行时动态导入 |

Python 与 Node 的对比最有启发：两者都是"运行时解析模块路径"，但 Python 把**查找协议**做成了公开接口（`sys.meta_path` 是文档化列表），Node 的钩子更多是"文档外的黑魔法"（覆写 `Module._load`）。Java 的 `ServiceLoader` 与 Python 的 `importlib.metadata.entry_points`（10.6.1）是同一思想：**声明式插件发现**。

> **设计哲学**："运行时导入可编程"是把双刃剑——它让插件系统、测试替身、热加载成为可能（Python 生态的活力来源），也让供应链攻击有了入口。Python 的选择是：**开放协议 + 文档化风险**（`sys.meta_path` 是官方列表、`-P` 是官方防御），而不是封闭系统。理解协议，才能既用其利、又防其害。

---

## 10.3 包：组织代码的目录层级

单个 `.py` 文件是模块，**包（package）是"带 `__path__` 的模块"**——一个目录，目录里的每个 `.py` 是子模块，目录本身是一个可被导入的模块对象。包让"几千行代码"的组织成为可能。

### 10.3.1 常规包与 __init__.py

```python
mypkg/
├── __init__.py          # 包的"主体"——导入 mypkg 时执行它
├── utils.py
└── models/
    ├── __init__.py
    └── user.py
```

```python
>>> import mypkg            # 执行 mypkg/__init__.py
>>> mypkg.__path__          # 包的搜索路径——PathFinder 用它找子模块
['/path/to/mypkg']
>>> import mypkg.utils      # 在 mypkg.__path__ 下找 utils.py
```

#### __init__.py 是"包的执行体"

`import mypkg` 与 `import mypkg.utils` 的关键差异：**导入子模块会先导入父包**（`__init__.py` 先执行）。所以：

- 空 `__init__.py` = "这个目录是包，但包本身不提供内容"；
- 有内容的 `__init__.py` = "导入包时运行这些初始化"。

```python
# mypkg/__init__.py
from .version import __version__   # 让 mypkg.__version__ 可用
from .core import Engine           # 提升子模块中的名字到包顶层

# 用法：用户无需知道 Engine 在 core 里
>>> import mypkg
>>> mypkg.Engine
<class 'mypkg.core.Engine'>
```

> **实战建议**：`__init__.py` 的两种常见风格——
> 1. **薄壳**：只放 `__version__` 和 `__all__`，一切走 `mypkg.submodule`（大库常用，避免导入开销）；
> 2. **收口**：把常用 API 提升到顶层（`mypkg.Engine` 而非 `mypkg.core.Engine`），用户友好。
> 库越大越应该薄壳——`__init__.py` 里 `import` 大量子模块会拖慢 `import mypkg` 本身（见 10.2.3 的性能讨论）。

#### __all__ 与 from pkg import *

```python
# mypkg/__init__.py
from .core import Engine, Config
__all__ = ["Engine", "Config"]     # 公开 API 收口
```

`from mypkg import *` 只取 `__all__` 列出的名字——**这是包层级的 API 契约**，也是 IDE 自动补全的依据。没有 `__all__` 时，`*` 会导入所有非 `_` 开头的名字——对包而言这几乎总是错的（会连带导入 `sys`、`os` 等被 `__init__.py` 间接引入的名字）。

> **⚠️ 陷阱**：`from mypkg import *` 若 `__init__.py` 里 `import os`，而 `__all__` 未定义——`os` 会被 `*` 导出。这不是 bug，是"没有 `__all__` 就没有 API 边界"。写包**必须**定义 `__all__`。

#### 子模块的导入路径

```python
import mypkg.models.user      # 完整路径
from mypkg.models import user # 等价
```

导入 `mypkg.models.user` 时，`PathFinder` 的查找过程是**逐层**的：先按 `sys.path` 找 `mypkg`（命中目录，且目录里有 `__init__.py` → 常规包），然后用 `mypkg.__path__` 找 `models`，再用 `models.__path__` 找 `user.py`。每层的 `__path__` 就是下一层的搜索范围——这就是"包 = 带 `__path__` 的模块"的完整含义。

#### 动态扩展 __path__：插件挂载点

`__path__` 是**普通列表**，可以在包初始化时修改——这给了包"动态声明自己包含哪些子目录"的能力：

```python
# mypkg/__init__.py
import os
_PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "..", "plugins")
__path__.append(_PLUGIN_DIR)      # 把插件目录纳入子模块搜索范围
```

```python
>>> import mypkg.plugin_a         # 不在 mypkg/ 目录下，但在 plugins/ 下
<module 'mypkg.plugin_a' ...>
```

标准库 `pkgutil.extend_path` 把这件事封装成"合并多个路径"的惯用法：

```python
# mypkg/__init__.py
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)   # 合并所有同名的包目录
```

```python
# pkgutil.extend_path 的效果等价于命名空间包的合并逻辑：
# 在 sys.path 上所有含 mypkg/ 的目录中，收集它们的路径进 __path__
```

> **实战模式**：`__path__` 动态扩展是"**目录级插件系统**"的底座——主包声明插件目录，插件以"放文件"的方式接入，无需改主包代码。它与 10.3.3 命名空间包（`PEP 420` 自动合并）互补：命名空间包是"静态多目录合并"，`__path__.append` 是"运行时任意指定"。注意：append 不存在的路径是无害的（`PathFinder` 找不到就跳过），所以插件目录可以先声明后创建。

### 10.3.2 相对导入（PEP 328 / 366）

#### . 和 .. 的真实语义

```python
# mypkg/models/user.py
from . import base            # 从当前包（mypkg.models）导入 base
from ..core import Engine     # 从父包（mypkg）的 core 导入 Engine
from .user import User        # 从当前包导入 user 模块（同目录）
```

| 写法 | 含义 |
|------|------|
| `from . import x` | 当前包内找 `x`（子模块或名字） |
| `from .mod import x` | 当前包的 `mod` 子模块里取 `x` |
| `from .. import x` | 父包内找 `x` |
| `from ..pkg.mod import x` | 祖父包（`..` 再往上）的 `pkg.mod` 里取 `x` |

相对导入的机制依赖 `__package__`（3.3 前）或 `__spec__.parent`（3.3+）：`. `的解析基准是"当前模块所属的包"。CPython 中 `importlib._bootstrap._calc___package__` 计算它。

```python
>>> import mypkg.models.user
>>> mypkg.models.user.__package__
'mypkg.models'
```

#### 为什么顶层脚本里相对导入必然报错

这是新手第一道坎：

```python
# scripts/run.py（作为顶层脚本运行）
# from .. import mypkg   ← 试图在顶层脚本里用相对导入
```

```python
$ python scripts/run.py
ImportError: attempted relative import with no known parent package
```

原因：顶层脚本的 `__package__` 是 `''`（空），`__spec__` 为 `None`——**它不属于任何包**，相对导入没有"当前包"可依。`sys.modules["__main__"]` 是一个没有包上下文的模块对象。

| 执行方式 | `__name__` | `__package__` | 相对导入 |
|---------|-----------|--------------|---------|
| `python run.py` | `"__main__"` | `''` | ❌ 失败 |
| `python -m scripts.run` | `"__main__"` | `"scripts"` | ✅ 可用（按包执行） |
| `import scripts.run` | `"scripts.run"` | `"scripts"` | ✅ 可用 |

> **🔑 核心结论**：`python file.py` 与 `python -m file` **不是等价物**——后者把文件当作"包内的模块"执行，`__package__` 被正确设置。**包内代码永远用 `python -m` 运行**，这是工程铁律。

#### 显式相对导入 vs 绝对导入

| 维度 | 相对导入（`.core`） | 绝对导入（`mypkg.core`） |
|------|-------------------|------------------------|
| 可读性 | 短，本地依赖一目了然 | 长，但自解释 |
| 重构 | 移动子包时内部引用自动跟随 | 顶层包名变了要全局改 |
| 歧义 | 无歧义，锁定"当前包" | 可能撞上 `sys.path` 上同名顶层包 |
| 规范立场 | PEP 8 允许，用于包内 | 社区主流（尤其大库） |

> **实战建议**：包内模块之间**优先相对导入**（同目录用 `.`，跨目录用 `..`），对外暴露的入口（`__init__.py`、`__main__.py`、测试）用绝对导入。混合使用时记住规则：**相对导入只认 `__package__`，顶层脚本没有 `__package__`**。

### 10.3.3 命名空间包（PEP 420）

#### 没有 __init__.py 时发生了什么

```python
ns_pkg/
└── color.py          # 注意：没有 __init__.py
```

```python
>>> import ns_pkg
>>> ns_pkg.__path__          # 不是 None！是命名空间包的路径列表
_NamespacePath(['/path/to/ns_pkg'])
>>> ns_pkg.__file__          # 没有文件
None
```

**PEP 420**（2012，3.3 起）规定：目录里没有 `__init__.py`，且**不属于任何常规包**时，它成为一个**命名空间包**——一个"只有 `__path__`、没有 `__init__.py` 可执行、没有 `__file__`"的模块。它的意义在下一小节。

#### 多目录合并：sys.path 上的同名目录

```python
# sys.path 上有两个目录都含 ns_pkg/（且都无 __init__.py）
/path1/ns_pkg/a.py
/path2/ns_pkg/b.py
```

```python
>>> import ns_pkg
>>> ns_pkg.__path__
_NamespacePath(['/path1/ns_pkg', '/path2/ns_pkg'])   # 两个目录合并！
>>> import ns_pkg.a
>>> import ns_pkg.b          # ✅ 都能导入
```

命名空间包的本质：**把 `sys.path` 上所有匹配的目录"拼接"成一个逻辑包**。`PathFinder` 发现某个路径条目下存在 `ns_pkg/` 目录且无 `__init__.py` 时，不立即判定"找不到"，而是**继续扫描后续路径条目**，把所有匹配目录收进 `__path__`。

> **版本注意**：3.3 之前没有命名空间包——`__init__.py` 是包的**必需**文件（PEP 328 时代）。PEP 420 把它变成可选，是为了支持"把同一逻辑包拆到多个独立安装的分发"（见下方场景）。如果你的包没有 `__init__.py` 却能 import，说明它已是命名空间包。

#### 适用场景与陷阱

| 场景 | 说明 |
|------|------|
| 插件生态 | 如 `zope.` 系列、`google.cloud` 风格：多个独立分发包贡献同一命名空间下的子包 |
| 大型 monorepo | 不同团队目录各自发布，共享顶层命名空间 |
| 容器/部署合并 | 多个只读文件系统层的同名目录自动合并 |

```python
# 陷阱 1：命名空间包没有 __init__.py 可执行——无法做包级初始化
# ❌ ns_pkg/__init__.py 不存在，以下代码不可能存在
# ✅ 需要初始化逻辑时，改用常规包（加 __init__.py）

# 陷阱 2：目录名冲突时谁赢？——都进 __path__，按 sys.path 顺序
# 若 /path1 是常规包（有 __init__.py）、/path2 是纯目录：
# 常规包优先，/path2 被忽略（PathFinder 找到常规包即停止）
```

> **⚠️ 陷阱**：常规包与命名空间包同名时，**常规包优先**——`PathFinder` 扫描到第一个含 `__init__.py` 的匹配目录就返回常规包 spec，不再合并后续目录。这会造成"我的插件目录为什么没生效"的迷惑。排查命令：`python -c "import ns_pkg; print(ns_pkg.__path__)"`。

### 10.3.4 包布局工程实践

#### src layout vs flat layout

```python
# flat layout（老式）
proj/
├── mypkg/
│   ├── __init__.py
│   └── core.py
└── tests/
    └── test_core.py

# src layout（现代推荐）
proj/
├── src/
│   └── mypkg/
│       ├── __init__.py
│       └── core.py
├── tests/
│   └── test_core.py
└── pyproject.toml
```

| 维度 | flat | src |
|------|------|-----|
| `import mypkg` 可用性 | 仓库根目录直接可用（未安装也能 import） | 需安装（`pip install -e .`）后才可用 |
| 测试隔离 | ❌ 测试可能 import 到仓库根而非已安装版本 | ✅ 强制测试已安装版本 |
| cwd 污染 | `python` 在仓库根运行时会误 import 根下的模块 | ✅ 干净 |
| 打包正确性 | 容易漏文件/把测试打进包 | ✅ 包边界清晰 |

> **实战建议**：新项目一律 **src layout** + `pip install -e .`（见 10.6.3）。flat layout 的唯一优势"未安装即可 import"恰恰是它的隐患——它让"开发环境"与"真实环境"不一致。`pip install -e .` 已经解决了开发体验问题，src 的收益没有代价。

#### 单模块包 vs 多模块包

```python
# 单模块包：名字即模块
myutil.py          # import myutil

# 多模块包：目录 + __init__
myutil/
├── __init__.py    # import myutil → 执行 __init__.py
├── core.py
└── io_utils.py
```

决策标准：**功能超过约 300–500 行、或有两个以上独立主题**，就升级为包。包带来的额外能力：子模块组织、`__path__` 扩展（插件挂载点）、`__all__` 收口、版本与元数据集中管理。

#### 包内命名约定

- 私有子模块：`_internal.py`（下划线前缀，声明"非公共 API"）；
- `__init__.py` 提升的公开名字 + `__all__` = 唯一公共面；
- 避免在包内用"模块名遮蔽标准库"（如包内放 `json.py`，`from . import json` 尚可，但 `import json` 在包内会拿到自己——危险）。

#### import 排序与编码规范（PEP 8 / isort）

模块头部是"第一个被读的部分"，PEP 8 对 import 有明确排序：

```python
"""模块 docstring。"""

import os                       # 1. 标准库
import sys

import requests                 # 2. 第三方库
import numpy as np

from mypkg import core          # 3. 本地包/模块
from mypkg.utils import helper
```

PEP 8 的三段式 + 组内字母序，`isort`/`ruff` 自动执行：

```bash
$ ruff check --select I src/          # 检查 import 排序
$ ruff check --select I --fix src/    # 自动修正
```

```python
# 为什么排序重要（不只是审美）：
# 1. import 是执行的——顺序影响"谁先初始化"，循环导入的触发与否可能只差一行顺序；
# 2. 代码评审时，"新增了哪个依赖"一目了然；
# 3. 与 __all__（10.3.1）一样，是"模块公共面"的可读性工程。
```

> **实战建议**：把 `ruff`（或 `isort` + `black`）作为 pre-commit 钩子固定下来。import 排序争议是团队内耗的经典来源，用工具终结争议（"机器说了算"）。

---

## 10.4 模块的高级玩法

### 10.4.1 模块级 __getattr__ / __dir__（PEP 562）

第 7 章讲过实例的 `__getattr__` 协议：属性查找失败时调用。**PEP 562**（2017，3.7）把同一协议带给了模块——模块对象也可以定义 `__getattr__`，在名字缺失时被调用：

```python
# mypkg/__init__.py
def __getattr__(name):
    if name == "deprecated_api":
        import warnings
        warnings.warn("deprecated_api 已废弃，请用 new_api", DeprecationWarning, stacklevel=2)
        return new_api
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

两大杀手级用途：

**1. 延迟加载子模块（lazy submodule）**

```python
# mypkg/__init__.py
def __getattr__(name):
    if name in ("heavy", "rarely_used"):
        import importlib
        mod = importlib.import_module(f"{__name__}.{name}")
        return mod
    raise AttributeError(...)

# 用户侧
>>> import mypkg
>>> mypkg.heavy            # 首次访问才加载 heavy 子模块（import 开销被推迟）
<module 'mypkg.heavy' ...>
```

这解决了"薄壳 vs 收口"的两难：`import mypkg` 仍然很快（不预载 heavy），但 `mypkg.heavy` 可用（按需加载）。注意 `import mypkg.heavy` 仍会立即加载——懒加载只对属性访问路径生效。

**2. 废弃 API 的兼容垫片（deprecation shim）**

```python
# 旧版：from mypkg import old_name
# 新版：old_name 移到 mypkg._legacy.old_name，仍保留 mypkg.old_name 访问
def __getattr__(name):
    if name == "old_name":
        warnings.warn("use mypkg.new_name instead", DeprecationWarning, stacklevel=2)
        return _legacy.old_name
    raise AttributeError(...)
```

配合 `__dir__` 让 `dir(mypkg)` 也正确：

```python
def __dir__():
    return sorted(set(globals()) | {"heavy"})    # dir() 可见性同步
```

> **版本注意**：模块级 `__getattr__` 是 Python 3.7+（PEP 562）。之前的标准做法是 `__init__.py` 里手动 `import` 或用 `sys.modules` 技巧——都不如 PEP 562 干净。注意：模块 `__getattr__` 中**访问未定义名字必须抛 `AttributeError`**，否则 `hasattr()` 等内省会得到错误结果。

### 10.4.2 模块即单例：全局状态的正确容器

模块天然是单例：`sys.modules` 保证"每个名字只加载一次"，模块命名空间就是"进程级全局状态"的官方容器。第 6 章说"函数是对象"，模块则是"**可被任何地方导入的全局单例**"。

```python
# appconfig.py —— 全局配置的正确载体
_settings = {"debug": False, "timeout": 30}

def get(key): return _settings[key]
def set(key, value): _settings[key] = value
```

```python
# 任意模块里
import appconfig
appconfig.set("debug", True)       # 全局可见
```

这比"全局变量 + `from appconfig import _settings`"更稳：`_settings` 带下划线是模块私有约定，且所有访问走函数收口。但请警惕模块单例的两个边界：

- **测试污染**：单例状态在测试间残留，需要 fixture 重置（`appconfig._settings.clear()`）；
- **并发**：多线程读写共享模块状态需要锁（第 11 章展开）；
- **导入时副作用**：`__init__.py` 顶层代码里连数据库、读文件、起线程——会让"import 你的包"变成"执行你的副作用"。**导入必须是幂等、可重复、快速的**，副作用放到显式的 `init()` 调用或 `lazy` 路径里。

> **工程影响**：`import` 时执行重量级副作用是"启动慢 + 测试难"的头号来源。规范：模块顶层只做**定义**（函数/类/常量），一切 I/O 和初始化交给显式函数。

#### 三种"单例"形态的选择

"全局只有一份"的需求有多个实现路径，机制与代价各异：

| 形态 | 实现 | 线程安全 | 适用 |
|------|------|---------|------|
| 模块单例 | 模块命名空间即单例（本节主题） | 天然（初始化在 import 时，GIL 下完成） | 配置、注册表、连接池 |
| 类单例 | `__new__` 拦截或类属性 | 需自行加锁 | 需要"对象语义"（可继承、可替换实例） |
| `functools.cache` 惰性单例 | 函数级缓存（第 6 章） | 天然 | 昂贵且幂等的"计算一次" |

```python
# 模块单例：最简单、零样板
# settings.py
_CFG = {"timeout": 30}
def get_timeout(): return _CFG["timeout"]

# 类单例：需要"它是对象"时（如可序列化、可被 isinstance 判断）
class Config:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

> **实战建议**：默认选**模块单例**——它零样板、测试易重置（`module._CFG.clear()`）、无继承复杂性。类单例只在你确实需要"把单例当对象传参/序列化/子类化"时才值得（第 7 章 7.4 的静态方法模式也讨论过类似权衡）。`functools.cache` 则是"函数级单例"——计算的单例，而非状态的单例。

### 10.4.3 循环导入：成因、危害与解法

#### 为什么会发生

```python
# a.py
import b
def a_func(): return b.b_func()

# b.py
import a
def b_func(): return "b"
```

```python
>>> import a
```

执行链：`import a` → a.py 执行到 `import b` → b.py 执行到 `import a` → 查 `sys.modules`：**`a` 已在里面（但只执行了一半！）** → 返回半成品 `a` → b.py 继续，`b_func` 定义完成 → 回到 a.py，继续完成。上面这个例子侥幸成功，因为 b 没有在导入期访问 `a` 的属性。真正的崩溃长这样：

```python
# a.py
import b
X = b.B_VALUE        # 导入期就访问 b 的属性

# b.py
import a
B_VALUE = a.X + 1    # ❌ AttributeError: module 'a' has no attribute 'X'
```

```python
>>> import a
Traceback (most recent call last):
  File "a.py", line 2, in <module>
    X = b.B_VALUE
AttributeError: module 'b' has no attribute 'B_VALUE'
```

b 在导入 `a` 时拿到的是**半初始化**的 `a`（`X` 还没定义），而 a 又在等 b 的 `B_VALUE`——死锁。**循环导入不是"两个文件互相 import"本身，而是"导入期就互相依赖对方的数据"**。

#### 四种解法（按推荐顺序）

```python
# 解法 1：延迟导入——把 import 移到函数内（最常用、改动最小）
# a.py
def a_func():
    import b                  # 运行时才导入，此时 b 已完整初始化
    return b.b_func()

# 解法 2：依赖倒置——把共享数据下沉到第三个模块
# common.py
VALUE = 10
# a.py
import common
X = common.VALUE
# b.py
import common
B_VALUE = common.VALUE + 1

# 解法 3：只做定义，不做初始化——导入期别访问对方属性
# a.py
import b
def a_func(): return b.b_func()     # ✅ 函数体内访问，导入期无依赖

# 解法 4：模块级 __getattr__（PEP 562）懒加载
# b.py
import a
def __getattr__(name):
    if name == "B_VALUE":
        return a.X + 1
    raise AttributeError(...)
```

> **🔑 架构信号**：循环导入几乎总是**"依赖方向画错了"**——两个模块互相依赖说明缺少抽象层。长期解法是重构出第三个模块（解法 2），延迟导入（解法 1）是止血，不是根治。真实项目里先看依赖图：`python -c "import mypkg; import pydeps..."` 或 `pip install pydeps` 可视化。

#### 一个真实的调试走查

```
场景：flask 应用 app.py ↔ models.py 互相 import
报错：ImportError: cannot import name 'db' from partially initialized module 'app'
```

排查路径：

1. 看 `sys.modules` 里两个模块的初始化状态——报错时 `app` 是"partially initialized"；
2. 找出**导入期的属性访问**：`models.py` 顶层写了 `from app import db`，而 `app.py` 顶层 `from models import User`——谁先导入谁吃亏；
3. 修复：把 `db`（`SQLAlchemy` 实例）下沉到独立 `database.py`，`app.py` 和 `models.py` 都从它导入——依赖图变成树状，问题消失。

> **实战模式**：依赖注入容器、ORM 实例、配置对象这类"被多方引用"的全局，永远放独立模块。一个包内**最多允许一层**"包内模块互相 import"，超过就要重构。

### 10.4.4 if __name__ == "__main__" 与脚本/模块双用

#### __name__ 在三种执行方式下的取值

```python
# mytool.py
print(f"__name__ = {__name__!r}")
```

| 执行方式 | `__name__` | 效果 |
|---------|-----------|------|
| `python mytool.py` | `"__main__"` | 顶层脚本，执行全部代码 |
| `python -m mytool` | `"__main__"` | 作为 `__main__` 模块执行（`__package__` 仍为 `''`） |
| `import mytool` | `"mytool"` | 作为模块导入，`__main__` 分支不执行 |

机制：`python mytool.py` 时，CPython 把 `mytool.py` 编译后以 `__main__` 的名字装进 `sys.modules["__main__"]` 执行。被 import 时则以 `"mytool"` 为名。`if __name__ == "__main__":` 就是检测"我是不是被当作入口执行"。

```python
def main():
    ...

if __name__ == "__main__":      # 双用模式：可导入（函数/类）也可直接运行
    main()
```

> **⚠️ 陷阱**：`python -m mytool` 与 `python mytool.py` 对 `__name__` 而言**没有区别**（都是 `"__main__"`）——但 `__package__` 有区别（见 10.3.2 表格）。所以 `-m` 的优势不是 `__name__`，而是**包上下文**：`python -m mypkg.scripts.run` 让 `run.py` 里的相对导入可用。

#### __main__.py：把目录/包变成可执行单元

```python
mypkg/
├── __init__.py
├── core.py
└── __main__.py        # 入口
```

```python
$ python mypkg            # 执行 mypkg/__main__.py（3.x 起目录可执行）
$ python -m mypkg         # 等价，且 __package__ 正确（推荐）
```

`__main__.py` 让一个包同时是"库"和"命令行工具"。结合 10.3.2 的规则，`__main__.py` 内部**必须用绝对导入或相对导入**（它位于包内，`__package__` 存在，相对导入可用）：

```python
# mypkg/__main__.py
from .cli import main      # ✅ 相对导入可用（-m 执行时 __package__='mypkg'）

# ❌ 错误：$ python mypkg 直接执行 __main__.py 时 __package__ 可能为空
# 用 python -m mypkg 执行则无此问题
```

> **实战建议**：命令行工具统一用 `python -m mypkg` + `__main__.py` 组织，并把真正的逻辑放 `cli.py`/`app.py`（`__main__.py` 只做入口转发）。这样 `main()` 可被测试直接导入，不用 subprocess。

#### python -m 的完整机制：runpy 在幕后

`python -m mypkg` 不是"import mypkg 然后执行"的语法糖，它走的是 `runpy` 模块：

```
$ python -m mypkg
  → runpy.run_module("mypkg", run_name="__main__")
  → 在 sys.path 上定位 mypkg（含其 __main__.py）
  → 以 __name__ = "__main__" 执行 mypkg/__main__.py
  → sys.modules["__main__"] 指向该模块；sys.modules["mypkg"] 是另一个对象
```

```python
# runpy 的等价手写（理解机制）
import runpy
runpy.run_module("mypkg", run_name="__main__")
```

关键差异点（对比 `python mypkg/__main__.py`）：

| 维度 | `python -m mypkg` | `python mypkg/__main__.py` |
|------|-------------------|---------------------------|
| `sys.path[0]` | cwd（`''`） | `mypkg/` 目录 |
| `__package__` | `"mypkg"`（相对导入可用） | `''`（相对导入失败） |
| 包身份 | 按"已安装/可导入的包"定位 | 按文件系统路径定位 |
| 依赖包内其他模块 | ✅ 正常 | ⚠️ 依赖 cwd 恰好正确 |

> **🔑 结论**：`-m` 是"以包的身份运行"，`python 路径.py` 是"以文件身份运行"。凡代码在包内（有相对导入、有包内依赖），一律 `-m`。`python -m` 还常用于：`python -m pip`、`python -m http.server`、`python -m venv`——标准库工具全部以 `-m` 为推荐入口。

#### sitecustomize 与 usercustomize：启动即导入的钩子

在 10.2.1 说过 `site` 模块启动时构建 `sys.path`。`site` 还有第二份工作：**尝试导入 `sitecustomize` 和 `usercustomize` 两个模块**（若存在）：

```python
# site-packages/sitecustomize.py —— 每次 Python 启动都会执行
import sys
sys.setrecursionlimit(100_000)          # 改默认递归深度
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)   # 过滤告警
```

| 钩子 | 加载时机 | 典型用途 |
|------|---------|---------|
| `sitecustomize` | 每次启动，`site` 初始化末尾 | 全局默认值、公司内部代理、自定义编码 |
| `usercustomize` | 同上（`ENABLE_USER_SITE` 时） | 个人开发环境偏好 |

```python
# 查看当前是否加载了它们
>>> import sitecustomize, usercustomize
>>> sitecustomize.__file__
'/usr/local/lib/python3.14/site-packages/sitecustomize.py'
```

> **⚠️ 安全**：`sitecustomize.py` 与 `.pth`、`PYTHONPATH`、`sys.meta_path` 注入并列为"import 系统的四大投放点"——任何能往 `site-packages` 写文件的人，都能让**每次 Python 启动执行任意代码**。排查"Python 莫名其妙变慢/多出网络请求"时，先检查这四个地方（`python -c "import site; print(site.getsitepackages())"` 定位目录）。

#### import 安全总览：四个投放点与三层防护

```python
# 攻击链示例：恶意 PYTHONPATH 或 cwd 里的同名文件
# cwd/requests.py  —— 一个假的 requests
import sys
sys.path.insert(0, ".")        # 攻击者控制 cwd
import requests                # ✅ 你的代码里正常 import → 拿到的是假 requests
```

| 投放点 | 攻击方式 | 防护 |
|--------|---------|------|
| `PYTHONPATH` | 注入路径遮蔽标准库/第三方包 | `-P` / `PYTHONSAFEPATH`（3.11+） |
| cwd / 脚本目录 | 同名文件遮蔽（`json.py`） | `-P`；不从未信任目录运行 |
| `.pth` / `sitecustomize` | 启动即执行代码 | 锁定 `site-packages` 写权限；审计 |
| `sys.meta_path` 注入 | 劫持模块加载 | 运行时 `sys.meta_path` 快照对比 |

```bash
# 生产环境默认开启
$ python -P -I app.py          # -I：隔离模式（隐含 -P、-E，忽略用户 site）
```

> **工程影响**：安全三层——(1) 运行层：`-P`/`-I` + 最小权限账户；(2) 依赖层：锁文件 + hash 校验（10.7.3），`site-packages` 只读；(3) 代码层：`import` 白名单审计、不信任 `sys.path` 上可写的目录。多数供应链攻击（如 2022 年以来多起 PyPI 投毒事件）走的正是"有人能往 `site-packages`/`PYTHONPATH` 写文件"这一条路。

---

## 10.5 虚拟环境：依赖隔离的工程基石

模块机制（10.1–10.4）解决"代码怎么组织"，虚拟环境解决"**依赖怎么隔离**"。没有隔离时，`pip install` 把所有包写进同一个 `site-packages`——项目 A 要 `numpy 1.26`、项目 B 要 `numpy 2.1`，直接冲突。虚拟环境就是"每项目一套 `sys.path` 的 `site-packages`"。

### 10.5.1 venv 的内部机制

```bash
$ python -m venv .venv
$ .venv\Scripts\python -m pip install numpy    # Windows
$ .venv/bin/python -m pip install numpy        # macOS/Linux
```

创建后看目录结构（Windows 为例）：

```
.venv/
├── pyvenv.cfg              # ★ 虚拟环境的"身份证"
├── Scripts/
│   ├── python.exe          # 启动器（不是完整的解释器！）
│   ├── pip.exe
│   └── activate.bat / Activate.ps1
└── Lib/
    └── site-packages/      # 本环境的第三方包
```

#### pyvenv.cfg：虚拟环境的"身份证"

```ini
home = C:\Python314          ; 基础解释器的位置
include-system-site-packages = false
version = 3.14.0
executable = C:\Python314\python.exe
```

`.venv\Scripts\python.exe` 是一个**启动器**（venvlauncher.exe），它读取 `pyvenv.cfg`：

1. 根据 `home` 找到**基础解释器**（base interpreter）的完整 Python——虚拟环境**不复制解释器**，只复制启动器；
2. 启动后强制设置 `sys.prefix = .venv`、`sys.base_prefix = C:\Python314`；
3. `site` 模块据此把 `site-packages` 指向 `.venv\Lib\site-packages`，**而不包含**基础解释器的 `site-packages`（`include-system-site-packages = false`）。

```python
>>> import sys
>>> sys.prefix          # 虚拟环境
'D:\\proj\\.venv'
>>> sys.base_prefix     # 基础解释器
'C:\\Python314'
>>> sys.path            # 注意：没有 C:\Python314\Lib\site-packages
['', 'D:\\proj\\.venv\\Lib\\site-packages', ...标准库..., 'C:\\Python314\\Lib\\site-packages' if include-system-site-packages]
```

> **🔑 机制洞察**：虚拟环境 = "**启动器 + pyvenv.cfg + 独立的 site-packages**"，不是"第二个 Python"。解释器本体（`python314.dll`、标准库）仍在基础位置，通过 `home` 复用。所以 venv 创建**秒级完成**、体积小——与 conda 的"完整克隆解释器"形成对比（见 10.5.2）。

#### 为什么虚拟环境整体可复制、可移动

`pyvenv.cfg` 的 `home` 在 3.11 之前是**绝对路径**，移动 venv 目录后启动器找不到基础解释器。**3.11+ 支持相对 `home`**（创建时用 `python -m venv --copies` 或默认行为的变化），配合"`sys.prefix` 由启动器根据自身位置推导"的设计，**整个 `.venv` 目录可以复制到另一台机器**（只要基础 Python 版本一致）——这是"venv 可移植"的底层原因。

> **版本注意**：venv 可移动性在 3.11 显著增强（PEP 相关改进：相对路径解析）。旧版本（≤3.10）移动 venv 后 `pyvenv.cfg` 的绝对 `home` 会失效，需手动修正或重建。**可移植 ≠ 跨平台**：Windows 建的 venv 不能拿到 Linux 用（启动器是平台二进制）。

#### activate 到底做了什么

```bash
$ .venv\Scripts\activate        # Windows（cmd）
$ source .venv/bin/activate     # macOS/Linux
```

`activate` **只是修改 shell 环境变量**：把 `.venv\Scripts` 插到 `PATH` 最前，让裸 `python`/`pip` 指向虚拟环境。它**不修改任何 Python 内部状态**——你完全可以用 `.venv\Scripts\python.exe` 直接调用，效果等同。工程上推荐**不用 activate**，直接全路径调用或配置 IDE 解释器，避免"激活了哪个环境"的隐式状态。

#### venv 实操参数与常见坑

```bash
$ python -m venv --system-site-packages .venv   # 允许看到基础环境的 site-packages
$ python -m venv --copies .venv                 # 复制解释器（默认符号链接/硬链接）
$ python -m venv --upgrade .venv                # 升级到当前解释器版本
```

```python
# include-system-site-packages = true 时的 sys.path 特例：
# 基础解释器的 site-packages 被加进来 —— 用于"系统装了大型库，不想重复装"的场景
```

| 坑 | 现象 | 解法 |
|----|------|------|
| 裸 `pip` 装错环境 | 装进系统 Python | 永远用 `python -m pip`（10.2.1 的调试技巧） |
| Windows 上 `python` 找不到 | 未加入 PATH 或 `py` 启动器未选对 | `py -3.14 -m venv .venv` 指定版本 |
| 激活状态丢失 | 新开终端 `python` 又变回系统版 | 用 IDE 配置解释器为 `.venv\Scripts\python.exe`，不依赖 activate |
| venv 目录被移动（≤3.10） | 启动报 `Could not find platform independent libraries` | 重建 venv，或升级到 3.11+ 的相对 home |

> **版本注意**：venv 的"可移动性"在 3.11 前后是分水岭——3.11+ 创建时默认记录**相对路径**（`pyvenv.cfg` 里 `home = .` 的变体），整个目录可复制；更早版本写死绝对路径。部署脚本里判断：`python -c "import sys; print(sys.version_info >= (3, 11))"`。

### 10.5.2 venv / conda / uv 三方对比

| 维度 | venv（标准库） | conda | uv |
|------|---------------|-------|-----|
| 隔离级别 | 依赖级（共享基础解释器） | **解释器级**（每环境独立 Python 副本） | 依赖级 |
| 创建速度 | 秒级（只复制启动器） | 分钟级（克隆解释器） | 亚秒级（硬链接） |
| 解释器版本管理 | ❌ 用系统已有 Python | ✅ 任意版本独立安装 | ✅ `uv python install 3.12` |
| 非 Python 库 | ❌ | ✅（C 库、CUDA 等） | 部分（`uv` 聚焦 Python 生态） |
| 包解析 | 调 pip | conda 解析器 | **Rust 并行解析器** |
| 锁文件 | ❌（配合 pip-tools/uv 等） | environment.yml | ✅ `uv.lock` |

> **决策矩阵**：
> - 纯 Python 项目 → **uv**（速度 + 锁文件）或 **venv + pip**（零依赖，标准方案）；
> - 需要多种 Python 版本切换 → **uv**（`uv python install`）或 **conda**；
> - 数据科学全家桶（CUDA、MKL、R 等非 Python 依赖）→ **conda**（mamba 加速）；
> - 团队协作、CI/CD → uv 或 venv + requirements 锁定。

#### uv 的极速原理

`uv`（Rust 实现）快在三个机制：

1. **全局内容寻址缓存**：`~/.cache/uv` 里按内容 hash 存每个 wheel 的**解压结果**，新环境通过**硬链接**引用——不重新下载、不重新解压、不复制字节；
2. **并行解析**：解析依赖树时并发请求 PyPI，多线程下载；
3. **内建解析器**：跳过 pip 的"下载 metadata → 评估 → 回溯"串行循环，用 `Requires-Python`/`Requires-Dist` 预筛。

```bash
$ uv venv .venv            # 创建（≈50ms）
$ uv pip install numpy     # 解析+下载+链接（缓存命中时 <1s）
$ uv sync                  # 按 uv.lock 精确复现
```

> **工程影响**：uv 的硬链接方案有个前提——**缓存与 venv 在同一文件系统**（硬链接不能跨设备）。CI 里把 `UV_CACHE_DIR` 设为持久化缓存目录，能省掉每次流水线重下依赖的时间。

#### conda 内部：解释器级隔离的代价与必要

`conda create -n tf python=3.11 numpy cuda-toolkit` 与 venv 的本质差异：

```
conda env 的目录树（完整、自洽）
envs/tf/
├── python.exe            # ★ 真实的解释器副本（不是启动器）
├── Library/bin/*.dll     # 非 Python 依赖（MKL、CUDA、openssl...）
├── Lib/site-packages/
└── conda-meta/           # 环境内已装包清单（JSON）
```

- **每环境一份完整 Python**：`sys.prefix == sys.base_prefix`，解释器与库完全自包含——代价是创建慢（分钟级）、体积大（数百 MB）；
- **`conda-meta/` 是环境的锁**：类似 `sys.modules` 之于模块，conda 用它记录环境内每个包的确切版本与文件清单；
- **pkgs 缓存 + 硬链接**：`~/anaconda3/pkgs/` 是内容缓存，新环境通过硬链接复用，避免重复拷贝——与 uv 的缓存思路同构。

> **决策补充**：conda 的**不可替代场景**是"非 Python 依赖"——CUDA 驱动库、MKL 数学库、R 包、系统级二进制。这些 pip/uv 装不了（或装不好）。而 conda 的代价：解析慢（`conda` 本体 Python 实现，`mamba` 用 C++ 重写解析器提速数倍）、与 PyPI 的包版本不完全对齐、环境迁移不如 venv 轻。**规则**：项目依赖全是 Python 包 → venv/uv；需要系统级库 → conda/mamba。

---

## 10.6 打包与分发：从代码到可安装的发行版

虚拟环境解决"装在哪"，打包解决"**装什么、怎么装**"。现代 Python 打包的完整链路（PEP 517/518/621/427/660 等）围绕一个文件展开：`pyproject.toml`。

### 10.6.1 pyproject.toml 与 PEP 517 / 518 / 621

#### 一个最小 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]            # 构建时需要的工具（构建后端）
build-backend = "hatchling.build"   # 构建后端入口

[project]
name = "mypkg"
version = "1.0.0"
description = "A demo package"
requires-python = ">=3.9"
dependencies = ["requests>=2.28"]   # 运行时依赖
```

三个 PEP 各管一块：

| PEP | 年份 | 内容 |
|-----|------|------|
| PEP 518 | 2016 | 定义 `[build-system]`：**构建工具本身**怎么装 |
| PEP 517 | 2015 | 定义构建后端接口：`build_wheel()` / `build_sdist()` / `prepare_metadata_for_build_wheel()` |
| PEP 621 | 2020 | 定义 `[project]`：**标准化的包元数据**（名字/版本/依赖/入口点） |

#### 为什么"装你的包"需要"先装一个工具"

这是新手最费解的一环。`pip install mypkg` 时，如果只有 sdist（源码包），pip 必须**构建 wheel**，而构建需要构建后端（setuptools/hatchling…）。但 pip 不能假设机器上有哪个后端——所以：

```
pip install mypkg
  → 读 pyproject.toml 的 [build-system]
  → 在【隔离环境】里安装 requires（如 hatchling）
  → 调用 build-backend.build_wheel() 得到 wheel
  → 安装 wheel
```

```python
# 构建后端接口（PEP 517）——你的打包工具只需实现这几个函数
def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """返回 wheel 文件名"""
def build_sdist(sdist_directory, config_settings=None):
    """返回 sdist 文件名"""
```

> **设计哲学**：构建后端是**独立可插拔**的——`setuptools`、`hatchling`、`flit_core`、`pdm-backend` 都是 PEP 517 后端的实现，任何实现都能被 pip 驱动。这把"打包工具"从"pip 的附属"解放为"标准协议上的自由竞争"（类似第 10.2.4 的 import 钩子哲学）。

#### 构建后端对比

| 后端 | 特点 | 适合 |
|------|------|------|
| `setuptools` | 老牌、生态最大、配置兼容 `setup.py` | 迁移老项目、复杂构建 |
| `hatchling` | 现代、纯 `pyproject.toml`、内置版本管理 | 新项目默认推荐 |
| `flit_core` | 极简、面向纯 Python 小包 | 单模块/简单库 |
| `pdm-backend` | PDM 项目自带、支持 PEP 621 完整 | PDM 用户 |
| `meson-python` | C/C++ 扩展的现代构建 | 混合项目 |

#### 完整 pyproject.toml 实战示例

一个生产级 `pyproject.toml` 覆盖 PEP 621 元数据、可选依赖（extras）、入口点、构建细节：

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mytool"
version = "1.0.0"
description = "CLI tool demo with plugins"
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["cli", "demo"]
classifiers = [                       # PyPI 分类（必须来自 trove 分类器列表）
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
]

dependencies = [
    "click>=8.0",
    "rich>=13; python_version >= '3.11'",      # 环境标记条件依赖
]

[project.optional-dependencies]       # extras：可选功能组
dev = ["pytest>=7", "ruff", "mypy"]
docs = ["mkdocs>=1.5"]
test = ["pytest-cov"]

[project.scripts]                     # 安装后生成命令
mytool = "mytool.cli:main"

[project.entry-points."mytool.plugins"]   # 插件注册表（见下方）
format-json = "mytool.plugins.json:Plugin"
format-yaml = "mytool.plugins.yaml:Plugin"

[tool.hatch.build.targets.wheel]      # 构建后端专属配置
packages = ["src/mytool"]
```

安装与使用：

```bash
$ pip install "mytool[dev]"           # 基础依赖 + dev extras
$ mytool                              # 来自 [project.scripts]
```

**extras 的机制**：`mytool[dev]` 展开为"`mytool` 的基础依赖 + `dev` 组的依赖"（PEP 508 依赖描述语法）。用户按需选择功能，避免"为了文档装整套依赖"。

**entry points 的双重身份**：

```python
# 身份 1：console scripts（[project.scripts]）——生成可执行命令
# 身份 2：插件注册表（任意分组名）——importlib.metadata 可查询
>>> from importlib.metadata import entry_points
>>> eps = entry_points(group="mytool.plugins")
>>> eps
[EntryPoint(name='format-json', value='mytool.plugins.json:Plugin', group='mytool.plugins'),
 EntryPoint(name='format-yaml', value='mytool.plugins.yaml:Plugin', group='mytool.plugins')]
>>> Plugin = eps["format-json"].load()      # 动态导入并取对象
<class 'mytool.plugins.json.Plugin'>
```

`importlib.metadata`（PEP 376 的现代实现）是"**已安装包的信息入口**"：`version()`、`metadata()`、`entry_points()`。插件系统用它替代"手工扫描目录"——声明式、可校验、可卸载。

> **实战建议**：entry points 是 Python 生态插件系统的**标准接口**（pytest 的插件、Jupyter 的 kernelspec、setuptools 的命令都是它）。`EntryPoint.load()` 内部就是 `importlib.import_module` + 属性取用——和 10.2.4 的 import 钩子呼应：import 系统提供的灵活，最终成就了插件生态的繁荣。

#### 版本单一来源（single source of truth）

`pyproject.toml` 里写了 `version = "1.0.0"`，但代码里常常还想访问版本（`mypkg.__version__`）。**版本只应有一处定义**，否则改版本要改两处、三处，必然漂移。四种方案：

```python
# 方案 1：运行时从元数据读取（推荐，零维护）
# mypkg/__init__.py
from importlib.metadata import version
__version__ = version("mypkg")      # 安装后始终与包元数据一致

# 方案 2：构建时注入（hatch-vcs/setuptools-scm 从 git tag 生成）
# pyproject.toml
# [tool.hatch.version]
# source = "vcs"                    # version = "1.0.0" 改为动态

# 方案 3：单文件常量 + 构建读取
# mypkg/_version.py
__version__ = "1.0.0"
# pyproject: dynamic = ["version"] + tool.hatch.version.path = "src/mypkg/_version.py"

# 方案 4（❌ 反模式）：两处硬编码
# pyproject.toml: version = "1.0.0"  与  mypkg/__init__.py: __version__ = "1.0.0"
```

```python
>>> import mypkg
>>> mypkg.__version__
'1.0.0'
>>> from importlib.metadata import version
>>> version("mypkg") == mypkg.__version__    # ✅ 方案 1/2/3 下恒等
True
```

> **实战建议**：追求零维护选**方案 1**（`importlib.metadata.version`，注意仅安装后可用，源码树里直接跑会报 `PackageNotFoundError`）；git 驱动发布选**方案 2**（`setuptools-scm`/`hatch-vcs`，版本号跟着 tag 走，天然单一来源）。无论哪种，**禁止**在 `pyproject.toml` 和代码里各写一份。

#### 打包配置演进史：setup.py → setup.cfg → pyproject.toml

今天的 `pyproject.toml` 是三代配置演进的终点，看懂历史才能理解遗留项目：

```python
# 第一代：setup.py（可执行脚本，Python 代码即配置）
from setuptools import setup
setup(name="mypkg", version="1.0", install_requires=["requests"])

# 第二代：setup.cfg（声明式，但仍是 setuptools 专属）
[metadata]
name = mypkg
version = 1.0
[options]
install_requires = requests

# 第三代：pyproject.toml（PEP 621 标准，后端无关）
[project]
name = "mypkg"
version = "1.0.0"
dependencies = ["requests"]
```

| 代 | 形态 | 问题 |
|----|------|------|
| `setup.py` | 可执行 Python | 构建时执行任意代码（安全 + 不可缓存）；配置与逻辑耦合 |
| `setup.cfg` | INI 声明 | 绑定 setuptools，无法换构建后端 |
| `pyproject.toml` | TOML 标准（PEP 621） | 解决前两代问题：声明式、后端无关、可被任何工具解析 |

> **版本注意**：`setup.py` 至今仍被支持（setuptools 兼容），但**新项目一律用 `pyproject.toml`**。你仍会看到大量 `setup.py` 老项目——读它们时知道"这是历史形态"即可。pip 的 PEP 517 隔离构建让"构建工具版本"不再污染宿主环境（10.6.1 已述）。

### 10.6.2 wheel 与 sdist（PEP 427 / 625）

#### 两种发行格式的本质

| | sdist（`mypkg-1.0.0.tar.gz`） | wheel（`mypkg-1.0.0-py3-none-any.whl`） |
|---|---|---|
| 内容 | 源码 + `pyproject.toml` + 构建脚本 | **构建产物**：`.py`/`.so` + 元数据 |
| 安装时 | **要先构建**（跑构建后端） | **直接解压安装** |
| 平台 | 通用 | 纯 Python 通用（`any`）或平台特定（`win_amd64`） |
| 类比 | 源码包（`apt source`） | 预编译二进制（`.deb`/`.msi`） |

```bash
$ python -m build            # 生成两种格式（需要 pip install build）
dist/
├── mypkg-1.0.0.tar.gz       # sdist
└── mypkg-1.0.0-py3-none-any.whl   # wheel
```

#### wheel 的内部结构

wheel 本质是**zip 文件**（`import zipfile` 可直接查看）：

```
mypkg-1.0.0-py3-none-any.whl
├── mypkg/__init__.py          # 实际代码
├── mypkg/core.py
└── mypkg-1.0.0.dist-info/     # 元数据目录
    ├── METADATA               # 依赖、描述（PEP 621 生成）
    ├── WHEEL                  # wheel 版本、标签
    └── RECORD                 # 所有文件 + hash 清单（卸载/校验用）
```

**wheel 文件名 = 平台标签**（PEP 625 规范化）：

```
{name}-{version}-{python tag}-{abi tag}-{platform tag}.whl
mypkg-1.0.0-py3-none-any.whl                    # 纯 Python，任何平台
examplepkg-1.2.3-cp314-cp314-win_amd64.whl      # 示例标签：CPython 3.14，Windows x64
numpy-2.2.0-cp313-cp313-manylinux_2_28_x86_64.whl   # 示例：CPython 3.13，Linux 兼容集
```

`py3-none-any` = 任何 Python 3、无 ABI 绑定、任何平台。C 扩展的 wheel 会把 `py3` 换成 `cp314`（CPython 版本）、`none` 换成 `cp314`（ABI 兼容性）、`any` 换成平台名。**`pip` 依据这些标签挑选匹配本机的最优 wheel**——这就是"`pip install` 为啥不装 sdist"的答案：有匹配 wheel 就不构建。

> **🔑 性能洞察**：`pip install wheel` 只是解压（秒级）；`pip install sdist` 要先建隔离环境、装构建依赖、跑构建（十秒到分钟级，还可能失败）。**发布包时同时发 sdist + wheel** 是规范；**安装时优先 wheel** 是 pip 默认策略。

#### 平台标签详解：cp314 / abi3 / manylinux 是什么

wheel 文件名里的三个标签（Python 标签 - ABI 标签 - 平台标签）是 pip 挑选 wheel 的匹配依据：

| 标签示例 | 含义 | 谁能装 |
|---------|------|--------|
| `py3-none-any` | 纯 Python，无 ABI 绑定 | 任何 Python 3、任何平台 |
| `cp314-cp314-win_amd64` | CPython 3.14 专属，Windows 64 位 | 仅 CPython 3.14 on Windows x64 |
| `cp38-abi3-win_amd64` | 稳定 ABI（PEP 384） | **CPython 3.8+ 全部版本**都能用 |
| `cp314-cp314-manylinux_2_28_x86_64` | Linux 发行版兼容集 | 多数现代 Linux x64 |

- **`cp314-cp314`**：第一个 `cp314` 是 Python 标签（CPython 3.14），第二个是 ABI 标签（与 CPython 3.14 的 C ABI 绑定）。C 扩展一般绑定具体版本，因为 `.pyd`/`.so` 里的符号与特定 CPython 的 ABI 相关；
- **`abi3`（PEP 384，2012）**：CPython 承诺的**稳定 C ABI**。按 abi3 构建的扩展一个 wheel 覆盖 3.8–3.14 所有版本——极大简化分发（`cryptography`、`pydantic-core` 等都用它）；
- **`manylinux`（PEP 599/600 等）**：Linux 上"兼容哪些发行版"的约定。`manylinux2014`/`manylinux_2_28` 表示基于特定 glibc 版本构建，向下兼容旧发行版——解决"在一台 Linux 上编的 .so 到另一台跑不起来"的经典问题。

```bash
# 排查"pip 找不到匹配 wheel"：查看本机标签
# 标准库先看平台（不需要额外依赖）
$ python -c "import sysconfig; print(sysconfig.get_platform())"
win-amd64
# 完整标签序列需要 packaging 库（pip 自带，可直接 import）
$ python -c "from packaging.tags import sys_tags; print(list(sys_tags())[:5])"
[Tag(interpreter='cp314', abi='cp314', platform='win_amd64'), ...]
```

> **⚠️ 陷阱**：`pip install` 报 `Could not find a version that satisfies the requirement` 或只找到 sdist 时，常见原因不是包不存在，而是**标签不匹配**——太老的 Python（如 3.7 找不到新包）、罕见平台、或该包只发布了源码包。此时 pip 会尝试 sdist 构建；构建失败（缺编译工具链）才报错。

#### 发布到 PyPI：twine 完整流程

```bash
$ pip install build twine
$ python -m build                     # 生成 sdist + wheel 到 dist/
$ twine check dist/*                  # 校验元数据/描述格式
$ twine upload -r testpypi dist/*     # 先上 TestPyPI 验证
$ pip install -i https://test.pypi.org/simple/ mypkg   # 试装
$ twine upload dist/*                 # 正式发布
```

`twine upload` 是**只上传构建产物**——它不重新构建，所以"构建"与"上传"分离（`setup.py upload` 已被弃用，因其在旧版曾把账号凭据写进明文历史）。上传前 `twine check` 必做：README 里的 Markdown 渲染问题、元数据缺字段都在这一步暴露。

### 10.6.3 editable install（PEP 660）

#### 为什么需要它

开发中改了源码想立刻生效。`pip install .` 会把代码**复制**进 `site-packages`——之后每次改代码都要重装。**editable install**（`pip install -e .`）让 `site-packages` 里的"包"**指向源码目录**，改完即生效。

#### 两种实现机制

**机制一：`.pth` 文件（setuptools 传统方案）**

```
# site-packages/__editable__.mypkg-1.0.0.pth（内容示例）
C:\proj\src        # 把源码目录加入 sys.path
```

`.pth` 把 `src/` 加进 `sys.path`，于是 `import mypkg` 直接命中源码——最朴素的"编辑即生效"。

**机制二：`__editable__` 导入钩子（PEP 660 后现代方案）**

```
# site-packages/__editable___mypkg_1_0_0_finder.py + .pth
# .pth 里 import 这个 finder，finder 把"包名 → 源码目录"的映射写进 sys.meta_path
```

后者的优势：不需要把源码目录整体塞进 `sys.path`（避免名字遮蔽，见 10.2.1 的 `PYTHONPATH` 讨论），而是精确地把 `mypkg` 映射到源码。

```bash
$ pip install -e .            # 现代 pip（>=21.3）走 PEP 660 协议
$ python -c "import mypkg; print(mypkg.__file__)"   # 指向源码！
C:\proj\src\mypkg\__init__.py
```

> **工程影响**：`pip install -e .` + src layout（10.3.4）是**开发环境的黄金组合**：测试、工具都能 `import` 到"真实包"，且改码即时生效。对比"手动设 `PYTHONPATH`"：editable 只影响本环境、可被 `pip freeze` 记录、卸载干净——工程上完胜。

### 10.6.4 依赖声明与版本约束

#### PEP 440 版本说明符：`~=1.4` 到底是什么意思

| 写法 | 等价展开 | 含义 |
|------|---------|------|
| `==1.4.5` | `==1.4.5` | 精确匹配 |
| `>=1.4,<2` | `>=1.4,<2` | 范围 |
| `~=1.4.5` | `>=1.4.5,==1.4.*` | **兼容性匹配**：允许补丁级升级，锁死次版本 |
| `~=1.4` | `>=1.4,==1.*` | 兼容性匹配：允许次版本升级，锁死主版本 |
| `!=1.4.*` | — | 排除系列 |
| `*`（通配） | `==1.4.*` | 系列匹配 |

`~=` 的规则：`~=X.Y.Z` 表示 `>=X.Y.Z` 且 `<X.(Y+1)`（最后一段之后封顶）。`~=1.4.5` 允许 `1.4.9`，不允许 `1.5.0`；`~=1.4` 允许 `1.9`，不允许 `2.0`。

> **实战建议**：库的 `dependencies` 用**宽松范围**（`>=1.4,<2`），把精确锁定留给锁文件（10.7.3）。库把依赖锁死（`==1.4.5`）会与用户的依赖冲突——"依赖地狱"的根源。

#### PEP 508 依赖描述与环境标记

```toml
[project]
dependencies = [
    "requests>=2.28",
    "numpy>=1.21; python_version < '3.11'",      # 环境标记：条件依赖
    "tomli>=2.0; python_version < '3.11'",       # 3.11 前需要回填包
    "colorama>=0.4; sys_platform == 'win32'",    # 平台条件
]
```

`;` 后面是**环境标记**（environment marker）：`python_version`、`sys_platform`、`platform_machine` 等变量在**安装时**求值，pip 只安装满足条件的依赖。这是"同一份 pyproject 跨平台正确安装"的机制。

---

## 10.7 依赖管理实战：pip 与 uv

打包协议（10.6）回答"包长什么样"，本节回答"**依赖树怎么解析、怎么锁定、怎么复现**"。

### 10.7.1 pip 的解析过程与陷阱

#### 解析器在做什么

```bash
$ pip install "numpy>=1.20" "pandas>=2.0"
```

pip 必须找到一组**同时满足所有约束**的版本：`pandas 2.x` 要求 `numpy>=1.22.4`，与用户的 `numpy>=1.20` 取交集 → 实际约束变成 `numpy>=1.22.4`。这就是"解析器"：构建依赖图、传播约束、回溯冲突。

```python
# 冲突示例：三个包对 numpy 的要求互斥
$ pip install "a>=1" "b>=1"
ERROR: Cannot install a and b because these package versions have conflicting dependencies.
The conflict is caused by: a 1.0 depends on numpy<2.0; b 1.0 depends on numpy>=2.0
```

**2020 年 pip 换了默认解析器**（旧版回溯式解析器 → 新版"依赖解析器"）：旧版按直觉顺序解析，遇冲突直接报错；新版做完整回溯，能给出更精确的冲突报告，但更慢。

> **⚠️ 陷阱**：`pip install` 的解析结果**不做持久化**——明天再装可能装到不同版本（上游发了新版本）。"今天能跑，明天不能跑"多半源于此。解法：锁文件（10.7.3）。

#### pip 的经典痛点

1. **无锁文件**：`requirements.txt` 需要自己维护，无法自动解析传递依赖的精确版本；
2. **解析慢**：Python 实现，串行请求 metadata；
3. **环境切换慢**：每次 `pip install` 都要重新解析；
4. **无自动回滚**：装坏一个包，只能手动 `uninstall`。

#### 一个真实的冲突排查案例

```
症状：pip install 一个新包后，import 时报 ImportError
$ pip install mytool        # 成功
$ python -c "import mytool"
ImportError: cannot import name 'X' from 'somepkg'
```

排查链（对应 10.7.3 的三段法）：

```bash
$ pip check                                   # ① 已装包自洽性
somepkg 2.0 requires numpy<2.0, but you have numpy 2.1.0 which is incompatible.
```

```bash
$ pipdeptree -p somepkg                        # ② 谁依赖了它、谁引入了冲突
somepkg==2.0
└── mytool==1.0 [requires: somepkg>=2.0]
$ pip show somepkg | Select-String Location    # ③ 确认装在哪
Location: C:\proj\.venv\Lib\site-packages
```

结论：`mytool` 引入的 `somepkg 2.0` 与既有 `numpy 2.1` 冲突，`X` 在 numpy<2 的分支下才有。修复：`pip install "somepkg==1.9"` 或用 `pip-compile` 生成全树锁定后 `pip-sync`——**从"一个个装"升级为"按锁定文件整体同步"**，这类漂移问题就失去了生存空间。

> **实战模式**：任何"新装包后旧代码炸了"的场景，先 `pip check` 确认是不是依赖冲突，再决定"降级新包"还是"升级旧约束"。不要直接改代码——多数时候是环境漂移，不是代码 bug。

### 10.7.2 uv：命令对照与迁移路径

uv 是 pip/venv/pip-tools 的现代替代（Rust 实现），命令高度兼容：

| 传统 | uv 等价 | 说明 |
|------|--------|------|
| `python -m venv .venv` | `uv venv` | 创建环境（亚秒级） |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` | 安装 |
| `pip freeze > requirements.txt` | `uv pip freeze` | 冻结 |
| `pip install -e .` | `uv pip install -e .` | 可编辑安装 |
| — | `uv sync` | **按锁文件精确复现**（删除多余包） |
| — | `uv lock` | 生成/更新 `uv.lock` |
| `pip install --upgrade pip` | `uv self update` | 升级 uv 自身 |

```bash
$ uv init myproj && cd myproj     # 生成 pyproject.toml + src layout
$ uv add requests                 # 解析 + 安装 + 写进 pyproject + 更新 uv.lock
$ uv run python app.py            # 自动用项目环境执行
```

> **工程影响**：uv 的 `uv run`/`uv sync` 把"环境即代码"落到实处——`uv.lock` 提交进 git，任何机器 `uv sync` 得到**逐字节一致**的环境。CI 里加缓存（`UV_CACHE_DIR` 持久化）后，依赖安装从分钟级降到秒级。

#### uv 的多 Python 版本管理

`venv` 只能基于"系统已装的解释器"建环境，`uv` 把解释器本身也纳入了管理：

```bash
$ uv python install 3.12 3.13        # 下载管理多个 CPython（存 ~/.local/share/uv/python）
$ uv python list                     # 查看已安装
$ uv venv --python 3.12 .venv312     # 指定解释器建环境
$ uv run --python 3.13 script.py     # 指定解释器运行
```

这补齐了 venv 对比 conda 的最大短板（解释器级管理）。`uv python` 的机制：下载官方 CPython 发行包到**用户级缓存**，建环境时按 `pyvenv.cfg` 的 `home` 指向它——与 10.5.1 的 venv 机制完全一致，只是"基础解释器"由 uv 代为获取。

> **实战建议**：`pyproject.toml` 的 `requires-python = ">=3.9"` 是"声明兼容窗口"，`uv python install` 是"实际准备哪些解释器"。CI 里用 `uv python install` 替代 `actions/setup-python`，同一套命令本地/CI 一致。需要测试多版本兼容性时：`uv run --python 3.10` / `--python 3.12` 各自跑一遍测试即可。

### 10.7.3 可复现环境：锁文件与 hash 校验

#### requirements.txt 精确锁定 vs 语义范围

```txt
# 方式一：范围（可复现性差）
numpy>=1.26

# 方式二：精确锁定（可复现）
numpy==1.26.4

# 方式三：pip-tools/uv 生成（含传递依赖 + hash）
numpy==1.26.4 \
    --hash=sha256:2a02abaec693e4a1d3c... \
    --hash=sha256:...
```

| 层级 | 工具 | 可复现性 |
|------|------|---------|
| 顶层范围 | 手写 `requirements.txt`（`numpy>=1.26`） | ❌ 每次安装可能不同 |
| 直接锁定 | `pip freeze` / 手写 `==` | ⚠️ 顶层锁定，传递依赖漂移 |
| **全树锁定** | `pip-compile`、`uv lock` | ✅ 每个传递依赖都锁死 |
| 全树锁定 + 校验 | uv.lock / pip hash 模式 | ✅✅ 版本 + 内容 hash 双保险 |

#### 锁文件的哲学

```python
# 为什么不能只用 pyproject 的范围声明？
# pyproject:  "库的兼容窗口"（宽松，给使用方弹性）
# 锁文件:     "应用的精确事实"（严格，保证可复现）

# 库 → 发布 pyproject.toml（范围约束），不提交锁文件
# 应用 → 提交 uv.lock / requirements-lock.txt（精确版本 + hash）
```

> **实战建议**：
> - **应用/服务**：提交锁文件，CI 与生产用同一份；升级 = 显式改锁文件 + 跑测试；
> - **库**：只声明范围约束，锁文件不提交（用户需要弹性）；
> - **安全**：开启 hash 校验（`uv` 默认写入 `uv.lock` 的 hash；pip 用 `--require-hashes`）——锁文件本身是供应链攻击的目标，hash 校验让"锁文件被篡改"无法静默生效。

#### pip-tools：经典锁文件工作流

不想引入 uv 的团队，用 `pip-tools` 得到同样的"范围声明 + 全树锁定"：

```bash
$ pip install pip-tools

# requirements.in —— 手写"范围声明"（库视角）
numpy>=1.26
pandas>=2.0

# 生成全树锁定（含传递依赖的精确版本）
$ pip-compile requirements.in
$ cat requirements.txt
numpy==1.26.4
pandas==2.2.2
python-dateutil==2.9.0.post0
pytz==2024.1
...

# 同步环境到锁定状态（删除多余包）
$ pip-sync requirements.txt
```

| 工具 | 输入 | 输出 |
|------|------|------|
| `pip-compile` | `requirements.in`（范围） | `requirements.txt`（全树 `==` 锁定） |
| `pip-sync` | `requirements.txt` | 让环境与该文件**完全一致**（含卸载多余的） |
| `pip freeze` | 当前环境 | 扁平 `==` 列表（不含传递依赖来源信息，不可作构建输入） |

> **注意**：`pip freeze` 常用于记录环境，但它是"结果的快照"而非"约束的解析"——缺 hash、缺来源标注，且**可能包含本机残留包**。规范的锁定请用 `pip-compile`/`uv lock`。

#### 依赖调试：pipdeptree

依赖冲突排查的第一工具是**依赖树可视化**：

```bash
$ pip install pipdeptree
$ pipdeptree                        # 整棵树
$ pipdeptree -p numpy               # 谁依赖了 numpy（反向查询）
numpy==1.26.4
├── pandas==2.2.2 [requires: numpy>=1.22.4]
└── scikit-learn==1.5.0 [requires: numpy>=1.19.5]
$ pipdeptree --warn                 # 检查冲突
Warning: numpy 1.26.4 conflicts with pandas (requires numpy<2.0)  # 示例
```

配合 `pip check`（检查已安装包的依赖一致性）快速定位"运行时 ImportError 是不是装坏了"：

```bash
$ pip check
No broken requirements found.
```

> **实战模式**：依赖问题三段排查——(1) `pip check` 查"已装包自洽性"；(2) `pipdeptree -p <包名>` 查"冲突来源"；(3) 锁文件 + 干净环境复现（`uv sync` 或 `pip-sync`）确认是"环境漂移"还是"声明错误"。

---

## 10.8 部署形态：可执行包

wheel 是"库的形态"，命令行工具还需要"**可执行形态**"。本节三种方案从"零依赖单文件"到"自声明依赖脚本"。

### 10.8.1 zipapp：把包打成单个 .pyz 文件

`zipapp` 把整个包目录压缩进单个 `.pyz` 文件——**Python 能直接运行 zip 里的代码**（zip 是合法的导入源，`PathFinder` 的 `zipimport` 支持它）：

```bash
$ python -m zipapp myapp -m "myapp.__main__:main" -p "/usr/bin/env python3"
$ ./myapp.pyz                 # 直接执行
```

```python
# myapp.pyz 内部结构（就是 zip）
myapp/__init__.py
myapp/__main__.py
__main__.py                   # zipapp 注入的入口（调用 myapp.__main__:main）
```

关键机制：运行时 `sys.path[0]` 是 `.pyz` 文件本身，`zipimport` 负责从 zip 里加载模块；`__main__.py` 是 zip 的入口点。

> **适用场景**：把"一个目录的纯 Python 工具"打包成**单文件分发**（运维拷贝即用、无安装步骤）。局限：不含第三方依赖（除非手动塞进 zip）、不含 C 扩展、启动需解释器。要"带依赖的可执行文件"用 PyInstaller/Nuitka（原理类似：打包解释器 + 模块 + 依赖，跳过"按需查找"）。

#### 独立可执行文件：PyInstaller / Nuitka 的原理

当"目标机器没有 Python"或"不想让用户装环境"时，用独立可执行文件。两类方案的本质：

```bash
$ pyinstaller myapp.py            # PyInstaller：解释器 + 模块 + 依赖 打成一个目录/exe
$ nuitka --onefile myapp.py       # Nuitka：把 Python 编译成 C，再编成原生可执行文件
```

| 方案 | 原理 | 产物 | 启动速度 | 体积 |
|------|------|------|---------|------|
| PyInstaller | 把 CPython 解释器 + 入口脚本 + **收集到的依赖模块**（字节码）打包；启动时解包到临时目录再运行 | 目录 / 单 exe | 慢（解包 + 初始化解释器） | 大（含解释器，~30MB+） |
| Nuitka | 把 Python 源码编译为 C 代码再编译为机器码 | 单 exe | 快（无解释器启动，但有运行时） | 中 |
| zipapp（10.8.1） | 纯字节码 zip，需系统解释器 | `.pyz` | 快 | 小 |

PyInstaller 的"收集依赖"是它的成败关键：它通过**静态分析 + 运行时钩子**决定把哪些模块打进去，但动态导入（`importlib.import_module(name)` 带变量）无法静态发现——这就是"PyInstaller 打包后运行报 `ModuleNotFoundError`"的头号原因。对策：`--hidden-import` 显式声明，或让源码避免隐藏的动态导入。

> **工程影响**：独立可执行文件适合"分发给无 Python 环境的终端用户"（GUI 工具、运维单文件）。代价：体积大、启动慢、杀毒软件误报率高（自解压行为像恶意软件）。权衡后若可接受"目标机装 Python"，zipapp 或 pipx 更轻。

### 10.8.2 PEP 723 内联脚本元数据

PEP 723（2023，3.11+ 工具链支持）允许**单个 .py 文件自声明依赖**：

```python
# script.py
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.28",
#     "rich>=13",
# ]
# ///
import requests
from rich import print

print(requests.get("https://example.com").status_code)
```

```bash
$ uv run script.py        # uv 读取内联元数据，自动建环境、装依赖、运行
$ pipx run script.py      # pipx 也支持
```

机制：`uv run` 解析文件头 `# /// script` 块（标准 TOML），在缓存环境里安装声明的依赖后执行脚本——**"脚本即项目"**。对运维脚本、数据分析脚本、内部工具尤其实用。

> **版本注意**：PEP 723 定义的是**元数据格式**，解释器本身（`python script.py`）不会自动装依赖——需要 `uv run`/`pipx run` 这类支持工具。Python 3.11 起标准库 `tomllib` 可解析该块，但安装动作仍由外部工具完成。

### 10.8.3 实战：用 __main__.py 组织一个命令行工具包

综合本章全部机制，搭一个"库 + CLI"双形态的最小工具：

```python
mytool/
├── __init__.py          # __version__ + __all__
├── cli.py               # 真正逻辑（可测试）
├── __main__.py          # 入口转发
└── pyproject.toml
```

```python
# mytool/cli.py
import argparse

def build_parser():
    p = argparse.ArgumentParser(prog="mytool")
    p.add_argument("--upper", action="store_true")
    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    text = "hello, mytool"
    print(text.upper() if args.upper else text)
    return 0
```

```python
# mytool/__main__.py
import sys
from .cli import main      # 相对导入：-m 执行时 __package__ 正确

if __name__ == "__main__":
    sys.exit(main())
```

```toml
# pyproject.toml（安装后提供 mytool 命令）
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mytool"
version = "0.1.0"
requires-python = ">=3.9"

[project.scripts]
mytool = "mytool.cli:main"     # 入口点：安装后生成 mytool 可执行命令
```

```bash
$ python -m mytool --upper     # 开发期：模块方式运行
HELLO, MYTOOL
$ pip install -e .
$ mytool --upper               # 安装后：命令方式运行
HELLO, MYTOOL
```

入口点（entry point）`[project.scripts]` 的机制：`pip install` 时在 `Scripts/`（或 `bin/`）生成一个**启动脚本**，内容是"定位解释器 → `import mytool.cli` → 调 `main()`"。与 `__main__.py` 是两条互补的路径：前者面向"安装后的命令"，后者面向"未安装的开发期"。

> **实战模式**：本章收官的完整链路——`src layout + pyproject.toml + __main__.py + [project.scripts] + pip install -e .`，这是一个"可测试、可分发、可命令行运行"的现代 Python 工具包的标准骨架。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| `import` 的本质 | 查找 → 加载（执行代码）→ 绑定；是**有副作用的语句**；字节码为 `IMPORT_NAME` + `STORE_NAME` |
| 模块对象 | 一个 `__dict__` 命名空间；`import a.b.c` 只绑定 `a`；`from x import y` 拷贝引用 |
| `sys.modules` | 模块只执行一次的缓存；键 = 全名，值 = 模块对象；永不淘汰 |
| 导入流水线 | `sys.meta_path` finder → `ModuleSpec` → loader；PEP 451 三件套 |
| `__pycache__` | magic + 时间戳/hash 校验（PEP 552）；`-B`/`PYTHONDONTWRITEBYTECODE` 禁写 |
| import 钩子 | 自定义 `MetaPathFinder` 可劫持导入（插件/热加载/pytest assert 重写） |
| 包 | 带 `__path__` 的模块；`__init__.py` 是执行体；`__all__` 是 API 收口 |
| 相对导入 | 依赖 `__package__`；顶层脚本无包上下文必然失败；包内代码用 `python -m` 运行 |
| 命名空间包 | PEP 420：无 `__init__.py`，多目录合并；常规包优先 |
| 循环导入 | 导入期互相访问属性才崩；延迟导入止血，依赖下沉根治 |
| venv | 启动器 + `pyvenv.cfg` + 独立 site-packages；不是第二个解释器 |
| 打包 | PEP 517/518/621：`pyproject.toml` + 构建后端；wheel 是构建产物，安装即解压 |
| editable | PEP 660：`.pth`/`__editable__` 钩子让源码目录直连 site-packages |
| 版本约束 | PEP 440 `~=` 兼容匹配；PEP 508 环境标记；库用范围、应用用锁文件 |
| 可复现 | `uv.lock`/pip-tools 全树锁定 + hash 校验；uv 靠全局缓存 + 硬链接提速 |
| 可执行形态 | zipapp `.pyz`；PEP 723 内联依赖；`__main__.py` + `[project.scripts]` 双入口 |

---

#### 练习 10

**第 1–3 题：验证理解（预测/解释）**

1. 预测输出并解释：`import os.path` 之后，`os`、`os.path`、`path` 三个名字中哪些可用？为什么？`sys.modules` 里此时有哪些相关键？

2. 解释下面的现象：模块 `config.py` 内容为 `value = 1`。执行 `from config import value` 后，`config.value = 2`，再打印 `value` 仍是 `1`；但若 `value` 是字典，`config.value["k"] = 2` 后原变量可见 `2`。为什么？

3. 用 `dis.dis` 反汇编一个包含 `import a.b`、`from a import b`、`from a import *` 的函数，解释 `IMPORT_NAME`、`IMPORT_FROM`、`POP_TOP` 各自的作用。

**第 4–6 题：动手实战**

4. 写一个 `MetaPathFinder`，让 `import db_conn` 返回一个从 `os.environ` 读取连接串构造的假模块（用于测试，不真实连接）。验证 `import db_conn` 不再触发 `ModuleNotFoundError`。

5. 创建 `mypkg`（含 `__init__.py`、`core.py`、`sub/`），在 `core.py` 用相对导入引用 `sub` 下的模块。分别用 `python core.py` 和 `python -m mypkg.core` 运行，记录并解释两种结果。

6. 构造一个循环导入的最小复现（A 导入期访问 B 的属性，B 导入期访问 A 的属性），用 `importlib.reload` + 观察 `sys.modules` 中两个模块的初始化状态来调试，然后用"下沉共享模块"方案修复，并画出修复前后的依赖图。

**第 7–9 题：实战进阶**

7. 为一个小工具包写完整的 `pyproject.toml`（PEP 621 + `[project.scripts]`），用 `python -m build` 生成 sdist 和 wheel，用 `python -m zipfile -l`（跨平台）检查 wheel 内部结构，并 `pip install` 到干净 venv 验证 `mytool` 命令可用。

8. 分别用 `pip install -e .`（setuptools 与 hatchling 各一次）和手动 `PYTHONPATH` 方案，验证三者的 `mypkg.__file__` 差异，解释 `.pth` 与 `__editable__` 钩子的区别。

9. 用 `uv` 初始化一个项目：`uv add requests`，提交 `uv.lock`，删掉 `.venv` 后 `uv sync` 恢复，用 `uv tree` 查看依赖树，并解释 `uv sync` 为什么比 `pip install -r` 快。

**第 10 题：深度思考**

10. 假设你要设计一个"热更新"系统：不重启进程，让线上代码在修改后自动生效。基于本章知识回答：(a) 为什么 `importlib.reload` 不足以胜任？(b) 自定义 `MetaPathFinder` 方案需要处理哪些一致性问题（`sys.modules` 缓存、`from` 导入的旧引用、新代码里被删除的名字、类实例的旧类对象）？(c) 相比"进程重启 + 蓝绿部署"，热更新省下了什么、引入了什么新风险？

---

**进入下一章的准备**：
- ✅ 能画出 `import a.b` 的完整执行链路（缓存命中与未命中两条路径）
- ✅ 能解释 `sys.path` 每一段的来源与 `PYTHONSAFEPATH` 的意义
- ✅ 能区分模块、常规包、命名空间包，并说出各自适用场景
- ✅ 能读懂并排查 `ImportError` / `ModuleNotFoundError` / `AttributeError: partially initialized module`
- ✅ 能用 `pyproject.toml` + wheel + editable install 完成"开发 → 打包 → 安装"闭环
- ✅ 理解锁文件为什么是"应用的精确事实"，以及 uv 快在哪

下一章（第 11 章 并发与异步）将进入进程/线程/协程的世界——模块机制（`sys.modules` 的全局性）正是"为什么多线程下 import 是安全的"这一经典问题的答案，届时我们会回来引用本章。
