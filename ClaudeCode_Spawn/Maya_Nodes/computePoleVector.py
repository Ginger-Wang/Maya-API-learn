# -*- coding: utf-8 -*-
"""computePoleVector —— 对应 UE5 Control Rig 的 ComputePoleVector 函数。

参照 RigVM 图的实现（StandardFunctionLibrary > ComputePoleVector）：

    axis   = C - A                          链的主轴（根 -> 末端）
    t      = dot(B - A, axis) / |axis|      中间骨在主轴上的投影长度
    bend   = (B - A) - unit(axis) * t       从投影点指向中间骨的弯曲向量
    pole   = B + bend * OffsetFactor        极向量位置

    A o--------o------------o C
              |  投影点
              |  <-- bend
              o B  ----> pole

UE 的函数返回的是一个完整 Transform（位置 + 旋转），旋转由两次 cross
组出的正交基构成（图里 cross1 / cross2 -> From Vectors -> To Transform，
再经 To Euler / From Euler 规范化）。这里同样输出 translate / rotate /
matrix 三种形式。

本节点构建的正交基（右手系）：

    X 轴 = unit(C - A)              链主轴方向
    Y 轴 = unit(bend)               弯曲（极向量）方向
    Z 轴 = X ^ Y                    链平面法线

输入
    boneAMatrix / boneBMatrix / boneCMatrix
        三根骨骼的世界矩阵，直接接 joint.worldMatrix[0]，节点内部自己取平移。
    offsetFactor
        对应 UE 的 OffsetFactor。
    offsetMode
        ``Bend Length``  —— 与 UE 完全一致，偏移量 = 弯曲向量长度 × offsetFactor。
        ``Chain Length`` —— 偏移量 = 链总长 × offsetFactor。
        UE 那套在链接近伸直时 bend 趋近于 0，极向量会塌到中间骨上；
        Chain Length 模式没有这个问题，做 IK 控制器时通常更好用。
    originScale
        对应 UE Entry 的 Origin Scale，作为输出矩阵的缩放。
    rotateOrder
        对应 To Euler / From Euler 的 Rotation Order，与 Maya 的 rotateOrder 一致。
    parentInverseMatrix
        可选。接控制器的 parentInverseMatrix[0]，输出即落在该父空间下，
        可以直接驱动 translate / rotate，不用额外的 multMatrix。

输出
    outMatrix       位置 + 旋转 + originScale 组成的完整矩阵
    outChainLength  |B-A| + |C-B|

    以下四个输出因为结果不对，暂时注销，代码用 ``[暂时注销]`` 标记，
    排查完直接搜这个标记恢复：
    outTranslate    极向量位置
    outRotate       上述正交基的欧拉角（角度属性，可直接接 rotate）
    outPoleVector   单位弯曲方向
    outPlaneNormal  单位链平面法线

UE 图里的 Draw Transform / Initial 是 Control Rig 的调试绘制和初始姿态开关，
Maya 里没有对应概念，未实现。

链完全伸直时没有弯曲平面，UE 的做法会得到零向量；这里改为取一个确定性的
垂直向量（与链轴最不平行的世界轴做叉乘），既不会翻转跳变也不会出 NaN。

用法::

    import maya.cmds as cmds
    cmds.loadPlugin("computePoleVector.py")

    node = cmds.createNode("computePoleVector")
    cmds.connectAttr("shoulder.worldMatrix[0]", node + ".boneAMatrix")
    cmds.connectAttr("elbow.worldMatrix[0]",    node + ".boneBMatrix")
    cmds.connectAttr("wrist.worldMatrix[0]",    node + ".boneCMatrix")

    ctrl = cmds.spaceLocator(name="arm_pv_ctrl")[0]
    cmds.connectAttr(ctrl + ".parentInverseMatrix[0]", node + ".parentInverseMatrix")
    cmds.connectAttr(node + ".outTranslate", ctrl + ".translate")
    cmds.connectAttr(node + ".outRotate",    ctrl + ".rotate")

基于 Maya Python API 1.0（maya.OpenMaya / maya.OpenMayaMPx）编写。
"""

import sys

import maya.OpenMaya as om
import maya.OpenMayaMPx as ompx


kPluginNodeName = "computePoleVector"
# 0x00000000 - 0x0007ffff 是 Autodesk 留给原型和不外发的自研节点的区间，
# 场景要交付给外部之前记得换成正式申请的 ID。
kPluginNodeId = om.MTypeId(0x0007F3A1)

kEpsilon = 1.0e-7

# offsetMode
kOffsetBendLength = 0
kOffsetChainLength = 1


def _getTranslation(matrix):
    """从一个世界矩阵里取出平移部分。"""
    return om.MTransformationMatrix(matrix).getTranslation(om.MSpace.kWorld)


