# 第4章 运算符

> **学习目标**：建立对 Python 运算符体系的完整理解——不仅知道每个运算符"做什么"，更要理解其数学定义、底层协议、短路语义、优先级规则，以及如何在自定义类型中正确实现运算符重载。

---

Python 的运算符体系远不止"加减乘除"。它是一套精心设计的**协议系统**——每个运算符背后都对应着特定的魔术方法（dunder methods），由解释器在求值时自动调用。理解这套协议，你就能写出与内置类型行为一致的、可组合的自定义类型。

本章与第 2 章的关系：第 2 章的 2.6 节（赋值全解）和 2.7 节（运算符与表达式）提供了快速概览。本章在此基础上**逐类深入**，并新增位运算、成员运算、运算符协议和重载专题。两部分互为补充——第 2 章的概述适合速查，本章适合系统学习。

---

## 4.1 算术运算符

算术运算符是编程语言中最古老的运算符家族。Python 的算术运算符在简洁性之外，隐藏了值得深入理解的细节。

### 4.1.1 基本算术：`+` `-` `*` `/`

```python
# 加减乘除——最基础的四个
>>> 10 + 3        # 13
>>> 10 - 3        # 7
>>> 10 * 3        # 30
>>> 10 / 3        # 3.3333333333333335
```

**`/` 始终返回 float**：这是 Python 3 最值得注意的除法设计决策。在 Python 2 中，`/` 在两个整数之间执行**地板除**（截断小数部分）。Python 3 修正了这个反直觉的行为——`/` 始终返回浮点数，无论操作数的类型。

```python
# Python 3：/ 始终是"真除法"
>>> 10 / 5        # 2.0——即使能整除也返回 float
>>> 10 / 3        # 3.3333333333333335
>>> type(10 / 5)
<class 'float'>

# 如果你需要整数结果，用 //
>>> 10 // 5       # 2（int）
```

**数值类型提升规则**：当两个操作数类型不同时，Python 遵循"向更宽的类型转换"原则：

```python
>>> type(1 + 2)          # int + int → int
<class 'int'>
>>> type(1 + 2.0)        # int + float → float（int 被提升为 float）
<class 'float'>
>>> type(1.5 + 2.0j)     # float + complex → complex
<class 'complex'>
```

这条规则来自 C 的"寻常算术转换"（usual arithmetic conversions），但 Python 的 `int` 是无限精度的，所以不会发生 C 中常见的整数溢出。类型提升链条为：`int → float → complex`。

> **工程影响**：`int` 到 `float` 的隐式转换可能丢失精度——`float` 只有 53 位尾数，而 Python `int` 可以表示任意大的整数。当你处理超过 `2**53` 的整数时，`float(int_value)` 会产生舍入误差。这不是 Python 特有的问题，而是 IEEE 754 的固有限制。

### 4.1.2 地板除 `//`：向下取整的精确语义

`//` 是**地板除**（floor division）——结果向**负无穷方向**取整（即 `math.floor(a / b)`），而非向零取整。

```python
# 正数行为——符合直觉
>>> 7 // 2        # 3（3.5 → 向下 → 3）
>>> 10 // 3       # 3

# 负数行为——关键差异！
>>> -7 // 2       # -4（-3.5 → 向下 → -4，而非 -3！）
>>> 7 // -2       # -4（-3.5 → 向下 → -4）
```

**Python vs C/Java 的地板除**：

| 语言 | `-7 / 2`（整数除法） | 取整方向 |
|------|---------------------|---------|
| Python (`//`) | `-4` | 向负无穷（floor） |
| C / Java / JavaScript | `-3` | 向零（truncate） |

```python
# 直观对比
>>> import math
>>> math.floor(-3.5)     # -4（向负无穷）
>>> int(-3.5)             # -3（向零截断）
>>> -7 // 2               # -4（Python 地板除 = floor）

# 如果你需要 C 风格的"向零截断"，用 int(a / b)
>>> int(-7 / 2)           # -3（先浮点除法，再向零截断）
```

**地板除的数学定义**：

```
a // b = floor(a / b)

其中 floor(x) 是 ≤ x 的最大整数
```

**为什么 Python 选择向负无穷取整？**

这是为了与取模运算 `%` 保持数学上的一致性——保证以下恒等式始终成立：

```
a = b * (a // b) + (a % b)    # 除法恒等式——对任意 a, b 成立
```

如果 `//` 向零取整（如 C），则 `%` 也必须相应调整，导致负数的 `%` 结果不直观。Python 的设计确保了 `a % b` 始终与 `b` 同号（当 `b > 0` 时非负），这对环形缓冲等场景非常有用（见 4.1.3）。

### 4.1.3 取模 `%`：不仅仅是"取余数"

Python 的 `%` 是**数学取模**，而非 C 语言风格的**余数**。两者的区别只在涉及负数时出现。

**Python 取模的数学定义**：

```
a % b = a - b * floor(a / b)
```

这保证了 `a % b` 的结果始终与除数 `b` 同号（当 `b != 0` 时）。

```python
# Python 取模——结果与除数同号
>>> 7 % 3         # 1（7 = 3*2 + 1）
>>> -7 % 3        # 2（-7 = 3*(-3) + 2）  ← 结果为正！
>>> 7 % -3        # -2（7 = -3*(-3) + (-2)）
>>> -7 % -3       # -1（-7 = -3*2 + (-1)）

# 对比：C/Java 的 %——结果与被除数同号
# C: -7 % 3 = -1  （截断除法下：-7 = 3*(-2) + (-1)）
```

**实用场景**：

```python
# 场景 1：环形缓冲——索引在 0..n-1 之间循环
>>> def circular_index(i, n):
...     return i % n
>>> circular_index(5, 3)     # 2
>>> circular_index(-1, 3)    # 2（从末尾回绕！）

# 场景 2：判断周期——每 N 个元素触发一次
>>> for i in range(1, 21):
...     if i % 5 == 0:
...         print(f"第 {i} 个——五的倍数")

# 场景 3：将任意整数映射到固定范围 [0, n)
>>> def clamp_to_range(value, n):
...     return value % n      # 始终在 [0, n) 内
>>> clamp_to_range(-10, 7)    # 4

# 场景 4：时间计算——分钟/秒的进位
>>> total_seconds = 125
>>> minutes = total_seconds // 60    # 2
>>> seconds = total_seconds % 60     # 5
```

**`divmod()`：同时获取商和余数**：

```python
>>> divmod(7, 3)        # (2, 1)   → 7 = 3*2 + 1
>>> divmod(-7, 3)       # (-3, 2)  → -7 = 3*(-3) + 2
>>> divmod(7, -3)       # (-3, -2) → 7 = -3*(-3) + (-2)

# divmod 的内部实现等价于：
# (a // b, a % b)
```

**`%` 的字符串格式化用途**（旧式）：

```python
# printf 风格——已不推荐但大量存在于老代码中
>>> "Hello, %s! You are %d years old." % ("Alice", 30)
'Hello, Alice! You are 30 years old.'

# ✅ 现代替代：f-string 或 str.format()
>>> name, age = "Alice", 30
>>> f"Hello, {name}! You are {age} years old."
```

### 4.1.4 幂运算 `**`：右结合性与模幂

`**` 是 Python 中唯一的**右结合**算术运算符。

```python
# 右结合：2**3**2 = 2**(3**2) = 2**9 = 512
>>> 2 ** 3 ** 2
512
>>> 2 ** (3 ** 2)       # 512——显式括号确认
512
>>> (2 ** 3) ** 2        # 64——左结合的结果
64

# 如果写成链式，从右向左分组
# a ** b ** c  永远等价于  a ** (b ** c)
```

**`pow()` 内置函数**：

```python
# pow(base, exp) —— 等价于 base ** exp
>>> pow(2, 10)          # 1024

# pow(base, exp, mod) —— 三参数形式：模幂运算（高效！）
>>> pow(2, 1000, 100)   # 2**1000 % 100，但不需要先算 2**1000
76
```

