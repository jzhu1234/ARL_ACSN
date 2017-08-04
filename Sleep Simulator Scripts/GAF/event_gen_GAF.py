import random

area_x = 50
area_y = 50

def event_gen():
  fe = open('event_GAF.txt','w')
  fl = open('log_GAF.txt','w')
  # Generate events
  num = random.randrange(100,150,1)
  events = []
  eventid = 1
  for i in range(num):
    time = random.random()*80
    pos = [random.random()*area_x,random.random()*area_y]
    #pos = [25,25]
    # Event.txt
    fe.write("%0.3f %d %f %f\n" %(time,eventid,pos[0],pos[1]))  
    # Log.txt
    fl.write("%0.2f Event-%d 3 %f %f 0 False Event\n" %(time,eventid,pos[0],pos[1]))
    eventid += 1
  fe.close()
  fl.close()      

