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
args = vars(parser.parse_args())

#conf = open(args['i'],'r').readlines()
#ndx = "".join(open(args['x'],'r').readlines()[1:]).split()
#top = open(args['p'],'r').read()
conf = args['i']
ndx = args['x']
# should be an xvgarray... 
# n = len(xvg_array)
n = int(args['n'])

selection = res_selection.res_select(conf,ndx)
protein = res_selection.protein(conf)

for k in range(1,n):
    newtop=open('%s.itp'%k,'w')
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
				newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(phi[i].atomnr,
                    phi[i+1].atomnr, phi[i+2].atomnr, phi[i+3].atomnr, 1,
                    1, phi_val, 0, 1, 2))
                newtop.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(psi[i].atomnr,
                    psi[i+1].atomnr, psi[i+2].atomnr, psi[i+3].atomnr, 1, 
                    1, psi_val, 0, 1, 2))
                i+=4 
