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
import time



import cpc.server.command.platform_exec_reader
import cpc.server.state.cmdlist
import cpc.util
import cpc.util.log

from cpc.server.command.worker_matcher import CommandWorkerMatcher

from cpc.worker.message import WorkerMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.util import json_serializer
from cpc.network.node import Nodes,Node
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.server.tracking.tracker import Tracker
from cpc.util.conf.server_conf import ServerConf
from cpc.util.conf.connection_bundle import ConnectionBundle
from server_command import ServerCommand

log=logging.getLogger('cpc.server.workercmd')


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
        cwm=CommandWorkerMatcher(rdr.getPlatforms(), 
                                 rdr.getExecutableList(),
                                 rdr.getWorkerRequirements())
        cmds=cwm.getWork(serverState.getCmdQueue())
        if not cwm.isDepleted():
            # now sleep for 5 seconds to give the dataflow time to react to any 
            # new state. 
            time.sleep(5)
            cmds.extend(cwm.getWork(serverState.getCmdQueue()))
        #cmds=serverState.getCmdQueue().getUntil(matchCommandWorker, cwm)
        if request.headers.has_key('originating-server'):
            originating = request.headers['originating-server']
        else:
            # If the originating server property has not been set,  the 
            # request hasn't been forwarded, therefore we are the originating 
            # server
            originating = ServerConf().getHostName() 
        log.debug("worker identified %s"%request.headers['originating-client'] )
        serverState.setWorkerState("idle",workerData,
                                   request.headers['originating-client'])    
        
        if len(cmds) > 0:
            # construct the tar file with the workloads. 
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
            
            thisNode = Node(conf.getHostName(),
                            conf.getServerHTTPPort(),
                            conf.getServerHTTPSPort(),
                            conf.getHostName())                                
            thisNode.nodes = conf.getNodes()      
            topology.addNode(thisNode)
      
            hasJob =False # temporary flag that should be removed
            for node in nodes:
                if topology.exists(node.getId()) == False:
                    log.log(cpc.util.log.TRACE,'IMAN from %s'%node.host)
                    clnt = WorkerMessage(node.host,
                                         node.https_port,
                                         conf=ServerConf()) 
                    
                    clientResponse = clnt.workerRequest(workerData,topology)
                    
                    if clientResponse.getType() == 'application/x-tar':

                        log.log(cpc.util.log.TRACE,
                                'got work from %s'%
                                (clientResponse.headers['originating-server']))
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
        returncode=None
        if request.hasParam('return_code'):
            returncode=int(request.getParam('return_code'))
        cputime=0
        if request.hasParam('used_cpu_time'):
            cputime=float(request.getParam('used_cpu_time'))

        if ( workerServer is not None and 
            ( request.hasParam('run_data') and 
              int(request.getParam('run_data'))!=0 ) ): 
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
            cmd.setReturncode(returncode)
            cmd.addCputime(cputime)
            if runfile is not None:
                log.debug("extracting file for %s to dir %s"%(cmdID,cmd.dir))
                cpc.util.file.extractSafely(cmd.dir, fileobj=runfile)
        
        task = cmd.getTask()
        if task is not None:
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
        returncode=None
        if request.hasParam('return_code'):
            returncode=int(request.getParam('return_code'))
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
        ret = msg.commandFinishForwardRequest(cmdID, workerServer, 
                                              returncode, cputime, True)

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
        returncode=None
        if request.hasParam('return_code'):
            returncode=int(request.getParam('return_code'))
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
        ret = msg.commandFinishForwardRequest(cmdID, workerServer, returncode, 
                                              cputime, (runfile is not None))

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


 
