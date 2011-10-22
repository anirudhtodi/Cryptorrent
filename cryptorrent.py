import time
from bootstrap import Bootstrapper
from gossip import GossipServer

bs = Bootstrapper('xx')
bs.bootstrap()

time.sleep(5)

gs = GossipServer(bs)
gs.start()


while True:
    filename = raw_input('Filename: ')
    if filename == 'exit':
        exit()
    gs.init_file_request(filename)
    
