# 第7章 面向对象编程

> **学习目标**：建立三个心智模型——"类也是对象"、"方法是绑定的函数"、"封装是约定而非强制"；理解三大底层机制——属性查找链、MRO 线性化、描述符绑定；掌握四大特性（抽象、封装、继承、多态）及其争议；最终能用特殊方法（协议）让自定义类型融入语言语法。

---

面向对象编程（Object-Oriented Programming，OOP）是 Python 中争议最大、也最容易"见名知意"的领域。初学者往往把它当成"语法糖合集"：会写 `class`、会写 `__init__`、会写 `self`，就以为自己懂了 OOP。但真正的 OOP 是**一种思维组织方式**——它解决的是"当程序规模大到一个人无法同时记住所有细节时，如何建模"这个根本问题。

本章不是 API 手册。我们会回答四个"为什么"：

1. **为什么 `class` 也是可执行语句？**（类对象、命名空间、字节码）
2. **为什么方法调用时第一个参数自动传 `self`？**（描述符绑定）
3. **为什么 Python 的"私有"是约定而不是强制？**（封装哲学）
4. **为什么自定义类型能参与 `+`、`for`、`with`？**（特殊方法协议）

本章与前面章节的关系：第 2 章 2.3 节建立了"变量绑定到对象"的引用语义（深浅拷贝专题进一步深化），第 6 章把函数提升为一等公民并讲了命名空间与闭包——**本章把"函数 + 数据"打包成一个单元，就是类的雏形**。第 4 章的运算符重载协议、第 5 章的迭代器协议与真值协议，将在 7.7 节被系统化归入"特殊方法"框架。第 8 章的上下文管理器、第 12 章的描述符与元类，本章会给出必要的预览与衔接。第 10 章会补充"类作为模块的组成单元"。

---

## 7.1 类对象与实例对象：数据与行为的绑定

### 7.1.1 从面向过程到面向对象

**面向过程的世界观**：程序 = 算法 + 数据结构。函数操作数据，数据由函数加工。当程序很小时，这种组织方式清晰直接：

```python
# 面向过程：状态被当作参数传来传去
def deposit(balance, amount):
    return balance + amount

def withdraw(balance, amount):
    if amount > balance:
        raise ValueError("余额不足")
    return balance - amount

balance = 1000
balance = deposit(balance, 500)      # 每次都要手动传递 balance
balance = withdraw(balance, 200)
```

问题出在规模变大之后：账户不仅有余额，还有卡号、利率、交易流水、开户时间……每个函数都得把它们挨个传进去，或者用一个 `dict` 塞下所有字段。字段一旦增加，所有函数签名都要改。**数据与逻辑是分离的，变更会波及全程序。**

**面向对象的世界观**：程序 = 一组互相协作的对象。对象把**状态（数据）**和**操作这些状态的方法（函数）**绑定成一个单元：

```python
# 面向对象：状态被"封装"进对象，方法自动携带状态
class BankAccount:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount          # self 就是"我的账户"

    def withdraw(self, amount):
        if amount > self.balance:
            raise ValueError("余额不足")
        self.balance -= amount

acc = BankAccount("Alice", 1000)
acc.deposit(500)
acc.withdraw(200)
print(acc.balance)                      # 1300
```

注意这个转变的本质：**`self` 取代了显式传参**。`self` 就是那个一直要传来传去的 `balance` 及其同类——现在它被"绑"进了对象。这正是 7.2 节要揭示的：方法的第一个参数不是魔法，而是"把对象自己塞进函数"的显式表达。

> **设计哲学**：Python 是一门**多范式**语言，过程式、函数式、面向对象三种风格并存（这一点在写数据管道时体会最深——往往面向过程的流程 + 函数式的映射 + 少量 OOP 的封装混用）。对比 Java/C++：Java 强制一切代码都在类里（连 `main` 都得包在 `class` 中），而 Python 允许你写裸函数。这不是 Python 的"不纯粹"，而是 Guido 的一贯立场——**语言应提供范式，而不是强制范式**。Python 的 OOP 是你需要时的工具，不是唯一的组织方式。

**四大特性**：经典的 OOP 教学把这门技术概括为四大特性——**抽象（Abstraction）、封装（Encapsulation）、继承（Inheritance）、多态（Polymorphism）**。国内教材常见"三大特性"的说法（封装、继承、多态），把"抽象"排除在外；英文教科书则常称为"四大支柱"（four pillars of OOP）。本章采用四大特性框架，并在 7.3 节专门讨论"抽象作为特性"的争议。四种特性的关系可以这样记忆：**抽象解决"建什么模型"，封装解决"怎么藏细节"，继承解决"类之间怎么复用"，多态解决"同一接口怎么容纳不同实现"**。

### 7.1.2 类语句是可执行语句

**`class` 是一条可执行语句，不是声明**。这一点是理解 Python OOP 所有"奇怪行为"的钥匙。与 C++/Java 的类（编译期声明）不同，Python 的 `class` 语句在运行时执行，每次执行都会**创建一个新的类对象**。

`class` 语句的执行分三步：

1. **解析基类**：求值 `class Name(Base1, Base2):` 中的基类表达式
2. **执行类体**：在**独立的命名空间**中从上到下执行类体内的所有语句
3. **创建类对象**：把类体命名空间打包，用 `type` 构造类对象并绑定到名字 `Name`

看一个反直觉的例子——类体里居然能写 `for` 循环和 `if`：

```python
>>> class Matrix:
...     rows = []                    # 类体是一条条语句，逐行执行
...     for i in range(3):
...         rows.append([0] * 3)     # 类体里可以写循环！
...     if len(rows) > 0:
...         title = "matrix"         # 类体里可以写条件！
>>> Matrix.rows
[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
>>> Matrix.title
'matrix'
```

类体内定义的函数、变量、甚至 `if`/`for` 的结果，都会进入类的命名空间。这就是为什么"类变量"其实只是"放在类命名空间里的变量"——没有任何特殊魔法。

**字节码：`class` 语句如何编译？** 用一个工厂函数包装，用 `dis` 看清全过程：

```python
>>> import dis
>>> def make():
...     class Foo:
...         x = 1
...     return Foo
>>> dis.dis(make)
  2           0 RESUME                   0
  3           2 LOAD_BUILD_CLASS                  # 压入内建 __build_class__（构造类的函数）
             4 LOAD_CONST               1 (<code object Foo at 0x..., file "<stdin>", line 3>)
             6 LOAD_CONST               2 ('Foo')
             8 MAKE_FUNCTION            0         # 把类体代码对象包装成函数
            10 LOAD_CONST               2 ('Foo')
            12 CALL                     2         # __build_class__(类体函数, 'Foo')
  4          18 STORE_FAST               0 (Foo)  # 把类对象绑定到名字 Foo
             20 LOAD_FAST                0 (Foo)
             22 RETURN_VALUE
```

`LOAD_BUILD_CLASS` 压入一个函数，等价于 `__build_class__`，它接收三个参数：一个"类体函数"（由 `MAKE_FUNCTION` 创建）、类名、以及基类元组。`__build_class__` 内部会：执行类体函数得到命名空间 → 用元类构造类对象。字节码揭示了核心事实：**类体被编译成一个独立的代码对象，像函数一样被调用**——这正是"类体拥有独立命名空间"的底层原因。

> **版本注意**：Python 3.8–3.10 中 `CALL 2` 写作 `CALL_FUNCTION 2`，Python 3.11 起改为 `CALL`；3.12 起 `LOAD_BUILD_CLASS` 与 `MAKE_FUNCTION` 之间还会出现 `PRECALL`。字节码细节随版本演进，但"`class` 可执行、类体有独立命名空间"这一结论在所有 Python 3 版本中一致。

**每次执行 `class` 都会新建类**——所以把 `class` 放进函数、放进循环，每次调用都会得到不同的类对象：

```python
>>> def build(kind):
...     class Animal:
...         species = kind
...     return Animal
>>> A = build("dog")
>>> B = build("cat")
>>> A is B        # False——两次执行产生两个不同的类对象
False
>>> A.species
'dog'
>>> B.species
'cat'
```

> **工程影响**：这个特性支撑了"动态创建类"的高级用法（`type` 直接构造、工厂函数返回类、`dataclass` 内部机制，详见 7.8.1）。也提醒我们：**不要用 `is` 比较运行时动态生成的类**，除非能确认是同一个对象。

### 7.1.3 类对象与实例对象的本质

第 2 章说过"一切皆对象"。那"类"本身是什么对象？

- **类对象**是 **`type` 的实例**（它的类型是 `type`）
- **实例对象**是**类**的实例

```python
>>> class Dog: ...
>>> d = Dog()
>>> type(d)          # 实例的类型是类
<class '__main__.Dog'>
>>> type(Dog)        # 类的类型是 type
<class 'type'>
>>> type(type)       # type 的类型是自己——"元类之环"
<class 'type'>
```

三者的关系可画成：

```
type  ——"类之父"——> Dog（类对象）——"实例之母"——> d（实例对象）
  │                                                        │
  └──────────── 元类（type 的实例） ←──────────────────────┘
                     （Dog 是 type 的实例，d 是 Dog 的实例）
```

`type` 是"元类"（metaclass）——制造类的类。默认所有类都是 `type` 的实例（第 12 章会讲自定义元类）。`isinstance` 与 `type` 的差异在这里变得清晰：

```python
>>> class Animal: ...
>>> class Dog(Animal): ...
>>> d = Dog()
>>> type(d) is Dog           # type 只认"直接类型"
True
>>> type(d) is Animal        # ❌ 错误观念：type 不沿继承链看
False
>>> isinstance(d, Dog)       # isinstance 沿继承链看
True
>>> isinstance(d, Animal)    # d 是 Animal 的子类实例
True
```

**实例对象里装了什么？** 一个实例在 CPython 里本质是：`__dict__`（存放实例属性）+ `__class__`（指向它的类）。用 `dir()` 和 `__dict__` 验证：

```python
>>> class Dog:
...     def __init__(self, name):
...         self.name = name
>>> d = Dog("旺财")
>>> d.__dict__               # 实例自己的属性都在这里
{'name': '旺财'}
>>> d.__class__ is Dog       # 实例知道自己属于哪个类
True
```

`__dict__` 就是一个普通字典——这意味着实例属性的存取在底层就是字典的键值操作。这也解释了 7.1.4 的"类变量 vs 实例变量"以及 7.1.6 的"动态加属性"为什么毫无障碍：**给对象加属性 = 往它的字典里放一个键**。

**实例创建流程：`__new__` → `__init__`。** `Dog("旺财")` 这句调用背后是 `type.__call__` 依次做两件事：

1. `Dog.__new__(Dog, "旺财")` —— 分配裸内存，返回一个**空实例**（默认 `object.__new__`）
2. `Dog.__init__(实例, "旺财")` —— 初始化实例属性，返回 `None`

```python
>>> class Probe:
...     def __new__(cls, name):
...         print(f"__new__: 分配 {cls.__name__} 的空实例")
...         return object.__new__(cls)      # 必须调用父类 __new__ 才拿到实例
...     def __init__(self, name):
...         print(f"__init__: 初始化 {name}")
...         self.name = name
>>> p = Probe("probe")       # 先 __new__ 后 __init__
__new__: 分配 Probe 的空实例
__init__: 初始化 probe
```

> **⚠️ 陷阱**：`__init__` 的返回值必须是 `None`。若显式返回其他值，Python 会抛 `TypeError`。而 `__new__` 的返回值是**实例本身**——若 `__new__` 返回了别的类型的对象，`__init__` 甚至不会被调用。这两个方法的分工是"分配"与"初始化"，多数情况你只需要写 `__init__`。

> **实战建议**：绝大多数类只需 `__init__`。需要覆盖 `__new__` 的典型场景是**不可变类型**（如 `tuple`/`str` 子类，必须在分配时确定内容）和**单例**。`__new__` 将在第 12 章元编程中深入。

### 7.1.4 类变量与实例变量

类体里的赋值语句创建**类变量**（也叫类属性），`__init__` 里通过 `self.xxx = ...` 创建**实例变量**（实例属性）。两者的根本区别在**存放位置**：

```python
>>> class Counter:
...     count = 0                 # 类变量：存在类的命名空间（Counter.__dict__）
...     def __init__(self, name):
...         self.name = name      # 实例变量：存在实例的命名空间（self.__dict__）
>>> Counter.__dict__
mappingproxy({'__module__': '__main__', 'count': 0, '__init__': <function ...>, ...})
>>> c1, c2 = Counter("a"), Counter("b")
>>> c1.__dict__, c2.__dict__
({'name': 'a'}, {'name': 'b'})
```

**类变量被所有实例共享**，**实例变量每个实例独立**。用 `id()` 直接看内存位置：

```python
>>> c1.count is c2.count          # 读类变量：两个实例找到的是同一个对象
True
>>> id(Counter.count), id(c1.count), id(c2.count)
(140472619200496, 140472619200496, 140472619200496)   # 三个 id 完全相同
```

那么"修改类变量"会发生什么？关键在**赋值是重新绑定，不是修改**：

```python
>>> c1.count += 1                 # 等价于 c1.count = c1.count + 1
>>> c1.count                      # c1 自己新建了一个实例变量
1
>>> c2.count                      # c2 看到的仍是类变量
0
>>> Counter.count                 # 类变量没被动过
0
```

`c1.count += 1` 的流程：读取 `c1.count`（沿查找链拿到类变量 0）→ 加 1 → **把结果赋值给 `c1`**（在 `c1.__dict__` 里新建键 `count`）。从此 `c1` 的 `count` 就是它自己的了，类变量被"遮蔽"。

> **⚠️ 陷阱——可变类变量**：这是 OOP 新手最经典、最隐蔽的 bug。当类变量是**可变对象**（list、dict、set）时，就地修改会**穿透共享**：

```python
>>> class Employee:
...     skills = []               # ❌ 可变类变量：所有实例共享同一个 list
...     def __init__(self, name):
...         self.name = name
...     def add_skill(self, s):
...         self.skills.append(s) # 就地修改 → 改的是共享的那一份
>>> a, b = Employee("甲"), Employee("乙")
>>> a.add_skill("Python")
>>> b.skills                     # 乙莫名其妙学会了 Python！
['Python']
```

```python
>>> class Employee:
...     def __init__(self, name):
...         self.name = name
...         self.skills = []      # ✅ 可变对象放实例变量，每个实例独立
...     def add_skill(self, s):
...         self.skills.append(s)
>>> a, b = Employee("甲"), Employee("乙")
>>> a.add_skill("Python")
>>> b.skills                     # 乙干净如初
[]
```

