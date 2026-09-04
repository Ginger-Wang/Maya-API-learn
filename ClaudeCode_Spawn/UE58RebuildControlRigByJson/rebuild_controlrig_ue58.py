# -*- coding: utf-8 -*-
"""
rebuild_controlrig_ue58.py

Rebuild a complete Control Rig asset in Unreal Engine 5.8 from the
"UE58ControlRigTextExport" v2.0 JSON produced by the text-export dump.

RUN THIS INSIDE THE UNREAL EDITOR
    Window > Output Log  ->  switch the input box to "Python"  ->
        exec(open(r"H:/rebuild_controlrig_ue58.py", encoding="utf-8").read())
or
    py "H:/rebuild_controlrig_ue58.py"

What it does
    1. loads + repairs the JSON (the export was written with mojibake node names)
    2. creates / replaces the target Control Rig Blueprint
    3. sets the preview skeletal mesh + shape libraries, imports the bones
    4. creates the member variables
    5. rebuilds every node of the top level graph
         - RigVMUnitNode      -> add_unit_node_from_struct_path
         - RigVMDispatchNode  -> add_template_node + resolve_wild_card_pin
         - RigVMAggregateNode -> unit node + add_aggregate_pin (recreates the sub graph)
         - RigVMRerouteNode   -> add_free_reroute_node
         - RigVMVariableNode  -> add_variable_node
         - RigVMCommentNode   -> add_comment_node
    6. sizes array pins, writes every literal pin default
    7. recreates all 96 links
    8. compiles, runs Construction, saves

Everything the engine API refuses is logged and collected in a report at the
end instead of aborting the run, so you always get a partially-built asset you
can inspect rather than a half-torn-down one.
"""

import json
import os
import unreal # type: ignore


# ----------------------------------------------------------------------------
# configuration
# ----------------------------------------------------------------------------

JSON_PATH = r"H:\controlrig_rebuild.json"

# Where the rebuilt rig goes. Leave TARGET_PACKAGE_PATH/TARGET_ASSET_NAME as
# None to reuse asset.runtime_asset_path from the JSON (which would overwrite
# the original asset - not recommended).
TARGET_PACKAGE_PATH = "/Game/Materials_Learn"
TARGET_ASSET_NAME = "CR_AssetName_Rebuilt"

# The export contains UTF-8 bytes decoded as latin-1 ("è®¾ç½®åæ°æ®_2").
# We repair that, then optionally romanise it because non-ASCII RigVM node
# names are legal but painful to work with.
SANITIZE_NON_ASCII_NODE_NAMES = True

# The Construction Event in this rig spawns every Control / Null / animation
# channel itself (SpawnControl*, HierarchyAddNull*, SpawnAnimationChannel*).
# So the hierarchy only needs the imported bones. Flip this on only if you
# want the elements pre-created from hierarchy.controls / .nulls as well.
CREATE_HIERARCHY_ELEMENTS = False

RUN_CONSTRUCTION_AFTER_BUILD = True
SAVE_WHEN_DONE = True

# Reroute nodes are purely cosmetic (pure pass-through wires). Probing the
# engine for AddFreeRerouteNode's signature has proven unstable on 5.8, so by
# default we skip them and collapse the wires instead - the resulting graph is
# functionally identical, just with straighter links. Flip to True only if you
# want the original wire routing back and are willing to risk the API probe.
CREATE_REROUTE_NODES = False

# Writes one line per engine operation to rebuild_trace.log, flushed
# immediately, so that if the editor hard-crashes the last line tells you
# exactly which call did it. Cheap enough to leave on.
ENABLE_TRACE = True
TRACE_PATH = os.path.join(os.path.dirname(JSON_PATH) or ".", "rebuild_trace.log")

# Modules probed when turning "FRigUnit_GetTransform::Execute" into a
# /Script/<Module>.<Struct> path.
STRUCT_MODULES = [
    "ControlRig",
    "RigVM",
    "ControlRigDynamics",
    "ControlRigSpline",
    "AnimationCore",
    "Engine",
    "CoreUObject",
]

# Mojibake-free Chinese node names -> ASCII, used when SANITIZE_... is on.
CJK_NAME_MAP = {
    u"\u67e5\u627e": "ArrayFind",                                    # 查找
    u"\u83b7\u53d6\u5143\u6570\u636e": "GetMetadata",                 # 获取元数据
    u"\u8bbe\u7f6e\u5143\u6570\u636e": "SetMetadata",                 # 设置元数据
    u"\u9009\u62e9": "Select",                                        # 选择
    u"\u9488\u5bf9\u6bcf\u4e2a": "ForEach",                           # 针对每个
}

LOG_PREFIX = "[CR-Rebuild]"


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------

class Report(object):
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.counts = {}

    def bump(self, key, amount=1):
        self.counts[key] = self.counts.get(key, 0) + amount

    def warn(self, msg):
        self.warnings.append(msg)
        unreal.log_warning("%s %s" % (LOG_PREFIX, msg))

    def error(self, msg):
        self.errors.append(msg)
        unreal.log_error("%s %s" % (LOG_PREFIX, msg))

    def dump(self):
        log("---------------- rebuild report ----------------")
        for key in sorted(self.counts):
            log("  %-28s %s" % (key, self.counts[key]))
        log("  warnings %d / errors %d" % (len(self.warnings), len(self.errors)))
        for w in self.warnings:
            log("    WARN  %s" % w)
        for e in self.errors:
            log("    ERROR %s" % e)
        log("-----------------------------------------------")


REPORT = Report()


def log(msg):
    unreal.log("%s %s" % (LOG_PREFIX, msg))
    trace("LOG  %s" % msg)


