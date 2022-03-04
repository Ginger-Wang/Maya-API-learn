# -*- coding: UTF-8 -*-
from maya import OpenMaya, cmds
import pymel.core as pm

def getAxis(vector = [0,0,1],xyzList = ['X','Y','Z']):
    axis = None
    for v,a in zip(vector,xyzList):
        if v != 0:
            axis = a
            break    
    return axis

def createMatrixNode(jointName,transform = "Rotate"):
    if pm.objExists("%s_DPCM"%(jointName)):
        dcpmName = pm.PyNode("%s_DPCM"%(jointName))
    else:
        dcpmName = pm.createNode("decomposeMatrix",name = "%s_DPCM"%(jointName))
    if pm.objExists("%s_CPM"%(jointName)):
        cpmName = pm.PyNode("%s_CPM"%(jointName))
    else:
        cpmName  = pm.createNode("composeMatrix",name = "%s_CPM"%(jointName))
    dcpmAttr = pm.PyNode("%s.output%s"%(dcpmName,transform))
    cpmAttr = pm.PyNode("%s.input%s"%(cpmName,transform))
    dcpmAttr.connect(cpmAttr,f = 1)
    #connectAttr -f BaseBody_LeftArmRoll1.matrix Snake_LeftArm_AutoJnt02_RollJointDecMtx.inputMatrix;
    jointName.matrix.connect(dcpmName.inputMatrix,f = 1)
    return cpmName

def createAngleBetweem(jointName,childJnt,vector = [0,0,1],axis = "Y"):
    xyz = getAxis(vector)
    childJntAttr = pm.PyNode("%s.translate%s"%(childJnt,xyz))
    jntValue = childJntAttr.get()
    nameMatrix = "%s%s_Matrix"%(jointName,xyz)
    nameMultdcpm = "%s%s_MultDCPM"%(jointName,xyz)
    nameAngleBet = "%s%s_AngleBet"%(jointName,xyz)
    nameAngleRemap = "%s%s_AngleRemap"%(jointName,xyz)
    nameTrRemap = "%s%s_TrRemap"%(jointName,xyz)
    if pm.objExists(nameMatrix):
        multMatrix = pm.PyNode(nameMatrix)
    else:
        multMatrix = pm.createNode("multMatrix",name = nameMatrix)
    if pm.objExists(nameMultdcpm):
        multdcpmName = pm.PyNode(nameMultdcpm)
    else:
        multdcpmName = pm.createNode("decomposeMatrix",name = nameMultdcpm)
    if pm.objExists(nameAngleBet):
        angleBetName = pm.PyNode(nameAngleBet)
    else:
        angleBetName = pm.createNode("angleBetween",name = nameAngleBet)
    if pm.objExists(nameAngleRemap):
        angleRemapName = pm.PyNode(nameAngleRemap)
    else:
        angleRemapName = pm.createNode("remapValue",name = nameAngleRemap)
    if pm.objExists(nameTrRemap):
        trRemapName = pm.PyNode(nameTrRemap)
    else:
        trRemapName = pm.createNode("remapValue",name = nameTrRemap)
                
    multMatrix.matrixSum.connect(multdcpmName.inputMatrix,f = 1)
    if jntValue > 0:
        angleBetName.vector1.set([(i *-1) for i in vector])
    else:
        angleBetName.vector1.set(vector)          
    multdcpmName.outputTranslate.connect(angleBetName.vector2,f = 1)
    remapAttrName = pm.PyNode("%s.euler%s"%(angleBetName,axis))
    angleRemapName.inputMin.set(0)
    angleRemapName.inputMax.set(180)
    angleRemapName.outputMin.set(0)
    angleRemapName.outputMax.set(1)
    remapAttrName.connect(angleRemapName.inputValue,f = 1)
    angleRemapName.outValue.connect(trRemapName.inputValue,f = 1)
    trRemapName.outputMin.set(jntValue)
    trRemapName.outputMax.set(jntValue*1.2)
    trRemapName.ov >> childJntAttr
    return multMatrix,trRemapName
    
