import random

##双色球生成器
def getNumber(numberLisr):
    num = random.randint(1,33)
    if num in numberLisr:
        num = getNumber(numberLisr)        
    return num    

def getBallNum():
    redBall = []
    num = 0
    while num < 6:
        intNum = getNumber(redBall)
        redBall.append(intNum)
        num +=1
        
    if len(set(redBall)) < 6:
        print(redBall)
    blueBall = random.randint(1,16)
    return [sorted(redBall),blueBall]


number = 0
selection = []
while number < 100:
    sel = getBallNum()
    number += 1
    print(sel)
