# brushTipCurve —— Maya 笔刷笔尖压弯曲线节点

把「毛笔压在纸上」做成一次 DG 求值:给一张纸/地面 mesh,再用两个(或更多)定位器标出笔杆朝向,节点直接输出**一条已经压弯的刷毛曲线**和**一个对应类型的笔刷实体 mesh**。

- 四种笔刷:毛笔 / 绘画笔 / 毛刷 / 扇形笔,各自的截面和廓形不同
- 刷毛**长度固定**,压下去只会弯不会变长
- 只要毛够得着纸面就**自动弯曲**,不需要调任何参数
- 压下去贴地那一段会**散开变宽、压扁**,笔画跟着变粗

典型用途:毛笔/画笔绑定、笔尖接触地面的形变、拿 `outPressure` 驱动笔迹宽度和墨色浓度。

---

## 文件

| 文件 | 说明 |
|---|---|
| [brushTipCurveNode.py](brushTipCurveNode.py) | 插件本体。单文件,只依赖 Maya Python **API 1.0** |
| [brush_utils.py](brush_utils.py) | 纯 `cmds` 的搭建函数 + 笔刷类型预设 |
| [AEbrushTipCurveTemplate.mel](AEbrushTipCurveTemplate.mel) | 属性编辑器模板,在 AE 里切换类型时自动套推荐手感 |
| [example_setup.py](example_setup.py) | 一键演示场景,跑完直接拖着玩 |
| [selftest.py](selftest.py) | mayapy standalone 自测,102 项数值断言 |

---

## 快速开始

一键演示:

```python
import sys; sys.path.append(r"H:/DBackUp/EFBack/F/VS-Code_Project/ClaudeCode_Spawn/MayabrushNode")
import example_setup
example_setup.build()
```

拖动红色的 `brush_root` 往下压,曲线就会自动在接触处弯折、笔尖沿纸面铺开。绿色的 `brush_tip` 只管朝向,拖多远毛都是那么长。

自己搭:

```python
import brush_utils
paper = cmds.listRelatives("pPlane1", shapes=True)[0]
rig = brush_utils.build_brush(mesh=paper,
                              root_pos=(0, 0.35, 0),    # 毛根 = 笔杆与刷毛连接处
                              tip_pos=(0.3, -0.85, 0),  # 只决定朝向
                              bristle_length=1.2,       # 不填就按初始间距量一次
                              brush_type="flat")        # 毛刷
```

换笔刷类型(顺带套上该类型的推荐手感):

```python
brush_utils.set_brush_type(rig["node"], "calligraphy")        # 换类型 + 套手感
brush_utils.set_brush_type(rig["node"], "fan", apply_feel=False)  # 只换廓形
```

要在**属性编辑器**里切换类型也能自动套手感,先 source 一次模板:

```mel
source "H:/.../MayabrushNode/AEbrushTipCurveTemplate.mel";
```

(或者把这个目录加进 `MAYA_SCRIPT_PATH`,Maya 会自己找到。)

纯手工接线的话,四个地方别接错:

> **mesh 要连 `worldMesh[0]`,不是 `outMesh`** —— 连错的话纸一被移动,碰撞位置就不对了。
> **定位器要连 `worldMatrix[0]`,索引 0 是毛根、最大索引是笔尖朝向** —— 顺序反了毛就倒着长。
> **`bristleLength` 要填上** —— 留 0 的话毛长会跟着定位器间距跑,拖笔尖往纸里压的同时毛也在变长。
> **输出曲线的 transform 要把 `worldInverseMatrix[0]` 连回节点的 `parentInverseMatrix`** —— 不接的话曲线 transform 一旦不在原点,整条毛会整体偏移。

```python
cmds.connectAttr(paper + ".worldMesh[0]",        node + ".inMesh")
cmds.connectAttr(rootLoc + ".worldMatrix[0]",    node + ".controlMatrix[0]")
cmds.connectAttr(tipLoc  + ".worldMatrix[0]",    node + ".controlMatrix[1]")
cmds.connectAttr(node + ".outCurve",             curveShape + ".create")
cmds.connectAttr(curveXform + ".worldInverseMatrix[0]", node + ".parentInverseMatrix")
```

