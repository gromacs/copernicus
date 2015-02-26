#!/usr/bin/python
# Grant Rotskoff, 18 July 2012
# TODO edit for a topology type file
# inputs: 
#	index.ndx
#	conf.gro
# outputs:
#	list of residues
#

import sys
import re
import os

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


# read a .gro file into atom types
def protein(conf): 
    conf=open(conf,'r').readlines()
    j=2 # skip the header of the .gro file
    prot = []
    while j < len(conf)-1:
            if "SOL" not in conf[j]:
                    prot.append(atom(conf[j]))
            j+=1
    return prot

# index file MUST have exactly one group
def res_select(conf,index):
    prot=protein(conf)
    ndx = ''.join(open(index,'r').readlines()[1:]).split()
    
    res_selection = []
    for a in ndx:
            res_selection+=[prot[int(a)-1].resnr]
    res_selection = list(set(res_selection)) # remove redundant copies of the resnr
    return res_selection


