# 第3章 标准数据类型

> **学习目标**：深入理解 Python 内置数据类型的底层行为、方法体系和最佳实践，拒绝"见名知意"的浅层认知。

---

## 3.1 数字类型

Python 提供四种核心数字类型，它们构成了一切数值计算的基础。

### 3.1.1 类型概览与构造函数签名

Python 的内置类型看起来简单，但它们的构造函数都有多组重载——理解这些重载能让你写出更简洁、更高效的代码。

| 类型 | 构造函数 | 字面量示例 | 底层 | 可变性 |
|------|---------|-----------|------|--------|
| `int` | `int()` | `42`, `-7`, `0b1010`, `0o755`, `0xFF` | 无限精度 | 不可变 |
| `float` | `float()` | `3.14`, `-2.5e-3`, `inf`, `nan` | IEEE 754 双精度 | 不可变 |
| `complex` | `complex()` | `1+2j`, `3-4j` | 双浮点（实部+虚部） | 不可变 |
| `bool` | `bool()` | `True`, `False` | `int` 子类 | 不可变 |

**关键事实**：`bool` 是 `int` 的子类——`True == 1` 且 `False == 0`，但 `True is 1` 为 `False`。这在类型检查时可能引发意外行为。

#### 构造函数签名详解

构造函数是理解一个类型的第一扇门。这里给出四个核心数值类型的完整签名。

**`int()`** — 三种构造模式：

```
int(x=0)
int(x, base=10)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x` | `int \| float \| str \| bytes \| bytearray` | `0` | 要转换的数值/字符串；省略则返回 `0` |
| `base` | `int` | `10` | 进制（2–36），仅在 `x` 为 `str`/`bytes` 时有效 |

```python
# 模式 1：从数值转换（截断，非四舍五入）
>>> int(3.99)           # 3
>>> int(-3.99)          # -3

# 模式 2：从字符串 + 进制解析
>>> int("42")           # 42  （base 默认为 10）
>>> int("FF", 16)       # 255  （十六进制）
>>> int("1010", 2)      # 10   （二进制）
>>> int("0xff", 0)      # 255  （base=0 时从字面量前缀自动推断：0x→16, 0o→8, 0b→2）

# 模式 3：无参数——返回 0
>>> int()               # 0
```

> **`base=0` 的妙用**：传 `base=0` 时，Python 从字符串前缀自动推断进制——`"0x"` 为 16 进制，`"0o"` 为 8 进制，`"0b"` 为 2 进制，无前缀为 10 进制。这在解析用户输入或配置文件时尤其方便。

**`float()`** — 两种构造模式：

```
float(x=0.0)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `x` | `int | float | str | bytes | bytearray` | 要转换的数值或字符串；省略返回 `0.0` |

```python
>>> float(42)               # 42.0
>>> float("3.14")           # 3.14
>>> float("-2.5e-3")        # -0.0025  （自动 trim，支持科学计数法）
>>> float("inf")            # inf      （无穷大）
>>> float("-inf")           # -inf
>>> float("nan")            # nan
>>> float()                 # 0.0
```

**`complex()`** — 三种构造模式：

```
complex(real=0, imag=0)
complex(string)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `real` | `int | float | str` | `0` | 实部；如果传字符串则整体解析 |
| `imag` | `int | float` | `0` | 虚部（不能与字符串同时使用） |

```python
# 模式 1：分别指定实部和虚部
>>> complex(3, 4)           # (3+4j)
>>> complex(3.0)            # (3+0j)——imag 默认为 0

# 模式 2：从字符串解析（注意：字符串中不能有空格！）
>>> complex("3+4j")         # (3+4j)
>>> complex("1j")           # 1j

# ❌ 常见错误：字符串中包含空格
>>> complex("3 + 4j")       # ValueError

# 模式 3：无参数
>>> complex()               # 0j
```

> **`complex()` 与 `real`+`imag` 的区别**：`complex(3, 4)` 和 `complex("3+4j")` 结果相同，但前者不涉及字符串解析。当 `real` 参数是字符串时，`imag` 参数必须省略——这是常见的使用陷阱。

**`bool()`**：

```
bool(x=False)
```

`bool(x)` 调用 `x.__bool__()`，若未定义则回退到 `x.__len__()`，两者都没有则返回 `True`。详见 4.4.3 节（逻辑运算符）的真值测试规则。

```python
>>> issubclass(bool, int)
True
>>> isinstance(True, int)
True
>>> True + True          # bool 是 int 子类，True == 1，所以结果是 2
2
>>> ['no', 'yes'][True]  # True 被当作索引 1
'yes'
```

### 3.1.2 整数：无限精度与字面量表示

Python 3 的 `int` 是任意精度整数——仅受内存限制。这使得大数运算不需要特殊库。

```python
>>> 2 ** 1000
10715086071862673209484250490600018105614048117055336074437
50388370351051124936122493198378815695858127594672917553146
82518714528569231404359845775746985748039345677748242309854
21074605062371141877954182153046474983581941267398767559165
54394607706291457119647768654216766042983165262438683720566
8069376
```

**字面量前缀**：

```python
0b1010    # 二进制 → 10
0o755     # 八进制 → 493
0xFF      # 十六进制 → 255
```

使用 `_` 分隔数字提高可读性（Python 3.6+）：

```python
1_000_000       # 一百万
0xDEAD_BEEF     # 十六进制
0b0100_1010     # 二进制
```

**整数方法**：整数虽然是不可变类型，但拥有少量方法：

```python
>>> (42).bit_length()     # 二进制表示的位数
6
>>> int.bit_count(42)     # 二进制中 1 的个数（Python 3.8+）
3
>>> (42).to_bytes(2, 'big')
b'\x00*'
>>> int.from_bytes(b'\x00*', 'big')
42
```

### 3.1.3 浮点数：IEEE 754 的真相

`float` 是 IEEE 754 双精度浮点数——53 位尾数，提供约 15-17 位十进制精度。

**精度陷阱**：

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> 0.1 + 0.2 == 0.3
False
```

这不是 Python 的 bug，而是二进制浮点表示的根本限制。处理精确小数时使用 `decimal` 模块或整数化（如以分为单位存钱）。

**特殊值**：

```python
float('inf')      # 正无穷
float('-inf')     # 负无穷
float('nan')      # 非数值 (Not a Number)
```

`nan` 的特殊性——它与任何值比较都返回 `False`，包括自身：

```python
>>> nan = float('nan')
>>> nan == nan
False
>>> nan is nan    # 但对象身份相同
True
```

使用 `math.isnan()` 做正确判断。

**浮点数方法**：

```python
>>> (3.14159).hex()          # 十六进制表示
'0x1.921f9f01b866ep+1'
>>> float.fromhex('0x1.921f9f01b866ep+1')
3.14159
>>> (3.14159).as_integer_ratio()  # 精确分数近似
(3537115888337719, 1125899906842624)
>>> (3.14159).is_integer()
False
```

### 3.1.4 复数

`complex` 类型由实部和虚部组成，均为 `float`。

```python
>>> c = 3 + 4j
>>> c.real, c.imag
(3.0, 4.0)
>>> c.conjugate()
(3-4j)
>>> abs(c)                    # 模 |z| = sqrt(a² + b²)
5.0
```

Python 原生支持复数运算，包括 `cmath` 模块提供复数的三角函数、对数等。

### 3.1.5 布尔类型

`bool` 实例只有两个：`True` 和 `False`，是单例（singleton）。

**真值测试**：以下值在布尔上下文中被视为 `False`：

| 值 | 类型 |
|----|------|
| `False` | bool |
| `0`, `0.0`, `0j` | 零值 |
| `''`, `""` | 空字符串 |
| `[]`, `()`, `{}`, `set()` | 空容器 |
| `None` | 空值 |
| 自定义类的 `__bool__` 或 `__len__` 返回 0/False | 用户定义 |

其余所有对象视为 `True`。

```python
# 常见陷阱：包含空容器的容器是真值
>>> bool([[]])
True
```

### 3.1.6 类型转换

```python
int("42")           # str → int     "42" → 42
int("FF", 16)       # hex → int     FF₁₆ → 255
int(3.99)           # float → int   (截断，非四舍五入) → 3
float(42)           # int → float   42 → 42.0
float("3.14")       # str → float   "3.14" → 3.14
complex(3, 4)       # 实部, 虚部 → 3+4j
str(42)             # int → str     "42"
repr(0.1)           # float → str  "0.1"
hex(255)            # int → hex str "0xff"
oct(64)             # int → oct str "0o100"
bin(10)             # int → bin str "0b1010"
bool(42)            # → True
bool(0)             # → False
```

**隐式转换**：Python 在混合类型运算中自动转换：

```python
>>> type(1 + 2.0)           # int + float → float
<class 'float'>
>>> type(True + 1)          # bool + int → int
<class 'int'>
>>> type(3 + 4j + 5.0)     # complex + float → complex
<class 'complex'>
```

转换规则：`bool < int < float < complex`。运算结果取"最高"类型。

### 3.1.7 数值运算符

```python
# 算术
+ - * /      # 加减乘除（/ 始终返回 float）
//           # 整除（向下取整）  7 // 2 → 3,  -7 // 2 → -4
%            # 取模              7 % 2 → 1
**           # 幂运算            2 ** 10 → 1024
- (+)        # 单目负号/正号

