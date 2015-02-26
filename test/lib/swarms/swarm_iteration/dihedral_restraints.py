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

parser = argparse.ArgumentParser()
parser.add_argument('-i',required=True, help='The initial .gro file')
parser.add_argument('-n',required=True, help='The number of interpolation steps')
parser.add_argument('-x',required=True, help='The desired index file (.ndx)')
parser.add_argument('-p',required=True, help='A topology file for the restraints, must contain the line "#include dihedral_restraints" where the restraints are to be written')
args = vars(parser.parse_args())

conf=args['i']
ndx=args['x']
n=int(args['n'])
top = open(args['p'],'r').read()
selection = res_selection.res_select(conf,ndx)
protein = res_selection.protein(conf)

top=top.split('#include dihedral_restraints')
print selection

theta_val=[1.6, 1.48, 1.36, 1.24, 1.12, 1.0, 0.8799999999999999, 0.7599999999999999, 0.6399999999999999, 0.5199999999999998, 0.3999999999999999, 0.2799999999999998, 0.1599999999999997, 0.039999999999999813, -0.0800000000000003, -0.20000000000000018, -0.3200000000000003, -0.4400000000000004, -0.5600000000000005, -0.8]
zeta_val=[-4.3, -3.8, -3.3, -2.8, -2.3, -1.7999999999999998, -1.2999999999999998, -0.7999999999999998, -0.2999999999999998, 0.20000000000000018, 0.7000000000000002, 1.2000000000000002, 1.7000000000000002, 2.2, 2.7, 3.2, 3.7, 4.2, 4.7, 5.7]


for k in range(1,n):
    newtop=open('%s.top'%k,'w')
    # write the initial part of the topology file
    newtop.write('%s'%top[0])
    xvg = open('%s.xvg'%k,'r').readlines()
    #print "Writing restraints for interpolant number %i" %k
    newtop.write("[ dihedral_restraints ]\n")
    newtop.write("; ai   aj   ak   al  type  label  phi  dphi  kfac  power\n")
    for r in selection:
        i = 0 # there may be multiple residues matching the resnr, e.g., dimers
        phi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C')) or
                      (a.resnr == int(r)-1 and a.atomname == 'C')]

        psi = [a for a in protein if (a.resnr == int(r) and
                      (a.atomname == 'N' or a.atomname == 'CA' or a.atomname == 'C')) or
                      (a.resnr == int(r)+1 and a.atomname == 'N')]


        # get phi and psi values from the g_rama output
        for line in xvg:
            if re.search(r'\-%s\n'%r,line):
                phi_val = float(line.split()[0])
                psi_val = float(line.split()[1])

                # write phi, psi angles
                #newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(phi[i].atomnr,
                #    phi[i+1].atomnr, phi[i+2].atomnr, phi[i+3].atomnr, 1,
                #    1, phi_val, 0, 1, 2))
                #newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(psi[i].atomnr,
                #    psi[i+1].atomnr, psi[i+2].atomnr, psi[i+3].atomnr, 1, 
                #    1, psi_val, 0, 1, 2))
                newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(5,7,9,15,1,1,phi_val,0,1,2))
                newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(7,9,15,17,1,1,psi_val,0,1,2))
                newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(1,5,7,9,1,1,theta_val[k],0,1,2))
                newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(9,15,17,19,1,1,zeta_val[k],0,1,2))
                i+=4
    newtop.write('%s'%top[1])
