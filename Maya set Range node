####  setRange node 原理

value = float()
minNum = float()
maxNum = float()
oldMin = float()
oldMax = float()

if oldMin >= value:
  outValue = minNum
elif oldMax <= value:
  outValue = maxNum
else:
  outValue = (maxNum - minNum ) / (oldMax - oldMin) * (value - oldMin) + minNum
