# rbfSolver —— Maya RBF 插值节点

一个纯 Python 的 Maya 依赖节点（Maya API 2.0），把**多个物体的三维值**作为一个整体样本空间做 RBF（径向基函数）插值，输出**多个物体的三维值**。

典型用途：姿势读取器（pose reader）、多驱动的辅助骨骼/矫正、用多个控制器的位置驱动一堆物体的位移/旋转、把 RBF 权重接到 blendShape。

## 文件

| 文件 | 说明 |
| --- | --- |
| [rbfSolverNode.py](rbfSolverNode.py) | 节点插件本体，无第三方依赖 |
| [rbf_utils.py](rbf_utils.py) | 建立连接、录制/删除/回读姿势的工具函数 |
| [example_setup.py](example_setup.py) | 一键搭建演示场景（2 驱动 → 2 被驱动，5 个姿势） |
| [example_snap_to_locators.py](example_snap_to_locators.py) | 一键搭建"控制器靠近哪个 loc，物体就吸到哪个 loc" |
| [selftest.py](selftest.py) | mayapy 独立自测，88 项检查 |

## 快速开始

```python
import sys
sys.path.append(r"H:/ClaudeCode_Spawn/MayaRBFNode")

import example_setup
example_setup.build()      # 直接生成可玩的演示场景
```

自己搭：

```python
import maya.cmds as cmds
import rbf_utils

cmds.loadPlugin(r"...\MayaRBFNode\rbfSolverNode.py")

# 2 个驱动物体 -> 3 个被驱动物体（默认连 translate，也可传 "pCube1.rotate" 这种完整属性）
rbf = rbf_utils.create_rbf(["ctrlA", "ctrlB"], ["jntA", "jntB", "jntC"])

rbf_utils.set_edit_mode(rbf, True)     # 断开 output，方便手动摆姿势
for _ in range(5):
    # ... 摆驱动物体，再摆被驱动物体到你想要的结果 ...
    rbf_utils.add_pose(rbf)            # 录制当前状态为一个样本
rbf_utils.set_edit_mode(rbf, False)    # 重新接回 output
```

> **必须先 `set_edit_mode(node, True)` 再录姿势**。否则被驱动物体正被节点自己驱动，录下来的只是当前插值结果。

## 增加 / 删除驱动和被驱动物体

已经录好姿势之后再加物体，**关键是要给每个已有姿势补上新物体的样本值**——缺失的项会按 (0,0,0) 参与计算，会把已录的姿势全部带歪。`add_driver` / `add_driven` 会自动回填，默认填该物体的**当前值**，所以加完之后已有姿势的结果一模一样（自测里误差 1e-15）。

```python
import rbf_utils

# 加一个驱动控制器：先摆到它的静止位置再加
rbf_utils.add_driver(rbf, "ctrlC")                  # 默认 translate
rbf_utils.add_driver(rbf, "ctrlD.rotate")           # 也可以指定属性

# 加一个被驱动物体：先摆到它的静止位置再加
rbf_utils.add_driven(rbf, "jntD")

# 删除（连带清掉所有姿势里对应的样本值）
rbf_utils.remove_driver(rbf, 2)      # 参数是 input 索引
rbf_utils.remove_driven(rbf, 2)      # 参数是 output 索引
```

新加的物体此时在所有姿势里都是同一个值，等于"还没参与进来"。逐个姿势给它真实值：

```python
rbf_utils.set_edit_mode(rbf, True)
for i in rbf_utils.pose_indices(rbf):
    rbf_utils.apply_pose(rbf, i)     # 把场景摆回第 i 个姿势
    # ... 摆新加的驱动 / 雕新加的被驱动 ...
    rbf_utils.update_pose(rbf, i)    # 覆盖这个姿势
rbf_utils.set_edit_mode(rbf, False)
```

也可以在加的时候一次性给全每个姿势的值（顺序对应 `pose_indices(node)`）：

```python
rbf_utils.add_driven(rbf, "jntD", pose_values=[(0,0,0), (0,5,0), (0,0,5), (2,0,0), (1,1,1)])
```

如果物体还不多、姿势也好重录，最省事的做法就是直接用完整列表重建一个：

```python
rbf = rbf_utils.create_rbf(["ctrlA", "ctrlB", "ctrlC"], ["jntA", "jntB", "jntC", "jntD"])
```