想看到实体的毛,给输出曲线挂一个 sweep mesh(`Create > Sweep Mesh`)或者 extrude 即可,再把 `outPressure` 连到 sweep 的 taper 上,压得越深笔迹越粗。

---

## 属性

| 属性(长名 / 短名) | 类型 | 默认 | 说明 |
|---|---|---|---|
| `inMesh` / `im` | mesh | — | 纸张/地面,连 `worldMesh[0]` |
| `controlMatrix[]` / `cmx` | matrix 数组 | — | 定位器 `worldMatrix[0]`,索引升序 = 毛根 → 笔尖朝向 |
| `bristleLength` / `bln` | double | 0.0 | **毛长,固定不变**。留 0 则退回用定位器间距(那样拖笔尖会改变毛长) |
| `stiffness` / `stf` | double 0–1 | 0.35 | **毛硬度**。1=硬毛弯成均匀圆弧、贴地段短;0=软毛上段直末端急弯、躺得长 |
| `envelope` / `env` | double 0–1 | 1.0 | 效果开关。0 = 完全不弯,回到定位器连成的自然形状 |
| `samples` / `smp` | int 6–400 | 24 | 输出曲线的 CV 数 |
| `curveDegree` / `cdg` | enum | cubic | `linear`(1)/ `cubic`(3) |
| `contactOffset` / `cof` | double | 0.0 | 沿法线抬离表面,防和纸面 z-fighting |
| `conformToSurface` / `cts` | bool | on | 贴地段逐点吸附到真实表面。纸是平的时无所谓,地面起伏时必须开 |
| `parentInverseMatrix` / `pim` | matrix | 单位阵 | 把结果转回曲线的本地空间 |
| `brushType` / `bty` | enum | calligraphy | 笔刷类型,决定截面和廓形。见下节 |
| `brushWidth` / `bwd` | double | 0.08 | 毛束基础半径,线性缩放整个截面 |
| `meshSides` / `msd` | int 3–64 | 8 | 截面一圈几个点 |
| `spreadByPressure` / `spp` | double | 0.8 | 贴地段横向散开量。满压时宽度变 1.8 倍 |
| `flattenByPressure` / `flp` | double 0–1 | 0.5 | 贴地段压扁量。满压时厚度减半 |

| 输出 | 类型 | 说明 |
|---|---|---|
| `outCurve` / `ocv` | nurbsCurve | 压弯后的刷毛曲线 |
| `outMesh` / `omh` | mesh | 笔刷实体,直接连到 `mesh` 节点的 `inMesh` |
| `outPressure` / `opr` | double | 贴地长度占毛长的比例 0–1。驱动笔迹宽度、墨色浓度 |
| `outContact` / `oct` | bool | 笔尖是否接触到纸面 |
| `outContactPoint` / `ocp` | double3 | 落纸点坐标,与 `outCurve` 同一空间 |

---

## 笔刷类型

`brushType` 决定截面形状和粗细廓形,`outMesh` 按它扫掠出实体:

| 类型 | 截面 | 廓形(根 → 尖) | 推荐硬度 | 用途 |
|---|---|---|---|---|
| `calligraphy` 毛笔 | 圆 | 根部饱满,一路收成锥尖 | 0.20 | 书法、水墨 |
| `round` 绘画笔 | 圆 | 大部分等宽,末端圆润收头 | 0.50 | 水彩、油画圆头笔 |
| `flat` 毛刷 | 扁 4:1 | 等宽到底,末端平切 | 0.80 | 平头刷、宽笔画 |
| `fan` 扇形笔 | 扁 5.5:1 | 越往尖端越宽、越薄 | 0.65 | 树枝、头发、纹理 |

```
毛笔 calligraphy        绘画笔 round         毛刷 flat          扇形笔 fan
 ████████████▄▄▄         ██████████████▄      ███████████████    ▄▄████████
 ██████████████▄▄▄▄      ███████████████      ███████████████   ███████████
 ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀      ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀    ▀▀████████
```

**扁笔的宽面朝向**由笔杆矩阵的局部 X 轴沿曲线平行传输得到 —— 转笔杆就能转刷子朝向。这和垂直下压时决定倒向用的是同一根轴,不会各转各的。

**推荐硬度只是起点,不锁定。** DG 节点的 `compute` 不允许回写自己的输入属性(会造成循环求值),所以「选了类型就有对应手感」这件事由 `brush_utils.set_brush_type()` 和 AE 模板在 UI 层代劳:切换类型时填一次,填完之后你调成多少就是多少,直到下次再换类型。

