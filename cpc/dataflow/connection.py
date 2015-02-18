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

log=logging.getLogger(__name__)


import cpc.util
import apperror
import keywords
import vtype
import function_io

"""Set of classes describing instance connections."""


class ConnError(apperror.ApplicationError):
    pass


def splitIOName(name, expectedDirection=None):
    """Split an input/output name into a 3-tuple, as:
       instance-name:'in'/'out'.itemname.subItemname[subItem2name]
       (except for 'self')

       Checks whether [in/out] item corresponds with expected
       type, if given (it can be implicit, such as instance-name.itemname.
       If expectedDirection is not given, it must be specified in name.

       returns tuple of  instance-name, in/out/sub-in/sub-out, item-list
       """
    instance=None
    direction=None
    ioitem=None
    #subItem=None

    # split into fullInstance and ioitem
    srcp0=name.split(keywords.SubTypeSep,1)
    if len(srcp0) < 2:
        if name.find(keywords.SubTypeSep) >= 0:
            raise ConnError("Item '%s': syntax error"%name)
        fullInstance=name
        fullIoItem=None
    else:
        fullInstance=srcp0[0]
        #fullIoItem=".%s"%srcp0[1] # TODO: fix this so it's more flexible
        fullIoItem=srcp0[1]
    # now split fullInstance
    srcp1=fullInstance.rsplit(keywords.InstSep,1)
    dirnm=srcp1[-1]
    instance=srcp1[0]
    if (dirnm==keywords.In or dirnm==keywords.Out):
        if (expectedDirection is not None) and (dirnm != expectedDirection):
            raise ConnError("%s: expected %s item, not %s"%
                            (name, expectedDirection, dirnm))
        if instance != keywords.Self:
            if dirnm == keywords.In:
                direction=function_io.inputs
            else:
                direction=function_io.outputs
        else:
            if dirnm == keywords.In:
                direction=function_io.subnetInputs
            else:
                direction=function_io.subnetOutputs
    elif (dirnm==keywords.ExtIn or dirnm==keywords.ExtOut):
        if (expectedDirection is not None) and (dirnm != expectedDirection):
            raise ConnError("%s: expected %s item, not %s"%
                            (name, expectedDirection, dirnm))
        if instance != keywords.Self:
            raise ConnError(
                      "%s: can't specify external I/O on non-self instance %s"%
                      (name, instance))
        else:
            if dirnm == keywords.ExtIn:
                direction=function_io.inputs
            else:
                direction=function_io.outputs
    elif (dirnm==keywords.SubIn or dirnm==keywords.SubOut):
        if (expectedDirection is not None) and (dirnm != expectedDirection):
            raise ConnError("%s: expected %s item, not %s"%
                            (name, expectedDirection, dirnm))
        # in this case, 'self' doesn't change anything.
        if dirnm == keywords.SubIn:
            direction=function_io.subnetInputs
        else:
            direction=function_io.subnetOutputs
    else:
        if expectedDirection is None:
            raise ConnError("Item %s ambigiuous on in/out"%name)
        elif srcp1[-1]!="":
            raise ConnError("Syntax error in in/out specifier in %s"%name)
        else:
            dirstr=expectedDirection
    # now split ioitem
    #if fullIoItem is not None:
    #    # TODO fix this so we check for closing brackets etc.
    #    # for now, we just replace the brackets with dots.
    #    ioitemlist=fullIoItem.replace('[', keywords.SubTypeSep).\
    #                          replace(']', '').split(keywords.SubTypeSep)
    ##    ioitem=ioitemlist[0]
    #    subItems=ioitemlist[1:]
    #    for i in range(len(subItems)):
    #        if subItems[i].isdigit():
    #            subItems[i]=int(subItems[i])
    #else:
    #    subItems=[]
    #log.debug("instance=%s, direction=%s, ioitem=%s, subitems=%s"%
    #          (str(instance), str(direction), str(ioitem), str(subItems)))
    if fullIoItem is not None:
        ioitem=vtype.parseItemList(fullIoItem)
    else:
        ioitem=[]
    return (instance, direction, ioitem)

def makeConnectionFromDesc(network, srcStr, dstStr):
    """Make a connection object by splitting two names with splitIOName."""
    srcInstanceName, srcDir, srcItemList=splitIOName(srcStr)
    dstInstanceName, dstDir, dstItemList=splitIOName(dstStr)

    return makeConnection(network,
                          srcInstanceName, srcDir, srcItemList,
                          dstInstanceName, dstDir, dstItemList)

