# 第12章 元编程

> **学习目标**：建立"**代码也是数据**"的元编程心智——掌握装饰器（函数级）、描述符/属性协议（类级）、元类（类创建级）三层能力；能读懂 `@dataclass`/`@property`/`classmethod` 这些"魔法"背后的实现；会用元编程写类型校验、插件注册表、声明式 API；并清楚**什么时候该用、什么时候该躲**。

---

第 6 章教过"函数是一等公民"，第 7 章教过"类与对象模型"——本章把这两件事推向极致：**用代码来写代码**。`@property` 为什么能让方法像属性？`@dataclass` 为什么能自动生成 `__init__`？`classmethod` 的第一个参数为什么是类？这些"魔法"不是解释器的特殊照顾，而是**普通 Python 代码实现的普通对象**——读懂它们，你就从"用 Python 编程"升级到"编程 Python 本身"。

本章与前面章节的关系：第 6 章 6.5 用装饰器做了"先用起来"的示例，本章**细讲机制**（语法糖展开、wraps、工厂）；第 7 章 7.2 的方法绑定、7.3 的属性查找链、7.7 的特殊方法协议，本章深入描述符与属性协议的**完整查找路径**；第 10 章的 import 钩子与模块 `__getattr__`（PEP 562）、第 14 章的 pytest AST 改写，都是元编程的生产级应用；第 13 章的 `functools.wraps`/`lru_cache` 内部是装饰器的标准实现。**风险提示**：元编程是把双刃剑——本章最后（12.9.4）会明确"能不用就不用"的使用边界。

---

## 12.1 元编程全景

### 12.1.1 什么是元编程：代码操作代码

**元编程（metaprogramming）**：程序**在运行时创建、修改或操纵代码本身**。普通编程写"业务逻辑"，元编程写"制造逻辑的机器"。

```python
# 普通编程：写逻辑
def add(a, b):
    return a + b

# 元编程：写"制造函数的代码"
def make_adder(n):
    def adder(x):            # 运行时创建函数
        return x + n
    return adder

add5 = make_adder(5)         # add5 是在运行时被"造"出来的
add5(10)                     # 15
```

Python 是**动态语言**（类型在运行时检查、对象可随时改），这让元编程天然容易——没有编译期的"类/函数不可变"限制。对比：

| 语言 | 元编程能力 | 形式 |
|------|-----------|------|
| Python | ★★★ 极强 | 装饰器/描述符/元类/动态属性 |
| Java | ★★ 受限 | 注解（编译期）+ 反射（运行时，慢且啰嗦） |
| Ruby | ★★★ 极强 | open class / method_missing |
| C++ | ★★ 编译期 | 模板元编程（编译期计算） |
| Rust | ★ 编译期 | 宏（编译期展开） |

> **设计哲学**：Python 的元编程哲学是"**显式优于隐式**"——`@decorator` 语法糖把"包装函数"写得显眼；元类虽然强大但要求"想清楚再用"。对比 Ruby 的 `method_missing`（几乎无限制的隐式魔法），Python 更克制：每个魔法点（`__getattr__`/`__setattr__`）都是**显式声明的协议方法**。

### 12.1.2 元编程的三层能力地图

Python 的元编程能力分三层，**层级越高、威力越大、越该谨慎**：

| 层 | 作用对象 | 核心工具 | 解决什么 | 复杂度 |
|----|---------|---------|---------|--------|
| **第一层** | 函数 | 装饰器（`@deco`） | 包装/增强函数行为 | 低 |
| **第二层** | 类成员 | 描述符（`__get__`/`__set__`）、属性协议（`__getattr__` 等） | 定制属性访问 | 中 |
| **第三层** | 类本身 | 元类（`type` 子类）、`__init_subclass__` | 定制类的创建 | 高 |

```python
# 三层各看一眼（本章逐一展开）
# 第一层：装饰器 —— 包装函数
@timer
def work(): ...

# 第二层：描述符 —— 定制属性
class Celsius:
    def __get__(self, obj, objtype): ...

# 第三层：元类 —— 定制类创建
class Meta(type):
    def __new__(cls, name, bases, ns): ...
```

> **实战建议**：**从第一层开始用，能不用第三层就不用**。装饰器解决 80% 的"需要元编程"场景；描述符解决属性级定制；元类是"最后的手段"（标准库 `dataclass`/`Enum`/`ABC` 用元类是因为它们要接管类创建的完整过程）。**复杂度与威力成正比，与可读性成反比**——12.9.4 会给出边界判断。

### 12.1.3 与已有章节的回环

| 已有内容 | 本章深挖 |
|---------|---------|
| 第 6 章 6.5：装饰器示例（先用起来） | 12.2：语法糖展开、工厂、wraps、栈 |
| 第 7 章 7.2：方法绑定与描述符 | 12.3：描述符协议完整实现 |
| 第 7 章 7.3：属性查找链 | 12.4：`__getattribute__` 完整路径 |
| 第 7 章 7.7：特殊方法协议 | 12.6/12.7/12.8：`__call__`/`__new__`/`__reduce__` |
| 第 13 章：`functools.wraps`/`lru_cache` | 12.2：它们的内部实现 |
| 第 14 章：pytest AST 改写 | 12.9：元编程的生产级应用 |
| 第 10 章：模块 `__getattr__`（PEP 562） | 12.4.4：动态属性的模块级版本 |

---

## 12.2 装饰器深潜

### 12.2.1 装饰器本质：语法糖的完整展开

第 6 章 6.5 见过装饰器"怎么用"，现在看"它到底是什么"：

```python
# 装饰器定义：接收函数，返回函数（或其他可调用）
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter()-t0:.4f}s")
        return result
    return wrapper

# 用法 1：语法糖
@timer
def work(): ...

# 用法 2：手工等价 —— @timer 就是这一行的缩写！
def work(): ...
work = timer(work)
```

**完整等价**：

```python
@timer
def work(): ...
# ≡
def work(): ...
work = timer(work)          # 名字 work 重新绑定到 timer 的返回值
```

关键推论：

1. **`@deco` 是"赋值"，不是"声明"**——`work` 这个名字在装饰后指向 `wrapper`；
2. **装饰器返回值决定替换物**——`work` 被重绑成"装饰器返回的任何东西"，不限于函数：返回可调用实例（12.6）照样能调用（12.2.4 有完整示例）；甚至返回**不可调用对象也合法**——`@property` 返回的 property 描述符就不可调用（12.3）；当然，返回 `None` 则调用就崩；
3. 装饰器在**模块导入时**执行（定义后立即应用）——不是调用时。

```python
# ❌ 反模式：装饰器忘记返回
def bad_deco(func):
    func.extra = True       # 只加属性，不返回！

@bad_deco
def f(): ...
f()                          # TypeError: 'NoneType' object is not callable

# ✅ 想"只加属性不改行为"也必须返回原函数
def attr_deco(func):
    func.extra = True
    return func              # 返回原函数
```

> **🔑 机制洞察**：装饰器是"**定义期的赋值钩子**"——Python 在编译 `@deco` 时生成"调用 deco 并重新绑定"的字节码。它在模块导入时执行，所以装饰器内部的一切副作用（注册、打印、连接）都在导入时发生——这和第 10 章"import 有副作用"是同一原理。

#### 跨语言对比：装饰器 vs 注解 vs 反射

Python 的 `@decorator` 常被拿来和 Java 注解（Annotation）比较，但**本质完全不同**：

| | Python 装饰器 | Java 注解 | Java 反射 |
|---|---|---|---|
| 本质 | **代码**（函数调用） | **元数据**（标记） | **API**（运行时查询） |
| 执行时机 | 导入时**立即执行** | 不执行（只是标记） | 运行时按需调用 |
| 能力 | 替换/包装函数 | 只能被读取 | 读取/调用 |
| 示例 | `@timer` 真的包装函数 | `@Override` 只是标记 | `obj.getClass().getMethods()` |

```java
// Java 注解：本质是"贴标签"，要有人（框架）去读它才有意义
@Retryable(maxAttempts = 3)
public void fetch() { ... }
// 运行时：Spring 等框架用反射读取注解并生成代理——"框架做装饰器"
```

```python
# Python 装饰器：自己就是代码，不需要"框架去读"
@retry(times=3)
def fetch(): ...          # 装饰器本身就是实现！
```

> **设计哲学**：Java 的元编程是"**元数据 + 反射 + 框架**"三层分离（注解只声明，框架用反射解释）；Python 的元编程是"**代码即实现**"（装饰器直接执行逻辑）。Python 更直接，代价是"装饰器的副作用在导入时发生"（12.2.1 的机制）；Java 更可控，代价是"注解本身没有任何行为，全靠框架"。**Ruby 的 `method_missing`/open class** 比 Python 更激进（几乎无限制的运行时修改）；Python 在"强大"与"显式"之间取了中道。

### 12.2.2 装饰器工厂：带参数装饰器

`@timer` 用起来不能传参。`@retry(times=3)` 这种**带参数的装饰器**需要两层结构：

