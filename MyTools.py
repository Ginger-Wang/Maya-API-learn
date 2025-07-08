#coding:utf-8
from maya.cmds import *
import pymel.core as pm

def CreatMywindow():    
    if window("JGW_window", ex=True):
        deleteUI("JGW_window", window=True)
    window("JGW_window", title="Jinge.Wang")  
    columnLayout(adjustableColumn=True)
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='Close',w=240, h=30, command=('deleteUI(\"' + "JGW_window" + '\", window=True)'),ann="?????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='Box',w=240, h=30,  command=('polyCube()'),ann="????Box")
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='SkinWrap', w=240, h=30, command=('wrapSkin()'),ann="?????????,??????skin???,????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='MirrorBlend', w=240, h=30, command=('JGw_MirrorBlend()'),ann="??????,???????????????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='ZeroGroup', w=240, h=30, command=('JGw_zeroTransformCmd()'),ann="???????????????????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='CreatFKCtrl', w=240, h=30, command=('CreatFKCtrl()'),ann="????FK??" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='MouthCtrlLoaction', w=240, h=30, command=('wMouthCtrlLoaction()'),ann="??????????,?????Face??" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='CreatMoveCtrl', w=240, h=30, command=('CreatMoveCtrl()'),ann="??????????????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='JntDisType', w=240, h=30, command=('JGwJntDisType()'),ann="??????????,(????????Bone??Box)" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='Scale or Rotate or ColorCtrl', w=240, h=30, command=('scaleCtrl()'),ann="??????????,???????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='SecondaryCtrl', w=240, h=30, command=('secondaryCtrl()'),ann="?????????,???????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='secondaryJointCtrl', w=240, h=30, command=('secondaryJointCtrl()'),ann="?????????,???????" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='Set Smooth', w=240, h=30, command=('setSmoothWindow()'),ann="???????Polygon" )
    text(l="<--------------->",h= 10, fn="fixedWidthFont")
    button( label='ConnectGeometryDisplayType', w=240, h=30, command=('GeomtryDisplayType()'),ann="???????,????" )
    setParent( '..' )
    showWindow( "JGW_window" )
'''
def wrapSkin():
    wSlePoly = ls( sl=True)
    wBone = skinCluster(wSlePoly[len(wSlePoly)-1], q =True, inf=True)
    for wrapSkin in wSlePoly:
        if wrapSkin == wSlePoly[len(wSlePoly)-1]:
            pass
        else:
            skinCluster(wBone,wrapSkin, tsb =True  )
            copySkinWeights(wSlePoly[len(wSlePoly)-1],wrapSkin,  nm=True, sa= 'closestPoint', ia ='closestJoint')
'''

def getChild(polyName):
    childShapes = pm.listRelatives(polyName,ad = 1,shapes = 1)
    childPolys = pm.listRelatives(childShapes,p = 1,type = 'transform')
    if childPolys:
        return childPolys
    else:
        return None    
    
def getSkinClu(polyName):
    skinCluName = pm.listHistory(polyName,type = 'skinCluster')
    if skinCluName:
        return skinCluName[0]
    else:
        return None  

def skinIt(skinedBones,polyName,skinClu): 
    skinCluDS = getSkinClu(polyName)   
    if skinCluDS:
        pm.copySkinWeights(ss=skinClu,ds=skinCluDS,nm=True,sa='closestPoint', ia='closestJoint')    
    else:
        skinCluDS = pm.skinCluster(skinedBones,polyName, tsb =True)
        pm.copySkinWeights(ss=skinClu,ds=skinCluDS,nm=True,sa='closestPoint', ia='closestJoint')

def getAllJnt(polyName):    
    skinClu = pm.listHistory(polyName,type = 'skinCluster')[0]
    skinedBones =  skinClu.getInfluence()

def wrapSkin():    
    selPolys = pm.ls(sl = 1)
    skinClu = pm.listHistory(selPolys[-1],type = 'skinCluster')[0]
    skinedBones = skinClu.getInfluence()
    for polyName in selPolys:
        if polyName != selPolys[-1]:
            childPolys = getChild(polyName)
            if childPolys:
                childs = set(childPolys)
                for childPoly in childs:
                    skinIt(skinedBones,childPoly,skinClu)
            else:
                skinIt(skinedBones,polyName,skinClu)