# 位运算（仅 int）
&            # 按位与            0b1100 & 0b1010 → 0b1000
|            # 按位或            0b1100 | 0b1010 → 0b1110
^            # 按位异或          0b1100 ^ 0b1010 → 0b0110
~            # 按位取反          ~0b1100 → -13（补码！）
<<           # 左移              1 << 3 → 8
>>           # 右移              8 >> 2 → 2

# 增强赋值
+= -= *= /= //= %= **= &= |= ^= <<= >>=
```

**整除的陷阱**：`//` 是**向下取整**，不是"向零截断"：

```python
>>> 7 // 2
3
>>> -7 // 2
-4          # -3.5 向下 → -4，不是 -3
```

如需向零截断，使用 `int(a / b)`。

**`//` 与 `%` 的关系**：`a = b * (a // b) + (a % b)` 始终成立。

### 3.1.8 内置数值函数

```python
abs(x)              # 绝对值
round(x, ndigits)   # 四舍五入（银行家舍入！）
pow(x, y, mod)      # x**y % mod，高效模幂
divmod(a, b)        # 返回 (a // b, a % b)
max(iterable)       # 最大值
min(iterable)       # 最小值
sum(iterable, start)# 求和
complex(real, imag) # 构造函数
```

**`round()` 的银行家舍入**：

```python
>>> round(2.5)      # 向偶数舍入
2
>>> round(3.5)
4
>>> round(1.235, 2) # 注意：这也不精确
1.24                # 实际上是 1.235 在二进制中不是精确值
```

**`pow()` 的模参数**：当提供第三个参数时，使用快速模幂算法：

```python
>>> pow(2, 1000000, 1000)   # 比 (2**1000000) % 1000 快得多
376
```

### 3.1.9 `math` 模块精要

```python
import math

math.pi, math.e, math.tau, math.inf, math.nan
math.ceil(3.2)          # 4    向上取整
math.floor(3.8)         # 3    向下取整
math.trunc(-3.8)        # -3   向零截断
math.isclose(a, b)      # 浮点近似比较（推荐！）
math.isnan(x)           # 判断 NaN
math.isinf(x)           # 判断无穷
math.gcd(12, 8)         # 4    最大公约数
math.lcm(12, 8)         # 24   最小公倍数（3.9+）
math.comb(5, 2)         # 10   组合数 C(5,2)
math.perm(5, 3)         # 60   排列数 P(5,3)
math.sqrt(16)           # 4.0
math.log(8, 2)          # 3.0  log₂8
math.log2(8)            # 3.0
math.degrees(math.pi)   # 180.0
math.radians(180)       # 3.14159...
math.sin/cos/tan(x)     # 三角函数
math.factorial(5)       # 120
math.prod([1,2,3,4,5])  # 120  （3.8+）
```

> **实战建议**：永远用 `math.isclose()` 而不是 `==` 比较浮点数。默认 `rel_tol=1e-9` 足以应对大多数情况。

#### 练习 3.1

1. 计算 `2**100` 的十进制位数（提示：用 `len(str(...))`）。
2. 解释为什么 `0.1 + 0.2 == 0.3` 返回 `False`，并写出用 `math.isclose()` 的正确比较方式。
3. 写出 `-7 // 2` 和 `-7 % 2` 的结果，并验证 `a = b * (a // b) + (a % b)` 是否成立。
4. 用 `round()` 分别对 `2.5` 和 `3.5` 取整，解释为什么结果不同。
5. 将十进制数 `255` 分别转换为二进制、八进制、十六进制字符串表示。

---

## 3.2 字符串

在 Python 中，字符串是一切文本处理的核心。`str` 是不可变的 Unicode 字符序列。

### 3.2.0 `str()` 构造函数签名

`str()` 是 Python 中最频繁调用的内置函数之一，它的多重重载覆盖了各种"转字符串"场景：

```
str()
str(object='')
str(object, encoding='utf-8', errors='strict')
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `object` | `Any` | `''` | 要转换的对象（省略时返回空串 `""`） |
| `encoding` | `str` | `'utf-8'` | 仅当 `object` 为 `bytes`/`bytearray` 时使用，指定解码编码 |
| `errors` | `str` | `'strict'` | 解码错误处理：`'strict'`（抛错）、`'ignore'`（静默跳过）、`'replace'`（替换为 `�`） |

```python
# 模式 1：无参数——返回空字符串
>>> str()                        # ""

# 模式 2：任意对象 → 字符串（调用 object.__str__() 或 object.__repr__()）
>>> str(42)                      # "42"
>>> str(3.14)                    # "3.14"
>>> str([1, 2, 3])              # "[1, 2, 3]"
>>> str(None)                    # "None"

# 模式 3：bytes + 编码 → 字符串（解码）
>>> str(b"hello", "utf-8")       # "hello"
>>> str(b"\xff", "utf-8", "replace")   # "�"（非法字节被替换）
```

> **调用链**：`str(obj)` 首先调用 `obj.__str__()`；如果未定义，回退到 `obj.__repr__()`；如果均未定义，继承自 `object` 的 `__repr__` 返回形如 `<__main__.Foo object at 0x...>` 的默认字符串。

### 3.2.1 字面量与引号

```python
'单引号'
"双引号"
'''三单引号
   可跨行'''
"""三双引号
   可跨行"""
```

**选择引号的策略**：
- 任选单引号或双引号，在项目中保持一致即可
- 字符串内含双引号时，用 `'单引号包含"双引号"'`
- 字符串内含单引号时，用 `"双引号包含'单引号'"`
- 文档字符串（docstring）始终用 `"""三双引号"""`

### 3.2.2 转义序列与原始字符串

```python
\\          # 反斜杠本身
\'          # 单引号
\"          # 双引号
\n          # 换行 LF
\r          # 回车 CR
\r\n        # Windows 换行
\t          # 制表符 Tab
\b          # 退格
\f          # 换页
\v          # 垂直制表
\0          # 空字符
\x41        # 十六进制字符 'A'
\u0041      # 16 位 Unicode 'A'
\U00000041  # 32 位 Unicode 'A'
\N{GREEK SMALL LETTER ALPHA}  # Unicode 名称
```

**原始字符串** `r"..."` 不处理转义序列，尤其适用于正则表达式和 Windows 路径：

```python
>>> print("C:\new_folder\temp")    # 灾难
C:
ew_folder       emp

>>> print(r"C:\new_folder\temp")   # 正确
C:\new_folder\temp
```

> **注意**：原始字符串也不能以奇数个反斜杠结尾。`r"hello\"` 会语法错误。解决：`r"hello" + "\\"` 或不用原始字符串。

### 3.2.3 字符串的不可变性

```python
>>> s = "hello"
>>> s[0] = "H"
TypeError: 'str' object does not support item assignment
```

所有字符串"修改"操作都返回**新字符串**。原地修改不存在。

### 3.2.4 字符串格式化：三种方式

#### 3.2.4.1 f-string（Python 3.6+，推荐）

这是目前最强大、最可读的格式化方式：

```python
name = "Alice"
age = 25

# 基本插值
f"Hello, {name}. You are {age} years old."

# 表达式
f"Next year: {age + 1}"
f"Is adult: {age >= 18}"

# 内联函数调用
f"Name length: {len(name)}"
f"PI: {math.pi:.4f}"                     # 精度 → "3.1416"

# 格式说明符
f"{42:5d}"                                # 右对齐 5 列 → "   42"
f"{42:<5d}"                               # 左对齐     → "42   "
f"{42:05d}"                               # 零填充     → "00042"
f"{255:#x}"                               # 带前缀十六进制 → "0xff"
f"{0.1234:.2%}"                           # 百分比 → "12.34%"
f"{1000000:,}"                            # 千位分隔 → "1,000,000"
f"{3.14159265:.3f}"                       # 浮点精度
f"{42:b}"                                 # 二进制 → "101010"

# datetime 直接格式化
from datetime import datetime
f"{datetime.now():%Y-%m-%d %H:%M:%S}"

# 多行 f-string
f"""
Name:   {name}
Age:    {age:>3d}
Status: {'Adult' if age >= 18 else 'Minor'}
"""

# 使用 !r 获取 repr, !s 获取 str, !a 获取 ascii
f"value: {name!r}"                        # → "value: 'Alice'"

# = 说明符（Python 3.8+）：同时输出表达式和值（调试利器）
f"{age + 1 = }"                           # → "age + 1 = 26"
```

