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


import time
import logging
import os
import xml.sax
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util

log=logging.getLogger('cpc.heartbeat.item')


class HeartbeatReaderError(cpc.util.CpcXMLError):
    pass


class HeartbeatWorker(object):
    """A collection of heartbeat items belonging to a worker."""
    def __init__(self, workerID, workerDir):
        self.workerID=workerID
        self.workerDir=workerDir
        self.items=[]
        self.lastHeard=time.time()

    def getWorkerDir(self):
        return self.workerDir
    def haveWorkerDir(self):
        """Return whether the worker's run directory is accessible."""
        return os.path.exists(self.workerDir)

    def ping(self):
        """Update the time associated with the last heard ping to now."""
        self.lastHeard=time.time()
    def addItem(self, item):
        """Add a single heartbeat item to the worker."""
        self.items.append(item)

    def setItems(self, items):
        """Set the heartbeat item list."""
        self.items=items

    def getItems(self):
        """Get the full heartbeat item list."""
        return self.items
    def clearItems(self):
        """clear the full heartbeat item list."""
        self.items=[]

    def writeXML(self, outf):
        outf.write('<worker id="%s" dir="%s">\n'%(self.workerID, 
                                                  self.workerDir))
        for item in self.items:
            item.writeXML(outf)
        outf.write('</worker>\n')

    def toJSON(self):
        """Returns a dict with the object contents so it can be 
           JSON-serialized."""
        ret=dict()
        ret['worker_id'] = self.workerID
        ret['worker_dir'] = self.workerDir
        ret['items'] = []
        for item in self.items:
            ret['items'].append(item.toJSON())
        return ret


class HeartbeatItem(object):
    """A single heartbeat command item."""
    def __init__(self, cmdID, serverName, runDir):
        """Initialize the heartbeat item
           cmdID      = the command ID of the command to watch
           serverName = the command's originating server
           runDir     = the run directory of the worker."""
        self.cmdID=cmdID
        self.serverName=serverName
        self.runDir=runDir

    def writeXML(self, outf):
        """Write state as xml."""
        outf.write('    <heartbeat-item cmd_id="%s" server_name="%s" run_dir="%s"/>\n'
                   %(self.cmdID, self.serverName, self.runDir))

    def getCmdID(self):
        """Return the command ID."""
        return self.cmdID
    def getServerName(self):
        """Return the originating server name."""
        return self.serverName
    def getRunDir(self):
        """Return the item's run directory."""
        return self.runDir
    def haveRunDir(self):
        """Return whether the item's run directory is accessible."""
        return os.path.exists(self.runDir)

    def toJSON(self):
        ret=dict()
        ret['cmd_id']=self.cmdID
        ret['server_name']=self.serverName
        ret['run_dir']=self.runDir
        ret['data_accessible']=self.haveRunDir()
        return ret


class HeartbeatWorkerReader(xml.sax.handler.ContentHandler):
    """XML reader for (a list of) HeartbeatWorkers. 
       Can read either a heartbeat signal (for one given worker), or a
       list of heartbeat workers and items from a saved state."""
    def __init__(self, worker=None):
        """Initialize the reader.
           worker = the worker to read heartbeat signal into. If it is none,
                    a heartbeat list containing multiple workers will be read"""
        if worker is None:
            self.curWorker=None
            self.workers=[]
        else:
            self.curWorker=worker
            self.workers=None
        self.readList=(worker is None)

    def getWorkers(self):
        """Get the worker list with items."""
        return self.workers

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
            if self.curWorker is None:
                raise HeartbeatReaderError("Hearbeat item without worker", 
                                           self.loc)
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
            hbi=HeartbeatItem(cmdID, serverName, runDir)
            self.curWorker.addItem(hbi)
        elif name == "worker":
            if not self.readList:
                raise HeartbeatReaderError("More than one worker in heartbeat signal")
            if not attrs.has_key("id"):
                raise HeartbeatReaderError("worker has no id", self.loc)
            if not attrs.has_key("dir"):
                raise HeartbeatReaderError("worker has no dir", self.loc)
            id=attrs.getValue('id')
            workerDir=attrs.getValue('dir')
            self.curWorker=HeartbeatWorker(id, workerDir)
            self.workers.append(self.curWorker)
        elif name == "heartbeat-list":
            if not self.readList:
                raise HeartbeatReaderError("Unsupported tag %s"%name, self.loc)
        elif name == "heartbeat":
            if self.readList:
                raise HeartbeatReaderError("Unsupported tag %s"%name, self.loc)
        else:
            raise HeartbeatReaderError("Unknown tag %s"%name, self.loc)
            
    def endElement(self, name):
        if name == "worker":
            self.curWorker=None

