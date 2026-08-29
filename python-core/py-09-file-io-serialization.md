# 第9章 文件 I/O 与序列化

> **学习目标**：建立"文件 = 字节流 + 缓冲 + 编码器"的分层心智模型；掌握 `open()` 每一个参数的**真实语义**（模式、编码、换行、缓冲）；分清文本 / 二进制 / 随机访问三类 I/O 的适用场景；理解序列化的本质——把对象状态变成字节——并能在"安全"与"跨语言"之间正确选择 `pickle` / `json`。

---

第 8 章把 `with open(...)` 当成黑盒：它只告诉你"盒子会保证文件被关闭"，却没解释盒子内部是什么。本章掀开盒子。打开一个文件，Python 实际做的是**三段式包装**：一个文件描述符（fd）在最底层，上面叠一层缓冲减少系统调用，再上面叠一层编码器处理文本。`open()` 一个函数，背后是这条调用链的组装工厂。

本章与前面章节的关系：第 2 章 2.8 的 `print`/`input` 和 2.6 赋值节的 `readline` 海象示例第一次碰了文件，但那是"会用"；第 3 章 3.2.7 讲了 Unicode 与编码常识，本章把编码**落到文件层**（BOM、错误策略、UTF-8 mode），并展开 PEP 597/686 的工程含义；第 5 章的迭代器协议、第 8 章的 `with` 协议，本章是它们的**复用现场**——文件对象同时是迭代器和上下文管理器；第 7 章 7.7.2 强调"资源清理交给 `with` 而非 `__del__`"，本章 `with open()` 就是这句话最日常的兑现。

---

## 9.1 文件 I/O 的分层体系：从系统调用到文本流

### 9.1.1 文件是什么：文件描述符、系统调用与 Python 对象

先回到操作系统视角，再谈 Python。

**文件在 OS 里是什么？** 是一段**命名了的字节序列**，存在磁盘上。进程要读写它，不能直接操作磁盘，只能通过系统调用：

```c
// 打开 -> 拿到一个整数句柄（文件描述符，fd）
int fd = open("a.txt", O_RDONLY);     // fd = 3（0/1/2 被 stdin/stdout/stderr 占用）
char buf[4096];
ssize_t n = read(fd, buf, sizeof buf); // 一次 read = 一次系统调用
```

fd 是**当前进程**的打开文件表里的一个下标。同一文件的两次 `open` 拿到两个不同的 fd，各自有独立的文件位置指针。fd 不是文件本身，是"句柄"——关闭 fd 只是切断进程与文件的联系，文件还在磁盘上。

**关键概念：每次 `read()`/`write()` 都是系统调用**——从用户态陷入内核态，拷贝数据、查页缓存，开销不小。所以任何语言的 IO 库都会在中间加一层**缓冲**：攒一批字节再一次系统调用。这就是"分层"的根本动机。

对比其他语言对"文件"的抽象，都是"fd + 缓冲"的变体：

| 语言 | 文件抽象 | 层级 |
|------|---------|------|
| C | `FILE*`（`fopen`） | `FILE*` 内部有缓冲，再包 fd |
| Java | `FileInputStream` → `BufferedInputStream` → `InputStreamReader` | 显式装饰器链，**字节流 + 缓冲 + 字符流**逐层包 |
| Python | `open()` 返回分层对象 | `TextIOWrapper` → `BufferedReader` → `FileIO`，和 Java 几乎同构 |

Java 的"装饰器链"和 Python 的"分层包装"是同一思想：把"读字节"、"缓冲"、"编码"拆成独立组件，按需组合。C 语言把三件事糊在一个 `FILE*` 里，简单但不灵活；Python 学 Java，拆开了。

> **设计哲学**：`open()` 返回的对象**不是**一个"文件"，而是一个**分层堆栈**。理解这一点，后面所有"为什么 `encoding=` 不管用""为什么 `flush()` 没用"的困惑都会消失——因为你始终知道自己站在堆栈的哪一层。

### 9.1.2 `io` 模块三层架构：`RawIOBase` → `BufferedIOBase` → `TextIOBase`

Python 的 `io` 模块定义了这套分层的类。真实文件对象的类属于标准库的三个抽象基类之一：

```
io.IOBase                     # 所有 IO 对象的基类：close/flush/seekable/closed...
 ├── io.RawIOBase             # 原始层：直接系统调用，操作字节，无缓冲
 │     └── _io.FileIO         # open() 真正打开 fd 的那个对象
 ├── io.BufferedIOBase        # 缓冲层：攒字节，减少系统调用次数
 │     ├── _io.BufferedReader     # 读缓冲
 │     ├── _io.BufferedWriter     # 写缓冲
 │     ├── _io.BufferedRandom     # 可读可写（r+/w+ 等模式）
 │     └── _io.BufferedRWPair
 └── io.TextIOBase            # 文本层：字节 <-> 字符 编解码 + 换行翻译
       └── _io.TextIOWrapper
```

`open()` 根据**模式字符串**决定组装哪几层。实测（3.14）：

```python
>>> f = open("a.txt")            # 默认 'r'——文本模式
>>> type(f)
<class '_io.TextIOWrapper'>      # 文本层在最外面
>>> type(f.buffer)               # 穿过文本层，看它的缓冲层
<class '_io.BufferedReader'>
>>> type(f.buffer.raw)           # 再往下一层，才是真正的文件对象
<class '_io.FileIO'>
```

各模式的组装结果：

| 模式 | 最外层 `type(f)` | `.buffer`（若有） | `.raw` |
|------|----------------|------------------|--------|
| `'r'` / `'w'` / `'a'` | `TextIOWrapper` | `BufferedReader` / `BufferedWriter` / `BufferedWriter` | `FileIO` |
| `'rb'` / `'wb'` / `'ab'` | `BufferedReader` / `BufferedWriter` / `BufferedWriter` | —（自身即缓冲层） | `FileIO` |
| `'r+'` / `'w+'` / `'a+'` | `TextIOWrapper` | `BufferedRandom` | `FileIO` |
| `'r+b'` / `'w+b'` | `BufferedRandom` | — | `FileIO` |

**三层的职责，就是 9.1.1 说的"拆分"**：

- **`FileIO`（RawIOBase）**：唯一真正调系统调用的层。持有 fd，负责 `read()`/`write()`/`seek()` 的裸字节版本。它不认识字符，不知道编码。
- **缓冲层（BufferedIOBase）**：在用户态维护一块缓冲区。`f.read(1)` 表面上只读 1 字节，实际可能一次从内核读走 8 KiB 存进缓冲，下次 `read` 直接从缓冲取。缓冲层把"多次小读"合并成"少数大系统调用"。
- **文本层（`TextIOWrapper`）**：在缓冲层的字节之上加编码器。`write("中文")` 进来是字符，编码器把它变成 UTF-8 字节再交给缓冲层；`read()` 则是反向解码。同时负责 universal newlines（9.2.3）。

> **注意**：文本模式 `open()` 返回 `TextIOWrapper`，但 `type(f)` 显示的是 `_io.TextIOWrapper`——`_io` 是 C 实现的模块名（CPython 的 `Modules/_io/`）。`io` 模块本身是纯 Python 接口层，把 C 实现暴露出来。这和 `collections.abc` 与具体类型的关系类似。

**打开文件时只有一次真正的系统调用**：最底层的 `FileIO` 调 `open(2)` 拿到 fd；上面两层只是"包装"这个 fd，不再重复打开。关闭时同理：`f.close()` 从外层向内逐层关闭，最终关闭 fd（9.3.2 实测 `f.closed` 与 `f.fileno()` 的行为）。

> **⚠️ 陷阱**：很多初学者以为 `open("a.txt", "w")` 之后 `f` 直接就是"文件"。`f` 是**文本层**，不是 fd。所以：
> ```python
> >>> f = open("a.bin", "wb")        # 二进制模式没有文本层
> >>> type(f)
> <class '_io.BufferedWriter'>
> >>> f.write("中文")                # ❌ 缓冲层只要 bytes，不要 str
> TypeError: a bytes-like object is required, not 'str'
> ```

### 9.1.3 文件对象是一个"协议集合"

文件对象最大的特点：它**同时**实现了前面章节讲过的多个协议，把它们组装成一体。这正是 Python "协议即接口"哲学的集中体现：

```python
# ① 迭代器协议（第 5 章）：文件对象是它自己的迭代器
>>> f = open("a.txt")
>>> iter(f) is f            # True——__iter__ 返回自身
True
>>> next(f)                 # __next__ 返回"下一行"
'line1\n'

# ② 上下文管理器协议（第 8 章）：__enter__ 返回文件对象自身，__exit__ 负责关闭
>>> with open("a.txt") as f:
...     data = f.read()     # __exit__ 在块结束时自动 close()

# ③ 能力查询（capability query）：不用猜，直接问
>>> f.seekable(); f.readable(); f.writable()   # 'r' 模式 → (True, True, False)
True
True
False
```

**`IOBase` 基类为所有文件对象提供了通用的协议实现**——`__enter__`/`__exit__`（`__exit__` 调 `close()`）、`__iter__`/`__next__`（逐行迭代）。所以无论 `open()` 返回哪一层，`with` 和 `for` 都通用。

**文件对象没有实现 `__len__`**：

```python
>>> len(f)                  # ❌ 为什么不能用 len()？
TypeError: object of type '_io.TextIOWrapper' has no len()
```

设计上是故意的：文本文件经过编码，字节数 ≠ 字符数（中文一个字符 3 个 UTF-8 字节），"行数/字节数"没法在 O(1) 给出，必须读一遍才知道。想知道大小，问 OS 而不是问文件对象：

```python
>>> os.fstat(f.fileno()).st_size   # 文件对象有个 fileno()，能拿到底层 fd
```

**`closed` 状态与 `fileno()`**：

```python
>>> f = open("a.txt")
>>> f.closed
False
>>> fd = f.fileno()          # 拿到底层的文件描述符（整数）
>>> f.close()
>>> f.closed
True
>>> f.fileno()               # ❌ 关闭后再拿 fd 会抛异常
ValueError: I/O operation on closed file
```

> **实战建议**：拿到 fd 后可以和操作系统 API 交互——`os.fsync(f.fileno())`（9.4.1）、`os.fstat`、`mmap.mmap(f.fileno(), ...)`（9.6.2）、`select.select`（第 11 章）。`fileno()` 是 Python 文件对象和 POSIX 世界的"护照"。

