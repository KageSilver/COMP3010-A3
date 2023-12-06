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

JOIN_DELAY = 10000  #Set to a huge number as it'll just be overridden
STATS_TIMEOUT = 20
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
    blockchain = []
    def __init__(self, height:int, hash:str, messages, nonce:str, time:time) :
        self.height = height
        self.hash = hash
        self.messages = messages #A list of messages
        self.nonce = nonce
        self.time = time
    def addBlock(self, block) :
        self.blockchain.append(block)
    
    
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
        elif self.type == "STATS_REPLY" :
            result = self.start + STATS_TIMEOUT
        elif self.type == "JOIN" :
            result = self.start + JOIN_DELAY
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
        
    def addTimeout ( self, type:str ) :
        timeout = Timeout(type)
        self.timeoutList.append(timeout)
        
    def getTimeout ( self, type ) :
        result = None
        for i in range(len(self.timeoutList)) :
            if self.timeoutList[i].type == type :
                result = self.timeoutList[i]
        return result
    
    #Used to forcibly remove a specific type of timeout from the list of timeouts we have
    def removeTimeout ( self, type ) :
        for i in range(len(self.timeoutList)) :
            if self.timeoutList[i].type == type :
                self.timeoutList.pop(i)

    #Send it the protocols object so it can do a call back to it
    def handleTimeouts ( self, protocols ) :
        #this won't run if there aren't any timeouts in the list
        removedTimeouts = []
        #Making sure there are timeouts in the list to go through
        if len(self.timeoutList) > 0 :
            #Iterating through the list
            for i in range(len(self.timeoutList)) :
                #Checking if the current timeout is gonna expire
                if self.timeoutList[i].expires <= time.time() :
                    #If a regossip timeout happens, we need to rest the gossips we have, and send out more
                    if self.timeoutList[i].type == "REGOSSIP" :
                        protocols.resetGossips()
                        protocols.sendGossip()
                    
                    #If a reconsensus timeout happens, we're going to rerun a consensus
                    elif self.timeoutList[i].type == "RECONSENSUS" :
                        protocols.doConsensus()
                    
                    #If a peer timeout happens, we're going to remove that peer from the list we have
                    elif self.timeoutList[i].type == "PEER" :
                        protocols.PEERS.pop(i)
                    
                    #If a stats reply timeout happens, then we're going to move forward with finding the
                    #longest chain process.
                    elif self.timeoutList[i].type == "STATS_REPLY" :
                        protocols.findLongest()
                    
                    #If a join timeout happens, then we're going to start a consensus
                    elif self.timeoutList[i].type == "JOIN" :
                        protocols.doConsensus()
                    
                    #Adding all of the timeout to the removedTimeouts list so we can remove them all at the end
                    removedTimeouts.append(i)
        
        #Used to remove timeouts from the list if they've already expired. If nothing timed out, do nothing.
        if len(removedTimeouts) > 0 :
            for i in range(len(removedTimeouts)) :
                self.timeoutList.pop(i)
    
    #This will cause the timeout to expire and we'll then 
    def joinedNetwork ( self ) :
        self.timeoutList[0].expires = time.time()
    
    def updatePeer ( self, host, port ) :
        pass


