#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtGui import *
from PySide2.QtCore import *
try:
    from maya import cmds
    import pymel.core as pm
except ImportError,err:
    print err


class UiLoader(QUiLoader):
    def __init__(self, baseinstance, customWidgets=None):
        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets

    def createWidget(self, class_name, parent=None, name=''):
        if parent is None and self.baseinstance:
            return self.baseinstance
        else:
            if class_name in self.availableWidgets():
                widget = QUiLoader.createWidget(self, class_name, parent, name)
            else:
                try:
                    widget = self.customWidgets[class_name](parent)
                except (TypeError, KeyError) as e:
                    raise Exception('No custom widget '+class_name+' found in customWidgets param of UiLoader __init__.')
            if self.baseinstance:
                setattr(self.baseinstance, name, widget)
            return widget


def loadUi(uifile, baseinstance=None, customWidgets=None, workingDirectory=None):
    loader = UiLoader(baseinstance, customWidgets)
    if workingDirectory is not None:
        loader.setWorkingDirectory(workingDirectory)
    widget = loader.load(uifile)
    QMetaObject.connectSlotsByName(widget)
    return widget


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        file_Path = os.path.dirname(__file__)
        loadUi("%s/animtorsToolsAB.ui"%file_Path,self)
        self._rubberPos = None
        self._rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.set_ui()

    def getButtons(self):
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        lastTab = tabWidget.findChild(QWidget, "selectTool_tab")
        bodyUIName = lastTab.findChild(QWidget, "Body_UI")
        leftHandName = lastTab.findChild(QWidget, "LeftHandUI")
        RightHandname = lastTab.findChild(QWidget, "RightHandUI")
        FootUIName = lastTab.findChild(QWidget, "Foot_UI")
        HandUIname = lastTab.findChild(QWidget, "Hand_UI")
        if bodyUIName.isVisible():
            buttons = bodyUIName.findChildren(QPushButton, QRegExp("bodyPB_*"))
        if leftHandName.isVisible():
            buttons = leftHandName.findChildren(QPushButton, QRegExp("bodyPB_*"))
        if RightHandname.isVisible():
            buttons = RightHandname.findChildren(QPushButton, QRegExp("bodyPB_*"))
        if FootUIName.isVisible():
            buttons = FootUIName.findChildren(QPushButton, QRegExp("bodyPB_*"))
        return buttons
    def getAllButtons(self):
        tabWidget = self.findChild(QTabWidget, "tabWidget")
        lastTab = tabWidget.findChild(QWidget, "selectTool_tab")
        buttons = lastTab.findChildren(QPushButton, QRegExp("bodyPB_*"))
        return buttons
    def getButtonCenter(self, pos, rect):
        return QPoint(pos.x(), pos.y())
    def mousePressEvent(self, event):
        super(MainWindow, self).mousePressEvent(event)
        if event.buttons() != Qt.LeftButton:
            return
        self._rubberPos = event.pos()
        self._rubberBand.setGeometry(QRect(self._rubberPos, QSize()))
        buttons = self.getAllButtons()
        for b in buttons:
            b.setChecked(False)
        self._rubberBand.show()
        self.update()
    def mouseMoveEvent(self, event):
        super(MainWindow, self).mouseMoveEvent(event)
        if self._rubberPos:
            pos = event.pos()
            lx, ly = self._rubberPos.x(), self._rubberPos.y()
            #print lx, ly
            rx, ry = pos.x(), pos.y()
            #print rx, ry
            size = QSize(abs(rx - lx), abs(ry - ly))
            #print size
            self._rubberBand.setGeometry(QRect(QPoint(min(lx, rx), min(ly, ry)), size))
            buttons = self.getButtons()
            rect = self._rubberBand.geometry()
            banPos = self._rubberBand.pos()
            print banPos.x(),banPos.y(),rect
            for b in buttons:
                buttonPos = b.pos()
                buttonSize = b.size()
                newPos = QPoint(buttonPos.x(), buttonPos.y()+100.0)
                buttonRect = QRect(newPos, buttonSize)                
                if buttonRect.intersected(rect):
                    print b.objectName(),buttonRect
                    b.setChecked(True)
        self.update()
    def mouseReleaseEvent(self, event):
        super(MainWindow, self).mouseReleaseEvent(event)
        self._rubberBand.hide()
        

    def set_ui(self):
        self.resetMinmumValue()
        self.getReferencesFiles()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.weight_VerticalSlider.valueChanged.connect(self.setValue)
        self.weight_doubleSpinBox.valueChanged.connect(self.setWeightValue)
        self.add_pushButton.clicked.connect(self.applyConstraintButton)
        self.apply_pushButton.clicked.connect(self.applyConstraintButton)
        self.matchtransforms_pushButton.clicked.connect(self.matchTranformsButton)
        self.matchTr_pushButton.clicked.connect(self.matchTrButton)
        self.matchRo_pushButton.clicked.connect(self.matchRoButton)
        self.tabWidget.currentChanged.connect(self.resetMinmumValue)
        self.replacename_pushButton.clicked.connect(self.searchAndReplace)
        self.addPrefix_pushButton.clicked.connect(self.addPrefix)
        self.addSuffix_pushButton.clicked.connect(self.addSuffix)
        self.rename_pushButton.clicked.connect(self.renameaddNumber)
        self.reloadFile_pushButton.clicked.connect(self.getReferencesFiles)
        #self.RightHand_PB.clicked.connect(self.Body_UI.setEnabled(False))



    def resetMinmumValue(self):
        """
        Click Select tabWidget and resize the window
        """
        tabObjectName = self.tabWidget.currentWidget()
        tabName = tabObjectName.objectName()
        if tabName == "rename_tab":
            self.setMinimumWidth(400)
            self.setMinimumHeight(520)
            self.resize(QSize(400, 520))            
        elif tabName == "match_tab":
            self.setMinimumWidth(400)
            self.setMinimumHeight(260)
            self.resize(QSize(400, 260))
        elif tabName == "constraint_tab":
            self.setMinimumWidth(520)
            self.setMinimumHeight(360)
            self.resize(QSize(520, 360))
        elif tabName == "selectTool_tab":
            self.setMinimumWidth(460)
            self.setMinimumHeight(835)
            self.resize(QSize(460, 835))
            self.Hand_UI.close()
        elif tabName == "poseTool_tab":
            self.setMinimumWidth(400)
            self.setMinimumHeight(300)
            self.resize(QSize(400, 300))
        self.update()
    def setBodyUIEnabled(self):

        tabWidget = self.findChild(QTabWidget, "tabWidget")
        bodyUIName = tabWidget.findChild(QWidget, "Body_UI")
        leftHandName = tabWidget.findChild(QWidget, "LeftHandUI")
        RightHandname = tabWidget.findChild(QWidget, "RightHandUI")
        FootUIName = tabWidget.findChild(QWidget, "Foot_UI")
        HandUIname = tabWidget.findChild(QWidget, "Hand_UI")
        LeftHand_BP = tabWidget.findChild(QPushButton, "LeftHand_PB")
        RightHand_PB = tabWidget.findChild(QPushButton, "RightHand_PB")
        Foot_PB = tabWidget.findChild(QPushButton, "Foot_PB")
        print LeftHand_BP.objectName()

        LeftHand_BP.clicked.connect(HandUIname.setEnabled(True))
        LeftHand_BP.clicked.connect(leftHandName.setEnabled(True))
        RightHand_PB.clicked.connect(HandUIname.setEnabled(True))
        RightHand_PB.clicked.connect(RightHandname.setEnabled(True))
        Foot_PB.clicked.connect(HandUIname.setEnabled(True))
        Foot_PB.clicked.connect(FootUIName.setEnabled(True))
        Foot_PB.clicked.connect(bodyUIName.setEnabled(False))
        RightHand_PB.clicked.connect(bodyUIName.setEnabled(False))
        LeftHand_BP.clicked.connect(bodyUIName.setEnabled(False))





    def getReferencesFiles(self,allNames= []):
        #allNames = cmds.ls(type="joint")
        nameSpaces = set([":".join(i.split(":")[:-1]) for i in allNames])
        nameSpacesList = list(nameSpaces)
        nameSpacesList.sort()
        self.filePrefix_comboBox.clear()
        self.poseFilePrefix_comboBox.clear()
        for name in nameSpacesList:
            self.filePrefix_comboBox.addItem("%s:" % name)
            self.poseFilePrefix_comboBox.addItem("%s:" % name)
    def setValue(self):
        """
        Get weight_VerticalSlider vlaue
        Set to weight_doubleSpinBox vlaue
        """
        value = self.weight_VerticalSlider.value()
        self.weight_doubleSpinBox.setValue(value / 1000.0)


    def setWeightValue(self):
        """
        Get weight_doubleSpinBox vlaue
        Set to weight_VerticalSlider vlaue
        """
        value = self.weight_doubleSpinBox.value()
        self.weight_VerticalSlider.setValue(value * 1000.0)
    def applyConstraintButton(self):
        print "applyConstraintButton..."

    def matchTrButton(self):
        """
        only copy Translation,
        first select A Object,
        second select B Object,
        then A move to B
        """
        ctrls = self.getCtrls()
        targetCtrl, sourceCtrl = ctrls[0], ctrls[1]
        isChecked = self.world_radioButton.isChecked()
        localIsChecked = self.local_radioButton.isChecked()
        if isChecked:
            tr = sourceCtrl.getTranslation(space="world")
            targetCtrl.setTranslation(tr, space="world")
        if localIsChecked:
            tr = sourceCtrl.getTranslation(space="object")
            targetCtrl.setTranslation(tr, space="object")
        # print "matchTrButton..."

    def matchRoButton(self):
        pass
        """only copy Translation,
        first select A Object,
        second select B Object,
        then A Rotate to B
        ctrls = self.getCtrls()
        targetCtrl, sourceCtrl = ctrls[0], ctrls[1]
        isChecked = self.world_radioButton.isChecked()
        localIsChecked = self.local_radioButton.isChecked()
        if isChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=1, ro=1)
            pm.xform(targetCtrl, ws=1, ro=ro)
        if localIsChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=0, ro=1)
            pm.xform(targetCtrl, ws=0, ro=ro)"""

    # print "matchRoButton..."

    def matchTranformsButton(self):
        """copy transforms,
        first select A Object,
        second select B Object,
        then A Rotate to B"""
        ctrls = self.getCtrls()
        targetCtrl, sourceCtrl = ctrls[0], ctrls[1]
        isChecked = self.world_radioButton.isChecked()
        localIsChecked = self.local_radioButton.isChecked()
        if isChecked:
            matrix = sourceCtrl.getMatrix(worldSpace=True)
            targetCtrl.setMatrix(matrix, worldSpace=True)
        if localIsChecked:
            matrix = sourceCtrl.getMatrix(objectSpace=True)
            targetCtrl.setMatrix(matrix, objectSpace=True)

    # aAlign2B()
    # print "matchTranformsButton..."
    def searchAndReplace(self):
        """
        Search and Replace Selected objects name
        """
        selectionNames = self.getCtrls()
        searchText = self.search_lineEdit.text()
        replaceText = self.replace_lineEdit.text()
        for name in selectionNames:
            newName = name.replace(searchText, replaceText)
            name.rename(newName)
        # print "searchAndReplace",searchText,replaceText

    def addPrefix(self):
        """
        Add Prefix Selected objects name
        """
        prefixText = self.prefix_lineEdit.text()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            newName = "%s%s" % (prefixText, name)
            name.rename(newName)
        # print "addPrefix",prefixText

    def addSuffix(self):
        """
        Add Suffix Selected objects name
        """
        suffixText = self.suffix_lineEdit.text()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            newName = "%s%s" % (name, suffixText)
            name.rename(newName)
        # print "addSuffix"

    def renameaddNumber(self):
        """
        Rename Selected objects name
        """
        nameText = self.rename_lineEdit.text()
        startNumber = self.startNum_spinBox.value()
        paddingNumber = self.paddingNum_spinBox.value()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            strName = "%s{:0%dd}" % (nameText, paddingNumber)
            newName = strName.format(startNumber)
            name.rename(newName)
            startNumber += 1
        # print "renameaddNumber"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

"""

import sys,os
from maya import cmds,mel

def onMayaDroppedPythonFile(parm):
	pass
file_Path,fileName = os.path.split(__file__)
paths = sys.path
gShelfTopLevel = mel.eval('$tmpVar=$gShelfTopLevel')
parentName = cmds.tabLayout(gShelfTopLevel,q= 1,selectTab =1)
scriptType = "py"
scriptFile = "animtorsTools"
command = '''import sys,os
from PySide2 import QtWidgets, QtUiTools, QtCore
paths = sys.path
addPath = "{0}"
if addPath not in paths:
    sys.path.append(addPath)
#print "\\n".join(paths)

import animtorsTools
reload(animtorsTools)
app = QtWidgets.QApplication
mainwindow = animtorsTools.MainWindow()
mainwindow.show()
app.exec_()
'''.format(file_Path)
#command = "execfile('{0}/{1}.{2}')".format(file_Path,scriptFile,scriptType)
cmds.shelfButton(c = command  ,image1='pythonFamily.png',sourceType="python",imageOverlayLabel = scriptFile,p = parentName,ann = scriptFile )






"""