---

## 9.2 `open()` 全参数：打开文件的每一个旋钮

`open()` 的完整签名：

```python
open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None,
     closefd=True, opener=None)
```

前两章只用过 `open(path)` 和 `open(path, "w")`——只拧了最外面两个旋钮。本节把剩下的一一展开。

### 9.2.1 模式字符串：每个字符的含义

模式由三组字符组合而成：**操作**（`r`/`w`/`a`/`x`）、**加号**（`+`，可读写）、**类别**（`b`/`t`，字节/文本）。

| 模式 | 含义 | 文件不存在 | 文件已存在 | 初始指针 |
|------|------|-----------|-----------|---------|
| `'r'` | 只读 | 抛 `FileNotFoundError` | 打开 | 开头 |
| `'w'` | 只写（覆盖） | **创建** | **立即截断为空** | 开头 |
| `'a'` | 追加 | **创建** | 保留，**所有写都到末尾** | 写：末尾 |
| `'x'` | 排他创建 | 创建 | **抛 `FileExistsError`** | 开头 |
| `'r+'` | 读写 | 抛异常 | 打开 | 开头 |
| `'w+'` | 读写（覆盖） | 创建 | 立即截断 | 开头 |
| `'a+'` | 读写（追加） | 创建 | 保留 | **写：末尾；读：开头** |

> **`'x'` 的原子性价值**：`x` 是"创建新文件，且只有我能创建"——如果文件已存在就失败。这是**无竞态的排他创建**，适合写锁文件、PID 文件、防止覆盖的导出文件：
> ```python
> >>> open("lock.pid", "x")     # 第一次：成功
> <_io.TextIOWrapper ...>
> >>> open("lock.pid", "x")     # ❌ 第二次：文件已存在
> Traceback (most recent call last):
>   ...
> FileExistsError: [Errno 17] File exists: 'lock.pid'
> ```
> 对比 `"w"`：它不检查，直接覆盖。`"w"` 适合"我就是要重建这个文件"，`"x"` 适合"我不允许覆盖"。

**最反直觉的一个点：`"w"` 在 `open()` 时就截断文件，不是在第一次写入时。**

```python
>>> f = open("data.txt", "w")     # 这一刻文件已被清空，还没写任何东西
>>> import os
>>> os.path.getsize("data.txt")   # 已经是 0，而不是原来的 1 MB
0
```

这带来一个真实事故模式：程序 `open(path, "w")` 之后崩溃、或参数传错——**原文件已经被毁，哪怕一个字节都没写成**。要"先全部准备好再动原文件"，用原子写模式（9.7.2 + 9.9）。

**`+` 号与指针语义的细节**：

```python
>>> f = open("data.txt", "r+")    # 读写：指针在开头，读到的就是原有内容
>>> f = open("data.txt", "a+")    # 追加读：写永远在末尾，但初始读指针在开头
>>> f.read()                      # a+ 可以读到原有内容（读指针在开头）
>>> f.write("x")                  # 但写总是追加到末尾，seek 到中间也拦不住
```

> **⚠️ 陷阱**：`"a+"` 里 `seek()` 不能把写指针移回开头——追加模式的写**永远**写到文件末尾（由 `O_APPEND` 标志在内核保证）。想"读了中间再改中间"，用 `"r+"`。

**`b` 与 `t`**：默认是文本模式，`'t'` 只是显式写出来（`open(path, "rt")` == `open(path)`）。`'b'` 切换到二进制。二者决定**最外层是哪一层**（9.1.2 的表），以及后面的 `encoding`/`newline` 参数有没有意义。

> **版本注意**：`buffering` 参数在文本/二进制模式下行为不同（9.2.4）；`'x'` 模式是 Python 3 新增（PEP 无关，直接加在 3.0 之后的小版本里）。

### 9.2.2 `encoding` 与 `errors`：文本层的编解码开关

这两个参数**只在文本模式有意义**（二进制模式没有编码这回事）。`encoding` 指定用什么编解码器把 `str` ↔ `bytes`，`errors` 指定转换失败时怎么办。

**默认编码是什么？这是个坑。**

```python
>>> import sys, locale
>>> sys.getdefaultencoding()          # 永远 'utf-8'，不用看
'utf-8'
>>> locale.getpreferredencoding(False)  # 这才是 open() 的默认编码来源！
'cp936'          # 中文 Windows：GBK/GB2312 的方言
```

**`open()` 的默认编码不是 `sys.getdefaultencoding()`**（那个恒为 utf-8），而是**区域设置的偏好编码** `locale.getpreferredencoding(False)`。在中文 Windows 上是 `cp936`（GBK），在英文 Linux 上是 `utf-8`，在日本 Windows 上是 `cp932`。

后果立现：

```python
# 中文 Windows 上，不指定 encoding：
>>> f = open("a.txt", "w")
>>> f.encoding                      # 文件对象知道自己用的什么编码
'cp936'
>>> f.write("中文")
2
>>> f.close()

# 这台机器上没任何异常——因为 GBK 能编码中文。换个环境就炸：
```

```python
# ① 用 UTF-8 写，用默认（GBK）读 —— 乱码
>>> open("a.txt", "w", encoding="utf-8").write("中文")
2
>>> print(open("a.txt").read())     # ❌ GBK 解码 UTF-8 字节 → 乱码
��ġ

# ② 用默认（GBK）写，用 UTF-8 读 —— UnicodeDecodeError
>>> open("a.txt", "w").write("中文")
2
>>> open("a.txt", encoding="utf-8").read()
Traceback (most recent call last):
  ...
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd6 in position 0: invalid continuation byte
```

> **⚠️ 陷阱**：同一个程序，在中文 Windows（默认 cp936）和英文 Linux（默认 utf-8）上跑，**行为完全不同**——这就是"编码不显式指定 = 行为不可移植"。生产代码里，`open()` 一律写 `encoding=`。

> **版本注意（PEP 597 + PEP 686）**：PEP 597 在 3.10 加了 `EncodingWarning`（`-X warn_default_encoding` 开启，提示你哪个 `open()` 没写编码）；PEP 686 已定案 **Python 3.15 起默认启用 UTF-8 mode**——届时 `open()` 默认编码统一为 UTF-8，这个坑自动消失。当前 3.14 上可手动开启：`python -X utf8` 或环境变量 `PYTHONUTF8=1`（实测本机 `sys.flags.utf8_mode == 0`，未开启）。**但建议从现在起就把 `encoding="utf-8"` 写进每个 `open()`**，别等 3.15 替你改。

**`errors` 五策略**——解码/编码失败时的行为：

| `errors` | 行为 | 适用 |
|---------|------|------|
| `'strict'`（默认） | 抛 `UnicodeDecodeError`/`EncodeError` | 数据该是干净的 |
| `'replace'` | 解码：坏字节→`�`；编码：无法表示的字符→`?` | 容忍脏数据，但不丢失其余内容 |
| `'ignore'` | 静默丢弃坏字节/无法表示的字符 | ⚠️ 会**丢数据**，慎用 |
| `'backslashreplace'` | 用 `\xNN`/`\uNNNN` 转义表示 | 调试/生成安全文本 |
| `'surrogateescape'` | 坏字节 → `U+DC80..DCFF` 专用代理区（`\udcxx`） | **文件路径**（文件名转义） |

`surrogateescape` 是三者里最"神奇"的：它把非法字节映射到 Unicode 的**专用代理码位**（`U+DC80..DCFF`），读出来是**带病态的 `str`**，但可以原样写回去：

```python
>>> import codecs
>>> s = codecs.decode(b"a\xffb", "utf-8", errors="surrogateescape")
>>> repr(s)
'a\udcffb'                            # 坏字节 \xff 变成 surrogate 码位 \udcff
>>> codecs.encode(s, "utf-8", errors="surrogateescape")
b'a\xffb'                             # 原样写回，不丢数据
```

`surrogateescape` 的典型战场是 **POSIX 文件名**——Unix 上文件名是任意字节序列，Python 用 surrogateescape 把它们安全映射成 `str`（不崩、可显示），写回时原样还原。Windows 走另一条路（PEP 529：路径用 UTF-8 + surrogatepass 解码），机制不同，目的相同——**任何字节都不该让程序崩溃**。

> **注意**：`surrogateescape` 用于普通文件内容会制造出"看起来能读、其实是坏数据"的字符串——日常用 `'strict'`，脏数据场景用 `'replace'`。

### 9.2.3 `newline` 与 universal newlines：三个换行世界的调和

换行符有三个"世界"：

| 系统 | 换行符 | 十六进制 |
|------|--------|---------|
| Unix/Linux/macOS（现代） | `\n` | `0x0A` |
| Windows | `\r\n` | `0x0D 0x0A` |
| 老 Mac（System 9 及以前） | `\r` | `0x0D` |

Python 的文本模式默认开启 **universal newlines**：读文件时把 `\r\n`、`\r`、`\n` **一律翻译成 `\n`**。这样你在 Linux 写的 `for line in f`，在 Windows 打开同一个文件也能逐行正确迭代。这是文本模式相对二进制模式最大的便利。

**`newline` 参数的完整语义**（实测验证）：

```python
# 环境：Windows（os.linesep == '\r\n'）

# ① newline=None（默认）：读翻译，写翻译
>>> open("a.txt", "w").write("a\nb")     # 写时 \n → \r\n
>>> open("a.txt", "rb").read()
b'a\r\nb'

# ② newline=''：读不翻译（universal 模式关掉），写不翻译
>>> open("a.txt", "w", newline="").write("a\nb")
>>> open("a.txt", "rb").read()
b'a\nb'

# ③ newline='\r\n'：读只认 \r\n 为行尾（且不翻译），写 \n → \r\n
>>> open("a.txt", "w", newline="\r\n").write("a\nb")
>>> open("a.txt", "rb").read()
b'a\r\nb'
```

完整对照表：

