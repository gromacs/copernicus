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
import shutil

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO




import cpc.command.platform_exec_reader
import cpc.util
import cpc.util.log

from cpc.command.worker_matcher import CommandWorkerMatcher

from cpc.worker.message import WorkerMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.util import json_serializer
from cpc.network.node import Nodes,Node
from cpc.server.message.server_message import ServerMessage
from cpc.server.tracking.tracker import Tracker
from cpc.util.conf.connection_bundle import ConnectionBundle
from server_command import ServerCommand
from cpc.network.node import getSelfNode

import cpc.command.heartbeat



log=logging.getLogger('cpc.server.workercmd')


#Child to Parent message
class WorkerReadyBase(ServerCommand):
    """Respond to the availability of a worker with a command to execute.
       This is the base class for SCWorkerReady and SCWorkerReadyForwarded,
       which implement the same functions. This way we kan enforce the
       setting of worker_server and heartbeat-interval properties only on
       the server, not the client."""

    def run(self, serverState, request, response):
        # first read platform capabilities and executables
        rdr=cpc.command.platform_exec_reader.PlatformExecutableReader()
        workerData=request.getParam('worker')
        if request.hasParam('worker-id'):
            workerID=request.getParam('worker-id')
        else:
            workerID='(none)'
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
        # now check the forwarded variables
        conf=serverState.conf
        originating=None
        heartbeatInterval=None
        # check whether there is an originating server. If not, we're it
        if self.forwarded:
            if request.hasParam('originating-server'):
                originating = request.getParam('originating-server')
            # check the expected heartbeat time.
            log.debug("Forwarded message")
            if request.hasParam('heartbeat-interval'): 
                heartbeatInterval = int(request.getParam('heartbeat-interval'))
                log.debug("Forwarded heartbeat interval is %d"%
                          heartbeatInterval)
        if originating is None:
            # If the originating server property has not been set,  the 
            # request hasn't been forwarded, therefore we are the originating 
            # server
            selfNode=getSelfNode(conf)
            originating = selfNode.getId() 
        if heartbeatInterval is None:
            heartbeatInterval = conf.getHeartbeatTime() 
        log.debug("worker identified %s"%request.headers['originating-client'] )
        serverState.setWorkerState("idle",workerData,
                                   request.headers['originating-client'])
        
        if len(cmds) > 0:
            # first add them to the running list so they never get lost
            runningCmdList=serverState.getRunningCmdList()
            runningCmdList.add(cmds, originating, heartbeatInterval)
            # construct the tar file with the workloads. 
            tff=tempfile.TemporaryFile()
            tf=tarfile.open(fileobj=tff, mode="w:gz")
            # make the commands ready
            for cmd in cmds:
                log.debug("Adding command id %s to tar file."%cmd.id)
                # write the command description to the command's directory
                task=cmd.getTask()
                #log.debug(cmd)
                project=task.getProject()
                taskDir = "task_%s"%task.getID()
                cmddir=cmd.getDir()
                #os.path.join(project.basedir,taskDir, cmd.getDir())
                arcdir="%s"%(cmd.id)
                log.debug("cmddir=%s"%cmddir)
                outf=open(os.path.join(cmddir, "command.xml"), "w")
                cmd.writeWorkerXML(outf)
                outf.close()
                tf.add(cmddir, arcname=arcdir, recursive=True)
                # set the state of the command.
            tf.close()
            tff.seek(0)
            # now send it back
            response.setFile(tff,'application/x-tar')
            #project.writeTasks()
            # the file is closed after the response is sent.            
            log.info("Did direct worker-ready")
        else:
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
                    clnt=ServerMessage(node.getId())
                    
                    clientResponse=clnt.workerReadyForwardedRequest(workerID,
                                                            workerData,
                                                            topology,
                                                            originating,
                                                            heartbeatInterval)
                    
                    if clientResponse.getType() == 'application/x-tar':

                        log.log(cpc.util.log.TRACE,
                                'got work from %s'%
                                (clientResponse.headers['originating-server']))
                        hasJob=True
                        # we need to rewrap the message 
                        
                        #FIXME stupid intermediary step because the mmap form 
                        # clientresponse is prematurely closed
                        tmp = tempfile.TemporaryFile('w+b')
                        
                        message = clientResponse.getRawData()
                        
                        tmp.write(message.read(len(message)))
                        tmp.seek(0)    
                        
                        #for key in clientResponse.headers:
                        #    print "%s:%s"%(key,clientResponse.headers[key])
                                                    
                        response.setFile(tmp,'application/x-tar')
                        response.headers['originating-server']=\
                                  clientResponse.headers['originating-server']
                    #OPTIMIZE leads to a lot of folding and unfolding of 
                    #packages 
            if not hasJob:           
                response.add("No command")
            log.info("Did delegated worker-ready")


