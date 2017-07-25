import socket
import struct
import sys
import time

f = open('log.txt', 'w')
f2 = open('lifetime.txt','w')
message = 'step'
multicast_group = ('224.0.0.1', 5005)
num = int(sys.argv[1])

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a timeout so the socket does not block indefinitely when trying
# to receive data.
#sock.settimeout(.1)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

# Create dictionary of nodes containing their states
prev_state = dict()
for i in range(num):
  prev_state['Node-'+str(i+1)] = None

# Continue reading until all nodes are dead
while(len(prev_state)!=0):
  data_list = dict() # Contains the data
  data_state = dict() # Contains the state for comparison
  sent = sock.sendto('step', multicast_group)
  del_list = []
  print 'Sent'
  for i in range(num): 
    try:
      data, server = sock.recvfrom(1024)
    except socket.timeout: 
      pass
    else:
      # Check if this contains node info or death message
      print data
      val_list = data.split(' ')
      if(val_list[2] == '-1'):
        num -= 1
        del_list.append(val_list[1])
        print val_list[1],'has died'
      data_list[val_list[1]] = data
      data_state[val_list[1]] = val_list[2]

  # Collected all information
  #if len(data_state) == len(prev_state):
  if(data_state != prev_state):
    for key in data_list:
      #print data_list[key]
      f.write(data_list[key]+'\n')
    # Update prev_state to not include dead nodes 
    prev_state = data_state
    for key in del_list:
      del prev_state[key]
  f2.write(val_list[0]+' '+str(num)+'\n')
f.close()
f2.close()
'''
# If we have collected all of the information for that time_stamp
if len(data_list) == len(prev_list):
# Print timestamp
print data_list['Node-1'][1]
# Check if states are different
for key in data_list:
  print key
  if(data_list[key][0] != prev_list[key][0]):
    prev_list = data_list
    for key in data_list:
      print key
      #print key,"State:",debug_state[data_list[key][0]],"Energy:",data_list[key][4]
      message = val_list[2]+' '+val_list[0]+' '+val_list[1]+' '+val_list[3]+' '+val_list[4]+' '+val_list[5]
      print message
      #f.write(message)
      pass
    break
'''
sock.close()


