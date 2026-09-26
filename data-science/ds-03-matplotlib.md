# 第3章 Matplotlib：图形是一棵对象树

> **学习目标**：掌握 matplotlib 的对象模型、坐标变换与渲染流水线，能独立构造出版级多面板图，并能把"图没按预期显示"的每一类根因归结为可断言的检查项。
>
> - **建模型**：把图看成 Figure → Axes → Artist 三级对象树；`plot()` 是造对象不是画图，真正的渲染在 `show()`/`savefig()` 才发生
> - **会定位**：四套坐标系（data / axes / figure / display）随取随用，任何"元素放错位置"的问题都能归因到 transform 选错
> - **会出图**：统计图族按"背后是哪些 Artist"选型不犹豫；GridSpec 多面板、刻度图例标注、色彩管线到手即用
> - **会工程**：rc 可复现配置、矢量/位图输出账算得清、无头渲染进 CI、静默错误清单随查随用

上一章的结尾交付了一张透视表和一条 7 日滚动序列——它们正是本章的输入。但和前两章不同，本章的"底层"不是内存布局也不是计算内核：**numpy 的底层在数据里，pandas 的底层在算法里，matplotlib 的底层在对象图里**。市面上的 matplotlib 材料几乎全是菜谱（"怎么画直方图"），因为菜谱最好写；代价是每个新需求都要重新搜索一遍。本章反其道而行：先花四节把这台机器的构造讲透（对象树、坐标变换、延迟渲染），后面所有图型都是这四节的推论。**学完你应该达到的标准是：给一张没画过的图，能不查手册说出该改哪个对象、该用哪段坐标变换。**

本章有两个边界。第一，**只讲静态出版图这条主线**：动画、渲染器内核、单位机器等实现细节放进配套文件，不打断查阅节奏；seaborn 只讲桥接（3.13），统计推断本身属于 `ds-04`。第二，**每张统计图都标注它的返回容器类型**——这是菜谱知识和模型知识的分水岭。

| 配套文件 | 装什么 | 状态 |
|---------|--------|------|
| `ds-03b-matplotlib-internals.md` | draw 全流水线与 stale 机制、transform 的复合数学、单位机器（日期轴为什么自动）、后端与嵌入、色彩管线内核、渲染成本实测、动画与 blitting、何时离开 matplotlib | 🚧 规划中（纲目见 README） |

**验证环境**：本章所有可执行输出都在 Linux 上的 Python 3.14.4 + matplotlib 3.11.2 + NumPy 2.5.3 + pandas 3.0.6 + seaborn 0.13.2 下实跑得到，后端为无头 **Agg**（3.2.1 设定后 `matplotlib.get_backend()` 返回 `'Agg'`）。计时数字随机器波动，文中只保证数量级，且已标注"本机实测"；输出图片的字节数同理。

---

## 3.0 导读：本章地图与使用方式

### 3.0.1 全章地图

层级标记：● 核心（第一遍必读）· ◐ 进阶（用到再读）· ○ 深水（在配套文件展开）。

全章分三段主线：**架构层（3.2–3.5）**回答"matplotlib 是台什么机器"；**图型层（3.6–3.13）**是这台机器的产出；**工程层（3.14–3.16）**让它进生产。

| 节 | 要解决的问题 | 层级 |
|----|-------------|------|
| 3.1 生态定位与选型 | matplotlib 在绘图生态里的位置，什么时候不用它 | ● |
| 3.2 两条接口 | pyplot 状态机为什么会"串图"，为什么 OO 是正解 | ● |
| 3.3 一切皆 Artist | `plot()` 到底做了什么，图在内存里长什么样 | ● |
| 3.4 Figure 与 Axes 解剖 | `ax.*` 方法动物园的由来，fig 级与 ax 级怎么分工 | ● |
| 3.5 transform 四段链 | 同一个坐标为什么在四个坐标系下含义不同 | ● |
| 3.6 线型图与散点 | 类别轴的等距陷阱、zorder 图层、散点颜色语义 | ● |
| 3.7 统计图族 | 分布/区间/比较怎么选型，每个方法返回什么容器 | ● |
| 3.8 多面板与画布尺寸 | figsize/dpi/字号三尺度怎么换算，布局三件套怎么选 | ● |
| 3.9 色彩系统 | 数值→颜色的完整管线，colorbar 为什么是一根轴 | ●◐ |
| 3.10 标注与精修 | 刻度定位器/格式化器、图例锚定、autoscale 的隐性代价 | ●◐ |
| 3.11 样式与配置 | rcParams 优先级链，怎么写出可复现的绘图配置 | ◐ |
| 3.12 输出与后端 | 矢量/位图的账、SVG 文字为什么不可编辑、无头渲染 | ● |
| 3.13 pandas.plot 与 seaborn | 转发关系、两级 API、返回对象怎么接管 | ● |
| 3.14 性能工程 | 渲染何时变慢，三个杠杆分别值多少 | ◐ |
| 3.15 调试与验证 | 静默错误清单 + 断言式检查（收口） | ● |
| 3.16 综合实战 | 接过 ds-02 产物，出一张出版级多面板图 | ● |

### 3.0.2 三条阅读路线

不必一次读完。按你当下的目的选一条：

- **快查线**（只想把图画出来）：3.6 → 3.7 → 3.8 → 3.9 → 3.10 → 3.12；被坐标或对象卡住时回头补 3.3、3.5
- **系统线**（第一次完整学）：3.1 → 3.16 顺读——架构层四节（3.2–3.5）不可跳过，它们是图型层的推导前提
- **深水线**（要写库、要排诡异问题）：系统线 + 配套文件 `ds-03b` 的全部内容

**菜谱索引**（快查线专用，按需求直达）：

| 想画什么 | 去哪节 |
|---------|--------|
| 折线/散点/子图连线 | 3.6 |
| 直方图、箱线、小提琴、误差条、条形、ECDF | 3.7 |
| 两行代码出多面板、固定图片尺寸 | 3.8 |
| 按数值上色、加 colorbar、换配色 | 3.9 |
| 自定义刻度标签、图例放图外、箭头标注 | 3.10 |
| 全局改字号/改网格/团队统一样式 | 3.11 |
| 存 PDF/SVG/PNG、CI 里出图、Notebook 不弹窗 | 3.12 |
| 接管 `df.plot()` 的图、seaborn 分面 | 3.13 |
| 图太大/导出太慢/点太多卡 | 3.14 |
| 图上有个东西"看不见了" | 3.15 |

### 3.0.3 本章向后续章节交付什么

每节末尾都会重申一次本节交付的接口，汇总如下：

| 本章交付 | 谁在用 |
|---------|--------|
| Artist/transform 延迟渲染心智 | `ds-04` 全部统计图、卷 3–4 的一切可视化排障 |
| 统计图选型表与容器类型 | `ds-04` 分布图与置信区间、卷 3 的 ROC/混淆矩阵/学习曲线 |
| GridSpec 多面板报告图模板 | 卷 3 工作报告、卷 5 指标看板 |
| rc 可复现配置与团队样式骨架 | 全书统一绘图风格、各卷的图注格式 |
| 矢量输出账与无头渲染模板 | CI 图片产物、论文/报告出图 |
| seaborn 两级 API 桥接 | 卷 3 分面统计图、卷 4 训练曲线 |
| 图形契约断言与静默错误清单 | 与 `ds-01` 1.17、`ds-02` 2.14 构成全书统一的验证方法论 |

### 3.0.4 代码、答案与文献约定

- **代码**：概念演示用 REPL 会话（带 `>>>`），完整实验用脚本块；输出为实跑结果。所有示例只创建 Figure 不弹窗（Agg 后端），可直接在无显示环境复现。
- **答案**：与 `ds-00`/`ds-01`/`ds-02` 一致，随堂自测与章末练习都不附参考答案；数值题用文中同款代码当场核对。
- **文献**：正文用 `> **延伸阅读**：……` 指向章末参考文献；需要实现细节时，进配套文件 `ds-03b`。

> **版本注意（matplotlib 3.11 基线）**：本章以 matplotlib 3.11 为准，与旧教程有五处显著差异，正文中会逐一标注——
> ① `ax.hist` **没有 `stat=` 参数**（那是 seaborn 的），比例化用 `density=True`（3.7）；
> ② `plt.cm.get_cmap` / `ax.cmap` 注册表写法自 matplotlib 3.9 起移除，统一用 `matplotlib.colormaps["name"]`（3.9）；
> ③ 布局用 `layout=` 关键字（`plt.subplots(layout="constrained")`，3.6+），`tight_layout()` 仍可用但逐步让位（3.8）；
> ④ 后端改为注册表（`matplotlib.backends.registry.BackendRegistry`，3.9+），`rcsetup.interactive_bk` 之类的旧属性已删（3.12）；
> ⑤ pandas 3 侧的连带：`Period` 用 `freq="M"`、`DatetimeIndex` 用 `"ME"`，画 Period 轴时数据被自动转成 `datetime64`（回链 ds-02 版本注意第⑤条，见 3.13）。
> seaborn 0.13 侧还有一条：分面后的 `FacetGrid` 上访问 `.ax` 直接抛错，要用 `.axes`（3.13 实测）。

---

## 3.1 matplotlib 解决什么问题：生态定位与选型

### 3.1.1 命令式绘图 vs 声明式绘图

绘图库分两个代际，差别不在美丑而在**你向库描述什么**：

- **命令式（imperative）**：你指挥画笔，一步步往画布上"放东西"。matplotlib 是典型——`ax.plot()`、`ax.annotate()` 每一步都在创建对象，最终由你负责让它们组成一张合理的图。
- **声明式（declarative）**：你只描述"数据列 → 视觉通道（x/y/颜色/大小）"的映射，剩下的布局、图例、刻度由库推导。Vega-Lite/Altair、Plotly、ggplot2 是典型。

| 维度 | 命令式（matplotlib） | 声明式（Altair/Plotly） |
|------|---------------------|------------------------|
| 控制力 | 每个像素都能管（3.5 的坐标变换是极限控制） | 管到"语法"为止，长尾需求要绕 |
| 交互 | 需要额外工程（mpld3/ipympl） | 内建（悬停/缩放/筛选） |
| 学习曲线 | API 面积大，**但模型只有四个概念**（3.2–3.5） | 起步平缓，长尾需求时反而陡 |
| 输出 | 矢量出版级（SVG/PDF/PGF→LaTeX） | 主要是 HTML/JSON |
| 图数据量 | 十万点级（3.14 实测） | 浏览器侧通常先卡 |

两条经验定位：**出版/论文/静态报告 → matplotlib；交互探索/Web 报表 → 声明式库**。而 3.13 会看到，seaborn/pandas 已经替你在 matplotlib 之上补了大半层声明式语法——两者不是对立而是分层。

### 3.1.2 它是底层画布：整个生态都骑在上面

matplotlib 的真实地位是 Python 可视化的**事实标准渲染层**。证据是它到处"被返回"：

```python
>>> import matplotlib.pyplot as plt, pandas as pd, seaborn as sns
>>> df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 1, 2]})
>>> isinstance(df.plot(kind="line"), plt.Axes)     # pandas 画完还给你一个 matplotlib Axes
True
>>> isinstance(sns.regplot(data=df, x="a", y="b"), plt.Axes)   # seaborn 的 axes 级 API 同样
True
```

`pandas.plot`、`seaborn`、`ggplot`（pd visualization）、sklearn 的示例图、TensorBoard 的图……最终都返回或操作 matplotlib 的 `Axes`。这意味着两件事：

1. **学会接管 `Axes` = 学会接管整个生态的输出**——库画完，你还能继续精修（3.13.3）；
2. **只学"某个库怎么画"永远差一层**——出了样式/坐标问题，所有库的答案都会指向同一个地方：matplotlib 的对象模型。

> **机制洞察**：这就是为什么本章先讲对象树再讲图型。上游库（seaborn/pandas）只是"批量调用 `ax.*` 方法的代码"，你读懂了 3.3–3.5，它们的返回值就不再是黑箱。

### 3.1.3 什么时候不该用 matplotlib

| 场景 | 更好的选择 | 代价 |
|------|-----------|------|
| Jupyter 里快速看一眼分布 | `df.col.hist()`（pandas 一行） | 样式糙，但 0 学习成本 |
| 统计分面图（按类别铺网格 + 估计量） | seaborn（3.13 接管） | 自定义长尾时仍要回 matplotlib |
| Web 交互报表、仪表盘 | Plotly / Altair→Vega | 出版级排版弱 |
| 海量点的交互探索 | datashader / deck.gl | 静态出版弱 |
| 一切出版级静态图、LaTeX 论文图 | **matplotlib** | —— |

判断顺序和全书一致：**先用上游省事（pandas.plot/seaborn），被长尾需求卡住时下潜到 matplotlib 原生，仍不够再换生态**。本章教的就是"下潜"的那一层。

**随堂自测 3.1**

1. 命令式与声明式绘图的根本分界是什么？各举一个本节之外的例子。
2. `sns.regplot()` 返回 `Axes` 意味着什么？给一个"先让 seaborn 画、再用 matplotlib 改"的具体需求。
3. 什么时候"用 pandas 一行画"反而是正确选择？什么时候不是？
4. 论文插图要求 300 dpi 且字号与 LaTeX 正文一致，选哪个生态？为什么？

**本节交付**："底层画布"的定位与选型矩阵，是后续所有章节选工具的依据；"上游库只是批量调用 `ax.*`"这条判断，是 3.13 桥接节的前提。

---

## 3.2 两条接口：pyplot 状态机与 OO 对象树

matplotlib 有两个平行的写法，新教程常把它们并列成"风格选择"。**这不是风格，是两套架构**：一套是为 MATLAB 迁移者设计的全局状态机，一套是底层的真实模型。本节用可复现实验说明为什么串图 bug 是原理必然、为什么 OO 是唯一正解。

### 3.2.1 pyplot 是什么：缓存"当前图"的模块级状态

pyplot 是一个模块级状态缓存：它记住"当前 Figure"和"当前 Axes"，让你不用传递对象就能画图——和 MATLAB 的 global workspace 同构。

```python
>>> import matplotlib
>>> matplotlib.use("Agg")            # 必须在 import pyplot 之前设置（3.12 展开）
>>> import matplotlib.pyplot as plt
>>> plt.close("all")                          # 清掉上一节残留，本块从单图状态开始
>>> fig = plt.figure()
>>> ax1 = fig.add_subplot(121)
>>> ax2 = fig.add_subplot(122)
>>> _ = ax1.plot([1, 2, 3]); _ = ax2.plot([3, 2, 1])
>>> plt.gca() is ax2                 # "当前 Axes"就是最后创建的那个
True
>>> plt.gcf() is fig                 # "当前 Figure"同理
True
>>> plt.get_fignums()                # 状态机维护着一张 figure 管理表
[1]
```

`plt.plot` = `plt.gca().plot`，`plt.title` = `plt.gca().set_title`。**pyplot 不提供任何底层做不到的能力**——它只是把"先拿到 ax"这一步省掉了，代价是你再也说不清"现在拿到的是哪个 ax"。

### 3.2.2 串图复现：状态机的两个必然 bug

**Bug 1：循环/函数里 figure 泄漏。** 每次迭代都新建 figure 但从不关闭：

```python
>>> plt.close("all")
>>> for i in range(3):
...     fig = plt.figure()
...     l = plt.plot([i, i + 1], [0, 1])   # 状态式画图，忘了 savefig/close
>>> plt.get_fignums()                       # 3 个 figure 全部挂在内存里
[1, 2, 3]
```

**Bug 2：画到"错的图"上。** 状态跟着创建顺序走，与代码顺序无关：

```python
>>> plt.close("all")
>>> fig1 = plt.figure(); _ = plt.plot([1, 2])
>>> fig2 = plt.figure(); _ = plt.plot([3, 4])
>>> plt.gca().set_title("title lands on fig2")
Text(0.5, 1.0, 'title lands on fig2')
>>> [ax.get_title() for ax in fig1.axes], [ax.get_title() for ax in fig2.axes]
([''], ['title lands on fig2'])
```

两行代码之间插了一个 `plt.figure()`，title 就落到了上一张图上——**在函数里、在 notebook 的多个 cell 之间、在库代码的深处，你无法保证"当前 Axes"还是你以为的那个**。这就是"串图"的全部机制，与手误无关，是状态机的必然。