class SCWorkerReady(WorkerReadyBase):
    def __init__(self):
        self.forwarded=False
        ServerCommand.__init__(self, "worker-ready")

class SCWorkerReadyForwarded(WorkerReadyBase):
    def __init__(self):
        self.forwarded=True
        ServerCommand.__init__(self, "worker-ready-forward")


class SCCommandFinishedForward(ServerCommand):
    """Handle forwarded finished command. The command output is not sent in 
       this message"""
    def __init__(self):
        ServerCommand.__init__(self, "command-finished-forward")

    def run(self, serverState, request, response):
        #self.lock = threading.Lock()
        cmdID=request.getParam('cmd_id')
        workerServer=request.getParam('worker_server')
        #cmd=runningCmdList.getCmd(cmdID)
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
        #log.log(cpc.util.log.TRACE,"finished forward command %s"%cmdID)
        runningCmdList=serverState.getRunningCmdList()
        runningCmdList.handleFinished(cmdID, returncode, cputime, runfile)
        log.info("finished forward command %s"%cmdID)


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
        selfNode=getSelfNode(serverState.conf)
        workerServer = selfNode.getId() #ServerConf().getHostName() 
        #workerServer = serverState.conf.getHostName()
        
        # TODO: some sort of verification  to check whether this was in fact
        #       the client that we sent the command to
        serverState.getLocalAssets().addCmdOutputAsset(cmdID, 
                                                       projServer, runfile)
        
        #forward CommandFinished-signal to project server
        #FIXME if this is current server do not make a connection to self??
        msg=ServerMessage(projServer)  
        ret = msg.commandFinishedForwardedRequest(cmdID, workerServer, 
                                                  returncode, cputime, True)
        log.info("Finished command %s"%cmdID)

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
        selfNode=getSelfNode(serverState.conf)
        workerServer = selfNode.getId() #ServerConf().getHostName() 
        #workerServer = serverState.conf.getHostName()
   
        log.debug("runfile= %s, projServer=%s"%(str(runfile), str(projServer)) )
        if runfile is not None:    
            # TODO: some sort of verification  to check whether this was in fact
            #       the client that we sent the command to
            serverState.getLocalAssets().addCmdOutputAsset(cmdID, 
                                                           projServer, runfile)
        #forward CommandFinished-signal to project server
        msg=ServerMessage(projServer)
        ret = msg.commandFinishedForwardedRequest(cmdID, workerServer, 
                                                  returncode, cputime, 
                                                  (runfile is not None))
        log.info("Run failure reported on %s"%cmdID)

