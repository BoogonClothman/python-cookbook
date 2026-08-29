# 第 7 章配套：设计模式全景

> **学习目标**：建立"模式 = 命名过的设计经验"的心智模型；掌握 GoF 三大类模式中与 Python 关联最强的 15 个；能判断每个模式**在 Python 里还需要不需要**（很多被语言特性替代）；能识别过度设计与反模式。

---

这是第 7 章 **7.9 节的完整版**。7.9 只讲了原则与 4 个重点模式（单例、工厂、适配器、策略）；本文件按 GoF 分类展开全部常用模式，每条都回答同一个问题：**"在 Python 里，这个模式还值得手写吗？"** 阅读顺序建议：先读 7.9.1 的 SOLID 原则，再回到本文件逐类过一遍。

与本章的关系：模式是 7.1–7.8 全部机制的**组织方式**——继承（7.5）支撑模板方法，组合（7.5.6）支撑装饰器/适配器/代理，特殊方法（7.7）支撑代理与观察者的底层，`@classmethod`（7.2.3）是工厂方法，`@dataclass`（7.8.1）替代建造者，`enum`（7.8.2）简化状态模式。**先有机制，后有模式**。

---

## 1. 设计模式与 SOLID 原则

### 1.1 模式四要素与 GoF 分类

**设计模式**（design pattern）是"对反复出现的设计问题的、命名过的、可复用的解法"。GoF《设计模式》（1994）收录 23 个模式，按目的分三类：

| 类别 | 数量 | 关注 | 模式 |
|------|:---:|------|------|
| 创建型（Creational） | 5 | 怎么造对象 | 工厂方法、抽象工厂、建造者、原型、单例 |
| 结构型（Structural） | 7 | 怎么组合对象 | 适配器、桥接、组合、装饰器、外观、享元、代理 |
| 行为型（Behavioral） | 11 | 怎么协作 | 责任链、命令、解释器、迭代器、中介者、备忘录、观察者、状态、策略、模板方法、访问者 |

每个模式四要素：**名称**（共同词汇）、**问题**（解决什么）、**方案**（结构与协作）、**后果**（权衡与代价）。**后果**最容易被忽略——没有代价的模式说明没读懂。

### 1.2 SOLID 详解（每条都带 Python 视角）

SOLID 是模式的地基。逐条看它在 Python 里怎么落地、怎么被违反：

**S — 单一职责（SRP）**：一个类只为**一个**变化原因负责。

```python
# ❌ God Object：一个类什么都管
class Report:
    def fetch_data(self): ...      # 数据获取
    def render_html(self): ...     # 渲染
    def save_to_db(self): ...      # 持久化
    def send_email(self): ...      # 通知

# ✅ 拆开：每个类一个职责
class DataFetcher: ...
class HtmlRenderer: ...
class ReportRepository: ...
```

> **注意**：SRP 的"职责"指**变化的原因**，不是"功能的数量"。`render_html` 与 `render_pdf` 可以放一个类（都随"格式"变化）；`fetch_data` 和 `send_email` 必须分开（随"数据源"和"通知渠道"独立变化）。

**O — 开闭（OCP）**：对扩展开放、对修改关闭。7.5.2 的"覆盖"是 OCP 的继承形态；Python 里更常见的是**注册表**形态：

```python
# ✅ 新格式只需"登记"，不动主逻辑（对扩展开放）
FORMATS = {}                                   # 注册表
def register(name):
    def deco(cls):
        FORMATS[name] = cls
        return cls
    return deco

@register("json")
class JsonSerializer: ...
@register("xml")
class XmlSerializer: ...

def serialize(data, fmt):
    cls = FORMATS[fmt]                          # 查表分派
    return cls().dump(data)
```

**L — 里氏替换（LSP）**：子类必须能替换父类而不破坏行为契约。

```python
class Bird:
    def fly(self) -> str:
        return "fly"

# ❌ 子类收窄了契约：所有把 Bird 当参数的地方，换成 Ostrich 都会炸
class Ostrich(Bird):
    def fly(self):
        raise NotImplementedError("鸵鸟不会飞")
```

LSP 在 Python 里最常见的两种违反：子类**抛父类不抛的异常**、子类**收窄入参/拓宽出参**。补救：把 `fly` 从基类拿掉，用 `Protocol`（7.6.4）声明"会飞的"接口，只有真正会飞的实现它。

**I — 接口隔离（ISP）**：不强迫客户端依赖它用不到的接口。Python 里 ISP 常被鸭子类型/`Protocol` 天然满足——客户端只依赖它调用的那部分接口：