```python
import time

def retry(times=3, delay=0.1):
    """装饰器工厂：外层接收参数，内层接收函数。"""
    def decorator(func):              # 真正的装饰器
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise           # 最后一次：抛出原始异常
                    time.sleep(delay)   # 否则等待后重试
        return wrapper
    return decorator

@retry(times=3, delay=0.5)      # 先调 retry(3, 0.5) 得到 decorator，再装饰
def fetch(): ...

# 展开等价：
# def fetch(): ...
# decorator = retry(times=3, delay=0.5)
# fetch = decorator(fetch)
```

| 写法 | 结构 | 何时执行 |
|------|------|---------|
| `@deco` | 1 层（deco 收函数） | 导入时：`deco(f)` |
| `@deco(args)` | 2 层（外层收参数 → 内层收函数） | 导入时：`deco(args)(f)` |
| `@deco(a)(b)` | 任意表达式依次调用 | 导入时：`f = deco(a)(b)(f)` |

> **实战建议**：带参数装饰器的惯用命名——外层函数名即"装饰器名"（`retry`），内层常用 `decorator`/`wrapper` 的约定命名，可读性最佳。注意：`@retry`（不带括号）与 `@retry()`（带空括号）**不是一回事**——前者是"retry 直接收函数"（会因参数错位出错），后者是"先调用工厂"。设计装饰器时要决定支持哪种形态（多数支持 `@retry()`）。

### 12.2.3 functools.wraps 与元信息

第 13 章 13.4.4 会把 `wraps` 收入 functools 工具箱并标注"写装饰器必加"，这里先看它为什么必要：

```python
# 不 wraps 的后果
def timer(func):
    def wrapper(*args, **kwargs):
        """wrapper 的 docstring"""
        ...
    return wrapper

@timer
def work():
    """work 的 docstring"""

>>> work.__name__              # 丢失！变成了 wrapper
'wrapper'
>>> work.__doc__               # 丢失！变成了 wrapper 的
'wrapper 的 docstring'
>>> help(work)                 # 帮助文档全错
```

```python
# ✅ wraps 修复：复制元信息 + 保留 __wrapped__ 链
from functools import wraps

def timer(func):
    @wraps(func)               # 把 func 的 __name__/__doc__/__module__ 复制给 wrapper
    def wrapper(*args, **kwargs):
        ...
    return wrapper

>>> work.__name__
'work'
>>> work.__doc__
'work 的 docstring'
>>> work.__wrapped__           # wraps 额外设置的：指向原始函数
<function work at 0x...>
```

**`__wrapped__` 的价值**：`inspect.signature(work)` 能**穿透装饰器**拿到原始签名（`inspect.signature` 会沿 `__wrapped__` 链解析）——这对文档生成、类型检查、框架（如 Flask 路由）至关重要。

> **🔑 机制洞察**：`wraps` 本质是 `update_wrapper(wrapper, func)`——把 `func` 的 `__module__`/`__name__`/`__qualname__`/`__annotations__`/`__doc__`/`__dict__` 拷贝到 `wrapper`，再设 `__wrapped__ = func`。它解决的是"**装饰器让函数丢失身份**"——没有它，调试器、`help()`、pickle、测试（第 14 章的断言信息）都会引用错误的函数名。

### 12.2.4 类装饰器

装饰器不仅能装饰函数，还能装饰**类**——`@dataclass` 就是最著名的类装饰器：

```python
def add_repr(cls):
    """类装饰器：给类追加 __repr__"""
    def __repr__(self):
        return f"{cls.__name__}({self.__dict__!r})"
    cls.__repr__ = __repr__
    return cls                # 返回修改后的类（也可以返回全新类）

@add_repr
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

>>> Point(1, 2)
Point({'x': 1, 'y': 2})
```

**类装饰器的时机**：类**定义完成后**调用（此时类对象已创建）——它接收类、返回类。与元类（12.5）的分工：

| 方式 | 时机 | 能力 |
|------|------|------|
| 类装饰器 | 类创建**之后** | 修改类属性、追加方法、替换类 |
| 元类 | 类创建**过程中** | 拦截/修改命名空间、控制继承、改变创建流程 |

> **实战建议**：**能类装饰器就不元类**——类装饰器更简单、更易读（`@dataclass` 就是"类装饰器 + 内省注解"实现的，没有用元类！）。标准库 `dataclasses`、`functools.total_ordering`、`enum` 的 `@unique`/`@verify` 都是类装饰器方案。元类只在"需要接管类创建过程"时才上（12.5.5）。

#### 别混淆：装饰类 vs 用类实现的装饰器

上面讲的是"**装饰类**"的装饰器（收类、返类）。另一个正交概念是"**用类实现装饰器**"——它利用的正是 12.2.1 推论 2："替换物只要是可调用对象即可"，而实现了 `__call__` 的实例正是可调用对象（12.6）。陷阱清单里"每实例状态用可调用对象"（12.2.6）指的就是这种形态：

```python
import time
from functools import wraps

class Timed:
    """用类实现的计时装饰器：__init__ 收函数，__call__ 代为调用。"""
    def __init__(self, func):
        wraps(func)(self)          # wraps 也能用在实例上：元信息复制到 self
        self.func = func
        self.calls = 0             # 状态在实例里：显式、可直接读写
    def __call__(self, *args, **kwargs):
        self.calls += 1
        t0 = time.perf_counter()
        result = self.func(*args, **kwargs)
        print(f"{self.func.__name__} #{self.calls} took {time.perf_counter()-t0:.4f}s")
        return result

@Timed                            # ≡ slow = Timed(slow)：slow 现在是 Timed 实例！
def slow():
    time.sleep(0.01)

>>> slow()                        # 调用实例 → 触发 __call__
slow #1 took 0.0104s
>>> slow.calls                    # 状态可直接读取——闭包版做不到
1
>>> isinstance(slow, Timed)       # 可类型判断——闭包版同样做不到
True
```

两种形态的取舍：

| | 函数式 wrapper | 类实现（`__call__`） |
|---|---|---|
| 样板代码 | 少（一层闭包） | 多（`__init__` + `__call__`） |
| 携带状态 | 闭包变量（隐式、外部读不到） | 实例属性（显式、可读写、可重置） |
| 类型判断 | 不便 | `isinstance(x, Timed)` |
| 适用 | 无状态/轻状态的横切逻辑 | 需要管理状态或配置的装饰器 |

> **🔑 机制闭环**：标准库里 `property` 本身就是"类当装饰器用"的活例子——且它返回的实例**不可调用**（是描述符，12.3.3），证明装饰器的返回值连 Callable 都不必是。至此三种形态凑齐完整图景：**函数返回函数 → 类返回可调用实例 → 类返回描述符**。

### 12.2.5 装饰器栈与顺序

多个装饰器叠加是**洋葱模型**：

```python
@a
@b
def f(): ...
# ≡
# f = a(b(f))      —— 先应用最下面的 b，再应用 a
```

```python
def a(func):
    print(f"a decorating {func.__name__}")
    def wrapper(): print("a before"); func(); print("a after")
    return wrapper

def b(func):
    print(f"b decorating {func.__name__}")
    def wrapper(): print("b before"); func(); print("b after")
    return wrapper

@a
@b
def f(): print("f")

f()
# 应用顺序（定义时）：先打印 b decorating f，再打印 a decorating wrapper
#                    （a 拿到的是 b 的 wrapper，所以 func.__name__ 是 "wrapper"）
# 调用顺序（运行时）：a before → b before → f → b after → a after
```

> **⚠️ 陷阱**：装饰器顺序在"依赖行为"的装饰器上很重要——如 `@app.route`（Flask 路由注册）与 `@login_required`（权限）：**注册装饰器通常放最外层**（先被应用，先登记）。再看缓存与日志的顺序：`@lru_cache` 在外、日志在内 → 命中缓存时**不打印日志**；反过来则**每次调用都打印**——哪个正确取决于语义，放错就是 bug。
>
> **版本注意**：3.9–3.12 曾支持 `@classmethod` 包裹 `@property` 实现"类级属性"（3.11 起文档标记弃用，3.13 移除）；如今**两种叠加顺序都无法实现类级属性**——`@property` 在外会 `TypeError: 'classmethod' object is not callable`，`@classmethod` 在外则 `property` 被静默忽略。

### 12.2.6 实战模式大全（🔑 实战模式）

五个高频装饰器模式：

```python
# 1. 注册表模式：把函数登记进全局表（插件系统基础）
REGISTRY = {}

def register(name=None):
    def decorator(func):
        REGISTRY[name or func.__name__] = func
        return func            # 保持原函数不变
    return decorator

@register("add")
def add(a, b): return a + b
# REGISTRY = {'add': <function add>}

# 2. 计时/性能（lru_cache 的兄弟）
def timed(func): ...

# 3. 重试（12.2.2 已实现）

# 4. 权限/前置校验
def require_admin(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            raise PermissionError("admin only")
        return func(*args, **kwargs)
    return wrapper

# 5. 缓存（functools.lru_cache 的手写简化版）
def memoize(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper
```

```python
# 标准库 lru_cache 的装饰器形态（13.4.2 详述）：
# @lru_cache(maxsize=128)  ← 装饰器工厂
# 内部：_lru_cache_wrapper（C 实现）+ OrderedDict LRU（move_to_end 见 13.2.2）
```