def makeInitialValueFromDesc(network, dstStr, val):
    """Make a connection object with an initial value, based on a network,
       and splitIO-ablen ame for the destination."""
    dstInstanceName, dstDir, dstItemList=splitIOName(dstStr)
    return makeInitialValue(network, dstInstanceName, dstDir, dstItemList, val)


def makeConnection(network,
                   srcInstanceName, srcDir, srcItemList,
                   dstInstanceName, dstDir, dstItemList):
    """Make a connection object based on a network, and names for source and
       destination.

        network = the network the instance(s) belong to
        srcInstanceName = the name of the source instance
        srcDir = direction (function_io.in/out/sub_in/sub_out) of source item
        srcItemName = the name of the source item
        srcSubItem = sub items (array subscripts, etc) for the source
        ...
        """
    #log.debug("making connection %s.%s.%s -> %s.%s.%s"%
    #          (srcInstanceName, srcDir, str(srcItemList),
    #           dstInstanceName, dstDir, str(dstItemList)))

    srcInst=network.getInstance(srcInstanceName)
    if srcDir==function_io.inputs:
        srcIO=srcInst.getInputs()
    elif srcDir==function_io.outputs:
        srcIO=srcInst.getOutputs()
    elif srcDir==function_io.subnetInputs:
        srcIO=srcInst.getSubnetInputs()
    elif srcDir==function_io.subnetOutputs:
        srcIO=srcInst.getSubnetOutputs()
    #
    dstInst=network.getInstance(dstInstanceName)
    if dstDir==function_io.inputs:
        dstIO=dstInst.getInputs()
    elif dstDir==function_io.outputs:
        dstIO=dstInst.getOutputs()
    elif dstDir==function_io.subnetInputs:
        dstIO=dstInst.getSubnetInputs()
    elif dstDir==function_io.subnetOutputs:
        dstIO=dstInst.getSubnetOutputs()

    return Connection(srcInst, srcIO, srcItemList, dstInst, dstIO, dstItemList)

def makeInitialValue(network,
                     dstInstanceName, dstDir, dstItemList,
                     val):
    """Make a connection object with an initial value, based on a network,
       and names for the destination."""

    dstInst=network.getInstance(dstInstanceName)
    if dstDir==function_io.inputs:
        dstIO=dstInst.getInputs()
    elif dstDir==function_io.outputs:
        dstIO=dstInst.getOutputs()
    elif dstDir==function_io.subnetInputs:
        dstIO=dstInst.getSubnetInputs()
    elif dstDir==function_io.subnetOutputs:
        dstIO=dstInst.getSubnetOutputs()
    return Connection(None, None, None, dstInst, dstIO, dstItemList, val)


def copyConnection(conn, dstNetwork):
    """Copy the connection to run from instances in the destination network."""
    if conn.getSrcInstance() is not None:
        ret=makeConnection(dstNetwork,
                           conn.getSrcInstance().getName(),
                           conn.getSrcIO().getDir(),
                           conn.getSrcItemList(),
                           conn.getDstInstance().getName(),
                           conn.getDstIO().getDir(),
                           conn.getDstItemList())
    else:
        ret=makeInitialValue(dstNetwork,
                             conn.getDstInstance().getName(),
                             conn.getDstIO().getDir(),
                             conn.getDstItemList(),
                             conn.getInitialValue())
    #ret.setSubnetLoop(conn.isSubnetLoop())
    return ret


