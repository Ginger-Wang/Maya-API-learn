# -*- coding: utf-8 -*-
from maya.cmds import *
if window('moveWindow', ex=True):
	deleteUI('moveWindow', window=True)	
moveWindow = window('moveWindow',title =  "Joint To SelectEdge V-1.0") 
moveJntlayoutName = formLayout() 
textName = text('textName',fn = 'fixedWidthFont',l = 'Local:',align = 'left')
localBox = checkBox('localBox',l = '')
moveButton = button('moveButton',l = 'Move...',h = 25,w= 130, c = 'moveJoint()')
creatButton = button('creatJnt',l = 'creat Joint',h = 30,w= 130, c = 'creatJnt()')
textL = text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)

formLayout(moveJntlayoutName,edit = 1,af=[(textName,'top',15),(textName,'left',8),(localBox,'top',18),
(moveButton,'top',8),(moveButton,'right',5),(creatButton,'right',5),(creatButton,'left',5),(textL,'left',5),(textL,'right',5),(textL,'bottom',5)],
ac = [(localBox,'left',5,textName),(moveButton,'left',10,localBox),(creatButton,'top',10,localBox),(textL,'top',3,creatButton)])
window('moveWindow',e = 1,w=210,h= 40)
showWindow(moveWindow)

def moveJoint():
	locBoxNum = checkBox(localBox,q= 1,v= 1)
	selectList = ls(sl =1 )	
	postion = getPosition(selectList)
	if locBoxNum:
		move(postion[0],postion[1],postion[2],selectList[-1]+'.scalePivot',selectList[-1]+'.rotatePivot')		
	else:
		xform(selectList[-1],ws = 1,t = postion)	
	cmannd = selectList[-1]+': moved To->selectEdge' +('%s' % postion)
	print cmannd

def creatJnt():
	selectList = ls(sl = 1)
	position = getPosition(selectList)
	select(cl = 1)
	joint(p = position)
	#moveJoint()
	
def getPosition(selectList):
	pointList = []
	if nodeType(selectList[-1]) != 'joint':
		for i in selectList:
			pointList.append(i)
	else:
		for i in selectList[:-1]:
			pointList.append(i)
	clu = cluster(pointList)	
	position = xform(clu[1],q=1,ws =1,rp = 1)
	delete(clu)
	return position
	

