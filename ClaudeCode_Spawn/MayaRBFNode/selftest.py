# -*- coding: utf-8 -*-
"""
rbfSolver 节点的独立自测脚本。

    "H:/Program Files/Autodesk/Maya2025/bin/mayapy.exe" selftest.py

既可以在 mayapy 中运行，也可以直接在 Maya 的脚本编辑器里执行本文件
（已经处于 Maya 会话中时会跳过 maya.standalone 的初始化）。

整套脚本共包含 88 项检查，覆盖插值精度、各种核函数、退化输入、
稀疏逻辑索引、场景存取往返、rbf_utils 编辑流程以及若干示例场景。
"""

import math
import os
import sys

PLUGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "rbfSolverNode.py")

_IN_MAYA = "maya" in sys.executable.lower() and "mayapy" in sys.executable.lower()
if _IN_MAYA:
    import maya.standalone
    maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402


FAILURES = []
CHECKS = [0]


def check(condition, message):
    """记录并打印单项检查结果。

    参数:
        condition: 布尔表达式，为真表示该项检查通过。
        message: 描述这项检查的文本，会原样出现在输出里；
            检查失败时同一段文本还会被收进 FAILURES，
            供 main() 在末尾汇总。

    副作用:
        CHECKS[0] 自增，作为全局检查计数；失败项追加到 FAILURES。
    """
    CHECKS[0] += 1
    if condition:
        print("  ok   - {0}".format(message))
    else:
        print("  FAIL - {0}".format(message))
        FAILURES.append(message)


def close(a, b, tol=1e-6):
    """判断两个标量在给定容差内是否相等。

    浮点求解结果不可能精确相等，所有数值断言都要走容差比较。

    参数:
        a, b: 待比较的两个数。
        tol: 允许的绝对误差，默认 1e-6。

    返回:
        绝对差不超过 tol 时返回 True。
    """
    return abs(a - b) <= tol


def vclose(a, b, tol=1e-6):
    """判断两个三分量向量在给定容差内是否逐分量相等。

    参数:
        a, b: 长度至少为 3 的可索引序列（三维坐标、平移值等）。
        tol: 每个分量允许的绝对误差。

    返回:
        三个分量都满足 close() 时返回 True。
    """
    return all(close(a[i], b[i], tol) for i in range(3))


def make_node():
    """新建一个空的 rbfSolver 节点。

    返回:
        新建节点的名字。
    """
    return cmds.createNode("rbfSolver")


def set_pose(node, i, inputs, outputs):
    """把一组样本（姿势）写入节点的 pose[i]。

    一个姿势由若干输入向量（每个驱动器一个）和若干输出向量
    （每个被驱动物体一个）组成，二者共同构成 RBF 的一条训练样本。

    参数:
        node: rbfSolver 节点名。
        i: 姿势的逻辑索引。
        inputs: 三元组序列，按顺序写入 poseInput[0..n]。
        outputs: 三元组序列，按顺序写入 poseOutput[0..m]。
    """
    for j, v in enumerate(inputs):
        cmds.setAttr("{0}.pose[{1}].poseInput[{2}]".format(node, i, j),
                     v[0], v[1], v[2], type="double3")
    for k, v in enumerate(outputs):
        cmds.setAttr("{0}.pose[{1}].poseOutput[{2}]".format(node, i, k),
                     v[0], v[1], v[2], type="double3")


def set_input(node, inputs):
    """设置节点当前的查询点，即各个驱动器的当前值。

    参数:
        node: rbfSolver 节点名。
        inputs: 三元组序列，按顺序写入 input[0..n]。
    """
    for j, v in enumerate(inputs):
        cmds.setAttr("{0}.input[{1}]".format(node, j),
                     v[0], v[1], v[2], type="double3")


def get_output(node, k):
    """读取第 k 个输出向量，触发一次求解。

    参数:
        node: rbfSolver 节点名。
        k: 输出的逻辑索引。

    返回:
        由三个浮点数组成的元组。
    """
    return cmds.getAttr("{0}.output[{1}]".format(node, k))[0]


def get_weights(node, count):
    """读取前 count 个姿势权重。

    权重表示每条样本对当前结果的贡献，是判断插值行为是否正确的
    另一条独立线索。

    参数:
        node: rbfSolver 节点名。
        count: 需要读取的权重个数。

    返回:
        长度为 count 的浮点数列表。
    """
    return [cmds.getAttr("{0}.outputWeight[{1}]".format(node, i))
            for i in range(count)]


# 两个驱动物体（构成 6 维样本空间），两个被驱动物体
POSES = [
    ([(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)], [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]),
    ([(10.0, 0.0, 0.0), (0.0, 0.0, 0.0)], [(0.0, 5.0, 0.0), (0.0, 1.0, 0.0)]),
    ([(0.0, 10.0, 0.0), (0.0, 0.0, 0.0)], [(0.0, 0.0, 5.0), (0.0, 0.0, 1.0)]),
    ([(0.0, 0.0, 0.0), (0.0, 0.0, 10.0)], [(-5.0, 0.0, 0.0), (2.0, 2.0, 2.0)]),
    ([(10.0, 10.0, 0.0), (0.0, 0.0, 10.0)], [(1.0, 2.0, 3.0), (3.0, 0.0, 0.0)]),
]