class SCWorkerHeartbeat(ServerCommand):
    """Handle a worker's heartbeat signal."""
    def __init__(self):
        ServerCommand.__init__(self, "worker-heartbeat")

    def run(self, serverState, request, response):
        workerID=request.getParam('worker_id')
        workerDir=request.getParam('worker_dir')
        iteration=request.getParam('iteration')
        itemsXML=request.getParam('heartbeat_items')
        version=0
        if request.hasParam('version'):
            version=int(request.getParam('version'))
        hwr=cpc.command.heartbeat.HeartbeatItemReader()
        hwr.readString(itemsXML, "worker heartbeat items")
        heartbeatItems=hwr.getItems()
        # The worker data list
        workerDataList=serverState.getWorkerDataList()
        haveADir=False
        # Order the heartbeat items by destination server
        destList={}
        Nhandled=0
        for item in heartbeatItems:
            dest=item.getServerName()
            item.checkRunDir()
            if item.getHaveRunDir():
                haveADir=True
            if dest in destList:
                destList[dest].append(item)
            else:
                destList[dest]=[item]
            Nhandled+=1
        if haveADir:
            if iteration!="final":
                workerDataList.add(workerDir)
        if iteration=="final":
            workerDataList.remove(workerDir)
        # get my own name to compare
        selfNode=getSelfNode(serverState.conf)
        selfName = selfNode.getId() #ServerConf().getHostName() 
        #selfName = serverState.conf.getHostName()
        # now iterate over the destinations, and send them their heartbeat
        # items.
        # Once we have many workers, this would be a place to pool heartbeat
        # items and send them as one big request.
        faultyItems=[]
        for dest, items in destList.iteritems():
            if dest == selfName:
                ret=serverState.getRunningCmdList().ping(workerID, workerDir,
                                                         iteration, items, True,
                                                         faultyItems)
            else:
                msg=ServerMessage(dest)
                co=StringIO()
                co.write('<heartbeat worker_id="%s" worker_server_id="%s">'%
                         (workerID, selfName))
                for item in items:
                    item.writeXML(co)
                co.write('</heartbeat>')
                resp = msg.heartbeatForwardedRequest(workerID, workerDir,
                                                     selfName, iteration,
                                                     co.getvalue())
                presp=ProcessedResponse(resp)
                if presp.getStatus() != "OK":
                    log.info("Heartbeat response from %s not OK"%dest)
                    retitems=presp.getData()
                    for item in retitems:
                        faultyItems.append(item)
        if version > 1:
            retData = { 'heartbeat-time' : serverState.conf.
                                                getHeartbeatTime(),
                        'random-file': workerDataList.getRnd(workerDir) }
        else:
            retData=serverState.conf.getHeartbeatTime()
        if len(faultyItems)==0:
            response.add('', data=retData)
        else:
            if version > 1:
                retData['faulty']=faultyItems
            # TODO: per-workload error reporting
            response.add('Heatbeat NOT OK', status="ERROR", data=retData)
        log.info("Handled %d heartbeat signal items."%(Nhandled))
            

class SCHeartbeatForwarded(ServerCommand):
    """Handle a worker's heartbeat signal."""
    def __init__(self):
        ServerCommand.__init__(self, "heartbeat-forward")

    def run(self, serverState, request, response):
        workerID=request.getParam('worker_id')
        workerDir=request.getParam('worker_dir')
        iteration=request.getParam('iteration')
        itemsXML=request.getParam('heartbeat_items')
        log.log(cpc.util.log.TRACE, 'items: %s'%itemsXML)
        hwr=cpc.command.heartbeat.HeartbeatItemReader()
        hwr.readString(itemsXML, "worker heartbeat items")
        faultyItems=[]
        Nhandled=len(hwr.getItems())
        ret=serverState.getRunningCmdList().ping(workerID, workerDir, iteration,
                                                 hwr.getItems(), False, 
                                                 faultyItems)
        if len(faultyItems)==0:
            response.add('', data=serverState.conf.getHeartbeatTime())
        else:
            response.add('Heatbeat NOT OK', status="ERROR", data=faultyItems)
        log.info("Handled %d forwarded heartbeat signal items."%(Nhandled))

class SCDeadWorkerFetch(ServerCommand):
    """Attempt to fetch the data from a dead worker."""
    def __init__(self):
        ServerCommand.__init__(self, "dead-worker-fetch")

    def run(self, serverState, request, response):
        # TODO: some verification that the request comes from the server that
        # owns the file
        workerDir=request.getParam('worker_dir')
        runDir=request.getParam('run_dir')
        workerDataList=serverState.getWorkerDataList()
        # check the directory and throw an exception if not allowed
        if workerDataList.checkDirectory(workerDir, [runDir]):
            # first check whether we have any of these files
            if os.path.isdir(runDir):
                tff=tempfile.TemporaryFile()
                tf=tarfile.open(fileobj=tff, mode="w:gz")
                tf.add(runDir, arcname=".", recursive=True)
                tf.close()
                tff.seek(0)
                response.setFile(tff,'application/x-tar')
                request.setFlag('remove', True)
            response.add('Returning data')
            log.info("Fetched data from dead worker")
        else:
            log.info("Did not fetch data from dead worker")

    def finish(self, serverState, request):
        """Now delete the directories associated with that run.
            
           This will only be run if the run() method threw no exception"""
        doRemove=request.getFlag('remove')
        if doRemove is not None and doRemove:
            runDir=request.getParam('run_dir')
            shutil.rmtree(runDir)


