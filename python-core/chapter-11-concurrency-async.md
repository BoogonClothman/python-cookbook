# 第11章 并发与异步编程

> **学习目标**：建立"进程 / 线程 / 协程"三张完整的心智地图——知道**每种的调度单位、内存模型、切换成本**；理解 GIL 的真实机制与影响（为什么它既不是灾难也不是借口）；掌握线程锁、进程池、asyncio 事件循环三套工具箱；能用决策矩阵在 IO 密集 / CPU 密集 / 混合场景做出正确选型，并避开死锁、竞态、过度并发三大陷阱。

---

第 10 章结尾埋了一个钩子："`sys.modules` 的全局性正是'为什么多线程下 import 是安全的'这一经典问题的答案"——本章来兑现它。在此之前，你的程序都是**单线程**的：从上到下、一次一件事。本章打开"同时做很多事"的世界。但先泼一盆冷水：**并发不是免费的**——它带来正确性难题（数据竞争、死锁）、调试难题（时序不可复现）和性能难题（切换开销）。本章的目标不是"教你用并发"，而是"**教你何时用、怎么用、以及不用时会怎样**"。

本章与前面章节的关系：第 13 章提到 `queue`/`contextvars` 是"点到为止"，本章展开它们的机制；第 14 章的 `faulthandler`/日志在此成为并发调试工具；第 10 章 `sys.modules` 的"只初始化一次"在此解释 import 的线程安全；第 8 章的 `with` 协议是锁的标配写法；第 5 章的生成器是协程（11.6）的进化前身。与第 15 章的分工：本章讲**并发正确性与模式**，第 15 章讲**单线程内的性能优化**。

---

## 11.1 并发心智模型：进程 / 线程 / 协程

### 11.1.1 三个抽象的定义与本质对比

**进程（process）**：操作系统级别的执行单元——**独立的内存空间** + 独立的资源。两个进程之间除了显式通信（管道/文件/网络）**谁也看不见谁**。

**线程（thread）**：进程内部的执行单元——**共享进程的内存**，有独立的执行栈。多个线程读写同一个变量，互相可见（这也是麻烦的来源）。

**协程（coroutine）**：**单个线程内**的"函数级"执行单元——共享一切，由**程序自己**（事件循环）协作式调度，而非操作系统抢占式调度。

```python
# 三种并发的"最小形态"
# 进程
import multiprocessing
p = multiprocessing.Process(target=work)   # 独立解释器实例

# 线程
import threading
t = threading.Thread(target=work)          # 同进程内共享内存

# 协程
import asyncio
async def work(): ...
asyncio.run(work())                        # 同线程内协作切换
```

六维对比：

| 维度 | 进程 | 线程 | 协程 |
|------|------|------|------|
| 调度者 | 操作系统 | 操作系统 | **程序自身**（事件循环） |
| 调度方式 | 抢占式 | 抢占式 | **协作式**（await 点让出） |
| 内存 | 独立（隔离） | 共享 | 共享 |
| 通信 | IPC（Queue/Pipe/共享内存） | 直接读写变量 + 锁 | 直接读写变量 |
| 切换成本 | ms 级（页表切换） | µs–ms 级（内核态） | **µs 级（纯用户态）** |
| 崩溃影响 | 一个进程崩溃不影响其他 | **一个线程崩溃杀整个进程** | 同左（共享进程） |
| 适用 | CPU 密集（多核） | IO 密集（老式） | IO 密集（现代首选） |

> **🔑 机制洞察**：切换成本阶梯（协程 < 线程 < 进程）来自"切什么"——协程只切换**执行栈**（用户态寄存器 + 栈指针）；线程要经过**内核**（系统调用进内核态，调度器换上下文）；进程除了线程的切换，还要换**页表**（虚拟内存映射，TLB 失效）。这就是为什么"一万个协程"可行而"一万个线程"会崩——线程有内核资源上限（栈默认 8MB 虚拟内存），协程的栈按需增长且轻量得多。

#### 跨语言对比：并发模型的家族谱

Python 的"进程/线程/协程"三件套不是孤例——各语言的并发模型都是同一谱系的不同组合：

| 语言 | 并发原语 | 调度 | 特点 |
|------|---------|------|------|
| Python | 线程 / 进程 / asyncio 协程 | OS 抢占 + 协作 | GIL 使 CPU 线程受限；三套 API 并存 |
| Java | `Thread` / `ExecutorService` / `virtual threads`（21+） | OS 抢占 | 虚拟线程 = JVM 级协程（对标 asyncio） |
| Go | **goroutine** | **运行时协作 + 抢占混合** | goroutine 默认无栈上限、channel 通信 |
| JavaScript | 单线程 + 事件循环 | 协作 | 没有多线程，只有 async/await |
| Rust | `std::thread` / async runtime | OS + 协作 | 无 GC、所有权保证线程安全 |

**两个关键观察**：

1. **"协程"是普遍趋势**：Java 的 virtual threads（Project Loom）、Go 的 goroutine、JS 的 async/await、Python 的 asyncio——大家都在往"轻量、协作式、可大规模"的模型收敛。Python 的 asyncio 就是这场趋势的一员；
2. **Python 的特殊性**：GIL 让 Python 的线程**不能做 CPU 并行**（11.1.3），所以 Python 生态的进程（multiprocessing）用得比别家多——这是 GIL 的"副作用"之一（也让进程池成了 Python 的独门标配）。

> **设计哲学**：Go 的 goroutine 与 Python asyncio 的对比最有启发——Go 用"运行时自动调度的协作 + 抢占"，程序员写同步代码就拿到并发；Python 用"显式 `async/await`"，程序员手动标注挂起点。Python 更啰嗦，但**更可控**（挂起点看得见，符合"显式优于隐式"的 Python 哲学）。

### 11.1.2 并发 vs 并行：Amdahl 定律

**并发（concurrency）≠ 并行（parallelism）**：

- **并发**：多个任务**交错执行**（单核也能做）——"看起来同时在做"；
- **并行**：多个任务**同时执行**（必须多核）——"真的同时在做"。

```python
# 类比：一个人同时煮饭+洗衣服（并发，交错做）
#       两个人一人做饭一人洗衣（并行，同时做）
```

**Amdahl 定律**（阿姆达尔定律）：并行加速比的上限由**不可并行部分**决定：

```
加速比 S(n) = 1 / ((1 - p) + p / n)

p = 可并行部分占比
n = 处理器/核心数
(1 - p) = 必须串行的部分（如初始化、聚合结果）

极限：n → ∞ 时，S → 1 / (1 - p)
```

```python
# 例：任务 90% 可并行（p=0.9）
# 4 核：  S = 1 / (0.1 + 0.9/4) = 1 / 0.325 ≈ 3.08 倍
# 16 核： S = 1 / (0.1 + 0.9/16) = 1 / 0.156 ≈ 6.4 倍
# ∞ 核：  S → 1 / 0.1 = 10 倍（永远到不了 10 倍！）
```

> **🔑 数学定义**：Amdahl 定律的教训——**串行部分 10%，并行部分 90%，无论多少核，加速比封顶 10 倍**。工程含义：加核之前先砍串行部分（初始化、I/O 汇总、全局锁）；加核的边际收益递减（4 核 3 倍、16 核才 6.4 倍）。这也是"IO 密集用并发、CPU 密集用并行"的数学根源：IO 等待是可并行化的"假串行"（等待时不占 CPU），所以并发就能吃掉等待时间。

### 11.1.3 GIL：Python 并发的第一道墙（🔑 机制洞察）

**GIL（Global Interpreter Lock，全局解释器锁）**：CPython 解释器同一时刻**只允许一个线程执行 Python 字节码**。

```python
>>> import sys
>>> sys._is_gil_enabled()      # 3.13+：检查 GIL 是否启用（自由线程构建为 False）
True
```

#### 为什么存在

CPython 的对象内存管理靠**引用计数**（第 3 章提过）：`x = obj` 时 `obj` 的引用计数 `+1`，`del x` 时 `-1`，归零即释放。问题：**引用计数的增减不是原子操作**——两个线程同时操作同一个对象，计数可能错乱（少一次 +1 就提前释放，悬垂指针 → 崩溃）。

解法选择：

1. 给每个对象加锁 —— 太贵（每个对象都要锁）；
2. 全局一把锁，保证"同一时刻只有一个线程在改解释器状态" —— **GIL 方案**（简单、单线程零开销）。

CPython 选了 2：**一个进程内只有一个线程能执行字节码**。

#### 持有与释放的机制

```python
# GIL 的切换策略：时间片 + IO 让出
>>> import sys
>>> sys.getswitchinterval()      # 默认 0.005 秒（5ms 时间片）
0.005
```

- **时间片轮转**：线程每执行 `sys.getswitchinterval()`（默认 5ms）后，解释器检查是否有其他线程等待 GIL，有则切换；
- **IO 时主动释放**：任何阻塞式 IO（`read`/`write`/`sleep`/`socket`）都会**释放 GIL**——因为等待 IO 不需要 CPU，让别的线程跑。

```python
# 实测：GIL 对两种任务的影响（timeit 对比）
import threading, time

def cpu_work():
    total = 0
    for _ in range(5_000_000):
        total += 1
    return total

def run_threads(n):
    threads = [threading.Thread(target=cpu_work) for _ in range(n)]
    for t in threads: t.start()
    for t in threads: t.join()

# CPU 密集：4 线程 ≈ 4 倍单线程耗时（GIL 串行化！）
# IO 密集（time.sleep）：4 线程 ≈ 1/4 单线程耗时（IO 时释放 GIL，并行等待）
```

