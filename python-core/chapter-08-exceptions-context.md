# 第8章 异常处理与上下文管理器

> **学习目标**：建立"异常 = 对象"的心智模型（类型 + 参数 + 回溯）；掌握 `try`/`except`/`else`/`finally` 四件套与异常链（`raise ... from`）；理解 EAFP 哲学与"该吞还是该抛"的决策；掌握 `with` 协议的完整语义与 `contextlib` 工具箱，能写出确定性地获取/释放资源的代码——最终让程序"出错可预期、资源不泄漏"。

---

异常处理与上下文管理器，是 Python 回答两个根本问题的机制：**"程序出错时，错误信号如何产生、传播、被处理？"** 以及 **"资源（文件、连接、锁）如何保证被确定性释放？"**。这两个问题看似独立，实则共享同一套底层设施——`try`/`finally` 是 `with` 的语法内核，`with` 又是异常语义的精确化。因此本章把两者放在一起讲。

本章与前面章节的关系：第 2 章 2.9 讲了 `assert`（`raise` 的调试形态），第 5 章的迭代器协议靠 `StopIteration` 异常做控制流，第 6 章函数返回值是"正常通道"——本章补上它的"异常通道"；第 7 章 7.7.7 已经用 `Timer` 预览了 `with` 协议，7.7.2 生命周期又强调"资源清理交给 `with` 而非 `__del__`"——本章把这两个伏笔完整兑现。附录 A 对 `ExceptionGroup`（PEP 654）与零成本异常的**版本条目**，本章展开其**语义与用法**。

---

## 8.1 异常：Python 的错误信号机制

### 8.1.1 从错误码到异常对象

**程序出错时怎么报告？** 不同的语言给出了截然不同的答案：

```c
// C：返回错误码，调用方必须手动检查
int fd = open("config.json", O_RDONLY);
if (fd == -1) {                          // errno 存了错误细节
    fprintf(stderr, "open failed: %s\n", strerror(errno));
    return -1;
}
```

```go
// Go：返回 (值, error)，错误是普通值
f, err := os.Open("config.json")
if err != nil {
    return nil, err                      // 错误必须显式传递
}
```

```python
# Python：抛出异常对象——不用检查返回值，出错时"直接打断"
>>> with open("config.json") as f:       # 文件不存在时，open 抛 FileNotFoundError
...     data = f.read()
Traceback (most recent call last):
  ...
FileNotFoundError: [Errno 2] No such file or directory: 'config.json'
```

三者的本质差异在于**错误信号的传递路径**：

| 语言 | 错误信号 | 传递方式 | 漏检后果 |
|------|---------|---------|---------|
| C | 错误码（int + `errno`） | 返回值手动传递 | 忘记检查 → 静默失败 |
| Go | `error` 值 | 返回值显式传递 | 忘记检查 → 静默失败（`_` 丢弃） |
| Python | 异常对象 | **调用栈自动向上传播** | 无人捕获 → 打印 `traceback` 并终止 |

Python 的关键设计：**异常不占用返回值通道**。函数可以放心地返回"结果值"，出错时异常自动沿调用栈向上找处理器——调用链中间的每一层都不必为"转发错误"写代码（对比 Go 的层层 `if err != nil`）。代价是：**错误是隐式流动的**，你无法从函数签名看出它可能抛什么（第 12 章的类型标注可缓解）。

**"异常也是对象"。** `Exception` 是一个普通类，异常实例携带错误信息。两个关键部件：

```python
>>> e = ValueError("金额必须为正")
>>> type(e)                    # 类型：决定能被哪个 except 捕获
<class 'ValueError'>
>>> e.args                     # 参数：构造时传入的信息元组
('金额必须为正',)
>>> str(e)                     # 打印时显示的消息
'金额必须为正'
```

> **衔接 `assert`（第 2 章 2.9）**：`assert cond, msg` 是 `if not cond: raise AssertionError(msg)` 的语法糖。差别在运行时：`python -O` 下 `assert` 会被整个删除，而 `raise` 不会。所以 **`assert` 只用于调试期的不变量检查，正式的错误检查用显式的 `raise`**。

### 8.1.2 异常类层次：`BaseException` 家族树

Python 的异常是一个**类继承树**，根是 `BaseException`。这棵树决定了"捕获的粒度"：

```
BaseException                          # 一切异常的根
├── BaseExceptionGroup（3.11+）        # 异常组（8.2.5 展开）
├── GeneratorExit                      # 生成器被 close() 时抛出（第5章）
├── KeyboardInterrupt                  # Ctrl+C——用户想中断，不是 bug
├── SystemExit                         # sys.exit()——程序主动退出
└── Exception                          # ★ 常规错误的父类
    ├── ArithmeticError
    │   └── ZeroDivisionError
    ├── AssertionError
    ├── AttributeError
    ├── LookupError
    │   ├── IndexError
    │   └── KeyError
    ├── OSError
    │   └── FileNotFoundError
    ├── RuntimeError
    │   └── RecursionError
    ├── StopIteration                  # 迭代器"用尽"信号（控制流！）
    ├── TypeError
    └── ValueError
```

三个直接挂在 `BaseException` 下的类型，**都不属于 `Exception`**——这是刻意的设计：

```python
>>> try:
...     1 / 0
... except Exception:                   # ✅ 捕获"常规错误"
...     pass
>>> try:
...     raise KeyboardInterrupt()       # ❌ KeyboardInterrupt 不在 Exception 下
... except Exception:                   #    所以这里捕获不到！
...     print("捕获了？")
KeyboardInterrupt
```

**为什么？** `SystemExit`/`KeyboardInterrupt`/`GeneratorExit` 代表的不是"代码里的 bug"，而是"**需要立刻退出的信号**"——程序被要求终止、用户按了 Ctrl+C、生成器被 `close()`。如果把它们归入 `Exception`，那么"捕获一切常规错误的 `except Exception`"就会把这些退出信号一并吞掉，导致**程序该退退不了**（比如后台任务想优雅退出，却被一个宽泛的 `except` 拦住）。这直接引出一个最重要的实践规则：

> **⚠️ 陷阱——永远不要用裸 `except:`**：
> ```python
> >>> try:
> ...     1 / 0
> ... except:                    # ❌ 捕获一切，含 KeyboardInterrupt/SystemExit
> ...     pass
> ```
> 裸 `except:` 等价于 `except BaseException:`。它会吞掉 `KeyboardInterrupt`（用户按 Ctrl+C 无效）、`SystemExit`（程序退不出去），制造"杀不死"的程序。**正确的默认是 `except Exception:`**——只捕获常规错误，放行退出信号。

**常见异常速查表**（写代码时最常遇到的十来个）：

| 异常 | 触发场景 | 典型修复 |
|------|---------|---------|
| `ValueError` | 参数值不合法（`int("abc")`） | 先校验再转换 |
| `TypeError` | 类型不匹配/参数个数错（`1 + "a"`） | 检查类型或调用签名 |
| `KeyError` | 字典键不存在（`d["x"]`） | 用 `d.get("x", 默认)` |
| `IndexError` | 序列下标越界（`lst[10]`） | 检查 `len()` 或用 `try` |
| `AttributeError` | 属性不存在（`obj.xxx`） | `hasattr` 或补属性 |
| `ZeroDivisionError` | 除零 | 先判断除数 |
| `FileNotFoundError` | 打开不存在的文件 | `os.path.exists` 或 `try` |
| `StopIteration` | 迭代器耗尽（`next(it)`） | 用 `for` 或 `next(it, 默认)` |
| `RecursionError` | 递归太深 | 检查终止条件 |
| `ImportError`/`ModuleNotFoundError` | 导入失败 | 装依赖/查路径 |

