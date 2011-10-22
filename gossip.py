import signal
import json
import copy
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
        ('chunk', {start}, {end}, {data}, filereq, {hop-ttl})
      Has File - 
        ('has_file', {source_ip}, {filesize}, filereq, {hop_ttl})
    """
    
    def __init__(self, bootstrapper):
        self.server = NodeServer(self)
        self.server.start()
        self.filemanager = FileManager()
        self.manager = Manager()
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip_queue = []
        self.gossip = {}

    def process_gossip(self, data):
        for item, ttl in data.items():
            if item not in self.gossip:
                if item[0] == 'filereq':
                    file_offer = self.gen_file_offer(item)
                    if file_offer:
                        manager_ip = item[3]
                        self.gossip_queue.append(manager_ip, file_offer)            
                elif item[0] == 'chunk':
                    tag, start, end, data, filereq, hopttl = item
                    tag, destip, filename, mip, hopttl = filreq
                    self.filemanager.receive_chunk(filename, start, finish, data)
                elif item[0] == 'send_chunk':
                    tag, dest_ip, start, end, filereq, hopttl = item
                    tag, destip, filename, mip, hopttl = filreq
                    chunk = ('chunk', start, end, self.filemanager.find_chunk(filename, start, end), filereq, 1)
                    self.gossip_queue.append(destip, chunk)
                elif item[0] == 'has_file':
                    self.manager.manage(item)

    def send_chunk_request(self, req, ip):
        self.gossip_queue.append(ip, req)

    def gen_file_offer(self, item):
        tag, dest_ip, filename, manager_ip, hop_ttl = item
        self.gossip[(name, dest_ip, filename, manager_ip, hop_ttl - 1)] = 100
        filesize = self.file_manager.find_file(filname)
        if filesize != None:
            return ('has_file', self.bootstrapper.myip, filesize, item, 1)
        return None

    def init_file_request(self, filename):
        manager = choose_random_host()
        filereq = ('filreq', self.bootstrapper.myip, filename, manager, 255)
        self.gossip[filereq] = 100

    def timed_gossip(self):
        self.gossip()
        threading.Timer(3, self.timed_gossip, ()).start()

    def timed_lease_check(self):
        #threading.Timer(30, self.timed_lease_check, ()).start()
        pass

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
        if len(self.gossip_queue) > 0:
            host, item = self.gossip_queue.pop(0)
        else:
            host = self.choose_random_host()
            item = None
        if not host:
            return
        self.send(host, item)

    def gossip_data(self, item):
        if item != None:
            g = copy.deepcopy(self.gossip)
            g[item] = 100
            return json.dumps(g)
        else:
            return json.dumps(self.gossip)

    def send(self, host, item):
        data = self.gossip_data(item)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, 7060))
        s.send(data)

    
