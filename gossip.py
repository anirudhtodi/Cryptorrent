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
    """
    
    Possible Gossip Information:
      Manager Request - 
      File Request - 
        ('filereq', {dest-ip}, {filename}, {manager-ip})
      
    """

    time_interval = 3
    
    def __init__(self, bootstrapper):
        self.server = NodeServer()
        self.server.start()
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip = {}

    def init_file_request(self, filename):
        filereq = ('filreq', self.bootstrapper.myip, filename, 'no-manager')
        self.gossip[filereq] = 100

    def timed_gossip(self):
        self.gossip()
        threading.Timer(self.time_interval, self.timed_gossip, ()).start()

    def timed_hostcheck(self):
        for ip, pkey in self.bootstrapper.hosts.items():
            self.hosts[ip] = pkey
        threading.Timer(30, self.timed_hostcheck, ()).start()

    def choose_random_host(self):
        if len(self.hosts) == 0:
            return None
        host_list = self.hosts.keys()
        return choice(host_list)

    def gossip(self):
        host = self.choose_random_host()
        if not host:
            return
        self.send(host)

    def gossip_data(self):
        return json.dumps(self.gossip)

    def send(self, host):
        data = self.gossip_data()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, 7060))
        s.send(data)

    