> **记忆口诀**：**不可变对象当类变量（常量、计数器、枚举表）安全；可变对象一律放实例变量**。若确实需要"所有实例共享一份可变状态"，务必明确这是有意设计（如连接池、全局配置表），并在 docstring 中注明。

### 7.1.5 属性查找链

访问 `obj.attr` 时，Python 按什么顺序找？本质是**先找实例自己的字典，再沿类向上找**：

```
obj.attr
  ① obj.__dict__          ← 实例自己的属性（7.1.4 的实例变量）
  ② type(obj).__dict__    ← 类的属性（类变量、方法）
  ③ 基类链（MRO）         ← 依次向上找（7.5 节深讲 MRO）
```

```python
>>> class Animal:
...     kingdom = "animal"
...     def speak(self): ...
>>> class Dog(Animal):
...     def __init__(self, name):
...         self.name = name
>>> d = Dog("旺财")
>>> d.name         # ① 实例字典里有 → 直接命中
'旺财'
>>> d.kingdom      # ① 没有 → ② 类里找到 → "animal"
'animal'
>>> d.speak        # ① 没有 → ② 类里找到（方法也是类属性）→ 绑定方法
<bound method Dog.speak of <__main__.Dog object at 0x...>>
>>> d.legs         # ①②③ 都没有 → AttributeError
Traceback (most recent call last):
  ...
AttributeError: 'Dog' object has no attribute 'legs'
```

注意**方法也在查找链上**——方法只是存放在类命名空间里的函数对象（这正是 7.2 的起点）。

**一个重要对称性：赋值不沿查找链走。** `obj.attr = value` 永远只做一件事：写进 `obj.__dict__`。它不会去检查类里是否已有同名属性，也不会"修改类的属性"：

```python
>>> d.kingdom = "mammal"      # 赋值：在 d.__dict__ 新建键，遮蔽类变量
>>> d.kingdom                 # 实例视角
'mammal'
>>> Dog.kingdom               # 类视角——类变量毫发无损
'animal'
>>> d.__dict__                # 实例字典里多了 kingdom
{'name': '旺财', 'kingdom': 'mammal'}
```

这个"**读走查找链、写不走查找链**"的不对称，是理解 OOP 一切"遮蔽/共享"现象的基石。它也引出两个高级钩子的预览：`__getattr__`（查找链全部失败时才调用）与 `__getattribute__`（拦截一切属性读取）——详见 7.4.4。

> **⚠️ 陷阱**：`hasattr(obj, "attr")` 会**吞掉**属性访问抛出的 `AttributeError` 并返回 `False`。如果属性 getter 内部本身抛了 `AttributeError`，`hasattr` 会误判为"没有该属性"。调试诡异行为时，先用 `getattr(obj, "attr", None)` 或直接访问看真实异常。

### 7.1.6 动态定义变量与属性

因为实例属性就是"字典里的键"，所以 Python 允许**在运行时给实例或类动态添加属性**——这在静态语言里是不可能的事。

```python
>>> class Dog: ...
>>> d = Dog()
>>> d.name = "旺财"            # 运行中给实例加属性
>>> d.color = "black"          # 再加一个
>>> d.__dict__
{'name': '旺财', 'color': 'black'}
```

动态加属性有两种形式：**实例级**（只影响这一个实例）与**类级**（影响所有实例，包括已创建的）：

```python
>>> Dog.species = "canine"     # 类级：给类加类变量
>>> d.species                  # 已有实例立刻能读（沿查找链）
'canine'
>>> d2 = Dog()
>>> d2.species                 # 新实例也能读
'canine'
```

三个内置函数提供程序化访问：`getattr(obj, name, default)`、`setattr(obj, name, value)`、`delattr(obj, name)`。它们的名字不是简写，而是**属性访问协议的操作入口**（与 `__getattribute__`/`__setattr__`/`__delattr__` 对应，7.4.4 讲）。当属性名是**动态计算出来的**时，只能用它们：

```python
>>> field = "name"
>>> getattr(d, field)          # 动态取属性——等价于 d.name
'旺财'
>>> setattr(d, "age", 3)       # 等价于 d.age = 3
>>> delattr(d, "color")        # 等价于 del d.color
```

**动态加属性的两种反模式**：

1. **用字典或动态属性代替"设计好的类结构"**——`obj.anything = ...` 看似方便，实则放弃了类型契约、拼写检查（`obj.naem` 不会报错，只是新键）、IDE 提示。一旦属性是"业务字段"，就该写进 `__init__`。
2. **类型未声明就访问**——`d.legs` 直接 `AttributeError`；动态属性让"缺少初始化"从编译期错误（静态语言）退化成运行时错误。

**`__slots__` 预告**：如果想让类**拒绝**动态加属性（同时节省内存），可以用 `__slots__` 声明"允许的属性白名单"：

```python
>>> class Point:
...     __slots__ = ("x", "y")     # 只允许这两个属性
...     def __init__(self, x, y):
...         self.x, self.y = x, y
>>> p = Point(1, 2)
>>> p.z = 3                        # ❌ 超出白名单 → 报错
Traceback (most recent call last):
  ...
AttributeError: 'Point' object has no attribute 'z'
```

`__slots__` 移除了实例的 `__dict__`，属性改为**固定槽位**（类似 C 结构体字段），既省内存又提速。代价是不能动态加属性、且与某些依赖 `__dict__` 的工具不兼容。完整权衡见 7.8.3。

> **实战建议**：动态属性适合三类场景——（1）数据来自外部、字段名运行时才知道（如解析 JSON 后映射成对象）；（2）装饰器/框架注入（如 ORM 的查询代理）；（3）原型快速迭代。**生产代码的业务对象请老老实实写 `__init__` + `__slots__`/`dataclass`（7.8.1），把动态性留给框架层**。

---

## 7.2 方法三兄弟：实例方法、类方法、静态方法

### 7.2.1 方法的本质：函数 + 绑定

在第 6 章我们把函数提升为一等公民。方法（method）是什么？**方法 = 定义在类命名空间里的普通函数 + 一层绑定机制**。没有魔法，只有查找链（7.1.5）与描述符协议（7.2.6）的组合。

看一个关键差异——通过类访问 vs 通过实例访问同一个函数：

```python
>>> class Greeter:
...     def hello(self, name):
...         return f"Hello, {name}!"
>>> Greeter.hello          # 通过类访问：它就是普通函数
<function Greeter.hello at 0x...>
>>> g = Greeter()
>>> g.hello                # 通过实例访问：变成"绑定方法"
<bound method Greeter.hello of <__main__.Greeter object at 0x...>>
```

两者的类型与调用方式都不同：

```python
>>> type(Greeter.hello)    # 函数
<class 'function'>
>>> type(g.hello)          # 绑定方法
<class 'method'>
>>> Greeter.hello(g, "World")   # 函数需要显式传第一个参数
'Hello, World!'
>>> g.hello("World")            # 绑定方法自动带上 g
'Hello, World!'
```

绑定方法内部保存着"函数"和"绑定对象"两个成分，可以用 `__func__` 和 `__self__` 访问：

```python
>>> g.hello.__func__ is Greeter.hello   # 同一个底层函数
True
>>> g.hello.__self__ is g               # 绑定到了哪个实例
True
```

这个拆解说明：**"方法调用"`g.hello(...)` 与"函数调用"`Greeter.hello(g, ...)` 在语义上完全等价**。`g.hello` 只是个"记住了第一个参数是 `g`"的函数。理解这一点，7.2.2 的 `self` 就不再神秘。

**字节码：`LOAD_METHOD` 的优化。** Python 3.7+ 对"实例取方法"有专门字节码：

```python
>>> import dis
>>> def call(g):
...     return g.hello("World")
>>> dis.dis(call)
  2           0 RESUME                   0
              2 LOAD_FAST                0 (g)
              4 LOAD_METHOD              1 (hello)    # 取绑定方法（有专用指令）
             10 CALL                     1
             18 RETURN_VALUE
```

`LOAD_METHOD` 会尝试做**免绑定优化**：如果能确认方法不需绑定（或调用就是 `self.method()`），CPython 可以绕过创建 `method` 对象、直接用 `self.method(函数, 实例, ...)` 三元组调用，省一次分配。这是纯内部优化，语义与普通属性访问完全一致。

> **版本注意**：`LOAD_METHOD` 与 `LOAD_ATTR` 的取舍在 Python 3.11 的 JIT 内联缓存（inline caching）中被进一步优化——CPython 会给每个 `LOAD_METHOD` 指令记住"上次命中的类型"，下次直接走快捷路径。这也是 Python 3.11 性能大幅提升的来源之一。

### 7.2.2 实例方法（对象方法）与 `self`

**`self` 不是关键字，只是第一个参数的约定名**。你甚至可以写成 `this`、`me`、`_`：

```python
>>> class Odd:
...     def greet(this, name):        # 名字随意，约定叫 self
...         return f"Hi {name}"
>>> Odd().greet("x")
'Hi x'
```

但**参数个数是固定的**：实例方法的第一个位置参数永远接收"实例本身"。调用 `obj.method(a, b)` 时，实际传入的是 `(obj, a, b)`。

**为什么 Python 要显式写 `self`？** 这是 Guido 深思熟虑的设计，与 C++/Java 的隐式 `this` 形成鲜明对比：

- **显式优于隐式**（PEP 20）：`self.x = x` 明确表达了"写进当前实例"；隐式 `this` 则把对象引用藏在语法里。
- **函数与方法共用一套函数对象**：因为 `self` 是普通参数，同一个函数既可以被实例绑定（`g.hello("x")`），也可以被当作普通函数调用（`Greeter.hello(g, "x")`）、甚至被赋值给别的类——无需两套机制。
- **装饰器友好**：函数与方法的统一让 `@staticmethod`/`@classmethod` 只是"改绑定的参数"，而非发明新的对象类型。

> **跨语言对比**：Java 的 `this` 是编译器插入的隐式引用；C++ 的 `this` 是指针且不可重新绑定；JavaScript 的 `this` 是**运行时动态绑定**（`obj.method` 被单独取出调用时 `this` 会丢！）。Python 的显式 `self` 从根本上避免了 JS 的 `this` 丢失问题——因为绑定发生在取属性那一刻，而不是调用时猜。

**调用实例方法的完整路径**（串联 7.1.5 与 7.2.1）：

```
g.hello("World")
  ├─ ① 属性查找：g.hello
  │     ├─ g.__dict__ 没有 → 类里找到函数对象 hello
  │     └─ 触发描述符 __get__ → 返回绑定方法(函数=hello, self=g)
  └─ ② 调用绑定方法(g, "World") → 即 hello(g, "World")
```

### 7.2.3 `@classmethod` 类方法

类方法的第一个参数绑定的是**类**（约定名 `cls`），而不是实例：

```python
>>> class Tool:
...     version = "1.0"
...     @classmethod
...     def describe(cls):
...         return f"Tool version {cls.version}"
>>> Tool.describe()          # 通过类调用
'Tool version 1.0'
>>> Tool().describe()        # 通过实例调用也可以——绑定的仍是类
'Tool version 1.0'
```

实例调用类方法时，`cls` 是**实例所属的类**，而不是"恰好能访问的那个类"。这一点在继承中至关重要：

```python
>>> class Tool:
...     name = "generic"
...     @classmethod
...     def get_name(cls):
...         return cls.name
>>> class Hammer(Tool):
...     name = "hammer"
>>> Hammer.get_name()        # cls 动态绑定到 Hammer
'hammer'
>>> Tool().get_name()        # cls 是 Tool
'generic'
```

**类方法的经典用途：备选构造器（alternative constructor）。** 用类方法创建实例，可以让一个类有多种"入口"，且能正确创建子类实例：

```python
>>> class Date:
...     def __init__(self, year, month, day):
...         self.year, self.month, self.day = year, month, day
...     @classmethod
...     def from_iso(cls, iso: str):            # "从字符串解析"这个入口
...         y, m, d = map(int, iso.split("-"))
...         return cls(y, m, d)                 # 用 cls 而不是 Date——子类也能用
...     def __repr__(self):
...         return f"Date({self.year}, {self.month}, {self.day})"
>>> Date.from_iso("2026-08-11")
Date(2026, 8, 11)
```

注意 `return cls(...)` 而不是 `Date(...)`：标准库中 `datetime.datetime.fromtimestamp`、`dict.fromkeys`、`pathlib.Path.cwd` 都采用这个模式。若写成硬编码的 `Date(...)`，继承后的备选构造器就永远只造父类实例——这是类方法最容易被误解的价值点。

> **实战建议**：判断"该用类方法还是实例方法"：如果方法**不依赖实例状态**（不读 `self.xxx`），但**需要知道"我是哪个类"**（构造同类实例、读类变量、支持子类化），用 `@classmethod`。如果连类都不需要知道，见 7.2.4。

### 7.2.4 `@staticmethod` 静态方法

静态方法不绑定任何东西——既不收 `self` 也不收 `cls`，就是个**放在类命名空间里的普通函数**：

```python
>>> class MathUtil:
...     @staticmethod
...     def clamp(x, lo, hi):
...         return max(lo, min(x, hi))
>>> MathUtil.clamp(15, 0, 10)     # 通过类调用
10
>>> MathUtil().clamp(15, 0, 10)   # 通过实例调用也可——只是"恰好借道"
10
```

静态方法在继承中**不会**动态绑定子类：`Sub.clamp(...)` 拿到的还是定义它的那个函数，没有任何 `cls`。它的价值纯粹是**逻辑分组与命名空间**：把与类强相关的工具函数收进类的命名空间，调用处 `MathUtil.clamp` 比裸函数 `clamp` 更有语义上下文。

**什么时候用静态方法，什么时候用模块级函数？** 这是个真实的工程决策：

| 场景 | 选择 | 理由 |
|------|------|------|
| 函数与某个类强相关，且会随着该类一起被"发现" | `@staticmethod` | 语义归属清晰，`MathUtil.clamp` 自文档化 |
| 函数要被其他模块的类复用 | 模块级函数 | 静态方法不好单独 import，模块级函数更直白 |
| 函数依赖其他同类函数 | 模块级函数 | 静态方法无法调用"类里的其他静态方法"（没有类引用） |

> **反模式提醒**：把静态方法当成"为了不用 import 而塞进类的函数"是常见坏味道。如果模块内已有同功能的裸函数，静态方法只是多一层间接。`functools` 标准库的实践值得参考——`functools.reduce` 就是普通模块函数，而不是某个类的静态方法。

### 7.2.5 三种方法的选择决策矩阵