### 3.2.3 使用纪律：哪些地方允许 pyplot

| 场景 | 用法 | 理由 |
|------|------|------|
| 一行流快速看数据 | `plt.plot(...)` 允许 | 即时反馈，单图无状态风险 |
| **拿到 `fig, ax` 之后的所有操作** | 只用 `ax`/`fig` 上的方法 | `plt.subplots()` 的返回值就是 OO 入口 |
| 循环、函数、库代码、notebook 多 cell | **禁止无主 pyplot 调用** | 状态归属不可考（3.2.2） |
| 批量出图 | 循环内 `fig, ax = plt.subplots()` + `plt.close(fig)` | 每张图显式建、显式关 |

一条可以背下来的纪律：**`plt` 只用来做两件事——建图（`plt.subplots`/`plt.figure`/`plt.close`）和保存（`plt.savefig`），其余一律走 `fig`/`ax`。** 更多状态机细节与 figure manager 的实现，见配套文件 `ds-03b` B1。

> **⚠️ 陷阱**：`matplotlib.use("Agg")` 与 `matplotlib.rcParams` 的全局设置**必须发生在 `import matplotlib.pyplot` 之前**才对后端生效；已经 import 过 pyplot 后再改，部分设置只影响新建对象。无头环境（CI/服务器）最稳的做法是在进程环境变量里设 `MPLBACKEND=Agg`（3.12.4）。

> **延伸阅读**：pyplot 的 figure manager 状态表、`gca()` 的完整查找路径、stale 标记与重绘触发时机，见配套文件 `ds-03b` 第 B1 节。

**随堂自测 3.2**

1. `plt.plot(x, y)` 和 `ax.plot(x, y)` 在数据存储上有区别吗？在状态上有区别吗？
2. 用两行代码复现"title 画到上一张图"的 bug，再用 OO 写法重写成不会出错的版本。
3. 为什么"notebook 多 cell"是 pyplot 全局状态的高危场景？给出你的防范姿势。
4. `plt.gca()` 在一个从未绘图的 figure 上调用会发生什么（试一试）？这说明"当前 Axes"是惰性创建的吗？

**本节交付**：OO 优先从"最佳实践建议"升级为"状态机原理的必然结论"；`plt` 只管建图与保存的纪律，是后面 15 节所有代码的书写格式；串图 bug 归入 3.15 静默错误清单。

---

## 3.3 一切皆 Artist：图的内存模型

这一节是全章的地基。只需回答三个问题：`plot()` 到底做了什么、图在内存里长什么样、什么时候真正被画出来。答案分别是：**造对象、造一棵对象树、最后才画**。

### 3.3.1 plot() 不画图，只是造对象

```python
>>> fig, ax = plt.subplots()
>>> ret = ax.plot([1, 2, 3], [4, 5, 6], label="a")
>>> ret                                          # 返回一个 list（不是 None！）
[<matplotlib.lines.Line2D object at 0x74e52f8be120>]
>>> type(ret[0]).__name__
'Line2D'
>>> lines = ax.plot([3, 2, 1], [6, 5, 4], label="b")
>>> ax.lines                                     # Axes 是这些对象的容器（列表视图）
<Axes.ArtistList of 2 lines>
>>> ax.lines[0] is ret[0]                        # 同一个对象，不是拷贝
True
```

关键事实链：`plot()` **返回数据对象本身**，数据（`x/y` 数组）被存进 `Line2D`，坐标变换（3.5）被挂到对象上——此刻屏幕上什么都没发生。这带来三个直接推论：

1. **改图 = 改对象**：`ret[0].set_color("red")` 立即改的是内存里的属性，下次渲染时生效；
2. **返回值可以继续加工**：`l, = ax.plot(...)` 解包拿到句柄，后面 `l.set_linewidth(3)`；
3. **不保存返回值也能改**：容器（`ax.lines`）永远找得到它们。

```python
>>> ret[0].set_color("red"); ret[0].get_color()
'red'
```

### 3.3.2 对象树：Figure 装 Axes，Axes 装 Artist

图在内存里是一棵有限深的树，`get_children()` 遍历它：

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([1, 2, 3], [1, 2, 3])
>>> sorted({type(k).__name__ for k in fig.get_children()})
['Axes', 'Rectangle']
>>> sorted({type(k).__name__ for k in ax.get_children()})
['Line2D', 'Rectangle', 'Spine', 'Text', 'XAxis', 'YAxis']
```

翻译成结构表：

| 层 | 成员 | 说明 |
|----|------|------|
| `Figure` | `Axes`、背景 `Rectangle` | Figure 本身也是 Artist（可 `set_facecolor`） |
| `Axes` | `Line2D`×n、`Rectangle`（背景 patch）、`Spine`×4、`Text`（标题/轴标签）、`XAxis`/`YAxis` | **Axes 自己也是 Artist**，可整体设透明度/背景 |
| `XAxis`/`YAxis` | 刻度线 `Line2D`、刻度标签 `Text`、`Formatter`/`Locator` | 3.10 拆开讲 |
| 你创建的一切 | `Line2D`、`Rectangle`、`PathCollection`、`Legend`、`Colorbar`…… | **全是 Artist 子类** |

配套的容器属性（按类型取回对象的固定入口）：

| 容器 | 内容 | 典型用途 |
|------|------|---------|
| `ax.lines` | Line2D | 改某条线、删某条线 |
| `ax.patches` | Rectangle/Polygon 等 | 柱、直方图柱、色块 |
| `ax.collections` | PathCollection/PolyCollection | 散点、填充区间 |
| `ax.texts` | Text | 独立文本标注 |
| `ax.images` | AxesImage | `imshow` 结果 |
| `ax.containers` | BarContainer/ErrorbarContainer 等 | 方法返回的成组对象（3.7） |

### 3.3.3 延迟绘制：stale 一树，draw 一次

改了对象之后图不会自动更新——对象上有个 `stale` 标记，改动把它置真，真正的渲染只发生在两个入口：

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([1, 2, 3])
>>> ax.set_title("later")
Text(0.5, 1.0, 'later')
>>> fig.stale                                    # 改动向上传播，整棵树标记为"脏"
True
>>> import io, matplotlib.image as mpimg
>>> buf = io.BytesIO(); fig.savefig(buf, format="png")
>>> mpimg.imread(io.BytesIO(buf.getvalue())).shape   # 此刻才光栅化
(480, 640, 4)
```

三个入口、三种去向：`plt.show()` 交给交互后端弹窗、`fig.savefig()` 交给输出后端写文件、`fig.canvas.draw()` 交给渲染器画进内存画布（3.14 计时就测它）。**"画完还能改"的全部原理就在这**：对象常驻，渲染瞬时。

> **机制洞察**：延迟渲染意味着**你看到的从来不是"当前状态"，而是"上一次 draw 时刻的快照"**。Notebook 里"改了没生效"九成是没重跑绘图单元；脚本里"删了还在"要怀疑删错了对象（3.3.4 的 `remove()`）。stale 的传播规则与 draw 流水线是配套文件 `ds-03b` B1 的主题。

### 3.3.4 属性设置三式与 property cycle

Artist 的属性永远是"getter/setter 对"，设置有三种等价写法：

```python
>>> l, = ax.plot([1, 2], [1, 2])
>>> l.set_linewidth(4); l.get_linewidth()        # ① 显式 setter（最直白）
4.0
>>> plt.setp(l, linewidth=2, linestyle="--")     # ② setp：批量设置，常用于脚本
[None, None]
>>> l.get_linewidth(), l.get_linestyle()
(2.0, '--')
>>> _ = ax.plot([1, 2], [2, 1], lw=1, ls=":")    # ③ 画的时候用缩写 kwargs 直接给
```

kwargs 不是三套词典——`color/c/lw/linewidth/linestyle/ls` 全部归一到同一张属性表（`Artist.set` 的别名解析），写错名字会直接报错而非静默忽略（这条报错机制是 3.15 排查树的"显式失败"一类）。

每条线的颜色从哪来？**属性循环（property cycle）**，全局 rc 配置的一条：

```python
>>> matplotlib.rcParams["axes.prop_cycle"].by_key()["color"][:3]
[(0.12156862745098039, 0.4666666666666667, 0.7058823529411765), (1.0, 0.4980392156862745, 0.054901960784313725), (0.17254901960784313, 0.6274509803921569, 0.17254901960784313)]
```

不指定 `color=` 时按这条循环逐条取色——这就是"同一张图上第 2 条线自动变橙"的机制，也是改配色只需要改 rc 一处的原理（3.11）。

### 3.3.5 对象的生命周期：remove() 只是摘链

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([1, 2], [1, 2], [2, 1], [1, 2])   # 一次调用画两条
>>> gone = ax.lines[0]
>>> gone.remove()
>>> len(ax.lines)                                 # 从树上摘掉了
1
>>> gone in ax.lines                              # 已不在容器里
False
>>> gone.set_color("blue"); gone.get_color()      # 但对象还活着（你手里还有引用）
'blue'
```

`remove()` 解除的是"父容器 → 子对象"的链接，画面上消失；但**你手里的引用仍然指向它**，再 `set_*` 不会再出现在图上——"改了没反应"的一类根因。反过来，垃圾回收会处理无引用的孤儿对象，但**figure 本身不 remove 就一直挂着**（3.2.2 的泄漏、3.14 的内存反模式）。

> **⚠️ 陷阱**：`ax.cla()` / `ax.clear()` 清空的是**当前 axes 上**的一切（包括 xlim、标签），`fig.clf()` 清整个 figure——它们是"重画一张"的捷径，但在函数里用会连带清掉调用方刚设置的样式。要删单个对象永远用 `obj.remove()`。

> **延伸阅读**：stale 的传播与 draw 触发链、`Artist.set` 的别名归一实现、`remove()` 的解链细节，见配套文件 `ds-03b` 第 B1 节。

**随堂自测 3.3**

1. `ax.plot(...)` 的返回值是 `None` 还是对象？不保存它时，事后想改这条线有哪两条路？
2. 写一段代码证明：`set_title` 之后、`savefig` 之前，像素没变（提示：两次 savefig 对比字节/形状）。
3. `ax.patches` 里现在有 3 个 Rectangle（3 条柱），再调一次 `ax.hist` 后有几个？为什么（用 3.4 的证据回答）？
4. `l.remove()` 之后 `l.set_color("blue")` 为什么不改变画面？
5. "图改了但 notebook 没更新"有哪两种机制性根因？

**本节交付**："造对象 → 挂树上 → 延迟渲染"三段心智是全章推导的前提；容器属性表（`ax.lines/patches/collections`）是 3.15 断言检查的取数入口；property cycle 交付给 3.11 配置与 3.9 色彩。

---

## 3.4 Figure 与 Axes 解剖：子图布局与方法动物园

3.3 讲了"放进去的是什么"，本节讲"放进去的容器怎么建、怎么分工"。两个核心认识：**Figure 是画布容器、Axes 才是坐标系**；**几十个 `ax.*` 方法只是"造 Artist + 自动缩放 + 返回容器"的包装器**。

### 3.4.1 三种建图法与 fig/ax 分工

```python
>>> fig, ax = plt.subplots()                  # ① 九成场景：一次拿齐（内部=add_subplot(111)）
>>> fig, axes = plt.subplots(1, 2)            #    规则网格
>>> gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1])   # ② 自由布局（3.8 展开）
>>> axA = fig.add_subplot(gs[:, 0])
>>> axB = fig.add_axes([0.7, 0.1, 0.25, 0.8]) # ③ 精确矩形 [left, bottom, w, h]（分数坐标）
```

归属纪律——**同一件事只有一个正确层级**，写错层级是"设置了却没生效"的常见根因：

| 你要设的 | 层级 | 错误写法 → 后果 |
|---------|------|----------------|
| 标题（单面板） | `ax.set_title` | `fig.suptitle` → 多面板时全都叠到 figure 顶部 |
| 标题（整图总标题） | `fig.suptitle` | `ax.set_title` → 只有一个面板有标题 |
| 图例（跟随数据） | `ax.legend` | `fig.legend` → 图例不随面板、handles 收不全 |
| 轴标签 | `ax.set_xlabel` | fig 级无此 API（强制你走对） |
| 尺寸/DPI | `fig.set_size_inches` / `fig.set_dpi` | ax 级无此 API |
| 背景色 | `fig.set_facecolor` / `ax.set_facecolor` | 二者独立（论文模板常要区分） |

### 3.4.2 方法动物园：每个方法 = 造一批 Artist + autoscale

`ax` 上有近百个 `plot` 系方法，但没有一个引入新概念——它们全是同一模式。实测返回值：

```python
>>> fig, ax = plt.subplots()
>>> bars = ax.bar(["a", "b", "c"], [3, 1, 2])
>>> type(bars).__name__, type(bars[0]).__name__, len(bars)
('BarContainer', 'Rectangle', 3)
>>> [type(p).__name__ for p in ax.patches]      # 已经挂进树了
['Rectangle', 'Rectangle', 'Rectangle']
>>> h = ax.hist([1, 1, 2, 3, 3, 3, 4])          # 返回 (频数, 分箱边界, 容器)
>>> (len(h), type(h[2]).__name__)
(3, 'BarContainer')
>>> len(ax.patches)                             # hist 又叠了 10 根柱上去
13
>>> type(ax.scatter([1], [2], c=[5])).__name__
'PathCollection'
```

三句话总结动物园：

1. **`ax.bar` → 一组 `Rectangle`（装在 `BarContainer` 里）；`ax.hist` → 又一组 Rectangle；`ax.scatter` → 一个 `PathCollection`**——都是 3.3 的 Artist，只是批量创建；
2. **方法顺手做 autoscale**：造完对象把数据范围报给轴，xlim/ylim 自动扩（3.10.4 讲它的代价）；
3. **返回值是容器不是画面**：拿到 `BarContainer` 就能逐根 `rect.set_hatch(...)`，与手搓 Rectangle 等价——**"方法能做的，手工摆 Artist 都能做"，反之亦然**。

这也直接回答了 3.3 自测第 3 题：同一 axes 上先 `bar` 再 `hist`，`ax.patches` 从 3 涨到 13——**组合图（柱+线+参考带）的原理就是往同一个容器里反复加对象**。

### 3.4.3 双轴与副轴：twinx 挂第二套坐标系

```python
>>> fig, ax = plt.subplots()
>>> ax2 = ax.twinx()
>>> type(ax2).__name__, ax2.figure is fig       # ax2 就是同 figure 上的第二个 Axes
('Axes', True)
>>> ax2.xaxis is ax.xaxis                       # x 轴对象是两个（不是同一个）
False
>>> ax2 in ax.get_shared_x_axes().get_siblings(ax)   # 但通过 Grouper 绑进了同一个共享组
True
>>> ax.set_xlim(0, 100)                          # set_xlim 返回新 limits
(0.0, 100.0)
>>> ax2.get_xlim()                               # 另一个 Axes 的 xlim 跟着变
(np.float64(0.0), np.float64(100.0))
>>> len(fig.axes)                               # colorbar、inset 也各占一个 Axes（3.9）
2
```

`twinx` 的构造 = **同位置新 Axes + 共享 x 组 + 右侧 y 轴 + 隐藏上/右脊线以外的刻度**。两个要点：

- **左右轴读错边是静默错误的常客**（进 3.15 清单）：两条线量纲不同，颜色对应哪条轴要靠图例/颜色约定说清；
- **`figure.axes` 的顺序就是创建顺序**，3.15/3.16 的断言按索引取面板时以此为准。

> **机制洞察**：共享轴的底层是 `Grouper`（对象组），不是同一个 Axis 对象——所以 `sharex=` 的两个 axes 各有自己的 `XAxis` 实例、独立的刻度状态，却联动 limits。`twinx` 的"共享 x"和"独立 y"可以分别从这两个事实推出来。坐标共享与刻度联动的分离，3.8.4 再算一次账。

> **⚠️ 陷阱**：`ax.twinx()` 之后，**对 `ax2` 调 `ax2.set_xlim` 会因共享而改掉 `ax` 的 xlim**（它们在一个组里）；要解除用 `ax2.get_shared_x_axes().remove(ax2)`。同理，在共享组里手动设了 xlim 会关掉双方的 autoscale（3.10.4）。

> **延伸阅读**：`add_gridspec`/`add_axes` 的分数坐标与 transAxes 的关系、`Grouper` 的共享实现，见配套文件 `ds-03b` 第 B2 节。

**随堂自测 3.4**

1. `ax.plot` 返回 list、`ax.bar` 返回 `BarContainer`、`ax.hist` 返回 tuple——共同点是什么？为什么 matplotlib 不统一返回类型（提示：hist 还要回传分箱边界）？
2. 单面板图的标题写 `fig.suptitle` 会有什么可见问题？多面板图呢？
3. 在同一 axes 上"先画直方图、再叠一条核密度线、最后加一条参考竖线"，三个对象分别是什么类型、进哪个容器？
4. `twinx()` 后 `len(fig.axes)` 是几？colorbar 还会再加一个吗（3.9 验证）？
5. 为什么"方法动物园"意味着没学过的方法也能上手（给出你的推导步骤）？

**本节交付**：fig 级/ax 级归属表消灭"设了没生效"一族错误；"方法 = 造 Artist + autoscale + 返回容器"是 3.7 统计图选型的统一框架；`twinx`/共享组机制归入 3.15 双轴静默错误。

---

## 3.5 transform 四段链：数据坐标到屏幕坐标

"标注飞了""文字跑到图外面""改了 xlim 元素位置全乱"——这些抱怨的根因几乎总是同一个：**在错误的坐标系里给点**。matplotlib 同时活着四套坐标系，任何一个点交给它，都必须先说清"这是哪套坐标系的点"。

### 3.5.1 四套坐标系

| 坐标系 | 原点 | 范围 | 谁在用 |
|--------|------|------|--------|
| **data** | 数据里的点 | `xlim`/`ylim` 决定 | 数据点、`ax.plot(x, y)` |
| **axes** | axes 左下角 | 0–1（可越界） | 贴着面板放的元素：面板内角标 `(0.02, 0.98)` |
| **figure** | 画布左下角 | 0–1（可越界） | 跨面板元素：总标题、整图注记 |
| **display** | 画布左下角 | 像素（device） | 渲染器内部、blitting 打算盘（`ds-03b` B7） |

前三个是"分数世界"，display 是"像素世界"；**所有变换的终点都是 display**。`ax.transData`/`ax.transAxes`/`fig.transFigure` 就是三座桥，`.transform(点)` 过桥、`.inverted().transform(点)` 回桥。

### 3.5.2 同一个点，四种含义：实测

```python
>>> fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
>>> _ = ax.set_xlim(0, 10); _ = ax.set_ylim(0, 10)   # 两者都返回新 limits（3.4.3 实测过，此处丢弃）
>>> pt = (5.0, 5.0)
>>> for name, tr in [("transData", ax.transData), ("transAxes", ax.transAxes),
...                  ("transFigure", fig.transFigure)]:
...     print(f"{name:>11} {tuple(round(float(v), 1) for v in tr.transform(pt))}")
  transData (307.5, 198.0)
  transAxes (2400.0, 1584.0)
