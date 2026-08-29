# 专题：Python 深浅拷贝，从引用语义到 CPython 底层

> **核心问题**：`a = b`、`a = b[:]`、`a = b.copy()`、`a = copy.copy(b)`、`a = copy.deepcopy(b)` 到底有什么区别？为什么 `[[]] * 3` 是经典的 Python 新手杀手？为什么函数默认参数用 `[]` 会出 bug？这些问题指向同一个根源——Python 的对象模型。

---

## 0. 为什么这个专题必须精通

深浅拷贝不是"了解一下就行"的知识。它直接关系到：

- **数据完整性**：你修改一个列表，另一个"副本"也跟着变了——数据被悄悄破坏
- **并发安全**：多线程共享对象时，浅拷贝和深拷贝的语义完全不同
- **性能决策**：什么时候可以安全地用浅拷贝（省内存），什么时候必须用深拷贝（正确性）
- **调试能力**：`is` vs `==` 的困惑、`id()` 的含义、CPython 小整数/字符串内部化——都源于同一个对象模型

**学习建议**：不要跳读。每一节的示例都亲手在 REPL 里跑一遍。

---

## 1. 变量是标签，不是盒子

### 1.1 引用语义

几乎所有主流语言中，"变量"都是一个有名字的内存区域。但 Python 不同：

```python
# C/Java 思维模型（错误！）：
#   a → [1, 2, 3]    （a 是一个"装有"列表的盒子）
#   b → [1, 2, 3]    （b 是另一个盒子，装着另一个列表）

# Python 实际模型（正确）：
#   a → [1, 2, 3] ← b   （a 和 b 都是贴在同一个列表上的标签）

>>> a = [1, 2, 3]
>>> b = a              # 没有创建新列表，只是多贴了一张标签

>>> a is b             # True——同一个对象
>>> id(a) == id(b)     # True——内存地址相同

>>> a.append(4)        # 通过 a 修改
>>> b                  # b 也"变"了——因为 b 指向同一个列表
[1, 2, 3, 4]
```

**核心认知**：Python 中**赋值永远不创建新对象**。它只改变名字到对象的绑定。

### 1.2 `is` vs `==`：身份 vs 值

这是理解深浅拷贝的前提。很多开发者用错了 `is`：

```python
# is：身份相等——两个名字指向同一个内存对象？
# ==：值相等——两个对象的内容相同？

>>> a = [1, 2, 3]
>>> b = [1, 2, 3]
>>> a == b            # True——内容相同
>>> a is b            # False——但不是同一个对象

>>> c = a
>>> a is c            # True——c 就是 a

# is 本质上是比较 id()
>>> a is b            # 等价于 id(a) == id(b)
```

**CPython 实现**——`is` 运算符在字节码层面只做指针比较：

```python
>>> import dis
>>> def compare(a, b):
...     return a is b
>>> dis.dis(compare)
  2           RESUME                   0
              LOAD_FAST                0 (a)
              LOAD_FAST                1 (b)
              IS_OP                    0              # ← 单条字节码，O(1) 指针比较
              RETURN_VALUE
```

`IS_OP` 在 C 源码中就是 `(PyObject *)a == (PyObject *)b`——比较两个 `PyObject*` 指针的值。

### 1.3 `id()` 的真实含义

```python
# id() 返回的是 CPython 中 PyObject* 的内存地址
# 这不是 Python 语言规范的一部分——是 CPython 的实现细节

>>> import sys
>>> a = [1, 2, 3]
>>> hex(id(a))         # 例如 '0x7f8b1c001680'
>>> sys.getsizeof(a)   # 对象占用的内存大小（字节）

# 注意：id() 在对象生命周期内唯一，但可以被复用
>>> x = [1, 2, 3]
>>> addr = id(x)
>>> del x
>>> y = [4, 5, 6]
>>> id(y) == addr      # 可能是 True——CPython 复用了释放的内存
```

