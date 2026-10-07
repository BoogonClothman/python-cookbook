# Matplotlib 深水：draw 流水线、坐标变换与渲染内核

> **定位**：这是 `ds-03` 第 3 章的配套深水文件，不是独立章节。主章把 matplotlib 当"Figure → Axes → Artist 三棵树 + 四套坐标"来用；本文件回答主章只给了结论的几个问题——**一次 `savefig` 在内部究竟按什么顺序做了什么**、**坐标轴为什么能看懂任意数据类型**、**渲染慢的时候钱花在哪一行**。
>
> **学习目标**：
> - **看得见**：能把 stale、Artist 树、transform 链、单位机器对应到可复现的实验与源码位置
> - **算得清**：能预判一次 draw 的成本分布，并说出三个渲染杠杆各值多少
> - **判得准**：能解释"改了没生效""元素放错位置""导出忽然几百 MB"的根因归属
> - **知道边界**：知道什么时候该光栅化、什么时候该 blit、什么时候该离开 matplotlib
>
> **阅读前提**：主章 3.1–3.16。主章的延伸阅读从这些位置指过来：3.2/3.3/3.4 → B1；3.5 → B2、B3；3.6 → B3；3.7 → B1；3.8 → B2；3.9 → B5；3.10 → B1、B3；3.11 → B1；3.12 → B4、B7；3.13 → B3；3.14 → B6、B7；3.15 → B1、B2。**B4 与 B8 主章没有回链**：它们是按 README 纲目补的两节，分别承接 3.12（后端与输出）和 3.14/3.15（性能与边界）。
>
> **验证环境**：所有输出在 Linux（WSL2，x86_64，glibc 2.43）上的 Python 3.14.4 + matplotlib 3.11.2 + NumPy 2.5.3 + pandas 3.0.6 实跑得到，后端为无头 **Agg**。计时为本机重复 3–5 次取最小值，随负载波动，文中只保证量级与相对关系。本环境**未安装** seaborn、SciPy、ffmpeg，涉及它们的结论标注为"文献/源码"而非实测。凡涉及 `_lut`、`_converter`、`_stale_viewlims`、`_child` 这类私有成员的输出都标注"仅取证"；引用的行号以 3.11.2 为准，版本间会漂移。

---

## B1 draw 全流水线与 stale 机制

主章 3.3 的结论是"`plot()` 只造对象，渲染发生在 `show()`/`savefig()`"。本节把"渲染"这一步拆开：它由谁发起、按什么顺序走、stale 标记如何从一条线传到整张图、以及为什么 `savefig` 结束后 `fig.stale` 反而是 `True`。

### B1.1 一次 `canvas.draw()` 的六个阶段

```python
# 仅取证：Agg 画布的 draw() 源码骨架
def draw(self):
    self.renderer = self.get_renderer()      # 1. 取/建渲染器
    self.renderer.clear()                    # 2. 清空像素缓冲
    with (...):
        self.figure.draw(self.renderer)      # 3. 画整张图
        super().draw()                       # 4. 通知 GUI/画布刷新
```

第 3 步 `Figure.draw` 是主体，它自己又是一条流水线：

```
Figure.draw(renderer)                       # artist.py 的 @_finalize_rasterization + @allow_rasterization 包裹
├─ with self._render_lock:                  # 线程安全：多线程 draw 会串行化
├─ artists = self._get_draw_artists(renderer)   # ① 过滤 patch、剔除 animated、按 zorder 排序
│                                              #    并对每个 Axes 执行 apply_aspect（aspect 在这里生效）
├─ renderer.open_group("figure", gid=...)
├─ self.get_layout_engine().execute(self)   # ② constrained/tight 布局求解
├─ self.patch.draw(renderer)                # ③ 先铺背景
├─ mimage._draw_list_compositing_images(...)  # ④ 按序画 artists；见下方"图像合成"说明
├─ renderer.close_group("figure")
└─ finally: self.stale = False              # ⑤ 清 stale
   DrawEvent("draw_event", ...)._process()  # ⑥ 广播事件（动画、回调的入口）
```

`Axes.draw` 是同一模式的下一层，顺序值得背下来：

```
Axes.draw(renderer)                          # axes/_base.py
├─ self._unstale_viewLim()                   # ① 兑现待处理的 autoscale（见 B1.8）
├─ self._stale = True                        # ② 绘制期间屏蔽回调，避免"画的时候又标脏"
├─ self.apply_aspect(...)                    # ③ 按 aspect 收缩活动框
├─ artists = self.get_children(); artists.remove(self.patch)
├─ 条件移除 spines（frameon=False）、移除 axis（axison=False）
├─ if not canvas.is_saving(): 剔除 animated artists   # ④ 保存时 animated 反而要画（见 B7.1）
├─ artists = sorted(artists, key=attrgetter("zorder"))  # ⑤ 稳定排序，见 B1.3
├─ 按 _rasterization_zorder 切出需要整块光栅化的艺术家  # ⑥ 见 B6.5
├─ mimage._draw_list_compositing_images(...)
└─ self.stale = False
```

实测各阶段的量级（640×480、一条 10 万点折线、本机）：

```
canvas.get_renderer()         0.003 ms
renderer.clear()              0.025 ms      # 清 640×480 缓冲，几乎免费
fig.draw_without_rendering()  3.53  ms      # 只跑布局，不落笔
fig.draw(renderer)          123.90  ms      # 真正的绘制
canvas.draw()               125.18  ms      # 上面的全流程
fig.canvas.print_png(...)   127.38  ms      # 多出编码与压缩
```

**结论先行**：布局只占一次保存的约 **3%**（3.5/125），"图慢"几乎总是慢在 `Artist.draw` 这一步，而不是布局或缓冲管理。所以主章 3.14 的三个杠杆（简化、分块、对象合并）全部作用在同一处——见 B6。

补一句 `_draw_list_compositing_images` 的机制，它的名字容易让人误解：它确实会把**相邻的 `_ImageBase`** 合成一张再画，但前提是渲染器允许（`not renderer.option_image_nocomposite()`）。而 **Agg 硬编码返回 `True`（"直接合成到画布更快"），所以位图路径上这一步直接退回成"逐个 `a.draw(renderer)`"**；只有 pdf/ps/svg/pgf 才按 `rcParams["image.composite_image"]` 决定。换句话说，`image.composite_image` 对 PNG 输出**没有任何影响**——它在矢量后端里才是"多张小图合成一张"的开关。

### B1.2 stale 的三级传播

`stale` 是 matplotlib 唯一的"脏标记"。它不是一个布尔字段，而是一条**回调链**：

```python
# artist.py（仅取证）
def stale(self, val):
    self._stale = val
    if self._animated:          # animated artist 不参与常规绘制，也就不标脏
        return
    if val and self.stale_callback is not None:
        self.stale_callback(self, val)

def _stale_axes_callback(self, val):        # 普通 Artist 的默认回调
    if self.axes:
        self.axes.stale = val

def _stale_figure_callback(self, val):      # Axes 与 figure 级 Artist 的回调（figure.py）
    if (fig := self.get_figure(root=False)) is not None:
        fig.stale = val
```

回调不是构造时装的，而是**挂载时**装的：`Artist.axes` 的 setter 里有一行 `self.stale_callback = _stale_axes_callback`（`artist.py:314`），而 `Figure.add_axes` 给 Axes 装上 `_stale_figure_callback`（`figure.py:789`，figure 级 text/image/colorbar 同理）。于是 `line.set_color("red")` 的完整传播是：`Line2D` → `Axes` → `Figure`，三级一起变脏：

```python
>>> fig, ax = plt.subplots()
>>> fig.stale, ax.stale
(True, True)                       # 刚建图就是脏的
>>> ln, = ax.plot([0, 1], [0, 1])
>>> fig.canvas.draw()              # 触发一次真实绘制
>>> fig.stale, ax.stale, ln.stale
(False, False, False)              # 画完全清
>>> ln.set_color("red")
>>> fig.stale, ax.stale, ln.stale
(True, True, True)                 # 一个属性改动传到顶
```

两条容易忽略的推论：

1. **`animated=True` 会截断传播**。设了 `line.set_animated(True)` 之后，改它的属性不会让 figure 变脏——**主图不会因为它重绘**，这正是 blitting 省时间的前提（B7.2），代价是你不主动重绘它就永远停在旧帧上。
2. **stale 不做"局部重绘"**。它只有"整张图脏 / 不脏"两态，即使只改了一个刻度标签的颜色，下一次 draw 也是全量重画。所以"省重绘"的唯一办法是 blit 或缓存。

> **⚠️ 陷阱**：同一个 artist **不能挂在两根轴上**。`Artist.axes` 的 setter 一旦发现"已有轴、又要挂到另一根"就直接拒绝，而且对象不会被加入第二根轴：

```python
>>> f, axs = plt.subplots(1, 2); ln, = axs[0].plot([0, 1], [0, 1])
>>> axs[1].add_line(ln)
ValueError: Can not reset the Axes. You are probably trying to reuse an artist
            in more than one Axes which is not supported
>>> axs[1].lines
<Axes.ArtistList of 0 lines>
```

> 想在两根轴上展示同一份数据，只能**为每根轴各建一个 artist**——数据可以共享同一个 ndarray（零拷贝），对象不能共享。这也是"复制一张子图"必须重建 artists 而不能直接搬的原因。

### B1.3 排序走两处，都是稳定排序

主章 3.6.3 讲 zorder，机制上它落在两处 `sorted`：

| 位置 | 代码 | 作用范围 |
|------|------|---------|
| `figure.py` 的 `Figure._get_draw_artists` | `sorted((a for a in artists if not a.get_animated()), key=lambda a: a.get_zorder())` | figure 级 children（axes、suptitle、figure 级 legend 等） |
| `axes/_base.py` 的 `Axes.draw` | `sorted(artists, key=attrgetter("zorder"))` | axes 级 children（线、集合、文本、spine……） |

两处都是 Python 内置 `sorted`，即 **Timsort、稳定排序**：**zorder 相同的艺术家保持插入顺序**，谁先 `plot` 谁在下面。

```python
>>> l1, = a.plot([0,1],[0,1], zorder=3, color="red")
>>> l2, = a.plot([0,1],[1,0], zorder=3, color="blue")
>>> l3, = a.plot([0,1],[.5,.5], zorder=1, color="green")
>>> sorted([l1, l2, l3], key=attrgetter("zorder")).index(l1) < \
... sorted([l1, l2, l3], key=attrgetter("zorder")).index(l2)
True                              # 同 zorder，插入序决定压盖关系
```

> **⚠️ 陷阱**：既然稳定排序是契约的一部分，"后画的盖住先画的"就成了可依赖行为；反过来说，**想改压盖顺序又不改 zorder，就必须改添加顺序**（删了重加）。`zorder` 支持小数，默认层级本身就是"整数打底、小数插缝"：`AxesImage` 0、`Patch` 1、`Line2D`/gridline 2、`Text` 3，而 axis 是 1.5、spine 是 2.5、tick 是 0——**要插到任意两层之间，用一个中间小数最省事**，不必把整条链重排。

### B1.4 stale 取证：两次 `savefig` 的字节差

主章练习 15 要求用字节差证明延迟渲染。这里给出可复现的最小实验：

```python
>>> import io
>>> fig, ax = plt.subplots(); ax.plot([0,1,2],[0,1,0])
>>> def snap():
...     b = io.BytesIO(); fig.savefig(b, format="png"); return b.getvalue()
>>> b1 = snap(); b1[:8]
b'\x89PNG\r\n\x1a\n'              # PNG 头固定，说明比的是像素内容
>>> len(b1)
24000
>>> ax.lines[0].set_color("crimson")
>>> len(snap())
24169                             # 改了颜色 -> 字节变了
>>> len(snap())
24169                             # 没再改 -> 字节完全一致（PNG 无时间戳）
```

这同时给出两个事实：**PNG 是逐字节可复现的**（同一进程内两次保存完全一致），而 **`fig.stale` 不能当"需要重绘"的信号**——

```python
>>> fig.canvas.draw(); fig.stale
False
>>> _ = snap(); fig.stale
True                              # savefig 之后反而变脏了
```

**为什么**：`print_figure` 在打印期间用上下文管理器临时改 figure 属性（`layout_engine="none"`、`dpi=...`），而属性赋值走 `Artist._update_props`，它在末尾统一 `self.stale = True`；等上下文退出、属性还原时**又赋一次值**，于是最终状态是脏的。用回溯钩住 `stale` 的 setter 可以直接看到来源（仅取证）：

```
set stale=True from:
  backend_bases.py:2284 print_figure   -> _cm_set(layout_engine="none")
  backend_bases.py:2235 print_figure   -> _setattr_cm(dpi=...)
  axes/_base.py:2045    apply_aspect   -> _set_position
  ...
```

> **机制洞察**：matplotlib 的"延迟渲染"不是靠复杂的状态机，而是**一把脏标记 + 全量重绘**。这解释了主章 3.3.5 的所有现象：改了没生效 = 没触发 draw；删了还在 = 对象没解链（B1.7）；Notebook 里"重跑单元就好了" = 重跑触发了一次 draw。

> **延伸阅读**：`Figure.draw` / `Axes.draw` 见 `matplotlib/figure.py`、`matplotlib/axes/_base.py`；脏标记回调与 `_finalize_rasterization` 见 `matplotlib/artist.py`；`print_figure` 的属性上下文见 `matplotlib/backend_bases.py`。