def trace(msg):
    """Append one line and close the file, so nothing is buffered when the
    editor crashes mid-call."""
    if not ENABLE_TRACE:
        return
    try:
        with open(TRACE_PATH, "a", encoding="utf-8") as handle:
            handle.write(msg + "\n")
    except Exception:  # noqa: BLE001 - never let tracing break the rebuild
        pass


def trace_reset():
    if not ENABLE_TRACE:
        return
    try:
        with open(TRACE_PATH, "w", encoding="utf-8") as handle:
            handle.write("=== rebuild trace ===\n")
        unreal.log("%s trace -> %s" % (LOG_PREFIX, TRACE_PATH))
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning("%s trace file unavailable: %s" % (LOG_PREFIX, exc))


def repair_mojibake(text):
    """'è®¾ç½®åæ°æ®' -> '设置元数据'. Returns text untouched if it is not mojibake."""
    if not isinstance(text, str) or all(ord(c) < 128 for c in text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def ascii_node_name(name):
    """Map a (repaired) node name onto something ASCII and RigVM-safe."""
    if all(ord(c) < 128 for c in name):
        return name
    base, suffix = name, ""
    if "_" in name:
        head, _, tail = name.rpartition("_")
        if tail.isdigit():
            base, suffix = head, "_" + tail
    mapped = CJK_NAME_MAP.get(base)
    if mapped:
        return mapped + suffix
    # last resort: strip to ASCII, keep it unique-ish via the code points
    return "Node_" + "".join("%04X" % ord(c) for c in base) + suffix


def call_first(obj, method_names, *args, **kwargs):
    """Call the first method in method_names that exists. Returns (ok, result)."""
    for name in method_names:
        fn = getattr(obj, name, None)
        if fn is None:
            continue
        try:
            return True, fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - engine raises bare Exception
            REPORT.warn("%s(%s) failed: %s" % (name, _short(args), exc))
            return False, None
    return False, None


def _short(args):
    text = ", ".join(repr(a) for a in args)
    return text if len(text) <= 90 else text[:87] + "..."


def vec2(position):
    return unreal.Vector2D(float(position.get("x", 0.0)), float(position.get("y", 0.0)))


def linear_color(color):
    return unreal.LinearColor(
        float(color.get("r", 0.0)),
        float(color.get("g", 0.0)),
        float(color.get("b", 0.0)),
        float(color.get("a", 1.0)),
    )


def load_cpp_type_object(path):
    if not path:
        return None
    try:
        return unreal.load_object(None, path)
    except Exception:  # noqa: BLE001
        return None


def cpp_type_object_args(path):
    """Candidate values for RigVMController's cpp_type_object parameter.

    5.8 declares it as InCPPTypeObjectPath (an FName), older builds took a
    UObject. Path string first, loaded object second, then empty.
    """
    candidates = []
    if path:
        candidates.append(path)
        obj = load_cpp_type_object(path)
        if obj is not None:
            candidates.append(obj)
    candidates.append("")
    candidates.append(None)
    return candidates


# ----------------------------------------------------------------------------
# JSON loading
# ----------------------------------------------------------------------------

def load_export(path):
    if not os.path.isfile(path):
        raise IOError("JSON not found: %s" % path)
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    schema = data.get("schema", {})
    log("loaded %s v%s from %s" % (schema.get("name"), schema.get("version"), path))
    return data


def build_name_map(graph):
    """original JSON node name -> name we will actually create in UE."""
    mapping = {}
    used = set()
    for node in graph.get("nodes", []):
        raw = node["name"]
        fixed = repair_mojibake(raw)
        final = ascii_node_name(fixed) if SANITIZE_NON_ASCII_NODE_NAMES else fixed
        while final in used:
            final += "_x"
        used.add(final)
        mapping[raw] = final
        if final != raw:
            log("  rename node '%s' -> '%s'" % (raw, final))
    return mapping


def split_pin_path(path):
    """'NodeName.Pin.Sub' -> ('NodeName', 'Pin.Sub'). Node names never contain '.'."""
    node, _, pin = path.partition(".")
    return node, pin


def remap_pin_path(path, name_map):
    node, pin = split_pin_path(path)
    node = name_map.get(node, ascii_node_name(repair_mojibake(node)))
    return "%s.%s" % (node, pin) if pin else node


# ----------------------------------------------------------------------------
# asset creation
# ----------------------------------------------------------------------------

def resolve_target_path(asset_info):
    if TARGET_PACKAGE_PATH and TARGET_ASSET_NAME:
        return TARGET_PACKAGE_PATH, TARGET_ASSET_NAME
    runtime = asset_info.get("runtime_asset_path", "")
    obj_path = runtime.split(".")[0]
    return obj_path.rsplit("/", 1)[0], obj_path.rsplit("/", 1)[1]


def close_editors_for(full_path):
    """A Control Rig that is open in its editor cannot be deleted; ForceDelete
    then leaves a corrupt package behind."""
    try:
        asset = unreal.load_asset(full_path)
    except Exception:  # noqa: BLE001
        return
    if asset is None:
        return
    try:
        subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        subsystem.close_all_editors_for_asset(asset)
    except Exception as exc:  # noqa: BLE001
        REPORT.warn("could not close editors for %s: %s" % (full_path, exc))


def free_target_path(package_path, asset_name):
    """Delete the target asset, or pick an unused name if it refuses to go."""
    full_path = "%s/%s" % (package_path, asset_name)
    if not unreal.EditorAssetLibrary.does_asset_exist(full_path):
        return full_path, asset_name

    log("deleting existing asset %s" % full_path)
    close_editors_for(full_path)
    try:
        deleted = unreal.EditorAssetLibrary.delete_asset(full_path)
    except Exception as exc:  # noqa: BLE001
        REPORT.warn("delete_asset raised: %s" % exc)
        deleted = False

    if deleted and not unreal.EditorAssetLibrary.does_asset_exist(full_path):
        return full_path, asset_name

    for index in range(2, 100):
        candidate = "%s_%d" % (asset_name, index)
        candidate_path = "%s/%s" % (package_path, candidate)
        if not unreal.EditorAssetLibrary.does_asset_exist(candidate_path):
            REPORT.warn("%s is locked (still open, or referenced) - building %s instead. "
                        "Close the Control Rig editor tab and delete the old asset by hand."
                        % (full_path, candidate_path))
            return candidate_path, candidate
    raise RuntimeError("could not find a free asset name next to %s" % full_path)


def create_blueprint(asset_info):
    package_path, asset_name = resolve_target_path(asset_info)
    full_path, asset_name = free_target_path(package_path, asset_name)

    mesh = None
    mesh_path = asset_info.get("preview_skeletal_mesh", "")
    if mesh_path:
        try:
            mesh = unreal.load_asset(mesh_path)
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("preview mesh %s could not be loaded: %s" % (mesh_path, exc))

    factory = unreal.ControlRigBlueprintFactory()
    blueprint = None

    # Preferred path in 5.8: the factory builds the runtime + editor-only pair
    # and imports the skeleton for us.
    if mesh is not None and hasattr(factory, "create_control_rig_from_skeletal_mesh_or_skeleton"):
        try:
            blueprint = factory.create_control_rig_from_skeletal_mesh_or_skeleton(mesh)
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("create_control_rig_from_skeletal_mesh_or_skeleton failed: %s" % exc)

    if blueprint is not None:
        created_path = blueprint.get_path_name().split(".")[0]
        if created_path != full_path:
            log("moving %s -> %s" % (created_path, full_path))
            if unreal.EditorAssetLibrary.rename_asset(created_path, full_path):
                blueprint = unreal.load_asset(full_path)
            else:
                REPORT.warn("rename to %s failed, keeping %s" % (full_path, created_path))
                blueprint = unreal.load_asset(created_path)
    else:
        log("falling back to AssetTools.create_asset")
        blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name, package_path, unreal.ControlRigBlueprint, factory
        )

    if blueprint is None:
        raise RuntimeError("could not create the Control Rig Blueprint")

    log("blueprint: %s" % blueprint.get_path_name())
    REPORT.bump("asset created", 1)
    return blueprint, mesh


