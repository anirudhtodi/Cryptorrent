import signal
import json
import threading
import socket
from filemanager import FileManager
#from encryption import Encryptor
from random import choice
from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver


signal.signal(signal.SIGINT, signal.SIG_DFL)



def dict_convert(dic, item):
    newdic = {}
    if item != None:
        newdic[json.dumps(item)] = 100
    for key, val in dic.items():
        newdic[json.dumps(key)] = val
    return newdic

def dict_unconvert(dic):
    newdic = {}
    for key, val in dic.items():
        newdic[tuple(json.loads(key))] = val
    return newdic
    

class NodeServer(LineReceiver, threading.Thread):
    hosts = set()
    gossiper = None

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        reactor.listenTCP(7060, NodeFactory())
        reactor.run(installSignalHandlers=0)

    def connectionMade(self):
        #client = self.transport.getPeer().host
        pass

    def dataReceived(self, line):
        self.gossiper.process_gossip(dict_unconvert(json.loads(line)))
        
    def lineReceived(self, line):
         pass

    def rawDataReceived(self, data):
         pass

    def add_host(self, host):
        self.hosts.add(host)

class NodeFactory(Factory):
    protocol = NodeServer



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
        self.server = NodeServer()
        NodeServer.gossiper = self
        self.server.start()
        self.filemanager = FileManager()
        self.manager = ManagerNode(self)
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip_queue = []
        self.gossip_dict = {}

        self.timed_gossip()
        self.timed_hostcheck()
        print "Gossip Server Started..."

    def process_gossip(self, data):
        for item, ttl in data.items():
            if item not in self.gossip_dict:
                print "Processing Gossip:", item
                if item[0] == 'filereq':
                    file_offer = self.gen_file_offer(item)
                    if file_offer:
                        manager_ip = item[3]
                        self.gossip_queue.append(manager_ip, file_offer)            
                elif item[0] == 'chunk':
                    tag, start, end, data, filereq, hopttl = item
                    tag, destip, filename, mip, hopttl = filereq
                    self.filemanager.receive_chunk(filename, start, end, data)
                elif item[0] == 'send_chunk':
                    tag, dest_ip, start, end, filereq, hopttl = item
                    tag, destip, filename, mip, hopttl = filereq
                    chunk = ('chunk', start, end, self.filemanager.find_chunk(filename, start, end), filereq, 1)
                    self.gossip_queue.append(destip, chunk)
                elif item[0] == 'has_file':
                    self.manager.manage(item)

    def send_chunk_request(self, req, ip):
        self.gossip_queue.append(ip, req)


    def gen_file_offer(self, item):
        tag, dest_ip, filename, manager_ip, hop_ttl = item
        self.gossip_dict[(tag, dest_ip, filename, manager_ip, hop_ttl - 1)] = 100
        filesize = self.filemanager.find_file(filename)
        if filesize != None:
            return ('has_file', self.bootstrapper.myip, filesize, item, 1)
        return None

    def init_file_request(self, filename):
        manager = self.choose_random_host()
        filereq = ('filreq', self.bootstrapper.myip, filename, manager, 255)
        self.gossip_dict[filereq] = 100

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
        return json.dumps(dict_convert(self.gossip_dict, item))

    def send(self, host, item):
        try:
            data = self.gossip_data(item)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host, 7060))
            s.send(data)
        except Exception as e:
            print "EXCEPTION IN SEND:", str(e), "\n\tFOR HOST:", host


class ManagerNode(GossipServer):
    chunk_size = 512
    files_to_process = {}
    
    def __init__ (self, gossiper):
        self.gossiper = gossiper
        
    def manager(self, item):
        # Register each file that this node should be a manager of
        # Register every node that tells the manager that it is the source
        source_ip = item[1]
        filesize = item[2]
        filereq = item[3]
        filename = filereq[2]
        if not self.files_to_process.contains(filereq):
            self.files_to_process.put(filereq, [0, filesize])
        self.files_to_process[filereq].add(source_ip)

    def send_chunk_requests(self):
        for filereq_to_process, filereq_info in self.files_to_process.items():
            amount_processed = filereq_info[0]
            filesize = filereq_info[1]
            for file_containing_node in filereq_info[2:]:
                start_byte_number = amount_processed
                end_byte_number = amount_processed + self.chunk_size
                if end_byte_number > filesize:
                    end_byte_number = filesize
                    del filereq_to_process[filereq_to_process]
                amount_processed = end_byte_number+1
                chunk_request = ('send_chunk', filereq_to_process[1],
                                 start_byte_number, end_byte_number,
                                 filereq_to_process, 1)
                self.gossiper(chunk_request)
            