### 压力散开

压下去之后,贴在纸上那一段会横向散开、纵向压扁,散开量由 `outPressure` 驱动:

```
half_width     *= 1 + spreadByPressure  × pressure
half_thickness *= 1 - flattenByPressure × pressure
```

只作用在落纸点之后,并且用几个采样点平滑过渡 —— 整根一起变粗的话笔杆连接处会跟着鼓起来,不过渡的话接触点会突然粗一圈、像套了个箍。

---

## 原理

刷毛被当成一根**不可伸长**的弹性杆,总弧长恒等于定位器之间的距离。压到纸面时分成两段:

```
        笔杆
         ●  B
          \
           \          空中段 sAir:俯角 phi 从 alpha 单调衰减到 0,
            \_        到达纸面时恰好与纸面相切
    ━━━━━━━━━━●━━━━━━━━━●  笔尖
                贴地段 L - sAir:沿切向平铺
```

```
phi(s) = alpha * (1 - s/sAir) ** p        s 是从毛根量起的弧长
h      = ∫ sin(phi(s)) ds                 毛根到纸面的垂直高度
sAir   = h / I(alpha, p)                  I 就是上式的归一化积分
```

关键在于 **sAir 由 h 和 alpha 唯一确定,不是一个可调参数**。这让两条性质成为模型的内在保证,而不是靠事后 clamp 兜出来的:

- **不穿透** —— 空中段高度随 s 单调下降(`dh/ds = -sin(phi) <= 0`),终点恰好落在纸面上;贴地段始终贴着纸面
- **弧长守恒** —— 空中段逐步沿单位方向积分,长度精确等于 sAir;加上贴地段 `L - sAir` 正好是 L

### 自动弯曲

**只要毛够得着纸面就一定会弯**,不需要手动调任何东西。判据就一条:

```
毛长 L > 毛根到纸面的直线距离 h / sin(alpha)   ->  接触
```

麻烦在于弯曲比走直线需要**更长**的弧长,所以按设定硬度算出来的 `sAir` 可能超过毛长 —— 毛明明够得着纸面,却「弯不过去」。这时候节点不会放弃,而是二分解出一个更软的有效硬度,让毛恰好弯到纸面(贴地段长度为 0):

| 状态 | 行为 |
|---|---|
| `sAir(设定硬度) <= L` | 毛有富余,设定硬度完全生效,多出来的长度躺在纸上 |
| `sAir(设定硬度) > L` 但够得着 | **自动放软**到刚好够,贴地段为 0,`outPressure = 0` |
| 够不着 | 不接触,保持直线 |

物理上也说得通:刚接触时毛是绷紧的,压深了才有余量按自己的软硬程度弯。实际效果是浅压时调 `stiffness` 看不出变化,压深之后才逐渐显现。

没有这一步的话,硬毛会出现「笔尖明明扎到纸下面了,毛却还是直的,得手动把硬度调低才弯」——正是要去掉的手动陷阱。

### 硬度

`stiffness` 映射到指数 `p`,落在 `(0, 1]`:

| stiffness | p | 形状 | sAir | 贴地段 |
|---|---|---|---|---|
| 1.0(硬毛) | 1.0 | 俯角线性衰减,整根弯成均匀圆弧 | 大 | 短 |
| 0.0(软毛) | 0.35 | 上段几乎保持笔杆方向,临近纸面才急弯 | 小 | 长 |

**p 不能大于 1**。这是实现时踩的坑:p > 1 会让俯角一出根就衰减到 0,毛立刻弯平然后水平滑行 —— 而水平滑行是不降高度的,结果怎么压都落不到纸面(实测 `stiffness <= 0.5` 全部判定为不接触)。真实软毛恰恰相反:上段直、末端急弯,对应 p < 1。

### 为什么弯曲发生在接触**之前**

直觉上会想「从接触点开始往后弯」,但那样在接触点处方向仍然是向下的入射角,积分出来会先扎进纸面再抬起来,必须靠 clamp 兜,而 clamp 会破坏弧长守恒。物理上正确的是:刷毛在**空中**就已经被压弯,到达纸面时是相切的,然后才沿纸面铺开。

---

## 自测

