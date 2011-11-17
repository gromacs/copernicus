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



import xml.sax
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.server.command
import cpc.util
class PlatformReservation(object):
    """A reservation associated with a platform. Used to communicate
       with the platform plugin.
       All calls of the platform plugin (except the info command) are
       done with at least one PlatformReservation; the 'platform' command
       simply contains no reservations, but it always has the 
       worker directory set."""
    def __init__(self, workerDir, cmdDir=None, reservationID=None,
                 reservedResources=None):
        """Makes a platform reservation
           workerDir        = the worker's base working directory
           cmdDir           = a specific command's directory (only set if
                              a reservation is being made)
           reservationID    = a specific ID associated with the reservation
           reservedResources = a dict with the reserved resources."""
        self.workerDir=workerDir
        self.cmdDir=cmdDir
        self.id=reservationID
        if reservedResources is not None:
            self.reservedResources=reservedResources
        else:
            self.reservedResources=dict()

    def getWorkerDir(self):
        return self.workerDir
    def getCmdDir(self):
        return self.cmdDir
    def getID(self):
        return self.id
    def getReservedResources(self):
        return self.reservedResources
    def setReservedResources(self, reservedResources):
        self.reservedResources=reservedResources

    def writeXML(self, outf):
        attrs=""
        if self.cmdDir is not None:
            attrs += ' command_dir="%s"'%self.cmdDir
        if self.id is not None:
            attrs += ' id="%s"'%self.id
        outf.write('<platform-reservation worker_dir="%s" %s>\n'%
                   (self.workerDir,attrs))
        for rsrc in self.reservedResources.itervalues():
            rsrc.writeXML(outf)
        outf.write('</platform-reservation>\n')

    def printXML(self):
        cf=StringIO()
        self.writeXML(cf)
        return cf.getvalue()


class PlatformReservationReaderError(cpc.util.CpcXMLError):
    pass

class PlatformReservationReader(xml.sax.handler.ContentHandler):
    """xml reader for resources."""
    def __init__(self):
        self.reservation=None
        self.inResources=False
        self.resourceReader=None

    def getReservation(self):
        return self.reservation

    def read(self, file):
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        #inf=open(file, 'r')
        parser.parse(file)
        #inf.close()

    def setDocumentLocator(self, locator):
        self.loc=locator
        if self.resourceReader is not None:
            self.resourceReader.setDocumentLocator(locator)

    def startElement(self, name, attrs):
        if self.inResources:
            self.resourceReader.startElement(name, attrs)    
        elif name == "platform-reservation":
            if self.reservation  is not None:
                raise PlatformReservationReaderError(
                              "Double-booked reservation", self.loc)
            if not attrs.has_key('worker_dir'):
                raise PlatformReservationReaderError(
                              "No worker directory in reservation", self.loc)
            workerDir=attrs.getValue('worker_dir')
            cmdDir=None
            if attrs.has_key('command_dir'):
                cmdDir=attrs.getValue('command_dir')
            id=None
            if attrs.has_key('id'):
                id=attrs.getValue('id')
            self.reservation=PlatformReservation(workerDir, cmdDir, id)
            self.inResources=True
            self.resourceReader=cpc.server.command.ResourceReader()
        else:
            raise PlatformReservationReaderError("unknown tag %s"%name, 
                                                 self.loc)

    def endElement(self, name):
        if self.inResources:
            if name=="platform-reservation":
                self.inResources=False
                self.reservation.setReservedResources(
                                 self.resourceReader.getResourceList())
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)

