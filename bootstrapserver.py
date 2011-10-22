# This file is part of Scale.

# Scale is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Scale is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Scale.  If not, see <http://www.gnu.org/licenses/>.

from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver
import time
import datetime
import threading
from threading import Timer
from threading import Thread
import signal

signal.signal(signal.SIGINT,signal.SIG_DFL)

hosts = {}

class LoggingProtocol(LineReceiver):

    def connectionMade(self):
        client = self.transport.getPeer().host
        t = datetime.datetime.utcnow()
        if client != "127.0.0.1":
            hosts[client] = time.mktime(t.timetuple())
        self.factory.fp.write(client + '\t' + str(time.mktime(t.timetuple())))
        print "connection from", client #other options are port, type
        

    def dataReceived(self, line):
        print self.transport.getPeer().host, "says", line
        if line == "HERE":
            self.transport.write("OK")
        elif line == "GIMMEHOSTS":
            print hosts
            for host in hosts:
                self.transport.write(host)
        else:
            self.transport.write("Invalid Message")
        self.factory.fp.write(line+'\n')
        self.factory.fp.flush()


class LogfileFactory(Factory):

    protocol = LoggingProtocol

    def __init__(self, fileName):
        self.file = fileName

    def startFactory(self):
        self.fp = open(self.file, 'a')

    def stopFactory(self):
        self.fp.close()

def runCleanUp():
    bootable = []
    for host in hosts:
        if(hosts[host] + TIMEOUT < time.mktime(datetime.datetime.utcnow().timetuple())):
            bootable.append(host)
    for host in bootable:
        del hosts[host]
        print host + " was booted beacuse of a timeout.\n"
    Timer(CLEANUPTIMEINTERVAL,runCleanUp,()).start()
        
class runListener(Thread):
    def run(self):
        reactor.listenTCP(8007, LogfileFactory("bootstrap.log"))
        print "listening TCP on port 8007"
        reactor.run(installSignalHandlers=0)

runListener().start()

TIMEOUT = 30
CLEANUPTIMEINTERVAL = 2
runCleanUp()


import signal
signal.signal(signal.SIGINT,signal.SIG_DFL)