| `newline` | 读：universal newlines | 读：行尾翻译 | 写：`\n` 翻译为 |
|-----------|----------------------|-------------|----------------|
| `None`（默认） | ✅ 开 | `\r\n`、`\r`、`\n` 全部 → `\n` | `os.linesep`（Windows 上 `\r\n`） |
| `''` | ✅ 开（但） | **不翻译**，原样返回 | 不翻译 |
| `'\n'` | ❌ 只认 `\n` 为行尾 | 不翻译 | 不翻译 |
| `'\r'` | ❌ 只认 `\r` 为行尾 | 不翻译 | `\r` |
| `'\r\n'` | ❌ 只认 `\r\n` 为行尾 | 不翻译 | `\r\n` |

**什么时候必须碰 `newline` 参数？**

- **写 Windows 格式文件、且要精确控制**：`newline=''`，自己写 `\r\n`，避免 `\r\n` → `\r\r\n` 的双重翻译事故。
- **读一个行尾混用的文件**：默认 `None` 最稳，全部规整为 `\n`。
- **处理按行传输的协议**（如 CSV、HTTP）：`newline=''` 保留原始行尾，交给解析器自己处理。

> **⚠️ 陷阱：二进制读文本，文本读二进制**。用二进制模式读一个 `\r\n` 文件，你看到的行尾是 `b'\r\n'`（没翻译）；反过来把 `\r\n` 当字符串写进文本模式文件，读回来变 `\r\r\n`。**选错模式 = 换行符双重翻译**，是跨平台 bug 的重灾区。判定准则：内容是人读的 → 文本模式（让它管换行）；内容是机器读的 → 二进制模式（管好自己的字节）。

### 9.2.4 `buffering`、`fd`、`closefd` 与 `opener`

**`buffering`**：控制缓冲层的粒度。

| 值 | 语义 |
|----|------|
| `-1`（默认） | 用默认缓冲：文本/二进制都是 8 KiB（`io.DEFAULT_BUFFER_SIZE`） |
| `0` | **无缓冲**——每次读写直接系统调用。**文本模式禁止** |
| `1` | **行缓冲**——只对文本模式有效；遇到换行就刷到 OS |
| `>1` | 缓冲区的字节数 |

```python
>>> open("a.txt", "w", buffering=0)     # ❌ 文本模式不能无缓冲
ValueError: can't have unbuffered text I/O
>>> open("a.bin", "wb", buffering=0)    # ✅ 二进制可以：直接裸系统调用
<_io.BufferedWriter ...>                 # 注意：仍是 BufferedWriter，但绕过缓冲
```

为什么文本模式禁止 `buffering=0`？编码器把 1 个字符变成 1~4 字节，无缓冲意味着每个字符都可能触发系统调用——荒谬的慢。行缓冲（`buffering=1`）常用于 `stdout`：写给终端时希望回车即见。

**`closefd` 与从 fd 构造文件对象**：文件也可以从**已经打开的 fd** 构造（fd 来自 `os.open`、socket、管道）：

```python
>>> fd = os.open("a.txt", os.O_WRONLY)   # 底层 os 接口，拿到 fd
>>> f = open(fd, "wt", closefd=False)    # 包装 fd，但告诉 Python：别关它
>>> f.write("hi")
>>> f.close()
>>> os.close(fd)                         # fd 还活着，由我们手动关
```

`closefd=False` 的场景：fd 是从别的模块借来的（socket、`os.pipe()`、`multiprocessing` 的管道），**文件对象的关闭不该连带关闭它**——所有权在别处。默认 `closefd=True` 时，`f.close()` 会关闭 fd。

> **实战建议**：管道、socket 等"类文件"对象都可以用 `open(fd, ...)` 包装成文本/二进制流，从而享受 `readline()`、`for line in` 这些便利。这是把"文件处理"的能力借给网络/进程通信的桥（第 11 章会大量用到）。

**`opener`**：一个自定义的"打开函数"，接收 `(path, flags)` 返回 fd，取代默认的 `os.open`：

```python
def my_opener(path, flags):
    flags |= os.O_EXCL               # 强制排他
    return os.open(path, flags)

f = open("a.txt", "w", opener=my_opener)   # 用我们的 opener 打开
```

极少用，但它是"打开过程"的钩子——比如加 `O_SYNC`（写直达磁盘）、自定义权限位。

---

## 9.3 读写方法详解：TextIOBase 协议

打开文件只是开始。真正日常打交道的是 `read`/`write` 一族方法。本节以文本层（`TextIOBase`）为对象，逐方法拆解——二进制层的同名方法语义相同，只是单位从"字符"换成"字节"。

### 9.3.1 读的三种粒度：`read` / `readline` / `readlines`

```python
>>> f = open("a.txt")
>>> f.read()              # 读全部 → 一个 str
'line1\nline2\n'
>>> f.read()              # ❌ 指针已到末尾，再读是空串，不是报错
''
```

| 方法 | 返回 | 语义 | 内存占用 |
|------|------|------|---------|
| `read(size=None)` | `str`/`bytes` | `size=None` 读全部；`size>0` 读至多 `size` 个字符/字节 | 全部内容 |
| `readline(size=-1)` | `str`/`bytes` | 读一行（含行尾）到换行符；`size` 限制最多读几个字符 | 一行 |
| `readlines()` | `list[str]` | 读全部，按行切分 | 全部内容 + 列表开销 |
| `for line in f` | `str` | 迭代协议，逐行产出 | 一行 |

**`readlines()` 的"两倍内存"陷阱**：它既读出全部内容，又为每行建一个 `str` 对象——大文件上内存可能是文件的数倍（每个 `str` 对象本身还有 ~50 字节的 header）。**能迭代就不要 `readlines()`**：

```python
# ❌ 全量 + 每行对象，双倍内存
for line in open("big.log").readlines():
    ...

# ✅ 迭代器逐行，同一时刻只有一行在内存
for line in open("big.log"):
    ...
```

**`readline(size)` 的妙用——既防大行又保语义**：`readline(1024)` 读至多 1024 字符就返回，即使这一行有 10 万字符。这是"处理可能超长的行"的标准防爆手段。

**`iter(f.readline, sentinel)`：按行读 + 提前终止的惯用法**（第 5 章的哨兵迭代器形式）。它让 `readline` 变成一个可控迭代器，比 `for line in f` 多了"读到某行就停"的能力：

```python
>>> lines = iter(open("a.txt").readline, "STOP\n")   # 读到 "STOP\n" 就停
>>> list(lines)                                       # 只会读到 STOP 之前
['line1\n']
```

> **实战建议**：日志文件"读到标记行就停"、CSV 跳过表头、"只处理前 N 行"——这三类需求都是 `iter(f.readline, sentinel)` 的典型场景。它能配合 `next()` 手动推进，比 `readline` 循环更 Pythonic。

### 9.3.2 写：`write` / `writelines` / `print`

```python
>>> f = open("a.txt", "w")
>>> n = f.write("hello")     # write 返回写入了多少个字符
>>> n
5
```

**`write` 返回的是字符/字节数**，不是布尔成功标志——这个返回值在**写 socket** 时是必须检查的（可能写了一半），写文件时通常可以忽略（缓冲层保证要么全写要么报错）。

**`writelines` 不补换行——这是它最常见的坑**：

```python
>>> f = open("a.txt", "w")
>>> f.writelines(["a", "b"])     # ❌ 你以为在写两行，实际写成一串
>>> f.close()
>>> open("a.txt").read()
'ab'                              # 没有任何换行符
```

`writelines` 的字面意思是"写一组行"，但它**不会**给你加任何分隔符——它只是"对每行调用 `write`"的简写。想要换行，自己带上：

```python
>>> f.writelines(line + "\n" for line in ["a", "b"])   # ✅
```

**`print(file=f)`：把文本格式化交给 `print`**。`print` 的 `end` 参数和文件对象的换行翻译叠加时要小心：

```python
>>> with open("a.txt", "w") as f:
...     print("hello", file=f)      # 写 "hello\n"（end 默认 \n）
...     print("world", file=f, end="")   # 写 "world"（不加换行）
>>> open("a.txt").read()
'hello\nworld'
```

> **⚠️ 陷阱**：`print(..., file=f)` 在 Windows 文本模式下，`end="\n"` 会被翻译成 `\r\n`（9.2.3）。想要"Windows 文件但纯 `\n` 行尾"，用 `open(path, "w", newline="")` 再 `print(..., file=f)`。

**`flush=True` 参数的场景**：进度日志、实时监控文件——写了立刻可见：

```python
print(f"step {i}/{n}", file=progress_file, flush=True)   # 不等缓冲满
```

### 9.3.3 编码器落地：BOM 与大文件解码

**BOM（Byte Order Mark，字节序标记）**：文件开头的几个特殊字节，声明"我是 UTF-8/UTF-16/UTF-32，字节序如此"。Windows 记事本保存 UTF-8 文件时会自动加 BOM。

| 编码 | BOM 字节 |
|------|---------|
| UTF-8 | `EF BB BF` |
| UTF-16 LE | `FF FE` |
| UTF-16 BE | `FE FF` |
| UTF-32 LE | `FF FE 00 00` |

Python 用特殊的编码名来"处理 BOM"：

```python
# utf-8-sig：写入时自动加 BOM，读取时自动剥掉 BOM
>>> f = open("a.txt", "w", encoding="utf-8-sig")
>>> f.write("中文")
2
>>> f.close()
>>> open("a.txt", "rb").read()          # 写进去的字节：BOM + UTF-8 编码的中文
b'\xef\xbb\xbf\xe4\xb8\xad\xe6\x96\x87'

# 普通 utf-8 读：BOM 会变成文本里的一个不可见字符 ﻿
>>> open("a.txt", encoding="utf-8").read()
'﻿中文'
>>> open("a.txt", encoding="utf-8-sig").read()   # utf-8-sig 自动剥掉
'中文'
```

> **⚠️ 陷阱**：`﻿` 是 **零宽不换行空格**（ZWNBSP），打印看不见，但 `startswith`、JSON 解析、`csv` 表头比对都会因为它出错。"用 utf-8-sig 读，遇到 `﻿` 就剥掉"是处理记事本文件的必会操作。
>
> **UTF-16/32 必须靠 BOM 才能稳定读写**——它们没有 UTF-8 那种自同步的字节序指示，`encoding="utf-16"` 默认会写 BOM、读时靠 BOM 判断字节序。所以"UTF-8 文件可能带也可能不带 BOM，UTF-16 文件几乎必然带 BOM"。

**大文件解码错误定位**：`UnicodeDecodeError` 携带出错位置：