**f-string 的限制**：
- 不能包含反斜杠 `\`（表达式内部也不行）
- 不能用于动态格式模板——用 `str.format()` 代替

#### 3.2.4.2 `str.format()`

```python
# 位置参数
"{} + {} = {}".format(2, 3, 5)            # "2 + 3 = 5"

# 显式索引
"{0} + {1} = {2}".format(2, 3, 5)

# 命名参数（推荐）
"Hello, {name}. Score: {score:.1f}".format(name="Bob", score=95.5)

# 字典解包
data = {"name": "Carol", "age": 30}
"{name} is {age}".format(**data)

# 属性访问
from collections import namedtuple
Point = namedtuple('Point', 'x y')
"{0.x}, {0.y}".format(Point(1, 2))

# 对齐与填充
"{:*^20}".format("center")                # "*******center*******" 剩余位数为奇数时，左侧少1个符号
"{:->10}".format("123")                   # "-------123"
"{:-<10}".format("123")                   # "123-------"
```

#### 3.2.4.3 `%` 运算符（旧式，不推荐新代码）

```python
"Hello, %s. Value: %.2f" % ("World", 3.14)
```

存在安全隐患（不支持对象属性访问、元组歧义），新项目避免使用。

### 3.2.5 字符串方法：分类精讲

#### 搜索与定位

**`str.find()` 和 `str.index()` 方法签名**：

```
s.find(sub)
s.find(sub, start)
s.find(sub, start, end)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sub` | `str` | — | 要搜索的子串 |
| `start` | `int` | `0` | 搜索的起始索引（包含） |
| `end` | `int` | `len(s)` | 搜索的结束索引（不包含） |

`index()` 签名与 `find()` 完全相同——唯一区别在失败行为：`find()` 返回 `-1`，`index()` 抛 `ValueError`。

```python
s.find(sub, start, end)     # 返回首次出现索引，未找到 -1
s.rfind(sub)                # 从右搜索
s.index(sub)                # 同 find，但未找到抛 ValueError
s.rindex(sub)
s.count(sub)                # 子串出现次数（非重叠）
```

**`find` vs `index`**：两者定位相同，区别在失败行为。优先用 `find`——返回 `-1` 比异常更易处理。

```python
>>> "hello world".find("z")     # -1（安全）
>>> "hello world".index("z")    # ValueError!
```

**`count` 的非重叠特性**：

```python
>>> "aaaa".count("aa")
2            # 重叠的 "aa" 只计一次？不对——是非重叠扫描的结果
```

#### 检查与判断

```python
s.startswith(prefix)        # 是否以 prefix 开头（接受 tuple!）
s.endswith(suffix)          # 是否以 suffix 结尾
s.isalpha()                 # 全字母？
s.isdigit()                 # 全数字？（仅 0-9）
s.isdecimal()               # 全十进制数字？（Unicode 通用类别 Nd，更严格）
s.isnumeric()               # 全数值？（含罗马数字、全角数字等，最宽）
s.isalnum()                 # 全字母数字？
s.isspace()                 # 全空白字符？
s.islower() / s.isupper()   # 全小写/全大写？
s.istitle()                 # 标题格式？
s.isascii()                 # 全 ASCII？（3.7+）
s.isidentifier()            # 合法标识符？
s.isprintable()             # 全可打印字符？
```

**`isdigit` vs `isdecimal` vs `isnumeric` 区别**：

| 方法 | `"123"` | `"²"` | `"½"` | `"四"` | `"١"`(阿拉伯) |
|------|---------|-------|-------|-------|-------------|
| `isdecimal()` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `isdigit()` | ✅ | ✅ | ❌ | ❌ | ✅ |
| `isnumeric()` | ✅ | ✅ | ✅ | ✅ | ✅ |

**`startswith` 接受元组**（`endswith` 同理）：

```python
>>> filename = "report.pdf"
>>> filename.endswith((".pdf", ".docx", ".xlsx"))
True
```

但 **不接受 list**。这是一个常见的面试陷阱。

#### 大小写变换

```python
s.upper()           # 全大写
s.lower()           # 全小写
s.capitalize()      # 首字母大写，其余全小写
s.title()           # 每个单词首字母大写
s.swapcase()        # 大小写翻转
s.casefold()        # 激进小写（比 lower 更强，适合不区分大小写的比较）
```

**`casefold` vs `lower`**：

```python
>>> "Straße".lower()           # "straße"
>>> "Straße".casefold()        # "strasse" — ß 展开为 ss，用于匹配更安全
```

> **实战建议**：做不区分大小写的字符串比较时，用 `s.casefold()` 代替 `s.lower()`。

#### 修剪与填充

**`str.strip()` 方法签名**：

```
s.strip()
s.strip(chars)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `chars` | `str | None` | `None` | 要从两端删除的**字符集合**（非子串！）；为 `None` 时删除所有 ASCII 空白字符（空格、`\t`、`\n`、`\r` 等） |

```python
s.strip(chars)      # 去除两侧指定字符（默认空白）
s.lstrip(chars)     # 只去左侧
s.rstrip(chars)     # 只去右侧
s.zfill(width)      # 零填充左侧到指定宽度
s.center(n, fill)   # 居中
s.ljust(n, fill)    # 左对齐
s.rjust(n, fill)    # 右对齐
```

**`strip` 的字符集行为**（非前缀/后缀匹配）：

```python
>>> "www.example.com/".strip("mocw./")
'example'           # 从两端依次删除任意 m, o, c, w, ., / 字符
```

#### 拆分与连接

**`str.split()` 方法签名**：

```
s.split()
s.split(sep)
s.split(sep, maxsplit)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sep` | `str | None` | `None` | 分隔符；为 `None` 时按任意连续空白字符拆分（且自动去除首尾空白） |
| `maxsplit` | `int` | `-1`（不限） | 最多拆分次数。`rsplit()` 的 `maxsplit` 同理，但从右侧计数 |

```python
s.split(sep, maxsplit)      # 按分隔符拆分 → list
s.rsplit(sep, maxsplit)     # 从右侧拆分
s.splitlines(keepends)      # 按行拆分
s.partition(sep)            # 三部分：(前, 分隔符, 后)
s.rpartition(sep)           # 从右侧分三部分
sep.join(iterable)          # 用 sep 连接可迭代对象 → str
s.removeprefix(pref)        # 移除前缀（3.9+）
s.removesuffix(suf)         # 移除后缀（3.9+）
s.expandtabs(tabsize)       # 展开 Tab
```

**`split` 的特殊行为**：

```python
>>> "a   b  c".split()         # 无参数：连续空白合并
['a', 'b', 'c']

>>> "a   b  c".split(' ')       # 有参数：每个空格都拆分
['a', '', '', 'b', '', 'c']

>>> "a,b,c".rsplit(',', 1)      # 从右侧拆一次
['a,b', 'c']
```

**`partition` 比 `split` 更安全**——始终返回三元组，不抛异常：

```python
>>> "key=value".partition('=')
('key', '=', 'value')

>>> "no-equal".partition('=')
('no-equal', '', '')
```

**`join` 的性能**：如果你需要拼接大量字符串，用 `''.join(list_of_strings)` 而不是循环 `+=`——前者是 O(n)，后者是 O(n²)。

```python
# ❌ 错误：O(n²)
result = ""
for s in large_list:
    result += s

# ✅ 正确：O(n)
result = ''.join(large_list)
```

#### 替换

```python
s.replace(old, new, count)          # 替换子串
s.translate(table)                   # 字符映射替换
str.maketrans(x, y, z)              # 创建转换表
```

**`translate` 的性能优势**：需要多字符替换时，`translate` 比多次 `replace` 快得多：

```python
# 快速删除元音
table = str.maketrans('', '', 'aeiou')
>>> "beautiful".translate(table)
'btfl'

# 字符映射：a→1, e→2, i→3, o→4, u→5
table = str.maketrans('aeiou', '12345')
>>> "beautiful".translate(table)
'b21t3f5l'
```

#### 编码与解码

**`str.encode()` 和 `bytes.decode()` 方法签名**：

