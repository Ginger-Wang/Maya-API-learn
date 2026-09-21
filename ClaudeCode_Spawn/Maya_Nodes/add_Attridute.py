"""属性创建辅助模块。

把 Maya API 1.0 里创建节点属性的样板代码收拢成四个函数：

- ``create_Attribute``     —— 创建单值属性（double / float / int / bool / enum / matrix）
- ``createAttr_double3``   —— 创建三分量复合属性（double3 / angle3）
- ``mark_Attribute``       —— 设置属性的读 / 写 / 存盘标记
- ``_set_attr_Value``      —— 内部函数，设置可K状态与数值上下限（硬限制 + 软限制）

职责划分:
    "值域相关"（可K、min/max、软限制）在创建时由 ``_set_attr_Value`` 就地设置，
    因为这些调用作用于函数集当前指向的属性，必须紧跟 create()；
    "连接相关"（读 / 写 / 存盘）在属性建好之后由 ``mark_Attribute`` 统一设置，
    它每次自建 MFnAttribute，不受函数集指向的影响。

注意：本模块只负责"创建 + 打标记"，不负责 ``addAttribute``。
把属性挂到节点上仍由各节点的 ``nodeInitializer`` 自己调用，
这样同一个属性要挂到哪个节点、挂的顺序如何都由节点自己决定。
"""

import maya.OpenMaya as om

# 模块级共享的函数集（function set）。
# 这里可以复用同一个实例，因为每次调用 create() 都会把函数集重新指向新建的属性。
# 但也正因为如此：setKeyable / setMin / setMax / setDefault 这类"作用于当前属性"的调用
# 必须紧跟在对应的 create() 之后，中间一旦插入另一次 create()，就会写到错误的属性上。
# 下面各函数里 _set_attr_Value 紧贴 create() 调用，就是这个原因。
nAttr = om.MFnNumericAttribute()    # 数值属性：double / float / int / bool / 三分量复合
uAttr = om.MFnUnitAttribute()       # 单位属性：角度 / 距离 / 时间（带单位，会跟随场景单位显示）
eAttr = om.MFnEnumAttribute()       # 枚举属性（下拉菜单）
mAttr = om.MFnMatrixAttribute()     # 矩阵属性
cAttr = om.MFnCompoundAttribute()   # 复合属性（父 + 子属性）—— 目前尚未使用

def mark_Attribute(attribute,
                   isStorable=True,isReadable=True,isWritable=True
                   )-> om.MObject:
    """设置属性的连接与存盘标记，并把属性原样返回，方便链式写在 addAttribute 里。

    参数:
        attribute:   create_Attribute / createAttr_double3 返回的 MObject
        isStorable:  是否随场景存盘。输出属性通常应为 False（每次都重新计算）
        isReadable:  是否可作为连接的"源"。输出属性必须为 True，否则接不出去
        isWritable:  是否可作为连接的"目标"。输出属性应为 False，避免被外部写入

    惯例:
        输入属性:  isReadable=True, isWritable=True,  isStorable=True
        输出属性:  isReadable=True, isWritable=False, isStorable=False

    可K状态不在这里设置 —— 它由创建时的 isInput 参数经 _set_attr_Value 决定。

    注意: 标记只作用于传入的这一个属性，不会递归到三分量属性的 X / Y / Z 子属性。
    子属性的标记在 createAttr_double3 里逐个创建时就已确定。
    """
    fnAttr = om.MFnAttribute(attribute)
    fnAttr.setReadable(isReadable)
    fnAttr.setWritable(isWritable)
    fnAttr.setStorable(isStorable)
    return attribute


