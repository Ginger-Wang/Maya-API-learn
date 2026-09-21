# -*- coding: utf-8 -*-
"""
brushTipCurve 节点的独立自测脚本。

    "C:/Program Files/Autodesk/Maya2025/bin/mayapy.exe" selftest.py

既可以在 mayapy 中运行,也可以直接在 Maya 的脚本编辑器里执行本文件
(已经处于 Maya 会话中时会跳过 maya.standalone 的初始化)。

断言全部是数值断言,不依赖任何目视检查。重点盯住模型的两条不变量:

    弧长守恒 —— 刷毛不可伸长,输出点连成的折线总长必须恒等于定位器间距
    不穿透   —— 任何一个点都不许落到纸面以下

这两条只要有一条被破坏,笔刷压下去就会出现穿模或者毛忽长忽短,而这两种毛病在
视口里未必一眼看得出来,却会在渲染和 sweep mesh 上暴露。

print 一律用英文:Windows 控制台默认 cp1252,打中文会直接 UnicodeEncodeError
把测试打断。中文只出现在注释和 docstring 里。
"""

import math
import os
import sys

PLUGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "brushTipCurveNode.py")

_IN_MAYA = "maya" in sys.executable.lower() and "mayapy" in sys.executable.lower()
if _IN_MAYA:
    import maya.standalone
    maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.OpenMaya as om  # noqa: E402

FAILURES = []
CHECKS = [0]


# ---------------------------------------------------------------------------
# 检查与数值辅助
# ---------------------------------------------------------------------------

def check(condition, message):
    """记录并打印单项检查结果。"""
    CHECKS[0] += 1
    if condition:
        print("  ok   - {0}".format(message))
    else:
        print("  FAIL - {0}".format(message))
        FAILURES.append(message)


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def vclose(a, b, tol=1e-6):
    return all(abs(a[i] - b[i]) <= tol for i in range(len(a)))


def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def polyline_length(pts):
    """折线总长。

    说明:
        节点把采样点**直接当作 CV**,所以这个长度就是模型里的刷毛弧长,
        degree=1 和 degree=3 都一样 —— degree 只影响曲线怎么在 CV 之间穿行,
        不影响 CV 本身的位置。
    """
    return sum(dist(pts[i], pts[i - 1]) for i in range(1, len(pts)))


# ---------------------------------------------------------------------------
# 场景构造
# ---------------------------------------------------------------------------

def build(root_pos=(0.0, 0.4, 0.0), tip_pos=(0.3, -0.8, 0.0),
          extra_locators=(), plane=True, plane_size=20.0, plane_div=8, **attrs):
    """新建场景,搭一套「纸面 + 定位器 + brushTipCurve + 输出曲线」。

    参数:
        root_pos / tip_pos  毛根、笔尖定位器的位置
        extra_locators      插在两者之间的额外定位器位置,用来测多定位器
        plane               False 时不建纸面(测没有 mesh 的兜底)
        attrs               其余关键字直接 setAttr 到节点上

    返回:
        dict,含 node / curve / root / tip / mesh / locators
    """
    cmds.file(new=True, force=True)
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)

    node = cmds.createNode("brushTipCurve", name="brushSolver")
    curve = cmds.createNode("nurbsCurve", name="brushCurveShape")
    cmds.connectAttr(node + ".outCurve", curve + ".create")
    brush_mesh = cmds.createNode("mesh", name="brushMeshShape")
    cmds.connectAttr(node + ".outMesh", brush_mesh + ".inMesh")

    mesh = None
    if plane:
        transform = cmds.polyPlane(w=plane_size, h=plane_size,
                                   sx=plane_div, sy=plane_div, ax=(0, 1, 0))[0]
        mesh = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        cmds.connectAttr(mesh + ".worldMesh[0]", node + ".inMesh")

    # 毛根在索引 0,笔尖在最大索引,中间的额外定位器按顺序插进去。
    positions = [root_pos] + list(extra_locators) + [tip_pos]
    locators = []
    for i, pos in enumerate(positions):
        loc = cmds.spaceLocator(name="bristle{0}".format(i))[0]
        cmds.setAttr(loc + ".translate", *pos)
        cmds.connectAttr(loc + ".worldMatrix[0]",
                         "{0}.controlMatrix[{1}]".format(node, i))
        locators.append(loc)

    for attr, value in attrs.items():
        cmds.setAttr("{0}.{1}".format(node, attr), value)

    return {"node": node, "curve": curve, "mesh": mesh,
            "brushMesh": brush_mesh,
            "root": locators[0], "tip": locators[-1], "locators": locators}


def mesh_rings(rig):
    """求值并把输出 mesh 的顶点按截面环组织成 [[(x,y,z) × sides], ...]。

    顶点是按「环优先」顺序生成的(第 i 环的 sides 个点连续排列),
    所以直接按 sides 切片就是一圈一圈的截面。
    """
    cmds.dgeval(rig["node"] + ".outMesh")
    selection = om.MSelectionList()
    selection.add(rig["brushMesh"])
    dag_path = om.MDagPath()
    selection.getDagPath(0, dag_path)
    fn_mesh = om.MFnMesh(dag_path)

    points = om.MPointArray()
    fn_mesh.getPoints(points, om.MSpace.kWorld)
    flat = [(points[i].x, points[i].y, points[i].z)
            for i in range(points.length())]
    sides = cmds.getAttr(rig["node"] + ".meshSides")
    return [flat[i:i + sides] for i in range(0, len(flat), sides)]


def ring_diameter(ring):
    """环上最远两点的距离,也就是这一圈的最大直径。"""
    return max(dist(a, b) for a in ring for b in ring)


def ring_center(ring):
    return tuple(sum(p[k] for p in ring) / float(len(ring)) for k in range(3))


def cvs(rig):
    """求值并读回输出曲线的全部 CV(世界空间)。"""
    cmds.dgeval(rig["node"] + ".outCurve")
    shape = rig["curve"]
    count = cmds.getAttr(shape + ".spans") + cmds.getAttr(shape + ".degree")
    return [cmds.pointPosition("{0}.cv[{1}]".format(shape, i), world=True)
            for i in range(count)]


def bristle_length(rig):
    """定位器连成的折线长度,也就是刷毛应该恒定保持的总弧长。"""
    pts = [cmds.getAttr(loc + ".translate")[0] for loc in rig["locators"]]
    return polyline_length(pts)


def out(rig, attr):
    cmds.dgeval(rig["node"] + ".outCurve")
    return cmds.getAttr("{0}.{1}".format(rig["node"], attr))


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------

def test_no_contact_is_straight():
    """验证笔尖悬空时刷毛保持定位器给定的自然形状。

    验证内容:
        两个定位器、笔尖停在纸面上方时,输出必须是一条直线,首尾精确落在两个
        定位器上,弧长等于两者间距,且 outContact / outPressure 都为 0。
    为什么重要:
        这是「没压下去」的基准态。如果悬空时就已经被弯了,说明接触判据把
        够不着的情况误判成了接触,后面所有压深相关的行为都不可信。
    场景构造:
        毛根 (0, 2, 0),笔尖 (1, 0.4, 0),纸面在 y=0,笔尖离纸面还有 0.4。
    """
    print("[test] tip above the paper stays a straight line")
    rig = build(root_pos=(0.0, 2.0, 0.0), tip_pos=(1.0, 0.4, 0.0))
    pts = cvs(rig)
    length = bristle_length(rig)

    check(vclose(pts[0], (0.0, 2.0, 0.0), 1e-6), "first CV sits on the root locator")
    check(vclose(pts[-1], (1.0, 0.4, 0.0), 1e-6), "last CV sits on the tip locator")
    check(close(polyline_length(pts), length, 1e-6),
          "arc length {0:.6f} == locator distance {1:.6f}".format(
              polyline_length(pts), length))
    check(out(rig, "outContact") == 0, "outContact is 0")
    check(close(out(rig, "outPressure"), 0.0), "outPressure is 0")

    # 直线判据:每个点到首尾连线的距离都应为 0
    a, b = pts[0], pts[-1]
    ab = [b[i] - a[i] for i in range(3)]
    ab_len = math.sqrt(sum(v * v for v in ab))
    max_dev = 0.0
    for p in pts:
        ap = [p[i] - a[i] for i in range(3)]
        cross = (ap[1] * ab[2] - ap[2] * ab[1],
                 ap[2] * ab[0] - ap[0] * ab[2],
                 ap[0] * ab[1] - ap[1] * ab[0])
        max_dev = max(max_dev, math.sqrt(sum(v * v for v in cross)) / ab_len)
    check(max_dev < 1e-9, "all CVs are collinear (max deviation {0:.2e})".format(max_dev))


