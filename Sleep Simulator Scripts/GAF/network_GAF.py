import multiprocessing
import socket
import time
from random import random, uniform, seed
import sys
import math
import struct
from event_gen_GAF import event_gen


UDP_PORT = 5005
# Initialize global variables. Will be overwritten by arguments
r = 10
num = 0       # Number of nodes in network
area_x = 50    # Width of area
area_y = 50    # Height of area

# Detection Sensors
detect_list = {'PIR':14.0,'Vibration':10.0,'Ultrasound':14.0}
# Classifiying Sensors
class_list = {'Camera':6.0,'Microphone':10.0,'RFID':1.0,'Magnetomer':1.0}

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
    self.type = node_info[2]
    self.neighbors = neighbor_info
    # Give the node a random amount of energy between 1.9 and 2.1 J
    #self.energy = 1.9 + random()*.2 #15,390 J
    self.energy = 0.01 + random()*.0001
    # Calculate estimated node lifetime
    self.ene_cons = self.calc_energy("transmit",1000) + self.calc_energy("receive",1000)*4
    
    # Node State
    # -1 = Dead, 0 = Sleep, 1 = Discovery, 2 = Awake
    self.state = 1
    self.timestamp = 0
    self.time_left = uniform(iter_per,self.Td_max)
    
    # Used to store time when broadcast messages should be sent while transmitting
    self.act_iter = 0

    # Events
    self.event_detected = False
    self.message_buffer = []
    self.transmit_buffer = []
    self.message_index = 0
    self.events = dict()
    
    if self.name == 'Node-'+str(num+1):
      self.name = 'Basestation'
      self.state = 2
      self.energy = 10000 # Some abnormally large value
      self.num_event = 0
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
      try:
        data, address = self.contr_sock.recvfrom(1024)
        if(data == "step"):
          bs_msg = ''
          # Step through current time period
          if self.energy < 0:
            self.state = -1
          if self.name != 'Basestation':
            self.step()
          else:
            self.step_basestation()
            bs_msg = ' '+str(self.num_event)
          message = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+" "+str(self.pos[1])+' '+str(self.energy)+' '+str(self.event_detected)+' '+self.type+bs_msg
          # Send message
          self.contr_sock.sendto(message, address)
          self.event_detected = False
        elif(data == "quit"):
          break
      except IOError:
        # Try send again
        self.contr_sock.sendto(message, address)
    
    # Close all sockets
    self.ownsock.close()
    for sock in self.neighbor_socks:
      sock.close()
    self.contr_sock.close()

  def step(self):
    self.timestamp += iter_per
    self.time_left -= iter_per

    # Sleep
    if(self.state==0):
      if (self.time_left <= 0):
        # Node goes from discovery to awake
        self.state = 1
        self.time_left += uniform(iter_per,self.Td_max)
        print self.name, "Going from Sleep to Discovery for", self.time_left
        self.socket_wake()

    # Discovery
    elif(self.state==1):
      # If passed, increment time. Check if Td had passed or not      
      if (self.time_left <= 0):
        # When discovery phase ends, broadcast information
        message = "B_%0.2f_%s_%s_%0.2f_%0.2f_%0.6f" % (self.timestamp,self.name,self.type,self.pos[0],self.pos[1],self.energy)
        self.transmit(message)
        # Node goes from discovery to awake
        self.state = 2
        self.time_left += (self.energy*self.Td_max)/(self.ene_cons*4) # Self.enlt/2
        if (self.time_left < 10):
          self.time_left = 10
        print self.name, "Going from Discovery to Active for", self.time_left
        self.act_iter = uniform(iter_per,self.Td_max)
    
      data = self.receive()
      if data != None:
        for msg in data:
          msg_list = msg.split('_')
          # Ignore event messages, and focus only on Broadcast messages
          if msg_list[0] == 'B':
            self.broadcast_logic(msg)
            # If node has fallen asleep, change state 
            if self.state == 0:
              # Calculate how long to sleep
              enat = (self.energy*self.Td_max)/(self.ene_cons*4) # Self.enlt/2
              self.time_left = uniform(enat/2,enat)
              print self.name, "Going from Discovery to Sleep for", self.time_left
              self.socket_sleep()
      
    # Awake
    elif(self.state==2):
      # Energy taken to transmit packets
      self.act_iter -= iter_per

      # Check for events
      for key in self.events:
        # If an event is sensed, broadcast message
        if key < (self.timestamp - 0.0000001) and key >= (self.timestamp - iter_per - 0.0000001):
           for eventid in self.events[key]:
             message = "E_%0.2f_%s_%s_0" %(self.timestamp,self.name,eventid)
             self.transmit(message)
             #del self.events[key]
             self.event_detected = True

      # If self.act_iter is less than one, then we broadcast energy
      if(self.act_iter <= 0):
        message = "B_%0.2f_%s_%s_%0.2f_%0.2f_%0.6f" % (self.timestamp,self.name,self.type,self.pos[0],self.pos[1],self.energy)
        self.transmit(message)
        self.act_iter = uniform(iter_per,self.Td_max)
      
      # Transmit any packages that were found in the previous stage
      
      for msg in self.transmit_buffer:
        self.transmit(msg)
      self.transmit_buffer = []

      # Listen for broadcast messages from higher ranked nodes
      data = self.receive()
      if data != None:
        for msg in data:
          msg_list = msg.split('_')
          if msg_list[0] == 'E':
            self.event_logic(msg)
          elif msg_list[0] == 'B':
            # If a message or messages were received, figure out if you are to sleep or not
            self.broadcast_logic(msg)
          if(self.state == 0):
            # Report back time and set new period
            enat = (self.energy*self.Td_max)/(self.ene_cons*4)
            self.time_left = uniform(enat/2,enat)
            print self.name, "Going from Awake to Sleep for", self.time_left
            self.socket_sleep()    
          
      # Switch to discovery phase if time left has been exceeded
      if(self.time_left <= 0):
        self.state = 1
        self.time_left = uniform(iter_per,self.Td_max)
        self.act_iter = 0

  def step_basestation(self):
    self.timestamp += iter_per
    # Check if basestation would sense an event
    for key in self.events:
      # If an event is sensed, broadcast message
      if key < (self.timestamp - 0.0000001) and key >= (self.timestamp - iter_per - 0.0000001):
         for eventid in self.events[key]:
           self.message_buffer.append(eventid)
           self.event_detected = True
           self.num_event += 1

    # Basestation is always awake
    data = self.receive()
    if data != None:
      for msg in data:
        msg_list = msg.split('_')
        #E,timestamp,node,eventid,hop = msg.split('_')
        if msg_list[0] == 'E':  
          if msg_list[3] not in self.message_buffer:
            self.message_buffer.append(msg_list[3])
            self.num_event += 1
            self.event_detected = True

  def event_logic(self,msg):
    E,timestamp,node,eventid,hop = msg.split('_')
    msg_val = '_'.join([node,eventid])
    # If the number of times it hopped is less than 2, then transmit it again
    if (msg_val not in self.message_buffer):
      self.message_buffer.append(msg_val)
      self.event_detected = True
      # If number of hops
      if int(hop) < 3:
        hop = int(hop) + 1
        timestamp = '%s' %(self.timestamp + iter_per)
        msg = '_'.join([E,timestamp,node,eventid,str(hop)])
        self.transmit_buffer.append(msg)

  def broadcast_logic(self,msg):
    r_blk = r/math.sqrt(5)
    blockx = self.pos[0]//r_blk
    blocky = self.pos[1]//r_blk
    # Check if neighbors have rank
    B, timestamp, node, ntype, x, y, energy = msg.split("_")
    x = float(x)
    y = float(y)
    energy = float(energy)
    own_blockx = x//r_blk
    own_blocky = y//r_blk
    if(own_blockx == blockx and own_blocky == blocky): 
      if(energy > self.energy):
        # If node is detection type, check if neighbor node is also detect type
        if (self.type in detect_list and ntype in detect_list):
          self.state = 0 
        elif self.type in class_list and self.type == ntype:
          self.state = 0
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
    
    # Open event folder
    f = open('event_GAF.txt','r')
    for line in f.readlines():
      line = line.rstrip('\n')
      val_list = line.split(' ')
      # Time, EventId, PosX, PosY
      val_list[0] = float(val_list[0])
      val_list[2] = float(val_list[2])
      val_list[3] = float(val_list[3])
      # Calculate distance
      dist = math.sqrt((val_list[2]-self.pos[0])**2 + (val_list[3]-self.pos[1])**2)
      if self.type in detect_list:
        dist2 = detect_list[self.type]
      elif self.type in class_list:
        dist2 = class_list[self.type]
      if dist <= dist2:
        # Check if key is already being used
        if val_list[0] not in self.events:
          self.events[val_list[0]] = [val_list[1]]
        else:
          self.events[val_list[0]].append(val_list[1])
        
    if len(self.events)>0:
      print self.name,'Events',self.events
    f.close()

  def transmit(self,message):
    # Transmit message about energy rank and position     
    print >>sys.stderr, self.name,'sending "%s"' % message
    sent = self.ownsock.sendto(message, (self.ip,UDP_PORT))
    self.energy -= self.calc_energy('transmit',len(message)*8)

  def receive(self):
    # Read from each neighbor for a response
    data_list = []
    length = 0
    for sock in self.neighbor_socks: 
      while(True):
        try:
          data, address = sock.recvfrom(1024)
          # Check if data has the same timestamp
          timestamp = float(data.split('_')[1])
          if timestamp <= self.timestamp+0.000001 and timestamp >= self.timestamp-0.000001:
            length += len(data)*8
            data_list.append(data)
          else:
            print '*************DEBUG3*************'
            print self.name, 'Message', data
            print self.name, 'Timestamp', self.timestamp
            print self.name, 'Message Timestamp', data.split('_')[1]
            sys.exit()
        except socket.timeout:
          break
     
    if (len(data_list) != 0):
      print self.name,"Data_received",data_list
      self.energy -= self.calc_energy('receive',length)
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
    # Clear buffer
    self.receive()



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

