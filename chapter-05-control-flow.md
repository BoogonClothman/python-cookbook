# 第5章 条件语句 & 循环语句 & 推导式

> **学习目标**：建立对 Python 控制流的完整理解——不仅掌握 `if`/`for`/`while` 的语法，更要理解真值协议、迭代器协议、`for-else` 的设计哲学、推导式的底层机制，以及控制流语句对变量作用域和性能的影响。

---

控制流是程序的骨架。Python 的控制流设计体现了"可读性优先"的哲学——用缩进定义块、用 `for-else` 表达搜索模式、用推导式将循环压缩为声明式表达式。但简洁的语法之下，隐藏着值得深入理解的协议和机制。

本章与第 2 章的关系：第 2 章的 2.8 节（print/input/assert）和 2.7 节（运算符与表达式）提供了控制流的快速概览。本章在此基础上**逐类深入**，新增真值协议、`for-else`/`while-else`、迭代器协议、match/case 模式匹配和推导式专题。两部分互为补充——第 2 章适合速查，本章适合系统学习。

---

## 5.1 条件语句与三元表达式

条件语句是程序"做出决策"的基本机制。Python 的条件系统由三部分组成：`if/elif/else` 语句、真值测试协议、以及三元条件表达式。三者协同工作，让条件逻辑既清晰又强大。

### 5.1.1 `if`/`elif`/`else` 基础

```python
# 最简单的条件语句
if condition:
    execute_block()

# 二分支
if condition:
    true_branch()
else:
    false_branch()

# 多分支——elif 是 "else if" 的缩写
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
elif score >= 70:
    grade = 'C'
elif score >= 60:
    grade = 'D'
else:
    grade = 'F'
```

**`elif` 的字节码——它是好的语法糖**：

```python
# 用 dis 模块查看 if/elif/else 的字节码
>>> import dis
>>> def grade(score):
...     if score >= 90:
...         return 'A'
...     elif score >= 80:
...         return 'B'
...     else:
...         return 'C'
>>> dis.dis(grade)
  2           RESUME                   0
              LOAD_FAST                0 (score)
              LOAD_CONST               1 (90)
              COMPARE_OP              18 (>=)       # if score >= 90
              POP_JUMP_IF_FALSE        1 (to L1)
              LOAD_CONST               2 ('A')
              RETURN_VALUE
  3     >> L1 LOAD_FAST                0 (score)
              LOAD_CONST               3 (80)
              COMPARE_OP              18 (>=)       # elif score >= 80
              POP_JUMP_IF_FALSE        1 (to L2)
              LOAD_CONST               4 ('B')
              RETURN_VALUE
  4     >> L2 LOAD_CONST               5 ('C')      # else
              RETURN_VALUE
```

注意 `elif` 在字节码层面被编译为嵌套的 `if-else` 跳转——它本质上是语法糖，但它是**好的**语法糖，因为它消除了 C 语言中 `else { if ... }` 的嵌套大括号地狱。

**`if` 的求值语义**：

```python
# if 的条件被隐式转换为 bool
if obj:          # 等价于 if bool(obj):
    ...

# 这意味着任何对象都可以用作条件
# Python 会调用其 __bool__ 或 __len__ 方法（详见 5.1.2）
```

### 5.1.2 Python 的真值测试：Truthy 与 Falsy

Python 的条件不仅接受 `bool` 类型——**任何对象**都可以放在 `if` 后面。这是通过一套被称为"真值测试"（truth value testing）的协议实现的。

**真值测试规则**（按优先级）：

1. 如果对象定义了 `__bool__()`，调用它——返回 `True` 或 `False`
2. 如果对象定义了 `__len__()`，调用它——`0` 为 `False`，非零为 `True`
3. 否则，对象被视为 `True`

**内置 Falsy 值**：

```python
# Python 中只有这些值是 Falsy 的——其它一切皆为 Truthy
falsy_values = [
    False,        # bool 的假值
    None,         # NoneType 的唯一值
    0,            # int 零
    0.0,          # float 零
    0j,           # complex 零
    '',           # 空字符串
    [],           # 空列表
    (),           # 空元组
    {},           # 空字典
    set(),        # 空集合
    frozenset(),  # 空冻结集合
    range(0),     # 空 range
    b'',          # 空字节串
]

# 验证
>>> for v in [False, None, 0, 0.0, 0j, '', [], (), {}, set(), frozenset(), range(0), b'']:
...     assert bool(v) is False, f"{v!r} should be falsy"
>>> print("All correct")
```

> **工程影响**：`bool` 是 `int` 的子类（`issubclass(bool, int)` 为 `True`）。这意味着 `False == 0` 且 `True == 1`。在 `isinstance(x, int)` 检查时，`True` 和 `False` 会通过——如果你需要严格区分，用 `type(x) is bool`。

**自定义类型的真值行为**：

```python
# 通过 __bool__ 控制真值
class ShoppingCart:
    def __init__(self):
        self.items = []

    def __bool__(self):
        return len(self.items) > 0   # 有商品时为 True

cart = ShoppingCart()
if cart:           # 调用 cart.__bool__()
    print("购物车不为空")
else:
    print("购物车是空的")

# 如果不定义 __bool__，Python 会退而求其次调用 __len__
class Team:
    def __init__(self, members):
        self.members = members

    def __len__(self):
        return len(self.members)
    # 没有定义 __bool__，所以 Python 用 __len__()

team = Team([])
if team:           # False——len(team) == 0
    print("有成员")
else:
    print("没有成员")
```

**`__bool__` vs `__len__` 的优先级**：

```
if obj:
    │
    ├─ type(obj).__bool__ 已定义且不是 object.__bool__？
    │   ├─ 是 → 调用它，取返回值
    │   └─ 否 → 继续
    │
    ├─ type(obj).__len__ 已定义？
    │   ├─ 是 → 调用它，0 为 False，非零为 True
    │   └─ 否 → 返回 True（默认）
```

**常见陷阱：`__len__` 返回 0 被视为 False**：

```python
# ⚠️ 潜在陷阱
class Counter:
    def __init__(self, value=0):
        self.value = value

    def __len__(self):
        return self.value

# 这看起来无害——但当 value 为 0 时，对象是 falsy 的
c = Counter(0)
if c:                    # False——因为 len(c) == 0
    print("This won't print")

# ✅ 修正：如果真值对你很重要，显式定义 __bool__
class Counter:
    def __init__(self, value=0):
        self.value = value

    def __bool__(self):
        return True       # Counter 实例始终为真

    def __len__(self):
        return self.value
```

**实用惯用法：利用真值测试简化代码**：

```python
# ❌ 冗余的真值检查
if len(items) > 0:       # 不 Pythonic
if items != []:          # 同样不好
if bool(items) is True:  # 最糟

# ✅ Pythonic 写法
if items:                 # 利用真值测试——简洁清晰

# ❌ 检查 None 的冗余写法
if value is not None and value != '':
if len(value) != 0:

# ✅ 简洁写法
if value:                 # 如果 value 为 None 或 '' 都是 falsy

# ⚠️ 但是注意——如果你需要区分 None 和空字符串
if value is not None:     # 只有 None 触发，空字符串不会
```

### 5.1.3 三元表达式：`x if condition else y`

Python 的三元表达式（条件表达式）语法与传统 C 系列语言截然不同——它读起来更像英语。

```python
# Python 语法
result = value_if_true if condition else value_if_false

# 对比 C/Java/JavaScript 语法
# result = condition ? value_if_true : value_if_false

# 示例
>>> age = 20
>>> status = "Adult" if age >= 18 else "Minor"
>>> status
'Adult'
```

**为什么 Python 选择了 `A if C else B` 而不是 `C ? A : B`？**

Guido 在 PEP 308 中对此有过详细讨论。核心原因：
1. **可读性**：`A if C else B` 遵循英语的阅读顺序——"结果 A 如果条件成立，否则结果 B"
2. **避免歧义**：`C ? A : B` 在嵌套时极难阅读（C 程序员都经历过 `a ? b : c ? d : e` 的调试地狱）
3. **与 Python 现有语法一致**：`if` 在 Python 中始终在条件之前（列表推导式的 `if` 也在条件前）

**求值策略——短路语义**：

```python
# 三元表达式是短路的——只有一个分支被求值
>>> def true_branch():
...     print("True branch evaluated")
...     return "yes"
>>> def false_branch():
...     print("False branch evaluated")
...     return "no"

>>> result = true_branch() if True else false_branch()
True branch evaluated
>>> result
'yes'

# 条件为 False 时，true_branch 根本不会被执行
>>> result = true_branch() if False else false_branch()
False branch evaluated
```

**实用场景**：

```python
# 场景 1：变量赋值时的默认值
name = user_input if user_input else "Anonymous"
# 或更简洁地（利用 or 的短路语义）
name = user_input or "Anonymous"

# 场景 2：格式化输出时根据条件选择
label = f"温度 {'偏高' if temp > 35 else '正常'}"

# 场景 3：函数返回值的条件选择
def absolute_value(x):
    return x if x >= 0 else -x

# 场景 4：列表元素的条件映射
values = [1, -2, 3, -4, 5]
processed = [x if x > 0 else 0 for x in values]  # [1, 0, 3, 0, 5]
```

**三元表达式的字节码——它确实是表达式**：

```python
>>> import dis
>>> def ternary(x):
...     return "positive" if x > 0 else "non-positive"
>>> dis.dis(ternary)
              LOAD_FAST                0 (x)
              LOAD_CONST               1 (0)
              COMPARE_OP               4 (>)         # x > 0
              POP_JUMP_IF_FALSE        1 (to L1)
              LOAD_CONST               2 ('positive')
              RETURN_VALUE
        >> L1  LOAD_CONST               3 ('non-positive')
              RETURN_VALUE
```

三元表达式编译为条件跳转，与 `if/else` 语句产生相同的控制流——区别在于三元表达式求值为一个值，可以嵌入更大的表达式中。

### 5.1.4 条件表达式的嵌套与可读性边界

