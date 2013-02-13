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
log=logging.getLogger('cpc.dataflow.status')

import threading
import os
import sys
import copy
import xml.sax.saxutils


import cpc.util
import apperror
import vtype
import value
from cpc.dataflow.value import ValError

class MsgError(apperror.ApplicationError):
    pass

class ActiveInstanceMsg(value.ValueBase):
    """The active instance message object is a value that holds the
       messages associated with an active instance: errors, warnings and
       logs. It is accessible through cpcc get <active_inst_path>.msg"""

    def __init__(self, activeInst):
        """Initialize an empty message object."""
        # create the log file

        self.logVal=value.Value(None,
                                vtype.fileType, parent=self,
                                owner=activeInst, selfName="log")
        if activeInst.function.hasLog():
            self.log=ActiveRunLog(os.path.join(activeInst.getFullBasedir(),
                                               "_log"))
            self.logVal.setLiteral(self.log.getFilename())
        else:
            self.log=None

        self.warning=value.Value(None, vtype.stringType, parent=self,
                                 owner=activeInst, selfName="warning")
        self.error=value.Value(None, vtype.stringType, parent=self,
                               owner=activeInst, selfName="error")
        self.subvals={ "warning" : self.warning,
                       "error" : self.error,
                       "log" : self.logVal }

    def getLog(self):
        return self.log

    def setError(self, msg):
        """Set the error message to None, or a string/unicode"""
        if msg is None:
            self.error.setNone()
        elif isinstance(msg, unicode):
            self.error.setLiteral(msg)
        else:
            self.error.setLiteral(unicode(msg, encoding="utf-8",
                                          errors='ignore'))

    def getError(self):
        """Get the error message"""
        return self.error.value

    def hasError(self):
        """Check whether there is an error message."""
        return self.error.value is not None

    def setWarning(self, msg):
        """Set the warning message to None, or a string/unicode"""
        if msg is None:
            self.warning.setNone()
        elif isinstance(msg, unicode):
            self.warning.setLiteral(msg)
        else:
            self.warning.setLiteral(unicode(msg, encoding="utf-8",
                                            errors='ignore'))

    def getWarning(self):
        """Get the error message"""
        return self.warning.value

    def hasWarning(self):
        """Check whether there is a warning message."""
        return self.warning.value is not None


    ########################################################
    # Member functions from the ValueBase interface:
    ########################################################
    def _getSubVal(self, itemList):
        """Helper function"""
        return self.subvals.get(itemList[0])
 
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
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.getCreateSubValue(itemList[1:], createType,
                                            setCreateSourceTag)
        raise ValError("Cannot create sub value of message")

    def getClosestSubValue(self, itemList):
        """Get the closest relevant subvalue through a list of subitems

           itemList = the path of the value to get the closest value for """
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        if subval is not None:
            return subval.getClosestSubValue(itemList[1:])
        return self

    def getSubValueList(self):
        """Return a list of addressable subvalues."""
        ret=self.subvals.keys()
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
        return vtype.msgType

    def getDesc(self):
        """Return a 'description' of a value: an item that can be passed to
           the client describing the value."""
        ret=dict()
        for name, i in self.subvals.iteritems():
            if i.value is not None:
                ret[name]=name #i.getDesc()
            else:
                ret[name]="None"
        return ret
    ########################################################


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


