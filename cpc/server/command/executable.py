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

log = logging.getLogger('cpc.server.command.executable')


class Executable(object):
    """An executable is an object that points to a platform-specific binary
       that can be executed to run a command."""
    def __init__(self, basedir, name, platform, arch, version, id=None):
        """Initialize based on 
           basedir  = directory containing the xml file of the  executable
           name     = the name of the executable
           platform = the platform name this executable runs on (MPI,SMP,etc)
           arch     = the architecture this executable runs on (x86,x86_64,etc)
           version  = the version number object associated with this executable.
           id       = an optional ID for the executable. This is usually 
                      non-persistent.
           """
        self.basedir=basedir
        self.name=name
        self.platform=platform
        self.arch=arch
        self.version=version
        self.id=id
        self.runSet=False
        self.joinable=False

    def setID(self, id):
        """Set a new ID."""
        self.id=id

    def getID(self):
        """Get the ID."""
        return self.id

    def addRun(self, inPath, cmdline):
        """Add run parameters.
           inPath = whether the file to execute should be in $PATH
           cmdline = the command line to execute."""
        self.inPath=inPath
        self.cmdline=cmdline
        self.runSet=True

    def addJoinable(self, matchArgs, matchNcores, commonArgs, specificArgs):
        """Add command-joining capability parameters.
           matchArgs = whether the arguments have to match to be able to join
           matchNcores = whether the number of cores  have to match 
           commonArgs = the string of arguments common for all directories to 
                        be joined
           specificArgs = the string of arguments specific for each directory
                          to be joined
           """
        self.joinMatchArgs=matchArgs
        self.joinMatchNcores=matchNcores
        self.joinCommonArgs=commonArgs
        self.joinSpecificArgs=specificArgs
        self.joinable=True

    def isJoinable(self):
        """Returns whether the executable supports joinable commands."""
        return self.joinable

    def printPartialXML(self):
        """Write out the parts of the executable that need to be transmitted
           from worker to server to a string."""
        co=StringIO()
        self.writePartialXML(co)
        return co.getvalue()

    def writePartialXML(self, outf):
        """Write out the parts of the executable that need to be transmitted
           from worker to server."""
        outf.write('<executable name="%s" platform="%s" arch="%s" version="%s"'%
                   (self.name, self.platform, self.arch, self.version.getStr()))
        if self.id is not None:
            outf.write(' id="%s"'%self.id)
        outf.write(' />\n')

class ExecutableList(object):
    """The (searchable) list of executables on the worker."""
    def __init__(self, list=[]):
        self.executables=list
    
    def readDir(self, bindir, platforms):
        """Read a directory (usually in the search path) for all executables.
    
            bindir = the directory name.
            platforms = the list of availble platforms."""
        reader=ExecutableReader(bindir)
        
        try:
            files=os.listdir(bindir)
        except OSError:
            files=[]
        for file in files:
            try:
                basedir=os.path.join(bindir, file)
                log.debug("basedir is %s"%basedir)
                pfile=os.path.join(basedir, "plugin")
                log.debug("pfile is %s"%pfile)                
                nfile=os.path.join(basedir, "executable.xml")
                log.debug("exec xml is %s"%nfile)
                pl=None
                # check whether this is in fact a plugin
                if (not os.path.isdir(basedir)) and os.access(basedir, os.X_OK):
                    plf=basedir
                    pl=cpc.util.plugin.ExecutablePlugin(
                                                    specificLocation=basedir,conf=ServerConf())
                # or it contains a plugin
                elif (not os.path.isdir(pfile)) and os.access(pfile, os.X_OK):
                    plf=basedir
                    pl=cpc.util.plugin.ExecutablePlugin(
                                                    specificLocation=pfile,conf=ServerConf())
                if pl is not None:
                    # and run the plugin if it is one
                    for platform in platforms:
                        (retcode, retst)=pl.run(plf, platform)
                        if retcode==0:
                            reader.readString(retst, "executable plugin output",
                                              basedir)
                elif os.path.exists(nfile):
                    try:
                        # otherwise just read the executable xml
                        reader.read(nfile, basedir)
                    except IOError:
                        pass
            except IOError:
                pass
        self.executables.extend(reader.getExecutables())

    def printPartialXML(self):
        """Construct a string with a list of all available executables."""
        co=StringIO()
        for exe in self.executables:
            exe.writePartialXML(co)
        return co.getvalue()

        retstr=u''
        for exe in self.executables:
            retstr += exe.printPartialXML()
        return retstr

    def find(self, name, platform, minVersion, maxVersion):
        """Find a matching executable in the list."""
        log.debug("have %d executables"%len(self.executables))
        for exe in self.executables:
            log.debug("exe name:%s platform name %s"%(exe.name,platform.name))
            if name == exe.name and platform.name == exe.platform and \
                    ((minVersion is None) or (minVersion<=exe.version)) and \
                    ((maxVersion is None) or (maxVersion>=exe.version)):
                return exe
        return None
    
    def findAllByPlattform(self,platform):
        exes = []
        for exe in self.executables:
            if exe.platform == platform:
                exes.append(exe)
        
        return exes

    def genIDs(self):
        """Generate IDs for all executables in the list. Used for identifying 
           executables when transmitting them to the server."""
        i=0
        for executable in self.executables:
            executable.setID(str(i))