| 特性 | 实例方法 | `@classmethod` | `@staticmethod` |
|------|---------|----------------|-----------------|
| 第一个参数 | `self`（实例） | `cls`（类） | 无 |
| 能否读实例状态（`self.xxx`） | ✅ | ❌ | ❌ |
| 能否读类状态（`cls.xxx`） | ✅（经 `type(self)`） | ✅ | ❌ |
| 继承时是否随子类绑定 | ✅ | ✅（cls 为子类） | ❌ |
| 典型用途 | 业务行为、操作对象状态 | 备选构造器、类级工厂、读类常量 | 工具函数、逻辑分组 |
| 能否被实例调用 | ✅ | ✅ | ✅ |

三个要点：

1. **能用普通方法解决时，优先普通方法**。`classmethod`/`staticmethod` 是"降级"工具——当方法不需要实例状态时才考虑。
2. **`@classmethod` 能做的，`@staticmethod` 不一定能做**；反之 `@staticmethod` 是最弱绑定。
3. 方法自身也是"类属性"，因此也有 7.1.5 的查找链与遮蔽规则——子类可以**覆盖**任何一类方法（包括把实例方法覆盖成静态方法），Python 不做强制。

```python
>>> class Base:
...     def f(self):
...         return "instance"
...     @classmethod
...     def g(cls):
...         return "class"
>>> class Sub(Base):
...     f = staticmethod(lambda: "now static")   # 覆盖：实例方法 → 静态方法
...     g = "now a string"                        # 覆盖：类方法 → 类变量
>>> Sub().f()
'now static'
>>> Sub.g
'now a string'
```

这种"想怎么换怎么换"的灵活正是动态语言 OOP 的特质——既是优势（自由），也是约束（没有编译期保护，全靠自觉）。

### 7.2.6 绑定机制的底层：描述符协议 `__get__` 预览

现在揭穿 7.2.1 的"绑定"到底怎么发生。答案藏在**描述符协议**里：当一个类属性实现了 `__get__` 方法，它就被称为描述符，访问该属性时 `__get__` 会被调用。**函数对象恰好实现了 `__get__`**——这就是"绑定方法"的来源。

```python
>>> class Function:                 # 复刻函数对象的绑定行为的最小描述符
...     def __init__(self, fn):
...         self.fn = fn
...     def __get__(self, instance, owner):
...         if instance is None:
...             return self.fn                       # 类访问 → 返回原函数
...         from types import MethodType
...         return MethodType(self.fn, instance)    # 实例访问 → 返回绑定方法
>>> class Demo:
...     hello = Function(lambda self: "hi")         # 用一个描述符当属性
>>> Demo.hello          # 类访问 → 原函数
<function <lambda> at 0x...>
>>> Demo().hello        # 实例访问 → 绑定方法
<bound method ... of <__main__.Demo object at 0x...>>
```

这就是 `g.hello` 变出 `bound method` 的全部秘密：**属性访问发现 `hello` 是描述符 → 调用 `__get__(g, type(g))` → 返回"函数 + 绑定对象"的复合体**。

描述符协议共三个钩子（第 12 章深入）：

- `__get__(self, instance, owner)` —— 读取属性时调用（`instance` 为 `None` 表示类访问）
- `__set__(self, instance, value)` —— 赋值时调用
- `__delete__(self, instance)` —— 删除时调用

只有 `__get__` 的称为**非数据描述符**（如函数、`staticmethod`），`__get__`+`__set__` 的称为**数据描述符**（如 `property`，7.4.3）。两者在属性查找链上的**优先级不同**：数据描述符优先于实例字典，非数据描述符被实例字典覆盖。这解释了为什么 `obj.f` 这样的方法可以被实例属性遮蔽，而 `obj.x`（若 `x` 是 property）不行——细节在 7.4.3 揭晓。

> **本章的伏笔**：描述符是 Python OOP 的"隐藏引擎"——`property`（7.4.3）、`classmethod`/`staticmethod`（本节的装饰器）、甚至 `dataclass`（7.8.1）底层都是描述符在干活。第 12 章会给你全套。

---

## 7.3 抽象（Abstraction）：四大特性中争议最大的一个

> **开宗明义**：本章采用**四大特性**框架（抽象、封装、继承、多态）。国内教材常见的"三大特性"说法把抽象排除在外，英文教科书则常称"四大支柱"（four pillars of OOP）。本节先把抽象的实质讲透，再在 7.3.3 专门讨论"抽象是否配得上一个特性名额"的争议。

### 7.3.1 什么是抽象：从问题域到模型域

**抽象（abstraction）是"从一大堆具体事实中提取出本质、舍弃非本质细节"的认知过程。** 它不是编程独有的概念——人类语言本身就是抽象（"鸟"这个字概括了几万种会飞的、不会飞的、能下蛋的动物）。编程中的抽象，是把**问题域**（现实中的业务、数据、流程）映射为**模型域**（类、函数、数据结构）的过程。

抽象分为两种，恰好对应 Python 的两个语法设施：

**过程抽象（procedural abstraction）：把"怎么做"藏进函数，调用者只关心"做什么"。**

```python
def send_email(to, subject, body):
    smtp = connect_smtp(...)        # 建立连接
    msg = build_message(...)        # 组装协议头
    smtp.send(...)                  # 发送
    smtp.quit()                     # 断开
```

调用者写 `send_email(...)` 时不需要知道 SMTP 握手、MIME 编码的细节——**函数签名就是抽象出的"接口"**。`def` 是过程抽象的语法化（第 6 章已充分展开）。

**数据抽象（data abstraction）：把"内部表示"藏进类型，外部只能通过约定的操作访问数据。**

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius            # 内部表示：摄氏温度

    @property
    def celsius(self):
        return self._celsius

    @property
    def fahrenheit(self):                  # 对外暴露的"视角"（7.4.3 详解 property）
        return self._celsius * 9 / 5 + 32

    @classmethod
    def from_fahrenheit(cls, f):           # 备选构造器：另一种"入口"
        return cls((f - 32) * 5 / 9)
```

外部使用 `Temperature` 时只跟"摄氏/华氏"两个概念打交道，完全不关心内部存的是 `float` 还是 `Decimal`、单位换算怎么算。**`class` 是数据抽象的语法化**——这也是为什么"类"这个词被命名为 `class`：它源自哲学里的"共相"（柏拉图把万物归类为理念），最终在数学集合论里成为"具有共同特征的成员的集合"，再被编程语言借来指代"具有共同数据与行为的对象模板"。

> **设计哲学**：面向过程的语言（C）只有过程抽象（函数），数据要靠 `struct` 裸露在外，谁都能直接改内部字段。面向对象的语言把"数据 + 操作数据的过程"捆成一个单元（类），抽象的对象从"函数"升级为"类型"。Python 两种抽象都有——`def` 管过程，`class` 管数据。写任何类之前先问一句：**这个类要对外隐藏什么内部表示？对外暴露什么稳定接口？** 这个问题就是"做抽象"。

### 7.3.2 抽象与另外三大特性的关系

四大特性不是四个并列的孤岛。**抽象是其余三个的"地基"**，后三者都是建立在"先抽象出了类"这个前提之上的：

```
        抽象（建模：把问题域变成类与接口）
                │
    ┌───────────┼───────────────┐
    ▼           ▼               ▼
   封装        继承              多态
（隐藏类的  （类之间按抽象    （对同一个抽象
 内部细节）   层级复用）        接口给出不同实现）
```

- **抽象 → 封装**：先抽象出"类暴露什么接口、隐藏什么内部"，才有"隐藏"可言。封装（7.4）就是抽象在"实现侧"的执行——抽象定接口，封装守实现。
- **抽象 → 继承**：先抽象出"基类的公共本质"，才谈得上"子类在基类基础上扩展"。继承（7.5）是抽象在"层级"上的复用——把多个类的共性再次抽象成父类。
- **抽象 → 多态**：先抽象出"统一的接口约定"（如"会叫"），多态（7.6）才让不同实现（狗叫、猫叫）都能填进同一个接口。多态是抽象在"调用侧"的兑现。

**一句话**：抽象定义"是什么"，封装决定"藏什么"，继承决定"怎么复用"，多态决定"怎么替换"。

### 7.3.3 对"抽象作为特性"的质询：三大特性 vs 四大特性

**争议背景**。为什么会产生"三大"与"四大"两套口径？

- **"三大特性"**（封装、继承、多态）：国内教材主流说法，历史可追溯到早期 OOP 教学对 C++ 的概括。它的逻辑是"三大特性是可被语言机制直接验证的行为"——你能看到 `private`、能看到继承语法、能看到虚函数，但"抽象"没有对应的单一语法构造。
- **"四大特性"**：源自英文教科书的 *four pillars of OOP*（四大支柱），在抽象之外显式加上 Abstraction，因为它强调 OOP"以建模为中心"的本质。
- 也有教材讲"三大特性 + 一种设计原则"，把抽象降级为贯穿始终的原则而非并列特性。

**对抽象的质询**主要有三条，各有道理：

**质询 1：抽象不是 OOP 独有的。** 过程式编程有函数抽象，函数式编程有高阶函数与数据流抽象，模块系统有模块抽象。如果"抽象"是所有编程范式的共性，凭什么它是"OOP 的特性"？——这条质询认为抽象是**所有程序设计的普遍原理**，不该被划归 OOP 专有。支持方反驳：OOP 里的"数据抽象 + 封装"组合（抽象出类型并隐藏其表示）是 OOP 相对过程式最本质的增量，把这个增量命名为抽象是合理的。

**质询 2：抽象与封装高度重叠。** "隐藏细节"这句话既是抽象的定义也是封装的定义。有人据此认为：把抽象与封装并列会重复计数。辨析方法：抽象偏重**建模选择**（决定"对外可见什么"），封装偏重**实现约束**（保证"内部不被误用"）。抽象是设计期概念，封装是实现期概念——两者虽孪生，但层面不同。

**质询 3（最有力）：抽象与其他三者不在同一层级。** 这是"范畴错误"（category error）论证：封装、继承、多态都是**作用在已经抽象好的类之上**的操作；而抽象是**生成类的过程**——没有抽象就没有类，也就谈不上后三者。把"前提"与"被前提支撑的结果"并列，逻辑上不齐整。这也是"三大特性"说法在学术上的主要辩护：封装/继承/多态是对"类"的三类操作，抽象则是对"问题域"的操作，二者维度不同。

**工程界的实际态度**。面对争议，工程实践给出的答案很务实：**争论"抽象算不算特性"不如争论"抽象在 Python 里如何落地"**。因为无论教材怎么写，OOP 的第一件事永远是"把这个需求域抽象成哪些类型"——这一步做不好，封装/继承/多态都是无本之木。所以：

> **提醒（写代码 & 面试答题时）**："三大特性"与"四大特性"都有出处，不是谁对谁错。**答题/写作时建议口径**：先答"教材常见三大特性：封装、继承、多态"，再补充"更完整的表述是四大特性，加上抽象——抽象是另外三者共同的前提，因此也有人把它视为贯穿的设计原则而非并列特性"。这样两种口径都覆盖到，也显示你理解争议本身。**写代码时**：把抽象当作"第一步的建模动作"来对待——先定义清楚类型与接口，再谈封装与继承。

**Python 语境下的特殊回应**：在其他语言里"抽象"有显式语法支撑（C++/Java 的 `abstract class`、接口 `interface`），而 **Python 没有 `abstract` 关键字**（`abc.ABC` 只是标准库，不是语法）。Python 的抽象落地方式恰恰是它最独特的：**协议（特殊方法）+ 鸭子类型**。这反而让"抽象是不是特性"在 Python 里有了更本质的回答——见 7.3.4。

### 7.3.4 Python 中抽象的落地：接口、协议与鸭子类型

**Python 不强制抽象，但给了三套"抽象工具"，按约束强度递增：**

| 工具 | 约束强度 | 用途 | 位置 |
|------|---------|------|------|
| 鸭子类型（Duck Typing） | 无约束（运行时按行为判断） | 快速组合，灵活至上 | 7.6.2 |
| 抽象基类 `abc.ABC` | 强制（未实现抽象方法则不能实例化） | 显式契约、统一接口 | 7.6.3 |
| `typing.Protocol` | 静态层面约束（类型检查器），运行时仍靠鸭子 | 结构化子类型 | 7.6.4 |

三条路都指向同一件事：**把"应该长什么样"的约定抽象出来，让不同的具体实现能互相替换。** 这就是多态（7.6）的前提——抽象先定义接口，多态再填充实现。

**一个贯穿三章的实战例子**——抽象一个"可持久化"的接口，让不同数据源可替换：

```python
# 抽象层：定义"支持持久化的东西长什么样"（协议）
class Persistable:                       # 纯抽象：只声明方法，没有实现
    def save(self, path): ...
    def load(self, path): ...

# 具体实现 1
class User:
    def save(self, path):
        with open(path, "w") as f:
            f.write(self.name)
    def load(self, path):
        with open(path) as f:
            self.name = f.read()

# 具体实现 2：完全不同的存储方式，同样满足抽象
class Config:
    def __init__(self):
        self.data = {}
    def save(self, path):
        # 存成 JSON ...
        pass
    def load(self, path):
        # 读 JSON ...
        pass

def backup(obj, path):                   # 面向"抽象接口"编程，不面向具体类
    """任意实现了 save/load 的对象都能备份——这就是抽象的价值。"""
    obj.save(path)
```

`backup` 函数只依赖"`obj` 有 `save` 和 `load`"这个抽象约定，不依赖 `User` 还是 `Config`。新增第三种存储实现时，`backup` 一行不用改。**这就是抽象在 Python 里最朴素的形态**——接口不靠关键字声明，靠"调用它的人约定它存在"。

> **实战建议**：抽象的正确姿势是"从下往上"——先让两个真实类都能工作，发现共性后**再**抽象出接口/父类/协议（第 12 章将强调这种"以具体为先"的演进式设计）。为抽象而抽象（一上来就设计一堆永不实现的接口层）是过度设计的主要来源。

---

## 7.4 封装：接口与实现的隔离

### 7.4.1 封装的本质与 Python 的哲学

**封装（encapsulation）有两个层面**：

1. **打包（bundling）**：把数据与操作数据的方法放进同一个单元（类）——这是 7.1 已经做的事
2. **信息隐藏（information hiding）**：对外只暴露稳定接口，把内部实现细节藏起来——本节的焦点

信息隐藏的价值很实际：**内部实现可以随便改，只要接口不变，外部调用方就不用跟着变**。这是大规模协作与长期维护的基石——想象一个库：如果它内部字段全部裸露，作者每次重构都可能"打碎"用户代码；有封装，作者可以在不破坏接口的前提下优化实现。

**但 Python 的封装哲学与 Java/C++ 有根本不同**：

```java
// Java：private 是编译器强制——写错就编译不过
public class BankAccount {
    private double balance;          // 外部物理上访问不到
    public void deposit(double n) { this.balance += n; }
}
```

```python
# Python：没有 private 关键字，一切靠约定
class BankAccount:
    def __init__(self, balance=0):
        self._balance = balance      # 单下划线：约定的"内部"（不强制）

    def deposit(self, n):
        self._balance += n
