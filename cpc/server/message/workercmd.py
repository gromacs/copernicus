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


import json
import logging
import os
import tarfile
import tempfile
import threading



import cpc.server.command.platform_exec_reader
import cpc.server.state.cmdlist
import cpc.util
import cpc.util.log

from cpc.worker.message import WorkerMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.util import json_serializer
from cpc.network.node import Nodes,Node
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.server.command import Resource
from cpc.server.tracking.tracker import Tracker
from cpc.util.conf.server_conf import ServerConf
from cpc.util.conf.connection_bundle import ConnectionBundle
from server_command import ServerCommand

log=logging.getLogger('cpc.server.workercmd')

class CommandWorkerMatcher(object):
    """Object that stores information about a worker for the 
       matchCommandWorker() function that is used in queue.getUntil()"""
    def __init__(self, platforms, executableList):
        self.platforms=platforms
        self.executableList=executableList
        maxPlatform=platforms[0]
        # get the platform with the biggest number of cores.
        ncores_max=0
        for platform in platforms:
            if (platform.hasMaxResource('cores')):
                ncores_now=platform.getMaxResource('cores')
                if ncores_now > ncores_max:
                    ncores_max=ncores_now
                    maxPlatform=platform
        self.usePlatform=maxPlatform
        # construct a list of all max. resources with settings for the
        # platform we use.
        self.used=dict()
        for rsrc in self.usePlatform.getMaxResources().itervalues():
            self.used[rsrc.name]=Resource(rsrc.name, 0)
        self.type=None

    def checkType(self, type):
        """Check whether the command type is the same as one used before in the
           list of commands to send back"""
        if self.type is None:
            self.type=type
            return True
        return type == self.type

    def getExecID(self, cmd):
        """Check whether the worker has the right executable."""
        # first try the usePlatform
        
        ret=self.executableList.find(cmd.executable, self.usePlatform,
                                     cmd.minVersion, cmd.maxVersion)
        if ret is not None:
            return ret.getID()
        for platform in self.platforms:
            ret=self.executableList.find(cmd.executable, platform,
                                         cmd.minVersion, cmd.maxVersion)
            if ret is not None:
                return ret.getID()
        return None


    def checkAddResources(self, cmd):
        """Check whether a command falls within the current resource allocation
           and add its requirements to teh used resources if it does.
           cmd = the command to check
           returns: True if the command fits within the capabilities is added,
                    False if the command doesn't fit."""
        for rsrc in self.used.itervalues():
            platformMax = self.usePlatform.getMaxResource(rsrc.name)
            cmdMinRsrc = cmd.getMinRequired(rsrc.name)
            rsrcLeft = platformMax - rsrc.value
            if cmdMinRsrc is not None:
                # check whether there's any left
                if rsrcLeft < cmdMinRsrc:
                    log.debug("Left: %d, max=%d, minimum resources: %d"%
                              (rsrcLeft, platformMax, cmdMinRsrc))
                    return False
        # now reserve the resources
        cmd.resetReserved()
        for rsrc in self.used.itervalues():
            platformMax = self.usePlatform.getMaxResource(rsrc.name)
            platformPref = self.usePlatform.getPrefResource(rsrc.name)
            cmdMinRsrc = cmd.getMinRequired(rsrc.name)
            if cmdMinRsrc is not None:
                rsrcLeft = platformMax - rsrc.value
                if (platformPref is not None and rsrcLeft>platformPref):
                    value=platformPref
                else:
                    value=rsrcLeft
                # now we know how many
                log.debug("Reserving %d cores"%value)
                cmd.setReserved(rsrc.name, value)
                rsrc.value += value
        return True


def matchCommandWorker(matcher, command):
    """Function to use in queue.getUntil() to get a number of commands from
       the queue.
       TODO: this is where performance tuning results should be used."""
    cont=True # whether to continue getting commands from the queue
    # whether to use this command: make sure we only have a single type
    use=False
    execID=matcher.getExecID(command)
    log.debug('exec id is %s'%execID)
    if execID is not None:
        use=matcher.checkType(command.getTask().getFunctionName())
    if use:
        if matcher.checkAddResources(command):
            use=True
        else:
            use=False
            cont=False
    return (cont, use)