def test_arclength_is_conserved():
    """验证刷毛不可伸长:不管压多深、毛多软,总弧长恒定。

    验证内容:
        在多组压深 × 多组硬度下,输出折线的总长必须恒等于定位器间距。
    为什么重要:
        这是整个模型的核心不变量。弧长一旦随压深漂移,笔杆 sweep 出来的毛就会
        忽长忽短,而且说明空中段的积分或者贴地段的分配算错了 —— 这类错误在
        视口里看起来「好像也还行」,只有量出来才发现。
    场景构造:
        笔尖固定在 (0.3, -0.8, 0) 扎进纸里,毛根高度从 0.45 一路降到 0.05,
        每个高度再扫一遍 stiffness。
    """
    print("[test] arc length stays constant across depth and stiffness")
    rig = build()
    worst = 0.0
    for height in (0.45, 0.35, 0.25, 0.15, 0.05):
        cmds.setAttr(rig["root"] + ".translate", 0.0, height, 0.0)
        for stiffness in (0.0, 0.25, 0.5, 0.75, 1.0):
            cmds.setAttr(rig["node"] + ".stiffness", stiffness)
            pts = cvs(rig)
            err = abs(polyline_length(pts) - bristle_length(rig))
            worst = max(worst, err)
    check(worst < 1e-5,
          "worst arc length error over 25 combinations is {0:.2e}".format(worst))


def test_never_penetrates():
    """验证刷毛任何一点都不会落到纸面以下。

    验证内容:
        压深 × 硬度的组合下,所有 CV 的 Y 都 >= 0(允许 1e-6 的浮点容差)。
    为什么重要:
        穿模是这类节点最刺眼的失败。模型保证不穿透靠的是「空中段高度单调下降到 0、
        贴地段恒在 0」,这里就是在核对那个保证真的成立,而不是靠事后 clamp 兜出来的。
        顺带也保证了 degree=3:三次曲线落在 CV 凸包内,CV 都不穿,曲线也不会穿。
    场景构造:
        同上,纸面在 y=0。
    """
    print("[test] no CV ever drops below the paper")
    rig = build()
    worst = 0.0
    for height in (0.45, 0.35, 0.25, 0.15, 0.05):
        cmds.setAttr(rig["root"] + ".translate", 0.0, height, 0.0)
        for stiffness in (0.0, 0.5, 1.0):
            cmds.setAttr(rig["node"] + ".stiffness", stiffness)
            worst = min(worst, min(p[1] for p in cvs(rig)))
    check(worst > -1e-6, "lowest CV across 15 combinations is {0:+.2e}".format(worst))


def test_lands_tangent_to_paper():
    """验证刷毛落到纸面时是「相切」而不是「戳进去」。

    验证内容:
        空中段末尾那几个点的高度应该已经降到 0,且贴地段完全水平
        (各点 Y 相同),说明俯角确实衰减到了 0。
    为什么重要:
        相切落地是不穿透的前提。如果落地时还带着俯角,下一段要么插进纸里,
        要么得硬拐一个折角 —— 前者穿模,后者在毛上留下一个尖点。
    场景构造:
        毛根 (0, 0.4, 0),笔尖 (0.3, -0.8, 0),软硬取中间值。
    """
    print("[test] bristle lands tangent to the paper")
    rig = build()
    pts = cvs(rig)
    tail = [p for p in pts if p[1] < 1e-6]
    check(len(tail) >= 2, "at least two CVs are lying on the paper")
    spread = max(p[1] for p in tail) - min(p[1] for p in tail)
    check(spread < 1e-6,
          "grounded CVs share one height (spread {0:.2e})".format(spread))
    check(close(pts[-1][1], 0.0, 1e-6), "the very tip rests on the paper")


def test_stiffness_drives_spread():
    """验证硬度单调地控制铺开量:毛越软,躺在纸上的部分越长。

    验证内容:
        stiffness 从 1.0 扫到 0.0,outPressure(贴地长度占毛长的比例)必须单调递增。
    为什么重要:
        这是用户唯一要调的手感参数,方向反了就完全不能用。实现时这里确实踩过坑:
        弯曲剖面的指数写成 >1 时,软毛反而怎么压都接触不到纸面。
    场景构造:
        固定压深,只扫 stiffness。
    """
    print("[test] softer bristles spread further along the paper")
    rig = build()
    previous = -1.0
    monotonic = True
    values = []
    for stiffness in (1.0, 0.75, 0.5, 0.25, 0.0):
        cmds.setAttr(rig["node"] + ".stiffness", stiffness)
        pressure = out(rig, "outPressure")
        values.append(pressure)
        if pressure <= previous:
            monotonic = False
        previous = pressure
    check(monotonic,
          "outPressure rises as stiffness falls: {0}".format(
              ", ".join("{0:.4f}".format(v) for v in values)))
    check(values[-1] - values[0] > 0.05,
          "soft-vs-hard spread differs by {0:.4f}".format(values[-1] - values[0]))


def test_deeper_press_spreads_more():
    """验证压得越深,贴地段越长。

    验证内容:
        毛根高度从 0.45 降到 0.05,outPressure 单调递增。
    为什么重要:
        这是「压力」这个输出的语义所在 —— 下游要拿它驱动笔迹宽度和墨色浓度,
        不单调的话笔画粗细会在中途反向。
    场景构造:
        笔尖固定扎在纸下,只降毛根。
    """
    print("[test] pressing deeper increases the grounded fraction")
    rig = build()
    previous = -1.0
    monotonic = True
    values = []
    for height in (0.45, 0.35, 0.25, 0.15, 0.05):
        cmds.setAttr(rig["root"] + ".translate", 0.0, height, 0.0)
        pressure = out(rig, "outPressure")
        values.append(pressure)
        if pressure <= previous:
            monotonic = False
        previous = pressure
    check(monotonic, "outPressure rises with depth: {0}".format(
        ", ".join("{0:.4f}".format(v) for v in values)))


def test_envelope_zero_disables():
    """验证 envelope=0 时节点完全不改变刷毛形状。

    验证内容:
        压到纸里但把 envelope 关掉,输出应该和定位器连成的直线完全重合
        (笔尖仍在纸面以下),outContact 为 0。
    为什么重要:
        envelope 是绑定师临时关效果、做 A/B 对比的开关。它必须是干净的 0,
        而不是「弯得少一点」,否则没法用来定位问题。
    场景构造:
        毛根 (0, 0.4, 0),笔尖 (0.3, -0.8, 0),envelope=0。
    """
    print("[test] envelope=0 leaves the bristle untouched")
    rig = build(envelope=0.0)
    pts = cvs(rig)
    check(vclose(pts[0], (0.0, 0.4, 0.0), 1e-6), "first CV on the root locator")
    check(vclose(pts[-1], (0.3, -0.8, 0.0), 1e-6),
          "last CV still at the tip locator, below the paper")
    check(out(rig, "outContact") == 0, "outContact is 0 when the effect is off")


