#!/usr/bin/python
# Grant Rotskoff, 11 July 2012
# Euclidean interpolation between two .gro files
# Usage: interpolate.py -i initial.gro -o final.gro -n numsteps

# The structures must be aligned beforehand! And centered in the pbc box!

#import argparse
#parser = argparse.ArgumentParser()
#parser.add_argument('-i', required=True, help='The initial .gro file.')
#parser.add_argument('-f', required=True, help='The target .gro file.')
#parser.add_argument('-n', required=True, help='The number of interpolants.')
#args = vars(parser.parse_args())

import os
import sys
import re
import random

class atom:
    # read an atom from a line
    def __init__(self, line):
        self.resnr=int(line[0:5])
        self.resname=line[5:10].strip()
        self.atomname=line[10:15].strip()
        self.atomnr=int(line[15:20])
        self.x=float(line[20:28])
        self.y=float(line[28:36])
        self.z=float(line[36:44])
        vxs=line[44:52]
        if vxs.strip() != "":
            self.vx=float(vxs)
            self.vy=float(line[52:60])
            self.vz=float(line[60:68])
            self.vset=True
        else:
            self.vset=False
        self.group=[]


def make_path(start, end, n):
    i = open(start,'r').readlines()
    f = open(end,'r').readlines()

    # open n files for writing out conf files
    # store the file names in a dictionary
    files = {}
    for k in range(n):
        files[k] = open(str(k)+'.gro','w')
        files[k].write(i[0])
        files[k].write(i[1])

    j=2 # start reading after the header
    while j < len(i)-1:
        line = i[j]
        # TODO prevent interpolation of non-protein part in general.
        # TODO allow optional ignore groups, or specific index files
        if "SOL" not in line or "DOPC" not in line: 
            i_atom = atom(line)
            f_atom = atom(f[j])
            dx = f_atom.x - i_atom.x
            dy = f_atom.y - i_atom.y
            dz = f_atom.z - i_atom.z
            for k in range (n):
                newx = i_atom.x + (k+1)*(dx/n)
                newy = i_atom.y + (k+1)*(dy/n)
                newz = i_atom.z + (k+1)*(dz/n)
                if i_atom.vset:
                    files[k].write("%5d%5s%5s%5d%8.3f%8.3f%8.3f%8.4f%8.4f%8.4f\n"%
                                (i_atom.resnr, i_atom.resname, i_atom.atomname, i_atom.atomnr,
                                newx, newy, newz, i_atom.vx, i_atom.vy, i_atom.vz))
                else:
                    files[k].write("%5d%5s%5s%5d%8.3f%8.3f%8.3f\n"%
                                    (i_atom.resnr, i_atom.resname, i_atom.atomname, i_atom.atomnr,
                                    newx, newy, newz))
        else: 
            for k in range(n):
                files[k].write(i[j])
        j+=1

    for k in range(n):
        files[k].write(f[-1]) # append the last line of the target .gro file
        files[k].close()
