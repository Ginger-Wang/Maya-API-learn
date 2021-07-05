# -*- coding: UTF-8 -*-
import pymel.core as pm
from maya import cmds
"""
Test in Maya 2018.4

"""
def patchingShapeWindow():
	if cmds.window("patchingShapeWindow", ex=True):
		cmds.deleteUI("patchingShapeWindow", window=True)
	cmds.window("patchingShapeWindow", title="Patching Shape V-1.0")
	layoutName = cmds.formLayout()
	
	meshNameText = cmds.text('meshNameText',label = 'Mesh Name :')
	meshNameTextField = cmds.textField('meshNameTextField',text = '',h = 25,w = 180,ed = 0)
	loadMeshButton = cmds.button("loadMeshButton",label = "<<< Pick",h = 50,c = "loadGeo('meshNameTextField')")
	blendShapeText = cmds.text('blendShapeText',label = 'BlendShape:')
	blendShapeTextField = cmds.textField('blendShapeTextField',text = '',h = 25,w = 180,ed = 0)
	jointText = cmds.text('jointText',label = 'Joint Name:')
	jointTextTextField = cmds.textField('jointTextTextField',text = '',h = 25,w = 180,ed = 0)
	loadJointButton = cmds.button("loadJointButton",label = "<<< Pick",h = 25,c = "loadJoint('jointTextTextField')")
	#jointAxisText = cmds.text('jointAxisText',label = 'Joint Axis  :')
	sep1 = cmds.separator("sep1",style="in",h = 1)
	jointAxisRadioButton = cmds.radioButtonGrp("jointAxisRadioButton", nrb=3, label='Joint Axis :', labelArray3=['X', 'Y', 'Z'],sl =2,cw4 = [85 ,60 ,60 ,60],cc ="rotateJoint()")
	angleTextField = cmds.floatFieldGrp("angleTextField",label = "Joint Angle:",cw2=[90,80],v1 = 0,cc ="rotateJoint()")
	reverseChechBox = cmds.checkBox("reverseChechBox",l = "Reverse",cc ="rotateJoint()")
	creatConnectButton = cmds.button("creatConnectButton",label = "Create Patch Shape",h = 30,c = "creatConnect()")
	#applyButton = cmds.button("applyButton",label = "Apply",h = 30,c = "pass")
	sep2 = cmds.separator("sep2",style="in",h = 1)
	aboutMeTxt = cmds.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
	
	cmds.formLayout(layoutName,e = 1,
	af = [(meshNameText,"top",15),(meshNameText,"left",5),(meshNameTextField,"top",7),(loadMeshButton,"top",10),(loadMeshButton,"right",5),
	(blendShapeText,"left",5),(jointText,"left",5),(loadJointButton,"right",5),(sep1,"left",0),(sep1,"right",0),(jointAxisRadioButton,"left",1),(angleTextField,"left",5),(creatConnectButton,"left",5),(creatConnectButton,"right",5),
	(jointAxisRadioButton,"left",5),(sep2,"left",0),(sep2,"right",0),(aboutMeTxt,"left", 5),(aboutMeTxt,"right", 5),(aboutMeTxt,"bottom", 5)],
	ac = [(meshNameTextField,"left",5,meshNameText),(loadMeshButton,"left",5,meshNameTextField),(blendShapeText,"top",12,meshNameTextField),(blendShapeTextField,"left",5,blendShapeText),
	(blendShapeTextField,"top",5,meshNameTextField),(jointText,"top",12,blendShapeTextField),(jointTextTextField,"left",10,jointText),(jointTextTextField,"top",5,blendShapeTextField),
	(loadJointButton,"top",5,blendShapeTextField),(loadJointButton,"left",5,jointTextTextField),(sep1,"top",5,jointTextTextField),(jointAxisRadioButton,"top",12,jointTextTextField),
	(angleTextField,"top",10,jointAxisRadioButton),(reverseChechBox,"left",5,angleTextField),(reverseChechBox,"top",15,jointAxisRadioButton),(creatConnectButton,"top",5,angleTextField),
	(sep2,"top",5,creatConnectButton),(aboutMeTxt,"top", 5,sep2)])
	
	cmds.window('patchingShapeWindow', edit =True, width = 320,height = 200)
	cmds.showWindow("patchingShapeWindow")


	