transFigure (3000.0, 2000.0)
```

同一个 `(5.0, 5.0)`：按 data 解释是"面板正中"（xlim 0–10 的中点）→ 像素 (307.5, 198)；按 axes 解释是"500% 的位置"（0–1 之外 5 倍）→ 冲出画布的 (2400, 1584)；按 figure 解释同理冲到 (3000, 2000)。**transform 不做任何"聪明的猜测"——它只按你给的解释规则执行。**

更妙的是反过来看：axes 的中心点 `(0.5, 0.5)` 走 `transAxes` 得到 (307.5, 198.0)——**和 data 的 (5, 5) 落在同一个像素**。四套坐标系描述的是同一张画布，只是各自的记法不同：

```python
>>> ax.transAxes.transform((0.5, 0.5)) == ax.transData.transform((5, 5))   # 同一像素，两套记法
array([ True,  True])
>>> ax.transData.inverted().transform((307.5, 198.0))   # display → data 回桥
array([5., 5.])
```

### 3.5.3 组合与反查：`+` 是串联，`.inverted()` 是反向

复合变换用 `+`（**先左后右**）。下面把"axes 分数 (0.5, 0.5)"先转 display、再逆回 data：

```python
>>> ax.transData.inverted().transform(ax.transAxes.transform((0.5, 0.5)))   # axes 分数 → display → data
array([5., 5.])
```

实践里最常用的三个选择：

| 需求 | 写法 |
|------|------|
| 元素钉在面板某处、**不随数据范围变** | `transform=ax.transAxes` |
| 元素锚定某个数据点、**xlim 变化时跟随** | `transform=ax.transData`（默认） |
| 从锚点**偏移固定像素**（标注箭头文字） | `textcoords="offset points"` |

第三条的实测——`annotate` 的锚点在 data、文字在像素偏移：

```python
>>> a = ax.annotate("mark", xy=(2, 2), xytext=(10, -15),
...                 textcoords="offset points", arrowprops=dict(arrowstyle="->"))
>>> a.xy, a.get_position()
((2, 2), (10, -15))
```

**锚定效果验证**：`transAxes` 写的角落文字，在 xlim 从 (0,1) 改到 (0,1000) 前后纹丝不动：

```python
>>> fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
>>> _ = ax.plot([0, 1], [0, 1])
>>> t = ax.text(0.02, 0.98, "hi", transform=ax.transAxes, va="top")
>>> fig.canvas.draw(); p1 = ax.transAxes.transform((0.02, 0.98))
>>> _ = ax.set_xlim(0, 1000); fig.canvas.draw(); p2 = ax.transAxes.transform((0.02, 0.98))
>>> tuple(round(float(v), 1) for v in p1), tuple(round(float(v), 1) for v in p2)
((84.3, 345.8), (84.3, 345.8))
```

而同样位置若用 data 坐标给，xlim 一改就飞走——**"位置对不对"在画出来之前就能断言**（3.15.3 用的就是这招）。

### 3.5.4 混合变换：axhline 为什么自动贯穿

`ax.axhline(y)` 是四段链的最佳教具——它的一条线**同时用两套坐标系**：

```python
>>> h = ax.axhline(1.5)
>>> h.get_ydata(), h.get_xdata()
([1.5, 1.5], [0, 1])
>>> type(h.get_transform()).__name__
'BlendedGenericTransform'
```

路径是 `x∈[0,1]`、`y∈[1.5, 1.5]`：**x 段按 axes 分数解释（自动贯穿整幅面板），y 段按 data 解释（贴在 1.5 上）**，`BlendedGenericTransform` 把两个方向的变换拼起来。所以参考线/参考带（`axvspan`/`axhspan`）天生"贴数据、贯穿画面"，改 xlim 不影响它的视觉行为。看懂这个 blend，也就看懂了 3.5 表格里"谁在用"那一列的全部设计动机。

> **机制洞察**：四段链的数学（仿射复合、`transData = transScale + transLimits` 的拆解、offset transform 的实现）在配套文件 `ds-03b` B2 展开；主章只要求达到一个标准——**看到"元素放错位置"，第一反应是检查 `transform=` 给没给对，而不是反复试坐标值**。

> **⚠️ 陷阱**：`fig.text` / `fig.legend` / `fig.suptitle` 默认用 **figure** 坐标，`ax.text` 默认用 **data** 坐标——把 `ax.text(0.5, 0.9, ...)` 当"面板高度 90%"用，数据一变就出事。统一习惯：面板内相对定位**永远显式写 `transform=ax.transAxes`**。

> **延伸阅读**：transform 复合的数学与单位机器（日期轴为什么自动转 display），见配套文件 `ds-03b` 第 B2、B3 节。

**随堂自测 3.5**

1. `ax.transAxes.transform((1, 1))` 和 `fig.transFigure.transform((1, 1))` 各返回什么（试跑）？为什么不是 (1, 1)？
2. 想在"面板右上角内侧"放一行小字，给出两种写法并说明哪种能扛住 xlim 变化。
3. `ax.transData.inverted().transform(ax.transAxes.transform(p))` 这条复合在算什么？为什么要两步而不是直接 `ax.transAxes.transform(p)`？
4. `ax.axvline(x)` 的路径 xdata/ydata 各是什么？（用 3.5.4 的方法自证。）
5. 一个错误症状："annotations 在数据范围小时正常、放大后跑到图外"。归因到本节哪个概念。

**本节交付**：四套坐标系的选型表与"先查 transform 再试坐标"的排障次序，是 3.10 标注精修与 3.15 排查树的公共前提；混合变换解释了参考线/参考带的全部行为。

---

## 3.6 线型图与散点：Line2D 的语义与陷阱

架构层到此够用了。图型层从最常见的两类图开始——它们看似简单，却各藏着一个**静默错误**：类别轴的等距假设、散点颜色的双重语义。

### 3.6.1 简写格式与 Line2D 常用属性

```python
>>> fig, ax = plt.subplots()
>>> l, = ax.plot([1, 2, 3], [4, 5, 6], "r--o", lw=1.5, ms=4, label="run A")
>>> l.get_color(), l.get_linestyle(), l.get_marker()
('r', '--', 'o')
```

简写格式 `"r--o"` = 颜色 `r` + 线型 `--` + 标记 `o`，与 kwargs 等价但**不如 kwargs 可读**——工程代码建议全用 kwargs。高频属性速查：

| 属性 | kwarg | 语义要点 |
|------|-------|---------|
| 颜色 | `color` / `c` | 未指定时按 property cycle 取（3.3.4） |
| 线宽 | `lw` / `linewidth` | 期刊图常用 0.8–1.5 |
| 线型 | `ls` / `linestyle` | `-` `--` `:` `-.` |
| 标记 | `marker` + `ms` | 点少于 30 个再加，否则糊成一条 |
| 透明 | `alpha` | 叠线/密点必备，0.3–0.7 |
| 标签 | `label` | 只是**字符串存在 Line2D 上**，legend() 才消费（3.10.2） |
| 层级 | `zorder` | 见 3.6.4 |

### 3.6.2 类别轴陷阱：缺档被静默压缩

`plot` 对类别 x 做的事是"**按出现顺序编号**"，不是"按类别集合铺格"：

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot(["Q1", "Q2", "Q4"], [1, 2, 3])   # 注意：缺 Q3
>>> ax.get_xticks()                             # 刻度：0, 1, 2 —— 三个位置
[0, 1, 2]
>>> ax.lines[0].get_xdata()                     # 数据按顺序编号，占满 0,1,2
array(['Q1', 'Q2', 'Q4'], dtype='<U2')
```

**Q2 和 Q4 被画成相邻两点、中间一条直线连过去——Q3 的缺口在图上完全不可见**。这不是 bug：`plot` 把类别当"次序"处理，等距铺格是它的语义（`ds-00` 讲过的次序尺度）。但对"按季度对比"这类需求，它就是静默错图。正确姿势按需求二选一：

- **要显示"缺了一档"** → 用 `ax.bar`（条形图按类别集合铺格，缺失类别留空位），或先 `reindex` 补全类别；
- **确是时间序列** → x 传 datetime，交给日期轴（3.10.1 自动换疏密刻度）。

同样的等距假设还有第二张脸：**`plot` 适合等间隔采样**，不等间隔的时间数据画折线会出现"挤在左侧"——`scatter` 或日期轴才是对的工具。

### 3.6.3 散点：c 与 color 的双重语义

```python
>>> sc = ax.scatter([1, 2, 3], [1, 2, 3], c=[10, 20, 30], cmap="viridis")
>>> sc.get_clim()                               # clim 自动取数据范围
(10.0, 30.0)
>>> _ = ax.scatter([1], [2], c="red")            # c 也接受固定颜色（单值）
>>> ax.scatter([1], [2], c=[5], color="red")     # 两者同时给 → 直接报错
Traceback (most recent call last):
  ...
ValueError: Supply a 'c' argument or a 'color' kwarg but not both; they differ but their functionalities overlap.
```

语义分界线（背下来）：

| 写法 | 含义 | 走不走 colormap |
|------|------|----------------|
| `color="red"` | 所有点同一个颜色 | 否 |
| `c="red"` | 同上（允许，但别与 `color` 并用） | 否 |
| `c=[数值序列]` | **每个点一个数值 → 经 Normalize→cmap 上色** | 是（3.9） |

三个连带要点：**`s` 控制尺寸**（与 `c` 无关，别混）；`c` 走 colormap 时 **clim 自动取该次数据的 min/max**——同一份数据画两张子图、各自 autoscale 的 clim 会让**同色不同值**（3.9.3、3.15 清单）；密度大时用 `alpha=0.3` + `rasterized=True`（3.14）。

### 3.6.4 zorder：图层是排序值，不是绘制顺序