```python
>>> data = b"abc\xe4\xb8\xad\n" + b"bad\xff\xfe"     # 末尾是坏字节
>>> open("a.bin", "wb").write(data)
>>> try:
...     open("a.bin", encoding="utf-8").read()
... except UnicodeDecodeError as e:
...     print(e.reason, "at byte", e.start, "-", e.end)
'invalid continuation byte' at byte 10 - 11
```

`e.start`/`e.end` 是**字节偏移**（编码层在解码缓冲区里的位置），`e.object` 是坏字节所在的片段。生产环境定位"哪个文件的哪一段坏了"，这是唯一的线索。

---

## 9.4 缓冲机制与性能：为什么小写小读那么慢

### 9.4.1 三层缓冲：`flush()` 与 `os.fsync()` 是两个"落盘"

文件写入从 Python 到磁盘，要过**三层**：

```
print/write → ① 用户态缓冲（Python 的 8 KiB buffer）
            → ② 内核页缓存（OS page cache）
            → ③ 磁盘

   flush()   只把 ① 推给 ② —— "写到了操作系统手里"
   os.fsync() 把 ② 真正刷到 ③ —— "落盘了"
```

- **`f.flush()`**：把 Python 缓冲层里攒的字节**提交给内核**。此后进程崩溃，数据还在内核里；**机器断电/内核崩溃**，数据可能丢。
- **`os.fsync(f.fileno())`**：强制内核把脏页写回磁盘，并等待完成。这才是"保证物理落盘"。

```python
>>> f = open("a.txt", "w")
>>> f.write("important")              # 此刻还在①用户态缓冲，甚至没进内核
>>> f.flush()                         # ①→②：进内核页缓存
>>> os.fsync(f.fileno())              # ②→③：落盘
```

> **实战建议**：普通文件写完，`close()` 会隐式 `flush()`，够用。**数据库、记账、日志审计这类"不能丢一条"的数据**，必须 `fsync`——但要知道代价：`fsync` 一次可能 1~10 ms（取决于磁盘），比普通写慢几个数量级，**别对每个小写都 `fsync`**，攒批后一次 `fsync` 是工业标准做法（数据库的 WAL 就是这个思想）。

**为什么 `f.flush()` 后另一个进程还看不到数据？** 因为另一个进程读的是自己的内核页缓存（②），`flush` 已经把数据放进内核，所以**同机**一般能看到；但如果 `flush` 只是把 ① 交给 ②，而 ② 还没刷到磁盘，**跨机器**（网络文件系统）或**断电**后就看不到。

### 9.4.2 性能实验：写入分块是 200 倍的差距

实测（Python 3.14，Windows，SSD）：向文件写 **1 MiB** 数据，不同分块大小的耗时：

| 写入方式 | 耗时 | 吞吐 |
|---------|------|------|
| 逐字节 `write(b"x")` × 1048576 | **68.5 ms** | **15 MiB/s** |
| 每 64 字节写一次 | 1.9 ms | 568 MiB/s |
| 每 4 KiB 写一次 | 0.5 ms | 2.1 GiB/s |
| 每 64 KiB 写一次 | 0.4 ms | 2.6 GiB/s |
| 一次性 `write(全部)` | **0.34 ms** | **3.1 GiB/s** |

**逐字节比一次性写慢 200 倍。** 为什么？每次 `write()` 调用都有固定开销：Python 方法调用、编码（文本模式）、缓冲边界检查，可能还有系统调用。1 MiB 的 200× 差距里，绝大部分是**调用次数 × 单次开销**，而不是数据本身。

> **注意**：这个实验里的"慢"和"快"都不是磁盘真实速度——`os.urandom` 的数据写进文件时大多命中了内存页缓存（③ 没发生）。它衡量的是 **Python 层的调用开销**，而这恰恰是我们要优化的对象：**代码层的浪费，远比磁盘快慢影响大**。

**文本模式没有这个差距？** 也测了（1 MiB 中文文本，UTF-8）：

| 写入方式 | 耗时 | 吞吐 |
|---------|------|------|
| 每 4 KiB 写一次 | 1.2 ms | 1.5 GiB/s |
| 一次性写完 | 1.3 ms | 1.3 GiB/s |

文本模式分块与全量几乎无差——因为 `TextIOWrapper` 内部有**编码缓冲**：你 `write` 一小段，它攒起来编码成一批字节再交给缓冲层。**只要别逐字符写**（那会绕过编码缓冲、逐字符编码），文本模式的调用开销基本可忽略。

**结论一句话**：写数据时，**至少 4 KiB 一写**；能用一次性 `write` 就一次性。逐字节/逐字符写是大忌。

```python
# ❌ 逐字符/逐字节——200 倍慢
for ch in data:
    f.write(ch)

# ✅ 分块
for i in range(0, len(data), 1 << 16):
    f.write(data[i:i + (1 << 16)])

# ✅✅ 一次性（数据已在内存时）
f.write(data)
```

> **实战建议**：读这边同理，但方向相反——**读全量反而更快**（少了每块一次的函数调用）。实测 1 MiB `read()` 一次 vs `read(4096)` 循环，全量读更简单且不慢（读是磁盘/内存带宽主导，不是调用次数主导）。**"文件能放进内存，就一次性读进来处理"** 是简单又快的默认选择。

### 9.4.3 大文件处理模式：四种范式的选型

文件大到不能（或不该）全量进内存时，四种模式：

| 范式 | 代码 | 内存 | 适用 |
|------|------|------|------|
| 逐行迭代 | `for line in f:` | 一行 | 按行处理（日志、CSV、配置） |
| 固定块 | `while chunk := f.read(1<<20):` | 一块 | 二进制流、任意行界 |
| 哨兵迭代 | `for line in iter(f.readline, ""):` | 一行 | 半行边界、提前终止 |
| 内存映射 | `mmap`（9.6.2） | 虚拟内存映射 | 随机访问大文件 |

```python
# 逐行：处理日志，一行进一行出
with open("big.log") as f:
    for line in f:
        process(line)

# 固定块：二进制大文件，比如统计字节分布
with open("big.bin", "rb") as f:
    while chunk := f.read(1 << 20):        # 海象：读到空块为止
        stats.update(chunk)
```

> **⚠️ 陷阱：`for line in f` 遇到超长行**。如果文件里有 1 亿字节的一行（没有换行符），`for line in f` 会把这整行读进内存。需要防爆时，用 `readline(1 << 16)`（9.3.1）或者干脆按块读。
>
> **衔接卷 2**：`pandas.read_csv(path, chunksize=...)` 的分块读取、`pd.read_csv` 的类型推断，底层用的就是"按行迭代 + 提前停止"这套机制。文件层的性能意识，直接决定你处理 10 GB CSV 会不会爆内存。

---

## 9.5 随机访问：`seek` / `tell` / `truncate`

到目前为止讲的都是**顺序读**：从头读到尾。但很多场景需要**跳着读**——索引文件、数据库页、日志的尾部。文件对象有个**位置指针**（file position），`seek` 移动它，`tell` 查询它。

### 9.5.1 二进制层的指针：字节偏移

二进制模式下，`tell()` 返回的是**从文件头开始的字节数**，`seek` 直接指定字节偏移：

```python
>>> f = open("data.bin", "r+b")        # 二进制可读可写
>>> f.write(b"0123456789")
10
>>> f.tell()
10
>>> f.seek(3)                          # 移到字节 3
3
>>> f.read(4)
b'3456'
>>> f.tell()                           # 现在在字节 7
7
```

`seek(offset, whence)` 的 `whence` 三基元：

```python
import os
f.seek(0, os.SEEK_SET)      # 从文件头偏移（默认）
f.seek(2, os.SEEK_CUR)      # 相对当前位置往后 2 字节
f.seek(-4, os.SEEK_END)     # 相对文件末尾往前 4 字节（读最后 4 字节）
f.seek(0, os.SEEK_END)      # 跳到文件末尾——经典"算文件大小"手法
```

**`seek` 到文件末尾之后**：文件出现一个"空洞"——逻辑上存在、读出来是 `\x00` 的区域。写数据库/WAL 时常用"预留空间"。

```python
>>> f.seek(1000)                       # 跳到字节 1000
>>> f.write(b"END")                    # 0..1000 之间全是空洞
>>> os.path.getsize("data.bin")        # 逻辑大小
1003
```

> **注意**：逻辑大小 1003 在任何平台都成立。空洞在**磁盘上是否真的不占空间**（稀疏文件），取决于文件系统：Linux 的 ext4/btrfs、Windows 上显式标记 sparse 的文件才会；NTFS 普通文件会把空洞按 `\x00` 写满。别依赖"空洞不占盘"做容量假设。

> **⚠️ 陷阱：字节偏移 vs 字符偏移**。`tell()` 在**文本模式**下返回的不是字符数（见 9.5.2），在**二进制**模式下才是纯字节。把两个混用是 bug 根源——记住：**二进制模式 `tell`/`seek` 是干净的字节偏移，文本模式不是**。

### 9.5.2 文本层的指针："幻象"偏移

文本层（`TextIOWrapper`）经过编码，`tell()` 返回的**不是字符数，也不是字节数，而是一个不透明的"cookie"**——编码器内部用来恢复位置的私有状态。

文本模式的 `seek` 因此有严格限制（实测）：

```python
>>> f = open("a.txt")                  # 文本模式
>>> f.seek(0)                          # ✅ 绝对位置，允许
0
>>> f.seek(0, 2)                       # ✅ 跳到末尾，允许
11
>>> f.seek(2, 1)                       # ❌ 相对当前偏移，禁止！
UnsupportedOperation: can't do nonzero cur-relative seeks
>>> f.seek(5)                          # 绝对位置允许，但……
5
>>> f.seek(f.tell())                   # ✅ 唯一"安全"的移动：回到上次 tell 的位置
```

**为什么相对 seek 被禁止？** 因为编码是**有状态**的（多字节字符可能跨缓冲边界），"往后跳 2 个字符"在不知道字节边界的情况下根本没法实现。而"回到 `tell()` 给的那个 cookie"是可靠的，因为 `tell()` 返回的就是编码器自己记住的状态。

