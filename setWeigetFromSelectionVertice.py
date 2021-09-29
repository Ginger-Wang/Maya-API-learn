#!/usr/bin/python
# -*- coding: UTF-8 -*-
import pymel.core as pm
def setWeigetFromSelectionVertice():
    selectionPoints = pm.ls(sl = 1)
    for point in selectionPoints:
        meshName = point._node
        numVertices = meshName._numVertices()
        skinClusterName = meshName.listConnections(type = "skinCluster")[0]
        getInfluences = skinClusterName.getInfluence()
        weights = pm.skinPercent(skinClusterName,point,q = 1,v =1)
        transformValue = [(jnt,weight) for jnt,weight in zip(getInfluences,weights)]
        pm.skinPercent(skinClusterName,meshName,transformValue=transformValue)

if __name__ == "__main__":
    setWeigetFromSelectionVertice()
