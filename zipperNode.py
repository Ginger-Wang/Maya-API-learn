# -*- coding: UTF-8 -*-
import sys
from maya import OpenMaya, OpenMayaMPx
om = OpenMaya
omm = OpenMayaMPx

class CreateZipperNode(omm.MPxNode):
    kNodeName = "newZipperNode"
    kTypeID = om.MTypeId(0x01021)
    zip = om.MObject()
    zipType = om.MObject()
    attenuation = om.MObject()
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
        mFnEnumAttr = om.MFnEnumAttribute()

        thisNode.zipType = mFnEnumAttr.create("zipType","zt")
        for feild,value in zip(["Tip","End","BothEnd"],range(3)):
            mFnEnumAttr.addField(feild,value)
        mFnEnumAttr.setWritable(True)
        mFnEnumAttr.setStorable(True)
        mFnEnumAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.zipType)

        thisNode.attenuation = mFnNumAttr.create("attenuation","at",om.MFnNumericData.kFloat,0.0)
        mFnNumAttr.setKeyable(True)
        mFnNumAttr.setMin(0.0)
        mFnNumAttr.setSoftMax(1.0)
        mFnNumAttr.setMax(2.0)
        thisNode.addAttribute(thisNode.attenuation)

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
        thisNode.attributeAffects(thisNode.zipType, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.attenuation, thisNode.outCurve)



    def compute(self, plug, dataBlock):
        if plug == self.outCurve:
            zipHandle = dataBlock.inputValue(self.zip)
            typeHandle = dataBlock.inputValue(self.zipType)
            targetCurvehandle = dataBlock.inputValue(self.inputTarget)
            attenuationHandle = dataBlock.inputValue(self.attenuation)
            typeValue = typeHandle.asInt()
            zipValue = zipHandle.asFloat()
            attenuationValue = attenuationHandle.asFloat()

            incurveHandle = dataBlock.inputValue(self.input)
            incurveObject = incurveHandle.asNurbsCurve()
            targetCurveObject = targetCurvehandle.asNurbsCurve()
            outCurveHandle = dataBlock.outputValue(self.outCurve)
            cvs = om.MPointArray()
            if not incurveObject.isNull():
                curveFn = om.MFnNurbsCurve(incurveObject)
                targetCurve = om.MFnNurbsCurve(targetCurveObject)
                curveFn.getCVs(cvs, om.MSpace.kWorld)
                lenNum = cvs.length()
                cvsLength = float(lenNum)
                if cvsLength%2:
                    halfValue = (cvsLength + 1) / 2.0
                else:
                    halfValue = (cvsLength) / 2.0 + 1.0
                sped = (10.0 - attenuationValue) / cvsLength
                mPoint = om.MPoint()
                cvsPoints = om.MPointArray()
                cvsPoints.setLength(lenNum)
                valAt_util = om.MScriptUtil()
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
                    if typeValue == 0:
                        oldMin = sped * count
                        oldMax = sped * (count + 1.0) + attenuationValue
                    elif typeValue == 1:
                        oldMin = sped * (cvsLength-count-1.0)
                        oldMax = sped * (cvsLength-count) + attenuationValue
                    else:
                        if count < (halfValue-1):
                            oldMin = sped * count
                            oldMax = sped * (count + 1) * 2.0 + attenuationValue
                        elif count > (halfValue-1):
                            oldMin = sped * (cvsLength - count - 1.0)
                            oldMax = sped * (cvsLength - count) * 2.0 + attenuationValue
                        else:
                            oldMin = sped * (cvsLength - count - 1.0)
                            oldMax = 10
                    mPoint.x = getOutputValue(cvs[count].x, points.x, oldMin, oldMax, zipValue)
                    mPoint.y = getOutputValue(cvs[count].y, points.y, oldMin, oldMax, zipValue)
                    mPoint.z = getOutputValue(cvs[count].z, points.z, oldMin, oldMax, zipValue)
                    cvsPoints.set(mPoint, count)
                newCurveFn.setCVs(cvsPoints)
                newCurveFn.updateCurve()
                outCurveHandle.setMObject(newCurveData)
                outCurveHandle.setClean()
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
 