def test_vertical_press_flips_predictably():
    """验证笔杆扫过「完全垂直」时,倒向的翻转发生在确定的位置、且只发生一次。

    验证内容:
        笔尖横向位置从 +0.08 扫到 -0.08(中间经过完全垂直),笔尖落点应当:
          - 只在一步之内发生大幅换边,其余每一步都是小位移;
          - 换边恰好发生在通过垂直的那一步;
          - 换边前后两侧的铺开距离对称。
    为什么重要:
        这个翻转是**消不掉**的,不是 bug:真实毛笔垂直下压时向四周均匀散开,
        而单条中轴曲线必须选一边,左右倾之间必然翻 180 度。能做的是让它落在
        唯一讲得通的位置(正垂直那一刻),而不是被浮点噪声或某个阈值决定。
        实现上靠的是先把笔杆 X 轴回退方向翻到与倾斜方向同侧再混合 —— 少了这步,
        线性混合两个相反向量会在权重 0.5 处退化,翻转会跑到一个莫名其妙的角度上。
    场景构造:
        毛根固定 (0, 0.4, 0),笔尖 Y 固定 -0.8,X 从 +0.08 扫到 -0.08 共 33 步。
    """
    print("[test] sweeping through vertical flips the spread exactly once")
    rig = build()
    steps = 33
    xs, tips = [], []
    for i in range(steps):
        x = 0.08 - 0.16 * i / float(steps - 1)
        cmds.setAttr(rig["tip"] + ".translate", x, -0.8, 0.0)
        xs.append(x)
        tips.append(cvs(rig)[-1])

    jumps = [dist(tips[i], tips[i - 1]) for i in range(1, len(tips))]
    biggest = max(jumps)
    where = jumps.index(biggest)
    others = sorted(jumps)[:-1]

    check(max(others) < 0.02,
          "every step except the flip is small (largest {0:.5f})".format(max(others)))
    check(abs(xs[where]) < 0.006 and abs(xs[where + 1]) < 0.006,
          "the flip happens as the shaft passes vertical (x {0:+.4f} -> {1:+.4f})".format(
              xs[where], xs[where + 1]))
    check(close(tips[0][0], -tips[-1][0], 1e-4),
          "spread is symmetric either side of vertical ({0:+.4f} vs {1:+.4f})".format(
              tips[0][0], tips[-1][0]))

    # 近垂直时倒向必须被笔杆 X 轴锁住,不能被微小抖动带着来回翻。
    directions = []
    for x in (1e-5, 3e-5, 1e-4, 5e-4):
        cmds.setAttr(rig["tip"] + ".translate", x, -0.8, 0.0)
        directions.append(cvs(rig)[-1][0])
    check(all(d > 0.0 for d in directions),
          "tiny tilts on one side all spread the same way")


def test_shaft_roll_steers_spread():
    """验证完全垂直下压时,转动笔杆定位器能控制刷毛往哪边倒。

    验证内容:
        笔尖正下方垂直压入,毛根定位器 rotateY 取 0 / 90 / 180,
        笔尖的铺开方向必须跟着转过相同的角度。
    为什么重要:
        垂直下压时没有任何几何信息能决定倒向,节点回退到笔杆矩阵的局部 X 轴。
        这让绑定师转一下笔杆就能控制毛的朝向,符合真实转笔的直觉;
        如果回退方向写死成世界轴,转笔杆就完全失效了。
    场景构造:
        毛根 (0, 0.4, 0),笔尖 (0, -0.8, 0) 正下方,扫 rotateY。
    """
    print("[test] rolling the shaft steers the spread direction")
    rig = build(tip_pos=(0.0, -0.8, 0.0))
    directions = {}
    for angle in (0, 90, 180):
        cmds.setAttr(rig["root"] + ".rotateY", angle)
        tip = cvs(rig)[-1]
        directions[angle] = (tip[0], tip[2])

    radius = math.hypot(*directions[0])
    check(radius > 0.1, "the tip actually spreads out ({0:.4f})".format(radius))

    # rotateY 把局部 X 轴从 +X 转向 -Z,所以 90 度时铺开方向应该落在 -Z 上。
    check(vclose(directions[90], (0.0, -radius), 1e-4),
          "rotateY=90 spreads towards -Z: {0}".format(
              tuple(round(v, 4) for v in directions[90])))
    check(vclose(directions[180], (-radius, 0.0), 1e-4),
          "rotateY=180 spreads towards -X: {0}".format(
              tuple(round(v, 4) for v in directions[180])))


def test_multiple_locators():
    """验证三个以上定位器时的自然毛形和弧长守恒。

    验证内容:
        插一个中间定位器,悬空时曲线必须过这个点;压下去之后弧长仍等于
        定位器折线的总长。
    为什么重要:
        用户要「两个或多个定位器」。中间点用 Catmull-Rom 过点插值,选它就是
        因为它精确穿过控制点 —— 绑定师摆在哪毛就弯到哪,不会往里收。
    场景构造:
        毛根 (0, 2, 0)、中间 (0.4, 1.2, 0.25)、笔尖 (1.0, 0.5, 0),先悬空后压入。
    """
    print("[test] three locators shape the bristle and keep its length")
    rig = build(root_pos=(0.0, 2.0, 0.0),
                extra_locators=[(0.4, 1.2, 0.25)],
                tip_pos=(1.0, 0.5, 0.0),
                samples=60)
    pts = cvs(rig)
    check(out(rig, "outContact") == 0, "still airborne")

    middle = (0.4, 1.2, 0.25)
    nearest = min(dist(p, middle) for p in pts)
    check(nearest < 0.02,
          "the curve passes through the middle locator (gap {0:.5f})".format(nearest))
    # Catmull-Rom 是绕着控制点走的曲线,弧长本来就比定位器折线长一点点。
    check(polyline_length(pts) > bristle_length(rig),
          "the curved bristle is slightly longer than the locator polyline")

    # 压进纸里。基准不能用定位器折线长,要用「同一组定位器下的自然毛形长度」,
    # 也就是 envelope=0 时的输出 —— 守恒说的是压弯前后长度不变。
    cmds.setAttr(rig["root"] + ".translate", 0.0, 0.5, 0.0)
    cmds.setAttr(rig["locators"][1] + ".translate", 0.2, 0.1, 0.1)
    cmds.setAttr(rig["tip"] + ".translate", 0.5, -0.6, 0.0)

    cmds.setAttr(rig["node"] + ".envelope", 0.0)
    natural_length = polyline_length(cvs(rig))
    cmds.setAttr(rig["node"] + ".envelope", 1.0)
    pts = cvs(rig)
    check(out(rig, "outContact") == 1, "now pressed into the paper")
    # 容差比两定位器那条松一档:自然形是 Catmull-Rom 加密折线重采样出来的,
    # 重采样必然比原曲线略短,而压弯段走的是解析积分、长度取自加密折线。
    # 两者相差的就是这点重采样离散误差(~5e-5),不是守恒被破坏。
    check(close(polyline_length(pts), natural_length, 2e-4),
          "arc length survives the press ({0:.6f} vs natural {1:.6f})".format(
              polyline_length(pts), natural_length))
    check(min(p[1] for p in pts) > -1e-6, "nothing dips below the paper")


