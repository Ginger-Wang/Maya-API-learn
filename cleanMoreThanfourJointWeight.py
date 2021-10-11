#!/usr/bin/python
# -*- coding: UTF-8 -*-
import pymel.core as pm
from maya import cmds
#清除大于四块骨骼影响的权重
def moreThanFour(influences,weights):
    newWeights = [i for i in weights if i > 0]
    weight =  sorted(weights,reverse = 1)[3]
    if len(newWeights)>4:
        reSetWeights = [i if i >= weight else 0.0 for i in weights]
        transformValue = [(jnt,weight) for jnt,weight in zip(influences,reSetWeights) if weight > 0]
    else:
        transformValue = [(jnt,weight) for jnt,weight in zip(influences,weights) if weight > 0]
    return transformValue

def reSetWeight(selectionPoints):    
    meshName = selectionPoints[0]._node
    pointsList = len(selectionPoints)
    skinClusterName = meshName.listHistory(type = "skinCluster")[0]
    influences = skinClusterName.getInfluence()
    #weights = skinClusterName.getWeights(meshName ,influenceIndex = None)
    mainProgressBar = "mainProgressBar"
    cmds.progressBar( mainProgressBar,edit=True,beginProgress=True,isInterruptable=True,status='ReSetSkinWeight Complete ...',maxValue= pointsList )
    
    for point in selectionPoints:
        if cmds.progressBar(mainProgressBar, query=True, isCancelled=True ) :
            break
        #point = "%s.vtx[%d]"%(meshName,num)
        weights = pm.skinPercent(skinClusterName,point,q = 1,v =1)
        transformValue = moreThanFour(influences,weights)
        pm.skinPercent(skinClusterName,point,transformValue=transformValue,zri = 1)
        cmds.progressBar(mainProgressBar, edit=True, step=1)
    cmds.progressBar(mainProgressBar, edit=True, endProgress=True)
    commands = "%s ReSetSkinWeight finish..."%(meshName)
    print commands
    return commands
        

selectionPoints = pm.ls(sl = 1,fl =1)
reSetWeight(selectionPoints)
    



