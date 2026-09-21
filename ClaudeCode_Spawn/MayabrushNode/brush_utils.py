# -*- coding: utf-8 -*-
"""
brushTipCurve 的搭建工具。

纯 cmds,不是插件的一部分 —— 插件只管解算,这里管「怎么把线接对」。
手工接线最容易错的四处都在 build_brush() 里处理掉了:

    1. mesh 必须连 worldMesh[0](不是 outMesh),否则纸一移动碰撞位置就错
    2. 定位器必须连 worldMatrix[0],且索引 0 是毛根、最大索引是笔尖朝向
    3. 输出曲线的 transform 要把 worldInverseMatrix[0] 连回节点,
       否则曲线 transform 一旦不在原点,整条毛就会偏移
    4. bristleLength 要填上,否则毛长会跟着定位器间距跑 —— 拖笔尖往纸里压的
       同时毛也在变长,既不物理,接触判据也跟着漂

在 Maya 中使用:
    import sys; sys.path.append(r"H:/.../MayabrushNode")
    import brush_utils
    brush_utils.build_brush()
"""

import math
import os

import maya.cmds as cmds

PLUGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "brushTipCurveNode.py")


# 四种笔刷的出厂预设。索引必须和节点里 brushType 的 addField 顺序一致。
#
# 节点自己**不会**用这张表去改 stiffness —— DG 节点的 compute 不允许回写自己的
# 输入属性,硬来会造成循环求值。所以「选了类型就有对应手感」这件事放在这里做:
# 切换类型时填一次推荐值,填完之后你调成多少就是多少,再切类型才会再填一次。
BRUSH_PRESETS = {
    "calligraphy": {"index": 0, "stiffness": 0.20, "width": 0.06,
                    "spread": 1.2, "flatten": 0.65,
                    "label": "毛笔:圆锥笔锋,软,压下去铺得长"},
    "round":       {"index": 1, "stiffness": 0.50, "width": 0.07,
                    "spread": 0.8, "flatten": 0.50,
                    "label": "绘画笔:圆头,中等硬度"},
    "flat":        {"index": 2, "stiffness": 0.80, "width": 0.09,
                    "spread": 0.5, "flatten": 0.35,
                    "label": "毛刷:平头扁刷,硬,画宽笔画"},
    "fan":         {"index": 3, "stiffness": 0.65, "width": 0.09,
                    "spread": 0.7, "flatten": 0.45,
                    "label": "扇形笔:扁而散开,画树枝头发纹理"},
}

# 反查:enum 下标 -> 名字
BRUSH_NAMES = dict((preset["index"], name)
                   for name, preset in BRUSH_PRESETS.items())


def ensure_plugin():
    """确保插件已加载。重复调用是安全的。"""
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)


def set_width_profile(node, segments):
    """设置 5 段手动宽度倍率,从毛根排到笔尖。

    参数:
        node     brushTipCurve 节点名
        segments 长度 1-5 的倍率序列;不足 5 个时后面补 1.0

    说明:
        这是**乘在 brushType 廓形之上**的,全 1.0 表示不干预。
        想完全自己塑形,先把 brushType 设成 "flat"(等宽廓形)再用这个。

        例:笔肚鼓、笔锋尖的毛笔
            set_brush_type(node, "flat")
            set_width_profile(node, [0.8, 1.3, 1.2, 0.7, 0.05])
    """
    values = list(segments)[:5]
    values += [1.0] * (5 - len(values))
    for index, value in enumerate(values):
        cmds.setAttr("{0}.widthSegment{1}".format(node, index + 1),
                     max(0.0, value))
    return values


def set_brush_type(node, brush_type, apply_feel=True):
    """切换笔刷类型,顺带把该类型的推荐手感参数填上。

    参数:
        node        brushTipCurve 节点名
        brush_type  "calligraphy" / "round" / "flat" / "fan",或者 enum 下标
        apply_feel  True 时连 stiffness / brushWidth / 压力响应一起填;
                    False 则只换类型,手感参数原样不动

    返回:
        用上的那份预设 dict。

    说明:
        填进去的只是**起点**,不锁定 —— 之后你把 stiffness 调成多少就是多少,
        直到下一次再调用本函数。想只换廓形不动手感,传 apply_feel=False。
    """
    if isinstance(brush_type, int):
        brush_type = BRUSH_NAMES.get(brush_type, "calligraphy")
    preset = BRUSH_PRESETS.get(brush_type)
    if preset is None:
        raise ValueError(
            "未知的笔刷类型 {0!r},可选:{1}".format(
                brush_type, ", ".join(sorted(BRUSH_PRESETS))))

    cmds.setAttr(node + ".brushType", preset["index"])
    if apply_feel:
        cmds.setAttr(node + ".stiffness", preset["stiffness"])
        cmds.setAttr(node + ".brushWidth", preset["width"])
        cmds.setAttr(node + ".spreadByPressure", preset["spread"])
        cmds.setAttr(node + ".flattenByPressure", preset["flatten"])
    return preset


def chain_length(positions):
    """一串位置连成的折线长度。"""
    return sum(
        math.sqrt(sum((positions[i][k] - positions[i - 1][k]) ** 2
                      for k in range(3)))
        for i in range(1, len(positions)))


