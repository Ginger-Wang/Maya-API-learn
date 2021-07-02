#!/usr/bin/python
# -*- coding: UTF-8 -*-
from maya import cmds


class TestFunction:
    def __init__(self):
        self.name = __name__
        self.windowName = "mytestWindow"

    def thisFunction(self):
        print "thisFunction..."
        self.testFunction()

    def testFunction(self):
        print "This Function Name :%s" % (self.name)

    def testCloseWin(self):
        cmds.deleteUI(self.windowName, window=1)
        print "close..."

    def windowPars(self):
        cmds.columnLayout(adjustableColumn=1)
        cmds.button(l="print:", c=(lambda *args: self.thisFunction()), h=30)
        cmds.button(label='Close', command=(lambda *args: self.testCloseWin()), h=30)

    def thisWindow(self):
        if cmds.window(self.windowName, q=1, ex=1):
            cmds.deleteUI(self.windowName)
        theWindow = cmds.window(self.windowName, t="test...")
        self.windowPars()
        cmds.window(self.windowName,e = 1,w = 120,h = 60)
        cmds.showWindow(self.windowName)


if __name__ == "__main__":
    aa = TestFunction()
    aa.thisWindow()