```
str.encode(encoding='utf-8', errors='strict')
bytes.decode(encoding='utf-8', errors='strict')
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `encoding` | `str` | `'utf-8'` | 字符编码格式（如 `'utf-8'`、`'gbk'`、`'latin-1'`） |
| `errors` | `str` | `'strict'` | 错误处理策略 |

**`errors` 参数的可选值**：

| 值 | 行为 | 适用场景 |
|------|------|---------|
| `'strict'` | 遇到无法编码/解码的字符时抛 `UnicodeError` | 默认——数据应是干净的 |
| `'ignore'` | 静默跳过无法处理的字符 | 数据清洗——丢弃噪音 |
| `'replace'` | 替换为 `?`（编码）或 `�`（解码） | 数据清洗——保留占位 |
| `'xmlcharrefreplace'` | 替换为 XML 数字字符引用（仅编码） | HTML/XML 输出 |
| `'backslashreplace'` | 替换为 `\uXXXX` 转义序列（仅编码） | 调试/日志 |
| `'surrogateescape'` | 将无效字节编码为代理码点，可无损还原（仅解码） | 操作系统文件名处理 |

```python
>>> "hello".encode('utf-8')                     # b'hello'
>>> "café".encode('utf-8')                      # b'caf\xc3\xa9'
>>> "café".encode('ascii', errors='ignore')     # b'caf'（é 被静默跳过！）
>>> "café".encode('ascii', errors='replace')    # b'caf?'（é 被替换为 ?）
>>> b"caf\xc3\xa9".decode('utf-8')              # 'café'
>>> b"hello".decode('utf-8')                    # 'hello'
```

> **黄金法则**：编码用 `str.encode()`，解码用 `bytes.decode()`。牢记 str 是 Unicode 文本，bytes 是原始字节。

### 3.2.6 字符串的序列行为

因为 `str` 是不可变序列，所以支持索引、切片和常用序列操作（详见 3.3节）：

```python
>>> "Python"[0]         # 'P'  （索引）
>>> "Python"[-1]        # 'n'  （反向索引）
>>> "Python"[2:5]       # 'tho'（切片）
>>> "Python"[::-1]      # 'nohtyP'（反转）
>>> len("Python")       # 6
>>> 'h' in "Python"     # True
>>> 'z' in "Python"     # False
>>> for ch in "Python": print(ch)  # 迭代
```

### 3.2.7 Unicode 与编码常识

```python
ord('A')        # 65   字符 → Unicode 码点
chr(65)         # 'A'  Unicode 码点 → 字符
'\u0041'        # 'A'（仅 BMP 平面）
'\U0001F600'    # '😀'（完整 Unicode）
```

**字符串的内部表示**（CPython 3.3+）：根据实际内容自动选择 1/2/4 字节每字符——对纯 ASCII 文本极省内存。

### 3.2.8 字符串拼接 vs 格式化：无争议结论

```python
# ❌ 不推荐
'Hello, ' + name + '! You are ' + str(age) + ' years old.'

# ✅ f-string（最推荐——可读性、性能兼得）
f'Hello, {name}! You are {age} years old.'

# ✅ join（大量字符串拼接）
'-'.join(items)

# ✅ format（动态模板）
template.format(**data)
```

**f-string 拥有最好的性能**——它在编译时被解析为操作码，比 `+` 和 `%` 都快。

#### 练习 3.2

1. 用三种方式（f-string、`str.format()`、`%` 运算符）格式化输出：`"Hello, Alice. Your score is 95.5."`。
2. 给定字符串 `s = "  Hello, World!  "`，写一行代码将其清理为 `"hello, world"`（去除两端空白 + 全小写）。
3. 写出 `"www.example.com/".strip("mocw./")` 的结果，并解释 `strip` 的参数行为。
4. 用 `split()` 和 `join()` 将一个句子中的单词顺序反转（如 `"Hello World"` → `"World Hello"`）。
5. 解释 `"aaaa".count("aa")` 为什么返回 `2` 而不是 `3`。
6. 用 `str.maketrans()` 和 `translate()` 实现：将字符串中的 `a→1, e→2, i→3, o→4, u→5`，并删除所有空格。

---

## 3.3 序列：列表与元组

序列（sequence）是 Python 最基本的组合类型之一。列表和元组在本质上共享一套序列协议，区别仅在于**可变性**。

### 3.3.1 序列协议

所有序列类型（`str`, `list`, `tuple`, `range`, `bytes`, `bytearray`）支持以下通用操作：

```python
len(seq)            # 长度
seq[i]              # 正向索引（i >= 0）
seq[-i]             # 反向索引（i > 0）
seq[start:stop:step]# 切片
elem in seq         # 成员检查
elem not in seq
for x in seq        # 迭代
min(seq)            # 最小值
max(seq)            # 最大值
seq.count(x)        # 出现次数
seq.index(x)        # 首次索引（找不到抛 ValueError）
```

### 3.3.2 索引与切片（重点）

#### 索引

Python 索引从 0 开始：

```
 0   1   2   3   4   5   6   7   8   9   (正向索引)
 P   y   t   h   o   n   中   文   字   符
-10  -9  -8  -7  -6  -5  -4  -3  -2  -1   (反向索引)
```

```python
>>> s = "Python中文字符"
>>> s[0]        # 'P'
>>> s[6]        # '中'
>>> s[-1]       # '符'
>>> s[-4]       # '中'（注意：中文每个字符占一个索引位）
```

> **越界会抛 `IndexError`**。

#### 切片：`seq[start:stop:step]`

切片返回一个**新对象**（浅拷贝），语法规则：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `start` | `0`（step > 0）或 `-1`（step < 0） | 起始索引（包含） |
| `stop` | 末尾（step > 0）或开头前（step < 0） | 结束索引（不包含） |
| `step` | `1` | 步长 |

```python
>>> lst = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

# 基本切片
>>> lst[2:5]        # [2, 3, 4]   索引 2,3,4（不含 5）
>>> lst[:5]         # [0, 1, 2, 3, 4]   从开头
>>> lst[5:]         # [5, 6, 7, 8, 9]   到结尾
>>> lst[:]          # 完整浅拷贝

# 带步长
>>> lst[::2]        # [0, 2, 4, 6, 8]   每隔一个
>>> lst[1::2]       # [1, 3, 5, 7, 9]   从索引 1 开始每隔一个

# 反向
>>> lst[::-1]       # [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]  反转
>>> lst[8:2:-1]     # [8, 7, 6, 5, 4, 3]    反向步长

# 删除切片（效果等价于 del lst[2:5]）
>>> lst[2:5] = []
```

**切片不会越界**——这是 Python 的设计特性：

```python
>>> [1,2,3][5:10]          # [] 而不是 IndexError
>>> [1,2,3][5:]            # []
>>> [1,2,3][:100]          # [1, 2, 3]
```

**`slice` 对象**：命名切片可用于复用：

```python
>>> EVERY_OTHER = slice(None, None, 2)
>>> lst[EVERY_OTHER]
[0, 2, 4, 6, 8]
>>> s.indices(len(lst))    # 规范化切片边界
(0, 10, 2)
```

### 3.3.3 列表

列表是**可变、有序、可重复**的异构序列。存储为指向对象的指针的动态数组。

#### 创建

**`list()` 构造函数签名**：

```
list()
list(iterable)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `iterable` | `Iterable` | — | 任何可迭代对象（省略时返回空列表） |

`list()` 的行为本质上是对传入的可迭代对象做**热切求值**——它会立即遍历整个可迭代对象，将所有元素收集到一个新的列表对象中。这意味着 `list(range(10**9))` 会尝试分配约 8GB 内存，务必小心。

```python
[]                              # 空列表（最快）
[1, 2, 3]                       # 字面量
list()                          # 构造空列表（同 []）
list("hello")                   # 从可迭代对象 → ['h','e','l','l','o']
list(range(5))                  # 从 range → [0, 1, 2, 3, 4]
list({'a': 1, 'b': 2})         # 从字典（取键）→ ['a', 'b']
[0] * 5                         # [0, 0, 0, 0, 0]  但注意下面这个坑
```

**列表乘法的浅拷贝陷阱**：

```python
>>> row = [0] * 3               # 不可变对象没问题
>>> matrix = [[0] * 3] * 3      # ❌ 三行指向同一个内部列表！
>>> matrix[0][0] = 1
>>> matrix
[[1, 0, 0], [1, 0, 0], [1, 0, 0]]

# ✅ 正确：用推导式
>>> matrix = [[0] * 3 for _ in range(3)]
```

#### 访问与修改

```python
lst[i]          # 索引
lst[i:j]        # 切片（返回新列表）
lst[i] = val    # 赋值单元素
lst[i:j] = seq  # 赋值切片（替换该段）
lst[i:j:k] = seq# 赋值带步长切片（长度必须匹配）
lst.append(x)   # 末尾追加
lst.insert(i, x)# 指定位置插入
lst.extend(it)  # 追加可迭代对象的所有元素
lst.remove(x)   # 删除首次出现的 x（没找到抛 ValueError）
lst.pop(i=-1)   # 删除并返回索引 i（默认最后一个）
lst.clear()     # 清空（同 del lst[:]）
del lst[i]      # 删除索引 i
del lst[i:j]    # 删除切片区间
del lst[i:j:k]  # 删除带步长切片
```

**`append` vs `extend` vs `+=` vs `insert`**：

