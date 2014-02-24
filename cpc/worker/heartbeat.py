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
import os
import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



from cpc.worker.message import WorkerMessage
from cpc.network.com.client_response import ProcessedResponse

log=logging.getLogger(__name__)


class HeartbeatSender(object):
    def __init__(self, worker, runCondVar):
        """Start a heartbeat thread."""
        self.lock=threading.Lock()
        self.runCondVar=runCondVar
        self.workerID=worker.getID()#workerID
        self.workerDir=worker.getWorkerDir()
        self.worker=worker
        self.run=False
        # dict by cmd id of a tuple of cmd id and originating server:
        #self.cmds=dict() 
        self.cmdsChanged=True
        self.thread=None 
        log.debug("Started heartbeat thread")
        self.randomFileCreated=False
        self.randomFile=None

    def addWorkloads(self, workloads):
        """Add a workload list."""
        with self.lock:
            # set run for the first time a workload is added.
            if len(workloads) > 0:
                self.run=True
            self.cmdsChanged=True
            #for workload in workloads:
            #    self.cmds[workload.cmd.id] = workload
            #    for subwl in workload.joinedTo:
            #        self.cmds[subwl.cmd.id]= subwl

            #for workload in workloads:
            #    hbi=cpc.command.heartbeat.HeartbeatItem(workload.cmd.id, 
            #                                    workload.originatingServer,
            #                                    workload.rundir)
            #    self.cmds[workload.cmd.id]=hbi
            #    for subwl in workload.joinedTo:
            #        hbi=cpc.command.heartbeat.HeartbeatItem(subwl.cmd.id, 
            #                                        subwl.originatingServer,
            #                                        subwl.rundir)
            #        self.cmds[subwl.cmd.id] = hbi
            self._startThread()
                
    def delWorkloads(self, workloads):
        """Remove a workload list."""
        with self.lock:
            self.cmdsChanged=True
            #for workload in workloads:
            #    del self.cmds[workload.cmd.id]
            #    for subwl in workload.joinedTo:
            #        del self.cmds[subwl.cmd.id]
            self._startThread()

    def _startThread(self):
        #Assume locked object.
        if self.thread is None:
            self.thread=threading.Thread(target=heartbeatSenderThread, 
                                         args=(self,))
            self.thread.daemon=True
            self.thread.start()
        else:
            if self.run:
                self._sendPing(False, False)

    def stop(self):
        """Tell the hearbeat thread to stop running."""
        with self.lock:
            log.debug("Stopping heartbeat thread")
            if self.run:
                self._sendPing(False, True)
            self.run=False

    def getRun(self):
        """Check whether the heartbeat thread should run."""
        with self.lock:
            return self.run

    def setRun(self, run):
        """Set whether the heartbeat thread should run."""
        with self.lock:
            self.run=run


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
        with self.runCondVar:
            # first write the items to xml
            cmds=self.worker._getWorkloads()
            co=StringIO()
            co.write('<heartbeat worker_id="%s">'%self.workerID)
            for item in cmds:
                if item.running:
                    item.hbi.writeXML(co)
                    for subwl in item.joinedTo:
                        subwl.hbi.writeXML(co)
            co.write("</heartbeat>")
        clnt=WorkerMessage()
        resp=clnt.workerHeartbeatRequest(self.workerID, self.workerDir, 
                                         first, last, changed, 
                                         co.getvalue())
        presp=ProcessedResponse(resp)
        if last:
            timestr=" last"
        else:
            timestr="" 
        if first:
            timestr+=" first"
        if changed:
            timestr+=" update"
        log.debug("Sent%s heartbeat signal. Result was %s"%
                  (timestr, presp.getStatus()))
        if presp.getStatus() != "OK":
            # if the response was not OK, the upstream server thinks we're 
            # dead and has signaled that to the originating server. We 
            # should just die now.
            faulty=presp.getData()
            log.info("Error from heartbeat request. Stopping %s"%str(faulty))
            #log.error("Got error from heartbeat request. Stopping worker.")
            if ( type(faulty) == type(dict()) and 'faulty' in faulty): 
                for faultyItem in faulty['faulty']:
                    self.worker.killWorkload(faultyItem)
            else:
                pass
                #sys.exit(1)
        respData=presp.getData()
        if type(respData) == type(dict()):
            rettime=int(respData['heartbeat-time'])
            self.randomFile=respData['random-file']
            self._createRandomFile()
        else:
            rettime=int(respData)
        #rettime=int(presp.getData())
        log.debug("Waiting %s seconds for next ping"%(rettime))
        return rettime

    def _createRandomFile(self):
        """Create a file wiht a random name chosen by the server. Used to 
            make sure the worker has write access to the directory it's 
            claiming is its work directory."""
        if not self.randomFileCreated and self.randomFile is not None:
            randomFileName=os.path.join(self.workerDir, self.randomFile)
            log.debug("Creating random file %s"%randomFileName)
            self.randomFileCreated=True
            outf=open(randomFileName, 'w')
            outf.write('\n')
            outf.close()

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

