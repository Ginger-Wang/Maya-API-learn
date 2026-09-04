# -*- coding: utf-8 -*-
"""
rbfSolver 节点的建立与录制辅助工具。

    import rbf_utils
    rbf = rbf_utils.create_rbf(["driverA", "driverB"], ["drivenA", "drivenB"])

    rbf_utils.set_edit_mode(rbf, True)      # 断开被驱动物体
    # ... 摆放驱动器，雕刻被驱动物体 ...
    rbf_utils.add_pose(rbf)                 # 录制当前状态
    # ... 每个姿势重复一次 ...
    rbf_utils.set_edit_mode(rbf, False)     # 重新接回连接

姿势直接从 driver / driven plug 当前的取值录制，因此节点本身保持为普通的
dependency node（不需要自定义命令或 MPxCommand），本模块只负责驱动它的属性。

语法同时兼容 Python 2.7 / 3.x（已在 Maya 2025 上验证）。
"""

import json
import re

import maya.cmds as cmds

NODE_TYPE = "rbfSolver"
META_ATTR = "rbfMeta"

# 用于从 plug 字符串中提取所有 "[数字]" 形式的 logical index
_INDEX_RE = re.compile(r"\[(\d+)\]")


# ---------------------------------------------------------------------------
# 底层辅助
# ---------------------------------------------------------------------------

def _plug_index(plug):
    """取出 plug 字符串中最后一个方括号里的 logical index。

    例如 ``'node.output[3]'`` 返回 ``3``。取最后一个是因为嵌套的 multi
    （如 ``node.pose[2].poseInput[5]``）需要的是最内层那一级的下标。

    参数:
        plug: plug 名称字符串。

    返回:
        int，解析出的 logical index；字符串中没有方括号下标时返回 0。
    """
    found = _INDEX_RE.findall(plug)
    return int(found[-1]) if found else 0


def _read_meta(node):
    """读取节点上以 JSON 形式保存的附加信息（meta）。

    meta 存放在节点的 ``rbfMeta`` 字符串属性里，记录 edit mode 状态以及
    edit mode 期间被临时断开的 driven 连接，用于在退出 edit mode 时恢复。

    参数:
        node: rbfSolver 节点名。

    返回:
        dict。属性不存在、内容为空、或 JSON 解析失败时返回空字典，
        因此调用方无需额外做容错。
    """
    if not cmds.attributeQuery(META_ATTR, node=node, exists=True):
        return {}
    raw = cmds.getAttr("{0}.{1}".format(node, META_ATTR)) or ""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def _write_meta(node, meta):
    """把 meta 字典序列化成 JSON 写回节点。

    若 ``rbfMeta`` 属性尚不存在则先添加（string 类型的动态属性），
    因此可以安全地在任意 rbfSolver 节点上调用。

    参数:
        node: rbfSolver 节点名。
        meta: 需要保存的字典，必须可被 json 序列化。

    返回:
        None。
    """
    plug = "{0}.{1}".format(node, META_ATTR)
    if not cmds.attributeQuery(META_ATTR, node=node, exists=True):
        cmds.addAttr(node, longName=META_ATTR, dataType="string")
    cmds.setAttr(plug, json.dumps(meta), type="string")


def _multi_indices(plug):
    """列出一个 multi 属性上实际存在的 logical index。

    multi 的 logical index 可以是稀疏的（例如删除中间某项后会留下空洞），
    因此不能用 ``range(count)`` 代替，必须查询真实存在的下标。

    参数:
        plug: multi 属性的 plug 名，如 ``"node.input"`` 或
            ``"node.pose[0].poseInput"``。

    返回:
        升序排列的 int 列表；该 multi 上没有任何元素时返回空列表。
    """
    return sorted(cmds.getAttr(plug, multiIndices=True) or [])


def driver_plugs(node):
    """列出所有连入 ``.input`` 的驱动器 plug。

    参数:
        node: rbfSolver 节点名。

    返回:
        ``[(inputIndex, sourcePlug), ...]``，按 input 的 logical index 升序排列。
        inputIndex 是 ``.input`` multi 上的 logical index，sourcePlug 是上游的
        源 plug 名（如 ``"pCube1.translate"``）。

    注意:
        driver 侧的连接不会被 edit mode 断开，所以这里直接查询连接即可，
        无需像 :func:`driven_plugs` 那样从 meta 回退读取。
    """
    conns = cmds.listConnections("{0}.input".format(node), plugs=True,
                                 connections=True, source=True,
                                 destination=False) or []
    pairs = []
    for i in range(0, len(conns), 2):
        pairs.append((_plug_index(conns[i]), conns[i + 1]))
    pairs.sort()
    return pairs


