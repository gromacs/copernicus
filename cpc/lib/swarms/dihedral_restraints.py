#!/usr/bin/python
# Grant Rotskoff, 11 July 2012
# write the initial topology file for restrained simulations 
# in swarm free energy calculations
# usage: ./dihedral_restraints conf.gro topol.top numsteps index.ndx

import sys
import re
import random
import os
import argparse
import res_selection
from molecule import molecule

def write_restraints(start, end, start_xvg, end_xvg, top, includes, n, ndx, Nchains):
    
    start_xvg=open(start_xvg,'r').readlines()
    end_xvg=open(end_xvg,'r').readlines()
    selection=res_selection.res_select(start,ndx)
    n=int(n)


    # create the path
    startpts={}
    endpts={}
    for r in selection:
        startpts[r]=[]
        chain=0
        for line in start_xvg:
            if re.search(r'\-%s$'%r,line):
                startpts[r].append([float(line.split()[0]),float(line.split()[1])])
                chain+=1
    for r in selection:
        endpts[r]=[]
        chain=0
        for line in end_xvg:
            if re.search(r'\-%s$'%r,line):
                endpts[r].append([float(line.split()[0]),float(line.split()[1])])
                chain+=1
    
    sys.stderr.write('%s'%includes)
    for k in range(1,n-1):
        in_top=open(top).read()       
        for mol in range(Nchains):
            if len(includes)>0:
                includename=includes[mol].split('/')[-1]
                in_top=re.sub(includename,'dihre_%d_chain_%d.itp'%(k,mol),in_top)
        out_top=open('topol_%d.top'%k,'w')
       # sys.stderr.write('%s'%in_top)
        out_top.write(in_top)   
            
    
    for k in range(1,n-1):
        # make the directory for the restraints
        for mol in range(Nchains):
            restraint_itp=open('dihre_%d_chain_%d.itp'%(k,mol),'w')
            if Nchains>1:
                moltop=open(includes[mol]).read()
                restraint_itp.write(moltop)
            # write the initial part of the topology file
            restraint_itp.write("[ dihedral_restraints ]\n")
            restraint_itp.write("; ai   aj   ak   al  type  label  phi  dphi  kfac  power\n")
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
                phi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C')) or
                      (a.resnr == int(r)-1 and a.atomname == 'C')]

                psi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'N' or a.atomname == 'CA' or a.atomname == 'C')) or
                      (a.resnr == int(r)+1 and a.atomname == 'N')]

                # write phi, psi angles
                phi_val=startpts[r][mol][0]+(endpts[r][mol][0]-startpts[r][mol][0])/n*k
                psi_val=startpts[r][mol][1]+(endpts[r][mol][1]-startpts[r][mol][1])/n*k

                restraint_itp.write("%5d%5d%5d%5d%5d%5d %8.4f%5d%5d%5d\n"
                                    %(phi[0].atomnr,phi[1].atomnr,phi[2].atomnr,phi[3].atomnr, 
                                      1, 1, phi_val, 0, 1, 2))
                restraint_itp.write("%5d%5d%5d%5d%5d%5d %8.4f%5d%5d%5d\n"
                                    %(psi[0].atomnr,psi[1].atomnr,psi[2].atomnr,psi[3].atomnr, 
                                      1, 1, psi_val, 0, 1, 2))
            restraint_itp.close()


