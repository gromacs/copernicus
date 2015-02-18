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

from cpc.network.com.client_response import ProcessedResponse
from cpc.util import json_serializer
from cpc.network.node import Nodes
from cpc.server.message.server_message import ServerMessage
from cpc.server.tracking.tracker import Tracker
from server_command import ServerCommand
from cpc.network.node import Node
from cpc.util.worker_state import WorkerStatus

import cpc.command.heartbeat



log=logging.getLogger(__name__)


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
        originatingServer=None
        heartbeatInterval=None
        try:
            # check whether there is an originating server. If not, we're it
            if self.forwarded:
                if 'originating-server-id' in request.headers:
                    originatingServer = request.headers['originating-server-id']
                # check the expected heartbeat time.
                log.debug("Forwarded message")
                if request.hasParam('heartbeat-interval'):
                    heartbeatInterval = int(request.getParam('heartbeat-interval'))
                    log.debug("Forwarded heartbeat interval is %d"%
                            heartbeatInterval)
        except NameError:
            # self.forwarded does not exist. Treat it as if self.forwarded == False
            pass

        if originatingServer is None:
            # If the originating server property has not been set,  the
            # request hasn't been forwarded, therefore we are the originating
            # server
            selfNode=Node.getSelfNode(conf)
            originatingServer = selfNode.getId()
            # we only store worker state in the server the worker connects to
            serverState.setWorkerState(WorkerStatus.WORKER_STATUS_CONNECTED,workerID,
                                       request.headers['originating-client'])
        if heartbeatInterval is None:
            heartbeatInterval = conf.getHeartbeatTime()
        log.debug("worker identified %s"%request.headers['originating-client'] )

        if len(cmds) > 0:
            # first add them to the running list so they never get lost
            runningCmdList=serverState.getRunningCmdList()
            runningCmdList.add(cmds, originatingServer, heartbeatInterval)
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
                if not os.path.exists(cmddir):
                    log.debug("cmddir %s did not exist. Created directory."%cmd.id)
                    os.mkdir(cmddir)
                arcdir="%s"%(cmd.id)
                log.debug("cmddir=%s"%cmddir)
                outf=open(os.path.join(cmddir, "command.xml"), "w")
                cmd.writeWorkerXML(outf)
                outf.close()
                tf.add(cmddir, arcname=arcdir, recursive=True)
                # set the state of the command.
            tf.close()
            del(tf)
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

            thisNode = Node.getSelfNode(conf)
            thisNode.nodes = conf.getNodes()
            topology.addNode(thisNode)

            hasJob =False # temporary flag that should be removed
            for node in nodes:
                if topology.exists(node.getId()) == False:
                    clnt=ServerMessage(node.getId())

                    clientResponse=clnt.workerReadyForwardedRequest(workerID,
                                        workerData,
                                        topology,
                                        originatingServer,
                                        heartbeatInterval,
                                        request.headers['originating-client'])

                    if clientResponse.getType() == 'application/x-tar':

                        log.log(cpc.util.log.TRACE,
                                'got work from %s'%
                                (clientResponse.headers[
                                     'originating-server-id']))
                        hasJob=True
                        # we need to rewrap the message

                        #TODO stupid intermediary step because the mmap form
                        # clientresponse is prematurely closed
                        tmp = tempfile.TemporaryFile('w+b')

                        message = clientResponse.getRawData()

                        tmp.write(message.read(len(message)))
                        tmp.seek(0)

                        #for key in clientResponse.headers:
                        #    print "%s:%s"%(key,clientResponse.headers[key])

                        response.setFile(tmp,'application/x-tar')
                        response.headers['originating-server-id']=\
                                  clientResponse.headers[
                                      'originating-server-id']
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

class CommandFinishError(cpc.util.CpcError):
    pass

