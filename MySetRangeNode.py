# -*- coding: UTF-8 -*-
import sys, math
from maya import OpenMaya, OpenMayaMPx, cmds, mel
om = OpenMaya
omm = OpenMayaMPx



class MySetRangeNode(omm.MPxNode):
    kNodeName = "mySetRangeNode"
    kTypeID = om.MTypeId(0x01019)
    value = om.MObject()
    outValue = om.MObject()
    oldMinMax = om.MObject()
    minMax = om.MObject()
    minNum = om.MObject()
    maxNum = om.MObject()
    oldMin = om.MObject()
    oldMax = om.MObject()

    def __init__(self):
        omm.MPxNode.__init__(self)

    @staticmethod
    def node_creator():
        return omm.asMPxPtr(MySetRangeNode())

    @staticmethod
    def node_initalize():
        thisNode = MySetRangeNode
        mFnFloatAttr = om.MFnNumericAttribute()
        mFnTypeAttr = om.MFnTypedAttribute()
        thisNode.value = mFnFloatAttr.create("value","v",om.MFnNumericData.kDouble,0.0)
        mFnFloatAttr.setKeyable(True)
        #mFnFloatAttr.setMin(0.0)
        thisNode.addAttribute(thisNode.value)

        thisNode.minNum = mFnFloatAttr.create("min","min",om.MFnNumericData.kDouble,0.0)
        mFnFloatAttr.setStorable(True)
        #mFnFloatAttr.setDefault(0.0)

        thisNode.maxNum = mFnFloatAttr.create("max", "max", om.MFnNumericData.kDouble, 1.0)
        mFnFloatAttr.setStorable(True)
        #mFnFloatAttr.setDefault(1.0)

        thisNode.minMax = mFnFloatAttr.create("minMax", "mm",thisNode.minNum,thisNode.maxNum)
        mFnFloatAttr.setKeyable(True)
        mFnFloatAttr.setStorable(True)
        thisNode.addAttribute(thisNode.minMax)

        thisNode.oldMin = mFnFloatAttr.create("oldMin","oldMin",om.MFnNumericData.kDouble,0.0)
        mFnFloatAttr.setStorable(True)
        thisNode.oldMax = mFnFloatAttr.create("oldMax", "oldMax", om.MFnNumericData.kDouble, 0.0)
        mFnFloatAttr.setStorable(True)

        thisNode.oldMinMax = mFnFloatAttr.create("oldMinMax","om",thisNode.oldMin,thisNode.oldMax)
        mFnFloatAttr.setKeyable(True)
        mFnFloatAttr.setStorable(True)
        mFnFloatAttr.setWritable(True)
        mFnFloatAttr.setArray(True)
        thisNode.addAttribute(thisNode.oldMinMax)

        thisNode.outValue = mFnFloatAttr.create("outValue","ov",om.MFnNumericData.kDouble,0.0)
        mFnFloatAttr.setKeyable(False)
        mFnFloatAttr.setWritable(False)
        mFnFloatAttr.setStorable(False)
        mFnFloatAttr.setArray(True)
        thisNode.addAttribute(thisNode.outValue)

        thisNode.attributeAffects(thisNode.minMax,thisNode.outValue)
        thisNode.attributeAffects(thisNode.oldMinMax,thisNode.outValue)
        thisNode.attributeAffects(thisNode.value,thisNode.outValue)

    def compute(self,plug,dataBlock):
        thisNode = self.thisMObject()

        if plug == self.outValue:
            valueHandle = dataBlock.inputValue(self.value)
            minHandle = dataBlock.inputValue(self.minNum)
            maxHandle = dataBlock.inputValue(self.maxNum)
            outValueHandle = dataBlock.outputArrayValue(self.outValue)
            oldArrayHandle = dataBlock.inputArrayValue(self.oldMinMax)
            countNum = oldArrayHandle.elementCount()
            valueNum = valueHandle.asDouble()
            minValue = minHandle.asDouble()
            maxValue = maxHandle.asDouble()
            #outputValue = (maxValue - minValue) * valueNum
            for num in range(countNum):
                oldArrayHandle.jumpToElement(num)
                oldMinValue = oldArrayHandle.inputValue()
                oldMinMaxValueNum = oldMinValue.asDouble2()
                oldMin = oldMinMaxValueNum[0]
                oldMax = oldMinMaxValueNum[1]

                if oldMin >= valueNum:
                    outputValue = minValue
                elif oldMax <= valueNum:
                    outputValue = maxValue
                else:
                    outputValue = (maxValue - minValue) / (oldMax - oldMin) * (valueNum - oldMin) + minValue
                try:
                    outValueHandle.jumpToElement(num)
                    outputdataValue = outValueHandle.outputValue()
                    outputdataValue.setDouble(outputValue)
                    outputdataValue.setClean()
                except Exception,err:
                    print err
                #oldValue = oldMin + oldMax
                #outputValue += oldValue
            #outValueHandle.setFloat(outputValue)
            outValueHandle.setAllClean()

        else:
            om.kUnknownParameter
        

def initializePlugin(obj):
    thisNode = MySetRangeNode
    pluginFn = omm.MFnPlugin(obj, "Wang Jinge - WeChat:370871841", "0.0.1", "Any")
    try:
        pluginFn.registerNode(
            thisNode.kNodeName,
            thisNode.kTypeID,
            thisNode.node_creator,
            thisNode.node_initalize
        )
    except:
        sys.stderr.write("Failed to register node: %s" % thisNode.kNodeName)



def uninitializePlugin(obj):
    thisNode = MySetRangeNode
    pluginFn = omm.MFnPlugin(obj)
   try:
        pluginFn.deregisterNode(thisNode.kTypeID)
    except:
        sys.stderr.write("Failed to deregister node : %s" % thisNode.kNodeName)
 
