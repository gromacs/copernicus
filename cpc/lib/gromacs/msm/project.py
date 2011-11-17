import os
import sys
import subprocess
import re
import logging

from scipy.stats import halfnorm
import scipy 
import scipy.sparse
from random import random
from numpy import where
from numpy import array,argmax
import numpy
#import random

import matplotlib
#Use a non GUI backend for matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

#import copernicus.project.gromacs
#from copernicus.task.gromacs import GromacsTask
#from project_parse import ProjectSettingsParser

# Make sure msmbuilder is in the PYTHONPATH
from msmbuilder.CopernicusProject import *
import msmbuilder.MSMLib
import msmbuilder.Serializer
import msmbuilder.Trajectory
#import DataFile

# cpc stuff
import cpc.dataflow
from cpc.dataflow import FileValue

log = logging.getLogger('cpc.msm.project')



#def convertXtc2lh5(xtcfile,  ref_conf, outFilename, persDir):
#    ''' Convert the xtc-files to a .lh5 file '''
#    
#    #OutFilename='traj.nopbc.lh5'
#    PDBFilename=str(ref_conf)
#
#    mstdout=open(os.path.join(persDir, "tohl5.out"),"w")
#    mstdout.write("Writing to %s, %s"%(xtcfile, PDBFilename))
#    log.debug("%s, %s %s %s"%(xtcfile, PDBFilename, os.path.exists(xtcfile),
#                              os.path.exists(PDBFilename)))
#    Traj = msmbuilder.Trajectory.Trajectory.LoadFromXTC([xtcfile],
#                                                       PDBFilename=PDBFilename)
#    Traj.Save("%s"%outFilename)
#    mstdout.close()
#
#def removeSolAndPBC(inFile, outFile, tprFile, grpname, ndxFile, persDir):
#    ''' Removes PBC on trajectories '''
#   
#    msm1=os.path.join(persDir, 'remove_sol.txt')
#    msm2=os.path.join(persDir, 'remove_sol_err.txt')
#    mstdout=open(msm1,'w') 
#    mstderr=open(msm2,'w')
#    args=["trjconv","-f","%s"%inFile,"-s", tprFile,"-o","%s"%outFile,"-pbc",
#            "mol"]
#    if ndxFile is not None:
#        args.extend( [ '-n', ndxFile ] )
#    proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
#                            stdout=mstdout, stderr=mstderr)
#    proc.communicate(grpname)
#    ret = []
#    mstdout.close() 
#    mstdout.close() 
#    
    