> **⚠️ 陷阱**：`id()` 的值在对象被 `del` 后可以被回收复用。不要拿 `id()` 值做持久化的"唯一标识"。

---

## 2. 不可变类型的"假拷贝"问题

### 2.1 不可变对象不需要拷贝——但"看起来像拷贝"

```python
# 对不可变类型（int, str, tuple, frozenset, bytes），拷贝显得"无聊"
>>> import copy
>>> a = 42
>>> b = copy.copy(a)
>>> a is b             # True——copy.copy 对 int 什么都不做！
>>> b = copy.deepcopy(a)
>>> a is b             # True——deepcopy 同样什么都不做

>>> s = "hello"
>>> copy.copy(s) is s   # True
>>> copy.deepcopy(s) is s  # True
```

**为什么 CPython 这样做？** 不可变对象的内容永远不会改变，所以复制它没有意义——直接返回同一个对象既安全又高效。在 `copy` 模块源码中，对不可变类型的处理就是直接 `return x`。

### 2.2 例外——tuple 中的可变元素

这是最容易被忽视的陷阱：

```python
# 不可变的 tuple 可以包含可变元素
>>> t = ([1, 2], [3, 4])

# copy.copy(t) 返回 t 本身（tuple 不可变）
>>> shallow = copy.copy(t)
>>> shallow is t        # True！似乎没问题

# 但 deepcopy 就不同了
>>> deep = copy.deepcopy(t)
>>> deep is t           # False
>>> deep[0] is t[0]     # False——内嵌的列表也被复制了

# ❌ 危险场景
>>> original = ([1, 2, 3], [4, 5, 6])
>>> shallow = copy.copy(original)
>>> shallow[0].append(999)
>>> original            # 被"污染"了！
([1, 2, 3, 999], [4, 5, 6])

# ✅ 安全做法
>>> deep = copy.deepcopy(original)
>>> deep[0].append(999)
>>> original            # 不受影响
([1, 2, 3], [4, 5, 6])
```

**结论**：不可变容器 ≠ 安全的浅拷贝。如果容器内有可变元素，浅拷贝等于没拷贝。

---

## 3. 浅拷贝：只复制第一层

### 3.1 什么是浅拷贝

浅拷贝创建一个新的容器对象，但**容器中的元素仍然是原对象的引用**：

```
原始列表:       浅拷贝后:
a → [●, ●, ●]   b → [●, ●, ●]
     |  |  |          |  |  |
     ▼  ▼  ▼          └──┴──┘── 和 a 指向相同的元素对象
     A  B  C
```

### 3.2 五种浅拷贝方式

```python
>>> original = [1, 2, [3, 4]]

# 方式 1：list.copy()（Python 3.3+）
>>> b = original.copy()

# 方式 2：切片 [:]  ——最经典的浅拷贝写法
>>> b = original[:]

# 方式 3：copy 模块
>>> import copy
>>> b = copy.copy(original)

# 方式 4：类型构造函数
>>> b = list(original)

# 方式 5：解包（Python 3.5+）
>>> b = [*original]

# 五种方式结果相同——都是浅拷贝
```

**验证浅拷贝行为**：

```python
>>> original = [1, 2, [3, 4]]
>>> shallow = original[:]

>>> original is shallow          # False——容器本身是新的
>>> original[0] is shallow[0]    # True——元素 1 是同一个对象
>>> original[2] is shallow[2]    # True——嵌套列表是同一个对象！

# 🔥 关键验证：修改嵌套对象
>>> original[2].append(5)        # 通过 original 修改嵌套列表
>>> shallow[2]                   # shallow 的嵌套列表也变了！
[3, 4, 5]

# 但修改顶层元素不会影响彼此
>>> original.append(6)
>>> len(shallow)                 # 4——shallow 不受影响
```

### 3.3 CPython 中 `list.copy()` 的实现

