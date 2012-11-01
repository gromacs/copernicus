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


import os
import os.path
import copy
import tarfile
import shutil
import tempfile
import logging
import threading
import signal
import time


import cpc.util.file
import cpc.command
from cpc.command.platform_reservation import PlatformReservation
from cpc.util.plugin import PlatformPlugin
import workload
import heartbeat
from cpc.worker.message import WorkerMessage

log=logging.getLogger('cpc.worker')
import sys

class WorkerError(cpc.util.CpcError):
    pass


# variables for the signal handler associated with workers
signalHandlerLock=threading.Lock() # the lock for the workers list
signalHandlerWorkers=[] # the list of workers to shutdown
signalHandlerWorking=False # whether the signal handler has been installed

def _signalHandlerFunction(signum, frame):
    """The signal handler function. """
    # Start a thread and handle signals in that thread. This allows us to
    # safely lock mutexes.
    th=threading.Thread(target=_signalHandlerThread)
    th.daemon=True
    th.start()

def _signalHandlerThread():
    """Helper function for signal handling."""
    global signalHandlerLock
    global signalHandlerWorkers
    global signalHandlerWorking
    with signalHandlerLock:
        for worker in signalHandlerWorkers:
            worker.shutdown()

def signalHandlerAddWorker(worker):
    """Add one worker to the list of workers to notify when a signal arrives."""
    global signalHandlerLock
    global signalHandlerWorkers
    global signalHandlerWorking
    """Add a worker to the list of workers for the signal handler"""
    with signalHandlerLock:
        signalHandlerWorkers.append(worker)
        if not signalHandlerWorking:
            signalHandlerWorking=True
            signal.signal(signal.SIGINT, _signalHandlerFunction)