```python
>>> lst = [1, 2]
>>> lst.append([3, 4])      # 加一个元素 → [1, 2, [3, 4]]
>>> lst = [1, 2]
>>> lst.extend([3, 4])      # 追加每个元素 → [1, 2, 3, 4]
>>> lst += [3, 4]           # 同 extend → [1, 2, 3, 4]
>>> lst = [1, 2]
>>> lst.insert(1, 'x')      # 在索引 1 前插入 → [1, 'x', 2]
```

**`pop()` 是栈操作**：

```python
>>> stack = [1, 2, 3]
>>> stack.pop()             # 3（LIFO 栈顶）
>>> stack.pop(0)            # 1（FIFO 队首，但 O(n)，不建议）
```

#### 排序

**`list.sort()` 方法签名**：

```
lst.sort(*, key=None, reverse=False)
```

**`sorted()` 内置函数签名**：

```
sorted(iterable, *, key=None, reverse=False)
```

两者的参数完全相同——唯一的区别：`sort()` 是**原地排序**（修改自身，返回 `None`），`sorted()` 返回**新列表**（原数据不变）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `iterable` | `Iterable` | — | （仅 `sorted`）要排序的可迭代对象 |
| `key` | `Callable` | `None` | 单参数函数——排序前对每个元素调用一次，按其返回值比较 |
| `reverse` | `bool` | `False` | `True` 时降序排列 |

> 注意 `*` 是 Python 3 的语法标记——`key` 和 `reverse` 必须用**关键字参数**传递，不能按位置传参。

**`sort()` 返回 `None`**——这是一个著名设计选择（令 API 一致——所有原地修改的方法均返回 `None`）：

```python
>>> lst = [3, 1, 2]
>>> result = lst.sort()
>>> print(result)           # None  ← 常见陷阱
>>> print(lst)              # [1, 2, 3]
```

正确用法：

```python
# 如果需要链式调用
result = sorted(lst, reverse=True)      # 返回新列表
```

**`key` 参数**：最常见的自定义排序方式：

```python
>>> words = ['apple', 'Banana', 'cherry', 'date']
>>> sorted(words, key=str.lower)                # 不区分大小写
['apple', 'Banana', 'cherry', 'date']

>>> students = [('Alice', 90), ('Bob', 85)]
>>> sorted(students, key=lambda x: x[1])        # 按成绩
[('Bob', 85), ('Alice', 90)]

>>> from operator import itemgetter
>>> sorted(students, key=itemgetter(1))         # 更快：itemgetter 是 C 实现的
```

**稳定排序**：Python 的排序是稳定的——相等元素的相对位置不变。这一特性允许链式排序：

```python
# 先按年龄降序，再按姓名升序（利用稳定排序：先排次要键，再排主要键）
result = sorted(people, key=lambda p: p.name)
result = sorted(result, key=lambda p: p.age, reverse=True)
```

#### 其他方法

```python
lst.count(x)    # x 出现的次数
lst.index(x, i, j)  # 在 [i, j) 区间首次出现 x 的索引（找不到抛 ValueError）
lst.copy()      # 浅拷贝（同 lst[:]）
```

### 3.3.4 列表推导式

推导式是 Python 的核心语法糖——将循环和过滤压缩到一行：

```python
# 基本形式
[x * 2 for x in range(5)]              # [0, 2, 4, 6, 8]

# 带条件过滤
[x for x in range(10) if x % 2 == 0]   # [0, 2, 4, 6, 8]

# if-else 表达式在左侧时
[x if x % 2 == 0 else -x for x in range(5)]  # [0, -1, 2, -3, 4]

# 嵌套循环（笛卡尔积）
[(x, y) for x in range(2) for y in range(3)]
# [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2)]
```

**推导式 vs `map`/`filter`**：

```python
# 推导式（推荐——可读性更高）
[x * 2 for x in range(10) if x % 2 == 0]

# 等价的功能组合（不推荐——嵌套难以阅读）
list(map(lambda x: x * 2, filter(lambda x: x % 2 == 0, range(10))))
```

> **实战建议**：推导式优于 `map`/`filter`（除非函数已经是 `str.lower` 这类预先存在的可调用对象）。

**Walrus 运算符 (`:=`) 在推导式中**（3.8+）：

```python
# 避免重复计算
[(y := x ** 2) for x in range(10) if y > 25]
# [36, 49, 64, 81]
```

### 3.3.5 元组

元组是**不可变、有序、可重复**的异构序列。

**`tuple()` 构造函数签名**：

```
tuple()
tuple(iterable)
```

与 `list()` 完全对称——对传入的可迭代对象做热切求值，返回一个不可变的元组。

```python
()                  # 空元组（最快）
(1,)                # 单元素——逗号是关键！（不是括号）
(1, 2, 3)           # 多元素
1, 2, 3             # 括号可省略（打包）
tuple()             # 构造空元组
tuple([1, 2, 3])    # 从可迭代对象构造
tuple("hello")      # ('h', 'e', 'l', 'l', 'o')
```

**单元素元组的陷阱**：必须保留逗号：

```python
>>> type((1))
<class 'int'>       # 这是括号包裹的整数，不是元组！

>>> type((1,))
<class 'tuple'>     # 这才是元组
```

#### 不可变性的含义

元组本身的**结构**不可变，但**元素指向的对象**可能可变：

```python
>>> t = ([1, 2], [3, 4])
>>> t[0].append(5)          # 允许！修改的是列表对象，不是元组结构
>>> t
([1, 2, 5], [3, 4])

>>> t[0] = [7, 8]           # ❌ 不允许！修改元组结构
TypeError: 'tuple' object does not support item assignment
```

#### 序列解包

```python
a, b = (1, 2)               # 元组解包
a, b = [1, 2]               # 也可用于列表
a, *rest = [1, 2, 3, 4]     # * 收集剩余元素（3.0+）
first, *_, last = range(10) # _ 约定为"不关心"

# 交换变量（无临时变量）
a, b = b, a                 # Python 风格！

# 函数返回多值
def divmod_alt(a, b):
    return a // b, a % b
quotient, remainder = divmod_alt(10, 3)
```

#### `namedtuple`：自文档元组

当元组的含义需要名字而非索引表达时，用 `namedtuple`：