class CommandFinishedBase(ServerCommand):
    """Base class for command finished requests"""
    def __init__(self, name, forwarded):
        """name is the message name, forwarded is whether the request is
           forwarded."""
        ServerCommand.__init__(self, name)
        self.forwarded=forwarded

    def runLocal(self, serverState, request, response):
        #self.lock = threading.Lock()
        cmdID=request.getParam('cmd_id')

        selfNode=Node.getSelfNode(serverState.conf)
        selfName = selfNode.getId()

        # get the source server if set. If not set, it means that this server
        # is the worker server.
        if request.hasParam('worker_server'):
            workerServer=request.getParam('worker_server')
        else:
            workerServer=selfName

        # get the destination server if set
        if request.hasParam('project_server'):
            projServer=request.getParam('project_server')
        else:
            # for backward compatibility, we assume that we are the project
            # server if it's forwarded. If not, there's something wrong.
            projServer=selfName
            if not self.forwarded:
                raise CommandFinishError(
                           "no project server set in command finished request.")

        returncode=None
        if request.hasParam('return_code'):
            returncode=int(request.getParam('return_code'))
        cputime=0
        if request.hasParam('used_cpu_time'):
            cputime=float(request.getParam('used_cpu_time'))

        runfile=None
        if request.haveFile('run_data'):
            runfile=request.getFile('run_data')
        elif request.haveFile('rundata'):
            # backward compatibility
            runfile=request.getFile('rundata')

        if projServer != selfName:
            # forward the request using remote assets. Note that the workers
            # usually don't take this path anyway and forward directly to the
            # project server. This might change in the futuure.
            # TODO: some sort of verification  to check whether this was in fact
            #       the client that we sent the command to
            serverState.getLocalAssets().addCmdOutputAsset(cmdID,
                                                           projServer, runfile)
            #forward CommandFinished-signal to project server
            msg=ServerMessage(projServer)
            ret = msg.commandFinishedForwardedRequest(cmdID,
                                                      workerServer,
                                                      projServer,
                                                      returncode,
                                                      cputime,
                                                      runfile is not None)
        else:
            # handle the input locally.
            # get the remote asset if it exists
            if ( workerServer is not None and
                 runfile is None and
                 ( request.hasParam('run_data') and
                   int(request.getParam('run_data'))!=0 ) ):
                #remote asset tracking
                log.info("Pulling asset from %s"%workerServer)
                serverState.getRemoteAssets().addAsset(cmdID, workerServer)
                #for now, get the command data output immediately
                rundata = Tracker.getCommandOutputData(cmdID, workerServer)
                if rundata != None:
                    runfile = rundata.getRawData()
            # now handle the finished command.
            runningCmdList=serverState.getRunningCmdList()
            runningCmdList.handleFinished(cmdID, returncode, cputime, runfile)

class SCCommandFinishedForward(CommandFinishedBase):
    """Handle forwarded finished command. The command output is not sent in
       this message"""
    def __init__(self):
        CommandFinishedBase.__init__(self, "command-finished-forward", True)

    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        self.runLocal(serverState, request, response)
        log.info("finished forward command %s"%cmdID)

class SCCommandFinished(CommandFinishedBase):
    """Get finished command data."""
    def __init__(self):
        CommandFinishedBase.__init__(self, "command-finished", False)

    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        self.runLocal(serverState, request, response)
        log.info("Finished command %s"%cmdID)

class SCCommandFailed(CommandFinishedBase):
    """Get notified about a failed run."""
    def __init__(self):
        CommandFinishedBase.__init__(self, "command-failed", False)

    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        self.runLocal(serverState, request, response)
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
        selfNode= Node.getSelfNode(serverState.conf)
        selfName = selfNode.getId()

        #updating the status at every hearbeat. This is how we knwo that the worker
        # is still talking to the server
        serverState.setWorkerState(WorkerStatus.WORKER_STATUS_CONNECTED,workerID,
                                   request.headers['originating-client'])
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
                del(tf)
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


