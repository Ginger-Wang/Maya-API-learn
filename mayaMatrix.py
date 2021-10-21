import pymel.core as pm
import math
"""
Maya中的4*4 矩阵代表的含义

Maya中4*4变换矩阵，实际是分为3个4*4矩阵，缩放矩阵（4*4）旋转矩阵（4*4）和位移矩阵（4*4）

而旋转矩阵又可以分为3个4*4矩阵，物体绕X轴旋转x轴矩阵（4*4），物体绕Y轴旋转y轴矩阵（4*4），物体绕Z轴旋转z轴矩阵（4*4）

实际变换矩阵可以理解为: 缩放矩阵 * （旋转矩阵：旋转x轴矩阵*旋转y轴矩阵*旋转z轴矩阵）* 位移矩阵

例子是缩放比例为1,1,1
旋转角度为 21，-45 ，145
位移为 15 ，5,25
"""
sx = 1.0 
sy = 1.0 
sz = 1.0
rx = 21
ry = -45
rz = 145
tx = 15 
ty = 5
tz = 25

mat_scale =[[sx, 0.0, 0.0, 0.0 ],[ 0.0, sy, 0.0, 0.0 ],[ 0.0, 0.0, sz, 0.0 ],[ 0.0, 0.0, 0.0, 1.0 ]]
scaleMatrix = pm.datatypes.Matrix(mat_scale)

cx = math.cos(math.radians(rx))
sx = math.sin(math.radians(rx))
mat_x = [[1.0, 0.0, 0.0, 0.0 ],[ 0.0, cx, sx, 0.0 ],[ 0.0, -sx, cx, 0.0 ],[ 0.0, 0.0, 0.0, 1.0 ]]
roX_Matrix = pm.datatypes.Matrix(mat_x)

cy = math.cos(math.radians(ry))
sy = math.sin(math.radians(ry))
mat_y = [[cy, 0.0, -sy, 0.0 ],[ 0.0, 1.0, 0.0, 0.0 ],[ sy, 0.0, cy, 0.0 ],[ 0.0, 0.0, 0.0, 1.0 ]]
roY_Matrix = pm.datatypes.Matrix(mat_y)

cz = math.cos(math.radians(rz))
sz = math.sin(math.radians(rz))
mat_z = [[cz,sz, 0.0, 0.0 ],[ -sz, cz, 0.0, 0.0 ],[ 0.0, 0.0, 1.0, 0.0 ],[ 0.0, 0.0, 0.0, 1.0 ]]
roZ_Matrix = pm.datatypes.Matrix(mat_z)

mat_rotation = roX_Matrix * roY_Matrix * roZ_Matrix


mat_translation = [[ 1.0, 0.0, 0.0, 0.0 ],[ 0.0, 1.0, 0.0, 0.0 ],[ 0.0, 0.0, 1.0, 0.0 ],[ tx, ty, tz, 1.0 ]]
trMatrix = pm.datatypes.Matrix(mat_translation)

transformMatrix = scaleMatrix * mat_rotation * trMatrix

name = pm.PyNode("pCube1")
name.setMatrix( transformMatrix,objectSpace=1)
