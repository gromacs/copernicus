# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2017, Sander Pronk, Iman Pouya, Magnus Lundborg,
# Erik Lindahl, and others.
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

def _genconf(inp, fo):
    """Internal implementation of genconf"""
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("genconf -version")
        return
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))
    if pers.get('init') is None:
        init=True
        pers.set('init', 1)
    else:
        inpItems=[ 'conf', 'nmolat', 'nbox', 'dist', 'cmdline_options' ]
        if not checkUpdated(inp, inpItems):
            return
        init=False
    writeStdin=StringIO()

    conf=inp.getInput('conf')

    outDir=inp.getOutputDir()
    outname=os.path.join(outDir, "out.gro")

    nmolat=inp.getInput('nmolat')

    cmdline=["genconf", '-f', conf, '-o', outname, '-nmolat', nmolat]

    nbox=inp.getInput('nbox')
    if nbox is not None and len(nbox) == 3:
        cmdline.extend(['-nbox', '%d %d %d' % (nbox[0], nbox[1], nbox[2])])
    dist=inp.getInput('dist')
    if dist is not None and len(dist) == 3:
        cmdline.extend(['-dist', '%.3f %.3f %.3f' % (dist[0], dist[1], dist[2])])
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
        raise GromacsError("ERROR: genconf returned %s"%(stdout))
    fo.setOut('conf', FileValue(outname))

    pers.write()

def genconf(inp):
    fo=inp.getFunctionOutput()
    _genconf(inp, fo)
    return fo

def _editconf(inp, fo):
    """Internal implementation of genconf"""
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("editconf -version")
        return
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))
    if pers.get('init') is None:
        init=True
        pers.set('init', 1)
    else:
        inpItems=[ 'conf', 'boxtype', 'box', 'angles', 'distance', 'cmdline_options' ]
        if not checkUpdated(inp, inpItems):
            return
        init=False
    writeStdin=StringIO()

    conf=inp.getInput('conf')

    outDir=inp.getOutputDir()
    outname=os.path.join(outDir, "out.gro")
    cmdline=["editconf", '-f', conf, '-o', outname]


    bt=inp.getInput('boxtype')
    if bt:
        cmdline.extend(['-bt', '%s' % bt])
    box=inp.getInput('box')
    if box is not None and len(box) == 3:
        cmdline.extend(['-box', '%.3f %.3f %.3f' % (box[0], box[1], box[2])])
    angles=inp.getInput('angles')
    if angles is not None and len(angles) == 3:
        cmdline.extend(['-angles', '%.3f %.3f %.3f' % (angles[0], angles[1], angles[2])])
    d=inp.getInput('distance')
    if d is not None:
        cmdline.extend(['-d', '%.3f' % d])
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
        raise GromacsError("ERROR: editconf returned %s"%(stdout))
    fo.setOut('conf', FileValue(outname))

    pers.write()

def editconf(inp):
    fo=inp.getFunctionOutput()
    _editconf(inp, fo)
    return fo

def genWhamInput(inp):

    outDir=inp.getOutputDir()

    tprListFileName = os.path.join(outDir, 'tpr-files.dat')
    pullXListFileName = os.path.join(outDir, 'pullx-files.dat')
    pullFListFileName = os.path.join(outDir, 'pullf-files.dat')

    tpr = inp.getInput('tpr')
    nUmbrellas = len(tpr)
    pullx = inp.getInput('pullx')
    pullf = inp.getInput('pullf')
    if not pullx and not pullf:
        raise GromacsError("SYNTAX ERROR: pullx OR pullf must be provided.")
    if pullx and pullf:
        raise GromacsError("SYNTAX ERROR: Both pullx AND pullf cannot be provided.")

    tprListFile = open(tprListFileName, 'w')
    if pullx:
        pullXListFile = open(pullXListFileName, 'w')
        pullFListFile = None
        pullFListFileName = None
    else:
        pullFListFile = open(pullFListFileName, 'w')
        pullXListFile = None
        pullXListFileName = None

    for i in xrange(nUmbrellas):
        f = inp.getInput('tpr[%d]' % i)
        tprListFile.write('%s\n' % f)
        if pullx:
            f = inp.getInput('pullx[%d]' % i)
            pullXListFile.write('%s\n' % f)
        else:
            f = inp.getInput('pullf[%d]' % i)
            pullFListFile.write('%s\n' % f)

    return(tprListFileName, pullXListFileName, pullFListFileName)

def getWhamRange(tprFile):

    cmd=['gmxdump', '-s', tprFile ]
    sp=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT)
    for line in sp.stdout:
        if ' init ' in line:
            pos=abs(float(line.split()[2]))
            return pos


def wham(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand('g_wham -version')
        return

    writeStdin=StringIO()

    outDir=inp.getOutputDir()

    (tprFiles, pullxFiles, pullfFiles) = genWhamInput(inp)

    outProf = os.path.join(outDir, 'profile.xvg')
    outHist = os.path.join(outDir, 'histo.xvg')
    outIact = os.path.join(outDir, 'iact.xvg')


    cmdline=['g_wham', '-it', tprFiles, '-o', outProf, '-hist', outHist, '-ac']

    if pullxFiles:
        cmdline.extend(['-ix', pullxFiles])
    else:
        cmdline.extend(['-if', pullfFiles])

    limitRange = inp.getInput('limit_range')
    if limitRange or limitRange is None:
        f = inp.getInput('tpr[0]')
        limit = getWhamRange(f)
        if limit:
            cmdline.extend(['-min', '%f' % (-limit), '-max', '%f' % limit])

    beginTime = inp.getInput('begin_time')
    if beginTime is not None:
        cmdline.extend(['-b', '%g' % beginTime])
    endTime = inp.getInput('end_time')
    if endTime is not None:
        cmdline.extend(['-e', '%g' % endTime])
    temperature = inp.getInput('temperature')
    if temperature is not None:
        cmdline.extend(['-temp', '%f' % temperature])
    bins = inp.getInput('bins')
    if bins is not None:
        cmdline.extend(['-bins', '%d' % bins])
    cyclic = inp.getInput('cyclic')
    if cyclic:
        cmdline.extend(['-cycl'])
    sym = inp.getInput('sym')
    if sym:
        cmdline.extend(['-sym'])
    nBootstraps = inp.getInput('n_bootstraps')
    if nBootstraps:
        outBSRes = os.path.join(outDir, 'bsResult.xvg')
        outBSProfs = os.path.join(outDir, 'bsProfs.xvg')
        cmdline.extend(['-nBootstrap', '%d' % nBootstraps, '-bsres', outBSRes, '-bsprof', outBSProfs, '-tol', '1e-05'])
    else:
        outBSRes = None
        outBSProfs = None
    acsig = inp.getInput('ac_smooth')
    if acsig:
        cmdline.extend(['-acsig', '%f' % acsig])

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
        raise GromacsError("ERROR: g_wham returned %s"%(stdout))

    fo=inp.getFunctionOutput()

    fo.setOut('profile', FileValue(outProf))
    fo.setOut('histogram', FileValue(outHist))
    fo.setOut('bs_results', FileValue(outBSRes))
    fo.setOut('bs_profiles', FileValue(outBSProfs))
    fo.setOut('iact', FileValue(outIact))

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

