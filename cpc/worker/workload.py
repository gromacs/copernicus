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
from  cpc.server.command import Resource
from  cpc.server.command import RunVars
from  cpc.server.command import RunVarReader
import cpc.client
from cpc.server.command.platform_reservation import PlatformReservation
import cpc.worker
from cpc.worker.message import *

log=logging.getLogger('cpc.workload')


# this lock avoids two simultaneous Popen commands. This seems to fix
# a python bug.
splock=threading.Lock()

class WorkloadError(cpc.util.CpcError):
    pass

class WorkLoad(object):
    """The description of a single command with run directory and originating
       server."""
    def __init__(self, workerDir, cmd, rundir, originatingServer, executable, 
                 platform, id):
        self.cmd=cmd # the command. A constant property
        self.rundir=rundir # full path of the run directory. A constant property
        self.originatingServer=originatingServer # A constant property
        self.executable=executable
        self.platform=platform
        self.addArgs="" # additional arguments
        self.joinedTo=[] # the workloads that this workload joins
        self.used=dict() # the list of used resources
        # work out how many resources it uses:
        for rsrc in platform.getMaxResources().itervalues():
            cmdRes=cmd.getReserved(rsrc.name)
            if cmdRes is not None:
                self.used[rsrc.name]= Resource(rsrc.name, cmdRes)
        # this should be protected by a lock, given by the worker:
        self.running=False
        self.args=None # the argument list for low level run
        self.failed=False # whether the run caused an exception
        self.id=id
        self.workerDir=workerDir
        # the amount of cpu time used for this workload
        #self.cputime=0
        self.realTimeSpent=0
        # for now, the number of cores is the multiplier factor
        self.cputimeMultiplier=self.used['cores'].value

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

    def getCputime(self):
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
        for wl in nothers:
            vars= RunVars()
            vars.add("RUN_DIR", wl.rundir)
            vars.add("NCORES", "%d"%wl.used['cores'].value)
            vars.add("NCORES_TOT", "%d"%ncores)
            vars.add("ARGS", wl.cmd.getArgStr() )
            # expand the string now because it contains variables specific 
            # to this joining
            args=vars.expandStr(self.executable.joinSpecificArgs)
            #args=self._expandDict(self.executable.joinSpecificArgs, vars)
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
        tff.seek(0)
        shutil.rmtree(self.rundir, ignore_errors=True)
        # and send it back 
        # TODO: find out where the original request came from.
        clnt= WorkerMessage()
        # the cmddir, taskID and projectID together define a unique command.
        clnt.commandFinishedRequest(self.cmd.id, self.originatingServer, 
                                    self.getCputime(), tff)
        tff.close()
        for workload in self.joinedTo:
            workload.returnResults()

    def run(self, condVar, plugin, pluginArgs):
        """Run the workload in a separate thread. Signal the condvar when
           done. Run platfrom plugin with run command when neccesary."""
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
        self.args=shlex.split(str(cmdstring))
        # set the status to running
        condVar.acquire()
        prevRun=self.running
        self.running=True
        condVar.release()
        if prevRun:
            raise cpc.util.CpcError("workload already running.")
        # start the thread in which to run.
        th=threading.Thread(target=runThreadFn, args=(self, condVar))
        th.daemon=True
        th.start()

    def finish(self, plugin, pluginArgs):
        """Run the platform plugin with finish when needed."""
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
        log.debug("Run thread with cmd id=%s started in directory %s"%
                  (self.cmd.id, self.rundir))
        if self.args is None:
            raise cpc.util.CpcError("No argument.")
        stdoutname=os.path.join(self.rundir, "stdout")
        stdoutf=open(stdoutname, 'w')
        stderrname=os.path.join(self.rundir, "stderr")
        stderrf=open(stderrname, 'w')
        cenv=self.cmd.getEnv()
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
        sp.wait() 
        stdoutf.close()
        stderrf.close()
        self.args=None
        log.debug("Run with cmd id=%s finished"%self.cmd.id)
        #self._returnResults()

def runThreadFn(workload, condVar):
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
    condVar.acquire()
    workload.running=False
    workload.realTimeSpent += endTime-startTime
    condVar.notify() 
    condVar.release()

