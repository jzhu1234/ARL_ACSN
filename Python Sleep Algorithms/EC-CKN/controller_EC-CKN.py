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

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

# Create dictionary of nodes containing their states
prev_state = dict()
for i in range(num):
  prev_state['Node-'+str(i+1)] = None

cont = True

# Continue reading until all nodes are dead
while(cont):
  data_list = dict() # Contains the data
  data_state = dict() # Contains the state for comparison
  dead = 0
  # Data 
  sent = sock.sendto('step', multicast_group)
  print 'Sent'
  for i in range(num): 
    data, server = sock.recvfrom(1024)
    # Check if this contains node info or death message
    print data
    # Check whether it is useful information or continue
    if data != 'Continue':
      val_list = data.split(' ')
      data_list[val_list[1]] = data
      data_state[val_list[1]] = val_list[2]
      if val_list[2] == '-1':
        dead += 1
      # Check if number of data matches with
      if len(data_state) == len(prev_state):
        if(data_state != prev_state):
          for key in data_list:
            f.write(data_list[key]+'\n')
          prev_state = data_state
        f2.write(val_list[0]+' '+str(num-dead)+'\n')
        # Check if all nodes are dead
        if dead == num:
        #if all(value == '-1' for value in prev_state.values()):
          cont = False
# Tell all nodes to stop
sent = sock.sendto('quit', multicast_group)

# Close all sockets
f.close()
f2.close()
sock.close()


