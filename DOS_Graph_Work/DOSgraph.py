import matplotlib.pyplot as plt
import time
from math import log
import matplotlib as mp
from matplotlib.pyplot import draw, show
import numpy as np

def plots(d):

   plt.plot(numLines, d[0], "xb-")
   plt.plot(numLines, d[1], '.r-')
   plt.plot(numLines, d[2], 'g^')
   plt.plot(numLines, d[3], 'ms')
   plt.plot(numLines, d[4], 'ys')
   plt.plot(numLines, d[5], 'ks')

   
   #plt.ylabel("Packets")
   #plt.xlabel("Loops")
   #figure(num=None,, figsize=(20,20), dpi =80
   plt.draw()


data=[]
numLines = 0;
with open ('blah.txt') as input_file:
  for line in input_file:
    text = line.split(',')
    s1 = text[0]
    s2 = text[1]
    s3 = text[2]
    s4 = text[3]
    s5 = text[4]
    s6 = text[5]

    s1=(float(s1))
    s2=(float(s2))
    s3=(float(s3))
    s4=(float(s4))
    s5=(float(s5))
    s6=(float(s6))
    data.append([s1, s2, s3, s4, s5, s6])
    numLines+=1
    
#plt.plot(data)
plt.xlabel('Loops')
plt.ylabel('Packets')
plt.title('DOS Simulation')
plt.plot(data)
plt.show(block=False)
time.sleep(10)
