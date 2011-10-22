from boostrap import Bootstrapper
from gossip import GossipServer

bs = Bootstrapper()
bs.bootstrap()


gs = GossipServer(bs)
gs.start()


while True:
    filename = raw_input('Filename: ')
    if filename == 'exit':
        exit()
    gs.init_file_request(filename)
    
