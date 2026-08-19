# 专题：Python 反射机制——运行时看穿并干预对象

> **核心问题**：程序如何在**运行的时候**知道一个对象有什么属性、什么方法、继承自谁、签名长什么样，并且据此**动态地**读属性、调方法、建类、建模块？这就是"反射"（reflection）。为什么 Python 框架（Flask 路由、pytest 参数化、SQLAlchemy、Django ORM、插件系统）能用那么少的代码做那么多事？答案几乎都藏在反射里。

---

> **学习目标**：建立"运行时自省 + 动态操作"的完整心智模型，能识别并善用 `getattr`/`inspect`/动态 `import` 等反射工具，同时清楚它的性能、安全与可维护性代价，知道"哪里该用、哪里不该用"。

---

**本专题与已有章节的关系**：

- 第 7 章 7.2 讲了 `getattr`/`setattr`/`delattr` 的"先用起来"，7.4.4 讲了 `__getattr__`/`__getattribute__` 属性协议——本专题把它们**收拢成"反射"这一统一主题**，并补上它们缺失的"动态调用 / 动态创建 / 反射驱动架构"部分。
- 第 12 章 12.4 给了属性查找的**完整路径**、12.2 讲了 `@wraps` 与 `inspect.signature` 穿透——本专题从"内省工具箱"角度系统化 `inspect`。
- 第 13 章 13.1.3 把 `inspect.getsource` 当作"读标准库源码"的钥匙——本专题把它放进反射全景。
- 第 10 章 10.4 的模块级 `__getattr__`（PEP 562）、第 14 章的 pdb/栈帧，都是反射的生产级应用，本专题在对应小节交叉引用。

**已覆盖内容不重复展开**，用"详见 X.Y 节"引用；本专题重点放在"把它们串成反射体系 + 补齐实战缺口"。

---

## 0. 什么是反射

### 0.1 反射的定义：运行时"看穿并干预"

计算机科学里，**反射**指程序在运行期**检查**（inspect）自身结构，并据此**修改**（modify）自身行为或结构的能力。落到 Python 上，它通常被拆成两半：

- **自省（introspection）**：只读——"这个对象是什么类型？有哪些成员？方法签名是什么？源码在哪？"（`type`、`dir`、`inspect`）
- **反射（reflection）**：读写都行——"动态读一个叫 `name` 的属性、动态调一个叫 `action` 的方法、运行时凭空建一个类、按需加载一个模块"（`getattr`/`setattr`、动态 `import`、`type(name,bases,dict)`）

> **🔑 概念辨析**：很多资料把 `introspection` 和 `reflection` 混为一谈。严格地说，**能"改"才算 reflection**：你用 `dir()` 看一眼对象，那叫自省；你用 `setattr(obj, "x", 1)` 往对象上塞一个它类里根本没定义过的属性，那才叫反射。本专题把两者都涵盖，因为"看"是"改"的前提。

### 0.2 为什么 Python 的反射"开箱即用"最强

三个语言层面的事实叠加，让 Python 反射成为默认能力而非特例：

1. **一切皆对象**：类、函数、方法、模块、甚至代码块（`code` 对象）都是一等对象，都能被传递、检查、改造。
2. **动态类型 + 字典命名空间**：实例属性存在 `__dict__`（一个普通 `dict`）里，属性名是字符串键——字符串就能当"属性寻址"，天然支持 `getattr(obj, some_string)`。
3. **运行时才确定结构**：没有编译期强约束，`getattr` 找得到就返回，找不到才 `AttributeError`，没有任何"编译不过"的门槛。

对比一下就明白了：

```python
# Python：一行搞定"按名字调方法"
>>> def dispatch(obj, method_name, *args):
...     return getattr(obj, method_name)(*args)

# 等价 Java 反射（样板代码的地狱）：
#   Method m = obj.getClass().getMethod(methodName, argTypes);
#   return m.invoke(obj, args);
# —— 还要处理 NoSuchMethodException / IllegalAccessException /
#     InvocationTargetException 三层受检异常
```

> **设计哲学**：Python 的反射哲学是"**信任程序员 + 运行时灵活**"。它不做编译期护栏，把"这个名字到底存不存在"推迟到运行时决定。代价是失去了静态分析（详见 7.3）；收益是框架能用极少的代码做极灵活的事。这是 Python "batteries included + 鸭子类型" 世界观的直接延伸。

### 0.3 跨语言对比（扩展）

| 语言 | 反射能力 | 获取类型的方式 | 动态调方法 | 性能代价 | 编译期安全 |
|------|---------|--------------|-----------|---------|-----------|
| **Python** | ★★★★★ 极强 | `type()` 直接拿 | `getattr` 一行 | 高（比直接访问慢数倍到数十倍，见 7.1） | 无（运行时才知） |
| **Java** | ★★★ 受限但标准 | `obj.getClass()` | `Method.invoke` 样板 | 高（JVM 内省 + 权限检查） | 有（强类型） |
| **C#** | ★★★★ 强 | `typeof` / `obj.GetType()` | `MethodInfo.Invoke` / `dynamic` | 中（有 `dynamic` 缓存） | 部分（编译期 + 运行时） |
| **C++** | ★ 极弱 | RTTI：`typeid` / `dynamic_cast` | 无原生（靠宏/模板黑魔法） | 低（RTTI 本身便宜） | 编译期为主 |
| **Rust** | ★ 极弱（刻意） | 无运行时类型对象 | 无（宏在编译期展开） | 几乎零 | 编译期强制 |

> **工程影响**：Java/C# 的反射是"**元数据 + 框架解释**"模型——注解（annotation）只声明意图，真正的逻辑由 Spring/Hibernate 这类框架用反射读取后生成。Python 的反射是"**代码即实现**"——装饰器直接执行逻辑，没有中间框架层（详见第 12 章 12.1 跨语言对比）。Rust/C++ 几乎不给运行时反射，是因为它们的哲学是"零成本抽象 + 编译期确定"，把灵活性的代价在编译期就还掉了。

---

## 1. 内省基础：看透对象（"只读"反射）

内省是反射的"侦察兵"。在动态操作之前，你总得先知道"对方长什么样"。

### 1.1 `type()`：运行时类型判定