### B1.5 pyplot 的 figure manager：单例注册表

`plt.subplots()` 返回的 `fig` 背后还有一个全局注册表，主章没展开的部分在这里：

```python
>>> import matplotlib._pylab_helpers as ph
>>> fig, ax = plt.subplots()
>>> list(ph.Gcf.figs), plt.get_fignums()
([1], [1])
>>> mgr = ph.Gcf.get_fig_manager(fig.number)
>>> type(mgr).__name__, type(mgr.canvas).__name__, mgr.toolbar
('FigureManagerBase', 'FigureCanvasAgg', None)
>>> plt.close(fig)
>>> plt.fignum_exists(fig.number), list(ph.Gcf.figs)
(False, [])
```

- `Gcf`（Global figure container）是 `{number: manager}` 的字典；`plt.get_fignums()` 只是它的键视图。
- manager 把 **figure 与 canvas 绑定**：`fig.canvas is mgr.canvas` 为 `True`。Agg 下的 manager 没有工具栏（`toolbar is None`），GUI 后端才有。
- `plt.close(fig)` 从注册表移除；**不 close 的 figure 会一直占内存**，这是循环里建图最真实的泄漏源。pyplot 会在第 21 张图时报警（实测为 `RuntimeWarning`）：

```
RuntimeWarning: More than 20 figures have been opened. Figures created through
the pyplot interface ... are retained until explicitly closed ...
```

`gca()` 的查找路径只有两行——**没有 axes 就顺手建一个**：

```python
>>> f, a = plt.subplots()
>>> type(f._axstack).__name__, f.gca() is a
('_AxesStack', True)
# Figure.gca(): ax = self._axstack.current(); return ax if ax is not None else self.add_subplot()
```

`_AxesStack` 记录"谁是当前 axes"（不只是"有哪些 axes"），所以 `fig.axes` 与 `fig.gca()` 是两个问题：前者是列表，后者是栈顶。多面板图里 `plt.gca()` 拿到的往往是最后创建的那根轴——**显式持有 `ax` 是唯一稳的写法**（回链主章 3.2）。

### B1.6 `set()` 的别名归一：表挂在类上，不挂在 Artist 上

`ax.set(xlabel="X")` 与 `line.set(lw=3)` 都会工作，但 `ax.set(lw=3)` 会直接报错——原因在别名表的挂载位置：

```python
>>> from matplotlib.artist import Artist
>>> from matplotlib.lines import Line2D
>>> from matplotlib.collections import Collection
>>> {c.__name__: len(getattr(c, "_alias_to_prop", {}) or {})
...  for c in (Artist, Line2D, Collection)}
{'Artist': 0, 'Line2D': 10, 'Collection': 12}
>>> Line2D._alias_to_prop["lw"], Line2D._alias_to_prop["c"]
('linewidth', 'color')
>>> ax.set(lw=3)
AttributeError: Axes.set() got an unexpected keyword argument 'lw'
>>> ln.set(lw=3, c="red", ls="--")      # Line2D 有表，能归一
```

机制是两段：

1. `Artist.set` = `self._internal_update(cbook.normalize_kwargs(kwargs, self))`。`normalize_kwargs` 读 **实例所属类的 `_alias_to_prop`**，把 `lw` 翻成 `linewidth`；
2. `_update_props` 逐个 `getattr(self, "set_<name>")`，找不到就抛 `AttributeError("<类名>.set() got an unexpected keyword argument '<名>'")`，全部成功后统一 `pchanged(); stale = True`。

别名表由 `matplotlib._api.define_aliases` 装饰器生成，`3.11` 只装饰了 `Line2D`、`Collection`、`Patch`、`Text` 四个类。`Axes` 的表是空的，`_AxesBase.set` 只是一个转发到 `Artist.set` 的 lambda，所以：

> **⚠️ 陷阱**：`ax.set(...)` 只接受 `Axes` 自己的 `set_*` 方法名（`xlabel`、`xlim`、`facecolor`……），**不含 Artist 别名**。想批量设置轴内元素，要么对每个对象 `set()`，要么用 `plt.setp(lines, lw=2)`（`setp` 走的就是同一套别名表，支持 `setp(lines, "lw")` 查询）。

### B1.7 `remove()` 的解链：一半干净，一半是坑

```python
>>> f3, a3 = plt.subplots(); l3, = a3.plot([0,1],[1,0])
>>> n0 = len(a3._children); l3.remove()
>>> len(a3._children), a3.lines, l3.axes, l3.figure is f3
(0, <Axes.ArtistList of 0 lines>, None, False)
>>> l3.remove()                      # 再来一次
ValueError: list.remove(x): x not in list
```

`remove()` 做四件事：调用 `_remove_method`（通常是 `list.remove`）、清掉 `stale_callback`、把 `axes` 置 `None`、把 `_parent_figure` 置 `None`。三个必须知道的细节：

1. **不是幂等**。`_remove_method` 调用后没有清空，第二次调用进同一个 `list.remove` 直接 `ValueError`；而且 `_remove_method is None` 的艺术家会抛 `NotImplementedError("cannot remove artist")`——**能不能删取决于父容器有没有给它装 `_remove_method`**。
2. **不删图例条目**。docstring 明说没有这个支持；`ax.legend()` 里的句柄要自己重建。
3. **不动坐标范围**。删完数据范围仍是旧的，要 `ax.relim(); ax.autoscale_view()` 才收紧（B1.8）。

好在它是**真解链**：`axes` 与 figure 引用都被切断，所以删掉的 artist 不会拖住整张图的内存，这是"循环里反复建删元素"能扛住的原因。

### B1.8 dataLim / viewLim / autoscale 状态机

这三个名词的关系，主章只说了"autoscale 按数据自动定范围"。机制上有**两个 Bbox 和一个懒标记**：

| 名字 | 是什么 | 谁写 | 谁读 |
|------|--------|------|------|
| `dataLim` | 所有数据的包围盒（普通属性） | 每次 `plot`/`scatter`/`add_*` 时 `update_from_data_*` | `autoscale_view` |
| `_viewLim` | 当前显示范围（`Bbox`） | `autoscale_view` 或 `set_xlim` | transform（`transLimits` 的源） |
| `_stale_viewlims` | `{"x": bool, "y": bool}`，待兑现标记 | `_request_autoscale_view` | `_unstale_viewLim` |

关键是 **"读 viewLim 会消费懒标记"**——`viewLim` 是 property，getter 第一行就是 `self._unstale_viewLim()`：

```python
>>> fig, ax = plt.subplots(); ax.plot([0, 10], [0, 5])
>>> dict(ax._stale_viewlims), ax._viewLim.intervalx
({'x': True, 'y': True}, array([0., 1.]))     # 还没兑现：viewLim 仍是初始 [0,1]
>>> _ = ax.viewLim.intervalx                  # 读一次公开属性
>>> dict(ax._stale_viewlims), ax._viewLim.intervalx
({'x': False, 'y': False}, array([-0.5, 10.5]))  # 被这次读"顺便"算掉了
```

这解释了一个调试幻象：**用 `print(ax.viewLim)` 断点会改变状态机的时序**。真正的兑现点在 `Axes.draw` 的第一行（B1.1 ①），所以"不 draw 就不会重算"只在你不读 `viewLim` 时成立。

另外三条规则都值得记住：

```python
>>> ax.set_xlim(0, 20); ax.get_autoscalex_on()
False                                 # 显式设限 = 关掉该轴 autoscale
>>> ax.autoscale(enable=True, axis="x"); ax.get_autoscalex_on()
True                                  # 重新打开只标脏，不立刻算
>>> ax.plot([100, 200], [0, 0]); ax.dataLim.intervalx
array([  0., 200.])                   # dataLim 立刻扩张
>>> ax.set_xlim(0, 20); ax.relim(); ax.dataLim.intervalx
array([  0., 200.])                   # relim 是"重扫数据重建 dataLim"
```

- **共享轴一次算一族**：`_unstale_viewLim` 用 `_shared_axes[name].get_siblings(self)` 收集同组轴的标记，任一根脏就整组重算，保证 `sharex` 的轴永远同步。
- **`apply_aspect` 只改活动框**：`set_aspect("equal")` 后 `ax.get_position()` 会缩成 `[0.2558, 0.11, 0.5133, 0.77]`，而 `ax.get_position(original=True)` 仍是 `[0.125, 0.11, 0.775, 0.77]`——**布局框与可视框是两个 Bbox**，这也是 `tightbbox` 与 `bbox_inches="tight"` 结果的差异来源之一（B2.8）。

> **⚠️ 陷阱**：`ax.set_xlim` 之后**不要**再指望 `plot` 新数据会自动扩范围——autoscale 已被关掉（上面第一行）。反之，`autoscale(enable=True)` 之后 `dataLim` 仍是旧值，要 `relim()` 才会把先前被忽略的数据算进去。

### B1.9 图型容器的批量构造：`hist`、`boxplot`、`fill_between`

主章 3.7 要求记住每个方法返回什么容器。这里给"内部到底造了几个 Artist"的实测：

```python
>>> h = a.hist(np.random.default_rng(0).normal(size=1000), bins=20)
>>> type(h), len(h), type(h[2]).__name__
(tuple, 3, 'BarContainer')
>>> len(a.patches), type(a.patches[0]).__name__
(20, 'Rectangle')                 # 每个箱一个 Rectangle，不是 Collection
```

`hist` 返回 `(counts, bin_edges, BarContainer)`；`bins=20` 就是 **20 个独立的 `Rectangle` patch**，所以箱数一多，`ax.patches` 会长得很快（B6.2 的 Artist 数量杠杆）。

```python
>>> b = a.boxplot(np.random.default_rng(0).normal(size=(100, 3)))
>>> {k: type(v[0]).__name__ if v else "<空>" for k, v in sorted(b.items())}
{'boxes': 'Line2D', 'caps': 'Line2D', 'fliers': 'Line2D',
 'means': '<空>', 'medians': 'Line2D', 'whiskers': 'Line2D'}
```

两个反直觉点：**箱体是 `Line2D`（四条线组成的矩形）而不是 `Patch`**；`means` 默认是空列表（`showmeans=False`），按位置取值前必须判空。箱线图一个箱子 = 6 个以上 `Line2D`，这是它比 `violinplot` 更"重"的原因。

```python
>>> type(a.fill_between([0,1,2], [0,1,0], [1,2,1])).__name__
'FillBetweenPolyCollection'
>>> [type(x).__name__ for x in a.stackplot([0,1,2], [1,2,3], [1,1,1])]
['FillBetweenPolyCollection']
>>> len(a.collections), len(a.patches)
(2, 0)
```

`fill_between` 与 `stackplot` 都归到 `FillBetweenPolyCollection`（`PolyCollection` 的子类，**一个对象装下整片多边形**）——所以它们在 `ax.collections` 里，不在 `ax.patches` 里。这正是"同样的视觉，Artist 数量差一个数量级"的实例：**用集合类图型（fill/collection/scatter）代替逐个 patch，是 3.14 性能那一节最直接的落地。**

> **延伸阅读**：`hist` 的批量 patch 构造与 `BarContainer` 见 `matplotlib/axes/_axes.py`；`FillBetweenPolyCollection` 的路径拼装见 `matplotlib/collections.py`；`bxp` 的各部件装配见 `matplotlib/axes/_axes.py` 的 `boxplot`/`bxp`。

### B1.10 rcParams 的校验器与样式表分层

`rcParams` 不是一个普通字典，它有 339 个键、每个键配一个校验/转换器，**赋值即校验**：

```python
>>> import matplotlib as mpl
>>> type(mpl.rcParams).__name__, len(mpl.rcParams)
('RcParams', 339)
>>> mpl.rcParams["font.size"] = "big"
ValueError: Key font.size: Could not convert 'big' to float
>>> mpl.rcParams["no.such.key"] = 1
KeyError: "'no.such.key' is not a valid value for rcParam."
```

两个报错类型不同不是笔误：**值非法抛 `ValueError`（消息带出校验器名），键不存在抛 `KeyError`**。校验器表在 `matplotlib.rcsetup._validators`（私有，仅取证），公开可见的是 `rcsetup.validate_*` 一族函数。

样式表的分层规则只有一句：**`style.use` 只覆盖样式文件里出现过的键，其余键保持原值；后加载的样式覆盖先加载的。**

```python
>>> mpl.rcParams["savefig.transparent"] = True
>>> mpl.rcParams["font.size"] = 17
>>> mpl.style.use("ggplot")
>>> mpl.rcParams["savefig.transparent"]        # ggplot 没有这个键
True
>>> mpl.rcParams["font.size"]                   # ggplot 里有 font.size: 10
10.0
>>> mpl.style.use(["ggplot", "dark_background"])
>>> mpl.rcParams["figure.facecolor"]
'black'                                          # 后者赢
```

而 `style.context(...)` 是**成对保存/还原**的，适合给单张图临时换皮：

```python
>>> with mpl.style.context("ggplot"):
...     mpl.rcParams["axes.facecolor"] = "pink"   # 运行期覆盖样式
...     print(mpl.rcParams["axes.facecolor"])
pink
>>> mpl.rcParams["axes.facecolor"]                # 退出即还原
'white'
```

> **⚠️ 陷阱**：`style.use("default")` 会把样式层恢复成默认，但**不会**撤销你通过 `rcParams[...] = ...` 设过的值（它只覆盖 default 样式里定义的键）。要"彻底回厂"，得配合保存一份 `rcParams.copy()` 或 `rcParamsDefault`。团队统一样式的正解是**写 `.mplstyle` 文件 + 在入口处 `style.use(path)`**，而不是散落的 `rcParams` 赋值（回链主章 3.11）。

