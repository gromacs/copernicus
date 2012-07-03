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
import subprocess
import logging
import time


log=logging.getLogger('cpc.lib.mdrun')


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import StringValue
from cpc.dataflow import FloatValue
import cpc.server.command
import cpc.util

#hack to test for shutil.split()
has_split=True
try:
  shutil.split('foo bar')
except:
  has_split=False

class GromacsError(cpc.util.CpcError):
    def __init__(self, str):
        self.str=str

def g_energy(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("g_energy -version")
        return 
    edrfile=inp.getInput('edr')
    item=inp.getInput('item')
    outDir=inp.getOutputDir()
    xvgoutname=os.path.join(outDir, "energy.xvg")
    proc=subprocess.Popen(["g_energy", "-f", edrfile, "-o", xvgoutname], 
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.outputDir,
                          close_fds=True)
    (stdout, stderr)=proc.communicate(item)
    if proc.returncode != 0:
        raise GromacsError("ERROR: g_energy returned %s"%(stdout))
    regitem=re.compile(r'^%s'%(item))
    regsplit=re.compile(r'---------------')
    splitmatch=False
    for line in iter(stdout.splitlines()):
        if not splitmatch:
            if regsplit.match(line):
                splitmatch=True
        else:
            if regitem.match(line):
                foundmatch=True
                sp=line.split()
                av=float(sp[1])
                err=float(sp[2])
                rmsd=float(sp[3])
                drift=float(sp[4])
                unit=sp[5]
                break
    if not foundmatch:
        raise GromacsError("ERROR: couldn't find match for energy item %s in output."%
                           item)
    fo=inp.getFunctionOutput()
    fo.setOut('xvg', FileValue(xvgoutname))
    fo.setOut('average', FloatValue(av))
    fo.setOut('error', FloatValue(err))
    fo.setOut('rmsd', FloatValue(rmsd))
    fo.setOut('drift', FloatValue(drift))
    fo.setOut('unit', StringValue(unit))
    return fo 

def trjconv(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("trjconv -version")
        return
    output_groups=inp.getInput('output_groups')
    trjfile=inp.getInput('trj')
    tprfile=inp.getInput('tpr')
    if inp.getInput('cmdline_options') is not None:
        if has_split:
            cmdlineOpts=shutil.split(inp.getInput('cmdline_options'))
        else:
            cmdlineOpts=inp.getInput('cmdline_options')
    else:
        cmdlineOpts=[]
    cmdlist=["trjconv", "-s", tprfile, "-f", trjfile]
    cmdlist.extend(cmdlineOpts)

    if inp.hasInput('ndx'):
        cmdlist.extend(["-n", inp.getInput('ndx')])

    proc=subprocess.Popen(cmdlist,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.outputDir,
                          close_fds=True)
    (stdout, stderr)=proc.communicate(output_groups)
    if proc.returncode != 0:
        raise GromacsError("ERROR: trjconv returned %s"%(stdout))
    fo=inp.getFunctionOutput()
    fo.setOut('xtc', FileValue(os.path.join(inp.outputDir,'trajout.xtc')))
    return fo

 
def pdb2gmx(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("pdb2gmx -version")
        return
    input_choices=inp.getInput('input_choices')
    if input_choices is None:
        input_choices=''
    pdbfile=inp.getInput('conf')
    #pdbfile=os.path.join(inp.outputDir,inp.getInput('conf'))
    #shutil.copy(inp.getInput('conf'),pdbfile)
    forcefield=inp.getInput('ff')
    watermodel=inp.getInput('water')
    skip_hydrogens=True #default to ignh
    if inp.getInput('cmdline_options') is not None:
        if has_split:
            cmdlineOpts=shutil.split(inp.getInput('cmdline_options'))
        else:
            cmdlineOpts=inp.getInput('cmdline_options')
    else:
        cmdlineOpts=[]
    cmdlist=["pdb2gmx", "-f", pdbfile, "-ff", forcefield, "-water", watermodel]
    if skip_hydrogens:
        cmdlist.append(["-ignh"]
    cmdlist.extend(cmdlineOpts)

    proc=subprocess.Popen(cmdlist,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.outputDir,
                          close_fds=True)
    (stdout, stderr)=proc.communicate(input_choices)
    if proc.returncode != 0:
        raise GromacsError("ERROR: pdb2gmx returned %s"%(stdout))
    fo=inp.getFunctionOutput()
    fo.setOut('conf', FileValue(os.path.join(inp.outputDir,'conf.gro')))
    fo.setOut('top', FileValue(os.path.join(inp.outputDir,'topol.top')))
    #how do we handle itp output files?
    itpfiles=glob.glob(os.path.join(inp.outputDir,'*.itp'))
    fo.setOut('include',itpfiles)
    for i in range(len(itpfiles)):
        fo.setOut('include[%d]'%(i),itpfiles[i])
    return fo
 