三元表达式可以嵌套，但**嵌套三层就失去了 Python 选择 `A if C else B` 语法的初衷**。

```python
# 两级嵌套——可接受，但需要括号帮助阅读
result = (
    "Hot" if temperature > 35 else
    "Warm" if temperature > 20 else
    "Cool" if temperature > 10 else
    "Cold"
)

# ✅ 更好的选择：对于多级判断，用 if/elif/else
if temperature > 35:
    feeling = "Hot"
elif temperature > 20:
    feeling = "Warm"
elif temperature > 10:
    feeling = "Cool"
else:
    feeling = "Cold"

# ❌ 过度嵌套的三元表达式——不可读
# result = a if x else b if y else c if z else d
```

**决策：三元表达式 vs if/elif/else vs 字典映射**

```python
# 情况 A：二选一 → 三元表达式
status = "Adult" if age >= 18 else "Minor"

# 情况 B：三到四个分支 → if/elif/else
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
elif score >= 70:
    grade = 'C'
else:
    grade = 'F'

# 情况 C：固定值映射 → 字典（最高效）
status_codes = {
    200: "OK",
    301: "Moved Permanently",
    404: "Not Found",
    500: "Internal Server Error",
}
message = status_codes.get(code, f"Unknown status: {code}")

# 情况 D：条件来自数据（非硬编码） → 配置驱动的 if/elif
# 或使用 match/case（Python 3.10+，见 5.1.5）
```

### 5.1.5 `match`/`case`：结构化模式匹配（Python 3.10+）

Python 3.10 引入的 `match`/`case` 是 Python 历史上最大的语法扩展之一。它远不止是 C 语言 `switch` 的替代品——它是一套**结构化模式匹配**引擎，可以解构嵌套数据、绑定变量、附加守卫条件。

```python
# 基础用法——类似 switch，但更强大
def http_status_message(code):
    match code:
        case 200:
            return "OK"
        case 301 | 302 | 307:          # | 表示"或"——多个备选模式
            return "Redirect"
        case 404:
            return "Not Found"
        case 500:
            return "Internal Server Error"
        case _:                          # _ 是通配符——匹配一切
            return f"Unknown: {code}"
```

**模式的类型——从简单到高级**：

```python
# 1. 字面量模式 —— 与常量比较
match value:
    case 0:
        print("Zero")
    case 1:
        print("One")
    case True:         # ⚠️ 注意：True 在这里会匹配 1（因为 bool 是 int 的子类）
        print("True")
    case None:
        print("None")

# 2. 捕获模式 —— 绑定到变量
match command:
    case "quit":
        print("Exiting")
    case cmd:           # cmd 绑定到任意值（捕获一切）
        print(f"Unknown command: {cmd}")

# 3. 序列模式 —— 解构列表/元组
match point:
    case (0, 0):
        print("原点")
    case (0, y):
        print(f"在 y 轴上，y={y}")
    case (x, 0):
        print(f"在 x 轴上，x={x}")
    case (x, y):
        print(f"点 ({x}, {y})")
    case [x, y, z]:          # 列表也可以
        print(f"3D 点 ({x}, {y}, {z})")

# 4. 映射模式 —— 解构字典
match config:
    case {"host": host, "port": port}:
        print(f"连接 {host}:{port}")
    case {"host": host, "port": port, **rest}:
        print(f"连接 {host}:{port}，额外选项: {rest}")

# 5. 类模式 —— 匹配数据类/命名元组
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

match shape:
    case Point(x=0, y=0):
        print("原点")
    case Point(x=x, y=y):
        print(f"点 ({x}, {y})")

# 6. 守卫条件 —— 在模式上附加条件
match value:
    case x if x < 0:
        print(f"负数: {x}")
    case x if x > 0:
        print(f"正数: {x}")
    case 0:
        print("零")
```

**`match`/`case` 与 `if`/`elif` 的关键差异**：

| 特性 | `match`/`case` | `if`/`elif` |
|------|---------------|-------------|
| 求值方式 | 将 `match` 对象与各 `case` 模式逐一匹配 | 对每个 `elif` 条件表达式逐一求值 |
| 变量绑定 | 模式可以直接绑定变量（如 `case (x, y)`） | 需要手动提取/解构 |
| 结构解构 | 内置解构序列、映射、类实例 | 需要写显式解构代码 |
| 守卫 | `case` 后可跟 `if` 守卫 | 本身就是守卫 |
| 穷尽性检查 | 没有——未匹配的 case 静默通过 | 没有——但 `else` 提供兜底 |
| 性能 | 对于纯字面量匹配，CPython 可能做跳转表优化 | 逐个求值，O(n) |

**match/case 的字节码——为什么它不只是语法糖**：

```python
>>> import dis
>>> def match_example(code):
...     match code:
...         case 200:
...             return "OK"
...         case 404:
...             return "Not Found"
...         case _:
...             return "Unknown"
>>> dis.dis(match_example)
  2           RESUME                   0
  3           LOAD_FAST                0 (code)
              LOAD_CONST               1 (200)
              COMPARE_OP              40 (==)       # code == 200
              POP_JUMP_IF_FALSE        1 (to L1)
  4           LOAD_CONST               2 ('OK')
              RETURN_VALUE
  5     >> L1  LOAD_FAST               0 (code)
              LOAD_CONST               3 (404)
              COMPARE_OP              40 (==)       # code == 404
              POP_JUMP_IF_FALSE        1 (to L2)
  6           LOAD_CONST               4 ('Not Found')
              RETURN_VALUE
  7     >> L2  LOAD_CONST               5 ('Unknown')  # case _: 通配符
              RETURN_VALUE
```

对于简单字面量模式，`match`/`case` 被编译为与 `if`/`elif` 几乎相同的比较+跳转指令。但对于序列解构、类模式等复杂匹配，CPython 会生成专用的 `MATCH_SEQUENCE`、`MATCH_MAPPING`、`MATCH_KEYS` 等字节码指令（Python 3.10+），这才是 `match`/`case` 真正的底层优势。
```

**match 的常见陷阱**：

```python
# ⚠️ 陷阱 1：所有简单名称都是捕获变量
# 你可能会以为 case 中的大写名会被当作常量引用——但这是错的。
# match/case 中，所有简单名称（无论大小写）都是捕获变量！
NOT_FOUND = 404

match code:
    case NOT_FOUND:    # 这不会匹配 NOT_FOUND 变量的值！
        # 实际上 NOT_FOUND 被当作捕获变量——匹配一切
        print("匹配一切，NOT_FOUND 被绑定到 code 的值")
    case 404:           # 这个字面量永远不会到达——上面的 case 捕获了一切
        print("Not Found")

# ✅ 修正：使用枚举或类属性来引用常量
from enum import Enum

class Status(Enum):
    NOT_FOUND = 404

match code:
    case Status.NOT_FOUND.value:   # 或在守卫中使用
        print("Not Found")

# 或使用守卫
match code:
    case x if x == NOT_FOUND:
        print("Not Found")

# ⚠️ 陷阱 2：序列模式的贪婪性
match [1, 2, 3]:
    case [x, y]:         # 不匹配——3 个元素 < 2 个模式
        pass
    case [x, y, z]:
        print(f"{x}, {y}, {z}")   # 匹配——1, 2, 3

# ⚠️ 陷阱 3：映射模式的"包含"语义而非"等于"语义
match {"a": 1, "b": 2}:
    case {"a": x}:       # 匹配！映射模式检查键的包含关系
        print(f"a = {x}")   # 输出 a = 1——键 "b" 被忽略
```

**什么时候用 match/case，什么时候用 if/elif？**

| 场景 | 推荐 |
|------|------|
| 简单值比较（整数、字符串） | `if/elif` |
| 解构嵌套数据结构 | `match/case` |
| 多分支，每个分支有复杂条件 | `if/elif` |
| 按数据结构"形状"分发（如 AST 遍历） | `match/case` |
| 只有 2-3 个分支 | `if/elif` |

> **版本注意**：`match`/`case` 是 Python 3.10（2021 年 10 月）引入的。如果你的代码需要支持 Python 3.9 及更早版本，使用 `if`/`elif`。

### 5.1.6 条件语句的性能考量

**短路求值**是所有条件语句的核心优化——一旦能确定结果，剩下的条件不会被求值。

```python
# 将最可能为假的条件放在前面（对于 and 链）
if user_is_active and user_has_permission and expensive_database_check():
    # expensive_database_check 只在前面两个条件都为 True 时才执行
    grant_access()

# 将最可能为真的条件放在前面（对于 or 链）
result = cached_value or compute_expensive_fallback()

# if/elif 链的性能顺序
# ✅ 把最常见的 case 放在前面
if common_case_1:         # 80% 的情况
    handle()
elif common_case_2:       # 15% 的情况
    handle()
else:                      # 5% 的情况
    handle()
```

**CPython 字节码层面的条件优化**：

```python
# CPython 对 "if x is None" 这样的常见模式没有特殊优化
# 但 and/or 的短路语义是在字节码层面保证的

>>> def short_circuit(a, b):
...     return a and b and expensive()
>>> dis.dis(short_circuit)
              LOAD_FAST                0 (a)
              COPY                     1
              TO_BOOL
              POP_JUMP_IF_FALSE       18 (to L1)   # a 为假→直接返回 a
              POP_TOP
              LOAD_FAST                1 (b)
              COPY                     1
              TO_BOOL
              POP_JUMP_IF_FALSE       18 (to L1)   # b 为假→返回 b
              POP_TOP
              LOAD_GLOBAL              1 (expensive)
              CALL                     0            # 只有 a,b 都为真才调用
              RETURN_VALUE
        >> L1 ...
```

---

## 5.2 `while` 循环、`for` 循环、循环控制语句

循环是程序"重复执行"的机制。Python 只有两种循环——`while` 和 `for`——但通过迭代器协议和 `else` 子句等独特设计，它们比大多数语言中的循环更强大。

### 5.2.1 `while` 循环：条件驱动的重复

`while` 是'当条件成立时重复'——它是最基础的循环形式，所有其他循环都可以用 `while` 实现。

```python
# 基础语法
while condition:
    body

