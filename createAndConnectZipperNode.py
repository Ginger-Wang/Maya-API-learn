from maya import cmds
curves = cmds.ls(sl = 1)
targetShape = cmds.listRelatives(curves[0],s = 1)[0]
for cur in curves[1:]:
  shapeName = cmds.listRelatives(cur,s = 1)[0]
  inputCurveShape = cmds.createNode("nurbsCurve",name = "%sOrg"%(shapeName),p = cur,ss = 1)
  cmds.connectAttr("%s.worldSpace[0]"%(shapeName),"%s.create"%(inputCurveShape),f = 1)
  cmds.refresh()
  cmds.disconnectAttr("%s.worldSpace[0]"%(shapeName),"%s.create"%(inputCurveShape))
  zipper = cmds.createNode("newZipperNode")
  cmds.refresh()
  cmds.connectAttr("%s.worldSpace[0]"%(inputCurveShape),"%s.in"%(zipper),f = 1)
  cmds.connectAttr("%s.worldSpace[0]"%(targetShape),"%s.int"%(zipper),f = 1)
  cmds.connectAttr("%s.outc"%(zipper),"%s.create"%(shapeName),f = 1)
  cmds.setAttr("%s.intermediateObject"%(inputCurveShape),1)
  
