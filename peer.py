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


# constants
HOST = ''
PORT = 8680 #I have 8680-8684
ID = str(uuid.uuid4()) #Creating a uuid for this peer...?
NAME = ":]"
#Only needed if I do the mining part
MESSAGES = ["She", "sells", "sea", "shells", "by the", "sea", "shore."]

JOIN_DELAY = 10000  #Set to a huge number as it'll just be overridden
STATS_TIMEOUT = 10
PEER_TIMEOUT = 90   #every minute and a half, remove dead peer
REGOSSIP = 30       #every thirty seconds (as per instructions)
RECONSENSUS = 120   #every 2 minutes
CHECK_CHAIN = 5     #every 5 seconds

KNOWN_HOST = '192.168.102.146'#'silicon.cs.umanitoba.ca'
KNOWN_PORT = 8999

DIFFICULTY = 8


#Class for being able to access the hostname and port number of each peer
class Peer :
    peerList = []
    def __init__(self,host:str,port:int) :
        self.host = host
        self.port = port
    def addPeer ( self, peer ) :
        self.peerList.append(peer)
    def dropPeer ( self, peer ) :
        self.peerList.remove(peer)
    def getPeers ( self ) :
        return self.peerList
    def equals ( self, peer ) :
        result = False
        if ( self.host == peer.host and self.port == peer.port ) :
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
    def __init__(self, height:int, hash:str, messages, minedBy:str, nonce:str, timestamp:int) :
        self.height = height
        self.hash = hash
        self.messages = messages #A list of messages
        self.minedBy = minedBy
        self.nonce = nonce
        self.timestamp = timestamp
    def addBlock(self, block) :
        self.blockchain.append(block)
    
    
#Class for the queue of timeouts
class Timeout : 
    peerIds = 0
    
    def __init__(self, type:str, host:str=None, port:int=None) :
        self.start = time.time()
        self.type = type
        self.expires = self.expiryTime()
        if ( host != None and port != None ) :
            self.host = host
            self.port = port

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
        elif self.type == "GET_BLOCK" :
            result = self.start + STATS_TIMEOUT #Doesn't need to be different, really
        elif self.type == "CHECK_CHAIN" :
            result = self.start + CHECK_CHAIN
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
        
    def addTimeout ( self, type:str, host:str=None, port:int=None ) :
        if ( host is None and port is None ) :
            timeout = Timeout(type)
        else :
            timeout = Timeout(type, host, port)
        self.timeoutList.append(timeout)
        #print(self.timeoutList[0])
        
    def getTimeout ( self, type:str ) :
        result = None
        for i in range(len(self.timeoutList)) :
            if self.timeoutList[i].type == type :
                result = self.timeoutList[i]
        return result
    
    #Used to forcibly remove a specific type of timeout from the list of timeouts we have
    def removeTimeout ( self, type:str, host:str=None, port:int=None ) :
        if ( host != None and port != None ) :
            for i in range(len(self.timeoutList)) :
                if ( self.timeoutList[i].type == type and 
                    (self.timeoutList[i].host == host and self.timeoutList[i].port == port) ):
                    self.timeoutList.pop(i)
        else :
            for i in range(len(self.timeoutList)) :
                if self.timeoutList[i].type == type :
                    self.timeoutList.pop(i)

    #Send it the protocols object so it can do a call back to it
    def handleTimeouts ( self, protocols ) :
        #this won't run if there aren't any timeouts in the list

        #Making sure there are timeouts in the list to go through
        if len(self.timeoutList) > 0 :
            #Iterating through the list
            for timeout in self.timeoutList :
                #Checking if the current timeout is gonna expire
                if timeout.expires <= time.time() :
                    #If a regossip timeout happens, we need to rest the gossips we have, and send out more
                    if timeout.type == "REGOSSIP" :
                        protocols.resetGossips()
                        protocols.sendGossip()
                        self.addTimeout("REGOSSIP")
                    
                    #If a reconsensus timeout happens, we're going to rerun a consensus
                    elif timeout.type == "RECONSENSUS" :
                        protocols.doConsensus()
                        self.addTimeout("RECONSENSUS")
                    
                    #If a peer timeout happens, we're going to remove that peer from the list we have
                    elif timeout.type == "PEER" :
                        protocols.peers.pop(0)
                    
                    #If a stats reply timeout happens, then we're going to move forward with finding the
                    #longest chain process.
                    elif timeout.type == "STATS_REPLY" :
                        protocols.findLongest()
                    
                    elif timeout.type == "GET_BLOCK" :
                        protocols.checkGetBlock(timeout.host, timeout.port)
                        
                    elif timeout.type == "CHECK_CHAIN" :
                        protocols.checkChainStatus()
                    
                    #Now we remove this timeout
                    self.timeoutList.remove(timeout)

    #This will cause the timeout to expire and we'll then trigger a consensus
    def joinedNetwork ( self, protocols ) :
        self.timeoutList.pop(0)
        protocols.doConsensus()
        #self.timeoutList[0].expires = time.time()
        #for i in range(len(self.timeoutList)) :
        #    if self.timeoutList[i].type == "JOIN" :
        #        self.timeoutList[i].expires = time.time()
        #        break
    
    def updatePeer ( self, host, port ) :
        pass


