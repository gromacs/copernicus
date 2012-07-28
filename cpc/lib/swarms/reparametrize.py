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


def reparametrize(diheds, selection, start_conf, start_xvg, end_conf, end_xvg, top): 
    Nswarms = len(diheds[0])
    #newtop = open(newtop,'w')
    rsel = res_selection.res_select('%s'%start_conf,'%s'%selection)
    #sys.stderr.write('%s'%rsel)
    # helper functions for list operations
    def add(x,y): return x+y
    def scale(k,v):
            scaled=[]
            for vi in v:
                    scaled+=[k*vi]
            return scaled
    def mapadd(x,y): return map(add,x,y)
    # for each interpolant:
    # calculate average drift in collective variables space
    newpts = []
    for interp in range(len(diheds)):
            avg = []
            for r in rsel:
                    driftList = []
                    for i in range(len(diheds[interp])):
                            vec=[]
                            xvg = open(diheds[interp][i],'r')
                            for line in xvg:
                                    if re.search(r'\-%s\n'%r,line):
                                            phi_val = float(line.split()[0])
                                            psi_val = float(line.split()[1])
                                            vec+=[phi_val,psi_val]
                            driftList.append(vec)
                    # driftList has phi,psi values for residue in every swarm
                    avg+=[scale((1/float(Nswarms)),reduce(mapadd,driftList))]
            newpts+=avg
    # reparametrize the points
    # see Maragliano et al, J. Chem Phys (125), 2006
    # we use a linear interpolation in Euclidean space
    # adjusted to ensure equidistance points
    # each item in newpts is a point an r*2 dimensional point in colvars space,
    # where r is the number of residues in the selection
    def sub(x,y): return y-x
    def dist(v1,v2):
            return sum([x**2 for x in map(sub,v1,v2)])**(.5)
    # path length upto the nth interpolant
    def L(n):
            if n==0: return 1
            else:
                    pathlength = 0
                    i=0
                    while i < n:
                            pathlength+=dist(newpts[i],newpts[i+1])
                            i+=1
                    return pathlength
    def s(m):
            n=len(newpts)-1
            return (m-1)*L(n)/(n-1)
    def dir(v1,v2):
            normed = []
            d = dist(v1,v2)
            for x in map(sub,v1,v2):
                    normed+=[x/d]
            return normed

    # extract initial and target dihedral values
    initpt = []
    for r in rsel:
            xvg = open(start_xvg,'r')
            for line in xvg:
                    if re.search(r'\-%s\n'%r,line):
                            phi_val = float(line.split()[0])
                            psi_val = float(line.split()[1])
                            initpt+=[phi_val,psi_val]

    targetpt = []
    for r in rsel:
            xvg = open(end_xvg,'r')
            for line in xvg:
                    if re.search(r'\-%s\n'%r,line):
                            phi_val = float(line.split()[0])
                            psi_val = float(line.split()[1])
                            targetpt+=[phi_val,psi_val]

    newpts.insert(0,initpt)
    newpts.append(targetpt)
    adjusted = [initpt,targetpt]
    sys.stderr.write('The new list of points is: %s' %newpts)
    for i in range(1,len(newpts)-1): # as defined s(1) = 0
            k = 1
            #while k<len(newpts)-1:
            #     while (L(k-1)>=s(i) or s(i)>L(k)):
            #        k+=1
            tail=adjusted[i:] 
            adjusted[:i].append(map(add,adjusted[k-1],scale((s(i)-L(k-1)),dir(adjusted[k],adjusted[k-1]))))
            adjusted=adjusted+tail
            k+=1
            

    # write the topology for the next iteration
    # treat the reparam values as a stack
    for k in range(1,len(diheds)+1):
            itp=open('%d.itp'%k,'w')
            sys.stderr.write("Writing restraints for interpolant number %i\n" %k)
            #newtop.write("\n#ifdef %i_restraints\n"% k)
            itp.write("[ dihedral_restraints ]\n")
            itp.write("; ai   aj   ak   al  type  label  phi  dphi  kfac  power\n")
            stack=adjusted[k]
            protein = res_selection.protein('%s'%start_conf)
            for r in rsel:
                    # there may be multiple residues matching the resnr, e.g., dimers
                    phi = [a for a in protein if (a.resnr == int(r) and
                          (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C')) or
                          (a.resnr == int(r)-1 and a.atomname == 'C')]

                    psi = [a for a in protein if (a.resnr == int(r) and
                          (a.atomname == 'N' or a.atomname == 'CA' or a.atomname == 'C')) or
                          (a.resnr == int(r)+1 and a.atomname == 'N')]

                    # get phi and psi values from the reparametrization vector
                    numres = len(phi)/4
                    for i in range(numres):
                            phi_val=stack[i]
                            psi_val=stack[i+1]
                            # write phi, psi angles
                            itp.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(phi[i*4].atomnr,phi[i*4+1].atomnr,
                                              phi[i*4+2].atomnr,phi[i*4+3].atomnr,1,1,phi_val,0,1,2))
                            itp.write("%5d%5d%5d%5d%5d%5d%8.4f%5d%5d%5d\n"%(psi[i*4].atomnr,psi[i*4+1].atomnr,
                                              psi[i*4+2].atomnr,psi[i*4+3].atomnr,1,1,psi_val,0,1,2))

                    # delete the already added values from the stack
                    stack = stack[numres*2-1:]

            itp.write("#endif\n")


#Nswarms=200
#n=2 # for testing

#selection = res_selection.res_select('init.gro','index.ndx')
#top = open('topol.top','r').read()
#newtop = open('newtop.itp','w')
#newtop.write(top)


