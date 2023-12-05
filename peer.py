#!/usr/bin/python3

#------------------------------------------
# NAME		: Tara Boulanger
# STUDENT NUMBER	: 7922331
# COURSE		: COMP 3010
# INSTRUCTOR	: Robert Guderian
# ASSIGNMENT	: Assignment 3
# 
# REMARKS: 
#
#------------------------------------------

#imports
 
import socket
import sys
import uuid
import json
import time
import traceback
import random
import hashlib
import itertools


# constants
HOST = ''
PORT = 8680 #I have 8680-8684
ID = str(uuid.uuid4()) #Creating a uuid for this peer...?
NAME = ":]"
#Only needed if I do the mining part
MESSAGES = ["She", "sells", "sea", "shells", "by the", "sea", "shore."]

STATS_TIMEOUT = 5
PEER_TIMEOUT = 90   #every minute and a half, remove dead peer
REGOSSIP = 30       #every thirty seconds (as per instructions)
RECONSENSUS = 120   #every 2 minutes

KNOWN_HOST = '192.168.102.146'#'silicon.cs.umanitoba.ca'
KNOWN_PORT = 8999

DIFFICULTY = 9


#Class for being able to access the hostname and port number of each peer
class Peer :
    peerList = []
    def __init__(self,host,port) :
        self.hostname = host
        self.portnum = port
    def addPeer ( self, peer ) :
        self.peerList.append(peer)
    def dropPeer ( self, peer ) :
        self.peerList.remove(peer)
    def getPeers ( self ) :
        return self.peerList
    def equals ( self, peer ) :
        result = False
        if ( self.hostname == peer.hostname and self.portnum == peer.portnum ) :
            result = True
        return result


class Stat :
    def __init__(self, height:int, hash:str, host:str, port:int) :
        self.height = height
        self.hash = hash
        self.host = host
        self.port = port


#Class containing the pertinent information stored in a block
class Block : 
    def __init__(self, height:int, hash:str, nonce:str, time:time) :
        self.height = height
        self.hash = hash
        self.nonce = nonce
        self.time = time


#Class containing the current blockchain for our peer
class Blockchain :
    blockList = []
    def __init__(self) :
        self.height = 0
        self.hash = ''
        self.message = ''
        self.name = ''
        self.nonce = ''
        self.time = 0
    
    def addBlock ( self, block:Block ) :
        self.blockList.append(block)
        self.updateValues()
    
    def updateValues ( self ) :
        heights = []
        for i in range(len(self.blockList)) :
            heights.append(self.blockList[i].height)
            
        self.height = max(heights)
    
    
#Class for the queue of timeouts
class Timeout : 
    peerIds = 0
    
    def __init__(self, type:str) :
        self.start = time.time()
        self.type = type
        self.expires = self.expiryTime()
        self.id = self.setId()
    def expiryTime (self) :
        if self.type == "REGOSSIP" :
            result = self.start + REGOSSIP
        elif self.type == "RECONSENSUS" :
            result = self.start + RECONSENSUS
        elif self.type == "PEER" :
            result = self.start + PEER_TIMEOUT
        return result
    def setId (self) :
        if self.type == "REGOSSIP" :
            result = 1 #placeholder
        elif self.type == "RECONSENSUS" :
            result = 1 #placeholder
        elif self.type == "PEER" :
            result = self.peerIds
            self.peerIds = self.peerIds + 1
        return result
    def getExpiry (self) :
        return self.expires
    def __str__(self) :
        return "start: "+str(self.start)+"  type: "+str(self.type)+"   expires: "+str(self.expires)


