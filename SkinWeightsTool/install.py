import sys,os
from maya import cmds,mel

def onMayaDroppedPythonFile(parm):
	_add_shelfButton()

def _add_shelfButton():
    file_Path,fileName = os.path.split(__file__)
    paths = sys.path
    gShelfTopLevel = mel.eval('$tmpVar=$gShelfTopLevel')
    parentName = cmds.tabLayout(gShelfTopLevel,q= 1,selectTab =1)
    scriptType = "py"
    scriptFile = "skinWeightTools"
    command =(f"""import sys,os
from importlib import reload
from PySide2 import QtWidgets, QtUiTools, QtCore
paths = sys.path
addPath = '{file_Path}'
if addPath not in paths:
    sys.path.append(addPath)
import skinWeightTools
reload(skinWeightTools)
app = QtWidgets.QApplication
mainwindow = skinWeightTools.SkinWeightTools()
mainwindow.ui.show()
app.exec_()""")
    #command = "execfile('{0}/{1}.{2}')".format(file_Path,scriptFile,scriptType)
    cmds.shelfButton(c = command  ,image1='pythonFamily.png',sourceType="python",imageOverlayLabel = scriptFile,p = parentName,ann = scriptFile )



