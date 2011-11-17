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


import platform
import executable


class PlatformExecutableReader(xml.sax.handler.ContentHandler):
    """XML Reader for platforms and executables. User at the server
       to read the platform&executable descriptions from the workers."""
    def __init__(self, executableDir=None):
        self.platformReader=platform.PlatformReader()
        self.executableReader=executable.ExecutableReader(executableDir)
        self.inPlatform=False
        self.inExecutable=False

    def getPlatforms(self):
        return self.platformReader.getPlatforms()

    def getExecutableList(self):
        return executable.ExecutableList(self.executableReader.getExecutables())

    def read(self,filename):
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
        self.platformReader.setDocumentLocator(locator)
        self.executableReader.setDocumentLocator(locator)

    def startElement(self, name, attrs):
        if name == 'worker-arch-capabilities':
            pass
        elif name == 'platform':
            self.inPlatform=True
        elif name == 'executable':
            self.inExecutable=True
        if self.inPlatform:
            self.platformReader.startElement(name, attrs)
        elif self.inExecutable:
            self.executableReader.startElement(name, attrs)

    def endElement(self, name):
        if self.inPlatform:
            self.platformReader.endElement(name)
        if self.inExecutable:
            self.executableReader.endElement(name)
        if name == 'platform':
            self.inPlatform=False
        elif name == 'executable':
            self.inExecutable=False