```bash
"H:/Program Files/Autodesk/Maya2025/bin/mayapy.exe" selftest.py
```

已在 Maya 2025 跑通 **107/107**。覆盖:

- 悬空时是直线、首尾精确落在定位器上、共线性 5.9e-17
- 弧长守恒:25 组压深 × 硬度组合,最大误差 **1.2e-07**
- 不穿透:15 组组合,最低点 **-7.8e-17**
- 落纸相切、贴地段共面
- 硬度单调性(0.4342 → 0.6000)、压深单调性(0.5082 → 0.9201)
- **固定毛长**:笔尖定位器放在 0.8 和 2.6 两处,曲线完全一致(差 4.5e-08),长度恒 1.200000
- **自动弯曲**:毛长 1.2 垂直下压,高度 ≥1.2 判不接触、<1.2 全部接触,`outPressure` 单调
- **自动放软**:浅压到硬毛弯不下去的高度,扫遍 `stiffness` 每一档都接触且长度不变
- `envelope=0` 精确退化成直线
- 扫过垂直只翻转一次且恰在垂直处,近垂直时倒向不抖
- 转笔杆 `rotateY` 90°/180°,倒向精确跟随
- 三定位器过点插值(偏差 0.003)、压弯前后弧长守恒
- 倾斜 30° 的纸面、起伏地面上的 `conformToSurface`(关掉时陷进坡里 0.188,开启后 0.000)
- `parentInverseMatrix` 还原世界位置(误差 9.9e-16)
- **mesh 拓扑**:顶点数 = `samples × meshSides`、面数 = `(samples-1) × meshSides + 2`,`brushWidth=0` 时拓扑不变
- **法线朝外**:四种类型的每一个侧壁面,法线与径向点积恒 > 0(毛刷 0.35,扇形笔 0.06)
- **四种廓形**:毛笔收到根部的 15%、绘画笔中段仍 98% 饱满、毛刷首尾等宽且宽:厚 = 4:1、扇形笔尖端是根部的 2 倍宽
- **mesh 贴合曲线**:每圈截面重心落在对应 CV 上(误差 7.5e-09)
- **压力散开**:笔尖环 0.160 → 0.261 单调变宽,毛根环始终不动;归零参数后回到原截面
- **宽度线性**:`brushWidth` 翻倍则每一圈直径翻倍(误差 0)
- **扁笔朝向**:笔杆 `rotateY` 90°,宽面轴从 X 精确转到 Z
- **UV**:数量 = `samples × (meshSides+1)`,u/v 各铺满 0-1,每个面都分到 UV face
- **预设同步**:MEL 模板和 `brush_utils.BRUSH_PRESETS` 四种类型逐项一致
- 退化输入:没连 mesh / 只有一个定位器 / 定位器重合 / 毛根在纸下 / `samples` 取边界 —— 均不崩溃、不出 NaN

---

## 踩过的坑

### 1. 连了 `worldMesh[0]`,拿到的点却是局部坐标

这是最容易把整个碰撞做错的地方。mesh data object 自带一个变换矩阵,**点数据永远是局部的**,世界变换藏在那个矩阵里。

```python
fnMesh.closestIntersection(src, dir_, om.MSpace.kObject, ...)   # 错：静默给出错误位置
fnMesh.closestIntersection(src, dir_, om.MSpace.kWorld,  ...)   # 对
```

传 `kObject` 不会报错,只会安静地算错。节点里所有 `MFnMesh` 调用一律走 `kWorld`。

### 2. API 1.0 的射线求交靠输出参数,读回要带 ptr

1.0 的 `closestIntersection` 返回 `bool`,命中结果全从输出参数带出来,`float` / `int` 必须用 `MScriptUtil` 包一层:

```python
hitPoint  = om.MFloatPoint()
paramUtil = om.MScriptUtil(0.0); paramPtr = paramUtil.asFloatPtr()
faceUtil  = om.MScriptUtil(0);   facePtr  = faceUtil.asIntPtr()
triUtil   = om.MScriptUtil(0);   triPtr   = triUtil.asIntPtr()

found = fnMesh.closestIntersection(
    om.MFloatPoint(ox, oy, oz), om.MFloatVector(dx, dy, dz),
    None, None, False, om.MSpace.kWorld, maxDist, False, None,
    hitPoint, paramPtr, facePtr, triPtr, None, None)

faceId = faceUtil.getInt(facePtr)      # 不是 faceUtil.getInt()
```

