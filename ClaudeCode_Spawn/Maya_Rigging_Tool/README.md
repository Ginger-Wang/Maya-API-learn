# 可变 FK 绑定工具（Variable FK Rig · Maya）

复刻参考视频里那套"可变 FK / 触手"绑定工具：几个控制器浮在一条密集的骨骼链上，
每个控制器把自身旋转的一部分分摊给衰减范围内的骨骼。因为骨骼是真实的父子层级，
这些分摊值会逐节累加，于是链条围着控制器平滑地拱起来，而不是在某一节上硬折。

思路由 **Cameron Black** 提出并推广，视频演示作者为 **Jonah Reinhart**。
https://www.youtube.com/watch?v=2SljVRrWDVI
本工具是独立的节点化实现。

---

## 安装

**拖拽安装：** 把 [install.py](install.py) 拖进 Maya 视口即可。它会把本目录加进
`sys.path`，在用户 scripts 目录写一个 `.pth` 文件（重启后依然有效），
并在当前 shelf 上放一个 `VarFK` 按钮。

**手动安装：** 把本目录加到 `PYTHONPATH` / `MAYA_SCRIPT_PATH`，然后：

```python
import variableFK
variableFK.show()
```

只依赖 `maya.cmds` 和 `maya.api.OpenMaya`，Maya 2018–2026 通用，不依赖 PySide。

---

## 界面说明

| 控件 | 作用 |
| --- | --- |
| **命名前缀** | 所有新建节点的前缀。只支持英文数字下划线，其它字符会被自动替换成 `_`。 |
| **控制器数量** | 创建几个浮动的可变 FK 控制器。 |
| **绑定骨骼数量** | 沿曲线均匀铺几根绑定骨骼。 |
| **V_min** | 在控制器上暴露根部一侧的衰减属性 `falloffMin`。 |
| **V_max** | 在控制器上暴露末端一侧的衰减属性 `falloffMax`。 |
| **归一化模式** | 控制器是否默认开启 `normalize`（见下文）。 |
| **生成蒙皮面片** | 顺带生成一块沿骨骼链的面片并蒙皮上去（见下文）。 |
| **开放控制器缩放** | 解锁 FK 控制器的截面缩放，按衰减权重分摊给骨骼（见下文）。 |
| **Load Curve** | 把当前选中的 NURBS 曲线载入为基础曲线。 |
| **Create Rig** | 开始构建。 |

不勾 `V_min` / `V_max` 时，那一侧的衰减会被固定成一个常量，不暴露给动画师。

## 绑定怎么用

选中任意 `*_fk_NN_ctrl`，可以调：

- **position** —— 控制器沿链条滑动的量，单位是骨骼序号。
  **出厂值永远是干净的 0**，正负表示往根部或末端滑。
  控制器始终贴在它对应的那根骨骼上：链条被别的控制器掰弯时，
  自己没动过的控制器也会跟着链条走，不会留在原地。
- **basePosition** —— 控制器出厂时待的位置（同样以骨骼序号为单位）。
  它是"设置"而不是"动画"：可以在通道盒里改，但不可 K 帧。
  实际位置 = `basePosition + position`，再钳回 `[0, 骨骼数-1]`，
  所以 `position` 推到头也不会让控制器滑出链条。
- **falloffMin / falloffMax** —— 位置两侧各有多少根骨骼被带进这次弯曲。
  值越大，弧线越宽越软。
- **normalize** —— `0` … `1`，混合进归一化模式。
- **rotate X/Y/Z** —— X 是沿链条的扭转，Y/Z 是弯曲。
- **scale Y/Z** —— 截面缩放，让触手在这一段变粗/变细。中性值是 1。

把 `position` 和 `rotate` 全部归零就能回到绑定姿势，不用记每个控制器的偏移量；
镜像、复制姿势、做 reset 按钮也都省事。

### 两种缩放

**整体缩放** 选中 `*_global_ctrl` 按 `R`，骨骼、控制器、
面片会一起等比放大缩小，比例完全正确（长度 ×2 时宽度也 ×2）。移动和旋转同理。

**局部缩放**：选中某个 FK 控制器调 `scaleY` / `scaleZ`，用和旋转同一套衰减权重
分摊给骨骼，做出触手某一段变粗/变细的效果。它走的是"增量累加"（中性值 1，
分摊的是偏离 1 的量），而且**刻意不经过归一化因子** —— 归一化是为了让旋转沿链条
累加到输入值，缩放并不累加，除以权重和只会把它压没。