**`StopIteration` 是"用异常做控制流"的合法代表。** 迭代器协议（第 5 章）要求 `__next__` 在耗尽时抛出 `StopIteration` 来告诉 `for` 循环"该结束了"——这是"异常用于控制流"最正当的场合，因为它简洁地表达了"正常路径的终止信号"。**除此之外，用异常做流程控制都是反模式**（8.3.2 详谈）。

### 8.1.3 `raise`：抛出一个异常

**`raise` 的三种形态：**

```python
>>> raise ValueError("金额必须为正")     # 形态一：raise 一个实例（最常用）
Traceback (most recent call last):
  ...
ValueError: 金额必须为正

>>> raise ValueError                    # 形态二：raise 一个类——自动实例化
Traceback (most recent call last):
  ...
ValueError

>>> def f():
...     raise ValueError("内部错误")
>>> try:
...     f()
... except ValueError:
...     raise                                # 形态三：裸 raise = 原样重新抛出
Traceback (most recent call last):
  ...
ValueError: 内部错误
```

**裸 `raise` 只在 `except` 块内合法**，它的语义是"把当前正在处理的异常**原样**重新抛出"——保留原始回溯，不新建异常对象。这在"记录日志后继续传播"的场景里是标配：

```python
>>> import logging
>>> def process(data):
...     try:
...         return data["name"]
...     except KeyError:
...         logging.exception("处理数据时缺字段")
...         raise                                # 记完日志，原样往上抛
```

**自定义异常：继承 `Exception`。** 定义自己的异常类型，是为了让调用方**精确捕获**——捕获 `ValueError` 的代码可能误伤库内部逻辑，捕获你自己的 `BizError` 则是精准的契约：

```python
class BizError(Exception):
    """业务异常：携带错误码与消息"""
    def __init__(self, code: int, message: str):
        self.code = code                       # 结构化字段
        super().__init__(message)              # Exception 的 args 存 message

>>> try:
...     raise BizError(42, "订单状态非法")
... except BizError as e:
...     print(e.code, e)                       # 42 订单状态非法
42 订单状态非法
```

> **实战建议**：自定义异常命名以 `Error`/`Exception` 结尾；**一定要继承 `Exception`，而不是 `BaseException`**（否则会误伤退出信号）；基类调用 `super().__init__(message)` 把消息存进 `args`，保证 `str(e)` 和日志可用。复杂的自定义异常体系设计见 8.3.3。

### 8.1.4 CPython 层机制：异常如何产生、传播、被处理

**异常对象长什么样？** 一个异常对象由三部分构成：**类型**（决定了能被谁捕获）、**参数**（`args`，构造时传入的信息）、**回溯**（`__traceback__`，记录"一路抛上来"的调用位置链）：

```python
>>> def inner():
...     raise ValueError("boom")
>>> def outer():
...     inner()
>>> try:
...     outer()
... except ValueError as e:
...     tb = e.__traceback__
>>> tb.tb_frame.f_code.co_name        # 最近的帧：inner
'inner'
>>> tb.tb_next.tb_frame.f_code.co_name   # 上一帧：outer
'outer'
```

`__traceback__` 是一个**链表**：每个节点对应栈上的一层调用帧，从抛出点一路指回 `try` 所在帧。解释器打印的错误报告正是沿着这条链渲染的：

```
Traceback (most recent call last):
  File "<stdin>", line 2, in outer      ← 链上第 2 层
  File "<stdin>", line 2, in inner      ← 链上第 1 层（抛出点）
ValueError: boom
```

**`raise` 的字节码。** `raise X(msg)` 编译为两段——先构造异常对象（`LOAD_GLOBAL` + `CALL`），再用 `RAISE_VARARGS` 抛出：

```python
>>> import dis
>>> def f():
...     raise ValueError("boom")
>>> dis.dis(f)
 25           LOAD_GLOBAL              1 (ValueError + NULL)
              LOAD_CONST               0 ('boom')
              CALL                     1                    # 构造异常实例
              RAISE_VARARGS            1                    # 抛出（1 = 带参数）
```

**零成本异常处理（Python 3.11+）。** 在 3.11 之前，`try` 块会在字节码里插入 `SETUP_FINALLY`，解释器对每一帧都要维护"当前 try 栈"——**即使从不抛异常，每次进入函数都有成本**。3.11 的零成本异常处理（zero-cost exception handling）改成了**把异常处理器的映射关系抽离到独立的 `ExceptionTable`**，字节码的"正常路径"里完全没有异常检查指令：

```python
>>> def safe_div(x):
...     try:
...         return 10 // x
...     except ZeroDivisionError:
...         return -1
>>> dis.dis(safe_div)
  6            NOP
  7   L1:     LOAD_SMALL_INT          10
              LOAD_FAST_BORROW         0 (x)
              BINARY_OP                2 (//)
       L2:     RETURN_VALUE            # 正常路径：零异常检查指令！
  --   L3:     PUSH_EXC_INFO           # 异常路径：由 ExceptionTable 跳转而来
  8           LOAD_GLOBAL              0 (ZeroDivisionError)
              CHECK_EXC_MATCH          # 检查异常类型是否匹配
              ...
       L4:     POP_EXCEPT
              RETURN_VALUE
ExceptionTable:
  L1 to L2 -> L3 [0]     # 字节码区间 [L1, L2) 内的异常 → 跳到 L3 处理
```

关键点：**正常执行时，解释器根本不会去看 `ExceptionTable`**——只有真正的异常发生，才按表跳转。这让 `try` 块的开销趋近于零（详见 8.3.4 的性能实测）。

> **版本注意**：异常处理器的形态随版本演进——3.11 引入零成本异常处理与 `ExceptionTable`；3.12 起特殊方法的字节码由 `LOAD_METHOD` 改为 `LOAD_SPECIAL`（`with` 的 `__enter__`/`__exit__` 调用即如此，见 8.4.2）。**"异常发生时沿表跳转"的结论在所有 3.11+ 版本一致**，字节码细节随版本变化。

**传播的查找过程。** 一个异常被 `raise` 后，解释器做两件事：先看**当前帧**有没有能匹配的处理器（查 `ExceptionTable`），没有就**销毁当前帧**（栈帧弹出）、把异常交给调用帧继续找——直到某帧匹配，或栈底无处理，此时打印 `traceback` 并退出解释器。理解这一点，"异常成本主要花在构造回溯上"（8.3.4）就好懂了：**传播本身是常数级的，贵的是把每一帧的上下文记录进 `__traceback__`**。

---

## 8.2 `try`/`except`/`else`/`finally`：异常处理四件套

`try` 语句有四个子句，各司其职。用一句话记住各自的时机：

| 子句 | 时机 |
|------|------|
| `try` | 受保护的代码块 |
| `except` | 抛异常时执行（按声明顺序匹配） |
| `else` | **没有**异常时执行 |
| `finally` | **无论**是否异常都执行（清理） |

### 8.2.1 `try`/`except`：捕获并处理

