#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys, os, re, csv
from PySide2 import QtWidgets, QtUiTools, QtCore, QtGui
"""
### 搜索关键字，添加到列表中
"""

file_Path = "D:\\test\\"
uiName = "AAA.ui"
uiPath = os.path.join(file_Path, uiName)
iteamsStr = """teststr\nteststr1\nteststr2\nteststr3\nteststr4\nteststr5\nteststr6\nteststr7\n"""
iteams = iteamsStr.split("\n")

class TestSearch(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(TestSearch, self).__init__(*args, **kwargs)
        self.setupUI()
    def setupUI(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(uiPath)
        self.ui.setWindowFlags(QtCore.Qt.Window)
        self.addIteams()
        self.addText()
        self.ui.pushButton_addIteams.clicked.connect(self.addIteamsList)
        self.ui.lineEdit.textChanged.connect(self.addIteams)
        self.ui.pushButton_toDo.clicked.connect(self.dolistWidget)
        self.ui.pushButton_A.clicked.connect(self.dolistWidget_A)
    def addIteams(self):
        """搜索关键字，匹配到的关键字的项目显示在列表中，没有输入关键字显示所有的列表"""
        self.ui.listWidget_A.clear()
        seacrhContent = self.ui.lineEdit.text()
        if seacrhContent:
            labels = [i for i in iteams if seacrhContent in i]
            self.ui.listWidget_A.addItems(labels)
        else:
            self.ui.listWidget_A.addItems(iteams)
    def showsearchIteams(self,listWidget):
        listIteams = listWidget.selectedItems()
        for iteam in listIteams:
            print(iteam.text())
    def dolistWidget(self):
        self.showsearchIteams(self.ui.listWidget)
    def dolistWidget_A(self):
        self.showsearchIteams(self.ui.listWidget_A)
    def addIteamsList(self):
        """文本中存在的名称，添加到列表中"""
        textContent = self.ui.textEdit.toPlainText()
        listIteams = textContent.split("\n")
        newIteams = [i for i in listIteams if i in iteams]
        self.ui.listWidget.clear()
        self.ui.listWidget.addItems(newIteams)

    def addText(self):
        self.ui.textEdit.setText("""teststr\nteststr1\nteststr2\nteststr3\nteststr4\nteststr5\nteststr6\nteststr7\n""")
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = TestSearch()
    mainwindow.ui.show()
    sys.exit(app.exec_())

#### ui file "AAA.ui"

"""
<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>684</width>
    <height>417</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>Form</string>
  </property>
  <layout class="QGridLayout" name="gridLayout_3">
   <item row="3" column="0">
    <widget class="QPushButton" name="pushButton">
     <property name="text">
      <string>Exit</string>
     </property>
    </widget>
   </item>
   <item row="0" column="0">
    <layout class="QGridLayout" name="gridLayout">
     <item row="1" column="0">
      <widget class="QListWidget" name="listWidget_A">
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
     <item row="0" column="0">
      <widget class="QLineEdit" name="lineEdit">
       <property name="minimumSize">
        <size>
         <width>0</width>
         <height>35</height>
        </size>
       </property>
      </widget>
     </item>
     <item row="2" column="0">
      <widget class="QPushButton" name="pushButton_A">
       <property name="minimumSize">
        <size>
         <width>0</width>
         <height>35</height>
        </size>
       </property>
       <property name="text">
        <string>PushButton</string>
       </property>
      </widget>
     </item>
    </layout>
   </item>
   <item row="2" column="0">
    <layout class="QGridLayout" name="gridLayout_2">
     <item row="1" column="1">
      <widget class="QPushButton" name="pushButton_toDo">
       <property name="minimumSize">
        <size>
         <width>0</width>
         <height>35</height>
        </size>
       </property>
       <property name="text">
        <string>PushButton</string>
       </property>
      </widget>
     </item>
     <item row="0" column="0">
      <widget class="QTextEdit" name="textEdit"/>
     </item>
     <item row="0" column="1">
      <widget class="QListWidget" name="listWidget">
       <property name="dragEnabled">
        <bool>false</bool>
       </property>
       <property name="selectionMode">
        <enum>QAbstractItemView::ExtendedSelection</enum>
       </property>
      </widget>
     </item>
     <item row="1" column="0">
      <widget class="QPushButton" name="pushButton_addIteams">
       <property name="minimumSize">
        <size>
         <width>0</width>
         <height>35</height>
        </size>
       </property>
       <property name="text">
        <string>&gt;&gt;&gt;&gt;</string>
       </property>
      </widget>
     </item>
    </layout>
   </item>
   <item row="4" column="0">
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
 <resources/>
 <connections>
  <connection>
   <sender>pushButton</sender>
   <signal>clicked()</signal>
   <receiver>Form</receiver>
   <slot>close()</slot>
   <hints>
    <hint type="sourcelabel">
     <x>270</x>
     <y>309</y>
    </hint>
    <hint type="destinationlabel">
     <x>269</x>
     <y>347</y>
    </hint>
   </hints>
  </connection>
 </connections>
</ui>
"""