> **⚠️ 陷阱：文本层绝对 `seek` 到任意位置是"未定义"的**。`f.seek(5)` 在 ASCII 文本上碰巧正确（5 个字节 = 5 个字符），但在含多字节字符（中文、emoji）的 UTF-8 文件里，`seek(5)` 可能落在某个字符的中间——**读出来是乱码，不报错**。所以文本文件要随机访问，正确姿势是：先 `read()`/`tell()` 走一遍拿到 cookie，**不要手动算偏移**；真要自由跳转，用二进制模式打开，自己管编码。
>
> **实战建议**：文本文件唯一靠谱的"跳到某处"是 `seek(0, 2)` 跳到末尾（配合"看日志尾部"）。其余随机访问，一律走二进制层。

### 9.5.3 `truncate`：截断文件

`truncate(size=None)` 把文件**裁到指定大小**（默认裁到当前位置）：

```python
>>> f = open("log.txt", "r+b")         # 二进制模式：字节语义干净
>>> f.read()
b'line1\nline2\nline3\n'
>>> f.seek(0)
>>> f.truncate(7)                      # 只保留前 7 字节
7
>>> open("log.txt", "rb").read()
b'line1\nl'
```

> **⚠️ 陷阱：文本模式的 `truncate`**。`truncate(size)` 的 `size` 永远是**原始字节数**，但文本模式下磁盘上的换行是 `\r\n`（Windows）——`truncate(7)` 截的是 7 个原始字节（含 `\r`），读回来却是 6 个字符。想按"你看到的字符"精确截断，用二进制模式自己数字节。这是又一个"文本模式掩盖字节真相"的例子（呼应 9.5.2 的 cookie）。

**典型用途**：日志轮转（保留最近 N 字节）、崩溃恢复后清理残段、"重写配置文件但先清空"。

> **注意**：`truncate` 与 `os.ftruncate(f.fileno(), size)` 是同一操作的两面。`truncate` 可能只缩到用户态缓冲的大小，需要落盘时记得 `flush()`。

---

## 9.6 二进制 I/O 实战：`struct` 与 `mmap`

文本 I/O 处理人读的数据；二进制 I/O 处理**机器读的数据**——协议包、文件格式、数值数组。本节是二进制世界的两大工具：`struct`（字节 ↔ 字段）和 `mmap`（文件当内存）。

### 9.6.1 `struct`：在字节和结构化字段之间转换

很多二进制格式（`.bmp`、`.wav`、自定义协议）是**定长字段**的排列。`struct` 用一条格式字符串描述布局，把 Python 值打包成字节、把字节解包成 Python 值：

```python
>>> import struct
>>> struct.pack("i", 5)            # 打包：int 5 → 4 字节（本机小端）
b'\x05\x00\x00\x00'
>>> struct.unpack("i", b"\x05\x00\x00\x00")
(5,)
>>> struct.pack("h", 5)            # h = short（2 字节），i = int（4 字节）
b'\x05\x00'
```

**格式字符串 = 字段序列**，每个字符一种类型。常用类型：

| 格式 | C 类型 | Python 类型 | 大小 |
|------|--------|------------|------|
| `b` / `B` | `signed char` / `unsigned char` | `int` | 1 |
| `h` / `H` | `short` / `unsigned short` | `int` | 2 |
| `i` / `I` | `int` / `unsigned int` | `int` | 4 |
| `q` / `Q` | `long long` / `unsigned long long` | `int` | 8 |
| `f` / `d` | `float` / `double` | `float` | 4 / 8 |
| `c` | `char` | `bytes`（长度 1） | 1 |
| `s` | `char[]` | `bytes` | 跟长度 |
| `?` | `_Bool` | `bool` | 1 |

**⚠️ 格式顺序就是参数顺序**——这个坑我写本章时亲手踩过：

```python
>>> struct.pack("=ci", b"x", 1)     # ✅ 'c' 对应第一个参数（bytes），'i' 对应第二个
b'x\x01\x00\x00\x00'
>>> struct.pack("=ci", 1, b"x")     # ❌ 顺序错：1 被塞给 'c'，报错
struct.error: char format requires a bytes object of length 1
```

> **注意**：上面的示例特意用了 `=` 前缀（标准紧凑）。**不带前缀的默认 `@` 是本机对齐**——`struct.pack("ci", ...)` 会插入填充字节变成 8 字节（对齐陷阱，见下）。写可移植格式，**永远显式写 `=`/`<`/`>`**。

**字节序：`<>` 前缀显式声明**。同一个 `i`，大端小端完全是不同字节：

```python
>>> struct.pack("<i", 5)           # 小端：低字节在前（x86/ARM 默认）
b'\x05\x00\x00\x00'
>>> struct.pack(">i", 5)           # 大端：高字节在前（网络协议默认）
b'\x00\x00\x00\x05'
```

| 前缀 | 字节序 | 对齐 |
|------|--------|------|
| `@`（默认） | 本机 | **本机对齐（会填 padding！）** |
| `=` | 本机 | 标准（紧凑） |
| `<` | 小端 | 标准（紧凑） |
| `>` `!` | 大端 | 标准（紧凑） |

**对齐 padding 是最大陷阱**。`@`（默认，本机对齐）会按 C 编译器规则插入填充字节；`=`/`<`/`>` 紧凑排列。实测同一份数据：

```python
>>> struct.calcsize("@ci")         # 本机对齐：char(1) + 3 填充 + int(4) = 8
8
>>> struct.calcsize("=ci")         # 标准紧凑：char(1) + int(4) = 5
5
>>> struct.pack("@ci", b"x", 1)    # 有填充：x 后跟 3 个 0
b'x\x00\x00\x00\x01\x00\x00\x00'
>>> struct.pack("=ci", b"x", 1)    # 紧凑：x 后直接跟 4 字节 int
b'x\x01\x00\x00\x00'
```

> **⚠️ 陷阱**：写跨平台二进制格式**永远用 `=`/`<`/`>` 显式字节序**。默认 `@` 的填充和字节序都随平台漂移——你本机写的文件，换台机器 unpack 就错位。**显式 `=` 是二进制格式的底线**。
>
> **格式复用**：反复 pack 相同结构时，预编译成 `Struct` 对象，避免每次解析格式字符串：
> ```python
>>> rec = struct.Struct("<HHI")          # 头部：2+2+4 字节
>>> rec.pack(1, 2, 3)
b'\x01\x00\x02\x00\x03\x00\x00\x00'
>>> rec.size                              # 8——比每次 calcsize 快
8
```

**典型实战——二进制文件头**（比如一个图片/日志文件，前 8 字节是 "magic + 版本 + 数据长度"）：

```python
import struct

HEADER = struct.Struct("<4sHB")           # 4 字节 magic + uint16 版本 + uint8 标志
with open("img.dat", "rb") as f:
    magic, version, flags = HEADER.unpack(f.read(HEADER.size))
    if magic != b"DIMG":
        raise ValueError("not our file")
    print(f"version {version}, flags {flags:#010b}")
    data = f.read()                       # 剩余部分就是载荷
```

> **衔接卷 2**：numpy 的 `np.dtype` 就是"结构化二进制布局"的工业实现，`dtype('<i4')` 和 `struct.Struct('<i')` 说的是同一件事。`struct` 是手搓二进制格式的标准工具，numpy 是矢量化的批量版本。

### 9.6.2 `mmap`：把文件映射成内存

`mmap`（memory-mapped file）把文件的页面直接映射进进程地址空间——**读写文件像读写一个 `bytearray` 一样**，由 OS 负责页面换入换出，无需 `read()`/`write()` 系统调用，也**不吃堆内存**（用的是虚拟地址空间）。

```python
>>> import mmap
>>> with open("data.bin", "r+b") as f:        # 必须 r+（可读可写）才能写映射
...     m = mmap.mmap(f.fileno(), 0)          # length=0 → 映射整个文件
...     print(m[0:5])                          # 切片读：像 bytes
...     b'01234'
...     m[0] = ord("X")                        # 单字节写：写进文件
...     m[5:8] = b"abc"                        # 切片写
...     m.close()                              # 用完关闭映射
>>> open("data.bin", "rb").read()             # 写入已经落进文件
b'X1234abc89abcdef'
```

**`mmap` vs `read()` 的性能与适用**：

| 场景 | `read()` | `mmap` |
|------|---------|--------|
| 顺序读完整个文件 | ✅ 简单快 | 并不更快 |
| 大文件**随机访问**多次 | 每次 `seek`+`read` 开销大 | **映射后像数组一样 `m[i]` 跳读** |
| 多个进程**共享**数据 | 不适用 | ✅ 同一映射共享 |
| 数据要**同时读和改** | 手动读写 | 改映射即改文件 |

```python
# 经典：大文件里随机查找记录（比如每 64 字节一条记录）
import mmap

REC = 64
with open("huge.dat", "r+b") as f:
    m = mmap.mmap(f.fileno(), 0)
    try:
        total = len(m) // REC                 # 总记录数
        rec = m[7 * REC: 8 * REC]             # 直接切片拿第 8 条记录，O(1) 寻址
        m[7 * REC: 8 * REC] = rec.upper()     # 原地修改
    finally:
        m.close()
```

> **⚠️ 陷阱**：`mmap` 要求文件至少有 1 字节（空文件映射会 `ValueError`）；写映射前文件要以 `r+b`/`w+b` 打开，只读用 `mmap.ACCESS_READ` 显式声明。映射是**虚拟地址**，别以为"读进来了"——性能分析时要意识到数据是惰性换页的，第一次触碰某个区域才真正发生 IO。
>
> **版本注意**：`mmap` 支持 `madvise` 提示（`mmap.MADV_SEQUENTIAL` 等）预声明访问模式，3.x 一直可用；Windows 上 `m[0:5]` 返回 bytes、`m[:] = ` 等写接口与 POSIX 一致，但空映射、超出长度等边界行为有平台差异。

---

## 9.7 路径与临时文件：`pathlib` / `tempfile` / `os`

一个文件操作不只是 `open()`——还有**路径怎么组织、临时文件怎么安全创建、文件怎么改名删除**。这三块是文件章节的"周边基建"。

### 9.7.1 `pathlib`：面向对象的路径

`pathlib` 是 Python 3.4 引入的**面向对象路径库**（PEP 428）。它把路径从"字符串"升级为"对象"，解决了 `os.path` 时代最烦人的两个问题：**跨平台分隔符**和**方法要记函数名**。