def node_placement():
  node_info = []
  ip_part = 1
  detect_keys = detect_list.keys()
  class_keys = class_list.keys()
  # Place detector nodes first between 0-45 and 135-180
  for i in range(0,num/2):
    if (i%2 == 0):
      lim_y1 = 0
      lim_y2 = area_y/4
    else: 
      lim_y1 = (area_y*3)/4
      lim_y2 = area_y
    pos = [uniform(0,area_x),uniform(lim_y1, lim_y2)]
    ctype = detect_keys[ip_part%len(detect_keys)]
    ip = '239.0.0.' + str(ip_part)
    node_info.append([pos,ip,ctype])
    ip_part += 1
  # Place classifying nodes first between 45 and 135
  for i in range(0,(num/2)+(num%2)):
    pos = [uniform(0,area_x),uniform(area_y/4,3*area_y/4)]
    ctype = class_keys[ip_part%len(class_keys)]
    ip = '239.0.0.' + str(ip_part)
    node_info.append([pos,ip,ctype])
    ip_part += 1
  
  # Place a basestation node in the middle
  node_info.append([[area_x/2,area_y/2],'239.0.0.254','Camera'])
  return node_info

if __name__ == '__main__':
  #node_info = [] # Contain information about each node. Position, IP Address, Own Connection
  network = [] # Used to start and join processes
  # Debug
  #seed(5)
  try:
    num = int(sys.argv[1])
  except IndexError or ValueError:
    print 'Arguments should be num'
    sys.exit()

  if (num >= 255 or num <=0):
    print 'Number of nodes exceeds range: 1-253'
    sys.exit()
  
  # Setup Node Placement
  node_info = node_placement()

  # Setup up Routes and Calculate Broadcast energy
  edge_list = route_setup(node_info)
  
  # Print out edge_list
  for node in edge_list:
    print node  
  
  # Create the events
  event_gen()
  
  # Start up all nodes
  for i in range(num+1):
    n = Node(node_info[i], edge_list[i])
    network.append(n)
    n.start()

  for i in range(num):
    network[i].join()
  
        
