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
import shutil
import os
import sys
import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



import cpc.util
import cpc.command.heartbeat
#from cpc.util.conf.server_conf import ServerConf
from cpc.server.message.server_message import ServerMessage

log=logging.getLogger('cpc.server.heartbeat')

class RunningCmdListNotFoundError(cpc.util.CpcError):
    def __init__(self, cmdID):
        self.str="Command %s not found"%cmdID

class RunningCmdListError(cpc.util.CpcError):
    pass
class WorkerDataListError(cpc.util.CpcError):
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
        # before the first ping we have to assume this
        self.isLocal=False
        self.haveData=False

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

    def setIsLocal(self, isLocal):
        self.isLocal=isLocal
    def getIsLocal(self):
        return self.isLocal

    def setHaveData(self, haveData):
        self.haveData=haveData
    def getHaveData(self):
        return self.haveData

    def ping(self):
        """Update the timer to reflect a new heartbeat signal"""
        self.lastHeard=time.time()

    def toJSON(self):
        ret=dict()
        ret['cmd_id']=self.cmd.id
        ret['server_name']=self.workerServer
        if self.workerID is not None:
            ret['worker_id']=self.workerID
        else:
            ret['worker_id']="not set"
        if self.workerDir is not None:
            ret['worker_dir']=self.workerDir
        else:
            ret['worker_dir']="not set"
        if self.runDir is not None:
            ret['run_dir']=self.runDir
        else:
            ret['run_dir']="not set"
        ret['task_id']=self.cmd.task.getID()
        ret['heartbeat_expiry_time']= int( (self.lastHeard + 
                                            2*self.heartbeatInterval) - 
                                           time.time())
        ret['data_accessible']=self.haveData
        return ret

class WorkerDataList(object):
    """Maintains a list of directories used by workers connected to this
       server. Only these directories are fetchable with dead-worker-fetch.
       
       Each directory indexes a random has that is the name of a file that
       the worker should generate. This way a worker can prove that it 
       can write to the directory it claims is the worker directory. This
       closes a potential security issue where the worker could make the 
       server read any file."""
    def __init__(self):
        # the directories are held in a dict that indexes the random file
        # the worker should create. That is sent with every heartbeat reply
        self.workerDirs=dict()

    def add(self, workerDir):
        wd=os.path.normpath(workerDir)
        if not wd in self.workerDirs:
            self.workerDirs[wd] = cpc.util.rng.getRandomHash()

    def remove(self, workerdir):
        wd=os.path.normpath(workerDir)
        if wd in self.workerDirs:
            del self.workerDirs[wd]

    def getRnd(self, workerDir):
        wd=os.path.normpath(workerDir)
        if wd in self.workerDirs:
            return self.workerDirs[wd]
        return None

    def checkDirectory(self, dir, runDirs):
        """check whether a requested directory is a worker directory.

           return True if the directory 'dir' exists, False if it doesn't exist,
           and raise an exception if the access is denied (for example, when
           the random file wasn't created)."""
        dir=os.path.normpath(dir)
        for runDir in runDirs:
            cp=[dir, os.path.normpath(runDir)]
            # the worker directory must be a parent directoryS
            try:
                sameFile=os.path.samefile(os.path.commonprefix(cp), dir)
            except:
                return False
            if not sameFile:
                raise WorkerDataListError(
                            "Access denied: %s is not a subdirectory of %s"%
                            (runDir, dir))
        if not dir in self.workerDirs:
            raise WorkerDataListError(
                    "Access denied: %s not in list of known worker directories"%
                    (dir))
        if not os.path.exists(os.path.join(dir, self.workerDirs[dir])):
            raise WorkerDataListError(
                    "Access denied: %s doesn't have required random file"%
                    (dir))
        return os.path.isdir(dir)