class Connection(object):
    """Describes a link between a instance output and a instance input, or
       an input's initial value (if the connection has no source instance)."""
    __slots__=['srcInstance', 'srcIO', 'srcItemList', 'dstInstance', 'dstIO',
               'dstItemList', 'initialValue', 'implicit', 'srcExternal',
               'dstExternal', 'srcAcp', 'dstAcp']
    def __init__(self,
                 srcInstance, srcIO, srcItemList,
                 dstInstance, dstIO, dstItemList,
                 initialValue=None):
        """Initialize a connection

           srcInstance = the function instance of the connection's source
                            (an output), or None
           srcIO       = the source output item (the inputs/outputs/.. object),
                         or None
           srcItemList = the source output item list, or None
           dstInstance = the function instance of the connection's destination
                            (an input)
           dstItemList  = the connection's destination (input) item list.
           srcIO        = the dest. input item (the inputs/outputs/.. object)
           initialValue = the connection's initial value (or None). Only
                          valid if there srcInstance is None."""
        self.srcInstance=srcInstance
        self.srcIO=srcIO
        self.srcItemList=srcItemList

        self.dstInstance=dstInstance
        self.dstIO=dstIO
        self.dstItemList=dstItemList

        self.initialValue=initialValue
        #if self.initialValue is not None:
            #self.initialValue.addRef()
        # check for clashes
        if self.srcInstance is None and self.initialValue is None:
            raise ConnError("Both source instance and initial value empty")
        if self.srcInstance is not None and self.initialValue is not None:
            raise ConnError("Both source instance and initial value set")
        # whether the connection is implicit in the network. For writing
        # active.writeXML
        self.implicit=False

        self.srcExternal=False # whether the source is an 'ext_in' object
        self.dstExternal=False # whether the destination is an 'ext_out' object
        #self.subnetLoop=False # whether this connection is self subnet-to-net

        # source and destination active connection points for when making
        # changes to active networks.
        self.srcAcp = None
        self.dstAcp = None

    def markImplicit(self):
        """Mark this connection as implicit: it shouldn't be written out
           when the state is written."""
        self.implicit=True
    def isImplicit(self):
        """Check whether  this connection as implicit: it shouldn't be written
           out when the state is written."""
        return self.implicit

    def getSrcInstance(self):
        return self.srcInstance
    def getSrcIO(self):
        return self.srcIO
    def getSrcItemList(self):
        return self.srcItemList

    def getDstInstance(self):
        return self.dstInstance
    def getDstIO(self):
        return self.dstIO
    def getDstItemList(self):
        return self.dstItemList

    def getInitialValue(self):
        return self.initialValue
    def setInitialValue(self, value):
        if value is not None:
            value.addRef()
        if self.initialValue is not None:
            self.initialValue.rmRef()
        self.initialValue=value

    def isSrcExternal(self):
        """Return whether the source is an 'external' source (i.e., 'self's
           non subnet I/O"""
        return self.srcExternal

    def isDstExternal(self):
        """Return whether the destination is an 'external' source (i.e., 'self's
           non subnet I/O"""
        return self.dstExternal

    #def isSubnetLoop(self):
    #    """Check whether this connection is a 'subnet loop': a connection
    #       in the self instance from one of its inputs to a subnet output,
    #       or from a subnet input to an output."""
    #    return self.subnetLoop
    #def setSubnetLoop(self, slo):
    #    """set the subnetloop bool."""
    #    self.subnetLoop=slo

    def connect(self):
        """Connect both ends of the connection."""
        # Normally, the connection has a source output and a destination
        # input. There is one exception: when connection 'self' inputs/outputs
        # to its subnet inputs/outputs
        #
        # so now we check whether the connection is from/to
        # self, and that it connects subnet to non-subnet. If it is
        # it's the above exception.
        if self.dstInstance.getName() == keywords.Self:
            if not self.dstIO.direction.isInput():
                if not self.dstIO.direction.isInSubnet():
                    self.dstExternal=True
                else:
                    raise ConnError("Trying to connect to a self.sub_out: %s"%
                                    (self.dstString()))
        if ( (self.srcInstance is not None) and
             self.srcInstance.getName() == keywords.Self):
            if self.srcIO.direction.isInput():
                if not self.srcIO.direction.isInSubnet():
                    self.srcExternal=True
                else:
                    raise ConnError("Trying to connect from a self.sub_in: %s"%
                                    (self.srcString()))
        if not (self.srcExternal or self.dstExternal):
            #
            #   ( (self.dstInstance.getName() == keywords.Self or
            #      self.srcInstance.getName() == keywords.Self) ):
            # check whether we connect an output to an input
            if not self.dstIO.direction.isInput():
                raise ConnError("Trying to connect an input as dest: %s->%s, %s, %s"%
                                (self.srcString(), self.dstString(),
                                str(self.srcIO.direction.isInSubnet()),
                                str(self.dstIO.direction.isInSubnet())))
            if self.srcInstance is not None:
                if self.srcIO.direction.isInput():
                    raise ConnError("Trying to connect an input as source")
                if self.srcIO.direction.isInSubnet():
                    if not self.srcInstance.getName() == keywords.Self:
                        raise ConnError("Trying to connect to non-self subnet")
                #    self.srcInstance.addSubnetOutputConnection(self)
                #else:
                #    self.srcInstance.addOutputConnection(self)
            if self.dstIO.direction.isInSubnet():
                if not self.dstInstance.getName() == keywords.Self:
                    raise ConnError("Trying to connect to non-self subnet")
                #self.dstInstance.addSubnetInputConnection(self)
            #else:
                #self.dstInstance.addInputConnection(self)
        #else:
        #else:
            # the exception. Check whether we connect a input to a subnet output
            # or a subnet input to an output
            #self.subnetLoop=True
            #if self.srcIO.direction.isInSubnet():
            #    self.srcInstance.addSubnetInputConnection(self)
            #else:
            #    self.srcInstance.addInputConnection(self)
            #if self.srcIO.direction.isInSubnet():
            #    #if not self.srcItem.isInput() or self.dstItem.isInput():
            #   #    raise ConnError("Trying to connect subnet output to input")
            #    self.dstInstance.addOutputConnection(self)
            #else:
            #    #if not self.srcItem.isInput() or self.dstItem.isInput():
            #   #    raise ConnError("Trying to connect output to subnet input")
            #    self.srcInstance.addInputConnection(self)
            #    self.dstInstance.addSubnetOutputConnection(self)
        if self.srcInstance is not None:
            if self.srcIO.direction == function_io.outputs:
                self.srcInstance.addOutputConnection(self, False)
            elif self.srcIO.direction == function_io.subnetOutputs:
                self.srcInstance.addSubnetOutputConnection(self, False)
            elif self.srcIO.direction == function_io.inputs:
                self.srcInstance.addInputConnection(self, False)
            elif self.srcIO.direction == function_io.subnetInputs:
                self.srcInstance.addSubnetInputConnection(self, False)

        if self.dstIO.direction == function_io.inputs:
            self.dstInstance.addInputConnection(self, True)
        elif self.dstIO.direction == function_io.subnetInputs:
            self.dstInstance.addSubnetInputConnection(self, True)
        elif self.dstIO.direction == function_io.outputs:
            self.dstInstance.addOutputConnection(self, True)
        elif self.dstIO.direction == function_io.subnetOutputs:
            self.dstInstance.addSubnetOutputConnection(self, True)


    def disconnect(self):
        """Disconnect both ends of the connection."""
        if self.srcInstance is not None:
            if not self.srcIO.direction.isInSubnet():
                self.srcInstance.removeOutputConnection(self)
            else:
                self.srcInstance.removeSubnetOutputConnection(self)
        if not self.dstIO.direction.isInSubnet():
            self.dstInstance.removeInputConnection(self)
        else:
            self.dstInstance.removeSubnetInputConnection(self)

    def srcString(self):
        """Return the source as a splitIO()-able string."""
        if self.srcInstance is None:
            return ""
        itemStr=vtype.itemListStr(self.srcItemList)
        srcDir=self.srcIO.getDir()
        # now fix the naming for 'self':
        if self.srcInstance.getName() == keywords.Self:
            if srcDir == function_io.inputs:
                srcDirStr=keywords.ExtIn
            elif srcDir == function_io.outputs:
                srcDirStr=keywords.ExtOut
            if srcDir == function_io.subnetInputs:
                srcDirStr=keywords.In #str(function_io.subnetInputs)
            elif srcDir == function_io.subnetOutputs:
                srcDirStr=keywords.Out #str(function_io.subnetOutputs)
        else:
            srcDirStr=str(srcDir)
        retstr="%s:%s%s"%(self.srcInstance.getName(), srcDirStr, itemStr)
        return retstr

    def dstString(self):
        """Return the destination as a splitIO()-able string."""
        itemStr=vtype.itemListStr(self.dstItemList)
        dstDir=self.dstIO.getDir()
        # now fix the naming for 'self':
        if self.dstInstance.getName() == keywords.Self:
            if dstDir == function_io.inputs:
                dstDirStr=keywords.ExtIn
            elif dstDir == function_io.outputs:
                dstDirStr=keywords.ExtOut
            if dstDir == function_io.subnetInputs:
                dstDirStr=keywords.In #str(function_io.subnetInputs)
            elif dstDir == function_io.subnetOutputs:
                dstDirStr=keywords.Out #str(function_io.subnetOutputs)
        else:
            dstDirStr=str(dstDir)
        retstr="%s:%s%s"%(self.dstInstance.getName(), dstDirStr, itemStr)
        return retstr

    def writeXML(self, outf, indent=0):
        """Write a connection out as XML"""
        indstr=cpc.util.indStr*indent
        if self.srcInstance is not None:
            outf.write('%s<connection src="%s" dest="%s" />\n'%
                       (indstr, self.srcString(), self.dstString()))
        else:
            val=self.initialValue.type.valueToLiteral(self.initialValue.value)
            tp=self.initialValue.type.getFullName()
            if not self.initialValue.type.isCompound():
                outf.write('%s<assign type="%s" value="%s" dest="%s" />\n'%
                           (indstr, tp, val, self.dstString()))
            else:
                outf.write('%s<assign type="%s" dest="%s" />\n'%
                           (indstr, tp, self.dstString()))
                self.initialValue.writeXML(outf, indent+1)
                outf.write('%s</assign>\n'%indstr)