```python
# ❌ 大而全的"接口"，用不到的也被迫依赖
class Worker(ABC):
    @abstractmethod
    def work(self): ...
    @abstractmethod
    def eat(self): ...            # 机器人工人也得实现"吃"

# ✅ 拆成小协议（7.6.4），按需组合
class Workable(Protocol):
    def work(self): ...
class Eatable(Protocol):
    def eat(self): ...
```

**D — 依赖倒置（DIP）**：依赖抽象，不依赖具体实现。落地手段是**依赖注入（DI）**——把依赖从"在内部 new 出来"改成"从外部传进来"：

```python
# ❌ 高层直接 new 具体实现，换数据库要改 App 内部
class App:
    def __init__(self):
        self.db = MySQLDatabase()

# ✅ 依赖注入：App 只认"实现了 connect/query 的对象"
class App:
    def __init__(self, db):       # db 可以是 MySQL / Postgres / 测试替身
        self.db = db
```

> **记忆口诀**：SRP 管"类的边界"，OCP 管"扩展方式"，LSP 管"继承契约"，ISP 管"接口粒度"，DIP 管"依赖方向"。**五个原则一起把"面向对象"推向"面向抽象"。**

### 1.3 模式会"消失"：语言特性替代一览

GoF 写作时的 C++ 语言缺很多东西，模式是**补语言之缺**。Python 的语言特性让相当一部分模式不再需要手写：

| 模式 | Python 替代 | 说明 |
|------|------------|------|
| 单例 | 模块级实例 | `import` 天然单例（7.9.2） |
| 工厂方法 | `@classmethod` 备选构造器 | 7.2.3 |
| 建造者 | `@dataclass` + 关键字参数 | 7.8.1 |
| 原型 | `copy.copy` / `copy.deepcopy` | 深浅拷贝专题 |
| 适配器 | 鸭子类型 | 结构匹配即兼容 |
| 装饰器（GoF） | `@decorator` 语法 / `__getattr__` 委托 | 语义不同，见 3.2 |
| 代理 | `property` / `__getattr__` | 7.4 |
| 外观 | 模块级函数 | 第 10 章 |
| 策略 | 一等函数 / `functools.partial` | 第 6 章 |
| 命令 | 闭包 / 可调用对象 `__call__` | 7.7.6 |
| 迭代器 | 生成器 / `__iter__` | 第 5 章 |
| 状态 | `enum` + 字典 / `match-case` | 7.8.2、第 5 章 |
| 模板方法 | 继承 + `super()` / `contextmanager` | 7.5、第 8 章 |
| 观察者 | 回调 / 事件 / 信号库 | |

**读模式的正确姿势**：先问"这个模式解决什么问题"，再问"Python 有没有原生特性已解决它"。有 → 用特性；没有 → 才手写模式。**模式不是装饰，是语言能力的补丁。**

---

## 2. 创建型模式：怎么造对象

### 2.1 工厂（Factory）：把"造"从"用"里解耦

**问题**：创建逻辑散落、实现可切换、构造复杂。**方案**：把"决定造哪个、怎么造"集中到一个入口。三个层级：

**① 简单工厂函数**——一个函数按参数返回不同对象：

```python
def make_serializer(fmt: str):
    if fmt == "json":
        return JsonSerializer()
    if fmt == "xml":
        return XmlSerializer()
    raise ValueError(f"未知格式 {fmt}")
```

**② 工厂方法**——让**类自己**提供多种"造自己的入口"，`@classmethod` 就是它的语法化（7.2.3 的 `Date.from_iso`）。关键在 `return cls(...)`，子类调用时造出子类实例。

**③ 抽象工厂**——创建"一族相关对象"（如一套 UI 控件：按钮+输入框+对话框）。Python 里通常一个函数或字典就够：

```python
def build_ui(theme: str):
    """返回一族配套的控件工厂"""
    if theme == "dark":
        return DarkButton, DarkInput, DarkDialog
    return LightButton, LightInput, LightDialog
```

**什么时候才值得抽象出工厂**：（1）创建逻辑会变（多实现、配置驱动）；（2）创建过程复杂（组装、缓存、注册）；（3）测试需要注入替身。**反模式**：只有一个实现还硬套工厂——`if/elif` 换成字典分派是 Python 里最常见的"降噪"，但为模式而模式的工厂是负资产。

### 2.2 单例（Singleton）：全局唯一，慎用