def configure_asset(blueprint, mesh, asset_info):
    if mesh is not None:
        call_first(blueprint, ["set_preview_mesh"], mesh)

    libs = asset_info.get("shape_libraries") or []
    loaded = []
    for lib_path in libs:
        try:
            lib = unreal.load_asset(lib_path)
            if lib is not None:
                loaded.append(lib)
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("shape library %s not loaded: %s" % (lib_path, exc))
    if loaded:
        try:
            blueprint.set_editor_property("shape_libraries", loaded)
            REPORT.bump("shape libraries", len(loaded))
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("shape_libraries could not be assigned: %s" % exc)


def hierarchy_controller(blueprint):
    ok, ctrl = call_first(blueprint, ["get_hierarchy_controller"])
    if ok and ctrl is not None:
        return ctrl
    return blueprint.hierarchy.get_controller()


def describe_api(obj, needle=""):
    """List the callable members of an engine object - used when an API probe
    fails so the log tells us what this build actually exposes."""
    names = sorted(n for n in dir(obj)
                   if not n.startswith("_") and (not needle or needle.lower() in n.lower()))
    return ", ".join(names)


def all_element_keys(hierarchy):
    """Every RigElementKey in the hierarchy, across UE API revisions.

    5.0-5.3 had get_bone_keys()/get_control_keys(); newer builds dropped them in
    favour of get_all_keys()/get_keys(), and index access always works.
    """
    for method, args in (
        ("get_all_keys", (True,)),
        ("get_all_keys", ()),
        ("get_keys", (True,)),
        ("get_keys", ()),
    ):
        fn = getattr(hierarchy, method, None)
        if fn is None:
            continue
        try:
            keys = list(fn(*args))
            if keys is not None:
                return keys
        except Exception:  # noqa: BLE001
            continue

    # index based fallback
    for count_method in ("num", "get_num_elements", "size"):
        fn = getattr(hierarchy, count_method, None)
        if fn is None:
            continue
        try:
            count = int(fn())
        except Exception:  # noqa: BLE001
            continue
        for key_method in ("get_key", "get_key_at_index"):
            getter = getattr(hierarchy, key_method, None)
            if getter is None:
                continue
            try:
                return [getter(i) for i in range(count)]
            except Exception:  # noqa: BLE001
                continue

    REPORT.warn("cannot enumerate hierarchy keys. RigHierarchy exposes: %s"
                % describe_api(hierarchy, "key"))
    return []


def key_type_of(key):
    return getattr(key, "type", None)


def keys_of_type(hierarchy, element_type):
    return [k for k in all_element_keys(hierarchy) if key_type_of(k) == element_type]


def bone_keys(hierarchy):
    return keys_of_type(hierarchy, unreal.RigElementType.BONE)


def bone_names(hierarchy):
    return [str(k.name) for k in bone_keys(hierarchy)]