#Child to Parent message
class SCWorkerReady(ServerCommand):
    """Respond to the availability of a worker with a command to execute"""
    def __init__(self):
        ServerCommand.__init__(self, "worker-ready")

    def run(self, serverState, request, response):
        # first read platform capabilities and executables
        rdr=cpc.server.command.platform_exec_reader.PlatformExecutableReader()
        workerData=request.getParam('worker')
        log.debug("Worker platform + executables: %s"%workerData)
        rdr.readString(workerData,"Worker-reported platform + executables")
        # match queued commands to executables.
        cwm=CommandWorkerMatcher(rdr.getPlatforms(), rdr.getExecutableList())
        cmds=serverState.getCmdQueue().getUntil(matchCommandWorker, cwm)
        if request.headers.has_key('originating-server'):
            originating = request.headers['originating-server']
        else:
            originating = ServerConf().getHostName() #FIXME this cannot be correct ever
        log.debug("worker identified %s"%request.headers['originating-client'] )
        serverState.setWorkerState("idle",workerData,request.headers['originating-client'])    
        
        if len(cmds) > 0:
            # construct the tar file.
            tff=tempfile.TemporaryFile()
            tf=tarfile.open(fileobj=tff, mode="w:gz")
            rcmd=serverState.getRunningCmdList()
            # make the commands ready
            for cmd in cmds:
                log.debug("Adding command id %s to tar file."%cmd.id)
                # write the command description to the command's directory
                task=cmd.getTask()
                log.debug(cmd)
                project=task.getProject()
                taskDir = "task_%s"%task.getID()
                cmddir=os.path.join(project.basedir,taskDir, cmd.dir)
                arcdir="%s"%(cmd.id)
                outf=open(os.path.join(cmddir, "command.xml"), "w")
                cmd.writeWorkerXML(outf)
                outf.close()
                tf.add(cmddir, arcname=arcdir, recursive=True)
                # set the state of the command.
                #cmd.setRunning(True, originating)
                rcmd.add(cmd, originating)
                #cmd.getTask().setState(Task.running)
                #FIXME commands should have a set state
                
            tf.close()
            tff.seek(0)
            # now send it back
            response.setFile(tff,'application/x-tar')
            #project.writeTasks()
            # the file is closed after the response is sent.            
        else:
            conf = ServerConf()
            nodes = conf.getNodes().getNodesByPriority()
            
            topology = Nodes()
            if request.hasParam('topology'):
                topology = json.loads(request.getParam('topology')
                                      ,object_hook = json_serializer.fromJson)
            
            thisNode = Node(conf.getHostName(),conf.getServerHTTPPort(),conf.getServerHTTPSPort(),conf.getHostName())                                
            thisNode.nodes = conf.getNodes()      
            topology.addNode(thisNode)
      
            hasJob =False # temporary flag that should be removed
            for node in nodes:
                if topology.exists(node.getId()) == False:
                    clnt = WorkerMessage(node.host,node.https_port) 
                    
                    clientResponse = clnt.workerRequest(workerData,topology)
                    
                    if clientResponse.getType() == 'application/x-tar':

                        log.log(cpc.util.log.TRACE,'got work from %s'%(clientResponse.headers['originating-server']))
                        hasJob=True
                        # we need to rewrap the message 
                        
                        #FIXME stupid intermediary step because the mmap form clientresponse is prematurely closed                        
                        tmp = tempfile.TemporaryFile('w+b')
                        
                        message = clientResponse.getRawData()
                        
                        tmp.write(message.read(len(message)))
                        tmp.seek(0)    
                        
                        #for key in clientResponse.headers:
                        #    print "%s:%s"%(key,clientResponse.headers[key])
                                                    
                        response.setFile(tmp,'application/x-tar')
                        response.headers['originating-server']=\
                                  clientResponse.headers['originating-server']
                    #OPTIMIZE leads to a lot of folding and unfolding of packages 
                    
            if not hasJob:           
                response.add("No command")

class SCCommandFinishedForward(ServerCommand):
    """Get forwarded finished command info. The command output is not sent in 
       this message"""
    def __init__(self):
        ServerCommand.__init__(self, "command-finished-forward")

    def run(self, serverState, request, response):
        self.lock = threading.Lock()
        cmdID=request.getParam('cmd_id')
        workerServer=request.getParam('worker_server')
        cmd=serverState.getRunningCmdList().get(cmdID)
        cputime=0
        if request.hasParam('used_cpu_time'):
            cputime=float(request.getParam('used_cpu_time'))
      
        if workerServer is not None:  
            #remote asset tracking
            serverState.getRemoteAssets().addAsset(cmdID, workerServer)
            
            #for now, get the command data output immediately
            rundata = Tracker.getCommandOutputData(cmdID, workerServer)
        else:
            rundata=None
        runfile = None
        if rundata != None:
            runfile = rundata.getRawData()
        log.log(cpc.util.log.TRACE,"finished forward command %s"%cmdID)

        serverState.getRunningCmdList().handleFinished(cmd)
        
        #TODO should be located elsewhere
        with self.lock:
            cmd.running = False
            cmd.addCputime(cputime)
            if runfile is not None:
                log.debug("extracting file for %s to dir %s"%(cmdID,cmd.dir))
                cpc.util.file.extractSafely(cmd.dir, fileobj=runfile)
        
        task = cmd.getTask()
        (newcmds, cancelcmds) = task.run(cmd)
            
        cmdQueue = serverState.getProjectList().getCmdQueue()
        if cancelcmds is not None:
            for cmd in cancelcmds:
                cmdQueue.remove(cmd)
        if newcmds is not None:
            for cmd in newcmds:
                cmdQueue.add(cmd)
        
        #TODO handle persistence
        
                
        
