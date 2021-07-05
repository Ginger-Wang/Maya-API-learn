# -*- coding: UTF-8 -*-
import pymel.core as pm
from maya import cmds
if pm.window("skinWeightWindowE", ex=True):
    pm.deleteUI("skinWeightWindowE", window=True)
pm.window("skinWeightWindowE", title="transferEveryMeshSkinWeight V-1.0")
layoutNameE = pm.formLayout()
prefixFileloadE = pm.textFieldButtonGrp("prefixFileload",l = "Prefix :",text="",bl = "<<<<<",columnWidth=([1,40],[2,240],[3,60]), bc = "getPrefixE()",ann = "get one mesh name's prefix")
transferskinButtonE = pm.button('transferskinButton',label = 'Transfer SkinWeight',w = 300,h = 30,c = 'doItE()',ann = "transfer every mesh skinweight to have a prefix mesh")
closeButtonE = pm.button('',label = 'Close',w= 300,h = 30,c = 'pm.deleteUI("skinWeightWindowE")',ann = "close this window")
aboutMeTxtE = cmds.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)

pm.formLayout(layoutNameE,e = 1,af = [(prefixFileloadE,"top",5),(prefixFileloadE,"left",5),(prefixFileloadE,"right",5),(transferskinButtonE,'left',8),(transferskinButtonE,'right',8),
(closeButtonE,'right',8),(closeButtonE,'left',8),(aboutMeTxtE,"left",5),(aboutMeTxtE,"right",5),(aboutMeTxtE,'bottom',5)],ac = [(transferskinButtonE,'top',8,prefixFileloadE),(closeButtonE,'top',8,transferskinButtonE),
(aboutMeTxtE,'top',8,closeButtonE)])

pm.window('skinWeightWindowE', edit =True, width = 240,height = 120)
pm.showWindow("skinWeightWindowE")




def getChildE(polyName):
    childShapes = pm.listRelatives(polyName,ad = 1,shapes = 1)
    childPolys = pm.listRelatives(childShapes,p = 1,type = 'transform')
    if childPolys:
        return childPolys
    else:
        return None 
def getSkinCluE(polyName):
    skinCluName = pm.listHistory(polyName,type = 'skinCluster')
    if skinCluName:
        return skinCluName[0]
    else:
        return None 

def skinItE(skinedBones,polyName,skinClu): 
    skinCluDS = getSkinCluE(polyName) 
    if skinCluDS:
        pm.copySkinWeights(ss=skinClu,ds=skinCluDS,nm=True,sa='closestPoint', ia='closestJoint') 
    else:
        skinCluDS = pm.skinCluster(skinedBones,polyName, tsb =True,sm = 0)
        pm.copySkinWeights(ss=skinClu,ds=skinCluDS,nm=True,sa='closestPoint', ia='closestJoint')

def getAllJntE(polyName): 
    skinClu = pm.listHistory(polyName,type = 'skinCluster')[0]
    skinedBones = skinClu.getInfluence()    

def wrapSkinE(sourceMesh,targetMesh): 
    skinClu = pm.listHistory(sourceMesh,type = 'skinCluster')[0]
    skinedBones = skinClu.getInfluence()
    skinItE(skinedBones,targetMesh,skinClu)



def doItE():
    errorObj = []
    for selection in pm.ls(sl =1):
        allPolys = getChildE(selection)
        for targetMesh in allPolys:
            sourceMesh = targetMesh.split(":")[-1]
            try:
                wrapSkinE(sourceMesh,targetMesh)
                pm.refresh()
            except Exception,err:
                errorObj.append(targetMesh)
                pm.warning("%s"%(err))
                pm.refresh()
            print targetMesh
    pm.select(errorObj,r = 1) 

def getPrefixE():
    selections = cmds.ls(sl = 1)[0]
    splitNames = selections.split(":")[:-1]
    prefix = ":".join(splitNames)
    pm.textFieldButtonGrp("prefixFileload",e = 1,text =prefix)

      
        
        
