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
import os.path
import xml.sax.saxutils


import cpc.util
import apperror
import connection
import function
import instance
import network
import active_network
import active_conn
import vtype
import task
import run
import value
import active_value
import function_io

class ActiveError(apperror.ApplicationError):
    pass


class ActiveInstanceState:
    """The state of an active instance with its associated string."""
    def __init__(self, str):
        self.str=str
    def __str__(self):
        return self.str

class ActiveInstance(object):
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
    # one of the non-var inputs have changed. Must be set to active to run again
    blocked=ActiveInstanceState("blocked")
    # one of the non-var inputs have changed. Must be set to active to run again
    error=ActiveInstanceState("error")

    # a list of them
    states=[ held, active, blocked, error ]

    def __init__(self, inst, project, activeNetwork, dirName):
        """Initialize an active instance, based on an already existing
            instance.
    
            instance = the already existing instance
            project = the project this is a part of
            activeNetwork = the active network this active instance is a part of
            dirName = the directory associated with this a.i.
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
        # a run lock used for running a task with this active instance if
        # there is a persistent directory.
        if self.function.persistentDirNeeded():
            self.runLock=threading.Lock()
        else:
            self.runLock=None
        self.activeNetwork=activeNetwork # the network we're a part of

        # These are the basic value trees
        self.inputVal=active_value.ActiveValue(None, inst.getInputs(),
                          selfName="%s:%s"%(self.getCanonicalName(), "in"),
                          fileList=fileList)
        self.outputVal=active_value.ActiveValue(None, inst.getOutputs(),
                          selfName="%s:%s"%(self.getCanonicalName(), "out"),
                          fileList=fileList)

        self.subnetInputVal=active_value.ActiveValue(None, 
                          inst.getSubnetInputs(),
                          selfName="%s:%s"%(self.getCanonicalName(),"sub_in"),
                          fileList=fileList)
        self.subnetOutputVal=active_value.ActiveValue(None, 
                          inst.getSubnetOutputs(),
                          selfName="%s:%s"%(self.getCanonicalName(), "sub_out"),
                          fileList=fileList)

        # And these are the staged versions of the inputs. 
        # These can be updated by their sources without influencing any 
        # running thread. Once all updates are done, the values can be copied 
        # to the non-staged versions with acceptNewValue()
        self.stagedInputVal=active_value.ActiveValue(None, inst.getInputs(),
                          selfName="%s:%s"%(self.getCanonicalName(), "in"),
                          fileList=fileList)

        self.stagedSubnetInputVal=active_value.ActiveValue(None, 
                          inst.getSubnetInputs(),
                          selfName="%s:%s"%(self.getCanonicalName(),"sub_in"),
                          fileList=fileList)

        # list of active connection points
        self.inputAcps=[]
        self.outputAcps=[]
        self.subnetInputAcps=[]
        self.subnetOutputAcps=[]

        # make the directory if needed
        if ( (self.function.outputDirNeeded() or 
              self.function.persistentDirNeeded() or
              self.function.hasLog()) and 
             not os.path.exists(dirName)):
            os.mkdir(dirName)
        self.baseDir=dirName
        # make a persistent scratch dir if needed.
        if ( self.function.persistentDirNeeded() ):
            self.persDir=os.path.join(dirName, "_persistence")
            if not os.path.exists(self.persDir):
                os.mkdir(self.persDir)
        else:
            self.persDir=None

        if self.function.hasLog():
            self.log=ActiveRunLog(os.path.join(dirName, "_log"))
        else:
            self.log=None
        # an ever-increasing number to prevent outputs from overwriting 
        # each other
        self.outputDirNr=0 

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
        self.errmsg=None
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

    def getStateStr(self):
        """Get the current state."""
        with self.lock:
            if self.state != ActiveInstance.error:
                return self.state
            else:
                return "ERROR: %s"%self.errmsg
    def getFunction(self):
        """Get the function associated with this a.i."""
        with self.lock:
            return self.function

    # functions for readxml:
    def setState(self, state):
        """Set the state without updating values"""
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
        return self.log

    def setErrmsg(self, msg):
        """Set the error message."""
        with self.lock:
            self.errmsg=msg

    def getBasedir(self):
        """Get the active instance's base directory."""
        return self.baseDir

    def getInputs(self):
        """Get the input value object."""
        return self.inputVal
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
        val=self.stagedInputVal.getSubValue(itemList, True)
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
        val=self.outputVal.getSubValue(itemList, True)
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
        val=self.stagedSubnetInputVal.getSubValue(itemList, True)
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
        val=self.subnetOutputVal.getSubValue(itemList, True)
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

    def handleTaskOutput(self, task, output, subnetOutput):
        """Handle the output of a finished task that is generated from 
           this active instance.

           NOTE: assumes that the ai is locked with self.outputLock!!!"""
        log.debug("Handling task %s output"%self.getCanonicalName())
        # first set things locally 
        changedInstances=set()
        # Round 1: set the new output values
        if output is not None:
            for out in output:
                outItems=vtype.parseItemList(out.name)
                # now get the actual entry in the output value tree
                oval=self.outputVal.getSubValue(outItems, create=True)
                # remember it
                out.item=oval
                if oval is None:
                    raise ActiveError(
                              "output '%s' not found in instance %s of %s"%
                              (out.name, self.getCanonicalName(), 
                               self.function.getName()))
                #log.debug("Updated value name=%s"%(oval.getFullName()))
                oval.update(out.val, task.seqNr, task)
                #oval.markUpdated(True)
                # now stage all the inputs 
                oval.propagate(task, task.seqNr)
        if subnetOutput is not None:
            for out in subnetOutput:
                outItems=vtype.parseItemList(out.name)
                oval=self.subnetOutputVal.getSubValue(outItems, create=True)
                # remember it
                out.item=oval
                if oval is None:
                    raise ActiveError(
                        "subnet output '%s' not found in instance %s of %s"%
                        (out.name, self.getCanonicalName(), 
                         self.function.getName()))
                #log.debug("Updated value name=%s"%(oval.getFullName()))
                oval.update(out.val, task.seqNr, task)
                #oval.markUpdated(True)
                # now stage all the inputs 
                oval.propagate(task, task.seqNr)
        # Round 2: now alert the receiving active instances
        if output is not None:
            for out in output:
                out.item.notifyListeners(task, task.seqNr)
        if subnetOutput is not None:
            for out in subnetOutput:
                out.item.notifyListeners(task, task.seqNr)
        self.outputVal.setUpdated(False)
        self.subnetOutputVal.setUpdated(False)

    def handleNewInput(self, sourceTag, seqNr):
        """Process new input based on the changing of values.
           
           sourceTag =  the source to look for 

           if source is None, all the active connections that have 
           newSetValue set are updated. The seqNr is then ignored.

           NOTE: If sourceAI is None, this function assumes that there is 
                 some global lock preventing concurrent updates, and 
                 that it is locked. This normally is project.networkLock.
           """
        log.debug("handleNewInput on  %s"%self.getCanonicalName())
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
            upd1=self.inputVal.acceptNewValue(self.stagedInputVal,sourceTag)
            # also check the subnet input values
            upd2=self.subnetInputVal.acceptNewValue(self.stagedSubnetInputVal, 
                                                    sourceTag)
            if upd1 or upd2:
                log.debug("%s: Processing new input for %s of fn %s"%
                          (self.getCanonicalName(), self.instance.getName(), 
                           self.function.getName()))
                # only continue if we're active
                if self.state != ActiveInstance.active:
                    return
                # and make it run.
                if self._canRun():
                    self._genTask()

    def handleNewOutputConnections(self):
        """Process a new output connection. Must be called BEFORE the 
           corresponding handleNewInputConnections for a network update
           
           NOTE: This function assumes that self.outputLock is locked and
                 that there is some global lock preventing concurrent updates, 
                 and that it is locked. This normally is project.networkLock.
           """
        log.debug("%s: Processing new connections"%(self.getCanonicalName()))
        # regenerate the output listeners' list of connected active 
        # instances and other listeners. We rely on a global network 
        # update lock to prevent multiple threads from adding connections 
        # concurrently.
        listeners=[]
        self.outputVal.findListeners(listeners)
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

    def findNamedInput(self, direction, itemList):
        """Find the *staging* value object corresponding to the named item.
           direction = the input/output/subnetinput/subnetoutput direction
           itemList = a path gettable by value.getSubValue

           Assumes a locked self.inputLock
           """
        log.debug("%s: Finding value for %s of fn %s"%
                  (self.getCanonicalName(), self.instance.getName(), 
                   self.function.getName()))
        if direction==function_io.inputs:
            topval=self.stagedInputVal
        elif direction==function_io.subnetInputs:
            topval=self.stagedSubnetInputVal
        else:
            raise ActiveError("Trying to set output value %s"%
                              str(direction.name))
        val=topval.getSubValue(itemList, create=True)
        return val

    def getNamedInputAffectedAIs(self, val, newVal, affectedInputAIs):
        """Get the affected input ais for setting a new value."""
        listeners=[]
        val.findListeners(listeners)
        log.debug("Finding affected inputs for %s"%self.getCanonicalName())
        for listener in listeners:
            log.debug("   found listener: %s"%(listener.value.getFullName()))
            listener.findConnectedInputAIs(affectedInputAIs)
            #destais=listener.getDestinationAIs()
        for ai in affectedInputAIs:
            log.debug("   add affected input: %s"%(ai.getCanonicalName()))
            #affectedInputAIs.update(destais)
        affectedInputAIs.add(self)

    def stageNamedInput(self, val, newVal, sourceTag):
        """Stage a new value to the list of new input values. handleNewInput()
           will pick up these inputs if sourceAI == None.

           This function assumes that there is some kind of lock between
           setNamedInput() and handleNewInput() so that no network-wide update 
           from another source can take place in the mean time. 
           Normally, this is project.networkLock
          """
        val.update(newVal, val.seqNr, sourceTag)
        val.propagate(sourceTag, None)
               

    def getNamedValue(self, direction, itemList):
        """Get a specific named value ."""
        # now change input values
        log.debug("Processing new value for %s of fn %s"%
                  (self.instance.getName(), self.function.getName()))
        if direction==function_io.inputs:
            with self.inputLock:
                val=self.inputVal.getSubValue(itemList)
        elif direction==function_io.outputs:
            with self.outputLock:
                val=self.outputVal.getSubValue(itemList)
        elif direction==function_io.subnetInputs:
            with self.inputLock:
                val=self.subnetInputVal.getSubValue(itemList)
        elif direction==function_io.subnetOutputs:
            with self.outputLock:
                val=self.subnetOutputVal.getSubValue(itemList)
        return val

    def getNamedType(self, direction, itemList):
        """Get the type of a specific named value."""
        # now change input values
        log.debug("Processing new value for %s of fn %s"%
                  (self.instance.getName(), self.function.getName()))
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
                  (self.instance.getName(),
                   self.function.getName()))
        changed=False
        with self.inputLock:
            with self.lock:
                if self.state == ActiveInstance.held:
                    if self.subnet is not None:
                        self.subnet.activateAll()            
                    self.state=ActiveInstance.active
                    changed=True
            if changed:
                if self._canRun():
                    self._genTask()

    def unblock(self):
        """Unblock a task, forcing it to run"""
        changed=False
        with self.inputLock:
            with self.lock:
                 if self.state == ActiveInstance.blocked:
                    # in this case, always run
                    self.state=ActiveInstance.active
                    changed=True
            if changed:
                if self._canRun():
                    self._genTask()


    def _canRun(self):
        """Whether all inputs are there for the instance to be run.
           Assumes self.inputLock is locked.
           """
        if ( (self.state == ActiveInstance.active) and
             (self.function.genTasks) ):
            ret=self.inputVal.haveAllRequiredValues()
            #log.debug("Checking whether instance %s can run: %s"%
            #          (self.getCanonicalName(), str(ret)))
            return ret
        return False

    def _genTask(self):
        """Generate a task.  Assumes self.inputLock is locked ."""
        # prepare inputs
        log.debug("Generating task for %s (of fn %s)"%
                  (self.getCanonicalName(), self.function.getName()))
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
                self.outputDirNr+=1 
                if not os.path.exists(outputDirName):
                    os.mkdir(outputDirName)
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

    def addTask(self, tsk):
        """Append an existing task to the task list. Useful for reading in"""
        self.tasks.append(tsk)

    def markError(self, msg):
        """Mark active instance as being in error state."""
        with self.lock:
            self.errmsg=msg
            self.state=ActiveInstance.error
            print msg
            log.error("Instance %s (fn %s): %s"%(self.instance.getName(), 
                                                 self.function.getName(), msg))

    def writeXML(self, outf, indent=0):
        """write out values as xml."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        with self.lock:
            if self.state==ActiveInstance.error:
                strn=str(self.errmsg)
                msg='errmsg=%s'%str(xml.sax.saxutils.quoteattr(strn))
            else:
                msg=""
            outf.write('%s<active id="%s" state="%s" %s seqnr="%d">\n'%
                       (indstr, self.name, str(self.state), msg,
                        self.runSeqNr))
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
        

class ActiveRunLog(object):
    """Class holding a run log for an active instance requiring one."""
    def __init__(self, filename):
        """Initialize with an absolute path name"""
        self.filename=filename
        self.lock=threading.Lock()
        self.outf=None
    def open(self):
        """Open the run log and return a file object, locking the log."""
        self.lock.acquire()
        self.outf=open(self.filename, 'a')
        return self.outf
    def close(self):
        """Close the file opened with open()"""
        self.outf.close()
        self.outf=None
        self.lock.release()
    def getFilename(self):
        """Get the file name"""
        return self.filename


