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



import os
import sys
import subprocess
import re
import logging

import traceback
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


from scipy.stats import halfnorm
import scipy 
import scipy.sparse
import random
from numpy import where
from numpy import array,argmax
import numpy
#import random

import matplotlib
#Use a non GUI backend for matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Make sure msmbuilder is in the PYTHONPATH
from msmbuilder.CopernicusProject import *
import msmbuilder.MSMLib
import msmbuilder.Serializer
import msmbuilder.Trajectory
#import DataFile

# cpc stuff
import cpc.dataflow
from cpc.dataflow import FileValue
from cpc.lib.gromacs import cmds

log=logging.getLogger(__name__)


class TrajData(object):
    """Information about a trajectory"""
    def __init__(self, lh5, xtc, xtc_nopbc, tpr, dt, frames):
        self.lh5=lh5
        self.xtc=xtc
        self.xtc_nopbc=xtc_nopbc
        self.tpr=tpr
        self.dt=dt
        self.frames=frames


class MSMProject(object):
    ''' MSM specific project data '''

    # the name of the top-level element for this project data type
    elementName = ""

    def __init__(self, inp, out):
        ''' Initialize MSMProject '''
        self.inp=inp
        self.out=out # the output of this call of the MSM function

        self.num_micro     = inp.getInput('num_microstates')
        if self.num_micro <= 1:
            sys.stderr("Error: num_micro=%d: invalid number\n"%self.num_micro)
        self.num_macro     = int(inp.getInput('num_macrostates'))
        if self.num_macro <= 1:
            sys.stderr("Error: num_macro=%d: invalid number\n"%self.num_macro)
        self.ref_conf      = inp.getInput('reference')
        self.grpname       = inp.getInput('grpname')
        #self.num_sim       = inp.getInput('num_to_start')
        self.lag_time      = inp.getInput('lag_time')
        self.cmdnames = cmds.GromacsCommands()

        #TODO IMAN get input weights
        if self.lag_time is not None and self.lag_time <= 0:
            sys.stderr("Error: lag_time=%g: invalid number\n"%self.lag_time)

        if  inp.getInput('ndx') is not None:
            self.ndx = inp.getInput('ndx')
        else:
            self.ndx = None

        # The msm-builder project
        self.Proj = None

        # The assignments from msm-builder
        self.assignments = None

        # The transition count matrix from msm-builder
        self.T = None

        # The desired lag time
        self.max_time = None

        # Sims to start per round
        self.num_to_start = int(inp.getInput('start_per_state'))

        # handle trajectories
        self.avgtime=0.
        self.filelist=[]
        self.trajData=dict()
        ta=self.inp.getInput('trajectories')
        i=0
        for traj in ta:
            lh5=self.inp.getInput('trajectories[%d].lh5'%i)
            xtc=self.inp.getInput('trajectories[%d].xtc'%i)
            xtc_nopbc=self.inp.getInput('trajectories[%d].xtc_nopbc'%i)
            tpr=self.inp.getInput('trajectories[%d].tpr'%i)
            dt=self.inp.getInput('trajectories[%d].dt'%i)
            frames=self.inp.getInput('trajectories[%d].frames'%i)
            self.filelist.append([lh5])
            self.trajData[lh5]=TrajData(lh5, xtc, xtc_nopbc, tpr, dt, frames)
            self.avgtime += dt * (frames-1)/1000.
            i+=1
        self.avgtime /= i
        sys.stderr.write("Average trajectory time: %g ns\n"%(self.avgtime))
        sys.stderr.write("filelist size=%d.\n"%(len(self.filelist)))

        random.seed()


    #def updateBoxVectors(self):
    #    ''' Fixes new box-vectors on all gro-files in the RandomConfs-dir '''
    #    
    #    grolist = []
    #
    #    files = os.listdir('RandomConfs')
    #    for f in files:
    #        if f.endswith('.gro'):
    #            confFile = os.path.join('RandomConfs',f)
    #            
    #            cmd = 'sed \'$d\' < %s > foo; mv foo %s'%(confFile,confFile)
    #            retcode = subprocess.call(cmd,shell=True)
    #            cmd = 'tail -n 1 %s >> %s'%(self.grofile[0],confFile)
    #            retcode = subprocess.call(cmd,shell=True)
    #            
    #            grolist.append(f)
    # 
    #    return grolist           

                

    #def listRandomConfs(self):
    #    ''' Makes a list of all gro-files in the RandomConfs dir '''
    #    grolist = []
    #    files = os.listdir(self.inp.getOutputDir())
    #    for f in files:
    #        if f.endswith('.gro'):
    #            grolist.append(f)
    #    return grolist
    #    

    def getNewSimTime(self):
        ''' Compute a new simulation time from a half-normal distribution '''
     
        # Extend to 400 ns (hardcoded for villin)
        new_length = 400000
        
        r = random.random()

        if(r>0.9):
            nst = int(new_length/self.dt)
        else:
            nst = 25000000
    
        return nst


    def createMicroStates(self):
        ''' Build a micro-state MSM '''
        sys.stderr.write("Creating msm project, ref_conf=%s.\n"%
                         str(self.ref_conf))
        # Create the msm project from the reference conformation
        #TODO IMAN provide weighting here
        Proj = CreateCopernicusProject(self.ref_conf, self.filelist)
        self.Proj = Proj
        C1   = Conformation.Conformation.LoadFromPDB(self.ref_conf)
        
        # Automate the clustering to only CA or backbone atoms
        # TODO: fix this
        a = C1["AtomNames"]
        AtomIndices=where((a=="N") | (a=="C") | (a=="CA") | (a=="O"))[0]
        
        sys.stderr.write("Cluster project.\n")
        # Do msm-stuff
        GenF = os.path.join('Data','Gens.nopbc.h5')
        AssF = os.path.join('Data','Ass.nopbc.h5')
        AssFTrimmed = os.path.join('Data','Assignment-trimmed.nopbc.h5')
        RmsF = os.path.join('Data','RMSD.nopbc.h5')
        
        Generators = Proj.ClusterProject(AtomIndices=AtomIndices,
                                         NumGen=self.num_micro,Stride=30)
        sys.stderr.write("Assign project.\n")
        Assignments,RMSD,WhichTrajs = Proj.AssignProject(Generators,
                                                       AtomIndices=AtomIndices)
        if os.path.exists(GenF):
            os.remove(GenF)
        Generators.SaveToHDF(GenF)
        if os.path.exists(AssF):
            os.remove(AssF)
        msmbuilder.Serializer.SaveData(AssF,Assignments)
        if os.path.exists(RmsF):
            os.remove(RmsF)
        msmbuilder.Serializer.SaveData(RmsF,RMSD)
        
        sys.stderr.write("Trim data.\n")
        # Trim data
        Counts = msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                       self.num_micro,
                                                       LagTime=1,
                                                       Slide=True)
                
        # Get the most populated state
        sys.stderr.write("Get the most populated state.\n")
        X0       = array((Counts+Counts.transpose()).sum(0)).flatten()
        X0       = X0/sum(X0)
        MaxState = argmax(X0)


        ## Calculate only times up to at maximum half the
        ## length of an individual trajectory
        max_time = self.avgtime/2.
        #max_time = ((self.dt * self.nstep / 1000)*0.5)
        ## SP this is almost certainly wrong:
        #if max_time > 1:
        #    max_time=int(max_time)
        #else:
        #    max_time=2
        ###max_time = 300 # hard-coded for villin

        self.max_time = max_time
        
        # More trimming
        # PK want ErgodicTrim instead of EnforceMetastability
        # This is from BuildMSM script
        sys.stderr.write("More trimming...\n")
        CountsAfterTrimming,Mapping=msmbuilder.MSMLib.ErgodicTrim(Counts)
        msmbuilder.MSMLib.ApplyMappingToAssignments(Assignments,Mapping)
        ReversibleCounts = msmbuilder.MSMLib.IterativeDetailedBalance(
                                                CountsAfterTrimming,
                                                Prior=0)
        TC = msmbuilder.MSMLib.EstimateTransitionMatrix(ReversibleCounts)
        Populations=numpy.array(ReversibleCounts.sum(0)).flatten()
        Populations/=Populations.sum()

        self.assignments=Assignments
        self.T=TC

        NumStates=max(Assignments.flatten())+1
        sys.stderr.write("New number of states=%d\n"%NumStates)
        if os.path.exists(AssFTrimmed):
            os.remove(AssFTrimmed)
        msmbuilder.Serializer.SaveData(AssFTrimmed,Assignments)
        
        sys.stderr.write("Calculating implied time scales..\n")
        # Calculate the implied time-scales
        time = numpy.arange(1,max_time+1,1)
        TS = msmbuilder.MSMLib.GetImpliedTimescales(AssFTrimmed,NumStates,time,
                                                    NumImpliedTimes=len(time)+1)
        sys.stderr.write("TS=%s, time=%s\n"%(str(TS), time))
        try:
            plt.scatter(TS[:,0],TS[:,1])
            plt.title('Lag times versus implied time scale')
            plt.xlabel('Lag Time (assignment-steps)')
            plt.ylabel('Implied Timescale (ps)')
            plt.yscale('log')
            timescalefn=os.path.join(self.inp.getOutputDir(), 'msm_timescales.png')
            sys.stderr.write('Writing timescale plot to %s'%timescalefn)
            try:
                plt.savefig(timescalefn)
            except:
                fo=StringIO()
                traceback.print_exception(sys.exc_info()[0], 
                                          sys.exc_info()[1],
                                          sys.exc_info()[2], file=fo)
                errmsg="Run error generating timescale plot: %s\n"%(fo.
                                                                    getvalue())
                sys.stderr.write(errmsg)
            plt.close()
            self.out.setOut('timescales', FileValue(timescalefn))
        except ValueError as e:
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            errmsg="Run error generating timescale plot: %s\n"%(fo.getvalue())
            sys.stderr.write(errmsg)

        
        # Get random confs from each state
        sys.stderr.write("Getting random configuration from each state..\n")
        RandomConfs = Proj.GetRandomConfsFromEachState(Assignments,NumStates,1,
                                                       JustGetIndices=True)
        
        # Compute the MaxState with the new assignments (ie. after trimming)
        sys.stderr.write("Computing MaxState.\n")
        Counts=msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                               NumStates,
                                                               LagTime=1,
                                                               Slide=True)
        X0=array((Counts+Counts.transpose()).sum(0)).flatten()
        X0=X0/sum(X0)
        MaxState=argmax(X0)

        # Create a tpr-file for trjconv with -pbc mol
        #sys.stderr.write("making randomconfs.\n")
        #try:
        #    os.mkdir('RandomConfs')
        #except:
        #    pass
        # we need a tpr file to be able to trjconv random confs later
        #proc = subprocess.Popen(["grompp","-f","%s"%self.mdpfile,
        #                          "-c","%s"%self.grofile[0],
        #                          "-p", "%s"%self.topfile,"-o",
        #                          "%s"%os.path.join(self.inp.getOutputDir(),
        #                                            'topol.tpr')],
        #                      stdin=None,stdout=sys.stdout, stderr=sys.stdout)
        #proc.communicate(None)

        # we pick one of the tpr files.
        self.tprfile=self.inp.getInput('trajectories[0].tpr')
        

        # Set a flag to indicate if we have written the maxstate.pdb-file
        have_maxstate=0
        
        for i in xrange(NumStates):
            traj_num    = RandomConfs[i][0][0]
            frame_nr    = RandomConfs[i][0][1]
            lh5name     = Proj.GetTrajFilename(traj_num)            
            #sys.stderr.write("trajectory name=%s\n"%lh5name)
            trajdata    = self.trajData[lh5name]
            trajname    = trajdata.xtc
            #trajname    = trajname.replace('.nopbc.lh5','.xtc')
            time        = frame_nr * trajdata.dt #* self.nstxtcout

            #if(i<10*self.num_to_start):
                #proc = subprocess.Popen(["trjconv","-f","%s"%trajname,"-s","%s"%os.path.join(self.inp.getOutputDir(),'topol.tpr'),"-o",os.path.join(self.inp.getOutputDir(),'micro%d.gro'%i),"-pbc","mol","-dump","%d"%time], stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
                
                #proc.communicate("0")

            # Write out a pdb of the most populated state
            if(i==MaxState and have_maxstate==0):
                maxstatefn=os.path.join(self.inp.getOutputDir(), 'maxstate.pdb')
                sys.stderr.write("writing out pdb of most populated state.\n")
                args = self.cmdnames.trjconv.split()
                args += ["-f", trajname, "-s", self.tprfile,
                         "-o", maxstatefn, "-pbc", "mol", "-dump", "%d" % time]
                if self.ndx is not None:
                    args.extend( [ "-n", self.ndx ] )
                proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
                                        stdout=sys.stdout, stderr=sys.stderr)
                proc.communicate(self.grpname)
                self.out.setOut('maxstate', FileValue(maxstatefn))
                have_maxstate=1

        # now evenly sample configurations and put them in the array
        # newRuns. If we're later assigning macrosates, we'll overwrite them
        # with adaptive sampling configurations
        self.newRuns=[]
        for j in xrange(self.num_to_start*self.num_macro):
            # pick a cluster at random:
            i=random.random()*int(NumStates)
            traj_num    = RandomConfs[i][0][0]
            frame_nr    = RandomConfs[i][0][1]
            lh5name     = Proj.GetTrajFilename(traj_num)            
            trajdata    = self.trajData[lh5name]
            trajname    = trajdata.xtc
            time        = frame_nr * trajdata.dt 
            #maxstatefn=os.path.join(self.inp.getOutputDir(), '.conf')
            outfn=os.path.join(self.inp.getOutputDir(), 'new_run_%d.gro'%(j))
            args = self.cmdnames.trjconv.split()
            args += ["-f", "%s"%trajname, "-s", self.tprfile, 
                     "-o", outfn, "-pbc", "mol", "-dump", "%d" % time]
            sys.stderr.write("writing out new run %s .\n"%outfn)
            proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
                                    stdout=sys.stdout, 
                                    stderr=sys.stderr)
            proc.communicate('0')
            self.newRuns.append(outfn)


        #os.remove('mdout.mdp')

        # Make a plot of the rmsd vs rel. population (rmsd)
