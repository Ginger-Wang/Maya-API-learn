# -*- coding: utf-8 -*-
"""
rbfSolver - Maya RBF（Radial Basis Function，径向基函数）插值节点。

该节点把 N 个驱动物体的三维数值拼接成一个统一的采样空间，对一组已记录的姿势
（pose）做插值，输出 M 个被驱动的三维数值以及每个姿势的混合权重。

    input[j]              -> 驱动物体 j 的实时三维数值            (double3)
    pose[i].poseInput[j]  -> 姿势 i 中驱动物体 j 记录下来的三维数值
    pose[i].poseOutput[k] -> 姿势 i 中被驱动物体 k 记录下来的三维数值
    output[k]             -> 被驱动物体 k 的插值结果三维数值
    outputWeight[i]       -> 姿势 i 的混合权重（正好落在该姿势上时为 1.0）

数学原理
    f(x) = sum_i lambda_i(x) * y_i ,  lambda(x) = M^-1 * u(x)
    M 是由所有已记录姿势输入构成的核矩阵（带正则化，可选地再增广多项式列），
    u(x) 则是实时输入相对各个中心点的核向量。
    由于 M 是对称矩阵，lambda_i 恰好就是姿势 i 的插值权重，并且满足
    lambda(x_i) = e_i，也就是说落在已记录姿势上时能被精确复现。

仅依赖 Maya API 2.0，不引入任何第三方库。语法同时兼容 Python 2.7 / 3.x
（已在 Maya 2025 上验证）。

加载方式：
    import maya.cmds as cmds
    cmds.loadPlugin(r"<this file>")
    node = cmds.createNode("rbfSolver")
"""

import math

import maya.api.OpenMaya as om


def maya_useNewAPI():
    """声明本插件使用 Maya Python API 2.0。

    Maya 在加载插件模块时会查找这个名字的模块级函数；只要它存在（无论返回什么），
    Maya 就按 API 2.0 的方式来解释插件里的注册回调与数据类型。

    参数：
        无。

    返回：
        无（函数体只有 pass，返回 None）。Maya 只检测该函数是否存在，不使用返回值。

    注意：
        函数名必须完全是 maya_useNewAPI，且必须定义在插件模块的顶层，否则 Maya 会
        退回到 API 1.0 的解释方式，导致注册失败。
    """
    pass


kPluginNodeName = "rbfSolver"
kPluginNodeId = om.MTypeId(0x0007F0A1)  # 位于 Autodesk 预留给内部自用的 ID 区段
kPluginVersion = "1.0.0"
kAuthor = "MayaRBFNode"

# 核函数枚举值，与 kernel 属性上 addField 注册的顺序一一对应
KERNEL_LINEAR = 0
KERNEL_GAUSSIAN = 1
KERNEL_EXPONENTIAL = 2
KERNEL_MULTIQUADRIC = 3
KERNEL_INV_MULTIQUADRIC = 4
KERNEL_THINPLATE = 5
KERNEL_CUBIC = 6
KERNEL_QUINTIC = 7

EPS = 1e-12


# ---------------------------------------------------------------------------
# 数学辅助函数（纯 Python 实现；姿势数量通常很小，无需引入矩阵库）
# ---------------------------------------------------------------------------

def kernel_value(kernel, r, sigma):
    """计算径向基函数 phi(r)，其中 sigma 为支撑半径（尺度参数）。

    参数：
        kernel: 核函数类型，取值为上面的 KERNEL_* 常量之一。
        r: 非负的欧氏距离，即查询点到某个中心点的距离。
        sigma: 支撑半径。距离先被它归一化成 x = r / sigma，这样同一套核公式
            就能适应不同尺度的采样空间。

    返回：
        float，核函数在该距离上的取值。

    各核函数的特性：
        linear (x)                  - 一阶连续，外推平缓，最不容易产生过冲，
                                      但在中心点附近不够“尖锐”。
        gaussian (exp(-x^2))        - 局部性最强，离中心稍远即迅速衰减为 0，
                                      影响范围完全由 sigma 控制；sigma 过小会
                                      使核矩阵接近单位阵、姿势之间失去过渡，
                                      sigma 过大则矩阵接近全 1、趋于病态。
        exponential (exp(-x))       - 同样是局部核，但衰减比高斯慢，在原点处
                                      不可导，过渡更“硬”一些。
        multiQuadratic              - sqrt(1 + x^2)，随距离单调递增的全局核，
                                      外推能力强，通常需要配合多项式项使用。
        inverseMultiQuadratic       - 1 / sqrt(1 + x^2)，全局核但单调递减，
                                      比高斯衰减得更缓，过渡更柔和。
        thinPlate (x^2 * log x)     - 薄板样条，最小化弯曲能量，形变过渡最自然；
                                      x -> 0 时 log x 发散，因此在 x < EPS 处
                                      直接返回 0.0（该点的数学极限也是 0）。
        cubic (x^3)                 - 多项式条件正定核，光滑度高于 linear。
        quintic (x^5)               - 比 cubic 更光滑，但外推时增长更快、
                                      更容易出现过冲。

    注意：
        sigma 被强制抬到至少 EPS，避免除零；未识别的 kernel 值退化为 linear，
        保证任何情况下都能返回一个有意义的数值而不是抛异常。
    """
    if sigma < EPS:
        sigma = EPS
    x = r / sigma

    if kernel == KERNEL_LINEAR:
        return x
    if kernel == KERNEL_GAUSSIAN:
        return math.exp(-x * x)
    if kernel == KERNEL_EXPONENTIAL:
        return math.exp(-x)
    if kernel == KERNEL_MULTIQUADRIC:
        return math.sqrt(1.0 + x * x)
    if kernel == KERNEL_INV_MULTIQUADRIC:
        return 1.0 / math.sqrt(1.0 + x * x)
    if kernel == KERNEL_THINPLATE:
        # x -> 0 时 x^2 * log(x) 的极限为 0，但直接计算会因 log(0) 报错
        if x < EPS:
            return 0.0
        return x * x * math.log(x)
    if kernel == KERNEL_CUBIC:
        return x * x * x
    if kernel == KERNEL_QUINTIC:
        return x * x * x * x * x
    # 兜底：枚举值异常时按 linear 处理
    return x


