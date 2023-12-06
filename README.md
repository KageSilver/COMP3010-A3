# COMP 3010 Assignment 3 - Tara Boulanger (7922331)

## Compilation details:
Nothing requires compilation.

## Running details
You can run the peer by typing: `python3 peer.py ip port` where ip is the ip you're connecting from and where port is the port number that you're using for that ip. I use 8680-8684.

### Other notes:
#### Starting consensus:
I start a consensus by setting a timeout before we join the network, and triggering the doConsensus function in the Protocols class once we get a gossip message from the network, meaning our peer has successfully joined the network. It can be triggered when it receives a CONSENSUS or a DO_CONSENSUS message.

#### Peer cleaning:
I clean the peers in my TimeoutsQueue class.

#### Choosing longest chain:
I choose the longest chain in the findLongest() function in the Protocols class.

#### Validating chain:
I validate my chain by calling the validateChain() function in the Protocols class. That function iterates through the list of blocks that I have and validates each of them by calling the validateBlock() function in the Protocols class. The validateBlock() function checks the hash of the given block and many other conditions/constraints outlined in the assignment instructions/discussions. If all of the conditions are met, it will return true for it being a valid block.