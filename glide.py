# -*- coding: UTF-8 -*-
import sys
from maya import OpenMaya, OpenMayaMPx, cmds
om = OpenMaya
omm = OpenMayaMPx

#vertexIncrement = 0.1
kApiVersion = om.MAYA_API_VERSION
#print kApiVersion
if kApiVersion < 201600:
    kInput = omm.cvar.MPxDeformerNode_input
    kInputGeom = omm.cvar.MPxDeformerNode_inputGeom
    kOutputGeom = omm.cvar.MPxDeformerNode_outputGeom
    kEnvelope = omm.cvar.MPxDeformerNode_envelope
else:
    kInput = omm.cvar.MPxGeometryFilter_input
    kInputGeom = omm.cvar.MPxGeometryFilter_inputGeom
    kOutputGeom = omm.cvar.MPxGeometryFilter_outputGeom
    kEnvelope = omm.cvar.MPxGeometryFilter_envelope


##########################################################
# Plug-in
##########################################################
class CreateTestDeformerNode(omm.MPxDeformerNode):
    kPluginNodeName = 'testDeformerNode'  # The name of the node.
    kPluginNodeId = om.MTypeId(0x101026)
    glide = om.MObject()
    fixedBase = om.MObject()
    aimDirection = om.MObject()
    drivenSurface = om.MObject()
    #baseSurface = om.MObject()


    def __init__(self):
        omm.MPxDeformerNode.__init__(self)
    @staticmethod
    def nodeCreator():
        return omm.asMPxPtr(CreateTestDeformerNode())

    @staticmethod
    def nodeInitializer():
        thisNode = CreateTestDeformerNode
        numericAttributeFn = om.MFnNumericAttribute()
        enumAttributeFn = om.MFnEnumAttribute()
        typedAttributeFn = om.MFnTypedAttribute()

        thisNode.glide = numericAttributeFn.create('glide', 'glide', om.MFnNumericData.kFloat, 0.0)
        numericAttributeFn.setKeyable(True)
        thisNode.addAttribute(thisNode.glide)


        thisNode.fixedBase = numericAttributeFn.create('fixedBase', 'fb', om.MFnNumericData.kBoolean, 0)
        numericAttributeFn.setKeyable(True)
        thisNode.addAttribute(thisNode.fixedBase)

        thisNode.aimDirection  = enumAttributeFn.create("aimDirection", "ad", 0)
        enumAttributeFn.addField("directionU", 0)
        enumAttributeFn.addField("directionV", 1)
        enumAttributeFn.setKeyable(True)
        enumAttributeFn.setStorable(True)
        thisNode.addAttribute(thisNode.aimDirection )

        thisNode.drivenSurface = typedAttributeFn.create("drivenSurface","df",om.MFnData.kNurbsSurface)
        typedAttributeFn.setStorable(False)
        typedAttributeFn.setKeyable(True)
        thisNode.addAttribute(thisNode.drivenSurface)

        """
        thisNode.baseSurface = typedAttributeFn.create("baseSurface", "bf", om.MFnData.kNurbsSurface)
        typedAttributeFn.setStorable(False)
        typedAttributeFn.setKeyable(True)
        thisNode.addAttribute(thisNode.baseSurface)
        """

        print dir(omm.cvar)
        thisNode.attributeAffects(thisNode.glide, kOutputGeom)
        thisNode.attributeAffects(thisNode.fixedBase, kOutputGeom)
        thisNode.attributeAffects(thisNode.aimDirection, kOutputGeom)
        thisNode.attributeAffects(thisNode.drivenSurface, kOutputGeom)
        #thisNode.attributeAffects(thisNode.baseSurface, kOutputGeom)

    def deform(self, dataBlock, mItGeometry,mMatrix,multiIndex):
        envelopeHandle = dataBlock.inputValue(self.envelope)
        glideHandle = dataBlock.inputValue(self.glide)
        fixedBaseHandle = dataBlock.inputValue(self.fixedBase)
        aimDirectionHandle = dataBlock.inputValue(self.aimDirection)
        drivenSurfaceHandle = dataBlock.inputValue(self.drivenSurface)
        #baseSurfaceHandle = dataBlock.inputValue(self.baseSurface)

        envelopeValue = envelopeHandle.asFloat()
        glideValue = glideHandle.asFloat()
        fixedBaseValue = fixedBaseHandle.asInt()
        aimDirectionValue = aimDirectionHandle.asShort()
        drivenSurfaceData = drivenSurfaceHandle.asNurbsSurface()
        #baseSurfaceData = baseSurfaceHandle.asNurbsSurface()

        paramU_util = om.MScriptUtil()
        paramV_util = om.MScriptUtil()
        paramU_util.createFromDouble(0.0)
        paramV_util.createFromDouble(0.0)
        paramU = paramU_util.asDoublePtr()
        paramV = paramV_util.asDoublePtr()

        if not drivenSurfaceData.isNull():
            surfaceFn = om.MFnNurbsSurface(drivenSurfaceData)
            #baseSurfaceFn = om.MFnNurbsSurface(baseSurfaceData)
            if fixedBaseValue == 0:
                while not mItGeometry.isDone():
                    mPoint = mItGeometry.position()
                    mPoint *= mMatrix
                    test = getClosestUVParm(mPoint,surfaceFn,paramU,paramV)
                    paramUValue = paramU_util.getDouble(paramU)
                    paramVValue = paramV_util.getDouble(paramV)
                    #pointInSurfacePointMatrix = getPointFromSurfacePoint(surfaceFn, paramUValue, paramVValue)
                    if test == False:
                        continue
                    if (aimDirectionValue == 0):
                        print paramUValue
                        newParamU = paramUValue + (glideValue * paramUValue)
                        newParamU -= int(newParamU)
                        if newParamU >= 0:
                            afterDeformedPt = getPointFromSurfacePoint(surfaceFn, newParamU, paramVValue)
                        elif newParamU < 0:
                            newParamU += 1.0
                            afterDeformedPt = getPointFromSurfacePoint(surfaceFn, newParamU, paramVValue)

                    afterDeformedPt *= mMatrix.inverse()
                    mItGeometry.setPosition(afterDeformedPt)
                    mItGeometry.next()

            else:
                print "False",fixedBaseValue
                #print fixedBaseValue,aimDirectionValue,envelopeValue,glideValue
                #afterDeformedPt *= mMatrix.inverse()
                #mItGeometry.setPosition(afterDeformedPt)
                # print ((mPoint.x,mPoint.y,mPoint.z),(afterDeformedPt.x,afterDeformedPt.y,afterDeformedPt.z))


