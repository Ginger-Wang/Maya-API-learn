# -*- coding: UTF-8 -*-
import pymel.core as pm

def rebuildBoneWindow():    
    if pm.window("rebuildBoneWindow", ex=True):
        pm.deleteUI("rebuildBoneWindow", window=True)
        
    pm.window("rebuildBoneWindow", title="Rebuil Bone V-1.0")
    layoutName = pm.formLayout()
    startJntText = pm.textFieldButtonGrp('startTfbName', label='StartJoint :', text='', buttonLabel='<<<Pick' ,bc = 'pickJoint("start")',columnWidth=([1,60],[2,200],[3,50]),columnAlign=([1,'left'],[2,'left'],[3,'left']),rat = ([1,'top',10],[2,'top',5],[3,'top',2]))
    endJntText = pm.textFieldButtonGrp('endTfbName', label='EndJoint :', text='', buttonLabel='<<<Pick' ,bc = 'pickJoint("end")',columnWidth=([1,60],[2,200],[3,50]),columnAlign=([1,'left'],[2,'left'],[3,'left']),rat = ([1,'top',10],[2,'top',5],[3,'top',2]))
    NumberName = pm.text('NumberName',label = 'Bone Number:')
    JointNumInt = pm.intSliderGrp('JointNumInt',field = True,min = 2, max = 20,fieldMaxValue =100, w = 240, v =2)
    boneNameText = pm.text(label = 'Bone Name:',h =25)
    boneNameField = pm.textField('boneNameField',text = 'Jnt',h = 25,w = 246)
    hierarchyTxt = pm.text('hierarchyTxt',label = 'Hierarchy: ')
    radioButtonGrpName = pm.radioButtonGrp('radioButtonGrpName',numberOfRadioButtons =2,labelArray2 =("Self", "Hierarchy"),sl = 2)
    buildButton = pm.button('buildButton',label = 'Build Bone',h= 30,c = 'buildBone()')
    partNumberName = pm.text('partNumberName',label = 'Bone Part Number:')
    partJointNumInt = pm.intSliderGrp('partJointNumInt',field = True,min = 0, max = 20,fieldMaxValue =100, w = 240, v =1)
    createButton = pm.button('createButton',label = 'Part Bone',h= 30,c = 'createPartJnt()')
    aboutMeTxt = pm.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
    pm.formLayout(layoutName,e = 1,af = [(startJntText,'top',8),(NumberName,'left',5),(JointNumInt,'top',8),(boneNameText,'left',5),(hierarchyTxt,'left',5),(JointNumInt,'right',5),(boneNameField,'right',5),
    (buildButton,'left',5),(partNumberName,"left",5),(partJointNumInt,"right",5),(createButton,"left",5),(createButton,"right",5),(aboutMeTxt,'left',5),(aboutMeTxt,'right',5),(aboutMeTxt,'bottom',5)],
    ac = [(endJntText,'top',12,startJntText),(NumberName,'top',12,endJntText),(JointNumInt,'top',8,endJntText),(JointNumInt,'left',5,NumberName),(boneNameField,'top',15,partNumberName),(boneNameText,'top',15,partNumberName),
    (boneNameField,'left',5,boneNameText),(hierarchyTxt,'top',10,boneNameText),(radioButtonGrpName,'top',5,boneNameField),(radioButtonGrpName,'left',5,hierarchyTxt),(buildButton,'top',10,hierarchyTxt),
    (partNumberName,'top',15,NumberName),(partJointNumInt,'left',1,partNumberName),(partJointNumInt,'top',5,JointNumInt),(createButton,"top",10,hierarchyTxt),(createButton,"left",5,buildButton),(aboutMeTxt,'top',3,createButton)],
    ap = [(startJntText,'right',1,99),(endJntText,'right',1,99),(startJntText,'left',1,1),(endJntText,'left',1,1),(createButton,"left",2.5,75),(buildButton,"right",2.5,75)])
         
    pm.window('rebuildBoneWindow', edit =True, width = 240,height = 120)
    pm.showWindow("rebuildBoneWindow")

