# -*- coding: UTF-8 -*-
from maya import cmds,mel

allNameSpaces = cmds.namespaceInfo(lon = 1,recurse = 1)
removeList = ["UI","shared"]
nameSpaces = [name for name in allNameSpaces if name not in removeList]
nameSpaces.sort(reverse = 1)
for nameSpace in nameSpaces:
    cmds.namespace(moveNamespace=[nameSpace,":"],f=1)
    cmds.namespace(removeNamespace=nameSpace)
    print "Remove Name_Space :%s"%(nameSpace)
mel.eval('print "Remove nameSpaces finish..."') 
