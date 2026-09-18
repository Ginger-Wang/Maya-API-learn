# MayaNodes

Maya 自定义节点（Python API 1.0，`maya.OpenMaya` / `maya.OpenMayaMPx`）。
后期根据实际节点作用，修改 def compute() 内容，和 def nodeInitializer() 里的属性 

本文档说明其中两个文件：

| 文件 | 作用 |
| --- | --- |
| [add_Attribute.py](add_Attribute.py) | 属性创建辅助库，收拢 API 1.0 里创建节点属性的样板代码 |
| [functionTest_node.py](functionTest_node.py) | 测试节点 `testFunctionNode`，用来验证属性创建函数在 Maya 里的实际表现 |

同目录下的 `computePoleVector.py` 是独立的功能节点，不在本文档范围内。

环境：Maya 2025（Python 3）。

---

## 快速开始

1. 把本目录加入 Maya 的插件搜索路径：

   ```python
   import os, sys
   path = r"H:\ScriptPath\MayaNodes"
   sys.path.append(path)                                    # 让 add_Attribute 可被 import
   os.environ["MAYA_PLUG_IN_PATH"] += os.pathsep + path     # 让插件管理器能找到
   ```

   或者直接在 **Windows > Settings/Preferences > Plug-in Manager** 里浏览到
   `functionTest_node.py` 加载。注意 `add_Attribute` 是普通模块而非插件，
   必须能通过 `sys.path` 被 import 到。

2. 加载插件并创建节点。**文件名和节点名不一致**，别搞混：

   ```python
   import maya.cmds as cmds
   cmds.loadPlugin("functionTest_node.py")   # 用文件名
   node = cmds.createNode("testFunctionNode")  # 用节点类型名
   ```

3. 验证属性：

   ```python
   cmds.listAttr(node, userDefined=True)
   # ['inputRoteta',
   #  'inRotate', 'inRotateX', 'inRotateY', 'inRotateZ',
   #  'inTranslate', 'inTranslateX', 'inTranslateY', 'inTranslateZ',
   #  'output',
   #  'outRotate', 'outRotateX', 'outRotateY', 'outRotateZ']
   ```

   通道盒里只会看到三个输入（`isInput=True` → 可K）。输出属性不可K，
   需要在属性编辑器、节点编辑器里查看，或用 `cmds.getAttr` 读取。

---

## 节点属性一览（testFunctionNode）

| 属性 | 短名 | 类型 | 方向 | 备注 |
| --- | --- | --- | --- | --- |
| `inputRoteta` | `inRoteta` | double | 输入 | 软限制 0~360 |
| `inRotate` | `inRot` | angle3 | 输入 | 软限制传了 0~360，但角度按弧度解释，实际无效 |
| `inTranslate` | `inTrans` | double3 | 输入 | 无限制 |
| `output` | `out` | double | 输出 | 目前 `isReadable=False`，接不出去，见"待改进" |
| `outRotate` | `outRot` | angle3 | 输出 | |

依赖关系是全连接：三个输入中任意一个变化，两个输出都被标记为脏。

---

## add_Attribute 用法

三个公开函数配合使用，职责分工是刻意分开的：

- **值域相关**（可K、min/max、软限制）在 **创建时** 由内部函数 `_set_attr_Value`
  就地设置 —— 这些调用作用于函数集当前指向的属性，必须紧跟 `create()`。
- **连接相关**（读 / 写 / 存盘）在属性建好之后由 `mark_Attribute` 设置 ——
  它每次自建 `MFnAttribute`，不受函数集指向影响。

典型写法是三步：

```python
Node.aFoo = mark_Attribute(                        # 2. 定读/写/存盘
    create_Attribute("foo", "f", "double",         # 1. 建属性 + 定可K和范围
                     0.0, minValue=0.0, isInput=True))
Node.addAttribute(Node.aFoo)                       # 3. 挂到节点
```

