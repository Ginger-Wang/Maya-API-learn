# -*- coding: utf-8 -*-
"""无头构建自检 —— 用 mayapy 跑,不要在 Maya 里跑。

    mayapy examples/headless_test.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import maya.standalone
maya.standalone.initialize(name='python')

import maya.cmds as cmds

import variableFK
from variableFK import core


def almost(a, b, tol=1e-4):
    return abs(a - b) < tol


def expected_point(joints, position):
    """position 处应该在的世界坐标。

    轨道曲线是线性的,所以相邻两根骨骼之间就是直线插值 —— 这样
    basePosition 不是整数时(比如 3 控制器配 12 骨骼)断言依然成立。
    """
    low = max(0, min(int(math.floor(position)), len(joints) - 1))
    high = min(low + 1, len(joints) - 1)
    blend = position - low
    a = cmds.xform(joints[low], q=True, ws=True, t=True)
    b = cmds.xform(joints[high], q=True, ws=True, t=True)
    return [a[k] + (b[k] - a[k]) * blend for k in range(3)]


def gap_to_joints(ctrl, joints, position):
    """控制器到它在链条上应在位置的距离。"""
    actual = cmds.xform(ctrl, q=True, ws=True, t=True)
    want = expected_point(joints, position)
    return sum((actual[k] - want[k]) ** 2 for k in range(3)) ** 0.5


def row_width(plane, row):
    """面片第 row 行两个顶点之间的距离。

    用 pointPosition 逐点量,不用 exactWorldBoundingBox —— 后者在批处理
    模式下会返回没刷新的旧包围盒,量出来的宽度是错的。
    """
    a = cmds.pointPosition('%s.vtx[%d]' % (plane, row * 2), world=True)
    b = cmds.pointPosition('%s.vtx[%d]' % (plane, row * 2 + 1), world=True)
    return sum((a[k] - b[k]) ** 2 for k in range(3)) ** 0.5


def main():
    failures = []

    span = 20.0
    curve = cmds.curve(degree=3,
                       point=[(0, 0, 0), (span * .25, 0, 0), (span * .5, 0, 0),
                              (span * .75, 0, 0), (span, 0, 0)],
                       name='base_crv')

    rig = variableFK.build(curve, prefix='test_', num_controls=4,
                           num_joints=40)

    print('root         : %s' % rig['root'])
    print('joints       : %d' % len(rig['joints']))
    print('controls     : %s' % rig['controls'])
    print('utility nodes: %d' % len(cmds.ls(type=('multiplyDivide',
                                                  'plusMinusAverage',
                                                  'condition', 'remapValue',
                                                  'clamp', 'blendTwoAttr'))))

    if len(rig['joints']) != 40:
        failures.append('joint count')
    if len(rig['controls']) != 4:
        failures.append('control count')

    # --- 骨骼沿曲线均匀分布 ---------------------------------------------
    first = cmds.xform(rig['joints'][0], q=True, ws=True, t=True)
    last = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
    if not (almost(first[0], 0.0, 1e-3) and almost(last[0], span, 1e-2)):
        failures.append('joint placement %s %s' % (first, last))

    # --- 所有控制器的 position 必须是干净的 0 ---------------------------
    for ctrl in rig['controls']:
        for attr in ('position', 'rotateX', 'rotateY', 'rotateZ'):
            value = cmds.getAttr('%s.%s' % (ctrl, attr))
            if not almost(value, 0.0):
                failures.append('%s.%s is %.4f, expected a clean 0'
                                % (ctrl, attr, value))
    print('clean zeros      : %s' % [cmds.getAttr(c + '.position')
                                     for c in rig['controls']])
    print('basePosition     : %s' % [cmds.getAttr(c + '.basePosition')
                                     for c in rig['controls']])

    # --- 控制器正好落在自己的 basePosition 上 ---------------------------
    # 轨道曲线是线性的,落位应该是精确的,不留逼近误差的余量
    for ctrl in rig['controls']:
        gap = gap_to_joints(ctrl, rig['joints'],
                            cmds.getAttr(ctrl + '.basePosition'))
        if gap > 1e-3:
            failures.append('ctrl %s sits %.4f away from its place on the '
                            'chain' % (ctrl, gap))

    # --- 旋转控制器只影响衰减范围内的骨骼 -------------------------------
    ctrl = rig['controls'][1]
    cmds.setAttr(ctrl + '.falloffMin', 5)
    cmds.setAttr(ctrl + '.falloffMax', 5)
    cmds.setAttr(ctrl + '.normalize', 0)
    cmds.setAttr(ctrl + '.rotateZ', 10)

    position = cmds.getAttr(ctrl + '.basePosition')
    rotations = [cmds.getAttr(j + '.rotateZ') for j in rig['joints']]
    peak = rotations.index(max(rotations))
    if abs(peak - position) > 1.0:
        failures.append('peak influence at joint %d, control at %.2f'
                        % (peak, position))
    if not almost(rotations[0], 0.0):
        failures.append('root joint should be outside the falloff')
    if not almost(rotations[-1], 0.0):
        failures.append('tip joint should be outside the falloff')
    inside = [r for r in rotations if r > 1e-6]
    print('influenced joints: %d, peak %.4f at joint %d'
          % (len(inside), max(rotations), peak))

    # --- 链条弯了以后,没动过的控制器也必须跟着走,不能留在原地 -----------
    # 用一个大衰减把整条链带弯,然后检查每个控制器还贴在自己那根骨骼上。
    cmds.setAttr(ctrl + '.falloffMax', 40)
    cmds.setAttr(ctrl + '.rotateZ', 60)
    drifted = [gap_to_joints(other, rig['joints'],
                             cmds.getAttr(other + '.basePosition'))
               for other in rig['controls']]
    print('bent follow      : max gap %.5f between ctrl and its joint'
          % max(drifted))
    if max(drifted) > 1e-3:
        failures.append('controls stayed behind when the chain bent, '
                        'max gap %.4f' % max(drifted))
    # 末端控制器确实被带离了原位(否则上面的检查可能只是"都没动")
    tip_ctrl = cmds.xform(rig['controls'][-1], q=True, ws=True, t=True)
    if almost(tip_ctrl[0], span, 1e-2) and almost(tip_ctrl[1], 0.0, 1e-2):
        failures.append('tip control never moved, the bend test is vacuous')
    print('tip ctrl moved to: [%.2f, %.2f, %.2f]' % tuple(tip_ctrl))
    cmds.setAttr(ctrl + '.rotateZ', 10)
    cmds.setAttr(ctrl + '.falloffMax', 5)

    # --- 归一化模式:被影响骨骼的旋转之和等于输入值 ---------------------
    cmds.setAttr(ctrl + '.normalize', 1)
    total = sum(cmds.getAttr(j + '.rotateZ') for j in rig['joints'])
    print('normalized sum   : %.4f (input 10.0)' % total)
    if not almost(total, 10.0, 1e-3):
        failures.append('normalized sum is %.4f, expected 10.0' % total)

    cmds.setAttr(ctrl + '.normalize', 0)
    raw = sum(cmds.getAttr(j + '.rotateZ') for j in rig['joints'])
    print('raw sum          : %.4f' % raw)
    if raw <= 10.0:
        failures.append('raw mode should over-shoot the input')

    # --- 滑动控制器,影响区域跟着走(position 是相对 basePosition 的偏移)--
    cmds.setAttr(ctrl + '.position', 30 - position)
    rotations = [cmds.getAttr(j + '.rotateZ') for j in rig['joints']]
    peak = rotations.index(max(rotations))
    if abs(peak - 30) > 1.0:
        failures.append('after sliding, peak is at joint %d not 30' % peak)
    cpos = cmds.xform(ctrl, q=True, ws=True, t=True)
    jpos = cmds.xform(rig['joints'][30], q=True, ws=True, t=True)
    if not almost(cpos[0], jpos[0], 1e-3):
        failures.append('control did not slide with position: %.4f vs %.4f'
                        % (cpos[0], jpos[0]))
    print('after slide      : peak at joint %d, ctrl x %.3f' % (peak, cpos[0]))

    # --- position 推到头时被钳住,控制器不会滑出链条 -----------------------
    # basePosition 13 + position 39 = 52,应该被钳回末端骨骼 39。
    # 先把旋转归零,链条恢复笔直,末端骨骼才精确落在曲线末端上可比。
    cmds.setAttr(ctrl + '.rotateZ', 0)
    limit = cmds.attributeQuery('position', node=ctrl, maximum=True)[0]
    cmds.setAttr(ctrl + '.position', limit)
    cpos = cmds.xform(ctrl, q=True, ws=True, t=True)
    tip = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
    if not almost(cpos[0], tip[0], 1e-3):
        failures.append('over-driven position not clamped: %.3f vs %.3f'
                        % (cpos[0], tip[0]))
    print('clamp test       : base %.0f + position %.0f -> x %.3f (tip %.3f)'
          % (position, limit, cpos[0], tip[0]))
    cmds.setAttr(ctrl + '.position', 30 - position)
    cmds.setAttr(ctrl + '.rotateZ', 10)

    # --- 面片:顶点数、蒙皮、跟随骨骼 --------------------------------------
    plane = rig['plane']
    if not plane or not cmds.objExists(plane):
        failures.append('no bind plane was created')
    else:
        vertices = cmds.polyEvaluate(plane, vertex=True)
        if vertices != len(rig['joints']) * 2:
            failures.append('plane has %d verts, expected %d'
                            % (vertices, len(rig['joints']) * 2))
        if not rig['skin_cluster'] or not cmds.objExists(rig['skin_cluster']):
            failures.append('plane is not skinned')
        # 绑定姿势下,面片最后一行应该骑在末端骨骼上
        tip = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
        row = [cmds.pointPosition('%s.vtx[%d]' % (plane, vertices - 2 + i),
                                  world=True) for i in (0, 1)]
        centre = [(row[0][k] + row[1][k]) * 0.5 for k in range(3)]
        if not almost(centre[0], tip[0], 1e-2):
            failures.append('plane tip row at %.3f, joint tip at %.3f'
                            % (centre[0], tip[0]))
        print('plane            : %s, %d verts, skin %s'
              % (plane, vertices, rig['skin_cluster']))

        # 掰一下控制器,面片必须跟着骨骼走
        before = cmds.pointPosition('%s.vtx[%d]' % (plane, vertices - 1),
                                    world=True)
        cmds.setAttr(ctrl + '.rotateZ', 25)
        after = cmds.pointPosition('%s.vtx[%d]' % (plane, vertices - 1),
                                   world=True)
        moved = max(abs(after[k] - before[k]) for k in range(3))
        print('plane follows    : tip vert moved %.3f' % moved)
        if moved < 1e-3:
            failures.append('plane does not follow the joints')
        cmds.setAttr(ctrl + '.rotateZ', 10)

    # --- 控制器缩放:按衰减权重分摊,范围外的骨骼保持 1 ---------------------
    cmds.setAttr(ctrl + '.rotateZ', 0)
    cmds.setAttr(ctrl + '.position', 0)
    base = cmds.getAttr(ctrl + '.basePosition')
    for attr in ('scaleY', 'scaleZ'):
        if cmds.getAttr('%s.%s' % (ctrl, attr), lock=True):
            failures.append('%s.%s is still locked' % (ctrl, attr))
        if not almost(cmds.getAttr('%s.%s' % (ctrl, attr)), 1.0):
            failures.append('%s.%s should default to 1.0' % (ctrl, attr))
    # 沿链条方向的 X 必须保持锁死
    if not cmds.getAttr(ctrl + '.scaleX', lock=True):
        failures.append('scaleX must stay locked, it stretches the chain')

    # 面片是 XZ 平面上的平带子,宽度沿骨骼局部 Z 轴,所以要缩 scaleZ 才看得见;
    # scaleY 对一个零厚度的平面不产生视觉变化(骨骼本身的值仍然是对的)。
    cmds.setAttr(ctrl + '.scaleZ', 3.0)
    scales = [cmds.getAttr(j + '.scaleZ') for j in rig['joints']]
    peak = scales.index(max(scales))
    print('ctrl scale       : peak %.4f at joint %d (base %.0f)'
          % (max(scales), peak, base))
    if not almost(max(scales), 3.0, 1e-3):
        failures.append('peak joint scaleZ is %.4f, expected 3.0'
                        % max(scales))
    if abs(peak - base) > 1.0:
        failures.append('scale peak at joint %d, control at %.0f'
                        % (peak, base))
    if not (almost(scales[0], 1.0) and almost(scales[-1], 1.0)):
        failures.append('joints outside the falloff must stay at scale 1')

    # 面片应该在那一段鼓起来,而且正好鼓 3 倍
    if plane and cmds.objExists(plane):
        bulge = row_width(plane, peak)
        flat = row_width(plane, 0)
        print('plane bulge      : %.3f at peak vs %.3f at root (ratio %.3f)'
              % (bulge, flat, bulge / flat))
        if not almost(bulge / flat, 3.0, 1e-3):
            failures.append('plane bulge ratio %.3f, expected 3.0'
                            % (bulge / flat))
    # 截面缩放不能改变链条的长度/走向 —— 这正是把 scaleX 锁死换来的性质
    tip_before = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
    cmds.setAttr(ctrl + '.scaleY', 4.0)
    cmds.setAttr(ctrl + '.scaleZ', 4.0)
    tip_after = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
    drift = max(abs(tip_after[k] - tip_before[k]) for k in range(3))
    print('chain drift      : %.6f (cross-section scale must not stretch)'
          % drift)
    if drift > 1e-6:
        failures.append('cross-section scale moved the chain by %.5f' % drift)
    cmds.setAttr(ctrl + '.scaleY', 1.0)
    cmds.setAttr(ctrl + '.scaleZ', 1.0)

    # --- 整体缩放(视频 29 秒:选中总控放大整套绑定)------------------------
    width_before = row_width(plane, 0) if plane else None
    cmds.setAttr(rig['global_ctrl'] + '.scale', 2, 2, 2)
    tip = cmds.xform(rig['joints'][-1], q=True, ws=True, t=True)
    if not almost(tip[0], span * 2.0, 1e-2):
        failures.append('scaled tip at %.3f, expected %.3f'
                        % (tip[0], span * 2.0))
    cpos = cmds.xform(rig['controls'][-1], q=True, ws=True, t=True)
    if not almost(cpos[0], span * 2.0, 0.05):
        failures.append('scaled control at %.3f, expected %.3f'
                        % (cpos[0], span * 2.0))
    print('scaled tip       : %.3f (expected %.3f)' % (tip[0], span * 2.0))

    # 面片是被蒙皮的:它必须跟着骨骼落在 40,而不是被变换两遍到 80
    if plane and cmds.objExists(plane):
        vertices = cmds.polyEvaluate(plane, vertex=True)
        row = [cmds.pointPosition('%s.vtx[%d]' % (plane, vertices - 2 + i),
                                  world=True) for i in (0, 1)]
        centre = (row[0][0] + row[1][0]) * 0.5
        print('scaled plane tip : %.3f (expected %.3f)' % (centre,
                                                           span * 2.0))
        if not almost(centre, span * 2.0, 1e-2):
            failures.append('plane double-transformed: %.3f, expected %.3f'
                            % (centre, span * 2.0))

        # 宽度方向也必须跟着放大 —— 只验证长度是不够的
        width_after = row_width(plane, 0)
        print('scaled plane wid : %.3f -> %.3f (ratio %.3f)'
              % (width_before, width_after, width_after / width_before))
        if not almost(width_after / width_before, 2.0, 1e-3):
            failures.append('plane width ratio %.3f, expected 2.0'
                            % (width_after / width_before))

    cmds.setAttr(rig['global_ctrl'] + '.scale', 1, 1, 1)

    # --- 没有循环依赖 ------------------------------------------------------
    cycles = cmds.cycleCheck(all=True, list=True) or []
    if cycles:
        failures.append('cycles: %s' % cycles[:5])

    # --- 关掉 V_min / V_max ------------------------------------------------
    cmds.file(new=True, force=True)
    curve = cmds.curve(degree=1, point=[(0, 0, 0), (10, 0, 0)], name='c2')
    rig2 = core.build(curve, prefix='nofall_', num_controls=2, num_joints=10,
                      use_falloff_min=False, use_falloff_max=False,
                      normalized=True)
    ctrl = rig2['controls'][0]
    if cmds.objExists(ctrl + '.falloffMin'):
        failures.append('falloffMin should not exist when V_min is off')
    cmds.setAttr(ctrl + '.rotateY', 20)
    total = sum(cmds.getAttr(j + '.rotateY') for j in rig2['joints'])
    print('V_min/V_max off  : normalized sum %.4f (input 20.0)' % total)
    if not almost(total, 20.0, 1e-3):
        failures.append('fixed-falloff normalized sum is %.4f' % total)

    # --- 关掉控制器缩放:scale 应该锁死,也不该驱动骨骼 ----------------------
    cmds.file(new=True, force=True)
    curve = cmds.curve(degree=1, point=[(0, 0, 0), (10, 0, 0)], name='c5')
    rig3 = core.build(curve, prefix='noscl_', num_controls=2, num_joints=8,
                      use_control_scale=False)
    ctrl3 = rig3['controls'][0]
    locked = [cmds.getAttr('%s.%s' % (ctrl3, a), lock=True)
              for a in ('scaleX', 'scaleY', 'scaleZ')]
    driven = cmds.listConnections(rig3['joints'][0] + '.scaleY',
                                  source=True, destination=False)
    print('scale locked off : %s, joint.scale driven by %s' % (locked, driven))
    if not all(locked):
        failures.append('scale should be locked when the option is off')
    if driven:
        failures.append('joint.scale should stay free when the option is off')

    # --- 不生成面片时轨道曲线照样要工作,basePosition 也可以不是整数 --------
    cmds.file(new=True, force=True)
    curve = cmds.curve(degree=1, point=[(0, 0, 0), (10, 0, 0)], name='c6')
    rig4 = core.build(curve, prefix='nopl_', num_controls=3, num_joints=12,
                      create_plane=False)
    bases = [cmds.getAttr(c + '.basePosition') for c in rig4['controls']]
    cmds.setAttr(rig4['controls'][0] + '.falloffMax', 12)
    cmds.setAttr(rig4['controls'][0] + '.rotateZ', 45)
    gaps = [gap_to_joints(c, rig4['joints'], b)
            for c, b in zip(rig4['controls'], bases)]
    print('no-plane bent    : bases %s, max gap %.6f' % (bases, max(gaps)))
    if rig4['plane'] is not None:
        failures.append('plane should not exist when create_plane is off')
    if max(gaps) > 1e-3:
        failures.append('without a plane the controls drifted %.4f'
                        % max(gaps))

    # --- 边界情况:1 个控制器 / 最少骨骼 -----------------------------------
    cmds.file(new=True, force=True)
    curve = cmds.curve(degree=1, point=[(0, 0, 0), (5, 0, 0)], name='c3')
    core.build(curve, prefix='tiny_', num_controls=1, num_joints=2)
    print('edge case        : 1 control / 2 joints built')

    # --- 中文/非法前缀会被清洗成合法节点名 ---------------------------------
    cmds.file(new=True, force=True)
    curve = cmds.curve(degree=1, point=[(0, 0, 0), (5, 0, 0)], name='c4')
    rig4 = core.build(curve, prefix=u'触手 01-', num_controls=1, num_joints=3)
    print('prefix sanitised : %s' % rig4['root'])
    if not cmds.objExists(rig4['root']):
        failures.append('sanitised prefix produced an invalid name')

    print('')
    if failures:
        print('FAILED:')
        for item in failures:
            print('  - %s' % item)
        return 1
    print('ALL CHECKS PASSED')
    return 0


if __name__ == '__main__':
    code = main()
    try:
        maya.standalone.uninitialize()
    except Exception:
        pass
    sys.exit(code)
