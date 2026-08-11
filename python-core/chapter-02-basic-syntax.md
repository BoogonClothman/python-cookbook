# 第2章 Python 基础语法

> **学习目标**：建立对 Python 语法规则的完整心智模型——不是背语法，而是理解每条规则为何如此设计、它在你日常编码中如何影响你、以及踩坑后如何最快爬出来。

---

## 2.1 语句与表达式

这是最基础的区分，但很多教程一笔带过。"理解语句和表达式的区别"直接决定了你能否理解为什么某些代码合法、另一些不合法。

### 2.1.1 核心区分

| | 表达式 Expression | 语句 Statement |
|------|------|------|
| **定义** | 可以**求值**（evaluate）为一个对象的代码片段 | 执行一个**动作**（action）的代码单元 |
| **有无返回值** | 有（一定产生一个对象） | 无（不产生值） |
| **能否嵌套** | 可以嵌套在其他表达式中 | 语句内部可以包含表达式，但语句不能嵌套在表达式中 |
| **典型例子** | `42`, `x + 1`, `len(lst)`, `x if cond else y` | `if`, `for`, `while`, `def`, `class`, `import`, `pass` |

```python
# 表达式：返回一个对象
>>> 2 + 3          # → 5（int 对象）
>>> "hello".upper()  # → "HELLO"（str 对象）
>>> x = 5             # 赋值语句——但 x = 5 本身不返回值！
```

**Python 与 C/Java 的关键差异**：在 C 中，赋值 `x = 5` 是一个表达式（返回值 5），可以写 `while (x = getchar())`。Python 刻意不允许这样做——赋值是语句，不能出现在需要表达式的位置。这是一个**故意为之的安全设计**，防止 `==` 和 `=` 混淆导致的经典 bug。

```python
# Python 禁止（语法错误）
>>> while line = file.readline():   # SyntaxError
...     process(line)

# 必须这样写——Python 3.8+ 可以用海象运算符破例：
>>> while line := file.readline():  # := 是赋值表达式
...     process(line)
```

### 2.1.2 表达式语句

有些表达式可以**单独作为语句**使用——它们被求值后，结果被丢弃。合法的表达式语句只有：

- 函数调用：`print("hello")`
- 方法调用：`lst.append(1)`
- 原地运算符：`lst += [1]`

```python
# ✅ 合法的表达式语句
print("hello")
lst.sort()
data.update({"key": "value"})

# ❌ 非法——纯算术表达式作为语句没有意义
2 + 3          # 合法但不做任何事（结果被丢弃）
x              # 合法但不做任何事
```

### 2.1.3 `pass`：空语句

`pass` 是 Python 的**空操作语句**——语法上需要一个语句但你暂时不想写任何代码：

```python
# 占位——稍后实现
def not_implemented_yet():
    pass

class EmptyBase:
    pass

# 在 except 中吞掉异常（谨慎使用！）
try:
    risky_operation()
except ValueError:
    pass       # 显式决定忽略这个异常
```

> **风格建议**：用 `...`（Ellipsis 字面量）替代 `pass` 也是合法的，且在存根文件中更常见。但在普通代码中，`pass` 是惯用法。

---

## 2.2 缩进与代码块

Python 用缩进定义代码块——这不是语法糖，而是语法的**核心组成部分**。缩进错误是**语法错误**，不是风格问题。

### 2.2.1 缩进规则

```python
# 冒号(:)后下一行缩进，开启一个新代码块
if condition:          # ← 冒号说"下面是一个代码块"
    do_first()         # ← 缩进 4 空格，这条语句属于 if
    do_second()        # ← 同缩进，也属于 if
do_after()             # ← 回到原缩进层级，不属于 if
```

**核心规则**：
1. **冒号 `:` 开启新块**——`if`、`else`、`elif`、`for`、`while`、`def`、`class`、`try`/`except`/`finally`、`with`、`match`/`case`
2. **块的第一条语句确定该块的基准缩进量**
3. **同块内的所有语句缩进量必须严格一致**
4. **块结束后回退到上一级缩进**

### 2.2.2 空格 vs 制表符

这是一个值得花 3 分钟彻底理解的问题——它制造的 bug 可以浪费你 3 个小时。

```python
# 这个文件看起来没问题，但：
def greet():
    print("Hello")      # 这行用空格缩进
	print("World")      # 这行用 Tab 缩进 ← 看起来很对齐
```

Python 3 **禁止混用 Tab 和空格**——会直接抛出 `TabError: inconsistent use of tabs and spaces in indentation`。这不是可配置的 linting 选项，是硬语法规则。