#Class to handle the timeouts
class TimeoutQueue : 
    timeoutList = []
    def __init__(self) :
        pass
        
    def addTimeout (self, type:str) :
        timeout = Timeout(type)
        self.timeoutList.append(timeout)
        
    #Send it the protocols object so it can do a call back to it
    def handleTimeouts(self, protocols) :
        #this won't run if there aren't any timeouts in the list
        removedTimeouts = []
        if len(self.timeoutList) > 0 :
            for i in range(len(self.timeoutList)) :
                #print("IN THE FOR LOOP")
                if self.timeoutList[i].expires <= time.time() :
                    print(self.timeoutList[i].expires)
                    print(time.time())
                    if self.timeoutList[i].type == "REGOSSIP" :
                        protocols.resetGossips()
                        protocols.sendGossip()
                        #print("WE BACK BAYABY")
                    elif self.timeoutList[i].type == "RECONSENSUS" :
                        protocols.doConsensus()
                    elif self.timeoutList[i].type == "PEER" :
                        protocols.PEERS.pop(i)
                        
                    removedTimeouts.append(i)
        #Used to remove timeouts from the list if they've already expired
        if len(removedTimeouts) > 0 :
            for i in range(len(removedTimeouts)) :
                self.timeoutList.pop(i)
    
    def updatePeer(self,host,port) :
        pass