def import_bones(blueprint, mesh, hierarchy_info):
    if mesh is None:
        REPORT.warn("no preview mesh - bones were NOT imported, item arrays will "
                    "reference missing elements")
        return

    hierarchy = blueprint.hierarchy
    controller = hierarchy_controller(blueprint)
    existing = bone_names(hierarchy)
    wanted = [b["name"] for b in hierarchy_info.get("bones", [])]

    if not set(wanted).issubset(set(existing)):
        skeleton = getattr(mesh, "skeleton", None)
        attempts = [
            (["import_bones_from_asset"], (mesh.get_path_name(), "", True, True, False)),
            (["import_bones"], (skeleton, "", True, True, False, True, False)),
            (["import_bones"], (skeleton, "", True, True, False)),
            (["import_bones"], (skeleton,)),
        ]
        for names, args in attempts:
            if args[0] is None:
                continue
            fn = getattr(controller, names[0], None)
            if fn is None:
                continue
            try:
                fn(*args)
                break
            except Exception:  # noqa: BLE001
                continue

    have = bone_names(hierarchy)
    REPORT.bump("bones in hierarchy", len(have))
    if not have:
        REPORT.warn("no bones present after import. RigHierarchyController exposes: %s"
                    % describe_api(controller, "import"))
    missing = [name for name in wanted if name not in have]
    if missing:
        REPORT.warn("bones referenced by the graph but absent from the skeleton: %s" % missing)


def create_hierarchy_elements(blueprint, hierarchy_info):
    """Optional: pre-create Controls / Nulls / channels instead of relying on
    the Construction Event to spawn them."""
    hierarchy = blueprint.hierarchy
    controller = hierarchy_controller(blueprint)
    keys = bone_keys(hierarchy)
    bone_local = {}
    for key in keys:
        try:
            bone_local[str(key.name)] = hierarchy.get_local_transform(key, True)
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("local transform of %s unavailable: %s" % (key.name, exc))

    parent_of_bone = {}
    for key in keys:
        ok, parent = call_first(hierarchy, ["get_first_parent"], key)
        name = str(getattr(parent, "name", "None")) if (ok and parent is not None) else "None"
        parent_of_bone[str(key.name)] = "" if name == "None" else name

    settings = unreal.RigControlSettings()
    settings.control_type = unreal.RigControlType.EULER_TRANSFORM
    settings.animation_type = unreal.RigControlAnimationType.ANIMATION_CONTROL

    made = {}
    for control in hierarchy_info.get("controls", []):
        name = control["name"]
        bone = control.get("matching_bone") or ""
        parent_key = unreal.RigElementKey()
        if bone:
            parent_bone = parent_of_bone.get(bone, "")
            parent_ctrl = parent_bone + hierarchy_info.get("control_suffix", "_ctrl")
            if parent_bone and parent_ctrl in made:
                parent_key = made[parent_ctrl]
        value = unreal.RigHierarchy.make_control_value_from_euler_transform(
            unreal.EulerTransform()
        )
        ok, key = call_first(controller, ["add_control"], name, parent_key, settings, value)
        if ok and key is not None:
            made[name] = key
            REPORT.bump("controls created")
            if bone and bone in bone_local:
                try:
                    hierarchy.set_control_offset_transform(key, bone_local[bone], True, True)
                except Exception as exc:  # noqa: BLE001
                    REPORT.warn("offset for %s failed: %s" % (name, exc))

    for null in hierarchy_info.get("nulls", []):
        ok, _ = call_first(
            controller, ["add_null"], null["name"], unreal.RigElementKey(),
            unreal.Transform(), True
        )
        if ok:
            REPORT.bump("nulls created")

    for channel in hierarchy_info.get("animation_channels", []):
        owner = made.get(channel.get("owner_control", ""))
        if owner is None:
            REPORT.warn("channel %s: owner control %s missing" %
                        (channel["name"], channel.get("owner_control")))
            continue
        ch_settings = unreal.RigControlSettings()
        ch_settings.animation_type = unreal.RigControlAnimationType.ANIMATION_CHANNEL
        ch_settings.control_type = {
            "Bool": unreal.RigControlType.BOOL,
            "Float": unreal.RigControlType.FLOAT,
            "Integer": unreal.RigControlType.INTEGER,
        }.get(channel.get("control_type", "Bool"), unreal.RigControlType.BOOL)
        ok, _ = call_first(
            controller, ["add_animation_channel"], channel["name"], owner, ch_settings
        )
        if ok:
            REPORT.bump("animation channels created")


def create_variables(blueprint, variables):
    for var in variables:
        name = var["name"]
        cpp_type = var.get("cpp_type", "FName")
        default = var.get("default_value", "")
        ok, _ = call_first(
            blueprint, ["add_member_variable"], name, cpp_type, True, False, default
        )
        if not ok:
            ok, _ = call_first(blueprint, ["add_member_variable"], name, cpp_type)
        if ok:
            REPORT.bump("variables created")
        else:
            REPORT.error("member variable %s (%s) could not be created" % (name, cpp_type))


# ----------------------------------------------------------------------------
# graph rebuild
# ----------------------------------------------------------------------------

def get_controller(blueprint, graph_name="RigVMModel"):
    ok, controller = call_first(blueprint, ["get_controller_by_name"], graph_name)
    if ok and controller is not None:
        return controller
    ok, model = call_first(blueprint, ["get_model"])
    if ok and model is not None:
        ok, controller = call_first(blueprint, ["get_controller"], model)
        if ok and controller is not None:
            return controller
    ok, controller = call_first(blueprint, ["get_controller"])
    if ok and controller is not None:
        return controller
    raise RuntimeError("no RigVMController for graph %s" % graph_name)


def clear_graph(controller):
    """A brand new Control Rig already ships with a Forwards Solve node; the JSON
    contains one too, so wipe the graph first to avoid name collisions."""
    ok, model = call_first(controller, ["get_graph"])
    if not ok or model is None:
        return
    removed = 0
    for node in list(model.get_nodes()):
        name = str(node.get_fname())
        gone = False
        for args in ((name, True, False), (name,)):
            try:
                controller.remove_node_by_name(*args)
                gone = True
                break
            except Exception:  # noqa: BLE001
                continue
        if not gone:
            try:
                controller.remove_node(node)
                gone = True
            except Exception as exc:  # noqa: BLE001
                REPORT.warn("could not remove pre-existing node %s: %s" % (name, exc))
        removed += 1 if gone else 0
    REPORT.bump("pre-existing nodes removed", removed)


