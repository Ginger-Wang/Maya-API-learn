#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os
from PySide2 import QtWidgets, QtUiTools, QtCore
from maya import cmds,standalone,mel
#import pymel.core as pm
#standalone.initialize()

file_Path, fileName = os.path.split(__file__)

uiName = "AutoRetargetTool.ui"
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


    def setRetarget(self):
        mel.eval('hikSetCharacterInput("Mocap","Character1");')
    #设置HumanIK Source : None
    def disconnectRetarget(self):
        mel.eval('hikSetInactiveStanceInput("Mocap");')
        if cmds.objExists("Root_MoCap_M"):
            rootName ="Root_MoCap_M"
        elif cmds.objExists("AsRoot_MoCap_M"):
            rootName ="AsRoot_MoCap_M"
        cmds.setAttr("%s.t"%rootName,0,0,0,type = "double3")
        cmds.joint(rootName,e= 1,apa = 1,ch =1)
        
    def getParent(self,node):
        parentName = cmds.listRelatives(node,p = 1)[0]
        return parentName

    def bakeAnim(self):
        allFKCtrlShapes = pm.ls("FK*",type = "nurbsCurve")
        if cmds.objExists("RootX_M"):
            rootxName = pm.PyNode("RootX_M")
        elif cmds.objExists("AsRootX_M"):
            rootxName = pm.PyNode("AsRootX_M")            
        rootxGrpName = rootxName.getParent()
        tr = rootxGrpName.getTranslation()
        allFKCtrls = [i.getParent() for i in allFKCtrlShapes if "IK" not in str(i)]
        allParentCtrls =  [i.getParent() for i in allFKCtrls]
        parentRotation = [i.getRotation() for i in allParentCtrls]
        for ctrl,rotation in zip(allFKCtrls,parentRotation):
            ctrl.setRotation(rotation)
            pm.setKeyframe(ctrl,at = "rotate")
            #print ctrl,rotation
        rootxName.setTranslation(tr)
        pm.setKeyframe(rootxName,at = "translate")
        
    def runExport(self):        
        standalone.initialize()
        cmds.loadPlugin("fbxmaya.mll")
        cmds.loadPlugin("mayaHIK.mll")
        cmds.loadPlugin("mayaCharacterization.mll")
        cmds.loadPlugin("OneClick.mll")
        pathName = self.ui.lineEdit.text()
        fileNames = self.ui.listWidget.selectedItems()
        mayaFileName = self.ui.mayaFile_lineEdit.text()
        #F:/Maya_Project/snake/000normal_idle.fbx
        
        mayaFilesPath = "%s/MayaFiles"%(pathName)
        fbxFilesPath = "%s/FBXFiles"%(pathName)
        if not os.path.isdir(mayaFilesPath):
            os.mkdir(mayaFilesPath)
        if not os.path.isdir(fbxFilesPath):
            os.mkdir(fbxFilesPath)
        
        for name in fileNames:
            cmds.file(mayaFileName,o = True,f = True)
            #print pm.ls(type = "nurbsCurve")
            fbxFileName = name.text()
            fbxFilePath = os.path.join(pathName,fbxFileName)
            #print(fbxFilePath.replace("\\","/"))
            cmds.file(fbxFilePath,i = True)
            cmds.refresh()
            cmds.currentUnit( time='60fps' )
            maxTime,minTime = self.getTimes()
            cmds.playbackOptions(ast = minTime,aet = maxTime,max = maxTime,min = minTime)
            for num in range(int(minTime),int(maxTime+1)):
                cmds.currentTime(num)
                self.bakeAnim()
            self.disconnectRetarget() 
            
            mayaFullPath = os.path.join(mayaFilesPath, fbxFileName.replace(".fbx", ".ma"))
            fbxFullPath = os.path.join(fbxFilesPath, fbxFileName)
            cmds.file(rename=mayaFullPath)
            cmds.file(save=True, type='mayaAscii')
            allJoints = cmds.listRelatives("|Root",ad = 1,type = "joint")
            cmds.select("|Root",allJoints)
            cmds.bakeResults(cmds.ls(sl = 1),t = (minTime,maxTime),simulation = 1,sb = 1)
            cmds.file(fbxFullPath,typ = "FBX export",force = 1,options = "v=0;",pr = 1,es = 1)
            #
            #print( "\n".join(allJoints))
            cmds.file(new = 1, f = 1)
            print "Save as file %s  finshed..."%(mayaFullPath)
        print "Save as files  finshed..."
    def getTimes(self):
        uAnimcurveTpyes = ['animCurveUL','animCurveUA','animCurveUT','animCurveUU']
        anis = cmds.ls(type = 'animCurve')
        maxTime = max([cmds.keyframe(i,q = 1)[-1] for i in anis if cmds.nodeType(i) not in uAnimcurveTpyes])
        minTime = min([cmds.keyframe(i,q = 1)[0] for i in anis if cmds.nodeType(i) not in uAnimcurveTpyes])
        return maxTime,minTime

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = ExportFiles()
    mainwindow.ui.show()
    sys.exit(app.exec_())


'''

echo start
cd %cd%
call "C:/Program Files/Autodesk/Maya2018/bin/mayapy.exe" AutoRetargetTool.py
pause

'''

