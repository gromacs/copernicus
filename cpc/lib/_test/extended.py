# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2013, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
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


import sys
import os
import logging

log=logging.getLogger(__name__)


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import StringValue
from cpc.dataflow import Resources
import cpc.util

class GromacsError(cpc.util.CpcError):
    pass




def extended_err(inp):
    if inp.testing(): 
        # if there are no inputs, we're testing wheter the command can run
        return 
    fo=inp.getFunctionOutput()
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))

    a=inp.getInput('a')
    b=inp.getInput('b')
    if a<0:
        fo.setError("A was negative!")
    if b<0:
        fo.setWarning("B was negative!")

    fo.setOut('a', FloatValue(a+b))
    pers.write()
    return fo




