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
import shutil
import tarfile
import tempfile
import threading
import time
import logging
import os

from cpc.network.com.server_connection import ServerConnectionError
from cpc.network.https_connection_pool import ServerConnectionPool, ConnectionPoolEmptyError
from cpc.network.node import Node
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.server.message.direct_message import PersistentServerMessage
from cpc.server.message.server_message import ServerMessage
from cpc.server.message.direct_message import DirectServerMessage
from cpc.util.conf.server_conf import ServerConf
import projectlist
import cpc.server.queue
import heartbeat
import cpc.server.queue
import cpc.util.plugin
import localassets
import remoteassets
from cpc.util.worker_state import WorkerState
from cpc.server.state.session import SessionHandler
from cpc.network.broadcast_message import BroadcastMessage

log=logging.getLogger(__name__)

class ServerState:
    """Maintains the server state. Must provide synchronized access
       because the server is threaded.

       No threads are to be started in the __init__ method, but rather
       in the startExecThreads method. This is because the ServerState
       is initialized before the server forks. The main process would
       take those threads with it to the grave"""

    def __init__(self, conf):
        self.conf=conf
        self.quit=False
        self.quitlock=threading.RLock()
        self.cmdQueue=cpc.server.queue.CmdQueue()
        self.projectlist=projectlist.ProjectList(conf, self.cmdQueue)
        self.taskExecThreads=None
        self.workerDataList=heartbeat.WorkerDataList()
        self.runningCmdList=heartbeat.RunningCmdList(conf, self.cmdQueue,
                                                     self.workerDataList)
        self.localAssets=localassets.LocalAssets()
        self.remoteAssets=remoteassets.RemoteAssets()
        self.sessionHandler=SessionHandler()
        self.workerStates = dict()
        self.stateSaveThread=None
        self.updateThread = None
        self.keepAliveThread = None
        self.reestablishConnectionThread = None

        self.readableSocketLock = threading.Lock()
        self.readableSockets = []


    def startExecThreads(self):
        """Start the exec threads."""
        self.taskExecThreads=cpc.server.queue.TaskExecThreads(self.conf, 1,
                                                self.projectlist.getTaskQueue(),
                                                self.cmdQueue)
        self.stateSaveThread=threading.Thread(target=stateSaveLoop,
                                              args=(self, self.conf, ))
        self.stateSaveThread.daemon=True
        self.stateSaveThread.start()
        log.debug("Starting state save thread.")
        self.runningCmdList.startHeartbeatThread()


    def startConnectServerThread(self):
        self.connectServerThread=threading.Thread(
                                            target=establishConnections,
                                            args=(self,)
                                            ,name="ConnectServerThread")
        self.connectServerThread.daemon=True
        self.connectServerThread.start()

    def startKeepAliveThread(self):
         self.keepAliveThread=threading.Thread(target=sendKeepAlive,
                                                 args=(self.conf, )
                                                ,name="KeepAliveThread")
         self.keepAliveThread.daemon=True
         self.keepAliveThread.start()

    def startReestablishConnectionThread(self):
        self.reestablishConnectionThread=threading.Thread(target=reestablishConnections,
            args=(self, ),name="reestablishConnectionThread")
        self.reestablishConnectionThread.daemon=True
        self.reestablishConnectionThread.start()

    def doQuit(self):
        """set the quit state to true"""
        log.debug('In doQuit. Lock: %s' % self.quitlock)
        with self.quitlock:
            log.debug('Stopping taskExecThreads')
            self.taskExecThreads.stop()
            log.debug('Stopped taskExecThreads')
            self._write()
            self.quit=True
            doProfile = self.conf.getProfiling()
            if doProfile:
                try:
                    import yappi
                    logDir = self.conf.getLogDir()
                    profFile = os.path.join(logDir, 'server_profile.call')
                    yappi.get_func_stats().save(profFile, 'callgrind')
                    profFile = os.path.join(logDir, 'server_profile.txt')
                    profFileF = open(profFile, 'w')
                    yappi.get_func_stats().print_all(profFileF)
                    profFileF.close()
                except:
                    log.exception('Cannot write profiling information')

    def getQuit(self):
        """get the quit state"""
        with self.quitlock:
            ret=self.quit
        return ret

    def getLocalAssets(self):
        """Get the localassets object"""
        return self.localAssets

    def getRemoteAssets(self):
        """Get the remoteassets object"""
        return self.remoteAssets

    def getSessionHandler(self):
        """Get the session handler"""
        return self.sessionHandler

    def getProjectList(self):
        """Get the list of projects as an object."""
        return self.projectlist

    def getCmdQueue(self):
        """Get the run queue as an object."""
        return self.cmdQueue

    def getRunningCmdList(self):
        """Get the running command list."""
        return self.runningCmdList

    def getWorkerDataList(self):
        """Get the worker directory list."""
        return self.workerDataList

    def getCmdLocation(self, cmdID):
        """Get the argument command location."""
        return  self.runningCmdList.getLocation(cmdID)

    def write(self):
        """Write the full server state out to all appropriate files."""
        # we go through all these motions to make sure that nothing prevents
        # the server from starting up again.
        self.taskExecThreads.acquire()
        try:
            self.taskExecThreads.pause()
            self._write()
            self.taskExecThreads.cont()
        finally:
            self.taskExecThreads.release()

    def saveProject(self,project):
        self.taskExecThreads.acquire()
        conf = ServerConf()
        try:
            self.taskExecThreads.pause()
            self._write()
            projectFolder = "%s/%s"%(conf.getRunDir(),project)
            if(os.path.isdir(projectFolder)):
                #tar the project folder but keep the old files also, this is
                # only a backup!!!
                #copy _state.xml to _state.bak.xml
                stateBackupFile = "%s/_state.bak.xml"%projectFolder
                shutil.copyfile("%s/_state.xml"%projectFolder,stateBackupFile)
                tff=tempfile.TemporaryFile()
                tf=tarfile.open(fileobj=tff, mode="w:gz")
                tf.add(projectFolder, arcname=".", recursive=True)
                tf.close()
                del(tf)
                tff.seek(0)
                os.remove(stateBackupFile)
                self.taskExecThreads.cont()
            else:
                self.taskExecThreads.cont()
                raise Exception("Project does not exist")
        finally:
            self.taskExecThreads.release()

        return tff

    def _write(self):
        self.projectlist.writeFullState(self.conf.getProjectFile())
        #self.taskQueue.writeFullState(self.conf.getTaskFile())
        #self.projectlist.writeState(self.conf.getProjectFile())
        self.runningCmdList.writeState()

    def read(self):
        self.projectlist.readState(self, self.conf.getProjectFile())
        self.runningCmdList.readState()

    #rereads the project state for one specific project
    def readProjectState(self,projectName):
        self.projectlist.readProjectState(projectName)


    def getWorkerStates(self):
        '''
        returns: dict
        '''
        return self.workerStates

    def setWorkerState(self,state,workerId,originating):
        # we construct the object first as the key is dependant on the id
        # generated by the constructor. Not thread safe
        workerState = cpc.util.worker_state.WorkerState(originating,state,workerId)
        if workerState.workerId in self.workerStates:
            self.workerStates[workerState.workerId].setState(state)
        else:
            self.workerStates[workerState.workerId] = workerState


    def addReadableSocket(self,socket):
        with self.readableSocketLock:
            self.readableSockets.append(socket)

    def removeReadableSocket(self,socket):
        with self.readableSocketLock:
            self.readableSockets.remove(socket)

