import sys,os
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,mel
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from importlib import reload
from funtions import getFilePath

def get_maya_main_window():
    """获取Maya的主窗口"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)

file_Path = os.path.dirname(__file__)
uiName = "exportFbxTools.ui"
uiPath = os.path.join(file_Path, uiName)
reload(getFilePath)
local_path = getFilePath.getOpenedMayaPath()

class ExportFBXTools(QtWidgets.QMainWindow):
    def __init__(self,*args, **kwargs):
        super(ExportFBXTools,self).__init__(*args, **kwargs)
        self.ui_funtion()        

    def ui_funtion(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath, parentWidget=get_maya_main_window())
        self.ui.setWindowFlags(QtCore.Qt.Window)
        self.ui.lineEdit_fbxPath.setText(local_path)
        # self.get_export_path() 
        self.ui.pushButton_loadfbxPath.clicked.connect(self.get_export_path)
        self.ui.pushButton_export.clicked.connect(self.export_file)

    def get_export_path(self):
        filePath = getFilePath.getPath(self.ui,"Select The Export Folder")
        self.ui.lineEdit_fbxPath.setText(filePath) #getFilePath

    def set_ui(self):
        self.ui.setMinimumWidth(560)
        self.ui.setMinimumHeight(210)
        self.ui.resize(QtCore.QSize(560, 210))

    def export_selected_to_fbx(self,file_path):
        # 确保 FBX 插件是被加载的
        if not cmds.pluginInfo('fbxmaya', query=True, loaded=True):
            cmds.loadPlugin('fbxmaya')
        cmds.FBXExportSmoothingGroups("-v",True)    # 导出平滑组
        cmds.FBXExportHardEdges("-v",False)         # 不导出硬边
        cmds.FBXExportTangents("-v",True)           # 导出切线
        cmds.FBXExportInstances("-v",False)         # 不导出实例
        cmds.FBXExportBakeComplexAnimation("-v",False) # 不烘焙复杂动画
        cmds.FBXExportInputConnections("-v",False)  # 不导出输入连接
        cmds.FBXExportSkins("-v",True)              # 导出皮肤变形
        cmds.FBXExportShapes("-v",True)             # 导出形状变换
        cmds.FBXExportCameras("-v",False)           # 不导出摄像机
        cmds.FBXExportLights("-v",False)            # 不导出灯光
        cmds.FBXExportReferencedAssetsContent("-v",False) # 不导出引用的资产内容
        #cmds.FBXExport(f=True, file=file_path)
        cmds.FBXExport('-file', file_path, '-s')

    def export_file(self):
        file_Path = self.ui.lineEdit_fbxPath.text()
        fbxName = self.ui.lineEdit_fbxName.text()        
        headPart = self.ui.radioButton_headPart.isChecked()
        bodyPart = self.ui.radioButton_bodyPart.isChecked()
        otherPart = self.ui.radioButton_otherPart.isChecked()
        if fbxName:
            fullPath = os.path.join(file_Path,f"{fbxName}.fbx")
            # print(fullPath)
        else:
            message = 'The FBX file name was not entered.\nDo you want to enter it according to the selected object name?'
            confirmValue = cmds.confirmDialog(title = "My Funtion",ma = "center",message = message, button=['Yes','No'], )
            if confirmValue == "Yes":
                fbxName = cmds.ls(sl = 1)[0]
                self.ui.lineEdit_fbxName.setText(fbxName)
                cmds.refresh()
            else:
                cmds.warning("Please enter an export file name in 'Export Name : '")
                # mel.eval(f'print("Please enter an FBX file name...");')
                return
        fullPath = os.path.join(file_Path,f"{fbxName}.fbx")
        if headPart:
            nameSpace = "DHIhead"
            if cmds.namespace(exists=nameSpace):
                cmds.select(f"{nameSpace}:spine_04",add = 1)
            else:
                cmds.select("|spine_04",add = 1)
            # self.export_selected_to_fbx(fullPath)
        if bodyPart:
            nameSpace = "DHIbody"
            if cmds.namespace(exists=nameSpace):
                cmds.select(f"{nameSpace}:root",add = 1)
            else:
                cmds.select("|root",add = 1)
        if otherPart:
            nameSpace = "DHIbody"
            if cmds.namespace(exists=nameSpace):
                cmds.select(f"{nameSpace}:root",add = 1)
            else:
                cmds.select("|root",add = 1)
        self.export_selected_to_fbx(fullPath)
        cmds.select(cl = 1)


if __name__ == "__main__":
    app = QtWidgets.QApplication
    mainwindow = ExportFBXTools()
    mainwindow.ui.show()
    app.exec_()