class MSMProject(object):
    ''' MSM specific project data '''

    # the name of the top-level element for this project data type
    elementName = ""

    def __init__(self, inp, fnOutput):
        ''' Initialize MSMProject '''
        #ProjectSettingsParser.__init__(self)
        #self.inputs=inputs  # dict with the MSM function inputs         
        self.inp=inp
        #self.subnetInputs=subnetInputs# dict with the MSM function's subnet inp
        self.fnOutput=fnOutput # the output of this call of the MSM function

        ''' Initialize with data '''
        #self.InitStart     = inputs['init_start']
        #self.ClusterAtoms = inp.getInput('cluster_atoms')        
        log.debug("num_states=%s"%inp.getInput('num_states'))
        print("num_states=%s"%inp.getInput('num_states'))
        self.num_states    = int(inp.getInput('num_states'))
        self.dt            = float(inp.getInput('time_step'))
        self.nstep         = int(inp.getInput('nstep'))
        self.nstxtcout     = int(inp.getInput('nstxtcout'))
        self.recluster     = float(inp.getInput('recluster'))
        self.ref_conf      = os.path.join(inp.getBaseDir(),
                                          inp.getInput('reference'))
        self.grpname       = inp.getInput('grpname')
        self.num_sim       = int(inp.getInput('num_sim'))

        # we make absolute paths because msmbuilder may need that.
        self.mdpfile = os.path.join(inp.getBaseDir(),inp.getInput('mdp'))
        self.topfile = os.path.join(inp.getBaseDir(),inp.getInput('top'))
        if  inp.getInput('ndx') is not None:
            self.ndx = os.path.join(inp.getBaseDir(),inp.getInput('ndx'))
        else:
            self.ndx = None
        self.grofile=[]
        self.gronames=[]

        for i in range(10):
            nm='conf_%d'%i
            if inp.getInput(nm) is not None: 
                self.gronames.append(os.path.join(inp.getBaseDir(),
                                                  inp.getInput(nm)))
                self.grofile.append(os.path.join(inp.getBaseDir(),
                                                 inp.getInput(nm)))
            
        if (len(self.grofile) > 1):
            self.multi_gro = 1
        else:
            self.multi_gro = 0

        # The msm-builder project
        self.Proj = None

        # The assignments from msm-builder
        self.assignments = None

        # The transition count matrix from msm-builder
        self.T = None

        # The desired lag time
        self.max_time = None

        # Sims to start per round
        self.num_to_start = 10

        # Number of macrostates. Hardcoded in the XML too because there are
        # no arrays yet.
        self.num_macro = 10



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

                

    def listRandomConfs(self):
        ''' Makes a list of all gro-files in the RandomConfs dir '''
        grolist = []
        files = os.listdir(self.inp.outputDir)
        for f in files:
            if f.endswith('.gro'):
                grolist.append(f)
        return grolist
        
    def getNewSimTime(self):
        ''' Compute a new simulation time from a half-normal distribution '''
     
        # Extend to 400 ns (hardcoded for villin)
        new_length = 400000
        
        r = random()

        if(r>0.9):
            nst = int(new_length/self.dt)
        else:
            nst = 25000000
    
        return nst


    def createMicroStates(self,filelist):
        ''' Build a micro-state MSM '''
        # we assume we're in a persistent, writable directory 
        # Need to redirect output from original stdout 
        stdoutfn=os.path.join(self.inp.outputDir, 'msm_stdout.txt')
        stderrfn=os.path.join(self.inp.outputDir, 'msm_stderr.txt')
        
        old_stdout = sys.stdout  
        sys.stdout=open(stdoutfn,'w') 
        old_stderr = sys.stderr  
        sys.stderr=open(stderrfn,'w')

        log.debug("Creating msms project, ref_conf=%s.", str(self.ref_conf))
        log.debug("filelist size=%d.", len(filelist))
        print("Creating msms project, ref_conf=%s.", str(self.ref_conf))
        print("filelist size=%d.", len(filelist))
        # Create the msm project from the reference conformation        
        Proj = CreateCopernicusProject(self.ref_conf, filelist)
        self.Proj = Proj
        C1   = Conformation.Conformation.LoadFromPDB(self.ref_conf)
        
        # Automate the clustering to only CA or backbone atoms
        a = C1["AtomNames"]
        AtomIndices=where((a=="N") | (a=="C") | (a=="CA") | (a=="O"))[0]
        
        log.debug("Cluster project.")
        print("Cluster project.")
        # Do msm-stuff
        GenF = os.path.join('Data','Gens.nopbc.h5')
        AssF = os.path.join('Data','Ass.nopbc.h5')
        AssFTrimmed = os.path.join('Data','Assignment-trimmed.nopbc.h5')
        RmsF = os.path.join('Data','RMSD.nopbc.h5')
        
        Generators = Proj.ClusterProject(AtomIndices=AtomIndices,
                                         NumGen=self.num_states,Stride=30)
        log.debug("Assign project.")
        print("Assign project.")
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
        
        log.debug("Trim data.")
        print("Trim data.")
        # Trim data
        Counts = msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                            self.num_states,
                                                            LagTime=1,
                                                            Slide=True)
                
        # Get the most populated state
        log.debug("Get the most populated state.")
        print("Get the most populated state.")
        X0       = array((Counts+Counts.transpose()).sum(0)).flatten()
        X0       = X0/sum(X0)
        MaxState = argmax(X0)

        # Calculate only times up to at maximum half the
        # length of an individual trajectory
        max_time = ((self.dt * self.nstep / 1000)*0.5)
        # SP this is almost certainly wrong:
        if max_time > 1:
            max_time=int(max_time)
        else:
            max_time=2
        #max_time = 300 # hard-coded for villin
        self.max_time = max_time
        
        # More trimming
        #Tools.IterativeTrim(Assignments,max_time,Symmetrize=True,Start=MaxState)
        # msmbuilder.MSMLib.EnforceMetastability(Assignments,max_time) 
        # PK want ErgodicTrim instead of EnforceMetastability
        # This is from BuildMSM script
        log.debug("More trimming...")
        print("More trimming...")
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
        log.debug("New number of states=%d"%NumStates)
        print("New number of states=%d"%NumStates)
        if os.path.exists(AssFTrimmed):
            os.remove(AssFTrimmed)
        msmbuilder.Serializer.SaveData(AssFTrimmed,Assignments)
        
        log.debug("Calculating implied time scales..")
        print("Calculating implied time scales..")
        # Calculate the implied time-scales
        time = numpy.arange(1,max_time,20)
        TS = msmbuilder.MSMLib.GetImpliedTimescales(AssFTrimmed,NumStates,time,
                                                    NumImpliedTimes=len(time))
        log.debug("TS=%s"%str(TS))
        print("TS=%s"%str(TS))
        plt.scatter(TS[:,0],TS[:,1])
        plt.title('Lag times versus implied time scale')
        plt.xlabel('Lag Time (assignment-steps)')
        plt.ylabel('Implied Timescale (ps)')
        plt.yscale('log')
        timescalefn=os.path.join(self.inp.outputDir, 'msm_timescales.png')
        plt.savefig(timescalefn)
        plt.close()
        self.fnOutput.setOut('timescales', FileValue(timescalefn))

        
        # Get random confs from each state
        log.debug("Getting random configuration from each state..")
        print("Getting random configuration from each state..")
        RandomConfs = Proj.GetRandomConfsFromEachState(Assignments,NumStates,1,JustGetIndices=True)
        
        # Compute the MaxState with the new assignments (ie. after trimming)
        log.debug("Computing MaxState.")
        print("Computing MaxState.")
        Counts=msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                               NumStates,
                                                               LagTime=1,
                                                               Slide=True)
        X0=array((Counts+Counts.transpose()).sum(0)).flatten()
        X0=X0/sum(X0)
        MaxState=argmax(X0)

        # Create a tpr-file for trjconv with -pbc mol
        log.debug("making randomconfs.")
        #try:
        #    os.mkdir('RandomConfs')
        #except:
        #    pass
        # we need a tpr file to be able to trjconv random confs later
        proc = subprocess.Popen(["grompp","-f","%s"%self.mdpfile,
                                  "-c","%s"%self.grofile[0],
                                  "-p", "%s"%self.topfile,"-o",
                                  "%s"%os.path.join(self.inp.outputDir,
                                                    'topol.tpr')],
                                stdin=None,stdout=sys.stdout, stderr=sys.stdout)
        
        proc.communicate(None)

        # Set a flag to indicate if we have written the maxstate.pdb-file
        have_maxstate=0
        
        for i in range(NumStates):
            traj_num    = RandomConfs[i][0][0]
            frame_nr    = RandomConfs[i][0][1]
            time        = frame_nr * self.dt * self.nstxtcout
            trajname    = Proj.GetTrajFilename(traj_num)            
            trajname    = trajname.replace('.nopbc.lh5','.xtc')

            if(i<10*self.num_to_start):
                pass
                #proc = subprocess.Popen(["trjconv","-f","%s"%trajname,"-s","%s"%os.path.join(self.inp.outputDir,'topol.tpr'),"-o",os.path.join(self.inp.outputDir,'micro%d.gro'%i),"-pbc","mol","-dump","%d"%time], stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
                
                #proc.communicate("0")

            # Write out a pdb of the most populated state
            if(i==MaxState and have_maxstate==0):
                maxstatefn=os.path.join(self.inp.outputDir, 'maxstate.pdb')
                log.debug("writing out pdb of most populated state.")
                args=["trjconv","-f","%s"%trajname,
                      "-s","%s"%os.path.join(self.inp.outputDir,'topol.tpr'),
                      "-o",maxstatefn,"-pbc","mol","-dump","%d"%time]
                if self.ndx is not None:
                    args.extend( [ "-n", self.ndx ] )
                proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
                                        stdout=sys.stdout, stderr=sys.stderr)
                proc.communicate(self.grpname)
                self.fnOutput.setOut('maxstate', FileValue(maxstatefn))
                have_maxstate=1
            
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

 #       sys.exit()
        # Set back stdout/stderr to old values
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr 
        self.fnOutput.setOut('msm_stdout', FileValue(stdoutfn))
        self.fnOutput.setOut('msm_stderr', FileValue(stderrfn))


    def createMacroStates(self):
        ''' Build a macro-state MSM '''
        # Again we redirect output
        stdoutfn=os.path.join(self.inp.outputDir, 'msm_stdout_macro.txt')
        stderrfn=os.path.join(self.inp.outputDir, 'msm_stderr_macro.txt')
        
        old_stdout = sys.stdout
        sys.stdout=open(stdoutfn,'w')
        old_stderr = sys.stderr
        sys.stderr=open(stderrfn,'w')  
        
        Map         = msmbuilder.MSMLib.PCCA(self.T,self.num_macro)
        Assignments = self.assignments
        Assignments = Map[Assignments]
        NumStates = max(Assignments.flatten())+1

        log.debug("Calculating macrostates.")
        print("Calculating macrostates.")

        # Now repeat any calculations with the new assignments
        Counts = msmbuilder.MSMLib.GetCountMatrixFromAssignments(Assignments,
                                                        self.num_macro,
                                                        LagTime=self.max_time,
                                                        Slide=True)
        
        #PK want reversible MLE estimator again here
        log.debug("Recalculating assignments & trimming again.")
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

        tcoutf=os.path.join(self.inp.outputDir, "tc.dat")
        if scipy.sparse.issparse(TC):
            scipy.savetxt(tcoutf, TC.todense())
        else:
            numpy.savetxt(tcoutf, TC, fmt="%12.6g" )
        self.fnOutput.setOut('transition_counts', FileValue(tcoutf))

        woutf=os.path.join(self.inp.outputDir, "weights.dat")
        numpy.savetxt(woutf, X0, fmt="%12.6g" )
        self.fnOutput.setOut('weights', FileValue(woutf))

       
        # Do adaptive sampling on the macrostates
        log.debug("Adaptive sampling.")
        print("Adaptive sampling.")
        Proj = self.Proj
        StartStates = Proj.AdaptiveSampling(Counts.toarray(),
                                            self.num_macro*self.num_to_start)

        #print StartStates

        #PK note JustGetIndices gives indices into original conformations
        RandomConfs = Proj.GetRandomConfsFromEachState(Assignments,NumStates,1,
                                                       JustGetIndices=True)
       
        startConfs=[]
        for k,v in StartStates.items():
            num_started = 0
            for i in range(NumStates):
                if i==k:
                    trajnum  = RandomConfs[i][0][0]
                    frame_nr = RandomConfs[i][0][1]
                    time     = frame_nr * self.dt *self.nstxtcout
                    trajname = Proj.GetTrajFilename(trajnum)
                    trajname = trajname.replace('.nopbc.lh5','.xtc')

                    first=True
                    # Use trjconv to write new starting confs
                    while(num_started < self.num_to_start):
                    
                        log.debug("Writing new start confs.")
                        print("Writing new start confs.")
                        outfn=os.path.join(self.inp.outputDir,
                                           'macro%d-%d.gro'%(i,num_started))
                        args=["trjconv","-f","%s"%trajname,
                              "-s","%s"%os.path.join(self.inp.outputDir,
                                                     'topol.tpr'),
                              "-o", os.path.join(self.inp.outputDir,
                                                 'macro%d-%d.gro'%
                                                 (i,num_started)),
                              "-pbc","mol","-dump","%d"%time]
                        #if self.ndx is not None:
                        #    args.extend( [ "-n", self.ndx ] )
                        proc = subprocess.Popen(args, stdin=subprocess.PIPE, 
                                                stdout=sys.stdout, 
                                                stderr=sys.stderr)
                        proc.communicate('0')
                        num_started = num_started + 1
                        startConfs.append(outfn)
                        if first:
                            nm='macrostate_conf_%d'%i
                            self.fnOutput.setOut(nm, FileValue(outfn))
                            first=False

                        
        os.remove(os.path.join(self.inp.outputDir,'topol.tpr'))

        # Set back stdout/stderr to old values
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr 
        
        self.fnOutput.setOut('msm_macro_stdout', FileValue(stdoutfn))
        self.fnOutput.setOut('msm_macro_stderr', FileValue(stderrfn))

        return startConfs