class RunningCmdList(object):
    """Maintains a list of all running commands owned by this server, for
       which periodic heartbeat signals are expected."""

    # Minimum time to wait for heartbeat expiries. This limits the rate
    # at which worker failures can cause data requests to worker servers if
    # they can be bundled. 
    rateLimitTime = 5 

    def __init__(self, conf, cmdQueue, workerData):
        """Initialize the object with an empty list."""
        # a list of heartbeat items in a dict indexed by command ID, of
        # RunningCommand objects. Because this is just a flat list, we can
        # ensure that if a worker 'forgets' about a job, it will trigger a 
        # heartbeat timeout on a single job. Likewise, if a group of jobs time
        # out, they will time out closely in time so a small lag time will
        # gather a group of job-failure requests to send to the worker-server
        # in a single batch.
        self.conf=conf
        self.cmdQueue=cmdQueue
        self.runningCommands=dict()
        self.workerData=workerData
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
        # the command is now removed from the list so we can stop locking.
        if runfile is not None:
            log.debug("extracting file for %s to dir %s"%(cmd.id,cmd.getDir()))
            cpc.util.file.extractSafely(cmd.getDir(), fileobj=runfile)
        self._handleFinishedCmd(cmd, returncode, cputime)

    def _handleFinishedCmd(self, cmd, returncode, cputime):
        """Handle the command finishing itself. The command must be removed
           from the list first using self.lock, so no two threads own this
           command first."""
        # handle the associated status 
        task=cmd.getTask()
        cmd.running=False
        cmd.setReturncode(returncode)
        cmd.addCputime(cputime)
        #if runfile is not None:
        #    log.debug("extracting file for %s to dir %s"%(cmd.id,cmd.getDir()))
        #    cpc.util.file.extractSafely(cmd.getDir(), fileobj=runfile)
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

    def ping(self, workerID, workerDir, iteration, heartbeatItems, isLocal,
             faultyItems):
        """Handle a heartbeat signal from a worker (possibly relayed)
          
           workerID = the sending worker's ID
           workerDir = the sending worker's run directory 
           iteration = the sending workers' claimed iteration
           heartbeatItems = the hearbeat items describing commands.
           isLocal = a boolean that is true when the worker server is this 
                     server
           faultyItems = a list containing faulty heartbeat items
           """
        response=[]
        OK=True
        for item in heartbeatItems:
            with self.lock:
                cmdid=item.getCmdID()
                log.debug("Heartbeat signal for command %s"%cmdid)
                if cmdid not in self.runningCommands:
                    item.setState(item.stateNotFound)
                    log.info("Heartbeat item %s not found"%cmdid)
                    faultyItems.append(item.cmdID)
                    OK=False
                else:
                    cwid=self.runningCommands[cmdid].getWorkerID()
                    if (cwid is not None) and (cwid != workerID):
                        item.setState(item.stateWrongWorker)
                        log.info("Worker ID for %s not found"%cmdid)
                        OK=False
                        faultyItems.append(item.cmdID)
                    else:
                        item.setState(item.stateOK)
                        rc=self.runningCommands[cmdid]
                        if cwid is None:
                            rc.setWorkerID(workerID)
                        rc.setWorkerDir(workerDir)
                        rc.setRunDir(item.getRunDir())
                        rc.setIsLocal(isLocal)
                        haveData=item.getHaveRunDir() 
                        if haveData is None:
                            haveData=False
                        rc.setHaveData(haveData)
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

    def _fetchRemoteRunFiles(self, rc):
        """Get the result files from a remote run directory to a local 
            command directory. 
            Return true if successful. May throw exception in case of failure"""
        if rc.haveData:
            log.debug("Fetching remote results directory %s to %s"%
                      (rc.runDir, rc.cmd.getDir()))
            # the data is remote: we must fetch data through a 
            # server-to-server command.
            msg=ServerMessage(rc.workerServer)
            resp=msg.deadWorkerFetchRequest(rc.workerDir, rc.runDir)
            if resp.getType() == "application/x-tar":
                # untar the return data and  use it.
                runfile=resp.getRawData()
                log.debug("extracting file for %s to dir %s"%
                          (rc.cmd.id,rc.cmd.getDir()))
                cpc.util.file.extractSafely(rc.cmd.getDir(), fileobj=runfile)
                return True
        return False

    def _moveRunFiles(self, rc):
        """Move the result files from a local run directory to a local 
            command directory. 
            Return true if successful. May throw exception in case of failure"""
        runDir=rc.runDir
        destDir=rc.cmd.getDir()
        done=False
        tmpDirName="__heartbeat_failure_results"
        backupDirName="__heartbeat_failure_backup"
        if self.workerData.checkDirectory(rc.workerDir, [runDir] ):
            log.debug("Moving data from %s to %s"%(runDir, destDir))
            # first make a temp dest directory in the command dir
            tmpDestDir=os.path.join(destDir, tmpDirName)
            tmpBackupDir=os.path.join(destDir, backupDirName)
            if os.path.exists(tmpDestDir):
                # If it already exists, it must first be removed. This means
                # we cannont name files with double underscores in cmd dirs.
                shutil.rmtree(tmpDestDir)
            if os.path.exists(tmpBackupDir):
                shutil.rmtree(tmpBackupDir)
            os.mkdir(tmpDestDir)
            try:
                os.mkdir(tmpBackupDir)
                # now move all the files into the temp dest dir 
                # If there is a problem with permissions, it will happen now, 
                # before we overwrite any of the original files.
                files=os.listdir(runDir)
                # now move the files individually
                for filename in files:
                    if filename != tmpDirName and filename != backupDirName:
                        srcFile=os.path.join(runDir, filename)
                        dstFile=os.path.join(tmpDestDir, filename)
                        # we must remove them first because otherwise
                        # shutil.move will thrown an exception
                        shutil.move(srcFile, dstFile)
                # and move all of them in place. We can now do this safely with 
                # os.rename
                files=os.listdir(tmpDestDir)
                for filename in files:
                    if filename != tmpDirName and filename != backupDirName:
                        srcFile=os.path.join(tmpDestDir, filename)
                        dstFile=os.path.join(destDir, filename)
                        # we move any existing files to dstBackupDir
                        if os.path.exists(dstFile):
                            os.rename(dstFile, os.path.join(tmpBackupDir, 
                                                            filename))
                        os.rename(srcFile, dstFile)
                # and remove the run directory, the tmp dir and the backup dir
                shutil.rmtree(runDir)
                done=True
            finally:
                shutil.rmtree(tmpDestDir)
                shutil.rmtree(tmpBackupDir)
            return done
          
    def checkHeartbeatTimes(self):
        """Check the heartbeat times and deal with dead jobs. 
           Returns the time of the first heartbeat expiry."""
        interval = self.conf.getHeartbeatTime()
        with self.lock:
            # The maximum first expiry time is the server heartbeat interval
            firstExpiry=time.time()+interval
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
            # first try to get the data
            finishedReported=False
            haveDir=False
            for rc in todelete:
                # TODO: consolidate all requests for each worker server into
                # one request
                try:
                    if not rc.isLocal:
                        haveDir=self._fetchRemoteRunFiles(rc)
                    else: 
                        # the data is local. Copy the directory
                        haveDir=self._moveRunFiles(rc)
                    if haveDir:
                        self._handleFinishedCmd(rc.cmd, None, 0)
                        finishedReported=True
                except cpc.util.CpcError as e:
                    log.error(e.__str__())
                except:
                    # we can ignore these, because they are simply associated
                    # with fetching output data.
                    fo=StringIO()
                    traceback.print_exception(sys.exc_info()[0],
                                              sys.exc_info()[1],
                                              sys.exc_info()[2], file=fo)
                    log.error("Heartbeat exception: %s"%(fo.getvalue()))
                if not finishedReported:
                    log.info("Running command %s died: didn't get its data."%
                             rc.cmd.id)
                    # just add it back into the queue
                    self.cmdQueue.add(rc.cmd)
                else:
                    log.info("Running command %s died: got its data."%
                             rc.cmd.id)
        return (interval, firstExpiry)

def heartbeatServerThread(runningCommandList):
    """The hearbeat thread's endless loop.
       runningCommandList = the heartbeat list associated with this loop."""
    log.info("Starting heartbeat monitor thread.")
    while True:
        # so we can reread the ocnfiguration
        (interval, firstExpiry)=runningCommandList.checkHeartbeatTimes()
        # calculate how long we can sleep before we need to check again.
        # we simply double the first expiry time, with a minimum of
        # runningCommandList.rateLimitTime seconds
        # (this serves as a rate limiter)
        now=time.time()
        #serverHeartbeatInterval=runningCommandList.conf.getHeartbeatTime()
        sleepTime = (firstExpiry - now) 
        if sleepTime < runningCommandList.rateLimitTime:
            sleepTime=runningCommandList.rateLimitTime
        log.debug("Heartbeat thread sleeping for %d seconds."%sleepTime)
        time.sleep(sleepTime)

