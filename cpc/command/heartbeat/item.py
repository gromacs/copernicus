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
import threading
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util
import cpc.server.message

log=logging.getLogger('cpc.heartbeat.item')


class HeartbeatReaderError(cpc.util.CpcXMLError):
    pass


#class HeartbeatWorker(object):
#    """A collection of heartbeat items belonging to a worker."""
#    def __init__(self, workerID, workerDir):
#        self.workerID=workerID
#        self.workerDir=workerDir
#        self.items=[]
#        self.lastHeard=time.time()
#        self.lock=threading.Lock()
#
#    def getWorkerDir(self):
#        return self.workerDir
#    def haveWorkerDir(self):
#        """Return whether the worker's run directory is accessible."""
#        return os.path.exists(self.workerDir)
#
#    def ping(self):
#        """Update the time associated with the last heard ping to now."""
#        with self.lock:
#            self.lastHeard=time.time()
#    def addItem(self, item):
#        """Add a single heartbeat item to the worker."""
#        with self.lock:
#            self.items.append(item)
#
#    def setItems(self, items):
#        """Set the heartbeat item list."""
#        with self.lock:
#            self.items=items
#
#    #def getItems(self):
#    #    """Get the full heartbeat item list."""
#    #    with self.lock:
#    #        return self.items
#    def clearItems(self):
#        """clear the full heartbeat item list."""
#        with self.lock:
#            self.items=[]
#
#
#    def notifyServer(self):
#        """Notify the server that a worker has died.
#           Returns the client response."""
#        log.info("Worker %s has died."%(self.workerID))
#        with self.lock:
#            # now notify all the appropriate servers.
#            #sendSucceeded=False
#            for item in self.items:
#                log.info("Notifying %s that worker of cmd %s has died."%
#                         (item.serverName, item.cmdID))
#                tff=None
#                try:
#                    if item.haveRunDir():
#                        # if it exists, we create a tar file and send it.
#                        tff=tempfile.TemporaryFile()
#                        tf=tarfile.open(fileobj=tff, mode="w:gz")
#                        tf.add(item.getRunDir(), arcname=".", recursive=True)
#                        tf.close()
#                        tff.seek(0)
#                        #sendSucceeded=True
#                except:
#                    # we make sure we don't upload in case of doubt
#                    pass
#                clnt=cpc.server.message.server_message.ServerMessage()
#                clnt.commandFailedRequest(item.cmdID, item.serverName, tff)
#            if self.haveWorkerDir():
#                try:
#                    # remove the worker directory
#                    shutil.rmtree(self.workerDir, ignore_errors=True)
#                except:
#                    # and duly ignore the response.
#                    pass
#
#
#    def writeXML(self, outf, serverName=None):
#        """Write the XML for a worker's heartbeat items to outf. If serverName
#           is not None, only list heartbeat items for that server."""
#        with self.lock:
#            outf.write('<worker id="%s" dir="%s">\n'%(self.workerID, 
#                                                      self.workerDir))
#            for item in self.items:
#                if serverName is None or serverName == item.serverName:
#                    item.writeXML(outf)
#            outf.write('</worker>\n')
#
#    def toJSON(self):
#        """Returns a dict with the object contents so it can be 
#           JSON-serialized."""
#        ret=dict()
#        with self.lock:
#            ret['worker_id'] = self.workerID
#            ret['worker_dir'] = self.workerDir
#            ret['items'] = []
#            for item in self.items:
#                ret['items'].append(item.toJSON())
#        return ret


class HeartbeatItem(object):
    stateOK=0               # Item is OK
    stateNotFound=1         # The command was not found by the server
    stateWrongWorker=2      # The command is owned by another worker

    """A single heartbeat command item."""
    def __init__(self, cmdID, serverName, runDir):
        """Initialize the heartbeat item
           cmdID      = the command ID of the command to watch
           serverName = the command's originating server
           runDir     = the run directory of the worker."""
        self.cmdID=cmdID
        self.serverName=serverName
        self.runDir=runDir
        self.state=self.stateOK

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
        #log.debug("Checking whether %s exists."%(self.runDir))
        return os.path.exists(self.runDir)

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
            hbi=HeartbeatItem(cmdID, serverName, runDir)
            self.items.append(hbi)
        elif name == "heartbeat":
            pass
        else:
            raise HeartbeatReaderError("Unknown tag %s"%name, self.loc)
            
    def endElement(self, name):
        if name == "worker":
            self.curWorker=None

