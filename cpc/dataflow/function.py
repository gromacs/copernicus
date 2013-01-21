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



#import logging


import collections

#log=logging.getLogger('cpc.dataflow.function')


import cpc.util
import apperror
import keywords
import description
import value
import function_io
import vtype
import run

class FunctionError(apperror.ApplicationError):
    pass

class FunctionState(object):
    """Class describing a function state. Instantiated as static objects in 
       the Function class."""
    def __init__(self, name):
        self.name=name
    def __str__(self):
        return self.name

class Function(description.Describable):
    """The class describing a function. A function is a single 
       computational unit in a dataflow network. It can consist of either 
       a controller with input and output definitions, or of a function graph.
       """
    # this class is an abstract base class

    ok=FunctionState("ok")
    error=FunctionState("error")

    def __init__(self, name, lib=None):
        """Initializes a function.

           input = list of input items
           output = list of output items
        """
        self.name=name

        # the I/O items are types (lists)
        self.inputs=vtype.RecordType("%s:in"%self.name, 
                                     vtype.recordType, lib=lib)
        self.outputs=vtype.RecordType("%s:out"%self.name, 
                                      vtype.recordType, lib=lib)
        self.subnetInputs=vtype.RecordType("%s:sub_in"%self.name, 
                                           vtype.recordType, lib=lib)
        self.subnetOutputs=vtype.RecordType("%s:sub_out"%self.name, 
                                            vtype.recordType, lib=lib)
        self.inputs.markImplicit()
        self.outputs.markImplicit()
        self.subnetInputs.markImplicit()
        self.subnetOutputs.markImplicit()

        self.genTasks=True # whether to generate tasks based on this function
                           # NetworkFunctions, for example, have no tasks
        self.log=False # whether the function wants to log output

        # whether an output dir is needed despite having no input/output files
        self.outputDirWithoutFiles=False
        self._checkOutputDirNeeded()
        # whether a persistent scratch directory is needed
        self.persistentDir=False
        # whether the current (subnet)outputs are given to the task when 
        # it is executed
        self.taskAccessOutputs=False
        self.taskAccessSubnetOutputs=False
        #self.importLib=None
        self.state=Function.ok
        self.stateMsg=""
        if lib is not None:
            self.setLib(lib)
        description.Describable.__init__(self)

    def getName(self):
        """Returns the function's name."""
        return self.name

    def getFullName(self):
        """Return the function's full name."""
        if self.lib is not None and self.lib.getName() != "":
            return "%s%s%s"%(self.lib.getName(), keywords.ModSep, self.name)
        else:
            return self.name

    def setLib(self, lib):
        """Set the function's library."""
        self.lib=lib
        lib.addType(self.inputs)
        lib.addType(self.outputs)
        lib.addType(self.subnetInputs)
        lib.addType(self.subnetOutputs)
        self.inputs.setLib(lib)
        self.outputs.setLib(lib)
        self.subnetInputs.setLib(lib)
        self.subnetOutputs.setLib(lib)

    def getLib(self):
        """Get the function's library."""
        return self.lib

    #def getSelf(self):
    #    """Get the 'self' object, if it exists. None, otherwise."""
    #    return None

    def getState(self):
        """Get the state of the function."""
        return self.state

    def hasLog(self):
        """Return whether this function has a log."""
        return self.log
    def setLog(self, log):
        """Set whether this function has a log."""
        self.log=log
        self._checkOutputDirNeeded()


    def accessOutputs(self):
        """Return whether we want to give the current outputs to tasks""" 
        return self.taskAccessOutputs
    def accessSubnetOutputs(self):
        """Return whether we want to give the current outputs to tasks""" 
        return self.taskAccessSubnetOutputs
    def setAccessOutputs(self, use):
        """Set whether we want to give the current outputs to tasks""" 
        self.taskAccessOutputs=use
    def setAccessSubnetOutputs(self, use):
        """Set whether we want to give the current outputs to tasks""" 
        self.taskAccessSubnetOutputs=use

    def getStateMsg(self):
        """Get the state message (in case of error) of the function."""
        return self.stateMsg

    def check(self):
        """Perform a check on whether the function can run and set
           the state to reflect this."""
        self.stateMsg=""
        self.state=Function.ok

    def setOutputDirWithoutFiles(self, val):
        """Set whether there should be a run directory even if there's no
           output files.

           val =  a boolean
           """
        self.outputDirWithoutFiles=val
        self._checkOutputDirNeeded()



    def getInputs(self):
        """Get a the type of all inputs."""
        return self.inputs

    def getOutputs(self):
        """Get a the type of all outputs."""
        return self.outputs

    def getSubnetInputs(self):
        """Get a the type of all subnet inputs."""
        return self.subnetInputs

    def getSubnetOutputs(self):
        """Get a the type of all subnet outputs."""
        return self.subnetOutputs

    def getSubnet(self):
        """Return a subnetwork associated with this function, or None."""
        return None

    def _checkOutputDirNeeded(self):
        if self.outputDirWithoutFiles or self.log:
            self._outputDirNeeded=True
            return 
        # set to true if the outputs/subnetOutputs contain files
        if self.outputs.containsBasetype(vtype.fileType):
            self._outputDirNeeded=True
            return
        if self.subnetOutputs.containsBasetype(vtype.fileType):
            self._outputDirNeeded=True
            return
        self._outputDirNeeded=False

    def outputDirNeeded(self):
        """Returns  whether an output directory is needed."""
        self._checkOutputDirNeeded()
        return self._outputDirNeeded

    def setPersistentDir(self, val):
        """Set whether a persistent scratch dir is needed."""
        self.persistentDir=val
    def persistentDirNeeded(self):
        """Return whether a persistance scratch storage directory is needed."""
        return self.persistentDir

    def _writeInputOutputXML(self, outf, indent=0):
        """Describe the inputs and outputs"""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        if self.desc is not None:
            self.desc.writeXML(outf, indent)
        if self.inputs.hasMembers():
            outf.write('%s<inputs>\n'%indstr)
            self.inputs.writePartsXML(outf, indent+1)
            outf.write('%s</inputs>\n'%indstr)
        if self.outputs.hasMembers():
            outf.write('%s<outputs>\n'%indstr)
            self.outputs.writePartsXML(outf, indent+1)
            outf.write('%s</outputs>\n'%indstr)
        if self.subnetInputs.hasMembers():
            outf.write('%s<subnet-inputs>\n'%indstr)
            self.subnetInputs.writePartsXML(outf, indent+1)
            outf.write('%s</subnet-inputs>\n'%indstr)
        if self.subnetOutputs.hasMembers():
            outf.write('%s<subnet-outputs>\n'%indstr)
            self.subnetOutputs.writePartsXML(outf, indent+1)
            outf.write('%s</subnet-outputs>\n'%indstr)

    def writeXML(self, outFile, indent=0):
        """Describe the fucntion in XML."""
        pass

    def run(self, fnInput):
        """Run a function. Return a dict of outputs as Value objects, a 
           command to be queued, or None.
          
           fnInput = a run.FunctionRunInput object. 
           returns: a run.FunctionRunOutput object. 
           """
        return run.FunctionRunOutput()


class ConstFunction(Function):
    """A function that holds a constant value."""
    def __init__(self, name, tp, value, lib):
        """Initializes a const function.

           type = a const type
           value = its value
        """
        self.type=tp
        self.value=value
        inputs=[]
        outputs=[ function_io.FunctionOutput("val", tp)  ]
        Function.__init__(self, "const", inputs, outputs)
        self.genTasks=False

    def writeXML(self, outFile, indent=0):
        """The function itself does not need to be described."""
        pass

    def run(self, fnInput):
        """Run the const function, returning the value."""
        return run.FunctionRunOutput( 
                      outputs={ "val" : value.Value(self.value, self.type) })

