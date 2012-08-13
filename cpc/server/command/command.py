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
import random
import hashlib
import threading
import logging
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cpc.util
import version
import resource


log=logging.getLogger('cpc.project')


seeded=False # whether the command id generator has been seeded
seededLock=threading.Lock()


class CommandInputFile(object):
    """A class describing an input file in a command"""
    def __init__(self, realName, packagedName):
        """Initialized with a real file name and a packaged name.

           realName = the real file name, relative to the command's execution
                      diretory (or absolute path).
           packagedName = the file name relative to the command execution 
                          directory that the file should have when unpacked
                          on the worker."""
        self.realName=realName
        self.packagedName=packagedName

    def getRealName(self):
        return self.realName
    def getPackagedName(self):
        return self.packagedName

class Command(object):
    """A command is what is executed on runners. Each task that is emitted
       by the controller is broken up in commands (using the task plugins).
       """
    def __init__(self, dir, executable, args, 
                 addPriority=0, minVersion=None, maxVersion=None, 
                 id=None, task=None, running=False, workerServer=None,
                 env=None, outputFiles=None):
        """Create a command
            dir = the directory 
            executable = the name of the executable object
            args = the arguments for the executable
            files = the needed input files (as a list of CommandInputFile     
                                            objects) 
            minVersion = the minimum version for the command's executable
            maxVersion = the maximum version for the executable
            id = the command's ID (or None to generate one at random).
            task = the task associated with the command
            running = whether the cmd is running
            workerServer = the server the worker executing this command is 
                           connected to.
            env = environment variables to set: a dict of values (or None).
            outputFiles = the list of any expected output files.
           """
        #self.taskID=taskID
        self.dir=dir
        self.executable=executable
        self.inputFiles=[]
        self.outputFiles=outputFiles
        self.args=args
        self.minVersion=minVersion
        self.maxVersion=maxVersion
        self.addPriority=addPriority
        self.task=None
        self.running=running # whether the command is running
        self.id=id
        self.workerServer=workerServer
        # the cpu time in seconds used by this command
        self.cputime=0
        # dictionary of reserved resource objects
        self.reserved={}
        # dictionary of required resource objects
        # all commands need a CPU to run on
        cores=resource.Resource('cores', 1) 
        self.minRequired = { cores.name: cores }
        # dictionary of max allowed resource objects
        self.maxAllowed = { }
        self.task=None
        self.env=env

    #def setTaskID(self, id):
    #    self.taskID=id
    def setTask(self, task):
        self.task=task

    def tryGenID(self):
        """Generate an ID if it doesn't already have one."""
        global seeded
        global seededLock
        with seededLock:
            if not seeded:
                random.seed(os.urandom(8))
                seeded=True
        # TODO: We should be using a cryptographically secure RNG for this.
        if self.id is None:
            self.id=hashlib.sha1("%x%x%x%x"%
                             (random.getrandbits(32),
                              random.getrandbits(32),
                              random.getrandbits(32),
                              random.getrandbits(32))).hexdigest()
    def getID(self):
        """Return the ID."""
        return self.id

    def addArg(self, arg):
        self.args.append(arg)
    def getArgs(self):
        return self.args
    def getArgStr(self):
        retstr=""
        for arg in self.args:
            retstr += "%s "%arg
        return retstr

    def addEnv(self, name, value):
        """Add a single environment variable."""
        if self.env is None:
            self.env=dict()
        self.env[name]=value

    def getEnv(self):
        """Get the dict of environment values (or None if none set)"""
        return self.env


    def getOutputFiles(self):
        """Get the list of all possible relevant output files this command 
           generates."""
        return self.outputFiles

    def addOutputFile(self, filename):
        """Add a file name to the list of output files that this command may
           generate. The file name is relative to the run directory, and 
           does not include the standard 'stdout' and 'stderr'"""
        if self.outputFiles is None:
            self.outputFiles=[]
        self.outputFiles.append(filename)

    def addFile(self, file):
        """Add a commandInputFile object"""
        self.files.append(file)

    def getFiles(self):
        """Get the file names"""
        return self.files
    #def addInput(self, input):
    #    self.inputs.append(input)
    #def getInputs(self):
    #    return self.inputs

    def setRunning(self, running, workerServer=None):
        """Set the command to a running (or not) state.
           running = boolean indicating the running state
           workerServer = the server name of the server the worker is 
                          connected to."""
        self.running=running
        if running:
            self.workerServer=workerServer
        else:
            self.workerServer=None

    def getRunning(self):
        """Return whether the command is running."""
        return self.running

    def getWorkerServer(self):
        """Get the server name of the server the worker is connected to."""
        if self.running:
            return self.workerServer
        else:
            return None

    def addCputime(self, cputime):
        """Add a number of cpu seconds used."""
        self.cputime += cputime

    def setCputime(self, cputime):
        """Set a number of cpu seconds used."""
        self.cputime = cputime

    def getCputime(self):
        """Return the amount of cpu seconds used for this command."""
        return self.cputime

    def addMinRequired(self, rsrc):
        """Add a single required resource.
           rsrc = the resource object"""
        self.minRequired[rsrc.name] = rsrc
    def getMinRequired(self, name):
        """Get the value for a required resource.
           returns: the resource object or None if it is not found."""
        if self.minRequired.has_key(name):
            return self.minRequired[name].value
        else:
            return None
    def getAllMinRequired(self):
        """Get the dict with all required resources."""
        return self.minRequired


    def addMaxAllowed(self, rsrc):
        """Add a single max. allowed resource.
           rsrc = the resource object"""
        self.maxAllowed[rsrc.name] = rsrc
    def getMaxAllowed(self, name):
        """Get the value for a max. allowed resource.
           returns: the resource object or None if it is not found."""
        if self.maxAllowed.has_key(name):
            return self.maxAllowed[name].value
        else:
            return None
    def getAllMaxAllowed(self):
        """Get the dict with all max. allowed resources."""
        return self.maxAllowed


    def resetReserved(self):
        """Reset the list of reserved resources from the required resources."""
        self.reserved=dict()
        for name, val in self.minRequired.iteritems():
            self.reserved[name]=val
    def addReserved(self, rsrc):
        """Add a resource to the reserved list."""
        self.reserved[rsrc.name] = rsrc
    def setReserved(self, name, value):
        """Add a resource to the reserved list."""
        rsrc=resource.Resource(name, value)
        self.reserved[name] = rsrc
    def getReserved(self, name):
        """Get the value for a reserved resource.
           returns: the resource object or None if it is not found."""
        if self.reserved.has_key(name):
            return self.reserved[name].value
        else:
            return None
    def hasReserved(self, name):
        return self.reserved.has_key(name)
    def joinReserved(self, other):
        """Join a reservation list from another command."""
        for (name, value) in other.reserved.iteritems():
            if self.reserved.has_key(name):
                self.reserved[name].add(value)
            else:
                self.reserved[name] = value


    def setTask(self, task):
        self.task=task
        #self.taskID=task.getID()
    def getTask(self):
        return self.task
    def getFullPriority(self):
        return self.task.priority + self.addPriority
    def increasePriority(self):
        self.addPriority += 1

    def _writeXML(self, outf, writeReservations, writeProject, indent=0):
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outf.write('%s<command executable="%s"'%(indstr, self.executable))
        if self.id is not None:
            outf.write(' id="%s"'%self.id)
        if writeProject:
            outf.write(' task_id="%s"'%(self.task.getID()))
            if self.running:
                outf.write(' running="yes"')
                if self.workerServer is not None:
                    outf.write(' worker_server="%s"'%self.workerServer)
            else:
                outf.write(' running="no"')
        if self.dir is not None:
            outf.write(' dir="%s"'%self.dir)
        if self.addPriority!=0:
            outf.write(' add_priority="%d"'%self.addPriority)
        if self.minVersion is not None:
            outf.write(' min_version="%s"'%self.minVersion.getStr())
        if self.maxVersion is not None:
            outf.write(' max_version="%s"'%self.maxVersion.getStr())
        if self.cputime > 0:
            outf.write(' used_cpu_time="%d"'%self.cputime)
        outf.write('>\n')
        for arg in self.args:
            outf.write('%s<arg value="%s"/>\n'%(iindstr, arg))
        #for input in self.inputs:
        #    input.writeXML(outf)
        # required resources
        if self.env is not None:
            for name, value in self.env.iteritems():
                outf.write('%s<env name="%s" value="%s"/>\n'%(iindstr, name, 
                                                              value))
        if self.outputFiles is not None:
            for name in self.outputFiles:
                outf.write('%s<output_file name="%s"/>\n'%(iindstr, name))
        outf.write('%s<min-required>\n'%iindstr)
        for rsrc in self.minRequired.itervalues():
            rsrc.writeXML(outf, indent+2)
        outf.write('%s</min-required>\n'%iindstr)
        # max.allowed resources
        outf.write('%s<max-allowed>\n'%iindstr)
        for rsrc in self.maxAllowed.itervalues():
            rsrc.writeXML(outf, indent+2)
        outf.write('%s</max-allowed>\n'%iindstr)
        # reserved resources
        outf.write('%s<reserved>\n'%iindstr)
        for rsrc in self.reserved.itervalues():
            rsrc.writeXML(outf, indent+2)
        outf.write('%s</reserved>\n'%iindstr)
        outf.write('%s</command>\n'%indstr)

    def writeXML(self, outf, indent=0):
        """Write an XML description of the command to the file outf.
           This XML is for the controller."""
        self._writeXML(outf, writeReservations=False, writeProject=True, 
                       indent=indent)

    def toJSON(self):
        commandDict = dict()        
        #commandDict['projectID'] = self.projectID
        commandDict['taskID'] = self.task.getID()
        commandDict['id'] = self.id
        commandDict['executable'] = self.executable
        commandDict['priority'] = self.getFullPriority()
        #commandDict['dir'] = os.path.join(self.task.dir, self.dir)
        commandDict['dir'] = self.dir
        if self.cputime > 0:
            commandDict['used-cpu-time'] = self.cputime
        return commandDict

    def writeWorkerXML(self, outf):
        """Write an XML description of the command to the file outf.
           If restriction==True, it won't write project and task information."""
        self._writeXML(outf, writeReservations=True, writeProject=False, 
                       indent=0)


