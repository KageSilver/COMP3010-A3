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
import os
import uuid
import json
import time
import traceback
import random


# constants
HOST = ''
PORT = 8680 #I have 8680-8684
ID = str(uuid.uuid4()) #Creating a uuid for this peer...?
NAME = ":]"
#Only needed if I do the mining part
MESSAGES = ["She", "sells", "sea", "shells", "by the", "sea", "shore."]

TIMEOUT = 0.5
REGOSSIP = 30
RECONSENSUS = 120 #every 2 minutes

KNOWN_HOST = '192.168.102.146'#'silicon.cs.umanitoba.ca'
KNOWN_PORT = 8999

DIFFICULTY = 9

#variables
timeouts = []


#Checking timeouts
gossipTime = time.time()
consensusTime = time.time()


#Class for being able to access the hostname and port number of each peer
class Peer :
    def __init__(self,host,port) :
        self.hostname = host
        self.portnum = port
    def getHostname ( self ) :
        return self.hostname
    def getPortnum ( self ) :
        return self.portnum


#Class to handle the timeouts, add a protocol class to be able to do the stuff when needed
class TimeoutQueue : 
    timeoutWhen = 0
    def handleTimeouts() :
        protocols = Protocols

        if ( time.time() > gossipTime + REGOSSIP ) :
            random.sample(peers,3)
            protocols.sendGossip()


#Class containing the pertinent information stored in a block
class Block : 
    height = 0
    hash = ''
    nonce = ''
    time = ''


#Class containing all of the protocols and messages
class Protocols :
    def __init__(self, peer) :
        self.PEERS = peer

    #functions
    def sendGossip ( self, host, port, id, name ) :
        response = {
            "type" : "GOSSIP",
            "host" : host,
            "port" : port,
            "id" : id,
            "name" : name
        }
        print("Sending gossip: " + response)
        #Send it to 3 peers we know of doing random.choices
        if (len(self.PEERS)<3) :
            pass
        else :
            thePeers = random.choice(self.PEERS,k=3)
            for i in 3 :
                thePeers[i].sendto(json.dumps(response).encode(),(thePeers[i].hostname,thePeers[i].portnum))

    def sendReceivedGossip ( self, message ) :
        print("Forwarding gossip: " + message)
        for i in len(self.PEERS) :
            self.PEERS[i].sendto(json.dumps(message),(self.PEERS[i].hostname,self.PEERS[i].portnum))
        #We don't need to get anything back

    def processGossip ( self, message ) :
        #We haven't seen this gossip message yet
        if ( message['id'] != self.tempGossipID ) :
            senderHost = message['host']
            senderPort = message['port']
            self.sendGossipReply(senderHost,senderPort)
            self.sendReceivedGossip(message)
        
    def sendGossipReply ( self, host:str, port:int ) :
        response = {
            "type" : "GOSSIP-REPLY",
            "host" : self.HOST,
            "port" : self.PORT,
            "name" : self.NAME
        }
        print("Sending gossip reply: " + response)
        #sending it back to the one who sent the first response
        self.SOCKET.sendto(json.dumps(response),(host,port))
                
    def processGossipReply ( self, message ) :
        print("Received gossip reply: " + message)
        #Basically just joining the network by adding this peer to our list
        peer = Peer(host=message['host'],port=message['port'])
        self.PEERS.append(peer)

    def sendStats () :
        response = {
            "type" : "STATS"
        }
        for i in len(peers) :
            peerSocket.sendto(json.dumps(response),(peers[i].hostname,peers[i].portnum))

    def sendStatsReply ( block, host:str, port:int ) :
        response = {
            "type" : "STATS_REPLY",
            "height" : block.height,
            "hash" : block.hash
        }
        #sending it back to the one who sent the first response
        peerSocket.sendto(json.dumps(response),(host,port))

    def doConsensus (self) :
        #Do a consensus here
        results = self.sendStats()
        self.findLongest(results)
        
    def findLongest (stats) :
        theJson = []
        for i in 3 :
            theJson[i] = json.dumps(stats[i])
        maxHeight = max(theJson['height'])
        indecies = theJson['height'] == maxHeight
        
        for i in indecies :
            hashes = theJson[i].get('hash')
        
        #check for the majority hashes
        #DO STUFF HERE

    def sendGetBlock (block) :
        response = {
            "type" : "GET_BLOCK",
            "height" : block.height
        }
        for i in len(peers) :
            peerSocket.sendto(json.dumps(response),(peers[i].hostname,peers[i].portnum))

    def sendGetBlockReply ( block, host:str, port:int ) :
        response  = {
            "type" : "GET_BLOCK_REPLY",
            "hash" : block.hash,
            "height" : block.height,
            "messages" : MESSAGES,
            "minedBy" : NAME,
            "nonce" : block.nonce,
            "timestamp" : block.time
        }
        #sending it back to the one who sent the first response
        peerSocket.sendto(json.dumps(response),(host,port))
               
    def getAnnounce () :
        #process the announce message
        print("got an announcement")
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
    def __init__ (self, host, port, id, name, peerSocket, knownHost, knownPort) :
        self.HOST = host
        self.PORT = port
        self.ID = id
        self.NAME = name
        self.SOCKET = peerSocket
        self.KNOWN_HOST = knownHost
        self.KNOWN_PORT = knownPort
        self.protocols = Protocols([Peer(self.KNOWN_HOST,self.KNOWN_PORT)])
    def processMessage ( self, message ) :
        #Loading the information we received from bytes into a json object
        try :
            jsonObj = json.loads(message)
        except :
            print("Bad JSON format.")
        
        #Now let's work with the json. Figure out what needs to be done.
        if ( jsonObj['type'] == "GOSSIP" ) :
            self.protocols.processGossip(jsonObj)
        elif ( jsonObj['type'] == "GOSSIP-REPLY" ) :
            Protocols.processGossipReply(jsonObj)
        elif ( jsonObj['type'] == "STATS" ) :
            print()
            #Protocols.processStats(jsonObj)
        else :
            print("Invalid procedure requested.")


#This class is for joining the network once by sending a gossip message
class JoinNetwork :
    def __init__(self, host, port, id, name, peerSocket, knownHost, knownPort) :
        self.HOST = host
        self.PORT = port
        self.ID = id
        self.NAME = name
        self.SOCKET = peerSocket
        self.KNOWN_HOST = knownHost
        self.KNOWN_PORT = knownPort
    def joinNetwork (self) :
        message = {
            "type" : "GOSSIP",
            "host" : self.HOST,
            "port" : self.PORT,
            "id" : self.ID,
            "name" : self.NAME
        }
        print("Joining the network with: " + str(message))
        #Send it to the 1 well-known peer
        try :
            self.SOCKET.sendto(json.dumps(message).encode(),(self.KNOWN_HOST,self.KNOWN_PORT))
        except Exception as e :
            print("Something went wrong: ")
            traceback.print_exc()
    

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

joiningNetwork = JoinNetwork(HOST,PORT,ID,NAME,SOCKET,KNOWN_HOST,KNOWN_PORT)
joiningNetwork.joinNetwork()

processingMessages = ProcessMessage(HOST,PORT,ID,NAME,SOCKET,KNOWN_HOST,KNOWN_PORT)

while True :
    try :
        #Getting any message being sent to us
        data, addr = SOCKET.recvfrom(2048)

        processingMessages.processMessage(data)
    
    except KeyboardInterrupt as ki:
        print("User exited process.")
        sys.exit(0)