# -*- coding: UTF-8 -*-
import pymel.core as pm

def setJointOrient(newJoint,thisJoint):
    jointOrient = newJoint.jointOrient.get()
    thisJoint.r.set(0,0,0)
    thisJoint.jointOrient.set(jointOrient)
    
def setJointToZero(thisJoint):    

    parentJoint = thisJoint.getParent()
    newJoint = pm.createNode("joint",p = jnt,ss = 1)
    if parentJoint:
        parentJoint.addChild(newJoint)
        setJointOrient(newJoint,thisJoint)
    else:
        pm.parent(newJoint,w = 1)
        setJointOrient(newJoint,thisJoint) 
    pm.delete(newJoint)

if __name__ == "__main__":
    allJoints = pm.ls(sl =1)
    for jnt in allJoints:
        setJointToZero(jnt)
    pm.select(allJoints,r =1)
