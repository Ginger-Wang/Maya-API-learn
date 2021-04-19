# Maya-API-learn
# -*- coding: UTF-8 -*-
import sys, math
from maya import OpenMaya, OpenMayaMPx, cmds, mel

om = OpenMaya
omm = OpenMayaMPx


class ZipperNode(omm.MPxNode):
    kNodeName = "zipperNode"
    kTypeID = om.MTypeId(0x01018)
    scale = om.MObject()
    bias = om.MObject()
    zip = om.MObject()
    incurve = om.MObject()
    rCurveRamp = om.MObject()
    gCurveRamp = om.MObject()
    outCurve = om.MObject()

    def __init__(self):
        omm.MPxNode.__init__(self)

    @staticmethod
    def zipperNode_creator():
       return omm.asMPxPtr(ZipperNode())

    @staticmethod
    def zipperNode_initalize():
        thisNode = ZipperNode
        mFnNumAttr = om.MFnNumericAttribute()
        mFnTypeAttr = om.MFnTypedAttribute()

        thisNode.rCurveRamp = om.MRampAttribute.createCurveRamp("curveZipperRamp", "curveZipperRamp")
        thisNode.addAttribute(thisNode.rCurveRamp)

        thisNode.gCurveRamp = om.MRampAttribute.createCurveRamp("curveRampSpeed", "curveRampSpeed")

        thisNode.addAttribute(thisNode.gCurveRamp)

        thisNode.scale = mFnNumAttr.create("scale", "sc", om.MFnNumericData.kInt, 0.0)
        mFnNumAttr.setDefault(2)
        mFnNumAttr.setMin(0)
        mFnNumAttr.setMax(100)
        mFnNumAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.scale)

        thisNode.bias = mFnNumAttr.create("bias", "b", om.MFnNumericData.kFloat, 0.0)
        mFnNumAttr.setDefault(0.5)
        mFnNumAttr.setMin(0.0)
        mFnNumAttr.setMax(1.0)
        mFnNumAttr.setKeyable(True)
        thisNode.addAttribute(thisNode.bias)

        thisNode.zip = mFnNumAttr.create("zip", "zip", om.MFnNumericData.kFloat, 0.0)
        mFnNumAttr.setKeyable(True)
        mFnNumAttr.setMin(0.0)
        mFnNumAttr.setMax(10.0)
        thisNode.addAttribute(thisNode.zip)

        thisNode.incurve = mFnTypeAttr.create("inCurve", "inc", om.MFnNurbsCurveData.kNurbsCurve)
        mFnTypeAttr.setStorable(True)
        thisNode.addAttribute(thisNode.incurve)

        thisNode.outCurve = mFnTypeAttr.create("outCurve", "outc", om.MFnNurbsCurveData.kNurbsCurve)
        mFnTypeAttr.setArray(True)
        mFnTypeAttr.setStorable(False)
        mFnTypeAttr.setKeyable(False)
        mFnTypeAttr.setWritable(False)
        mFnTypeAttr.setUsesArrayDataBuilder(True)
       thisNode.addAttribute(thisNode.outCurve)

        thisNode.attributeAffects(thisNode.rCurveRamp, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.gCurveRamp, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.scale, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.bias, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.zip, thisNode.outCurve)
        thisNode.attributeAffects(thisNode.incurve, thisNode.outCurve)


    def compute(self, plug, dataBlock):
        thisNode = self.thisMObject()
        if plug == self.outCurve:
            cvs = om.MPointArray()
            scaleHandle = dataBlock.inputValue(self.scale)
            biasHandle = dataBlock.inputValue(self.bias)
            zipHandle = dataBlock.inputValue(self.zip)
            incurveHandle = dataBlock.inputValue(self.incurve)

            scaleValue = scaleHandle.asInt()
            biasValue = biasHandle.asFloat()
            zipValue = zipHandle.asFloat() * 0.1

            scaleRamp = om.MRampAttribute(thisNode, self.rCurveRamp)
            speedRamp = om.MRampAttribute(thisNode, self.gCurveRamp)
            # getValAtPos(self, myFloat, myRamp)
            outputArrayCurvesHandle = dataBlock.outputArrayValue(self.outCurve)
            curvesBuilder = om.MArrayDataBuilder(self.outCurve, 2)

            incurveObject = incurveHandle.asNurbsCurve()
            if incurveObject.isNull() == False:
                curveFn = om.MFnNurbsCurve(incurveObject)
                curveFn.getCVs(cvs, om.MSpace.kWorld)
                lenNum = cvs.length()
                cvsLength = float(lenNum)
                step = 1.0 / (cvsLength - 1)
                mPoint = om.MPoint()
                cvsPoints = om.MPointArray()
                cvsPoints.setLength(lenNum)
                valAt_util = om.MScriptUtil()
                valAt_util.createFromDouble(0.0)


                for num in range(2):
                    outCuveHandle = curvesBuilder.addElement(num)
                    # outputValue = outCuveHandle.outputValue()
                    newCurveDataFn = om.MFnNurbsCurveData()
                    newCurveData = newCurveDataFn.create()
                    newCurveFn = om.MFnNurbsCurve()
                    newCurveFn.copy(incurveObject, newCurveData)
                    newCurveFn.setObject(newCurveData)
                    for count in range(lenNum):
                        valAtPtr = valAt_util.asFloatPtr()
                        fAtPtr = valAt_util.asFloatPtr()
                        scaleRamp.getValueAtPosition(count * step, fAtPtr)
                        ff = valAt_util.getFloat(fAtPtr)
                        if zipValue > ff:
                            y = (zipValue - ff) * cvsLength * zipValue
                        else:
                            #0.5*((zipValue - ff)*(cvsLength * 0.5 +0.5)*zipValue)
                            y = 0
                        speedRamp.getValueAtPosition(y, valAtPtr)
                        sideY = valAt_util.getFloat(valAtPtr)
                        if num > 0:
                            mPoint.y = (cvs[count].y - (scaleValue * (sideY * biasValue)))
                        else:
                            mPoint.y = (cvs[count].y + (scaleValue * (sideY * (1 - biasValue))))
                        mPoint.x = cvs[count].x
                        mPoint.z = cvs[count].z
                        cvsPoints.set(mPoint, count)
                    newCurveFn.setCVs(cvsPoints)
                    newCurveFn.updateCurve()
                    outCuveHandle.setMObject(newCurveData)
                outputArrayCurvesHandle.set(curvesBuilder)
                outputArrayCurvesHandle.setAllClean()
            dataBlock.setClean(plug)
        else:
            om.kUnknownParameter