def create_Attribute(attrName, shortName, attrType,
                     defaultValue=None, minValue=None, maxValue=None,
                     softMax=None, softMin=None,isInput=True)-> om.MObject:
    """创建单值属性。

    参数:
        attrName:    长名，节点上显示和 getAttr/setAttr 使用的名字
        shortName:   短名，必须在同一节点内唯一（含子属性在内）
        attrType:    "double" / "float" / "int" / "bool" / "enum" / "matrix"
        defaultValue: 默认值。enum 和 matrix 不使用该参数
        minValue / maxValue: 硬限制，超出范围的值无法输入；为 None 时不设限
        softMax / softMin: 软限制，只影响属性编辑器里滑块的默认范围，
                           手动输入仍可超出；为 None 时不设限
        isInput:     True 表示输入属性，会被设为可K并出现在通道盒里；
                     False 表示输出属性，不可K

    限制:
        minValue / maxValue / softMin / softMax 只有数值属性（MFnNumericAttribute）
        支持。enum 和 matrix 传入这些参数会抛 AttributeError，保持为 None 即可。

    返回:
        新建属性的 MObject（尚未挂到任何节点上）
    """
    if attrType == "double":
        attribute = nAttr.create(attrName, shortName, om.MFnNumericData.kDouble, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

    elif attrType == "float":
        attribute = nAttr.create(attrName, shortName, om.MFnNumericData.kFloat, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

    elif attrType == "int":
        attribute = nAttr.create(attrName, shortName, om.MFnNumericData.kInt, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

    elif attrType == "bool":
        attribute = nAttr.create(attrName, shortName, om.MFnNumericData.kBoolean, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

    elif attrType == "enum":
        # 枚举项需要在 create() 之后由调用方用 eAttr.addField(标签, 序号) 逐个补充
        attribute = eAttr.create(attrName, shortName)
        # 枚举只能吃到 isInput（setKeyable），min/max 系列参数必须保持 None
        _set_attr_Value(eAttr, minValue, maxValue, softMax, softMin, isInput)

    elif attrType == "matrix":
        attribute = mAttr.create(attrName, shortName)
        # 矩阵同上：只有 isInput 生效
        _set_attr_Value(mAttr, minValue, maxValue, softMax, softMin, isInput)

    else:
        raise ValueError("Unsupported attribute type: {}".format(attrType))

    return attribute

def createAttr_double3(attrName, shortName, attrType,
                       defaultValue=0.0, minValue=None, maxValue=None,
                       softMax=None, softMin=None, isInput=True)-> om.MObject:
    """创建三分量复合属性（父属性 + X / Y / Z 三个子属性）。

    为什么必须这样写：
        MFnNumericAttribute.create() 不接受 k3Double / k3Float 这类复合类型，
        三分量属性只能先建好三个子属性，再用 create(长名, 短名, x, y, z) 组合出父属性。
        直接传 om.MFnNumericData.k3Double 会抛异常。

    参数:
        attrType:  "double3" —— 普通三维数值（位置、缩放、向量等）
                   "angle3"  —— 三维角度，子属性用 MFnUnitAttribute.kAngle 创建，
                                Maya 才会按角度单位显示，也才能直接连到 rotate 上
        defaultValue: 三个分量共用的默认值
        minValue / maxValue / softMin / softMax: 三个分量共用的限制
        isInput:   True 则三个子属性都设为可K（出现在通道盒里），False 则都不可K

    单位陷阱:
        attrType="angle3" 时子属性是角度属性，其 min / max / soft 限制都以
        内部单位（弧度）解释，不是度。想限制到 0~360 度应传 0 ~ 2*pi，
        直接传 360.0 会得到 360 弧度（约 20626 度），等于没限制。

    返回:
        父属性的 MObject。子属性会随父属性一起被 addAttribute，
        调用方不要再单独把 X / Y / Z 挂一次。
    """
    # 子属性的命名沿用 Maya 惯例：父名 + X/Y/Z（如 inRotate -> inRotateX）
    xAttrName,xAttrShortName = (attrName + "X", shortName + "X")
    yAttrName,yAttrShortName = (attrName + "Y", shortName + "Y")
    zAttrName,zAttrShortName = (attrName + "Z", shortName + "Z")
    if attrType == "double3":
        # 三个子属性逐个创建，每个都紧跟一次 _set_attr_Value：
        # 函数集此刻指向刚建好的那个子属性，晚一步就写错对象了
        xAttr = nAttr.create(xAttrName,xAttrShortName, om.MFnNumericData.kDouble, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

        yAttr = nAttr.create(yAttrName,yAttrShortName, om.MFnNumericData.kDouble, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

        zAttr = nAttr.create(zAttrName,zAttrShortName, om.MFnNumericData.kDouble, defaultValue)
        _set_attr_Value(nAttr, minValue, maxValue, softMax, softMin, isInput)

        # 用三个子属性组合出父属性，得到的是 k3Double 类型。
        # 这里没有再调 _set_attr_Value，所以父属性沿用数值属性的默认可K状态
        attribute = nAttr.create(attrName, shortName, xAttr, yAttr, zAttr)

    elif attrType == "angle3":
        # 角度子属性由 uAttr 创建，父属性仍用 nAttr 组合（Maya 自带的 rotate 就是这个结构）
        # 注意：这里的 min/max/soft 以弧度解释，见 docstring 的"单位陷阱"
        xAttr = uAttr.create(xAttrName,xAttrShortName, om.MFnUnitAttribute.kAngle, defaultValue)
        _set_attr_Value(uAttr, minValue, maxValue, softMax, softMin, isInput)

        yAttr = uAttr.create(yAttrName,yAttrShortName, om.MFnUnitAttribute.kAngle, defaultValue)
        _set_attr_Value(uAttr, minValue, maxValue, softMax, softMin, isInput)

        zAttr = uAttr.create(zAttrName,zAttrShortName, om.MFnUnitAttribute.kAngle, defaultValue)
        _set_attr_Value(uAttr, minValue, maxValue, softMax, softMin, isInput)

        attribute = nAttr.create(attrName, shortName, xAttr, yAttr, zAttr)
    else:
        raise ValueError("Unsupported attribute type for double3: {}".format(attrType))
    return attribute



def _set_attr_Value(funcAttr,minValue=None, maxValue=None,
                       softMax=None, softMin=None, isInput=True):
    """设置可K状态与取值范围。内部函数，必须紧跟对应的 create() 调用。

    作用对象不是显式传入的属性，而是 funcAttr **当前指向的**那个属性 ——
    也就是最近一次 funcAttr.create() 建出来的那个。中间插入任何别的 create()，
    设置就会落到错误的属性上。

    参数:
        funcAttr:  刚调用过 create() 的函数集实例（nAttr / uAttr / eAttr / mAttr）
        minValue / maxValue: 硬限制，超出无法输入
        softMax / softMin:   软限制，只影响滑块范围，手输可超出
        isInput:   直接传给 setKeyable —— 输入属性可K并出现在通道盒，输出属性不可K

    setKeyable 来自 MFnAttribute 基类，四种函数集都支持；
    但 setMin / setMax / setSoftMin / setSoftMax 只有数值和单位属性有，
    对 eAttr / mAttr 传入非 None 的限制会抛 AttributeError。
    """
    funcAttr.setKeyable(isInput)    # 数值属性默认可K，出现在通道盒里
    if minValue is not None:
        funcAttr.setMin(minValue)
    if maxValue is not None:
        funcAttr.setMax(maxValue)
    if softMax is not None:
        funcAttr.setSoftMax(softMax)
    if softMin is not None:
        funcAttr.setSoftMin(softMin)
