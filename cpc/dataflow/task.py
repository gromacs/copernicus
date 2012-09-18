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



import logging
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import Queue
import traceback
import sys
import threading


import cpc.util
from cpc.util.conf.server_conf import ServerConf
import apperror
import function
import instance
import cpc.server.command
import cpc.util
import run
import connection
import value
import active_inst


log=logging.getLogger('cpc.dataflow.task')

class TaskError(apperror.ApplicationError):
    pass

class TaskNoNetError(TaskError):
    def __init__(self, name):
        self.str=("Trying to add new instance in instance %s without subnet"%
                  name)

class TaskQueue(object):
    """A task queue holds the a list of tasks to execute in order."""
    def __init__(self, cmdQueue):
        log.debug("Creating new task queue.")
        self.queue=Queue.Queue(maxsize=ServerConf().getTaskQueueSize())
        self.cmdQueue=cmdQueue
    
    def put(self, task):
        """Put a task in the queue."""
        self.queue.put(task)

    def putNone(self):
        """Put a none into the queue to make sure threads are reading it."""
        self.queue.put(None)
    
    def get(self):
        return self.queue.get()

    def empty(self):
        return self.queue.empty()


class Task(object):
    """A task is a queueable and runnable function with inputs."""
    def __init__(self, project, activeInstance, function, fnInput, 
                 priority, seqNr):
        """Create a task based on a function 
       
           project = the project of this task 
           activeInstance = the activeInstance this task belongs to
           function = the function object
           fnInput = the FunctionRunInput object
           priority = the task's priority.
           seqNr = the task's sequence number
           """
           
        #log.debug("creating task")    
        log.debug("Making task of instance %s"%
                  (activeInstance.getCanonicalName()) )
        self.activeInstance=activeInstance
        self.function=function
        self.priority=priority
        self.id=id(self)
        self.project = project
        # we want only one copy of a task running at a time
        self.lock=threading.Lock() 
        self.seqNr=seqNr
        self.fnInput=fnInput
        self.cmds=[]
        self.cputime=0
        self.canceled=False

    def setFnInput(self, fnInput):
        """Replace the fnInput object. Only for readxml"""
        self.fnInput=fnInput
    def addCommands(self, cmds, deactivate):
        """Add commands. Only for readxml"""
        for cmd in cmds:
            cmd.setTask(self)
            if deactivate:
                cmd.deactivate()
        self.cmds.extend(cmds)

    def getFnInput(self):
        """Get the fnInput object."""
        return self.fnInput

    def getCommands(self):
        return self.cmds

    def activateCommands(self):
        """Activate all the commands in this task."""
        for cmd in self.cmds:
            cmd.activate()
    def deactivateCommands(self):
        """Deactivate all the commands in this task."""
        for cmd in self.cmds:
            cmd.deactivate()

    def cancel(self):
        with self.lock:
            self.canceled=True

    def isActive(self):
        """Return whether the underlying active instance is active."""
        return self.activeInstance.state == active_inst.active

    def _handleFnOutput(self, out):
        # handle addInstances
        addedInstances=[]
        # new instances are always unconnected and inactive at first, so we
        # don't need to lock them, etc. 
        if out.newInstances is not None:
            activeNet=self.activeInstance.getNet()
            if activeNet is None:
                raise TaskNetError(self.activeInstance.instance.getName())
            imports=self.project.getImportList()
            for newInstance in out.newInstances:
                #log.debug("Making new instance %s (%s)"%
                #          (newInstance.name, 
                #           newInstance.functionName))
                fn=imports.getFunctionByFullName(newInstance.functionName,
                                                 self.function.getLib())
                inst=instance.Instance(newInstance.name, fn, 
                                       fn.getFullName())
                addedInstances.append(activeNet.addInstance(inst))
        # we handle new network connnections and new output atomically: 
        # if the new network connection references newly outputted data,
        # that is all the instance sees.
        try:
            affectedInputAIs=None
            affectedOutputAIs=None
            outputsLocked=False
            # whether the task's ai is already locked
            selfLocked=False
            if out.newConnections is not None:
                #log.debug("Handling new connections for task of %s"%
                #          self.activeInstance.getCanonicalName())
                # we have new connections so we need to lock the global lock
                self.project.networkLock.acquire()
                imports=self.project.getImportList()
                activeNet=self.activeInstance.getNet()
                if activeNet is None:
                    raise TaskNetError(self.activeInstance.instance.getName())
                # and allocate emtpy sets
                affectedInputAIs=set()
                affectedOutputAIs=set()
                # Make the connections
                conns=[]
                for newConnection in out.newConnections:
                    if newConnection.srcStr is not None:
                        #log.debug("Making new connection %s -> %s)"%
                        #          (newConnection.srcStr, newConnection.dstStr))
                        conn=connection.makeConnectionFromDesc(activeNet,
                                                           newConnection.srcStr,
                                                           newConnection.dstStr)
                    else:
                        #log.debug("Making assignment %s -> %s)"%
                        #          (newConnection.val.value, 
                        #           newConnection.dstStr))
                        conn=connection.makeInitialValueFromDesc(activeNet,
                                                           newConnection.dstStr,
                                                           newConnection.val)
                    conns.append(conn)
                    activeNet.findConnectionSrcDest(conn, affectedInputAIs,
                                                    affectedOutputAIs)
                # Now lock all affected outputs
                # An exception during this loop should be impossible:
                for ai in affectedOutputAIs:
                    ai.outputLock.acquire()
                    if ai == self.activeInstance: 
                        selfLocked=True
                outputsLocked=True
                # now handle the connection updates
                for conn in conns:
                    activeNet.addConnection(conn, self)
            if not selfLocked:
                self.activeInstance.outputLock.acquire()
                selfLocked=True
            #log.debug("Handling output for task of %s"%
            #          self.activeInstance.getCanonicalName())
            # we can do this safely because activeInstance.inputLock is an rlock
            self.activeInstance.handleTaskOutput(self, out.outputs, 
                                                 out.subnetOutputs)
            #log.debug("Handling new inputs for task of %s"%
            #          self.activeInstance.getCanonicalName())
            # now handle the input generated by making new connections
            if affectedInputAIs is not None:
                for ai in affectedInputAIs:
                    ai.handleNewInput(self, None)
        finally:
            # unlock everything in the right order
            # we still need to unlock self
            if selfLocked:
                self.activeInstance.outputLock.release()
            if (affectedOutputAIs is not None) and outputsLocked:
                for ai in affectedOutputAIs:
                    if ai != self.activeInstance:
                        ai.outputLock.release()
            if out.newConnections is not None:
                # we release the global lock
                self.project.networkLock.release()
        # now activate any new added instances.
        for inst in addedInstances:
            inst.activate()

    def run(self, cmd=None):
        """Run the task's underlying function with the required inputs,
           possibly in response to a finished command (given as parameter cmd) 
           and return a list of commands to queue. If a command is queued,
           the task should continue existining until its corresponding 
           run() call is called. """
        with self.lock:
            if self.canceled:
                return (None, None)
            locked=False
            canceled=None
            try:
                log.debug("Running function %s"%
                          self.activeInstance.instance.getName())
                self.fnInput.cmd=cmd
                self.fnInput.reset()

                if self.activeInstance.runLock is not None:
                    self.activeInstance.runLock.acquire()
                locked=True
                # now actually run
                ret=self.function.run(self.fnInput)
                # and we're done.
                if ret.cancelCmds:
                    # cancel all outstanding commands.
                    canceled=self.activeInstance.cancelTasks(self.seqNr)
                if self.activeInstance.runLock is not None:
                    self.activeInstance.runLock.release()
                locked=False

                self.fnInput.cmd=None
                if cmd is not None:
                    self.cmds.remove(cmd)
                    # do cpu time accounting.
                    cputime=cmd.getCputime()
                    if cputime > 0:
                        self.activeInstance.addCputime(cputime)

                # handle things that can throw exceptions:
                haveRetcmds=(ret.cmds is not None) and len(ret.cmds)>0
                   
                if ( (ret.hasOutputs() or ret.hasSubnetOutputs()) and
                     ( haveRetcmds or len(self.cmds)>0 ) ):
                    raise TaskError(
                       "Task returned both outputs: %s, %s and commands %s,%s"%
                       (str(ret.outputs), str(ret.subnetOutputs), 
                       str(self.cmds),str(ret.cmds)))

                self._handleFnOutput(ret)

                #if ret.cancelCmds:
                #   log.debug("Canceling %d existing commands"%(len(self.cmds)))
                #    canceled=self.cmds
                #    for cmd in canceled:
                #        cmd.setTask(None)
                #    self.cmds=[]

                if ret.cmds is not None: 
                    for cmd in ret.cmds:
                        cmd.setTask(self)
                        self.cmds.append(cmd)
                else:
                    # the task is done.
                    self.activeInstance.removeTask(self)

                    

                # everything went OK; we got results
                log.debug("Ran fn %s, got %s"%(self.function.getName(), 
                                                   str(ret.outputs)) )
                # there is nothing more to execute
                if len(self.cmds) == 0:
                    self.fnInput.destroy()
            except cpc.util.CpcError as e:
                if locked:
                    if self.activeInstance.runLock is not None:
                        self.activeInstance.runLock.release()
                self.activeInstance.markError(e.__unicode__())
                return (None, canceled)
            except:
                if locked:
                    if self.activeInstance.runLock is not None:
                        self.activeInstance.runLock.release()
                fo=StringIO()
                traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                          sys.exc_info()[2], file=fo)
                errmsg="Run error: %s"%(fo.getvalue())
                self.activeInstance.markError(errmsg)
                return (None, canceled)
            return (ret.cmds, canceled)

    def getID(self):
        return "%s.%s"%(self.activeInstance.getCanonicalName(), self.seqNr)

    def getFunctionName(self):
        return self.function.getName()
    
    def getProject(self):
        return self.project

    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outf.write('%s<task project="%s" priority="%d" active_instance="%s" seqnr="%d">\n'%
                   (indstr,
                    self.project.getName(),
                    self.priority, 
                    self.activeInstance.getCanonicalName(),
                    self.seqNr))
        self.fnInput.writeXML(outf, indent+1)
        if len(self.cmds)>0:
            outf.write('%s<command-list>\n'%iindstr)
            for cmd in self.cmds:
                cmd.writeXML(outf, indent+2)
            outf.write('%s</command-list>\n'%iindstr)
        outf.write('%s</task>\n'%indstr)

