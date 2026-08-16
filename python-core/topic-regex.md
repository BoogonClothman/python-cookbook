# 专题：正则表达式——从自动机到生产级实践

> **核心问题**：为什么"用正则解析 HTML"是错的？为什么某些正则会让程序卡死？`re` 模块内部到底发生了什么？正则表达式到底是什么？
>
> 这三个问题的答案分别指向：**计算理论**、**回溯算法**、**有限自动机**。正则不是"高级字符串搜索"，而是一套完整的形式化语言系统。本专题从乔姆斯基层次出发，建立第一性原理认知，再下沉到 Python `re` 和 `regex` 模块的工程实践。

---

## 0. 为什么这个专题必须精通

正则表达式是程序员工具箱中最常被低估、也最常被误用的工具之一。理解正则需要从三个层面建立认知：

| 层面 | 问题 | 不理解的后果 |
|------|------|------------|
| **理论层** | 正则能做什么、不能做什么 | 试图用正则解析 HTML/XML，陷入无休止的 bug |
| **算法层** | 匹配是如何执行的 | 写出灾难性回溯的正则，生产事故 |
| **工程层** | 如何正确使用 `re`/`regex` | 性能低下、Unicode 陷阱、维护困难 |

**学习建议**：第一部分（形式语言与自动机）可能比 `re` 模块本身更重要。这部分建立了"正则是什么"的底层直觉，理解了自动机，就能理解为什么某些模式无法表达、某些正则会卡死、为什么 Go/Rust 的正则引擎比 Python 的更安全。每一节建议亲手实现一个最小版 NFA/DFA，这是建立直觉最有效的方式。

---

## 1. 计算理论根基

### 1.1 正则不是"一种搜索语法"

在深入之前，需要澄清一个普遍的术语混淆：**日常所说的"正则表达式"与理论中的"正则语言"不是同一件事**。

| 概念 | 定义 | 关系 |
|------|------|------|
| **正则表达式**（Regex） | 一种**表示法/语法**，用来描述字符串集合 | 工具层 |
| **正则语言**（Regular Language） | 一类**形式语言**，能被有限自动机识别的语言集合 | 理论层 |
| **有限自动机**（Finite Automaton） | 一个**计算模型**，用来判断字符串是否属于某个语言 | 机器层 |

**关键认知**：正则表达式是正则语言的**语法糖**。理论上，任何正则表达式都可以翻译为一个等价的有限自动机，反之亦然。这个等价性是理解一切正则行为的基础。

#### 乔姆斯基层次：正则语言在何处

诺姆·乔姆斯基（Noam Chomsky）在 1956 年提出了形式语言的四种类型，按表达能力从弱到强排列：

```
类型 3：正则语言        ← 有限自动机识别
        ↑
类型 2：上下文无关语言  ← 下推自动机识别（如算术表达式、HTML 结构）
        ↑
类型 1：上下文相关语言  ← 线性有界自动机识别
        ↑
类型 0：递归可枚举语言  ← 图灵机识别（所有可计算语言）
```

- **正则语言**是最弱的一类，只能描述"无记忆"的模式——状态转移只依赖当前状态和输入字符，不依赖历史。
- **上下文无关语言**引入了"栈"的记忆能力，可以描述嵌套结构（如 `((()))`）。
- **HTML 的标签嵌套**属于上下文无关语言，**不能用正则语言精确描述**——这就是"不要用电锯切木头"级别的原则性问题。

> **⚠️ 陷阱**："正则能匹配 HTML 标签"是半真半假的误导。简单情况下可以（如提取 `<a href="...">`），但遇到嵌套标签、注释、属性值中含尖括号时必然失败。这不是工程技巧问题，是**数学上不可能**。

### 1.2 形式语言基础

#### 1.2.1 字母表、字符串与语言

**定义 1.1（字母表）**：字母表 `Σ` 是一个非空的有穷符号集合。例如：
- `Σ = {a, b}` ——二元字母表
- `Σ = {0, 1}` ——二进制字母表
- `Σ = ASCII` ——字符集字母表

**定义 1.2（字符串）**：字符串是字母表中符号的**有穷序列**。空字符串记为 `ε`（epsilon），长度为 0。

```
a       → 长度 1 的字符串
abba    → 长度 4 的字符串
ε       → 长度 0 的字符串（什么都不是，但有存在意义）
```

**定义 1.3（语言）**：语言 `L` 是字符串的集合。因为字符串集合可以是无穷的，所以语言也可以是无穷的。

```
L1 = {ε, a, aa, aaa, ...}        = a*        （a 的任意重复）
L2 = {ε, a, b, aa, ab, ba, bb, ...} = (a|b)*  （a 和 b 的任意组合）
L3 = {ab, aab, aaab, ...}        = a+b       （至少一个 a 后跟一个 b）
L4 = {}                          = ∅         （空语言，永远不匹配）
```

> **注意**：`∅`（空集）和 `ε`（空字符串）完全不同。`∅` 是"什么都没有"的集合；`ε` 是"有一个什么也没有的字符串"的元素。`{ε} ≠ ∅`。

#### 1.2.2 Kleene 星闭包

**定义 1.4（Kleene 星）**：对任意语言 `L`，`L*` 表示 `L` 中字符串的**任意次连接**（包括零次）：

```
L* = ⋃_{n≥0} L^n = ε ∪ L ∪ LL ∪ LLL ∪ ...

其中：
  L^0 = {ε}
  L^1 = L
  L^2 = {xy | x ∈ L, y ∈ L}   （连接运算）
```

举例：若 `L = {a, b}`，则：
```
L* = {ε, a, b, aa, ab, ba, bb, aaa, aab, aba, abb, baa, bab, bba, bbb, ...}
   = (a|b)*          ← 这就是正则表达式 (a|b)* 描述的全体字符串
```

**关键性质**：
```
(1) ε ∈ L*                  （总是成立）
(2) L ⊆ L*                  （原语言包含在其星闭包中）
(3) L* = LL* ∪ {ε}          （L* 比 LL* 多的只是空串；仅当 ε ∈ L 时 L* = LL*）
(4) (L*)* = L*              （幂等性：双重星等于单星）
```

#### 1.2.3 三种基本运算

正则语言由三种运算生成：

| 运算 | 符号 | 定义 | 直觉 |
|------|------|------|------|
| **并**（Union） | `R \| S` 或 `R ∪ S` | `{w | w ∈ L(R) 或 w ∈ L(S)}` | "或者" |
| **连接**（Concatenation） | `R · S` 或 `RS` | `{xy | x ∈ L(R), y ∈ L(S)}` | "先匹配 R，再匹配 S" |
| **Kleene 星** | `R*` | 连接运算的闭包 | "重复零次或多次" |

**形式化递归定义**：

```
基础情况（原子）：
  1. ∅ 是正则表达式，L(∅) = ∅
  2. ε 是正则表达式，L(ε) = {ε}
  3. 对任意 a ∈ Σ，a 是正则表达式，L(a) = {a}

递归情况：
  4. 若 R、S 是正则表达式，则 (R|S) 是，L(R|S) = L(R) ∪ L(S)
  5. 若 R、S 是正则表达式，则 (RS) 是，L(RS) = L(R) · L(S)
  6. 若 R 是正则表达式，则 (R*) 是，L(R*) = (L(R))*
```

所有更复杂的正则表达式（`+`、`?`、`{m,n}`、字符类 `[abc]` 等）都是这三种运算的**语法糖**，可以在语法分析阶段翻译回这三种基本运算。

### 1.3 自动机理论

#### 1.3.1 DFA：确定有限状态自动机

**定义 1.5（DFA）**：一个确定性有限状态自动机是一个五元组：

```
M = (Q, Σ, δ, q₀, F)

其中：
  Q      —— 状态的有穷集合
  Σ      —— 输入字母表
  δ      —— 转移函数：δ: Q × Σ → Q  （每个状态 + 每个输入，唯一确定下一个状态）
  q₀ ∈ Q —— 初始状态
  F ⊆ Q  —— 接受状态集合
```

**DFA 的判定规则**：给定输入字符串 `w = a₁a₂...aₙ`，DFA 的执行过程：
1. 从 `q₀` 开始
2. 读取 `a₁`，转移到 `δ(q₀, a₁)`
3. 读取 `a₂`，转移到 `δ(q_{step2}, a₂)`
4. ...依次类推
5. 读完所有字符后，若当前状态 ∈ `F`，则**接受**；否则**拒绝**

**示例**：设计一个 DFA，识别"以 `1` 结尾的二进制字符串"（Σ = {0, 1}）：

```
状态定义：
  q0 —— 尚未读取任何字符，或最后一个字符是 0（拒绝态）
  q1 —— 最后一个字符是 1（接受态）

转移函数 δ：
        输入 0     输入 1
  q0  →  q0       →  q1     （看到 0 留在 q0，看到 1 进入 q1）
  q1  →  q0       →  q1     （看到 0 回到 q0，看到 1 留在 q1）

接受状态：F = {q1}

验证：
  "001"  → q0 → q0 → q0 → q1   接受 ✓（以 1 结尾）
  "010"  → q0 → q1 → q0 → q0   拒绝 ✓（以 0 结尾）
  "111"  → q0 → q1 → q1 → q1   接受 ✓
  ""     → q0                  拒绝 ✓（空串不以 1 结尾）
```

状态转移图（等价于上面的表格）：

```
q0 --0--> q0        q0 --1--> q1
q1 --0--> q0        q1 --1--> q1        （q1 为接受态）
```

> **工程影响**：DFA 的核心特性——**无回溯**。每个输入字符只触发一次状态转移，匹配时间复杂度严格为 **O(n)**（n 为输入长度），不受正则表达式复杂度影响。这就是 Go 的 `regexp`（RE2）与 Rust 的 `regex` 采用线性时间自动机引擎的原因：安全性优于功能丰富度。

#### 1.3.2 NFA：非确定有限状态自动机

**定义 1.6（NFA）**：与 DFA 类似，但转移函数允许"不确定性"：

```
δ: Q × (Σ ∪ {ε}) → P(Q)     （P(Q) 表示 Q 的幂集，即 Q 的子集集合）
```

关键差异：
- NFA 可以在**同一输入**下转移到**多个状态**（非确定性）
- NFA 可以有 **ε-转移**（不消耗输入字符的状态跳转）
- NFA 的接受条件：只要存在**至少一条路径**到达接受状态，就接受

**示例**：NFA 识别正则表达式 `(a|b)*a`（以 `a` 结尾的任意 `a/b` 字符串）：

```
状态：q0（起始/循环）、q1（接受，即最后一个字符是 a）

转移：
  q0 --a--> q0    （继续循环）
  q0 --b--> q0    （继续循环）
  q0 --a--> q1    （看到 a，进入接受态）
  q1 --a--> q1    （在 q1 看到 a，仍停留在接受态）
  q1 --b--> q0    （在 q1 看到 b，回到 q0）

这与前述 DFA 完全等价——但构造方式不同。
```

**NFA 的 ε-转移**：

ε-转移是 NFA 独有的能力，允许状态在不消耗输入的情况下跳转。这在将正则表达式转换为 NFA 时非常有用。

```
正则表达式：ab*c

NFA 构造（Thompson 构造法）：
  1. 原子 a    →  起始 --a--> 中间
  2. b*        →  中间 --ε--> b_loop --b--> b_loop
                              --ε--> 下一
  3. c         →  下一 --c--> 接受

组合后的 NFA：
  q_start -(a)-> q_a -(ε)-> q_bloop -(b)-> q_bloop
                                      -(ε)-> q_c -(c)-> q_accept
```

> **理论意义**：ε-转移让 NFA 能够"分解"复杂的正则表达式为小块的自动机，再通过 ε-边拼接。这就是 Thompson 构造法的核心思想。

#### 1.3.3 DFA ↔ NFA 等价性：子集构造算法

**定理 1.1**：对任意 NFA，存在一个等价的 DFA，接受完全相同的语言。

**证明思路**：DFA 的每个状态对应 NFA 的一个**状态集合**（即 NFA 在某个时刻可能处于的所有状态的集合）。

**子集构造算法（Subset Construction）**：

