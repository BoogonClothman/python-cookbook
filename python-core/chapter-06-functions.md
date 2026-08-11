# 第6章 函数：从调用约定到函数式编程

> **学习目标**：掌握 Python 的调用约定——传参语义（call-by-sharing）、参数分类（位置/关键字/`*args`/`**kwargs`）、封包解包的两面性；理解命名空间与闭包的底层机制；建立"函数是一等公民"的心智模型，能用匿名函数、高阶函数和生成器写出声明式、流式的数据处理代码。

---

函数是程序组织的基本单元。第 2 章把函数定义为"可复用的代码块"，但 Python 的函数远不止于此——它是一等公民（可以作为值传递）、是带有复杂调用约定的接口（位置/关键字/默认值/限定参数）、是名字解析的边界（作用域与闭包）、也是惰性计算与函数式编程的载体。

Python 的函数设计体现了两个核心哲学：**"可读性优先"**（关键字参数、限定参数让调用自文档化）和**"显式优于隐式"**（`global`/`nonlocal` 声明、`lambda` 的单表达式约束）。本章不仅讲语法，更用字节码揭穿"参数如何组装""名字如何查找""闭包如何捕获"这三个底层问题。

本章与前面章节的关系：第 2 章 2.2 节给出了函数的快速概览（定义/调用/`return`）；第 4 章 4.9 节讲了赋值侧的序列解包（`a, b = ...`、`*rest`）；第 5 章讲了迭代器协议与生成器表达式。本章在此基础上**系统化**：把"封包解包"从赋值侧扩展到函数调用侧与定义侧（6.3），把"函数对象"上升到一等公民（6.1），并用字节码揭穿名字解析与闭包的底层机制（6.4）。深浅拷贝专题中的"引用语义"是理解 6.2 传参语义的前提。

---

## 6.1 函数定义与函数对象

函数是"延迟执行的代码块"，同时也是"可以被传递的值"。这两个身份构成了理解 Python 函数的起点：前者对应 `def` 的语法与调用机制，后者对应函数的一等公民地位。

### 6.1.1 `def` 与函数创建

**定义不等于执行**。`def` 是一条可执行语句（在第 2 章提到 Python 万物皆对象），它只做一件事：创建一个函数对象并把它绑定到名字。函数体内部的代码要等到"调用"时才运行。

```python
>>> def greet(name):
...     return f"Hello, {name}!"
...                      # 注意：定义到这里结束，函数体尚未执行
>>> greet             # 名字绑定到一个函数对象
<function greet at 0x...>
>>> greet("World")    # 调用——此刻函数体才执行
'Hello, World!'
```

**`return` 的语义**：

- `return` 立即结束函数并返回值；函数内可有多条 `return`
- 没有 `return` 或 `return` 后不带表达式 → 返回 `None`
- `return` 之后的代码**永不执行**（不可达代码）

```python
>>> def f():
...     return 1
...     print("不可达")     # 编译不报错，但永远不会运行
>>> f()
1

>>> def g():
...     pass
>>> print(g())          # 没有 return → None
None
```

> **⚠️ 陷阱**：写"会返回真值的函数"时忘了写 `return`，是 Python 最常见的新手 bug——函数静默返回 `None`，不抛任何错误。排查技巧：`bool(func_result)` 与预期不符时，先检查函数体是否有 `return`。

**函数签名**：函数名 + 形参列表构成签名。用 `inspect.signature` 可以程序化地检查：

```python
>>> import inspect
>>> def process(data, *, strict=False, timeout=None): ...
>>> inspect.signature(process)
<Signature (data, *, strict=False, timeout=None)>
>>> str(inspect.signature(process))
'(data, *, strict=False, timeout=None)'
```

`inspect.signature` 是框架/装饰器在运行时反射函数签名的标准工具（衔接第 12 章元编程）。

**字节码：函数是如何被创建的？**

`def` 编译为 `MAKE_FUNCTION` 指令。看一个简单例子：

```python
>>> import dis
>>> def make():
...     def inner():
...         return 42
...     return inner
>>> dis.dis(make)
  1           0 RESUME                   0
  2           2 LOAD_CONST               1 (<code object inner at 0x..., file "<stdin>", line 2>)
              4 MAKE_FUNCTION            0
              6 STORE_FAST               0 (inner)
  3           8 LOAD_FAST                0 (inner)
             10 RETURN_VALUE
```

`LOAD_CONST` 把一个**代码对象**（`code object`）压栈，`MAKE_FUNCTION` 把它包装成函数对象，`STORE_FAST` 绑定到局部名 `inner`。这说明：

- 函数体在编译期就编译为字节码并打包进代码对象（字节码 + 常量 + 名字表）
- `def` 语句创建函数对象 → 函数对象持有对代码对象的引用
- 每次执行 `def`（例如在循环里）都会**新建一个函数对象**，即使它们的代码相同

**调用时发生了什么？** 调用 `f(...)` 会创建一个**栈帧**（frame）——包含局部变量、求值栈、指令指针，函数体字节码在帧上执行。这就是"函数调用栈"的底层：每次调用压入一帧，返回时弹出。

```python
>>> dis.dis(lambda: 1)
  1           0 RESUME                   0
              2 LOAD_CONST               1 (1)
              4 RETURN_VALUE
```

> **工程影响**：递归或深嵌套调用会消耗栈空间，CPython 的默认递归上限是 1000 层（详见 6.1.4）。理解"调用 = 建帧"，就能理解为什么无限递归会 `RecursionError`。

### 6.1.2 函数是一等公民

**函数是对象**——这意味着它有类型、有属性、可以被赋给变量、放进容器、作为参数传递或作为返回值。这正是"函数式编程"的地基。

```python
>>> def add(a, b):
...     """返回两数之和"""
...     return a + b
>>> type(add)
<class 'function'>
>>> add.__name__          # 函数名（不带模块限定）
'add'
>>> add.__qualname__      # 限定名（含类/嵌套层级）
'add'
>>> add.__doc__           # docstring
'返回两数之和'
>>> add.__code__          # 底层代码对象
<code object add at 0x..., file "<stdin>", line 1>
```

**函数可以像值一样使用**：

```python
>>> # 赋给变量——变量成为函数的别名
>>> f = add
>>> f(1, 2)
3

>>> # 放进容器
>>> ops = [add, lambda a, b: a - b]
>>> ops[0](3, 4)
7

>>> # 作为参数（这就是"高阶函数"，详见 6.5）
>>> def apply(func, x, y):
...     return func(x, y)
>>> apply(add, 3, 4)
7

>>> # 作为返回值（工厂函数，详见 6.4.4 闭包）
>>> def make_add(n):
...     def add_n(x):
...         return x + n
...     return add_n
>>> add_10 = make_add(10)
>>> add_10(5)
15
```

**"调用"的底层：`callable` 与 `__call__` 协议**。函数之所以能被 `()` 调用，是因为 `function` 类型实现了 `__call__` 魔术方法。更准确地说，`f(x)` 等价于 `type(f).__call__(f, x)`——这是第 4 章运算符重载协议的延续。

```python
>>> callable(add)          # 函数是可调用的
True
>>> callable(42)
False
>>> callable(int)          # 类型本身也可调用（构造对象）
True
```

`callable()` 检查一个对象是否实现了 `__call__`。任何对象都可以通过定义 `__call__` 变成"可调用对象"：

```python
>>> class Multiplier:
...     """带状态的"函数"——每次调用乘上 factor"""
...     def __init__(self, factor):
...         self.factor = factor
...     def __call__(self, x):
...         return x * self.factor
>>> double = Multiplier(2)
>>> double(10)             # 像函数一样调用！
20
>>> callable(double)
True
```

可调用对象 = 函数 + 状态，是"带记忆的函数"。它预览了第 7 章 OOP：当函数需要跨调用保存状态时，类实例（`__call__`）往往比闭包更清晰。**选型建议**：轻量状态用闭包，复杂状态用可调用对象。

> **跨语言对比**：
> - **C**：函数不是值，只能通过**函数指针**间接传递，没有闭包
> - **Java**：函数不是值，用"只有一个方法的接口"（`Runnable`/`Comparator`）模拟；Java 8 之后才有方法引用和 lambda
> - **JavaScript / Rust**：函数是一等值，与 Python 类似；Rust 用 `Fn`/`FnMut`/`FnOnce` trait 区分捕获方式（比 Python 更精细）

Python 的"万物皆对象 + 一等函数"让它成为函数式编程语言里最易入门的之一——不需要学习新概念，`map`/`filter`/`sorted(key=)` 天然可用。

### 6.1.3 docstring 与函数注解

**docstring** 是函数的第一个字符串字面量，作为文档存在 `__doc__` 属性里：

```python
>>> def area(width, height):
...     """计算矩形面积。
...
...     参数是正数，否则结果无意义。
...     """
...     return width * height
>>> area.__doc__.splitlines()[0]
'计算矩形面积。'
>>> help(area)             # 交互式帮助 = 渲染 docstring
```

> **实战建议**：docstring 约定见 PEP 257。一行函数用单行 docstring；复杂函数用三引号多行，写明参数、返回值、异常。这是"肘后备急"哲学的体现——代码即文档。

**函数注解（annotations）**：在形参和返回值后标注类型，存入 `__annotations__`：

```python
>>> def add(a: int, b: int) -> int:
...     return a + b
>>> add.__annotations__
{'a': <class 'int'>, 'b': <class 'int'>, 'return': <class 'int'>}
```

**关键认知：注解不参与运行时。** Python 不会因为注解是 `int` 就阻止你传字符串——注解是"给人和工具看的元数据"，不是类型检查。类型检查由外部工具（`mypy`/`pyright`）或运行时检查器完成。

```python
>>> add("1", "2")          # 不会报错——注解只是元数据
'12'
```

> **版本注意**（注解的演进，衔接附录 A）：
> - **PEP 3107**（Py3.0）：引入注解语法
> - **PEP 484**（Py3.5）：`typing` 模块，注解成为类型提示的事实标准
> - **PEP 563**（Py3.7，`from __future__ import annotations`）：注解延迟为字符串求值，解决前向引用
> - **PEP 649 / PEP 749**（Py3.14+）：注解懒求值成为默认，彻底解决自引用类型与性能问题

### 6.1.4 递归

递归是"函数调用自己"的编程范式。三要素：**基线条件**（终止）、**递归步**（向基线收敛）、**不变量**（每层问题变小）。