> **实战建议**：装饰器模式的选择表——**无参数注册**用 `@register`（单层）；**带参数**用工厂（双层）；**需要状态**用闭包字典或可调用对象（12.6）；**需要保留签名**必加 `@wraps`。本节示例为聚焦模式本身省略了 `@wraps`，实际项目中必加。装饰器是"横切关注点"（日志/权限/缓存/重试）的标准载体——它们不该散落在业务函数内部，装饰器把它们提升为**可组合的声明**。

#### 装饰器陷阱清单

| 陷阱 | 现象 | 解药 |
|------|------|------|
| 忘记 `return` | `TypeError: 'NoneType' object is not callable` | 装饰器必须返回函数/可调用 |
| 忘加 `@wraps` | `__name__`/`__doc__` 丢失；help/调试/pickle 全乱 | `from functools import wraps` |
| `@deco` vs `@deco()` 混淆 | 参数错位、运行时才炸 | 明确装饰器形态并写文档 |
| 装饰器内捕获异常吞掉 | 函数"假成功" | 重试装饰器最后一次 `raise` |
| 装饰器顺序错误 | 注册/权限失效 | 洋葱模型：从下往上应用 |
| 共享可变状态 | 装饰器闭包里的 dict/list 被并发污染（第 11 章） | 每实例状态用可调用对象/`threading.local` |
| 装饰器副作用在导入时执行 | 导入慢、导入即注册 | 明确"导入时 vs 调用时"的设计 |

```python
# 陷阱 6 的实例：装饰器闭包状态与并发（衔接第 11 章）
def counter():
    state = {"n": 0}
    def deco(func):
        def wrapper(*args, **kwargs):
            state["n"] += 1        # ⚠️ 多线程下不是原子的（11.2.2）！
            return func(*args, **kwargs)
        return wrapper
    return deco
```

> **实战建议**：装饰器的"隐藏状态"（闭包变量）是并发 bug 的温床——需要计数的装饰器要么加锁（11.2.3），要么用可调用对象（12.6，状态在实例里可显式管理）。**装饰器是"横切关注点"，它的状态也是"横切状态"**——要像全局状态一样谨慎（第 10 章 10.4.2 的模块单例陷阱同源）。

---

## 12.3 描述符协议

第 7 章 7.2 提过"方法三兄弟与描述符绑定"，本章把描述符协议讲透——它是 `property`/`classmethod`/`staticmethod`/`__slots__` 的共同底层。

### 12.3.1 描述符是什么：__get__ / __set__ / __delete__

**描述符（descriptor）**：实现了 `__get__`（可选 `__set__`/`__delete__`）的类，其实例**作为另一个类的类属性**时，属性访问会被"拦截"：

```python
class Positive:                      # 描述符类
    def __init__(self):
        self.data = {}
    def __get__(self, obj, objtype=None):
        print("__get__ 被调用")
        return self.data[obj]
    def __set__(self, obj, value):
        print("__set__ 被调用")
        if value < 0:
            raise ValueError("must be positive")
        self.data[obj] = value

class Order:
    price = Positive()               # 描述符实例作为类属性！

o = Order()
o.price = 10          # → __set__(Positive实例, o, 10)
o.price               # → __get__(Positive实例, o, Order) → 10
o.price = -5          # ValueError: must be positive（校验生效！）
```

**协议签名**：

| 方法 | 签名 | 触发时机 |
|------|------|---------|
| `__get__` | `(self, obj, objtype=None)` | `obj.attr` 或 `cls.attr` |
| `__set__` | `(self, obj, value)` | `obj.attr = value` |
| `__delete__` | `(self, obj)` | `del obj.attr` |

`obj.attr` 的访问路径（简化，完整版见 12.4.1）：在 `type(obj)` 的 MRO 上找 `attr` → **如果找到的是描述符实例** → 调用 `__get__`。

> **🔑 机制洞察**：描述符是 Python"**把属性访问变成方法调用**"的机制——`o.price` 表面是字段访问，实际执行的是描述符的 `__get__` 方法。这让你能**用字段的语法、获得方法的控制力**（校验、计算、缓存、代理）。所有"魔法属性"（`property`/绑定方法/`__slots__` 槽位）都是描述符。

### 12.3.2 数据描述符 vs 非数据描述符（🔑 机制洞察）

按是否实现 `__set__`，描述符分两类——**优先级完全不同**：

```python
class DataDesc:                      # 数据描述符：有 __set__
    def __get__(self, obj, objtype=None): return "data get"
    def __set__(self, obj, value): ...

class NonDataDesc:                   # 非数据描述符：只有 __get__
    def __get__(self, obj, objtype=None): return "nondata get"

class C:
    d = DataDesc()
    n = NonDataDesc()

c = C()
c.d = "instance value"               # 数据描述符优先：__set__ 被调用，实例 dict 没写入
c.d                                  # 'data get'（不是 'instance value'！）

c.n = "instance value"               # 非数据描述符：实例 dict 优先 → 遮蔽描述符
c.n                                  # 'instance value'
del c.n                              # 删除实例属性 → 恢复描述符
c.n                                  # 'nondata get'
```

**优先级规则**（属性查找中的描述符部分）：

```
数据描述符 > 实例 __dict__ > 非数据描述符
```

**为什么方法是非数据描述符**——这是 Python 最优雅的设计之一：

```python
class C:
    def method(self): return "hi"

c = C()
# c.method 每次访问 → __get__(method, c, C) → 返回绑定方法（新对象）
>>> c.method is c.method
False          # 每次绑定都是新对象！

# 非数据描述符 → 实例 dict 优先 → 你可以"遮蔽"方法！
c.method = "not a method"
>>> c.method
'not a method'   # ✅ 合法！方法可以被实例属性遮蔽
>>> C.method     # 类属性访问仍走描述符
<function C.method at ...>
```

> **🔑 设计哲学**：方法选"非数据描述符"是刻意的——**允许实例属性遮蔽方法**（灵活，如给实例"定制行为"），且绑定方法的每次创建（`__get__` 返回新 `MethodType`）开销极小。而 `property`/`__slots__` 槽位选"数据描述符"是因为**它们必须优先于实例 dict**（否则 `obj.x = ...` 会绕过校验/槽位）。选择描述符类型 = 选择"谁优先"。

### 12.3.3 property 的实现

`property` 就是一个**内置的数据描述符**——用 `fget`/`fset`/`fdel` 三个函数实现 `__get__`/`__set__`/`__delete__`：

```python
class property:
    """property 的 Python 等价实现（示意）"""
    def __init__(self, fget=None, fset=None, fdel=None):
        self.fget, self.fset, self.fdel = fget, fset, fdel
    def __get__(self, obj, objtype=None):
        if obj is None:            # 类访问：cls.x → 返回 property 对象本身（或 fget）
            return self
        return self.fget(obj)
    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)
    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)
    def setter(self, fset):        # @x.setter 装饰器
        self.fset = fset
        return self
```

```python
# @property 语法如何工作（第 7 章用过，现在懂原理了）
class Circle:
    def __init__(self, r): self._r = r

    @property                       # radius = property(radius)  ← fget
    def radius(self): return self._r

    @radius.setter                  # radius = radius.setter(radius)  ← 追加 fset
    def radius(self, value):
        if value < 0: raise ValueError("radius must be >= 0")
        self._r = value

c = Circle(5)
c.radius          # → property.__get__ → radius(self) → 5
c.radius = 10     # → property.__set__ → setter 校验
c.radius = -1     # ValueError
```

> **实战建议**：`property` 的使用准则——**先用普通属性，需要"计算/校验/只读"时再升级为 property**（不要一上来就写 getter/setter，Python 不是 Java）。`@property` 的只读用法（只有 fget）是"对外只读、对内可写"的标准封装：外部 `obj.radius` 读、内部 `self._radius` 写。

### 12.3.4 classmethod / staticmethod 的描述符本质

```python
class C:
    def instance_method(self): ...        # 函数（非数据描述符）
    @classmethod
    def class_method(cls): ...            # 绑定 cls
    @staticmethod
    def static_method(): ...              # 不绑定

c = C()
# 三种访问方式 → __get__ 返回什么：
c.instance_method     # <bound method C.instance_method of <C object>>  （绑定实例）
c.class_method        # <bound method C.class_method of <class 'C'>>    （绑定类！）
c.static_method       # <function C.static_method at ...>                （原样函数）
C.instance_method     # <function C.instance_method>                     （类访问：普通函数）
C.class_method        # <bound method C.class_method of <class 'C'>>
C.static_method       # <function C.static_method>
```

**实现视角**（`classmethod` 与 `staticmethod` 都是描述符，`__get__` 返回不同东西）：

```python
class classmethod:
    """classmethod 的等价实现（示意）"""
    def __init__(self, func): self.__func__ = func
    def __get__(self, obj, objtype=None):
        # 无论从实例还是类访问，都绑定到【类】（objtype）
        return MethodType(self.__func__, objtype)      # 绑定 cls

class staticmethod:
    """staticmethod 的等价实现（示意）"""
    def __init__(self, func): self.__func__ = func
    def __get__(self, obj, objtype=None):
        return self.__func__                            # 原样返回

class C:
    @classmethod
    def cm(cls): ...            # cm = classmethod(cm)  ← 描述符实例
```

