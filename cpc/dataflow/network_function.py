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



import logging


log=logging.getLogger('cpc.dataflow.function')


import cpc.util
import apperror
import keywords
import instance
import function
import network

class NetworkFunctionError(apperror.ApplicationError):
    pass

class SelfFunction(function.Function):
    """A pseudo-funciton describing a function network's inputs and outputs
       This is the only function type that can connect inputs to subnetOutputs
       and outputs to subnetInputs. This is the function named 'self' in 
       each subnet"""

    #"""A pseudo-function describing a function network's inputs or outputs.
    #   This reverses the function network's encapsulating function's inputs
    #   and outputs for internal use in the network (because a function 
    #   network's outputs are inputs from the network's point of view, and 
    #   vice versa)
    #   """
    def __init__(self, inFunction):
        """Initialize based on externally visible NetworkFunction object."""
        function.Function.__init__(self, keywords.Self, [], [])
        self.name=keywords.Self # this is its name
        self.function=inFunction # the parent function
        self.genTasks=False

class SelfInstance(instance.Instance):
    """An instance specifically for the 'self' object."""
    def __init__(self, fn):
        instance.Instance.__init__(self, keywords.Self, fn, keywords.Self)

class NetworkedFunction(function.Function):
    """Base class of functions that have internal networks. 
       """
    def __init__(self, name, lib=None):
        """Initializes a networked function."""
        function.Function.__init__(self, name, lib)

        self.network=network.Network(self)
        # This is almost a palindrome:
        self.selfInstance=SelfInstance(self)
        self.network.addInstance(self.selfInstance)

    def getSelf(self):
        return self.selfInstance

    #def addSubnetInput(self, ioitem):
    #    """Add a single subnet input item to the list of subnet inputs.
    #       A subnet input is a function input connected to an output in 
    #       an internal network visible only to the function."""
    #    if ioitem.getName() in self.subnetInputs:
    #        raise NetworkFunctionError(
    #                          "Subnet input %s already exists in function %s"%
    #                          (ioitem.getName(), self.name) )
    #    self.subnetInputs[ioitem.getName()]=ioitem
    #    self._checkOutputDirNeeded()

    #def addSubnetOutput(self, ioitem):
    #    """Add a single output item to the list of outputs."""
    #    if ioitem.getName() in self.subnetOutputs:
    #        raise NetworkFunctionError(
    #                        "Subnet output %s already exists in function %s"%
    #                        (ioitem.getName(), self.name) )
    #    self.subnetOutputs[ioitem.getName()]=ioitem
    #    self._checkOutputDirNeeded()

    def getSelf(self):
        """Get the self instance."""
        return self.selfInstance

    def getSubnet(self):
        return self.network

class NetworkFunction(NetworkedFunction):
    """A function that consists of purely of function instances in a 
       function graph.
       
       In a NetworkFunction, the inputs are directly connected to
       subnetOutputs, and subnetInputs are connected to outputs."""
    def __init__(self, name, lib=None):
        """Initializes a network function.
           input = list of input items
           output = list of output items """
        NetworkedFunction.__init__(self, name, lib)
        self.genTasks=False

    #def addInput(self, ioitem):
    #    """Add an input, and a corresponding subnetOutput and its connection.
    #       """
    #    function.Function.addInput(self, ioitem)
    #    # make a copy for the corresponding subnet output
    #    ioitemCopy=function_io.FunctionOutput(ioitem.getName(),
    #                                          ioitem.getType(), True)
    #    ioitemCopy.markImplicit()
    #    NetworkedFunction.addSubnetOutput(self, ioitemCopy)
    #    conn=connection.Connection(self.selfInstance, ioitem, [],
    #                               self.selfInstance, ioitemCopy, [], None)
    #    conn.markImplicit()
    #    self.network.addConnection(conn)

    #def addOutput(self, ioitem):
    #    """Add an output, and a corresponding subnetInput and its connection.
    #       """
    #    function.Function.addOutput(self, ioitem)
    #    # make a copy for the corresponding subnet input. 
    #    # function inputs are always opt and var
    #    ioitemCopy=function_io.FunctionInput(ioitem.getName(),
    #                                         ioitem.getType(),
    #                                         True, True, True)
    #    ioitemCopy.markImplicit()
    #    NetworkedFunction.addSubnetInput(self, ioitemCopy)
    #    conn=connection.Connection(self.selfInstance, ioitemCopy, [],
    #                               self.selfInstance, ioitem, [], None)
    #    conn.markImplicit()
    #    self.network.addConnection(conn)

    #def addSubnetInput(self, ioitem):
    #    """This should never happen."""
    #    raise NetworkFunctionError(
    #           "Tried to directly create a subnet input in a NetworkFunction.")

    #def addSubnetOutput(self, ioitem):
    #    """This should never happen."""
    #    raise NetworkFunctionError(
    #          "Tried to directly create a subnet output in a NetworkFunction.")
    
    def writeXML(self, outFile, indent=0):
        indstr=cpc.util.indStr*indent
        outFile.write('%s<function id="%s" type="network">\n'%
                      (indstr,self.name))
        self._writeInputOutputXML(outFile, indent+1)
        self.network.writeXML(outFile, indent+1)
        outFile.write('%s</function>\n'%indstr)


