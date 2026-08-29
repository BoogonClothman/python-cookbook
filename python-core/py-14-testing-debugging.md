# 第14章 测试与调试

> **学习目标**：建立"专业程序员与业余的分水岭是测试"的心智；掌握从 `unittest` 到 `pytest` 的完整测试体系（断言/夹具/参数化/mock/覆盖率）；会用 `pdb` 断点调试、`traceback` 诊断、`cProfile` 定位性能瓶颈；理解"可测试性"如何反向塑造更好的代码设计。

---

前 13 章教你"把程序写对"——本章教你"**证明它对**，以及**它不对时怎么找到错**"。这两件事是工程能力的最后一块拼图：能写出 100 行的脚本是入门，能写出"10000 行代码 + 改动后依然正确"的系统是专业。测试不是写完代码后的点缀，而是**设计工具**：它逼你把代码拆成可验证的单元，逼你显式声明依赖，逼你写下行为契约。调试则是测试的镜像——测试说"哪里错了"，调试器说"错的时候发生了什么"。

本章与前面章节的关系：第 2 章的 `assert` 语句是"运行时防御"，本章的断言**框架**（`unittest`/`pytest`）是"事后验证"，两者机制不同（框架断言失败不抛 `AssertionError` 中止进程，而是记录并继续）；第 8 章的异常链在 14.8 的 traceback 解读里再次出场；第 10 章提过 pytest 用 import 钩子改写 `assert`，14.3.2 展开它的 AST 机制；第 13 章的 `logging`/`random.seed`/`zoneinfo` 是本章"可复现测试"与"日志驱动调试"的直接工具；性能剖析本章只到 `cProfile` 入门，C 扩展/JIT/内存深挖留给第 15 章。

---

## 14.1 测试哲学与策略

### 14.1.1 为什么测试是专业的分水岭

先回答"为什么"再谈"怎么做"。测试的三个不可替代的价值：

**1. 回归安全网**：改一行代码，怎么知道没弄坏别的？测试把"我改的时候心里没底"变成"跑一遍就知道"。

**2. 重构的勇气**：没有测试的重构是"重写"（怕弄坏不敢动）；有测试的重构是"手术"（切哪里都不怕，测试是生命体征监护仪）。这正是第 7 章设计模式、第 10 章包结构调整等一切"改进"的前提。

**3. 活的文档**：测试是**可执行的行为规格**——它不会像注释那样过期。`test_parse_rejects_empty_string()` 这个测试名，比"解析函数不接受空串"这种注释更可信，因为它**真的在验证**。

```python
# 反模式：能跑的"一次性脚本"（写完就没再碰过）
def process(data):
    ...
# 一年后：没人敢改 process，因为不知道它依赖什么、该输出什么

# 正模式：测试即刹车
def test_process_handles_empty_input():
    assert process([]) == []
def test_process_preserves_order():
    assert process([3, 1, 2]) == [3, 1, 2]
# 现在改 process 之前，跑一遍测试就知道有没有弄坏契约
```

> **工程影响**：**变更成本随代码量指数增长，而测试把增长曲线压平**。没有测试的项目，越到后期越不敢动（"这代码只有神能改"）；有测试的项目，10 万行也敢重构。这是"专业"与"业余"最实际的分界。

### 14.1.2 测试金字塔

测试分三层，正确配比是金字塔形：

```
         ╱ 端到端 ╲        少（十几个）：整个系统从用户视角走一遍
       ╱   集成    ╲      中（几十个）：模块之间协作、数据库、外部服务
     ╱     单元     ╲    多（成百上千）：单个函数/类的行为
```

| 层级 | 测什么 | 速度 | 稳定性 | 成本 |
|------|--------|------|--------|------|
| 单元测试 | 单个函数/方法/类 | 毫秒级 | 高（无外部依赖） | 低 |
| 集成测试 | 模块协作、DB、网络 | 秒级 | 中（依赖环境） | 中 |
| 端到端测试 | 完整用户流程 | 分钟级 | 低（UI/环境脆） | 高 |

```python
# 各层职责示例（一个购物系统）
# 单元：test_calculate_total_applies_discount()      —— 纯逻辑
# 集成：test_order_creation_writes_to_database()      —— 逻辑 + 数据库
# 端到端：test_user_can_checkout_from_cart()          —— 全流程
```

> **⚠️ 陷阱**：金字塔**倒置**（端到端最多）是新手常见错误——跑一次要几分钟、环境一抖全红、排错困难。规则：**单元测试打底（70%+），端到端只覆盖关键用户路径**。端到端测试的价值是"兜底验证集成正确"，不是"替代单元测试"。

### 14.1.3 TDD 与测试先行

**TDD（测试驱动开发）**的三步循环：

```
红灯（写一个会失败的测试）→ 绿灯（写最小代码让它过）→ 重构（改进实现，测试保持绿）
```

```python
# 1. 红灯：先写测试（此时实现还不存在）
def test_roman_to_int_basic():
    assert roman_to_int("IV") == 4          # ImportError/NameError —— 红

# 2. 绿灯：写最小实现
def roman_to_int(s: str) -> int:
    return 4 if s == "IV" else 0            # 只求这个测试过

# 3. 重构：加更多用例后抽象出通用实现
#    测试保持绿色，实现从"特例"演进为"规则"
```

**TDD 是设计工具，不是测试工具**——这是最被误解的一点。先写测试的**真正收益**是逼你在写实现前就想清楚：

- 函数**叫什么**、**入参出参**是什么（接口设计）；
- 边界条件（空输入、异常）**先被定义**；
- 依赖怎么注入（否则没法测）——可测试性设计（14.1.4）。

> **实战建议**：TDD 不必教条（"先测试后代码"对探索性代码不适用），但"**写代码前至少想清楚一个测试**"是底线。务实路线：新功能先写 1–2 个关键测试再实现；修 bug 先写复现测试再修（这是调试方法论 14.7.4 的一部分——**能复现的 bug 已经好了一半**）。

### 14.1.4 可测试性：让代码天生好测

**可测试性**是代码质量的先行指标——不好测的代码，往往也是耦合重、难维护的代码。三个抓手：

**1. 纯函数优先**（衔接第 6 章）：同输入必同输出、无副作用——天然可测，不需要任何 mock：

```python
# ❌ 难测：逻辑与 I/O 绞在一起
def process_file(path):
    data = open(path).read()          # 文件 I/O 在函数里
    result = data.upper()
    open(path + ".out", "w").write(result)   # 副作用
    return result

# ✅ 可测：纯逻辑 + 薄 I/O 壳
def transform(data: str) -> str:      # 纯函数：测它！
    return data.upper()

def process_file(path):               # 薄壳：I/O 只做搬运，不值得测
    with open(path) as f:
        result = transform(f.read())
    with open(path + ".out", "w") as f:
        f.write(result)
```

**2. 依赖注入**：需要的外部资源（DB、网络、时间）**从参数进**，而不是函数内部 `import`/`datetime.now()`：

```python
# ❌ 隐式依赖：测试无法替换
def send_report():
    client = EmailClient()                    # 内部创建 → 测试必连真邮件
    client.send("report", generate())

# ✅ 显式依赖：测试注入假的
def send_report(client: EmailClient) -> None:   # client 从参数进
    client.send("report", generate())

# 测试：send_report(FakeClient())  —— 不用 mock 也能测
```

**3. 边界分离**：I/O（网络/文件/时间/随机）与业务逻辑分开——这正是 14.4 mock 哲学的基础：**只 mock 边界，不 mock 自己的逻辑**。

> **工程影响**："可测试性"与"设计质量"几乎同义：纯函数 = 低耦合，依赖注入 = 显式依赖，边界分离 = 单一职责。**如果你发现代码很难测，先别急着学更多 mock 技巧——回头重构代码**。测试是设计质量的体检仪。

---

## 14.2 unittest：标准库测试框架

`unittest` 是标准库自带（从 Python 2.1 起）的 xUnit 风格框架（JUnit 的 Python 移植）。虽然 pytest（14.3）是事实标准，但 `unittest` **零依赖**、内置于 `python -m unittest`，理解它的模型（`TestCase`/`TestSuite`/`TestRunner`）对读懂任何 xUnit 系框架都有帮助。

### 14.2.1 TestCase 与断言方法速查

```python
import unittest

class TestCalc(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(1, 2), 3)

    def test_float_precision(self):
        # ⚠️ 浮点断言：不要 assertEqual(0.1 + 0.2, 0.3)！
        self.assertAlmostEqual(0.1 + 0.2, 0.3)      # 默认 7 位小数容差

    def test_identity(self):
        a = [1]; b = a
        self.assertIs(a, b)                         # is 语义（第 2 章）
        self.assertIsNone(None)

    def test_collections(self):
        self.assertIn("k", {"k": 1})
        self.assertIn(3, [1, 2, 3])
        self.assertIsInstance(3, int)
```

| 断言 | 等价于 | 用途 |
|------|--------|------|
| `assertEqual(a, b)` | `a == b` | 值相等 |
| `assertIs(a, b)` | `a is b` | 身份（第 2 章 `is` vs `==`） |
| `assertAlmostEqual(a, b)` | 容差内相等 | **浮点**（第 3 章精度陷阱） |
| `assertTrue/assertFalse(x)` | `bool(x)` | 真值 |
| `assertIn(x, c)` | `x in c` | 成员（第 5 章 `__contains__`） |
| `assertIsInstance(x, T)` | `isinstance` | 类型 |
| `assertRaises(E, fn, *a)` | 期望抛 E | 异常（见 14.2.4） |

**与裸 `assert` 的本质区别**：

```python
# 裸 assert：失败即抛 AssertionError → 进程中止
assert calc.add(1, 2) == 3        # 第一个失败的断言直接崩

# unittest 断言：失败被框架捕获 → 该测试记为 FAILED，继续跑其他测试
self.assertEqual(calc.add(1, 2), 3)
```

