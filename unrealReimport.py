#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os,unreal
from PySide2 import QtWidgets, QtUiTools, QtCore
from QtUtil import qt_util


file_Path, fileName = os.path.split(__file__)
# path = '//Cnshasgamefsv1/MGS3/Users/WangJinge/Scripts/test'
uiName = "reimportFBX.ui"
uiPath = os.path.join(file_Path, uiName)


class ReimportSourceFiles(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ReimportSourceFiles, self).__init__(parent)
        self.setupUI()

    def setupUI(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath)
        uiName = self.ui
        uiName.loadFile_pushButton.clicked.connect(self.getAllFBXFiles)
        uiName.getAssets_pushButton.clicked.connect(self.getAnimationAssets)

    def getAllFBXFiles(self):
        fileDialog = QtWidgets.QFileDialog(self.ui)
        pathName = fileDialog.getExistingDirectory(self.ui, "Export Files")
        self.ui.fbxFile_lineEdit.setText(pathName)
        fbxFiles = [i for i in os.listdir(pathName) if os.path.splitext(i)[-1] == ".fbx"]
        self.ui.listWidget_FBX.clear()
        self.ui.listWidget_FBX.addItems(fbxFiles)

    def getAnimationAssets(self):
        #directory = unreal.Paths.get_path(self.ui.assets_lineEdit.text())
        assets = unreal.EditorAssetLibrary.list_assets(self.ui.assets_lineEdit.text())
        print(self.ui.assets_lineEdit.text())
        self.ui.listWidget_Asset.clear()
        self.ui.listWidget_Asset.addItems(assets)


#unreal.Paths.get_path("/Game/ZVMinus1Anims/AnimSequences")

if __name__ == "__main__":
    app = qt_util.create_qt_application()
    mainwindow = ReimportSourceFiles()
    mainwindow.ui.show()
    unreal.parent_external_window_to_slate(mainwindow.ui.winId())
"""
###   UI
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form_reimport</class>
 <widget class="QWidget" name="Form_reimport">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>508</width>
    <height>578</height>
   </rect>
  </property>
  <property name="minimumSize">
   <size>
    <width>450</width>
    <height>320</height>
   </size>
  </property>
  <property name="windowTitle">
   <string>ReImport</string>
  </property>
  <layout class="QGridLayout" name="gridLayout_3">
   <item row="0" column="0">
    <layout class="QGridLayout" name="gridLayout_2">
     <item row="0" column="0">
      <widget class="QLabel" name="label_FBX">
       <property name="minimumSize">
        <size>
         <width>110</width>
         <height>30</height>
        </size>
       </property>
       <property name="font">
        <font>
         <pointsize>12</pointsize>
        </font>
       </property>
       <property name="toolTip">
        <string>Select the completed retarget maya file</string>
       </property>
       <property name="text">
        <string>FBX Files Path:</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignLeading|Qt::AlignLeft|Qt::AlignVCenter</set>
       </property>
       <property name="indent">
        <number>5</number>
       </property>
      </widget>
     </item>
     <item row="0" column="1">
      <widget class="QLineEdit" name="fbxFile_lineEdit">
       <property name="minimumSize">
        <size>
         <width>240</width>
         <height>30</height>
        </size>
       </property>
       <property name="baseSize">
        <size>
         <width>0</width>
         <height>298</height>
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
        <string>FBX Files Path</string>
       </property>
      </widget>
     </item>
     <item row="0" column="2">
      <widget class="QPushButton" name="loadFile_pushButton">
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
       <property name="toolTip">
        <string>Select the completed retarget maya file</string>
       </property>
       <property name="text">
        <string>&lt;&lt;&lt;</string>
       </property>
      </widget>
     </item>
     <item row="1" column="0">
      <widget class="QLabel" name="label_Assets">
       <property name="minimumSize">
        <size>
         <width>110</width>
         <height>30</height>
        </size>
       </property>
       <property name="font">
        <font>
         <pointsize>12</pointsize>
        </font>
       </property>
       <property name="toolTip">
        <string>Select the completed retarget maya file</string>
       </property>
       <property name="text">
        <string>Assets  Path:</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignCenter</set>
       </property>
       <property name="indent">
        <number>5</number>
       </property>
      </widget>
     </item>
     <item row="1" column="1">
      <widget class="QLineEdit" name="assets_lineEdit">
       <property name="minimumSize">
        <size>
         <width>240</width>
         <height>30</height>
        </size>
       </property>
       <property name="baseSize">
        <size>
         <width>0</width>
         <height>298</height>
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
        <string>Asset Files Path</string>
       </property>
      </widget>
     </item>
     <item row="1" column="2">
      <widget class="QPushButton" name="getAssets_pushButton">
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
       <property name="toolTip">
        <string>Select the completed retarget maya file</string>
       </property>
       <property name="text">
        <string>GetAssets</string>
       </property>
      </widget>
     </item>
    </layout>
   </item>
   <item row="1" column="0">
    <layout class="QGridLayout" name="gridLayout">
     <item row="1" column="2">
      <widget class="QListWidget" name="listWidget_FBX">
       <property name="styleSheet">
        <string notr="true">background-color:rgb(100, 100,100);\ncolor: rgb(0, 0, 0);</string>
       </property>
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
     <item row="1" column="0">
      <widget class="QListWidget" name="listWidget_Asset">
       <property name="styleSheet">
        <string notr="true">background-color:rgb(100, 100,100);\ncolor: rgb(0, 0, 0);</string>
       </property>
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
     <item row="0" column="2">
      <widget class="QLabel" name="label_fbx">
       <property name="font">
        <font>
         <pointsize>12</pointsize>
         <weight>50</weight>
         <bold>false</bold>
        </font>
       </property>
       <property name="layoutDirection">
        <enum>Qt::LeftToRight</enum>
       </property>
       <property name="text">
        <string>FBX Files List</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignCenter</set>
       </property>
      </widget>
     </item>
     <item row="0" column="0">
      <widget class="QLabel" name="label_assets">
       <property name="font">
        <font>
         <pointsize>12</pointsize>
         <weight>50</weight>
         <bold>false</bold>
        </font>
       </property>
       <property name="layoutDirection">
        <enum>Qt::LeftToRight</enum>
       </property>
       <property name="text">
        <string>Asset Files List</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignCenter</set>
       </property>
      </widget>
     </item>
     <item row="2" column="0" colspan="3">
      <widget class="QPushButton" name="pushButton_apply">
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
       <property name="text">
        <string>Reimport Selected</string>
       </property>
      </widget>
     </item>
     <item row="3" column="0" colspan="3">
      <widget class="QPushButton" name="pushButton_exit">
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
       <property name="text">
        <string>Qiut</string>
       </property>
      </widget>
     </item>
     <item row="4" column="0" colspan="3">
      <widget class="QLabel" name="label_aboutme">
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
     <item row="1" column="1">
      <widget class="Line" name="line">
       <property name="orientation">
        <enum>Qt::Vertical</enum>
       </property>
      </widget>
     </item>
    </layout>
   </item>
  </layout>
 </widget>
 <resources/>
 <connections>
  <connection>
   <sender>pushButton_exit</sender>
   <signal>clicked()</signal>
   <receiver>Form_reimport</receiver>
   <slot>close()</slot>
   <hints>
    <hint type="sourcelabel">
     <x>238</x>
     <y>254</y>
    </hint>
    <hint type="destinationlabel">
     <x>239</x>
     <y>-23</y>
    </hint>
   </hints>
  </connection>
 </connections>
</ui>


"""