def struct_paths_for(resolved_function_name):
    """'FRigUnit_GetTransform::Execute' -> candidate /Script/... paths + method."""
    struct, _, method = resolved_function_name.partition("::")
    method = method or "Execute"
    if struct.startswith("F"):
        struct = struct[1:]
    return [("/Script/%s.%s" % (module, struct)) for module in STRUCT_MODULES], method


def add_unit_node(controller, node, node_name):
    fn = node.get("resolved_function_name") or ""
    if not fn:
        REPORT.error("%s: RigVMUnitNode without resolved_function_name" % node_name)
        return None
    candidates, method = struct_paths_for(fn)
    method = node.get("method_name") or method
    position = vec2(node.get("position", {}))
    for path in candidates:
        try:
            created = controller.add_unit_node_from_struct_path(
                path, method, position, node_name, True
            )
            if created is not None:
                return created
        except Exception:  # noqa: BLE001
            continue
    REPORT.error("%s: no struct found for %s (tried %s)" % (node_name, fn, candidates))
    return None


def add_dispatch_node(controller, node, node_name):
    notation = node.get("template_notation") or ""
    if not notation:
        REPORT.error("%s: dispatch node without template_notation" % node_name)
        return None
    position = vec2(node.get("position", {}))
    created = None
    try:
        created = controller.add_template_node(notation, position, node_name, True)
    except Exception as exc:  # noqa: BLE001
        REPORT.error("%s: add_template_node(%s) failed: %s" % (node_name, notation, exc))
        return None
    if created is None:
        REPORT.error("%s: add_template_node returned None for %s" % (node_name, notation))
        return None

    # Resolve the wildcards so the pins get their concrete types (and their
    # struct sub-pins / array elements) back. Without this the node stays a
    # wildcard and the compiler rejects it.
    pins = node.get("pins", {})
    for pin_name, cpp_type in (node.get("resolved_pin_types") or {}).items():
        pin_path = "%s.%s" % (node_name, pin_name)
        if resolve_wildcard(controller, pin_path, cpp_type,
                            pins.get(pin_name, {}).get("cpp_type_object_path", "")):
            REPORT.bump("wildcards resolved")
    return created


def resolve_wildcard(controller, pin_path, cpp_type, type_object_path):
    last = None
    for type_arg in cpp_type_object_args(type_object_path):
        for tail in ((True, False), (True,), ()):
            try:
                controller.resolve_wild_card_pin(pin_path, cpp_type, type_arg, *tail)
                return True
            except Exception as exc:  # noqa: BLE001
                last = exc
                continue
    REPORT.warn("wildcard not resolved: %s -> %s (%s)" % (pin_path, cpp_type, last))
    return False


def add_aggregate_node(controller, node, node_name):
    """RigVMAggregateNode: a unit node whose aggregate pins were expanded.

    In this rig they are Sequence nodes grown from A/B to A/B/C/D. We create the
    plain unit node from the inner graph's function, then call add_aggregate_pin
    once per extra pin, which is exactly what the editor does when you press '+'.
    """
    contained = node.get("contained_graph") or {}
    inner_fn = ""
    for inner in contained.get("nodes", []):
        if inner.get("resolved_function_name"):
            inner_fn = inner["resolved_function_name"]
            break
    if not inner_fn:
        REPORT.error("%s: aggregate node without an inner function" % node_name)
        return None

    stub = dict(node)
    stub["resolved_function_name"] = inner_fn
    created = add_unit_node(controller, stub, node_name)
    if created is None:
        return None

    exec_names = {"ExecuteContext", "ExecutePin"}
    aggregate_pins = [p for p in node.get("pin_order", []) if p not in exec_names]
    # a plain Sequence ships with two aggregate pins (A, B)
    extra = max(0, len(aggregate_pins) - 2)
    for _ in range(extra):
        ok, _res = call_first(controller, ["add_aggregate_pin"], node_name, "", "", True, False)
        if not ok:
            ok, _res = call_first(controller, ["add_aggregate_pin"], node_name, "", "")
        if ok:
            REPORT.bump("aggregate pins added")
        else:
            REPORT.warn("%s: add_aggregate_pin failed - pin %s may be missing"
                        % (node_name, aggregate_pins))
            break
    return created


def add_reroute_node(controller, node, node_name):
    if not CREATE_REROUTE_NODES:
        trace("  reroute skipped by config: %s" % node_name)
        return None

    pin = (node.get("pins") or {}).get("Value", {})
    cpp_type = pin.get("cpp_type", "FRigVMExecuteContext")
    default = pin.get("default_value", "") or ""
    position = vec2(node.get("position", {}))

    is_constant = bool(pin.get("is_constant"))
    widget = pin.get("custom_widget_name", "") or ""

    # Signature reverse-engineered from 5.8's own nativize errors:
    #   AddFreeRerouteNode(FString InCPPType, FName InCPPTypeObjectPath,
    #                      bool bIsConstant, FName InCustomWidgetName,
    #                      FString InDefaultValue, FVector2D InPosition,
    #                      FString InNodeName, bool bSetupUndoRedo, bool bPrint)
    attempts = []
    for method in ("add_free_reroute_node", "add_reroute_node"):
        for type_arg in cpp_type_object_args(pin.get("cpp_type_object_path", "")):
            attempts += [
                (method, (cpp_type, type_arg, is_constant, widget, default,
                          position, node_name, True, False)),
                (method, (cpp_type, type_arg, is_constant, widget, default,
                          position, node_name, True)),
                (method, (cpp_type, type_arg, is_constant, widget, default,
                          position, node_name)),
                # older layouts, kept as fallbacks
                (method, (is_constant, widget, cpp_type, type_arg, default,
                          position, node_name, True, False)),
                (method, (cpp_type, type_arg, default, position, node_name)),
            ]

    last_error = None
    for method, args in attempts:
        fn = getattr(controller, method, None)
        if fn is None:
            continue
        try:
            created = fn(*args)
            if created is not None:
                return created
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    global _REROUTE_API_LOGGED
    hint = ""
    if not _REROUTE_API_LOGGED:
        hint = " RigVMController exposes: %s" % describe_api(controller, "reroute")
        _REROUTE_API_LOGGED = True
    REPORT.warn("%s: reroute node not created (%s) - its links will be bypassed.%s"
                % (node_name, last_error, hint))
    return None