**三参数 `pow()` 的效率秘密**：`pow(a, b, c)` 使用**快速模幂算法**（平方-乘算法），时间复杂度为 O(log b)，且中间值始终保持在 `c` 的范围内——不会产生巨大的中间结果。这与 `a ** b % c` 有天壤之别，后者会先计算出可能占据大量内存的 `a ** b`。

```python
# ❌ 计算 2**1000000——一个 30 万位的整数，然后取模
# result = (2 ** 1000000) % (10**9 + 7)    # 极慢且占用大量内存

# ✅ 模幂运算——几乎瞬间完成
>>> result = pow(2, 1000000, 10**9 + 7)    # 毫秒级
```

这在密码学（RSA、Diffie-Hellman）和组合数学中至关重要。

**大整数幂**：

```python
# Python 的 int 是无限精度的——2**1000 完全没问题
>>> len(str(2 ** 1000))     # 302 位数字
302

# 负指数——返回 float
>>> 10 ** -2                # 0.01
>>> 4 ** -0.5               # 0.5（即 1/√4）

# 分数指数——返回 float
>>> 16 ** 0.5               # 4.0（√16）
>>> 8 ** (1/3)              # 2.0（∛8）
```

### 4.1.5 矩阵乘法 `@`（Python 3.5+）

`@` 运算符由 PEP 465（2014）引入，专门用于**矩阵乘法**。它是 Python 生态中一个罕见的"为特定领域添加的运算符"。

```python
# 纯 Python 中 @ 没有内置实现——它依赖 __matmul__
# 其真正用途在 numpy 等数值计算库中：

import numpy as np

a = np.array([[1, 2],
              [3, 4]])
b = np.array([[5, 6],
              [7, 8]])

# @ 使矩阵乘法代码可读性飞跃
result = a @ b            # 矩阵乘法——清晰直观

# 对比：之前的写法
result = a.dot(b)         # 方法调用——不自然
result = np.dot(a, b)     # 函数调用——冗长
result = np.matmul(a, b)  # 另一函数

# @ 同样支持增强赋值
a @= b                    # 等价于 a = a @ b
```

**为什么需要 `@`？**

在 `@` 出现之前，Python 中写矩阵乘法极其痛苦。`*` 在 numpy 中是逐元素乘法（Hadamard 积），而不是数学家和数据科学家期待的矩阵乘法。这导致代码中充满 `.dot()` 调用，在复杂表达式中尤其难以阅读：

```python
# ❌ 没有 @ 时
result = (S.inv().dot(X.T).dot(W)).dot(y)

# ✅ 有了 @ 之后
result = S.inv() @ X.T @ W @ y
```

**`@` 的魔术方法**：

| 方法 | 用途 |
|------|------|
| `__matmul__(self, other)` | `self @ other` |
| `__rmatmul__(self, other)` | `other @ self`（当 other 的 `__matmul__` 返回 NotImplemented） |
| `__imatmul__(self, other)` | `self @= other` |

### 4.1.6 一元运算符：`+x` `-x`

```python
# 一元正——几乎恒等（但会调用 __pos__，可用于类型转换）
>>> +42             # 42
>>> +(-3.14)        # -3.14

# 一元负——取负数（调用 __neg__）
>>> -42             # -42
>>> -(-3.14)        # 3.14

# 一元正的实际用途：显式触发类型转换（如 decimal）
>>> from decimal import Decimal
>>> +Decimal('3.14')     # Decimal('3.14')——保持精度
```

**`abs()`：绝对值**：

```python
>>> abs(-42)            # 42
>>> abs(-3.14)          # 3.14
>>> abs(3 + 4j)         # 5.0（复数的模——√(3²+4²)）

# abs() 调用 __abs__ 魔术方法
```

---

## 4.2 比较运算符

### 4.2.1 值比较：`==` `!=` `<` `<=` `>` `>=`

六种值比较运算符构成了 Python 的排序和相等判断基础：

```python
# 基本的比较运算
>>> 5 == 5          # True（相等）
>>> 5 != 3          # True（不等）
>>> 3 < 5           # True（小于）
>>> 5 <= 5          # True（小于等于）
>>> 10 > 3          # True（大于）
>>> 5 >= 5          # True（大于等于）
```

**这些运算符可以用于任何实现了对应魔术方法的类型**：

| 运算符 | 魔术方法 |
|--------|---------|
| `==` | `__eq__(self, other)` |
| `!=` | `__ne__(self, other)` |
| `<` | `__lt__(self, other)` |
| `<=` | `__le__(self, other)` |
| `>` | `__gt__(self, other)` |
| `>=` | `__ge__(self, other)` |

> **`!=` 的自动回退**：如果类型没有定义 `__ne__`，Python 会自动使用 `not (self.__eq__(other))`。因此你通常只需要实现 `__eq__`，`!=` 会自动工作。

### 4.2.2 链式比较：编译器级别的语法糖

Python 的链式比较是其最优雅的特性之一——任意数量的比较运算符可以串联，中间项只求值一次。

```python
# 数学直觉：0 < x < 10
>>> x = 5
>>> 0 < x < 10         # True
>>> 0 < x <= 10        # True
>>> 0 < x < 4          # False

# 解析：a < b < c   等价于   a < b and b < c
# 但关键区别：b 只被求值一次！
```

**链式比较的精确语义**：

```
a OP1 b OP2 c OP3 d ...

被 Python 编译器转换为：

(a OP1 b) and (b OP2 c) and (c OP3 d) ...

但中间的每个表达式（b, c, ...）只求值一次
```

```python
# 验证"只求值一次"——使用带副作用的函数
>>> calls = 0
>>> def get_x():
...     global calls
...     calls += 1
...     return 5
>>> 0 < get_x() < 10       # True
>>> calls                  # 1——get_x() 只被调用一次！
```

**链式比较可以混合不同类型的运算符**：

```python
>>> a, b, c = 1, 2, 2
>>> a < b == c              # a < b AND b == c → True AND True → True

# 但这可能造成混淆——建议保持运算符方向一致
>>> 1 < 5 > 3 < 10          # True——全为 True，但读起来费劲
```

**与 C 语言的根本差异**：

```c
// C 语言中：
// 0 < x < 10  先求值 (0 < x)，结果为 1 或 0
//             再求值 (1 或 0) < 10，结果几乎永远是 1
// 这是一个经典 bug！
```

```python
# Python 中：0 < x < 10 做的是你直觉所想的事
>>> x = 5
>>> 0 < x < 10      # True——Python 方式，正确
# C 语言的等效写法：0 < x && x < 10
```

### 4.2.3 富比较协议：`NotImplemented` 的角色

当你实现自定义类型的比较时，关键的一点是理解 `NotImplemented`（注意：**不是** `NotImplementedError`）。

```python
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):
        if isinstance(other, Vector):
            return self.x == other.x and self.y == other.y
        return NotImplemented    # ← 告诉 Python "我不知道怎么比较"
        # ❌ 常见错误：raise TypeError 或 return False
```

**`NotImplemented` 的作用**：当 `__eq__` 返回 `NotImplemented` 时，Python 会**尝试调换操作数的位置**，调用 `other.__eq__(self)`。如果也返回 `NotImplemented`，Python 才进行默认的身份比较（`is`）。

```python
# 正确实现比较协议的三个要点：
# 1. 能处理的情况返回 bool
# 2. 不能处理的情况返回 NotImplemented（不是 raise 也不是 False）
# 3. 类型检查用 isinstance，不要精确匹配 type()

class Temperature:
    def __init__(self, celsius):
        self.celsius = celsius

    def __eq__(self, other):
        if isinstance(other, Temperature):
            return self.celsius == other.celsius
        if isinstance(other, (int, float)):
            return self.celsius == other
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, Temperature):
            return self.celsius < other.celsius
        if isinstance(other, (int, float)):
            return self.celsius < other
        return NotImplemented

# 使用
>>> t = Temperature(25)
>>> t == 25         # True（Temperature.__eq__ 处理了 int）
>>> 25 == t         # True！（int.__eq__ 返回 NotImplemented，
                    #        Python 转而调用 Temperature.__eq__）
```