```python
>>> from pathlib import Path
>>> p = Path("data/report.txt")
>>> type(p)                       # Windows 上：WindowsPath；Linux 上：PosixPath
<class 'pathlib.WindowsPath'>
>>> p.name                        # 文件名
'report.txt'
>>> p.stem                        # 去掉后缀的主名
'report'
>>> p.suffix                      # 扩展名
'.txt'
>>> p.parent                      # 父目录（还是一个 Path！）
WindowsPath('data')
>>> p.parts                       # 拆开的每一段
('data', 'report.txt')
```

**`/` 运算符拼路径——告别 `os.path.join` 的字符串地狱**：

```python
>>> base = Path("/home/user")
>>> cfg = base / "config" / "app.json"     # 自动处理分隔符，跨平台
>>> cfg
PosixPath('/home/user/config/app.json')
```

> **设计哲学**：`/` 运算符重载（第 4 章运算符协议）在路径上的应用——`Path / "a" / "b"` 直观地表达"路径层级"。这是 Python "让语法配合领域"的又一例子，也是 `pathlib` 比 `os.path.join` 更受欢迎的根本原因：**读起来就是路径的样子**。

**常用方法速查**：

```python
p.exists()                       # 是否存在
p.is_file(); p.is_dir()          # 是文件？是目录？
p.stat().st_size                 # 文件大小（字节）
p.read_text(encoding="utf-8")    # 一次读文本（等价 open+read+close）
p.write_text("...", encoding="utf-8")   # 一次写文本
p.read_bytes(); p.write_bytes(b"...")   # 二进制版本
p.open("a")                      # 等价内置 open，返回文件对象
p.rename("new.txt")              # 改名
p.replace("new.txt")             # 改名（已存在则覆盖，原子）
p.unlink()                       # 删除文件
p.mkdir(parents=True, exist_ok=True)    # 建目录（含父目录）
p.iterdir()                      # 遍历子项（惰性迭代器）
p.glob("*.py")                   # 按通配符找子项（惰性迭代器）
p.rglob("**/__init__.py")        # 递归找
p.with_suffix(".md")             # 换扩展名：report.txt → report.md
p.with_name("new.txt")           # 换文件名
p.resolve()                      # 解析成绝对路径（含符号链接）
p.home()                         # 用户主目录；Path.cwd() 当前目录
```

**`Path.read_text`/`write_text`/`open` 与内置 `open()` 的关系**：

```python
>>> p = Path("a.txt")
>>> f = p.open("r")              # ✅ 完全等价 open(p, "r")，返回同一类文件对象
>>> type(f)
<class '_io.TextIOWrapper'>
>>> p.read_text(encoding="utf-8")       # 便捷版：open + read + close 一步完成
```

**`glob` 的惰性**：返回的是迭代器，不是列表——文件多时不一次性全建对象：

```python
>>> for py in Path(".").glob("**/*.py"):     # 惰性遍历，内存 O(1)
...     print(py)
```

> **⚠️ 陷阱 1**：`Path` 不是字符串。拼给 `open("prefix_" + p)` 会 `TypeError`，要 `str(p)` 或直接用 `p` 本身（`open()` 接受 Path）。但**别**在内部到处 `str(p)`——`p / "x"` 比字符串拼接安全得多。
>
> **⚠️ 陷阱 2**：`Path("a") / "b"` 与 `Path("a/b")` 语义相同，但 `Path("a") / "/b"` 会把 `/b` 当**绝对路径**直接覆盖前面的 `a`（右侧以 `/` 开头）——拼用户输入时注意。
>
> **实战建议**：`pathlib` 是**文件操作的统一门面**：`read_text` 管读、`write_text` 管写、`glob` 管找、`replace` 管原子替换。老代码里的 `os.path.join`/`os.path.exists` 混用，逐步迁移到 `Path`，新代码**默认 `Path`**。

### 9.7.2 `tempfile`：安全地创建临时文件

临时文件的需求到处都是：下载中转、导出暂存、原子写（9.9）。**自己拼 `/tmp/xxx_123.txt` 是错的**——两个问题：

1. **不可移植**：Windows 没有 `/tmp`，路径还要考虑权限。
2. **竞态与安全**：`/tmp/xxx` 这个"先猜名再创建"两步之间，可能被别的进程抢先创建（symlink 攻击）——猜名字创建临时文件是经典安全漏洞。

`tempfile` 模块解决这两件事：**用随机名 + 排他创建（O_EXCL）**，并自动清理：

```python
>>> import tempfile

# ① 临时文件：关闭即删除（无名字，最安全）
>>> with tempfile.TemporaryFile("w+") as tf:     # 没有 name 属性，纯内存级安全
...     tf.write("hello")
...     tf.seek(0)
...     print(tf.read())
'hello'                                          # 关闭后自动清理

# ② 带名字的临时文件：需要传给别的程序用
>>> with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as ntf:
...     ntf.write("a,b\n1,2\n")
...     path = ntf.name            # 拿到路径交给别人
>>> # delete=False 时记得自己清理：
>>> import os; os.remove(path)

# ③ 临时目录：一堆临时文件的归属地
>>> with tempfile.TemporaryDirectory() as td:     # 退出时整个目录被删
...     p = Path(td) / "sub" / "f.txt"
...     p.parent.mkdir(parents=True)
...     p.write_text("ok")
```

> **实战建议**：`TemporaryFile` 无路径 → 别的进程碰不到，安全性最好；`NamedTemporaryFile` 有路径 → 可交给子进程/外部程序，但记得 `delete=False` 时手动清。**原子写的标准动作就是 `TemporaryFile`/`NamedTemporaryFile` + 写 + `flush` + `os.replace`**（9.9 实战）。
>
> **注意**：临时文件默认放 `tempfile.gettempdir()`（Windows 上是 `C:\Users\<user>\AppData\Local\Temp`）。`TemporaryDirectory` 是 3.2+ 的标准答案，替代手写 `shutil.rmtree` 清理。

### 9.7.3 `os` 层文件操作：改名、删除与遍历

文件操作的地基还是 `os` 模块（`pathlib` 底层也调它）。几个高频操作值得明确语义：

```python
import os

os.rename("a.txt", "b.txt")        # 改名/移动；若 b 已存在，行为平台相关（Windows 报错）
os.replace("a.txt", "b.txt")       # 改名/移动；若 b 已存在，原子覆盖
os.remove("a.txt")                 # 删文件（= os.unlink）
os.makedirs("a/b/c", exist_ok=True)   # 递归建目录
os.walk(".")                       # 深度遍历目录树，产出 (root, dirs, files)
```

**`os.replace` 的原子性**——它是"原子替换"技术的核心原语：

```python
# 写配置安全模式：先写临时文件，再原子替换目标
tmp = "config.json.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(config, f)
    f.flush()
os.replace(tmp, "config.json")     # 要么是旧文件，要么是新文件——不会读到一半的脏文件
```

> **注意**：`os.replace` 的原子性只在**同一文件系统**内成立（跨设备是拷贝+删除，不原子）。这就是为什么临时文件要建在**目标文件同目录**（9.9 展开）。
>
> **`os.walk` 的两个技巧**：① `dirs` 列表可以原地修改——`del dirs[:]` 或过滤可**剪枝**（不递归进某些目录）；② `dirs`/`files` 都是**未排序**的，顺序敏感场景先 `sort()`。

```python
for root, dirs, files in os.walk("."):
    # 跳过所有 __pycache__ 和 .git
    dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}]
    for f in files:
        ...
```

> **衔接第 10 章**：`os` 是"操作系统接口"模块，`pathlib` 是它的面向对象门面——第 10 章讲模块组织时还会看到 `os` 与 `shutil`、`sys` 等系统模块的协作。

---

## 9.8 序列化：把对象状态变成字节

文件 I/O 的终极形态之一：**把对象持久化**——存到磁盘、跨进程传输、发到网络。序列化（serialization）的本质是回答一个问题：

> **怎么把一个"活着"的对象（`dict`、`list`、自定义类实例），变成一串能写进文件、能传走、能再变回对象的字节？**

序列化要解决三个子问题：
1. **类型映射**：Python 的类型系统 ↔ 目标格式的类型系统（比如 JSON 没有 `tuple`，没有 `datetime`）。
2. **引用与循环**：对象可能引用同一个对象（共享）、可能循环引用（A → B → A）。序列化要么保留引用关系，要么展开成树。
3. **安全性**：反序列化 = 执行对方送来的指令。**反序列化不可信数据是最危险的操作之一。**

### 9.8.1 `pickle`：Python 原生的对象持久化

`pickle` 把**任意 Python 对象图**序列化成字节流——不是给人看的，是给 Python 自己看的。

```python
>>> import pickle
>>> obj = {"name": "boogo", "tags": ["a", "b"], "n": 42}
>>> blob = pickle.dumps(obj)          # 对象 → bytes
>>> pickle.loads(blob)                # bytes → 对象
{'name': 'boogo', 'tags': ['a', 'b'], 'n': 42}
```

**类型映射近乎全支持**：`dict`/`list`/`tuple`/`set`/`int`/`float`/`str`/`bytes`/`bool`/`None`、自定义类实例、**甚至函数和类**（按名字引用）。这是 `pickle` 相对 `json` 的杀手锏——**它序列化的是"对象图"，不是"数据树"**。

**引用与循环**：`pickle` 是**图遍历**，天然支持共享引用和循环引用：

```python
>>> lst = [1, 2]
>>> obj = {"shared": lst, "again": lst}    # 两个键引用同一个列表
>>> blob = pickle.dumps(obj)
>>> back = pickle.loads(blob)
>>> back["shared"] is back["again"]        # ✅ 引用关系被保留！
True
>>> back["shared"].append(3)
>>> back["again"]                          # 两个键看到同一个对象
[1, 2, 3]
```

**协议版本**（PEP 307/3154/574 的演进）：

| 协议 | 版本 | 说明 |
|------|------|------|
| 0 | Python 2.3 | 人类可读的 ASCII 格式 |
| 1 | Python 2.3 | 旧二进制格式 |
| 2 | Python 2.3 | 新式类支持的二进制格式 |
| 3 | Python 3.0 | 支持 `bytes`；**不再兼容 Python 2** |
| 4 | Python 3.4 | 大对象优化、更多类型（PEP 3154）；**3.8–3.13 默认** |
| 5 | Python 3.8 | 带外数据缓冲、缓冲区速度优化（PEP 574）；**3.14 起默认** |

