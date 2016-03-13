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
import shlex
import time
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



log=logging.getLogger(__name__)


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import StringValue
from cpc.dataflow import FloatValue
import cpc.util
import cmds

class GromacsError(cpc.util.CpcError):
    def __init__(self, str):
        self.str=str

def g_energy(inp):
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.g_energy)
        return
    edrfile=inp.getInput('edr')
    item=inp.getInput('item')
    outDir=inp.getOutputDir()
    xvgoutname=os.path.join(outDir, "energy.xvg")
    cmdlist = cmdnames.g_energy.split() + ["-f", edrfile, "-o", xvgoutname]
    proc=subprocess.Popen(cmdlist,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.getOutputDir(),
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


def checkUpdated(inp, items):
    for item in items:
        if inp.getInputValue(item).isUpdated():
            return True
    return False

def _trjconv(inp, fo, split):
    """Internal implementation of trjconv and trjconv_split"""
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.trjconv)
        return
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))
    if pers.get('init') is None:
        init=True
        pers.set('init', 1)
    else:
        inpItems=[ 'traj', 'tpr', 'ndx', 'dt', 'skip', 'dump', 'pbc', 'ur',
                   'center', 'fit', 'fit_type', 'cmdline_options' ]
        if not checkUpdated(inp, inpItems):
            return
        init=False
    writeStdin=StringIO()
    trajfile=inp.getInput('traj')
    tprfile=inp.getInput('tpr')
    #item=inp.getInput('item')
    outDir=inp.getOutputDir()
    xtcoutname=os.path.join(outDir, "trajout.xtc")
    grooutname=os.path.join(outDir, "out.gro")
    cmdline = cmdnames.trjconv.split() + ['-s', tprfile, '-f', trajfile]
    if not split:
        cmdline.extend(['-o', xtcoutname])
    else:
        cmdline.extend(['-sep', '-o', grooutname])
    ndxfile=inp.getInput('ndx')
    if ndxfile is not None:
        cmdline.extend(['-n', ndxfile] )
    first_frame_ps=inp.getInput('first_frame_ps')
    if first_frame_ps is not None:
        cmdline.extend(['-b', "%g"%first_frame_ps] )
    last_frame_ps=inp.getInput('last_frame_ps')
    if last_frame_ps is not None:
        cmdline.extend(['-b', "%g"%last_frame_ps] )
    dt=inp.getInput('dt')
    if dt is not None:
        cmdline.extend(['-dt', "%g"%dt] )
    skip=inp.getInput('skip')
    if skip is not None:
        cmdline.extend(['-skip', "%d"%skip] )
    dump=inp.getInput('dump')
    if dump is not None:
        cmdline.extend(['-dump', "%g"%dump] )
    pbc=inp.getInput('pbc')
    if pbc is not None:
        cmdline.extend(['-pbc', pbc] )
    ur=inp.getInput('ur')
    if ur is not None:
        cmdline.extend(['-ur', ur] )
    center=inp.getInput('center')
    if center is not None:
        cmdline.extend(['-center'])
        writeStdin.write("%s\n"%center)
    fit=inp.getInput('fit')
    fit_type=inp.getInput('fit_type')
    if fit is not None:
        if center is not None:
            raise GromacsError('Both fit and center set')
        if fit_type is None:
            fit_type='rot+trans'
        cmdline.extend(['-fit', fit_type])
        writeStdin.write("%s\n"%fit)
    if inp.getInput('cmdline_options') is not None:
        cmdlineOpts=shlex.split(inp.getInput('cmdline_options'))
    else:
        cmdlineOpts=[]
    cmdline.extend(cmdlineOpts)
    log.debug(cmdline)
    outputGroup=inp.getInput('output_group')
    if outputGroup is not None:
        writeStdin.write("%s\n"%outputGroup)
    else:
        writeStdin.write("System\n")

    proc=subprocess.Popen(cmdline,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.getOutputDir(),
                          close_fds=True)
    (stdout, stderr)=proc.communicate(writeStdin.getvalue())
    if proc.returncode != 0:
        raise GromacsError("ERROR: trjconv returned %s"%(stdout))
    if not split:
        fo.setOut('xtc', FileValue(xtcoutname))
    else:
        i=0
        # iterate as long as there are files with anme 'out%d.gro' for
        # increasing i
        while True:
            filename=os.path.join(outDir, 'out%d.gro'%i)
            if not os.path.exists(filename):
                break
            fo.setOut('confs[%d]'%i, FileValue(filename))
            i+=1
    pers.write()