def stateSaveLoop(serverState, conf):
    """Function for the state saving thread."""
    while True:
        time.sleep(conf.getStateSaveInterval())
        if not serverState.getQuit():
            log.debug("Saving server state.")
            serverState.write()


def establishConnections(serverState):
    establishInboundConnections(serverState)
    establishOutBoundConnections()
    serverState.startKeepAliveThread()
    serverState.startReestablishConnectionThread()


def establishOutboundConnection(node):
    conf = ServerConf()

    for i in range(0, conf.getNumPersistentConnections()):
        try:
            #This will make a regular call, the connection pool will take
            # care of the rest
            message = PersistentServerMessage(node, conf)
            resp = message.persistOutgoingConnection()
            node.addOutboundConnection()

        except ServerConnectionError as e:
            #The node is not reachable at this moment,
            # no need to throw an exception since we are marking the node
            # as unreachable in ServerConnection
            log.log(cpc.util.log.TRACE, "Exception when establishing "
                                        "outgoing connections: %s " % e)
            break

    if node.isConnectedOutbound():
        log.log(cpc.util.log.TRACE,"Established outgoing "
                                   "connections to server "
                                   "%s"%node.toString())

    else:
        log.log(cpc.util.log.TRACE,"Could not establish outgoing "
                                   "connections to %s"%node.toString())
