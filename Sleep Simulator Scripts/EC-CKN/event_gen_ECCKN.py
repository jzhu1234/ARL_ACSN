import random

area_x = 50
area_y = 50

def event_gen():
  fe = open('event_ECCKN.txt','w')
  fl = open('log_ECCKN.txt','w')
  # Generate events
  num = random.randrange(40,50,1)
  events = []
  eventid = 1
  for i in range(num):
    inst = random.randrange(0,4,1)
    for j in range(inst):
      pos = [random.random()*area_x,random.random()*area_y]
      time = i
      # Event.txt
      fe.write("%d %d %f %f\n" %(time,eventid,pos[0],pos[1]))  
      # Log.txt
      fl.write("%d Event-%d 3 %f %f 0 False Event\n" %(time,eventid,pos[0],pos[1]))
      eventid += 1
  fe.close()
  fl.close()      
  
