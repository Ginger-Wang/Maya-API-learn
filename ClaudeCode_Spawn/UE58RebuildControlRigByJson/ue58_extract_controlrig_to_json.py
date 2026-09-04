# -*- coding: utf-8 -*-
"""
UE 5.8 Control Rig 导出文本 -> 重建 JSON 提取器。

用途
----
解析 UE 5.8 Control Rig 导出文本，例如 E:\\to-json.txt，并输出结构化 JSON，
其中包含重建 Control Rig 所需的关键信息：

- Runtime/editor asset metadata
- RigVM nodes, positions, resolved functions and template notations
- Pin types, object paths, defaults and array structure
- RigVM links
- ItemArray dynamic elements
- Variables
- Referenced controls and nulls
- Bool/Float animation channels and their owner controls
- Inferred control hierarchy based on imported-bone hierarchy
- Correct transform reconstruction instructions
- Missing/unsupported/ambiguous data diagnostics

本提取器不需要 Unreal Python 模块，可以使用标准 Python 3 运行，也不会修改
任何 Unreal 资产。输出的 JSON 供后续 UE Editor 重建脚本使用。

用法
----
  python ue58_extract_controlrig_to_json.py
  python ue58_extract_controlrig_to_json.py E:\\to-json.txt
  python ue58_extract_controlrig_to_json.py E:\\to-json.txt E:\\controlrig_rebuild.json
"""

from __future__ import annotations

import argparse
import cmd
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_SOURCE = r"E:\\to-json.txt"
DEFAULT_OUTPUT = r"E:\\CR_SKM_WaterUP_controlrig_rebuild_data.json"
# JSON Schema 版本。后续修改输出字段时应同步提升此版本号。
SCHEMA_VERSION = "1.0"
# 通过控制器名称后缀反推对应骨骼名称，例如 Bone_01_ctrl -> Bone_01。
CONTROL_SUFFIX = "_ctrl"

BEGIN_RE = re.compile(
    r'^\s*Begin Object(?: Class=(?P<class>\S+))? Name="(?P<name>[^"]+)"'
)
END_RE = re.compile(r'^\s*End Object\s*$')
PROP_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$')
POSITION_RE = re.compile(r'\(X=([-+0-9.eE]+),Y=([-+0-9.eE]+)\)')
EXPORT_ASSET_RE = re.compile(
    r"ExportPath=\"[^']*'(?P<object_path>/Game/[^']+)'\""
)

NODE_CLASS_SUFFIXES = (
    "RigVMUnitNode",
    "RigVMDispatchNode",
    "RigVMAggregateNode",
    "RigVMRerouteNode",
    "RigVMVariableNode",
    "RigVMCommentNode",
    "RigVMFunctionEntryNode",
    "RigVMFunctionReturnNode",
    "RigVMFunctionReferenceNode",
)


# ------------------------- 解析结果数据结构 -------------------------
# 使用数据类保存中间结果，避免在解析函数之间传递难以维护的裸元组。
@dataclass
class PinRecord:
    path: str
    direction: str = ""
    cpp_type: str = ""
    cpp_type_object: str = ""
    cpp_type_object_path: str = ""
    default_value: str = ""
    custom_widget_name: str = ""
    is_dynamic_array: bool = False
    is_constant: bool = False
    is_expanded: bool = False
    parent_path: str = ""
    children: List[str] = field(default_factory=list)


@dataclass
class NodeRecord:
    name: str
    class_name: str
    position: Tuple[float, float] = (0.0, 0.0)
    resolved_function_name: str = ""
    template_notation: str = ""
    node_title: str = ""
    method_name: str = "Execute"
    pins: Dict[str, PinRecord] = field(default_factory=dict)


@dataclass
class LinkRecord:
    source: str
    target: str


@dataclass
class ObjectBlock:
    class_name: str
    name: str
    lines: List[str]


def unquote(value: str) -> str:
    """移除 Unreal 属性值的外层引号，并还原常见转义字符。"""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
        value = value.replace('\\"', '"').replace('\\\\', '\\')
    return value


