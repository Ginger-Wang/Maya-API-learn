# -*- coding: utf-8 -*-
"""构建器用到的 cmds 薄封装。

这里没有什么花活,目的只是让 :mod:`variableFK.core` 读起来清爽一点,
并且把每个工具节点的创建都收敛成一行。
"""

import maya.cmds as cmds


# --------------------------------------------------------------------- 杂项
def shape_of(node):
    """返回 ``node`` 下第一个非中间态 shape(没有就返回 None)。

    一律返回完整 DAG 路径:复制出来的曲线经常和源曲线共用短名,
    名字一旦有歧义,connectAttr 会悄悄连到错误的那一个。
    """
    if cmds.nodeType(node) in ('nurbsCurve', 'mesh', 'nurbsSurface'):
        return cmds.ls(node, long=True)[0]
    shapes = cmds.listRelatives(node, shapes=True, noIntermediate=True,
                                fullPath=True) or []
    return shapes[0] if shapes else None


def is_nurbs_curve(node):
    """判断 ``node`` 是不是一条 NURBS 曲线(传 transform 或 shape 都行)。"""
    shape = shape_of(node) if cmds.objExists(node) else None
    return bool(shape) and cmds.nodeType(shape) == 'nurbsCurve'


def set_color(node, index):
    """给 ``node`` 的所有 shape 套上线框显示颜色。"""
    for shape in cmds.listRelatives(node, shapes=True, noIntermediate=True) or []:
        cmds.setAttr(shape + '.overrideEnabled', 1)
        cmds.setAttr(shape + '.overrideColor', index)


def lock_hide(node, attrs):
    """锁定并从通道盒里隐藏指定属性。"""
    for attr in attrs:
        plug = '{0}.{1}'.format(node, attr)
        cmds.setAttr(plug, lock=True, keyable=False, channelBox=False)


def add_float(node, name, value=0.0, minimum=None, maximum=None,
              keyable=True, nice=None):
    """添加一个 float 属性,返回它的 plug 字符串。"""
    kwargs = {'longName': name, 'attributeType': 'double',
              'defaultValue': value, 'keyable': keyable}
    if nice:
        kwargs['niceName'] = nice
    if minimum is not None:
        kwargs['minValue'] = minimum
    if maximum is not None:
        kwargs['maxValue'] = maximum
    cmds.addAttr(node, **kwargs)
    plug = '{0}.{1}'.format(node, name)
    cmds.setAttr(plug, value)
    return plug


def add_separator(node, name='rigAttrs'):
    """在通道盒里加一条分隔线。"""
    cmds.addAttr(node, longName=name, niceName='_' * 12,
                 attributeType='enum', enumName='____')
    cmds.setAttr('{0}.{1}'.format(node, name), keyable=False,
                 channelBox=True, lock=True)


# ------------------------------------------------------------------ 工具节点
def multiply_divide(name, operation=1):
    """operation:1 = 乘,2 = 除,3 = 幂。"""
    node = cmds.createNode('multiplyDivide', name=name)
    cmds.setAttr(node + '.operation', operation)
    return node


def plus_minus(name, operation=1):
    """operation:1 = 求和,2 = 相减,3 = 求平均。"""
    node = cmds.createNode('plusMinusAverage', name=name)
    cmds.setAttr(node + '.operation', operation)
    return node


def condition(name, operation=5):
    """operation:0 ==,1 !=,2 >,3 >=,4 <,5 <=。"""
    node = cmds.createNode('condition', name=name)
    cmds.setAttr(node + '.operation', operation)
    return node


def remap_smooth(name, input_min, input_max, output_min=0.0, output_max=1.0):
    """把 remapValue 接成一条带钳制的平滑过渡(smooth-step)曲线。

    超出 ``[input_min, input_max]`` 的值由节点自己钳制,
    这正好就是我们想要的"衰减范围之外不产生影响"——链条两端自动收敛。
    """
    node = cmds.createNode('remapValue', name=name)
    cmds.setAttr(node + '.inputMin', input_min)
    cmds.setAttr(node + '.inputMax', input_max)
    cmds.setAttr(node + '.outputMin', output_min)
    cmds.setAttr(node + '.outputMax', output_max)
    # 两个 spline 关键点 => 缓入缓出,而不是线性直上直下
    for i, (position, value) in enumerate(((0.0, 0.0), (1.0, 1.0))):
        cmds.setAttr('{0}.value[{1}].value_Position'.format(node, i), position)
        cmds.setAttr('{0}.value[{1}].value_FloatValue'.format(node, i), value)
        cmds.setAttr('{0}.value[{1}].value_Interp'.format(node, i), 3)
    return node


def clamp(name, minimum, maximum):
    """创建一个只用 R 通道的 clamp 节点。"""
    node = cmds.createNode('clamp', name=name)
    cmds.setAttr(node + '.minR', minimum)
    cmds.setAttr(node + '.maxR', maximum)
    return node


def blend_two(name, value_a=0.0, value_b=0.0):
    """创建 blendTwoAttr,用于在两个标量之间混合。"""
    node = cmds.createNode('blendTwoAttr', name=name)
    cmds.setAttr(node + '.input[0]', value_a)
    cmds.setAttr(node + '.input[1]', value_b)
    return node


def connect_scalar_to_triple(scalar_plug, node, attr):
    """把一个 float 同时接到复合属性的 X / Y / Z 三个子属性上。"""
    for axis in 'XYZ':
        cmds.connectAttr(scalar_plug, '{0}.{1}{2}'.format(node, attr, axis))
