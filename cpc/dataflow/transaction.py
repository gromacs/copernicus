# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Magnus Lundborg,
# Erik Lindahl, and others.
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
import threading
import traceback
import sys

import apperror
#import connection
import value
import run
#import instance
#import active_value
import vtype


log=logging.getLogger(__name__)

class SetError(apperror.ApplicationError):
    pass

class SetValue(object):
    def __init__(self, project, itemName,
                 #activeInstance, direction, ioItemList,
                 literal, sourceType, printName):
        """Object to hold an set value for an arbitrary active instance."""
        self.itemName=itemName
        self.project=project
        #instanceName,direction,ioItemList=connection.splitIOName(itemName,
        #                                                         None)
        #instance=self.activeNetwork.getNamedActiveInstance(instanceName)
        self.itemList=vtype.parseItemList(itemName)
        item=project.getClosestSubValue(self.itemList)
        log.debug('TRANSACTION: %s' % item)
        if not isinstance(item, value.Value):
            raise SetError("Value of '%s' cannot be set"%itemName)
        #self.activeInstance=item.owner
        self.closestVal=item
        #self.activeInstance=activeInstance
        #self.direction=direction
        #self.ioItemList=ioItemList
        self.literal=literal
        self.sourceType=sourceType
        if printName is not None:
            self.printName=printName
        else:
            self.printName=literal
        #with self.activeInstance.lock:
        #    self.closestVal=self.activeInstance.findClosestNamedInput(
        #                                                self.direction,
        #                                                self.ioItemList)
        #if self.closestVal is None:
        #    raise SetError(itemName)


    #def findAffected(self, affectedOutputAIs, affectedInputAIs):
        #"""Find all affected input and output active instances."""
        #activeInstance=self.closestVal.ownerFunction
        #activeInstance.getValueAffectedAIs(self.closestVal, affectedInputAIs)

    def set(self, project, sourceTag):
        log.debug('TRANSACTION: set. self.sourceType: %s' % self.sourceType)
        activeFunction = self.closestVal.ownerFunction
        if activeFunction:
            with activeFunction.lock:
                dstVal=self.project.getCreateSubValue(self.itemList)
                dstVal.setFromString(self.literal)
        else:
            dstVal=self.project.getCreateSubValue(self.itemList)
            dstVal.setFromString(self.literal)

            #tp=dstVal.getType()
            #if not isinstance(self.literal, value.Value):
                #newVal=value.interpretLiteral(self.literal, tp, self.sourceType,
                                              #project.fileList)
            #else:
                #newVal=self.literal
                #if not (tp.isSubtype(rval.getType()) or
                        #rval.getType().isSubtype(tp) ):
                    #raise SetError(
                              #"Incompatible types in assignment: '%s' to '%s'"%
                              #(rval.getType().getName(), tp.getName()))
        #activeInstance.stageNamedInput(dstVal, newVal, sourceTag)
        ##this should be done in the transaction:
        #dstVal.notifyOwner(sourceTag, None)
        #dstVal.notifyDestinations(sourceTag, None)

    def describe(self, outf):
        """Print a description of this setValue to outf"""
        outf.write('Set %s to %s\n'%(self.itemName, self.printName))