def createOrientConstrain(parentJoint,autoJoint):
    if not autoJoint.hasAttr("constWeight"): autoJoint.addAttr("constWeight",at="float",k=1,max =1,min = 0,dv = 0.5)

    parentConsTagJRotComMtx = pm.createNode("composeMatrix",name = "%sParentConsTagJRotComMtx"%(autoJoint))
    parentConsArmJRotComMtx = pm.createNode("composeMatrix",name = "%sParentConsArmJRotComMtx"%(autoJoint))
    parentConsParentSpaceMltMtx = pm.createNode("multMatrix",name = "%sParentConsParentSpaceMltMtx"%(autoJoint))
    parentConsParentSpaceDecMtx =pm.createNode("decomposeMatrix",name = "%sParentConsParentSpaceDecMtx"%(autoJoint))
    pairBlendName = pm.createNode("pairBlend",name = "%sParentConsNoJRotPairBlend"%(autoJoint))
    parentConsTagJRotInvMtx = pm.createNode("inverseMatrix",name = "%sParentConsTagJRotInvMtx"%(autoJoint))
    parentConsPairBlendResultComMtx = pm.createNode("composeMatrix",name = "%sParentConsPairBlendResultComMtx"%(autoJoint))
    parentConsResultMltMtx = pm.createNode("multMatrix",name = "%sParentConsResultMltMtx"%(autoJoint))
    parentConsResultDecMtx = pm.createNode("decomposeMatrix",name = "%sParentConsResultDecMtx"%(autoJoint))
    
    parentConsTagJRotComMtx.outputMatrix.connect(parentConsParentSpaceMltMtx.matrixIn[0])
    parentConsArmJRotComMtx.outputMatrix.connect(parentConsParentSpaceMltMtx.matrixIn[2])
    parentJoint.im.connect(parentConsParentSpaceMltMtx.matrixIn[3])
    parentJoint.jo.connect(parentConsArmJRotComMtx.ir)
    autoJoint.jo.connect(parentConsTagJRotComMtx.ir)
    parentConsParentSpaceMltMtx.o.connect(parentConsParentSpaceDecMtx.imat)
    pairBlendName.ri.set(1)
    autoJoint.constWeight.connect(pairBlendName.w)
    autoJoint.jo.connect(pairBlendName.ir1)
    parentConsParentSpaceDecMtx.outputRotate.connect(pairBlendName.ir2)
    parentConsTagJRotComMtx.omat.connect(parentConsTagJRotInvMtx.imat)
    pairBlendName.outRotate.connect(parentConsPairBlendResultComMtx.ir)
    parentConsPairBlendResultComMtx.omat.connect(parentConsResultMltMtx.matrixIn[0])
    parentConsTagJRotInvMtx.omat.connect(parentConsResultMltMtx.matrixIn[1])
    parentConsResultMltMtx.o.connect(parentConsResultDecMtx.imat)
    parentConsResultDecMtx.outputRotate.connect(autoJoint.r)
def createZeroCPM(jointName,axis = "Z"):    
    childJnt = jointName.getChildren()[0]
    jntAttr = pm.PyNode("%s.translate%s"%(childJnt,axis))
    value = jntAttr.get()
    if pm.objExists("%s%s_CPM"%(childJnt,axis)):
        zeroCPM = pm.PyNode("%s%s_CPM"%(childJnt,axis))
    else:
        zeroCPM  = pm.createNode("composeMatrix",name = "%s%s_CPM"%(childJnt,axis))
    cpmAttr = pm.PyNode("%s.inputTranslate%s"%(zeroCPM,axis))   
    if value > 0:
        cpmAttr.set(-1)
    else:
        cpmAttr.set(1)
    return zeroCPM,childJnt
    
     
'''
jointNames = pm.ls(sl=1)
parentJoint = jointNames[0]
autoJoint = jointNames[1]
createOrientConstrain(parentJoint,autoJoint)
 
cpmName = createMatrixNode(parentJoint,transform = "Rotate")
multMatrix,trRemapName = createAngleBetweem(parentJoint,autoJoint.getChildren()[0],vector = [0,1,0],axis = "Z") 
zeroCPM,childJnt = createZeroCPM(autoJoint,axis = "Y")
zeroCPM.omat >> multMatrix.i[0]
cpmName.omat >> multMatrix.i[1]

#connectAttr -f joint7_CPM.outputMatrix joint2_Matrix.matrixIn[0];
jntName = pm.ls(sl = 1)
cpmName = createMatrixNode(jntName[0],transform = "Translate")

attrName = pm.PyNode("joint2_AngleRemap.outValue")
print attrName.shortName()
'''



