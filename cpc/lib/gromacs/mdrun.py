# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2014, Sander Pronk, Iman Pouya, Magnus Lundborg,
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
import shlex
import glob
import stat
import subprocess
import logging
import time


log=logging.getLogger(__name__)


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import StringValue
from cpc.dataflow import Resources
import cpc.command
import cpc.util

import tune
import iterate
import cmds

class MdrunError(cpc.util.CpcError):
    pass

class GromacsError(cpc.util.CpcError):
    pass

def extractConf(tprFile, confFile):
    """Extract a configuration to confFile from tprFile."""
    cmdnames = cmds.GromacsCommands()
    cmdlist = cmdnames.editconf.split() + ['-f', tprFile, '-o', confFile]
    proc=subprocess.Popen(cmdlist,
                          stdin=None,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=os.path.split(confFile)[0])
    proc.communicate(None)
    if proc.returncode != 0:
        raise GromacsError("Error running editconf: %s"%
                           proc.stdout)


def runGmxCheckGap(fileTypeFlag, checkFile):
    cmdnames = cmds.GromacsCommands()
    cmd = cmdnames.gmxcheck.split() + [fileTypeFlag, checkFile]
    proc=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    #noMatchLine=re.compile(r'Timesteps at.*don\'t match.*\(([0-9.]+),\s([0-9.]+)\)')

    stdExpected = None

    for line in proc.stdout:
        #m = noMatchLine.match(line)
        #if m:
        if 'Timesteps at t=' in line:
            log.debug("%s, %s", checkFile, line)
            parts = line.split()
            thisExpected = float(parts[5][1:-1])
            thisActual = float(parts[6][:-1])
            if stdExpected == None:
                stdExpected = thisExpected
            if thisActual > stdExpected:
                log.debug("Discarding %s due to a gap in the file" % checkFile)
                return False

    return True

def checkConfoutDir(path):

    xtcso = sorted(glob.glob(os.path.join(path, "traj.*xtc")))
    trrso = sorted(glob.glob(os.path.join(path, "traj.*trr")))
    edrso = sorted(glob.glob(os.path.join(path, "ener.*edr")))

    xtcs = []
    trrs = []
    edrs = []

    for f in xtcso:
        if runGmxCheckGap('-f', f):
            xtcs.append(f)
    for f in trrso:
        if runGmxCheckGap('-f', f):
            trrs.append(f)
    for f in edrso:
        if runGmxCheckGap('-e', f):
            edrs.append(f)

    if xtcs or trrs or edrs:
        return True

    return False

