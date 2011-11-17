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
import shutil
import glob
import stat
import subprocess
import logging
import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


# we can do this in a python controller:
log=logging.getLogger('cpc.lib.gromacs.msm')


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import ArrayValue
from cpc.dataflow import FunctionRunOutput
from cpc.dataflow import NewInstance
from cpc.dataflow import NewConnection
from cpc.dataflow import NewSubnetIO
import cpc.util


import msmbuilder.Trajectory

#import project

class GromacsError(cpc.util.CpcError):
    pass

def convertXtc2lh5(xtcfile,  ref_conf, outFilename, persDir):
    ''' Convert the xtc-files to a .lh5 file '''

    #OutFilename='traj.nopbc.lh5'
    PDBFilename=str(ref_conf)

    mstdout=open(os.path.join(persDir, "tohl5.out"),"w")
    mstdout.write("Writing to %s, %s"%(xtcfile, PDBFilename))
    log.debug("%s, %s %s %s"%(xtcfile, PDBFilename, os.path.exists(xtcfile),
                              os.path.exists(PDBFilename)))
    Traj = msmbuilder.Trajectory.Trajectory.LoadFromXTC([xtcfile],
                                                        PDBFilename=PDBFilename)
    Traj.Save("%s"%outFilename)
    mstdout.close()

def removeSolAndPBC(inFile, outFile, tprFile, grpname, ndxFile, persDir):
    ''' Removes PBC on trajectories '''

    msm1=os.path.join(persDir, 'remove_sol.txt')
    msm2=os.path.join(persDir, 'remove_sol_err.txt')
    mstdout=open(msm1,'w')
    mstderr=open(msm2,'w')
    args=["trjconv","-f","%s"%inFile,"-s", tprFile,"-o","%s"%outFile,"-pbc",
            "mol"]
    if ndxFile is not None:
        args.extend( [ '-n', ndxFile ] )
    proc = subprocess.Popen(args, stdin=subprocess.PIPE,
                            stdout=mstdout, stderr=mstderr)
    proc.communicate(grpname)
    ret = []
    mstdout.close()
    mstdout.close()


# convert an xtc to an lh5
def tolh5(inp): 
    """The function that implements converting to lh5.
       Makes two files: nopbc.xtc and nopbc.lh5."""
    if inp.testing(): #inputs is None or len(inp.inputs) == 0:
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("trjconv -version")
        cpc.util.plugin.testCommand("grompp -version")
        return True
    outFilename=os.path.join(inp.outputDir, "traj.nopbc.lh5")
    nopbcXtcFilename=os.path.join(inp.outputDir, "traj.nopbc.xtc")
    # we do this because it makes things easier in the msm project.
    # TODO: fix this
    xtcCopyFilename=os.path.join(inp.outputDir, "traj.xtc")
    xtcFilename=inp.getInput('xtc')
    tprFilename=inp.getInput('tpr')
    grpname=inp.getInput('grpname')
    ndxFile=inp.getInput('ndx')
    removeSolAndPBC(xtcFilename, nopbcXtcFilename, tprFilename,
                            grpname, ndxFile, inp.persistentDir)
    refFilename=inp.getInput('ref')
    convertXtc2lh5(nopbcXtcFilename, refFilename, outFilename,
                           inp.persistentDir)
    shutil.copy(xtcFilename, xtcCopyFilename)

    fo=inp.getFunctionOutput()
    fo.setOut("lh5", FileValue(outFilename))
    fo.setOut("xtc", FileValue(nopbcXtcFilename))
    fo.setOut("xtc_orig", FileValue(xtcCopyFilename))
    return fo


