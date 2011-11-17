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



import threading
import time

import projectlist
import cpc.server.queue
import cmdlist
import logging
import cpc.server.heartbeat
import cpc.server.queue
import cpc.util.plugin
import localassets
import remoteassets
import cpc.util.worker_state

log=logging.getLogger('cpc.server.command')

class ServerState:
    """Maintains the server state. Must provide synchronized access 
       because the server is threaded."""

    def __init__(self, conf):
        self.conf=conf
        self.quit=False
        self.quitlock=threading.Lock()
        self.cmdQueue=cpc.server.queue.CmdQueue()
        self.projectlist=projectlist.ProjectList(conf, self.cmdQueue)
        self.taskExecThreads=None
        self.runningCmdList=cmdlist.RunningCmdList()
        self.heartbeatList=cpc.server.heartbeat.HeartbeatList()
        self.localAssets=localassets.LocalAssets()
        self.remoteAssets=remoteassets.RemoteAssets()
        self.workerStates = dict()
        log.debug("Starting state save thread.")
        self.stateSaveThread=threading.Thread(target=stateSaveLoop,
                                              args=(self, conf, ))
        self.stateSaveThread.daemon=True
        self.stateSaveThread.start()

    def startExecThreads(self):
        """Start the exec threads."""
        self.taskExecThreads=cpc.server.queue.TaskExecThreads(
                                                1,
                                                self.projectlist.getTaskQueue(),
                                                self.cmdQueue)

    def doQuit(self):
        """set the quit state to true"""
        with self.quitlock:
            self.taskExecThreads.stop()
            self._write()
            self.quit=True

    def getQuit(self):
        """Set the quit state"""
        with self.quitlock:
            ret=self.quit
        return ret
    
    def getLocalAssets(self):
        """Get the localassets object"""
        return self.localAssets 
    
    def getRemoteAssets(self):
        """Get the remoteassets object"""
        return self.remoteAssets

    def getProjectList(self):
        """Get the list of projects as an object."""        
        return self.projectlist

    def getCmdQueue(self):        
        """Get the run queue as an object."""
        return self.cmdQueue    

    def getRunningCmdList(self):
        """Get the running command list."""
        return self.runningCmdList
    
    def getCmdLocation(self, cmdID):
        """Get the argument command location."""
        return  self.runningCmdList.getLocation(cmdID)

    def getHeartbeatList(self):
        """Get the heartbeat list."""
        return self.heartbeatList

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


    def _write(self):
        self.projectlist.writeFullState(self.conf.getProjectFile())
        #self.taskQueue.writeFullState(self.conf.getTaskFile())
        #self.projectlist.writeState(self.conf.getProjectFile())
        self.heartbeatList.writeState()

    def read(self):
        self.projectlist.readState(self, self.conf.getProjectFile())
        self.heartbeatList.readState()

    def getWorkerStates(self):
        return self.workerStates
    
    def setWorkerState(self,state,workerData,originating):
        workerState = cpc.util.worker_state.WorkerState(originating,state)
        if workerState.id in self.workerStates:
            self.workerStates[workerState.id].state = state
        else:
            self.workerStates[workerState.id] = workerState                        
        
def stateSaveLoop(serverState, conf):
    """Function for the state saving thread."""
    while True:
        time.sleep(conf.getStateSaveInterval())
        if not serverState.getQuit():
            log.debug("Saving server state.")
            serverState.write()