**基本形态**——捕获特定的异常类型：

```python
>>> try:
...     n = int("abc")              # 抛 ValueError
... except ValueError:
...     n = 0                       # 处理：给个默认值
>>> n
0
```

**多 `except` 按声明顺序自上而下匹配**——写在前面的优先，命中后不再继续：

```python
>>> try:
...     int("abc")
... except TypeError:                # 先匹配 TypeError
...     print("类型错误")
... except ValueError:               # 再匹配 ValueError——这次命中
...     print("值错误")
值错误
```

> **⚠️ 陷阱——捕获顺序**：子类必须写在父类**前面**，否则父类把子类截胡。因为 `ZeroDivisionError` 是 `ArithmeticError` 的子类（8.1.2 的树），下面的写法永远走不到 `ZeroDivisionError`：
> ```python
> >>> try:
> ...     1 / 0
> ... except ArithmeticError:         # ❌ 父类在前，捕获一切算术错误
> ...     print("算术错误")
> ... except ZeroDivisionError:       #    这一行是死代码
> ...     print("除零")
> 算术错误
> ```

**元组捕获——多个不相关的类型一起处理：**

```python
>>> try:
...     d = {"name": "alice"}; name = d["age"]
... except (KeyError, IndexError) as e:      # 一个处理器管多个类型
...     print("取不到:", e)
取不到: 'age'
```

**`as` 绑定异常对象**——上面用 `as e` 拿到异常实例，以便读取 `e.args` 或自定义字段。**注意作用域**：`except ... as e:` 块结束后，`e` 在 Python 3 里会被**自动删除**（`del e`），防止循环引用导致的内存泄漏：

```python
>>> try:
...     1 / 0
... except ZeroDivisionError as e:
...     pass
>>> e                      # ❌ NameError——except 块外 e 已被清理
Traceback (most recent call last):
  ...
NameError: name 'e' is not defined
```

**未捕获的异常如何传播**——沿调用栈向上找处理器，层层都没有就终止程序：

```python
>>> def inner():
...     raise KeyError("缺 key")
>>> def middle():
...     inner()                 # 不处理，继续往上抛
>>> def top():
...     try:
...         middle()
...     except KeyError as e:   # 在 top 这一层被捕获
...         print("在顶层处理:", e)
>>> top()
在顶层处理: 缺 key
```

### 8.2.2 `else`：没有异常才执行

`else` 子句在 **`try` 块成功完成、没有抛异常** 时执行。它的价值是**精确划定"受保护代码"的边界**：

```python
>>> try:
...     data = load_data()          # ① 可能抛 IOError——需要保护
... except IOError as e:
...     print("读取失败:", e)
... else:
...     print("读取成功，共", len(data), "条")   # ② 只有成功才走到这
```

为什么要用 `else` 而不是把 ② 直接写进 `try`？因为**写进 `try` 的代码出错也会被 `except` 捕获**——如果 ② 本身抛了个 `IOError`，你会错误地把"后处理代码的 bug"当成"读取失败"。`else` 把这层误伤隔开：

```python
>>> try:
...     data = load_data()
...     process(data)                  # ❌ process 里的 IOError 也被当成"读取失败"
... except IOError:
...     print("读取失败")
```

> **实战建议**：`try` 块只放"真的需要被 `except` 保护的代码"。后续处理放进 `else`——既隔离误伤，又让读者一眼看清"哪些代码可能被捕获、哪些不会"。

### 8.2.3 `finally`：无论如何都执行

`finally` 是清理钩子：**无论 `try` 正常完成、还是抛异常、还是被 `return`/`break`/`continue` 跳出，`finally` 里的代码都保证执行**：

```python
>>> def f():
...     try:
...         return "try 的返回值"
...     finally:
...         print("finally 总是执行")
>>> f()
finally 总是执行
'try 的返回值'
```

`finally` 用于释放资源——文件、锁、网络连接。它是 `with` 语句的语法内核（8.4 展开），在 `with` 出现前的 Python 2.x 里，人们正是这样写：

```python
# 老式写法：try/finally 手动释放（现在用 with）
f = open("data.txt")
try:
    data = f.read()
finally:
    f.close()               # 无论读写是否出错，都关文件
```

> **⚠️ 陷阱——`finally` 里的 `return` 会覆盖一切**。`finally` 中的 `return` 会把 try 的返回值、甚至正在传播的异常都覆盖掉（编译器会发 `SyntaxWarning`）：
> ```python
> >>> def f():
> ...     try:
> ...         return "try"
> ...     finally:
> ...         return "finally"       # ❌ 覆盖了 try 的 return
> >>> f()
> 'finally'
> ```
> **`finally` 里不要写 `return`**——它本应是"清理"的钩子，混入返回值语义会让控制流难以预测。同理，`finally` 里也不该抛异常（会覆盖正在处理的异常）。

**`finally` 与 `return` 的执行顺序**——`return` 先**求值**，再执行 `finally`，最后真正返回：

```python
>>> def f():
...     try:
...         return expensive()      # ① 先算出返回值
...     finally:
...         cleanup()               # ② 再执行清理
>>>                                  # ③ 最后把 ① 的值返回
```

### 8.2.4 异常链与上下文：`__cause__`、`__context__`、`raise ... from`

**捕获一个异常、再抛出一个新异常**是常见操作（翻译层、包装层）。问题是：新异常与原始异常的因果关系如何保留？Python 用三个字段记录：

| 字段 | 含义 | 显示 |
|------|------|------|
| `__context__` | **隐式上下文**：在 `except` 里抛新异常时自动记录"正在处理谁" | 显示 "During handling..." |
| `__cause__` | **显式原因**：`raise X from Y` 里明确指定的 `Y` | 显示 "The above exception was the direct cause" |
| `__suppress_context__` | `True` 时隐藏 `__context__`（`from None` 会设置它） | 不显示上下文 |

**默认的隐式链**——在 `except` 块里抛新异常，旧异常自动成为 `__context__`：

```python
>>> def wrapper():
...     try:
...         1 / 0
...     except ZeroDivisionError:
...         raise ValueError("计算失败")        # 隐式链接原异常
>>> wrapper()
Traceback (most recent call last):
  File "...", line 3, in wrapper
    raise ValueError("计算失败")
ValueError: 计算失败
During handling of the above exception, another exception occurred:   ← __context__
Traceback (most recent call last):
  File "...", line 2, in wrapper
    1 / 0
ZeroDivisionError: division by zero
```

**`raise X from Y`——显式指定因果**。`from` 把 `Y` 设为 `__cause__`，打印效果更明确（"这个才是直接原因"）：

```python
>>> def wrapper():
...     try:
...         int("abc")
...     except ValueError as e:
...         raise TypeError("需要数字") from e     # 显式因果
```

**`raise ... from None`——切断上下文**。有时你想把底层异常完全隐藏（不暴露内部实现细节，或底层错误对调用方毫无信息量）：

```python
>>> def public_api():
...     try:
...         _internal()                 # 内部细节
...     except InternalError:
...         raise PublicError("操作失败") from None   # 不暴露内部异常
```

> **注意一个精确的语义**：`from None` 做的是设置 `__suppress_context__ = True`（隐藏**显示**）并把 `__cause__` 设为 `None`——但 `__context__` 字段**仍然记录了**原异常。所以 `from None` 是"不展示因果"，而不是"抹掉因果"：
> ```python
> >>> try:
> ...     1 / 0
> ... except ZeroDivisionError:
> ...     raise ValueError("bad") from None
> >>> # e.__context__ 仍是 division by zero，只是不显示
> ```

