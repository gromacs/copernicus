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


import cpc.util
import resource
import runvars

class Platform(object):
    """The run platform with its associated capabilities."""
    def __init__(self, name, arch, preferJoin, callRun=False, callFinish=False):
        """Initialize a platform based on a 
           name = the platform name
           arch = the platform hw architecture
           preferJoin = whether the platform prefers joined commands 
                        (i.e.: whether commands should be joined into
                         one big one, such as with mdrun -multidir).
           callRun = whether to call the platform plugin with the run command
                     before each run.
           callFinish = whether to call the platform plugin with the finish
                        command after each run."""
        self.name=name
        self.arch=arch
        self.preferJoin=preferJoin
        self.callRun=callRun
        self.callFinish=callFinish
        # the maximum resource values
        self.maxResources = dict()
        # the minimum resource value supported
        self.minResources = dict()
        # The preferred resource values
        self.prefResources = dict()
        self.runvars = runvars.RunVars()
        

    def addMaxResource(self, rsrc):
        """Add a single max. resource to the platform."""
        self.maxResources[rsrc.name] = rsrc
    def getMaxResources(self):
        """Get the list (dict) of max. resources."""
        return self.maxResources
    def getMaxResource(self, name):
        """Get a specific max. resource value or None."""
        if self.maxResources.has_key(name):
            return self.maxResources[name].value
        else:
            return None
    def hasMaxResource(self, name):
        """Check whether a specific max. resource has been set for 
           this platform."""
        return self.maxResources.has_key(name)

    def addMinResource(self, rsrc):
        """Add a single min. resource to the platform."""
        self.minResources[rsrc.name] = rsrc
    def getMinResources(self):
        """Get the list (dict) of min. resources."""
        return self.minResources
    def getMinResource(self, name):
        """Get a specific min. resource value or None."""
        if self.minResources.has_key(name):
            return self.minResources[name].value
        else:
            return None
    def hasMinResource(self, name):
        """Check whether a specific min. resource has been set for this 
           platform."""
        return self.minResources.has_key(name)

    def addPrefResource(self, rsrc):
        """Add a single pref. resource to the platform."""
        self.prefResources[rsrc.name] = rsrc
    def getPrefResources(self):
        """Get the list (dict) of pref. resources."""
        return self.prefResources
    def getPrefResource(self, name):
        """Get a specific pref. resource value or None."""
        if self.prefResources.has_key(name):
            return self.prefResources[name].value
        else:
            return None
    def hasPrefResource(self, name):
        """Check whether a specific pref. resource has been set for 
           this platform."""
        return self.prefResources.has_key(name)

    def reserveCmdResources(self, cmd):
        """Subtract a command's reservations from this platform's max.
           resources. 
           Changes the available resources to reflect the reservation of 
           that command's reserved resources.
           cmd = the command"""
        for rsrc in self.maxResources.itervalues():
            if cmd.hasReserved(rsrc.name):
                rsrc.value -= cmd.getReserved(rsrc.name)

    def releaseCmdResources(self, cmd):
        """Add a command's reservations from this platform's max.
           resources. 
           Changes the available resources to reflect the release of 
           that command's reserved resources.
           cmd = the command"""
        for rsrc in self.maxResources.itervalues():
            if cmd.hasReserved(rsrc.name):
                rsrc.value += cmd.getReserved(rsrc.name)

    def canReserveCmdResources(self, cmd):
        """Check whether all of a command's reserved resources can be reserved
           with the current platform state.
           cmd = the command to check reserved resources for."""
        for rsrc in self.maxResources.itervalues():
            if cmd.hasReserved(rsrc.name):
                if rsrc.value - cmd.getReserved(rsrc.name) < 0:
                    return False
        return True

    def addRunVar(self, name, value):
        """Add a single run variable to the platform."""
        self.runvars.add(name, value)
    def getRunVars(self):
        """Return the runvars object."""
        return self.runvars
    def setRunVars(self, runvars):
        """Set a new runvars object."""
        self.runvars=runvars
    #def getRunVars(self):
    #    """Return a dictionary with run variables."""
    #    return self.runvars

    def getName(self):
        return self.name

    def getArch(self):
        return self.arch

    def isJoinPrefered(self):
        return self.preferJoin
    def callRunSet(self):
        return self.callRun
    def callFinishSet(self):
        return self.callFinish

    def printXML(self):
        co=StringIO()
        self.writeXML(co)
        return co.getvalue()

    def writeXML(self, outf):
        if self.preferJoin:
            pjs=' prefer_join="true"'
        else:
            pjs=''
        if self.callRun:
            pjs += ' call_run="true"'
        if self.callFinish:
            pjs += ' call_finish="true"'
        outf.write('<platform name="%s" arch="%s"%s>\n'%(self.name, self.arch,
                                                          pjs))
        outf.write(' <resources>\n')
        outf.write('  <max>\n')
        for rsrc in self.maxResources.itervalues():
            rsrc.writeXML(outf)
        outf.write('  </max>\n')
        outf.write('  <min>\n')
        for rsrc in self.minResources.itervalues():
            rsrc.writeXML(outf)
        outf.write('  </min>\n')
        outf.write('  <pref>\n')
        for rsrc in self.prefResources.itervalues():
            rsrc.writeXML(outf)
        outf.write('  </pref>\n')
        outf.write(' </resources>\n')
        outf.write('</platform>\n')



