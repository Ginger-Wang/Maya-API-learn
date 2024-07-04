# -*- coding: UTF-8 -*-
#!/usr/bin/python
import os,sys
from maya.api import OpenMaya,OpenMayaAnim
import pymel.core as pm

def setSkinWeight(vertex_DP,influenceList,mWeightList):
    skinName2.setWeights(vertex_DP,influenceList,mWeightList)

meshName = pm.PyNode("pPlaneShape1")
skinName = pm.PyNode("skinCluster1")

influences = skinName.influenceObjects()
influenceList = OpenMaya.MIntArray()
mWeightList = OpenMaya.MDoubleArray()
moldWeightList = OpenMaya.MDoubleArray()
for name in influences:
    currentIndex = skinName.indexForInfluenceObject(name)
    print currentIndex
    influenceList.append(currentIndex)
weights = skinName.getWeights(meshName)

for w in weights:
    [mWeightList.append(i) for i in w]

meshName2 = pm.PyNode("%s.vtx[*]"%"pPlaneShape2")
skinName2 = pm.skinCluster(influences,meshName2,tsb = 1)

vertex_DP = meshName2.__apimdagpath__()
oldWeights = skinName2.getWeights(meshName2)

for weight in mWeightList:
    moldWeightList.append(weight)

setSkinWeight(vertex_DP,influenceList,moldWeightList)


"""

# -*- coding: UTF-8 -*-
#!/usr/bin/python
import os,sys
from maya.api import OpenMaya,OpenMayaAnim
from maya import cmds
import time


def meshSpape2Vertex(meshName):
    vertex_list = OpenMaya.MSelectionList()
    vertex_list.add('%s.vtx[*]'%meshName)
    vertex_dag_path, vertex_object = vertex_list.getComponent(0)
    return vertex_DagPath, vertexMObject


def getSkimWeights(shapeName):
    selectApi = OpenMaya.MSelectionList()
    mobject = OpenMaya.MObject()
    selectApi.add(shapeName)
    apiShapeDP = selectApi.getDagPath(0)
    apiShapeMO = selectApi.getDependNode(0)
    weights= OpenMaya.MDoubleArray()
    dependencyIterator = OpenMaya.MItDependencyGraph(apiShapeMO,OpenMaya.MFn.kSkinClusterFilter,OpenMaya.MItDependencyGraph.kUpstream)
    apiSkinCluster = OpenMayaAnim.MFnSkinCluster(dependencyIterator.currentNode())
    weightsComplete,influences= apiSkinCluster.getWeights(apiShapeDP,mobject)
    return weightsComplete,apiSkinCluster

startTime = time.time()
shapeName = 'pCylinderShape1'
weightsComplete,apiSkinCluster = getSkimWeights(shapeName)

influenceObjects = apiSkinCluster.influenceObjects()
influenceList = OpenMaya.MIntArray()
for eachInfluenceObject in influenceObjects:
    currentIndex = apiSkinCluster.indexForInfluenceObject(eachInfluenceObject)
    influenceList.append(currentIndex)


print len(weightsComplete) 
# weights
mWeightList = OpenMaya.MDoubleArray()
for wIndex in range(len(weightsComplete)):
    mWeightList.append(weightsComplete[wIndex])

shapeName1 = 'pCylinderShape3'
selectApi1 = OpenMaya.MSelectionList()

selectApi1.add(shapeName1)
apiShapeDP1 = selectApi1.getDagPath(0)
apiShapeMO1 = selectApi1.getDependNode(0)

influenceBones = [i.fullPathName() for i in influenceObjects]
cmds.skinCluster(influenceBones,shapeName1,tsb =1)
vertex_DagPath,vertexMObject = meshSpape2Vertex(shapeName1)

dependencyIterator1 = OpenMaya.MItDependencyGraph(apiShapeMO1,OpenMaya.MFn.kSkinClusterFilter,OpenMaya.MItDependencyGraph.kUpstream)
apiSkinCluster1 = OpenMayaAnim.MFnSkinCluster(dependencyIterator1.currentNode())

apiSkinCluster1.setWeights(apiShapeDP1, vertex_object,influenceList,weightsComplete)

endTime = time.time()


print(endTime - startTime)
#0.167000055313

"""


