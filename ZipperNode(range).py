# -*- coding: UTF-8 -*-
import sys, math
from maya import OpenMaya, OpenMayaMPx, cmds, mel

om = OpenMaya
omm = OpenMayaMPx


class CreateZipperNode(omm.MPxNode):
    kNodeName = "newAZipperNode"
    kTypeID = om.MTypeId(0x01021)
    bias = om.MObject()
    zip = om.MObject()
    input = om.MObject()
    inputTarget = om.MObject()
    outCurve = om.MObject()

    def __init__(self):
        omm.MPxNode.__init__(self)

    @staticmethod
    def zipperNode_creator():
        return omm.asMPxPtr(CreateZipperNode())

    @staticmethod
    def zipperNode_initalize():
        thisNode = CreateZipperNode
        mFnNumAttr = om.MFnNumericAttribute()
        mFnTypeAttr = om.MFnTypedAttribute()

        thisNode.zip = mFnNumAttr.create("zip", "zip", om.MFnNumericData.kFloat, 0.0)
        mFnNumAttr.setKeyable(True)
        mFnNumAttr.setMin(0.0)
        mFnNumAttr.setMax(10.0)
        thisNode.addAttribute(thisNode.zip)

        thisNode.input = mFnTypeAttr.create("input", "in", om.MFnNurbsCurveData.kNurbsCurve)
        mFnTypeAttr.setStorable(False)
        mFnTypeAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.input)

        thisNode.inputTarget = mFnTypeAttr.create("inputTarget", "int", om.MFnNurbsCurveData.kNurbsCurve)
        mFnTypeAttr.setStorable(False)
        mFnTypeAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.inputTarget)

        thisNode.outCurve = mFnTypeAttr.create("outCurve", "outc", om.MFnNurbsCurveData.kNurbsCurve)
        #mFnTypeAttr.setArray(True)
        mFnTypeAttr.setStorable(False)
        mFnTypeAttr.setKeyable(False)
        mFnTypeAttr.setWritable(False)
        #mFnTypeAttr.setUsesArrayDataBuilder(True)
        thisNode.addAttribute(thisNode.outCurve)

        thisNode.attributeAffects(thisNode.inputTarget, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.input, thisNode.outCurve)
        #thisNode.attributeAffects(thisNode.bias, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.zip, thisNode.outCurve)



    def compute(self, plug, dataBlock):
        if plug == self.outCurve:
            zipHandle = dataBlock.inputValue(self.zip)
            targetCurvehandle = dataBlock.inputValue(self.inputTarget)

            # biasValue = biasHandle.asFloat()
            zipValue = zipHandle.asFloat()
            incurveHandle = dataBlock.inputValue(self.input)
            incurveObject = incurveHandle.asNurbsCurve()
            targetCurveObject = targetCurvehandle.asNurbsCurve()
            outCurveHandle = dataBlock.outputValue(self.outCurve)
            outCurve = outCurveHandle.asNurbsCurve()
            cvs = om.MPointArray()
            if not incurveObject.isNull():
                curveFn = om.MFnNurbsCurve(incurveObject)
                targetCurve = om.MFnNurbsCurve(targetCurveObject)
                curveFn.getCVs(cvs, om.MSpace.kWorld)
                lenNum = cvs.length()
                cvsLength = float(lenNum)
                sped = 10.0 / cvsLength
                mPoint = om.MPoint()
                cvsPoints = om.MPointArray()
                cvsPoints.setLength(lenNum)
                valAt_util = om.MScriptUtil()
                valAt_util.createFromDouble(0.0)
                targetMaxParamter = targetCurve.findParamFromLength(targetCurve.length())
                maxParamter = curveFn.findParamFromLength(curveFn.length())
                increment = targetMaxParamter / maxParamter
                newCurveDataFn = om.MFnNurbsCurveData()
                newCurveData = newCurveDataFn.create()
                newCurveFn = om.MFnNurbsCurve()
                newCurveFn.copy(incurveObject, newCurveData)
                newCurveFn.setObject(newCurveData)
                for count in range(lenNum):
                    position = curveFn.closestPoint(cvs[count])
                    points = om.MPoint()
                    parameter = valAt_util.asDoublePtr()
                    curveFn.getParamAtPoint(position, parameter, om.MSpace.kWorld)
                    targetCurve.getPointAtParam(valAt_util.getDouble(parameter) * increment, points, om.MSpace.kWorld)
                    oldMin = sped * count
                    oldMax = sped * (count + 1)

                    mPoint.x = getOutputValue(cvs[count].x, points.x, oldMin, oldMax, zipValue)
                    mPoint.y = getOutputValue(cvs[count].y, points.y, oldMin, oldMax, zipValue)
                    mPoint.z = getOutputValue(cvs[count].z, points.z, oldMin, oldMax, zipValue)
                    cvsPoints.set(mPoint, count)
                newCurveFn.setCVs(cvsPoints)
                newCurveFn.updateCurve()
                outCurveHandle.setMObject(newCurveData)

            dataBlock.setClean(plug)
        else:
            om.kUnknownParameter
def getOutputValue(minValue,maxValue,oldMin,oldMax,Value):
    if oldMin >= Value:
        outputValue = minValue
    elif oldMax <= Value:
        outputValue = maxValue
    else:
        outputValue = (maxValue - minValue) / (oldMax - oldMin) * (Value - oldMin) + minValue
    return outputValue
def initializePlugin(obj):
    thisNode = CreateZipperNode
    pluginFn = omm.MFnPlugin(obj, "Wang Jinge - WeChat:370871841", "0.0.1", "Any")
    try:
        pluginFn.registerNode(
            thisNode.kNodeName,
            thisNode.kTypeID,
            thisNode.zipperNode_creator,
            thisNode.zipperNode_initalize
        )
    except:
        sys.stderr.write("Failed to register node: %s" % thisNode.kNodeName)



def uninitializePlugin(obj):
    thisNode = CreateZipperNode
    pluginFn = omm.MFnPlugin(obj)
    try:
        pluginFn.deregisterNode(thisNode.kTypeID)
    except:
        sys.stderr.write("Failed to deregister node : %s" % thisNode.kNodeName)