**`functools.total_ordering`：自动补全比较方法**：

如果你只需要定义 `__eq__` 和**一个**序关系方法（`__lt__`、`__le__`、`__gt__` 或 `__ge__` 中的任一个），`functools.total_ordering` 装饰器会自动补全其余四种：

```python
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, major, minor):
        self.major, self.minor = major, minor

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor) < (other.major, other.minor)

# 以下方法被 @total_ordering 自动生成：
# __le__, __gt__, __ge__

>>> v1, v2 = Version(2, 1), Version(2, 3)
>>> v1 < v2         # True（你定义的）
>>> v1 <= v2        # True（自动生成的！）
>>> v1 >= v2        # False（自动生成的！）
```

**`@total_ordering` 的代价**：自动生成的方法比手写实现慢——它们通过组合 `__lt__` 和 `__eq__` 来推导结果（例如 `__le__` 实现为 `self < other or self == other`），这意味着每次调用可能执行两次比较。在性能敏感的热路径上，手动实现所有六个方法。

### 4.2.4 不同类型间的比较

```python
# Python 3 对不同"不可比较"类型的行为
>>> 3 < "hello"
TypeError: '<' not supported between instances of 'int' and 'str'

# 但 == 和 != 不会报错——它们比较的是对象类型
>>> 3 == "hello"    # False（不抛异常——类型不同就是不等）
>>> 3 != "hello"    # True

# 例外：float 和 int 可以互相比较（通过类型提升）
>>> 3 == 3.0            # True
>>> 3 < 3.5             # True

# float 和 Decimal/Complex 则不行
>>> from decimal import Decimal
>>> 3.0 == Decimal('3.0')
False            # ← 注意：不等！float 和 Decimal 是不同的类型
```

> **Python 2 的遗留教训**：Python 2 对不同类型使用"任意全序"——`3 < "hello"` 可以执行（比较类型名）。Python 3 废除了这个设计，因为它制造了隐蔽的 bug。

---

## 4.3 身份运算符

### 4.3.1 `is` / `is not` 的底层原理

`is` 检查两个引用是否指向**内存中同一个对象**——它比较的是 `id()` 的值，而不是对象的内容。

```python
# is 的本质
>>> a = [1, 2, 3]
>>> b = a
>>> a is b               # True——同一个对象
>>> id(a) == id(b)       # True——证明

>>> a = [1, 2, 3]
>>> b = [1, 2, 3]
>>> a is b               # False——内容相同但对象不同
>>> a is not b           # True
```

**`id()` 与 CPython 实现**：在 CPython 中，`id()` 返回对象在内存中的起始地址。这是一个实现细节——其他 Python 实现（如 PyPy、Jython）可能返回别的标识符。但所有实现都保证：**对象在其生命周期内 `id()` 不变，且同一时刻不同对象的 `id()` 不同**。

```python
# 生命周期内的 id 不变性
>>> x = [1, 2, 3]
>>> original_id = id(x)
>>> x.append(4)            # 原地修改——对象不变
>>> id(x) == original_id   # True

# 但重新绑定后，x 指向新对象
>>> x = x + [5]            # 创建新列表
>>> id(x) == original_id   # False——新的 id
```

### 4.3.2 对象内部化（Interning）

CPython 对某些常用不可变对象做**内部化**——预先创建并共享同一个实例，以节省内存和比较成本。

```python
# 小整数缓存：-5 到 256（CPython 启动时预先创建）
>>> a = 256
>>> b = 256
>>> a is b              # True——CPython 内部化

>>> a = 257
>>> b = 257
>>> a is b              # False！（同一行写可能为 True，不同行必定 False）
                        # 原因：超出缓存范围，每次创建新对象

# 短字符串的内部化（编译时常量自动内部化）
>>> a = "hello"
>>> b = "hello"
>>> a is b              # True——同一编译单元中的相同字符串被内部化

>>> a = "hello world!"
>>> b = "hello world!"
>>> a is b              # True——较短且看起来像标识符的字符串

# 运行时构造的字符串默认不内部化
>>> a = "".join(["h", "e", "l", "l", "o"])
>>> b = "".join(["h", "e", "l", "l", "o"])
>>> a is b              # False——运行时构造，不在内建缓存中

# 显式内部化：sys.intern()
>>> import sys
>>> a = sys.intern("".join(["h", "e", "l", "l", "o"]))
>>> b = sys.intern("".join(["h", "e", "l", "l", "o"]))
>>> a is b              # True——sys.intern() 强制内部化
```

**interning 的目的**：在大量字符串比较的场景（如解析器、编译器）中，内部化后的 `is` 比 `==` 快得多——`is` 是 O(1) 指针比较，`==` 是 O(n) 逐字符比较。

```python
# 小整数缓存的范围是 CPython 实现细节
>>> import sys
>>> a = -6; b = -6
>>> a is b     # False—— -6 不在缓存范围内
>>> a = 256; b = 256
>>> a is b     # True——在缓存范围内
```

> **⚠️ 永远不要依赖 interning 行为来比较相等性。** 缓存范围是实现细节，随 Python 版本和实现（CPython vs PyPy vs Jython）不同而不同。依赖 `is` 来做值比较的代码是不可移植的。

### 4.3.3 `==` vs `is`：决策树

```
你在做什么？

├─ 与 None（或 True/False）比较
│   └─ 用 is ／ is not
│      if x is None: ...
│      if flag is True: ...
│
├─ 检查两个名字是否指向完全相同的对象
│   └─ 用 is
│      if cached_result is current_result: ...
│
├─ 检查两个对象的值是否相等
│   └─ 用 ==
│      if user_input == "yes": ...
│
└─ 其他一切情况
    └─ 用 ==
```

```python
# ✅ 正确的惯用法
if value is None:              # 检查 None——用 is
    handle_missing()

if data is not None:           # 检查非 None
    process(data)

if flag is True:               # 检查布尔单例（当需要区分 True 和 truthy 值时）
    do_something()

# ❌ 错误
if value == None:              # 可行但非惯用—— __eq__ 可能被重载
    ...

# ✅ 使用 == 来比较值
if name == "Alice":            # 值相等
    greet()
```

**为什么 `is None` 是唯一正确的写法？**

`None` 在 Python 中是**单例**（singleton）——整个解释器中只有一个 `None` 对象。`is` 直接比较两个引用是否指向这个唯一的对象。而 `==` 调用了 `__eq__` 方法——如果一个（可能是恶意的或有 bug 的）类重载了 `__eq__` 并声称自己"等于 None"，用 `==` 就会产生误判。`is` 绕过了 `__eq__`，直接做身份检查，因此是安全的。

```python
# 假设有人写了这样一个类
class Dangerous:
    def __eq__(self, other):
        return True        # 无论和谁比都说 True

d = Dangerous()
print(d == None)           # True——被 __eq__ 欺骗！
print(d is None)           # False——is 不受重载影响，正确
```

**`==` 和 `is` 的完整对照**：

| | `==` | `is` |
|------|------|------|
| **检查什么** | 值相等（equality） | 身份相同（identity） |
| **调用方法** | `__eq__` | 无（C 层指针比较） |
| **可否被重载** | 是 | 否 |
| **速度** | O(1)～O(n)，取决于 `__eq__` 实现 | 始终 O(1) |
| **适用场景** | 比较内容 | 检查单例 / 检查同一对象 |

---

## 4.4 逻辑运算符

### 4.4.1 `and` / `or` / `not`

Python 的逻辑运算符在语法上是英文单词而非符号（`&&`、`||`、`!` 在 Python 中不存在），在语义上使用短路求值并**返回操作数本身**。

