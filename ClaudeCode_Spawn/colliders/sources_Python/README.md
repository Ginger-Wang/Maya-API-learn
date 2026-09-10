This project is a Python port of the excellent C++ library (https://github.com/azagoruyko/colliders/tree/main) developed by [Alexander Zagoruyko]. We heavily reuse their logic and algorithms under the terms of the Apache License 2.0.
# sources_Python

[`../sources`](../sources) 中 C++ 插件的 Python 重写版，基于 **Maya Python API 1.0**
(`maya.OpenMaya` / `maya.OpenMayaMPx`) 编写。不需要编译器、Visual Studio 和 CMake，
直接加载 `.py` 文件即可。

## 与 C++ 版最大的差异：输出真实网格，而不是视口绘制

C++ 版靠 `MPxDrawOverride` 把碰撞体画在视口里 —— 那些圆柱**不是场景物体**，
大纲视图里找不到，也不能选、不能上材质。

**API 1.0 没有 `MPxDrawOverride` 的 Python 绑定**（Viewport 2.0 那套可子类化的绘制类只
存在于 API 2.0），而 legacy `MPxLocatorNode.draw()` 在现代 Viewport 2.0 下并不可靠
（DirectX 11 和 Core Profile 严格模式下立即模式 OpenGL 直接失效）。

所以这个版本换了思路：**把几何作为网格/曲面数据输出出来**，接到普通 shape 上。
好处是完全绕开渲染引擎的限制，用 Maya 原生渲染 —— 能选、能上材质、能渲染，
半透明和深度排序都正常，性能也比立即模式好。

## 三个节点

`colliders_Node.py` 注册以下三个节点：

| 节点 | typeId | 形状由什么决定 | 输出 |
| --- | --- | --- | --- |
| `bellCollider` | `0x01023` | 属性（底/顶圈半径 + 矩阵） | `outputCurve`、`outputBellMesh`、`outputRingMesh` |
| `bellColliderMulti` | `0x01024` | **输入的控制曲线** | `outputBellMesh`、`outputRingMesh` |
| `skirtBellCollider` | `0x01025` | 六个关节矩阵 + ramp | `outputSurface`、`outputRingMesh` |

`bellCollider` / `skirtBellCollider` 与 C++ 版**同名**，所以 `scripts/colliders.py`
那个界面脚本可以直接沿用（它只认这两个节点类型）。
`bellColliderMulti` 是本 Python 版新增的节点，C++ 版没有对应实现。

三个节点都继承 `MPxLocatorNode`，所以 `createNode` 出来会自带一个 transform，
可以像 locator 一样在视口里选中和摆放。

### 接出来看

节点算出的是**数据**，不接到 shape 上是看不见的。手动接线：

```python
import maya.cmds as cmds

node = "bellCollider1"

# 网格输出 → mesh shape 的 inMesh
shape = cmds.createNode("mesh")
cmds.connectAttr(node + ".outputBellMesh", shape + ".inMesh")
cmds.sets(shape, edit=True, forceElement="initialShadingGroup")   # 否则是黑的

# 环的显示网格同理
ringShape = cmds.createNode("mesh")
cmds.connectAttr(node + ".outputRingMesh", ringShape + ".inMesh")
cmds.sets(ringShape, edit=True, forceElement="initialShadingGroup")
```

不同数据类型接的目标属性不一样：

| 输出类型 | 目标 shape | 目标属性 |
| --- | --- | --- |
| `kMesh`（`outputBellMesh` / `outputRingMesh`） | `mesh` | `.inMesh` |
| `kNurbsSurface`（`outputSurface`） | `nurbsSurface` | `.create` |
| `kNurbsCurve`（`outputCurve`） | `nurbsCurve` | `.create` |

网格和曲面输出（`outputBellMesh` / `outputRingMesh` / `outputSurface`）都设了
`writable=False` + `storable=False`：只出不进，且**不写进 `.ma`/`.mb`**。
几何每次求值都算得出来，存进场景只会让文件变大，还可能在改过代码后残留一份对不上的
旧结果。接出来的 shape 由节点驱动，直接改它们的形状没有意义。

> `outputCurve` 是个例外：它只设了 `setHidden(True)`（曲线数据在属性编辑器里没法
> 编辑，露出来只会碍事），没有设 writable / storable。脚本照样能 `connectAttr` 连它。

---

## `bellCollider`

C++ 版 `bellCollider` 的直接移植，外加一个 `outputRingMesh`。

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `bellMatrix` | matrix | 单位 | 钟形的世界矩阵，通常从 locator 的 `worldMatrix` 连过来 |
| `ringMatrix[]` | matrix 数组 | — | 碰撞环的世界矩阵，可接任意多个 |
| `bellSubdivision` | int | 16 | 钟形一圈的分段数，3..64 |
| `ringSubdivision` | int | 16 | **纯显示**，只决定 `outputRingMesh` 画得多圆，3..64 |
| `bellBottomRadius` | float | 0.8 | 底圈相对顶圈的半径比，`<1` 上宽下窄，`==1` 退化成圆柱 |
| `falloff` | float | 0 | 变形的**余弦阈值**，-1..1 |
| `collision` | float | 0 | 径向挤压强度，0..1 |

### 矩阵的语义约定（贯穿整个工程）

矩阵不只是位置和朝向，**轴的长度携带尺寸信息**：

- 平移（第 3 行）= 钟形底面圆心 / 环的中心
- **Y 轴（第 1 行）既是朝向，轴长又是高度**（环则是沿骨骼方向的长度）
- **X/Z 轴长 = 横向缩放**，即环的实际半径（环按基础半径 1 建模）

所以节点上没有单独的 height / radius 属性 —— 调尺寸靠**缩放那个 locator**。
求解器内部也依赖这一点：局部空间下钟形永远是"高 1、顶圈半径 1"的标准形状，
碰撞检测才能简化成"与单位球求交"。

### falloff 和 collision 是两套独立效果

| | 作用 | 关掉的方式 |
| --- | --- | --- |
| 倾斜避让 | 环顶进来时，钟形整体朝远离环的方向偏摆 | `falloff = 1` |
| 径向挤压 | 陷进环里的点沿径向被推到环表面 | `collision = 0`（默认） |

两者叠加生效。`falloff` 是拿"顶点方向 · 环方向"的**余弦**去比的阈值，不是距离：
`-1` = 整圈都受影响，`0`（默认）= 朝着环那半边受影响，越接近 `1` 影响范围越窄。

> **`collision` 调了没反应？** 挤压只在环**真的插进**钟形里时才有位移。
> 环与钟形恰好相切时判据不成立，怎么调都不会动。

---

## `bellColliderMulti`：用控制曲线驱动形状

和 `bellCollider` 的关键区别：**曲线是输入，不是输出。**

`bellCollider` 的钟形是算出来的（底圈半径 + 顶圈半径），用户只能通过属性间接影响。
这个节点反过来：场景里放 N 条控制曲线，**每条曲线就是钟形的一圈** ——

> 拖动曲线的 CV / 移动缩放曲线 → `outputBellMesh` 立刻跟着变形

形状完全由曲线决定，所以它**没有** `bellBottomRadius`，也没有 `bellScaleRamp`：
想要什么轮廓，直接把曲线摆成什么样。

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `inputCurve[]` | nurbsCurve 数组 | — | **输入**控制曲线，索引 0 是最底下那圈，依次往上 |
| `ringMatrix[]` | matrix 数组 | — | 碰撞环，语义同 `bellCollider` |
| `bellSubdivision` | int | 16 | 网格每圈采样多少个点，下限 3（软上限 64） |
| `ringSubdivision` | int | 16 | 纯显示 |
| `falloff` | float | 0 | 同 `bellCollider` |
| `collision` | float | 0 | 同 `bellCollider` |

**曲线负责形状，`bellSubdivision` 负责精度**，两者互不干涉：曲线上放几个 CV 只影响
手动调整的自由度，网格每圈有多少个点由 `bellSubdivision` 说了算。节点沿曲线**等弧长**
采样，所以曲线被 rebuild 过、参数化不均匀也不影响采样点分布，各条曲线的 CV 数
也不必相同。

> degree 1 的折线曲线本身没有曲率，把 `bellSubdivision` 调高只会在直边上多插点，
> 轮廓不会变圆滑。想靠细分变平滑，控制曲线要用 degree 3。

### 连曲线时注意坐标空间

`inputCurve` 要接曲线 shape 的 **`worldSpace[0]`**，不是 `local`。
transform 已经烘进 `worldSpace` 的曲线数据里了；接 `local` 的症状是
"曲线看着没动，mesh 却飞到原点附近"。

```python
cmds.connectAttr("curveShape1.worldSpace[0]", node + ".inputCurve[0]")
cmds.connectAttr("curveShape2.worldSpace[0]", node + ".inputCurve[1]")
```

`inputCurve` 和 `ringMatrix` 都是数组属性，连线时要**写明索引**。
`inputCurve` 的索引即层序，索引 0 是最底下那圈。

### 碰撞求解完全复用求解器

顶点布局是 `[中心, 圈0, 圈1, …, 圈N]`，与 `bellCollider` 刻意保持一致，
所以求解器一行都不用改：它的变形循环正好从 `bellSubdivision + 1` 开始
（跳过中心点和最底下那圈，也就是"腰"固定不动），中间各圈自动全部参与碰撞。

> **`outputBellMesh` 是碰撞后的结果，而控制曲线是输入、不受碰撞影响。**
> 所以环顶进来时 mesh 会被推开、曲线留在原处 —— 这是控制器的正常表现。

---

## `skirtBellCollider`

最完整的那个节点：把裙子拆成 N 段钟形逐层求解，再放样成一张 NURBS 曲面。
整体是四步流水线：**量身 → 造环 → 逐层求解 → 拼曲面**。

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `bellMatrix` | matrix | 单位 | 腰部矩阵：裙子的起点和朝向 |
| `leftHipMatrix` 等 6 个 | matrix | 单位 | 左右各 髋 / 膝 / 踝，用来量腿长、造碰撞环 |
| `skirtType` | enum | `Long`(1) | `Short`(0) / `Long`(1) |
| `height` | float | 1.0 | 裙长，0.01..1.0 |
| `ringScale` | float3 | (0.5, 1, 0.5) | X/Z = 环半径（腿的粗细），Y = 沿骨骼长度的倍率 |
| `bellScale` | float3 | (0.8, 1, 0.8) | X/Z = 裙子胖瘦，Y = 每层高度的倍率 |
| `bellSubdivision` | int | 16 | 决定曲面 U 方向 CV 数（`+3`）和 knot 数（`+5`），3..64 |
| `ringSubdivision` | int | 16 | 纯显示 |
| `falloff` | float | 0.0 | 同前 |
| `collision` | float | **1.0** | 同前；这里默认全开 |
| `tightness` | float | 0.5 | 见下 |
| `bellScaleRamp` | ramp | — | 沿裙子**高度**的半径倍率曲线 |
| `leftRingAxis` | enum | `X`(0) | 左腿环的横向轴 |
| `rightRingAxis` | enum | `-X`(3) | 右腿环的横向轴（与左腿镜像） |
| `bellAxis` | enum | `Y`(1) | 裙子沿腰关节的哪根轴往下长 |

### `bellScaleRamp` 沿高度采样，不是沿角度

参数 `0` = 腰，`1` = 裙摆，值就是该高度处的半径倍率（`1` = 不缩放）。
采样点用**真实距离比例**而不是层序号 —— 各层高度并不相等，用序号会让 ramp
在视觉上被拉歪。

ramp 的默认条目**建不在 `initialize` 里**（条目属于节点实例的数据），由
`postConstructor` 补；Maya 之后还会自己再插一条默认斜坡，两者冲突时用
`resetBellScaleRamp()` 清干净。

### `tightness` 的方向与直觉相反

| 值 | 效果 |
| --- | --- |
| `0` | **蓬松** —— 额外用一根"加长版膝盖环"把裙摆撑开 |
| `1` | **贴腿** —— 只受"髋→踝"那根环约束 |

那根加长环方向瞄膝盖、长度却取整条腿长，是从髋部沿大腿方向捅出去、一直伸过膝盖的
一根长柱。它是 `tightness` 的内部手段，所以**故意不出现在 `outputRingMesh` 里**。

`tightness` 只对**长裙**生效，`skirtType = Short` 时调它没有任何反应。

### 环是"整段骨头"，不是骨头上的一个圈

大腿环 = 髋→膝这一整段（Y 轴长 = 大腿长），长裙还会额外造"髋→踝"的整腿环。
所以 `ringAxis` **不要**选成沿骨骼方向的那根轴 —— 会撞上环矩阵构造里的
180 度反向退化分支。

> **裙子从原点被拉出去很远？** `bellMatrix` 没连接时默认是单位矩阵，腰会落在
> 世界原点。节点检测到"腰到髋的距离 > 整条腿长 × 2"时会 `displayWarning`
> 提示，不必靠看视口猜。

---

## 求解器可以脱离节点单独跑

`bellColliderSolver.py` 里的 `BellColliderSolver` 全是 `@staticmethod`，不持有状态、
不碰 `dataBlock`，输入输出都走两个普通结构体：

```python
from bellColliderSolver import BellColliderInputs, BellColliderOutputs, BellColliderSolver

inputs = BellColliderInputs()
inputs.bellMatrix = ...       # om.MMatrix
inputs.ringMatrices = [...]   # [om.MMatrix, ...]
inputs.bellSubdivision = 16
inputs.collision = 0.5

outputs = BellColliderOutputs()
BellColliderSolver.solve(inputs, outputs)
# outputs.outputBellMeshData / outputs.outputCurveData 是 mesh / 曲线数据对象
```

`solve` 是完整流程（造基础网格 → 逐环变形 → 融合 → 抽轮廓曲线）。
如果网格不是标准两圈锥台（例如 `bellColliderMulti` 那样由曲线拼出来的），
可以跳过 `solve`、只借用中间两步：

- `deformPoints(inputs, baseBellPoints, bellPlane)` —— 每个环独立变形一份，
  返回 N 份点集
- `averageDisplacements(bellSubdivision, baseBellPoints, bellPointsList)` ——
  把 N 份融合成一份

**多环融合的规则值得知道**：位移的**方向**取加权平均（权重是各位移长度的平方占比，
用平方是让推得狠的环主导方向），但**长度取最大值、不做平均**。
若长度也平均，两个环从相反方向夹住钟形时会互相抵消、看起来像没碰撞；
取最大值保证"至少满足挤得最狠的那个环"，不会穿模。

## 文件对应关系

| C++ | Python | 内容 |
| --- | --- | --- |
| `utils.hpp` | `utils.py` | `Plane`、`maxis`/`xaxis`/`yaxis`/`zaxis`/`taxis`、`findSphereLineIntersection`，以及一批 API 1.0 的 out-param 封装和踩坑封装 |
| `bellColliderSolver.h/.cpp` | `bellColliderSolver.py` | `BellColliderInputs`、`BellColliderOutputs`、`BellColliderSolver`（`makeBellMesh`、`makeRingsMesh`、`deformPoints`、`averageDisplacements`、`solve`） |
| `bellCollider.h/.cpp` | `bellCollider.py` | `bellCollider` 节点 |
| `skirtBellCollider.h/.cpp` | `skirtBellCollider.py` | `skirtBellCollider` 节点 |
| （本版本新增） | `bellColliderMulti.py` | `bellColliderMulti` 节点 —— 控制曲线驱动 |
| `main.cpp` | `colliders_Node.py` | `initializePlugin` / `uninitializePlugin` |
| — | `test_node.py` | 调试脚手架，见下 |

## 加载方式

```python
import maya.cmds as cmds
cmds.loadPlugin(r"<path_to_colliders>/sources_Python/colliders_Node.py")
```

`colliders_Node.py` 会在 `initializePlugin` 里先定位自身目录并加入 `sys.path`，
再导入同级模块，所以放在任何位置都能加载。定位顺序为
`__file__` → `MFnPlugin.loadPath()` → `cmds.pluginInfo` —— Maya 执行 `.py` 插件时
**不保证**定义 `__file__`（Maya 2025 就不定义），所以三条路都要留着；三条都失败时
直接抛异常，不静默继续。

卸载插件时会把同级模块从 `sys.modules` 中清除，因此**改完代码只要 unload / load
一次插件就能生效**，不必重启 Maya。（`sys.path` 里插入的那个目录故意不撤销。）

界面照旧（`colliders.py` 在 `scripts/` 目录下，不是 `colliders/` 根目录）：

```python
import sys
sys.path.insert(0, r"<path_to_colliders>/scripts")
import colliders
colliders.show()
```

> **注意模块重名。** `utils` 这类名字很通用。加载插件会把本目录插到 `sys.path[0]`，
> 如果你的环境里另有同名模块，两边都可能被顶替。真遇到冲突时，最简单的办法是把
> 本目录改放到一个独立位置，或者给这些文件加上项目前缀。

## ⚠️ 不要同时加载两个插件

Python 版的 `bellCollider` / `skirtBellCollider` 沿用了 C++ 版的**节点名**。
如果 `../plugins` 里编译好的插件已经加载，Maya 会拒绝重复注册同名节点 ——
请先卸载其中一个，再加载另一个。

## `test_node.py`

**调试脚手架，不属于正式插件**：`colliders_Node.py` 不注册它。
它是 `bellColliderMulti` 的单文件试验版（节点名 `Test_ColliderMulti`，
typeId `0x01022`，自带 `initializePlugin` / `uninitializePlugin`），
可以和正式插件同时加载、互不冲突。

它顶层就 `import utils` / `bellColliderSolver`、自己不做目录定位，
所以 `loadPlugin` 之前要先手动把本目录加进 `sys.path`：

```python
import sys, maya.cmds as cmds
sys.path.insert(0, r"<path_to_colliders>/sources_Python")
cmds.loadPlugin(r"<path_to_colliders>/sources_Python/test_node.py")
```

## 已删除 `drawColor` / `drawOpacity`

这两个属性在 C++ 版里控制 `MPxDrawOverride` 的绘制颜色。本版本没有视口绘制，
它们不影响任何显示，留着只会误导，所以**直接删掉了**。
外观请用 shape 上的材质来控制。

连带改了共用的 `scripts/AEbellColliderTemplate.mel`：那里的 "Draw Attributes" 分组
外面加了一层 `attributeExists` 判断，这样 C++ 版加载时照常显示这两个控件、
Python 版加载时自动隐藏 —— 一份模板两个版本都对。
两个 AE 模板也补了 `-suppress "outputRingMesh"`（suppress 不存在的属性是安全的）。

> **旧场景。** 用 C++ 版存的场景如果给 `drawColor` / `drawOpacity` 设过值，
> 用本版本打开时 Maya 会提示这两个属性找不到并丢弃它们的值。纯装饰属性，
> 丢了不影响绑定；但如果你给它们打过关键帧或做过连接，那些连接会断。

## 其它与 C++ 源码的差异

数学计算本身没有改动，以下差异都是 API 或 Python 语义导致的。

- **没有 TBB。** C++ 里虽然 include 了 `<tbb/parallel_for.h>` 但从未使用，所以没有任何功能损失。
  Python 求解器会明显慢于编译版本 —— 用于绑定和摆姿势没问题，重播放场景就吃力了。
- **拷贝必须显式写出。** Python 中 `MPointArray` 赋值是绑定引用，所以在 `deformPoints` 和
  `averageDisplacements` 里用 `utils.copy_points()` 代替 C++ 的拷贝构造。
- **新增 `lerp_point` / `midpoint` 辅助函数。** C++ 依赖 `MPoint`↔`MVector` 的隐式转换来写
  `p * w + q * (1 - w)` 这类表达式，Python 绑定不做这种转换，所以把运算展开写清楚。
  （`lerp_point` 刻意写成 `a*(1-t)+b*t` 而不是 `a+(b-a)*t`：前者在 `t=0/1` 时返回逐位
  精确的端点值，权重为 0 的顶点必须与原始顶点完全一致，否则网格会有细微抖动。）
- **状态码改为异常。** `MStatus`/`CHECK_MSTATUS` 变成普通 Python 异常；`compute` 对不处理的
  插槽返回 `om.kUnknownParameter`。
- **`wrapParam`** 按原样保留为 `_wrapParam`；和 C++ 里一样，它并未被使用。
- **`utils.py` 里有一批当前无调用点的函数**（`clamp`、`mscale`、`set_mscale`、
  `scaled_color`、`mesh_triangles`、`surface_cvs`、`RAD2DEG`/`DEG2RAD`），保留是为了与
  `utils.hpp` 逐项对应。其中 `scaled_color` / `mesh_triangles` 对应 C++ 的视口绘制，
  Python 版没有实现那部分。

### API 1.0 特有的几个坑（都封装在 `utils.py` 里）

| 用途 | API 1.0 写法 |
| --- | --- |
| 读矩阵元素 | `mat(row, col)`，**没有** `getElement` |
| 写矩阵元素 | `MScriptUtil.setDoubleArray(mat[row], col, v)` → `set_maxis()` |
| 从列表建矩阵 | `MScriptUtil.createMatrixFromList()` → `matrix_from_rows()`（部分版本会**静默失败**，所以内部带自检和逐元素回退） |
| 从 dataBlock 取矩阵 | `asMatrix()` 返回的是**内部引用**、临时 handle 一出语句就悬空 → 必须立刻拷贝，用 `input_matrix()` |
| 读 3 分量属性 | `dataBlock` 那条路会读到垃圾值（`createPoint` 的子属性是 float，`asDouble()` 按 8 字节读会串到相邻属性）→ 必须走 `plug_vector()` |
| 建 3 分量属性 | 必须 `createPoint()`；`create(..., k3Double)` 之后 `setDefault(x,y,z)` 会抛 kInvalidParameter。且**每个属性要用独立的 function set** → `create_numeric3()` |
| 数组长度 / 写元素 | `arr.length()` / `arr.set(v, i)`，**不是** `len()` / `arr[i] = v` |
| `float * MVector` | **不可用**（没有 `__rmul__`），一律写成 `MVector * float` |
| 取网格点 / 三角面 | out-param：`getPoints(arr)` / `getTriangles(c, i)` → `mesh_points()` / `mesh_triangles()` |
| 取曲面 CV | out-param：`getCVs(arr, space)` → `surface_cvs()` |
| 渐变曲线取值 | out-param + MScriptUtil float 指针 → `ramp_value_at()` |
| `MFnMesh.create` | 需要显式传顶点数和面数；顶点为空时会报错（`buildMeshData` 会返回空数据对象兜底） |
| `numVertices` / `numCVsInU` | 是**方法**，要带括号 |
| `MColor` | `MColor(r, g, b, a)` 位置参数，不是元组 |
| 属性设置 | `setKeyable(True)` / `setHidden(True)`，不是属性赋值 |
| 数组插槽按物理索引 | `jumpToArrayElement(i)`（`jumpToElement` 是逻辑索引） |

> `utils.py` 里的 `CODE_REVISION` 常量：改动那个文件时顺手 +1。诊断时打印它，可以确认
> Maya 里跑的到底是不是磁盘上的最新代码 —— 插件重载不彻底时 `sys.modules` 里可能还留着
> 旧模块，表现就是"明明改了却没效果"。
