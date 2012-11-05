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

"""Driver for pairmodel."""

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


log=logging.getLogger('cpc.lib.pairmodel')


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from sets import Set
from cpc.dataflow import Resources
import cpc.command
import cpc.util

import tune

#hack to test for shutil.split()
has_split=True
try:
  shutil.split('foo bar')
except:
  has_split=False


class ModelError(cpc.util.CpcError):
    pass

def pairmodel_multi(inp):
    if inp.testing():
    # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("pairmodel --help")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
        "persistent.dat"))

    if(pers.get('running')):
        running_sims = pers.get('running')

    else:
        running_sims=0

    arr_testseq = inp.getInput('testseq')

    out = inp.getFunctionOutput()
    for i in range(running_sims,len(arr_testseq)):
        out.addInstance("pairmodel_%d"%i,"pairmodel")
        out.addConnection("self:ext_in.testseq[%d]"%i,"pairmodel_%d:in.testseq"%i)
        out.addConnection("self:ext_in.pdb1[%d]"%i,"pairmodel_%d:in.pdb1"%i)
        out.addConnection("self:ext_in.pdb2[%d]"%i,"pairmodel_%d:in.pdb2"%i)
        out.addConnection("self:ext_in.seq1","pairmodel_%d:in.seq1"%i)
        out.addConnection("self:ext_in.seq2","pairmodel_%d:in.seq2"%i)
        out.addConnection("self:ext_in.cmdline_options","pairmodel_%d:in.cmdline_options"%i)

        out.addConnection("pairmodel_%d:out.conf"%i,"self:ext_out.result[%d].conf"%i)
        out.addConnection("pairmodel_%d:out.stderr"%i,"self:ext_out.result[%d].stderr"%i)
        out.addConnection("pairmodel_%d:out.stdout"%i,"self:ext_out.result[%d].stdout"%i)
        running_sims+=1

    pers.set("running",running_sims)
    pers.write()
    return out

def pairmodel(inp):
    if inp.testing(): 
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("pairmodel --help")
        return 
    persDir=inp.getPersistentDir()
    outDir=inp.getOutputDir()
    fo=inp.getFunctionOutput()
    rsrc=Resources(inp.getInputValue("resources"))
    rsrcFilename=os.path.join(persDir, 'rsrc.dat')
    log.debug("Initializing pairmodel")
    seq1=inp.getInput('seq1')
    seq2=inp.getInput('seq2')
    pdb1=inp.getInput('pdb1')
    pdb2=inp.getInput('pdb2')
    testseq=inp.getInput('testseq')
    #how do we assign suffix name?
    suffixname=pdb1.split('_')[-1]
    if len(suffixname)>3:
        suffixname=suffixname[:-4]
    #do we need to copy files to working directory?
    if inp.getInput('cmdline_options') is not None:
        if has_split:
            cmdlineOpts=shutil.split(inp.getInput('cmdline_options'))
        else:
            cmdlineOpts=inp.getInput('cmdline_options').split()
    else:
        cmdlineOpts=[]
    # now add to the priority if this run has already been started
    # we can always add state.cpt, even if it doesn't exist.
    args=["--seqfile", testseq, "--template1", seq1, "--template2", seq2, 
           "--seqname", os.path.basename(testseq)[:-4], "--samples1", pdb1,
           "--samples2", pdb2, "--suffix", suffixname ]
    args.extend(cmdlineOpts)
    cmd=cpc.command.Command(newdirname, "modeltools/pairmodel", args)
    if inp.hasInput("resources") and inp.getInput("resources") is not None:
        log.debug("resources is %s"%(inp.getInput("resources")))
        #rsrc=Resources(inp.getInputValue("resources"))
        rsrc.updateCmd(cmd)
    log.debug("Adding command")
    fo.addCommand(cmd)
    # and save for further invocations
    rsrc.save(rsrcFilename)
    return fo