```

Python 社区的一句名言概括了它的立场：**"我们都是成年人"（We are all consenting adults）**。语言信任你不会去乱摸内部属性，同时也承认：**真正的封装是文档、命名与纪律，而不是编译器的锁**。Guido 在邮件列表中的立场很明确——强制私有违反 Python 的透明哲学，也会阻碍调试与测试（测试恰恰经常需要查看内部状态）。

> **跨语言对比**：

| 语言 | 私有机制 | 强度 | 说明 |
|------|---------|------|------|
| Java/C++/C# | `private`/`protected` 关键字 | 编译期强制 | 违反即编译失败 |
| Python | `_x` 约定 + `__x` 名称改写 | 约定（运行时无锁） | 违反不报错，靠自觉 |
| JavaScript | `#x`（ES2022）+ `_x` 约定 | 半强制 | `#x` 运行时私有，`_x` 靠约定 |

> **注意**："Python 没有私有"≠"Python 不做封装"。封装在 Python 里是**设计纪律**——用单下划线标记内部、用 `property` 控制访问、用文档写明公共 API。纪律的执行者是代码审查和 linter（如 `ruff` 的私有成员规则），而不是语言。

### 7.4.2 单下划线 `_x` 与双下划线 `__x`：两种约定，别混淆

**`_x`（单下划线前缀）：纯约定，表示"内部实现，请勿外部使用"。** 它**完全不影响行为**——`obj._x` 照样能访问。它的实际效力有三处：

1. **文档语义**：告诉读者"这是实现细节，不在公共 API 承诺范围内"
2. **`from module import *` 的排除**：默认不导入以单下划线开头的名字（详见第 10 章）
3. **IDE/linter 提示**：多数 IDE 会对"外部访问单下划线成员"给出风格警告

```python
>>> class A:
...     def __init__(self):
...         self._secret = 42
>>> a = A()
>>> a._secret          # 能访问——约定没有锁
42
```

**`__x`（双下划线前缀）：触发名称改写（name mangling）。** 在**类体内**出现的 `__x` 会被自动改写成 `_ClassName__x`：

```python
>>> class A:
...     def __init__(self):
...         self.__value = 10           # 类体内写 __value
>>> a = A()
>>> a.__dict__                         # 实际上存成了 _A__value
{'_A__value': 10}
>>> a.__value                          # ❌ 直接访问失败——名字被改了
Traceback (most recent call last):
  ...
AttributeError: 'A' object has no attribute '__value'
>>> a._A__value                        # ✅ 改写后的名字照样能访问
10
```

**名称改写的目的不是"私有"，而是"防止子类意外覆盖"**。看它的经典应用场景：

```python
>>> class Base:
...     def __init__(self):
...         self.__id = "base"        # 改写为 _Base__id
...     def id(self):
...         return self.__id
>>> class Sub(Base):
...     def __init__(self):
...         super().__init__()
...         self.__id = "sub"         # 改写为 _Sub__id——与父类互不干扰！
>>> s = Sub()
>>> s._Base__id, s._Sub__id           # 两个名字各存各的
('base', 'sub')
```

如果不用双下划线而用 `self._id`，子类再定义 `self._id` 就会**覆盖**父类的同一属性，导致父类方法读到的 `_id` 被偷换——双下划线机制正是为消除这类"子类踩父类变量"的意外而生（`_` 前缀约定 + 名称改写 = 防御性隔离）。

> **⚠️ 陷阱 1**：名称改写是**编译期字符串替换**，不是运行时保护。改写只发生在**类体内**书写 `__x` 的地方——在类外 `a.__x = 1` 不会改写，直接存成 `__x`。
> **⚠️ 陷阱 2**：`__x` 不能真正阻止访问（`a._A__value` 照样读），所以**别用它来"加密"内部数据**。要防的是"意外踩踏"，不是"恶意读取"。
> **⚠️ 陷阱 3**：不要在 `__init__` 里同时用 `self.__x` 定义属性、又在子类里用 `self.__x` 定义同名属性来"复用"——两个名字是分开的，你会困惑为什么子类的赋值"不生效"（其实是写了另一个键）。
> **命名风格**：以单下划线结尾 `x_`（避免与关键字冲突，如 `class_`）不是私有标记；以双下划线开头**且结尾** `__x__` 是**特殊方法**（7.7 章的主角），与 `__x` 名称改写无关——`__init__` 不会改写。

### 7.4.3 `property`：让属性读写走"受控通道"

**`property` 把一个属性从"裸字典键"升级为"受控的读写通道"**——它让"读"和"写"都经过我们指定的函数。最经典的用法：**以属性语法访问，内部做计算或校验**。

```python
>>> class Circle:
...     def __init__(self, radius):
...         self._radius = radius          # 私有存储
...     @property
...     def radius(self):
...         """读取：返回内部存储"""
...         return self._radius
...     @radius.setter
...     def radius(self, value):
...         """写入：先校验再存储"""
...         if value <= 0:
...             raise ValueError("半径必须为正")
...         self._radius = value
...     @property
...     def area(self):
...         """计算属性：没有 setter，只读"""
...         return 3.14159 * self._radius ** 2
>>> c = Circle(1)
>>> c.radius              # 属性语法，实际调用 radius 的 getter
1
>>> c.radius = -5         # 触发 setter 校验
Traceback (most recent call last):
  ...
ValueError: 半径必须为正
>>> c.area                # 只读计算属性
3.14159
>>> c.area = 10           # ❌ 没有 setter 的属性不能赋值
Traceback (most recent call last):
  ...
AttributeError: can't set attribute
```

`property` 的三个核心价值：

1. **校验与只读**：setter 里拦非法值；不写 setter 即只读（如上 `area`）。
2. **计算属性**：`area` 不占存储，每次读取现算——对外表现得像普通字段。
3. **接口稳定性（最重要的价值）**：可以先公开普通属性 `self.radius`，等需要校验/计算时再平滑升级为 property，**外部代码一行不用改**：

```python
# 阶段一：公开裸属性（原型期）
class Circle:
    def __init__(self, radius):
        self.radius = radius          # 外部：c.radius = 5

# 阶段二：升级为 property（加校验），外部调用方代码不变
class Circle:
    def __init__(self, radius):
        self._radius = radius
    @property
    def radius(self): return self._radius
    @radius.setter
    def radius(self, v):
        if v <= 0: raise ValueError(...)
        self._radius = v
```

这就是"封装保护演进"的经典演示：**内部从裸字段换成受控字段，公共接口 `c.radius` 纹丝不动**。Java 里做这种事需要 `getRadius()`/`setRadius()` 从第一天就建好 getter/setter 惯例；Python 里你可以先裸奔、需要时再升级。

**`property` 的底层：它就是一个数据描述符。** 回到 7.2.6 的描述符协议——`property` 实现了 `__get__` 与 `__set__`：

```python
>>> class Demo:
...     @property
...     def x(self): return 42
>>> D = Demo
>>> D.x                                  # 类访问 → property 对象本身（描述符实例）
<property object at 0x...>
>>> Demo().x                             # 实例访问 → 触发 __get__ → 42
42
```

字节码验证"属性访问 → 描述符分发"：

```python
>>> import dis
>>> def read(c):
...     return c.radius
>>> dis.dis(read)
  2           0 RESUME                   0
              2 LOAD_FAST                0 (c)
              4 LOAD_ATTR                2 (radius)      # 命中描述符 → 转 __get__
             10 RETURN_VALUE
```

**数据描述符 vs 非数据描述符的优先级**（补全 7.2.6 的伏笔）：

- `property`（数据描述符，有 `__set__`）：**优先于实例字典**——`obj.x = ...` 不会在实例字典里建键，而是走 setter
- 函数（非数据描述符，只有 `__get__`）：**被实例字典覆盖**——`obj.f = lambda...` 能遮蔽方法

验证数据描述符的"截胡"：

```python
>>> class Demo:
...     @property
...     def x(self): return "from property"
...     def __init__(self):
...         self.x = "from instance"     # 有 __set__ → 走 setter，不进实例字典
>>> d = Demo()
>>> d.x                                  # 还是 property 的值！
'from property'
>>> d.__dict__                           # 实例字典里根本没有 x
{}
```

> **实战建议**：不要给每个属性都上 property——那是 Java 迁移者的坏习惯。Python 的最佳实践是"**先裸属性，需要时再升级**"（如上阶段一/二）。只在三处用 property：需要校验、需要计算、需要只读。纯透传的 property（getter 只 `return self._x`）是反模式——它只是给 `_x` 穿了件马甲，毫无封装收益。

### 7.4.4 属性访问协议：`__getattr__`、`__setattr__`、`__getattribute__`

`property` 管的是"某个属性"，而属性访问协议管的是"**所有**属性访问的底层通道"。它们是在查找链（7.1.5）之上挂的四个钩子：

| 钩子 | 触发时机 | 作用 |
|------|---------|------|
| `__getattribute__` | **每次**读取任何属性 | 拦截一切（含 `__dict__`、特殊方法） |
| `__getattr__` | **仅在查找链全部失败后** | 兜底：处理"没有的属性" |
| `__setattr__` | **每次**赋值 | 拦截一切写操作 |
| `__delattr__` | **每次**删除 | 拦截一切删操作 |

**`__getattr__`：只在实际没有这个属性时被调用。** 它是"动态属性"的引擎（7.1.6 的延伸）：

```python
>>> class LazyAttr:
...     def __init__(self):
...         self._data = {}
...     def __getattr__(self, name):
...         # 属性不存在时，尝试从内部字典取——实现"属性即数据"的委托
...         if name in self._data:
...             return self._data[name]
...         raise AttributeError(name)        # 一定要抛，否则掩盖错误
>>> la = LazyAttr()
>>> la._data["greeting"] = "hello"
>>> la.greeting          # 实例/类里都没有 greeting → 走 __getattr__ → 从字典取
'hello'
```

> **⚠️ 陷阱**：`__getattr__` 内部访问 `self._data` 时，如果 `_data` 也恰好不存在，会**再次**进入 `__getattr__` → 无限递归。所以 `__getattr__` 里访问其他属性时务必确保它们真实存在（如用 `self.__dict__` 或 `object.__getattribute__`）。

**`__setattr__`：拦截一切赋值——但极易写出无限递归。** 经典错误：

```python
>>> class Bug:
...     def __init__(self):
...         self.x = 1
...     def __setattr__(self, name, value):
...         self.x = value       # ❌ 这行又触发 __setattr__ → 无限递归 → RecursionError
```

正确写法是用 `object.__setattr__` 绕过钩子：

```python
>>> class Fixed:
...     def __init__(self):
...         object.__setattr__(self, "x", 1)   # ✅ 直接写底层字典
...     def __setattr__(self, name, value):
...         print(f"拦截: {name} = {value}")
...         object.__setattr__(self, name, value)   # 转发给默认实现
>>> f = Fixed()          # 打印 "拦截: x = 1"
拦截: x = 1
>>> f.y = 2              # 打印 "拦截: y = 2"
拦截: y = 2
```

> **⚠️ 陷阱**：Python 特殊方法（7.7）在**类型**上查找，不走实例属性。因此用 `__setattr__` 给实例动态注入 `__repr__`、`__eq__` 等方法**不会生效**——注入特殊方法必须改类（或元类，见第 12 章）。

**`__getattribute__`：连"存在"的属性都能拦截。** 它比 `__getattr__` 更强（也更容易出错），每次属性访问都经过它：

```python
>>> class Guard:
...     def __getattribute__(self, name):
...         if name.startswith("_"):
...             raise AttributeError("拒绝访问内部属性")
...         return object.__getattribute__(self, name)   # 转发默认查找
>>> g = Guard()
>>> g.public = 1
>>> g.public          # 正常
1
>>> g._private        # 被拦截
Traceback (most recent call last):
  ...
AttributeError: 拒绝访问内部属性
```

> **实战建议**：`__getattribute__` 是四个钩子里最"重"的，滥用会拖慢**每一次**属性访问（包括 `self.xxx`），且容易与框架冲突。绝大多数"动态属性"需求用 `__getattr__` 就够。`__getattribute__` 的典型场景：安全网关、调试审计、ORM 属性代理。**设计顺序：`__getattr__` → `__setattr__` → 最后才考虑 `__getattribute__`。**

### 7.4.5 封装的实战与反模式

**反模式 1：Java 式 getter/setter 搬家。**

```python
class Bad:
    def __init__(self, x):
        self._x = x
    def get_x(self):            # ❌ 纯透传 getter——Python 里是噪音
        return self._x
    def set_x(self, value):     # ❌ 纯透传 setter——直接用属性不香吗
        self._x = value
```

```python
class Good:
    def __init__(self, x):
        self.x = x              # ✅ 公开裸属性
    # 需要校验时再升级为 property，接口不变
```

**反模式 2：为了"私有"而私有。** 把一切属性都塞成 `__xxx`（双下划线），结果是子类继承、序列化、调试全都不便，封装收益却为零——因为名称改写不提供任何真正保护。**实践标准**：内部状态用 `_x`（单下划线）；只有"防止子类命名冲突"这一种明确需求时才用 `__x`。

**反模式 3：`__getattr__` 把所有访问都"变魔术"。** 用户读 `obj.typo`（拼错）时，`__getattr__` 若无脑返回默认值，拼写错误会被静默吞掉，Debug 变成灾难。**凡是 `__getattr__` 处理不了的名字，必须抛 `AttributeError`**，让 `hasattr`、`getattr(obj, n, d)` 等依赖正常错误语义的工具能工作。

**实战：懒加载（lazy load）——封装的典型收益。**

```python
class Report:
    def __init__(self, data):
        self._data = data
        self._cache = None

    @property
    def summary(self):
        """第一次访问时计算并缓存，之后直接复用（把缓存细节藏在内部）"""
        if self._cache is None:
            print("计算 summary...")
            self._cache = sum(self._data) / len(self._data)     # 昂贵的计算
        return self._cache

>>> r = Report([10, 20, 30])
>>> r.summary      # 首次：打印"计算..."并缓存
计算 summary...
20.0
>>> r.summary      # 再次：直接用缓存，不再计算
20.0
```

