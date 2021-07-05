# -*- coding: UTF-8 -*-
import pymel.core as pm

def loadObject(side):
    sels = pm.ls(sl = 1)
    if len(sels) !=1:
        print 'Please select and select only one object...'
    elif len(sels) == 0:
        print 'Please select and select only one object...'    	    	
    else:
        pm.textField('objectName%sField'%(side),e =1,text = str(sels[0]))
        
def loadWeapon(side):
	sels = pm.ls(sl = 1)
	if len(sels) !=1:
		print 'Please select and select only one object...'
	elif len(sels) == 0:
		print 'Please select and select only one object...'
	else:
		parentConstraintName = getConstrain(sels[0])
		pm.textField('objectName%sField'%(side),e =1,text = str(parentConstraintName))


def getConstrain(constraint):
	connections = constraint.connections(source = True)
	parentConstraintName = None
	connectionsNew = list(set(connections))
	for constraint in connectionsNew:
		connectType = pm.nodeType(constraint)
		if connectType == 'parentConstraint':
			parentConstraintName = constraint
			#print connectType
	return parentConstraintName

def constrainWeight(constrainL,constrainR,parentConstraintName):
	weightList = parentConstraintName.getWeightAliasList()
	constrainLWeight = None
	constrainRWeight = None
	for weightName in weightList:
		handcons = weightName.split('.')[-1]
		sourceCons = handcons.split('W')[0]
		if sourceCons == constrainL:
			constrainLWeight = weightName
		elif sourceCons == constrainR:
			constrainRWeight = weightName
	return constrainLWeight,constrainRWeight


def setKey(constrainA,constrainB,parentConstraintName,constrainWeights):	
	frameTr = 'targetOffsetTranslate'
	frameRo = 'targetOffsetRotate'
	pm.parentConstraint(constrainA,constrainB,parentConstraintName,e = True,maintainOffset = True)
	parentConstraintName.enableRestPosition.set(0)
	pm.setKeyframe(constrainWeights,ott = 'step')
	pm.setKeyframe('%s.tg[0].%s'%(parentConstraintName,frameRo),'%s.tg[1].%s'%(parentConstraintName,frameRo),ott = 'step')
	pm.setKeyframe('%s.tg[0].%s'%(parentConstraintName,frameTr),'%s.tg[1].%s'%(parentConstraintName,frameTr),ott = 'step')



def getObjectName():
	name_L = pm.textField('objectNameLField',q =1,text = 1)
	name_R = pm.textField('objectNameRField',q =1,text = 1)
	name_Cons = pm.textField('objectNameConsField',q =1,text = 1) 
	return name_L,name_R,name_Cons

def getValue():
	value_L = pm.checkBox('localBox',q= 1,v = 1)
	value_R = pm.checkBox('localRBox',q= 1,v = 1)
	return value_L,value_R

def transferConstraint():
	leftCtrl = pm.PyNode(getObjectName()[0])
	rightCtrl = pm.PyNode(getObjectName()[1])
	parentConstraintName = pm.PyNode(getObjectName()[2])
	constrainWeights = constrainWeight(leftCtrl,rightCtrl,parentConstraintName)
	pm.currentTime( pm.currentTime(query = True) - 1, update=False, edit=True )
	setKey(leftCtrl,rightCtrl,parentConstraintName,constrainWeights)
	pm.currentTime( pm.currentTime(query = True) + 1, update=False, edit=True )
	setKey(leftCtrl,rightCtrl,parentConstraintName,constrainWeights)
	value = getValue()
	constrainWeights[0].set(value[0])
	constrainWeights[1].set(value[1])
	pm.setKeyframe(constrainWeights,ott = 'step')
  
  
  
    
def transferConstraintWindow():	
    if pm.window("transferConstraintWindow", ex=True):
        pm.deleteUI("transferConstraintWindow", window=True)
        
    pm.window("transferConstraintWindow", title="Transfer Constraint V - 1.0")
    layoutName = pm.formLayout()
    leftCtrlButton = pm.button(label = 'LeftCtrl :',h =25,w = 80,c= 'loadObject("L")')      
    objectNameLField = pm.textField('objectNameLField',text = '',h = 25,w = 120)
    followCheckBox = pm.checkBox('localBox',l = 'Follow This')
    
    rightCtrlButton = pm.button(label = 'RightCtrl :',h =25,w = 80,c= 'loadObject("R")')      
    objectNameRField = pm.textField('objectNameRField',text = '',h = 25,w = 120)
    followRCheckBox = pm.checkBox('localRBox',l = 'Follow This')
        
    constraintButton = pm.button(label = 'Weapon :',h =25,w = 80,c = 'loadWeapon("Cons")')      
    objectNameConsField = pm.textField('objectNameConsField',text = '',h = 25,w = 120)
    setKeyframeButton = pm.button(label = 'Transfer Constraint',h = 30,c = 'transferConstraint()')
    aboutMeTxt = pm.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)

    
    
    pm.formLayout(layoutName,e = 1,
    af = [(leftCtrlButton,'top',8),(leftCtrlButton,'left',8),(followCheckBox,'top',16),(objectNameLField,'top',8),(rightCtrlButton,'left',8),
    (aboutMeTxt,'bottom',5),(aboutMeTxt,'left',8),(aboutMeTxt,'right',8),(constraintButton,'left',8),(objectNameConsField,'right',5),
    (setKeyframeButton,'left',8),(setKeyframeButton,'right',8),(objectNameLField,'right',100),(objectNameRField,'right',100)],
    ac = [(followCheckBox,'left',5,objectNameLField),(objectNameLField,'left',5,leftCtrlButton),(rightCtrlButton,'top',5,leftCtrlButton),
    (objectNameRField,'top',5,leftCtrlButton),(followRCheckBox,'top',12,followCheckBox),(objectNameRField,'left',5,rightCtrlButton),
    (followRCheckBox,'left',5,objectNameRField),(objectNameConsField,'left',5,constraintButton),(constraintButton,'top',5,rightCtrlButton),
    (objectNameConsField,'top',5,objectNameRField),(setKeyframeButton,'top',5,constraintButton),(aboutMeTxt,'top',2,setKeyframeButton)])
      
    pm.window('transferConstraintWindow', edit =True, width = 240,height = 120)
    pm.showWindow("transferConstraintWindow")

transferConstraintWindow()
'''
maya 2018 环境中测试
2020年3月17日完成
'''


