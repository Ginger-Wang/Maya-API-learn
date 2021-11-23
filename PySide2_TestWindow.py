import sys,os
from PySide2 import QtWidgets, QtUiTools, QtCore
import pymel.core as pm

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self,parent=None):
        super(MainWindow, self).__init__(parent)
        self.set_ui()
        
    def set_ui(self):
        file_Path = os.path.dirname(__file__)
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load("%s/animtorsTools.ui"%(file_Path))
        myUI = self.ui
        myUI.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        myUI.weight_VerticalSlider.valueChanged.connect(self.__setValue)
        myUI.weight_doubleSpinBox.valueChanged.connect(self.__setWeightValue)
        myUI.add_pushButton.clicked.connect(self.applyConstraintButton)
        myUI.apply_pushButton.clicked.connect(self.applyConstraintButton)
        myUI.matchtransforms_pushButton.clicked.connect(self.matchTranformsButton)
        myUI.matchTr_pushButton.clicked.connect(self.matchTrButton)
        myUI.matchRo_pushButton.clicked.connect(self.matchRoButton)
        myUI.tabWidget.currentChanged.connect(self.__resetMinmumValue)
        myUI.replacename_pushButton.clicked.connect(self.searchAndReplace)
        myUI.addPrefix_pushButton.clicked.connect(self.addPrefix)
        myUI.addSuffix_pushButton.clicked.connect(self.addSuffix)
        myUI.rename_pushButton.clicked.connect(self.renameaddNumber)

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
    	targetCtrl, sourceCtrl = ctrls[0],ctrls[1]
        myUI = self.ui
        isChecked = myUI.world_radioButton.isChecked()
        localIsChecked = myUI.local_radioButton.isChecked()
        if isChecked:
            tr = sourceCtrl.getTranslation(space="world")
            targetCtrl.setTranslation(tr, space="world")
        if localIsChecked:
            tr = sourceCtrl.getTranslation(space="object")
            targetCtrl.setTranslation(tr, space="object")
        #print "matchTrButton..."

    def matchRoButton(self):
        """only copy Translation,
    	first select A Object,
    	second select B Object,
    	then A Rotate to B"""
    	ctrls = self.getCtrls()
    	targetCtrl, sourceCtrl = ctrls[0],ctrls[1]
        myUI = self.ui
        isChecked = myUI.world_radioButton.isChecked()
        localIsChecked = myUI.local_radioButton.isChecked()
        if isChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=1, ro=1)
            pm.xform(targetCtrl, ws=1, ro=ro)
        if localIsChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=0, ro=1)
            pm.xform(targetCtrl, ws=0, ro=ro)
        #print "matchRoButton..."

    def matchTranformsButton(self):
        """copy transforms,
    	first select A Object,
    	second select B Object,
    	then A Rotate to B"""
    	ctrls = self.getCtrls()
    	targetCtrl, sourceCtrl = ctrls[0],ctrls[1]
        myUI = self.ui
        isChecked = myUI.world_radioButton.isChecked()
        localIsChecked = myUI.local_radioButton.isChecked()
        if isChecked:
            matrix = sourceCtrl.getMatrix(worldSpace=True)
            targetCtrl.setMatrix(matrix, worldSpace=True)
        if localIsChecked:
            matrix = sourceCtrl.getMatrix(objectSpace=True)
            targetCtrl.setMatrix(matrix, objectSpace=True)
        # aAlign2B()
        #print "matchTranformsButton..."

    def __setValue(self):
        """
        Get weight_VerticalSlider vlaue
        Set to weight_doubleSpinBox vlaue
        """
        value = self.ui.weight_VerticalSlider.value()
        self.ui.weight_doubleSpinBox.setValue(value / 1000.0)

    def __setWeightValue(self):
        """
        Get weight_doubleSpinBox vlaue
        Set to weight_VerticalSlider vlaue
        """
        value = self.ui.weight_doubleSpinBox.value()
        self.ui.weight_VerticalSlider.setValue(value * 1000.0)

    def __resetMinmumValue(self):
        """
        Click Select tabWidget and resize the window        
        """        
        myUI = self.ui
        tabObjectName = myUI.tabWidget.currentWidget()
        tabName = tabObjectName.objectName()
        if tabName == "rename_tab":
            myUI.setMinimumWidth(400)
            myUI.setMinimumHeight(520)
            myUI.resize(QtCore.QSize(400, 520))
        elif tabName == "match_tab":
            myUI.setMinimumWidth(400)
            myUI.setMinimumHeight(260)
            myUI.resize(QtCore.QSize(400, 260))
        elif tabName == "constraint_tab":
            myUI.setMinimumWidth(520)
            myUI.setMinimumHeight(360)
            myUI.resize(QtCore.QSize(520, 360))
            
    def getCtrls(self):
        ctrls = pm.ls(sl=1)
        return ctrls
    def searchAndReplace(self):
        """
        Search and Replace Selected objects name
        """
        selectionNames = self.getCtrls()
        searchText = self.ui.search_lineEdit.text()
        replaceText = self.ui.replace_lineEdit.text()
        for name in selectionNames:
            newName = name.replace(searchText,replaceText)
            name.rename(newName)
        #print "searchAndReplace",searchText,replaceText
    def addPrefix(self):
        """
        Add Prefix Selected objects name
        """
        prefixText = self.ui.prefix_lineEdit.text()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            newName = "%s%s"%(prefixText,name)
            name.rename(newName)
        #print "addPrefix",prefixText
                        
    def addSuffix(self):
        """
        Add Suffix Selected objects name
        """
        suffixText = self.ui.suffix_lineEdit.text()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            newName = "%s%s"%(name,suffixText)
            name.rename(newName)
        #print "addSuffix"

    def renameaddNumber(self):
        """
        Rename Selected objects name
        """
        nameText = self.ui.rename_lineEdit.text()
        startNumber = self.ui.startNum_spinBox.value()
        paddingNumber =self.ui.paddingNum_spinBox.value()
        selectionNames = self.getCtrls()
        for name in selectionNames:
            strName = "%s{:0%dd}"%(nameText,paddingNumber)         
            newName = strName.format(startNumber)
            name.rename(newName)
            startNumber+=1
        #print "renameaddNumber"

           
if __name__ == "__main__":
    app = QtWidgets.QApplication
    childrenNames = app.activeWindow()
    if childrenNames:
        for child in childrenNames.children():
            print  child.objectName()
            if child.objectName() == "MyTestWindow":
                child.deleteLater()

    mainwindow = MainWindow()
    mainwindow.ui.show()
    app.exec_()