```python
>>> pickle.DEFAULT_PROTOCOL     # 3.14 上默认已是 5
5
>>> pickle.HIGHEST_PROTOCOL     # 最高协议
5
```

> **版本注意**：协议 5 的 pickle 文件**不能被旧版 Python 读**（3.14 写的，3.11 打不开）。跨版本传输/存储时，显式指定低协议 `pickle.dumps(obj, protocol=4)`，或者干脆用 JSON。**协议默认值会随版本变**（3.14 从 4 升到 5），不要假设默认值稳定。

**`__reduce__`：pickle 的协议钩子**。自定义对象默认按 `__dict__` 序列化；`__reduce__` 让你自定义"怎么重建这个对象"——它返回 `(可调用对象, 参数)`，反序列化时调用 `可调用对象(*参数)` 重建：

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y
    def __reduce__(self):
        # 反序列化时用 Point(x, y) 重建，而不是塞回 __dict__
        return (Point, (self.x, self.y))

>>> p = pickle.loads(pickle.dumps(Point(3, 4)))
>>> p.x, p.y
(3, 4)
```

**⚠️⚠️ 安全：`pickle` 是任意代码执行通道。** 这一点必须大写加粗。

`__reduce__` 返回的"可调用对象 + 参数"在反序列化时会被**无条件调用**。攻击者构造一个恶意 pickle，`__reduce__` 返回 `(os.system, ("rm -rf /",))`——受害者一 `loads`，命令就执行了：

```python
>>> import os, pickle
>>> class Evil:
...     def __reduce__(self):
...         return (os.system, ("echo PWNED",))    # 反序列化时执行！
>>> pickle.loads(pickle.dumps(Evil()))
PWNED
```

**结论**：
- **永远不要 `pickle.loads` 不可信数据**（网络传过来的、用户上传的、别处下载的）。
- pickle 只用于**自己信任的闭环**：`multiprocessing` 进程间传参、自己的缓存文件、内存对象复制。
- 需要跨信任边界传对象 → 用 `json`（9.8.2）或专门的格式。
- 审计工具：`pickletools.dis(blob)` 可以**检查**一个 pickle 文件里有什么指令（是审计用的，不是安全边界）。

> **工程影响**：很多"API 数据泄露"漏洞的根源就是"图省事用 pickle 做缓存/做消息传递"。用 pickle 之前问一句：**这个字节流会不会经过不信任的路径？** 会，就换格式。

### 9.8.2 `json`：跨语言的文本格式

`json` 是**数据交换**的事实标准——人可读、跨语言、Python 标准库自带。它和 `pickle` 的分工：**pickle 管"Python 对象图"，json 管"可交换的数据"**。

```python
>>> import json
>>> json.dumps({"name": "boogo", "tags": ["a", "b"], "n": 42})
'{"name": "boogo", "tags": ["a", "b"], "n": 42}'
>>> json.loads('{"name": "boogo", "tags": ["a", "b"], "n": 42}')
{'name': 'boogo', 'tags': ['a', 'b'], 'n': 42}
```

**类型映射表**——JSON 的类型系统比 Python 小：

| Python | JSON | 反向 |
|--------|------|------|
| `dict` | `object` | `dict` |
| `list` | `array` | `list` |
| `str` | `string` | `str` |
| `int` / `float` | `number` | `int` / `float` |
| `bool` | `true` / `false` | `bool` |
| `None` | `null` | `None` |
| **`tuple`** | `array` | **`list`（类型降级！）** |
| **`set`** / **`datetime`** / **bytes** | ❌ 不支持 | ❌ |

```python
>>> json.dumps((1, 2))            # tuple → 数组
'[1, 2]'
>>> json.loads('[1, 2]')          # 反向变 list，不是 tuple
[1, 2]
>>> json.dumps({1, 2, 3})         # ❌ set 不支持
TypeError: Object of type set is not JSON serializable
>>> json.dumps({"d": datetime.now()})   # ❌ datetime 不支持
TypeError: Object of type datetime is not JSON serializable
```

> **⚠️ 陷阱 1：`NaN`/`Infinity` 是非法 JSON**。Python 默认会输出它们（`json.dumps(float("nan"))` → `'NaN'`），但这不是标准 JSON——**严格 JSON 解析器会拒绝**。跨语言/跨系统时，要么过滤，要么接受这个不兼容。这是 `json.dumps` 的一个著名"宽松点"。
>
> **⚠️ 陷阱 2：`ensure_ascii` 默认 `True`**——非 ASCII 字符被转义成 `\uXXXX`：
> ```python
>>> json.dumps("中文")
'"\\u4e2d\\u6587"'
>>> json.dumps("中文", ensure_ascii=False)   # 存成可读的 UTF-8 文本
'"中文"'
```

**自定义编码/解码**：`default=` 回调处理"JSON 不认识的类型"，`object_hook` 在解码时自定义对象构建：

```python
>>> from datetime import datetime
>>> def encode_default(o):
...     if isinstance(o, datetime):
...         return o.isoformat()          # datetime → ISO 字符串
...     raise TypeError(f"cannot encode {o!r}")
>>> json.dumps({"ts": datetime(2026, 8, 12, 9, 30)}, default=encode_default)
'{"ts": "2026-08-12T09:30:00"}'
>>> def decode_hook(d):
...     if "ts" in d:
...         d["ts"] = datetime.fromisoformat(d["ts"])   # 解码还原
...     return d
>>> json.loads('{"ts": "2026-08-12T09:30:00"}', object_hook=decode_hook)
{'ts': datetime.datetime(2026, 8, 12, 9, 30)}
```

**文件读写便捷版**（`dump`/`load` 直接接文件对象——和第 8 章的 `with` 无缝配合）：

```python
>>> with open("config.json", "w", encoding="utf-8") as f:
...     json.dump(config, f, indent=2, ensure_ascii=False)   # indent 美化
>>> with open("config.json", encoding="utf-8") as f:
...     config = json.load(f)
```

**`pickle` vs `json` 决策矩阵**：

| 维度 | `pickle` | `json` |
|------|----------|--------|
| 人可读 | ❌ 字节流 | ✅ 文本 |
| 跨语言 | ❌ 仅 Python | ✅ 所有语言 |
| 支持类型 | ✅ 任意 Python 对象图 | 基础类型 + 自定义钩子 |
| 引用/循环 | ✅ 保留 | ❌ 展开成树（循环会无限递归） |
| 安全性 | ⚠️ **不可信数据 = 任意代码执行** | ✅ 只是数据 |
| 性能 | 快（二进制） | 较慢（文本解析） |
| 版本兼容 | ⚠️ 协议随版本变 | ✅ 稳定 |

> **实战建议**：**配置、API 响应、跨语言数据 → `json`；Python 进程内缓存、`multiprocessing` 传参、对象深拷贝 → `pickle`**。两条铁律：跨信任边界永远 `json`；`pickle` 只进不出（只给自己用）。

### 9.8.3 其他格式纵览

| 格式 | 模块 | 特点 | 用途 |
|------|------|------|------|
| CSV | `csv` | 表格文本，带引号/转义规则 | 数据交换、Excel |
| TOML | `tomllib`（3.11+，只读）/ `tomli-w`（写） | 配置友好，嵌套结构 | 配置文件（`pyproject.toml`） |
| YAML | `pyyaml`（第三方） | 人类可读，引用/锚点 | 配置、K8s manifest |
| MessagePack | `msgpack`（第三方） | 二进制 JSON 类似物 | 高性能跨语言传输 |
| HDF5 | `h5py`/`pandas` | 层次化二进制大数据 | 科学数据（衔接卷 2） |
| numpy `.npy`/`.npz` | `numpy` | 数组原始字节 + 头 | 数值数组（衔接卷 2） |

> **注意**：`csv` 不是"用逗号切一下"——`csv` 模块处理引号、`\r\n`、换行内嵌引号这些真实世界的坑（9.2.3 的 `newline=''` 正是为了配 `csv` 的官方推荐）。配置文件序列化、科学数据序列化在卷 2/3 展开，这里只建立"序列化 = 类型映射 + 安全边界"的心智。

---

## 9.9 综合实战：一个带原子写的配置系统

把本章的碎片组装成一个真实系统。需求：**一个应用配置管理器**——从 JSON 读配置，改配置，**安全地写回**（崩溃/断电时配置文件要么是旧的、要么是新的，绝不读到半截）。

### 9.9.1 需求拆解

我们要解决的是 9.2.1 埋下的那个雷："`open(path, "w")` 在打开瞬间就把文件截断"。直接 `w` 写配置，写一半断电 → **配置文件损坏，应用下次启动崩**。解决思路是**原子写**：

```
write to temp file in same dir → flush → fsync → os.replace(tmp, target)
```

- 临时文件建在**目标同目录**：保证 `os.replace` 是同一文件系统内的原子改名（9.7.3）。
- `fsync` 保证落盘（9.4.1）。
- `os.replace` 要么成功（新文件就位）、要么没发生（旧文件还在）——**不存在中间态**。

### 9.9.2 组装：`pathlib` + `tempfile` + `json` + `os.replace`

```python
import json, os, tempfile
from pathlib import Path


