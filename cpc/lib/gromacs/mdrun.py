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
import shlex
import glob
import stat
import subprocess
import logging
import time


log=logging.getLogger('cpc.lib.mdrun')


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import StringValue
from cpc.dataflow import Resources
import cpc.server.command
import cpc.util

import tune
import iterate

class GromacsError(cpc.util.CpcError):
    pass

def extractConf(tprFile, confFile):
    """Extract a configuration to confFile from tprFile."""
    cmdlist=['editconf', '-f', tprFile, '-o', confFile]
    proc=subprocess.Popen(cmdlist, 
                          stdin=None,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=os.path.split(confFile)[0])
    proc.communicate(None)
    if proc.returncode != 0:
        raise GromacsError("Error running editconf: %s"%
                           (open(stdoutfn,'r').read()))



def procSettings(inp, outMdpDir):
    """Process settings into a new mdp file, or return the old mdp file if
       there are no additional settings."""
    mdpfile=inp.getInput('mdp')
    if ( inp.hasInput('settings') and len(inp.getInput('settings'))>0 ):
        repl=dict()
        if inp.hasInput('settings'):
            settings=inp.getInput('settings')
            for setting in settings:
                if ("name" in setting.value) and ("value" in setting.value):
                    val = setting.value["value"].value
                    name = setting.value["name"].value
                    name = name.strip().replace('-', '_').lower()
                    repl[name] = val
        # now set the gen_vel option
        outMdpName=os.path.join(outMdpDir, "grompp.mdp")
        outf=open(outMdpName, "w")
        inf=open(mdpfile, "r")
        for line in inf:
            sp=line.split('=')
            if len(sp) == 2:
                key=sp[0].strip().replace('-', '_').lower()
                if key in repl:
                    outf.write('%s = %s\n'%(key, str(repl[key])))
                    del repl[key]
                else:
                    outf.write(line)
        # and write our remaining options 
        for key, value in repl.iteritems():
            outf.write('%s = %s\n'%(key, str(value)))
        outf.close()
        return outMdpName
    else:
        return mdpfile



def grompp(inp):
    if inp.testing(): 
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("grompp -version")
        return 

    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
                                               "persistent.dat"))
    fo=inp.getFunctionOutput()
    if not (inp.getInputValue('conf').isUpdated() or 
            inp.getInputValue('top').isUpdated() or 
            inp.getInputValue('include').isUpdated() or 
            inp.getInputValue('settings').isUpdated() or
            inp.getInputValue('ndx').isUpdated()):
        if pers.get('init') is not None:
            return fo
    if pers.get('init') is not None:
        log.debug("conf: %s"%(inp.getInputValue('conf').isUpdated()))
        log.debug("top: %s"%(inp.getInputValue('top').isUpdated()))
        log.debug("include: %s"%(inp.getInputValue('include').isUpdated()))
        log.debug("settings: %s"%(inp.getInputValue('settings').isUpdated()))
        log.debug("ndx: %s"%(inp.getInputValue('ndx').isUpdated()))

    pers.set('init', 1)
    mdpfile=procSettings(inp, inp.outputDir)
    # copy the topology and include files 
    topfile=os.path.join(inp.outputDir, 'topol.top')
    shutil.copy(inp.getInput('top'), topfile)
    incl=inp.getInput('include')
    if incl is not None and len(incl)>0:
        for i in range(len(incl)):
            filename=inp.getInput('include[%d]'%i)
            if filename is not None:
                # same name, but in one directory.
                nname=os.path.join(inp.outputDir, os.path.split(filename)[1])
                shutil.copy(filename, nname)
    # and execute grompp
    cmdlist=[ "grompp", "-f", mdpfile,
              "-quiet",
              "-c", inp.getInput('conf'),
              "-p", 'topol.top', # we made sure it's there
              "-o", "topol.tpr" ]
    if inp.hasInput('ndx'):
        cmdlist.append('-n')
        cmdlist.append(inp.getInput('ndx'))
    # TODO: symlink all the auxiliary files into the run dir
    stdoutfn=os.path.join(inp.outputDir, "stdout")
    stdoutf=open(stdoutfn,"w")
    stdoutf.write("%s\n"%time.strftime("%a, %d %b %Y %H:%M:%S"))
    stdoutf.write("%f\n"%time.time())
    #stdoutf=open(os.path.join(inp.outputDir, "stderr"),"w")
    proc=subprocess.Popen(cmdlist, 
                          stdin=None,
                          stdout=stdoutf,
                          stderr=subprocess.STDOUT,
                          cwd=inp.outputDir)
    proc.communicate(None)
    stdoutf.close()
    if proc.returncode != 0:
        raise GromacsError("Error running grompp: %s"%
                           (open(stdoutfn,'r').read()))
    fo.setOut('stdout', FileValue(stdoutfn))
    fo.setOut('tpr', FileValue(os.path.join(inp.outputDir, "topol.tpr")))
    pers.write()
    return fo


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
                    lastfound=True
                    lastrundir=currundir
                    cpt=os.path.join(lastrundir, "state.cpt")
                    if os.path.exists(cpt):
                        # and check the size
                        st=os.stat(cpt)
                        if st.st_size>0: 
                            self.lastcpt=cpt
                    # now check if this has produced trajectories
                    trajl=dict()
                    xtc = glob.glob(os.path.join(lastrundir, "traj.part*.xtc"))
                    trr = glob.glob(os.path.join(lastrundir, "traj.part*.trr"))
                    edr = glob.glob(os.path.join(lastrundir, "ener.part*.edr"))
                    trajl['xtc']=None
                    if len(xtc) > 0:
                        trajl['xtc']=xtc[-1]
                    if len(trr) > 0:
                        trajl['trr']=trr[-1]
                    if len(edr) > 0:
                        trajl['edr']=edr[-1]
                    self.trajlist.append(trajl)
            except OSError:
                pass
        self.lastDirNr=i
        self.lastDir=lastrundir
        self.newRunDir=currundir
        self.lastTrajNr=self._extractLastTrajNr()

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
            # now check how far along the run is by inspecting the
            # step number we're at.
            cmd=['gmxdump', '-cp', self.lastcpt ]
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
            cmd=['gmxdump', '-s', tpr ]
            sp=subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
            stepline=re.compile('[ ]*nsteps.*')
            for line in sp.stdout:
                if stepline.match(line):
                    nsteps=int(line.split()[2])
                    break
            sp.stdout.close()
            #sp.communicate()
            return float(stepnr)/float(nsteps)
        return 0


