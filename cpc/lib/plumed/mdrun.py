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


log=logging.getLogger(__name__)


from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import FloatValue
from cpc.dataflow import StringValue
from cpc.dataflow import Resources
import cpc.command
import cpc.util

import cpc.lib.gromacs.tune as tune
import cpc.lib.gromacs.iterate as iterate
from cpc.lib.gromacs import cmds
from cpc.lib.gromacs.mdrun import extractConf, TrajFileCollection, MdrunError

class PLUMEDError(cpc.util.CpcError):
   pass


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
        if re.match(r'.*PLUMED ERROR.*', line):
            fatalErr=True
            log.debug("Found a PLUMED error.")
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
        cmd = cmdnames.trjcat + ["-f"]
        cmd.extend(trrs)
        cmd.extend(["-o", trroutname])
        stdo=open(os.path.join(persDir,"trjcat_trr.out"),"w")
        sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
        sp.communicate(None)
        stdo.close()
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
        cmd = cmdnames.eneconv.split() + ["-f"]
        cmd.extend(edrs)
        cmd.extend(["-o", edroutname])
        stdo=open(os.path.join(persDir,"eneconv.out"),"w")
        sp=subprocess.Popen(cmd, stdout=stdo, stderr=subprocess.STDOUT)
        sp.communicate(None)
        stdo.close()
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
    
    # do the COLVAR file
    colvaro = glob.glob(os.path.join(persDir, "run_???", "COLVAR"))
    colvarname=os.path.join(outDir, "COLVAR")
    outf=open(colvarname,'w')
    for cvfile in colvaro:
        inf=open(cvfile,'r')
        outf.write(inf.read())
        inf.close()
    outf.close()
    fo.setOut('COLVAR',FileValue(colvarname))

    # take the last HILLS file and the bias.dat file
    hillso = glob.glob(os.path.join(persDir, "run_???", "HILLS"))
    if len(hillso)>0:
      hillsname = os.path.join(outDir, "HILLS")
      outf = open(hillsname,'w')
      inf = open(hillso[-1],'r')
      outf.write(inf.read())
      inf.close()
      log.debug("Set the HILLS outfile")
      fo.setOut('HILLS',FileValue(hillsname))

    biaso = glob.glob(os.path.join(persDir, "run_???", "bias.dat"))
    if len(biaso)>0:
      biasname = os.path.join(outDir, "bias.dat")
      outf = open(biasname,'w')
      inf = open(biaso[-1],'r')
      outf.write(inf.read())
      inf.close()
      fo.setOut('bias',FileValue(biasname))



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
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
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
    if inp.cmd is not None:
        log.debug("Return code was %s"%str(inp.cmd.getReturncode()))
    # try to find out whether the run has already finished
    confout=glob.glob(os.path.join(persDir, "run_???", "confout.part*.gro"))
    if len(confout) > 0:
        log.debug("Extracting data. ")
        # confout exists. we're finished. Concatenate all the runs if
        # we need to, but first create the output dict
        extractData(confout, outDir, persDir, fo)
        return fo
    else:
        tfc=TrajFileCollection(persDir)
        # first check whether we got an error code back
        if (inp.cmd is not None) and inp.cmd.getReturncode()!=0:
            # there was a problem. Check the log
            stde=os.path.join(tfc.getLastDir(), "stderr")
            if checkErr(stde, rsrc, newtpr, persDir):
                if os.path.exists(stde):
                    stdef=open(stde, 'r')
                    errmsg=unicode(stdef.read(), errors='ignore')
                    stdef.close()
                    raise MdrunError("Error running mdrun: %s"%errmsg)
        else:
            # now check whether any of the last 4 iterations produced 
            # trajectories
            trajlist=tfc.getTrajList()
            if len(trajlist) > 4:
                ret=False
                for j in range(4):
                    haveTraj=(len(trajlist[-j-1]) > 0)
                    ret=ret or haveTraj  #prevtraj[-j-1]
                if not ret:
                    stde=os.path.join(tfc.getLastDir(), "stderr")
                    if os.path.exists(stde):
                        stdef=open(stde, 'r')
                        errmsg=unicode(stdef.read(), errors='ignore')
                        stdef.close()
                    else:
                        errmsg=""
                    raise MdrunError("Error running mdrun. No trajectories: %s"%
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
        # include the plumed file here
        args=["-quiet", "-s", "topol.tpr", "-noappend", "-cpi", "state.cpt",
               "-rcon", "0.7", "-plumed", "plumed.dat" ]
        args.extend(cmdlineOpts)
        # for the new neighbor search scheme in Gromacs 4.6, set this env 
        # variable
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
                      "COLVAR",
                      "HILLS",
                      "bias.dat",
                      "state.cpt", "state_prev.cpt" ]
        log.debug("Expected output files: %s"%outputFiles)
        cmd=cpc.command.Command(newdirname, "plumed/mdrun",args,
                                minVersion=cpc.command.Version("4.5"),
                                addPriority=prio,
                                outputFiles=outputFiles)
        if inp.hasInput("resources") and inp.getInput("resources") is not None:
            #log.debug("resources is %s"%(inp.getInput("resources")))
            #rsrc=Resources(inp.getInputValue("resources"))
            rsrc.updateCmd(cmd)
        log.debug("Adding command")
         # copy the plumed file to the run dir
        plumed_inp=inp.getInput("plumed")
        log.debug("Adding the PLUMED file: %s"%plumed_inp)
        src=os.path.join(inp.getBaseDir(),plumed_inp)
        dst=os.path.join(newdirname,"plumed.dat")
        # check if we need to restart metadynamics
        if tfc.lastDir is not None:
          lasthills=os.path.join(tfc.lastDir,"HILLS")
          if os.path.isfile(lasthills):
            plumed_dat=open(plumed_inp,'r').read()
            log.debug("Adding a RESTART statement to the PLUMED file.")
            newplumed=re.sub(r"HILLS","HILLS RESTART",plumed_dat)
            open(dst,"w").write(newplumed)
            newhills=os.path.join(newdirname,"HILLS")
            shutil.copy(lasthills,newhills)
          else: shutil.copy(src,dst)
        else: shutil.copy(src,dst)

        fo.addCommand(cmd)
        if inp.getInputValue('tpr').isUpdated() and inp.cmd is not None:
            log.debug("Canceling commands")
            fo.cancelPrevCommands()
    # and save for further invocations
    rsrc.save(rsrcFilename)
    pers.write()
    return fo