def distance(a, b):
    """计算两个等长一维向量之间的欧氏距离。

    参数：
        a: 序列类型的向量（列表或元组），元素为 float。
        b: 与 a 等长的向量。

    返回：
        float，两个向量之间的欧氏距离 sqrt(sum((a_i - b_i)^2))。

    注意：
        为了性能这里不检查长度是否一致，遍历以 a 的长度为准；调用方需自行保证
        两个向量来自同一次 flatten，维度天然对齐。
    """
    total = 0.0
    for i in range(len(a)):
        d = a[i] - b[i]
        total += d * d
    return math.sqrt(total)


def invert_matrix(mat):
    """用带部分主元（partial pivoting）的高斯-约当消元法求矩阵的逆。

    参数：
        mat: n x n 的方阵，用嵌套列表表示（每个元素是一行的列表）。

    返回：
        n x n 的逆矩阵（嵌套列表）；若矩阵奇异或数值上过于接近奇异，返回 None。
        空矩阵输入时返回空列表。

    算法说明：
        1. 先把原矩阵右侧拼接上同阶单位阵，构成 n x 2n 的增广矩阵。
        2. 逐列消元：对第 col 列，在第 col 行及其下方寻找绝对值最大的元素作为
           主元并交换到当前行——这就是“部分主元”。它不改变解，但能避免用一个
           很小的数去做除数，从而抑制舍入误差被放大，是纯 Python 浮点实现里
           最关键的数值稳定手段。
        3. 若最大主元的绝对值仍小于 1e-11，说明该列已无法找到有效主元，矩阵
           秩亏，直接返回 None 交由调用方走退化处理分支。
        4. 主元行整体除以主元使对角线归一，再用它把同列其余各行消成 0。
        5. 全部列处理完后，增广矩阵左半部分变成单位阵，右半部分即为逆矩阵。

    实现细节：
        内层循环从 j = col 开始而不是 0，因为第 col 列左侧的元素在之前的迭代中
        已经被消为 0（或已归一），重复计算没有意义。factor 恰为 0.0 时跳过整行，
        省掉一轮无效的浮点乘减。
    """
    n = len(mat)
    if n == 0:
        return []

    # 在右侧拼接单位阵，形成 n x 2n 的增广矩阵
    aug = []
    for i in range(n):
        row = list(mat[i]) + [1.0 if i == j else 0.0 for j in range(n)]
        aug.append(row)

    for col in range(n):
        # 部分主元：在当前列的对角线及以下找绝对值最大的元素做主元
        pivot_row = col
        pivot_val = abs(aug[col][col])
        for r in range(col + 1, n):
            v = abs(aug[r][col])
            if v > pivot_val:
                pivot_val = v
                pivot_row = r
        # 主元过小视为秩亏，继续消元只会得到被舍入误差主导的垃圾结果
        if pivot_val < 1e-11:
            return None
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]

        # 主元行归一化：整行乘以主元的倒数（乘法比逐个做除法更快）
        pivot = aug[col][col]
        inv_pivot = 1.0 / pivot
        row_c = aug[col]
        for j in range(col, 2 * n):
            row_c[j] *= inv_pivot

        # 用归一化后的主元行消去其余各行在该列上的分量
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor == 0.0:
                continue
            row_r = aug[r]
            for j in range(col, 2 * n):
                row_r[j] -= factor * row_c[j]

    # 左半部分此时已是单位阵，右半部分就是所求的逆矩阵
    return [row[n:] for row in aug]


def independent_poly_columns(centers):
    """挑选出线性多项式项中真正线性无关的那些列。

    参数：
        centers: 采样中心点列表，每个中心点是一个等长的一维 float 向量
            （即展平后的姿势输入）。

    返回：
        列表，每个元素描述一列可用的多项式列：-1 表示常数项那一列，其余为非负
        整数，表示采样向量中对应的维度索引。空输入返回空列表。

    为什么需要这一步：
        RBF 加上线性多项式项可以保证对线性趋势的精确复现、改善外推表现。但多项式
        块的列是 [1, x_0, x_1, ... x_d]，一旦所有采样点落在同一个平面或同一条
        直线上——比如一圈定位器全部位于 y = 0、或者只用两个轴的 pose reader——
        某些维度列就会与常数列（或彼此）线性相关。此时增广后的核矩阵必然奇异，
        而且这种奇异来自多项式块本身的秩亏：往核矩阵的对角线上加 ridge 正则项
        只能改善核块，对多项式块毫无作用，加多大都救不回来。
        因此这里用改进版 Gram-Schmidt 正交化逐列检验：把每一列减去它在已保留列
        张成空间上的投影，若剩余残差的模相对原列的模小到可以忽略，就说明这一列
        是冗余的，直接丢弃；保留下来的列构成一组线性无关的多项式基，既避免了
        奇异，又尽可能保留了多项式项带来的好处。

    实现细节：
        scale 是原列的模，先用它过滤掉整列几乎全为 0 的维度（该维度不携带任何
        信息）。判据 norm <= 1e-7 * scale 采用相对阈值而非绝对阈值，这样结论
        不随场景单位（厘米/米）缩放而改变。basis 中保存的是已单位化的正交向量，
        故投影系数直接取点积即可。
    """
    n = len(centers)
    if n == 0:
        return []
    dim = len(centers[0])

    kept = []
    basis = []
    # -1 代表常数列，其后依次是各个采样维度列
    for spec in [-1] + list(range(dim)):
        vec = [1.0] * n if spec < 0 else [c[spec] for c in centers]
        scale = math.sqrt(sum(v * v for v in vec))
        if scale < EPS:
            continue                      # 整列全为零的维度不携带任何信息

        # Gram-Schmidt：减去该列在已保留正交基上的投影，只留下新增的分量
        residual = list(vec)
        for b in basis:
            dot = sum(residual[i] * b[i] for i in range(n))
            for i in range(n):
                residual[i] -= dot * b[i]

        norm = math.sqrt(sum(v * v for v in residual))
        if norm <= 1e-7 * scale:
            continue                      # 与已保留的列线性相关，丢弃

        basis.append([v / norm for v in residual])
        kept.append(spec)

    return kept


