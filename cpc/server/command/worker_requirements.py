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
import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util.plugin
from cpc.util.conf.server_conf import ServerConf
import platform
from version import Version
import logging

log = logging.getLogger('cpc.server.command.extras_handler')



class ExtrasReaderError(cpc.util.CpcXMLError):
    pass

class WorkerRequirementsReader(xml.sax.handler.ContentHandler):
    """XML Reader for extra options."""
    def __init__(self):
        self.workerRequirements={}
        self.curKey=None
        self.curValue=None

    def getWorkerRequirements(self):
        return self.workerRequirements

    def read(self, filename):
        self.filename=filename
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

    def setDocumentLocator(self, locator):
        self.loc=locator

    def startElement(self, name, attrs):
        if name == 'worker-requirements':
            pass
        elif name == 'option':
            if self.curKey is not None:
                raise ExtrasReaderError("second option in reader",
                                            self.loc)
            if not attrs.has_key('key'):
                raise ExtrasReaderError("option has no key",
                                            self.loc)
            if not attrs.has_key('value'):
                raise ExtrasReaderError("option has no value",
                                            self.loc)
            self.curKey=attrs.getValue('key')
            self.curValue=attrs.getValue('value')
        else:
            raise ExtrasReaderError("Unknown tag %s"%name, self.loc)


    def endElement(self,name):
        if name == 'option':
            self.workerRequirements[self.curKey]=self.curValue
            self.curKey=None
            self.curValue=None