| 任务类型 | GIL 的影响 | 原因 |
|---------|-----------|------|
| IO 密集（网络/磁盘/睡眠） | **几乎无感** | 等待时释放 GIL，线程并行等待 |
| CPU 密集（计算/循环） | **严重**（≈ 单线程） | 都在抢 GIL，时间片轮转 |
| C 扩展（numpy 等） | 取决于实现 | 可释放 GIL 后并行（`Py_BEGIN_ALLOW_THREADS`） |

> **🔑 机制洞察**：GIL 的真实影响不是"Python 不能并发"，而是"**纯 Python 的 CPU 计算不能并行**"。IO 密集并发（web 服务、爬虫、数据库访问）用线程完全够；CPU 密集并行必须走**多进程**（11.5）或**释放 GIL 的 C 扩展**（numpy/pandas 内部）。**"GIL 是 Python 慢的原因"是最大误解**——单线程 Python 的慢是解释器开销，与 GIL 无关。

#### 历史与未来：PEP 703 与自由线程

| 阶段 | 内容 |
|------|------|
| 1992 | GIL 随 CPython 诞生（解决引用计数竞争） |
| 多次讨论 | "去掉 GIL"的尝试（如 1999 年 Greg Stein 的 free-threading 补丁）因单线程性能下降 20–50% 被拒 |
| **PEP 703**（2023） | 提案：让 GIL 变成**可选**（no-GIL 构建）——通过"偏向引用计数"（biased refcounting）+ 每个对象加锁，把单线程开销控制在可接受范围 |
| **3.13（2024）** | 首个实验性自由线程（free-threaded）构建（`python3.13t`）；`sys._is_gil_enabled()` 可查询 |
| 未来 | 3.14+ 继续优化；生态（C 扩展）逐步适配线程安全 |

> **版本注意**：自由线程构建目前是**实验性**的——大多数 C 扩展尚未完全线程安全（需要显式加锁适配）。生产环境 3.13/3.14 默认仍是 GIL 版。**学习本章的内容（锁/进程/协程）在自由线程时代依然成立**——GIL 消失不等于数据竞争消失，反而意味着"曾经 GIL 帮你挡住的竞争"现在要自己处理。

---

## 11.2 线程：threading 与共享状态

线程是"共享内存 + 抢占式调度"的组合——**能力最强，陷阱最多**。本节从创建到同步，逐层展开。

### 11.2.1 Thread 的创建与生命周期

```python
import threading, time

def worker(name, delay):
    print(f"{name} start")
    time.sleep(delay)
    print(f"{name} done")

t = threading.Thread(target=worker, args=("A", 1))
t.start()            # 启动线程（异步返回）
t.join()             # 等待线程结束（阻塞）
print("main done")   # 输出顺序：A start → main done → A done？不——join 阻塞了
```

```python
>>> t = threading.Thread(target=worker, args=("A", 1))
>>> t.start()
>>> t.is_alive()     # 运行中
True
>>> t.join()         # 阻塞直到结束
>>> t.is_alive()
False
```

**`daemon` 线程**：主线程退出时，**非 daemon 线程会被阻塞等待**（程序不退出），而 daemon 线程**随主线程直接终止**：

```python
t = threading.Thread(target=worker, args=("A", 1), daemon=True)
t.start()
# 主线程结束 → daemon 线程被强杀（可能没执行完）
```

> **⚠️ 陷阱**：
> - **daemon 线程的"突然死亡"**：主线程退出时 daemon 线程被**强制终止**（不执行清理、不抛异常）——daemon 适合"后台心跳/监控"这种死了无所谓的线程，**资源清理类线程绝不 daemon**；
> - `join(timeout=...)` 超时返回后线程**可能还在跑**（join 只等待，不终止）；
> - 没有"安全终止线程"的 API——想要"停止线程"应该用 `Event` 发信号（见 11.2.4），让线程自己退出（协作式取消，和协程的取消同源）。

### 11.2.2 数据竞争与"假原子"

先看经典反例——两个线程各给同一个变量加 100 万次：

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(1_000_000):
        counter += 1

threads = [threading.Thread(target=increment) for _ in range(2)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)        # 期望 2_000_000，实际通常是 100 万左右！
```

为什么？**`counter += 1` 不是原子操作**——反汇编看它的字节码：

```python
>>> import dis
>>> def inc():
...     global counter
...     counter += 1
>>> dis.dis(inc)
  3           0 LOAD_GLOBAL    0 (counter)    # ① 读 counter 到栈
              2 LOAD_CONST     1 (1)
              4 BINARY_OP      0 (+=)         # ② 栈上相加
              6 STORE_GLOBAL   0 (counter)    # ③ 写回 counter
              8 RETURN_VALUE
```

**三条指令之间，GIL 可能切换线程**（5ms 时间片内可以执行上万条字节码，但**恰好**在 ① 和 ③ 之间切换时，两个线程都读了旧值，各加 1 后写回——**丢了一次更新**）：

```
线程 A: LOAD(读 counter=100) → [切换！] 
线程 B: LOAD(读 counter=100) → ADD → STORE(counter=101)
线程 A: ADD → STORE(counter=101)   ← A 的更新丢了！
```

> **🔑 字节码洞察**："GIL 保证线程安全"是**流传最广的并发误解**。GIL 只保证"**解释器内部状态**不会被两个线程同时修改"（引用计数、对象分配），**不保证"你的 Python 代码逻辑原子"**。`x += 1`、`d[k] = d.get(k, 0) + 1`、`list.append`（这个其实是原子的，见下）——每个都要看字节码/实现才知道原子性。**规则：多线程共享的可变状态，一律显式加锁**。

```python
# 哪些操作在 CPython 里是"真的原子"的？（GIL 保护的单条字节码/单次 C 调用）
# ✅ 原子：list.append / list.pop / d[k] 赋值 / 变量赋值（单条 STORE）
# ❌ 非原子：x += 1 / d[k] = d.get(k,0)+1 / 任何"读-改-写"复合操作
# ⚠️ 即使"原子"，也不要依赖它——自由线程时代（PEP 703）这些都不再安全！
```

### 11.2.3 锁：Lock 与 RLock

```python
import threading

counter = 0
lock = threading.Lock()

def increment():
    global counter
    for _ in range(1_000_000):
        with lock:                    # 等价 acquire/release，且异常安全（第 8 章 with）
            counter += 1

# 加锁后：结果稳定 = 2_000_000（正确，但串行化了——这就是并发的代价）
```

**`Lock`（互斥锁）**：同一时刻只能一个线程持有。**`RLock`（可重入锁）**：**同一个线程**可以多次 `acquire`（用于嵌套调用）：

```python
lock = threading.Lock()
lock.acquire()
lock.acquire()        # ❌ 死锁！Lock 不可重入，第二次 acquire 阻塞等待自己释放

rlock = threading.RLock()
rlock.acquire()
rlock.acquire()       # ✅ 同一线程可重入（计数 +1）
rlock.release()       # 释放一次（计数 -1）
rlock.release()       # 归零才真正释放
```

```python
# RLock 的真实场景：递归/嵌套函数共享一把锁
rlock = threading.RLock()

def outer():
    with rlock:
        inner()           # inner 也要同一把锁

def inner():
    with rlock:           # ✅ RLock：同一线程可以再拿
        ...

# 若用 Lock：outer 持锁 → inner 再 acquire → 死锁（自己等自己）
```

> **⚠️ 陷阱**：`Lock` 的 `acquire` 默认**无限阻塞**——`lock.acquire(timeout=5)` 设超时，返回 `False` 表示没拿到（避免永久卡死）。锁粒度权衡：**大锁简单安全但串行化**（并发白开）；**细锁并发好但易死锁**（锁顺序问题，见 11.2.6）。

#### 锁的真实开销：加锁不是免费的

```python
# 实测：锁对单线程代码的拖累（无竞争时）
import threading, timeit

def no_lock():
    return sum(range(1000))

lock = threading.Lock()
def with_lock():
    with lock:
        return sum(range(1000))

>>> timeit.timeit(no_lock, number=100_000)
0.31
>>> timeit.timeit(with_lock, number=100_000)
0.37       # 加锁开销约 +20%（无竞争时是纯系统调用开销）
```

| 场景 | 开销 | 原因 |
|------|------|------|
| 无竞争加锁/解锁 | 每次 ~0.1µs（系统调用） | 获取/释放原子操作 |
| 有竞争（多线程抢） | 可能毫秒级 | 阻塞 + 上下文切换 + 唤醒 |
| 锁竞争激烈 | 吞吐崩塌 | 线程都在等锁（串行化） |

> **🔑 性能洞察**：锁的代价主要在**竞争**——两个线程抢同一把锁时，锁等待让线程们实际退化为"串行 + 切换开销"，比单线程还慢。工程含义：(1) **锁保护的范围越小越好**（临界区短）；(2) **能用不可变数据/局部变量就别用共享状态**（无锁最快）；(3) 锁竞争严重时考虑改数据结构（如读写分离、`queue` 消息传递）。

### 11.2.4 同步原语：Event / Condition / Semaphore / Barrier

| 原语 | 解决的问题 | 核心 API | 类比 |
|------|-----------|---------|------|
| `Event` | 线程间**发信号**（一次/多次） | `set()`/`wait()`/`is_set()`/`clear()` | 旗帜/红绿灯 |
| `Condition` | 等待**某个条件**满足（配合锁） | `wait()`/`notify()`/`notify_all()` | 广播 |
| `Semaphore` | **限流**：控制最多 N 个并发 | `acquire()`/`release()` | 停车位 |
| `Barrier` | **对齐**：N 个线程到齐才继续 | `wait()` | 起跑线 |

```python
# Event：优雅的"停止信号"（比 daemon 强杀安全）
import threading, time

