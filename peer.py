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
STATS_TIMEOUT = 5
PEER_TIMEOUT = 90   #every minute and a half, remove dead peer
REGOSSIP = 30       #every thirty seconds (as per instructions)
RECONSENSUS = 120   #every 2 minutes
CHECK_CHAIN = 10     #every 10 seconds

KNOWN_HOST = '192.168.102.146'#'silicon.cs.umanitoba.ca'
KNOWN_PORT = 8999

DIFFICULTY = 9


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
        
    def addTimeout ( self, type:str, host:str, port:int ) :
        timeout = Timeout(type, host, port)
        self.timeoutList.append(timeout)
        
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

                    elif self.timeoutList[i].type == "GET_BLOCK" :
                        protocols.checkGetPeers(self.timeoutList[i].host, self.timeoutList[i].port)
                        
                    elif self.timeoutList[i].type == "CHECK_CHAIN" :
                        protocols.checkChainStatus()
                    
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
        self.longestChain = [] #Holds the information for the longest chain computations
        self.agreedPeers = []  #Holds the information for the peers who agree on the longest chain
        self.getBlocks = []    #A list to hold which responses we got back
        #These are needed for us to be able to send the proper get block requests
        self.highestHeight = 0
        self.highestHeightIndex = 0 #Just of the longest chain list

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
                    SOCKET.sendto(json.dumps(response).encode(),(self.PEERS[i].host,self.PEERS[i].port))
            except :
                print("Something went wrong in sending to host:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.PEERS,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(response).encode(),(thePeers[i].host,thePeers[i].port))
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
                    SOCKET.sendto(json.dumps(message).encode(),(self.PEERS[i].host,self.PEERS[i].port))
            except :
                print("Something went wrong in sending to all currently known peers:")
                traceback.print_exc()
        else :
            thePeers = random.choices(self.PEERS,k=3)
            for i in range(3) :
                try :
                    SOCKET.sendto(json.dumps(message).encode(),(thePeers[i].host,thePeers[i].port))
                except :
                    print("Something went wrong in sending to 3 peers:")
                    traceback.print_exc()

    #When we get a gossip message, we know that we've successfully joined the network.
    def processGossip ( self, message ) :
        try :            
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
        except :
            traceback.print_exc()
    
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
        try :
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
        except :
            print("The given gossip reply had an invalid format.")

    def sendStats (self) :
        response = {
            "type" : "STATS"
        }
        print("Sending stats: " + str(response))
        #Send stats to all peers at once!
        for i in range(len(self.PEERS)) :
            try :
                SOCKET.sendto(json.dumps(response).encode(),(self.PEERS[i].host,self.PEERS[i].port))
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
                "height" : self.highestHeight,
                "hash" : self.BLOCKS[self.highestHeight-1].hash
            }
            print("Sending stats reply: " + str(response))
            try :        
                #Sending it back to the one who sent the first response
                SOCKET.sendto(json.dumps(response).encode(),(host,port))
            except :
                print("Something happened when sending the stats reply back:")
                traceback.print_exc()
        else :
            print("We don't have any stats to send...")
    
    def processStats ( self, message, address ) :
        print("Received stats message: " + str(message))
        #We'll just need to send a stats reply back to the person who sent the message to us
        self.sendStatsReply(address[0],address[1])
    
    def processStatsReply ( self, message, address ) :
        print("Received stats reply: " + str(message))
        #Here I'm creating a stats instance to add to our list of obtained stats
        try :
            stat = Stat(message['height'],message['hash'],address[0],address[1])
            self.STATSLIST.append(stat)
        except : 
            traceback.print_exc()

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
            
            #We will need to ask for the blocks from everyone, starting a timeout, keeping track of which
            #peers answered, and then validate the chain once we've gotten all of the peers' responses.
            self.TIMEOUTQUEUE.addTimeout("CHECK_CHAIN")
        else :
            print("Already doing a consensus...")
            
    def restartConsensus ( self ) :
        #The original consensus failed. Let's move to find the next most agreed-upon longest chain.
        self.longestChain[self.highestHeightIndex].pop()
        self.findMajority()
    
    def findLongest ( self ) :
        #Only called once we have all of the stats replies, so STATSLIST shouldn't be empty
        if ( len(self.STATSLIST) == 0 ) :
            print("Nobody sent us stat replies, we can't decide what the longest chain is...")
        #Continue, as planned
        else :
            #Fill it with a starting list of the first stat, so we can append to it
            self.longestChain[0] = [self.STATSLIST[0]]

            #looping through the entire stats list, skipping the first index (we already added it)
            for i in range(1,len(self.STATSLIST)) :
                notAdded = True
                #looping through the entire length of our 2D list
                for j in range(len(self.longestChain) and notAdded ) :
                    #If the hash and height is equal, append it to the end of this list
                    if ( self.STATSLIST[i].height == self.longestChain[j][0].height and
                        self.STATSLIST[i].hash == self.longestChain[j][0].hash ) :
                        self.longestChain[j][0].append(self.STATSLIST[i])
                        notAdded = False
                if notAdded == True :
                    #We haven't seen any matches for height and hash so far, let's add it as a new
                    #entry to the longestChain list
                    self.longestChain.append([self.STATSLIST[i]])
        self.findMajority()

    def findMajority ( self ) :
            #Used to identify which index and which height is the max height we found
            self.highestHeightIndex = 0
            self.highestHeight = self.longestChain[0][0].height
            #Looping through our longest chain list to see which height is the highest and where
            #it is stored within that list
            for i in range(1,len(self.longestChain)) :
                if ( self.highestHeight < self.longestChain[i][0].height ) :
                    self.highestHeight = self.longestChain[i][0].height
                    self.highestHeightIndex = i
                #edge case for there being two equal heights, but only one has the majority
                if ( self.highestHeight == self.longestChain[i][0].height ) :
                    #If the "new" one has more peers, then that's actually the highest we want to keep track of
                    if ( len(self.longestChain[self.highestHeightIndex][0]) < len(self.longestChain[i][0].height) ) :
                        self.highestHeight = self.longestChain[i][0].height
                        self.highestHeightIndex = i
            
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
        #Restarting the get block process, we need a fresh list of them since we either haven't
        #gotten any yet, or we need to restart grabbing them.
        self.getBlocks = []
        self.BLOCKS = []
        
        #Here so that we can avoid starting off with a bad peer. Starting at a random index.
        counter = int(random()*len(self.agreedPeers))
        #We're handling each of the heights for the get blocks
        for i in self.highestHeight :
            self.sendGetBlock(i,self.agreedPeers[counter].host,self.agreedPeers[counter].port)
            counter = counter + 1
            if ( counter % len(self.agreedPeers) == 0 ) :
                counter = 0
            
    #Used to know which peer to drop from our known peers list and what we need to send out for it.
    #We'll need to resend the get blocks for the indices that weren't filled.
    def resendGetBlocks ( self, host, port ) :
        found = False
        #Finding the index of the bad peer and removing it
        for i in range(len(self.agreedPeers)) and not found :
            if ( self.agreedPeers[i].host == host and self.agreedPeers[i].port == port ) :
                self.agreedPeers.pop(i)
                found = True
        
        heights = []
        #Finding which indices weren't filled
        for i in range(len(self.BLOCKS)) :
            if ( self.BLOCKS[i] == None ) :
                heights.append(i)
                
        #Now sending out the rest of the get block requests that weren't fulfilled
        counter = int(random()*len(self.agreedPeers))
        for i in range(len(heights)) :
            self.sendGetBlock(heights[i],self.agreedPeers[counter].host,self.agreedPeers[counter].port)
            counter = counter + 1
            if ( counter % len(self.agreedPeers) == 0 ) :
                counter = 0

    def sendGetBlock ( self, height, host, port ) :
        response = {
            "type" : "GET_BLOCK",
            "height" : height
        }
        try :
            SOCKET.sendto(json.dumps(response).encode(),(host,port))
            self.TIMEOUTQUEUE.addTimeout("GET_BLOCK",host,port)
        except :
            traceback.print_exc()
        
    def sendGetBlockReply ( self, height:int, host:str, port:int ) :
        #only send a get block reply if we have a chain
        if ( len(self.BLOCKS) >= 1 ) :
            #Was a valid height provided?
            if ( height <= 0 or height >= len(self.BLOCKS) ) :
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
                    "hash" : self.BLOCKS[height].hash,
                    "height" : height,
                    "messages" : self.BLOCKS[height].message,
                    "minedBy" : self.BLOCKS[height].name,
                    "nonce" : self.BLOCKS[height].nonce,
                    "timestamp" : self.BLOCKS[height].time
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
        
        try :
            #We don't have the genesis block so make this it 
            if ( len(self.BLOCKS) == 0 ) :
                block = Block(message['height'],None,message['messages'],message['nonce'],message['time'])
            else :
                block = Block(message['height'],message['hash'],message['messages'],message['nonce'],message['time'])

            self.BLOCKS.append(block)

            #This is here to confirm that we've received this getBlockReply for our timeout
            self.getBlocks.append(Peer(address[0],address[1]))
        except :
            traceback.print_exc()
    
    def checkGetBlock ( self, host, port ) :
        gotBlock = False
        for i in range(len(self.getBlocks)) and gotBlock == False :
            if (self.getBlocks[i].host == host and self.getBlocks[i].port == port) :
                #The timeout is ok since we already got its reply.
                gotBlock = True
        #So if we didn't get the block, we have to resend the request
        if ( gotBlock == False ) :
            self.resendGetBlocks(host, port)

    def validateBlock ( self, block, prevHash=None ) :
        #Return the hash representation for this block
        result = True
        thisHash = None
        if ( block.hash != prevHash) :
            print("The hash in this block doesn't match the previous hash.")
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
        if result :
            thisHash = hashlib.sha256()
            #We already have the genesis block, include the hash.
            if ( len(self.BLOCKS) != 0 ) :
                thisHash.update(block['hash'].encode())

            thisHash.update(block['minedby'].encode())
                        
            for i in range(len(block['messages'])) :
                thisHash.update(block['messages'][i].encode())
                    
            thisHash.update(block['timestamp'].to_bytes(8,'big'))
                        
            thisHash.update(block['nonce'].encode())
            
            #This is the hash representation for this block       
            thisHash = thisHash.hexdigest()
        #If this returns None, then the block was invalid
        return thisHash
    
    #This validates our entire blockchain
    def validateChain ( self ) :
        prevHash = None
        isValid = True
        for i in range(len(self.BLOCKS)) and isValid :
            prevHash = self.validateBlock(self.BLOCKS[i],prevHash)
            if ( prevHash == None ) :
                isValid = False
        #Once we're at the end, it should be a valid chain
        if isValid :
            print("The chain is still valid! :D")
        else :
            print("The chain is not valid! :(")
            self.restartConsensus()
    
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

    #Used to see if the chain has been completely filled. If it has, we can move on with the chain validation/consensus
    def checkChainStatus ( self ) :
        allGood = True
        for i in self.highestHeight :
            if (self.BLOCKS[i] == None) :
                allGood = False
        if not allGood :
            print("The chain is not ready to be validated yet.")
        else :
            self.validateChain()
        


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

    except KeyboardInterrupt as ki:
        print("User exited process.")
        sys.exit(0)