def read_object_block(lines: List[str], start: int) -> Tuple[List[str], int]:
    """读取一个完整的 ``Begin Object`` 块。

    UE 导出文本允许对象嵌套对象，例如节点包含 Pin、Pin 又包含子 Pin。
    深度计数可以准确找到与起始对象对应的 ``End Object``。
    """
    output: List[str] = []
    depth = 0
    for index in range(start, len(lines)):
        line = lines[index]
        if BEGIN_RE.match(line):
            depth += 1
        if depth:
            output.append(line)
        if END_RE.match(line):
            depth -= 1
            if depth == 0:
                return output, index + 1
    raise ValueError("Unclosed Begin Object at line {}".format(start + 1))


def direct_children(block: List[str]) -> List[ObjectBlock]:
    """返回对象块的直接子对象，不展开更深层对象。"""
    result: List[ObjectBlock] = []
    index = 1
    while index < len(block) - 1:
        match = BEGIN_RE.match(block[index])
        if not match:
            index += 1
            continue
        child, next_index = read_object_block(block, index)
        result.append(
            ObjectBlock(match.group("class") or "", match.group("name"), child)
        )
        index = next_index
    return result


def direct_properties(block: List[str]) -> Dict[str, str]:
    """读取对象本身的属性，忽略嵌套子对象中的同名属性。"""
    result: Dict[str, str] = {}
    depth = 0
    for line in block[1:-1]:
        if BEGIN_RE.match(line):
            depth += 1
            continue
        if END_RE.match(line):
            depth -= 1
            continue
        if depth == 0:
            match = PROP_RE.match(line)
            if match:
                result[match.group(1)] = unquote(match.group(2))
    return result


def build_class_map(lines: List[str]) -> Dict[str, str]:
    """建立对象名称到 Unreal 类名的映射。

    部分导出对象省略了 ``Class=``，后续可利用同名对象的完整声明补全类别。
    """
    result: Dict[str, str] = {}
    for line in lines:
        match = BEGIN_RE.match(line)
        if match and match.group("class"):
            result.setdefault(match.group("name"), match.group("class"))
    return result


def find_configured_model(lines: List[str]) -> List[str]:
    """从可能存在的多个 RigVMModel 中选择配置最完整的模型。

    评分依据是已解析的函数名、模板记法和连线属性数量，而不是简单取第一个
    匹配项，因为导出文件可能同时包含运行时模型和编辑器缓存模型。
    """
    candidates: List[Tuple[int, List[str]]] = []
    for index, line in enumerate(lines):
        match = BEGIN_RE.match(line)
        if not match or match.group("name") != "RigVMModel":
            continue
        block, _ = read_object_block(lines, index)
        score = (
            sum("SourcePinPath=" in item for item in block)
            + sum("ResolvedFunctionName=" in item for item in block)
            + sum("TemplateNotation=" in item for item in block)
        )
        candidates.append((score, block))
    if not candidates:
        raise ValueError("RigVMModel was not found")
    score, block = max(candidates, key=lambda pair: pair[0])
    if score == 0:
        raise ValueError("RigVMModel exists but has no configured graph data")
    return block


def parse_pin_tree(node_block: List[str], class_map: Dict[str, str]) -> Dict[str, PinRecord]:
    """递归解析节点下的 Pin 树。

    Pin 使用点号路径表示层级，例如 ``Value.0.Name``。保存完整路径后，
    重建器可以直接据此设置嵌套 Pin 的默认值和动态数组元素。
    """
    result: Dict[str, PinRecord] = {}

    def walk(block: List[str], parent_path: str = "") -> None:
        for child in direct_children(block):
            class_name = child.class_name or class_map.get(child.name, "")
            if class_name and not class_name.endswith("RigVMPin"):
                continue
            path = child.name if not parent_path else parent_path + "." + child.name
            props = direct_properties(child.lines)
            record = PinRecord(
                path=path,
                direction=props.get("Direction", ""),
                cpp_type=props.get("CPPType", ""),
                cpp_type_object=props.get("CPPTypeObject", ""),
                cpp_type_object_path=props.get("CPPTypeObjectPath", ""),
                default_value=props.get("DefaultValue", ""),
                custom_widget_name=props.get("CustomWidgetName", ""),
                is_dynamic_array=props.get("bIsDynamicArray") == "True",
                is_constant=props.get("bIsConstant") == "True",
                is_expanded=props.get("bIsExpanded") == "True",
                parent_path=parent_path,
            )
            result[path] = record
            if parent_path and parent_path in result:
                result[parent_path].children.append(path)
            walk(child.lines, path)

    walk(node_block)
    return result