> **🔑 机制洞察**：`unittest` 断言失败抛的是 `AssertionError` 子类（`unittest.fail` 路径），但由 `TestRunner` 捕获并记入结果，**不中断整个测试进程**——这就是"测试框架"与"运行时防御断言"（第 2 章）的分工：前者**汇总报告**，后者**立即中止**。裸 `assert` 还能被 `python -O` 优化掉，而 `unittest` 断言永远生效。

### 14.2.2 测试生命周期：setUp / tearDown / setUpClass

```python
class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):                      # 整个类只跑一次
        cls.conn = create_connection()        # 昂贵资源（DB 连接）

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def setUp(self):                          # 每个测试方法前跑
        self.conn.execute("BEGIN")            # 每测一个干净事务

    def tearDown(self):                       # 每个测试方法后跑
        self.conn.execute("ROLLBACK")         # 不留脏数据

    def test_insert(self):
        self.conn.execute("INSERT ...")
        # ...
```

生命周期时序：

```
TestDatabase 类加载
  → setUpClass（1 次）
    → setUp → test_insert → tearDown     （每个测试方法独立实例！）
    → setUp → test_query  → tearDown
  → tearDownClass（1 次）
```

> **🔑 机制洞察**：`unittest` 为**每个测试方法创建新的 `TestCase` 实例**（`TestSuite` 按方法实例化）——所以 `self.xxx` 属性在测试之间**天然隔离**（第 10 章模块单例的污染在测试类里不存在）。`setUp`/`tearDown` 的职责是"环境准备/清理"；资源清理优先用 `addCleanup`（比 `tearDown` 更稳，`setUp` 中途失败也会执行）。

> **⚠️ 陷阱**：`setUp` 里 `open`/`connect` 的资源，**忘在 `tearDown` 关闭 = 测试间泄漏**（文件句柄耗尽、DB 连接池爆）。现代写法用 `self.addCleanup(conn.close)`（等价第 8 章的 `with` 语义，但即使 `setUp` 断言失败也会注册清理）。

### 14.2.3 测试发现与运行

```python
# 测试文件约定：test_*.py 或 *_test.py，测试方法以 test_ 开头
# tests/test_calc.py
import unittest
from mypkg import calc

class TestCalc(unittest.TestCase):
    def test_add(self): ...
    def test_sub(self): ...

if __name__ == "__main__":
    unittest.main()
```

```bash
$ python -m unittest                    # 自动发现（当前目录递归）
$ python -m unittest tests.test_calc    # 指定模块
$ python -m unittest tests/test_calc.py # 指定文件
$ python -m unittest -v                 # 详细输出（每个测试一行）
```

```python
$ python -m unittest -v
test_add (tests.test_calc.TestCalc) ... ok
test_sub (tests.test_calc.TestCalc) ... ok

Ran 2 tests in 0.001s
OK
```

> **实战建议**：`python -m unittest` 是零依赖的底线方案（任何环境都能跑）；团队项目直接用 pytest（14.3）——pytest **能直接跑 unittest 风格的测试**（兼容层），迁移成本极低。

### 14.2.4 上下文断言：assertRaises / assertWarns / assertLogs

```python
class TestErrors(unittest.TestCase):
    def test_raises(self):
        # 方式 1：上下文管理器（推荐——能精确检查异常对象）
        with self.assertRaises(ValueError) as ctx:
            parse_int("abc")
        self.assertEqual(str(ctx.exception), "invalid literal for int()")

        # 方式 2：回调形式
        self.assertRaises(ValueError, parse_int, "abc")

        # 方式 3：精确异常类型（子类不匹配会失败）
        with self.assertRaisesRegex(ValueError, "invalid"):
            parse_int("abc")

    def test_warns(self):
        with self.assertWarns(DeprecationWarning):
            legacy_function()

    def test_logs(self):                # 断言日志输出（衔接 13.9）
        with self.assertLogs("mypkg", level="INFO") as cm:
            mypkg.do_something()
        self.assertIn("starting", cm.output[0])
```

> **⚠️ 陷阱**：`assertRaises(ValueError)` 捕获的是**精确类型或子类**（`assertRaises(ValueError)` 会通过 `TypeError`？不会——`TypeError` 不是 `ValueError` 子类）。想"只要抛异常就行"用 `assertRaises(Exception)`——但这是**反模式**（掩盖了"抛的为什么是它"的信息），精确到具体类型才是好的测试。

### 14.2.5 subTest 与 skip

```python
class TestValidation(unittest.TestCase):
    def test_all_rules(self):
        cases = [
            ("", False),            # (输入, 期望)
            ("a" * 100, False),
            ("valid", True),
        ]
        for value, expected in cases:
            with self.subTest(value=value):     # 子测试：一个失败不影响其他
                self.assertEqual(validate(value), expected)
```

```python
class TestPlatform(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "POSIX only feature")
    def test_fork(self): ...

    @unittest.skipUnless(sys.version_info >= (3, 11), "needs 3.11+")
    def test_new_api(self): ...

    @unittest.skip("not implemented yet")
    def test_future(self): ...
```

`subTest` 的价值：**循环数据驱动的用例，一个失败不再"一票否决"整组**——失败报告会显示 `subTest(value='a'*100)` 指明哪组数据挂了。`skip` 让"平台/版本条件"（衔接 13.7.4）不阻塞 CI。

---

## 14.3 pytest：现代测试框架

pytest 是 Python 测试的**事实标准**（Flask/Django/pandas/numpy 全在用）。它的胜利不是"又一个框架"，而是三个设计决策：**零样板**（函数即测试）、**fixture 依赖注入**（解决 setUp 的继承地狱）、**断言重写**（失败信息直接可读）。

### 14.3.1 为什么 pytest 是事实标准

```python
# test_calc.py —— 不用类、不用 self、不用继承
def test_add():
    assert calc.add(1, 2) == 3        # 普通 assert！不是 self.assertEqual

def test_float():
    assert calc.add(0.1, 0.2) == pytest.approx(0.3)   # 浮点容差
```

```bash
$ pytest -q
2 passed in 0.01s
```

| 维度 | unittest | pytest |
|------|----------|--------|
| 样板 | 类 + `self` + 专用断言 | 函数 + 裸 `assert` |
| fixture | `setUp` 继承（层级深了难缠） | **依赖注入**（参数名即依赖） |
| 参数化 | `subTest` 循环 | `@pytest.mark.parametrize` 声明式 |
| 失败信息 | "assertEqual failed: 3 != 4" | "assert 3 == 4，两侧值+上下文" |
| 插件 | 少 | 丰富（`pytest-cov`/`xdist`/`freezegun`...） |
| 兼容 | — | **能直接跑 unittest 风格** |

> **实战建议**：新项目直接 pytest；遗留项目从 unittest 迁 pytest 零成本（pytest 原生兼容 `unittest.TestCase`）。唯一该坚持 unittest 的场景：**受限环境装不了第三方包**（CI 沙箱、标准库-only 部署）。

#### 跨语言对比：测试框架的家族谱

Python 的测试框架不是孤例——整个 xUnit 家族同构，理解一家通吃全家：

| 语言 | 框架 | 断言 | 夹具 | 参数化 |
|------|------|------|------|--------|
| Python | unittest / pytest | `assertEqual` / 裸 `assert` | `setUp` / fixture | `subTest` / `parametrize` |
| Java | JUnit 5 | `assertEquals` | `@BeforeEach` | `@ParameterizedTest` |
| JavaScript | Jest / Vitest | `expect(x).toBe(y)` | `beforeEach` | `it.each([...])` |
| Go | testing | `t.Errorf` | `TestMain` | 表驱动（for 循环） |
| Rust | `#[test]` | `assert_eq!` | 无（值即夹具） | 无内置 |

**共同心智**（跨语言通用）：

1. **断言**：声明"应该怎样"，失败记录不中断；
2. **夹具**：准备/清理环境（`setUp` ↔ `@BeforeEach` ↔ `beforeEach`）；
3. **发现机制**：按命名约定自动收集（`test_*` ↔ `*Test` ↔ `*.test.js`）；
4. **报告**：通过/失败/跳过汇总 + 失败详情。

> **设计哲学**：测试框架的"家族相似"说明测试是**工程方法论**而非语言特性——换语言不换思路。Python 生态的特殊之处在于 pytest 的**声明式风格**（fixture 注入 + 断言重写）走到了其他语言前面（Jest 的 `beforeEach` 仍是命令式）。学新语言的测试框架时，先找"它的 pytest 对应物"。

### 14.3.2 断言重写机制（🔑 机制洞察）

pytest 最惊艳的特性是"普通 `assert` 失败时显示两侧值"：

```python
$ pytest test_calc.py
def test_add():
>       assert calc.add(1, 2) == 4
E       assert 3 == 4
E        +  where 3 = calc.add(1, 2)
```

**机制**：pytest 在**收集测试文件时用 AST 改写源码**——这正是第 10 章 10.2.4 讲的 import 钩子实战：pytest 把 `AssertionRewritingHook`（一个 `MetaPathFinder`）插入 `sys.meta_path`，在模块被导入时**拦截编译**，把 `assert x == y` 改写成"计算 x、计算 y、比较、失败时拼接详细报告"的字节码：

```python
# 源代码
assert calc.add(1, 2) == 4

# 改写后的逻辑（示意）
__tmp1 = calc.add(1, 2)          # 先算左侧
__tmp2 = 4                       # 再算右侧
if not (__tmp1 == __tmp2):
    raise AssertionError(f"assert {__tmp1!r} == {__tmp2!r}\n"
                         f" + where {__tmp1} = calc.add(1, 2)")
```