### `create_Attribute(attrName, shortName, attrType, defaultValue=None, minValue=None, maxValue=None, softMax=None, softMin=None, isInput=True)`

创建单值属性，返回尚未挂到节点上的 `MObject`。

支持的 `attrType`：`"double"` `"float"` `"int"` `"bool"` `"enum"` `"matrix"`

| 参数 | 说明 |
| --- | --- |
| `minValue` / `maxValue` | 硬限制，超出范围无法输入 |
| `softMin` / `softMax` | 软限制，只影响属性编辑器滑块范围，手动输入可超出 |
| `isInput` | `True` → 设为可K、出现在通道盒；`False` → 不可K |

`"enum"` 只创建属性本身，枚举项需要调用方自己用模块级的
`eAttr.addField(标签, 序号)` 紧接着补充。

`"enum"` 和 `"matrix"` **不支持** min/max/soft 系列参数（那是数值属性专属），
传了非 `None` 会抛 `AttributeError`，保持默认即可。

### `createAttr_double3(attrName, shortName, attrType, defaultValue=0.0, minValue=None, maxValue=None, softMax=None, softMin=None, isInput=True)`

创建三分量复合属性（父属性 + X/Y/Z 子属性），返回**父属性**。
`defaultValue` 和各限制由三个分量共用。

| `attrType` | 子属性类型 | 适用场景 |
| --- | --- | --- |
| `"double3"` | `kDouble` | 位置、缩放、向量 |
| `"angle3"` | `kAngle`（单位属性） | 旋转，可直接连到 `rotate` |

子属性会随父属性一起被 `addAttribute`，**不要再单独挂一次子属性**。

### `mark_Attribute(attribute, isStorable=True, isReadable=True, isWritable=True)`

设置读 / 写 / 存盘标记，并把属性原样返回。

| | `isReadable` | `isWritable` | `isStorable` |
| --- | --- | --- | --- |
| 输入属性 | `True` | `True` | `True` |
| 输出属性 | **`True`** | `False` | `False` |

输出属性的 `isReadable` 必须是 `True` —— 它决定属性能不能作为连接的**源**。
设成 `False` 等于把输出封死，谁都接不出去。

`mark_Attribute` 只作用于传入的这一个属性，**不会递归到 X/Y/Z 子属性**。
子属性的标记在 `createAttr_double3` 里创建时就已确定。

---

## 踩过的坑

### 1. 改了 add_Attribute.py 却不生效 / 报 ImportError

`add_Attribute` 被 import 后会留在 `sys.modules` 里，**在 Maya 里卸载再加载插件
不会重新执行它**。典型症状是明明已经写了某个函数，加载时却报
`cannot import name 'xxx' from 'add_Attribute'`。

`functionTest_node.py` 已经在顶部加了开发期强制 reload：

```python
import add_Attribute
importlib.reload(add_Attribute)
```

手工处理的话，在 Script Editor 里执行一次 `importlib.reload(add_Attribute)`，
或者重启 Maya。删 `__pycache__` 没用 —— 问题在内存里，不在磁盘。

### 2. 三分量属性不能直接用 k3Double 创建

`MFnNumericAttribute.create()` 不接受 `k3Double` / `k3Float`。

```python
# 错 —— 会抛异常
nAttr.create("inRotate", "inRot", om.MFnNumericData.k3Double)

# 对 —— 先建三个子属性再组合
x = nAttr.create("inRotateX", "inRotX", om.MFnNumericData.kDouble, 0.0)
y = nAttr.create("inRotateY", "inRotY", om.MFnNumericData.kDouble, 0.0)
z = nAttr.create("inRotateZ", "inRotZ", om.MFnNumericData.kDouble, 0.0)
attr = nAttr.create("inRotate", "inRot", x, y, z)
```

`nAttr.createPoint()` 也可以，它会自动建三个 `kDouble` 子属性。

