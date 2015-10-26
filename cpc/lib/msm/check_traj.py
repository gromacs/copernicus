#!/usr/bin/env python

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
import os.path
import subprocess
import re

from cpc.lib.gromacs import cmds

def checkTrajectory(filename):
    """Check an existing trajectory and return the trajectory time in ns, 
        the delta t, and the number of frames"""
    cmdnames = cmds.GromacsCommands()
    proc=subprocess.Popen(cmdnames.gmxcheck.split() + ["-f", filename],
                          stdin=None,
                          stderr=subprocess.STDOUT,
                          stdout=subprocess.PIPE)
    ret=proc.communicate()
    step=re.compile('^Step\s*([0-9]*)\s*([0-9]*)', re.MULTILINE)
    if proc.returncode != 0: 
        sys.stderr.write('pwd= %s\n'%os.getcwd())
        sys.stderr.write('Got: %s\n'%(unicode(ret[0], errors="ignore")))
    match=step.search(ret[0])
    frames=int(match.group(1))
    dt=float(match.group(2))
    ns=(frames-1)*dt/1000.
    sys.stderr.write("Using trajectory %s with %g ns of trajectories\n"%
                     (filename, ns))
    # return the time in ns
    return (ns, dt, frames)