```python
# not：逻辑非——始终返回 True 或 False
>>> not True                # False
>>> not False               # True
>>> not 0                   # True（0 是假值）
>>> not "hello"             # False（非空字符串是真值）

# and：逻辑与——返回第一个假值，或最后一个值
>>> 0 and 1                 # 0
>>> 1 and 0                 # 0
>>> 1 and 2 and 3           # 3（全真，返回最后一个）
>>> [] and [1, 2]           # []（第一个为假）

# or：逻辑或——返回第一个真值，或最后一个值
>>> 0 or 1                  # 1
>>> "" or "default"         # "default"
>>> 0 or [] or {}           # {}（全假，返回最后一个）
>>> False or None or 0      # 0
```

**关键事实**：`and` 和 `or` 返回的是**操作数对象本身**，而不是 `True` / `False`。`not` 则总是返回 `True` 或 `False`。

```python
>>> result = 3 and 5
>>> result                  # 5——不是 True！
>>> bool(result)            # True——当然，5 是真值

>>> result = 0 or "hello"
>>> result                  # "hello"——不是 True！
>>> bool(result)            # True
```

这一特性催生了若干个语言层面的惯用模式。

### 4.4.2 短路求值：原理与经典模式

**短路求值的定义**：

- **`x and y`**：先求值 `x`。如果 `bool(x)` 为 `False`，返回 `x`（`y` **永远不会被求值**）。否则，返回 `y`。
- **`x or y`**：先求值 `x`。如果 `bool(x)` 为 `True`，返回 `x`（`y` **永远不会被求值**）。否则，返回 `y`。

```python
# 短路证明
>>> 0 and print("这不会打印")      # 0 是假值 → 短路 → print 不执行

>>> 1 or print("这也不会打印")     # 1 是真值 → 短路 → print 不执行
```

**短路求值的经典惯用模式**：

```python
# ── 模式 1：安全链式访问（防御 None） ──
# 如果 obj 为 None，obj.attribute 会抛出 AttributeError
# 短路求值提供了一种简洁的保护机制
>>> result = obj and obj.attribute and obj.attribute.method()
# 等价于：
# if obj is not None and obj.attribute is not None:
#     result = obj.attribute.method()
# else:
#     result = None

# ── 模式 2：提供默认值 ──
>>> name = user_input or "Anonymous"
# 如果 user_input 为假值（""、None、0 等），使用 "Anonymous"

# ⚠️ 注意：这会视空字符串和 0 为"未设置"
# 如果需要精确区分 None 和空值，用：
>>> name = user_input if user_input is not None else "Anonymous"

# ── 模式 3：条件副作用（谨慎使用） ──
>>> debug and print(f"Debug: value = {value}")
# 当 debug 为 True 时执行 print；为 False 时短路跳过

# ── 模式 4：嵌套多级默认值 ──
>>> final = config_override or env_var or config_file or "default_value"
# 取第一个真值——优先级链
```

**短路求值 vs 热切求值**：

```python
# 短路（Python 的方式）
def safe_division(a, b):
    return b != 0 and a / b > 0     # b=0 时不会执行 a/b

# 如果 Python 使用热切求值（所有参数都先求值再调用函数）
# 那么 safe_division(5, 0) 会在 and 判断之前就因 a/b 抛出异常
```

### 4.4.3 真值测试：`bool()` 与 `__bool__` / `__len__`

Python 中**每个对象**都有布尔真值。判定规则遵循一个明确的优先级链：

```
bool(obj) 的求值流程：

1. 如果 obj 定义了 __bool__，调用 obj.__bool__()
   结果必须返回 bool 类型（True 或 False），否则抛出 TypeError

2. 如果没定义 __bool__ 但有 __len__，调用 obj.__len__()
   返回 0 为 False，非 0 为 True

3. 如果两者都没定义，默认为 True
```

**内置类型的假值完整清单**：

| 类型 | 假值（`bool(x) == False`） |
|------|--------------------------|
| `NoneType` | `None` |
| `bool` | `False` |
| `int` | `0` |
| `float` | `0.0` |
| `complex` | `0j` |
| `str` | `""`（空字符串） |
| `bytes` | `b""`（空字节） |
| `list` | `[]`（空列表） |
| `tuple` | `()`（空元组） |
| `dict` | `{}`（空字典） |
| `set` | `set()`（空集合） |
| `frozenset` | `frozenset()` |
| `range` | `range(0)` |
| 自定义 | `__bool__` 返回 `False` 或 `__len__` 返回 `0` |

**除了以上列出的，一切皆为真值。**

```python
# 常见误解：这些全是真值！
>>> bool("False")        # True——非空字符串！
>>> bool(" ")            # True——非空字符串（空格也算字符）
>>> bool([None])         # True——非空列表！
>>> bool([[]])           # True——非空列表！
>>> bool("0")            # True——非空字符串！

# 验证
>>> "False" == False     # False
>>> bool("False")        # True
```

> **实战建议**：写 `if items:` 而非 `if len(items) > 0:`。前者更快（调用 `__bool__`，通常是 O(1)），后者可能遍历整个容器（O(n)）。同样，写 `if items is not None:` 来区分"空容器"和"没有容器"。

```python
# ✅ 惯用法
if items:                    # items 非空
if not items:                # items 为空
if items is None:            # items 是 None（没有容器）
if items is not None:        # items 存在（可能是空容器）

# ❌ 啰嗦
if len(items) > 0:           # 多余且对某些容器是 O(n)
if items != []:              # 不必要地构建了一个空列表
```

---

## 4.5 位运算符

位运算符直接操作整数的二进制表示。在系统编程、协议解析、权限模型和性能优化中，它们是不可替代的工具。

### 4.5.1 按位与 `&`、或 `|`、异或 `^`

```python
# 二进制层面操作
>>> a = 0b1100    # 12
>>> b = 0b1010    # 10

>>> bin(a & b)    # '0b1000'——按位与（两位同时为 1 则结果位为 1）
8

>>> bin(a | b)    # '0b1110'——按位或（任一位为 1 则结果位为 1）
14

>>> bin(a ^ b)    # '0b0110'——按位异或（两位不同则结果位为 1）
6
```

**真值表**（适用于单个位）：

| a | b | a & b | a \| b | a ^ b |
|---|---|-------|--------|-------|
| 0 | 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 1 | 1 |
| 1 | 0 | 0 | 1 | 1 |
| 1 | 1 | 1 | 1 | 0 |

```python
# 位运算对 Python 的无限精度整数完全有效
>>> big = (1 << 1000) | (1 << 500)  # 在第 1000 位和第 500 位各设一个 1
>>> big.bit_length()                # 1001
>>> big.bit_count()                 # 2（Python 3.8+）
```

### 4.5.2 按位取反 `~`：补码世界的真相

`~` 在二进制**补码**表示下工作。在补码中，`-x` 表示为 `~x + 1`。等价地：**`~x = -x - 1`**。

```python
# 关键公式：~x = -x - 1
>>> ~0           # -1
>>> ~1           # -2
>>> ~(-1)        # 0
>>> ~42          # -43
>>> ~(-42)       # 41

# 为什么？因为 Python 的整数是无限精度的补码表示：
# 0  的补码是 ...0000（无限个 0）
# ~0 的补码是 ...1111（无限个 1）→ 在补码中这就是 -1
# 1  的补码是 ...0001
# ~1 的补码是 ...1110 → 即 -2
```

```python
# 实用场景：按位取反常用于位掩码操作
# 例如：清除某一位
>>> flags = 0b1111
>>> mask = 0b0010
>>> flags & ~mask       # 0b1101——清除了第 2 位
>>> bin(flags & ~mask)
'0b1101'
```

### 4.5.3 位移 `<<` `>>`

```python
# 左移：x << n = x * (2**n)
>>> 1 << 0       # 1
>>> 1 << 1       # 2
>>> 1 << 10      # 1024
>>> 5 << 3       # 40（5 * 8）

# 右移：x >> n = floor(x / (2**n))
>>> 1024 >> 1    # 512
>>> 1024 >> 10   # 1
>>> 40 >> 3      # 5（40 / 8）
>>> -16 >> 2     # -4（-16 / 4 = -4）
```

**位移对大整数的行为**：