遮挡由 `zorder` 排序决定，与创建顺序无关。把一棵子树的 zorder 排出来：

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([1, 2], [1, 2], zorder=5)
>>> span = ax.axhspan(0, 10, zorder=0)
>>> sorted((a.get_zorder(), type(a).__name__) for a in ax.get_children()
...        if hasattr(a, "get_zorder"))
[(0, 'Rectangle'), (1, 'Rectangle'), (1.5, 'XAxis'), (1.5, 'YAxis'), (2.5, 'Spine'), (2.5, 'Spine'), (2.5, 'Spine'), (2.5, 'Spine'), (3, 'Text'), (3, 'Text'), (3, 'Text'), (5, 'Line2D')]
```

逐行对号入座：`(0, Rectangle)` 是我设了 `zorder=0` 的参考带、`(1, Rectangle)` 是 axes 背景 patch、`(1.5, XAxis/YAxis)` 是刻度系统、`(2.5, Spine)` 是四条边框、`(3, Text)` 是标题与轴标签、`(5, Line2D)` 是我画的线。默认档位很有规律：**背景 1 → 数据线/参考线 2 → 坐标轴 1.5 → 边框 2.5 → 文本 3**（注意默认档并非严格按创建层次排列，`axhspan` 默认 1、`Line2D` 默认 2，而 `XAxis` 是 1.5）——数据线在边框和文本之上，这是所有默认图都能读的原因。两个实用推论：

1. **参考带想垫在数据下面**：显式给 `axhspan(..., zorder=1.5)`（背景 patch=1 之上、数据线=2 之下）——默认 1 与背景同档，前后关系赌的是创建顺序，不可靠；
2. **覆盖型元素想压住一切**：给 10 以上即可，无需关心创建顺序。

> **⚠️ 陷阱**：`ax.plot` 在**同一 axes 连续调用**时，数据线默认 zorder 相同（2），遮挡靠"后画盖前画"——**这在调整了某条线的 zorder 之后就不成立了**。凡是"谁盖谁"有业务含义（如均线盖散点），显式写 zorder，别赌顺序。

> **延伸阅读**：类别轴的单位机器与 `Categorical` 定位器、zorder 的排序实现（`sorted` 在 draw 里的确切位置），见配套文件 `ds-03b` 第 B3 节。

**随堂自测 3.6**

1. `ax.plot(["a","b","c"], y)` 的 `get_xticks()` 返回什么？把数据改成 `["a","c"]` 后图上会发生什么（试跑并解释）？
2. "季度折线图缺一季却看不出"如何系统性避免？给出两条不同原理的防线。
3. `scatter(..., c="red")` 与 `scatter(..., color="red")` 有区别吗？`c=[1,2]` 呢？
4. 想让某条均线画在所有散点之上、参考带画在所有东西之下，zorder 怎么给？
5. 为什么"两张子图各用 `c=` 画同一量纲的数据"会产生误导？修复姿势是什么（预习 3.9）？

**本节交付**：类别轴等距陷阱与 `c/color` 语义表是静默错误清单（3.15）的头两条；zorder 档位表是精修节（3.10）与组合图的排层依据。

---

## 3.7 统计图族：分布、区间、比较

统计图不用背菜谱。3.4 已经给出统一框架——**每个方法 = 批量造 Artist + autoscale + 返回容器**——本节只做两件事：把"目的 → 方法 → 容器"的映射表填满，把每类图的静默陷阱标出来。容器类型为什么重要？因为它决定你**事后能不能改**（拿到 `BarContainer` 才能逐根改柱子）以及 3.15 **能不能断言**（按容器数验数据）。

### 3.7.1 容器总表：先认容器，再认图

| 目的 | 方法 | 返回容器 | 里面是哪些 Artist |
|------|------|---------|------------------|
| 单变量分布 | `ax.hist` | `(n, bins, BarContainer)` | Rectangle × 分箱数 |
| 比例化分布 | `ax.hist(..., density=True)` | 同上 | 同上（面积归一） |
| 经验分布 | `ax.ecdf` | `Line2D` | 一条阶梯线 |
| 五数概括 | `ax.boxplot` | `dict(boxes/caps/whiskers/medians/fliers/means)` | Rectangle + Line2D |
| 分布形状 | `ax.violinplot` | `dict(bodies/cbars/cmins/cmaxes)` | PolyCollection |
| 点估计 ± 区间 | `ax.errorbar` | `ErrorbarContainer` | Line2D + cap Lines |
| 区间填充 | `ax.fill_between` | `FillBetweenPolyCollection` | PolyCollection |
| 类别比较 | `ax.bar` / `ax.barh` | `BarContainer` | Rectangle × n |
| 堆叠比较 | `ax.stackplot` | `list[PolyCollection]` | 每层一个 |
| 两变量关系 | `ax.scatter` | `PathCollection` | 单个聚合 path |

实测三个代表（输出见下文各小节）：

```python
>>> fig, ax = plt.subplots()
>>> type(ax.errorbar([1, 2], [3, 4], yerr=[0.5, 0.5])).__name__
'ErrorbarContainer'
>>> sorted(ax.boxplot([[1, 2, 3, 4, 10], [2, 3, 4]]).keys())
['boxes', 'caps', 'fliers', 'means', 'medians', 'whiskers']
>>> sorted(ax.violinplot([[1, 2, 3]]).keys())
['bodies', 'cbars', 'cmaxes', 'cmins']
```

### 3.7.2 直方图：分箱是假设，density 是口径

```python
>>> fig, ax = plt.subplots()
>>> n, bins, patches = ax.hist([1, 2, 2, 3], bins=3, density=True)
>>> sum(n * (bins[1:] - bins[:-1]))       # 面积归一：直方图下面积 = 1
np.float64(1.0)
```

要点三条：

1. **`density=True` 是 matplotlib 的写法**（seaborn 的 `histplot` 才用 `stat="density"`——3.13 的参数差异表）；不开 density 时 y 轴是频数，两组样本量不同的数据不能叠画；
2. **分箱数/边界是统计假设不是样式**：默认 `bins="auto"`（fd/sqrt/Sturges 的择优），同一批数据换分箱能画出两种"形态"——发表图要在方法学里写明分箱策略，或改用 ECDF 绕开（3.7.5）；
3. **叠加 KDE 是组合图的常规操作**：hist（`alpha=0.5`，`ax.patches`）+ 密度曲线（`ax.plot`，`ax.lines`）同居一个 axes，分层靠 3.6.4 的 zorder；核密度估计的统计细节属于 `ds-04`。

### 3.7.3 箱线与小提琴：规则画出来的图

```python
>>> fig, ax = plt.subplots()
>>> parts = ax.boxplot([[1, 2, 3, 4, 10], [2, 3, 4]])
>>> sorted(parts.keys())
['boxes', 'caps', 'fliers', 'means', 'medians', 'whiskers']
```

箱线图的每个部件都是**规则的可视化**，不是装饰：盒子 = 四分位距（IQR），中线 = 中位数，**须延伸到 1.5×IQR 内的最远数据点，之外的点单独画成 `fliers`**（上例的 10 就是）——所以箱线图天然携带离群点信息，不需要再叠散点。小提琴图则是每组一个 KDE（`bodies` 是 PolyCollection，左右对称拼合），带宽 `bw_method` 影响胖瘦。

选型：**样本量小（n<30）→ 箱线 + 原始散点**（jitter）；**要比较分布形状/多峰 → 小提琴**；**要同时看两者的面板排版 → 并排箱线更省空间**。多组并排时共享同一 xlim/y 范围，否则视觉比较失效。

### 3.7.4 区间图：点估计的不确定性怎么落笔

`errorbar` 是"点估计 ± 误差"的正统写法，返回 `ErrorbarContainer`（线 + 上下 cap + 误差棒三件套）：

```python
>>> fig, ax = plt.subplots()
>>> eb = ax.errorbar([1, 2, 3], [2.0, 2.5, 2.2], yerr=[0.3, 0.2, 0.4])
>>> type(eb).__name__, type(eb[0]).__name__
('ErrorbarContainer', 'Line2D')
```

`fill_between` 画连续带（时序置信带的标准件），返回 `FillBetweenPolyCollection`（`PolyCollection` 子类）：

```python
>>> f = ax.fill_between([1, 2, 3], [1.5, 2.0, 1.7], [2.5, 3.0, 2.7], alpha=0.3)
>>> type(f).__name__
'FillBetweenPolyCollection'
```

语义纪律（回链 `ds-00` 的标准误与置信区间）：**误差棒的"误差"必须在图例/轴标签里写清是 SD、SE 还是 95% CI**——三者数值不同、结论可能相反；`yerr` 只接受对称值，非对称区间（分位数区间）用 `fill_between` 或 `errorbar` 的 `[lower, upper]` 二元组形式。时序滚动带的构造（rolling ± k·SE）在 3.16 综合实战里落地。

### 3.7.5 条形图：类别比较与它的起点陷阱

`ax.bar` 返回 `BarContainer`（3.4.2 已实测），三个高频决策：

| 决策 | 选项 | 判断依据 |
|------|------|---------|
| 横竖 | `bar` vs `barh` | 类别名长 → 横向（标签不挤） |
| 分组 vs 堆叠 | `pivot(...).plot(kind="bar", stacked=...)` | 分组看单项对比、堆叠看总量构成 |
| 宽度 | `width=`（竖）/ `height=`（横） | 分组柱总宽 1.0，按组数均分 |

**起点陷阱**：`bar` 的柱从 0 起——这是它的语义完整性（柱长=值），也是它和折线的根本区别；**若 y 轴被手动截断（`set_ylim(50, 100)`），"长度"与"值"脱钩，柱状对比立刻失真**。条形图的截断比折线截断误导性强得多，是 3.15 清单的常驻条目。分组柱的断言数很好写：`len(ax.patches) == 组数 × 系列数`（3.16 用 12×3=36 实测过）。

### 3.7.6 ECDF：不设分箱的诚实图

```python
>>> fig, ax = plt.subplots()
>>> type(ax.ecdf([1, 2, 2, 3])).__name__
'Line2D'
```

ECDF（经验累积分布函数）只有一条阶梯线（一个 `Line2D`），**没有任何分箱假设**：每个数据点都在图上有位置、所有分位数都能直接读出、小样本也不失真。代价是不如直方图直观地展示"形态"。经验法则：**探索阶段看 ECDF（诚实），汇报形态看直方图（直观）**，n 很小时箱线图的五数概括最省墨。`ds-04` 的分布拟合检验会回到这张图上。

### 3.7.7 组合图与选型收口

组合图的原理 3.4.2 已给：往同一个 axes 反复加对象（`ax.patches` 从 3 涨到 13 就是 hist 叠 bar 的实测）。一张"直方图 + 均值线 + ±1.96σ 参考带"的标配分层：

```python
ax.hist(x, bins=30, density=True, alpha=0.6, zorder=1)   # 底层分布
ax.axvline(x.mean(), color="k", lw=1.5, zorder=3)         # 中心
ax.axvspan(lo, hi, color="tab:red", alpha=0.15, zorder=1.5)  # 区间（3.6.4 的档位）
```

**选型收口表**：

| 目的 | 首选 | 备选 | 头号坑 |
|------|------|------|--------|
| 单组分布形态 | `hist` (+KDE) | `ecdf`（n 小/要分位数） | 分箱假设（3.7.2） |
| 多组分布对比 | 并排 `boxplot` | `violinplot` / 分组 `hist` | 各组轴范围不一致 |
| 点估计 ± 不确定性 | `errorbar` | 时序用 `fill_between` 带 | 误差类型未标注 |
| 类别比较 | `bar`/`barh` | 堆叠看构成 | y 轴截断（长度失真） |
| 两变量关系 | `scatter` | 密度高时 hexbin/2d hist | `c/color` 双语义（3.6.3） |
| 时间趋势 | `plot` + 日期轴 | 面积图 `fill_between` | 类别式等距假设（3.6.2） |

> **⚠️ 陷阱**：`ax.boxplot` **默认每次调用都新建全部部件**，在同一 axes 上循环调用会叠出多组箱子而不报错——多组数据要一次传入 `ax.boxplot([g1, g2, g3])`，让方法自己分组。同理 `ax.bar` 循环叠加前先算好 `x` 位置，否则柱会互相压住（这是"容器不查重"的代价：**matplotlib 不会替你发现画重了**）。

> **延伸阅读**：`hist`/`boxplot` 内部对 Artist 的批量构造、`FillBetweenPolyCollection` 的路径拼装，见配套文件 `ds-03b` 第 B1 节。

**随堂自测 3.7**

1. 默写"分布/区间/比较"三类需求各自的方法与返回容器（不许翻表）。
2. `ax.hist(x, density=True)` 下 `sum(n * np.diff(bins))` 为什么是 1？换成 `density=False` 它是什么？
3. 箱线图上怎么一眼找到 1.5×IQR 的界？`fliers` 里画的是什么点？
4. 非对称置信区间（25%/75% 分位）该用 `errorbar` 还是 `fill_between`？为什么 `yerr=标量` 不够？
5. "柱状图截断 y 轴"比"折线图截断 y 轴"危险在哪？
6. 想断言"这张分组柱图恰好画了 4 组 × 3 系列"，写一行断言。

**本节交付**：容器总表 + 选型收口表是全书统计作图的统一入口（`ds-04` 的分布图、卷 3 的评估图全部按此选型）；分箱/截断/误差口径三条坑进 3.15 静默错误清单。

---

## 3.8 多面板与画布尺寸：figsize、dpi、布局三件套

### 3.8.1 三个尺度别混：英寸、dpi、像素

一张图有三个可调量，换算关系只有一条：**像素 = 英寸 × dpi**，字号是**点（pt）**、与 dpi 无关（1 pt = 1/72 英寸）：

```python
>>> fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
>>> fig.get_size_inches(), fig.dpi
(array([6., 4.]), 100)
>>> fig.canvas.get_width_height()          # 内存画布像素
(600, 400)
>>> fig.set_dpi(200); fig.canvas.get_width_height()   # 改 dpi：像素翻倍，英寸不变
(1200, 800)
>>> fig.savefig("t.png", dpi=150); fig.savefig("t2.png")   # t2 不传 dpi → 默认 'figure'
>>> from PIL import Image
>>> Image.open("t.png").size, Image.open("t2.png").size
((900, 600), (600, 400))
```

三个不直觉但重要的结论：

1. **字号的物理尺寸由 pt 锁定，不随 dpi 变**——同一份代码在 100 dpi 和 300 dpi 导出下，字与图的比例一致（这正是"论文图字号可复现"的原理）；但**像素数变了**：`px = pt × dpi / 72`，10 pt 字在 300 dpi 下是 42 px；
2. **`figsize` 决定构图比例，`savefig(dpi=)` 决定输出清晰度**——期刊要求 600 dpi 时只改 `savefig(dpi=600)`，不要去动 `figsize`（动了版式全变）；
3. **`fig.dpi`（画布）与 `savefig(dpi)`（导出）是两个旋钮**，而默认导出 dpi 是个陷阱：`savefig` 的 `dpi="figure"` 解析的是**创建 figure 时**的 `_original_dpi`，不是 `set_dpi()` 之后的当前值——上例画布已改到 200 dpi，`t2.png` 仍然是 (600,400)。**要改导出清晰度，永远显式传 `savefig(dpi=...)`**；`fig.set_dpi()` 只影响屏幕交互。

尺寸经验值（单栏/双栏/幻灯）：论文单栏 3.5 in、双栏 7 in、16:9 幻灯 `(13.33, 7.5)`；**先定 figsize 再定字号**，反过来永远在补丁上打补丁。

### 3.8.2 三种建布局：规则、自由、精确

```python
>>> fig, axes = plt.subplots(2, 2, figsize=(8, 6))        # ① 规则网格：一行代码
>>> gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1])    # ② 自由网格：列宽不等
>>> axA = fig.add_subplot(gs[:, 0])                       #    左列跨两行
>>> axB = fig.add_subplot(gs[0, 1])                       #    右列上下分
>>> axC = fig.add_axes([0.7, 0.1, 0.25, 0.8])             # ③ 精确矩形 [l, b, w, h]
```

选型规则：**等分网格用 `subplots`（90% 场景）；某面板要跨行/跨列或宽度不等用 `GridSpec`（3.16 的报告图就是 2×2 左列跨行）；要绝对像素级定位（inset 放大镜）才用 `add_axes`**。`GridSpec` 的分数坐标与 `add_axes` 的 `[l,b,w,h]` 同属一套（figure 分数），贴面板内部的定位则属于 axes 分数（3.5 的 `transAxes`）——三种"分数"分属两套坐标系，别串。

### 3.8.3 布局三件套：tight、constrained、bbox 裁剪

标题、轴标签、出轴图例经常被裁——三种修法**作用时机完全不同**：

| 方案 | 作用时机 | 作用对象 | 适用 |
|------|---------|---------|------|
| `layout="constrained"`（`subplots(...)`/`figure(...)`） | 每次 draw **前**重新排版 | figure 内全部子图 | **默认推荐**；带 colorbar/出轴图例最稳 |
| `fig.tight_layout()` | draw 前近似排版 | 子图的 tightbbox | 简单场景，出轴元素容易翻车 |
| `fig.savefig(..., bbox_inches="tight")` | **导出时**裁剪画布 | 只影响导出文件 | 补救；**不改变内存布局** |

实测 bbox 裁剪的代价（同图、同 dpi=150 导出）：

```python
>>> fig, ax = plt.subplots(); _ = ax.plot([1, 2, 3], [1, 2, 3])
>>> ax.set_title("hello world")
Text(0.5, 1.0, 'hello world')
>>> fig.savefig("plain.png", dpi=150); fig.savefig("tight.png", dpi=150, bbox_inches="tight")
>>> Image.open("plain.png").size, Image.open("tight.png").size
((960, 720), (834, 651))
```

**输出尺寸从 960×720 变成 834×651**——补救了裁切，但破坏了"图占固定版面"的要求：期刊模板要固定宽度时，`bbox_inches="tight"` 会让排版尺寸不可控。**纪律：排版问题在布局层解决（constrained），`bbox_inches` 只当最后一道保险，且不要与 constrained 混用**（两者叠加后连"最终多大"都算不出来）。

> **版本注意**：`layout=` 关键字是 3.6 起的正写法（`plt.subplots(layout="constrained")`），旧教程的 `constrained_layout=True` 仍可用但属旧写法；`plt.tight_layout()` 保留，但与 colorbar/`fig.legend` 配合常出"越修越歪"，遇复杂布局直接换 constrained。

### 3.8.4 共享轴：sharex 联动什么、不联动什么

```python
>>> fig, (a1, a2) = plt.subplots(2, 1, sharex=True)
>>> _ = a1.plot([0, 50], [0, 1]); _ = a2.plot([0, 50], [1, 0])
>>> a1.get_xlim()
(np.float64(-2.5), np.float64(52.5))
>>> a1.get_xlim() == a2.get_xlim()              # 两个面板同一套范围
True
>>> a1.set_xlim(0, 100)                          # 设一个，两个都动（set_xlim 返回新 limits）
(0.0, 100.0)
>>> a2.get_xlim()
(np.float64(0.0), np.float64(100.0))
>>> fig.canvas.draw(); a1.xaxis.get_tick_params()['labelbottom']   # 上面板标签自动隐藏
False
```

`sharex=True` 做了两件事：**limits 进同一个 Grouper（改一处、处处变）+ 下面板之外的刻度标签自动关闭**（`labelbottom=False`）。它和 `twinx`（3.4.3）是两个正交工具，别混：

| | `sharex=True` | `twinx()` |
|---|---|---|
| 面板数 | 各占一块矩形（上下排） | 同一矩形叠两层 |
| 坐标系 | **同一套** x 数据范围 | **两套** y 量纲 |
| 典型用途 | 多指标共享时间轴 | 双量纲（温度 vs 湿度） |
| 关系 | 通过 Grouper 联动 limits | 通过 Grouper 联动 x |

多面板对齐的完整账（面板间距、共享边框 `sharey`、GridSpec 的 `wspace/hspace`）与布局排版的内部计算，见配套文件 `ds-03b` B2。

> **⚠️ 陷阱**：`sharex` 下手动 `set_xlim` 会**关闭共享组的 autoscale**（同 3.10.4 的机制）——共享面板再收到新数据也不会扩轴，跑批前记得 `ax.autoscale()` 复位。另一个高频坑：**`sharey=True` 时各组数据量级差异巨大，小量级组被压成直线**——只有"确实同量级"才共享 y。

> **延伸阅读**：`Grouper` 的共享实现、`layout="constrained"` 的求解过程、GridSpec 的 `wspace/hspace` 计算，见配套文件 `ds-03b` 第 B2 节。

**随堂自测 3.8**

1. 期刊要求"宽 180 mm、600 dpi、正文 9 pt"——`figsize` 和 `savefig` 参数各给多少（mm→inch 换算：180 mm ≈ 7.09 in）？
2. `fig.dpi=200` 之后 `savefig("a.png")` 和 `savefig("b.png", dpi=150)` 的像素各是多少？为什么？
3. `plt.subplots(1, 2)` 与 `add_gridspec(1, 2)` 再 `add_subplot` 的区别是什么？什么时候必须用后者？
4. 三件套里哪个只影响导出文件、不动内存布局？哪个会改变最终输出尺寸？
5. `sharex` 和 `twinx` 各自联动了什么、没联动什么？各举一个误用症状。
6. 共享面板"新数据进来了轴不扩"，根因是什么、怎么复位？

**本节交付**：英寸/dpi/pt 换算是全书出图参数的公共公式（`ds-04`、卷 3 报告图直接引用）；布局三件套选型表与共享轴账目归入 3.15 排查树的"位置/尺寸"类问题。

---

## 3.9 色彩系统：colormap、Normalize 与 colorbar

颜色在 matplotlib 里不是样式而是**一条数据管线**：`数据值 → Normalize → [0,1] → Colormap 查表 → RGBA`。理解这条管线，"两张子图颜色不可比""colorbar 数值对不上"这类问题就都成了断言可查的显式错误。

### 3.9.1 三种色源与归一化实测

颜色只有三个来源：**具体色**（名字/hex/rgba，一个值管全部）、**属性循环**（未指定时逐条取色，3.3.4/3.11）、**按值映射**（cmap 管线，本节主角）。实测管线两步：

```python
>>> fig, ax = plt.subplots()
>>> sc = ax.scatter([1, 2, 3], [1, 2, 3], c=[10, 20, 30], cmap="viridis")
>>> sc.get_clim()                        # 归一化窗口：自动取数据 min/max
(10.0, 30.0)
>>> type(sc.norm).__name__               # 数值 → [0,1] 的归一化器
'Normalize'
>>> sc.cmap(sc.norm(10))                 # 归一后查表 → RGBA
(np.float64(0.267004), np.float64(0.004874), np.float64(0.329415), np.float64(1.0))
>>> sc.set_clim(0, 100)                  # 只动窗口，数据没动
>>> sc.cmap(sc.norm(10))                 # 同一个值，颜色变了
(np.float64(0.282623), np.float64(0.140926), np.float64(0.457517), np.float64(1.0))
```

两个必须内化的结论：

1. **颜色是"值 + clim"的函数，不是值的函数**。同一个 10，clim=(10,30) 时是深蓝、clim=(0,100) 时偏亮——**两张子图各自 autoscale 的 clim 会让同色不同值**（3.15 静默错误清单第 7 条），批量出图必须显式统一 `vmin/vmax`（即 `set_clim`，或 `scatter(..., vmin=, vmax=)`）；
2. **clim 与数据是两个自由度**：调"视觉对比度"动 clim、调数据本身动数据，别用改数据的方式调颜色。

### 3.9.2 colormap 三类与选型

| 类型 | 适用 | 代表 | 特征 |
|------|------|------|------|
| 顺序（sequential） | 单调数值（大=深） | `viridis`（默认）、`magma`、`Blues` | 感知均匀，灰度打印仍可读 |
| 发散（diverging） | 有业务中点（正/负、高于/低于均值） | `RdBu`、`coolwarm`、`PiYG` | 两侧反向、中间中性色 |
| 分类（categorical） | 无序类别 | `tab10`、`Set2` | 离散槽位，不表达大小 |

选型口诀：**数值有方向 → 顺序；围绕零/均值摆动 → 发散；类别无序 → 分类**。避开彩虹色（`jet`/`hsv`）：感知不均匀，会在数据里制造假边界。注册表与旧写法（3.0 版本注意第②条）：

```python
>>> matplotlib.cm.get_cmap("viridis")          # 旧教程的写法，3.9 起已移除
Traceback (most recent call last):
  ...
