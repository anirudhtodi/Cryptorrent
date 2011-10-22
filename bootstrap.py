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
        print 'Multicast Server Started Listening....'
        # Join a specific multicast group, which is the IP we will respond to
        self.transport.joinGroup('224.0.1.123')

    def datagramReceived(self, datagram, address):
        print address
        if datagram != Bootstrapper.myip:
            Bootstrapper.hosts[datagram] = time.mktime(datetime.datetime.utcnow().timetuple()) + 600.0
            print "Bootstrap Server Hosts:....", Bootstrapper.hosts
            print "Heard Multicast Datagram:", repr(datagram)
            self.transport.write(Bootstrapper.myip, address)

class MulticastServerThread(Thread):
    def run(self):
        reactor.listenMulticast(8005, MulticastServerUDP())
        reactor.run(installSignalHandlers=0)

##########
# CLIENT #
##########

class MulticastClientUDP(DatagramProtocol):

    def datagramReceived(self, datagram, address):
        if datagram != Bootstrapper.myip:
            Bootstrapper.hosts[datagram] = time.mktime(datetime.datetime.utcnow().timetuple()) + 600.0

class MulticastClientThread(Thread):
    def run(self):
        print "sending multicast hello"
        # Send multicast on 224.0.1.123:8005, on our dynamically allocated port
        reactor.listenUDP(0, MulticastClientUDP()).write(Bootstrapper.myip, ('224.0.1.123', 8005))

##########
# BACKUP #
##########

HOST = '172.23.124.59'
PORT = 8007

class BackupClientThread(Thread):
    def run(self):
        print "No clients located, attempting to contact backup server...."
        while (len(Bootstrapper.hosts)==0):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((HOST, PORT))
                s.send("GIMMEHOSTS")
                data = s.recv(1024)
                if data != Bootstrapper.myip:
                    Bootstrapper.hosts[data] = time.mktime(datetime.datetime.utcnow().timetuple()) + 600.0
                print "received", repr(data)
            except Exception as e:
                print "Home server is not available at this time: ", e, HOST, PORT
            print "Hosts received from backup server:", Bootstrapper.hosts
            time.sleep(60)

######################
### INITIALIZATION ###
######################

class Bootstrapper():

    hosts = {}
    myip = urlopen('http://whatismyip.org/').read()
    myip = socket.gethostbyname(socket.gethostname())

    def bootstrap(self):
        MulticastServerThread().start()
        MulticastClientThread().start()
        #Give multicast a chance to find some friends
        time.sleep(5)
        if len(self.hosts)==0:
            BackupClientThread().start()

if __name__ == "__main__":
    b = Bootstrapper()
    b.bootstrap()
