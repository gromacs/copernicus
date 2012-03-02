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
        # new value; needed to collect updated values into an update transaction
        # self.newValue=None
        # self.newValueSource=None
        # new value from manual setting. Used for update transactions generated
        # by user (cpcc set)
        self.newSetValue=None
        #self.newSetValueSeqnr=0
        # 
        self.dests=[]
        self.activeInstance=activeInstance
        self.sourceValue=self.value
        self.sourceAcp=self
        self.receiverList=[]
        self.direction=direction
        # the destination active instances:
        self.destAIs=set()
        self.newlyAdded=False

    def getValue(self):
        return self.value
    def getActiveInstance(self):
        return self.activeInstance

    def getSourceActiveInstance(self):
        return self.sourceAcp.activeInstance

    def setSource(self, sourceAcp, sourceValue):
        """Set the source active instance."""
        #self.sourceInstances=sourceInstance
        self.sourceValue=sourceValue
        self.sourceAcp=sourceAcp
        for dest in self.dests:
            dest.acp.setSource(sourceAcp, sourceValue)

    def copyValue(self, seqNr):
        self.value.update(self.sourceValue, seqNr)
        # if it's copied this way, this specific item is always updated.
        # Any sub-items could be marked updated before.
        self.value.markUpdated(True)

    def copySpecificSourceValue(self, sourceAI, seqNr):
        """Check and update this acp's value based on the presence of an 
           updated value in the source, if sourceAI and seqNr match the 
           source's value."""
        if ( sourceAI == self.sourceAcp.activeInstance and 
               seqNr == self.sourceValue.seqNr ): 
            self.value.update(self.sourceValue, seqNr)
            self.value.markUpdated(True)
            return True
        return False

    def copyNewSetValue(self):
        """Check and update this acp's value based on the presence of an 
           updated value in the source in newSetValue."""
        if self.newSetValue is not None:
            self.value.update(self.newSetValue, self.value.seqNr)
            self.value.markUpdated(True)
            self.newSetValue=None
            return True
        return False

    def setNewSetValue(self, val, affectedInputAIs):
        """Set a newSetValue val to be checked for with copyNewSetValue or
           copySpecificSourceValue."""
        self._searchDestinationAI(affectedInputAIs, True, val)

    def getDestinations(self):
        """Get all downstream connections."""
        return self.dests

    def connectDestination(self, destAcp, conn, 
                           affectedInputAIs, affectedOutputAIs):
        """Add a downstream connection to another activeConnectionPoint. 
           To be called from ActiveNetwork.addConnection()."""
        dst=Dest(destAcp, conn)
        self.dests.append(dst)
        destAcp.newlyAdded=True
        # set the source.
        destAcp.setSource(self.sourceAcp, self.sourceValue)
        # now figure out which active instances changed
        affectedOutputAIs.add(self.sourceAcp.activeInstance)
        destAcp._searchDestinationAI(affectedInputAIs, True)

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


    def searchDestinationActiveInstances(self):
        """Get the set of destination active instances for this source
           acp."""
        self.destAIs=set()
        self._searchDestinationAI(self.destAIs, False)

    def getDestinationActiveInstances(self):
        """Return the pre-computed set of destination active instances."""
        return self.destAIs

    def _searchDestinationAI(self, destAIs, selfAdd, newVal=None):
        """Helper function for searchDestinationActiveInstances."""
        if selfAdd:
            log.debug("  Adding dest %s"% self.value.getFullName())
            destAIs.add(self.activeInstance)
            if newVal is not None:
                log.debug("     Adding newSetValue to %s"%
                          self.value.getFullName())
                self.newSetValue=newVal
        # first find direct destinations
        for dest in self.dests:
            dest.acp._searchDestinationAI(destAIs, True, newVal)
        # find other listeners in sub-values
        listeners=self.value.findListeners()
        for listener in listeners:
            if listener is not self:
                listener._searchDestinationAI(destAIs, True, newVal)



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

