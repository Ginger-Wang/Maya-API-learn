"""testFunctionNode —— 自定义节点的功能测试脚手架。

这个节点本身不做实际运算，用途是验证 add_Attribute 里的属性创建函数
在 Maya 里是否按预期生成属性（类型、单位、可K状态、软硬限制、通道盒是否显示）。
要试新的属性类型时，在 nodeInitializer 里加一段即可。

加载方式:
    把所在目录加入 Maya 的插件搜索路径（MAYA_PLUG_IN_PATH），
    或在插件管理器（Windows > Settings/Preferences > Plug-in Manager）里
    直接浏览到本文件加载。

创建节点:
    import maya.cmds as cmds
    cmds.createNode("testFunctionNode")

注意文件名与节点名不一致: 文件是 functionTest_node.py，节点类型叫 testFunctionNode，
loadPlugin 用文件名，createNode 用节点名。
"""

import sys
import importlib
import maya.OpenMaya as om          # Maya API 1.0 基础类型（MObject / MTypeId / 各类函数集）
import maya.OpenMayaMPx as ompx     # 自定义节点与插件注册相关（MPxNode / MFnPlugin）

# add_Attribute 一旦被 import 就会留在 sys.modules 里，
# 在 Maya 里卸载再加载插件并不会重新执行它 —— 改了 add_Attribute.py 也只会跑到旧代码，
# 表现为"明明写了某个函数却报 ImportError"。开发期在这里强制 reload 规避。
import add_Attribute
importlib.reload(add_Attribute)

NODE_NAME = "testFunctionNode"
# 节点类型的唯一标识。正式发布的插件需要向 Autodesk 申请 ID 段，
# 自用可取 0x00000000-0x0007ffff 区间，但必须保证本机所有插件之间不重复。
NODE_ID = om.MTypeId(0x0007F3A2)

AUTHOR = "Ginger Wang - WeChat:370871841"
VERSION = "1.0.0"
REQUIRED_API_VERSION = "Any"

class FunctionTestNode(ompx.MPxNode):
    # 属性句柄声明为类变量：nodeInitializer 里创建后回填，
    # compute 里再用它们从 dataBlock 取值。每个节点类型只有一份，所有节点实例共享。
    inputRoteta = om.MObject()      # 单值 double
    inRotate = om.MObject()         # 三维角度 angle3
    inTranslate = om.MObject()      # 三维数值 double3
    output = om.MObject()           # 单值 double 输出
    outRotate = om.MObject()        # 三维角度输出
    def __init__(self):
        ompx.MPxNode.__init__(self)

    def compute(self, plug, dataBlock):
        # Maya 在需要某个输出属性的值时调用本方法。
        # plug 是被请求的属性，dataBlock 是本次求值的数据块。
        # 目前只是占位：尚未写出任何值，也未调用 dataBlock.setClean(plug)。
        if plug == FunctionTestNode.output:
            pass

def nodeCreator():
    # 工厂函数：Maya 每次创建该类型节点时调用。
    # asMPxPtr 把 Python 对象的所有权交给 Maya，避免被 Python 垃圾回收掉。
    return ompx.asMPxPtr(FunctionTestNode())

def nodeInitializer():
    # 每个节点类型只执行一次（注册时），负责创建属性并声明依赖关系。
    # 这里一旦抛异常，节点类型会以"已注册但没有属性"的状态留在 Maya 里。
    #
    # 每个属性的写法都是三步：
    #   create_Attribute / createAttr_double3  —— 建属性，同时定可K状态和取值范围
    #   mark_Attribute                          —— 定读 / 写 / 存盘标记
    #   addAttribute                            —— 挂到节点上

    # 输入: 单值 double。isInput=True 即可K，会出现在通道盒里。
    # softMin/softMax 只影响属性编辑器滑块范围，手输仍可超出 0~360
    FunctionTestNode.inputRoteta = add_Attribute.mark_Attribute(
        add_Attribute.create_Attribute(
            "inputRoteta", "inRoteta", "double",
            0.0, softMin=0.0, softMax=360.0, isInput=True))
    ompx.MPxNode.addAttribute(FunctionTestNode.inputRoteta)

    # 输入: 三维角度。X/Y/Z 子属性随父属性一起挂上，不需要再单独 addAttribute。
    # 注意 angle3 的软限制以弧度解释，这里的 360.0 实际是 360 弧度，等于没限制
    FunctionTestNode.inRotate = add_Attribute.mark_Attribute(
        add_Attribute.createAttr_double3(
            "inRotate", "inRot", "angle3",
            0.0, softMin=0.0, softMax=360.0, isInput=True))
    ompx.MPxNode.addAttribute(FunctionTestNode.inRotate)

    # 输入: 三维数值，不设限制
    FunctionTestNode.inTranslate = add_Attribute.mark_Attribute(
        add_Attribute.createAttr_double3(
            "inTranslate", "inTrans", "double3",
            0.0, isInput=True))
    ompx.MPxNode.addAttribute(FunctionTestNode.inTranslate)

    # 输出: isInput=False 即不可K，所以不出现在通道盒，
    # 只能在属性编辑器 / 节点编辑器里看到，或用 cmds.getAttr 读取
    FunctionTestNode.output = add_Attribute.mark_Attribute(
        add_Attribute.create_Attribute(
            "output", "out", "double",
            0.0, isInput=False),
        isWritable=False)
    ompx.MPxNode.addAttribute(FunctionTestNode.output)

    FunctionTestNode.outRotate = add_Attribute.mark_Attribute(
        add_Attribute.createAttr_double3(
            "outRotate", "outRot", "angle3",
            isInput=False),
        isWritable=False)
    ompx.MPxNode.addAttribute(FunctionTestNode.outRotate)

    # 声明依赖：任一输入变化时，把所有输出标记为脏，Maya 下次取值才会调用 compute。
    # 漏掉 attributeAffects 的直接后果是改了输入而输出不更新。
    # 这里用双层循环建立全连接（每个输入影响每个输出）；
    # 实际节点如果某输入只影响部分输出，应逐条声明以减少不必要的重算。
    intputs = (FunctionTestNode.inputRoteta,
               FunctionTestNode.inRotate,
               FunctionTestNode.inTranslate)
    outputs = (FunctionTestNode.output,
               FunctionTestNode.outRotate)

    for input_attr in intputs:
        for output_attr in outputs:
            FunctionTestNode.attributeAffects(input_attr, output_attr)


def initializePlugin(mobject):
    # 插件加载入口，函数名由 Maya 约定，不能改。
    mplugin = ompx.MFnPlugin(mobject, AUTHOR, VERSION, REQUIRED_API_VERSION)
    try:
        mplugin.registerNode(NODE_NAME, NODE_ID, nodeCreator, nodeInitializer)
    except:
        # 注意: 这里吞掉了异常，只留一行提示。
        # nodeInitializer 出错时节点会"有类型但没属性"，而真实堆栈看不到。
        # 排查问题时建议临时改成打印 traceback.format_exc() 并 raise。
        sys.stderr.write("Failed to register node: %s" % NODE_NAME)

def uninitializePlugin(mobject):
    # 插件卸载入口，函数名由 Maya 约定。
    # 场景里还存在该类型节点时反注册会失败，需要先删除节点。
    mplugin = ompx.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(NODE_ID)
    except:
        sys.stderr.write("Failed to deregister node: %s" % NODE_NAME)
