# -*- coding: utf-8 -*-
"""
brushTipCurve —— 笔刷笔尖压弯曲线节点(Maya Python API 1.0)。

把「毛笔压在纸上」这件事做成一次 DG 求值:给一张纸/地面 mesh,再给两个(或更多)
定位器标出笔杆朝向,节点直接吐出一条已经压弯的刷毛曲线,可以拿去挂 sweep mesh、
驱动笔迹宽度,不需要任何解算或驱动关键帧。

刷毛是一根**长度固定**的不可伸长弹性杆(长度由 bristleLength 指定)。压到纸面时:

        笔杆
         ●  B
          \\
           \\          空中段 sAir:俯角 phi 从 alpha 单调衰减到 0,
            \\_        到达纸面时恰好与纸面相切
    ━━━━━━━━━━━●━━━━━━━━━●  笔尖
                  贴地段 L - sAir:沿切向平铺

    phi(s) = alpha * (1 - s/sAir) ** p          s 是从毛根量起的弧长
    h      = ∫ sin(phi(s)) ds                   毛根到纸面的垂直高度
    sAir   = h / I(alpha, p)                    I 是上式的归一化积分

关键点是 **sAir 由 h 和 alpha 唯一确定,不是一个可调参数**。这让「不穿透纸面」和
「弧长守恒」成为模型的内在性质,而不是靠事后 clamp 兜出来的 —— 空中段的高度
随 s 单调下降(dh/ds = -sin(phi) <= 0)且终点恰好落在纸面上,贴地段则始终贴着纸面。

毛的软硬由指数 p 控制,p 落在 (0, 1] 区间:

    stiffness = 1(硬毛) -> p = 1.0,phi 线性衰减,整根弯成均匀圆弧,sAir 大,贴地段短
    stiffness = 0(软毛) -> p = 0.35,上段几乎保持笔杆方向,临近纸面才急弯,贴地段长

p 不能大于 1:那会让俯角一出根就衰减到 0,毛立刻弯平然后水平滑行,而水平滑行
不降高度,结果是怎么压都落不到纸面。软毛的正确形状是「上段直、末端急弯」,对应 p < 1。

**自动弯曲**:只要毛尖够得着纸面(毛长 > 毛根到纸面的直线距离),就一定会弯。
按设定硬度算出来的 sAir 如果超过了毛长,说明毛还没富余到能按那个曲率弯,
这时节点会自动解出一个更软的有效硬度,让毛恰好弯到纸面(贴地段长度为 0)。
物理上也对:刚接触时毛是绷紧的,压深了才有余量按自己的软硬程度弯。

属性映射:
    inMesh              <- 纸张/地面 shape 的 worldMesh[0]
    controlMatrix[0..n] <- 定位器的 worldMatrix[0],索引升序 = 毛根 -> 笔尖朝向
    bristleLength       <- 毛长,0 表示退回用定位器之间的距离
    outCurve            -> 曲线 shape 的 create
    outPressure         -> 贴地长度占比,直接拿去驱动笔迹宽度/墨色浓度

依赖:仅 Maya Python API 1.0(maya.OpenMaya / maya.OpenMayaMPx),无第三方库。
语法同时兼容 Python 2.7 / 3.x(没有 f-string、没有类型标注)。

加载方式:
    import maya.cmds as cmds
    cmds.loadPlugin(r"H:/.../MayabrushNode/brushTipCurveNode.py")
    cmds.createNode("brushTipCurve")
"""

import math

import maya.OpenMaya as om
import maya.OpenMayaMPx as ompx


kPluginNodeName = "brushTipCurve"
kPluginNodeId = om.MTypeId(0x0007F0A2)  # 位于 Autodesk 预留给内部自用的 ID 区段
kPluginVersion = "2.0.0"
kAuthor = "MayabrushNode"

# 浮点比较用的通用小量。刷毛长度、角度这些量级都在 1e-2 以上,1e-12 足够安全。
EPS = 1e-12

# 切向退化的判定阈值。笔杆越接近垂直下压,入射方向在纸面上的投影越短
# (投影长度正好等于 cos(alpha)),短到这个值以下就认为「方向已经没意义了」,
# 改用笔杆矩阵的局部 X 轴来决定往哪边倒。0.05 对应 alpha 约 87 度。
TANGENT_EPS = 0.05

# 硬度映射到弯曲剖面指数 p:p = STIFFNESS_EXP_MIN + stiffness * (1 - STIFFNESS_EXP_MIN)。
#
# p 落在 (0, 1] 区间,注意**不能大于 1**:phi(s) = alpha * (1-s/sAir)**p,p 越大俯角
# 衰减越快,毛一出根就弯平了,然后水平滑行 —— 而水平滑行是不降高度的,于是需要
# 长得离谱的毛才落得到纸面,压不下去。真实的软毛恰恰相反:上段基本保持笔杆方向,
# 到贴近纸面才急弯,那对应 p < 1。
#
#   p = 1.0  -> phi 线性衰减,整根弯成均匀圆弧 = 硬毛
#   p = 0.35 -> 上段接近直线,末端急弯      = 软毛
#
# 下限取 0.35 而不是更小:p 再小的话末端弯折会陡到采样点跟不上,曲线在接触点
# 附近出现肉眼可见的折角。
STIFFNESS_EXP_MIN = 0.35

# 自动放软时二分搜索的指数下限。比 STIFFNESS_EXP_MIN 小得多 —— 毛刚够到纸面的
# 极限情况下剖面会非常接近直线,那正是 p -> 0 的样子。
EXP_SEARCH_MIN = 1e-3
EXP_SEARCH_ITER = 40

# 求解 sAir 时的积分分段数。只影响先判断走哪条分支,输出采样时会用实际点数重算。
SOLVE_STEPS = 64

# curveDegree 枚举值,与 nodeInitializer() 里 addField 注册的顺序一一对应。
DEGREE_LINEAR = 0
DEGREE_CUBIC = 1

# brushType 枚举值,同样与 addField 的注册顺序一一对应。
BRUSH_CALLIGRAPHY = 0   # 毛笔:圆截面,根部饱满、向尖端收成锥
BRUSH_ROUND = 1         # 绘画笔:圆截面,大部分等宽、末端圆润收头
BRUSH_FLAT = 2          # 毛刷:扁截面,等宽到底、末端平切
BRUSH_FAN = 3           # 扇形笔:更扁,向尖端扇形展开

# 每种笔刷的截面「厚/宽」比。1.0 是正圆,越小越扁。
BRUSH_ASPECT = {
    BRUSH_CALLIGRAPHY: 1.0,
    BRUSH_ROUND: 1.0,
    BRUSH_FLAT: 0.25,
    BRUSH_FAN: 0.18,
}

# 每种笔刷的推荐硬度。节点自己**不会**用这张表去覆盖 stiffness ——
# DG 节点的 compute 不允许回写自己的输入属性,硬来会造成循环求值。
# 它是给 brush_utils.set_brush_type() 和 AE 模板用的,切换类型时填一次,
# 填完之后你改成多少就是多少,再切类型才会再填。
BRUSH_STIFFNESS = {
    BRUSH_CALLIGRAPHY: 0.20,
    BRUSH_ROUND: 0.50,
    BRUSH_FLAT: 0.80,
    BRUSH_FAN: 0.65,
}

# 截面尺寸的下限(相对 brushWidth)。锥形笔的尖端理论上收到 0,真收成 0 的话
# 末端那一圈会退化成重合点,生成一圈零面积的面,Maya 的法线和 UV 都会出问题。
MIN_SECTION_SCALE = 0.02

# 手动宽度控制的段数。5 个控制点均匀落在毛根(t=0)到笔尖(t=1)之间,
# 即 t = 0, 0.25, 0.5, 0.75, 1.0。
WIDTH_SEGMENTS = 5


