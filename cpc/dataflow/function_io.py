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


#log=logging.getLogger(__name__)

import apperror
import keywords
import vtype

class FunctionIOError(apperror.ApplicationError):
    pass


class IODir(object):
    """A function io direction: in/out/sub_in/sub_out."""
    def __init__(self, name, isInput, isInSubnet):
        """Initialize based on name and direction."""
        self.name=name
        self.isSubnet=isInSubnet
        self.isInp=isInput
    def __str__(self):
        return self.name
    def isInSubnet(self):
        return self.isSubnet
    def isInput(self):
        return self.isInp

inputs =     IODir(keywords.In, True, False)    
outputs =    IODir(keywords.Out, False, False)  
subnetInputs =  IODir(keywords.SubIn, True, True)
subnetOutputs = IODir(keywords.SubOut, False, True)

class IOType(vtype.RecordType):
    """The list type specific for instance inputs/outputs/subnetinputs/...
       """
    __slots__=['direction']
    def __init__(self, direction, instName, parentType):
        """Initialize based on direction and name."""
        self.direction=direction
        name="%s%s%s"%(instName,
                       keywords.InstSep,
                       direction.name)
        vtype.RecordType.__init__(self, name, parentType)

    def getDir(self):
        return self.direction

class IOArrayType(vtype.ArrayType):
    """The list type specific for instance array inputs/outputs/subnetinputs/...
       """
    def __init__(self, direction, instName, IOType):
        """Initialize based on direction and name."""
        self.direction=direction
        name="%s%s%s"%(instName,
                       keywords.InstSep,
                       direction.name)
        vtype.ArrayType.__init__(self, name, vtype.arrayType, memberType=IOType)

    def getDir(self):
        return self.direction