驱动/被驱动的数量没有上限，索引也可以稀疏（`input[0]`、`input[5]` 这样跳着接都行），只要 `poseInput` 的索引跟 `input` 对得上即可。

## 用法示例：控制器靠近哪个 loc，物体就吸到哪个 loc

```python
import example_snap_to_locators
example_snap_to_locators.build(count=8, ring_radius=10.0, snap=0.15)
```

映射方式（只有 1 个驱动、8 个姿势、1 个被驱动）：

```
input[0]              <- snapCtrl.translate       控制器
pose[i].poseInput[0]  <- snapTarget<i>.translate  第 i 个 loc 的位置（"控制器到这儿"）
pose[i].poseOutput[0] <- snapTarget<i>.translate  同一个位置（"物体也到这儿"）
output[0]             -> snapObject.translate     被驱动物体
```

姿势数据是**连接**到 loc 的（不是烤死的数值），所以后面随便拖 loc，整个解算实时更新。

关键三个参数：

| 参数 | 值 | 作用 |
| --- | --- | --- |
| `normalizeWeights` | 开 | 权重恒定和为 1。不开的话控制器一离开 loc 权重就衰减到 0，物体塌回原点 |
| `clampWeights` | 开 | 去掉负权重，物体不会冲过 loc |
| `useLinearTerm` | **关** | 开着的话多项式项会拟合一个全局平面，把结果摊平到所有 loc 上，吸附感全没了 |
| `radius` | 0.15~0.3 | 吸附硬度。实测 0.15 = 在两个 loc 正中间瞬间翻转，0.3 = 中点附近有一小段过渡，1.0 = 大范围软混合 |

自测里验过：控制器停在任意一个 loc 上，物体误差 < 1e-4；在 loc1→loc2 走到 20%/40% 仍吸在 loc1，60%/80% 已经吸到 loc2；圈外和圆心的行为也符合预期。

## 后期修改某个姿势的输出

姿势数据就是普通属性，**知道数值就直接 setAttr，立即生效**，不需要 edit mode：

```python
cmds.setAttr(rbf + ".pose[3].poseOutput[0]", -2, -2, -2, type="double3")
```

想用眼睛摆的话走 edit mode，注意 `inputs=False`：

```python
rbf_utils.set_edit_mode(rbf, True)
skipped = rbf_utils.apply_pose(rbf, 3)     # 场景摆回姿势 3
if skipped:
    print("这些控制器摆不回去（被锁定/约束）:", skipped)
# ... 调整被驱动物体 ...
rbf_utils.update_pose(rbf, 3, inputs=False)   # 只重录输出，不动输入
rbf_utils.set_edit_mode(rbf, False)
```

**`inputs=False` 很重要**：`update_pose` 默认会把 `poseInput` 也按当前驱动器的值重写一遍。如果驱动器被锁定或被约束/连接驱动，`apply_pose` 摆不回去（它会把这些属性名返回给你），此时默认行为会把姿势的输入值悄悄写成错的。只改输出就一律带上 `inputs=False`。

改完只影响这一个姿势，其他姿势仍然精确还原（自测里其余姿势误差 1e-15）。

## 属性

| 属性（长名 / 短名） | 类型 | 说明 |
| --- | --- | --- |
| `input[j]` / `in` | double3 数组 | 第 j 个驱动物体的实时三维值。j 个元素拼成一个 3·j 维样本空间 |
| `inputScale[j]` / `insc` | double 数组 | 第 j 个驱动的权重（默认 1.0）。混合平移(cm)和旋转(度)时用它统一量纲 |
| `pose[i].poseInput[j]` / `pin` | double3 数组 | 第 i 个样本里，第 j 个驱动的记录值 |
| `pose[i].poseOutput[k]` / `pot` | double3 数组 | 第 i 个样本里，第 k 个被驱动物体的目标值 |
| `output[k]` / `out` | double3 数组 | 第 k 个被驱动物体的插值结果 |
| `outputWeight[i]` / `owt` | double 数组 | 第 i 个样本的混合权重，正好落在该样本上时为 1.0。可直接接 blendShape 权重 |
| `kernel` / `krn` | enum | linear / gaussian / exponential / multiQuadratic / inverseMultiQuadratic / thinPlate / cubic / quintic |
| `radius` / `rad` | double | 核半径。`autoRadius` 开启时它是自动半径的**倍率**（默认 1.0，调大更平滑，调小更"贴样本"） |
| `autoRadius` / `arad` | bool | 默认开。自动半径 = 样本间平均最近邻距离 |
| `regularization` / `reg` | double | 岭回归项。样本很密或有噪声时加一点（0.001~0.1）会更稳，代价是不再严格穿过样本 |
| `useLinearTerm` / `ult` | bool | 默认开。加线性多项式项，改善外推；linear / multiQuadratic / thinPlate / cubic / quintic 这几个条件正定核尤其需要它。做吸附/最近邻效果时要关掉，它会把结果摊平到所有样本上 |
| `normalizeWeights` / `nwt` | bool | 权重归一化到和为 1 |
| `clampWeights` / `cwt` | bool | 权重截断到 [0, 1]，配合 `normalizeWeights` 适合驱动 blendShape |
| `envelope` / `env` | double | 0~1 整体强度 |