# 经典示例：计数循环
>>> count = 0
>>> while count < 5:
...     print(count, end=' ')
...     count += 1
0 1 2 3 4
```

**`while` 的字节码**：

```python
>>> def while_example(n):
...     while n > 0:
...         print(n)
...         n -= 1
>>> import dis
>>> dis.dis(while_example)
  2           RESUME                   0
  3     >>    LOAD_FAST                0 (n)
              LOAD_CONST               1 (0)
              COMPARE_OP               4 (>)          # n > 0
              POP_JUMP_IF_FALSE        4 (to L1)      # 条件为假→退出循环
  4           LOAD_GLOBAL              1 (print + NULL)
              LOAD_FAST                0 (n)
              CALL                     1
              POP_TOP
  5           LOAD_FAST                0 (n)
              LOAD_CONST               2 (1)
              BINARY_OP               23 (-=)          # n -= 1
              STORE_FAST               0 (n)
              JUMP_BACKWARD           10 (to L2)       # 跳回条件检查
  3     >> L1  RETURN_CONST             0 (None)
```

`while` 循环的核心是 `JUMP_BACKWARD` 指令——它让执行流跳回循环开头重新检查条件。循环结束时（条件为假或 `break`）执行 `POP_JUMP_IF_FALSE` 跳出。

**实用 while 模式**：

```python
# 模式 1：交互式输入循环——最常见的 while 用法
while True:
    user_input = input("Enter command (q to quit): ")
    if user_input.lower() == 'q':
        break
    process(user_input)

# 模式 2：海象运算符简化 while 循环（Python 3.8+）
# ❌ 传统写法——需要重复的 read 调用
line = file.readline()
while line:
    process(line)
    line = file.readline()

# ✅ 海象运算符——一次搞定
while line := file.readline():
    process(line)

# 模式 3：条件不定的循环（如网络重试）
max_retries = 3
attempt = 0
while attempt < max_retries:
    try:
        result = make_network_request()
        break                             # 成功——退出循环
    except NetworkError:
        attempt += 1
        time.sleep(2 ** attempt)          # 指数退避
else:
    raise RuntimeError("All retries exhausted")

# 模式 4：数值逼近——牛顿法求平方根
def sqrt_newton(n, tolerance=1e-10):
    """牛顿迭代法求平方根"""
    if n < 0:
        raise ValueError("不能对负数开平方")
    if n == 0:
        return 0
    x = n
    while True:
        next_x = (x + n / x) / 2
        if abs(next_x - x) < tolerance:
            return next_x
        x = next_x
```

**`while True`——Python 中的无限循环惯用法**：

```python
# Python 没有 "loop { }" 或 "do { } while()" 语法
# while True 是标准惯用法——编译器对其有微小优化

# ✅ Pythonic 的无限循环
while True:
    event = get_next_event()
    if event is None:    # 终止条件
        break
    process(event)

# ❌ 使用标志变量——不 Pythonic
running = True
while running:
    event = get_next_event()
    if event is None:
        running = False
    else:
        process(event)
```

### 5.2.2 `for` 循环与可迭代对象

`for` 是 Python 中最常用的循环——它遍历**可迭代对象**（iterable）中的每一个元素。与 C 风格的 `for(;;)` 不同，Python 的 `for` 是"for-each"——你不需要手写索引变量。

```python
# 基础语法
for item in iterable:
    body

# 示例
>>> for color in ['red', 'green', 'blue']:
...     print(color)
red
green
blue
```

**Python `for` vs C `for`——设计哲学的差异**：

| 语言 | 循环风格 | 示例 |
|------|---------|------|
| Python | for-each（遍历可迭代对象） | `for item in items:` |
| C / Java（传统） | 索引循环 / 迭代器 | `for (int i = 0; i < n; i++)` |
| JavaScript（现代） | 两者皆有 | `for...of` / `Array.forEach` |

```python
# Python 中如果你需要索引，用 enumerate（见 5.2.4）
# 不需要手写 for i in range(len(items))
```

**`for` 循环的底层机制**：

```python
# for 循环的实际执行过程
for item in iterable:
    process(item)

# 等价于以下代码
iterator = iter(iterable)          # 1. 调用 __iter__() 获取迭代器
while True:
    try:
        item = next(iterator)      # 2. 不断调用 __next__() 获取下一个元素
    except StopIteration:          # 3. 迭代完毕时捕获 StopIteration
        break
    process(item)                  # 4. 对每个元素执行循环体
```

这个等价代码揭示了几个关键事实：
- `for` 循环**不依赖索引**——它通过迭代器协议工作
- `StopIteration` 是循环结束的**正常信号**，不是异常错误
- 任何实现了 `__iter__` 的对象都可以被 `for` 遍历

```python
# 验证等价性
>>> class MyIterable:
...     def __init__(self, data):
...         self.data = data
...     def __iter__(self):
...         return iter(self.data)

>>> for item in MyIterable([1, 2, 3]):
...     print(item)
1
2
3
```

**`for` 循环支持多种可迭代对象**：

```python
# 序列：list, tuple, str, bytes, bytearray, range
for x in [1, 2, 3]: pass
for x in (1, 2, 3): pass
for ch in "hello": pass
for i in range(5): pass

# 映射（默认遍历键）
for key in {'a': 1, 'b': 2}: pass           # 'a', 'b'
for key in {'a': 1, 'b': 2}.keys(): pass    # 同上，显式
for val in {'a': 1, 'b': 2}.values(): pass  # 1, 2
for k, v in {'a': 1, 'b': 2}.items(): pass  # ('a', 1), ('b', 2)

# 集合
for item in {1, 2, 2, 3}: pass   # 1, 2, 3（去重且无序）

# 文件对象（逐行遍历）
with open('file.txt') as f:
    for line in f:               # 惰性读取，不会一次性加载到内存
        process(line)

# 生成器——惰性求值的可迭代对象
for x in (x**2 for x in range(10)): pass

# 自定义可迭代对象
for item in MyCustomIterable(): pass
```

### 5.2.3 `range()` 深度解析

`range` 是 Python 循环中最常用的工具——但它不是列表，它是一种**惰性序列**。

**`range()` 的完整构造函数签名**：

```
range(stop)
range(start, stop)
range(start, stop, step)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start` | `int` | `0` | 起始值（包含） |
| `stop` | `int` | — | 终止值（**不包含**——半开区间 [start, stop)） |
| `step` | `int` | `1` | 步长（可为负数） |

```python
# 三种形式
>>> list(range(5))           # [0, 1, 2, 3, 4]  —— stop 不包含
>>> list(range(2, 7))        # [2, 3, 4, 5, 6]  —— [start, stop)
>>> list(range(1, 10, 2))    # [1, 3, 5, 7, 9]  —— 步长为 2
>>> list(range(10, 0, -1))   # [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
```

**为什么 `range` 不包含 `stop`？——半开区间的优势**：

```python
# 优势 1：长度 = stop - start（步长为 1 时）
>>> len(range(10)) == 10     # 直观

# 优势 2：连续切片无间隙
>>> list(range(0, 5)) + list(range(5, 10))
[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]  # 无缝衔接

# 优势 3：for i in range(len(items)) 遍历索引——常见惯用法
>>> for i in range(len(items)):
...     print(f"第 {i} 个元素: {items[i]}")
```

**`range` 不是列表——它是惰性序列**：

```python
# range 对象不存储所有元素——它只存储 start, stop, step
>>> r = range(10**9)          # 十亿个元素
>>> import sys
>>> sys.getsizeof(r)          # 只占用 48 字节（取决于平台）
48
>>> sys.getsizeof(list(r))    # 8 GB——如果尝试转为列表的话

# range 支持高效的成员检查
>>> 500_000_000 in range(10**9)    # O(1)——数学计算，不遍历
True
>>> 10**10 in range(10**9)         # O(1)
False

# range 支持索引访问
>>> range(10, 100, 3)[5]            # 10 + 3*5 = 25（O(1)计算）
25

# range 支持切片
>>> range(100)[10:20:2]             # range(10, 20, 2)
range(10, 20, 2)
```

**`range` 的关键特性**：

```python
# 相等性——比较值，而非身份
>>> range(0, 10, 2) == range(0, 11, 2)    # True——都产出 [0, 2, 4, 6, 8]
True

# 哈希——range 是可哈希的（不可变的序列）
>>> {range(5): "small range"}              # 可以作为字典键
{range(0, 5): 'small range'}

# 但 range 不支持 __mutable__ 意义上的序列操作（如 append）
>>> r = range(5)
>>> r[0] = 10                              # TypeError——range 是不可变的
TypeError: 'range' object does not support item assignment
```

**`range` 的常见陷阱**：

```python
# ⚠️ 陷阱 1：step 为 0 导致 ValueError
>>> range(1, 10, 0)
ValueError: range() arg 3 must not be zero

# ⚠️ 陷阱 2：start > stop 但 step 为正——产生空 range
>>> list(range(10, 5))                     # []
>>> list(range(10, 5, 1))                  # []

# ⚠️ 陷阱 3：浮点数不能用于 range
>>> range(0, 1, 0.1)
TypeError: 'float' object cannot be interpreted as an integer

# ✅ 如果你需要浮点数步长，用列表推导式或 numpy
>>> [i * 0.1 for i in range(11)]           # [0.0, 0.1, ..., 1.0]
# 或者
>>> import numpy as np
>>> np.arange(0, 1.1, 0.1)                # 更精确的浮点范围

# ⚠️ 陷阱 4：range 不是迭代器
>>> r = range(5)
>>> next(r)
TypeError: 'range' object is not an iterator

# range 是可迭代对象，但每次 iter() 调用产生新的迭代器
>>> it1 = iter(range(3))
>>> it2 = iter(range(3))
>>> next(it1), next(it2)
(0, 0)  # 两个独立的迭代器
```

### 5.2.4 `enumerate()` 和 `zip()`：循环中的瑞士军刀

**`enumerate()`——同时获取索引和值**：

```python
# enumerate(iterable, start=0)