**PEP 8 裁决**：**只用空格，每级 4 个空格**。

```python
# ✅ 正确
def func():
    if condition:
        do_something()
        if nested:
            do_other()

# ❌ 错误：混用
def func():
    if condition:
        do_something()
		if nested:       # Tab 混入
		    do_other()
```

> **实战配置**：在 VS Code 中设置 `"editor.renderWhitespace": "all"`，让 Tab 和空格可视化显示为 `→` 和 `·`。永远不要在肉眼看不到缩进字符的情况下调试缩进问题。

### 2.2.3 隐式行连接

括号 `()`、`[]`、`{}` 内的内容可以**自动跨行**，无需反斜杠：

```python
# ✅ 括号内自动续行（推荐）
result = function_with_many_args(
    arg1, arg2, arg3,
    arg4, arg5, arg6
)

numbers = [
    1, 2, 3,
    4, 5, 6,
]

config = {
    "host": "localhost",
    "port": 5432,
    "debug": True,
}

# ✅ 长表达式用括号包裹
total = (
    revenue
    - cost_of_goods_sold
    - operating_expenses
    + other_income
)

# ✅ 长条件——括号包裹实现拆分
if (condition_one
    and condition_two
    and (nested_condition_a or nested_condition_b)):
    handle_complex_case()
```

### 2.2.4 显式行连接：反斜杠 `\`

当隐式连接不适用（没有括弧可用），用 `\` 显式续行：

```python
# 显式续行——不得已时使用
long_string = "this is a very long string that " \
              "spans multiple lines for readability"

# 多个 with 语句——\ 续行
with open("input.txt") as infile, \
     open("output.txt", "w") as outfile:
    outfile.write(infile.read())
```

**反斜杠续行的陷阱**：`\` 后必须是换行符——后面不能有空格或注释：

```python
# ❌ 反斜杠后有空格——SyntaxError
x = 1 + \   
    2

# ❌ 反斜杠后有注释——SyntaxError
x = 1 + \  # this is a comment
    2
```

> **建议**：能用隐式续行就不用 `\`。隐式续行不会出现上述看不见的 bug。

### 2.2.5 一行多语句：分号 `;`

Python 允许用分号在一行写多个语句，但**强烈不建议**：

```python
# 合法但不可读
a = 1; b = 2; print(a + b)

# ✅ 只有一种情况分号可以接受：极短的两句紧密相关操作
import sys; sys.setrecursionlimit(10000)
```

---

## 2.3 注释与文档

### 2.3.1 注释的种类

```python
# 这是行注释——从 # 到行尾的所有内容被忽略

x = 42  # 行内注释——说明"为什么"，而非"做什么"

"""这不是注释——这是一个字符串字面量。
如果它不在赋值语句或表达式里，Python 会生成它然后丢弃。
这就是为什么它可以被用作多行注释——但严格来说它不是注释。
"""
```

**四种写"注释"的方式**：

| 方式 | 语法 | 实际身份 | 用途 |
|------|------|---------|------|
| 行注释 | `# 文本` | 真正的注释 | 解释"为什么" |
| 文档字符串 | `"""文本"""` | 字符串字面量（被 `help()` 读取） | 模块/类/函数的公开文档 |
| 独立字符串字面量 | `"任意文本"` | 字符串对象（被丢弃） | 临时多行注释（不推荐） |
| 类型注解 | `x: int = 5` | 被 `__annotations__` 存储 | 类型信息 |

### 2.3.2 注释的黄金法则

**注释解释"为什么"（why），代码表达"做什么"（what）。**

```python
# ❌ 废话注释——重复代码已经说了的事
counter = counter + 1       # 把 counter 加 1

# ✅ 有效注释——解释代码不能表达的决策原因
counter = counter + 1       # 补偿 API 返回结果中的 off-by-one 错误

# ✅ TODO/FIXME/HACK/NOTE 约定
# TODO(alice): 用二分查找替换线性扫描（数据量 > 10^6 时）
# FIXME(bob): Python 3.8 后可以用 math.comb 替代
# HACK: 临时绕开第三方库的缓存失效 bug（v2.1.0 修复后移除）
# NOTE: 因为 GIL，这段代码在多线程下是安全的
```

### 2.3.3 文档字符串（Docstring）

文档字符串是模块、函数、类或方法体中的**第一个字符串字面量**，被 `help()` 和文档生成工具自动读取。

```python
def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers.

    Uses iterative generation (not recursion) for O(n) time
    and O(1) auxiliary space.

    Args:
        n: Number of Fibonacci numbers to generate (non-negative).

    Returns:
        A list of the first n Fibonacci numbers, starting with [0, 1, ...].

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(5)
        [0, 1, 1, 2, 3]
        >>> fibonacci(0)
        []
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    result = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result
```

