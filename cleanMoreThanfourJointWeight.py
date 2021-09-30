#!/usr/bin/python
# -*- coding: UTF-8 -*-
import pymel.core as pm
#清除大于四块骨骼影响的权重
def moreThanFour(influences,weights):
    newWeights = [i for i in weights if i > 0]
    weight =  sorted(weights,reverse = 1)[3]
    if len(newWeights)>4:
        reSetWeights = [i if i >= weight else 0.0 for i in weights]
        transformValue = [(jnt,weight) for jnt,weight in zip(influences,reSetWeights)]
    else:
        transformValue = [(jnt,weight) for jnt,weight in zip(influences,weights)]
    return transformValue
        



selectionPoints = pm.ls(sl = 1)[0]
meshName = selectionPoints.getShape()
pointsList = meshName._numVertices()
skinClusterName = meshName.listHistory(type = "skinCluster")[0]
influences = skinClusterName.getInfluence()
weights = skinClusterName.getWeights(meshName ,influenceIndex = None)
mainProgressBar = "mainProgressBar"
cmds.progressBar( mainProgressBar,edit=True,beginProgress=True,isInterruptable=True,status='ReSetSkinWeight Complete ...',maxValue= pointsList )

for weight,num in zip(weights,range(pointsList)):
    if cmds.progressBar(mainProgressBar, query=True, isCancelled=True ) :
        break
    point = "%s.vtx[%d]"%(meshName,num)
    transformValue = moreThanFour(influences,weight)
    pm.skinPercent(skinClusterName,point,transformValue=transformValue,zri = 1)
    cmds.progressBar(mainProgressBar, edit=True, step=1)
cmds.progressBar(mainProgressBar, edit=True, endProgress=True)
print "%s ReSetSkinWeight finish..."%(meshName) 
    



