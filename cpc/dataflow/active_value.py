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
import collections
import os
import os.path
import xml.sax


log=logging.getLogger('cpc.dataflow.active_value')


import cpc.util
import apperror
import vtype
import value

class ActiveValError(cpc.util.CpcError):
    pass

class ValueUpdateListener(object):
    """Base class of any class that wants to listen to updates of specific
       values."""
    def update(self, val):
        """The method that will be called when the value is updated. 
           Can either return None, or a list of items that are 
           returned with the value's update() method."""
        return None

class ActiveValue(value.Value):
    """The class describing an active data value, as held by an active 
       instance."""
    def __init__(self, val, tp, parent=None, selfName=None, seqNr=0,
                 createObject=None, fileList=None):
        """Initializes an new value, with no references
    
           val = an original value
           tp = the actual type
           parent = the parent in which this value is a sub-item
           selfName = the name in the parent's collection
        """
        if createObject is None:
            createObject=ActiveValue
        value.Value.__init__(self, val, tp, parent, selfName,
                             createObject=createObject, fileList=fileList)
        self.seqNr=seqNr # sequence number.
        self.listener=None

    def setListener(self, listener):
        """Set a pointer to an associated listener (usually an active 
           connection point)."""
        self.listener=listener
    def getListener(self):
        """Get the associated listener."""
        return self.listener

    def update(self, outputVal, newSeqNr):
        """Set a new value from a Value, and call update() on all subitems. 
           This keeps all the metadata intact."""
        if self.seqNr > newSeqNr:
            log.debug("Rejecting update because of sequence number: %d>%d."%
                      (self.seqNr, newSeqNr))
            return
        if self.basetype!=outputVal.basetype:
            raise ActiveValError("Type mismatch in %s: expected %s, got %s"%
                                 (self.getFullName(),
                                  self.basetype.getName(), 
                                  outputVal.basetype.getName()))
        self.seqNr=newSeqNr
        # keep the file value for later.
        fileValue=self.fileValue
        self.fileValue=None
        # check updated
        if outputVal.updated:
            self.markUpdated(True)
        # now set the value.
        if not outputVal.basetype.isCompound():
            # and set value
            if (self.fileList is not None and 
                outputVal.basetype.isSubtype(vtype.fileType)
                and outputVal.value is not None):
                if os.path.isabs(outputVal.value):
                    self.fileValue=self.fileList.getAbsoluteFile(outputVal.
                                                                 value)
                    self.value=self.fileValue.getName()
                else:
                    self.fileValue=self.fileList.getFile(outputVal.value)
                    self.value=outputVal.value
            else:
                self.value=outputVal.value
        else:
            self.updated=outputVal.updated
            if self.basetype == vtype.listType:
                for name, item in outputVal.value.iteritems():
                    if not self.type.hasMember(name):
                        raise ActiveValError("Unknown member item '%s'"%name)
                    # make the value if it doesn't exist
                    if not self.value.has_key(name):
                        self.value[name]=self._create(None, 
                                                      self.type.getMember(name),
                                                      members[name], name)
                    self.value[name].update(item, newSeqNr)
            elif self.basetype == vtype.dictType:
                for name, item in outputVal.value:
                    if not self.value.has_key(name):
                        self.value[name]=self._create(None,
                                                      self.type.getMembers(),
                                                      name)
                    self.value[name].update(item, newSeqNr)
            elif self.basetype == vtype.arrayType:
                i=0
                if not isinstance(self.value, list):
                    self.value=[]
                for item in outputVal.value:
                    if len(self.value) < i+1:
                        self.value.append(self._create(None, 
                                                       self.type.getMembers(), 
                                                       i))
                    self.value[i].update(item, newSeqNr)
                    i+=1
            else:
                raise ActiveValError("Unknown compound type")
        # remove previous reference, only after we know the new value
        # has added a ref (it might be the same file).
        if fileValue is not None:
            fileValue.rmRef()

    def addMember(self, name, tp, opt, const):
        """Add a member item to a list if this value is a list.
           name = the name
           tp = the member type
           opt = whether it is optional
           const = whether it should be constant."""
        if self.type.isSubtype(vtype.listType):
            self.type.addMember(name, tp, opt, const)
            self.value[name]=self._create(None, tp, name)
        else:
            raise ActiveValError("Tried to add member to non-list value")

    def _findSubListeners(self, listlist):
        """Helper function for findListeners()."""
        if self.listener is not None:
            listlist.append(self.listener)
        if isinstance(self.value, dict):
            for val in self.value.itervalues():
                val._findSubListeners(listlist)
        elif isinstance(self.value, list):
            for val in self.value:
                val._findSubListeners(listlist)

    def _findSuperListeners(self, listlist):
        """Helper function for findListeners()."""
        if self.listener is not None:
            listlist.append(self.listener)
        if self.parent is not None:
            self.parent._findSuperListeners(listlist)

    def findListeners(self):
        """Find all listeners on this value and all its subvalues."""
        listlist=[]
        self._findSubListeners(listlist)
        if self.parent is not None:
            self.parent._findSuperListeners(listlist)
        return listlist