**文档字符串风格**：Google 风格（上例）、NumPy 风格、Sphinx reStructuredText 风格均可。在一个项目中保持一致即可。Google 风格因可读性最高，在科学计算之外的主流 Python 项目中增长最快。

---

## 2.4 标识符、关键字与命名

### 2.4.1 标识符规则

Python 3 的标识符支持 Unicode——这意味着中文、日文、emoji 都可以作为变量名。但**可以不等于应该**。

```python
# 合法命名规则：
# - 首字符：字母（Unicode 分类 L_*）、下划线 _
# - 后续字符：字母、数字（Unicode 分类 Nd）、下划线
# - 大小写敏感
# - 不能是关键字
# - 不能是 Python 内置常量/函数名（不强制，但会遮蔽）

# ✅ 合法但风格存疑
名字 = "小明"       # 中文变量名——合法，但不建议在非中文教学代码中使用
café = "coffee"     # 重音字母——合法

# ❌ 非法
1st_place = "gold"  # 数字开头
class = "CS101"     # 关键字
my-var = 42         # 连字符不是合法字符
```

### 2.4.2 关键字完整清单

Python 3.14 共有 **35 个关键字**（含 3 个软关键字）：

```python
# 任何时候都会检查这些关键字——检查脚本：
>>> import keyword
>>> keyword.kwlist
['False', 'None', 'True', 'and', 'as', 'assert', 'async',
 'await', 'break', 'class', 'continue', 'def', 'del', 'elif',
 'else', 'except', 'finally', 'for', 'from', 'global', 'if',
 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or',
 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']

# 软关键字（soft keywords）——仅在特定上下文检查
>>> keyword.softkwlist
['_', 'case', 'match']
```

**软关键字的含义**：`match`、`case`、`_` 只在 `match` 语句中作为关键字，在其他位置可以自由用作变量名。这意味着旧代码中把 `match` 作为变量名的不会因为 Python 版本升级而报错。

### 2.4.3 特殊标识符

| 标识符 | 含义 |
|------|------|
| `_` | 交互模式：上一个表达式的结果；在循环/解包中："不关心的值"；在 `match` 中：通配符 |
| `__name__` | 当前模块名（顶级执行时为 `"__main__"`） |
| `__file__` | 当前模块的文件路径 |
| `__all__` | 控制 `from module import *` 的导出列表 |
| `__init__` | 包初始化文件或类构造函数 |
| `__dunder__` | 双下划线前后缀——Python 的"魔术方法"，由解释器调用，**不应自己发明新的** |

### 2.4.4 命名约定全景

```python
# PEP 8 命名约定（从松散到紧密）

# 变量、函数、方法、模块、包：snake_case
user_name = "alice"
def calculate_average(scores):
    pass

# 类、异常：PascalCase
class UserProfile:
    pass

# 常量（模块级）：ALL_CAPS
MAX_RETRY_COUNT = 3
PI = 3.14159

# 内部/私有（约定，非强制）：_leading_underscore
_internal_cache = {}
def _helper_function():
    """外部调用者请不要依赖此函数——它可能随时变化。"""
    pass

# 避免与关键字/内置名冲突：trailing_underscore_
class_ = MyClass      # class 是关键字
type_ = "user"        # type 是内置函数
list_ = [1, 2, 3]     # 不遮蔽内置的 list

# 名称修饰（Name Mangling）：__leading_double_underscore
class Parent:
    def __really_private(self):
        pass          # 被 Python 自动改名为 _Parent__really_private

# 魔术方法：__dunder__（双下划线前后缀）
class MyContainer:
    def __len__(self):
        return 0
    def __getitem__(self, key):
        raise IndexError

# 类型变量（泛型）：PascalCase 或 _T 风格
from typing import TypeVar
T = TypeVar('T')
_KT = TypeVar('_KT')
```

> **`_` 约定**：`_` 在不同的编码风格中有不同含义。
> - `_ = get_value()` → "我不用这个返回值"
> - `for _ in range(10):` → "循环变量不重要"
> - `first, *_, last = data` → "中间那些给我扔掉"
> - `from module import *` → 不会导出 `_` 开头的名字（除非在 `__all__` 中）

---

## 2.5 变量与对象

这是 Python 新手和老手之间最大的认知差距所在——**变量的实质是什么**。

### 2.5.1 名字是标签，不是盒子

在 C/Java 中，变量是一个**内存盒子**，声明 `int x` 分配了一块内存。赋值 `x = 42` 是把 42 放进去。