```python
# Python 整数无限精度——左移不受位宽限制
>>> 1 << 100     # 1267650600228229401496703205376
>>> (1 << 100).bit_length()   # 101

# 负数右移：Python 对负数使用符号扩展（算术右移）
>>> -8 >> 1      # -4
>>> -8 >> 2      # -2
# 补码层面：-8 是 ...11111000，右移 2 位变成 ...11111110 = -2
```

### 4.5.4 位运算实战应用

**场景 1：位掩码——标志位（Flags）**

```python
# 定义权限标志
READ    = 0b0001    # 1
WRITE   = 0b0010    # 2
EXECUTE = 0b0100    # 4
DELETE  = 0b1000    # 8

# 设置权限
user_perms = READ | WRITE    # 0b0011 = 3

# 添加权限
user_perms |= EXECUTE        # 0b0111 = 7

# 移除权限
user_perms &= ~WRITE         # 0b0101 = 5

# 检查权限
has_read = (user_perms & READ) != 0        # True
has_write = (user_perms & WRITE) != 0      # False

# 切换权限（toggle）
user_perms ^= READ            # 有 READ → 移除；无 READ → 添加

# 直观输出
def show_perms(flags):
    names = []
    if flags & READ:    names.append("READ")
    if flags & WRITE:   names.append("WRITE")
    if flags & EXECUTE: names.append("EXECUTE")
    if flags & DELETE:  names.append("DELETE")
    return " | ".join(names) if names else "NONE"

>>> show_perms(user_perms)
'READ | EXECUTE'
```

**Python 3.6+ 的 `enum.Flag`**（更高级的标志位方案）：

```python
from enum import Flag, auto

class Permission(Flag):
    READ = auto()       # 1
    WRITE = auto()      # 2
    EXECUTE = auto()    # 4
    DELETE = auto()     # 8

# 组合与检查
>>> perm = Permission.READ | Permission.WRITE
>>> Permission.READ in perm            # True
>>> Permission.EXECUTE in perm         # False
>>> perm
<Permission.READ|WRITE: 3>
```

**场景 2：快速乘除 2 的幂**

```python
# 左移 = 乘以 2 的幂
>>> x = 7
>>> x << 1      # 14（*2）
>>> x << 3      # 56（*8）
>>> x << 10     # 7168（*1024）

# 右移 = 除以 2 的幂（向下取整）
>>> x >> 1      # 3（//2）
>>> 100 >> 3    # 12（100//8）

# 性能说明：在 CPython 中，小整数的位移和乘法性能差异不大
#（CPython 对小整数的乘法做了高度优化）。
# 但在性能关键的循环中，x << n 提供了清晰的意图。
```

**场景 3：快速判奇偶**

```python
# 比 x % 2 更快（虽然差异微小）
>>> def is_odd(n):
...     return n & 1         # 最后一位是 1 → 奇数
>>> def is_even(n):
...     return not (n & 1)   # 最后一位是 0 → 偶数
```

**场景 4：交换两个整数（无临时变量）**

```python
# XOR 交换——经典的位运算技巧
>>> a, b = 10, 20
>>> a ^= b
>>> b ^= a
>>> a ^= b
>>> a, b            # (20, 10)
# 但在 Python 中，直接用 a, b = b, a 更简洁——它同样是高效的
```

**场景 5：大小写转换（ASCII 字符）**

```python
# 大写转小写：设置第 6 位（0x20）
>>> chr(ord('A') | 0x20)     # 'a'
>>> chr(ord('Z') | 0x20)     # 'z'

# 小写转大写：清除第 6 位
>>> chr(ord('a') & ~0x20)    # 'A'
>>> chr(ord('z') & ~0x20)    # 'Z'

# 切换大小写：翻转第 6 位
>>> chr(ord('A') ^ 0x20)     # 'a'
>>> chr(ord('a') ^ 0x20)     # 'A'

# ⚠️ 注意：这只对 ASCII 字母有效——处理 Unicode 请用 str.upper()/lower()
```

**场景 6：判断一个数是否是 2 的幂**

```python
>>> def is_power_of_two(n):
...     return n > 0 and (n & (n - 1)) == 0
>>> is_power_of_two(64)      # True
>>> is_power_of_two(100)     # False
# 原理：2 的幂在二进制中是 100...0 的形式
# n-1 是 011...1，两者按位与必为 0
```

---

## 4.6 成员运算符

### 4.6.1 `in` / `not in`

`in` 检查一个元素是否存在于一容器中，依赖于容器的 `__contains__` 方法。

```python
# 所有内置容器的基本用法
>>> 3 in [1, 2, 3]         # True
>>> 4 in [1, 2, 3]         # False
>>> "a" in "abc"           # True（子串检查）
>>> "ab" in "abc"          # True
>>> "key" in {"key": 42}   # True（检查键，不是值）
>>> 42 in {"key": 42}      # False（in 检查键）
>>> 42 in {"key": 42}.values()  # True（检查值）
>>> "a" in {"a", "b"}      # True

# not in——显式的"不在其中"
>>> 4 not in [1, 2, 3]     # True
```

### 4.6.2 `__contains__` 协议

```python
# in 的本质：调用 __contains__
# x in container  →  container.__contains__(x)

# 如果类型没有定义 __contains__，Python 使用回退策略：
# 1. 通过 __iter__ 迭代容器，逐元素用 == 比较
# 2. 如果也没有 __iter__，使用 __getitem__ 从索引 0 开始查找
```

**回退策略的实际影响**：

```python
class MyContainer:
    def __init__(self, items):
        self._items = items

    def __iter__(self):
        return iter(self._items)
    # 没有定义 __contains__

c = MyContainer([1, 2, 3])
>>> 2 in c                  # True（回退到迭代查找）

# 如果定义了 __contains__，它优先于迭代回退
class FastLookup:
    def __init__(self):
        self._set = set()

    def __contains__(self, item):
        return item in self._set     # O(1) 的哈希查找

    def __iter__(self):
        return iter(self._set)

# in 使用 O(1) 的 __contains__，而不是 O(n) 的迭代
```

### 4.6.3 不同容器中 `in` 的复杂度

这是 `in` 最容易被忽视的性能真相——同一运算符的复杂度取决于容器类型：

| 容器类型 | `in` 的实现 | 时间复杂度 | 备注 |
|---------|------------|-----------|------|
| `list` | 线性扫描 | **O(n)** | 从头开始逐元素 `==` |
| `tuple` | 线性扫描 | **O(n)** | 同 list |
| `str` | 子串搜索 | **O(nm)** 最坏 | 使用 Crochemore-Perrin 等高效算法 |
| `set` | 哈希查找 | **O(1)** | 平均情况 |
| `frozenset` | 哈希查找 | **O(1)** | 同 set |
| `dict` (键) | 哈希查找 | **O(1)** | 检查键，不检查值 |
| `range` | 数学计算 | **O(1)** | Python 3.2+——不迭代！ |
| `bytes` | 子序列搜索 | **O(nm)** 最坏 | 类似 str |

```python
# 性能差异的实战意义
>>> import timeit

# list——线性扫描
>>> timeit.timeit('99999 in data', setup='data = list(range(100000))', number=1000)
1.5  # 秒级

# set——哈希查找
>>> timeit.timeit('99999 in data', setup='data = set(range(100000))', number=1000)
0.0001  # 毫秒级——快了一万倍
```

**实战法则**：如果你反复用 `in` 在一个大型集合中进行成员检查，将 `list` 转换为 `set`。如果顺序无关紧要，一开始就用 `set`。

```python
# range 的 in 是 O(1)——Python 3.2+ 优化
>>> 500 in range(1000000)        # True——瞬间完成
# CPython 实现：直接通过数学计算判断，不迭代
```

### 4.6.4 `for` 循环中的 `in` 不是运算符

初学者常困惑的一点：

```python
# for 中的 in 和作为运算符的 in 是两回事
for item in container:       # ← 这不是成员检查！
    process(item)

# 这里的 in 是 for 语句的语法组成部分，不是运算符
# 它调用的是 container.__iter__()，而非 container.__contains__()
```