普通 Python 的 `assert` 失败只报 `AssertionError`（无两侧值）；pytest 的改写把"**断言的内容**"变成失败报告的一部分。这就是为什么 pytest 的失败信息"像人写的"——它确实是被编译器重写出来的。

> **🔑 版本注意**：断言重写只对**测试文件**生效（pytest 通过 `--assert=rewrite` 控制，默认改写测试模块）——被测试的**业务代码不重写**（保持零运行时开销）。调试"为什么我的 assert 报告这么详细/不详细"时，检查 `--assert` 选项与文件是否被 pytest 收集。

### 14.3.3 fixture：作用域、依赖与 conftest

fixture 是 pytest 对 `setUp` 的彻底重构——**按需注入，而非继承**：

```python
import pytest

@pytest.fixture
def db():                        # fixture 名字 = 测试的参数名
    conn = create_connection()
    yield conn                   # yield 前：准备；yield 后：清理（第 8 章 with 协议）
    conn.close()

def test_insert(db):             # 声明依赖 db → pytest 自动调用 fixture
    db.execute("INSERT ...")

def test_query(db):              # 每个测试拿到【新的】db（默认 function 作用域）
    rows = db.query("...")
```

**作用域**（`scope`）控制 fixture 的复用粒度：

| scope | 生命周期 | 适用 |
|-------|---------|------|
| `function`（默认） | 每个测试 | 大多数（隔离） |
| `class` | 每类一次 | 类内共享昂贵对象 |
| `module` | 每模块一次 | 模块级共享（DB schema） |
| `session` | 整个测试会话 | 最昂贵（网络客户端） |

```python
@pytest.fixture(scope="session")
def api_client():
    return create_api_client()       # 整个会话只建一次
```

**fixture 依赖 fixture**（参数名即依赖，无继承层级）：

```python
@pytest.fixture
def user(db):                        # 依赖 db fixture
    return db.insert_user("alice")

def test_user_profile(user):         # 依赖 user（自动先建 db）
    assert user.name == "alice"
```

**`conftest.py`**：放共享 fixture/钩子的文件（pytest 自动加载，无需 import）——按第 10 章包结构，`tests/conftest.py` 放全项目共享 fixture，子目录的 `conftest.py` 放局部共享。

**内置 fixture 三件套**（高频）：

```python
def test_tmp(tmp_path):              # 临时目录（自动清理）
    f = tmp_path / "data.txt"
    f.write_text("hi")
    assert f.read_text() == "hi"

def test_output(capsys):             # 捕获 stdout/stderr
    print("hello")
    captured = capsys.readouterr()
    assert captured.out == "hello\n"

def test_env(monkeypatch):           # 环境变量/属性/字典的临时修改
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setattr(calc, "VERSION", "9.9")
```

> **🔑 机制洞察**：fixture 依赖注入的本质是**参数名即查找键**——pytest 收集测试函数签名，按参数名查 fixture 注册表（`_fixturemanager` 按名字解析）。所以：**fixture 名与参数名必须精确一致**，拼写错误 pytest 会报 "fixture 'x' not found"（好错误信息也是设计）。fixture 可以互相依赖形成图，pytest 自动拓扑排序、缓存结果（同 scope 内只初始化一次）。

### 14.3.4 参数化测试：@pytest.mark.parametrize

数据驱动测试的声明式写法：

```python
import pytest

@pytest.mark.parametrize("value,expected", [
    ("", False),
    ("a" * 100, False),
    ("valid", True),
    ("a-b", False),
])
def test_validate(value, expected):
    assert validate(value) == expected
```

```bash
$ pytest -q
4 passed          # 每个参数组合 = 一个独立测试
```

```python
# 组合参数：两组参数笛卡尔积（衔接 13.3 product 思想）
@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [10, 20])
def test_combine(x, y):
    assert combine(x, y) in (11, 21, 12, 22)   # 4 个组合
```

> **实战建议**：参数化把"同一个断言跑 N 组数据"从 `subTest` 循环升级为**声明式用例**——每个组合独立报告、独立失败、`-k` 可筛选（`pytest -k "validate and 100"` 只跑特定组合）。参数过多时用 `ids=` 给用例命名（失败报告可读）。

### 14.3.5 标记与配置

```python
# 标记：给测试分组/加语义
import pytest

@pytest.mark.slow                      # 自定义标记：慢测试
def test_big_analysis(): ...

@pytest.mark.skipif(sys.version_info < (3, 11), reason="needs 3.11")
def test_new_feature(): ...

@pytest.mark.xfail(reason="known bug #42")   # 期望失败（已知 bug 占位）
def test_known_issue(): ...
```

```bash
$ pytest -m "not slow"                 # 排除慢测试
$ pytest -k "validate"                 # 按名字筛选
$ pytest --durations=5                 # 显示最慢的 5 个测试（性能门禁）
```

```toml
# pyproject.toml（pytest 配置，衔接第 10 章）
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: 标记慢测试"]
addopts = "-q --strict-markers"        # 未注册标记直接报错（防拼写错误）
```

> **实战建议**：`--strict-markers` 强制注册标记（拼错的 `@pytest.mark.slo` 会在收集时报错而不是静默忽略）；`--durations` 是"测试变慢"的监控起点（衔接 14.9 性能剖析）。

#### fixture 进阶：autouse 与参数化 fixture

**`autouse=True`**：无需显式声明，**自动应用于每个测试**——适合"环境准备"（清理全局状态、设置环境变量）：

```python
@pytest.fixture(autouse=True)
def clean_state():
    STATE.clear()               # 每个测试前自动清理全局状态（14.5.3）
    yield
    STATE.clear()               # 测试后再清一次

def test_one():                 # 不用声明依赖，自动生效
    STATE["x"] = 1
def test_two():                 # 也自动是干净环境
    assert "x" not in STATE
```

**参数化 fixture（`params`）**：一个 fixture 产生多组数据，依赖它的每个测试**自动展开为多用例**：

```python
@pytest.fixture(params=["json", "yaml"])
def serializer(request):
    if request.param == "json":
        return json_serializer
    return yaml_serializer

def test_roundtrip(serializer):      # 自动跑 2 次（json / yaml）
    data = {"a": [1, 2]}
    assert serializer.loads(serializer.dumps(data)) == data
```

```bash
$ pytest -q
2 passed    # test_roundtrip[json]、test_roundtrip[yaml]
```

| fixture 特性 | 作用 |
|-------------|------|
| `autouse=True` | 免声明自动应用（环境准备） |
| `params=[...]` | 参数化 fixture（测试自动展开） |
| `request.param` | 访问当前参数值 |
| `scope="module"/"session"` | 跨测试复用（14.3.3） |
| `yield` | 准备/清理分离（第 8 章 with 协议） |

> **实战建议**：`autouse` 是"全局环境纪律"的载体——但**慎用**（隐式依赖会让测试"看不懂为什么环境是干净的"）。参数化 fixture 与 14.3.4 的 `parametrize` 二选一：**数据直接给测试**用 `parametrize`；**fixture 本身有多种实现**（json/yaml 两种序列化器）用 `params`。

---

## 14.4 mock 与打桩

单元测试的目标是"测**我的**逻辑，不测**别人的**（网络、数据库、时钟）"。mock 就是在测试里**替换掉外部依赖**，让被测代码在可控的假环境下运行。

### 14.4.1 何时需要 mock：外部依赖的三种形态

| 依赖形态 | 例子 | mock 的理由 |
|---------|------|------------|
| 网络 | HTTP 请求、邮件、支付 | 慢、不稳定、有副作用、外部不可控 |
| 时间 | `datetime.now()` | 不可复现（14.5.2 的固定时间方案） |
| 随机 | `random`/`uuid` | 不可复现（`seed` 可解决部分） |

```python
# 被测代码：依赖外部 HTTP
def fetch_price(symbol: str) -> float:
    resp = requests.get(f"https://api.example.com/price/{symbol}")
    resp.raise_for_status()
    return resp.json()["price"]
```

测试它而不真发请求——**mock 掉 `requests.get`**。

> **⚠️ 陷阱：只 mock 边界，不 mock 自己的逻辑**。mock 是"替换我调用的外部东西"，不是"替换我自己"。如果测试里 mock 了被测函数**自己**（`patch("mypkg.calc.add")`），那测试测的是空气——这叫"假绿测试"（14.4.4）。

### 14.4.2 unittest.mock：Mock / MagicMock / patch

```python
>>> from unittest.mock import Mock, MagicMock, patch

>>> m = Mock()
>>> m.any_attribute           # 任何属性都能访问（自动创建）
<Mock name='mock.any_attribute' id='...'>
>>> m.method(1, 2)            # 任何调用都返回 Mock
<Mock name='mock.method()' id='...'>
>>> m.method.assert_called_with(1, 2)   # ✅ 调用了且参数对

>>> mm = MagicMock()          # 带魔术方法支持的版本
>>> len(mm), mm[0], str(mm)   # __len__/__getitem__/__str__ 自动可用
(0, <MagicMock ...>, '')
```

`Mock` 是"万能替身"：**任何属性、任何调用都合法**——这既是便利也是危险（拼错属性名不报错！）。`MagicMock` 额外预配置了魔术方法（`__len__`/`__iter__`/`__contains__`...），替换对象/容器时用。

**`patch` 的三种用法**（替换"某模块里的名字"）：

```python
# 用法 1：装饰器
@patch("mypkg.pricing.requests.get")       # 路径 = "使用方模块.名字"！
def test_fetch_price(mock_get):
    mock_get.return_value.json.return_value = {"price": 42.0}
    assert fetch_price("AAPL") == 42.0

# 用法 2：上下文管理器
def test_fetch_price():
    with patch("mypkg.pricing.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"price": 42.0}
        assert fetch_price("AAPL") == 42.0

# 用法 3：patch.object（按对象属性）
def test_fetch_price():
    with patch.object(pricing.requests, "get") as mock_get:
        ...
```