```python
>>> def factorial(n):
...     """n! = n * (n-1) * ... * 1"""
...     if n <= 1:          # 基线条件
...         return 1
...     return n * factorial(n - 1)   # 递归步：n-1 < n，收敛
>>> factorial(5)
120
```

**为什么 CPython 不优化尾递归**：许多函数式语言（Scheme、Haskell）对"递归调用在最后一步"的尾递归做优化，让递归不消耗额外栈帧。CPython **明确不做**（Guido 在 2009 年的邮件里给出理由：会让字节码调试栈混乱，且"更好的办法是改用循环"）。所以 Python 里深递归会撞上 `RecursionError`：

```python
>>> def forever():
...     return forever()
>>> forever()
RecursionError: maximum recursion depth exceeded

>>> import sys
>>> sys.getrecursionlimit()      # 默认 1000 层
1000
>>> sys.setrecursionlimit(5000)  # 可以调大，但改栈大小有栈溢出的 C 层风险
```

> **实战建议**：Python 中**能用循环就用循环**，递归用于"问题天然递归"的场景——树的遍历、分治、目录结构。而"经典递归适合写"的例子（斐波那契）在 Python 里会指数级爆炸，必须配合记忆化：

```python
>>> from functools import lru_cache
>>> @lru_cache(maxsize=None)
... def fib(n):
...     return n if n < 2 else fib(n - 1) + fib(n - 2)
>>> fib(100)                 # 无缓存时这行会跑几万年
354224848179261915075
```

**实战：目录树遍历**（递归的教科书场景）：

```python
>>> import os
>>> def walk(path, depth=0):
...     """递归打印目录树"""
...     for entry in sorted(os.scandir(path), key=lambda e: e.name):
...         prefix = "  " * depth + ("└ " if entry.is_dir() else "· ")
...         print(prefix + entry.name)
...         if entry.is_dir():
...             walk(entry.path, depth + 1)
```

递归每深入一层就创建一个新栈帧，理解这一点（结合 6.1.1 的帧模型），就明白为什么深目录用 `os.walk`（迭代式，不耗栈）更安全。

> **工程影响**：递归深度 = 栈帧数量 × 每帧大小。解析深嵌套的 JSON/XML 或用递归处理深度超过 ~900 的数据结构时，优先考虑显式栈（用 `list` 模拟）的迭代版本。

### 6.1.5 函数对象速查

函数对象携带大量可检查的元数据——这是"肘后备急"场景下最常用的参考。

```python
>>> def f(a, b=10, *args, c=20, **kwargs): ...
>>> f.__defaults__          # 位置参数的默认值（元组）
(10,)
>>> f.__kwdefaults__        # keyword-only 参数的默认值（字典）
{'c': 20}
>>> f.__annotations__       # 注解字典（如果标注了）
{}
>>> f.__code__              # 底层代码对象
<code object f at 0x..., file "<stdin>", line 1>
>>> f.__dict__              # 自定义属性字典——函数可以"挂"状态
{}
```

**常用函数属性一览**：

| 属性 | 含义 | 场景 |
|------|------|------|
| `__name__` / `__qualname__` | 名字 / 限定名 | 日志、调试、装饰器 |
| `__defaults__` | 位置参数默认值元组 | 检查默认参数、元编程 |
| `__kwdefaults__` | keyword-only 默认值字典 | 同上 |
| `__annotations__` | 注解字典 | 类型检查工具 |
| `__code__` | 代码对象（字节码 + 常量 + 名字表） | 字节码分析 |
| `__dict__` | 自定义属性字典 | 函数挂载元数据 |
| `__closure__` | cell 元组（闭包捕获的变量） | 检查闭包状态 |

**`inspect` 模块**——比裸属性更友好的运行时检查（衔接第 12 章元编程）：

```python
>>> import inspect
>>> inspect.signature(f)          # 完整签名对象
<Signature (a, b=10, *args, c=20, **kwargs)>
>>> inspect.getfullargspec(f)
FullArgSpec(args=['a', 'b'], varargs='args', varkw='kwargs', defaults=(10,),
            kwonlyargs=['c'], kwonlydefaults={'c': 20}, annotations={})
>>> inspect.isfunction(f)         # 谓词：是否普通函数
True
>>> inspect.isgeneratorfunction(f)  # 是否生成器函数
False
>>> inspect.getsource(f)          # 还原源码（交互式里不可得）
```

**"函数挂属性"——极简状态容器**：

```python
>>> def calls():
...     """统计被调用次数——状态挂在函数对象上"""
...     calls.count += 1
...     return calls.count
>>> calls.count = 0               # 函数对象也是对象，能挂属性
>>> calls(); calls(); calls()
3
```

> **实战建议**：`func.__name__` 在日志/装饰器/调度系统里是标配。用属性挂状态是"极简计数器"，但**跨调用状态优先用闭包（6.4.4）或可调用对象（6.1.2）**——属性挂载是全局单例，多实例会互相踩；且它依赖外部"先初始化属性"，易出错。

---

## 6.2 传参语义与参数分类

这一节回答两个问题：**参数是怎么传进去的**（语义）？**有哪些声明方式**（分类）？先讲语义，因为不理解"按对象传递"，参数分类（尤其默认参数陷阱）就会显得莫名其妙。

### 6.2.1 按对象传递（call-by-sharing）

**Python 的传参模式是"按对象传递"（call-by-sharing）**，也叫"传对象引用"。它是值传递和引用传递的折中：

| 模式 | 机制 | 典型语言 |
|------|------|---------|
| 传值（call-by-value） | 拷贝实参的值，函数内修改不影响调用方 | C、C++（默认）、Java 基本类型 |
| 传引用（call-by-reference） | 传实参的地址，函数内修改反映到调用方 | C++（引用参数）、C#（ref） |
| 按对象传递（call-by-sharing） | 传实参**引用的对象**，对象可变则修改可见，重新绑定则不可见 | Python、Java（对象）、JavaScript、Ruby |

用深浅拷贝专题的"变量 = 标签"模型理解：形参和实参是**指向同一对象的两个标签**。

```python
>>> def f(lst):
...     lst.append(1)        # 通过形参修改了对象本身
>>> a = []
>>> f(a)
>>> a                       # 调用方看到了修改——对象是同一个
[1]

>>> def g(lst):
...     lst = [100]         # 重新绑定形参——只是让形参指向新对象
>>> b = []
>>> g(b)
>>> b                       # 调用方不受影响——b 仍指向原对象
[]
```

**判断规则一句话**：**形参修改对象的内容（`.append`、`d[k]=v`、`x.attr=`）→ 调用方可见；形参重新绑定（`=` 赋值给形参）→ 调用方不可见。** 这与第 4 章讲的"就地修改 vs 重新绑定"完全一致。

**为什么"不可变对象像值传递"？** 因为不可变对象（`int`/`str`/`tuple`）无法被修改，函数内任何"修改"都是重新绑定（`n = n + 1`），自然不影响调用方——看起来就像值传递。但本质没变：传的还是同一个对象，只是不可变对象改不动。

```python
>>> def inc(n):
...     n += 1               # 重新绑定，不影响调用方
...     return n
>>> x = 1
>>> inc(x)
2
>>> x
1
```

> **⚠️ 陷阱（可变默认参数与传参语义联动）**：`lst.append(1)` 修改共享对象这一点，是大量隐蔽 bug 的来源。例如把列表当"累加器"传给多个调用：
> ```python
> >>> def accumulate(data, result=[]):    # ❌ 见 6.2.3，这里先看语义层面
> ...     result.extend(data)
> ...     return result
> ```
> 正确姿势是返回新对象或显式创建累加器。**不可变参数永远安全，可变参数要格外小心"是否希望调用方看到修改"**。

**字节码视角——调用时实参如何传递**：

```python
>>> def f(a, b):
...     return a + b
>>> dis.dis(f)      # 函数体：形参从帧的局部变量数组读取
  1           0 RESUME                   0
              2 LOAD_FAST                0 (a)
              4 LOAD_FAST                1 (b)
              6 BINARY_OP                0 (+)
             10 RETURN_VALUE
```

调用方 `f(x, y)` 编译为：`LOAD_FAST x` → `LOAD_FAST y` → `CALL 2`。CPython 把实参的**引用**依次压栈，`CALL 2` 取出 2 个引用建立新帧并把它们绑定为形参。**传递的是引用，不是拷贝**——这就是 call-by-sharing 的字节码证据。

> **跨语言对比**：
> - C：`int f(int x)` 拷贝；`void f(int* x)` 传地址（可改）
> - Java：基本类型传值，对象传引用（与 Python 的可变对象一致）
> - Python 独特之处：**没有"C 指针"这种主动表达引用**的能力，传参语义完全由对象可变性决定。这降低了心智负担，但要求开发者对"可变/不可变"敏感

### 6.2.2 位置参数与关键字参数

Python 有两种传参/收参方式，各有一个"侧"：

| 侧 | 位置参数 | 关键字参数 |
|----|---------|-----------|
| 调用侧（传） | `f(1, 2)` | `f(a=1, b=2)` |
| 定义侧（收） | `def f(a, b)` | 同上，名字就是关键字 |

```python
>>> def describe(name, age, city):
...     return f"{name}, {age}岁, 来自{city}"
>>> describe("小明", 25, "上海")            # 全部按位置
'小明, 25岁, 来自上海'
>>> describe(name="小明", city="上海", age=25)  # 全部按关键字——顺序无所谓
'小明, 25岁, 来自上海'
>>> describe("小明", city="上海", age=25)       # 混合：位置在前，关键字在后
'小明, 25岁, 来自上海'
```

**调用规则**：
1. 位置参数必须在关键字参数**之前**（`f(1, a=2)` 合法，`f(a=2, 1)` 语法错误）
2. 同一个参数不能既按位置又按关键字（重复赋值）

```python
>>> f(1, a=2)     # ❌ TypeError: got multiple values for argument 'a'
>>> f(a=2, 1)     # ❌ SyntaxError: positional argument follows keyword argument
```

**设计哲学：关键字参数 = 自文档化调用**。对比两种调用的可读性：

```python
>>> sorted(nums, True)              # ❌ True 是什么意思？
>>> sorted(nums, reverse=True)      # ✅ 一目了然
```

Python 明确鼓励对"非显然"的参数用关键字传参。标准库大量使用这个模式（`open(file, mode='r', encoding='utf-8')`），因为函数名已经说明"做什么"，关键字参数说明"怎么做"。

> **实战建议**：调用第三方函数时，除了第一个位置参数，其余尽量用关键字——既自文档化，又对"函数签名未来加参数"更健壮。

