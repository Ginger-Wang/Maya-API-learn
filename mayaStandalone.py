#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,standalone
#standalone.initialize()

path = 'D:/MayaPycharm/Maya_Scripts'
uiName = "standalone.ui"
uiPath = os.path.join(path, uiName)
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

    def getAllMayaFiles(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        pathName = fileDialog.getExistingDirectory(self.ui,"Export Files")
        self.ui.lineEdit.setText(pathName)
        mayaFiles = [i for i in os.listdir(pathName) if os.path.splitext(i)[-1] == ".ma"]
        self.ui.listWidget.clear()
        self.ui.listWidget.addItems(mayaFiles)
    def runExport(self):
        standalone.initialize()
        pathName = self.ui.lineEdit.text()
        fileNames = self.ui.listWidget.selectedItems()
        #print fileNames
        for name in fileNames:
            print(os.path.join(pathName,name.text()))
            cmds.file(os.path.join(pathName,name.text()),o = True)
            allJoints = cmds.ls(type="joint")
            print( "\n".join(allJoints))

'''

@echo off
cmd /k mayapy D:\MayaPycharm\mayaStandalone.py

后台运行Maya输出打印场景中的所有骨骼，以上是bat批处理运行此代码
'''



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = ExportFiles()
    mainwindow.ui.show()
    sys.exit(app.exec_())
