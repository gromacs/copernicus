#!/usr/bin/python
# Grant Rotskoff, 12 July 2012
# inputs: 
#	swarm structure dihedral angles (.xvg)
#	topology file (.itp)
#	index.ndx
#	n - number of interpolants 
# outputs:
#	topology file for use with next iteration
#
# dihedrals are swarm_n.xvg

import sys
import re
import os
import res_selection
from molecule import molecule

# helper functions
def add(x,y): return x+y

def scale(k,v):
        scaled=[]
        for vi in v:
                scaled+=[k*vi]
        return scaled

def mapadd(x,y): return map(add,x,y)

def sub(x,y): return y-x

def dist(v1,v2):
        return sum([x**2 for x in map(sub,v1,v2)])**(.5)

# path length upto the nth interpolant
# 1-based indexing following Maragliano
def L(n,path):
        if n==0: return 1
        else:
                pathlength = 0
                for i in range(n-1):
                        pathlength+=dist(path[i],path[i+1])
                return pathlength

def s(m,path):
        R=len(path)-1
        return (m-1)*L(R,path)/(R-1)

def dir(v1,v2):
        normed = []
        d = dist(v1,v2)
        for x in map(sub,v1,v2):
                normed+=[x/d]
        return normed

# reparametrize the points
# see Maragliano et al, J. Chem Phys (125), 2006
# we use a linear interpolation in Euclidean space
# adjusted to ensure equidistance points
# each item in newpts is a point an r*2 dimensional point in colvars space,
# where r is the number of residues in the selection
def rep_pts(newpts):
    adjusted=[newpts[0],newpts[len(newpts)-1]]
    for i in range(2,len(newpts)): 
            k=2
            while (L(k-1,newpts)>=s(i,newpts) or s(i,newpts)>L(k,newpts)):
               k+=1
            v=dir(newpts[k-2],newpts[k-1])
            reppt=(map(add,newpts[k-2],scale((s(i,newpts)-L(k-1,newpts)),v)))
            adjusted.insert(i-1,reppt)
            #sys.stderr.write('The swarm point %d is: %s'%(i,newpts[i-1]))
            #print('The swarm point %d is: %s'%(i,newpts[i-1]))
            #sys.stderr.write('The reparametrized point %d is: %s\n'%(i,reppt))
            #print('The reparametrized point %d is: %s\n'%(i,reppt))
    #i=0 
    #for i in range(len(newpts)-1):
    #    print dist(adjusted[i],adjusted[i+1])
    return adjusted

def reparametrize(diheds, selection, start_conf, start_xvg, end_conf, end_xvg, top, includes): 
    Nswarms = len(diheds[0])
    rsel = res_selection.res_select('%s'%start_conf,'%s'%selection)
    
    # calculate average drift in collective variables space
    #sys.stderr.write('Residue selection: %s' %rsel)
    newpts=[]
    for pathpt in range(len(diheds)):
        swarmpts=[]
        for i in range(len(diheds[pathpt])):
            zpt=[]
            for r in rsel:
                xvg=open(diheds[pathpt][i],'r')
                for line in xvg:
                     if re.search(r'\-%d\n'%r,line):
                         phi_val = float(line.split()[0])
                         psi_val = float(line.split()[1])
                         zpt+=[phi_val,psi_val]
            swarmpts.append(zpt)
        zptsum=reduce(mapadd,swarmpts)
        avgdrift=scale((1/float(Nswarms)),zptsum)
        newpts.append(avgdrift)

    # extract initial and target dihedral values
    initpt = []
    for r in rsel:
            xvg = open(start_xvg,'r')
            for line in xvg:
                    if re.search(r'\-%d\n'%r,line):
                            phi_val = float(line.split()[0])
                            psi_val = float(line.split()[1])
                            initpt+=[phi_val,psi_val]

    targetpt = []
    for r in rsel:
            xvg = open(end_xvg,'r')
            for line in xvg:
                    if re.search(r'\-%d\n'%r,line):
                            phi_val = float(line.split()[0])
                            psi_val = float(line.split()[1])
                            targetpt+=[phi_val,psi_val]
    # something with 1 indexing makes this padding necessary.
    paddingpt=[0]*len(initpt)
    newpts.insert(0,initpt)
    newpts.append(targetpt)
    newpts.append(paddingpt)
    adjusted=rep_pts(newpts)
    # TODO implement a dist_treshold=1.0
    iters=[adjusted]
    for i in range(100):
        iters.append(rep_pts(iters[i]))

    adjusted=iters[-1]
    # delete the padding point
    adjusted=adjusted[:-1]
    #sys.stderr.write('The adjusted pts:\n %s'%adjusted)
    # calculate reparam distance

    sys.stderr.write('Length of the adjusted vector: %d'%len(adjusted))
    # TODO Nchains should depend on the specific residue
    Nchains=len(initpt)/(2*len(rsel))
    # TODO measure distant
    # write the topology for the next iteration
    for k in range(1,len(adjusted)-1):
        for chain in range(Nchains):
            restraint_itp=open('dihre_%d_chain_%d.itp'%(k,chain),'w')

            in_itp=open(includes[k-1][chain], 'r').read()
            moltop=in_itp.split('[ dihedral_restraints ]')[0]
            restraint_itp.write('%s'%moltop)
            sys.stderr.write("Writing restraints for interpolant point %d chain %d\n"%(k,chain))
            restraint_itp.write("[ dihedral_restraints ]\n")
            restraint_itp.write("; ai   aj   ak   al  type  label  phi  dphi  kfac  power\n")
            pathpoint=adjusted[k] # just a list of phi/psi angles
            if Nchains==1:
                protein=molecule(top)
            else:
                protein=molecule('%s'%includes[k-1][chain])
            # keep track of the position in the path point
            pos=0
            for r in rsel:
                    # there may be multiple residues matching the resnr, e.g., dimers
                    phi = [a.atomnr for a in protein if (a.resnr == int(r) and
                          (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C')) or
                          (a.resnr == int(r)-1 and a.atomname == 'C')]

                    psi = [a.atomnr for a in protein if (a.resnr == int(r) and
                          (a.atomname == 'N' or a.atomname == 'CA' or a.atomname == 'C')) or
                          (a.resnr == int(r)+1 and a.atomname == 'N')]

                    # get phi and psi values from the reparametrization vector
                    phi_val=pathpoint[pos+chain]
                    psi_val=pathpoint[pos+chain+1]
                    
                    
                    # write phi, psi angles
                    restraint_itp.write("%5d%5d%5d%5d%5d%5d %8.4f%5d%5d%5d\n"
                                        %(phi[0],phi[1],phi[2],phi[3],1,1,phi_val,0,1,2))
                    restraint_itp.write("%5d%5d%5d%5d%5d%5d %8.4f%5d%5d%5d\n"
                                        %(psi[0],psi[1],psi[2],psi[3],1,1,psi_val,0,1,2))


                    # delete the already added values from the stack
                    pos+=2*Nchains
            restraint_itp.close()