def _perpendicular(axis):
    """返回一个与 axis 垂直的单位向量，结果是确定性的。

    拿 axis 分量最小的那根世界轴去做叉乘，既保证叉乘不退化，
    又因为只有主导分量变化时选择才会改变，动画过程中不会来回跳。
    """
    ax, ay, az = abs(axis.x), abs(axis.y), abs(axis.z)
    if ax <= ay and ax <= az:
        reference = om.MVector(1.0, 0.0, 0.0)
    elif ay <= az:
        reference = om.MVector(0.0, 1.0, 0.0)
    else:
        reference = om.MVector(0.0, 0.0, 1.0)
    return (axis ^ reference).normal()


def _buildMatrix(xAxis, yAxis, zAxis, position, scale):
    """用三根轴 + 位置 + 缩放组出一个 Maya 行向量矩阵。"""
    values = [xAxis.x * scale.x, xAxis.y * scale.x, xAxis.z * scale.x, 0.0,
              yAxis.x * scale.y, yAxis.y * scale.y, yAxis.z * scale.y, 0.0,
              zAxis.x * scale.z, zAxis.y * scale.z, zAxis.z * scale.z, 0.0,
              position.x, position.y, position.z, 1.0]
    matrix = om.MMatrix()
    om.MScriptUtil.createMatrixFromList(values, matrix)
    return matrix


class ComputePoleVector(ompx.MPxNode):

    aBoneAMatrix = om.MObject()
    aBoneBMatrix = om.MObject()
    aBoneCMatrix = om.MObject()
    aOffsetFactor = om.MObject()
    aOffsetMode = om.MObject()
    aOriginScale = om.MObject()
    aRotateOrder = om.MObject()
    aParentInverseMatrix = om.MObject()

    # [暂时注销] aOutTranslate = om.MObject()
    # [暂时注销] aOutRotate = om.MObject()
    # [暂时注销] aOutRotateX = om.MObject()
    # [暂时注销] aOutRotateY = om.MObject()
    # [暂时注销] aOutRotateZ = om.MObject()
    aOutMatrix = om.MObject()
    # [暂时注销] aOutPoleVector = om.MObject()
    # [暂时注销] aOutPlaneNormal = om.MObject()
    aOutChainLength = om.MObject()

    def __init__(self):
        ompx.MPxNode.__init__(self)

    def compute(self, plug, data):
        # 子 plug（比如 outTranslateX）要归到父属性上再判断。
        attribute = plug.parent().attribute() if plug.isChild() else plug.attribute()
        if attribute not in (self.aOutMatrix,
                             # [暂时注销] self.aOutTranslate,
                             # [暂时注销] self.aOutRotate,
                             # [暂时注销] self.aOutPoleVector,
                             # [暂时注销] self.aOutPlaneNormal,
                             self.aOutChainLength):
            return om.kUnknownParameter

        # ---- 取输入 ----------------------------------------------------
        posA = _getTranslation(data.inputValue(self.aBoneAMatrix).asMatrix())
        posB = _getTranslation(data.inputValue(self.aBoneBMatrix).asMatrix())
        posC = _getTranslation(data.inputValue(self.aBoneCMatrix).asMatrix())

        offsetFactor = data.inputValue(self.aOffsetFactor).asDouble()
        offsetMode = data.inputValue(self.aOffsetMode).asShort()
        originScale = data.inputValue(self.aOriginScale).asVector()
        # [暂时注销] 只有 outRotate 用得到
        # rotateOrder = data.inputValue(self.aRotateOrder).asShort()
        parentInverse = data.inputValue(self.aParentInverseMatrix).asMatrix()

        # ---- 算弯曲向量 ----------------------------
        upperVector = posB - posA           # 根 -> 中
        lowerVector = posC - posB           # 中 -> 末
        chainLength = upperVector.length() + lowerVector.length()

        axis = posC - posA                  # Subtract：C - A
        axisLength = axis.length()          # Length
        if axisLength > kEpsilon:
            axisNormal = axis * (1.0 / axisLength)              # Unit
            # Dot / Divide / Scale：中间骨在主轴上的投影向量
            bend = upperVector - axisNormal * (upperVector * axisNormal)
        else:
            # A 和 C 重合，没有主轴可投影，整段 A->B 本身就是弯曲方向。
            axisNormal = None
            bend = upperVector

        bendLength = bend.length()
        if bendLength > kEpsilon:
            poleDirection = bend * (1.0 / bendLength)
        else:
            # 链完全伸直（或整段塌缩）：没有链平面，退化到确定性垂直方向。
            base = axisNormal if axisNormal is not None else om.MVector(0.0, 1.0, 0.0)
            poleDirection = _perpendicular(base)
            bendLength = 0.0

        if offsetMode == kOffsetChainLength:
            offset = chainLength * offsetFactor
        else:
            offset = bendLength * offsetFactor      # UE 的 Scale 节点

        # Final vector 组：Add(B, bend * OffsetFactor)
        polePosition = posB + poleDirection * offset

        # ---- 对应 UE 图下半部分：Compute the rotation ------------------
        if axisNormal is None:
            axisNormal = _perpendicular(poleDirection)
        planeNormal = (axisNormal ^ poleDirection).normal()     # cross1
        # 重新正交化，保证基严格正交（cross2）。
        yAxis = (planeNormal ^ axisNormal).normal()

        matrix = _buildMatrix(axisNormal, yAxis, planeNormal,
                              polePosition, originScale) * parentInverse

        # [暂时注销] To Euler / From Euler：按指定旋转顺序取欧拉角。
        # transform = om.MTransformationMatrix(matrix)
        # euler = transform.eulerRotation()
        # euler.reorderIt(rotateOrder)
        # translation = transform.getTranslation(om.MSpace.kWorld)

        # [暂时注销] 方向类输出只受父矩阵的旋转/缩放影响，不受平移影响。
        # outPoleVector = (poleDirection * parentInverse).normal()
        # outPlaneNormal = (planeNormal * parentInverse).normal()

        # ---- 写输出 ----------------------------------------------------
        # [暂时注销]
        # translateHandle = data.outputValue(self.aOutTranslate)
        # translateHandle.set3Double(translation.x, translation.y, translation.z)

        # [暂时注销]
        # rotateHandle = data.outputValue(self.aOutRotate)
        # rotateHandle.child(self.aOutRotateX).setMAngle(om.MAngle(euler.x))
        # rotateHandle.child(self.aOutRotateY).setMAngle(om.MAngle(euler.y))
        # rotateHandle.child(self.aOutRotateZ).setMAngle(om.MAngle(euler.z))

        matrixHandle = data.outputValue(self.aOutMatrix)
        matrixHandle.setMMatrix(matrix)

        # [暂时注销]
        # poleHandle = data.outputValue(self.aOutPoleVector)
        # poleHandle.set3Double(outPoleVector.x, outPoleVector.y, outPoleVector.z)

        # [暂时注销]
        # normalHandle = data.outputValue(self.aOutPlaneNormal)
        # normalHandle.set3Double(outPlaneNormal.x, outPlaneNormal.y, outPlaneNormal.z)

        lengthHandle = data.outputValue(self.aOutChainLength)
        lengthHandle.setDouble(chainLength)

        # 所有输出都已经写过了，一起标记为 clean，而不是只清 Maya 问到的那个。
        for attr in (self.aOutMatrix,
                     # [暂时注销] self.aOutTranslate, self.aOutRotate,
                     # [暂时注销] self.aOutPoleVector, self.aOutPlaneNormal,
                     self.aOutChainLength):
            data.setClean(attr)
        data.setClean(plug)
        return None