def JGw_MirrorBlend():
	baseMesh = ls(sl=True)
	base = baseMesh[0]
	mirrorMesh = baseMesh[1]
	copymirrorMesh = duplicate(base,rr=True,name=mirrorMesh+'_L')
	wrapmirrorMesh = duplicate(base,rr=True,name=mirrorMesh+'wrap')
	if objExists('deleteThisGrp'):
		parent(mirrorMesh,copymirrorMesh,wrapmirrorMesh,'deleteThisGrp')
	else:
		deleteGrp = createNode( 'transform', n='deleteThisGrp' )
		parent(mirrorMesh,copymirrorMesh,wrapmirrorMesh,'deleteThisGrp')
	setAttr(wrapmirrorMesh[0]+".scaleX",-1)
	setAttr(wrapmirrorMesh[0]+".v",0)
	blend = blendShape(mirrorMesh,wrapmirrorMesh)
	select(copymirrorMesh,wrapmirrorMesh)
	maya.mel.eval('doWrapArgList "7" { "1","0","1", "2", "1", "1", "1", "1" };')
	setAttr(blend[0]+'.'+mirrorMesh,1)
	Position = xform(mirrorMesh,q=True,worldSpace=True,t=True)
	xform(copymirrorMesh,t=(-Position[0],Position[1],Position[2]))
	xform(wrapmirrorMesh,t=(-Position[0],Position[1],Position[2]))
	xform(wrapmirrorMesh[0]+'Base',t=(-Position[0],Position[1],Position[2]))
	select(baseMesh[1]) 
def JGw_setAttrToZero(_objTransform):    
    _trAttr = ('.tx','.ty','.tz','.rx','.ry','.rz')
    _scAttr = ('.sx','.sy','.sz')
    for i in range(6):
        setAttr(_objTransform+_trAttr[i],0)
    for l in range(3):
        setAttr(_objTransform+_scAttr[l],1)


def JGw_zeroTransform(_zeroObj):
    _nameGrp = group(em=True ,name= _zeroObj+'_Grp#')
    parent( _nameGrp, _zeroObj)
    JGw_setAttrToZero( _nameGrp)
    _parentObj = listRelatives( _zeroObj ,p=True)
    try:
        parent( _nameGrp, _parentObj)
        parent(_zeroObj, _nameGrp)
    except:
        parent(_nameGrp,w= True)
        parent(_zeroObj, _nameGrp)   
            
            
 #??????????????0??#     

def JGw_zeroTransformCmd():
    try:
        JGw_selObj = ls(sl=True)
        for i in JGw_selObj:
           JGw_zeroTransform(i)
    except:
        pass  
        
 ###??FK???###       
def CreatFKCtrl():
    wSelectFKJnt = ls(sl=True)
    for FKJntNub in wSelectFKJnt:
        select(FKJntNub,hi=True) 
        SelectFKJntAll = ls(sl=True,type='joint')
        nameCtrlGrpNew = []
        nameCtrlNew = []
        OffSetNameNew = []
        for selJnt in range(len(SelectFKJntAll)):
            curve(d=1, p =[(-1 ,0, -0.109055),(-1, 0, 0.109055),(-0.307046, 0, 0.307046),(-0.109055, 0, 1 ),( 0.109055, 0, 1),(0.307046, 0, 0.307046),( 1 ,0, 0.109055),( 1, 0, -0.109055),( 0.307046, 0, -0.307046),(0.109055, 0, -1),( -0.109055, 0, -1),( -0.307046, 0, -0.307046),( -1, 0, -0.109055)],k=[0 , 1 , 2 , 3 , 4 , 5 , 6 , 7 ,8 , 9 , 10 , 11 , 12 ])    
            nameCurves = rename(SelectFKJntAll[selJnt].replace('Jnt','FKCtrl'))
            CurvesShape = listRelatives(nameCurves,s=True)
            for shapeID in CurvesShape:
                if nodeType(shapeID) == 'nurbsCurve':
                    setAttr(shapeID+".overrideEnabled",1) 
                    setAttr(shapeID+".overrideColor", 18)
            nameCtrlGrp = group(name= nameCurves+'_Grp0#')
            OffSetName = createNode('transform',name = nameCurves+'Offset') 
            parent(OffSetName,nameCtrlGrp)    
            parent(nameCtrlGrp,SelectFKJntAll[selJnt])
            setAttr(nameCtrlGrp+'.translate',0,0,0)
            setAttr(nameCtrlGrp+'.rotate',0,0,90)
            parent(nameCtrlGrp,w= True)
            constraintOne = parentConstraint(nameCurves,SelectFKJntAll[selJnt],mo=True,w=1)
            if objExists('parentConstraintGrp'):
                 parent(constraintOne,'parentConstraintGrp')
            else:
                createConstraintGrp = createNode( 'transform', n='parentConstraintGrp' )
                parent(constraintOne,createConstraintGrp)   
            connectAttr(nameCurves+'.scale',SelectFKJntAll[selJnt]+'.scale',f = True)

            parent(nameCurves,OffSetName) 
            nameCtrlGrpNew.append(nameCtrlGrp)
            nameCtrlNew.append(nameCurves)
            OffSetNameNew.append(OffSetName)
        for each in range(len(nameCtrlNew)-1):
            parent(nameCtrlGrpNew[each+1],nameCtrlNew[each])
        for i in OffSetNameNew:
        	childrenCtrl = listRelatives(i,c =True)
        	if childrenCtrl[0] != nameCtrlNew[len(nameCtrlNew)-1]:        		
        		connectAttr(nameCtrlNew[len(nameCtrlNew)-1]+'.rotate',i+'.rotate')