```python
from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])
p = Point(3, 4)
p.x, p.y            # 3, 4    （用属性访问）
p[0], p[1]          # 3, 4    （也可用索引）
p._asdict()         # {'x': 3, 'y': 4}  → OrderedDict

# 数据类风格（Python 3.7+）
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

与全功能类的对比：`namedtuple` 内存占用与普通元组相同（无 `__dict__`），适合大量小对象。

#### 元组方法

```python
t.count(x)      # x 出现次数
t.index(x)      # x 首次索引位置
```

仅此两个——因为不可变性，无需 `append`、`sort` 等方法。

### 3.3.6 `range`：惰性数值序列

`range` 表示一个**不可变**的等差数列——它不存储所有值，而是按需计算。无论表示多大范围，内存占用始终恒定（48 字节左右）。

#### 创建

**`range()` 构造函数签名**——三种调用形式：

```
range(stop)
range(start, stop)
range(start, stop, step)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start` | `int` | `0` | 起始值（包含） |
| `stop` | `int` | —（必填*） | 结束值（不包含） |
| `step` | `int` | `1` | 步长（不能为 0） |

> \* 仅传入一个参数时，它被解释为 `stop`（此时 `start` 默认为 0）。

```python
>>> range(5)              # range(0, 5)    —— stop=5, start=0, step=1
>>> range(2, 8)           # range(2, 8)    —— start=2, stop=8, step=1
>>> range(0, 10, 2)       # range(0, 10, 2)—— start=0, stop=10, step=2
>>> range(10, 0, -1)      # range(10, 0, -1)——反向递减
```

**参数约束**：
- `step` 不能为 `0`——会抛 `ValueError: range() arg 3 must not be zero`
- `start`、`stop`、`step` 必须是整数（`int` 或任何实现了 `__index__` 的对象）——浮点数不行
- 当 `step > 0` 且 `start >= stop` 时，range 为空（长度为 0）
- 当 `step < 0` 且 `start <= stop` 时，range 为空

```python
>>> range(5, 2)           # range(5, 2)——空 range（start > stop 且 step > 0）
>>> list(range(5, 2))     # []
>>> list(range(2, 8, -1)) # []——空 range（start < stop 且 step < 0）
```

#### `range` 的序列行为

`range` 完全实现了序列协议——支持 `len`、索引、切片、成员检查、迭代：

```python
>>> r = range(0, 20, 2)
>>> len(r)                 # 10
>>> r[0]                   # 0
>>> r[5]                   # 10
>>> r[-1]                  # 18
>>> r[2:5]                 # range(4, 10, 2)  ← 切片返回新的 range！
>>> 10 in r                # True（O(1)——不对元素做遍历！）
>>> 7 in r                 # False
>>> list(r)                # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
```

**为什么 `range` 更省内存**：

```python
>>> import sys
>>> sys.getsizeof(range(1000))       # 48 字节（始终固定）
>>> sys.getsizeof(list(range(1000))) # 8056 字节（随元素增长）
```

#### 关键特性

- **不可变**：`r[0] = 1` 会抛 TypeError
- **惰性求值**：`range(10**100)` 创建瞬间完成——值在迭代时才计算
- **O(1) 索引与切片**：不依赖元素总数，直接用公式 `start + i * step` 计算
- **O(1) 成员检查**：`x in range(...)` 只检查 `x - start` 能否被 `step` 整除（仅对整数有效）
- **可哈希**：可作为字典键或集合元素
- **支持 `==` / `!=` 比较**：相同 start/stop/step 的 range 判定为相等

```python
>>> range(0, 10, 2) == range(0, 10, 2)    # True
>>> range(0, 10, 2) == range(0, 11, 2)    # False（stop 不同）
```

> **实战建议**：循环 N 次用 `for i in range(N)`（而非 `for i in list(range(N))`）；大范围迭代或成员检查时永远用 `range` 而非 `list`——内存占用恒定，成员检查 O(1)。

### 3.3.7 `bytes` 与 `bytearray`：二进制序列

`bytes` 是不可变的字节序列（0–255），`bytearray` 是其可变版本。两者与 `str` 密切相关——`str` 通过编码转为 `bytes`，`bytes` 通过解码转为 `str`。

**`bytes()` 构造函数签名**——三种构造模式：

```
bytes()                        # 空 bytes
bytes(iterable_of_ints)        # 从 0–255 整数序列
bytes(bytes_like)              # 从 bytes-like 对象（buffer 协议）
bytes(string, encoding, errors='strict')  # 从字符串编码
```

| 参数 | 说明 |
|------|------|
| 无参数 | 返回空 `bytes` 对象 `b""` |
| `iterable_of_ints` | 每个元素必须是 0–255 的整数 |
| `bytes_like` | 任何实现了 buffer 协议的对象（如 `bytes`、`bytearray`、`memoryview`） |
| `string` + `encoding` | 按指定编码将字符串转为字节，`errors` 控制非法字符的处理（`'strict'`/`'ignore'`/`'replace'`） |

**`bytearray()` 构造函数签名**——参数同 `bytes()`，但返回可变对象：

```
bytearray()
bytearray(iterable_of_ints)
bytearray(bytes_like)
bytearray(string, encoding, errors='strict')
bytearray(size)                # 创建指定长度的零填充 bytearray
```

```python
# bytes——不可变
>>> b = b"hello"                # 字面量（仅 ASCII 字符）
>>> b = bytes([72, 101])       # 从整数列表 → b'He'
>>> b = "中文".encode("utf-8")  # str → bytes（编码）
>>> b.decode("utf-8")           # bytes → str（解码）→ "中文"
>>> b[0]                        # 118（返回整数，不是 bytes！）
>>> b[:2]                       # b'he'（切片返回 bytes）

# bytearray——可变
>>> ba = bytearray(b"hello")
>>> ba[0] = 72                  # 赋单个整数（0–255）
>>> ba.append(33)               # 追加
>>> ba                          # bytearray(b'Hello!')
>>> ba2 = bytearray(10)         # 创建 10 字节的零填充 → bytearray(b'\x00'*10)
```

**关键区别速览**：

| 特性 | `bytes` | `bytearray` | `str` |
|------|---------|-------------|-------|
| 可变性 | ❌ | ✅ | ❌ |
| 元素类型 | 整数 (0–255) | 整数 (0–255) | 单字符 str |
| 字面量 | `b"hello"` | `bytearray(b"hello")` | `"hello"` |
| 可哈希 | ✅ | ❌ | ✅ |

> **区分要点**：`str` 是 Unicode **文本**（人类可读），`bytes`/`bytearray` 是原始**字节**（机器可读）。`b"hello"[0]` 返回 `104`（整数），而 `"hello"[0]` 返回 `"h"`（字符串）。

### 3.3.8 `del` 语句

`del` 删除的是**名字**（或引用），不是对象本身。对象本身在被全部引用消除后被 GC 回收。

```python
# 删除变量（解绑名字）
>>> x = 42
>>> del x
>>> x
NameError: name 'x' is not defined

# 删除序列元素
>>> lst = [1, 2, 3, 4, 5]
>>> del lst[2]          # [1, 2, 4, 5]
>>> del lst[1:3]        # [1, 5]

# 删除字典键
>>> d = {'a': 1, 'b': 2}
>>> del d['a']          # {'b': 2}

# 删除对象属性
>>> del obj.attr
```

**多重赋值删除**：

```python
>>> a = b = [1, 2, 3]
>>> del a               # 只删除名字 a，不影响 b
>>> b
[1, 2, 3]
```

### 3.3.9 列表 vs 元组：何时用哪个？

| 考量 | 列表 | 元组 |
|------|------|------|
| 数据会变？ | ✅ | ❌ |
| 固定结构（如 (x,y) 坐标） | ❌ | ✅ |
| 字典键或集合元素 | ❌ 不可哈希 | ✅ 可哈希（内部元素全可哈希） |
| 函数返回多值 | 可，但语义弱 | ✅ 语义更明确 |
| 内存开销 | 略高（存储扩容缓冲区） | 更低 |
| 速度 | 略慢 | 略快（无写时复制逻辑） |

#### 练习 3.3

1. 用列表推导式生成 1 到 100 中所有能被 7 整除的数的平方列表。
2. 解释为什么 `[[0] * 3] * 3` 不是创建 3×3 零矩阵的正确方式，并写出正确写法。
3. 给定 `lst = [3, 1, 4, 1, 5, 9, 2, 6]`，写代码获取排序后的前 3 个最大元素（不改变原列表）。
4. 用 `range()` 创建一个从 100 递减到 0（含 0）步长为 5 的序列，并将其转为列表。
5. 写出以下代码的结果：
   ```python
   t = (1, 2, [3, 4])
   t[2].append(5)
   print(t)
   ```
   解释为什么元组"不可变"却可以发生这种变化。
6. 用 `namedtuple` 定义一个表示 RGB 颜色的 `Color` 类型，并创建 `red = Color(255, 0, 0)`。

---

## 3.4 映射与集合：字典与集合

### 3.4.1 字典

字典是 Python 的**核心映射类型**：基于哈希表实现的键值对集合。键必须可哈希（不可变），值可为任意对象。

**CPython 实现**：Python 3.6 起保序（3.7+ 正式纳入语言规范），内存效率大幅改进。

#### 创建

`dict()` 是 Python 中**构造模式最丰富的内置类型之一**——它支持三种截然不同的构造方式，理解它们各自的适用场景能极大简化代码。

**`dict()` 构造函数签名**——三种重载形式：

```
dict()                          # (1) 空字典
dict(**kwargs)                  # (2) 关键字参数
dict(mapping, **kwargs)         # (3a) 从映射对象
dict(iterable, **kwargs)        # (3b) 从可迭代对象（键值对序列）
```

注意所有重载中的 `**kwargs` 是可选的——它可以在任何模式下提供额外的键值覆写。

---

**模式 1：关键字参数（Keyword Arguments）**

```
dict(**kwargs)
```

这是最"Pythonic"的构造方式——键自动作为字符串，无需引号包裹，适合键为合法标识符的场景：

```python
>>> dict(name="Alice", age=25, active=True)
{'name': 'Alice', 'age': 25, 'active': True}

# 参数名成为键，参数值成为值——键必须是合法的 Python 标识符
```

| 优点 | 限制 |
|------|------|
| 简洁、可读性极高 | 键必须是合法 Python 标识符（不能有空格、特殊字符、数字开头） |
| IDE 自动补全友好 | 键名数量固定（不能是动态的） |
| 无引号噪音 | 键始终是字符串 |

```python
# ❌ 不能用于非标识符键
>>> dict(area-code="415")          # SyntaxError——连字符不是合法标识符
>>> dict(42="answer")              # SyntaxError——数字开头不合法
>>> dict(class="CS101")            # 合法但不推荐——class 是关键字（Python 允许但易混淆）
```

---

**模式 2：从映射对象（Mapping）**

```
dict(mapping, **kwargs)
```

传入一个实现了 `Mapping` 协议的对象（如 `dict`、`OrderedDict`、`defaultdict` 等），创建其浅拷贝：

```python
>>> original = {'a': 1, 'b': 2}
>>> dict(original)                           # {'a': 1, 'b': 2}——浅拷贝
>>> dict(original, c=3, d=4)                 # {'a': 1, 'b': 2, 'c': 3, 'd': 4}——拷贝并追加

