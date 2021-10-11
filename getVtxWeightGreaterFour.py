#!/usr/bin/python
# -*- coding: UTF-8 -*-
import pymel.core as pm

def getVtxWeightGreaterFour(meshName):
    #Gets vertices with weights greater than four
    skinClusterName = meshName.listHistory(type = "skinCluster")[0]
    #get All meshVertexs
    meshVertexs = meshName.listComp()[-1]
    weights = skinClusterName.getWeights(meshName)
    moreThanPoints = []
    for point,weight in zip(meshVertexs,weights):
        if len([i for i in weight if i > 0])>4:
            moreThanPoints.append(point)
            #Get vertex with weights greater than four ,add vertex to the list(moreThanPoints)
            #print point
    pm.select(moreThanPoints)
    if moreThanPoints:
        return moreThanPoints
    else:
        return None

'''
selections = pm.ls(sl = 1)
for selected in selections:
    meshName = selected.getShape()
    moreThanPoints = getVtxWeightGreaterFour(meshName)
    print moreThanPoints
'''
