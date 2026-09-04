# RebuildControlRigFromJson —— UE 5.8 Control Rig 文本导出 → JSON → 重建

把一个 UE 5.8 的 Control Rig 资产**导出成自描述 JSON**，再在另一个工程/引擎里**从 JSON 重建**出等价的 Control Rig 蓝图。

本目录里的一整套数据对应的源资产是 `/Game/Materials_Learn/CR_SKM_WaterUP1_A1`（一个水体动力学 rig），可以直接当参考样例看。



## 数据流

```
① 手工：Content Browser 选中 ControlRig → Ctrl+C → 粘贴保存
      └─────────────────────────────────────────► to-json.txt
                                                      │
② ue58_controlrig_text_to_json.py（UE 外，纯标准库）    │
      to-json.txt ────────────────────────────────────►┴──► controlrig_rebuild.json
                                                              │
④ rebuild_controlrig_ue58.py（UE 内，写资产）                  │
      controlrig_rebuild.json ────────────────────────────────┘
      └──► 新蓝图 /Game/Materials_Learn/CR_SKM_WaterUP1_A1_Rebuilt
      └──► rebuild_trace.log
```

## ⚠️ 运行 rebuild 脚本前必读

**1. 这个脚本 import 即执行。** 文件末尾是：

```python
if __name__ == "__main__":
    rebuild()
else:
    rebuild()
```

两个分支都调 `rebuild()`——无论直接运行还是被 `import` / `exec`，加载瞬间就开始重建。没有"只加载不执行"的模式，也没有 dry-run 和确认提示。

**2. 它会删除同名的目标资产。** `free_target_path()` 发现 `/Game/Materials_Learn/CR_SKM_WaterUP1_A1_Rebuilt` 已存在时，会强制关闭它的所有编辑器窗口然后 `delete_asset`。删不掉才退让改名成 `_2`…`_99`。

**3. 默认配置不会碰原资产**，因为目标名是 `CR_SKM_WaterUP1_A1_Rebuilt`。但如果把 `TARGET_PACKAGE_PATH` / `TARGET_ASSET_NAME` 设成 `None`，目标就会回落到 JSON 里的 `asset.runtime_asset_path`，**那样会删掉并覆盖原始 rig**。代码注释已标注 `not recommended`。

## 用法

### ② 文本 → JSON（在普通 Python 里跑）

```bash
python ue58_controlrig_text_to_json.py                          # 用默认路径
python ue58_controlrig_text_to_json.py <输入.txt> <输出.json>
python ue58_controlrig_text_to_json.py --dry-run                # 只打摘要不写文件
python ue58_controlrig_text_to_json.py --compact                # 紧凑 JSON
```

默认路径（本目录内，开箱即用）：

```python
DEFAULT_SOURCE = r"...\RebuildControlRigFromJson\to-json.txt"
DEFAULT_OUTPUT = r"...\RebuildControlRigFromJson\controlrig_rebuild.json"
```

退出码：`0` 成功，`1` 结构异常/写出失败，`2` 输入文件不存在或非 UTF-8。只读输入、只写输出，不碰任何 UE 资产。

### ③ 导出层级文本（在 UE Editor 里跑，可选）

`Tools > Execute Python Script` 运行。顶部三个常量：

```python
SOURCE_ASSET = "/Game/Materials_Learn/CR_SKM_Water_UP1"
TEXT_OUT     = r"...\ClaudeCode_Spawn\source_hierarchy.txt"
JSON_PATH    = r"...\ClaudeCode_Spawn\controlrig_rebuild.json"
```

只读源资产，写两个本地文件：`TEXT_OUT`，以及在 `JSON_PATH` 指向的 JSON **已存在时**回写 `hierarchy.export_text` 和 `hierarchy.export_text_source` 两个字段。

### ④ 重建（在 UE Editor 里跑）

`Window > Output Log` → 输入框切到 `Python`：

```python
exec(open(r"H:/ClaudeCode_Spawn/RebuildControlRigFromJson/rebuild_controlrig_ue58.py", encoding="utf-8").read())
```

主要配置常量：