def nodeCreator():
    return ompx.asMPxPtr(ComputePoleVector())


def nodeInitializer():
    nAttr = om.MFnNumericAttribute()
    eAttr = om.MFnEnumAttribute()
    mAttr = om.MFnMatrixAttribute()
    # [暂时注销] outRotate 用的角度属性函数集
    # uAttr = om.MFnUnitAttribute()

    def addInput(attribute, keyable=True):
        fnAttr = om.MFnAttribute(attribute)
        fnAttr.setKeyable(keyable)
        fnAttr.setStorable(True)
        fnAttr.setWritable(True)
        ComputePoleVector.addAttribute(attribute)
        return attribute

    def markOutput(attribute):
        fnAttr = om.MFnAttribute(attribute)
        fnAttr.setWritable(False)
        fnAttr.setStorable(False)
        fnAttr.setKeyable(False)
        return attribute

    def addOutput(attribute):
        markOutput(attribute)
        ComputePoleVector.addAttribute(attribute)
        return attribute

    # ---- 输入 ----------------------------------------------------------
    ComputePoleVector.aBoneAMatrix = addInput(
        mAttr.create("boneRootMatrix", "brm", om.MFnMatrixAttribute.kDouble))
    ComputePoleVector.aBoneBMatrix = addInput(
        mAttr.create("boneMiddleMatrix", "bmm", om.MFnMatrixAttribute.kDouble))
    ComputePoleVector.aBoneCMatrix = addInput(
        mAttr.create("boneEndMatrix", "bem", om.MFnMatrixAttribute.kDouble))

    ComputePoleVector.aOffsetFactor = addInput(
        nAttr.create("offsetFactor", "ofc", om.MFnNumericData.kDouble, 3.0))

    offsetMode = eAttr.create("offsetMode", "ofm", kOffsetBendLength)
    eAttr.addField("Bend Length", kOffsetBendLength)
    eAttr.addField("Chain Length", kOffsetChainLength)
    ComputePoleVector.aOffsetMode = addInput(offsetMode)

    originScale = nAttr.createPoint("originScale", "osc")
    nAttr.setDefault(1.0, 1.0, 1.0)
    ComputePoleVector.aOriginScale = addInput(originScale)

    rotateOrder = eAttr.create("rotateOrder", "ro", 0)
    for index, label in enumerate(("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")):
        eAttr.addField(label, index)
    ComputePoleVector.aRotateOrder = addInput(rotateOrder)

    ComputePoleVector.aParentInverseMatrix = addInput(
        mAttr.create("parentInverseMatrix", "pim",
                     om.MFnMatrixAttribute.kDouble),
        keyable=False)

    # ---- 输出 ----------------------------------------------------------
    # [暂时注销]
    # ComputePoleVector.aOutTranslate = addOutput(
    #     nAttr.createPoint("outTranslate", "ot"))

    # [暂时注销] 旋转必须用角度属性，Maya 才会按角度单位显示并能直接接到 rotate 上。
    # ComputePoleVector.aOutRotateX = markOutput(
    #     uAttr.create("outRotateX", "orx", om.MFnUnitAttribute.kAngle, 0.0))
    # ComputePoleVector.aOutRotateY = markOutput(
    #     uAttr.create("outRotateY", "ory", om.MFnUnitAttribute.kAngle, 0.0))
    # ComputePoleVector.aOutRotateZ = markOutput(
    #     uAttr.create("outRotateZ", "orz", om.MFnUnitAttribute.kAngle, 0.0))
    # # 子属性会随父属性一起被 addAttribute，不要单独再加一次。
    # ComputePoleVector.aOutRotate = addOutput(
    #     nAttr.create("outRotate", "ort",
    #                  ComputePoleVector.aOutRotateX,
    #                  ComputePoleVector.aOutRotateY,
    #                  ComputePoleVector.aOutRotateZ))

    outMatrix = mAttr.create("outMatrix", "omt", om.MFnMatrixAttribute.kDouble)
    ComputePoleVector.aOutMatrix = addOutput(outMatrix)

    # [暂时注销]
    # ComputePoleVector.aOutPoleVector = addOutput(
    #     nAttr.createPoint("outPoleVector", "opv"))
    # ComputePoleVector.aOutPlaneNormal = addOutput(
    #     nAttr.createPoint("outPlaneNormal", "opn"))

    ComputePoleVector.aOutChainLength = addOutput(
        nAttr.create("outChainLength", "ocl", om.MFnNumericData.kDouble, 0.0))

    inputs = (ComputePoleVector.aBoneAMatrix,
              ComputePoleVector.aBoneBMatrix,
              ComputePoleVector.aBoneCMatrix,
              ComputePoleVector.aOffsetFactor,
              ComputePoleVector.aOffsetMode,
              ComputePoleVector.aOriginScale,
              ComputePoleVector.aRotateOrder,
              ComputePoleVector.aParentInverseMatrix)
    outputs = (ComputePoleVector.aOutMatrix,
               # [暂时注销] ComputePoleVector.aOutTranslate,
               # [暂时注销] ComputePoleVector.aOutRotate,
               # [暂时注销] ComputePoleVector.aOutRotateX,
               # [暂时注销] ComputePoleVector.aOutRotateY,
               # [暂时注销] ComputePoleVector.aOutRotateZ,
               # [暂时注销] ComputePoleVector.aOutPoleVector,
               # [暂时注销] ComputePoleVector.aOutPlaneNormal,
               ComputePoleVector.aOutChainLength)

    for source in inputs:
        for target in outputs:
            ComputePoleVector.attributeAffects(source, target)


def initializePlugin(mobject):
    plugin = ompx.MFnPlugin(mobject, "MayaNodes", "1.0", "Any")
    try:
        plugin.registerNode(kPluginNodeName,
                            kPluginNodeId,
                            nodeCreator,
                            nodeInitializer)
        print("%s initialized..." % kPluginNodeName)
    except Exception:
        sys.stderr.write("注册节点失败: %s\n" % kPluginNodeName)
        raise


def uninitializePlugin(mobject):
    plugin = ompx.MFnPlugin(mobject)
    try:
        plugin.deregisterNode(kPluginNodeId)
    except Exception:
        print("%s uninitialized..." % kPluginNodeName)
        raise