# ---------------------------------------------------------------------------
# 纯几何辅助
#
# 这一段刻意不碰任何节点上下文(不读 MDataBlock、不碰属性),只吃 MVector 和浮点数,
# 这样 selftest 里可以脱离节点直接喂数据验算。
# ---------------------------------------------------------------------------

def _clamp(value, low, high):
    """把 value 夹到 [low, high]。"""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _smoothstep(edge0, edge1, x):
    """标准 smoothstep,在 [edge0, edge1] 之间给出 C1 连续的 0->1 过渡。"""
    if edge1 - edge0 <= EPS:
        return 0.0 if x < edge1 else 1.0
    t = _clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _safe_normal(vec, fallback):
    """归一化 vec;长度过小则返回 fallback(fallback 必须已是单位向量)。"""
    length = vec.length()
    if length <= EPS:
        return om.MVector(fallback)
    return vec / length


def _orthonormalize(vec, normal, fallback):
    """把 vec 投影到以 normal 为法线的平面上再归一化。"""
    projected = vec - normal * (vec * normal)
    return _safe_normal(projected, fallback)


def _any_perpendicular(normal):
    """给一个单位向量,返回任意一个与之垂直的单位向量。

    取世界 X 轴与 normal 叉乘;当 normal 本身就接近世界 X 轴时改用世界 Z 轴,
    保证叉乘结果不会退化成零向量。
    """
    seed = om.MVector(1.0, 0.0, 0.0)
    if abs(normal * seed) > 0.9:
        seed = om.MVector(0.0, 0.0, 1.0)
    return (seed ^ normal).normal()


