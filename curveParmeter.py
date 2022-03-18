# -*- coding: UTF-8 -*-
import sys
from maya import OpenMaya, OpenMayaMPx
#
#This node is get the parameter value on the  curve according to the percentage of the input curve length
#


om = OpenMaya
omm = OpenMayaMPx

class CurveParameterNode(omm.MPxNode):
    kNodeName = "curveParmeter"
    kTypeID = om.MTypeId(0x01023)
    percent = om.MObject()
    input = om.MObject()
    parameter = om.MObject()

    def __init__(self):
        omm.MPxNode.__init__(self)

    @staticmethod
    def curveParmeter_creator():
        return omm.asMPxPtr(CurveParameterNode())

    @staticmethod
    def curveParmeter_initalize():
        thisNode = CurveParameterNode
        mFnNumAttr = om.MFnNumericAttribute()
        mFnTypeAttr = om.MFnTypedAttribute()

        thisNode.percent = mFnNumAttr.create("percent", "per", om.MFnNumericData.kFloat, 0.0)
        mFnNumAttr.setKeyable(True)
        mFnNumAttr.setMin(0.0)
        mFnNumAttr.setMax(100.0)
        thisNode.addAttribute(thisNode.percent)

        thisNode.input = mFnTypeAttr.create("input", "in", om.MFnNurbsCurveData.kNurbsCurve)
        mFnTypeAttr.setStorable(False)
        mFnTypeAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.input)


        thisNode.parameter = mFnNumAttr.create("parameter", "pr", om.MFnNumericData.kFloat, 0.0)
        mFnNumAttr.setKeyable(False)
        mFnNumAttr.setStorable(False)
        mFnNumAttr.setWritable(False)
        thisNode.addAttribute(thisNode.parameter)

        thisNode.attributeAffects(thisNode.input, thisNode.parameter)
        thisNode.attributeAffects(thisNode.percent, thisNode.parameter)


    def compute(self, plug, dataBlock):
        if plug == self.parameter:
            percentHandle = dataBlock.inputValue(self.percent)
            percentValue = percentHandle.asFloat()
            incurveHandle = dataBlock.inputValue(self.input)
            incurveObject = incurveHandle.asNurbsCurve()
            parameterHandle = dataBlock.outputValue(self.parameter)
            if not incurveObject.isNull():
                curveFn = om.MFnNurbsCurve(incurveObject)
                curveLength = curveFn.length()
                parameter = curveFn.findParamFromLength(curveLength*percentValue*0.01)
                parameterHandle.setFloat(parameter)
            else:
                pass
            dataBlock.setClean(plug)
def initializePlugin(obj):
    thisNode = CurveParameterNode
    pluginFn = omm.MFnPlugin(obj, "Wang Jinge - WeChat:370871841", "0.0.1", "Any")
    try:
        pluginFn.registerNode(
            thisNode.kNodeName,
            thisNode.kTypeID,
            thisNode.curveParmeter_creator,
            thisNode.curveParmeter_initalize
        )
        print("%s initialized..."%(thisNode.kNodeName))
    except:
        sys.stderr.write("Failed to register node: %s" % thisNode.kNodeName)



def uninitializePlugin(obj):
    thisNode = CurveParameterNode
    pluginFn = omm.MFnPlugin(obj)
    try:
        pluginFn.deregisterNode(thisNode.kTypeID)
    except:
        sys.stderr.write("Failed to deregister node : %s" % thisNode.kNodeName)
