#!/usr/bin/python
# Grant Rotskoff, 6 September 2012
# TODO edit for a topology type file
# outputs:
#	list of residues
#

import sys
import re
import os

class atom:
    # read an atom from a line
    def __init__(self, line):
        line=line.split()
        self.resnr=int(line[2])
        self.resname=line[3].strip()
        self.atomname=line[4].strip()
        self.atomnr=int(line[0])
        self.group=[]


# read a .top file into a structure description
def molecule(top): 
    top=open(top,'r').read()
    # isolate the [ atoms ] section
    top=top.split('[ atoms ]')
    top=top[1].split('[ bonds ]')[0]
    top=top.split('\n')
    prot = []
    for line in top:
            if len(line)>0 and ";"!=line[0]:
                prot.append(atom(line))
    return prot

