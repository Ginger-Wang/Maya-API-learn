# -*- coding: utf-8 -*-
"""
brushTipCurve 的一键演示场景。

在 Maya 中运行:
    import sys; sys.path.append(r"H:/ClaudeCode_Spawn/MayabrushNode")
    import example_setup
    example_setup.build()

跑完之后直接拖动红色的毛根定位器(brush_root)往下压,曲线就会自动在接触处弯折、
笔尖沿纸面铺开 —— 只要毛够得着纸面就一定会弯,不用调任何参数。可以试的几件事:

    - 把 brush_root 往下压            -> 贴地段变长,outPressure 变大
    - 把 brush_solver.stiffness 调到 0 -> 软毛,躺得更长
    - 调到 1                          -> 硬毛,弯成一个大圆弧,贴地段很短
    - 转动 brush_root 的 rotateY       -> 垂直下压时控制毛往哪边倒
    - 拖绿色的 brush_tip              -> 只改变笔的**朝向**,毛长不会跟着变
    - 把 brush_solver.envelope 归零     -> 关掉效果,回到定位器给出的直线

注意笔尖定位器只管朝向:毛长由 brush_solver.bristleLength 固定(本示例是初始
姿势量出来的 1.2),拖笔尖定位器拖多远,毛都还是那么长。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)

import maya.cmds as cmds  # noqa: E402

import brush_utils  # noqa: E402


def build(new_scene=True, brush_type="calligraphy"):
    """搭出「一张纸 + 一支笔刷」的演示场景。

    执行流程:
        1. 新建场景并加载插件;
        2. 建一张 10x10 的纸放在 y=0;
        3. 建一套笔刷,毛长 1.2,笔尖略微前倾地扎进纸面 0.2;
        4. 染色放大定位器,选中笔尖让人直接拖着玩。

    参数:
        new_scene   True 时先清空场景
        brush_type  "calligraphy"(毛笔)/ "round"(绘画笔)/ "flat"(毛刷)
                    / "fan"(扇形笔);会连带套上该类型的推荐手感

    返回:
        build_brush() 的返回值(含 node / curve / mesh / locators)
    """
    if new_scene:
        cmds.file(new=True, force=True)
    brush_utils.ensure_plugin()

    paper_transform = cmds.polyPlane(name="paper", w=10, h=10,
                                     sx=10, sy=10, ax=(0, 1, 0))[0]
    paper = cmds.listRelatives(paper_transform, shapes=True)[0]
    cmds.setAttr(paper_transform + ".overrideEnabled", True)
    cmds.setAttr(paper_transform + ".overrideColor", 16)   # 白

    # 毛根在 y=0.35、笔略微前倾,毛长固定 1.2 —— 这个比例下大约一半的毛会躺在
    # 纸上,效果最直观。笔尖定位器摆在方向上就行,它不决定毛长。
    rig = brush_utils.build_brush(
        mesh=paper,
        name="brush",
        root_pos=(0.0, 0.35, 0.0),
        tip_pos=(0.3, -0.85, 0.0),
        bristle_length=1.2,
        brush_type=brush_type,
        samples=32,
    )
    brush_utils.style_locators(rig["locators"])

    cmds.setAttr(rig["curveTransform"] + ".overrideEnabled", True)
    cmds.setAttr(rig["curveTransform"] + ".overrideColor", 17)   # 黄

    # 选中毛根:现在「压笔」是把毛根往下推,笔尖定位器只管朝向
    cmds.select(rig["root"])
    cmds.dgeval(rig["node"] + ".outCurve")

    print("brush ready: {0}".format(rig["node"]))
    print("  contact  = {0}".format(cmds.getAttr(rig["node"] + ".outContact")))
    print("  pressure = {0:.4f}".format(cmds.getAttr(rig["node"] + ".outPressure")))
    print("  drag '{0}' down to press the brush into the paper".format(rig["root"]))
    print("  '{0}' only aims the brush; the length is fixed".format(rig["tip"]))
    return rig


if __name__ == "__main__":
    build()