_REROUTE_API_LOGGED = False


def add_variable_node(controller, node, node_name, variables_by_name):
    pins = node.get("pins", {})
    var_name = (pins.get("Variable", {}) or {}).get("default_value", "")
    value_pin = pins.get("Value", {}) or {}
    cpp_type = value_pin.get("cpp_type", "FName")
    default = (variables_by_name.get(var_name, {}) or {}).get("default_value", "")
    position = vec2(node.get("position", {}))
    last = None
    for type_arg in cpp_type_object_args(value_pin.get("cpp_type_object_path", "")):
        for args in (
            (var_name, cpp_type, type_arg, True, default, position, node_name, True, False),
            (var_name, cpp_type, type_arg, True, default, position, node_name, True),
            (var_name, cpp_type, type_arg, True, default, position, node_name),
        ):
            try:
                created = controller.add_variable_node(*args)
                if created is not None:
                    return created
            except Exception as exc:  # noqa: BLE001
                last = exc
                continue
    REPORT.error("%s: variable node for '%s' could not be created (%s)"
                 % (node_name, var_name, last))
    return None


def add_comment_node(controller, node, node_name):
    text = node.get("node_title") or ""
    position = vec2(node.get("position", {}))
    size = unreal.Vector2D(400.0, 200.0)
    color = linear_color(node.get("node_color") or {"r": 0.15, "g": 0.15, "b": 0.15, "a": 0.5})
    for args in (
        (text, position, size, color, node_name, True),
        (text, position, size, color, node_name),
    ):
        try:
            created = controller.add_comment_node(*args)
            if created is not None:
                return created
        except Exception:  # noqa: BLE001
            continue
    REPORT.warn("%s: comment node skipped" % node_name)
    return None


SKIPPED_CLASSES = {"RigVMFunctionEntryNode", "RigVMFunctionReturnNode"}
DEFAULT_TITLES = {"Sequence", "Branch", "And", "Get Transform", "Set Transform",
                  "Get Transform Array", "Set Transform Array", "Get Interaction",
                  "Get Parent", "Spawn Null", "Construction Event", "Forwards Solve",
                  "Step Dynamics Solver", "Spawn Dynamics Chains", "Spawn Dynamics Solver",
                  "Set Dynamics Particle Strength"}


def create_nodes(controller, graph, name_map, variables_by_name):
    created = {}
    skipped = set()
    for node in graph.get("nodes", []):
        raw_name = node["name"]
        node_name = name_map[raw_name]
        cls = node.get("class_short", "")

        if cls in SKIPPED_CLASSES:
            continue

        trace("node %-24s %-22s %s" % (cls, node_name, node.get("resolved_function_name")
                                       or node.get("template_notation") or ""))

        if cls == "RigVMUnitNode":
            obj = add_unit_node(controller, node, node_name)
        elif cls == "RigVMDispatchNode":
            obj = add_dispatch_node(controller, node, node_name)
        elif cls == "RigVMAggregateNode":
            obj = add_aggregate_node(controller, node, node_name)
        elif cls == "RigVMRerouteNode":
            obj = add_reroute_node(controller, node, node_name)
        elif cls == "RigVMVariableNode":
            obj = add_variable_node(controller, node, node_name, variables_by_name)
        elif cls == "RigVMCommentNode":
            obj = add_comment_node(controller, node, node_name)
        else:
            REPORT.warn("%s: unhandled node class %s" % (node_name, cls))
            skipped.add(raw_name)
            continue

        if obj is None:
            skipped.add(raw_name)
            continue

        created[raw_name] = obj
        REPORT.bump("nodes created")

        actual = str(obj.get_fname())
        if actual != node_name:
            # UE renamed it (collision / illegal char) - keep links consistent.
            REPORT.warn("node created as '%s' instead of '%s'" % (actual, node_name))
            name_map[raw_name] = actual
            node_name = actual

        call_first(controller, ["set_node_position_by_name"], node_name,
                   vec2(node.get("position", {})))

        color = node.get("node_color")
        if color and cls != "RigVMCommentNode":
            call_first(controller, ["set_node_color_by_name"], node_name, linear_color(color))

        title = node.get("node_title") or ""
        if title and title not in DEFAULT_TITLES and cls != "RigVMCommentNode":
            ok, _ = call_first(controller, ["set_node_title_by_name"], node_name, title)
            if not ok:
                call_first(controller, ["set_node_title"], obj, title)

    return created, skipped


# ----------------------------------------------------------------------------
# pin defaults
# ----------------------------------------------------------------------------

