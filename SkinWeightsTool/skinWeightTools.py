import os
import sys
import xml.etree.ElementTree as ET
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,mel
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui

def get_maya_main_window():
    """获取Maya的主窗口"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

file_Path = os.path.dirname(__file__)
uiName = "skinWeightTools.ui"
uiPath = os.path.join(file_Path, uiName)

class SkinWeightTools(QtWidgets.QMainWindow):
    def __init__(self, parent=get_maya_main_window()):
        super(SkinWeightTools, self).__init__(parent)
        self.load_ui()
        
    def load_ui(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath)
        # 设置窗口始终在Maya主窗口顶部显示
        self.ui.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.resetMinmumValue()
        self.ui.toolBox.currentChanged.connect(self.resetMinmumValue)

        self.ui.pushButton_LoadMesh.clicked.connect(self.addMeshToListWidget)
        self.ui.pushButton_LoadPath.clicked.connect(self.getAllXMLFiles)
        self.ui.lineEdit_FilePath.textChanged.connect(self.editItems)
        
        self.ui.pushButton_ImportWeight.clicked.connect(self.importSkinWeight)
        self.ui.pushButton_ImportSSkinweight.clicked.connect(self.importSSkinweight)
        self.ui.pushButton_SaveWeight.clicked.connect(self.savaSkinWeight)
        
        self.ui.pushButton_selcteJointByMesh.clicked.connect(self.selectJoints)
        self.ui.pushButton_selcteJointByXML.clicked.connect(self.selectJoints)
        
        self.ui.listWidget_MeshList.itemSelectionChanged.connect(self.selectMeshs)
        
        self.ui.pushButton_Reload.clicked.connect(self.editItems)
        
        self.ui.listWidget_XMLLIst.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.listWidget_MeshList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.listWidget_MeshList.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.listWidget_XMLLIst.customContextMenuRequested.connect(self.show_context_menu)
        self.ui.pushButton_Transferskin.clicked.connect(self.toDoTransferSkinWeights)

        self.ui.pushButton_LoadPrefix.clicked.connect(self.getPrefix)


        self.ui.pushButton_testFuntion.clicked.connect(self.importNoSkinClusterWeight)
        
    def translateName(self,textName):
        special_chars = "/:*?\"<>|\\"
        
        # 创建一个转换表，将特殊字符映射为空格
        translation_table = str.maketrans(special_chars, '_' * len(special_chars))

        # 使用 translate 方法进行转换
        converted_text = textName.translate(translation_table)

        return converted_text
    
    def savaSkinWeight(self):
        saveToPath = self.ui.lineEdit_FilePath.text()
        if not saveToPath:
            saveToPath = self.exportFilePath()
        meshs = self.ui.listWidget_MeshList.selectedItems()
        meshNames = [name.text() for name in meshs]
        for mesh in meshNames:
            skinDict = self.getSkinCluster(mesh)
            xmlName = self.translateName(mesh)
            deformerName = skinDict[mesh][0]
            print(f"{xmlName}.xml",deformerName)
            cmds.deformerWeights (f"{xmlName}.xml", ex=True, deformer=deformerName,path = saveToPath)
        # print("savaSkinWeight funtion...")

    def exportFilePath(self):
        path = cmds.file(q=1,location = 1)
        file_Path,file_Name = os.path.split(path)
        return file_Path


    def importSkinWeight(self):
        saveToPath = self.ui.lineEdit_FilePath.text()
        meshs = self.ui.listWidget_MeshList.selectedItems()
        meshNames = [name.text() for name in meshs]
        for name in meshNames:
            xmlName = self.translateName(name)
            skinDict = self.getSkinCluster(name)
            if os.path.exists(os.path.join(saveToPath,f"{xmlName}.xml")):
                self.importSkinWeights(f"{xmlName}.xml",saveToPath,skinDict[name][0])
                # cmds.deformerWeights(f"{xmlName}.xml",im = 1,m = "index",ignoreName = 1,deformer = skinDict[name][0],path = saveToPath)
                # cmds.skinCluster(skinDict[name][0],e=1 ,forceNormalizeWeights= 1)
                print(f"{name} Imported SkinWeight ...")
            else:
                cmds.warning(f"{xmlName}.xml Do't exist...")

    def importSSkinweight(self):
        meshs = self.ui.listWidget_MeshList.selectedItems()
        meshNames = [name.text() for name in meshs]
        skinWeights = self.ui.listWidget_XMLLIst.selectedItems()
        skinWeightsPath =  [name.text() for name in skinWeights]
        for mesh,skin in zip(meshNames,skinWeightsPath):
            xmlName = self.translateName(mesh)
            skinDict = self.getSkinCluster(mesh)
            pathName,weightFileName = os.path.split(skin)
            self.importSkinWeights(weightFileName,pathName,skinDict[mesh][0])
            mel.eval(f'print("{mesh} Skin Weights Imported...");')
            # print(xmlName,skinDict,pathName,weightFileName)
    def importNoSkinClusterWeight(self):
        saveToPath = self.ui.lineEdit_FilePath.text()
        meshs = cmds.ls(sl = 1)
        noSkinMeshs = []
        for mesh in meshs:
            xmlName = self.translateName(mesh)
            xmlFullPath = os.path.join(saveToPath,f"{xmlName}.xml")
            skinDict = self.getSkinCluster(mesh)
            if skinDict[mesh][0]:
                self.importSkinWeights(f"{xmlName}.xml",saveToPath,skinDict[mesh][0])
            elif os.path.exists(xmlFullPath):
                jointsList = self.getjointsFromXml(xmlFullPath)
                skinClusterName = cmds.skinCluster(jointsList,mesh,tsb = True) #skinCluDS = cmds.skinCluster(skinedBones,polyName, tsb =True)
                self.importSkinWeights(f"{xmlName}.xml",saveToPath,skinClusterName[0])
                print(xmlFullPath)
            else:
                noSkinMeshs.append(mesh)
        if noSkinMeshs:
            cmds.select(noSkinMeshs)

    def importSkinWeights(self,xmlFile,xmlPath,skinClusterName):
        cmds.deformerWeights(xmlFile,im = 1,m = "index",ignoreName = 1,deformer = skinClusterName,path = xmlPath)
        cmds.skinCluster(skinClusterName,e=1 ,forceNormalizeWeights= 1)
        
    def getjointsFromXml(self,path):
        weightDict = self.getXMLContent(path)
        allJointFromXML = weightDict["source"]
        existJoint = [i for i in allJointFromXML if cmds.objExists(i)]
        notExistJoint = [i for i in allJointFromXML if not cmds.objExists(i)]
        if notExistJoint:
            QtWidgets.QMessageBox.warning(self, "Lost Bones", f"{notExistJoint} These bones don't exist.")
        return existJoint

    def selectJoints(self):
        jointName = []
        sender = self.sender()
        button_name = sender.objectName()
        print(button_name)
        if button_name == "pushButton_selcteJointByXML":
            xmlFiles = self.ui.listWidget_XMLLIst.selectedItems()
            selectedXML = [name.text() for name in xmlFiles]
            for path in selectedXML:
                weightDict = self.getXMLContent(path)
                allJointFromXML = weightDict["source"]
                existJoint = [i for i in allJointFromXML if cmds.objExists(i)]
                notExistJoint = [i for i in allJointFromXML if not cmds.objExists(i)]
                if notExistJoint:
                    QtWidgets.QMessageBox.warning(self, "Lost Bones", f"{notExistJoint} These bones don't exist.")
                    print(notExistJoint)
                jointName.extend([jnt for jnt in existJoint if jnt not in jointName])

            # jointNames = [self.getXMLContent(i) for i in selectedXML]
            # weightDict = self.getXMLContent()
        elif button_name == "pushButton_selcteJointByMesh":
            meshs = self.ui.listWidget_MeshList.selectedItems()
            meshNames = [name.text() for name in meshs]
            for mesh in meshNames:
                skinDict = self.getSkinCluster(mesh)
                jointName.extend([jnt for jnt in skinDict[mesh][1] if jnt not in jointName])
        cmds.select(jointName)
        print(f"selectJoints {jointName}")
        
    def selectMeshs(self):
        meshs = self.ui.listWidget_MeshList.selectedItems()
        meshNames = [name.text() for name in meshs] 
        cmds.select(meshNames)
        
    def getSkinCluster(self,meshName):
        historys = cmds.listHistory(meshName,ac = 1)
        joints = [i for i in historys if cmds.nodeType(i) == "joint"]
        skinCusters = [i for i in historys if cmds.nodeType(i) == "skinCluster"]       
        if skinCusters:
            skinDict = {meshName : [skinCusters[0],joints]}
            # mel.eval(f'print("skinCluster name is {skinCusters}");')
        else:
            skinDict = {meshName : [None,None]}
        return skinDict
                    
    def addMeshToListWidget(self):
        items = cmds.ls(sl = 1)
        meshs = [i for i in items if self.getSkinCluster(i)[i][0]]
        self.ui.listWidget_MeshList.clear()
        self.ui.listWidget_MeshList.addItems(meshs)
        mel.eval(f'print("Added selected object to listWidget...");')

    def getAllXMLFiles(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        file_path = fileDialog.getExistingDirectory(self.ui, "Select Skin Weight Path")
        self.ui.lineEdit_FilePath.setText(file_path)
        self.editItems()

    def editItems(self):
        filePath = self.ui.lineEdit_FilePath.text()
        xmlFiles = []
        for root, dirs, files in os.walk(filePath, followlinks=True):
            # print(root,dirs)
            for name in files:
                file_name = os.path.join(root, name)
                if os.path.splitext(file_name)[-1] == ".xml":
                    xmlFiles.append(file_name.replace("\\", "/"))
        # fbxFiles = [i for i in os.listdir(pathName) if os.path.splitext(i)[-1] == ".fbx"]
        self.ui.listWidget_XMLLIst.clear()
        self.ui.listWidget_XMLLIst.addItems(xmlFiles)

    def getXMLContent(self,xmlFullPath):
        # 读取XML文件内容
        with open(xmlFullPath, 'r') as file:
            xml_content = file.read()
        # 使用ElementTree解析XML内容
        root = ET.fromstring(xml_content)
        weightDict = {}
        # 提取deformer，source，shape的内容
        weights = root.findall('weights')
        for weight in weights:
            deformerName = weight.get('deformer')
            sourceName = weight.get('source')
            shapeName = weight.get('shape')
            # 确保'deformer'键存在且是列表，然后添加元素（如果不存在）
            if "deformer" not in weightDict or not isinstance(weightDict["deformer"], list):
                weightDict["deformer"] = []
            if "source" not in weightDict or not isinstance(weightDict["source"], list):
                weightDict["source"] = []
            if "shape" not in weightDict or not isinstance(weightDict["shape"], list):
                weightDict["shape"] = []
                        
            # 检查新值是否已存在于列表中，如果不存在则添加
            if deformerName not in weightDict["deformer"]:
                weightDict["deformer"].append(deformerName)  
            if sourceName not in weightDict["source"]:
                weightDict["source"].append(sourceName) 
            if shapeName not in weightDict["shape"]:
                weightDict["shape"].append(shapeName) 
            #print(f'deformer: {deformer}, source: {source}, shape: {shape}\n')
        return weightDict

    def getMeshNameFromXML(self,path):
        shapeName = self.getXMLContent(path)["shape"]
        if shapeName:
            return shapeName[0]

    def show_context_menu(self, position):
        sender_widget = self.sender()
        menu = QtWidgets.QMenu()

        delete_action = menu.addAction("Remove Item")
        eleteFile_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_item(sender_widget))
        eleteFile_action.triggered.connect(lambda: self.delete_file(sender_widget))
        menu.exec_(sender_widget.mapToGlobal(position))

    def delete_item(self, list_widget):
        selected_item = list_widget.selectedItems()
        for item in selected_item:
            list_widget.takeItem(list_widget.row(item))
            print(f"Deleted item: {item.text()}")

    def delete_file(self,list_widget):
        selected_item = list_widget.selectedItems()
        selected_items = [i.text() for i in selected_item]
        if list_widget.objectName() == "listWidget_MeshList":
            cmds.delete(selected_items)
            # QtWidgets.QMessageBox.information(self, "提示", f"File {selected_items} Deleted...")
        elif list_widget.objectName() == "listWidget_XMLLIst":
            for path in selected_items:
                if os.path.exists(path):
                    os.remove(path)
                else:
                    QtWidgets.QMessageBox.warning(self, "警告", f"File {path} not exists")
            QtWidgets.QMessageBox.information(self, "提示", f"File {selected_items} Deleted...")
           
        for item in selected_item:
            list_widget.takeItem(list_widget.row(item))


    def getChild(self,polyName):
        listChild = cmds.listRelatives(polyName,ad= 1,type = 'transform',fullPath = 1)
        if listChild:
            childShapes = cmds.listRelatives(listChild,ad = 1,shapes = 1,fullPath = 1) 
        else:
            childShapes = cmds.listRelatives(polyName,ad = 1,shapes = 1,fullPath = 1) 
        # print(f"{polyName} is shape is {childShapes}")
        childPolys = cmds.listRelatives(childShapes,p = 1,type = 'transform',fullPath = 1)
        if childPolys:
            return childPolys
        else:
            return None    
    
    def skinIt(self,skinedBones,polyName,skinClu): 
        skinCluDS = self.getAllJnt(polyName)   
        if skinCluDS:
            cmds.copySkinWeights(ss=skinClu,ds=skinCluDS[0],nm=True,sa='closestPoint', ia='closestJoint')    
        else:
            skinCluDS = cmds.skinCluster(skinedBones,polyName, tsb =True)
            cmds.copySkinWeights(ss=skinClu,ds=skinCluDS[0],nm=True,sa='closestPoint', ia='closestJoint')

    def getAllJnt(self,polyName):    
        historys= cmds.listHistory(polyName,ac = 1)
        skinClus = [i for i in historys if cmds.nodeType(i) == "skinCluster"]
        if skinClus:
            skinClu = skinClus[0]
            skinedBones =  cmds.skinCluster(skinClu,query=True,inf=True)
            return skinClu,skinedBones
        else:
            return None


    def wrapSkin(self):    
        selPolys = cmds.ls(sl = 1)
        skinClu,skinedBones = self.getAllJnt(selPolys[-1])
        for polyName in selPolys:
            if polyName != selPolys[-1]:
                childPolys = self.getChild(polyName)
                if childPolys:                
                    childs = set(childPolys)
                    for childPoly in childs:
                        try:
                            self.skinIt(skinedBones,childPoly,skinClu)
                        except Exception as err:
                            cmds.warning(err)                        
                else:
                    self.skinIt(skinedBones,polyName,skinClu)

    def getSkinedMesh(self,nameSpace):
        skinedMeshs = []
        if nameSpace:
            allNameSpaceMesh = cmds.ls(f"{nameSpace}:*",type = "mesh")
            meshTransforms = cmds.listRelatives(allNameSpaceMesh,p = 1,type = "transform",fullPath = 1)
            for i in meshTransforms:
                splitList = i.split("|")
                newList = []
                for spl in splitList:
                    nameSpaceList = spl.split(":")[-1]
                    newList.append(nameSpaceList)
                skinedMeshs.append("|".join(newList))
        return skinedMeshs,meshTransforms

    def transferSkinWeight(self,nameSpace):
        # nameSpace = self.ui.lineEdit_Prefix.text()        
        skinedMeshs,meshTransforms = self.getSkinedMesh(nameSpace)
        errorObj = []
        for sm,mt in zip(skinedMeshs,meshTransforms):
            skinedHistory = self.getAllJnt(sm)
            try:
                self.skinIt(skinedHistory[1],mt,skinedHistory[0])
            except Exception as err:        
                errorObj.append(mt)
            cmds.refresh()   
        cmds.select(errorObj)

    def getPrefix(self):
        selections = cmds.ls(sl = 1)[0]
        splitNames = selections.split(":")[:-1]
        prefix = ":".join(splitNames)
        self.ui.lineEdit_Prefix.setText(prefix)
        # pm.textFieldButtonGrp("prefixFileload",e = 1,text =prefix)


    def toDoTransferSkinWeights(self):
        nameSpace = self.ui.lineEdit_Prefix.text()
        if nameSpace:
            self.transferSkinWeight(nameSpace)
        else:
            self.wrapSkin()


    def resetMinmumValue(self):
        """
        Click Select tabWidget and resize the window
        """
        tabObjectName = self.ui.toolBox.currentWidget()
        tabName = tabObjectName.objectName()

        if tabName == "skinWeighttool_tab":
            self.ui.setMinimumWidth(575)
            self.ui.setMinimumHeight(600)
            self.ui.resize(QtCore.QSize(575, 600))
        elif tabName == "transferSkinWeight_tab":
            self.ui.setMinimumWidth(575)
            self.ui.setMinimumHeight(275)
            self.ui.resize(QtCore.QSize(575, 275))
        elif tabName == "aboutme_tab":
            self.ui.setMinimumWidth(575)
            self.ui.setMinimumHeight(260)
            self.ui.resize(QtCore.QSize(460, 260))   

    def testFuntion(self):
        filePath = self.ui.lineEdit_FilePath.text()
        if filePath:
            print(f"File path is {filePath}")
        else:
            print("None...")
    
if __name__ == "__main__":
    app = QtWidgets.QApplication
    mainwindow = SkinWeightTools()
    mainwindow.ui.show()
    app.exec_()
    

"""
#install to Maya 2023

import sys,os
from maya import cmds,mel

def onMayaDroppedPythonFile(parm):
	_add_shelfButton()

def _add_shelfButton():
    file_Path,fileName = os.path.split(__file__)
    paths = sys.path
    gShelfTopLevel = mel.eval('$tmpVar=$gShelfTopLevel')
    parentName = cmds.tabLayout(gShelfTopLevel,q= 1,selectTab =1)
    scriptType = "py"
    scriptFile = "skinWeightTools"
    command =(f"""import sys,os
from importlib import reload
from PySide2 import QtWidgets, QtUiTools, QtCore
paths = sys.path
addPath = '{file_Path}'
if addPath not in paths:
    sys.path.append(addPath)
import skinWeightTools
reload(skinWeightTools)
app = QtWidgets.QApplication
mainwindow = skinWeightTools.SkinWeightTools()
mainwindow.ui.show()
app.exec_()""")
    #command = "execfile('{0}/{1}.{2}')".format(file_Path,scriptFile,scriptType)
    cmds.shelfButton(c = command  ,image1='pythonFamily.png',sourceType="python",imageOverlayLabel = scriptFile,p = parentName,ann = scriptFile )

"""




