读回值时 **`getInt` / `getFloat` 要把 ptr 再传回去**。写成 `faceUtil.getInt()` 会报 `takes exactly one argument (0 given)` —— 看起来像少传了参数,其实是 ptr 忘了给。法线也是输出参数:`fnMesh.getPolygonNormal(faceId, normalVector, om.MSpace.kWorld)`。

### 2b. API 1.0 和 2.0 的同名东西,一个是方法一个是属性

两边代码互抄时这类差异不报错,只是**默默失效**:

| | API 1.0 | API 2.0 |
|---|---|---|
| 判断子 plug | `plug.isChild()` 方法 | `plug.isChild` 属性 |
| 判断有无输入连接 | `plug.isDestination()` 方法 | `plug.isDestination` 属性 |
| 设置属性特性 | `nAttr.setKeyable(True)` | `nAttr.keyable = True` |
| 数组元素个数 | `handle.elementCount()` | `len(handle)` |
| 跳到第 i 个元素 | `handle.jumpToArrayElement(i)` | `handle.jumpToPhysicalElement(i)` |
| compute 不处理时返回 | `om.kUnknownParameter` | `None` |

最阴的是前两行:1.0 里漏写括号,拿到的是**方法对象**,布尔判断永远为真。

### 3. knot 个数是 `numCVs + degree - 1`

不是教科书的 `numCVs + degree + 1`。Maya 省掉了首尾各一个,数量不对直接抛 `kInvalidParameter`。degree=3、8 个 CV 时是 10 个:`[0,0,0, 1,2,3,4, 5,5,5]`。

另外 CV 少于 `degree + 1` 时公式会退化,只有两三个定位器时必然遇到,要补重复的末点顶上。

### 4. `maxParam` 是射线参数,不是距离

单位是 `|rayDirection|`。方向没归一化就会提前 MISS —— 表现为碰撞时好时坏,极难查。一律先归一化,`maxParam` 才等于世界单位距离。

### 5. 断开 mesh 之后,datablock 里还留着旧几何

`asMesh().isNull()` 这时候返回的是 `False`,照用的话笔刷会和一张已经不存在的纸发生碰撞。要先查连接:

```python
if not om.MPlug(self.thisMObject(), attr).isDestination:
    return None      # 没有上游连接 -> 忽略残留数据
```

### 6. 笔杆扫过垂直时笔尖会换边,这个消不掉

一开始想用 smoothstep 在「真实倾斜方向」和「笔杆 X 轴回退方向」之间混合来抹平跳变,但线性混合两个**相反**的向量会在权重 0.5 处经过零向量,跳变只是被挪到了一个由阈值决定的、毫无道理的角度上。

根子在于:真实毛笔垂直下压时是向四周均匀散开的(所以垂直下压得到一个圆点笔触),而单条中轴曲线没法表示「四周散开」,它必须选一边,左右倾之间必然翻 180°。

所以现在不追求消除跳变,只保证它落在**唯一讲得通的位置**——正垂直那一刻。做法是先把回退方向翻到与倾斜方向同侧再混合,夹角恒 ≤ 90°,混合结果不会中途退化。副作用是笔接近垂直时倒向被笔杆 X 轴锁住,不会被浮点噪声来回抖。

### 7. 自动放软时不能把 `sAir` 夹到毛长了事

判断「毛够不够按设定硬度弯」用的是 64 步粗积分,而实际出点用的是 `n_air` 步 —— 两者会得出不同结论。初判说够、重算说不够时,如果图省事把 `sAir` 夹到 `0.98 * L`,落点就**悬在空中**,后面的贴地段接着水平铺出去,再被 `conformToSurface` 一把拽回纸面,折线凭空变长。

表现是弧长守恒只在某一两档 `stiffness` 上破掉(实测 `stiffness=0.25` 时长度 1.2001322 而不是 1.2),看起来像随机的浮点问题,其实是分支判据前后不一致。正确做法是重算后发现不够就**退回自动放软**,让空中段走满全长,把二分残差转移到末端高度上(1e-8 量级的离地误差),长度严格守恒。

---

### 8. `polygonConnects` 索引越界会直接崩掉 Maya,而且抓不住

