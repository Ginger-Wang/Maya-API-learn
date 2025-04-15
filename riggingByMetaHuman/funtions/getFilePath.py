import sys,os
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds
def getPath(uiName,conntent):
    """"指定路径"""
    mayafilePath = getOpenedMayaPath()
    fileDialog = QtWidgets.QFileDialog(uiName)
    fileDialog.setDirectory(mayafilePath)
    file_path = fileDialog.getExistingDirectory(uiName,conntent)
    return file_path

def getFilePath(uiName, conntet,fileType):
    fileDialog = QtWidgets.QFileDialog(uiName)
    mayafilePath = getOpenedMayaPath()
    fileDialog.setDirectory(mayafilePath)
    # fileType =  "DNA File (*.dna);;All File (*.*)"
    pathName = fileDialog.getOpenFileName(uiName, conntet, mayafilePath,fileType)
    return pathName[0]

def getOpenedMayaPath():
    path = cmds.file(q=1,location = 1)
    if path == "unknown":
        return None
    else:        
        file_Path,file_Name = os.path.split(path)
        return file_Path