rebuildBoneWindow()

def pickJoint(name):
    sels = pm.ls(sl = 1)
    if len(sels) ==1:
        pm.textFieldButtonGrp('%sTfbName'%(name),e =1,text = sels[0])
    elif len(sels) == 0:
        print 'Please select and select only one object...'
    else:
        pm.textFieldButtonGrp('startTfbName',e =1,text = sels[0])
        pm.textFieldButtonGrp('endTfbName',e =1,text = sels[-1])

def jntSeleted(fJnt,eJnt):
    chirld = []
    jntPosition = []
    jntPosition.append(pm.xform(fJnt,q = 1, ws = 1, t =1))
    chirld.append(fJnt)
    while chirld[-1] != eJnt :
        chirldA = pm.listRelatives(chirld[-1],c=1,type = 'joint')
        jntPosition.append(pm.xform(chirldA[0],q = 1, ws = 1, t =1))
        chirld.append(chirldA[0])
    return chirld,jntPosition

def createInfoNode(crvShapeName):
    infoNode = pm.createNode('pointOnCurveInfo',name = 'CVRinfoNode0#')
    crvShapeName.worldSpace.connect(infoNode.inputCurve)
    return infoNode

def createCrv(fJnt,eJnt):
    handleName,effectorName,crvName = pm.ikHandle(sj= fJnt, ee= eJnt,sol= 'ikSplineSolver',scv=0,pcv=0)
    jointList = handleName.getJointList()
    crvShapeName = crvName.getShape()
    pm.delete(handleName,effectorName)
    return crvName,crvShapeName,jointList

def buildBone():
	fJnt = pm.PyNode(pm.textFieldButtonGrp('startTfbName',q = 1,text = 1))
	eJnt = pm.PyNode(pm.textFieldButtonGrp('endTfbName',q = 1,text = 1))
	jntRadius = fJnt.radius.get()
	jntNum = pm.intSliderGrp('JointNumInt',q =1,v =1)
	boneName = pm.textField('boneNameField',q = 1,tx = 1)
	x = radioButtonGrpName = pm.radioButtonGrp('radioButtonGrpName',q = 1,sl =1)
	crvName,crvShapeName,jointList = createCrv(fJnt,eJnt)
	value = crvShapeName.length()
	CurveAbsV = value/(jntNum-1)
	#print CurveAbsV
	infoNode = createInfoNode(crvShapeName)
	if x == 1:
		for num in range(jntNum):
			#pm.setAttr(infoNode+'.parameter',num*CurveAbsV)
			parameter = crvShapeName.findParamFromLength(CurveAbsV*num)
			infoNode.parameter.set(parameter)
			jntPosition = infoNode.position.get()
			jntName = pm.joint(p =jntPosition,radius = 0.5,name = '%s%03d'%(boneName,num+1))
			infoNode.position.connect(jntName.t)
			pm.refresh()
	elif x == 2:
		jntNames = []
		for num in range(1,jntNum-1):
			parameter = crvShapeName.findParamFromLength(CurveAbsV*num)
			infoNode.parameter.set(parameter)
			jntPosition = infoNode.position.get()
			jntName = pm.joint(p =jntPosition,radius = jntRadius,name = '%s%03d'%(boneName,num))
			if jntNames:
				pm.joint(jntNames[-1],e = 1, zso = 1,oj = 'xyz',sao = 'yup')
			jntNames.append(jntName)
			pm.refresh()
		delJnt = [i for i in fJnt.getChildren() if eJnt not in fJnt.getChildren()]
		print delJnt		
		fJnt.addChild(jntNames[0])
		pm.parent(eJnt,jntNames[-1])
		if delJnt:
			pm.delete(delJnt)
	pm.delete(crvName)