> **机制洞察**：把 B1 收成一句话——**matplotlib 的运行时是一个"脏标记 + 全量重绘"的系统，数据范围、布局、元素顺序全部推迟到 `draw` 的固定顺序里兑现**。所以排查顺序永远是：先确认 draw 真的发生了（B1.2/B1.5），再看数据范围算对没有（B1.8），再看坐标变换给对没有（B2），最后才怀疑渲染器。

> **延伸阅读**：`RcParams` 与校验器见 `matplotlib/rcsetup.py`；样式表的解析与上下文见 `matplotlib/style/core.py`；figure 注册表见 `matplotlib/_pylab_helpers.py`。

---

## B2 transform 复合数学与布局求解

主章 3.5 给了四套坐标的用途，B2 给它们的**复合顺序、矩阵形式与惰性**。一句可以背的话：**变换不是"把点搬过去"，而是"把坐标系逐层套起来"，每一层只做一件最简单的事。**

### B2.1 四段链的括号：谁套着谁

```python
>>> fig = plt.figure(figsize=(6.4, 4.8), dpi=100)
>>> ax = fig.add_axes([0.125, 0.11, 0.775, 0.77])
>>> ax.set_xlim(0, 10); ax.set_ylim(0, 100)
>>> ax.transData == ax.transScale + (ax.transLimits + ax.transAxes)
True
>>> ax.transData == (ax.transScale + ax.transLimits) + ax.transAxes
False
```

复合有**结合律但没有交换律**，而 matplotlib 选定的括号是 `transScale + (transLimits + transAxes)`。写成公式：

$$\text{transData} = \text{transScale} \circ (\text{transLimits} \circ \text{transAxes})$$

其中每一层的职责严丝合缝：

| 层 | 输入 → 输出 | 做什么 | 线性轴上的实现 |
|----|------------|--------|---------------|
| `transScale` | 数据 → "线性化数据" | 非线性标度的唯一入口 | `TransformWrapper(BlendedAffine2D(Identity, Identity))`，恒等 |
| `transLimits` | 线性化数据 → 轴分数 | 平移 + 缩放，把 `dataLim` 映射到 `[0,1]²` | `BboxTransformFrom`，一个仿射矩阵 |
| `transAxes` | 轴分数 → 显示像素 | 把 `[0,1]²` 映射到轴在画布上的矩形 | `BboxTransformTo`，一个仿射矩阵 |

矩阵形式直接可见：

```python
>>> np.round(ax.transLimits.get_matrix(), 6)
array([[ 0.1 ,  0.  , -0.  ],
       [ 0.  ,  0.01, -0.  ],
       [ 0.  ,  0.  ,  1.  ]])
```

`xlim=(0,10)` 配合 `ylim=(0,100)`，矩阵对角线正好是 `1/10` 与 `1/100`——**`transLimits` 就是"缩放 + 平移"的 3×3 仿射矩阵**，别被类名骗了。

### B2.2 四套坐标的输入域：喂错就外推

```python
>>> ax.transAxes.transform((0, 0)), ax.transAxes.transform((1, 1))
(array([ 80. ,  52.8]), array([576. , 422.4]))
>>> fig.transFigure.transform((0, 0)), fig.transFigure.transform((1, 1))
(array([0., 0.]), array([640., 480.]))
>>> ax.transData.transform((5, 50))
array([328. , 237.6])
>>> ax.transAxes.transform((5, 50))          # 把 data 喂给 axes 变换
array([ 2560. , 18532.8])                    # 外推，不是报错
```

三件事一起看：

1. **`transAxes` 的合法输入是 `[0,1]`**，`(0,0)` 是轴框左下角（显示坐标 `(80, 52.8)`，正是 `add_axes` 的左/下边距），`(1,1)` 是右上角；
2. **`fig.transFigure` 挂在 `Figure` 上，`Axes` 没有 `transFigure` 属性**（`hasattr(ax, "transFigure")` 为 `False`）。子图内想让元素对齐整张画布，写成 `fig.transFigure`；
3. **喂错坐标系不报错，只会外推**——所以"元素跑到天边"几乎总是 transform 选错而非数据错。主章 3.5 的那条纪律（先查 `transform=`）就建立在这个性质上。

反解用 `.inverted()`，它同样是惰性的：

```python
>>> np.round(ax.transData.inverted().transform((400, 300)), 4)
array([ 6.4516, 66.8831])
```

### B2.3 对数轴：换的是 `transScale` 的 `_child`

```python
>>> fig2, ax2 = plt.subplots(); ax2.set_yscale("log"); ax2.set_ylim(1, 1000)
>>> ax2.transScale                     # 仅取证：一层包装 + 逐轴混合
TransformWrapper(
    BlendedGenericTransform(
        IdentityTransform(),
        LogTransform(base=10, nonpositive='clip')))
>>> ax2.transScale.transform([[0,1.],[0,10.],[0,1000.]]).ravel()[1::2]
array([0., 1., 3.])                    # 1 -> 0, 10 -> 1, 1000 -> 3（log10）
```

所以 `y=10` 明确落在轴的 **1/3** 处（而不是线性轴上的 `10/1000`）：

```python
>>> (ax2.transScale + ax2.transLimits).transform([[0, 10.0]])
array([[0.        , 0.333333]])
```

**为什么 `transScale` 要包一层 `TransformWrapper`**——因为 setter 只换内胆，不重建对象：

```python
>>> td, ts = ax2.transData, ax2.transScale
>>> ax2.set_yscale("linear")
>>> ax2.transData is td, ax2.transScale is ts, type(ts._child).__name__
(True, True, 'BlendedAffine2D')       # id 不变，只换了 _child
```

这是 transform 设计的核心权衡：**艺术家在创建时就持有 `transData` 的引用**，如果换标度要重建整条链，所有已存在的 artist 都得更新引用；把可变部分塞进 wrapper，换标度就退化成"改一个属性"。同一机制也支撑了 `sharex` 的同步（共享的是轴对象与 limits）。

> **⚠️ 陷阱**：`LogTransform` 的 `nonpositive="clip"` 意味着 **log 轴上的 0 与负值被静默裁剪**，而不是报错。数据里混了 0 时，`set_yscale("log")` 后那一点直接消失——排查顺序是"先看数据有没有 ≤0，再看 transform"。

### B2.4 单位偏移：`ScaledTranslation`

想在数据坐标上做"固定 10 pt 的偏移"（标注错位、抖动点、偏移文本），必须引入一个**以英寸/点为单位的仿射**，再与 `transData` 复合：

```python
>>> from matplotlib.transforms import ScaledTranslation
>>> off = ax.transData + ScaledTranslation(10/72, 0, fig.dpi_scale_trans)
>>> np.asarray(off.transform((5, 50))) - np.asarray(ax.transData.transform((5, 50)))
array([13.8889,  0.    ])
>>> 10/72*100                                  # 10 pt @ 100 dpi
13.88888888888889
>>> np.round(fig.dpi_scale_trans.get_matrix(), 6)
array([[100.,   0.,   0.],
       [  0., 100.,   0.],
       [  0.,   0.,   1.]])
```

`dpi_scale_trans` 的矩阵就是 `dpi` 本身——**"点/英寸"到"像素"的汇率只有这一个来源**。所有"随图尺寸缩放而保持物理大小"的元素（线宽、字号、偏移标注）都通过它换算；这也是同一张图改 `dpi` 时线宽不变、图片变大的原因。

### B2.5 惰性：矩阵每次现算

```python
>>> ax.set_xlim(0, 10); ax.transData.get_matrix()[0]
array([49.6,  0. , 80. ])
>>> ax.set_xlim(0, 20); ax.transData.get_matrix()[0]
array([24.8,  0. , 80. ])
```

`CompositeGenericTransform` 不在构造时缓存矩阵，`get_matrix()` 每次都从子变换现取。好处是**一致**（改 limits 不需要通知任何人），代价是**热路径上别反复调 `transform()`**——一张 10 万点的散点若逐点调 `transData.transform` 而不是整块数组，多出来的是 Python 层循环，这正是主章 3.5 末尾"坐标变换也是性能路径"的机制解释。

### B2.6 布局求解的时机：`GridSpec` → `SubplotParams`

布局参数的解析有一条**两级回退链**：`GridSpec` 上显式给了就用，没给就落回 `fig.subplotpars`（而 `subplotpars` 的初值来自 `rcParams["figure.subplot.*"]`）。

```python
>>> f2, axs = plt.subplots(2, 2, figsize=(6, 4))
>>> gs = axs[0,0].get_gridspec(); gs.wspace is None
True                                  # GridSpec 没给 -> 走 subplotpars
>>> f2.subplotpars.left, f2.subplotpars.right, f2.subplotpars.wspace
(0.125, 0.9, 0.2)
>>> b, t, l, r = gs.get_grid_positions(f2)   # 返回 (bottoms, tops, lefts, rights)
>>> np.round(b, 4), np.round(t, 4)
(array([0.53, 0.11]), array([0.88, 0.46]))
>>> np.round(l, 4), np.round(r, 4)
(array([0.125 , 0.5477]), array([0.4773, 0.9   ]))
```

单元框由这四条边界直接相减得到：`cell(0,0) = [0.125, 0.53, 0.3523, 0.35]`。间距公式也正是一个"比例定义"：

```python
>>> round(f2.subplotpars.wspace * axs[0,0].get_position().width, 4)
0.0705
>>> round(axs[0,1].get_position().x0 - axs[0,0].get_position().x1, 4)
0.0705                                # wspace 是"格宽的倍数"，不是绝对像素
```

所以 `wspace=0.2` 的真实含义是**列间距 = 单格宽的 20%**——图越窄，缝越窄。`subplots_adjust(wspace=0.6)` 只是改 `subplotpars`，单元宽度从 `0.3523` 收到 `0.2981`（解算发生在下一次 draw）。

### B2.7 `constrained` / `tight`：一套可调用的求解器

```python
>>> f3, axs3 = plt.subplots(2, 2, layout="constrained", figsize=(6, 4))
>>> eng = f3.get_layout_engine()
>>> type(eng).__name__, eng.get()
('ConstrainedLayoutEngine',
 {'h_pad': 0.04167, 'w_pad': 0.04167, 'hspace': 0.02, 'wspace': 0.02, 'rect': (0, 0, 1, 1)})
>>> before = np.round(axs3[0,0].get_position().bounds, 4); eng.execute(f3)
>>> before, np.round(axs3[0,0].get_position().bounds, 4)
(array([0.125 , 0.53  , 0.3523, 0.35  ]),
 array([0.0598, 0.5694, 0.4149, 0.4069]))   # 引擎重算了整个网格
>>> eng.set(wspace=0.5, hspace=0.5); eng.execute(f3)
>>> np.round(axs3[0,0].get_position().bounds, 4)
array([0.0748, 0.684 , 0.2744, 0.2924])
```

要点有三：

1. **引擎是可执行对象**（`get` / `set` / `execute`），`Figure.draw` 每次都会调 `execute`——所以布局不是"设一次就固定"，而是**每次绘制都重新求解**（B1.1 ②）;
2. `layout="tight"` 换成 `TightLayoutEngine`，`layout=None` 则是 `None`，此时 `subplots_adjust` 的静态参数说了算；
3. `constrained` 的 `hspace/wspace` 是**分数**（默认 0.02），语义与 `subplotpars` 的 `0.2` 完全不同——两套参数不要互相抄。改完 `set()` 之后必须触发一次 draw（或手动 `execute`）才看得到。

### B2.8 `apply_aspect`：活动框 vs 原始框

```python
>>> ax.set_aspect("equal"); fig.canvas.draw()
>>> ax.get_position().bounds
array([0.2558, 0.11  , 0.5133, 0.77  ])     # 活动框被收缩
>>> ax.get_position(original=True).bounds
array([0.125 , 0.11  , 0.775 , 0.77  ])     # 原始框不变
```

`apply_aspect` 在 `Figure._get_draw_artists` 里对每根轴调用一次（B1.1 ①）。**它只改活动框，不改原始框**——这就是 `tightbbox`、`bbox_inches="tight"`、`colorbar` 自动留白三者的共同基础：所有"按内容重新排布"的工具读的都是活动框。想恢复就 `set_aspect("auto")` 再 draw。

### B2.9 共享轴：`Grouper` 用弱引用组队

```python
>>> f4, axs4 = plt.subplots(1, 2, sharey=True)
>>> grp = axs4[0]._shared_axes["y"]              # 仅取证
>>> type(grp).__name__, grp.get_siblings(axs4[0]) == grp.get_siblings(axs4[1])
('Grouper', True)
>>> type(grp._mapping).__name__                   # 只读结构
'WeakKeyDictionary'
>>> axs4[1].remove(); len(grp.get_siblings(axs4[0]))
1                                                  # 轴一删，自动退出该组
```

`_shared_axes` 在 3.11 是一个普通 `dict`（键为 `"x"/"y"`），值 `Grouper` 内部是 **`WeakKeyDictionary[str, set[weakref]]`**。两个设计后果：**共享关系随轴的生命周期自动清理**（删轴不用手动退组，也就不会泄漏 figure），**共享是按"轴"而不是按"figure"**——同一张图里可以有 `sharey` 的两根轴和另一根独立轴并存。

