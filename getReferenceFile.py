# -*- coding: UTF-8 -*-
import os,sys
from maya import OpenMaya,cmds
'''
#cmds.referenceQuery( 'Char_Medium_CtrlRigRN',filename=True )
thisFile = cmds.file(q=1 ,location = 1 )
thisPath,thisName = os.path.split(thisFile)
print thisPath,thisName
allReferenceFiles = cmds.file(q=1 ,r = 1,wcn = 1)
pathAndName = [os.path.split(path) for path in allReferenceFiles]
print pathAndName
'''

"""
######################################################
#                                                    #
#  List the files for all references in the file...  #
#                                                    #
######################################################
"""

thisFile = cmds.file(q=1 ,location = 1 )
allReferenceFiles = cmds.file(q=1 ,r = 1,wcn = 1)
pathAndName = [os.path.split(path) for path in allReferenceFiles]
if cmds.window("referenceFileWin",ex = 1):
    cmds.deleteUI("referenceFileWin") 
cmds.window("referenceFileWin",title ="Reference File...")
formLayoutName = cmds.formLayout()
aboutMeTxt = cmds.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',
backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
thisFileGrp = cmds.textFieldButtonGrp(l = "This File Full Name :",bl="Reload All Reference Files...",tx = thisFile,bc= "print('Hello...')")
rowLayoutName = cmds.rowLayout('rowLayoutName',numberOfColumns = 2,columnAttach=[(1, 'left', 5), (2, 'right',5)])
listName = ["FilePath:","FileName:"]
for i in listName:
    columnLayoutName = cmds.menuBarLayout()
    for string in pathAndName:
        cmds.textFieldGrp(l = i,cw = [1,50],tx = string[listName.index(i)],h = 30)
        cmds.separator(style='in',h=1)
    cmds.setParent('..')  
cmds.formLayout(formLayoutName,e = 1,af = [(thisFileGrp,"top",5),(thisFileGrp,"left",5),(thisFileGrp,"right",5),(aboutMeTxt,"left",5),(aboutMeTxt,"right",5),(aboutMeTxt,"bottom",5)],
ac = [(rowLayoutName,"top",5,thisFileGrp),(aboutMeTxt,"top",5,rowLayoutName)])
cmds.window("referenceFileWin",e = 1,h = 30,w = 200)
cmds.showWindow("referenceFileWin")