**问题**：全局只需要一个实例。**方案**：把"只产一个实例"固化进类。三种实现对比：

| 实现 | 代码量 | 是否防子类旁路 | 推荐度 |
|------|:---:|:---:|:---:|
| 模块级实例（7.9.2 方式一） | 2 行 | 不防（但也没必要防） | ⭐⭐⭐ 默认 |
| `__new__` 拦截 | ~5 行 | 不防（子类各自实例） | ⭐⭐ |
| 元类 | ~8 行 | 防（所有子类共享） | ⭐ |

`__new__` 版本有个隐蔽坑：**子类会各自有实例**（`cls._instance` 按子类存）。要"全继承树唯一"得用元类版。

**线程安全**：CPython 的 GIL 让 `__new__` 里"检查-创建-赋值"三步在单条指令粒度上不是原子的，极端并发下可能建出两个实例。需要绝对安全时加 `threading.Lock`（第 11 章）。

**为什么常被当反模式**：全局状态让测试无法注入替身、让并发程序共享隐式状态。**Borg 模式**是 Python 特有的替代——所有实例**各自是对象**但共享同一份 `__dict__`：

```python
class Borg:
    _shared = {}
    def __new__(cls, *a, **kw):
        inst = super().__new__(cls)
        inst.__dict__ = cls._shared     # 共享状态字典
        return inst
>>> a, b = Borg(), Borg()
>>> a.x = 1
>>> b.x                                # b 看到 a 的设置
1
>>> a is b                             # 但 a、b 不是同一个对象
False
```

**结论**：默认模块级单例；要"构造上保证唯一"用 `__new__`/元类；要"状态唯一但不强绑对象身份"用 Borg。

### 2.3 建造者（Builder）：复杂构造的分步组装

**问题**：对象构造参数太多、需要分步/可选地装配。**方案**：把构造拆成链式步骤。Java 里 Builder 是标配；**Python 里 `@dataclass` + 关键字参数 + 默认值已覆盖 90% 场景**（7.8.1）。真正需要链式 Builder 的是"参数几十个且分组可选"的配置对象：

```python
@dataclass
class HttpRequest:
    method: str
    url: str
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    timeout: float = 5.0

    def with_header(self, k, v):        # 链式方法，返回 self 以便 .with_().with_()
        self.headers[k] = v
        return self
    def with_timeout(self, t):
        self.timeout = t
        return self

req = HttpRequest("POST", "https://api.example.com").with_header("X-K", "v").with_timeout(10)
```

> **注意**：链式 Builder 的代价是**破坏 dataclass 的不可变性**（方法就地改字段）。要不可变 + 链式，用 `functools.replace` 返回新对象，或用第三方 `attrs`/`pydantic`。**判断：字段多到构造器签名不可读，才考虑 Builder；否则 `@dataclass` 就够。**

### 2.4 原型（Prototype）：以复制代替新建

**问题**：创建对象很贵，或对象状态复杂想"复制一份改一点"。**方案**：以现有对象为原型，复制出新对象。Python 用 `copy` 模块一行搞定（深浅拷贝专题已深讲）：

```python
>>> from copy import deepcopy
>>> template = Config(trace=True, retries=3, hooks=[hook1])
>>> dev = deepcopy(template); dev.env = "dev"     # 复制一份再微调
```

GoF 里"原型必须实现 clone 方法"的样板，在 Python 里就是 `copy.copy`/`copy.deepcopy`——又一个被语言特性替代的模式。

---

## 3. 结构型模式：怎么组合对象

### 3.1 适配器（Adapter）：接口不同，翻译一层

**问题**：目标接口与现有类接口对不上。**方案**：包一层"翻译"。

GoF 分**类适配器**（靠继承）与**对象适配器**（靠组合）。Python 里优先组合 + 鸭子类型（7.5.6）：

```python
class OldReader:
    def __init__(self):
        self.lines = ["a", "b"]
    def readline(self):
        return self.lines.pop(0) if self.lines else ""

# 对象适配器：组合 + 转发
class ReaderAdapter:
    def __init__(self, old: OldReader):
        self._old = old
    def read(self):                      # 补齐目标接口 read()
        return self._old.readline()
```

**自动转发式适配器**——用 `__getattr__`（7.4.4）把未定义属性全委托给内层对象，只覆盖需要"翻译"的方法：