在 `Objects/listobject.c` 中，`list.copy()` 的本质：

```c
// 简化的 C 逻辑
static PyObject *
list_copy(PyListObject *self) {
    Py_ssize_t size = Py_SIZE(self);
    PyObject *new_list = PyList_New(size);  // 分配新的列表对象
    for (Py_ssize_t i = 0; i < size; i++) {
        PyObject *item = self->ob_item[i];
        Py_INCREF(item);                    // 只增加引用计数
        new_list->ob_item[i] = item;        // 直接复制指针——不复制对象
    }
    return new_list;
}
```

关键：**只复制了指针数组，没有递归复制元素对象**。这就是"浅"的根源。

### 3.4 dict 和 set 的浅拷贝

```python
# dict 的浅拷贝
>>> d = {"a": 1, "b": [2, 3]}
>>> shallow = d.copy()
>>> shallow is d                # False
>>> shallow["b"] is d["b"]      # True——嵌套对象共享

# set 的浅拷贝
>>> s = {1, (2, 3)}
>>> shallow = s.copy()
>>> shallow is s                # False
# 但如果元素是可变对象（如列表），一样是共享引用
```

### 3.5 切片赋值的"隐藏拷贝"

```python
# 切片赋值会产生拷贝行为
>>> a = [1, 2, 3, 4, 5]
>>> a[1:4] = [9, 9, 9]    # 替换索引 1-3——不涉及拷贝
>>> a
[1, 9, 9, 9, 5]

# 但如果右侧是 a 自身的切片，就需要先拷贝
>>> a = [1, 2, 3, 4, 5]
>>> a[0:3] = a[2:5]        # 右侧先被求值——创建了一个切片副本
>>> a
[3, 4, 5, 4, 5]            # 结果正确——因为右侧 a[2:5] 先被拷贝了

# 如果没有这个隐式拷贝，结果会错乱
```

---

## 4. 深拷贝：递归复制一切

### 4.1 `copy.deepcopy()` 的行为

深拷贝递归地复制整个对象图——新对象和原对象没有任何共享引用：

```python
>>> import copy
>>> original = [1, 2, [3, 4, [5, 6]]]
>>> deep = copy.deepcopy(original)

>>> original is deep              # False
>>> original[2] is deep[2]        # False——嵌套列表也被复制了
>>> original[2][2] is deep[2][2]  # False——三层嵌套也被复制

# 修改 original 的任何层级都不影响 deep
>>> original[2].append(999)
>>> deep[2]                       # [3, 4, [5, 6]]——不受影响
```

### 4.2 `deepcopy` 如何处理循环引用

这是 `deepcopy` 最精妙的设计——它能正确处理对象引用自身的情况：

```python
>>> import copy
>>> a = [1, 2]
>>> a.append(a)            # a 引用自身：[1, 2, [...]]
>>> a
[1, 2, [...]]

>>> b = copy.deepcopy(a)   # 不会无限递归！
>>> b
[1, 2, [...]]
>>> b is a                 # False——独立的副本
>>> b[2] is b              # True——b 内部的循环引用被正确重建
```

**CPython 实现原理**：`deepcopy` 维护一个 `memo` 字典（`id(原对象) → 新对象`），每次复制前先检查是否已经复制过该对象：

```python
# deepcopy 的核心逻辑（简化版）
def _deepcopy(x, memo):
    if id(x) in memo:
        return memo[id(x)]          # 已复制过，直接返回副本
    if isinstance(x, list):
        y = []
        memo[id(x)] = y             # 先注册，再递归——关键！
        for item in x:
            y.append(_deepcopy(item, memo))
        return y
    # ... 处理其他类型
```

**先注册、再递归**——这个顺序是关键。如果反过来（先递归、再注册），循环引用就会导致无限递归。

### 4.3 `deepcopy` 的性能代价