#### ⚠️ patch 的位置：这是 mock 第一陷阱

```python
# ❌ 错误：patch 定义方（requests 模块里），测试无效
@patch("requests.get")                      # 'requests' 是定义方！
def test_fetch_price(mock_get):
    ...                                     # fetch_price 里的 requests.get
                                            # 已经在导入时绑定，patch 不到

# ✅ 正确：patch 使用方（fetch_price 所在模块里）
@patch("mypkg.pricing.requests.get")        # 'mypkg.pricing' 是使用方！
def test_fetch_price(mock_get):
    ...
```

**原理（衔接第 10 章 10.1.2 的绑定语义）**：`mypkg.pricing` 模块执行了 `import requests`，于是 `pricing.requests` 是**该模块命名空间里的一个名字**（指向 requests 模块）。`fetch_price` 内部访问 `requests.get` 时，解析的是 `pricing.requests.get`——所以 patch 必须改 `pricing.requests.get` 这个**查找路径上的名字**。patch `requests.get`（全局模块）不会影响 `pricing` 里已绑定的引用。

> **记忆口诀**：**patch 使用方，不 patch 定义方**——"在谁的地盘上用它，就 patch 谁的名字"。

### 14.4.3 行为编程与断言

```python
from unittest.mock import Mock

# return_value：固定返回值
m = Mock()
m.return_value = 42
m()          # 42

# side_effect：三种形态
# 形态 1：异常
m.side_effect = TimeoutError("timed out")
m()          # 抛 TimeoutError

# 形态 2：序列（依次返回）
m.side_effect = [1, 2, 3]
m(); m(); m()      # 1, 2, 3；第四次抛 StopIteration

# 形态 3：函数（按参数计算）
def fake_get(url):
    return {"price": 42.0} if "AAPL" in url else {"price": 0.0}
m.side_effect = fake_get
```

```python
# 调用断言
m = Mock()
m.fetch("AAPL", timeout=5)
m.fetch.assert_called_once_with("AAPL", timeout=5)   # 精确匹配
m.fetch.assert_called()                              # 至少调用过
m.fetch.call_count                                   # 次数
# 失败信息：显示实际调用记录（好调试）
# AssertionError: expected call not found.
# Expected: fetch('AAPL', timeout=5)
# Actual: fetch('AAPL', timeout=5) —— 但 timeout 是 3？
```

> **实战建议**：`side_effect` 的函数形态是最强工具——可以写"假响应函数"模拟真实服务的多种返回（成功/超时/404），比固定 `return_value` 真实得多。复杂假服务考虑 `responses`/`requests-mock` 库（HTTP 层 mock）或 `VCR.py`（录制回放真实请求）。

### 14.4.4 过度 mock 的代价

mock 是把双刃剑，三个典型反模式：

```python
# 反模式 1：mock 自己（假绿）
@patch("mypkg.calc.add")            # 被测函数自己被替换
def test_add(mock_add):
    mock_add.return_value = 3
    assert calc.add(1, 2) == 3      # 测了个寂寞

# 反模式 2：过度指定（测试与实现耦合）
@patch("mypkg.service.requests.get")
def test_order(mock_get):
    ...                             # mock 断言了"调用了 requests.get 两次"
                                    # 一旦实现改成批量请求 → 测试崩
                                    # 但其实行为没变

# 反模式 3：mock 替代一切（测试失去意义）
# 数据库 mock、文件 mock、时间 mock、连自己的函数都 mock → 测试只验证"mock 被调用了"
```

> **工程影响**：过度 mock 的症状是"**测试在重构时比业务代码先崩**"——测试本应是重构的安全网，结果成了重构的绊脚石。三个解药：(1) 只 mock **真实外部边界**（网络/时钟/随机），DB 测试用真 DB（集成测试层级）；(2) 断言**行为结果**而非**调用细节**；(3) 觉得"必须 mock 才能测"时，回到 14.1.4 的可测试性重构（注入依赖而非 mock 全局）。

#### spec 与 autospec：让 mock 不再是"什么都行"

`Mock` 的"任何属性都能访问"是便利也是陷阱——**拼错属性名不报错**（`mock.requsets.get` 返回一个新 Mock，测试继续跑，最后"假绿"）。`spec`/`autospec` 让 mock **只接受真实对象有的属性**：

```python
>>> from unittest.mock import Mock, MagicMock, create_autospec
>>> import requests

>>> # spec：按对象"形状"限制 mock 的属性
>>> m = Mock(spec=requests.get)              # 只有 requests.get 的属性
>>> m.return_value                            # ✅ 合法（调用结果）
>>> m.status_code                             # ❌ 没有这个属性 → AttributeError
AttributeError: Mock object has no attribute 'status_code'

>>> # create_autospec：自动按签名检查参数
>>> mock_get = create_autospec(requests.get)
>>> mock_get("https://x.com", timeout=10)     # ✅ 参数合法
>>> mock_get("https://x.com", bogus_arg=1)    # ❌ 未知参数 → TypeError
TypeError: unexpected keyword argument 'bogus_arg'
```

| 工具 | 保护 | 适用 |
|------|------|------|
| `Mock()` | 无（任何属性/调用合法） | 简单替身 |
| `Mock(spec=obj)` | 属性白名单 | 防止拼错属性 |
| `create_autospec(func)` | 属性 + **签名校验** | 防"调用参数写错" |
| `MagicMock(spec=...)` | 同上 + 魔术方法 | 替换对象/容器 |

> **实战建议**：mock **真实外部对象**时（`requests`/`datetime`/SDK 客户端），**一律 `spec`/`autospec`**——它们的"严格性"把 mock 的隐患（拼错名、传错参）变成显式错误。只有"完全虚构的替身"（测试里自己设计的假对象）才用裸 `Mock`。

---

## 14.5 测试设计进阶

### 14.5.1 测试数据与工厂

测试需要数据，但"每个测试都手写一坨数据"会让测试又长又脆。两种组织方式：

```python
# 方式 1：fixture 返回数据（pytest 风格）
@pytest.fixture
def user_dict():
    return {"name": "Alice", "email": "alice@example.com", "age": 30}

def test_user_validation(user_dict):
    assert validate_user(user_dict) is None

# 方式 2：工厂函数（参数化变体）
def make_user(**overrides):
    data = {"name": "Alice", "email": "alice@example.com", "age": 30}
    data.update(overrides)               # 覆盖默认值
    return data

def test_user_rejects_bad_email():
    assert validate_user(make_user(email="not-an-email")) is not None
```

> **实战建议**：默认值齐全的**工厂函数**（`make_user(**overrides)`）最实用——测试只写"与默认不同的部分"，可读性最高。数据量大时用 `faker` 库生成假数据；但**测试断言必须用固定值**（faker 随机值会让断言失效，除非只断言结构）。

### 14.5.2 可复现性：固定时间与随机

**时间测试**——`datetime.now()` 使测试不可复现（衔接 13.5.5 的陷阱清单）。两个方案：

```python
# 方案 1：设计上注入时钟（14.1.4 依赖注入）
def is_expired(ts: datetime, now: datetime) -> bool:   # now 从参数进！
    return now > ts + timedelta(days=30)

def test_is_expired():
    now = datetime(2026, 8, 16, tzinfo=timezone.utc)    # 固定 now
    assert is_expired(now - timedelta(days=31), now)
    assert not is_expired(now - timedelta(days=29), now)

# 方案 2：monkeypatch 替换（遗留代码）
def test_expiry(monkeypatch):
    fake_now = datetime(2026, 8, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(mypkg.timeutil, "now", lambda: fake_now)
    ...
```

**随机测试**——`random.seed` 固定（衔接 13.6.4）：

```python
def test_sample_with_seed():
    random.seed(42)                    # 固定种子 → 序列确定
    assert random.sample(range(100), 5) == [81, 14, 3, 94, 35]

# 但注意：seed 是全局状态！测试间会互相干扰（14.5.3）
# 更稳：monkeypatch 或 fixture 内 seed + 恢复
```

> **⚠️ 陷阱**：`random.seed` 改的是**全局**随机状态——一个测试 seed 了，后面的测试"随机性"就变了（顺序相关）。规范：fixture 里 seed 并在 teardown 恢复，或直接让被测函数**接收随机源**（依赖注入的又一例）。

### 14.5.3 测试隔离与顺序无关性

**测试必须互相独立、顺序无关**——"单独跑通过、一起跑失败"是最常见的测试 bug 形态：

```python
# ❌ 顺序相关：测试 A 改了全局状态，测试 B 依赖 A 先跑
STATE = {}

def test_a_sets_state():
    STATE["x"] = 1

def test_b_reads_state():            # 单独跑 B 会失败！
    assert STATE["x"] == 1

# ✅ 隔离：每个测试自给自足
def test_b_independent():
    STATE.clear()                    # 或 fixture 里重置
    STATE["x"] = 1
    assert STATE["x"] == 1
```

污染源清单（衔接第 10 章模块单例 10.4.2）：

| 污染源 | 隔离手段 |
|--------|---------|
| 模块级全局变量 | fixture 里重置（`monkeypatch`） |
| 环境变量 | `monkeypatch.setenv`（自动恢复） |
| 文件/目录 | `tmp_path`（每个测试独立临时目录） |
| 数据库 | 事务回滚 / 每测试独立 schema |
| 随机/时间 | seed + 恢复 / 注入时钟 |
| 日志配置 | `logging` 配置是全局的（13.9）——fixture 保存恢复 |

```python
# pytest 的 -p no:randomly 或插件 pytest-randomly 控制顺序：
# 默认 pytest 按文件顺序执行——顺序无关是【你】的责任，不是框架的
```

