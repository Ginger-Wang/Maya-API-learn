from maya  import cmds,OpenMaya
import pymel.core as pm
def api_mobject(node):
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    mObject = OpenMaya.MObject()
    selectionList.getDependNode(0, mObject)
    return mObject
    
def api_mdagpath(node):
    mObject = api_mobject(node)
    if mObject.hasFn(OpenMaya.MFn.kDagNode):
        mdagpath = OpenMaya.MDagPath.getAPathTo(mObject)
        return mdagpath
    else:
        return None
        


def getUVatPosition(verticePoint,mfn_mesh):
    #locPoint = OpenMaya.MPoint(position[0],position[1],position[2],)
    #获取最近的点
    theClosestPoint = OpenMaya.MPoint()
    mfn_mesh.getClosestPoint(verticePoint,theClosestPoint,OpenMaya.MSpace.kWorld)
    
    #根据点获取UV
    util = OpenMaya.MScriptUtil()
    util.createFromList([0.0, 0.0], 2)
    uvPoint = util.asFloat2Ptr()
    mfn_mesh.getUVAtPoint(theClosestPoint,uvPoint,OpenMaya.MSpace.kWorld)
    pos = [theClosestPoint.x,theClosestPoint.y,theClosestPoint.z]
    
    u = util.getFloat2ArrayItem(uvPoint,0,0)
    v = util.getFloat2ArrayItem(uvPoint,0,1)
    return u,v

def createFollicle(mesh,folliceName):
    
    follicleTr = cmds.createNode("transform",name = folliceName ,ss = 1)
    follicleShape = cmds.createNode("follicle",name = f"{follicleTr}Shape",ss = 1,p = follicleTr)
    #属性连接
    cmds.connectAttr(f"{follicleShape}.ot",f"{follicleTr}.t",f = 1)
    cmds.connectAttr(f"{follicleShape}.or",f"{follicleTr}.r",f = 1)
    cmds.connectAttr(f"{mesh}.worldMatrix[0]",f"{follicleShape}.inputWorldMatrix",f = 1)
    cmds.connectAttr(f"{mesh}.outMesh",f"{follicleShape}.inputMesh",f = 1)
    #设置毛囊位置
    '''
    cmds.setAttr(f"{follicleShape}.parameterU",uvValue[0])
    cmds.setAttr(f"{follicleShape}.parameterV",uvValue[1])
    '''
    return follicleShape
    

meshName = "pPlane1"
meshShape = cmds.listRelatives(meshName,s = 1)[0]

dag_path = api_mdagpath(meshName)
mfn_mesh = OpenMaya.MFnMesh(dag_path)
numVertices = mfn_mesh.numVertices()
verticePoint = OpenMaya.MPoint()
hairSystem1Follicles = "hairSystem1Follicles"
if not cmds.objExists(hairSystem1Follicles):
    cmds.createNode("transform",name = hairSystem1Follicles,ss = 1)
    
for num in range(numVertices):
    index = num+1
    folliceName = f"{meshName}_Follice{index:03d}"    
    mfn_mesh.getPoint(num,verticePoint,OpenMaya.MSpace.kWorld)
    position = [verticePoint.x,verticePoint.y,verticePoint.z,]    
    u,v = getUVatPosition(verticePoint,mfn_mesh)
    follicleShape = createFollicle(meshShape,folliceName)
    #设置毛囊位置
    cmds.setAttr(f"{follicleShape}.parameterU",u)
    cmds.setAttr(f"{follicleShape}.parameterV",v)
    cmds.parent(folliceName,hairSystem1Follicles)




















