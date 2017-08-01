import random

area_x = 50
area_y = 50

def event_gen():
  fe = open('event_CKN.txt','w')
  fl = open('log_CKN.txt','w')
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
      fe.write(str(time)+' '+str(eventid)+' '+str(pos[0])+' '+str(pos[1])+'\n')  
      # Log.txt
      fl.write(str(time)+' Event-'+str(eventid)+' 3 '+str(pos[0])+' '+str(pos[1])+' 0 False\n')
      eventid += 1
  fe.close()
  fl.close()      
  