```
输入：NFA N = (Q_N, Σ, δ_N, q0_N, F_N)
输出：DFA M = (Q_M, Σ, δ_M, q0_M, F_M)

算法：
  1. q0_M = ε-closure({q0_N})          // NFA 初始状态的 ε-闭包
  2. Q_M = {q0_M}                      // 已发现的状态集合
  3. F_M = {S ∈ Q_M | S ∩ F_N ≠ ∅}   // 包含至少一个 NFA 接受状态

  4. while Q_M 中存在未处理的状态 S:
       取出 S
       for each 字符 a ∈ Σ:
           T = ε-closure(δ_N(S, a))    // 对 S 中所有状态，读入 a 后取 ε-闭包
           if T 不在 Q_M 中:
               加入 Q_M（未处理）
           δ_M(S, a) = T               // 记录 DFA 转移

  5. return M
```

**具体示例**：将 NFA 转换为 DFA

以 `(a|b)*a` 为例（与 1.3.2 节同一语言）。先用 Thompson 构造法得到带 ε-边的 NFA：

```
NFA 状态：{0, 1, 2, 3, 4}，0 起始，4 接受
  0 --ε--> 1        （进入 (a|b) 循环）
  0 --ε--> 3        （跳过循环，直接到最后的 a）
  1 --a--> 2,  1 --b--> 2
  2 --ε--> 1        （循环回 (a|b)）
  2 --ε--> 3        （退出循环）
  3 --a--> 4        （最后的 a）
```

**第一步：计算起始 DFA 状态（ε-闭包）**

DFA 的起始状态是 `ε-closure({0})`——从 0 出发仅沿 ε-边能到达的所有状态：

```
ε-closure({0}) = {0, 1, 3}      （0 →ε→ 1，0 →ε→ 3；1、3 无 ε 出边）

DFA 状态 A = {0, 1, 3}（起始态，不含 NFA 接受态 4）
```

**第二步：逐符号求转移（读入 a 或 b 后取 ε-闭包）**

```
δ_DFA(A, a) = ε-closure(δ_N({0,1,3}, a))
            = ε-closure({2, 4})        // 1 经 a 到 2，3 经 a 到 4
            = {1, 2, 3, 4}             // 2 经 ε 可达 1、3
            = B                        // 含接受态 4 → B 是接受态

δ_DFA(A, b) = ε-closure(δ_N({0,1,3}, b))
            = ε-closure({2})           // 仅 1 经 b 到 2
            = {1, 2, 3}                = C

δ_DFA(B, a) = ε-closure({2, 4}) = {1, 2, 3, 4} = B
δ_DFA(B, b) = ε-closure({2})     = {1, 2, 3}   = C
δ_DFA(C, a) = ε-closure({2, 4}) = {1, 2, 3, 4} = B
δ_DFA(C, b) = ε-closure({2})     = {1, 2, 3}   = C
```

得到 3 个 DFA 状态：

| DFA 状态 | NFA 状态集合 | 接受？ | `a` | `b` |
|---------|-------------|--------|-----|-----|
| A | {0, 1, 3} | 否 | B | C |
| B | {1, 2, 3, 4} | **是** | B | C |
| C | {1, 2, 3} | 否 | B | C |

注意 A 与 C 的转移完全相同（`a → B, b → C`）且都不含接受态——1.3.4 节的最小化会把它们合并；B 因含接受态 4 必须单独保留。

**用 Python 验证**（两个关键点：DFA 起始状态必须是 `ε-closure({q0})` 而非裸的 `{q0}`；`dfa_states` 的键是 NFA 集合、值是 DFA 编号，打印时别弄反）：

```python
"""子集构造算法：NFA → DFA"""

from collections import defaultdict, deque

def epsilon_closure(states, transitions):
    """计算给定状态集合的 ε-闭包"""
    closure = set(states)
    queue = deque(states)
    while queue:
        state = queue.popleft()
        for next_state in transitions.get(state, {}).get('ε', []):
            if next_state not in closure:
                closure.add(next_state)
                queue.append(next_state)
    return closure

def subset_construction(nfa_alphabet, nfa_transitions, nfa_start, nfa_accept):
    """子集构造：NFA → DFA（dfa_states: frozenset → int）"""
    dfa_states = {}
    dfa_transitions = defaultdict(dict)
    dfa_accept = set()

    # 起始 DFA 状态 = ε-闭包（不是裸的 {nfa_start}！）
    start_closure = frozenset(epsilon_closure({nfa_start}, nfa_transitions))
    dfa_states[start_closure] = 0
    if nfa_accept in start_closure:
        dfa_accept.add(0)

    unprocessed = [start_closure]
    state_id = 1

    while unprocessed:
        current_nfa_set = unprocessed.pop(0)
        current_dfa_id = dfa_states[current_nfa_set]

        for symbol in sorted(nfa_alphabet):
            # 对 NFA 集合中每个状态找 symbol 转移，再取 ε-闭包
            next_nfa_states = set()
            for nfa_state in current_nfa_set:
                next_nfa_states |= nfa_transitions.get(nfa_state, {}).get(symbol, set())
            target = frozenset(epsilon_closure(next_nfa_states, nfa_transitions))

            if target not in dfa_states:
                dfa_states[target] = state_id
                if nfa_accept in target:
                    dfa_accept.add(state_id)
                state_id += 1
                unprocessed.append(target)

            dfa_transitions[current_dfa_id][symbol] = dfa_states[target]

    return dfa_states, dfa_transitions, dfa_accept

# Thompson 构造的 NFA：识别 (a|b)*a，0 起始，4 接受
nfa_trans = {
    0: {'ε': {1, 3}},
    1: {'a': {2}, 'b': {2}},
    2: {'ε': {1, 3}},
    3: {'a': {4}},
    4: {},
}

dfa_states, dfa_trans, dfa_accept = subset_construction(
    nfa_alphabet={'a', 'b'},
    nfa_transitions=nfa_trans,
    nfa_start=0,
    nfa_accept=4,
)

print("DFA 状态数:", len(dfa_states))
print("DFA 接受态:", dfa_accept)
for nfa_set, dfa_id in dfa_states.items():
    print(f"  DFA状态 {dfa_id} = NFA集合 {sorted(nfa_set)}")
    for sym, next_id in sorted(dfa_trans.get(dfa_id, {}).items()):
        print(f"    {sym} → {next_id}")
```

**输出**（Python 3.12 实测）：

```
DFA 状态数: 3
DFA 接受态: {1}
  DFA状态 0 = NFA集合 [0, 1, 3]
    a → 1
    b → 2
  DFA状态 1 = NFA集合 [1, 2, 3, 4]
    a → 1
    b → 2
  DFA状态 2 = NFA集合 [1, 2, 3]
    a → 1
    b → 2
```

验证语言等价性（`(a|b)*a` 应恰好接受"以 a 结尾"的串）：

```
'a'    → 接受     'aa'   → 接受     'ba'   → 接受     'aba'  → 接受
'ab'   → 拒绝     'b'    → 拒绝     ''     → 拒绝     'abba' → 接受
```

> **⚠️ 陷阱**：子集构造有两处容易写错——(1) 起始 DFA 状态必须是 `ε-closure({q0})`，若起始状态有 ε-边而漏算闭包，得到的 DFA 是错的；(2) 遍历 `dfa_states.items()` 时键（NFA 集合）与值（DFA 编号）别弄反。

> **关键推论**：NFA 的"非确定性"是一种描述便利，不是计算能力的提升。任何 NFA 都可以转换为等价的 DFA——正则表达式的表达能力不会因为"非确定性"而增强。本例中：Thompson NFA（5 状态）→ 子集构造得 3 状态 DFA → 1.3.4 节最小化后仅剩 2 状态，与前文 1.3.2 节的直观 DFA 完全一致。

> **关键推论**：NFA 的"非确定性"是一种描述便利，不是计算能力的提升。任何 NFA 都可以转换为等价的 DFA——正则表达式的表达能力不会因为"非确定性"而增强。

#### 1.3.4 状态最小化：分区细化（Moore 算法思想）

DFA 可能不是最优的——可能有冗余状态。最小化目标是：合并等价状态，得到状态数最少的等价 DFA。

**分区细化（Partition Refinement）**的核心思想（Moore 1956 提出，Hopcroft 1971 给出 O(n log n) 优化版）：
1. 初始分区：接受态一组，非接受态一组
2. 反复分裂分区：如果同一分区中的两个状态对某个输入符号转移到不同分区的状态，则分裂
3. 直到不再能分裂

```python
"""DFA 最小化（分区细化，Moore 算法思想的简化实现）"""

def minimize_dfa(transitions, alphabet, start, accept):
    """分区细化：反复按转移目标所在分区分裂，直到稳定"""
    all_states = set(transitions.keys())
    
    # 初始分区：接受态 vs 非接受态
    accepted = accept
    rejected = all_states - accepted
    
    partitions = [sorted(accepted), sorted(rejected)]
    
    changed = True
    while changed:
        changed = False
        new_partitions = []
        
        for partition in partitions:
            if len(partition) <= 1:
                new_partitions.append(partition)
                continue
            
            # 尝试按转移目标分区
            groups = defaultdict(list)
            for state in partition:
                signature = tuple(sorted(transitions[state].get(sym, -1) 
                                        for sym in sorted(alphabet)))
                groups[signature].append(state)
            
            if len(groups) > 1:
                changed = True
                new_partitions.extend(groups.values())
            else:
                new_partitions.append(partition)
        
        partitions = new_partitions
    
    return partitions
```

> **工程影响**：Go 和 Rust 的正则引擎在编译时会对 NFA 进行子集构造 + 状态最小化，生成最优 DFA。这使得它们在运行时具有严格的 O(n) 性能保证，同时避免了灾难性回溯。

### 1.4 正则语言的封闭性与泵引理

#### 1.4.1 封闭性

**定理 1.2**：正则语言在以下运算下封闭：
- **并**：若 L₁, L₂ 是正则，则 L₁ ∪ L₂ 是正则
- **连接**：若 L₁, L₂ 是正则，则 L₁·L₂ 是正则
- **Kleene 星**：若 L 是正则，则 L* 是正则
- **补**：若 L 是正则，则 Σ* \ L 是正则
- **交**：若 L₁, L₂ 是正则，则 L₁ ∩ L₂ 是正则
- **同态**：若 L 是正则，则 h(L) 是正则

**补运算的构造**（DFA → DFA）：
```
给定 DFA M = (Q, Σ, δ, q0, F) 接受 L
构造 DFA M' = (Q, Σ, δ, q0, Q\F) 接受 Σ* \ L
即将接受态和非接受态互换
```

**交的构造**（DFA 乘积）：
```
M1 接受 L1，M2 接受 L2
M 的状态 = Q1 × Q2（笛卡尔积）
M 接受 L1 ∩ L2
```

> **注意**：这些封闭性证明通常借助 **DFA** 完成。补运算直接对 DFA 交换接受/非接受态即可；NFA 不能直接"交换接受态"得到补（非确定性导致接受路径的判定方式不同），需要先确定化。但语言类本身在补运算下封闭——封闭性是**语言类**的性质，与用 NFA 还是 DFA 表示无关。

#### 1.4.2 泵引理（Pumping Lemma）

泵引理是证明**某个语言不是正则语言**的标准工具。它的核心思想：如果一个语言是正则的，那么足够长的字符串必然可以被"泵"（重复某段），且泵后的字符串仍在语言中。

**定理 1.3（泵引理）**：设 L 是正则语言，则存在泵长度 `p ≥ 1`，使得对任意字符串 `w ∈ L`，只要 `|w| ≥ p`，就可以写成 `w = xyz`，满足：
1. `|xy| ≤ p`（泵的部分在前 p 个字符内）
2. `|y| ≥ 1`（泵的部分非空）
3. 对任意 `i ≥ 0`，`xyⁱz ∈ L`（重复 y 任意次仍在语言中）

**几何直观**：当字符串足够长时，DFA 必然会**重复经过某个状态**（鸽巢原理）。从第一个重复状态到第二个重复状态之间的子串就是 `y`，可以无限重复而不改变接受性。

**经典应用：证明 L = {aⁿbⁿ | n ≥ 0} 不是正则语言**

反证法：假设 L 是正则的，则存在泵长度 p。

