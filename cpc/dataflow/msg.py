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
log=logging.getLogger(__name__)

import threading
import os
import sys
import copy

import cpc.util
#import apperror
from value import StringValue, DictValue

#class MsgError(apperror.ApplicationError):
    #pass

class ActiveInstanceMsg(DictValue):
    """The active instance message object is a value that holds the
       messages associated with an active instance: errors, warnings and
       logs. It is accessible through cpcc get <active_inst_path>.msg"""

    def __init__(self, activeInst):
        """Initialize an empty message object."""
        # create the log file

        #self.logVal=value.Value(None,
                                #vtype.fileType, parent=self,
                                #owner=activeInst, selfName="log")
        #if activeInst.function.hasLog():
            #self.log=ActiveRunLog(os.path.join(activeInst.getFullBasedir(),
                                               #"_log"))
            #self.logVal.setLiteral(self.log.getFilename())
        #else:
            #self.log=None

        DictValue.__init__(self,
                           {'warning': StringValue(None, name='warning', container=self),
                            'error': StringValue(None, name='error', container=self)},
                           name='msg', ownerFunction=activeInst,
                           description='The active instance message object is a value that holds the'
                           'messages associated with an active instance: errors, warnings and'
                           'logs. It is accessible through cpcc get <active_inst_path>.msg')

        #self.subvals={ "warning" : self.warning,
                       #"error" : self.error,
                       #"log" : self.logVal }

    #def getLog(self):
        #return self.log

    def setError(self, msg):
        """Set the error message to None, or a string/unicode"""
        self.value['error'].value = msg

        #if msg is None:
            #self.error.setNone()
        #elif isinstance(msg, unicode):
            #self.error.setLiteral(msg)
        #else:
            #self.error.setLiteral(unicode(msg, encoding="utf-8",
                                          #errors='ignore'))

    def getError(self):
        """Get the error message"""
        return self.value['error'].value

    def hasError(self):
        """Check whether there is an error message."""
        return self.value['error'].value is not None

    def setWarning(self, msg):
        """Set the warning message to None, or a string/unicode"""
        self.value['warning'].value = msg

        #if msg is None:
            #self.warning.setNone()
        #elif isinstance(msg, unicode):
            #self.warning.setLiteral(msg)
        #else:
            #self.warning.setLiteral(unicode(msg, encoding="utf-8",
                                            #errors='ignore'))

    def getWarning(self):
        """Get the warning message"""
        return self.value['warning'].value

    def hasWarning(self):
        """Check whether there is a warning message."""
        return self.value['warning'].value is not None




#class ActiveRunLog(object):
    #"""Class holding a run log for an active instance requiring one."""
    #def __init__(self, filename):
        #"""Initialize with an absolute path name"""
        #self.filename=filename
        #self.lock=threading.Lock()
        #self.outf=None
    #def open(self):
        #"""Open the run log and return a file object, locking the log."""
        #self.lock.acquire()
        #self.outf=open(self.filename, 'a')
        #return self.outf
    #def close(self):
        #"""Close the file opened with open()"""
        #self.outf.close()
        #self.outf=None
        #self.lock.release()
    #def getFilename(self):
        #"""Get the file name"""
        #return self.filename


