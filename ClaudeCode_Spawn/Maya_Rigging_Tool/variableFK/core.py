# -*- coding: utf-8 -*-
"""可变 FK 绑定构建器。

复刻经典的 "Cameron Black 触手绑定" 思路:

*   沿一条基础 NURBS 曲线铺一串密集的绑定骨骼。
*   几个控制器浮在这串骨骼上。每个控制器有一个 ``position`` 属性
    (以骨骼序号为单位)和一个衰减范围,它会把自己旋转的 *一部分*
    分摊给衰减范围内的每一根骨骼。
*   因为骨骼本身是真实的父子层级,这些分摊值会逐节累加,
    于是链条围绕控制器平滑地弯曲,而不是在某一节上硬折。

每个控制器 *c* 对每根骨骼 *j* 的权重计算::

    d  = j - position                       # 有符号距离,单位是骨骼序号
    s  = d / falloffMin   if d <= 0         # 衰减边缘处为 -1 ……
         -d / falloffMax  if d >  0         # …… 控制器所在处为 0
    w  = smoothstep(remap(s, -1 -> 0, 0 -> 1))
    joint[j].rotate += control.rotate * k * w

默认模式下 ``k`` 为 1;当控制器的 ``normalize`` 属性打开时 ``k = 1 / sum(w)``,
也就是"归一化模式"——被影响的骨骼旋转量加起来正好等于你填进控制器的数值。

整套网络只用普通工具节点搭建:不用表达式、不用脚本节点,
因此能在并行/GPU 求值模式下正常运算,引用(reference)进场也不会出问题。
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

from . import nodes as nd

# 迭代调试用:改完 nodes.py 不必重启 Maya。
# Python 2(Maya 2020 及更早)没有 importlib.reload,得回落到内置 reload。
try:
    from importlib import reload as _reload
except ImportError:                                       # Maya 2019 / py2
    _reload = reload                                      # type: ignore # noqa: F821
_reload(nd)

DEFAULT_PREFIX = 'vfk_'

COLOR_GLOBAL = 17      # 黄色
COLOR_CONTROL = 18     # 浅蓝
COLOR_JOINT = 13       # 红色


# =============================================================== 曲线相关工具
def _curve_fn(curve):
    """拿到曲线 shape 的 MFnNurbsCurve。"""
    sel = om.MSelectionList()
    sel.add(curve)
    dag = sel.getDagPath(0)
    dag.extendToShape()
    return om.MFnNurbsCurve(dag)


def sample_curve(curve, count):
    """沿曲线 *按弧长* 均匀取 ``count`` 个世界坐标点。

    用弧长而不是参数值,可以保证 CV 分布不均的曲线上骨骼间距依然均匀;
    而且这和 ``motionPath.fractionMode`` 的算法一致,
    所以控制器能准确落在它对应的骨骼上。
    """
    fn = _curve_fn(curve)
    total = fn.length()
    points = []
    for i in range(count):
        fraction = 0.0 if count < 2 else i / float(count - 1)
        length = min(max(total * fraction, 0.0), total)
        param = fn.findParamFromLength(length)
        point = fn.getPointAtParam(param, om.MSpace.kWorld)
        points.append((point.x, point.y, point.z))
    return points


def curve_length(curve):
    """曲线弧长。"""
    return _curve_fn(curve).length()


# ================================================================== 绑定部件
def _build_joint_chain(points, prefix):
    """在给定点位上建一条骨骼链,并统一朝向。"""
    cmds.select(clear=True)
    joints = []
    for i, point in enumerate(points):
        joint = cmds.joint(name='{0}bind_{1:03d}_jnt'.format(prefix, i),
                           position=point)
        joints.append(joint)

    cmds.joint(joints[0], edit=True, orientJoint='xyz',
               secondaryAxisOrient='yup', children=True, zeroScaleOrient=True)
    # 末端骨骼跟随父级朝向,避免留下一个无意义的旧朝向值
    cmds.setAttr(joints[-1] + '.jointOrient', 0.0, 0.0, 0.0)
    for joint in joints:
        cmds.setAttr(joint + '.radius', 0.0)
    return joints


def _circle(name, radius, normal=(1, 0, 0), color=None):
    """建一个圆形控制器曲线。"""
    ctrl = cmds.circle(name=name, normal=normal, radius=radius,
                       constructionHistory=False)[0]
    shape = cmds.listRelatives(ctrl, shapes=True)[0]
    cmds.rename(shape, ctrl + 'Shape')
    if color is not None:
        nd.set_color(ctrl, color)
    return ctrl


def _build_fk_control(prefix, index, curve_shape, num_joints, position,
                      falloff, size, use_min, use_max, normalized,
                      use_scale=True):
    """创建一个浮动控制器,并把它挂到 motionPath 上。"""
    tag = '{0}fk_{1:02d}'.format(prefix, index)

    path_grp = cmds.group(empty=True, name=tag + '_path_grp')
    offset_grp = cmds.group(empty=True, name=tag + '_offset_grp',
                            parent=path_grp)
    ctrl = _circle(tag + '_ctrl', size, normal=(1, 0, 0), color=COLOR_CONTROL)
    cmds.parent(ctrl, offset_grp)
    cmds.xform(ctrl, objectSpace=True, matrix=[1, 0, 0, 0, 0, 1, 0, 0,
                                               0, 0, 1, 0, 0, 0, 0, 1])

    # ---- 控制器属性 ----------------------------------------------------
    nd.add_separator(ctrl)
    # basePosition 属于"设置"而不是"动画":它记住控制器出厂时待的地方,
    # 于是 position 可以保持干净的 0 —— 归零、打关键帧、镜像都不用再记偏移量。
    base_plug = nd.add_float(ctrl, 'basePosition', position,
                             minimum=0.0, maximum=float(num_joints - 1),
                             keyable=False, nice='Base Position')
    cmds.setAttr(base_plug, channelBox=True)

    position_plug = nd.add_float(ctrl, 'position', 0.0,
                                 minimum=-float(num_joints - 1),
                                 maximum=float(num_joints - 1),
                                 nice='Position')

    # 实际位置 = basePosition + position,再钳回合法区间,
    # 这样动画师把 position 推到头也不会让控制器滑出链条。
    offset = cmds.createNode('addDoubleLinear', name=tag + '_position_adl')
    cmds.connectAttr(base_plug, offset + '.input1')
    cmds.connectAttr(position_plug, offset + '.input2')
    solved = nd.clamp(tag + '_position_clp', 0.0, float(num_joints - 1))
    cmds.connectAttr(offset + '.output', solved + '.inputR')
    solved_plug = solved + '.outputR'

    min_plug = None
    max_plug = None
    if use_min:
        min_plug = nd.add_float(ctrl, 'falloffMin', falloff, minimum=0.01,
                                nice='Falloff Min')
    if use_max:
        max_plug = nd.add_float(ctrl, 'falloffMax', falloff, minimum=0.01,
                                nice='Falloff Max')
    normalize_plug = nd.add_float(ctrl, 'normalize',
                                  1.0 if normalized else 0.0,
                                  minimum=0.0, maximum=1.0, nice='Normalize')

    # 缩放开放时把截面方向(Y/Z)留给动画师,它的中性值是 1 不是 0。
    # 沿链条方向的 X 始终锁死:Maya 骨骼的 scaleX 一定会把子骨骼顺着链条推走
    # (segmentScaleCompensate 只能阻止缩放继续向下累乘,消不掉这一次位移),
    # 那会让链条被拉长、控制器和骨骼也就对不上了。
    locked = ['tx', 'ty', 'tz', 'v', 'sx']
    if not use_scale:
        locked += ['sy', 'sz']
    nd.lock_hide(ctrl, locked)

    # ---- 让控制器沿基础曲线滑动 -----------------------------------------
    motion_path = cmds.createNode('motionPath', name=tag + '_mp')
    cmds.connectAttr(curve_shape + '.worldSpace[0]',
                     motion_path + '.geometryPath')
    cmds.setAttr(motion_path + '.fractionMode', True)
    cmds.setAttr(motion_path + '.follow', True)
    cmds.setAttr(motion_path + '.frontAxis', 0)      # X 指向链条前方
    cmds.setAttr(motion_path + '.upAxis', 1)         # Y 朝上
    cmds.setAttr(motion_path + '.worldUpType', 3)    # 向量模式
    cmds.setAttr(motion_path + '.worldUpVector', 0, 1, 0, type='double3')

    # 解算后的位置单位是骨骼序号,而 motionPath 要的是 0-1 的比例
    to_fraction = nd.multiply_divide(tag + '_uValue_md', operation=2)
    cmds.connectAttr(solved_plug, to_fraction + '.input1X')
    cmds.setAttr(to_fraction + '.input2X', float(max(num_joints - 1, 1)))
    cmds.connectAttr(to_fraction + '.outputX', motion_path + '.uValue')

    cmds.connectAttr(motion_path + '.allCoordinates', path_grp + '.translate')
    cmds.connectAttr(motion_path + '.rotate', path_grp + '.rotate')
    cmds.connectAttr(motion_path + '.rotateOrder', path_grp + '.rotateOrder')

    return {'ctrl': ctrl, 'path_grp': path_grp, 'offset_grp': offset_grp,
            'motion_path': motion_path,
            'position': solved_plug,          # 解算后的位置,供下游网络使用
            'position_attr': position_plug,   # 控制器上那个干净的 0
            'base_position': base_plug,
            'falloff_min': min_plug, 'falloff_max': max_plug,
            'normalize': normalize_plug}


def _build_bind_plane(prefix, joints, width):
    """沿骨骼链生成一块面片,并蒙皮到这些骨骼上。

    面片每一行顶点正好骑在一根骨骼上(沿骨骼局部 Z 轴左右各撑开半个宽度),
    所以每个顶点 100% 绑给对应骨骼就是数学上正确的权重,
    不需要再刷,也不会出现权重渗漏。
    """
    count = len(joints)

    plane = cmds.polyPlane(name=prefix + 'ribbon_geo',
                           width=1.0, height=1.0,
                           subdivisionsWidth=1, subdivisionsHeight=count - 1,
                           axis=(0, 1, 0), createUVs=2,
                           constructionHistory=False)[0]

    # 把顶点摆到骨骼上。polyPlane 的顶点按行排列:先沿宽度后沿高度,
    # 所以第 j 行的两个顶点是 vtx[j * 2] 和 vtx[j * 2 + 1]。
    half = width * 0.5
    for j, joint in enumerate(joints):
        matrix = cmds.xform(joint, query=True, worldSpace=True, matrix=True)
        origin = om.MVector(matrix[12], matrix[13], matrix[14])
        side = om.MVector(matrix[8], matrix[9], matrix[10])   # 局部 Z 轴
        if side.length() > 1e-9:
            side.normalize()
        for column in (0, 1):
            point = origin + side * (half if column else -half)
            cmds.xform('{0}.vtx[{1}]'.format(plane, j * 2 + column),
                       worldSpace=True, translation=(point.x, point.y,
                                                     point.z))

    skin = cmds.skinCluster(joints, plane, name=prefix + 'ribbon_skc',
                            toSelectedBones=True, bindMethod=0, skinMethod=0,
                            normalizeWeights=1, obeyMaxInfluences=False)[0]
    for j, joint in enumerate(joints):
        for column in (0, 1):
            cmds.skinPercent(skin, '{0}.vtx[{1}]'.format(plane,
                                                         j * 2 + column),
                             transformValue=[(joint, 1.0)])

    return plane, skin


def _build_weight_network(prefix, index, ctrl_data, joint_sums, falloff,
                          joint_scale_sums=None):
    """把一个控制器接到链条上的每一根骨骼。

    每个「控制器 x 骨骼」组合 5 个工具节点,每个控制器再额外 8 个;
    开放缩放时每个组合再多 1 个、每个控制器再多 1 个。
    """
    tag = '{0}c{1:02d}'.format(prefix, index)
    ctrl = ctrl_data['ctrl']
    num_joints = len(joint_sums)

    # 1 / falloffMin 和 -1 / falloffMax,每个控制器只算一次
    reciprocal = nd.multiply_divide(tag + '_recipFalloff_md', operation=2)
    cmds.setAttr(reciprocal + '.input1X', 1.0)
    cmds.setAttr(reciprocal + '.input1Y', -1.0)
    for plug, axis in ((ctrl_data['falloff_min'], 'X'),
                       (ctrl_data['falloff_max'], 'Y')):
        target = '{0}.input2{1}'.format(reciprocal, axis)
        if plug:
            cmds.connectAttr(plug, target)
        else:
            cmds.setAttr(target, falloff)

    weight_plugs = []
    for j in range(num_joints):
        jtag = '{0}_j{1:03d}'.format(tag, j)

        # 到控制器的有符号距离,单位是骨骼序号
        delta = nd.plus_minus(jtag + '_delta_pma', operation=2)
        cmds.setAttr(delta + '.input1D[0]', float(j))
        cmds.connectAttr(ctrl_data['position'], delta + '.input1D[1]')

        # X = d / falloffMin,Y = -d / falloffMax
        ratio = nd.multiply_divide(jtag + '_ratio_md', operation=1)
        cmds.connectAttr(delta + '.output1D', ratio + '.input1X')
        cmds.connectAttr(delta + '.output1D', ratio + '.input1Y')
        cmds.connectAttr(reciprocal + '.outputX', ratio + '.input2X')
        cmds.connectAttr(reciprocal + '.outputY', ratio + '.input2Y')

        # 根据骨骼落在控制器哪一侧,选用对应的那个分支
        side = nd.condition(jtag + '_side_cnd', operation=5)   # d <= 0
        cmds.connectAttr(delta + '.output1D', side + '.firstTerm')
        cmds.setAttr(side + '.secondTerm', 0.0)
        cmds.connectAttr(ratio + '.outputX', side + '.colorIfTrueR')
        cmds.connectAttr(ratio + '.outputY', side + '.colorIfFalseR')

        # -1(衰减边缘)..0(控制器处) -> 0..1,并做平滑
        weight = nd.remap_smooth(jtag + '_weight_rmv', -1.0, 0.0)
        cmds.connectAttr(side + '.outColorR', weight + '.inputValue')
        weight_plugs.append(weight + '.outValue')

    # ---- 归一化模式 ------------------------------------------------------
    total = nd.plus_minus(tag + '_weightSum_pma', operation=1)
    for i, plug in enumerate(weight_plugs):
        cmds.connectAttr(plug, '{0}.input1D[{1}]'.format(total, i))

    # 只缩小不放大:权重和若小于 1,除下去反而会把旋转放大到爆炸
    safe_total = nd.clamp(tag + '_weightSum_clp', 1.0, 1.0e6)
    cmds.connectAttr(total + '.output1D', safe_total + '.inputR')

    inverse = nd.multiply_divide(tag + '_weightSumInv_md', operation=2)
    cmds.setAttr(inverse + '.input1X', 1.0)
    cmds.connectAttr(safe_total + '.outputR', inverse + '.input2X')

    factor = nd.blend_two(tag + '_normalize_bta', value_a=1.0)
    cmds.connectAttr(inverse + '.outputX', factor + '.input[1]')
    cmds.connectAttr(ctrl_data['normalize'], factor + '.attributesBlender')

    scaled_rotation = nd.multiply_divide(tag + '_scaledRot_md', operation=1)
    cmds.connectAttr(ctrl + '.rotate', scaled_rotation + '.input1')
    nd.connect_scalar_to_triple(factor + '.output', scaled_rotation, 'input2')

    # ---- 把旋转推给各个骨骼 ----------------------------------------------
    for j, plug in enumerate(weight_plugs):
        contribution = nd.multiply_divide(
            '{0}_j{1:03d}_contrib_md'.format(tag, j), operation=1)
        cmds.connectAttr(scaled_rotation + '.output', contribution + '.input1')
        nd.connect_scalar_to_triple(plug, contribution, 'input2')
        cmds.connectAttr(contribution + '.output',
                         '{0}.input3D[{1}]'.format(joint_sums[j], index))

    # ---- 缩放:同一套权重,但走"增量累加",且不经过归一化 --------------------
    # 缩放的中性值是 1,所以分摊的是"偏离 1 的增量",控制器 scale 为 1 时零影响。
    # 这里刻意不乘归一化因子:归一化是为了让旋转沿链条累加到输入值,
    # 而缩放并不累加(骨骼开了 segmentScaleCompensate),除以权重和只会把它压没。
    if joint_scale_sums is None:
        return

    delta = nd.plus_minus(tag + '_scaleDelta_pma', operation=2)
    cmds.connectAttr(ctrl + '.scale', delta + '.input3D[0]')
    cmds.setAttr(delta + '.input3D[1]', 1.0, 1.0, 1.0, type='double3')

    for j, plug in enumerate(weight_plugs):
        contribution = nd.multiply_divide(
            '{0}_j{1:03d}_sclContrib_md'.format(tag, j), operation=1)
        cmds.connectAttr(delta + '.output3D', contribution + '.input1')
        nd.connect_scalar_to_triple(plug, contribution, 'input2')
        # input3D[0] 被常量 1 占着,所以控制器从 1 号槽位开始
        cmds.connectAttr(contribution + '.output',
                         '{0}.input3D[{1}]'.format(joint_scale_sums[j],
                                                   index + 1))


# ==================================================================== 主入口
def build(curve=None, prefix=DEFAULT_PREFIX, num_controls=4, num_joints=40,
          use_falloff_min=True, use_falloff_max=True, falloff=None,
          normalized=False, control_size=None,
          create_plane=True, plane_width=None, use_control_scale=True):
    """沿 ``curve`` 构建一套可变 FK 绑定。

    参数:
        curve: 基础 NURBS 曲线的 transform(或 shape)。留空则取当前选择。
        prefix: 所有新建节点的命名前缀。
        num_controls: 浮动控制器数量。
        num_joints: 沿曲线铺设的绑定骨骼数量。
        use_falloff_min: 暴露 ``falloffMin`` 属性(根部一侧)。
        use_falloff_max: 暴露 ``falloffMax`` 属性(末端一侧)。
        falloff: 默认衰减宽度,单位是骨骼序号。默认约等于一个控制器分到的长度。
        normalized: 控制器是否一开始就处于归一化模式。
        control_size: 控制器半径,默认按曲线长度取一个比例。
        create_plane: 是否顺带生成一块蒙皮到骨骼上的面片。
        plane_width: 面片宽度,默认按曲线长度取一个比例。
        use_control_scale: 开放 FK 控制器的缩放,按衰减权重分摊给骨骼
            (做局部变粗/变细)。关掉则把控制器的 scale 锁上。

    返回:
        描述这套绑定的 dict(组、骨骼、控制器等)。
    """
    # ------------------------------------------------------------ 参数校验
    if curve is None:
        selection = cmds.ls(selection=True, long=False) or []
        curve = selection[0] if selection else None
    if not curve or not cmds.objExists(curve):
        raise ValueError(u'没有指定基础曲线 —— 请先选中一条 NURBS 曲线。')
    if not nd.is_nurbs_curve(curve):
        raise ValueError(u'"{0}" 不是 NURBS 曲线。'.format(curve))

    num_joints = int(num_joints)
    num_controls = int(num_controls)
    if num_joints < 2:
        raise ValueError(u'num_joints 至少为 2。')
    if num_controls < 1:
        raise ValueError(u'num_controls 至少为 1。')

    prefix = _sanitize_prefix(prefix)
    root_name = prefix + 'rig_grp'
    if cmds.objExists(root_name):
        raise ValueError(u'"{0}" 已存在 —— 请换一个前缀。'.format(root_name))

    length = curve_length(curve)
    if falloff is None:
        falloff = max(1.0, (num_joints - 1) / float(num_controls))
    if control_size is None:
        control_size = max(length * 0.06, 0.05)
    if plane_width is None:
        plane_width = max(length * 0.08, 0.05)

    # --------------------------------------------------------------- 构建
    cmds.undoInfo(openChunk=True, chunkName='Build Variable FK Rig')
    try:
        root_grp = cmds.group(empty=True, name=root_name)

        global_ctrl = _circle(prefix + 'global_ctrl', max(length * 0.25, 0.1),
                              normal=(0, 1, 0), color=COLOR_GLOBAL)
        cmds.parent(global_ctrl, root_grp)
        nd.lock_hide(global_ctrl, ['v'])
        nd.add_separator(global_ctrl, 'rigVis')
        joint_vis = nd.add_float(global_ctrl, 'jointVis', 0.0, minimum=0.0,
                                 maximum=1.0, nice='Joint Vis')
        ctrl_vis = nd.add_float(global_ctrl, 'controlVis', 1.0, minimum=0.0,
                                maximum=1.0, nice='Control Vis')
        for plug in (joint_vis, ctrl_vis):
            cmds.setAttr(plug, keyable=False, channelBox=True)

        curve_grp = cmds.group(empty=True, name=prefix + 'curve_grp',
                               parent=global_ctrl)
        joint_grp = cmds.group(empty=True, name=prefix + 'joint_grp',
                               parent=global_ctrl)
        ctrl_grp = cmds.group(empty=True, name=prefix + 'control_grp',
                              parent=global_ctrl)
        # 控制器是按世界空间贴着曲线走的,所以这一层不能再继承一次
        # 总控的变换,否则会叠加两遍
        cmds.setAttr(ctrl_grp + '.inheritsTransform', 0)

        # 复制一份自己用,不动用户原来的曲线
        base_curve = cmds.duplicate(curve, name=prefix + 'base_crv',
                                    returnRootsOnly=True)[0]
        for attr in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz'):
            cmds.setAttr('{0}.{1}'.format(base_curve, attr), lock=False)
        base_curve = cmds.ls(cmds.parent(base_curve, curve_grp)[0],
                             long=True)[0]
        # 复制出来的 shape 会和源曲线共用短名,导致后面所有 plug 都有歧义
        cmds.rename(nd.shape_of(base_curve), prefix + 'base_crvShape')
        cmds.setAttr(base_curve + '.visibility', 0)
        curve_shape = nd.shape_of(base_curve)

        # ---- 骨骼 --------------------------------------------------------
        points = sample_curve(base_curve, num_joints)
        joints = _build_joint_chain(points, prefix)
        cmds.parent(joints[0], joint_grp)
        nd.set_color(joints[0], COLOR_JOINT)
        cmds.connectAttr(joint_vis, joint_grp + '.visibility')
        cmds.connectAttr(ctrl_vis, ctrl_grp + '.visibility')

        # 每根骨骼一个累加节点 —— 每个控制器往自己那一路输入里写
        joint_sums = []
        for i, joint in enumerate(joints):
            total = nd.plus_minus('{0}j{1:03d}_rotSum_pma'.format(prefix, i),
                                  operation=1)
            cmds.connectAttr(total + '.output3D', joint + '.rotate')
            joint_sums.append(total)

        # 缩放同理,但 input3D[0] 固定成 1 作为中性值
        joint_scale_sums = None
        if use_control_scale:
            joint_scale_sums = []
            for i, joint in enumerate(joints):
                total = nd.plus_minus(
                    '{0}j{1:03d}_sclSum_pma'.format(prefix, i), operation=1)
                cmds.setAttr(total + '.input3D[0]', 1.0, 1.0, 1.0,
                             type='double3')
                # 只接截面方向:scaleX 会沿链条把骨骼推走,见 _build_fk_control
                cmds.connectAttr(total + '.output3Dy', joint + '.scaleY')
                cmds.connectAttr(total + '.output3Dz', joint + '.scaleZ')
                joint_scale_sums.append(total)
                # 开着 SSC,缩放才不会沿链条一路累乘放大
                cmds.setAttr(joint + '.segmentScaleCompensate', 1)

        # ---- 控制器 ------------------------------------------------------
        controls = []
        for i in range(num_controls):
            if num_controls == 1:
                position = 0.0
            else:
                position = i * (num_joints - 1) / float(num_controls - 1)
            data = _build_fk_control(prefix, i + 1, curve_shape, num_joints,
                                     position, falloff, control_size,
                                     use_falloff_min, use_falloff_max,
                                     normalized, use_control_scale)
            cmds.parent(data['path_grp'], ctrl_grp)
            # 上面关掉了 inheritsTransform,这里把总控的缩放再接回来
            cmds.connectAttr(global_ctrl + '.scale',
                             data['path_grp'] + '.scale')
            _build_weight_network(prefix, i, data, joint_sums, falloff,
                                  joint_scale_sums)
            controls.append(data['ctrl'])

        # ---- 蒙皮面片 ----------------------------------------------------
        plane = None
        skin = None
        if create_plane:
            plane, skin = _build_bind_plane(prefix, joints, plane_width)
            # 几何体挂在 rig_grp 下、而不是总控下:蒙皮结果里已经包含了
            # 骨骼的世界变换,再继承一层就会被变换两遍。
            geo_grp = cmds.group(empty=True, name=prefix + 'geo_grp',
                                 parent=root_grp)
            cmds.setAttr(geo_grp + '.inheritsTransform', 0)
            plane = cmds.parent(plane, geo_grp)[0]

        bind_set = cmds.sets(joints, name=prefix + 'bind_joints_set')
        cmds.select(global_ctrl, replace=True)
    finally:
        cmds.undoInfo(closeChunk=True)

    return {'root': root_grp, 'global_ctrl': global_ctrl,
            'joints': joints, 'controls': controls,
            'curve': base_curve, 'bind_set': bind_set,
            'joint_grp': joint_grp, 'control_grp': ctrl_grp,
            'plane': plane, 'skin_cluster': skin}


_SAFE_CHARS = set('abcdefghijklmnopqrstuvwxyz'
                  'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')


def _sanitize_prefix(prefix):
    """把前缀里 Maya 不接受的字符换成下划线。

    只放行 ASCII 字母数字和下划线:Maya 的节点名不支持中文,
    而 Python 3 的 ``isalnum()`` 对中文会返回 True,不能拿来判断。
    """
    prefix = (prefix or DEFAULT_PREFIX).strip()
    if not prefix:
        prefix = DEFAULT_PREFIX
    cleaned = ''.join(c if c in _SAFE_CHARS else '_' for c in prefix)
    if cleaned[0].isdigit():
        cleaned = '_' + cleaned
    return cleaned
