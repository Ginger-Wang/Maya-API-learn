# -*- coding: utf-8 -*-
"""可变 FK 绑定工具的 Maya 界面。

布局照着参考视频来:前缀、两个滑杆、V_min / V_max 开关、载入曲线、创建绑定。
用纯 ``maya.cmds`` 搭建,所以从 Maya 2018 到 2026 都能跑,
不用管 PySide2 还是 PySide6。
"""
import traceback
import maya.cmds as cmds

from . import core
from . import nodes as nd


WINDOW = 'variableFkRiggerWindow'
TITLE = u'可变 FK 绑定工具 (Variable FK Rigger)'

_widgets = {}


# -------------------------------------------------------------------- 回调
def _load_curve(*_args):
    """把当前选中的 NURBS 曲线填进输入框。"""
    selection = cmds.ls(selection=True, long=False) or []
    if not selection:
        cmds.warning(u'请先选中一条 NURBS 曲线,再点 Load Curve。')
        return
    curve = selection[0]
    if not nd.is_nurbs_curve(curve):
        cmds.warning(u'"{0}" 不是 NURBS 曲线。'.format(curve))
        return
    cmds.textField(_widgets['curve'], edit=True, text=curve)


def _create_rig(*_args):
    """读取界面参数并调用构建器。"""
    curve = cmds.textField(_widgets['curve'], query=True, text=True).strip()
    if not curve:
        cmds.warning(u'还没载入曲线 —— 选中一条后点 Load Curve。')
        return
    if not cmds.objExists(curve):
        cmds.warning(u'"{0}" 在场景里已经不存在了。'.format(curve))
        return

    kwargs = {
        'curve': curve,
        'prefix': cmds.textField(_widgets['prefix'], query=True, text=True),
        'num_controls': cmds.intSliderGrp(_widgets['controls'], query=True,
                                          value=True),
        'num_joints': cmds.intSliderGrp(_widgets['joints'], query=True,
                                        value=True),
        'use_falloff_min': cmds.checkBox(_widgets['v_min'], query=True,
                                         value=True),
        'use_falloff_max': cmds.checkBox(_widgets['v_max'], query=True,
                                         value=True),
        'normalized': cmds.checkBox(_widgets['normalized'], query=True,
                                    value=True),
        'create_plane': cmds.checkBox(_widgets['plane'], query=True,
                                      value=True),
        'use_control_scale': cmds.checkBox(_widgets['ctrl_scale'],
                                           query=True, value=True),
    }

    try:
        result = core.build(**kwargs)
    except Exception as error:                            # noqa: BLE001
        traceback.print_exc()
        cmds.confirmDialog(title=u'可变 FK 绑定工具', icon='critical',
                           message=u'{0}'.format(error), button=[u'确定'])
        return

    cmds.inViewMessage(
        assistMessage=u'已创建 <hl>{0}</hl>:{1} 根骨骼,{2} 个控制器。'.format(
            result['root'], len(result['joints']), len(result['controls'])),
        position='midCenter', fade=True)


def _reset(*_args):
    """把界面恢复成默认值。"""
    cmds.textField(_widgets['prefix'], edit=True, text='test_')
    cmds.intSliderGrp(_widgets['controls'], edit=True, value=4)
    cmds.intSliderGrp(_widgets['joints'], edit=True, value=40)
    cmds.checkBox(_widgets['v_min'], edit=True, value=True)
    cmds.checkBox(_widgets['v_max'], edit=True, value=True)
    cmds.checkBox(_widgets['normalized'], edit=True, value=False)
    cmds.checkBox(_widgets['plane'], edit=True, value=True)
    cmds.checkBox(_widgets['ctrl_scale'], edit=True, value=True)
    cmds.textField(_widgets['curve'], edit=True, text='')