class TrajFileCollection(object):
    def __init__(self, persDir):
        self.persDir=persDir
        lastfound=True
        self.trajlist=[]
        self.lastcpt=None
        lastrundir=None
        i=0
        while lastfound:
            i+=1
            currundir=os.path.join(persDir, "run_%03d"%i)
            lastfound=False
            try:
                st=os.stat(currundir)
                if st.st_mode & stat.S_IFDIR:
                    lastfound = True
                    lastrundir = currundir
                    trajl = self.checkResults(lastrundir)
                    self.trajlist.append(trajl)
            except OSError:
                pass
        self.lastDirNr=i
        self.lastDir=lastrundir
        self.newRunDir=currundir
        self.lastTrajNr=self._extractLastTrajNr()
        self.cmdnames = cmds.GromacsCommands()

    def getLastDir(self):
        """Return the last run directory."""
        return self.lastDir

    def getLastDirNr(self):
        """Return the last run directory number."""
        return self.lastDirNr

    def getNewRunDir(self):
        """Get the new run directory"""
        return self.newRunDir

    def getLastCpt(self):
        """return the last checkpoint."""
        return self.lastcpt

    def getTrajList(self):
        """Return the list of trajectories (a list of lists)."""
        return self.trajlist

    def checkResults(self, rundir):
        """Runs gmx check on the expected output files to see that they
           are OK. Returns a dictionary of output files if successful. """
        trajl = dict()

        # Check if this has produced trajectories
        xtc = glob.glob(os.path.join(rundir, "traj.part*.xtc"))
        trr = glob.glob(os.path.join(rundir, "traj.part*.trr"))
        edr = glob.glob(os.path.join(rundir, "ener.part*.edr"))

        for f in reversed(xtc):
            if os.path.isfile(f) and runGmxCheckGap('-f', f):
                trajl['xtc'] = f
                break

        for f in reversed(trr):
            if os.path.isfile(f) and runGmxCheckGap('-f', f):
                trajl['trr'] = f
                break

        for f in reversed(edr):
            if os.path.isfile(f) and runGmxCheckGap('-e', f):
                trajl['edr'] = f
                break

        # Only consider this the last checkpoint if valid (no gaps) output files
        # were produced.
        if trajl.get('xtc') or trajl.get('trr') or trajl.get('edr'):
            cpt=os.path.join(rundir, "state.cpt")
            if os.path.exists(cpt):
                # and check the size
                st=os.stat(cpt)
                if st.st_size>0:
                    self.lastcpt=cpt

        return trajl

    def _extractLastTrajNr(self):
        """Return the trajectory number of the last run (or None if there
           were no trajectory files in that run)"""
        if len(self.trajlist) <= 0:
            return None
        edr=self.trajlist[-1].get('edr')
        xtc=self.trajlist[-1].get('xtc')
        trr=self.trajlist[-1].get('trr')
        log.debug("edr=%s"%edr)
        log.debug("xtc=%s"%xtc)
        log.debug("trr=%s"%trr)
        nr=None
        try:
            if edr is not None:
                # extract all numbers, and get the final one:
                nrs=re.findall(r'\d+', edr)
                if len(nrs)>0:
                    nr=int(nrs[-1])
            elif xtc is not None:
                nrs=re.findall(r'\d+', xtc)
                if len(nrs)>0:
                    nr=int(nrs[-1])
            elif trr is not None:
                nrs=re.findall(r'\d+', trr)
                if len(nrs)>0:
                    nr=int(nrs[-1])
        except ValueError:
            pass
        return nr

    def getLastTrajNr(self):
        if self.lastTrajNr is not None:
            return self.lastTrajNr
        else:
            return 0

    def getFractionCompleted(self, tpr):
        """Get the fraction of steps completed."""
        # also check whether we need to check file numbers:
        checkFileNumbers=False
        if self.lastTrajNr is None:
            checkFileNumbers=True
        newFileNumber=0
        if self.lastcpt is not None:
            stepnr=0
            firststep=0
            nsteps=1
            # now check how far along the run is by inspecting the
            # step number we're at.
            cmd = self.cmdnames.gmxdump.split() + ['-cp', self.lastcpt]
            sp=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
            stepline=re.compile('step = .*')
            outfileline=re.compile('output filename = .*')
            for line in sp.stdout:
                if stepline.match(line):
                    stepnr=int(line.split('=')[1])
                    if not checkFileNumbers:
                        break
                elif checkFileNumbers and outfileline.match(line):
                    filename=line.split('=')[1]
                    nrs=re.findall(r'\d+', filename)
                    #log.debug("**NRS=%s, line=%s"%(nrs, line))
                    #for nr in nrs:
                    if len(nrs)>0:
                        nr=int(nrs[-1])
                        if nr > newFileNumber:
                            #log.debug("found new file number: %d"%(nr))
                            newFileNumber = nr
            sp.stdout.close()
            if checkFileNumbers:
                self.lastTrajNr=newFileNumber
            #sp.communicate()
            # and get the total step number
            cmd = self.cmdnames.gmxdump.split() + ['-s', tpr]
            sp=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
            stepline=re.compile('[ ]*nsteps.*')
            firststepline=re.compile('[ ]*init-step.*')
            for line in sp.stdout:
                if stepline.match(line):
                    nsteps=int(line.split()[2])
                elif firststepline.match(line):
                    firststep=int(line.split()[2])
                    break
            sp.stdout.close()
            #sp.communicate()
            return float(stepnr-firststep)/nsteps
        return 0

    def checkpointToConfout(self):
        """Convert a checkpoint file to a confout.gro"""

        if self.lastcpt is not None:
            outfile=os.path.join(self.lastDir, 'confout.part%04d.gro'  % self.getLastTrajNr())
            tprfile=os.path.join(self.lastDir, 'topol.tpr')
            cmd = self.cmdnames.trjconv.split()
            cmd += ['-f', self.lastcpt, '-s', tprfile, '-o', outfile]
            sp = subprocess.Popen(cmd, stdin = subprocess.PIPE,
                                  stdout = subprocess.PIPE,
                                  stderr = subprocess.PIPE)

            (output, err) = sp.communicate('System')
            if sp.returncode != 0:
                raise GromacsError("Error running trjconv: %s" % err)

            return outfile