> **工程影响**：并行测试（`pytest-xdist`）的前提就是**隔离**——能并行的测试必然顺序无关。隔离做不好，xdist 一开就红。规则：**每个测试的 setUp 必须把环境恢复到"全新"状态**。

### 14.5.4 测试即规格

好的测试是**可执行的规格说明书**——测试名读起来就是需求：

```python
# ❌ 模糊的测试名
def test_1():
    assert f(1) == 2

# ✅ 规格式测试名：名字即需求
def test_discount_applies_when_total_over_100():
    assert calculate_total([60, 50]) == 99.0        # 100+ 打 9 折

def test_no_discount_below_threshold():
    assert calculate_total([60, 30]) == 90.0

def test_discount_rounds_to_cents():
    assert calculate_total([33.34] * 3) == 90.018 → pytest.approx(90.02)
```

> **实战建议**：写测试时问自己"如果新同事只看测试名和断言，能不能理解这个函数的行为？"——能，测试就是文档；不能，重写测试名/拆分断言。**断言即契约**：每个 `assert` 都是对"行为边界"的声明，测试集合就是函数行为的完整规格。这也是 14.1.1"活的文档"的实现细节。

---

## 14.6 覆盖率与质量门禁

### 14.6.1 coverage.py：行覆盖与分支覆盖

覆盖率（coverage）回答："测试跑过的代码占多少？"——`coverage.py` 是事实标准（`pytest-cov` 是 pytest 集成）：

```bash
$ pip install pytest-cov
$ pytest --cov=mypkg --cov-report=term-missing
---------- coverage: platform win32, python 3.14 ----------
Name              Stmts   Miss  Cover   Missing
-----------------------------------------------
mypkg/calc.py        12      3    75%    8-10
mypkg/utils.py       20      0   100%
-----------------------------------------------
TOTAL               32      3    91%
```

| 列 | 含义 |
|----|------|
| Stmts | 可执行语句数 |
| Miss | 未执行到的语句数 |
| Cover | 行覆盖率（执行到的 / 总语句） |
| Missing | 未覆盖的行号（`8-10`）——**直接告诉你该补什么测试** |

**分支覆盖**（`--cov-branch`）比行覆盖更严格：`if` 的两个分支都要跑到：

```python
def classify(n):
    if n > 0:        # 行覆盖：执行到 if 就算覆盖
        return "pos"
    return "neg"     # 分支覆盖：还要跑到 else 分支

# 只有 test_classify(1) → 行覆盖 100%，分支覆盖 50%（neg 没跑到）
$ pytest --cov=mypkg --cov-branch
mypkg/calc.py    ...   branch=2, part-branches=1  →  分支覆盖 50%
```

> **🔑 机制洞察**：`coverage.py` 的实现原理是 **trace 钩子**（`sys.settrace`，每行字节码执行时回调）——这带来两个推论：(1) 它**拖慢测试**（每条语句都有回调开销）；(2) C 扩展代码测不到（trace 只覆盖 Python 层）。`--concurrency` 参数可配合多线程/多进程测试。

### 14.6.2 覆盖率的真相

> **⚠️ 陷阱**：**100% 覆盖 ≠ 无 bug**。覆盖率只回答"跑没跑到"，不回答"测得好不好"：

```python
def divide(a, b):
    if b == 0:
        raise ZeroDivisionError()
    return a / b

# 一个测试就能 100% 覆盖：
def test_divide():
    assert divide(4, 2) == 2        # 覆盖了两行 + 分支的"非零"路径

# 但 bug 依然存在（没测 b==0 的行为、没测负数、没测类型错误）
assert divide(1, 0)                 # ZeroDivisionError 行为没验证
```

**覆盖率的正确解读**：

- 覆盖率是**下限**不是**目标**：80% 的精心测试 > 100% 的凑数测试；
- "未覆盖的行"是**明确的信号**（那里有代码没被验证——要么补测试，要么删代码）；
- 低覆盖率的反向价值：告诉你**哪些代码是死代码或没被测试保护的重灾区**。

```python
# 哪些代码不值得凑覆盖率：
# 1. 框架胶水（模板渲染、ORM 配置）
# 2. 纯声明（常量表、dataclass 字段）
# 3. 第三方调用的一行转发
# 规则：值得测的是【逻辑】，不是【仪式】
```

> **实战建议**：覆盖率的目标设在 **80–90%**（行覆盖），关键模块（核心算法、金额计算）要求 100%——用 `# pragma: no cover` 显式豁免"不值得测"的行（如 `if __name__ == "__main__":` 入口），让"豁免"成为**有意的声明**而不是"漏测的遮羞布"。

### 14.6.3 质量门禁：CI 中的测试策略

测试进入 CI（持续集成）后，"跑一遍"变成"**不达标就拦下**"：

```bash
# 门禁 1：覆盖率下限（低于 80% 构建失败）
$ pytest --cov=mypkg --cov-fail-under=80

# 门禁 2：测试耗时预算（慢测试是隐患）
$ pytest --durations=10           # 最慢的 10 个 —— 定期清理
$ pytest -m "not slow"            # CI 快速通道跑非慢测试

# 门禁 3：警告升级（衔接 14.8.3）
$ pytest -W error                 # DeprecationWarning 直接失败
```

**测试金字塔在 CI 的落地**：

| CI 阶段 | 跑什么 | 频率 |
|---------|--------|------|
| 提交时（pre-commit） | 相关模块的单测 + lint | 每次提交 |
| PR 检查 | 全量单测 + 覆盖率门禁 | 每次 PR |
| 合并后 | 集成测试 + 端到端（慢） | 每次合并 |
| 发布前 | 全量 + 性能基准（14.9） | 发布 |

> **工程影响**：质量门禁的价值不在"挡人"，而在"**让失败成为显式信号**"——没有门禁时，测试失败被忽略（"明天再修"变成永远）；有门禁时，红构建当天修复。**门禁要少而准**：两条覆盖率 + 一条耗时 + 一条警告，超过五条就会开始有人"绕过门禁"（`--no-cov`、`skipif` 滥用）。

#### coverage 配置实战

覆盖率配置（豁免规则、来源排除）可以沉淀在配置文件里，而不是每次命令行传参：

```toml
# pyproject.toml
[tool.coverage.run]
source = ["mypkg"]                     # 只统计 mypkg（排除测试本身）
omit = ["mypkg/version.py"]            # 排除生成文件

[tool.coverage.report]
exclude_lines = [                      # 豁免规则：这些行不计入"未覆盖"
    "pragma: no cover",                # 显式豁免标记
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
fail_under = 80                        # 覆盖率下限（等价 --cov-fail-under）
```

```python
# 代码里显式豁免"不值得测"的行（14.6.2）
def load_defaults():
    if os.path.exists("config.json"):      # pragma: no cover  # 环境分支
        ...
```

```bash
$ pytest --cov=mypkg                     # 自动读 [tool.coverage.run] 配置
$ coverage report                        # 生成报告（无需重复传参）
```

> **实战建议**：把覆盖率配置写进 `pyproject.toml`（第 10 章的统一配置入口）——**豁免是声明，不是漏测**：`pragma: no cover` 标注的每一行都是"我故意不测，理由明确"。审查覆盖率报告时重点看**未标注的 Missing 行**——那才是真的没测到。

---

## 14.7 调试：pdb 与断点

测试告诉你"哪里错了"，调试器告诉你"**错的时候发生了什么**"。本章后半段进入调试世界——这是"肘后备急"最实战的部分。

### 14.7.1 从 print 到断点

```python
# print 调试的四个局限：
# 1. 要改代码（加 print → 跑 → 删 print → 再跑）
# 2. 只能看"打印的瞬间"，看不到调用栈、看不到调用者
# 3. 生产环境不能加（要改代码 = 要重新部署）
# 4. 忘了删的 print 污染输出（14.3 capsys 都救不了你）
```

**`breakpoint()`（3.7+，PEP 553）**：内置函数，调用即进入调试器：

```python
def process(data):
    result = []
    for item in data:
        breakpoint()          # 执行到这里暂停，进入 pdb
        result.append(item * 2)
    return result
```

```bash
$ python app.py
> app.py(5)process()
-> result.append(item * 2)
(Pdb) item                   # 看当前变量
3
(Pdb) p data                 # 打印表达式
[1, 2, 3]
(Pdb) c                      # 继续到下一个断点
```

`PYTHONBREAKPOINT` 环境变量控制 `breakpoint()` 的行为：

```bash
$ PYTHONBREAKPOINT=pdb.set_trace python app.py   # 默认（pdb）
$ PYTHONBREAKPOINT=0 python app.py               # 禁用（生产环境！）
$ PYTHONBREAKPOINT=ipdb.set_trace python app.py  # 换成 ipdb（更好用的第三方调试器）
```

> **🔑 机制洞察**：`breakpoint()` 等价 `sys.breakpointhook()` → 默认调用 `pdb.set_trace()`。它是**可配置的钩子**——生产代码里留着 `breakpoint()` 不删？设 `PYTHONBREAKPOINT=0` 就完全禁用（不会崩、不会有副作用）。这是"代码里留调试入口"的安全姿势，比裸 `import pdb; pdb.set_trace()` 干净。

### 14.7.2 pdb 命令全解

进入 pdb 后（`(Pdb)` 提示符），核心命令：