```python
>>> import copy, timeit

# 构造一个深层嵌套结构
>>> def build_nested(depth):
...     if depth == 0:
...         return [1, 2, 3]
...     return [build_nested(depth - 1)]

>>> data = build_nested(100)

# 浅拷贝：O(n) 指针复制
>>> %timeit copy.copy(data)
# ~0.5 μs

# 深拷贝：O(总节点数)——递归遍历整个对象图
>>> %timeit copy.deepcopy(data)
# ~50 μs——约 100 倍差距

# 结论：能浅则浅。deepcopy 只在确有必要时使用。
```

### 4.4 不可变对象的 deepcopy 优化

```python
# deepcopy 对纯不可变结构有优化——但还是比 copy 慢
>>> t = (1, 2, "hello", (3, 4))
>>> copy.deepcopy(t) is t      # True——全是不可变，直接返回

>>> t = ([1, 2], 3)            # 包含可变元素的 tuple
>>> copy.deepcopy(t) is t      # False——必须复制
```

---

## 5. `__copy__` 和 `__deepcopy__` 协议

### 5.1 自定义类型的默认拷贝行为

```python
import copy

class Node:
    def __init__(self, value, children=None):
        self.value = value
        self.children = children if children is not None else []

# 默认行为：copy 和 deepcopy 都可以工作，但使用默认的 __reduce__ 或 __copy__ 回退
>>> root = Node(1, [Node(2), Node(3)])
>>> shallow = copy.copy(root)
>>> shallow is root                    # False
>>> shallow.children is root.children  # True——children 列表是浅拷贝的
```

### 5.2 实现 `__copy__`：控制浅拷贝

```python
import copy

class LinkedList:
    """单向链表——默认的 copy 行为不对，需要自定义"""
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node

    def __copy__(self):
        """浅拷贝：只复制当前节点，next 共享"""
        return LinkedList(self.value, self.next)

    def __repr__(self):
        return f"{self.value} → {self.next}"

>>> node2 = LinkedList(2)
>>> node1 = LinkedList(1, node2)
>>> shallow = copy.copy(node1)
>>> shallow is node1               # False——新的 Node 对象
>>> shallow.next is node1.next     # True——共享同一个 node2
```

### 5.3 实现 `__deepcopy__`：控制深拷贝

```python
class LinkedList:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node

    def __copy__(self):
        return LinkedList(self.value, self.next)

    def __deepcopy__(self, memo):
        """深拷贝：递归复制整个链表"""
        # 先查 memo——处理循环链表
        if id(self) in memo:
            return memo[id(self)]

        copied = LinkedList(self.value)
        memo[id(self)] = copied  # 先注册

        if self.next is not None:
            copied.next = copy.deepcopy(self.next, memo)
        return copied

    def __repr__(self):
        return f"{self.value} → {self.next}"

>>> node2 = LinkedList(2)
>>> node1 = LinkedList(1, node2)
>>> deep = copy.deepcopy(node1)
>>> deep is node1                  # False
>>> deep.next is node1.next        # False——整个链被独立复制
```

### 5.4 `__deepcopy__` 的 `memo` 参数

`memo` 不是可选的——如果你的对象可能被多次引用（例如 DAG 或有循环引用），必须在 `__deepcopy__` 中使用 `memo`，否则 `deepcopy` 会无限递归：

```python
class GraphNode:
    def __init__(self, name):
        self.name = name
        self.neighbors = []

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]

        copied = GraphNode(self.name)
        memo[id(self)] = copied          # ✅ 先注册
        # 递归复制邻居时，memo 会防止无限循环
        copied.neighbors = [
            copy.deepcopy(n, memo) for n in self.neighbors
        ]
        return copied
```

> **⚠️ 陷阱**：如果你 `__deepcopy__` 中调用 `copy.deepcopy(x)` 而不是 `copy.deepcopy(x, memo)`，memo 不会被传递，循环引用会导致无限递归。

---

## 6. 经典陷阱集