# -------------------------------------------------------------------- 窗口
def show():
    """打开(或重新打开)工具窗口。"""
    if cmds.window(WINDOW, exists=True):
        cmds.deleteUI(WINDOW)

    window = cmds.window(WINDOW, title=TITLE, sizeable=True,
                         widthHeight=(460, 300), menuBar=True)

    cmds.menu(label=u'帮助', helpMenu=True)
    cmds.menuItem(label=u'恢复默认设置', command=_reset)
    cmds.menuItem(label=u'关于', command=_about)

    cmds.columnLayout('vfkMain', adjustableColumn=True, rowSpacing=4,
                      columnAttach=('both', 10))

    cmds.separator(height=6, style='none')
    cmds.text(label=u'ENTER PREFIX  /  命名前缀', font='smallBoldLabelFont')
    _widgets['prefix'] = cmds.textField(
        text='test_', annotation=u'所有新建节点的命名前缀(只支持英文和数字)。')

    cmds.separator(height=10, style='none')
    cmds.text(label=u'ADJUST RIG SETTING  /  绑定参数',
              font='smallBoldLabelFont')

    _widgets['controls'] = cmds.intSliderGrp(
        label=u'控制器数量', field=True, value=4,
        minValue=1, maxValue=12, fieldMinValue=1, fieldMaxValue=50,
        columnWidth3=(110, 45, 240), adjustableColumn=3,
        annotation=u'沿链条浮动的可变 FK 控制器个数。')

    _widgets['joints'] = cmds.intSliderGrp(
        label=u'绑定骨骼数量', field=True, value=40,
        minValue=2, maxValue=100, fieldMinValue=2, fieldMaxValue=400,
        columnWidth3=(110, 45, 240), adjustableColumn=3,
        annotation=u'沿基础曲线均匀铺设的绑定骨骼数量。')

    cmds.rowLayout(numberOfColumns=3, columnWidth3=(80, 80, 200),
                   columnAlign3=('left', 'left', 'left'),
                   columnAttach3=('both', 'both', 'both'))
    _widgets['v_min'] = cmds.checkBox(
        label='V_min', value=True,
        annotation=u'在控制器上暴露根部一侧的衰减属性 falloffMin。')
    _widgets['v_max'] = cmds.checkBox(
        label='V_max', value=True,
        annotation=u'在控制器上暴露末端一侧的衰减属性 falloffMax。')
    _widgets['normalized'] = cmds.checkBox(
        label=u'归一化模式', value=False,
        annotation=u'控制器默认开启归一化:被影响骨骼的旋转量'
                   u'加起来正好等于你填的数值。')
    cmds.setParent('..')

    cmds.rowLayout(numberOfColumns=2, columnWidth2=(160, 200),
                   columnAlign2=('left', 'left'),
                   columnAttach2=('both', 'both'))
    _widgets['plane'] = cmds.checkBox(
        label=u'生成蒙皮面片', value=True,
        annotation=u'顺带生成一块沿骨骼链的面片,并蒙皮到这些骨骼上。')
    _widgets['ctrl_scale'] = cmds.checkBox(
        label=u'开放控制器缩放', value=True,
        annotation=u'解锁 FK 控制器的 scale,按同一套衰减权重分摊给骨骼,'
                   u'可以做触手局部变粗/变细。关掉则锁死 scale。')
    cmds.setParent('..')

    cmds.separator(height=10, style='none')
    cmds.button(label=u'Load Curve  /  载入曲线', height=24,
                command=_load_curve,
                annotation=u'把当前选中的 NURBS 曲线作为基础曲线。')
    _widgets['curve'] = cmds.textField(
        text='', annotation=u'绑定所依附的基础曲线。')

    cmds.separator(height=6, style='none')
    cmds.button(label=u'Create Rig  /  创建绑定', height=30,
                command=_create_rig, backgroundColor=(0.36, 0.52, 0.36))
    cmds.separator(height=8, style='none')

    cmds.setParent('..')
    cmds.showWindow(window)
    return window


def _about(*_args):
    cmds.confirmDialog(
        title=u'关于',
        message=(u'可变 FK 绑定工具 (Variable FK Rigger)\n\n'
                 u'构建一套"可变 FK"/触手绑定:控制器沿密集骨骼链滑动,'
                 u'并把自身旋转按衰减范围分摊给范围内的骨骼。\n\n'
                 u'思路由 Cameron Black 提出并推广,本工具是独立的'
                 u'节点化实现。'),
        button=[u'确定'])
