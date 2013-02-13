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
log=logging.getLogger('cpc.dataflow.active_inst')

import threading
import os
import sys
import copy
import xml.sax.saxutils


import cpc.util
import apperror
import keywords
import function
import active_network
import active_conn
import vtype
import task
import run
import value
import active_value
import function_io
import msg

from cpc.dataflow.value import ValError

class ActiveError(apperror.ApplicationError):
    pass


class ActiveInstanceState:
    """The state of an active instance with its associated string."""
    def __init__(self, str):
        self.str=str
    def __str__(self):
        return self.str

class ActiveInstance(value.ValueBase):
    """An active instance is the instance and the data associated with running
       that instance. An active instance can have a subnetwork that is itself an
       active network. 
       
       It is itself not an instance object because there can be many active 
       realizations of instances (i.e. multiple instances of the same network 
       being active at the same time causes those instances to exist multiple
       times)."""
    
    # The initial state: will not run, until activated.
    held=ActiveInstanceState("held")
    # The active state where it's waiting for inputs to complete
    active=ActiveInstanceState("active")
    # A warning has been emitted. (ActiveInstance.state itself will never
    # actually be set to this value but it is returned with getState when there
    # is a current warning).
    warning=ActiveInstanceState("warning")
    # one of the non-var inputs have changed. Must be set to active to run again
    blocked=ActiveInstanceState("blocked")
    # The active instance encountered a run-time error
    error=ActiveInstanceState("error")

    # a list of them
    states=[ held, active, warning, blocked, error ]

    def __init__(self, inst, project, activeNetwork, dirName):
        """Initialize an active instance, based on an already existing
            instance.
    
            instance = the already existing instance
            project = the project this is a part of
            activeNetwork = the active network this active instance is a part of
            dirName = the directory associated with this a.i. relative to the
                      project directory
            """

        # the source active instance
        self.instance=inst
        self.function=inst.function
        
        if self.function.getState() != function.Function.ok:
            raise ActiveError("Error activating function %s: %s"%
                              (inst.getFullFnName(), 
                               self.function.getStateMsg()))

        # there is at least one instance linked to this active instance
        #self.linkedInstances=[ inst ]
        self.name=inst.name
        self.project=project
        fileList=project.getFileList()
        # counts the nubmer of times a task has been generated
        self.runSeqNr=0 
        # counts the number of CPU seconds that this instance has used
        # on workers. Locked with outputLock
        self.cputime=0.
        # a run lock used for running a task with this active instance if
        # there is a persistent directory.
        if self.function.persistentDirNeeded():
            self.runLock=threading.Lock()
        else:
            self.runLock=None
        self.activeNetwork=activeNetwork # the network we're a part of

        # These are the basic value trees
        self.inputVal=active_value.ActiveValue(None, inst.getInputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(), "in"),
                          fileList=fileList)
        self.outputVal=active_value.ActiveValue(None, inst.getOutputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(), "out"),
                          fileList=fileList)

        self.subnetInputVal=active_value.ActiveValue(None, 
                          inst.getSubnetInputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(),"sub_in"),
                          fileList=fileList)
        self.subnetOutputVal=active_value.ActiveValue(None, 
                          inst.getSubnetOutputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(), "sub_out"),
                          fileList=fileList)

        # And these are the staged versions of the inputs. 
        # These can be updated by their sources without influencing any 
        # running thread. Once all updates are done, the values can be copied 
        # to the non-staged versions with acceptNewValue()
        self.stagedInputVal=active_value.ActiveValue(None, inst.getInputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(), "in"),
                          fileList=fileList)

        self.stagedSubnetInputVal=active_value.ActiveValue(None, 
                          inst.getSubnetInputs(),
                          parent=None, owner=self,
                          selfName="%s:%s"%(self.getCanonicalName(),"sub_in"),
                          fileList=fileList)

        # list of active connection points
        self.inputAcps=[]
        self.outputAcps=[]
        self.subnetInputAcps=[]
        self.subnetOutputAcps=[]

        fullDirName=os.path.join(project.basedir, dirName)
        # make the directory if needed
        if ( (self.function.outputDirNeeded() or 
              self.function.persistentDirNeeded() or
              self.function.hasLog()) and 
             not os.path.exists(fullDirName)):
            os.mkdir(fullDirName)
        self.baseDir=dirName
        # make a persistent scratch dir if needed.
        if ( self.function.persistentDirNeeded() ):
            self.persDir=os.path.join(dirName, "_persistence")
            fullPersDir=os.path.join(project.basedir, self.persDir)
            if not os.path.exists(fullPersDir):
                os.mkdir(fullPersDir)
        else:
            self.persDir=None

        # the message object.
        self.msg=msg.ActiveInstanceMsg(self)

        # an ever-increasing number to prevent outputs from overwriting 
        # each other
        self.outputDirNr=0 
        # whether this instance generates tasks
        self.genTasks=True

        # whether any input value has changed, prompting a task run if 
        # the instance is active.
        self.updated=False

        # There are three locks: lock, inputLock and outputLock. 
        # Because updates involve multiple active instances, maintaining 
        # of locks is not done from within the active instances.
        #
        # inputLock prevents simultaneous changes to self.inputVal, 
        # self.subnetInputVal, any associated listening active connection
        # points, and the task list. Generally, multiple updates to 
        # inputVal/subnetInputVal may be 'in flight', but only one per source
        # (connected output, or global update). These are then handled with
        # handleNewInput(source).
        # Because different sources always affected different inputs, this
        # can be done safely.
        # TODO: we now rely on the python global lock to make sure that
        # stagedInputValues are always readable. We should probably lock 
        # it while doing handleNewInput or updates (we can do this on a
        # very fine-grained level).
        # 
        # It is an rlock because a function that locks it (handleNewInput)
        # could be called when the inputlock is already locked 
        # (see task.handleFnOutput and project.commitChanges).
        self.inputLock=threading.RLock()
        # outputLock protects the output from being changed concurrently, and
        # the list of destinations for each output. Specifically, these are
        # the values in self.outputVal, self.subnetOutputVal, self.seqNr, and 
        # the destination active instances stored in their listening active
        # connection points. 
        self.outputLock=threading.Lock()
        # The default lock protects single-instance non-constant data such 
        # as its state, etc. 
        self.lock=threading.Lock()
        # All network connectivity is locked with a global lock: 
        # project.networkLock
        # NOTE: only when this global lock is locked, is the locking of more
        # than one instance's outputLock or inputLock allowed. In any other
        # case, only one outputLock is allowed, and simultaneously only one
        # inputLock (which must be locked after the outputLock, and unlocked
        # before the outputLock is unlocked). 
        # When the global project.networkLock is locked, multiple outputLocks
        # may be locked, after which, multiple inputLocks may be locked.

        # whether the instance has already been called with all required inputs:
        self.state=ActiveInstance.held
        self.tasks=[]
        # now check whether the instance has a sub-network, and
        # activate that network if needed.
        subnet=inst.getSubnet()
        if subnet is not None:
            self.subnet=active_network.ActiveNetwork(self.project, subnet, 
                                                     activeNetwork.taskQueue, 
                                                     dirName, 
                                                     activeNetwork.\
                                                        getNetworkLock(),
                                                     self)
        # the list of listeners (ActiveConnectionPoints) for inputs
        self.inputListeners=[]
        # The source and sequence number of the last active instance to call
        # for an input update. This makes the update algorithm optimistic:
        # the update algorithm works by calling handleNewInput() at least once
        # for each active instance that has changed item in an output change;
        # all output changes to the same active instance cause a single new
        # task to be emitted. If handleNewInput() is called multiple times for
        # the same update, it is ignored. These values are a quick check for
        # this.
        self.lastUpdateAI=None
        self.lastUpdateSeqNr=-1

    def writeDebug(self, outf):
        outf.write("Active instance %s\n"%self.getCanonicalName())
        outf.write("memory usage: %d bytes\n"%sys.getsizeof(self))

    def getStateStr(self):
        """Get the current state as a string."""
        ret=self.getState()
        return str(ret)

    def getState(self):
        """ Get the current state as an object """
        with self.lock:
            ret = self.state
            if self.state == ActiveInstance.active and self.msg.hasWarning():
                ret=ActiveInstance.warning
        return ret

    def getPropagatedStateStr(self):
        """Get the propagated state associated with this active instance:
           i.e. with any error conditions of sub-instances."""
        errlist=[]
        warnlist=[]
        # find any errors
        self.findErrorStates(errlist, warnlist)
        if len(errlist) > 0:
            return str(ActiveInstance.error)
        elif len(warnlist) > 0:
            return str(ActiveInstance.warning)
        else:
            return self.getStateStr()

    def findErrorStates(self, errlist, warnlist):
        """Find any error & warning states associated with this ai or any
           of its sub-instances. Fills errlist and warnlist active instances
           in these states."""
        with self.lock:
            if self.state == ActiveInstance.error:
                errlist.append( self )
            elif self.state == ActiveInstance.warning:
                warnlist.append( self )
        self.subnet.findErrorStates(errlist, warnlist)

    def getFunction(self):
        """Get the function associated with this a.i."""
        with self.lock:
            return self.function


    def addCputime(self, cputime):
        """add used cpu time to this active instance."""
        with self.outputLock:
            self.cputime+=cputime

    def getCputime(self):
        with self.outputLock:
            return self.cputime

    def setCputime(self, cputime):
        """set used cpu time to this active instance."""
        with self.outputLock:
            self.cputime=cputime

    def getCumulativeCputime(self):
        """Get the total CPU time used by active instance and its 
            internal network."""
        with self.outputLock:
            cputime = self.cputime
        cputime += self.subnet.getCumulativeCputime()
        return cputime

    # functions for readxml:
    def setState(self, state):
        """Set the state without side effects"""
        with self.lock:
            self.state=state

    def setSeqNr(self, seqNr):
        """Set the sequence number"""
        with self.inputLock:
            self.runSeqNr=seqNr
    def getIncreasedSeqNr(self):
        with self.inputLock:
            self.runSeqNr+=1
            ret=self.runSeqNr
        return ret
    def getSeqNr(self):
        with self.inputLock:
            ret=self.runSeqNr
        return ret

    def getLog(self):
        """Get the log object associated with this active instance, or None"""
        return self.msg.getLog()

    def getBasedir(self):
        """Get the active instance's base directory relative to the project 
            dir."""
        return self.baseDir

    def getFullBasedir(self):
        """Get the active instance's absolute base directory."""
        return os.path.join(self.project.basedir, self.baseDir)

    def getTasks(self):
        """ Get the task list """
        return self.tasks
    def getInputs(self):
        """Get the input value object."""
        return self.inputVal
    def getStagedInputs(self):
        """Get the staged input value object."""
        return self.stagedInputVal
    def getOutputs(self):
        """Get the output value object."""
        return self.outputVal
    def getSubnetInputs(self):
        """Get the subnet input value object."""
        return self.subnetInputVal
    def getStagedSubnetInputs(self):
        """Get the staged subnet input value object."""
        return self.stagedSubnetInputVal
    def getSubnetOutputs(self):
        """Get the subnet output value object."""
        return self.subnetOutputVal


    def getInputACP(self, itemList):
        """Get or make an active connection point in the input. 

           It is assumed project.networkLock is locked when using this 
           function."""
        val=self.stagedInputVal.getCreateSubValue(itemList)
        if val is None:
            raise ActiveError("Can't find input %s for active instance %s"%
                              (itemList, self.instance.getName()))
        # get the active connection point or create it if it doesn't exist
        nAcp=val.getListener()
        if nAcp is None:
            nAcp=active_conn.ActiveConnectionPoint(val, self, 
                                                   function_io.inputs)
            #log.debug("making new acp for %s"%val.getFullName())
            self.inputAcps.append(nAcp)
        return nAcp

    def getOutputACP(self, itemList):
        """Get or make an active connection point in the output. 

           It is assumed project.networkLock is locked when using this 
           function."""
        val=self.outputVal.getCreateSubValue(itemList)
        #log.debug("->%s, %s"%(str(type(self.outputVal)), str(type(val))))
        if val is None:
            raise ActiveError("Can't find output %s for active instance %s"%
                              (itemList, self.instance.getName()))
        # get the active connection point or create it if it doesn't exist
        nAcp=val.getListener()
        if nAcp is None:
            nAcp=active_conn.ActiveConnectionPoint(val, self, 
                                                   function_io.outputs)
            #log.debug("making new acp for %s"%val.getFullName())
            self.outputAcps.append(nAcp)
        return nAcp

    def getSubnetInputACP(self, itemList):
        """Get or make an active connection point in the subnet input. 

           It is assumed project.networkLock is locked when using this 
           function."""
        val=self.stagedSubnetInputVal.getCreateSubValue(itemList)
        if val is None:
            raise ActiveError("Can't find subnet input %s for active instance %s"%
                              (itemList, self.instance.getName()))
        # get the active connection point or create it if it doesn't exist
        nAcp=val.getListener()
        if nAcp is None:
            nAcp=active_conn.ActiveConnectionPoint(val, self, 
                                                   function_io.subnetInputs)
            #log.debug("making new acp for %s"%val.getFullName())
            self.subnetInputAcps.append(nAcp)
        return nAcp

    def getSubnetOutputACP(self, itemList):
        """Get or make an active connection point in the subnet output. 

           It is assumed project.networkLock is locked when using this 
           function."""
        val=self.subnetOutputVal.getCreateSubValue(itemList)
        if val is None:
            raise ActiveError("Can't find subnet output %s for active instance %s"%
                              (itemList, self.instance.getName()))
        # get the active connection point or create it if it doesn't exist
        nAcp=val.getListener()
        if nAcp is None:
            nAcp=active_conn.ActiveConnectionPoint(val, self,
                                                   function_io.subnetOutputs)
            #log.debug("making new acp for %s"%val.getFullName())
            self.subnetOutputAcps.append(nAcp)
        return nAcp


    def getName(self):
        """Get the local name of this active instance."""
        return self.name

    def getCanonicalName(self):
        """Get the canonical name for this active instance."""
        parent=self.activeNetwork.getParentInstance()
        if parent is not None:
            name="%s:"%parent.getCanonicalName()
        else:
            name=""
        return name+self.name


    def _getNamedInstanceFromList(self, instancePathList):
        """Part of the activeNetwork.getNamedInstance functionality."""
        if len(instancePathList)>0:
            return self.subnet._getNamedInstanceFromList(instancePathList)
        else:
            return self

    def getNet(self):
        """Get the subnet network, or None if none exists. Is a constant
           property"""
        return self.subnet


    def removeTask(self, task):
        """Remove a task from the list"""
        with self.inputLock:
           self.tasks.remove(task)

    def handleTaskOutput(self, sourceTag, seqNr, output, subnetOutput,
                         warnMsg):
        """Handle the output of a finished task that is generated from 
           this active instance.

           NOTE: assumes that the ai is locked with self.outputLock!!!"""
        #log.debug("Handling task %s output"%self.getCanonicalName())
        # first set things locally 
        changedInstances=set()
        # Round 1: set the new output values
        if output is not None:
            for out in output:
                outItems=vtype.parseItemList(out.name)
                # now get the actual entry in the output value tree
                oval=self.outputVal.getCreateSubValue(outItems,
                                                setCreateSourceTag=sourceTag)
                #log.debug("Handling output for %s"%(oval.getFullName()))
                # remember it
                out.item=oval
                if oval is None:
                    raise ActiveError(
                              "output '%s' not found in instance %s of %s"%
                              (out.name, self.getCanonicalName(), 
                               self.function.getName()))
                #log.debug("Updated value name=%s"%(oval.getFullName()))
                oval.update(out.val, seqNr, sourceTag)
                #log.debug("1 - Marking update for %s"%oval.getFullName())
                oval.markUpdated(True)
                # now stage all the inputs 
                oval.propagate(sourceTag, seqNr)
        if subnetOutput is not None:
            for out in subnetOutput:
                outItems=vtype.parseItemList(out.name)
                oval=self.subnetOutputVal.getCreateSubValue(outItems, 
                                                   setCreateSourceTag=sourceTag)
                #log.debug("Handling output for %s"%(oval.getFullName()))
                # remember it
                out.item=oval
                if oval is None:
                    raise ActiveError(
                        "subnet output '%s' not found in instance %s of %s"%
                        (out.name, self.getCanonicalName(), 
                         self.function.getName()))
                #log.debug("Updated value name=%s"%(oval.getFullName()))
                oval.update(out.val, seqNr, sourceTag)
                #log.debug("2 - Marking update for %s"%oval.getFullName())
                oval.markUpdated(True)
                # now stage all the inputs 
                oval.propagate(sourceTag, seqNr)
        # Round 2: now alert the receiving active instances
        if output is not None:
            for out in output:
                out.item.notifyListeners(sourceTag, seqNr)
        if subnetOutput is not None:
            for out in subnetOutput:
                out.item.notifyListeners(sourceTag, seqNr)
        self.outputVal.setUpdated(False)
        self.subnetOutputVal.setUpdated(False)
        self.msg.setWarning(warnMsg)

    def handleNewInput(self, sourceTag, seqNr, noNewTasks=False):
        """Process new input based on the changing of values.
           
           sourceTag =  the source to look for 

           if source is None, all the active connections that have 
           newSetValue set are updated. The seqNr is then ignored.

           if noNewTasks == true, no new tasks will be generated

           NOTE: If sourceAI is None, this function assumes that there is 
                 some global lock preventing concurrent updates, and 
                 that it is locked. This normally is project.networkLock.
           """
        #log.debug("handleNewInput in %s: %s"%(self.getCanonicalName(), 
        #                                      sourceTag))
        with self.inputLock:
            # first check whether we've already checked this
            #self.updated=False
            if seqNr is not None:
                if self.lastUpdateAI==sourceTag and self.lastUpdateSeqNr==seqNr:
                    # this is an optimistic check: assuming there is only one
                    # thread working on an active instance at a time, it is
                    # quick. If more than one thread is doing this, it gets
                    # less efficient. 
                    return
                self.lastUpdateSource=sourceTag
                self.lastUpdateSeqNr=seqNr
            # now accept new inputs from the specific source
            # this is where the locking comes in: the source should be
            # outputLocked, so that it doesn't overwrite the staged input,
            # and this a.i. should be inputLocked so no two threads do the
            # same at the same time.
            upd1=self.inputVal.acceptNewValue(self.stagedInputVal,sourceTag,
                                              True)
            # also check the subnet input values
            upd2=self.subnetInputVal.acceptNewValue(self.stagedSubnetInputVal, 
                                                    sourceTag, True)
            # now merge it with whether we should already update
            self.updated = self.updated or (upd1 or upd2)
            if noNewTasks:
                # don't set updated flag if it's not needed; noNewTasks
                # is true when reading in current state, and setting updated
                # to True will cause unexpected runs later on.
                self.updated=False
                return
            # only continue if we're active
            if self.state != ActiveInstance.active:
                return
            if self.updated:
                #log.debug("%s: Processing new input for %s of fn %s"%
                #          (self.getCanonicalName(), self.instance.getName(), 
                #           self.function.getName()))
                # and make it run.
                if self._canRun():
                    self._genTask()
            if upd1:
                self.stagedInputVal.setUpdated(False)
                self.inputVal.setUpdated(False)
            if upd2:
                self.stagedSubnetInputVal.setUpdated(False)
                self.subnetInputVal.setUpdated(False)

   
    def resetUpdated(self):
        with self.inputLock:
            self.outputVal.setUpdated(False)
            self.subnetOutputVal.setUpdated(False)
            self.updated=False

    #def resetUpdated(self):
    #    """Reset the updated tag."""
    #    self.updated=False

    def handleNewConnections(self):
        """Process a new output connection. 
           
           NOTE: This function assumes that self.outputLock is locked and
                 that there is some global lock preventing concurrent updates, 
                 and that it is locked. This normally is project.networkLock.
           """
        #log.debug("%s: Processing new connections"%(self.getCanonicalName()))
        # regenerate the output listeners' list of connected active 
        # instances and other listeners. We rely on a global network 
        # update lock to prevent multiple threads from adding connections 
        # concurrently.
        listeners=[]
        self.outputVal.findListeners(listeners)
        #log.debug("%s: %d listeners"%(self.outputVal.getFullName(), 
        #                              len(listeners)))
        for listener in listeners:
            listener.searchDestinations()
        listeners=[]
        self.subnetOutputVal.findListeners(listeners)
        for listener in listeners:
            listener.searchDestinations()
        listeners=[]
        self.stagedInputVal.findListeners(listeners)
        for listener in listeners:
            listener.searchDestinations()
        listeners=[]
        self.stagedSubnetInputVal.findListeners(listeners)
        for listener in listeners:
            listener.searchDestinations()

    def getValueAffectedAIs(self, closestVal, affectedInputAIs):
        """Get the affected input ais for setting a new value."""
        listeners=[]
        closestVal.findListeners(listeners)
        #log.debug("Finding affected inputs for %s"%self.getCanonicalName())
        for listener in listeners:
            #log.debug("   found listener: %s"%(listener.value.getFullName()))
            listener.findConnectedInputAIs(affectedInputAIs)
        affectedInputAIs.add(self)

    def stageNamedInput(self, val, newVal, sourceTag):
        """Stage a new value to the list of new input values. handleNewInput()
           will pick up these inputs if sourceAI == None.

           This function assumes that there is some kind of lock between
           setNamedInput() and handleNewInput() so that no network-wide update 
           from another source can take place in the mean time. 
           Normally, this is project.networkLock
          """
        #log.debug("3 - Marking update for %s"%newVal.getFullName())
        newVal.markUpdated(True)
        val.update(newVal, None, sourceTag=sourceTag)
        val.propagate(sourceTag, None)

    def getNamedType(self, direction, itemList):
        """Get the type of a specific named value."""
        # now change input values
        #log.debug("Processing new value for %s of fn %s"%
        #          (self.instance.getName(), self.function.getName()))
        if direction==function_io.inputs:
            with self.inputLock:
                tp=self.inputVal.getSubType(itemList)
        elif direction==function_io.outputs:
            with self.outputLock:
                tp=self.outputVal.getSubType(itemList)
        elif direction==function_io.subnetInputs:
            with self.inputLock:
                tp=self.subnetInputVal.getSubType(itemList)
        elif direction==function_io.subnetOutputs:
            with self.outputLock:
                tp=self.subnetOutputVal.getSubType(itemList)
        return tp

    def activate(self):
        """Set the state of this active instance to active, if held."""
        log.debug("Activating active instance %s of fn %s"%
                  (self.instance.getName(), self.function.getName()))
        changed=False
        with self.inputLock:
            with self.lock:
                if self.state == ActiveInstance.held:
                    if self.subnet is not None:
                        self.subnet.activateAll()            
                    self.state=ActiveInstance.active
                    changed=True
            if changed:
                for task in self.tasks:
                    task.activateCommands()
                self._reactivate()
        return changed


    def deactivate(self):
        """Set the state of this active instance to held, if active."""
        log.debug("Deactivating active instance %s of fn %s"%
                  (self.instance.getName(), self.function.getName()))
        changed=False
        with self.inputLock:
            with self.lock:
                if self.state == ActiveInstance.active:
                    changed=True
                    if self.subnet is not None:
                        self.subnet.deactivateAll()            
                    self.state=ActiveInstance.held
                    for task in self.tasks:
                        task.deactivateCommands()
        return changed

    def unblock(self):
        """Unblock a task, forcing it to run"""
        changed=False
        with self.inputLock:
            with self.lock:
                 if self.state == ActiveInstance.blocked:
                    # in this case, always run
                    self.state=ActiveInstance.active
                    for task in self.tasks:
                        task.activateCommands()
                    changed=True
            if changed:
                self._reactivate()

    def _reactivate(self):
        """Check for new inputs, and run if there are any."""
        if self.inputVal.hasUpdates() or self.subnetInputVal.hasUpdates():
            self.updated=True
        if self._canRun():
            self._genTask()
          
    def cancelTasks(self, seqNr):
        """Cancel all tasks (and commands) with sequence number before 
           the given seqNr. 
           Returns a list of cancelled commands."""
        with self.lock:
            tsk=copy.copy(self.tasks)
            ret=[]
            for task in tsk:
                if task.seqNr < seqNr:
                    cmds=task.getCommands()
                    if cmds is not None:
                        ret.extend(cmds)
                    task.cancel()
                    self.tasks.remove(task)
            return ret

    def _canRun(self):
        """Whether all inputs are there for the instance to be run.
           Assumes self.inputLock is locked.
           """
        if ( (self.state == ActiveInstance.active) and
             (self.function.genTasks) and
             (self.updated) ):
            ret=self.inputVal.haveAllRequiredValues()
            return ret
        return False

    def _genTask(self):
        """Generate a task.  Assumes self.inputLock is locked ."""
        # prepare inputs
        #log.debug("Generating task for %s (of fn %s)"%
        #          (self.getCanonicalName(), self.function.getName()))
        inputs=value.Value(self.inputVal, self.inputVal.type)
        subnetInputs=value.Value(self.subnetInputVal, self.subnetInputVal.type)
        # reset the status of the inputs, subnetInputs
        self.inputVal.setUpdated(False)
        self.subnetInputVal.setUpdated(False)
        # run dir
        if self.function.outputDirNeeded():
            #log.debug("Creating output dir")
            created=False
            while not created:
                outputDirName=os.path.join(self.baseDir, 
                                           "_run_%04d"%(self.outputDirNr))
                fullOutputDirName=os.path.join(self.project.basedir,
                                               outputDirName)
                self.outputDirNr+=1 
                if not os.path.exists(fullOutputDirName):
                    os.mkdir(fullOutputDirName)
                    created=True
        else:
            #log.debug("Not creating output dir")
            outputDirName=None
        # make a task out of it.
        outputs=None
        if self.function.accessOutputs():
            outputs=value.Value(self.subnetOutputVal, self.outputVal.type)
        subnetOutputs=None
        if self.function.accessSubnetOutputs():
            subnetOutputs=value.Value(self.subnetOutputVal, 
                                      self.subnetOutputVal.type)
        fnInput=run.FunctionRunInput(inputs, subnetInputs,
                                     outputs, subnetOutputs,
                                     outputDirName, self.persDir, 
                                     None, self.function, self, self.project) 
        self.runSeqNr+=1
        tsk=task.Task(self.project, self, self.function, fnInput, 0, 
                      self.runSeqNr)
        self.activeNetwork.taskQueue.put(tsk)
        self.tasks.append(tsk)
        self.updated=False

    def addTask(self, tsk):
        """Append an existing task to the task list. Useful for reading in"""
        self.tasks.append(tsk)

    def markError(self, msg, reportAsNew=True):
        """Mark active instance as being in error state.

           If reportAsNew is True, the error will be reported as new, otherwise
           it is an existing error that is being re-read"""
        with self.lock:
            self.msg.setError(msg)
            self.state=ActiveInstance.error
            for task in self.tasks:
                task.deactivateCommands()
            #print msg
            if reportAsNew:
                log.error(u"Instance %s (fn %s): %s"%(self.instance.getName(),
                                                      self.function.getName(),
                                                      self.msg.getError()))


    def setWarning(self, msg):
        """Set warning message."""
        with self.lock:
            self.msg.setWarning(msg)

    def rerun(self, recursive, clearError, outf=None):
        """Force the rerun of this instance, or clear the error if in error
           state and clearError is True. If recursive is set, 
           do the same for any subinstances. 
           Returns the number of reruns forced"""
        ret=0
        changed=False
        with self.inputLock:
            with self.lock:
                if clearError:
                    if self.state == ActiveInstance.error:
                        self.updated=True
                        self.msg.setError(None)
                        self.msg.setWarning(None)
                        self.state=ActiveInstance.active
                        log.debug("Clearing error on %s"%
                                  self.getCanonicalName())
                        outf.write("Cleared error state on %s\n"%
                                   self.getCanonicalName())
                        changed=True
                        ret+=1
                else:
                    log.debug("Forcing rerun on %s"%self.getCanonicalName())
                    outf.write("Forcing rerun on %s\n"%self.getCanonicalName())
                    self.updated=True
                    changed=True
                    ret+=1
                if recursive and (self.subnet is not None):
                    ret+=self.subnet.rerun(recursive, clearError, outf)
            if changed:
                if self._canRun():
                    self._genTask()
        return ret
 
    def writeXML(self, outf, indent=0):
        """write out values as xml."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        with self.lock:
            outf.write('%s<active '%indstr)
            outf.write(' id=%s state="%s" seqnr="%d" cputime="%g"'%
                       (xml.sax.saxutils.quoteattr(self.name).encode('utf-8'), 
                        str(self.state), self.runSeqNr, self.cputime) )
            if self.state==ActiveInstance.error:
                outf.write(' errmsg=%s'%
                           xml.sax.saxutils.quoteattr(self.msg.getError()).
                           encode('utf-8'))
            if self.msg.hasWarning():
                outf.write(' warnmsg=%s'%
                           xml.sax.saxutils.quoteattr(self.msg.getWarning()).
                           encode('utf-8'))
            outf.write('>\n')
            outf.write('%s<inputs>\n'%(iindstr))
            self.inputVal.writeContentsXML(outf, indent+2)
            outf.write('%s</inputs>\n'%(iindstr))

            outf.write('%s<outputs>\n'%(iindstr))
            self.outputVal.writeContentsXML(outf, indent+2)
            outf.write('%s</outputs>\n'%(iindstr))
            
            outf.write('%s<subnet-inputs>\n'%(iindstr))
            self.subnetInputVal.writeContentsXML(outf, indent+2)
            outf.write('%s</subnet-inputs>\n'%(iindstr))

            outf.write('%s<subnet-outputs>\n'%(iindstr))
            self.subnetOutputVal.writeContentsXML(outf, indent+2)
            outf.write('%s</subnet-outputs>\n'%(iindstr))
            
            if self.subnet is not None:
                self.subnet.writeXML(outf, indent+1)
            if len(self.tasks) > 0:
                outf.write('%s<tasks>\n'%iindstr)
                for tsk in self.tasks:
                    tsk.writeXML(outf, indent+2)
                outf.write('%s</tasks>\n'%iindstr)
            outf.write('%s</active>\n'%indstr)


    ########################################################
    # Member functions from the ValueBase interface:
    ########################################################
    def _getSubVal(self, itemList, staging=False):
        """Helper function"""
        subval=None
        if itemList[0]==keywords.In:
            with self.inputLock:
                if staging:
                    subval=self.stagedInputVal
                else:
                    subval=self.inputVal
        elif itemList[0]==keywords.Out:
            with self.outputLock:
                subval=self.outputVal
        elif itemList[0]==keywords.SubIn:
            with self.inputLock:
                if staging:
                    subval=self.stagedSubnetInputVal
                else:
                    subval=self.subnetInputVal
        elif itemList[0]==keywords.SubOut:
            with self.outputLock:
                subval=self.subnetOutputVal
        elif itemList[0]==keywords.Msg:
            with self.outputLock:
                subval=self.msg
        elif self.subnet is not None:
            subval=self.subnet.tryGetActiveInstance(itemList[0])
        return subval
 
    def getSubValue(self, itemList):
        """Get a specific subvalue through a list of subitems, or return None 
           if not found.
           itemList = the path of the value to return"""
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.getSubValue(itemList[1:])
        return None
        
    def getCreateSubValue(self, itemList, createType=None,
                          setCreateSourceTag=None):
        """Get or create a specific subvalue through a list of subitems, or 
           return None if not found.
           itemList = the path of the value to return/create
           if createType == a type, a subitem will be created with the given 
                            type
           if setCreateSourceTag = not None, the source tag will be set for
                                   any items that are created."""
        if len(itemList)==0:
            return self
        # staging is true because we know we want to be able to create a new
        # value.
        subval=self._getSubVal(itemList, staging=True)
        if subval is not None:
            return subval.getCreateSubValue(itemList[1:], createType,
                                            setCreateSourceTag)
        raise ValError("Cannot create sub value of active instance")

    def getClosestSubValue(self, itemList):
        """Get the closest relevant subvalue through a list of subitems, 
           
           itemList = the path of the value to get the closest value for """
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.getClosestSubValue(itemList[1:])
        return self

    def getSubValueList(self):
        """Return a list of addressable subvalues."""
        ret=[ function_io.inputs, function_io.outputs, 
              function_io.subnetInputs, function_io.subnetOutputs,
              keywords.Msg ]
        if self.activeNetwork is not None:
            ailist=self.subnet.getActiveInstanceList(False, False)
            ret.extend( ailist.keys() )
        return ret

    def getSubValueIterList(self):
        """Return an iterable list of addressable subvalues."""
        return self.getSubValueList()

    def hasSubValue(self, itemList):
        """Check whether a particular subvalue exists"""
        if len(itemList) == 0:
            return True
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.hasSubValue(itemList[1:])
        return False

    def getType(self):
        """Return the type associated with this value"""
        return vtype.instanceType

    def getDesc(self):
        """Return a 'description' of a value: an item that can be passed to 
           the client describing the value."""
        if self.subnet is not None:
            ret=self.subnet.getActiveInstanceList(False, False)
        else:
            ret=dict()
        ret[keywords.In]="inputs"
        ret[keywords.Out]="outputs"
        ret[keywords.SubIn]="subnet_inputs"
        ret[keywords.SubOut]="subnet_outputs"
        ret[keywords.Msg]="msg"
        return ret
    ########################################################