AttributeError: module 'matplotlib.cm' has no attribute 'get_cmap'
>>> type(matplotlib.colormaps["viridis"]).__name__   # 现在的正路：注册表
'ListedColormap'
```

### 3.9.3 colorbar：一根挂在旁边的 Axes

```python
>>> cb = fig.colorbar(sc)
>>> isinstance(cb.ax, plt.Axes)                # colorbar 自己就是一根 Axes
True
>>> cb.ax in fig.axes                          # 所以它占一个面板名额（3.4.3 预言过）
True
```

三条使用纪律：

- **colorbar 与 mappable 绑定**：它显示的是 `sc` 当前的 `norm+cmap+clim`——之后 `sc.set_clim(...)`，colorbar 跟着变（同一个对象，不是快照）；
- **它是 Axes 意味着占布局**：多面板 GridSpec 里 colorbar 会挤占空间，用 `fig.colorbar(sc, ax=[ax1, ax2])` 或 `constrained_layout`（3.8.3）消化；
- **`extend=` 标出超界区**（clamp 掉的值），数据有越界时图上要能看出来，否则又是静默错误。

> **⚠️ 陷阱**：`scatter` 的 `c=` 与 colorbar 一起用时，**`c` 的数值数组与 `x/y` 等长**是硬约束，错位会直接报错；但 `c` 传类别字符串（如 `c=df["grp"]`）会静默走字典映射，颜色含义要靠 `colorbar` 的刻度标签自证。对数量级的值用 `Norm`（`LogNorm`）而不是改数据取对数——管线里换归一化器才是正路，内部实现见 `ds-03b` B5。

> **延伸阅读**：Normalize 家族（`LogNorm`/`PowerNorm`/`BoundaryNorm`）与 colormap 的离散化、RGBA 查表的字节级过程，见配套文件 `ds-03b` 第 B5 节。

**随堂自测 3.9**

1. 默写色彩管线的四个环节；`set_clim(0, 100)` 改的是哪一环？
2. 两个子图各画一组 `c=[10,20,30]` 和 `c=[5,6,7]`，为什么会出现"同色不同值"？给出修复的两种写法。
3. "温度距平图（±5℃，0 为正常）"该选哪类 cmap？为什么不能用 viridis？
4. colorbar 是什么类型对象？这带来哪两个布局上的推论？
5. `matplotlib.cm.get_cmap` 报错说明什么？注册表的新写法是什么？

**本节交付**：归一化管线与"clim 是第二自由度"是全书所有带色图的正确性前提（`ds-04` 的相关热力图、卷 3 的混淆矩阵同此）；"统一 clim"进 3.15 静默错误清单。

---

## 3.10 标注与精修：刻度、图例、annotate

出版级和"能看"的差距，八成在这三件事上。全部建立在 3.5 的坐标系与 3.3 的 Artist 模型之上：**刻度是 Locator+Formatter 两个对象、图例是消费 label 的独立 Artist、标注是选对 transform 的 Text**。

### 3.10.1 刻度系统：Locator 管"放哪"，Formatter 管"写啥"

每个轴都挂着一对对象，换它们就换了刻度行为：

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([0, 10], [0, 1])
>>> type(ax.xaxis.get_major_locator()).__name__       # 默认：自动挑整数间距
'AutoLocator'
>>> type(ax.xaxis.get_major_formatter()).__name__     # 默认：标量格式
'ScalarFormatter'
>>> ax.xaxis.set_major_locator(plt.MultipleLocator(2))
>>> from matplotlib.ticker import FuncFormatter
>>> ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.0f} ms"))
>>> type(ax.xaxis.get_major_locator()).__name__, type(ax.xaxis.get_major_formatter()).__name__
('MultipleLocator', 'FuncFormatter')
```

日期轴"自动认识"datetime 的原理就是换了这对对象——3.5.3 说过坐标要先转换单位，日期轴的单位机器注册后由定位器自动选日期粒度：

```python
>>> from datetime import datetime, timedelta
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([datetime(2024, 1, 1) + timedelta(days=i) for i in range(5)], [1, 2, 3, 4, 5])
>>> type(ax.xaxis.get_major_locator()).__name__
'AutoDateLocator'
```

高频三招：`MultipleLocator(n)` 固定间隔；`FuncFormatter` 自定义文本（单位、千分位、百分号）；日期轴用 `ConciseDateLocator` 压缩标签。**自定义标签后记得检查与数据单位一致**（"ms"标在秒数据上是静默错误）。

### 3.10.2 图例：label 是声明，legend 是消费

```python
>>> fig, ax = plt.subplots()
>>> l1, = ax.plot([1, 2], [1, 2], label="a")
>>> l2, = ax.plot([1, 2], [2, 1], label="b")
>>> leg = ax.legend()
>>> [type(h).__name__ for h in leg.legend_handles]     # 自动收集带 label 的 artist
['Line2D', 'Line2D']
>>> h3 = ax.axhline(0, color="k", ls="--")             # 没有 label 的对象
>>> leg2 = ax.legend(handles=[h3], labels=["zero"], loc="upper left", bbox_to_anchor=(1.01, 1))
>>> type(leg2).__name__, len(leg2.legend_handles)      # 手动指定 + 锚到轴外右上
('Legend', 1)
```

要点：`label` 只是**挂在对象上的字符串**（3.3.1），`legend()` 调用那一刻才收集——所以**先画完再调 legend**；`bbox_to_anchor=(1.01, 1)` + `loc="upper left"` 是"贴在 axes 右缘外侧"的惯用组合，坐标属于 **axes 分数系**（3.5，可越出 0–1）；不想进图例的 artist 给 `label="_nolegend_"`（pandas.plot 生成的图例常需手动 `ax.legend(handles, labels)` 重排）。

### 3.10.3 annotate：锚点与文字可以分属两套坐标系

`annotate(文字, xy=锚点, xytext=文字位置, textcoords=..., arrowprops=...)` 是 3.5.3 实测过的组合：**锚点走 data（跟数据跑），文字走 offset 像素（保持相对距离）**。决策表：

| 需求 | 写法 |
|------|------|
| 指向数据点、文字在旁侧固定像素处 | `xy=`data、`xytext=(dx,dy)` + `textcoords="offset points"`（默认） |
| 文字固定在面板角落、指数据 | `xytext=(0.02,0.95)` + `textcoords="axes fraction"` |
| 箭头样式 | `arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.2")` |

标注密度的经验值：**一张图 3–5 个为宜**；要标 20 个点，说明该换标注策略（直标 vs 图例），不是该写 20 个 annotate。

### 3.10.4 autoscale 与 margin：手动设限的隐性代价

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([10, 20], [5, 5])
>>> ax.get_xlim()                          # 数据 [10,20]，两侧各留 5% 边距
(np.float64(9.5), np.float64(20.5))
>>> ax.margins()                           # 默认边距
(0.05, 0.05)
>>> ax.margins(x=0.2); fig.canvas.draw()   # 改边距要重画才落账
>>> ax.get_xlim()
(np.float64(8.0), np.float64(22.0))
>>> ax.set_xlim(10, 20)                    # 手动设限——顺手关掉了 x 轴 autoscale
(10.0, 20.0)
>>> ax.get_xlim()                          # 之后进新数据也不会自动扩轴
(np.float64(10.0), np.float64(20.0))
```

**`set_xlim` 返回新 limits、同时把该轴的 autoscale 关掉**——这是 3.15 排查树"轴不更新"的头号根因，也是 3.8.4 共享轴"新数据不扩轴"的同一机制。复位用 `ax.autoscale(enable=True)` 或 `ax.autoscale_view()`；跑批函数里**不要写死 xlim**，把范围作为参数传入。

### 3.10.5 出版级精修检查清单

| 检查项 | 做法 |
|--------|------|
| 字号 | 正文 9–10 pt、轴标签 10 pt、标题 11 pt（pt 锁物理尺寸，3.8.1） |
| 线宽/标记 | 线 ≥0.8，缩图后仍可辨；标记在点少时才开 |
| 单位 | 轴标签带单位：`revenue (k USD)`；刻度格式与数据单位一致 |
| 边框 | 学术风常去上/右 spine（`ax.spines["top"].set_visible(False)`） |
| 网格 | 只留主方向、低透明度；栅格在数据之下（zorder < 数据，3.6.4） |
| 图例 | 不遮数据；出轴用 `bbox_to_anchor`；类别多时改直标 |
| 重叠 | 旋转 x 标签（`rot=45`）或改横向；刻度过密换 Locator |
| 可灰度打印 | 分类色配合 `hatch`；避免纯靠红绿区分 |
| 输出 | 矢量 + `bbox_inches` 复核（3.8.3）、最终以目标 dpi 复验像素 |
| 一致性 | 同报告内字号/配色走同一份 rc（3.11） |

**随堂自测 3.10**

1. 想让 x 轴每 250 mL 显示一个刻度、标签带 "mL"，Locator 和 Formatter 分别给什么？
2. `label=` 和 `legend()` 的分工是什么？为什么"先 legend 后 plot"会得到空图例？
3. 标注文字要钉在面板左上角、箭头指向某个数据点——`xytext` 的坐标系选什么？
4. `set_xlim` 除了改范围还顺手做了什么？这会导致什么下游症状、怎么复位？
5. 用 3.10.4 的方法断言"手动设限后的图，后续进的新数据没被纳入 xlim"。

**本节交付**：刻度/图例/标注三个对象模型与精修检查清单是"出版级"的执行标准；autoscale 的隐性关闭进 3.15 排查树。

---

## 3.11 样式与配置：rcParams 与可复现绘图

matplotlib 的全部默认样式集中在一个字典 `rcParams` 里（约 300 个键）。本节只解决两件事：**改哪里（作用域）** 和 **怎么改得可复现（团队模板）**。

### 3.11.1 作用域：全局、局部、上下文三层

```python
>>> matplotlib.rcParams["figure.figsize"]          # 内置默认
[6.4, 4.8]
>>> with matplotlib.rc_context({"figure.figsize": (2, 1)}):   # 局部生效，退出自动还原
...     print(matplotlib.rcParams["figure.figsize"])
[2.0, 1.0]
>>> matplotlib.rcParams["figure.figsize"]          # 果然还原了
[6.4, 4.8]
>>> matplotlib.rcParams["figure.figsize"] = (9, 9) # 改全局：影响之后创建的所有 figure
>>> fig, _ = plt.subplots(); fig.get_size_inches()
array([9., 9.])
>>> matplotlib.rcParams["figure.figsize"] = [6.4, 4.8]   # 改完立即还原（脚本纪律）
```

| 层 | 写法 | 生命周期 |
|----|------|---------|
| 全局 | `matplotlib.rcParams[...] = ...` / `plt.rc(...)` | 进程内之后的所有对象 |
| 上下文 | `with matplotlib.rc_context({...}):` | 块内，退出自动还原 |
| 对象级 | `fig, ax = plt.subplots(...)` 各种 kwargs / `ax.set_*` | 只作用于该对象，**永远优先** |

**优先级链（高→低）：对象属性 > `rc_context` > `plt.style.use` 全局切换 > 用户 `matplotlibrc` 文件 > 内置默认**。设计含义：**能传参就传参，rc 管"一批图的默认"，样式表管"一份报告的风格"。**

### 3.11.2 样式表：一次切换一整组 rc

```python
>>> matplotlib.rcParams["axes.facecolor"]          # 内置默认
'white'
>>> plt.style.use("ggplot")
>>> matplotlib.rcParams["axes.facecolor"]          # 风格表本质上是一组 rc 赋值
'#E5E5E5'
>>> len(plt.style.available)                       # 内置风格数量
28
>>> plt.style.use("default"); matplotlib.rcParams["axes.facecolor"]   # 一键回默认
'white'
```

`plt.style.use` 是**全局且持久**的（不像 `rc_context` 自动还原）——在库代码里切换样式属于 3.2 同款"全局状态污染"，只允许出现在脚本入口；给函数加临时样式用 `with plt.style.context("ggplot"):`。

### 3.11.3 团队模板：一份 .mplstyle 文件

样式表就是**纯 `键: 值` 文本**，进版本库、所有图共享。骨架（`paper.mplstyle`）：

```text
# ---- 尺寸与输出 ----
figure.figsize: 7.0, 4.2          # 单栏宽度 7 in（3.8.1）
figure.dpi: 100                   # 屏幕交互
savefig.dpi: 600                  # 导出（永远显式，3.8.1 的 _original_dpi 教训）
# ---- 字体 ----
font.size: 10
axes.titlesize: 11
axes.labelsize: 10
xtick.labelsize: 9
ytick.labelsize: 9
legend.fontsize: 9
# ---- 线与网格 ----
lines.linewidth: 1.2
lines.markersize: 4
axes.grid: true
grid.alpha: 0.3
grid.linewidth: 0.6
# ---- 边框与图例 ----
axes.spines.top: false
axes.spines.right: false
legend.frameon: false
# ---- 属性循环（tab10 前六色）----
axes.prop_cycle: cycler('color', ['1f77b4', 'ff7f0e', '2ca02c', 'd62728', '9467bd', '8c564b'])
```

用法（把上面的骨架存为项目根目录的 `paper.mplstyle` 后）：

```python
plt.style.use("paper.mplstyle")          # 入口处：套用项目样式