#        NumConfsPerState=1
#        RandomConfs = Proj.GetRandomConfsFromEachState(Assignments,NumStates,NumConfsPerState,JustGetIndices=False)
#        Allatoms=RandomConfs["Atoms"]

#        CA=intersect1d(AtomRange,where(Allatoms=="CA")[0])
#        rmsd=RandomConfs.CalcRMSD(C1,CA,CA).reshape((NumStates,NumConfsPerState)).mean(1)
 
 #       NumEigen=NumStates/100
 #       EigAns=msmbuilder.MSMLib.GetEigenvectors(T,NumEigen);
 #       Populations=EigAns[1][:,0]

 #       plt.plot(rmsd,-log(Populations),'o')
 #       plt.title("Free Energy Versus RMSD [nm]")
 #       plt.ylabel("Free Energy")
 #       plt.xlabel("RMSD [nm]")
 #       plt.savefig(os.path.join('cpc-data','msm_fe.png'))
 #       plt.close()


    def createMacroStates(self):
        ''' Build a macro-state MSM '''
        # Again we redirect output
        #stdoutfn=os.path.join(self.inp.getOutputDir(), 'msm_stdout_macro.txt')
        #stderrfn=os.path.join(self.inp.getOutputDir(), 'msm_stderr_macro.txt')
        
        #old_stdout = sys.stdout
        #sys.stdout=open(stdoutfn,'w')
        #old_stderr = sys.stderr
        #sys.stderr=open(stderrfn,'w')  
        
        Map         = msmbuilder.MSMLib.PCCA(self.T,self.num_macro)
        Assignments = self.assignments
        Assignments = Map[Assignments]
        NumStates = max(Assignments.flatten())+1

        sys.stderr.write("Calculating macrostates with lag time %g.\n"%
                         self.lag_time)

        # Now repeat any calculations with the new assignments
        Counts = msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                        self.num_macro,
                                                        LagTime=self.lag_time,
                                                        Slide=True)
        
        #PK want reversible MLE estimator again here
        sys.stderr.write("Recalculating assignments & trimming again.\n")
        CountsAfterTrimming,Mapping=msmbuilder.MSMLib.ErgodicTrim(Counts)
        msmbuilder.MSMLib.ApplyMappingToAssignments(Assignments,Mapping)
        ReversibleCounts = msmbuilder.MSMLib.IterativeDetailedBalance(
                                                         CountsAfterTrimming,
                                                         Prior=0)
        TC = msmbuilder.MSMLib.EstimateTransitionMatrix(ReversibleCounts)
        Populations=numpy.array(ReversibleCounts.sum(0)).flatten()
        Populations/=Populations.sum()

        # Again, get the most populated state
        X0       = array((Counts+Counts.transpose()).sum(0)).flatten()
        X0       = X0/sum(X0)
        MaxState = argmax(X0)

        tcoutf=os.path.join(self.inp.getOutputDir(), "tc.dat")
        if scipy.sparse.issparse(TC):
            scipy.savetxt(tcoutf, TC.todense())
        else:
            numpy.savetxt(tcoutf, TC, fmt="%12.6g" )
        self.out.setOut('macro_transition_counts', FileValue(tcoutf))

        woutf=os.path.join(self.inp.getOutputDir(), "weights.dat")
        numpy.savetxt(woutf, X0, fmt="%12.6g" )
        self.out.setOut('macro_weights', FileValue(woutf))

       
        # Do adaptive sampling on the macrostates
        nstates=int(self.num_macro*self.num_to_start)
        sys.stderr.write("Adaptive sampling to %d=%d*%d states.\n"%
                         (nstates, self.num_macro, self.num_to_start))
        Proj = self.Proj

        StartStates = Proj.AdaptiveSampling(Counts.toarray(),nstates)

        #print StartStates

        #PK note JustGetIndices gives indices into original conformations
        RandomConfs = Proj.GetRandomConfsFromEachState(Assignments,NumStates,1,
                                                       JustGetIndices=True)
       
        self.newRuns=[]
        self.macroConfs=[]
        for k,v in StartStates.items():
            num_started = 0
            for i in xrange(NumStates):
                if i==k:
                    trajnum  = RandomConfs[i][0][0]
                    frame_nr = RandomConfs[i][0][1]
                    lh5name  = Proj.GetTrajFilename(trajnum)            
                    trajdata    = self.trajData[lh5name]
                    trajname    = trajdata.xtc
                    time        = frame_nr * trajdata.dt #* self.nstxtcout
                    #time     = frame_nr * self.dt *self.nstxtcout
                    #trajname = Proj.GetTrajFilename(trajnum)
                    #trajname = trajname.replace('.nopbc.lh5','.xtc')

                    first=True
                    # Use trjconv to write new starting confs
                    while(num_started < self.num_to_start):
                        sys.stderr.write("Writing new start confs.\n")
                        outfn=os.path.join(self.inp.getOutputDir(),
                                           'macro%d-%d.gro'%(i,num_started))
                        args = self.cmdnames.trjconv.split()
                        args += ["-f", "%s" % trajname, "-s", self.tprfile,
                              "-o", outfn, 
                              "-pbc", "mol", "-dump", "%d" % time]
                        proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
                                                stdout=sys.stdout, 
                                                stderr=sys.stderr)
                        proc.communicate('0')
                        num_started = num_started + 1
                        self.newRuns.append(outfn)
                        if first:
                            self.macroConfs.append(outfn)
                            first=False

        # now set the macro state outputs:
        i=0
        for fname in self.macroConfs:
            self.out.setOut('macro_conf[%d]'%i, cpc.dataflow.FileValue(fname))
            i+=1
                    
        