取字符串 `w = a^p b^p`（p 个 a 后跟 p 个 b），显然 `w ∈ L` 且 `|w| = 2p ≥ p`。

根据泵引理，`w = xyz`，`|xy| ≤ p`，`|y| ≥ 1`。

因为 `|xy| ≤ p`，所以 `xy` 完全在前 p 个字符中——即 `xy` 只包含 `a`，不包含 `b`。因此 `y = a^k`（k ≥ 1）。

现在考虑 `xy²z = a^(p+k) b^p`。这个字符串有 `p+k` 个 a 和 `p` 个 b，显然 `p+k ≠ p`，所以 `xy²z ∉ L`。

**矛盾！** 因此 L 不是正则语言。

> **核心结论**：`aⁿbⁿ` 类语言需要"计数"能力——记住 a 的个数，然后验证 b 的个数相同。有限自动机没有外部记忆，无法计数任意大的 n，因此这类语言超出了正则语言的能力范围。

#### 1.4.3 泵引理的其他应用

**示例 1**：证明 `L = {aⁿ | n 是质数}` 不是正则语言

假设 L 正则，取泵长度 p。取 `w = a^q`，其中 q 是大于 p 的质数。
`w = xyz`，`|xy| ≤ p`，`y = a^k`（k ≥ 1）。
考虑 `xy^(q+1)z = a^(q + qk) = a^(q(1+k))`。
因为 q ≥ 2, k ≥ 1，所以 `q(1+k)` 是合数（至少有两个大于 1 的因子），故 `a^(q(1+k)) ∉ L`。
矛盾。

**示例 2**：证明正则语言在补运算下封闭（使用泵引理的逆否命题）

这个证明不需要泵引理，直接用 DFA 构造即可（见前文）。泵引理主要用于证明**非正则性**。

> **⚠️ 常见误解**：泵引理是**必要条件而非充分条件**。即：如果是正则的，一定满足泵引理；但满足泵引理的不一定是正则的。不能用"满足泵引理"来证明一个语言是正则的。

#### 1.4.4 正则 vs 上下文无关：实践意义

| 特征 | 正则语言 | 上下文无关语言 |
|------|---------|-------------|
| 识别器 | 有限自动机（无记忆） | 下推自动机（带栈） |
| 能描述 | 线性模式、关键词、简单结构 | 嵌套结构、括号匹配、算术表达式 |
| 典型例子 | 邮箱格式、IP 地址、token 流 | 算术表达式 `1+(2*3)`、嵌套 JSON、HTML 结构 |
| 解析复杂度 | O(n) | O(n³)（CYK 算法）或 O(n)（LL/LR 解析器） |

**为什么不能用电锯切木头**：

HTML 的合法性要求标签正确嵌套：
```html
<div><span>text</span></div>   ✓ 合法
<div><span>text</div></span>   ✗ 不合法
```

要验证嵌套，需要**计数**——每遇到 `<div>` 压栈，每遇到 `</div>` 弹栈。有限自动机没有栈，无法做到这一点。这就是为什么 HTML 解析必须使用专门的解析器（如 BeautifulSoup、lxml），而不是正则表达式。

> **工程影响**：在爬虫、数据清洗场景中，如果用正则去匹配 HTML 结构，你会遇到：属性值中含尖括号、注释嵌套标签、自闭合标签等各种边缘情况。每次修复一个 edge case，又会引入新的 bug。正确的分层是：**正则做词法分析（提取 token），解析器做语法分析（理解结构）**。

---

## 2. 正则表达式理论体系

### 2.1 从 Kleene 正则表达式到 PCRE

理论正则表达式只有三种运算：`|`、`·`、`*`。日常使用的正则表达式（PCRE）在此基础上扩展了大量语法糖。理解这些语法糖如何翻译回基本运算，是掌握正则本质的重要途径。

#### 2.1.1 语法糖的数学翻译

| 语法糖 | 数学翻译 | 说明 |
|--------|---------|------|
| `R+` | `RR*` 或 `R*R` | 一次或多次 = 至少一个 R |
| `R?` | `R\|ε` | 零次或一次 = R 或空 |
| `R{m}` | `R` 重复 m 次 | 固定重复 |
| `R{m,n}` | `R^m(R|ε)^{n-m}`，即 `⋃_{k=m}^{n} R^k` | 区间重复 |
| `[abc]` | `a\|b\|c` | 字符类 = 字符的并 |
| `[^abc]` | 字母表中除 a,b,c 外的字符 | 负字符类 = 补集 |
| `.` | 任意字符（默认**不含**换行） | 通配符；`re.S`/DOTALL 下才等于 `[\s\S]` |
| `\d` | `[0-9]` | 预定义字符类（Unicode 模式下含其他 Unicode 数字） |
| `\w` | `[a-zA-Z0-9_]` | 单词字符（Unicode 模式下含中文等，见 3.6.3 节） |
| `\s` | `[\t\n\r\f\v ]` | 空白字符（Unicode 模式下含更多空白） |

**关键认知**：所有语法糖**不增加表达能力**，只增加书写便利。它们可以在编译期被翻译回基本运算，不影响正则语言的理论边界。

#### 2.1.2 断言（Assertions）不增加表达能力

先行断言（lookahead）和后行断言（lookbehind）看似增加了功能，但实际上**不突破正则语言的边界**：

```
(?=pattern)   —— 先行正断言：后面必须匹配 pattern（但不消耗字符）
(?!pattern)   —— 先行负断言：后面不能匹配 pattern
(?<=pattern)  —— 后行正断言：前面必须匹配 pattern
(?<!pattern)  —— 后行负断言：前面不能匹配 pattern
```

**为什么不增加表达能力**：断言只是"查看"相邻位置的内容，不消耗输入字符，不改变语言的定义。可以构造等价的 DFA 来模拟（虽然状态数可能爆炸增长）。

**实际价值**：断言大幅提升了**书写便利性**。没有断言，很多常见模式需要冗长的等价表达。

```python
# 用断言：匹配后面跟 "USD" 的数字
>>> import re
>>> re.findall(r'\d+(?= USD)', 'Price: 100 USD, Tax: 15 USD')
['100', '15']

# 不用断言的等价写法（更复杂）
>>> re.findall(r'(\d+) USD', 'Price: 100 USD, Tax: 15 USD')
['100', '15']     # 结果一样，但需要后处理去掉 " USD"
```

#### 2.1.3 惰性量词：最短匹配语义

贪婪量词（`*`、`+`、`?`、`{m,n}`）默认匹配尽可能多的字符。惰性量词（`*?`、`+?`、`??`、`{m,n}?`）匹配尽可能少的字符。

**理论解释**：惰性量词是**回溯策略**的不同选择，不改变语言本身：

```
贪婪：先尝试匹配整个可能的范围，失败时逐步回退
惰性：先尝试匹配最少，成功时逐步扩展
```

```python
>>> text = '<div>hello</div><span>world</span>'

# 贪婪：.* 匹配到最后一个 </div>
>>> re.findall(r'<div>.*</div>', text)
['<div>hello</div><span>world</span>']   # ❌ 错了，跨标签匹配

# 惰性：.*? 匹配到第一个 </div>
>>> re.findall(r'<div>.*?</div>', text)
['<div>hello</div>']                       # ✅ 正确
```

> **⚠️ 陷阱**：惰性量词不是银弹。对于嵌套结构，无论是贪婪还是惰性都无法正确处理——这是正则的固有限制。

### 2.2 贪婪与懒惰的自动机语义

#### 2.2.1 回溯树（Backtracking Tree）

正则引擎（基于 NFA 模拟）在匹配时的本质是一个**深度优先搜索树**。每个量词都会创建分支点，引擎尝试最贪婪的路径，失败时回溯。

```
正则：(a+)b
输入：aaab

匹配过程（回溯树）：
  尝试 a+ 匹配 "aaa" → 遇到 b，成功！→ 返回匹配
  （没有失败，所以没有回溯）

正则：(a+)b
输入：aaac

匹配过程：
  尝试 a+ 匹配 "aaa" → 遇到 c，不匹配 b → 回溯
  尝试 a+ 匹配 "aa"  → 遇到 a，不匹配 b → 回溯
  尝试 a+ 匹配 "a"   → 遇到 a，不匹配 b → 回溯
  尝试 a+ 匹配 ""    → 遇到 a，不匹配 b → 失败
  → 整体匹配失败
```

#### 2.2.2 灾难性回溯（Catastrophic Backtracking）

当正则表达式和输入字符串的组合导致回溯树**指数级膨胀**时，就发生了灾难性回溯。

**经典反例**：

```python
import time
import re

# 灾难性正则：嵌套的量词导致指数级回溯
pattern = r'(a+)+b'
text = 'a' * 30 + 'c'   # 没有 'b'，导致全部回溯

start = time.time()
re.match(pattern, text)
elapsed = time.time() - start

print(f"耗时: {elapsed:.4f} 秒")  # 实测 n=30 约 60–70 秒（指数增长，n=40 即无法等待）
```

**理论分析**：

```
正则 (a+)+ 对输入 a^n 的回溯树：
  第 1 层：尝试将 n 个 a 划分为 k 段（k 从 n 到 1）
  第 2 层：每段内部又有子划分...

回溯树节点数 = n 的有序划分数（组合数）= 2^(n-1)，指数级增长

对于 n=30：2^29 ≈ 5.4×10^8 种划分，Python 3.12 实测约 60 秒
对于 n=100：超出任何实际计算能力
```

> **注意**：网上常把这里的复杂度写成 Bell 数 `B(n)`，这是不准确的——Bell 数统计的是**集合**的划分（无序、分组无先后），而 `(a+)+` 的回溯对应的是**序列**的有序划分（组合数 `2^(n-1)`）；且 `B(30)` 实际约为 8.5×10^23，与 10^14 差着 9 个数量级。

**根本原因**：`(a+)+` 中有**重叠的子表达式**。外层 `+` 和内层 `+` 都能匹配 `a`，导致同一个输入字符可以通过多种路径被分配。正则引擎无法区分这些路径，逐一尝试。

**修复方案**：
1. **消除歧义**：`(?:a++)+b`（原子分组 + 拥有量词，Python 3.11+ 的 `re` 已直接支持，见 3.6.5 节）
2. **重写正则**：`a+b`（直接写，不需要嵌套）
3. **使用 DFA 引擎**：Go/Rust 的 `regex` 引擎不会发生灾难性回溯

```python
# ✅ 正确写法
>>> re.match(r'a+b', 'aaab')
<re.Match object; span=(0, 4), match='aaab'>

# ❌ 危险写法
>>> re.match(r'(a+)+b', 'a' * 50 + 'c')
# 这会卡住很久
```

> **⚠️ 陷阱**：灾难性回溯不仅影响性能，更是**安全漏洞**。攻击者可以故意构造恶意输入，导致服务器 CPU 100% 占用——这就是 ReDoS（Regular Expression Denial of Service）攻击。Stack Overflow（2016）和 Cloudflare（2019）都曾因此发生线上事故。

#### 2.2.3 NFA 模拟 vs DFA 模拟

| 特性 | 回溯引擎（Python `re` / PCRE） | 线性时间引擎（Go `regexp` / Rust `regex` / RE2） |
|------|------------------------------|--------------------------------------------------|
| 匹配时间 | 最坏 O(n·m)，n=输入长度，m=正则复杂度；可能指数级 | 严格 O(n) |
| 回溯风暴 | 可能发生 | 不可能 |
| 功能支持 | 捕获组、断言、回溯引用、原子分组（3.11+） | 有限（不支持回溯引用与环视） |
| 内存占用 | 较低 | 较高（需存储整个 DFA） |
| 代表引擎 | Python `re`、Java `Pattern`、PCRE | Go `regexp`、Rust `regex`、RE2 |

**Python `re` 的实现**：

Python 的 `re` 模块是**回溯型引擎**：编译阶段把正则翻译成内部指令序列（SRE bytecode），匹配阶段用一个带回溯的递归下降模拟器逐字符执行。它**不是** Thompson NFA 模拟（Thompson 模拟是线性时间的、无回溯），因此：
- 支持捕获组、命名分组、断言、回溯引用等丰富功能
- 但有灾难性回溯风险（3.11+ 可用原子分组/拥有量词约束回溯）

