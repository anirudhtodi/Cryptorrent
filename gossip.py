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
from subprocess import Popen, PIPE


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
        item = json.loads(key)
        if item[0] == 'chunk':
            item[3] = decrypt(item[3])

        for i in range(len(item)):
            if type(item[i]) == type([]):
                item[i] = tuple(item[i])
        newdic[tuple(item)] = val
    return newdic



def decrypt(msg):
    msg = str(msg)
    result = []
    for i in xrange(0, len(msg), 2):
        result.append(chr(int(msg[i:i+2], 16)))
    data = ''.join(result)

    start = 0
    block_sz = 256
    result = []
    while start < len(data) - 1:
        block = data[start: start + block_sz]
        p = Popen(['openssl', 'rsautl', '-decrypt', '-inkey',
                   'key.pem'], stdin=PIPE, stdout=PIPE)
        out, err = p.communicate(block)
        result.append(out)
        start += block_sz
    return ''.join(result)



class NodeServer(LineReceiver, threading.Thread):
    hosts = set()
    gossiper = None
    cache = ''

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        reactor.listenTCP(7060, NodeFactory())
        reactor.run(installSignalHandlers=0)

    def connectionMade(self):
        #client = self.transport.getPeer().host
        pass

    def dataReceived(self, line):
        if line[-1] != '}':
            self.cache += line
            return
        elif self.cache != '':
            self.cache += line
            line = self.cache
            self.cache = ''
            self.gossiper.process_gossip(dict_unconvert(json.loads(line)))
        else:
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
        ('filereq', {destination_ip}, {filename}, {manager-ip})
      Send Chunk -
        ('send_chunk', {destination_ip}, {start}, {end}, filereq)
      Chunk -
        ('chunk', {start}, {end}, {data}, filereq)
      Has File -
        ('has_file', {source_ip}, {filesize}, filereq)
    """

    def __init__(self, bootstrapper):
        self.server = NodeServer()
        NodeServer.gossiper = self
        self.server.start()
        self.filemanager = FileManager()
        self.file_lock = threading.RLock()

        self.manager = ManagerNode(self)
        self.bootstrapper = bootstrapper
        self.hosts = bootstrapper.hosts
        self.gossip_queue = []
        self.gossip_dict = {}
        self.current_gossip = set()

        self.timed_gossip()
        self.timed_hostcheck()
        print "Gossip Server Started..."

    @classmethod
    def encrypt(self, msg, key):
        data = str(msg)

        start = 0
        block_sz = 200
        result = []
        fout = open("/tmp/pub-key.pem", 'w')
        fout.write(key)
        fout.close()
        while start < len(data) - 1:
            block = data[start:start + block_sz]
            p = Popen(['openssl', 'rsautl', '-encrypt', '-inkey',
                       '/tmp/pub-key.pem', '-pubin'], stdin=PIPE, stdout=PIPE)
            out, err = p.communicate(block)
            result.append(out)
            start += block_sz
        expand = []
        for c in result:
            for char in c:
                expand.append(ord(char))
        return ''.join([(hex(c)[2:] if len(hex(c)) == 4
                         else '0' + hex(c)[2:]) for c in expand])



    def process_gossip(self, data):
        #print "PROCESS:", data

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
                    if destip in self.hosts:
                        encrypted_chunk = self.encrypt(file_chunk, self.hosts[destip])
                        chunk_descriptor = ('chunk', start, end, encrypted_chunk, filereq)
                        self.gossip_queue.append((destip, chunk_descriptor))
                elif item[0] == 'has_file':
                    self.manager.manage(item)

    def send_chunk_request(self, req, ip):
        if ip == self.bootstrapper.myip:
            self.process_gossip({req : 100})
        else:
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

        print "IIIIIIPPPPPPPPP:", self.bootstrapper.myip

        filereq = ('filereq', self.bootstrapper.myip, filename, manager)
        self.gossip_dict[filereq] = 100

    def timed_gossip(self):
        self.gossip()
        threading.Timer(3, self.timed_gossip, ()).start()

    def timed_lease_check(self):
        #threading.Timer(30, self.timed_lease_check, ()).start()
        pass

    def timed_hostcheck(self):
        self.hosts = self.bootstrapper.hosts
        #for ip, pkey in self.bootstrapper.hosts.items():
        #    self.hosts[ip] = pkey
        threading.Timer(3, self.timed_hostcheck, ()).start()

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
            ###print "EXCEPTION IN SEND:", str(e), "\n\tFOR HOST:", host
            pass


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

def rand_string():
    import random
    import string
    s = ""
    for i in xrange(1, random.randrange(1, 8)):
        s += random.choice(string.lowercase)
    s *= random.randint(2, 500)
    return s


if __name__ == "__main__":
    #encryption.make_key()
    #for i in xrange(1000):
    #    s = rand_string()
    #    e = GossipServer.encrypt(s, 123)
    #    r = GossipServer.decrypt(e)
    #    assert s != e and e != r and s == e
    #    print i,
    #    if i % 20 == 0: print


    a = {('ed', (1, 2, 3), 'fred') : 100, ('chunk', 1, (2, 3), 'cc') : 100}
    b = dict_convert(a, None)
    c = json.dumps(b)
    w = dict_unconvert(json.loads(c))
    print w