stop_event = threading.Event()

def worker():
    while not stop_event.is_set():      # 协作式退出
        do_work()
    print("worker exiting gracefully")

t = threading.Thread(target=worker)
t.start()
time.sleep(5)
stop_event.set()          # 发停止信号
t.join(timeout=10)        # 安全等待退出
```

```python
# Semaphore：限流（同时最多 3 个任务）
import threading
sem = threading.Semaphore(3)

def task(i):
    with sem:                    # 拿到"车位"才执行
        do_work(i)

# Barrier：N 个线程到齐才一起继续（如分块计算的同步点）
barrier = threading.Barrier(4)
def phase_worker():
    compute_part()
    barrier.wait()               # 等 4 个都算完
    merge_results()
```

> **实战建议**：选原语的口诀——"**要通知选 Event，要等条件选 Condition，要限流选 Semaphore，要对齐选 Barrier，要互斥选 Lock**"。80% 的场景用不上 Condition（它需要手写"等待-通知"循环，易错）；线程间传数据用 `queue.Queue`（11.3）比手写 Condition 更安全。

### 11.2.5 threading.local：线程局部存储

`threading.local` 让每个线程有**自己独立的变量副本**——解决"全局变量被多线程共享"的经典问题：

```python
import threading

ctx = threading.local()          # 线程局部对象

def set_user(name):
    ctx.user = name              # 每个线程各自存一份

def get_user():
    return getattr(ctx, "user", None)

# 线程 A set_user("alice")，线程 B set_user("bob")
# → A 看到 alice，B 看到 bob，互不干扰
```

**与第 14 章 `contextvars` 的关系**：`contextvars`（`ContextVar`）是 `threading.local` 的**异步升级版**——它不仅能隔离线程，还能隔离**协程**（同一个线程内不同协程各自独立），且支持"上下文复制"（`copy_context`）。规则：**线程场景用 `threading.local`，协程/异步场景用 `contextvars`**。

> **工程影响**：`threading.local` 是"**请求级上下文**"的经典载体（Web 框架的 request 对象：每个请求一个线程，`ctx.request` 全局可拿但互不串扰）。陷阱：线程池复用线程（11.4）时，`threading.local` 的**旧值会残留**——处理完要清理，否则下一个任务拿到上一个请求的上下文（著名的"请求串号" bug）。

### 11.2.6 死锁与排查

**死锁的四个必要条件**（Coffman 条件，缺一不可）：

1. **互斥**：资源一次只能被一个线程用（锁天然满足）；
2. **持有并等待**：拿着 A 锁等 B 锁；
3. **不可剥夺**：锁不能被别人抢走；
4. **循环等待**：A 等 B、B 等 A。

```python
# 经典死锁：两个线程反向拿两把锁
lock1, lock2 = threading.Lock(), threading.Lock()

def thread_a():
    with lock1:
        time.sleep(0.01)          # 故意制造交错
        with lock2:               # 等 lock2 —— 而 B 正拿着 lock2 等 lock1
            ...

def thread_b():
    with lock2:
        time.sleep(0.01)
        with lock1:               # 等 lock1 —— 互相等 → 死锁
            ...
```

**解药**：

1. **锁顺序约定**：所有线程**按同一顺序**拿锁（都先 lock1 后 lock2）——破坏"循环等待"；
2. **超时**：`lock.acquire(timeout=...)` 拿不到就放弃重试（破坏"持有等待"）；
3. **减少锁**：能用一把锁/不用锁就别用两把；
4. **设计层**：尽量避免嵌套锁（用消息传递 `queue` 替代共享状态 + 多把锁）。

```python
# 排查工具（衔接第 14 章）：死锁现场转储
import faulthandler, threading
faulthandler.dump_traceback_later(10, exit=True)   # 10 秒后打印所有线程栈并退出
# 输出里能看到：Thread A 停在 lock2.acquire、Thread B 停在 lock1.acquire → 死锁确认
```

> **⚠️ 陷阱**：死锁的可怕在于**不报错**——程序"卡住"但不崩溃。排查手段：`faulthandler.dump_traceback_later`（超时转储）、`threading.enumerate()` 列线程、日志记录锁的获取顺序。**预防 > 排查**：代码评审时看到"两把以上锁嵌套"就要警惕。

---

## 11.3 queue：线程安全的生产者-消费者

手写"共享列表 + 锁 + 条件变量"是并发编程最易错的部分——`queue.Queue` 把这些**全部封装好**：线程安全的队列 + 阻塞/超时语义。

### 11.3.1 Queue 的内部机制

```python
>>> import queue
>>> q = queue.Queue(maxsize=10)     # 有界队列（maxsize=0 表示无界）
>>> q.put("task")                   # 入队（满时阻塞）
>>> q.get()                         # 出队（空时阻塞）
'task'
>>> q.get(timeout=2)                # 超时返回：queue.Empty 异常
Traceback (most recent call last):
  ...
queue.Empty
```

**内部实现**（`Lib/queue.py`）：`deque`（第 13 章讲过的双端队列）+ `Condition`：

```
class Queue:
    def __init__(self, maxsize=0):
        self.queue = deque()            # 存储：deque（两端 O(1)）
        self.mutex = threading.Lock()   # 互斥锁：保护队列状态
        self.not_empty = Condition(self.mutex)   # 条件：有元素可取
        self.not_full = Condition(self.mutex)    # 条件：有空位可放
```

- `get()`：加锁 → 空则 `not_empty.wait()`（释放锁等待，被唤醒后重新拿锁）→ 取元素 → `not_full.notify()`（唤醒等待放入的）；
- `put()`：对称操作；
- **`task_done()`/`join()`**：`join()` 等待"所有已放入的任务都 `task_done()`"——生产者的"全部完成"信号。

### 11.3.2 生产者-消费者模式实战

```python
import queue, threading, time, random

q = queue.Queue(maxsize=5)          # 有界队列（带背压，见 11.3.3）

def producer():
    for i in range(20):
        q.put(f"task-{i}")          # 满时阻塞（自然限速）
        time.sleep(random.uniform(0.01, 0.05))
    q.put(None)                     # 哨兵：结束信号（每个消费者一个）

def consumer(name):
    while True:
        task = q.get()
        if task is None:            # 收到哨兵 → 退出
            q.task_done()
            break
        print(f"{name} processing {task}")
        time.sleep(random.uniform(0.05, 0.1))
        q.task_done()               # 必须调用！否则 join() 永远等

threads = [threading.Thread(target=consumer, args=(f"c{i}",)) for i in range(3)]
producer_t = threading.Thread(target=producer)
for t in threads + [producer_t]: t.start()
q.join()                            # 等所有任务 task_done（生产者也等）
# 注意：join 不包含哨兵后的收尾——工程里用 queue.join + 线程 join 双保险
for t in threads: t.join()
```

> **🔑 实战模式**：生产者-消费者是并发编程的"Hello World"——队列解耦了生产速度与消费速度（生产快没关系，队列缓冲；消费跟不上，`maxsize` 背压）。**结束信号用哨兵（`None`）而非"队列空就退出"**——队列空可能是"暂时没有"，哨兵才是"不会再有了"（每个消费者各收一个哨兵）。

### 11.3.3 有界队列与背压

**背压（backpressure）**：当消费者跟不上时，有界队列的 `put` 会**阻塞生产者**——这不是 bug，而是**自然的节流机制**：

```
无界队列（maxsize=0）：生产者疯狂生产 → 内存无限增长 → OOM
有界队列（maxsize=N）：生产者放满就停 → 消费者腾出空位再继续 → 内存有界
```

```python
q = queue.Queue(maxsize=100)        # 任务队列内存上限 ≈ 100 个任务
# 生产速度 > 消费速度时：put 阻塞 → 生产者"被迫"等消费者
# 效果：系统吞吐被消费者速度锚定，内存平稳
```

> **工程影响**：**生产系统几乎总是用有界队列**（`maxsize > 0`）——无界队列是内存炸弹（生产者的失控直接变成 OOM）。`queue.Queue` 还有 `LifoQueue`（后进先出，栈语义）和 `PriorityQueue`（按优先级取，内部是 `heapq`——第 13 章 13.2.6 的堆在这里兑现）。

---

## 11.4 线程池与 futures：并发的声明式抽象

手写 `Thread` + `queue` + 锁是"手动挡"；`concurrent.futures` 的 `ThreadPoolExecutor` 是"**自动挡**"——它把线程创建、任务分发、结果收集全部封装好。

### 11.4.1 ThreadPoolExecutor（concurrent.futures）

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch(url):
    time.sleep(0.5)               # 模拟 IO 等待
    return f"data from {url}"

urls = [f"https://api.example.com/{i}" for i in range(10)]

# 串行：10 × 0.5s = 5 秒
t0 = time.perf_counter()
results = [fetch(u) for u in urls]
print(f"串行: {time.perf_counter() - t0:.2f}s")        # ≈ 5.0s

# 线程池（4 线程）：≈ 1.5 秒（IO 等待并行）
with ThreadPoolExecutor(max_workers=4) as pool:
    t0 = time.perf_counter()
    results = list(pool.map(fetch, urls))
    print(f"线程池: {time.perf_counter() - t0:.2f}s")   # ≈ 1.5s
```

**内部机制**：`ThreadPoolExecutor` 就是"封装好的生产者-消费者"——内部有一个**任务队列 + `max_workers` 个工作线程**，`submit` 把任务放队列，工作线程循环 `get` 执行：