> **🔑 机制洞察**：`@classmethod`/`@staticmethod` 本质是"**用描述符改变绑定行为**"——`__get__` 返回什么，属性访问就得到什么。这解释了：为什么 `classmethod` 第一个参数是类（`__get__` 绑定了 `objtype`）；为什么 `staticmethod` 连类都不绑（`__get__` 原样返回函数）。**方法三兄弟（实例方法/类方法/静态方法）的差异 = 三个描述符 `__get__` 的返回值差异**——没有魔法，只有协议。

### 12.3.5 __slots__ 与描述符

第 7 章 7.6 讲过 `__slots__` 省内存（去掉 `__dict__`），现在揭示它的实现：**每个槽位都是一个描述符**（`member_descriptor`）：

```python
class Point:
    __slots__ = ("x", "y")       # 每个槽位 → 一个描述符

>>> p = Point()
>>> p.x = 1                      # → member_descriptor.__set__
>>> Point.x
<member 'x' of 'Point' objects>  # ← 就是描述符！
```

```python
# 内存实测（第 7 章结论的数据支撑，🔑 性能数据）
>>> import sys
>>> class WithDict: pass
>>> class WithSlots: __slots__ = ("x", "y")
>>> a = WithDict(); a.x = a.y = 1
>>> b = WithSlots(); b.x = b.y = 1
>>> sys.getsizeof(a)     # 含 __dict__ 的对象
56
>>> sys.getsizeof(b)     # 槽位描述符 + 无 dict
48
# 加上 __dict__ 本身的占用（约 120+ 字节），百万实例差距可达 100+ MB
```

> **⚠️ 陷阱**：`__slots__` 是"数据描述符"——所以**实例 dict 无法遮蔽槽位**（12.3.2 的优先级）；`__slots__` 与继承：**父类有 `__slots__` 而子类没有 → 子类重新获得 `__dict__`**（槽位只对本类生效）；需要动态属性时别用 `__slots__`（它禁止 `obj.attr = x` 对新名字赋值，除非在槽位里加 `__dict__`）。

### 12.3.6 描述符实战

```python
# 实战 1：类型校验属性（数据描述符 + 工厂）
class Typed:
    def __init__(self, name, expected_type):
        self.name, self.expected_type = name, expected_type
        self.data = {}
    def __get__(self, obj, objtype=None):
        return self.data[obj]
    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(f"{self.name} must be {self.expected_type.__name__}, got {type(value).__name__}")
        self.data[obj] = value

class Person:
    name = Typed("name", str)
    age = Typed("age", int)

p = Person()
p.name = "Alice"       # ✅
p.age = "thirty"       # TypeError: age must be int, got str
```

```python
# 实战 2：lazy property（首次访问才计算，结果缓存）
class lazy_property:
    def __init__(self, func): self.func = func
    def __get__(self, obj, objtype=None):
        if obj is None: return self
        value = self.func(obj)               # 计算
        obj.__dict__[self.func.__name__] = value   # 写入实例 dict（缓存）
        return value
    def __set__(self, obj, value):
        raise AttributeError("read-only")    # 数据描述符：防止覆盖

class Report:
    def __init__(self, data): self.data = data
    @lazy_property
    def summary(self):                       # 只算一次！
        print("computing...")
        return f"sum={sum(self.data)}"

r = Report([1, 2, 3])
r.summary      # computing... sum=6（计算一次）
r.summary      # 6（从实例 dict 缓存取——lazy_property 是非数据描述符的变体）
```

> **🔑 机制洞察**：`lazy_property` 利用了 12.3.2 的优先级——**非数据描述符 < 实例 dict**：首次访问走描述符计算，然后把结果写进 `obj.__dict__`；之后实例 dict 命中，**描述符不再被调用**（缓存生效）。这个"写入实例 dict 遮蔽描述符"的技巧是惰性属性的标准实现（很多框架如 Django 的 `cached_property` 就是它）。

---

## 12.4 属性访问协议深潜

第 7 章 7.3 画过属性查找链，本节给出**完整路径**（含描述符优先级与兜底钩子）。

### 12.4.1 属性查找完整路径（🔑 协议机制）

`obj.attr` 的执行由 `type(obj).__getattribute__`（`object.__getattribute__`）驱动，完整路径：

```
obj.attr
 1. __getattribute__(obj, "attr")            ← 总入口（一般不改它）
 2. 在 type(obj) 的 MRO 上找 "attr"
    → 找到？它是数据描述符（有 __set__）？
       是 → 调 desc.__get__(obj, type(obj))，返回        ★ 数据描述符最高优先
 3. 查 obj.__dict__（实例命名空间）
    → 命中 → 返回                                              ★ 实例 dict 第二
 4. 再沿 MRO 找（这次找普通属性/非数据描述符）
    → 找到非数据描述符 → desc.__get__(obj, type(obj))
    → 找到普通值（函数/字段）→ 返回
 5. 都没找到 → 调 __getattr__(obj, "attr")   ← 兜底钩子
    → 它抛 AttributeError 或返回值
```

```python
class Demo:
    def __init__(self):
        self.instance_attr = "from dict"
    def method(self): ...                    # 非数据描述符（函数）

d = Demo()
d.instance_attr       # 路径：MRO 无 → 实例 dict 命中 → 'from dict'
d.method              # 路径：MRO 找到函数（非数据描述符）→ __get__ → 绑定方法
d.nonexistent         # 路径：全没找到 → __getattr__ → 默认抛 AttributeError
```

> **🔑 机制洞察**：这条路径解释了所有"属性魔法"——`property` 在第 2 步拦截（数据描述符）、实例 dict 在第 3 步、方法在第 4 步绑定、`__getattr__` 在第 5 步兜底。**改任何一个钩子（`__getattr__`/`__setattr__`/描述符）都是在定制这条路径的某个环节**。

### 12.4.2 __getattr__ vs __getattribute__

两个钩子名字像、作用差很多：

| | `__getattr__(self, name)` | `__getattribute__(self, name)` |
|---|---|---|
| 触发时机 | **查找失败后**兜底 | **每次属性访问**（最先调用） |
| 频率 | 只在缺失时 | 每次 |
| 默认行为 | 抛 `AttributeError` | 走完整查找路径 |
| 用途 | 动态属性、代理、兼容旧 API | 拦截所有访问（审计、只读） |

```python
# __getattr__：动态属性（"计算出来的属性"）
class Config:
    def __init__(self): self._data = {"host": "localhost", "port": 5432}
    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"no config {name}")

cfg = Config()
cfg.host          # 'localhost'（没有这个属性！是 __getattr__ 算出来的）
```

```python
# __getattribute__：拦截一切（含已存在的属性）
class ReadOnly:
    def __init__(self, value):
        object.__setattr__(self, "_value", value)     # ⚠️ 见下方递归陷阱
    def __getattribute__(self, name):
        print(f"accessing {name}")
        return object.__getattribute__(self, name)    # 必须走 object 的！

r = ReadOnly(42)
r._value          # accessing _value → 42（每次都打印）
```

> **⚠️ 陷阱（`__getattribute__` 递归）**：在 `__getattribute__` 里写 `self.name` 会**无限递归**——因为 `self.name` 又触发 `__getattribute__`！必须显式调用 `object.__getattribute__(self, name)`（或 `super().__getattribute__`）绕过自己。同理 `__setattr__` 里写 `self.x = ...` 也是递归——用 `object.__setattr__`。

### 12.4.3 __setattr__ / __delattr__

```python
# 对象冻结：赋值/删除全部拦截
class Frozen:
    def __setattr__(self, name, value):
        raise AttributeError("frozen object")
    def __delattr__(self, name):
        raise AttributeError("frozen object")

f = Frozen()
f.x = 1            # AttributeError
```

```python
# 属性改写拦截（如强制统一存储）
class Normalized:
    def __setattr__(self, name, value):
        object.__setattr__(self, name, str(value).lower())   # 全部转小写

n = Normalized()
n.name = "Alice"   # 存的是 'alice'
n.name
'alice'
```

> **⚠️ 陷阱**：`__setattr__` 里所有赋值都走它——包括 `__init__` 里的 `self.x = ...`。所以"在 `__init__` 里想直接写原始值"也得用 `object.__setattr__`。**改写 `__setattr__` 要非常小心**：它影响对象的一切赋值（比 `__getattribute__` 更容易误伤）。

### 12.4.4 动态属性工程应用

```python
# 代理模式：__getattr__ 转发到内部对象（装饰器/API 包装）
class Proxy:
    def __init__(self, target):
        self._target = target
    def __getattr__(self, name):
        return getattr(self._target, name)      # 转发

class Service:
    def run(self): return "running"

p = Proxy(Service())
p.run()                # 'running'（Proxy 没有 run，转发给 Service）
```

```python
# 模块级 __getattr__（PEP 562，第 10 章 10.4.1 细讲）：动态模块属性
# 这是"对象级 __getattr__"的模块版，实现延迟加载/弃用垫片
```

> **实战建议**：`__getattr__` 的工程用途三件套——**代理转发**（包装对象）、**动态属性**（配置/虚拟字段）、**兼容垫片**（旧 API 名 → 新实现）。但**慎用**：`__getattr__` 让"拼错的属性名"静默变成"动态返回"（或每个都要抛 AttributeError）——调试噩梦。规则：**动态属性只给"明确的一族名字"（如 `cfg.host`/`cfg.port` 对应 `_data` 字典），不要做成"万能属性"**。

---

## 12.5 元类：类的类