###??????            
def wMouthCtrlLoaction():
    maya.mel.eval('''
global proc wMouthCtrlLoaction(){
    string $wMouthMorpher[] = `ls "asFaceBS.A""asFaceBS.E""asFaceBS.V""asFaceBS.M""asFaceBS.O""asFaceBS.U""asFaceBS.S""asFaceBS.Smile""asFaceBS.Sad"`;
    
    if(`objExists "MouthCtrl_Box_Grp"`){
      if(size($wMouthMorpher)== 9 ) {
        connectAttr -f A_Ctrl.connectAttr asFaceBS.A;
        connectAttr -f E_Ctrl.connectAttr asFaceBS.E;
        connectAttr -f V_Ctrl.connectAttr asFaceBS.V;
        connectAttr -f M_Ctrl.connectAttr asFaceBS.M;
        connectAttr -f O_Ctrl.connectAttr asFaceBS.O;
        connectAttr -f U_Ctrl.connectAttr asFaceBS.U;
        connectAttr -f S_Ctrl.connectAttr asFaceBS.S;
        connectAttr -f Smile_Ctrl.connectAttr asFaceBS.Smile;
        connectAttr -f Sad_Ctrl.connectAttr asFaceBS.Sad;
      } 
      else{
          print ("???asFaceBS?????????:\\n" + "A,E,V,M,O,U,S,Smile,Sad");
      }  
    }else{
    file -import -ignoreVersion -ra true -mergeNamespacesOnClash true -namespace ":" -options "v=0;"  -pr "F:/myFile/importFile/KouXing_Ctrl.ma";
    $wloactionCtrlBoxRight = `xform -q -ws -t ctrlBoxShape.cv[0]`;
    $wloactionCtrlBoxUp = `xform -q -ws -t ctrlBoxShape.cv[1]`;
    $wloactionCtrlBoxDown = `xform -q -ws -t ctrlBoxShape.cv[2]`;
    $wloactionMouthCtrl_BoxUp = `xform -q -ws -t MouthCtrl_BoxShape.cv[1]`;
    $wloactionMouthCtrl_BoxDown = `xform -q -ws -t MouthCtrl_BoxShape.cv[0]`;
    float $wLoc = ($wloactionCtrlBoxUp[1] - $wloactionCtrlBoxDown[1])/($wloactionMouthCtrl_BoxUp[1] - $wloactionMouthCtrl_BoxDown[1] );
    setAttr "MouthCtrl_Box_Grp.scaleX" $wLoc;
    setAttr "MouthCtrl_Box_Grp.scaleY" $wLoc;
    setAttr "MouthCtrl_Box_Grp.scaleZ" $wLoc;
    xform -ws -t $wloactionCtrlBoxDown[0] $wloactionCtrlBoxDown[1] $wloactionCtrlBoxDown[2] MouthCtrl_Box_Grp;
    parent MouthCtrl_Box_Grp ctrlBox ;
    $wloactionMouthCtrl_BoxRight = `xform -q -ws -t MouthCtrl_BoxShape.cv[1]`;
    $wloactionDym_Set_BoxLeft = `xform -q -ws -t Dym_Set_BoxShape.cv[0]`;
    $wloactionDym_Set_BoxRight = `xform -q -ws -t Dym_Set_BoxShape.cv[1]`;
    float $wDymLoc = ($wloactionMouthCtrl_BoxRight[0] - $wloactionCtrlBoxRight[0])/($wloactionDym_Set_BoxRight[0] - $wloactionDym_Set_BoxLeft[0] ); 
    setAttr "Dym_Set_Box_Grp.scaleX" $wDymLoc;
    setAttr "Dym_Set_Box_Grp.scaleY" $wDymLoc;
    setAttr "Dym_Set_Box_Grp.scaleZ" $wDymLoc;   
    xform -ws -t $wloactionCtrlBoxRight[0] $wloactionCtrlBoxRight[1] $wloactionCtrlBoxRight[2] Dym_Set_Box_Grp;
    $wloactionMouthCtrl_BoxUp1 = `xform -q -ws -t MouthCtrl_BoxShape.cv[1]`;
    $wloactionMouthCtrl_BoxDown1 = `xform -q -ws -t MouthCtrl_BoxShape.cv[0]`;
    $wloactionDym_Set_BoxLeft = `xform -q -ws -t Dym_Set_BoxShape.cv[0]`;
    $wloactionDym_Set_BoxRight = `xform -q -ws -t Dym_Set_BoxShape.cv[1]`;
    xform -ws -t $wloactionDym_Set_BoxRight[0] $wloactionDym_Set_BoxRight[1] $wloactionDym_Set_BoxRight[2] ctrlBoxShape.cv[1];
    xform -ws -t $wloactionMouthCtrl_BoxDown1[0] $wloactionMouthCtrl_BoxDown1[1] $wloactionMouthCtrl_BoxDown1[2] ctrlBoxShape.cv[2];
    xform -ws -t $wloactionDym_Set_BoxLeft[0] $wloactionDym_Set_BoxLeft[1] $wloactionDym_Set_BoxLeft[2] ctrlBoxShape.cv[0] ctrlBoxShape.cv[4];
    
    parent Dym_Set_Box_Grp ctrlBox ;
      if(size($wMouthMorpher)== 9 ) {
        connectAttr -f A_Ctrl.connectAttr asFaceBS.A;
        connectAttr -f E_Ctrl.connectAttr asFaceBS.E;
        connectAttr -f V_Ctrl.connectAttr asFaceBS.V;
        connectAttr -f M_Ctrl.connectAttr asFaceBS.M;
        connectAttr -f O_Ctrl.connectAttr asFaceBS.O;
        connectAttr -f U_Ctrl.connectAttr asFaceBS.U;
        connectAttr -f S_Ctrl.connectAttr asFaceBS.S;
        connectAttr -f Smile_Ctrl.connectAttr asFaceBS.Smile;
        connectAttr -f Sad_Ctrl.connectAttr asFaceBS.Sad;
      } 
      else{
           print ("???asFaceBS?????????:\\n" + "A,E,V,M,O,U,S,Smile,Sad");
      }
      }
      delete "MouthCtrl_Box" "Dym_Set_Box";
}
wMouthCtrlLoaction;''')
###???????
def CreatMoveCtrl():
	if objExists('Main_Move'):
		print("????????..."+"\n")
		wUpCurves = listRelatives('Main_Move',c = True)
		#print(wUpCurves[1])
		for i in wUpCurves:
			if i == 'Main':
				print("??????..."+"\n")
			else:
				parent('Main','Main_Move')
	else:			
		mainMoveCurve = circle(center=( 0, 0, 0,), nr=( 0 , 1, 0) ,sw= 360 , r = 1 , d = 3 , ut = 0, tol = 0.01, s = 8, ch = 1, name = 'Main_Move')
		setAttr(mainMoveCurve[0] + 'Shape.overrideEnabled' ,1)
		setAttr(mainMoveCurve[0] + 'Shape.overrideColor' ,13)
		mainMoveOffsetCurve = circle(center=( 0, 0, 0,), nr=( 0 , 1, 0) ,sw= 360 , r = 1 , d = 3 , ut = 0, tol = 0.01, s = 8, ch = 1, name = 'Main_Move_Offset')
		setAttr(mainMoveOffsetCurve[0] + 'Shape.overrideEnabled' ,1)
		setAttr(mainMoveOffsetCurve[0] + 'Shape.overrideColor' ,17)
		
		wMainMaxCV = xform('MainShape.cv[5]', q= True , ws = True, t=True)
		wMainMinCV = xform('MainShape.cv[1]', q= True , ws = True, t=True)
		
		wMoveMainMaxCV = xform(mainMoveCurve[0]+'Shape.cv[5]', q= True , ws = True, t=True)
		wMoveMainMinCV = xform(mainMoveCurve[0]+'Shape.cv[1]', q= True , ws = True, t=True)
		
		wScale =  ((wMainMaxCV[2] - wMainMinCV[2])/(wMoveMainMaxCV[2] - wMoveMainMinCV[2]))*1.35
		#print( wScale)
		select(mainMoveCurve[0] +'.cv[*]')
		scale(wScale,wScale,wScale,r=True)
		
		select(mainMoveOffsetCurve[0] +'.cv[*]')
		scale(wScale*1.3,wScale*1.3,wScale*1.3,r=True)
		
		parent('Main', mainMoveCurve[0])
		parent( mainMoveCurve[0],mainMoveOffsetCurve[0])
		parent(mainMoveOffsetCurve[0],'Group')
		
