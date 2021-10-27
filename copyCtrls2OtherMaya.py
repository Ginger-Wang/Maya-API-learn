#!/usr/bin/python
# -*- coding: UTF-8 -*-
import pymel.core as pm
import pyperclip

def returnFloat(numList):
    try:
        floatList = [float(i) for i in numList]
        return floatList
    except:
        pass
        
def translationMatrix(matrixStr):
    matrixList = matrixStr.strip("[[").strip("]]").split("], [")
    floatList = [returnFloat(i.split(",")) for i in matrixList]
    matrix = pm.datatypes.Matrix(floatList)
    return matrix
    
ctrls = pm.ls(sl = 1)
copyDict = {}
for ctrl in ctrls:
    matrix = ctrl.getMatrix(worldSpace = 1)
    copyDict[str(ctrl)] = [list(i) for i in matrix]
print copyDict
pyperclip.copy(str(copyDict))

'''
matrixStr = pyperclip.paste()
pasteDict = {}
likeDictList = matrixStr.strip("{").strip("}").split(", '")
dictList = [i.split(":") for i in likeDictList]
for dic in dictList:
    key = dic[0].strip("'")
    value = dic[1].strip(" ")
    pasteDict[pm.PyNode(key)] = translationMatrix(value)

for key,value in pasteDict.items():
    key.setMatrix(value)

'''