### 6.2.3 默认参数

默认参数让函数在"未传该参数"时使用预置值：

```python
>>> def greet(name, greeting="你好"):
...     return f"{greeting}, {name}!"
>>> greet("小明")
'你好, 小明!'
>>> greet("小明", "早上好")
'早上好, 小明!'
```

**核心机制：默认值在 `def` 执行时求值一次，且只求值一次。** 这是 Python 与多数语言最大的不同，也是无数 bug 的根源。

```python
>>> import datetime
>>> def log(msg, when=datetime.datetime.now()):   # ❌ when 在 def 时就固定了
...     return f"[{when}] {msg}"
>>> log("第一条")          # 时间戳 = def 时刻
>>> import time; time.sleep(2)
>>> log("第二条")          # 时间戳没变！仍是 def 时刻
```

**可变默认参数陷阱**（衔接深浅拷贝专题）——默认值 `[]`/`{}`/`set()` 是**同一个对象**，被所有调用共享：

```python
>>> def add_item(item, lst=[]):     # ❌ 经典陷阱
...     lst.append(item)
...     return lst
>>> add_item("a")
['a']
>>> add_item("b")           # 期望 ['b']，实际 ['a', 'b']！
['a', 'b']
>>> add_item.__defaults__   # 默认值是一个共享的列表对象
(['a', 'b'],)
```

**正确模式：用 `None` 哨兵 + 函数体内惰性创建**：

```python
>>> def add_item(item, lst=None):   # ✅
...     if lst is None:
...         lst = []
...     lst.append(item)
...     return lst
>>> add_item("a")
['a']
>>> add_item("b")           # 每次都是新列表
['b']
```

> **⚠️ 陷阱**：为什么 `None` 哨兵安全而 `[]` 不安全？因为每次调用 `if lst is None: lst = []` 都执行——创建**新**列表；而 `def f(lst=[])` 只执行一次——共享**旧**列表。**不可变默认值永远安全**（`0`、`""`、`None`、`tuple`），**可变默认值几乎总是 bug**。

**为什么 Python 不每次都重新求值默认值？** 这是设计选择：默认值在定义期绑定，可以用 `__defaults__` 检查，也让 CPython 把默认值存为函数对象的常量。Guido 承认这是"最大的设计失误之一"（2009 年 he talked about it），但因为要改就得让默认值在每次调用重建——语义大改，代价过高，于是保留并用"`None` 哨兵"作为惯用法。

> **性能小实验**：`None` 哨兵版本每次调用多一个 `if lst is None` 判断，但换来的是正确性。**永远用正确性换这一点点性能**。对纯函数（无可变默认参数）来说，默认参数反而是优化——CPython 无需为缺省参数传值。

### 6.2.4 关键字限定与位置限定参数

Python 3 引入两种"限定"语法，让函数作者**强制**调用方使用特定传参方式：

**关键字限定（keyword-only）——`*` 分隔符（PEP 3102，Py3.0）**：

```python
>>> def f(a, *, b):        # b 只能用关键字传
...     return a + b
>>> f(1, b=2)
3
>>> f(1, 2)                # ❌ TypeError: f() takes 1 positional argument but 2 were given
```

**位置限定（positional-only）——`/` 分隔符（PEP 570，Py3.8）**：

```python
>>> def f(a, /, b):        # a 只能用位置传
...     return a + b
>>> f(1, 2)
3
>>> f(1, b=2)
3
>>> f(a=1, b=2)            # ❌ TypeError: f() got some positional-only arguments passed as keyword arguments: 'a'
```

两者可以组合，形成完整的签名语法（`/` 在 `*` 之前）：

```python
>>> def f(a, /, b, *, c):  # a 位置限定；c 关键字限定；b 都行
...     ...
```

**标准库为什么用 `/`？** 看 `pow` 的签名：

```python
>>> help(pow)
pow(x, y, z=None, /)
```

`/` 让 CPython 保留"用 C 实现、参数是真正的位置"的自由——**不承诺参数名，允许未来改名而不破坏调用方**。这是 API 设计原则：**参数名一旦被关键字调用使用，就成了公共 API 的一部分，改名会破坏代码**。`/` 帮你解除这个承诺。

**自定义 API 何时用哪种？**

| 场景 | 用 `*`（keyword-only） | 用 `/`（positional-only） |
|------|------------------------|--------------------------|
| 参数含义不显然、需名字说明 | `def find(items, *, case_sensitive=False)` | |
| 未来可能改名的内部实现参数 | | `def _internal(a, /)` |
| 保持 C 扩展/旧实现的灵活性 | | 标准库大量用 |
| 禁止调用方依赖顺序 | 让所有可选参数 keyword-only | |

> **实战建议**：新 API 的默认惯例——**核心数据参数用位置，选项/标志用 keyword-only**（`*`）。这既自文档化，又让未来扩展选项而不破坏调用。参考 `sorted(iterable, *, key=None, reverse=False)` 的签名设计。

### 6.2.5 CPython 如何组装参数

调用 `f(a, b, c=3)` 时，CPython 的字节码做了三件事：求值实参、打包成调用、绑定形参。

**三种调用字节码**（版本注意：Python 3.12 起统一为 `CALL`，3.13 后关键字调用是 `CALL_KW`）：

```python
>>> def f(a, b=0, *, c=1): ...
>>> dis.dis("f(1, 2, c=3)")
  0           0 RESUME                   0
              2 LOAD_NAME                0 (f)
              4 LOAD_CONST               0 (1)
              6 LOAD_CONST               1 (2)
              8 LOAD_CONST               2 ('c')
             10 LOAD_CONST               3 (3)
             12 CALL_KW                  3        # 2 位置 + 1 关键字，共 3 个实参
             20 RETURN_VALUE
```

`CALL_KW 3`：操作数 3 = 实参总数，关键字名字（`'c'`）从栈顶弹出并按顺序配对。

**`*args`/`**kwargs` 的组装代价**：

```python
>>> def f(*args, **kwargs): ...
>>> dis.dis("f(1, 2, x=3)")
  ...
             10 CALL_KW                  2        # 普通调用：2 个实参
  ...
```

而解包调用 `f(*lst)` 编译为 `CALL_FUNCTION_EX`——**运行时展开**：

```python
>>> def f(a, b, c): return a + b + c
>>> dis.dis("f(*[1, 2, 3])")      # Python 3.12 实测
  0           0 RESUME                   0
  1           2 PUSH_NULL
              4 LOAD_NAME                0 (f)
              6 BUILD_LIST               0
              8 LOAD_CONST               0 ((1, 2, 3))
             10 LIST_EXTEND              1
             12 CALL_FUNCTION_EX         0      # 把 [1,2,3] 展开为 3 个实参
             14 RETURN_VALUE
```

实际调用 `f(*lst)` 的指令 `CALL_FUNCTION_EX`（3.11–3.14 同名；3.14 起不再带操作数）把序列**逐个拆开**填入形参——这个展开发生在 C 层，且会先创建临时元组，这就是它比普通调用稍慢的原因之一。

> **性能**：函数调用本身有开销（建帧 + 形参绑定）。高频循环里：
> - 直接位置传参最快
> - 关键字传参稍慢（要构造名字对）
> - `*args`/`**kwargs` 解包调用最慢（运行时拆装元组/字典）
>
> 看一个量级参考：
> ```python
> >>> from timeit import timeit
> >>> def f(a, b=0, c=0): return a + b + c
> >>> def kw(a, b=0, c=0): return a + b + c
> >>> timeit("f(1, 2, 3)", globals=locals())            # 位置
> 0.041
> >>> timeit("f(1, 2, c=3)", globals=locals())          # 关键字
> 0.053
> >>> timeit("f(*[1,2,3])", globals=locals())           # 解包
> 0.078
> ```
> 差值在纳秒级，**除极端热路径外不值得为此牺牲可读性**。库作者倾向位置参数（`numpy` 的 `np.zeros(shape, dtype=...)`）正是为了让热路径调用更快、签名更短。

> **版本注意**：调用指令在不同 CPython 版本名字不同——3.11 用 `CALL_FUNCTION`/`CALL_METHOD`/`CALL_FUNCTION_KW`/`CALL_FUNCTION_EX`；3.12 统一为 `CALL`（关键字参数改用 `KW_NAMES` 指令提供名字表）；3.13 起关键字调用改回 `CALL_KW`；解包调用一直是 `CALL_FUNCTION_EX`（3.14 起简化掉操作数，没有叫 `CALL_EX` 的指令）。本书示例按 3.14 风格标注，读者在自己版本上看到的指令名可能不同，**语义一致**。

---

## 6.3 封包与解包：`*` 与 `**` 的完整图景

`*` 和 `**` 是 Python 中"上下文相关"的运算符——同一个符号在不同位置做相反的事情。理解它们的关键是**硬币模型**：

- **解包（unpack）**：把一个集合**拆开**成多个独立的值
- **封包（pack）**：把多个独立的值**收拢**成一个集合

| 位置 | `*` 做什么 | 示例 |
|------|-----------|------|
| 赋值左侧（第4章已讲） | 解包：收集剩余元素 | `a, *rest = lst` |
| 函数调用 `f(*seq)` | 解包：拆开为位置参数 | `f(*[1, 2, 3])` |
| 函数定义 `def f(*args)` | 封包：收拢为元组 | `def f(*args)` |
| 字面量 `[*a]`（PEP 448） | 展开：合并进新容器 | `[1, *a, 2]` |

第 4 章讲了赋值侧解包。本章把它扩展到函数的两侧，并补全 PEP 448。

### 6.3.1 解包：从赋值到调用

**回顾赋值侧**（详见第 4 章 4.9 节）：`a, *rest = lst` 把首元素给 `a`，其余收进 `rest`。

```python
>>> a, *rest = [1, 2, 3, 4]
>>> a, rest
(1, [2, 3, 4])
```

**调用侧解包——`f(*seq)`**：把序列/迭代器的元素**逐个展开**为位置参数：

```python
>>> def add(a, b, c):
...     return a + b + c
>>> add(*[1, 2, 3])          # 等价于 add(1, 2, 3)
6
>>> nums = (10, 20)
>>> add(0, *nums)            # 可以混用：位置参数 + 解包
30
```

**`f(**mapping)`**：把字典展开为**关键字参数**（键必须是字符串）：

