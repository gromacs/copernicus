#!/usr/bin/python
# Grant Rotskoff, 18 July 2012
# inputs: 
#	index.ndx
#	conf.gro
# outputs:
#	list of residues
#

import sys
import re
import os

# accepts a .gro file and a .ndx file with exactly one group
def res_select(conf,index):
    conf = open(conf,'r').readlines()
    ndx = ''.join(open(index,'r').readlines()[1:]).split()

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

    # read the conf file into atom types
    # TODO restrict to index numbers
    j=2
    protein = []
    while j < len(conf)-1:
            if "SOL" not in conf[j]:
                    protein.append(atom(conf[j]))
            j+=1

    # convert the ndx file to a list of residues
    res_selection = []
    for a in ndx:
            res_selection+=[protein[int(a)-1].resnr]
    res_selection = list(set(res_selection)) # remove redundant copies of the resnr
    print res_selection
