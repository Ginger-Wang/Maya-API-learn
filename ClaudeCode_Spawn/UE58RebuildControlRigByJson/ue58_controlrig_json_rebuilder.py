# -*- coding: utf-8 -*-
"""UE 5.8 JSON 驱动的 Control Rig 重建器。

输入 Schema 为 ``UE58ControlRigReconstructionData v1.0``，由
``ue58_extract_controlrig_to_json.py`` 生成。

脚本必须在 Unreal Editor Python 环境中运行。首次运行应保持
``SAVE_AFTER_SUCCESS=False``，先检查 JSON 报告和编辑器中的结果。

用法
----
在 Content Browser 中选中目标 ControlRigRuntimeAsset，然后在 UE Python Console 中运行：
E:\ue58_controlrig_json_rebuilder.py

或者：
exec(
    open(
        r"E:\ue58_controlrig_json_rebuilder.py",
        encoding="utf-8",
    ).read()
)
"""
from __future__ import annotations

import json
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

import unreal # type: ignore

# =============================== 用户配置 ===============================
# 输入 JSON 文件。该文件保存节点、Pin、数组、连线和层级重建规则。
JSON_PATH = r"E:\CR_SKM_WaterUP_controlrig_rebuild_data.json"
# 为空时使用 Content Browser 当前选中的 ControlRigRuntimeAsset。
TARGET_CONTROL_RIG_ASSET = ""

# 是否重建 RigVM 图和层级。
REBUILD_GRAPH = True
REBUILD_HIERARCHY = True
REPLACE_EXISTING_GRAPH_NODES = True
REPLACE_DESCRIBED_HIERARCHY_ELEMENTS = True
REPAIR_ITEM_ARRAYS = True
STRICT_LINKS = False

POSITION_OFFSET = (0.0, 0.0)
DEFAULT_SHAPE_NAME = "Circle_Thick"
DEFAULT_SHAPE_SCALE = 5.0

# 首次测试保持 False；只有所有关键阶段成功后才允许保存资产。
SAVE_AFTER_SUCCESS = False
REPORT_PATH = r"E:\controlrig_json_rebuild_report.json"
# 固定的流水线阶段顺序。阶段编号用于日志和报告，不应随意调整。
WORKFLOW_STAGES = [
    "读取并验证 UE58ControlRigReconstructionData JSON",
    "获取 ControlRigRuntimeAsset 和内部 ControlRigEditorAsset",
    "获取 RigVMController",
    "获取 RigHierarchyController",
    "重建 Null、Control 和 Animation Channel",
    "根据导入骨骼层级解析控制器父级",
    "使用骨骼 Initial Local Transform 恢复控制器 Offset",
    "将控制器 Initial、Current Value 设置为 Identity",
    "验证层级和层级连接",
    "删除并重建 RigVM 节点",
    "恢复节点位置",
    "解析 Dispatch Wildcard 类型",
    "创建 ItemArray 动态数组元素",
    "恢复 Pin 默认值",
    "恢复节点连接",
    "所有关键阶段成功后按配置保存资产",
]
# =======================================================================


def log(message: Any, warning: bool = False) -> None:
    """向 Unreal Output Log 输出带统一前缀的普通日志或警告。"""
    fn = unreal.log_warning if warning else unreal.log
    fn("[CR JSON Rebuilder] " + str(message))


