# -*- coding: UTF-8 -*-
import pymel.core as pm

def addAttributes(ctrlName,*attrs):
    for attr in attrs:
        pm.addAttr(ctrlName,ln = attr,at='double',min=0,max=10,keyable = 1)
           
def createTransform(**kwargs):
    transformName = pm.createNode(kwargs['type'],name = kwargs['name'], ss = 1)
    if 'p' in kwargs:
        kwargs['p'].addChild(transformName)
        transformName.t.set(0,0,0)
        transformName.r.set(0,0,0)
    if 'c' in kwargs:
        transformName.addChild(kwargs['c'])
        kwargs['c'].t.set(0,0,0)
    if 'it' in kwargs:
        transformName.inheritsTransform.set(kwargs['it'])
    if 't' in kwargs:
        transformName.t.set(kwargs['t'])           
    if 'r' in kwargs:
        transformName.r.set(kwargs['r'])
    return transformName
def createRootCtrl(name = "Main"):
	pos = [[0.000, 0.000, -5.000],[-1.250, 0.000, -3.750],[-0.626, 0.000, -3.750],
	[-0.600, 0.003, -3.119],[-1.195, 0.000, -2.915],[-1.757, 0.000, -2.651],[-2.233, 0.000, -2.248],
	[-2.633, 0.000, -1.772],[-2.923, 0.000, -1.222],[-3.107, 0.000, -0.627],[-3.750, 0.000, -0.636],
	[-3.750, 0.000, -1.250],[-5.000, 0.000, 0.000],[-3.750, 0.000, 1.250],[-3.750, 0.000, 0.616],
	[-3.108, 0.000, 0.610],[-2.935, 0.000, 1.205],[-2.635, 0.000, 1.753],[-2.254, 0.000, 2.240],
	[-1.765, 0.000, 2.630],[-1.222, 0.000, 2.928],[-0.624, 0.000, 3.106],[-0.626, 0.000, 3.750],
	[-1.250, 0.000, 3.750],[0.000, 0.000, 5.000],[1.250, 0.000, 3.750],[0.626, 0.000, 3.750],
	[0.612, 0.000, 3.108],[1.210, 0.000, 2.932],[1.754, 0.000, 2.637],[2.245, 0.000, 2.249],
	[2.629, 0.000, 1.764],[2.930, 0.000, 1.216],[3.106, 0.000, 0.623],[3.750, 0.000, 0.628],
	[3.750, 0.000, 1.250],[5.000, 0.000, 0.000],[3.750, 0.000, -1.250],[3.750, 0.000, -0.624],
	[3.110, 0.000, -0.615],[2.928, 0.000, -1.211],[2.639, 0.000, -1.761],[2.242, 0.000, -2.240],
	[1.766, 0.000, -2.641],[1.211, 0.000, -2.920],[0.620, 0.000, -3.119],[0.626, 0.000, -3.750],
	[1.250, 0.000, -3.750],[0.000, 0.000, -5.000]]
	ctrlName = pm.curve(p = pos,d = 1,name = name)
	shape = ctrlName.getShape()
	shape.overrideEnabled.set(1)
	shape.overrideColor.set(13)
	return ctrlName
	
def createSplineIKRootCtrl(grp,name = "Test"):
	splineRootCtrl = pm.curve(p=[(0.0, 0.6, 1), (0,1.15, 0), (0, 0.6, -1),(0, -0.6, -1),(0, -1.15, 0), (0, -0.6, 1),(0, 0.6, 1)],d=1,name='{0}RootCtrl'.format(name))
	grp.addChild(splineRootCtrl)
	splineRootCtrl.t.set(0,0,0)
	splineRootCtrl.r.set(0,0,0)
	shape = splineRootCtrl.getShape()
	shape.overrideEnabled.set(1)
	shape.overrideColor.set(6)
	return splineRootCtrl,shape
	
