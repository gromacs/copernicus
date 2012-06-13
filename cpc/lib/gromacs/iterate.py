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


import sys
import os
import re
import os.path
import shutil
import glob
import stat
import subprocess
import logging
import time


log=logging.getLogger('cpc.lib.mdrun')

import cpc.util

class IterateError(cpc.util.CpcError):
    pass


class iterations:
    """Decide what inputs to iterate over, given a set of inputs."""
    def __init__(self, inp, inputs, outputs, pers):
        """Decide what inputs to iterate over, and return a list of booleans
           that control this.
           
           inp = the function input object
           inputs = a list of strings of input names to potentially iterate over
           pers = the persistence object."""
        self.N=0
        self.inputs={}
        for inputName in inputs:
            inpval=inp.getInput(inputName)
            if inpval is not None:
                Ncur=len(inp.getInput(inputName)) # the number of inputs 
            else:
                Ncur=0
            it=False # whether to iterate this one
            if Ncur > 1:
                it=True
                if self.N == 0 or self.N == 1:
                    self.N=Ncur
                elif self.N != Ncur:
                    raise IterateError(
                        "Inconsistent number of items in %s: must be 1 or %d"%
                        (inputName, self.N))
            elif Ncur == 1:
                # set it to be at least 1
                if self.N == 0:
                    self.N=1
            self.inputs[inputName]=it
        self.outputs=outputs

    def getN(self):
        """Get the number of iterations."""
        return self.N

    def iterate(self, inputName):
        """Return whether to iterate over a variable with this name"""
        return self.inputs[inputName]

    def connect(self, out, i, instName):
        """Connect all inputs with their corresponding input name of a new
           instance.
           
           out = the runOutput object
           i = the instance counter
           instName = the name of the new instance"""
        for inpName, iterate in self.inputs.iteritems():
            if iterate:
                out.addConnection("self:ext_in.%s[%d]"%(inpName, i),
                                  "%s:in.%s"%(instName, inpName))
            else:
                out.addConnection("self:ext_in.%s[0]"%(inpName),
                                  "%s:in.%s"%(instName, inpName))
        for outputName in self.outputs:
            out.addConnection("%s:out.%s"%(instName, outputName),
                              "self:ext_out.%s[%d]"%(outputName,i))



