from boostrap import Bootstrapper
from gossip import GossipServer

bs = Bootstrapper()
bs.bootstrap()


gs = GossipServer(bs)
gs.start()