> **实战建议**：三层原则——① 包装异常时**默认保留链**（不写 `from` 也行，隐式链已在）；② 要强调直接原因用 `raise X from Y`；③ 只有确认"底层异常对调用方是噪音"时才用 `from None`。**日志系统（8.3.5）与调试时，异常链是无价线索，别轻易切断。**

### 8.2.5 `ExceptionGroup` 与 `except*`（Python 3.11+，PEP 654）

**问题**：并发/批处理场景下，一次操作可能同时产生**多个**不相关的错误（十个任务，五个失败）。传统的"抛一个异常"只能报告其中一个。**PEP 654** 引入 `ExceptionGroup`：一个容器异常，可以打包任意多个子异常：

```python
>>> eg = ExceptionGroup("批处理失败", [ValueError(1), TypeError(2), ValueError(3)])
>>> eg
ExceptionGroup('批处理失败', [ValueError(1), TypeError(2), ValueError(3)])
```

**`except*` 按类型匹配子组**——`except*` 会把组里匹配某类型的子异常**成组取出**，剩下的留在组里继续匹配：

```python
>>> try:
...     raise ExceptionGroup("batch", [ValueError(1), TypeError(2)])
... except* ValueError as eg:
...     print("值错误组:", list(eg.exceptions))
... except* TypeError as eg:
...     print("类型错误组:", list(eg.exceptions))
值错误组: [ValueError(1)]
类型错误组: [TypeError(2)]
```

**`except*` 与普通 `except` 的规则差异**：

| | `except` | `except*` |
|---|---|---|
| 匹配对象 | 单个异常 | 异常组中的**子组** |
| 多个子句 | 第一个匹配即停 | 每个子句匹配自己的子组，可多次命中 |
| 与 `else`/`finally` | 可用 | 可用 |
| 嵌套组 | 支持（类型传播） | 支持（结构保留） |

**典型场景**：`asyncio.gather`、`concurrent.futures` 会把多个任务的结果聚合，失败时抛 `ExceptionGroup`（第 11 章并发展开）。手动创建组也常用于"收集所有校验错误"：

```python
>>> errors = []
>>> for field, value in {"name": "", "age": "abc"}.items():
...     if not value:
...         errors.append(ValueError(f"{field} 不能为空"))
>>> if errors:
...     raise ExceptionGroup("校验失败", errors)
Traceback (most recent call last):
  ...
ExceptionGroup: 校验失败 (1 sub-exception)
```

> **版本注意**：`ExceptionGroup`/`except*` 是 3.11 新增（PEP 654）。3.12 起内置 `ExceptionGroup` 可被 `except*` 之外的普通 `except ExceptionGroup` 整体捕获（作为单个对象处理）。若需兼容 3.11 之前的版本，标准库 `exceptiongroup`（`import exceptiongroup as eg`）提供等价实现。

---

## 8.3 异常处理哲学与工程实践

### 8.3.1 EAFP vs LBYL：两种错误处理风格

处理"可能出错的操作"，有两种截然相反的姿势：

**LBYL（Look Before You Leap，先看再跳）**——操作前先检查所有可能的失败条件：

```python
>>> if os.path.exists(path):              # 先检查
...     with open(path) as f:             # 再执行
...         data = f.read()
```

**EAFP（Easier to Ask Forgiveness than Permission，请求宽恕比请求许可容易）**——直接做，出错再捕获：

```python
>>> try:                                  # 直接干
...     with open(path) as f:
...         data = f.read()
... except OSError:                       # 失败了再说
...     data = None
```

**Python 社区强烈倾向 EAFP**，理由有三：

1. **检查与执行之间的竞态（TOCTOU）**。LBYL 的检查通过后，条件可能已经改变——`os.path.exists(path)` 返回 `True` 之后、`open` 之前文件被删了，照样抛异常。EAFP 不做"事前的许诺"，天生免疫这种窗口。
2. **检查成本翻倍**。LBYL 要为每个操作多写一套"预检"，且预检的失败模式未必与真实操作一致（`exists` 通过了，`open` 却可能因为权限失败）。EAFP 只需一次 `try` 就能覆盖所有失败模式。
3. **与鸭子类型（7.6.2）同源**。鸭子类型"不检查它是什么，只调用它做什么"，EAFP"不检查能不能做，做了再说"——两者共享同一个哲学：**行为主义优于本质主义**。

**什么时候 LBYL 合理？**

| 场景 | 选择 | 原因 |
|------|------|------|
| 操作有**明显副作用**，失败会产生脏状态 | LBYL | 先验再干，避免做一半留残局 |
| 性能极度敏感、异常路径会被高频触发 | LBYL | 抛异常要构造回溯（8.3.4） |
| 检查比操作便宜得多，且操作几乎必失败 | LBYL | 如"用户输入是否为空" |
| 常规 I/O、解析、网络 | **EAFP** | 竞态免疫 + 覆盖全面 |

> **记忆**：**EAFP 是默认**，LBYL 是性能/副作用驱动的特例。判断口诀：问自己"这个操作失败是常态还是意外？"——常态失败（输入校验）用 LBYL，意外失败（I/O、格式）用 EAFP。

### 8.3.2 该吞还是该抛：反模式清单

异常处理最大的坑，不是语法，而是**决策**。四个经典反模式：

**反模式 1：裸 `except:` 吞一切。**（8.1.2 已讲）`except:` 吞掉 `KeyboardInterrupt`/`SystemExit`，程序"杀不死"。**正确：`except Exception:`。**

**反模式 2：吞异常后无声（silent failure）。** `except` 里只有一个 `pass`，错误信息彻底消失——这是最难排查的 bug 来源：

```python
>>> try:
...     save_to_db(record)
... except DBError:
...     pass                          # ❌ 失败？谁也不知道，包括用户
```

```python
>>> try:
...     save_to_db(record)
... except DBError:
...     logger.error("保存失败", exc_info=True)   # ✅ 至少记录；需要重试就 raise
```

**反模式 3：捕获过宽。** `except Exception:` 一把抓，把 `KeyboardInterrupt` 之外的**所有**错误都当成"预期的失败"，包括程序 bug（`AttributeError`、`IndexError`）——于是真正的逻辑错误被当作"可忽略的运行时异常"吞掉：

```python
>>> try:
...     process(data)
... except Exception:                 # ❌ 连代码 bug 都吞了
...     print("出错了")               #    process 内部拼写错误也走这
```

```python
>>> try:
...     process(data)
... except (OSError, ValueError) as e:   # ✅ 只捕获"已知可能发生"的类型
...     print("预期失败:", e)
```

**反模式 4：用异常做常规流程控制。** 把 `try/except` 当 `if/else` 用（`StopIteration` 除外）：

```python
>>> # ❌ 用异常判断"键在不在"
>>> try:
...     v = d["name"]
... except KeyError:
...     v = "default"
```

```python
>>> # ✅ 用 dict.get——意图直白、更快（8.3.4）
>>> v = d.get("name", "default")
```

**该吞还是该抛的决策树：**