class Transaction(run.FunctionRunOutput):
    """Holds a set of new output data + new connections + new instances to
       add in a single transaction. All updates must happen through this
       object"""
    def __init__(self, project, task, activeNetwork, importLib):
        """Initialize. Task may be None if outputs/subnetOutputs/cmds are
           empty.

           project = the project this transaction belongs to
           task = the task this transaction belongs to (may be None)
           activeNetwork = the active network this transaction manipulates
           importLib = the import library to use."""
        run.FunctionRunOutput.__init__(self)
        self.activeNetwork=activeNetwork
        self.task=task
        if task is not None:
            self.activeInstance=task.activeInstance
            self.seqNr=task.seqNr
        else:
            self.activeInstance=None
            self.seqNr=None
        self.project=project
        #self.imports=project.imports
        self.lib=importLib
        self.setValues=None # a list of new values to set

    def addSetValue(self, itemName, literal, sourceType, printName):
        sv=SetValue(self.project, itemName,
                    #instance, direction, ioItemList,
                    literal, sourceType, printName)
        if not isinstance(self.setValues, list):
            self.setValues=[sv]
        else:
            self.setValues.append(sv)
        return sv

    #def _makeConn(self, newConnection):
        #"""Make a connection object for a new connection."""
        #if newConnection.srcStr is not None:
            #log.debug("Making new connection %s -> %s"%
                      #(newConnection.srcStr, newConnection.dstStr))
            #conn=connection.makeConnectionFromDesc(self.activeNetwork,
                                                   #newConnection.srcStr,
                                                   #newConnection.dstStr)
        #else:
            #log.debug("Making assignment %s -> %s"%
                      #(newConnection.val.value,
                       #newConnection.dstStr))
            #conn=connection.makeInitialValueFromDesc(self.activeNetwork,
                                                     #newConnection.dstStr,
                                                     #newConnection.val)
        #newConnection.conn=conn

    def check(self, outf=None):
        """Check the transaction items for any errors."""
        # TODO: implement!!
        pass

    def run(self, outf=None):
        """Do a transaction."""
        # we start out with 'none' objects, and initialize them to sets if
        # there's a need for it.
        #locked=False
        addedInstances=None
        affectedOutputAIs=None
        affectedInputAIs=None
        # check for errors
        if (self.errMsg is not None):
            if self.activeInstance is not None:
                self.activeInstance.markError(self.errMsg)
                # and bail out immediately
                return
        try:
            log.debug("TRANSACTION STARTING *****************")
            log.debug('TRANSACTION: setValues: %s' % self.setValues)
            if (self.newConnections is None and self.setValues is None):
                # In this case, there is only one active instance to lock
                pass
            else:
                # there are multiple updates, so we must lock a network lock
                self.project.updateLock.acquire()
                # these are the active instances for which output locks are set
                affectedOutputAIs=set()
                # these are active instances for which handleNewInput() is
                # called
                affectedInputAIs=set()
                if self.activeInstance is not None:
                    affectedOutputAIs.add(self.activeInstance)
            # now make the new instances
            if self.newInstances is not None:
                addedInstances=[]
                for newInstance in self.newInstances:
                    log.debug("Making new instance %s of fn %s"%
                              (newInstance.name, newInstance.functionName))
                    fn=self.project.imports.getFunctionByFullName(
                                                    newInstance.functionName,
                                                    self.lib)
                    inst=instance.Instance(newInstance.name, fn,
                                           fn.getFullName())
                    # for later activation
                    addedInstances.append(self.activeNetwork.addInstance(inst))
            # make the new connections
            if self.newConnections is not None:
                # Make the connections
               for newConnection in self.newConnections:
                    #if newConnection.conn is None:
                    srcItemList = vtype.parseItemList(newConnection.srcStr)
                    dstItemList = vtype.parseItemList(newConnection.dstStr)
                    log.debug('NEW CONNECTION: %s %s' % (srcItemList, dstItemList))
                    srcVal = self.project.getCreateSubValue(srcItemList)
                    dstVal = self.project.getCreateSubValue(dstItemList)
                    if outf is not None:
                        newConnection.describe(outf)
                    log.debug('Adding connection from %s to %s' % (srcVal, dstVal))
                    srcVal.addConnection(dstVal)
                    #self.activeNetwork.findConnectionSrcDest(
                                                        #newConnection.conn,
                                                        #affectedOutputAIs,
                                                        #affectedInputAIs)
            if self.setValues is not None:
                for val in self.setValues:
                    log.debug("Setting new value %s"%(val.itemName))
                    #val.findAffected(affectedOutputAIs, affectedInputAIs)
            #if affectedOutputAIs is None:
                #if self.activeInstance is not None:
                    #self.activeInstance.outputLock.acquire()
                    #locked=True
            #else:
                #for ai in affectedOutputAIs:
                    #ai.outputLock.acquire()
                #locked=True
                #log.debug("Locked.")
            # now do the transaction
            # new values
            if self.setValues is not None:
                for val in self.setValues:
                    if outf is not None:
                        val.describe(outf)
                    val.set(self.project, self)
            # connections
            #if self.newConnections is not None:
                #for newConnection in self.newConnections:
                    #if outf is not None:
                        #newConnection.describe(outf)
                    #self.activeNetwork.addConnection(newConnection.conn, self)
            # call the function meant specifically for this
            #if self.activeInstance is not None:
                #if outf is not None:
                    #if self.outputs is not None:
                        #for output in self.outputs:
                            #output.describe(outf)
                    #if self.subnetOutputs is not None:
                        #for output in self.subnetOutputs:
                            #output.describe(outf)
                #if len(self.outputs) > 0 or len(self.subnetOutputs)>0:
                    #self.activeInstance.handleTaskOutput(self,
                                                         #self.seqNr,
                                                         #self.outputs,
                                                         #self.subnetOutputs,
                                                         #self.warnMsg)
            #if affectedInputAIs is not None:
                #for ai in affectedInputAIs:
                    ##log.debug("affected input AI %s"%ai.getCanonicalName())
                    #ai.handleNewInput(self, self.seqNr)
        except:
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            errmsg="Transaction error: %s"%(fo.getvalue())
            if self.activeInstance is not None:
                self.activeInstance.markError(errmsg)
            else:
                log.error(errmsg)
        finally:
            self.project.updateLock.release()
            #if locked:
                #if affectedOutputAIs is None:
                    #self.activeInstance.outputLock.release()
                #else:
                    #for ai in affectedOutputAIs:
                        #ai.outputLock.release()
            #if affectedOutputAIs is not None:
            #if not (self.newConnections is None and self.setValues is None):
                #self.project.updateLock.release()
        log.debug("Finished transaction locks")
        if addedInstances is not None:
            for inst in addedInstances:
                inst.activate()
        #log.debug("TRANSACTION ENDING *****************")