调用方完全不知道"第一次要算、之后有缓存"——这是封装（信息隐藏）最漂亮的回报：**复杂度被关在门内，门外只有稳定的 `r.summary`。**

---

## 7.5 继承：MRO、super 与 Mixin

### 7.5.1 继承的语义与用途

**继承（inheritance）表达"is-a"关系**：`class Dog(Animal)` 声明"狗是一种动物"。继承带来两个能力：

1. **代码复用**：子类自动获得父类的方法与属性，不用重写
2. **子类型关系**：`isinstance(dog, Animal)` 为真，子类实例可以"当作父类用"（多态的基石，7.6）

```python
>>> class Animal:
...     def __init__(self, name):
...         self.name = name
...     def breathe(self):
...         return f"{self.name} 在呼吸"
>>> class Dog(Animal):            # 继承：Dog 是 Animal 的子类
...     def bark(self):
...         return f"{self.name} 汪汪！"
>>> d = Dog("旺财")
>>> d.breathe()                   # 复用父类方法
'旺财 在呼吸'
>>> d.bark()                      # 子类自己的方法
'旺财 汪汪！'
>>> isinstance(d, Animal)         # 子类型关系成立
True
>>> issubclass(Dog, Animal)       # 类层面的判断
True
```

**Python 的继承是运行时机制，不是编译期布局**。继承在 Python 里不过是"属性查找链上多挂了一层"（7.1.5 的 ③ 步）：`Dog` 实例找不到的属性，沿 `Dog → Animal → object` 一路向上找。没有 C++ 的虚表布局问题，也没有 C++ 的菱形对象拷贝——查找链天然就是"延迟绑定"的。

> **跨语言对比**：

| 语言 | 多继承 | 继承形态 |
|------|--------|---------|
| C++ | ✅（但有菱形二义性问题） | 编译期布局，多重基类子对象 |
| Java/C# | ❌（单继承 + 接口） | 单继承类 + 多接口 |
| Python | ✅（MRO 解决菱形） | 运行时查找链，C3 线性化（7.5.4） |

### 7.5.2 单继承与方法覆盖

子类可以**覆盖（override）**父类的任何属性或方法——因为"类属性"只是查找链上的名字，子类在自己的 `__dict__` 里放一个同名项就把父类遮蔽了：

```python
>>> class Animal:
...     kind = "animal"
...     def speak(self):
...         return "..."
>>> class Dog(Animal):
...     kind = "dog"                 # 覆盖类变量
...     def speak(self):             # 覆盖方法
...         return "汪汪"
>>> Dog().speak()
'汪汪'
>>> Dog.kind
'dog'
```

覆盖后若**还想调用父类的版本**，用 `super()`（下一节详讲）：

```python
>>> class Cat(Animal):
...     def speak(self):
...         base = super().speak()     # 调用 Animal.speak
...         return f"{base} 喵~"
>>> Cat().speak()
'... 喵~'
```

**为什么要覆盖？** 覆盖是"扩展而不修改"的实现手段——子类在父类行为基础上**增量修改**，父类代码一行不动。这是开放-封闭原则（Open-Closed Principle，OCP）的载体：**对扩展开放，对修改关闭**。

> **⚠️ 陷阱**：覆盖只在**类属性**这一层生效。实例属性（写进 `self.__dict__` 的）本来就属于实例，谈不上"覆盖"；但注意 7.1.5 的赋值规则——`self.kind = "xxx"` 会遮蔽类属性，误以为是"改了父类的 kind"。

### 7.5.3 `super()`：不是"父类"，而是 MRO 中的下一个

**`super()` 是最被误解的名字。** 初学者以为 `super()` 返回"父类"，其实它返回一个**代理对象**，让属性查找从 **MRO 中当前位置的下一个**开始。在单继承下"下一个"恰好就是父类，所以直觉没错；但到了多重继承，这个误解会让代码出错。

**零参数 `super()` 的用法与等价形式：**

```python
>>> class Dog(Animal):
...     def __init__(self, name):
...         super().__init__(name)              # 等价写法：super(Dog, self).__init__(name)
```

两种形式完全等价。`super()` 的查找机制：`super(Dog, self)` 内部从 `type(self).__mro__` 中 `Dog` 的位置**往后**取下一个类开始找 `__init__`。

**为什么用 `super()` 而不是直接 `Animal.__init__(self, name)`？** 关键差异在多重继承下：

```python
class A:
    def __init__(self):
        print("A")
        super().__init__()          # A 也调用 super——协同设计

class B(A):
    def __init__(self):
        print("B")
        super().__init__()

class C(B):
    def __init__(self):
        print("C")
        super().__init__()

C()
# 输出顺序：C → B → A（而不是 C → B 就停）
```

如果 B 直接写 `A.__init__(self)`，那么 `class C(B, A2)` 这种菱形场景下，A 的 `__init__` 会被**重复调用**、A2 的则**永远不被调用**。`super()` 解决的是"**MRO 里的下一个**"——让每个类在继承链上恰好被调用一次，不管这个链多曲折。这就是**协同 super（cooperative super）**：每个类假设链上还有别人，自己只负责调用下一个。

**菱形继承的 `__init__` 调用顺序**（完整例子，配合 7.5.4 的 MRO 理解）：

```python
class Root:
    def __init__(self):
        print("Root.__init__")
        super().__init__()          # 链的尽头是 object

class Left(Root):
    def __init__(self):
        print("Left.__init__")
        super().__init__()

class Right(Root):
    def __init__(self):
        print("Right.__init__")
        super().__init__()

class Diamond(Left, Right):
    def __init__(self):
        print("Diamond.__init__")
        super().__init__()

Diamond()
# 输出（每个 __init__ 恰好一次，顺序 = MRO）：
# Diamond.__init__
# Left.__init__
# Right.__init__
# Root.__init__
```

> **⚠️ 陷阱**：只有当**整条链**都使用 `super().__init__()` 时，协同才成立。如果某个类用 `Root.__init__(self)` 硬编码，链条就断了——后面的类不会被调用。**多继承里，硬编码类名的 `__init__` 调用是 bug。**

> **工程建议**：单继承下用 `super()` 还是 `Parent.__init__()` 都行，但**坚持 `super()`** 能保证将来引入多继承时不出问题。更重要的是：**如果覆盖了 `__init__`，要么调 `super().__init__(...)`，要么明确不调**（并注释为什么）——不调父类 `__init__` 意味着父类的初始化状态被跳过。

### 7.5.4 MRO 与 C3 线性化算法

**MRO（Method Resolution Order，方法解析顺序）** 决定了"属性查找链"到底按什么顺序走（7.1.5 的 ③ 步）。每个类都有 `__mro__` 属性，可以直接查看：

```python
>>> class Root: ...
>>> class Left(Root): ...
>>> class Right(Root): ...
>>> class D(Left, Right): ...
>>> D.__mro__
(<class '__main__.D'>, <class '__main__.Left'>, <class '__main__.Right'>, <class '__main__.Root'>, <class 'object'>)
```

`D` 的 MRO 是 `D → Left → Right → Root → object`。注意两个关键点：

- `Root` 排在 `object` **之前**，但**只出现一次**
- 左右两棵子树的基类 `Root` 被合并到 `Right` 之后——而不是在 `Left` 之后立刻出现

这个顺序由 **C3 线性化算法**（C3 linearization）计算得出，它满足三条公理：

1. **单调性（monotonicity）**：子类的 MRO 中，父类的相对顺序不变。若 `A` 在 `B` 之前，那么任何 `A` 子类的 MRO 中 `A` 也必须在 `B` 之前
2. **局部优先（local precedence）**：`class D(Left, Right)` 声明中 `Left` 排在 `Right` 前，则 MRO 中 `Left` 在 `Right` 前
3. **一致优先（consistency）**：每个类的 MRO 是其所有基类 MRO 的"稳定合并"

**手算一个 C3 例子。** 设 `class D(A, B, C)`，已知 `A.mro = [A, X, object]`、`B.mro = [B, Y, object]`、`C.mro = [C, X, Y, object]`。合并 `[D] + [A,X,object] + [B,Y,object] + [C,X,Y,object]`：

- 候选头：`A`（不出现在其他列表的**尾部**）→ 取 `A`
- 候选头：`B` → 取 `B`
- 候选头：`C` → 取 `C`
- 候选头：`X`（`[A,X,object]` 已空，X 出现在 `[C,X,Y,object]` 的头部、其他尾部的没有 X）→ 取 `X`
- 候选头：`Y` → 取 `Y`
- 最后 `object`

结果：`D → A → B → C → X → Y → object`。

**如果无法合并，Python 直接报错**——这比 C++ 在调用时才发现二义性要优雅得多。真正的冲突来自**基类顺序互相矛盾**：

```python
>>> class X: ...
>>> class Y: ...
>>> class A(X, Y): ...          # A 要求 X 在 Y 前
>>> class B(Y, X): ...          # B 要求 Y 在 X 前——与 A 矛盾！
>>> class C(A, B): ...          # 合并时 X、Y 谁也不能先取 → 报错
Traceback (most recent call last):
  ...
TypeError: Cannot create a consistent method resolution order (MRO) for bases X, Y
```

> **历史演进**：Python 2 的"经典类"（没有 `object` 基类）用**深度优先**解析——`D(Left, Right)` 的查找顺序是 `D → Left → Root → Right`，`Root` 会先于 `Right` 被搜到，造成"右侧子树被基类抢占"的经典 bug。PEP 253（2001 年，Python 2.2）引入**新式类**（统一继承自 `object`），并采用 C3 算法（由 Python 2.3 的 `type` 实现），同时从 `Root.__init__` 这类场景彻底解决菱形重复调用。Python 3 里**所有类都是新式类**，经典类已被移除。

> **实战建议**：绝大多数情况不需要手算 MRO——记住三条就够：（1）`__mro__` 能查；（2）多继承时基类**声明顺序**决定优先级（左优先）；（3）菱形场景靠 C3 保证"每个类只出现一次、基类总在子类之后"。真遇到奇怪的查找顺序，用 `D.__mro__` 打印出来看，比在脑子里推演可靠。

### 7.5.5 多重继承与 Mixin 模式

Python 支持多重继承。直接业务类多重继承容易踩坑，但 **Mixin 模式**是多重继承的"标准姿势"。

**Mixin = 一组可独立复用的小型行为单元**，特点是：不独立存在、不定义状态（或少状态）、只提供方法，靠 `super()` 沿链协作。**用 Mixin 实现"横向复用"**——多个类共用同一份能力，但不产生"is-a"的强耦合。

```python
>>> class JSONMixin:                       # 一个"横切"能力：JSON 序列化
...     def to_json(self):
...         import json
...         return json.dumps(self.__dict__)
...     @classmethod
...     def from_json(cls, s):
...         import json
...         return cls(**json.loads(s))
>>> class LogMixin:                        # 另一个横切能力：行为日志
...     def log(self, msg):
...         print(f"[{self.__class__.__name__}] {msg}")
```

这两个 Mixin 可以**独立组合**进任何类：

```python
>>> class User(JSONMixin, LogMixin):
...     def __init__(self, name):
...         self.name = name
>>> u = User("alice")
>>> u.to_json()              # 来自 JSONMixin
'{"name": "alice"}'
>>> u.log("登录成功")         # 来自 LogMixin
[User] 登录成功
```

**Mixin 命名规范**：以 `Mixin` 结尾（如 `ThreadingMixIn`、`Mapping` 的 `MutableMapping`），一看就知道"这是可组合的能力"而非"业务父类"。标准库与主流框架大量使用：`collections.abc` 的抽象集合、Django 的 `LoginRequiredMixin`、Flask 的视图类。

**多继承下的命名冲突**：两个基类定义了同名方法，**声明顺序（MRO）决定谁赢**：

```python
>>> class A:
...     def f(self): return "A"
>>> class B:
...     def f(self): return "B"
>>> class C(A, B): ...      # A 在前 → A.f 胜出
>>> C().f()
'A'
>>> class D(B, A): ...      # B 在前 → B.f 胜出
>>> D().f()
'B'
```

> **Mixin 反模式**：一个 Mixin 依赖"宿主类必须有什么属性"（隐藏耦合），或 Mixin 太大、几乎成了半个业务类。**Mixin 应该小、聚焦、无依赖**。如果发现某个 Mixin 需要宿主提供一堆前置条件，说明抽象粒度错了——它可能是该做基类的部分。

### 7.5.6 继承 vs 组合：设计决策

**"组合优先于继承"（Composition over inheritance）** 是 OOP 最重要的设计忠告之一。继承把两个类的生命周期**焊死**（父类改了子类跟着受影响，父子关系永久），而组合只是"我拥有一个部件"，换部件/加部件都灵活。

**组合的形态**：实例把另一个对象作为自己的属性（或 `__getattr__` 委托，7.4.4）：

```python
>>> class Engine:
...     def start(self): return "引擎启动"
>>> class Car:
...     def __init__(self):
...         self._engine = Engine()      # 组合：车"拥有"一个引擎
...     def start(self):
...         return self._engine.start()  # 转发（也可以加前后逻辑）
>>> Car().start()
'引擎启动'
```

**什么时候用继承，什么时候用组合？**

| 判断 | 用继承 | 用组合 |
|------|--------|--------|
| 关系本质 | "A 是一种 B"（is-a） | "A 拥有一个 B"（has-a） |
| 复用方式 | 方法/属性自动继承 | 显式转发/委托 |
| 可变性 | 继承链难改（焊死） | 部件可替换（灵活） |
| 多态需求 | 子类要替换父类出现的位置 | 只需行为一致（鸭子即可） |
| 典型反例 | 为复用而继承（"只是想抄方法"） | 为继承而继承（强迫 is-a） |

**经典反模式——"为了复用而继承"**：

```python
>>> class Stack(list):        # ❌ "栈是 list"？其实只是想要 list 的存储能力
...     def push(self, x): self.append(x)
...     def pop(self): return super().pop()
>>> s = Stack()
>>> s.insert(0, "从底部塞")    # 栈暴露了 list 的所有方法——栈被破坏了！
```

这就是"组合优先"要防的事：**通过继承获得的能力超出了你想要的接口**。正确做法是组合：

```python
>>> class Stack:
...     def __init__(self):
...         self._items = []              # ✅ 组合：内部用 list，但只暴露栈接口
...     def push(self, x): self._items.append(x)
...     def pop(self): return self._items.pop()
...     def __len__(self): return len(self._items)    # 顺便实现容器协议（7.7.4）
```