def infer_method_name(resolved: str) -> str:
    """从 ResolvedFunctionName 中提取 RigVM 方法名，通常为 Execute。"""
    if "::" not in resolved:
        return "Execute"
    method = resolved.rsplit("::", 1)[-1]
    return "Execute" if ":" in method else method


def parse_graph(lines: List[str]) -> Tuple[List[NodeRecord], List[LinkRecord]]:
    """解析 RigVMModel 中的节点和连线。

    节点只保留重建相关的类型；RigVMLink 被转换为源 Pin 到目标 Pin 的简单
    记录。这样生成的 JSON 不依赖 Unreal 内部对象路径。
    """
    class_map = build_class_map(lines)
    model = find_configured_model(lines)
    nodes: List[NodeRecord] = []
    links: List[LinkRecord] = []

    for child in direct_children(model):
        props = direct_properties(child.lines)
        class_name = child.class_name or class_map.get(child.name, "")
        source = props.get("SourcePinPath", "")
        target = props.get("TargetPinPath", "")

        # Link 对象没有可重建的节点 Pin，单独保存为 source -> target 关系。
        if class_name.endswith("RigVMLink") or (source and target):
            if source and target:
                links.append(LinkRecord(source, target))
            continue

        # 忽略控制器、缓存、编辑器图节点等与 RigVMModel 无关的对象。
        if not any(class_name.endswith(suffix) for suffix in NODE_CLASS_SUFFIXES):
            continue

        position = (0.0, 0.0)
        match = POSITION_RE.search(props.get("Position", ""))
        if match:
            position = (float(match.group(1)), float(match.group(2)))

        resolved = props.get("ResolvedFunctionName", "")
        nodes.append(
            NodeRecord(
                name=child.name,
                class_name=class_name,
                position=position,
                resolved_function_name=resolved,
                template_notation=props.get("TemplateNotation", ""),
                node_title=props.get("NodeTitle", ""),
                method_name=infer_method_name(resolved),
                pins=parse_pin_tree(child.lines, class_map),
            )
        )

    return nodes, links


def parse_asset_metadata(text: str, lines: List[str]) -> Dict[str, object]:
    """提取运行时资产、EditorOnly 资产和源文件统计信息。"""
    runtime_class = ""
    runtime_name = ""
    runtime_export_path = ""
    editor_asset_name = ""

    for line in lines:
        match = BEGIN_RE.match(line)
        if not match:
            continue
        class_name = match.group("class") or ""
        # 运行时资产保存最终 VM；EditorOnly 资产保存可编辑的节点图。
        if class_name.endswith("ControlRigRuntimeAsset") and not runtime_class:
            runtime_class = class_name
            runtime_name = match.group("name")
            path_match = EXPORT_ASSET_RE.search(line)
            if path_match:
                runtime_export_path = path_match.group("object_path")
        elif class_name.endswith("ControlRigEditorAsset") and not editor_asset_name:
            editor_asset_name = match.group("name")

    # 某些导出文本会省略标准资产头，使用宽松正则提供路径兜底。
    if not runtime_export_path:
        match = re.search(r"(/Game/[A-Za-z0-9_./]+)\.[A-Za-z0-9_]+", text)
        if match:
            runtime_export_path = match.group(1)

    return {
        "runtime_asset_class": runtime_class,
        "runtime_asset_name": runtime_name,
        "runtime_asset_path": runtime_export_path,
        "editor_asset_name": editor_asset_name,
        "source_character_count": len(text),
        "source_line_count": len(lines),
    }


def parse_element_keys(nodes: List[NodeRecord]) -> List[Dict[str, str]]:
    """从 Pin 的 Type/Name 子字段中提取去重后的 RigElementKey。"""
    unique = {}
    for node in nodes:
        for path, pin in node.pins.items():
            if not path.endswith(".Type") or not pin.default_value:
                continue
            name_path = path[:-5] + ".Name"
            name_pin = node.pins.get(name_path)
            if not name_pin or not name_pin.default_value:
                continue
            # Type + Name 共同决定一个 RigElementKey，使用元组去重。
            key = (pin.default_value, name_pin.default_value)
            unique.setdefault(
                key,
                {
                    "type": pin.default_value,
                    "name": name_pin.default_value,
                    "first_source": node.name + "." + path.rsplit(".", 1)[0],
                },
            )
    return sorted(unique.values(), key=lambda item: (item["type"], item["name"]))