```python
class AutoAdapter:
    def __init__(self, wrapped):
        self._wrapped = wrapped
    def __getattr__(self, name):         # 没定义的属性，一律交给内层
        return getattr(self._wrapped, name)
    def read(self):                      # 只"翻译"这一个接口
        return self._wrapped.readline()
```

**鸭子类型才是真正的答案**：多数情况下目标函数只依赖几个方法，直接用 `__getattr__` 或裸对象即可，适配器类都不用写。**判断：适配成本 < 改源码成本才适配；否则直接改接口。**

### 3.2 装饰器模式 vs Python `@decorator`：同名不同物

**最容易被混淆的一组**。两者名字相同，语义和实现完全不同：

| | GoF 装饰器 | Python `@decorator` |
|---|---|---|
| 包装对象 | **对象**（运行时） | **函数/类**（定义期） |
| 时机 | 运行时任意时刻组装 | 定义时一次性应用 |
| 能否叠加 | 能（多层包装） | 能（多层装饰） |
| 能否卸载 | 能（拆掉包装） | 不能 |
| 本质 | 组合 + 委托 | 语法糖：`f = deco(f)` |

**GoF 装饰器在 Python 里**——给对象运行时添加职责，用组合 + 委托：

```python
class LoggedReader:                      # 装饰"对象"：给 reader 加日志职责
    def __init__(self, reader):
        self._reader = reader
    def read(self):
        print("read 被调用")
        return self._reader.read()

r = LoggedReader(FileReader())           # 运行时组装，想卸就换个普通 reader
```

**Python `@decorator`**——定义期变换函数（第 12 章深讲），作用在**函数**上：

```python
def logged(fn):
    def wrapper(*a, **kw):
        print(f"{fn.__name__} 被调用")
        return fn(*a, **kw)
    return wrapper

@logged                                   # 定义时套上，之后固定
def read(): ...
```

> **辨析结论**：要"给某个对象实例动态加职责"→ GoF 装饰器（组合委托）；要"给某个函数定义期加行为"→ Python `@decorator`。**两者不是同一件事的两种写法**，是"对象包装"与"函数变换"两种不同机制。

### 3.3 代理（Proxy）：为访问加一层控制

**问题**：不能/不想直接访问目标对象。**方案**：用一个代理对象站在前面，控制访问。三种典型用途，Python 各有对应：

| 用途 | 目的 | Python 落地 |
|------|------|------------|
| 懒加载（Virtual） | 真正用到才创建 | `property`（7.4.5 懒加载） |
| 访问控制（Protection） | 校验权限 | `__getattribute__`（7.4.4 安全网关） |
| 远程（Remote） | 本地代理远端 | 网络层，超出本章 |

懒加载代理的最小形态（呼应 7.4.5）：

```python
class HeavyService:
    def query(self): ...                 # 昂贵对象

class Proxy:
    def __init__(self):
        self._real = None
    def query(self):
        if self._real is None:
            self._real = HeavyService()  # 首次调用才真正创建
        return self._real.query()
```

**代理 vs 适配器**：适配器改**接口**（翻译），代理不改接口、只管**访问方式**（延迟/鉴权）。**代理 vs 装饰器**：装饰器加**职责**，代理加**控制**。

### 3.4 外观（Facade）：给复杂子系统一个"大门"

**问题**：子系统类很多、调用序列繁琐。**方案**：提供一个简化入口。Python 里最简单的 Facade 就是**模块级函数**：

```python
def start_server():
    """把配置、监听、启动三步收敛成一个入口"""
    cfg = load_config()
    listener = create_listener(cfg.port)
    listener.bind(); listener.listen()
    return listener
```

调用方只面对 `start_server()`，不用关心背后的类。**外观的意义在 Python 里几乎被"模块即门面"消解**——第 10 章会讲模块作为组织单元。

### 3.5 组合（Composite）与享元（Flyweight）：一句话各得其所

- **组合**：树形结构递归处理（文件系统、UI 树、表达式树）。Python 里"节点既有子节点接口又自己实现"的递归，靠鸭子类型 + 递归天然成立，无需模式类。
- **享元**：大量重复对象共享内部状态。Python 里对应 `functools.lru_cache`、字符串驻留（intern）、`__slots__`（7.8.3 省内存）。GoF 手写的"共享池"，在 Python 里是缓存工具的事。

---

## 4. 行为型模式：怎么协作

### 4.1 策略（Strategy）：行为是参数

7.9.5 已给核心例子：**Python 里策略 = 函数**，不需要策略类层次。补两个工程细节：

**策略带参数时用 `partial`**：

