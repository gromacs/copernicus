# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
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


log=logging.getLogger(__name__)


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import Resources
import cpc.util
import cmds

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


def tryRun(tprFile, runDir, Ncores):
    """Try to run mdrun with Ncores cores."""
    cmdnames = cmds.GromacsCommands()
    cmdlist = cmdnames.mdrun.split()
    cmdlist += ["-nt", "%d"%Ncores, "-s", tprFile, "-rcon", "0.7",
                "-maxh", "0.0005" ]
    proc=subprocess.Popen(cmdlist, 
                          stdin=None,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=runDir)
    (stdo, stde) = proc.communicate(None)
    if proc.returncode != 0:
        return (False, stdo)
    return (True, stdo)

def tune(rsrc, confFile, tprFile, testRunDir, Nmax=None):
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
    if Nmax is None:
        # the max number of processors to use should be the minimum of these
        Nmax = min(Nsize, NN)
    Nmax = max(1, Nmax)

    while True:
        # make sure we return a sane number:
        # It's either 4 or smaller, 6, or has at least 3 prime factors. 
        if (Nmax < 5 or Nmax == 6 or 
            (Nmax < 32 and len(primefactors(Nmax)) > 2) or
            (Nmax < 32 and len(primefactors(Nmax)) > 3) ): 
            canRun, stdo=tryRun(tprFile, testRunDir, Nmax)
            if canRun:
                break
        Nmax -= 1 
        if Nmax < 1:
            raise GromacsError("Can't run simulation: %s"%stdo)
    rsrc.min.set('cores', 1)
    rsrc.max.set('cores', Nmax)


