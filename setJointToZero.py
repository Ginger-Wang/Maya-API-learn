# -*- coding: UTF-8 -*-
import pymel.core as pm

def setJointOrient(newJoint,thisJoint):
    jointOrient = newJoint.jointOrient.get()
    thisJoint.r.set(0,0,0)
    thisJoint.jointOrient.set(jointOrient)
    
def setJointToZero():    
    thisJoint = pm.ls(sl = 1)[0]
    parentJoint = thisJoint.getParent()
    newJoint = pm.joint()
    if parentJoint:
        parentJoint.addChild(newJoint)
        setJointOrient(newJoint,thisJoint)
    else:
        pm.parent(newJoint,w = 1)
        setJointOrient(newJoint,thisJoint) 
    pm.delete(newJoint)
    pm.select(thisJoint,r = 1) 

if __name__ == "__main__":
    setJointToZero()