def checkErr(stde, rsrc, tpr, persDir):
    """Check whether an error condition is recoverable.

       Returns True if there is an issue, False if the error is recoverable"""
    if not os.path.exists(stde):
        # we assume it's a worker error
        return False
    inf=open(stde, 'r')
    fatalErr=False
    OK=True
    for line in inf:
        if re.match(r'.*Fatal error.*', line):
            fatalErr=True
            log.debug("Found fatal error")
            OK=False
        if fatalErr:
            if re.match(r'.*domain decomposition.*', line):
                # the number of cores is wrong
                log.debug("Found domain decomp error")
                confFile=os.path.join(persDir, 'conf.gro')
                extractConf(tpr, confFile)
                tune.tune(rsrc, confFile, tpr, persDir, rsrc.max.get('cores')-1)
                OK=True
                break
    inf.close()
    return not OK


def extractData(confout, outDir, persDir, fo):
    """Concatenate all output data from the partial runs into the end results"""
    cmdnames = cmds.GromacsCommands()
    #outputs=dict()
    # Concatenate stuff
    confoutPath=os.path.join(outDir, "confout.gro")
    shutil.copy(confout[0], confoutPath )
    #outputs['conf'] = Value(confoutPath,
    #                        inp.function.getOutput('conf').getType())
    fo.setOut('conf', FileValue(confoutPath))
    # fix the xtc files
    xtcso = sorted(glob.glob(os.path.join(persDir, "run_???",
                                          "traj.*xtc")))
    # cull empty files and duplicate trajectory names
    xtcs=[]
    xtcbase=[]
    try:
        for file in xtcso:
            st=os.stat(file)
            base=os.path.split(file)[1]
            if st.st_size>0:
                if base not in xtcbase:
                    xtcs.append(file)
                    xtcbase.append(base)
                else:
                    # there already was a file with this name. Overwrite
                    # it because mdrun wasn't aware of it when writing.
                    ind=xtcbase.index(base)
                    xtcs[ind]=file
    except OSError:
        pass

    # concatenate them
    xtcoutname=os.path.join(outDir, "traj.xtc")
    if len(xtcs) > 0:
        cmd = cmdnames.trjcat.split() + ["-f"]
        cmd.extend(xtcs)
        cmd.extend(["-o", xtcoutname])
        stdo=open(os.path.join(persDir,"trjcat_xtc.out"),"w")
        sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
        sp.communicate(None)
        stdo.close()
        fo.setOut('xtc', FileValue(xtcoutname))
    # do the trrs
    trrso = sorted(glob.glob(os.path.join(persDir, "run_???",
                                          "traj.*trr")))
    # cull empty files and duplicate trajectory names
    trrs=[]
    trrbase=[]
    try:
        for file in trrso:
            st=os.stat(file)
            base=os.path.split(file)[1]
            if st.st_size>0:
                if base not in trrbase:
                    trrs.append(file)
                    trrbase.append(base)
                else:
                    # there already was a file with this name. Overwrite
                    # it because mdrun wasn't aware of it when writing.
                    ind=trrbase.index(base)
                    trrs[ind]=file
    except OSError:
        pass
    # concatenate them
    trroutname=os.path.join(outDir, "traj.trr")
    if len(trrs) > 0:
        cmd = cmdnames.trjcat.split() + ["-f"]
        cmd.extend(trrs)
        cmd.extend(["-o", trroutname])
        stdo=open(os.path.join(persDir,"trjcat_trr.out"),"w")
        sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
        sp.communicate(None)
        stdo.close()
        fo.setOut('trr', FileValue(trroutname))
    # and the edrs
    edrso = glob.glob(os.path.join(persDir, "run_???", "ener.*edr"))
    # cull empty files and duplicate trajectory names
    edrs=[]
    edrbase=[]
    try:
        for file in edrso:
            st=os.stat(file)
            base=os.path.split(file)[1]
            if st.st_size>0:
                if base not in edrbase:
                    edrs.append(file)
                    edrbase.append(base)
                else:
                    # there already was a file with this name. Overwrite
                    # it because mdrun wasn't aware of it when writing.
                    ind=edrbase.index(base)
                    log.debug("Overwriting existing edr file %s with %s" % (edrs[ind], file))
                    edrs[ind]=file
    except OSError:
        pass
    edroutname=os.path.join(outDir, "ener.edr")
    if len(edrs) > 1:
        log.debug("Concatenating edr files: %s" % edrs)
    # concatenate them
    if len(edrs) > 0:
        cmd = cmdnames.eneconv.split() + ["-f"]
        cmd.extend(edrs)
        cmd.extend(["-o", edroutname])
        stdo=open(os.path.join(persDir,"eneconv.out"),"w")
        sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
        sp.communicate(None)
        stdo.close()
        log.debug("Setting edr output to %s" % edroutname)
        fo.setOut('edr', FileValue(edroutname))
    # do the stdout
    stdouto = glob.glob(os.path.join(persDir, "run_???", "stdout"))
    stdoutname=os.path.join(outDir, "stdout")
    outf=open(stdoutname,"w")
    for infile in stdouto:
        inf=open(infile, "r")
        outf.write(inf.read())
        inf.close()
    outf.write("%s\n"%time.strftime("%a, %d %b %Y %H:%M:%S"))
    outf.write("%f\n"%time.time())
    outf.close()
    fo.setOut('stdout', FileValue(stdoutname))
    # do the stderr
    stderro = glob.glob(os.path.join(persDir, "run_???", "stderr"))
    stderrname=os.path.join(outDir, "stderr")
    outf=open(stderrname,"w")
    for infile in stderro:
        inf=open(infile, "r")
        outf.write(inf.read())
        inf.close()
    outf.close()
    fo.setOut('stderr', FileValue(stderrname))
    # and do md.log
    logo = glob.glob(os.path.join(persDir, "run_???", "md.*log"))
    logname=os.path.join(outDir, "md.log")
    outf=open(logname,"w")
    for infile in logo:
        inf=open(infile, "r")
        outf.write(inf.read())
        inf.close()
    outf.close()
    fo.setOut('log', FileValue(logname))

    log.debug("Returning without command.")
    log.debug("fo.cmds=%s"%str(fo.cmds))


