# -*- coding: utf-8 -*-
"""
为 rbfSolver 节点搭建一个演示场景。

在 Maya 中运行：

    import sys
    sys.path.append(r"H:/ClaudeCode_Spawn/MayaRBFNode")
    import example_setup
    example_setup.build()

这是最基础的一个演示：2 个驱动 -> 2 个被驱动，共记录 5 个姿势。
两个驱动定位器各自贡献 XYZ 三个分量，合起来构成一个 6 维的采样空间；
两个被驱动定位器同样由 6 维输出控制。

移动 ``rbf_driverA`` / ``rbf_driverB``，即可看到 ``rbf_drivenA`` /
``rbf_drivenB`` 在各姿势之间平滑插值；当驱动端正好落在某个已记录的姿势上时，
对应的被驱动姿势会被精确复现。
"""

import os
import sys

import maya.cmds as cmds

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)

import rbf_utils  # noqa: E402

PLUGIN = os.path.join(_HERE, "rbfSolverNode.py")

# 演示用的姿势表。每一项是一个四元组，依次为：
#     (驱动A 的位置, 驱动B 的位置, 被驱动A 的位置, 被驱动B 的位置)
# 每个位置都是 (X, Y, Z) 三个浮点分量。
# 前两项拼成该姿势的 6 维输入采样，后两项拼成对应的 6 维输出采样。
# 第一项是全零的静置姿势，作为插值的基准状态。
DEMO_POSES = [
    ((0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)),
    ((10, 0, 0), (0, 0, 0), (0, 8, 0), (5, 0, 0)),
    ((0, 10, 0), (0, 0, 0), (0, 0, 8), (0, 0, 5)),
    ((0, 0, 0), (0, 0, 10), (-8, 0, 0), (0, -5, 0)),
    ((10, 10, 0), (0, 0, 10), (4, 4, 4), (2, 2, 2)),
]


def build(new_scene=True):
    """搭建 2 驱动 -> 2 被驱动、5 个姿势的 rbfSolver 基础演示场景。

    执行流程：按需新建空场景 -> 加载 rbfSolverNode.py 插件 -> 创建两个驱动定位器
    和两个被驱动定位器并着色 -> 创建 rbfSolver 节点并接线 -> 进入编辑模式逐条录入
    ``DEMO_POSES`` 中的 5 个姿势 -> 退出编辑模式并把驱动端复位到静置姿势 ->
    设置求解核与半径参数 -> 选中第一个驱动定位器方便直接拖动试玩。

    参数：
        new_scene (bool): 是否在搭建之前新建一个空场景。默认 True，此时会以
            force 方式新建，当前场景中未保存的修改将被丢弃。若希望把这套演示
            装配追加到已有场景里，传入 False。

    返回：
        str: 新建的 rbfSolver 节点名称，可继续用于修改姿势或调参。
    """
    if new_scene:
        cmds.file(new=True, force=True)

    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)

    drivers = [cmds.spaceLocator(name="rbf_driverA")[0],
               cmds.spaceLocator(name="rbf_driverB")[0]]
    driven = [cmds.spaceLocator(name="rbf_drivenA")[0],
              cmds.spaceLocator(name="rbf_drivenB")[0]]

    # 给四个定位器上色并放大显示：驱动端用 13 号（红），被驱动端用 6 号（蓝）
    for loc, color in zip(drivers + driven, (13, 13, 6, 6)):
        shape = cmds.listRelatives(loc, shapes=True)[0]
        cmds.setAttr(shape + ".overrideEnabled", True)
        cmds.setAttr(shape + ".overrideColor", color)
        cmds.setAttr(shape + ".localScale", 1.5, 1.5, 1.5)

    node = rbf_utils.create_rbf(drivers, driven, name="demo")

    # 录制姿势期间先断开输出连接（编辑模式），避免求解结果反过来干扰摆姿势
    rbf_utils.set_edit_mode(node, True)
    for a, b, c, d in DEMO_POSES:
        cmds.setAttr(drivers[0] + ".translate", *a)
        cmds.setAttr(drivers[1] + ".translate", *b)
        cmds.setAttr(driven[0] + ".translate", *c)
        cmds.setAttr(driven[1] + ".translate", *d)
        rbf_utils.add_pose(node)
    rbf_utils.set_edit_mode(node, False)

    # 驱动端复位到静置姿势
    cmds.setAttr(drivers[0] + ".translate", 0, 0, 0)
    cmds.setAttr(drivers[1] + ".translate", 0, 0, 0)

    cmds.setAttr(node + ".kernel", 1)          # 1 = 高斯核
    cmds.setAttr(node + ".autoRadius", True)
    cmds.setAttr(node + ".radius", 1.0)

    cmds.select(drivers[0])
    print("rbfSolver demo built: {0}".format(node))
    print("  drivers : {0}".format(", ".join(drivers)))
    print("  driven  : {0}".format(", ".join(driven)))
    print("  poses   : {0}".format(len(rbf_utils.pose_indices(node))))
    return node


if __name__ == "__main__":
    build()