class SCCommandFinished(ServerCommand):
    """Get finished command data."""
    def __init__(self):
        ServerCommand.__init__(self, "command-finished")

    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        runfile=request.getFile('rundata')
        projServer=request.getParam('project_server')
        cputime=0
        if request.hasParam('used_cpu_time'):
            cputime=float(request.getParam('used_cpu_time'))
        
        #the command's workerserver is by definition this server
        workerServer = serverState.conf.getHostName()
        
        # TODO: some sort of verification  to check whether this was in fact
        #       the client that we sent the command to
        serverState.getLocalAssets().addCmdOutputAsset(cmdID, 
                                                       projServer, runfile)
        
        #forward CommandFinished-signal to project server
        log.debug("finished command %s"%cmdID)
        #msg=ServerToServerMessage(projServer)
        #ret = msg.commandFinishForwardRequest(cmdID, workerServer, cputime)
        msg=ServerToServerMessage(projServer)  #FIXME if this is current server do not make a connection to self??
        ret = msg.commandFinishForwardRequest(cmdID, workerServer, cputime)

class SCCommandFailed(ServerCommand):
    """Get notified about a failed run."""
    def __init__(self):
        ServerCommand.__init__(self, "command-failed")
    
    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        # For now, do a similar thing to WorkerFinished
        try:
            runfile=request.getFile('rundata')
        except cpc.util.CpcError:
            runfile=None
        cputime=0
        if request.hasParam('used_cpu_time'):
            cputime=float(request.getParam('used_cpu_time'))
        log.error("Failed cmd_id = %s\n"%cmdID)
        cmdID=request.getParam('cmd_id')
        projServer=request.getParam('project_server')
        
        #the command's workerserver is by definition this server
        workerServer = serverState.conf.getHostName()
   
        log.debug("runfile= %s, projServer=%s"%(str(runfile), str(projServer)) )
        if runfile is not None:    
            # TODO: some sort of verification  to check whether this was in fact
            #       the client that we sent the command to
            serverState.getLocalAssets().addCmdOutputAsset(cmdID, 
                                                           projServer, runfile)
        #forward CommandFinished-signal to project server
        log.debug("Run failure reported")
        msg=ServerToServerMessage(projServer)
        ret = msg.commandFinishForwardRequest(cmdID, workerServer, cputime)
        #found=False
        #try:
        #    cmd=serverState.getRunningCmdList().get(cmdID)
        #    if cmd is not None:
        #        found=True
        #    # remove the command from the running list
        #    serverState.getRunningCmdList().handleFinished(cmd)
        #    #getRunningCmdList().remove(cmd)
        #    # handle its new state
        #    #project=cmd.getTask().getProject()
        #    #project.handleFinishedCommand(cmd, runfile)
        #    #project.writeTasks()
        #except cpc.server.state.cmdlist.RunningCmdListError:
        #    # it wasn't found. 
        #    found=False
        #if found:
        #    response.add("Run failure reported succesfully.")
        #else:
        #    response.add("Command ID %s not found."%cmdID, status="ERROR")
       

class SCWorkerHeartbeat(ServerCommand):
    """Handle a worker's heartbeat signal."""
    def __init__(self):
        ServerCommand.__init__(self, "worker-heartbeat")

    def run(self, serverState, request, response):
        workerID=request.getParam('worker_id')
        workerDir=request.getParam('worker_dir')
        iteration=request.getParam('iteration')
        itemsXML=request.getParam('heartbeat_items')
        # handle this from within the (locked) list that we have of all 
        # monitored runs
        serverState.getHeartbeatList().ping(workerID, workerDir,
                                            iteration, itemsXML, response)

class SCWorkerFailed(ServerCommand):
    """Get notified about a failed worker."""
    def __init__(self):
        ServerCommand.__init__(self, "worker-failed")

    def run(self, serverState, request, response):
        workerID=request.getParam('worker_id')
        retOK=serverState.getHeartbeatList().workerFailed(workerID)
        if retOK:
            response.add("Worker failure reported succesfully.")
        else:
            response.add("Worker ID %s not found."%workerID, status="ERROR")


 