```
这个异常，调用方"预期"吗？
├─ 预期且能恢复 → 捕获并处理（返回默认值、重试、提示）
├─ 预期但不能在此恢复 → 记日志后 raise（或 raise ... from）
└─ 不预期（是 bug）→ 不要捕获，让它暴露、让测试抓住
```

> **实战建议**：捕获异常的宽度要**精确匹配已知可能发生的类型**；处理不了的异常**别拦住**，让调用链上层或调试器看到它。一个有用的自检：**如果你的 `except` 块里没有 `return`/`raise`/`logger`，它大概率是反模式 2。**

### 8.3.3 自定义异常体系设计

当业务足够复杂，需要一个"异常家族"。设计原则：

**① 定一个模块级基类，所有业务异常继承它。** 这样调用方只需 `except YourBaseError:` 就能捕获全部业务异常：

```python
class OrderError(Exception):            # 模块基类
    """所有订单相关异常的父类"""

class OrderNotFound(OrderError):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"订单 {order_id} 不存在")

class InvalidStatus(OrderError):
    def __init__(self, order_id, status):
        self.order_id = order_id
        self.status = status
        super().__init__(f"订单 {order_id} 状态 {status} 非法")
```

**② 异常携带结构化字段**（不只是字符串消息），让调用方程序化处理：

```python
>>> try:
...     raise OrderNotFound("A123")
... except OrderError as e:
...     if isinstance(e, OrderNotFound):
...         print("重定向到:", e.order_id)      # 访问结构化字段
...     else:
...         raise
重定向到: A123
```

**③ 与 `enum`（第 7 章）结合——错误码枚举**，替代散落的魔法数字：

```python
class ErrorCode(Enum):
    NOT_FOUND = 404
    INVALID = 422
    CONFLICT = 409

class APIError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code                 # 类型安全的错误码
        super().__init__(message)

>>> raise APIError(ErrorCode.NOT_FOUND, "资源不存在")
```

**反模式：为每个方法都造一个异常**（`UserSaveError`、`UserLoadError`...类爆炸）。**粒度应该对着"调用方要区分什么"**，而不是"每个操作一个"。绝大多数模块两三个异常就够：一个基类 + 少数几个需要单独捕获的。

### 8.3.4 性能：`try` 块几乎免费，抛异常很贵

两个性能事实，决定你该怎么写：

**① `try` 块本身几乎零成本。** 3.11 的零成本异常处理（8.1.4）让"进入/退出 `try` 块"没有指令开销——`ExceptionTable` 是静态元数据，正常路径根本不查它。用 `timeit` 实测：被 `try` 包裹与不包裹的正常代码，耗时几乎无差别（本机 3.14 实测仅约 6% 的开销，且函数体越大、占比越低）：

```python
>>> import timeit
>>> def no_try():
...     return 1 + 1
>>> def with_try():
...     try:
...         return 1 + 1
...     except Exception:      # 从不触发
...         return -1
>>> timeit.timeit(no_try, number=1_000_000)      # 裸代码
0.0152
>>> timeit.timeit(with_try, number=1_000_000)    # 套 try（3.11+）
0.0162
```

> **版本注意**：3.11 之前，`try` 块有可见开销（`SETUP_FINALLY` 每帧维护），高频函数里滥套 `try` 确实会慢。3.11 起这个顾虑基本消除——**"用 `try` 不用怕慢"成立**。

**② 抛异常很贵——贵在构造回溯。** 异常一旦抛出，解释器要沿调用栈记录每一帧的上下文（8.1.4 的 `__traceback__` 链）。实测对比：

```python
>>> def via_value(n):
...     if n < 0:
...         return None              # 哨兵值
...     return n * 2
>>> def via_raise(n):
...     try:                         # ✅ 必须捕获，否则 timeit 会崩溃
...         if n < 0:
...             raise ValueError("负值")
...         return n * 2
...     except ValueError:
...         return None
>>> # 每次都触发失败路径，测 20 万次
>>> timeit.timeit("via_value(-1)", number=200_000, globals=globals())
0.0045
>>> timeit.timeit("via_raise(-1)", number=200_000, globals=globals())
0.0203
```

同样是"失败"，走异常路径慢了约 **4~5 倍**（本机 3.14 实测）。且这个差距会随**调用栈深度**增大——回溯要记录的帧越多，构造越贵（8.1.4 的 `__traceback__` 链）。**结论**：

> **"预期会发生"的失败（常态分支）用返回值/哨兵值/`dict.get`；"不该发生"的失败（异常路径）才用异常。** 这正是 8.3.2 反模式 4 的性能依据——把异常当 `if` 用，等于每个"条件分支"都付一次回溯构造的代价。

### 8.3.5 运行时工具：`sys.exception()`、`sys.exc_info()` 与 `traceback`

处理异常时，有时需要拿到"当前正在处理的异常"做程序化检查：

**`sys.exception()`（Python 3.11 推荐）vs `sys.exc_info()`（旧）**：

```python
>>> import sys
>>> def f():
...     try:
...         1 / 0
...     except ZeroDivisionError:
...         e = sys.exception()      # 3.11+：直接返回当前异常（或 None）
...         old = sys.exc_info()     # 旧：返回三元组 (type, value, traceback)
...         return e, old
>>> e, old = f()
>>> e
ZeroDivisionError('division by zero')
>>> old[0] is ZeroDivisionError, old[1] is e, old[2] is e.__traceback__
(True, True, True)
```

**`traceback` 模块——把回溯变成字符串（日志、上报用）：**

```python
>>> import traceback
>>> try:
...     1 / 0
... except ZeroDivisionError:
...     msg = traceback.format_exc()   # 完整的 traceback 文本
>>> print(msg.splitlines()[-1])        # 最后一行是异常本身
ZeroDivisionError: division by zero
```

**`logging.exception()`——异常与日志的最佳搭档**。在 `except` 块里调用，它会**自动附带当前异常的完整回溯**：

```python
>>> import logging
>>> try:
...     process(data)
... except ValueError:
...     logging.exception("处理失败")   # 日志里自动包含 traceback
ERROR:root:处理失败
Traceback (most recent call last):
  ...
ValueError: ...
```

> **实战建议**：日志里记录异常用 `logging.exception`（或 `logger.error(msg, exc_info=True)`），它会带上 `__traceback__`——这是事后排障的唯一线索。**别只 `print(str(e))`**，那会丢掉调用栈。

---

## 8.4 上下文管理器：`with` 协议

### 8.4.1 `with` 语句的完整语义（PEP 343）

**`with` 是 Python 回答"资源如何确定性释放"的答案**（PEP 343，Python 2.5）。看它如何把 8.2.3 的 `try/finally` 压缩成一行：

```python
# 老式：try/finally 手动释放
f = open("data.txt")
try:
    data = f.read()
finally:
    f.close()

# with：资源的获取与释放成对出现
with open("data.txt") as f:
    data = f.read()          # 无论内部是否异常，f.close() 都保证执行
```

**`with` 的三步执行流程**：

```
with CM() as r:
    body
```
等价于：
```
    enter_result = CM().__enter__()   # ① 调用 __enter__，返回值绑定给 as 变量 r
    try:
        body                          # ② 执行代码块
    finally:
        CM().__exit__(...)            # ③ 无论②是否异常，都调用 __exit__
```