def build_default_node():
    """创建节点并写入 POSES 中的全部标准样本。

    多数测试都以这套固定样本为基准，便于横向对比不同设置下的结果。

    返回:
        已填好姿势的 rbfSolver 节点名。
    """
    node = make_node()
    for i, (ins, outs) in enumerate(POSES):
        set_pose(node, i, ins, outs)
    return node


# ---------------------------------------------------------------------------

def test_interpolates_samples_exactly():
    """验证 RBF 最核心的插值性质：在样本点上必须精确复现样本值。

    验证内容:
        把查询点逐一放到每条已记录样本的输入位置上，输出必须等于
        该样本记录的输出，并且权重向量必须恰好是第 i 个单位向量
        λ(x_i) = e_i —— 即当前样本独占权重 1，其余样本权重为 0。

    为什么重要:
        这是插值型 RBF 与拟合型方法的分水岭。若样本点上都对不上，
        说明线性方程组的求解或核矩阵的组装存在错误，中间过渡的结果
        更无从谈起。权重等于单位向量还进一步说明求解是"插值"而非
        被岭项过度平滑成了加权平均。

    场景构造:
        使用 build_default_node() 的五条标准样本，依次把 input
        设到每条样本的输入上，比较 output 与 outputWeight。
    """
    print("[test] recorded poses are reproduced exactly")
    node = build_default_node()
    for i, (ins, outs) in enumerate(POSES):
        set_input(node, ins)
        for k, expected in enumerate(outs):
            got = get_output(node, k)
            check(vclose(got, expected, 1e-5),
                  "pose {0} output {1}: {2} == {3}".format(i, k, got, expected))
        w = get_weights(node, len(POSES))
        expected_w = [1.0 if j == i else 0.0 for j in range(len(POSES))]
        check(all(close(w[j], expected_w[j], 1e-5) for j in range(len(POSES))),
              "pose {0} weights are e_{0}: {1}".format(i, [round(x, 4) for x in w]))
    cmds.delete(node)


def test_all_kernels():
    """验证枚举里的每一种核函数都能精确复现样本。

    验证内容:
        遍历 kernel 属性的所有枚举值，对每种核重跑一遍全部样本点，
        统计最大分量误差，要求小于 1e-4。

    为什么重要:
        不同核函数（高斯、多重二次、薄板样条等）的矩阵条件数差别很大，
        某些核还需要额外的形状参数或多项式项才能保证可解。逐个核验证
        可以及早发现"只有默认核能用"这类问题。

    场景构造:
        用 attributeQuery 取出 kernel 枚举名列表，逐个设置后遍历
        标准样本集，记录所有输出分量的最大偏差。
    """
    print("[test] every kernel reproduces the samples")
    node = build_default_node()
    kernels = cmds.attributeQuery("kernel", node=node, listEnum=True)[0].split(":")
    for ki, name in enumerate(kernels):
        cmds.setAttr(node + ".kernel", ki)
        worst = 0.0
        for i, (ins, outs) in enumerate(POSES):
            set_input(node, ins)
            for k, expected in enumerate(outs):
                got = get_output(node, k)
                for c in range(3):
                    worst = max(worst, abs(got[c] - expected[c]))
        check(worst < 1e-4,
              "kernel '{0}' max sample error {1:.3e}".format(name, worst))
    cmds.delete(node)


def test_interpolation_between_samples():
    """验证样本之间的过渡值是平滑且合理的，并检查权重的两个开关。

    验证内容:
        1. 取两条样本输入的中点作为查询点，输出既不等于其中任何一端，
           说明确实发生了混合而不是就近取值。
        2. 中点结果落在合理数值区间内，没有出现剧烈过冲。
        3. 打开 normalizeWeights 后，权重之和恒为 1。
        4. 打开 clampWeights 后，权重全部落在 [0, 1] 内。

    为什么重要:
        样本点上的精确性只是必要条件，插值真正的用途在于样本之间。
        权重归一化与钳制是给动画师做姿势混合时的常用保障，必须在
        任意查询点上都成立，而不只是在样本点上成立。

    场景构造:
        取标准样本 0 与样本 1 的输入逐分量平均作为中点查询，
        随后分别切换 normalizeWeights 与 clampWeights 并读取权重。
    """
    print("[test] in-between values blend smoothly")
    node = build_default_node()
    a, b = POSES[0], POSES[1]
    mid = [tuple((a[0][j][c] + b[0][j][c]) * 0.5 for c in range(3))
           for j in range(2)]
    set_input(node, mid)
    out0 = get_output(node, 0)
    check(not vclose(out0, a[1][0]) and not vclose(out0, b[1][0]),
          "midpoint differs from both neighbours: {0}".format(
              [round(v, 4) for v in out0]))
    check(-1.0 < out0[1] < 6.0,
          "midpoint stays inside a sane range: y={0:.4f}".format(out0[1]))

    # 归一化之后，任意位置上的权重之和都必须为 1
    cmds.setAttr(node + ".normalizeWeights", True)
    total = sum(get_weights(node, len(POSES)))
    check(close(total, 1.0, 1e-6), "normalized weights sum to 1: {0}".format(total))
    cmds.setAttr(node + ".normalizeWeights", False)

    # 钳制之后，权重不允许出现负值
    cmds.setAttr(node + ".clampWeights", True)
    w = get_weights(node, len(POSES))
    check(all(0.0 <= x <= 1.0 for x in w),
          "clamped weights inside [0,1]: {0}".format([round(x, 4) for x in w]))
    cmds.delete(node)