def driven_plugs(node):
    """列出所有被 ``.output`` 驱动的目标 plug。

    参数:
        node: rbfSolver 节点名。

    返回:
        ``[(outputIndex, destinationPlug), ...]``，已去重并排序。

    注意:
        节点处于 edit mode 时 output 的连接是被主动断开的，此时查询连接会
        什么都查不到。因此本函数在实际连接之外，还会从 meta 中记录的
        ``driven`` 列表回退读取，保证 :func:`update_pose`、:func:`apply_pose`
        等在 edit mode 期间仍然知道要读写哪些被驱动 plug。
        回退读取时会用 ``objExists`` 过滤掉已被删除的 plug。
    """
    conns = cmds.listConnections("{0}.output".format(node), plugs=True,
                                 connections=True, source=False,
                                 destination=True) or []
    pairs = []
    for i in range(0, len(conns), 2):
        pairs.append((_plug_index(conns[i]), conns[i + 1]))

    for index, plug in _read_meta(node).get("driven", []):
        if cmds.objExists(plug):
            pairs.append((index, plug))

    pairs = sorted(set(pairs))
    return pairs


def pose_indices(node):
    """列出节点上已存在的姿势的 logical index。

    参数:
        node: rbfSolver 节点名。

    返回:
        升序排列的 int 列表，对应 ``node.pose`` 这个 multi 上实际存在的元素。

    注意:
        删除过中间的姿势后下标会出现空洞，返回值不保证连续，也不等同于
        姿势数量的 ``range``；遍历姿势时应始终使用本函数的返回值。
    """
    return _multi_indices("{0}.pose".format(node))


def _resolve_plug(item, attr):
    """把物体名或完整 plug 名统一规整成完整 plug 名。

    参数:
        item: 物体名（如 ``"pCube1"``）或已带属性的完整 plug 名
            （如 ``"pCube1.rotate"``）。
        attr: 当 ``item`` 只是物体名时补上的属性名。

    返回:
        完整的 plug 名字符串。

    注意:
        判定依据仅仅是字符串中是否含有 ``"."``，因此含命名空间但不含属性的
        名称（如 ``"ns:pCube1"``）能正确处理，而带层级路径的名称
        （如 ``"|grp|pCube1"``）也不含点号，同样按物体名处理。
    """
    return item if "." in item else "{0}.{1}".format(item, attr)


def _plug_value(plug):
    """读取一个 plug 的值，并把复合类型的返回结果拆平。

    ``cmds.getAttr`` 读取 double3 之类的复合属性时返回的是 ``[(x, y, z)]``
    这种被多包了一层列表的结构，本函数负责剥掉外层，使调用方总能得到可以
    直接按 ``value[0]``、``value[1]``、``value[2]`` 索引的三元组。

    参数:
        plug: 要读取的 plug 名。

    返回:
        属性值；复合属性返回其内层元组，标量属性原样返回。
    """
    value = cmds.getAttr(plug)
    if isinstance(value, list):
        value = value[0]
    return value


def _used_driver_indices(node):
    """收集 driver 侧所有已被占用的 logical index。

    统计范围既包括 ``.input`` 上已存在的元素，也包括每个姿势的
    ``poseInput`` 上已存在的元素。后者不可省略：某个 driver 被断开但姿势里
    仍残留其样本值时，如果只看 ``.input`` 就会把新 driver 分配到同一个下标，
    从而复用到脏数据。

    参数:
        node: rbfSolver 节点名。

    返回:
        int 的集合（set）；没有任何占用时返回空集合。
    """
    used = set(_multi_indices("{0}.input".format(node)))
    for i in pose_indices(node):
        used.update(_multi_indices(
            "{0}.pose[{1}].poseInput".format(node, i)))
    return used


def _used_driven_indices(node):
    """收集 driven 侧所有已被占用的 logical index。

    与 :func:`_used_driver_indices` 同理，统计范围包括当前的 driven 连接
    （经 :func:`driven_plugs`，因此 edit mode 期间也能从 meta 取到）以及每个
    姿势 ``poseOutput`` 上已存在的元素，避免新 driven 复用到残留数据的下标。

    参数:
        node: rbfSolver 节点名。

    返回:
        int 的集合（set）；没有任何占用时返回空集合。
    """
    used = set(index for index, _ in driven_plugs(node))
    for i in pose_indices(node):
        used.update(_multi_indices(
            "{0}.pose[{1}].poseOutput".format(node, i)))
    return used