def establishOutBoundConnections():
    conf = ServerConf()

    log.log(cpc.util.log.TRACE,"Starting to establish outgoing connections")

    for node in conf.getNodes().nodes.itervalues():
        establishOutboundConnection(node)

    log.log(cpc.util.log.TRACE,"Finished establishing outgoing "
                               "connections")


def establishInboundConnection(node, serverState):
    conf=ServerConf()

    for i in range(0, conf.getNumPersistentConnections()):
        try:
            message = PersistentServerMessage(node, conf)
            socket = message.persistIncomingConnection()
            serverState.addReadableSocket(socket)
            node.addInboundConnection()


        except ServerConnectionError as e:
            #The node is not reachable at this moment,
            # no need to throw an exception since we are marking the node
            # as unreachable ins ServerConnectionHandler
            log.log(cpc.util.log.TRACE, "Exception when establishing "
                                        "inbound connections: %s " % e)
            break

    if node.isConnectedInbound():
        log.log(cpc.util.log.TRACE, "Established inbound "
                                "connections to server "
                                "%s" % node.toString())
    else:
        log.log(cpc.util.log.TRACE, "Could not establish inbound "
                                "connections to server "
                                "%s" % node.toString())


def establishInboundConnections(serverState):
    """
    for each node that is not connected
    try to establish an inbound connection
    """
    conf = ServerConf()
    log.log(cpc.util.log.TRACE,"Starting to establish incoming connections")
    for node in conf.getNodes().nodes.itervalues():
        establishInboundConnection(node, serverState)

    log.log(cpc.util.log.TRACE,"Finished establishing incoming "
                                   "connections")


def sendKeepAlive(conf):
    """
        Sends a message for each connected node in order to keep the
        connection alive
    """
    log.log(cpc.util.log.TRACE,"Starting keep alive thread")

    #first get the network topology. by doing this we know that the network
    # topology is fetched and resides in the cache.
    #since we are later on fetching all connections from the connection pool
    # there will be no connection left to do this call thus we must be sure
    # that its already cached.
    ServerToServerMessage.getNetworkTopology()

    while True:
        log.log(cpc.util.log.TRACE,"Starting to send keep alive")
        sentRequests = 0
        for node in conf.getNodes().nodes.itervalues():
            if node.isConnectedOutbound():
                try:
                    connections = ServerConnectionPool().getAllConnections(node)

                    for conn in connections:
                        try:
                            message = DirectServerMessage(node,conf)
                            message.conn = conn
                            message.pingServer(node.getId())
                            log.log(cpc.util.log.TRACE,"keepAlive sent to %s"%node
                            .toString())

                        except ServerConnectionError:
                            log.error("Connection to %s is broken"%node.toString())

                    sentRequests+=1

                except ConnectionPoolEmptyError:
                    #this just mean that no connections are available in the
                    # pool i.e they are used and communicated on thus we do
                    # not need to send keep alive messages on them
                    continue

        keepAliveInterval = conf.getKeepAliveInterval()
        log.log(cpc.util.log.TRACE,"sent keep alive to %s nodes "
                                   "will resend in %s seconds"%(sentRequests,
                                                         keepAliveInterval))
        time.sleep(keepAliveInterval)


def reestablishConnections(serverState):
    '''
    Tries to periodically check for nodes that have gone down and reestablish
     connections to them
    '''
    log.log(cpc.util.log.TRACE,"Starting reestablish connection thread")
    conf = ServerConf()
    while True:
        for node in conf.getNodes().nodes.itervalues():
            if not node.isConnected():
                establishInboundConnection(node,serverState)
                establishOutboundConnection(node)

            if not node.isConnected():
                log.log(cpc.util.log.TRACE,("Tried to reestablish a "
                                            "connection"
                                            " to %s but failed "%node.toString()))


        reconnectInterval = conf.getReconnectInterval()
        time.sleep(reconnectInterval)
