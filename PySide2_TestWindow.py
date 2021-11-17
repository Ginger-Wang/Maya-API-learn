from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2.QtCore import *

class MainWindow(QMainWindow):
    def __init__(self,parent = None):
        super(MainWindow,self).__init__(parent)
        self.load_ui()

    def load_ui(self):        
        loader = QUiLoader()
        self.ui = loader.load("D:\MayaPycharm\Maya_Scripts/test.ui")
    def set_ui(self):
        myUI = self.ui
        myUI.setWindowFlags(Qt.WindowStaysOnTopHint)
        myUI.setMinimumHeight(280)
        myUI.setMinimumWidth(360)
        myUI.weight_VerticalSlider.valueChanged.connect(self.setValue)
        myUI.weight_doubleSpinBox.valueChanged.connect(self.setWeightValue)
        myUI.add_pushButton.clicked.connect(self.applyConstraintButton)
        myUI.apply_pushButton.clicked.connect(self.applyConstraintButton)
        myUI.matchtransforms_pushButton.clicked.connect(self.matchTranformsButton)
        myUI.matchTr_pushButton.clicked.connect(self.matchTrButton)
        myUI.matchRo_pushButton.clicked.connect(self.matchRoButton)
       
    def applyConstraintButton(self):
        print "applyConstraintButton..."
    def matchTrButton(self):
        print "matchTrButton..."
    def matchRoButton(self):
        print "matchRoButton..."
    def matchTranformsButton(self):
        print "matchTranformsButton..."         
    def setValue(self):
        value = self.ui.weight_VerticalSlider.value()
        self.ui.weight_doubleSpinBox.setValue(value/1000.0)
    def setWeightValue(self):
        value = self.ui.weight_doubleSpinBox.value()
        self.ui.weight_VerticalSlider.setValue(value*1000.0)
                  
              
if __name__ == "__main__":
    #parentWindow = QApplication.activeWindow() 
    for child in QApplication.activeWindow().children():
        print  child.objectName()
        if child.objectName() == "MyTestWindow":
            child.deleteLater()
    mainwindow = MainWindow()
    mainwindow.set_ui()

    mainwindow.ui.show()


        
        
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
'''