#??????	
def JGwJntDisType():    
    JGwmenuItems = ("Bone","Multi-child as Box","None")
    if window("JGw_JntDisTypewindow", ex=True):
        deleteUI("JGw_JntDisTypewindow", window=True) 
    
    JGw_JntDisTypewindow = window( 'JGw_JntDisTypewindow', title ="??????")
    columnLayout(adjustableColumn=True)
    text( label='?????????',align='center',h= 30, fn="fixedWidthFont" )
    textField('inputTextBox',text='All Joint')
    button(label='SelectJnt By Name',command='selectJnt()',ann='?????,?????????,?????????')
    text(label='',align='center',h= 8)
    optionMenu("JGwType", label= "Draw Style",cc= 'setJnt()',height=30)
    for JGwmenuItem in JGwmenuItems:               
        menuItem( l= JGwmenuItem)
    window('JGw_JntDisTypewindow',edit=True,width=240)
    showWindow("JGw_JntDisTypewindow")
    
def setJnt():
    _JGwJnt_=ls(sl=True)
    for peath in _JGwJnt_:
        JGwType = optionMenu("JGwType", q=True, v=True)
        print(JGwType)        
        if JGwType== "Bone":
            setAttr( peath+".drawStyle", 0)
        if JGwType== "Multi-child as Box":
            setAttr( peath+".drawStyle", 1)    
        if JGwType== "None":
            setAttr( peath+".drawStyle", 2)