def trjconv(inp):
    fo=inp.getFunctionOutput()
    _trjconv(inp, fo, False)
    return fo

def trjconv_split(inp):
    fo=inp.getFunctionOutput()
    _trjconv(inp, fo, True)
    return fo

def _eneconv(inp, fo):
    """Internal implementation of eneconv"""
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.eneconv)
        return
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))
    if pers.get('init') is None:
        init=True
        pers.set('init', 1)
    else:
        inpItems=[ 'edr_files', 'scalefac', 'dt', 'offset', 'cmdline_options' ]
        if not checkUpdated(inp, inpItems):
            return
        init=False
    writeStdin=StringIO()

    edrFilesList=inp.getInput('edr_files')

    outDir=inp.getOutputDir()
    edrOutname=os.path.join(outDir, "fixed.edr")
    #cmdline=["eneconv", '-f', edrFiles, '-o', edrOutname]
    cmdline = cmdnames.eneconv.split() + ['-f']
    for i in xrange(len(edrFilesList)):
        cmdline.append(inp.getInput('edr_files[%d]' % i))

    cmdline.extend(['-o', edrOutname])

    first_frame_ps=inp.getInput('first_frame_ps')
    if first_frame_ps is not None:
        cmdline.extend(['-b', "%g"%first_frame_ps] )
    last_frame_ps=inp.getInput('last_frame_ps')
    if last_frame_ps is not None:
        cmdline.extend(['-e', "%g"%last_frame_ps] )
    dt=inp.getInput('dt')
    if dt is not None:
        cmdline.extend(['-dt', "%g"%dt] )
    offset=inp.getInput('offset')
    if offset is not None:
        cmdline.extend(['-offset', "%g"%offset] )
    scaleF=inp.getInput('scalefac')
    if scaleF is not None:
        cmdline.extend(['-scalefac', "%g"%scaleF] )
    if inp.getInput('cmdline_options') is not None:
        cmdlineOpts=shlex.split(inp.getInput('cmdline_options'))
    else:
        cmdlineOpts=[]
    cmdline.extend(cmdlineOpts)
    log.debug(cmdline)

    proc=subprocess.Popen(cmdline,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.getOutputDir(),
                          close_fds=True)
    (stdout, stderr)=proc.communicate(writeStdin.getvalue())
    if proc.returncode != 0:
        raise GromacsError("ERROR: eneconv returned %s"%(stdout))
    fo.setOut('edr', FileValue(edrOutname))

    pers.write()

def eneconv(inp):
    fo=inp.getFunctionOutput()
    _eneconv(inp, fo)
    return fo

def pdb2gmx(inp):
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.pdb2gmx)
        return
    input_choices=inp.getInput('input_choices')
    if input_choices is None:
        input_choices=''
    pdbfile=inp.getInput('conf')
    #pdbfile=os.path.join(inp.getOutputDir(),inp.getInput('conf'))
    #shutil.copy(inp.getInput('conf'),pdbfile)
    forcefield=inp.getInput('ff')
    watermodel=inp.getInput('water')
    skip_hydrogens=True #default to ignh
    if inp.getInput('cmdline_options') is not None:
        cmdlineOpts=shlex.split(inp.getInput('cmdline_options'))
    else:
        cmdlineOpts=[]
    cmdline = cmdnames.pdb2gmx
    cmdline += ["-f", pdbfile, "-ff", forcefield, "-water", watermodel]
    if skip_hydrogens:
        cmdline.extend(["-ignh"])
    cmdline.extend(cmdlineOpts)

    proc=subprocess.Popen(cmdline,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.getOutputDir(),
                          close_fds=True)
    (stdout, stderr)=proc.communicate(input_choices)
    if proc.returncode != 0:
        raise GromacsError("ERROR: pdb2gmx returned %s"%(stdout))
    fo=inp.getFunctionOutput()
    fo.setOut('conf', FileValue(os.path.join(inp.getOutputDir(),'conf.gro')))
    fo.setOut('top', FileValue(os.path.join(inp.getOutputDir(),'topol.top')))
    #how do we handle itp output files?
    itpfiles=glob.glob(os.path.join(inp.getOutputDir(),'*.itp'))
    fo.setOut('include',itpfiles)
    for i in xrange(len(itpfiles)):
        fo.setOut('include[%d]'%(i),itpfiles[i])
    return fo

