"""
Bootstrapping process is as follows
1. Listen on multicast address
2. Multicast your IP address, listen for responses (IP addresses of other nodes)
3. Store responses
4. If no responses, contact main server for list of nodes
5. Receive list of nodes from main server
6. If no other nodes, try again later
"""

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.application.internet import MulticastServer
import time, datetime, signal, socket
from urllib2 import urlopen
from threading import Thread

signal.signal(signal.SIGINT,signal.SIG_DFL)


##########
# SERVER #
##########

class MulticastServerUDP(DatagramProtocol):
    def startProtocol(self):
        print 'Started Listening'
        # Join a specific multicast group, which is the IP we will respond to
        self.transport.joinGroup('224.0.1.123')

    def datagramReceived(self, datagram, address):
        if datagram != Bootstrapper.myip:
            Bootstrapper.hosts[datagram] = time.mktime(datetime.datetime.utcnow().timetuple()) + 600.0
        print "Bootstrap Server Hosts:", Bootstrapper.hosts
        print "Heard Multicast Datagram:", repr(datagram)
        self.transport.write(Bootstrapper.myip, address)

class MulticastServerThread(Thread):
    def run(self):
        reactor.listenMulticast(8005, MulticastServerUDP())
        #reactor.run(installSignalHandlers=0)

##########
# CLIENT #
##########

class MulticastClientUDP(DatagramProtocol):

    def datagramReceived(self, datagram, address):
        if datagram != Bootstrapper.myip:
            Bootstrapper.hosts[datagram] = time.mktime(datetime.datetime.utcnow().timetuple()) + 600.0
        print "Bootstrap Multicast Client Received:" + repr(datagram)

class MulticastClientThread(Thread):
    def run(self):
        print "sending multicast hello"
        # Send multicast on 224.0.1.123:8005, on our dynamically allocated port
        reactor.listenUDP(0, MulticastClientUDP()).write(Bootstrapper.myip, ('224.0.1.123', 8005))

######################
### INITIALIZATION ###
######################

class Bootstrapper():

    hosts = {}
    myip = urlopen('http://whatismyip.org/').read()

    def bootstrap(self):
        MulticastServerThread().start()
        MulticastClientThread().start()
        #Give multicast a chance to find some friends
        while len(self.hosts)==0:
            continue
        MulticastClientThread.join()

if __name__ == "__main__":
    b = Bootstrapper()
    b.bootstrap()