def test_tilted_ground():
    """验证倾斜纸面上同样不穿透、同样贴合。

    验证内容:
        纸面绕 X 轴转 30 度,所有 CV 到该斜面的有符号距离都 >= 0,
        且贴地段确实贴在斜面上(距离 ~ 0)。
    为什么重要:
        水平面上很多错误(比如误用世界 Y 当法线、把 mesh 的局部空间当世界空间)
        都看不出来,一旦纸面被旋转过就立刻暴露。这条专门用来钉死「法线取自
        实际命中面、坐标全程走世界空间」。
    场景构造:
        polyPlane 绕 X 轴 30 度,笔沿斜面法线方向压下去。
    """
    print("[test] tilted paper is respected")
    rig = build(root_pos=(0.0, 0.5, 0.0), tip_pos=(0.25, -0.7, 0.0))
    plane_transform = cmds.listRelatives(rig["mesh"], parent=True, fullPath=True)[0]
    cmds.setAttr(plane_transform + ".rotateX", 30.0)

    normal = (0.0, math.cos(math.radians(30.0)), math.sin(math.radians(30.0)))
    pts = cvs(rig)
    check(out(rig, "outContact") == 1, "contact detected on the tilted plane")

    heights = [sum(p[i] * normal[i] for i in range(3)) for p in pts]
    check(min(heights) > -1e-6,
          "lowest signed height above the tilted plane is {0:+.2e}".format(min(heights)))
    grounded = [h for h in heights if h < 1e-5]
    check(len(grounded) >= 2, "part of the bristle lies on the tilted plane")