> **工程建议**：选择顺序——**先组合，组合满足不了"需要 is-a 语义 + 多态替换"时再考虑继承**。判断口诀：问自己"如果 A 继承 B，是否希望所有把 B 当参数的地方都能传 A？"——是，继承；否，组合。`isinstance` 检查（7.6.3 的 ABC）也只在继承语义下才有意义。

---

## 7.6 多态：同一接口，不同实现

### 7.6.1 多态的本质

**多态（polymorphism）是"同一个名字/接口，在不同类型上有不同行为"的能力。** 它的价值在调用侧：**调用者无需知道对象的真实类型，只依赖"它会做什么"**。

```python
>>> class Dog:
...     def speak(self): return "汪汪"
>>> class Cat:
...     def speak(self): return "喵喵"
>>> class Duck:
...     def speak(self): return "嘎嘎"
>>> def announce(animal):          # 不检查类型，只调用接口
...     print(f"动物说：{animal.speak()}")
>>> for a in (Dog(), Cat(), Duck()):
...     announce(a)                # 同一函数，三种输出
动物说：汪汪
动物说：喵喵
动物说：嘎嘎
```

`announce` 对三种类型的对象一视同仁——这是 Python 多态最纯粹的形态。**注意：这里没有任何继承**。`Dog`/`Cat`/`Duck` 互不相干，只因为都"会 `speak`"，就能被同一个函数使用。

**"多态"这个中文词也常被误读**：它不指"一个类有多种形态"，而指"一个接口有多种实现"。"多态性（polymorphism）"的字面是"多形性"——同一个 `speak` 调用，展现出"多形"。

> **跨语言对比——编译时多态 vs 运行时多态**：

| 类型 | 机制 | 语言 | 检查时机 |
|------|------|------|---------|
| 子类型多态（subtype polymorphism） | 继承 + 虚函数 | C++/Java/C# | 编译期检查接口，运行时分发 |
| 参数多态（parametric polymorphism） | 泛型/模板 | C++ 模板、Java 泛型 | 编译期 |
| **鸭子类型（structural/duck typing）** | 只要"会那个方法"即可 | **Python**/JS/Ruby | **运行时**（调用时才发现） |
| 静态结构化子类型 | 结构匹配 + 类型检查 | TypeScript、`typing.Protocol` | 编译期（Python 用 mypy 等） |

Python 的多态是**纯粹的运行时分发**：`animal.speak()` 在运行那一刻才去查找链上找 `speak`。没有虚表、没有接口声明，只有"查找链上有没有这个名字"。这正是动态语言 OOP 最轻巧也最强大的地方——也是 7.6.2 要展开的鸭子类型。

### 7.6.2 鸭子类型（Duck Typing）

**"如果它走起来像鸭子、叫起来像鸭子，那它就是鸭子"**——这是 Python 多态的核心哲学：**判断类型不看"它是什么"，而看"它会做什么"**。Python 内建函数是鸭子类型的最大受益者，看它们如何"只认协议、不认类型"：

```python
>>> sum([1, 2, 3])              # 传 list 可以
6
>>> sum((1, 2, 3))              # 传 tuple 可以
6
>>> sum({1, 2, 3})              # 传 set 可以
6
>>> sum(range(4))               # 传 range 也可以——甚至不是序列
6
```

`sum` 不检查 `type(x) is list`，它只需要迭代 `x`（`__iter__`/`__getitem__`）。**"能迭代"是一个鸭子特征，谁有算谁**。

鸭子类型与 `EAFP`（Easier to Ask Forgiveness than Permission，请求宽恕比请求许可更容易）天然配合——**先尝试调用，失败再处理异常**，而不是先 `isinstance` 判断：

```python
# ❌ LBYL 风格（Look Before You Leap）：先把类型问清楚
def speak_lbyl(animal):
    if hasattr(animal, "speak"):          # 问完再跳——检查与调用分离，可能竞态
        return animal.speak()
    raise TypeError("没有 speak 方法")

# ✅ EAFP + 鸭子：直接干，失败再说
def speak_eafp(animal):
    try:
        return animal.speak()
    except AttributeError:
        raise TypeError("没有 speak 方法") from None
```

**鸭子类型的边界（为什么它有时候"太自由"）**：
- 拼写错误：`animal.spak()` 直到调用那刻才报 `AttributeError`——大项目里这种错误要到运行时才炸
- 接口漂移：一个对象"碰巧有同名方法但语义完全不同"时，鸭子类型会静默接受错误对象
- 这正是 7.6.3/7.6.4 要提供的"补强"：**显式声明接口，让鸭子有迹可循**

> **设计哲学**：鸭子类型是 Guido 与静态语言论战的经典战场。Python 的回答是"调用者只关心行为"，这带来了极致的灵活与极致的组合性——但代价是放弃编译期接口检查。Python 官方的折中方案不是抛弃鸭子，而是**让鸭子可选地"上户口"**：`abc`（7.6.3）与 `typing.Protocol`（7.6.4）。

### 7.6.3 ABC 抽象基类：把接口声明出来

**抽象基类（Abstract Base Class，ABC）**让 Python 可以把"鸭子特征"变成**显式契约**：声明"这个类必须实现哪些方法"，并允许 `isinstance` 检查。标准库 `collections.abc`、`numbers` 都是 ABC 的大本营。

```python
>>> from collections.abc import Sequence
>>> isinstance([1, 2], Sequence)        # list 是"序列"——哪怕它没有继承 Sequence
True
>>> isinstance(42, Sequence)            # 数字不是序列
False
```

`isinstance([1,2], Sequence)` 成立，但 `list` 并没有继承 `Sequence`——这是 ABC 的**虚拟子类**机制：`Sequence.register(list)` 让类在 `isinstance` 层面"认作子类"。`list` 之所以被认作序列，是因为它实现了 `__len__` 和 `__getitem__`（Sequence 的抽象方法）。

**自己定义 ABC**：用 `abc.ABC` + `@abstractmethod`（PEP 3119）：

```python
>>> from abc import ABC, abstractmethod
>>> class Shape(ABC):                 # 抽象基类：只声明接口，不（完整）实现
...     @abstractmethod
...     def area(self): ...
...     @abstractmethod
...     def perimeter(self): ...
>>> s = Shape()                       # ❌ 抽象类不能实例化
Traceback (most recent call last):
  ...
TypeError: Can't instantiate abstract class Shape with abstract methods area, perimeter
>>> class Square(Shape):
...     def __init__(self, side): self.side = side
...     def area(self): return self.side ** 2        # 必须实现全部抽象方法
...     def perimeter(self): return self.side * 4
>>> Square(2).area()
4
>>> class Broken(Shape):              # 只实现一半 → 还是抽象
...     def area(self): return 0
>>> Broken()                          # ❌ 依然报错
Traceback (most recent call last):
  ...
TypeError: Can't instantiate abstract class Broken with abstract methods perimeter
```

**ABC 的两个价值**：
1. **契约强制**：漏实现抽象方法 → 实例化时直接报错（比运行到调用才炸早得多）
2. **类型检查**：`isinstance(x, Shape)` 成为有意义的多态判断（区别于纯鸭子）

**ABC 的陷阱**：ABC 继承自 `ABC` 后，`@abstractmethod` 只对**继承**生效，对"结构恰好相同"的类不生效——`isinstance(obj, Shape)` 对**没有继承 Shape** 的对象返回 `False`，除非显式 `Shape.register(obj类)`。也就是说：**ABC 是"显式契约"，鸭子类型是"隐式契约"**——ABC 要求你签约，鸭子不要求。

> **实战建议**：用 ABC 的时机——（1）你希望"不实现完整接口就报错"的强约束（框架、公共 API）；（2）需要 `isinstance` 做类型分派；（3）协作开发中把接口写清楚。如果只是内部小工具、接口松一点也没关系，纯鸭子（7.6.2）就够。

### 7.6.4 `typing.Protocol`：结构化的抽象接口

`typing.Protocol`（PEP 544，Python 3.8+）提供了**第三种抽象**：让"鸭子特征"可以被**静态类型检查器**识别——既保留运行时灵活性，又拿到静态检查的保护。

```python
>>> from typing import Protocol
>>> class SupportsSpeak(Protocol):
...     def speak(self) -> str: ...        # 只声明签名，没有实现
>>> class Dog:
...     def speak(self) -> str: return "汪汪"
>>> class Cat:
...     def speak(self) -> str: return "喵喵"
```

**结构化子类型（structural subtyping）**：`Dog` 和 `Cat` **没有继承** `SupportsSpeak`，但在类型检查器（mypy/pyright）眼里，它们结构上符合协议，因此可以传给标注了 `SupportsSpeak` 的函数：

```python
>>> def announce(a: SupportsSpeak) -> None:   # 类型检查器接受 Dog/Cat
...     print(a.speak())
```

**运行时**：协议默认不约束（不做 `isinstance` 检查）——除非给协议加 `@runtime_checkable`，让 `isinstance` 按结构匹配：

```python
>>> from typing import runtime_checkable
>>> @runtime_checkable
... class SupportsSpeak(Protocol):
...     def speak(self) -> str: ...
>>> isinstance(Dog(), SupportsSpeak)   # 结构上"会 speak"→ True
True
```

**ABC vs Protocol 的选择**：

| | `abc.ABC` | `typing.Protocol` |
|---|---|---|
| 运行时契约（不实现就不给实例化） | ✅ 强制 | ❌ 不强制（除非配合） |
| 静态类型检查 | 部分（继承关系可查） | ✅ 结构化子类型 |
| `isinstance`/`issubclass` | ✅ | ✅（需 `@runtime_checkable`） |
| 哲学 | 显式签约（nominal） | 结构匹配（structural） |
| 典型场景 | 框架强契约、公共 API | 库类型标注、鸭子类型的"上户口" |

> **版本注意**：`Protocol` 是 Python 3.8 加入（PEP 544）。Python 3.12 起 `typing` 的许多能力被合并进 `typing.Protocol` 的文档与工具链，但用法不变。**纯运行时项目**（不跑 mypy）用 `Protocol` 的价值有限——它主要价值在静态分析层。

### 7.6.5 运算符与协议多态：让类型融入语法

多态的终极形态，不是"让函数接受多种对象"，而是**让自定义类型参与语言本身的语法**。这正是第 4 章运算符重载与 7.7 特殊方法的意义所在——`a + b`、`len(x)`、`x in y`、`str(x)` 全都走的是"类型上找特殊方法"的多态分发：

```python
>>> class Vec:
...     def __init__(self, x, y): self.x, self.y = x, y
...     def __add__(self, other):          # 让 Vec 参与 +
...         return Vec(self.x + other.x, self.y + other.y)
...     def __repr__(self):
...         return f"Vec({self.x}, {self.y})"
>>> Vec(1, 2) + Vec(3, 4)                  # 语法级多态：+ 认识 Vec
Vec(4, 6)
```

`Vec(1,2) + Vec(3,4)` 底层就是"在 `Vec` 类型上查找 `__add__` 并分发"——**运算符是"接口"，各种类型是"实现"，这就是多态**。NumPy 的 `ndarray + ndarray` 之所以能做向量化，靠的正是这套机制（详见卷 2 的 NumPy 章节）。

**多态的三个层次（从窄到宽）**：

| 层次 | 机制 | 示例 |
|------|------|------|
| 继承多态 | 子类覆盖父类方法 | `Dog(Animal).speak()` |
| 鸭子多态 | 只要会那个方法，无需继承 | `announce(Dog())` 与 `announce(Cat())` |
| **语法多态** | 实现协议，融入语言语法 | `Vec + Vec`、`len(Stack)`、`x in Set` |

**一句话收束本章 7.5–7.6**：继承负责"让子类可以被当父类用"（is-a），多态负责"让不同实现填同一个接口"（会做什么），抽象负责"接口从哪来"（建模），封装负责"接口背后藏什么"（实现）。四者合起来，就是 OOP 的完整图景。

---

## 7.7 特殊方法（魔术方法）：协议系统全景

### 7.7.1 特殊方法总览：这不是魔法，是协议

**特殊方法（special methods，俗名"魔术方法"）是 Python 给类型预置的"协议钩子"**：你的类型实现某个特殊方法，就能参与对应的语言语法。它们统一写作 `__xxx__`（双下划线开头**和**结尾——注意与 7.4.2 的名称改写 `__x` 区分，后者没有后缀）。

**特殊方法不是魔法，是约定**。`len(x)` 之所以能作用于所有"长度"对象，是因为 CPython 内部把 `len(x)` 编译/分派为"在 `type(x)` 上找 `__len__` 并调用"。下表是完整地图（`__new__` 已在 7.1.3 出现，运算符重载细节在第 4 章已深讲，此处系统化）：

| 分类 | 特殊方法 | 触发的语法/内建 |
|------|---------|----------------|
| 创建/销毁 | `__new__`/`__init__`/`__del__` | `Cls(...)`、析构 |
| 表示 | `__repr__`/`__str__`/`__format__` | `repr()`、`str()`/`print()`、f-string |
| 数值 | `__add__`/`__sub__`/`__mul__`/`__neg__`/… | `+ - * -x` 等（第 4 章） |
| 比较 | `__eq__`/`__lt__`/`__le__`/… | `== < <=` 等（第 4 章） |
| 哈希/真值 | `__hash__`/`__bool__`/`__len__` | `hash()`、`if x`、真值（第 5 章） |
| 容器 | `__len__`/`__getitem__`/`__setitem__`/`__contains__`/`__iter__` | `len()`、`x[i]`、`in`、`for` |
| 可调用 | `__call__` | `obj(...)` |
| 属性 | `__getattr__`/`__setattr__`/`__delattr__`/`__getattribute__` | 属性访问（7.4.4） |
| 上下文 | `__enter__`/`__exit__` | `with`（第 8 章详讲） |
| 拷贝 | `__copy__`/`__deepcopy__` | `copy` 模块（深浅拷贝专题） |

**关键机制：特殊方法的隐式调用在"类型"上查找，绕过实例 `__dict__`。** 这是 Python 3 一个容易踩坑的硬规则：`len(x)`、`str(x)`、`x + y`、`x in y` 等**隐式调用**只会在 `type(x)` 及其 MRO 上找特殊方法，**不会**看你实例字典里有没有 `__len__`。