#Class containing all of the protocols and messages
#have a timeouts list in here to figure out when we need to send our messages out.
class Protocols :
    def __init__(self, peer:Peer, timeoutQueue:TimeoutQueue) :
        peer.addPeer(peer)
        self.peers = peer.getPeers()
        self.gossips = [] #Literally just to keep track of the gossips that we've gotten already
        self.blocks = [] #This is the blockchain that we have
        self.timeoutQueue = timeoutQueue
        self.statsList = []
        self.joined = False
        self.longestChain = [] #Holds the information for the longest chain computations
        self.agreedPeers = []  #Holds the information for the peers who agree on the longest chain
        self.getBlocks = []    #A list to hold which responses we got back
        #These are needed for us to be able to send the proper get block requests
        self.highestHeight = 0
        self.highestHeightIndex = 0 #Just of the longest chain list
        self.highestHash = ''
        self.chainReady = False
        self.checkedBlocks = []

    #functions
    def sendGossip ( self ) :
        print("in sendGossip")
        response = {
            "type" : "GOSSIP",
            "host" : HOST,
            "port" : PORT,
            "id" : ID,
            "name" : NAME
        }
        #print("Sending gossip: " + str(response))
        
        #Send it to 3 peers we know of doing random.choices or send it to the ones we do know
        if ( len(self.peers) < 3 ) :
            try : 
                for i in range(len(self.peers)) :
                    SOCKET.sendto(json.dumps(response).encode(),(self.peers[i].host,self.peers[i].port))
            except :
                print("Something went wrong in sending to host:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.peers,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(response).encode(),(thePeers[i].host,thePeers[i].port))
                except :
                    print("Something went wrong in sending to peers:")
                    traceback.print_exc()
        self.timeoutQueue.addTimeout("REGOSSIP")

    def sendReceivedGossip ( self, message ) :
        print("in sendReceivedGossip")
        #print("Forwarding gossip: " + str(message))
        #Send it to 3 peers we know of doing random.choices or send it to the ones we do know
        if ( len(self.peers) < 3 ) :
            try :
                for i in range(len(self.peers)) :
                    SOCKET.sendto(json.dumps(message).encode(),(self.peers[i].host,self.peers[i].port))
            except :
                print("Something went wrong in sending to all currently known peers:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.peers,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(message).encode(),(thePeers[i].host,thePeers[i].port))
                except :
                    print("Something went wrong in sending to 3 peers:")
                    traceback.print_exc()

    #When we get a gossip message, we know that we've successfully joined the network.
    def processGossip ( self, message ) :
        print("in processGossip")
        try :            
            senderHost = message['host']
            senderPort = message['port']
            #We haven't seen any gossips yet
            if len(self.gossips) == 0 :
                self.sendGossipReply(senderHost,senderPort)
                self.sendReceivedGossip(message)
                self.gossips.append(message['id'])
            else :
                goAhead = True
                for i in range(len(self.gossips)) :
                    #We've seen this gossip message, we shouldn't send a gossip reply or add it to our list
                    if ( message['id'] == self.gossips[i] ) :
                        goAhead = False
                        #break
                if goAhead == True :
                    self.sendGossipReply(senderHost,senderPort)
                    self.sendReceivedGossip(message)
                    self.gossips.append(message['id'])

            #If this is our official joining into the network, set our flag to true! Can do a consensus now.
            if ( self.joined == False ) :
                self.joined = True
                #Now it's time to join the network
                self.timeoutQueue.joinedNetwork(self)
        except :
            traceback.print_exc()
    
    def sendGossipReply ( self, host:str, port:int ) :
        print("in sendGossipReply")
        response = {
            "type" : "GOSSIP-REPLY",
            "host" : HOST,
            "port" : PORT,
            "name" : NAME
        }
        #print("Sending gossip reply: " + str(response))
        #sending it back to the one who sent the original gossip message
        try :
            SOCKET.sendto(json.dumps(response).encode(),(host,port))
        except :
            print("Something went wrong in sending the reply:")
            traceback.print_exc()
    
    def resetGossips ( self ) :
        self.gossips.clear()
    
    def processGossipReply ( self, message ) :
        print("in processGossipReply")
        #print("Received gossip reply: " + str(message))

        #Checking if the message itself is in the valid format
        try :
            #First peer to join! (other than the well-known one)
            peer = Peer(message['host'],message['port'])
            if len(self.peers) <= 1 :
                self.peers.append(peer)
                self.timeoutQueue.addTimeout("PEER")
            else :
                doIt = True
                for i in range(len(self.peers)) :
                    if (self.peers[i].equals(peer)) :
                        doIt = False
                if doIt == True :
                    #WILL NEED TO ADD MORE LOGIC TO RESET THE TIMEOUT SO THAT THEY DON'T GET CUT OUT THEN READDED
                    self.peers.append(peer)
                    self.timeoutQueue.addTimeout("PEER")
        except :
            print("The given gossip reply had an invalid format.")

    def sendStats (self) :
        print("in sendStats")
        response = {
            "type" : "STATS"
        }
        #print("Sending stats: " + str(response))
        #Send stats to all peers at once!
        for i in range(len(self.peers)) :
            try :
                print("Sending to: " + str(self.peers[i].host) + ":" + str(self.peers[i].port))
                SOCKET.sendto(json.dumps(response).encode(),(self.peers[i].host,self.peers[i].port))
            except :
                print("Something went wrong when asking for stats:")
                traceback.print_exc()
        #If we got here, it means that we can now successfully wait for the replies, then continue with the consensus
        self.timeoutQueue.addTimeout("STATS_REPLY")

    def sendStatsReply ( self, host:str, port:int ) :
        print("sendStatsReply")
        #only send a stats reply if we have a chain
        #if ( len(self.blocks) >= 1 ) :
        if ( self.chainReady ) :
            response = {
                "type" : "STATS_REPLY",
                "height" : self.highestHeight,
                #"hash" : self.blocks[self.highestHeight-1].hash
                "hash" : self.highestHash
            }
            #print("Sending stats reply: " + str(response))
            try :        
                #Sending it back to the one who sent the first response
                SOCKET.sendto(json.dumps(response).encode(),(host,port))
            except :
                print("Something happened when sending the stats reply back:")
                traceback.print_exc()
        else :
            print("We don't have any stats to send...")
    
    def processStats ( self, message, address ) :
        print("in processStats")
        #print("Received stats message: " + str(message))
        #We'll just need to send a stats reply back to the person who sent the message to us
        self.sendStatsReply(address[0],address[1])
    
    def processStatsReply ( self, message, address ) :
        print("in processStatsReply")
        #print("Received stats reply: " + str(message))
        #Here I'm creating a stats instance to add to our list of obtained stats
        try :
            stat = Stat(message['height'],message['hash'],address[0],address[1])
            self.statsList.append(stat)
        except : 
            traceback.print_exc()

    def resetStats ( self ) :
        self.statsList = []

    def doConsensus ( self ) :
        print("in doConsensus")
        #If there's no timeout for waiting for stats replies currently, let's start a consensus 
        if ( self.timeoutQueue.getTimeout("STATS_REPLY") == None ) :
            #Need to reset the statistics so that we can get a fresh set of them
            self.resetStats()
            
            self.sendStats() 
            #After sending the stats out, we need to wait to get all of them back before trying to find which
            #one is the longest. Added a timeout in the sendStats function, which will then trigger finding
            #the longest chain with what we've got so far.
            
            #We will need to ask for the blocks from everyone, starting a timeout, keeping track of which
            #peers answered, and then validate the chain once we've gotten all of the peers' responses.
            self.timeoutQueue.addTimeout("CHECK_CHAIN")
        else :
            print("Already doing a consensus...")
            
    def restartConsensus ( self ) :
        print("in restartConsensus")
        #The original consensus failed. Let's move to find the next most agreed-upon longest chain.
        self.longestChain.pop(self.highestHeightIndex)
        self.findMajority()
    
    def findLongest ( self ) :
        print("in findLongest")
        #Only called once we have all of the stats replies, so statsList shouldn't be empty
        if ( len(self.statsList) == 0 ) :
            print("Nobody sent us stat replies, we can't decide what the longest chain is...")
        #Continue, as planned
        else :
            #Fill it with a starting list of the first stat, so we can append to it
            self.longestChain.append([self.statsList[0]])

            #looping through the entire stats list, skipping the first index (we already added it)
            for i in range(len(self.statsList)) :
                notAdded = True
                #looping through the entire length of our 2D list
                for j in range(len(self.longestChain)) :
                    #If the hash and height is equal, append it to the end of this list
                    if ( self.statsList[i].height == self.longestChain[j][0].height and
                        self.statsList[i].hash == self.longestChain[j][0].hash ) :
                        self.longestChain[j].append(self.statsList[i])
                        notAdded = False
                        break
                if notAdded == True :
                    #We haven't seen any matches for height and hash so far, let's add it as a new
                    #entry to the longestChain list
                    self.longestChain.append([self.statsList[i]])
        self.findMajority()

    def findMajority ( self ) :
        print("in findMajority")
        #Used to identify which index and which height is the max height we found
        self.highestHeightIndex = 0
        if ( len(self.longestChain) <= 0 ) :
            print("There are no valid chains on this network...")
        else :
            self.highestHeight = self.longestChain[0][0].height
            #Looping through our longest chain list to see which height is the highest and where
            #it is stored within that list
            for i in range(len(self.longestChain)) :
                if ( self.highestHeight < self.longestChain[i][0].height ) :
                    self.highestHeight = self.longestChain[i][0].height
                    self.highestHeightIndex = i
                    self.highestHash = self.longestChain[i][0].hash
                #edge case for there being two equal heights, but only one has the majority
                if ( self.highestHeight == self.longestChain[i][0].height ) :
                    #If the "new" one has more peers, then that's actually the highest we want to keep track of
                    if ( len(self.longestChain[self.highestHeightIndex]) < len(self.longestChain[i]) ) :
                        self.highestHeight = self.longestChain[i][0].height
                        self.highestHeightIndex = i
                        self.highestHash = self.longestChain[i][0].hash
                
            #So now we know that the highest height is stored in highestHeight with the majority of peers
            #This list of peers is so that we can send them all a get block message
            self.agreedPeers = []
            for i in range(len(self.longestChain[self.highestHeightIndex])) :
                self.agreedPeers.append(Peer(self.longestChain[self.highestHeightIndex][i].host,
                                self.longestChain[self.highestHeightIndex][i].port))
                
            #Now we can ask for all of the blocks from these peers
            self.askForBlocks()

    #This is where I do the load balancing for sending the get blocks, giving the indices of the
    #height of the chain that we currently have to all of the peers who agreed upon the chain
    def askForBlocks ( self ) :
        print("in askForBlocks")
        #Restarting the get block process, we need a fresh list of them since we either haven't
        #gotten any yet, or we need to restart grabbing them.
        self.getBlocks = []
        self.blocks = []
        self.checkedBlocks = []
        
        #Here so that we can avoid starting off with a bad peer. Starting at a random index.
        counter = int(random.random()*len(self.agreedPeers))
        #We're handling each of the heights for the get blocks
        for i in range(self.highestHeight) :
            self.sendGetBlock(i,self.agreedPeers[counter].host,self.agreedPeers[counter].port)
            counter = counter + 1
            if ( counter % len(self.agreedPeers) == 0 ) :
                counter = 0
            
    #Used to know which peer to drop from our known peers list and what we need to send out for it.
    #We'll need to resend the get blocks for the indices that weren't filled.
    def resendGetBlocks ( self, host, port ) :
        print("in resendGetBlocks")
        #Finding the index of the bad peer and removing it
        for i in range(len(self.agreedPeers)) :
            if ( self.agreedPeers[i].host == host and self.agreedPeers[i].port == port ) :
                self.agreedPeers.pop(i)
                break
        
        heights = []
        #Finding which indices weren't filled
        for i in range(len(self.blocks)) :
            if ( self.blocks[i] == None ) :
                heights.append(i)
                
        #Now sending out the rest of the get block requests that weren't fulfilled
        counter = int(random.random()*len(self.agreedPeers))
        for i in range(len(heights)) :
            self.sendGetBlock(heights[i],self.agreedPeers[counter].host,self.agreedPeers[counter].port)
            counter = counter + 1
            if ( counter % len(self.agreedPeers) == 0 ) :
                counter = 0

    def sendGetBlock ( self, height, host, port ) :
        print("in sendGetBlock")
        response = {
            "type" : "GET_BLOCK",
            "height" : height
        }
        try :
            SOCKET.sendto(json.dumps(response).encode(),(host,port))
            self.timeoutQueue.addTimeout("GET_BLOCK",host,port)
        except :
            traceback.print_exc()
        
    def sendGetBlockReply ( self, height:int, host:str, port:int ) :
        print("in sendGetBlockReply")
        #only send a get block reply if we have a chain
        #if ( len(self.blocks) >= 1 ) :
        if ( self.chainReady ) :
            #Was a valid height provided?
            if ( height <= 0 or height >= len(self.blocks) ) :
                response =  {
                    "type" : "GET_BLOCK_REPLY",
                    "hash" : None,
                    "height" : None,
                    "messages" : None,
                    "minedBy" : None,
                    "nonce" : None,
                    "timestamp" : None
                }
            else :
                response  = {
                    "type" : "GET_BLOCK_REPLY",
                    "hash" : self.blocks[height].hash,
                    "height" : height,
                    "messages" : self.blocks[height].message,
                    "minedBy" : self.blocks[height].name,
                    "nonce" : self.blocks[height].nonce,
                    "timestamp" : self.blocks[height].time
                }
            #sending it back to the one who sent the first message
            try :
                SOCKET.sendto(json.dumps(response).encode(),(host,port))
            except :
                print("Something happened when sending the get block reply:")
                traceback.print_exc()
        else :
            print("We don't have a block to respond with.")
    
    def processGetBlock ( self, message, address ) :
        print("in processGetBlock")
        #Message variable only needed for printing
        #print("Received get block: " + str(message))
        self.sendGetBlockReply(address[0],address[1])
    
    def processGetBlockReply ( self, message, address ) :
        print("in processGetBlockReply")
        #print("Received get block reply: " + str(message) + "\tfrom: " + address)
        
        try :
            #We don't have the genesis block so make this it 
            if ( len(self.blocks) == 0 ) :
                block = Block(message['height'],None,message['messages'],message['minedBy'],message['nonce'],message['timestamp'])
            else :
                block = Block(message['height'],message['hash'],message['messages'],message['minedBy'],message['nonce'],message['timestamp'])

            self.blocks.append(block)

            #This is here to confirm that we've received this getBlockReply for our timeout
            self.getBlocks.append(Peer(address[0],address[1]))
        except :
            traceback.print_exc()
    
    def checkGetBlock ( self, host, port ) :
        print("in checkGetBlock")
        gotBlock = False
        for i in range(len(self.getBlocks)) :
            if (self.getBlocks[i].host == host and self.getBlocks[i].port == port) :
                #The timeout is ok since we already got its reply.
                gotBlock = True
                self.checkedBlocks.append(0)
                break
        #So if we didn't get the block, we have to resend the request
        if ( gotBlock == False ) :
            self.resendGetBlocks(host, port)
            self.checkedBlocks.append(1)


    def validateBlock ( self, block, prevHash=None ) :
        print("in validateBlock")
        #Return the hash representation for this block
        result = True
        thisHash = None
        try :
            if ( block.hash != prevHash) :
                print("The hash in this block doesn't match the previous hash.")
                result = False
            else :
                #Checking if there are too many messages
                if ( len(block.messages) <= 0 or len(block.messages) > 10 ) :
                    print("The number of messages in this block is invalid! " + str())
                    result = False
                else :
                    #Checking the length of each of the messages themselves
                    messagesLen = 0
                    for i in range(len(block.messages)) :
                        messagesLen = len(block.messages[i])
                    if (messagesLen <= 0 or messagesLen > 20) :
                        print("The length of the messages in this block is invalid! " + str(messagesLen))
                        result = False
                    else :
                        #Checking the length of the nonce
                        if len(block.nonce) <= 0 or len(block.nonce) > 40 :
                            print("The length of the nonce of this block is invalid! " + block.nonce)
                            result = False
                        else :
                            #Checking the hash's difficulty
                            if block.hash != None :
                                if block.hash[-1*DIFFICULTY:] != '0' * DIFFICULTY :
                                    print("The block's hash was not difficult enough: {}".format(hash))
                                    result = False
            #If it gets through all of these statements, then it is a valid block
            if result :
                thisHash = hashlib.sha256()
                #We already have the genesis block, include the hash.
                if ( block.hash != None ) :
                    thisHash.update(block.hash.encode())

                thisHash.update(block.minedBy.encode())
                            
                for i in range(len(block.messages)) :
                    thisHash.update(block.messages[i].encode())
                        
                thisHash.update(block.timestamp.to_bytes(8,'big'))
                            
                thisHash.update(block.nonce.encode())
                
                #This is the hash representation for this block       
                thisHash = thisHash.hexdigest()
        except :
            traceback.print_exc()
        #If this returns None, then the block was invalid
        return thisHash
    
    #This validates our entire blockchain
    def validateChain ( self ) :
        print("in validateChain")
        prevHash = None
        isValid = True
        for i in range(len(self.blocks)) :
            prevHash = self.validateBlock(self.blocks[i],prevHash)
            if ( prevHash == None ) :
                isValid = False
                break
        #Once we're at the end, it should be a valid chain
        if isValid :
            print("The chain is still valid! :D")
            self.chainReady = True
        else :
            print("The chain is not valid! :(")
            self.chainReady = False
            self.restartConsensus()
    
    def processAnnounce ( self, message ) :
        print("in processAnnounce")
        #process the announce message
        #print("Got an announcement: " + str(message))
        #Checking if the message itself is in the valid format
        try :    
            if message['hash'][-1*DIFFICULTY:] != '0' * DIFFICULTY:
                print("Block was not difficult enough: {}".format(hash))
            else :
                block = Block(message['height'],message['hash'],message['messages'],message['minedBy'],message['nonce'],time.time())
                #If the block ended up being valid, add it to the chain
                if ( self.validateBlock(block) ) :
                    #Now, add this block to our chain.
                    self.blocks.append(block)
                    
                    #Checking if we're currently in the middle of doing a consensus (doing one if there's a current stats reply timeout working),
                    #we'll need to redo the consensus now that we added a block. This covers one of the edge cases in the assignment outline.
                    statsTimeout = self.timeoutQueue.getTimeout("STATS_REPLY")
                    if ( statsTimeout != None and statsTimeout.type == "STATS_REPLY" ) :
                        self.timeoutQueue.removeTimeout("STATS_REPLY")
                        self.doConsensus()
                else :
                    print("The new block in invalid, silly.")
        except :
            traceback.print_exc()

    #Used to see if the chain has been completely filled. If it has, we can move on with the chain validation/consensus
    def checkChainStatus ( self ) :
        print("in checkChainStatus")
        allGood = True
        print("BLOCKS LENGTH: " + str(len(self.blocks)))
        print("HEIGHT: " + str(self.highestHeight))
        if len(self.checkedBlocks) != 0 and sum(self.checkedBlocks) == 0 :
            for i in range(self.highestHeight) :
                if (i >= len(self.blocks)) :
                    allGood = False
            if not allGood :
                print("The chain is not ready to be validated yet.")
                self.timeoutQueue.addTimeout("CHECK_CHAIN")
            else :
                self.validateChain()
        else :
            print("We haven't gotten all of the blocks back yet.")
            self.timeoutQueue.addTimeout("CHECK_CHAIN")
        


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
        self.timeoutQueue.addTimeout("JOIN")
        self.protocols.sendGossip()
        
    def processMessage ( self, message, address ) :
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
            self.protocols.processStats(jsonObj,address)

        elif ( jsonObj['type'] == "STATS_REPLY" ) :
            self.protocols.processStatsReply(jsonObj, address)

        elif ( jsonObj['type'] == "ANNOUNCE" ) :
            self.protocols.processAnnounce(jsonObj)

        elif ( jsonObj['type'] == "GET_BLOCK" ) :
            self.protocols.processGetBlock(jsonObj, address)

        elif ( jsonObj['type'] == "GET_BLOCK_REPLY" ) :
            self.protocols.processGetBlockReply(jsonObj, address)

        #elif ( jsonObj['type'] == "CONSENSUS" or jsonObj['type'] == "DO_CONSENSUS" ) :
        #    self.protocols.doConsensus()

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

    except KeyboardInterrupt as ki:
        print("User exited process.")
        sys.exit(0)