# -*- coding: UTF-8 -*-
import pymel.core as pm


def createParentConstraint(ctrlName,constraintObjName):
    parentName = constraintObjName.getParent()
    if not ctrlName.hasAttr("OffsetMatrix"): ctrlName.addAttr("OffsetMatrix",at="matrix",k=1)
    outMatrixName = pm.createNode("multMatrix",name = "%s_OutMatrix"%ctrlName)    
    offsetTrName = pm.createNode("transform",name = "%s_OffsetTr"%ctrlName,p = ctrlName)
    dcpmName = pm.createNode("decomposeMatrix",name = "%s_DCPM"%ctrlName)    
    offsetTrName.xm >> ctrlName.OffsetMatrix    
    ctrlName.OffsetMatrix >> outMatrixName.i[0]
    ctrlName.wm[0] >> outMatrixName.i[1]
    matrix = constraintObjName.getMatrix(worldSpace = 1)
    offsetTrName.setMatrix(matrix,worldSpace = 1)    
    if parentName: parentName.wim[0] >> outMatrixName.i[2]    
    outMatrixName.o >> dcpmName.imat
    dcpmName.ot >> constraintObjName.t
    dcpmName.outputRotate >> constraintObjName.r
    dcpmName.os >> constraintObjName.s

ctrlName = pm.ls(sl=1)[0]
constraintObjName = pm.ls(sl=1)[1]
createParentConstraint(ctrlName,constraintObjName)