```python
>>> class Sneaky:
...     def __init__(self):
...         self.__len__ = lambda: 999     # 在实例字典里塞一个 __len__
>>> s = Sneaky()
>>> s.__len__()          # 显式属性访问 → 找到实例里的那个
999
>>> len(s)               # 隐式调用 → 只在类型上找 → 没有 → TypeError
Traceback (most recent call last):
  ...
TypeError: object of type 'Sneaky' has no len()
```

**为什么这样设计？** 这是刻意的安全决策。如果 `len(x)` 尊重实例字典，那么任何"碰巧给实例赋了 `__len__` 属性"的对象都能伪造长度——内建操作的安全性取决于"类型"（类型是被创建时定死的契约），而不是"可变动的实例状态"。这也意味着：**给某个实例单独注入特殊方法是无效的，必须改类定义**（或元类，第 12 章）。

> **版本注意**：Python 2 中特殊方法会从实例 `__dict__` 找（实例可以遮蔽），导致大量诡异 bug；Python 3 统一改为类型查找，行为更可预测。**升级老代码时，若发现"明明在实例里定义了 `__str__` 却不起作用"，就是这个规则的差异。**

### 7.7.2 表示协议：`__repr__`、`__str__`、`__format__`

三个方法管"对象怎么被展示"。默认实现（`object` 的）只给 `模块名.类名 object at 0x地址`，毫无可读性——所以任何自定义类型都该至少实现 `__repr__`。

**`__repr__`（开发者视角）vs `__str__`（用户视角）**：

| | `__repr__` | `__str__` |
|---|---|---|
| 触发 | `repr(x)`、REPL 显示、容器内元素 | `str(x)`、`print(x)`、f-string |
| 目标读者 | 开发者/调试者 | 终端用户 |
| 理想形态 | 尽可能 `eval(repr(x)) == x`（可重建） | 人话，可读 |
| 兜底关系 | 无 `__str__` 时，`str()` 会**退回** `__repr__` | 无 `__repr__` 时，`repr()` 用默认 |

```python
>>> class Point:
...     def __init__(self, x, y): self.x, self.y = x, y
...     def __repr__(self):
...         return f"Point({self.x}, {self.y})"          # 可重建：eval 回来还是 Point
...     def __str__(self):
...         return f"({self.x}, {self.y})"               # 用户友好的坐标写法
>>> p = Point(1, 2)
>>> p                # REPL 用 __repr__
Point(1, 2)
>>> str(p)           # 显式转字符串用 __str__
'(1, 2)'
>>> print(p)         # print 优先 __str__
(1, 2)
>>> f"{p}"           # f-string 优先 __str__
'(1, 2)'
```

**为什么要 `eval(repr(x)) == x`？** 调试时把 `repr(x)` 直接粘回代码就能重建对象——这是"调试友好"的设计哲学。标准库 `datetime` 的 `repr` 是典范：`repr(datetime(2026, 8, 11))` 输出 `datetime.datetime(2026, 8, 11, 0, 0)`，可直接执行。**注意**：`repr` 的"可重建"是理想而非强制——含资源（文件、连接）的对象显然无法重建。

> **⚠️ 陷阱**：`__repr__` 里**绝不能依赖 `__str__` 再调用 `repr`** 之类，但更要命的是互相引用。实现 `__repr__` 时，不要访问"可能触发 `__getattr__`/递归"的属性——否则调试一打印就递归爆炸。标准做法是只访问稳定的内部字段。

**`__format__`：控制 f-string 的 `:规格`。** `f"{x:spec}"` 会调用 `x.__format__(spec)`：

```python
>>> class Money:
...     def __init__(self, cents): self.cents = cents
...     def __format__(self, spec):
...         if spec == "":
...             spec = ".2f"
...         return f"¥{self.cents / 100:{spec}}"
>>> m = Money(1250)
>>> f"{m}"            # 默认两位小数
'¥12.50'
>>> f"{m:.0f}"        # 自定义规格
'¥12'
```

### 7.7.3 数值与比较协议：`__eq__`、`__hash__`、`__bool__`

**`__eq__` 与 `__hash__` 的黄金法则：相等的对象必须有相等的哈希值。** 哈希值（第 3 章讲过 `dict`/`set` 靠哈希定位）决定了对象能进 `set`、能当 dict 的键。

```python
>>> class Point:
...     def __init__(self, x, y): self.x, self.y = x, y
...     def __eq__(self, other):
...         if not isinstance(other, Point): return NotImplemented   # 第4章规则
...         return (self.x, self.y) == (other.x, other.y)
...     def __hash__(self):
...         return hash((self.x, self.y))        # 与 __eq__ 使用的字段完全一致
>>> {Point(1, 2), Point(1, 2)}                  # 哈希相等 + eq 相等 → set 去重
{Point(1, 2)}
```

**一旦定义了 `__eq__`，Python 会默认把 `__hash__` 置为 `None`（对象不可哈希）**——因为"相等"变了，"哈希"不能沿用默认（默认按 id 哈希）：

```python
>>> class NoHash:
...     def __eq__(self, other): return True      # 定义了 __eq__ → __hash__ 变 None
>>> hash(NoHash())
Traceback (most recent call last):
  ...
TypeError: unhashable type: 'NoHash'
```

这就是"可变对象不该有哈希"的底层原因：`list` 定义 `__eq__` 但没有 `__hash__`，所以不可哈希。**自定义类型若定义了 `__eq__`，要么补上一致的 `__hash__`，要么明确 `__hash__ = None` 声明"不可哈希"。**

> **⚠️ 陷阱**：可变对象**可以**自己实现 `__hash__`，但一旦作为 dict 键后改变内容，哈希值跟着变，`dict` 就再也找不回这个键了。**可变对象默认不该哈希——这正是一条正确的默认。**

**`__bool__` 与真值协议**（衔接第 5 章 5.1）：`if x` 判定 `bool(x)`，走 `__bool__`；**没有 `__bool__` 但实现了 `__len__` 时，空对象为假**：

```python
>>> class Bag:
...     def __init__(self): self.items = []
...     def __len__(self): return len(self.items)     # 有长度 → 真值由长度决定
>>> Bag() and True or False        # 空 → 假
False
>>> b = Bag(); b.items.append(1); bool(b)   # 非空 → 真
True
```

**数值运算协议**：`__add__`/`__sub__`/`__mul__`/`__neg__` 等已在第 4 章详讲（含 `NotImplemented` 的双向调度），此处不再展开，只强调一条：**实现了数值协议，自定义类型就"融入"了 `+ - *` 语法**——这是 7.6.5 所说的"语法多态"的直接应用。

`functools.total_ordering` 可以帮你补全比较运算符——只要实现 `__eq__` + 任意一个（如 `__lt__`），其余自动推导：

```python
>>> from functools import total_ordering
>>> @total_ordering
... class Rank:
...     def __init__(self, score): self.score = score
...     def __eq__(self, o): return self.score == o.score
...     def __lt__(self, o): return self.score < o.score      # 只需这一个
>>> Rank(1) < Rank(2)          # 由 __lt__ 推导
True
>>> Rank(2) >= Rank(1)         # >= 由 __lt__ 反转推导
True
```

### 7.7.4 容器协议：让自定义类型"像序列/映射"

**`__getitem__` 是最强的容器钩子——实现它，`x[i]`、`in`、`for`、切片全都有了。**

```python
>>> class FibSeq:
...     """斐波那契序列：只实现 __getitem__，就能被索引、遍历、in 判断"""
...     def __getitem__(self, i):
...         if i < 0: raise IndexError("无负索引")
...         a, b = 0, 1
...         for _ in range(i):
...             a, b = b, a + b
...         return a
>>> f = FibSeq()
>>> f[0], f[1], f[5]            # 索引
(0, 1, 5)
>>> 5 in f                      # 没有 __contains__？退化为遍历逐项比较
True
```

**迭代的回退机制**：没有 `__iter__` 时，`for` 会退化为"从 0 开始反复调 `__getitem__`，遇到 `IndexError` 停止"。看一个**有限**序列如何被 `for` 消费：

```python
>>> class MyRange:
...     """模拟 range(0, 3)：只实现 __getitem__，一样能被 for 遍历"""
...     def __getitem__(self, i):
...         if i >= 3: raise IndexError           # 越界信号：迭代到此结束
...         return i
>>> list(MyRange())             # for 的底层：0 → 1 → 2 → IndexError 停止
[0, 1, 2]
```

> **⚠️ 陷阱**：无限序列（如上面的 `FibSeq`）配合迭代回退会**无限循环**——`for x in f` 永远等不到 `IndexError`。真正的序列要么实现 `__iter__`（配合 `__len__` 边界），要么在 `__getitem__` 里对越界抛 `IndexError`。生产代码请直接实现 `__iter__`（第 5 章迭代器协议），`__getitem__` 回退只是兼容层。

**完整容器协议**：

| 特殊方法 | 作用 | 备注 |
|---------|------|------|
| `__len__` | `len(x)`、真值（7.7.3）、`range(len(x))` | 无 `__bool__` 时兼管真值 |
| `__getitem__(k)` | `x[k]`、`x[a:b]`、`in`、`for` 回退 | 切片传入 `slice` 对象 |
| `__setitem__(k, v)` | `x[k] = v` | 只读序列可不实现 |
| `__contains__(x)` | `x in obj` | 无此方法时退化用 `__iter__`/`__getitem__` |
| `__iter__` | `iter(x)`、`for x` | 返回迭代器（第 5 章） |
| `__reversed__` | `reversed(x)` | 可选 |

**`__contains__` 的优先级**：实现它，`in` 是 O(1)；不实现，`in` 退化为 O(n) 遍历。

**`__missing__`：dict 子类的"查不到时"钩子**（如默认工厂、大小写不敏感字典）：

```python
>>> class CaseInsensitiveDict(dict):
...     def __missing__(self, key):
...         # 找不到键时：按小写再找一遍
...         if isinstance(key, str):
...             low = key.lower()
...             for k, v in self.items():
...                 if k.lower() == low:
...                     return v
...         raise KeyError(key)
>>> d = CaseInsensitiveDict(Name="Alice")
>>> d["NAME"]              # 直接命中 __missing__
'Alice'
```

### 7.7.5 `__call__`：让实例变成"可调用对象"

实现 `__call__` 后，实例就能像函数一样调用——**"带状态的函数"**。函数本来就是对象（第 6 章），`__call__` 让任意对象获得函数式用法。

**经典场景：记忆化（memoization）——函数 + 缓存状态：**

```python
>>> class Memoized:
...     def __init__(self, fn):
...         self.fn = fn
...         self._cache = {}
...     def __call__(self, n):
...         if n not in self._cache:
...             self._cache[n] = self.fn(n)          # 算一次，之后直接取
...         return self._cache[n]
>>> @Memoized                       # 装饰器本质就是"把函数交给 __call__ 对象"
... def fib(n):
...     return n if n < 2 else fib(n - 1) + fib(n - 2)
>>> fib(50)                          # 没有递归爆炸——因为结果被缓存了
12586269025
```

> **设计哲学**：`__call__` 让"函数"与"对象"在语法上统一——调用者无需知道 `fib` 是函数还是对象。这就是第 6 章"函数是一等公民"的延伸：**一等公民性是语法层的能力，`__call__` 让任何对象都能成为一等公民。** 装饰器、`functools.partial`、Django 视图、`dataclasses.field` 都大量使用 `__call__`。

**判别**：`callable(x)` 检查对象能否被调用。函数、方法、lambda、类、实现了 `__call__` 的对象都是可调用的。

### 7.7.6 上下文管理器协议预览

`__enter__`/`__exit__` 让对象支持 `with` 语法——资源的获取与释放成对出现，异常时也能保证清理。这是第 8 章的主角，此处给全貌：

```python
>>> class Timer:
...     def __enter__(self):
...         import time
...         self._start = time.perf_counter()
...         return self                      # with 语句 as 子句拿到这个返回值
...     def __exit__(self, exc_type, exc_val, exc_tb):
...         elapsed = time.perf_counter() - self._start
...         print(f"耗时 {elapsed:.4f}s")
...         return False                     # False = 不吞异常（正常传播）
>>> with Timer():
...     sum(range(100000))                   # 进入 → 退出时自动打印耗时
耗时 0.0021s
```

协议要点：`__enter__` 的返回值绑定给 `as` 变量；`__exit__(exc_type, exc_val, exc_tb)` 在退出时被调用——若返回真值则**吞掉**异常。简化写法 `contextlib.contextmanager`（把生成器函数变成上下文管理器）在第 8 章详讲。

### 7.7.7 综合实战：一个"融入语言"的自定义类型

把本章散落的协议串起来，实现一个**不可变的二维向量**——它应该参与 `repr`、比较、哈希、加法、真值、甚至 `+` 语法：

```python
class Vector:
    """不可变二维向量：实现表示、相等、哈希、运算、真值五个协议。"""
    def __init__(self, x, y):
        self._x, self._y = x, y          # 私有存储（7.4 封装）

    # —— 表示协议 ——
    def __repr__(self):
        return f"Vector({self._x}, {self._y})"

    # —— 数值协议 ——
    def __add__(self, other):
        if isinstance(other, Vector):
            return Vector(self._x + other._x, self._y + other._y)
        return NotImplemented            # 不认识的类型 → 交还给对方/抛错（第4章）

    def __neg__(self):
        return Vector(-self._x, -self._y)

    # —— 比较/哈希协议 ——
    def __eq__(self, other):
        if isinstance(other, Vector):
            return (self._x, self._y) == (other._x, other._y)
        return NotImplemented
    def __hash__(self):                  # 与 __eq__ 字段一致 → 可进 set/当键
        return hash((self._x, self._y))

    # —— 真值协议 ——
    def __bool__(self):
        return self._x != 0 or self._y != 0     # 零向量为假，否则为真
```

测试协议全家桶：

```python
>>> v, w = Vector(1, 2), Vector(3, 4)
>>> repr(v)                  # 表示
'Vector(1, 2)'
>>> v + w                    # 语法多态：+ 认识 Vector
Vector(4, 6)
>>> -v                      # 一元运算
Vector(-1, -2)
>>> {v, Vector(1, 2)}       # 哈希 + 相等 → 去重
{Vector(1, 2)}
>>> bool(v), bool(Vector(0, 0))    # 真值
(True, False)
>>> sorted([w, v])          # ❌ 没实现 __lt__，排序会怎样？
Traceback (most recent call last):
  ...
TypeError: '<' not supported between instances of 'Vector' and 'Vector'
```

最后这个报错是有意的教学点：**协议不是全自动的**——不实现 `__lt__`，`Vector` 就不参与 `<`/`sorted`。这正是"协议"一词的精确含义：**你按契约实现哪些钩子，语言就给你哪些能力，不多不少。** 7.8 会给你更省事的"协议全家桶"——`dataclass`。