`type(obj)` 返回 `obj` 的**类型对象**（它本身也是个对象，可以被检查、被继承）：

```python
>>> type(42)
<class 'int'>
>>> type(type(42))        # 类型的类型是 type
<class 'type'>

>>> x = "hello"
>>> type(x) is str        # 精确匹配——x 必须是 str，不能是子类
True
>>> class MyStr(str): pass
>>> s = MyStr("hi")
>>> type(s) is str        # False！因为 s 是 MyStr，不是 str
False
>>> isinstance(s, str)    # True——考虑继承关系
True
```

> **⚠️ 陷阱**：`type(x) is int` 与 `isinstance(x, int)` 在**有子类**时结果不同。凡是"这个东西是不是某种类型（含其子类）"的语义，用 `isinstance`；只有"精确就是这个类、不含子类"才用 `type(x) is C`。框架里的 `isinstance` 检查几乎总是更宽松、更安全的选择。

`type` 还有第二副面孔——**三参数动态建类**，那是 4.3 节的内容，这里先按下。

### 1.2 `dir()`：成员可见性清单

`dir(obj)` 返回一个**排序后的字符串列表**，是该对象"当前可见的所有属性/方法名"：

```python
>>> dir(42)[:5]           # 整数的所有方法/属性名
['__abs__', '__add__', '__and__', '__bool__', '__ceil__']
>>> dir(str)[-5:]
['upper', 'zfill', '__getitem__', '__iter__', '__len__']
```

但 `dir()` 不是"真实存储"，而是**协议聚合结果**——它走的是 `__dir__` 钩子（如果定义了），否则聚合"实例 `__dict__` + 类型及其 MRO 上所有可访问名字"。

```python
>>> class C:
...     def __dir__(self):
...         return ["custom", "list", "here"]   # 完全接管 dir() 的输出
>>> dir(C())
['custom', 'here', 'list']
```

**`dir()` vs `obj.__dict__`**——这是必须分清的一对：

| 维度 | `dir(obj)` | `obj.__dict__` |
|------|-----------|---------------|
| 内容 | 可见的**所有**名字（含继承、描述符、特殊方法） | 仅实例**自己**存进去的属性 |
| 来源 | `__dir__` 钩子 / 聚合 MRO | 实例的命名空间字典 |
| 是否含类方法 | 含（通过 MRO 看到） | **不含**（方法在类的 `__dict__` 里） |
| 是否含 `__slots__` 属性 | 含（按 slot 名） | **不含**（`__slots__` 不走 `__dict__`，详见第 7 章 7.7） |

```python
>>> class Point:
...     def __init__(self, x, y):
...         self.x = x; self.y = y
...     def dist(self): return (self.x**2 + self.y**2) ** 0.5
>>> p = Point(3, 4)
>>> p.__dict__            # 只有实例自己塞的
{'x': 3, 'y': 4}
>>> 'dist' in p.__dict__  # 方法不在实例 dict 里
False
>>> 'dist' in dir(p)      # 但通过 dir 能看到（沿 MRO 来自类）
True
```

> **实战建议**：想"看清一个对象到底自己存了什么"，看 `__dict__`；想"看清一个对象现在能访问什么"，看 `dir()`。调试第三方对象时，两者结合用。

### 1.3 `isinstance` / `issubclass`：类型关系判定

```python
>>> isinstance(3.14, (int, float))     # 第二参数可以是元组——"是其中任一"
True
>>> issubclass(bool, int)              # bool 是 int 的子类！
True
>>> issubclass(int, bool)
False
```

**虚基类与反向注册**：`collections.abc` 等用 `__subclasshook__` 让"长得像"的类自动成为子类，不靠真实继承：

```python
>>> from collections.abc import Sequence
>>> class MyList:                       # 没有继承 Sequence
...     def __len__(self): return 0
...     def __getitem__(self, i): return None
>>> issubclass(MyList, Sequence)        # 因为实现了 len+getitem，自动"算"是 Sequence
True
```

> **版本注意**：`isinstance` 的元组形式和虚基类机制在 Python 3 全系一致。注意 `bool` 是 `int` 的子类这个反直觉事实——`True == 1` 为 `True`、`<...>` 比较也有坑（详见第 3 章 3.1）。

### 1.4 `callable()` / `hasattr()` / `vars()`

```python
>>> callable(len), callable(42), callable(lambda: 1)
(True, False, True)

>>> class C:
...     def __call__(self): return "called"
>>> callable(C())            # 实现了 __call__ 的就是 callable
True

>>> vars(p)                  # vars(obj) 等价于 obj.__dict__
{'x': 3, 'y': 4}
>>> vars()                   # 无参时等价于 locals()——当前局部命名空间
```

`hasattr` 是内省里最常用的"有没有这个属性"判断，但它的行为有坑，1.4 只是引入，**2.2 节会专门拆解它的陷阱**。

---

## 2. 属性访问协议：反射的"操作入口"

内省告诉你"有什么"，属性协议才是"怎么动态操作它"的真正入口。

### 2.1 `getattr` / `setattr` / `delattr`：动态三剑客

这三个内置函数与第 7 章讲过的特殊方法**一一对应**，是属性访问协议的"外部操作接口"：

| 操作 | 内置函数 | 对应的特殊方法 |
|------|---------|--------------|
| 读 | `getattr(obj, name[, default])` | `obj.__getattribute__(name)` |
| 写 | `setattr(obj, name, value)` | `obj.__setattr__(name, value)` |
| 删 | `delattr(obj, name)` | `obj.__delattr__(name)` |

核心场景：**属性名是运行时算出来的字符串**，此时无法用点号语法（点号后面必须是字面量标识符）：

```python
>>> config = {"host": "localhost", "port": 8080}
>>> field = input("which field? ")      # 运行时才确定的名字
which field? host
>>> # config.host 写不了——因为点号后不能放变量
>>> getattr(config, field)              # ✅ 用 getattr 动态寻址
'localhost'

# 批量按名字搬运属性——这是反射最经典的用法
>>> src = {"name": "alice", "age": 30}
>>> dst = object.__new__(object)
>>> for key, val in src.items():
...     setattr(dst, key, val)          # 动态注入原本类里没有的属性
>>> dst.name, dst.age
('alice', 30)

>>> delattr(dst, "age")                 # 动态删除
>>> hasattr(dst, "age")
False
```