# 基础用法
>>> for i, color in enumerate(['red', 'green', 'blue']):
...     print(f"{i}: {color}")
0: red
1: green
2: blue

# 自定义起始索引
>>> for i, color in enumerate(['red', 'green', 'blue'], start=1):
...     print(f"{i}: {color}")
1: red
2: green
3: blue
```

**`enumerate` 的底层实现**：

```python
# enumerate 本质上是一个产生 (index, item) 元组的迭代器
def my_enumerate(iterable, start=0):
    count = start
    for item in iterable:
        yield count, item
        count += 1
```

**`zip()`——并行遍历多个可迭代对象**：

```python
# zip(*iterables, strict=False)  —— Python 3.10+ 支持 strict 参数

# 基础用法
>>> list(zip([1, 2, 3], ['a', 'b', 'c']))
[(1, 'a'), (2, 'b'), (3, 'c')]

# 长度不同时的默认行为——截断到最短的
>>> list(zip([1, 2, 3], ['a', 'b']))
[(1, 'a'), (2, 'b')]           # 3 被静默丢弃！

# strict=True（Python 3.10+）——长度不同时抛异常
>>> list(zip([1, 2, 3], ['a', 'b'], strict=True))
ValueError: zip() argument 2 is shorter than argument 1

# 压缩任意数量的可迭代对象
>>> list(zip([1, 2], [3, 4], [5, 6]))
[(1, 3, 5), (2, 4, 6)]
```

**`zip()` 的 `strict` 参数——为什么重要**：

```python
# ⚠️ 数据丢失隐患
# 假设你期望两个列表长度一致
names = ["Alice", "Bob"]
scores = [95, 88, 92]           # 多了一个元素！

for name, score in zip(names, scores):
    print(f"{name}: {score}")   # "Alice: 95", "Bob: 88"——92 被静默丢失！

# ✅ 使用 strict=True——立即暴露 bug
for name, score in zip(names, scores, strict=True):
    print(f"{name}: {score}")   # ValueError！
```

**`enumerate` + `zip` 组合用法**：

```python
# 同时遍历索引和多个序列
names = ["Alice", "Bob", "Carol"]
math_scores = [95, 88, 92]
eng_scores = [87, 91, 85]

for i, (name, math, eng) in enumerate(zip(names, math_scores, eng_scores)):
    avg = (math + eng) / 2
    print(f"{i+1}. {name}: Math={math}, English={eng}, Average={avg:.1f}")
```

**`zip` 的逆操作——`zip(*...)` 解压缩**：

```python
>>> pairs = [(1, 'a'), (2, 'b'), (3, 'c')]
>>> numbers, letters = zip(*pairs)
>>> numbers
(1, 2, 3)
>>> letters
('a', 'b', 'c')
```

**其他实用的循环工具——`itertools`**：

```python
import itertools