```python
>>> def describe(name, age):
...     return f"{name} {age}岁"
>>> person = {"name": "小明", "age": 25}
>>> describe(**person)       # 等价于 describe(name="小明", age=25)
'小明 25岁'
>>> describe(**{"name": "小明", "wrong": 1})  # ❌ 键必须是形参名
TypeError: describe() got an unexpected keyword argument 'wrong'
```

**多返回值天然配合解包**——函数返回元组，调用侧一行拆开：

```python
>>> def min_max(nums):
...     return min(nums), max(nums)
>>> lo, hi = min_max([3, 1, 4, 1, 5])
>>> lo, hi
(1, 5)
```

> **实战建议**：`*`/`**` 解包是"变量参数接口"的标准桥接。例如把从数据库读出的记录（字典）直接喂给构造函数：`User(**row)`。ORM 和配置系统大量使用。

**PEP 448（Py3.5）：字面量里的展开**。解包不再局限于函数调用和赋值，`*`/`**` 可以直接用在容器字面量里：

```python
>>> [1, *[2, 3], 4]           # 列表展开
[1, 2, 3, 4]
>>> {*[1, 2], *[2, 3]}        # 集合展开（自动去重）
{1, 2, 3}
>>> {'x': 1, **{'y': 2}}      # 字典展开——后出现的键覆盖先前的
{'x': 1, 'y': 2}
>>> {'x': 1, **{'x': 9}}      # 后者覆盖
{'x': 9}
>>> (*[1, 2], 3)              # 元组展开
(1, 2, 3)
>>> print(*[1, 2, 3])         # 最常用的：print 的多参数
1 2 3
```

PEP 448 之前，合并列表要 `a + b`（只支持两个），合并字典要循环 `update`。现在 `[*a, *b]`/`{**a, **b}` 是合并容器的最简洁写法。

> **⚠️ 陷阱：`*` 解包会"消耗"迭代器**。解包的对象是迭代器（如生成器）时，解包会把它取空：
> ```python
> >>> it = iter([1, 2, 3])
> >>> first = next(it)
> >>> [*it]                  # 剩下 [2, 3]
> [2, 3]
> >>> [*it]                  # 已耗尽
> []
> ```
> 生成器只能遍历一次（详见 6.6）。解包时请确认它是"可重复的序列"还是"一次性迭代器"。

### 6.3.2 封包：`*args` 与 `**kwargs`

定义侧，`*args` 把任意数量的**位置参数收拢为元组**，`**kwargs` 把任意数量的**关键字参数收拢为字典**：

```python
>>> def show(*args, **kwargs):
...     print("args:", args)
...     print("kwargs:", kwargs)
>>> show(1, 2, 3, name="小明", age=25)
args: (1, 2, 3)
kwargs: {'name': '小明', 'age': 25}
```

**名字只是约定**。关键符号是 `*` 和 `**`，名字通常用 `args`/`kwargs`（业界惯例），但可以任意：

```python
>>> def total(*nums):
...     return sum(nums)
>>> total(1, 2, 3, 4)
10
```

**封包与解包是逆操作**——`def f(*args)` 与 `f(*lst)` 互为对方：

```python
>>> def f(*args): return args     # 封包：多个值 → 元组
>>> f(1, 2, 3)                    # (1, 2, 3)
(1, 2, 3)
>>> f(*[1, 2, 3])                 # 解包：列表 → 多个值 → 再封包
(1, 2, 3)
```

**`*args` 与显式参数混用**：`*` 前的参数正常绑定，多余的全收进 `args`；`**kwargs` 必须放最后：

```python
>>> def config(host, port=80, *paths, **options):
...     print(host, port, paths, options)
>>> config("localhost", 8080, "/a", "/b", timeout=5)
localhost 8080 ('/a', '/b') {'timeout': 5}
```

> **注意**：`**kwargs` 只能出现**一次**且必须在所有参数之后；`*args` 出现在位置参数之后、关键字限定参数之前（衔接 6.2.4 的 `*` 分隔符——`def f(*args, key)` 里 `key` 是 keyword-only）。

### 6.3.3 参数透传与组合

**通用转发（forwarding）**——`*args, **kwargs` 是"原样转交所有参数"的惯用法，也是**装饰器的地基**（衔接第 12 章）：

```python
>>> def logged(func):
...     def wrapper(*args, **kwargs):
...         print(f"调用 {func.__name__}({args}, {kwargs})")
...         return func(*args, **kwargs)   # 原样转交
...     return wrapper
>>> @logged
... def add(a, b): return a + b
>>> add(1, 2)
调用 add((1, 2), {})
3
```

`wrapper(*args, **kwargs)` 不关心被包装函数有几个参数、什么名字——全部收拢再全部展开，**参数被透传**。这是"通用接口适配器"的通用机制（`functools.wraps` 会让 `wrapper` 保留原函数的元信息，详见第 12 章）。

> **⚠️ 陷阱 1：`**kwargs` 的键与显式参数冲突**。如果被转交的函数某个参数与 wrapper 的显式参数同名，调用时可能重复赋值：
> ```python
> >>> def wrapper(a, **kwargs):
> ...     return f(a=a, **kwargs)      # ❌ 若 kwargs 里有 'a'，f 收到两个 a
> >>> wrapper(1, a=2)
> TypeError: f() got multiple values for argument 'a'
> ```
>
> **⚠️ 陷阱 2：只转发 `*args` 不转发 `**kwargs`**（或反之），会把带关键字参数的调用方静默破坏。**透传必须成对**。

**参数组合全景**——一个函数定义可以同时用上所有形态：

```python
>>> def complex_api(a, /, b, *args, c=10, d=20, **kwargs):
...     """位置限定 a；普通 b；多余位置 → args；keyword-only c,d；多余关键字 → kwargs"""
...     return a, b, args, c, d, kwargs
>>> complex_api(1, 2, 3, 4, c=30, e=5)
(1, 2, (3, 4), 30, 20, {'e': 5})
```

完整参数顺序（从左到右）：`positional-only /` → 普通位置 → `*args` → keyword-only → `**kwargs`。

### 6.3.4 实战与反模式

**实战：可变参数 API 的签名设计**。标准库到处是 `*args`/`**kwargs` 的设计：

```python
>>> print(*objects, sep=' ', end='\n')     # 任意多个打印对象
>>> "{} {}!".format("Hello", "World")       # 格式化模板的任意参数
>>> max(3, 1, 4, 1, 5)                      # 任意多个比较对象
```

**反模式 1：滥用 `**kwargs` 掩盖签名**。`def f(**kwargs)` 让调用方**无法**用 `help`/编辑器看到参数名——违背"显式优于隐式"：

```python
>>> def connect(**kwargs):    # ❌ 反模式——kwargs 里到底要什么？
...     return kwargs.get("host", "localhost"), kwargs.get("port", 5432)
>>> # ✅ 显式写出参数，同时用 **kwargs 兜底未知选项：
>>> def connect(host="localhost", port=5432, **kwargs): ...
```

**反模式 2：解包使用过度**。`[*a]` 会**复制**列表（新建），而 `a` 是引用。在需要原对象时用 `*` 解包是隐蔽的浅拷贝（衔接深浅拷贝专题）：

```python
>>> a = [1, 2, 3]
>>> b = a              # 引用——b is a
>>> c = [*a]           # 新列表——c is not a
>>> c is a
False
```

> **工程影响**：`[*a]`/`list(a)`/`a[:]`/`a.copy()` 都是浅拷贝，各有语境偏好。`[*a]` 在"合并进新列表"时最自然，单独复制时 `a.copy()` 意图更明确。

### 6.3.5 综合实战：设计一个可参数化的数据处理 API

把 6.2 的参数分类与 6.3 的封包解包组合起来，设计一个生产级签名的示例。目标：一个"筛选 + 排序 + 截断 + 自定义转换"的迷你数据处理函数。

```python
def process_rows(rows, /, *, filters=(), sort_key=None, reverse=False,
                 limit=None, transform=None, **options):
    """处理记录列表。

    参数设计：
    - rows 位置限定（核心数据，未来可改实现细节）
    - filters 接收可调用对象元组，逐条过滤
    - sort_key/reverse/limit/transform 都是 keyword-only（自文档化）
    - **options 兜底扩展，不阻塞未来加参数
    """
    result = [r for r in rows if all(f(r) for f in filters)]
    if sort_key is not None or reverse:
        result = sorted(result, key=sort_key, reverse=reverse)
    if transform is not None:
        result = [transform(r) for r in result]
    if limit is not None:
        result = result[:limit]
    return result
```

调用侧——可读性与扩展性同时成立：

```python
>>> from operator import itemgetter
>>> data = [{"name": "小明", "score": 90, "age": 25},
...         {"name": "小红", "score": 85, "age": 23},
...         {"name": "小刚", "score": 95, "age": 26}]
>>> process_rows(data, filters=(lambda r: r["age"] >= 24,), sort_key=itemgetter("score"),
...              reverse=True, limit=2, transform=itemgetter("name"))
['小刚', '小明']
```

**这个签名示范了 6.2/6.3 的全部知识点**：

1. `/` 位置限定 `rows`——核心数据与"选项"分离，未来可改内部实现（6.2.4）
2. `*` 之后全部 keyword-only——`filters`/`sort_key`/`reverse`/`limit` 的含义靠名字说清（6.2.4）
3. 默认值用**不可变** `()`/`None`——无共享状态陷阱（6.2.3）
4. `**options` 兜底——未来加参数不破坏调用方，但别让签名变黑洞（6.3.4 反模式）
5. `filters` 收"函数元组"——高阶函数思想的封装（6.5）

> **工程影响**：这就是标准库/主流库（`sorted`、`filter`、`pandas.DataFrame.query`）的签名哲学——**核心数据走位置，选项走关键字，未来走 `**`**。读懂这个模式，就能读懂大多数库的 API 设计。

---

## 6.4 命名空间、作用域与闭包

函数体里出现一个名字时，Python 去哪找它？这一节回答名字解析（LEGB）与闭包捕获（cell）两个底层问题。

### 6.4.1 命名空间层次：LEGB

**命名空间**是"名字 → 对象"的映射。Python 有四种，按查找顺序排列：

| 层 | 名称 | 内容 | 何时建立 |
|----|------|------|---------|
| L | Local | 当前函数/代码块的局部变量 | 每次调用函数时 |
| E | Enclosing | 外层（嵌套）函数的局部变量 | 定义嵌套函数时 |
| G | Global | 当前模块的全局变量 | 模块加载时 |
| B | Builtin | `builtins` 模块 | 解释器启动时 |

