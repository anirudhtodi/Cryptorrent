import signal
import json
from filemanager import FileManager
from encryption import Encryptor
from random import host
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver


signal.signal(signal.SIGINT, signal.SIG_DFL)


class NodeServer(LineReceiver, threading.Thread):
    hosts = set()

    def __init__(self, gossiper):
        threading.Thread.__init__(self)
        self.gossiper = gossiper


    def run(self):
        reactor.listenTCP(7060, ScaleFactory())
        #reactor.run(installSignalHandlers=0)

    def connectionMade(self):
        client = self.transport.getPeer().host

    def dataReceived(self, line):
        data = process_socket_data(line)
        self.gossiper.process_gossip(json.loads(data))
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
      File Request - 
        ('filereq', {destination_ip}, {filename}, {manager-ip}, {hop_ttl})
      Send Chunk -
        ('send_chunk', {destination_ip}, {start}, {end}, filereq, {hop-ttl})
      Chunk - 
        ('chunk', {destination_ip}, {start}, {end}, {data}, filereq, {hop-ttl})
      Has File - 
        ('has_file', {source_ip}, {filesize}, filereq, {hop_ttl})
    """

    time_interval = 3
    
    def __init__(self, bootstrapper):
        self.server = NodeServer(self)
        self.server.start()
        self.filemanager = FileManager()
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip_queue = []
        self.gossip = {}

    def process_gossip(self, data):
        for item, ttl in data.items():
            if item not in self.gossip:
                self.gossip[item] = ttl
                if item[0] == 'filereq':
                    ### manager server stuff
                    file_offer = self.gen_file_offer(item)
                    if file_offer:
                        self.gossip[file_offer] = 10 + len(self.gossip_queue)
                        manager_ip = item[3]
                        self.gossip_queue.append(manager_ip)                  
                elif item[0] == 'chunk':
                    pass
                elif item[0] == 'send_chunk':
                    pass
                elif item[0] == 'has_file':
                    pass

    def gen_file_offer(self, item):
        name, dest_ip, filename, manager_ip, hope_ttl = item
        filesize = self.file_manager.find_file(filname):
        if filesize != None:
            return ('has_file', self.bootstrapper.myip, filesize, item, 1)
        return None

    def init_file_request(self, filename):
        filereq = ('filreq', self.bootstrapper.myip, filename, manager, 255)
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

    