### 6.1 陷阱 1：`[[]] * n`——Python 新手的第一大坑

```python
# ❌ 致命错误——所有子列表是同一个对象
>>> matrix = [[0] * 3] * 3
>>> matrix
[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
>>> matrix[0][0] = 999
>>> matrix
[[999, 0, 0], [999, 0, 0], [999, 0, 0]]          # 💀 三行全变了！

# 为什么？因为 * 运算符复制的是引用，不是对象
>>> matrix[0] is matrix[1] is matrix[2]             # True——同一个列表！

# ✅ 正确做法 1：列表推导式——每次迭代创建新列表
>>> matrix = [[0] * 3 for _ in range(3)]
>>> matrix[0][0] = 999
>>> matrix
[[999, 0, 0], [0, 0, 0], [0, 0, 0]]               # ✅ 正确

# ✅ 正确做法 2：嵌套推导式
>>> matrix = [[0 for _ in range(3)] for _ in range(3)]

# ✅ 正确做法 3（仅适用于简单类型）：copy.deepcopy
>>> import copy
>>> matrix = copy.deepcopy([[0] * 3] * 3)
```

**CPython 层面解释**——序列乘法 `*` 在字节码中的实现：

```python
>>> import dis
>>> def multiply_list():
...     return [[0] * 3] * 3
>>> dis.dis(multiply_list)
              LOAD_CONST               1 (0)
              BUILD_LIST               1
              LOAD_CONST               2 (3)
              BINARY_OP                7 (*)        # [0] * 3 → [0, 0, 0]
              BUILD_LIST               1             # 包装成 [[0, 0, 0]]
              LOAD_CONST               2 (3)
              BINARY_OP                7 (*)        # [[0, 0, 0]] * 3
              RETURN_VALUE
```

`BINARY_OP *` 对列表执行 `list_repeat`，它在 C 层做的是：分配一个容量为 `n * len(list)` 的新列表，然后**逐元素复制指针**——每个位置存的都是同一个 `PyObject*`。所以 `[x] * n` 中的每个元素都是 `x` 本身。

### 6.2 陷阱 2：`lst[:]` 只能浅拷贝一层

```python
# ❌ 以为 [:] 是万能的
>>> original = [[1, 2], [3, 4]]
>>> copy = original[:]               # 浅拷贝
>>> copy[0].append(999)
>>> original
[[1, 2, 999], [3, 4]]               # 还是被修改了！

# ✅ 多层嵌套结构需要 deepcopy
>>> original = [[1, 2], [3, 4]]
>>> import copy
>>> copy = copy.deepcopy(original)
>>> copy[0].append(999)
>>> original
[[1, 2], [3, 4]]                     # 安全
```

### 6.3 陷阱 3：函数默认参数的"记忆效应"

这是陷阱 6.1 的变体——根源完全相同：

```python
# ❌ 经典错误——默认参数在函数定义时只求值一次
def add_item(item, target=[]):
    target.append(item)
    return target

>>> add_item(1)
[1]
>>> add_item(2)
[1, 2]                         # 💀 上次的 1 还在！
>>> add_item(3)
[1, 2, 3]                      # 💀 默认列表在调用间"记住"了状态

# 为什么？因为 def 是一个可执行语句
>>> import dis
>>> def demo(x=[]):
...     pass
>>> dis.dis(demo)
              LOAD_CONST               0 (())       # 先构造空元组
              BUILD_LIST               0             # 构建空列表
              BUILD_TUPLE              1             # 放入默认值元组
              ...                                   # 这个列表对象被保存在函数的 __defaults__ 中

>>> demo.__defaults__           # ([],)  ——同一个列表对象
>>> demo.__defaults__[0] is add_item.__defaults__[0]   # 不同函数，各自独立

# ✅ 标准惯用法
def add_item(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

### 6.4 陷阱 4：`dict.fromkeys()` 的值共享

```python
# ❌ fromkeys 使用同一个值对象初始化所有键
>>> d = dict.fromkeys(['a', 'b', 'c'], [])
>>> d
{'a': [], 'b': [], 'c': []}
>>> d['a'].append(1)
>>> d
{'a': [1], 'b': [1], 'c': [1]}          # 💀 三个键共享同一个列表

