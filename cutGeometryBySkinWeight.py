# -*- coding: UTF-8 -*-
import re
import time 
import copy
import itertools as itt
import pymel.core as pm

def getContinuousNum(numList):	
	continuousNum = []
	useMethod = lambda x:x[1]-x[0]
	for serialNum,sList in itt.groupby(enumerate(numList),useMethod):
		adList = [i for a,i in sList]
		if len(adList)>1:
			continuousNum.append('[%d:%d]' % (adList[0],adList[-1]))
		else:
			continuousNum.append('[%d]' % adList[0])
	return continuousNum

def loadGeo():
    sels = pm.ls(sl = 1)
    if len(sels) !=1:
        print 'Please select and select only one object...'
    elif len(sels) == 0:
        print 'Please select and select only one object...'
    else:
        pm.textField('geoNameField',e =1,text = str(sels[0]))
    	
'''
def loadGeo():
	sels = pm.ls(sl = 1)    
	textList = ''
	for sel in sels:
		addT = sel+','
		textList += addT
	pm.textField('geoNameField',e =1,text = textList)
'''
def getAllJnt(polyName):    
    skinClu = pm.listHistory(polyName,type = 'skinCluster')[0]
    skinedBones =  skinClu.getInfluence()
    return skinedBones,skinClu 
def maximum(meshName,faceNum,skinCluName):
	faceName = pm.PyNode('%s.f[%d]'%(meshName,faceNum))
	vertices = faceName.getVertices()
	vtxs = ['%s.vtx[%d]'%(meshName,i) for i in vertices]
	weightJnts = pm.skinPercent(skinCluName,vtxs,ib = 0.01,q =1 ,t =None)
	maxWeight = 0
	mWJnt = None
	for jnt in weightJnts:
		for i in vtxs:
			weight = pm.skinPercent(skinCluName,i,ib = 0.01,q =1 ,t =jnt)
			if weight > maxWeight:
				maxWeight = weight
				mWJnt = jnt
	print 'Number %d Face the maximum weight bone is %s'%(faceNum,mWJnt)
	return mWJnt,faceNum

def buildCutGeo():    	
    sTime = time.time()	
    mainCtrl = pm.PyNode('Main')
    if not pm.objExists(mainCtrl+'.Geometry_Level'):
    	pm.addAttr(mainCtrl,ln= 'Geometry_Level',at = 'enum',en = 'Hight:Lower:')
    	mainCtrl.Geometry_Level.set(e = 1,channelBox = 1)
    		
    selection = pm.PyNode(pm.textField('geoNameField',q =1,text = 1))    
    allFaces = pm.ls('%s.f[:]'%selection)  
    faceListNum = [i.indices() for i in allFaces][0]  
    skinedBones,skinClu = getAllJnt(selection)
    faceDict = {}
    for face in faceListNum:	
    	mWJnt,faceNum = maximum(selection,face,skinClu)
    	faceDict[faceNum] = mWJnt
    		
    meshName = pm.duplicate(selection,name = 'CopyThis_Geo')[0]
    shapes = meshName.getShapes()
    if len(shapes)>1:
        if 'Orig' in str(shapes[-1]):
            pm.delete(shapes[-1])
        elif 'Deformed' in str(shapes[-1]):
            print shapes[:-1]
            pm.delete(shapes[:-1])
                                 
    jntDict	= {}
    num = len(skinedBones)	
    for jnt in skinedBones:
        jntDict[jnt] = [i for i in faceDict.keys() if faceDict[i] == jnt]	
        if jntDict[jnt]:
            poly = pm.duplicate(meshName,name = '%s_Geo'%jnt)[0]
            shapeName = poly.getShape()        
            for i in ['tx','ty','tz','rx','ry','rz','sx','sy','sz']:
                attr = pm.PyNode('%s.%s' % (poly,i))
                attr.set(e = True,lock = False)            
            continuousNum = getContinuousNum([i for i in faceListNum if i not in jntDict[jnt]])        
            invertSelectionFaces = [pm.PyNode('%s.f%s'%(shapeName,i)) for i in continuousNum]            
            pm.select(invertSelectionFaces,r = 1)
            pm.delete()
            mainCtrl.Geometry_Level.connect(poly.v,f =1)
            jnt.addChild(poly)
        num -= 1
        if num:
            print('\n%s created geometry finish\n\nThe remaining unacquired bones are %d pieces' % (jnt ,num))	
        else:
            print('\n%s created geometry finish\n\nCreating slice geometry complete......' % jnt)
    reverseNode = pm.createNode('reverse',name = mainCtrl+'_reverse')
    mainCtrl.Geometry_Level.connect(reverseNode.inputX)
    reverseNode.outputX.connect(selection.v,f =1)	
    pm.delete(meshName)
    eTime = time.time()
    mainCtrl.Geometry_Level.set(1)
    pm.select(mainCtrl,r =1)
    print '\n\nThe usage time is %f minutes.'%((eTime-sTime)/60)






def cutGeometryWindow():    
    if pm.window("cutGeometryWindow", ex=True):
        pm.deleteUI("cutGeometryWindow", window=True)
        
    pm.window("cutGeometryWindow", title="cutGeometryWindow V - 1.0")
    layoutName = pm.formLayout()
    copyText = pm.text(label = 'CopyGeometry :',h =25)    
    geoNameField = pm.textField('geoNameField',text = '',h = 25,w = 246)
    loadButton = pm.button('loadButton',label = '^Load Geometry^',h= 30,c = 'loadGeo()')

    buildCutGeoButton = pm.button('buildCutGeoButton', label = 'build CutGeometry',h = 30,c = 'buildCutGeo()')
    #aboutMeTxt = pm.text('aboutMeT',label = 'QQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
    bottomT = pm.text('aboutMeT',label = 'Please contact me if you have any questions!\nQQ&&WeChat: 370871841',backgroundColor=(0.5,0.5,1.0),fn ='fixedWidthFont',h = 30)
    
    
    pm.formLayout(layoutName,e = 1,af = [(copyText,'top',12),(copyText,'left',5),(geoNameField,'top',8),(geoNameField,'right',5),
    								(loadButton,'left',8),(loadButton,'right',5),(buildCutGeoButton,'left',8),(buildCutGeoButton,'right',5),
    								(bottomT,'left',8),(bottomT,'right',5),(bottomT,'bottom',5)],
    								ac = [(geoNameField,'left',5,copyText),(loadButton,'top',5,copyText),(buildCutGeoButton,'top',5,loadButton),
    								(bottomT,'top',5,buildCutGeoButton),(bottomT,'top',5,buildCutGeoButton)])  
    pm.window('cutGeometryWindow', edit =True, width = 240,height = 120)
    pm.showWindow("cutGeometryWindow")

cutGeometryWindow()