def parse_item_arrays(nodes: List[NodeRecord]) -> List[Dict[str, object]]:
    """提取常量 RigElementKey 数组及其元素默认值。

    这些数组通常对应 Full_Bones、Full_Controls 等动态常量节点，重建时必须
    先创建数组子 Pin，再设置每个元素的 Type 和 Name。
    """
    arrays: List[Dict[str, object]] = []
    for node in nodes:
        signature = node.resolved_function_name + " " + node.template_notation
        # 只提取 RigElementKey 常量数组，避免把其他动态数组交给重建器。
        is_constant_array = (
            "TArray<FRigElementKey>" in signature
            and "RigVMDispatch_Constant" in signature
        )
        if not is_constant_array:
            continue
        elements: Dict[int, Dict[str, str]] = defaultdict(dict)
        for path, pin in node.pins.items():
            match = re.fullmatch(r"Value\.(\d+)\.(Type|Name)", path)
            if match:
                elements[int(match.group(1))][match.group(2).lower()] = pin.default_value
        ordered = []
        for index in sorted(elements):
            ordered.append(
                {
                    "index": index,
                    "type": elements[index].get("type", ""),
                    "name": elements[index].get("name", ""),
                    "default_value": '(Type={},Name="{}")'.format(
                        elements[index].get("type", ""),
                        elements[index].get("name", ""),
                    ),
                }
            )
        arrays.append(
            {
                "node": node.name,
                "pin": node.name + ".Value",
                "cpp_type": node.pins.get("Value", PinRecord("Value")).cpp_type,
                "element_count": len(ordered),
                "elements": ordered,
                "rebuild_operation": "add_array_pin_then_set_leaf_defaults",
            }
        )
    return arrays


def parse_animation_channels(nodes: List[NodeRecord]) -> List[Dict[str, str]]:
    """提取 Bool/Float Animation Channel 及其所属控制器。"""
    result = {}
    for node in nodes:
        resolved = node.resolved_function_name
        channel_type = ""
        # 根据函数名区分 Bool 和 Float 通道；其他 Animation Channel 暂不推断。
        if "GetBoolAnimationChannel" in resolved:
            channel_type = "Bool"
        elif "GetFloatAnimationChannel" in resolved:
            channel_type = "Float"
        if not channel_type:
            continue
        owner = node.pins.get("Control", PinRecord("Control")).default_value
        name = node.pins.get("Channel", PinRecord("Channel")).default_value
        if owner and name:
            result[(owner, name, channel_type)] = {
                "owner_control": owner,
                "name": name,
                "control_type": channel_type,
                "source_node": node.name,
                "rebuild_operation": "RigHierarchyController.add_animation_channel",
            }
    return sorted(result.values(), key=lambda item: (item["owner_control"], item["name"]))


def parse_variables(nodes: List[NodeRecord]) -> List[Dict[str, str]]:
    """提取 RigVM VariableNode 的名称、类型、默认值和读写方向。"""
    result = []
    for node in nodes:
        if not node.class_name.endswith("RigVMVariableNode"):
            continue
        variable = node.pins.get("Variable")
        value = node.pins.get("Value")
        # ExecuteContext 是否存在可用来判断变量节点是 Getter 还是 Setter。
        result.append(
            {
                "node": node.name,
                "name": variable.default_value if variable else "",
                "cpp_type": value.cpp_type if value else "",
                "cpp_type_object_path": value.cpp_type_object_path if value else "",
                "default_value": value.default_value if value else "",
                "is_getter": "ExecuteContext" not in node.pins,
            }
        )
    return result