class PlatformReaderError(cpc.util.CpcXMLError):
    pass

class PlatformReader(xml.sax.handler.ContentHandler):
    """XML Reader for platforms."""
    def __init__(self):
        self.platforms=[]
        self.curPlatform=None
        self.inResources=False
        self.inMaxResources=False
        self.inMinResources=False
        self.inPrefResources=False
        self.resourceReader=None
        self.inRunVars=False
        self.runVarReader=None

    def getPlatforms(self):
        return self.platforms

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
        if self.resourceReader is not None:
            self.resourceReader.setDocumentLocator(locator)
        if self.runVarReader is not None:
            self.runVarReader.setDocumentLocator(locator)

    def startElement(self, name, attrs):
        if self.inMaxResources or self.inMinResources or self.inPrefResources:
            self.resourceReader.startElement(name, attrs)
        elif self.inRunVars:
            self.runVarReader.startElement(name, attrs)
        elif name == 'platform-list':
            pass
        elif name == 'platform':
            if not attrs.has_key('name'):
                raise PlatformReaderError("platform has no name", self.loc)
            if not attrs.has_key('arch'):
                raise PlatformReaderError("platform has no arch", self.loc)
            name=attrs.getValue('name')
            arch=attrs.getValue('arch')
            preferJoin=cpc.util.getBooleanAttribute(attrs, "prefer_join")
            callRun=cpc.util.getBooleanAttribute(attrs, "call_run")
            callFinish=cpc.util.getBooleanAttribute(attrs, "call_finish")
            self.curPlatform=Platform(name, arch, preferJoin, callRun, 
                                      callFinish)
        elif name == "resources":
            self.inResources=True
        elif name == 'max' and self.inResources:
            self.inMaxResources=True
            self.resourceReader=resource.ResourceReader()
        elif name == 'min' and self.inResources:
            self.inMinResources=True
            self.resourceReader=resource.ResourceReader()
        elif name == 'pref' and self.inResources:
            self.inPrefResources=True
            self.resourceReader=resource.ResourceReader()
        elif name == 'run-vars':
            self.inRunVars=True
            self.runVarReader=runvars.RunVarReader()

    def endElement(self, name):
        if self.inMinResources:
            if name == "min":
                for rsrc in self.resourceReader.getResourceList():
                    self.curPlatform.addMinResource(rsrc)
                self.inMinResources=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        elif self.inMaxResources:
            if name == "max":
                for rsrc in self.resourceReader.getResourceList():
                    self.curPlatform.addMaxResource(rsrc)
                self.inMaxResources=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        elif self.inPrefResources:
            if name == "pref":
                for rsrc in self.resourceReader.getResourceList():
                    self.curPlatform.addPrefResource(rsrc)
                self.inPrefResources=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        elif self.inResources:
            if name == "resources":
                self.inResources=False
        elif self.inRunVars:
            if name == "run-vars":
                self.inRunVars=False
                self.curPlatform.setRunVars(self.runVarReader.getRunVars())
                self.runVarReader=None
        elif name == 'platform':
            self.platforms.append(self.curPlatform)
            self.curPlatform=None