```python
>>> from functools import partial
>>> def scale(data, factor): return [x * factor for x in data]
>>> double = partial(scale, factor=2)      # 绑定参数的策略
>>> double([1, 2, 3])
[2, 4, 6]
```

**什么时候仍值得用"策略类"**：策略本身需要状态（如带缓存、带配置的压缩器），或需要组合多个策略。此时实现 `__call__`（7.7.6）让实例可调用，调用方语法不变。

### 4.2 模板方法（Template Method）：骨架在父类，钩子交给子类

**问题**：算法骨架固定，个别步骤因实现而异。**方案**：父类定骨架，子类覆盖"钩子方法"。这正是 7.5 继承 + `super()` 的典型应用：

```python
class DataPipeline:                        # 骨架
    def run(self):                         # 模板方法：固定流程
        data = self.load()                 # 钩子 1
        cleaned = self.clean(data)         # 钩子 2
        return self.save(cleaned)          # 钩子 3

class CsvPipeline(DataPipeline):
    def load(self): ...                    # 实现钩子
    def clean(self, data): ...
    def save(self, data): ...
```

**Python 里的替代**：如果只是"前后固定、中间可变"，`contextlib.contextmanager` 生成器版上下文管理器（第 8 章）常常更简洁；真正的"多步钩子骨架"才值得继承式模板方法。

### 4.3 观察者（Observer）：状态变化通知订阅者

**问题**：一个对象状态变化，多个对象需要响应。**方案**：订阅/通知。最小实现：

```python
class Subject:
    def __init__(self):
        self._observers = []
    def attach(self, o): self._observers.append(o)
    def detach(self, o): self._observers.remove(o)
    def notify(self, event):
        for o in self._observers:
            o.update(event)

class Logger:                               # 观察者
    def update(self, event): print(f"log: {event}")
```

**⚠️ 陷阱——观察者引用泄漏**：如果观察者是长生命周期对象、主题是短生命周期，用强引用列表会让主题**永远无法回收**（7.7.2 讲过的"还有引用就不死"）。用 `WeakSet`（弱引用集合）替换强引用列表：

```python
from weakref import WeakSet

class Subject:
    def __init__(self):
        self._observers = WeakSet()         # 弱引用：观察者死了自动移除
    def attach(self, o): self._observers.add(o)
    def notify(self, event):
        for o in list(self._observers):     # 遍历弱集合时拷贝一份
            o.update(event)
```

**工程化观察者**：标准库有 `logging` 的 handler 机制、第三方有 `blinker`（信号库）。Python 3.9+ 的字典合并、事件循环（第 11 章）也是观察者的现代形态。

### 4.4 状态（State）：行为随状态切换

**问题**：同一对象在不同状态下行为不同，`if/elif` 越来越长。**方案**：把状态与行为建模出来。GoF 用"状态类层次"；**Python 里 `enum`（7.8.2）+ 字典/`match-case`（第 5 章）通常更直接**：

```python
class TrafficLight:
    def __init__(self):
        self.state = State.RED

    def next(self):
        match self.state:                   # match/case 分发到下一状态
            case State.RED:    self.state = State.GREEN
            case State.GREEN:  self.state = State.YELLOW
            case State.YELLOW: self.state = State.RED

    def action(self):
        return {
            State.RED: "停车",
            State.GREEN: "通行",
            State.YELLOW: "减速",
        }[self.state]
```

**什么时候需要"状态类"**：状态转换伴随**复杂副作用**（进入/退出动作、历史回退），字典分发表达不了副作用钩子时，再回到 GoF 的状态类。

### 4.5 命令（Command）：把"动作"变成可传递/可撤销的对象

**问题**：把动作封装成可存储、可排队、可撤销的对象（undo 栈、任务队列、宏）。**方案**：命令对象。Python 里**闭包与 `partial` 已封装"动作 + 参数"**：

```python
from functools import partial
undo_stack = []
def delete_file(path):
    os.remove(path)
    undo_stack.append(partial(restore_file, path))    # 反向操作入栈
```

需要"命令对象"的场合——命令本身要携带状态（执行时间、重试次数）、或要序列化传输——用 `__call__`（7.7.6）类即可。**优先闭包，命令类留给有状态/可序列化的需求。**

### 4.6 迭代器、责任链、中介者：一行带过

- **迭代器**：已完全"消亡"——生成器（第 5 章）与 `__iter__` 协议（7.7.5）就是原生迭代器。
- **责任链**：链式处理请求（中间件）。Python 里就是**装饰器链**或**中间件函数列表**，如 Web 框架的 middleware 就是责任链。
- **中介者**：解耦网状协作。Python 里对应**事件总线**/回调——第 11 章异步编程会重逢。