def createPartJnt():	
	partJntNum =  pm.intSliderGrp('partJointNumInt',q =1,v =1)
	startJoint = pm.PyNode(pm.textFieldButtonGrp('startTfbName',q = 1,text = 1))
	endJoint = pm.PyNode(pm.textFieldButtonGrp('endTfbName',q = 1,text = 1))
	if partJntNum != 0:		
		crvName,crvShapeName,jointList = createCrv(startJoint,endJoint)
		pm.delete(crvName)
		jointList.append(endJoint)
		number = len(jointList)
		for each in range(number-1):
			print jointList[each],jointList[each+1]
			ro = pm.xform(jointList[each],q=1,ws =1,ro =1)	
			partCrvName,partCrvShapeName,partJointList = createCrv(jointList[each],jointList[each+1])
			infoNode = createInfoNode(partCrvShapeName)
			value = partCrvShapeName.length()
			CurveAbsV = value/(partJntNum + 1)
			parentJnt = jointList[each]
			for num in range(1,partJntNum+1):
				pm.select(cl =1)
				parameter = partCrvShapeName.findParamFromLength(CurveAbsV*num)
				infoNode.parameter.set(parameter)
				jntPosition = infoNode.position.get()
				jntName = pm.joint(p =jntPosition,radius = 0.4,o = ro,name = '%sPart%03d'%(jointList[each],num))
				parentJnt.addChild(jntName)
				parentJnt = jntName
				pm.refresh()
			parentJnt.addChild(jointList[each+1])
			pm.delete(partCrvName)
	




'''
	
startJnt = pm.PyNode('Root')	 
endJnt = pm.PyNode('Chest')	
handleName,effectorName,curveName = pm.ikHandle(sj= startJnt, ee= endJnt,sol= 'ikSplineSolver',scv=0,pcv=0)
jointList = handleName.getJointList()
nameJointList= []
dict = {}
for jnt in jointList:
	name = 'Del_%s'%(jnt)
	nameJointList.append(name)
	childrenName = [i for i in jnt.getChildren() if pm.nodeType(i) == 'joint']
	if len(childrenName) >=2:
		children = [i for i in childrenName if i not in jointList]
		dict[str(jnt)] = children
		
jointListA = [str(i) for i in jointList]

for jnt in jointList:
	if jnt in dict.keys():
		print dict[jnt]


creatJntList = ['joint11','joint12','joint13','joint14','joint15','joint16','joint17']
number = len(creatJntList)
for num in range(number):
	try:
		keyName = str()
		pm.rename(jointList[num],nameJointList[num])
		parentName = pm.rename(creatJntList[num],jointListA[num])
		if jointListA[num]in dict.keys():
			pm.parent(dict[jointListA[num]],parentName)
	except:
		pm.rename(creatJntList[num],'Jnt%03d'%(num+1))
		

try:
	print(jointList[7])
except:
	print('no object in list....')
	
	
def makeJoint(startJoint,endJoint,jntNum):
	childJoint = startJoint.getChildren()[0]
	if childJoint != endJoint:
		delJoint = childJoint
	else:
		delJoint = None
	crvName,crvShapeName,jointList = createCrv(startJoint,endJoint)
	value = crvShapeName.length()
	CurveAbsV = value/(jntNum-1)
	infoNode = createInfoNode(crvShapeName)
	parentJoint = startJoint
	for num in range(1,jntNum-1):
		pm.select(cl =1)
		parameter = crvShapeName.findParamFromLength(CurveAbsV*num)
		infoNode.parameter.set(parameter)
		jntPosition = infoNode.position.get()
		jntName = pm.joint(p =jntPosition)
		pm.joint(parentJoint,e = 1, zso = 1,oj = 'xyz',sao = 'yup')
		parentJoint.addChild(jntName)
		parentJoint = jntName
		pm.refresh()
	parentJoint.addChild(endJoint)
	pm.delete(crvName,delJoint)



startJoint = pm.PyNode("joint1")
endJoint = pm.PyNode("joint2")
makeJoint(startJoint,endJoint,13)


	

'''












	