class Config:
    """原子写 JSON 配置。读：缺文件返回默认；写：临时文件 + 原子替换。"""

    def __init__(self, path: Path, defaults: dict):
        self.path = Path(path)
        self.data = dict(defaults)

    def load(self) -> None:
        try:
            self.data.update(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except FileNotFoundError:
            pass                          # 首次运行：用默认配置
        # UnicodeDecodeError / json.JSONDecodeError 故意不吞——配置坏了要让人知道

    def save(self) -> None:
        payload = json.dumps(
            self.data, indent=2, ensure_ascii=False,
        ).encode("utf-8")
        # 临时文件建在目标同目录（原子替换的前提）
        with tempfile.NamedTemporaryFile(
            "wb", dir=self.path.parent, delete=False,
        ) as tf:
            tmp = tf.name
            try:
                tf.write(payload)
                tf.flush()                # 用户态缓冲 → 内核页缓存
                os.fsync(tf.fileno())     # 内核页缓存 → 磁盘
            except BaseException:
                os.unlink(tmp)            # 写失败：清理临时文件，不碰目标
                raise
        os.replace(tmp, self.path)        # 原子替换：旧文件直接变新文件
```

要点复习：

- **`dir=self.path.parent`**：临时文件必须和目标同目录（9.7.3 的原子性前提）。
- **`flush` + `fsync`**：两段落盘（9.4.1）——先保证数据进内核，再保证真落盘。
- **写失败清理临时文件**：否则每次崩溃留一个 `.tmp` 垃圾。
- **异常不吞**：`load` 里配置损坏会抛 `UnicodeDecodeError`/`JSONDecodeError` 传播给调用方——配置坏是要暴露的事故，不是要静默的事（呼应第 8 章"该抛就抛"）。

```python
>>> cfg = Config(Path("app.json"), {"host": "localhost", "port": 8080})
>>> cfg.load()
>>> cfg.data["port"] = 9000
>>> cfg.save()                        # 此刻 app.json 要么是旧的、要么是新的
```

### 9.9.3 与第 8 章联动：事务式资源管理

第 8 章 8.5 的 `Transaction` 和 `ExitStack` 在这里直接复用——**原子写本身就是一个资源管理问题**：临时文件必须"要么被替换、要么被清理"，正好是 `ExitStack` 的用武之地：

```python
import contextlib

def _safe_unlink(path):
    """删除临时文件；文件已被替换（不再存在）时静默。"""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def atomic_write_text(path: Path, text: str) -> None:
    """把 text 原子写入 path（含异常时的临时文件清理）。"""
    with contextlib.ExitStack() as stack:
        tf = stack.enter_context(
            tempfile.NamedTemporaryFile("w", encoding="utf-8",
                                        dir=path.parent, delete=False)
        )
        tf.write(text)
        tf.flush()
        os.fsync(tf.fileno())
        # 任何异常/提前退出：删临时文件（_safe_unlink 容忍"文件已被替换"）
        stack.callback(_safe_unlink, tf.name)
        os.replace(tf.name, path)        # 正常退出路径：原子替换
```

> **实战建议**：`ExitStack.callback` 是 **LIFO**（后注册先执行），且**某个回调抛异常不会阻止其余回调继续执行**——但 `close()` 最终会把**第一个**异常抛出来，**不会静默吞掉**（实测：正常退出时 `close()` 抛 `FileNotFoundError`）。所以清理回调必须写成"容忍目标不存在"的 `_safe_unlink`：正常路径 `os.replace` 成功之后，临时文件路径已不存在，若直接 `callback(os.unlink, tf.name)`，`close()` 会崩溃。这层防御不是多余的——`with` 块内 `return`、异常、`KeyboardInterrupt` 都会走清理路径，它必须不抛。

**一个完整的教训**：第 8 章的 `AtomicFileWriter` 练习（8.练习 6）和本章的 `atomic_write_text` 是**同一个模式的两个实现**——一个用类 + `__enter__`/`__exit__` 手写，一个用 `ExitStack` + 回调组合。看到两种写法等价，说明你已经掌握了"资源生命周期"这一抽象。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 文件 = 分层包装 | `open()` 返回 `TextIOWrapper` → 缓冲层 → `FileIO` 的三层栈，不是裸 fd |
| 三层职责 | `FileIO` 管系统调用、缓冲层减少调用次数、文本层管编码与换行 |
| 文件是协议集合 | 同时是迭代器（`iter(f) is f`）、上下文管理器（`with`）、有 `fileno()` 能力查询 |
| 模式字符串 | `r/w/a/x` + `+` + `b/t`；`w` 在 open 时截断；`x` 排他创建（原子） |
| 默认编码的坑 | `open()` 默认是 `locale` 编码（中文 Windows 是 cp936），不是 utf-8；写 `encoding=` |
| PEP 686 | 3.15 起默认 UTF-8 mode；当前用 `-X utf8` 可提前开启 |
| `errors` 策略 | strict/replace/ignore/backslashreplace/surrogateescape，各有适用与代价 |
| universal newlines | 默认读时 `\r\n`/`\r`/`\n` → `\n`；`newline=''` 关闭翻译写二进制式文本 |
| 缓冲与性能 | 写入分块 4 KiB+；逐字节写比一次性慢约 200×；`flush`≠`fsync` |
| 随机访问 | 二进制 `tell`/`seek` 是字节偏移；文本层是"cookie"，只允许绝对 seek |
| `struct` | 格式字符串描述布局；显式 `=`/`<`/`>` 字节序；`@` 本机对齐会填 padding |
| `mmap` | 文件映射成内存，随机访问/多进程共享；写映射需 `r+b` 打开 |
| `pathlib` | 路径对象化，`/` 拼路径；`read_text`/`glob`/`replace` 是文件操作门面 |
| 安全临时文件 | 用 `tempfile` 的随机名 + O_EXCL；别手拼 `/tmp/xxx` |
| 原子写 | 临时文件（同目录）+ flush + fsync + `os.replace`；崩溃不坏文件 |
| `pickle` | Python 对象图序列化；协议 0–5（3.14 默认 5）；**不可信数据 = 任意代码执行** |
| `json` | 跨语言数据交换；tuple→array 降级、`ensure_ascii`、`default=` 钩子 |
| 决策 | 配置/API/跨语言 → `json`；进程内缓存/多进程 → `pickle` |

---

#### 练习 9

**1.（预测输出）** 写出下列代码在 Windows 上的运行结果，并解释每个输出的原因：

```python
f = open("a.txt", "w", newline="")
f.write("a\nb")
f.close()
print(open("a.txt", "rb").read())

f2 = open("a.txt", "w")           # 默认 newline=None
f2.write("a\nb")
f2.close()
print(open("a.txt", "rb").read())
```

**2.（解释行为）** 中文 Windows 上，`open("a.txt", "w").write("中文")` 成功，但换到英文 Linux 上跑同样代码、内容却是乱码。解释原因（提示：9.2.2），并给出正确的写法。

**3.（修复 bug）** 下面代码想把每行写入文件，但结果 `a.txt` 里只有 `"ab"` 没有换行。指出问题并修复：

```python
with open("a.txt", "w") as f:
    f.writelines(["a", "b"])
```

**4.（预测输出）** 下列代码输出什么？为什么 `f.seek(2, 1)` 会报错而 `f.seek(0, 2)` 不会？

```python
f = open("a.txt", "w"); f.write("hello world"); f.close()
f = open("a.txt")
print(f.read(5))
try:
    f.seek(2, 1)
except Exception as e:
    print(type(e).__name__, e)
f.seek(0, 2)
print(f.tell())
```

**5.（手写实现）** 用 `struct` 实现一个二进制日志记录器：每条记录 = 时间戳（`int64`，小端）+ 级别（`uint8`）+ 消息（长度前缀 `uint16` + UTF-8 字节）。写三个 `append_log`/`read_logs` 函数，能追加、能全量读出 `(ts, level, msg)` 元组列表。提示：`struct.Struct("<qB")` + 前缀长度。

**6.（手写实现）** 实现 `iter(f.readline, sentinel)` 的行为：写一个函数 `lines_until(fileobj, stop_line)`，返回从当前指针读到 `stop_line` 之前的所有行。用第 5 章的迭代器协议解释它为什么能提前停止。

**7.（性能实验）** 生成一个 5 MB 的二进制文件，分别用 `write(b"x")` 逐字节、`write` 4 KiB 分块、一次性写入三种方式，用 `timeit` 测耗时并解释差距（提示：9.4.2）。

**8.（安全分析）** 解释为什么 `pickle.loads` 不可信数据等同于任意代码执行。给出一个 `__reduce__` 返回 `(os.system, ...)` 的恶意示例，并说明正确的替代方案。

**9.（手写实现）** 用 `pathlib` 写一个函数 `collect_files(root, exts)`，递归收集 `root` 下所有扩展名在 `exts` 里的文件，返回 `list[Path]`。要求：用 `glob` 的惰性迭代、跳过 `__pycache__` 目录。

**10.（设计）** 一个 Web 服务的会话数据需要持久化。方案 A：`pickle` 存到本地文件；方案 B：`json` 存到数据库。分别说明两种方案在"安全性、跨语言、性能、会话对象是否含非基础类型"四个维度上的取舍，并给出推荐。

**11.（综合实战）** 为 9.9.2 的 `Config` 类补一个 `save_atomic` 的兄弟方法 `save_safe`：不用 `tempfile`，而用 `pathlib` 的 `write_text` 到 `path.with_suffix(".tmp")`，再 `os.replace`。指出它相比 `NamedTemporaryFile` 版本的缺点（提示：临时文件路径可预测 → 竞态）。

**12.（深度思考）** `mmap` 把文件映射进内存，读大文件"像数组"。分析：① 什么场景 `mmap` 比 `read()` 快？② 什么场景 `mmap` 并不更快甚至更慢？③ 为什么写映射需要 `r+b` 而不是 `r`？④ 如果文件在映射期间被另一个进程 `truncate`，会发生什么？（提示：9.6.2 + 分页机制）

---

**进入下一章的准备**：

- ✅ 能画出 `open()` 的三层结构（文本层/缓冲层/`FileIO`），说出每层的职责
- ✅ 能解释 `open()` 默认编码的来源，以及为什么必须显式写 `encoding="utf-8"`
- ✅ 能说清 `newline` 参数的读/写翻译语义，以及 `\r\n` 双重翻译的坑
- ✅ 能解释 `flush()` 与 `os.fsync()` 的区别，以及为什么逐字节写慢 200 倍
- ✅ 能区分二进制层的 `seek`/`tell` 与文本层的"cookie"语义
- ✅ 会用 `struct` 打包二进制字段，能说出 `=` 与 `@` 的字节序/对齐差异
- ✅ 会用 `pathlib`、`tempfile` 完成安全的文件读写与原子替换
- ✅ 能区分 `pickle` 与 `json` 的适用边界，并且绝不对不可信数据 `pickle.loads`

> **衔接预告**：第 10 章"模块与包管理"会把视角从"单个文件"拉高到"文件如何组织成可复用单元"——`os`/`io`/`pathlib` 本身都是模块，`import` 机制决定它们如何被找到和加载；第 11 章"并发与异步编程"会看到文件 I/O 的异步形态（`asyncio` 的事件循环如何调度非阻塞 IO）；第 13 章"标准库精选"会补充 `shutil`（文件批量操作）等本章未展开的模块。

