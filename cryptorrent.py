import time
import encryption
from bootstrap import Bootstrapper
from gossip import GossipServer

encryption.make_key()
f = open('pub-key.pem', 'r')

bs = Bootstrapper(f.read())
f.close()
bs.bootstrap()

time.sleep(5)

gs = GossipServer(bs)

while True:
    filename = raw_input('Filename: ')
    if filename == 'exit':
        exit()
    gs.init_file_request(filename)
    