| 命令 | 全称 | 作用 |
|------|------|------|
| `n` | next | 单步（不进入函数） |
| `s` | step | 单步（**进入**函数） |
| `c` | continue | 继续到下一个断点/结束 |
| `r` | return | 执行到当前函数返回 |
| `p expr` / `pp expr` | print | 打印表达式（`pp` 美化） |
| `l` | list | 显示当前位置附近源码 |
| `w` | where | 打印调用栈 |
| `u` / `d` | up / down | 栈帧上/下移动（看调用者变量！） |
| `b` | break | 设置断点：`b file.py:10`、`b 10`、条件 `b 10, x > 5` |
| `cl` | clear | 清除断点 |
| `!stmt` | — | 执行 Python 语句（`!x = 100` 修改变量！） |
| `q` | quit | 退出调试器 |

```python
def outer():
    x = 10
    inner()

def inner():
    y = 20
    breakpoint()      # 停在这里
    return y + x      # x 是 outer 的局部变量——pdb 里看得到吗？
```

```
(Pdb) w                    # 调用栈：当前在最内层
  app.py(4)outer()
-> inner()
> app.py(9)inner()
-> return y + x
(Pdb) p y                  # 当前帧：inner 的局部
20
(Pdb) u                    # 上移一帧 → outer
> app.py(4)outer()
(Pdb) p x                  # 看到 outer 的局部变量！
10
(Pdb) d                    # 回到 inner
> app.py(9)inner()
```

> **🔑 调试洞察**：`u`/`d`（栈帧切换）是 pdb 最被低估的能力——"内部函数报错，想看看调用者传了什么"时，`u` 一上去就看到。pdb 里 `!` 可以执行任意语句（改变量、调函数）——调试器是"暂停的时间机器"，你可以**修改状态后继续跑**，验证猜想。

#### IDE 调试器：pdb 的图形化兄弟

VS Code / PyCharm 的调试器不是另一个工具，而是 **pdb 的图形化前端**——同一套机制（断点、单步、栈帧、变量），只是鼠标操作：

| 概念 | pdb 命令 | IDE 操作 |
|------|---------|---------|
| 断点 | `b app.py:10` | 点行号左侧（红点） |
| 单步不进入 | `n` | F10 |
| 单步进入 | `s` | F11 |
| 继续 | `c` | F5 |
| 看变量 | `p x` | 调试面板变量区 |
| 看栈 | `w` / `u` / `d` | 调用堆栈面板点击 |
| 条件断点 | `b 10, x > 5` | 断点右键"表达式" |

```python
# IDE 调试时也可以回到 pdb：
# breakpoint() 在 VS Code 里默认触发 IDE 调试器（调试会话中）
# PYTHONBREAKPOINT 可强制指定：PYTHONBREAKPOINT=pdb.set_trace 回文本调试器
```

> **实战建议**：本地开发用 IDE 调试器（可视化效率高）；**服务器/CI/无 GUI 环境用 pdb**（`breakpoint()` 进 pdb 是唯一选项）。两者共享同一套"调试心智"（断点/单步/栈/变量），学会 pdb 的文本命令，IDE 调试器自然上手——命令名与快捷键一一对应。ipdb（`pip install ipdb`）是 pdb 的增强版（补全/高亮），值得作为默认 `PYTHONBREAKPOINT`。

### 14.7.3 post-mortem 调试

**post-mortem（事后解剖）**：程序崩溃后进入调试器，**在崩溃现场**检查状态：

```bash
# 方式 1：python -m pdb 运行脚本 —— 崩溃自动进入
$ python -m pdb app.py
Traceback (most recent call last):
  File "app.py", line 5, in <module>
    result = data["key"]        # ← 崩溃现场
KeyError: 'key'
> app.py(5)<module>()
-> result = data["key"]
(Pdb) p data                   # 在崩溃点检查所有变量！
{}

# 方式 2：代码里捕获后进入（pdb.pm）
import pdb
try:
    main()
except Exception:
    pdb.pm()                   # post-mortem：停在异常帧
```

**`faulthandler`（3.3+）**——Python 层之外的崩溃诊断（段错误、C 扩展崩溃、死锁）：

```bash
$ python -X faulthandler app.py          # 崩溃时打印 Python 栈（含 C 帧）
$ PYTHONFAULTHANDLER=1 python app.py     # 环境变量形式
```

```python
# 死锁诊断：超时 dump 栈
import faulthandler, threading
faulthandler.dump_traceback_later(10, exit=True)   # 10 秒后打印所有线程栈并退出
```

> **实战建议**：`PYTHONFAULTHANDLER=1` 是**所有生产服务都应该默认开**的（代价极小）——进程异常死亡（段错误、被 kill）时，至少能拿到 Python 层的栈，知道死在哪一行。配合 `logging`（13.9）把栈写进日志，崩溃可复盘。

### 14.7.4 调试方法论

工具有了，方法论决定效率。四条铁律：

**1. 先复现，再定位**：不能复现的 bug 无法调试（14.1.3 的"能复现就好了一半"）。最小复现（MRE）：把问题缩小到"最少代码 + 最小输入"。

**2. 二分定位**：不是逐行读代码，而是**删一半**——注释掉一半逻辑，看 bug 还在不在；在的那一半继续二分。O(n) 逐行 → O(log n) 二分。

**3. 先查数据，再查逻辑**：80% 的 bug 是"输入/状态不符合预期"而非"逻辑写错"。`p` 打印变量、`u` 看调用者传参——先确认"数据对不对"，再怀疑"算法对不对"。

**4. 写下来的橡皮鸭**：把"我以为的流程"写下来，和"实际跑的流程"逐行对照（`l` 看源码 + `n` 单步）——差异处就是 bug。

```python
# 调试组合拳（测试 + 日志 + 调试器）：
# 1. 测试给出失败用例（14.3）——复现
# 2. logging 分级输出（13.9）——生产环境的"远程调试"
# 3. pdb 断点——本地"暂停时间"看现场
# 4. 修好后：把复现用例固化为测试（防止回归！）
```

> **工程影响**：**调试的产出不只是修复，而是回归测试**——"修 bug 不写测试 = 同一个 bug 会再回来"。专业调试流程：复现（测试红）→ 定位（调试器）→ 修复 → 测试绿 → **测试留下**。这就是测试与调试的闭环。

#### 一个完整的 pdb 调试走查

把方法论串起来。场景：`dedupe` 函数"去重但顺序错乱"：

```python
# app.py
def dedupe(items):
    result = []
    for item in items:
        if item not in result:      # 疑似问题点
            result.append(item)
    return result

items = [3, 1, 3, 2, 1, 3]
breakpoint()                        # ① 在调用前打断点
print(dedupe(items))                # 期望 [3, 1, 2]，实际 [3, 1, 2]？→ 先跑一次
```

```
$ python app.py
> app.py(10)<module>()
-> print(dedupe(items))
(Pdb) n                        # ② 单步进入 print 调用前
> app.py(10)<module>()
-> print(dedupe(items))
(Pdb) s                        # ③ step 进入 dedupe
--Call--
> app.py(2)dedupe()
-> def dedupe(items):
(Pdb) l                        # ④ 看源码
  1  def dedupe(items):
  2      result = []
  3      for item in items:
  4          if item not in result:
  5              result.append(item)
  6      return result
(Pdb) n                        # ⑤ 单步走循环
> app.py(3)dedupe()
-> for item in items:
(Pdb) n
> app.py(4)dedupe()
-> if item not in result:
(Pdb) p items, result          # ⑥ 看状态：items=[3,1,3,2,1,3] result=[]
(Pdb) n
> app.py(5)dedupe()
-> result.append(item)
(Pdb) p item                   # item=3，第一次遇到 → 加入
3
(Pdb) c                        # ⑦ 继续到结束，验证输出
[3, 1, 2]                      # 咦？没 bug？——因为"顺序错乱"需要更大的输入
```

**关键动作**：这个案例的正确调试姿势是**先复现**——用测试固定输入（14.7.4 方法论第 1 条）。真正的问题场景是"去重但希望保留**最后一次**出现的位置"或"顺序依赖输入结构"。用条件断点缩小范围：

```
(Pdb) b app.py:4, item == 3    # 条件断点：只在 item==3 时停
(Pdb) c                        # 跑到第一个 item==3
> app.py(4)dedupe()
-> if item not in result:
(Pdb) p result                 # 看到 result 当前状态
[3, 1, 2]
```

> **🔑 调试洞察**：这个走查演示了 pdb 的完整节奏——`l` 看源码定位行号、`n`/`s` 控制步进、`p` 随时看状态、条件断点只在感兴趣的输入停下、`c` 快速跳过无关循环。**调试器的效率 = 用条件断点把"逐行盯"变成"只在可疑处停"**。

---

## 14.8 traceback 与异常诊断

崩溃信息（traceback）是 Python 给调试者的第一份情报——**会读 traceback 的人 5 分钟定位，不会读的人对着报错发呆**。

### 14.8.1 读懂 traceback

```python
def parse(data):
    return json.loads(data)

def load_config(path):
    with open(path) as f:
        return parse(f.read())

load_config("missing.json")
```

```
Traceback (most recent call last):
  File "app.py", line 9, in <module>
    load_config("missing.json")
  File "app.py", line 6, in load_config
    return parse(f.read())
  File "app.py", line 2, in parse
    return json.loads(data)
  File "C:\Python314\Lib\json\__init__.py", line 346, in loads
    return _default_decoder.decode(s)
  File "C:\Python314\Lib\json\decoder.py", line 340, in decode
    raise JSONDecodeError("Extra data", s, end)
json.decoder.JSONDecodeError: Extra data: line 1 column 4 (char 3)
```

**阅读顺序**（关键认知）：

```
① 最底部一行：异常类型 + 消息   ← 先看这里！"发生了什么"
   json.decoder.JSONDecodeError: Extra data ...
② 从下往上：异常"向上传播"的路径  ← 每帧 = 一层调用
   json 内部 → parse → load_config → <module>
③ 每帧的 File/line/代码行：这层的"现场"（函数、行号、源码）
④ 最上面是异常"最初抛出"的地方（json 内部），
   但【你的代码】在中间层——真正要修的是 load_config 或 parse 的调用方式
```

