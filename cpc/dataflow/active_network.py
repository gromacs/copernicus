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
log=logging.getLogger('cpc.dataflow.active_network')

import threading
import os

import cpc.util
import apperror
import keywords
import connection
import network
import active_inst
import vtype
import function_io

class ActiveError(apperror.ApplicationError):
    pass


class ActiveNetwork(network.Network):
    """An active function network is a function network with actual data."""
    def __init__(self, project, net, taskQueue, dirName, networkLock,
                 inActiveInstance=None):
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
        fullDirName=os.path.join(project.basedir, dirName)
        if dirName != "" and not os.path.exists(fullDirName):
            os.mkdir(fullDirName)
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
                self.findConnectionSrcDest(connCopy, affectedInputAIs,
                                            affectedOutputAIs)
                self.addConnection(connCopy, self) 
            # and now run the right handlers for the affected AIs
            if inActiveInstance is not None:
                affectedOutputAIs.add(inActiveInstance)
            if inActiveInstance is not None:
                affectedInputAIs.add(inActiveInstance)
            for ai in affectedInputAIs:
                ai.handleNewInput(self, None)

    def getParentInstance(self):
        """Get the instance this active network belongs to."""
        return self.inActiveInstance

    def getNetworkLock(self):
        """Get the global network lock assigned to this active network."""
        return self.networkLock

    def addInstance(self, inst):
        """Add a new instance, and return its activeInstance."""
        with self.lock:
            name=inst.getName()
            if name in self.activeInstances:
                raise ActiveError(
                            "Tried to start instance %s which already exists"%
                            name)
            dirn=os.path.join(self.baseDir,name)
            ai=active_inst.ActiveInstance(inst, self.project, self, dirn)
            log.debug("Adding active instance %s"%ai.name)
            self.activeInstances[name]=ai 
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
        """Get the named active instance associated with this network.
           Throw an ActiveError if not found."""
        with self.lock:
            return self._getActiveInstance(name)


    def tryGetActiveInstance(self, name):
        """Get the named active instance and return None if not found."""
        with self.lock:
            if name == keywords.Self:
                return self.inActiveInstance
            return self.activeInstances.get(name)

    def getActiveInstanceList(self, listIO, listSelf):
        """Return a dict of instance names. If listIO is true, each instance's
           IO items are listed as well"""
        ret=dict()
        with self.lock:
            for inst in self.activeInstances.itervalues():
                il={ "state" : str(inst.state),
                     "fn_name" : str(inst.function.getFullName()) }
                if listIO:
                    inps=inst.getInputs().getSubValueList() 
                    outs=inst.getOutputs().getSubValueList() 
                    il = { "state" : str(inst.state), 
                           "fn_name" : str(inst.function.getFullName()),
                           "inputs": inps, 
                           "outputs" : outs }
                ret[inst.name] = il
            if listSelf and (self.inActiveInstance is not None):
                inst=self.inActiveInstance
                il={ "state" : str(inst.state),
                     "fn_name" : str(inst.function.getFullName()) }
                if listIO:
                    inps=inst.getInputs().getSubValueList() 
                    outs=inst.getOutputs().getSubValueList() 
                    subnet_inps=inst.getSubnetInputs().getSubValueList()
                    subnet_outs=inst.getSubnetOutputs().getSubValueList()
                    il = { "state" : str(inst.state), 
                           "fn_name" : str(inst.function.getFullName()),
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

    #def _getNamedInstanceFromList(self, instancePathList):
    #    """Get an instance/network in a sequence of path names. """
    #    getContainingNet(instancePathList)
    #    top=instancePathList[0]
    #    if top=="":
    #       return self
    #    with self.lock:
    #        topItem=self._getActiveInstance(top)
    #    rest=instancePathList[1:]
    #    return topItem._getNamedInstanceFromList(rest)

    def _getContainingNet(self, instancePathList):
        """Return the tuple of (network, instanceName), for an 
           instancePathList"""
        #log.debug("instance path list: %s"%(instancePathList))
        if len(instancePathList)==0 or instancePathList[0] == '':
            return (self, None)
        elif len(instancePathList) < 2:
            return (self, instancePathList[0])
        # otherwise, get the network of the next item in the path.
        topItem=self._getActiveInstance(instancePathList[0])
        topNet=topItem.getNet()
        if topNet is None:
            raise ActiveError("Active instance %s has not subnet"%
                              topItem.getName())
        rest=instancePathList[1:]
        return topNet._getContainingNet( rest )

    def getNamedActiveInstance(self, instancePath):
        """Get and instance/network in a path specifier according to 
           [instance]:[instance]:... 
           """
        sp=instancePath.split(':')
        ( net, instanceName ) = self._getContainingNet(sp)
        if instanceName is not None:
            ret = net._getActiveInstance(instanceName)    
        else:
            ret = net
        return ret #self._getNamedInstanceFromList(sp)

    def getContainingNetwork(self, instancePath):
        """Get the network and instanceName that contains the item in a 
           path specifier according to 
           [instance]:[instance]:... 

           returns a tuple (network, instanceName)
           """
        sp=instancePath.split(':')
        ( net, instanceName ) = self._getContainingNet(sp)
        return (net, instanceName)

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

    def findConnectionSrcDest(self, conn, affectedInputAIs, affectedOutputAIs):
        """First step in making a connection: finding out the source and 
           destination (and the affected source/destination active instances).

           conn = the Connection object. Updated by this function
           affectedInputAIs = a set that will be updated with the affected
                              destination active instances of the new 
                              connection.
           affectedOutputAIs = a set that will be updated with the active 
                               instances that have changed outputs because of 
                               the new connection. For these active instances,
                               handleNewOutputConnections will have to be
                               called. 
                               This makes it possible to make multiple 
                               connections in a single transaction.
           """
        with self.lock:
            (srcAcp, dstAcp) = self.__getSrcDestAcps(conn)
            conn.srcAcp = srcAcp
            conn.dstAcp = dstAcp
            if conn.getSrcInstance() is not None:
                #affectedOutputAIs.add(dstAcp.sourceAcp.activeInstance)
                dstAcp.findConnectedOutputAIs(affectedOutputAIs)
            affectedInputAIs.add(dstAcp.activeInstance)
            dstAcp.findConnectedInputAIs(affectedInputAIs)

    def addConnection(self, conn, sourceTag): 
        """Add a connection. 
            findConnectionSrcDest MUST have been called on this connection
            before, and all affected output AIs MUST be locked at this point.
            After this, handleConnectedListenerInput() must be called on 
            affected destination ACPs' value.

            conn = the connection object
            sourceTag = the source to tag new inputs with
            """
        with self.lock:
            network.Network.addConnection(self, conn, sourceTag)
            #(srcAcp, dstAcp) = self.__getSrcDestAcps(conn)
            if conn.getSrcInstance() is not None:
                conn.srcAcp.connectDestination(conn.dstAcp, conn, sourceTag)
                log.debug("Active connection points  %s->%s connected"%
                          (conn.srcAcp.value.getFullName(),
                           conn.dstAcp.value.getFullName()))
            else:
                val=conn.getInitialValue()
                #log.debug("Setting input to %s: %s"%
                #          (conn.dstAcp.value.getFullName(), val.value))
                conn.dstAcp.update(val, sourceTag, None)
                conn.dstAcp.propagate(sourceTag, None)

    def activateAll(self):
        """Activate all activeinstances in this network, starting them."""
        with self.lock:
            for inst in self.activeInstances.itervalues():
                inst.activate()

    def deactivateAll(self):
        """De-activate all activeinstances in this network, starting them."""
        with self.lock:
            for inst in self.activeInstances.itervalues():
                inst.deactivate()

    def rerun(self, recursive, clearError, outf=None):
        """Clear the error in all sub-instances if recursive is true
           Returns the number of errors cleared"""
        ret=0
        if recursive:
            with self.lock:
                for inst in self.activeInstances.itervalues():
                    ret+=inst.rerun(recursive, clearError, outf)
        return ret

    def getCumulativeCputime(self):
        """Get the cumulative CPU time used (in seconds) for all active
           instances in this network and all subnets."""
        cputime=0
        with self.lock:
            for ai in self.activeInstances.itervalues():
                cputime += ai.getCumulativeCputime()
        return cputime

    def findErrorStates(self, errlist, warnlist):
        """Find any error states associated with this any of the 
           sub-instances. Fill errlist & warnlist with active instances in
           these states."""
        with self.lock:
            for ai in self.activeInstances.itervalues():
                ai.findErrorStates(errlist, warnlist)

    def getNet(self):
        """Get the first network, or None if none exists."""
        return self

    def writeXML(self, outFile, indent=0):
        """Write an XML description of the active network."""
        indstr=cpc.util.indStr*indent
        with self.lock:
            outFile.write('%s<network>\n'%indstr)
            for inst in self.instances.itervalues():
                if not inst.isImplicit():
                    inst.writeXML(outFile, indent+1) 
            for ai in self.activeInstances.itervalues():
                if ai.getName() != keywords.Self:
                    ai.writeXML(outFile, indent+1)
            for conn in self.connections:
                if not conn.isImplicit():
                    conn.writeXML(outFile, indent+1)
            outFile.write('%s</network>\n'%indstr)

