import signal
from encryption import Encryptor
from random import host
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver


signal.signal(signal.SIGINT, signal.SIG_DFL)


def process_socket_data(line):
    pass


class NodeServer(LineReceiver, threading.Thread):
    hosts = set()

    def run(self):
        reactor.listenTCP(7060, ScaleFactory())
        #reactor.run(installSignalHandlers=0)

    def connectionMade(self):
        client = self.transport.getPeer().host

    def dataReceived(self, line):
        data = process_socket_data(line)
        GossipServer.process_gossip(data)
        output_data = self.output_data()
        self.transport.write(output_data)
        
    def lineReceived(self, line):
         pass

    def rawDataReceived(self, data):
         pass

    def add_host(self, host):
        self.hosts.add(host)

class NodeFactory(Factory):
    protocol = ScaleServer



class GossipServer:

    time_interval = 3
    
    def __init__(self):
        self.server = NodeServer()
        self.server.start()
        self.hosts = {}

    def add_host(self):
        pass


    def timed_gossip(self):
        self.gossip()
        threading.Timer(self.time_interval, self.timed_gossip, ()).start()

    def choose_random_host(self):
        if len(self.hosts) == 0:
            return None
        host_list = GissupServer.hosts.keys()
        return choice(host_list)

    def gossip(self):
        host = self.choose_random_host()
        if not host:
            return
        #####


    def send():
        

    
