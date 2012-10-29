# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2012, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
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
import time
import logging


import cpc.util
import cpc.command.heartbeat
from cpc.util.conf.server_conf import ServerConf

log=logging.getLogger('cpc.server.heartbeat')

class RunningCmdListNotFoundError(cpc.util.CpcError):
    def __init__(self, cmdID):
        self.str="Command %s not found"%cmdID

class RunningCmdListError(cpc.util.CpcError):
    pass

class RunningCommand(object):
    """The data associated with a running command. Mostly heartbeat monitoring
       data"""
    def __init__(self, cmd, workerID, workerDir, runDir, server, 
                 heartbeatInterval):
        self.cmd=cmd   # the command
        self.workerID=workerID 
        self.workerDir=workerDir # the working directory of the worker
        self.runDir=runDir # the working directory for this command
        self.lastHeard=time.time() 
        self.workerServer=server
        # the relevant heartbeat interval
        self.heartbeatInterval=int(heartbeatInterval) 

    def getCmd(self):
        return self.cmd
    def getWorkerServer(self):
        return self.workerServer
    def getHeartbeatInterval(self):
        return self.heartbeatInterval

    def getWorkerID(self):
        return self.workerID
    def setWorkerID(self, workerID):
        self.workerID=workerID

    def getWorkerDir(self):
        return self.workerDir
    def setWorkerDir(self, workerDir):
        self.workerDir=workerDir

    def getRunDir(self):
        return self.runDir
    def setRunDir(self, runDir):
        self.runDir=runDir

    def ping(self):
        """Update the timer to reflect a new heartbeat signal"""
        self.lastHeard=time.time()

    def toJSON(self):
        ret=dict()
        ret['cmd_id']=self.cmd.id
        ret['server_name']=self.workerServer
        ret['worker_id']=self.workerID
        ret['worker_dir']=self.workerDir
        ret['run_dir']=self.runDir
        ret['heartbeat_expiry_time']= int( (self.lastHeard + 
                                            2*self.heartbeatInterval) - 
                                           time.time())
        ret['data_accessible']=False
        return ret