def selectJnt():
    inputText=textField('inputTextBox',q=True,text=True)
    if (inputText=='All Joint'):
        select(ls(type='joint'),r=True)
    else:        
        select(ls(inputText+'*',type='joint'),r=True)
def scaleCtrl():
    if window("JGw_scaleCtrlwindow", ex=True):
        deleteUI("JGw_scaleCtrlwindow", window=True)
    scaleCtrlwindow = window('JGw_scaleCtrlwindow', title= "JGw_scaleCtrl" )
    scaleCtrlwindowform = formLayout()
    scaleCtrlText =text(label = 'Scale :',w = 30) 
    JGw_SliderGrp = floatSliderGrp('JGw_SliderNum', field= True, minValue= 0.1, maxValue= 4, value= 1.0,width=285)
    scaleButton = button(label= 'Scale',command='_scale_CVPoint()',width=200,height= 30)
    roXCtrlText =text(label = 'Rotate X:',w = 50) 
    roYCtrlText =text(label = 'Rotate Y:',w = 50) 
    roZCtrlText =text(label = 'Rotate Z:',w = 50) 
    JGw_RoXfloatField = floatField('JGw_RoXSliderGrp',editable=True,w=70,h=30)
    JGw_RoYfloatField = floatField('JGw_RoYSliderGrp',editable=True,w=70,h=30)
    JGw_RoZfloatField = floatField('JGw_RoZSliderGrp',editable=True,w=70,h=30)
    RoXButton = button(label= 'Rotate',command='_rotateX_CVPoint()',height= 27)
    RoYButton = button(label= 'Rotate',command='_rotateY_CVPoint()',height= 27)
    RoZButton = button(label= 'Rotate',command='_rotateZ_CVPoint()',height= 27)
    setColorText = text(label = 'Set Color :',w = 55)
    JGw_Colocrslider = colorIndexSliderGrp('JGw_Colocrslider', min= 1, max= 32, v= 1, cc= "JGw_setColor()",width= 260)
    defaultColorButton = button(label='Default Color',command='JGw_defaultColor()')
    JGw_Dynbutton = button(label='dynamicChainSetupTool', height= 35, command='dynamicChainSetupTool()')
    bottomText = text(label = '',height=5)
    
    formLayout(scaleCtrlwindowform,edit=True,
    af= [(scaleCtrlText,'top',10),
    (scaleCtrlText,'left',5),
    (JGw_SliderGrp,'right',5),
    (JGw_SliderGrp,'top',5),
    (scaleButton,'left',5),
    (roXCtrlText ,'left',5),
    (roYCtrlText ,'left',5),
    (roZCtrlText ,'left',5),
    (RoXButton,'right',5),
    (RoYButton,'right',5),
    (RoZButton,'right',5),
    
    (setColorText,'left',5),
    (scaleButton,'right',5),
    (JGw_Dynbutton,'left',5),
    (JGw_Dynbutton,'right',5),
    (JGw_Colocrslider,'right',5),
    (bottomText,'left',5),
    (defaultColorButton,'left',5)],
    
    ac=[(JGw_SliderGrp,'left',5,scaleCtrlText),
    (scaleButton,'top',8,scaleCtrlText),
    
    (JGw_Colocrslider,'left',5,setColorText),
    (roXCtrlText,'top',15,scaleButton),
    (JGw_RoXfloatField,'left',5,roXCtrlText),
    (JGw_RoXfloatField,'top',5,scaleButton),
    (RoXButton,'top',7,scaleButton),
    (RoXButton,'left',5,JGw_RoXfloatField),
    (roYCtrlText,'top',20,roXCtrlText),
    (JGw_RoYfloatField,'left',5,roXCtrlText),
    (JGw_RoYfloatField,'top',5,JGw_RoXfloatField),
    (RoYButton,'top',7,RoXButton),
    (RoYButton,'left',5,JGw_RoYfloatField),
    
    (roZCtrlText,'top',20,roYCtrlText),
    (JGw_RoZfloatField,'left',5,roYCtrlText),
    (JGw_RoZfloatField,'top',5,JGw_RoYfloatField),
    (RoZButton,'top',7,RoYButton),
    (RoZButton,'left',5,JGw_RoZfloatField),
    
    (setColorText,'top',15,roZCtrlText),
    (JGw_Colocrslider,'top',15,roZCtrlText),
    (defaultColorButton,'top',5,JGw_Colocrslider),
    (JGw_Dynbutton,'top',5,defaultColorButton),
    (bottomText,'top',5,JGw_Dynbutton)])
    
    window('JGw_scaleCtrlwindow',edit=True,width=320,height=135)
    showWindow( 'JGw_scaleCtrlwindow')
    
