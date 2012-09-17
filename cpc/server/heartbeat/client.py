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
import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



from cpc.worker.message import WorkerMessage
from cpc.network.com.client_response import ProcessedResponse
import item

log=logging.getLogger('cpc.heartbeat.client')


class HeartbeatSender(object):
    def __init__(self, workerID, workerDir):
        """Start a heartbeat thread."""
        self.lock=threading.Lock()
        self.workerID=workerID
        self.workerDir=workerDir
        self.run=True
        # dict by cmd id of a tuple of cmd id and originating server:
        self.cmds=dict() 
        self.cmdsChanged=True
        self.thread=None 
        log.debug("Started heartbeat thread")

    def addWorkloads(self, workloads):
        """Add a workload list."""
        with self.lock:
            self.cmdsChanged=True
            for workload in workloads:
                hbi=item.HeartbeatItem(workload.cmd.id, 
                                       workload.originatingServer,
                                       workload.rundir)
                self.cmds[workload.cmd.id]=hbi
                for subwl in workload.joinedTo:
                    hbi=item.HeartbeatItem(subwl.cmd.id, 
                                           subwl.originatingServer,
                                           subwl.rundir)
                    self.cmds[subwl.cmd.id] = hbi
            self._startThread()
                
    def delWorkloads(self, workloads):
        """Remove a workload list."""
        with self.lock:
            self.cmdsChanged=True
            for workload in workloads:
                del self.cmds[workload.cmd.id]
                for subwl in workload.joinedTo:
                    del self.cmds[subwl.cmd.id]
            self._startThread()

    def _startThread(self):
        #Assume locked object.
        if self.thread is None:
            self.thread=threading.Thread(target=heartbeatSenderThread, 
                                         args=(self,))
            self.thread.daemon=True
            self.thread.start()
        else:
            self._sendPing(False, False)

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
        changed=self.cmdsChanged
        self.cmdsChanged=False
        # first write the items to xml
        co=StringIO()
        co.write("<heartbeat>")
        for items in self.cmds.itervalues():
            items.writeXML(co)
        co.write("</heartbeat>")
        clnt=WorkerMessage()
        resp=clnt.workerHeartbeatRequest(self.workerID, self.workerDir, 
                                         first, last, changed, co.getvalue())
        presp=ProcessedResponse(resp)
        if last:
            timestr=" last"
        else:
            timestr="" 
        if first:
            timestr+=" first"
        if changed:
            timestr+=" update"
        log.debug("Sent%s heartbeat signal. Result was %s"%(timestr, 
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



def heartbeatSenderThread(hb):
    """The worker's heartbeat thread function. Sends a heartbeat within the 
       time requested by the server, as long as the process is running."""
    keepRunning=True
    first=True
    while keepRunning:
        try:
            secsToWait=hb.sendHeartbeat(first)
        except:
            # failed heartbeat signal connections should never cause the 
            # worker to run into problems
            secsToWait=60
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            log.error("Error from heartbeat request: %s"%fo.getvalue())
        first=False
        if secsToWait is None:
            keepRunning=False
        else:
            time.sleep(secsToWait)

