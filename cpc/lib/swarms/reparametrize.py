#!/usr/bin/python
# Grant Rotskoff, 12 July 2012
# Bjorn Wesen, June 2014
#
# inputs: 
#	swarm structure CVs (dihedral angles .xvg or atom positions .gro)
#	topology file (.itp)
#	index.ndx
#	n - number of interpolants 
# outputs:
#	topology file for use with next iteration including new restraint coordinates
#

import sys
import re
import os
import res_selection
import readxvg
import rwgro
from molecule import molecule

# helper functions
def add(x, y): return x + y

def scale(k, v):
        scaled = []
        for vi in v:
                scaled += [k * vi]
        return scaled

def mapadd(x, y): return map(add, x, y)

def sub(x, y): return y - x

def dist(v1, v2):
        return sum([x**2 for x in map(sub, v1, v2)])**(.5)

# path length upto the nth interpolant
# 1-based indexing following Maragliano
def L(n, path):
        if n==0: 
                return 1
        else:
                pathlength = 0
                for i in range(n - 1):
                        pathlength += dist(path[i], path[i + 1])
                return pathlength

def s(m, path):
        R = len(path) - 1
        return (m - 1) * L(R, path) / (R - 1)

def dir(v1, v2):
        normed = []
        d = dist(v1, v2)
        for x in map(sub, v1, v2):
                normed += [x / d]
        return normed

# reparametrize the points
# see Maragliano et al, J. Chem Phys (125), 2006
# we use a linear interpolation in Euclidean space
# adjusted to ensure equidistance points
# each item in newpts is a K-length list corresponding to a point in the K-dimensional CV-space
# (for example, K = 2*num_selected_residues for phi/psi dihedrals)
def rep_pts(newpts):
    adjusted = [ newpts[0], newpts[ len(newpts) - 1 ] ]
    for i in range(2, len(newpts)): 
            k = 2
            while (L(k - 1, newpts) >= s(i, newpts) or s(i, newpts) > L(k, newpts)):
               k += 1
            v = dir(newpts[k - 2], newpts[k - 1])
            reppt = (map(add, newpts[k - 2], scale((s(i, newpts) - L(k - 1, newpts)), v)))
            adjusted.insert(i - 1, reppt)
            #sys.stderr.write('The swarm point %d is: %s'%(i,newpts[i-1]))
            #print('The swarm point %d is: %s'%(i,newpts[i-1]))
            #sys.stderr.write('The reparametrized point %d is: %s\n'%(i,reppt))
            #print('The reparametrized point %d is: %s\n'%(i,reppt))
    #i=0 
    #for i in range(len(newpts)-1):
    #    print dist(adjusted[i],adjusted[i+1])
    return adjusted

# start/end_xvg will be None for the posres case
# last_resconfs[] will be None for dihedrals. It also begins at index 0, corresponding to the path point 1.

def reparametrize(use_posres, cvs, ndx_file, Nchains, start_conf, start_xvg, end_conf, end_xvg, last_resconfs, top, includes): 

    Nswarms = len(cvs[0])

    ndx_atoms = res_selection.read_ndx(ndx_file)

    # For dihedrals, we map the atoms to residues for a single chain, and the readxvg etc. will read the entire file and
    # select the same residues in each chain. But for the position restraints which use the atom indices directly, we have
    # to first expand the index so it covers all chains.

    # TODO: have to figure out or input atoms per chain in the .gro's so we can repeat the atom-selection Nchains times
    # for the posres case. The ndx file is for atoms inside the chain, but the .gro will contain global numbering.
    # We can detect the chain-repeat in rwgro, by looking for repeating first residue name.
    # Hardcode a repeat for testing for now.

    if use_posres == 0:
            # Map atoms to residues for the dihedral selection
            rsel = res_selection.res_select('%s' % start_conf, ndx_atoms)
            #sys.stderr.write('Residue selection: %s' %rsel)