**名字查找从内向外**：`L → E → G → B`，找到就停。

```python
>>> import builtins
>>> len                        # Builtin 层
<built-in function len>
>>> x = 10                     # Global 层
>>> def f():
...     y = 20                 # Local 层（f 的局部）
...     print(x, y)            # x → Global，y → Local
>>> f()
10 20
>>> dir(builtins)              # 内置命名空间
['ArithmeticError', ..., 'len', 'list', 'print', ...]
```

**遮蔽（shadowing）**：局部变量与外层同名时，局部优先：

```python
>>> x = "global"
>>> def f():
...     x = "local"            # 遮蔽全局 x
...     print(x)
>>> f()
local
>>> x                          # 全局不受影响
'global'
```

> **设计哲学：为什么全局访问比局部慢？** 局部变量存于栈帧的**数组**里，`LOAD_FAST` 按索引 O(1) 取；全局/内置要查**字典**（哈希查找）。CPython 对内置层还做了逐级退避查找。实测同操作全局约慢 1.5–2 倍。**热循环里把全局对象先绑定到局部**是经典优化（见下）。

```python
>>> import math
>>> def with_global(n):
...     return math.sqrt(n)          # 每次查 Global→Builtin 字典
>>> def with_local(n):
...     m = math                     # 绑定到局部，一次查找
...     return m.sqrt(n)
>>> from timeit import timeit
>>> timeit("with_global(100)", globals=locals())
0.078
>>> timeit("with_local(100)", globals=locals())
0.063
```

> **实战建议**：循环里反复调用 `len`/`max`/`math.sqrt` 等时，先 `local = len` 再循环，能稳定提速（第 5 章 5.2.5 的"缓存方法引用"同款思路）。量级微小，热路径值得。

### 6.4.2 名字解析与字节码

**变量的"归属"在编译期就决定了**，不是运行时。编译器扫描整个函数体，发现 `x = ...` 就把 `x` 标记为局部——即使这个赋值在函数末尾。

**字节码对照**：看三种名字分别编译成什么指令。

```python
>>> x = 10                      # 模块级
>>> def read_local():
...     y = 20
...     return y
>>> def read_global():
...     return x
>>> def read_builtin():
...     return len
>>> dis.dis(read_local)
  1           0 RESUME                   0
  2           2 LOAD_CONST               1 (20)
              4 STORE_FAST               0 (y)     # 局部 → STORE_FAST
  3           6 LOAD_FAST                0 (y)     # 局部 → LOAD_FAST（数组索引）
             10 RETURN_VALUE
>>> dis.dis(read_global)
  1           0 RESUME                   0
              2 LOAD_GLOBAL              0 (x)     # 全局 → LOAD_GLOBAL（字典查找）
             10 RETURN_VALUE
>>> dis.dis(read_builtin)
  1           0 RESUME                   0
              2 LOAD_GLOBAL              0 (len)   # 内置也走 LOAD_GLOBAL，查不到再退到 builtins
             10 RETURN_VALUE
```

**三个经典谜题，字节码一解释就通**：

**谜题 1：为什么这个报错？**（赋值在后面的 `print` 却找不到名字）

```python
>>> x = 10
>>> def f():
...     print(x)          # 编译期认为 x 是局部（因为下一行有赋值）
...     x = 20
>>> f()
UnboundLocalError: local variable 'x' referenced before assignment
```

因为编译器把 `x` 标记为局部 → `print(x)` 编译为 `LOAD_FAST x`，而局部 `x` 还没赋值 → 报"引用未赋值"。**在函数内赋值过的名字，整个函数体都把它当局部**。

**谜题 2：`def` 里的默认参数为什么能读到外部？** 默认值在 `def` 执行时求值（6.2.3），当时处于模块作用域，所以 `def f(x=default_var)` 能读到全局 `default_var`——但这是"求值"，不是"运行时查找"。**默认值是一次性快照**。

**谜题 3：嵌套函数读外层变量为什么是 `LOAD_DEREF`？** 见 6.4.4 闭包的字节码。

> **版本注意**：Python 3.11 起 `LOAD_GLOBAL` 附带 `CACHE` 指令（内联缓存），同一名字第二次查找显著变快；3.13 的"内联缓存"进一步加速。这也是"局部 vs 全局"差距在逐步缩小的原因之一，但原理不变。

### 6.4.3 `global` 与 `nonlocal`

**赋值默认创建局部变量**——在函数内 `x = 1` 不修改全局 `x`，而是新建局部。要想修改外层/全局，需要声明：

**`global` 声明**：

```python
>>> counter = 0
>>> def inc():
...     global counter          # 声明：我要修改全局 counter
...     counter += 1
>>> inc(); inc()
>>> counter
2
```

去掉 `global` 会怎样？

```python
>>> def inc():
...     counter += 1            # ❌ UnboundLocalError（见 6.4.2 谜题 1）
```

**`nonlocal` 声明（PEP 3104，Py3）**：修改**外层函数**的变量（闭包里）用 `nonlocal`，而不是 `global`：

```python
>>> def make_counter():
...     count = 0
...     def inc():
...         nonlocal count       # 修改外层 make_counter 的 count
...         count += 1
...         return count
...     return inc
>>> c = make_counter()
>>> c(), c(), c()
(1, 2, 3)
```

**为什么需要 `nonlocal`？** 因为"函数内赋值 = 局部变量"的规则对嵌套函数同样成立——如果不声明，`inc` 里的 `count += 1` 会让编译器把 `count` 当成 `inc` 的局部（谜题 1 重现）：

```python
>>> def make_counter():
...     count = 0
...     def inc():
...         count += 1          # ❌ 没声明 nonlocal → UnboundLocalError
...         return count
...     return inc
>>> make_counter()()
UnboundLocalError: local variable 'count' referenced before assignment
```

> **设计哲学**：`global`/`nonlocal` 是"显式优于隐式"的体现——修改外部作用域是**有副作用的操作**，Python 要求你**显式声明**。对比 JavaScript 隐式提升全局，Python 的声明让"谁改了什么"在代码里可见。但 `global`/`nonlocal` 仍是**应少用**的机制：函数与其外部环境耦合越深，越难测试（详见 6.4.5 的替代方案）。

**只读闭包不需要 `nonlocal`**：只**读取**外层变量不需要声明，只有**赋值**（含 `+=`、`.append` 之后的重新绑定）才需要：

```python
>>> def make_adder(n):
...     def add(x):
...         return x + n        # 只读 n，无需 nonlocal
...     return add
>>> add5 = make_adder(5)
>>> add5(3)
8
```

> **⚠️ 陷阱**：`lst.append(...)` 这类**方法调用不是赋值**，不需要 `nonlocal`（它改的是对象内容，不是重新绑定名字）。而 `count += 1`、`lst = [...]` 是重新绑定，需要声明。判断标准：**等号左边是不是这个名字**。

### 6.4.4 闭包

**闭包（closure）= 函数 + 它捕获的外部变量**。当一个内层函数引用了外层函数的变量，Python 会把这个变量存进一个 **cell 对象**，让内层函数在外层函数返回后仍能访问它。

```python
>>> def outer():
...     msg = "Hello"
...     def inner():
...         return msg          # 捕获 msg
...     return inner
>>> f = outer()
>>> outer() 已经返回，但：
>>> f()                         # 仍能访问 msg！
'Hello'
```

**底层：cell 对象与字节码**：

```python
>>> dis.dis(outer)
  1           0 RESUME                   0
  2           2 LOAD_CONST               1 ('Hello')
              4 STORE_DEREF              0 (msg)    # 存进 cell，而非普通局部
  3           6 LOAD_CONST               2 (<code object inner...>)
              8 MAKE_FUNCTION            8           # 带闭包标志
             10 STORE_FAST               0 (inner)
  4          12 LOAD_FAST                0 (inner)
             14 RETURN_VALUE
>>> dis.dis(f)
  1           0 RESUME                   0
  2           2 LOAD_DEREF               0 (msg)     # 从 cell 读取
              4 RETURN_VALUE
```

外层用 `STORE_DEREF`（存进 cell）、内层用 `LOAD_DEREF`（从 cell 读）。`MAKE_FUNCTION 8` 的操作数 8 = 闭包标志，告诉解释器"这个函数带闭包"。可以检查：

```python
>>> f.__closure__               # cell 对象元组
(<cell at 0x...: str object at 0x...>,)
>>> f.__closure__[0].cell_contents   # 取出 cell 里的值
'Hello'
```

> **工程影响——闭包与内存**：cell 让外层变量**生命周期延长**到闭包被回收为止。每次调用 `make_counter()` 都新建一组 cell（状态独立）。需要**跨调用保存状态**时，闭包是"无类版状态对象"；状态复杂时优先可调用对象（6.1.2）。

**工厂函数模式**——按参数定制函数（高阶函数 + 闭包的典型组合）：

```python
>>> def make_multiplier(factor):
...     def multiply(x):
...         return x * factor
...     return multiply
>>> double = make_multiplier(2)
>>> triple = make_multiplier(3)
>>> double(10), triple(10)
(20, 30)
```

**late binding 陷阱（晚期绑定）**——循环里创建的 lambda 全部捕获**同一个**循环变量（不是各自的值）：

```python
>>> funcs = [lambda: i for i in range(3)]
>>> [f() for f in funcs]        # ❌ 期望 [0, 1, 2]
[2, 2, 2]
```

因为 lambda 捕获的是 cell `i`，循环结束后 `i` 停在 2，所有 lambda 读到同一个 2。**修复：默认参数快照**（6.2.3 说默认值在 `def` 时求值——这里派上用场）：

```python
>>> funcs = [lambda i=i: i for i in range(3)]    # ✅ 默认参数捕获当前值
>>> [f() for f in funcs]
[0, 1, 2]
```

`i=i` 在 lambda **创建时**把当前 `i` 的值求值并绑定为默认参数——每个 lambda 拿到了独立快照。

> **⚠️ 陷阱**：`lambda: i` 与 `lambda i=i: i` 的区别，正是"捕获变量 vs 捕获值"的区别。任何"在循环里创建函数"的代码（回调、`sorted(key=...)`、线程）都可能踩中晚期绑定。第 5 章 5.2.6 的 for-else 陷阱同源。

**跨语言对比**：

