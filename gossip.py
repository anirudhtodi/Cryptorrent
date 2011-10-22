import signal
import json
import threading
import socket
import rsa
from filemanager import FileManager
import encryption
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
        item = tuple(json.loads(key))
        for i in range(len(item)):
            if type(item[i]) == type([]):
                temp = list(item)
                temp[i] = tuple(temp[i])
                item = tuple(temp)
        newdic[item] = val
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
        try:
            self.gossiper.process_gossip(dict_unconvert(json.loads(line)))
        except:
            try:
                decr = self.gossiper.decrypt(str(line))
                self.gossiper.process_gossip(dict_unconvert(json.loads(decr)))
            except:
                pass
        
        
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
        ('filereq', {destination_ip}, {filename}, {manager-ip})
      Send Chunk -
        ('send_chunk', {destination_ip}, {start}, {end}, filereq)
      Chunk - 
        ('chunk', {start}, {end}, {data}, filereq)
      Has File - 
        ('has_file', {source_ip}, {filesize}, filereq)
    """
    
    def __init__(self, bootstrapper, pubkey, privkey):
        self.server = NodeServer()
        NodeServer.gossiper = self
        self.server.start()
        self.filemanager = FileManager()
        self.file_lock = threading.RLock()

        self.pubkey = pubkey
        self.privkey = privkey

        self.manager = ManagerNode(self)
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip_queue = []
        self.gossip_dict = {}
        self.current_gossip = set()

        self.timed_gossip()
        self.timed_hostcheck()
        print "Gossip Server Started..."


    def encrypt(self, msg, key):
        #os.system("touch tempkey.pem")
        #f = open('tempkey.pem', 'w')
        #f.write(key)
        msg = str(msg)[:]
        key = key[10:-1]
        n, e = key.split(', ')
        pemkey = rsa.PublicKey(int(n) , int(e))

        crypt = []
        while True:
            if msg == '':
                break
            crypt.append(rsa.encrypt(msg[:115], pemkey))
            msg = msg[:115]

        return ''.join(crypt)

    def decrypt(self, msg):
        msg = str(msg)[:]
        decrypt = []
        while True:
            if msg == '':
                break
            decrypt.append(rsa.decrypt(msg[:115], pemkey))
            msg = msg[:115]

        return ''.join(decrypt), self.privkey

    def process_gossip(self, data):
        print "GOSSIP:", data
        for item, ttl in data.items():
            if item not in self.current_gossip:
                self.current_gossip.add(item)
                print "\tProcessing Gossip:", item, self.gossip_dict
                if item[0] == 'filereq':
                    file_offer = self.gen_file_offer(item)
                    if file_offer:
                        print "\tHave File:", item
                        manager_ip = item[3]
                        if manager_ip == self.bootstrapper.myip:
                            self.manager.manage(file_offer)
                        else:
                            self.gossip_queue.append((manager_ip, file_offer))
                elif item[0] == 'chunk':
                    print "RECEIVED CHUNK"
                    tag, start, end, data, filereq = item
                    tag, destip, filename, mip = filereq
                    self.file_lock.acquire()
                    self.filemanager.receive_chunk('files/' + filename, start, end, data)
                    self.file_lock.release()
                elif item[0] == 'send_chunk':
                    print "RECEIVED REQUEST FOR CHUNK"
                    tag, dest_ip, start, end, filereq = item
                    tag, destip, filename, mip = filereq
                    
                    file_chunk = self.filemanager.find_chunk('files/' + filename, start, end)
                    encrypted_chunk = encryption.encrypt(file_chunk, self.hosts[destip])

                    chunk_descriptor = ('chunk', start, end, encrypted_chunk, filereq)
                    self.gossip_queue.append((destip, chunk_descriptor))
                elif item[0] == 'has_file':
                    self.manager.manage(item)

    def send_chunk_request(self, req, ip):
        self.gossip_queue.append((ip, req))


    def gen_file_offer(self, item):
        tag, dest_ip, filename, manager_ip = item
        self.gossip_dict[(tag, dest_ip, filename, manager_ip)] = 100
        filesize = self.filemanager.find_file('files/' + filename)
        if filesize != None:
            return ('has_file', self.bootstrapper.myip, filesize, item)
        return None

    def init_file_request(self, filename):
        print "You requested:", filename
        manager = self.choose_random_host()
        filereq = ('filereq', self.bootstrapper.myip, filename, manager)
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
        print 'Gossip:', host
        self.send(host, item)

    def gossip_data(self, item):
        return json.dumps(dict_convert(self.gossip_dict, item))

    def send(self, host, item):
        #try:
            data = self.gossip_data(item)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host, 7060))
            s.send(data, self.hosts[host])
        #except Exception as e:
        #    print "EXCEPTION IN SEND:", str(e), "\n\tFOR HOST:", host


class ManagerNode(GossipServer):
    chunk_size = 1024
    files_to_process = {}
    
    def __init__ (self, gossiper):
        self.gossiper = gossiper
        threading.Timer(5, self.process_chunk_requests, ()).start()        


    def manage(self, item):
        # Register each file that this node should be a manager of
        # Register every node that tells the manager that it is the source
        print "MANAGEMNT STARTED:", item
        tag, source_ip, filesize, filereq = item

        if filereq not in self.files_to_process:
            print "Initializing managemt of:", filereq
            self.files_to_process[filereq] = [0, filesize]
        print "APPENDING", source_ip
        self.files_to_process[filereq].append(source_ip)

    def process_chunk_requests(self):
        for filereq_to_process, filereq_info in self.files_to_process.items():
            if not filereq_info:
                continue
            amount_processed = filereq_info[0]
            filesize = filereq_info[1]
            file_holders = filereq_info[2:]
            finished = False
            for file_containing_node in file_holders:
                start_byte_number = amount_processed
                end_byte_number = amount_processed + self.chunk_size
                if end_byte_number > filesize:
                    end_byte_number = filesize
                    del self.files_to_process[filereq_to_process]
                    print "FIN", filereq_to_process, self.files_to_process
                    finished = True
                amount_processed = end_byte_number+1
                chunk_request = ('send_chunk', filereq_to_process[1],
                                 start_byte_number, end_byte_number,
                                 filereq_to_process)
                self.gossiper.send_chunk_request(chunk_request, file_containing_node)
                print "SENDING CHUNK:", start_byte_number, end_byte_number
                newval = [amount_processed, filesize] + file_holders
                if not finished:
                    self.files_to_process[filereq_to_process] = newval
        threading.Timer(2, self.process_chunk_requests, ()).start()        