def auto_sigma(centers):
    """估算自动支撑半径：所有采样点最近邻距离的平均值。

    参数：
        centers: 采样中心点列表，每个中心点是展平后的一维 float 向量。

    返回：
        float，平均最近邻距离；采样点少于 2 个、或所有点几乎重合导致无有效距离
        时返回 1.0 作为安全默认值。

    为什么这样取：
        核函数的表现高度依赖 sigma 与采样点间距的相对关系。用最近邻距离的均值
        作为基准，可以让核的影响范围自动适配姿势的疏密程度，无论场景单位是
        厘米还是米、驱动值是角度还是位移，都不必手动调参。radius 属性随后会
        作为倍率乘在这个基准上。

    注意：
        实现是 O(n^2) 的双重循环，但姿势数量通常只有几十个，且结果会被求解缓存
        复用，开销可以忽略。小于 EPS 的最近邻距离（重复姿势）会被跳过，避免把
        平均值拉向 0。
    """
    n = len(centers)
    if n < 2:
        return 1.0
    total = 0.0
    count = 0
    for i in range(n):
        best = None
        for j in range(n):
            if i == j:
                continue
            d = distance(centers[i], centers[j])
            if best is None or d < best:
                best = d
        if best is not None and best > EPS:
            total += best
            count += 1
    if count == 0:
        return 1.0
    return total / count


# ---------------------------------------------------------------------------
# 节点本体
# ---------------------------------------------------------------------------

