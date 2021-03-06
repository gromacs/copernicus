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




import sys
import os
import signal
import logging
import subprocess
import shlex
import tempfile
import tarfile
import shutil
import threading
import traceback
import time
import copy
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util
from  cpc.command import Resource
from  cpc.command import RunVars
from  cpc.command import RunVarReader
import cpc.client
from cpc.command.platform_reservation import PlatformReservation
import cpc.worker
from cpc.worker.message import *

log=logging.getLogger(__name__)


# this lock avoids two simultaneous Popen commands. This seems to fix
# a python bug.
splock=threading.Lock()

class WorkloadError(cpc.util.CpcError):
    pass

class WorkLoad(object):
    """The description of a single command with run directory and originating
       server."""
    def __init__(self, workerDir, cmd, rundir, originatingServer, executable, 
                 platform, id, condVar):
        self.condVar=condVar
        self.cmd=cmd # the command. A constant property
        self.rundir=rundir # full path of the run directory. A constant property
        self.originatingServer=originatingServer # A constant property
        self.executable=executable
        self.platform=platform
        self.addArgs="" # additional arguments
        self.used=dict() # the list of used resources
        # work out how many resources it uses:
        for rsrc in platform.getMaxResources().itervalues():
            cmdRes=cmd.getReserved(rsrc.name)
            if cmdRes is not None:
                self.used[rsrc.name]= Resource(rsrc.name, cmdRes)
        self.id=id
        self.workerDir=workerDir
        self.cputimeMultiplier=self.used['cores'].value
        # the amount of cpu time used for this workload
        # for now, the number of cores is the multiplier factor
        self.hbi=cpc.command.heartbeat.HeartbeatItem(self.cmd.id,
                                                     self.originatingServer,
                                                     self.rundir)
        # the following data should be protected by a lock, given by the worker:
        self.joinedTo=[] # the workloads that this workload joins
        self.running=False
        self.failed=False # whether the run caused an exception
        self.realTimeSpent=0
        self.args=None # the argument list for low level run
        # the return code
        self.returncode=None
        self.subprocess=None


    def canJoin(self, other):
        """Check whether two workloads can be joined.
           other = the other workload to test."""
        if (self.platform != other.platform or 
            self.executable != other.executable):
            log.debug("platform/executable doesn't match")
            return False
        exe=self.executable
        matchNcores=((not exe.joinMatchNcores) or
                     (self.used['cores'].value==other.used['cores'].value))
        if not matchNcores:
            log.debug("ncores doesn't match: %d, %d"%
                      (self.used['cores'].value==other.used['cores'].value))
            return False
        if exe.joinMatchArgs:
            matchArgs=True
            aa=self.cmd.getArgs()
            ba=other.cmd.getArgs()
            if len(aa) != len(ba):
                log.debug("argument number doesn't match")
                matchArgs=False
            else:
                for aarg, barg in zip(aa, ba):
                    if aarg != barg:
                        matchArgs=False
                        break
                    else:
                        matchArgs=True
            if not matchArgs:
                log.debug("arguments don't match")
                return False
        return True

    def _getCputime(self):
        """Get the cpu time spent in this workload."""
        return self.cputimeMultiplier*self.realTimeSpent

    def join(self, others):
        """Join this workload to a list of others:
           others = a list of workloads."""
        self.addArgs += self.executable.joinCommonArgs
        # we add ourselves.
        nothers=[ self ]
        nothers.extend(others)
        ncores=0
        for wl in nothers:
            ncores+=wl.used['cores'].value
        with self.condVar:
            for wl in nothers:
                vars= RunVars()
                vars.add("RUN_DIR", wl.rundir)
                vars.add("NCORES", "%d"%wl.used['cores'].value)
                vars.add("NCORES_TOT", "%d"%ncores)
                vars.add("ARGS", wl.cmd.getArgStr() )
                # expand the string now because it contains variables specific 
                # to this joining
                args=vars.expandStr(self.executable.joinSpecificArgs)
                self.addArgs += " %s"%args
                if wl != self:
                    self.joinedTo.append(wl)
                    # add the used values.
                    for self_rsrc in self.used.itervalues():
                        name=self_rsrc.name
                        if wl.used.has_key(name):
                            self_rsrc.add(wl.used[name])

    def reservePlatform(self):
        """Reserve this workload's resources from the platform."""
        if not self.platform.canReserveCmdResources(self.cmd):
            raise cpc.util.CpcError("Overcommitted resources for platform %s!"%
                                    (self.platform.name))
        self.platform.reserveCmdResources(self.cmd)

    def releasePlatform(self):
        """Release a reservation from the platform."""
        self.platform.releaseCmdResources(self.cmd)
        for workload in self.joinedTo:
            workload.releasePlatform()


    def expandCmdString(self, additionalRunVars):
        """Expand an argument string's variables."""
        initialArgStr="%s %s %s"%(self.executable.cmdline,
                                  self.cmd.getArgStr(), self.addArgs)
        vars=RunVars()
        vars.add("EXECUTABLE_DIR", self.executable.basedir)
        vars.add("NCORES", "%d"%self.used['cores'].value)
        vars.add("RUN_DIR", self.rundir)
        vars.add("ARCH", self.executable.arch)
        vars.add("PLATFORM", self.executable.platform)
        vars.add("VERSION", self.executable.version.getStr())
        vars.add("CMD_ID", self.cmd.id)
        vars.addRunVars(self.platform.getRunVars())
        if additionalRunVars is not None:
            vars.addRunVars(additionalRunVars)
        retstr=vars.expandStr(initialArgStr)
        return retstr

    def returnResults(self):
        with self.condVar:
            log.debug("Returning run data for cmd id %s"%self.cmd.id)
            tff=tempfile.TemporaryFile()
            outputFiles=self.cmd.getOutputFiles()
            tf=tarfile.open(fileobj=tff, mode="w:gz")
            if outputFiles is None or len(outputFiles)==0:
                tf.add(self.rundir, arcname=".", recursive=True)
            else:
                outputFiles.append('stdout')
                outputFiles.append('stderr')
                for name in outputFiles:
                    fname=os.path.join(self.rundir,name)
                    if os.path.exists(fname):
                        tf.add(fname, arcname=name, recursive=False)
            tf.close()
            del(tf)
            tff.seek(0)
            shutil.rmtree(self.rundir, ignore_errors=True)
            # and send it back 
            clnt= WorkerMessage()
            # the cmddir, taskID and projectID together define a unique command.
            clnt.commandFinishedRequest(self.cmd.id, self.originatingServer, 
                                        self.returncode, self._getCputime(), 
                                        tff)
            tff.close()
            for workload in self.joinedTo:
                workload.returnResults()

    def run(self, plugin, pluginArgs):
        """Run the workload in a separate thread. Signal the condvar when
           done. Run platfrom plugin with run command when neccesary."""
        global splock
        additionalRunVars=None
        if self.platform.callRunSet():
            plr=PlatformReservation(self.workerDir, self.rundir, self.id,
                                    self.used)
            with splock:
                plugin_retmsg=plugin.run(".", "run", pluginArgs, plr.printXML())
            if plugin_retmsg[0] != 0:
                log.error("Platform plugin failed: %s"%plugin_retmsg[1])
                raise WorkloadError("Platform plugin failed: %s"%
                                    plugin_retmsg[1])
            log.debug("Platform plugin, run cmd: '%s'"%plugin_retmsg[1])
            rvr=RunVarReader()
            rvr.readString(plugin_retmsg[1], "Run vars from platform plugin")
            additionalRunVars=rvr.getRunVars()
        cmdstring=self.expandCmdString(additionalRunVars)
        log.debug("Full command string: %s"%cmdstring)
        with self.condVar:
            self.args=shlex.split(str(cmdstring))
            if self.running:
                raise cpc.util.CpcError("workload already running.")
            self.running=True
        # start the thread in which to run.
        th=threading.Thread(target=runThreadFn, args=(self,))
        th.daemon=True
        th.start()

    def isRunning(self):
        with self.condVar:
            return self.running

    def finish(self, plugin, pluginArgs):
        """Run the platform plugin with finish when needed."""
        global splock
        if self.platform.callFinishSet():
            plr=PlatformReservation(self.workerDir, self.rundir, self.id,
                                    self.used)
            with splock:
                plugin_retmsg=plugin.run(".", "finish", pluginArgs, 
                                         str(plr.printXML()))
            if plugin_retmsg[0] != 0:
                log.error("Platform plugin failed: %s"%plugin_retmsg[1])
                raise cpc.worker.WorkerError("Platform plugin failed: %s"%
                                             plugin_retmsg[1])
            log.debug("Platform plugin, finish cmd: '%s'"%plugin_retmsg[1])


    def _runInThread(self):
        """The low-level running function. Run from within a running thread
           started with runThreadFn()."""
        global splock
        log.debug("Run thread with cmd id=%s started in directory %s"%
                  (self.cmd.id, self.rundir))
        with self.condVar:
            if self.args is None:
                raise cpc.util.CpcError("No argument.")
        stdoutname=os.path.join(self.rundir, "stdout")
        stdoutf=open(stdoutname, 'w')
        stderrname=os.path.join(self.rundir, "stderr")
        stderrf=open(stderrname, 'w')
        cenv=self.cmd.getEnv()
        with self.condVar:
            if cenv is not None:
                # copy the environment variables
                nenv=copy.copy(os.environ)
                # and set the additional ones
                nenv.update(cenv)
            else:
                nenv=None
            with splock:
                sp=subprocess.Popen(self.args, stdin=None,
                                    stdout=stdoutf, stderr=stderrf,
                                    cwd=self.rundir, env=nenv)
                self.subprocess=sp
        sp.wait() 
        with self.condVar:
            self.returncode=sp.returncode
            self.subprocess=None
            stdoutf.close()
            stderrf.close()
            self.args=None
        log.debug("Run with cmd id=%s finished"%self.cmd.id)


    def killLocked(self):
        """Kill the process associated with this run. Assumes a locked 
           runCondVar"""
        sp=self.subprocess
        if self.running and sp!=None:
            os.kill(sp.pid, signal.SIGTERM)

    def signalMainThread(self, startTime, endTime):
        # now signal the main thread that we're finished.
        with self.condVar:
            log.debug("signaling end of run for %s"%self.cmd.id)
            self.running=False
            self.realTimeSpent += endTime-startTime
            self.condVar.notifyAll() 

def runThreadFn(workload):
    startTime=time.time()
    try:
        workload._runInThread()
        workload.failed=False
    except:
        fo=StringIO()
        traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                  sys.exc_info()[2], file=fo)
        log.error("Worker error: %s"%(fo.getvalue()))
        workload.failed=True
    endTime=time.time()
    # now signal the main thread that we're finished.
    workload.signalMainThread(startTime, endTime)

