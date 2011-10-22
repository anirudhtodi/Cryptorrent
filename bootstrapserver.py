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

import json
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
        print "connection from", client #other options are port, type
        

    def dataReceived(self, line):
        client = self.transport.getPeer().host
        print client, "says", line
        linedata = line.split()
        t = datetime.datetime.utcnow()
        if client != "127.0.0.1":
            hosts[client] = (linedata[1], time.mktime(t.timetuple()))

        if linedata[0] == "HERE":
            self.transport.write("OK")
        elif linedata[0] == "GIMMEHOSTS":
            print hosts
            to_send = {}
            counter = 0
            for host in hosts:
                counter += 1
                if counter > 10:
                    break
                to_send[host] = hosts[host][0]
            self.transport.write(json.dumps(to_send))
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
        if(hosts[host][1] + TIMEOUT < time.mktime(datetime.datetime.utcnow().timetuple())):
            bootable.append(host)
    for host in bootable:
        del hosts[host]
        print host + " was booted beacuse of a timeout.\n"
    Timer(CLEANUPTIMEINTERVAL,runCleanUp,()).start()
        
class runListener(Thread):
    def run(self):
        reactor.listenTCP(8007, LogfileFactory("bootstrap.log"))
        print "listening TCP on port 8007"
        #reactor.run(installSignalHandlers=0)

runListener().start()

TIMEOUT = 30
CLEANUPTIMEINTERVAL = 2
runCleanUp()


import signal
signal.signal(signal.SIGINT,signal.SIG_DFL)