def mdrun(inp):
    if inp.testing(): 
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("trjcat -version")
        cpc.util.plugin.testCommand("eneconv -version")
        cpc.util.plugin.testCommand("gmxdump -version")
        return 
    persDir=inp.getPersistentDir()
    outDir=inp.getOutputDir()
    fo=inp.getFunctionOutput()
    rsrc=Resources(inp.getInputValue("resources"))
    rsrcFilename=os.path.join(persDir, 'rsrc.dat')
    # check whether we need to reinit

    #log.debug("tpr updated: %s"%(inp.getInputValue('tpr').isUpdated()))
    #log.debug("resources updated: %s"%
    #          (inp.getInputValue('resources').isUpdated()))
    #log.debug("cmdline_options updated: %s"%
    #          (inp.getInputValue('cmdline_options').isUpdated()))
    #log.debug("priority updated: %s"%
    #          (inp.getInputValue('priority').isUpdated()))
    #if inp.cmd is None and inp.getInputValue('tpr').isUpdated():

    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
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
            except:
                pass
            for conf in confout:
                try:
                    os.rename(conf, os.path.join(backupDir, 
                                                 os.path.split(conf)[-1]))
                except:
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
    # try to find out whether the run has already finished
    confout=glob.glob(os.path.join(persDir, "run_???", "confout.part*.gro"))
    if len(confout) > 0:
        log.debug("Extracting data")
        # confout exists. we're finished. Concatenate all the runs if
        # we need to, but first create the output dict
        #outputs=dict()
        # Concatenate stuff
        confoutPath=os.path.join(outDir, "confout.gro")
        shutil.copy(confout[0], confoutPath ) 
        #outputs['conf'] = Value(confoutPath, 
        #                        inp.function.getOutput('conf').getType())
        fo.setOut('conf', FileValue(confoutPath))
        # fix the xtc files
        xtcso = sorted(glob.glob(os.path.join(persDir, "run_???", 
                                              "traj.part*.xtc")))
        # cull empty files and duplicate trajectory names
        xtcs=[]
        xtcbase=[]
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

        # concatenate them
        xtcoutname=os.path.join(outDir, "traj.xtc")
        if len(xtcs) > 0:
            cmd=["trjcat", "-f"]
            cmd.extend(xtcs)
            cmd.extend(["-o", xtcoutname])
            stdo=open(os.path.join(persDir,"trjcat_xtc.out"),"w")
            sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
            sp.communicate(None)
            stdo.close()
            #outputs['xtc'] = Value(xtcoutname, 
            #                       inp.function.getOutput('xtc').getType())
            fo.setOut('xtc', FileValue(xtcoutname))
        # do the trrs
        trrso = sorted(glob.glob(os.path.join(persDir, "run_???", 
                                              "traj.part*.trr")))
        # cull empty files and duplicate trajectory names
        trrs=[]
        trrbase=[]
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
        # concatenate them
        trroutname=os.path.join(outDir, "traj.trr")
        if len(trrs) > 0:
            cmd=["trjcat", "-f"]
            cmd.extend(trrs)
            cmd.extend(["-o", trroutname])
            stdo=open(os.path.join(persDir,"trjcat_trr.out"),"w")
            sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
            sp.communicate(None)
            stdo.close()
            #outputs['trr'] = Value(trroutname, 
            #                       inp.function.getOutput('trr').getType())
            fo.setOut('trr', FileValue(trroutname))
        # and the edrs
        edrso = glob.glob(os.path.join(persDir, "run_???", "ener.part*.edr"))
        # cull empty files and duplicate trajectory names
        edrs=[]
        edrbase=[]
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
                    edrs[ind]=file
        edroutname=os.path.join(outDir, "ener.edr")
        # concatenate them
        if len(edrs) > 0:
            cmd=["eneconv", "-f"]
            cmd.extend(edrs)
            cmd.extend(["-o", edroutname])
            stdo=open(os.path.join(persDir,"eneconv.out"),"w")
            sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
            sp.communicate(None)
            stdo.close()
            #outputs['edr'] = Value(edroutname, 
            #                       inp.function.getOutput('edr').getType())
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
        #outputs['stdout'] = Value(stdoutname, 
        #                          inp.function.getOutput('trr').getType())
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
        log.debug("Returning without command.")
        log.debug("fo.cmds=%s"%str(fo.cmds))
        return fo
    else:
        tfc=TrajFileCollection(persDir)
        # now check whether any of the last 4 iterations produced trajectories
        trajlist=tfc.getTrajList()
        if len(trajlist) > 4:
            ret=False
            for j in range(4):
                haveTraj=(len(trajlist[-j-1]) > 0)
                ret=ret or haveTraj  #prevtraj[-j-1]
            if not ret:
                stde=os.path.join(lastrundir, "stderr")
                if os.path.exists(stde):
                    stdef=open(stde, 'r')
                    # TODO fix unicode
                    errmsg=unicode(stdef.read(), errors='ignore')
                    stdef.close()
                else:
                    errmsg=""
                raise GromacsError("Error running mdrun. No trajectories: %s"%
                                   errmsg)
        # Make a new directory with the continuation of this run
        #newdirname=currundir #"run_%03d"%(i+1)
        newdirname=tfc.getNewRunDir()
        try:
            os.mkdir(newdirname)
        except OSError:
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
        # now add to the priority if this run has already been started
        completed=tfc.getFractionCompleted(tpr)
        if completed > 0:
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
        cenv={ 'GMX_VERLET_SCHEME': '1' }
        if lastcpt is not None:
            shutil.copy(lastcpt, os.path.join(newdirname,"state.cpt"))
        # any expected output files.
        newFileNr=tfc.getLastTrajNr()+1
        outputFiles=[ "traj.part%04d.xtc"%newFileNr, 
                      "traj.part%04d.trr"%newFileNr, 
                      "confout.part%04d.gro"%newFileNr, 
                      "ener.part%04d.edr"%newFileNr, 
                      "dhdl.part%04d.xvg"%newFileNr, 
                      "pullx.part%04d.xvg"%newFileNr, 
                      "pullf.part%04d.xvg"%newFileNr, 
                      "state.cpt", "state_prev.cpt" ]
        log.debug("Expected output files: %s"%outputFiles)
        cmd=cpc.server.command.Command(newdirname, "gromacs/mdrun",args,
                                 minVersion=cpc.server.command.Version("4.5"),
                                 addPriority=prio, env=cenv, 
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


def merge_mdp(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        return
    fo=inp.getFunctionOutput()
    mdpfile=procSettings(inp, inp.outputDir)
    fo.setOut('mdp', FileValue(mdpfile))
    return fo

def extract_mdp(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        return
    fo=inp.getFunctionOutput()
    keyFind=inp.getInput('name')
    keyFind=keyFind.strip().replace('-', '_').lower()
    setVal=None
    mdpfile=inp.getInput('mdp')
    #if ( inp.hasInput('settings') and len(inp.getInput('settings'))>0 ):
    repl=dict()
    if inp.hasInput('settings'):
        settings=inp.getInput('settings')
        for setting in settings:
            if ("name" in setting.value) and ("value" in setting.value):
                val = setting.value["value"].value
                name = setting.value["name"].value
                name = name.strip().replace('-', '_').lower()
                if name == keyFind:
                    setVal=val
    if setVal is None:
        #outMdpName=os.path.join(outMdpDir, "grompp.mdp")
        #outf=open(outMdpName, "w")
        inf=open(mdpfile, "r")
        for line in inf:
            sp=line.split('=')
            if len(sp) == 2:
                key=sp[0].strip().replace('-', '_').lower()
                if key==keyFind:
                    setVal=sp[1].strip()
    if setVal is not None:
        fo.setOut('value', StringValue(setVal))
    return fo

def tune_fn(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        #cpc.util.plugin.testCommand("grompp -version")
        #cpc.util.plugin.testCommand("mdrun -version")
        return
    fo=inp.getFunctionOutput()
    persDir=inp.getPersistentDir()
    mdpfile=procSettings(inp, inp.outputDir)
    # copy the topology and include files 
    topfile=os.path.join(inp.outputDir, 'topol.top')
    shutil.copy(inp.getInput('top'), topfile)
    incl=inp.getInput('include')
    if incl is not None and len(incl)>0:
        for i in range(len(incl)):
            filename=inp.getInput('include[%d]'%i)
            if filename is not None:
                # same name, but in one directory.
                nname=os.path.join(inp.outputDir, os.path.split(filename)[1])
                shutil.copy(filename, nname)
    # and execute grompp
    cmdlist=[ "grompp", "-f", mdpfile,
              "-quiet",
              "-c", inp.getInput('conf'),
              "-p", 'topol.top', # we made sure it's there
              "-o", "topol.tpr" ]
    if inp.hasInput('ndx'):
        cmdlist.append('-n')
        cmdlist.append(inp.getInput('ndx'))
    proc=subprocess.Popen(cmdlist, 
                          stdin=None,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          cwd=inp.outputDir)
    (stdo, stde) = proc.communicate(None)
    if proc.returncode != 0:
        raise GromacsError("Error running grompp: %s, %s"%
                           (stdo, stde))
    rsrc=Resources()
    tune.tune(rsrc, inp.getInput('conf'), 
              os.path.join(inp.outputDir, 'topol.tpr'), persDir)
    fo.setOut('mdp', FileValue(mdpfile))
    fo.setOut('resources', rsrc.setOutputValue())
    return fo

def grompp_multi(inp):
    if inp.testing():
    # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("grompp -version")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
                                               "persistent.dat"))

    inputs = ['mdp','top','conf', 'ndx', 'settings', 'include']
    outputs = [ 'tpr' ]
    running=0
    if(pers.get("running")):
        running=pers.get("running")
    it=iterate.iterations(inp, inputs, outputs, pers)
    out=inp.getFunctionOutput()
    for i in range(running, it.getN()):
        instName="grompp_%d"%i
        out.addInstance(instName, "grompp")
        it.connect(out, i, instName)
        out.addConnection("%s:out.tpr"%instName, "self:ext_out.tpr[%d]"%i)
        running+=1
    pers.set("running", running)
    pers.write()
    return out




def mdrun_multi(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("trjcat -version")
        cpc.util.plugin.testCommand("eneconv -version")
        cpc.util.plugin.testCommand("gmxdump -version")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
                                               "persistent.dat"))

    inputs = ['tpr','priority','cmdline_options','resources']
    outputs = [ 'conf', 'xtc', 'trr', 'edr' ]
    running=0
    if(pers.get("running")):
        running=pers.get("running")
    it=iterate.iterations(inp, inputs, outputs, pers)
    out=inp.getFunctionOutput()
    for i in range(running, it.getN()):
        instName="mdrun_%d"%i
        out.addInstance(instName, "mdrun")
        it.connect(out, i, instName)
        running+=1
    pers.set("running", running)
    pers.write()
    return out


def grompp_mdrun_multi(inp):
    if inp.testing():
    # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("grompp -version")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
                                               "persistent.dat"))

    grompp_inputs = ['mdp','top','conf', 'ndx', 'settings', 'include' ]
    mdrun_inputs = [ 'priority', 'cmdline_options', 'resources']
    inputs = grompp_inputs + mdrun_inputs
    grompp_outputs = [ 'tpr' ]
    mdrun_outputs = [ 'conf', 'xtc', 'trr', 'edr' ]
    outputs = grompp_outputs + mdrun_outputs
    running=0
    if(pers.get("running")):
        running=pers.get("running")
    it=iterate.iterations(inp, inputs, outputs, pers)
    out=inp.getFunctionOutput()
    for i in range(running, it.getN()):
        gromppInstName="grompp_%d"%i
        mdrunInstName="mdrun_%d"%i
        out.addInstance(gromppInstName, "grompp")
        out.addInstance(mdrunInstName, "mdrun")
        out.addConnection('%s:out.tpr'%gromppInstName, 
                          '%s:in.tpr'%mdrunInstName)
        it.connectOnly(grompp_inputs, grompp_outputs, out, i, gromppInstName)
        it.connectOnly(mdrun_inputs, mdrun_outputs, out, i, mdrunInstName)
        running+=1
    pers.set("running", running)
    pers.write()
    return out