def loadGeo(textFieldName):
    sels = cmds.ls(sl = 1)
    if len(sels) == 0:
        print 'Please select and select only one object...'
    else:
        cmds.textField(textFieldName,e =1,text = sels[0])
        history = cmds.listHistory(sels[0])
        blendShapeName = [i for i in history if cmds.nodeType(i)=="blendShape"]
        if blendShapeName:
        	cmds.textField("blendShapeTextField",e =1,text = blendShapeName[0])
        else:
        	cmds.textField("blendShapeTextField",e =1,text = "None")
        
def loadJoint(textFieldName):
    jointNames = pm.ls(sl = 1)
    if len(jointNames) == 0:
        print 'Please select and select only one object...'
    else:
        pm.textField(textFieldName,e =1,text = str(jointNames[0]))
        name = jointNames[0]
        xyzAxisNum = cmds.radioButtonGrp("jointAxisRadioButton",q=1,sl = 1)
        if xyzAxisNum == 1:
        	axis = pm.PyNode("%s.rx"%(name))
        elif xyzAxisNum == 2:
        	axis = pm.PyNode("%s.ry"%(name))
        elif xyzAxisNum == 3:
        	axis = pm.PyNode("%s.rz"%(name))
        value = axis.get()
        pm.floatFieldGrp("angleTextField",e = 1,v1 = value)
        

def createReverse(mainCtrl,name = "Test"):
	reverseName = pm.createNode("reverse",name = "%s_Reverse"%(name))
	multiply = pm.createNode("multiplyDivide",name = "%s_MD"%(name))
	#connectAttr -f Test_MD.outputX Test_Reverse.inputX;
	multiply.outputX.connect(reverseName.inputX,f = 1)
	mainCtrl.OX_Male.connect(multiply.input1X,f = 1)
	multiply.input2X.set(0.1)
	return reverseName
	
"""
mainCtrl = pm.PyNode("Main")
createReverse(mainCtrl,name = "Test")

"""
def addTarget(blendShapeName,baseMesh,targetName):
	baseObject = baseMesh.getShapes()
	newMesh = pm.createNode("mesh",name = targetName)
	baseObject[1].worldMesh[0].connect(newMesh.inMesh,f = 1)
	baseObject[1].worldMesh[0].disconnect(newMesh.inMesh)
	try:
		weightList = pm.listAttr("%s.w[:]"%blendShapeName)
		number = len(weightList)
		blendShapeName.addTarget(baseObject[0],number,newMesh,1.0,targetType= "object")
		print("sculptTarget -e -target %d %s;"%(number,blendShapeName))
	except:
		blendShapeName.addTarget(baseObject[0],0,newMesh,1.0,targetType= "object")
		print("sculptTarget -e -target 0 %s;"%(blendShapeName))
	pm.delete(newMesh.getTransform())