```python
# 等价的手写版（11.3 的生产者-消费者就是它的原理）
q = queue.Queue()
workers = [threading.Thread(target=worker_loop, args=(q,)) for _ in range(max_workers)]
# worker_loop: while True: fn, args = q.get(); result_queue.put(fn(*args))
```

> **🔑 性能数据**：IO 密集任务的加速比 ≈ `min(任务数, 线程数)`——10 个 0.5s 的请求、4 线程 → 约 2.5 批 = 1.25–1.5s。**线程池的最大价值：不用手动管理线程生命周期**（`with` 块退出自动 `shutdown` 等待）。

### 11.4.2 Future 对象

`submit` 返回 **`Future`**——一个"尚未完成的结果占位符"：

```python
with ThreadPoolExecutor(max_workers=4) as pool:
    future = pool.submit(fetch, "https://api.example.com/1")
    # future 立即返回（任务在后台跑）
    print(future.done())            # False（可能还没完成）
    result = future.result(timeout=5)   # 阻塞等待结果（超时抛 TimeoutError）
    print(result)

    # 回调：完成时自动调用
    def on_done(f):
        print(f"完成: {f.result()}")
    future2 = pool.submit(fetch, "...")
    future2.add_done_callback(on_done)
```

**`Future` 的状态机**：

```
pending（提交，未开始） → running（执行中） → finished（有结果）
                                          ↘ cancelled（被取消）
```

> **⚠️ 陷阱**：`future.result()` 在主线程调用是**阻塞**的——如果在"收集结果的循环"里逐个 `result()`，就退化成串行（先提交的都等第一个）。正确姿势：`concurrent.futures.as_completed(futures)` 按完成顺序取，或 `wait(futures, return_when=...)` 批量等。

### 11.4.3 什么时候线程池就够了

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch(url): ...                # IO 密集任务

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(fetch, u): u for u in urls}
    for future in as_completed(futures):        # 完成一个处理一个
        url = futures[future]
        try:
            data = future.result()
        except Exception as e:
            print(f"{url} 失败: {e}")           # 单个失败不影响其他
        else:
            process(data)
```

**选型判断**：你的任务是"等外部资源"（网络/磁盘/数据库）→ **线程池够用**（IO 密集，GIL 无碍）；任务是"纯计算"（循环/数值）→ 线程池**没用**（GIL 串行化），用进程池（11.5）。

| 场景 | 线程池 | 原因 |
|------|--------|------|
| 10 个 HTTP 请求 | ✅ 加速 ~N 倍 | 等待并行 |
| 1000 个文件读写 | ✅ 加速 | IO 释放 GIL |
| 矩阵乘法（纯 Python） | ❌ 无加速 | CPU 密集被 GIL 串行 |
| 混合（计算 + IO） | ⚠️ 部分 | 计算段串行，IO 段并行 |

> **实战建议**：**默认用 `ThreadPoolExecutor`，别手写线程**——它同时解决：线程复用（避免每任务建线程的开销）、异常隔离（`result()` 抛给调用方）、优雅关闭（`with`/`shutdown`）。手写 `Thread` 只在需要"长期存活的自定义线程"（守护进程、常驻消费者）时才有意义。

---

## 11.5 进程：multiprocessing 与多核

线程被 GIL 卡住 CPU 并行，进程是**绕过 GIL 的正道**——每个进程有独立的解释器和内存，天然并行。

### 11.5.1 为什么需要进程（绕过 GIL）

```python
import multiprocessing as mp
import time

def cpu_work(n):
    total = 0
    for i in range(n):
        total += i
    return total

N = 4
if __name__ == "__main__":            # ⚠️ spawn 机制必须（见 11.5.4）
    # 串行
    t0 = time.perf_counter()
    [cpu_work(20_000_000) for _ in range(N)]
    print(f"串行: {time.perf_counter()-t0:.2f}s")          # ≈ 4 份时间

    # 进程池（4 进程 → 4 核并行）
    t0 = time.perf_counter()
    with mp.Pool(4) as pool:
        pool.map(cpu_work, [20_000_000] * N)
    print(f"进程池: {time.perf_counter()-t0:.2f}s")        # ≈ 1 份时间（近线性加速）
```

> **🔑 性能数据**：CPU 密集任务，进程池的加速比接近核数（4 核 ≈ 3.5–3.9 倍）——因为每个进程独立持有 GIL，真正并行。对比 11.1.3：同样的任务用 4 线程 ≈ 无加速。**这就是"CPU 密集用进程、IO 密集用线程/协程"的实证**。

### 11.5.2 Process 与 Pool

```python
# 方式 1：Process（手动管理，类比 Thread）
import multiprocessing as mp

def worker(name, q):
    q.put(f"{name} done")

if __name__ == "__main__":
    q = mp.Queue()
    ps = [mp.Process(target=worker, args=(f"p{i}", q)) for i in range(3)]
    for p in ps: p.start()
    for p in ps: p.join()
    while not q.empty():
        print(q.get())
```

```python
# 方式 2：Pool（进程池，类比 ThreadPoolExecutor，且支持多参数）
import multiprocessing as mp

def add(a, b): return a + b

if __name__ == "__main__":
    with mp.Pool(4) as pool:
        results = pool.map(add, [(1, 2), (3, 4)])     # ❌ 注意：map 只传一个参数
        results = pool.starmap(add, [(1, 2), (3, 4)]) # ✅ starmap 解包参数
        single = pool.apply(add, (1, 2))              # 单任务
        async_res = pool.apply_async(add, (5, 6))     # 异步提交
        print(async_res.get(timeout=5))
```

| API | 语义 | 类比 |
|-----|------|------|
| `pool.map(f, it)` | 并行映射（单参数） | `ThreadPoolExecutor.map` |
| `pool.starmap(f, it)` | 多参数解包版 | `map` + `*args` |
| `pool.apply(f, args)` | 单任务（阻塞） | `executor.submit().result()` |
| `pool.apply_async` | 单任务（异步，返回结果对象） | `executor.submit()` |

#### ⚠️ 陷阱：`if __name__ == "__main__":` 保护

```python
# ❌ 不加保护：Windows/macOS（spawn）下会无限递归创建进程！
import multiprocessing as mp
p = mp.Process(target=work)      # 模块顶层！
p.start()
# spawn 机制：新进程要"重新导入"主模块来获取 target 函数
# → 重新导入时又执行到 mp.Process(...) → 又 spawn → 无限递归 → 崩溃

# ✅ 加保护：只有主入口才创建进程
if __name__ == "__main__":
    p = mp.Process(target=work)
    p.start()
```

### 11.5.3 进程间通信

进程内存独立，通信必须显式：

```python
# 1. Queue / Pipe：消息传递（推荐）
import multiprocessing as mp

def sender(q):
    q.put("hello")

if __name__ == "__main__":
    q = mp.Queue()
    p = mp.Process(target=sender, args=(q,))
    p.start(); p.join()
    print(q.get())          # 'hello'（数据被 pickle 序列化传输，第 9 章）

# 2. Value / Array：共享内存（快，但要自己加锁）
if __name__ == "__main__":
    counter = mp.Value("i", 0)          # 'i' = C int（共享内存）
    # ⚠️ 共享内存的 += 一样有竞争！mp.Value 自带锁：counter.value += 1 是原子的？
    # 不完全是——用 counter.get_lock() 显式保护：
    with counter.get_lock():
        counter.value += 1

# 3. Manager：代理对象（进程安全的 dict/list，最方便但最慢）
if __name__ == "__main__":
    mgr = mp.Manager()
    shared_dict = mgr.dict()            # 进程安全 dict
    shared_dict["key"] = "value"
```

| 方式 | 速度 | 复杂度 | 适用 |
|------|------|--------|------|
| `Queue`/`Pipe` | 中（pickle 序列化） | 低 | **默认首选**（消息传递） |
| `Value`/`Array` | 快（零拷贝共享内存） | 中（要加锁） | 数值/缓冲 |
| `Manager` | 慢（代理 + 网络协议） | 低 | 小数据、dict/list 共享 |

> **🔑 设计哲学**：进程间通信的推荐顺序与线程相反——线程**共享内存为主**（`threading.local`/锁），进程**消息传递为主**（Queue）。原因：进程共享内存的"锁保护"一旦出错就是跨进程的数据竞争（更难查），而消息传递（pickle 序列化）天然隔离。**能用 Queue 就别用共享内存**——"通过消息共享状态，而不是通过共享状态通信"（Erlang/Go 的并发哲学）。

### 11.5.4 spawn / fork / forkserver 三模式

| 启动方式 | 机制 | 平台 | 特点 |
|---------|------|------|------|
| **spawn** | 新进程**重新导入**主模块 | Windows、macOS（默认 3.8+） | 干净（无继承污染）；**慢**（重新导入）；必须 `if __name__` 保护 |
| **fork** | 复制当前进程内存（**含锁状态**） | Linux/Unix（默认） | 快；⚠️ 继承"持有中的锁/线程"——子进程里锁是死的 |
| forkserver | 先起一个干净服务进程，之后都从它 fork | Linux/Unix | 兼顾速度与干净 |

```python
import multiprocessing as mp
mp.set_start_method("spawn")        # 程序级指定（macOS 3.8+ 默认 spawn）
```

> **⚠️ 陷阱**：**fork 的继承陷阱**——fork 时如果父进程有线程持锁，子进程继承的锁是"死锁状态"（持有者是已不存在的线程）。所以：**fork 模式下，创建子进程前别开线程**；跨平台代码默认 **spawn**（Windows 只有 spawn，行为一致最稳）。`Pool`/`Process` 的 `target` 函数和参数**必须可 pickle**（第 9 章）——闭包、lambda、局部函数都会失败（`PicklingError`），这是进程版最常见的报错。

### 11.5.5 进程 vs 线程选型

| 维度 | 线程 | 进程 |
|------|------|------|
| CPU 密集并行 | ❌ GIL 卡死 | ✅ 近核数加速 |
| IO 密集 | ✅ 够用 | ✅（但重量级） |
| 启动开销 | 轻（µs） | 重（spawn 要重新导入，百 ms） |
| 内存 | 共享（省） | 独立（费） |
| 通信 | 变量 + 锁 | Queue/共享内存 |
| 崩溃 | 一个线程崩 = 全进程崩 | 进程隔离（可重启） |
| 适用 | IO 服务、web、爬虫 | 计算密集、并行数值、隔离任务 |

> **实战建议**：默认路线——**IO 密集用线程池（11.4）或协程（11.7），CPU 密集用进程池（11.5）**。进程的"重量级"不是缺点而是特性：**隔离**（一个子进程崩溃不影响主进程）是它的隐藏价值（如"可能崩的第三方计算"放进子进程）。

#### 进程池实战：并行处理一批文件

综合本章进程知识的一个完整案例——并行校验/压缩一批文件：

```python
import multiprocessing as mp
from pathlib import Path