class RunningCmdList(object):
    """Maintains a list of all running commands owned by this server, for
       which periodic heartbeat signals are expected."""

    # Minimum time to wait for heartbeat expiries. This limits the rate
    # at which worker failures can cause data requests to worker servers if
    # they can be bundled. 
    rateLimitTime = 5 

    def __init__(self, cmdQueue):
        """Initialize the object with an empty list."""
        # a list of heartbeat items in a dict indexed by command ID, of
        # RunningCommand objects. Because this is just a flat list, we can
        # ensure that if a worker 'forgets' about a job, it will trigger a 
        # heartbeat timeout on a single job. Likewise, if a group of jobs time
        # out, they will time out closely in time so a small lag time will
        # gather a group of job-failure requests to send to the worker-server
        # in a single batch.
        self.cmdQueue=cmdQueue
        self.runningCommands=dict()
        self.lock=threading.Lock()
        self.thread=threading.Thread(target=heartbeatServerThread, args=(self,))
        # this should be a thread that never stops but doesn't hold the server
        # up once other threads stop
        self.thread.daemon=True
        self.thread.start()

    def add(self, cmds, workerServer, heartbeatInterval):
        """Add a set of commands sent to a specific worker."""
        with self.lock:
            for cmd in cmds:
                if cmd.id in self.runningCommands:
                    raise RunningCmdListError("Duplicate command ID")
                # the worker ID and directory will be set when the first 
                # heartbeat signal is received.
                rc=RunningCommand(cmd, None, None, None, workerServer, 
                                  heartbeatInterval)
                self.runningCommands[cmd.id] = rc
                cmd.setRunning(True, workerServer)

    def remove(self, cmd):
        """Remove a command from the list, or throw a HeartbeatListError
           if no such command.
           cmd = a command object to remove."""
        with self.lock:
            if cmd.id not in self.runningCommands:
                raise RunningCmdListNotFoundError(cmd.id)
            del self.runningCommands[cmd.id]

    def handleFinished(self, cmdID, returncode, cputime, runfile):
        """Handle a finished command (successful or otherwise), with optional
           runfile
           cmd = the command to remove
           returncode = the return code
           runfile = a file object containing run results
           runfile = None or a file handle to the tarfile containing run data
           """
        task=None
        with self.lock:
            # remove it from the list
            if cmdID not in self.runningCommands:
                raise RunningCmdListNotFoundError(cmdID)
            cmd=self.runningCommands[cmdID].cmd
            del self.runningCommands[cmdID]
        self._handleFinishedCmd(cmd, returncode, cputime, runfile)

    def _handleFinishedCmd(self, cmd, returncode, cputime, runfile):
        """Handle the command finishing itself. The command must be removed
           from the list first using self.lock, so no two threads own this
           command first."""
        # handle the associated status 
        task=cmd.getTask()
        cmd.running=False
        cmd.setReturncode(returncode)
        cmd.addCputime(cputime)
        if runfile is not None:
            log.debug("extracting file for %s to dir %s"%(cmd.id,cmd.dir))
            cpc.util.file.extractSafely(cmd.dir, fileobj=runfile)
        # run the task
        if task is not None:
            (newcmds, cancelcmds) = task.run(cmd)
        if cancelcmds is not None:
            for ccmd in cancelcmds:
                self.cmdQueue.remove(ccmd)
        if newcmds is not None:
            for ncmd in newcmds:
                self.cmdQueue.add(ncmd)

    def getCmdList(self):
        """Return a list with all running commands as command objects."""
        ret=[]
        with self.lock:
            for value in self.runningCommands.itervalues():
                ret.append(value.cmd)
        return ret

    def ping(self, workerID, workerDir, iteration, heartbeatItems):
        """Handle a heartbeat signal from a worker (possibly relayed)
          
           workerID = the sending worker's ID
           workerDir = the sending worker's run directory 
           iteration = the sending workers' claimed iteration
           heartbeatItems = the hearbeat items describing commands.
           """
        response=[]
        OK=True
        for item in heartbeatItems:
            with self.lock:
                cmdid=item.getCmdID()
                log.debug("Heartbeat signal for command %s"%cmdid)
                if cmdid not in self.runningCommands:
                    item.setState(item.stateNotFound)
                    OK=False
                else:
                    cwid=self.runningCommands[cmdid].getWorkerID()
                    if (cwid is not None) and (cwid != workerID):
                        item.setState(item.stateWrongWorker)
                        OK=False
                    else:
                        item.setState(item.stateOK)
                        rc=self.runningCommands[cmdid]
                        if cwid is None:
                            rc.setWorkerID(workerID)
                        rc.setWorkerDir(workerDir)
                        rc.setRunDir(item.getRunDir())
                        rc.ping()
        return OK

    def toJSON(self):
        ret=dict()
        retlist=[]
        with self.lock:
            for item in self.runningCommands.itervalues():
                retlist.append(item.toJSON())
        ret['heartbeat_items']=retlist
        return ret

    def readState(self):
        pass
    def writeState(self):
        pass
      
    def checkHeartbeatTimes(self):
        """Check the heartbeat times and deal with dead jobs. 
           Returns the time of the first heartbeat expiry."""
        with self.lock:
            # The maximum first expiry time is the server heartbeat interval
            firstExpiry=time.time()+ServerConf().getHeartbeatTime()
            todelete=[]
            now=time.time()
            for rc in self.runningCommands.itervalues():
                expiry = rc.lastHeard + 2*rc.heartbeatInterval
                if now  > expiry:
                    todelete.append(rc)
                elif expiry < firstExpiry:
                    firstExpiry = rc.lastHeard + 2*rc.heartbeatInterval + 1
            # first remove the expired running commands from the 
            # running list
            for rc in todelete:
                del self.runningCommands[rc.cmd.id]
        # then handle their failure
        if len(todelete)>0:
            for rc in todelete:
                #rc.notifyServer()
                log.info("Running command %s died."%rc.cmd.id)
                # for now, we just add it back into the queue
                self.cmdQueue.add(rc.cmd)
                #self._handleFinishedCmd(rc.cmd, None, 0, None)
            # self.writeState()
        return firstExpiry

def heartbeatServerThread(runningCommandList):
    """The hearbeat thread's endless loop.
       runningCommandList = the heartbeat list associated with this loop."""
    log.info("Starting heartbeat monitor thread.")
    while True:
        # so we can reread the ocnfiguration
        firstExpiry=runningCommandList.checkHeartbeatTimes()
        # calculate how long we can sleep before we need to check again.
        # we simply double the first expiry time, with a minimum of
        # runningCommandList.rateLimitTime seconds
        # (this serves as a rate limiter)
        now=time.time()
        serverHeartbeatInterval=ServerConf().getHeartbeatTime()
        sleepTime = (firstExpiry - now) 
        if sleepTime < runningCommandList.rateLimitTime:
            sleepTime=runningCommandList.rateLimitTime
        log.debug("Heartbeat thread sleeping for %d seconds."%sleepTime)
        time.sleep(sleepTime)