def creatConnect():
	mainCtrl = pm.PyNode("Main")
	jntName = pm.PyNode(cmds.textField("jointTextTextField",q=1,text = 1))
	baseMesh = pm.PyNode(cmds.textField("meshNameTextField",q=1,text = 1))
	blendShapeName = cmds.textField("blendShapeTextField",q=1,text = 1)	
	#bsName = pm.PyNode(cmds.textField("blendShapeTextField",q=1,text = 1))
	xyzAxisNum = cmds.radioButtonGrp("jointAxisRadioButton",q=1,sl = 1)
	angleNum = cmds.floatFieldGrp("angleTextField",q = 1,v1 =1)
	reverseNum = cmds.checkBox("reverseChechBox",q = 1,v = 1)
	if blendShapeName != "None":
		bsName = pm.PyNode(cmds.textField("blendShapeTextField",q=1,text = 1))
		print bsName
	else:
		bsName = pm.blendShape(baseMesh,foc = True)[0]
		cmds.textField("blendShapeTextField",e =1,text = str(bsName))
	if reverseNum:
		angle = angleNum*-1
	else:
		angle = angleNum
	bsAngle = str(abs(angle)).replace(".","_")
	if xyzAxisNum == 1:
		xyzAxis = "rx"
		connectJntAxis = pm.PyNode("%s.rx"%(jntName))
	elif xyzAxisNum == 2:
		xyzAxis = "ry"
		connectJntAxis = pm.PyNode("%s.ry"%(jntName))	
	elif xyzAxisNum == 3:
		xyzAxis = "rz"
		connectJntAxis = pm.PyNode("%s.rz"%(jntName))
			
	#print angle,connectJntAxis,xyzAxis
	if pm.objExists("%s_Reverse"%(bsName)):
		adjust_Reverse = pm.PyNode("%s_Reverse"%(bsName))
	else:
		adjust_Reverse = createReverse(mainCtrl,name = bsName)
	jntAdjustMD = pm.createNode("multiplyDivide",name = "%sAdjust_MD_%s"%(jntName,xyzAxis),ss = 1)
	jntAdjustSR = pm.createNode("setRange",name = "%sAdjust_SR_%s"%(jntName,xyzAxis),ss = 1)
	if angle > 0:
		pm.setAttr("%s.maxX"%(jntAdjustSR),1)
		pm.setAttr("%s.oldMaxX"%(jntAdjustSR),angle)
		name = "BS_%s%s%s"%(jntName,xyzAxis,bsAngle)
		addTarget(bsName,baseMesh,name)
	else:
		pm.setAttr("%s.minX"%(jntAdjustSR),1)
		pm.setAttr("%s.oldMinX"%(jntAdjustSR),angle)
		name = "BS_%s%s%sF"%(jntName,xyzAxis,bsAngle)
		addTarget(bsName,baseMesh,name)
			
	adjust_Reverse.outputX.connect(jntAdjustMD.input1X,f = 1)
	connectJntAxis.connect(jntAdjustMD.input2X,f = 1)
	jntAdjustMD.outputX.connect(jntAdjustSR.valueX,f = 1)
	jntAdjustSR.outValueX.connect("%s.%s"%(bsName,name),f = 1)
	connectJntAxis.set(angle)


def rotateJoint():
	jntName = pm.PyNode(cmds.textField("jointTextTextField",q=1,text = 1))
	reverseNum = cmds.checkBox("reverseChechBox",q = 1,v = 1)
	xyzAxisNum = cmds.radioButtonGrp("jointAxisRadioButton",q=1,sl = 1)
	number = cmds.floatFieldGrp("angleTextField",q = 1,v1 =1)
	if reverseNum:
		angle = number*-1
	else:
		angle = number
	if xyzAxisNum == 1:
		jntName.r.set(angle,0,0)
	elif xyzAxisNum == 2:
		jntName.r.set(0,angle,0)	
	elif xyzAxisNum == 3:
		jntName.r.set(0,0,angle)




try:
	patchingShapeWindow()
except:
	if cmds.window("errorWindow", ex=True):
		cmds.deleteUI("errorWindow", window=True)	
	window = cmds.window("errorWindow",title="Tell Me", iconName='Short Name')
	cmds.columnLayout( adjustableColumn=True )
	cmds.separator("sepTop",style="in",h = 10)
	cmds.text("errorText",label="\n  The command an error occurred at runtime...\n",bgc = [1,0,0])
	cmds.separator("sepMiddle",style="in",h = 10)
	cmds.button( label='Close', command=('deleteUICommand()') )
	cmds.separator("sepBottom",style="in",h = 10)
	cmds.setParent( '..' )
	cmds.showWindow( window )

def deleteUICommand():
	cmds.deleteUI("errorWindow",window=True)
	print("Test in Maya 2018.4.\nPlease contact me if you have any questions!\nQQ&&WeChat: 370871841")
