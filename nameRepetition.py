# -*- coding: UTF-8 -*-
from maya.cmds import *

def listNameRepetition():
	allobjs = ls(tr = 1)
	allobjs.sort(reverse = 1)
	allnames = []
	for obj in allobjs:
		if len(obj.split('|')) > 1:	
			allnames.append(obj)
	return allnames					
#renameObj()


def SelectAllNameRepetitionObject():
	select(listNameRepetition())
		
def renameObj():
	allnames = listNameRepetition()
	for name in allnames:
		newName = name.replace('|','_')		
		inputText=textField(newName+'Layout',q=True,text=True)
		if inputText != newName:
			rename(name,inputText)

def theNameRepetitionWindow():	
	if window('NamerepetitionWindow',ex=True):
		deleteUI('NamerepetitionWindow')
	Namerepetitionwin = window('NamerepetitionWindow',t='Name Repetition 1.0')
	scrollLayout(h = 200 ,w =300)
	allnames = listNameRepetition()
	if len(allnames)!=0:
		rowLayout = rowColumnLayout()
		for objtext in allnames:
			textFieldName = text(label = objtext,align = 'left',h = 20,backgroundColor=(1,0,0),font='fixedWidthFont')
			tname = objtext.replace('|','_')
			renewName = objtext.split('|')[-1]
			#print renewName
			textField(objtext+'Layout',h = 25,text = renewName+'_#')
		inquireText = text(label = '重命名重名物体:',font='fixedWidthFont')
		renameButton = button(label = '执行...',h = 30,command = 'renameObj()',ann = '更改输入框中的名字，用以改变重名物体的名字...')
		selectButton = button(label = 'SelectAllNameRepetitionObject',h = 30,command = 'SelectAllNameRepetitionObject()',ann = '选择所有的重名物体...')
	else:
		rowLayoutA = rowColumnLayout(numberOfColumns=2, columnAttach=(1, 'right', 5), columnWidth=[(1, 175), (2, 100)])
		text(label = '该场景大纲中不存在重名物体:',font='fixedWidthFont')
		button(label = 'CLOSE...',h = 30,command ='deleteUI("NamerepetitionWindow")')
	
	
	window('NamerepetitionWindow',e = 1,w = 300,h = 200)
	showWindow(Namerepetitionwin)
	

theNameRepetitionWindow()
