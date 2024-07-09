# -*- coding: UTF-8 -*-
#!/usr/bin/python
import os,sys
from maya.api import OpenMaya,OpenMayaAnim
from maya import cmds

import pymel.core as pm

###Convert node to OpenMaya.MObject object
def get_object(node):
    selection = OpenMaya.MSelectionList()
    selection.add(node)
    return selection.getDependNode(0)
###Convert node to OpenMaya.MDagPath object
def get_DagPath(node):
    selection = OpenMaya.MSelectionList()
    selection.add(node)
    return selection.getDagPath(0)

### Add bonesList to mDagPathArray (OpenMaya.MDagPathArray )
def set_JointsDPArray(mDagPathArray,bonesList):
    for bone in bonesList:
        boneDP = get_DagPath(bone)
        mDagPathArray.append(boneDP)

###Convert mesh to OpenMaya.MDagPath,OpenMaya.MObject object
def meshSpape2Vertex(meshName):
    vertex_list = OpenMaya.MSelectionList()
    vertex_list.add('%s.vtx[*]'%meshName)
    vertex_dag_path, vertex_object = vertex_list.getComponent(0)
    return vertex_dag_path, vertex_object

   



mobject = OpenMaya.MObject()    
skinMObject = get_object("skinCluster1")
vertex_dag_path, vertex_object = meshSpape2Vertex("pPlaneShape1")
apiSkinCluster = OpenMayaAnim.MFnSkinCluster(skinMObject)
#获取蒙皮权重
weightsComplete,influences = apiSkinCluster.getWeights(apiShapeDP,mobject)
#获取蒙皮骨骼列表 MDagPathArray
influenceObjects = apiSkinCluster.influenceObjects()
# influenceObjects joint1 joint2 joint3;

cmds.delete("skinCluster1")
bonesList =['joint4' ,'joint5', 'joint6']
#创建新的skin cluster 使用bone list的骨骼
skinNewName = cmds.skinCluster(bonesList,"pPlaneShape1",tsb=1)[0]
skinNewMObject = get_object(skinNewName)
apiSkinNewCluster = OpenMayaAnim.MFnSkinCluster(skinNewMObject)
mDagPathArray = OpenMaya.MDagPathArray()
set_JointsDPArray(mDagPathArray,bonesList)
influenceList = OpenMaya.MIntArray()
for eachInfluenceObject in mDagPathArray:
    currentIndex = apiSkinNewCluster.indexForInfluenceObject(eachInfluenceObject)
    influenceList.append(currentIndex)

apiSkinNewCluster.setWeights(vertex_dag_path,vertex_object,influenceList,weightsComplete)
    
    






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


