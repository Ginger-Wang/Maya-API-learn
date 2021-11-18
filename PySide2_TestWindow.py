from PySide2 import QtWidgets, QtUiTools, QtCore
import pymel.core as pm


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.load_ui()

    def load_ui(self):
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load("//Cnshasgamefsv1/MGS3/Users/WangJinge/Scripts/animatorsTools/animtorsTools.ui")

    def set_ui(self):
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
        myUI = self.ui
        isChecked = myUI.world_radioButton.isChecked()
        localIsChecked = myUI.local_radioButton.isChecked()
        if isChecked:
            tr = sourceCtrl.getTranslation(space="world")
            targetCtrl.setTranslation(tr, space="world")
        if localIsChecked:
            tr = sourceCtrl.getTranslation(space="object")
            targetCtrl.setTranslation(tr, space="object")
        print "matchTrButton..."

    def matchRoButton(self):
        """only copy Translation,
    	first select A Object,
    	second select B Object,
    	then A Rotate to B"""
        ctrls = self.getCtrls()
        targetCtrl, sourceCtrl = ctrls[0], ctrls[1]
        myUI = self.ui
        isChecked = myUI.world_radioButton.isChecked()
        localIsChecked = myUI.local_radioButton.isChecked()
        if isChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=1, ro=1)
            pm.xform(targetCtrl, ws=1, ro=ro)
        if localIsChecked:
            ro = pm.xform(sourceCtrl, q=1, ws=0, ro=1)
            pm.xform(targetCtrl, ws=0, ro=ro)
        print "matchRoButton..."

    def matchTranformsButton(self):
        """copy transforms,
    	first select A Object,
    	second select B Object,
    	then A Rotate to B"""
        ctrls = self.getCtrls()
        targetCtrl, sourceCtrl = ctrls[0], ctrls[1]
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
        print "matchTranformsButton..."

    def __setValue(self):
        value = self.ui.weight_VerticalSlider.value()
        self.ui.weight_doubleSpinBox.setValue(value / 1000.0)

    def __setWeightValue(self):
        value = self.ui.weight_doubleSpinBox.value()
        self.ui.weight_VerticalSlider.setValue(value * 1000.0)

    def __resetMinmumValue(self):
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


if __name__ == "__main__":
    app = QtWidgets.QApplication
    childrenNames = app.activeWindow()
    if childrenNames:
        for child in childrenNames.children():
            print  child.objectName()
            if child.objectName() == "MyTestWindow":
                child.deleteLater()
        try:
            targetCtrl, sourceCtrl = pm.ls(sl=1)[0], pm.ls(sl=1)[1]
        except Exception, erro:
            print erro
            targetCtrl, sourceCtrl = None, None
        mainwindow = MainWindow()
        mainwindow.set_ui()
        mainwindow.ui.show()
    app.exec_()

        
        
'''
mainwindow.ui.label.setHidden(True)
mainwindow.ui.checkBox_2.setHidden(True)
mainwindow.ui.checkBox_3.setHidden(True)
mainwindow.ui.checkBox_4.setHidden(True)
value = mainwindow.ui.weight_doubleSpinBox.value()
mainwindow.ui.weight_VerticalSlider.setValue(value*100)
mainwindow.ui.weight_VerticalSlider.sliderMoved.connect()
sliderV = mainwindow.ui.weight_VerticalSlider.value()
mainwindow.ui.weight_doubleSpinBox.setValue(sliderV/100.0)
mainwindow.ui.weight_VerticalSlider.valueChanged(
mainwindow.ui.weight_doubleSpinBox.valueChanged.connect
mainwindow.ui.add_pushButton.clicked.connect
myUI.setMinimumHeight(280)
myUI.setMinimumWidth(360)
mainwindow.ui.setBaseSize(QSize(340,270))
mainwindow.ui.resize(QSize(340,270))
mainwindow.ui.world_radioButton.isChecked()
mainwindow.ui.tabWidget.currentChanged.connect(
tabname = mainwindow.ui.tabWidget.currentWidget()
print tabname.objectName()
textname = mainwindow.ui.search_lineEdit.text()
print textname()
'''
