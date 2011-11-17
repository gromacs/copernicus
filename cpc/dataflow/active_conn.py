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


log=logging.getLogger('cpc.dataflow.active_conn')
import threading
import copy


import cpc.util
import apperror
import value
import active_value

class ActiveConnectionError(apperror.ApplicationError):
    pass

class ReceiverConnection(object):
    """A class holding a single input connection for a receiver: an active
       connection point that is a destination of the current active connection 
       point."""
    def __init__(self, 
                 srcActiveInstance, srcConnectionPoint,
                 dstActiveInstance, dstConnectionPoint):
        """Initialize based on a specific activeConnectionPoint and a 
           (possibly empty) list of subitems. A subitem is a
           list of array subscripts, or data structure member names. """
        self.srcActiveInstance=srcActiveInstance
        self.srcConnectionPoint=srcConnectionPoint
        self.dstActiveInstance=dstActiveInstance
        self.dstConnectionPoint=dstConnectionPoint

class Dest(object):
    """An object holding information about a downstream connection."""
    def __init__(self, activeConnectionPoint, conn):
        """Initialize based on a destination active connection point, a
           connection, and a source and destination subItem."""
        self.acp=activeConnectionPoint
        self.conn=conn

class ActiveConnectionPoint(active_value.ValueUpdateListener):
    """An object holding a connection point that can is used in 
       ActiveConnection objects. Can serve as input or output
       point, with active instance or further connection points associated
       with it."""
    def __init__(self, val, activeInstance, direction):
        """Initialize an active connection point with an any active instance 
           and downstream connections.

           name = the acp (active connectin point)'s name
           val = the value associated with this connection point
           activeInstance = the active instance associated with this connection 
                            point
           direction = the direction associated with this acp
        """
        self.value=val
        self.value.setListener(self)
        self.dests=[]
        self.activeInstance=activeInstance
        self.sourceValue=self.value
        self.sourceAcp=self
        self.receiverList=[]
        self.direction=direction

    def getValue(self):
        return self.value
    def getActiveInstance(self):
        return self.activeInstance

    def setSource(self, sourceAcp, sourceValue):
        """Set the source active instance."""
        #self.sourceInstances=sourceInstance
        self.sourceValue=sourceValue
        self.sourceAcp=sourceAcp
        for dest in self.dests:
            dest.acp.setSource(sourceAcp, sourceValue)

    def copySourceValue(self, seqNr):
        self.value.update(self.sourceValue, seqNr)
        # if it's copied this way, this specific item is always updated.
        # Any sub-items could be marked updated before.
        self.value.markUpdated(True)

    def getDestinations(self):
        """Get all downstream connections."""
        return self.dests

    def connectDestination(self, destAcp, conn, seqNr):
        """Add a downstream connection to another activeConnectionPoint."""
        dst=Dest(destAcp, conn)
        self.dests.append(dst)
        # set the source.
        destAcp.setSource(self.sourceAcp, self.sourceValue)
        #self.findReceiverConnections()
        changed=set() 
        #seqNr=self.activeInstance.getSeqNr()
        #self.propagateValue(changed, seqNr)
        destAcp._acceptPropagateToListeners(changed, seqNr)
        #destAcp.propagateValue(changed, seqNr)
        for inst in changed:
            inst.handleNewInput()

    def disconnectDestination(self, activeConnection, conn):
        """Remove an existing downstream connection to another 
           activeConnectionPoint."""
        found=None
        for dest in self.dests:
            if dest.conn== conn:
                found=dest
                break
        if found:
            self.dests.remove(found)

    def update(self):
        """Function inherited from ValueUpdateListener. Called whenever a
           value changes."""
        pass

    def _acceptPropagate(self, changedSet, seqNr):
        self.copySourceValue(seqNr)
        changedSet.add(self.activeInstance)
        for dest in self.dests:
            dest.acp._acceptPropagateToListeners(changedSet, seqNr)

    def _acceptPropagateToListeners(self, changedSet, seqNr):
        self.copySourceValue(seqNr)
        changedSet.add(self.activeInstance)
        for dest in self.dests:
            dest.acp._acceptPropagate(changedSet, seqNr)
        # now find other listeners and propagate them
        listeners=self.value.findListeners()
        for listener in listeners:
            if listener is not self:
                listener._acceptPropagate(changedSet, seqNr)


    def propagateValue(self, changedSet, seqNr):
        """Propagate a new value to its destinations."""
        for dest in self.dests:
            dest.acp._acceptPropagateToListeners(changedSet, seqNr)

    #def _findDestReceiverConnections(self, source):
    #    """Add all receiver connections that this acp is directly connected 
    #       to."""
    #    ret=[]
    #    for dest in self.dests:
    #        ret.extend(dest.acp._findReceiverConnections(source))
    #    ret.append(ReceiverConnection(source.activeInstance, source, 
    #                                  self.activeInstance, self))
    #    return ret

    #def _findReceiverConnections(self, source):
    #    """Find all relevant listeners and update their receiver connections"""
    #    ret=[]
    #    for dest in self.dests:
    #        ret.extend(dest.acp._findReceiverConnections(source))
    #    # now find all the subitems
    #    listlist=self.value.findListeners()
    #    #log.debug("listlist=%s"%str(listlist))
    #    #nstr="[ "
    #    #for item in listlist:
    #    #    nstr+= "%s (%s), "%(item.value.getFullName(),
    #    #                        id(item))
    #    #nstr+=" ]"
    #    #log.debug("self=%s (%s), listlist=%s"% 
    #    #          (self.value.getFullName(), id(self), nstr))
    #    for acp in listlist:
    #        if acp != self:
    #            ret.extend(acp._findDestReceiverConnections(source)) 
    #    # and append myself.
    #    #if self.direction.isInput():
    #    # we assume we don't need to check whether we're ourselves an input
    #    # because this function is only run for dests
    #    ret.append(ReceiverConnection(source.activeInstance, source, 
    #                                  self.activeInstance, self))
    #    return ret

    #def findReceiverConnections(self):
    #    """Find and return all receiver connection objects associated with 
    #       this acp."""
    #    #lst=self._findDestReceiverConnections(self)
    #    lst=[]
    #    for dest in self.dests:
    #        lst.append(ReceiverConnection(self.activeInstance, self,
    #                                      dest.activeInstance, dest))
    #    #               dest.acp._findReceiverConnections(self))
    #    #listlist=self.value.findListeners()
    #    #for acp in listlist:
    #    #    if acp != self:
    #    #        lst.extend(acp._findReceiverConnections(self)) 
    #    self.receiverList=lst
    #    # update all upstream acps
    #    if self.sourceAcp is not None and self.sourceAcp is not self:
    #        self.sourceAcp.findReceiverConnections()

    def writeXML(self, outf, indent=0):
        """Write value to xml"""
        indstr=cpc.util.indStr*indent
        if self.value is not None:
            val='value="%s"'%self.value.value
            tp='value_type="%s"'%self.value.type.getName()
        else:
            val=""
            tp=""
        outf.write('%s<active-connection id="%s" %s/>\n'% 
                   (indstr, self.val.getFullName(), val) )

