from maya  import cmds,mel,OpenMaya

def get_offset_to_closest_point(mesh_name, position,space = OpenMaya.MSpace.kWorld):
    # 创建选择列表并添加多边形网格对象
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(mesh_name)
    dag_path = OpenMaya.MDagPath()
    selection_list.getDagPath(0, dag_path)
    mesh_fn = OpenMaya.MFnMesh(dag_path)

    # 创建空间中的点
    point = OpenMaya.MPoint(position[0], position[1], position[2])

    # 输出变量
    closest_point = OpenMaya.MPoint()
    util = OpenMaya.MScriptUtil()
    util.createFromInt(0)
    poly_id_ptr = util.asIntPtr()

    # 获取最近的表面点
    mesh_fn.getClosestPoint(point, closest_point, space, poly_id_ptr)
    
    # 计算偏移量
    offset_vector = OpenMaya.MVector(closest_point - point)

    # 使用迭代器找到最近的顶点ID
    it_mesh_vertex = OpenMaya.MItMeshVertex(dag_path)
    closest_vertex_id = None
    # 定义一个无限大的浮点数
    min_distance = float('inf')
    # 遍历所有点，查找距离最近的点
    while not it_mesh_vertex.isDone():
        vertex_point = it_mesh_vertex.position(OpenMaya.MSpace.kWorld)
        distance = vertex_point.distanceTo(point)
        if distance < min_distance:
            min_distance = distance
            closest_vertex_id = it_mesh_vertex.index()
        it_mesh_vertex.next()
    vertex_id_position = OpenMaya.MPoint()    
    mesh_fn.getPoint(closest_vertex_id,vertex_id_position,space)
    # 重新计算偏移量
    offset_vector_new = OpenMaya.MVector(vertex_id_position - point)
    return offset_vector_new,closest_vertex_id


def get_point(mesh_name, vertex_id,space=OpenMaya.MSpace.kWorld):
    """
    space 默认 OpenMaya.MSpace.kWorld
    space = OpenMaya.MSpace.kWorld or  OpenMaya.MSpace.kObject
    """
    # 创建选择列表并添加多边形网格对象
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(mesh_name)
    dag_path = OpenMaya.MDagPath()
    selection_list.getDagPath(0, dag_path)
    mesh_fn = OpenMaya.MFnMesh(dag_path)

    # 输出变量
    point_on_mesh = OpenMaya.MPoint()
    mesh_fn.getPoint(vertex_id,point_on_mesh,space)
    return point_on_mesh



# 定义一个函数，用于递归获取一个关节及其所有子关节
def getChildJoint(name, jointDic):
    # 使用cmds.listRelatives命令获取给定关节名的子关节列表，只包含类型为“joint”的子关节
    # 如果没有找到子关节，返回空列表
    children = cmds.listRelatives(name, type="joint", children=True) or []   
    # 在字典jointDic中记录当前关节name及其直接子关节列表children
    jointDic[name] = children  
    # 遍历当前关节的所有直接子关节
    for each in children:
        # 递归调用getChildJoint函数，获取当前子关节的子关节
        childrenJnt = getChildJoint(each, jointDic)
        # 更新字典，记录当前子关节each及其子关节childrenJnt
        jointDic[each] = childrenJnt 
    # 返回当前关节的子关节列表，这也是递归函数向上一级返回的结果
    return children



# 定义一个函数 根据骨骼名称，在对应的模型上创建新的骨骼
def transferJoints(sourceMesh,tatgetMesh,jointName,prefix = ""):
    positionWS = cmds.xform(jointName,q = 1,t = 1,ws = 1)
    # 调用获取骨骼位置距离模型上最近点的偏移量，和点ID
    offset_vector,closest_vertex_id = get_offset_to_closest_point(sourceMesh,positionWS)
    # 在 targetMesh 获取对应点的位置
    point_on_mesh = get_point(tatgetMesh,closest_vertex_id)
    # 计算偏移位置
    position = OpenMaya.MVector(point_on_mesh - offset_vector)
    mPoint = OpenMaya.MPoint(position)
    newJnt = cmds.createNode("joint",ss = 1,name = f"{prefix}_{jointName}")
    cmds.setAttr(f"{newJnt}.radius",5)
    cmds.xform(newJnt,t = [mPoint.x,mPoint.y,mPoint.z],ws = 1)

    


def runScript(**kwargs):
    """
    kwargs:{}
    sourceMesh = "head_lod0_mesh"
    tatgetMesh = "head_lod0_mesh1"
    rootJoint = "spine_04" 
    """
    
    dicNames = {}
    children = getChildJoint(kwargs["rootJoint"],dicNames)
    newJointDic = {k:v for k,v in dicNames.items() if v}
    parentJoints = [k for k,v in newJointDic.items()]
    #cmds.select(parentJoints)
    
    allJoints = cmds.listRelatives(kwargs["rootJoint"],c = 1,ad = 1,type = "joint")
    allJoints.append(kwargs["rootJoint"])
    for jnt in allJoints:
        transferJoints(kwargs["sourceMesh"],kwargs["tatgetMesh"],jnt,prefix = kwargs["prefix"])
        cmds.refresh()
        
    
    for k,v in newJointDic.items():
        cmds.parent([f"{kwargs['prefix']}_{i}" for i in v],f"{kwargs['prefix']}_{k}")


if __name__ == "__main__":
    runScript(sourceMesh = "head_lod0_mesh",tatgetMesh = "head_lod0_mesh1" ,rootJoint = "spine_04",prefix = "MetaHuamnNew")
    mel.eval("print('Transfer joints completed....');")
    



