装饰器定制函数、描述符定制属性，**元类定制"类本身"的创建过程**——元编程的第三层，也是最后的手段。

### 12.5.1 type 是类的类

```python
>>> type(42)                    # 实例的类型
<class 'int'>
>>> type(int)                   # 类的类型 —— int 是 type 的实例！
<class 'type'>
>>> type(type)                  # type 的类型是自己（自指）
<class 'type'>
>>> type(Point)                 # 我们写的类也是 type 的实例
<class 'type'>
```

**一切类都是 `type` 的实例**（包括 `type` 自己）。`type` 就是"元类"——**类的类**。`class` 语句的本质是调用 `type`：

```python
# class A: 是语法糖，等价于：
A = type("A", (), {})                     # 名字、基类、命名空间

# 等价演示：
>>> Point = type("Point", (), {"x": 1})   # 动态创建类！
>>> p = Point()
>>> p.x
1
```

> **🔑 机制洞察**：`type(name, bases, namespace)` 是"**运行时造类**"的 API——你可以在运行时根据数据动态创建类（工厂模式的高级形态）。`isinstance(obj, cls)` 检查 `type(obj)` 是不是 `cls` 或其子类；`issubclass(C, B)` 检查 C 的元类链。元类定制 = **替换"造类时的 type"**。

### 12.5.2 class 语句的执行流程（🔑 机制洞察）

```python
class Meta(type):                # 自定义元类 = type 的子类
    def __new__(mcls, name, bases, namespace):      # ① 创建类对象（分配）
        print(f"Meta.__new__ creating {name}")
        return super().__new__(mcls, name, bases, namespace)
    def __init__(cls, name, bases, namespace):      # ② 初始化类对象
        print(f"Meta.__init__ initializing {name}")
        super().__init__(name, bases, namespace)

class MyClass(metaclass=Meta):  # ③ 指定元类
    attr = 1
# 输出：Meta.__new__ creating MyClass
#       Meta.__init__ initializing MyClass
```

**class 语句的完整流程**：

```
class MyClass(Base, metaclass=Meta):
    attr = 1
 1. 执行类体代码（attr = 1 等）→ 收集进命名空间 namespace
 2. 确定元类：显式 metaclass= 优先，否则取基类的元类，否则 type
 3. 创建类对象：Meta.__new__(Meta, "MyClass", (Base,), namespace) → cls
 4. 初始化类对象：Meta.__init__(cls, "MyClass", (Base,), namespace)
 5. 绑定名字：MyClass = cls
```

**`__prepare__`（PEP 3115，3.0+）**：第 1 步之前的钩子——**定制类体代码的执行环境**：

```python
class Meta(type):
    def __prepare__(name, bases):        # 返回"类体代码的命名空间"
        print(f"preparing {name}")
        return {}                        # 默认 dict；可返回 OrderedDict/自定义映射

class WithMeta(metaclass=Meta):
    x = 1
# 输出：preparing WithMeta
```

> **🔑 机制洞察**：`__prepare__` 的意义——类体代码在**普通 dict** 里执行（无顺序保证，3.6 前）；`__prepare__` 让你换成 `OrderedDict`（保序：元类可知道字段声明顺序，ORM/`dataclass` 依赖它）。`__prepare__` → `__new__` → `__init__` 是类创建的三段钩子，分别控制"执行环境""创建""初始化"。

#### __prepare__ 实战：记录字段声明顺序

```python
from collections import OrderedDict

class Field:                        # 简单的字段标记
    def __init__(self, type_): self.type_ = type_

class OrderedMeta(type):
    @classmethod
    def __prepare__(mcls, name, bases):
        return OrderedDict()        # 类体在有序 dict 里执行 → 声明顺序保留

    def __new__(mcls, name, bases, namespace):
        # 从命名空间里按【声明顺序】提取字段
        cls = super().__new__(mcls, name, bases, dict(namespace))
        cls._field_order = [k for k, v in namespace.items() if isinstance(v, Field)]
        return cls

class User(metaclass=OrderedMeta):
    name = Field(str)
    age = Field(int)
    email = Field(str)

>>> User._field_order
['name', 'age', 'email']       # ✅ 声明顺序（普通 dict 无法保证）
```

> **🔑 机制洞察**：为什么 `__prepare__` 曾经如此重要——3.6 之前 dict 无序，字段顺序必须靠 `__prepare__` 的 `OrderedDict` 才能拿到（`dataclasses`/ORM 依赖"字段顺序"生成 `__init__` 参数序）。3.6+ 普通 dict 已保序，`__prepare__` 的价值变成"**自定义类体执行环境**"（如拦截赋值、统计使用）。读老框架源码（如旧版 `collections.namedtuple` 的元类实现）时，`__prepare__` 是理解"为什么能保序"的关键。

### 12.5.3 自定义元类基础

```python
# 元类能做什么：在类创建时修改/注入
class AutoAttr(type):
    def __new__(mcls, name, bases, namespace):
        namespace["created_by"] = f"auto-{name}"      # 注入类属性
        return super().__new__(mcls, name, bases, namespace)

class Service(metaclass=AutoAttr):
    pass

>>> Service.created_by
'auto-Service'
```

```python
# 校验：类必须有某属性
class RequireMethod(type):
    def __init__(cls, name, bases, namespace):
        if not hasattr(cls, "run"):
            raise TypeError(f"{name} must define run()")
        super().__init__(name, bases, namespace)

class Broken(metaclass=RequireMethod):   # TypeError！没有 run
    pass
```

**`__new__` vs `__init__` 在元类中的分工**（类比第 7 章实例的 `__new__`/`__init__`，12.7）：

| | `Meta.__new__` | `Meta.__init__` |
|---|---|---|
| 时机 | 先（创建类对象） | 后（初始化类对象） |
| 返回值 | 类对象（必须返回） | None |
| 用途 | 修改命名空间、换基类 | 类创建后的检查/附加 |

> **实战建议**：绝大多数元类只需要 `__init__`（类创建后的钩子）；要"改命名空间/换基类"才需要 `__new__`。**能 `__init_subclass__`（12.5.4）就别写元类**——它是 90% 元类需求的简单替代。

### 12.5.4 __init_subclass__（PEP 487，3.6+）

**PEP 487** 给了"子类创建时回调"的**非元类**方案：

```python
class Base:
    subclasses = []

    def __init_subclass__(cls, **kwargs):       # 每个子类创建时自动调用
        super().__init_subclass__(**kwargs)
        Base.subclasses.append(cls)

class A(Base): ...      # 创建 A 时 → Base.__init_subclass__(A)
class B(Base): ...      # 创建 B 时 → Base.__init_subclass__(B)

>>> Base.subclasses
[<class 'A'>, <class 'B'>]
```

**对比：`__init_subclass__` vs 元类**

| | `__init_subclass__` | 元类 |
|---|---|---|
| 语法 | 普通类方法（无魔法） | 需要 `metaclass=` |
| 触发 | 有子类创建时 | 类创建全程 |
| 能力 | 子类创建后的回调 | 拦截/修改创建过程 |
| 复杂度 | 低（推荐首选） | 高 |

```python
# 实战：自动注册 + 校验的现代写法（12.5.3 的元类版用 __init_subclass__ 重写）
class Plugin:
    registry = {}
    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "run"):
            raise TypeError(f"{cls.__name__} must define run()")
        Plugin.registry[name or cls.__name__] = cls

class JsonPlugin(Plugin, name="json"):      # 类关键字参数 → __init_subclass__
    def run(self): ...
```

> **版本注意**：`__init_subclass__` 是 3.6+（PEP 487）。**新代码优先用它而非元类**——标准库 `Enum`（3.11+）/`typing` 都在用它。注意子类的关键字参数（`name="json"`）会传给 `__init_subclass__`，但**必须调用 `super().__init_subclass__(**kwargs)`** 把剩余参数传下去，否则多层继承会报错。

### 12.5.5 元类实战（🔑 实战模式）

**实战 1：注册表元类**（自动登记所有子类——`__init_subclass__` 的元类版，用于"必须拦截创建"的场景）：

```python
class RegistryMeta(type):
    registry = {}
    def __new__(mcls, name, bases, namespace):
        cls = super().__new__(mcls, name, bases, namespace)
        if bases:                             # 排除基类本身
            RegistryMeta.registry[name] = cls
        return cls

class Handler(metaclass=RegistryMeta): ...    # 不进注册表（无基类）
class UserHandler(Handler): ...               # 自动登记
class OrderHandler(Handler): ...

>>> RegistryMeta.registry
{'UserHandler': <class ...>, 'OrderHandler': <class ...>}
```

**实战 2：单例元类**（让"用元类的类"自动单例——第 7 章配套设计模式的元类实现）：

```python
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):       # 拦截 cls() 调用
        if cls not in SingletonMeta._instances:
            SingletonMeta._instances[cls] = super().__call__(*args, **kwargs)
        return SingletonMeta._instances[cls]

class DB(metaclass=SingletonMeta): ...
>>> DB() is DB()
True                  # 单例成立（__call__ 拦截）
```

> **🔑 机制洞察**：单例元类的原理——`DB()` 会调用 `type(DB).__call__`（即元类的 `__call__`）——**拦截"类的调用"就是元类控制实例创建的方式**（`Meta.__call__` → `cls.__new__` → `cls.__init__`）。这比"在 `__new__` 里做单例"更彻底（连 `__init__` 都被控制）。

