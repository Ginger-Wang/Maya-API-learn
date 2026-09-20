# -*- coding: utf-8 -*-
"""快速试跑 —— 在 Maya 的脚本编辑器里执行。

新建场景、画一条直的基础曲线、在上面建好绑定,
并顺手摆一个控制器,方便直观看到衰减效果。
"""

import maya.cmds as cmds

import variableFK
variableFK.reload_all()


def run(num_joints=40, num_controls=4, span=20.0):
    cmds.file(new=True, force=True)

    curve = cmds.curve(degree=3,
                       point=[(0, 0, 0),
                              (span * 0.25, 0, 0),
                              (span * 0.5, 0, 0),
                              (span * 0.75, 0, 0),
                              (span, 0, 0)],
                       name='base_crv')

    rig = variableFK.build(curve, prefix='demo_', num_controls=num_controls,
                           num_joints=num_joints)

    # 掰一下第二个控制器,看链条如何围着它拱起来
    if len(rig['controls']) > 1:
        ctrl = rig['controls'][1]
        cmds.setAttr(ctrl + '.rotateZ', 8)
        cmds.setAttr(ctrl + '.falloffMin', 10)
        cmds.setAttr(ctrl + '.falloffMax', 10)

    cmds.setAttr(rig['global_ctrl'] + '.jointVis', 1)
    cmds.select(rig['controls'][1] if len(rig['controls']) > 1
                else rig['global_ctrl'])
    cmds.viewFit()
    return rig


if __name__ == '__main__':
    run()