# ---------------------------------------------------------------------------
# 建立
# ---------------------------------------------------------------------------

def create_rbf(drivers, driven, driver_attr="translate", driven_attr="translate",
               name="rbf"):
    """创建一个 rbfSolver 节点，并与给定的物体连好线。

    参数:
        drivers: 驱动器列表。元素可以是物体名（会自动补上 ``driver_attr``），
            也可以是完整 plug 名，如 ``"pCube1.rotate"``。
            按列表顺序依次接到 ``input[0]``、``input[1]`` ……
        driven: 被驱动物体列表，规则同上，依次接到 ``output[0]``、
            ``output[1]`` ……
        driver_attr: drivers 中只给了物体名时使用的属性名，默认 translate。
        driven_attr: driven 中只给了物体名时使用的属性名，默认 translate。
        name: 节点名前缀，最终节点名为 ``"<name>_rbf"``。

    返回:
        新建的 rbfSolver 节点名。

    注意:
        若 rbfSolverNode 插件尚未加载，会尝试按名称加载；加载失败则抛出
        RuntimeError，提示需要先用 ``cmds.loadPlugin(<path>)`` 指定完整路径。
        新节点会立即写入一份初始 meta（driven 为空、editMode 为 False）。
    """
    if not cmds.pluginInfo("rbfSolverNode", query=True, loaded=True):
        try:
            cmds.loadPlugin("rbfSolverNode")
        except RuntimeError:
            raise RuntimeError(
                "The rbfSolverNode plug-in is not loaded. Load rbfSolverNode.py "
                "first (cmds.loadPlugin(<path>)).")

    node = cmds.createNode(NODE_TYPE, name="{0}_rbf".format(name))
    _write_meta(node, {"driven": [], "editMode": False})

    for j, item in enumerate(drivers):
        plug = _resolve_plug(item, driver_attr)
        cmds.connectAttr(plug, "{0}.input[{1}]".format(node, j), force=True)

    for k, item in enumerate(driven):
        plug = _resolve_plug(item, driven_attr)
        cmds.connectAttr("{0}.output[{1}]".format(node, k), plug, force=True)

    return node


# ---------------------------------------------------------------------------
# 在已有的 solver 上增删物体
# ---------------------------------------------------------------------------

def add_driver(node, item, attr="translate", pose_values=None):
    """向已有的 solver 追加一个驱动器物体。

    参数:
        node: rbfSolver 节点名。
        item: 物体名或完整 plug 名。
        attr: 只给了物体名时使用的属性名，默认 translate。
        pose_values: 可选的 double3 列表，长度必须与现有姿势数量一致，
            顺序对应 ``pose_indices(node)``。给出时用它逐个回填各姿势的样本
            值，代替默认的"当前值"。长度不匹配时抛出 ValueError。

    返回:
        实际使用的 input logical index。

    注意:
        必须给每一个已录制的姿势都回填一个样本值。RBF 的插值依赖各姿势在
        driver 空间中的距离，缺失的 poseInput 项会按 (0, 0, 0) 参与距离计算，
        这会把之前录好的所有姿势全部带歪。
        默认回填的是该物体的*当前*值：由于所有姿势拿到的样本值完全相同，
        这一维在距离计算中恒为常量差，不影响既有插值结果，即新 driver 加入
        时是"中性"的。之后需要逐个姿势
        （``apply_pose`` + ``update_pose``）给它录上真正的取值才会生效。
    """
    plug = _resolve_plug(item, attr)
    used = _used_driver_indices(node)
    index = (max(used) + 1) if used else 0

    poses = pose_indices(node)
    if pose_values is not None and len(pose_values) != len(poses):
        raise ValueError(
            "pose_values has {0} entries but the solver has {1} poses".format(
                len(pose_values), len(poses)))

    current = _plug_value(plug)
    for n, i in enumerate(poses):
        value = current if pose_values is None else pose_values[n]
        cmds.setAttr("{0}.pose[{1}].poseInput[{2}]".format(node, i, index),
                     value[0], value[1], value[2], type="double3")

    cmds.connectAttr(plug, "{0}.input[{1}]".format(node, index), force=True)
    return index