#Class containing all of the protocols and messages
#have a timeouts list in here to figure out when we need to send our messages out.
class Protocols :
    def __init__(self, peer:Peer, timeoutQueue:TimeoutQueue) :
        peer.addPeer(peer)
        self.PEERS = peer.getPeers()
        self.GOSSIPS = [] #Literally just to keep track of the gossips that we've gotten already
        self.BLOCKS = [] #This is the blockchain that we have
        self.TIMEOUTQUEUE = timeoutQueue
        self.STATSLIST = []
        self.joined = False
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
            except :
                print("Something went wrong in sending to host:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.PEERS,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(response).encode(),(thePeers[i].hostname,thePeers[i].portnum))
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

    #When we get a gossip message, we know that we've successfully joined the network.
    def processGossip ( self, message ) :
        #Checking if the message itself is in the valid format
        if ( type(message['host']) == str and type(message['port']) == int ) :
            
            senderHost = message['host']
            senderPort = message['port']
            #We haven't seen any gossips yet
            if len(self.GOSSIPS) == 0 :
                self.sendGossipReply(senderHost,senderPort)
                self.sendReceivedGossip(message)
                self.GOSSIPS.append(message['id'])
            else :
                goAhead = True
                for i in range(len(self.GOSSIPS)) :
                    #We've seen this gossip message, we shouldn't send a gossip reply or add it to our list
                    if ( message['id'] == self.GOSSIPS[i] ) :
                        goAhead = False
                if goAhead == True :
                    self.sendGossipReply(senderHost,senderPort)
                    self.sendReceivedGossip(message)
                    self.GOSSIPS.append(message['id'])

            #If this is our official joining into the network, set our flag to true! Can do a consensus now.
            if ( self.joined == False ) :
                self.joined = True
                #Now it's time to join the network
                self.TIMEOUTQUEUE.joinedNetwork()
        else :
            print("The gossip that was sent had an invalid format.")
    
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

        #Checking if the message itself is in the valid format
        if ( type(message['host']) == str and type(message['port']) == int ) :
            #First peer to join! (other than the well-known one)
            peer = Peer(message['host'],message['port'])
            if len(self.PEERS) <= 1 :
                self.PEERS.append(peer)
                self.TIMEOUTQUEUE.addTimeout("PEER")
            else :
                doIt = True
                for i in range(len(self.PEERS)) :
                    if (self.PEERS[i].equals(peer)) :
                        doIt = False
                if doIt == True :
                    #WILL NEED TO ADD MORE LOGIC TO RESET THE TIMEOUT SO THAT THEY DON'T GET CUT OUT THEN READDED
                    self.PEERS.append(peer)
                    self.TIMEOUTQUEUE.addTimeout("PEER")
        else :
            print("The given gossip reply had an invalid format.")

    def sendStats (self) :
        response = {
            "type" : "STATS"
        }
        print("Sending stats: " + str(response))
        #Send stats to all peers at once!
        for i in range(len(self.PEERS)) :
            try :
                SOCKET.sendto(json.dumps(response).encode(),(self.PEERS[i].hostname,self.PEERS[i].portnum))
            except :
                print("Something went wrong when asking for stats:")
                traceback.print_exc()
        #If we got here, it means that we can now successfully wait for the replies, then continue with the consensus
        self.TIMEOUTQUEUE.addTimeout("STATS_REPLY")

    def sendStatsReply ( self, host:str, port:int ) :
        #only send a stats reply if we have a chain
        if ( len(self.BLOCKS ) >= 1 ) :
            response = {
                "type" : "STATS_REPLY",
                "height" : self.BLOCKS[len(self.BLOCKS)-1].height, #This logic is definitely wrong.
                "hash" : self.BLOCKS[len(self.BLOCKS)-1].hash
            }
            print("Sending stats reply: " + str(response))
            try :        
                #Sending it back to the one who sent the first response
                SOCKET.sendto(json.dumps(response).encode(),(host,port))
            except :
                print("Something happened when sending the stats reply back:")
                traceback.print_exc()
        else :
            print("We don't have any blocks to send...")
    
    def processStats ( self, message, address ) :
        print("Received stats message: " + str(message))
        #We'll just need to send a stats reply back to the person who sent the message to us
        self.sendStatsReply(address[0],address[1])
    
    def processStatsReply ( self, message, address ) :
        print("Received stats reply: " + str(message))
        #Here I'm creating a stats instance to add to our list of obtained stats, but checking if it's valid first
        if ( type(message['height']) == int and type(message['hash']) == str ) :
            stat = Stat(message['height'],message['hash'],address[0],address[1])
            self.STATSLIST.append(stat)
        else : 
            print("The stats reply message we received had an invalid format.")

    def resetStats ( self ) :
        self.STATSLIST = []

    def doConsensus ( self ) :
        #If there's no timeout for waiting for stats replies currently, let's start a consensus 
        if ( type(self.TIMEOUTQUEUE.getTimeout("STATS_REPLY")) == None ) :
            #Need to reset the statistics so that we can get a fresh set of them
            self.resetStats()
            
            self.sendStats() 
            #After sending the stats out, we need to wait to get all of them back before trying to find which
            #one is the longest. Added a timeout in the sendStats function, which will then trigger finding
            #the longest chain with what we've got so far.
        else :
            print("Already doing a consensus...")    
    
    #This needs to be rewritten, wtf is going on here LMAO
    def findLongest ( self ) :
        #Make a 2D list of everyone who agrees on the height and hash contained within the message.
        #so, if the messages are the same, then they can all go into that index of the list
        agreed = [[]]

        print(len(self.STATSLIST))

        agreed.append(self.STATSLIST[0])

        for i in range(1,len(self.STATSLIST)) :
            if ( (agreed[i][i].height == self.STATSLIST[i].height) and (agreed[i].hash == self.STATSLIST[i].hash) ) :
                pass
        #Need to ask for blocks as this comes from the consensus
        #self.askForBlocks(height,chain,peers)
        '''
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
        '''
        
    def askForBlocks ( self, height, chain, peers ) :
        #Send GET_BLOCK requests to all peers that agreed
        self.sendGetBlock(height, peers)

    def sendGetBlock ( self, height, peers ) :
        response = {
            "type" : "GET_BLOCK",
            "height" : height
        }
        #Here so that we can avoid starting off with a bad peer. Starting at a random index.
        counter = int(random()*len(peers))
        for i in range(len(peers)) :
            try :
                SOCKET.sendto(json.dumps(response).encode(),(peers[counter].hostname,peers[counter].portnum))
                #Wait for their response in a timeout amount of time . . .
            except :
                print("Something happened when sending the get block:")
                traceback.print_exc()
            counter = counter + 1
            if ( counter % len(peers) == 0 ) :
                counter = 0
    
    def sendGetBlockReply ( self, height:int, host:str, port:int ) :
        #Valid height given?
        #only send a get block reply if we have a chain
        if ( len(self.BLOCKS ) >= 1 ) :
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
                #sending it back to the one who sent the first message
                try :
                    SOCKET.sendto(json.dumps(response).encode(),(host,port))
                except :
                    print("Something happened when sending the get block reply:")
                    traceback.print_exc()
    
    def processGetBlock ( self, message, address ) :
        #Message variable only needed for printing
        print("Received get block: " + str(message))
        self.sendGetBlockReply(address[0],address[1])
    
    def processGetBlockReply ( self, message, address ) :
        print("Received get block reply: " + str(message) + "\tfrom: " + address)
        
        if ( type(message['height']) == str and type(message['hash']) == str and type(message['minedby']) == str and
            type(message['messages']) == list and type(message['timestamp']) == time and type(message['nonce']) == str) :

            #Do some stuff, creating a hash and block from the message we got and then validating the block

            chain = hashlib.sha256()
                    
            chain.update(message['hash'].encode())

            chain.update(message['minedby'].encode())
                    
            for i in range(len(message['messages'])) :
                chain.update(message['messages'][i].encode())
                
            chain.update(message['timestamp'].to_bytes(8,'big'))
                    
            chain.update(message['nonce'].encode())
                    
            hash = chain.hexdigest()
                
            block = Block(message['height'],hash,message['messages'],message['nonce'],message['time'])
            self.validateBlock(block)
        else :
            print("The format of the given get block reply was invalid.")
    
    def validateBlock ( self, block ) :
        #How do I know what the correct hash is though?
        result = True
        if ( block.hash != self.BLOCKS[len(self.BLOCKS)-1].hash) :
            print("The hash from this block doesn't match the correct hash.")
            result = False
        else :
            #Checking if there are too many messages
            if ( len(block.messages) <= 0 or len(block.messages) > 10 ) :
                print("The number of messages in this block is invalid!")
                result = False
            else :
                #Checking the length of each of the messages themselves
                messagesLen = 0
                for i in range (len(block.messages)) :
                    messagesLen = messagesLen + len(block.messages[i])
                if (messagesLen <= 0 or messagesLen > 20) :
                    print("The total length of the messages in this block is invalid!")
                    result = False
                else :
                    #Checking the length of the nonce
                    if len(block.nonce) <= 0 or len(block.nonce) > 40 :
                        print("The length of the nonce of this block is invalid!")
                        result = False
                    else :
                        #Checking the hash's difficulty
                        if block.hash[-1*DIFFICULTY:] != '0' * DIFFICULTY :
                            print("The block's hash was not difficult enough: {}".format(hash))
                            result = False
        #If it gets through all of these statements, then it is a valid block
        return result
    
    #This validates our entire blockchain
    def validateChain ( self ) :
        isValid = True
        for i in range(len(self.BLOCKS)) and isValid :
            isValid = self.validateBlock(self.BLOCKS[i])
        #Once we're at the end, it should be a valid chain
        if isValid :
            print("The chain is still valid! :D")
        else :
            print("The chain is not valid! :(")
    
    def processAnnounce ( self, message ) :
        #process the announce message
        print("Got an announcement: " + str(message))
        #Checking if the message itself is in the valid format
        if ( type(message['hash']) == str and type(message['minedby']) == str and type(message['messages']) == list
             and type(message['timestamp']) == time and type(message['nonce']) == str and type(message['height']) == str ) :
            
            if message['hash'][-1*DIFFICULTY:] != '0' * DIFFICULTY:
                print("Block was not difficult enough: {}".format(hash))
            else :
                block = Block(message['height'],message['hash'],message['nonce'],message['time'])
                #If the block ended up being valid, add it to the chain
                if ( self.validateBlock(block) ) :
                    #Now, add this block to our chain.
                    self.BLOCKS.append(block)
                    
                    #Checking if we're currently in the middle of doing a consensus (doing one if there's a current stats reply timeout working),
                    #we'll need to redo the consensus now that we added a block. This covers one of the edge cases in the assignment outline.
                    statsTimeout = self.TIMEOUTQUEUE.getTimeout("STATS_REPLY")
                    if ( statsTimeout != None and statsTimeout.type == "STATS_REPLY" ) :
                        self.TIMEOUTQUEUE.removeTimeout("STATS_REPLY")
                        self.doConsensus()
                else :
                    print("The new block in invalid, silly.")
        else :
            print("The given announcement message had an invalid format.")


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

        self.HOST = sys.argv[1]
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
        self.timeoutQueue.addTimeout("JOIN")

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

        elif ( jsonObj['type'] == "STATS_REPLY" ) :
            self.protocols.processStatsReply(jsonObj, adr)

        elif ( jsonObj['type'] == "ANNOUNCE" ) :
            self.protocols.processAnnounce(jsonObj)

        elif ( jsonObj['type'] == "GET_BLOCK" ) :
            self.protocols.processGetBlock(jsonObj, adr)

        elif ( jsonObj['type'] == "GET_BLOCK_REPLY" ) :
            self.protocols.processGetBlockReply(jsonObj)

        elif ( jsonObj['type'] == "CONSENSUS" or jsonObj['type'] == "DO_CONSENSUS" ) :
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

        #Just here for testing for now . . .
        if buffer == 20 :
            processingMessages.afterWeJoined()
    
        buffer = buffer+1

    except KeyboardInterrupt as ki:
        print("User exited process.")
        sys.exit(0)