# ✅ 正确做法：用字典推导式——每次迭代创建新的 []
>>> d = {k: [] for k in ['a', 'b', 'c']}
>>> d['a'].append(1)
>>> d
{'a': [1], 'b': [], 'c': []}             # ✅
```

### 6.5 陷阱 5：推导式是浅拷贝

```python
# 列表推导式创建的是新列表——但其元素是原对象的引用
>>> original = [[1, 2], [3, 4], [5, 6]]
>>> derived = [x for x in original]       # 浅拷贝等价

>>> derived is original                   # False——容器是新的
>>> derived[0] is original[0]             # True——元素是共享的
>>> derived[0].append(999)
>>> original[0]                           # [1, 2, 999]——被修改了

# 如果需要深拷贝的效果，在表达式中显式复制
>>> derived = [x[:] for x in original]    # 对每个子列表做浅拷贝
>>> derived = [copy.deepcopy(x) for x in original]  # 或用 deepcopy

# 集合推导式同理
>>> original = {(1, [2])}                 # 注意：可变元素不能放入 set
```

### 6.6 陷阱 6：`copy.copy` 对某些类型是"假拷贝"

```python
# 某些类型的 __copy__ 被优化为返回自身
>>> import copy, decimal, fractions

# 不可变类型：copy 返回自身
>>> copy.copy(42) is 42               # True
>>> copy.copy("hello") is "hello"     # True
>>> copy.copy((1, 2, 3)) is (1, 2, 3)  # True
>>> copy.copy(None) is None           # True

# 但如果包含可变元素，tuple 的 copy 行为成为陷阱（见 2.2 节）
```

### 6.7 陷阱 7：`*args` 和 `**kwargs` 的隐式拷贝

```python
# * 在函数调用时会创建一个 tuple——但元素是浅拷贝
def show_ids(*args):
    for i, arg in enumerate(args):
        print(f"args[{i}] id={id(arg)}")

>>> data = [[1, 2], [3, 4]]
>>> show_ids(*data)
args[0] id=140234567890123      # 和 data[0] 相同的 id
args[1] id=140234567890456      # 和 data[1] 相同的 id

# args 元组是新创建的，但其中的列表元素仍是共享引用
# 修改 args[0] 会影响 data[0]
```

---

## 7. CPython 底层全景

### 7.1 引用计数与拷贝

```python
>>> import sys
>>> a = [1, 2, 3]
>>> sys.getrefcount(a)   # 2——a 本身 + getrefcount 的临时参数

>>> b = a                # 增加引用，不分配新内存
>>> sys.getrefcount(a)   # 3

>>> c = a[:]             # 浅拷贝——分配新列表
>>> sys.getrefcount(a)   # 3——a 的引用计数不变
>>> sys.getrefcount(c)   # 2——新列表有独立的引用计数

# 每个 PyObject 都有一个 ob_refcnt（引用计数）字段
# 赋值 a=b 只是让 ob_refcnt + 1
# 浅拷贝分配新的 PyObject，ob_refcnt 从头开始
```

### 7.2 内存布局对比

```
原始列表 a = [1, [2, 3]] 的内存结构：

a (PyListObject)
├─ ob_refcnt: 1
├─ ob_type: &PyList_Type
├─ ob_size: 2
└─ ob_item ──→ [PyObject*, PyObject*]
                    │            │
                    ▼            ▼
              PyLongObject   PyListObject
              value=1        ├─ ob_size: 2
                             └─ ob_item ──→ [PyObject*(2), PyObject*(3)]

浅拷贝 b = a[:] 之后：