三个要点：
- **`__enter__` 的返回值绑定给 `as` 变量**——注意绑定的是"返回的资源"，不一定是 CM 实例本身（`open` 的 `__enter__` 返回的就是文件对象）。
- **`__exit__` 在三种情况下都被调用**：正常完成、抛异常、`return`/`break` 提前离开。
- **`with` 比手写 `try/finally` 更强**——`__exit__` 能拿到异常信息（8.4.2），可以决定吞掉还是传播；手写 `finally` 做不到"根据异常类型决策"。

> **设计哲学**：`with` 是 **RAII（Resource Acquisition Is Initialization）** 思想在 Python 的形态——C++ 靠析构函数保证资源释放，Python 靠 `with` 的**词法作用域**保证。差别在于：C++ 的析构时机由编译器决定，Python 的 `with` 把"何时释放"显式写在代码里——**更啰嗦，但更可预测**（这正是 7.7.2 说的"资源清理用 `with` 而非 `__del__`"）。

### 8.4.2 `__enter__`/`__exit__` 协议

一个对象要支持 `with`，只需实现两个方法：

| 方法 | 签名 | 返回值语义 |
|------|------|-----------|
| `__enter__(self)` | 无参数（除了 `self`） | 返回值绑定给 `as` 变量 |
| `__exit__(self, exc_type, exc_val, exc_tb)` | 三个异常参数 | **返回真值 = 吞掉异常**；`None`/`False` = 异常继续传播 |

**`__exit__` 的三个参数**是异常处理的关键：

```python
>>> class Reporter:
...     def __enter__(self):
...         return self
...     def __exit__(self, exc_type, exc_val, exc_tb):
...         if exc_type is None:
...             print("正常退出")
...         else:
...             print(f"异常退出: {exc_type.__name__}: {exc_val}")
...         return False                 # 不吞异常，让它继续传播
>>> with Reporter():
...     print("执行体")
执行体
正常退出
>>> with Reporter():
...     raise ValueError("boom")        # 执行体抛异常
异常退出: ValueError: boom
Traceback (most recent call last):
  ...
ValueError: boom                        # 因为返回了 False，异常继续传播
```

参数含义：
- `exc_type`：异常类型（如 `ValueError`）；正常退出时为 `None`
- `exc_val`：异常实例（`e.args` 可读）
- `exc_tb`：回溯对象

**返回真值 = 吞异常**——把异常"消化"在 `with` 里，不让它继续传播：

```python
>>> class Suppressor:
...     def __enter__(self): return self
...     def __exit__(self, exc_type, exc_val, exc_tb):
...         return exc_type is ValueError      # 只吞 ValueError，其余放行
>>> with Suppressor():
...     raise ValueError("被吞了")            # 不打印 traceback
>>> with Suppressor():
...     raise TypeError("放行")               # 返回 False → 继续传播
Traceback (most recent call last):
  ...
TypeError: 放行
```

**字节码：`with` 如何编译？** 用 3.14 反汇编一个 `with`（3.12+ 用 `LOAD_SPECIAL` 取特殊方法，3.11 是 `LOAD_METHOD`）：

```python
>>> import dis
>>> def f2():
...     with CM() as r:
...         return r
>>> dis.dis(f2)
 18           LOAD_GLOBAL              1 (CM + NULL)
              CALL                     0                  # 创建 CM 实例
              LOAD_SPECIAL             1 (__exit__)       # 3.12+ 取 __exit__
              LOAD_SPECIAL             0 (__enter__)      # 取 __enter__
              CALL                     0                  # 调用 __enter__()
       L1:     STORE_FAST               0 (r)             # 返回值绑定 as 变量
 19           LOAD_FAST_BORROW         0 (r)
 18   L2:     LOAD_CONST               0 (None) ×3        # 压入 (None,None,None)
              CALL                     3                  # 正常退出：__exit__(None,None,None)
              POP_TOP
              RETURN_VALUE
       L3:     PUSH_EXC_INFO
              WITH_EXCEPT_START                          # 异常退出：分发异常给 __exit__
              TO_BOOL
              POP_JUMP_IF_TRUE         2 (to L4)         # __exit__ 返回真值 → 吞异常
              RERAISE                  2                 # 否则重新抛出
```

两个分支一目了然：**正常路径压入三个 `None` 调 `__exit__`；异常路径用 `WITH_EXCEPT_START` 把异常交给 `__exit__`，看返回值决定吞还是抛**。这正好对应 `__exit__` 三参数在正常/异常时的两种形态。

### 8.4.3 自定义上下文管理器

实现一个上下文管理器有两种方式：**类实现**（`__enter__`/`__exit__`）与 **`contextmanager` 装饰器**（8.4.4）。先看类实现——第 7 章 7.7.7 的 `Timer` 是完整样本，这里看一个"连接管理"：

```python
class Connection:
    def __init__(self, dsn):
        self.dsn = dsn
        self._conn = None

    def __enter__(self):
        print(f"连接 {self.dsn}")
        self._conn = connect(self.dsn)      # 获取资源
        return self._conn                    # 返回值绑定给 as 变量

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"关闭连接" + ("（有异常）" if exc_type else ""))
        self._conn.close()                   # 释放资源——无论是否异常
        return False                         # 异常照常传播
```

> **实战建议**：类实现适合"资源有状态、退出时要做复杂处理（回滚、上报、多步清理）"的场景。如果只是"进入打印 / 退出打印"这类简单包裹，用 `contextmanager`（8.4.4）更省事。

### 8.4.4 `contextlib` 工具箱

标准库 `contextlib` 提供了"不用写类"的上下文管理器，以及一批现成的工具。

**① `@contextmanager`：把生成器函数变成上下文管理器。** 约定：**`yield` 之前的代码 = `__enter__`，`yield` 之后的代码 = `__exit__`**：

```python
>>> from contextlib import contextmanager
>>> @contextmanager
... def managed_resource():
...     print("进入")                        # yield 前 = __enter__
...     try:
...         yield "resource"                 # yield 的值 = __enter__ 的返回值
...     finally:
...         print("退出")                    # yield 后 = __exit__（finally 保证）
>>> with managed_resource() as r:
...     print("使用", r)
进入
使用 resource
退出
```

关键机制：`contextmanager` 内部把生成器包成一个上下文管理器——`__enter__` 驱动生成器到第一个 `yield`；`__exit__` 用 `GeneratorExit`/异常恢复生成器。**如果代码块抛异常，异常会在 `yield` 处被抛出**，此时可用 `try/except` 捕获：

```python
>>> @contextmanager
... def may_fail():
...     print("进入")
...     try:
...         yield 42
...     except ValueError:
...         print("代码块抛了 ValueError")
...     print("退出")
>>> with may_fail() as v:
...     raise ValueError("x")                # 在 yield 处被 except 捕获
进入
代码块抛了 ValueError
退出
```

> **⚠️ 陷阱——`yield` 后没有 `try/finally` 的裸写**：代码块抛异常时，`yield` 之后的语句**不会执行**（异常从 yield 处传播出去）。所以**需要保证的清理逻辑必须包在 `finally` 里**：
> ```python
> @contextmanager
> def bad():
>     yield "r"
>     print("清理")        # ❌ 代码块抛异常时这行不执行
>
> @contextmanager
> def good():
>     try:
>         yield "r"
>     finally:
>         print("清理")    # ✅ 无论是否异常都执行
> ```