def _catmull_rom(p0, p1, p2, p3, t):
    """Catmull-Rom 样条在 p1->p2 区间上 t∈[0,1] 处的点。

    选 Catmull-Rom 是因为它**过点**:三个以上定位器时曲线会精确穿过中间那些
    定位器,绑定师摆在哪就是哪,不像 B 样条那样往里收。
    """
    t2 = t * t
    t3 = t2 * t
    return (p1 * 2.0
            + (p2 - p0) * t
            + (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
            + (p1 * 3.0 - p0 - p2 * 3.0 + p3) * t3) * 0.5


def _densify(ctrl, per_span):
    """把控制点加密成一条折线,作为后续按弧长重采样的底稿。"""
    count = len(ctrl)
    if count < 2:
        return [om.MVector(p) for p in ctrl]
    if count == 2:
        return [om.MVector(ctrl[0]), om.MVector(ctrl[1])]

    ext = [ctrl[0] * 2.0 - ctrl[1]] + list(ctrl) + [ctrl[-1] * 2.0 - ctrl[-2]]
    dense = []
    for i in range(count - 1):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for j in range(per_span):
            dense.append(_catmull_rom(p0, p1, p2, p3, float(j) / per_span))
    dense.append(om.MVector(ctrl[-1]))
    return dense


def _arc_table(points):
    """折线的累计弧长表,长度与 points 相同,首项为 0。"""
    table = [0.0]
    for i in range(1, len(points)):
        table.append(table[-1] + (points[i] - points[i - 1]).length())
    return table


def _point_at_arc(points, table, target):
    """在折线上取累计弧长为 target 处的点(线性插值)。"""
    total = table[-1]
    if target <= 0.0 or total <= EPS:
        return om.MVector(points[0])
    if target >= total:
        return om.MVector(points[-1])

    lo, hi = 0, len(table) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if table[mid] <= target:
            lo = mid
        else:
            hi = mid
    span = table[lo + 1] - table[lo]
    frac = 0.0 if span <= EPS else (target - table[lo]) / span
    return points[lo] + (points[lo + 1] - points[lo]) * frac


def _sample_bristle(points, table, length, count):
    """在自然轴线上采出固定长度 length 的刷毛,共 count 个等弧长点。

    毛长是固定的,而定位器摆出来的轴线不一定正好这么长,所以两种情况都要管:
        轴线比毛长      -> 只取前 length 那一段,后面的定位器只参与决定形状走向
        轴线比毛短      -> 走完轴线后沿末端切向直线延伸补足

    这就是「笔尖定位器只管朝向」的落点:它决定毛往哪个方向长,不决定毛多长。
    """
    total = table[-1]
    if count <= 1:
        return [om.MVector(points[0])]
    tail_dir = _safe_normal(points[-1] - points[-2], om.MVector(0.0, -1.0, 0.0))

    out = []
    for i in range(count):
        s = length * i / float(count - 1)
        if s <= total:
            out.append(_point_at_arc(points, table, s))
        else:
            out.append(points[-1] + tail_dir * (s - total))
    return out


def _profile_integral(alpha, exponent, steps):
    """中点法求 I = ∫₀¹ sin(alpha * (1-x)**p) dx。

    I 的物理含义是空中段的**平均下降率**:走过单位弧长,高度平均降低 I。
    所以从高度 h 落到纸面需要的弧长就是 sAir = h / I。

    注意:
        这里用中点法而不是更精确的 Simpson,是为了和 _integrate_air() 用完全相同的
        离散化。两边取同一个 steps 时,积分出来的末端高度会精确等于 0(而不是差一个
        截断误差),笔尖落点正好在纸面上,不需要任何事后校正。
    """
    total = 0.0
    for k in range(steps):
        x = (k + 0.5) / float(steps)
        total += math.sin(alpha * math.pow(1.0 - x, exponent))
    return total / float(steps)


def _solve_exponent(alpha, target, steps):
    """二分求指数 p,使 I(alpha, p) 恰好等于 target。

    用在「毛尖够得着纸面、但按设定硬度算毛长不够弯到贴平」的时候:把毛自动放软到
    刚好够。I 关于 p 单调递减(p 越小俯角保持得越久、平均下降率越大),所以可以直接二分。

    参数:
        alpha   入射俯角
        target  需要达到的平均下降率,也就是 h / L
        steps   积分分段数,必须和后面 _integrate_air 用的步数一致

    返回:
        p,落在 [EXP_SEARCH_MIN, 1.0] 内。
    """
    lo, hi = EXP_SEARCH_MIN, 1.0
    if _profile_integral(alpha, lo, steps) <= target:
        # 连最软的剖面都达不到要求,毛是真的不够长,交给调用方去判不接触。
        return lo
    for _ in range(EXP_SEARCH_ITER):
        mid = 0.5 * (lo + hi)
        if _profile_integral(alpha, mid, steps) > target:
            lo = mid    # 下降率还偏大 -> p 要往大调
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _integrate_air(origin, tangent, normal, alpha, exponent, s_air, steps):
    """沿弯曲剖面积分出空中段的点序列(不含起点 origin,共 steps 个点)。

    每一步都沿单位方向走 ds,所以折线总长恒等于 s_air —— 弧长守恒是逐步保证的,
    不依赖任何后处理。
    """
    pts = []
    if steps <= 0:
        return pts
    ds = s_air / float(steps)
    pos = om.MVector(origin)
    for k in range(steps):
        x = (k + 0.5) / float(steps)
        phi = alpha * math.pow(1.0 - x, exponent)
        direction = tangent * math.cos(phi) - normal * math.sin(phi)
        pos = pos + direction * ds
        pts.append(om.MVector(pos))
    return pts


def _knot_vector(num_cvs, degree):
    """clamped(首尾夹持)均匀 knot 向量。

    Maya 要求 knot 个数 = CV 个数 + degree - 1(比教科书的 numCVs+degree+1 少两个)。
    首尾各重复 degree 个端点值,这样曲线会精确穿过第一个和最后一个 CV ——
    笔刷的毛根必须落在定位器上,不能被样条往里收。

    例:degree=3, num_cvs=8 -> [0,0,0, 1,2,3,4, 5,5,5],共 10 个。
    """
    span = num_cvs - degree
    knots = [0.0] * degree
    for i in range(1, span):
        knots.append(float(i))
    knots.extend([float(span)] * degree)
    return knots


def _section_scale(brush_type, t):
    """笔刷在 t 处的截面尺寸系数,返回 (宽度系数, 厚度系数)。

    t 从毛根 0 走到笔尖 1。两个系数都还要再乘 brushWidth 才是实际半径。

    四种笔刷的廓形(侧看):

        毛笔 calligraphy   根部饱满,一路收成锥尖
        绘画笔 round       大部分等宽,末端圆润收头
        毛刷 flat          等宽到底,末端平切
        扇形笔 fan         等厚不变,越往尖端越宽(扇开),同时越薄

    说明:
        扁笔(flat / fan)的「宽」指的是垂直于弯曲平面那个方向 —— 压下去的时候
        宽面横着贴在纸上,画出来才是宽笔画。方向由笔杆矩阵的局部 X 轴沿曲线
        平行传输得到,转笔杆就能转刷子朝向。
    """
    t = _clamp(t, 0.0, 1.0)
    if brush_type == BRUSH_ROUND:
        # 末端用高次项快速但圆滑地收口,前面几乎不变细
        scale = math.pow(max(0.0, 1.0 - math.pow(t, 5.0)), 0.4)
        width = thickness = scale
    elif brush_type == BRUSH_FLAT:
        width = thickness = 1.0
    elif brush_type == BRUSH_FAN:
        width = 1.0 + 1.2 * t          # 向尖端扇形展开
        thickness = 1.0 - 0.5 * t      # 同时摊薄
    else:
        # 毛笔:幂次小于 1,根部收得慢、临近尖端才急收,接近真实笔锋
        width = thickness = math.pow(1.0 - t, 0.65)

    aspect = BRUSH_ASPECT.get(brush_type, 1.0)
    return (max(width, MIN_SECTION_SCALE),
            max(thickness * aspect, MIN_SECTION_SCALE * aspect))


def _width_multiplier(segments, t):
    """手动宽度控制在 t 处的倍率。

    segments 是 5 个控制点,均匀落在 t = 0 / 0.25 / 0.5 / 0.75 / 1.0 上,
    中间用 Catmull-Rom 过点插值。全是 1.0 时不改变任何东西。

    说明:
        这是**乘在 brushType 廓形之上**的倍率,不是替代它。所以毛笔还是毛笔,
        只是某一段可以手动加粗或收细。想完全自己塑形,把 brushType 设成 flat
        (等宽廓形)再用这 5 段画出想要的形状。

        用 Catmull-Rom 而不是线性插值,是为了让调完一段之后周围平滑过渡 ——
        线性插值会在控制点处留下折角,沿着毛看过去是一圈一圈的棱。
        代价是相邻段落差很大时会轻微过冲,所以最后夹一下负值。
    """
    count = len(segments)
    if count == 0:
        return 1.0
    if count == 1:
        return max(0.0, segments[0])

    x = _clamp(t, 0.0, 1.0) * (count - 1)
    index = int(x)
    if index > count - 2:
        index = count - 2
    local = x - index

    p1 = segments[index]
    p2 = segments[index + 1]
    # 两端各镜像延伸一个虚拟控制点,补齐 Catmull-Rom 需要的四个点
    p0 = segments[index - 1] if index > 0 else 2.0 * p1 - p2
    p3 = segments[index + 2] if index + 2 < count else 2.0 * p2 - p1

    t2 = local * local
    t3 = t2 * local
    value = 0.5 * (2.0 * p1
                   + (p2 - p0) * local
                   + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                   + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t3)
    return max(0.0, value)


def _parallel_frames(points, seed):
    """沿折线做平行传输,给每个点算一个截面坐标系。

    返回:
        [(tangent, side, up), ...],三个都是单位向量且两两正交。
        side 是截面的「宽」方向,up 是「厚」方向。

    说明:
        逐段把上一个参考向量按「切向怎么转,它就怎么转」的方式带过去
        (用 MQuaternion 从上一段切向转到这一段切向)。这就是平行传输,
        它保证相邻截面之间不会凭空扭转 —— 直接每段拿切向和某个固定世界轴叉乘
        的话,曲线一拐弯截面就会绕着轴突然翻转,扁笔上尤其刺眼。
    """
    count = len(points)
    tangents = []
    for i in range(count):
        if i == 0:
            vec = points[1] - points[0]
        elif i == count - 1:
            vec = points[-1] - points[-2]
        else:
            vec = points[i + 1] - points[i - 1]
        tangents.append(_safe_normal(vec, om.MVector(0.0, -1.0, 0.0)))

    frames = []
    side = _orthonormalize(seed, tangents[0], _any_perpendicular(tangents[0]))
    for i in range(count):
        if i > 0:
            rotation = om.MQuaternion(tangents[i - 1], tangents[i])
            side = side.rotateBy(rotation)
            # 逐段旋转会累积浮点漂移,每一步重新正交化一次,成本可以忽略
            side = _orthonormalize(side, tangents[i], side)
        up = (tangents[i] ^ side).normal()
        frames.append((tangents[i], side, up))
    return frames


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------

class BrushTipCurveNode(ompx.MPxNode):
    """刷毛压弯求解节点。详细算法见模块 docstring。"""

    # 属性句柄,全部在 nodeInitializer() 中被赋值
    aInMesh = om.MObject()
    aControlMatrix = om.MObject()
    aBristleLength = om.MObject()
    aStiffness = om.MObject()
    aEnvelope = om.MObject()
    aSamples = om.MObject()
    aCurveDegree = om.MObject()
    aContactOffset = om.MObject()
    aConformToSurface = om.MObject()
    aParentInverseMatrix = om.MObject()

    aBrushType = om.MObject()
    aBrushWidth = om.MObject()
    aWidthSegments = []          # 5 个,毛根 -> 笔尖
    aMeshSides = om.MObject()
    aSpreadByPressure = om.MObject()
    aFlattenByPressure = om.MObject()

    aOutCurve = om.MObject()
    aOutMesh = om.MObject()
    aOutPressure = om.MObject()
    aOutContact = om.MObject()
    aOutContactPoint = om.MObject()

    def __init__(self):
        ompx.MPxNode.__init__(self)
        # 拓扑只跟 (环数, 每圈点数) 有关,顶点位置每帧变、连接关系不变。
        # 缓存下来省掉每帧重建那几个 MIntArray —— 实测填数组才是开销大头,
        # MFnMesh.create() 本身只占其中一小部分。
        self._topology_key = None
        self._topology = None

    # -- 内部辅助 -----------------------------------------------------------

    @staticmethod
    def _root_attribute(plug):
        """把子属性 / 数组元素归一到它的根属性。

        outContactPoint 是 k3Double,Maya 可能拿它的某个子 plug(ocpx/ocpy/ocpz)
        来调 compute,直接和 aOutContactPoint 比会匹配不上,导致输出永远是脏的。

        注意:
            API 1.0 里 isChild / isElement 是**方法**,要带括号调用;
            API 2.0 才是属性。两边代码互抄时这里必翻车(不带括号永远为真)。
        """
        if plug.isChild():
            return plug.parent().attribute()
        if plug.isElement():
            return plug.array().attribute()
        return plug.attribute()

    @staticmethod
    def _read_control_points(array_handle):
        """读出定位器的世界平移,外加毛根矩阵的局部 X 轴。

        返回:
            (points, x_axis) —— points 是按逻辑索引升序排列的 MVector 列表,
            x_axis 是索引最小那个矩阵(毛根/笔杆)的局部 X 轴单位向量,
            垂直下压时用它来决定刷毛往哪边倒。

        说明:
            MArrayDataHandle 的物理顺序本来就是按逻辑索引升序排的,所以顺序遍历
            即可 —— 稀疏数组(用户删掉中间某个元素)也不会乱序,只是逻辑索引空着。
            API 1.0 用 elementCount() + jumpToArrayElement();API 2.0 则是
            len() + jumpToPhysicalElement(),名字全不一样。
        """
        points = []
        x_axis = om.MVector(1.0, 0.0, 0.0)
        count = array_handle.elementCount()
        for i in range(count):
            array_handle.jumpToArrayElement(i)
            matrix = array_handle.inputValue().asMatrix()
            points.append(om.MVector(matrix(3, 0), matrix(3, 1), matrix(3, 2)))
            if i == 0:
                x_axis = om.MVector(matrix(0, 0), matrix(0, 1), matrix(0, 2))
        return points, _safe_normal(x_axis, om.MVector(1.0, 0.0, 0.0))

    @staticmethod
    def _bend_tangent(incident, normal, x_axis):
        """决定刷毛沿纸面铺开的方向。

        一般情况就是入射方向在纸面上的投影(笔往哪边斜就往哪边铺)。但笔杆越接近
        垂直下压,这个投影越短(长度正好是 cos(alpha)),方向也越不可靠,到完全
        垂直时彻底退化成零向量 —— 这时候改用笔杆矩阵的局部 X 轴投影,绑定师转一下
        笔杆定位器就能控制毛往哪边倒。

        注意(重要,不是可以调好的 bug):
            笔从右倾扫到左倾时,倒向本来就要翻 180 度,这个跳变**消除不掉**。
            真实毛笔在完全垂直的那一刻是向四周均匀散开的(所以垂直下压得到的是
            一个圆点笔触),而单条中轴曲线没有办法表示「四周散开」,它必须选一边。

            所以这里不追求消除跳变,只追求让它落在**确定且可解释**的位置:
            恰好是笔通过垂直的那一刻。做法是先把回退方向翻到与真实倾斜方向同侧,
            再做 smoothstep 混合 —— 两个向量夹角因此恒 <= 90 度,混合结果不会在
            中途经过零向量。如果不做这个符号对齐,线性混合两个相反向量会在权重
            0.5 处退化,跳变反而被挪到一个由 TANGENT_EPS 决定的、毫无道理的角度上。
        """
        fallback_seed = _any_perpendicular(normal)
        fallback = _orthonormalize(x_axis, normal, fallback_seed)

        projected = incident - normal * (incident * normal)
        length = projected.length()
        if length <= EPS:
            return fallback

        tilt = projected / length
        if tilt * fallback < 0.0:
            fallback = fallback * -1.0

        weight = _smoothstep(0.0, TANGENT_EPS, length)
        blended = tilt * weight + fallback * (1.0 - weight)
        return _orthonormalize(blended, normal, fallback)

    def _get_mesh(self, data):
        """取纸面,拿不到就返回 None(视作没有纸,刷毛保持自然形状)。

        注意:
            必须先查 isDestination()。mesh 连上之后又断开时,datablock 里会**残留**
            上一次求值的几何,asMesh().isNull() 这时候返回 False,照用的话笔刷会
            和一张已经不存在的纸发生碰撞 —— 这个坑不查连接就发现不了。
        """
        plug = om.MPlug(self.thisMObject(), BrushTipCurveNode.aInMesh)
        if not plug.isDestination():
            return None
        mesh_obj = data.inputValue(BrushTipCurveNode.aInMesh).asMesh()
        if mesh_obj.isNull():
            return None
        fn_mesh = om.MFnMesh(mesh_obj)
        if fn_mesh.numPolygons() == 0:
            return None
        return fn_mesh

    @staticmethod
    def _raycast(fn_mesh, origin, direction, max_dist):
        """从 origin 沿单位向量 direction 打一条长 max_dist 的射线。

        返回:
            (hit_point, normal, distance),未命中返回 None。normal 是单位向量,
            且已翻转到朝向射线来源的一侧 —— 纸是单面的,正面反面都该挡住笔。

        注意:
            - 全程用 MSpace.kWorld。连 worldMesh[0] 时点数据其实仍是**局部坐标**,
              世界变换藏在 mesh data 自带的矩阵里,传 kObject 不会报错,只会安静地
              给出错误的碰撞位置。
            - maxParam 是「射线参数」不是距离,单位是 |rayDirection|。这里传进来的
              direction 已经归一化,所以 maxParam 才等于世界单位距离。
            - API 1.0 的 closestIntersection 返回 bool,命中结果通过输出参数带出来,
              float / int 的输出参数必须用 MScriptUtil 包一层;读回时是
              util.getFloat(ptr) 而不是 util.getFloat()。
        """
        if max_dist <= EPS:
            return None

        hit_point = om.MFloatPoint()
        param_util = om.MScriptUtil(0.0)
        param_ptr = param_util.asFloatPtr()
        face_util = om.MScriptUtil(0)
        face_ptr = face_util.asIntPtr()
        tri_util = om.MScriptUtil(0)
        tri_ptr = tri_util.asIntPtr()

        found = fn_mesh.closestIntersection(
            om.MFloatPoint(origin.x, origin.y, origin.z),
            om.MFloatVector(direction.x, direction.y, direction.z),
            None, None, False,
            om.MSpace.kWorld,
            float(max_dist),
            False,
            None,
            hit_point, param_ptr, face_ptr, tri_ptr, None, None)
        if not found:
            return None

        normal = om.MVector()
        fn_mesh.getPolygonNormal(face_util.getInt(face_ptr), normal,
                                 om.MSpace.kWorld)
        normal = _safe_normal(normal, om.MVector(0.0, 1.0, 0.0))
        if normal * direction > 0.0:
            normal = normal * -1.0

        return (om.MVector(hit_point.x, hit_point.y, hit_point.z),
                normal, param_util.getFloat(param_ptr))

    @staticmethod
    def _conform(fn_mesh, points, normal, contact_offset, probe):
        """把贴地段逐点吸附到真实表面。

        接触点处的切平面只有在纸是平的时候才等于纸面。地面起伏时,贴地段会顺着
        切平面走直线,该抬的地方不抬、该降的地方不降,直接插进地里。所以这里对每个
        点从正上方往下补打一条短射线,落到真实表面上再抬 contactOffset。

        说明:
            吸附会轻微改变折线总长,严格的弧长守恒只在平面上成立(平面上这些点本来
            就落在面上,射线打回原处,不产生任何偏移)。这是为了不穿地付出的代价。
        """
        lift = max(probe * 0.25, 1e-3)
        down = normal * -1.0
        out = []
        for point in points:
            start = point + normal * lift
            hit = BrushTipCurveNode._raycast(fn_mesh, start, down, lift * 2.0)
            if hit is None:
                # 刷毛铺出纸边了,保持切平面上的位置,不强行拉回来。
                out.append(om.MVector(point))
                continue
            hit_point, local_n, _ = hit
            if local_n * normal < 0.0:
                local_n = local_n * -1.0
            out.append(hit_point + local_n * contact_offset)
        return out

    @staticmethod
    def _curve_data(points, degree):
        """把点列做成 NURBS 曲线 data object(可直接 setMObject 的那个)。

        注意:
            - Maya 的 knot 个数是 numCVs + degree - 1,比教科书的 numCVs+degree+1
              少两个。数量不对会抛 kInvalidParameter。
            - CV 少于 degree+1 时曲线建不出来,这里补重复的末点顶上。
              重复 CV 对 clamped 曲线是合法的。
            - 要写进 datablock 的是 MFnNurbsCurveData().create() 得到的 data object,
              不是 MFnNurbsCurve().create() 的返回值(那个是曲线几何本身)。
        """
        cvs = om.MPointArray()
        for point in points:
            cvs.append(om.MPoint(point.x, point.y, point.z))
        while cvs.length() < degree + 1:
            cvs.append(om.MPoint(cvs[cvs.length() - 1]))

        knots = om.MDoubleArray()
        for knot in _knot_vector(cvs.length(), degree):
            knots.append(knot)

        curve_data = om.MFnNurbsCurveData().create()
        om.MFnNurbsCurve().create(cvs, knots, degree,
                                  om.MFnNurbsCurve.kOpen,
                                  False,        # create2D
                                  False,        # createRational
                                  curve_data)   # parentOrOwner
        return curve_data

    def _mesh_topology(self, rings, sides):
        """给 (rings, sides) 造出连接关系和 UV,并缓存。

        返回:
            (counts, connects, us, vs, uv_counts, uv_ids) —— 都是 Maya 数组类型。
            索引越界时返回 None,调用方应当放弃生成 mesh。

        注意:
            **polygonConnects 越界不会抛异常**。MFnMesh.create() 照样返回成功,
            然后 Maya 会在之后某一次访问这个 mesh 时直接 Fatal Error —— 没有
            Python 异常、try/except 拦不住、整个进程连同未保存的场景一起没。
            所以这里在交出去之前自己把范围查一遍。查一次就缓存,不影响每帧开销。
        """
        key = (rings, sides)
        if self._topology_key == key:
            return self._topology

        counts = []
        connects = []
        uv_counts = []
        uv_ids = []

        # UV 网格比顶点多一列:周向接缝处 u=0 和 u=1 是同一圈顶点的两个 UV,
        # 不重复一列的话贴图会在接缝上整个倒着压缩回去。
        stride = sides + 1

        # 侧壁。绕序 (i,j) -> (i,j+1) -> (i+1,j+1) -> (i+1,j);配合
        # _parallel_frames 保证的右手系(up = tangent ^ side),法线朝外。
        for i in range(rings - 1):
            for j in range(sides):
                k = (j + 1) % sides
                counts.append(4)
                connects.extend((i * sides + j, i * sides + k,
                                 (i + 1) * sides + k, (i + 1) * sides + j))
                uv_counts.append(4)
                uv_ids.extend((i * stride + j, i * stride + j + 1,
                               (i + 1) * stride + j + 1, (i + 1) * stride + j))

        # 毛根端盖:法线朝 -tangent,顶点相对侧壁反着数。
        counts.append(sides)
        connects.extend(range(sides - 1, -1, -1))
        uv_counts.append(sides)
        uv_ids.extend(j for j in range(sides - 1, -1, -1))

        # 笔尖端盖:法线朝 +tangent,顺数。
        base = (rings - 1) * sides
        counts.append(sides)
        connects.extend(range(base, base + sides))
        uv_counts.append(sides)
        uv_ids.extend((rings - 1) * stride + j for j in range(sides))

        limit = rings * sides
        if connects and (max(connects) >= limit or min(connects) < 0):
            self._topology_key = key
            self._topology = None
            return None

        us = om.MFloatArray()
        vs = om.MFloatArray()
        for i in range(rings):
            for j in range(stride):
                us.append(float(j) / float(sides))
                vs.append(float(i) / float(rings - 1))

        count_array = om.MIntArray()
        om.MScriptUtil.createIntArrayFromList(counts, count_array)
        connect_array = om.MIntArray()
        om.MScriptUtil.createIntArrayFromList(connects, connect_array)
        uv_count_array = om.MIntArray()
        om.MScriptUtil.createIntArrayFromList(uv_counts, uv_count_array)
        uv_id_array = om.MIntArray()
        om.MScriptUtil.createIntArrayFromList(uv_ids, uv_id_array)

        self._topology_key = key
        self._topology = (count_array, connect_array, us, vs,
                          uv_count_array, uv_id_array)
        return self._topology

    def _mesh_data(self, points, pressure, landing, opts):
        """沿刷毛扫掠出笔刷实体,返回可直接 setMObject 的 mesh data object。

        参数:
            points   刷毛采样点(已经是输出空间)
            pressure 贴地长度占比,驱动散开和压扁
            landing  落纸点下标,None 表示没接触
            opts     见 compute 里组装的设置 dict

        拓扑:
            rings × sides 个顶点,(rings-1) × sides 个四边形,外加两个 n 边形端盖。
            截面坐标系由 _parallel_frames 平行传输得到,扁笔不会随曲线拐弯乱扭。
        """
        sides = opts["sides"]
        width = opts["width"]
        rings = len(points)
        mesh_data = om.MFnMeshData().create()

        if rings < 2:
            return mesh_data
        # brushWidth 归零时**不**返回空 mesh:拓扑时有时无会让下游的 deformer、
        # 材质分配、UV 全部失效,而且空 mesh 上连 MFnMesh 都构造不出来。
        # 夹到一个极小值,毛变成一根几乎看不见的线,顶点数和面数始终不变。
        width = max(width, 1e-5)

        frames = _parallel_frames(points, opts["seed"])
        spread = opts["spread"] * pressure
        flatten = opts["flatten"] * pressure

        # 受压权重:落纸点之前 0、之后 1,中间用几个采样点平滑过渡。
        # 不做过渡的话刷毛会在接触点突然粗一圈,像套了个箍。
        fade = max(1.0, rings * 0.08)

        vertices = om.MFloatPointArray()
        for i in range(rings):
            t = i / float(rings - 1)
            width_scale, thick_scale = _section_scale(opts["type"], t)
            # 手动 5 段控制是乘在类型廓形之上的,宽和厚同时缩放 ——
            # 「这一段粗一点」指的是整个截面变粗,不是只往一个方向摊开,
            # 否则扁笔调着调着纵横比就变了。
            manual = _width_multiplier(opts["segments"], t)

            if landing is None:
                pressed = 0.0
            else:
                pressed = _smoothstep(landing - fade, landing + fade * 0.5, i)
            half_w = width * width_scale * manual * (1.0 + spread * pressed)
            half_h = width * thick_scale * manual * (1.0 - flatten * pressed)

            center = points[i]
            side, up = frames[i][1], frames[i][2]
            for j in range(sides):
                angle = 2.0 * math.pi * j / float(sides)
                point = (center
                         + side * (math.cos(angle) * half_w)
                         + up * (math.sin(angle) * half_h))
                vertices.append(om.MFloatPoint(point.x, point.y, point.z))

        topology = self._mesh_topology(rings, sides)
        if topology is None:
            return mesh_data
        counts, connects, us, vs, uv_counts, uv_ids = topology

        # numVertices / numPolygons 直接取数组长度,别用公式另算一遍 ——
        # 对不上是 kInvalidParameter,而公式最容易在改拓扑时忘记同步。
        mesh_fn = om.MFnMesh()
        mesh_fn.create(vertices.length(), counts.length(),
                       vertices, counts, connects, mesh_data)
        # 没有 UV 也能赋材质(不会报错),但贴图会整张糊成一个像素。
        mesh_fn.setUVs(us, vs)
        mesh_fn.assignUVs(uv_counts, uv_ids)
        return mesh_data

    # -- 解算 ---------------------------------------------------------------

    def _solve_pressed(self, fn_mesh, root, incident, x_axis, total_len,
                       stiffness, samples, contact_offset, conform):
        """求解被压弯的刷毛形状。

        参数:
            fn_mesh        纸面(世界空间)
            root           毛根位置
            incident       毛根处的刷毛方向(单位向量,指向笔尖)
            x_axis         笔杆矩阵局部 X 轴,垂直下压时的倒向参考
            total_len      刷毛总弧长,固定不变
            stiffness      0-1 毛硬度
            samples        输出点数
            contact_offset 贴地段抬离表面的高度
            conform        贴地段是否吸附到真实表面

        返回:
            (points, contact_point, pressure, landing) —— landing 是落纸点在
            points 里的下标,它之后的点都是躺在纸上的那一段(生成 mesh 时
            靠它决定哪几圈截面要因为受压而变宽压扁)。判定为未接触时返回 None。

        说明:
            判不接触只有三种情况,合起来保证任何输入都不会算出 NaN:
              - 射线打不到纸面        -> 笔根本没朝着纸
              - 毛根已在纸面下方      -> 整根倒插,不在模型适用范围内
              - 毛长 <= 到纸面的直线距离 -> 毛是真的够不着

            注意**没有**「按这个硬度弯不到」这一条。只要毛尖够得着纸面就一定会弯:
            设定硬度算出来的 sAir 超过毛长时,走 _solve_exponent 自动解出一个更软的
            有效硬度,让毛恰好弯到纸面。物理上也说得通 —— 刚接触时毛是绷紧的,
            压深了才有余量按自己的软硬程度弯。
        """
        hit = self._raycast(fn_mesh, root, incident, total_len)
        if hit is None:
            return None
        hit_point, normal, _ = hit

        # 纸面被 contactOffset 整体抬高一层,空中段直接降到这个高度、贴地段就在
        # 这个高度平铺。比「先算到真实纸面再把贴地段抬起来」干净:后者会在空中段
        # 和贴地段的接缝处留一个小台阶。
        height = (root - hit_point) * normal - contact_offset
        if height <= EPS:
            return None

        sin_alpha = -(incident * normal)
        if sin_alpha <= EPS:
            return None
        alpha = math.asin(_clamp(sin_alpha, 0.0, 1.0))

        # 完全不弯(走直线)时够到纸面所需的弧长。毛比这还短就是真够不着。
        # 弯曲只会让所需弧长更长,所以这是接触与否的下界。
        if height / sin_alpha >= total_len:
            return None

        tangent = self._bend_tangent(incident, normal, x_axis)
        exponent = STIFFNESS_EXP_MIN + stiffness * (1.0 - STIFFNESS_EXP_MIN)

        integral = _profile_integral(alpha, exponent, SOLVE_STEPS)
        if integral <= EPS:
            return None

        segments = samples - 1
        n_air = segments
        n_ground = 0
        s_air = total_len
        soften = height / integral > total_len

        if not soften:
            # 初判毛有富余:设定硬度完全生效,多出来的长度躺在纸上。
            # 按空中段的弧长占比分配采样点,两段各自至少留 2 个点。
            n_air = int(_clamp(int(round(segments * (height / integral) / total_len)),
                               2, segments - 2))
            n_ground = segments - n_air

            # 用**实际输出点数**重算积分。_profile_integral 和 _integrate_air 用的是
            # 同一套中点离散,所以取同一个 n_air 时,积分出来的末端高度精确等于 0,
            # 笔尖正好落在纸面上,不需要任何事后校正。
            integral = _profile_integral(alpha, exponent, n_air)
            if integral <= EPS or height / integral > total_len:
                # 上面那次初判用的是 SOLVE_STEPS 步的粗积分,换成实际采样点数以后
                # 才发现毛其实不够按这个硬度弯。必须退回自动放软,**不能**把 s_air
                # 夹到毛长了事:夹完落点是悬在空中的,贴地段接着水平铺出去,再被
                # conform 拽回纸面,折线就凭空变长了。
                soften = True
            else:
                s_air = height / integral

        if soften:
            # 毛不够按这个硬度弯到贴平:自动放软到刚好够,没有贴地段。
            n_air = segments
            n_ground = 0
            exponent = _solve_exponent(alpha, height / total_len, n_air)
            # 直接让空中段走满全长,而不是再用 height/integral 反算一次。二分总有
            # 残差,反算出来的 s_air 会比毛长差一丁点,而这个分支没有贴地段去吸收
            # 那一截,长度就白白亏掉了。走满全长则把残差转移到末端高度上
            # (1e-8 量级的离地误差),长度严格守恒 —— 这是划算的交换。
            s_air = total_len

        s_ground = total_len - s_air

        air_points = _integrate_air(root, tangent, normal, alpha, exponent,
                                    s_air, n_air)
        points = [om.MVector(root)] + air_points

        if n_ground > 0:
            landing = air_points[-1]
            step = s_ground / float(n_ground)
            ground_points = []
            for k in range(1, n_ground + 1):
                ground_points.append(landing + tangent * (step * k))
            if conform:
                ground_points = self._conform(fn_mesh, ground_points, normal,
                                              contact_offset, total_len)
            points.extend(ground_points)

        # 落纸点就是空中段的最后一个点,它的下标正好等于 n_air(前面还有个毛根)。
        return (points, hit_point, _clamp(s_ground / total_len, 0.0, 1.0), n_air)

    def _write(self, data, points, contact_point, pressure, contact,
               landing, opts):
        """一次写齐全部输出。

        compute 本来就是一趟算全部结果的,分开写只会漏 setClean,让某个输出
        一直是脏的、每帧重算。

        参数:
            points        世界空间的刷毛采样点
            contact_point 落纸点
            pressure      贴地长度占比
            contact       是否接触
            landing       落纸点在 points 里的下标;None 表示没接触
            opts          其余设置,见 compute 里组装的那个 dict
        """
        world_matrix = opts["matrix"]
        local = []
        for point in points:
            transformed = om.MPoint(point.x, point.y, point.z) * world_matrix
            local.append(om.MVector(transformed.x, transformed.y, transformed.z))

        data.outputValue(self.aOutCurve).setMObject(
            self._curve_data(local, opts["degree"]))
        data.outputValue(self.aOutMesh).setMObject(
            self._mesh_data(local, pressure, landing, opts))
        data.outputValue(self.aOutPressure).setDouble(pressure)
        data.outputValue(self.aOutContact).setBool(contact)

        cp = om.MPoint(contact_point.x, contact_point.y,
                       contact_point.z) * world_matrix
        data.outputValue(self.aOutContactPoint).set3Double(cp.x, cp.y, cp.z)

        for attr in (self.aOutCurve, self.aOutMesh, self.aOutPressure,
                     self.aOutContact, self.aOutContactPoint):
            data.setClean(attr)

    # -- 求值 ---------------------------------------------------------------

    def compute(self, plug, data):
        """依赖图求值入口。

        返回:
            om.kUnknownParameter 表示请求的 plug 与本节点无关,交回 Maya 走默认
            处理;正常处理完直接返回 None。

        处理流程:
            1. 判断根属性是否为四个输出之一,不是则立即交回;
            2. 读参数和定位器,搭出未受力的自然毛形(长度固定为 bristleLength);
            3. 若 envelope > 0 且纸面可用,解算压弯形状;
            4. 按 envelope 在自然形和压弯形之间混合,一次写齐所有输出。

        说明:
            全程不用 try/except,改成处处防御式取值 —— 定位器不足、纸面没连、
            刷毛长度为零、射线打空、入射角退化,每一种都有明确的兜底分支,
            保证任何输入下都不会抛异常或输出 NaN。
        """
        root_attr = self._root_attribute(plug)
        if (root_attr != self.aOutCurve
                and root_attr != self.aOutMesh
                and root_attr != self.aOutPressure
                and root_attr != self.aOutContact
                and root_attr != self.aOutContactPoint):
            return om.kUnknownParameter

        # ---- 读参数 --------------------------------------------------------
        bristle_length = data.inputValue(self.aBristleLength).asDouble()
        stiffness = _clamp(data.inputValue(self.aStiffness).asDouble(),
                           0.0, 1.0)
        envelope = _clamp(data.inputValue(self.aEnvelope).asDouble(), 0.0, 1.0)
        samples = max(6, data.inputValue(self.aSamples).asInt())
        degree = (3 if data.inputValue(self.aCurveDegree).asShort()
                  == DEGREE_CUBIC else 1)
        contact_offset = data.inputValue(self.aContactOffset).asDouble()
        conform = data.inputValue(self.aConformToSurface).asBool()
        world_matrix = data.inputValue(self.aParentInverseMatrix).asMatrix()

        control, x_axis = self._read_control_points(
            data.inputArrayValue(self.aControlMatrix))

        # mesh 相关设置打包传下去,省得 _write 长出一串位置参数。
        opts = {
            "matrix": world_matrix,
            "degree": degree,
            "type": data.inputValue(self.aBrushType).asShort(),
            "width": max(0.0, data.inputValue(self.aBrushWidth).asDouble()),
            "sides": max(3, data.inputValue(self.aMeshSides).asInt()),
            "spread": max(0.0, data.inputValue(self.aSpreadByPressure).asDouble()),
            "flatten": _clamp(data.inputValue(self.aFlattenByPressure).asDouble(),
                              0.0, 1.0),
            "segments": [max(0.0, data.inputValue(attr).asDouble())
                         for attr in self.aWidthSegments],
            # 截面的「宽」方向种子:用笔杆局部 X 轴,和垂直下压时的倒向参考同一个轴,
            # 这样转笔杆既转倒向也转刷子朝向,不会各转各的。
            "seed": x_axis,
        }

        # ---- 自然毛形 ------------------------------------------------------
        # 定位器不够两个就没有「刷毛」可言。输出一条退化成一点的曲线,让下游拿到的
        # 是合法数据而不是空指针。
        if len(control) < 2:
            seed = control[0] if control else om.MVector(0.0, 0.0, 0.0)
            self._write(data, [seed] * samples, seed, 0.0, False, None, opts)
            return None

        dense = _densify(control, 8)
        table = _arc_table(dense)
        # 毛长优先用 bristleLength;没填(<=0)才退回定位器之间的距离。
        total_len = bristle_length if bristle_length > EPS else table[-1]
        if total_len <= EPS or table[-1] <= EPS:
            # 所有定位器重合,或者毛长被设成了 0,同样退化成一点。
            self._write(data, [control[0]] * samples, control[0],
                        0.0, False, None, opts)
            return None

        natural = _sample_bristle(dense, table, total_len, samples)
        # 毛根处的切向就是「笔指向哪儿」。两个定位器时它正好是毛根->笔尖的方向。
        incident = _safe_normal(dense[1] - dense[0], om.MVector(0.0, -1.0, 0.0))

        # ---- 压弯解算 ------------------------------------------------------
        solved = None
        if envelope > EPS:
            fn_mesh = self._get_mesh(data)
            if fn_mesh is not None:
                solved = self._solve_pressed(
                    fn_mesh, control[0], incident, x_axis, total_len,
                    stiffness, samples, contact_offset, conform)

        # ---- 混合并写出 ----------------------------------------------------
        if solved is None:
            self._write(data, natural, natural[-1], 0.0, False, None, opts)
            return None

        bent, contact_point, pressure, landing = solved
        if envelope >= 1.0:
            points = bent
        else:
            # 自然形和压弯形都是按弧长均匀参数化的 samples 个点,逐点插值才有意义。
            points = []
            for i in range(samples):
                points.append(natural[i] + (bent[i] - natural[i]) * envelope)
            pressure *= envelope

        self._write(data, points, contact_point, pressure, True, landing, opts)
        return None


# ---------------------------------------------------------------------------
# 注册用的 creator / initializer
# ---------------------------------------------------------------------------

def nodeCreator():
    """API 1.0 要求把实例包进 MPxPtr 再交给 Maya。"""
    return ompx.asMPxPtr(BrushTipCurveNode())


def nodeInitializer():
    """声明全部属性和依赖关系。

    注意:
        API 1.0 用 setXxx() 方法设置属性特性(setKeyable(True)),
        API 2.0 才是直接赋值(keyable = True)。两边互抄时赋值会静默无效。
    """
    nAttr = om.MFnNumericAttribute()
    tAttr = om.MFnTypedAttribute()
    mAttr = om.MFnMatrixAttribute()
    eAttr = om.MFnEnumAttribute()

    cls = BrushTipCurveNode

    # ---- 碰撞输入 ----------------------------------------------------------
    # inMesh:纸张/地面。必须连 shape 的 worldMesh[0] —— 连 outMesh 会得到本地
    # 空间几何,纸一旦被移动过碰撞位置就是错的。
    cls.aInMesh = tAttr.create("inMesh", "im", om.MFnData.kMesh)
    tAttr.setStorable(False)
    tAttr.setKeyable(False)

    # ---- 刷毛形状输入 ------------------------------------------------------
    # controlMatrix:定位器的 worldMatrix[0]。逻辑索引升序 = 毛根 -> 笔尖朝向,
    # 至少两个。多于两个时中间的点用 Catmull-Rom 过点插值成自然毛形。
    cls.aControlMatrix = mAttr.create("controlMatrix", "cmx",
                                      om.MFnMatrixAttribute.kDouble)
    mAttr.setArray(True)
    mAttr.setStorable(True)
    mAttr.setReadable(False)
    mAttr.setDisconnectBehavior(om.MFnAttribute.kDelete)

    # bristleLength:毛长,固定不变。定位器只决定毛往哪个方向长、长成什么形状,
    # 不决定长度 —— 真实笔刷压下去只会弯,不会变长。
    # 留 0 表示退回旧行为:用定位器之间的距离当毛长(那样拖笔尖定位器会改变毛长)。
    cls.aBristleLength = nAttr.create("bristleLength", "bln",
                                      om.MFnNumericData.kDouble, 0.0)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setSoftMax(10.0)

    # ---- 笔刷手感 ----------------------------------------------------------
    # stiffness:毛的软硬。1=硬毛(弯成均匀圆弧,贴地段短),0=软毛(上段保持
    # 笔杆方向,临近纸面才急弯,贴地段长)。见模块 docstring 的 p 映射。
    cls.aStiffness = nAttr.create("stiffness", "stf",
                                  om.MFnNumericData.kDouble, 0.35)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setMax(1.0)

    # envelope:效果开关。0 = 完全不弯,直接输出定位器给出的自然形状(方便
    # 对比和临时关掉);1 = 全效。中间值在两者之间线性混合。
    cls.aEnvelope = nAttr.create("envelope", "env",
                                 om.MFnNumericData.kDouble, 1.0)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setMax(1.0)

    # ---- 输出曲线设置 ------------------------------------------------------
    # samples:输出曲线的 CV 个数。下限 6 是算法要求 —— 空中段和贴地段各自
    # 至少要留 2 个点,再加上毛根那个点。
    cls.aSamples = nAttr.create("samples", "smp",
                                om.MFnNumericData.kInt, 24)
    nAttr.setKeyable(True)
    nAttr.setMin(6)
    nAttr.setSoftMax(64)
    nAttr.setMax(400)

    cls.aCurveDegree = eAttr.create("curveDegree", "cdg", DEGREE_CUBIC)
    eAttr.addField("linear", DEGREE_LINEAR)
    eAttr.addField("cubic", DEGREE_CUBIC)
    eAttr.setKeyable(True)

    # contactOffset:沿法线把贴地段抬离表面一点点,避免 sweep 出来的毛和纸面
    # z-fighting。默认 0。
    cls.aContactOffset = nAttr.create("contactOffset", "cof",
                                      om.MFnNumericData.kDouble, 0.0)
    nAttr.setKeyable(True)
    nAttr.setSoftMin(0.0)
    nAttr.setSoftMax(0.1)

    # conformToSurface:贴地段是否逐点吸附到真实表面。纸是平的时候开不开都
    # 一样;地面起伏时必须开,否则贴地段会按接触点的切平面走直线穿进地里。
    cls.aConformToSurface = nAttr.create("conformToSurface", "cts",
                                         om.MFnNumericData.kBoolean, True)
    nAttr.setKeyable(True)

    # parentInverseMatrix:连输出曲线 transform 的 worldInverseMatrix[0],
    # 把世界空间的解算结果转回曲线自己的本地空间。不连就是单位阵,输出即世界空间。
    cls.aParentInverseMatrix = mAttr.create("parentInverseMatrix", "pim",
                                            om.MFnMatrixAttribute.kDouble)
    mAttr.setStorable(False)
    mAttr.setKeyable(False)

    # ---- 笔刷 mesh ---------------------------------------------------------
    # brushType:决定截面形状和粗细廓形,见 _section_scale()。
    # 它**不会**自动改 stiffness —— DG 节点不能回写自己的输入。切换类型时顺带
    # 设好推荐硬度的是 brush_utils.set_brush_type() 和 AE 模板。
    cls.aBrushType = eAttr.create("brushType", "bty", BRUSH_CALLIGRAPHY)
    eAttr.addField("calligraphy", BRUSH_CALLIGRAPHY)
    eAttr.addField("round", BRUSH_ROUND)
    eAttr.addField("flat", BRUSH_FLAT)
    eAttr.addField("fan", BRUSH_FAN)
    eAttr.setKeyable(True)

    # brushWidth:毛束的基础半径。截面实际尺寸 = brushWidth × 廓形系数。
    cls.aBrushWidth = nAttr.create("brushWidth", "bwd",
                                   om.MFnNumericData.kDouble, 0.08)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setSoftMax(0.5)

    # widthSegment1..5:沿毛长的 5 段手动宽度倍率,均匀落在 t=0/0.25/0.5/0.75/1。
    # 乘在 brushType 廓形之上,全留 1.0 就是不干预。中间用 Catmull-Rom 平滑过渡。
    # 想完全自己塑形:把 brushType 设成 flat(等宽),再用这 5 段画廓形。
    cls.aWidthSegments = []
    for index in range(WIDTH_SEGMENTS):
        attr = nAttr.create("widthSegment{0}".format(index + 1),
                            "ws{0}".format(index + 1),
                            om.MFnNumericData.kDouble, 1.0)
        nAttr.setKeyable(True)
        nAttr.setMin(0.0)
        nAttr.setSoftMax(3.0)
        cls.aWidthSegments.append(attr)

    # meshSides:截面一圈几个点。8 够圆了;扁笔可以少一些,毛笔想要光滑锥尖可以给 12。
    cls.aMeshSides = nAttr.create("meshSides", "msd",
                                  om.MFnNumericData.kInt, 8)
    nAttr.setKeyable(True)
    nAttr.setMin(3)
    nAttr.setSoftMax(24)
    nAttr.setMax(64)

    # spreadByPressure:压下去之后贴地那一段横向散开多少(倍率增量)。
    # 0 = 不散开;0.8 = 满压时宽度变成 1.8 倍。笔画变粗主要靠它。
    cls.aSpreadByPressure = nAttr.create("spreadByPressure", "spp",
                                         om.MFnNumericData.kDouble, 0.8)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setSoftMax(3.0)

    # flattenByPressure:贴地段被压扁多少。0 = 不压扁;0.5 = 满压时厚度减半。
    cls.aFlattenByPressure = nAttr.create("flattenByPressure", "flp",
                                          om.MFnNumericData.kDouble, 0.5)
    nAttr.setKeyable(True)
    nAttr.setMin(0.0)
    nAttr.setMax(1.0)

    # ---- 输出 --------------------------------------------------------------
    cls.aOutCurve = tAttr.create("outCurve", "ocv", om.MFnData.kNurbsCurve)
    tAttr.setWritable(False)
    tAttr.setStorable(False)
    tAttr.setKeyable(False)

    # outMesh:按 brushType 沿刷毛扫掠出来的实体笔刷,直接连到 mesh 的 inMesh。
    cls.aOutMesh = tAttr.create("outMesh", "omh", om.MFnData.kMesh)
    tAttr.setWritable(False)
    tAttr.setStorable(False)
    tAttr.setKeyable(False)

    # outPressure:贴地长度占毛长的比例,0-1。压得越深越大,直接拿去驱动
    # 笔迹宽度或墨色浓度。
    cls.aOutPressure = nAttr.create("outPressure", "opr",
                                    om.MFnNumericData.kDouble, 0.0)
    nAttr.setWritable(False)
    nAttr.setStorable(False)
    nAttr.setKeyable(False)

    cls.aOutContact = nAttr.create("outContact", "oct",
                                   om.MFnNumericData.kBoolean, False)
    nAttr.setWritable(False)
    nAttr.setStorable(False)
    nAttr.setKeyable(False)

    # outContactPoint:刷毛落到纸面的那一点,与 outCurve 处在同一个空间
    # (都过了 parentInverseMatrix)。可以拿去贴墨迹 locator、驱动贴图 UV。
    cls.aOutContactPoint = nAttr.create("outContactPoint", "ocp",
                                        om.MFnNumericData.k3Double)
    nAttr.setWritable(False)
    nAttr.setStorable(False)
    nAttr.setKeyable(False)

    inputs = (cls.aInMesh, cls.aControlMatrix, cls.aBristleLength,
              cls.aStiffness, cls.aEnvelope, cls.aSamples, cls.aCurveDegree,
              cls.aContactOffset, cls.aConformToSurface,
              cls.aParentInverseMatrix,
              cls.aBrushType, cls.aBrushWidth, cls.aMeshSides,
              cls.aSpreadByPressure, cls.aFlattenByPressure) \
        + tuple(cls.aWidthSegments)
    outputs = (cls.aOutCurve, cls.aOutMesh, cls.aOutPressure, cls.aOutContact,
               cls.aOutContactPoint)

    for attr in inputs + outputs:
        cls.addAttribute(attr)

    # 声明依赖:任何一个输入变化都会弄脏全部四个输出。compute 本来就是一次
    # 算齐所有输出的,分开声明没有意义,还容易漏。
    for src in inputs:
        for dst in outputs:
            cls.attributeAffects(src, dst)


# ---------------------------------------------------------------------------
# 插件入口点
# ---------------------------------------------------------------------------

def initializePlugin(mobject):
    """注册 brushTipCurve 节点。"""
    plugin = ompx.MFnPlugin(mobject, kAuthor, kPluginVersion, "Any")
    try:
        plugin.registerNode(kPluginNodeName, kPluginNodeId,
                            nodeCreator, nodeInitializer,
                            ompx.MPxNode.kDependNode)
    except Exception:
        om.MGlobal.displayError(
            "Failed to register node: {0}".format(kPluginNodeName))
        raise


def uninitializePlugin(mobject):
    """注销 brushTipCurve 节点。按 ID 注销,不按名字,避免重名插件互相踩。"""
    plugin = ompx.MFnPlugin(mobject)
    try:
        plugin.deregisterNode(kPluginNodeId)
    except Exception:
        om.MGlobal.displayError(
            "Failed to deregister node: {0}".format(kPluginNodeName))
        raise