```python
import re

# Pattern 对象是编译产物，内部是 SRE 指令序列（不是"DFA 状态表"）
pattern = re.compile(r'(a+)+b')
print(pattern.pattern)   # '(a+)+b'
# 内部指令序列没有公开 API 可查看，理解其存在即可
```

### 2.3 正则表达式的能力边界

#### 2.3.1 正则能做什么

| 任务类型 | 示例 | 正则适用性 |
|---------|------|----------|
| 词法分析 | Token 识别（关键字、标识符、数字） | ✅ 完全适用 |
| 格式验证 | 邮箱、URL、IP、日期格式 | ✅ 适用（注意边界情况） |
| 简单提取 | 提取固定格式的字段 | ✅ 适用 |
| 文本替换 | 批量重命名、格式转换 | ✅ 适用 |
| 日志解析 | 结构化日志的行级解析 | ✅ 适用 |

#### 2.3.2 正则不能做什么

| 任务类型 | 原因 | 替代方案 |
|---------|------|---------|
| 嵌套括号匹配 | 需要计数/栈，超越正则语言 | 递归下降解析器、PEG |
| HTML/XML 解析 | 标签嵌套是上下文无关语言 | BeautifulSoup、lxml |
| `aⁿbⁿ` 类模式 | 需要跨距离相等比较 | 上下文无关文法 |
| 任意层级递归 | 有限自动机无外部记忆 | 下推自动机 |

#### 2.3.3 PCRE 的非正则扩展

Perl 兼容正则表达式（PCRE）在传统正则基础上添加了非正则功能：

| 扩展 | 语法 | 效果 |
|------|------|------|
| 递归模式 | `(?R)`、`(?1)` | 匹配嵌套结构（如括号） |
| 条件分支 | `(?(condition)yes\|no)` | 条件逻辑 |
| 平衡组 | `.NET` 特有 | 栈式分组 |
| 原子分组 | `(?>...)` | 限制回溯，防止灾难性回溯 |

> **⚠️ 注意**：这些扩展**突破了正则语言的边界**，使 PCRE 能够描述部分上下文无关语言。但也因此失去了 O(n) 性能保证。Python 的 `re` 模块不支持递归模式和条件分支；原子分组与拥有量词已在 Python 3.11+ 加入 `re`（详见 3.6.5 节），递归/条件分支等其余特性需用 `regex` 第三方模块。

---

## 3. Python `re` 模块深度剖析

### 3.1 `re` 模块的架构

Python 的 `re` 模块是对 Unix 正则引擎的面向对象封装。理解其架构有助于写出高效、正确的代码。

#### 3.1.1 核心对象模型

```
re.compile(pattern, flags)
    │
    ▼
Pattern 对象              # 编译后的正则，可重复使用
    │
    ├── match(string, pos, endpos)   # 从 pos 开始匹配
    ├── search(string, pos, endpos)  # 在整个 string 中搜索
    ├── findall(string, pos, endpos) # 返回所有匹配的列表
    ├── finditer(string, pos, endpos) # 返回 Match 迭代器
    ├── sub(repl, string, count)     # 替换
    ├── split(string, maxsplit)      # 分割
    └── flags                        # 编译标志
```

**Match 对象**：

```python
>>> m = re.search(r'(\d{4})-(\d{2})-(\d{2})', '今天是 2024-03-15')
>>> m.group(0)    # 完整匹配
'2024-03-15'
>>> m.group(1)    # 第 1 个分组
'2024'
>>> m.group(2)
'03'
>>> m.group(3)
'15'
>>> m.groups()    # 所有分组（不含 group(0)）
('2024', '03', '15')
>>> m.span(0)     # 匹配位置（'今天是 ' 占 4 个码位，日期占 10 个）
(4, 14)
>>> m.start(), m.end()
(4, 14)
```

#### 3.1.2 编译缓存机制

`re` 模块内部维护了一个 pattern 编译缓存 `_cache`：

```python
import re

# 每次调用 re.match() 都会先查缓存，未命中则编译并缓存
# _MAXCACHE = 512（3.12-3.14 均为 512）
>>> re._MAXCACHE
512

# 缓存淘汰策略：不是 LRU！缓存满（≥512 个）时整体 _cache.clear()，
# 所有已编译模式一次性全部失效（CPython Lib/re/__init__.py 源码如此）
```

**工程影响**：

```python
# ❌ 错误：每次调用都重新编译（即使 pattern 相同）
def validate_email(text):
    return bool(re.match(r'^[\w.-]+@[\w.-]+\.\w+$', text))
    # 每次调用都查询缓存，若 pattern 相同则直接命中——但仍有函数调用开销

# ✅ 正确：编译一次，复用 Pattern 对象
EMAIL_PATTERN = re.compile(r'^[\w.-]+@[\w.-]+\.\w+$')

def validate_email(text):
    return bool(EMAIL_PATTERN.match(text))
```

```python
# ❌ 危险：直接把用户输入拼进 pattern（注入风险 + 无法命中缓存）
username = 'alice@example.com'
pattern = re.compile(r'^' + username + r'$')   # username 里的 . 是通配符！
pattern.match('aliceXexampleXcom')             # ❌ 竟然匹配成功

# ✅ 正确：re.escape() 把用户输入全部转义为字面量
pattern = re.compile(r'^' + re.escape(username) + r'$')
pattern.match('alice@example.com')             # ✅ 匹配
pattern.match('aliceXexampleXcom')             # None ✅ 转义后 . 不再通配
```

### 3.2 模式语法全解

#### 3.2.1 原子（Atoms）

| 语法 | 含义 | 对应理论 | 陷阱 |
|------|------|---------|------|
| `a-z` | 字面字符 | 字母表元素 | 区分大小写（除非 `re.I`） |
| `.` | 任意字符（除换行） | 通配符 | 需 `re.S` 才能匹配换行 |
| `[abc]` | 字符类 | `a\|b\|c` | 内部 `-` 表示范围，需转义或放首尾 |
| `[^abc]` | 负字符类 | 补集 | 匹配任意非 a/b/c 的字符 |
| `\d` | `[0-9]` | 预定义类 | Unicode 模式下匹配所有 Unicode 数字 |
| `\D` | `[^0-9]` | 补集 | — |
| `\w` | `[a-zA-Z0-9_]` | 单词字符 | Unicode 模式包含中文等 |
| `\W` | `[^a-zA-Z0-9_]` | 补集 | — |
| `\s` | 空白字符 | — | 包含 `\t\n\r\f\v` 和 Unicode 空格 |
| `\S` | 非空白字符 | — | — |
| `\b` | 单词边界 | — | 不是位置，而是 `[\w]` 与 `[^\w]` 之间的边界 |
| `\B` | 非单词边界 | — | — |
| `\A` | 字符串开头 | — | 不受 `re.M` 影响（`^` 受） |
| `\Z` | 字符串结尾 | — | 不受 `re.M` 影响（`$` 受） |
| `$` | 行尾（或字符串尾） | — | `re.M` 下匹配每行末尾 |
| `^` | 行首（或字符串头） | — | `re.M` 下匹配每行开头 |

```python
# ❌ 常见错误：\b 不是"字母边界"，而是"单词字符边界"
>>> re.findall(r'\bcat\b', 'category cat scat')
['cat']           # 'category' 中的 'cat' 后面是 'e'（单词字符），不是边界

# ✅ 正确理解：\b 匹配 [\w][^\w] 或 [^\w][\w] 的边界
>>> re.findall(r'\bcat\b', 'the cat sat')
['cat']

# ❌ 常见错误：^ 和 $ 默认只锚定整个字符串的开头/结尾
>>> re.findall(r'^line\d+$', 'line1\nline2')
[]              # 默认模式下 ^$ 锚定整体，'line1\nline2' 不是单个 "line数字"

# ✅ re.MULTILINE：^ 和 $ 匹配每一行的首尾
>>> re.findall(r'^line\d+$', 'line1\nline2', re.M)
['line1', 'line2']

# ❌ 常见错误：. 默认不匹配换行符，跨行匹配会失败
>>> re.search(r'line1.*line2', 'line1\nline2')
None            # .* 跨不过 \n

# ✅ re.DOTALL：让 . 匹配换行符
>>> re.search(r'line1.*line2', 'line1\nline2', re.S)
<re.Match object; span=(0, 11), match='line1\nline2'>
```

#### 3.2.2 量词（Quantifiers）

| 语法 | 含义 | 贪婪/惰性 | 数学翻译 |
|------|------|---------|---------|
| `*` | 零次或多次 | 贪婪 | `R*` |
| `*?` | 零次或多次（惰性） | 惰性 | — |
| `+` | 一次或多次 | 贪婪 | `R+` = `RR*` |
| `+?` | 一次或多次（惰性） | 惰性 | — |
| `?` | 零次或一次 | 贪婪 | `R?` = `R\|ε` |
| `??` | 零次或一次（惰性） | 惰性 | — |
| `{m}` | 恰好 m 次 | 贪婪 | — |
| `{m,n}` | m 到 n 次 | 贪婪 | — |
| `{m,n}?` | m 到 n 次（惰性） | 惰性 | — |
| `{m,}` | m 次或更多 | 贪婪 | — |

```python
# 贪婪 vs 惰性：直观对比
>>> text = '<div>hello</div><span>world</span>'

# 贪婪 .* 匹配到最后一个 </div>
>>> re.findall(r'<div>.*</div>', text)
['<div>hello</div><span>world</span>']   # ❌ 吞掉了 span

# 惰性 .*? 匹配到第一个 </div>
>>> re.findall(r'<div>.*?</div>', text)
['<div>hello</div>']                      # ✅ 正确
```

```python
# {m,n} 与 {m,n}? 的性能差异
>>> import time
>>> pattern_greedy = re.compile(r'a{1,100}b')
>>> pattern_lazy = re.compile(r'a{1,100}?b')
>>> text = 'a' * 50 + 'b'

# 两者结果相同，但贪婪模式在匹配失败时的回溯路径更长
start = time.time()
pattern_greedy.match(text)
g_time = time.time() - start

start = time.time()
pattern_lazy.match(text)
l_time = time.time() - start

print(f"贪婪: {g_time:.6f}s, 惰性: {l_time:.6f}s")
# 惰性通常略快（更早成功，更少回溯）
```

#### 3.2.3 分组（Groups）

| 语法 | 类型 | 说明 |
|------|------|------|
| `(expr)` | 捕获分组 | 匹配内容存入 `\1`、`\2`... |
| `(?:expr)` | 非捕获分组 | 不存入编号，仅用于分组优先级 |
| `(?P<name>expr)` | 命名分组 | 可用 `m.group('name')` 访问 |
| `(?P=name)` | 命名回溯引用 | 引用前面同名分组的实际内容 |

```python
# 捕获分组
>>> m = re.search(r'(\d{4})-(\d{2})-(\d{2})', '2024-03-15')
>>> m.groups()
('2024', '03', '15')
>>> m.group(1)
'2024'

# 非捕获分组：用于优先级，不占用编号
>>> m = re.search(r'(?:https?://)?example\.com', 'https://example.com')
>>> m.group(0)
'https://example.com'
# 没有 group(1)——(?:...) 不捕获

# 命名分组
>>> m = re.search(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})', '2024-03-15')
>>> m.group('year')
'2024'
>>> m.groupdict()
{'year': '2024', 'month': '03', 'day': '15'}

# 命名回溯引用：确保两段内容完全相同
>>> m = re.search(r'(?P<word>\w+)\s+(?P=word)', 'hello hello world')
>>> m.group(0)
'hello hello'
```

> **⚠️ 陷阱**：分组编号按**左括号出现顺序**分配，不按使用顺序。非捕获分组不参与编号：

```python
# ❌ 错误预期
>>> m = re.search(r'(a)(?:b)(c)', 'abc')
>>> m.group(1), m.group(2)
('a', 'c')    # 编号是 1 和 2，(?:b) 不占编号

# ✅ 正确理解：(?:...) 只是分组，不编号
```

#### 3.2.4 断言（Assertions）