def initializePlugin(obj):
    pluginFn = omm.MFnPlugin(obj, "Wang Jinge -WeChat:370871841", "0.0.1", "Any")
    try:
        pluginFn.registerNode(
            ZipperNode.kNodeName,
            ZipperNode.kTypeID,
            ZipperNode.zipperNode_creator,
            ZipperNode.zipperNode_initalize
        )
    except:
        sys.stderr.write("Failed to register node: %s" % ZipperNode.kNodeName)

    evalAETemplate()


def uninitializePlugin(obj):
    pluginFn = omm.MFnPlugin(obj)
    try:
        pluginFn.deregisterNode(ZipperNode.kTypeID)
    except:
        sys.stderr.write("Failed to deregister node : %s" % ZipperNode.kNodeName)


def evalAETemplate():
    mel.eval('''
    global proc AEzipperNodeTemplate(string $nodeName)
    {
        editorTemplate -beginScrollLayout;
        editorTemplate -beginLayout "Attributes" -collapse 0;
                AEaddRampControl ($nodeName+".curveZipperRamp"); 
                AEaddRampControl ($nodeName+".curveRampSpeed");              
            editorTemplate -endLayout;
        editorTemplate -addExtraControls;
        editorTemplate -endScrollLayout;
    };   
    ''')
