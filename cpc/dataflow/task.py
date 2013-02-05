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
import cpc.util
import active_inst
import transaction


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
            finished=False
            try:
                log.debug("Running function %s"%
                          self.activeInstance.instance.getName())
                # a transaction object that serves as the function run 
                # output object.
                fnOutput=transaction.Transaction(self.project,
                                                 self,
                                                 self.activeInstance.getNet(),
                                                 self.function.getLib())
                self.fnInput.setFunctionRunOutput(fnOutput)
                self.fnInput.cmd=cmd
                #self.fnInput.reset()

                if self.activeInstance.runLock is not None:
                    self.activeInstance.runLock.acquire()
                    locked=True
                # now actually run
                self.ret=self.function.run(self.fnInput)
                # and we're done.
                if self.ret.cancelCmds:
                    # cancel all outstanding commands.
                    canceled=self.activeInstance.cancelTasks(self.seqNr)
                if self.activeInstance.runLock is not None:
                    self.activeInstance.runLock.release()
                    locked=False

                # the commands must be handled here because they're really
                # a property of the task 
                self.fnInput.cmd=None
                if cmd is not None:
                    self.cmds.remove(cmd)
                    # do cpu time accounting.
                    cputime=cmd.getCputime()
                    if cputime > 0:
                        self.activeInstance.addCputime(cputime)

                # handle things that can throw exceptions:
                haveRetcmds=(self.ret.cmds is not None) and len(self.ret.cmds)>0
                   
                if ( (self.ret.hasOutputs() or self.ret.hasSubnetOutputs()) and
                     ( haveRetcmds or len(self.cmds)>0 ) ):
                    raise TaskError(
                       "Task returned both outputs: %s, %s and commands %s,%s"%
                       (str(self.ret.outputs), str(self.ret.subnetOutputs), 
                       str(self.cmds),str(self.ret.cmds)))

                if self.ret.cmds is not None: 
                    for cmd in self.ret.cmds:
                        cmd.setTask(self)
                        self.cmds.append(cmd)
                    finished=False
                else:
                    finished=True

            except cpc.util.CpcError as e:
                if locked:
                    if self.activeInstance.runLock is not None:
                        self.activeInstance.runLock.release()
                self.activeInstance.markError(e.__unicode__())
                return (True, None, canceled)
            except:
                if locked:
                    if self.activeInstance.runLock is not None:
                        self.activeInstance.runLock.release()
                fo=StringIO()
                traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                          sys.exc_info()[2], file=fo)
                errmsg="Run error: %s"%(fo.getvalue())
                self.activeInstance.markError(errmsg)
                return (True, None, canceled)
        return (finished, self.ret.cmds, canceled)

    def handleOutput(self):
        with self.lock:
            self.ret.run()

            self.activeInstance.removeTask(self)

            # everything went OK; we got results
            log.debug("Ran fn %s, got %s"%(self.function.getName(), 
                                           str(self.ret.outputs)) )
            # there is nothing more to execute
            if len(self.cmds) == 0:
                self.fnInput.destroy()

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
        self.fnInput.writeStateXML(outf, indent+1)
        if len(self.cmds)>0:
            outf.write('%s<command-list>\n'%iindstr)
            for cmd in self.cmds:
                cmd.writeXML(outf, indent+2)
            outf.write('%s</command-list>\n'%iindstr)
        outf.write('%s</task>\n'%indstr)

