# -*- coding: UTF-8 -*-
'''
Writer : Giner.Wang
Date   : 2019.09.17
'''
import maya.cmds as cmds
class AttrDefault:
	def __init__(self,ctrlName):
		self.ctrlName = ctrlName
	def getAttrName(self):
		attrlist = []		 
		cbAttr = cmds.listAttr(self.ctrlName, cb=1)
		if cbAttr:
			attrlist.extend([i for i in cbAttr])
		keyAttr = cmds.listAttr(self.ctrlName, k=1,u = 1)
		if keyAttr:
			attrlist.extend([i for i in keyAttr])
		return attrlist
	def getAttrDefault(self,attr):
		return cmds.attributeQuery(attr,node = self.ctrlName,listDefault = True)[0]			
	def setAttrDefault(self,attr,num):
		cmds.setAttr('{0}.{1}'.format(self.ctrlName,attr),num)

def setAttrToDefault(name):	
	defaulAttr = AttrDefault(name)
	attrlist = defaulAttr.getAttrName()	
	for i in attrlist:
		num = defaulAttr.getAttrDefault(i)
		defaulAttr.setAttrDefault(i,num)
	return attrlist
	
ctrls = cmds.ls(sl = 1)
for name in ctrls:
	setAttrToDefault(name)
