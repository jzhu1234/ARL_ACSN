import multiprocessing
import socket
import time
from random import random, uniform
import sys
import math
import struct
import logging
import logging.handlers


UDP_PORT = 5005
# Initialize global variables. Will be overwritten by arguments
r = 0
num = 0       # Number of nodes in network
area_x = 0    # Width of area
area_y = 0    # Height of area

# How much time we step through
iter_per = 0.01
# Energy Model Parameters
E_fs = 10**-10 #pJ/bit/m^2
E_mp = 0.0013*10**-12 #pJ/bit/m^4
E_elec = 50*10**-9 #nJ/bit
d_thresh = 87.7058 #m

######################################
# Node Class
######################################

class Node(multiprocessing.Process):
  Td_max = .5 #It stays in discovery mode a maximum .5 second
  sample_rate = 0.5 # 1 sample per 2 seconds
  def __init__(self, node_info, neighbor_info):
    # Set up various characteristics about the node
    multiprocessing.Process.__init__(self)
    self.pos = node_info[0]
    self.ip = node_info[1]
    self.neighbors = neighbor_info
    # Give the node a random amount of energy between 1.9 and 2.1 J
    #self.energy = 1.9 + random()*.2 #15,390 J
    self.energy = 0.01 + random()*.0001
    # Calculate estimated node lifetime
    self.ene_cons = self.calc_energy("transmit",1000) + self.calc_energy("receive",1000)*4
    
    # Node State
    # -1 = Dead, 0 = Sleep, 1 = Discovery, 2 = Awake
    self.state = 2
    self.timestamp = 0
    self.time_left = uniform(iter_per,self.Td_max)
    
    # Used to store time when broadcast messages should be sent while transmitting
    self.act_iter = 0
    
    print self.name,"X:",self.pos[0],"Y:", self.pos[1],"E:", self.energy

  def calc_energy(self,mode,load):
    if(mode=="transmit"):
      # Multipath fading
      if(r > d_thresh):
        return E_mp*load*(r**4) + E_elec*load
      # Shadow fading
      else:
        return E_fs*load*(r**2) + E_elec*load
    elif(mode=="receive"):
      return E_elec*load

  def run(self):
    self.setup()
    
    # Receive packets from controller socket
    while(True):
      data, address = self.contr_sock.recvfrom(1024)
      if(data == "step"):
        if(self.energy > 0):
          # Create message
          message = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+" "+str(self.pos[1])+" "+str(self.energy)
          # Step through current time period
          self.step()
          # Send message
          try:
            self.contr_sock.sendto(message, address)
            #print message
          except:
            print "Unexpected error:", sys.exc_info()[0]
            raise
        else:
          self.state = -1
          message = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+" "+str(self.pos[1])+" "+str(self.energy)
          try:
            #print self.name, 'Died'
            self.contr_sock.sendto(message, address)
          except:
            print "Unexpected error:", sys.exc_info()[0]
            raise
          break
      elif(data == "quit"):
        break

    # Close all sockets
    self.ownsock.close()
    for sock in self.neighbor_socks:
      sock.close()
    self.contr_sock.close()

  def step(self):
    self.timestamp += iter_per

    if(self.state==2):
      # Energy taken to transmit packets
      #self.energy -= 0.5
      self.act_iter -= iter_per

      # If self.act_iter is less than one, then we broadcast energy
      if(self.act_iter <= 0):
        self.transmit()
        self.act_iter = uniform(iter_per,self.Td_max)
      
      # Listen for broadcast messages from higher ranked nodes
      data = self.receive()
      

  def check_package(self,packages):
    r_blk = r/math.sqrt(5)
    blockx = self.pos[0]//r_blk
    blocky = self.pos[1]//r_blk
    # Check if neighbors have rank
    for msg in packages:
      node, timestamp, x, y, energy, state = msg.split("_")
      x = float(x)
      y = float(y)
      energy = float(energy)
      state = int(state)
      own_blockx = x//r_blk
      own_blocky = y//r_blk
      # Check if valid message and if is not from the past or future
      if(timestamp == str(self.timestamp)):
        # Check if neighbor is in the same block
        if(own_blockx == blockx and own_blocky == blocky): 
          #if(int(state) < self.state):
          if(energy > self.energy):
            # Go to sleep
            self.state = 0
            return
          '''
          elif (int(state) == self.state):
            if(energy > self.energy):
              # Go to sleep
              self.state = 0
              return 
          '''
      else:
        print self.name, "My timestamp", self.timestamp
        print self.name, "Message timestamp", timestamp
    return 
    
  def setup(self):
    # Setup Neighbor Subscriber sockets
    self.neighbor_socks = []
    host = socket.gethostname()

    for multicast_group in self.neighbors:
      # Create the socket
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      # Bind to the server address
      sock.bind((multicast_group, UDP_PORT))
      sock.settimeout(.05)
      group = socket.inet_aton(multicast_group)
      mreq = struct.pack('4sL', group, socket.INADDR_ANY) 
      sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
      
      self.neighbor_socks.append(sock)

    # Setup Publisher Socket
    self.ownsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.ownsock.settimeout(.05)
    multicast_group = (self.ip, UDP_PORT)
    # Set the time-to-live for messages to 1 so they do not go past the local network segment.
    ttl = struct.pack('b', 1)
    self.ownsock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    # Setup Controller Socket
    self.contr_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.contr_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.contr_sock.bind(('224.0.0.1',UDP_PORT))
    #self.contr_sock.settimeout(.25)
    group = socket.inet_aton('224.0.0.1')
    mreq = struct.pack('4sL', group, socket.INADDR_ANY) 
    self.contr_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

  def transmit(self):
    # Transmit message about energy rank and position
    message = self.name + "_" + str(self.timestamp) + "_" + str(self.pos[0]) + "_" + str(self.pos[1]) + "_" + str(self.energy) + "_" + str(self.state)     
    print >>sys.stderr, self.name,'sending "%s"' % message
    sent = self.ownsock.sendto(message, (self.ip,UDP_PORT))
    self.energy -= self.calc_energy('transmit',len(message)*8)

  def receive(self):
    # Read from each neighbor for a response
    data_list = []
    for sock in self.neighbor_socks: 
      while(True):
        try:
          data, address = sock.recvfrom(1024)
          data_list.append(data)
        except socket.timeout:
          break
     
    if (len(data_list) != 0):
      print self.name,"Data_received",data_list
      length = 0
      for data in data_list:
         length += len(data)*8
      self.energy -= self.calc_energy("receive",length)
      return data_list
    else:
      return None

  def socket_sleep(self):
    for sock in self.neighbor_socks:
      sock.close()   

  def socket_wake(self):
    self.neighbor_socks = []
    host = socket.gethostname()

    for multicast_group in self.neighbors:
      # Create the socket
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      # Bind to the server address
      sock.bind((multicast_group, UDP_PORT))
      sock.settimeout(.05)
      group = socket.inet_aton(multicast_group)
      mreq = struct.pack('4sL', group, socket.INADDR_ANY) 
      sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
      
      self.neighbor_socks.append(sock)



