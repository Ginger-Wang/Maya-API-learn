# -*- coding: UTF-8 -*-
import maya.cmds as cmds

def mirrorAniWindow():    
    if cmds.window("mirrorAniWindow", ex=True):
        cmds.deleteUI("mirrorAniWindow", window=True)
    cmds.window("mirrorAniWindow", title="mirrorAni")  
    cmds.columnLayout(columnAttach=('both', 5),adjustableColumn=True)
    cmds.text(label = '',align='left',h = 5)
    cmds.button('mirrorTr',label = 'Mirror Translate',c = 'mirrorTr()',h= 30,ann = 'First select HIK Hip joint, Then press the button.....')
    cmds.text(label = '',align='left',h = 5)
    cmds.optionMenu("mirrorAxis", label= "Mirror Axis :",height=30,w = 240)
    for axis in ['X','Y','Z']:               
        cmds.menuItem( l= axis)
        
    cmds.rowLayout('FrowLayoutName',numberOfColumns = 2,columnAttach=[(1, 'both',1), (2, 'both', 1)])
    cmds.columnLayout(adjustableColumn = 1,columnAlign = 'center')   
    cmds.text(label = '',align='left',h = 10)
    cmds.text('SearchTxt',label = 'Search :',align='left',h= 30)
    #cmds.text(label = '',align='left',h = 15)
    cmds.text('ReplaceTxt',label = 'Replace:',align='left',h= 30)
    cmds.setParent('..')
    
    cmds.columnLayout(adjustableColumn = 1,columnAlign = 'center')
    cmds.textField('SearchT',tx = '_left',h = 30,w = 220)
    #cmds.text(label = '',align='left',h = 5)
    cmds.textField('ReplaceT',tx = '_right',h = 30)
    cmds.setParent('..')
    cmds.setParent('..')
    
    rowLayoutName = cmds.rowLayout('rowLayoutName',numberOfColumns = 3,columnAttach=[(1, 'both', 5), (2, 'both', 5), (3, 'both', 5)])
    cmds.columnLayout(adjustableColumn = 1,columnAlign = 'center')
    cmds.button('mirrorandclose',label = 'Mirror', command = 'deletW()',h= 30,w = 80,ann = 'apply and close window ')
    cmds.setParent('..')
    
    cmds.columnLayout(adjustableColumn = 1,columnAlign = 'center')
    cmds.button('applyB',label = 'Apply', command = 'applyMirror()',h= 30,w = 80,ann = 'apply mirror ')
    cmds.setParent('..')
    
    cmds.columnLayout(adjustableColumn = 1,columnAlign = 'center')
    cmds.button('closeB',label = 'Close', command = 'cmds.deleteUI("mirrorAniWindow", window=True)',h= 30,w = 80,ann = 'close Window')
    cmds.setParent('..')
    cmds.setParent('..')
    
    cmds.text(label = '',align='left',h = 5)
    aboutMeTxt = cmds.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
    cmds.window('mirrorAniWindow', edit =True, width = 300,height = 160)
    cmds.showWindow( "mirrorAniWindow" )
    
####apply and close window   
def deletW():
    applyMirror()
    cmds.deleteUI("mirrorAniWindow", window=True)
     

def listaAnimCurves(jntNames,axis):
    animCurves = []
    for jnt in jntNames:
        keyNum = cmds.listConnections(jnt+axis,d = 0, s = 1)
        if keyNum:
            animCurves.append(keyNum[0])
    return animCurves
        
def midMirror(animCurve):
    roAxis = cmds.optionMenu("mirrorAxis",q = 1, v=True)
    if ('_rotate'+roAxis) not in animCurve:
        cmds.select(animCurve, r= 1)
        cmds.scaleKey(scaleSpecifiedKeys= 1, timeScale =1, timePivot= 0 ,floatScale = 1,floatPivot =0 ,valueScale= -1 ,valuePivot= 0)
        
def leftToRight(jntName,animCurve,axis):
    searchAxis = cmds.textField('SearchT',q = 1,tx = 1)
    replaceAxis = cmds.textField('ReplaceT',q = 1,tx = 1)
    midMirror(animCurve)
    connectJnt = jntName.replace(searchAxis,replaceAxis)
    cmds.connectAttr(animCurve+'.output',connectJnt+axis ,f = 1)
    
def rightToLeft(jntName,animCurve,axis):
    searchAxis = cmds.textField('SearchT',q = 1,tx = 1)
    replaceAxis = cmds.textField('ReplaceT',q = 1,tx = 1)
    midMirror(animCurve)
    connectJnt = jntName.replace(replaceAxis,searchAxis)
    cmds.connectAttr(animCurve+'.output',connectJnt+axis ,f = 1)  
    
    
def applyMirror():
    selectedJnt = cmds.ls(sl = 1 )[0]
    cmds.select(selectedJnt,hi = 1)
    jntNames = cmds.ls(sl = 1,type = 'joint')
    cmds.select(jntNames,r = 1)     
    ctrlNames = cmds.ls(sl = 1)
    searchAxis = cmds.textField('SearchT',q = 1,tx = 1)
    replaceAxis = cmds.textField('ReplaceT',q = 1,tx = 1)
    rotateAaxis = ['.rotateX','.rotateY','.rotateZ']
    for axis in rotateAaxis:
        animCurves = listaAnimCurves(ctrlNames,axis)
        for animCurve in animCurves:
            jntName = animCurve.rsplit('_',1)[0]
            if replaceAxis in jntName:
                rightToLeft(jntName,animCurve,axis)
                cmds.rename(animCurve,animCurve.replace(replaceAxis,searchAxis+'A'))
            elif searchAxis in jntName:
                leftToRight(jntName,animCurve,axis)
                cmds.rename(animCurve,animCurve.replace(searchAxis,replaceAxis+'A'))
            else:
                midMirror(animCurve)

    for ax in rotateAaxis:
        animCurvesA = listaAnimCurves(ctrlNames,ax)
        for animCurveA in animCurvesA:
            jntNameA = animCurveA.rsplit('_',1)[0]
            if replaceAxis in jntNameA:
                cmds.rename(animCurveA,animCurveA.replace(replaceAxis+'A',replaceAxis))
            elif searchAxis in jntNameA:
                cmds.rename(animCurveA,animCurveA.replace(searchAxis+'A',searchAxis))
    cmds.select(ctrlNames,r =1)                
                
def mirrorTr():
    roAxis = cmds.optionMenu("mirrorAxis",q = True, v=True)
    hipJnt = cmds.ls(sl = 1)[0]
    trAxis = hipJnt + '_translate'+roAxis
    cmds.select(trAxis,r= 1)
    #cmds.select('Character1_Hips_translateX', r= 1)
    cmds.scaleKey(scaleSpecifiedKeys= 1, timeScale =1, timePivot= 0 ,floatScale = 1,floatPivot =0 ,valueScale= -1 ,valuePivot= 0)
    tName = cmds.listRelatives(hipJnt,p =1)[0]
    cmds.select(tName,r = 1)
    
    
mirrorAniWindow()