### 12.5.6 陷阱：元类冲突与继承

```python
# 陷阱 1：metaclass conflict —— 两个元类互不兼容
class MetaA(type): ...
class MetaB(type): ...
class A(metaclass=MetaA): ...
class B(metaclass=MetaB): ...

class C(A, B): ...        # TypeError: metaclass conflict!
# 解药：创建一个同时继承两个元类的元类
class MetaC(MetaA, MetaB): ...
class C(A, B, metaclass=MetaC): ...    # ✅
```

```python
# 陷阱 2：元类的类体访问 —— 类体里没有"类自己"
class Meta(type):
    def __new__(mcls, name, bases, ns):
        # ⚠️ 类体执行时，类还不存在——不能访问 cls/self 的东西
        return super().__new__(mcls, name, bases, ns)

# 陷阱 3：__slots__ 与元类 —— 元类上的 __slots__ 不影响其实例（类）
# 陷阱 4：动态类与 pickle —— 运行时创建的类没有稳定的 __module__/__qualname__，
#          pickle 无法重建（12.8.4 详述）
```

> **⚠️ 陷阱**：元类冲突是"多继承 + 多元类"的经典报错——规则：**一个继承体系只能有一条元类链**（子类元类必须是父类元类的子类）。元类还带来**隐式复杂度**（阅读者看不到"类为什么长这样"）——这也是 12.9.4"能不用就不用"的主要原因之一。

#### 标准库里的元类案例（学习元类的最佳教材）

元类不是"理论玩具"——你天天用的标准库就在用：

```python
# 案例 1：EnumMeta（enum 的元类）—— 枚举成员变成类的属性
import enum
>>> type(enum.Enum)
<class 'enum.EnumMeta'>          # Enum 的元类是 EnumMeta！
# 它做了什么：enum 类的每个成员（RED = 1）在类创建时变成
#             enum 实例（EnumMeta.__new__ 里转换成员类型）

# 案例 2：ABCMeta（abc 的元类）—— 抽象方法检查 + 注册虚拟子类
import abc
>>> type(abc.ABC)
<class 'abc.ABCMeta'>
# 它做了什么：__abstractmethods__ 追踪；register() 注册虚拟子类
#             （第 7 章 7.5 的 ABC 机制，元类是它的引擎）

# 案例 3：type 本身 —— 一切元类的父类
>>> type(type)
<class 'type'>
```

```python
# 用 inspect 拆解标准库元类（衔接第 14 章调试工具）
>>> import inspect, enum
>>> inspect.getsource(enum.EnumMeta)[:500]     # 直接读元类源码！
# 你会发现：EnumMeta.__new__ 里遍历命名空间、把成员包装成枚举实例、
#           设置 __members__ —— 全是普通 Python 代码
```

> **实战建议**：**读标准库元类源码是学元类的最快路径**——`enum`（成员转换）、`abc`（抽象检查）分别演示了元类的用途；而 `dataclasses`（第 7 章）**刻意不用元类**（用类装饰器）——对比两者设计差异，你就能领悟"何时该用元类、何时类装饰器足够"。读它们的 `__new__`/`__init__`，你会确认一个事实：**元类只是普通类，元编程只是普通代码**——"魔法"不存在，只有协议。

---

## 12.6 可调用对象：__call__

### 12.6.1 可调用协议：__call__ 与 callable()

`f(x)` 之所以能调用，是因为 `f` **实现了 `__call__` 协议**（或本身就是可调用类型）：

```python
>>> callable(len)          # 内置函数
True
>>> callable(int)          # 类（调用 = 创建实例）
True
>>> callable(42)           # 数字不可调用
False

class Adder:
    def __init__(self, n): self.n = n
    def __call__(self, x): return x + self.n   # 实现 __call__ → 实例可调用

>>> add5 = Adder(5)
>>> callable(add5)
True
>>> add5(10)               # 等价 add5.__call__(10)
15
```

**函数、方法、类、实现了 `__call__` 的实例——都是可调用对象**，`f(x)` 只是 `f.__call__(x)` 的语法糖。

### 12.6.2 可调用实例 vs 函数

可调用实例的独特价值：**带状态的可调用**（函数 + 属性）：

```python
# 有状态的计数器
class Counter:
    def __init__(self): self.count = 0
    def __call__(self):
        self.count += 1
        return self.count

c = Counter()
c(); c(); c()          # 1, 2, 3 —— 状态在实例里
c.count                # 3

# 对比闭包版（第 6 章）：可调用实例更"显式"（状态是属性）
def make_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter
```

> **实战建议**：**带配置的可调用**（`Processor(mode="fast")` 后 `p(data)`）是可调用实例的最佳场景——配置在 `__init__`、行为在 `__call__`。与"闭包携带配置"相比，可调用实例可 `isinstance` 判断、可序列化部分状态、可继承——工程上更规范。用它实现装饰器的完整形态见 12.2.4；`functools.partial`（13.4.1）则是"可调用对象"的标准库案例。

### 12.6.3 functools.partial 的实现视角

`partial` 对象是一个**可调用对象**（内部存 func/args/keywords，`__call__` 合并参数）：

```python
# partial 的等价实现（示意，实际是 C 实现的 _functools.partial）
class partial:
    def __init__(self, func, *args, **kwargs):
        self.func, self.args, self.keywords = func, args, kwargs
    def __call__(self, *args, **kwargs):
        merged = {**self.keywords, **kwargs}     # 关键字合并
        return self.func(*self.args, *args, **merged)

>>> from functools import partial
>>> pow2 = partial(pow, 2)        # pow2 = 可调用对象（预填 base=2）
>>> pow2(10)                      # 2 ** 10
1024
>>> pow2.func, pow2.args          # 状态可见、可调试
(<built-in function pow>, (2,))
```

> **🔑 机制洞察**：`partial` 是"**预填参数的可调用对象**"——它证明 Python 里"函数"与"带 `__call__` 的对象"在调用层面**完全等价**（`f(x)` 不关心 `f` 是函数还是对象）。这也是装饰器"返回可调用对象"能替换函数的原因（12.2.1）。

---

## 12.7 对象创建协议：__new__

第 7 章 7.1 讲过 `__new__`/`__init__` 的分工，本节深入"创建协议"的完整语义。

### 12.7.1 __new__ vs __init__

```python
class C:
    def __new__(cls, *args, **kwargs):       # ① 创建：分配内存，返回实例
        print("__new__")
        return super().__new__(cls)          # object.__new__ 分配
    def __init__(self, *args, **kwargs):     # ② 初始化：填充实例
        print("__init__")

c = C()
# 输出：__new__ → __init__
```

**分工与规则**：

| | `__new__` | `__init__` |
|---|---|---|
| 时机 | 先 | 后 |
| 职责 | **创建**（分配/返回实例） | **初始化**（填充状态） |
| 参数 | `cls`（类） | `self`（实例） |
| 返回值 | **必须返回实例**（返回 None 则无实例） | 必须返回 None |
| 触发 | `C()` 时 | `__new__` 返回**本类实例**时 |

```python
# 关键规则：__init__ 只有在 __new__ 返回【本类实例】时才被调用！
class C:
    def __new__(cls):
        return 42                    # 返回非本类对象
    def __init__(self):
        print("不会执行")

>>> C()
42                    # __init__ 没被调用！
```

> **🔑 机制洞察**：`__init__` 不是"必然第二步"——它是"`__new__` 返回了本类实例"时的自动回调。元类 `__call__`（12.5.5）正是控制"`__new__` 何时被调"的入口。**99% 的类只需要 `__init__`**；`__new__` 只在不可变对象、单例、池化时出现。

### 12.7.2 不可变对象的 __new__

**`tuple`/`str` 等不可变类型的子类，只能在 `__new__` 里设值**（`__init__` 无法修改）：

```python
class Point2D(tuple):
    def __new__(cls, x, y):
        return super().__new__(cls, (x, y))    # 值在 __new__ 里定死

    def __init__(self, x, y):
        # ⚠️ 即使写了 __init__ 也没用——tuple 已不可变
        pass

p = Point2D(3, 4)
p[0], p[1]            # (3, 4)
# p[0] = 5            # TypeError: 'Point2D' object does not support item assignment
```

> **⚠️ 陷阱**：给 `tuple`/`str` 子类写 `__init__` 想"初始化"是**无效的**——不可变对象的存储布局在 `__new__` 时就固定。这解释了为什么 `namedtuple`（第 13 章）用 `__new__` 生成（它在 `__new__` 里按字段打包）。

### 12.7.3 单例与池化的 __new__

```python
# 单例（__new__ 版）——每次 C() 返回同一实例
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

s1, s2 = Singleton(), Singleton()
s1 is s2              # True
```

```python
# 对象池（__new__ 版）——复用已释放的对象（性能优化，如连接池）
class Pooled:
    _pool = []
    def __new__(cls):
        if cls._pool:
            return cls._pool.pop()          # 复用
        return super().__new__(cls)
    def reset(self):
        type(self)._pool.append(self)       # 归还池子
```