> **为什么 `scaleX` 是锁死的**：Maya 骨骼的 `scaleX` 一定会把子骨骼顺着链条推走。
> `segmentScaleCompensate` 只能阻止缩放继续向下累乘（实测 4 节链条根部 ×3：
> 关 SSC 末端 6→18，开 SSC 6→10），消不掉这一次位移。沿链条拉伸会让链条变长、
> 控制器和骨骼对不上，所以这里只开放截面方向的 Y/Z，
> 换来"缩放不改变链条长度和走向"这个性质（自检里有断言）。
> 确实需要 squash & stretch 的话，把 `*_sclSum_pma.output3Dx` 接到
> `joint.scaleX` 即可，但要自己承担链条被拉长的后果。

`*_global_ctrl` 可以移动、旋转并**整体缩放绑定**，上面还有
`jointVis` / `controlVis` 两个显示开关。

绑定骨骼都收进了 `<前缀>bind_joints_set` 集合，要蒙皮别的模型直接选这个集合即可。

### 控制器怎么跟着链条走

控制器骑在一条 `<前缀>ride_crv` 上（隐藏）。这条曲线的每个 CV 100% 绑给
对应骨骼，所以它跟着骨骼一起变形，控制器也就跟着走了。

这里**不会**形成循环依赖：控制器的 `rotate` / `scale` 是输入属性，
它驱动骨骼、骨骼驱动这条曲线、曲线再摆放控制器的父组，
而 `rotate` 本身不依赖父组的变换。自检里有 `cycleCheck` 断言。

轨道曲线刻意用**线性**（degree 1）。二次/三次是"逼近" CV 而不是穿过它，
链条一弯曲线就往内侧塌、弧长也变短，控制器于是落不到自己那根骨骼上 ——
实测 40 骨骼弯 60°，三次偏 0.31、二次偏 0.20、线性 0.00。
代价是 `motionPath` 的朝向在每个 CV 处有一点阶梯感，但骨骼够密时每段转角很小，
而位置准确得多。

### 蒙皮面片

勾上"生成蒙皮面片"后会多出一块 `<前缀>ribbon_geo`：沿骨骼链铺开的多边形带子，
每根骨骼一行顶点，宽度方向 1 段。因为每行顶点正好骑在骨骼上
（沿骨骼局部 Z 轴左右各撑开半个宽度），所以每个顶点 100% 绑给对应骨骼
就是数学上正确的权重 —— 不用再刷权重，也不会有权重渗漏。

面片挂在 `<前缀>geo_grp` 下，这一层 `inheritsTransform = 0`：
蒙皮结果里已经包含骨骼的世界变换，再继承一层就会被变换两遍。

### 默认模式 vs 归一化模式

`normalize = 0` 时，每根受影响骨骼各拿 `旋转值 × 权重`，
总弯曲量 = 权重之和 × 输入值 —— 填一个很小的数就能拱出很大的弧。
这是这类绑定的经典手感。

`normalize = 1` 时，权重会先除以自己的总和，于是这些骨骼的旋转
**加起来正好等于你填的数值**：`rotateZ` 填 90，链条就正好弯 90°。
数值上更可预期，也是摆同一条链子的另一种思路。

---

## 原理

对每个控制器 *c* 和每根骨骼 *j*：

```
p = clamp(basePosition + position, 0, 骨骼数-1)   # 解算后的实际位置
d = j - p                             # 有符号距离，单位是骨骼序号
s = d / falloffMin     if d <= 0      # 衰减边缘处为 -1 ……
    -d / falloffMax    if d >  0      # …… 控制器所在处为 0
w = smoothstep(remap(s, [-1, 0] -> [0, 1]))
joint[j].rotate += control.rotate * k * w
```

`k` 平时为 `1`，归一化模式下为 `1 / max(sum(w), 1)`。

缩放同理，但用的是 `w` 原始权重、不乘 `k`：

```
joint[j].scaleYZ = 1 + Σ (control.scaleYZ - 1) * w
```

落到节点上：每个「控制器 × 骨骼」组合 5 个工具节点
（`plusMinusAverage`、`multiplyDivide`、`condition`、`remapValue`、
`multiplyDivide`），每个控制器再额外 8 个（含 `basePosition + position`
的 `addDoubleLinear` 和钳制用的 `clamp`），另外每根骨骼一个
`plusMinusAverage` 把所有控制器的贡献累加进 `joint.rotate`。
开放控制器缩放后，每个组合再多 1 个 `multiplyDivide`、每个控制器多 1 个
`plusMinusAverage`、每根骨骼多 1 个累加节点。