| 语法 | 类型 | 消耗字符？ |
|------|------|----------|
| `(?=expr)` | 先行正断言 | 否 |
| `(?!expr)` | 先行负断言 | 否 |
| `(?<=expr)` | 后行正断言 | 否 |
| `(?<!expr)` | 后行负断言 | 否 |

```python
# 先行断言：匹配后面是 USD 的数字
>>> re.findall(r'\d+(?= USD)', 'Price: 100 USD, Tax: 15 USD')
['100', '15']

# 先行负断言：匹配后面不是 USD 的数字
# ⚠️ 必须加 \b：否则 '100 USD' 会退一步匹配出 '10'（见下方陷阱）
>>> re.findall(r'\b\d+\b(?! USD)', '100 USD and 200 EUR')
['200']

# 后行断言：匹配前面是 $ 的数字
>>> re.findall(r'(?<=\$)\d+', 'Price: $100, Tax: $15')
['100', '15']

# 固定宽度限制：后行断言的 expr 必须是固定长度
>>> re.search(r'(?<=\d+)-\d+', 'abc-123-456')   # ❌ 变宽度，编译期报错
re.error: look-behind requires fixed-width pattern
>>> re.search(r'(?<=\d{3})-\d+', 'abc-123-456')  # ✅ 固定 3 位，匹配 '-456'
<re.Match object; span=(7, 11), match='-456'>
```

> **⚠️ 陷阱 1（负先行断言）**：`re.findall(r'\d+(?! USD)', '100 USD and 200 EUR')` 的返回值是 `['10', '200']` 而不是 `['200']`！原因：在 `'100'` 位置整体匹配失败后，引擎回溯把 `\d+` 缩短为 `'10'`，此时后面的字符是 `'0 USD'`，不再以 `' USD'` 开头，负断言成立，于是匹配出半截数字 `'10'`。用 `\b\d+\b(?! ...)` 锁定完整单词可避免。
>
> **陷阱 2（后行断言）**：后行断言只是"检查前面"，**不消耗字符**。`(?<=\d{3})-\d+` 匹配 `'123-456'` 时结果是 `'-456'`（span (3, 7)），不会把前面的数字吞进匹配结果。

> **版本注意**：`re` 的固定宽度后行断言自早期版本（Python 1.5 时代）就存在。实测（3.12–3.14）：同一交替内**等宽**分支可用（如 `(?<=ab|bc)`），**不同宽度**分支（如 `(?<=a|bc)`）仍报 `look-behind requires fixed-width pattern`。`regex` 模块（第三方，2010 年前后发布）自早期版本就支持**可变宽度**后行断言（如 `(?<=a+)`、`(?<=a|bc)`），与 Python 3.8 无关。

### 3.3 匹配方法详解

#### 3.3.1 四种核心匹配方法

| 方法 | 行为 | 返回值 | 典型用途 |
|------|------|--------|---------|
| `re.match()` | 只在字符串**开头**匹配 | Match 或 None | 前缀验证 |
| `re.search()` | 扫描整个字符串，返回**第一个**匹配 | Match 或 None | 是否存在 |
| `re.findall()` | 返回**所有**匹配的列表 | list[str] | 提取全部 |
| `re.finditer()` | 返回 Match 对象的迭代器 | iterator | 省内存遍历 |
| `re.fullmatch()` | 要求**整个字符串**匹配 | Match 或 None | 完整格式验证 |

```python
text = 'The price is 100 dollars and 50 cents'

# match：只看开头
>>> re.match(r'\d+', text)
None    # 开头是 'The'，不是数字

# search：找第一个（'100' 从下标 13 开始）
>>> re.search(r'\d+', text)
<re.Match object; span=(13, 16), match='100'>

# findall：找全部
>>> re.findall(r'\d+', text)
['100', '50']

# finditer：省内存版本
>>> for m in re.finditer(r'\d+', text):
...     print(m.span(), m.group())
(13, 16) 100
(29, 31) 50

# fullmatch：整个字符串必须匹配
>>> re.fullmatch(r'\d+', '100')
<re.Match object; span=(0, 3), match='100'>
>>> re.fullmatch(r'\d+', '100 dollars')
None    # 因为有非数字部分
```

#### 3.3.2 findall 的分组歧义

`findall` 有一个著名的陷阱：当正则包含**捕获分组**时，`findall` 返回的是分组内容而非完整匹配：

```python
# ❌ 意外行为
>>> re.findall(r'(\d{4})-(\d{2})-(\d{2})', '2024-03-15 and 2025-01-01')
[('2024', '03', '15'), ('2025', '01', '01')]
# 返回的是 tuple 列表，不是完整日期字符串！

# ✅ 正确：用非捕获分组
>>> re.findall(r'(?:\d{4})-(?:\d{2})-(?:\d{2})', '2024-03-15 and 2025-01-01')
['2024-03-15', '2025-01-01']

# ✅ 或者用 finditer（注意先定义 text）
>>> text = '2024-03-15 and 2025-01-01'
>>> [m.group(0) for m in re.finditer(r'\d{4}-\d{2}-\d{2}', text)]
['2024-03-15', '2025-01-01']
```

```python
# findall 的行为规则
# 1. 无分组 → 返回完整匹配的字符串列表
# 2. 一个分组 → 返回该分组的字符串列表
# 3. 多个分组 → 返回 tuple 列表（每个 tuple 是一个匹配的所有分组）
```

### 3.4 标志位与多行模式

#### 3.4.1 常用标志位

| 标志 | 简写 | 效果 | 典型场景 |
|------|------|------|---------|
| `re.IGNORECASE` | `re.I` | 忽略大小写 | 大小写不敏感的搜索 |
| `re.MULTILINE` | `re.M` | `^` `$` 匹配每行首尾 | 多行文本的行级操作 |
| `re.DOTALL` | `re.S` | `.` 匹配换行符 | 跨行匹配 |
| `re.VERBOSE` | `re.X` | 忽略空白和注释 | 可读性优先的正则书写 |
| `re.ASCII` | `re.A` | 禁用 Unicode 匹配 | 性能优化、安全控制 |
| `re.UNICODE` | `re.U` | Unicode 匹配（默认） | — |

```python
# MULTILINE：让 ^ 和 $ 匹配每行的开头和结尾
>>> text = 'line one\nline two\nline three'
>>> re.findall(r'^line\s+\w+', text)           # 默认：只匹配第一行
['line one']
>>> re.findall(r'^line\s+\w+', text, re.M)     # 加上 re.M
['line one', 'line two', 'line three']

# DOTALL：让 . 匹配换行符
>>> re.findall(r'hello.*world', 'hello\nworld')
[]                         # 默认：. 不匹配 \n
>>> re.findall(r'hello.*world', 'hello\nworld', re.S)
['hello\nworld']           # DOTALL 模式

# VERBOSE：支持空格和注释，极大提升可读性
>>> pattern = re.compile(r'''
...     ^                   # 字符串开头
...     (?P<user>[\w.-]+)   # 用户名
...     @                   # @ 符号
...     (?P<domain>[\w.-]+) # 域名
...     \.                  # 点号
...     (?P<tld>[a-z]{2,})  # 顶级域名（2+ 字母）
...     $                   # 字符串结尾
... ''', re.X | re.I)
>>> pattern.match('user@example.com').groupdict()
{'user': 'user', 'domain': 'example', 'tld': 'com'}
```

#### 3.4.2 Unicode 大小写折叠的坑

```python
# ✅ 正常工作：re.I 忽略大小写
>>> re.match(r'^[\w.-]+@[\w.-]+\.[a-z]{2,}$', 'USER@EXAMPLE.COM', re.I)
<re.Match object; span=(0, 16), match='USER@EXAMPLE.COM'>

# ⚠️ 但 re.I 做的是"简单大小写折叠"，不是完整的 Unicode case folding
>>> 'ß'.casefold()   # 德语 sharp s：完整折叠为 ss
'ss'
>>> 'ß'.lower()      # 简单小写仍是单字符
'ß'

# re.I 无法跨越"1 个字符 ↔ 2 个字符"的折叠
>>> re.match(r'^ss$', 'ß', re.I)   # 简单折叠下 ß 不会展开成 ss
None                              # ❌ 与 casefold 的预期不符
>>> 'ß'.casefold() == 'ss'        # 而完整折叠是相等的
True
```

> **⚠️ 陷阱**：`re.I` 基于**简单大小写映射**（simple case folding），对 ASCII 可靠，但**不做完整 case folding**：单字符 ↔ 多字符的映射（如 `ß` → `ss`、连字 `ﬁ` → `fi`）不会生效。需要完整折叠时先 `unicodedata.normalize('NFKC', s).casefold()` 再匹配。

#### 3.4.3 ASCII 标志的性能与安全

```python
# re.ASCII 禁用 Unicode 匹配，提升性能
# 实测（Python 3.12，50 次 findall）：Unicode 0.129s vs ASCII 0.081s，约 1.6 倍
>>> import time
>>> pattern_unicode = re.compile(r'\w+')
>>> pattern_ascii = re.compile(r'\w+', re.A)
>>> text = 'hello world ' * 10000

start = time.time()
pattern_unicode.findall(text)
t1 = time.time() - start

start = time.time()
pattern_ascii.findall(text)
t2 = time.time() - start

print(f"Unicode: {t1:.4f}s, ASCII: {t2:.4f}s")
# Unicode: 0.1294s, ASCII: 0.0808s（ASCII 版本更快，但远不到"2-3 倍"）
```

> **工程影响**：`re.ASCII` 的首要价值不是性能，而是**语义锁定**：`\w`/`\d`/`\s` 只匹配 ASCII 字符，避免全角字符、中文等被误判（例如 `re.match(r'^\w+$', '你好')` 默认能匹配，加 `re.ASCII` 后返回 `None`）。

### 3.5 替换与分割

#### 3.5.1 re.sub() 的 Replacement String

```python
# 基本替换
>>> re.sub(r'\d+', 'X', 'price: 100, tax: 15')
'price: X, tax: X'

# 反向引用：\1 \2 引用分组
>>> re.sub(r'(\d{4})-(\d{2})-(\d{2})', r'\3/\2/\1', '2024-03-15')
'15/03/2024'

# 命名分组引用：\g<name>
>>> re.sub(r'(?P<year>\d{4})-(?P<month>\d{2})', r'\g<month>/\g<year>', '2024-03-15')
'03/2024'

# ⚠️ 注意：& 在 Python 的 replacement 中没有任何特殊含义
# （sed/Perl 里 & 表示"整个匹配"，Python 不是！）
>>> re.sub(r'(\w+)', r'&1', 'abc')
'&1'      # 字面量 &1 整体替换
```

```python
# ❌ 危险：replacement 里引用不存在的分组会直接报错
>>> re.sub(r'test', r'\1', 'this is a test')   # 模式里没有分组
re.error: invalid group reference 1 at position 1

# ✅ 需要输出字面反斜杠时，用 \\ 转义
>>> re.sub(r'test', r'\\1', 'this is a test')
'this is a \\1'
```

#### 3.5.2 函数式替换

```python
# sub 可以接收函数作为 replacement
>>> def upper_match(m):
...     return m.group(0).upper()
...
>>> re.sub(r'\b\w+\b', upper_match, 'hello world')
'HELLO WORLD'

# 典型应用：驼峰命名转换
>>> def camel_to_snake(m):
...     return m.group(0).lower()
...
>>> re.sub(r'[A-Z]', lambda m: '_' + m.group(0).lower(), 'camelCase')
'_camel_case'

# 更优雅的方式
>>> import re
>>> def camel_to_snake(name):
...     return re.sub(r'([A-Z])', r'_\1', name).lower().strip('_')
...
>>> camel_to_snake('camelCaseName')
'camel_case_name'
```

#### 3.5.3 re.split() 的捕获组陷阱

```python
# 无分组：正常分割
>>> re.split(r',', 'a,b,c')
['a', 'b', 'c']

# 有分组：分隔符出现在结果中！
>>> re.split(r'(\,)', 'a,b,c')
['a', ',', 'b', ',', 'c']

# 典型陷阱：邮箱分割
>>> re.split(r'[@.]', 'user@example.com')
['user', 'example', 'com']      # ✅ 看起来正常

# 但如果想要保留 @ 和 .
>>> re.split(r'([@.])', 'user@example.com')
['user', '@', 'example', '.', 'com']  # 分隔符混入结果
```