---

## 5. 模式该用还是不该用：决策树

写代码遇到"要不要套模式"时，按这个顺序想：

```
① 这个"问题"在 Python 里还存不存在？
   └─ 已被语言特性解决（对照 1.3 表）→ 用特性，结束
② 问题是"反复出现"的，还是这一次性的？
   └─ 一次性 → 别模式化，直接写清楚
③ 套模式能显著降低某个维度的复杂度吗？（可扩展 / 可测试 / 可读）
   └─ 不能 → 是"为模式而模式"
④ 模式带来的间接层（类数量、抽象）值得吗？
   └─ 不值的标志：接口比实现还绕
```

> **一条铁律**：**模式是重构的目标，不是编码的起点**。正确流程是——先写出能跑的直白代码（哪怕 `if/elif`），等它真的出现"第二处重复/第三次变化"时，再重构成模式。**先具体、后抽象**（7.3.4 已强调"从下往上"的抽象）。

### 反模式清单（看到就警惕）

| 反模式 | 症状 | 对策 |
|--------|------|------|
| 为模式而模式 | 接口层比实现还多，没人说清"解决什么" | 删到只剩必要的抽象 |
| Singleton 滥用 | 全局可变状态遍地、测试互相污染 | 模块级 + 显式注入 |
| God Object | 一个类几百行、字段和方法互不相关 | 按 SRP 拆 |
| 功能嫉妒 | 方法大量访问别的对象的内部字段 | 把方法移到被访问者的类里 |
| 继承代替组合 | "想抄几个方法"就 `extends` | 组合 + 委托（7.5.6） |
| 魔法 `__getattr__` 兜底一切 | 拼写错误被静默吞掉 | 兜底方法必须抛 `AttributeError`（7.4.5） |

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 模式本质 | 命名过的设计经验，四要素：名称/问题/方案/后果；不是算法 |
| SOLID | 单一职责 / 开闭 / 里氏替换 / 接口隔离 / 依赖倒置；模式是原则的具体化 |
| 模式会消失 | Python 语言特性替代大量 GoF 模式（生成器、一等函数、鸭子类型、`@dataclass`） |
| 创建型 | 工厂（`@classmethod`/函数）、单例（模块级优先、慎用）、建造者（dataclass 够用）、原型（copy） |
| 结构型 | 适配器（鸭子/委托）、装饰器模式 vs `@decorator`（同名不同物）、代理（property/`__getattr__`）、外观（模块函数） |
| 行为型 | 策略（函数/partial）、模板方法（继承+super）、观察者（回调+WeakSet 防泄漏）、状态（enum+match）、命令（闭包） |
| 使用铁律 | 模式是重构目标不是编码起点；先直白后抽象；为模式而模式是最大反模式 |

---

#### 练习 7 配套

**1.（辨析）** 解释 GoF 装饰器模式与 Python `@decorator` 的三个本质区别，并各自给一个最小例子。

**2.（判断+理由）** 对下列场景，判断"该不该套模式"，说明理由：① 只有一个数据库实现，但用工厂包了一层；② 全项目需要统一配置入口；③ 一个排序函数要在三种比较规则间切换；④ 几十个字段的配置对象。

**3.（动手实现）** 用 `__getattr__` 实现一个通用代理 `class Proxy`：属性访问全部委托给 `_real`，但拦截 `secret` 属性抛 `PermissionError`。说明它同时具备"代理"的哪种用途。

**4.（动手实现）** 把下面这段过程式代码重构成"策略 + 工厂"：

```python
def process(order, kind):
    if kind == "credit":
        print("信用卡支付"); order.status = "paid"
    elif kind == "alipay":
        print("支付宝支付"); order.status = "paid"
    elif kind == "cash":
        print("现金支付"); order.status = "paid"
    else:
        raise ValueError(kind)
```

**5.（解释行为）** 观察者模式里，为什么用强引用列表保存观察者可能造成内存泄漏？`WeakSet` 如何解决？这与 7.7.2 的哪个机制直接相关？

---

**回到第 7 章**：本文件是 7.9 节的完整版，机制层面的所有铺垫（继承、组合、特殊方法、`dataclass`、`enum`）都在 `py-07-oop.md` 的 7.1–7.8 节。读本文件时遇到"这个特性哪来的"，回主文件查。