def test_live_update_on_pose_edit():
    """验证修改已有姿势后节点会立即重新求解。

    验证内容:
        1. 改动某条样本的 poseOutput，当前查询点若正落在该样本上，
           输出应马上变成新记录的值。
        2. 改动同一条样本的 poseInput，把查询点移到新的输入位置后，
           输出同样应命中该样本。

    为什么重要:
        求解器会缓存分解后的矩阵，任何一处姿势数据变动都必须让缓存
        失效。若脏值传播不完整，动画师调完姿势后视口不会更新，
        表现为"改了没反应"，是极难排查的问题。

    场景构造:
        把查询点停在样本 2 上，先改它的输出再改它的输入，
        两次都直接读取 output 观察是否跟随。
    """
    print("[test] editing a pose re-solves")
    node = build_default_node()
    set_input(node, POSES[2][0])
    before = get_output(node, 0)
    cmds.setAttr(node + ".pose[2].poseOutput[0]", 9.0, 9.0, 9.0, type="double3")
    after = get_output(node, 0)
    check(vclose(after, (9.0, 9.0, 9.0), 1e-5),
          "output follows the edited pose: {0} -> {1}".format(
              [round(v, 3) for v in before], [round(v, 3) for v in after]))

    cmds.setAttr(node + ".pose[2].poseInput[0]", 0.0, 20.0, 0.0, type="double3")
    set_input(node, [(0.0, 20.0, 0.0), (0.0, 0.0, 0.0)])
    check(vclose(get_output(node, 0), (9.0, 9.0, 9.0), 1e-5),
          "output follows the edited pose input too")
    cmds.delete(node)


def test_degenerate_cases():
    """验证退化配置下节点既不崩溃也不产生 NaN。

    验证内容:
        1. 一条样本都没有时，不应该产生任何输出元素。
        2. 只有一条样本时，无论查询点在哪里，输出都恒为该样本的值，
           且它的权重为 1。
        3. 存在完全重复的样本时，核矩阵必然奇异，求解不能抛异常，
           输出也不能是 NaN（用 v == v 判定，NaN 不等于自身）。

    为什么重要:
        动画师在搭建阶段一定会经过"零条姿势""一条姿势"这些中间状态，
        也常常不小心录入两条一模一样的姿势。任何一种情况让节点抛异常
        或输出 NaN，都会污染整个 DG 求值并可能拖垮场景。

    场景构造:
        从空节点开始逐步添加：先什么都不加，再加一条，
        最后再加一条与首条完全相同的样本以及一条正常样本。
    """
    print("[test] degenerate configurations")
    node = make_node()
    set_input(node, [(1.0, 2.0, 3.0)])
    check(cmds.getAttr(node + ".output", multiIndices=True) in (None, []),
          "no poses -> no outputs")

    set_pose(node, 0, [(1.0, 0.0, 0.0)], [(4.0, 5.0, 6.0)])
    set_input(node, [(99.0, 99.0, 99.0)])
    check(vclose(get_output(node, 0), (4.0, 5.0, 6.0)),
          "single pose -> constant output")
    check(close(cmds.getAttr(node + ".outputWeight[0]"), 1.0),
          "single pose -> weight 1")

    # 重复的姿势会让核矩阵奇异，此时不允许抛出异常
    set_pose(node, 1, [(1.0, 0.0, 0.0)], [(4.0, 5.0, 6.0)])
    set_pose(node, 2, [(2.0, 0.0, 0.0)], [(0.0, 0.0, 0.0)])
    set_input(node, [(1.0, 0.0, 0.0)])
    out = get_output(node, 0)
    check(all(v == v for v in out), "duplicate poses survive: {0}".format(
        [round(v, 4) for v in out]))
    cmds.delete(node)


def test_sparse_indices():
    """验证逻辑索引可以是稀疏、不连续的。

    验证内容:
        姿势索引取 0、7、14，输入索引取 0、3，输出索引取 0、5，
        全部不连续。求解结果仍须与稠密排列时一致：对应的
        output[0]、output[5] 命中样本值，outputWeight[7] 为 1。

    为什么重要:
        Maya 的 multi 属性天然是稀疏的——删掉中间一条姿势、
        断开一个驱动器连接，都会在逻辑索引上留下空洞。若节点内部
        按物理位置而非逻辑索引来配对输入与输出，删除操作之后
        整套对应关系就会错位。测试刻意从一开始就制造空洞。

    场景构造:
        直接用 setAttr 写带跳跃索引的 plug（不走 set_pose 辅助函数），
        把前三条标准样本铺在 7 的倍数上，输入分量按 3 的倍数分布。
    """
    print("[test] sparse / non contiguous logical indices")
    node = make_node()
    for i, (ins, outs) in enumerate(POSES[:3]):
        p = i * 7  # 刻意留出空洞的稀疏姿势索引
        for j, v in enumerate(ins):
            cmds.setAttr("{0}.pose[{1}].poseInput[{2}]".format(node, p, j * 3),
                         v[0], v[1], v[2], type="double3")
        for k, v in enumerate(outs):
            cmds.setAttr("{0}.pose[{1}].poseOutput[{2}]".format(node, p, k * 5),
                         v[0], v[1], v[2], type="double3")
    for j, v in enumerate(POSES[1][0]):
        cmds.setAttr("{0}.input[{1}]".format(node, j * 3),
                     v[0], v[1], v[2], type="double3")

    check(vclose(cmds.getAttr(node + ".output[0]")[0], POSES[1][1][0], 1e-5),
          "sparse output[0] matches")
    check(vclose(cmds.getAttr(node + ".output[5]")[0], POSES[1][1][1], 1e-5),
          "sparse output[5] matches")
    check(close(cmds.getAttr(node + ".outputWeight[7]"), 1.0, 1e-5),
          "sparse weight[7] == 1")
    cmds.delete(node)