| 常量 | 默认值 | 作用 |
| --- | --- | --- |
| `JSON_PATH` | 本目录 `controlrig_rebuild.json` | 输入 JSON |
| `TARGET_PACKAGE_PATH` | `"/Game/Materials_Learn"` | 目标包路径，`None` = 覆盖原资产（不推荐） |
| `TARGET_ASSET_NAME` | `"CR_SKM_WaterUP1_A1_Rebuilt"` | 目标资产名 |
| `SANITIZE_NON_ASCII_NODE_NAMES` | `True` | 中文节点名罗马化成 ASCII |
| `CREATE_HIERARCHY_ELEMENTS` | `False` | 是否预创建 Control/Null。本 rig 的 Construction Event 自己会 spawn，所以只需导入骨骼 |
| `CREATE_REROUTE_NODES` | `False` | 是否重建 reroute 节点。5.8 上探测 `AddFreeRerouteNode` 签名不稳定，默认跳过并压缩连线，图功能等价 |
| `RUN_CONSTRUCTION_AFTER_BUILD` | `True` | 编译后执行 Construction |
| `SAVE_WHEN_DONE` | `True` | 结束后保存资产 |
| `ENABLE_TRACE` | `True` | 每次引擎调用写一行 trace 并立即 flush，编辑器硬崩时最后一行就是元凶 |
| `TRACE_PATH` | JSON 同目录 `rebuild_trace.log` | trace 输出，每次运行覆盖 |
| `STRUCT_MODULES` | 7 个模块 | 把 `FRigUnit_X::Execute` 解析成 `/Script/<Module>.<Struct>` 时依次探测的模块 |

重建流程：读 JSON → 建蓝图 → 配置预览网格/形状库 → `import_bones` →（可选建层级元素）→ 建成员变量 → 取 controller → 清空默认图 → 建节点 → 设置 pin 默认值 → 建连线（最多 3 轮重试）→ 编译 / Construction / 保存。

**容错策略**：单个引擎 API 调用失败不中断整体，错误收集进 `Report` 最后统一 `dump()`（打印到 Output Log，并因为走 `log()` 而一并进 trace 文件），保证产出一个可检查、可继续调试的部分资产，而不是半截毁坏的状态。

## JSON 结构（v2.0）

11 个顶层 key：

| key | 内容 | 本样例实际值 |
| --- | --- | --- |
| `schema` | 格式名/版本/来源 | `UE58ControlRigTextExport` v2.0 |
| `source` | 输入 txt 的路径与规模 | 16830 行 / 3994768 字符 |
| `asset` | 资产名、路径、预览网格、形状库、支持的事件 | `CR_SKM_WaterUP1_A1`，事件 `Forwards Solve` + `Construction` |
| `variables` | 成员变量 | 1 个：`ParticleComponentName`（FName = `DynamicsParticle`） |
| `graph` | 主图 `RigVMModel` 的节点与连线，节点可嵌 `contained_graph` 递归 | 顶层 89 节点 / 96 连线；递归后 99 节点 / 110 连线 |
| `element_keys` | 去重的 RigElementKey 及引用点 | 15 |
| `item_arrays` | 常量 `TArray<FRigElementKey>` 数组内容 | 9 |
| `metadata_usage` | Metadata 读写记录 | 1 |
| `hierarchy` | **推断出来的**层级方案 | bones 6 / controls 7 / nulls 2 / animation_channels 4 |
| `rebuild_plan` | 11 条中文重建步骤清单 | — |
| `diagnostics` | 各类告警与限制 | 见下 |

节点条目固定 13 个字段：`name / class / class_short / position / node_title / node_color / resolved_function_name / template_notation / method_name / resolved_pin_types / pin_order / pins / contained_graph`。连线极简：`{"source": "NodeA.Pin", "target": "NodeB.Pin"}`。

顶层节点分类：UnitNode 48、Dispatch 21、Reroute 14、Aggregate 2、Variable 2、Comment 2。

`diagnostics` 里 `broken_links`、`node_names_containing_dot`、`empty_item_arrays` 等均为空；`node_names_with_non_ascii` 有 7 个中文节点名（`查找`、`获取元数据`、`设置元数据`×3、`选择`、`针对每个`）；`controls_without_matching_bone` 有 1 个（`proxy_ctrl`）。

## 上一次重建的实际结果

[rebuild_trace.log](rebuild_trace.log) 记录的是**部分成功**，不是干净成功：

```
asset created 1    compiled 1    saved 1
nodes created  71   （预期顶层 89）
links created  70   + 绕过缺失节点重连 8   （预期 96）
pin defaults set 152    wildcards resolved 69    aggregate pins added 4
bones in hierarchy 6    variables created 1     shape libraries 1
warnings 0 / errors 16
```

16 个 ERROR = 4 条"找不到 struct" + 12 条"连线被丢弃"：

```
FRigUnit_HierarchySetDynamicsParticleStrength
FRigUnit_StepDynamicsSolver
FRigUnit_SpawnDynamicsChains
FRigUnit_SpawnDynamicsSolver1
```

7 个模块路径都试过仍找不到，**这几个节点很可能来自当前工程未启用或缺失的第三方插件**。连带 12 条指向它们的连线被丢，所以重建后的资产里 dynamics 那条链路是断开的。节点数差额 = 14 个按配置跳过的 reroute + 4 个找不到 struct 的节点。

要修就是在目标工程里启用对应插件后重跑。

## 现状差异（按目前的文件内容，不是猜测）