Python 不是这样。Python 的变量是**贴在对象上的名字标签**。赋值 `x = 42` 的意思是："让名字 `x` 指向整数对象 `42`"。

```python
# 变量是标签，不是容器
>>> x = [1, 2, 3]
>>> y = x              # y 贴到了同一个列表对象上
>>> y.append(4)        # 通过 y 修改对象
>>> x                  # x 也"变了"
[1, 2, 3, 4]           # ← 新手震惊点

# 用 id() 验证——它们指向同一个对象
>>> id(x)
139912345678912
>>> id(y)              # 同上
139912345678912
```

### 2.5.2 `is` vs `==`：身份 vs 相等

| 运算符 | 检查什么 | 何时为 True |
|------|------|------|
| `==` | **值相等**（equality） | 对象的内容/值相同（由 `__eq__` 定义） |
| `is` | **身份相同**（identity） | 两个名字指向内存中的**同一个对象** |

```python
>>> a = [1, 2, 3]
>>> b = [1, 2, 3]
>>> a == b              # True——内容相同
>>> a is b              # False——不同的对象！
>>> a is a              # True——同一个对象

# 小整数和短字符串的内部化（interning）——常见的认知陷阱
>>> a = 256
>>> b = 256
>>> a is b              # True（CPython 内部化 -5 到 256）
>>> a = 257
>>> b = 257
>>> a is b              # False！（超出缓存范围，两个独立对象）

# ✅ 黄金法则：
# - 和 None/True/False 比较永远用 is
# - 其他情况永远用 ==
# - is 的唯一正确用途：检查单例（None, True, False）或检查两个名字是否指向完全相同的对象
```

### 2.5.3 可变对象 vs 不可变对象：赋值的两种语义

```python
# 不可变对象（int, float, str, tuple, frozenset, bytes）
>>> x = 100
>>> y = x                # y 指向同一个整数对象
>>> x = 200              # x 重新绑定到新对象——原对象 100 不受影响
>>> y
100                      # y 仍然指向 100

# 可变对象（list, dict, set, bytearray）
>>> x = [1, 2, 3]
>>> y = x                # y 指向同一个列表对象
>>> x.append(4)          # 原地修改——x 和 y 都被影响
>>> y
[1, 2, 3, 4]
```

**图解心智模型**：

```
不可变对象：x = 100; y = x; x = 200

  x ──────────→ 100          y ──→ 100
                      
  x ──→ 200                  y ──→ 100  (完好无损)


可变对象：x = [1,2,3]; y = x; x.append(4)

  x ──→ [1,2,3]  ←── y
  
  x ──→ [1,2,3,4]  ←── y   (同一个对象变化了)
```

### 2.5.4 `del` 的真意

`del` 删除的不是对象，而是**名字绑定**（引用）。对象本身只有在没有任何引用指向它时才会被 GC 回收。

```python
>>> x = [1, 2, 3]
>>> y = x               # 现在有两个引用指向这个列表
>>> del x               # 删除名字 x，但 y 还在
>>> x
NameError: name 'x' is not defined
>>> y
[1, 2, 3]               # 对象存活——y 还指向它

# 多重赋值与 del
>>> a = b = [1, 2, 3]   # a 和 b 指向同一对象
>>> del a                # 只删除 a
>>> b
[1, 2, 3]               # b 完好
```

### 2.5.5 引用计数与垃圾回收

Python 的内存管理基于**引用计数 + 循环检测 GC**：

```python
import sys

# 引用计数
>>> a = []
>>> sys.getrefcount(a)       # 2（a 变量 + getrefcount 的参数）
>>> b = a
>>> sys.getrefcount(a)       # 3
>>> del b
>>> sys.getrefcount(a)       # 2

# 循环引用——引用计数失效的场景
>>> lst = []
>>> lst.append(lst)          # lst[0] 指向 lst 自身
>>> sys.getrefcount(lst)     # 3（lst + lst[0] + getrefcount 参数）
>>> del lst                  # 引用计数降为 1（自己引用自己），永不归零
# → 由 GC 的循环检测器（generation 2）在适当时机回收
```

> **工程影响**：在 CPython 中，引用计数归零时对象**立即**被回收（`__del__` 被调用）。这与 Java/C# 的"某个不确定的 GC 时机"不同。这意味着文件句柄、锁等资源在 `del` 后立即释放。但因为有循环 GC 兜底，你不需要手动管理内存。

---

## 2.6 赋值全解

Python 的赋值语句远比表面丰富。这一节按复杂度递进，覆盖全部赋值形式。

### 2.6.1 基本赋值