def process_one(path: str) -> tuple[str, int]:
    """单个文件的 CPU 密集处理（如计算哈希/压缩）。"""
    data = Path(path).read_bytes()
    result = len(data)                   # 示例：返回处理结果
    return path, result

def main():
    files = [str(p) for p in Path("data").glob("*.dat")]

    # 串行基线
    serial = [process_one(f) for f in files]

    # 进程池并行（默认进程数 = CPU 核数）
    with mp.Pool() as pool:              # 不传参数 → mp.cpu_count() 个进程
        parallel = pool.map(process_one, files)

    assert serial == parallel            # 结果一致
    # 耗时：串行 ≈ N × 单文件时间；并行 ≈ (N/核数) × 单文件时间

if __name__ == "__main__":               # spawn 保护（11.5.4）
    main()
```

> **实战模式**：`pool.map` 的三个注意点——(1) **任务函数必须可 pickle**（顶层函数，不能是闭包/lambda，第 9 章）；(2) 任务返回值顺序与输入一致（`map` 保序），需要乱序返回用 `imap_unordered`；(3) 任务**异常**：`map` 在聚合时抛第一个异常（其他任务照跑），单个任务失败不影响整批——这正是"进程隔离"的价值（对比线程版一个异常杀全进程）。

---

## 11.6 协程与 async/await：事件循环的世界

进程与线程是"操作系统调度"的并发；协程是"**程序自己调度**"的并发——没有内核切换、没有锁（共享内存但协作式让出），是 IO 密集场景的现代首选。

### 11.6.1 协程的本质：生成器的进化

协程不是新发明——它是**生成器的直接进化**（第 5 章的生成器在此升级）：

| PEP | 版本 | 内容 |
|-----|------|------|
| PEP 342 | 2.5 | 生成器支持 `send()`/`throw()`——**双向通道**（可以往生成器里传值） |
| PEP 380 | 3.3 | `yield from`——委托给子生成器（生成器间"调用"） |
| PEP 492 | **3.5** | `async def`/`await` 语法糖——协程成为一等公民 |

```python
# 生成器版"协程"（PEP 342，手动 send）
def gen_coro():
    received = yield "ready"
    yield f"got: {received}"

c = gen_coro()
print(next(c))          # 'ready'
print(c.send("hello"))  # 'got: hello' —— 往生成器里发值！

# async 版（PEP 492，语法化）
async def async_coro():
    result = await something()    # await = "yield from + 等待"
    return result
```

**为什么需要协程**：线程的"抢占式切换"带来数据竞争（11.2.2）；协程是**协作式**的——**只有显式 `await` 的地方才可能切换**。这意味着：**协程之间不需要锁**（没有 await 的代码段是原子的）——这是协程相对线程最大的正确性红利。

> **🔑 设计哲学**：协作式调度的代价是"**一个协程卡住，全部卡住**"——`await` 点之间不能有阻塞调用（见 11.7.5 的陷阱）。但收益巨大：无锁、超轻量（万级协程）、切换成本 µs 级。Go 的 goroutine、Kotlin 的 suspend、JS 的 async/await 都是同一思想的实现。

### 11.6.2 async def / await 语法

```python
import asyncio

async def say_hello():          # async def 定义协程函数
    print("hello")
    await asyncio.sleep(1)      # await：挂起点，让出控制权给事件循环
    print("world")

# 协程对象是惰性的！
coro = say_hello()              # 只是创建对象，函数体【未执行】
print(type(coro))               # <class 'coroutine'>
# asyncio.run(coro)             # 必须有人驱动它（事件循环）
```

```python
>>> async def foo():
...     return 42
>>> f = foo()                   # 创建协程对象
>>> f                           # 还没执行！
<coroutine object foo at 0x...>
>>> asyncio.run(f)              # 事件循环执行 → 42
42
```

> **⚠️ 陷阱**：
> - **忘了 `await`**：`asyncio.sleep(1)` 没写 `await` → 只是创建协程对象，**什么都没发生**（还有个 "coroutine was never awaited" 警告）；
> - **忘了 `asyncio.run`**：直接 `say_hello()` 也是只创建对象；`asyncio.run()` 是 3.7+ 的标准入口（自动创建/关闭事件循环）；
> - `await` **只能**在 `async def` 内使用——普通函数里 `await` 是语法错误（"await outside async function"）。

#### 异步迭代与异步生成器（PEP 525，3.6+）

数据**逐条异步到达**（分页 API、流式响应、异步数据库游标）时，用**异步迭代器**：

```python
# 异步生成器：async def + yield（第 5 章生成器的异步版）
async def fetch_pages():
    page = 1
    while page <= 3:
        data = await fetch_page(page)     # 每次 yield 前可以 await
        yield data                        # 产出一条
        page += 1

async def main():
    async for page in fetch_pages():      # async for：异步迭代
        print(f"got page: {page}")
```

```python
# 协议层：__aiter__ / __anext__（第 5 章迭代器协议的异步版）
class AsyncRange:
    def __init__(self, n): self.n = n; self.i = 0
    def __aiter__(self): return self
    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration      # 异步版的 StopIteration
        self.i += 1
        return self.i
```

| 同步 | 异步 | 差异 |
|------|------|------|
| `yield` | `async def` + `yield` | 每个 yield 前可 `await` |
| `for x in it` | `async for x in it` | 迭代本身可挂起 |
| `__iter__`/`__next__` | `__aiter__`/`__anext__` | 返回 awaitable |
| `StopIteration` | `StopAsyncIteration` | 结束信号 |

> **实战建议**：**流式处理大响应**（逐条 JSON 流、逐行日志流）用异步生成器——避免一次性加载全部数据（第 5 章惰性的异步版）。`async for` 与 `asyncio.Queue`（11.7.4）组合是"异步消费者循环"的标准写法：`while True: item = await q.get()` 也可写成 `async for` 风格。

### 11.6.3 事件循环（EventLoop）

**事件循环**是协程世界的"调度器"：一个**单线程**循环，维护一个**就绪队列**，反复执行"取一个就绪协程 → 跑到下一个 await → 挂起"：

```python
# 事件循环的抽象流程（简化）
while ready_queue:
    coro = ready_queue.pop(0)
    result = coro.send(None)     # 推进协程到下一个 await
    if coro 还没完成:
        根据 result（IO 就绪事件）挂起，等事件再放回队列
```

```python
import asyncio

async def task(name, delay):
    print(f"{name} start")
    await asyncio.sleep(delay)   # 挂起：注册"delay 秒后唤醒"
    print(f"{name} done")

async def main():
    # 注意：这里两个任务【并发】执行
    await asyncio.gather(task("A", 1), task("B", 2))

asyncio.run(main())
# 输出顺序：
# A start → B start（B 不等 A！）→（1 秒后）A done →（再 1 秒）B done
# 总耗时 ≈ 2 秒（串行要 3 秒）
```

**`asyncio.run()` 的生命周期**（3.7+ 标准入口）：

```
asyncio.run(main())
  → 创建新事件循环（EventLoop）
  → 把 main() 包装成 Task 并运行到完成
  → 关闭事件循环（清理资源）
```

> **🔑 机制洞察**：`asyncio.sleep` 不是"睡 1 秒"——它向事件循环注册一个定时器然后**立即让出**。事件循环在这 1 秒里可以跑其他协程。**协程并发的本质：把"等待"变成"让出"**——每个 `await` 都是一次"我暂时不需要 CPU，先让别人跑"。这解释了为什么协程适合 IO 密集：IO 的等待时间全部被其他任务利用。

### 11.6.4 Task 与调度语义

**关键区分：`await coro` vs `await asyncio.create_task(coro)`**：

```python
async def main():
    # 方式 1：直接 await —— 逐个执行（没有并发！）
    await task("A", 1)          # A 跑完
    await task("B", 1)          # 才轮到 B（串行，总 2 秒）

    # 方式 2：create_task —— 并发调度
    t1 = asyncio.create_task(task("A", 1))   # 创建 Task，【立即】交给事件循环调度
    t2 = asyncio.create_task(task("B", 1))   # B 不等 A
    await t1                    # 等 A 完成
    await t2                    # 等 B 完成（总 ≈ 1 秒，并发）