> **机制洞察**：B2 的统一图景是 **"一切定位 = 若干层简单仿射的复合，且每层都可替换、可惰性求值"**。`transScale` 的 wrapper 让标度可换，`transLimits` 让数据范围可换，`transAxes` 让布局可换，`apply_aspect` 让长宽比可换，布局引擎让网格可换——你看到的"元素位置不对"，一定是这五层里**某一层的输入域给错了**。

> **延伸阅读**：`matplotlib/transforms.py`（`CompositeGenericTransform`、`TransformWrapper`、`BboxTransformFrom/To`、`ScaledTranslation`）；布局见 `matplotlib/_layoutgrid.py`、`matplotlib/gridspec.py`、`matplotlib/figure.py` 的 `SubplotParams`；共享轴 `Grouper` 见 `matplotlib/cbook.py`。

---

## B3 单位机器：坐标轴如何"看懂"数据

主章 3.6.1 说"类别轴会自动等距排布"，3.10.1 说"日期轴自动转 display"，3.13 说"pandas 的 Period 走自己的定位器"。三处背后是同一台机器：**units registry + 三方法接口**。B3 把它拆开。

### B3.1 注册表里到底有什么

```python
>>> import matplotlib.units as munits
>>> len(munits.registry)                      # 只导入 units 本体
1
>>> import matplotlib.dates                   # 日期模块在被导入时自注册
>>> len(munits.registry)
4
>>> import matplotlib.category                # 分类模块同理
>>> len(munits.registry)
8
>>> for k, v in munits.registry.items():
...     print(f"{getattr(k,'__name__',k):<12} -> {type(v).__name__}")
Decimal      -> DecimalConverter
datetime64   -> _SwitchableDateConverter
date         -> _SwitchableDateConverter
datetime     -> _SwitchableDateConverter
str          -> StrCategoryConverter
str_         -> StrCategoryConverter
bytes        -> StrCategoryConverter
bytes_       -> StrCategoryConverter
```

**注册表不是一张静态表，而是"随模块加载增长"的**：`units.py` 本体只带 `Decimal`，`matplotlib.dates` 在被导入时注册 datetime 三兄弟，`matplotlib.category` 注册四种字符串/字节类型；`pyplot` 会把这两个模块都拉进来，所以日常看到的就是这 8 条。**8 个条目覆盖了日常 95% 的非数值数据**：`Decimal`、四种字符串类型（`str` 与 NumPy 的 `str_`）、两种 `bytes`、以及 `datetime`/`date`/`np.datetime64` 共用一个 `_SwitchableDateConverter`。后者是较新的设计——**一个转换器在运行期按实际数据切换 datetime 与 date 两套内核**，避免了历史上"先画 date 再画 datetime 就崩"的问题。

### B3.2 轴上有两个槽位：`_converter` 与 `units`

这是理解整台机器的钥匙。`Axis` 存两样东西：

| 槽位 | 类型 | 日期轴上的值 | 分类轴上的值 |
|------|------|-------------|-------------|
| `_converter` | 转换器实例 | `_SwitchableDateConverter` | `StrCategoryConverter` |
| `units` | 转换器自定的"单位标签" | `None` | `UnitData` 实例 |

```python
>>> fig, ax = plt.subplots()
>>> ax.plot([dt.date(2026,1,1), dt.date(2026,2,1)], [1, 2])
>>> ax.xaxis.get_units(), type(ax.xaxis._converter).__name__, ax.xaxis.have_units()
(None, '_SwitchableDateConverter', True)      # units 是 None，但仍然"有单位"
>>> ax.xaxis.convert_units(dt.date(2026, 1, 1))
20454.0                                       # 1970-01-01 起的天数（float）
```

所以 `get_units() is None` **不代表没有单位机器在工作**——日期轴不需要"类别表"，它的单位概念被折叠进了 `_converter`。判断该看 `have_units()`（`_converter is not None or units is not None`）。

### B3.3 日期轴为什么自动：`axisinfo` 是"配置供应商"

`Axis.convert_units(x)` 的流程是：`_is_natively_supported(x)`？否 → 取 `_converter` → `converter.convert(x, self.units, self)` → 得到 float。**转换只做了数值化**，那 `AutoDateLocator`/`AutoDateFormatter` 是哪来的？来自 `_update_axisinfo`：

```python
>>> type(ax.xaxis.get_major_locator()).__name__
'AutoDateLocator'
>>> type(ax.xaxis.get_major_formatter()).__name__
'AutoDateFormatter'
>>> ax.xaxis._converter.axisinfo(ax.xaxis.get_units(), ax.xaxis).majloc
AutoDateLocator()                             # 转换器"供应"的配置
```

`ConversionInterface` 的三方法契约由此完整：

| 方法 | 签名 | 职责 |
|------|------|------|
| `convert` | `(value, unit, axis) -> float/array` | **数值化**：把你类型变成 float 数组 |
| `axisinfo` | `(unit, axis) -> AxisInfo \| None` | **供配置**：给默认的 locator/formatter/label/limits |
| `default_units` | `(data, axis) -> unit` | **定单位**：从数据推出 `units` 槽位放什么 |

三者分工清楚：`convert` 管"每条数据"，`axisinfo` 管"整根轴"。

### B3.4 自定义类型接入：20 行换一个"直接能画"的类型

```python
>>> import matplotlib.units as munits
>>> class Deg:
...     def __init__(self, deg): self.deg = deg
>>> class DegConverter(munits.ConversionInterface):
...     @staticmethod
...     def convert(value, unit, axis):
...         return value.deg if isinstance(value, Deg) else [v.deg for v in value]
...     @staticmethod
...     def axisinfo(unit, axis):
...         return munits.AxisInfo(label="角度 (°)", majloc=plt.MultipleLocator(90))
...     @staticmethod
...     def default_units(x, axis):
...         return None
>>> munits.registry[Deg] = DegConverter()
>>> f, a = plt.subplots(); a.plot([Deg(0), Deg(180), Deg(360)], [0, 1, 0], marker="o")
>>> a.dataLim.intervalx, a.get_xlabel(), type(a.xaxis.get_major_locator()).__name__
(array([  0., 360.]), '角度 (°)', 'MultipleLocator')
```

**注册即生效**：不需要碰 `Axes`、不需要子类化任何绘图方法，`dataLim`、坐标标签、刻度定位器全部按 `axisinfo` 的声明自动配置。这是 matplotlib 给领域类型（经纬度、货币、分数、时间码）留的正规接口。用完记得 `del munits.registry[Deg]`，注册表是**全局可变状态**。

### B3.5 分类轴：`UnitData` 就是一张会增长的表

```python
>>> f, a = plt.subplots(); a.bar(["apple", "banana", "cherry"], [3, 1, 2])
>>> ud = a.xaxis.get_units()
>>> type(ud).__name__, dict(ud._mapping)
('UnitData', {'apple': 0, 'banana': 1, 'cherry': 2})
>>> type(a.xaxis.get_major_locator()).__name__, type(a.xaxis.get_major_formatter()).__name__
('StrCategoryLocator', 'StrCategoryFormatter')
```

`UnitData` = `OrderedDict` + `itertools.count`（仅取证）：字符串按**首次出现顺序**编号 0,1,2,…，`convert` 时**顺带 `unit.update(values)`**，所以新类别会自动追加到表尾，老类别的编号永不改变——这把"类别顺序稳定"做成了结构保证，也是主章 3.6.1"类别轴等距"的实现：轴上的位置就是序号。

```python
>>> a.bar(["durian"], [5])
>>> dict(a.xaxis.get_units()._mapping)
{'apple': 0, 'banana': 1, 'cherry': 2, 'durian': 3}   # 追加，不重排
```

### B3.6 三个静默错误：字符串与数字的边界

这是本章最值得抄进 checklist 的一段。**分类与数值混用不会报错，只会画错。**

**错误一：数字字符串被当成类别**（绘制仍成功，尺度完全变了）：

```python
>>> a.plot(["1", "2", "3"], [1, 2, 3])
>>> dict(a.xaxis.get_units()._mapping)
{'1': 0, '2': 1, '3': 2}
# 标准日志（INFO 级）里其实说了：
# Using categorical units to plot a list of strings that are all parsable
# as floats or dates. If these strings should be plotted as numbers, cast
# to the appropriate data type before plotting.
```

`UnitData._str_is_convertible` 会试着把每个字符串 `float()`、`dateutil.parse()` 一遍：**能转也照样建类别表**，只在 `matplotlib.category` 这个 logger 上打一条 INFO。默认日志级别看不到它——**读 CSV 得到的字符串列要显式 `astype(float)` 或 `parse_dates`，不能指望 matplotlib 帮你转**（回链主章 3.13 的 pandas 桥接）。

**错误二：数值混进类别轴是静默外推**（新数据落在两个类别之间）：

```python
>>> a.plot([1.5], [1.0], marker="o")     # 轴已经是类别轴
>>> a.dataLim.intervalx
array([0., 2.])                          # 1.5 既不是类别也不是错误，只是被当浮点传了进去
```

**错误三：先数值后字符串会把已有的数据整体错位**：

```python
>>> f2, a2 = plt.subplots()
>>> a2.plot([1.0, 2.0], [1, 1])          # 数值轴
>>> a2.plot(["a"], [2])                  # 中途变类别轴
>>> type(a2.xaxis.get_units()).__name__
'UnitData'                                # 前一条线仍是 1.0、2.0，新点却是 0
```

> **⚠️ 陷阱**：判断一根轴到底是数值还是类别，看 `type(ax.xaxis.get_units()).__name__`，不要看数据长相。**统一数据类型的动作要在绘图之前完成**（`pd.to_numeric` / `astype(float)` / `pd.to_datetime`），这与主章 3.15"静默错误清单"是同一条纪律在单位层的投影。

### B3.7 Locator 与 Formatter：一个管位置，一个管文字

```python
>>> from matplotlib.ticker import MultipleLocator, FuncFormatter, Locator
>>> MultipleLocator(5).tick_values(-3, 22)
array([-5.,  0.,  5., 10., 15., 20., 25.])
>>> class OnlyTens(MultipleLocator):
...     def tick_values(self, vmin, vmax):
...         return np.array([v for v in super().tick_values(vmin, vmax) if v % 10 == 0])
>>> a.xaxis.set_major_locator(OnlyTens(5))
>>> a.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: "%g kg" % x))
>>> fig.canvas.draw(); a.get_xticks(), [t.get_text() for t in a.get_xticklabels()]
(array([ 0., 10., 20.]), ['0 kg', '10 kg', '20 kg'])
```

**契约只有一条**：`Locator` 负责"在这些数据坐标上打刻度"（`tick_values(vmin, vmax) -> 数组`），`Formatter` 负责"这个坐标显示成什么字符串"。自定义时**不要重写 `__call__`**，重写 `tick_values` 即可——matplotlib 会在 `__call__` 里处理范围外扩、`nonsingular`、视图限制等公共逻辑。这也是主章练习 16 的设计意图。

### B3.8 排序与单位在 draw 里的汇合点

回到 B1.1 的流水线：`convert_units` 发生在**设置数据的那一刻**（`update_units` → `dataLim` 更新），而 `sorted(..., key=zorder)` 发生在 **draw 的那一刻**（确切位置见 B1.3：`Figure._get_draw_artists` 与 `Axes.draw` 两处）。两者不重叠——**单位决定"点在哪"，zorder 决定"谁盖谁"**，一个在数据层、一个在渲染层。理解了这条分界，主章 3.6 的三条坑（类别轴等距、`c=` 语义、zorder）就能各自归因。

### B3.9 第三方怎么接进这台机器：pandas 的"临时换表"

pandas 的绘图栈要处理 `Period`、`datetime64`、带时区的 `DatetimeIndex`，它用的正是 B3.2/B3.3 那套接口——但**不是常驻注册**，而是"进 plot 换表、出 plot 还原"：

```python
# pandas/plotting/_matplotlib/converter.py（仅取证，结构示意）
def register_pandas_matplotlib_converters(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _mpl_units_registry_context():   # 进入：把 pandas 的转换器写进 registry
            return func(*args, **kwargs)      # 退出：还原 matplotlib 原本的条目
    return wrapper
```

这条"进出"可以直接观测：

```python
>>> import pandas as pd
>>> s = pd.Series([1, 2, 3], index=pd.period_range("2026-01", periods=3, freq="M"))
>>> ax = s.plot()
>>> type(ax.xaxis._converter).__name__                  # 轴"记住"了 pandas 的转换器
'PeriodConverter'
>>> type(munits.registry[datetime.datetime]).__name__   # 全局注册表已经还原
'_SwitchableDateConverter'
>>> len(munits.registry)                                # 条数也没变
8
```

两点结论：

1. **转换器是装在轴上的，不是装在注册表上的**。注册表只负责"绘图那一刻怎么把数据变成 float"，画完就不管了；轴上的 `_converter` 才是持久状态（B3.2）。所以一根轴一旦建好，它的坐标语义就固定了。
2. **`contextmanager` 临时改全局状态，是跨库桥接的标准手法**（源码里逐条 `previous = registry[type_]` / 退出时还原）。它保证 pandas 与 matplotlib 的日期处理不打架，代价是**跨库混用时语义随调用顺序变化**：同一根轴上先 `df.plot()`、再 `ax.plot(datetime)`，两者可能落在不同的转换器路径上——这正是主章 3.13"两级 API 桥接"最容易出问题的地方。