def grompp_mdruns(inp):
    if inp.testing():
    # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("grompp -version")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))

    grompp_inputs = ['mdp','top','conf', 'ndx', 'settings', 'include' ]
    mdrun_inputs = [ 'priority', 'cmdline_options', 'resources', 'plumed']
    inputs = grompp_inputs + mdrun_inputs
    grompp_outputs = [ 'tpr' ]
    mdrun_outputs = [ 'conf', 'xtc', 'trr', 'edr','COLVAR','HILLS','bias' ]
    outputs = grompp_outputs + mdrun_outputs
    running=0
    if(pers.get("running")):
        running=pers.get("running")
    it=iterate.iterations(inp, inputs, outputs, pers)
    out=inp.getFunctionOutput()
    for i in range(running, it.getN()):
        gromppInstName="grompp_%d"%i
        mdrunInstName="mdrun_%d"%i
        try:
          out.addInstance(gromppInstName, "gromacs::grompp")
        except:
          log.debug("Error: You must import the gromacs module to use this function.")
        out.addInstance(mdrunInstName, "mdrun")
        out.addConnection('%s:out.tpr'%gromppInstName, 
                          '%s:in.tpr'%mdrunInstName)
        it.connectOnly(grompp_inputs, grompp_outputs, out, i, gromppInstName)
        it.connectOnly(mdrun_inputs, mdrun_outputs, out, i, mdrunInstName)
        running+=1
    pers.set("running", running)
    pers.write()
    return out

def mdruns(inp):
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("trjcat -version")
        cpc.util.plugin.testCommand("eneconv -version")
        cpc.util.plugin.testCommand("gmxdump -version")
        return

    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))

    inputs = ['tpr','priority','cmdline_options','resources','plumed']
    outputs = [ 'conf', 'xtc', 'trr', 'edr','COLVAR', 'HILLS', 'bias']
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