```

| 写法 | 语义 | 时机 |
|------|------|------|
| `await coro` | 直接运行协程 | 需要"顺序执行"时 |
| `create_task(coro)` | 包装成 Task 并**并发调度** | 需要"并行执行"时 |
| `await gather(*tasks)` | 批量并发 + 等全部 | 扇出场景（11.8） |

**`Task`** 是"被事件循环调度的协程包装"（继承 `Future`）——`create_task` 返回的 Task 一旦创建就**进入调度队列**，即使你还没 `await` 它。`asyncio.gather` 内部就是"创建一堆 Task + 等全部完成"。

> **⚠️ 陷阱**：`create_task` 创建的任务**必须有地方 await/引用**——否则可能被 GC 回收（"Task was destroyed but it is pending" 警告）。规范：`tasks = [create_task(...) ...]` 存列表，最后 `await asyncio.gather(*tasks)`。

---

## 11.7 asyncio 实战

机制懂了，实战见真章。五个高频场景：并发请求、超时、限流、队列、桥接同步代码。

### 11.7.1 异步 IO：并发网络请求

```python
import asyncio

async def fetch(session, url):
    # 用 aiohttp（第三方，异步 HTTP 客户端）示意
    async with session.get(url) as resp:
        return await resp.text()

async def main():
    import aiohttp
    urls = [f"https://api.example.com/{i}" for i in range(20)]
    async with aiohttp.ClientSession() as session:
        # 并发 20 个请求
        results = await asyncio.gather(*(fetch(session, u) for u in urls))
    return results

# 对比实测（20 个各 0.5s 的请求）：
# 串行：10 秒
# 线程池（8 线程）：≈ 1.5 秒
# asyncio：≈ 0.5 秒（所有请求同时发出，总耗时 ≈ 单个请求耗时）
```

> **🔑 性能数据**：asyncio 的极限是"**同时等待的数量没有上限**"（万级连接都行）——每个连接只是一个协程对象（轻量）。对比线程池受 `max_workers` 限制、进程受资源限制。**IO 密集并发量大的场景，asyncio 是唯一能到"万级并发"的方案**（web 服务器、网关、爬虫）。

#### 按完成顺序处理：asyncio.as_completed / wait

`gather` 等**全部**完成才返回；需要"**完成一个处理一个**"（流式消费）时用 `as_completed`：

```python
import asyncio

async def fetch(url):
    await asyncio.sleep(hash(url) % 3)     # 模拟不同耗时
    return url

async def main():
    urls = [f"https://api.example.com/{i}" for i in range(10)]
    tasks = [asyncio.create_task(fetch(u)) for u in urls]

    # 完成一个处理一个（不管提交顺序）
    for coro in asyncio.as_completed(tasks):
        url = await coro
        print(f"完成: {url}")              # 按【完成时间】顺序输出

    # asyncio.wait：更细粒度的等待控制
    done, pending = await asyncio.wait(tasks, timeout=3, return_when=asyncio.FIRST_COMPLETED)
    # done: 已完成的；pending: 没完成的（可继续 await 或取消）
    for task in pending:
        task.cancel()
```

| 工具 | 语义 | 适用 |
|------|------|------|
| `asyncio.gather(*tasks)` | 等**全部**完成，返回结果列表 | 扇出-扇入（11.8） |
| `asyncio.as_completed(tasks)` | **逐个**产出完成的任务 | 流式处理、尽早消费 |
| `asyncio.wait(tasks, timeout=...)` | 等部分/全部，返回 done/pending | 超时控制、部分等待 |

> **⚠️ 陷阱**：`gather` 的**失败即取消**语义——任一任务异常，`gather` 立即抛（其余任务被取消）。想"部分失败继续跑"用 `return_exceptions=True`（异常作为结果返回），或用 `as_completed` 逐个 `try`。`as_completed` 内 await 某个任务抛异常时，**其他任务不受影响**（这正是它适合"批量 IO 容错"的原因）。

#### 异步上下文管理器：async with 的协议（PEP 492）

`async with session.get(url) as resp` 是第 8 章 `with` 协议的**异步版**——`__enter__`/`__exit__` 换成 `__aenter__`/`__aexit__`（都是协程）：

```python
class AsyncResource:
    async def __aenter__(self):          # 进入：可以 await（如异步连接）
        print("acquiring")
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc, tb):   # 退出：异步清理
        print("releasing")
        await asyncio.sleep(0.1)
        return False                     # False：不吞异常（第 8 章语义）

async def main():
    async with AsyncResource() as res:   # async with：进入/退出都是 await
        print("working")

# 输出：acquiring → working → releasing
```

```python
# contextlib 的异步版（第 8 章 8.5 的 @contextmanager 对应物）
from contextlib import asynccontextmanager

@asynccontextmanager
async def resource():
    conn = await connect()
    try:
        yield conn
    finally:
        await conn.close()               # 异常/正常都执行

async def main():
    async with resource() as conn:       # 用法与上下文管理器一致
        await conn.query(...)
```

| 同步（第 8 章） | 异步 | 场景 |
|----------------|------|------|
| `with open(...) as f` | `async with aiohttp.ClientSession() as s` | 异步资源（连接/会话） |
| `@contextmanager` | `@asynccontextmanager` | 协程版上下文 |
| `__enter__`/`__exit__` | `__aenter__`/`__aexit__` | 协议方法（协程） |

> **🔑 机制洞察**：`async with` 存在的根本原因是**异步资源的获取/释放本身需要等待**（连接池、握手、关闭）——同步 `with` 的 `__enter__` 不能 `await`，无法安全处理异步资源。**任何"打开/关闭都是 IO"的资源（网络连接、文件句柄的异步版、锁）都该实现异步上下文管理器**——aiohttp 的 `ClientSession`、`asyncio.Lock`（`async with lock:`）都是标准用法。

### 11.7.2 超时与取消

```python
import asyncio

async def slow():
    await asyncio.sleep(10)
    return "done"

async def main():
    try:
        # 超时：5 秒没完成就抛 TimeoutError（并取消任务）
        result = await asyncio.wait_for(slow(), timeout=5)
    except asyncio.TimeoutError:
        print("超时了")

    # 手动取消
    task = asyncio.create_task(slow())
    task.cancel()                # 请求取消
    try:
        await task
    except asyncio.CancelledError:
        print("任务被取消")
```

**取消的规范处理**（衔接第 8 章异常体系）：`CancelledError` 继承 `BaseException`（不是 `Exception`！）——普通 `except Exception` **接不住**：

```python
async def cleanup_task():
    try:
        await long_running()
    except asyncio.CancelledError:
        # 清理资源（关闭连接、回滚）...
        raise                # ⚠️ 必须重新抛出！否则任务"假完成"
```

> **⚠️ 陷阱**：捕获 `CancelledError` 后**必须 `raise` 重新抛出**——取消是"请求"，任务应该响应取消并传播它。吞掉 `CancelledError` 会让 `wait_for`/`gather` 的取消语义失效（任务假装还在跑）。

### 11.7.3 并发控制：Semaphore

`gather` 一次全发会打爆目标服务器/触发限流——用 `Semaphore` 限流：

```python
import asyncio

sem = asyncio.Semaphore(5)      # 最多 5 个并发

async def fetch(url):
    async with sem:             # 拿到"并发名额"才发请求
        async with session.get(url) as resp:
            return await resp.text()

async def main():
    urls = [f"https://api.example.com/{i}" for i in range(100)]
    # 100 个任务，但同时最多 5 个在飞
    results = await asyncio.gather(*(fetch(u) for u in urls))
```

> **实战模式**：爬虫/API 调用的标准姿势——`Semaphore` 限流 + `wait_for` 超时 + `gather` 并发。**先想清楚限流再写并发代码**：无限制的并发不是性能，是事故（被封 IP、拖垮目标服务、自己的资源耗尽）。

### 11.7.4 异步队列：asyncio.Queue

与线程版 `queue.Queue`（11.3）一一对应，只是 API 变成 `await`：

```python
import asyncio

async def producer(q):
    for i in range(20):
        await q.put(f"task-{i}")     # 满时【异步】等待（不阻塞事件循环！）
    await q.put(None)                # 哨兵

async def consumer(q, name):
    while True:
        item = await q.get()
        if item is None:
            q.task_done()
            break
        print(f"{name}: {item}")
        await asyncio.sleep(0.1)     # 模拟处理
        q.task_done()

async def main():
    q = asyncio.Queue(maxsize=5)     # 同样支持背压
    producers = [asyncio.create_task(producer(q))]
    consumers = [asyncio.create_task(consumer(q, f"c{i}")) for i in range(3)]
    await asyncio.gather(*producers, *consumers)
    await q.join()                   # 等全部 task_done

asyncio.run(main())
```

**与线程版的核心差异**：`await q.put()` 的"满时等待"**不阻塞事件循环**——等待期间其他协程照跑。线程版的 `q.put()` 满时阻塞**整个线程**（线程池里会占着一个 worker）。

> **🔑 对比洞察**：`asyncio.Queue` 内部就是"`deque` + 等待器列表"（没有锁！）——因为单线程事件循环里**不需要锁**，只需要"等待-唤醒"（`Future` 的 set/await）。这是协程"无锁并发"的又一次兑现：**同一套生产者-消费者模式，线程版要 Condition，协程版只要 Future**。

### 11.7.5 同步代码桥接：to_thread / run_in_executor

事件循环里**绝不能跑阻塞调用**（`time.sleep`/`requests.get`/大计算）——那会卡死整个循环（所有协程停摆）：

```python
import asyncio, time