**刻意不用表达式、不用脚本节点** —— 这样能在并行/GPU 求值模式下正常运算，
引用（reference）进场也不会出问题。一套 4 控制器 / 40 骨骼的绑定约 1076 个
工具节点（关掉控制器缩放是 872 个），构建耗时几秒。

### 场景结构

```
<前缀>rig_grp
└── <前缀>global_ctrl              整体移动 / 旋转 / 缩放
    ├── <前缀>curve_grp
    │   └── <前缀>base_crv         隐藏的副本；只用来铺骨骼，原曲线不会被改动
    ├── <前缀>joint_grp
    │   └── <前缀>bind_000_jnt …   骨骼链
    └── <前缀>control_grp          inheritsTransform = 0
        └── <前缀>fk_01_path_grp   由 ride_crv 上的 motionPath 驱动
            └── <前缀>fk_01_offset_grp
                └── <前缀>fk_01_ctrl
└── <前缀>geo_grp                  inheritsTransform = 0
    ├── <前缀>ride_crv             蒙皮到骨骼上的控制器轨道（隐藏）
    └── <前缀>ribbon_geo           蒙皮到骨骼链上的面片
```

注意 `geo_grp` 挂在 `rig_grp` 下、而**不是**总控下 —— 理由同上：避免双重变换。
`ride_crv` 和面片都被骨骼驱动，所以都放在这一层。

`control_grp` 关掉了 `inheritsTransform`，因为 motionPath 输出的已经是世界空间坐标，
再继承一次总控变换就会叠加两遍；总控的 `scale` 则单独接到每个 `*_path_grp` 上，
保证控制器外形依然跟着整体缩放。

---

## 脚本调用

```python
import variableFK

rig = variableFK.build(
    'myCurve',
    prefix='tentacle_',
    num_controls=5,
    num_joints=60,
    use_falloff_min=True,
    use_falloff_max=True,
    falloff=12.0,        # 默认衰减宽度，单位是骨骼序号
    normalized=True,
    control_size=1.5,
    create_plane=True,       # 生成蒙皮面片
    plane_width=2.0,
    use_control_scale=True,  # 开放控制器的截面缩放
)

print(rig['joints'], rig['controls'], rig['global_ctrl'])
print(rig['plane'], rig['skin_cluster'])
print(rig['ride_curve'], rig['ride_skin'])
```

[examples/demo.py](examples/demo.py) 会在 Maya 里从零搭一个测试场景。
[examples/headless_test.py](examples/headless_test.py) 是给 `mayapy` 用的自检脚本：

```
mayapy examples/headless_test.py
```

它会验证：骨骼间距均匀、**所有控制器的 `position` 和 `rotate` 都是干净的 0**、
控制器落在自己的 `basePosition` 上、影响量在控制器处最大并在衰减边缘归零、
归一化模式的和等于输入值、滑动与 clamp 生效、
**链条弯曲后所有控制器仍精确贴在自己的骨骼上（误差 0）**、
**整体缩放的长度和宽度都是 2 倍**、**控制器缩放按权重分摊且面片正好鼓 3 倍**、
**截面缩放不改变链条长度**、`scaleX` 保持锁死、关掉缩放开关时确实锁死且不驱动骨骼、
面片顶点数/蒙皮/跟随骨骼/不被双重变换、图里没有循环依赖、
关掉 `V_min`/`V_max` 时行为正确、以及非法前缀会被清洗成合法节点名。

## 已验证 / 注意事项

已用 `mayapy`（Maya 2020，Python 2.7）跑通全部自检。你日常用的 Maya 2025
是 Python 3，代码同时兼容两者——含中文注释的 `.py` 都写了
`# -*- coding: utf-8 -*-`，否则 Python 2 下会直接语法报错。

- 基础曲线是**按弧长**采样的，所以 CV 分布不均的曲线上骨骼间距依然均匀。
- 骨骼和控制器都是 **+X 指向链条前方、+Y 朝上**。如果曲线正好完全沿世界 Y 轴走，
  上方向向量会翻转 —— 把曲线稍微倾斜一点，或者事后改 `motionPath.worldUpVector`。
- 前缀已存在时会直接报错，不会往已有绑定上叠加。

