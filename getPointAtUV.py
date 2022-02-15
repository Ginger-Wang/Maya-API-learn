from maya  import cmds,OpenMaya
import pymel.core as pm

selectrds = pm.ls("pSphere1","locator1","pSphere2")
meshName = selectrds[0]
locName = selectrds[1]
meshName2 = selectrds[2]
loc_DagPath = locName.__apiobject__()
locPosition = locName.getTranslation(worldSpace = 1)
#locPosition.apicls()
locPoint = OpenMaya.MPoint(locPosition)
#获取最近的点
dag_path = meshName.__apimdagpath__()
mfn_mesh1 = OpenMaya.MFnMesh(dag_path)
theClosestPoint = OpenMaya.MPoint()
mfn_mesh1.getClosestPoint(locPoint,theClosestPoint,OpenMaya.MSpace.kWorld)
#根据点获取UV
util = OpenMaya.MScriptUtil()
util.createFromList([0.0, 0.0], 2)
uvPoint = util.asFloat2Ptr()
mfn_mesh1.getUVAtPoint(theClosestPoint,uvPoint,OpenMaya.MSpace.kWorld)
pos = [theClosestPoint.x,theClosestPoint.y,theClosestPoint.z]
locName.setTranslation(pos,worldSpace = 1)
u = util.getFloat2ArrayItem(uvPoint,0,0)
v = util.getFloat2ArrayItem(uvPoint,0,1)

#根据UV获取另一个物体上的点位置
mfn_mesh2 = OpenMaya.MFnMesh(meshName2.__apiobject__())
numPolygons = mfn_mesh2.numPolygons()
toThisPoint = OpenMaya.MPoint()
for num in range(numPolygons):    
    try:
        mfn_mesh2.getPointAtUV(num,toThisPoint,uvPoint,OpenMaya.MSpace.kWorld)
        break            
    except Exception,err:
        pass
   
posA = [toThisPoint.x,toThisPoint.y,toThisPoint.z]
jntName = pm.joint(p = posA)
