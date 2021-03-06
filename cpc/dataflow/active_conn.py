# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2014, Sander Pronk, Iman Pouya, Magnus Lundborg, Erik Lindahl, and others.
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


log=logging.getLogger(__name__)

import cpc.util
import apperror
import function_io
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
    __slots__=['value', 'directDests', 'activeInstance', 'sourceValue',
               'sourceAcp', 'directSource', 'direction', 'listeners']
    def __init__(self, val, activeInstance, direction):
        """Initialize an active connection point with an any active instance
           and downstream connections.

           name = the acp (active connectin point)'s name
           val = the value associated with this connection point
           activeInstance = the active instance associated with this connection
                            point
           direction = the direction associated with this acp
        """
        # tie ourselves into the value.
        self.value=val
        self.value.setListener(self)
        # immediate destination active connection points
        self.directDests=[]
        # the parent active instance
        self.activeInstance=activeInstance
        # the ultimate source value
        self.sourceValue=self.value
        self.sourceAcp=self
        # the direct source value (i.e. what this is connected to).
        self.directSource=None
        #self.receiverList=[]
        self.direction=direction
        # precomputed set of all the direct acps associated with the value of
        # this acp.
        self.listeners=[]

    def getValue(self):
        return self.value
    def getActiveInstance(self):
        return self.activeInstance

    def getSourceActiveInstance(self):
        return self.sourceAcp.activeInstance

    def setSource(self, directSource, sourceAcp, sourceValue):
        """Set the source active instance.

           directSource = the directly connectd source acp
           sourceAcp = the originating source (source of the source..)
           sourceValue = the originating source value
           """
        self.directSource=directSource
        self.sourceValue=sourceValue
        self.sourceAcp=sourceAcp
        for dest in self.directDests:
            dest.acp.setSource(self, sourceAcp, sourceValue)

    def stageNewInput(self, source, seqNr):
        """Stage new input into the newValue fields of the value

           source = the source output item/project
           seqNr = the new sequence number (or None)
           """
        self.value.stageNewValue(self.sourceValue, source, seqNr)

    def update(self, newValue, sourceTag, seqNr):
        """Update the value associated with this connection point."""
        self.value.update(newValue, seqNr, sourceTag)

    def connectDestination(self, destAcp, conn, sourceTag):
        """Add a downstream connection to another activeConnectionPoint.
           To be called from ActiveNetwork.addConnection().

           NOTE: assumes the active instance's output lock is locked
           """
        # now do the actual connecting bit
        dst=Dest(destAcp, conn)
        self.directDests.append(dst)
        # handle the destination's end.
        destAcp.setSource(self, self.sourceAcp, self.sourceValue)
        # recalculate the output connection points
        self.activeInstance.handleNewConnections()
        # now find the listeners of the destination value. We can do
        # this because its input is locked, and if it's an output, it cannot
        # write there anyway because it's a valid destination for this.
        listeners=[]
        destAcp.value.findListeners(listeners)
        for listener in listeners:
            listener.searchDestinations()
        # propagate our value downstream
        #self.value.setSourceTag(sourceTag)
        self._propagateSpecificDest(destAcp, sourceTag, None)


    def _propagateSpecificDest(self, dest, sourceTag, seqNr):
        """Propagate a value to a specific destination"""
        #log.debug("*Propagating new value %s to %s"%
        #          (self.value.value, dest.value.getFullName()))
        dest.value.update(self.value, seqNr, sourceTag=sourceTag)
        dest.propagate(sourceTag, seqNr)

    def propagate(self, sourceTag, seqNr, propagated = None):
        """Accept a new value with a source tag and sequence number,
           and propagate it to any listeners."""
        #log.debug("Propagating new value to %s"%self.value.getFullName())
        # first handle direct destinations

        # Propagated cannot have set() as default parameter for some reason.
        # In that case it is not properly emptied.
        if propagated is None:
            propagated = set()
        self._propagateDests(sourceTag, seqNr, propagated)
        # then handle other listeners to the same value
        for listener in self.listeners:
            # these listeners are in the same value tree, so no need to update
            #log.debug("Listener-propagating to %s"%
            #          (listener.value.getFullName()))
            listener._propagateDests(sourceTag, seqNr, propagated)

    #def _propagateSelfDests(self, sourceTag, seqNr):
    #   for dest in self.directDests:
    #       dest.acp.value.update(self.value, seqNr, sourceTag=sourceTag)

    def _propagateDests(self, sourceTag, seqNr, propagated):
        """Propagate an updated value to the direct destinations of this acp."""
        for dest in self.directDests:
            # If it has already been propagated it does not have to be propagated
            # again.
            if dest.acp.value not in propagated:
                #log.debug("Propagating new value %s to %s"%
                #          (self.value.value, dest.acp.value.getFullName()))
                propagated.add(dest.acp.value)
                # because in it's another value tree, we first need to update it
                dest.acp.value.update(self.value, seqNr, sourceTag=sourceTag)
                dest.acp.propagate(sourceTag, seqNr, propagated)

    def notifyDestinations(self, sourceTag, seqNr):
        """Notify the ActiveInstance associated with this acp through
           handleNewInput(), and notify all listeners through
           notifyListeners()."""
        self._notifyDests(sourceTag, seqNr)
        for listener in self.listeners:
            # these listeners are in the same value tree, so no need to update
            listener._notifyDests(sourceTag, seqNr)

    def _notifyDests(self, sourceTag, seqNr):
        """Helper function for notifyDestinations()"""
        for dest in self.directDests:
            # because in it's another value tree, we first need to update it
            if ( (dest.acp.direction == function_io.inputs) or
                 (dest.acp.direction == function_io.subnetInputs) ):
                dest.acp.activeInstance.handleNewInput(sourceTag, seqNr)
            else:
                dest.acp.activeInstance.resetUpdated()
            dest.acp.notifyDestinations(sourceTag, seqNr)

    def searchDestinations(self):
        """Get the set of destination active instances for this source acp."""
        self.listeners=[]
        self.value.findListeners(self.listeners, self)
        #log.debug("%s: %d listeners"%(self.value.getFullName(),
        #                              len(self.listeners)))

    def getListeners(self):
        """Return the pre-computed set listeners on the value of this acp."""
        return self.listeners

    def findConnectedInputAIs(self, affectedInputAIs):
        """Find all input AIs associated with this acp and add them to the set
           affectedInputAIs"""
        # we don't add self; that's already done when this function is called
        # (even recursively).
        self._findConnectedInputAIs(affectedInputAIs)
        for listener in self.listeners:
            listener._findConnectedInputAIs(affectedInputAIs)

    def _findConnectedInputAIs(self, affectedInputAIs):
        """Helper function for findConnectedInputAIs."""
        for dest in self.directDests:
            # we add it and then make it search for its direct destinations
            # in all its listeners
            if dest.acp.activeInstance not in affectedInputAIs:
                affectedInputAIs.add(dest.acp.activeInstance)
                dest.acp.findConnectedInputAIs(affectedInputAIs)

    def findConnectedOutputAIs(self, affectedOutputAIs):
        """Find all source acps and their active instances. Update the set
           affecteOutputAIs with these"""
        affectedOutputAIs.add(self.activeInstance)
        if self.directSource is not None:
            self.directSource.findConnectedOutputAIs(affectedOutputAIs)

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
                   (indstr, self.value.getFullName(), val) )