with plt.style.context("paper.mplstyle"):   # 或临时套用、退出自动还原
    fig, ax = plt.subplots()
    ...
```

中文报告在模板里追加两行（3.11.4 的三坑一次解决）：

```text
font.sans-serif: Noto Sans CJK SC, Microsoft YaHei, SimHei, DejaVu Sans
axes.unicode_minus: False
```

### 3.11.4 中文环境三坑

1. **豆腐块**：默认字体 `DejaVu Sans` 不含 CJK 字形，中文全部显示为 □——必须在模板里把中文字体排到 `font.sans-serif` **首位**（顺序即回退顺序，排在 DejaVu 后面会被先匹配）；
2. **负号乱码**：`axes.unicode_minus` 默认 `True`（用 Unicode 减号 `−`），中文字体里常常没有这个字形，坐标轴负数显示异常——中文模板置 `False`（回退成 ASCII `-`）：

```python
>>> matplotlib.rcParams["axes.unicode_minus"]
True
```

3. **字体是环境依赖**：模板里写的字体名必须在**运行机器**上真实存在，否则静默回退到 DejaVu——开发机上画中文正常、CI 里变豆腐块，是典型的"环境差异静默错"。CI 出图前用 `matplotlib.font_manager` 断言字体存在（3.15 的断言思路），或把字体文件随仓库分发。

> **⚠️ 陷阱**：`plt.rcParamsDefault` 是只读的全量默认表，**别整体赋值回 `rcParams`**（会丢掉运行期的合法修改）；单键还原写 `matplotlib.rcParams[key] = matplotlib.rcParamsDefault[key]`。`rcParams` 的键名拼错会 `KeyError` 而非静默忽略——这是好事，别用 try 吞掉。

> **延伸阅读**：`rcParams` 的校验器体系（每个键都有 validate 函数）、样式表的加载与合并顺序，见配套文件 `ds-03b` 第 B1 节。

**随堂自测 3.11**

1. 优先级链"对象属性 > rc_context > style.use > matplotlibrc > 默认"，各举一个使用场景。
2. 在被别人 import 的模块里 `plt.style.use(...)` 有什么问题？替代方案是什么？
3. 模板里 `savefig.dpi: 600` 与 3.8.1 的 `_original_dpi` 陷阱是什么关系？
4. 为什么中文字体必须排在 `font.sans-serif` 的第一位？
5. 写一个 `rc_context` 快照：临时改三个 rc 值，退出后断言全部还原。

**本节交付**：作用域三层与优先级链是"配置不打架"的判断依据；`paper.mplstyle` 骨架直接用于全书各卷的统一出图与 3.16 综合实战。

---

## 3.12 输出与后端：savefig、无头渲染、内联

后端（backend）是"渲染器 + 事件循环"的组合，决定了图**画到哪去**：弹窗、内存画布、还是文件。90% 的工程问题（CI 不出图、Notebook 弹窗、导出模糊）都是选错了这一层。

### 3.12.1 后端的两类与注册表

```python
>>> matplotlib.get_backend()               # 3.2.1 设过 matplotlib.use("Agg")
'Agg'
>>> from matplotlib.backends.registry import BackendRegistry, BackendFilter
>>> r = BackendRegistry()
>>> r.list_builtin(BackendFilter.INTERACTIVE)[:4]     # 交互类：要窗口/事件循环
['gtk3agg', 'gtk3cairo', 'gtk4agg', 'gtk4cairo']
>>> r.list_builtin(BackendFilter.NON_INTERACTIVE)     # 无头类：只产文件/像素
['agg', 'cairo', 'pdf', 'pgf', 'ps', 'svg', 'template']
```

规则就三条：

1. **`matplotlib.use("Agg")` 必须在 `import matplotlib.pyplot` 之前**（3.2.1 的坑位）；更稳的是进程级环境变量 `MPLBACKEND=Agg`（在 `pyplot` 被任何库提前 import 的场景下依然生效，实测子进程 `get_backend()` 返回 `'Agg'`）；
2. **服务器/CI 一律无头后端**——交互后端在无显示环境会 `ImportError`/挂起，且这是**启动期错误**，报错信息常指向你没写的代码；
3. 后端名的小写形式（`agg`）是 rc 风格名、`use("Agg")` 后 `get_backend()` 返回 `'Agg'`——两者指同一个后端，别当成两个东西。

> **版本注意**：`list_builtin` 的参数是 `BackendFilter` **枚举**而不是字符串——传 `'interactive'` 这样的字符串不报错、但两个分支都不匹配，**静默返回全部后端**（实测两类列表完全相同）。这是 3.15 "静默错误"的又一标本：API 给了你一个看起来合理的错误用法。

### 3.12.2 矢量 vs 位图：SVG 的文字是个坑

```python
>>> fig, ax = plt.subplots(); _ = ax.plot([1, 2, 3], [1, 2, 3]); ax.set_title("hello world")
Text(0.5, 1.0, 'hello world')
>>> fig.savefig("sv.pdf"); fig.savefig("sv.svg"); fig.savefig("sv.png", dpi=300)
>>> Image.open("sv.png").size                        # PNG 走 dpi（3.8.1）
(1920, 1440)
>>> len(open("sv.pdf", "rb").read()), len(open("sv.svg", "rb").read())   # 矢量极小
(7576, 19515)
>>> sv = open("sv.svg").read()
>>> sv.count("<text"), sv.count("<use")              # 文字去哪了？
(0, 101)
>>> "hello world" in sv                              # 只剩 XML 注释里的原字符串
True
```

**PNG 是像素（dpi 定大小），PDF/SVG 是指令（矢量，几 KB 起步）**。但 SVG 那两行要警觉：默认 `svg.fonttype: 'path'` 把**每个字形转成 path/`<use>` 引用**——文字不可选、不可搜、改字号要重画。要在 Illustrator/浏览器里编辑文字，导出时开 `none`：

```python
>>> with matplotlib.rc_context({"svg.fonttype": "none"}):
...     fig.savefig("sv_none.svg")
>>> open("sv_none.svg").read().count("<text")         # 文字保留为可编辑 <text> 元素
19
```

选型口诀：**论文/出版 → PDF（LaTeX 直接吃）、要改字 → SVG(`fonttype:none`)、PPT/Web/位图 → PNG(dpi≥200)**；同一批点既要矢量又要小文件，用 `rasterized=True` 混合输出（3.14.3 实测 11 倍体积差）。

### 3.12.3 savefig 参数账

`fig.savefig` = `canvas.print_figure`，参数三类（换算细节见 3.8.1/3.8.3）：

| 参数 | 作用 | 备注 |
|------|------|------|
| `dpi=` | 输出像素密度 | **显式给**，别依赖 `'figure'`（`_original_dpi` 陷阱） |
| `bbox_inches="tight"` | 导出时裁到内容边界 | 只影响文件、输出尺寸不可控 |
| `format=` | 显式指定格式 | 不靠扩展名猜；`open(...).read(4)` 可验 |
| `transparent=` | 背景透明 | PPT 场景常用 |
| `facecolor/edgecolor` | 覆盖图/边框色 | 与 rc 的 `savefig.*` 一族同源 |

```python
>>> fig.savefig("no_ext", format="pdf")               # 显式格式，不靠扩展名
>>> open("no_ext", "rb").read(4)
b'%PDF'
```

### 3.12.4 Notebook 与 CI 的固定姿势

- **Notebook**：`%matplotlib inline`（静态 png 内联）、`%matplotlib widget`（需 ipympl，可缩放）；`plt.show()` 在内联后端下是幂等的，不用判空；
- **CI/脚本**：`MPLBACKEND=Agg` 环境变量（3.12.1 规则 1）+ 出图函数返回 `Figure` 而不是依赖 `show()` + 断言文件存在与像素（3.15/3.16 的模板）；
- **无头≠不能交互**：Agg 也能 `fig.canvas.draw()` 拿像素、`print_figure` 出文件——交互后端只是多了窗口与事件循环。动画与 blitting 是 `ds-03b` B7 的主题。

**随堂自测 3.12**

1. 两类后端的本质区别是什么？CI 里用交互后端会得到什么形态的报错？
2. `MPLBACKEND=Agg` 与 `matplotlib.use("Agg")` 相比，各自免疫什么场景？
3. 为什么"SVG 里搜不到标题文字"？两种解法是什么？
4. 同一 figure 导出 300 dpi PNG 与默认导出，像素差多少？为什么改 `fig.set_dpi` 不算数（3.8.1）？
5. `list_builtin("interactive")` 为什么"看起来能用其实全错"？

**本节交付**：后端选型三条规则与 `MPLBACKEND` 姿势是 CI 出图的固定配置；矢量/位图选型表与 `savefig` 参数账服务于 3.16 的双格式导出。

---

## 3.13 pandas.plot 与 seaborn：生态桥接

3.1 说过整个生态都骑在 matplotlib 上。本节把"骑"的接口看清楚：pandas 是**转发器**，seaborn 是**两级 API**——两者的返回值都能无损接管，接管不了的差异集中在参数名与作用域上。

### 3.13.1 df.plot 就是转发器

```python
>>> import pandas as pd
>>> df = pd.DataFrame({"a": [1, 2, 3], "b": [3, 1, 2]})
>>> ax = df.plot(kind="line"); type(ax).__name__      # kind= 映射到 ax.plot/ax.bar/...
'Axes'
>>> ax2 = df.plot(kind="bar", ax=ax); ax2 is ax       # ax= 接管：同一根轴上继续叠画
True
```

`kind` 就是一张翻译表：`line→ax.plot`、`bar/barh→ax.bar/barh`、`hist→ax.hist`、`area→ax.stackplot`、`scatter→ax.scatter`、`box→ax.boxplot`……**翻译之外的能力（第二坐标轴、复杂标注）都要回 matplotlib 做**——`df.plot(...)` 的返回值就是为此准备的。

### 3.13.2 seaborn 的两级 API

```python
>>> import numpy as np, seaborn as sns
>>> rng = np.random.default_rng(0)
>>> df2 = pd.DataFrame({"x": rng.normal(size=60), "g": rng.choice(["A", "B"], 60)})
>>> g = sns.relplot(data=df2, x="x", y="x", col="g")  # ① figure 级：自带分面
>>> np.asarray(g.axes).shape                          # 返回 FacetGrid，面板是二维数组
(1, 2)
>>> g.ax                                               # ② 分面后 .ax 被禁用
Traceback (most recent call last):
  ...
AttributeError: Use the `.axes` attribute when facet variables are assigned.
>>> type(g.axes[0, 0]).__name__                       # 取单个面板，回到 matplotlib 世界
'Axes'
>>> type(sns.regplot(data=df2, x="x", y="x")).__name__  # ③ axes 级：直接返回 Axes
'Axes'
```

| 级别 | 例子 | 返回 | 适用 |
|------|------|------|------|
| figure 级 | `relplot`/`displot`/`catplot` | `FacetGrid`（分面网格） | 一张图铺多个子集 |
| axes 级 | `regplot`/`histplot`/`boxplot` | `Axes` | 精确放进我自己的 GridSpec |

选型规则：**要分面 → figure 级；要嵌入自己的多面板版式 → axes 级**。接管路径都是同一条：拿到 `Axes`（或 `g.axes[i, j]`）后按 3.3–3.10 继续改。

### 3.13.3 参数与作用域的三处冲突

| 差异 | matplotlib | seaborn | 后果 |
|------|-----------|---------|------|
| 直方图口径 | `hist(density=True)` | `histplot(stat="density")` | 照抄对方参数名 → `TypeError`（`stat=` 在 mpl 3.11 直接报错） |
| 样式作用域 | `rcParams` 全局 | `sns.set_theme(...)` 全局 + `axes_style` 上下文 | seaborn 改过的 rc 在它退出后**不自动还原** |
| 颜色默认 | prop cycle | seaborn 自带 palette | 混画时两套配色打架，显式 `color=` 收编 |

参数名的差别实测在文档里就写着：

```python
>>> "stat" in sns.histplot.__doc__                   # seaborn 的参数在自己的文档里
True
```

**样式冲突的处理纪律**：脚本入口 `sns.set_theme()` 或 `plt.style.use()` 二选一、不要叠；函数内要临时风格用 `with plt.style.context(...)` / `with sns.axes_style(...)`；被 seaborn 动过 rc 后想回默认，`plt.style.use("default")` 一键复位（3.11.2）。

### 3.13.4 单位机器：pandas 塞进来的日期轴

pandas 对 matplotlib 做的不止转发，还有**单位转换**：首次绘图时注册 `convert_units` 钩子，把 Period 数据交给自己的日期机器——连定位器都是 pandas 自带的（`ds-02` 版本注意第⑤条的下游）：

```python
>>> s = pd.Series([1, 2, 3], index=pd.period_range("2024-01", periods=3, freq="M"))
>>> ax = s.plot()
>>> type(ax.xaxis.get_major_locator()).__name__ != "AutoLocator"   # 轴已被日期机器接管
True
```

接管者具体是 `TimeSeries_DateLocator` 还是 `PandasAutoDateLocator`，取决于 pandas 两条注册路径（`timeseries.py` 与 `converter.py`）谁先被导入——**类名会漂移，但绝不是 3.10.1 的通用 `AutoLocator`**：刻度粒度与标签格式都随数据类型自动到位。

对照 3.10.1：**原生 datetime 走 matplotlib 自己的 `AutoDateLocator`，pandas 的 Period 走 pandas 注册的日期定位器**——无论哪条路，模式都是"数据类型 → 单位转换 → 定位器/格式化器"，三层各司其职。单位机器的注册机制（datetime/自定义类型的 `convert_units` 钩子）在 `ds-03b` B3 展开——自定义类型想要"直接画"，实现的就是这个钩子。

> **⚠️ 陷阱**：seaborn 的样式切换（`sns.set_theme`）**直接改全局 rcParams 且不会自动还原**；同一个 notebook 里 "seaborn 画完、matplotlib 精修" 时，两套网格/字体样式会叠加渗透——"上一格和这一格长得不一样"的样式漂移，根因在此，`plt.style.use("default")` 一步复位（3.11.2）。

> **延伸阅读**：seaborn 的 `FacetGrid` 实现与 matplotlib Artist 的关系、pandas 的单位注册，见配套文件 `ds-03b` 第 B3 节。

**随堂自测 3.13**

1. `df.plot(kind="bar")` 与 `ax.bar(...)` 是什么关系？`kind` 的完整翻译你能推出哪几个？
2. figure 级与 axes 级 seaborn API 各自的返回类型？分面后想改第 2 个面板的标题怎么写？
3. 在 seaborn 画好的 `FacetGrid` 上加一条 matplotlib 参考线，写出两条可选路径。
4. `hist(density=True)` 与 `histplot(stat="density")` 互抄参数各会得到什么报错？
5. 为什么"上一格 notebook 画的图网格和这一格不一样"？给出排查与复位各一步。

**本节交付**：两级 API 的选型与接管路径让 seaborn/pandas 的产物都能进 3.16 的统一版式；三处冲突是静默错误清单里"样式漂移"条目的出处。

---

## 3.14 性能工程：渲染何时变慢、如何量化

matplotlib 的性能剧本和 numpy/pandas **相反**：那边数据越大越要向量化，这边**渲染成本主要不在数据，在"对象数 × 输出格式"**。本节先把三本账量出来，再给三个杠杆。

### 3.14.1 三本账：数据点、对象数、输出后端

1. **数据点数**：光栅化器批量处理 path 顶点，点数翻倍成本远不翻倍；
2. **对象（Artist）数量**：每个 artist 一次 Python 级调度 + 一次渲染调用——**对象数比点数贵**；
3. **输出格式**：矢量导出要为每个 artist 写一段 PDF/SVG 指令，文字还要嵌字形——大图导出时这一项常是大头。

### 3.14.2 计时姿势：先预热，再量 draw

`fig.canvas.draw()` 就是完整渲染入口（3.3.3）。计时必须**预热一帧**（首帧含布局计算），本机实测（Agg，仅点数不同）：

```python
import time, numpy as np