```python
# ✅ 正确做法：用非捕获分组或 post-process
>>> re.split(r'(?:[@.])', 'user@example.com')
['user', 'example', 'com']
```

### 3.6 `re` 模块的深层陷阱

#### 3.6.1 陷阱 1：动态拼接 vs 预编译

```python
# ❌ 每次调用都重新编译（即使 pattern 相同）
def extract_date(text):
    return re.findall(r'\d{4}-\d{2}-\d{2}', text)
    # 每次调用：re.findall → 查缓存 → 编译（若未缓存）→ 执行

# ✅ 预编译：Pattern 对象可复用
_DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')

def extract_date(text):
    return _DATE_PATTERN.findall(text)
    # 直接执行，无编译开销
```

```python
# 性能对比
import timeit

text = '2024-01-01 and 2024-03-15 and 2024-06-30' * 1000

# 动态编译（每次 re.findall 内部查缓存）
t1 = timeit.timeit(lambda: re.findall(r'\d{4}-\d{2}-\d{2}', text), number=1000)

# 预编译 Pattern
pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
t2 = timeit.timeit(lambda: pattern.findall(text), number=1000)

print(f"动态: {t1:.4f}s, 预编译: {t2:.4f}s")
# 实测差距远小于 2-5 倍：re 内部有 512 条缓存，相同 pattern 会命中缓存，
# 预编译只是省去每次的缓存查找/哈希开销（3.12 实测约 1.2-1.4 倍）
```

#### 3.6.2 陷阱 2：findall 的分组合并

```python
# 混合分组与无分组
>>> re.findall(r'(\d+)-(\d+)', '1-2 and 3-4')
[('1', '2'), ('3', '4')]    # 两个分组 → tuple 列表

# 一个分组
>>> re.findall(r'(\d+)-\d+', '1-2 and 3-4')
['1', '3']    # 一个分组 → 字符串列表

# 无分组
>>> re.findall(r'\d+-\d+', '1-2 and 3-4')
['1-2', '3-4']    # 无分组 → 完整匹配列表
```

```python
# ✅ 最佳实践：始终使用 finditer，避免 findall 的歧义
>>> [m.group(0) for m in re.finditer(r'\d+-\d+', '1-2 and 3-4')]
['1-2', '3-4']
>>> [(m.group(1), m.group(2)) for m in re.finditer(r'(\d+)-(\d+)', '1-2 and 3-4')]
[('1', '2'), ('3', '4')]
```

#### 3.6.3 陷阱 3：Unicode 敏感匹配

```python
# \w 在 Unicode 模式下匹配中文！
>>> re.match(r'^\w+$', 'hello')
<re.Match object; span=(0, 5), match='hello'>
>>> re.match(r'^\w+$', '你好')
<re.Match object; span=(0, 2), match='你好'>    # 中文也被视为"单词字符"

# 如果需要纯 ASCII
>>> re.match(r'^[\w]+$', '你好', re.ASCII)
None    # ASCII 模式下 \w 只匹配 [a-zA-Z0-9_]
>>> re.match(r'^\w+$', '你好', re.ASCII)
None

# ⚠️ 注意：re.ASCII 需要显式传入
>>> re.match(r'^\w+$', '你好')   # 默认 Unicode 模式
<re.Match object; span=(0, 2), match='你好'>
```

#### 3.6.4 陷阱 4：`re.sub` 的贪婪替换

```python
# 贪婪替换可能导致意外结果
>>> re.sub(r'<.*>', '', '<div>hello</div>')
''    # ✅ 看起来正确

>>> re.sub(r'<.*>', '', '<div>hello</div><span>world</span>')
''    # ❌ 吞掉了整个字符串！贪婪 .* 匹配到最后一个 >

# ✅ 使用惰性量词
>>> re.sub(r'<.*?>', '', '<div>hello</div><span>world</span>')
'helloworld'    # ✅ 正确
```

#### 3.6.5 陷阱 5：原子分组与拥有量词（3.11+ 已原生支持）

