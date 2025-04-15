import sys,os
import math
import xml.etree.ElementTree as ET
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,mel,OpenMaya
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from importlib import reload
import skinWeights.skinWeightTools as skT
from exportFbxTools import exportFBX
from funtions import getFilePath
from dna import ( # type: ignore
    BinaryStreamReader,
    BinaryStreamWriter,
    DataLayer_All,
    FileStream,
    Status,
)
from dna_viewer import DNA, RigConfig, build_rig, build_meshes # type: ignore
from dnacalib import ( # type: ignore
    CommandSequence,RemoveJointCommand,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)
def get_maya_main_window():
    """获取Maya的主窗口"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

file_Path = os.path.dirname(__file__)
uiName = "riggingByMetaHuman.ui"
uiPath = os.path.join(file_Path, uiName)
skin_joints = ['spine_04','spine_05','clavicle_pec_l','clavicle_pec_r','spine_04_latissimus_l','spine_04_latissimus_r','clavicle_l','clavicle_out_l','clavicle_scap_l','upperarm_l','upperarm_correctiveRoot_l','upperarm_out_l','upperarm_in_l','upperarm_fwd_l','upperarm_bck_l','clavicle_r','clavicle_out_r','clavicle_scap_r',
'upperarm_r','upperarm_correctiveRoot_r','upperarm_out_r','upperarm_fwd_r','upperarm_in_r','upperarm_bck_r','neck_01','neck_02','head','FACIAL_C_FacialRoot','FACIAL_L_Temple','FACIAL_R_Temple','FACIAL_L_Sideburn1','FACIAL_R_Sideburn1','FACIAL_L_Sideburn4','FACIAL_R_Sideburn4','FACIAL_C_ForeheadSkin','FACIAL_L_ForeheadInSkin',
'FACIAL_R_ForeheadInSkin','FACIAL_L_ForeheadMidSkin','FACIAL_R_ForeheadMidSkin','FACIAL_L_ForeheadOutSkin','FACIAL_R_ForeheadOutSkin','FACIAL_C_Skull','FACIAL_C_Forehead','FACIAL_C_Forehead1','FACIAL_L_Forehead1','FACIAL_R_Forehead1','FACIAL_C_Forehead2','FACIAL_L_Forehead2','FACIAL_R_Forehead2','FACIAL_C_Forehead3','FACIAL_L_Forehead3',
'FACIAL_R_Forehead3','FACIAL_L_ForeheadIn','FACIAL_L_ForeheadInA1','FACIAL_L_ForeheadInA2','FACIAL_L_ForeheadInA3','FACIAL_L_ForeheadInB1','FACIAL_L_ForeheadInB2','FACIAL_R_ForeheadIn','FACIAL_R_ForeheadInA1','FACIAL_R_ForeheadInA2','FACIAL_R_ForeheadInA3','FACIAL_R_ForeheadInB1','FACIAL_R_ForeheadInB2','FACIAL_L_ForeheadMid',
'FACIAL_L_ForeheadMid1','FACIAL_L_ForeheadMid2','FACIAL_R_ForeheadMid','FACIAL_R_ForeheadMid1','FACIAL_R_ForeheadMid2','FACIAL_L_ForeheadOut','FACIAL_L_ForeheadOutA1','FACIAL_L_ForeheadOutA2','FACIAL_L_ForeheadOutB1','FACIAL_L_ForeheadOutB2','FACIAL_R_ForeheadOut','FACIAL_R_ForeheadOutA1','FACIAL_R_ForeheadOutA2','FACIAL_R_ForeheadOutB1',
'FACIAL_R_ForeheadOutB2','FACIAL_L_EyesackUpper','FACIAL_L_EyesackUpper1','FACIAL_L_EyesackUpper2','FACIAL_L_EyesackUpper3','FACIAL_R_EyesackUpper','FACIAL_R_EyesackUpper1','FACIAL_R_EyesackUpper2','FACIAL_R_EyesackUpper3','FACIAL_L_EyesackUpper4','FACIAL_R_EyesackUpper4','FACIAL_L_EyelidUpperFurrow','FACIAL_L_EyelidUpperFurrow1','FACIAL_L_EyelidUpperFurrow2',
'FACIAL_L_EyelidUpperFurrow3','FACIAL_R_EyelidUpperFurrow','FACIAL_R_EyelidUpperFurrow1','FACIAL_R_EyelidUpperFurrow2','FACIAL_R_EyelidUpperFurrow3','FACIAL_L_EyelidUpperB','FACIAL_L_EyelidUpperB1','FACIAL_L_EyelidUpperB2','FACIAL_L_EyelidUpperB3','FACIAL_R_EyelidUpperB','FACIAL_R_EyelidUpperB1','FACIAL_R_EyelidUpperB2','FACIAL_R_EyelidUpperB3',
'FACIAL_L_EyelidUpperA','FACIAL_L_EyelidUpperA1','FACIAL_L_EyelashesUpperA1','FACIAL_L_EyelidUpperA2','FACIAL_L_EyelashesUpperA2','FACIAL_L_EyelidUpperA3','FACIAL_L_EyelashesUpperA3','FACIAL_R_EyelidUpperA','FACIAL_R_EyelidUpperA1','FACIAL_R_EyelashesUpperA1','FACIAL_R_EyelidUpperA2','FACIAL_R_EyelashesUpperA2','FACIAL_R_EyelidUpperA3','FACIAL_R_EyelashesUpperA3',
'FACIAL_L_Eye','FACIAL_L_EyeParallel','FACIAL_R_Eye','FACIAL_R_EyeParallel','FACIAL_L_EyelidLowerA','FACIAL_L_EyelidLowerA1','FACIAL_L_EyelidLowerA2','FACIAL_L_EyelidLowerA3','FACIAL_R_EyelidLowerA','FACIAL_R_EyelidLowerA1','FACIAL_R_EyelidLowerA2','FACIAL_R_EyelidLowerA3','FACIAL_L_EyelidLowerB','FACIAL_L_EyelidLowerB1','FACIAL_L_EyelidLowerB2',
'FACIAL_L_EyelidLowerB3','FACIAL_R_EyelidLowerB','FACIAL_R_EyelidLowerB1','FACIAL_R_EyelidLowerB2','FACIAL_R_EyelidLowerB3','FACIAL_L_EyeCornerInner','FACIAL_L_EyeCornerInner1','FACIAL_L_EyeCornerInner2','FACIAL_R_EyeCornerInner','FACIAL_R_EyeCornerInner1','FACIAL_R_EyeCornerInner2','FACIAL_L_EyeCornerOuter','FACIAL_L_EyeCornerOuter1','FACIAL_L_EyelashesCornerOuter1',
'FACIAL_L_EyeCornerOuter2','FACIAL_R_EyeCornerOuter','FACIAL_R_EyeCornerOuter1','FACIAL_R_EyelashesCornerOuter1','FACIAL_R_EyeCornerOuter2','FACIAL_L_EyesackLower','FACIAL_L_EyesackLower1','FACIAL_L_EyesackLower2','FACIAL_R_EyesackLower','FACIAL_R_EyesackLower1','FACIAL_R_EyesackLower2','FACIAL_L_CheekInner','FACIAL_L_CheekInner1','FACIAL_L_CheekInner2',
'FACIAL_L_CheekInner3','FACIAL_L_CheekInner4','FACIAL_R_CheekInner','FACIAL_R_CheekInner1','FACIAL_R_CheekInner2','FACIAL_R_CheekInner3','FACIAL_R_CheekInner4','FACIAL_L_CheekOuter','FACIAL_L_CheekOuter1','FACIAL_L_CheekOuter2','FACIAL_L_CheekOuter3','FACIAL_R_CheekOuter','FACIAL_R_CheekOuter1','FACIAL_R_CheekOuter2','FACIAL_R_CheekOuter3','FACIAL_L_CheekOuter4',
'FACIAL_R_CheekOuter4','FACIAL_C_NoseBridge','FACIAL_L_NoseBridge','FACIAL_R_NoseBridge','FACIAL_C_NoseUpper','FACIAL_L_NoseUpper','FACIAL_R_NoseUpper','FACIAL_L_NasolabialBulge1','FACIAL_R_NasolabialBulge1','FACIAL_L_NasolabialBulge','FACIAL_L_NasolabialBulge2','FACIAL_L_NasolabialBulge3','FACIAL_R_NasolabialBulge','FACIAL_R_NasolabialBulge2','FACIAL_R_NasolabialBulge3',
'FACIAL_L_NasolabialFurrow','FACIAL_R_NasolabialFurrow','FACIAL_L_CheekLower','FACIAL_L_CheekLower1','FACIAL_L_CheekLower2','FACIAL_R_CheekLower','FACIAL_R_CheekLower1','FACIAL_R_CheekLower2','FACIAL_L_Ear','FACIAL_R_Ear','FACIAL_C_Nose','FACIAL_C_NoseLower','FACIAL_L_NostrilThickness3','FACIAL_R_NostrilThickness3','FACIAL_C_NoseTip','FACIAL_L_Nostril','FACIAL_L_NostrilThickness1',
'FACIAL_L_NostrilThickness2','FACIAL_R_Nostril','FACIAL_R_NostrilThickness1','FACIAL_R_NostrilThickness2','FACIAL_C_LipUpperSkin','FACIAL_L_LipUpperSkin','FACIAL_R_LipUpperSkin','FACIAL_L_LipUpperOuterSkin','FACIAL_R_LipUpperOuterSkin','FACIAL_C_MouthUpper','FACIAL_C_LipUpper','FACIAL_C_LipUpper1','FACIAL_C_LipUpper2','FACIAL_C_LipUpper3','FACIAL_L_LipUpper',
'FACIAL_L_LipUpper1','FACIAL_L_LipUpper2','FACIAL_L_LipUpper3','FACIAL_R_LipUpper','FACIAL_R_LipUpper1','FACIAL_R_LipUpper2','FACIAL_R_LipUpper3','FACIAL_L_LipUpperOuter','FACIAL_L_LipUpperOuter1',
'FACIAL_L_LipUpperOuter2','FACIAL_L_LipUpperOuter3','FACIAL_R_LipUpperOuter','FACIAL_R_LipUpperOuter1','FACIAL_R_LipUpperOuter2','FACIAL_R_LipUpperOuter3','FACIAL_L_LipCorner','FACIAL_L_LipCorner1','FACIAL_L_LipCorner2','FACIAL_L_LipCorner3','FACIAL_R_LipCorner','FACIAL_R_LipCorner1','FACIAL_R_LipCorner2','FACIAL_R_LipCorner3','FACIAL_L_JawBulge','FACIAL_R_JawBulge','FACIAL_L_JawRecess',
'FACIAL_R_JawRecess','FACIAL_L_Masseter','FACIAL_R_Masseter','FACIAL_C_UnderChin','FACIAL_L_UnderChin','FACIAL_R_UnderChin','FACIAL_C_TeethUpper','FACIAL_C_LowerLipRotation','FACIAL_C_LipLowerSkin','FACIAL_L_LipLowerSkin','FACIAL_R_LipLowerSkin','FACIAL_L_LipLowerOuterSkin','FACIAL_R_LipLowerOuterSkin','FACIAL_C_MouthLower','FACIAL_C_LipLower','FACIAL_C_LipLower1',
'FACIAL_C_LipLower2','FACIAL_C_LipLower3','FACIAL_L_LipLower','FACIAL_L_LipLower1','FACIAL_L_LipLower2','FACIAL_L_LipLower3','FACIAL_R_LipLower','FACIAL_R_LipLower1','FACIAL_R_LipLower2','FACIAL_R_LipLower3',
'FACIAL_L_LipLowerOuter','FACIAL_L_LipLowerOuter1','FACIAL_L_LipLowerOuter2','FACIAL_L_LipLowerOuter3','FACIAL_R_LipLowerOuter','FACIAL_R_LipLowerOuter1','FACIAL_R_LipLowerOuter2','FACIAL_R_LipLowerOuter3','FACIAL_C_TeethLower','FACIAL_C_Tongue1','FACIAL_C_Tongue2','FACIAL_C_Tongue3','FACIAL_C_Tongue4','FACIAL_C_Jaw','FACIAL_C_Jawline','FACIAL_L_Jawline','FACIAL_L_Jawline1','FACIAL_L_Jawline2',
'FACIAL_R_Jawline','FACIAL_R_Jawline1','FACIAL_R_Jawline2','FACIAL_L_ChinSide','FACIAL_R_ChinSide','FACIAL_C_Chin1','FACIAL_L_Chin1','FACIAL_R_Chin1','FACIAL_C_Chin2','FACIAL_L_Chin2','FACIAL_R_Chin2','FACIAL_C_Chin3','FACIAL_L_Chin3','FACIAL_R_Chin3','FACIAL_C_Neck2Root','FACIAL_C_AdamsApple','FACIAL_L_NeckA1','FACIAL_R_NeckA1','FACIAL_L_NeckA2','FACIAL_R_NeckA2',
'FACIAL_L_NeckA3','FACIAL_R_NeckA3','FACIAL_C_NeckBackA','FACIAL_L_NeckBackA','FACIAL_R_NeckBackA','FACIAL_C_Neck1Root','FACIAL_C_NeckB','FACIAL_L_NeckB1','FACIAL_R_NeckB1','FACIAL_L_NeckB2','FACIAL_R_NeckB2','FACIAL_C_NeckBackB','FACIAL_L_NeckBackB','FACIAL_R_NeckBackB',]

def vector_to_euler(normal):
    """
    将法线向量转换为欧拉角。
    假定起始向量为z轴，通过计算旋转四元数并将其转换为欧拉角，最终返回角度值。
    """
    start_vector = OpenMaya.MVector(0, 0, 1)
    end_vector = OpenMaya.MVector(normal.x, normal.y, normal.z)
    #计算 start_vector 和 end_vector 的叉积，得到一个垂直于这两个向量的向量 axis。
    #这个 axis 向量表示旋转轴，用于后续计算旋转四元数。
    axis = start_vector ^ end_vector
    axis.normalize()
    angle = math.acos(start_vector * end_vector)
    quaternion = OpenMaya.MQuaternion(angle, axis)
    euler = quaternion.asEulerRotation()
    euler_angles = [math.degrees(angle) for angle in (euler.x, euler.y, euler.z)]
    return euler_angles

def get_vertex_normal(mesh_name, vertex_id):
    """
    获取指定网格中某个顶点的法线。
    首先验证网格和顶点ID的有效性，然后通过Maya API获取顶点法线。
    """
    validate_mesh(mesh_name, vertex_id)
    selection_list, dag_path, mesh_fn = get_mesh_fn(mesh_name)
    normal = OpenMaya.MVector()
    mesh_fn.getVertexNormal(vertex_id, True, normal, OpenMaya.MSpace.kWorld)
    return normal

def get_closest_vertex_id(mesh_name, position, space=OpenMaya.MSpace.kWorld):
    """
    获取距离指定位置最近的顶点ID。
    通过Maya API找到最近的表面点，并使用迭代器找到最近的顶点ID。
    """
    selection_list, dag_path, mesh_fn = get_mesh_fn(mesh_name)
    point = OpenMaya.MPoint(position[0], position[1], position[2])
    closest_point = OpenMaya.MPoint()
    util = OpenMaya.MScriptUtil()
    util.createFromInt(0)
    poly_id_ptr = util.asIntPtr()
    mesh_fn.getClosestPoint(point, closest_point, space, poly_id_ptr)
    closest_vertex_id = find_closest_vertex_id(dag_path, point)
    vertex_id_position = OpenMaya.MPoint()    
    mesh_fn.getPoint(closest_vertex_id, vertex_id_position, space)
    return closest_vertex_id, vertex_id_position

def find_closest_vertex_id(dag_path, point):
    """
    辅助函数，用于在网格中找到距离指定点最近的顶点ID。
    """
    it_mesh_vertex = OpenMaya.MItMeshVertex(dag_path)
    closest_vertex_id = None
    min_distance = float('inf')
    while not it_mesh_vertex.isDone():
        vertex_point = it_mesh_vertex.position(OpenMaya.MSpace.kWorld)
        distance = vertex_point.distanceTo(point)
        if distance < min_distance:
            min_distance = distance
            closest_vertex_id = it_mesh_vertex.index()
        it_mesh_vertex.next()
    return closest_vertex_id

def get_mesh_fn(mesh_name):
    """
    辅助函数，创建选择列表并添加多边形网格对象，返回选择列表、DAG路径和网格函数对象。
    """
    selection_list = OpenMaya.MSelectionList()
    selection_list.add(mesh_name)
    dag_path = OpenMaya.MDagPath()
    selection_list.getDagPath(0, dag_path)
    mesh_fn = OpenMaya.MFnMesh(dag_path)
    return selection_list, dag_path, mesh_fn

def validate_mesh(mesh_name, vertex_id):
    """
    验证网格名称和顶点ID的有效性。
    如果网格不存在或顶点ID超出范围，则抛出错误。
    """
    if not cmds.objExists(mesh_name):
        raise ValueError("Mesh does not exist: {}".format(mesh_name))
    vertex_count = cmds.polyEvaluate(mesh_name, vertex=True)
    if vertex_id >= vertex_count:
        raise ValueError("Vertex ID out of range. Mesh '{}' has {} vertices.".format(mesh_name, vertex_count))

def get_child_joint(name, joint_dic):
    """
    递归获取一个关节及其所有子关节，并将其存储在字典中。
    返回当前关节的所有直接子关节。
    """
    children = cmds.listRelatives(name, type="joint", children=True) or []
    joint_dic[name] = children  
    for each in children:
        children_jnt = get_child_joint(each, joint_dic)
        joint_dic[each] = children_jnt 
    return children

def do_wrap(driven, driver):
    """
    执行Maya的doWrap命令，将驱动对象包裹到被驱动对象上。
    """
    cmds.select(driven, driver)
    mel.eval('doWrapArgList "7" { "1","0","1", "2", "0", "1", "0", "0" };')

def create_curve_from_joints(joint_dic):
    """
    根据关节字典中的关节位置创建一条曲线。
    返回曲线名称。
    """
    positions = [cmds.xform(i, q=1, t=1, ws=1) for i in joint_dic.keys()]
    curve_name = cmds.curve(p=positions, d=1)
    cmds.setAttr(f"{curve_name}.v",0)
    return curve_name

def process_meshes(prefix, lod0_meshes):
    """
    处理LOD0网格，为每个网格创建混合形状节点，并将LOD1到LOD7的网格包裹到LOD0网格上。
    """
    for mesh in lod0_meshes:
        target_mesh = f"{prefix}:{mesh}"
        if target_mesh:
            blend_shape_node = cmds.blendShape(target_mesh, mesh, name=f'{mesh}_BlendShape')[0]
        for num in range(1, 8):
            lod_name = mesh.replace("lod0", f"lod{num}")
            if cmds.objExists(lod_name):
                do_wrap(lod_name, mesh)
        cmds.setAttr(f"{blend_shape_node}.{mesh}", 1)
        cmds.refresh()

def create_and_position_joints(joint_dic, curve_name, body_joins):
    """
    创建并定位关节。
    根据曲线位置创建新关节，并根据顶点法线或原始关节旋转值设置关节旋转。
    返回旋转值字典。
    """
    rotation_value_dict = {}
    for joint_index, name in enumerate(joint_dic.keys()):
        position = cmds.pointPosition(f"{curve_name}.cv[{joint_index}]")
        joint_name = cmds.createNode("joint", ss=1, name=f"new_{name}")
        cmds.xform(joint_name, t=position, ws=1)  
        children_jnt = joint_dic[name]
        closest_vertex_id, closest_point = get_closest_vertex_id("head_lod0_mesh", position, space=OpenMaya.MSpace.kWorld)
        if not children_jnt and name not in body_joins:
            normal = get_vertex_normal("head_lod0_mesh", closest_vertex_id)      
            rotation_value = vector_to_euler(normal)
        else:
            rotation_value = cmds.xform(name, q=1, ws=1, ro=1)
        rotation_value_dict[name] = [closest_vertex_id, rotation_value]
        cmds.xform(joint_name, ro=rotation_value, ws=1)
        # cmds.setAttr(f"{joint_name}.radius", 3)
    return rotation_value_dict

def rename_and_parent_joints(joint_dic):
    """
    将新关节重命名并重新父子关系。
    应用变换。
    """
    new_joint_dic = {k: v for k, v in joint_dic.items() if v}    
    for k, v in new_joint_dic.items():
        cmds.parent([f"new_{i}" for i in v], f"new_{k}")
    for key,value in joint_dic.items():
        new_name = f"new_{key}"
        if cmds.objExists(new_name):
            cmds.rename(new_name,key)
        else:
            print(new_name)

    cmds.makeIdentity("spine_04", apply=1, t=1, r=1, s=1, n=0, pn=1)

def get_parent(mesh):
    return cmds.listRelatives(mesh,ap = 1)

def to_delete_wrap_meshs():
    base_meshs = cmds.ls("*Base*", type="mesh")
    wrap_base_meshs = set([get_parent(mesh)[0] for mesh in base_meshs])
    return wrap_base_meshs
    

class RiggingByMetaHuman(QtWidgets.QMainWindow):
    def __init__(self,*args, **kwargs):
        super(RiggingByMetaHuman,self).__init__(*args, **kwargs)
        self.load_ui()
        
    def load_ui(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath, parentWidget=get_maya_main_window())
        self.ui.setWindowFlags(QtCore.Qt.Window)
        self.addJoints()
        self.ui.pushButton_delete_nameSpace.clicked.connect(self.delete_nameSpace)
        self.ui.pushButton_delete_selected_skinCluster.clicked.connect(self.delete_selected_skinCluster)
        self.ui.pushButton_delete_constraints.clicked.connect(self.delete_constraints)
        self.ui.pushButton_createFacialBones.clicked.connect(self.createFacialBones)
        self.ui.pushButton_snapAlignBody.clicked.connect(self.adjust_Bones)
        self.ui.pushButton_LoadMetaHumanPath.clicked.connect(self.getCalibrationPath)
        self.ui.pushButton_LoadDNAPath.clicked.connect(self.getDNAFile)
        self.ui.pushButton_saveDNA.clicked.connect(self.save_dna)
        self.ui.pushButton_remove_joints.clicked.connect(self.remove_joints_calibrate_dna)
        self.ui.pushButton_loadNameSpace.clicked.connect(self.setPrefixToLineEdit)
        self.ui.pushButton_placBones.clicked.connect(self.placing_bones)
        self.ui.pushButton_skinWeightsTool.clicked.connect(self.skinWeight_tools)
        self.ui.pushButton_exportFbxTool.clicked.connect(self.exportFbxTools)
        self.resetMinmumValue_adjust()
        self.ui.toolBox_RiggingTools.currentChanged.connect(self.resetMinmumValue_adjust)
        self.ui.pushButton_add_nameSpace.clicked.connect(self.add_namespace_to_selected)

    def exportFbxTools(self):
        reload(exportFBX)  
        self.exportFBXToolWindow = exportFBX.ExportFBXTools()
        self.exportFBXToolWindow.ui.show()

    def skinWeight_tools(self):
        reload(skT)  
        self.skinWeightsWindow = skT.SkinWeightTools()        
        self.skinWeightsWindow.ui.show()

    def setPrefixToLineEdit(self):        
        prefix = skT.SkinWeightTools.getPrefix()
        self.ui.lineEdit_nameSpace.setText(prefix)
        # return prefix

    def placing_bones(self):
        prefix = self.ui.lineEdit_nameSpace.text()
        lod0_meshes = [
            "head_lod0_mesh", "teeth_lod0_mesh", "saliva_lod0_mesh", "eyeLeft_lod0_mesh", "eyeRight_lod0_mesh",
            "eyeshell_lod0_mesh", "eyelashes_lod0_mesh", "eyeEdge_lod0_mesh", "cartilage_lod0_mesh"
        ]
        body_joins = [
            "clavicle_pec_l", "clavicle_pec_r", "spine_04_latissimus_l", "spine_04_latissimus_r", "clavicle_out_l",
            "clavicle_scap_l", "upperarm_out_l", "upperarm_fwd_l", "upperarm_in_l", "upperarm_bck_l", "clavicle_out_r",
            "clavicle_scap_r", "upperarm_out_r", "upperarm_fwd_r", "upperarm_in_r", "upperarm_bck_r"
        ]

        joint_dic = {}
        get_child_joint("spine_04", joint_dic)
        curve_name = create_curve_from_joints(joint_dic)
        do_wrap(curve_name, "head_lod0_mesh")
        process_meshes(prefix, lod0_meshes)
        rotation_value_dict = create_and_position_joints(joint_dic, curve_name, body_joins)
        cmds.delete("rig",ch = 1)
        wrap_base_meshs = to_delete_wrap_meshs()
        cmds.delete("spine_04", curve_name,wrap_base_meshs)
        rename_and_parent_joints(joint_dic)


    def load_dna_reader(self,path):
        stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
        reader = BinaryStreamReader(stream, DataLayer_All)
        reader.read()
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error loading DNA: {status.message}")
        return reader
    
    def save_dna_funtion(self,reader,textcontent):
        """保存DNA到打开的Maya文件夹中"""
        thisFile = cmds.file(q = True, location =1)
        OUTPUT_DIR_PATH = os.path.split(thisFile)[0]
        # textcontent = self.ui.lineEdit_characterName.text()
        MODIFIED_CHARACTER_DNA = f"{OUTPUT_DIR_PATH}/{textcontent}"
        output_DNA = f"{MODIFIED_CHARACTER_DNA}.dna"
        stream = FileStream(output_DNA,FileStream.AccessMode_Write,FileStream.OpenMode_Binary,)
        writer = BinaryStreamWriter(stream)
        writer.setFrom(reader)
        writer.setName(textcontent)
        writer.write()
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error saving DNA: {status.message}")
        return output_DNA
    def run_joints_command(self,reader, calibrated):
        # Making arrays for joints' transformations and their corresponding mapping arrays
        joint_translations = []
        joint_rotations = []
        for i in range(reader.getJointCount()):
            joint_name = reader.getJointName(i)
            # print(joint_name)
            translation = cmds.xform(joint_name, query=True, translation=True)
            joint_translations.append(translation)
            rotation = cmds.joint(joint_name, query=True, orientation=True)
            joint_rotations.append(rotation)
        # This is step 5 sub-step a
        set_new_joints_translations = SetNeutralJointTranslationsCommand(joint_translations)
        # This is step 5 sub-step b
        set_new_joints_rotations = SetNeutralJointRotationsCommand(joint_rotations)
        # Abstraction to collect all commands into a sequence, and run them with only one invocation
        commands = CommandSequence()
        # Add vertex position deltas (NOT ABSOLUTE VALUES) onto existing vertex positions
        commands.add(set_new_joints_translations)
        commands.add(set_new_joints_rotations)
        commands.run(calibrated)
        # Verify that everything went fine
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error run_joints_command: {status.message}")
    def get_mesh_vertex_positions_from_scene(self,meshName):
        try:
            sel = OpenMaya.MSelectionList()
            sel.add(meshName)
            dag_path = OpenMaya.MDagPath()
            sel.getDagPath(0, dag_path)
            mf_mesh = OpenMaya.MFnMesh(dag_path)
            positions = OpenMaya.MPointArray()
            mf_mesh.getPoints(positions, OpenMaya.MSpace.kObject)
            return [
                [positions[i].x, positions[i].y, positions[i].z]
                for i in range(positions.length())
            ]
        except RuntimeError:
            print(f"{meshName} is missing, skipping it")
            return None
    def get_mesh_vertex_positions_from_dnafile(self,dna):
        current_vertices_positions = {}
        for mesh_index, name in enumerate(dna.meshes.names):
            position_count = dna.get_vertex_position_count(mesh_index)
            positions = [dna.get_vertex_position(vertex_index = i,mesh_index = mesh_index) for i in range(position_count)]
            current_vertices_positions[name] = {"mesh_index": mesh_index,"positions":positions}
        return current_vertices_positions

    def run_vertices_command(
        self,calibrated, old_vertices_positions, new_vertices_positions, mesh_index
    ):
        # Making deltas between old vertices positions and new one
        deltas = []
        for new_vertex, old_vertex in zip(new_vertices_positions, old_vertices_positions):
            delta = []
            for new, old in zip(new_vertex, old_vertex):
                delta.append(new - old)
            deltas.append(delta)

        # This is step 5 sub-step c
        new_neutral_mesh = SetVertexPositionsCommand(
            mesh_index, deltas, VectorOperation_Add
        )
        commands = CommandSequence()
        # Add nex vertex position deltas (NOT ABSOLUTE VALUES) onto existing vertex positions
        commands.add(new_neutral_mesh)
        commands.run(calibrated)

        # Verify that everything went fine
        if not Status.isOk():
            status = Status.get()
            raise RuntimeError(f"Error run_vertices_command: {status.message}")

    def save_dna(self):
        CHARACTER_DNA = self.ui.lineEdit_dnaPath.text()
        reader = self.load_dna_reader(CHARACTER_DNA)
        calibrated = DNACalibDNAReader(reader)
        self.run_joints_command(reader, calibrated)
        dna = DNA(CHARACTER_DNA)
        current_vertices_positions = self.get_mesh_vertex_positions_from_dnafile(dna)
        for name, item in current_vertices_positions.items():
            new_vertices_positions = self.get_mesh_vertex_positions_from_scene(name)
            if new_vertices_positions:
                self.run_vertices_command(
                    calibrated, item["positions"], new_vertices_positions, item["mesh_index"]
                )
        textcontent = self.ui.lineEdit_characterName.text()   
        output_DNA = self.save_dna_funtion(calibrated,textcontent)
        self.ui.lineEdit_dnaPath.setText(output_DNA)
        print(f"DNA {output_DNA} Saved...")
        cmds.refresh()
        message = 'Build a rig based on new DNA?'
        confirmValue = cmds.confirmDialog(title = "Meta Human build rig",ma = "center",message = message, button=['Yes','No'], )
        if confirmValue == "Yes":
            self.assemble_maya_scene(output_DNA)
        else:
            print("No rig was built based on the new DNA...")
        # self.assemble_maya_scene()

    def assemble_maya_scene(self,dna_path):
        MODIFIED_CHARACTER_DNA = dna_path
        ROOT_PATH = self.ui.lineEdit_MetaHumanPath.text()
        DATA_DIR = f"{ROOT_PATH}/data"
        ADDITIONAL_ASSEMBLE_SCRIPT = f"{DATA_DIR}/additional_assemble_script.py"
        dna = DNA(MODIFIED_CHARACTER_DNA)
        config = RigConfig(
            gui_path=f"{DATA_DIR}/gui.ma",
            analog_gui_path=f"{DATA_DIR}/analog_gui.ma",
            aas_path=ADDITIONAL_ASSEMBLE_SCRIPT,
        )
        build_rig(dna=dna, config=config)
        
        head_position = cmds.xform("head",q = 1,t = 1,ws = 1)
        cmds.xform("CTRL_faceGUI",t = [(head_position[0]+20),head_position[1],head_position[2]],ws = 1)
        cmds.setAttr(f"CTRL_faceGUI.rx",90)
        cmds.viewFit( "head_lod0_mesh" )

    def get_joints(self,dna):
        """从DNA中获取骨骼列表及其序列号"""
        joints = {}
        for jointIndex in range(dna.getJointCount()):
            joints[dna.getJointName(jointIndex)] = jointIndex
            #joints.append(dna.getJointName(jointIndex))
        return joints

    def remove_joints_calibrate_dna(self):
        """移除DNA中的骨骼"""
        CHARACTER_DNA = self.ui.lineEdit_dnaPath.text()
        dna = self.load_dna_reader(CHARACTER_DNA)
        # Copies DNA contents and will serve as input/output parameter to command
        calibrated = DNACalibDNAReader(dna)
        original_joints = self.get_joints(calibrated)
        remove_joints = {k:v for k,v in original_joints.items() if k not in skin_joints}
        for k,v in remove_joints.items():
            original_joints = self.get_joints(calibrated)
            index = original_joints[k]
            command = RemoveJointCommand(index)
            command.run(calibrated)
            print(f"Successfully removed joint `{k}`.",index)
        textcontent = self.ui.lineEdit_characterName.text()
        out_name = f"{textcontent}_removeJoints"
        print("Saving DNA...")
        output_DNA = self.save_dna_funtion(calibrated,out_name)
        self.ui.lineEdit_dnaPath.setText(output_DNA)
        print("Done.")
        cmds.refresh()
        message = 'Build a rig based on new DNA?'
        confirmValue = cmds.confirmDialog(title = "Meta Human build rig",ma = "center",message = message, button=['Yes','No'], )
        if confirmValue == "Yes":
            self.assemble_maya_scene(output_DNA)
        else:
            print("No rig was built based on the new DNA...")
        # self.assemble_maya_scene()

    def addJoints(self):
        """"将骨骼添加到列表中"""
        self.ui.listWidget_BonesList.clear()
        self.ui.listWidget_BonesList.addItems(skin_joints)
        # mel.eval(f'print("Added Bones to listWidget...");')


    def resetMinmumValue_adjust(self):
        """
        Click Select tabWidget and resize the window
        """
        tabObjectName = self.ui.toolBox_RiggingTools.currentWidget()
        tabName = tabObjectName.objectName()
        if tabName == "page_adjust_Bones":
            self.ui.setMinimumWidth(330)
            self.ui.setMinimumHeight(435)
            self.ui.resize(QtCore.QSize(330, 435))
        elif tabName == "page_MetaHuman":
            self.ui.setMinimumWidth(460)
            self.ui.setMinimumHeight(445)
            self.ui.resize(QtCore.QSize(460, 445))
        elif tabName == "page_AboutMe":
            self.ui.setMinimumWidth(400)
            self.ui.setMinimumHeight(260)
            self.ui.resize(QtCore.QSize(400, 260))   
  

    def getCalibrationPath(self):
        """"指定Meta Human功能路径"""
        fileDialog = QtWidgets.QFileDialog(self.ui)
        fileDialog.setDirectory("C:/dna_calibration")
        file_path = fileDialog.getExistingDirectory(self.ui, "Select MetaHuman-DNA-Calibration File Path")
        self.ui.lineEdit_MetaHumanPath.setText(file_path)


    def getDNAFile(self):
        """指定DNA文件路径"""
        filePath = getFilePath.getFilePath(self.ui, "Select DNA File","DNA File (*.dna);;All File (*.*)")
        self.ui.lineEdit_dnaPath.setText(filePath)

    def delete_constraints(self):
        """选择并删除非关节节点"""
        namespace = "DHIhead"
        if not cmds.namespace(exists=namespace):
            select_joint_name = "root"
            spine04Name = "spine_04"
        else:
            select_joint_name = "DHIhead:root"
            spine04Name = "DHIhead:spine_04"
        constraints = cmds.listRelatives(select_joint_name,ad = 1,type = "constraint")
        cmds.delete(constraints)
        cmds.parent(spine04Name,w = 1)
        cmds.delete(select_joint_name)
    #select_and_delete_non_joints(""DHIhead:root"")
    #select_and_delete_non_joints(""root"")

    def add_constraints(self,body_joint, constrain_head_joint):
        """为指定骨骼添加父约束和缩放约束"""
        cmds.parentConstraint(body_joint, constrain_head_joint, w=1, mo=1)
        cmds.scaleConstraint(body_joint, constrain_head_joint, w=1, mo=1)

    def get_body_joints(self,joint_names):
        """获取所有骨骼的矩阵并设置到对应的约束骨骼"""
        body_joint_dict = {}
        for head_jnt in joint_names:
            if cmds.objExists(head_jnt):
                constrain_head_joint = head_jnt
                body_joint = head_jnt.replace("DHIhead", "DHIbody")
            elif cmds.objExists(head_jnt.split(":")[-1]):
                constrain_head_joint = head_jnt.split(":")[-1]
                body_joint = f"DHIbody:{constrain_head_joint}"
            body_joint_dict[constrain_head_joint] = body_joint

            matrix_value = cmds.xform(body_joint, q=1, ws=1, m=1)
            cmds.xform(constrain_head_joint, ws=1, m=matrix_value)
        return body_joint_dict

    def parent_head_child_joints(self,facil_joints):
        """处理面部关节的父子关系"""
        head_child_joint = [i if cmds.objExists(i) else i.split(":")[-1] for i in facil_joints]
        head_child_joint_dict = {i: cmds.listRelatives(i, ap=1, type="joint")[0] for i in head_child_joint}
        cmds.parent(head_child_joint, w=1)
        return head_child_joint_dict

    def createFacialBones(self):
        """创建 root -- spine_03 的骨骼，DNA"""
        namespace = "DHIhead"
        bonesList = ["root", "pelvis", "spine_01", "spine_02", "spine_03",]
        if cmds.namespace(exists=namespace):
            facialBones = [f"DHIhead:{i}" for i in bonesList]
            spine4Name = "DHIhead:spine_04"
        else:
            facialBones = bonesList
            spine4Name = "spine_04"
        parentBoneName = None
        for jnt in facialBones:
            jntName = jnt.split(":")[-1]
            bodyBoneName = f"DHIbody:{jntName}"
            headBoneName = cmds.createNode("joint",name = jnt,ss = 1)
            matrix_value = cmds.xform(bodyBoneName, q=1, ws=1, m=1)
            if parentBoneName:
                cmds.parent(headBoneName,parentBoneName)
            cmds.xform(headBoneName, ws=1, m=matrix_value)
            parentBoneName = headBoneName    
        cmds.makeIdentity(facialBones[0], apply=1, t=1, r=1, s=1, n=0, pn=1)
        cmds.parent(spine4Name,facialBones[-1])
        cmds.select(facialBones[0],r = 1)

    def delete_nameSpace(self):
        nameSpace = "DHIhead"
        cmds.namespace(removeNamespace=nameSpace,mergeNamespaceWithRoot  = 1,f = 1)

    def adjust_Bones(self):
        """调整面部骨骼，对齐到身体骨骼"""
        constrain_names = [
            "DHIhead:root", "DHIhead:pelvis", "DHIhead:spine_01", "DHIhead:spine_02", "DHIhead:spine_03",
            "DHIhead:spine_04", "DHIhead:spine_05", "DHIhead:neck_01", "DHIhead:neck_02", "DHIhead:head",
            "DHIhead:clavicle_l", "DHIhead:upperarm_l", "DHIhead:upperarm_correctiveRoot_l", "DHIhead:upperarm_bck_l",
            "DHIhead:upperarm_fwd_l", "DHIhead:upperarm_in_l", "DHIhead:upperarm_out_l", "DHIhead:clavicle_out_l",
            "DHIhead:clavicle_scap_l", "DHIhead:clavicle_r", "DHIhead:upperarm_r", "DHIhead:upperarm_correctiveRoot_r",
            "DHIhead:upperarm_bck_r", "DHIhead:upperarm_in_r", "DHIhead:upperarm_fwd_r", "DHIhead:upperarm_out_r",
            "DHIhead:clavicle_out_r", "DHIhead:clavicle_scap_r", "DHIhead:clavicle_pec_r", "DHIhead:spine_04_latissimus_l",
            "DHIhead:spine_04_latissimus_r", "DHIhead:clavicle_pec_l"
        ]

        facil_joints = ["DHIhead:FACIAL_C_FacialRoot", "DHIhead:FACIAL_C_Neck1Root", "DHIhead:FACIAL_C_Neck2Root"]      
        select_joint_name = "root"
        head_child_joint_dict = self.parent_head_child_joints(facil_joints)
        body_joint_dict = self.get_body_joints(constrain_names)
        try:
            cmds.makeIdentity(select_joint_name, apply=1, t=1, r=1, s=1, n=0, pn=1)
        except Exception as erro:
            print(erro)
        for k, v in body_joint_dict.items():
            self.add_constraints(v, k)

        for k, v in head_child_joint_dict.items():
            cmds.parent(k, v)

    def delete_selected_skinCluster(self):
        meshs = cmds.ls(sl = 1)
        for mesh in meshs:
            historys = cmds.listHistory(mesh,ac = 1)
            skinClusters = [i for i in historys if cmds.nodeType(i) == "skinCluster"]
            cmds.delete(skinClusters)

    def add_namespace_to_selected(self):
        namespace = "DHIhead"
        cmds.select(hi = 1)
        selected_objects = cmds.ls(selection=True,type = "joint")
        if not selected_objects:
            cmds.warning("Nothing Selected...")
            return
        if not cmds.namespace(exists=namespace):
            cmds.namespace(add=namespace)
        for obj in selected_objects:
            if ':' in obj:
                cmds.warning(f"{obj} Name Space Exists")
                continue
            else:
                new_name = f"{namespace}:{obj}"
                cmds.rename(obj, new_name)
        cmds.select(cl = 1)


if __name__ == "__main__":
    app = QtWidgets.QApplication
    mainwindow = RiggingByMetaHuman()
    mainwindow.ui.show()
    app.exec_()