def add_driven(node, item, attr="translate", pose_values=None):
    """向已有的 solver 追加一个被驱动物体。

    参数:
        node: rbfSolver 节点名。
        item: 物体名或完整 plug 名。
        attr: 只给了物体名时使用的属性名，默认 translate。
        pose_values: 可选的 double3 列表，长度必须与现有姿势数量一致，
            顺序对应 ``pose_indices(node)``。长度不匹配时抛出 ValueError。

    返回:
        实际使用的 output logical index。

    注意:
        回填规则与 :func:`add_driver` 相同：每个已有姿势都必须写入样本值，
        缺失项会按 (0, 0, 0) 参与计算，导致该物体在所有姿势上都被拉回原点。
        默认把物体的当前值回填到全部姿势，因此接上线之后它不会突然跳动。
        之后再逐个姿势雕刻（``set_edit_mode`` -> ``apply_pose`` -> 摆姿势 ->
        ``update_pose``）。
        若此刻节点正处于 edit mode，output 是断开状态，不能直接连线，
        因此只把 (index, plug) 记入 meta，等退出 edit mode 时再接上。
    """
    plug = _resolve_plug(item, attr)
    used = _used_driven_indices(node)
    index = (max(used) + 1) if used else 0

    poses = pose_indices(node)
    if pose_values is not None and len(pose_values) != len(poses):
        raise ValueError(
            "pose_values has {0} entries but the solver has {1} poses".format(
                len(pose_values), len(poses)))

    current = _plug_value(plug)
    for n, i in enumerate(poses):
        value = current if pose_values is None else pose_values[n]
        cmds.setAttr("{0}.pose[{1}].poseOutput[{2}]".format(node, i, index),
                     value[0], value[1], value[2], type="double3")

    if is_edit_mode(node):
        # 此刻 output 处于断开状态 —— 先记入 meta，退出 edit mode 时再连线
        meta = _read_meta(node)
        meta.setdefault("driven", []).append([index, plug])
        _write_meta(node, meta)
    else:
        cmds.connectAttr("{0}.output[{1}]".format(node, index), plug,
                         force=True)
    return index


def remove_driver(node, index):
    """断开指定 ``index`` 的驱动器，并从每个姿势中删掉它的样本值。

    参数:
        node: rbfSolver 节点名。
        index: 要移除的 input logical index。

    返回:
        None。

    注意:
        除了断开连接，还会移除各姿势里对应的 ``poseInput`` 元素以及
        ``input`` 上的 multi 元素，避免残留项按 (0, 0, 0) 继续参与距离计算。
        清理后该 logical index 会重新变为可用。
    """
    plug = "{0}.input[{1}]".format(node, index)
    for src in cmds.listConnections(plug, plugs=True, source=True,
                                    destination=False) or []:
        cmds.disconnectAttr(src, plug)
    for i in pose_indices(node):
        cmds.removeMultiInstance(
            "{0}.pose[{1}].poseInput[{2}]".format(node, i, index), b=True)
    cmds.removeMultiInstance(plug, b=True)


def remove_driven(node, index):
    """断开指定 ``index`` 的被驱动物体，并从每个姿势中删掉它的目标值。

    参数:
        node: rbfSolver 节点名。
        index: 要移除的 output logical index。

    返回:
        None。

    注意:
        除了断开连接和移除各姿势的 ``poseOutput`` 元素，还会把 meta 中
        ``driven`` 列表里该下标的记录清掉，否则退出 edit mode 时会试图重新
        接回一个已经被移除的目标。只有列表确实发生变化时才回写 meta。
    """
    src = "{0}.output[{1}]".format(node, index)
    for dst in cmds.listConnections(src, plugs=True, source=False,
                                    destination=True) or []:
        cmds.disconnectAttr(src, dst)
    for i in pose_indices(node):
        cmds.removeMultiInstance(
            "{0}.pose[{1}].poseOutput[{2}]".format(node, i, index), b=True)

    meta = _read_meta(node)
    kept = [pair for pair in meta.get("driven", []) if pair[0] != index]
    if kept != meta.get("driven", []):
        meta["driven"] = kept
        _write_meta(node, meta)