| 语言 | 闭包捕获 | 晚期绑定修复 |
|------|---------|-------------|
| Python | 捕获 cell（变量），函数体内赋值需 `nonlocal` | 默认参数快照 |
| JavaScript | 捕获变量；`var` 函数级作用域更易踩中；`let` 每次迭代新绑定 | `let` 天然修复 |
| Rust | `Fn`/`FnMut`/`FnOnce` 按捕获方式分 trait | 借用/所有权检查 |
| C++ | lambda 捕获列表 `[x]`（值）/`[&x]`（引用） | 按值捕获 |

Python 的"晚绑定 + 默认参数快照"修复，本质是把 JS 社区熟悉的 `let` 语义手动做出来。

### 6.4.5 动态命名空间：`globals()` 与 `locals()`

`globals()` 返回**模块级**命名空间字典，`locals()` 返回当前局部命名空间：

```python
>>> x = 1
>>> globals()['x']
1
>>> globals()['y'] = 2          # 可以写！等价于 y = 2
>>> y
2
>>> def f():
...     z = 3
...     return locals()         # 只读快照
>>> f()
{'z': 3}
```

> **⚠️ 陷阱**：`locals()` 的返回值是**只读快照**——写入它不生效（CPython 编译期已把局部变量固化为数组，运行时改字典无用）：
> ```python
> >>> def f():
> ...     a = 1
> ...     locals()['a'] = 99     # ❌ 无效
> ...     return a
> >>> f()
> 1
> ```

**反模式：动态创建变量名**。用 `exec`/`setattr`/`globals()[name]` 动态生成 `var1`/`var2`... 是反模式——名字不在源代码里，无法静态分析、易冲突、难调试：

```python
>>> for i in range(5):
...     globals()[f"v{i}"] = i     # ❌ 反模式：动态命名空间
>>> v3
3
>>> # ✅ 正确：用容器
>>> data = {f"v{i}": i for i in range(5)}
```

> **实战建议**：需要"按名字存取变量"时，用字典（`data[key]`）而非操纵命名空间。需要把数据转为属性时用类实例或 `dataclasses`（第 7 章）。**命名空间操作只留给元编程/调试器这类场景**（第 12 章）。

---

## 6.5 匿名函数与高阶函数

函数既能被"调用"，也能被"传递"。lambda 让你在**需要函数的地方直接写函数**；高阶函数让**函数成为其他函数的参数或返回值**。两者合起来，就是 Python 函数式编程的核心。

### 6.5.1 `lambda`

`lambda` 是匿名函数的语法糖——一个只能包含**单个表达式**的迷你函数：

```python
>>> add = lambda a, b: a + b        # 相当于 def add(a, b): return a + b
>>> add(1, 2)
3
>>> (lambda x: x * 2)(5)            # 就地定义、就地调用（很少这么用）
10
```

**语法约束**：

| 能做 | 不能做 |
|------|--------|
| 单个表达式（`x + 1`、`x[1]`、`x.y`） | 语句：`if/for/while/return/assert` |
| 调用函数、运算符表达式 | 多行代码、赋值表达式以外的一切语句 |
| 默认参数、`*args`/`**kwargs` | docstring |

```python
>>> lambda x: if x: return 1        # ❌ SyntaxError
>>> lambda x: 1 if x else 0         # ✅ 用三元表达式代替 if
```

> **设计哲学：为什么 Guido 把 lambda 限制为单表达式？** 这是 1990 年代讨论的延续。支持语句的 lambda 会引入两套可读性问题（缩进？多行？），而 Python 有完整的语句级工具（`def`、推导式、`if`）。Guido 的观点：**能用一个表达式表达的逻辑才值得匿名；需要语句说明的逻辑应该命名**。这符合"可读性优先"——lambda 是简洁的工具，不是替代 `def` 的完整方案。

**选型矩阵**：

| 场景 | 推荐 | 理由 |
|------|------|------|
| 一次性的简单转换/比较 | `lambda` | 就地、无需取名 |
| 逻辑超过一行 | `def` | 可读性、可测试、有名字 |
| 需要跨调用保存状态 | 可调用对象（`__call__`）或闭包 | lambda 无状态 |
| 需要 docstring/类型注解 | `def` | lambda 没有 docstring |
| 调试时需要定位 | `def` | lambda 的 `__name__` 是 `<lambda>` |

```python
>>> f = lambda x: x + 1
>>> f.__name__          # ❌ 调试困难：所有 lambda 都叫这个名字
'<lambda>'
>>> import inspect
>>> inspect.getsourcefile(f)
None                    # lambda 没有源文件位置信息
```

> **⚠️ 陷阱**：lambda 的作用域与其他函数一样——**不创建新的作用域块**，但会创建新的名字空间。lambda 里的 `x` 遵循 LEGB（6.4）。**循环中创建 lambda 会踩中 6.4.4 的晚期绑定陷阱**：`[lambda: i for i in range(3)]` 得到三个都返回 2 的函数。别嵌套 lambda（`lambda x: lambda y: ...` 可读性崩坏）。

### 6.5.2 高阶函数：把函数当参数

高阶函数（higher-order function）= 接受函数作为参数、或返回函数的函数。标准库的核心高阶函数：

**`key` 参数——`sorted`/`min`/`max`**：不直接比较元素，而是先经 `key` 函数**变换**再比较：

```python
>>> words = ["apple", "Banana", "cherry", "Date"]
>>> sorted(words)                       # 默认按字典序（大写在前）
['Banana', 'Date', 'apple', 'cherry']
>>> sorted(words, key=str.lower)        # 忽略大小写
['apple', 'Banana', 'cherry', 'Date']
>>> sorted(words, key=len)              # 按长度
['Date', 'apple', 'Banana', 'cherry']
>>> max(words, key=len)                 # min/max 同样支持 key
'cherry'
```

**`key` 的设计哲学**：Python 3 用 `key` 取代了 Python 2 的 `cmp` 比较函数参数。原因（PEP 8 的推荐）：

1. **key 函数只调用 n 次**（每个元素一次），而 cmp 要调用 O(n log n) 次——`sorted` 用了 **DSU（Decorate-Sort-Undecorate）** 技巧，先变换、再排序、再还原
2. key 更容易写（`str.lower` 一行 vs 手写比较函数）
3. key 是"纯数据转换"，cmp 是"比较逻辑"，前者更不易错

```python
>>> # DSU 是 sorted(key=) 的底层：Decorate → Sort → Undecorate
>>> [(str.lower(w), w) for w in words]     # decorate
>>> # 排序后取 [1] 元素即还原
```

> **性能**：`key` 的 n 次调用可以缓存（如 `functools.cache`），而 `cmp` 每次比较都重新调用——大数据量下 `key` 的优势是数量级的。

**`map`/`filter`/`reduce`**——经典函数式三件套：

```python
>>> list(map(lambda x: x * 2, range(5)))         # 映射：[0, 2, 4, 6, 8]
[0, 2, 4, 6, 8]
>>> list(filter(lambda x: x % 2 == 0, range(10))) # 过滤：[0, 2, 4, 6, 8]
[0, 2, 4, 6, 8]
>>> from functools import reduce
>>> reduce(lambda a, b: a + b, range(1, 6))       # 归约：15（1+2+3+4+5）
15
```

**`map` 支持多可迭代对象**（并行映射）——这比 `zip` + 列表推导式更直接：

```python
>>> list(map(lambda a, b: a + b, [1, 2, 3], [10, 20, 30]))
[11, 22, 33]
>>> list(map(pow, [2, 3, 4], [5, 2, 1]))          # pow 直接可用
[32, 9, 4]
```

**关键点：`map`/`filter` 返回惰性迭代器**，必须 `list()` 才产生列表。这也是它们"省内存"的原因。

> **设计哲学：为什么社区"推导式优先于 map/filter"？** PEP 202/279 时代 Python 社区达成的共识——推导式**更可读**：
> ```python
> >>> [x * 2 for x in range(5)]              # ✅ 比 map 直观
> >>> [x for x in range(10) if x % 2 == 0]   # ✅ 比 filter 直观
> ```
> 推导式把"过滤"和"映射"写在同一个表达式里，而 `map`+`filter` 需要嵌套。**`map` 的独特价值只剩两个**：多可迭代对象并行、以及把内置函数（如 `pow`）直接当作映射器。**在能选推导式时，推导式是默认答案**（衔接第 5 章推导式性能分析——推导式还有专用字节码）。

**`functools` 工具箱**：

```python
>>> from functools import partial, reduce, cmp_to_key
>>> def power(base, exp): return base ** exp
>>> square = partial(power, exp=2)      # 部分应用：固定 exp=2
>>> square(5)
25
>>> def by_len_cmp(a, b):               # 旧式比较函数
...     return len(a) - len(b)
>>> sorted(words, key=cmp_to_key(by_len_cmp))  # 适配为新 key 体系
['Date', 'apple', 'Banana', 'cherry']
```

`partial` 部分应用 = 提前固定部分参数，生成"参数更少"的新函数。经典用途：给回调绑定上下文、把多参函数适配成单参接口（`map` 需要一个单参函数，`partial(power, exp=2)` 正好）。

> **跨语言对比**：
> - **JavaScript**：`Array.prototype.map/filter/reduce` 是方法（附着在数组上），不是独立函数——写法 `arr.map(f)`
> - **Rust**：`iter().map().filter().fold()` 链式迭代器，类型系统保证不变量
> - **Python**：独立函数 `map(f, it)`，与 `itertools` 模块组合成管道。Python 的 map/filter 是"函数"，推导式是"语法"——两条路都给你

### 6.5.3 函数式工具箱与实战模式

**纯函数 vs 副作用**。纯函数 = 输出只由输入决定、无外部副作用（不修改全局、不写文件、不依赖时间/随机）。纯函数的好处：**可测、可缓存、可并发**。

```python
>>> # 纯函数：同样的输入 → 同样的输出
>>> def pure(x): return x * 2
>>> # 不纯函数：依赖/修改外部状态
>>> total = 0
>>> def impure(x):
...     global total
...     total += x          # 副作用：改了全局
...     return total
```

> **工程影响**：副作用是 bug 温床——难测试（要构造环境）、难并行（共享状态竞争）、难缓存（结果不可复用）。**函数式风格 = 尽量写纯函数，把副作用收敛到边界**（I/O 层）。这与第 8 章异常、第 11 章并发的设计思想一致。

**管道模式（pipeline）**——把数据处理写成"一串变换"，每个环节是纯函数：

```python
>>> from functools import reduce
>>> def pipe(*funcs):
...     """函数组合：pipe(f, g)(x) == g(f(x))"""
...     def run(x):
...         return reduce(lambda v, f: f(v), funcs, x)
...     return run
>>> process = pipe(
...     lambda s: s.strip().lower(),
...     lambda s: s.replace(" ", "_"),
...     len,
... )
>>> process("  Hello World  ")
12
```