def createcurveCube(name = 'name', num = 1,multiply = 1):
    curveCtrl = pm.circle(c=(0, 0, 0), nr=(1, 0, 0), sw=360, d=3, name='{0}{2}{1:03d}'.format(name, num, 'Ctrl'))[0]
    
    shape = curveCtrl.getShape()
    shape.overrideEnabled.set(1)
    shape.overrideColor.set(18)
    pm.scale(shape.cv[:],multiply,multiply,multiply)    	
    connectGroup = createTransform(type='transform',name = '%s_ConnectGrp'%(curveCtrl))
    zeroGroup = createTransform(type='transform',name = '%s_Grp'%(curveCtrl),p = connectGroup)
    sclGroup = createTransform(type='transform',name = '%s_sclGrp'%(curveCtrl),p = curveCtrl)
    zeroGroup.addChild(curveCtrl)
    return connectGroup,curveCtrl,sclGroup


def getPositions(joints):
    positions = []
    for each in joints:
        position = each.getTranslation('world')
        positions.append(position)
    return positions       

def createIKSplinecurve(ctrlGrp,positions,number,name = 'Test'):
    ro = ctrlGrp.getRotation(worldSpace = 1)
    if number == 2:
        dergee = 1
    elif number == 3:
        dergee = 2
    elif number >= 4:
        dergee = 3    
    curveName,curveShapeName = createCurve(positions,d = 3,name = '%s_solCurve'%(name))    
    ctrlGrp.addChild(curveName)
    curveName.t.set(0,0,0),curveName.r.set(0,0,0)
    cvList = curveShapeName.cv[:]
    indices = cvList.indices()
    pocNumber = len(indices)
    length,curveLength = getIncrement(curveShapeName,number)
    pos = []
    for num in range(number):
        parameter = curveShapeName.findParamFromLength(length*num)
        position = curveShapeName.getPointAtParam(parameter,space = 'world')
        pos.append(position)
        pm.refresh()
    ikCtrlCrv,ikCtrlCrvShape= createCurve(pos,d = dergee,name = '%s_spineIKCtrlCurve'%(name))        
    ctrlGrp.addChild(ikCtrlCrv)
    ikCtrlCrv.t.set(0,0,0),ikCtrlCrv.r.set(0,0,0)
    pocLength,pocCurveLength = getIncrement(ikCtrlCrvShape,pocNumber)
    multiply = pocCurveLength/5.0
    for numb in range(number):
        pmaName,zeroGroup = createIKCtrl(ctrlGrp,name = name,num = numb+1,multiply = multiply)
        #pmaName.input3D[0].input3D.set(pos[num])
        zeroGroup.setTranslation(pos[numb],worldSpace = 1)
        zeroGroup.r.set(ro)
        pmaName.outputTranslate.connect(ikCtrlCrvShape.controlPoints[numb])
    for cv in indices:
        parameter = ikCtrlCrvShape.findParamFromLength(pocLength*cv)
        pocName = createPoc(parameter,ikCtrlCrvShape,'%s_Poc%03d'%(name,cv))
        pocName.position.connect(curveShapeName.controlPoints[cv])
    return [curveName,curveShapeName],[ikCtrlCrv,ikCtrlCrvShape]
         
         
def getIncrement(shape,number):
    curveLength = shape.length() 
    increment = 1.0/(number - 1)
    length = increment*curveLength
    return length,curveLength  
         
def createCurve(positions,d = 3,name = 'Test'):
    curveName = pm.curve(d = d,p = positions,name = name)
    curveShapeName = curveName.getShape()
    curveName.v.set(0)
    curveName.inheritsTransform.set(0)
    return curveName,curveShapeName
         
def createPoc(parameter,shape,name):
    pocName = createTransform(type = 'pointOnCurveInfo',name = name)
    pocName.parameter.set(parameter)
    shape.worldSpace[0].connect(pocName.inputCurve)
    return pocName
           


