"""
Bootstrapping process is as follows
1. Listen on multicast address
2. Multicast your IP address, listen for responses (IP addresses of other nodes)
3. Store responses
**4. If no responses, contact main server for list of nodes
**5. Receive list of nodes from main server 
**6. If no other nodes, try again later

** Currently Disabled
"""

import json
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.application.internet import MulticastServer
import time, datetime, signal, socket
from urllib2 import urlopen
#from threading import Thread
import threading

signal.signal(signal.SIGINT,signal.SIG_DFL)


##########
# SERVER #
##########

class MulticastServerUDP(DatagramProtocol):

    def __init__(self, pkey):
        self.pkey = pkey

    def startProtocol(self):
        print 'Multicast Server Started Listening....'
        # Join a specific multicast group, which is the IP we will respond to
        self.transport.joinGroup('224.0.1.123')

    def datagramReceived(self, datagram, address):
        ip, pkey = datagram.split()
        if ip != Bootstrapper.myip:
            Bootstrapper.hosts[ip] = pkey
            print "Bootstrap Server Hosts:....", Bootstrapper.hosts
            print "Heard Multicast Datagram:", repr(ip)
            self.transport.write("%s %s" % (Bootstrapper.myip, self.pkey), address)

class MulticastServerThread(threading.Thread):

    def __init__(self, pkey):
        threading.Thread.__init__(self)
        self.pkey = pkey

    def run(self):
        reactor.listenMulticast(8005, MulticastServerUDP(self.pkey))
        #reactor.run(installSignalHandlers=0)

##########
# CLIENT #
##########

class MulticastClientUDP(DatagramProtocol):

    def datagramReceived(self, datagram, address):
        ip, pkey = datagram.split()
        if ip != Bootstrapper.myip:
            Bootstrapper.hosts[ip] = pkey

class MulticastClientThread(threading.Thread):
    def __init__(self, pkey):
        threading.Thread.__init__(self)
        self.pkey = pkey
    
    def run(self):
        print "sending multicast hello"
        # Send multicast on 224.0.1.123:8005, on our dynamically allocated port
        reactor.listenUDP(0, MulticastClientUDP()).write("%s %s" % (Bootstrapper.myip, self.pkey), ('224.0.1.123', 8005))

##########
# BACKUP #
##########

HOST = '172.23.124.59'
PORT = 8007

class BackupClientThread(threading.Thread):
    
    def __init__(self, pkey):
        threading.Thread.__init__(self)
        self.pkey = pkey

    def run(self):
        print "No clients located, attempting to contact backup server...."
        while True:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((HOST, PORT))
                s.send("GIMMEHOSTS %s" % self.pkey)
                data = json.loads(s.recv(1024))
                for datum in data:
                    if datum != Bootstrapper.myip:
                        Bootstrapper.hosts[datum] = data[datum]
            except Exception as e:
                print "Home server is not available at this time: ", e, HOST, PORT
                break
            print "Hosts received from backup server:", Bootstrapper.hosts
            time.sleep(15)

######################
### INITIALIZATION ###
######################

class Bootstrapper:
    hosts = {}
    myip = urlopen('http://whatismyip.org/').read()
    myip = socket.gethostbyname(socket.gethostname())

    def __init__(self, pkey):
        self.pkey = pkey

    def bootstrap(self):
        MulticastServerThread(self.pkey).start()
        MulticastClientThread(self.pkey).start()
        #Give multicast a chance to find some friends
        time.sleep(5)
        if len(self.hosts)==0:
            BackupClientThread(self.pkey).start()

if __name__ == "__main__":
    b = Bootstrapper(1337)
    b.bootstrap()