管道模式的 Python 惯用法常直接用生成器/推导式串联（见 6.6.4），或者用第三方库（`toolz`）的 `pipe`。核心思想一致：**数据流经一串纯变换**，每个环节独立可测。

**性能取舍：推导式 / 生成器 / 显式循环何时用哪个？**

| 需求 | 选型 | 理由 |
|------|------|------|
| 结果需要全部在内存、逻辑简单 | 列表推导式 | 最快（专用字节码）、最可读 |
| 数据量大、逐元素处理 | 生成器表达式/生成器函数 | 惰性，省内存 |
| 结果需要多次迭代/索引 | 列表 | 生成器单次消费 |
| 逻辑复杂（多分支、副作用） | 显式 `for` | 推导式/生成器不可读 |
| 需要提前 `break` | 显式 `for` 或 `itertools.takewhile` | 推导式无法中途退出 |

```python
>>> # 中等规模：推导式最简洁
>>> [x * x for x in range(1000) if x % 2]
>>> # 大规模流式：生成器表达式
>>> sum(x * x for x in range(10**8))     # 不建中间列表
```

> **实战建议**：规则一句话——**逻辑一个表达式能写完用推导式，写不完用循环；数据大到装不下内存用生成器**。别为了"函数式"而函数式：`reduce` 在 Python 里常被 `sum`/`max`/推导式替代，多数 `map`/`filter` 用推导式更好。

**实战案例：纯函数配置验证管道**——用一个完整例子演示 纯函数 + `partial` + 管道组合。

```python
>>> from functools import partial
>>> def require(config, key, default=None):
...     """确保 key 存在，缺省补默认值——返回新字典，不修改输入（纯函数）"""
...     out = dict(config)
...     out.setdefault(key, default)
...     return out
>>> def coerce(config, key, fn):
...     out = dict(config)
...     if key in out:
...         out[key] = fn(out[key])        # 类型转换
...     return out
>>> def validate(config, rules):
...     """按规则表逐条处理配置——纯函数管道"""
...     for rule in rules:
...         config = rule(config)          # 每个规则是 (dict) -> dict
...     return config
```

规则表 + 管道执行：

```python
>>> # 用 partial 预绑定规则参数，让每个规则成为单参纯函数
>>> rules = [
...     partial(require, key="host", default="localhost"),
...     partial(require, key="port", default=5432),
...     partial(coerce, key="port", fn=int),
...     partial(coerce, key="retries", fn=int),
... ]
>>> validate({"host": "db1", "retries": "5"}, rules)
{'host': 'db1', 'port': 5432, 'retries': 5}
```

这个模式的价值：

- **纯函数**：每个规则不修改输入、不依赖外部状态 → 顺序可换、可单测、可复用（6.5.3）
- **`partial` 预绑定**：把"多参逻辑"适配成管道要求的"单参接口"（6.5.2）
- **数据驱动**：规则表是数据（列表），管道是通用逻辑 → 新增规则只需加一行 `partial(...)`
- 对比"手写一串 if 填默认值"：管道让每步独立、可插拔、可测

> **实战建议**：配置归一化、参数校验、请求中间件、数据清洗都是"纯函数管道"的天然场景。它把 6.5 的函数式工具箱（`partial`、纯函数、`reduce`）串成了一条可落地的生产线。

---

## 6.6 生成器函数：产出序列的函数

普通函数 `return` 一个结果；生成器函数 `yield` 一个接一个地产出——把"计算一整批"变成"计算一个、暂停、再要、再算"的流。这是第 5 章迭代器与生成器表达式的**函数形态**。

### 6.6.1 `yield` 与生成器函数

**变身规则**：只要函数体里含 `yield`，调用它返回的**不是结果，而是一个生成器对象**，函数体不立即执行：

```python
>>> def countdown(n):
...     print("开始倒计时")
...     while n > 0:
...         yield n
...         n -= 1
>>> g = countdown(3)          # 只是创建生成器——函数体没执行！
>>> print("未调用 next，上面那行 print 不会出现")
未调用 next，上面那行 print 不会出现
>>> next(g)                   # 首次 next 才执行到第一个 yield
开始倒计时
3
>>> next(g)
2
>>> next(g)
1
>>> next(g)                   # 耗尽 → StopIteration
Traceback (most recent call last):
  ...
StopIteration
```

**三种"产出序列"的方式对比**（衔接第 5 章）：

| 方式 | 求值 | 内存 | 代码 |
|------|------|------|------|
| 列表 | 立即全部算好 | 全量 | `[x * 2 for x in range(n)]` |
| 生成器表达式 | 惰性 | O(1) | `(x * 2 for x in range(n))` |
| 生成器函数 | 惰性 + 可含语句 | O(1) | `def gen(): ... yield x` |

**生成器表达式只能写单个表达式；生成器函数可以写任意逻辑**（循环、`if`、异常处理、嵌套）。需要复杂产出逻辑时，生成器函数是唯一选择：

```python
>>> def dedup(sorted_iterable):
...     """去重（要求输入已排序）——需要跨迭代状态，生成器表达式做不了"""
...     last = None
...     for item in sorted_iterable:
...         if item != last:
...             yield item
...             last = item
>>> list(dedup([1, 1, 2, 3, 3, 3, 4]))
[1, 2, 3, 4]
```

**惰性求值与单次消费**：

```python
>>> import itertools
>>> def naturals():
...     n = 0
...     while True:
...         yield n
...         n += 1
>>> evens = (x for x in naturals() if x % 2 == 0)
>>> next(evens), next(evens), next(evens)     # 无限序列！惰性使这成为可能
(0, 2, 4)
```

> **⚠️ 陷阱**：生成器**只能遍历一次**。第二次 `for` 直接空：
> ```python
> >>> g = (x for x in range(3))
> >>> list(g); list(g)
> [0, 1, 2]
> []                      # 已耗尽
> ```
> 需要重复使用就转成列表，或每次重新创建生成器。

### 6.6.2 生成器是状态机

**执行模型**：生成器对象内部保存一个**冻结的栈帧**。`next()` 恢复帧执行到下一个 `yield` 暂停并返回值；下一次 `next()` 从暂停处继续。这就是"状态机"——每 yield 一次，函数停在一个状态。

**字节码**：

```python
>>> def gen():
...     yield 1
...     yield 2
>>> dis.dis(gen)
  0           0 RESUME                   0
  1           2 LOAD_CONST               1 (1)
              4 YIELD_VALUE              0      # 产出并暂停
              6 RESUME                   0
  2           8 LOAD_CONST               2 (2)
             10 YIELD_VALUE              0      # 再次产出
             12 RESUME                   0
             14 LOAD_CONST               0 (None)
             16 RETURN_VALUE                    # 无 yield 可产 → StopIteration
```

与普通函数的 `RETURN_VALUE` 不同，`YIELD_VALUE` 把帧**挂起**而不是弹出。生成器对象有帧相关信息：

```python
>>> g = gen()
>>> g.gi_frame                # 被冻结的帧（未启动时为 None）
<frame at 0x..., file '<stdin>', line 1, code gen>
>>> g.gi_code                 # 代码对象
<code object gen at 0x..., file '<stdin>', line 1>
```

**与迭代器协议对接**（衔接第 5 章）：生成器对象本身就是迭代器——实现了 `__iter__`（返回自身）和 `__next__`（恢复执行），耗尽时抛 `StopIteration`。所以 `for x in gen():` 直接可用，`list(gen)`/`sum(gen)` 也可用。

> **工程影响**：生成器让"无限/超大数据"变得可处理——每时刻只存在一个元素。对比列表全量载入，处理 10 亿行日志、无限数论序列、流式网络数据时，这是唯一可行的内存方案。

### 6.6.3 进阶：`send` / `yield from`

**`yield` 是双向通道**：不仅向外产出值，还能接收外部 `send()` 的数据：

```python
>>> def echo():
...     received = yield "ready"       # 先产出，等待外部发送
...     yield f"收到: {received}"
>>> g = echo()
>>> next(g)                # 启动到第一个 yield
'ready'
>>> g.send("Hello")        # 向 yield 表达式发送值
'收到: Hello'
```

`yield` 表达式的结果 = 外部 `send()` 传来的值（没 send 时是 `None`）。这让生成器可以**双向通信**——协程（coroutine）的雏形：

```python
>>> def counter():
...     n = 0
...     while True:
...         received = yield n         # 产出当前值，等待外部指令
...         if received is not None:   # 收到数值 → 重置
...             n = received
...         else:                      # 没收到 → 自增
...             n += 1
>>> c = counter()
>>> next(c), next(c), next(c)          # 0, 1, 2
(0, 1, 2)
>>> c.send(100)                        # 重置到 100
100
>>> next(c)
101
```

> **版本注意**：`send()` 由 PEP 342（Python 2.5）引入，是 Python 协程史的起点。`async/await`（第 11 章）正是建立在生成器协程之上的语法层升级——理解 `send`/`yield` 的双向通道，理解 `async def` 会容易得多。

**`yield from`（PEP 380，Py3.3）**：把子生成器"委托"出去，扁平化嵌套：

```python
>>> def chain(*iterables):
...     for it in iterables:
...         yield from it        # 逐个产出子迭代器的元素
>>> list(chain([1, 2], [3, 4], [5]))
[1, 2, 3, 4, 5]
```

`yield from` 不止是 `for x in it: yield x` 的缩写——它**转发** `send`/`throw`/`close` 到子生成器，且子生成器的 `return` 值会成为 `yield from` 表达式的值：

```python
>>> def inner():
...     yield 1
...     return "完成"            # yield from 会拿到这个返回值
>>> def outer():
...     result = yield from inner()
...     yield result
>>> list(outer())
[1, '完成']
```

> **实战建议**：扁平化嵌套生成器时用 `yield from` 而不是手动 `for`——它更简洁且正确转发控制流。`itertools.chain(*iterables)` 是标准库的同款实现。

### 6.6.4 实战：数据管道

**流式读大文件**——逐行处理，内存恒定：

```python
>>> def read_lines_clean(path):
...     """逐行读取并跳过空行和注释（流式，不整文件载入）"""
...     with open(path, encoding="utf-8") as f:
...         for line in f:
...             line = line.strip()
...             if line and not line.startswith("#"):
...                 yield line
```

**无限序列**（与 `itertools` 组合）：