rng = np.random.default_rng(0)
for n in [1_000, 10_000, 100_000]:
    fig, ax = plt.subplots()
    ax.scatter(rng.normal(size=n), rng.normal(size=n), s=2)
    fig.canvas.draw()                              # 预热：首帧含布局
    t0 = time.perf_counter(); fig.canvas.draw(); t1 = time.perf_counter()
    print(f"scatter n={n:>6}: {(t1 - t0) * 1000:7.1f} ms")
    plt.close(fig)
```

```
scatter n=  1000:    12.5 ms
scatter n= 10000:    12.5 ms
scatter n=100000:    31.6 ms
```

**1 千点和 1 万点完全同价**（固定开销主导），十万点才涨 2.5 倍——点数不是第一敏感项。对象数才是，同为 10 万个点：

```python
fig, ax = plt.subplots()
ax.plot(rng.normal(size=100_000))                   # 1 个 Line2D
fig.canvas.draw()
t0 = time.perf_counter(); fig.canvas.draw(); t1 = time.perf_counter()
print(f"1 Line2D x 1e5 pts : {(t1 - t0) * 1000:6.1f} ms")
plt.close(fig)

fig, ax = plt.subplots()
for i in range(1000):                               # 1000 个 Line2D
    ax.plot(rng.normal(size=100))
fig.canvas.draw()
t0 = time.perf_counter(); fig.canvas.draw(); t1 = time.perf_counter()
print(f"1000 Line2D x 100  : {(t1 - t0) * 1000:6.1f} ms")
plt.close(fig)
```

```
1 Line2D x 1e5 pts :  168.3 ms
1000 Line2D x 100  :  379.7 ms
```

**同样的 10 万点，切成 1000 个对象贵 2.3 倍**——"循环里逐条 plot"的代价在这。

### 3.14.3 三个杠杆：抽稀、栅格化、并对象

**杠杆一：数据侧抽稀。** 展示用图不需要全部点——按业务粒度聚合（日→周）、或等高线/密度替代散点；抽稀在**画之前**做，draw 不到的数据不花钱。

**杠杆二：`rasterized=True`（导出侧，收益最大）。** 大量点进矢量格式时，让该 artist 光栅化成位图嵌入，其余保持矢量：

```python
fig, ax = plt.subplots()
ax.scatter(rng.normal(size=20_000), rng.normal(size=20_000), s=2, rasterized=True)
t0 = time.perf_counter(); fig.savefig("r.pdf"); t1 = time.perf_counter()
print(f"rasterized pdf: {(t1 - t0) * 1000:5.0f} ms, {len(open('r.pdf', 'rb').read())} bytes")
plt.close("all")

fig, ax = plt.subplots()
ax.scatter(rng.normal(size=20_000), rng.normal(size=20_000), s=2)
t0 = time.perf_counter(); fig.savefig("v.pdf"); t1 = time.perf_counter()
print(f"vector pdf:     {(t1 - t0) * 1000:5.0f} ms, {len(open('v.pdf', 'rb').read())} bytes")
```

```
rasterized pdf:    78 ms, 28427 bytes
vector pdf:       148 ms, 313056 bytes
```

**体积小 11 倍、导出快 1.9 倍**；代价是这部分不再可无限放大（按 `savefig(dpi=)` 决定清晰度）。文字、坐标轴保持矢量，只有数据层进位图——出版图的标准做法。

**杠杆三：并对象。** 1000 条线并成一个 artist：多列数据一次 `ax.plot(y1, y2, y3, ...)`、`LineCollection` 批量线、`hexbin`/2d 直方图替代百万散点。判断口径照抄卷 1 第 15 章：**先量（本节两段脚本）→ 再减对象 → 后换手段**。

### 3.14.4 渲染反模式清单

| 反模式 | 症状 | 改成 |
|--------|------|------|
| 循环里 `plt.figure()` 不 close | 内存线性涨、`figure.max_open_warning` | `subplots()` + `plt.close(fig)`（3.2.2） |
| 十万点直出 PDF/SVG | 导出几十秒、文件几百 MB | `rasterized=True` 或抽稀 |
| 每帧 `ax.cla()` 重画全部 | 动画卡顿、对象反复重建 | `line.set_data(...)` 原地更新 |
| 逐点 `ax.annotate`/`ax.text` | 文本几百个、draw 爆炸 | 直标关键点 / 表格化 / 稀疏标注 |
| 交互场景用 SVG 后端 | 每次重绘重写整个 XML | Agg/交互后端，仅导出时用矢量 |
| 计时不预热 | 首帧含布局，数字虚高且抖 | 预热一帧再 `perf_counter`（3.14.2） |

> **⚠️ 陷阱**：**不要跨机器比较这些数字**——同机同代码内的相对值才有意义（`ds-01`/`ds-02` 同款纪律）；本节所有数字为本机实测、只保证数量级。另一个隐蔽项：`plt.close(fig)` 关的是 figure 不是窗口句柄之外的东西，**跑批函数不 close 才是内存事故的常见根源**。

> **延伸阅读**：Agg 光栅化的时间分布、`LineCollection`/`PathCollection` 的批处理实现、动画的最小重绘策略，见配套文件 `ds-03b` 第 B6、B7 节。

**随堂自测 3.14**

1. 三本账分别对应什么成本结构？为什么"点数翻倍、耗时没翻倍"？
2. 计时脚本为什么必须预热一帧？不预热会看到什么现象？
3. 10 万点分 1000 个对象比 1 个对象贵 2.3 倍——这条规律如何反推"循环 plot"的改法？
4. `rasterized=True` 换来什么、付出什么？什么内容**不该**栅格化？
5. 用 3.14.2 的脚本量化你自己机器上的三本账，把数字记进项目笔记。

**本节交付**：两段计时脚本与反模式清单是全书渲染性能的统一入口；"先量→减对象→换手段"回链卷 1 第 15 章，栅格化账目交付给 3.16 的导出环节。

---

## 3.15 调试与验证：静默错误清单

前 13 节埋了十几处"不报错但画错"的地雷，本节收口成三件套：**一棵排查树**（有症状时查）、**一张静默错误清单**（交付前过）、**一套断言**（把"看起来对"变成 `assert`）。

### 3.15.1 排查树：按症状走，不靠猜

| 症状 | 第一嫌疑 | 去哪查 |
|------|---------|--------|
| 什么都没有 | 没触发渲染 | 有没有 `show/savefig/draw`？（3.3.3）后端对不对？（3.12.1） |
| 某元素消失 | transform 选错 | 用 `transX.transform(点)` 直接算 display 坐标，看它落在哪（3.5.2） |
| 元素被裁/数据不全 | 轴范围不含数据 | `get_xlim` vs `dataLim` 断言（3.15.3）；autoscale 被 `set_xlim` 关了（3.10.4） |
| 东西叠在一起 | zorder 同档赌创建顺序 | 显式 zorder（3.6.4） |
| 画到了别的图上 | pyplot 状态机 | `plt.gcf()/gca()` 归属（3.2.2），改 OO |
| 颜色/样式"时对时错" | clim 未统一 / rc 被污染 | 显式 `vmin/vmax`（3.9.1）；`plt.style.use("default")` 复位（3.11/3.13） |
| 输出尺寸/字号不对 | dpi 与 pt 混淆 | 3.8.1 换算表 + `_original_dpi` 陷阱 |
| 循环/跑批越跑越慢 | figure 泄漏 | `plt.get_fignums()` 数一下（3.2.2）；3.14 反模式表 |

**排查的第一动作永远是"算，不是看"**：transform 直接算坐标、`get_xlim` 直接读范围——凡是能算出来的问题，别靠肉眼在图上找。

### 3.15.2 静默错误清单（交付前逐条过）

| # | 静默错误 | 根因节 | 防线 |
|---|---------|-------|------|
| 1 | 类别缺档被压成等距折线 | 3.6.2 | 类别先 `reindex` 补全；比较用 `bar` |
| 2 | `c=` 与 `color=` 语义混用 | 3.6.3 | 固定色走 `color=`，映射走 `c=`+cmap |
| 3 | 双轴图读错左右边 | 3.4.3 | 图例/轴标签写明量纲与颜色归属 |
| 4 | 手动 `set_xlim` 关 autoscale、共享轴不扩 | 3.10.4/3.8.4 | 跑批复位 `ax.autoscale()`；范围当参数 |
| 5 | y 轴截断让柱长失真 | 3.7.5 | 柱状图不截断；截断必须在标题标注 |
| 6 | 多子图各自 clim → 同色不同值 | 3.9.1 | 批量图显式统一 `vmin/vmax` |
| 7 | `bbox_inches="tight"` 导致版面尺寸不可控 | 3.8.3 | 排版在 constrained 层解决 |
| 8 | 默认导出 dpi 落到 `_original_dpi` | 3.8.1 | `savefig(dpi=...)` 永远显式 |
| 9 | figure 泄漏 / 串图 | 3.2.2 | OO + `close`；`get_fignums()` 体检 |
| 10 | 样式漂移与中文豆腐块 | 3.13.3/3.11.4 | 样式入口唯一；CI 断言字体存在 |
| 11 | 枚举参数传字符串，静默返回全量 | 3.12.1 | 类型化 API 用枚举，结果做断言 |

### 3.15.3 断言式检查：范围、对象数、归属

```python
>>> fig, ax = plt.subplots()
>>> _ = ax.plot([10, 20], [1, 2])
>>> _ = ax.set_ylim(0, 1.5)                    # 手动截断——上界 1.5 裁掉了 2
>>> xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
>>> xd = ax.lines[0].get_xdata()
>>> bool(xmin <= min(xd) and max(xd) <= xmax)   # x 轴包含数据
True
>>> bool(ymin <= 1 and 2 <= ymax)               # y 轴没包含——静默错误现形
False
>>> len(ax.lines), ax in fig.axes               # 对象数与归属
(1, True)
```

把三条契约（面板数、轴开关、viewLim ⊇ dataLim）打包成出图前的守门函数——**注意用 `ax.dataLim`（数据实际范围）而不是遍历 `lines`**：参考线（`axhline`/`axhspan`）用的是混合坐标（3.5.4），其 `get_xdata` 不在数据坐标系里，逐线比较会误报：

```python
def check_figure(fig, expect_panels):
    """出图前契约：面板数、轴开关、viewLim 必须包含 dataLim。"""
    assert len(fig.axes) == expect_panels, f"panels {len(fig.axes)} != {expect_panels}"
    for i, ax in enumerate(fig.axes):
        assert ax.axison, f"ax{i}: axes off"
        xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
        dl = ax.dataLim
        assert xmin <= dl.x0 and dl.x1 <= xmax, \
            f"ax{i}: x clipped xlim={(xmin, xmax)} data=({dl.x0}, {dl.x1})"
        assert ymin <= dl.y0 and dl.y1 <= ymax, \
            f"ax{i}: y clipped ylim={(ymin, ymax)} data=({dl.y0}, {dl.y1})"
    return True
```

与全书验证方法论的拼接：`ds-01` 1.17 管数组（形状/dtype/浮点比较）、`ds-02` 2.14 管数据（索引/行数/类型），**本节管图形（面板/范围/对象）**——三层都是同一句话：**让"看起来对"变成断言**。3.16 直接调用 `check_figure`。

> **⚠️ 陷阱**：断言要在**数据全放进去之后、导出之前**跑——`savefig` 才触发布局计算，constrained 布局下的最终排版问题（重叠、裁字）只有 draw 后能验；关键出图在 CI 里加一步"导出→重开→查像素/查文件头"（3.16 第 8 步）。

> **延伸阅读**：`dataLim`/`viewLim` 的联动与 autoscale 状态机、stale 重绘的确切时机，见配套文件 `ds-03b` 第 B1、B2 节。

**随堂自测 3.15**

1. "图上一片空白"写出三步排查，每步给出一个可执行的检查表达式。
2. `set_xlim` 之后新加的数据画不出来——根因、症状、复位各是什么？
3. 两个面板画同量纲数据、clim 不同——写一行断言把这事变成 `AssertionError`。
4. 为什么 `check_figure` 比 `dataLim` 而不遍历 `ax.lines`？`axhline` 会造成什么误报？
5. CI 里图正常生成、中文全是豆腐块——归因到哪节？给出防线（两层）。

**本节交付**：排查树 + 静默错误清单 + `check_figure` 是本章的收口产物，也是全书验证方法论的第三块拼图（1.17 → 2.14 → 3.15）；3.16 直接调用本节的契约函数。

---

## 3.16 综合实战：接过 ds-02 第 4、7 步出一张出版级多面板图

`ds-02` 2.15 的收官交付是"透视表 + 滚动序列"，本节把它们变成一张三面板报告图，八步走完，**每一步都标注用到的节号**。若你跑过 `ds-02` 综合实战，第 1 步直接改读它的产物（`long`、`daily` 从文件来）；此处用固定 seed 复刻同构数据，保证任何人可跑。

```python
import matplotlib
matplotlib.use("Agg")
import numpy as np, pandas as pd, matplotlib.pyplot as plt

# ---- 第 1 步：取数（复刻 ds-02 第 4、7 步产物：透视长表 + 滚动序列）----
rng = np.random.default_rng(42)
months = pd.period_range("2024-01", "2024-12", freq="M")
wide = pd.DataFrame(rng.integers(80, 200, size=(12, 3)),
                    index=months, columns=["north", "south", "east"])
long = wide.stack().rename("sales").reset_index()
long.columns = ["month", "region", "sales"]
daily = pd.Series(rng.normal(100, 15, 60).cumsum(),
                  index=pd.date_range("2024-01-01", periods=60, freq="D"),
                  name="revenue")
roll = daily.rolling(7).mean()
print("long:", long.shape, "| roll valid:", int(roll.notna().sum()))

# ---- 第 2 步：数据契约断言（ds-02 2.14 的姿势）----
assert wide.notna().all().all() and long.shape == (36, 3)
assert daily.index.is_monotonic_increasing and roll.notna().sum() == 54
print("data contracts: OK")

# ---- 第 3 步：构图（GridSpec + constrained，3.8.2/3.8.3）----
fig = plt.figure(figsize=(9, 4.5), layout="constrained")
gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1])

# ---- 第 4 步：面板 A 分组柱（pandas 转发 + 接管，3.13.1/3.7.5）----
axA = fig.add_subplot(gs[:, 0])
pivot = long.pivot(index="month", columns="region", values="sales")
pivot.plot(kind="bar", ax=axA, rot=45)
axA.set_title("Monthly sales by region")
axA.set_ylabel("sales")