seaborn 走的是另一条路（文献）：它**完全不碰单位机器**，`FacetGrid` 的做法是"先按分面变量建一张 Axes 网格（`fig.subplots` 的循环版），再把每个子集的数据投到对应 Axes"，最后交回 matplotlib 的 `Axes` 数组。 **"不扩展底层协议，只组合现有对象"** 正是 seaborn 可以随时被 `ax` 层接管的原因（主章 3.13）。

> **机制洞察**：单位机器是 matplotlib 官方留出的**唯一一个"不改核心就能支持新数据类型"的扩展点**（B3.4 的 20 行接入就是证明）。它把"数据类型 → 浮点坐标 + 轴配置"做成一张可扩展的注册表，于是 `Axes` 永远只面对 float，而扩展点留给第三方。pandas 用它做"临时替换"、seaborn 干脆不用——两条路线都成立，区别只在**谁承担状态一致性**：前者把责任压在 `contextmanager` 的进出上，后者把责任压在"每张图自己重建"上。

> **延伸阅读**：`matplotlib/units.py`（`ConversionInterface`/`AxisInfo`/`Registry`）；分类见 `matplotlib/category.py`；日期见 `matplotlib/dates.py` 的 `_SwitchableDateConverter` 与 `AutoDateLocator`；pandas 侧见 `pandas/plotting/_matplotlib/converter.py` 的 `register_pandas_matplotlib_converters` 与 `PeriodConverter`；seaborn 的分面实现见 `seaborn/axisgrid.py` 的 `FacetGrid`（本环境未安装 seaborn，为源码结构说明、非实测）。

---

## B4 后端与嵌入：从 Figure 到像素与文件

主章 3.12 的结论是"矢量给出版、位图给预览、无头进 CI"。B4 讲这三句背后的对象模型与**产物可复现性**——后者是论文与 CI 里最容易被忽略、也最容易踩的一环。

### B4.1 后端是一张注册表，不是一串硬编码

```python
>>> from matplotlib.backends import registry as breg
>>> type(breg.backend_registry).__name__
'BackendRegistry'
>>> len(breg.backend_registry.list_builtin()), breg.backend_registry.list_builtin()[:6]
(24, ['gtk3agg', 'gtk3cairo', 'gtk4agg', 'gtk4cairo', 'macosx', 'nbagg'])
>>> breg.backend_registry.list_gui_frameworks()
['gtk3', 'gtk4', 'macosx', 'qt', 'qt5', 'qt6', 'tk', 'wx']
>>> mpl.rcsetup.interactive_bk
AttributeError: module 'matplotlib.rcsetup' has no attribute 'interactive_bk
```

**24 个内置后端、8 个 GUI 框架**，全部由 `BackendRegistry` 按名字解析；3.9 之后旧的 `rcsetup.interactive_bk` 一类属性已删除（主章"版本注意④"）。这带来一个实用好处：`rcParams["backend"]` 可以写 `"module://my.backend"` 形式，**注册表是第三方后端的正规入口**。

### B4.2 没有 GUI 时 `plt.show()` 会怎样

```python
>>> fig, ax = plt.subplots(); ax.plot([0,1],[0,1])
>>> plt.show()
UserWarning: FigureCanvasAgg is non-interactive, and thus cannot be shown
```

它**不报错、不阻塞**，只发一条 `UserWarning`。所以 CI 里出现这句警告说明"你在无头环境调了 `show()`"——正确的做法是直接 `savefig`（主章 3.12）。反过来说，**Agg 完全能画**：`canvas.draw()` 拿像素、`print_png` 出文件，交互后端只是多了窗口与事件循环。

### B4.3 `buffer_rgba()` 是零拷贝可写视图（不是拷贝）

```python
>>> fig.canvas.draw()
>>> buf = fig.canvas.buffer_rgba()
>>> type(buf).__name__, buf.readonly
('memoryview', False)
>>> arr = np.asarray(buf); arr.shape, arr.dtype
((480, 640, 4), dtype('uint8'))
>>> arr[0, 0] = [1, 2, 3, 255]
>>> np.asarray(fig.canvas.buffer_rgba())[0, 0]
array([  1,   2,   3, 255], dtype=uint8)   # 写穿了同一块缓冲
>>> np.shares_memory(arr, np.asarray(fig.canvas.buffer_rgba()))
True
```

三个必须知道的点：

1. **返回 `memoryview`（3.10+ 的变更）**，不是 ndarray。想要数组语义自己 `np.asarray(...)`，这一步**零拷贝**（实测 < 0.001 ms）；
2. **它指向画布内部缓冲，可写**。写进去等于改画布；下一次 `draw()` 会把它覆盖掉；
3. **不要长期持有**。正确姿势是"`draw()` 后立刻 `np.array(buf)` 拷一份"再送去下游（PIL、OpenCV、FFmpeg、HTTP 响应）。

```python
# 安全用法：显式拷贝，与画布生命周期解耦
fig.canvas.draw()
frame = np.asarray(fig.canvas.buffer_rgba()).copy()
```

### B4.4 格式矩阵：同一张图的体量与耗时

一张 640×480、带图例的折线图，各格式实测（本机，取最小值）：

| 格式 | 字节数 | 耗时 | 类型 | 适用 |
|------|--------|------|------|------|
| `png` | 24 301 | 21.1 ms | 位图 | 预览、网页、CI 快照 |
| `webp` | 7 112 | 98.1 ms | 位图 | 网页（体量最小，编码最贵） |
| `jpg` | 17 695 | 15.4 ms | 位图 | 照片类，线条有振铃 |
| `tif` | 1 229 006 | 15.5 ms | 位图 | 印刷/无损交换 |
| `raw` / `rgba` | 1 228 800 | ~14 ms | 裸缓冲 | 交给别的程序（= 640×480×4） |
| `svg` | 16 376 | 16.7 ms | 矢量 | 网页、可编辑图元 |
| `pdf` | 5 272 | 311.0 ms | 矢量 | 论文、印刷（时间花在字体子集化） |
| `eps` / `ps` | ~11 300 | 13–20 ms | 矢量 | 老排版链，**不支持透明** |

两点值得注意：**`raw`/`rgba` 的大小恰好是 `宽×高×4`**——位图格式的"信息量下界"就是这个数，PNG 能压到 2% 是因为大片同色；**`pdf` 明显比 `svg` 慢**（311 ms vs 17 ms），因为它要做字体子集与流压缩，但产物通常更小更规范。

### B4.5 产物可复现性：PNG 稳，矢量默认不稳

做 CI 快照或论文版本控制时，"同一份代码出同一份文件"是硬需求。实测（两次保存间隔 1.2 秒）：

| 格式 | 默认是否逐字节可复现 | 差异来自 | 钉死办法 |
|------|-------------------|---------|---------|
| `png` | ✅ 稳定 | 无时间戳 | 无需处理 |
| `pdf` / `eps` | ❌ 不稳定 | `/CreationDate (D:20261007124425+08'00')` | `SOURCE_DATE_EPOCH` |
| `svg` | ❌ 不稳定 | `<dc:date>` + **元素 id 随机** | `SOURCE_DATE_EPOCH` + `svg.hashsalt` |

```python
>>> os.environ["SOURCE_DATE_EPOCH"] = "1700000000"
>>> save("pdf") == save("pdf")           # 间隔 1.2 s
True                                      # CreationDate -> D:20231114221320Z
>>> import re
>>> re.search(rb"/CreationDate \(([^)]*)\)", save("pdf")).group(1)
b'D:20231114221320Z'
>>> mpl.rcParams["svg.hashsalt"] = "cookbook"
>>> save("svg") == save("svg")
True
```

SVG 的差异不在时间戳（那个 `SOURCE_DATE_EPOCH` 就能治），而在**元素 id**。机制在 `backend_svg.py` 的 `_make_id`（仅取证）：

```python
def _make_id(self, type, content):
    salt = mpl.rcParams["svg.hashsalt"]
    if salt is None:
        salt = str(uuid.uuid4())          # 没设盐 -> 每次都换 uuid
    m = hashlib.sha256()
    m.update(salt.encode("utf8"))
    m.update(str(content).encode("utf8"))
    return f"{type}{m.hexdigest()[:10]}"
```

所以 SVG 里 `<path id="m47cb76b092">` 的哈希每次保存都不同，`<use>` 引用随之全变——**逐字节 diff 两份 SVG 必然满屏噪声**。

> **⚠️ 陷阱**：**别用字节 diff 校验图形产物**。SVG/PDF 的"相同"需要 `SOURCE_DATE_EPOCH` + `svg.hashsalt` 双钉死，而这只是"能比"，不代表该比。正规做法是对**光栅化后的像素**比（`matplotlib.testing.compare_images`，或自己 `savefig` 成 PNG 后算差异），这也正是 matplotlib 自身测试的做法。若确实要提交矢量产物，就把两个环境变量写进 CI 配置，否则每次构建都是全量 diff。

### B4.6 `savefig(backend=...)` 的合法组合，以及绕过 pyplot 的嵌入

```python
>>> fig.savefig(buf, format="svg", backend="svg")     # ok
>>> fig.savefig(buf, format="pdf", backend="pdf")     # ok
>>> fig.savefig(buf, format="png", backend="svg")
ValueError: The 'svg' backend does not support png output
>>> fig.savefig(buf, format="png", backend="cairo")
ImportError: cairo backend requires that pycairo>=1.14.0 or cairocffi is installed
```

`backend=` 的语义是"**换一个画布来渲染这个格式**"，所以要求该后端支持该格式，且依赖要装齐。合法用法是 `format="png", backend="cairo"` 这类"位图换实现"，或者用 `"pgf"` 后端把 PDF 交给 LaTeX。

**嵌入**（把图塞进自己的程序，不经过 pyplot）：

```python
>>> from matplotlib.figure import Figure
>>> from matplotlib.backends.backend_agg import FigureCanvasAgg
>>> f2 = Figure(figsize=(3, 2), dpi=100)
>>> a2 = f2.subplots(); a2.plot([0, 1, 2], [2, 1, 0])
>>> canvas = FigureCanvasAgg(f2)              # 挂上画布，f2.canvas 就有了
>>> canvas.draw()
>>> np.asarray(canvas.buffer_rgba()).shape
(200, 300, 4)
>>> plt.get_fignums()                          # pyplot 完全不知道 f2 存在
[]
```

`Figure` 与 `pyplot` 是**解耦**的：直接 `Figure()` + `FigureCanvasAgg(fig)` 就是"无状态、可多线程、可嵌 GUI"的用法；pyplot 只是替你维护 `Gcf` 注册表（B1.5）。Web 服务里给每个请求建一个 `Figure` 而不用 pyplot，正是为了避免全局注册表与线程问题。

### B4.7 其他画布家族（文献，本环境只有 Agg）

| 画布 | 宿主 | 典型场景 |
|------|------|---------|
| `FigureCanvasAgg` | 无 | 文件输出、CI、批量出图（本文件全部实测用它） |
| `FigureCanvasQT*` | Qt | 桌面应用、大数据交互（Qt 原生缩放） |
| `FigureCanvasTk*` | Tk | 轻量工具、教学 |
| `FigureCanvasWebAgg` | 浏览器 + Tornado | 不必装 GUI 就能远程交互 |
| `FigureCanvasNbAgg` / `ipympl` | Jupyter | 内嵌交互（依赖 `ipympl`） |

共性是**都实现同一套 `FigureCanvasBase` 协议**（`draw`、`blit`、`print_*`、`mpl_connect`），所以从 Agg 到 Qt 代码结构不变，变的只是宿主与刷新方式。`plt.show()` 在哪个后端下做什么，由 manager 决定（B1.5）。

> **机制洞察**：`Figure` 是**与后端无关的抽象**，`canvas` 才连接具体宿主，`renderer` 才真正落笔。这张"抽象—适配—实现"的三层结构，正是同一份绘图代码可以在无头服务器、Qt 桌面、浏览器里跑同一套行为的原因。

> **延伸阅读**：`matplotlib/backend_bases.py`（`FigureCanvasBase.print_figure`、`_switch_canvas_and_return_print_method`）；Agg 实现见 `matplotlib/backends/backend_agg.py`；SVG id 生成见 `matplotlib/backends/backend_svg.py`；可复现构建见 <https://reproducible-builds.org/docs/source-date-epoch/>。

---

## B5 色彩管线内核：归一化、查表与 colorbar

主章 3.9 的结论是"数值 → 颜色的完整管线，`clim` 是第二自由度"。B5 把这条管线拆成 **归一化 → 查表** 两步，并说明 colorbar 到底是什么对象。

### B5.1 归一化家族：第一步只有"映射到 [0,1]"

```python
>>> vals = np.array([-10., -1., 0., 1., 10., 100.])
>>> for norm in (mcolors.Normalize(0, 100), mcolors.LogNorm(1, 100),
...              mcolors.SymLogNorm(1, vmin=-100, vmax=100),
...              mcolors.PowerNorm(0.5, 0, 100),
...              mcolors.TwoSlopeNorm(vcenter=0, vmin=-100, vmax=100),
...              mcolors.NoNorm()):
...     print(f"{type(norm).__name__:<16} {np.round(norm(vals), 4)}")
Normalize        [-0.1   -0.01   0.     0.01   0.1    1.   ]
LogNorm          [1.  1.  1.  0.  0.5 1. ]
SymLogNorm       [0.1607 0.3214 0.5    0.6786 0.8393 1.    ]
PowerNorm        [-0.1   -0.01   0.     0.1    0.3162 1.    ]
TwoSlopeNorm     [0.45  0.495 0.5   0.505 0.55  1.   ]
NoNorm           [-10.  -1.   0.   1.  10. 100.]
```