a ──→ [PyObject*(1), PyObject*(list)]     b ──→ [PyObject*(1), PyObject*(list)]
              │              │                          │              │
              │              └──────────┬───────────────┘              │
              ▼                         ▼                              ▼
        PyLongObject(1)          PyListObject([2,3])    ...同样指向这两个对象
                                  ↑ 这个嵌套列表是共享的！↑

深拷贝 b = copy.deepcopy(a) 之后：

a ──→ [PyObject*(1), PyObject*(listA)]    b ──→ [PyObject*(1'), PyObject*(listB)]
              │              │                          │              │
              ▼              ▼                          ▼              ▼
        PyLongObject(1)  PyListObject([2,3])    PyLongObject(1)  PyListObject([2,3])
                                                                  ↑ 全新分配！↑
```

### 7.3 `copy` 模块的调度机制

```python
# copy.copy 的调度逻辑（简化）
def copy(x):
    cls = type(x)
    # 1. 检查是否有 __copy__ 方法
    if hasattr(cls, '__copy__'):
        return cls.__copy__(x)

    # 2. 对内置类型使用注册的拷贝函数
    copier = _copy_dispatch.get(cls)
    if copier:
        return copier(x)

    # 3. 回退到 __reduce_ex__ 或 __reduce__（pickle 协议）
    rv = x.__reduce_ex__(4)  # 或 __reduce__()
    # ... 用返回的 (callable, args, state) 重建对象

# copy.deepcopy 的调度逻辑（简化）
_deepcopy_dispatch = {
    list: _deepcopy_list,
    dict: _deepcopy_dict,
    set: _deepcopy_set,
    # ... 每种类型都有专门的深拷贝函数
}
```

### 7.4 什么时候不能用 `deepcopy`

```python
# 1. 文件对象、socket、锁等——它们依赖外部资源，无法被"复制"
>>> import copy, threading
>>> lock = threading.Lock()
>>> copy.deepcopy(lock)         # TypeError: cannot deepcopy this pattern object

# 2. lambda 和嵌套函数——deepcopy 可能失败或产生意想不到的结果
>>> f = lambda x: x + 1
>>> copy.deepcopy(f)            # 大多数情况下可以，但不保证

# 3. 模块和类——deepcopy 返回它们自身
>>> import math
>>> copy.deepcopy(math) is math  # True

# 4. 包含大量重复引用的大型对象图——性能和内存可爆炸
#    deepcopy 的 memo 字典在极端情况下可能成为瓶颈
```

---

## 8. 决策指南

### 8.1 什么时候用哪种拷贝

| 场景 | 推荐方法 | 原因 |
|------|---------|------|
| 纯不可变数据 | 无需拷贝 | 内容永不改变，共享引用是安全的 |
| 只有一层可变容器 | `list.copy()` / `[:]` / `dict.copy()` | 浅拷贝已足够，性能最优 |
| 嵌套可变容器 | `copy.deepcopy()` | 必须递归复制才能完全隔离 |
| 自定义类 | 实现 `__copy__` / `__deepcopy__` | 精细控制拷贝行为 |
| 需要持久化对象状态 | `pickle.loads(pickle.dumps(obj))` | 另一种"深拷贝"方式，但更慢且有限制 |
| 大型嵌套结构 + 性能敏感 | 手动递归 + 针对性优化 | `deepcopy` 是通用方案，针对性代码可更快 |

### 8.2 性能排序

```python
# 从最快到最慢：
# 1. 不可变对象的 copy/deepcopy（直接返回自身）    ~0.02 μs
# 2. [:] / list.copy()                            ~0.05 μs
# 3. copy.copy()                                  ~0.10 μs
# 4. 列表推导式 [x for x in original]              ~0.20 μs
# 5. copy.deepcopy()（单层）                       ~2 μs
# 6. copy.deepcopy()（深层嵌套）                   ~10-100+ μs
# 7. pickle.loads(pickle.dumps(obj))              ~20-200+ μs
```

### 8.3 快速判断：我需要深拷贝吗？

问自己三个问题：

1. **对象图中有可变嵌套吗？** 没有 → 浅拷贝足够
2. **我会修改嵌套结构吗？** 不会 → 浅拷贝足够
3. **修改需要完全隔离吗？** 不需要 → 浅拷贝足够

只有三个问题都是"是"时，才需要 `deepcopy`。

---

## 专题小结

| 概念 | 本质 | 关键点 |
|------|------|--------|
| 引用语义 | Python 变量是对象标签，不是内存盒子 | 赋值 `=` 不创建新对象，只改变绑定 |
| `is` vs `==` | 身份相等 vs 值相等 | `is` 比较指针（`id()`），`==` 比较内容（`__eq__`） |
| 浅拷贝 | 创建新容器，复制元素指针 | 五种等价写法；嵌套对象仍共享 |
| 深拷贝 | 递归复制整个对象图 | 用 `memo` 字典防止循环引用；先注册再递归 |
| `__copy__` | 自定义浅拷贝协议 | 返回值是新的"浅等效"对象 |
| `__deepcopy__` | 自定义深拷贝协议 | 必须传递和更新 `memo` 参数 |
| `[[]] * n` | CPython 乘法复制的是指针 | 所有元素指向同一个对象——经典的共享引用陷阱 |
| 默认参数 | `def f(x=[])` 只求值一次 | `[]` 在函数定义时创建，所有调用共享 |

---

## 练习

1. **预测输出**：以下代码的输出是什么？解释每一步的 `is` 和 `==` 关系。
   ```python
   a = [1, 2, 3]
   b = [1, 2, 3]
   c = a
   d = a[:]
   e = [a, b, c, d]
   f = list(e)
   g = copy.copy(e)
   h = copy.deepcopy(e)
   
   print(a is c)
   print(a is d)
   print(e is f)
   print(e is g)
   print(e is h)
   print(e[0] is g[0])
   print(e[0] is h[0])
   ```

2. **矩阵陷阱修复**：以下代码哪里有问题？写出三种修复方式。
   ```python
   def make_matrix(rows, cols):
       return [[0] * cols] * rows
   ```

3. **实现 `__deepcopy__`**：为一个双向链表实现 `__deepcopy__` 方法，确保能正确处理节点间的相互引用。

4. **`deepcopy` 的 `memo` 作用**：以下代码会怎样运行？如果去掉 `memo` 检查会怎样？写出 `deepcopy` 在复制这个结构时的 `memo` 状态变化。
   ```python
   a = []
   b = [a, a]
   a.append(b)
   c = copy.deepcopy(a)
   ```

5. **默认参数 vs 浅拷贝**：写一个函数 `def f(x, cache={})` 的替代实现，在保持缓存功能的同时避免共享引用问题。

6. **性能实验**：构造一个 5 层嵌套的字典结构（每层 10 个键），用 `timeit` 对比 `copy.copy`、`copy.deepcopy`、`json.loads(json.dumps(...))`、手动递归函数四种方式的性能。分析和解释差异。

7. **引用计数探究**：创建以下结构，用 `sys.getrefcount` 跟踪每个操作后的引用计数变化：
   - 赋值 `b = a`
   - 浅拷贝 `b = a[:]`
   - 深拷贝 `b = copy.deepcopy(a)`
   - 删除 `del a`
   解释为什么 `deepcopy` 之后 `del a` 不会影响 `b`。

8. **`__copy__` 设计**：设计一个 `Snapshot` 类，它包装一个可变对象，`__copy__` 返回当前状态的冻结副本（tuple），`__deepcopy__` 递归冻结所有嵌套。写出完整实现并测试。

---

**关联专题**：
- 第 3 章：可变/不可变类型的完整讨论
- 第 4 章：`is`/`==` 运算符、增强赋值的引用语义