def test_conform_to_uneven_ground():
    """验证起伏地面上 conformToSurface 能把贴地段拉回表面。

    验证内容:
        把纸面中间一条顶点抬高成一道坎,开启 conformToSurface 后贴地段的每个点
        到 mesh 表面的距离都很小;关掉之后至少有点明显悬空或陷入。
    为什么重要:
        贴地段默认是沿接触点的切平面走直线的。纸是平的时无所谓,但用户说了
        输入可以是「地面 mesh」,地面一起伏,直线段就会穿进坡里。
    场景构造:
        4x4、8x8 分段的 plane(顶点间距 0.5),把 x=0.5 和 x=1.0 两列顶点抬到 0.12,
        做出一道**横跨笔尖铺开路径**的坡。坎必须落在刷毛真正经过的地方,
        否则开不开 conform 都一样,测了等于没测。
    """
    print("[test] conformToSurface follows uneven ground")
    rig = build(root_pos=(0.0, 0.5, 0.0), tip_pos=(0.2, -0.7, 0.0),
                plane_size=4.0, plane_div=8)
    transform = cmds.listRelatives(rig["mesh"], parent=True, fullPath=True)[0]
    # 9x9 顶点网格,索引 = row * 9 + col,col 沿 X:x = -2 + col * 0.5。
    # 抬起 col 5(x=0.5)和 col 6(x=1.0),刷毛沿 +X 铺开时正好要爬上这道坡。
    ridge = ["{0}.vtx[{1}]".format(transform, row * 9 + col)
             for row in range(9) for col in (5, 6)]
    cmds.select(ridge)
    cmds.move(0.12, y=True, relative=True)
    cmds.select(clear=True)

    # cmds 里没有 nearestPointOnMesh(那是个需要单独加载的插件节点),
    # 直接用 MFnMesh.getClosestPoint 量点到面的距离。API 1.0 下结果是输出参数。
    selection = om.MSelectionList()
    selection.add(rig["mesh"])
    dag_path = om.MDagPath()
    selection.getDagPath(0, dag_path)
    fn_mesh = om.MFnMesh(dag_path)

    def max_surface_gap():
        gaps = []
        for p in cvs(rig):
            closest = om.MPoint()
            fn_mesh.getClosestPoint(om.MPoint(p[0], p[1], p[2]), closest,
                                    om.MSpace.kWorld)
            gaps.append(dist(p, (closest.x, closest.y, closest.z)))
        # 只关心贴地那一段:取最后三分之一的点
        return max(gaps[-len(gaps) // 3:])

    cmds.setAttr(rig["node"] + ".conformToSurface", True)
    on_gap = max_surface_gap()
    cmds.setAttr(rig["node"] + ".conformToSurface", False)
    off_gap = max_surface_gap()

    check(on_gap < 0.02,
          "grounded CVs hug the surface when conform is on (max gap {0:.5f})".format(on_gap))
    check(off_gap > on_gap + 0.02,
          "turning conform off cuts into the slope ({0:.5f} vs {1:.5f})".format(
              off_gap, on_gap))


def test_parent_inverse_matrix():
    """验证 parentInverseMatrix 把结果正确转回曲线的本地空间。

    验证内容:
        把输出曲线的 transform 挪走,连上它的 parentInverseMatrix 之后,
        曲线的**世界**位置必须和没挪之前一模一样。
    为什么重要:
        不接这根线时输出是世界空间,曲线 transform 一旦不在原点,毛就会整体偏移
        一个 transform 的量。这是把节点塞进真实绑定层级时必然遇到的第一个问题。
    场景构造:
        先记下基准世界坐标,再把曲线的 transform 移到 (3, 1, -2) 并接上 pim。
    """
    print("[test] parentInverseMatrix keeps the curve in world space")
    rig = build()
    baseline = cvs(rig)

    transform = cmds.listRelatives(rig["curve"], parent=True, fullPath=True)[0]
    cmds.setAttr(transform + ".translate", 3.0, 1.0, -2.0)
    cmds.setAttr(transform + ".rotateY", 35.0)
    shifted = cvs(rig)
    check(not vclose(shifted[-1], baseline[-1], 1e-4),
          "moving the transform does shift the curve while pim is unconnected")

    cmds.connectAttr(transform + ".parentInverseMatrix[0]",
                     rig["node"] + ".parentInverseMatrix")
    # 曲线 transform 自己的 translate/rotate 也要算进去,所以用它的 worldInverseMatrix
    cmds.disconnectAttr(transform + ".parentInverseMatrix[0]",
                        rig["node"] + ".parentInverseMatrix")
    cmds.connectAttr(transform + ".worldInverseMatrix[0]",
                     rig["node"] + ".parentInverseMatrix")
    restored = cvs(rig)
    worst = max(dist(restored[i], baseline[i]) for i in range(len(baseline)))
    check(worst < 1e-5,
          "world positions restored after wiring the inverse matrix (worst {0:.2e})".format(worst))


def test_curve_degree_and_samples():
    """验证 CV 数量与 curveDegree 设置一致生效。

    验证内容:
        samples 改成不同值时 CV 个数必须精确等于 samples;
        degree 在 linear 和 cubic 之间切换时曲线次数跟着变,弧长不受影响。
    为什么重要:
        节点是把采样点直接当 CV 用的,所以 CV 数必须正好是 samples。
        数量对不上说明空中段和贴地段的点数分配算错了。
    场景构造:
        压入状态下扫 samples 和 curveDegree。
    """
    print("[test] samples and curveDegree behave")
    rig = build()
    for samples in (6, 12, 24, 50):
        cmds.setAttr(rig["node"] + ".samples", samples)
        check(len(cvs(rig)) == samples,
              "samples={0} yields {1} CVs".format(samples, len(cvs(rig))))

    cmds.setAttr(rig["node"] + ".samples", 24)
    cmds.setAttr(rig["node"] + ".curveDegree", 0)
    linear_pts = cvs(rig)
    check(cmds.getAttr(rig["curve"] + ".degree") == 1, "linear gives degree 1")

    cmds.setAttr(rig["node"] + ".curveDegree", 1)
    cubic_pts = cvs(rig)
    check(cmds.getAttr(rig["curve"] + ".degree") == 3, "cubic gives degree 3")
    check(close(polyline_length(linear_pts), polyline_length(cubic_pts), 1e-9),
          "CV positions are identical regardless of degree")


def test_contact_point_output():
    """验证 outContactPoint 落在纸面上。

    验证内容:
        接触时 outContactPoint 的 Y 必须是 0(纸面高度);不接触时不应报告接触。
    为什么重要:
        下游要拿它贴墨迹 locator、驱动贴图 UV,落点偏了整张画就错位。
    场景构造:
        先压入再抬起。
    """
    print("[test] outContactPoint lands on the paper")
    rig = build()
    cmds.dgeval(rig["node"] + ".outCurve")
    point = cmds.getAttr(rig["node"] + ".outContactPoint")[0]
    check(out(rig, "outContact") == 1, "contact reported")
    check(close(point[1], 0.0, 1e-6),
          "contact point sits on the paper: {0}".format(
              tuple(round(v, 5) for v in point)))

    cmds.setAttr(rig["root"] + ".translate", 0.0, 3.0, 0.0)
    cmds.setAttr(rig["tip"] + ".translate", 0.3, 2.0, 0.0)
    check(out(rig, "outContact") == 0, "lifting the brush clears outContact")


def test_fixed_bristle_length():
    """验证 bristleLength 固定毛长,笔尖定位器只决定朝向、不决定长度。

    验证内容:
        设定 bristleLength=1.2,把笔尖定位器放在同一方向上的远近两处
        (距离 0.8 和 2.6),输出曲线必须**完全一样**,长度都是 1.2。
        再扫一遍距离,曲线长度不得有任何漂移。
    为什么重要:
        真实笔刷压下去只会弯,不会变长。毛长跟着定位器间距跑的话,拖着笔尖往纸里
        压的同时毛也在变长,既不物理,也让接触判据跟着一起漂。
    场景构造:
        毛根 (0, 0.6, 0),笔尖定位器沿 -Y 放在不同距离处,bristleLength=1.2。
    """
    print("[test] bristleLength fixes the length, the tip locator only aims")
    rig = build(root_pos=(0.0, 0.6, 0.0), tip_pos=(0.0, -0.2, 0.0),
                plane=False, bristleLength=1.2)
    near = cvs(rig)
    cmds.setAttr(rig["tip"] + ".translate", 0.0, -2.0, 0.0)
    far = cvs(rig)

    check(close(polyline_length(near), 1.2, 1e-6),
          "close tip locator still gives length {0:.6f}".format(polyline_length(near)))
    check(close(polyline_length(far), 1.2, 1e-6),
          "distant tip locator still gives length {0:.6f}".format(polyline_length(far)))
    worst = max(dist(near[i], far[i]) for i in range(len(near)))
    check(worst < 1e-6,
          "same direction, same curve regardless of tip distance ({0:.2e})".format(worst))
    check(vclose(near[-1], (0.0, -0.6, 0.0), 1e-6),
          "the real tip sits one bristle length from the root: {0}".format(
              tuple(round(v, 4) for v in near[-1])))

    lengths = []
    for reach in (-0.1, -0.5, -1.2, -3.0):
        cmds.setAttr(rig["tip"] + ".translate", 0.0, reach, 0.0)
        lengths.append(polyline_length(cvs(rig)))
    check(max(lengths) - min(lengths) < 1e-6,
          "length never drifts as the tip locator moves (spread {0:.2e})".format(
              max(lengths) - min(lengths)))


def test_auto_bend_whenever_reachable():
    """验证「够得着就一定弯」,不需要手动调任何东西。

    验证内容:
        固定毛长 1.2 垂直下压,毛根高度从 1.3 降到 0.3:
          - 高度 >= 1.2(毛够不着纸面)必须判不接触;
          - 高度 < 1.2 全部必须接触,**而且硬毛也一样**;
          - outPressure 随压深单调递增。
    为什么重要:
        这是「自动弯曲」的正题。硬毛按设定曲率弯需要比直线长得多的弧长,
        如果不做自动放软,就会出现「笔尖明明扎到纸下面了,毛却还是直的」。
        节点在毛长不够按设定硬度弯时,会自动解出一个更软的有效硬度让毛恰好弯到纸面。
    场景构造:
        毛根沿 -Y 垂直压,笔尖定位器只给方向,bristleLength=1.2。
    """
    print("[test] the bristle bends automatically whenever it can reach")
    rig = build(root_pos=(0.0, 1.3, 0.0), tip_pos=(0.0, -1.0, 0.0),
                bristleLength=1.2, stiffness=1.0)

    check(out(rig, "outContact") == 0, "height 1.30 > length 1.20: cannot reach")
    cmds.setAttr(rig["root"] + ".translate", 0.0, 1.25, 0.0)
    check(out(rig, "outContact") == 0, "height 1.25 still out of reach")

    previous = -1.0
    monotonic = True
    reached = True
    values = []
    for height in (1.15, 1.0, 0.85, 0.7, 0.55, 0.4, 0.3):
        cmds.setAttr(rig["root"] + ".translate", 0.0, height, 0.0)
        if out(rig, "outContact") != 1:
            reached = False
        pressure = out(rig, "outPressure")
        values.append(pressure)
        if pressure < previous:
            monotonic = False
        previous = pressure
    check(reached, "every height below the bristle length makes contact")
    check(monotonic, "outPressure grows with depth: {0}".format(
        ", ".join("{0:.4f}".format(v) for v in values)))
    check(min(p[1] for p in cvs(rig)) > -1e-6, "still never penetrates")


def test_auto_softening_covers_all_stiffness():
    """验证浅压时任何硬度都能接触,不会「硬毛压不下去」。

    验证内容:
        固定毛长、浅压到一个硬毛按自己曲率弯不下去的高度,扫遍 stiffness,
        每一档都必须判定接触,且曲线仍然不穿透、长度仍然固定。
    为什么重要:
        自动放软是为了消除「调硬了就没反应」这个手动陷阱。旧行为下同一个姿势,
        stiffness 高就是不接触,得手动把硬度调低才弯 —— 正是要去掉的东西。
    场景构造:
        毛长 1.2,毛根高 0.95 垂直下压。硬毛(p=1)按理需要 1.571*0.95=1.49
        的弧长才弯得到纸面,比毛长还大,所以必然触发自动放软。
    """
    print("[test] every stiffness still contacts on a shallow press")
    rig = build(root_pos=(0.0, 0.95, 0.0), tip_pos=(0.0, -1.0, 0.0),
                bristleLength=1.2)
    for stiffness in (0.0, 0.25, 0.5, 0.75, 1.0):
        cmds.setAttr(rig["node"] + ".stiffness", stiffness)
        pts = cvs(rig)
        check(out(rig, "outContact") == 1,
              "stiffness={0:.2f} makes contact".format(stiffness))
        check(close(polyline_length(pts), 1.2, 1e-5) and min(p[1] for p in pts) > -1e-6,
              "stiffness={0:.2f}: length {1:.7f}, lowest {2:+.2e}".format(
                  stiffness, polyline_length(pts), min(p[1] for p in pts)))


def test_mesh_topology():
    """验证 outMesh 的顶点数、面数与 samples / meshSides 一致。

    验证内容:
        顶点数 = samples × meshSides,面数 = (samples-1) × meshSides + 2 个端盖。
        改 samples 和 meshSides 都要跟着变;brushWidth 归零时拓扑**不变**。
    为什么重要:
        拓扑得是可预测的,下游才敢往上挂 deformer、分材质、做 UV。
        尤其 brushWidth=0 不能退化成空 mesh —— 拓扑时有时无会让这些全部失效。
    场景构造:
        默认压入姿势,扫 samples 和 meshSides。
    """
    print("[test] outMesh topology follows samples and meshSides")
    rig = build(bristleLength=1.2)
    for samples, sides in ((16, 8), (24, 8), (16, 12), (10, 5)):
        cmds.setAttr(rig["node"] + ".samples", samples)
        cmds.setAttr(rig["node"] + ".meshSides", sides)
        cmds.dgeval(rig["node"] + ".outMesh")
        verts = cmds.polyEvaluate(rig["brushMesh"], vertex=True)
        faces = cmds.polyEvaluate(rig["brushMesh"], face=True)
        check(verts == samples * sides and faces == (samples - 1) * sides + 2,
              "samples={0} sides={1} -> {2} verts, {3} faces".format(
                  samples, sides, verts, faces))

    cmds.setAttr(rig["node"] + ".samples", 16)
    cmds.setAttr(rig["node"] + ".meshSides", 8)
    cmds.setAttr(rig["node"] + ".brushWidth", 0.0)
    cmds.dgeval(rig["node"] + ".outMesh")
    check(cmds.polyEvaluate(rig["brushMesh"], vertex=True) == 128,
          "brushWidth=0 keeps the topology instead of emptying the mesh")


def test_mesh_normals_face_outward():
    """验证笔刷 mesh 的法线朝外,没有面内翻。

    验证内容:
        每个侧壁四边形的法线,与「从该段中轴指向面中心」的径向必须同向(点积 > 0)。
        四种笔刷类型都要过。
    为什么重要:
        法线内翻在视口里经常看不出来(尤其开了双面渲染),一到渲染或导出就穿帮。
        管状网格的 polygonConnects 绕序很容易写反,这条就是钉死它的。
    场景构造:
        压入姿势,逐个切换 brushType。
    """
    print("[test] brush mesh normals point outward")
    rig = build(bristleLength=1.2, samples=16)
    sides = cmds.getAttr(rig["node"] + ".meshSides")

    for index, name in enumerate(("calligraphy", "round", "flat", "fan")):
        cmds.setAttr(rig["node"] + ".brushType", index)
        rings = mesh_rings(rig)

        selection = om.MSelectionList()
        selection.add(rig["brushMesh"])
        dag_path = om.MDagPath()
        selection.getDagPath(0, dag_path)
        fn_mesh = om.MFnMesh(dag_path)

        worst = 1.0
        for face in range((len(rings) - 1) * sides):
            ring_index = face // sides
            normal = om.MVector()
            fn_mesh.getPolygonNormal(face, normal, om.MSpace.kWorld)
            vertices = om.MIntArray()
            fn_mesh.getPolygonVertices(face, vertices)

            flat = rings[ring_index] + rings[ring_index + 1]
            axis = ring_center(flat)
            centre = ring_center([rings[v // sides][v % sides]
                                  for v in vertices])
            radial = om.MVector(centre[0] - axis[0], centre[1] - axis[1],
                                centre[2] - axis[2])
            if radial.length() < 1e-9:
                continue
            worst = min(worst, radial.normal() * normal)
        check(worst > 0.0,
              "{0}: every side face faces outward (worst dot {1:.4f})".format(
                  name, worst))


def test_brush_type_profiles():
    """验证四种笔刷类型各自的廓形特征。

    验证内容:
        毛笔   —— 尖端明显比根部细(锥形)
        绘画笔 —— 中段仍然饱满,只有末端收口
        毛刷   —— 从头到尾等宽,且截面是扁的(宽 ≠ 厚)
        扇形笔 —— 尖端比根部**更宽**,而且比毛刷更扁
    为什么重要:
        类型如果只是换个名字、廓形都一样,这个功能就没有意义。这条逐项量出
        每种类型该有的形状特征。
    场景构造:
        悬空(不受压,避免散开干扰廓形),量第 1 环和倒数第 2 环的直径。
    """
    print("[test] each brush type has its own silhouette")
    rig = build(root_pos=(0.0, 3.0, 0.0), tip_pos=(0.0, 1.5, 0.0),
                bristleLength=1.2, samples=20, plane=False)

    diameters = {}
    for index, name in enumerate(("calligraphy", "round", "flat", "fan")):
        cmds.setAttr(rig["node"] + ".brushType", index)
        rings = mesh_rings(rig)
        diameters[name] = (ring_diameter(rings[1]), ring_diameter(rings[-2]),
                           rings)

    root_d, tip_d, _ = diameters["calligraphy"]
    check(tip_d < root_d * 0.35,
          "calligraphy tapers to a point (root {0:.4f} -> tip {1:.4f})".format(
              root_d, tip_d))

    root_d, tip_d, rings = diameters["round"]
    mid_d = ring_diameter(rings[len(rings) // 2])
    check(mid_d > root_d * 0.9 and tip_d < root_d * 0.7,
          "round stays full then rounds off (root {0:.4f} mid {1:.4f} tip {2:.4f})".format(
              root_d, mid_d, tip_d))

    root_d, tip_d, rings = diameters["flat"]
    check(close(root_d, tip_d, 1e-6),
          "flat keeps one width end to end ({0:.4f} vs {1:.4f})".format(
              root_d, tip_d))
    # 扁截面:最远两点的距离应明显大于垂直方向的跨度
    ring = rings[len(rings) // 2]
    spans = sorted(dist(ring[j], ring[(j + len(ring) // 2) % len(ring)])
                   for j in range(len(ring) // 2))
    check(spans[-1] > spans[0] * 2.0,
          "flat section is flat (wide span {0:.4f} vs thin span {1:.4f})".format(
              spans[-1], spans[0]))

    root_d, tip_d, _ = diameters["fan"]
    check(tip_d > root_d * 1.5,
          "fan widens towards the tip (root {0:.4f} -> tip {1:.4f})".format(
              root_d, tip_d))


def test_mesh_hugs_the_curve():
    """验证 mesh 的中轴就是输出曲线本身。

    验证内容:
        每一圈截面的重心必须落在对应的曲线 CV 上。
    为什么重要:
        mesh 和曲线是同一次求值的两个输出,它们必须描述同一根毛。
        对不上的话,拿曲线做的事(比如吸附墨迹)和看到的毛就会错位。
    场景构造:
        压入姿势,逐点比对。
    """
    print("[test] mesh rings are centred on the curve CVs")
    rig = build(bristleLength=1.2, samples=16)
    curve_cvs = cvs(rig)
    rings = mesh_rings(rig)
    check(len(rings) == len(curve_cvs),
          "one ring per CV ({0} vs {1})".format(len(rings), len(curve_cvs)))
    worst = max(dist(ring_center(rings[i]), curve_cvs[i])
                for i in range(len(rings)))
    check(worst < 1e-5,
          "every ring is centred on its CV (worst {0:.2e})".format(worst))


def test_pressure_spreads_the_mesh():
    """验证压下去时贴地段变宽变扁,悬空段不受影响。

    验证内容:
        压深增加 -> 笔尖那一圈的直径单调变宽;
        spreadByPressure 归零则不再变宽;
        毛根那一圈始终不受压力影响。
    为什么重要:
        笔画变粗的视觉来源就是这个。而且散开必须只作用在贴地那一段 ——
        整根一起变粗的话,笔杆连接处会跟着鼓起来。
    场景构造:
        毛刷(等宽廓形,便于直接比较),毛根从 1.3 压到 0.2。
    """
    print("[test] pressure spreads the grounded section only")
    rig = build(root_pos=(0.0, 1.3, 0.0), tip_pos=(0.0, -1.0, 0.0),
                bristleLength=1.2, samples=16, brushType=2)

    tips, roots = [], []
    for height in (1.3, 0.8, 0.5, 0.2):
        cmds.setAttr(rig["root"] + ".translate", 0.0, height, 0.0)
        rings = mesh_rings(rig)
        tips.append(ring_diameter(rings[-1]))
        roots.append(ring_diameter(rings[0]))

    monotonic = all(tips[i] > tips[i - 1] - 1e-9 for i in range(1, len(tips)))
    check(monotonic, "tip ring widens with depth: {0}".format(
        ", ".join("{0:.4f}".format(v) for v in tips)))
    check(tips[-1] > tips[0] * 1.2,
          "deep press widens the tip by {0:.2f}x".format(tips[-1] / tips[0]))
    # 容差放到 1e-7:毛根环随压深会有 1e-9 量级的抖动,那是曲线形状变化后
    # 平行传输坐标系的浮点噪声,不是受压变宽(真受压是 1.6 倍这种量级)。
    check(max(roots) - min(roots) < 1e-7,
          "the root ring never reacts to pressure (spread {0:.2e})".format(
              max(roots) - min(roots)))

    cmds.setAttr(rig["node"] + ".spreadByPressure", 0.0)
    cmds.setAttr(rig["node"] + ".flattenByPressure", 0.0)
    rings = mesh_rings(rig)
    check(close(ring_diameter(rings[-1]), roots[0], 1e-6),
          "zeroing the pressure response restores the plain section")


def test_brush_width_scales_section():
    """验证 brushWidth 线性缩放截面尺寸。

    验证内容:
        brushWidth 翻倍,每一圈的直径也翻倍。
    为什么重要:
        这是最常调的参数,必须是干净的线性关系,不能和廓形、压力耦合在一起。
    场景构造:
        悬空的毛刷(等宽廓形),比较两个宽度下的环直径。
    """
    print("[test] brushWidth scales the section linearly")
    rig = build(root_pos=(0.0, 3.0, 0.0), tip_pos=(0.0, 1.5, 0.0),
                bristleLength=1.2, brushType=2, plane=False)
    cmds.setAttr(rig["node"] + ".brushWidth", 0.05)
    small = [ring_diameter(r) for r in mesh_rings(rig)]
    cmds.setAttr(rig["node"] + ".brushWidth", 0.10)
    large = [ring_diameter(r) for r in mesh_rings(rig)]
    worst = max(abs(large[i] - small[i] * 2.0) for i in range(len(small)))
    check(worst < 1e-6,
          "doubling brushWidth doubles every ring (worst {0:.2e})".format(worst))


def test_flat_brush_follows_shaft_roll():
    """验证扁笔的宽面朝向跟着笔杆转。

    验证内容:
        毛刷悬空,毛根定位器绕毛轴(这里是 Y 轴)转 90 度,
        截面的宽面方向也必须跟着转 90 度。
    为什么重要:
        平头刷画出来是宽线条还是细线条,全看宽面朝哪。这个必须能被绑定师控制,
        而且和垂直下压时的倒向参考用同一根轴(笔杆局部 X),不能各转各的。
    场景构造:
        毛刷沿 -Y 悬空,扫毛根的 rotateY。
    """
    print("[test] flat brush width axis follows the shaft roll")
    rig = build(root_pos=(0.0, 3.0, 0.0), tip_pos=(0.0, 1.5, 0.0),
                bristleLength=1.2, brushType=2, plane=False)

    def width_axis():
        ring = mesh_rings(rig)[len(mesh_rings(rig)) // 2]
        best = max(((dist(a, b), a, b) for a in ring for b in ring),
                   key=lambda item: item[0])
        vec = (best[2][0] - best[1][0], best[2][2] - best[1][2])
        length = math.hypot(*vec)
        return (abs(vec[0] / length), abs(vec[1] / length))

    cmds.setAttr(rig["root"] + ".rotateY", 0.0)
    axis0 = width_axis()
    cmds.setAttr(rig["root"] + ".rotateY", 90.0)
    axis90 = width_axis()

    check(axis0[0] > 0.99, "rotateY=0: width axis lies along X {0}".format(
        tuple(round(v, 4) for v in axis0)))
    check(axis90[1] > 0.99, "rotateY=90: width axis swung to Z {0}".format(
        tuple(round(v, 4) for v in axis90)))


def test_width_segments():
    """验证 5 段手动宽度控制。

    验证内容:
        - 全留 1.0 时不改变任何东西(和没这个功能一样);
        - 5 个控制点精确落在 t = 0 / 0.25 / 0.5 / 0.75 / 1 上,调哪段哪段变;
        - 只调中间一段,两端基本不动(局部性);
        - 全部乘 2 等价于 brushWidth 乘 2;
        - 段之间是平滑过渡,不出现阶梯。
    为什么重要:
        这是让绑定师自己塑笔锋形状的手段。它是**乘在 brushType 廓形之上**的,
        所以默认值必须是干净的 1.0 —— 一旦默认值让廓形发生了变化,
        所有类型的廓形断言就都不作数了。
    场景构造:
        毛刷(等宽廓形,便于直接读出倍率),悬空避免压力散开干扰。
        samples=21 让 5 个控制点正好落在第 0/5/10/15/20 圈采样上。
    """
    print("[test] five width segments reshape the brush")
    rig = build(root_pos=(0.0, 3.0, 0.0), tip_pos=(0.0, 1.5, 0.0),
                bristleLength=1.2, brushType=2, samples=21, plane=False)
    node = rig["node"]
    control_rings = (0, 5, 10, 15, 20)

    base = [ring_diameter(r) for r in mesh_rings(rig)]
    check(max(base) - min(base) < 1e-9,
          "defaults are a clean 1.0 (flat brush stays uniform)")

    # 逐段单独拉到 2.0,检查对应那一圈确实翻倍
    for index, ring_index in enumerate(control_rings):
        for reset in range(5):
            cmds.setAttr("{0}.widthSegment{1}".format(node, reset + 1), 1.0)
        cmds.setAttr("{0}.widthSegment{1}".format(node, index + 1), 2.0)
        rings = mesh_rings(rig)
        got = ring_diameter(rings[ring_index])
        check(close(got, base[ring_index] * 2.0, 1e-6),
              "widthSegment{0} drives ring {1} ({2:.4f} -> {3:.4f})".format(
                  index + 1, ring_index, base[ring_index], got))

    # 只动中间那段,两端不该跟着动
    for reset in range(5):
        cmds.setAttr("{0}.widthSegment{1}".format(node, reset + 1), 1.0)
    cmds.setAttr(node + ".widthSegment3", 2.5)
    rings = mesh_rings(rig)
    check(close(ring_diameter(rings[0]), base[0], 1e-6)
          and close(ring_diameter(rings[-1]), base[-1], 1e-6),
          "bulging the middle leaves both ends untouched")
    # 控制点本身(环 5)是 1.0,Catmull-Rom 在控制点处精确取到控制点值,
    # 所以它等于基准;鼓包只在控制点**之间**扩散出去。
    widths = [ring_diameter(r) for r in rings]
    check(widths[10] > widths[8] > widths[6] >= widths[5] - 1e-9,
          "the bulge falls off smoothly between control points "
          "({0:.4f} > {1:.4f} > {2:.4f} >= {3:.4f})".format(
              widths[10], widths[8], widths[6], widths[5]))

    # 平滑性:相邻环的直径变化不该出现阶梯式突跳
    diameters = [ring_diameter(r) for r in rings]
    steps = [abs(diameters[i] - diameters[i - 1])
             for i in range(1, len(diameters))]
    check(max(steps) < sum(steps) / len(steps) * 3.0,
          "no stair-stepping between segments (max step {0:.5f}, mean {1:.5f})".format(
              max(steps), sum(steps) / len(steps)))

    # 全部乘 2 == brushWidth 乘 2
    for reset in range(5):
        cmds.setAttr("{0}.widthSegment{1}".format(node, reset + 1), 2.0)
    doubled = [ring_diameter(r) for r in mesh_rings(rig)]
    worst = max(abs(doubled[i] - base[i] * 2.0) for i in range(len(base)))
    check(worst < 1e-6,
          "scaling all five equals scaling brushWidth (worst {0:.2e})".format(worst))

    # 收到 0:该段塌成中轴上的一点,但不能崩、不能出 NaN
    for reset in range(5):
        cmds.setAttr("{0}.widthSegment{1}".format(node, reset + 1), 1.0)
    cmds.setAttr(node + ".widthSegment5", 0.0)
    rings = mesh_rings(rig)
    check(ring_diameter(rings[-1]) < 1e-9,
          "a segment at 0 pinches that ring shut")
    check(all(v == v for r in rings for p in r for v in p),
          "pinching to zero produces no NaN")


def test_mesh_has_usable_uvs():
    """验证笔刷 mesh 带可用的 UV。

    验证内容:
        UV 数 = samples × (meshSides + 1),每个面都分到了 UV,
        u 铺满 0-1(周向)、v 铺满 0-1(沿毛长)。
    为什么重要:
        没有 UV 也能赋材质、不会报错(这点常被误传成会报错),但贴图会整张糊成
        一个像素 —— 毛刷要贴毛的纹理就废了。UV 比顶点多一列是因为周向有接缝:
        u=0 和 u=1 落在同一圈顶点上,不重复一列的话贴图会在接缝处整个倒压回去。
    场景构造:
        压入姿势,换几组 samples / meshSides。
    """
    print("[test] brush mesh carries usable UVs")
    rig = build(bristleLength=1.2)

    # 用 MFnMesh.numUVs();polyEvaluate 的 uvComponent 标志量的不是 UV 个数,
    # 它对这个 mesh 一律返回 0,拿它做断言会误判成「没建 UV」。
    selection = om.MSelectionList()
    selection.add(rig["brushMesh"])
    dag_path = om.MDagPath()
    selection.getDagPath(0, dag_path)
    fn_mesh = om.MFnMesh(dag_path)

    for samples, sides in ((16, 8), (24, 12)):
        cmds.setAttr(rig["node"] + ".samples", samples)
        cmds.setAttr(rig["node"] + ".meshSides", sides)
        cmds.dgeval(rig["node"] + ".outMesh")
        uvs = fn_mesh.numUVs()
        check(uvs == samples * (sides + 1),
              "samples={0} sides={1} -> {2} UVs (one extra column for the seam)".format(
                  samples, sides, uvs))

    u_array = om.MFloatArray()
    v_array = om.MFloatArray()
    fn_mesh.getUVs(u_array, v_array)
    us = [u_array[i] for i in range(u_array.length())]
    vs = [v_array[i] for i in range(v_array.length())]
    check(close(min(us), 0.0) and close(max(us), 1.0),
          "u spans 0..1 around the section ({0:.3f}..{1:.3f})".format(
              min(us), max(us)))
    check(close(min(vs), 0.0) and close(max(vs), 1.0),
          "v spans 0..1 along the bristle ({0:.3f}..{1:.3f})".format(
              min(vs), max(vs)))

    uv_counts = om.MIntArray()
    uv_ids = om.MIntArray()
    fn_mesh.getAssignedUVs(uv_counts, uv_ids)
    faces = cmds.polyEvaluate(rig["brushMesh"], face=True)
    check(uv_counts.length() == faces,
          "every face got a UV face ({0} vs {1} faces)".format(
              uv_counts.length(), faces))


def test_brush_presets_stay_in_sync():
    """验证 AE 模板(MEL)和 brush_utils(Python)两份笔刷预设表没有漂移。

    验证内容:
        对四种类型分别调用 MEL 里的 AEbrushTipCurveTypeChanged,把它写出来的
        stiffness / brushWidth / spreadByPressure / flattenByPressure
        和 brush_utils.BRUSH_PRESETS 逐项比对。
    为什么重要:
        同一份预设数据存在两个地方(MEL 模板不 import Python 模块,是为了不依赖
        sys.path 配好)。重复数据迟早会漂,漂了的表现是「AE 里切类型」和
        「脚本里切类型」给出不一样的手感,很难想到去查。
    场景构造:
        source 模板文件,建一个节点逐个类型调用。

    副作用:
        只验证切换逻辑。AE 的界面布局部分需要 GUI,无头环境测不了。
    """
    print("[test] MEL template and Python presets agree")
    import maya.mel as mel

    here = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    if here not in sys.path:
        sys.path.append(here)
    import brush_utils

    cmds.file(new=True, force=True)
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)
    mel.eval('source "{0}/AEbrushTipCurveTemplate.mel";'.format(here))

    node = cmds.createNode("brushTipCurve")
    fields = (("stiffness", "stiffness"), ("brushWidth", "width"),
              ("spreadByPressure", "spread"), ("flattenByPressure", "flatten"))

    for name, preset in sorted(brush_utils.BRUSH_PRESETS.items()):
        cmds.setAttr(node + ".brushType", preset["index"])
        mel.eval('AEbrushTipCurveTypeChanged("{0}.brushType");'.format(node))
        mismatched = [
            attr for attr, key in fields
            if not close(cmds.getAttr(node + "." + attr), preset[key], 1e-9)
        ]
        check(not mismatched,
              "{0}: MEL template matches BRUSH_PRESETS{1}".format(
                  name, "" if not mismatched else " (differs on " +
                  ", ".join(mismatched) + ")"))


def test_degenerate_inputs():
    """验证各种退化输入下节点不崩、不出 NaN。

    验证内容:
        没有 mesh / 只有一个定位器 / 定位器全部重合 / 毛根已经在纸面以下,
        四种情况都要能求出一条合法曲线,且坐标里没有 NaN。
    为什么重要:
        绑定过程中这些状态都会短暂出现(比如刚建好节点还没连线)。节点在
        compute 里不用 try/except,靠的就是每一个分支都有明确兜底,这里逐个核对。
    场景构造:
        见每个小节。
    """
    print("[test] degenerate inputs stay safe")

    def finite(pts):
        return all(v == v and abs(v) < 1e12 for p in pts for v in p)

    rig = build(plane=False)
    pts = cvs(rig)
    check(finite(pts) and len(pts) == 24, "no mesh connected: straight line, no NaN")
    check(out(rig, "outContact") == 0, "no mesh connected: no contact reported")

    rig = build()
    cmds.disconnectAttr(rig["tip"] + ".worldMatrix[0]",
                        rig["node"] + ".controlMatrix[1]")
    pts = cvs(rig)
    check(finite(pts), "single locator: no NaN")

    rig = build(root_pos=(0.0, 0.5, 0.0), tip_pos=(0.0, 0.5, 0.0))
    pts = cvs(rig)
    check(finite(pts), "coincident locators: no NaN")

    rig = build(root_pos=(0.0, -0.5, 0.0), tip_pos=(0.4, -1.5, 0.0))
    pts = cvs(rig)
    check(finite(pts), "root below the paper: no NaN")
    check(out(rig, "outContact") == 0, "root below the paper: treated as no contact")

    rig = build()
    for samples in (6, 400):
        cmds.setAttr(rig["node"] + ".samples", samples)
        check(finite(cvs(rig)), "samples={0}: no NaN".format(samples))


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)
    print("plugin loaded: {0}".format(PLUGIN))
    print("")

    test_no_contact_is_straight()
    test_arclength_is_conserved()
    test_never_penetrates()
    test_lands_tangent_to_paper()
    test_stiffness_drives_spread()
    test_deeper_press_spreads_more()
    test_envelope_zero_disables()
    test_vertical_press_flips_predictably()
    test_shaft_roll_steers_spread()
    test_multiple_locators()
    test_tilted_ground()
    test_conform_to_uneven_ground()
    test_parent_inverse_matrix()
    test_curve_degree_and_samples()
    test_contact_point_output()
    test_fixed_bristle_length()
    test_auto_bend_whenever_reachable()
    test_auto_softening_covers_all_stiffness()
    test_mesh_topology()
    test_mesh_normals_face_outward()
    test_brush_type_profiles()
    test_mesh_hugs_the_curve()
    test_pressure_spreads_the_mesh()
    test_brush_width_scales_section()
    test_flat_brush_follows_shaft_roll()
    test_width_segments()
    test_mesh_has_usable_uvs()
    test_brush_presets_stay_in_sync()
    test_degenerate_inputs()

    print("")
    print("{0} checks, {1} failed".format(CHECKS[0], len(FAILURES)))
    for failure in FAILURES:
        print("  FAILED: {0}".format(failure))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    code = main()
    if _IN_MAYA:
        try:
            maya.standalone.uninitialize()
        except Exception:
            pass
    sys.exit(code)
