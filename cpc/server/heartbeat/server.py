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


import time
import threading
import logging
import tarfile
import tempfile
import shutil
import errno


#from cpc.server.request import ServerToServerMessage
import cpc.server.message 
from cpc.util.conf.server_conf import ServerConf
import cpc.util.file
import item

log=logging.getLogger('cpc.heartbeat.server')


class HeartbeatError(cpc.util.CpcError):
    pass
class HeartbeatNotFoundError(cpc.util.CpcError):
    def __init__(self, workerID):
        self.str="Worker ID %s not found"%workerID
class HeartbeatReaderError(cpc.util.CpcXMLError):
    pass


class HeartbeatList(object):
    """Maintains the list of workers to expect heartbeats from."""
    def __init__(self):
        """Initialize an empty list."""
        # the current workers being monitored
        self.workers=dict() # dict of hearbeatWorkers
        self.thread=None
        self.lock=threading.Lock()

    def ping(self, workerID, workerDir, iteration, heartbeatItemsXML, response):
        """Handle a heartbeat signal from a worker with a given worker 
           ID, and whether it's the first or last heartbeat 
           (sent after the worker is done), or whether the list
           of items needs to be updated.

           iteration         = "first", "last", "updated" or empty.
           heartbeatItemsXML = XML string containing heartbeat items 
           response          = the server response object
           """
        heartbeatTime=ServerConf().getHeartbeatTime()
        stateChanged=False
        with self.lock:
            log.debug("heartbeat item: worker %s, dir %s, iteration %s, items '%s'"%
                      (workerID, workerDir, iteration, heartbeatItemsXML))
            if iteration=="first":
                # this is a new worker. Add it to the worker list.
                worker=item.HeartbeatWorker(workerID, workerDir)
                reader=item.HeartbeatWorkerReader(worker)
                reader.readString(heartbeatItemsXML,"heartbeat ping request")
                log.debug("New worker %s in the heartbeat list"%workerID)
                self.workers[workerID] = worker
                self._startThread()
                stateChanged=True
                response.add("", data=heartbeatTime)
            elif self.workers.has_key(workerID):
                worker=self.workers[workerID]
                if iteration == "update":
                    worker.clearItems()
                    reader=item.HeartbeatWorkerReader(worker)
                    reader.readString(heartbeatItemsXML,
                                      "heartbeat ping request")
                    #workerLst=reader.getWorkers()
                    stateChanged=True
                    response.add("", data=heartbeatTime)
                elif iteration == "last":
                    # last iteration. Delete the item.
                    del self.workers[workerID]
                    stateChanged=True
                    response.add("", data=0)
                else:
                    # plain ping.
                    worker.ping()
                    response.add("", data=heartbeatTime)
            else:
                # the worker isn't known about and probably should have 
                # been dead. Notify it of that through the response
                response.add("already-dead", data=None, status="ERROR")
            if stateChanged:
                self._writeStateLocked()


    def _startThread(self):
        if self.thread is None:
            self.thread=threading.Thread(target=heartbeatServerThread, 
                                         args=(self,))
            self.thread.daemon=True
            self.thread.start()
            
    def checkHeartbeatTimes(self, maxTime):
        """Check the heartbeat times, and notify the servers of dead workers.
           Returns the oldest living worker's last heard time.

           maxTime = the maximum allowed time between two heartbeats."""
        stateChanged=False
        with self.lock:
            now=time.time()
            oldestItem=now
            todelete=[] # the list of workers to delete
            for worker in self.workers.itervalues():
                if (now - worker.lastHeard) > maxTime:
                    todelete.append(worker)
                elif worker.lastHeard < oldestItem:
                    oldestItem = worker.lastHeard
            if len(todelete) > 0:
                stateChanged=True
            for worker in todelete:
                self._notifyServer(worker)
                del self.workers[worker.workerID]
            if stateChanged:
                self._writeStateLocked()
        return oldestItem

    def _notifyServer(self, worker):
        """Notify the server that a worker has died.
           Returns the client response."""
        log.info("Worker %s has died."%(worker.workerID))
        items=worker.getItems()
        # now notify all the appropriate servers.
        #sendSucceeded=False
        for item in items:
            log.info("Notifying %s that worker of cmd %s has died."%
                     (item.serverName, item.cmdID))
            tff=None
            try:
                if item.haveRunDir():
                    # if it exists, we create a tar file and send it.
                    tff=tempfile.TemporaryFile()
                    tf=tarfile.open(fileobj=tff, mode="w:gz")
                    tf.add(item.getRunDir(), arcname=".", recursive=True)
                    tf.close()
                    tff.seek(0)
                    #sendSucceeded=True
            except:
                # we make sure we don't upload in case of doubt
                pass
            clnt=cpc.server.message.server_message.ServerMessage()
            clnt.commandFailedRequest(item.cmdID, item.serverName, tff)
        if worker.haveWorkerDir():
            try:
                # remove the worker directory
                shutil.rmtree(worker.getWorkerDir(), ignore_errors=True)
            except:
                # and duly ignore the response.
                pass

    def _writeStateLocked(self):
        """Write the state of the list to a file, assuming a locked state."""
        stateFilename=ServerConf().getHeartbeatFile()
        cpc.util.file.backupFile(stateFilename)
        outf=open(stateFilename, "w")
        outf.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        outf.write('<heartbeat-list>\n')
        for worker in self.workers.itervalues():
            worker.writeXML(outf)
            #outf.write('  <worker id="%s" worker_dir="%s">\n'%(workerID,
            #                                                   itemList))
            #outf.write('  </worker>\n')
        outf.write('</heartbeat-list>\n')
        outf.close()

    def writeState(self):
        """Write the state of the list to a file."""
        with self.lock:
            self._writeStateLocked()

    def readState(self):
        """Read the state of the list from a file. The new heartbeat list
           items get a timeout that starts from the moment they've been
           read."""
        stateFilename=ServerConf().getHeartbeatFile()
        reader=item.HeartbeatWorkerReader()
        try:
            reader.read(stateFilename)
        except cpc.util.CpcError as e:
            log.info("Error reading heartbeat list: %s"%str(e))
        except IOError as e:
            if e[0] == errno.ENOENT:
                log.info("No heartbeat file")
            else:
                log.info("Couldn't read heartbeat list: %s"%str(e))
        with self.lock:
            wlst=reader.getWorkers()
            for worker in wlst:
                self.workers[worker.workerID] = worker
            if len(self.workers) > 0:
                self._startThread()

    def list(self):
        """Return a list of heartbeat workers.
           returns: a list of HearbeatWorker objects"""
        retlist=[]
        with self.lock:
            # shallow-copy the list
            for worker in self.workers.itervalues():
                retlist.append(worker)
        return retlist

    def workerFailed(self, workerID):
        """Force a worker-failed message to be sent to an item in the list. 
           Throws a HeartbeatNotFoundError if the command is not found.

           workerFailed = the command id in the list.
           Returns: whether the command has been succesfully processed by
                    the originating server."""
        if not self.workers.has_key(workerID):
            raise HeartbeatNotFoundError(workerID)
        worker=self.workers[workerID]
        self._notifyServer(worker)
        del self.workers[workerID]
        return True

    def toJSON(self):
        """Convert the object to a dictionary that can be JSON-serialized."""
        with self.lock:
            ret=dict()
            ret['class'] = self.__class__.__name__
            ret['workers']=[]
            for worker in self.workers.itervalues():
                ret['workers'].append(worker.toJSON())
            return ret   


def heartbeatServerThread(heartbeatList):
    """The hearbeat thread's endless loop.
       heartbeatList = the heartbeat list associated with this loop."""
    log.info("Starting heartbeat monitor thread.")
    while True:
        # so we can reread the ocnfiguration
        heartbeatTime=ServerConf().getHeartbeatTime()
        maxHeartbeatTime=2*heartbeatTime
        oldestTime=heartbeatList.checkHeartbeatTimes(maxHeartbeatTime)
        # calculate how long we can sleep before we need to check again.
        # if there weren't any items in the hearbeat list, the oldest time 
        # is now, so we wait (almost) exactly maxHearbeatTime. 
        now=time.time()
        sleepTime = (maxHeartbeatTime + oldestTime) - now + 1
        log.debug("Heartbeat thread sleeping for %d seconds."%sleepTime)
        if sleepTime > 0:
            time.sleep(sleepTime)