class TransactionList(object):
    """A list of transaction items (TransactionItem objects)"""
    def __init__(self, networkLock, autoCommit):
        """Initialize, with autocommit flag.
           networkLock = the project's network lock
           autoCommit = whether to autocommit every added item immediately"""
        self.lst=[]
        self.lock=threading.Lock()
        self.autoCommit=autoCommit
        self.networkLock=networkLock

    def addItem(self, transactionItem, project, outf):
        """Add a single transaction item to the list."""
        with self.lock:
            self.lst.append(transactionItem)
        if self.autoCommit:
            self.commit(project, outf)
        else:
            outf.write("Scheduled to ")
            transactionItem.describe(outf)
            outf.write(" at commit")

    def commit(self, project, outf):
        """Commit all items of the transaction in one step."""
        affectedInputAIs=set()
        affectedOutputAIs=set()
        outputsLocked=False
        outf.write("Committing scheduled changes:\n")
        with self.lock:
            with self.networkLock:
                try:
                    # first get all affected active instances.
                    for item in self.lst:
                        item.getAffected(project, affectedInputAIs,
                                         affectedOutputAIs)
                    # lock all affected I/O active instances
                    for ai in affectedOutputAIs:
                        ai.outputLock.acquire()
                    outputsLocked=True
                    # now run the transaction
                    for item in self.lst:
                        outf.write("- ")
                        item.run(project, project, outf)
                    for ai in affectedInputAIs:
                        ai.handleNewInput(project, 0)
                finally:
                    # make sure everything is released.
                    if outputsLocked:
                        for ai in affectedOutputAIs:
                            ai.outputLock.release()
                    self.lst=[]