# ---- 第 5 步：面板 B 时序 + 滚动均线（3.6.1/3.10.2）----
axB = fig.add_subplot(gs[0, 1])
axB.plot(daily.index, daily.values, lw=0.8, alpha=0.6, label="daily")
axB.plot(roll.index, roll.values, lw=2, label="7d MA")
axB.legend(loc="upper left", fontsize=8)
axB.set_title("Revenue trend")

# ---- 第 6 步：面板 C 分布（3.7.2）----
axC = fig.add_subplot(gs[1, 1])
axC.hist(daily.values, bins=12, density=True, alpha=0.7)
axC.set_title("Distribution")

# ---- 第 7 步：图形契约断言（3.15.3 的 check_figure）----
assert check_figure(fig, 3)
print("panels:", len(fig.axes), "| bar patches:", len(axA.patches),
      "| axB lines:", len(axB.lines), "| axC patches:", len(axC.patches))

# ---- 第 8 步：双格式导出与核对（3.12.2/3.12.3）----
fig.savefig("report.svg")
fig.savefig("report.png", dpi=200)
from PIL import Image
print("png @200dpi:", Image.open("report.png").size, "| svg bytes:", len(open("report.svg").read()))
```

实跑输出（本机）：

```
long: (36, 3) | roll valid: 54
data contracts: OK
panels: 3 | bar patches: 36 | axB lines: 2 | axC patches: 12
png @200dpi: (1800, 900) | svg bytes: 75220
```

四行输出对应四层验收，每一行都能反推一个学过的机制：

| 输出行 | 验收对象 | 对应机制 |
|--------|---------|---------|
| `long: (36, 3) / roll valid: 54` | 数据形状与滚动窗口有效位 | `ds-02` 变形与 rolling（首 6 日 NaN） |
| `data contracts: OK` | 输入契约 | 2.14 断言方法论 |
| `panels: 3 / patches: 36 / lines: 2` | 图形契约 | 容器类型与对象数（3.4.2/3.7）；`check_figure` 全绿 |
| `png (1800,900) / svg 75220` | 输出契约 | figsize×dpi 换算 9×200=1800（3.8.1）、矢量极小（3.12.2） |

两个设计决定值得复盘：**面板 A 用 `pivot.plot(ax=...)` 而不是循环 `ax.bar`**——pandas 一次算好分组偏移并批量造 36 个 Rectangle，循环画要自己管 x 位置且每次调用都过一遍单位转换（3.14 对象账）；**面板 B 的日线用 `alpha=0.6` 细线、均线用粗线**——同 axes 多 artist 的层与权重交给 zorder/线宽表达（3.6.4/3.10.5），而不是画两张图。

把 `check_figure` 与导出核对包进一个函数，就是卷 3 报告图的雏形：

```python
def report_figure(long, daily, roll, out_png="report.png", out_svg="report.svg"):
    """透视长表 + 日序列 -> 三面板出版图；出图即断言，导出即核对。"""
    fig = plt.figure(figsize=(9, 4.5), layout="constrained")
    gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1])

    axA = fig.add_subplot(gs[:, 0])
    long.pivot(index="month", columns="region", values="sales").plot(
        kind="bar", ax=axA, rot=45)
    axA.set_title("Monthly sales by region"); axA.set_ylabel("sales")

    axB = fig.add_subplot(gs[0, 1])
    axB.plot(daily.index, daily.values, lw=0.8, alpha=0.6, label="daily")
    axB.plot(roll.index, roll.values, lw=2, label="7d MA")
    axB.legend(loc="upper left", fontsize=8); axB.set_title("Revenue trend")

    axC = fig.add_subplot(gs[1, 1])
    axC.hist(daily.values, bins=12, density=True, alpha=0.7)
    axC.set_title("Distribution")

    check_figure(fig, 3)                       # 断言不过就地炸，不产出坏图
    fig.savefig(out_svg); fig.savefig(out_png, dpi=200)
    return fig
```

**随堂自测 3.16**

1. 默写八步的顺序与每步的节号出处（第 1、2、7、8 步是骨架）。
2. 面板 A 若改成 `for m in months: axA.bar(...)`，要多管哪些事？对象数变多少？
3. `check_figure` 能在面板 B（日期轴）上直接比 `dataLim` 与 `get_xlim()`——为什么两者在同一数值空间？
4. 第 8 步为什么要同时导出 png 与 svg？各自的验收点是什么（写出检查表达式）。
5. 把面板 C 换成 ECDF（3.7.6），改动落在哪几行？`check_figure` 需要动吗？

**本节交付**：八步模板 + `report_figure()` 是本章全部机制的集成产物——卷 3 的工作报告图、`ds-04` 的分布诊断图都从这里派生；四层验收（数据/契约/图形/输出）是全书验证方法论的完整形态。

---

## 本章小结

| 主题 | 核心要点 |
|------|---------|
| 生态定位 | matplotlib 是底层画布，命令式 vs 声明式两代际；上游库（pandas/seaborn）画完都还你 `Axes` |
| 两条接口 | pyplot 是全局状态机，串图/泄漏是原理必然；纪律：**`plt` 只管建图与保存** |
| Artist 模型 | `plot()` 造对象不画图；容器 `ax.lines/patches/collections`；渲染延迟到 `show/savefig/draw`；`remove()` 只摘链 |
| Fig/Axes 解剖 | fig 级/ax 级归属表（`suptitle` vs `title`）；方法动物园 = 造 Artist + autoscale + 返回容器；`twinx` = 同位新 Axes + 共享组 |
| transform | 四套坐标系同点四义；贴面板用 `transAxes`、跟数据用 `transData`、偏移用像素；`axhline` 是混合变换 |
| 线型与散点 | 类别轴等距压缩缺档；`c` 映射 vs `color` 固定；zorder 是排序值，同档赌创建顺序 |
| 统计图族 | 容器总表（hist→tuple/boxplot→dict/bar→BarContainer…）；`density` 归一；1.5×IQR 规则；柱状不截断；ECDF 无分箱 |
| 多面板 | `px = 英寸 × dpi`、字号 pt 锁物理尺寸；`_original_dpi` 陷阱；布局三件套作用时机不同；`sharex` 联动 limits |
| 色彩 | 管线 `值→Normalize→cmap→RGBA`；**clim 是第二自由度**，批量图必须统一；cmap 按方向选三类；colorbar 是一根 Axes |
| 精修 | Locator 管位置、Formatter 管文本；`legend()` 消费 label；`set_xlim` 顺手关 autoscale |
| 配置 | rc 作用域三层、优先级链对象属性最高；`.mplstyle` 进版本库；中文三坑（字体顺序/负号/环境依赖） |
| 输出与后端 | 交互 vs 无头两类；`MPLBACKEND=Agg` 最稳；`BackendFilter` 要枚举；SVG 默认字形转 path、`fonttype:none` 可编辑 |
| 桥接 | `df.plot` 是转发器（`kind`/`ax=`）；seaborn figure 级返回 `FacetGrid`、axes 级返回 `Axes`；单位注册换日期轴 |
| 性能 | 三本账（点数/对象数/输出格式）；先预热再计时；`rasterized` 体积 11 倍差；循环 plot → 并对象 |
| 调试 | 排查树按症状走；11 条静默错误清单；`check_figure` 三契约（面板数/轴开关/viewLim ⊇ dataLim） |
| 综合实战 | 八步模板 + `report_figure()`；四层验收：数据 → 契约 → 图形 → 输出 |

---

#### 练习 3

**基础：把机制用对**

1. **状态机预测**：不运行，写出下面代码的标题落在哪张图上，再验证。
   ```python
   import matplotlib.pyplot as plt
   fig1, ax1 = plt.subplots()
   plt.plot([1, 2], [3, 4])
   fig2, ax2 = plt.subplots()
   ax2.set_title("second")
   plt.gca().set_title("current")
   ```

2. **修 bug（figure 泄漏）**：函数本意"每组画一张存盘"，现状是内存涨 + 只剩最后一张图，修复并解释两处根因。
   ```python
   def plot_groups(df):
       for g, sub in df.groupby("g"):
           plt.figure()
           plt.plot(sub["x"], sub["y"])
           plt.savefig(f"{g}.png")
   ```

3. **transform 选型**：三个需求各选一套坐标系并写出行数级代码——(a) 图例钉在第 2 个面板右上角内侧；(b) 一条参考线的标签跟着 xlim 漂；(c) 箭头文字相对锚点固定偏移 10 px。

4. **容器默写**：`hist`/`boxplot`/`violinplot`/`bar`/`scatter`/`errorbar`/`fill_between`/`ecdf` 的返回容器类型，不许翻书；想逐根改柱子颜色，从哪个容器拿？

5. **尺寸计算**：单栏 7 in、正文字号 9 pt，(a) `savefig(dpi=600)` 输出多少像素？(b) 10 pt 字在 300 dpi 下多少 px？(c) 为什么改 `fig.set_dpi(200)` 不影响默认导出的像素（3.8.1）？

6. **缺档防线**：`ax.plot(["Q1", "Q2", "Q4"], y)` 画出来 Q3 去哪了？给出"补全"与"换图型"两条不同原理的修复，并各写一行断言防回归。

7. **统一 clim**：两个面板画同量纲数据，写一行断言抓"同色不同值"（提示：比较 `im.get_clim()` 或 mappable 的 clim）。

**进阶：把代码写稳**

8. **体检函数扩展**：把 3.15.3 的 `check_figure` 扩展为：每个面板必须有非空标题、图例存在且句柄数 ≥1、`ax.get_window_extent()` 在 figure 画布内；对 3.16 的三面板图全部通过，再人为制造一个失败案例看报错信息。

9. **串图取证**：分别用 pyplot 状态式与 OO 式实现"10 张图的批量导出"，用 `plt.get_fignums()` 与 `tracemalloc`（卷 1 第 15 章）量化两种写法的 figure 数与峰值内存。

10. **出版级加注**：在 3.16 的面板 B 上完成三件事：最高点 annotate（offset points）、7 日均线加粗到 2.5、日线 `alpha` 调到不遮均线；完成后跑 `check_figure` 与导出核对。

11. **性能账**：复现 3.14 的两段计时脚本，记录你机器上的"点数账""对象数账""栅格化账"三组数字；再把"1000 条线"改写成一次多列 `plot(y1, y2, ..., y1000)` 对比对象数与耗时。

12. **SVG 可编辑性**：导出两份 SVG（默认与 `svg.fonttype:"none"`），用 `grep -c "<text"` 与 `grep -c "<use"` 验证差异，并说明"在 Illustrator 里改标题"哪份能改。

13. **中文全链路**：写一份含中文字体的 `.mplstyle`，画一张带负值的中文标题图；在没有该字体的环境（或临时改字体名）复现豆腐块，用 `matplotlib.font_manager` 写出字体存在性断言。

14. **接管 seaborn**：用 `sns.relplot(col=...)` 分面后，在第 2 个面板上叠加一条 matplotlib 参考线与一个 annotate（两条路径：`g.axes[0,1]` 或取 figure 遍历 `fig.axes`），说明哪条更稳。

**深水：往实现里看一层**

15. **stale 取证**（→ `ds-03b` B1）：构造"改属性但不重绘"与"触发重绘"两个最小实验，用 `fig.stale` 与两次 `savefig` 的字节差异证明延迟渲染；再找出 `plt.show()` 在 Agg 下为什么什么都不做。

16. **自定义 Locator**（→ `ds-03b` B3）：实现一个"只在 0/5/10 处打刻度"的 `MultipleLocator` 子类（重写 `tick_values`），挂到轴上验证；再用 `FuncFormatter` 把刻度标签改成 `"5 kg"`，解释 Locator 与 Formatter 的职责分界。

---

**进入下一章的准备**（对应开篇四条学习目标）：

**建模型**
- ✅ 能把任何一张图解释为 Figure → Axes → Artist 树，并说出 `plot()` 之后、`draw()` 之前图在哪
- ✅ 能从任意 `ax.*` 方法的返回值推出它造了哪些 Artist、进了哪个容器

**会定位**
- ✅ 四套坐标系随口报出原点/范围；"放错位置"第一反应是查 `transform=` 而不是试坐标
- ✅ 能解释 `axhline` 为什么自动贯穿、`twinx` 联动了什么没联动什么

**会出图**
- ✅ 统计图按"目的 → 方法 → 容器"选型，分箱/截断/误差口径三个统计坑随口能提
- ✅ GridSpec 多面板、Locator/Formatter 刻度、图例锚定、统一 clim 的批量配色落到肌肉记忆

**会工程**
- ✅ dpi/pt 换算、`_original_dpi`、SVG 字形转 path、`MPLBACKEND=Agg` 四个工程结论能直接用
- ✅ 静默错误清单 11 条能过一遍，`check_figure` 与四层验收入了全书验证方法论

准备好了就进入 `ds-04`（SciPy 与统计）：概率分布、假设检验、优化——那里画的每一张分布图、置信区间图、QQ 图，选型靠本章 3.7 的容器总表，排版靠 3.8 的多面板，验收靠 3.15 的契约断言。**图从这里开始只是统计结论的表达层；本章没讲的统计口径（检验功效、多重比较），正是下一章的主角。**

---

## 参考文献

按"原始论文与专著 / 官方文档 / 源码"三类排列。正文中的"延伸阅读"均指向本表。

**原始论文与专著**

1. Hunter, J. D. (2007). *Matplotlib: A 2D Graphics Environment.* Computing in Science & Engineering, 9(3), 90–95. —— matplotlib 奠基论文，Figure/Axes/Artist 的 Artist-based 设计与"一切可见物皆 Artist"的原始出处（3.3、3.4）。<https://doi.org/10.1109/MCSE.2007.55>
2. Wilkinson, L. (2005). *The Grammar of Graphics* (2nd ed.). Springer. —— 声明式绘图的理论源头；3.1 命令式/声明式对照、Altair/Vega 一族的思想背景。
3. Tufte, E. R. (2001). *The Visual Display of Quantitative Information* (2nd ed.). Graphics Press. —— "数据墨水比"与图表精修原则，3.10.5 检查清单与 3.7.6 省墨选型的思想出处。

**官方文档**

4. Matplotlib Quick Start —— 对象模型、两条接口与首个图形的官方入门（3.2–3.4）。<https://matplotlib.org/stable/users/explain/quick_start.html>
5. Matplotlib Transformations Tutorial —— 四套坐标系与复合变换的官方长文，即 3.5 的展开版（3.5）。<https://matplotlib.org/stable/users/explain/artists/transforms_tutorial.html>
6. Matplotlib Customizing —— `rcParams`、样式表与属性循环的完整手册（3.3.4、3.11）。<https://matplotlib.org/stable/users/explain/customizing.html>
7. Matplotlib Backends —— 后端概念、无头渲染与嵌入（3.12）。<https://matplotlib.org/stable/users/explain/figure/backends.html>
8. Matplotlib Choosing Colormaps —— cmap 三类、感知均匀与色盲友好（3.9.2）。<https://matplotlib.org/stable/users/explain/colors/colormaps.html>
9. seaborn User Guide —— figure 级/axes 级两级 API 与分面语法（3.13）。<https://seaborn.pydata.org/> · <https://seaborn.pydata.org/tutorial.html>
10. pandas Visualization —— `df.plot` 的 `kind` 翻译表与返回对象（3.13.1）。<https://pandas.pydata.org/docs/user_guide/visualization.html>

**源码**

11. `lib/matplotlib/artist.py` —— `Artist.set` 的别名归一、`get_children` 与 stale 标记（对应 3.3、3.15）。
12. `lib/matplotlib/axes/_base.py` · `lib/matplotlib/axes/_axes.py` —— 方法动物园、autoscale 与 `dataLim`（对应 3.4、3.7、3.15.3）。
13. `lib/matplotlib/transforms.py` —— 四段坐标链、`BlendedGenericTransform` 与复合（对应 3.5）。
14. `lib/matplotlib/figure.py` · `lib/matplotlib/backend_bases.py` —— draw/print_figure 流水线与 `_original_dpi` 的解析（对应 3.8.1、3.12.3）。
15. `lib/matplotlib/ticker.py` · `lib/matplotlib/collections.py` —— Locator/Formatter 家族与容器类实现（对应 3.7、3.10）。
16. `pandas/plotting/_matplotlib/converter.py` · `pandas/plotting/_matplotlib/timeseries.py` —— 单位注册与日期定位器的两条路径（对应 3.13.4）。