class CommandReaderError(cpc.util.CpcXMLError):
    pass

class CommandReader(xml.sax.handler.ContentHandler):
    """XML reader for commands."""
    def __init__(self):
        self.commands=[]
        self.curCommand=None
        self.inMinRequired=False
        self.inMaxAllowed=False
        self.inReserved=False
        self.resourceReader=None
        self.loc=None

    def getCommands(self):
        return self.commands

    def resetCommands(self):
        """reset the commands array to make enable object re-use."""
        self.commands=[]
        self.curCommand=None

    def read(self, filename):
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

    def startElement(self, name, attrs):
        if self.inMinRequired or self.inReserved or self.inMaxAllowed:
            self.resourceReader.startElement(name, attrs)
        elif name == 'command-list':
            pass # ignore
        elif name == 'command':
            if self.curCommand is not None:
                raise CommandReaderError("second command in reader", self.loc)
            #projectID=None
            #taskID=None
            dir=None
            id=None
            workerServer=None
            cputime=0
            if attrs.has_key('id'):
                id=attrs.getValue('id')
            #if attrs.has_key('project_id'):
            #    projectID=attrs.getValue('project_id')
            #if attrs.has_key('task_id'):
            #    taskID=attrs.getValue('task_id')
            if attrs.has_key('dir'):
                dir=attrs.getValue('dir')
            if attrs.has_key('worker_server'):
                workerServer=attrs.getValue('worker_server')
            if not attrs.has_key('executable'):
                raise CommandReaderError("command has no executable", self.loc)
            if attrs.has_key('used_cpu_time'):
                cputime=float(attrs.getValue('used_cpu_time'))
            executable=attrs.getValue('executable')
            if attrs.has_key('add_priority'):
                try:
                    addPriority=int(attrs.getValue('add_priority'))
                except ValueError:
                    raise CommandReaderError("add_priority not a number", 
                                             self.loc)
            else:
                addPriority=0
            minVersion=None
            if attrs.has_key('min_version'):
                minVersion=version.Version(attrs.getValue('min_version'))
            maxVersion=None
            if attrs.has_key('max_version'):
                maxVersion=version.Version(attrs.getValue('max_version'))
            running=False
            if attrs.has_key('running'):
                if attrs.getValue('running') == "yes":
                    running=True
            self.curCommand=Command(dir, executable, [],
                                    addPriority, minVersion, maxVersion, 
                                    id=id, running=running, 
                                    workerServer=workerServer)
            if cputime > 0:
                self.setCputime(cputime)
        elif name == 'arg':
            if not attrs.has_key('value'):
                raise CommandReaderError("command argument has no value",
                                         self.loc)
            else:
                self.curCommand.addArg(attrs.getValue('value'))
        elif name == 'output_file':
            if not attrs.has_key('name'):
                raise CommandReaderError("output_file has no name", self.loc)
            self.curCommand.addOutputFile(attrs.getValue('name'))
        elif name == 'env':
            if not attrs.has_key('name'):
                raise CommandReaderError("environment variable has no name",
                                         self.loc)
            if not attrs.has_key('value'):
                raise CommandReaderError("environment variable has no value",
                                         self.loc)
            self.curCommand.addEnv(attrs.getValue('name'), 
                                   attrs.getValue('value'))
        elif name == "min-required":
            self.inMinRequired=True
            self.resourceReader=resource.ResourceReader()
        elif name == "max-allowed":
            self.inMaxAllowed=True
            self.resourceReader=resource.ResourceReader()
        elif name == "reserved":
            self.inReserved=True
            self.resourceReader=resource.ResourceReader()
        else:
            raise CommandReaderError("Unknown xml tag '%s'"%name, self.loc)

    def endElement(self, name):
        if self.inMinRequired:
            if name == "min-required":
                for rsrc in self.resourceReader.getResourceList():
                    self.curCommand.addMinRequired(rsrc)
                self.inMinRequired=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        if self.inMaxAllowed:
            if name == "max-allowed":
                for rsrc in self.resourceReader.getResourceList():
                    self.curCommand.addMaxAllowed(rsrc)
                self.inMaxAllowed=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        elif self.inReserved:
            if name == "reserved":
                for rsrc in self.resourceReader.getResourceList():
                    self.curCommand.addReserved(rsrc)
                self.inReserved=False
                self.resourceReader=None
            else:
                self.resourceReader.endElement(name)
        elif name == 'command':
            self.commands.append(self.curCommand)
            self.curCommand=None