def createIKCtrl(ctrlGrp,name = 'name', num = 1,multiply = 1):
    pos = [[0.0, 1.0, -1.0], [0.0, 1.0, 1.0], [0.0, -1.0, 1.0], [0.0, -1.0, -1.0], [0.0, 1.0, -1.0]]
    curveSquare = pm.curve(p=pos, d=1, name='{0}{2}{1:03d}'.format(name, num, 'Ctrl'))
    shapes = curveSquare.getShapes()
    
    for shape in shapes:
    	pm.scale(shape.cv[:],multiply,multiply,multiply)
    	shape.overrideEnabled.set(1)
    	shape.overrideColor.set(17)
    zeroGroup = createTransform(type='transform',name = '%s_Grp'%(curveSquare),p=ctrlGrp)
    #zeroGroup.r.set(ro)
    zeroGroup.addChild(curveSquare)
    curveSquare.t.set(0,0,0)
    dpmName = createTransform(type='decomposeMatrix',name='{0}{2}{1:03d}'.format(name, num, 'DPM'))
    curveSquare.worldMatrix[0].connect(dpmName.inputMatrix,f = 1)
    return dpmName,zeroGroup
    

def snapToObject(object,transform):
    tr = object.getTranslation(space = 'world')
    ro = object.getRotation(space = 'world')
    transform.setTranslation(tr,worldSpace = 1)
    transform.setRotation(ro,worldSpace = 1)

def createCondition(shape,name):
    curveInfoName = createTransform(type = 'curveInfo',name = '%s_CI'%(name))
    shape.worldSpace[0].connect(curveInfoName.inputCurve)
    length = shape.length()
    lengthMD = createTransform(type = 'multiplyDivide',name = '%s_MD'%(name))
    lengthMD.operation.set(2)
    lengthMD.input2X.set(length)
    conditionMD = createTransform(type = 'multiplyDivide',name = '%s_conMD'%(name))
    conditionMD.operation.set(1)
    lengthMD.outputX.connect(conditionMD.input2X)
    curveInfoName.arcLength.connect(lengthMD.input1X)
    setRangeName =  createTransform(type = 'setRange',name = '%s_SR'%(name))
    setRangeName.outValueX.connect(conditionMD.input1X)
    setRangeName.oldMaxX.set(10)
    setRangeName.maxX.set(1)
    return setRangeName,conditionMD
    
def creatFkCtrlCondition(range,multiply,ikConTr):    
    position = ikConTr.t.get()
    setRangeName =  createTransform(type = 'setRange',name = '%s_SR'%(ikConTr))  
    conditionName = createTransform(type = 'condition',name = '%s_Condition'%(ikConTr)) 
    range.outValueX.connect(setRangeName.valueX)
    range.outValueX.connect(setRangeName.valueY)
    range.outValueX.connect(setRangeName.valueZ)
    setRangeName.oldMax.set(1,1,1)
    setRangeName.oldMin.set(0,0,0)
    ikConTr.t.connect(setRangeName.max)
    setRangeName.min.set(position)
    conditionName.secondTerm.set(1)
    conditionName.operation.set(3)
    setRangeName.outValue.connect(conditionName.colorIfFalse)
    ikConTr.t.connect(conditionName.colorIfTrue)
    multiply.outputX.connect(conditionName.firstTerm)
    return conditionName

def connectAttributes(source,target,sourceAttrList,targetAttrList):
	for sourcAttr,targetAttr in zip(sourceAttrList,targetAttrList):
		sAttr = pm.PyNode('%s.%s'%(source,sourcAttr))
		tAttr = pm.PyNode('%s.%s'%(target,targetAttr))
		sAttr.connect(tAttr,f = True)

	
	
	
	
	
	
	
name = 'Test'   
number = 3
joints = pm.ls(sl=1)
jntNumber = len(joints)
if pm.objExists("Main"):
	rootCtrl = pm.PyNode("Main")
else:
	rootCtrl = createRootCtrl(name = "Main")
