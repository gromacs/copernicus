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


import os
import logging

log=logging.getLogger(__name__)

from cpc.dataflow import FileValue
from cpc.dataflow import FloatValue
from cpc.dataflow import FunctionRunOutput
from cpc.dataflow import NewInstance
from cpc.dataflow import NewConnection
from cpc.dataflow import NewSubnetIO

def cat(_outputDir, a, b):
    outname=os.path.join(_outputDir, "cat.%s"%(a.split('.')[-1]))
    outf=open(outname,'w')
    inf=open(a,'r')
    outf.write(inf.read())
    inf.close()
    inf=open(b,'r')
    outf.write(inf.read())
    inf.close()
    return { "c" : outname }

def toFile(inp):
    if inp.testing():
        return
    outname=os.path.join(inp.outputDir, "var.dat")
    # TODO: handle files
    outf=open(outname, 'w')
    #outf.write(str(a))
    array=inp.getInput("a")
    #log.debug("array=%s"%str(array.value))
    for val in array:
        #log.debug('val=%s'%(str(val)))
        outf.write("%s\n"%val.type.valueToLiteral(val.value))
        #outf.write("%s\n"%inputs["a"].type.valueToLiteral(inputs["a"].value))
    outf.close()
    out=FunctionRunOutput()
    out.setOut("b", FileValue(outname) )
    return out  #FunctionRunOutput( { "b" : Value(outname, fileType) } ) 


def testNetwork(inp): 
    if inp.subnetInputs is None or len(inp.subnetInputs) == 0:
        newSubnetInputs=[ NewSubnetIO( "b", "float" ) ]
        newSubnetOutputs=[ NewSubnetIO( "a", "float" ) ]
        newInstances=[ NewInstance("mul_0", "builtin:mul"),
                       NewInstance("mul_1", "builtin:mul"),
                       NewInstance("mul_2", "builtin:mul") ]
        newConnections=[ NewConnection("self", "a", [], "mul_0", "a", [] ),
                         NewConnection("self", "a", [], "mul_0", "b", [] ),
                         NewConnection("self", "a", [], "mul_1", "a", [] ),
                         NewConnection("self", "a", [], "mul_1", "b", [] ),
                         NewConnection("mul_0", "c", [], "mul_2", "a", [] ),
                         NewConnection("mul_1", "c", [], "mul_2", "b", [] ),
                         NewConnection("mul_2", "c", [], "self", "b", [] ) ]
        ret=FunctionRunOutput( None, { "a" : FloatValue(3) }, None,
                               newInstances, newConnections, 
                               newSubnetInputs, newSubnetOutputs) 
    else:
        ret=FunctionRunOutput( { "a" : inp.subnetInputs.get("b") } )
    return ret