| 归一化器 | 参数 | 什么时候用 | 关键性质 |
|---------|------|-----------|---------|
| `Normalize` | `vmin, vmax, clip` | 默认 | **输出可越界**（这里是 `-0.1`、`1.`），越界值交给 colormap 的 under/over |
| `LogNorm` | `vmin>0, vmax` | 跨数量级 | ≤0 的值被静默裁剪 |
| `SymLogNorm` | `linthresh` | 有正负且含 0 | 0 附近线性、两端对数 |
| `PowerNorm` | `gamma` | 偏态分布 | γ<1 提亮暗部 |
| `TwoSlopeNorm` | `vcenter` | 发散型数据（正负各有意义） | 强制 `vcenter → 0.5` |
| `BoundaryNorm` | `boundaries, ncolors` | 离散分级（热力分级图） | **输出整数索引**，越界给 `-1` / `ncolors` |
| `NoNorm` | — | 数据本身就是索引 | 直通，不做任何缩放 |

```python
>>> mcolors.Normalize(0, 100, clip=True)(np.array([-50., 150.]))
array([0., 1.])
>>> mcolors.BoundaryNorm([0, 1, 10, 100], ncolors=3)(vals)
array([-1, -1,  0,  1,  2,  3])       # -1 与 ncolors 是留给 under/over 的哨兵
>>> mcolors.Normalize(0, 100).inverse(0.5), mcolors.LogNorm(1, 100).inverse(0.5)
(50.0, 10.0)
```

两个细节直接对应主章 3.9：**`clip=False` 时"越界"是有意义的输出**（映射到 colormap 的 under/over 色，而不是被夹到端点色），这正是"`clim` 是第二自由度"的实现依据；**`inverse()` 存在**，所以 colorbar 的反向（拖动、点选）在数学上总有解。

### B5.2 Colormap 的内部就是一张 RGBA 表

```python
>>> cm = mpl.colormaps["viridis"]; cm._init()        # 仅取证
>>> cm.N, type(cm).__name__
(256, 'ListedColormap')
>>> cm._lut.shape, cm._i_under, cm._i_over, cm._i_bad
((259, 4), 256, 257, 258)
>>> np.round(cm._lut[-3:], 3)                        # 末尾三行：under / over / bad
array([[0.267, 0.005, 0.329, 1.   ],
       [0.993, 0.906, 0.144, 1.   ],
       [0.   , 0.   , 0.   , 0.   ]])
>>> cm.set_under("blue"); cm.set_over("green"); cm.set_bad("red")
>>> np.round(cm._lut[-3:], 3)
array([[0.   , 0.   , 1.   , 1.   ],                  # under
       [0.   , 0.502, 0.   , 1.   ],                  # over
       [1.   , 0.   , 0.   , 1.   ]])                 # bad
>>> cm(-0.1), cm(1.1), cm(np.ma.masked)
(array([0., 0., 1., 1.]), array([0.   , 0.502, 0.   , 1.   ]), array([1., 0., 0., 1.]))
```

读懂这张表就理解了全部规则：

- `_lut` 是 **`(N+3, 4)`** 的 float32/float64 数组：前 `N` 行是正常颜色，**最后三行专门留给 under / over / bad**，索引分别是 `N`、`N+1`、`N+2`；
- **默认 under/over 就是首尾色**（所以"越界不变色"是默认行为），**默认 bad 是全透明黑**（所以 `NaN` 位置默认是"洞"而不是黑块）；
- `cmap(x)` 的语义是"按归一化值查表"：`x<0 → under`、`x>1 → over`、 **掩码值 → bad**。`np.ma.masked` 走 bad 这一条，是 numpy 掩码数组与绘图库协作最优雅的一处。

```python
>>> r5 = cm.resampled(5); r5._init()
>>> r5.N, r5._lut.shape
(5, (8, 4))                            # 重采样后仍是 N+3 行
>>> np.round(cm.reversed()(0.0), 3)
array([0.993, 0.906, 0.144, 1.   ])    # reversed 只反转查表顺序
```

`resampled(n)` 把连续 colormap 变成 n 级离散（做分级图用），`reversed()` 反转——两者都返回新对象，**原 colormap 不被修改**（全局注册表里的对象是共享的，就地改会让全程序变色）。

### B5.3 注册表：182 个 colormap 的名字空间

```python
>>> type(mpl.colormaps).__name__, len(mpl.colormaps)
('ColormapRegistry', 182)
>>> mpl.colormaps.register(mpl.colormaps["viridis"], name="viridis")
ValueError: A colormap named "viridis" is already registered.
>>> import inspect; inspect.signature(mpl.colormaps.register)
(cm, *, name=None, force=False)         # 覆盖要显式 force=True
```

3.9 起统一走 `matplotlib.colormaps["name"]`，旧的 `plt.cm.get_cmap` 已移除（主章"版本注意②"）。**重名必须显式 `force=True`** 才能覆盖——这是防止库之间悄悄抢名字的保护。注册自己的 colormap（品牌色、领域色标）就是在这里插一条。

### B5.4 colorbar 不是一根轴，而是一个"拥有一根轴"的对象

主章说"colorbar 为什么是一根轴"。严格地说：**colorbar 自己不是 `Axes`，它持有一根 `Axes`**。

```python
>>> fig, ax = plt.subplots()
>>> im = ax.imshow(np.random.default_rng(0).random((10, 10)), cmap="viridis")
>>> cb = fig.colorbar(im, ax=ax)
>>> [c.__name__ for c in type(cb).__mro__[:2]]
['Colorbar', 'object']                  # 不是 Axes 子类
>>> isinstance(cb, plt.Axes), type(cb.ax).__name__, cb.ax is cb
(False, 'Axes', False)
>>> cb.mappable is im, type(cb.norm).__name__, im.colorbar is cb
(True, 'Normalize', True)
>>> len(fig.axes)
2                                       # 主图 + colorbar 的轴
>>> fig.colorbar(im, ax=ax); len(fig.axes)
3                                       # 每调一次就多一根轴，不会复用
```

这解释了三件事：

1. **colorbar 的刻度来自 mappable 的 `norm`**（`cb.get_ticks()` 就是 `norm` 的刻度），所以"colorbar 与图不一致"的根因永远在 `norm`/`clim`，不在 colorbar；
2. `cb.ax` 是一根**普通 Axes**，所以 `cb.ax.set_ylabel(...)`、`cb.ax.tick_params(...)` 全部可用，`cax=` 参数就是把"给你哪根轴"交回你手里；
3. **重复调用 `fig.colorbar(im)` 会不断加轴**，而且旧 colorbar 不会自动删除——循环里画图要显式 `cb.remove()` 或复用一个 `cax`。

### B5.5 成本账：归一化便宜，查表是大头

```python
>>> data = np.random.default_rng(1).random(1_000_000) * 100
>>> norm = mcolors.Normalize(0, 100); cm = mpl.colormaps["viridis"]
# 本机实测（取最小值）
Normalize(1e6)                1.38 ms
Normalize + cmap(...)         8.77 ms
查表部分                     ~7.39 ms        # 每点约 7.4 ns
cmap._lut[(norm(data)*255).astype(int)]   5.99 ms   # 手工索引快 1.5 倍（仅取证）
```

三个可操作的推论：

1. **归一化不是瓶颈**（1e6 点 1.4 ms），"颜色算得慢"通常是后面的查表与绘制；
2. **每次 `cmap(array)` 都要做边界判断 + 掩码处理**，比直接索引 `_lut` 慢 1.5 倍；批量预处理颜色（例如做缓存、做 LUT 索引）值得，但**不要为了这 1.5 倍在生产代码里依赖 `_lut`**（私有）；
3. `imshow`/`scatter` 的颜色换算发生在**设置数据时或绘制时**，与 B1.8 的 `dataLim` 同理：**数据一大，颜色管线要和数据管线一起优化**（同一条"向量化"纪律，回链 ds-01 1.15）。

> **机制洞察**：色彩系统的本质是 **"两步分离"——`Normalize` 管数值语义，`Colormap` 管视觉映射**。所有"颜色不对"的问题都能按这两步切开：先看 `norm(v)` 是不是你要的 [0,1]（`clim`/`clip` 的锅），再看 `cmap` 的 under/over/bad 设置（视觉语义的锅）。colorbar 只是这两步的可视化代理。