> **实战建议**：单例的三种实现对比——**模块单例**（第 10 章，最简单）、**`__new__` 单例**（本类内部）、**元类单例**（12.5.5，全局拦截）。`__new__` 单例适合"类内部保证唯一"；注意它与 `__init__` 的交互（单例复用旧实例时 `__init__` **仍会被调用**——要在 `__init__` 里判断"是否首次"）。

### 12.7.4 __slots__ 内存优化回顾（衔接第 7 章）

12.3.5 已实测 `__slots__` 的内存收益。组合完整视角：

| 方式 | 内存/实例 | 特性 |
|------|----------|------|
| 普通类（有 `__dict__`） | 大（dict 开销） | 动态属性自由 |
| `__slots__`（无 dict） | 小（槽位描述符） | 固定属性、更快访问 |
| `__slots__` + `__dict__` | 中 | 固定 + 允许动态 |

```python
class Light:
    __slots__ = ("x", "y")      # 百万实例省 100+ MB（12.3.5 实测）
    def __init__(self, x, y):
        self.x, self.y = x, y
```

> **实战建议**：**大量实例的数据类（百万级）用 `__slots__`**；需要动态属性（`obj.new_attr = 1`）的类别用。`dataclass` 支持 `@dataclass(slots=True)`（3.10+）一键获得"数据类 + 槽位"。注意 `__slots__` 与 `weakref` 的冲突（`__weakref__` 要显式加入槽位）。

---

## 12.8 序列化协议：__reduce__ 与 pickle

第 9 章 9.6 讲过 pickle 的协议 0–5 与安全，本节讲**协议层的自定义钩子**——如何让"不常规"的对象也能序列化。

### 12.8.1 pickle 协议回顾（衔接第 9 章）

`pickle` 把 Python 对象变成字节流（第 9 章：协议 0–5、`PROTOCOL` 标志、安全警告）。**默认能 pickle 的**：基本类型、容器、模块级类实例；**不能的**：lambda、嵌套函数、锁、连接、生成器。

### 12.8.2 __reduce__：自定义序列化

`__reduce__` 是 pickle 的**自定义契约**：返回 `(callable, args)`，反序列化时执行 `callable(*args)` 重建对象：

```python
import threading, pickle

# 锁/连接等不可 pickle 的对象 → 自定义 __reduce__
class Connection:
    def __init__(self, url):
        self.url = url
        self.lock = threading.Lock()       # ⚠️ 锁不可 pickle
    def __reduce__(self):
        # 反序列化时：Connection(url) 重建（锁重新创建，状态由 __setstate__ 恢复）
        return (Connection, (self.url,))

c = Connection("mysql://db")
data = pickle.dumps(c)
c2 = pickle.loads(data)                    # ✅ 重建成功（锁是新的）
c2.url                                     # 'mysql://db'
```

**`__reduce__` 的完整契约**（可返回多元素元组）：

```python
def __reduce__(self):
    # 1 个元素：(callable)                       —— callable() 重建
    # 2 个元素：(callable, args)                 —— callable(*args) 重建
    # 3 个元素：+ state                          —— 状态由 __setstate__ 恢复
    # 4 个元素：+ listitems / 5 个元素：+ dictitems
    return (ClassToRebuild, (arg1, arg2), self.__dict__)
```

### 12.8.3 __getstate__ / __setstate__

更精细的控制——**序列化时导出什么状态**（排除缓存/不可序列化字段）：

```python
class Model:
    def __init__(self, data):
        self.data = data
        self._cache = {}                   # 缓存字段：不该序列化

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_cache", None)          # 排除缓存
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._cache = {}                   # 反序列化后重建缓存

m = Model([1, 2, 3])
m._cache["key"] = "value"
m2 = pickle.loads(pickle.dumps(m))
m2._cache                                 # {}（缓存被正确地丢弃重建）
```

| 钩子 | 时机 | 用途 |
|------|------|------|
| `__reduce__` | 序列化时 | 自定义"怎么重建"（构造器） |
| `__getstate__` | 序列化时 | 自定义"导出哪些状态" |
| `__setstate__` | 反序列化时 | 自定义"怎么恢复状态" |
| `__getnewargs__` | 反序列化时 | 传给 `__new__` 的参数（不可变对象） |

> **实战建议**：默认情况下**优先用 `__getstate__`/`__setstate__`**（只调状态、不碰构造逻辑）；`__reduce__` 用于"对象的重建需要特殊构造器"（如工厂函数创建的对象）。两者可以组合：`__reduce__` 定构造、`__getstate__` 定状态。

### 12.8.4 陷阱：不可 pickle 的元编程产物

元编程创造的"动态产物"往往是 pickle 的克星：

```python
# 陷阱 1：装饰器包装的函数（未 wraps）—— __name__ 变 wrapper，pickle 找不到原函数
@timer                                   # 没加 @wraps（12.2.3）
def work(): ...
pickle.dumps(work)                       # PicklingError！找不到 wrapper 的模块路径

# ✅ 修复：@wraps 保留 __name__/__module__/__qualname__ → pickle 能定位原函数

# 陷阱 2：运行时动态创建的类
Dynamic = type("Dynamic", (), {"x": 1})
obj = Dynamic()
pickle.dumps(obj)                        # PicklingError！Dynamic 没有模块级名字
# ✅ 修复：把类绑定到模块级名字（Dynamic = ... 在模块顶层）

# 陷阱 3：lambda / 闭包 / 局部函数
add = lambda a, b: a + b
pickle.dumps(add)                        # PicklingError！（lambda 无法按名定位）
```

> **⚠️ 陷阱**：pickle 按**模块路径 + 限定名**（`__module__`/`__qualname__`）定位可调用对象——**元编程产物（装饰器包装、动态类、lambda）通常没有稳定的可定位路径**。规则：**需要跨进程/缓存序列化的对象，避免 lambda 与动态类**；装饰器务必 `@wraps`。这和第 11 章进程池"target 必须可 pickle"（11.5.4）是同一个坑。

---

## 12.9 元编程实战工坊

三个完整案例把本章机制串起来——**看代码如何被代码制造**。

### 12.9.1 复刻 @dataclass（🔑 实战模式）

用**类装饰器 + 注解内省**（第 7 章的 dataclass 是标准实现，这里理解原理）：

```python
import inspect

def dataclass_lite(cls):
    """mini dataclass：从 __init__ 的注解收集字段，自动生成 __repr__/__eq__"""
    # 1. 收集字段（从 __init__ 签名注解——简化版用类注解也行）
    annotations = getattr(cls, "__annotations__", {})
    fields = list(annotations.keys())

    # 2. 若没定义 __init__，自动生成（这里要求显式 __init__ 带注解）
    if "__init__" not in cls.__dict__:
        params = ", ".join(f"{name}={getattr(cls, name, None)!r}" for name in fields)
        code = (f"def __init__(self, {', '.join(fields)}):\n"
                + "\n".join(f"    self.{name} = {name}" for name in fields))
        ns = {}
        exec(code, ns)
        cls.__init__ = ns["__init__"]

    # 3. 自动生成 __repr__
    if "__repr__" not in cls.__dict__:
        def __repr__(self):
            parts = ", ".join(f"{n}={getattr(self, n)!r}" for n in fields)
            return f"{cls.__name__}({parts})"
        cls.__repr__ = __repr__

    # 4. 自动生成 __eq__
    if "__eq__" not in cls.__dict__:
        def __eq__(self, other):
            if not isinstance(other, cls): return NotImplemented
            return all(getattr(self, n) == getattr(other, n) for n in fields)
        cls.__eq__ = __eq__

    return cls

@dataclass_lite
class Point:
    x: int
    y: int

p = Point(1, 2)
repr(p)          # 'Point(x=1, y=2)' —— __repr__ 是生成的！
p == Point(1, 2) # True —— __eq__ 是生成的！
```

> **🔑 机制洞察**：标准库 `dataclasses` 做的事远多于此（默认值、`field()`、`__match_args__`、slots），但核心机制一致——**类装饰器 + 内省注解 + 运行时生成方法**。`exec` 生成代码是"运行时造代码"的直白形态；更优雅的是用 `types.FunctionType` 构造函数对象。**看懂这个 mini 版，`@dataclass` 就不再是黑盒**。

### 12.9.2 插件注册表系统

两种实现对比（12.2.6 装饰器版 vs 12.5.4 继承版）：

```python
# 方案 A：装饰器注册（显式、灵活——插件无需继承）
PLUGINS = {}

def plugin(name):
    def deco(cls):
        PLUGINS[name] = cls
        return cls
    return deco

@plugin("json")
class JsonHandler:
    def handle(self, data): ...

# 方案 B：__init_subclass__ 自动注册（隐式、约定式——继承即注册）
class BasePlugin:
    registry = {}
    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        BasePlugin.registry[cls.__name__] = cls

class YamlHandler(BasePlugin):    # 自动进 registry
    def handle(self, data): ...
```

| 方案 | 注册方式 | 优点 | 缺点 |
|------|---------|------|------|
| 装饰器 | 显式 `@plugin` | 不强制继承、可带参数 | 容易忘装饰 |
| `__init_subclass__` | 隐式自动 | 不漏注册、约束统一 | 强制继承、不可带名 |

> **实战建议**：**第三方插件**用装饰器（不强制别人继承你的基类）；**自家体系的实现**用 `__init_subclass__`（约定式、防漏）。两种都优于"手写 if/elif 分发"——新增插件=新增一个类/装饰，**开放-封闭原则**（第 7 章设计模式）的元编程实现。