def _scale_CVPoint():
    try:
        JGw_selObj = ls(sl=True)
        select(clear = True)
        for i in JGw_selObj:
           selectCurveCVs(i)
        select(JGw_selObj,replace=True)
    except:
        pass 


def selectCurveCVs(cvPoint):
    JGw_scale = floatSliderGrp('JGw_SliderNum',q=True,v=True)
    curveShapes = listRelatives(cvPoint,shapes = True)
    for a in curveShapes:
        select(a+'.cv[*]',toggle=True)
        scale(JGw_scale,JGw_scale,JGw_scale,r=True)
        select(clear = True) 

def _rotateX_CVPoint():
    try:
        JGw_selObj = ls(sl=True)
        select(clear = True)
        for i in JGw_selObj:
           JGw_RotateXCttrl(i)
        select(JGw_selObj,replace=True)
    except:
        pass 

def _rotateY_CVPoint():
    try:
        JGw_selObj = ls(sl=True)
        select(clear = True)
        for i in JGw_selObj:
           JGw_RotateYCttrl(i)
        select(JGw_selObj,replace=True)
    except:
        pass 

def _rotateZ_CVPoint():
    try:
        JGw_selObj = ls(sl=True)
        select(clear = True)
        for i in JGw_selObj:
           JGw_RotateZCttrl(i)
        select(JGw_selObj,replace=True)
    except:
        pass 

def JGw_RotateXCttrl(cvPoint):
    JGw_RotateX = floatField('JGw_RoXSliderGrp',q=True,v=True)
    curveShapes = listRelatives(cvPoint,shapes = True)
    for a in curveShapes:
        select(a+'.cv[*]',toggle=True)
        rotate(JGw_RotateX,0,0,r=True)
        select(clear = True) 
    
def JGw_RotateYCttrl(cvPoint):
    JGw_RotateY = floatField('JGw_RoYSliderGrp',q=True,v=True)
    curveShapes = listRelatives(cvPoint,shapes = True)
    for a in curveShapes:
        select(a+'.cv[*]',toggle=True)
        rotate(0,JGw_RotateY,0,r=True)
        select(clear = True) 

def JGw_RotateZCttrl(cvPoint):
    JGw_RotateZ = floatField('JGw_RoZSliderGrp',q=True,v=True)
    curveShapes = listRelatives(cvPoint,shapes = True)
    for a in curveShapes:
        select(a+'.cv[*]',toggle=True)
        rotate(0,0,JGw_RotateZ,r=True)
        select(clear = True)     
         

def dynamicChainSetupTool():
    from dynamicChainSetupTool import dynamicChainSetup as dc 
    dc.show()


def JGw_colorSet(listColor):    
    colorIndex = colorIndexSliderGrp('JGw_Colocrslider', q=True, v=True)
    for setcolorID in listColor:
        if nodeType(setcolorID) == 'nurbsCurve':
            setAttr(setcolorID+'.overrideEnabled', 1)
            setAttr(setcolorID+".overrideColor", (colorIndex - 1))


def JGw_setColor():
    selCurves =ls(sl=True)
    selCurveShape = listRelatives(selCurves, s=True)
    if len(selCurveShape)>0:
        JGw_colorSet(selCurveShape)

def JGw_defaultColor():
    selCurves =ls(sl=True)
    selCurveShape = listRelatives(selCurves, s=True)
    for defaultColor in selCurveShape:
        setAttr(defaultColor+'.overrideEnabled', 0) 
      
        