# 任何映射类型都适用
>>> from collections import OrderedDict
>>> od = OrderedDict([('first', 1), ('second', 2)])
>>> dict(od)                                 # {'first': 1, 'second': 2}
```

> `dict(mapping)` 做的是**浅拷贝**——值对象本身不被复制，两个字典指向相同的值对象。对可变对象值的修改会同时反映在两边。

---

**模式 3：从可迭代对象（Iterable of Pairs）**

```
dict(iterable, **kwargs)
```

这是最灵活的方式——接受任意可迭代对象，其中每个元素是一个长度为 2 的键值对（`(key, value)`）：

```python
# 字面量列表
>>> dict([('a', 1), ('b', 2), ('c', 3)])
{'a': 1, 'b': 2, 'c': 3}

# zip() 并行的列表
>>> dict(zip(['a', 'b', 'c'], [1, 2, 3]))
{'a': 1, 'b': 2, 'c': 3}

# 生成器表达式（动态生成键值对）
>>> dict((str(i), i**2) for i in range(4))
{'0': 0, '1': 1, '2': 4, '3': 9}

# enumerate 的数字索引作为键
>>> dict(enumerate(['apple', 'banana', 'cherry']))
{0: 'apple', 1: 'banana', 2: 'cherry'}

# 追加额外的键值覆写
>>> dict([('a', 1), ('b', 2)], c=3, d=4)
{'a': 1, 'b': 2, 'c': 3, 'd': 4}
```

| 优点 | 注意事项 |
|------|---------|
| 键名无标识符限制（可以是数字、带空格、特殊字符） | 语法比关键字参数啰嗦 |
| 键值对可以动态生成（生成器、函数调用） | 每个元素必须是恰好 2 个元素的迭代对 |
| 适合从 `zip`、`enumerate`、API 返回值构造 | 重复键以后出现的为准 |

---

**三种模式的对比总结**：

```python
# 同一个字典——三种写法

# 写法 1：关键字参数（最简洁，键必须是标识符）
d1 = dict(name="Alice", age=25)

# 写法 2：从映射（浅拷贝 + 覆写）
d2 = dict({'name': 'Alice'}, age=25)

# 写法 3：从可迭代对象（最灵活，键无限制）
d3 = dict([('name', 'Alice'), ('age', 25)])

# 三者结果完全相同
>>> d1 == d2 == d3
True
```

**决策树**：选择哪种模式？

```
dict() 的三种构造模式——何时用哪个？

├─ 键都是合法标识符，且在代码编写时就确定？
│   └─ → 关键字参数：dict(name="Alice", age=25)
│
├─ 已有另一个字典/映射对象，想复制或在此基础上扩展？
│   └─ → 映射：dict(existing_dict, extra_key=value)
│
├─ 键是动态的、非标识符（如数字、含空格）、或来自 zip/filter 等？
│   └─ → 可迭代对象：dict(zip(keys, values))
│
└─ 实际建议：最常用的是字面量 {} 和关键字参数两种
```

**字面量与推导式**（最快的创建方式）：

```python
{}                              # 空字典（比 dict() 快——不涉及函数调用）
{'a': 1, 'b': 2}                # 字面量（键已知时首选）
{a: a ** 2 for a in range(5)}   # 字典推导式（动态生成）
```

#### 访问与修改

这里集中了字典日常使用最频繁的方法，理解它们精确的签名是写出健壮字典操作代码的关键。

```python
d[key]              # 取值（KeyError 若键不存在）
d.get(key, default) # 安全取值（默认 None，不抛异常）
d.setdefault(key, default)  # 取值，若不存在则设置并返回默认值
d[key] = value      # 设值/改值
d.update(other)     # 合并其他字典（other 覆写 d 同名键）
del d[key]          # 删除键（KeyError 若键不存在）
d.pop(key, default) # 删除并返回值（KeyError 若键不存在且未提供 default）
d.popitem()         # 删除并返回最后一个键值对（LIFO），3.7+ 移除的是最后插入项
d.clear()           # 清空
```

**关键方法签名详解**：

**`dict.get(key, default=None)`**

```
d.get(key)
d.get(key, default)
```

这是防御性取值的第一选择——键存在时返回值，不存在时返回 `default`（默认 `None`），**从不抛 `KeyError`**。

```python
>>> d = {'a': 1}
>>> d.get('a')            # 1        （键存在，返回对应的值）
>>> d.get('z')            # None     （键不存在，返回 default 的默认值 None）
>>> d.get('z', 0)         # 0        （键不存在，返回指定的默认值）
>>> d.get('a', 999)       # 1        （键存在，忽略 default！）
```

> **`d.get(key)` ≠ `d[key]`**：前者是安全的查询（不抛异常），后者在键不存在时抛 `KeyError`。在不确定键是否存在时，始终用 `get`。

**`dict.setdefault(key, default=None)`**

```
d.setdefault(key)
d.setdefault(key, default)
```

这是字典中**最容易被误解**的方法——它是 `get` 和 `set` 的原子融合：

1. 如果 `key` 存在 → 返回其对应的值（**不修改字典**）
2. 如果 `key` 不存在 → **插入** `d[key] = default`，然后返回 `default`

```python
>>> d = {'a': 1}
>>> d.setdefault('a', 999)     # 1        （a 已存在，不修改，返回现有值）
>>> d                           # {'a': 1} （字典未变！）
>>> d.setdefault('b', 42)      # 42       （b 不存在，插入并返回默认值）
>>> d                           # {'a': 1, 'b': 42}
>>> d.setdefault('c')           # None     （不传 default 时默认为 None）
>>> d                           # {'a': 1, 'b': 42, 'c': None}
```

`setdefault` 的核心价值在于**嵌套字典的单行初始化**：

```python
# ❌ 传统写法——冗长
tree = {}
if 'a' not in tree:
    tree['a'] = {}
if 'b' not in tree['a']:
    tree['a']['b'] = {}
tree['a']['b']['c'] = 42

# ✅ setdefault——一行搞定
tree = {}
tree.setdefault('a', {}).setdefault('b', {})['c'] = 42
```

**`dict.update()` — 与 `dict()` 对称的三重载**

`update()` 的参数规则与 `dict()` 构造函数完全相同：

```
d.update(mapping)           # 从映射对象合并
d.update(iterable)           # 从键值对可迭代对象合并
d.update(**kwargs)           # 从关键字参数合并
```

```python
>>> d = {'a': 1, 'b': 2}

# 模式 1：从映射
>>> d.update({'b': 20, 'c': 30})          # {'a': 1, 'b': 20, 'c': 30}

# 模式 2：从键值对可迭代对象
>>> d.update([('d', 40), ('e', 50)])      # {'a': 1, 'b': 20, 'c': 30, 'd': 40, 'e': 50}

# 模式 3：从关键字参数
>>> d.update(f=60, g=70)                  # {... 'f': 60, 'g': 70}

# 混合使用
>>> d.update({'x': 99}, y=100, z=101)     # mapping + kwargs
```

> `update` 遵循"后来者居上"原则——如果同一个键出现多次，**最后一次**的值生效。

**`dict.pop(key, default)`**

```
d.pop(key)
d.pop(key, default)
```

删除指定键并返回其值。如果键不存在：
- 提供了 `default` → 返回 `default`（**不抛异常**）
- 没提供 `default` → 抛 `KeyError`

```python
>>> d = {'a': 1, 'b': 2}
>>> d.pop('a')            # 1     （删除并返回）
>>> d.pop('z', None)      # None  （不存在，返回默认值——安全）
>>> d.pop('z')            # KeyError! （不存在且无默认值）
```

**`get` 还是 `setdefault`？**

```python
# get：纯读取，不影响字典
counts = {}
for word in words:
    counts[word] = counts.get(word, 0) + 1

# setdefault：读取+条件设置。适合嵌套字典：
tree = {}
tree.setdefault('a', {}).setdefault('b', {})['c'] = 42
# 等价于（如果没有 setdefault）
if 'a' not in tree:
    tree['a'] = {}
if 'b' not in tree['a']:
    tree['a']['b'] = {}