```python
>>> import itertools
>>> def fibonacci():
...     a, b = 0, 1
...     while True:
...         yield a
...         a, b = b, a + b
>>> list(itertools.islice(fibonacci(), 10))      # 取前 10 个
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
>>> list(itertools.islice(itertools.takewhile(lambda x: x < 100, fibonacci()), 20))
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
```

**生成器管道**——每层一个生成器，数据流式穿过（不建中间列表）：

```python
>>> def integers():
...     n = 0
...     while True:
...         yield n
...         n += 1
>>> squares = (x * x for x in integers())
>>> evens_sq = (x for x in squares if x % 2 == 0)
>>> first10 = list(itertools.islice(evens_sq, 10))
>>> first10
[0, 4, 16, 36, 64, 100, 144, 196, 256, 324]
```

**内存对比实验**——同一任务，列表全量 vs 生成器流式：

```python
>>> import sys, itertools
>>> def square_list(n):
...     return [i * i for i in range(n)]
>>> def square_gen(n):
...     return (i * i for i in range(n))
>>> big = 10**7
>>> sys.getsizeof(square_list(big))       # 列表：~89 MB 内存（指针数组）
89095160
>>> g = square_gen(big)
>>> sys.getsizeof(g)                      # 生成器：常数级（~200 字节）
200
>>> sum(g)                                # 但能算出和，内存不变
333333283333335000000
```

> **工程影响**：`square_list` 的指针数组占 ~89 MB（且这不含各平方数的 `int` 对象本体——实际内存更大），`square_gen` 恒为 ~200 字节——对内存敏感的数据处理（大数据、日志、流媒体），生成器是默认选择。代价是**单次消费**和**逐元素开销**，批量场景要权衡（详见 6.5.3 的选型表）。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 函数定义 | `def` 是创建函数对象的可执行语句，函数体延迟执行。`return` 缺省返回 `None`。`def` 编译为 `MAKE_FUNCTION`，调用时建栈帧 |
| 一等公民 | 函数是对象：可赋值、入容器、作参数/返回值。`callable()` 与 `__call__` 协议让任何对象可调用（衔接第 7 章） |
| 注解 | 注解只存元数据（`__annotations__`），不参与运行时类型检查。PEP 3107 → 484 → 563 → 649 演进 |
| 传参语义 | 按对象传递（call-by-sharing）：形参修改对象内容 → 调用方可见；重新绑定 → 不可见。判断依据是可变性 |
| 默认参数 | 默认值在 `def` 时**求值一次**。可变默认参数共享同一对象是经典 bug，用 `None` 哨兵 + 函数体内惰性创建 |
| 限定参数 | `*` 之后 keyword-only（PEP 3102）；`/` 之前 positional-only（PEP 570）。`/` 释放"参数名承诺"，适合内部实现 |
| 封包解包 | `*`/`**` 是硬币两面：定义侧 `*args`/`**kwargs` 收拢，调用侧 `f(*seq)`/`f(**m)` 拆开。PEP 448 扩展到字面量 `[*a]`/`{**d}`。`*` 会消耗迭代器 |
| 参数透传 | `def wrapper(*args, **kwargs): return f(*args, **kwargs)` 是装饰器地基，透传必须成对 |
| 命名空间 | LEGB 查找链（Local→Enclosing→Global→Builtin）。变量归属**编译期**确定，`LOAD_FAST`/`LOAD_GLOBAL`/`LOAD_DEREF` 对应三种来源 |
| `global`/`nonlocal` | 函数内赋值默认建局部；改全局用 `global`，改外层函数变量用 `nonlocal`。只读外层不需要声明 |
| 闭包 | 闭包 = 函数 + cell 捕获变量，外层 `STORE_DEREF`/内层 `LOAD_DEREF`。**晚期绑定陷阱**：循环中建 lambda 捕获同一个变量，用 `lambda i=i:` 快照修复 |
| `lambda` | 单表达式匿名函数。Guido 拒绝语句级 lambda（可读性）。选型：一行逻辑用 lambda，其余用 `def` 或可调用对象 |
| 高阶函数 | `key=`（DSU 机制）比 `cmp` 高效且易写；`map`/`filter` 惰性、`reduce` 在 `functools`；`partial` 部分应用。**推导式优先于 map/filter** |
| 纯函数 | 纯函数可测/可缓存/可并发。函数式风格 = 写纯函数，副作用收敛到 I/O 边界 |
| 生成器函数 | 含 `yield` 即生成器：调用返回生成器对象、惰性产出、单次消费、状态机（`YIELD_VALUE` 挂起帧）。`send`/`yield from` 是协程基础（衔接第 11 章） |
| 数据管道 | 生成器让超大数据/无限序列可处理，内存恒定（O(1)），每时刻只存一个元素 |

---

#### 练习 6

1. **预测输出——函数对象**：运行以下代码，写出输出并解释为什么。
   ```python
   def f():
       print("函数体执行")
       return 42

   result = f
   print(result())
   print(f.__name__)
   ```

2. **传参语义判断**：以下每个函数对调用方的影响是什么？区分"修改了对象"和"重新绑定"。解释每个输出的原因。
   ```python
   a = [1, 2, 3]
   def f1(lst): lst.append(4)
   def f2(lst): lst = lst + [4]
   def f3(lst): lst[0] = 99
   def f4(lst): lst.extend([4])
   f1(a); print(a)    # ?
   f2(a); print(a)    # ?
   f3(a); print(a)    # ?
   f4(a); print(a)    # ?
   ```

3. **修复默认参数 bug**：下面的函数希望"每次调用返回一个以参数开头的独立列表"，但行为错误。修复它，并解释 `__defaults__` 里发生了什么。
   ```python
   def make_prefix(prefix, result=[]):
       result.insert(0, prefix)
       return result

   print(make_prefix("A"))   # 期望 ['A']
   print(make_prefix("B"))   # 期望 ['B']，实际 ['B', 'A']！
   ```

4. **手写 `*args`/`**kwargs` 转发**：写一个装饰器 `timed(func)`，打印函数的执行耗时（用 `time.perf_counter`），同时**原样转发**所有参数并返回原结果。要求：无论被装饰函数接受什么签名都能正确工作，最后用 `functools.wraps` 保留元信息（查文档）。

5. **签名设计**：为一个"按条件搜索用户"的 API 设计签名，要求满足：
   - `keyword` 是唯一必填的位置参数
   - `limit`、`offset`、`sort_by` 都是可选且**只能用关键字传**（keyword-only）
   - 未来可能改名 `sort_by`，所以它应该是 positional-only？还是保持 keyword-only？**讨论**这个权衡（参考 6.2.4 的 `/` 与 `*` 设计原则）。

6. **LEGB 预测**：下列每个函数会打印什么？还是报错？如果是 `UnboundLocalError`，解释编译器为什么这么做。
   ```python
   x = "global"
   def a(): print(x)
   def b():
       print(x)
       x = "local"
   def c():
       global x
       x = "changed"
   a()    # ?
   b()    # ?
   c(); print(x)  # ?
   ```

7. **闭包计数器**：用 `nonlocal` 实现 `make_multiplier(n)`——返回一个函数，每次调用返回 `当前计数 × n`，计数每次自增。要求：
   ```python
   m = make_multiplier(3)
   m()  # 0? 3? —— 自定规则，但要每次调用产生不同结果且共享状态
   ```
   再解释：如果不写 `nonlocal` 会怎样，为什么。

8. **修复晚期绑定**：下面代码想得到 `[0, 1, 2]`，实际得到 `[2, 2, 2]`。用两种方式修复（默认参数快照 + 工厂函数），并解释底层 cell 机制。
   ```python
   funcs = []
   for i in range(3):
       funcs.append(lambda: i)
   print([f() for f in funcs])
   ```

9. **高阶函数重构**：用 `sorted`/`key=` 和推导式重写下面这段命令式代码，并比较可读性。数据：`students = [("小明", 90), ("小红", 85), ("小刚", 95)]`（名字, 分数）。
   ```python
   # 命令式：按分数降序排列名字
   pairs = []
   for name, score in students:
       pairs.append((score, name))
   pairs.sort(reverse=True)
   result = [name for score, name in pairs]
   ```
   要求写出：`sorted(students, key=lambda s: s[1], reverse=True)` 及用 `operator.itemgetter` 的版本。

10. **生成器实现——大文件行数统计**：写一个生成器 `count_words(path)`，流式读取文件（不整体载入），返回 `(行号, 单词数)` 的序列，`while` 或 `for` 均可。用 100MB 左右的文本测试，对比"整体 `read().split()`"实现的内存差异（用 `tracemalloc` 测量峰值内存）。

11. **生成器管道**：只用生成器表达式和 `itertools`，实现"求出前 N 个既是平方数又是回文数的数"。要求全程惰性、不建中间列表。提示：`itertools.islice` + `itertools.takewhile`。

12. **深度思考——推导式 vs `map`/`filter`**：给出三个场景，分别论证"用推导式"和"用 `map`/`filter`"更合理，并给出原因。再从字节码/性能角度解释为什么推导式通常更快（衔接第 5 章 5.3）。最后讨论：Python 社区对 `map`/`filter` 的态度是什么，为什么 `reduce` 反而被从内置里挪到 `functools`？

---

**进入下一章的准备**：
- ✅ 理解 `def` 创建函数对象、函数体延迟执行、调用时建栈帧
- ✅ 掌握"函数是一等公民"——可作为参数、返回值、入容器；`__call__` 协议
- ✅ 分清传参语义：修改对象 vs 重新绑定（call-by-sharing）
- ✅ 理解默认参数在 `def` 时求值一次，能用 `None` 哨兵规避可变默认参数陷阱
- ✅ 会用 `*args`/`**kwargs` 封包与解包，能写参数透传的 `wrapper`
- ✅ 理解 PEP 3102（keyword-only）与 PEP 570（positional-only）及 API 设计含义
- ✅ 掌握 LEGB 查找规则，能解释 `UnboundLocalError` 的编译期根源
- ✅ 会用 `global`/`nonlocal` 修改外部作用域，并知道何时不该用
- ✅ 理解闭包的 cell 机制与晚期绑定陷阱，能修复循环中建函数的问题
- ✅ 会用 `lambda`、`sorted(key=)`、`map`/`filter`、`partial`，并懂得推导式优先原则
- ✅ 能写生成器函数，理解惰性求值、单次消费与内存优势
- ✅ 认识 `send`/`yield from` 是协程的底层，为第 7 章 OOP、第 11 章异步打底