> **🔑 调试洞察**：初学者最容易犯的错是"只看最后一行"或"只看第一帧"。正确读法：**底部看类型，往上找"第一帧属于我自己的代码"**——`parse`/`load_config` 是你的代码，json 内部是标准库。修复点几乎总在"你自己的最内层帧"。

**异常链在 traceback 里的呈现**（衔接第 8 章 8.3）：

```
Traceback (most recent call last):
  File "app.py", line 3, in <module>
    raise KeyError("missing key") from ValueError("bad data")
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
KeyError: 'missing key'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
```

`from` 链会显示 **"direct cause"**；隐式链（`__context__`）显示 **"During handling of the above exception"**。第 8 章讲过用 `from None` 切断链——traceback 里就能看到切断后的效果（只剩一层）。

### 14.8.2 traceback 模块与全局钩子

```python
import traceback

try:
    main()
except Exception:
    # 把完整 traceback 字符串化（记录到日志/文件/告警）
    tb_text = traceback.format_exc()     # 多行字符串
    log.error("crash:\n%s", tb_text)

    # 或者拿结构化帧列表（程序化处理）
    for frame in traceback.extract_tb(sys.exc_info()[2]):
        print(frame.filename, frame.lineno, frame.name)
```

**`sys.excepthook`**：未捕获异常的全局钩子——生产环境把崩溃自动上报：

```python
import sys, logging

def excepthook(exc_type, exc_value, exc_tb):
    logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

sys.excepthook = excepthook        # 之后任何未捕获异常都走这里

raise ValueError("boom")           # 不会打印默认 traceback，而是进日志
```

> **实战建议**：生产服务标配 `excepthook`（崩溃进日志/告警系统）；**测试里慎用**——pytest 捕获未处理异常有自己的机制，全局 hook 会干扰（用 `pytest` 的 `--tb=long` 控制展示而非改 hook）。`traceback.format_exc()` 在 except 块里是"把现场存下来"的标准姿势（配合 13.9 日志）。

### 14.8.3 warnings 的调试价值

警告（`DeprecationWarning` 等）是"还没崩，但快崩了"的预告——**CI 里把警告升级为错误**，提前抓住弃用：

```bash
# 把警告当错误：任何 DeprecationWarning 都会失败
$ pytest -W error
$ python -W error::DeprecationWarning app.py

# 环境变量形式（部署/CI 通用）
$ PYTHONWARNINGS=error::DeprecationWarning python app.py
```

```python
# 只看某个模块的警告
$ python -W "error::DeprecationWarning:mypkg" app.py
```

| 场景 | 命令 |
|------|------|
| 全部警告变错误（CI 铁腕） | `-W error` |
| 只看弃用警告 | `-W error::DeprecationWarning` |
| 忽略第三方库的噪音警告 | `-W "ignore::DeprecationWarning:requests"` |
| 打印警告来源（谁发的） | `-W always`（默认只显示一次） |

> **⚠️ 陷阱**：**`DeprecationWarning` 默认是"静默"的**（只显示一次，`__main__` 之外默认忽略）——这是 Python 的设计：不让库的弃用警告打扰普通用户（PEP 565）。但开发者/CI 必须主动 `-W error::DeprecationWarning` 把它暴露出来。忽略 = 欠技术债：3 个版本后 API 被删，你的代码"突然"崩。

### 14.8.4 日志驱动调试

生产环境没有 pdb——**日志是唯一的"远程调试器"**（衔接 13.9 全套）：

```python
# 调试会话的正确姿势：动态提级，而不是改代码
# 1. 代码里留好 DEBUG 级日志（13.9.4 的惰性格式化：%s 零开销）
logger.debug("processing %s items for user=%s", len(items), user_id)

# 2. 生产排查时动态开启（无需改代码/重启）
$ python -c "
import logging, myapp
logging.getLogger('myapp').setLevel(logging.DEBUG)
myapp.run()"                     # 或通过配置中心/环境变量控制

# 3. 关键路径的"日志标记"：进入/退出/异常
logger.info("start processing order=%s", order_id)
try:
    ...
except Exception:
    logger.exception("order=%s failed", order_id)   # 自动带 traceback！
```

> **工程影响**："日志驱动调试"的正确姿势是**代码里预埋分级日志**（`debug`/`info`/`exception`），排查时**提升级别**而非**补打印**——因为生产改代码要重新发布，而日志级别可以在运行时调。`logger.exception`（13.9.4 提过）在 except 块内自动附带 traceback——这就是 14.8.2 的 `format_exc` 的日志版。日志与调试器互补：**开发期用 pdb 看现场，生产期用日志还原现场**。

---

## 14.9 性能剖析入门：找到"慢在哪"

"程序慢"是另一种 bug。优化的第一铁律：**先测，再优化**——凭感觉优化的代码 90% 白费（优化的不是热点）。`cProfile` 回答"**时间花在哪个函数**"，`timeit` 回答"**这段代码多快**"。

### 14.9.1 cProfile：函数级剖析

```bash
$ python -m cProfile -s cumulative app.py
         1000004 function calls in 1.234 seconds

   Ordered by: cumulative time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    1.234    1.234 app.py:1(<module>)
  1000000    0.800    0.000    0.800    0.000 app.py:5(process_item)
  1000000    0.200    0.000    0.300    0.000 app.py:10(validate)
  1000000    0.100    0.000    0.100    0.000 {built-in method builtins.len}
```

| 列 | 含义 |
|----|------|
| ncalls | 调用次数 |
| **tottime** | **函数自身的耗时**（不含子调用）——找"自己慢"的函数 |
| **cumtime** | 含所有子调用的累计耗时——找"整体重"的函数 |
| percall | 每次调用平均 |

**解读方法**：

1. 按 `cumtime` 排序（`-s cumulative`）找**总耗时最大**的函数；
2. 看它的 `tottime`：`tottime` 大 → 函数**自己**慢（算法问题）；`tottime` 小、`cumtime` 大 → 慢在**子调用链**（往下钻）；
3. 找 `ncalls` 异常大的（百万次调用的小函数往往是大头——"调用次数"本身可能就是问题）。

```python
# 代码内剖析（只剖析关键段）
import cProfile, pstats, io

profiler = cProfile.Profile()
profiler.enable()
result = expensive_function()
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats("cumulative").print_stats(10)   # 前 10 名
```

### 14.9.2 timeit 微基准的规范姿势

`timeit` 测"**一小段代码**"（衔接第 13 章各处的基准）：

```python
>>> import timeit
>>> # number：重复次数；repeat：重复几轮取最优
>>> timeit.timeit("'-'.join(map(str, range(100)))", number=100_000)
0.35
>>> timeit.repeat("'-'.join(map(str, range(100)))", number=100_000, repeat=5)
[0.35, 0.34, 0.36, 0.35, 0.34]      # 取 min：消除系统噪声
```

**规范姿势**：

```python
>>> # 1. 用函数+默认参数消除全局查找开销
>>> def test_join():
...     return "-".join(map(str, range(100)))
>>> timeit.timeit(test_join, number=100_000)      # 传函数而非字符串
0.28        # 比字符串形式快（无 globals 查找）

>>> # 2. 多轮取最小（min），别取平均——平均值被 GC/系统噪声污染
>>> min(timeit.repeat(test_join, number=100_000, repeat=7))
0.27

>>> # 3. 对比测试：两个实现用同一套参数
>>> def test_f_string():
...     return ",".join(f"{i}" for i in range(100))
>>> min(timeit.repeat(test_f_string, number=100_000, repeat=7))
0.31        # 对比结论：join+map 略快于生成器+f-string（本例）
```

> **⚠️ 陷阱**：
> - `timeit` 测的是"干净环境"——真实代码有缓存、GC、并发，**微基准结果 ≠ 实际性能**；
> - 不要优化"每个调用省 1µs 但只调 10 次"的代码——优化**热点**（cProfile 找到的）；
> - 数字小到噪声级别时（<10µs），放大 `number`（测 10^6 次）再除。

### 14.9.3 剖析结果解读与优化路线

```python
# 典型剖析故事：报表生成慢
# cProfile 结果：cumtime 最大的是 generate_report
#   tottime 很小 → 慢在子调用
#   钻进去：format_rows 的 cumtime 大、tottime 大
#           → format_rows 里是逐单元格 f-string → 算法/实现问题

# 优化路线（按性价比排序）：
# 1. 算法/数据结构：O(n²) → O(n log n)（第 3 章 dict/set 查找）
# 2. 减少调用次数：缓存（lru_cache，13.4.2）、批量（executemany，13.8.1）
# 3. 惰性化：延迟计算、短路（itertools，13.3）
# 4. 微优化：f-string、局部变量、避免属性链 —— 最后才做！
```

> **工程影响**：优化的黄金流程 = `cProfile` 找热点 → `timeit` 验证假设 → 改 → **重新剖析确认**。改完不重测 = 白改（可能更慢）。本章只到 `cProfile` 入门：内存剖析（`tracemalloc`）、C 扩展、`dis` 字节码级、JIT 类工具（`numba`）留给第 15 章。

#### 内存剖析预告：tracemalloc（第 15 章深挖）

"内存涨个不停"是另一类性能问题。`tracemalloc`（3.4+）能定位**哪行代码分配了多少内存**：

```python
>>> import tracemalloc
>>> tracemalloc.start()                    # 开始跟踪（有性能开销，仅诊断时用）
>>> data = [str(i) * 100 for i in range(100_000)]
>>> snapshot = tracemalloc.take_snapshot() # 当前内存快照
>>> top = snapshot.statistics("lineno")    # 按"分配位置"统计
>>> for stat in top[:3]:
...     print(stat)
/path/app.py:3: size=9.8 MiB, count=100000, average=103 B   # ← 第 3 行分配了 9.8MB
```

