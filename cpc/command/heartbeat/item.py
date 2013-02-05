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
import os
import xml.sax

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util
import cpc.server.message

log=logging.getLogger('cpc.heartbeat.item')


class HeartbeatReaderError(cpc.util.CpcXMLError):
    pass



class HeartbeatItem(object):
    stateOK=0               # Item is OK
    stateNotFound=1         # The command was not found by the server
    stateWrongWorker=2      # The command is owned by another worker

    """A single heartbeat command item."""
    def __init__(self, cmdID, serverName, runDir):
        """Initialize the heartbeat item
           cmdID      = the command ID of the command to watch
           serverName = the command's originating server
           runDir     = the run directory of the worker.  """
        self.cmdID=cmdID
        self.serverName=serverName
        self.runDir=runDir
        self.state=self.stateOK
        self.haveRunDir=None

    def writeXML(self, outf):
        """Write state as xml."""
        if self.haveRunDir is None:
            outf.write('    <heartbeat-item cmd_id="%s" server_name="%s" run_dir="%s"/>\n'
                       %(self.cmdID, self.serverName, self.runDir))
        else:
            outf.write('    <heartbeat-item cmd_id="%s" server_name="%s" run_dir="%s" have_run_dir="%s"/>\n'
                       %(self.cmdID, self.serverName, self.runDir, 
                         str(self.haveRunDir)))


    def getCmdID(self):
        """Return the command ID."""
        return self.cmdID
    def getServerName(self):
        """Return the originating server name."""
        return self.serverName
    def getRunDir(self):
        """Return the item's run directory."""
        return self.runDir

    def setHaveRunDir(self, val):
        """Set whether the item's run directory is present."""
        self.haveRunDir=val

    def getHaveRunDir(self):
        """Return whether the item's run directory is accessible. 
           Returns None if it hasn't been checked."""
        return self.haveRunDir

    def checkRunDir(self):
        """Check whether the item's run directory is accessible."""
        #log.debug("Checking whether %s exists."%(self.runDir))
        self.haveRunDir=os.path.exists(self.runDir)

    def getState(self):
        """get the state of the item."""
        return self.state

    def setState(self, state):
        """set the state of the item. The state should be one of the constants
           stateOK, stateNotFound."""
        self.state=state

    def toJSON(self):
        ret=dict()
        ret['cmd_id']=self.cmdID
        ret['server_name']=self.serverName
        ret['run_dir']=self.runDir
        ret['data_accessible']=self.haveRunDir()
        return ret


class HeartbeatItemReader(xml.sax.handler.ContentHandler):
    """XML reader for (a list of) HeartbeatWorkers. 
       Can read either a heartbeat signal (for one given worker), or a
       list of heartbeat workers and items from a saved state."""
    def __init__(self, worker=None):
        """Initialize the reader.
           worker = the worker to read heartbeat signal into. If it is none,
                    a heartbeat list containing multiple workers will be read"""
        self.items=[]

    def getItems(self):
        """Get the worker list with items."""
        return self.items

    def setDocumentLocator(self, locator):
        self.loc=locator

    def read(self, filename):
        """Read a file with heartbeat items.
        filename = the file's name."""
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inf=open(filename, 'r')
        parser.parse(inf)
        inf.close()

    def readString(self, str, description):
        """Read the XML from the string str. 'description' describes the 
           source of this XML in exceptions."""
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inputSrc=xml.sax.InputSource()
        inputSrc.setByteStream(StringIO(str))
        inputSrc.setPublicId(description)
        inputSrc.setSystemId(description)
        parser.parse(inputSrc)

    def startElement(self, name, attrs):
        if name == "heartbeat-item":
            #if self.curWorker is None:
            #    raise HeartbeatReaderError("Hearbeat item without worker", 
            #                               self.loc)
            if not attrs.has_key("cmd_id"):
                raise HeartbeatReaderError("heartbeat item has no cmd id",
                                           self.loc)
            if not attrs.has_key("server_name"):
                raise HeartbeatReaderError("heartbeat item has no server_name",
                                               self.loc)
            if not attrs.has_key("run_dir"):
                raise HeartbeatReaderError("heartbeat item has no run_dir",
                                           self.loc)
            cmdID=attrs.getValue("cmd_id")
            serverName=attrs.getValue("server_name")
            runDir=attrs.getValue("run_dir")
            if attrs.has_key('have_run_dir'):
                haveRunDir=cpc.util.getBooleanAttribute(attrs,'have_run_dir')
            else:
                haveRunDir=None
            hbi=HeartbeatItem(cmdID, serverName, runDir)
            hbi.setHaveRunDir(haveRunDir)
            self.items.append(hbi)
        elif name == "heartbeat":
            pass
        else:
            raise HeartbeatReaderError("Unknown tag %s"%name, self.loc)
            
    def endElement(self, name):
        if name == "worker":
            self.curWorker=None