###???????####
def secondaryCtrl():
    listSel = ls(sl=True)
    select(listRelatives(listSel, p=True),r =True)
    cluster()
    ClusterName = rename("secondaryclusterHandle0#")
    select(listSel,r=True)
    emitter(type= 'omni' ,r =100 ,sro=0 ,nuv= 0,cye= 'none', cyi= 1, spd =1,srn =0 ,nsp =1, tsp= 0 ,mxd= 0,mnd =0 ,dx =1,dy= 0 ,dz= 0,sp =0)
    CrLoc = rename('secondaryemitter0#')
    createNodeGrp = createNode("transform",name = 'second'+ "Attach0#")
    connectAttr(CrLoc + ".translate", createNodeGrp + ".translate",force= True)
    curve( d = 1 ,p=[(-0.5 ,0.5 ,0.5),(0.5, 0.5, 0.5),(0.5, 0.5, -0.5),(-0.5, 0.5, -0.5),
    (-0.5, 0.5, 0.5),(-0.5, -0.5, 0.5),(-0.5, -0.5, -0.5),(0.5, -0.5, -0.5),(0.5, -0.5, 0.5),(-0.5,-0.5, 0.5),
    (0.5, -0.5, 0.5),(0.5, 0.5, 0.5),(0.5, 0.5, -0.5),(0.5, -0.5, -0.5),(-0.5, -0.5, -0.5),(-0.5,0.5, -0.5)], 
    k=[ 0 , 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9 , 10 , 11 , 12 , 13 , 14 , 15])
    curveNeme = rename("secondCtrl0#")
    parent(curveNeme,createNodeGrp)
    setAttr(curveNeme+'.translate',0,0,0)
    setAttr(curveNeme+'.rotate',0,0,0)
    offSetGrp =group(name =curveNeme+"Subtract0#")
    CreatGrp = group(name =curveNeme+"Offset0#")
    plusMinusName = shadingNode('plusMinusAverage',au=True, name=curveNeme+'plusMinusAverage0#')
    setAttr(plusMinusName+".operation", 2)
    connectAttr(curveNeme+".translate",plusMinusName+".input3D[0]",force= True)
    disconnectAttr(curveNeme+".translate",plusMinusName+".input3D[0]")
    connectAttr(curveNeme+".translate",plusMinusName+".input3D[1]",force= True)
    connectAttr(plusMinusName+".output3D",offSetGrp +".translate",force= True)
    connectAttr (curveNeme+".translate",ClusterName+".translate",force= True)
    connectAttr(curveNeme+".rotate",ClusterName+".rotate",force= True)
    connectAttr(curveNeme+".scale",ClusterName+".scale",force= True)
    setAttr(CrLoc+".v", 0)
    setAttr(ClusterName+".v",0)
    setAttr(ClusterName+"Cluster.relative",1)
    GrpCenterPoint=xform(createNodeGrp,q=True,t=True)
    setAttr(ClusterName+'.rotatePivot',GrpCenterPoint[0],GrpCenterPoint[1],GrpCenterPoint[2])
    setAttr(ClusterName+'.scalePivot',GrpCenterPoint[0],GrpCenterPoint[1],GrpCenterPoint[2])
    connectGrp = createNode("transform",name = 'JGwConnectGrp')
    connectAttr(connectGrp+'.rotate' , createNodeGrp+'.rotate',force= True)
    connectAttr(connectGrp+'.scale' , createNodeGrp+'.scale',force= True)
    connectMutiply = createNode( 'multiplyDivide',name = 'JGw_SecondCCDivide0#')
    setAttr(connectMutiply+'.input1',1,1,1)
    connectAttr(connectMutiply+'.output' , connectGrp+'.scale',force= True)
    secomdGrpAll = createNode("transform",name = 'JGw_SeconCtrlGrp0#')
    parent(ClusterName,createNodeGrp,CrLoc,connectGrp,secomdGrpAll)
    select(connectMutiply,replace= True)


def setSmooth():    
	selPoly = ls(sl=True)
	intSliderNub = int(intSliderGrp("intSliderGrpNub",q=True, v=True))
	for allHistory in selPoly:
		smoothFaceReferrer = []    
		polyHistory = listHistory(allHistory)
		for allNodetype in polyHistory:           
			if nodeType(allNodetype)== "polySmoothFace":
				setAttr(allNodetype+".divisions",intSliderNub)
				smoothFaceReferrer.append(allNodetype)				
		if len(smoothFaceReferrer) == 0:			
			polySmooth(allHistory,dv=intSliderNub)
		select(selPoly)

def deleteSmooth():    
    selPoly = ls(sl=True)
    for allHistory in selPoly:    
        polyHistory = listHistory(allHistory)
        for allNodetype in polyHistory:           
            if nodeType(allNodetype)== "polySmoothFace":
                delete(allNodetype)       

def selAllPolyGeo():
    maya.mel.eval('''select -r `listTransforms "-type mesh"`;''')