######################################
# Main
######################################

def route_setup(nodes):
  # Create empty list
  edge_list = []
  #energy_cost = [0]*5
  for i in range(len(nodes)):
    edge_list.append([])
    
  # For now, setup up routes if they are within range of each other
  for i in range(len(nodes)):
    p0 = nodes[i][0]
    for j in range(i+1,len(nodes)):
      p1 = nodes[j][0]
      dist = math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)
      if(dist < r):
        # If distance between two nodes is less than communication range, then connect
        edge_list[i].append(nodes[j][1])
        edge_list[j].append(nodes[i][1])
  return edge_list 

if __name__ == '__main__':
  node_info = [] # Contain information about each node. Position, IP Address, Own Connection
  network = [] # Used to start and join processes
  
  num, area_x, area_y, r = map(int,sys.argv[1:5])
  # For now, create five nodes in a 2x2 meter area
  ip_part1 = '239.0.0.'
  ip_part2 = 1

  for i in range(num):
    pos = [random()*area_x,random()*area_y]
    ip = ip_part1 + str(ip_part2)
    node_info.append([pos,ip])
    ip_part2 += 1
    if(ip_part2 >256):
      print "Error: Too many nodes created. Maximum limit is 256"
      break
  
  # Setup up Routes and Calculate Broadcast energy
  edge_list = route_setup(node_info)
  
  # Print out edge_list
  for node in edge_list:
    print node  

  # Start up all nodes
  for i in range(num):
    n = Node(node_info[i], edge_list[i])
    network.append(n)
    n.start()

  for i in range(num):
    network[i].join()
  
        