这是生成 mesh 最危险的一条。`MFnMesh.create()` 拿到越界索引**照样返回成功**,然后 Maya 会在之后某一次访问这个 mesh 时 Fatal Error —— 没有 Python 异常、`try/except` 拦不住、整个进程连同未保存的场景一起没。

所以必须在交给 `create()` 之前自己查一遍:

```python
if connects and (max(connects) >= rings * sides or min(connects) < 0):
    return mesh_data      # 宁可输出空 mesh，也不能把 Maya 搞崩
```

节点把这个检查放在拓扑缓存里,只在 `(rings, sides)` 变化时查一次,不影响每帧开销。

相关的两条:
- **同一个面里出现重复顶点索引会静默丢面**,而且后面所有面的索引整体前移一位 —— 不报错、不警告。注意区分:几何上重合但索引不同的顶点是安全的(锥形笔尖收口就靠这个)。
- **`numVertices` / `numPolygons` 直接写 `array.length()`**,别用公式另算,对不上是 `kInvalidParameter`。

### 9. 程序化 mesh 的法线不用管

`MFnMesh.create()` 出来的网格**默认就是全软边**,顶点法线已经是相邻面的平均值,渲染出来就是光滑的管子。`setVertexNormals` / `setFaceVertexNormals` / `updateSurface()` / 下游接 `polySoftEdge` —— 这些全都不需要,是白花时间。

只有想要硬边时才需要动手,而且那时 `getVertexNormal()` 在 mesh-data 上返回的还是旧的平均值(函数集缓存不刷新),要用 `isEdgeSmooth()` 验证。

### 10. `MFnMesh.create()` 省掉 `parentOrOwner` 会往场景里漏东西

省了它调用照样"成功",但会凭空建出一个 transform。在 compute 里这么写就是每帧漏一个节点。

顺带两个查询上的坑:`MFnMesh.boundingBox()` 在 mesh-data(非 DAG)上抛 `kFailure`;`polyEvaluate` 的 `uvComponent` 标志量的不是 UV 个数,对这个 mesh 一律返回 0 —— 拿它做断言会误判成"没建 UV",要用 `MFnMesh.numUVs()`。

---

## 已知限制

- **笔尖定位器不再定位毛尖**(填了 `bristleLength` 之后)。它只决定笔指向哪儿,实际毛尖落在「毛根沿该方向走一个毛长」的地方。想让毛尖精确跟随定位器,把 `bristleLength` 留 0 即可,代价是拖动它会改变毛长。
- **浅压时调 `stiffness` 看不出变化**。毛刚够到纸面时是绷紧的,有效硬度被自动放软接管;要等压深到有富余,设定的硬度才开始生效。
- **接触时中间定位器的影响会减弱**。压弯段是从「毛根位置 + 毛根方向 + 总长」解析重建的,三个以上定位器摆出的中间造型只通过总弧长参与。两个定位器(主要用法)不受影响;悬空时中间定位器完全生效。
- **只处理接触前的空中段弯曲,笔杆段不受力回弹**。真实硬毛压下去会整根向后弓,这里毛根的位置和方向完全由定位器说了算。
- **单条曲线代表整束毛的中轴**,不做毛束散开。垂直下压的圆点笔触、飞白这些要靠多套笔刷或下游处理。
- **毛根已经在纸面下方**(整根倒插)时检测不到接触,按不接触处理。
- `conformToSurface` 开启时,贴地段吸附会轻微改变总长,**严格的弧长守恒只在平面上成立**。
- `curveDegree = cubic` 时曲线不插值中间 CV,**曲线的实际弧长会略小于** CV 折线长度(也就是略小于毛长)。要严格的长度就用 `linear`。
- **`outMesh` 是单根毛束的实体,不是一根根分开的毛**。飞白、毛束散开这类效果要靠贴图或下游处理。
- **扇形笔在大压力下侧壁面会很斜**(法线与径向的点积低到 0.06),仍然朝外、不会内翻,但如果要做高精度的法线烘焙,建议把 `meshSides` 提高一些。
- `outCurve` 和 `outMesh` 共用同一个 `parentInverseMatrix`,所以**两者必须挂在同一个 transform 下**(`build_brush` 已经这么做了)。各给一个 transform 且位置不同的话,毛和曲线会错开。
