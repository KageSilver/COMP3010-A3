#!/usr/bin/python3

#------------------------------------------
# NAME		: Tara Boulanger
# STUDENT NUMBER	: 7922331
# COURSE		: COMP 3010
# INSTRUCTOR	: Robert Guderian
# ASSIGNMENT	: Assignment 2 Part 2
# 
# REMARKS: This is the coordinator of the workers.
#   It utilises the select.select() function to
#   achieve multi-threading. Started after the
#   workers.
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
PORT = 0 #I have 8680-8684
ID = str(uuid.uuid4())
NAME = ":]"
MESSAGES = ["She", "sells", "sea", "shells", "by the", "sea", "shore."]

TIMEOUT = 0.5
REGOSSIP = 30
RECONSENT = 120 #every 2 minutes

KNOWN_HOST = 'silicon.cs.umanitoba.ca'
KNOWN_PORT = 8998

#variables
timeouts = []
peers = [] #for the gossip, choose 3 to randomly send to, it is its own class

height = 0
myHash = ''
myNonce = ''
blockTime = 0


tempGossipID = ''


#Checking timeouts
gossipTime = time.time()
consensusTime = time.time()


#Class for being able to access the hostname and port number of each peer
class Peer :
    hostname = ''
    portnum = 0


#functions
def sendGossip () :
    response = {
        "type" : "GOSSIP",
        "host" : HOST,
        "port" : PORT,
        "id" : ID,
        "name" : NAME
    }
    #Send it to the only well-known peer
    peerSocket.sendto(response.encode(),(KNOWN_HOST,KNOWN_PORT))
    #Retreiving the gossip message back
    result = []
    result[1] = peerSocket.recvfrom(2048).decode()
    return result


def sendReceivedGossip ( message ) :
    for i in len(peers) :
        peerSocket.sendto(message.encode(),(peers[i].hostname,peers[i].portnum))
    #We don't need to get anything back


def processGossip ( message ) :
    #We haven't seen this gossip message yet
    if ( message['id'] != tempGossipID ) :
        senderHost = message['host']
        senderPort = message['port']
        sendGossipReply(senderHost,senderPort)
        sendReceivedGossip(message)
    else :
        #We've already seen this gossip, so no need to resend the gossip reply
        print()
    

def sendGossipReply ( host:str, port:int ) :
    response = {
        "type" : "GOSSIP-REPLY",
        "host" : HOST,
        "port" : PORT,
        "name" : NAME
    }
    #sending it back to the one who sent the first response
    peerSocket.sendto(response.encode(),(host,port))
    
    
def processGossipReply ( message ) :
    #Basically just joining the network by adding this peer to our list
    peer = Peer(host=message['host'],port=message['port'])
    peers.append(peer)


def sendStats () :
    response = {
        "type" : "STATS"
    }
    for i in len(peers) :
        peerSocket.sendto(response.encode(),(peers[i].hostname,peers[i].portnum))
    #Retreiving the stats messages
    result = []
    for i in 3 :
        result[i] = peerSocket.recvfrom(2048).decode()
    return result


def sendStatsReply ( host:str, port:int ) :
    response = {
        "type" : "STATS_REPLY",
        "height" : height,
        "hash" : myHash
    }
    #sending it back to the one who sent the first response
    peerSocket.sendto(response.encode(),(host,port))


def doConsensus () :
    #Do a consensus here
    results = sendStats()
    findLongest(results)
    

def findLongest( stats ) :
    theJson = []
    for i in 3 :
        theJson[i] = json.dumps(stats[i])
    maxHeight = max(theJson['height'])
    indecies = theJson['height'] == maxHeight
    
    for i in indecies :
        hashes = theJson[i].get('hash')
    
    #check for the majority hashes
    #DO STUFF HERE


def sendGetBlock () :
    response = {
        "type" : "GET_BLOCK",
        "height" : height
    }
    for i in len(peers) :
        peerSocket.sendto(response.encode(),(peers[i].hostname,peers[i].portnum))
    #Retreiving the getBlock messages
    result = []
    for i in 3 :
        result[i] = peerSocket.recvfrom(2048).decode()
    return result


def sendGetBlockReply ( host:str, port:int ) :
    response  = {
        "type" : "GET_BLOCK_REPLY",
        "hash" : myHash,
        "height" : height,
        "messages" : MESSAGES,
        "minedBy" : NAME,
        "nonce" : "huh?",   #I have no idea what this is
        "timestamp" : blockTime
    }
    #sending it back to the one who sent the first response
    peerSocket.sendto(response.encode(),(host,port))
    
    
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




#Parsing command line to get host IP and port number
if len(sys.argv) < 2:
    print("Open file as: python3 peer.py ip port")
    sys.exit(1)

HOST = sys.argv[1]
try:
    PORT = int(sys.argv[2])
except:
    print("Bad port number")
    sys.exit(1)

#Opening our socket
peerSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
peerSocket.bind((socket.gethostname(), 0))

hostname = socket.gethostname()
print("listening on interface " + hostname)
port = peerSocket.getsockname()[1]
print('listening on port:', port)

while True :
    # send a message 
    #peerSocket.sendto("hello".encode(), (HOST, PORT))
    #data, addr  = peerSocket.recvfrom(2048) #VERY IMPORTANT FOR recvfrom
    #print(data.decode('utf-8)'))
    
    if ( time.time() > gossipTime + REGOSSIP ) :
        sendGossip()