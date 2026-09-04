# -*- coding: utf-8 -*-
"""
演示：一个控制器、N 个定位器，一个始终吸附到最近定位器的物体。

    import sys
    sys.path.append(r"H:/ClaudeCode_Spawn/MayaRBFNode")
    import example_snap_to_locators
    example_snap_to_locators.build()

拖动 ``snapCtrl``：``snapObject`` 会朝控制器当前最靠近的那个定位器滑过去；
当控制器完全走到某个定位器上时，物体正好落在该定位器的位置上。

映射到 rbfSolver 上的接法：

    input[0]              <- snapCtrl.translate          （唯一的驱动）
    pose[i].poseInput[0]  <- snapTarget<i>.translate      （控制器要到达的位置）
    pose[i].poseOutput[0] <- snapTarget<i>.translate      （物体要去的位置）
    output[0]             -> snapObject.translate

也就是说第 i 个姿势的输入和输出都直接连到第 i 个 loc 的 translate 上。
姿势数据是"连接"到定位器的，而不是烤死的静态数值，因此拖动任意一个定位器
都会让整套解算实时重新计算。

真正起作用的是三个开关：

    normalizeWeights = 开    权重恒定归一化、和始终为 1，物体因此始终待在定位器
                             点云内部；若关闭，控制器一旦离开定位器，权重会衰减
                             到 0，物体就会塌回原点
    clampWeights     = 开    去掉负的权重瓣，物体不会冲过定位器（不会过冲）
    useLinearTerm    = 关    开着的话，多项式项会对所有采样拟合出一个全局平面，
                             把结果摊平分摊到所有定位器上，吸附感就消失了。
                             关掉之后，配合一个较小的半径，最近的那个定位器几乎
                             独占全部权重 —— 这就是吸附效果的来源。

``snap``（即节点的 ``radius``）是控制吸附强弱的旋钮。在本场景中的实测值：
0.15 = 硬吸附（物体在两个定位器正中间瞬间翻转到下一个），
0.3 = 中点附近有一小段过渡，
1.0 = 大范围的软混合。
"""

import math
import os
import sys

import maya.cmds as cmds

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)

import rbf_utils  # noqa: E402

PLUGIN = os.path.join(_HERE, "rbfSolverNode.py")


def build(count=8, ring_radius=10.0, snap=0.2, new_scene=True):
    """搭建"控制器吸附到最近定位器"的演示场景。

    执行流程：按需新建空场景 -> 加载 rbfSolverNode.py 插件 -> 在 XZ 平面上均匀
    摆放一圈定位器 -> 创建圆形控制器 ``snapCtrl`` 与球体 ``snapObject`` ->
    创建 rbfSolver 节点并接线 -> 为每个定位器建立一个姿势（输入与输出都直接连到
    该定位器的 translate）-> 设置核、半径与三个关键开关 -> 选中控制器。

    参数：
        count (int): 定位器数量，同时也是姿势数量。取值建议 3 到 16；数量越多，
            相邻定位器越密，需要相应调小 snap 才能保持清晰的吸附感。
        ring_radius (float): 定位器所在圆环的半径，圆环位于 XZ 平面、圆心在原点。
            该值改变了采样点之间的间距，通常需要与 snap 配合调整。
        snap (float): 写入节点 ``radius`` 的高斯核半径，控制吸附的硬度。
            实测参考值：0.15 = 硬吸附，在两个定位器正中间瞬间翻转；
            0.3 = 中点附近有一小段过渡；1.0 = 大范围软混合。数值越小越"脆"。
        new_scene (bool): 是否在搭建之前新建一个空场景。默认 True，此时以 force
            方式新建，当前场景中未保存的修改会被丢弃；传 False 则追加到当前场景。

    返回：
        tuple: ``(rbf, ctrl, obj, locators)`` 四元组，依次为 rbfSolver 节点名、
            控制器变换节点名、被驱动球体变换节点名，以及所有定位器名组成的列表。
    """
    if new_scene:
        cmds.file(new=True, force=True)
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)

    # 在 XZ 平面上按等角度间隔摆一圈定位器，作为吸附目标
    locators = []
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        loc = cmds.spaceLocator(name="snapTarget{0}".format(i + 1))[0]
        cmds.setAttr(loc + ".translate",
                     ring_radius * math.cos(angle), 0.0,
                     ring_radius * math.sin(angle))
        shape = cmds.listRelatives(loc, shapes=True)[0]
        cmds.setAttr(shape + ".localScale", 1.5, 1.5, 1.5)
        cmds.setAttr(shape + ".overrideEnabled", True)
        cmds.setAttr(shape + ".overrideColor", 17)      # 黄色
        locators.append(loc)

    # 唯一的驱动：一个圆形控制器
    ctrl = cmds.circle(name="snapCtrl", normal=(0, 1, 0), radius=1.5,
                       constructionHistory=False)[0]
    cmds.setAttr(cmds.listRelatives(ctrl, shapes=True)[0] + ".overrideEnabled", True)
    cmds.setAttr(cmds.listRelatives(ctrl, shapes=True)[0] + ".overrideColor", 13)

    # 被驱动物体
    obj = cmds.polySphere(name="snapObject", radius=1.0,
                          constructionHistory=False)[0]

    rbf = rbf_utils.create_rbf([ctrl], [obj], name="snap")

    # 每个定位器对应一个姿势，输入端和输出端都直接连到该定位器本身；
    # 因为是连接而非烤死的数值，拖动定位器会让整套解算实时重新计算
    for i, loc in enumerate(locators):
        cmds.connectAttr(loc + ".translate",
                         "{0}.pose[{1}].poseInput[0]".format(rbf, i))
        cmds.connectAttr(loc + ".translate",
                         "{0}.pose[{1}].poseOutput[0]".format(rbf, i))

    cmds.setAttr(rbf + ".kernel", 1)            # 1 = 高斯核
    cmds.setAttr(rbf + ".autoRadius", True)
    cmds.setAttr(rbf + ".radius", snap)
    cmds.setAttr(rbf + ".normalizeWeights", True)   # 权重和恒为 1，物体不会塌回原点
    cmds.setAttr(rbf + ".clampWeights", True)       # 去掉负权重，不会冲过定位器
    cmds.setAttr(rbf + ".useLinearTerm", False)  # 原因见模块 docstring

    cmds.select(ctrl)
    print("snap demo built: {0}".format(rbf))
    print("  ctrl    : {0}   (move it around)".format(ctrl))
    print("  object  : {0}".format(obj))
    print("  targets : {0} locators on a radius {1} ring".format(count, ring_radius))
    print("  snap    : {0}  (rbf.radius - smaller = snappier)".format(snap))
    return rbf, ctrl, obj, locators


if __name__ == "__main__":
    build()