class RBFSolverNode(om.MPxNode):
    """RBF 插值求解节点。

    以类属性的形式持有全部 MObject 属性句柄（在 initialize() 中创建），以实例
    属性的形式持有一份求解缓存，使得只要采样集合与求解设置不变，就无需在每次
    compute() 里重复做矩阵求逆。
    """

    # 属性句柄，全部在 initialize() 中被赋值
    aInput = None
    aInputScale = None
    aPose = None
    aPoseInput = None
    aPoseOutput = None
    aKernel = None
    aRadius = None
    aAutoRadius = None
    aRegularization = None
    aUseLinearTerm = None
    aNormalizeWeights = None
    aClampWeights = None
    aEnvelope = None
    aOutput = None
    aOutputWeight = None

    def __init__(self):
        """构造节点实例并初始化求解缓存。

        参数：
            无。Maya 通过 creator() 无参构造本类。

        返回：
            无。

        说明：
            必须显式调用基类 MPxNode 的 __init__，否则 C++ 侧的代理对象不会被
            正确建立。随后初始化的几个下划线开头的成员构成一份“求解缓存”：只有
            当 _cache_key 发生变化（姿势集合或求解设置改变）时，compute() 才会
            重新构建并求逆核矩阵，其余情况下直接复用 _minv。

        注意：
            每个节点实例各自持有一份缓存，互不干扰；节点被删除时缓存随实例一同
            释放，无需手动清理。
        """
        om.MPxNode.__init__(self)
        # 求解缓存
        self._cache_key = None
        self._minv = None          # （增广后）核矩阵的逆
        self._centers = []         # 已缩放并展平的姿势输入向量
        self._sigma = 1.0
        self._poly_cols = []       # 实际启用的多项式列，参见 _solve
        self._kernel = KERNEL_GAUSSIAN

    # -- 实例创建 ------------------------------------------------------------
    @staticmethod
    def creator():
        """节点创建回调，供 MFnPlugin.registerNode 使用。

        参数：
            无。

        返回：
            一个全新的 RBFSolverNode 实例。

        注意：
            Maya 每次实例化该节点类型时都会调用此函数，因此必须返回新对象而不是
            共享的单例，否则多个节点会共用同一份求解缓存。
        """
        return RBFSolverNode()

    # -- 属性定义 ------------------------------------------------------------
    @staticmethod
    def initialize():
        """创建节点的全部属性并建立属性间的依赖关系。

        参数：
            无。

        返回：
            无。

        说明：
            Maya 在注册节点类型时只调用一次本函数，创建出的属性由该节点类型的
            所有实例共享，因此句柄存放在类属性上。函数依次完成三件事：
            1. 用 MFnNumericAttribute / MFnCompoundAttribute / MFnEnumAttribute
               创建属性；
            2. 用 addAttribute 把顶层属性加入节点（复合属性的子属性由 addChild
               负责，不能再单独 addAttribute）；
            3. 用 attributeAffects 声明“哪些输入会弄脏哪些输出”，这是 Maya 依赖
               图触发 compute() 的依据。

        注意：
            设置修饰符（array / keyable / storable 等）时使用的是刚刚 create 出来
            的那个函数集对象，因此顺序不能打乱——必须紧跟在对应的 create 之后。
            输出属性必须开启 usesArrayDataBuilder，否则无法通过
            MArrayDataBuilder 写入数组元素。
        """
        nAttr = om.MFnNumericAttribute()
        cAttr = om.MFnCompoundAttribute()
        eAttr = om.MFnEnumAttribute()

        cls = RBFSolverNode

        # ---- 实时驱动输入 ------------------------------------------
        # input：驱动物体的实时三维数值数组，每个 logical index 对应一个驱动物体
        cls.aInput = nAttr.create("input", "in", om.MFnNumericData.k3Double)
        nAttr.array = True
        nAttr.keyable = True
        nAttr.storable = True
        nAttr.readable = False
        # 断开连接时删除该数组元素，避免残留的陈旧元素继续参与求解
        nAttr.disconnectBehavior = om.MFnAttribute.kDelete

        # inputScale：每个驱动维度的权重缩放，用于平衡量纲差异很大的驱动源
        cls.aInputScale = nAttr.create(
            "inputScale", "insc", om.MFnNumericData.kDouble, 1.0)
        nAttr.array = True
        nAttr.keyable = True
        nAttr.storable = True
        nAttr.readable = False

        # ---- 已记录的姿势 ----------------------------------------------
        # poseInput：该姿势下各驱动物体记录的三维数值，与 input 的 logical index 对齐
        cls.aPoseInput = nAttr.create(
            "poseInput", "pin", om.MFnNumericData.k3Double)
        nAttr.array = True
        nAttr.storable = True
        nAttr.keyable = True
        nAttr.readable = False

        # poseOutput：该姿势下各被驱动物体记录的三维数值，决定 output 的取值
        cls.aPoseOutput = nAttr.create(
            "poseOutput", "pot", om.MFnNumericData.k3Double)
        nAttr.array = True
        nAttr.storable = True
        nAttr.keyable = True
        nAttr.readable = False

        # pose：把一组 poseInput / poseOutput 打包成一个姿势的复合数组属性
        cls.aPose = cAttr.create("pose", "pos")
        cAttr.array = True
        cAttr.storable = True
        cAttr.addChild(cls.aPoseInput)
        cAttr.addChild(cls.aPoseOutput)

        # ---- 求解器设置 ----------------------------------------------
        # kernel：选择使用哪一种径向基核函数
        cls.aKernel = eAttr.create("kernel", "krn", KERNEL_GAUSSIAN)
        eAttr.addField("linear", KERNEL_LINEAR)
        eAttr.addField("gaussian", KERNEL_GAUSSIAN)
        eAttr.addField("exponential", KERNEL_EXPONENTIAL)
        eAttr.addField("multiQuadratic", KERNEL_MULTIQUADRIC)
        eAttr.addField("inverseMultiQuadratic", KERNEL_INV_MULTIQUADRIC)
        eAttr.addField("thinPlate", KERNEL_THINPLATE)
        eAttr.addField("cubic", KERNEL_CUBIC)
        eAttr.addField("quintic", KERNEL_QUINTIC)
        eAttr.keyable = True
        eAttr.storable = True

        # radius：核的支撑半径；autoRadius 打开时它退化为自动半径的倍率
        cls.aRadius = nAttr.create(
            "radius", "rad", om.MFnNumericData.kDouble, 1.0)
        nAttr.keyable = True
        nAttr.storable = True
        nAttr.setMin(0.001)
        nAttr.setSoftMax(5.0)

        # autoRadius：是否按姿势的平均最近邻距离自动推算支撑半径
        cls.aAutoRadius = nAttr.create(
            "autoRadius", "arad", om.MFnNumericData.kBoolean, True)
        nAttr.keyable = True
        nAttr.storable = True

        # regularization：加在核矩阵对角线上的 ridge 项，越大插值越平滑、越稳定
        cls.aRegularization = nAttr.create(
            "regularization", "reg", om.MFnNumericData.kDouble, 0.0)
        nAttr.keyable = True
        nAttr.storable = True
        nAttr.setMin(0.0)
        nAttr.setSoftMax(1.0)

        # useLinearTerm：是否为核矩阵增广线性多项式项，改善外推与线性趋势的还原
        cls.aUseLinearTerm = nAttr.create(
            "useLinearTerm", "ult", om.MFnNumericData.kBoolean, True)
        nAttr.keyable = True
        nAttr.storable = True

        # normalizeWeights：是否把权重归一化到总和为 1（形成凸组合）
        cls.aNormalizeWeights = nAttr.create(
            "normalizeWeights", "nwt", om.MFnNumericData.kBoolean, False)
        nAttr.keyable = True
        nAttr.storable = True

        # clampWeights：是否把权重限制到 [0, 1]，抑制过冲和负权重
        cls.aClampWeights = nAttr.create(
            "clampWeights", "cwt", om.MFnNumericData.kBoolean, False)
        nAttr.keyable = True
        nAttr.storable = True

        # envelope：整体强度系数，0 表示完全关闭该节点的影响
        cls.aEnvelope = nAttr.create(
            "envelope", "env", om.MFnNumericData.kDouble, 1.0)
        nAttr.keyable = True
        nAttr.storable = True
        nAttr.setMin(0.0)
        nAttr.setMax(1.0)

        # ---- 输出 --------------------------------------------------------
        # output：插值得到的被驱动三维数值数组，索引与 poseOutput 的 logical index 一致
        cls.aOutput = nAttr.create("output", "out", om.MFnNumericData.k3Double)
        nAttr.array = True
        nAttr.usesArrayDataBuilder = True
        nAttr.writable = False
        nAttr.storable = False
        nAttr.keyable = False

        # outputWeight：每个姿势的混合权重，索引与 pose 的 logical index 一致
        cls.aOutputWeight = nAttr.create(
            "outputWeight", "owt", om.MFnNumericData.kDouble, 0.0)
        nAttr.array = True
        nAttr.usesArrayDataBuilder = True
        nAttr.writable = False
        nAttr.storable = False
        nAttr.keyable = False

        # 注册顶层属性；aPoseInput / aPoseOutput 已作为 aPose 的子属性加入，不再单独添加
        for attr in (cls.aInput, cls.aInputScale, cls.aPose, cls.aKernel,
                     cls.aRadius, cls.aAutoRadius, cls.aRegularization,
                     cls.aUseLinearTerm, cls.aNormalizeWeights,
                     cls.aClampWeights, cls.aEnvelope, cls.aOutput,
                     cls.aOutputWeight):
            om.MPxNode.addAttribute(attr)

        # 声明依赖：任意一个输入变化都会同时弄脏两个输出，触发重新 compute
        drivers = (cls.aInput, cls.aInputScale, cls.aPose, cls.aPoseInput,
                   cls.aPoseOutput, cls.aKernel, cls.aRadius, cls.aAutoRadius,
                   cls.aRegularization, cls.aUseLinearTerm,
                   cls.aNormalizeWeights, cls.aClampWeights, cls.aEnvelope)
        for src in drivers:
            om.MPxNode.attributeAffects(src, cls.aOutput)
            om.MPxNode.attributeAffects(src, cls.aOutputWeight)

    # -- 内部辅助 ------------------------------------------------------------
    @staticmethod
    def _root_attribute(plug):
        """沿着元素/子属性层级向上回溯，取得 plug 所属的根属性。

        参数：
            plug: 传入 compute() 的 MPlug，可能是数组元素（如 output[3]）或
                复合属性的子 plug（如 output[3].outputX）。

        返回：
            MObject，该 plug 最终归属的根属性；用于判断本次 compute 请求的到底
            是 output 还是 outputWeight。

        说明：
            Maya 可能只请求某个数组元素甚至某个分量，直接拿 plug.attribute() 得到
            的会是子属性而非根属性，比较时就会漏判。isChild 表示它是复合属性的
            子项，用 parent() 上溯；isElement 表示它是数组的一个元素，用 array()
            上溯。

        注意：
            循环上限固定为 8 层，是为了防止异常嵌套导致死循环；真实场景中
            output[i].outputX 这类结构最多只需要两三层。
        """
        p = plug
        # 防止病态嵌套造成无限循环，限制回溯层数
        for _ in range(8):
            if p.isChild:
                p = p.parent()
            elif p.isElement:
                p = p.array()
            else:
                break
        return p.attribute()

    @staticmethod
    def _read_double3_array(array_handle):
        """把一个 double3 数组属性读成 {logicalIndex: (x, y, z)} 字典。

        参数：
            array_handle: 指向 double3 数组属性的 MArrayDataHandle。

        返回：
            dict，键为 logical index，值为 (x, y, z) 三元组。

        说明：
            必须用 jumpToPhysicalElement 按物理下标遍历，再用
            elementLogicalIndex() 取回逻辑索引：数组元素被删除后物理下标是连续
            的，而逻辑索引会出现空洞，两者并不相等。后续所有对齐逻辑都以逻辑
            索引为准，因此这里以字典而非列表返回。
        """
        result = {}
        for i in range(len(array_handle)):
            array_handle.jumpToPhysicalElement(i)
            idx = array_handle.elementLogicalIndex()
            result[idx] = tuple(array_handle.inputValue().asDouble3())
        return result

    @staticmethod
    def _read_double_array(array_handle):
        """把一个 double 数组属性读成 {logicalIndex: value} 字典。

        参数：
            array_handle: 指向 double 数组属性的 MArrayDataHandle。

        返回：
            dict，键为 logical index，值为 float。

        说明：
            与 _read_double3_array 同理，用物理下标遍历、用逻辑索引作键，以正确
            处理存在空洞的稀疏数组（例如 inputScale 只设置了个别索引）。
        """
        result = {}
        for i in range(len(array_handle)):
            array_handle.jumpToPhysicalElement(i)
            idx = array_handle.elementLogicalIndex()
            result[idx] = array_handle.inputValue().asDouble()
        return result

    def _read_poses(self, data):
        """读取 pose 复合数组属性中记录的全部姿势。

        参数：
            data: compute() 传入的 MDataBlock。

        返回：
            三元组 (poseIndices, poseInputs, poseOutputs)：
                poseIndices - 各姿势的 logical index 列表，用于回写 outputWeight；
                poseInputs  - 与 poseIndices 一一对应的 {logicalIndex: double3} 字典列表，
                              记录每个姿势下各驱动物体的数值；
                poseOutputs - 同上，记录每个姿势下各被驱动物体的数值。
            三个列表按物理遍历顺序对齐，长度相同。

        说明：
            elem.child() 取到的是复合元素内部的子句柄，由于子属性本身也是数组，
            需要再包一层 om.MArrayDataHandle 才能按数组方式遍历。
        """
        pose_indices = []
        pose_inputs = []
        pose_outputs = []

        pose_array = data.inputArrayValue(self.aPose)
        for i in range(len(pose_array)):
            pose_array.jumpToPhysicalElement(i)
            logical = pose_array.elementLogicalIndex()
            elem = pose_array.inputValue()

            # 复合元素的子句柄仍是数组，需要再包一层 MArrayDataHandle
            in_handle = om.MArrayDataHandle(elem.child(self.aPoseInput))
            out_handle = om.MArrayDataHandle(elem.child(self.aPoseOutput))

            pose_indices.append(logical)
            pose_inputs.append(self._read_double3_array(in_handle))
            pose_outputs.append(self._read_double3_array(out_handle))

        return pose_indices, pose_inputs, pose_outputs

    @staticmethod
    def _build_matrix(centers, kernel, sigma, ridge, poly_cols):
        """构建核矩阵，并按需增广多项式列。

        参数：
            centers: 采样中心点列表，每项为展平后的一维 float 向量。
            kernel: 核函数类型（KERNEL_* 常量）。
            sigma: 核的支撑半径。
            ridge: 加在对角线上的正则项，用于抑制病态、平滑插值结果。
            poly_cols: 需要增广的多项式列描述，每项 -1 表示常数列，非负整数表示
                采样向量中的维度索引；传空列表则只构建纯核矩阵。

        返回：
            (n + len(poly_cols)) 阶方阵（嵌套列表）。整体呈分块形式：
                [ K   P ]
                [ P^T 0 ]
            其中 K 是 n x n 的核矩阵，P 是多项式块，右下角为零块。

        说明：
            核矩阵天然对称（phi 只依赖距离），所以只计算上三角并镜像到下三角，
            省掉一半的核函数求值。对角线统一为 phi(0) + ridge：phi(0) 对高斯核
            是 1，对 thinPlate / cubic 等是 0，加上 ridge 后即构成标准的正则化
            核矩阵。多项式块同样对称地写入行与列，以保持整个矩阵对称——这正是
            后续 lambda = M^-1 * u 能直接解释成插值权重的前提。
        """
        n = len(centers)
        size = n + len(poly_cols)
        mat = [[0.0] * size for _ in range(size)]

        # 对角线为 phi(0) 加上 ridge 正则项
        diagonal = kernel_value(kernel, 0.0, sigma) + ridge
        for i in range(n):
            ci = centers[i]
            mat[i][i] = diagonal
            # 利用对称性只算上三角，再镜像写入下三角
            for j in range(i + 1, n):
                v = kernel_value(kernel, distance(ci, centers[j]), sigma)
                mat[i][j] = v
                mat[j][i] = v

        # 增广多项式块：同时写入右侧列和底部行，保持矩阵对称
        for t, spec in enumerate(poly_cols):
            col = n + t
            for i in range(n):
                v = 1.0 if spec < 0 else centers[i][spec]
                mat[i][col] = v
                mat[col][i] = v

        return mat

    def _solve(self, centers, kernel, sigma, regularization, use_poly):
        """构建并求逆核矩阵，把结果缓存到 self._minv 与 self._poly_cols。

        参数：
            centers: 采样中心点列表（展平后的姿势输入）。
            kernel: 核函数类型。
            sigma: 核的支撑半径。
            regularization: ridge 正则项强度。
            use_poly: 是否尝试增广线性多项式项。

        返回：
            无。结果写入两个实例成员：
                self._minv      - 逆矩阵；彻底失败时为 None（此时 _weights 全返回 0）；
                self._poly_cols - 最终真正生效的多项式列，必须与 _minv 的阶数保持
                                  一致，否则 _weights 构建的向量 u 长度会对不上。

        两层退化兜底策略：
            第一层——多项式列的取舍。先用 independent_poly_columns 过滤掉线性相关
            的列，再检查 unisolvency 条件（多项式项数必须少于采样点数，即
            len(poly_cols) + 1 > n 时放弃多项式）。随后依次尝试 [带多项式, 不带
            多项式] 两种矩阵：因为 ridge 只作用在核块的对角线上，对秩亏的多项式
            块毫无帮助，一旦增广矩阵仍然奇异，唯一的出路就是整个丢掉多项式项。
            第二层——递增 ridge。若不带多项式仍然求逆失败（典型原因是存在完全
            重复的姿势，导致核矩阵出现相同的两行），就从 max(regularization, 1e-8)
            起步，每次把 ridge 乘以 10，最多尝试 6 次。ridge 逐步增大会让矩阵越来
            越接近对角占优，几乎必然可逆；代价是插值变得平滑、不再严格穿过每个
            姿势，但这远好于直接输出全零。
        """
        n = len(centers)

        poly_cols = independent_poly_columns(centers) if use_poly else []
        # unisolvency 条件：采样点数必须多于多项式项数，否则多项式块必定秩亏
        if len(poly_cols) + 1 > n:
            poly_cols = []

        # 先试带多项式项的矩阵，失败再试不带的——ridge 只加在核块对角线上，
        # 救不了秩亏的多项式块，丢弃多项式项是唯一出路
        minv = None
        for cols in ([poly_cols, []] if poly_cols else [[]]):
            minv = invert_matrix(
                self._build_matrix(centers, kernel, sigma, regularization, cols))
            if minv is not None:
                poly_cols = cols
                break

        # 仍然退化（例如存在完全重复的姿势）——用逐步放大的 ridge 强行拉开
        if minv is None:
            poly_cols = []
            ridge = max(regularization, 1e-8)
            for _ in range(6):
                minv = invert_matrix(
                    self._build_matrix(centers, kernel, sigma, ridge, []))
                if minv is not None:
                    break
                ridge *= 10.0

        self._minv = minv
        # 求逆失败时必须把多项式列一并清空，保证与 _minv 的实际阶数一致
        self._poly_cols = poly_cols if minv is not None else []

    def _weights(self, query):
        """计算 lambda(query)：查询点对应的每个已记录姿势的混合权重。

        参数：
            query: 当前实时输入展平并缩放后的一维 float 向量，维度与 _centers
                中的各个中心点一致。

        返回：
            长度为姿势数量 n 的 float 列表，第 i 项即姿势 i 的混合权重。若尚无
            姿势或矩阵求逆失败（_minv 为 None），返回全 0 列表。

        为什么 lambda = M^-1 * u 就是混合权重：
            标准 RBF 插值先解 M * c = y 得到系数 c，再用 f(x) = u(x)^T * c 求值。
            把两式合并得 f(x) = u(x)^T * M^-1 * y。由于 M 是对称矩阵，M^-1 也对称，
            于是 u^T * M^-1 = (M^-1 * u)^T，记 lambda = M^-1 * u 便有
            f(x) = lambda^T * y = sum_i lambda_i * y_i。也就是说输出恰好是各姿势
            记录输出值的线性组合，而 lambda_i 就是姿势 i 的权重。
            进一步地，当 query 正好等于第 i 个中心点时 u 就是 M 的第 i 列，此时
            M^-1 * u = e_i，即该姿势权重为 1、其余为 0——这保证了已记录姿势能被
            精确复现。这一性质也让 lambda 可以直接作为 outputWeight 输出，用来
            驱动 blendShape 目标体等下游需要“每个姿势一个权重”的场景。

        实现细节：
            向量 u 的长度是 n + 多项式列数，前 n 项是核值，后面是多项式项（-1 对应
            常数 1.0，其余取 query 在该维度上的分量）。求积时只遍历 _minv 的前 n 行
            即可：后面几行对应的是多项式方程的约束，不属于姿势权重。
        """
        n = len(self._centers)
        if n == 0 or self._minv is None:
            return [0.0] * n

        # u 的前 n 项是查询点到各中心的核值，其后是多项式项
        size = n + len(self._poly_cols)
        u = [0.0] * size
        for i in range(n):
            u[i] = kernel_value(
                self._kernel, distance(query, self._centers[i]), self._sigma)
        for t, spec in enumerate(self._poly_cols):
            u[n + t] = 1.0 if spec < 0 else query[spec]

        # lambda = M^-1 * u；只取前 n 行，多余的行属于多项式约束而非姿势权重
        weights = []
        for i in range(n):
            row = self._minv[i]
            acc = 0.0
            for j in range(size):
                acc += row[j] * u[j]
            weights.append(acc)
        return weights

    # -- 求值入口 ------------------------------------------------------------
    def compute(self, plug, data):
        """依赖图求值入口：由实时输入与已记录姿势算出插值输出与混合权重。

        参数：
            plug: Maya 请求求值的 MPlug，可能是 output / outputWeight 本身，也
                可能是它们的某个数组元素或分量。
            data: MDataBlock，用于读取输入属性、写入输出属性。

        返回：
            self 表示本次求值已由该函数处理；返回 None 表示请求的 plug 与本节点
            无关，交回 Maya 走默认处理。

        处理流程：
            1. 判断根属性是否为两个输出之一，不是则立即返回 None；
            2. 读取全部求解设置与采样数据；
            3. 按 logical index 对齐并展平驱动/被驱动数值；
            4. 必要时重新求解核矩阵（命中缓存则跳过）；
            5. 计算权重、施加 clamp / normalize / envelope；
            6. 用 MArrayDataBuilder 写回两个输出数组并标记为 clean。

        注意：
            无论是 output 还是 outputWeight 被请求，都会走完整套计算并同时写入
            两个输出，因为它们共享同一次求解结果，分开算反而浪费。
        """
        root = self._root_attribute(plug)
        if root != self.aOutput and root != self.aOutputWeight:
            return None

        # ---- 求解设置 ------------------------------------------------------
        kernel = data.inputValue(self.aKernel).asShort()
        radius = data.inputValue(self.aRadius).asDouble()
        auto_radius = data.inputValue(self.aAutoRadius).asBool()
        regularization = data.inputValue(self.aRegularization).asDouble()
        use_poly = data.inputValue(self.aUseLinearTerm).asBool()
        normalize = data.inputValue(self.aNormalizeWeights).asBool()
        clamp = data.inputValue(self.aClampWeights).asBool()
        envelope = data.inputValue(self.aEnvelope).asDouble()

        # ---- 采样数据 --------------------------------------------------------
        pose_indices, pose_inputs, pose_outputs = self._read_poses(data)
        live_input = self._read_double3_array(data.inputArrayValue(self.aInput))
        scales = self._read_double_array(data.inputArrayValue(self.aInputScale))

        # 驱动维度的排列顺序：实时输入与所有姿势输入的 logical index 取并集后排序。
        # 取并集而不是只用实时输入，是为了让某个驱动物体暂时未连接时，姿势里记录的
        # 该维度依然占据固定的位置，保证 centers 与 query 的维度始终一一对齐。
        in_indices = set(live_input.keys())
        for d in pose_inputs:
            in_indices.update(d.keys())
        in_indices = sorted(in_indices)

        # 被驱动维度的排列顺序：所有姿势输出的 logical index 取并集后排序
        out_indices = set()
        for d in pose_outputs:
            out_indices.update(d.keys())
        out_indices = sorted(out_indices)

        def flatten(values):
            """把 {logicalIndex: double3} 字典展平成一维向量。

            参数：
                values: 待展平的字典，键为 logical index，值为 (x, y, z)。

            返回：
                长度为 len(in_indices) * 3 的 float 列表，按 in_indices 的顺序
                依次排列每个驱动维度的 x、y、z 分量，并乘上对应的 inputScale。

            注意：
                字典中缺失的索引按 (0.0, 0.0, 0.0) 填充，缺失的缩放系数按 1.0
                处理。这条规则让实时输入与各姿势输入即使元素集合不同，也能得到
                长度一致、位置对应的向量，从而可以直接参与距离计算。
            """
            vec = []
            for idx in in_indices:
                s = scales.get(idx, 1.0)
                v = values.get(idx, (0.0, 0.0, 0.0))
                vec.append(v[0] * s)
                vec.append(v[1] * s)
                vec.append(v[2] * s)
            return vec

        centers = [flatten(d) for d in pose_inputs]
        query = flatten(live_input)

        # 每个姿势的输出值按 out_indices 的顺序摊平成列表，缺失项同样补 (0, 0, 0)
        values = []
        for d in pose_outputs:
            values.append([d.get(idx, (0.0, 0.0, 0.0)) for idx in out_indices])

        # ---- 仅在采样集合或求解设置发生变化时才重新求解 ---------
        sigma = radius
        if auto_radius:
            # 自动模式下 radius 变成自动半径的倍率；max 防止倍率为 0 导致 sigma 归零
            sigma = auto_sigma(centers) * max(radius, EPS)

        # 缓存键涵盖所有会影响矩阵内容的量：核类型、sigma、正则项、是否用多项式，
        # 以及全部中心点坐标。中心点转成元组是为了可哈希且可按值比较——只要姿势
        # 数值没变，即便驱动物体在实时移动，也能命中缓存跳过昂贵的矩阵求逆。
        cache_key = (kernel, sigma, regularization, use_poly,
                     tuple(tuple(c) for c in centers))
        if cache_key != self._cache_key:
            self._kernel = kernel
            self._sigma = sigma
            self._centers = centers
            if centers:
                self._solve(centers, kernel, sigma, regularization, use_poly)
            else:
                # 没有任何姿势时清空缓存的矩阵，避免沿用上一次的陈旧结果
                self._minv = None
                self._poly_cols = []
            self._cache_key = cache_key

        # ---- 求值 --------------------------------------------------------
        n = len(centers)
        if n == 0:
            weights = []
        elif n == 1:
            # 只有一个姿势时无需求解，权重恒为 1，输出即该姿势的记录值
            weights = [1.0]
        else:
            weights = self._weights(query)

        # clamp 必须在 normalize 之前执行：先截断掉负权重与过冲，再归一化，
        # 才能得到一组真正的凸组合系数
        if clamp:
            weights = [0.0 if w < 0.0 else (1.0 if w > 1.0 else w)
                       for w in weights]
        if normalize:
            total = sum(weights)
            # 总和接近 0 时归一化会放大噪声，此时保持原始权重不变
            if abs(total) > EPS:
                weights = [w / total for w in weights]

        # 用权重线性混合各姿势记录的输出值；权重为 0 的姿势直接跳过
        results = []
        for k in range(len(out_indices)):
            x = y = z = 0.0
            for i in range(n):
                w = weights[i]
                if w == 0.0:
                    continue
                v = values[i][k]
                x += w * v[0]
                y += w * v[1]
                z += w * v[2]
            results.append((x * envelope, y * envelope, z * envelope))

        # 输出值在上面已经乘过 envelope，这里只需再补偿到权重输出上，
        # 使 outputWeight 与 output 的强度保持一致
        if envelope != 1.0:
            weights = [w * envelope for w in weights]

        # ---- 写出结果 ----------------------------------------------------
        # output 用被驱动物体的 logical index，outputWeight 用姿势的 logical index
        self._write_double3_array(data, self.aOutput, out_indices, results)
        self._write_double_array(data, self.aOutputWeight, pose_indices, weights)

        data.setClean(plug)
        return self

    @staticmethod
    def _prune_builder(array_handle, builder, keep):
        """从输出数组中移除本次不再产生的陈旧元素。

        参数：
            array_handle: 输出数组的 MArrayDataHandle。
            builder: 由该数组句柄取出的 MArrayDataBuilder。
            keep: 本次需要保留的 logical index 序列。

        返回：
            无，直接在 builder 上做删除。

        为什么需要：
            MArrayDataBuilder 只会新增或覆盖元素，不会自动清理。若某个姿势或被
            驱动物体被删除，其对应的输出元素会保持上一次的数值残留下来，下游节点
            仍会读到过期的值。因此每次写出前先扫描现有元素，把不在 keep 集合中的
            全部删掉。

        注意：
            必须先把待删索引收集到 stale 列表，再统一删除——边遍历边删会打乱物理
            下标。removeElement 对不存在的索引会抛异常，这里用 try/except 静默
            吞掉，因为“目标本来就不存在”与“删除成功”对本函数而言结果一致。
        """
        keep_set = set(keep)
        stale = []
        # 先收集，后删除：边遍历边删会让物理下标错位
        for i in range(len(array_handle)):
            array_handle.jumpToPhysicalElement(i)
            idx = array_handle.elementLogicalIndex()
            if idx not in keep_set:
                stale.append(idx)
        for idx in stale:
            try:
                builder.removeElement(idx)
            except Exception:
                # 元素本就不存在，与删除成功等价，忽略即可
                pass

    def _write_double3_array(self, data, attribute, indices, values):
        """把一组三维数值写入 double3 输出数组属性。

        参数：
            data: compute() 传入的 MDataBlock。
            attribute: 目标输出属性（本节点中为 aOutput）。
            indices: 要写入的 logical index 列表。
            values: 与 indices 一一对应的 (x, y, z) 序列。

        返回：
            无。

        说明：
            流程固定为“取 builder -> 清理陈旧元素 -> addElement 逐个写入 ->
            array_handle.set(builder) 提交 -> setAllClean 标记干净”。addElement
            对已存在的逻辑索引返回原有元素的句柄，对不存在的则创建，因此无需区分
            新增与更新。最后的 setAllClean 会把整个数组连同所有元素标记为已求值，
            否则 Maya 可能重复调用 compute()。

        注意：
            目标属性必须在 initialize() 中开启 usesArrayDataBuilder，否则
            builder() 会失败。
        """
        array_handle = data.outputArrayValue(attribute)
        builder = array_handle.builder()
        self._prune_builder(array_handle, builder, indices)
        for i, idx in enumerate(indices):
            handle = builder.addElement(idx)
            v = values[i]
            handle.set3Double(v[0], v[1], v[2])
        array_handle.set(builder)
        array_handle.setAllClean()

    def _write_double_array(self, data, attribute, indices, values):
        """把一组标量数值写入 double 输出数组属性。

        参数：
            data: compute() 传入的 MDataBlock。
            attribute: 目标输出属性（本节点中为 aOutputWeight）。
            indices: 要写入的 logical index 列表，此处即各姿势的逻辑索引。
            values: 与 indices 一一对应的 float 权重列表。

        返回：
            无。

        说明：
            与 _write_double3_array 的流程完全一致，只是写入的是单个 double。
            使用姿势本身的 logical index 作为输出索引，可以让 outputWeight[i]
            始终对应 pose[i]，即使中间有姿势被删除留下索引空洞也不会错位。
        """
        array_handle = data.outputArrayValue(attribute)
        builder = array_handle.builder()
        self._prune_builder(array_handle, builder, indices)
        for i, idx in enumerate(indices):
            handle = builder.addElement(idx)
            handle.setDouble(values[i])
        array_handle.set(builder)
        array_handle.setAllClean()