def infer_hierarchy(
    element_keys: List[Dict[str, str]],
    arrays: List[Dict[str, object]],
    channels: List[Dict[str, str]],) -> Dict[str, object]:
    """根据导出图中的元素引用生成层级重建规则。

    该类文本导出通常不包含完整的 RigHierarchy 元素表，因此不能直接恢复
    每个控制器的父级。脚本输出规则：``*_ctrl`` 通过对应骨骼的父级控制器
    解析，proxy_ctrl 和 proxy_buffer 则使用显式命名规则。
    """
    control_names = {
        item["name"] for item in element_keys if item["type"] == "Control"
    }
    null_names = {
        item["name"] for item in element_keys if item["type"] == "Null"
    }
    for array in arrays:
        for item in array["elements"]:
            if item["type"] == "Control":
                control_names.add(item["name"])
            elif item["type"] == "Null":
                null_names.add(item["name"])
    for channel in channels:
        control_names.add(channel["owner_control"])

    # 这类文本导出不序列化完整 RigHierarchy 元素列表，因此父级关系只能输出
    # 规则，由 UE 重建脚本在导入骨骼后结合实际层级解析。
    controls = []
    for name in sorted(control_names):
        matching_bone = ""
        if name.lower().endswith(CONTROL_SUFFIX.lower()):
            matching_bone = name[:-len(CONTROL_SUFFIX)]
        parent_rule = "root"
        if name == "proxy_ctrl" and "proxy_offset" in null_names:
            parent_rule = "explicit:proxy_offset"
        elif matching_bone:
            parent_rule = "matching_bone_parent_control"
        controls.append(
            {
                "name": name,
                "element_type": "Control",
                "control_type": "EulerTransform",
                "matching_bone": matching_bone,
                "parent_rule": parent_rule,
                "transform_rule": {
                    "offset_initial": "matching_bone.initial_local_transform",
                    "offset_current": "matching_bone.initial_local_transform",
                    "value_initial": "identity",
                    "value_current": "identity",
                    "space": "local_parent_space",
                },
            }
        )

    nulls = []
    for name in sorted(null_names):
        parent_rule = "root"
        if name == "proxy_buffer" and "proxy_ctrl" in control_names:
            parent_rule = "explicit:proxy_ctrl"
        nulls.append(
            {
                "name": name,
                "element_type": "Null",
                "parent_rule": parent_rule,
                "transform_rule": "identity_unless_source_hierarchy_is_available",
            }
        )

    return {
        "control_suffix": CONTROL_SUFFIX,
        "controls": controls,
        "nulls": nulls,
        "animation_channels": channels,
        "parent_resolution_order": [
            "create root nulls",
            "create controls ordered by matching imported-bone depth",
            "create animation channels under owner_control",
            "create child nulls such as proxy_buffer",
        ],
        "important_transform_note": (
            "Control offsets are local to the control parent. Use the matching "
            "bone Initial Local Transform, not its Global Transform."
        ),
    }


def node_to_dict(node: NodeRecord) -> Dict[str, object]:
    """将 NodeRecord 转换为可被 json.dump 序列化的字典。"""
    data = asdict(node)
    data["position"] = {"x": node.position[0], "y": node.position[1]}
    data["pins"] = {path: asdict(pin) for path, pin in node.pins.items()}
    return data


def diagnostics(
    nodes: List[NodeRecord],
    links: List[LinkRecord],
    arrays: List[Dict[str, object]],
    hierarchy: Dict[str, object],
) -> Dict[str, object]:
    """生成重建前诊断信息，包括断链、Wildcard 和空数组。"""
    node_names = {node.name for node in nodes}
    # 只检查端点节点是否存在，Pin 类型兼容性需要在 UE RigVM 中最终验证。
    broken_links = []
    for link in links:
        source_node = link.source.split(".", 1)[0]
        target_node = link.target.split(".", 1)[0]
        if source_node not in node_names or target_node not in node_names:
            broken_links.append(asdict(link))

    # Dispatch 签名含冒号时通常代表尚未固定的模板类型，重建时需要解析。
    wildcard_nodes = [
        node.name
        for node in nodes
        if "DISPATCH_" in node.resolved_function_name
        and ":" in node.resolved_function_name.split("::", 1)[-1]
    ]
    missing_resolved = [
        node.name
        for node in nodes
        if node.class_name.endswith(("RigVMUnitNode", "RigVMAggregateNode"))
        and not node.resolved_function_name
    ]
    empty_arrays = [array["node"] for array in arrays if not array["elements"]]

    return {
        "node_class_counts": dict(Counter(node.class_name for node in nodes)),
        "broken_link_endpoints": broken_links,
        "dispatch_nodes_requiring_type_resolution": wildcard_nodes,
        "unit_or_aggregate_nodes_without_resolved_function": missing_resolved,
        "empty_item_arrays": empty_arrays,
        "limitations": [
            "The export does not contain a complete serialized RigHierarchy element table.",
            "Control shape color, custom shape transform and limits may be unavailable.",
            "Control parents are resolved from the imported bone hierarchy during rebuild.",
            "Null transforms default to identity unless another source supplies them.",
        ],
    }