"""
#UI

<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>430</width>
    <height>390</height>
   </rect>
  </property>
  <property name="minimumSize">
   <size>
    <width>430</width>
    <height>390</height>
   </size>
  </property>
  <property name="font">
   <font>
    <pointsize>10</pointsize>
    <weight>75</weight>
    <bold>true</bold>
   </font>
  </property>
  <property name="windowTitle">
   <string>Auto Retarget</string>
  </property>
  <widget class="QWidget" name="centralwidget">
   <layout class="QGridLayout" name="gridLayout_4">
    <item row="0" column="0">
     <layout class="QGridLayout" name="gridLayout_3">
      <item row="1" column="0">
       <layout class="QGridLayout" name="gridLayout">
        <item row="1" column="2">
         <widget class="QPushButton" name="pushButton">
          <property name="toolTip">
           <string>Select the folder where the FBX files are stored</string>
          </property>
          <property name="text">
           <string>&lt;&lt;&lt;</string>
          </property>
         </widget>
        </item>
        <item row="1" column="0">
         <widget class="QLabel" name="label">
          <property name="minimumSize">
           <size>
            <width>0</width>
            <height>30</height>
           </size>
          </property>
          <property name="toolTip">
           <string>Select the folder where the FBX files are stored</string>
          </property>
          <property name="text">
           <string>FBX Files Folder:</string>
          </property>
          <property name="alignment">
           <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
          </property>
          <property name="indent">
           <number>5</number>
          </property>
         </widget>
        </item>
        <item row="0" column="0">
         <widget class="QLabel" name="label_3">
          <property name="minimumSize">
           <size>
            <width>0</width>
            <height>30</height>
           </size>
          </property>
          <property name="toolTip">
           <string>Select the completed retarget maya file</string>
          </property>
          <property name="text">
           <string>Retarget Maya File:</string>
          </property>
          <property name="alignment">
           <set>Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter</set>
          </property>
          <property name="indent">
           <number>5</number>
          </property>
         </widget>
        </item>
        <item row="0" column="2">
         <widget class="QPushButton" name="loadFile_pushButton">
          <property name="toolTip">
           <string>Select the completed retarget maya file</string>
          </property>
          <property name="text">
           <string>&lt;&lt;&lt;</string>
          </property>
         </widget>
        </item>
        <item row="1" column="1">
         <widget class="QLineEdit" name="lineEdit">
          <property name="minimumSize">
           <size>
            <width>0</width>
            <height>30</height>
           </size>
          </property>
          <property name="font">
           <font>
            <pointsize>12</pointsize>
            <weight>50</weight>
            <bold>false</bold>
           </font>
          </property>
          <property name="toolTip">
           <string>Select the folder where the FBX files are stored</string>
          </property>
          <property name="layoutDirection">
           <enum>Qt::LeftToRight</enum>
          </property>
          <property name="alignment">
           <set>Qt::AlignLeading|Qt::AlignLeft|Qt::AlignVCenter</set>
          </property>
          <property name="placeholderText">
           <string>path</string>
          </property>
         </widget>
        </item>
        <item row="0" column="1">
         <widget class="QLineEdit" name="mayaFile_lineEdit">
          <property name="minimumSize">
           <size>
            <width>0</width>
            <height>30</height>
           </size>
          </property>
          <property name="font">
           <font>
            <pointsize>12</pointsize>
            <weight>50</weight>
            <bold>false</bold>
           </font>
          </property>
          <property name="toolTip">
           <string>Select the completed retarget maya file</string>
          </property>
          <property name="layoutDirection">
           <enum>Qt::LeftToRight</enum>
          </property>
          <property name="alignment">
           <set>Qt::AlignLeading|Qt::AlignLeft|Qt::AlignVCenter</set>
          </property>
          <property name="placeholderText">
           <string>Maya File</string>
          </property>
         </widget>
        </item>
       </layout>
      </item>
      <item row="5" column="0">
       <widget class="QPushButton" name="pushButton_2">
        <property name="minimumSize">
         <size>
          <width>0</width>
          <height>35</height>
         </size>
        </property>
        <property name="text">
         <string>Qiut</string>
        </property>
       </widget>
      </item>
      <item row="4" column="0">
       <widget class="QPushButton" name="export_pushButton">
        <property name="minimumSize">
         <size>
          <width>0</width>
          <height>30</height>
         </size>
        </property>
        <property name="text">
         <string>Export FBX Files By Retarget File</string>
        </property>
       </widget>
      </item>
      <item row="0" column="0">
       <widget class="Line" name="line">
        <property name="orientation">
         <enum>Qt::Horizontal</enum>
        </property>
       </widget>
      </item>
      <item row="2" column="0">
       <widget class="Line" name="line_2">
        <property name="orientation">
         <enum>Qt::Horizontal</enum>
        </property>
       </widget>
      </item>
      <item row="3" column="0">
       <widget class="QListWidget" name="listWidget">
        <property name="selectionMode">
         <enum>QAbstractItemView::ExtendedSelection</enum>
        </property>
        <property name="selectionRectVisible">
         <bool>false</bool>
        </property>
        <property name="sortingEnabled">
         <bool>false</bool>
        </property>
       </widget>
      </item>
      <item row="6" column="0">
       <widget class="QLabel" name="label_4">
        <property name="minimumSize">
         <size>
          <width>0</width>
          <height>35</height>
         </size>
        </property>
        <property name="font">
         <font>
          <weight>75</weight>
          <bold>true</bold>
         </font>
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
    </item>
   </layout>
  </widget>
  <widget class="QMenuBar" name="menubar">
   <property name="geometry">
    <rect>
     <x>0</x>
     <y>0</y>
     <width>430</width>
     <height>23</height>
    </rect>
   </property>
  </widget>
  <widget class="QStatusBar" name="statusbar"/>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>pushButton_2</sender>
   <signal>clicked()</signal>
   <receiver>MainWindow</receiver>
   <slot>close()</slot>
   <hints>
    <hint type="sourcelabel">
     <x>260</x>
     <y>282</y>
    </hint>
    <hint type="destinationlabel">
     <x>243</x>
     <y>30</y>
    </hint>
   </hints>
  </connection>
 </connections>
</ui>



"""