---

## 7.8 现代 OOP 工具箱：`dataclass`、`enum` 与 `__slots__`

前三节我们手写了协议的每个钩子。现代 Python（3.7+）提供了三个"类工厂"工具，把这些样板自动化——**你声明数据，语言生成协议**。

### 7.8.1 `dataclass`：声明式数据类（PEP 557，Python 3.7+）

**问题**：定义纯数据类（只有字段、相等、表示，没有复杂逻辑）时，手写 `__init__`/`__repr__`/`__eq__` 是枯燥且易错的样板代码：

```python
# 手写样板（7.7 综合实战的向量，去掉了自定义逻辑后的样子）
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def __repr__(self):
        return f"Point(x={self.x!r}, y={self.y!r})"
    def __eq__(self, other):
        if not isinstance(other, Point): return NotImplemented
        return (self.x, self.y) == (other.x, other.y)
```

**`@dataclass` 一句搞定**——自动生成 `__init__`、`__repr__`、`__eq__`（字段顺序与声明一致）：

```python
>>> from dataclasses import dataclass
>>> @dataclass
... class Point:
...     x: float                      # 类型注解 = 声明字段（顺序即初始化顺序）
...     y: float
...     label: str = "origin"         # 有默认值的字段放后面
>>> p = Point(1.0, 2.0)
>>> p
Point(x=1.0, y=2.0, label='origin')   # __repr__ 自动生成
>>> Point(1.0, 2.0) == Point(1.0, 2.0)   # __eq__ 按字段比较
True
```

**`field()` 与 `default_factory`——处理可变默认值**（回看 7.1.4 的可变类变量陷阱，dataclass 直接帮你规避）：

```python
>>> from dataclasses import dataclass, field
>>> @dataclass
... class Stack:
...     items: list = field(default_factory=list)   # ✅ 每次实例化都新建一个 list
>>> a, b = Stack(), Stack()
>>> a.items.append(1)
>>> b.items                     # 互不干扰——default_factory 避免了共享
[]
```

> **⚠️ 陷阱**：`@dataclass` 的默认值若是可变对象（`items: list = []`），**会直接报错**——`ValueError: mutable default <class 'list'> for field items is not allowed`。这是 dataclass 把 7.1.4 的经典陷阱**从设计上消灭**了，必须用 `field(default_factory=...)`。

**`frozen=True`：不可变数据类**——生成带 `__setattr__` 拦截的只读类（底层实现见 7.4.4 的 `object.__setattr__`）：

```python
>>> @dataclass(frozen=True)
... class Coordinate:
...     x: float
...     y: float
>>> c = Coordinate(1, 2)
>>> c.x = 3                 # ❌ frozen 拦截赋值
Traceback (most recent call last):
  ...
dataclasses.FrozenInstanceError: cannot assign to field 'x'
>>> hash(Coordinate(1, 2))  # frozen + eq → 自动获得 __hash__，可当 dict 键
7073325519029565851
```

**底层机制**：`dataclass` 是个**类装饰器**，它读取类体的**注解**（`x: float`），自动向类体注入生成的 `__init__`/`__repr__`/`__eq__` 等方法——**用的正是 7.7 的协议钩子**。这也是第 12 章"元编程"的绝佳实例：`dataclass` 让我们"声明式地描述类，让代码生成代码"。

**`slots=True`（Python 3.10+）**：生成带 `__slots__` 的类（配合 7.8.3），声明即省内存：

```python
>>> @dataclass(slots=True)          # Python 3.10+
... class Slim:
...     x: int
...     y: int
```

**选择矩阵：什么时候用 dataclass？**

| 场景 | 用 dataclass | 手写类 |
|------|:---:|:---:|
| 纯数据载体（配置、DTO、坐标、记录） | ✅ | |
| 需要校验/计算属性（7.4.3） | ✅（property 照常可写） | |
| 有复杂不变量、私有状态、复杂方法 | | ✅ |
| 需要继承 + 多态的设计 | ✅（可继承） | ✅ |

> **工程建议**：**现代 Python 的默认选择就是 `@dataclass`**——它消灭了大量样板、规避了可变默认值陷阱、自动对齐协议。手写 `__init__` 只留给"确实需要手写控制"的类。第三方的 `pydantic`（带校验与序列化）与 `attrs`（更早的同类库）是进阶选项。

### 7.8.2 `enum`：让魔法数字/字符串变成有名字的常量

**问题**：到处写 `"active"`、`1` 这类魔法值，拼写无检查、比较无意义、类型无约束。`enum.Enum` 提供了真正的"枚举类型"（PEP 435，Python 3.4+）：

```python
>>> from enum import Enum, auto
>>> class Status(Enum):
...     PENDING = auto()          # auto() 自动分配 1,2,3...
...     RUNNING = auto()
...     DONE = auto()
>>> Status.RUNNING
<Status.RUNNING: 2>
>>> Status.RUNNING.name           # 名字
'RUNNING'
>>> Status.RUNNING.value          # 值
2
```

**枚举的三条关键语义**：

1. **成员唯一且不可变**——重复值会合并成别名（alias），不报错但第二个名字指向同一成员：

```python
>>> class Color(Enum):
...     RED = 1
...     CRIMSON = 1          # 别名：CRIMSON 就是 RED 的另一个名字
>>> Color.RED is Color.CRIMSON     # 同一个成员
True
```

2. **成员比较走"身份"而非值**——`Status.RUNNING == 2` 为 `False`；要"和整数可比"，用 `IntEnum`：

```python
>>> from enum import IntEnum
>>> class Code(IntEnum):
...     OK = 200
...     NOT_FOUND = 404
>>> Code.NOT_FOUND == 404       # IntEnum 行为同 int
True
>>> Code.OK < Code.NOT_FOUND    # 甚至能排序
True
```

3. **迭代成员、拒绝重复值**（用 `@unique` 装饰器强制唯一）：

```python
>>> list(Color)                 # 迭代只出"主名"，别名不出现在迭代里
[<Color.RED: 1>]
>>> from enum import unique
>>> @unique
... class Bad(Enum):
...     A = 1
...     B = 1                  # ❌ ValueError: duplicate values found in <enum 'Bad'>
```

**实战**：用枚举替换魔法值（状态机、错误码、配置项），配合 `match/case`（第 5 章）效果极佳：

```python
def describe(status: Status) -> str:
    match status:                      # match/case 直接匹配枚举成员
        case Status.PENDING: return "排队中"
        case Status.RUNNING: return "运行中"
        case Status.DONE:    return "已完成"
```

### 7.8.3 `__slots__`：去掉 `__dict__`，省内存、提速

7.1.6 预告过：`__slots__` 声明"允许的属性白名单"，实例不再拥有 `__dict__`，属性存在**固定槽位**（类似 C 结构体字段）。省多少内存？——**单看一个实例"看不出来"，量变才见质变**：

```python
>>> import sys
>>> class Normal:                      # 默认：每个实例有一个 __dict__
...     def __init__(self): self.x = 1; self.y = 2
>>> class Slotted:
...     __slots__ = ("x", "y")         # 只有 x、y 两个槽位
...     def __init__(self): self.x = 1; self.y = 2
>>> n, s = Normal(), Slotted()
>>> sys.getsizeof(n), sys.getsizeof(s)   # 单实例大小竟然一样！
(48, 48)
```

**陷阱提醒**：`sys.getsizeof` 只算对象本身，**不计入**每个实例持有的 `__dict__` 对象——而 `__dict__` 本体（空字典 56 字节、有键时更大，实测 2 个键 ≈ 296 字节）才是真正被省掉的。用 `tracemalloc` 测**总量**才见分晓：

```python
>>> import tracemalloc
>>> def measure(cls, n=100_000):
...     tracemalloc.start()
...     objs = [cls() for _ in range(n)]
...     peak = tracemalloc.get_traced_memory()[1]
...     tracemalloc.stop()
...     return peak
>>> measure(Normal) / 1e6, measure(Slotted) / 1e6     # 10 万个实例的峰值内存（MB）
(9.6, 5.6)                                             # 省约 42%
```

**单看一个实例只省几十字节，但 100 万个对象就是上百 MB 的差距**（省掉的不只是 `__dict__` 本体，还有它每次插入的扩容与哈希表开销）。这正是"数量级"的含义——大数据批处理、游戏实体、ML 特征对象这类**以百万计**的实体类，`__slots__` 是标配。

**`__slots__` 的三条代价/规则**：

1. **拒绝动态属性**（7.1.6）——`s.z = 3` 直接 `AttributeError`
2. **继承时，子类若不声明 `__slots__`，实例又会拿回 `__dict__`**（槽位不自动继承）：

```python
>>> class SlottedChild(Slotted): ...      # 没声明 __slots__ → 又有了 __dict__
>>> SlottedChild().__dict__
{}
```

3. 与 `weakref`、`copy`、多进程 `pickle` 等工具的兼容需额外注意

**`__slots__` 与 `@dataclass` 结合**（7.8.1 的 `slots=True`）是现代 Python 的"省内存默认配方"。**是否默认全用 `__slots__`？** 社区意见不一——大多数应用对象数量不足以让内存成为瓶颈，而失去动态属性灵活性是实打实的约束。**决策：对象数量在十万级以上、或对性能敏感时启用；一般业务对象不必。**

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 类与实例 | `class` 是可执行语句；类对象是 `type` 的实例；实例创建走 `__new__`→`__init__` |
| 类变量 vs 实例变量 | 类变量共享、实例变量独立；**可变对象放实例变量**；赋值是重新绑定、不沿查找链走 |
| 属性查找链 | 实例 `__dict__` → 类 → 基类（MRO）；读走查找链、写不走 |
| 方法三兄弟 | 实例方法绑定 `self`、类方法绑定 `cls`、静态方法不绑定；底层是函数描述符 `__get__` |
| 四大特性 | 抽象（建模）、封装（藏细节）、继承（复用+is-a）、多态（同接口多实现）；抽象之争见 7.3.3 |
| 封装 | Python 无强制私有；`_x` 约定、`__x` 名称改写防冲突；`property` 受控属性；`__getattr__` 系协议 |
| 继承 | `super()` 是 MRO 的下一个而非父类；MRO 由 C3 算法保证单调性；Mixin 是多重继承的标准姿势；组合优先于继承 |
| 多态 | 鸭子类型（会什么就是什么）、ABC（显式契约）、`Protocol`（结构化子类型）；语法多态让类型融入语言 |
| 特殊方法 | 隐式调用在**类型**上查找、绕过实例 `__dict__`；表示/数值/容器/调用/上下文协议是"你实现钩子，语言给能力" |
| 现代工具箱 | `@dataclass` 声明式数据类（自动生成协议、规避可变默认值）；`Enum` 告别魔法值；`__slots__` 内存优化 |

---

#### 练习 7

**1.（预测输出）** 下面的代码输出什么？解释 `count` 的行为。

```python
class Counter:
    count = 0
    def __init__(self):
        self.count += 1

a, b = Counter(), Counter()
print(Counter.count)
```

**2.（解释行为）** `__slots__` 的类为什么能省内存？"子类不声明 `__slots__` 就恢复 `__dict__`"的机制原因是什么？

**3.（修复 bug）** 下面代码有共享状态 bug，修正它并说明属于 7.1.4 的哪种陷阱。

```python
class Student:
    courses = []
    def __init__(self, name):
        self.name = name
        self.courses.append("数学")
```

**4.（动手实现）** 用 `@dataclass` 实现一个 `Book`（字段：`title`、`author`、`year`），要求：相等按字段比较、可哈希（`frozen=True`）、`repr` 可读。再给 `year` 加一个校验——年份必须在 1000–2100 之间（提示：`__post_init__` 是 dataclass 的初始化后钩子）。

**5.（动手实现）** 手写一个类 `Rectangle`（不用 dataclass），实现：`__init__`、`__repr__`、`__eq__`、`__hash__`、`__bool__`（面积为 0 时为假）、`__slots__`。验证它能在 `set` 中去重。

**6.（解释行为）** 说明 `super()` 在下面的菱形继承中，`__init__` 的调用顺序，并解释为什么 `Root.__init__` 只被调用一次。

```python
class Root:
    def __init__(self): print("Root")
class A(Root):
    def __init__(self):
        print("A"); super().__init__()
class B(Root):
    def __init__(self):
        print("B"); super().__init__()
class C(A, B):
    def __init__(self):
        print("C"); super().__init__()
C()
```

**7.（分析）** 为什么 Python 3 中 `len(x)` 忽略实例字典里的 `__len__`？这与"内建操作的安全性"有什么关系？（提示：7.7.1）

**8.（动手实现）** 实现一个 `Temperature` 类：内部存摄氏温度，提供 `celsius` 与 `fahrenheit` 两个 `property`（华氏可写、双向换算），并要求华氏写入时校验不低于绝对零度（-459.67°F）。用"裸属性 → property"两步说明封装的接口稳定性。

**9.（深度思考）** 对比 `abc.ABC` 与 `typing.Protocol`：分别适合什么场景？"鸭子类型"在这两者之间处于什么位置？给出一个"用 Protocol 但运行时依赖鸭子"的真实例子（如 `os.PathLike`）。

**10.（综合实战）** 设计一个 `Playlist` 类，实现完整容器协议：`__len__`、`__getitem__`、`__setitem__`、`__contains__`、`__iter__`，再通过 `@dataclass` 或手写补上 `__eq__`。让它能参与 `len()`、`for`、`in`、切片，并解释"切片传入的是 `slice` 对象"这个事实。

---

**进入下一章的准备**：

- ✅ 能解释 `class` 语句的三步执行过程与"类也是对象"的含义
- ✅ 能说清类变量/实例变量的内存位置与可变类变量陷阱
- ✅ 能区分实例方法、类方法、静态方法并解释绑定的描述符机制
- ✅ 能说出 `_x` 与 `__x` 的区别、`property` 的三种价值
- ✅ 能解释 `super()` 的本质、MRO 的 C3 三原则、Mixin 模式
- ✅ 能区分鸭子类型、ABC、`Protocol` 三种抽象形态
- ✅ 能解释"特殊方法在类型上查找"的规则并实现一个多协议类型
- ✅ 能判断何时用 `@dataclass`、`Enum`、`__slots__`

> **衔接预告**：第 8 章"异常处理与上下文管理器"将完整展开 7.7.6 的 `with` 协议与 `__exit__` 的异常语义；第 12 章"元编程"会把 7.2.6 与 7.8.1 伏笔的描述符、类装饰器、元类收拢成体系。