def extract(source_path: Path) -> Dict[str, object]:
    """执行完整提取流程并返回最终 JSON 数据结构。"""
    text = source_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    # 先解析图，再用节点信息派生数组、通道、变量和层级规则。
    nodes, links = parse_graph(lines)
    element_keys = parse_element_keys(nodes)
    arrays = parse_item_arrays(nodes)
    channels = parse_animation_channels(nodes)
    hierarchy = infer_hierarchy(element_keys, arrays, channels)

    return {
        "schema": {
            "name": "UE58ControlRigReconstructionData",
            "version": SCHEMA_VERSION,
            "source_format": "Unreal text export",
        },
        "source": {
            "path": str(source_path),
            "file_name": source_path.name,
            "size_bytes": source_path.stat().st_size,
        },
        "asset": parse_asset_metadata(text, lines),
        "graph": {
            "model_name": "RigVMModel",
            "node_count": len(nodes),
            "link_count": len(links),
            "nodes": [node_to_dict(node) for node in nodes],
            "links": [asdict(link) for link in links],
            "variables": parse_variables(nodes),
        },
        "hierarchy": hierarchy,
        "element_keys": element_keys,
        "item_arrays": arrays,
        # 这是给后续 UE 重建脚本使用的有序操作清单，而不是执行器。
        "rebuild_plan": [
            "Load ControlRigRuntimeAsset and obtain its ControlRigEditorAsset.",
            "Obtain the default RigVMModel and RigVMController.",
            "Create RigVM nodes before applying defaults and links.",
            "Resolve Dispatch wildcard types from resolved_function_name.",
            "Create dynamic array elements with add_array_pin before setting leaf defaults.",
            "Apply pin defaults, skipping runtime cache pins.",
            "Create RigVM links after all endpoint nodes and array pins exist.",
            "Obtain RigHierarchy and RigHierarchyController.",
            "Resolve *_ctrl parent relationships from imported-bone parent relationships.",
            "Create Nulls, transform Controls and Animation Channels in dependency order.",
            "Copy matching bone Initial Local Transform to control Initial/Current Offset.",
            "Set control Initial/Current local values to identity.",
            "Compile, validate, then save the top-level Runtime Asset only.",
        ],
        "diagnostics": diagnostics(nodes, links, arrays, hierarchy),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数，支持默认输入输出路径和紧凑 JSON。"""
    parser = argparse.ArgumentParser(
        description="Extract UE 5.8 Control Rig reconstruction data to JSON."
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE)
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--compact", action="store_true", help="Write compact JSON instead of indented JSON."
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """读取源文件、提取数据、写出 JSON，并返回命令行退出码。"""
    args = parse_args(argv)
    source = Path(args.source)
    output = Path(args.output)

    if not source.is_file():
        print("ERROR: source file does not exist: {}".format(source), file=sys.stderr)
        return 2

    try:
        # 解析阶段完全在标准 Python 中完成，因此可以在不启动 Unreal 的情况下检查输出。
        data = extract(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as stream:
            json.dump(
                data,
                stream,
                ensure_ascii=False,
                indent=None if args.compact else 2,
            )
        print(
            "Extracted nodes={nodes}, links={links}, controls={controls}, arrays={arrays}".format(
                nodes=data["graph"]["node_count"],
                links=data["graph"]["link_count"],
                controls=len(data["hierarchy"]["controls"]),
                arrays=len(data["item_arrays"]),
            )
        )
        print("JSON: {}".format(output))
        return 0
    except Exception as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# cmd
# python ue58_extract_controlrig_to_json.py E:\to-json.txt E:\controlrig_rebuild_data.json