def children_of(pins):
    tree = {}
    for path, info in pins.items():
        tree.setdefault(info.get("parent_path", "") or "", []).append(path)
    for parent, kids in tree.items():
        # array elements must be ordered 0,1,2..., struct members can be anything
        def sort_key(path):
            leaf = path.rsplit(".", 1)[-1]
            return (0, int(leaf)) if leaf.isdigit() else (1, leaf)
        kids.sort(key=sort_key)
    return tree


def set_pin_default(controller, pin_path, value, quiet=False):
    trace("  pin  %s = %s" % (pin_path, _short((value,))))
    for args in ((pin_path, value, True, True, False), (pin_path, value, True), (pin_path, value)):
        try:
            controller.set_pin_default_value(*args)
            REPORT.bump("pin defaults set")
            return True
        except Exception:  # noqa: BLE001
            continue
    if not quiet:
        REPORT.warn("pin default not applied: %s = %s" % (pin_path, _short((value,))))
    return False


QUOTED_TYPES = ("FName", "FString", "FText")


def build_literal(pins, tree, path):
    """Reconstruct a UE ImportText literal for a pin from the exported sub-pins.

    (Type=Control,Name="Bone_01_ctrl") for structs,
    ((..),(..)) for arrays - matching the `literal` strings in item_arrays.
    """
    info = pins[path]
    kids = tree.get(path, [])
    cpp_type = info.get("cpp_type", "")

    if not kids:
        value = info.get("default_value")
        if value in (None, ""):
            return None
        if cpp_type in QUOTED_TYPES:
            return '"%s"' % value
        return value

    parts = []
    if cpp_type.startswith("TArray<"):
        for child in kids:
            piece = build_literal(pins, tree, child)
            parts.append(piece if piece is not None else "()")
        return "(" + ",".join(parts) + ")"

    for child in kids:
        piece = build_literal(pins, tree, child)
        if piece is None:
            continue
        parts.append("%s=%s" % (child.rsplit(".", 1)[-1], piece))
    if not parts:
        return None
    return "(" + ",".join(parts) + ")"


def size_array_pin(controller, pin_path, size):
    for args in ((pin_path, size, "", True, False), (pin_path, size, ""), (pin_path, size)):
        try:
            controller.set_array_pin_size(*args)
            REPORT.bump("array pins sized")
            return True
        except Exception:  # noqa: BLE001
            continue
    # fall back to adding elements one by one
    added = 0
    for _ in range(size):
        try:
            controller.add_array_pin(pin_path, "", True, False)
            added += 1
        except Exception:  # noqa: BLE001
            try:
                controller.add_array_pin(pin_path, "")
                added += 1
            except Exception:  # noqa: BLE001
                break
    if added == size:
        REPORT.bump("array pins sized")
        return True
    REPORT.warn("array pin %s: wanted %d elements, created %d" % (pin_path, size, added))
    return False


def apply_pin_defaults(controller, node, node_name, linked_targets):
    pins = node.get("pins", {})
    if not pins:
        return
    tree = children_of(pins)

    def any_linked(path):
        full = "%s.%s" % (node_name, path)
        if full in linked_targets:
            return True
        return any(any_linked(child) for child in tree.get(path, []))

    def walk(path):
        info = pins[path]
        full = "%s.%s" % (node_name, path)
        if info.get("direction") in ("Output", "Hidden"):
            return
        if full in linked_targets:
            return

        kids = tree.get(path, [])
        is_array = info.get("cpp_type", "").startswith("TArray<")

        if is_array and kids:
            # One-shot literal first: set_pin_default_value with resize_arrays
            # both grows the array and fills the elements, which works even when
            # set_array_pin_size / add_array_pin refuse the pin.
            if not any_linked(path):
                literal = build_literal(pins, tree, path)
                if literal and set_pin_default(controller, full, literal, quiet=True):
                    REPORT.bump("array pins filled from literal")
                    return
            if size_array_pin(controller, full, len(kids)):
                for child in kids:
                    walk(child)
            return

        if kids:
            if not any_linked(path):
                # Rebuild from the sub-pins FIRST. The exporter writes the
                # struct's factory default into the parent pin's default_value
                # (e.g. SpawnControl_2.Settings says Shape.Name="Default") while
                # the real values only live on the leaves
                # (Settings.Shape.Name="RoundedSquare_Thick"). Trusting the
                # parent literal silently reverts shape names, colours and
                # shape transforms.
                literal = build_literal(pins, tree, path)
                if literal and set_pin_default(controller, full, literal, quiet=True):
                    return
                # only fall back to the exported parent literal
                literal = info.get("default_value") or ""
                if (literal and literal != "()" and info.get("has_default_value")
                        and set_pin_default(controller, full, literal, quiet=True)):
                    return
            for child in kids:
                walk(child)
            return

        if not info.get("has_default_value"):
            return
        if info.get("default_value_type") == "Unset":
            return
        literal = info.get("default_value")
        if literal in (None, ""):
            return
        set_pin_default(controller, full, literal)

    for root in tree.get("", []):
        walk(root)


# ----------------------------------------------------------------------------
# links
# ----------------------------------------------------------------------------