`for` 中的 `in` 是语法结构，不能单独出现在表达式中；`x in y` 中的 `in` 是运算符，返回布尔值。

---

## 4.7 增强赋值运算符

增强赋值运算符（`+=` `-=` `*=` `/=` `//=` `%=` `**=` `&=` `|=` `^=` `<<=` `>>=`）提供了一种简写方式，但其底层机制与普通赋值有本质差异。

### 4.7.1 `__iadd__` vs `__add__`：原地修改与新对象

`x += y` 并非简单等同于 `x = x + y`。Python 对增强赋值的执行流程为：

```
x += y 的执行流程：

1. 如果 x 有 __iadd__ 方法：
   x = x.__iadd__(y)
   注意：__iadd__ 应该返回 self（原地修改），但也可以返回新对象

2. 如果没有 __iadd__（退化为普通加法）：
   x = x.__add__(y)

关键区别：
- x = x + y   → 总是先计算 x + y（新对象），再让 x 指向它
- x += y      → 先尝试原地修改；不可行时再退化为新对象
```

**可变对象 vs 不可变对象的行为差异**：

```python
# ── 不可变对象（如 int, str, tuple）──
# __iadd__ 不存在 → 退化为 x = x + y → 创建新对象
>>> a = 10
>>> b = a                # a 和 b 指向同一个 10
>>> a += 5               # 退化为 a = a + 5 → 创建新 int(15)
>>> a, b
(15, 10)                 # b 不受影响

# ── 可变对象（如 list, dict, set, bytearray）──
# __iadd__ 存在 → 原地修改 → 不创建新对象
>>> a = [1, 2, 3]
>>> b = a                # a 和 b 指向同一个列表
>>> a += [4, 5]          # 调用 a.__iadd__([4, 5]) → list.extend() → 原地修改
>>> a, b
([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])   # b 也变了！
```

**`+=` 对 list 的行为陷阱——一个经典的 Python 面试题**：

```python
# x = x + y  和  x += y  对可变对象的区别
>>> a = [1, 2, 3]
>>> b = a
>>> a = a + [4, 5]        # 创建新列表并赋值——a 指向新对象
>>> a is b                 # False
>>> b                      # [1, 2, 3]——不受影响

>>> c = [1, 2, 3]
>>> d = c
>>> c += [4, 5]            # 原地修改——c 还是同一个对象
>>> c is d                 # True
>>> d                      # [1, 2, 3, 4, 5]——也变了
```

**tuple 的 `+=` 陷阱**：

```python
# tuple 是不可变对象，没有 __iadd__，所以 += 退化为 加法+赋值
# 但有一个微妙之处：
>>> t = (1, 2, [3, 4])
>>> t[2] += [5, 6]
# 会发生什么？

# 答案：既成功又失败！
# 1. t[2].__iadd__([5, 6]) 被调用——列表的原地修改成功，t[2] 变成了 [3,4,5,6]
# 2. 然后 Python 尝试 t[2] = <结果>——将修改后的列表赋回 tuple 的位置 2
# 3. tuple 不支持赋值 → TypeError!
# 4. 但列表已经被修改了！

>>> t
(1, 2, [3, 4, 5, 6])      # 列表确实被修改了——尽管抛了异常！
```

> **教训**：不要在 tuple 中包含可变对象并用 `+=` 修改它。这个模式同时产生了副作用（列表被修改）和异常（赋回失败），是最隐蔽的 bug 之一。

**增强赋值的实际优势**：

```python
# ✅ 节省不必要的方法调用
total = total + 1     # 调用 total.__add__(1)，返回新 int，赋值
total += 1            # 同上——int 没有 __iadd__

# ✅ 对可变对象，避免创建中间对象
words += ["more"]     # 原地扩展列表，不创建新列表
words = words + ["more"]  # 创建新的 [*words, "more"]，旧列表被丢弃

# ✅ 代码简洁
matrix[i][j] += delta  # 比 matrix[i][j] = matrix[i][j] + delta 清晰太多
```

---

## 4.8 赋值表达式（海象运算符 `:=`）

`:=`（正式名称为"赋值表达式"）由 PEP 572（2018）引入，Python 3.8+ 可用。它在**表达式内部**完成赋值并返回所赋的值。

由于第 2 章 2.6.5 节已做了详细介绍，这里仅做关键补充：

**`:=` vs `=` 的核心区别**：

| | `=`（赋值语句） | `:=`（赋值表达式） |
|------|---------|---------|
| **语法地位** | 语句（不返回值） | 表达式（返回所赋的值） |
| **使用位置** | 独立一行 | 任何表达式中（需要括号包围） |
| **典型场景** | 普通变量赋值 | 在 `if`/`while` 条件中同时求值和绑定 |

```python
# = 不能出现在表达式中
# if (x = get_value()):    ← SyntaxError!

# := 可以在表达式中
if (x := get_value()):
    process(x)
```

**海象运算符的三个黄金场景**：

```python
# 1. while 循环——读取与判断合一
while chunk := file.read(1024):
    process(chunk)

# 2. if 中捕获中间值
if match := pattern.search(text):
    print(match.group(0))

# 3. 列表推导中避免重复计算
results = [y for x in data if (y := expensive(x)) > threshold]
```

> **节制使用**：`:=` 是一个"有品味地使用"的工具。如果一行因为 `:=` 变得难以理解——回到传统的两行写法。代码是写给人读的。

---

## 4.9 运算符优先级与结合性

### 4.9.1 完整优先级表

以下是 Python 运算符优先级的完整排列——从最高（绑定最紧）到最低：

| 优先级 | 运算符 | 说明 | 结合性 |
|--------|--------|------|--------|
| 1（最高） | `(...)` `[...]` `{...}` | 括号分组、字面量、索引/切片 | 左 |
| 2 | `x(...)` `x.y` | 函数/方法调用、属性访问 | 左 |
| 3 | `await x` | await 表达式 | — |
| 4 | `**` | 幂运算 | **右** |
| 5 | `+x` `-x` `~x` | 一元正/负、按位取反 | **右** |
| 6 | `*` `/` `//` `%` `@` | 乘、除、整除、取模、矩阵乘 | 左 |
| 7 | `+` `-` | 加、减 | 左 |
| 8 | `<<` `>>` | 左移、右移 | 左 |
| 9 | `&` | 按位与 | 左 |
| 10 | `^` | 按位异或 | 左 |
| 11 | `\|` | 按位或 | 左 |
| 12 | `in` `not in` `is` `is not` `<` `<=` `>` `>=` `!=` `==` | 比较、成员、身份 | 左（链式比较除外*） |
| 13 | `not x` | 逻辑非 | **右** |
| 14 | `and` | 逻辑与 | 左 |
| 15（最低） | `or` | 逻辑或 | 左 |
| — | `x if cond else y` | 条件表达式 | — |
| — | `lambda` | lambda 表达式 | — |
| — | `:=` | 赋值表达式 | **右** |

> \* 链式比较（如 `a < b < c`）虽然不是严格意义的左结合，但等价的展开 `a < b and b < c` 中 `and` 是左结合的。

### 4.9.2 常见陷阱：优先级导致的隐蔽 bug

**陷阱 1：位运算符优先级低于比较运算符**

这是 Python 中最容易踩的优先级坑——`&` `|` `^` 的优先级**低于** `==` `!=` `<` `>` 等比较运算符。

```python
# ❌ 大多数人以为的表达顺序
if flags & MASK == MASK:        # 被解析为 flags & (MASK == MASK)！
    ...

# 实际上：
# flags & MASK == MASK
# → flags & (MASK == MASK)     # MASK == MASK → True (= 1)
# → flags & 1                   # 完全不是你以为的结果！

# ✅ 正确写法
if (flags & MASK) == MASK:
    ...
```