**② `suppress`：优雅地忽略特定异常**——比 `try/except/pass` 更声明式：

```python
>>> from contextlib import suppress
>>> with suppress(FileNotFoundError):        # 文件不存在时静默通过
...     os.remove("tmp.json")               # 等价于 try/except FileNotFoundError: pass
```

**③ `ExitStack`：动态管理"数量未知"的资源。** 前面所有 `with` 都在编译期写死了资源个数；当资源个数在运行时才知道（一批连接、可配置的文件列表），用 `ExitStack`：

```python
>>> from contextlib import ExitStack
>>> def open_many(paths):
...     files = []
...     with ExitStack() as stack:          # 栈退出时，所有资源统一释放
...         for p in paths:
...             f = open(p)                 # 逐个打开
...             stack.enter_context(f)      # 注册到栈上（注意：这里传的是已打开的对象）
...             files.append(f)
...         return files                    # ExitStack 退出时全部 close
```

**`ExitStack` 的核心方法**（语义已实测）：

| 方法 | 行为 |
|------|------|
| `enter_context(cm)` | 调用 `cm.__enter__()` 并返回其结果，退出时调用 `__exit__` |
| `push(cm)` | **只注册 `__exit__`，不调用 `__enter__`**——用于"已进入的 CM 补注册" |
| `callback(fn, *args)` | 退出时调用回调（栈式，LIFO） |
| `close()` / `pop_all()` | 提前释放 / 把栈转交出去（解耦生命周期） |

> **⚠️ 陷阱——`push` vs `enter_context`**：`push(cm)` **不会**调用 `cm.__enter__()`，但退出时**仍会**调用 `cm.__exit__()`。如果 `__exit__` 依赖 `__enter__` 建立的状态，用 `push` 会踩空。**默认用 `enter_context`**，`push` 只在你已经手动进入过 CM、想补注册清理时用。

**④ 其他常用工具**：

| 工具 | 作用 |
|------|------|
| `closing(obj)` | 退出时调用 `obj.close()`（即使没实现 `__exit__`） |
| `nullcontext(enter_result)` | 空操作上下文管理器——给"可选加锁/不锁"的分支一个统一的 `with` 接口 |
| `redirect_stdout(io)` / `redirect_stderr` | 临时把输出重定向到别的流 |
| `AbstractContextManager` | 抽象基类（配合 7.6.3 的 ABC） |

**`nullcontext` 的实战——"可开关"的锁**：

```python
>>> from contextlib import nullcontext
>>> lock = threading.Lock()          # 或 None（不加锁）
>>> cm = lock if lock else nullcontext()
>>> with cm:                         # 两个分支同一个接口
...     critical_section()
```

### 8.4.5 多上下文与嵌套

**`with A as a, B as b:`——一行管理多个资源**，等价于嵌套 `with`，退出顺序**从内到外**（后进入的先退出）：

```python
>>> with open("a.txt") as fa, open("b.txt") as fb:
...     data_a = fa.read()           # 两个文件都打开
>>>                                  # 退出顺序：先 fb，后 fa（LIFO）
```

**求值顺序**：`__enter__` 从左到右依次调用；中途某个 `__enter__` 抛异常，**之前已进入的资源会立即被退出清理**（不会泄漏）。

**嵌套 `with` vs `ExitStack` 的选型**：

| 场景 | 选择 |
|------|------|
| 资源数量编译期确定（2~3 个） | `with A as a, B as b` |
| 资源数量运行时才知道（循环打开） | `ExitStack` |
| 需要条件性进入/中途退出 | `ExitStack`（`enter_context` 可按条件调用） |

```python
# 条件性进入：只有日志开启时才挂上日志处理器
with ExitStack() as stack:
    if logging_enabled:
        stack.enter_context(open_log())
    # 主体逻辑...
```

### 8.4.6 上下文管理器的陷阱与设计

**陷阱 1：`__exit__` 误吞异常。** `__exit__` 返回 `True` 会吞掉代码块的异常——如果函数**忘记写 `return`**（隐式返回 `None`）没事，但**错误地返回了 `True`**（比如 `return self.closed`），异常会被静默吞掉。**除非明确要吞，`__exit__` 一律返回 `False`/`None`。**

**陷阱 2：`contextmanager` 里"假 exit"**。8.4.4 已讲：`yield` 后不包 `finally`，异常时清理不执行。写 `contextmanager` 时**清理逻辑永远放 `finally`**。

**陷阱 3：把 `with` 当装饰品**。`with open(...)` 打开的**对象生命周期**只到 `with` 块结束——块外引用它并不会让它保持打开：

```python
>>> f = None
>>> with open("a.txt") as fh:
...     f = fh                  # 块内引用
>>> f.closed                    # ✅ 块结束，文件已被关闭（即使 f 还引用它）
True
```

**与 `__del__`/`finally` 的对比**（呼应 7.7.2 的闭环）：

| 机制 | 释放时机 | 可靠性 |
|------|---------|--------|
| `with` / `finally` | 代码块结束，**确定** | ✅ 首选 |
| `__del__` | 引用计数归零，**不确定**（循环引用、退出时序） | ❌ 只兜底 |

> **设计哲学收束**：`with` 把"获取/释放"写成一**对词法上的对称结构**，任何读者都能在一屏内看出资源边界；`__del__` 把释放藏在对象生命周期里，谁也说不准什么时候发生。**工程上要确定性，就要把生命周期显式化**——这就是本章与第 7 章 7.7.2 共同的核心结论。

> **`async with`（版本注意）**：异步代码用 `async with` 配合 `__aenter__`/`__aexit__`（PEP 492，3.5+），语义与 `with` 完全对应，只是进入/退出是协程调用（第 11 章异步编程展开）。

---

## 8.5 综合实战：事务式上下文管理器

把本章所有机制串起来，实现一个**事务**语义的资源管理器：进入时开启事务，正常退出提交，异常退出回滚。这正是 8.4.3 类实现的完整形态，也是 `with` 相对 `try/finally` 最强的地方——**`__exit__` 能根据异常参数做决策**（提交 or 回滚），手写 `finally` 做不到。

用一个内存版 `FakeDB` 让示例可运行：

```python
class FakeDB:
    """模拟数据库：记录每次操作，便于验证事务边界"""
    def __init__(self):
        self.log = []

    def begin(self):        self.log.append("BEGIN")
    def insert(self, row):  self.log.append(f"INSERT {row}")
    def commit(self):       self.log.append("COMMIT")
    def rollback(self):     self.log.append("ROLLBACK")

class Transaction:
    """事务上下文管理器：成功提交、异常回滚"""
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.begin()              # ① 进入：开启事务
        return self.db               # 绑定给 as 变量

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.db.commit()         # ② 无异常 → 提交
        else:
            self.db.rollback()       # ③ 有异常 → 回滚
            logging.exception("事务已回滚")   # 8.3.5：日志带回溯
        return False                 # ④ 异常照常传播，调用方感知失败
```

**成功路径——`BEGIN → INSERT → COMMIT`**：

```python
>>> db = FakeDB()
>>> with Transaction(db) as tx:
...     tx.insert("A")
...     tx.insert("B")
>>> db.log
['BEGIN', 'INSERT A', 'INSERT B', 'COMMIT']
```

**异常路径——`BEGIN → INSERT → ROLLBACK`，且异常继续传播**：