```python
x = 42                  # 名字绑定
x = y = z = 0           # 多重赋值——三个名字指向同一个对象 0
```

### 2.6.2 序列解包（Iterable Unpacking）

```python
# 元组解包（最经典）
a, b = (1, 2)           # a=1, b=2
a, b = 1, 2             # 括号可省略
a, b = [1, 2]           # 任何可迭代对象都行
a, b = "hi"             # a='h', b='i'

# 交换变量——Python 风格的骄傲
a, b = b, a             # 不需要临时变量！

# 多值解包（左右数量必须匹配）
x, y, z = [1, 2, 3]

# ❌ 数量不匹配
x, y = [1, 2, 3]        # ValueError: too many values to unpack
```

### 2.6.3 星号解包（Extended Unpacking, Python 3.0+）

```python
# * 收集"剩余部分"为一个列表
>>> first, *rest = [1, 2, 3, 4, 5]
>>> first      # 1
>>> rest       # [2, 3, 4, 5]

>>> *head, last = [1, 2, 3, 4, 5]
>>> head       # [1, 2, 3, 4]
>>> last       # 5

>>> first, *middle, last = [1, 2, 3, 4, 5]
>>> first, middle, last
(1, [2, 3, 4], 5)

# 实用场景
>>> line = "Alice,25,Engineer,New York"
>>> name, age, *_ = line.split(",")   # 只取前两个字段，后面全扔
>>> name, age
('Alice', '25')

>>> *_, tail = range(10)              # 只要最后一个
>>> tail
9
```

### 2.6.4 增强赋值（Augmented Assignment）

```python
x += 1          # x = x + 1
x -= 1          # x = x - 1
x *= 2          # x = x * 2
x /= 2          # x = x / 2
x //= 2         # x = x // 2
x %= 3          # x = x % 3
x **= 2         # x = x ** 2
x &= 0xFF       # x = x & 0xFF
x |= 0x80       # x = x | 0x80
x ^= 0xFF       # x = x ^ 0xFF
x <<= 1         # x = x << 1
x >>= 1         # x = x >> 1
```

**增强赋值对可变对象的语义差异**：

```python
# 对于不可变对象：+= 创建新对象然后重新绑定
>>> x = 10
>>> y = x
>>> x += 5          # 等价于 x = x + 5——创建新的 int(15)，x 重新绑定
>>> x, y
(15, 10)            # y 不受影响

# 对于可变对象：+= 是原地修改！
>>> x = [1, 2, 3]
>>> y = x
>>> x += [4, 5]     # 等价于 x.extend([4, 5])——原地修改！
>>> x, y
([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])  # y 也变了！
```

**`x += y` 的精确语义**：

```python
# Python 执行 x += y 时：
# 1. 尝试调用 x.__iadd__(y)（原地加法）
# 2. 如果 __iadd__ 没有定义（不可变对象），退化为 x = x.__add__(y)
# 这就是为什么 int 的 += 返回新对象而 list 的 += 原地修改
```

### 2.6.5 海象运算符 `:=`（Python 3.8+）

正式名称是"赋值表达式"（Assignment Expression）。它允许在**表达式内部**做赋值并返回所赋的值。这个名字来自 `:=` 看起来像海象的眼睛和獠牙。

```python
# 经典场景 1：在 while 条件中同时读取和判断（最常见）
# ❌ 之前：读取和判断分离
line = file.readline()
while line:
    process(line)
    line = file.readline()

# ✅ 之后：一行搞定
while line := file.readline():
    process(line)

# 经典场景 2：在 if 中捕获中间值
# ❌ 之前
m = re.match(pattern, text)
if m:
    print(m.group(1))

# ✅ 之后
if m := re.match(pattern, text):
    print(m.group(1))

# 经典场景 3：在列表推导式中避免重复计算
# ❌ 之前：f(x) 被计算两次（一次 filter，一次 map）
results = [f(x) for x in data if f(x) > 0]

# ✅ 之后：算一次，存起来复用
results = [y for x in data if (y := f(x)) > 0]
```

**海象运算符的限制**：

```python
# ❌ 不能用在赋值语句的位置
x := 5                        # SyntaxError

# ✅ 必须用在带括号的表达式中
(x := 5)                      # 合法但无意义
if (x := get_value()):        # 合法
while (x := next_value()):    # 合法

# ❌ 不能用在 f-string 的表达式部分（反斜杠一样的限制）
f"{(x := 5)}"                 # SyntaxError（部分 Python 版本）
```

