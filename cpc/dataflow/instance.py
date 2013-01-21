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

log=logging.getLogger('cpc.dataflow.instance')


import cpc.util
import apperror
import keywords
import connection
import function
import function_io

class InstanceError(apperror.ApplicationError):
    pass



class Instance(object):
    """The class describing a function instance in a function network. 
       An instance is a connected function in a network.  """
    def __init__(self, name, func, fullFnName, lib=None):
        """Initializes the instance with no inputs or outputs

           name =  the name of the instance
           func = the function whose instance this is
           fullFnName = the full function name
           """

        self.name=name
        self.function=func
        self.fullFnName=fullFnName

        # if it has a self.
        #if name != keywords.Self:
        #    self.selfInst=func.getSelf()
        #else:
        #    self.selfInst=None
        #self.selfInst=None
        self._genIO()
            
        # lists of input connections. Inputs can have multiple
        # values if they point to separate subitems
        self.inputConns=[]
        # list of output connections
        self.outputConns=[]
        self.subnetInputConns=[]
        self.subnetOutputConns=[]
        
        # whether the instance is implicit in the network. For writing
        # active.writeXML
        self.implicit=False

        if lib is not None:
            self.setLib(lib)

    def _genIO(self):
        """Generate the input/output IO types."""
        # dicts with dynamic input/output/subnetInput/subnetOutput connections
        # in addition to those defined in the function.
        self.inputs=function_io.IOType(function_io.inputs, self.name, 
                                       self.function.getInputs())
        self.outputs=function_io.IOType(function_io.outputs, self.name, 
                                        self.function.getOutputs())
        self.subnetInputs=function_io.IOType(function_io.subnetInputs, 
                                             self.name, 
                                             self.function.getSubnetInputs())
        self.subnetOutputs=function_io.IOType(function_io.subnetOutputs, 
                                              self.name,
                                              self.function.getSubnetOutputs())
        self.inputs.markImplicit()
        self.outputs.markImplicit()
        self.subnetInputs.markImplicit()
        self.subnetOutputs.markImplicit()



    def copy(self):
        """Return a copy of this instance with its own copied types."""
        inst=Instance(self.name, self.function, self.fullFnName)
        inst.inputs.copyMembers(self.inputs)
        inst.outputs.copyMembers(self.outputs)
        inst.subnetInputs.copyMembers(self.subnetInputs)
        inst.subnetOutputs.copyMembers(self.subnetOutputs)
        return inst

    def markImplicit(self):
        """Mark this instance as automatically generated. If marked, the 
           instance will not be written out when an XML state file is 
           written."""
        self.implicit=True

    def isImplicit(self):
        """Return whether this instance is automatically generated."""
        return self.implicit

    def getName(self):
        """Get the instance name (id)."""
        return self.name
    def setName(self,name):
        """Set the instance name (id)."""
        self.name=name

    def getFunction(self):
        """Get the function."""
        return self.function

    def getFullFnName(self):
        """Get the full (including module names) function name."""
        return self.fullFnName

    def setLib(self, lib):
        self.lib=lib
        lib.addType(self.inputs)
        lib.addType(self.outputs)
        lib.addType(self.subnetInputs)
        lib.addType(self.subnetOutputs)
        self.inputs.setLib(lib)
        self.outputs.setLib(lib)
        self.subnetInputs.setLib(lib)
        self.subnetOutputs.setLib(lib)

    def getInputs(self):
        """Get instance-specific inputs"""
        return self.inputs
    def getOutputs(self):
        """Get instance-specific outputs"""
        return self.outputs
    def getSubnetInputs(self):
        """Get instance-specific subnet inputs"""
        return self.subnetInputs
    def getSubnetOutputs(self):
        """Get instance-specific subnet outputs"""
        return self.subnetOutputs

    def getInputConnections(self):
        """Get an input connnection by name, or None when not connected."""
        return self.inputConns

    def getOutputConnections(self):
        """Get list of output connnections by name, or empty list when 
           not connected."""
        return self.outputConns

    def getSubnetInputConnections(self):
        """Get an input connnection by name, or None when not connected."""
        return self.subnetInputConns

    def getSubnetOutputConnections(self):
        """Get list of output connnections by name, or empty list when 
           not connected."""
        return self.subnetOutputConns

    def addInputConnection(self, conn, isDst):
        """Set an input connection, possibly replacing an existing input
           connection with that input name."""
        #log.debug("Adding input connection %s"%(conn.dstString()))
        if isDst:
            for iconn in self.inputConns:
                # check whether one of the inputs completely subsumes the other
                same=True
                if iconn.isDstExternal():
                    same=False
                if same:
                    iconnSub=iconn.getDstItemList()
                    connSub=conn.getDstItemList()
                    for i in range(min(len(iconnSub), len( connSub))):
                        if iconnSub[i] != connSub[i]:
                            same=False
                            break
                if same:
                    raise InstanceError("%s: New input for connection to %s equal to existing connnection %s"%
                          (self.name, conn.dstString(), iconn.dstString()))
        self.inputConns.append(conn)

    def addSubnetInputConnection(self, conn, isDst):
        """Set an input connection, possibly replacing an existing input
           connection with that input name."""
        #log.debug("Adding subnet input connection %s"%(conn.dstString()))
        if isDst:
            for iconn in self.subnetInputConns:
                # check whether one of the inputs completely subsumes the other
                same=True
                if iconn.isDstExternal():
                    same=False
                if same:
                    iconnSub=iconn.getDstItemList()
                    connSub=conn.getDstItemList()
                    for i in range(min(len(iconnSub), len( connSub))):
                        if iconnSub[i] != connSub[i]:
                            same=False
                            break
                if same:
                    raise InstanceError("%s: New subnet input connection to %s equal to existing connnection %s"%
                          (self.name, conn.dstString(), iconn.dstString()))
        self.subnetInputConns.append(conn)

    def addOutputConnection(self, conn, isDst):
        """Add an output connection."""
        self.outputConns.append(conn)
        
    def addSubnetOutputConnection(self, conn, isDst):
        """Add an output connection."""
        self.subnetOutputConns.append(conn)
    
    def removeOutputConnection(self, conn):
        """Remove an output connection."""
        self.outputConns.remove(conn)
    
    def removeInputConnection(self, conn):
        """Remove an output connection."""
        self.inputConns.remove(conn)

    def getSubnet(self):
        """Get any subnetwork associated with this instance."""
        return self.function.getSubnet()

    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        iiindstr=cpc.util.indStr*(indent+2)
        outf.write('%s<instance id="%s" function="%s">\n'%
                   (indstr, self.name, self.fullFnName))
        outf.write('%s</instance>\n'%indstr)

