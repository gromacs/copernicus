# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.



import threading
import logging
import time
import sys

from cpc.network.com.client_response import ProcessedResponse
from cpc.worker.message import WorkerMessage
log=logging.getLogger('cpc.worker.heartbeat')


class Heartbeat:
    def __init__(self, cmdID, originatingServer, wd):
        """Start a heartbeat thread."""
        self.lock=threading.Lock()
        self.cmdID=cmdID
        self.originatingServer=originatingServer
        self.wd=wd
        self.run=True
        self.thread=threading.Thread(target=heartbeatThread, args=(self,))
        self.thread.daemon=True        
        self.thread.start()
        log.debug("Started heartbeat thread")

    def stop(self):
        """Tell the hearbeat thread to stop running."""
        with self.lock:
            log.debug("Stopping heartbeat thread")
            self.run=False
            self._sendPing(False, True)

    def getRun(self):
        """Check whether the heartbeat thread should still run."""
        with self.lock:
            return self.run

    def sendHeartbeat(self, first):
        """Try to send a hearbeat signal (if we're still supposed to be running)
           and return the number of seconds to wait. If the run has finished,
           return None.
           first: whether this is the first heartbeat signal
           """
        with self.lock:
            if self.run:
                return self._sendPing(first, False)
            else:
                return None

    def _sendPing(self, first, last):
        """Do the actual sending"""
        clnt=WorkerMessage()
        resp=clnt.workerHeartbeatRequest(self.cmdID, self.originatingServer, 
                                         self.wd, first, last)
        presp=ProcessedResponse(resp)
        if last:
            timestr=" last"
        else:
            timestr="" 
        if first:
            timestr+=" first"
        log.debug("Sent%s heartbeat signal. Result was %s"% (timestr, 
                                                             presp.getStatus()))
        if presp.getStatus() != "OK":
            # if the response was not OK, the upstream server thinks we're 
            # dead and has signaled that to the originating server. We 
            # should just die now.
            log.error("Got error from heartbeat request. Stopping worker.")
            sys.exit(1)
        rettime=int(presp.getData())
        log.debug("Need to wait %s seconds"%(rettime))
        return rettime



def heartbeatThread(hb):
    """The worker's heartbeat thread function. Sends a heartbeat within the 
       time requested by the server, as long as the process is running."""
    keepRunning=True
    first=True
    while keepRunning:
        secsToWait=hb.sendHeartbeat(first)
        first=False
        if secsToWait is None:
            keepRunning=False
        else:
            time.sleep(secsToWait)