> **使用建议**：海象运算符是个"有品味地使用"的工具。`while line := file.readline()` 是完美的惯用法；在列表推导式中用它避免重复计算也是好的。但如果一个表达式因为 `:=` 变得难以理解——回到传统写法。

---

## 2.7 运算符与表达式

### 2.7.1 运算符优先级全表

优先级从高到低。同一行内优先级相同，从左到右结合（右结合有标注）。

| 优先级 | 运算符 | 说明 |
|------|------|------|
| 1（最高） | `()` `[]` `{}` | 括号、索引、字面量 |
| 2 | `x.attr` `f(args)` | 属性访问、函数调用 |
| 3 | `await x` | await 表达式 |
| 4 | `**` | 幂运算（**右结合**） |
| 5 | `+x` `-x` `~x` | 一元正/负、按位取反 |
| 6 | `*` `/` `//` `%` `@` | 乘、除、整除、取模、矩阵乘 |
| 7 | `+` `-` | 加、减 |
| 8 | `<<` `>>` | 左移、右移 |
| 9 | `&` | 按位与 |
| 10 | `^` | 按位异或 |
| 11 | `\|` | 按位或 |
| 12 | `in` `not in` `is` `is not` `<` `<=` `>` `>=` `!=` `==` | 比较、成员、身份 |
| 13 | `not x` | 逻辑非 |
| 14 | `and` | 逻辑与 |
| 15（最低） | `or` | 逻辑或 |
| — | `if ... else` | 条件表达式 |
| — | `lambda` | lambda 表达式 |
| — | `:=` | 海象运算符（赋值表达式） |

```python
# 不依赖记忆——加括号让意图明确
result = a + b * c       # 合法但需要心算优先级
result = a + (b * c)      # 一目了然

# 少数不需要括号的惯用写法（所有人都知道）
if x and y:
if not items:
for key in dict:
value = data.get('key', default)
```

### 2.7.2 比较链（Comparison Chaining）

Python 允许链式比较——这是数学写法的自然映射：

```python
# ✅ Python 独特风格
>>> x = 5
>>> 0 < x < 10         # True——等价于 0 < x and x < 10，但 x 只求值一次
>>> 1 < x <= 10 > 3    # 合法但可读性差——不推荐过长的链

# Python 的解析：
# 0 < x < 10  被解析为  0 < x and x < 10（但 x 只求值一次）

# 这意味着你可以写：
>>> a, b, c = 1, 2, 2
>>> a < b == c         # a < b AND b == c → True AND True → True

# 对比其他语言：C 中 0 < x < 10 先求值 (0 < x) → 1，再求值 1 < 10 → 1
# 结果一样但语义完全不同！Python 的做法更接近数学直觉
```

### 2.7.3 短路求值（Short-Circuit Evaluation）

`and` 和 `or` 使用短路求值——一旦结果确定就停止对后续表达式的求值。

```python
# and：第一个为假时短路，返回第一个假值（或最后一个值）
>>> 0 and print("不会执行")    # 0 是假值 → 短路 → 返回 0
0

>>> 1 and 2 and 3              # 全真 → 返回最后一个
3

# or：第一个为真时短路，返回第一个真值（或最后一个值）
>>> 1 or print("不会执行")     # 1 是真值 → 短路 → 返回 1
1

>>> 0 or [] or 3               # 前两个是假值 → 返回 3
3
```

**关键认知**：`and` 和 `or` 返回的是**操作数本身**，不是 `True`/`False`！

```python
>>> 3 and 5       # 5（不是 True！）
>>> 0 or "hello"  # "hello"（不是 True！）
```

**短路求值的实用模式**：

```python
# 模式 1：安全访问——如果 a 为 None 则不访问其属性
result = a and a.method()

# 模式 2：默认值——如果首选为空则用备选
name = user_input or "Anonymous"    # 注意：会把空字符串也当作假值！

# 更精确的默认值写法（3.8+）：
name = user_input if user_input is not None else "Anonymous"

# 模式 3：条件执行
condition and do_something()        # 利用短路——但不建议用于副作用

# ✅ 这个模式是可接受的（常见于测试和脚本）：
debug and print(f"Debug: value = {value}")
```

### 2.7.4 三元表达式

```python
# 语法：<value_if_true> if <condition> else <value_if_false>
status = "Adult" if age >= 18 else "Minor"

# 可以嵌套，但过度嵌套是大忌
result = "High" if score > 90 else "Mid" if score > 60 else "Low"

# ✅ 比下面这个更可读
if score > 90:
    result = "High"
elif score > 60:
    result = "Mid"
else:
    result = "Low"
# （对于简单值映射，上面的嵌套三元表达式其实也还行）
```

### 2.7.5 运算符分类速查

