# -*- coding: UTF-8 -*-
from maya import OpenMaya,cmds
import pymel.core as pm		
def CreatBoneWindow():    
    if cmds.window("CreatBoneWindow", ex=True):
        cmds.deleteUI("CreatBoneWindow", window=True)
        
    cmds.window("CreatBoneWindow", title="Creat Bone By Curve V-1.0")
    layoutName = cmds.formLayout()
    NumberName = cmds.text('NumberName',label = 'Bone Number:')
    JointNumInt = cmds.intSliderGrp('creatJointNumInt',field = True,min = 2, max = 20,fieldMaxValue =100, w = 240, v =4)
    boneNameText = cmds.text(label = 'Bone Name:',h =25)    
    boneNameField = cmds.textField('creatboneNameField',text = 'myTest',h = 25,w = 246)
    rebiuldChech = cmds.checkBox('rebiuldChech', label='Rebiuld Curve',v = False)
    #hierarchyTxt = cmds.text('hierarchyTxt',label = 'Hierarchy: ')
    radioButtonGrpName = cmds.radioButtonGrp('creatRadioButtonGrpName',numberOfRadioButtons =3,labelArray3 =("FollowCurve","Self", "Hierarchy"),sl = 1)
    creatButton = cmds.button('creatButton',label = 'Creat Bone',h= 30,c = 'biuldJoints()')
    showButton = cmds.button('showButton',label = 'Show Axis',h= 20,c = 'showAxis()')
    hideButton = cmds.button('hideButton',label = 'Hide Axis',h= 20,c = 'hideAxis()')
    creatPcube = cmds.button('creatPcube', label = 'Creat Pcube',h = 30,c = 'creatPcube()')
    aboutMeTxt = cmds.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
    
    
    cmds.formLayout(layoutName,e = 1,
    af = [(NumberName,'top',12),(NumberName,'left',5),(JointNumInt,'top',8),(boneNameText,'left',5),(JointNumInt,'right',5),(boneNameField,'right',5),(rebiuldChech,'left',25),
    (creatButton,'left',5),(creatButton,'right',5),(showButton,'left',5),(hideButton,'right',5),(creatPcube,'left',5),(creatPcube,'right',5),(aboutMeTxt,'left',5)
    ,(aboutMeTxt,'right',5),(aboutMeTxt,'bottom',5),(radioButtonGrpName,'left',15)],    
    ac = [(JointNumInt,'left',5,NumberName),(boneNameField,'top',6,JointNumInt),(boneNameText,'top',15,NumberName),(boneNameField,'left',5,boneNameText),(rebiuldChech,'top',6,boneNameText)
    ,(radioButtonGrpName,'top',5,rebiuldChech),
    (creatButton,'top',5,radioButtonGrpName),(showButton,'top',5,creatButton),(hideButton,'top',5,creatButton),(creatPcube,'top',5,hideButton),(aboutMeTxt,'top',3,creatPcube)],    
    ap = [(showButton,'right',2.5,50),(hideButton,'left',2.5,50)])
         
    cmds.window('CreatBoneWindow', edit =True, width = 240,height = 120)
    cmds.showWindow("CreatBoneWindow")

CreatBoneWindow()

def reBuCrv(crvName,jntNum):
        pm.rebuildCurve(crvName,ch =1,rpo =1,rt =0,end =1,kr =0,kcp =0,kep =1,kt =0,s = jntNum,d= 3,tol =0.01 )
        crvShapeName = crvName.getShapes()
        return crvShapeName
        
def toMObject(node):
    selectionList = OpenMaya.MSelectionList()
    selectionList.add(node)
    obj = OpenMaya.MObject()
    selectionList.getDependNode(0, obj)    
    return obj
    
def toMDagPath(node):
    obj = toMObject(node)
    if obj.hasFn(OpenMaya.MFn.kDagNode):
        dag = OpenMaya.MDagPath.getAPathTo(obj)
        return dag
def asMFnNurbsCurve(curveName):
    dag = toMDagPath(curveName)
    nurbsCurveFn = OpenMaya.MFnNurbsCurve(dag)
    return nurbsCurveFn
    
def createPointOnCurve(curve,name,jointNum):
	mFnCurve = asMFnNurbsCurve(curve)
	increment = 1.0 / (jointNum - 1)
	if cmds.getAttr("{0}.form".format(curve)) == 2:
		increment = 1.0 / (jointNum)	
	pointOnCurves = []
	suffix = ''
	for i in range(jointNum):
		parameter = mFnCurve.findParamFromLength(mFnCurve.length() * increment * i)
		poc = cmds.createNode('pointOnCurveInfo',name = '{0}{1:03d}_poc{2}'.format(name,i+1,suffix))
		cmds.setAttr('{0}.parameter'.format(poc),parameter)
		pointOnCurves.append(poc)
	return pointOnCurves
	#createPointOnCurve('curve1','myTest',5)	

def createFourByFourM(name,jointNum):
	fourByFourMatrixs = []
	suffix = ''
	for i in range(jointNum):
		fbm = cmds.createNode('fourByFourMatrix',name = '{0}{1:03d}_fbm{2}'.format(name,i+1,suffix))
		fourByFourMatrixs.append(fbm)
	return fourByFourMatrixs
	#createFourByFourM('myTest',5)	

def createDecomposeM(name,jointNum):
	decomposeMatrixs = []
	suffix = ''
	for i in range(jointNum):
		dpm = cmds.createNode('decomposeMatrix',name = '{0}{1:03d}_dpm{2}'.format(name,i+1,suffix))
		decomposeMatrixs.append(dpm)
	return decomposeMatrixs
	#createDecomposeM('myTest',5)	

