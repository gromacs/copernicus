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
log=logging.getLogger('cpc.dataflow.active')

import threading
import os
import os.path


import cpc.util
import apperror
import keywords
import connection
import instance
import network
import active_inst
import active_conn
import task
import vtype
import run
import value
import function_io

class ActiveError(apperror.ApplicationError):
    pass


class ActiveNetwork(network.Network):
    """An active function network is a function network with actual data."""
    def __init__(self, project, net, taskQueue, dirName, 
                 networkLock, inActiveInstance=None):
        """Create a new active network from a network. It may be part
           of an active instance.
          
           project =  the project the active network is a part of 
           net = any pre-exsiting network to copy
           functionNetwork = the function network to make an active network
                             from
           taskQueue =  the task queue associated with this active network
           dirName = the name of the base directory for this active network
           inActiveInstance = an optional activeInstance object that contains
                              this active network."""
        network.Network.__init__(self)
        self.project=project
        self.taskQueue=taskQueue
        self.baseDir=dirName
        if not os.path.exists(dirName):
            os.mkdir(dirName)
        # first make a 'self' instance
        self.inActiveInstance=inActiveInstance
        self.activeInstances=dict()
        # a lock to prevent concurrent mutations
        self.lock=threading.Lock()
        # and a global lock to prevent concurrent network mutations
        self.networkLock=networkLock
        # add self
        if inActiveInstance is not None:
            instCopy=inActiveInstance.instance.copy()
            instCopy.setName(keywords.Self)
            instCopy.markImplicit()
            # we only add the instance to the instance list, not the
            # active instance list:
            #self.activeInstances[instCopy.getName()]=ai 
            network.Network.addInstance(self, instCopy)
        # now copy the network
        if net is not None:
            log.debug("Adding active instances %s"%str(net.instances))
            for inst in net.getInstances().itervalues():
                name=inst.getName()
                # we treat 'self' specially: it doesn't get an activeinstance 
                # because it should already be active and passed as  
                # 'inActiveInstance'. 
                if name != keywords.Self: 
                    # create a new empty (unconnected) instance 
                    instCopy=inst.copy()
                    instCopy.markImplicit()
                    self.addInstance(instCopy)
                #else:
                    # we copy the top-level instance because that contains
                    # any additionally defined subnet inputs/outputs
                    #instCopy=inst.copy()
                    #instCopy.setName(keywords.Self)
                    #instCopy.markImplicit()
                    # we only add the instance to the instance list, not the
                    # active instance list:
                    #network.Network.addInstance(self, instCopy)
                    # now get notified whenever a subnet input/output gets added
                    #if self.inActiveInstance is not None:
                    #    self.inActiveInstance.addLinkedInstance(instCopy)
            # and now connect
            affectedInputAIs=set()
            affectedOutputAIs=set()
            for conn in net.connections:
                # copy the connection
                connCopy=connection.copyConnection(conn, self)
                connCopy.markImplicit()
                self.addConnection(connCopy, affectedInputAIs, 
                                   affectedOutputAIs)
            # and now run the right handlers for the affected AIs
            if inActiveInstance is not None:
                affectedOutputAIs.add(inActiveInstance)
            if inActiveInstance is not None:
                affectedInputAIs.add(inActiveInstance)
            for ai in affectedOutputAIs:
                ai.handleNewOutputConnections()
            for ai in affectedInputAIs:
                ai.handleNewInputConnections()

    def getBasedir(self):
        """Get the base directory."""
        return baseDir

    def getParentInstance(self):
        """Get the instance this active network belongs to."""
        return self.inActiveInstance

    def getNetworkLock(self):
        """Get the global network lock assigned to this active network."""
        return self.networkLock

    def addInstance(self, inst):
        """Add a new instance, and return its activeInstance."""
        name=inst.getName()
        dirn=os.path.join(self.baseDir,name)
        ai=active_inst.ActiveInstance(inst, self.project, self, dirn)
        with self.lock:
            if inst.getName() in self.activeInstances:
                raise ActiveError(
                            "Tried to start instance %s which already exists"%
                            inst.getName())
            #if inst.getName() not in self.activeInstances:
            else:
                log.debug("Adding active instance %s"%ai.name)
                self.activeInstances[inst.getName()]=ai 
                network.Network.addInstance(self, inst)
        return ai

    #def removeInstance(self, instance):
    # TODO: implement this
    #    """React to an instance being removed. Called after all its            
    #       connections are removed"""
    #    del self.activeInstances[instance.getName()]

    def _getActiveInstance(self, name):
        """Get the named active instance associated with this network."""
        try:
            if name==keywords.Self:
                return self.inActiveInstance
            return self.activeInstances[name]
        except KeyError:
            raise ActiveError("Active instance '%s' not found"%name)

    def getActiveInstance(self, name):
        """Get the named active instance associated with this network."""
        with self.lock:
            return self._getActiveInstance(name)

    def getActiveInstanceList(self, listIO=False, listSelf=False):
        """Return a dict of instance names. If listIO is true, each instance's
           IO items are listed as well"""
        ret=dict()
        with self.lock:
            for inst in self.activeInstances.itervalues():
                if not listIO:
                    il=str(inst.state)
                else:
                    inps=inst.getInputs().getSubValueList() 
                    outs=inst.getOutputs().getSubValueList() 
                    il = { "state" : str(inst.state), 
                           "inputs": inps, 
                           "outputs" : outs }
                ret[inst.name] = il
            if listSelf and (self.inActiveInstance is not None):
                inst=self.inActiveInstance
                if not listIO:
                    il=str(inst.state)
                else:
                    inps=inst.getInputs().getSubValueList() 
                    outs=inst.getOutputs().getSubValueList() 
                    subnet_inps=inst.getSubnetInputs().getSubValueList()
                    subnet_outs=inst.getSubnetOutputs().getSubValueList()
                    il = { "state" : str(inst.state), 
                           "inputs": inps, 
                           "outputs" : outs,
                           "subnet_inputs" : subnet_inps,
                           "subnet_outputs" : subnet_outs  }
                ret[keywords.Self] = il
        return ret

 
    def getConnectionList(self):
        """Return a list of instance connections."""
        ret=[]
        with self.lock:
            for conn in self.connections:
                dstInstance=conn.getDstInstance().getName()
                dstIO=str(conn.getDstIO().direction)
                dstItemList=vtype.itemListStr(conn.getDstItemList())
                dstItem="%s%s"%(dstIO, dstItemList)
                #dstSubItem=conn.getDstSubItem()
                if conn.getSrcInstance() is None:
                    ret.append( [ None, None, None,
                                  dstInstance, dstIO, dstItemList, 
                                  conn.getInitialValue().value ] )
                else:
                    srcInstance=conn.getSrcInstance().getName()
                    srcIO=str(conn.getSrcIO().direction)
                    srcItemList=vtype.itemListStr(conn.getSrcItemList())
                    srcItem="%s%s"%(srcIO, srcItemList)
                    #srcSubItem=conn.getSrcSubItem()
                    ret.append( [ srcInstance, srcItem, "", 
                                  dstInstance, dstItem, "", 
                                  None ] )
        return ret

    def _getNamedInstanceFromList(self, instancePathList):
        """Get an instance/network in a sequence of path names. """
        top=instancePathList[0]
        if top=="":
           return self
        with self.lock:
            topItem=self._getActiveInstance(top)
        rest=instancePathList[1:]
        return topItem._getNamedInstanceFromList(rest)

    def getNamedActiveInstance(self, instancePath):
        """Get and instance/network in a path specifier according to 
           [instance]:[instance]:... """
        sp=instancePath.split(':')
        if len(sp) == 1 and sp[0]=="":
            return self
        return self._getNamedInstanceFromList(sp)

    def getTaskQueue(self):
        """Get the task queue associated with this network."""
        return self.taskQueue

    def __getSrcDestAcps(self, conn):
        """Get source and destination active connection points based on a
           connection object."""
        # get the start active connection point
        srcAcp=None
        if conn.getSrcInstance() is not None:
            srcInstanceName=conn.getSrcInstance().getName()
            srcDir=conn.getSrcIO().getDir()
            if srcInstanceName != keywords.Self:
                srcAcpInst=self._getActiveInstance(srcInstanceName)
            else:
                srcAcpInst=self.inActiveInstance
            if srcDir==function_io.inputs:
                srcAcp=srcAcpInst.getInputACP(conn.getSrcItemList())
            elif srcDir==function_io.outputs:
                srcAcp=srcAcpInst.getOutputACP(conn.getSrcItemList())
            if srcDir==function_io.subnetInputs:
                srcAcp=srcAcpInst.getSubnetInputACP(conn.getSrcItemList())
            elif srcDir==function_io.subnetOutputs:
                srcAcp=srcAcpInst.getSubnetOutputACP(conn.getSrcItemList())
        # then get the destination instance 
        dstInstanceName=conn.getDstInstance().getName()
        dstItemName=conn.getDstItemList()
        dstDir=conn.getDstIO().getDir()
        if dstInstanceName != keywords.Self:
            dstAcpInst=self._getActiveInstance(dstInstanceName)
        else:
            dstAcpInst=self.inActiveInstance
        if dstDir==function_io.inputs:
            dstAcp=dstAcpInst.getInputACP(conn.getDstItemList())
        elif dstDir==function_io.outputs:
            dstAcp=dstAcpInst.getOutputACP(conn.getDstItemList())
        if dstDir==function_io.subnetInputs:
            dstAcp=dstAcpInst.getSubnetInputACP(conn.getDstItemList())
        elif dstDir==function_io.subnetOutputs:
            dstAcp=dstAcpInst.getSubnetOutputACP(conn.getDstItemList())
        return (srcAcp, dstAcp)

    #def _addConnection(self, conn, srcAcp, dstAcp):
        #if srcAcp is not None:
        # it's a real connection
        #log.debug("Connecting %s.%s.%s to %s.%s.%s"%
        #          (srcAcp.activeInstance.name, 
        #           str(srcAcp.ioItem.getDir()), srcAcp.name,
        #           dstAcp.activeInstance.name, 
        #           str(dstAcp.ioItem.getDir()), dstAcp.name))
        #srcAcp.connectDestination(dstAcp, conn)
        #log.debug("%s->%s connected"%(srcAcp.value.getFullName(),
        #                              dstAcp.value.getFullName()))
        #else:
        #    # it's an initial value
        #    dstAcp.setPropagateValue(initialValue) 


    def addConnection(self, conn, affectedInputAIs=None, 
                      affectedOutputAIs=None):
        """Add a connection
            conn = the Connection object
            affectedInputAIs = a set that will be updated with the active 
                               instances that have changed inputs because of 
                               the new connection. For these active instances,
                               handleNewInputConnections AND handleNewInput
                               will have to be called (AFTER affectedOutputAIs
                               are handled). This makes it possible
                               to make multiple connections in a single
                               transaction.
            affectedOutputAIs = a set that will be updated with the active 
                                instances that have changed outputs because of 
                                the new connection. For these active instances,
                                handleNewOutputConnections will have to be
                                called. 
                                This makes it possible to make multiple 
                                connections in a single transaction.

            if both affectedInputAIs and affectedOutputAIs are None, the 
            affected AIs will be updated immediately.
            """
        with self.lock:
            network.Network.addConnection(self, conn, 
                                          affectedInputAIs,
                                          affectedOutputAIs)
            (srcAcp, dstAcp) = self.__getSrcDestAcps(conn)
            # it is an error to have only one of them None. 
            ownSet=(affectedInputAIs is None and affectedOutputAIs is None)
            if conn.getSrcInstance() is not None:
                if ownSet:
                    affectedInputAIs=set()
                    affectedOutputAIs=set()
                srcAcp.connectDestination(dstAcp, conn, affectedInputAIs, 
                                          affectedOutputAIs)
                log.debug("Active connection points  %s->%s connected"%
                          (srcAcp.value.getFullName(),
                           dstAcp.value.getFullName()))
                if ownSet:
                    for ai in affectedOutputAIs:
                        ai.handleNewOutputConnections()
                    for ai in affectedInputAIs:
                        ai.handleNewInputConnections()
                    for ai in affectedInputAIs:
                        ai.handleNewInput(None, 0)
            else:
                #dstAcp.activeInstance.setNamedInputValue(
                #                                conn.getDstIO().getDir(),
                #                                conn.getDstItemList(),
                #                                conn.getInitialValue())
                val=conn.getInitialValue()
                log.debug("Setting input to %s: %s"%(dstAcp.value.getFullName(),
                                                     val.value))
                if ownSet:
                    affectedInputAIs=set()
                with dstAcp.activeInstance.lock:
                    dstAcp.setNewSetValue(conn.getInitialValue(),
                                          affectedInputAIs)
                if ownSet:
                    for ai in affectedInputAIs:
                        ai.handleNewInput(None, 0)
                    

    def activateAll(self):
        """Activate all activeinstances in this network, starting them."""
        with self.lock:
            for inst in self.activeInstances.itervalues():
                inst.activate()

    def getNet(self):
        """Get the first network, or None if none exists."""
        return self

    def writeXML(self, outFile, indent=0):
        """Write an XML description of the active network."""
        indstr=cpc.util.indStr*indent
        #iindstr=cpc.util.indStr*(indent+1)
        with self.lock:
            outFile.write('%s<network>\n'%indstr)
            for inst in self.instances.itervalues():
                #if inst.getName() != keywords.Self:
                if not inst.isImplicit():
                    inst.writeXML(outFile, indent+1) 
            for conn in self.connections:
                if not conn.isImplicit():
                    conn.writeXML(outFile, indent+1)
            for ai in self.activeInstances.itervalues():
                if ai.getName() != keywords.Self:
                    ai.writeXML(outFile, indent+1)
            outFile.write('%s</network>\n'%indstr)