#    else:
#            selected_atoms = []
#            for ch in range(5):
#                    for i in range(len(ndx_atoms)):
#                            selected_atoms += [ ndx_atoms[i] + ch * 5566 ]

    # Calculate the average drift in CV space

    # newpts is a per-swarm-point list of CV points (each a list of the CV dimension length)
    newpts = []

    for pathpt in range(len(cvs)):
            swarmpts = []
            for i in range(len(cvs[pathpt])):
                    if use_posres == 1:
                            zpt = rwgro.readgro_flat(cvs[pathpt][i], ndx_atoms)
                            #sys.stderr.write('Read pathpt %d swarm %d (%s), got %d CVs\n' % (pathpt, i, cvs[pathpt][i], len(zpt)))
                    else:
                            zpt = readxvg.readxvg_flat(cvs[pathpt][i], rsel)
                    swarmpts.append(zpt)
            zptsum = reduce(mapadd, swarmpts)
            avgdrift = scale((1 / float(Nswarms)), zptsum)
            newpts.append(avgdrift)

    # Read in the fixed start and end CV values
    if use_posres == 1:
            # TODO: the start/end_conf are full Systems so the atom numbering aliases for the ndx_atoms array :/
            # Currently fixed in readgro_flat temporary, hardcoded for the GLIC Protein number. 
            initpt = rwgro.readgro_flat(start_conf, ndx_atoms)
            targetpt = rwgro.readgro_flat(end_conf, ndx_atoms)
    else:
            initpt = readxvg.readxvg_flat(start_xvg, rsel)
            targetpt = readxvg.readxvg_flat(end_xvg, rsel)

    sys.stderr.write('Length of initpt %d, targetpt %d\n' % (len(initpt), len(targetpt)))

    # something with 1 indexing makes this padding necessary.
    paddingpt = [0] * len(initpt)
    newpts.insert(0, initpt)
    newpts.append(targetpt)
    newpts.append(paddingpt)

    # Do the actual reparameterization

    # Initial iteration
    adjusted = rep_pts(newpts)

    # Keep iterating 100 times, feeding the result of the previous result into rep_pts again
    # TODO implement a dist_treshold=1.0
    # Changed to 35 now, with long CV vectors (> 4000 dimensions) 100 iterations takes forever
    # (at least 45 min for 25 iterations).
    iters = [adjusted]
    for i in range(35):
            sys.stderr.write('Rep iter %d\n' % i)
            sys.stderr.flush()
            iters.append(rep_pts(iters[i]))

    # Get the final iteration's result
    adjusted = iters[-1]
 
    # delete the padding point
    adjusted = adjusted[:-1]
    #sys.stderr.write('The adjusted pts:\n %s'%adjusted)
    # calculate reparam distance

    sys.stderr.write('Length of the adjusted vector: %d\n' % len(adjusted))
    # TODO Nchains should depend on the specific residue (?)
    # Given as function argument now.
    #Nchains = len(initpt) / (2 * len(rsel))

    # TODO measure distance
    # write the CV control data for the next iteration

    # The output file expected for the posres case is rep_resconf_%d.gro for each stringpoint.
    # For dihedrals its res_%d_chain_%d.itp for each stringpoint and chain.

    for k in range(1, len(adjusted) - 1):
            if use_posres == 1:
                    # Open the output resconf which will go into the next iteration as minimization target
                    with open('rep_resconf_%d.gro' % k, 'w') as rep_resconf:
                            # Open and read the previous (input) resconf, which has basically tagged along since the last
                            # reparametrization step (or was set initially at swarm-start)
                            with open(last_resconfs[k - 1], 'r') as in_resconf_f:
                                    in_resconf = in_resconf_f.readlines()
                            # TODO: maybe this chunk of code could be done by the rwgro module for us.
                            # Copy the first 2 rows (title and number of atoms) straight over
                            rep_resconf.write(in_resconf[0])
                            rep_resconf.write(in_resconf[1])
                            # Go through the atoms row-by-row and update the xyz coordinates for the atoms the reparametrize
                            # step moved
                            # Note: we are only copying over positions here. The velocities are not needed as the use for these files
                            # will only be as a base for the next iterations position restraint coordinates.
                            pathpoint = adjusted[k] # the 1-D list of CVs (positions): x,y,z * nbr atoms in index
                            if len(pathpoint) != (1555 * 3):  # assert
                                    sys.stderr.write('adjusted[] entry of wrong length %d\n' % len(pathpoint))
                            cvpos = 0
                            for line in in_resconf[2:][:-1]:
                                    resname = line[0:8]  # python-ranges are inclusive the first index and exclusive the second...
                                    atname = line[8:15]
                                    atomnr = int(line[15:20])
                                    x = float(line[20:28])
                                    y = float(line[28:36])
                                    z = float(line[36:44])
                                    if atomnr in ndx_atoms:
                                            # Update to new coords
                                            x = pathpoint[cvpos]
                                            y = pathpoint[cvpos + 1]
                                            z = pathpoint[cvpos + 2]
                                            cvpos += 3
                                    # Write out the row, updated or not
                                    rep_resconf.write('%s%s%5d%8.3f%8.3f%8.3f\n' % (resname, atname, atomnr, x, y, z))
                            # Copy the last row which was the cell dimensions
                            rep_resconf.write(in_resconf[len(in_resconf) - 1]) 
            else:
                    for chain in range(Nchains):
                            with open('res_%d_chain_%d.itp' % (k, chain), 'w') as restraint_itp:
                                    with open(includes[k - 1][chain], 'r') as in_itpf:
                                            in_itp = in_itpf.read()
                                            moltop = in_itp.split('[ dihedral_restraints ]')[0]
                                            restraint_itp.write('%s' % moltop)

                                    sys.stderr.write("Writing restraints for interpolant point %d chain %d\n" % (k, chain))
                                    # Note: this format is for Gromacs 4.6+. Before, there was a "label" and no B-morph possibility (optional)
                                    restraint_itp.write("[ dihedral_restraints ]\n")
                                    restraint_itp.write("; ai   aj   ak   al  type     phi    dphi    kfac   phiB    dphiB    kfacB\n")
                                    pathpoint = adjusted[k] # just a list of phi/psi angles

                                    if Nchains == 1:
                                            protein = molecule(top)
                                    else:
                                            protein = molecule('%s' % includes[k - 1][chain])

                                    # Create a lookup-table for the protein topology that maps residue to dihedrally relevant
                                    # backbone atom indices for N, CA and C.

                                    dih_atoms = {}

                                    for a in protein:
                                            if (a.atomname == 'CA' or a.atomname == 'N' or a.atomname == 'C'):
                                                    try:
                                                            dih_atoms[a.resnr][a.atomname] = a.atomnr;
                                                    except KeyError:
                                                            dih_atoms[a.resnr] = { a.atomname: a.atomnr }
                                                            
                                    # Use the lookup-table built above and get the dihedral specification atoms needed for each
                                    # residue in the selection. This is O(n) in residues, thanks to the dih_atoms table.

                                    pos = 0

                                    for r in rsel:
                                            # Get the atom numbers to use for the phi and psi dihedrals (4 atoms each)
                    
                                            # phi is C on the previous residue, and N, CA, C on this
                                            phi = [ dih_atoms[r - 1]['C'], dih_atoms[r]['N'], dih_atoms[r]['CA'], dih_atoms[r]['C'] ]
                                    
                                            # psi is N, CA and C on this residue and N on the next
                                            psi = [ dih_atoms[r]['N'], dih_atoms[r]['CA'], dih_atoms[r]['C'], dih_atoms[r + 1]['N'] ]
                                    
                                            # get phi and psi values from the reparametrization vector
                                            phi_val = pathpoint[pos + chain]
                                            psi_val = pathpoint[pos + chain + 1]

                                            # Go to the next residue (phi,phi vals * number of chains apart)
                                            pos += 2 * Nchains
                    
                                            # write phi, psi angles and k-factor
                                            # Note: in the Gromacs 4.6+ format, the k-factor is here. Before, it was in the .mdp as
                                            # dihre_fc.
                                            
                                            # Since we need different force constants in different stages, we need to put
                                            # a searchable placeholder in the file here and replace it later
                                            restraint_itp.write("%5d%5d%5d%5d%5d %8.4f%5d  KFAC\n"
                                                                % (phi[0], phi[1], phi[2], phi[3], 1, phi_val, 0))
                                            restraint_itp.write("%5d%5d%5d%5d%5d %8.4f%5d  KFAC\n"
                                                                % (psi[0], psi[1], psi[2], psi[3], 1, psi_val, 0))