def createJoint(name,jointNum):
	suffix = ''
	joints = []
	for i in range(jointNum):
		cmds.select(cl =1)
		jnt = cmds.joint(p = [0,0,0],name ='{0}{1:03d}_Jnt{2}'.format(name,i+1,suffix))
		joints.append(jnt)
	return joints
	#createJoint('myTest',5)

def connectAtr(outObject,inObject,outputAttrs,inputAttrs):
	for output,input in zip(outputAttrs,inputAttrs):
		cmds.connectAttr("{0}.{1}".format(outObject,output), "{0}.{1}".format(inObject,input) ,f = 1)
	
def connectPoc2Fbm(pointOnCurves,fourByFourMatrixs):
	for poc,fbm in zip(pointOnCurves,fourByFourMatrixs):
		connectAtr(poc,fbm,['px','py','pz','ntx','nty','ntz'],['in30','in31','in32','in00','in01','in02'])
		#pointOnCrv.normalizedTangent.normalizedTangentX.connect(fourByFourM.in00)
		cmds.setAttr('{0}.in11'.format(fbm),1)
	'''
pointOnCurves = createPointOnCurve('curve1','myTest',5)
fourByFourMatrixs = createFourByFourM('myTest',5)	
connectPoc2Fbm(pointOnCurves,fourByFourMatrixs)
	'''
	
def connectFbm2dpm(fourByFourMatrixs,decomposeMatrixs):
	for fbm,dpm in zip(fourByFourMatrixs,decomposeMatrixs):
		cmds.connectAttr('{0}.output'.format(fbm),'{0}.inputMatrix'.format(dpm),f = 1)
	'''
fourByFourMatrixs = createFourByFourM('myTest',5)
decomposeMatrixs = createDecomposeM('myTest',5)	
connectFbm2dpm(fourByFourMatrixs,decomposeMatrixs)
	'''
def connectDpm2Jnt(decomposeMatrixs,joints):
	#value = cmds.radioButtonGrp('creatRadioButtonGrpName',q =True,sl = 1)
	for dpm,jnt in zip(decomposeMatrixs,joints):
		cmds.connectAttr('{0}.outputRotate'.format(dpm),'{0}.jo'.format(jnt),f = 1)
		cmds.connectAttr('{0}.outputTranslate'.format(dpm),'{0}.translate'.format(jnt),f = 1)
		cmds.refresh()
'''		
joints = createJoint('myTest',5)
decomposeMatrixs = createDecomposeM('myTest',5)	
connectDpm2Jnt(decomposeMatrixs,joints)
'''

def connectCrv2Poc(courveName,name,jointNum):	
	pointOnCurves = createPointOnCurve(courveName,name,jointNum)
	for poc in pointOnCurves:
		cmds.connectAttr("{0}.worldSpace".format(courveName),"{0}.inputCurve".format(poc))
	fourByFourMatrixs = createFourByFourM(name,jointNum)
	decomposeMatrixs = createDecomposeM(name,jointNum)
	joints = createJoint(name,jointNum)
	connectPoc2Fbm(pointOnCurves,fourByFourMatrixs)
	connectFbm2dpm(fourByFourMatrixs,decomposeMatrixs)
	connectDpm2Jnt(decomposeMatrixs,joints)
	obj2delete = decomposeMatrixs+fourByFourMatrixs+pointOnCurves
	return joints,obj2delete
	
'''
connectCrv2Poc('curve1','myTest',5)	
if not cmds.objExists(jointName+'JointGroup'):
	jntGrp = cmds.createNode('transform',name = jointName+'JointGroup')
joints = connectCrv2Poc('curve1','myTest',5)	
cmds.parent(joints,'JointGroup')



'''
def biuldJoints():
	rebuildcheck = cmds.checkBox('rebiuldChech', q=1,v = True)
	jointNum = cmds.intSliderGrp('creatJointNumInt',q = 1,v =1)
	jointName = cmds.textField('creatboneNameField',q = 1,tx = 1)	
	crvName = cmds.ls(sl = 1)	
	if not cmds.objExists(jointName+'JointGroup'):
		jntGrp = cmds.createNode('transform',name = jointName+'JointGroup')
	jntGrp = '{}JointGroup'.format(jointName)	
	for crv in crvName:
		joints,obj2delete = connectCrv2Poc(crv,jointName,jointNum)
		cmds.parent(joints,jntGrp)
		value = cmds.radioButtonGrp('creatRadioButtonGrpName',q =True,sl = 1)
		if value != 1:
			cmds.delete(obj2delete)
			if value == 3:
				for jntName in [pm.PyNode(i) for i in joints[:-1]]:
					num = joints.index(str(jntName))
					jntName.addChild(joints[num+1])
					#cmds.joint("myTest002_Jnt",e = 1, zeroScaleOrient = 1,orientJoint="xyz",secondaryAxisOrient="yup")
					pm.joint(jntName,e = 1, zeroScaleOrient = 1,orientJoint="xyz",secondaryAxisOrient="yup")
				cmds.select(joints[0],r = 1)
			#print obj2delete
 

def showAxis():    
    all_selected = pm.ls(sl =1)
    for jnt in all_selected:    
        jnt.displayLocalAxis.set(True)
        jnt.displayHandle.set(1)
        
def hideAxis(): 
    all_selected = pm.ls(sl =1) 
    for jnt in all_selected:    
        jnt.displayLocalAxis.set(False)
        jnt.displayHandle.set(0)
 
def creatPcube():
    all_name = pm.ls(sl = 1)
    PCNames = []
    for name in all_name:        
        PCName,PCShapeName = pm.polyCube(w = 0.8,h = 0.2,d = 0.2,name = name+'pBC0#')
        name.addChild(PCName)
        PCName.t.set(0,0,0)
        PCName.r.set(0,0,0)
        PCNames.append(PCName)
	pm.select(PCNames,r = 1)        