索引是**逻辑索引**，允许稀疏：`input[3]` 对应 `pose[i].poseInput[3]`，`output[7]` 对应所有 `pose[i].poseOutput[7]`；某个样本缺某项时按 (0,0,0) 处理。

## 数学

```
f(x) = Σ λ_i(x) · y_i         λ(x) = M⁻¹ · u(x)
```

`M` 是样本点两两之间的核矩阵（可加岭项和线性多项式增广），`u(x)` 是实时输入对各样本的核向量。因为 `M` 对称，`λ_i` 正好就是第 i 个样本的混合权重，且满足 `λ(x_i) = e_i`——**记录过的姿势会被精确还原**（自测里各核的误差都在 1e-15 量级）。

`M⁻¹` 只在样本集或求解参数变化时重算（高斯-约当消元 + 部分主元），每帧只做一次 O(n²) 的矩阵-向量乘。

样本退化时有两层兜底：样本共面/共线（比如一圈 y 全为 0 的 loc）会让多项式项的某些列跟常数列线性相关，矩阵必然奇异、加多少岭项都救不回来——求解前先用 Gram-Schmidt 挑出真正独立的多项式列，只保留这些；若仍然奇异（重复样本等），再退化为不带多项式项并逐级加大岭项。任何情况下都不会报错或输出 NaN。

## 性能

纯 Python 求解，复杂度 O(n³)（n = 样本数），只在样本或求解参数变动时触发。实测单次矩阵求逆耗时：

| 样本数 | 30 | 60 | 100 | 150 |
| --- | --- | --- | --- | --- |
| 重解耗时 | 3 ms | 20 ms | 90 ms | 0.31 s |

超过 200 个样本就会明显卡顿（≈0.7 s 一次重解），建议拆成多个节点。

每帧求值是 O(n² + n·m)，n 是样本数、m 是输出数，几十个样本的量级完全跟得上实时播放。

## 自测

```bash
"H:/Program Files/Autodesk/Maya2025/bin/mayapy.exe" selftest.py
```

已在 Maya 2025 的 mayapy 跑通 **88/88**：样本精确还原、8 种核、中间值插值、权重归一化/截断、改姿势后重解、无样本/单样本/重复样本、稀疏索引、真实 transform 驱动、存盘重开、`rbf_utils` 全流程、事后增删驱动/被驱动物体、事后改姿势输出（含锁定驱动器的保护）、共面/共线样本、最近邻吸附示例。

代码只用 Maya API 2.0 + 标准库，语法上同时兼容 Python 2.7 / 3.x（没有 f-string、类型标注），理论上 Maya 2019+ 都能加载，但只在 2025 实测过。

## 已知限制

- 高斯 / 指数核在远离所有样本时权重会整体衰减到 0，输出跟着塌成 0。想让它在外侧保持最近姿势的形状，打开 `normalizeWeights`（必要时配合 `clampWeights`）。
- 距离度量是欧氏距离。要做旋转驱动，建议接 `rotate`（配合 `inputScale` 缩小量纲）或自己转成向量再接进来；四元数测地距离尚未实现。
- `rbf_utils` 的 edit mode 把被驱动属性名存在节点的 `rbfMeta` 字符串属性里，处于 edit mode 期间重命名物体会导致重连失败。
