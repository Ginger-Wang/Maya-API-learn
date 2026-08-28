# -*- coding: utf-8 -*-
"""
UE 5.8 Control Rig 文本导出 -> 重建 JSON。

输入是在 Content Browser 里对 ControlRig 资产执行 Copy(Ctrl+C) 得到的文本，
例如 ``E:\\to-json.txt``。输出一份自描述的 JSON，供后续 UE Editor Python
脚本重建整个 Control Rig。

本脚本只用标准库，不需要 Unreal 环境，也不会修改任何资产。

导出文本的结构
--------------
UE 的对象导出分两段，二者是**并列的兄弟节点**，同名对象出现两次::

    Begin Object Class=ControlRigRuntimeAsset Name="CR_X"
       Begin Object Class=... Name="CR_X_EditorOnly"     <- 声明段：只有 Class 和层级
          ...
       End Object
       Begin Object Name="CR_X_EditorOnly"               <- 数据段：只有属性
          ...
       End Object
       PreviewSkeletalMesh="..."                         <- 资产级属性
    End Object

因此解析器必须按**路径**把两段合并：类型取自声明段，属性取自数据段。
不能建立全局的“名称 -> 类”映射，因为 ``Value`` / ``Type`` / ``Name`` 这类
Pin 名在文件里重复出现上百次。

已知的坑
--------
* ``Rig`` / ``*_SubGraph`` / ``RigVMFunctionLibraryEdGraph`` 是 ControlRigGraph，
  属于编辑器视觉镜像，节点与 RigVMGraph 一一重复，必须跳过。
* 聚合节点 (RigVMAggregateNode) 带 ``ContainedGraph`` 子图，需要递归。
* 节点名可以含空格 (``Set Transform``) 和中文 (``查找``)。连线路径按**第一个**
  点号切分，所以节点名不能含点号。
* 导出文本里的 ``Hierarchy`` 对象是空的，**不含任何 RigHierarchy 元素**。
  控制器/Null 的父子关系和 Transform 必须另外获取，见输出中的
  ``hierarchy.requires_external_source``。

用法
----
  python ue58_controlrig_text_to_json.py
  python ue58_controlrig_text_to_json.py E:\\to-json.txt
  python ue58_controlrig_text_to_json.py E:\\to-json.txt E:\\rebuild.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from typing import Dict, List, Optional, Tuple

# Windows 控制台默认 cp1252，直接 print 中文节点名会抛 UnicodeEncodeError。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

DEFAULT_SOURCE = r"H:\DBackUp\EFBack\F\VS-Code_Project\ClaudeCode_Spawn\to-json.txt"
DEFAULT_OUTPUT = r"H:\DBackUp\EFBack\F\VS-Code_Project\ClaudeCode_Spawn\controlrig_rebuild.json"

SCHEMA_NAME = "UE58ControlRigTextExport"
SCHEMA_VERSION = "2.0"

BEGIN_RE = re.compile(
    r'^(?P<indent>\s*)Begin Object'
    r'(?: Class=(?P<cls>\S+))?'
    r' Name="(?P<name>[^"]*)"'
)
END_RE = re.compile(r'^\s*End Object\s*$')
# 属性行：Key=Value 或 Key(3)=Value（UE 的数组属性）
PROP_RE = re.compile(r'^\s*(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?:\((?P<index>\d+)\))?=(?P<value>.*)$')
POSITION_RE = re.compile(r'\(X=(?P<x>[-+0-9.eE]+),Y=(?P<y>[-+0-9.eE]+)\)')
COLOR_RE = re.compile(
    r'\(R=(?P<r>[-+0-9.eE]+),G=(?P<g>[-+0-9.eE]+),'
    r'B=(?P<b>[-+0-9.eE]+),A=(?P<a>[-+0-9.eE]+)\)'
)
# ExportPath="/Script/X.Y'/Game/Path/Asset.Asset'"
OBJECT_PATH_RE = re.compile(r"'(?P<path>/[^']+)'")
# Variables=(Value=/Engine/Transient.PropertyBag_xxxx(A="1",B=2))
PROPERTY_BAG_RE = re.compile(r'PropertyBag_[0-9a-f]+\((?P<body>.*)\)\s*\)?\s*$')

# 只有这些类会被当作可重建的 RigVM 节点。
NODE_CLASS_SUFFIXES = (
    "RigVMUnitNode",
    "RigVMDispatchNode",
    "RigVMAggregateNode",
    "RigVMRerouteNode",
    "RigVMVariableNode",
    "RigVMFunctionEntryNode",
    "RigVMFunctionReturnNode",
    "RigVMFunctionReferenceNode",
    "RigVMCommentNode",
    "RigVMCollapseNode",
    "RigVMInvokeEntryNode",
)
# 编辑器视觉镜像，节点与 RigVMGraph 重复，解析时整棵跳过。
EDGRAPH_CLASS_SUFFIX = "ControlRigGraph"
RIGVM_GRAPH_SUFFIX = "RigVMGraph"

CONTROL_SUFFIX = "_ctrl"
# 动画通道 RigUnit 名 -> 通道类型。
ANIM_CHANNEL_TYPES = {
    "GetBoolAnimationChannel": "Bool",
    "GetFloatAnimationChannel": "Float",
    "GetIntAnimationChannel": "Integer",
    "GetVector2DAnimationChannel": "Vector2D",
    "GetVectorAnimationChannel": "Position",
    "GetRotatorAnimationChannel": "Rotator",
    "GetTransformAnimationChannel": "Transform",
}


# ============================== 文本解析 ==============================
class ExportObject:
    """导出文本中的一个 ``Begin Object`` 块。

    ``props`` 保存标量属性，``arrays`` 保存 ``Key(n)=`` 形式的数组属性并保持
    索引顺序。``children`` 里可能出现同名对象（声明段 + 数据段），由
    :func:`merge_passes` 负责合并。
    """

    __slots__ = ("name", "class_name", "export_path", "line", "props", "arrays", "children")

    def __init__(self, name: str, class_name: str, line: int):
        self.name = name
        self.class_name = class_name
        self.export_path = ""
        self.line = line
        self.props: Dict[str, str] = {}
        self.arrays: Dict[str, List[str]] = {}
        self.children: List["ExportObject"] = []

    def child(self, name: str) -> Optional["ExportObject"]:
        for item in self.children:
            if item.name == name:
                return item
        return None

    def suffix_is(self, suffix: str) -> bool:
        return self.class_name.endswith(suffix)


def unquote(value: str) -> str:
    """去掉 UE 属性值的外层引号并还原转义。"""
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
        value = value.replace('\\"', '"').replace("\\\\", "\\")
    return value


def parse_export(lines: List[str]) -> ExportObject:
    """把整份导出文本解析成一棵对象树。

    用显式栈而不是递归，避免深层 Pin 嵌套触发 Python 递归上限。
    """
    root = ExportObject("<root>", "", 0)
    stack: List[ExportObject] = [root]

    for number, line in enumerate(lines, 1):
        begin = BEGIN_RE.match(line)
        if begin:
            node = ExportObject(begin.group("name"), begin.group("cls") or "", number)
            path_match = OBJECT_PATH_RE.search(line)
            if path_match:
                node.export_path = path_match.group("path")
            stack[-1].children.append(node)
            stack.append(node)
            continue

        if END_RE.match(line):
            if len(stack) > 1:
                stack.pop()
            continue

        prop = PROP_RE.match(line)
        if prop and len(stack) > 1:
            current = stack[-1]
            key = prop.group("key")
            value = prop.group("value").rstrip()
            if prop.group("index") is None:
                current.props[key] = value
            else:
                current.arrays.setdefault(key, []).append(value)

    if len(stack) != 1:
        raise RuntimeError("导出文本的 Begin/End Object 不配对，可能被截断")
    return root


def merge_passes(node: ExportObject) -> ExportObject:
    """合并同名子对象：类型来自声明段，属性来自数据段。

    UE 先输出一遍纯结构（带 ``Class=``），再输出一遍纯属性（不带 ``Class=``）。
    两段在同一层是兄弟关系，按名称对齐即可。
    """
    merged: "OrderedDict[str, ExportObject]" = OrderedDict()
    for child in node.children:
        existing = merged.get(child.name)
        if existing is None:
            merged[child.name] = child
            continue
        # 声明段没有属性，数据段没有 Class，两边互补。
        if child.class_name and not existing.class_name:
            existing.class_name = child.class_name
        if child.export_path and not existing.export_path:
            existing.export_path = child.export_path
        existing.props.update(child.props)
        for key, values in child.arrays.items():
            existing.arrays.setdefault(key, []).extend(values)
        existing.children.extend(child.children)

    node.children = list(merged.values())
    for child in node.children:
        merge_passes(child)
    return node


# ============================== 结构提取 ==============================
def parse_position(raw: str) -> Dict[str, float]:
    match = POSITION_RE.search(raw or "")
    if not match:
        return {"x": 0.0, "y": 0.0}
    return {"x": float(match.group("x")), "y": float(match.group("y"))}


def parse_color(raw: str) -> Optional[Dict[str, float]]:
    match = COLOR_RE.search(raw or "")
    if not match:
        return None
    return {k: float(match.group(k)) for k in ("r", "g", "b", "a")}


def parse_bool(raw: Optional[str]) -> bool:
    return str(raw or "").strip().strip('"').lower() == "true"


def collect_pins(node: ExportObject) -> "OrderedDict[str, dict]":
    """递归收集节点下的 Pin，键为相对节点的点号路径（如 ``Value.0.Name``）。

    只走 RigVMPin 子对象；顺序按 ``SubPins(n)`` 声明的顺序，缺失时按出现顺序。
    """
    pins: "OrderedDict[str, dict]" = OrderedDict()

    def walk(owner: ExportObject, prefix: str) -> None:
        for pin in owner.children:
            if not pin.suffix_is("RigVMPin"):
                continue
            path = pin.name if not prefix else prefix + "." + pin.name
            direction = pin.props.get("Direction", "").strip()
            pins[path] = {
                "direction": direction,
                "cpp_type": unquote(pin.props.get("CPPType", "")),
                "cpp_type_object_path": unquote(pin.props.get("CPPTypeObjectPath", "")),
                "default_value": unquote(pin.props.get("DefaultValue", "")),
                "default_value_type": pin.props.get("DefaultValueType", "").strip(),
                "display_name": unquote(pin.props.get("DisplayName", "")),
                "custom_widget_name": unquote(pin.props.get("CustomWidgetName", "")),
                "is_dynamic_array": parse_bool(pin.props.get("bIsDynamicArray")),
                "is_expanded": parse_bool(pin.props.get("bIsExpanded")),
                "is_constant": parse_bool(pin.props.get("bIsConstant")),
                "is_lazy": parse_bool(pin.props.get("bIsLazy")),
                "has_default_value": "DefaultValue" in pin.props,
                "sub_pin_count": len(pin.arrays.get("SubPins", [])),
                "parent_path": prefix,
            }
            walk(pin, path)

    walk(node, "")
    return pins


def infer_method_name(resolved: str) -> str:
    """从 ResolvedFunctionName 里取出 RigVM 方法名，通常是 Execute。"""
    if "::" not in resolved:
        return "Execute"
    tail = resolved.rsplit("::", 1)[-1]
    # Dispatch 的签名形如 ``Struct::Pin:Type,Pin:Type``，冒号后不是方法名。
    return "Execute" if ":" in tail else tail


def parse_dispatch_types(resolved: str) -> "OrderedDict[str, str]":
    """解析 Dispatch 节点已固化的模板类型：``Pin:Type,Pin:Type`` -> {Pin: Type}。

    值里可能出现 ``TArray<FRigElementKey>`` 这种带尖括号的类型，所以只能在
    尖括号深度为 0 的逗号处切分。
    """
    result: "OrderedDict[str, str]" = OrderedDict()
    if "::" not in resolved:
        return result
    body = resolved.split("::", 1)[1]
    depth = 0
    current = ""
    parts: List[str] = []
    for char in body:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current:
        parts.append(current)

    for part in parts:
        if ":" not in part:
            continue
        pin, _, cpp_type = part.partition(":")
        result[pin.strip()] = cpp_type.strip()
    return result


def extract_graph(graph: ExportObject, path: str) -> dict:
    """提取一个 RigVMGraph 的节点、连线和子图（递归）。"""
    nodes: List[dict] = []
    links: List[dict] = []
    skipped: List[dict] = []

    for child in graph.children:
        if child.suffix_is("RigVMLink"):
            source = unquote(child.props.get("SourcePinPath", ""))
            target = unquote(child.props.get("TargetPinPath", ""))
            if source and target:
                links.append({"source": source, "target": target})
            continue

        if child.suffix_is(RIGVM_GRAPH_SUFFIX) or child.suffix_is(EDGRAPH_CLASS_SUFFIX):
            # 图对象只会作为节点的 ContainedGraph 出现，不在这里单独处理。
            continue

        if not any(child.suffix_is(s) for s in NODE_CLASS_SUFFIXES):
            if child.class_name:
                skipped.append({"name": child.name, "class": child.class_name})
            continue

        resolved = unquote(child.props.get("ResolvedFunctionName", ""))
        entry = {
            "name": child.name,
            "class": child.class_name,
            "class_short": child.class_name.rsplit(".", 1)[-1],
            "position": parse_position(child.props.get("Position", "")),
            "node_title": unquote(child.props.get("NodeTitle", "")),
            "node_color": parse_color(child.props.get("NodeColor", "")),
            "resolved_function_name": resolved,
            "template_notation": unquote(child.props.get("TemplateNotation", "")),
            "method_name": infer_method_name(resolved),
            "resolved_pin_types": parse_dispatch_types(resolved),
            "pin_order": [unquote(v).rsplit("'", 2)[-2] if "'" in v else unquote(v)
                          for v in child.arrays.get("Pins", [])],
            "pins": collect_pins(child),
        }
        if child.props.get("VariableGuid"):
            entry["variable_guid"] = child.props["VariableGuid"].strip()

        # 聚合节点 / 折叠节点带内嵌子图，递归下去。
        contained = None
        for sub in child.children:
            if sub.suffix_is(RIGVM_GRAPH_SUFFIX):
                contained = sub
                break
        if contained is not None:
            entry["contained_graph"] = extract_graph(
                contained, path + "|" + child.name + "|" + contained.name
            )

        nodes.append(entry)

    return {
        "graph_path": path,
        "graph_name": graph.name,
        "is_editable": parse_bool(graph.props.get("bEditable", "True")),
        "node_count": len(nodes),
        "link_count": len(links),
        "nodes": nodes,
        "links": links,
        "skipped_objects": skipped,
    }


def iter_all_nodes(graph: dict):
    """深度优先遍历图及其所有子图中的节点，产出 (图路径, 节点)。"""
    for node in graph["nodes"]:
        yield graph["graph_path"], node
        contained = node.get("contained_graph")
        if contained:
            for item in iter_all_nodes(contained):
                yield item


# ============================== 语义提取 ==============================
def extract_element_keys(graph: dict) -> List[dict]:
    """从 Pin 的 ``*.Type`` / ``*.Name`` 兄弟对中提取去重的 RigElementKey。

    这是本导出格式里**唯一**能拿到元素名的地方，因为 Hierarchy 对象是空的。
    """
    unique: Dict[Tuple[str, str], dict] = {}
    for graph_path, node in iter_all_nodes(graph):
        pins = node["pins"]
        for path, pin in pins.items():
            if not path.endswith(".Type"):
                continue
            name_pin = pins.get(path[: -len(".Type")] + ".Name")
            if name_pin is None:
                continue
            element_type = pin["default_value"].strip()
            element_name = name_pin["default_value"].strip()
            if not element_type or not element_name or element_name == "None":
                continue
            if element_type == "None":
                continue
            key = (element_type, element_name)
            record = unique.setdefault(key, {
                "type": element_type,
                "name": element_name,
                "referenced_by": [],
            })
            if len(record["referenced_by"]) < 8:
                record["referenced_by"].append(
                    node["name"] + "." + path[: -len(".Type")]
                )
    return sorted(unique.values(), key=lambda item: (item["type"], item["name"]))


def extract_item_arrays(graph: dict) -> List[dict]:
    """提取常量 ``TArray<FRigElementKey>`` 数组（Full_Bones / Full_Controls 之类）。

    重建时必须先 ``add_array_pin`` 建出元素，再逐个设置 Type / Name 叶子默认值，
    直接给父 Pin 塞字符串默认值是无效的。
    """
    element_re = re.compile(r"^Value\.(\d+)\.(Type|Name)$")
    arrays: List[dict] = []
    for graph_path, node in iter_all_nodes(graph):
        if "RigVMDispatch_Constant" not in node["resolved_function_name"]:
            continue
        if "TArray<FRigElementKey>" not in node["resolved_function_name"]:
            continue

        buckets: Dict[int, Dict[str, str]] = {}
        for path, pin in node["pins"].items():
            match = element_re.match(path)
            if match:
                buckets.setdefault(int(match.group(1)), {})[
                    match.group(2).lower()
                ] = pin["default_value"].strip()

        elements = []
        for index in sorted(buckets):
            item = buckets[index]
            elements.append({
                "index": index,
                "type": item.get("type", ""),
                "name": item.get("name", ""),
                "literal": '(Type={},Name="{}")'.format(
                    item.get("type", ""), item.get("name", "")
                ),
            })

        arrays.append({
            "graph_path": graph_path,
            "node": node["name"],
            "node_title": node["node_title"],
            "array_pin": "Value",
            "cpp_type": "TArray<FRigElementKey>",
            "element_count": len(elements),
            "elements": elements,
            "rebuild": "add_array_pin x N, then set Value.<i>.Type / Value.<i>.Name",
        })
    return arrays


def extract_animation_channels(graph: dict) -> List[dict]:
    """提取动画通道及其宿主控制器。

    在 UE 里动画通道本身也是 Control 元素，父级就是 ``owner_control``；
    重建时用 ``RigHierarchyController.add_animation_channel``，
    不要再当成普通 Control 建一遍。
    """
    found: Dict[Tuple[str, str], dict] = {}
    for graph_path, node in iter_all_nodes(graph):
        resolved = node["resolved_function_name"]
        channel_type = ""
        for marker, name in ANIM_CHANNEL_TYPES.items():
            if marker in resolved:
                channel_type = name
                break
        if not channel_type:
            continue

        owner = node["pins"].get("Control", {}).get("default_value", "").strip()
        channel = node["pins"].get("Channel", {}).get("default_value", "").strip()
        if not owner or not channel:
            continue

        record = found.setdefault((owner, channel), {
            "name": channel,
            "owner_control": owner,
            "control_type": channel_type,
            "source_nodes": [],
            "rebuild": "RigHierarchyController.add_animation_channel",
        })
        record["source_nodes"].append(node["name"])
    return sorted(found.values(), key=lambda item: (item["owner_control"], item["name"]))


def extract_metadata_usage(graph: dict) -> List[dict]:
    """记录图里用到的 RigHierarchy Metadata，供重建后自检。

    这些值是运行时写入的，重建脚本不需要预先创建，但知道有哪些键有助于排查。
    """
    usage: Dict[Tuple[str, str, str], dict] = {}
    for graph_path, node in iter_all_nodes(graph):
        resolved = node["resolved_function_name"]
        if "RigDispatch_GetMetadata" in resolved:
            mode = "get"
        elif "RigDispatch_SetMetadata" in resolved:
            mode = "set"
        else:
            continue

        pins = node["pins"]
        element = pins.get("Item.Name", {}).get("default_value", "").strip()
        element_type = pins.get("Item.Type", {}).get("default_value", "").strip()
        key = pins.get("Name", {}).get("default_value", "").strip()
        if not element or not key:
            continue
        record = usage.setdefault((element_type, element, key), {
            "element_type": element_type,
            "element_name": element,
            "metadata_key": key,
            "namespace": pins.get("NameSpace", {}).get("default_value", "").strip(),
            "modes": [],
            "source_nodes": [],
        })
        if mode not in record["modes"]:
            record["modes"].append(mode)
        record["source_nodes"].append(node["name"])
    return sorted(
        usage.values(), key=lambda i: (i["element_name"], i["metadata_key"])
    )


def extract_variables(asset: ExportObject, graph: dict) -> List[dict]:
    """合并两个来源的成员变量：资产级 PropertyBag 默认值 + VariableNode 类型。"""
    defaults: Dict[str, str] = {}
    raw = asset.props.get("Variables", "")
    bag = PROPERTY_BAG_RE.search(raw)
    if bag:
        # body 形如 ``ParticleComponentName="DynamicsParticle",Other=1``
        for piece in re.findall(r'(\w+)=("(?:[^"\\]|\\.)*"|[^,()]*)', bag.group("body")):
            defaults[piece[0]] = unquote(piece[1])

    variables: "OrderedDict[str, dict]" = OrderedDict()
    for graph_path, node in iter_all_nodes(graph):
        if not node["class"].endswith("RigVMVariableNode"):
            continue
        name = node["pins"].get("Variable", {}).get("default_value", "").strip()
        value_pin = node["pins"].get("Value", {})
        if not name:
            continue
        record = variables.setdefault(name, {
            "name": name,
            "cpp_type": value_pin.get("cpp_type", ""),
            "cpp_type_object_path": value_pin.get("cpp_type_object_path", ""),
            "default_value": defaults.get(name, ""),
            "accessor_nodes": [],
        })
        record["accessor_nodes"].append({
            "node": node["name"],
            "graph_path": graph_path,
            # 变量节点没有 ExecuteContext Pin 时是 Getter。
            "is_getter": "ExecuteContext" not in node["pins"],
        })

    # PropertyBag 里有但图上没有引用的变量也要保留。
    for name, value in defaults.items():
        variables.setdefault(name, {
            "name": name,
            "cpp_type": "",
            "cpp_type_object_path": "",
            "default_value": value,
            "accessor_nodes": [],
        })
    return list(variables.values())


def infer_hierarchy(element_keys: List[dict], channels: List[dict]) -> dict:
    """根据图中引用到的元素推断 RigHierarchy 重建方案。

    **重要**：文本导出里的 ``Hierarchy`` 对象是空壳，不含任何元素、父子关系或
    Transform。这里输出的只是**推断**，父子关系和 Transform 必须由
    ``preview_skeletal_mesh`` 的骨架、或 UE 内导出的 hierarchy JSON 补齐。
    """
    by_type: Dict[str, List[str]] = {}
    for item in element_keys:
        by_type.setdefault(item["type"], []).append(item["name"])

    bones = sorted(set(by_type.get("Bone", [])))
    bone_set = set(bones)
    channel_names = {c["name"] for c in channels}
    nulls = sorted(set(by_type.get("Null", [])))

    controls = []
    for name in sorted(set(by_type.get("Control", []))):
        if name in channel_names:
            # 动画通道也是 Control，但要走 add_animation_channel，跳过。
            continue
        matching_bone = ""
        if name.lower().endswith(CONTROL_SUFFIX):
            candidate = name[: -len(CONTROL_SUFFIX)]
            if candidate in bone_set:
                matching_bone = candidate
        controls.append({
            "name": name,
            "control_type": "EulerTransform",
            "matching_bone": matching_bone,
            # 没有真实层级数据，只能给出解析策略而不是确定的父级。
            "parent_strategy": (
                "mirror_matching_bone_parent" if matching_bone else "unresolved"
            ),
            "offset_strategy": (
                "copy_matching_bone_initial_local_transform"
                if matching_bone else "identity"
            ),
            "value_initial": "identity",
            "value_current": "identity",
            "confidence": "high" if matching_bone else "low",
        })

    return {
        "requires_external_source": True,
        "why": (
            "文本导出的 Hierarchy 对象为空，不含元素表、父子关系和 Transform。"
            "以下内容由图中引用到的 RigElementKey 反推，仅覆盖被图引用的元素。"
        ),
        "recommended_sources": [
            "preview_skeletal_mesh 指向的 SkeletalMesh（提供 Bone 及其 Initial Local Transform）",
            "在 UE Editor 内用 Python 读取 RigHierarchy 导出的元素表（提供 Control/Null 的真实父级与 Offset）",
        ],
        "control_suffix": CONTROL_SUFFIX,
        "bones": [{"name": n, "source": "imported_from_skeletal_mesh"} for n in bones],
        "controls": controls,
        "nulls": [{
            "name": n,
            "parent_strategy": "unresolved",
            "transform_strategy": "identity",
            "confidence": "low",
        } for n in nulls],
        "animation_channels": channels,
        "creation_order": [
            "导入 PreviewSkeletalMesh 的骨架，得到全部 Bone",
            "按骨骼深度创建 *_ctrl 控制器，父级镜像对应骨骼的父级控制器",
            "创建 Null（父级需外部数据确认）",
            "在 owner_control 下创建 Animation Channel",
            "用对应骨骼的 Initial Local Transform 设置控制器 Offset，Value 置 Identity",
        ],
    }


def extract_asset(root: ExportObject) -> Tuple[ExportObject, ExportObject, dict]:
    """定位运行时资产与 EditorOnly 资产，并读取资产级设置。"""
    runtime = None
    for child in root.children:
        if child.suffix_is("ControlRigRuntimeAsset"):
            runtime = child
            break
    if runtime is None:
        raise RuntimeError("没有找到 ControlRigRuntimeAsset，输入可能不是 Control Rig 导出文本")

    editor = None
    for child in runtime.children:
        if child.suffix_is("ControlRigEditorAsset"):
            editor = child
            break
    if editor is None:
        raise RuntimeError("没有找到 ControlRigEditorAsset，导出文本可能不完整")

    info = {
        "runtime_asset_name": runtime.name,
        "runtime_asset_class": runtime.class_name,
        "runtime_asset_path": runtime.export_path,
        "editor_asset_name": editor.name,
        "preview_skeletal_mesh": unquote(runtime.props.get("PreviewSkeletalMesh", "")),
        "shape_libraries": [unquote(v) for v in runtime.arrays.get("ShapeLibraries", [])],
        "supported_event_names": [
            unquote(v) for v in runtime.arrays.get("SupportedEventNames", [])
        ],
        "exposes_animatable_controls": parse_bool(
            runtime.props.get("bExposesAnimatableControls")
        ),
    }
    return runtime, editor, info


def build_diagnostics(graph: dict, arrays: List[dict], hierarchy: dict) -> dict:
    """重建前的体检：断链、未固化的模板类型、含点号的节点名等。"""
    node_names = set()
    class_counter: Counter = Counter()
    for _, node in iter_all_nodes(graph):
        node_names.add(node["name"])
        class_counter[node["class_short"]] += 1

    def check_links(current: dict, broken: List[dict]) -> None:
        local = {n["name"] for n in current["nodes"]}
        for link in current["links"]:
            source_node = link["source"].split(".", 1)[0]
            target_node = link["target"].split(".", 1)[0]
            missing = [n for n in (source_node, target_node) if n not in local]
            if missing:
                broken.append({
                    "graph_path": current["graph_path"],
                    "link": link,
                    "missing_nodes": missing,
                })
        for node in current["nodes"]:
            if node.get("contained_graph"):
                check_links(node["contained_graph"], broken)

    broken_links: List[dict] = []
    check_links(graph, broken_links)

    # 只有 Dispatch 节点需要固化模板类型。UnitNode 也可能带 TemplateNotation
    # （属于模板族），但它的 ResolvedFunctionName 已经是具体的 FRigUnit_X::Execute。
    unresolved_dispatch = [
        node["name"]
        for _, node in iter_all_nodes(graph)
        if node["class_short"] == "RigVMDispatchNode" and not node["resolved_pin_types"]
    ]
    # 聚合节点靠 ContainedGraph 而不是函数名，没有 ResolvedFunctionName 是正常的。
    missing_function = [
        node["name"]
        for _, node in iter_all_nodes(graph)
        if node["class_short"] == "RigVMUnitNode" and not node["resolved_function_name"]
    ]
    aggregates_without_graph = [
        node["name"]
        for _, node in iter_all_nodes(graph)
        if node["class_short"] in ("RigVMAggregateNode", "RigVMCollapseNode")
        and not node.get("contained_graph")
    ]
    dotted_names = sorted(n for n in node_names if "." in n)
    non_ascii_names = sorted(n for n in node_names if any(ord(c) > 127 for c in n))

    return {
        "node_class_counts": dict(class_counter),
        "total_nodes": sum(class_counter.values()),
        "broken_links": broken_links,
        "dispatch_nodes_without_resolved_types": unresolved_dispatch,
        "unit_nodes_without_resolved_function": missing_function,
        "aggregate_nodes_without_contained_graph": aggregates_without_graph,
        "empty_item_arrays": [a["node"] for a in arrays if not a["elements"]],
        # 连线路径按第一个点号切分，节点名含点号会解析错。
        "node_names_containing_dot": dotted_names,
        "node_names_with_non_ascii": non_ascii_names,
        "controls_without_matching_bone": [
            c["name"] for c in hierarchy["controls"] if not c["matching_bone"]
        ],
        "limitations": [
            "Hierarchy 元素表未随文本导出，控制器/Null 的父级与 Offset 无法从本文件获得。",
            "控制器的 Shape、颜色、Limit、Channel 排序等外观设置不在导出文本中。",
            "Bone 需要由 PreviewSkeletalMesh 导入，本文件只记录被图引用到的骨骼名。",
        ],
    }


# ============================== 主流程 ==============================
def convert(source: str) -> dict:
    with open(source, "r", encoding="utf-8", errors="strict") as stream:
        text = stream.read()
    lines = text.splitlines()

    root = merge_passes(parse_export(lines))
    runtime, editor, asset_info = extract_asset(root)

    model = editor.child("RigVMModel")
    if model is None or not model.suffix_is(RIGVM_GRAPH_SUFFIX):
        raise RuntimeError("EditorOnly 资产下没有 RigVMModel 图")

    graph = extract_graph(model, "RigVMModel")
    element_keys = extract_element_keys(graph)
    item_arrays = extract_item_arrays(graph)
    channels = extract_animation_channels(graph)
    metadata = extract_metadata_usage(graph)
    variables = extract_variables(runtime, graph)
    hierarchy = infer_hierarchy(element_keys, channels)

    return {
        "schema": {
            "name": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
            "source_format": "Unreal Engine 5.8 Control Rig text export",
        },
        "source": {
            "path": source,
            "line_count": len(lines),
            "character_count": len(text),
        },
        "asset": asset_info,
        "variables": variables,
        "graph": graph,
        "element_keys": element_keys,
        "item_arrays": item_arrays,
        "metadata_usage": metadata,
        "hierarchy": hierarchy,
        "rebuild_plan": [
            "创建或加载目标 ControlRigBlueprint，设置 PreviewSkeletalMesh。",
            "导入骨架，得到 hierarchy.bones 中列出的 Bone。",
            "按 hierarchy.creation_order 建 Null、Control 和 Animation Channel。",
            "创建 variables 中的成员变量并写入 default_value。",
            "取得 RigVMController，先按 graph.nodes 建节点（Unit 用 resolved_function_name，Dispatch 用 template_notation）。",
            "对 Dispatch 节点按 resolved_pin_types 固化模板类型。",
            "对 item_arrays 先 add_array_pin 建元素，再设置每个叶子 Pin 的默认值。",
            "设置其余 Pin 默认值，跳过 Direction=Hidden 的缓存 Pin 和 Output Pin。",
            "递归处理 contained_graph（聚合节点子图）。",
            "所有节点和数组 Pin 就位后再建 graph.links。",
            "编译、验证 diagnostics 中的告警项，最后只保存顶层 Runtime Asset。",
        ],
        "diagnostics": build_diagnostics(graph, item_arrays, hierarchy),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把 UE 5.8 Control Rig 导出文本转成重建用 JSON。"
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE, help="导出的 .txt")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT, help="写出的 .json")
    parser.add_argument("--compact", action="store_true", help="输出紧凑 JSON")
    parser.add_argument("--dry-run", action="store_true", help="只打印摘要，不写文件")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        data = convert(args.source)
    except FileNotFoundError:
        print("ERROR: 找不到输入文件: {}".format(args.source), file=sys.stderr)
        return 2
    except UnicodeDecodeError as error:
        print("ERROR: 输入文件不是 UTF-8: {}".format(error), file=sys.stderr)
        return 2
    except RuntimeError as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1

    diag = data["diagnostics"]
    graph = data["graph"]
    print("资产      : {} ({})".format(
        data["asset"]["runtime_asset_name"], data["asset"]["runtime_asset_path"]))
    print("骨骼网格  : {}".format(data["asset"]["preview_skeletal_mesh"] or "(未设置)"))
    print("主图      : {} 节点 / {} 连线".format(graph["node_count"], graph["link_count"]))
    print("含子图共  : {} 节点".format(diag["total_nodes"]))
    print("元素      : Bone {} / Control {} / Null {} / 动画通道 {}".format(
        len(data["hierarchy"]["bones"]), len(data["hierarchy"]["controls"]),
        len(data["hierarchy"]["nulls"]), len(data["hierarchy"]["animation_channels"])))
    print("变量      : {}   常量数组: {}".format(
        len(data["variables"]), len(data["item_arrays"])))

    for label, items in (
        ("断链", diag["broken_links"]),
        ("模板类型未固化", diag["dispatch_nodes_without_resolved_types"]),
        ("Unit 缺少函数名", diag["unit_nodes_without_resolved_function"]),
        ("聚合节点缺子图", diag["aggregate_nodes_without_contained_graph"]),
        ("空常量数组", diag["empty_item_arrays"]),
        ("节点名含点号", diag["node_names_containing_dot"]),
        ("控制器无匹配骨骼", diag["controls_without_matching_bone"]),
    ):
        if items:
            print("WARN {}: {}".format(label, items if len(items) < 8 else
                                       str(items[:8]) + " ...共{}项".format(len(items))))

    if args.dry_run:
        print("dry-run: 未写出文件")
        return 0

    try:
        with open(args.output, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False,
                      indent=None if args.compact else 2)
    except OSError as error:
        print("ERROR: 写出失败: {}".format(error), file=sys.stderr)
        return 1

    print("JSON: {}".format(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
