#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,standalone
#standalone.initialize()

file_Path, fileName = os.path.split(__file__)
# path = '//Cnshasgamefsv1/MGS3/Users/WangJinge/Scripts/test'
uiName = "standalone.ui"
uiPath = os.path.join(file_Path, uiName)

class ExportFiles(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(ExportFiles, self).__init__(parent)
        self.setupUI()

    def setupUI(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath)
        uiName = self.ui
        uiName.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        uiName.pushButton.clicked.connect(self.getAllMayaFiles)
        uiName.export_pushButton.clicked.connect(self.runExport)
        uiName.loadFile_pushButton.clicked.connect(self.getSourceFile)

    def getAllMayaFiles(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        pathName = fileDialog.getExistingDirectory(self.ui,"Export Files")
        self.ui.lineEdit.setText(pathName)
        mayaFiles = [i for i in os.listdir(pathName) if os.path.splitext(i)[-1] == ".fbx"]
        self.ui.listWidget.clear()
        self.ui.listWidget.addItems(mayaFiles)
    def getSourceFile(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        pathName = fileDialog.getOpenFileName(
            self.ui,"Select MayaFile","",
            "Maya File (*.ma *.mb);;FBX(*.fbx);;All File (*.*)")
        #print pathName
        self.ui.mayaFile_lineEdit.setText(pathName[0])

    def runExport(self):
        standalone.initialize()
        cmds.loadPlugin("fbxmaya.mll")
        pathName = self.ui.lineEdit.text()
        fileNames = self.ui.listWidget.selectedItems()
        mayaFileName = self.ui.mayaFile_lineEdit.text()
        #F:/Maya_Project/snake/000normal_idle.fbx
        cmds.file(mayaFileName,o = True)
        mayaFilesPath = "%s/MayaFiles"%(pathName)
        if not os.path.isdir(mayaFilesPath):
            os.mkdir(mayaFilesPath)
        for name in fileNames:
            fbxFileName = name.text()
            fbxFilePath = os.path.join(pathName,fbxFileName)
            #print(fbxFilePath.replace("\\","/"))
            cmds.file(fbxFilePath,i = True)
            cmds.refresh()
            cmds.currentUnit( time='60fps' )
            maxTime,minTime = self.getTimes()
            cmds.playbackOptions(ast = minTime,aet = maxTime,max = maxTime,min = minTime)
            #allJoints = cmds.ls(type="joint")
            fullPath = os.path.join(mayaFilesPath, fbxFileName.replace(".fbx", ".ma"))
            cmds.file(rename=fullPath)
            cmds.file(save=True, type='mayaAscii')
            #print( "\n".join(allJoints))

    def getTimes(self):
        anis = cmds.ls(type = 'animCurve')
        maxTime = max([cmds.keyframe(i,q = 1)[-1] for i in anis])
        minTime = min([cmds.keyframe(i,q = 1)[0] for i in anis])
        return maxTime,minTime

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = ExportFiles()
    mainwindow.ui.show()
    sys.exit(app.exec_())
'''

@echo off
cmd /k mayapy D:\MayaPycharm\mayaStandalone.py

后台运行Maya输出打印场景中的所有骨骼，以上是bat批处理运行此代码
'''