def test_connected_transforms():
    """验证节点在真实 DG 连接下驱动变换节点。

    验证内容:
        把两个 locator 的 translate 连到 input，把 output 连到
        另外两个 locator 的 translate，然后移动驱动器到样本位置，
        被驱动物体的实际 translate 应等于样本记录的输出。

    为什么重要:
        前面的测试都是直接 setAttr / getAttr，走的是属性缓存路径。
        接上真实连接后，求值由 DG 的脏值传播驱动，输入是连接进来的
        而不是写死的，这条路径必须单独验证。

    场景构造:
        新建两个驱动 locator 与两个被驱动 locator，逐一连接，
        先测试第一个驱动器控制的样本 1，再测试第二个驱动器
        控制的样本 3，确认两个驱动器都真正参与了求解。
    """
    print("[test] driving real transforms")
    node = build_default_node()
    drivers = [cmds.spaceLocator(name="rbfDriver#")[0] for _ in range(2)]
    driven = [cmds.spaceLocator(name="rbfDriven#")[0] for _ in range(2)]
    for j, d in enumerate(drivers):
        cmds.connectAttr(d + ".translate", "{0}.input[{1}]".format(node, j))
    for k, d in enumerate(driven):
        cmds.connectAttr("{0}.output[{1}]".format(node, k), d + ".translate")

    cmds.setAttr(drivers[0] + ".translate", 10.0, 0.0, 0.0)
    cmds.setAttr(drivers[1] + ".translate", 0.0, 0.0, 0.0)
    check(vclose(cmds.getAttr(driven[0] + ".translate")[0], (0.0, 5.0, 0.0), 1e-4),
          "driven[0] follows pose 1")
    check(vclose(cmds.getAttr(driven[1] + ".translate")[0], (0.0, 1.0, 0.0), 1e-4),
          "driven[1] follows pose 1")

    cmds.setAttr(drivers[1] + ".translate", 0.0, 0.0, 10.0)
    cmds.setAttr(drivers[0] + ".translate", 0.0, 0.0, 0.0)
    check(vclose(cmds.getAttr(driven[0] + ".translate")[0], (-5.0, 0.0, 0.0), 1e-4),
          "driven[0] follows pose 3 (second driver)")
    cmds.delete(node, drivers, driven)