def build_brush(mesh=None, name="brush",
                root_pos=(0.0, 3.0, 0.0), tip_pos=(0.0, 0.0, 0.0),
                extra_positions=(), brush_type="calligraphy",
                stiffness=None, samples=24, bristle_length=None,
                build_mesh=True, width_profile=None):
    """搭一套完整的笔刷:定位器 + brushTipCurve + 输出曲线,并接好全部连线。

    参数:
        mesh            纸张/地面的 **shape** 名;None 表示暂时不接,之后再连
        name            命名前缀
        root_pos        毛根(笔杆与刷毛连接处)定位器的位置
        tip_pos         笔尖定位器的位置
        extra_positions 插在毛根和笔尖之间的额外定位器位置,从毛根往笔尖排
        brush_type      "calligraphy" / "round" / "flat" / "fan",决定廓形和
                        一整套推荐手感参数,见 BRUSH_PRESETS
        stiffness       毛硬度 0-1;None 表示用该类型的推荐值
        samples         输出曲线的 CV 数
        bristle_length  毛长;None 表示按初始定位器间距量一次并写死
        build_mesh      是否顺带建一个 mesh 接上 outMesh(实体笔刷)
        width_profile   5 段手动宽度倍率(毛根 → 笔尖);None 表示不干预类型廓形

    返回:
        dict,含 node / curve / curveTransform / locators / root / tip,
        build_mesh=True 时还有 mesh / meshTransform

    说明:
        毛长写进 bristleLength 之后就固定了,**笔尖定位器从此只决定朝向**:
        它指哪毛往哪长,但拖远拖近都不会改变毛的长度(真实笔刷压下去只会弯,
        不会变长)。所以摆完初始姿势再调用本函数,毛长就是那个姿势的长度。

        定位器都建在世界空间下、没有父物体。真正绑定时把毛根定位器约束到笔杆
        控制器、笔尖定位器约束到笔尖控制器即可,节点读的是 worldMatrix,
        父子关系怎么搭都不影响解算。
    """
    ensure_plugin()

    if bristle_length is None:
        bristle_length = chain_length(
            [root_pos] + list(extra_positions) + [tip_pos])

    node = cmds.createNode("brushTipCurve", name=name + "_solver")
    cmds.setAttr(node + ".bristleLength", bristle_length)
    cmds.setAttr(node + ".samples", samples)
    # 先套类型预设,再让显式传进来的 stiffness 覆盖它
    set_brush_type(node, brush_type)
    if stiffness is not None:
        cmds.setAttr(node + ".stiffness", stiffness)
    if width_profile is not None:
        set_width_profile(node, width_profile)

    curve_transform = cmds.createNode("transform", name=name + "_curve")
    curve = cmds.createNode("nurbsCurve", name=name + "_curveShape",
                            parent=curve_transform)
    cmds.connectAttr(node + ".outCurve", curve + ".create")
    # 把曲线自己的世界逆矩阵接回去,这样无论 transform 被挪到哪、被 parent 到谁
    # 底下,解算出来的世界空间形状都不会跟着偏移。
    cmds.connectAttr(curve_transform + ".worldInverseMatrix[0]",
                     node + ".parentInverseMatrix")

    if mesh:
        cmds.connectAttr(mesh + ".worldMesh[0]", node + ".inMesh")

    brush_mesh = None
    if build_mesh:
        # mesh shape 和曲线挂在**同一个** transform 下。节点只有一个
        # parentInverseMatrix,两个输出必然处在同一个空间;各给一个 transform
        # 的话,只要两者位置不同,毛和曲线就会错开。
        brush_mesh = cmds.createNode("mesh", name=name + "_meshShape",
                                     parent=curve_transform)
        cmds.connectAttr(node + ".outMesh", brush_mesh + ".inMesh")
        cmds.sets(brush_mesh, edit=True, forceElement="initialShadingGroup")

    positions = [root_pos] + list(extra_positions) + [tip_pos]
    labels = ["root"] + ["mid{0}".format(i + 1) for i in range(len(extra_positions))] \
        + ["tip"]
    locators = []
    for i, (pos, label) in enumerate(zip(positions, labels)):
        loc = cmds.spaceLocator(name="{0}_{1}".format(name, label))[0]
        cmds.setAttr(loc + ".translate", *pos)
        cmds.connectAttr(loc + ".worldMatrix[0]",
                         "{0}.controlMatrix[{1}]".format(node, i))
        locators.append(loc)

    return {"node": node, "curve": curve, "curveTransform": curve_transform,
            "mesh": brush_mesh, "brushType": brush_type,
            "locators": locators, "root": locators[0], "tip": locators[-1]}


def style_locators(locators, scale=0.3):
    """把定位器放大、染色,方便在视口里抓。毛根红、笔尖绿、中间黄。"""
    colors = {0: 13, len(locators) - 1: 14}   # 13=红, 14=绿, 17=黄
    for i, loc in enumerate(locators):
        for axis in "XYZ":
            cmds.setAttr("{0}.localScale{1}".format(loc, axis), scale)
        shape = cmds.listRelatives(loc, shapes=True)[0]
        cmds.setAttr(shape + ".overrideEnabled", True)
        cmds.setAttr(shape + ".overrideColor", colors.get(i, 17))