```python
# ── 算术运算符 ──
+ - * /             # 加 减 乘 除（/ 始终返回 float）
//                  # 整除（向下取整）  7//2→3, -7//2→-4
%                   # 取模              7%2→1
**                  # 幂运算            2**10→1024

# ── 比较运算符 ──
== != < <= > >=     # 值比较
is / is not         # 身份比较（只用于 None/True/False 或检查是否同一对象）

# ── 逻辑运算符 ──
and / or / not      # 短路求值，返回操作数本身（不是 True/False）

# ── 位运算符 ──
& | ^ ~ << >>       # 按位与/或/异或/取反/左移/右移

# ── 成员运算符 ──
in / not in         # 成员检查（调用 __contains__）

# ── 身份运算符 ──
is / is not         # 身份检查（比较 id()）
```

---

## 2.8 标准输入输出

### 2.8.1 `print()` 深度解析

```python
print(*objects, sep=' ', end='\n', file=None, flush=False)
```

每个参数的含义：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `*objects` | — | 要输出的对象（任意数量），自动调用 `str()` 转为字符串 |
| `sep` | `' '` | 对象之间的分隔符 |
| `end` | `'\n'` | 输出结尾追加的字符 |
| `file` | `sys.stdout` | 输出目标（任何有 `write()` 方法的对象） |
| `flush` | `False` | 是否强制刷新输出缓冲区 |

```python
# 日常用法
>>> print("Hello", "World")                    # Hello World
>>> print("Hello", "World", sep="-")           # Hello-World
>>> print("Hello", end="...")                  # Hello...（不换行）
>>> print("One", "Two", sep="\n")              # One\nTwo

# 输出到文件
>>> with open("output.txt", "w") as f:
...     print("log message", file=f)

# 进度条模式（覆盖当前行）
>>> import time
>>> for i in range(101):
...     print(f"\rProgress: {i}%", end="", flush=True)
...     time.sleep(0.01)
>>> print()  # 最后的换行

# 快速调试：用 repr 输出精确表示
>>> value = "hello\nworld"
>>> print(value)               # hello
                               # world
>>> print(repr(value))         # 'hello\nworld'（看到转义符）
```

**`print()` 的缓冲问题**：默认情况下，`print()` 的输出是**行缓冲**的——只在遇到换行符时才刷新到终端。当 `end` 不包含 `\n` 时，内容可能被留在缓冲区不显示。这时需要 `flush=True`。

### 2.8.2 `pprint`：美化打印

当数据结构嵌套或很长时，`print()` 的输出难以阅读：

```python
>>> data = {"users": [{"name": "Alice", "scores": [95, 87, 91]}, 
...                   {"name": "Bob", "scores": [82, 88, 79]}]}
>>> print(data)
{'users': [{'name': 'Alice', 'scores': [95, 87, 91]}, {'name': 'Bob', 'scores': [82, 88, 79]}]}  # 一行

>>> from pprint import pprint
>>> pprint(data, width=40)
{'users': [{'name': 'Alice',
            'scores': [95, 87, 91]},
           {'name': 'Bob',
            'scores': [82, 88, 79]}]}
```

### 2.8.3 `input()` 的使用与陷阱

```python
# 基本用法
>>> name = input("What's your name? ")    # 显示提示符，等待用户输入
What's your name? Alice                    # 用户键入 "Alice" 并回车
>>> name
'Alice'                                    # 返回的是字符串（不含末尾换行）

# ⚠️ 陷阱：input() 永远返回字符串
>>> age = input("Age: ")
Age: 25
>>> type(age)
<class 'str'>                              # 不是 int！
>>> age + 1
TypeError: can only concatenate str (not "int") to str
>>> int(age) + 1                           # 需要显式转换
26

# ✅ 安全的输入处理模式
while True:
    try:
        age = int(input("Enter your age: "))
        if age < 0:
            print("Age cannot be negative.")
            continue
        break
    except ValueError:
        print("Please enter a valid integer.")
```

**`input()` vs `sys.stdin`**：`input()` 适合交互式输入（有提示符，自动 strip 换行）。对于批量输入（如管道输入、重定向文件），用 `sys.stdin.read()` 或 `sys.stdin.readlines()` 更合适。

```python
# 读取管道传入的全部内容
import sys
data = sys.stdin.read()

# 逐行读取（处理大文件）
for line in sys.stdin:
    process(line.rstrip('\n'))
```

### 2.8.4 格式化输出的决策树