#Class containing all of the protocols and messages
#have a timeouts list in here to figure out when we need to send our messages out.
class Protocols :
    def __init__(self, peer:Peer, timeoutQueue:TimeoutQueue) :
        peer.addPeer(peer)
        self.PEERS = peer.getPeers()
        self.GOSSIPS = [] #Literally just to keep track of the gossips that we've gotten already
        self.BLOCKS = Blockchain #This is the blockchain that we have
        self.TIMEOUTQUEUE = timeoutQueue
        self.doingConsensus = False
        self.STATSLIST = []
    #functions
    def sendGossip ( self ) :
        response = {
            "type" : "GOSSIP",
            "host" : HOST,
            "port" : PORT,
            "id" : ID,
            "name" : NAME
        }
        print("Sending gossip: " + str(response))
        
        #Send it to 3 peers we know of doing random.choices or send it to the ones we do know
        if ( len(self.PEERS) < 3 ) :
            try : 
                for i in range(len(self.PEERS)) :
                    SOCKET.sendto(json.dumps(response).encode(),(self.PEERS[i].hostname,self.PEERS[i].portnum))
                    #data, adr = SOCKET.recvfrom(2048)
                    #jsonObj = json.loads(data)
                    #self.processGossipReply(jsonObj)
            except :
                print("Something went wrong in sending to host:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.PEERS,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(response).encode(),(thePeers[i].hostname,thePeers[i].portnum))
                    #data, adr = SOCKET.recvfrom(2048)
                    #jsonObj = json.loads(data)
                    #self.processGossipReply(jsonObj)
                except :
                    print("Something went wrong in sending to peers:")
                    traceback.print_exc()
        self.TIMEOUTQUEUE.addTimeout("REGOSSIP")

    def sendReceivedGossip ( self, message ) :
        print("Forwarding gossip: " + str(message))
        #Send it to 3 peers we know of doing random.choices or send it to the ones we do know
        if ( len(self.PEERS) < 3 ) :
            try :
                for i in range(len(self.PEERS)) :
                    SOCKET.sendto(json.dumps(message).encode(),(self.PEERS[i].hostname,self.PEERS[i].portnum))
            except :
                print("Something went wrong in sending to all currently known peers:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.PEERS,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(message).encode(),(thePeers[i].hostname,thePeers[i].portnum))
                except :
                    print("Something went wrong in sending to 3 peers:")
                    traceback.print_exc()

    def processGossip ( self, message ) :
        senderHost = message['host']
        senderPort = message['port']
        if message['id'] != ID :
            #We haven't seen any gossips yet
            if len(self.GOSSIPS) == 0 :
                self.sendGossipReply(senderHost,senderPort)
                self.sendReceivedGossip(message)
                self.GOSSIPS.append(message['id'])
            else :
                goAhead = True
                for i in range(len(self.GOSSIPS)) :
                    #We haven't seen this gossip message yet
                    if ( message['id'] == self.GOSSIPS[i] ) :
                        goAhead = False
                        #print(len(self.GOSSIPS))
                if goAhead != True :
                    self.sendGossipReply(senderHost,senderPort)
                    self.sendReceivedGossip(message)
                    self.GOSSIPS.append(message['id'])
        else :
            #This is to reset itself in the timeout, confirming it's still here
            #This kinda sucks so...
            for i in range(len(self.PEERS)) :
                if (self.PEERS[i].hostname == senderHost and self.PEERS[i].portnum == senderPort) :
                    self.TIMEOUTQUEUE.updatePeer(senderHost,senderPort)
        
    def sendGossipReply ( self, host:str, port:int ) :
        response = {
            "type" : "GOSSIP-REPLY",
            "host" : HOST,
            "port" : PORT,
            "name" : NAME
        }
        print("Sending gossip reply: " + str(response))
        #sending it back to the one who sent the original gossip message
        try :
            SOCKET.sendto(json.dumps(response).encode(),(host,port))
        except :
            print("Something went wrong in sending the reply:")
            traceback.print_exc()
    
    def resetGossips ( self ) :
        self.GOSSIPS.clear()
    
    def processGossipReply ( self, message ) :
        print("Received gossip reply: " + str(message))
        #Basically just joining the network by adding this peer to our list
        #First peer to join! (other than the well-known one)
        peer = Peer(message['host'],message['port'])
        if len(self.PEERS) <= 1 :
            self.PEERS.append(peer)
            self.TIMEOUTQUEUE.addTimeout("PEER")
            print(len(self.PEERS))
        else :
            doIt = True
            for i in range(len(self.PEERS)) :
                if (self.PEERS[i].equals(peer)) :
                    doIt = False
            if doIt == True :
                #WILL NEED TO ADD MORE LOGIC TO RESET THE TIMEOUT SO THAT THEY DON'T GET CUT OUT THEN READDED
                self.PEERS.append(peer)
                self.TIMEOUTQUEUE.addTimeout("PEER")
                print(len(self.PEERS))

    def sendStats (self) :
        response = {
            "type" : "STATS"
        }
        print("Sending stats: " + str(response))
        #Send stats to all peers!
        for i in range(len(self.PEERS)) :
            try :
                SOCKET.sendto(json.dumps(response).encode(),(self.PEERS[i].hostname,self.PEERS[i].portnum))
                SOCKET.settimeout(STATS_TIMEOUT)
                data, adr = SOCKET.recvfrom(2048)
                jsonObj = json.loads(data)
                self.processStatsReply(jsonObj,adr)
            except :
                print("Something went wrong when asking for stats:")
                traceback.print_exc()

    def sendStatsReply ( self, host:str, port:int ) :
        response = {
            "type" : "STATS_REPLY",
            "height" : self.BLOCKS.height,
            "hash" : self.BLOCKS.hash
        }
        print("Sending stats reply: " + str(response))
        try :        
            #Sending it back to the one who sent the first response
            SOCKET.sendto(json.dumps(response).encode(),(host,port))
        except :
            print("Something happened when sending the stats reply back:")
            traceback.print_exc()
    
    def processStats ( self, message, addr ) :
        print("Received stats message: " + str(message))
        #We'll just need to send a stats reply back to the person who sent the message to us
        self.sendStatsReply(addr[0],addr[1])
    
    #This function is different since it is only called within the sendStats function
    def processStatsReply (self, message, address) :
        print("Received stats reply: " + str(message))
        #This is where we see what their height and what their hash is.
        #Maybe have a list of peers with heights and hashes and how many of them agree on which combination
        stat = Stat(message['height'],message['hash'],address[0],address[1])
        self.STATSLIST.append(stat)

    def doConsensus ( self ) :
        #Do a consensus here
        self.doingConsensus = True
        self.sendStats()
        self.findLongest()
        self.doingConsensus = False
    
    #This needs to be rewritten, wtf is going on here LMAO
    def findLongest ( self ) :
        #Let's sort the list by heights so that we can then get the groups of heights
        self.STATSLIST.sort(key = lambda x: x.get('height'))
        #heights = set(map(lambda x:x[0], self.STATSLIST))
        heights = [list(g) for g in itertools.groupby(sorted(self.STATSLIST, key=lambda x:x[0]))]
        
        #The most-agreed-upon heights is at the front of our list, should also be a list still?
        print(len(heights))
        mostAgreedUponHeight = heights[0]
                
        #Now let's sort the hashes from those heights
        for i in range(len(heights)):
            heights[i].sort(key = lambda x: x[1])
        #This is a list of the different grouped hashes
        #theGroups = [list(g) for g in itertools.groupby(sorted(self.STATSLIST, lambda x: x[1]))]

        #Now that all of the hashes are now grouped together in their respective heights, we should be able to
        #choose the most agreed-upon one
        mostAgreedUponChain = max(heights[1],key=len)[1]
        
        peers = self.STATSLIST[mostAgreedUponHeight, mostAgreedUponChain]
        
        self.askForBlocks(mostAgreedUponHeight, mostAgreedUponChain, peers)
    
    def askForBlocks ( self, height, chain, peers ) :
        #Send GET_BLOCK requests to all peers that agreed
        self.sendGetBlock(height, peers)

    def sendGetBlock ( self, height, peers ) :
        response = {
            "type" : "GET_BLOCK",
            "height" : height
        }
        for i in range(len(peers)) :
            try :
                SOCKET.sendto(json.dumps(response).encode(),(peers[i].hostname,peers[i].portnum))
                data, adr = SOCKET.recvfrom(2048)
                jsonObj = json.loads(data)
                self.processGetBlockReply(jsonObj,adr)
            except :
                print("Something happened when sending the get block:")
                traceback.print_exc()
    
    def sendGetBlockReply ( self, height:int, host:str, port:int ) :
        #Valid height given?
        if ( height < self.BLOCKS[len(self.BLOCKS)].height ) :
            height = None
        else :
            response  = {
                "type" : "GET_BLOCK_REPLY",
                "hash" : self.BLOCKS[len(self.BLOCKS)].hash,
                "height" : height,
                "messages" : self.BLOCKS[len(self.BLOCKS)].message,
                "minedBy" : self.BLOCKS[len(self.BLOCKS)].name,
                "nonce" : self.BLOCKS[len(self.BLOCKS)].nonce,
                "timestamp" : self.BLOCKS[len(self.BLOCKS)].time
            }
            #sending it back to the one who sent the first response
            try :
                SOCKET.sendto(json.dumps(response).encode(),(host,port))
            except :
                print("Something happened when sending the get block reply:")
                traceback.print_exc()
    
    def processGetBlock ( self, message, adr ) :
        print("Received get block: " + str(message))
        self.sendGetBlockReply(adr[0],adr[1])
    
    def processGetBlockReply ( self, message, address ) :
        print("Received get block reply: " + str(message) + "from: " + address)
        
        #Do some stuff, is this just adding a block to our current chain?
        
        if ( len(message['messages']) <= 0 or len(message['messages'] > 10 ) ) :
            print("Invalid messages provided in block.")
        else :
            chain = hashlib.sha256()
            
            chain.update(message['hash'].encode())

            chain.update(message['minedby'].encode())
            
            for i in range(len(message['messages'])) :
                chain.update(message['messages'][i].encode())
        
            chain.update(message['timestamp'].to_bytes(8,'big'))
            
            chain.update(message['nonce'].encode())
            
            hash = chain.hexdigest()

            if hash[-1*DIFFICULTY:] != '0' * DIFFICULTY:
                print("Block was not difficult enough: {}".format(hash))
        
            block = Block(message['height'],hash,message['nonce'],message['time'])
            self.validateBlock(block)
    
    def validateBlock ( self, block ) :
        if ( block.height == 0) :
            pass
        #Add block to our chain in here or smt
    
    #This validates our entire blockchain
    def validateChain ( self ) :
        for i in range(len(self.BLOCKS)) :
            self.validateBlock(self.BLOCKS[i])
    
    def processAnnounce ( self, message ) :
        #process the announce message
        print("Got an announcement: " + str(message))
        
        if message['hash'][-1*DIFFICULTY:] != '0' * DIFFICULTY:
            print("Block was not difficult enough: {}".format(hash))
        else :
            block = Block(message['height'],message['hash'],message['nonce'],message['time'])
            self.validateBlock(block)
        #the format is as follows
        '''
        {
            "type" : "ANNOUNCE",
            "height" : height,
            "minedBy" : NAME,
            "nonce" : myNonce,
            "messages" : MESSAGES,
            "hash" : myHash,
            "timestamp" : blockTime
        }
        '''    


#Class to handle the command line input
class HandleInput :
    def __init__(self, host, port) :
        self.HOST = host
        self.PORT = port
        
    def handleInput (self) :
        #Parsing command line to get host IP and port number
        if len(sys.argv) < 2:
            print("Open file as: python3 peer.py ip port")
            sys.exit(1)

        self.HOST = "192.168.102.146"
        #HOST = sys.argv[1]
        try:
            self.PORT = int(sys.argv[2])
        except:
            print("Bad port number")
            sys.exit(1)
            
    def getHost (self) :
        return self.HOST
    
    def getPort (self) :
        return self.PORT


#This class is for processing the message received in the socket
class ProcessMessage : 
    def __init__ (self) :
        self.timeoutQueue = TimeoutQueue()
        self.protocols = Protocols(Peer(KNOWN_HOST,KNOWN_PORT),self.timeoutQueue)
        
    def joinNetwork (self) :
        self.protocols.sendGossip()

    def afterWeJoined ( self ) :
        self.protocols.doConsensus()
        self.protocols.validateChain()
        
    def processMessage ( self, message, adr ) :
        #Loading the information we received from bytes into a json object
        try :
            jsonObj = json.loads(message)
        except :
            print("Bad JSON format.")
        
        #Now let's work with the json. Figure out what needs to be done.
        if ( jsonObj['type'] == "GOSSIP" ) :
            self.protocols.processGossip(jsonObj)
        elif ( jsonObj['type'] == "GOSSIP_REPLY" ) :
            self.protocols.processGossipReply(jsonObj)
        elif ( jsonObj['type'] == "STATS" ) :
            self.protocols.processStats(jsonObj,adr)
        #elif ( jsonObj['type'] == "STATS_REPLY" ) :
        #    self.protocols.processStatsReply(jsonObj)
        elif ( jsonObj['type'] == "ANNOUNCE" ) :
            self.protocols.processAnnounce(jsonObj)
        elif ( jsonObj['type'] == "GET_BLOCK" ) :
            self.protocols.processGetBlock(jsonObj, adr)
        #elif ( jsonObj['type'] == "GET_BLOCK_REPLY" ) :
        #    self.protocols.processGetBlockReply(jsonObj)
        elif ( jsonObj['type'] == "CONSENSUS" ) :
            self.protocols.doConsensus()
        else :
            print("Invalid procedure requested.")
    
    def handleTimeouts(self) :
        self.timeoutQueue.handleTimeouts(self.protocols)


    

#Process the command-line input
handlingInput = HandleInput(HOST,PORT)
handlingInput.handleInput()

HOST = handlingInput.getHost()
PORT = handlingInput.getPort()

#Opening our socket
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCKET.bind(('', PORT))

print("listening on interface " + HOST)
print('listening on port:', PORT)

processingMessages = ProcessMessage()
processingMessages.joinNetwork()

buffer = 0

while True :
    try :
        #Getting any message being sent to us
        data, addr = SOCKET.recvfrom(2048)

        processingMessages.processMessage(data,addr)
        processingMessages.handleTimeouts()

        if buffer == 20 :
            processingMessages.afterWeJoined()
    
    except KeyboardInterrupt as ki:
        print("User exited process.")
        sys.exit(0)