def mdrun(inp):
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.trjcat)
        cpc.util.plugin.testCommand("%s -version" % cmdnames.eneconv)
        cpc.util.plugin.testCommand("%s -version" % cmdnames.gmxdump)
        return
    persDir=inp.getPersistentDir()
    outDir=inp.getOutputDir()
    fo=inp.getFunctionOutput()
    rsrc=Resources(inp.getInputValue("resources"))
    rsrcFilename=os.path.join(persDir, 'rsrc.dat')
    # check whether we need to reinit
    pers=cpc.dataflow.Persistence(os.path.join(persDir,
                                               "persistent.dat"))
    init=False
    lasttpr=pers.get('lasttpr')
    newtpr=inp.getInput('tpr')
    #if inp.getInputValue('tpr').isUpdated():
    if newtpr!= lasttpr:
        lasttpr=newtpr
        # there was no previous command.
        # purge the persistent directory, by moving the confout files to a
        # backup directory
        log.debug("(Re)initializing mdrun")
        confout=glob.glob(os.path.join(persDir, "run_???"))
        if len(confout)>0:
            backupDir=os.path.join(persDir, "backup")
            try:
                os.mkdir(backupDir)
            except OSError:
                pass
            for conf in confout:
                try:
                    os.rename(conf, os.path.join(backupDir,
                                                 os.path.split(conf)[-1]))
                except OSError:
                    pass
        init=True
        pers.set('lasttpr', lasttpr)
    elif inp.cmd is None:
        return fo
    if init:
        if rsrc.max.get('cores') is None:
            confFile=os.path.join(persDir, 'conf.gro')
            extractConf(newtpr, confFile)
            tune.tune(rsrc, confFile, newtpr, persDir)
        if inp.cmd is not None:
            log.debug("Canceling commands")
            fo.cancelPrevCommands()
        pers.set('initialized', True)
    else:
        if rsrc.max.get('cores') is None:
            rsrc.load(rsrcFilename)
    if inp.cmd is not None:
        log.debug("Return code was %s"%str(inp.cmd.getReturncode()))
    # try to find out whether the run has already finished
    confout=glob.glob(os.path.join(persDir, "run_???", "confout.*gro"))
    if len(confout) > 0:
        confoutDir = os.path.dirname(confout[0])
        hasFinalData = checkConfoutDir(confoutDir)
        if hasFinalData:
            log.debug("Extracting data. ")
            # confout exists. we're finished. Concatenate all the runs if
            # we need to, but first create the output dict
            extractData(confout, outDir, persDir, fo)
            return fo

    tfc=TrajFileCollection(persDir)
    lastDir = tfc.getLastDir()
    # first check whether we got an error code back
    if (inp.cmd is not None) and inp.cmd.getReturncode()!=0:
        # there was a problem. Check the log
        if lastDir:
            stde=os.path.join(lastDir, "stderr")
            if checkErr(stde, rsrc, newtpr, persDir):
                if os.path.exists(stde):
                    stdef=open(stde, 'r')
                    errmsg=unicode(stdef.read(), errors='ignore')
                    stdef.close()
                    raise MdrunError("Error running mdrun: %s"%errmsg)
        else:
            log.debug("An error has occured, but no lastDir was found.")

        # now check whether any of the last 4 iterations produced
        # trajectories
        trajlist=tfc.getTrajList()
        if len(trajlist) > 4:
            ret=False
            for j in range(4):
                haveTraj=(len(trajlist[-j-1]) > 0)
                ret=ret or haveTraj  #prevtraj[-j-1]
            if not ret:
                if lastDir:
                    stde=os.path.join(lastDir, "stderr")
                    if os.path.exists(stde):
                        stdef=open(stde, 'r')
                        errmsg=unicode(stdef.read(), errors='ignore')
                        stdef.close()
                    else:
                        errmsg=""
                    raise MdrunError("Error running mdrun. No trajectories: %s"%
                                    errmsg)
                else:
                    raise MdrunError("Error running mdrun. No trajectories and no lastDir was found.")
    # Make a new directory with the continuation of this run
    #newdirname=currundir #"run_%03d"%(i+1)
    newdirname=tfc.getNewRunDir()
    log.debug("Making a new directory for this run: %s" % newdirname)
    try:
        os.mkdir(newdirname)
    except OSError:
        log.debug("Directory already exists.")
        pass
    tpr=newtpr
    src=os.path.join(inp.getBaseDir(), tpr)
    dst=os.path.join(newdirname,"topol.tpr")
    shutil.copy(src,dst)
    # handle command line inputs
    if inp.getInput('cmdline_options') is not None:
        cmdlineOpts=shlex.split(inp.getInput('cmdline_options'))
    else:
        cmdlineOpts=[]
    if inp.getInput('priority') is not None:
        prio=inp.getInput('priority')
    else:
        prio=0
    lastcpt=tfc.getLastCpt()
    # copy the checkpoint to the new cmd dir
    if lastcpt is not None:
        shutil.copy(lastcpt, os.path.join(newdirname,"state.cpt"))
        log.debug("Continuing from checkpoint")
    # now add to the priority if this run has already been started
    completed=tfc.getFractionCompleted(tpr)
    if completed > 0:
        log.debug("Fraction completed: %s" % completed)
        # Already finished, but no confout.gro?
        if completed >= 1:
            log.debug("Iteration finished, but the final coordinates were not written.")
            if tfc.trajlist[-1].get('edr') or tfc.trajlist[-1].get('xtc') or tfc.trajlist[-1].get('trr'):
                log.debug("Last run produced output files without gaps (but no confout.gro). Generating coordinates from checkpoint.")
                confout=tfc.checkpointToConfout()
                if confout:
                    log.debug("Extracting data.")
                    extractData([confout], outDir, persDir, fo)
                    return fo
            else:
                log.debug("Last run did not produce any output files. Cannot generate coordinates from checkpoint.")
        # now the priority ranges from 1 to 4, depending on how
        # far along the simulation is.
        prio += 1+int(3*(completed))
        log.debug("Setting new priority to %d because it's in progress"%
                  prio)
    # we can always add state.cpt, even if it doesn't exist.
    args=["-quiet", "-s", "topol.tpr", "-noappend", "-cpi", "state.cpt",
           "-rcon", "0.7"  ]
    args.extend(cmdlineOpts)
    # for the new neighbor search scheme in Gromacs 4.6, set this env
    # variable

    # any expected output files.
    newFileNr=tfc.getLastTrajNr()+1
    outputFiles=[ "traj.part%04d.xtc"%newFileNr,
                  "traj.part%04d.trr"%newFileNr,
                  "confout.part%04d.gro"%newFileNr,
                  "ener.part%04d.edr"%newFileNr,
                  "dhdl.part%04d.xvg"%newFileNr,
                  "pullx.part%04d.xvg"%newFileNr,
                  "pullf.part%04d.xvg"%newFileNr,
                  "md.part%04d.log"%newFileNr,
                  "state.cpt", "state_prev.cpt" ]
    log.debug("Expected output files: %s"%outputFiles)
    cmd=cpc.command.Command(newdirname, "gromacs/mdrun",args,
                            minVersion=cpc.command.Version("4.5"),
                            addPriority=prio,
                            outputFiles=outputFiles)
    if inp.hasInput("resources") and inp.getInput("resources") is not None:
        #log.debug("resources is %s"%(inp.getInput("resources")))
        #rsrc=Resources(inp.getInputValue("resources"))
        rsrc.updateCmd(cmd)
    log.debug("Adding command")
    fo.addCommand(cmd)
    if inp.getInputValue('tpr').isUpdated() and inp.cmd is not None:
        log.debug("Canceling commands")
        fo.cancelPrevCommands()

    # and save for further invocations
    rsrc.save(rsrcFilename)
    pers.write()
    return fo