async def bad():
    time.sleep(2)               # ❌ 阻塞整个事件循环 2 秒！其他协程全部冻结

async def good():
    await asyncio.sleep(2)      # ✅ 异步等待，事件循环继续跑

# 阻塞的同步函数怎么办？丢给线程池：
import requests

async def fetch_with_requests(url):
    # to_thread（3.9+）：同步函数在线程池里跑，协程异步等结果
    resp = await asyncio.to_thread(requests.get, url, timeout=5)
    return resp.json()
```

| 场景 | 正确姿势 |
|------|---------|
| 需要等待 | `await asyncio.sleep()` |
| 同步阻塞函数 | `await asyncio.to_thread(fn, *args)`（3.9+） |
| CPU 密集子任务 | `loop.run_in_executor(None, fn, ...)`（进程池） |
| ❌ 禁忌 | 事件循环里直接 `time.sleep`/`requests.get`/同步文件读 |

```python
async def main():
    # to_thread 的并发也走线程池（默认 ThreadPoolExecutor）
    results = await asyncio.gather(
        *(asyncio.to_thread(requests.get, u) for u in urls)
    )
```

> **⚠️ 陷阱**："事件循环里做同步 IO"是最隐蔽的 asyncio 性能 bug——**代码看起来在跑，实际是假并发**（一个 `time.sleep` 让所有协程排队等）。排查：程序慢但 CPU 空转 → 检查有没有阻塞调用在循环里。规矩：**asyncio 世界里，一切等待都要 `await`**。

---

## 11.8 并发模式与选型决策

### 11.8.1 决策矩阵

三张地图画完，回到工程核心问题：**我的任务用哪种？**

```python
# 一句话决策：
# 任务在"等"（网络/磁盘/用户）→ IO 密集 → 协程（首选）或线程
# 任务在"算"（循环/数值）→ CPU 密集 → 进程
# 既有等又有算 → 分层（计算放进程池，等待放协程）
```

| 场景 | 首选 | 备选 | 理由 |
|------|------|------|------|
| Web 服务（高并发连接） | **asyncio** | 线程 | 万级连接、无锁 |
| 爬虫/批量 API 调用 | **asyncio** | 线程池 | 并发量大 + 限流 |
| 数据库批量操作 | 线程池 | asyncio（配异步驱动） | 同步驱动居多 |
| 数值计算/矩阵运算 | **进程池** | numpy（C 释放 GIL） | CPU 并行 |
| 大数据并行（numpy 内部） | 进程/多进程 | — | 向量化 + 多核 |
| 简单脚本加速 | 协程（`asyncio.run`） | 线程池 | 零配置 |

**复杂度阶梯**（从低到高）：协程（无锁）< 线程池（声明式）< 手写线程 + 锁 < 多进程。**能用低复杂度解决的不用高的**——这是并发选型第一原则。

> **实战建议**：不确定时按这个顺序试——**先 `asyncio.to_thread`/线程池**（改动最小）→ 瓶颈在并发量就换 asyncio → CPU 密集上进程池。**并发方案在引入前先想清楚"它解决什么问题"**：如果单线程 + 超时就能满足，就别上并发（复杂度的代价 > 收益）。

### 11.8.2 常见并发模式

**模式 1：生产者-消费者**（11.3/11.7.4 已完整演示）——解耦生产与消费速度。

**模式 2：扇出-扇入（fan-out / fan-in）**——一个任务拆成 N 个并行子任务，再聚合：

```python
import asyncio

async def process_chunk(chunk):
    return sum(chunk)

async def main():
    data = list(range(1000))
    chunks = [data[i:i+100] for i in range(0, 1000, 100)]   # 10 块
    # 扇出：10 个并行子任务 → 扇入：聚合结果
    partials = await asyncio.gather(*(process_chunk(c) for c in chunks))
    return sum(partials)          # 聚合
```

**模式 3：流水线（pipeline）**——数据流经多个处理阶段（每阶段一个队列）：

```python
# 阶段 A（读）→ Queue1 → 阶段 B（处理）→ Queue2 → 阶段 C（写）
# 每个阶段独立消费/生产，形成流水线（管道思想，同 Unix pipe）
```

### 11.8.3 与第 15 章衔接：性能视角的并发

- 并发解决"**等待**"（IO 密集）与"**多核**"（CPU 密集并行）；
- 第 15 章解决"**单线程内的快**"：算法优化、`dis` 字节码、`numpy` 向量化、C 扩展、`PyPy`/JIT；
- 组合拳：**算法优化优先**（先砍复杂度）→ 需要并行时按本节矩阵选型 → 还不够再 C 扩展（15 章）。

> **工程影响**：并发不是性能银弹——**在 11.1.2 的 Amdahl 定律约束下，串行部分永远是瓶颈**。先剖析（14.9）确认瓶颈在"等待"还是"计算"，再决定上不上并发、上哪种。盲目并发（"用了线程一定快"）是新手最常见的性能反模式。

#### 异步生态速查（现实世界的 asyncio）

标准库 asyncio 是地基，生产环境通常配生态工具：

| 层 | 标准库 | 生态（第三方） | 说明 |
|----|--------|--------------|------|
| 事件循环 | `asyncio.run()` | `uvloop` | uvloop 是 C 实现的事件循环（快 2–4 倍） |
| HTTP 客户端 | `urllib`（同步） | **`httpx` / `aiohttp`** | 异步 HTTP（本章示例用 aiohttp） |
| Web 框架 | — | **`FastAPI` / `Starlette`** | 异步 web 服务（uvicorn 驱动） |
| 数据库 | `sqlite3`（同步） | `asyncpg` / `aiomysql` / `SQLAlchemy async` | 异步驱动 |
| 测试 | — | `pytest-asyncio`（11.9） | 事件循环测试 |

```python
# 一个"异步 Web 服务"的最小形态（FastAPI + uvicorn）
# 这不是本章教学重点，但让你知道 asyncio 在现实中的落点
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.get("/proxy/{url}")
async def proxy(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)          # 异步请求（不阻塞其他请求）
    return {"status": resp.status_code}
# 启动：uvicorn main:app —— 高并发请求都由 asyncio 事件循环处理
```

> **实战建议**：学完本章后进入异步 Web 生态的路线——`asyncio` 基础（本章）→ `httpx`（异步客户端）→ `FastAPI`（异步服务）→ `pytest-asyncio`（测试）。注意：**同步框架（Flask）与异步框架（FastAPI）不能混用阻塞 IO**——在 FastAPI 里用 `requests.get`（同步）会卡住事件循环（11.7.5 的陷阱在框架层同样成立）。

---

## 11.9 并发陷阱大全

### 11.9.1 死锁 / 活锁 / 饥饿

| 问题 | 表现 | 区别 |
|------|------|------|
| **死锁** | 全部**卡死**（互相等锁） | 无法推进（11.2.6 已详述） |
| **活锁** | 程序"在跑"但**不前进**（互相让路） | 状态在变但无进展 |
| **饥饿** | 某个线程**永远等不到**资源 | 其他线程在跑，它被饿死 |

```python
# 活锁示例：两个线程"礼貌地互相让"
lock_a, lock_b = threading.Lock(), threading.Lock()
def polite():
    while True:
        if lock_a.acquire(timeout=0.01):
            if lock_b.acquire(timeout=0.01):
                ...  # 成功
                break
            lock_a.release()     # 让出 → 另一个线程也这么干 → 永远让来让去
        time.sleep(0.001)

# 饥饿示例：高优先级任务反复抢锁，低优先级永远拿不到
```

> **⚠️ 陷阱**：活锁比死锁更阴险——死锁"卡住"好发现，活锁"CPU 忙但不干活"。解药与死锁类似：**锁顺序约定 + 退避策略（随机等待）**。

### 11.9.2 竞态与数据竞争：经典计数器案例

三种并发模型下的同一个 bug——"计数器 ++ 竞争"：

```python
# 版本 1：线程（GIL 假原子，11.2.2 已演示）
# counter += 1 在字节码层读-改-写，线程切换丢更新 → 结果 < 预期

# 版本 2：进程共享内存
counter = mp.Value("i", 0)
def inc(): 
    with counter.get_lock():     # 忘加锁？→ 同样丢更新（跨进程竞争更难查）
        counter.value += 1

# 版本 3：协程 —— 竟然也中招！
total = 0
async def inc():
    global total
    tmp = total                  # ① 读
    await asyncio.sleep(0)       # ② await！【让出】——另一个协程也读了 total
    total = tmp + 1              # ③ 写回 → 两个协程都基于同一旧值 → 丢更新

async def main():
    await asyncio.gather(*(inc() for _ in range(1000)))
# total ≠ 1000！因为 await 点是协程的"切换点"——跨 await 的状态不是原子的
```

> **🔑 机制洞察**：协程"无锁"的前提是"**没有 await 的代码段是原子的**"——但**跨 await 的读-改-写**照样竞争！规则：**协程里的共享可变状态，要么用 `asyncio.Lock` 保护，要么在 await 前完成读-改-写**。三种模型的共同教训：**共享可变状态是并发 bug 的温床，能避免就避免**（不可变数据、消息传递、每任务独立状态）。

### 11.9.3 过度并发：上下文切换开销

并发不是越多越好——线程/协程数存在最优区间：

```
吞吐量
  │        ╱──── 平台期
  │      ╱
  │    ╱           ╲ 下降（切换开销 > 并行收益）
  │  ╱               ╲
  └─┴──────────────────→ 线程数
    （核数附近最优）