# itertools.product —— 笛卡尔积（嵌套循环的替代）
>>> list(itertools.product([1, 2], ['a', 'b']))
[(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]

# itertools.chain —— 串联多个可迭代对象
>>> list(itertools.chain([1, 2], [3, 4], [5, 6]))
[1, 2, 3, 4, 5, 6]

# itertools.islice —— 惰性切片
>>> list(itertools.islice(range(100), 10, 20))
[10, 11, 12, 13, 14, 15, 16, 17, 18, 19]

# itertools.combinations / permutations —— 组合与排列
>>> list(itertools.combinations('ABC', 2))
[('A', 'B'), ('A', 'C'), ('B', 'C')]
>>> list(itertools.permutations('ABC', 2))
[('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B')]

# itertools.groupby —— 按键分组（数据需要预排序）
>>> data = [('a', 1), ('a', 2), ('b', 3), ('b', 4)]
>>> for key, group in itertools.groupby(data, key=lambda x: x[0]):
...     print(key, list(group))
a [('a', 1), ('a', 2)]
b [('b', 3), ('b', 4)]
```

### 5.2.5 `break`、`continue`、`pass`

三个关键字，三种截然不同的控制流转移目的。

**`break`——立即退出最内层循环**：

```python
# break 终止整个循环——不再执行任何迭代
>>> for i in range(10):
...     if i == 5:
...         break
...     print(i, end=' ')
0 1 2 3 4

# 实用场景：搜索并提前退出
def find_first(items, predicate):
    for item in items:
        if predicate(item):
            return item       # return 同时退出函数和循环
    return None

# 如果没有 return，用 break
found = None
for item in items:
    if predicate(item):
        found = item
        break
```

**`break` 的字节码行为**：

`break` 编译为 `JUMP_FORWARD` 或 `JUMP_ABSOLUTE` 指令，跳转到循环之后的第一条指令。它不会执行 `else` 子句（见 5.2.6）。

**`continue`——跳过当前迭代的剩余部分**：

```python
# continue 只跳过当前这次迭代——循环继续运行
>>> for i in range(10):
...     if i % 2 == 0:
...         continue          # 跳过偶数
...     print(i, end=' ')
1 3 5 7 9

# 实用场景：过滤不需要处理的元素
for line in file:
    line = line.strip()
    if not line or line.startswith('#'):
        continue              # 跳过空行和注释
    process(line)
```

**`pass`——什么也不做（但作为语法占位符）**：

```python
# pass 是"故意留空"的声明——它不是被忽略的，而是主动选择了不执行

# 场景 1：占位——后续实现
class FutureFeature:
    def not_implemented_yet(self):
        pass                 # TODO: 稍后实现

# 场景 2：空异常处理——有意忽略
try:
    might_fail()
except SomeError:
    pass                     # 这个错误可以安全忽略

# 场景 3：创建最小的可工作结构
if condition:
    pass                     # 暂不处理这种情况
else:
    handle_default()

# ⚠️ pass vs ... (Ellipsis)
# pass 是语句（什么都不做）
# ... 是表达式（Ellipsis 字面量）——返回 Ellipsis 对象
# 两者都可以用作占位符，但 pass 更语义化

def todo():
    ...                      # 可以，但不如 pass 明确

def todo():
    pass                     # ✅ 更明确的"暂未实现"
```

**`break`/`continue` 只作用于最内层循环**：

```python
# ⚠️ break 和 continue 只控制最内层循环
for i in range(3):
    for j in range(3):
        if j == 1:
            break            # 只退出内层 j 循环，i 循环继续
        print(f"({i}, {j})", end=' ')
# 输出: (0, 0) (1, 0) (2, 0)

# 如果需要在嵌套循环中跳出外层，需要额外的标志或重构
found = False
for i in range(10):
    for j in range(10):
        if matrix[i][j] == target:
            found = True
            break
    if found:
        break

# ✅ 更好的做法：提取为函数，用 return 一次性退出
def find_position(matrix, target):
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if value == target:
                return i, j
    return None
```

### 5.2.6 `for`-`else` 和 `while`-`else`：Python 最被误解的特性

Python 的循环可以带 `else` 子句——但它的行为与初学者的直觉相反。`else` 在循环**正常完成**（未被 `break` 终止）时执行，而不是在循环条件为假时执行。

```python
# for-else 的语义
for item in iterable:
    if condition(item):
        break          # 提前退出——跳过 else
else:
    # 只有当 break 没有被执行时才运行
    handle_not_found()
```

**`for-else` 的经典用例——搜索模式**：

```python
# 模式：搜索——找到就停止；没找到就执行回退逻辑
def find_and_process(items, target):
    for item in items:
        if item == target:
            print(f"Found: {item}")
            break
    else:
        # 循环完整运行，没有 break——意味着没找到
        print(f"{target} not found——creating default")
        items.append(target)

# ❌ 如果没有 for-else，你需要额外的标志变量
def find_and_process_no_else(items, target):
    found = False
    for item in items:
        if item == target:
            print(f"Found: {item}")
            found = True
            break
    if not found:
        print(f"{target} not found——creating default")
        items.append(target)
```

**`for-else` 的更多实用场景**：

```python
# 场景 1：验证所有元素——"都是"检查
def all_positive(numbers):
    for n in numbers:
        if n <= 0:
            print(f"发现非正数: {n}")
            break
    else:
        print("所有数字都为正")

# 场景 2：质数检查
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False     # 找到因子——不是质数
    else:
        return True          # 没找到因子——是质数

# 场景 3：查找——有则处理，无则创建
def get_or_create(cache, key):
    for entry in cache:
        if entry.key == key:
            return entry.value
    else:
        value = create_value(key)
        cache.append(Entry(key, value))
        return value
```

**`while`-`else`——同样的语义**：

```python
# while-else：当 while 的条件变为 False（而非 break 退出）时执行
>>> count = 0
>>> while count < 3:
...     print(count)
...     count += 1
... else:
...     print("循环正常结束")
0
1
2
循环正常结束

# break 跳过 else
>>> count = 0
>>> while count < 3:
...     if count == 2:
...         break
...     print(count)
...     count += 1
... else:
...     print("这行不会打印")
0
1
```

**`for-else` 的命名争议——为什么它叫 `else`？**

许多人认为 `else` 的名字有误导性——它听起来像"条件为假时执行"。Guido 曾表示，如果重新设计，他可能会选择 `nobreak` 这个名字。但改名已经不可能（向后兼容）。

```python
# 记忆技巧：把 else 理解为 "no break"
for item in items:
    if found:
        break
else:  # "no break"——循环没被中断
    handle_not_found()
```

### 5.2.7 循环中的变量作用域

**Python 的循环不会创建新的作用域**——这是 Python 与许多其他语言的重要区别。

```python
# for 循环变量在循环结束后仍然存在
>>> for i in range(5):
...     x = i * 2
>>> i            # 循环变量仍然可用
4
>>> x            # 循环体内的变量也可用
8

# 这与 C/Java/C++ 不同——在那些语言中，循环变量在循环结束后不再可用
# C: for (int i = 0; i < 5; i++) { }  // i 在此之后不可见
```

**循环变量的"泄漏"——是特性而非 bug**：

```python
# 这个"泄漏"在特定场景下很有用
# 如：找到某元素后，循环变量保留找到的位置

>>> for i, item in enumerate(['a', 'b', 'c', 'd', 'e']):
...     if item == 'c':
...         break
>>> print(f"'c' found at index {i}")
'c' found at index 2

# ⚠️ 但如果循环为空（空可迭代对象），变量不会被赋值
>>> for i in []:    # 循环体从未执行
...     pass
>>> i               # NameError！
NameError: name 'i' is not defined
```

**列表推导式中的变量作用域——Python 3 的关键变化**：

```python
# Python 3：列表推导式有自己的局部作用域
>>> [x**2 for x in range(5)]
[0, 1, 4, 9, 16]
>>> x               # Python 3：NameError——x 被限制在推导式内部
NameError: name 'x' is not defined

# ⚠️ Python 2 中推导式会泄漏变量（与 Python 3 不同！）
# Python 2: x 在推导式后仍可访问——这是一个常见的 bug 来源
```

**循环与闭包——经典的晚期绑定陷阱**：

```python
# ⚠️ 经典陷阱：循环中创建的函数都引用同一个变量
>>> funcs = []
>>> for i in range(3):
...     funcs.append(lambda: i)
>>> [f() for f in funcs]
[2, 2, 2]        # 全是 2——而不是 [0, 1, 2]！

# 为什么会这样？
# lambda 中的 i 是自由变量——它在调用时才查找，而不是定义时
# 循环结束后，i = 2，所有 lambda 都看到同一个 i

# ✅ 修复 1：用默认参数"快照"当前值
>>> funcs = []
>>> for i in range(3):
...     funcs.append(lambda i=i: i)     # 默认参数在定义时求值
>>> [f() for f in funcs]
[0, 1, 2]

# ✅ 修复 2：嵌套函数创建新的作用域
>>> funcs = []
>>> for i in range(3):
...     def make_func(n):
...         return lambda: n
...     funcs.append(make_func(i))
>>> [f() for f in funcs]
[0, 1, 2]
```

### 5.2.8 迭代器协议：`for` 循环的底层引擎

理解迭代器协议是理解 Python `for` 循环的关键。迭代器协议由两个方法组成：`__iter__()` 和 `__next__()`。

**核心概念**：

| 概念 | 定义 | 协议方法 |
|------|------|---------|
| **可迭代对象**（Iterable） | 可以被 `for` 遍历的对象 | `__iter__()` 返回迭代器 |
| **迭代器**（Iterator） | 跟踪遍历状态的对象 | `__iter__()` 返回自身 + `__next__()` 返回下一个元素 |

```python
# Iterable ≠ Iterator
# 可迭代对象：你可以多次遍历它
>>> lst = [1, 2, 3]
>>> for x in lst: print(x)    # 第一次遍历
1 2 3
>>> for x in lst: print(x)    # 第二次遍历——仍然有效
1 2 3

# 迭代器：只能遍历一次
>>> it = iter(lst)
>>> for x in it: print(x)     # 第一次遍历
1 2 3
>>> for x in it: print(x)     # 第二次遍历——空！迭代器已耗尽
# （不输出任何内容）
```

**手动使用迭代器**：

```python
>>> it = iter([1, 2, 3])
>>> next(it)
1
>>> next(it)
2
>>> next(it)
3
>>> next(it)
StopIteration                   # 没有更多元素

# next() 的第二个参数——提供默认值而非抛异常
>>> it = iter([1, 2, 3])
>>> next(it, None)
1
>>> next(it, None)
2
>>> next(it, None)
3
>>> next(it, None)
None                            # 优雅终止，而非 StopIteration
```

**实现自定义可迭代对象和迭代器**：

```python
# 方式 1：分开的 iterable 和 iterator（推荐——允许多次遍历）
class Fibonacci:
    """斐波那契数列——可迭代对象"""
    def __init__(self, max_n):
        self.max_n = max_n

    def __iter__(self):
        return FibonacciIterator(self.max_n)

class FibonacciIterator:
    """斐波那契数列——迭代器（持有遍历状态）"""
    def __init__(self, max_n):
        self.max_n = max_n
        self.a, self.b = 0, 1
        self.count = 0

    def __iter__(self):
        return self       # 迭代器的 __iter__ 返回自身

    def __next__(self):
        if self.count >= self.max_n:
            raise StopIteration
        result = self.a
        self.a, self.b = self.b, self.a + self.b
        self.count += 1
        return result

>>> fib = Fibonacci(10)
>>> list(fib)           # 第一次遍历
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
>>> list(fib)           # 第二次遍历——仍然有效！
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

# 方式 2：用生成器函数——更简洁（但只能遍历一次）
def fibonacci(max_n):
    a, b = 0, 1
    for _ in range(max_n):
        yield a
        a, b = b, a + b

>>> fib_gen = fibonacci(5)
>>> list(fib_gen)
[0, 1, 1, 2, 3]
>>> list(fib_gen)       # 第二次——空！
[]
```

**检查对象是否是可迭代对象 / 迭代器**：

```python
>>> from collections.abc import Iterable, Iterator

>>> isinstance([], Iterable)          # True——列表是可迭代对象
>>> isinstance([], Iterator)          # False——但列表不是迭代器

>>> isinstance(iter([]), Iterable)    # True——迭代器也是可迭代对象
>>> isinstance(iter([]), Iterator)    # True

>>> isinstance(range(10), Iterable)   # True
>>> isinstance(range(10), Iterator)   # False
```

**迭代器工具——`itertools` 模块的精华**：

```python
import itertools

# 无限迭代器
itertools.count(10, 2)          # 10, 12, 14, 16, ...（无限递增）
itertools.cycle('ABC')          # 'A', 'B', 'C', 'A', 'B', 'C', ...（无限循环）
itertools.repeat('hello', 3)    # 'hello', 'hello', 'hello'（重复 n 次）

# 组合迭代器
itertools.accumulate([1,2,3,4]) # 1, 3, 6, 10（前缀和）
itertools.pairwise('ABCDE')     # ('A','B'), ('B','C'), ('C','D'), ('D','E')  (Python 3.10+)
itertools.chain('ABC', 'DEF')   # 'A', 'B', 'C', 'D', 'E', 'F'（串联）

# 过滤迭代器
itertools.compress('ABCD', [1,0,1,0])  # 'A', 'C'（按选择器保留）
itertools.dropwhile(lambda x: x<5, [1,4,6,4,1])  # 6, 4, 1（跳过符合条件的前缀）
itertools.takewhile(lambda x: x<5, [1,4,6,4,1])  # 1, 4（取符合条件的前缀）
```

### 5.2.9 循环性能优化

**循环优化的黄金法则——把计算"提升"出循环**：

```python
# ❌ 每次迭代都重复计算
for item in items:
    result = expensive_setup() + process(item)

# ✅ 将不变量提升出循环
setup_result = expensive_setup()
for item in items:
    result = setup_result + process(item)
```

**循环优化的具体技巧**：

```python
# 1. 属性查找缓存——点号查找每次都要解析
# ❌ 每次循环都查找 list.append 属性
result = []
for item in range(1000000):
    result.append(item)

# ✅ 缓存方法引用（微小但可度量的提升）
result = []
append = result.append
for item in range(1000000):
    append(item)

# 2. 局部变量 vs 全局变量——局部变量访问快得多
# ❌ 每次迭代都查找全局变量
THRESHOLD = 100
for value in data:
    if value > THRESHOLD:
        process(value)

# ✅ 缓存到局部（在函数内部或显式局部化）
def process_data(data):
    threshold = THRESHOLD          # 局部化
    for value in data:
        if value > threshold:
            process(value)

# 3. map() / filter() vs 列表推导式 vs for 循环
# map/filter 在纯 C 函数（如 str.upper）上可能有优势
# 但对 Python 函数/ lambda，列表推导式通常更快

# 4. 生成器 vs 列表——对于大型数据，惰性求值节省内存
# ❌ 一次性加载到内存
for line in open('huge_file.txt').readlines():
    process(line)

# ✅ 惰性迭代——内存占用固定
for line in open('huge_file.txt'):
    process(line)
```

**CPython 循环的字节码开销**：

```python
# Python 循环比 C 循环慢——每次迭代都要执行大量字节码指令
# 理解这一点有助于做更好的设计决策

# ❌ Python 层面的嵌套循环——慢
for i in range(1000):
    for j in range(1000):
        result[i][j] = compute(i, j)

# ✅ 如果性能敏感，将核心循环推到 C 层面
import numpy as np
result = np.fromfunction(compute, (1000, 1000))
```

---

## 5.3 列表推导式、字典推导式、集合推导式

推导式（Comprehension）是 Python 最具特色的语法之一——它将循环和条件压缩为单个声明式表达式，在简洁性和可读性之间取得了优雅的平衡。更重要的是，推导式在 CPython 中以专门的字节码指令执行，通常比等价的 `for` 循环更快。

### 5.3.1 列表推导式

**基本语法**：

```python
# 语法
[expression for item in iterable]
[expression for item in iterable if condition]
[expression for item in iterable if condition1 and condition2]

# 经典示例
>>> [x**2 for x in range(10)]
[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

>>> [x**2 for x in range(10) if x % 2 == 0]   # 只对偶数求平方
[0, 4, 16, 36, 64]
```

**列表推导式 vs `for` 循环——等价的写法**：

```python
# 推导式
squares = [x**2 for x in range(10)]

# 等价的 for 循环
squares = []
for x in range(10):
    squares.append(x**2)
```

**带条件的推导式**：

```python
# 单一过滤条件
>>> [x for x in range(20) if x % 2 == 0]       # 过滤奇数
[0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

# 多个条件的组合——if 之间是 AND 关系
>>> [x for x in range(100) if x % 2 == 0 if x % 3 == 0]  # 能被 2 和 3 整除
[0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84, 90, 96]

# 等价于
>>> [x for x in range(100) if x % 2 == 0 and x % 3 == 0]

# if-else 在表达式部分（而非过滤条件部分）
>>> [x if x % 2 == 0 else -x for x in range(10)]    # 偶数保留，奇数变负
[0, -1, 2, -3, 4, -5, 6, -7, 8, -9]
```

**理解推导式中的 `if` 位置**：

```python
# 位置 1：if 在 for 之后 = 过滤（条件为 True 才包含）
[expression for item in iterable if condition]
#                                 ^^^^^^^^^^^^
#                                 过滤条件

# 位置 2：if-else 在表达式位置 = 映射（为每个元素选值）
[value_if_true if condition else value_if_false for item in iterable]
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# 映射表达式

# 两者结合
>>> [x**2 if x % 2 == 0 else x**3 for x in range(10) if x > 0]
[1, 4, 27, 16, 125, 36, 343, 64, 729]
# 先过滤 (if x > 0)，再映射 (偶数→平方，奇数→立方)
```

**列表推导式的字节码——为什么它更快**：

```python
>>> import dis
>>> def comprehension():
...     return [x**2 for x in range(10)]
>>> def loop():
...     result = []
...     for x in range(10):
...         result.append(x**2)
...     return result

>>> dis.dis(comprehension)
  2           RESUME                   0
              LOAD_CONST               1 (<code object <listcomp>>)
              MAKE_FUNCTION            0                 # 创建列表推导式内部函数
              LOAD_GLOBAL              1 (range + NULL)
              LOAD_CONST               2 (10)
              CALL                     1
              GET_ITER                                    # 获取 range 的迭代器
              CALL                     0                  # 调用 listcomp 函数
              RETURN_VALUE

# <listcomp> 内部 code object 的字节码：
#   BUILD_LIST               0                           # 创建空列表
#   LOAD_FAST                .0                          # 加载迭代器
#   FOR_ITER                 L_end                       # 遍历每个元素
#   STORE_FAST               x                           # 绑定到 x
#   LOAD_FAST                x
#   LOAD_CONST               2
#   BINARY_OP               8 (**)                       # x**2
#   LIST_APPEND              2                           # ★ 直接追加到内部列表
#   JUMP_BACKWARD            L_start
# L_end:
#   RETURN_VALUE                                        # 返回构建好的列表

>>> dis.dis(loop)
  3           RESUME                   0
              BUILD_LIST               0
              STORE_FAST               0 (result)        # result = []
  4           LOAD_GLOBAL              1 (range + NULL)
              LOAD_CONST               1 (10)
              CALL                     1
              GET_ITER
  4     >>    FOR_ITER                 L_end (to L1)
              STORE_FAST               1 (x)              # x = next(iterator)
  5           LOAD_FAST                0 (result)
              LOAD_METHOD              2 (append)         # ★ 每轮都查找 .append 方法
              LOAD_FAST                1 (x)
              LOAD_CONST               2 (2)
              BINARY_OP                8 (**)
              CALL                     1                  # ★ 每轮都调用方法
              POP_TOP
              JUMP_BACKWARD            L_start (to L2)
  3     >> L1  LOAD_FAST                0 (result)
  6           RETURN_VALUE
```

关键差异：推导式使用 `LIST_APPEND` 字节码直接操作内部列表缓冲区，而 `for` 循环每轮迭代都要 `LOAD_METHOD` 查找 `.append` + `CALL` 调用。这避免了属性查找和方法调用开销，是推导式比 `for` 循环快 30%-50% 的根本原因。
```

**性能对比**：

```python
>>> import timeit
>>> # 以下为典型相对性能（具体数值因机器而异）
>>> # timeit.timeit('[x**2 for x in range(1000)]', number=10000)
>>> # → 列表推导式
>>> # timeit.timeit('result = [];\nfor x in range(1000): result.append(x**2)', number=10000)
>>> # → for+append（比推导式慢 30%-50%）
```

列表推导式更快的原因：
1. **专用的 `LIST_APPEND` 字节码**——直接操作列表内部缓冲区，避免了 `.append` 的属性查找
2. **局部作用域**——推导式在自己的作用域中运行，变量查找更快
3. **避免方法调用开销**——`result.append(x)` 的每个 `.` 和 `()` 都有开销

**列表推导式的实用场景**：

```python
# 扁平化一层嵌套
>>> nested = [[1, 2], [3, 4], [5, 6]]
>>> [item for sublist in nested for item in sublist]
[1, 2, 3, 4, 5, 6]

# 等价于
>>> result = []
>>> for sublist in nested:
...     for item in sublist:
...         result.append(item)

# 字符串操作
>>> words = ['hello', 'world', 'python']
>>> [w.upper() for w in words]
['HELLO', 'WORLD', 'PYTHON']
>>> [w[0] for w in words]                     # 首字母
['h', 'w', 'p']

# 数据清洗——过滤 None 和空值
>>> data = [1, None, 3, '', 5, None, 0, 'data']
>>> [x for x in data if x is not None]
[1, 3, '', 5, 0, 'data']

# 类型转换
>>> [str(x) for x in [1, 2, 3]]
['1', '2', '3']
>>> [int(x) for x in ['1', '2', '3'] if x.isdigit()]
[1, 2, 3]

# 笛卡尔积——生成 (i, j) 组合
>>> [(i, j) for i in range(3) for j in range(2)]
[(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]
```

**海象运算符在列表推导式中的应用**：

```python
# ❌ 重复计算——expensive(x) 被调用了两次
results = [expensive(x) for x in data if expensive(x) > 0]

# ✅ 海象运算符避免重复计算（Python 3.8+）
results = [y for x in data if (y := expensive(x)) > 0]

# 更复杂的例子——在表达式和条件中都使用同一个计算值
from math import sqrt
results = [y for x in range(100) if (y := sqrt(x)) % 1 == 0]
# 只有完全平方数的平方根（整数）被保留
# [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
```

### 5.3.2 字典推导式

**基本语法**：

```python
# 语法
{key_expression: value_expression for item in iterable}
{key_expression: value_expression for item in iterable if condition}

# 经典示例——创建映射
>>> {x: x**2 for x in range(5)}
{0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# 带过滤
>>> {x: x**2 for x in range(10) if x % 2 == 0}
{0: 0, 2: 4, 4: 16, 6: 36, 8: 64}
```

**字典推导式的实用场景**：

```python
# 键值反转
>>> original = {'a': 1, 'b': 2, 'c': 3}
>>> {v: k for k, v in original.items()}
{1: 'a', 2: 'b', 3: 'c'}

# ⚠️ 注意：如果值有重复，后面的会覆盖前面的
>>> original = {'a': 1, 'b': 1, 'c': 2}
>>> {v: k for k, v in original.items()}
{1: 'b', 2: 'c'}                     # 'a' 被 'b' 覆盖了！

# 从可迭代对象构建映射
>>> words = ['apple', 'banana', 'cherry']
>>> {w: len(w) for w in words}
{'apple': 5, 'banana': 6, 'cherry': 6}

# 过滤字典的键或值
>>> scores = {'Alice': 95, 'Bob': 78, 'Carol': 88, 'Dave': 65}
>>> {name: score for name, score in scores.items() if score >= 80}
{'Alice': 95, 'Carol': 88}

# 转换键或值
>>> {name.upper(): score for name, score in scores.items()}
{'ALICE': 95, 'BOB': 78, 'CAROL': 88, 'DAVE': 65}

# 合并多个字典（后者覆盖前者）
>>> d1 = {'a': 1, 'b': 2}
>>> d2 = {'b': 3, 'c': 4}
>>> {**d1, **d2}              # 解包方式（Python 3.5+）
{'a': 1, 'b': 3, 'c': 4}

# 从两个列表创建字典
>>> keys = ['a', 'b', 'c']
>>> values = [1, 2, 3]
>>> {k: v for k, v in zip(keys, values)}
{'a': 1, 'b': 2, 'c': 3}
```

**字典推导式 vs 构造函数**：

```python
# 有些情况下直接使用 dict() 构造更简洁
>>> pairs = [('a', 1), ('b', 2), ('c', 3)]
>>> dict(pairs)                         # 更简单
{'a': 1, 'b': 2, 'c': 3}

>>> {k: v for k, v in pairs}            # 等价但更冗长
{'a': 1, 'b': 2, 'c': 3}

# 但需要转换或过滤时，推导式更合适
>>> {k.upper(): v * 10 for k, v in pairs}
{'A': 10, 'B': 20, 'C': 30}
```

### 5.3.3 集合推导式

**基本语法**：

```python
# 语法
{expression for item in iterable}
{expression for item in iterable if condition}

# 经典示例
>>> {x**2 for x in range(-5, 6)}
{0, 1, 4, 9, 16, 25}       # 注意去重——(-3)**2 和 3**2 都产生 9

# 带过滤
>>> {x for x in range(20) if x % 2 == 0}    # 0 到 19 的偶数
{0, 2, 4, 6, 8, 10, 12, 14, 16, 18}
```

**集合推导式 vs 列表推导式**：

```python
# 关键差异：集合自动去重且无序
>>> [x % 3 for x in range(10)]        # 列表
[0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
>>> {x % 3 for x in range(10)}        # 集合
{0, 1, 2}

# 如果你需要去重但保持顺序（Python 3.7+ 可用 dict）
>>> list(dict.fromkeys([x % 3 for x in range(10)]).keys())
[0, 1, 2]
```

**集合推导式的实用场景**：

```python
# 场景 1：去重
>>> names = ['Alice', 'Bob', 'Alice', 'Carol', 'Bob']
>>> unique_names = {name for name in names}
>>> unique_names
{'Alice', 'Bob', 'Carol'}

# 场景 2：获取文本中的所有唯一字符
>>> text = "hello world"
>>> {ch for ch in text if not ch.isspace()}
{'h', 'e', 'l', 'o', 'w', 'r', 'd'}

# 场景 3：求两个集合的交集（用推导式加过滤）
>>> set1 = {1, 2, 3, 4, 5}
>>> set2 = {4, 5, 6, 7, 8}
>>> {x for x in set1 if x in set2}            # 本质上等同于 set1 & set2
{4, 5}
# 不过对于纯交集操作，直接用 & 运算符更高效
>>> set1 & set2
{4, 5}

# 场景 4：从嵌套结构中收集所有标签
>>> articles = [
...     {'title': 'A', 'tags': ['python', 'web']},
...     {'title': 'B', 'tags': ['python', 'data']},
...     {'title': 'C', 'tags': ['web', 'design']},
... ]
>>> {tag for article in articles for tag in article['tags']}
{'python', 'web', 'data', 'design'}
```

### 5.3.4 生成器表达式

生成器表达式是**惰性求值**的推导式——它不一次性创建所有元素，而是生成一个迭代器，在需要时才计算每个元素。

```python
# 语法——用圆括号代替方括号
(expression for item in iterable)
(expression for item in iterable if condition)

# 生成器表达式 vs 列表推导式
>>> squares_list = [x**2 for x in range(10)]   # 列表——立即求值
>>> squares_gen = (x**2 for x in range(10))    # 生成器——惰性求值

>>> squares_list                                # 可以直接查看
[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
>>> squares_gen                                 # 生成器对象——不能直接查看
<generator object <genexpr> at 0x...>
>>> list(squares_gen)                           # 需要迭代才能获取值
[0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

**生成器表达式的内存优势**：

```python
>>> import sys

# 列表推导式——一次性创建 1000 万个元素的列表（~80 MB）
>>> big_list = [x**2 for x in range(10_000_000)]
>>> sys.getsizeof(big_list)                    # ~80,000,000 字节

# 生成器表达式——几乎不占内存
>>> big_gen = (x**2 for x in range(10_000_000))
>>> sys.getsizeof(big_gen)                     # ~200 字节！
```

**生成器表达式的使用场景**：

```python
# 场景 1：作为函数参数——可以省略外层括号
>>> sum(x**2 for x in range(100))              # sum 直接消费生成器
328350
# 注意：当生成器表达式是函数的唯一参数时，外层括号可以省略
# sum((x**2 for x in range(100))) 的简写

# 场景 2：处理无法一次性放入内存的大型数据
with open('huge_file.txt') as f:
    # 生成器表达式——不会一次性加载整个文件
    line_lengths = (len(line) for line in f)
    total_chars = sum(line_lengths)

# 场景 3：管道——数据流经多个生成器
numbers = (x for x in range(100) if x % 2 == 0)     # 生成偶数
squared = (x**2 for x in numbers)                    # 平方
small = (x for x in squared if x < 1000)             # 过滤
# 管道只有在你迭代时才执行——整个链条是惰性的
result = list(small)

# 场景 4：与 all() / any() 搭配使用
>>> any(x > 100 for x in range(200))                # True——不需要生成全部 200 个
>>> all(isinstance(x, int) for x in [1, 2, 'x'])    # False——遇到 'x' 就停止
```

**生成器表达式 vs 列表推导式的选择**：

| 场景 | 推荐 |
|------|------|
| 需要多次遍历结果 | 列表推导式 |
| 需要索引访问 (`result[3]`) | 列表推导式 |
| 数据可能非常大 | 生成器表达式 |
| 只迭代一次（如传给 `sum`） | 生成器表达式 |
| 需要 `len()` 查看元素数量 | 列表推导式 |
| 管道处理（链式过滤/转换） | 生成器表达式 |

**`yield`——生成器函数**：

```python
# 生成器表达式是"匿名生成器"——单行表达式
gen = (x**2 for x in range(10))

# 生成器函数——当逻辑更复杂时使用
def squares(n):
    for i in range(n):
        yield i**2

# yield 的语义：返回一个值，但保留函数的执行状态
# 下次迭代时，从 yield 之后的语句继续执行

def fibonacci_gen():
    """无限斐波那契生成器"""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

>>> fib = fibonacci_gen()
>>> [next(fib) for _ in range(10)]
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

# yield from——委托给子生成器（Python 3.3+）
def flatten(nested_list):
    for sublist in nested_list:
        yield from sublist    # 等价于 for item in sublist: yield item

>>> list(flatten([[1, 2], [3, 4]]))
[1, 2, 3, 4]
```

### 5.3.5 嵌套推导式

多层 `for` 在推导式中的顺序与普通 `for` 循环一致——**从左到右是从外到内**。

```python
# for 循环的嵌套顺序
for i in range(3):         # 外层
    for j in range(2):     # 内层
        result.append((i, j))

# 推导式中的对应写法——顺序相同！
[(i, j) for i in range(3) for j in range(2)]
#  [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]
```

**嵌套列表推导式——扁平化**：

```python
# 扁平化两层嵌套
>>> matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
>>> [item for row in matrix for item in row]
[1, 2, 3, 4, 5, 6, 7, 8, 9]

# 等价于
>>> result = []
>>> for row in matrix:
...     for item in row:
...         result.append(item)

# 扁平化并过滤
>>> [x for row in matrix for x in row if x % 2 == 0]
[2, 4, 6, 8]
```

**嵌套列表推导式——创建矩阵**：

```python
# 创建 3×3 矩阵
>>> [[i * 3 + j for j in range(3)] for i in range(3)]
[[0, 1, 2], [3, 4, 5], [6, 7, 8]]

# 理解嵌套推导式的结构
# [[内层推导式] for i in 外层迭代]
#        ↑                    ↑
#   为每个 i 生成一行       遍历每一行

# 等价于
>>> matrix = []
>>> for i in range(3):
...     row = []
...     for j in range(3):
...         row.append(i * 3 + j)
...     matrix.append(row)
```

**嵌套推导式中的过滤条件定位**：

```python
# 外层过滤——if 放在外层 for 后面
>>> [[i, j] for i in range(5) if i % 2 == 0 for j in range(3)]
[[0, 0], [0, 1], [0, 2], [2, 0], [2, 1], [2, 2], [4, 0], [4, 1], [4, 2]]
# 只有偶数 i 参与迭代

# 内层过滤——if 放在内层 for 后面
>>> [[i, j] for i in range(3) for j in range(5) if j % 2 == 0]
[[0, 0], [0, 2], [0, 4], [1, 0], [1, 2], [1, 4], [2, 0], [2, 2], [2, 4]]
# 所有 i 都参与，但只取偶数 j

# 双重过滤
>>> [[i, j] for i in range(5) if i % 2 == 0 for j in range(5) if j % 2 == 0]
[[0, 0], [0, 2], [0, 4], [2, 0], [2, 2], [2, 4], [4, 0], [4, 2], [4, 4]]
```

**嵌套推导式的可读性边界**：

```python
# ⚠️ 三层嵌套——可读性开始下降
>>> [(i, j, k) for i in range(2) for j in range(2) for k in range(2)]
# 对于许多读者来说这已经超出了舒适区

# ✅ 三层以上——回到传统 for 循环
result = []
for i in range(2):
    for j in range(2):
        for k in range(2):
            result.append((i, j, k))

# 或者提取为函数
from itertools import product
>>> list(product(range(2), repeat=3))
```

### 5.3.6 推导式 vs 传统循环：性能分析

**基准测试——不同方式的性能差异**：

```python
import timeit

# 测试 1：简单映射——平方运算
setup = "data = list(range(1000))"

# 列表推导式
t1 = timeit.timeit("[x**2 for x in data]", setup, number=10000)

# for 循环 + append
t2 = timeit.timeit("""
result = []
for x in data:
    result.append(x**2)
""", setup, number=10000)

# for 循环 + 预分配（对于大列表可能更快）
t3 = timeit.timeit("""
result = [0] * len(data)
for i, x in enumerate(data):
    result[i] = x**2
""", setup, number=10000)

# map + lambda
t4 = timeit.timeit("list(map(lambda x: x**2, data))", setup, number=10000)

# map + 内置函数（最快！）
# 对于纯 C 实现的可调用对象，迭代全程在 C 层面执行
t5 = timeit.timeit("list(map((2).__rpow__, data))", setup, number=10000)
# (2).__rpow__(x) 等价于 x**2，__rpow__ 是 C 函数

# 典型结果（相对速度，依机器和 Python 版本而异）：
# 列表推导式 ≈ for+append 的 1.3-1.5x
# map + lambda ≈ for+append 的 0.8x（更慢！——lambda 是 Python 调用）
# map + 内置 C 函数 ≈ 列表推导式的 2x（最快！——全程 C 执行）
```

**为什么 `map` + C 函数最快？**

`map` 在纯 C 实现的可调用对象上，整个迭代发生在 C 层面——没有 Python 字节码执行开销。但 `map` + lambda 则相反——lambda 的 Python 调用开销加上 `map` 的迭代器开销反而更慢。

```python
# 最快的选择取决于具体情况

# 1. 简单的纯计算 → 列表推导式（可读性最好）
[x**2 for x in data]

# 2. 调用 C 实现的函数 → map（性能最好）
list(map(str.upper, words))            # str.upper 是 C 函数
list(map(int, string_list))            # int 是 C 构造函数

# 3. 复杂逻辑 → for 循环（最灵活，可读性最高）
result = []
for item in data:
    if complex_condition(item):
        result.append(complex_transform(item))
```

**字典推导式的性能**：

```python
# 字典推导式同样快于等价的 for 循环
# 原因相同：专用的字节码指令 + 避免了 __setitem__ 的属性查找

# 集合推导式同理——使用专用的 SET_ADD 字节码
```

### 5.3.7 什么时候不用推导式

推导式是强大的工具，但并非万能。滥用推导式会损害可读性——而可读性是 Python 最看重的品质。

**反模式 1：推导式有副作用**

```python
# ❌ 推导式用于副作用——不要这样做！
[print(x) for x in range(10)]         # 创建了一个无用的列表
[files.remove(f) for f in stale]      # 副作用 + 浪费内存

# ✅ 推导式用于创建新集合——副作用留给 for 循环
for x in range(10):
    print(x)
for f in stale:
    files.remove(f)
```

**反模式 2：过度复杂的推导式**

```python
# ❌ 不可读的推导式
result = [f(x) if g(x) else h(x) for x in data if p(x) and q(x) or r(x)]

# ✅ 重写为 for 循环或分步处理
result = []
for x in data:
    if p(x) and q(x) or r(x):
        result.append(f(x) if g(x) else h(x))
```

**反模式 3：嵌套过深**

```python
# ❌ 三层嵌套推导式——难以理解
values = [y for row in [sub for sub in matrix if sub] for y in row if y > 0]

# ✅ 分步处理
non_empty = [sub for sub in matrix if sub]
values = [y for row in non_empty for y in row if y > 0]
```

**推导式的可读性边界——经验法则**：

```
推导式适合：
├─ 单层 for + 可选 if 过滤
├─ 两层 for（如扁平化）
├─ 简单的 if-else 表达式
└─ 容易用一句话描述的操作

推导式不适合：
├─ 有副作用的操作（print、文件 I/O、状态修改）
├─ 三个或更多 for 子句
├─ 三个或更多 if 条件
├─ 复杂的嵌套 if-else
└─ 任何需要注释才能理解的表达式
```

**推导式与调试**：

```python
# 推导式中途调试困难——没有地方插入 print
# 如果你需要调试每一步，先展开为 for 循环

# ❌ 难以调试
result = [expensive(x) for x in data if validate(x)]

# ✅ 调试友好
result = []
for x in data:
    if validate(x):
        value = expensive(x)
        print(f"x={x}, value={value}")    # 可以插入调试输出
        result.append(value)

# 调试完成后，可以再折叠为推导式
```

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 条件语句 | `if/elif/else` 是 Python 唯一的条件控制流。`elif` 编译为嵌套跳转。条件可以是任何对象——通过 `__bool__`/`__len__` 协议 |
| 真值测试 | 仅 9 类值是 falsy 的：`False`、`None`、零值（`0`/`0.0`/`0j`）、空容器（`''`/`[]`/`()`/`{}`/`set()`/`frozenset()`/`range(0)`/`b''`）。`bool` 是 `int` 的子类 |
| 三元表达式 | `A if C else B` 是 Python 唯一的条件表达式。短路求值——只有一个分支被计算。嵌套超过两层时改用 `if/elif` |
| match/case | Python 3.10+ 的结构化模式匹配。支持字面量、捕获、序列、映射、类模式 + 守卫。远不止是 switch 替代品 |
| while 循环 | 条件驱动的循环。`while True:` + `break` 是标准惯用法。海象运算符 `:=` 完美配合 while 循环 |
| for 循环 | for-each 风格——遍历任何可迭代对象。底层通过 `iter()` + `next()` + `StopIteration` 实现。不依赖索引 |
| range | 惰性不可变序列——只存 start/stop/step。O(1) 成员检查和索引。半开区间 [start, stop) |
| enumerate/zip | `enumerate` 同时获取索引和值。`zip` 并行遍历多个可迭代对象，`strict=True`（3.10+）防止数据丢失 |
| break/continue/pass | `break` 退出最内层循环。`continue` 跳过当前迭代。`pass` 是故意的空操作占位符 |
| for-else/while-else | `else` 在循环未被 `break` 终止时执行——理解为 "no break"。搜索模式的最佳表达 |
| 循环变量作用域 | Python 循环不创建新作用域——循环变量在循环后仍可访问。推导式有独立局部作用域（Python 3） |
| 迭代器协议 | Iterable = `__iter__` 返回 Iterator。Iterator = `__iter__` 返回自身 + `__next__` 返回下一个元素。`StopIteration` 是正常终止信号 |
| 列表推导式 | `[expr for x in iter if cond]`。使用 `LIST_APPEND` 字节码，比等价 for 循环快 30-50%。`if` 在 `for` 后=过滤，`if-else` 在表达式位置=映射 |
| 字典推导式 | `{k: v for x in iter if cond}`。用于键值反转、过滤、转换 |
| 集合推导式 | `{expr for x in iter if cond}`。自动去重、无序 |
| 生成器表达式 | `(expr for x in iter if cond)`。惰性求值——节省内存。适合管道处理和大型数据流。做唯一函数参数时可省略外层括号 |
| 嵌套推导式 | 从左到右 = 从外到内。两层可以接受，三层以上回到传统 for 循环 |
| 不当使用推导式 | 有副作用时不要用。过度复杂的推导式伤害可读性。调试时先展开为 for 循环 |

---

#### 练习 5

1. **真值测试陷阱**：以下代码的输出是什么？解释为什么。
   ```python
   class AlwaysTrue:
       def __bool__(self):
           return True

   class AlwaysFalse:
       def __len__(self):
           return 0

   class Tricky:
       def __bool__(self):
           return False
       def __len__(self):
           return 999

   tests = [AlwaysTrue(), AlwaysFalse(), Tricky()]
   for t in tests:
       print(bool(t))
   ```

2. **三元表达式嵌套**：用三元表达式和其他工具重写以下代码，但有一个限制——每种重写方式都不同（三元表达式、字典映射、if/elif）。哪种最可读？为什么？
   ```python
   def get_season(month):
       if month in [12, 1, 2]:
           return "Winter"
       elif month in [3, 4, 5]:
           return "Spring"
       elif month in [6, 7, 8]:
           return "Summer"
       elif month in [9, 10, 11]:
           return "Autumn"
       else:
           return "Invalid"
   ```

3. **match/case 模式匹配**：用 `match`/`case` 实现一个函数 `describe(value)`，可以识别以下模式并返回描述字符串：
   - `0` → "Zero"
   - 正整数 → "Positive: <number>"
   - 负整数 → "Negative: <number>"
   - 空列表 → "Empty list"
   - 单元素列表 → "Single: <element>"
   - 两元素列表 → "Pair: <a>, <b>"
   - `{"error": msg}` → "Error: <msg>"
   - 其它 → "Unknown: <value>"
   （需要 Python 3.10+）

4. **for-else 搜索**：用 `for`-`else` 实现 `find_first_prime(numbers)`，找到第一个质数并返回，没找到则返回 `None`。对比用标志变量的版本，哪个更清晰？

5. **循环中的闭包陷阱**：下面的代码有什么问题？写出修复后的版本。
   ```python
   handlers = []
   for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
       handlers.append(lambda msg: f"[{level}] {msg}")

   for handler in handlers:
       print(handler("Something happened"))
   ```

6. **迭代器 vs 可迭代对象**：解释以下代码的行为差异。
   ```python
   # 版本 A
   data = [1, 2, 3]
   for x in data:
       for y in data:
           print(x, y, end=' | ')

   # 版本 B
   data = iter([1, 2, 3])
   for x in data:
       for y in data:
           print(x, y, end=' | ')
   ```

7. **列表推导式优化**：以下哪些推导式可以进一步优化（用 `map`、集合推导式等）？写出优化后的版本。
   ```python
   # (a)
   [x.lower() for x in words]
   # (b)
   [x for x in data if x not in seen]
   # (c)
   [x * y for x in range(10) for y in range(10)]
   # (d)
   [x for x in data if x is not None and x != '']
   ```

8. **嵌套推导式——矩阵转置**：用嵌套列表推导式实现矩阵转置。输入是一个 m×n 矩阵（列表的列表），输出是一个 n×m 矩阵。
   ```python
   matrix = [
       [1, 2, 3],
       [4, 5, 6],
   ]
   # 期望输出：[[1, 4], [2, 5], [3, 6]]
   ```

9. **生成器表达式管道**：用生成器表达式构建一个管道，处理 `range(1000)`——先过滤出被 3 或 5 整除的数，然后求平方，再过滤出平方值小于 10000 的数，最后求和。要求整个链条不使用任何临时列表。

10. **推导式 vs 循环性能实战**：编写四个版本的"筛选出 1-1000000 中所有质数"：
    - (a) 用传统 `for` 循环
    - (b) 用列表推导式
    - (c) 用 `filter` + lambda
    - (d) 用生成器表达式（惰性求值）
    使用 `timeit` 或 `time` 模块对比四种方式的执行时间和内存占用。分析结果差异的原因。

11. **真值测试与短路求值**：给定以下代码，写出每种调用情况下的输出。
    ```python
    def mystery(a, b, c):
        return a and b or c

    # 测试用例
    print(mystery(True,  True,  False))   # ?
    print(mystery(True,  False, True))    # ?
    print(mystery(False, True,  False))   # ?
    print(mystery(0,    1,     2))        # ?
    print(mystery(1,    0,     2))        # ?
    print(mystery(1,    2,     0))        # ?
    ```
    为什么 `mystery` 不能作为三元表达式的可靠替代？在什么条件下它才能工作？

12. **`while` + 海象运算符**：以下是一个文件处理函数。用海象运算符 `:=` 简化它，同时保持完全相同的行为。
    ```python
    def process_blocks(filename, block_size=4096):
        """按块读取并处理文件"""
        results = []
        with open(filename, 'rb') as f:
            block = f.read(block_size)
            while block:
                if len(block) < block_size:
                    # 最后一个不完整的块——特殊处理
                    results.append(block.upper())
                else:
                    results.append(block)
                block = f.read(block_size)
        return results
    ```

---

**进入下一章的准备**：
- ✅ 理解 Python 的真值测试协议（`__bool__` → `__len__` → 默认 True）
- ✅ 能按场景选择合适的条件表达方式（if/elif、三元表达式、字典映射、match/case）
- ✅ 理解 `match`/`case` 的捕获语义（小写变量是捕获，大写是常量引用）
- ✅ 理解 `for`-`else` 和 `while`-`else` 的 "no break" 语义
- ✅ 理解迭代器协议——可迭代对象 vs 迭代器的区别
- ✅ 掌握 `range()` 的惰性实现和 O(1) 成员检查
- ✅ 能使用 `enumerate`/`zip`/`itertools` 写出更 Pythonic 的循环
- ✅ 能解决循环中闭包的晚期绑定问题
- ✅ 理解推导式比等价 for 循环快的原因（专用字节码 + 避免方法调用）
- ✅ 能根据场景选择合适的推导式类型（列表/字典/集合/生成器）
- ✅ 知道什么时候不应该用推导式（副作用、过深嵌套、复杂逻辑）
- ✅ 理解生成器表达式在内存和性能上的权衡