def load_json() -> Dict[str, Any]:
    """读取并验证重建 JSON，确保 Schema、graph 和 hierarchy 数据存在。"""
    if not os.path.isfile(JSON_PATH):
        raise RuntimeError("JSON 文件不存在: " + JSON_PATH)
    with open(JSON_PATH, "r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    schema = data.get("schema", {})
    if schema.get("name") != "UE58ControlRigReconstructionData":
        raise RuntimeError("不支持的 JSON Schema: " + repr(schema))
    if not data.get("graph") or not data.get("hierarchy"):
        raise RuntimeError("JSON 缺少 graph 或 hierarchy 数据")
    return data


def load_required_modules() -> None:
    """尝试加载 RigVM、Control Rig 和 Dynamics 相关编辑器模块。

    某些模块可能已经加载或在当前安装中不存在，因此单个模块失败只记录
    警告，不立即终止；真正缺失的节点类型会在后续报告中显示。
    """
    for module_name in (
        "RigVMDeveloper", "ControlRigDeveloper", "ControlRigEditor",
        "ControlRigDynamics", "ControlRigDynamicsEditor",
    ):
        try:
            unreal.load_module(module_name)
        except Exception as error:
            log("模块加载警告 {}: {}".format(module_name, error), True)


def get_assets(data: Dict[str, Any]):
    """取得运行时 Control Rig 资产及其内部 EditorOnly 编辑资产。

    优先使用用户配置路径，其次使用提取器记录的资产路径，最后使用当前
    Content Browser 选中的资产。EditorOnly 资产负责节点图编辑。
    """
    asset_path = TARGET_CONTROL_RIG_ASSET
    if not asset_path:
        asset_path = data.get("asset", {}).get("runtime_asset_path", "")
        # Extractor can return ObjectPath (/Game/A.A); load_asset accepts package path more reliably.
        if "." in asset_path.rsplit("/", 1)[-1]:
            asset_path = asset_path.rsplit(".", 1)[0]

    runtime = unreal.load_asset(asset_path) if asset_path else None
    if not runtime:
        selected = list(unreal.EditorUtilityLibrary.get_selected_assets() or [])
        if not selected:
            raise RuntimeError(
                "无法加载 JSON 中的资产，也没有选择资产。请填写 TARGET_CONTROL_RIG_ASSET。"
            )
        runtime = selected[0]

    class_name = runtime.get_class().get_name()
    editor = runtime if class_name.endswith("EditorAsset") else runtime.get_editor_asset()
    if not editor:
        raise RuntimeError("ControlRigRuntimeAsset.get_editor_asset() 返回 None")
    log("Runtime Asset: {} ({})".format(runtime.get_path_name(), class_name))
    return runtime, editor


def get_graph_controller(editor):
    """通过多个兼容入口获取 RigVMModel 对应的 RigVMController。"""
    errors = []
    for model_call in (
        lambda: editor.get_default_model(),
        lambda: editor.get_model("RigVMModel"),
        lambda: editor.get_model(),
    ):
        try:
            model = model_call()
            if model:
                controller = editor.get_controller(model)
                if controller:
                    return controller
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError("无法获取 RigVMController: " + " | ".join(errors))


def get_hierarchy(editor):
    """获取 RigHierarchy 和 RigHierarchyController。"""
    hierarchy = None
    controller = None
    for call in (lambda: editor.get_hierarchy(), lambda: editor.get_editor_property("hierarchy")):
        try:
            hierarchy = call()
            if hierarchy:
                break
        except Exception:
            pass
    if hierarchy:
        for call in (lambda: editor.get_hierarchy_controller(), lambda: hierarchy.get_controller(True)):
            try:
                controller = call()
                if controller:
                    break
            except Exception:
                pass
    if not hierarchy or not controller:
        raise RuntimeError("无法获取 RigHierarchy / RigHierarchyController")
    return hierarchy, controller


def get_registered_unit_map() -> Dict[str, str]:
    """建立当前 UE 环境中已注册 Rig Unit 名称到结构路径的映射。"""
    result: Dict[str, str] = {}
    try:
        for struct in unreal.ControlRigBlueprintLibrary.get_available_rig_units() or []:
            name = str(struct.get_name())
            path = str(struct.get_path_name())
            result[name] = path
            result[name.removeprefix("F")] = path
    except Exception as error:
        log("get_available_rig_units 失败: " + str(error), True)
    return result


def struct_path_from_resolved(resolved: str, unit_map: Dict[str, str]) -> str:
    """根据导出的 ResolvedFunctionName 推断 Rig Unit ScriptStruct 路径。"""
    struct_name = resolved.split("::", 1)[0]
    bare_name = struct_name.removeprefix("F")
    if struct_name in unit_map:
        return unit_map[struct_name]
    if bare_name in unit_map:
        return unit_map[bare_name]
    if bare_name.startswith("RigVMFunction_"):
        return "/Script/RigVM." + bare_name
    if "Dynamic" in bare_name:
        return "/Script/ControlRigDynamics." + bare_name
    return "/Script/ControlRig." + bare_name


def graph_node_map(controller) -> Dict[str, Any]:
    """返回当前 RigVM 图的节点名称到节点对象映射。"""
    return {str(node.get_name()): node for node in controller.get_graph().get_nodes()}


def clear_graph(controller, report: Dict[str, Any]) -> None:
    """通过 RigVMController 删除现有图节点，并记录无法删除的节点。"""
    for node in list(controller.get_graph().get_nodes()):
        try:
            controller.remove_node(node, False, False)
        except Exception as error:
            report["graph"]["remove_failures"].append({
                "node": str(node.get_name()), "error": str(error)
            })


def pin_record(node_data: Dict[str, Any], path: str) -> Dict[str, Any]:
    """从 JSON 节点记录中读取指定 Pin 的属性字典。"""
    return node_data.get("pins", {}).get(path, {})


def create_aggregate_sequence(controller, node_data: Dict[str, Any], position):
    """创建 Aggregate Sequence 节点，并按 JSON 追加额外聚合执行 Pin。"""
    pins = set(node_data.get("pins", {}))
    if not {"ExecuteContext", "A", "B"}.issubset(pins):
        raise RuntimeError("不支持的 Aggregate 节点 Pins: " + repr(sorted(pins)))
    node = controller.add_unit_node_from_struct_path(
        "/Script/RigVM.RigVMFunction_Sequence", "Execute", position,
        node_data["name"], False, False
    )
    for extra_pin in ("C", "D", "E", "F", "G", "H"):
        if extra_pin in pins:
            controller.add_aggregate_pin(node_data["name"], extra_pin, "", False, False)
    return node


def create_node(controller, node_data: Dict[str, Any], unit_map: Dict[str, str]):
    """按 JSON 中的节点类别创建一个 RigVM 节点。

    UnitNode 使用 ScriptStruct，Dispatch 使用 TemplateNotation，Reroute 使用
    专用 API，Variable 使用变量 API；不同类别不能共用同一种创建方式。
    """
    name = node_data["name"]
    class_name = node_data.get("class_name", "")
    position_data = node_data.get("position", {})
    if isinstance(position_data, dict):
        x, y = position_data.get("x", 0.0), position_data.get("y", 0.0)
    else:
        x, y = position_data[0], position_data[1]
    position = unreal.Vector2D(x + POSITION_OFFSET[0], y + POSITION_OFFSET[1])

    if class_name.endswith("RigVMAggregateNode"):
        return create_aggregate_sequence(controller, node_data, position)

    if class_name.endswith("RigVMUnitNode"):
        resolved = node_data.get("resolved_function_name", "")
        if not resolved:
            raise RuntimeError("缺少 resolved_function_name")
        path = struct_path_from_resolved(resolved, unit_map)
        method = node_data.get("method_name") or "Execute"
        return controller.add_unit_node_from_struct_path(path, method, position, name, False, False)

    if class_name.endswith("RigVMDispatchNode"):
        notation = node_data.get("template_notation", "")
        if not notation:
            raise RuntimeError("缺少 template_notation")
        return controller.add_template_node(notation, position, name, False, False)

    if class_name.endswith("RigVMRerouteNode"):
        pin = pin_record(node_data, "Value")
        return controller.add_free_reroute_node(
            pin.get("cpp_type") or "float",
            pin.get("cpp_type_object_path") or "",
            bool(pin.get("is_constant", False)),
            pin.get("custom_widget_name") or "",
            pin.get("default_value") or "",
            position, name, False,
        )

    if class_name.endswith("RigVMVariableNode"):
        variable_pin = pin_record(node_data, "Variable")
        value_pin = pin_record(node_data, "Value")
        variable_name = variable_pin.get("default_value", "")
        cpp_type = value_pin.get("cpp_type") or "float"
        object_path = value_pin.get("cpp_type_object_path") or ""
        default_value = value_pin.get("default_value") or ""
        is_getter = "ExecuteContext" not in node_data.get("pins", {})
        if hasattr(controller, "add_variable_node_from_object_path"):
            return controller.add_variable_node_from_object_path(
                variable_name, cpp_type, object_path, is_getter,
                default_value, position, name, False, False
            )
        type_object = unreal.load_object(None, object_path) if object_path else None
        return controller.add_variable_node(
            variable_name, cpp_type, type_object, is_getter,
            default_value, position, name, False, False
        )

    raise RuntimeError("不支持的节点类型: " + class_name)


def restore_node_positions(controller, nodes_data, name_map, report):
    """在所有节点创建完成后恢复 JSON 中记录的节点位置。"""
    report["graph"].setdefault("positions_restored", 0)
    report["graph"].setdefault("position_failures", [])
    for node_data in nodes_data:
        source_name = node_data["name"]
        if source_name not in name_map:
            continue
        position_data = node_data.get("position", {})
        if isinstance(position_data, dict):
            x = float(position_data.get("x", 0.0))
            y = float(position_data.get("y", 0.0))
        else:
            x = float(position_data[0])
            y = float(position_data[1])
        position = unreal.Vector2D(x + POSITION_OFFSET[0], y + POSITION_OFFSET[1])
        actual_name = name_map[source_name]
        success = False
        errors = []
        for call in (
            lambda: controller.set_node_position(actual_name, position, False, False),
            lambda: controller.set_node_position(actual_name, position, False),
            lambda: controller.set_node_position(actual_name, position),
        ):
            try:
                call()
                success = True
                break
            except Exception as error:
                errors.append(str(error))
        if success:
            report["graph"]["positions_restored"] += 1
        else:
            report["graph"]["position_failures"].append({
                "node": actual_name, "error": " | ".join(errors)
            })


def parse_resolved_pin_types(signature: str) -> Dict[str, str]:
    """从 Dispatch 的 ResolvedFunctionName 中提取 Pin 名称和 C++ 类型。"""
    result = {}
    if "::" not in signature:
        return result
    for item in signature.split("::", 1)[1].split(","):
        if ":" in item:
            name, cpp_type = item.split(":", 1)
            result[name.strip()] = cpp_type.strip()
    return result


def resolve_wildcards(controller, actual_name: str, node_data: Dict[str, Any], report):
    """使用导出的类型签名解析 Dispatch 节点的 Wildcard Pin。"""
    if not hasattr(controller, "resolve_wild_card_pin"):
        return
    for pin_name, cpp_type in parse_resolved_pin_types(
        node_data.get("resolved_function_name", "")
    ).items():
        source_pin = pin_record(node_data, pin_name)
        object_path = source_pin.get("cpp_type_object_path", "")
        try:
            controller.resolve_wild_card_pin(
                actual_name + "." + pin_name, cpp_type, object_path,
                False, False
            )
        except Exception as error:
            report["graph"]["wildcard_failures"].append({
                "pin": actual_name + "." + pin_name,
                "cpp_type": cpp_type,
                "error": str(error),
            })


def existing_array_size(node) -> int:
    """读取动态数组 Value Pin 当前已有的子元素数量。"""
    try:
        value_pin = node.find_pin("Value")
        return len(value_pin.get_sub_pins()) if value_pin else 0
    except Exception:
        return 0


def restore_item_arrays(controller, data: Dict[str, Any], name_map, report):
    """创建缺失的 ItemArray 元素并恢复每个元素的 Type、Name 默认值。

    必须先调用 add_array_pin 创建子 Pin，再设置叶子 Pin；直接设置父级 Value
    默认值可能会覆盖或清空整个动态数组。
    """
    nodes = graph_node_map(controller)
    for array_data in data.get("item_arrays", []):
        source_name = array_data["node"]
        actual_name = name_map.get(source_name, source_name)
        node = nodes.get(actual_name)
        if not node:
            report["arrays"]["failures"].append({
                "node": actual_name, "error": "节点不存在"
            })
            continue
        try:
            existing = existing_array_size(node)
            elements = array_data.get("elements", [])
            for element in elements[existing:]:
                default_value = element.get("default_value") or '(Type={},Name="{}")'.format(
                    element.get("type", "Bone"), element.get("name", "")
                )
                controller.add_array_pin(actual_name + ".Value", default_value, False, False)
                report["arrays"]["elements_added"] += 1
            for element in elements:
                index = element["index"]
                if element.get("type"):
                    controller.set_pin_default_value(
                        "{}.Value.{}.Type".format(actual_name, index),
                        element["type"], False, False, False
                    )
                if element.get("name"):
                    controller.set_pin_default_value(
                        "{}.Value.{}.Name".format(actual_name, index),
                        element["name"], False, False, False
                    )
            report["arrays"]["restored"] += 1
        except Exception as error:
            report["arrays"]["failures"].append({
                "node": actual_name, "error": str(error)
            })


def should_skip_default(pin_path: str, pin_data: Dict[str, Any]) -> bool:
    """判断某个 Pin 默认值是否应跳过，避免覆盖输出值、缓存或动态数组。"""
    if not pin_data.get("default_value"):
        return True
    if pin_data.get("direction") in ("Output", "Visible"):
        return True
    if any(token in pin_path for token in ("CachedIndex", "CachedChannel", ".Cache")):
        return True
    # Parent dynamic-array default "()" would clear elements restored earlier.
    if pin_data.get("is_dynamic_array") and pin_path.count(".") == 0:
        return True
    if pin_data.get("cpp_type", "").startswith("TArray<"):
        return True
    return False


def restore_pin_defaults(controller, nodes_data, name_map, report):
    """恢复普通节点 Pin 默认值，并按嵌套深度先父后子排序。"""
    for node_data in nodes_data:
        source_name = node_data["name"]
        if source_name not in name_map:
            continue
        actual_name = name_map[source_name]
        sorted_pins = sorted(
            node_data.get("pins", {}).items(),
            key=lambda item: (item[0].count("."), item[0]),
        )
        for path, pin_data in sorted_pins:
            if should_skip_default(path, pin_data):
                continue
            # ItemArray leaves are already restored by restore_item_arrays.
            if path.startswith("Value.") and source_name in {
                item["node"] for item in report.get("_item_arrays", [])
            }:
                continue
            try:
                controller.set_pin_default_value(
                    actual_name + "." + path,
                    pin_data["default_value"], False, False, False
                )
                report["graph"]["pin_defaults_set"] += 1
            except Exception as error:
                report["graph"]["pin_default_failures"].append({
                    "pin": actual_name + "." + path, "error": str(error)
                })


def restore_links(controller, links, name_map, report):
    """在所有节点和动态数组 Pin 创建完成后恢复 RigVM 节点连线。"""
    for link in links:
        try:
            source_node, source_pin = link["source"].split(".", 1)
            target_node, target_pin = link["target"].split(".", 1)
            if source_node not in name_map or target_node not in name_map:
                raise RuntimeError("连接端点节点未创建")
            source = name_map[source_node] + "." + source_pin
            target = name_map[target_node] + "." + target_pin
            result = controller.add_link(source, target, False, False)
            if result is False:
                raise RuntimeError("add_link 返回 False")
            report["graph"]["links_created"] += 1
        except Exception as error:
            report["graph"]["link_failures"].append({**link, "error": str(error)})
            if STRICT_LINKS:
                raise


def rebuild_graph(controller, data, report):
    """按固定阶段重建 RigVM 图、位置、Wildcard、数组、默认值和连线。"""
    log("步骤 10/16: 删除并重建 RigVM 节点")
    if REPLACE_EXISTING_GRAPH_NODES:
        clear_graph(controller, report)
    unit_map = get_registered_unit_map()
    name_map: Dict[str, str] = {}
    nodes_data = data["graph"].get("nodes", [])

    for node_data in nodes_data:
        source_name = node_data["name"]
        try:
            existing = graph_node_map(controller).get(source_name)
            node = existing or create_node(controller, node_data, unit_map)
            actual_name = str(node.get_name()) if node else source_name
            name_map[source_name] = actual_name
            report["graph"]["nodes_created"] += 1
        except Exception as error:
            report["graph"]["node_failures"].append({
                "node": source_name,
                "class_name": node_data.get("class_name", ""),
                "resolved_function_name": node_data.get("resolved_function_name", ""),
                "error": str(error),
            })

    log("步骤 11/16: 恢复节点位置")
    restore_node_positions(controller, nodes_data, name_map, report)

    log("步骤 12/16: 解析 Dispatch Wildcard 类型")
    for node_data in nodes_data:
        if node_data["name"] in name_map and node_data.get("class_name", "").endswith("RigVMDispatchNode"):
            resolve_wildcards(controller, name_map[node_data["name"]], node_data, report)

    log("步骤 13/16: 创建 ItemArray 动态数组元素")
    if REPAIR_ITEM_ARRAYS:
        restore_item_arrays(controller, data, name_map, report)

    log("步骤 14/16: 恢复 Pin 默认值")
    report["_item_arrays"] = data.get("item_arrays", [])
    restore_pin_defaults(controller, nodes_data, name_map, report)

    log("步骤 15/16: 恢复节点连接")
    restore_links(controller, data["graph"].get("links", []), name_map, report)
    report["graph"]["name_map"] = name_map
    return name_map


# ----------------------------- Hierarchy -----------------------------

def key_name(key) -> str:
    """兼容不同 UE Python 版本读取 RigElementKey 的名称。"""
    if key is None:
        return ""
    try:
        return str(key.name)
    except Exception:
        try:
            return str(key.get_editor_property("name"))
        except Exception:
            return ""


def key_type(key) -> str:
    """兼容不同 UE Python 版本读取 RigElementKey 的元素类型。"""
    try:
        return str(key.type).split(".")[-1]
    except Exception:
        try:
            return str(key.get_editor_property("type")).split(".")[-1]
        except Exception:
            return ""


def all_hierarchy_keys(hierarchy):
    """返回 RigHierarchy 中的全部元素 Key。"""
    return list(hierarchy.get_all_keys(True) or [])


def find_key(hierarchy, name: str, preferred_type: str = ""):
    """按名称查找层级元素，并优先返回指定类型的元素。"""
    candidates = [
        key for key in all_hierarchy_keys(hierarchy)
        if key_name(key).lower() == name.lower()
    ]
    if preferred_type:
        for key in candidates:
            if preferred_type.lower() in key_type(key).lower():
                return key
    return candidates[0] if candidates else None


def first_parent_name(hierarchy, key) -> str:
    """读取元素的第一个父级名称，兼容两种层级查询 API。"""
    for call in (
        lambda: hierarchy.get_first_parent(key),
        lambda: hierarchy.get_parents(key)[0],
    ):
        try:
            return key_name(call())
        except Exception:
            pass
    return ""


def empty_key():
    """创建表示无父级的空 RigElementKey。"""
    return unreal.RigElementKey()


def set_prop(obj, name, value) -> bool:
    """优先通过编辑器属性设置值，失败时回退到普通属性赋值。"""
    if value is None:
        return False
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception:
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            return False


def enum_value(enum_class, names):
    """从候选名称中获取当前 UE 版本实际存在的枚举值。"""
    for name in names:
        if hasattr(enum_class, name):
            return getattr(enum_class, name)
    return None


def transform_control_settings(control_data):
    """根据 JSON 控制器记录创建 Transform Control 设置。"""
    settings = unreal.RigControlSettings()
    requested = control_data.get("control_type", "EulerTransform")
    names = ["EULER_TRANSFORM", "TRANSFORM"] if requested == "EulerTransform" else [requested.upper(), "EULER_TRANSFORM"]
    set_prop(settings, "control_type", enum_value(unreal.RigControlType, names))
    if hasattr(unreal, "RigControlAnimationType"):
        set_prop(settings, "animation_type", enum_value(
            unreal.RigControlAnimationType,
            ["ANIMATION_CONTROL", "ANIMATION_CONTROL_VISIBLE"]
        ))
    set_prop(settings, "display_name", control_data["name"])
    set_prop(settings, "shape_name", control_data.get("shape_name") or DEFAULT_SHAPE_NAME)
    set_prop(settings, "shape_visible", True)
    return settings


def animation_channel_settings(channel_data):
    """根据 JSON 记录创建 Bool 或 Float Animation Channel 设置。"""
    settings = unreal.RigControlSettings()
    channel_type = channel_data.get("control_type", "Float")
    names = ["BOOL"] if channel_type == "Bool" else ["FLOAT", "SCALE_FLOAT"]
    set_prop(settings, "control_type", enum_value(unreal.RigControlType, names))
    if hasattr(unreal, "RigControlAnimationType"):
        set_prop(settings, "animation_type", enum_value(
            unreal.RigControlAnimationType, ["ANIMATION_CHANNEL"]
        ))
    set_prop(settings, "shape_visible", False)
    return settings


def add_control(hierarchy_controller, control_data, parent_key):
    """使用多个兼容签名创建 Transform Control。"""
    settings = transform_control_settings(control_data)
    value = unreal.RigControlValue()
    transform = unreal.Transform()
    errors = []
    for call in (
        lambda: hierarchy_controller.add_control(
            control_data["name"], parent_key, settings, value,
            transform, transform, False, False
        ),
        lambda: hierarchy_controller.add_control(
            control_data["name"], parent_key, settings, value, False, False
        ),
        lambda: hierarchy_controller.add_control(
            control_data["name"], parent_key, settings, value, False
        ),
    ):
        try:
            key = call()
            if key:
                return key
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError("add_control 失败: " + " | ".join(errors))


def add_null(hierarchy_controller, null_data, parent_key):
    """使用多个兼容签名创建 Null 层级元素。"""
    transform = unreal.Transform()
    errors = []
    for call in (
        lambda: hierarchy_controller.add_null(
            null_data["name"], parent_key, transform, True, False, False
        ),
        lambda: hierarchy_controller.add_null(
            null_data["name"], parent_key, transform, True, False
        ),
        lambda: hierarchy_controller.add_null(
            null_data["name"], parent_key, transform, False, False
        ),
    ):
        try:
            key = call()
            if key:
                return key
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError("add_null 失败: " + " | ".join(errors))


def initial_local_transform(hierarchy, bone_key):
    """读取骨骼的 Initial Local Transform，作为控制器 Offset 的来源。"""
    errors = []
    for call in (
        lambda: hierarchy.get_local_transform(bone_key, True),
        lambda: hierarchy.get_transform(bone_key, True),
    ):
        try:
            return call()
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError("无法读取 Bone Initial Local Transform: " + " | ".join(errors))


def set_control_offset_and_neutral_value(hierarchy, hierarchy_controller, control_key, local_offset):
    """设置控制器初始/当前本地 Offset，并将控制器值设为 Identity。"""
    errors = []
    for initial in (True, False):
        success = False
        for call in (
            lambda initial=initial: hierarchy.set_control_offset_transform(
                control_key, local_offset, initial, True, False, False
            ),
            lambda initial=initial: hierarchy.set_control_offset_transform(
                control_key, local_offset, initial, True, False
            ),
            lambda initial=initial: hierarchy.set_control_offset_transform(
                control_key, local_offset, initial, True
            ),
            lambda initial=initial: hierarchy_controller.set_control_offset_transform(
                control_key, local_offset, initial, False
            ),
        ):
            try:
                call()
                success = True
                break
            except Exception as error:
                errors.append(str(error))
        if not success:
            raise RuntimeError("设置 Control Offset 失败: " + " | ".join(errors))

    identity = unreal.Transform()
    for initial in (True, False):
        success = False
        for call in (
            lambda initial=initial: hierarchy.set_local_transform(
                control_key, identity, initial, True, False, False
            ),
            lambda initial=initial: hierarchy.set_local_transform(
                control_key, identity, initial, True, False
            ),
            lambda initial=initial: hierarchy.set_local_transform(
                control_key, identity, initial, True
            ),
        ):
            try:
                call()
                success = True
                break
            except Exception as error:
                errors.append(str(error))
        if not success:
            raise RuntimeError("清零 Control Local Value 失败: " + " | ".join(errors))


def set_shape_scale(hierarchy, control_key):
    """设置控制器形状缩放；形状 API 失败不会阻断主要重建流程。"""
    shape_transform = unreal.Transform(scale=unreal.Vector(
        DEFAULT_SHAPE_SCALE, DEFAULT_SHAPE_SCALE, DEFAULT_SHAPE_SCALE
    ))
    for call in (
        lambda: hierarchy.set_control_shape_transform(control_key, shape_transform, True),
        lambda: hierarchy.set_control_shape_transform(control_key, shape_transform),
    ):
        try:
            call()
            return
        except Exception:
            pass


def bone_depth(hierarchy, bone_name: str) -> int:
    """计算骨骼在导入骨骼层级中的深度，用于父级优先创建控制器。"""
    key = find_key(hierarchy, bone_name, "Bone")
    depth, visited = 0, set()
    while key:
        name = key_name(key)
        if not name or name in visited:
            break
        visited.add(name)
        parent = first_parent_name(hierarchy, key)
        if not parent:
            break
        depth += 1
        key = find_key(hierarchy, parent, "Bone")
    return depth


def resolve_parent_name(hierarchy, element_data, control_by_bone) -> str:
    """将 JSON 中的 parent_rule 解析为实际父级名称。"""
    rule = element_data.get("parent_rule", "root")
    if rule.startswith("explicit:"):
        return rule.split(":", 1)[1]
    if rule == "matching_bone_parent_control":
        bone_name = element_data.get("matching_bone", "")
        bone_key = find_key(hierarchy, bone_name, "Bone")
        if bone_key:
            parent_bone = first_parent_name(hierarchy, bone_key)
            return control_by_bone.get(parent_bone.lower(), "")
    return ""


def removal_order(hierarchy_data):
    """生成从子级到父级的安全删除顺序。"""
    channels = [item["name"] for item in hierarchy_data.get("animation_channels", [])]
    nulls = [item["name"] for item in hierarchy_data.get("nulls", [])]
    controls = [item["name"] for item in hierarchy_data.get("controls", [])]
    # Repeated removal in this order handles common leaf-to-root chains.
    return channels + list(reversed(controls)) + list(reversed(nulls))


def remove_described_elements(hierarchy, hierarchy_controller, hierarchy_data, report):
    """删除 JSON 描述的旧层级元素，并记录删除失败信息。"""
    for name in removal_order(hierarchy_data):
        while True:
            key = find_key(hierarchy, name)
            if not key:
                break
            try:
                hierarchy_controller.remove_element(key, False, False)
                report["hierarchy"]["removed"].append({
                    "name": name, "type": key_type(key)
                })
            except Exception as error:
                report["hierarchy"]["remove_failures"].append({
                    "name": name, "error": str(error)
                })
                break


def rebuild_hierarchy(hierarchy, hierarchy_controller, hierarchy_data, report):
    """重建 Null、Control、Animation Channel 和控制器本地变换。"""
    log("步骤 5/16: 重建 Null、Control 和 Animation Channel")
    if REPLACE_DESCRIBED_HIERARCHY_ELEMENTS:
        remove_described_elements(hierarchy, hierarchy_controller, hierarchy_data, report)

    controls_data = hierarchy_data.get("controls", [])
    nulls_data = hierarchy_data.get("nulls", [])
    channels_data = hierarchy_data.get("animation_channels", [])

    log("步骤 6/16: 根据导入骨骼层级解析控制器父级")
    control_by_bone = {
        item.get("matching_bone", "").lower(): item["name"]
        for item in controls_data if item.get("matching_bone")
    }
    created: Dict[str, Any] = {}

    # 先创建根级 Null；有明确父级的子 Null 延迟到父级控制器创建后。
    pending_nulls = []
    for null_data in nulls_data:
        parent_name = resolve_parent_name(hierarchy, null_data, control_by_bone)
        if parent_name:
            pending_nulls.append(null_data)
            continue
        try:
            key = find_key(hierarchy, null_data["name"], "Null") or add_null(
                hierarchy_controller, null_data, empty_key()
            )
            created[null_data["name"]] = key
            report["hierarchy"]["nulls_created"] += 1
        except Exception as error:
            report["hierarchy"]["failures"].append({
                "name": null_data["name"], "error": str(error)
            })

    # 按导入骨骼深度创建控制器，确保父级控制器先于子级控制器存在。
    log("步骤 7/16: 使用骨骼 Initial Local Transform 恢复控制器 Offset")
    log("步骤 8/16: 将控制器 Initial、Current Value 设置为 Identity")
    controls_data = sorted(
        controls_data,
        key=lambda item: (
            bone_depth(hierarchy, item.get("matching_bone", ""))
            if item.get("matching_bone") else 0,
            item["name"],
        ),
    )
    for control_data in controls_data:
        parent_name = resolve_parent_name(hierarchy, control_data, control_by_bone)
        parent_key = created.get(parent_name) or find_key(hierarchy, parent_name) or empty_key()
        try:
            key = find_key(hierarchy, control_data["name"], "Control") or add_control(
                hierarchy_controller, control_data, parent_key
            )
            created[control_data["name"]] = key
            report["hierarchy"]["controls_created"] += 1

            bone_name = control_data.get("matching_bone", "")
            if bone_name:
                bone_key = find_key(hierarchy, bone_name, "Bone")
                if not bone_key:
                    raise RuntimeError("匹配 Bone 不存在: " + bone_name)
                local_offset = initial_local_transform(hierarchy, bone_key)
                set_control_offset_and_neutral_value(
                    hierarchy, hierarchy_controller, key, local_offset
                )
                report["hierarchy"]["transforms_restored"] += 1
            set_shape_scale(hierarchy, key)
        except Exception as error:
            report["hierarchy"]["failures"].append({
                "name": control_data["name"], "error": str(error)
            })

    # 将 Animation Channel 创建为 JSON 指定 owner control 的直接子级。
    for channel_data in channels_data:
        owner_name = channel_data["owner_control"]
        owner_key = created.get(owner_name) or find_key(hierarchy, owner_name, "Control")
        if not owner_key:
            report["hierarchy"]["failures"].append({
                "name": channel_data["name"], "error": "Owner Control 不存在: " + owner_name
            })
            continue
        try:
            existing = find_key(hierarchy, channel_data["name"], "Control")
            if not existing:
                hierarchy_controller.add_animation_channel(
                    channel_data["name"], owner_key,
                    animation_channel_settings(channel_data), False, False
                )
            report["hierarchy"]["channels_created"] += 1
        except Exception as error:
            report["hierarchy"]["failures"].append({
                "name": channel_data["name"], "error": str(error)
            })

    # 最后创建 proxy_buffer 等依赖控制器的子 Null。
    for null_data in pending_nulls:
        parent_name = resolve_parent_name(hierarchy, null_data, control_by_bone)
        parent_key = created.get(parent_name) or find_key(hierarchy, parent_name)
        if not parent_key:
            report["hierarchy"]["failures"].append({
                "name": null_data["name"], "error": "Parent 不存在: " + parent_name
            })
            continue
        try:
            key = find_key(hierarchy, null_data["name"], "Null") or add_null(
                hierarchy_controller, null_data, parent_key
            )
            created[null_data["name"]] = key
            report["hierarchy"]["nulls_created"] += 1
        except Exception as error:
            report["hierarchy"]["failures"].append({
                "name": null_data["name"], "error": str(error)
            })

    log("步骤 9/16: 验证层级和层级连接")
    validate_hierarchy(hierarchy, hierarchy_data, control_by_bone, report)


def validate_hierarchy(hierarchy, hierarchy_data, control_by_bone, report):
    """验证 Control、Animation Channel 和 Null 的实际父级关系。"""
    for control_data in hierarchy_data.get("controls", []):
        name = control_data["name"]
        key = find_key(hierarchy, name, "Control")
        if not key:
            report["hierarchy"]["validation_failures"].append(name + " 缺失")
            continue
        expected = resolve_parent_name(hierarchy, control_data, control_by_bone)
        actual = first_parent_name(hierarchy, key)
        if actual != expected:
            report["hierarchy"]["validation_failures"].append(
                "{} parent={} expected={}".format(name, actual, expected)
            )

    for channel in hierarchy_data.get("animation_channels", []):
        key = find_key(hierarchy, channel["name"], "Control")
        if not key:
            report["hierarchy"]["validation_failures"].append(channel["name"] + " 缺失")
            continue
        actual = first_parent_name(hierarchy, key)
        if actual != channel["owner_control"]:
            report["hierarchy"]["validation_failures"].append(
                "{} parent={} expected={}".format(
                    channel["name"], actual, channel["owner_control"]
                )
            )

    for null_data in hierarchy_data.get("nulls", []):
        key = find_key(hierarchy, null_data["name"], "Null")
        if not key:
            report["hierarchy"]["validation_failures"].append(null_data["name"] + " 缺失")
            continue
        expected = resolve_parent_name(hierarchy, null_data, control_by_bone)
        actual = first_parent_name(hierarchy, key)
        if actual != expected:
            report["hierarchy"]["validation_failures"].append(
                "{} parent={} expected={}".format(null_data["name"], actual, expected)
            )


def new_report(data) -> Dict[str, Any]:
    """创建包含图、数组、层级和编译状态的标准化报告结构。"""
    return {
        "json": JSON_PATH,
        "schema": data.get("schema", {}),
        "graph": {
            "expected_nodes": data["graph"].get("node_count", len(data["graph"].get("nodes", []))),
            "expected_links": data["graph"].get("link_count", len(data["graph"].get("links", []))),
            "nodes_created": 0,
            "links_created": 0,
            "pin_defaults_set": 0,
            "positions_restored": 0,
            "position_failures": [],
            "name_map": {},
            "remove_failures": [],
            "node_failures": [],
            "wildcard_failures": [],
            "pin_default_failures": [],
            "link_failures": [],
        },
        "arrays": {
            "expected": len(data.get("item_arrays", [])),
            "restored": 0,
            "elements_added": 0,
            "failures": [],
        },
        "hierarchy": {
            "controls_created": 0,
            "nulls_created": 0,
            "channels_created": 0,
            "transforms_restored": 0,
            "removed": [],
            "remove_failures": [],
            "failures": [],
            "validation_failures": [],
        },
        "compile_warning": "",
        "saved": False,
        "all_critical_phases_succeeded": False,
    }


def is_clean(report) -> bool:
    """判断所有启用的关键重建阶段是否都没有报告错误。"""
    graph = report["graph"]
    arrays = report["arrays"]
    hierarchy = report["hierarchy"]
    graph_ok = (
        (not REBUILD_GRAPH)
        or (
            graph["nodes_created"] == graph["expected_nodes"]
            and graph["links_created"] == graph["expected_links"]
            and not graph["node_failures"]
            and not graph["position_failures"]
            and not graph["wildcard_failures"]
            and not graph["link_failures"]
        )
    )
    arrays_ok = (not REPAIR_ITEM_ARRAYS) or (
        arrays["restored"] == arrays["expected"] and not arrays["failures"]
    )
    hierarchy_ok = (not REBUILD_HIERARCHY) or (
        not hierarchy["failures"] and not hierarchy["validation_failures"]
    )
    return graph_ok and arrays_ok and hierarchy_ok


def main():
    """执行完整 JSON 驱动重建、编译、验证、保存和报告输出流程。"""
    load_required_modules()

    log("步骤 1/16: 读取并验证 UE58ControlRigReconstructionData JSON")
    data = load_json()
    report = new_report(data)
    report["workflow_stages"] = WORKFLOW_STAGES
    report["completed_stages"] = []
    report["completed_stages"].append(1)

    log("步骤 2/16: 获取 ControlRigRuntimeAsset 和内部 ControlRigEditorAsset")
    runtime, editor = get_assets(data)
    report["completed_stages"].append(2)

    log("步骤 3/16: 获取 RigVMController")
    graph_controller = get_graph_controller(editor)
    report["completed_stages"].append(3)

    log("步骤 4/16: 获取 RigHierarchyController")
    hierarchy, hierarchy_controller = get_hierarchy(editor)
    report["completed_stages"].append(4)

    # 先完成层级重建和校验，再删除 RigVM 图，保留节点引用所需的控制器名称。
    if REBUILD_HIERARCHY:
        rebuild_hierarchy(
            hierarchy, hierarchy_controller, data["hierarchy"], report
        )
        report["completed_stages"].extend([5, 6, 7, 8, 9])
    else:
        log("步骤 5-9 已按配置跳过", True)

    # 只有层级阶段完成后才开始 RigVM 图重建。
    if REBUILD_GRAPH:
        rebuild_graph(graph_controller, data, report)
        report["completed_stages"].extend([10, 11, 12, 13, 14, 15])
    else:
        log("步骤 10-15 已按配置跳过", True)

    # 层级和图都处理完后再编译，并在编译后评估最终成功状态。
    try:
        if hasattr(editor, "recompile_vm"):
            editor.recompile_vm()
    except Exception as error:
        report["compile_warning"] = str(error)
        log("编译警告: " + str(error), True)

    report.pop("_item_arrays", None)
    report["all_critical_phases_succeeded"] = is_clean(report)

    log("步骤 16/16: 所有关键阶段成功后按配置保存资产")
    if SAVE_AFTER_SUCCESS and report["all_critical_phases_succeeded"]:
        unreal.EditorAssetLibrary.save_loaded_asset(runtime, False)
        report["saved"] = True
        log("Runtime Asset 已保存")
    elif SAVE_AFTER_SUCCESS:
        log("存在关键失败，已跳过保存", True)
    else:
        log("SAVE_AFTER_SUCCESS=False，本次仅重建和验证，不保存")
    report["completed_stages"].append(16)

    report_dir = os.path.dirname(REPORT_PATH)
    if report_dir and not os.path.isdir(report_dir):
        raise RuntimeError("报告目录不存在: " + report_dir)
    with open(REPORT_PATH, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)

    log("完成: nodes {}/{} links {}/{} arrays {}/{} controls={} channels={} nulls={}".format(
        report["graph"]["nodes_created"], report["graph"]["expected_nodes"],
        report["graph"]["links_created"], report["graph"]["expected_links"],
        report["arrays"]["restored"], report["arrays"]["expected"],
        report["hierarchy"]["controls_created"],
        report["hierarchy"]["channels_created"],
        report["hierarchy"]["nulls_created"],
    ))
    log("总报告: " + REPORT_PATH)
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc(), True)
        raise