### 12.9.3 声明式 API（ORM 式字段）

描述符 + 元类的组合拳——"字段声明"自动获得校验/序列化：

```python
# 字段描述符（12.3.6 的 Typed 扩展：带名字 + 序列化）
class Field:
    def __init__(self, name, type_):
        self.name, self.type_ = name, type_
        self.data = {}
    def __get__(self, obj, objtype=None):
        return self.data[obj]
    def __set__(self, obj, value):
        if not isinstance(value, self.type_):
            raise TypeError(f"{self.name} must be {self.type_.__name__}")
        self.data[obj] = value

# 元类：自动把"裸 Field 实例"命名（否则描述符不知道自己的名字）
class ModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        for key, value in namespace.items():
            if isinstance(value, Field):
                value.name = key              # 注入字段名！
        return super().__new__(mcls, name, bases, namespace)

class Model(metaclass=ModelMeta):
    def to_dict(self):
        return {k: getattr(self, k) for k, v in type(self).__dict__.items()
                if isinstance(v, Field)}

class User(Model):
    name = Field(str)                  # 声明式：name 是 str 字段
    age = Field(int)

u = User()
u.name = "Alice"       # ✅ 类型校验
u.age = "30"           # TypeError: age must be int
u.to_dict()            # {'name': 'Alice'} —— 声明式 API 的序列化
```

> **🔑 机制洞察**：**"描述符不知道自己的名字"**是声明式 API 的核心难题——`name = Field(str)` 创建描述符时还没有 `name` 这个名字。解法：**元类在类创建时注入名字**（`ModelMeta.__new__` 遍历命名空间）。这就是 Django/SQLAlchemy 字段声明（`name = CharField()`）背后的机制——元类把"声明"变成"带名字的字段元数据"。**描述符管行为、元类管命名**，组合成完整的声明式框架。

### 12.9.4 元编程使用边界

**元编程是把双刃剑**——威力与隐式复杂度成正比：

```python
# ✅ 该用元编程的场景（有明确收益）：
# 1. 横切关注点：日志/缓存/权限/重试（装饰器）——消除重复
# 2. 声明式 API：dataclass/ORM/校验框架——用户写声明拿行为
# 3. 框架基础设施：pytest 断言重写、Flask 路由——面向大众的 API

# ❌ 不该用元编程的场景（隐式魔法 > 收益）：
# 1. 只有自己/团队内部用的小工具——显式 if/else 更可读
# 2. "为了炫技"的元类——同事看不懂、调试难
# 3. 可以普通代码实现的——"能用装饰器就别描述符，能用描述符就别元类"
```

**元编程的调试成本**（衔接第 14 章）：

```python
# 元编程产物的调试三件套：
import inspect
inspect.getsource(ClassWithMeta)       # 看类定义（元类注入的看不到）
inspect.getmro(ClassWithMeta)          # 看继承链
inspect.signature(DecoratedFunc)       # 看真实签名（穿透 __wrapped__）

# 断点看元类执行：在 Meta.__new__/__init__ 打断点（第 14 章 pdb）
# 反汇编：dis.dis(DecoratedFunc) 看装饰后的字节码
```

> **工程影响**：元编程的**黄金规则**——**"隐式"必须为"显著收益"买单**。判断标准：使用者是否从中获得**实质的简洁或安全**（写声明拿行为）？如果只是"代码少几行但难懂十倍"，别用。参考标准库的态度：`dataclass`（收益巨大、广泛采用）、`Enum`（收益明确）、`ABC`（收益明确）——它们都是"收益 >> 复杂度"的正面案例，也是你衡量自己元编程设计的标尺。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 元编程 | 代码操作代码；三层能力（装饰器/描述符/元类）；复杂度与威力成正比 |
| 装饰器 | `@deco` ≡ `f = deco(f)`（导入时执行）；工厂两层结构；`@wraps` 保元信息；类装饰器（`@dataclass` 形态）；洋葱模型顺序 |
| 描述符 | `__get__`/`__set__`/`__delete__`；**数据描述符 > 实例 dict > 非数据描述符**；`property`/`classmethod`/`staticmethod`/`__slots__` 全是描述符 |
| 属性协议 | 完整查找路径（数据描述符→dict→非数据描述符→`__getattr__`）；`__getattr__` 兜底 vs `__getattribute__` 全拦截；`__setattr__` 递归陷阱；代理模式 |
| 元类 | 一切类都是 `type` 的实例；`class` ≡ `type(name, bases, ns)`；`__prepare__`/`__new__`/`__init__` 三段钩子；`__init_subclass__`（PEP 487）优先于元类；注册表/单例元类；metaclass 冲突 |
| 可调用 | `__call__` 协议；带状态的可调用实例；`partial` 是标准库案例 |
| `__new__` | 创建 vs 初始化；返回非本类则 `__init__` 不执行；不可变对象只能 `__new__` 设值；单例/池化 |
| 序列化 | `__reduce__`（自定义重建）/`__getstate__`/`__setstate__`（状态控制）；元编程产物（lambda/动态类）不可 pickle |
| 实战 | mini-dataclass（类装饰器+内省）、插件注册（装饰器 vs `__init_subclass__`）、声明式字段（描述符+元类） |
| 边界 | 收益 >> 复杂度才用；能用低级不用高级；标准库 dataclass/Enum 是正面标尺 |

---

#### 练习 12

**第 1–3 题：验证理解（预测/解释）**

1. 预测输出并解释：`@a @b def f(): ...` 的定义时应用顺序与运行时调用顺序（洋葱模型）；装饰器忘记 `return` 会发生什么？

2. 解释：为什么 `c.method` 每次返回新的绑定对象（`c.method is c.method` 为 False）？`property` 与普通方法在描述符类型上有什么本质区别（数据 vs 非数据）？`obj.x = ...` 对两者分别发生什么？

3. 解释 `class C: ...` 与 `C = type("C", (), {})` 的等价性；元类的 `__new__`/`__init__`/`__prepare__` 各在类创建流程的哪个环节触发？`__init_subclass__` 为什么能替代大部分元类需求？

**第 4–6 题：动手实战**

4. 写一个 `@logged(level="INFO")` 装饰器工厂：记录调用参数与返回值（用 `logging`，衔接 13.9），支持 `@logged` 与 `@logged(level=...)` 两种用法（需要判断参数形态），并确保 `@wraps` 保留签名（用 `inspect.signature` 验证）。

5. 实现类型校验描述符 `Validated`（校验 int/str/float 之一，带默认值），并用它定义 `Product`（name/price/stock）；验证非法赋值抛错、合法赋值通过；再实现 `lazy_property` 并验证"只计算一次"。

6. 写一个注册表元类 `AutoRegister`：所有子类自动登记到 `registry`；再用 `__init_subclass__` 实现同样功能；对比两者的注册时机（哪个能拿到类关键字参数 `name=`）。

**第 7–9 题：实战进阶**

7. 复刻 mini-`@dataclass`（12.9.1）：支持 `__init__`/`__repr__`/`__eq__` 自动生成 + 类型校验；用 `@dataclass_lite` 定义 2–3 个类并测试；对比标准库 `@dataclass` 的行为差异（至少找出 3 个你缺失的特性）。

8. 实现"声明式字段 + 序列化"（12.9.3 的 `Field`/`ModelMeta`）：支持 `to_dict`/`from_dict` 与类型校验；再加一个"默认值"特性（`Field(str, default="")`）。

9. 序列化实战：定义一个含锁/连接的对象，用 `__reduce__` 让它可 pickle；再定义一个带缓存字段的对象，用 `__getstate__`/`__setstate__` 排除缓存；验证 `pickle.loads(pickle.dumps(obj))` 的往返正确性。

**第 10 题：深度思考**

10. 设计判断：团队项目里有人提议用元类实现"所有模型类自动加 created_at/updated_at 时间戳字段"。基于 12.9.4 的边界原则：(a) 你会支持还是反对？给出收益/复杂度分析；(b) 有没有更简单的替代方案（类装饰器？`__init_subclass__`？混入类？）；(c) 如果必须用元类，你会怎么设计（钩子放在 `__new__` 还是 `__init__`？如何处理与 `__slots__`、继承的关系）？结合本章机制给出完整设计。

---

**进入下一章的准备**：
- ✅ 能展开 `@deco` 语法糖并写出带参数装饰器 + `@wraps`
- ✅ 能解释描述符优先级并手写 `property`/`classmethod` 等价实现
- ✅ 能画出属性访问的完整查找路径，区分 `__getattr__`/`__getattribute__`
- ✅ 能写出简单元类并解释 `class` 语句的创建流程；优先用 `__init_subclass__`
- ✅ 理解 `__call__`/`__new__`/`__reduce__` 协议并能用于实战
- ✅ 掌握元编程使用边界："收益 >> 复杂度"才用

下一章（第 15 章 性能优化与 C 扩展）是卷 1 的收官章——元编程的"运行时生成代码"与第 14 章的剖析工具在此汇合：届时将用 `dis` 看元编程产物的字节码、用 `timeit` 比较描述符 vs 普通属性、并进入 `ctypes`/Cython/C 扩展的世界，回答"Python 为什么慢、怎么让它快"。