```python
# 更多位运算符优先级的坑
>>> a = 5
>>> a & 1 == 1          # → a & (1 == 1) → 5 & True → 5 & 1 → 1
1                       # 碰巧对了——但语义是错的

>>> a & 3 == 3          # → 5 & (3 == 3) → 5 & True → 5 & 1 → 1
1                       # ≠ 5 & 3 → 1——这次错了也没那么容易发现

# ✅ 规则：位运算与比较运算同处一行时，必加括号
>>> (a & 3) == 3        # False（正确的语义）
```

**陷阱 2：`not` 的优先级**

```python
# not 优先级高于 and/or，但低于比较运算符
>>> not a == b          # → not (a == b)   ——符合直觉
>>> not a and b         # → (not a) and b  ——可能不符合直觉

# ✅ 建议
if not (a and b):       # 显式括号——意图明确
```

**陷阱 3：链式比较与 `in`**

```python
# 链式比较中 in 的行为
>>> "a" in "abc" == True
False
# 解析为：("a" in "abc") and ("abc" == True)
#                   → True         → False
# 结果：False——不直观

# ✅ 不要写出这样的表达式。拆开或加括号。
```

**陷阱 4：`lambda` 的最低优先级**

```python
# lambda 的体止于第一个优先级低于它的运算符——几乎全部都是
>>> f = lambda x: x * 2 + 1    # 体是 x * 2 + 1——OK

# 但条件表达式不是——lambda 优先级低于 if...else
>>> f = lambda x: "even" if x % 2 == 0 else "odd"  # OK，if...else 可以

# 赋值表达式同理——lambda 优先级低于 :=
>>> g = lambda: (x := 5)       # 需要括号——否则被解析为 (lambda: x) := 5
```

### 4.9.3 括号的使用哲学

> **"当有疑问时，加括号。当你不再有疑问时——你可能还是应该加括号。"**

```python
# 少数不需要括号、所有人都一看就懂的惯用写法：
if x and y:
if not items:
for key in d:
value = d.get('k', default)
a, b = b, a

# 其他一切情况——如果表达式包含两种以上不同类型的运算符，加括号
# ✅ 好
result = (a + b) * c
if (flags & MASK) == EXPECTED:
    ...

# ❌ 省下两个字符的代价是读者（包括三个月后的你）的心智负担
result = a + b * c             # 需要心算"* 先于 +"
if flags & MASK == EXPECTED:   # 实际上做的是 flags & (MASK == EXPECTED)
    ...
```

---

## 4.10 运算符重载协议（扩展专题）

Python 的运算符系统本质上是一套**协议**——每种运算符对应特定的魔术方法，由解释器在求值时自动调用。理解并正确实现这些方法，可以让你创建与内置类型行为一致的自定义类型。

### 4.10.1 完整魔术方法速查表

**算术运算符**：

| 运算符 | 正向方法 | 反向方法 | 原地方法 |
|--------|---------|---------|---------|
| `+` | `__add__` | `__radd__` | `__iadd__` |
| `-` | `__sub__` | `__rsub__` | `__isub__` |
| `*` | `__mul__` | `__rmul__` | `__imul__` |
| `/` | `__truediv__` | `__rtruediv__` | `__itruediv__` |
| `//` | `__floordiv__` | `__rfloordiv__` | `__ifloordiv__` |
| `%` | `__mod__` | `__rmod__` | `__imod__` |
| `**` | `__pow__` | `__rpow__` | `__ipow__` |
| `@` | `__matmul__` | `__rmatmul__` | `__imatmul__` |

**一元运算符**：

| 运算符 | 方法 |
|--------|------|
| `-x` | `__neg__` |
| `+x` | `__pos__` |
| `~x` | `__invert__` |
| `abs(x)` | `__abs__` |

**比较运算符**：

| 运算符 | 方法 |
|--------|------|
| `==` | `__eq__` |
| `!=` | `__ne__` |
| `<` | `__lt__` |
| `<=` | `__le__` |
| `>` | `__gt__` |
| `>=` | `__ge__` |

**其他运算符**：

| 运算符 | 方法 |
|--------|------|
| `in` | `__contains__` |

### 4.10.2 反向方法（Reflected Methods）与 `NotImplemented`

反向方法是 Python 运算符协议的精华部分——它允许两种不同类型的对象参与同一次运算，由解释器自动协商调用顺序。

**调用规则**：

```
计算 a OP b 时：

1. 尝试 a.__OP__(b)
2. 如果返回 NotImplemented：
   尝试 b.__ROP__(a)     ← 反向方法——"你有办法处理我吗？"
3. 如果也返回 NotImplemented：
   抛出 TypeError
```

这就是为什么 `3.0 + 5` 能正常工作——`float.__add__` 遇到 `int` 时不知道怎么处理（严格来说可以处理但先返回 NotImplemented），Python 转而调用 `int.__radd__(float)`，`int` 知道如何将自身提升为 `float` 后相加。

```python
# 正确的反向方法实现模式
class Vector2D:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        if isinstance(other, tuple) and len(other) == 2:
            return Vector2D(self.x + other[0], self.y + other[1])
        return NotImplemented    # ← 关键：告诉 Python "我处理不了，换手"

    def __radd__(self, other):
        # 反向方法——当 other.__add__ 返回 NotImplemented 时被调用
        # 通常可以委托给 __add__
        if isinstance(other, tuple) and len(other) == 2:
            return Vector2D(self.x + other[0], self.y + other[1])
        return NotImplemented

    def __repr__(self):
        return f"Vector2D({self.x}, {self.y})"

# 使用
>>> v = Vector2D(1, 2)
>>> v + Vector2D(3, 4)     # Vector2D(4, 6)——正向
>>> v + (3, 4)              # Vector2D(4, 6)——正向，__add__ 处理了 tuple
>>> (3, 4) + v              # Vector2D(4, 6)——反向！
                             # tuple.__add__ 返回 NotImplemented
                             # Python 转而调用 Vector2D.__radd__
```

### 4.10.3 实战：一个完整的可运算类型

```python
import math
from functools import total_ordering

@total_ordering
class Vector2D:
    """支持所有算术和比较运算符的二维向量。"""

    __slots__ = ('x', 'y')    # 节省内存——禁止实例字典

    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    # ── 表示 ──
    def __repr__(self):
        return f"Vector2D({self.x!r}, {self.y!r})"

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __abs__(self):
        """向量长度（模）"""
        return math.hypot(self.x, self.y)

    # ── 一元运算符 ──
    def __neg__(self):
        return Vector2D(-self.x, -self.y)

    def __pos__(self):
        return Vector2D(+self.x, +self.y)

    # ── 算术——正向方法 ──
    def _validate_operand(self, other):
        """将 other 标准化为 (x, y) 对，或返回 NotImplemented。"""
        if isinstance(other, Vector2D):
            return (other.x, other.y)
        if isinstance(other, (int, float)):
            return (float(other), float(other))    # 标量广播
        if isinstance(other, tuple) and len(other) == 2:
            return (float(other[0]), float(other[1]))
        return NotImplemented

    def __add__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        return Vector2D(self.x + validated[0], self.y + validated[1])

    def __sub__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        return Vector2D(self.x - validated[0], self.y - validated[1])

    def __mul__(self, other):
        """标量乘法：Vector2D * scalar"""
        if isinstance(other, (int, float)):
            return Vector2D(self.x * other, self.y * other)
        return NotImplemented

    def __truediv__(self, other):
        """标量除法：Vector2D / scalar"""
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("division by zero")
            return Vector2D(self.x / other, self.y / other)
        return NotImplemented

    # ── 反向方法（处理左侧操作数不支持 Vector2D 的情况）──
    def __radd__(self, other):
        return self.__add__(other)    # 加法可交换

    def __rsub__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        return Vector2D(validated[0] - self.x, validated[1] - self.y)

    def __rmul__(self, other):
        return self.__mul__(other)    # 标量乘法可交换

    # ── 原地运算符（返回 self 以避免不必要的对象创建）──
    def __iadd__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        self.x += validated[0]
        self.y += validated[1]
        return self

    def __isub__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        self.x -= validated[0]
        self.y -= validated[1]
        return self

    def __imul__(self, other):
        if isinstance(other, (int, float)):
            self.x *= other
            self.y *= other
            return self
        return NotImplemented

    # ── 比较（只需 __eq__ 和 __lt__，@total_ordering 补全其余）──
    def __eq__(self, other):
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        return self.x == validated[0] and self.y == validated[1]

    def __lt__(self, other):
        """按向量长度比较"""
        validated = self._validate_operand(other)
        if validated is NotImplemented:
            return NotImplemented
        return abs(self) < math.hypot(validated[0], validated[1])

    def __hash__(self):
        return hash((self.x, self.y))


# ── 使用演示 ──
>>> v1 = Vector2D(3, 4)
>>> v2 = Vector2D(1, 2)

# 算术
>>> v1 + v2                  # Vector2D(4.0, 6.0)
>>> v1 - v2                  # Vector2D(2.0, 2.0)
>>> v1 * 2                   # Vector2D(6.0, 8.0)
>>> v1 / 2                   # Vector2D(1.5, 2.0)

# 一元
>>> -v1                      # Vector2D(-3.0, -4.0)
>>> abs(v1)                  # 5.0

# 与其他类型混合
>>> v1 + (1, 2)              # Vector2D(4.0, 6.0)
>>> (1, 2) + v1              # Vector2D(4.0, 6.0)——反向方法

# 比较（按长度）
>>> v1 > v2                  # True——5.0 > 2.236

# 原地操作
>>> v1 += (1, 0)
>>> v1                       # Vector2D(4.0, 4.0)
```