def setSmoothWindow():
    if window('myWindow',ex=True):
        deleteUI('myWindow')
    window('myWindow', title='Set Smooth By Python-1.0' )
    smoothformLayout = formLayout('smoothformLayout')
    selAllPolyButton = button(label='Select All PolyPolygon',width=308,height=30,command='selAllPolyGeo()')
    smoothTextLabel = text(label = 'Divisions :',w = 60)
    smoothintSliderGrp = intSliderGrp('intSliderGrpNub', field=True,min=1,max=4,fmn=0,fmx=15,v=0 )
    smoothButton = button('smoothButton',label = 'Set Smooth',width= 150,height=30,command='setSmooth()')
    deletesmoothButton = button('deletesmoothButton',label='Delete Smooth',width=150,height=30,command='deleteSmooth()')
    splitLineText = text(label='',height=5)
    formLayout(smoothformLayout,edit=True,
    attachForm=[(selAllPolyButton,"top",10 ),
    (selAllPolyButton,"left",8 ),
    (smoothTextLabel,"left",8 ),
    (smoothButton,"left",8),
    (splitLineText,"left",8),
    (splitLineText,"right",8)],
    attachControl=[(smoothTextLabel,"top",10,selAllPolyButton ),
    (smoothintSliderGrp,"top",8,selAllPolyButton),
    (smoothintSliderGrp,"left",5,smoothTextLabel),
    (smoothButton,"top",8,smoothintSliderGrp),
    (deletesmoothButton,"left",8,smoothButton),
    (deletesmoothButton,"top",8,smoothintSliderGrp),
    (splitLineText,"top",5,deletesmoothButton)])
    window('myWindow',edit=True,width = 310,height=120)
    showWindow( 'myWindow' )
def secondaryJointCtrl():

    listSelvtx = ls(sl=True)
    listSelPolyTranFrom=listRelatives(listSelvtx, p=True)
    listSelvtxPos=xform(listSelvtx[0],q=True,t=True)
    JointName = joint(p=(listSelvtxPos[0],listSelvtxPos[1],listSelvtxPos[2]),name='secondaryJnt0#')
    parent(w=True)
    JGw_zeroTransformCmd()
    CrLoc = spaceLocator( name= "POPLoc0#", p=(0 ,0, 0))  
    select(listSelvtx,CrLoc,r= True)
    maya.mel.eval('doCreatePointOnPolyConstraintArgList 2 {   "0" ,"0" ,"0" ,"1" ,"" ,"1" ,"0" ,"0" ,"0" ,"0" };')
    createNodeGrp = createNode("transform",name = CrLoc[0]+ "_FollowGrp0#")
    connectAttr(CrLoc[0] + ".translate", createNodeGrp + ".translate")
    curve( d = 1 ,p=[(-0.5 ,0.5 ,0.5),(0.5, 0.5, 0.5),(0.5, 0.5, -0.5),(-0.5, 0.5, -0.5),
    (-0.5, 0.5, 0.5),(-0.5, -0.5, 0.5),(-0.5, -0.5, -0.5),(0.5, -0.5, -0.5),(0.5, -0.5, 0.5),(-0.5,-0.5, 0.5),
    (0.5, -0.5, 0.5),(0.5, 0.5, 0.5),(0.5, 0.5, -0.5),(0.5, -0.5, -0.5),(-0.5, -0.5, -0.5),(-0.5,0.5, -0.5)], 
    k=[ 0 , 1 , 2 , 3 , 4 , 5 , 6 , 7 , 8 , 9 , 10 , 11 , 12 , 13 , 14 , 15])
    curveNeme = rename("POPCtrl0#")
    parent(curveNeme,createNodeGrp)
    setAttr(curveNeme+'.translate',0,0,0)
    setAttr(curveNeme+'.rotate',0,0,0)    
    offSetGrp =group(name =curveNeme+"_OffsetGrp0#")
    plusMinusName = shadingNode('plusMinusAverage',au=True, name=curveNeme+"plusMinusAverage0#")
    setAttr(plusMinusName+".operation", 2)
    connectAttr(curveNeme+".translate",plusMinusName+".input3D[0]")
    disconnectAttr(curveNeme+".translate",plusMinusName+".input3D[0]")
    connectAttr(curveNeme+".translate",plusMinusName+".input3D[1]")
    connectAttr(plusMinusName+".output3D",offSetGrp +".translate")
    connectAttr (curveNeme+".translate",JointName+".translate")
    connectAttr(curveNeme+".rotate",JointName+".rotate")
    connectAttr(curveNeme+".scale",JointName+".scale")
    setAttr(CrLoc[0]+".v", 0)
    setAttr(JointName+".v",0)
    skinCluster(listSelPolyTranFrom,edit=True,ai=JointName,lw=True,wt=0)

def GeomtryDisplayType():
    thisCurve = ls(sl=True)
    addAttr(thisCurve[0],ln='DisplayType',at='enum',en='Normal:Template:Reference', defaultValue = 2)
    setAttr(thisCurve[0]+'.DisplayType',e =True,keyable= True)
    polyMesh = ls(type='mesh')
    for displayObj in polyMesh:
        setAttr(displayObj + ".overrideEnabled",1) 
        connectAttr(thisCurve[0]+'.DisplayType',displayObj+".overrideDisplayType",f=True)

 
CreatMywindow()