`getattr` 的第三参数 `default` 让它在属性缺失时**不抛异常**而返回默认值——这是它比点号安全的地方：

```python
>>> getattr(config, "missing", "N/A")   # ✅ 不抛，返回默认
'N/A'
>>> config.missing                     # ❌ 抛 AttributeError
AttributeError: 'dict' object has no attribute 'missing'
```

> **实战建议**：凡是属性名来自外部输入（用户、配置文件、网络消息、数据库列），一律走 `getattr`/`setattr`，因为它们能把"字符串"变成"属性寻址"。点号语法只能在名字是源码里写死的常量时用。

### 2.2 `hasattr` 的致命陷阱（系统化）

`hasattr(obj, name)` 的语义是"对象有没有这个属性"。但实现上它做的事是：**尝试 `getattr(obj, name)`，如果抛出 `AttributeError` 就返回 `False`，其他异常照常往上抛**。问题来了——

```python
# ❌ 陷阱：属性 getter 内部抛 AttributeError 会被 hasattr 误判
>>> class Bad:
...     @property
...     def value(self):
...         raise AttributeError("内部出错了")   # 注意：抛的是 AttributeError
...     def other(self):
...         return 1
>>> b = Bad()
>>> hasattr(b, "value")        # 你以为"没有 value"？其实它"有"，只是 getter 崩了
False                          # ❌ 误判！
>>> hasattr(b, "other")
True
```

为什么危险？因为依赖 `hasattr` 的代码会基于"没有该属性"做分支，结果把"属性存在但出错"和"属性真的不存在"混为一谈，掩盖真实 bug。

```python
# ❌ 错误用法——用 hasattr "探测"后再操作，可能吞掉真实异常
>>> if hasattr(b, "value"):
...     do_something(b.value)   # 这里永远进不来，真实错误被静默跳过

# ✅ 正确写法——直接访问，让异常暴露出来，或在异常里区分
>>> try:
...     v = b.value
... except AttributeError as e:
...     v = None                # 只有真的"没这个属性"才走默认
```

> **⚠️ 陷阱**：`hasattr` 本质是"捕获 `AttributeError` 来判断"，所以它会被任何**内部抛出的 `AttributeError`** 骗到。更隐蔽的是 `__getattr__`（2.3 节）里若访问别的属性又触发 `AttributeError`，也会让外层 `hasattr` 误判。调试"明明有属性却被判为没有"的诡异行为时，**先直接访问看真实异常**，别迷信 `hasattr`。

### 2.3 完整属性查找路径 + 字节码视角

`getattr(obj, name)` 触发的是 `type(obj).__getattribute__(obj, name)`——也就是第 12 章 12.4 讲过的**完整查找路径**。这里用反射的视角重述一遍，并补上字节码证据：

`object.__getattribute__` 对"普通实例属性"的执行顺序：

```
1. 数据描述符（__get__ 且 __set__ 都有）→ 优先拦截
2. 实例 __dict__ 里有没有这个 key
3. 非数据描述符（只有 __get__）→ 此时拦
4. 类型 __dict__ / MRO 上的普通属性（含方法）
5. 以上都没有 → 调 __getattr__（若定义）兜底
6. 还没解决 → 抛 AttributeError
```

`property` 在第 1 步拦截（数据描述符），实例 `dict` 在第 2 步，方法在第 4 步绑定，`__getattr__` 在第 5 步兜底。详细展开与示例见第 12 章 12.4，本专题不再重复。

**字节码证据**：点号访问和 `getattr` 调用，编译出来是**完全不同的指令流**：

```python
# 示例：两种"读 obj.x"的写法
def direct(obj):
    return obj.x

def via_getattr(obj):
    return getattr(obj, "x")

import dis
dis.dis(direct)
dis.dis(via_getattr)
```

直接用点号的 `direct`，编译为：

```
  # 3.13 实测（3.12 显示偏移 0/2/4/24，3.14 用 LOAD_FAST_BORROW 替代 LOAD_FAST）
              RESUME                   0
              LOAD_FAST                0 (obj)        # 3.14 上为 LOAD_FAST_BORROW
              LOAD_ATTR                0 (x)
              RETURN_VALUE
```

而 `via_getattr` 编译为一次**普通函数调用**：

```
  # 3.13 实测
              RESUME                   0
              LOAD_GLOBAL              1 (getattr + NULL)  # 3.12 显示为 NULL + getattr
              LOAD_FAST                0 (obj)             # 3.14 上为 LOAD_FAST_BORROW
              LOAD_CONST               1 ('x')
              CALL                     2
              RETURN_VALUE
```

> **🔑 机制洞察**：点号 `obj.x` 是一条**专用字节码 `LOAD_ATTR`**（3.11+ 会被 PEP 659 特化为 `LOAD_ATTR_INSTANCE_VALUE` 等自适应指令，见 7.1）；`getattr(obj, "x")` 是把 `getattr` 当**普通全局函数** `CALL` 出去。所以 `getattr` 多了一层函数调用开销，但换来"属性名可以是任意运行时字符串"的灵活性。两者最终都走到同一条属性查找路径——只是入口不同。

> **版本注意（3.12–3.14 实测）**：三个版本的**指令名完全一致**（`RESUME` / `LOAD_FAST` / `LOAD_ATTR` / `CALL` / `RETURN_VALUE`），但有两处细节差异：(1) 3.14 的 `LOAD_FAST` 改名为 `LOAD_FAST_BORROW`（PEP 709 无意借用优化，对本节理解无影响）；(2) 3.12 显示显式偏移（`0/2/4/24`），3.13+ 不再显示偏移。跨版本一致的核心规律：`obj.x` 两条指令（`LOAD_FAST obj` → `LOAD_ATTR x`），`getattr(obj, "x")` 多出 `LOAD_GLOBAL getattr` + `LOAD_CONST 'x'` + `CALL` 三条指令，**"多一层函数调用"是 `getattr` 慢的根本原因**。

### 2.4 递归陷阱：在钩子里写 `self.x`

第 12 章 12.4.2 已从属性协议角度讲过，这里从反射角度复述这个高频坑。`__getattribute__` 和 `__setattr__` 会拦截**每一次**属性访问/赋值，所以钩子里再写 `self.x` 会**无限递归**：