> **延伸阅读**：`matplotlib/colors.py`（`Normalize` 家族、`Colormap._lut`、`ColormapRegistry`）；colorbar 装配见 `matplotlib/figure.py` 的 `Figure.colorbar`/`Colorbar`；分级图实践见主章 3.9 与 [Choosing Colormaps](https://matplotlib.org/stable/users/explain/colors/colormaps.html)。

---

## B6 渲染成本实测：三个杠杆值多少

主章 3.14 给了"三本账"的框架。B6 回答"每一笔花在哪"，并给出可复现的数字。所有计时都是 640×480、`dpi=100`、Agg、取 3–5 次最小值。

### B6.1 先定位：draw 内部的时间分布

用一条 10 万点折线做基准（B1.1 已列全）：

```
renderer.clear()                0.025 ms    0.02%
fig.draw_without_rendering()    3.53  ms    2.8%     布局
fig.draw(renderer)            123.90  ms   98.6%     绘制
canvas.draw() 合计            125.18  ms
+ PNG 编码                     2.2   ms    1.7%
```

**结论：优化目标只有一个——`Artist.draw`。** 布局、缓冲、编码加起来不到 5%。这也是为什么下面的三个杠杆全部作用于"落笔"这一层。

### B6.2 杠杆一：Artist 数量（对象合并）

同样的 1000 组数据，切成不同数量的对象：

| 画法 | draw | PNG 体量 |
|------|------|---------|
| 1 条 `Line2D` | 9.98 ms | 23 324 B |
| 10 条 `Line2D` | 10.73 ms | 26 508 B |
| 100 条 `Line2D` | 14.07 ms | 42 259 B |
| 1000 条 `Line2D` | **72.09 ms** | 125 628 B |
| 1000 段合成 1 个 `LineCollection` | **56.95 ms** | **20 318 B** |

两条曲线形状不同，值得分开说：

- **时间随对象数近线性增长**：1→1000 条是 10 ms→72 ms 的 **7 倍**，而数据量完全一样。多出来的是每个 artist 的属性解析（`gc` 设置）、`transData` 复合、`open_group/close_group` 与 Agg 的路径提交——**Python/C 边界的固定税**。
- **产物体量差 6 倍**（125 KB vs 20 KB）：1000 个 artist 会产生 1000 组独立描边元数据与重复样式；`LineCollection` 把它们合并成一次批处理路径。

> 注意 `LineCollection` 的 draw 没有比 1000 条 `Line2D` 快一个数量级（56.95 vs 72.09），因为主导成本是 10 万个顶点的光栅化本身。**对象合并省的是"每次落笔的固定开销"，不是顶点成本**——顶点成本要靠 B6.3 的简化。

### B6.3 杠杆二：路径简化（`path.simplify`）

100 万个噪声点画成一条线（像素只有 640×480，绝大多数点落在同一像素里）：

| 设置 | draw | PNG 体量 |
|------|------|---------|
| `path.simplify=True`（默认，阈值 1/9） | **215.57 ms** | 20 194 B |
| `path.simplify=False` | **7984.36 ms** | 19 161 B |

**37 倍**，这是三个杠杆里最猛的一个。原理是**顶点抽稀**——官方 rcParam 的措辞是 "simplify paths by removing *invisible* points to reduce file size and increase rendering speed"，阈值 `path.simplify_threshold` 则是"低于此相似度就删点"。它可以被直接观测：

```python
>>> from matplotlib.path import Path
>>> from matplotlib.transforms import IdentityTransform
>>> p = Path(np.column_stack([np.linspace(0, 10, 2000), noisy_y]))   # 2000 点噪声折线
>>> pc = p.cleaned(transform=IdentityTransform(), simplify=True)     # 仅取证
>>> len(p.vertices), len(pc.vertices)
(2000, 271)                                    # 保留 13.6%
>>> d = np.abs(pc.vertices[:, None] - p.vertices[None]).max(axis=2).min(axis=1)
>>> round(float((d < 1e-9).mean()), 3)         # 保留点里与原始顶点逐位相同的比例
0.996
```

**它是删点而不是拟合**：保留下来的顶点坐标原封不动，被丢掉的都是像素尺度上分辨不出的中间点（顺带把共线点也压掉）。所以它不会改变"你看得见的形状"，只丢"看不见的细节"——这与"降采样"是两回事，后者会移动每一个点。（注意 `Path.cleaned` 会在路径两端追加闭合顶点，所以点数不是严格子集；绘制路径上的简化发生在 C 层的 `_path.cleanup_path`。）

```python
>>> mpl.rcParams["path.simplify"], mpl.rcParams["path.simplify_threshold"]
(True, 0.1111111111111111)
```

**什么时候该关**：数据本身在像素尺度上确实有细节、且你要放大看（例如保存后交给别人做矢量缩放）。此时把它显式关掉并接受慢，比拿到一条被"磨平"的曲线好。但要注意**这个开关只有全局 rcParams，没有 artist 级接口**——`Line2D` 上并没有 `set_simplify`（`set_sketch_params` 是手绘风格效果，不是这个）。实践中只有两条路：用 `mpl.rc_context({"path.simplify": False})` 临时全局关闭，或**先在数据层抽稀/加密**再绘制（把控制权拿回自己手里，也更容易写进测试）。

### B6.4 杠杆三：渲染器分块（`agg.path.chunksize`）

200 万点的折线：

| `agg.path.chunksize` | draw |
|---------------------|------|
| 0（默认，不分块） | 232.12 ms |
| 1000 | **107.72 ms** |
| 100 000 | 115.36 ms |

**2.2 倍**。原因是 Agg 光栅化一条超长折线时会构造巨大的顶点/覆盖缓冲，**缓存与临时内存都爆掉**；分块后每块只占一个小缓冲，吞吐由内存局部性决定。1000 与 100000 差别不大，说明**只要分块就有收益，块大小不必精调**。

这条杠杆的定位很明确：**它是"百万点以上的折线"专用药**，曲线子图、少量点、散点都用不上。默认 0 是保守选择（避免影响需要精确覆盖判断的场景）。

### B6.5 散点与矢量爆炸：什么时候必须光栅化

| 点数 | draw | PNG | SVG | SVG 耗时 |
|------|------|-----|-----|---------|
| 1 000 | 8.55 ms | 21 KB | 119 KB | 16.6 ms |
| 10 000 | 9.56 ms | 83 KB | 1.08 MB | 72.0 ms |
| 100 000 | 17.70 ms | 100 KB | **10.66 MB** | 611.2 ms |
| 1 000 000 | 100.47 ms | 10.5 KB | **106.5 MB** | 6254.4 ms |

三列数字讲三个不同的故事：

1. **draw 只从 8.5 ms 涨到 100 ms（12 倍）**，而点数涨了 1000 倍——Agg 在屏幕尺度上的光栅化是"按像素覆盖"而非"按点"的，所以上百万点仍然能画（100 ms/帧，静态图完全可用）；
2. **SVG 从 119 KB 涨到 106.5 MB（900 倍）**——矢量格式必须为每个点保留一条 `<path>`/`<use>`，**这就是"矢量爆炸"**：它是**产物**问题，不是渲染问题；
3. **PNG 在 100 万点时反而比 10 万点小**（10.5 KB vs 100 KB）：点太密把画面涂成了近似纯色，压缩率飙升。**"PNG 变小"不代表数据变少**，这条常被误读。

救护方法一行：

```python
>>> s = ax.scatter(x, y, s=1); s.set_rasterized(True)
n=10000   svg 1 077 410 B -> 106 703 B    (78.7 -> 31.4 ms)
n=100000  svg 10 663 042 B -> 124 580 B   (609.2 -> 40.6 ms)
```

**`set_rasterized(True)` 让单个艺术家在矢量输出里退化成一张位图**——10 万点时 SVG 缩小 **85 倍**、耗时缩短 **15 倍**，而坐标轴、文字、标注仍是矢量。这是"出版图要矢量"与"百万数据要位图"之间的标准折中，也是主章 3.12 与 3.14 交界处最实用的一招。

同一份 10 万点数据存 PDF 是 1 588 540 B / 618 ms——**PDF 比 SVG 小一个数量级**，因为它的内容流是压缩的。所以"矢量太大"时，换 PDF 也是选项。

### B6.6 三本账的汇总表

| 杠杆 | 开启方式 | 本机收益 | 适用信号 | 副作用 |
|------|---------|---------|---------|--------|
| **路径简化** | `path.simplify=True`（默认开） | **37×** | 点数 ≫ 像素数 | 细节被抽稀，放大看不到 |
| **渲染分块** | `agg.path.chunksize=1000` | **2.2×** | 单条线 > 百万点 | 需确认覆盖判断无影响 |
| **对象合并** | `LineCollection`/`PatchCollection`/`scatter` 取代逐个 artist | 时间 **1.3×**、产物 **6×** | artist 数量 > 数百 | 需改写法，灵活性下降 |
| **光栅化** | `artist.set_rasterized(True)` | 产物 **85×**、耗时 **15×** | 矢量输出爆炸 | 该元素不可矢量缩放 |

> **⚠️ 陷阱**：**别把四个杠杆一起上**。它们治的是不同的病：简化治"点太多"、分块治"线太长"、合并治"对象太多"、光栅化治"产物太大"。先量（B6.1 的分布）→ 再定位（哪一列数字不对）→ 只上对应的那一个。四个一起上的典型后果是：曲线被抽稀（简化）、覆盖判断错位（分块）、元素无法单独样式化（合并）、导出后无法缩放（光栅化）——**四种副作用同时到场，而其中三种本来没必要**。这与 ds-01 第 15 章"五层路线图"的次序纪律完全一致。

> **机制洞察**：渲染性能的三个数量级分别对应三种"冗余"——**像素冗余**（简化，37×）、**内存冗余**（分块，2.2×）、**对象冗余**（合并，6× 产物）。matplotlib 的默认值（简化开、分块关）说明它优先保护**视觉保真**，把"要更快"的选择留给用户；理解这一点，就不会指望"改一个 rcParam 就全局变快"。

> **延伸阅读**：`matplotlib/path.py` 的 `cleanup`/`simplify` 与 `Path.cleaned`；Agg 分块见 `matplotlib/backends/backend_agg.py`（`agg.path.chunksize`）；artist 光栅化见 `matplotlib/artist.py` 的 `allow_rasterization` 与 `_rasterization_zorder`；官方性能建议见 [Performance](https://matplotlib.org/stable/users/explain/performance.html)。

---

## B7 动画与 blitting：最小重绘

主章 3.12 说"无头≠不能交互"，动画与 blitting 是它的延伸。B7 回答：**为什么动画能比静态图快 50 倍，以及 `animated` 到底改变了什么。**

### B7.1 `animated` 标志是"两副面孔"

```python
>>> line.set_animated(True)
>>> line.get_animated(), line in ax.get_children()
(True, True)                                  # 仍在树里，只是不参与常规绘制
>>> fig.canvas.is_saving()
False

# 关键对照实验
>>> normal = save_png(fig)                    # 未设 animated
>>> ax.lines[0].set_animated(True)
>>> anim = save_png(fig)
>>> normal == anim
True                                          # savefig 时 animated 线仍然被画！
>>> fig.canvas.draw()
>>> b = io.BytesIO(); fig.canvas.print_png(b)
>>> b.getvalue() == anim
False                                         # 普通重绘时它被跳过
```

机制在 B1.1 的第 ④ 步：

```python
if not self.get_figure(root=True).canvas.is_saving():
    artists = [a for a in artists if not a.get_animated()]
```

而 `savefig` 会在 `print_figure` 里 `cbook._setattr_cm(self.figure.canvas, _is_saving=True)`（`animation.save` 同样设置）。所以：

| 场景 | `is_saving()` | animated artist |
|------|--------------|----------------|
| `fig.savefig()` | `True` | **画**（保证导出完整） |
| `canvas.draw()` / `print_png()` | `False` | **跳过**（交给动画循环自己画） |
| `anim.save(...)` | `True` | **画** |

> **⚠️ 陷阱**：这正是"Notebook 里动画正常、导出的 GIF 里少了一条线"或**反过来**"静态导出多出一条本该隐藏的辅助线"的根因。`animated=True` 的语义不是"隐藏"，而是 **"由我负责画"**——你必须在动画的 `update` 里手动 `draw_artist` + `blit`，否则它在交互视图里永远不会更新（B7.2）；而导出时它又被自动画进去，两条路径的行为刻意不同。

### B7.2 blitting：一次 49 倍的账

blit 的思路是 **"背景快照 + 只重绘变化的部分"**：

```python
>>> bg = fig.canvas.copy_from_bbox(fig.bbox)
>>> type(bg).__name__
'BufferRegion'
>>> x = np.linspace(0, 10, 100)
>>> def full_frame(i):
...     line.set_data(x, np.sin(x + i*0.1)); fig.canvas.draw()
>>> def blit_frame(i):
...     fig.canvas.restore_region(bg)              # 贴回背景快照
...     line.set_data(x, np.sin(x + i*0.1))
...     ax.draw_artist(line)                       # 只画这条线到缓冲
...     fig.canvas.blit(fig.bbox)                  # 把缓冲里这块刷到屏幕

整帧 canvas.draw():   9.89 ms/帧
blit 局部重绘:        0.20 ms/帧      -> 49.4 倍
```

四步各自的作用：`copy_from_bbox` 存下静态背景；`restore_region` 抹掉上一帧的线；`draw_artist` 只光栅化这一个 artist；`blit` 把脏矩形交给宿主刷新。**省掉的正是 B6.2 里"每个 artist 的固定税"与背景的全部重绘。**

诚实的边界：**`blit` 的收益取决于宿主**。Agg 的 `blit` 是真实的内存拷贝（所以上面测得出 49 倍）；GUI 后端的 `blit` 会把矩形推给窗口系统，收益更大；而**保存视频时 blit 帮不上忙**（B7.4）。所以主章 3.14 那句"动画的最小重绘策略"只对交互场景成立。

### B7.3 `FuncAnimation` 的骨架与 writer 生态

```python
>>> anim = FuncAnimation(fig, update, frames=20, interval=50, blit=True)
>>> type(anim).__name__
'FuncAnimation'
>>> [a for a in ("_fig","_func","_blit","frame_seq","save_count","event_source") if hasattr(anim, a)]
['_fig', '_func', '_blit', 'frame_seq', 'save_count', 'event_source']
>>> list(anim.new_frame_seq())[:5]
[0, 1, 2, 3, 4]
```

`FuncAnimation` 只做三件事：**产生帧号序列**（`frames` 可以是 int/迭代器/生成器）、**每帧调用你的 `update(i)`**、**把返回的 artist 集合按 `blit` 策略重绘**。它内部连接 `draw_event` 来启动，所以"动画不播"的第一嫌疑永远是**figure 没被显示出来**（无头环境下没有事件源）。

保存需要**真实文件路径**（`anim.save(BytesIO)` 会 `TypeError`，writer 要 `Path(outfile).parent.resolve()`）：

```python
>>> from matplotlib.animation import PillowWriter
>>> anim.save("/tmp/a.gif", writer=PillowWriter(fps=20))
20 帧 GIF: 605 ms, 124 026 字节, 头 b'GIF89a'
>>> anim.save("/tmp/b.gif", writer="pillow", fps=20, dpi=50)
67 698 字节                                  # dpi 直接乘面积
>>> FFMpegWriter.isAvailable(), HTMLWriter.isAvailable()
(False, True)                                # 本机没装 ffmpeg；HTMLWriter 可用
```

writer 生态的分工：

| writer | 依赖 | 产物 | 备注 |
|--------|------|------|------|
| `PillowWriter` | `Pillow` | GIF / APNG | 无需外部程序，体积大、无音轨 |
| `FFMpegWriter` | ffmpeg 可执行文件 | mp4 / webm / gif | 质量与体积最好，**需系统装 ffmpeg** |
| `HTMLWriter` | 无（自包含 JS） | HTML | 内嵌 base64 视频，体积受 `animation.embed_limit` 限制 |
| `ImageMagickWriter` | ImageMagick | GIF | 老牌管线 |

`animation.embed_limit` 默认 **20.0**（MB）——HTMLWriter 超出会警告并截断，这是"Notebook 里动画只有前几秒"的常见原因。

### B7.4 保存时 blit 无效，因为每帧都是"新的一帧"

`anim.save` 把 `is_saving` 置 `True`（B7.1），此时：

1. `Axes.draw` **不再剔除 animated artist**，每帧都完整重绘；
2. writer 逐帧取 `canvas.buffer_rgba()` 编码——**没有"屏幕"，也就没有"脏矩形"可刷**。

所以 `blit=True` 在保存路径上**语义正确地退化为全量重绘**（不会出错，只是不省时间）。想加快导出，只能从三处下手：**降 `dpi`、减帧数、减每帧的 artist 数量**（B6 的三个杠杆对每帧同样有效）。GIF 的体量则近似正比于 `dpi² × 帧数`（实测 100 dpi 124 KB → 50 dpi 68 KB）。

> **机制洞察**：动画的性能模型是 **"把静态图的 draw 拆到 N 帧里"**。因此它继承了 B1 的全部性质（stale、全量重绘、zorder 排序）与 B6 的全部杠杆，只额外多了一条"允许少画"的通道——blit。理解这一层，就不会再问"为什么我的动画导出还是慢"：**导出必然全量，快慢只由 `dpi × 帧数 × 每帧复杂度` 决定。**

> **延伸阅读**：`matplotlib/animation.py`（`FuncAnimation`、`Animation.save`、各 writer 的 `isAvailable`）；blit 协议见 `matplotlib/backend_bases.py` 的 `FigureCanvasBase.blit` 与 `BufferRegion`；官方教程 [Animations with Matplotlib](https://matplotlib.org/stable/users/explain/animations/animations.html)。

---

## B8 何时离开 matplotlib：把边界量化

主章 3.14/3.15 讲的是"在 matplotlib 内部怎么快"。B8 回答下一个问题：**什么时候不该在它内部解决。** 与 ds-02b B8 的写法一致——先给量化信号，再给决策表。

### B8.1 三个已经量化的信号

| 信号 | 实测证据 | 说明 |
|------|---------|------|
| **矢量产物爆炸** | 1e5 点散点：SVG 10.66 MB / 611 ms，PNG 100 KB / 17.7 ms（B6.5） | 出力格式与交互需求不匹配 |
| **单帧超出交互预算** | 1e6 点散点：100 ms/帧（B6.5） | 60 fps 的预算是 16 ms，差 6 倍以上 |
| **重绘成本压在背景上** | 整帧 9.89 ms 里主线只占不到 1 ms（B7.2 的 blit 实验） | 说明"要动的东西少、背景大"，blit 或换库 |

三个信号指向三种不同的出路：**产物问题 → 光栅化（不出 matplotlib）**；**交互问题 → 换交互库（出 matplotlib）**；**局部更新问题 → blit（留在 matplotlib）**。

### B8.2 第一选择永远是光栅化，不是换库

B6.5 已经证明：`set_rasterized(True)` 让 1e5 点散点的 SVG 从 10.66 MB 降到 124 KB（**85 倍**），而出版所需的坐标轴、刻度、文字、标注全部保持矢量。**"matplotlib 出不了大图"这个判断，在绝大多数情况下是错的**——错的只是"全部都要矢量"这个隐含前提。

判断顺序：

1. **这个元素需要矢量缩放吗？** 散点、密集折线、热力图 → 不需要 → `set_rasterized(True)`；
2. **观众需要缩放/悬停吗？** 需要 → 才轮到交互库；
3. **数据点数量级超过 1e6 且要交互吗？** 是 → 数据聚合（datashader 的思路）比换画布更根本。

### B8.3 生态边界表（文献，非实测）

| 库 | 定位 | 与 matplotlib 的关系 | 什么时候选它 |
|----|------|---------------------|-------------|
| **matplotlib** | 静态出版图 + 万能底层 | 生态的公共地基 | 论文、报告、CI 出图、需要像素级控制 |
| **seaborn** | 统计图高层封装 | **构建在 matplotlib 上**，返回/接受 matplotlib 对象 | 分面统计图、分布比较，且仍要 matplotlib 收尾（主章 3.13） |
| **pandas.plot** | 数据框快捷出图 | 转发到 matplotlib | 探索期一行出图，进一步定制前 `plt.gca()` 接管（主章 3.13） |
| **plotly** | 交互图 + Web | 各自独立 | 需要悬停/缩放/导出交互 HTML |
| **bokeh** | 交互 + 仪表盘服务 | 各自独立 | 实时刷新、流式数据、Web 服务 |
| **altair** | 声明式（Vega-Lite） | 各自独立 | 数据变换即声明、图表即 JSON |
| **datashader** | 大数据量光栅聚合 | 常与 HoloViews/Bokeh 配合 | 1e6–1e9 点：先聚合到像素再画 |
| **holoviews** | 统一抽象层 | 可选用 matplotlib 作后端 | 一份代码切多个后端 |

边界一句话：**matplotlib 管"出版级的静态正确性"，交互库管"探索期的响应速度"，datashader 管"点数超过像素数时的聚合"。** seaborn/pandas.plot 不是替代品而是上层——它们的产物仍然是 matplotlib 对象，随时可以掉回 `ax` 层收尾（主章 3.13 的两级 API）。

### B8.4 决策次序

```
先问：产物是给人看，还是给机器看？
├─ 给人看（报告/论文）
│   ├─ 元素需要缩放？ → 是的部分留矢量，其余 set_rasterized(True)     ← 先做这个
│   └─ 还是太大？      → 换 PDF（同数据小一个数量级，B6.5）
└─ 给人操作（交互）
    ├─ 点数 < 1e5，要悬停/缩放        → plotly / bokeh
    ├─ 点数 1e5–1e6，要局部刷新       → matplotlib + blit（B7.2，49×）
    └─ 点数 > 1e6                     → datashader 聚合后再画
```

与 ds-02b B8 的次序纪律逐字一致：**先归因到层（产物层/渲染层/对象层）→ 在层内解决 → 最后才换工具**。反过来做（先换库）最常见的结果是：把"没光栅化"的问题变成"两套 API 都要维护"的问题。

> **机制洞察**：matplotlib 的边界由它的设计目标划出——**"出版级静态图，像素级可控"**。它为此选择了 Agg 的 CPU 光栅化、矢量 fs 的完整输出、以及"全量重绘"的简单模型（B1.2）。这三条决定了它的三个边界：**交互**（给它事件循环不如给浏览器）、**百万级交互数据**（像素聚合比图元堆叠更根本）、**实时流**（全量重绘模型天生不适合）。知道边界在哪，才知道什么时候不该硬扛。

> **延伸阅读**：数据量边界与聚合策略见 [Datashader](https://datashader.org/)；交互库定位见 [Plotly](https://plotly.com/python/)、[Bokeh](https://docs.bokeh.org/)；声明式见 [Vega-Altair](https://altair-viz.github.io/)；seaborn 与 matplotlib 的关系见主章 3.13 与其官方文档 [seaborn](https://seaborn.pydata.org/)。

---

## 本文件小结

| 节 | 核心结论 |
|----|---------|
| B1 | draw = 脏标记 + 全量重绘：`Figure.draw` 六步、`Axes.draw` 按 `sorted(zorder)` 稳定排序；stale 三级回调可被 `animated` 截断；**`savefig` 结束反而 `fig.stale == True`**；`viewLim` 的 getter 会消费 autooscale 懒标记；`remove()` 不幂等（二次抛 `ValueError`）；别名表只挂在 Line2D/Collection/Patch/Text 上，所以 `ax.set(lw=)` 报错 |
| B2 | `transData = transScale + (transLimits + transAxes)`，每层一个仿射；换标度只换 `transScale._child`（对象 id 不变）；`wspace` 是格宽倍数、`GridSpec(None)` 回退到 `fig.subplotpars`；`constrained` 是每次 draw 都 `execute` 的求解器；`apply_aspect` 只改活动框；共享轴 `Grouper` 用弱引用自动退组 |
| B3 | 注册表**随模块加载增长**（`units` 只带 1 条，`+dates` 4 条，`+category` 8 条）；轴上有 `_converter` 与 `units` 两个槽位（日期轴的 `units` 是 `None` 但 `have_units()` 为真）；`axisinfo` 是 locator/formatter/label 的供应商；自定义类型 20 行接入；**字符串↔数值混用三种静默错误**（数字字符串变类别、数值外推、中途换轴导致错位）；pandas 在 plot 期间临时换表、退出还原——**转换器装在轴上，不装在注册表上** |
| B4 | 24 个内置后端走注册表；Agg 下 `plt.show()` 只发 `UserWarning`；`buffer_rgba()` 是**零拷贝可写** `memoryview`，用前 `.copy()`；**PNG 可复现，PDF/EPS 需 `SOURCE_DATE_EPOCH`，SVG 还需 `svg.hashsalt`**（id 是 `sha256(salt+content)`，默认盐是随机 uuid） |
| B5 | 色彩 = 归一化 + 查表：`Normalize` 家族含 `BoundaryNorm`（整数索引）与 `NoNorm`；`_lut` 是 `(N+3, 4)`，末三行是 under/over/bad；`resampled`/`reversed` 返回新对象；**`Colorbar` 不是 `Axes`，它持有 `cb.ax`**，重复调用会不断加轴；1e6 点归一化 1.4 ms、查表 7.4 ns/点 |
| B6 | 布局只占 3%，优化目标只有 `Artist.draw`；三个杠杆实测：**简化 37×**、**分块 2.2×**、**对象合并时间 1.3× / 产物 6×**；光栅化让 1e5 点 SVG 缩小 **85×**；PNG 在 1e6 点时反而更小（密集成纯色） |
| B7 | `animated` 是"由我负责画"：普通重绘跳过、`savefig`/`anim.save` 强制画；blit = 背景快照 + 局部重绘，实测 **49×**（9.89 → 0.20 ms/帧）；保存路径上 blit 语义正确但无效，导出快慢只由 `dpi × 帧数 × 每帧复杂度` 决定 |
| B8 | 三个量化信号：矢量爆炸 / 单帧超预算 / 成本压在背景；**第一选择是光栅化而不是换库**（85×）；matplotlib 的三个边界是交互、百万级交互数据、实时流；次序永远是"归因到层 → 层内解决 → 最后换工具" |

**回到主章**：B1 → 3.2、3.3、3.7、3.11、3.15；B2 → 3.5、3.8；B3 → 3.6、3.10、3.13；B4 → 3.12；B5 → 3.9；B6 → 3.14；B7 → 3.12、3.14；B8 → 3.14、3.15。

**三本深水文件的分工**：`ds-01b`/`ds-01c` 讲数组的"内存在哪、算的时候发生什么"；`ds-02b` 讲表格的"存储、对齐、分组"；本文件讲图形的"**画的时候按什么顺序做了什么、坐标怎么套、颜色怎么查、钱花在哪一步**"。三者共用的方法论只有一条——**先归因到层，再在层内解决**（回链 ds-02b B8 与卷 1 第 15 章）。

---

## 参考文献

**官方文档**

1. [Anatomy of a Figure](https://matplotlib.org/stable/gallery/showcase/anatomy.html) —— B1 的对象树与 B2 的坐标层对应关系。
2. [Transformations Tutorial](https://matplotlib.org/stable/users/explain/artists/transforms_tutorial.html) —— B2 四段链的权威说明。
3. [Artist Tutorial](https://matplotlib.org/stable/users/explain/artists/artist_tutorial.html) 与 [Lifecycle of a plot](https://matplotlib.org/stable/users/explain/quick_start.html) —— B1 的 draw/stale 与 pyplot 状态机。
4. [Performance](https://matplotlib.org/stable/users/explain/performance.html) —— B6 三个杠杆的官方建议（简化、分块、`LineCollection`）。
5. [Animations](https://matplotlib.org/stable/users/explain/animations/animations.html) 与 [Blitting](https://matplotlib.org/stable/users/explain/animations/blitting.html) —— B7 的最小重绘协议。
6. [Choosing Colormaps in Matplotlib](https://matplotlib.org/stable/users/explain/colors/colormaps.html) 与 [Colormap normalization](https://matplotlib.org/stable/users/explain/colors/colormapnorms.html) —— B5 的归一化家族与视觉语义。
7. [Custom ticking](https://matplotlib.org/stable/users/explain/axes/ticks.html) 与 [Axis units / categorical](https://matplotlib.org/stable/api/units_api.html) —— B3 的 Locator/Formatter 契约与单位接口。
8. [matplotlib 3.x What's New](https://matplotlib.org/stable/users/prev_whats_new/) —— 全部"版本注意"与 `buffer_rgba`/后端正则式注册表的原始清单。

**规范与工具**

9. [SOURCE_DATE_EPOCH](https://reproducible-builds.org/docs/source-date-epoch/) —— B4.5 中 PDF/EPS/SVG 可复现性的规范出处。
10. Hunter, J. D. (2007). *Matplotlib: A 2D graphics environment.* Computing in Science & Engineering, 9(3), 90–95. DOI: [10.1109/MCSE.2007.55](https://doi.org/10.1109/MCSE.2007.55) —— 对象树与后端抽象的原始设计动机。
11. Rougier, N. P., Droettboom, M., & Bourne, P. E. (2014). *Ten Simple Rules for Better Figures.* PLOS Computational Biology, 10(9), e1003833. DOI: [10.1371/journal.pcbi.1003833](https://doi.org/10.1371/journal.pcbi.1003833) —— 出版图的工程纪律（对应主章 3.15 的验收清单）。
12. [Agg 渲染器](https://agg.sourceforge.net/antigrain.com/) —— B6 光栅化成本与分块策略的下层实现。
13. [Datashader](https://datashader.org/) · [Plotly](https://plotly.com/python/) · [Bokeh](https://docs.bokeh.org/) · [Vega-Altair](https://altair-viz.github.io/) —— B8 生态边界表的能力依据。

**源码（3.11.2）**

14. `matplotlib/figure.py` —— B1.1 的 `Figure.draw`、B1.3 的 `_get_draw_artists`、B1.8 的 `apply_aspect` 调用点、B2.6 的 `SubplotParams`、B5.4 的 `Figure.colorbar`。
15. `matplotlib/axes/_base.py` —— B1.1 的 `Axes.draw`、B1.8 的 `viewLim`/`_unstale_viewLim`/`autoscale_view`、B2.8 的 `apply_aspect`。
16. `matplotlib/artist.py` —— B1.2 的 `stale` 回调与 `_update_props`、B1.6 的 `_api.define_aliases`、B1.7 的 `remove`、B7.1 的 `allow_rasterization`。
17. `matplotlib/transforms.py` —— B2 的 `CompositeGenericTransform`/`TransformWrapper`/`BboxTransformFrom`/`ScaledTranslation`/`dpi_scale_trans`。
18. `matplotlib/units.py` · `matplotlib/category.py` · `matplotlib/dates.py` · `pandas/plotting/_matplotlib/converter.py` —— B3 的 `ConversionInterface`、`UnitData`、`_SwitchableDateConverter` 与 pandas 的"临时换表"。
19. `matplotlib/backend_bases.py` · `matplotlib/backends/backend_agg.py` · `matplotlib/backends/backend_svg.py` —— B4 的 `print_figure`/`_is_saving`、B6 的分块、B4.5 的 `_make_id`。
20. `matplotlib/colors.py` · `matplotlib/cm.py` —— B5 的 `Normalize` 家族、`Colormap._lut`、`ColormapRegistry`。
21. `matplotlib/animation.py` —— B7 的 `FuncAnimation`、`Animation.save`、各 writer 与 `_is_saving` 设置。
22. `matplotlib/_pylab_helpers.py` · `matplotlib/cbook.py` —— B1.5 的全局 figure 注册表、B2.9 的 `Grouper`。
