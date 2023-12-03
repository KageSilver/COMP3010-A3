# COMP 3010 Assignment 3 - Tara Boulanger (7922331)

## Compilation details:
Nothing requires compilation.

## Running details
For part 1, you can run the webserver by typing: `python3 website.py 8680 localhost:8684`. I was using ports 8680-8684 as they were assigned to me. The `localhost:8684` part is for saying where the coordinator is currently running.
<br>
For part 2, you can run the workers by typing: `python3 worker.py 8681` - where the port numbers can be either 8681, 8682, or 8683. You can then run the coordinator by typing: `python3 coordinator.py 8684`.

### Other notes:
I clean the peers in my TimeoutsQueue class.