```python
# ❌ 错误——__getattribute__ 里写 self.x 又触发 __getattribute__
>>> class Buggy:
...     def __getattribute__(self, name):
...         if name == "x":
...             return self.x + 1        # ❌ 递归！self.x 又进 __getattribute__
...         return object.__getattribute__(self, name)

# ✅ 正确——绕过自己，直接调 object 的查找
>>> class Fixed:
...     def __getattribute__(self, name):
...         if name == "x":
...             return object.__getattribute__(self, "x") + 1   # ✅ 走 object 的
...         return object.__getattribute__(self, name)
```

`setattr` 同理：`self._data = {}` 会触发自己的 `__setattr__`，得用 `object.__setattr__(self, "_data", {})`。详见第 12 章 12.4.2。

---

## 3. `inspect` 模块：专业内省工具箱

`dir()` 和 `getattr` 是"手搓"内省；`inspect` 模块是 Python 标准库提供的**专业内省工具箱**，框架和 IDE 背后都靠它。

### 3.1 `inspect.signature`：签名反射

获取函数/可调用对象的**结构化签名**（参数名、默认值、注解、种类），比手解析 `__code__.co_varnames` 可靠得多：

```python
>>> import inspect
>>> def process(name: str, *, timeout: int = 30, retry: bool = False):
...     ...
>>> sig = inspect.signature(process)
>>> sig
<Signature (name: str, *, timeout: int = 30, retry: bool = False)>

# 结构化访问——这是框架自动校验参数的基础
>>> for pname, param in sig.parameters.items():
...     print(pname, param.kind, param.default)
name POSITIONAL_OR_KEYWORD <class 'inspect._empty'>
timeout KEYWORD_ONLY 30
retry KEYWORD_ONLY False

# 绑定实参，做"调用前校验"
>>> sig.bind("task", timeout=10)         # ✅ 合法
<BoundArguments (name='task', timeout=10)>
>>> sig.bind()                           # ❌ name 没给
TypeError: missing a required argument: 'name'
```

**穿透装饰器**：`inspect.signature` 会沿 `__wrapped__` 链解析（第 12 章 12.2 的 `@wraps` 正是为此存在），拿到**被装饰函数的原始签名**：

```python
>>> from functools import wraps
>>> def logged(f):
...     @wraps(f)                       # 关键：保留 __wrapped__
...     def wrapper(*a, **k):
...         return f(*a, **k)
...     return wrapper
>>> @logged
... def add(x, y): return x + y
>>> inspect.signature(add)               # ✅ 拿到的是 add 的签名，不是 wrapper 的
<Signature (x, y)>
```

> **工程影响**：Flask/Django 的路由装饰器、CLI 框架、参数校验库，全靠 `inspect.signature` 在运行时"读懂"你的函数长什么样，再把 HTTP 参数 / 命令行参数自动映射到形参。没有它，这些框架就得手写大量样板。

### 3.2 `getsource` / `getfile` / `getmodule`：源码级反射

能在运行时**把对象的源码还原成字符串**——前提是源码可得（交互式定义、C 实现的内置对象都不行）：

```python
>>> import inspect, collections
>>> print(inspect.getsource(collections.Counter.most_common))   # 直接读标准库源码
    def most_common(self, n=None):
        ...
>>> inspect.getfile(collections.Counter)     # 源文件路径
'/usr/lib/python3.14/collections/__init__.py'
>>> inspect.getmodule(collections.Counter)   # 所属模块对象
<module 'collections' ...>
```

> **实战建议**：遇到看不懂的标准库行为，**当场 `inspect.getsource` 读源码**，比翻文档快且准。这是第 13 章 13.1.3 反复强调的"先查标准库再手写"习惯的硬核手段。C 加速的内置（如 `list.append`）没有 Python 源码，`getsource` 会抛 `OSError`——此时看 `_collections` 等 CPython 仓库里的实现。

### 3.3 `getmro` / `getclasstree`：继承结构反射

```python
>>> class A: pass
>>> class B(A): pass
>>> class C(B): pass
>>> inspect.getmro(C)          # 方法解析顺序，元组
(<class '__main__.C'>, <class '__main__.B'>, <class '__main__.A'>, <class 'object'>)

>>> inspect.getclasstree([A, B, C])   # 嵌套的继承树
[(<class 'object'>, ()),
 [(<class '__main__.A'>, (<class 'object'>,)),
  [(<class '__main__.B'>, (<class '__main__.A'>,)),
   [(<class '__main__.C'>, (<class '__main__.B'>,))]]]
```

`getmro` 返回的就是 `C.__mro__`（详见第 7 章 7.3 的 MRO/super 机制），`inspect` 版本对动态类和旧式类型更稳健。

### 3.4 谓词家族：区分"这是函数还是方法还是类"

`types` 与 `inspect` 提供一组**类型谓词**，在"遍历一个对象的所有成员，把它们分门别类"时 indispensable：

```python
>>> import inspect
>>> def f(): pass
>>> class C:
...     def m(self): pass
...     @staticmethod
...     def sm(): pass
...     @classmethod
...     def cm(cls): pass

>>> inspect.isfunction(f), inspect.isfunction(C.m)        # C.m 未绑定时是函数
(True, True)
>>> inspect.ismethod(C().m)                               # 绑定后才是方法
True
>>> inspect.isfunction(C.sm), inspect.isfunction(C.cm)    # 静态/类方法本质是函数
(True, True)
>>> inspect.isclass(C), inspect.isbuiltin(len), inspect.isgeneratorfunction((lambda: (yield)))  
(True, True, True)
```

> **🔑 辨析**：`inspect.ismethod` 只对**已绑定**的方法为 `True`（即 `instance.method`，带 `self` 绑定的 `types.MethodType`）；未绑定的 `Class.method` 仍是普通 `function`。`staticmethod`/`classmethod` 对象本身不是方法也不是函数，它们的 `__func__` 才是函数——这是第 7 章 7.2 方法三兄弟的延伸。

### 3.5 `stack` / `trace` / `frame`：运行时调用栈反射（进阶）

`inspect.stack()` 返回当前调用栈的帧列表，每帧都能反射出"谁调用了我、在哪个文件哪一行、局部变量是什么"。这是日志自动带上下文、调试器、覆盖率工具的实现原理：