def getClosestUVParm(mPoint,surfaceFn,paramU,paramV):
    u_util = om.MScriptUtil()
    u_util.createFromDouble(0.0)
    u_param = u_util.asDoublePtr()
    v_util = om.MScriptUtil()
    v_util.createFromDouble(0.0)
    v_param = v_util.asDoublePtr()
    mPointCls = surfaceFn.closestPoint(mPoint, False, u_param, v_param,  False, 0.001, om.MSpace.kWorld)
    fVal_u = om.MScriptUtil.getDouble(u_param)
    fVal_v = om.MScriptUtil.getDouble(v_param)
    u_util.setDouble(u_param,0.0)
    v_util.setDouble(v_param,0.0)
    surfaceFn.getParamAtPoint(mPointCls, paramU, paramV, True, om.MSpace.kWorld, 0.001)
    return True


def getPointFromSurfacePoint(surfaceFn,paramU,paramV):
    surfacePoint = om.MPoint()
    surfaceFn.getPointAtParam(paramU, paramV, surfacePoint,om.MSpace.kWorld)
    return surfacePoint


def initializePlugin(mobject):
    ''' Initialize the plug-in '''
    mplugin = omm.MFnPlugin(mobject,"Wang Jinge - WeChat:370871841", "0.0.1", "Any")
    thisNode = CreateTestDeformerNode
    try:
        mplugin.registerNode(thisNode.kPluginNodeName,
                             thisNode.kPluginNodeId,
                             thisNode.nodeCreator,
                             thisNode.nodeInitializer,
                             omm.MPxNode.kDeformerNode)
        print("%s initialized....." % (thisNode.kPluginNodeName))
    except:
        sys.stderr.write('Failed to register node: %s'%(thisNode.kPluginNodeName))
        raise


def uninitializePlugin(mobject):
    thisNode = CreateTestDeformerNode
    mplugin = omm.MFnPlugin(mobject)
    try:
        mplugin.deregisterNode(thisNode.kPluginNodeId)
        print("%s uninitialized....." % (thisNode.kPluginNodeName))
    except:
        sys.stderr.write('Failed to deregister node: %s'%(thisNode.kPluginNodeName))
        raise

