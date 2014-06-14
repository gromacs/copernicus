#!/usr/bin/python
# Write the initial topology file for restrained simulations in swarm free energy calculations
# Grant Rotskoff, 11 July 2012
# Rewritten by Bjorn Wesen 2014

# This function can do two things - either get a start and end config and associated xvg's, and then interpolate 
# n states between them and write out to .itp files, or get a whole array of configs, extract dihedrals from them
# without interpolation and write to the same .itp files.

# Note: the start/end xvg's can be created from the conf's by g_rama -s topol.tpr -f a.gro -o a.xvg, but we don't
# do it for that mode here in the script, for the case where the user might want to modify the dihedrals for the
# start and end without updating the actual configs (I'm not sure this use-case is relevant at all, if it isn't, we can
# simply remove the start/end_xvg inputs)

import sys
import re
import random
import os
from subprocess import Popen
import argparse
import res_selection
from molecule import molecule
#import cpc.dataflow
#from cpc.dataflow import FileValue

# If initial_confs is None or zero length, use start/end etc to interpolate, otherwise use the structures in intial_confs
#
# Note: if initial_confs are given, they should include the start and end configs as well (the complete string)

def write_restraints(inp, initial_confs, start, end, start_xvg, end_xvg, tpr, top, includes, n, ndx, Nchains):
    
    selection = res_selection.res_select(start,ndx)
    n = int(n)  # number of points in the string, including start and end point

    use_interpolation = False

    if initial_confs is None or len(initial_confs) == 0:
        use_interpolation = True
        # Read the starting and ending dihedrals for later interpolation
        # Read the entire file into a list so we can scan it multiple times
        startxvg = open(start_xvg,'r').readlines()
        endxvg = open(end_xvg,'r').readlines()
        startpts = {}
        endpts = {}
        for r in selection:
            # There will be an array for each residue dihedral, over the chains (they are looping in the xvg)
            startpts[r] = [] # list of phi/psi pairs for each chain
            for line in startxvg:
                # Match the "ASP-178" etc. residue names at the ends of the lines, for the residue index r.
                # Have to have the \S there (non-whitespace at least 1 char) otherwise we match stuff like
                # the headers with -180.
                if re.search(r'\S+\-%s$'%r, line):
                    startpts[r].append([float(line.split()[0]), float(line.split()[1])])
        for r in selection:
            endpts[r] = []
            for line in endxvg:
                if re.search(r'\S+\-%s$'%r, line):
                    endpts[r].append([float(line.split()[0]), float(line.split()[1])])
    else:
        # Have to generate the dihedrals ourselves
        # TODO: assert that len(initial_confs) == n otherwise?
        # Use g_rama on each intermediate conf (not start/end) and output to a temporary .xvg
        stringpts = {}  # Will have 4 levels: stringpoint, residue, chain, phi/psi value
        for i in range(1,n-1):
            # Start array indexed by residue
            stringpts[i] = {}
            ramaproc = Popen(['g_rama', '-f', initial_confs[i], '-s', tpr, '-o', '0%3d.xvg' % i])  # TODO: g_rama_mpi.. like everywhere else
            xvg_i = os.path.join(inp.getOutputDir(), '0%3d.xvg' % i)
            # Which we will read back in and parse like above
            ramaproc.wait()
            xvg_f = open(xvg_i, 'r')
            # Read the entire file into a list so we can scan it multiple times
            xvg = xvg_f.readlines()
            for r in selection:
                # Support many chains so the last level will be a list of phi,psi lists
                stringpts[i][r] = []
                for line in xvg:
                    if re.search(r'\S+\-%d\n' % r, line):
                        stringpts[i][r].append([float(line.split()[0]), float(line.split()[1])])

            xvg_f.close()

    # Rewrite the topology to include the dihre.itp files instead of the original per-chain itps (if any)
    # There will be one topol_x.top per intermediate string point

    sys.stderr.write('%s' % includes)
    for k in range(1,n-1):
        in_top=open(top).read()       
        for mol in range(Nchains):
            if len(includes)>0:
                includename=includes[mol].split('/')[-1]
                in_top=re.sub(includename,'dihre_%d_chain_%d.itp'%(k,mol),in_top)
        out_top=open('topol_%d.top'%k,'w')
       # sys.stderr.write('%s'%in_top)
        out_top.write(in_top)   
            
    # Generate/copy and write-out the dihedrals for each intermediate point (not for the start/end points)
    for k in range(1,n-1):
        for mol in range(Nchains):
            restraint_itp=open('dihre_%d_chain_%d.itp'%(k,mol),'w')
            if Nchains>1:
                moltop=open(includes[mol]).read()
                restraint_itp.write(moltop)
            # write the initial part of the topology file
            # NOTE: the dihedral_restraints format changed in gromacs 4.6+ or so to this. before it had
            # some other parameters as well. 
            restraint_itp.write("[ dihedral_restraints ]\n")
            restraint_itp.write("; ai   aj   ak   al  type phi  dphi  kfac\n")
            if len(includes)>0:
                protein=molecule(includes[mol])
                # replace the chain names with the chain names
            else:
                out_top=open('topol_%d.top'%k,'w')
                protein=molecule(top)
                in_itp=open(top,'r').read().split('; Include Position restraint file')
                out_top.write(in_itp[0])
                out_top.write('#include "dihre_%d_chain_%d.itp"\n'%(k,mol))
                #out_top.write('#include "dihre_%d_chain_%d.itp"\n'%(k,mol))
                out_top.write(in_itp[1])
                out_top.close()

            for r in selection:
                # Get the atom numbers to use for the phi and psi dihedrals (4 atoms each)
                phi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C')) or
                      (a.resnr == int(r)-1 and a.atomname == 'C')]

                psi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'N' or a.atomname == 'CA' or a.atomname == 'C')) or
                      (a.resnr == int(r)+1 and a.atomname == 'N')]

                # Write phi, psi angles and the associated k factor into a row in the restraint file
                # Note: in the Gromacs 4.6+ format, the k-factor is here. Before, it was in the .mdp as
                # dihre_fc.
                # Also see reparametrize.py

                kfac = 1000.0

                if use_interpolation:
                    phi_val = startpts[r][mol][0] + (endpts[r][mol][0] - startpts[r][mol][0]) / n * k
                    psi_val = startpts[r][mol][1] + (endpts[r][mol][1] - startpts[r][mol][1]) / n * k
                else:
                    phi_val = stringpts[k][r][mol][0]
                    psi_val = stringpts[k][r][mol][1]

                restraint_itp.write("%5d%5d%5d%5d%5d %8.4f%5d  %8.4f\n"
                                    %(phi[0].atomnr,phi[1].atomnr,phi[2].atomnr, phi[3].atomnr, 1, phi_val, 0, kfac))
                restraint_itp.write("%5d%5d%5d%5d%5d %8.4f%5d  %8.4f\n"
                                    %(psi[0].atomnr,psi[1].atomnr,psi[2].atomnr, psi[3].atomnr, 1, psi_val, 0, kfac))

            restraint_itp.close()