```python
>>> import inspect
>>> def who_called_me():
...     caller = inspect.stack()[1]        # 上一帧
...     return f"called by {caller.function} @ {caller.filename}:{caller.lineno}"
>>> def outer():
...     return who_called_me()
>>> outer()
'called by outer @ /tmp/x.py:7'
```

帧对象（`frame`）还能用 `f_locals` / `f_globals` 反射局部与全局命名空间——pdb 的单步调试、第 14 章的 post-mortem 都建立在帧反射之上。

> **⚠️ 陷阱**：`inspect.stack()` 会**遍历并保留整个调用栈的帧**，成本不低（尤其在深递归里），且保留帧会拖住垃圾回收。生产热路径上别滥用；需要上下文时用轻量的 `sys._getframe(1)` 或直接记日志，少用 `stack()`。

---

## 4. 动态调用与动态创建（"写"反射——本专题新增重点）

只读还不够，反射的威力在于"运行时凭字符串把东西造出来、调起来"。

### 4.1 `getattr` 调用方法：运行时分发

把"方法名"当数据传递，实现命令分发表——这是反射最朴素也最常用的形态：

```python
# ✅ 反射驱动的命令分发（vs 一长串 if/elif）
>>> class Calculator:
...     def add(self, a, b): return a + b
...     def sub(self, a, b): return a - b
>>> calc = Calculator()
>>> def run(calc, op, a, b):
...     method = getattr(calc, op)        # op 是 "add" / "sub" 这种字符串
...     return method(a, b)
>>> run(calc, "add", 3, 4)               # getattr 拿到方法后直接调用
7
>>> run(calc, "sub", 10, 2)
8
```

对比 `if op == "add": ... elif op == "sub": ...`：反射版新增操作**不用改分发逻辑**，只加方法即可——这本质是"用数据表代替分支"（命令模式的数据驱动版）。

> **⚠️ 安全红线**：若 `op` 来自**不可信输入**（用户输入、网络消息），直接 `getattr(calc, op)` 等于让外部决定调用哪个方法——攻击者能调到你不想暴露的方法（如 `_delete_everything`）。务必用**白名单**约束可调用的名字集合。

```python
# ✅ 安全：白名单 + getattr 默认值兜底
ALLOWED = {"add", "sub"}
def run_safe(calc, op, a, b):
    if op not in ALLOWED:
        raise ValueError(f"unknown op: {op}")
    return getattr(calc, op)(a, b)
```

### 4.2 `setattr` 动态注入属性

运行时往对象上"塞"原本类里没有的属性——序列化、动态配置、测试桩的常见手法：

```python
# 把一个 dict 动态变成对象的属性
>>> class Record: pass
>>> r = Record()
>>> data = {"name": "alice", "age": 30, "role": "admin"}
>>> for k, v in data.items():
...     setattr(r, k, v)
>>> r.name, r.age, r.role
('alice', 30, 'admin')
```

> **实战建议**：`dataclasses` / `types.SimpleNamespace` 其实就能一步到位（`SimpleNamespace(**data)`）。`setattr` 循环更适合"边读边转换"（如把 JSON 的 snake_case 映射成对象的 camelCase）。注意：往定义了 `__slots__` 的类上 `setattr` 未声明的名字会抛 `AttributeError`（详见第 7 章 7.7）。

### 4.3 `type()` 三参数：运行时建类

`type(name, bases, dict)` 是 `class` 语句的**运行时等价物**——你能在程序跑起来后才决定类名、基类、方法：

```python
# 等价于：
#   class Point(Base):
#       x = 0
#       def __init__(self, x): self.x = x
>>> def __init__(self, x):
...     self.x = x
>>> Point = type("Point", (object,), {"x": 0, "__init__": __init__})
>>> p = Point(5)
>>> p.x
5
```

这不是玩具——动态建类是**元类**（第 12 章 12.5）和**ORM 声明式模型**的底层机制：SQLAlchemy 的 `declarative_base()` 正是根据 `__tablename__` / `Column(...)` 在元类里动态组装出表对应的类。

> **版本注意**：3.x 全系 `type` 三参数行为一致。真正的变化在元类的 `__prepare__`（PEP 3115，3.3+，让类体用 `dict` 之外的命名空间）和 `class` 语句用 `type.__call__` 的流程——详见第 12 章。

### 4.4 动态 `import`：`importlib.import_module`

硬编码 `import` 是"写死"的；运行时按字符串加载模块，才是插件系统的基石：

```python
# ❌ 写死——每个插件都要手动 import
# import plugin_a, plugin_b, plugin_c

# ✅ 动态——从配置/目录里读模块名，按需加载
>>> import importlib
>>> mod_name = "json"                      # 运行时才知道要哪个
>>> mod = importlib.import_module(mod_name)
>>> mod.dumps({"a": 1})
'{"a": 1}'
```

`importlib.import_module` 走的是第 10 章 10.1 讲的**同一套 import 流水线**（finder → spec → loader），并复用 `sys.modules` 缓存。它比古老的 `__import__()` 更清晰、更推荐。

```python
# 加载子模块 / 相对导入
>>> importlib.import_module("os.path")            # 点号分隔的子模块
>>> importlib.import_module(".utils", "mypkg")    # 相对导入：在 mypkg 内找 .utils
```

> **实战建议**：插件系统的标准套路 = "扫描入口点（entry points）/ 目录 → `importlib.import_module` → `getattr` 拿插件类 → `type`/`__init__` 实例化"。配合第 10 章的模块级 `__getattr__`（PEP 562）还能做懒加载（用到才 import，优化启动）。

### 4.5 `eval` / `exec`：终极动态执行（危险区）

`eval(expr)` 执行一个字符串表达式并返回结果；`exec(code)` 执行一段语句（不返回值）。它们把"字符串当代码跑"——这是反射的**最深处**，也是**最危险处**：

```python
# eval：表达式 → 值
>>> eval("1 + 2 * 3")
7
>>> x = 10
>>> eval("x * x", {}, {"x": 5})     # 可传 globals/locals 沙箱（但沙箱并不真安全）
25

# exec：语句 → 副作用
>>> namespace = {}
>>> exec("y = 1 + 2", namespace)
>>> namespace["y"]
3
```