**1. `ue58_export_hierarchy_text.py` 的路径指向上一级目录。** 它的 `TEXT_OUT` 和 `JSON_PATH` 写的是 `ClaudeCode_Spawn\`，而转换器的 `DEFAULT_OUTPUT` 和重建脚本的 `JSON_PATH` 都在 `ClaudeCode_Spawn\RebuildControlRigFromJson\`。上一级目录下这两个文件都不存在，所以按现状直接跑第 ③ 步会走到"JSON 不存在，跳过写回"分支。要把三步串起来，得先把这两个常量改到本目录。

**2. `hierarchy.export_text` 目前没人消费。** `rebuild_controlrig_ue58.py` 里 grep 不到 `export_text` 或 `import_from_text` 的任何引用；现存的 `controlrig_rebuild.json` 里也没有这个字段。重建脚本只从 `hierarchy` 取 `bones` 走 `import_bones`，以及默认关闭的 `create_hierarchy_elements`。第 ③ 步产出的数据是**为将来的 `import_from_text` 路线准备的**，在当前链路上是可选项。

**3. 重建脚本 docstring 里的 exec 路径少了一层目录**（写的是 `ClaudeCode_Spawn/rebuild_controlrig_ue58.py`），照抄会找不到文件。用上面「④ 重建」里的完整路径。

**4. JSON 里的源资产名与第 ③ 步的 `SOURCE_ASSET` 不是同一个**：JSON 记的是 `CR_SKM_WaterUP1_A1`，而 `SOURCE_ASSET = "/Game/Materials_Learn/CR_SKM_Water_UP1"`。用之前先确认要导的是哪个资产。

## 为什么需要这么绕：UE 文本导出的坑

**Hierarchy 是空的。** 已实测确认：`to-json.txt` 里 `RigHierarchy` 对象出现两次（声明段 + 数据段），两处都只包含一个 `RigHierarchyController` 子对象，**零属性、零元素**。全文 `Type=Bone|Control|Null` 只有 8 处命中，全部来自图节点的 pin 默认值，不是元素表。所以骨骼/控制器/Null 的父子关系、Offset、形状、颜色、通道默认值**完全没有导出**，只能靠图里引用到的 `RigElementKey` 反推——这就是 JSON 里 `hierarchy.requires_external_source = true` 的根因。

**据 `ue58_export_hierarchy_text.py` 的说明**（作者实测结论）：UE 5.8 的 `set_control_offset_transform` 在 Python 里是**静默 no-op**，调用不报错也不写入，所以逐元素重建根本摆不好控制器位置；而 `RigHierarchyController.export_to_text` / `import_from_text` 配对使用，与源资产逐元素比对 0 差异。这是第 ③ 步存在的理由。

**导出文本是两段式的。** UE 把同一个对象导出两次且是并列的兄弟节点：声明段只有 `Class=` 和层级，数据段只有属性。解析器必须按**路径**合并两段（类型取声明段，属性取数据段），不能建全局的"名称 → 类"映射——因为 `Value` / `Type` / `Name` 这类 pin 名在文件里重复上百次。

**其他已知坑**（均来自脚本注释，逐条列出）：

- `Rig` / `*_SubGraph` / `RigVMFunctionLibraryEdGraph` 是 `ControlRigGraph`，属编辑器视觉镜像，节点与 RigVMGraph 一一重复，必须整棵跳过
- 聚合节点 `RigVMAggregateNode` 带 `ContainedGraph` 子图，需要递归解析
- 节点名可含空格（`Set Transform`）和中文（`查找`）；连线路径按**第一个**点号切分，所以节点名不能含点号
- 导出文本里中文节点名是 UTF-8 字节被按 latin-1 解码的 mojibake（`è®¾ç½®åæ°æ®_2`），重建时先 `encode("latin-1").decode("utf-8")` 修复，再可选罗马化
- 数组 pin 必须先 `add_array_pin` 建出元素再逐个设叶子默认值，直接给父 pin 塞字符串默认值无效
- struct 父 pin 的 `default_value` 是**工厂默认值**，真实值只在叶子上。信父 pin 的字面值会静默把形状名、颜色、形状 transform 回退成默认——必须用子 pin 重组字面值
- Dispatch/模板节点必须先 `resolve_wild_card_pin` 固化类型，否则编译器拒绝
- 进 template 节点 struct 子 pin 的连线，要等别的连线先解析了该节点的 wildcard 才合法，所以连线需要多轮重试
- 打开着编辑器窗口的 Control Rig 删不掉，`ForceDelete` 会留下损坏的 package——必须先 `close_all_editors_for_asset`
- 5.8 移除了 `get_bone_keys()` / `get_control_keys()`，改用 `get_all_keys()` / `get_keys()`；`cpp_type_object` 参数从 UObject 变成了 FName 路径。脚本对这类差异统一用"多签名穷举 + 探测失败就把该 build 实际暴露的成员打进 Report"的方式兼容
