import socket
import struct
import sys
import time

f = open('log_GAF.txt', 'a')
f2 = open('lifetime_GAF.txt','w')
f3 = open('detect_GAF.txt','w')
message = 'step'
multicast_group = ('224.0.0.1', 5005)
num = int(sys.argv[1]) + 1

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

# Create dictionary of nodes containing their states
prev_state = dict()
for i in range(num):
  prev_state['Node-'+str(i+1)] = None

# Number of events detected
num_event = -1

# Continue reading until all nodes are dead
while(True):
  dead = 0
  change = False
  data_list = dict() # Contains the data
  data_state = dict() # Contains the state for comparison
  sent = sock.sendto('step', multicast_group)
  del_list = []
  print 'Sent'
  for i in range(num): 
    data, server = sock.recvfrom(1024)
    # Check if this contains node info or death message
    print data
    val_list = data.split(' ')
    # Check if basestation message
    if len(val_list) == 9 and val_list[1] == 'Basestation':
      # If the number of events has changed, write down in f3 what time and how many events were sensed
      if int(val_list[8]) != num_event:
        num_event = int(val_list[8])
        f3.write('%s %s\n' %(val_list[0],val_list[8]))
      # Remove num of events so that number of columns is 8
      data = ' '.join(val_list[0:8])
    if(val_list[2] == '-1'):
      dead += 1
      print val_list[1],'has died'
    if(val_list[6] == 'True'):
      change = True
    data_list[val_list[1]] = data
    data_state[val_list[1]] = val_list[2]

  # Collected all information
  if(data_state != prev_state or change):
    for key in data_list:
      f.write(data_list[key]+'\n')
    # Update prev_state to not include dead nodes 
    prev_state = data_state
  f2.write(val_list[0]+' '+str(num-dead-1)+'\n')
  # Check if all nodes except basestaion is dead
  if (dead == num - 1):
    break
sent = sock.sendto('quit', multicast_group)
f.close()
f2.close()
f3.close()
sock.close()