class Worker(object):
    """The worker class creates a worker client that contacts a server
       and asks for tasks."""
    def __init__(self, cf, opts, type, args, workdir, quitMinutes):
        """Initialize the object as a client, given a configuration.
           cf =  the configuration class
		   opts = dictionary with options
           type = the worker plugin name to start.
           args = arguments for the worker plugin."""
        self.conf=cf
        self.opts = opts
        self.type=type
        self.args=args
        self.quit=False
        self.id="%s-%d"%(self.conf.getHostName(), os.getpid())
        # the number of seconds after which to quit if there is no work:
        self.quitSeconds=None 
        if quitMinutes is not None:
            self.quitSeconds=60*quitMinutes
        log.info("Worker ID: %s."%self.id)
        # Process (untar) the run request into a directory name
        # that is unique for this process+hostname, and worker job iteration
        if workdir is None:
            self.workerTopDir=self.conf.getRunDir()
            createTopDir=True
            #self.mainDir=os.path.join(self.conf.getRunDir(), self.id)
        else:
            if not os.path.exists(workdir):
                raise WorkerError("Given run directory %s does not exist."%
                                  (workdir))
            self.workerTopDir=workdir
            createTopDir=False

        # fix the path so the server knows where it is
        if not os.path.isabs(self.workerTopDir):
            self.workerTopDir=os.path.join(os.getcwd(), self.workerTopDir)
            isabs=False
        else:
            isabs=True

        # set the actual path being used.
        self.mainDir=os.path.join(self.workerTopDir, self.id)

        try:
            log.debug("Creating work directory %s"%(self.mainDir))
            if createTopDir:
                if not os.path.exists(self.workerTopDir):
                    os.mkdir(self.workerTopDir)
                self.workerTopDirCreated=True
            else:
                self.workerTopDirCreated=False
            os.mkdir(self.mainDir)
        except:
            if isabs:
                absn=""
            else:
                absn="in the current working directory"
            log.error("Can't create the directory '%s' %s."% (self.mainDir, 
                                                              absn))
            log.error(
                   "cpc-worker must be able to write in a temporary directory")
            log.error(
                   "Run cpc-worker from a user-writeable directory (e.g. /tmp)")
            raise WorkerError("Can't create directory '%s' %s."%
                              (self.mainDir, absn))
        self.heartbeat=heartbeat.HeartbeatSender(self.id, self.mainDir)
        # First get our architecture(s) (hw + sw) from the plugin
        self.plugin=PlatformPlugin(self.type, self.mainDir, self.conf)
        canRun=self.plugin.canRun()
        if not canRun:
            raise WorkerError("Plugin can't run.")
        self.platforms=self._getPlatforms(self.plugin)

        # we make copies to be able to subtract our usage off the max resources
        self.remainingPlatforms=copy.deepcopy(self.platforms)
        # Then check what executables we already have
        self._getExecutables()
        # start without workloads

        if len(self.exelist.findAllByPlattform(self.type)) == 0:
            print "No executables found for platform %s"%self.type
            sys.exit(1)

        self._printAvailableExes()
        self.workloads=[]
        # the run lock and condition variable
        self.runLock=threading.Lock()
        self.runCondVar=threading.Condition(self.runLock)
        self.iteration=0
        self.acceptCommands = True
        # install the signal handler
        signalHandlerAddWorker(self)

    def run(self):
        """Ask for tasks until told to quit."""
        noWorkSeconds=0
        while not self.quit:
            # send a request for a command to run
            startWaitingTime=time.time()
            with self.runCondVar:
                acceptCommands=self.acceptCommands
            if acceptCommands:
                resp=self._obtainCommands()
                # and extract the command and run directory
                workloads=self._extractCommands(resp)
                log.info("Got %d commands."%len(workloads))
                for workload in workloads:
                    log.info("cmd ID=%s"%workload.cmd.id)
                    # Check whether we have the neccesary executable.
                    # (If not, we need to ask for it)
                    if workload.executable is None:
                        # TODO: implement getting the executable
                        log.error("Found no executable!")
                        raise WorkerError("Executable not found")
                    workload.reservePlatform()
                if len(workloads)>0:
                    # We first prepare
                    self._prepareWorkloads(workloads)
                    # add the new workloads to our lists
                    self.workloads.extend(workloads)
                    self.heartbeat.addWorkloads(workloads)
                    # Now we run.
                    log.debug("Running workloads: %d"%len(self.workloads))
                    #hb=heartbeat.Heartbeat(cmd.id, origServer, rundir)
                    # just before starting to run, we again check whether we
                    # should.
                    with self.runCondVar:
                        acceptCommands=self.acceptCommands
                    if acceptCommands:
                        for workload in workloads:
                            workload.run(self.runCondVar, self.plugin,
                                         self.args)
            # now wait until a workload finishes
            finishedWorkloads = []
            self.runCondVar.acquire()
            continueWaiting=True
            while continueWaiting:
                haveFinishedWorkloads=False
                for workload in self.workloads:
                    if not workload.running:
                        haveFinishedWorkloads=True
                        break
                if self.acceptCommands and not haveFinishedWorkloads:
                    haveRemainingResources=self._haveRemainingResources()
                    if haveRemainingResources:
                        log.info("Have free resources. Waiting 30 seconds")
                        self.runCondVar.wait(30)
                        continueWaiting=False
                    else:
                        # we can't ask for new jobs, so we wait indefinitely
                        self.runCondVar.wait()
                else:
                    continueWaiting=False
                # loop over all workloads
                for workload in self.workloads:
                    if not workload.running:
                        finishedWorkloads.append(workload)
                        log.info("Command id %s finished"%workload.cmd.id)
                        continueWaiting=False
                    #else:
                    #    log.debug("Command %s still running"%workload.cmd.id)
                #log.debug("End of waiting loop")
            #log.debug("Out of waiting loop")
            self.runCondVar.release()
            stopWaitingTime=time.time()
            # check whether there was work to do. If not, start counting
            # the amount of time we waited.
            if len(self.workloads) == 0:
                noWorkSeconds += stopWaitingTime-startWaitingTime
                if ( ( self.quitSeconds is not None ) and 
                     ( noWorkSeconds > self.quitSeconds ) ):
                    with self.runCondVar:
                        # signal quit.
                        self.acceptCommands=False
            else:
                noWorkSeconds = 0
            # now deal with finished workloads.
            for workload in finishedWorkloads:
                workload.finish(self.plugin, self.args)
                workload.returnResults()
                workload.releasePlatform()
            if len(finishedWorkloads)>0:
                self.heartbeat.delWorkloads(finishedWorkloads)
                for workload in finishedWorkloads:
                    self.workloads.remove(workload)
            with self.runCondVar:
                acceptCommands=self.acceptCommands
            if not acceptCommands and len(self.workloads)==0:
                self.quit = True
        self.heartbeat.stop()


    def cleanup(self):
        shutil.rmtree(self.mainDir)
        # now clean up the worker top dir. This might be in use by other workers
        # so we use rmDir
        try:
            if self.workerTopDirCreated:
                os.rmdir(self.workerTopDir)
        except:
            log.debug("Couldn't erase worker top dir %s"%self.workerTopDir)

    def _printAvailableExes(self):

        print "Available executables for platform %s:"%self.type
        for exe in self.exelist.findAllByPlattform(self.type):
            print "%s %s"%(exe.name,exe.version.getStr())


    def _getPlatforms(self, plugin):
        """Get the list of platforms als an XML string from the run plugin."""
        # make an empty platform reservation
        plr=PlatformReservation(self.mainDir)
        plugin_retmsg=plugin.run(".", "platform", self.args,
                                 str(plr.printXML()))
        if plugin_retmsg[0] != 0:
            log.error("Platform plugin failed: %s"%plugin_retmsg[1])
            raise WorkerError("Platform plugin failed: %s"%plugin_retmsg[1])
        log.debug("From platform plugin, platform cmd: '%s'"%plugin_retmsg[1])
        pfr=cpc.command.PlatformReader()
        # we also parse it for later.
        pfr.readString(plugin_retmsg[1],
                       ("Platform description from platform plugin %s"%
                        plugin.name) )
        platforms=pfr.getPlatforms()
        return platforms

    def _getExecutables(self):
        """Get a list of executables as an ExecutableList object."""
        execdirs=self.conf.getExecutablesPath()
        self.exelist=cpc.command.ExecutableList()
        for execdir in execdirs:
            self.exelist.readDir(execdir, self.platforms)
        self.exelist.genIDs()

        log.debug("Found %d executables."%(len(self.exelist.executables)))

    def _obtainCommands(self):
        """Obtain a command from the up-most server given a list of
           platforms and exelist. Returns the client response object."""
        # Send a run request with our arch+binaries
        req=u'<?xml version="1.0"?>\n'
        req+=u'<worker-request>\n'
        req+=u'<worker-arch-capabilities>\n'
        for platform in self.remainingPlatforms:
            req+=platform.printXML()
        req+='\n'
        req+=self.exelist.printPartialXML()
        req+=u'\n</worker-arch-capabilities>'
        #Append optional project specifics
        req+=u'\n<worker-requirements>\n'
        if "project" in self.opts:
            req+=u'  <option key="project" value="%s"/>\n'%self.opts['project']
        req+=u'</worker-requirements>\n'
        req+=u'</worker-request>\n'
        log.debug('request string is: %s'%req)
        runreq_clnt=WorkerMessage()
        resp=runreq_clnt.workerRequest(self.id,req)
        #print "Got %s"%(resp.read(len(resp)))
        return resp

    def _extractCommands(self, resp):
        """Extract a command and a run directory from a server response.
            Returns a list of Workloads."""
        workloads=[]
        log.debug("Response type=%s"%resp.getType())
        if resp.getType() == "application/x-tar":
            if resp.headers.has_key('originating-server'):
                origServer=resp.headers['originating-server']
            elif resp.headers.has_key('Originating-Server'):
                origServer=resp.headers['Originating-Server']
            else:
                raise WorkerError("Originating server not found")
            log.debug("Originating server: %s"%origServer)
            rundir=os.path.join(self.mainDir, "%d"%self.iteration)
            log.debug("run directory: %s"%rundir)
            #os.mkdir(rundir)
            cpc.util.file.extractSafely(rundir, fileobj=resp.getRawData())
            # get the commands.
            i=0
            for subdir in os.listdir(rundir):
                cmddir=os.path.join(rundir, subdir)
                if os.path.exists(os.path.join(cmddir, "command.xml")):
                    log.debug("trying command directory: %s"%cmddir)
                    # there is a command here. Get the command.
                    cr=cpc.command.CommandReader()
                    commandFilename=os.path.join(cmddir, "command.xml")
                    cr.read(commandFilename)
                    # write log
                    inf=open(commandFilename, "r")
                    log.debug("Received job. Command is: %s"%inf.read())
                    inf.close()
                    cmd=cr.getCommands()[0]
                    (exe, pf)=self._findExecutable(cmd)
                    if (exe is None):
                        raise WorkerError("Executable not found")
                    id="%d/%d"%(self.iteration, i)
                    workloads.append(workload.WorkLoad(self.mainDir, cmd,
                                                       cmddir, origServer,
                                                       exe, pf, id))
                    i+=1
            resp.close()
        self.iteration+=1
        return workloads

    def _findExecutable(self, cmd):
        """Find the right executable for a command given the list of platforms.
           cmd = the command
           returns tuple with the executable and the platform
           """
        for platform in self.remainingPlatforms:
            # we iterate in the order we got from the run plugin. This
            # might be important: it should return in the order it thinks
            # goes from most to least optimal.

            log.debug("Using platform %s for executable search"%platform.name)
            exe=self.exelist.find(cmd.executable, platform,
                                  cmd.minVersion, cmd.maxVersion)
            if exe is not None:
                log.debug("Found matching executable")
                return (exe, platform)
        return (None, None)

    def _prepareWorkloads(self, workloadlist):
        """Prepare the workloads (by joining, for example)."""
        # do a join
        joinableWorkloads=[]
        for workload in workloadlist:
            if (workload.platform.isJoinPrefered() and
                workload.executable.isJoinable()):
                joinableWorkloads.append(workload)
        while len(joinableWorkloads)>0:
            joinTo=joinableWorkloads[0]
            joinableWorkloads.remove(joinTo)
            join=[]
            for i in range(len(joinableWorkloads)):
                if joinTo.canJoin(joinableWorkloads[i]):
                    log.debug("Joining command %s and %s"%
                              (joinTo.cmd.id, joinableWorkloads[i].cmd.id))
                    join.append(joinableWorkloads[i])
            # and do the actual joining
            if len(join)>0:
                joinTo.join(join)
                for j in join:
                    # now remove those from the original lists
                    joinableWorkloads.remove(j)
                    workloadlist.remove(j)

    def _haveRemainingResources(self):
        """Check whether any of the resources has been depleted.
           returns: True if none of the resources have been depleted, False
                    otherwise
           """
        for platform in self.remainingPlatforms:
            for rsrc in platform.getMaxResources().itervalues():
                if rsrc.value <= 0:
                    return False
        return True

    def shutdown(self):
        """Shut down this worker cleanly. This must be called from a thread,
           not directly from a signal handler."""
        #log.log(cpc.util.log.TRACE,"Received shutdown signal")
        log.debug("Received shutdown signal")
        # now set the variable and notify
        self.runCondVar.acquire()
        self.acceptCommands = False
        self.runCondVar.notifyAll()
        self.runCondVar.release()


