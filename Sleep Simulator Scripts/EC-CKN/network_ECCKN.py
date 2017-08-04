import multiprocessing
import socket
import time
from random import seed, uniform, random
import sys
import math
import struct
from event_gen_ECCKN import event_gen

UDP_PORT = 5005
# Initialize global variables. Will be overwritten by arguments
#r = 90
r = 10
num = 0       # Number of nodes in network
area_x = 50    # Width of area
area_y = 50    # Height of area
k = 0

# Detection Sensors
#detect_list = ['PIR','Vibration','Distance']
detect_list = {'PIR':14,'Vibration':10,'Ultrasound':14}
# Classifiying Sensors
class_list = {'Camera':6,'Microphone':10,'RFID':1,'Magnetomer':1}

# Energy Model Parameters
E_fs = 10**-10 #pJ/bit/m^2
E_mp = 0.0013*10**-12 #pJ/bit/m^4
E_elec = 50*10**-9 #nJ/bit
d_thresh = 87.7058 #m
######################################
# Node Class
######################################

class Node(multiprocessing.Process):
  epoch = 2.0
  maxhops = 2 #It is maxhops + 1. Ex: maxhops = 2. Three multihops allowed
  def __init__(self, node_info, neighbor_info):
    # Set up various characteristics about the node
    multiprocessing.Process.__init__(self)
    self.pos = node_info[0]
    self.ip = node_info[1]
    self.type = node_info[2]
    self.neighbors = neighbor_info
    # Give the node a random amount of energy between 1.9 and 2.1 J
    #self.energy = 0.01 + random()*.0001
    self.energy = .05 + random()*.001
    # Contains list of neighbor nodes, energy, and connections
    self.ninfo = dict()
    self.n2info = dict()
    
    # States. Init = 0, Sleep = 1, Awake = 2, Dead = -1
    # Self.stage. 0 = Transmit first message. 1 = Receive other messages. 2 = Transmit neighbor info. 3 = Receive neighbor info
    self.state = 0
    self.stage = 0
    self.timestamp = 0
    
    # Events
    self.stage_event = 0
    self.event_detected = False
    self.message_buffer = []
    self.message_index = 0
    self.events = dict()

    # Basestation
    if self.name == 'Node-'+str(num+1):
      self.name = 'Basestation'
      self.state = 2
      self.energy = 10000 # Some abnormally large value
      self.num_event = 0
    print self.name,'Type:',self.type,"X:",self.pos[0],"Y:", self.pos[1],"E:", self.energy

  def calc_energy(self,mode,load):
    '''
    time = float(load)/250000.0 #kbps
    if mode == "transmit":
      return .00125*time
    elif mode == "receive:
      return .00125*time
    '''
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
          # Step through current time period
          if self.name == 'Basestation':
            message = self.step_basestation()
          else:
           message = self.step()
          # Send message
          self.contr_sock.sendto(message, address)
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

  def event_transmit(self):
    # Send any messages that have been received in the previous event_stage 
    for i in range(self.message_index,len(self.message_buffer)):
      self.transmit(self.message_buffer[i])
      self.message_index += 1

  def event_process(self):
    data,length = self.receive()
    # Check if data is empty
    if data != None:
      for msg in data:
        # Check whether data is already in message buffer. Drop if otherwise
        if msg not in self.message_buffer:
          self.event_detected = True
          self.message_buffer.append(msg)   

  def step_basestation(self):
    sock_msg = 'Continue'
    # Event detection stage
    if self.stage == 0:
      if self.stage_event == 0:
        if self.timestamp in self.events:
          self.event_detected = True
          for eventid in self.events[self.timestamp]:
            self.message_buffer.append(eventid)
            self.num_event += 1
        # Receive any messages
        data,length = self.receive()
        if data != None:
          for msg in data:
            timestamp,node,eventid = msg.split(' ')
            if eventid not in self.message_buffer:
              self.event_detected = True
              self.message_buffer.append(eventid)
              self.num_event += 1
      elif self.stage_event >= 1 and self.stage_event <= self.maxhops:
        data,length = self.receive()
        if data != None:
          for msg in data:
            timestamp,node,eventid = msg.split(' ')
            if eventid not in self.message_buffer:
              self.event_detected = True
              self.message_buffer.append(eventid)
              self.num_event += 1
      # Check if at end of event detection stage
      if self.stage_event == self.maxhops:
        print self.name, 'Message Buffer', self.message_buffer
        print self.name, 'Index', self.message_index
        # Record energy at the start of the epoch
        self.beg_ene = self.energy
        self.stage = 1
        self.message_buffer = []
      print self.name,'Stage_Event',self.stage_event
      # Control Stage Event
      if self.stage_event < self.maxhops:
        self.stage_event += 1
      else:
        self.stage_event = 0
    # Transmit message to 
    elif self.stage == 1:
      sock_msg = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+' '+str(self.pos[1])+' '+str(self.energy)+' '+str(self.event_detected)+' '+self.type+' '+str(self.num_event)
      self.stage = 2
    elif self.stage == 2:
      self.stage = 3
    elif self.stage == 3:
      # Clear receive buffer
      self.receive()
      # Reset values for next epoch
      self.stage = 0
      self.event_detected = False
      self.timestamp += 1
      
    return sock_msg

  def step(self):
    # Simulate each epoch
    sock_msg = 'Continue'
    print self.name, 'Stage', self.stage
    # Initial, Awake, or sleep
    if self.state != -1:
      # Event detection stage. An event triggers, and then semi flood the network by sending packets with max life of three hops
      if self.stage == 0:
        # Check if it is asleep
        if self.state != 1:
          if self.stage_event == 0:
            # Key here is the time the event occurs. If the event occurs between the epoch, send a message saying you sensed it
            if self.timestamp in self.events:
              self.event_detected = True
              for eventid in self.events[self.timestamp]:
                message = str(self.timestamp)+' '+self.name+' '+eventid
                self.message_buffer.append(message)
                self.transmit(message)
                self.message_index += 1
              # Receive any messages
            self.event_process()
          elif self.stage_event >= 1 and self.stage_event <= self.maxhops:
            self.event_transmit()
            self.event_process()
        # Check if at end of event detection stage
        if self.stage_event == self.maxhops:
          print self.name, 'Message Buffer', self.message_buffer
          print self.name, 'Index', self.message_index
          # If node was awake, take out some energy
          if self.state == 2 or self.state == 0:
            self.energy -= 0.001*self.epoch
          # Record energy at the start of the epoch
          self.beg_ene = self.energy
          self.stage = 1
          self.message_buffer = []
          if self.state == 1:
            self.socket_wake()
        print self.name,'Stage_Event',self.stage_event
        # Control Stage Event
        if self.stage_event < 2:
          self.stage_event += 1
        else:
          self.stage_event = 0

      # Transmit message about current status
      elif self.stage == 1:
        sock_msg = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+' '+str(self.pos[1])+' '+str(self.energy)+' '+str(self.event_detected)+' '+self.type
        # Transmit energy info and receive neighbor's energy info
        message = str(self.timestamp)+' '+self.name+' '+self.type+' '+str(self.beg_ene)
        # Transmit message
        self.transmit(message)
        # Receive information
        data,length = self.receive()
        # Store neighbor info in self.ninfo
        if data != None:
          self.store_info(data,'n')
        else:
          print 'Warning: Did not receive message packets'
        self.stage = 2
      # Transmit neighbor info and receive neighbor's neighbor info
      elif self.stage == 2:
        message = str(self.timestamp)+' '+self.name+'|'
        for node in self.ninfo:
          info = self.ninfo[node]
          if len(info) != 2:
            print '*************DEBUG5*************'
            print self.name, self.ninfo, info
            sys.exit()
          message += node+' '+info[0]+' '+info[1]+'|'
        message = message.rstrip('|')
        # Transmit second message
        self.transmit(message)
        # Receive neighbor neighbor info
        data,length = self.receive()
        if data != None:
          self.store_info(data,'n2')
        self.stage = 3
      # Run sleep scheduling algorithm
      elif self.stage == 3:
        self.state = self.sleep_scheduler()
        # If node's battery has died, set to dead state
        if self.energy <= 0:
          self.state = -1
        elif self.state == 1:
          self.socket_sleep()
        # Clear Reset various information
        self.ninfo = dict()
        self.n2info = dict()
        self.stage = 0
        self.event_detected = False
        self.timestamp += 1
        
    # Dead
    elif self.state == -1:
      if self.stage < 3+self.maxhops:
        self.stage += 1
      else:
        self.stage = 0
      if self.stage == 2 + self.maxhops:
        sock_msg = str(self.timestamp)+' '+self.name+' '+str(self.state)+' '+str(self.pos[0])+" "+str(self.pos[1])+' '+str(self.energy)+' False '+self.type
        self.timestamp += 1
    # Close and open sockets to remove any buffered messages
    # Check for any values left in buffer
    if self.state != 1 and self.state != -1:
      data, length = self.receive()
      if data != None:
        print '*************DEBUG4*************'
        print self.name, 'Received extra data at the end of simulation'
        sys.exit()


    return sock_msg

  def sleep_scheduler(self):
    # Sleep scheduling algorithm
    # Check if Nu < k and Nv < k
   
    cond_nbr = True
    for node in self.n2info:
      val = len(self.n2info[node])
      # One of the neighbor nodes has more neighbors than k
      if val >= k:
        cond_nbr = False
        break
    
    if len(self.ninfo) < k or cond_nbr:
      print self.name, 'has Nu >= k and Nv >= k'
      return 2
   
    else:
      #Calculate Eu
      Eu = dict()
      try:
        for node in self.ninfo:
          # If it has a higher energy rank, add it to Eu
          if float(self.ninfo[node][1]) >= self.beg_ene:
            Eu[node] = self.ninfo[node]

      except ValueError:
        print '*************DEBUG2*************'
        print self.name, self.ninfo, node
        sys.exit()

      # If there are less than 2 nodes that have a higher energy rank
      if len(Eu) <= 1:
        print self.name, 'has less than two neighbors with higher energy rank'
        return 2
      
      # Check for Condition 1: Any two nodes in Eu are connected directly or indirectly through nodes which is in the su's 2-hop neighborhood
      # that have Erank larger than Eranku

      # Calculate 2-hop neighbors
      two_hop = []      
      for node in self.n2info:
        for val in self.n2info[node]:
          if val[0] != self.name and not (val[0] in self.ninfo):
            if val[2] > self.beg_ene:
              two_hop.append(val[0])
      # Get only unique values
      two_hop = set(two_hop)
      two_hop = list(two_hop)

      # See if any two nodes in Eu are connected directly or indirectly
      keys = Eu.keys()
      '''
      # Get a list of all Eu connections
      connect_Eu = []
      for i in range(len(keys)):
        # Create a list of neighbor Eu
        nbr = []
        for node_info in self.n2info[keys[i]]:
          nbr.append(node_info[0])
        nbr = [m for m in nbr if m in Eu]
        result = [keys[i]] + nbr
        # If result is not 0, check if we can combine indices in connect_Eu
        if len(result) != 1:
          if len(connect_Eu) == 0:
            connect_Eu.append(result)
          else:
            for 
            # Check if Eu node is indirectly connected to any other nodes
            for list_Eu in connect_Eu:
              if
        else:
          # Eu node is not directly connected to anything
          pass
      '''
      for i in range(len(keys)):
        # Create a list of neighbors
        nbr = []
        for node_info in self.n2info[keys[i]]:
          nbr.append(node_info[0])
        # Look for direct connection between node i and node j by looking for a match between node i's neighbors and node j
        for j in range(i+1,len(keys)):
          # If there is no direct connection, look for indirect connection through two-hop and Eu
          if keys[j] not in nbr:
            nbr2 = []
            for node_info in self.n2info[keys[j]]:
              nbr2.append(node_info[0])
            match = [m for m in nbr if m in nbr2]
            match_twohop = [m for m in match if m in two_hop]
            match_Eu = [m for m in match if m in Eu]
            # If no match is found, return 2
            if len(match_twohop)+len(match_Eu) == 0:
              return 2             
      
      # Check for Condition 2: Any node in Nu has at least k neighbors from Eu
      for node in self.n2info:
        conn = 0
        for val in self.n2info[node]:
          # Check if node is in Eu
          if val[0] in Eu:
            conn += 1
        # If any node does not have at least k neighbors from Eu, it stays awake
        if conn < k:
          return 2
      # If it gets here, that means it passes both conditions
      return 1
          
  def store_info(self,data,store):
    if store == 'n':
      for val in data:
        val_list = val.split(' ')
        self.ninfo[val_list[1]] = val_list[2:len(val_list)] 
    elif store == 'n2':
      for val in data:
        try:
          val_list = val.split('|')
          node = val_list[0].split(' ')[1]
          self.n2info[node] = []
          for i in range(1,len(val_list)):
            self.n2info[node].append(val_list[i].split(' '))
        except AttributeError:
          print '*************DEBUG1*************'
          print self.name, data, val
          sys.exit()

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
    group = socket.inet_aton('224.0.0.1')
    mreq = struct.pack('4sL', group, socket.INADDR_ANY) 
    self.contr_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    # Open event folder
    f = open('event_ECCKN.txt','r')
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

  def transmit(self,message):
    # Transmit message
    #print >>sys.stderr, self.name,'sending "%s"' % message
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
          if int(data.split(' ')[0]) == self.timestamp:
            length += len(data)*8
            data_list.append(data)
          else:
            print '*************DEBUG3*************'
            print self.name, 'Message', data
            print self.name, 'Timestamp', self.timestamp
            print self.name, 'Message Timestamp', data.split(' ')[0]
            sys.exit()
        except socket.timeout:
          break
     
    if (len(data_list) != 0):
      #print self.name,"Data_received",data_list
      self.energy -= self.calc_energy('receive',length)
      return data_list,length
    else:
      return None, None

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
      if(dist <= r):
        #print 'Node',i+1,' Node',j+1
        #print p0, p1, dist
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
  #seed(2)
  try:
    num, k = map(int,sys.argv[1:5])
  except IndexError:
    print 'Arguments should be num, area_x, area_y, k'
    sys.exit()

  if (num >= 254 or num <=0):
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

  for i in range(num+1):
    network[i].join()
  
       