def set_edit_mode(node, state):
    """进入（True）/ 退出（False）edit mode，即断开 / 接回被驱动物体。

    参数:
        node: rbfSolver 节点名。
        state: 真值表示进入 edit mode（断开 output 连接），
            假值表示退出 edit mode（按 meta 记录恢复连接）。

    返回:
        None。

    注意:
        录制姿势前必须断开 output。原因是：连线状态下被驱动物体正被节点
        自己驱动，其属性值完全由 solver 计算得出，此时无法手动摆动它们，
        录下来的 poseOutput 只是节点当前的插值结果，而不是想要的目标姿势
        —— 相当于把输出又喂回给自己，姿势永远录不进去。
        进入 edit mode 时会把断开的 (index, plug) 全部记入 meta，退出时据此
        恢复；重复进入 edit mode 会直接返回，避免把已经断开的状态记成空表
        而丢失恢复信息。退出时用 ``objExists`` 跳过已删除的 plug。
    """
    meta = _read_meta(node)
    state = bool(state)

    if state:
        if meta.get("editMode"):
            return
        stored = []
        for index, plug in driven_plugs(node):
            src = "{0}.output[{1}]".format(node, index)
            if cmds.isConnected(src, plug):
                cmds.disconnectAttr(src, plug)
            stored.append([index, plug])
        meta["driven"] = stored
        meta["editMode"] = True
    else:
        for index, plug in meta.get("driven", []):
            if cmds.objExists(plug):
                cmds.connectAttr("{0}.output[{1}]".format(node, index), plug,
                                 force=True)
        meta["driven"] = []
        meta["editMode"] = False

    _write_meta(node, meta)


def is_edit_mode(node):
    """查询节点当前是否处于 edit mode。

    参数:
        node: rbfSolver 节点名。

    返回:
        bool。True 表示 output 连接当前被 :func:`set_edit_mode` 主动断开。

    注意:
        状态来自 meta 中的 ``editMode`` 标记，而非实时检测连接情况；
        若绕过本模块手工改动了连线，该标记可能与场景实际状态不一致。
    """
    return bool(_read_meta(node).get("editMode"))


# ---------------------------------------------------------------------------
# 姿势
# ---------------------------------------------------------------------------

def add_pose(node, index=None):
    """把当前的 driver / driven 取值录制为一个新姿势。

    参数:
        node: rbfSolver 节点名。
        index: 可选的目标姿势 logical index。为 None 时取现有最大下标加一，
            没有任何姿势时用 0。显式给出已存在的下标会覆盖该姿势。

    返回:
        实际写入的姿势 logical index。

    注意:
        实际写入由 :func:`update_pose` 完成，因此同样应在 edit mode 下调用，
        否则录到的 poseOutput 只是 solver 自己算出的结果（会有警告提示）。
    """
    if index is None:
        used = pose_indices(node)
        index = (used[-1] + 1) if used else 0
    update_pose(node, index)
    return index


def update_pose(node, index, inputs=True, outputs=True):
    """用当前的 driver / driven 取值覆写指定 ``index`` 的姿势。

    参数:
        node: rbfSolver 节点名。
        index: 要覆写的姿势 logical index。
        inputs: 是否重写该姿势的 ``poseInput``（驱动器侧样本值）。
        outputs: 是否重写该姿势的 ``poseOutput``（被驱动侧目标值）。

    返回:
        None。

    注意:
        后期微调某个姿势时，通常应传 ``inputs=False``，只重录被驱动侧。
        原因是：驱动器若被锁定、被约束或被其他东西连接，:func:`apply_pose`
        就摆不回原来记录的姿势值，此时场景里驱动器的实际取值并不等于该姿势
        录制时的取值；如果连 ``poseInput`` 一起重写，就会把这个错误的当前值
        当成姿势输入写进去，把姿势的位置改错。传 ``inputs=False`` 可以让已
        录制的驱动器样本值保持原样不变。
        若 outputs 为真、存在被驱动 plug、但节点不在 edit mode，会发出警告：
        此时读到的被驱动值就是 solver 自己的输出结果。
    """
    driven = driven_plugs(node)
    if outputs and driven and not is_edit_mode(node):
        cmds.warning(
            "rbf_utils: '{0}' is not in edit mode - the recorded outputs will "
            "be the solver's own result. Call set_edit_mode(node, True) "
            "first.".format(node))

    if inputs:
        for j in _multi_indices("{0}.input".format(node)):
            value = cmds.getAttr("{0}.input[{1}]".format(node, j))[0]
            cmds.setAttr("{0}.pose[{1}].poseInput[{2}]".format(node, index, j),
                         value[0], value[1], value[2], type="double3")

    if not outputs:
        return

    for k, plug in driven:
        value = cmds.getAttr(plug)
        if isinstance(value, list):
            value = value[0]
        cmds.setAttr("{0}.pose[{1}].poseOutput[{2}]".format(node, index, k),
                     value[0], value[1], value[2], type="double3")