rigRoot = createTransform(type='transform',name = '%s_Group'%(name),p = joints[0])
splineRootCtrl,splineShape = createSplineIKRootCtrl(rigRoot,name = name)
rootCtrl.addChild(rigRoot)
jntGrp = createTransform(type='transform',name = '%s_Jnt_Grp'%(name),p = splineRootCtrl)
ctrlGrp = createTransform(type='transform',name = '%s_CtrlRoot_Grp'%(name),p = splineRootCtrl)
ikConnectGrp = createTransform(type='transform',name = '%s_IK_conGrp'%(name),p = ctrlGrp)
twistGroup = createTransform(type='transform',name = '%s_TwistGroup'%(name),p=ikConnectGrp)
constraintSysterm = createTransform(type='transform',name = '%s_ConstraintSysterm'%(name),p = splineRootCtrl)
#pm.makeIdentity(rigRoot,apply = 1,t=1,r=1,s=1)
#snapToObject(joints[0],rigRoot)
positions = getPositions(joints)
solCurve,ikCtrlCurve = createIKSplinecurve(ctrlGrp,positions,number,name = name)
setRangeName,conditionMD = createCondition(solCurve[0],solCurve[0])
length,curveLength = getIncrement(solCurve[1],jntNumber)
multiply = curveLength/5.0
addAttributes(splineRootCtrl,'switch')
pm.scale(splineShape.cv[:],multiply*1.4,multiply*1.4,multiply*1.4)
parentGrp = None
ikParent = None
for number in range(jntNumber):
    parameter = solCurve[1].findParamFromLength(length*number)
    connectGroup,curveCube,sclGroup = createcurveCube(name = '%s_FK'%(name), num = number+1,multiply = multiply*0.7)
    consIKGrp = createTransform(type='transform',name = 'IK_ConTr%03d'%(number+1),p = joints[number])    
    joints[number].addChild(connectGroup)
    connectGroup.t.set(0,0,0)
    connectGroup.r.set(0,0,0)
    pm.refresh()
    if parentGrp:
        parentGrp.addChild(connectGroup)
    elif parentGrp == None:
        ctrlGrp.addChild(connectGroup)    
    if ikParent:
        ikParent.addChild(consIKGrp)        
    elif ikParent == None:
        ikConnectGrp.addChild(consIKGrp)
    #conditionName.outColor.connect(connectGroup.t)              
    connectAttributes(consIKGrp,connectGroup,['r'],['r'])    
    ikParent = consIKGrp
    parentGrp = curveCube
    consTransformName = createTransform(type='transform',name = 'ConsTr%02d'%(number+1),p = joints[0])
    twistGroup.addChild(consTransformName)
    transformName = createTransform(type='transform',name = 'UpTr%02d'%(number+1),p = joints[0],t = [0,0,multiply*6])
    twistGroup.addChild(transformName)
    connectTransformName = createTransform(type='transform',name = 'ConnectTr%02d'%(number+1),p = ikConnectGrp,it = 0)
    upTrConstraint = pm.parentConstraint(consTransformName,transformName,mo=1,w=1) 
    constraintSysterm.addChild(upTrConstraint)   
    motionPathName = pm.createNode('motionPath',name = 'motionPath%02d'%(number+1),ss= 1)
    motionPathName.frontAxis.set(0)
    motionPathName.upAxis.set(2)
    motionPathName.uValue.set(parameter)
    solCurve[1].worldSpace[0].connect(motionPathName.geometryPath)
    transformName.t.connect(motionPathName.worldUpVector)     
    connectAttributes(motionPathName,connectTransformName,['msg','ro','ac','r'],['sml','ro','t','r'])
    IKGrpConstraint = pm.parentConstraint(connectTransformName,consIKGrp,mo = 1,w =1)
    constraintSysterm.addChild(IKGrpConstraint)
    jntConstraint = pm.parentConstraint(curveCube,joints[number],mo = 1,w =1)
    constraintSysterm.addChild(jntConstraint)
    conditionName = creatFkCtrlCondition(setRangeName,conditionMD,consIKGrp)
    conditionName.outColor.connect(connectGroup.t) 
    if number == 0:
        connectAttributes(consIKGrp,connectGroup,['t'],['t']) 
	
splineRootCtrl.switch.connect(setRangeName.valueX)
jntGrp.addChild(joints[0])
