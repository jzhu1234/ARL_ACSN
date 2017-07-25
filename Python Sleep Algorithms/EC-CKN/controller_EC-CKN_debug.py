import socket
import struct
import sys
import time


message = 'step'
multicast_group = ('224.0.0.1', 5005)
num = int(sys.argv[1])

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

sent = sock.sendto('step', multicast_group)
 
for i in range(num): 
  data, server = sock.recvfrom(1024)
  # Check if this contains node info or death message
  print data

# Close all sockets
sock.close()