def delete_pose(node, index):
    """删除指定 ``index`` 的姿势。

    参数:
        node: rbfSolver 节点名。
        index: 要删除的姿势 logical index。

    返回:
        None。

    注意:
        整个 ``pose[index]`` 复合元素（含其下的 poseInput / poseOutput）会被
        一并移除。删除中间的姿势会在 logical index 中留下空洞，后续遍历必须
        使用 :func:`pose_indices` 而不能假设下标连续。
    """
    cmds.removeMultiInstance("{0}.pose[{1}]".format(node, index), b=True)


def apply_pose(node, index, drivers=True, driven=True):
    """把已录制的姿势推回场景物体上（用于检视或微调）。

    参数:
        node: rbfSolver 节点名。
        index: 要应用的姿势 logical index。
        drivers: 是否把 ``poseInput`` 写回驱动器 plug。
        driven: 是否把 ``poseOutput`` 写回被驱动 plug。

    返回:
        写入失败的 plug 名列表。plug 被锁定或已被其他东西驱动时无法 setAttr，
        这些 plug 会被收集进返回值，而不是被静默跳过，便于调用方察觉并处理。

    注意:
        返回列表非空意味着这些物体应用后并*没有*停在该姿势上。此时紧接着
        调用 :func:`update_pose` 必须传 ``inputs=False``，否则会把这些错误的
        当前值当作姿势样本录进去。
    """
    pose = "{0}.pose[{1}]".format(node, index)
    skipped = []

    if drivers:
        for j, plug in driver_plugs(node):
            value = cmds.getAttr("{0}.poseInput[{1}]".format(pose, j))[0]
            if not _set_plug(plug, value):
                skipped.append(plug)

    if driven:
        for k, plug in driven_plugs(node):
            value = cmds.getAttr("{0}.poseOutput[{1}]".format(pose, k))[0]
            if not _set_plug(plug, value):
                skipped.append(plug)

    return skipped


def _set_plug(plug, value):
    """尽力而为的 setAttr：遇到锁定 / 已连接的 plug 返回失败而不抛异常。

    参数:
        plug: 目标 plug 名，需为 double3 类型。
        value: 可按 ``value[0]``、``value[1]``、``value[2]`` 索引的三元组。

    返回:
        bool。True 表示写入成功；plug 不可设置（settable 为假）或 setAttr
        抛出 RuntimeError 时返回 False。

    注意:
        双重保护：先查 ``settable`` 拦掉锁定 / 被连接的情况，再用 try 捕获
        其余运行期错误，使批量应用姿势时不会因个别 plug 中断。
    """
    try:
        if not cmds.getAttr(plug, settable=True):
            return False
        cmds.setAttr(plug, value[0], value[1], value[2], type="double3")
        return True
    except RuntimeError:
        return False


def list_poses(node):
    """导出所有姿势的录制内容，便于调试查看。

    参数:
        node: rbfSolver 节点名。

    返回:
        ``[(index, [driverValues], [drivenValues]), ...]``。index 为姿势的
        logical index，两个列表分别是该姿势下各 ``poseInput`` /
        ``poseOutput`` 的取值，元素为 (x, y, z) 元组。

    注意:
        列表按各自 multi 上实际存在的 logical index 升序排列；由于下标可能
        稀疏，列表中的位置并不一定等于 logical index。
    """
    result = []
    for i in pose_indices(node):
        pose = "{0}.pose[{1}]".format(node, i)
        ins = [tuple(cmds.getAttr("{0}.poseInput[{1}]".format(pose, j))[0])
               for j in _multi_indices("{0}.poseInput".format(pose))]
        outs = [tuple(cmds.getAttr("{0}.poseOutput[{1}]".format(pose, k))[0])
                for k in _multi_indices("{0}.poseOutput".format(pose))]
        result.append((i, ins, outs))
    return result


def pose_weights(node):
    """读取每个姿势当前的混合权重。

    参数:
        node: rbfSolver 节点名。

    返回:
        ``[(index, weight), ...]``，weight 取自节点的
        ``outputWeight[index]``，反映驱动器处于当前取值时各姿势的影响比例。

    注意:
        读取会触发节点求值，因此得到的是驱动器当前状态下的权重；
        常用于检查姿势之间的过渡是否平滑或是否存在权重异常。
    """
    return [(i, cmds.getAttr("{0}.outputWeight[{1}]".format(node, i)))
            for i in pose_indices(node)]
