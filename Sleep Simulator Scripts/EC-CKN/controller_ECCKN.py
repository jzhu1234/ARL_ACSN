import socket
import struct
import sys
import time

f = open('log_ECCKN.txt', 'a')
f2 = open('lifetime_ECCKN.txt','w')
f3 = open('detect_ECCKN.txt','w')
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
  data_list = dict() # Contains the data
  data_state = dict() # Contains the state for comparison
  dead = 0
  write = False
  # Data 
  sent = sock.sendto('step', multicast_group)
  print 'Sent'
  for i in range(num): 
    data, server = sock.recvfrom(1024)
    # Check if this contains node info or death message
    print data
    # Check whether it is useful information or continue
    if data != 'Continue':
      write = True
      val_list = data.split(' ')
      if len(val_list) == 9 and val_list[1] == 'Basestation':
        # If the number of events has changed, write down in f3 what time and how many events were sensed
        if int(val_list[8]) != num_event:
          num_event = int(val_list[8])
          f3.write('%s %s\n' %(val_list[0],val_list[8]))
        # Remove num of events so that number of columns is 8
        data = ' '.join(val_list[0:8])
      # Check how many nodes are dead
      if val_list[2] == '-1':
        dead += 1
      # Append data to data_list to be written into log file
      data_list[val_list[1]] = data
     
  if (write):  
    for key in data_list:
      f.write(data_list[key]+'\n')
    f2.write(val_list[0]+' '+str(num-dead)+'\n')
    # Check if all nodes are dead
    if dead == (num-1):
      break
# Tell all nodes to stop
sent = sock.sendto('quit', multicast_group)

# Close all sockets
f.close()
f2.close()
sock.close()