def bypass_missing_reroutes(graph, skipped_nodes):
    """Collapse chains through reroute nodes we could not create.

    A reroute is a pure pass-through, so  A -> R1.Value -> R2.Value -> B
    becomes  A -> B  when R1/R2 are missing. Returns (raw) link pairs.
    """
    reroutes = set(n["name"] for n in graph.get("nodes", [])
                   if n.get("class_short") == "RigVMRerouteNode")
    # Only reroutes are safe to collapse; any other missing node means its links
    # are genuinely lost and must be reported, not silently rewired.
    bypassable = skipped_nodes & reroutes
    lost = skipped_nodes - reroutes

    if not skipped_nodes:
        return [(l["source"], l["target"]) for l in graph.get("links", [])]

    skipped_nodes = bypassable
    upstream = {}
    for link in graph.get("links", []):
        node, _ = split_pin_path(link["target"])
        if node in skipped_nodes:
            upstream[node] = link["source"]

    def real_source(pin_path, seen=None):
        seen = seen or set()
        node, _ = split_pin_path(pin_path)
        while node in skipped_nodes:
            if node in seen:
                return None  # cyclic reroute chain, give up
            seen.add(node)
            pin_path = upstream.get(node)
            if not pin_path:
                return None
            node, _ = split_pin_path(pin_path)
        return pin_path

    resolved = []
    for link in graph.get("links", []):
        target_node, _ = split_pin_path(link["target"])
        source_node, _ = split_pin_path(link["source"])
        if target_node in lost or source_node in lost:
            REPORT.error("link dropped, node was not created: %s -> %s"
                         % (link["source"], link["target"]))
            continue
        if target_node in skipped_nodes:
            continue  # internal edge of a collapsed chain
        source = real_source(link["source"])
        if source is None:
            REPORT.error("could not bypass reroute chain feeding %s" % link["target"])
            continue
        if source != link["source"]:
            REPORT.bump("links rerouted around missing nodes")
        resolved.append((source, link["target"]))
    return resolved


def try_add_link(controller, source, target):
    trace("  link %s -> %s" % (source, target))
    last = None
    for args in ((source, target, True, False), (source, target, True), (source, target)):
        try:
            controller.add_link(*args)
            return True, None
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
    return False, last


def create_links(controller, resolved_links, name_map):
    pending = [
        (remap_pin_path(src, name_map), remap_pin_path(dst, name_map))
        for src, dst in resolved_links
    ]

    # Several passes: a link into a struct sub-pin of a template node only
    # becomes legal once some other link has resolved that node's wildcard, so
    # a failure in pass N can succeed in pass N+1.
    last_error = {}
    for attempt in range(1, 4):
        failed = []
        for source, target in pending:
            ok, exc = try_add_link(controller, source, target)
            if ok:
                REPORT.bump("links created")
            else:
                last_error[(source, target)] = exc
                failed.append((source, target))
        no_progress = len(failed) == len(pending)
        pending = failed          # must happen before we break, or the report
        if not pending:           # below re-reports links that already succeeded
            break
        if no_progress:
            break
        log("link pass %d: %d still failing, retrying" % (attempt, len(pending)))

    for source, target in pending:
        REPORT.error("link failed: %s -> %s (%s)" % (source, target, last_error.get((source, target))))


# ----------------------------------------------------------------------------
# finishing
# ----------------------------------------------------------------------------

def compile_and_finish(blueprint):
    trace("PHASE compile")
    ok, _ = call_first(blueprint, ["recompile_vm"])
    if not ok:
        call_first(unreal.ControlRigBlueprintLibrary, ["recompile_vm"], blueprint)
    REPORT.bump("compiled", 1)

    if RUN_CONSTRUCTION_AFTER_BUILD:
        trace("PHASE construction")
        ok, _ = call_first(blueprint, ["request_construction"])
        if not ok:
            call_first(unreal.ControlRigBlueprintLibrary, ["request_construction"], blueprint)

    if SAVE_WHEN_DONE:
        trace("PHASE save")
        try:
            unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False)
            REPORT.bump("saved", 1)
        except Exception as exc:  # noqa: BLE001
            REPORT.warn("save failed: %s" % exc)
    trace("PHASE done")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def rebuild(json_path=JSON_PATH):
    trace_reset()
    trace("PHASE load json")
    data = load_export(json_path)

    asset_info = data.get("asset", {})
    graph = data.get("graph", {})
    variables = data.get("variables", [])
    hierarchy_info = data.get("hierarchy", {})

    trace("PHASE create asset")
    blueprint, mesh = create_blueprint(asset_info)
    trace("PHASE configure asset")
    configure_asset(blueprint, mesh, asset_info)
    trace("PHASE import bones")
    import_bones(blueprint, mesh, hierarchy_info)
    if CREATE_HIERARCHY_ELEMENTS:
        trace("PHASE hierarchy elements")
        create_hierarchy_elements(blueprint, hierarchy_info)
    trace("PHASE variables")
    create_variables(blueprint, variables)

    trace("PHASE get controller")
    controller = get_controller(blueprint, graph.get("graph_name", "RigVMModel"))
    call_first(controller, ["open_undo_bracket"], "Rebuild Control Rig from JSON")

    try:
        trace("PHASE clear graph")
        clear_graph(controller)

        name_map = build_name_map(graph)
        variables_by_name = {v["name"]: v for v in variables}

        trace("PHASE create nodes")
        created, skipped_nodes = create_nodes(controller, graph, name_map, variables_by_name)

        resolved_links = bypass_missing_reroutes(graph, skipped_nodes)
        linked_targets = set(remap_pin_path(pair[1], name_map) for pair in resolved_links)

        trace("PHASE pin defaults")
        for node in graph.get("nodes", []):
            if node["name"] not in created:
                continue
            trace(" defaults for %s" % name_map[node["name"]])
            apply_pin_defaults(controller, node, name_map[node["name"]], linked_targets)

        trace("PHASE links")
        create_links(controller, resolved_links, name_map)
    finally:
        call_first(controller, ["close_undo_bracket"])

    compile_and_finish(blueprint)

    expected_nodes = len([n for n in graph.get("nodes", [])
                          if n.get("class_short") not in SKIPPED_CLASSES])
    log("expected %d top-level nodes, %d links" % (expected_nodes, len(graph.get("links", []))))
    REPORT.dump()
    return blueprint


if __name__ == "__main__":
    rebuild()
else:
    rebuild()
