#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os, re, csv
from PySide2 import QtWidgets, QtUiTools, QtCore, QtGui
from maya import cmds, OpenMayaUI
import pymel.core as pm
from shiboken2 import wrapInstance

# standalone.initialize()

# file_Path, fileName = os.path.split(__file__)
file_Path = os.path.dirname(__file__)
# file_Path = "D:\\test\\"
uiName = "constrainWeapon.ui"
uiPath = os.path.join(file_Path, uiName)
weaponListFile = "weapon_list.csv"

mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()
mayaMainWindow = wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)


class AttchWeapon(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(AttchWeapon, self).__init__(*args, **kwargs)
        # self.setParent(mayaMainWindow)
        # self.setWindowFlags( QtCore.Qt.Window )
        self.setupUI()
        # print(getMayaWindow().objectName())

    def setupUI(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath, parentWidget=self)
        self.ui.setParent(mayaMainWindow)
        self.ui.setWindowFlags(QtCore.Qt.Window)

        # self.setWindowTitle("AttchWeapon 1.0")
        self.resetMinmumValue()
        self.setDefaultValue()
        self.editItems()
        self.ui.pushButton_Attch.clicked.connect(self.attachToHand)
        self.ui.comboBox_weaponName.currentTextChanged.connect(self.setDefaultValue)
        self.ui.pushButton_SaveValue.clicked.connect(self.saveValues)
        self.ui.pushButton.clicked.connect(self.selectJoint)
        self.ui.toolBox.currentChanged.connect(self.resetMinmumValue)
        self.ui.pushButton_GetValue.clicked.connect(self.getJointPosition)
        # self.ui.pushButton_Exit.clicked.connect(self.close)

    def getValue(self, spinBoxName):
        return spinBoxName.value()

    def getIeams(self):
        """获取csv内容"""
        with open(os.path.join(file_Path, weaponListFile), "r") as fileName:
            reader = csv.reader(fileName)
            header = next(reader)
            weaponDict = {}
            for row in reader:
                weaponName = row[0]
                values = [float(i) for i in row[1:]]
                weaponDict[weaponName] = values
        return weaponDict

    def editItems(self):
        """将csv内容中的第一列做为武器名称，添加到comboBox中"""
        weaponDict = self.getIeams()
        self.ui.comboBox_weaponName.addItems(weaponDict.keys())

    def setDefaultValue(self):
        """读取csv内容中的第二列到第七列的内容，做为移动旋转值，设置到doubleSpinBox中"""
        weaponName = self.ui.comboBox_weaponName.currentText()
        weaponValue = self.getIeams()
        if weaponName in weaponValue.keys():
            self.ui.doubleSpinBox_TX.setValue(weaponValue[weaponName][0])
            self.ui.doubleSpinBox_TY.setValue(weaponValue[weaponName][1])
            self.ui.doubleSpinBox_TZ.setValue(weaponValue[weaponName][2])
            self.ui.doubleSpinBox_RX.setValue(weaponValue[weaponName][3])
            self.ui.doubleSpinBox_RY.setValue(weaponValue[weaponName][4])
            self.ui.doubleSpinBox_RZ.setValue(weaponValue[weaponName][5])

    def getJointPosition(self):
        try:
            jointName = pm.selected()[0]
            tr = jointName.getTranslation()
            ro = jointName.getRotation()
            self.ui.doubleSpinBox_TX.setValue(tr[0])
            self.ui.doubleSpinBox_TY.setValue(tr[1])
            self.ui.doubleSpinBox_TZ.setValue(tr[2])
            self.ui.doubleSpinBox_RX.setValue(ro[0])
            self.ui.doubleSpinBox_RY.setValue(ro[1])
            self.ui.doubleSpinBox_RZ.setValue(ro[2])
        except Exception as err:
            pm.warning("%s" % err)

    def getWeaponName(self):
        """获取当前comboBox选择的名称"""
        weaponName = self.ui.comboBox_weaponName.currentText()
        return weaponName

    def getValues(self):
        """获取所有doubleSpinBox中的值"""
        value_tx = self.getValue(self.ui.doubleSpinBox_TX)
        value_ty = self.getValue(self.ui.doubleSpinBox_TY)
        value_tz = self.getValue(self.ui.doubleSpinBox_TZ)
        value_rx = self.getValue(self.ui.doubleSpinBox_RX)
        value_ry = self.getValue(self.ui.doubleSpinBox_RY)
        value_rz = self.getValue(self.ui.doubleSpinBox_RZ)
        return value_tx, value_ty, value_tz, value_rx, value_ry, value_rz

    def attachToHand(self):
        """将引用到Maya中的武器Root骨骼约束在对应的手腕武器骨骼上"""
        if self.ui.radioButton_Left.isChecked():
            self.parentConstraintWeapon("BaseBody_LeftHand_MTPA")
        if self.ui.radioButton_Right.isChecked():
            self.parentConstraintWeapon("BaseBody_RightHand_MTPA")

    def parentConstraintWeapon(self, jointName):
        pathName, nameSpace = self.getSourceFile()
        value_tx, value_ty, value_tz, value_rx, value_ry, value_rz = self.getValues()
        jointName = pm.PyNode(jointName)
        jointName.t.set([value_tx, value_ty, value_tz])
        jointName.r.set([value_rx, value_ry, value_rz])
        pm.parentConstraint(jointName, "%s:Root" % (nameSpace), mo=0, w=1)

    def selectJoint(self):
        try:
            if self.ui.radioButton_Left.isChecked():
                jointName_L = pm.PyNode("BaseBody_LeftHand_MTPA")
                pm.select(jointName_L)
            if self.ui.radioButton_Right.isChecked():
                jointName_R = pm.PyNode("BaseBody_RightHand_MTPA")
                pm.select(jointName_R)
        except Exception as err:
            pm.warning("%s" % err)

    def resetMinmumValue(self):
        myUI = self.ui
        tabObjectName = myUI.toolBox.currentWidget()
        # tabObjectName = myUI.tabWidget.currentWidget()
        tabName = tabObjectName.objectName()
        # print(tabName)
        if tabName == "aboutMe":
            self.setMinimumWidth(730)
            self.setMinimumHeight(120)
            myUI.setMinimumWidth(730)
            myUI.setMinimumHeight(120)
            self.resize(QtCore.QSize(730, 120))
            myUI.resize(QtCore.QSize(730, 120))
        if tabName == "attachWeapon":
            self.setMinimumWidth(730)
            self.setMinimumHeight(270)
            self.resize(QtCore.QSize(730, 270))
            myUI.setMinimumWidth(730)
            myUI.setMinimumHeight(270)
            myUI.resize(QtCore.QSize(730, 270))

    def getSourceFile(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        pathName = fileDialog.getOpenFileName(
            self.ui, "Select MayaFile", "",
            "Maya File (*.ma *.mb);;FBX(*.fbx);;All File (*.*)")
        # print pathName
        # self.ui.mayaFile_lineEdit.setText(pathName[0])
        # file -r -type "mayaAscii"  -ignoreVersion -gl -mergeNamespacesOnClash false -namespace "test" -options "v=0;" "F:/Cobra_UE5/Art/Rig/Characters/Ene_Kgb_Rig/test.ma";
        fileName = os.path.split(pathName[0])
        nameSpace = os.path.splitext(fileName[-1])[0]
        refileName = pm.createReference(pathName[0], namespace=nameSpace)
        print(refileName)
        return pathName[0], refileName.namespace

    def repalceContent(self, fileName, content):
        with open(fileName, "r") as file:
            reader = csv.reader(file)
            newContent = [i for i in reader]
            for row in newContent:
                if row[0] == content[0]:
                    index = newContent.index(row)
                    newContent.pop(index)
                    newContent.insert(index, content)
            # newContent = [i for i in reader]
            return newContent

    def saveValues(self):
        weaponDict = self.getIeams()
        weaponName = self.getWeaponName()
        value_tx, value_ty, value_tz, value_rx, value_ry, value_rz = self.getValues()
        content = [weaponName, value_tx, value_ty, value_tz, value_rx, value_ry, value_rz]
        # fileName = self.valuePath()
        csvPath = os.path.join(file_Path, weaponListFile)
        if weaponName not in weaponDict.keys():
            with open(csvPath, "a+") as fileName:
                csv_writer = csv.writer(fileName)
                csv_writer.writerow(content)
                self.ui.comboBox_weaponName.addItem(weaponName)
        else:
            newContent = self.repalceContent(csvPath, content)
            recode = self.msg()
            if recode == QtWidgets.QMessageBox.StandardButton.Yes:
                with open(csvPath, "w") as fileName:
                    csv_writer = csv.writer(fileName)
                    csv_writer.writerows(newContent)

    def msg(self):
        recode = QtWidgets.QMessageBox.question(self, "weapon already exists", "Repalce values...",
                                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                QtWidgets.QMessageBox.Yes)
        return recode


'''
def main():
    ui = AttchWeapon()
    ui.show()
    return ui
'''
if __name__ == "__main__":
    app = QtWidgets.QApplication
    mainwindow = AttchWeapon()
    mainwindow.ui.show()
    # main()
    app.exec_()
    
    
# install.py
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
scriptFile = "attchWeapon"

command = '''import sys,os
from PySide2 import QtWidgets, QtUiTools, QtCore
paths = sys.path
addPath = "{0}"
if addPath not in paths:
    sys.path.append(addPath)
#print "\\n".join(paths)

import attchWeapon
reload(attchWeapon)
app = QtWidgets.QApplication
mainwindow = attchWeapon.AttchWeapon()
mainwindow.ui.show()
app.exec_()
'''.format(file_Path)
#command = "execfile('{0}/{1}.{2}')".format(file_Path,scriptFile,scriptType)
cmds.shelfButton(c = command  ,image1='pythonFamily.png',sourceType="python",imageOverlayLabel = scriptFile,p = parentName,ann = scriptFile )


"""
    
 ##UiFile
'''
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>AttchWeapon</class>
 <widget class="QWidget" name="AttchWeapon">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>735</width>
    <height>265</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>AttchWeapon 2.0</string>
  </property>
  <layout class="QGridLayout" name="gridLayout">
   <property name="leftMargin">
    <number>2</number>
   </property>
   <property name="topMargin">
    <number>2</number>
   </property>
   <property name="rightMargin">
    <number>2</number>
   </property>
   <property name="bottomMargin">
    <number>2</number>
   </property>
   <property name="spacing">
    <number>0</number>
   </property>
   <item row="2" column="0">
    <widget class="QPushButton" name="pushButton_Exit">
     <property name="minimumSize">
      <size>
       <width>0</width>
       <height>30</height>
      </size>
     </property>
     <property name="styleSheet">
      <string notr="true">QPushButton{
background-color: rgba(45,45,45,100);
border-style: outset;
border-width: 0px;
border-radius: 10px;
border-color: red;
}
QPushButton:hover{
background-color:rgba(0,0,200,60); 
color: black;}
QPushButton:checked{
background-color: rgba(0,255, 0 ,200);
border-style: inset; }</string>
     </property>
     <property name="text">
      <string>Exit</string>
     </property>
    </widget>
   </item>
   <item row="0" column="0">
    <widget class="QToolBox" name="toolBox">
     <property name="minimumSize">
      <size>
       <width>710</width>
       <height>0</height>
      </size>
     </property>
     <property name="frameShape">
      <enum>QFrame::NoFrame</enum>
     </property>
     <property name="currentIndex">
      <number>0</number>
     </property>
     <property name="tabSpacing">
      <number>0</number>
     </property>
     <widget class="QWidget" name="attachWeapon">
      <property name="geometry">
       <rect>
        <x>0</x>
        <y>0</y>
        <width>731</width>
        <height>183</height>
       </rect>
      </property>
      <attribute name="label">
       <string>Attach Weapon</string>
      </attribute>
      <layout class="QGridLayout" name="gridLayout_5">
       <property name="leftMargin">
        <number>0</number>
       </property>
       <property name="topMargin">
        <number>0</number>
       </property>
       <property name="rightMargin">
        <number>0</number>
       </property>
       <property name="bottomMargin">
        <number>0</number>
       </property>
       <property name="spacing">
        <number>0</number>
       </property>
       <item row="1" column="0">
        <widget class="Line" name="line">
         <property name="orientation">
          <enum>Qt::Horizontal</enum>
         </property>
        </widget>
       </item>
       <item row="2" column="0">
        <widget class="QPushButton" name="pushButton_Attch">
         <property name="minimumSize">
          <size>
           <width>0</width>
           <height>30</height>
          </size>
         </property>
         <property name="styleSheet">
          <string notr="true">QPushButton{
background-color: rgba(45,45,45,100);
border-style: outset;
border-width: 0px;
border-radius: 10px;
border-color: red;
}
QPushButton:hover{
background-color:rgba(0,0,200,60); 
color: black;}
QPushButton:checked{
background-color: rgba(0,255, 0 ,200);
border-style: inset; }</string>
         </property>
         <property name="text">
          <string>Attch To Hand</string>
         </property>
        </widget>
       </item>
       <item row="0" column="0">
        <layout class="QGridLayout" name="gridLayout_3">
         <property name="spacing">
          <number>2</number>
         </property>
         <item row="2" column="0">
          <layout class="QGridLayout" name="gridLayout_2">
           <property name="spacing">
            <number>2</number>
           </property>
           <item row="0" column="0" rowspan="3">
            <widget class="QLabel" name="label_8">
             <property name="text">
              <string/>
             </property>
            </widget>
           </item>
           <item row="2" column="4">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_RX">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="0" column="8" rowspan="3">
            <widget class="QLabel" name="label_7">
             <property name="text">
              <string/>
             </property>
            </widget>
           </item>
           <item row="0" column="5">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_TY">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="2" column="6">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_RZ">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="2" column="5">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_RY">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="baseSize">
              <size>
               <width>120</width>
               <height>0</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="0" column="4">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_TX">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="0" column="3">
            <widget class="QLabel" name="label">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="layoutDirection">
              <enum>Qt::RightToLeft</enum>
             </property>
             <property name="text">
              <string>Translate：</string>
             </property>
             <property name="alignment">
              <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
             </property>
             <property name="wordWrap">
              <bool>true</bool>
             </property>
             <property name="indent">
              <number>0</number>
             </property>
            </widget>
           </item>
           <item row="0" column="1" rowspan="3">
            <widget class="QLabel" name="label_3">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="font">
              <font>
               <pointsize>12</pointsize>
              </font>
             </property>
             <property name="styleSheet">
              <string notr="true">QLabel{

backgroud color rgba(0, 0, 255,0)

}</string>
             </property>
             <property name="text">
              <string>Weapon:</string>
             </property>
             <property name="alignment">
              <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
             </property>
            </widget>
           </item>
           <item row="2" column="3">
            <widget class="QLabel" name="label_2">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="layoutDirection">
              <enum>Qt::RightToLeft</enum>
             </property>
             <property name="text">
              <string>Rotate：</string>
             </property>
             <property name="alignment">
              <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
             </property>
             <property name="indent">
              <number>0</number>
             </property>
            </widget>
           </item>
           <item row="0" column="6">
            <widget class="QDoubleSpinBox" name="doubleSpinBox_TZ">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="alignment">
              <set>Qt::AlignCenter</set>
             </property>
             <property name="buttonSymbols">
              <enum>QAbstractSpinBox::NoButtons</enum>
             </property>
             <property name="specialValueText">
              <string/>
             </property>
             <property name="decimals">
              <number>3</number>
             </property>
             <property name="minimum">
              <double>-100000000000000005366162204393472.000000000000000</double>
             </property>
             <property name="maximum">
              <double>9999999999999999932209486743616279764617084419440640.000000000000000</double>
             </property>
            </widget>
           </item>
           <item row="0" column="2" rowspan="3">
            <widget class="QComboBox" name="comboBox_weaponName">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="font">
              <font>
               <pointsize>12</pointsize>
              </font>
             </property>
             <property name="layoutDirection">
              <enum>Qt::LeftToRight</enum>
             </property>
             <property name="styleSheet">
              <string notr="true">QComboBox{
bakegroud-color:rgba(0,0,255,0);
}</string>
             </property>
             <property name="editable">
              <bool>true</bool>
             </property>
             <property name="duplicatesEnabled">
              <bool>false</bool>
             </property>
            </widget>
           </item>
           <item row="0" column="7">
            <widget class="QPushButton" name="pushButton_SaveValue">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>20</height>
              </size>
             </property>
             <property name="toolTip">
              <string>将数值保存至文本文档中
Save values to text document</string>
             </property>
             <property name="styleSheet">
              <string notr="true">QPushButton{
background-color: rgba(45,45,45,100);
border-style: outset;
border-width: 0px;
border-radius: 5px;
border-color: red;
}
QPushButton:hover{
background-color:rgba(0,0,200,60); 
color: black;}
QPushButton:checked{
background-color: rgba(0,255, 0 ,200);
border-style: inset; }</string>
             </property>
             <property name="text">
              <string>SaveValues</string>
             </property>
            </widget>
           </item>
           <item row="2" column="7">
            <widget class="QPushButton" name="pushButton_GetValue">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>20</height>
              </size>
             </property>
             <property name="styleSheet">
              <string notr="true">QPushButton{
background-color: rgba(45,45,45,100);
border-style: outset;
border-width: 0px;
border-radius: 5px;
border-color: red;
}
QPushButton:hover{
background-color:rgba(0,0,200,60); 
color: black;}
QPushButton:checked{
background-color: rgba(0,255, 0 ,200);
border-style: inset; }</string>
             </property>
             <property name="text">
              <string>GetValues</string>
             </property>
            </widget>
           </item>
           <item row="1" column="3" colspan="5">
            <widget class="Line" name="line_4">
             <property name="orientation">
              <enum>Qt::Horizontal</enum>
             </property>
            </widget>
           </item>
          </layout>
         </item>
         <item row="0" column="0">
          <layout class="QGridLayout" name="gridLayout_4">
           <property name="leftMargin">
            <number>1</number>
           </property>
           <property name="topMargin">
            <number>1</number>
           </property>
           <property name="rightMargin">
            <number>1</number>
           </property>
           <property name="bottomMargin">
            <number>1</number>
           </property>
           <property name="horizontalSpacing">
            <number>1</number>
           </property>
           <property name="verticalSpacing">
            <number>0</number>
           </property>
           <item row="0" column="3">
            <widget class="QPushButton" name="pushButton">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="toolTip">
              <string>选择相对应的骨骼
Select the corresponding bone</string>
             </property>
             <property name="styleSheet">
              <string notr="true">QPushButton{
background-color: rgba(45,45,45,100);
border-style: outset;
border-width: 0px;
border-radius: 10px;
border-color: red;
}
QPushButton:hover{
background-color:rgba(0,0,200,60); 
color: black;}
QPushButton:checked{
background-color: rgba(0,255, 0 ,200);
border-style: inset; }

</string>
             </property>
             <property name="text">
              <string>&lt;&lt;&lt;Select Bone&gt;&gt;&gt;</string>
             </property>
            </widget>
           </item>
           <item row="0" column="6">
            <widget class="QLabel" name="label_5">
             <property name="text">
              <string/>
             </property>
            </widget>
           </item>
           <item row="0" column="0">
            <widget class="QLabel" name="label_4">
             <property name="text">
              <string/>
             </property>
            </widget>
           </item>
           <item row="0" column="4">
            <widget class="QRadioButton" name="radioButton_Left">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="font">
              <font>
               <weight>75</weight>
               <bold>true</bold>
              </font>
             </property>
             <property name="layoutDirection">
              <enum>Qt::RightToLeft</enum>
             </property>
             <property name="text">
              <string>Left Hand</string>
             </property>
            </widget>
           </item>
           <item row="0" column="1">
            <widget class="QRadioButton" name="radioButton_Right">
             <property name="minimumSize">
              <size>
               <width>0</width>
               <height>30</height>
              </size>
             </property>
             <property name="font">
              <font>
               <weight>75</weight>
               <bold>true</bold>
              </font>
             </property>
             <property name="layoutDirection">
              <enum>Qt::LeftToRight</enum>
             </property>
             <property name="text">
              <string>Right Hand</string>
             </property>
             <property name="checked">
              <bool>true</bool>
             </property>
            </widget>
           </item>
          </layout>
         </item>
         <item row="1" column="0">
          <widget class="Line" name="line_3">
           <property name="orientation">
            <enum>Qt::Horizontal</enum>
           </property>
          </widget>
         </item>
        </layout>
       </item>
       <item row="3" column="0">
        <widget class="QLabel" name="label_6">
         <property name="maximumSize">
          <size>
           <width>16777215</width>
           <height>2</height>
          </size>
         </property>
         <property name="text">
          <string/>
         </property>
        </widget>
       </item>
      </layout>
     </widget>
     <widget class="QWidget" name="aboutMe">
      <property name="geometry">
       <rect>
        <x>0</x>
        <y>0</y>
        <width>731</width>
        <height>183</height>
       </rect>
      </property>
      <attribute name="label">
       <string>About Me</string>
      </attribute>
      <layout class="QGridLayout" name="gridLayout_6">
       <property name="leftMargin">
        <number>0</number>
       </property>
       <property name="topMargin">
        <number>0</number>
       </property>
       <property name="rightMargin">
        <number>0</number>
       </property>
       <property name="bottomMargin">
        <number>0</number>
       </property>
       <property name="spacing">
        <number>0</number>
       </property>
       <item row="0" column="0">
        <widget class="QLabel" name="label_9">
         <property name="minimumSize">
          <size>
           <width>0</width>
           <height>35</height>
          </size>
         </property>
         <property name="styleSheet">
          <string notr="true">background-color:rgb(134, 110, 255);
color: rgb(0, 0, 0);</string>
         </property>
         <property name="text">
          <string>Please contact me if you have any questions!
QQ&amp;&amp;WeChat: 370871841</string>
         </property>
         <property name="alignment">
          <set>Qt::AlignCenter</set>
         </property>
        </widget>
       </item>
      </layout>
     </widget>
    </widget>
   </item>
   <item row="1" column="0">
    <widget class="Line" name="line_2">
     <property name="orientation">
      <enum>Qt::Horizontal</enum>
     </property>
    </widget>
   </item>
   <item row="3" column="0">
    <widget class="Line" name="line_5">
     <property name="orientation">
      <enum>Qt::Horizontal</enum>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <tabstops>
  <tabstop>radioButton_Right</tabstop>
  <tabstop>pushButton</tabstop>
  <tabstop>radioButton_Left</tabstop>
  <tabstop>comboBox_weaponName</tabstop>
  <tabstop>doubleSpinBox_TX</tabstop>
  <tabstop>doubleSpinBox_TY</tabstop>
  <tabstop>doubleSpinBox_TZ</tabstop>
  <tabstop>doubleSpinBox_RX</tabstop>
  <tabstop>doubleSpinBox_RY</tabstop>
  <tabstop>doubleSpinBox_RZ</tabstop>
  <tabstop>pushButton_Attch</tabstop>
  <tabstop>pushButton_Exit</tabstop>
  <tabstop>toolBox</tabstop>
 </tabstops>
 <resources/>
 <connections>
  <connection>
   <sender>pushButton_Exit</sender>
   <signal>clicked()</signal>
   <receiver>AttchWeapon</receiver>
   <slot>close()</slot>
   <hints>
    <hint type="sourcelabel">
     <x>446</x>
     <y>259</y>
    </hint>
    <hint type="destinationlabel">
     <x>441</x>
     <y>347</y>
    </hint>
   </hints>
  </connection>
 </connections>
</ui>



'''
    