# ---------------------------------------------------------------------------
# 插件入口点
# ---------------------------------------------------------------------------

def initializePlugin(mobject):
    """插件加载入口，向 Maya 注册 rbfSolver 节点类型。

    参数：
        mobject: Maya 传入的插件 MObject，用于构造 MFnPlugin。

    返回：
        无。

    说明：
        registerNode 需要节点名、唯一的 MTypeId、创建回调、属性初始化回调，以及
        节点类别（此处为 kDependNode，普通依赖图节点）。注册失败时先向脚本编辑器
        打印可读的错误信息，再把异常重新抛出——必须重新抛出，否则 Maya 会误认为
        插件已加载成功，后续 createNode 会以更晦涩的方式失败。

    注意：
        函数名必须是 initializePlugin，Maya 依靠这个约定名来调用。
    """
    plugin = om.MFnPlugin(mobject, kAuthor, kPluginVersion, "Any")
    try:
        plugin.registerNode(
            kPluginNodeName,
            kPluginNodeId,
            RBFSolverNode.creator,
            RBFSolverNode.initialize,
            om.MPxNode.kDependNode,
        )
    except Exception:
        om.MGlobal.displayError(
            "Failed to register node: {0}".format(kPluginNodeName))
        raise


def uninitializePlugin(mobject):
    """插件卸载入口，注销 rbfSolver 节点类型。

    参数：
        mobject: Maya 传入的插件 MObject，用于构造 MFnPlugin。

    返回：
        无。

    说明：
        注销时使用的是 MTypeId 而非节点名。若场景中仍存在该类型的节点实例，
        Maya 会拒绝卸载并抛出异常；此处同样先打印错误再重新抛出，让 Maya 知道
        卸载未完成，从而保持插件处于已加载状态。

    注意：
        函数名必须是 uninitializePlugin，Maya 依靠这个约定名来调用。
    """
    plugin = om.MFnPlugin(mobject)
    try:
        plugin.deregisterNode(kPluginNodeId)
    except Exception:
        om.MGlobal.displayError(
            "Failed to deregister node: {0}".format(kPluginNodeName))
        raise