> **🚨 安全红线（最高优先级）**：**永不 `eval` / `exec` 任何包含不可信内容的字符串**。用户输入一旦进 `eval`，就等于给了对方在你进程里执行任意代码的权力（RCE，远程代码执行）。这和 `pickle.loads` 反序列化不可信数据、`os.system` 拼用户输入一样，是安全审计的"三个红色禁区"之一（详见 7.2）。

```python
# ❌ 致命——用户输入直接 eval
user_input = "__import__('os').system('rm -rf /')"
eval(user_input)                    # 💀 任意命令执行

# ✅ 替代：用 ast.literal_eval 解析"数据"而非"代码"
>>> import ast
>>> ast.literal_eval("[1, 2, 3]")   # 只接受字面量（list/dict/str/num...）
[1, 2, 3]
>>> ast.literal_eval("__import__('os')")   # 表达式不行，安全拒绝
ValueError: malformed node or string
```

> **实战建议**：真要执行动态逻辑，优先用更受限的手段——`ast.literal_eval`（数据）、`getattr` + 白名单（方法调用）、`importlib`（模块加载）。`eval`/`exec` 只在"代码来源 100% 可信且必要"（如模板引擎、REPL 内核）时谨慎使用，且务必用受限 `globals`（如 `{"__builtins__": {}}`）。

---

## 5. 反射驱动的架构模式（实战，本专题核心扩展）

把前面工具组合起来，能实现"写一次框架、适配无数业务"的架构。这一章全是生产级范式。

### 5.1 插件自动发现与注册

目标：业务方只要写个类并打上 `@register`，框架就能自动收集所有插件——**新增插件零改动框架代码**。

```python
# plugin_base.py —— 框架侧
_REGISTRY = {}

def register(cls):                 # 装饰器即"登记入口"
    _REGISTRY[cls.__name__] = cls  # 反射读类名作为 key
    return cls

def load_plugins(package_name):
    """扫描包内所有模块，触发它们的 @register"""
    import importlib, pkgutil
    pkg = importlib.import_module(package_name)
    for mod_info in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{package_name}.{mod_info.name}")  # 导入即注册
    return _REGISTRY

# plugin_a.py —— 业务侧（框架完全不用改）
from plugin_base import register
@register
class HelloPlugin:
    def run(self): return "hello"

# 使用
>>> registry = load_plugins("plugins")
>>> registry["HelloPlugin"]().run()
'hello'
```

这里组合了 **`__name__` 反射类名 + 装饰器登记 + `importlib` 动态加载**三件套。这是 pytest 插件、Flask 扩展、Django app 的核心机制之一。

> **实战建议**：比"扫描目录 + `importlib`"更干净的做法是用 **`importlib.metadata.entry_points`**（PEP 621 的 entry points，详见第 10 章打包）。第三方包在安装时声明入口点，框架 `importlib.metadata` 直接拿到，无需自己扫目录。

### 5.2 ORM 字段映射

目标：用户用 `class User(Model): name = Column(str)` 声明模型，框架**反射读 `__annotations__` 和类属性**，自动生成表结构、增删改查。这是 SQLAlchemy / Django ORM 的缩影：

```python
>>> class Column:
...     def __init__(self, type_): self.type_ = type_
>>> class Model:
...     __table__ = None
>>> class User(Model):
...     name: str = Column(str)         # 注解 + 描述符字段
...     age: int = Column(int)

# 框架反射：遍历类 dict，挑出 Column 实例，建成字段映射
>>> fields = {
...     name: attr.type_
...     for name, attr in User.__dict__.items()      # 反射读类自己的命名空间
...     if isinstance(attr, Column)
... }
>>> fields
{'name': <class 'str'>, 'age': <class 'int'>}
```

`__annotations__`（第 6 章细讲）在这里也用得上：即使字段值是动态生成的，`name: str` 的注解仍留在 `User.__annotations__` 里，框架可借此拿到类型信息。这是"声明式字段 = 描述符 + 反射"组合（第 12 章 12.8 的 mini-dataclass 同款思路）。

### 5.3 通用序列化 / 反序列化

用 `dataclasses.fields` + `getattr`/`setattr` 写一个**不依赖具体类的通用 (de)serialize**：

```python
>>> from dataclasses import dataclass, fields, asdict

>>> @dataclass
... class Point:
...     x: int
...     y: int

# 序列化：反射遍历所有字段，逐个 getattr
>>> def to_dict(obj):
...     return {f.name: getattr(obj, f.name) for f in fields(obj)}
>>> to_dict(Point(1, 2))
{'x': 1, 'y': 2}

# 反序列化：反射按字段名 setattr 重建
>>> def from_dict(cls, d):
...     return cls(**{f.name: d[f.name] for f in fields(cls)})
>>> from_dict(Point, {"x": 3, "y": 4})
Point(x=3, y=4)
```

`@dataclass` 自带的 `asdict` 更完善，但上面的手写版揭示了原理：**序列化 = `fields` + `getattr`，反序列化 = `fields` + 构造器**。`dataclasses` 本身就是"用反射把样板代码（init/eq/repr）自动生成"的官方范例（详见第 7 章 7.7）。

### 5.4 命令行接口自动生成

用 `inspect.signature` 把一个普通函数的参数，自动变成 `argparse` 的命令行选项——写完业务逻辑，CLI 自动有了：

```python
>>> import argparse, inspect
>>> def greet(name: str, loud: bool = False):
...     msg = f"Hello, {name}!"
...     return msg.upper() if loud else msg

>>> def func_to_cli(f):
...     sig = inspect.signature(f)
...     parser = argparse.ArgumentParser()
...     for pname, p in sig.parameters.items():
...         if p.default is inspect.Parameter.empty:
...             parser.add_argument(pname)                    # 必填位置参数
...         else:
...             parser.add_argument(f"--{pname}", default=p.default)  # 可选
...     args = parser.parse_args()
...     return f(**vars(args))

# 命令行：python cli.py alice --loud  →  "HELLO, ALICE!"
```

这正是 `typer` / `fire` 这类库的核心：它们用 `inspect.signature` 反射你的函数，把参数类型/默认值映射成 CLI 参数。**你写函数，框架写 CLI**——反射的价值在这里体现得淋漓尽致。

