# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This file is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301   
# USA 

import logging
import os
import os.path
import xml.sax
import stat
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

log=logging.getLogger('cpc.dataflow.run')

import cpc.util
import apperror
import keywords
import value
import vtype
import cpc.command


class FunctionRunError(apperror.ApplicationError):
    pass

curVersion=1


def readInput(inputFile=sys.stdin, name="stdin"):
    """Read input from stdin and parse it into a FunctionRunInput object."""
    inp=FunctionRunInput()
    reader=IOReader(inp, None)
    reader.read(inputFile, name)
    return inp

class FunctionRunInput(object):
    """Class describing the inputs of a function.
       
        Its readable member variables are:
        inputs (a Value object, or None)
        subnetInputs (a Value object, or None)
        cmd (a Command that has just finished, or None)
        outputDir (a string holding the output directory, or None)
        persistentDir (a string holding the persistent directory, or None)"""
    def __init__(self, inputs=None, subnetInputs=None, 
                 outputs=None, subnetOutputs=None,
                 outputDir=None, persistentDir=None, cmd=None,
                 fn=None, activeInstance=None, project=None):
        self.inputs=inputs
        self.subnetInputs=subnetInputs
        self.outputs=outputs
        self.subnetOutputs=subnetOutputs
        self.outputDir=outputDir
        self.persistentDir=persistentDir
        self.cmd=cmd
        self.function=fn
        self.activeInstance=activeInstance
        self.project=project
        if self.project is not None:
            self.baseDir=project.getBasedir()
        else:
            self.baseDir=None
        self.fo=None

    def testing(self):
        return self.inputs is None

    # inputs
    def hasInput(self, itemname):
        """Check whether a particular input exists"""
        items=vtype.parseItemList(itemname)
        return self.inputs.hasSubValue(items)
    def getInput(self, itemname):
        """Get the actual value associated with an input."""
        items=vtype.parseItemList(itemname)
        retv=self.inputs.getSubValue(items)
        if retv is None:
            return None
        if retv is not None and retv.fileValue is not None:
            return retv.fileValue.getAbsoluteName()
        else:
            # if we're running in an external function, the current directory
            # is the base dir, so we don't need to distinguish between them
            if retv.value is not None and retv.type.isSubtype(vtype.fileType):
                return os.path.join(self.baseDir, retv.value)
            else:
                return retv.value
    def getInputValue(self, itemname):
        """Get the Value object associated with an input."""
        items=vtype.parseItemList(itemname)
        retv=self.inputs.getSubValue(items)
        return retv

    def getInputNames(self):
        return vtype.parseItemList(" ")
    def isInputUpdated(self, itemname):
        """Check whether a particular subnet input has been updated."""
        items=vtype.parseItemList(itemname)
        retv=self.inputs.getSubValue(items)
        if retv is None:
            return False
        return retv.isUpdated()

    # subnet inputs
    def hasSubnetInput(self, itemname):
        """Check whether a particular input exists"""
        items=vtype.parseItemList(itemname)
        return self.subnetInputs.hasSubValue(items)
    def getSubnetInput(self, itemname):
        """Get the actual value associated with a subnet input."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetInputs.getSubValue(items)
        if retv is None:
            return None
        if retv.fileValue is not None:
            return retv.fileValue.getAbsoluteName()
        else:
            # if we're running in an external function, the current directory
            # is the base dir, so we don't need to distinguish between them
            if retv.value is not None and retv.type.isSubtype(vtype.fileType):
                return os.path.join(self.baseDir, retv.value)
            else:
                return retv.value
            #return retv.value
    def getSubnetInputValue(self, itemname):
        """Get the Value object associated with an input."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetInputs.getSubValue(items)
        return retv
    def isSubnetInputUpdated(self, itemname):
        """Check whether a particular subnet input has been updated."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetInputs.getSubValue(items)
        if retv is None:
            return False
        return retv.isUpdated()
 
    # outputs
    def hasOutput(self, itemname):
        """Check whether a particular output exists"""
        items=vtype.parseItemList(itemname)
        if self.outputs is None:
            return False
        return self.outputs.hasSubValue(items)
    def getOutput(self, itemname):
        """Get the actual value associated with an output."""
        items=vtype.parseItemList(itemname)
        retv=self.outputs.getSubValue(items)
        if retv is None:
            return None
        if retv is not None and retv.fileValue is not None:
            return retv.fileValue.getAbsoluteName()
        else:
            # if we're running in an external function, the current directory
            # is the base dir, so we don't need to distinguish between them
            return retv.value
    def getOutputValue(self, itemname):
        """Get the Value object associated with an input."""
        items=vtype.parseItemList(itemname)
        retv=self.outputs.getSubValue(items)
        return retv
    def isOutputUpdated(self, itemname):
        """Check whether a particular subnet output has been updated."""
        items=vtype.parseItemList(itemname)
        retv=self.outputs.getSubValue(items)
        if retv is None:
            return False
        return retv.isUpdated()

    # subnet outputs
    def hasSubnetOutput(self, itemname):
        """Check whether a particular output exists"""
        items=vtype.parseItemList(itemname)
        if self.subnetOutputs is None:
            return False
        return self.subnetOutputs.hasSubValue(items)
    def getSubnetOutput(self, itemname):
        """Get the actual value associated with a subnet output."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetOutputs.getSubValue(items)
        if retv is None:
            return None
        if retv.fileValue is not None:
            return retv.fileValue.getAbsoluteName()
        else:
            # if we're running in an external function, the current directory
            # is the base dir, so we don't need to distinguish between them
            return retv.value
    def getSubnetOutputValue(self, itemname):
        """Get the Value object associated with an input."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetOutputs.getSubValue(items)
        return retv
    def isSubnetOutputUpdated(self, itemname):
        """Check whether a particular subnet output has been updated."""
        items=vtype.parseItemList(itemname)
        retv=self.subnetOutputs.getSubValue(items)
        if retv is None:
            return False
        return retv.isUpdated()
 

    def getBaseDir(self):
        """Get the project's basedir."""
        return self.baseDir

    def getPersistentDir(self):
        """Get the persistence directory"""
        if self.persistentDir is None:
            return None
        if not os.path.isabs(self.persistentDir): 
            return os.path.join(self.baseDir, self.persistentDir)
        else:
            return self.persistentDir


    def getOutputDir(self):
        """Get the output directory"""
        if self.outputDir is None:
            return None
        if not os.path.isabs(self.outputDir): 
            return os.path.join(self.baseDir, self.outputDir)
        else:
            return self.outputDir

    def getCmd(self):
        """Get the command."""
        return self.cmd

    def setMissing(self, activeInstance, project):
        """Set an actual instance and project. For use by readxml"""
        self.activeInstance=activeInstance
        self.function=self.activeInstance.getFunction()
        self.project=project
        if self.project is not None:
            self.baseDir=project.getBasedir()
            if ( self.persistentDir is not None and 
                 os.path.isabs(self.persistentDir)) : 
                self.persistentDir=os.path.relpath(self.persistentDir,
                                                   self.baseDir)
            if ( self.outputDir is not None and 
                 os.path.isabs(self.outputDir)) : 
                self.outputDir=os.path.relpath(self.outputDir,
                                               self.baseDir)
 
    def destroy(self):
        """Destroy all file object refs associated with this task."""
        if self.inputs is not None:
            self.inputs.destroy()
        if self.subnetInputs is not None:
            self.subnetInputs.destroy()

    def setFunctionRunOutput(self, fo):
        """Set a specific FunctionRunOutput object."""
        self.fo=fo

    def getFunctionOutput(self):
        """Create a functionrunoutput object, possibly based on information
           read in with this object."""
        if self.fo is None:
            self.fo=FunctionRunOutput()
        return self.fo

    def setFunctionRunOutput(self, fo):
        """Set a specific FunctionRunOutput object."""
        self.fo=fo

    def _writeXML(self, outf, writeState, indent=0):
        """Write the contents of this object in XML form to a file."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outf.write('%s<function-input version="%d">\n'%(indstr,curVersion))
        # write the inputs
        outf.write('%s<env '%iindstr)
        if self.outputDir is not None:
            outf.write(' output_dir="%s"'%self.outputDir)
        if self.persistentDir is not None:
            outf.write(' persistent_dir="%s"'%self.persistentDir)
        if not writeState:
            if self.baseDir is not None:
                outf.write(' base_dir="%s"'%self.baseDir)
        outf.write('/>\n')
        if self.inputs is not None:
            outf.write('%s<inputs>\n'%iindstr)
            self.inputs.writeContentsXML(outf, indent+3)
            outf.write('%s</inputs>\n'%iindstr)
        if self.subnetInputs is not None:
            outf.write('%s<subnet-inputs>\n'%iindstr)
            self.subnetInputs.writeContentsXML(outf, indent+2)
            outf.write('%s</subnet-inputs>\n'%iindstr)
        if self.outputs is not None:
            outf.write('%s<outputs>\n'%iindstr)
            self.outputs.writeContentsXML(outf, indent+3)
            outf.write('%s</outputs>\n'%iindstr)
        if self.subnetOutputs is not None:
            outf.write('%s<subnet-outputs>\n'%iindstr)
            self.subnetOutputs.writeContentsXML(outf, indent+2)
            outf.write('%s</subnet-outputs>\n'%iindstr)
        if self.cmd is not None:
            outf.write('%s<commands>\n'%iindstr)
            self.cmd.writeXML(outf, indent+2)
            outf.write('%s</commands>\n'%iindstr)
        outf.write('%s</function-input>\n'%indstr)

    def writeRunXML(self, outf, indent=0):
        self._writeXML(outf, False, indent)

    def writeStateXML(self, outf, indent=0):
        self._writeXML(outf, True, indent)

class FunctionRunOutput(object):
    """A class holding the output of a function's run method.
       
       Its readable and directly manipulable member variables are:
       - outputs (a list of OutputItem objects)
       - subnetOutputs (a list of OutputItem objects)
       - cmds (a list of Commands)
       - newInstances (a list of NewInstances)
       - newConnections (a list of NewConnections)
       """
    def __init__(self):
        """Initialize a run output (usually just before returning a run
           method). """
        # A list of OutputItem objects for outputs
        self.outputs=[]
        # A list of OutputItem objects for subnet outputs
        self.subnetOutputs=[]
        #cmds = a list of commands to queue
        self.cmds=None
        #newInstances = a list of new instances to spawn in the subnet
        self.newInstances=None
        #newConnections = a list of new connections to make in the subnet
        self.newConnections=None
        # whether to cancel all existing commands.
        self.cancelCmds=False

    def setOut(self, ioitem, outval):
        """Add a specified output value.
            ioitem = the full output specifier 
            outval = an OutValue (OutValue object) """
        if not isinstance(outval, value.Value):
            raise FunctionRunError(
                        "Output value for '%s' is not a Value object."%
                        (ioitem))
        oi=OutputItem(ioitem, outval) 
        self.outputs.append( oi )
        return oi
        #self.outputs.append( OutputItem(ioitem, outval) )

    def setSubOut(self, ioitem, outval):
        """Set a specified subnet output value.
            name = the output name
            outval = the output value (OutValue object) """
        if not isinstance(outval, value.Value):
            raise FunctionRunError(
                        "Subnet output value for '%s' is not a Value object."%
                        (ioitem))
        oi=OutputItem(ioitem, outval) 
        self.subnetOutputs.append( oi )
        return oi
        #self.subnetOutputs.append( OutputItem(ioitem, outval) )

    def hasOutputs(self):
        """Check whether there are outputs."""
        return (self.outputs is not None) and len(self.outputs)>0
    def hasSubnetOutputs(self):
        """Check whether there are subnet outputs."""
        return (self.subnetOutputs is not None) and len(self.subnetOutputs)>0

    def addInstance(self, instanceName, functionName):
        """Add a new subnet function instance to the list.
            instanceName  = the new instance's name
            functionName  = the new instance's function name"""
        # initialize if it doesn't exist
        if self.newInstances is None:
            self.newInstances=[]
        ni=NewInstance(instanceName, functionName)
        self.newInstances.append(ni)
        return ni
        #self.newInstances.append(NewInstance(instanceName, functionName))

    def addConnection(self, srcStr, dstStr, val=None):
        """Add a new subnet connection to the list.
            srcStr = the source as instance:out.item
            dstStr = the destination as instance:in.item
            val  = optional value instead of source"""
        # initialize if it doesn't exist
        if self.newConnections is None:
            self.newConnections=[]
        nc=NewConnection(srcStr, dstStr, val)
        self.newConnections.append(nc)
        return nc
        #self.newConnections.append(NewConnection(srcStr, dstStr, val))

    def addCommand(self, cmd):
        """Add a command to the list.
            cmd = the command object"""
        # initialize if it doesn't exist
        if self.cmds is None:
            self.cmds=[]
        self.cmds.append(cmd)

    def cancelPrevCommands(self):
        """Cancel any previous commands."""
        self.cancelCmds=True

    def writeXML(self, outf, indent=0):
        """Write the contents of this object in XML form to a file."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        iiindstr=cpc.util.indStr*(indent+2)
        outf.write('%s<function-output version="%d">\n'%(indstr,curVersion))
        # write the outputs
        if self.outputs is not None and len(self.outputs)>0:
            outf.write('%s<outputs>\n'%iindstr)
            for output in self.outputs:
                outf.write('%s<value id="%s">\n'%(iiindstr, output.name))
                output.val.writeXML(outf, indent+3)
                outf.write('%s</value>\n'%(iiindstr))
            outf.write('%s</outputs>\n'%iindstr)
        if self.subnetOutputs is not None and len(self.subnetOutputs)>0:
            outf.write('%s<subnet-outputs>\n'%iindstr)
            for output in self.subnetOutputs:
                outf.write('%s<value id="%s">\n'%(iiindstr, output.name))
                output.val.writeXML(outf, indent+3)
                outf.write('%s</value>\n'%(iiindstr))
            outf.write('%s</subnet-outputs>\n'%iindstr)
        if self.newInstances is not None and len(self.newInstances)>0:
            outf.write('%s<new-instances>\n'%iindstr)
            for instance in self.newInstances:
                instance.writeXML(outf, indent+2)
            outf.write('%s</new-instances>\n'%iindstr)
        if self.newConnections is not None and len(self.newConnections)>0:
            outf.write('%s<new-connections>\n'%iindstr)
            for conn in self.newConnections:
                conn.writeXML(outf, indent+2)
            outf.write('%s</new-connections>\n'%iindstr)
        if self.cmds is not None and len(self.cmds)>0 or self.cancelCmds:
            if self.cancelCmds:
                cancelStr='cancel_prev="1"'
            else:
                cancelStr=''
            outf.write('%s<commands %s>\n'%(iindstr, cancelStr))
            for cmd in self.cmds:
                self.cmd.writeXML(outf, indent+2)
            outf.write('%s</commands>\n'%iindstr)
        outf.write('%s</function-output>\n'%indstr)

class NewInstance(object):
    """A class describing a new instance for a function's subnet, as an 
       output of a function."""
    def __init__(self, instanceName, functionName):
        self.name=instanceName
        self.functionName=functionName
    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        outf.write('%s<instance id="%s" function="%s" />\n'%
                   (indstr, self.name, self.functionName))
    def describe(self, outf):
        """Print a description of this new instance to outf."""
        outf.write('Function instance of %s, named %s\n'%
                   (self.functionName, self.instanceName))

 
class NewConnection(object):
    """A class describing a new connection, as an output of a function."""
    def __init__(self, srcStr, dstStr, val=None):
        """Initialize based on srouce and destination strings, in the form
           of 
           instance_name:in/out/sub_in/sub_out.itemname[subItemname]
           that can be parsed with connection.splitIOName()

           either srcStr or val can have a value (i.e. not be None)

            srcStr = source item (or None)
            dstStr = source item
            val = IOItem for initial value (if srcStr is None), or None
           """
        self.srcStr=srcStr
        self.dstStr=dstStr
        self.val=val
        self.conn=None # used in transaction object
    def describe(self, outf):
        """Print a description of this new connection to outf."""
        outf.write('Connection from %s to %s\n'%(self.srcStr, self.dstStr))


    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        if self.val is None:
            outf.write('%s<connection src="%s" dst="%s" />\n'%
                       (indstr, self.srcStr, self.dstStr))
        else:
            outf.write('%s<connection value="%s" type="%s" dst="%s" />\n'%
                       (indstr, self.val.value, self.val.getType().getName(), 
                        self.dstStr))

       

class IOReaderError(apperror.ApplicationXMLError):
    def __init__(self, msg, reader):
        loc=reader.getLocator()
        if loc is not None:
            self.str = "%s (line %d, column %d): %s"%(reader.getFilename(),
                                                      loc.getLineNumber(),
                                                      loc.getColumnNumber(),
                                                      msg)
        else:
            self.str = "%s: %s"%(reader.getFilename(), msg)



class OutputItem:
    """Class to hold information about an output item:
       name = the full name of the output item
       val = the value
       destVal = (optional) the actual output subvalue as used by the server
       """
    def __init__(self, name, val, destVal=None):
        self.name=name
        self.val=val
        #self.item=None
        self.destVal=destVal

    def describe(self, outf):
        """Print a description of this outputItem to outf"""
        outf.write('Set %s to %s\n'%(self.name, self.val))

class BoolValue(value.Value):
    """OutValue for boolean objects."""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.boolType)
        self.value=val

class IntValue(value.Value):
    """OutValue for integers."""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.intType)
        self.value=val

class FloatValue(value.Value):
    """OutValue for floats."""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.floatType)
        self.value=val

class StringValue(value.Value):
    """OutValue for strings."""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.stringType)
        self.value=val

class FileValue(value.Value):
    """OutValue for files."""
    def __init__(self, val, fileList=None):
        """Assuming val is a valid filename."""
        value.Value.__init__(self, None, vtype.fileType)
        self.value=val
        if fileList is not None:
            if os.path.isabs(val):
                self.fileValue=fileList.getAbsoluteFile(val)
            else:
                self.fileValue=fileList.getFile(val)

class ArrayValue(value.Value):
    """OutValue for arrays. Assumes a list of Values"""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.arrayType)
        self.value=val

class DictValue(value.Value):
    """OutValue for arrays. Assumes a dict of Values"""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.dictType)
        self.value=val

class RecordValue(value.Value):
    """OutValue for records. Assumes a dict of Values"""
    def __init__(self, val):
        value.Value.__init__(self, None, vtype.recordType)
        if val is not None:
            self.value=val
        else:
            self.value=dict()
    def addItem(self, name, val):
        """Add a single item."""
        self.value[name] = val



class IOReader(xml.sax.handler.ContentHandler):
    """XML reader for external commands. Parses input and output generated by 
       ExternalFunction.run()."""
    # Section numbers
    none=0
    env=1
    inputs=2
    outputs=3
    subnetInputs=4
    subnetOutputs=5
    newInstances=6
    newConnections=7
    cmd=8

    def __init__(self, functionRunInput, functionRunOutput):
        """Initialize based on whether the reader is for input or output."""
        #self.isInput=isInput
        self.commands=[]
        self.cmdReader=None
        self.cmdReaderEndTag=None
        # and internal stuff
        self.section=IOReader.none
        self.valueReader=None
        self.valueReaderEndTag=None
        self.valueName=None
        self.inp=functionRunInput
        self.out=functionRunOutput
        self.loc=None
        if self.inp is None:
            if self.out is None:
                raise IOReaderError("IOReader is neither input nor output", 
                                    self)
            self.isInput=False
        else:
            if self.out is not None:
                raise IOReaderError("IOReader is both input nor output", self)
            self.isInput=True

    def setCmdReader(self, cmdReader, endTag):
        self.curCmdReader=cmdReader
        self.curCmdReaderEndTag=endTag
        if cmdReader is not None:
            cmdReader.setDocumentLocator(self.loc)

    def setValueReader(self, valueReader, endTag):
        self.valueReader=valueReader
        self.valueReaderEndTag=endTag
        if valueReader is not None:
            valueReader.setDocumentLocator(self.loc)

    def setReportFilename(self, reportFilename):
        self.filename=reportFilename

    def read(self, file, reportFilename):
        """Read a file object with input items. reportFilename is used for error
           messages."""
        self.filename=reportFilename
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        #inf=open(file, 'r')
        parser.parse(file)
        #inf.close()

    def getFilename(self):
        return self.filename
    def getLocator(self):
        return self.loc


    def getFunctionRunInput(self):
        return self.inp
    def getFunctionRunOutput(self):
        return self.out

    def setDocumentLocator(self, locator):
        self.loc=locator
        if self.cmdReader is not None:
            self.cmdReader.setDocumentLocator(locator)

    def startElement(self, name, attrs):
        if self.valueReader is not None:
            self.valueReader.startElement(name, attrs)
            return
        elif self.cmdReader is not None:
            self.cmdReader.startElement(name, attrs)
            return
        # otherwise
        elif name=="function-input":
            # the top-level input tag
            if not self.isInput:
                raise IOReaderError("Misplaced controller-input tag", self)
            if attrs.has_key("version"):
                self.fileVersion=int(attrs.getValue("version"))
            else:
                self.fileVersion=0
            if self.fileVersion > curVersion:
                raise IOReaderError("function-input is from the future (%d)"%
                                    self.fileVersion, self)
        if name=="function-output":
            # the return top-level tag
            if self.isInput:
                raise IOReaderError("Misplaced controller-output tag", self)
            if attrs.has_key("version"):
                self.fileVersion=int(attrs.getValue("version"))
            else:
                self.fileVersion=0
            if self.fileVersion > curVersion:
                raise IOReaderError("function-output is from the future (%d)"%
                                    self.fileVersion, self)
        elif name == "env":
            if (self.section != IOReader.none) or not self.isInput:
                raise IOReaderError("Misplaced env tag", self)
            self.section=IOReader.env
            if attrs.has_key('output_dir'):
                self.inp.outputDir=attrs.getValue('output_dir')
            if attrs.has_key('persistent_dir'):
                self.inp.persistentDir=attrs.getValue('persistent_dir')
            if attrs.has_key('base_dir'):
                self.inp.baseDir=attrs.getValue('base_dir')
        elif name == "inputs":
            if (self.section != IOReader.none) or not self.isInput:
                raise IOReaderError("Misplaced inputs tag", self)
            self.section=IOReader.inputs
            val=value.Value(None, vtype.recordType)
            self.setValueReader(value.ValueReader(self.filename, val,
                                                  allowUnknownTypes=True), name)
        elif name == "subnet-inputs":
            if (self.section != IOReader.none) or not self.isInput:
                raise IOReaderError("Misplaced subnet-inputs tag", self)
            self.section=IOReader.subnetInputs
            val=value.Value(None, vtype.recordType)
            self.setValueReader(value.ValueReader(self.filename, val,
                                                  allowUnknownTypes=True), name)
        elif name == "outputs":
            if (self.section != IOReader.none) :
                raise IOReaderError("Misplaced outputs tag", self)
            self.section=IOReader.outputs
            if self.isInput:
                # read it in as a value
                val=value.Value(None, vtype.recordType)
                self.setValueReader(value.ValueReader(self.filename, val,
                                                      allowUnknownTypes=True), 
                                    name)

        elif name == "subnet-outputs":
            if (self.section != IOReader.none) :
                raise IOReaderError("Misplaced subnet-outputs tag", self)
            self.section=IOReader.subnetOutputs
            if self.isInput:
                # read it in as a value
                val=value.Value(None, vtype.recordType)
                self.setValueReader(value.ValueReader(self.filename, val,
                                                      allowUnknownTypes=True), 
                                    name)
        elif name == "new-instances":
            if (self.section != IOReader.none) or self.isInput:
                raise IOReaderError("Misplaced new-instances tag", 
                                       self)
            self.section=IOReader.newInstances
        elif name == "new-connections":
            if (self.section != IOReader.none) or self.isInput:
                raise IOReaderError("Misplaced new-connections tag", self)
            self.section=IOReader.newConnections
        elif name == "commands":
            if (self.section != IOReader.none): 
                raise IOReaderError("Misplaced commands tag", self)
            self.section=IOReader.cmd
            cancel=cpc.util.getBooleanAttribute(attrs,"cancel_prev")
            if cancel:
                if self.out is not None:
                    self.out.cancelPrevCommands()
                else:
                    raise IOReaderError("Can't cancel commands in input", self)
            if self.cmdReader is not None:
                self.cmdReader=cpc.command.CommandReader()
        elif name == "value":
            if not attrs.has_key('id'):
                raise IOReaderError("no id for value", self)
            self.valueName=id=attrs.getValue("id")
            # TODO: handle compound types
            #val=value.Value(None, vtype.valueType)
            self.setValueReader(value.ValueReader(self.filename, None, 
                                                  implicitTopItem=False,
                                                  allowUnknownTypes=True), name)
        elif name == "instance":
            if not attrs.has_key('id'):
                raise IOReaderError("instance has no id", self)
            if not attrs.has_key('function'):
                raise IOReaderError("instance has no function", self)
            name=attrs.getValue('id')
            fn=attrs.getValue('function')
            if self.section == IOReader.newInstances:
                self.out.addInstance(name, fn)
            else:
                raise IOReaderError("Misplaced instance tag", self)
        elif name == "connection":
            if not attrs.has_key('src') and not attrs.has_key('value'):
                raise IOReaderError("connection has no src or value", self)
            if not attrs.has_key('dst'):
                raise IOReaderError("connection has no dst", self)
            if self.section != IOReader.newConnections:
                raise IOReaderError("Misplaced connection tag", self)
            if attrs.has_key('src'):
                self.out.addConnection(attrs.getValue('src'),
                                       attrs.getValue('dst'))
            else:
                if not attrs.has_key('type'):
                    raise IOReaderError("connection has no type", self)
                tpname=attrs.getValue('type')
                if ( (tpname not in vtype.basicTypes) or 
                     vtype.basicTypes[tpname].isCompound() ):
                    raise IOReaderError(
                                "Value connection with non-basic type %s"%
                                tpname,self)
                tp=vtype.basicTypes[tpname]
                val=value.interpretLiteral(attrs.getValue('value'), tp)
                self.out.addConnection(None, attrs.getValue('dst'), val)

    def endElement(self, name):
        if self.valueReader is not None:
            if name == self.valueReaderEndTag:
                if self.isInput:
                    if name == "inputs":
                        self.inp.inputs=self.valueReader.value
                        self.section=IOReader.none
                    elif name == "subnet-inputs":
                        self.inp.subnetInputs=self.valueReader.value
                        self.section=IOReader.none
                    elif name == "outputs":
                        self.inp.outputs=self.valueReader.value
                        self.section=IOReader.none
                    elif name == "subnet-outputs":
                        self.inp.subnetOutputs=self.valueReader.value
                        self.section=IOReader.none
                else:
                    if name == "value":
                        if self.section==IOReader.outputs:
                            self.out.setOut(self.valueName, 
                                            self.valueReader.value)
                        elif self.section==IOReader.subnetOutputs:
                            self.out.setSubOut(self.valueName, 
                                               self.valueReader.value)
                        else:
                            raise IOReaderError("Wrong section for value",self)
                    self.valueName=None
                self.setValueReader(None, None)
            else:
                self.valueReader.endElement(name)
        elif self.cmdReader is not None:
            if name == self.cmdReaderEndTag:
                self.commands=extend(self.cmdReader.getCommands())
                self.cmdReader.resetCommnands()
                self.setCmdReader(None, None)
                self.section=IOReader.none
                if self.isInput:
                    self.inp.cmd=commands[0]
                else:
                    self.out.cmds=commands
            else:
                self.cmdReader.endElement(name)
        elif (name == "inputs" or 
              name == "outputs" or 
              name == "subnet-inputs" or 
              name == "subnet-outputs" or
              name == "new-instances" or 
              name == "new-connections" or
              name == "env"):
            self.section=IOReader.none