def test_scene_roundtrip():
    """验证保存并重新打开场景后整套设置依然有效。

    验证内容:
        在新场景里建好节点、设定查询点并记录输出，存成 mayaAscii，
        清空场景再打开，重新读取输出应与保存前完全一致。

    为什么重要:
        复合 multi 属性（pose 下面嵌套 poseInput / poseOutput）的
        序列化很容易出错——分量顺序、稀疏索引、默认值抑制都可能
        导致文件里丢数据。存盘后对不上的节点在实际项目里毫无用处。

    场景构造:
        文件写到 Maya 的用户临时目录，测试结束后清空场景并删除临时文件；
        重新打开后节点名固定为 rbfSolver1。
    """
    print("[test] save / reload keeps the setup")
    cmds.file(new=True, force=True)
    node = build_default_node()
    set_input(node, POSES[4][0])
    expected = get_output(node, 0)

    path = os.path.join(cmds.internalVar(userTmpDir=True), "rbf_selftest.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)
    cmds.file(new=True, force=True)
    cmds.file(path, open=True, force=True)

    check(vclose(get_output("rbfSolver1", 0), expected, 1e-5),
          "reopened scene evaluates the same: {0}".format(
              [round(v, 4) for v in expected]))
    cmds.file(new=True, force=True)
    try:
        os.remove(path)
    except OSError:
        pass


def test_utils_and_example():
    """验证 rbf_utils 的编辑流程以及 example_setup 演示场景。

    验证内容:
        1. 演示场景搭建后姿势条数、编辑模式状态、被驱动 plug 解析都正确。
        2. 演示场景里记录的每条姿势都能被精确复现。
        3. 进入编辑模式会断开被驱动物体的连接，让动画师能手动摆放。
        4. 通过 add_pose 录制的新姿势，退出编辑模式后能被精确复现，
           且在该姿势上新样本独占权重。
        5. delete_pose 能真正移除姿势，apply_pose 能把驱动器摆回记录值。

    为什么重要:
        动画师不会直接操作属性，全部经由 rbf_utils 这层封装。
        录制、应用、删除姿势构成完整的编辑闭环，任何一环出错都会
        让工具在实际使用中失效，而这类错误在纯节点层面测不出来。

    场景构造:
        调用 example_setup.build() 得到带两个驱动器和两个被驱动物体的
        完整演示场景，随后依次演练整套编辑流程，最后清空场景。
    """
    print("[test] rbf_utils authoring workflow / demo scene")
    sys.path.insert(0, os.path.dirname(PLUGIN))
    import rbf_utils
    import example_setup

    node = example_setup.build()
    drivers = ["rbf_driverA", "rbf_driverB"]
    driven = ["rbf_drivenA", "rbf_drivenB"]

    check(len(rbf_utils.pose_indices(node)) == len(example_setup.DEMO_POSES),
          "demo recorded {0} poses".format(len(rbf_utils.pose_indices(node))))
    check(not rbf_utils.is_edit_mode(node), "demo left edit mode")
    check([p for _, p in rbf_utils.driven_plugs(node)] ==
          [d + ".translate" for d in driven], "driven plugs resolved")

    for i, (a, b, c, d) in enumerate(example_setup.DEMO_POSES):
        cmds.setAttr(drivers[0] + ".translate", *a)
        cmds.setAttr(drivers[1] + ".translate", *b)
        check(vclose(cmds.getAttr(driven[0] + ".translate")[0], c, 1e-4) and
              vclose(cmds.getAttr(driven[1] + ".translate")[0], d, 1e-4),
              "demo pose {0} reproduced".format(i))

    # 经由辅助函数录制的姿势必须能原样复现
    rbf_utils.set_edit_mode(node, True)
    check(not (cmds.listConnections(node + ".output") or []),
          "edit mode disconnected the driven objects")
    cmds.setAttr(drivers[0] + ".translate", -10, 0, 0)
    cmds.setAttr(drivers[1] + ".translate", 0, 0, 0)
    cmds.setAttr(driven[0] + ".translate", 1, 2, 3)
    cmds.setAttr(driven[1] + ".translate", 4, 5, 6)
    new_index = rbf_utils.add_pose(node)
    rbf_utils.set_edit_mode(node, False)
    check(vclose(cmds.getAttr(driven[0] + ".translate")[0], (1, 2, 3), 1e-4) and
          vclose(cmds.getAttr(driven[1] + ".translate")[0], (4, 5, 6), 1e-4),
          "pose {0} added through rbf_utils".format(new_index))

    weights = dict(rbf_utils.pose_weights(node))
    check(close(weights[new_index], 1.0, 1e-4),
          "new pose owns the weight: {0:.4f}".format(weights[new_index]))

    rbf_utils.delete_pose(node, new_index)
    check(new_index not in rbf_utils.pose_indices(node),
          "pose {0} deleted".format(new_index))

    rbf_utils.apply_pose(node, 2)
    check(vclose(cmds.getAttr(drivers[0] + ".translate")[0], (0, 10, 0), 1e-4),
          "apply_pose pushed the drivers back")
    cmds.file(new=True, force=True)


def test_add_and_remove_objects():
    """验证事后增删驱动器与被驱动物体不会破坏已有姿势。

    验证内容:
        1. add_driver 之后，所有旧姿势仍能被精确复现——说明新驱动器
           在每条已有姿势上都被回填了当时的实际值。
        2. 新驱动器确实参与了距离度量：把它挪开会改变求解结果。
        3. add_driven 之后，新物体在每条姿势上都保持它被回填的初值。
        4. 只给某一条姿势重新雕刻新物体的值，其余姿势仍保持回填值，
           且原有的两个被驱动物体不受影响。
        5. remove_driven / remove_driver 会断开连接并清掉各姿势里
           对应的分量。

    为什么重要:
        这是最容易出错也最要命的一条。事后加物体时若不把已有姿势
        回填成物体的当前值，缺失项会被当成 (0, 0, 0) 参与求解，
        整套已经调好的姿势就会被生生带歪，而且现象隐蔽——只在
        某些姿势上偏移一点，很难归因。

    场景构造:
        从 example_setup 演示场景出发，先加第三个驱动器再加第三个
        被驱动物体，每一步都用嵌套的 poses_still_exact() 重扫全部
        旧姿势核对最大误差，最后再依次移除并复查。
    """
    print("[test] adding / removing drivers and driven objects later")
    sys.path.insert(0, os.path.dirname(PLUGIN))
    import rbf_utils
    import example_setup

    node = example_setup.build()
    drivers = ["rbf_driverA", "rbf_driverB"]
    driven = ["rbf_drivenA", "rbf_drivenB"]

    def poses_still_exact(label):
        """重扫演示场景的全部姿势，核对旧姿势是否依然被精确复现。

        参数:
            label: 出现在检查文本里的阶段标签，用于区分是哪一步之后
                做的复查。

        做法:
            把驱动器逐一摆到每条姿势的记录输入上，读取两个被驱动物体的
            实际 translate，统计所有分量与记录输出的最大偏差，
            要求小于 1e-4。
        """
        worst = 0.0
        for a, b, c, d in example_setup.DEMO_POSES:
            cmds.setAttr(drivers[0] + ".translate", *a)
            cmds.setAttr(drivers[1] + ".translate", *b)
            for obj, expected in ((driven[0], c), (driven[1], d)):
                got = cmds.getAttr(obj + ".translate")[0]
                for i in range(3):
                    worst = max(worst, abs(got[i] - expected[i]))
        check(worst < 1e-4, "{0}: old poses unchanged (max {1:.2e})".format(
            label, worst))

    # ---- 追加第三个驱动器 ---------------------------------------------------
    driver_c = cmds.spaceLocator(name="rbf_driverC")[0]
    cmds.setAttr(driver_c + ".translate", 3, 3, 3)
    j = rbf_utils.add_driver(node, driver_c)
    check(j == 2, "add_driver used input index {0}".format(j))
    check(len(rbf_utils.driver_plugs(node)) == 3, "three drivers connected")
    poses_still_exact("after add_driver")

    # 新驱动器已成为距离度量的一部分：原有驱动器停在姿势 1 上、
    # 而新驱动器偏离它的记录值时，结果就不再等于姿势 1
    def go_to_pose(index, driver_c_value=(3, 3, 3)):
        """把三个驱动器摆到指定演示姿势的记录位置。

        参数:
            index: 演示姿势的序号。
            driver_c_value: 第三个驱动器的位置，默认为它被回填的
                初值 (3, 3, 3)；传入其它值即可制造"偏离该姿势"的情形。
        """
        a, b = example_setup.DEMO_POSES[index][0], example_setup.DEMO_POSES[index][1]
        cmds.setAttr(drivers[0] + ".translate", *a)
        cmds.setAttr(drivers[1] + ".translate", *b)
        cmds.setAttr(driver_c + ".translate", *driver_c_value)

    go_to_pose(1, (9, 3, 3))
    pulled = cmds.getAttr(driven[0] + ".translate")[0]
    check(not vclose(pulled, (0, 8, 0), 1e-3),
          "the new driver affects the result: {0} instead of pose 1's "
          "(0, 8, 0)".format([round(v, 3) for v in pulled]))
    go_to_pose(1)

    # ---- 追加第三个被驱动物体 -------------------------------------------
    driven_c = cmds.spaceLocator(name="rbf_drivenC")[0]
    cmds.setAttr(driven_c + ".translate", 1, 1, 1)
    k = rbf_utils.add_driven(node, driven_c)
    check(k == 2, "add_driven used output index {0}".format(k))
    check(cmds.isConnected(node + ".output[2]", driven_c + ".translate"),
          "new driven object connected")
    poses_still_exact("after add_driven")

    for index in range(len(example_setup.DEMO_POSES)):
        go_to_pose(index)
        if not vclose(cmds.getAttr(driven_c + ".translate")[0], (1, 1, 1), 1e-4):
            break
    else:
        index = None
    check(index is None,
          "new driven object holds its backfilled value on every pose")

    # 只在姿势 2 上给它一个真正雕刻过的值
    rbf_utils.set_edit_mode(node, True)
    rbf_utils.apply_pose(node, 2)
    cmds.setAttr(driven_c + ".translate", 7, 7, 7)
    rbf_utils.update_pose(node, 2)
    rbf_utils.set_edit_mode(node, False)

    go_to_pose(2)
    check(vclose(cmds.getAttr(driven_c + ".translate")[0], (7, 7, 7), 1e-4),
          "sculpted value reached on pose 2")
    go_to_pose(0)
    check(vclose(cmds.getAttr(driven_c + ".translate")[0], (1, 1, 1), 1e-4),
          "backfilled value still held on pose 0")
    poses_still_exact("after sculpting the new driven object")

    # ---- 移除 -----------------------------------------------------------
    rbf_utils.remove_driven(node, 2)
    check(not cmds.listConnections(driven_c + ".translate", source=True),
          "remove_driven disconnected the object")
    check(all(2 not in (cmds.getAttr("{0}.pose[{1}].poseOutput".format(node, i),
                                     multiIndices=True) or [])
              for i in rbf_utils.pose_indices(node)),
          "remove_driven cleared poseOutput[2] everywhere")

    rbf_utils.remove_driver(node, 2)
    check(len(rbf_utils.driver_plugs(node)) == 2, "remove_driver unhooked it")
    poses_still_exact("after removals")
    cmds.file(new=True, force=True)


def test_editing_outputs_later():
    """验证事后修改某条姿势的输出值，且不波及其它姿势。

    验证内容（分三段）:
        A. 直接对 poseOutput setAttr 就能立刻生效，无需进入编辑模式，
           其余姿势保持不变。
        B. 进入编辑模式手工雕刻被驱动物体，再用 update_pose 录回去，
           结果同样只影响目标姿势。
        C. 驱动器被锁定（或被约束）时，apply_pose 无法把它摆回记录位置，
           会在返回值里报告这个 plug。此时必须用 inputs=False 更新，
           poseInput 保持原样；反之 inputs=True 会把驱动器当时所在的
           错误位置录成新样本，测试显式演示了这一后果并随即还原。

    为什么重要:
        锁定或被约束的驱动器在真实绑定里非常普遍。如果 update_pose
        无条件连输入一起录，就会把"摆不过去"的错误位置写成样本，
        整条姿势静默损坏。inputs=False 正是为这种场景提供的保护，
        必须确保它真的什么都没动。

    场景构造:
        沿用 example_setup 演示场景，以姿势 3 为编辑目标；
        嵌套的 others_intact() 负责在每次改动后复查其余姿势。
        第三段先把 driverA 的 translate 上锁，再走一遍应用与更新流程。
    """
    print("[test] changing a pose's output after the fact")
    sys.path.insert(0, os.path.dirname(PLUGIN))
    import rbf_utils
    import example_setup

    node = example_setup.build()
    drivers = ["rbf_driverA", "rbf_driverB"]
    driven = ["rbf_drivenA", "rbf_drivenB"]

    def go_to_pose(index):
        """把两个驱动器摆到指定演示姿势的记录输入位置。

        参数:
            index: 演示姿势的序号。
        """
        a, b = example_setup.DEMO_POSES[index][0], example_setup.DEMO_POSES[index][1]
        cmds.setAttr(drivers[0] + ".translate", *a)
        cmds.setAttr(drivers[1] + ".translate", *b)

    def pose_input(index, j):
        """读取某条姿势中第 j 个驱动器记录的输入值。

        参数:
            index: 姿势的逻辑索引。
            j: 驱动器（输入）的逻辑索引。

        返回:
            三元组形式的记录值，便于直接用 == 比较是否被改写。
        """
        return tuple(cmds.getAttr(
            "{0}.pose[{1}].poseInput[{2}]".format(node, index, j))[0])

    def others_intact(skip, label):
        """复查除 skip 之外的所有姿势是否仍被精确复现。

        参数:
            skip: 本轮被有意修改、因而跳过检查的姿势序号。
            label: 出现在检查文本里的阶段标签。

        做法:
            逐条摆到姿势输入上，统计两个被驱动物体所有分量的
            最大偏差，要求小于 1e-4。
        """
        worst = 0.0
        for i, (a, b, c, d) in enumerate(example_setup.DEMO_POSES):
            if i == skip:
                continue
            go_to_pose(i)
            for obj, expected in ((driven[0], c), (driven[1], d)):
                got = cmds.getAttr(obj + ".translate")[0]
                for n in range(3):
                    worst = max(worst, abs(got[n] - expected[n]))
        check(worst < 1e-4,
              "{0}: the other poses are untouched (max {1:.2e})".format(label, worst))

    # ---- A：直接 setAttr 改写记录值，无需进入编辑模式 -----------
    cmds.setAttr(node + ".pose[3].poseOutput[0]", -2, -2, -2, type="double3")
    go_to_pose(3)
    check(vclose(cmds.getAttr(driven[0] + ".translate")[0], (-2, -2, -2), 1e-4),
          "setAttr on poseOutput takes effect immediately")
    others_intact(3, "after setAttr")
    restore = example_setup.DEMO_POSES[3][2]
    cmds.setAttr(node + ".pose[3].poseOutput[0]",
                 restore[0], restore[1], restore[2], type="double3")

    # ---- B：手工雕刻后录回 -----------------------------------------------
    rbf_utils.set_edit_mode(node, True)
    skipped = rbf_utils.apply_pose(node, 3)
    check(skipped == [], "apply_pose could place everything: {0}".format(skipped))
    cmds.setAttr(driven[0] + ".translate", 3, 3, 3)
    rbf_utils.update_pose(node, 3, inputs=False)
    rbf_utils.set_edit_mode(node, False)

    go_to_pose(3)
    check(vclose(cmds.getAttr(driven[0] + ".translate")[0], (3, 3, 3), 1e-4),
          "sculpted output recorded on pose 3")
    others_intact(3, "after sculpting")

    # ---- C：被锁定或被约束的驱动器不能污染 poseInput ---------
    go_to_pose(3)
    cmds.setAttr(drivers[0] + ".translate", lock=True)
    before = pose_input(1, 0)

    rbf_utils.set_edit_mode(node, True)
    skipped = rbf_utils.apply_pose(node, 1)
    check(drivers[0] + ".translate" in skipped,
          "apply_pose reports the locked driver: {0}".format(skipped))

    rbf_utils.update_pose(node, 1, inputs=False)
    check(pose_input(1, 0) == before,
          "inputs=False left poseInput alone: {0}".format(before))

    # ……换成 inputs=True 确实会把错误的样本录进去，这里显式演示后再还原
    rbf_utils.update_pose(node, 1, inputs=True, outputs=False)
    check(pose_input(1, 0) != before,
          "inputs=True would have overwritten it with {0}".format(
              pose_input(1, 0)))
    cmds.setAttr("{0}.pose[1].poseInput[0]".format(node),
                 before[0], before[1], before[2], type="double3")

    rbf_utils.set_edit_mode(node, False)
    cmds.setAttr(drivers[0] + ".translate", lock=False)
    others_intact(3, "after the locked-driver round trip")
    cmds.file(new=True, force=True)


def test_degenerate_sample_layouts():
    """回归测试：开启线性项时，共面或共线的样本分布仍须可解。

    验证内容:
        对三种退化的样本分布（XZ 平面上的一圈点、沿 X 轴共线的点、
        除一个点外全部重合），在 useLinearTerm 打开的情况下，
        每条样本仍须被精确复现。

    为什么重要:
        这是一个针对既有缺陷的回归测试。当一圈样本的 y 分量全为 0 时，
        多项式部分里对应 y 的那一列与常数列线性相关，增广矩阵必然奇异，
        而且岭项只作用在核矩阵块上，加多少都救不回来。求解器必须识别
        并丢弃这些线性相关的列，而不是直接放弃——曾经的行为是放弃并把
        所有权重置零，表现为被驱动物体全部塌到原点。

    场景构造:
        每种分布单独建一个节点，样本的输入与输出取同一个点
        （恒等映射，期望值一目了然），打开 useLinearTerm 后遍历
        全部样本点统计最大误差。
    """
    print("[test] coplanar / collinear samples with the linear term on")
    # 一圈 y 全为 0 的样本会让多项式里对应 y 的列与常数列线性相关：
    # 增广矩阵必然奇异，在核矩阵块上加多少岭项都无济于事。求解器必须
    # 丢弃这些相关列继续求解，而不是放弃（旧行为会把所有权重置零）。
    layouts = {
        "ring in the XZ plane": [
            (10.0 * math.cos(2 * math.pi * i / 8), 0.0,
             10.0 * math.sin(2 * math.pi * i / 8)) for i in range(8)],
        "collinear along X": [(float(i) * 3.0, 0.0, 0.0) for i in range(6)],
        "all on one point but one": [(0.0, 0.0, 0.0)] * 3 + [(5.0, 0.0, 0.0)],
    }
    for label, points in layouts.items():
        node = make_node()
        cmds.setAttr(node + ".useLinearTerm", True)
        for i, p in enumerate(points):
            set_pose(node, i, [p], [p])
        worst = 0.0
        for i, p in enumerate(points):
            set_input(node, [p])
            got = get_output(node, 0)
            for c in range(3):
                worst = max(worst, abs(got[c] - p[c]))
        check(worst < 1e-4,
              "{0}: samples still reproduced (max {1:.2e})".format(label, worst))
        cmds.delete(node)


def test_snap_to_nearest_locator():
    """验证"吸附到最近 locator"示例的行为。

    验证内容:
        1. 控制器正好停在某个 locator 上时，被驱动物体精确落在其上。
        2. 在相邻两个 locator 之间移动时，结果始终吸附到较近的那一个，
           在 20%、40% 处贴向前者，60%、80% 处贴向后者——即中点附近
           发生一次干脆的切换，而不是平滑过渡。
        3. 控制器移到圆环之外时，仍保持在最近的 locator 上。
        4. 控制器位于圆环中心时，物体停在中心。
        5. 姿势样本是连接进来的，拖动某个 locator 会实时重新求解，
           物体随之跟到它的新位置。

    为什么重要:
        这个示例用很小的 snap 参数把 RBF 逼成近似阶跃的响应，
        既是常见的"最近邻吸附"用法，也是对核函数形状参数的一次
        极端取值检验：过渡带过宽会失去吸附感，过窄则会数值不稳。
        样本输入采用连接而非固化的值，还顺带验证了样本随场景实时更新。

    场景构造:
        用 example_snap_to_locators.build() 生成半径 10、
        8 个 locator 的圆环，snap 取 0.15；嵌套的 obj_at() 负责
        移动控制器并读回物体位置，dist() 计算三维欧氏距离。
    """
    print("[test] snap-to-nearest-locator demo")
    sys.path.insert(0, os.path.dirname(PLUGIN))
    import example_snap_to_locators as demo

    rbf, ctrl, obj, locs = demo.build(count=8, ring_radius=10.0, snap=0.15)
    targets = [cmds.getAttr(l + ".translate")[0] for l in locs]

    def obj_at(pos):
        """把控制器移到指定位置，返回被驱动物体求解后的位置。

        参数:
            pos: 控制器的目标位置（三元组）。

        返回:
            被驱动物体的实际 translate。
        """
        cmds.setAttr(ctrl + ".translate", pos[0], pos[1], pos[2])
        return cmds.getAttr(obj + ".translate")[0]

    def dist(a, b):
        """计算两个三维点之间的欧氏距离。

        参数:
            a, b: 长度至少为 3 的可索引序列。

        返回:
            距离标量，用于判断是否吸附到了目标点。
        """
        return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))

    worst = 0.0
    for i, t in enumerate(targets):
        worst = max(worst, dist(obj_at(t), t))
    check(worst < 1e-4,
          "ctrl on a locator puts the object on it (max {0:.2e})".format(worst))

    a, b = targets[0], targets[1]
    for frac, expected, label in ((0.2, a, "20%"), (0.4, a, "40%"),
                                  (0.6, b, "60%"), (0.8, b, "80%")):
        mid = tuple(a[i] + (b[i] - a[i]) * frac for i in range(3))
        check(dist(obj_at(mid), expected) < 0.05,
              "{0} of the way loc1->loc2 still snaps to the nearer one".format(label))

    check(dist(obj_at((14.0, 0.0, 0.0)), targets[0]) < 0.05,
          "outside the ring it holds the nearest locator")
    check(dist(obj_at((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0)) < 1e-4,
          "at the ring centre it sits at the centre")

    # 姿势样本是连接进来的，因此拖动 locator 会触发实时重新求解
    cmds.setAttr(locs[0] + ".translate", 20.0, 5.0, 0.0)
    check(dist(obj_at((20.0, 5.0, 0.0)), (20.0, 5.0, 0.0)) < 1e-4,
          "dragging a locator updates the solve")
    cmds.file(new=True, force=True)


def main():
    """加载插件并依次运行全部测试，最后汇总结果。

    流程:
        先确保 rbfSolverNode.py 已加载，然后按顺序执行所有 test_*
        函数，最后打印检查总数与失败数，并逐条列出失败项。

    返回:
        存在失败项时返回 1，全部通过返回 0，可直接用作进程退出码。
    """
    if not cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.loadPlugin(PLUGIN)
    print("plugin loaded: {0}".format(PLUGIN))

    test_interpolates_samples_exactly()
    test_all_kernels()
    test_interpolation_between_samples()
    test_live_update_on_pose_edit()
    test_degenerate_cases()
    test_sparse_indices()
    test_connected_transforms()
    test_scene_roundtrip()
    test_utils_and_example()
    test_add_and_remove_objects()
    test_editing_outputs_later()
    test_degenerate_sample_layouts()
    test_snap_to_nearest_locator()

    print("")
    print("{0} checks, {1} failed".format(CHECKS[0], len(FAILURES)))
    for f in FAILURES:
        print("  FAILED: {0}".format(f))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    code = main()
    if _IN_MAYA:
        try:
            maya.standalone.uninitialize()
        except Exception:
            pass
    sys.exit(code)