```python
# 内存增长排查：对比两个时刻的快照
tracemalloc.start()
before = tracemalloc.take_snapshot()
run_workload()
after = tracemalloc.take_snapshot()
for diff in after.compare_to(before, "lineno")[:5]:
    print(diff)          # 增长最多的代码位置
```

> **实战建议**：`tracemalloc` 是"内存泄漏/内存暴涨"的第一工具——配合 `PYTHONTRACEMALLOC=N`（启动即跟踪）在生产复现。它的机制是**分配钩子**（`PyMem` 层拦截），开销显著，只用于诊断会话。第 15 章将结合 `gc` 模块、`objgraph`、C 扩展内存（`pymalloc`）完整展开。

---

## 14.10 doctest：文档即测试

### 14.10.1 doctest 机制

`doctest` 从 **docstring 里的 `>>>` 示例**提取测试并执行——本系列教案全文都是 REPL 风格（`>>>`），正是 doctest 的语法：

```python
def add(a, b):
    """返回两数之和。

    >>> add(1, 2)
    3
    >>> add(-1, 1)
    0
    """
    return a + b

if __name__ == "__main__":
    import doctest
    doctest.testmod()          # 执行 docstring 里的示例并比对输出
```

```bash
$ python mymod.py -v           # 详细模式
Trying:
    add(1, 2)
Expecting:
    3
ok
```

机制：`doctest` 解析 docstring，把 `>>>` 后的表达式用 `compile` 编译执行，把**实际输出**与 `期望输出` 逐字符比较。它检验的正是"文档示例没有过期"——**文档里的例子一定是真的**。

### 14.10.2 适用场景与局限

```python
# ⚠️ 陷阱 1：浮点输出（第 3 章精度）
def div(a, b):
    """>>> div(10, 3)
    3.3333333333333335     ← 不同平台可能不同！用 +ELLIPSIS 或 doctest 容差
    """
    return a / b

# ⚠️ 陷阱 2：字典/集合输出顺序（3.7+ 保序但集合无序）
def make():
    """>>> make()
    {'a': 1, 'b': 2}        ← 稳定（dict 保序）
    """
    return {"a": 1, "b": 2}

# ⚠️ 陷阱 3：I/O 副作用、随机、时间——docstring 示例无法 mock
# 定位：doctest 是"示例的验证器"，不是测试主力
```

| 定位 | 说明 |
|------|------|
| ✅ 适合 | 纯函数的简单示例、API 文档演示、教学文档 |
| ❌ 不适合 | 复杂逻辑、依赖/副作用、需要 fixture/mock 的测试 |
| 定位 | **文档质量工具**（示例不骗人），**不是**测试框架替代品 |

> **实战建议**：doctest 的黄金用法是"**给公开 API 写 1–3 个最小示例**"（顺带当文档）；复杂行为交给 pytest（14.3）。一个函数 docstring 里有"太多 doctest"通常是坏味道——说明例子在替代真测试。

### 14.10.3 与 pytest 集成

pytest 原生支持 doctest——**文档示例也进测试套件**：

```bash
$ pytest --doctest-modules mypkg/      # 检查所有模块的 docstring 示例
$ pytest --doctest-modules --doctest-continue-on-failure   # 一个失败不中断
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--doctest-modules"          # 默认开启
```

```python
# doctest 里的容差/标记（pytest 也支持）
def div(a, b):
    """>>> div(10, 3)  # doctest: +ELLIPSIS
    3.3333...
    """
    return a / b
```

> **实战模式**：完整测试组合拳 = pytest（单元/集成/fixture/mock）+ `--doctest-modules`（文档示例验证）+ coverage 门禁（14.6）+ CI 警告升级（14.8.3）。这套组合覆盖了"逻辑正确、文档可信、覆盖可查、弃用暴露"四个维度。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 测试价值 | 回归安全网 / 重构勇气 / 活的文档；变更成本曲线被测试压平 |
| 测试金字塔 | 单元（多快稳）→ 集成 → 端到端（少慢脆）；70%+ 单测打底 |
| TDD | 红灯 → 绿灯 → 重构；是**设计工具**（逼出接口/边界/依赖） |
| 可测试性 | 纯函数优先、依赖注入、边界分离——"难测"是设计信号 |
| unittest | `TestCase` + 断言方法（`assertAlmostEqual` 处理浮点）；`setUp`/`tearDown`/`setUpClass`；每方法独立实例；`assertRaises`/`subTest`/`skip` |
| pytest | 函数即测试 + 裸 assert；**AST 断言重写**（import 钩子实战）；fixture 依赖注入（`yield`/scope/conftest/`tmp_path`）；`parametrize`；标记与 `-k` |
| mock | 只 mock 外部边界（网络/时间/随机）；**patch 使用方而非定义方**（第 10 章绑定语义）；`side_effect` 三形态；过度 mock = 假绿测试 |
| 测试设计 | 工厂函数造数据；注入时钟/seed 保可复现；隔离与顺序无关；**测试名即规格** |
| 覆盖率 | `pytest --cov`/分支覆盖；**100% ≠ 无 bug**（下限不是目标）；80–90% + 显式豁免 |
| 质量门禁 | `--cov-fail-under`、`--durations`、`-W error`；门禁少而准 |
| pdb | `breakpoint()`（3.7+/`PYTHONBREAKPOINT`）；n/s/c/p/w/u/d/!；post-mortem（`python -m pdb`/`pdb.pm`）；`faulthandler` 抓段错误/死锁 |
| 调试方法论 | 先复现 → 二分定位 → 先查数据再查逻辑；修复后固化为回归测试 |
| traceback | 底部看类型、往上找"自己的最内层帧"；`format_exc`/`sys.excepthook`；`-W error` 抓弃用 |
| 日志驱动调试 | 预埋分级日志、排查时提级不改码；`logger.exception` 自动带栈 |
| cProfile/timeit | 先测再优化；`tottime`（自己慢）vs `cumtime`（整体重）；`repeat` 取 min |
| doctest | docstring 示例即测试；验证"文档不骗人"；pytest `--doctest-modules` 集成 |

---

#### 练习 14

**第 1–3 题：验证理解（预测/解释）**

1. 解释：`self.assertEqual(0.1 + 0.2, 0.3)` 为什么可能失败？应该用什么断言？`assertEqual` 与裸 `assert` 在测试中的行为差异是什么？

2. 预测：下面的 pytest 测试会输出什么失败信息？为什么 pytest 能显示两侧值而普通 `assert` 不能？

```python
def test_mystery():
    assert {"a": 1, "b": 2} == {"a": 1, "b": 3}
```

3. 解释：`@patch("requests.get")` 为什么经常无效？正确写法是什么？这背后是第 10 章的哪个绑定语义？

**第 4–6 题：动手实战**

4. 用 unittest 给 `calc.py`（含 `add`/`div`/`parse_int`）写测试：正常值、边界、异常（`assertRaises`）、浮点（`assertAlmostEqual`）。用 `python -m unittest -v` 运行。

5. 把第 4 题的测试迁移到 pytest：函数式 + `parametrize` 参数化 + fixture 提供数据。用 `pytest -q` 运行，观察"断言重写"带来的失败信息差异（故意改坏一个断言看报告）。

6. 给 `fetch_price` 函数写 mock 测试：`@patch("模块路径.requests.get")` 模拟成功/超时/404 三种响应（`side_effect`），并验证"只 mock 边界"原则——如果发现必须 mock 内部逻辑，解释该重构哪里。

**第 7–9 题：实战进阶**

7. 调试实战：写一个故意含 bug 的程序（如"列表去重但顺序错误"），用 `breakpoint()` + pdb 走查（`l`/`n`/`p`/`u`），定位后用"先复现（测试）→ 修复 → 固化测试"流程完成。

8. 覆盖率门禁：给一个小包配置 `pytest --cov --cov-fail-under=80`，用 `--cov-branch` 查看分支覆盖，找出"行覆盖 100% 但分支没测全"的 `if` 语句，补测试。

9. 性能剖析：写一个 O(n²) 的算法（如冒泡排序或双重循环），用 `python -m cProfile -s cumulative` 剖析，用 `timeit` 对比"优化前后"两个实现（至少一个数据结构优化，如 dict 替代 list 查找），给出数据。

**第 10 题：深度思考**

10. 假设团队让你建立测试体系：(a) 用本章知识设计测试分层（单测/集成/端到端）与 CI 门禁（覆盖率/耗时/警告）的完整方案；(b) 论述"mock 使用边界"如何影响测试体系的可维护性（重构时测试先崩怎么办）；(c) 结合 14.1.4 的可测试性，分析"测试写起来痛苦"与"代码设计差"的因果关系，给出重构优先级。

---

**进入下一章的准备**：
- ✅ 能用 unittest 和 pytest 写出覆盖正常/边界/异常的三类测试
- ✅ 理解 fixture 依赖注入、参数化、mock 使用方语义，知道"只 mock 边界"
- ✅ 能读覆盖率报告并设置质量门禁；理解"100% ≠ 无 bug"
- ✅ 会用 `breakpoint()`/pdb 单步、post-mortem、`faulthandler` 调试
- ✅ 能读懂 traceback 并定位"自己代码的最内层帧"
- ✅ 会用 cProfile 找热点、timeit 验证优化假设

下一章（第 15 章 性能优化与 C 扩展）是卷 1 的收官章——本章的 `cProfile`/`timeit` 是它的起点，届时将进入：内存剖析（`tracemalloc`）、字节码级优化、`dis` 反汇编、C 扩展（`setuptools` 编译、GIL、`ctypes`/`Cython`），把"Python 为什么慢/怎么变快"讲到底。