class ExecutableReaderError(cpc.util.CpcXMLError):
    pass

class ExecutableReader(xml.sax.handler.ContentHandler):
    """XML Reader for executables."""
    def __init__(self, basedir):
        self.basedir=basedir
        self.executables=[]
        self.curExec=None

    def getExecutables(self):
        return self.executables

    def read(self, filename, basedir=None):
        self.filename=filename
        if basedir is not None:
            self.basedir=basedir
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inf=open(filename, 'r')
        parser.parse(inf)
        inf.close()

    def readString(self, str, description, basedir=None):
        """Read the XML from the string str. 'description' describes the 
            source of this XML in exceptions."""
        if basedir is not None:
            self.basedir=basedir
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
        if name == 'executable':
            if self.curExec is not None:
                raise ExecutableReaderError("second executable in reader", 
                                            self.loc)
            if not attrs.has_key('name'):
                raise ExecutableReaderError("executable has no name", 
                                            self.loc)
            if not attrs.has_key('platform'):
                raise ExecutableReaderError("executable has no platform", 
                                            self.loc)
            if not attrs.has_key('arch'):
                raise ExecutableReaderError("executable has no arch", 
                                            self.loc)
            if not attrs.has_key('version'):
                raise ExecutableReaderError("executable has no version", 
                                            self.loc)
            name=attrs.getValue('name')
            version=Version(attrs.getValue('version'))
            platform=attrs.getValue('platform')
            arch=attrs.getValue('arch')
            id=None
            if attrs.has_key('id'):
                id=attrs.getValue('id')
            self.curExec=Executable(self.basedir, name, platform, arch,
                                    version, id=id)
        elif name == "run":
            if not attrs.has_key('cmdline'):
                raise ExecutableReaderError("run tag has no cmdline")
            inPath=cpc.util.getBooleanAttribute(attrs, 'in_path')
            cmdline=attrs.getValue("cmdline")
            self.curExec.addRun(inPath, cmdline)
        elif name=="cmd-joinable":
            matchArgs=cpc.util.getBooleanAttribute(attrs, 'match_args')
            matchNcores=cpc.util.getBooleanAttribute(attrs, 
                                                            'match_ncores')
            commonArgs=attrs.getValue('common_args')
            specificArgs=attrs.getValue('specific_args')
            self.curExec.addJoinable(matchArgs, matchNcores, commonArgs, 
                                     specificArgs)
        else:
            raise ExecutableReaderError("Unknown tag %s"%name, self.loc)

    def endElement(self,name):
        if name == 'executable':
            self.executables.append(self.curExec)
            self.curExec=None