```python
>>> db = FakeDB()
>>> try:
...     with Transaction(db) as tx:
...         tx.insert("A")
...         raise RuntimeError("中途出错")
... except RuntimeError:
...     print("调用方感知到失败")
调用方感知到失败
>>> db.log
['BEGIN', 'INSERT A', 'ROLLBACK']
```

对比两条路径的差异：**同样一行 `with`，`__exit__` 的三个参数决定了截然不同的结局**——这就是"异常感知式资源管理"的精髓。

**增强 1：组合 `ExitStack` 管理多个事务资源。** 当一次操作跨多个事务（主库 + 从库）时，用 8.4.4 的 `ExitStack` 统一生命周期：

```python
def transfer(db_from, db_to, amount):
    with ExitStack() as stack:
        tx1 = stack.enter_context(Transaction(db_from))
        tx2 = stack.enter_context(Transaction(db_to))
        tx1.insert(f"扣款 {amount}")
        tx2.insert(f"入账 {amount}")
    # 任一步异常 → 两个事务都回滚（栈式退出，LIFO）
```

**增强 2：用异常链保留失败因果。** 回滚后若想抛一个"业务语义"的异常，用 `raise ... from`（8.2.4）保留底层原因：

```python
class TransferError(Exception): ...

def transfer(db_from, db_to, amount):
    try:
        with Transaction(db_from) as tx1, Transaction(db_to) as tx2:
            tx1.insert(f"扣款 {amount}")
            tx2.insert(f"入账 {amount}")
    except Exception as e:
        raise TransferError("转账失败，已回滚") from e   # 保留原异常链
```

**这个例子回答了一句话**：为什么 `with` 值得学？因为**资源边界 + 异常决策**这两件事，`with` 让你写在**一对对称的代码块**里——获取与释放相邻、成功与失败的分支就在 `__exit__` 的 `if exc_type is None` 里，任何读者都能在一屏内看懂整个生命周期。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 异常对象 | 类型 + `args` + `__traceback__`；异常是可实例化的对象；`assert` 是 `raise` 的调试形态 |
| 异常层次 | 根是 `BaseException`；`KeyboardInterrupt`/`SystemExit`/`GeneratorExit` 独立于 `Exception`；**裸 `except` 是反模式**，默认 `except Exception` |
| `raise` | 三形态：实例 / 类（自动实例化）/ 裸 raise（re-raise）；自定义异常继承 `Exception` 并携带结构化字段 |
| 底层机制 | 3.11+ 零成本异常（`ExceptionTable` 独立于正常路径）；传播沿栈找处理器；回溯是帧链 |
| 四件套 | `try`/`except`（按序匹配、子类在前、元组捕获）/`else`（无异常才执行）/`finally`（保证清理，别 `return`） |
| 异常链 | 隐式 `__context__` / 显式 `__cause__`（`raise ... from`）/ `from None` 抑制显示；日志 `logging.exception` 保留链 |
| `ExceptionGroup` | PEP 654 聚合多错误；`except*` 按类型取子组；并发/批处理场景（3.11+） |
| EAFP vs LBYL | EAFP 默认（免疫 TOCTOU、覆盖全面）；LBYL 用于副作用敏感 / 性能敏感 |
| 性能 | `try` 块近零成本（3.11+）；**抛异常贵**（构造回溯）——常态失败用返回值/哨兵值 |
| `with` 协议 | `__enter__` 返回绑定 `as`；`__exit__(exc_type, exc_val, exc_tb)` 返回真值吞异常；字节码 `WITH_EXCEPT_START` |
| `contextlib` | `contextmanager`（yield 前=进入、yield 后=退出，清理放 `finally`）；`suppress`；`ExitStack` 动态多资源（`push` ≠ `enter_context`）；`closing`/`nullcontext` |
| 设计哲学 | `with` = RAII 的 Python 形态；资源生命周期要**显式**；清理用 `with`/`finally`，`__del__` 只兜底 |

---

#### 练习 8

**1.（预测输出）** 下面代码打印什么？解释 `finally` 与 `return` 的执行顺序。

```python
def f():
    try:
        return "try"
    finally:
        print("清理")
print(f())
```

**2.（预测输出）** 下面代码会打印 `捕获` 吗？为什么？

```python
try:
    raise KeyboardInterrupt()
except Exception:
    print("捕获")
```

**3.（解释行为）** 分别说明 `raise X`、`raise X from Y`、`raise X from None` 对 `__cause__`/`__context__`/`__suppress_context__` 的影响，以及回溯打印的差异。

**4.（修复 bug）** 下面代码静默吞掉了所有异常。指出问题并修正，要求：只捕获 `ValueError`，其余异常照常传播，且失败时有日志。

```python
def parse(value):
    try:
        return int(value)
    except:
        return None
```

**5.（手写实现）** 用 `contextlib.contextmanager` 实现一个 `timed` 上下文管理器：进入时记开始时间，退出时打印耗时（含异常时的耗时）。

**6.（手写实现）** 用类实现一个 `AtomicFileWriter`：`__enter__` 打开临时文件，正常退出写回目标文件，异常退出删除临时文件并抛异常。说明它比"直接 `with open()`"强在哪。

**7.（解释行为）** 在 `ExceptionGroup` 里抛 `[ValueError(1), TypeError(2), ValueError(3)]`，分别写出 `except* ValueError` 与 `except* TypeError` 各自拿到的子组。

**8.（设计）** 下列场景选 EAFP 还是 LBYL，说明理由：① 从字典取值，键可能不存在；② 删除一个"大概率不存在"的临时文件；③ 解析用户输入的数字；④ 高并发下给文件加锁。

**9.（性能实验）** 用 `timeit` 对比"用异常判断除零"与"先检查再除"两种写法，在 `number=100_000` 下的耗时差距，并解释原因（提示：8.3.4）。

**10.（综合实战）** 为一个小型银行转账系统设计自定义异常体系：基类 `TransferError` + 至少三个子类（余额不足、账户不存在、金额非法），每个携带结构化字段；再写一个 `transfer(from_acct, to_acct, amount)` 函数，用 `Transaction` 模式保证"全部成功或全部回滚"，失败时抛带异常链的业务异常。

---

**进入下一章的准备**：

- ✅ 能画出 `BaseException` 家族树，说出三个非 `Exception` 子类存在的原因
- ✅ 能说清 `try/except/else/finally` 四个子句的时机，并解释 `finally` 里 `return` 的陷阱
- ✅ 能区分 `__context__`/`__cause__`/`__suppress_context__`，会正确使用 `raise ... from`
- ✅ 能解释 3.11 零成本异常的原理，以及"为什么抛异常很贵"
- ✅ 能判断 EAFP 与 LBYL 的适用场景
- ✅ 能写出 `with` 协议（`__enter__`/`__exit__`）与 `contextmanager` 版本
- ✅ 会用 `ExitStack` 管理运行时才知道数量的资源，能说出 `push` 与 `enter_context` 的区别

> **衔接预告**：第 9 章"文件 I/O 与序列化"将是本章知识的最大应用场——`with open(...)` 的每个细节（缓冲、编码、`TextIOBase` 协议）都建立在本章之上；第 11 章"并发与异步编程"会用到 `async with` 与 `ExceptionGroup` 聚合任务错误；第 12 章"元编程"则会展示如何用装饰器与元类**自动生成**上下文管理器。