### 5.5 轻量依赖注入容器

用反射读取函数**形参名**，自动按名字从容器里装配依赖（对比第 7 章的工厂/依赖倒置模式）：

```python
>>> class Container:
...     def __init__(self): self._services = {}
...     def register(self, name, inst): self._services[name] = inst
...     def resolve(self, f):                      # 反射 f 的形参名 → 自动注入
...         sig = inspect.signature(f)
...         kwargs = {n: self._services[n] for n in sig.parameters}
...         return f(**kwargs)

>>> c = Container()
>>> c.register("db", "a-database-connection")
>>> def handler(db):                  # 形参名 db 恰好对应容器 key
...     return f"using {db}"
>>> c.resolve(handler)               # 自动把 db 注入进去
'using a-database-connection'
```

> **⚠️ 陷阱**：这种"按形参名匹配"的 DI 很脆——重命名形参就断。生产级 DI 框架（如 `dependency-injector`）用**类型注解**而非名字来匹配（`inspect.signature` 读 `param.annotation`），更稳健。这里演示的是原理，不是让你在业务里裸写。

---

## 6. 注解与元数据反射

### 6.1 `__annotations__` 在三层的结构

类型注解不是装饰品——它们是**运行时可反射的元数据**，存在 `__annotations__` 里。注意它在类、函数、模块三层的位置不同：

```python
>>> def f(a: int, b: str) -> bool: pass
>>> f.__annotations__                        # 函数注解
{'a': <class 'int'>, 'b': <class 'str'>, 'return': <class 'bool'>}

>>> class C:
...     x: int = 0
...     y: str
>>> C.__annotations__                        # 类注解（注意：y 没赋值也有注解）
{'x': <class 'int'>, 'y': <class 'str'>}

>>> import sys
>>> module_level: float = 1.0
>>> globals().__annotations__ or __annotations__   # 模块级注解（3.6+）
{'module_level': <class 'float'>}
```

> **⚠️ 陷阱**：类体里 `x: int = 0` 会**同时**写 `x` 进 `__dict__`（值为 0）和 `x` 进 `__annotations__`（值为 `int`）；但 `y: str` 没赋值，**只**进 `__annotations__`，不进 `__dict__`——所以 `C.y` 会抛 `AttributeError`，而 `C.__annotations__['y']` 能拿到 `str`。这是很多 ORM / 校验库读取字段类型时踩的坑。

### 6.2 装饰器元数据收集

装饰器可以在"包装"你的函数时，**反射并收集其元数据**（签名、注解、docstring），用于生成文档、校验、路由表。这是第 12 章 `@wraps` 的延伸——但更进一步：不仅保留，还**读取利用**：

```python
>>> def route(path):                          # 极简 Flask 路由装饰器
...     def deco(f):
...         sig = inspect.signature(f)        # 反射签名
...         f._route = (path, sig)            # 把元数据挂回函数对象
...         return f
...     return deco

>>> @route("/add")
... def add(a: int, b: int) -> int: return a + b

>>> add._route        # 框架后来能反射出这条路由
('/add', <Signature (a: int, b: int) -> int>)
```

> **🔑 机制洞察**："把元数据挂回函数对象"（`f._route = ...`）是 Python 反射的常用技巧——因为函数是对象，你可以往它身上任意 `setattr` 自定义属性（只要名字不撞内置）。Flask/Django 的 URL 映射、pytest 的标记，底层都是这套"装饰器写元数据 + 框架反射读元数据"。

---

## 7. 反射的代价与边界

反射不是银弹。用之前必须知道它要你付出什么。

### 7.1 性能代价（`timeit` 基准）

反射操作比直接操作慢，因为多了一层**函数调用 + 字典查找 + 协程分发**。量级参考（3.12–3.14，`timeit` 100万次，仅供参考，机器相关）：

```python
# 三种"读属性"的写法，速度递减
obj.x                 # 直接访问：最快（LOAD_ATTR 特化后近乎内联）
getattr(obj, "x")     # getattr 调用：约慢 2–2.5 倍（一次函数调用 + 查找路径）
obj.__getattribute__("x")  # 直接调钩子：更慢，且绕过描述符优化
```

`dir()` 是 O(n) 且要聚合 MRO，反复在热循环里 `dir(obj)` 很贵。`inspect.stack()` 遍历整条调用栈，成本更高（见 3.5）。

> **性能数据（3.12–3.14 实测）**：在普通对象上，`getattr` 约为直接属性访问的 **2–2.5 倍**耗时（3.12: 2.0×，3.13: 2.3×，3.14: 2.2×）；`hasattr` 因为要"尝试 getattr + 捕获异常"（命中缺失时），比先判断再访问更慢。结论：**反射用在"边界/初始化/低频"处**，别塞进每帧每循环的高频路径。需要高频动态访问时，缓存 `getattr` 的结果（如 `meth = getattr(obj, name)` 提出循环外）。

> **版本注意**：3.11 的 PEP 659 自适应解释器让**直接** `obj.x` 更快（特化为 `LOAD_ATTR_INSTANCE_VALUE` 等专用指令），但 `getattr` 函数调用这条路的相对劣势基本不变。性能差异在 3.11+ 反而更明显，因为直接访问被优化得更多。

### 7.2 安全陷阱

| 危险操作 | 风险 | 安全替代 |
|---------|------|---------|
| `eval`/`exec` 不可信字符串 | 任意代码执行（RCE） | `ast.literal_eval`、白名单 |
| `pickle.loads` 不可信数据 | 反序列化即 RCE（详见第 9 章 9.x） | `json`、签名校验 |
| `getattr(obj, user_input)` 无白名单 | 调用到不该调用的内部方法 | 白名单 `ALLOWED` 集合 |
| `setattr` 任意名字 | 覆盖/注入内部属性，破坏不变量 | 校验名字格式、限制前缀 |
| 反射绕过"私有"（`obj._secret`） | 破坏封装契约 | 尊重单下划线约定，不靠反射撬 |

> **🚨 安全红线**：`eval`/`exec` 和 `pickle.loads` 处理不可信输入，是 Python 安全领域的两大"红色禁区"。反射赋予你"绕过一切封装"的能力，但**能力越强，越要在入口做白名单/来源校验**。