```

```python
# 线程数经验法则：
# IO 密集：线程数 ≈ IO 等待占比 × 核数 × (1 + 余量)
#          常见做法：线程数 = 核数 × 5~10（甚至更多，取决于等待比例）
# CPU 密集：线程数 ≈ 核数（多了只有切换开销）
# 进程数：≈ 核数（mp.cpu_count()）
```

> **⚠️ 陷阱**：**"线程越多越快"是错的**——超过平台期后，线程调度的开销（内核态切换、缓存抖动、锁竞争）会**吃掉**并行收益甚至变负。GC 线程、GIL 轮转还会放大问题。**用并发数可配置**（环境变量/参数），生产环境实测调优，而不是拍脑袋定死。

### 11.9.4 并发调试实战

并发 bug 的调试难点是**时序不可复现**——"跑 10 次错 1 次"。工具箱（衔接第 14 章）：

```python
# 1. 日志必须带线程/协程名（衔接 13.9）
import logging
logging.basicConfig(format="%(asctime)s %(threadName)s %(message)s", level=logging.INFO)
# Thread-1, Thread-2 ... 一眼看出谁在什么时候做了什么

# 2. 线程列表快照
import threading
for t in threading.enumerate():
    print(t.name, t.is_alive())

# 3. 死锁转储（11.2.6）
import faulthandler
faulthandler.dump_traceback_later(10, exit=True)

# 4. 协程调试：asyncio 的调试模式
#    PYTHONASYNCIODEBUG=1 python app.py
#    → 未 await 的协程、慢回调、阻塞调用都会有警告

# 5. 竞态放大：多跑几遍（`pytest -x --count` 或循环）——竞态 bug 是概率性的
```

```bash
$ PYTHONASYNCIODEBUG=1 python app.py
# 输出示例：Task was destroyed but it is pending! → 有协程没被 await（11.6.4 陷阱）
```

> **实战模式**：并发 bug 排查四步——(1) 日志带线程名**复现时序**；(2) `faulthandler` 转储**死锁现场**；(3) 把可疑的共享状态改成"每任务副本"验证是不是竞争；(4) 修复后**保留复现测试**（用 `Event`/`barrier` 人为制造交错时序，让竞态可复现——这比"跑 100 遍碰运气"专业得多）。

#### 并发代码的测试（衔接第 14 章）

并发测试的难点：**时序是概率性的**——测试"偶尔红"让人抓狂。三个策略：

```python
# 策略 1：固定交错点（用 Event 制造确定的时序）
import threading

def test_race_controlled():
    step1, step2 = threading.Event(), threading.Event()

    def thread_a():
        counter += 1           # 读-改-写
        step1.set()            # 通知"我读完了"
        step2.wait()           # 等 B 也读完（制造竞争窗口）

    def thread_b():
        step1.wait()           # 等 A 读完 → 此时 A 还没写回 → 竞争！
        counter += 1           # 与 A 基于同一旧值
        step2.set()

    # 两个线程按 Event 精确交错 → 竞态【必然】发生 → 测试确定地复现 bug
```

```python
# 策略 2：压力放大（多轮多线程，统计断言）
# 不追求"必现"，而是"跑 N 轮必须有 N 轮正确"
def test_counter_concurrent():
    for _ in range(50):                    # 50 轮
        reset_counter()
        run_two_threads(100_000)
        assert counter == 200_000          # 每轮都必须对

# 策略 3：asyncio 测试（pytest 插件 pytest-asyncio / pytest.mark.asyncio）
import pytest
@pytest.mark.asyncio
async def test_async_task():
    result = await some_async_fn()
    assert result == expected
```

| 策略 | 适用 | 特点 |
|------|------|------|
| 固定交错（Event 同步） | 验证**竞态确实存在** | 确定性（首选） |
| 压力放大（多轮） | 验证**修复有效** | 概率性（次选） |
| 时间等待（`sleep` 猜时序） | ❌ 不推荐 | 慢 + 不稳定 |
| `pytest-asyncio` | asyncio 代码 | 事件循环自动管理 |

> **工程影响**：并发测试的黄金标准是"**确定性复现**"——用 `Event`/`barrier` 把线程钉在指定的交错点上，让竞态**必然发生**（而不是碰运气）。这样的测试：修复前必红（证明 bug 真实）、修复后必绿（证明修复有效）、跑一万遍都稳定。**"测 100 次偶尔失败"的测试不是测试，是噪音**——要么固定交错点，要么别写。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 三抽象 | 进程（独立内存/OS 调度/ms 切换）、线程（共享内存/OS 调度/µs 级）、协程（共享内存/协作调度/µs 级无锁） |
| 并发 vs 并行 | 并发=交错，并行=同时；Amdahl：加速比 ≤ 1/(1−p)，串行部分决定上限 |
| GIL | 引用计数非线程安全 → 全局锁；IO 时释放；CPU 密集线程≈无加速；PEP 703 自由线程（3.13 实验） |
| 线程 | `x += 1` 三条字节码间可切换（非原子！）；`Lock`/`RLock`/`Event`/`Semaphore`/`Barrier`；`threading.local`；死锁四条件 |
| queue | `deque` + `Condition`；生产者-消费者 + 哨兵；有界队列背压 |
| 线程池 | `ThreadPoolExecutor` = 封装的生产者-消费者；IO 密集够用；`Future` 状态机；`as_completed` |
| 进程 | CPU 密集近核数加速；`Pool.map/starmap`；spawn 需 `if __name__` 保护；Queue/共享内存/Manager；fork 继承锁陷阱 |
| 协程 | 生成器进化（PEP 342/380/492）；`async def`/`await` 惰性；事件循环单线程调度；`create_task` 并发 vs `await` 串行 |
| asyncio | `gather`/`wait_for`/`CancelledError` 必重抛/`Semaphore` 限流/`asyncio.Queue`/`to_thread` 桥接；循环里禁同步阻塞 |
| 选型 | IO 密集→协程/线程、CPU 密集→进程、混合→分层；复杂度阶梯从低到高 |
| 陷阱 | 死锁/活锁/饥饿；协程跨 await 竞争；过度并发（线程数 ≈ 核数×系数）；并发调试四步 |

---

#### 练习 11

**第 1–3 题：验证理解（预测/解释）**

1. 预测输出并解释：两个线程各执行 `counter += 1` 一百万次，`counter` 最终值可能是多少？为什么 GIL 没有阻止错误？反汇编 `counter += 1` 说明哪一步之间可能切换线程？

2. 解释：`queue.Queue` 内部为什么需要 `Condition` 而不只是 `deque` + `Lock`？`task_done()`/`join()` 解决了什么问题？

3. 判断对错并解释：(a) "GIL 让 Python 的线程完全没用"；(b) "asyncio 的协程之间不需要锁"；(c) "进程池一定比线程池快"。分别给出反例。

**第 4–6 题：动手实战**

4. 写一个生产者-消费者程序（线程版）：3 个生产者、5 个消费者、有界队列 `maxsize=10`，任务带编号，用哨兵结束。验证：输出无重复、无丢失（任务编号 0–99 各恰好处理一次）。

5. 用 `ThreadPoolExecutor` 实现并发下载：10 个 URL（用 `time.sleep` 模拟），对比串行/线程池（4/8/16 线程）的耗时，画出"线程数 vs 耗时"并解释曲线形状。

6. 用 asyncio 重写练习 5：`asyncio.gather` + `Semaphore(3)` 限流 + `wait_for` 超时。对比与线程池版的耗时与代码复杂度。

**第 7–9 题：实战进阶**

7. 用 `multiprocessing.Pool` 实现 CPU 密集任务（如大量质数判断/矩阵运算）的并行加速：串行 vs 2/4/8 进程，验证加速比并对照 Amdahl 定律（`p` 取你的任务可并行占比，算出理论上限）。

8. 构造并修复一个死锁：两个线程反向获取两把锁（带 `time.sleep` 制造交错），用 `faulthandler.dump_traceback_later` 确认死锁，再用"锁顺序约定"修复。写一个测试用 `Event` 人为制造交错时序，让死锁可复现。

9. 异步生产者-消费者 + 取消：用 `asyncio.Queue` 实现任务系统，消费者收到 `CancelledError` 时正确清理（重新 `raise`），验证 `wait_for` 超时后的取消传播。

**第 10 题：深度思考**

10. PEP 703（自由线程）讨论：如果未来 CPython 默认无 GIL，(a) 本章哪些结论会失效（如"`x += 1` 靠 GIL 部分保护"、"CPU 密集线程无加速"）？(b) 哪些结论依然成立（锁的必要性、协程模型、进程通信）？(c) 对 C 扩展生态（numpy/pandas）意味着什么？结合 11.1.3 与你的理解给出分析。

---

**进入下一章的准备**：
- ✅ 能画出进程/线程/协程的调度模型与切换成本对比
- ✅ 理解 GIL 机制（存在原因、IO 释放、CPU 串行）与自由线程方向
- ✅ 能解释 `x += 1` 的非原子性并正确加锁
- ✅ 会用 queue 生产者-消费者、ThreadPoolExecutor、multiprocessing.Pool、asyncio 四套方案
- ✅ 会用决策矩阵选型，并识别死锁/竞态/过度并发三大陷阱

下一章（第 12 章 元编程）将进入"写代码的代码"——装饰器细讲、描述符、元类。届时会用到第 6 章的函数对象、第 7 章的对象模型、第 10 章的 import 机制，把"类与函数的运行时可编程性"讲到底。第 11 章的并发视角（线程安全）也会在"元编程的全局副作用"处再次出现。