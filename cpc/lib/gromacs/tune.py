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
import math


log=logging.getLogger('cpc.lib.gromacs.tune')


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import Resources
import cpc.server.command
import cpc.util


class GromacsError(cpc.util.CpcError):
    pass

def primefactors(x):
    """Return a list with all prime factors of a number."""
    factorlist=[]
    loop=2
    while loop<=x:
        if x%loop==0:
            x/=loop
            factorlist.append(loop)
        else:
            loop+=1
    return factorlist


def tune(rsrc, confFile, tprFile):
    """Set max. run based on configuration file."""
    # TODO: fix this. For now, only count the number of particles and
    # the system size.
    # read the system size 
    inf=open(confFile, 'r')
    i=0
    for line in inf:
        lastsplit=line.split()
        if i==1:
            N=int(line)
        i+=1
    sx=float(lastsplit[0])
    sy=float(lastsplit[0])
    sz=float(lastsplit[0])
    # as a rough estimate, the max. number of cells is 1 per rounded nm
    mincellsize=1.2
    Nsize = int(sx/mincellsize)*int(sy/mincellsize)*int(sz/mincellsize)
    # and the max. number of processors should be N/250
    NN = int(N/250)
    # the max number of processors to use should be the minimum of these
    Nmax = min(Nsize, NN)

    while True:
        # make sure we return a sane number:
        # It's either 4 or smaller, 6, or has at least 3 prime factors. 
        if (Nmax < 5 or Nmax == 6 or 
            (Nmax < 32 and len(primefactors(Nmax)) > 2) or
            (Nmax < 32 and len(primefactors(Nmax)) > 3) ): 
            break
        Nmax -= 1 
    rsrc.min.set('cores', 1)
    rsrc.max.set('cores', Nmax)

#def tune_fn(inp):
#    if inp.testing(): 
#        # if there are no inputs, we're testing wheter the command can run
#        #cpc.util.plugin.testCommand("grompp -version")
#        #cpc.util.plugin.testCommand("mdrun -version")
#        return 
#    fo=inp.getFunctionOutput()
#    fo.setOut('settings', inp.getInputValue('settings'))
#    rsrc=Resources()
#    tune(rsrc, inp.getInput('conf'))
#    fo.setOut('resources', rsrc.setOutputValue())
#    return fo