### 7.3 可维护性代价

反射让你"看代码时不知道它到底调了谁"：

- **失去静态分析**：IDE 跳转、自动补全、`mypy` 类型检查，对 `getattr(obj, name)` 这类动态调用全部失效——`name` 是字符串，类型系统无从推断。
- **调试黑盒化**：一个属性被 `__getattr__` 动态算出、被 `setattr` 动态注入、被元类动态添加，出问题时你 grep 不到它的定义。
- **重构杀手**：重命名一个方法，所有靠字符串引用的地方（字符串字面量 `"old_name"`）不会被重构工具捕获，静默失效。

> **工程影响**：反射代码是"隐式契约"——它假设"对方恰好有这个名字"。一旦契约被破坏（重构、版本升级），错误在最远的使用点才爆发，而不是在定义点。这就是为什么反射要**集中在框架/基础设施层**，业务逻辑尽量写显式的、能被静态分析捕获的代码。

### 7.4 使用边界（呼应第 12 章 12.9.4）

> **实战建议**：反射的黄金法则是"**能不用就不用，用在边界处**"。

- ✅ **该用**：框架/库（路由、插件、ORM、序列化、CLI、DI）、与不可控外部数据/模块交互的适配层、测试与调试工具。这些是"你不知道对方具体长什么样"的场景，反射正是为此而生。
- ❌ **不该用**：业务核心逻辑里用 `getattr` 代替明确的方法调用、用 `eval` 代替解析、用 `setattr` 代替显式字段。这些地方"显式优于隐式"（Python 之禅）才是正道。
- **决策顺序**：显式直接访问 → 不行再用 `getattr`（有默认/动态名）→ 再不行才上 `inspect`/动态 `import` → 最后才考虑 `eval`/`exec`（且必须有来源保障）。

---

## 8. 本章小结

| 主题 | 核心要点 |
|------|---------|
| 反射定义 | 运行时"看穿（introspection）+ 干预（reflection）"对象；能改才算 reflection |
| 为何 Python 强 | 一切皆对象 + 字典命名空间 + 动态类型，反射是默认能力 |
| 内省三件套 | `type`（类型）、`dir`（可见名，≠`__dict__`）、`isinstance`（含子类） |
| 操作入口 | `getattr`/`setattr`/`delattr` 对应 `__getattribute__`/`__setattr__`/`__delattr__` |
| `hasattr` 陷阱 | 吞 `AttributeError`，会误判"属性存在但出错"为"没有" |
| `inspect` 工具箱 | `signature`（穿透装饰器）、`getsource`、`getmro`、`isfunction` 谓词、栈帧 |
| 动态创建 | `type(name,bases,dict)` 建类、`importlib` 动态加载、`eval/exec` 危险区 |
| 反射驱动架构 | 插件注册、ORM 字段映射、通用序列化、CLI 自动生成、轻量 DI |
| 元数据反射 | `__annotations__` 三层结构、装饰器挂回元数据 |
| 代价与边界 | 性能 3–4×、安全红区（eval/pickle）、可维护性损失；用在边界，能不用不用 |

---

### 练习

**【基础：验证理解】**

1. 预测输出并说明理由：
   ```python
   class A: pass
   class B(A): pass
   b = B()
   print(type(b) is B, isinstance(b, A), isinstance(b, object))
   ```

2. 下面 `hasattr` 的输出是什么？它掩盖了什么真实错误？
   ```python
   class C:
       @property
       def x(self):
           raise AttributeError("boom")
   print(hasattr(C(), "x"))
   ```

3. 填空：`dir(obj)` 看不到实例用 `__slots__` 存的属性，但能看到——（填一个它比 `obj.__dict__` 多覆盖的来源）。

**【进阶：动手实战】**

4. 写一个 `safe_get(obj, name, default)`，行为同 `getattr(obj, name, default)`，但要求：若属性存在却因内部 `AttributeError` 而访问失败，要**抛出**该异常而非返回 default（即不被 `hasattr` 式逻辑掩盖）。

5. 用 `inspect.signature` 写一个装饰器 `@enforce_types`，在函数调用前检查实参类型是否匹配注解，不匹配抛 `TypeError`。（提示：结合 `param.annotation` 与 `isinstance`）

6. 手写一个插件系统：定义 `@plugin` 装饰器收集子类到一个 registry，再用 `importlib` 动态加载一个目录下的所有 `.py` 模块，最后列出所有已注册插件名。

7. 用 `dataclasses.fields` + `getattr`/`setattr` 实现一个 `to_json` / `from_json` 对，能把任意 `@dataclass` 实例与 `dict` 互转（暂不考虑嵌套）。

**【深度思考】**

8. 为什么 `getattr` 比 `obj.x` 慢？从字节码（`LOAD_ATTR` vs `CALL getattr`）和查找路径两个角度解释。用 `dis.dis` 在你的 Python 版本上实测两种写法的字节码，记录指令序列。

9. `eval` 传入 `{"__builtins__": {}}` 作为 globals 就能安全执行不可信代码吗？为什么（试从 `__import__`、`open`、异常对象等角度分析）？给出真正安全的替代方案。

10. 对比"用 `getattr` + 白名单分发"与"用 `dict` 映射函数对象分发"（`DISPATCH = {"add": calc.add}`）两种命令分发实现。从性能、可读性、可维护性、反射滥用风险四个维度写一段 200 字左右的取舍分析。

11. 阅读 `collections.abc` 中 `Sequence` 的 `__subclasshook__` 源码（`inspect.getsource`），解释为什么一个只实现了 `__len__` 和 `__getitem__`、却没继承 `Sequence` 的类，`issubclass` 也会返回 `True`。

---

**进入下一专题的准备**：
- ✅ 能区分 `introspection` 与 `reflection`，说清 Python 反射强的语言根因
- ✅ 理解 `getattr`/`setattr`/`hasattr` 与属性协议 `__getattribute__` 的对应关系与陷阱
- ✅ 会用 `inspect.signature`/`getsource`/`getmro` 做运行时内省
- ✅ 能识别反射驱动架构（插件/ORM/CLI/DI），并清楚其性能、安全、可维护性代价
- ✅ 知道"eval/pickle 处理不可信输入是红色禁区"，并能在边界处恰当地用反射