> **版本注意**：Python **3.11** 起（[bpo-433030](https://github.com/python/cpython/commit/345b390ed69f36681dbc41187bc8f49cd9135b54)）标准库 `re` 原生支持**原子分组 `(?>...)`** 与**拥有量词 `*+` `++` `?+` `{m,n}+`**。3.10 及更早版本会报 `re.error: bad character in group name '?>a+'`，旧教程常把这个当"re 不支持"来写——对 3.12–3.14 已不成立。

```python
# ✅ Python 3.11+：原子分组直接可用，且能阻止灾难性回溯
>>> import re, time
>>> re.match(r'(?>a+)b', 'aaaac')          # a+ 吞掉全部 a，b 匹配失败
None                                       # 原子组不回溯 → 立即失败
>>> re.match(r'a++b', 'aaaac')             # 拥有量词写法，等价
None
>>> t0 = time.perf_counter()
>>> re.match(r'(?>(a+)+)b', 'a' * 28 + 'c')   # 原子化后瞬间返回
>>> print(f"{time.perf_counter() - t0:.4f}s") # ≈ 0.0000s（对比下方未原子化的 14s）
```

```python
# ❌ 未原子化时：灾难性回溯依旧（n=28 实测约 14 秒）
>>> import time
>>> t0 = time.perf_counter()
>>> re.match(r'(a+)+b', 'a' * 28 + 'c')
>>> print(f"{time.perf_counter() - t0:.1f}s")
14.1s

# ✅ 重写正则（消除歧义，最简单）
>>> re.match(r'a+b', 'aaaac')
None
```

> **仍不支持**：递归模式 `(?R)`、条件分支 `(?(cond)yes|no)`、`regex` 模块特有的模糊匹配/可变宽度后行断言等——这些仍需要第三方 `regex` 模块（见第 4 章）。

### 3.7 性能基准与优化

#### 3.7.1 编译收益量化

```python
import timeit
import re

pattern_text = r'(?:https?://)?(?:www\.)?[\w.-]+\.[a-z]{2,}'
text = 'Visit https://example.com or http://test.org for more info' * 5000

# 方案 1：每次动态编译
t1 = timeit.timeit(
    lambda: re.search(pattern_text, text),
    number=10000
)

# 方案 2：预编译 Pattern
compiled = re.compile(pattern_text)
t2 = timeit.timeit(
    lambda: compiled.search(text),
    number=10000
)

print(f"动态编译: {t1:.4f}s")
print(f"预编译:   {t2:.4f}s")
print(f"加速比:   {t1/t2:.2f}x")
```

**实测结果**（Python 3.12.13，`number=10000`；数值随硬件波动）：
```
动态编译: 0.0077s
预编译:   0.0056s
加速比:   1.37x
```

> **结论**：因为 `re` 内部有编译缓存，相同 pattern 的"动态编译"实际只是多一次缓存查找，加速比通常在 **1.2–1.4x**，远没有传说中"2–5 倍"。真正值得预编译的场景是：**动态拼接的 pattern**（无法命中缓存）和**超高频热路径**。

#### 3.7.2 正则 vs 字符串方法

```python
# 字符串方法通常比正则更快
import timeit

text = 'hello world' * 1000

# 方法 1：正则
t1 = timeit.timeit(lambda: re.search(r'^hello', text), number=10000)

# 方法 2：startswith
t2 = timeit.timeit(lambda: text.startswith('hello'), number=10000)

# 方法 3：切片 + 比较
t3 = timeit.timeit(lambda: text[:5] == 'hello', number=10000)

print(f"正则: {t1:.4f}s, startswith: {t2:.4f}s, 切片: {t3:.4f}s")
# 典型结果：startswith 和切片比正则快 5-10 倍
```

```python
# 决策矩阵：何时用字符串方法，何时用正则（见下表）
```

| 任务 | 推荐方法 | 原因 |
|------|---------|------|
| 前缀匹配 | `str.startswith()` | O(n) 且无编译开销 |
| 后缀匹配 | `str.endswith()` | 同上 |
| 子串存在 | `str in text` | C 实现，最快 |
| 子串位置 | `str.find()` | 返回索引，比 `search()` 快 |
| 格式验证（复杂） | `re` | 字符串方法无法表达 |
| 提取结构化数据 | `re` | 分组能力 |
| 批量替换 | `re.sub()` | 表达式级替换 |
| 分割（复杂分隔符） | `re.split()` | 正则分隔符 |

#### 3.7.3 VERBOSE 模式的可维护性收益

```python
# ❌ 难以维护的内联正则
PATTERN = re.compile(r'^[\w.-]+@[\w.-]+\.\w{2,}$')

# ✅ VERBOSE 模式：可读性优先
PATTERN = re.compile(r'''
    ^                       # 开头
    [\w.-]+                 # 用户名（字母数字、点、连字符）
    @                       # @ 符号
    [\w.-]+                 # 域名
    \.                      # 点号
    \w{2,}                  # 顶级域名（至少 2 位）
    $                       # 结尾
''', re.VERBOSE | re.IGNORECASE)

# 注释和空白被忽略，正则变成了"自文档化"的代码
```

> **工程影响**：在团队协作中，VERBOSE 模式的可维护性收益远大于微小的性能代价（空白与注释在编译期被忽略，不影响编译产物的匹配速度）。生产级正则建议使用 VERBOSE 模式。

---

## 4. `regex` 模块：超越 `re`

### 4.1 为什么需要 `regex`

Python 标准库 `re` 是**回溯型引擎**（类似 PCRE 风格，不是 POSIX 引擎——POSIX 有"最左最长"语义，`re` 没有），功能稳定但受限。`regex` 是 Matthew Barnett 维护的第三方模块（**自研引擎，与 Oniguruma 无关**；Oniguruma 是另一款日本开发者 K. Kosako 写的引擎，被 Ruby 等使用），API 与 `re` 兼容，提供了大量增强功能：

| 功能 | `re` | `regex` | 应用场景 |
|------|------|---------|---------|
| 原子分组 `(?>...)` | ✅（3.11+） | ✅ | 防止灾难性回溯 |
| 拥有量词 `++` `*+` | ✅（3.11+） | ✅ | 非回溯量词 |
| 条件分支 `(?(cond)y\|n)` | ❌ | ✅ | 动态正则 |
| 模糊匹配 `(?:pat){e<=N}` | ❌ | ✅ | 拼写纠错 |
| 递归模式 `(?R)` | ❌ | ✅ | 嵌套结构 |
| 属性匹配 `\p{Lu}` | ❌ | ✅ | Unicode 脚本级匹配 |
| 可变宽度后行断言 | ❌ | ✅ | 复杂前缀匹配 |
| 分支重置 `(?|...)` | ❌ | ✅ | 各分支分组统一编号 |

### 4.2 核心增强功能

#### 4.2.1 原子分组与拥有量词

```python
import regex

# 原子分组：匹配成功后不回溯
>>> regex.match(r'(?>a+)b', 'aaaac')
None    # a+ 匹配 "aaaa"，然后 b 不匹配 c，但原子分组不回溯 → 整体失败
          # 对比 re：同样失败，但原因不同（re 会回溯尝试所有可能）

# 拥有量词：不回溯的量词
>>> regex.match(r'a++b', 'aaaac')
None    # a++ 拥有所有 a，不回溯

# 灾难性回溯的防护（注意：两个 pattern 必须不同，才有对比意义！）
text = 'a' * 10000 + 'c'
pattern_atomic = regex.compile(r'(?>(a+)+)b')   # 原子化：外层 + 不回溯
pattern_normal = regex.compile(r'(a+)+b')       # 普通：可能灾难性回溯

import time
start = time.time()
pattern_atomic.match(text)
t_atomic = time.time() - start

start = time.time()
pattern_normal.match(text)
t_normal = time.time() - start

print(f"原子分组: {t_atomic:.6f}s")
print(f"普通分组: {t_normal:.6f}s")
# 实测（regex 2026.7.19，Python 3.12）：原子分组 0.000s，普通分组约 0.3s
# （regex 模块对 (a+)+ 有内部优化，不像 re 那样指数爆炸；但原子化依然最快）
```

#### 4.2.2 模糊匹配

`regex` 的模糊匹配语法是 `(?:pattern){e<=N}`（N 为允许的错误数，e=编辑距离），**不是** `(~N)pattern`：

```python
# 允许最多 1 个编辑距离的错误匹配（e = edit distance）
>>> regex.search(r'(?:colour){e<=1}', 'I like the color red')
<regex.Match object; span=(11, 16), match='color', fuzzy_counts=(0, 0, 1)>
# fuzzy_counts=(误插, 误删, 误替)：'color' 比 'colour' 少一个 'u'，计 1 次删除

>>> regex.search(r'(?:flavour){e<=1}', 'I like the flavor')
<regex.Match object; span=(11, 17), match='flavor', fuzzy_counts=(0, 0, 1)>
# 英式 flavour ↔ 美式 flavor，同样 1 次删除
```

> **⚠️ 陷阱**：网上流传的 `(~3)appl` 写法在 `regex` 模块中**不是**模糊匹配语法——`(~3)` 会被当作普通分组尝试匹配字面量 `~3`，返回 `None` 而非报错，极易误导。

#### 4.2.3 Unicode 属性匹配

```python
# 匹配任意 Unicode 字母
>>> regex.findall(r'\p{L}+', 'Hello 世界 World')
['Hello', '世界', 'World']

# 匹配特定脚本
>>> regex.findall(r'\p{Han}+', '中文 English 日本語')
['中文', '日本語']

# 匹配数字（含各种 Unicode 数字）
# ⚠️ 注意：汉字数字（四五六）属于 \p{Lo}（表意文字），不属于 \p{N}！
>>> regex.findall(r'\p{N}+', '123 四五六 ١٢٣')
['123', '١٢٣']
>>> regex.findall(r'\p{Lo}+', '123 四五六 ١٢٣')
['四五六']

# 匹配空白（含 Unicode 空白）——用 \u00a0 表示 NBSP（U+00A0）
>>> regex.findall(r'\p{Z}+', 'a b\u00a0c')
[' ', '\xa0']
```

> **版本注意**：`regex` 模块支持完整的 Unicode 属性，这是 `re` 模块无法比拟的。对于多语言文本处理，`regex` 是更好的选择。

#### 4.2.4 分支重置

```python
# 分支重置：不同分支的分组共享同一编号
>>> m = regex.search(r'(?:(\d+)|([a-z]+))', 'abc')
>>> m.groups()
(None, 'abc')     # 第二组获胜，第一组为 None

>>> m = regex.search(r'(?:(\d+)|([a-z]+))', '123')
>>> m.groups()
('123', None)     # 第一组获胜，第二组为 None

# 分支重置版本：覆盖重复编号
>>> m = regex.search(r'(?|(\d+)|([a-z]+))', 'abc')
>>> m.group(1)
'abc'             # 无论哪个分支获胜，都在 group(1)

>>> m = regex.search(r'(?|(\d+)|([a-z]+))', '123')
>>> m.group(1)
'123'
```

### 4.3 `regex` vs `re`：决策矩阵

| 场景 | 推荐 | 原因 |
|------|------|------|
| 简单文本搜索/替换 | `re` | 标准库，无需额外依赖 |
| 性能敏感 + 简单模式 | `re` + `re.ASCII` | 更快的 Unicode 处理 |
| 防止灾难性回溯 | `re`（3.11+ 原子分组）或 `regex` | 原子化即可，无需第三方 |
| 复杂 Unicode 文本 | `regex` + `\p{}` | 丰富的 Unicode 支持 |
| 模糊搜索/拼写纠错 | `regex` + 模糊匹配 | 编辑距离容差 |
| 嵌套结构解析（有限） | `regex` + `(?R)` | 递归模式 |
| 可变宽度后行断言 | `regex` | `re` 只支持固定宽度 |
| 生产级代码（长期维护） | `re` + VERBOSE | 标准库稳定性优先 |

---

## 5. 工程实践与跨领域对比

### 5.1 正则在不同语言中的实现差异

| 语言/库 | 引擎类型 | 特色功能 | 注意事项 |
|---------|---------|---------|---------|
| Python `re` | 回溯引擎（SRE bytecode） | 命名分组、Unicode、原子分组（3.11+） | 有回溯风险，可原子化防护 |
| Python `regex` | 回溯引擎（Matthew Barnett 自研） | 原子组、条件分支、模糊匹配、可变宽度后行断言 | 第三方，API 与 `re` 兼容 |
| JavaScript `RegExp` | 回溯引擎 | 非捕获分组、lastIndex | 全局模式下 lastIndex 状态残留 |
| Java `Pattern` | 回溯引擎 | 命名分组 `(?<name>...)` | 语法与 Python 略有差异 |
| Go `regexp` | 线性时间（RE2：NFA 模拟 + DFA） | 线性时间、无回溯风暴 | 不支持环视与回溯引用 |
| Rust `regex` | 线性时间（自动机 + 预过滤） | 线性时间、内存安全 | 不支持环视（lookaround） |
| Perl / PCRE | 回溯引擎 | 最丰富的功能 | 灾难性回溯风险最高 |

#### 5.1.1 JavaScript 的 lastIndex 陷阱

```javascript
// ❌ JavaScript 的全局正则有状态
let regex = /abc/g;
console.log(regex.test('xabcy'));  // true
console.log(regex.lastIndex);      // 3

console.log(regex.test('xabcy'));  // false！lastIndex 从 3 开始，找不到
console.log(regex.lastIndex);      // 0（重置）

console.log(regex.test('xabcy'));  // true（lastIndex 重置后恢复正常）

// ✅ 解决方案：每次使用新实例，或手动重置
regex.lastIndex = 0;
```

```python
# Python 的 re 没有这个问题
import re
pattern = re.compile(r'abc', re.I)
print(pattern.search('xabc').group())  # 'abc'
print(pattern.search('xABC').group())  # 'ABC'（忽略大小写，无状态残留）
```

#### 5.1.2 Java 与 Python 的语法差异

```java
// Java：命名分组使用 (?<name>...)
Pattern p = Pattern.compile("(?<year>\\d{4})-(?<month>\\d{2})");
Matcher m = p.matcher("2024-03-15");
if (m.matches()) {
    System.out.println(m.group("year"));   // "2024"
    System.out.println(m.group("month"));  // "03"
}

// Python：同样使用 (?P<name>...)
import re
m = re.search(r'(?P<year>\d{4})-(?P<month>\d{2})', '2024-03-15')
print(m.group('year'))    # "2024"
print(m.group('month'))   # "03"
```

```go
// Go：不支持后行断言（也不支持任何环视）
package main

import (
	"fmt"
	"regexp"
)

func main() {
	// Go 的 regexp（RE2 引擎）不支持 (?<=...)，连先行断言 (?=...) 也不支持
	// 需要用其他方式实现类似功能
	re := regexp.MustCompile(`\d+ USD`)
	fmt.Println(re.FindAllString("Price: 100 USD", -1))  // ["100 USD"]
}
```

### 5.2 正则 vs 解析器生成器

#### 5.2.1 为什么不能用电锯切木头

**核心论点**：正则表达式只能描述**正则语言**（Chomsky 类型 3），而 HTML/XML 的结构是**上下文无关语言**（类型 2）。两者之间存在根本的能力差距。

```
正则语言能做的：
  ✓ 匹配 token 流（关键字、标识符、数字）
  ✓ 验证固定格式（邮箱、IP、日期）
  ✓ 提取简单结构（键值对、URL）

正则语言不能做的：
  ✗ 验证嵌套结构（括号匹配、标签嵌套）
  ✗ 处理任意深度的递归
  ✗ 保证结构合法性（如 HTML 的 balanced tags）
```

**反例证明**：

```python
# 试图用正则验证 HTML 标签嵌套——必然失败
html_examples = [
    '<div><span>text</span></div>',     # 合法
    '<div><span>text</div></span>',     # 非法：标签交叉
    '<div><div><span>deep</span></div></div>',  # 合法但更深层
]

# 不存在一个正则表达式能区分合法和非法嵌套
# 因为 aⁿbⁿ 类结构需要计数，超出正则语言能力
```

#### 5.2.2 Tokenizer 与 Parser 的分层

```
输入文本
    │
    ▼
┌─────────────┐
│  Tokenizer   │  ← 正则擅长：将字符流变为 token 流
│  （词法分析） │     用正则识别：关键字、标识符、数字、字符串
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parser     │  ← 需要上下文无关文法：理解 token 之间的关系
│  （语法分析） │     用 LL/LR 解析器理解：表达式、语句、结构
└──────┬──────┘
       │
       ▼
   AST（抽象语法树）
```

**实际应用**：

```python
# 词法分析：用正则提取 token
import re

TOKEN_PATTERNS = [
    ('COMMENT',  r'#.*'),
    ('NUMBER',   r'\d+\.?\d*'),
    ('STRING',   r'"[^"]*"'),
    ('IDENT',    r'[a-zA-Z_]\w*'),
    ('OP',       r'[+\-*/=]'),
    ('WHITESPACE', r'\s+'),
]

COMPILED_PATTERNS = [(name, re.compile(pattern)) for name, pattern in TOKEN_PATTERNS]

def tokenize(text):
    tokens = []
    pos = 0
    while pos < len(text):
        matched = False
        for name, pattern in COMPILED_PATTERNS:
            m = pattern.match(text, pos)
            if m:
                token = m.group(0)
                if name != 'WHITESPACE':  # 跳过空白
                    tokens.append((name, token))
                pos = m.end()
                matched = True
                break
        if not matched:
            raise ValueError(f"Unexpected character at position {pos}: {text[pos]!r}")
    return tokens

# 测试
print(tokenize('x = 42 # set x to forty-two'))
# [('IDENT', 'x'), ('OP', '='), ('NUMBER', '42'), ('COMMENT', '# set x to forty-two')]
```

#### 5.2.3 解析器生成器 vs 手写解析器

| 方案 | 代表工具 | 适用场景 | 学习曲线 |
|------|---------|---------|---------|
| 解析器生成器 | PLY、Lark、ANTLR | 复杂语言、需要自动生成 AST | 陡峭 |
| 手写递归下降 | — | 中等复杂度、需要精细控制 | 中等 |
| 正则 + 后处理 | `re` | 简单结构、token 级提取 | 平缓 |

```python
# Lark：声明式语法定义
from lark import Lark

grammar = '''
    start: expr
    expr: term (( "+" | "-" ) term)*
    term: factor (( "*" | "/" ) factor)*
    factor: NUMBER | "(" expr ")"
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
'''

parser = Lark(grammar)
tree = parser.parse("3 + 4 * (2 - 1)")
print(tree.pretty())
```

### 5.3 实际项目中的正则工程

#### 5.3.1 日志解析

```python
"""
Nginx 访问日志解析
日志格式：$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
示例：192.168.1.1 - - [15/Mar/2024:10:30:45 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0"
"""
import re
from datetime import datetime
from typing import Optional

NGINX_LOG_PATTERN = re.compile(r'''
    ^(?P<remote_addr>[\d.]+)\s+-\s+(?P<remote_user>\S+)\s+
    \[(?P<time_local>[^\]]+)\]\s+
    "(?P<request>[^"]*)"\s+
    (?P<status>\d{3})\s+(?P<body_bytes>\d+)\s+
    "(?P<referer>[^"]*)"\s+
    "(?P<user_agent>[^"]*)"\s*$
''', re.VERBOSE)

# ⚠️ VERBOSE 模式只忽略"模式里的"空白，日志文本里的空格必须显式匹配
# （上面每个字段之间都用 \s+ / \s* 显式吃掉分隔空白，否则 match 会失败）

def parse_nginx_log(line: str) -> Optional[dict]:
    m = NGINX_LOG_PATTERN.match(line)
    if not m:
        return None
    d = m.groupdict()
    d['time_local'] = datetime.strptime(d['time_local'], '%d/%b/%Y:%H:%M:%S %z')
    return d

# 测试
log_line = '192.168.1.1 - - [15/Mar/2024:10:30:45 +0800] "GET /api/users HTTP/1.1" 200 1234 "-" "Mozilla/5.0"'
print(parse_nginx_log(log_line))
```

#### 5.3.2 数据清洗中的正则

```python
"""
电话号码标准化：支持多种格式，统一为 +86 138xxxx xxxx 格式
"""
import re

PHONE_PATTERNS = [
    # 国内手机号（11 位）
    re.compile(r'1[3-9]\d{9}'),
    # 带区号的固定电话
    re.compile(r'0\d{2,3}[-.]?\d{7,8}'),
    # 国际格式 +86 138...（注意：是 86，不是 86?——那会误匹配 +8）
    re.compile(r'\+?86[-.]?1[3-9]\d{9}'),
]

def normalize_phone(raw: str) -> str:
    """将各种格式的电话号码统一为标准格式"""
    # 清理非数字字符
    digits = re.sub(r'\D', '', raw)

    # 去掉国家码 86 前缀（86 + 11 位手机号 = 13 位）
    if len(digits) == 13 and digits.startswith('86'):
        digits = digits[2:]

    # 剩下 11 位且以 1 开头 → 标准手机号
    if len(digits) == 11 and digits.startswith('1'):
        return f'+86 {digits[:3]} {digits[3:7]} {digits[7:]}'
    return raw  # 无法识别，原样返回

# 测试
test_cases = [
    '13812345678',
    '+8613812345678',
    '86-138-1234-5678',
    '010-12345678',
]
for tc in test_cases:
    print(f'{tc!r:20s} → {normalize_phone(tc)}')
# 实测输出：
# '13812345678'      → '+86 138 1234 5678'
# '+8613812345678'   → '+86 138 1234 5678'
# '86-138-1234-5678' → '+86 138 1234 5678'
# '010-12345678'     → '010-12345678'（固话不在本函数处理范围）
```

#### 5.3.3 安全扫描中的正则

```python
"""
SQL 注入检测：识别常见的注入模式
注意：这只是一个辅助手段，不能完全替代参数化查询
"""
import re

SQL_INJECTION_PATTERNS = [
    # 注释注入
    re.compile(r'(?:--|#|/\*)', re.I),
    # UNION 注入
    re.compile(r'\bUNION\s+SELECT\b', re.I),
    # 布尔注入
    re.compile(r'\bOR\s+\d+\s*=\s*\d+', re.I),
    # 时间延迟注入
    re.compile(r'\bSLEEP\s*\(', re.I),
    # 堆叠查询
    re.compile(r';\s*(?:DROP|INSERT|UPDATE|DELETE)\b', re.I),
]

def detect_sql_injection(text: str) -> list[str]:
    """检测文本中的 SQL 注入模式"""
    matches = []
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return matches

# 测试
tests = [
    "1' OR 1=1 --",
    "admin' UNION SELECT * FROM users --",
    "normal text without injection",
    "1; DROP TABLE users; --",
]
for t in tests:
    result = detect_sql_injection(t)
    print(f'{t!r:40s} → {"INJECTION DETECTED" if result else "CLEAN"}')
```

> **⚠️ 重要声明**：安全扫描正则只能作为**辅助手段**。真正防御 SQL 注入必须使用**参数化查询**。正则无法覆盖所有注入变体。

### 5.4 现代替代方案

#### 5.4.1 树形正则（Tree Regex）

树形正则是一种学术上的扩展，允许在正则中嵌入"树模式"，从而处理一定程度的嵌套结构。但这不是工业级解决方案，理解其原理有助于理解正则的边界。

```
传统正则：   (a+b)+        → 匹配 aab、abb、aaabbb 等
树形正则：   (a<b>)#       → 要求 < 和 > 之间的内容平衡

# 伪代码示例
tree_regex = r'<div>(?<content>.*?)</div>'  # 尝试匹配 balanced tags
# 实际上 Python re 不支持此语法
```

#### 5.4.2 Parsing Expression Grammar（PEG）

PEG 是由 Bryan Ford 提出的解析框架，比正则表达式更强（能描述部分上下文无关语言），同时保持确定性（无回溯歧义）。

```python
"""
使用 lark（PEG 解析器生成器）解析简单的算术表达式
"""
from lark import Lark

expr_grammar = '''
    start: expr
    expr: term (( "+" | "-" ) term)*
    term: factor (( "*" | "/" ) factor)*
    factor: NUMBER | "(" expr ")" | "-" factor
    
    %import common.NUMBER
    %import common.WS
    %ignore WS
'''

parser = Lark(expr_grammar)

# 测试
expressions = ['3 + 4 * 2', '(1 + 2) * 3', '10 / 2 - 3']
for expr in expressions:
    tree = parser.parse(expr)
    print(f'{expr:15s} → {tree.pretty()[:80]}')
```

#### 5.4.3 LLM + 正则：最佳实践

```
大模型时代的正则使用策略：

1. 生成阶段：用 LLM 生成正则表达式草稿
   Prompt: "生成一个匹配 IPv4 地址的正则，要求..."

2. 验证阶段：用测试用例验证正则的正确性
   - 边界用例：合法 IP、非法 IP、边缘格式
   - 性能用例：恶意输入测试（防灾难性回溯）

3. 简化阶段：人工审查，移除不必要的复杂度
   - 用 re.VERBOSE 添加注释
   - 必要时重写为更简洁的形式

4. 安全审查：检查正则的安全性
   - 是否存在灾难性回溯风险？
   - 是否过度匹配（如匹配了不该匹配的字符）？
```

```python
"""
LLM 辅助的正则开发工作流示例
"""
import re
from typing import Callable

class RegexValidator:
    """正则验证器的封装，支持测试和文档化"""
    
    def __init__(self, pattern: str, description: str, 
                 compile_flags: int = 0):
        self.pattern = pattern
        self.compiled = re.compile(pattern, compile_flags)
        self.description = description
        self._test_cases: list[tuple[str, bool]] = []
    
    def add_test(self, text: str, should_match: bool):
        """添加测试用例"""
        self._test_cases.append((text, should_match))
    
    def validate(self, text: str) -> bool:
        """执行验证"""
        return bool(self.compiled.fullmatch(text))
    
    def run_tests(self) -> dict:
        """运行所有测试用例"""
        results = []
        for text, expected in self._test_cases:
            actual = self.validate(text)
            status = '✓' if actual == expected else '✗'
            results.append({
                'text': text,
                'expected': expected,
                'actual': actual,
                'status': status
            })
        return results
    
    def __repr__(self):
        return f'RegexValidator({self.description!r}, pattern={self.pattern!r})'


# 示例：IPv4 地址验证器
ip_validator = RegexValidator(
    pattern=r'^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$',
    description='IPv4 地址验证',
    compile_flags=re.ASCII  # 只匹配 ASCII 数字
)

# 添加测试用例
ip_validator.add_test('192.168.1.1', True)
ip_validator.add_test('255.255.255.255', True)
ip_validator.add_test('0.0.0.0', True)
ip_validator.add_test('256.1.1.1', False)  # 超出范围
ip_validator.add_test('192.168.1', False)  # 缺少一段
ip_validator.add_test('192.168.1.1.1', False)  # 多一段
ip_validator.add_test('abc.def.ghi.jkl', False)  # 非数字

# 运行测试
results = ip_validator.run_tests()
for r in results:
    print(f"{r['status']} {r['text']:20s} expected={r['expected']} actual={r['actual']}")
```

---

## 6. 练习

### 6.1 理论题

**练习 1**：使用泵引理证明 `L = {aⁿbⁿcⁿ | n ≥ 0}` 不是正则语言。
> 提示：取 `w = a^p b^p c^p`，分析 `xy` 的可能位置，推导矛盾。

**练习 2**：为正则表达式 `(a|b)*abb` 构造 NFA，然后使用子集构造算法转换为 DFA，最后最小化 DFA。
> 提示：先画出 NFA 的状态转移图，再逐步推导 DFA 状态。

**练习 3**：证明正则语言在商运算（quotient）下封闭。
> 定义：`L₁ / L₂ = {x | ∃y ∈ L₂, xy ∈ L₁}`

**练习 4**：解释为什么先行断言 `(?=...)` 不增加正则表达式的表达能力。
> 提示：构造一个等价的不使用断言的正则表达式。

### 6.2 编程题

**练习 5**：实现一个简化版的 NFA 模拟器（支持 `.` `*` `|`），验证与 DFA 的等价性。
> 要求：输入正则表达式和字符串，输出是否匹配。

**练习 6**：诊断并修复以下正则的灾难性回溯问题：
```python
import re
pattern = re.compile(r'(a+b)+c')
text = 'a' * 30 + 'd'  # 没有 c，会导致大量回溯
```
> 要求：提供修复方案并解释原因。

**练习 7**：使用 `re.finditer()` 和 `re.VERBOSE` 编写一个能解析简化版 CSV 的正则（支持双引号转义）。
> 格式示例：`"John","Doe","30","Engineer"`

**练习 8**：实现一个电话号码验证器，支持：
- 中国大陆手机号（11 位，13/14/15/16/17/18/19 开头）
- 带国家码的国际格式（+86 或 0086 前缀）
- 固话（区号 3-4 位 + 号码 7-8 位）
- 排除伪号码（如 110、119 等紧急号码）

**练习 9**：对比 `re` 和 `regex` 模块在处理以下场景时的表现：
- 包含中文的多语言文本匹配
- 存在嵌套结构的文本提取
- 模糊匹配（允许 1-2 个字符错误）

**练习 10**：编写一个 ReDoS 测试工具，随机生成正则和输入，检测是否存在灾难性回溯风险。
> 要求：设置超时阈值，超过则报告潜在风险。

### 6.3 综合题

**练习 11**：设计一个简单的 Tokenizer，使用正则表达式识别以下 token 类型：
- 关键字（`if`、`else`、`for`、`while`、`return`）
- 标识符（字母开头的字母数字序列）
- 数字（整数和浮点数）
- 运算符（`+`、`-`、`*`、`/`、`=`、`==`、`!=`）
- 分隔符（`(`、`)`、`{`、`}`、`;`、`,`）
- 注释（`//` 单行注释）

要求：
1. 使用 `re.VERBOSE` 书写可读的正则
2. 预编译所有模式，提升性能
3. 提供测试用例验证正确性

**练习 12**：实现一个"正则表达式可视化"工具，将正则表达式转换为状态转移图（文本形式）。
> 要求：支持基本运算（`|`、`*`、`+`、`?`），展示 NFA 状态转移。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 形式语言 | 正则语言 ⊂ 上下文无关语言；泵引理是证明非正则性的工具 |
| 自动机 | DFA（确定、O(n)）↔ NFA（非确定、功能丰富）等价；子集构造连接两者 |
| 正则语法 | 所有语法糖可翻译回 `|`、`·`、`*` 三运算；断言不增加表达能力 |
| 回溯算法 | 灾难性回溯源于重叠子表达式；原子分组/拥有量词可防护 |
| Python `re` | 预编译 Pattern 对象是性能关键；`findall` 分组歧义需警惕；VERBOSE 提升可维护性 |
| `regex` 模块 | 原子分组、模糊匹配、Unicode 属性；适合复杂场景 |
| 工程实践 | 词法分析用正则，语法分析用解析器；安全扫描正则仅作辅助 |

---

## 进入下一章的准备

正则专题是卷 1 的独立专题，可与后续章节并行学习。掌握本专题后，你应具备：

- ✅ 能解释 DFA 和 NFA 的区别与等价性
- ✅ 能用泵引理证明一个语言不是正则语言
- ✅ 能诊断并修复灾难性回溯问题
- ✅ 能在 `re` 和 `regex` 之间做出正确选择
- ✅ 能书写生产级的 VERBOSE 正则

> **下一步建议**：理解正则的理论边界后，可以深入学习卷 1 第 12 章（元编程）中的 AST 操作，或进入卷 2（科学计算）学习 NumPy 的向量化模式匹配。

---

## 参考资源

1. **《Introduction to the Theory of Computation》** — Michael Sipser（形式语言与自动机理论经典教材）
2. **《Mastering Regular Expressions》** — Jeffrey Friedl（正则工程实践权威著作）
3. **RE2 论文** — Russ Cox, "Regular Expression Matching: the Simple Way"（DFA 正则引擎设计）
4. **Python `re` 文档** — https://docs.python.org/3/library/re.html
5. **`regex` 模块文档** — https://pypi.org/project/regex/