```
你要输出什么？
│
├─ 调试时快速看一眼
│   └─ print(variable) 或 print(f"{var=}")
│
├─ 展示给用户的格式化文本
│   └─ f-string（首选）或 str.format()（动态模板）
│
├─ 复杂嵌套数据结构
│   └─ pprint.pprint()
│
├─ 写到文件
│   └─ print(..., file=f) 或 f.write(f"{...}\n")
│
├─ 生产环境日志
│   └─ logging 模块（不要用 print！）
│
└─ 表格化/列对齐文本
    └─ str.ljust()/rjust()、tabulate 库、或 pandas DataFrame
```

---

## 2.9 `assert`：调试断言

`assert` 是 Python 内置的轻量级调试工具。它不是错误处理机制——它是**程序员的 sanity check**。

```python
# 语法：assert <condition>, <optional error message>
def divide(a, b):
    assert b != 0, "Division by zero is not allowed"
    return a / b

# ✅ assert 用于捕获"不应该发生"的情况——内部不变量
def calculate_internal(data):
    assert len(data) > 0, "Empty data should have been filtered upstream"

# ❌ assert 不用于用户输入验证（原因见下）
def process_user_input(value):
    assert value > 0, "Value must be positive"  # 错！-O 模式下会消失
```

**危险**：`assert` 在 `-O`（优化模式）下被**完全移除**——条件不被检查，错误信息不产生：

```bash
$ python -O script.py    # assert 语句被当空白行！
```

**正确使用 `assert` 的指南**：

| 适合 | 不适合 |
|------|------|
| 检查内部不变量 | 数据验证（用户输入、API 参数） |
| 单元测试中的断言 | 生产环境的安全检查 |
| 开发阶段的临时检查 | 替代异常处理 |
| 检查 API 调用方的契约遵守情况 | 控制程序流程 |

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 表达式 vs 语句 | 表达式求值为对象，语句执行动作。赋值在 Python 中是语句而非表达式——这是安全设计 |
| 缩进 | 冒号开启新块、同级一致缩进、4 空格为首选。Tab/空格混用是 TabError |
| 行结构 | 隐式续行（括号）优于显式续行（`\`），分号只在极简语句中使用 |
| 注释 | 注释写"为什么"而非"做什么"。docstring 给 help() 用。TODO/FIXME/HACK 约定 |
| 标识符 | 支持 Unicode，大小写敏感，35 个关键字。`_` 前后缀有特殊语义 |
| 变量 | 名字是标签，不是盒子。`is` 查身份，`==` 查值。可变对象共享引用时要警觉 |
| 赋值 | 序列解包、`*` 收集、增强赋值的原地/新建语义差异、`:=` 海象运算符 |
| 运算符 | 链式比较、`and`/`or` 短路且返回操作数本身（非 True/False）、比较链 |
| print | `sep`, `end`, `file`, `flush` 四个参数覆盖所有输出需求 |
| input | 永远返回字符串——需要自己转换类型。`sys.stdin` 处理批量输入 |
| assert | 调试工具，非错误处理。——O 模式下被移除，不用于数据验证 |

---

#### 练习 2

1. 下面的代码合法吗？为什么？
   ```python
   if (x = get_value()):
       process(x)
   ```
   如果改成 `if (x := get_value()):` 呢？

2. 写出以下代码的输出，并解释每一步：
   ```python
   a = [1, 2, 3]
   b = a
   a = a + [4, 5]
   print(a, b)
   
   c = [1, 2, 3]
   d = c
   c += [4, 5]
   print(c, d)
   ```

3. 解释 `0 < x < 10` 在 Python 中的精确语义，以及它与 C 语言中间写法 `0 < x && x < 10` 的区别。

4. 用 `*` 解包提取下列数据的首尾元素，中间部分丢弃：
   ```python
   scores = [95, 88, 76, 92, 84, 79, 91]
   # 期望：first = 95, last = 91
   ```

5. 使用海象运算符简化以下代码：
   ```python
   m = re.match(r'^(\d{3})-(\d{4})$', phone)
   if m:
       area, number = m.groups()
       print(f"Area: {area}, Number: {number}")
   ```

6. 写一个交互式输入循环：不断提示用户输入数字，直到用户输入 `q` 退出。对每次输入验证是否为有效数字，是则累加，最后打印总和。要求正确处理 `ValueError`。

---

**进入下一章的准备**：
- ✅ 能区分表达式和语句，理解为什么 `x = 5` 不能出现在 `if` 条件中
- ✅ 能解释 `a is b` 和 `a == b` 的区别
- ✅ 理解可变对象共享引用时的副作用
- ✅ 能使用序列解包和 `*` 收集
- ✅ 遇到缩进错误时知道检查 Tab/空格混用