**实现运算符重载的核心原则总结**：

1. **能处理则返回有效结果，不能处理则返回 `NotImplemented`**（而非抛出异常或返回 `False`）
2. **原地方法（`__i*__`）返回 `self`**——方便链式调用，且避免不必要的对象创建
3. **`__radd__` 等反向方法通常委托给正向方法**——反之则需要小心不对称性
4. **使用 `isinstance` 做类型检查**——不要用 `type()` 精确匹配，这会阻断继承
5. **运算符应返回新对象**（除非是原地运算符）——保持不可变语义

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 算术运算符 | `/` 始终返回 float；`//` 向负无穷取整；`%` 取模结果与除数同号；`**` 右结合；`@` 矩阵乘（Python 3.5+） |
| 比较运算符 | 链式比较只求值中间表达式一次；`NotImplemented` 触发反向方法协商；不同类型间 `==` 不抛异常 |
| 身份运算符 | `is` 比较内存地址（`id()`）；小整数 -5~256 被内部化；与 `None` 比较永远用 `is` |
| 逻辑运算符 | 短路求值；`and`/`or` 返回操作数本身（非 True/False）；`not` 始终返回 bool |
| 位运算符 | `~x = -x - 1`；位移用作快速乘除 2^n；位掩码实现权限系统；位运算符优先级**低于**比较运算符 |
| 成员运算符 | `in` 调用 `__contains__`；不同容器 O(1)~O(n)；`for` 中的 `in` 不是运算符 |
| 增强赋值 | `x += y` 先尝试 `__iadd__`，失败则退化为 `x = x + y`；可变对象原地修改，不可变对象创建新对象 |
| 赋值表达式 | `:=` 在表达式内赋值并返回；3.8+；黄金场景：while、if 中间值、列表推导；不可滥用 |
| 优先级 | 完整 15 级；位运算 < 比较运算是最常见的坑；有疑问就加括号 |
| 运算符重载 | 正向/反向/原地三类魔术方法；`NotImplemented` 启动反向协商；`@total_ordering` 自动补全比较方法 |

---

#### 练习 4

1. **地板除与取模**：写出以下表达式的计算结果并解释原因。
   ```python
   -17 // 5
   -17 % 5
   17 // -5
   17 % -5
   ```
   验证 `a = b * (a // b) + (a % b)` 对上述每一组都成立。

2. **链式比较 vs 短路**：下面两种写法等价吗？
   ```python
   # 写法 A
   0 < x < 10

   # 写法 B
   0 < x and x < 10
   ```
   如果 `x` 是一个有副作用的函数调用 `get_x()`，两者行为有什么不同？设计一个实验验证。

3. **位运算权限系统**：用位掩码实现一个 Unix 文件权限系统（读=4, 写=2, 执行=1）。要求：
   - 用位运算实现权限的设置、清除、检查、切换（toggle）
   - 写一个辅助函数 `format_perms(mode: int) -> str`，输出如 `"rwx"` 或 `"r-x"` 的格式

4. **逻辑运算符返回值**：写出下列表达式的返回值，并解释每步的短路行为。
   ```python
   [] and 3
   0 or "result"
   "a" and "b" and "c"
   0 or [] or {}
   True and False or True   # 提示：注意优先级
   ```

5. **`in` 的性能**：给定一个包含 100 万个随机整数的列表，你需要反复检查任意整数是否在列表中。如何优化？写出优化前后的代码，并用 `timeit` 对比性能。

6. **`==` vs `is`**：以下代码在 CPython 中的输出是什么？如果换成 PyPy 或 Jython 呢？解释原因。
   ```python
   a = 256
   b = 256
   print(a is b)

   a = 257
   b = 257
   print(a is b)

   a = "hello"
   b = "hello"
   print(a is b)

   a = "hello world!"
   b = "hello world!"
   print(a is b)
   ```

7. **增强赋值陷阱**：写出以下代码的输出，解释每一步发生了什么。
   ```python
   # 第一组
   a = [1, 2, 3]
   b = a
   a = a + [4, 5]
   print(a, b, a is b)

   # 第二组
   c = [1, 2, 3]
   d = c
   c += [4, 5]
   print(c, d, c is d)

   # 第三组
   e = (1, 2, [3, 4])
   try:
       e[2] += [5, 6]
   except TypeError as ex:
       print(f"Error: {ex}")
   print(e)
   ```

8. **运算符重载**：实现一个 `Money` 类，支持以下运算：
   - `money1 + money2`（相同币种才能相加，不同币种抛 `ValueError`）
   - `money * n` 和 `n * money`（标量乘法）
   - `money / n`（分配为等额）
   - 比较运算符（按金额比较，忽略币种）
   - `abs(money)` 返回金额的绝对值
   ```python
   # 使用示例
   m1 = Money(100, "USD")
   m2 = Money(50, "USD")
   m3 = m1 + m2    # Money(150, "USD")
   m4 = m1 * 3     # Money(300, "USD")
   m5 = m1 / 2     # Money(50, "USD")
   ```

9. **位运算符优先级陷阱**：找出以下代码中的 bug 并修复。
   ```python
   READ = 1
   WRITE = 2

   def check_permission(flags, expected):
       return flags & expected == expected   # 有 bug 吗？

   # 测试
   print(check_permission(3, READ))    # 期望 True
   print(check_permission(2, READ))    # 期望 False
   ```

10. **海象运算符实战**：用海象运算符 `:=` 重写以下代码，使其更简洁而不失可读性。
    ```python
    # (a) 逐行读取文件直到空行
    with open("data.txt") as f:
        line = f.readline().strip()
        while line:
            process(line)
            line = f.readline().strip()

    # (b) 正则匹配并提取
    import re
    pattern = re.compile(r'^(\w+) = (.+)$')
    for line in config_lines:
        m = pattern.match(line)
        if m and m.group(1) != 'ignore':
            config[m.group(1)] = m.group(2)
    ```

---

**进入下一章的准备**：
- ✅ 能解释 `//` 和 `%` 的负数行为，知道为什么 Python 选择向负无穷取整
- ✅ 理解链式比较的"只求值一次"保证
- ✅ 绝不依赖 interning 做相等性判断
- ✅ 理解 `and`/`or` 返回操作数本身而非 True/False
- ✅ 能使用位掩码实现标志位
- ✅ 理解 `x += y` 和 `x = x + y` 对可变对象的语义差异
- ✅ 知道位运算符优先级低于比较运算符（`flags & mask == mask` 是个 bug）
- ✅ 能正确实现 `__add__`/`__radd__`/`__iadd__` 并返回 `NotImplemented`