### 3. 角度属性的 min/max 单位是弧度，不是度

单位属性（`MFnUnitAttribute`）的限制值一律按**内部单位**解释 —— 角度是弧度、
距离是厘米。想把旋转限制在 0~360 度要传 `0 ~ 2*math.pi`：

```python
# 看起来是 360 度，实际是 360 弧度（约 20626 度），等于没限制
createAttr_double3("inRotate", "inRot", "angle3", 0.0, softMax=360.0)

# 正确
createAttr_double3("inRotate", "inRot", "angle3", 0.0, softMax=2*math.pi)
```

默认值同理：`defaultValue=90.0` 在 angle3 里是 90 弧度。
`functionTest_node.py` 里 `inRotate` 的软限制目前就踩着这个坑（作为演示保留）。

### 4. "插件加载成功，但节点没有属性"

`nodeInitializer` 抛异常时，节点类型已经注册、属性却没加上，于是节点存在但空空如也。
而 `initializePlugin` 里的裸 `except` 会把真实堆栈吞掉，只留一行没信息量的提示。

排查时把异常处理临时改成：

```python
except:
    import traceback
    sys.stderr.write(traceback.format_exc())
    raise
```

### 5. 旋转属性必须用角度类型

旋转要用 `MFnUnitAttribute.kAngle`（即 `createAttr_double3(..., "angle3")`），
Maya 才会按角度单位显示、并允许直接连到 transform 的 `rotate` 上。
用 `double3` 承载旋转会得到无单位的裸数值。

### 6. 短名必须全局唯一

同一节点内所有属性（**包括 X/Y/Z 子属性**）的短名不能重复，否则
`addAttribute` 失败。`createAttr_double3` 的子属性短名是 `短名 + X/Y/Z`，
起名时留意不要和别的属性撞上。

### 7. 函数集是模块级共享的

`nAttr` / `uAttr` / `eAttr` / `mAttr` 是模块级单例。每次 `create()` 都会把
函数集重新指向新建的属性，所以 `setKeyable` / `setMin` / `setMax` / `setSoftMax` /
`addField` 这类"作用于当前属性"的调用**必须紧跟对应的 `create()`**。

这正是 `createAttr_double3` 里每建一个子属性就立刻调一次 `_set_attr_Value`
的原因 —— 三个子属性不能先全建完再统一设置，否则前两个会被漏掉。

### 8. 卸载插件失败

场景里还存在该类型的节点时 `deregisterNode` 会失败。先删干净：

```python
cmds.delete(cmds.ls(type="testFunctionNode"))
cmds.unloadPlugin("functionTest_node.py")
```

---

## 待改进

`functionTest_node.py` 作为基础框架目前有几处未完成，正式节点不要照抄：

- **`compute` 是空的** —— 没有写出任何输出值，也没有调用 `dataBlock.setClean(plug)`，
  所以 `output` / `outRotate` 永远是默认值，且 Maya 每次取值都会重复调用。
  未处理的 plug 应当 `return om.kUnknownParameter` 而不是 `None`，
  否则 Maya 会认为该 plug 已被处理。
- **`initializePlugin` 吞异常** —— 见坑 4。
- **输出属性的 `isStorable` 仍为默认 `True`** —— 输出值不应随场景存盘，
  应显式传 `isStorable=False`。
- **`inRotate` 的软限制单位错了** —— 见坑 3，`softMax=360.0` 实际是 360 弧度。
- **三分量父属性的可K状态没设** —— `createAttr_double3` 里 `_set_attr_Value`
  只跟在三个子属性后面，组合出父属性之后没再调一次，所以父属性沿用数值属性
  默认的可K状态。输出型 `outRotate` 的父属性因此仍是可K的。
- 拼写：`inputRoteta`（应为 `Rotate`）、`intputs`（应为 `inputs`）。
- `add_Attribute.py` 里的 `sys`、`ompx`、`cAttr` 目前未被使用。
