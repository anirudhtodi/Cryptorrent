import time
import encryption
import rsa
from bootstrap import Bootstrapper
from gossip import GossipServer

try:
    f = open('pub-key.pem', 'r')
except IOError:
    encryption.make_key()
    f = open('pub-key.pem', 'r')

pubkey = f.read()
f.close()

bs = Bootstrapper(pubkey)
bs.bootstrap()

time.sleep(5)

gs = GossipServer(bs)

while True:
    filename = raw_input('Filename: ')
    if filename == 'exit':
        exit()
    gs.init_file_request(filename)