tree['a']['b']['c'] = 42
```

**`|` 和 `|=` 运算符合并字典**（Python 3.9+）：

```python
>>> a = {'x': 1, 'y': 2}
>>> b = {'y': 3, 'z': 4}
>>> a | b                       # 新字典 {'x': 1, 'y': 3, 'z': 4}
>>> a |= b                      # 原地更新（a 现在是 {'x': 1, 'y': 3, 'z': 4}）
```

注意：`|` 在 3.9 以下不可用。在此之前用 `{**a, **b}` 解包技巧。

#### 视图对象

```python
d.keys()        # 键视图（集合语义——支持 & | - ^）
d.values()      # 值视图（非集合语义——可能重复）
d.items()       # 键值对视图
```

视图是动态的——随原字典变化而变化：

```python
>>> d = {'a': 1}
>>> keys = d.keys()
>>> d['b'] = 2
>>> keys
dict_keys(['a', 'b'])   # ← 自动反映了新增键
```

**`keys()` 支持集合操作**：

```python
>>> d1 = {'a': 1, 'b': 2, 'c': 3}
>>> d2 = {'b': 20, 'c': 30, 'd': 40}
>>> d1.keys() & d2.keys()          # 共同键
{'b', 'c'}
>>> d1.keys() - d2.keys()          # d1 独有的键
{'a'}
>>> d1.keys() ^ d2.keys()          # 不同时在两者中的键
{'a', 'd'}
```

#### 迭代

```python
for key in d:              # 迭代键（等价于 for key in d.keys()）
for value in d.values():   # 迭代值
for key, value in d.items():  # 迭代键值对（推荐）
```

**迭代中修改**：禁止在迭代字典对象时改变其大小——会触发 `RuntimeError: dictionary changed size during iteration`。应对方式：先收集要修改的键到列表，再对列表操作。

#### 字典推导式

```python
# 基本
{word: len(word) for word in ['hello', 'world']}
# {'hello': 5, 'world': 5}

# 交换键值
{v: k for k, v in {'a': 1, 'b': 2}.items()}
# {1: 'a', 2: 'b'}

# 带过滤
{k: v for k, v in data.items() if v is not None}
```

#### `defaultdict` 与 `Counter`

```python
from collections import defaultdict, Counter

# defaultdict：自动为缺失键生成默认值
dd = defaultdict(list)
for word in words:
    dd[word[0]].append(word)

dd2 = defaultdict(int)          # int() 返回 0
for word in words:
    dd2[word] += 1

# Counter：快速计数
c = Counter(['a', 'b', 'a', 'c', 'a', 'b'])
# Counter({'a': 3, 'b': 2, 'c': 1})
c.most_common(2)    # [('a', 3), ('b', 2)]
c['a']              # 3
c['z']              # 0（不存在的键；不同于普通 dict 的 KeyError）
```

### 3.4.2 集合

集合是**无序、不重复、可哈希**的对象集合。CPython 实现同样基于哈希表（与 `dict` 共享基础设施）。

#### 创建

**`set()` 构造函数签名**：

```
set()
set(iterable)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `iterable` | `Iterable` | — | 任何可迭代对象（省略时返回空集合） |

```python
set()                       # 空集合（注意：{} 是空字典！）
{1, 2, 3}                   # 字面量（最快）
set([1, 2, 3, 2, 1])        # 从可迭代对象去重 → {1, 2, 3}
set("hello")                # {'h', 'e', 'l', 'o'}——每个字符去重
{x * 2 for x in range(5)}   # 集合推导式
```

> **经典坑**：`set()` 是空集合，`{}` 是空字典。要记住。

#### 集合运算

```python
# 基本运算
a | b       # 并集：在 a 或 b 中的元素
a & b       # 交集：同时在 a 和 b 中的元素
a - b       # 差集：在 a 中但不在 b 中的元素
a ^ b       # 对称差集：在 a 或 b 中，但不同时在两者中的元素

# 原地运算（修改 a 自身）
a |= b      # 更新为并集
a &= b      # 更新为交集
a -= b      # 更新为差集
a ^= b      # 更新为对称差集

# 比较运算
a <= b      # a 是 b 的子集？
a < b       # a 是 b 的真子集？
a >= b      # a 是 b 的超集？
a > b       # a 是 b 的真超集？
a.isdisjoint(b)  # a 与 b 不相交？
```

```python
>>> a = {1, 2, 3, 4}
>>> b = {3, 4, 5, 6}
>>> a | b                # {1, 2, 3, 4, 5, 6}
>>> a & b                # {3, 4}
>>> a - b                # {1, 2}
>>> a ^ b                # {1, 2, 5, 6}
```

#### 集合方法

```python
s.add(x)            # 添加元素
s.remove(x)         # 删除元素（KeyError 若不存在）
s.discard(x)        # 删除元素（不存在则静默忽略）
s.pop()             # 移除并返回任意元素（集合无序，结果不确定）
s.clear()           # 清空
s.update(other)     # 等价于 s |= other
s.intersection_update(other)  # 等价于 s &= other
s.difference_update(other)    # 等价于 s -= other
s.symmetric_difference_update(other)  # 等价于 s ^= other
```

**`remove` vs `discard`**：

```python
>>> s = {1, 2, 3}
>>> s.remove(4)             # KeyError: 4
>>> s.discard(4)            # 静默完成（无异常）
```

#### 集合推导式

```python
{x for x in range(10) if x % 2 == 0}
# {0, 2, 4, 6, 8}

# 利用集合去重
{len(word) for word in ['a', 'bb', 'ccc', 'bb']}
# {1, 2, 3}
```

### 3.4.3 `frozenset`：不可变集合

`frozenset` 是可哈希的不可变集合——可作为字典键或集合元素。

**`frozenset()` 构造函数签名**：

```
frozenset()
frozenset(iterable)
```

与 `set()` 签名完全一致——但对传入的可迭代对象做热切求值后返回**不可变**集合（因此可哈希，无原地修改方法）。

```python
>>> fs = frozenset([1, 2, 3])
>>> hash(fs)                # 可哈希 ✓
>>> d = {fs: "value"}       # 可作为字典键
>>> {fs, frozenset([4,5])}  # 可作为集合元素
```

方法集合与 `set` 相同（但不可原地修改）：

```python
fs.union(other)         # 返回新 frozenset（无 | 简写）
fs.intersection(other)
fs.difference(other)
fs.symmetric_difference(other)
fs.isdisjoint(other)
fs.issubset(other)
fs.issuperset(other)
fs.copy()
```

### 3.4.4 集合的常见应用

**去重**：

```python
>>> list(set([1, 2, 2, 3, 3, 3, 1]))
[1, 2, 3]         # 注意：不保留顺序
# 如需保序去重（Python 3.7+）：
>>> list(dict.fromkeys([1, 2, 2, 3, 3, 3, 1]))
[1, 2, 3]
```

**成员检查**：`x in set_lookup` 是 O(1)——远快于列表的 O(n)：

```python
>>> large_list = list(range(10_000_000))
>>> large_set = set(large_list)
>>> 9_999_999 in large_list  # O(n)——慢
>>> 9_999_999 in large_set   # O(1)——瞬发
```

**数学集合论操作**：

```python
# 共有好友
mutual_friends = alice_friends & bob_friends

# 移除已处理项
remaining = all_items - processed_items
```

#### 练习 3.4

1. 给定 `data = {"a": 1, "b": 2, "c": 3}`，用字典推导式创建一个新字典，其中值翻倍：`{"a": 2, "b": 4, "c": 6}`。
2. 解释 `d.get(key)` 和 `d[key]` 的区别，并给出各自适合的使用场景。
3. 用 `Counter` 统计一段文本中每个单词的出现次数，并用 `most_common(3)` 输出前三个高频词。
4. 给定两个集合 `a = {1, 2, 3, 4}` 和 `b = {3, 4, 5, 6}`，计算它们的并集、交集、差集（`a - b`）和对称差集。
5. 解释为什么 `{[]}` 会报错而 `{frozenset([1,2])}` 不会。
6. 用 `dict.fromkeys()` 实现对列表的去重并保持顺序。

---

## 本章小结

| 类型 | 可变 | 有序 | 可重复 | 语法 | 典型用途 |
|------|------|------|--------|------|---------|
| `int`/`float`/`complex` | ❌ | N/A | N/A | `42`, `3.14`, `1+2j` | 数值计算 |
| `bool` | ❌ | N/A | N/A | `True`, `False` | 逻辑判断 |
| `str` | ❌ | ✅ | N/A | `"hello"` | 文本处理 |
| `list` | ✅ | ✅ | ✅ | `[1, 2, 3]` | 动态集合 |
| `tuple` | ❌ | ✅ | ✅ | `(1, 2)` | 固定记录、字典键 |
| `dict` | ✅ | ✅ (3.7+) | ❌（键去重） | `{'a': 1}` | 键值映射 |
| `set` | ✅ | ❌ | ❌ | `{1, 2}` | 去重、成员检查 |
| `frozenset` | ❌ | ❌ | ❌ | `frozenset({1,2})` | 不可变集合键 |

**核心要义**：

1. **不可变性**≠数据不能变化——包含可变元素的元组结构不变，但元素对象可变
2. **切片**永远不会越界——这是 Python 的设计选择
3. **`sort()` 返回 `None`**——原地方法不返回自身
4. **字典保序**——3.7+ 正式保证，利用 `popitem()` 实现 LIFO
5. **`set()` 是空集合，`{}` 是空字典**——初学者的经典陷阱
6. **选择正确的数据结构**——成员检查用集合 O(1)，保序用列表，映射用字典
