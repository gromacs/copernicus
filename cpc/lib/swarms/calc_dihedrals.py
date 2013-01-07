#!/usr/bin/env python
# Grant Rotskoff, 7 January 2013
#

import sys
import re
import os
from math import sqrt,asin,pi

# parse a .gro file
# 3 dimensional vector
class v3d:
  def __init__(self,array):
    self.x=float(array[0])
    self.y=float(array[1])
    self.z=float(array[2])
  def __add__(v,w):
    return v3d([v.x+w.x,v.y+w.y,v.z+w.z])
  def __sub__(v,w):
    return v3d([v.x-w.x,v.y-w.y,v.z-w.z])
  def __mul__(v,w):
    return v3d([v.y*w.z-v.z*w.y,v.x*w.z-v.z*w.x,v.x*w.y-v.y*w.x])
  def __str__(v):
    return "<%5.3f,%5.3f,%5.3f>"%(v.x,v.y,v.z)
def dot(v,w):
  return v.x*w.x+v.y*w.y+v.z*w.z
def norm(v):
  return sqrt(dot(v,v))

class atom:
    # read an atom from a line
    def __init__(self, line):
        self.atomnr=int(line[15:20])
        self.coord=v3d([line[20:28],line[28:36],line[36:44]])

def calc_dihre(a1,a2,a3,a4):
  n1=(a1-a2)*(a3-a2)
  n2=(a4-a3)*(a2-a3)
  rad=asin(norm(n1*n2)/(norm(n1)*norm(n2)))
  #if rad>pi:
  #  return rad*180/pi-360
  #else: 
  return rad*180/pi

def dihedrals(conf,ndx): 
    # parse the necessary files
    conf=open(conf,'r').readlines()[2:][:-1]
    ndx=open(ndx,'r').readlines()[1].split()
    if len(ndx)%4 != 0:
      sys.stderr.write('The index contains a number of atoms which is not divisible by 4, thus does not define a set of dihedral angles!')
    for i in range(len(ndx)):
      ndx[i]=int(ndx[i])
    p={}
    for line in conf:
      if len(line)>0 and ";"!=line[0]:
        a=atom(line)
        p[a.atomnr]=a.coord
    # call the dihedral function
    dihres=[]
    while len(ndx)!=0:
      dihres.append(calc_dihre(p[ndx[0]],p[ndx[1]],p[ndx[2]],p[ndx[3]]))
      ndx=ndx[4:]
    return dihres
