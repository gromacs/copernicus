#!/usr/bin/python
# Write the initial topology file for position-restrained simulations in swarm free energy calculations
# Bjorn Wesen, July 2014

# Position restraints in Gromacs work by supplying the restrained atoms coordinates to grompp
# by the extra -r option from a .gro file, and also supplying the force constants and atom
# indices for each molecule in an .itp file. 
#
# We have to create both the initial set of .gro files for the starting configurations of the
# string points here, and the .itp template files which will be used by all subsequent passes
# (and will not need to change). Note that this is a bit different from the dihedral restraint
# version where the .itp files change.
#
# This function can do two things - either get a start and end config and then interpolate 
# n states between them and write out to .gro's, or get a whole array of configs
# without interpolation and just copy out the coordinates
#
# NOTE: as we currently have not implemented the interpolation step here anyway, we actually don't
# need to copy and generate the resconf .gro's for this first step at all. We can simply keep the
# path[].resconf unset, and grompp won't use the -r option and it will take the restraint positions
# from the starting conf.

# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Grant Rotskoff, Bjorn Wesen, Erik Lindahl and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import sys
import re
import random
import os
from subprocess import Popen
import argparse
import res_selection

from molecule import molecule
#import cpc.dataflow
#from cpc.dataflow import FileValue

# If initial_confs is None or zero length, use start/end etc to interpolate, otherwise use the structures in intial_confs
#
# Note: if initial_confs are given, they should include the start and end configs as well (the complete string)

def write_restraints(inp, initial_confs, start, end, tpr, top, includes, n, ndxfn, Nchains):
    
    n = int(n)  # number of points in the string, including start and end point

    ndx_atoms = res_selection.read_ndx(ndxfn)

    use_interpolation = False

    if initial_confs is None or len(initial_confs) == 0:
        use_interpolation = True
        # Read the starting and ending atom configurations for later interpolation TODO
        #startpts = readxvg.readxvg(start_xvg, selection)
        #endpts = readxvg.readxvg(end_xvg, selection)

    # Rewrite the topology to include the res itp files instead of the original per-chain itps (if any)
    # There will be one topol_x.top per intermediate string point

    sys.stderr.write('%s' % includes)
    for k in range(n):
        with open(top) as in_topf:
            in_top = in_topf.read()       
            for mol in range(Nchains):
                if len(includes) > 0:
                    includename = includes[mol].split('/')[-1]
                    in_top = re.sub(includename, 'res_%d_chain_%d.itp' % (k, mol), in_top)
            with open('topol_%d.top' % k, 'w') as out_top:
                # sys.stderr.write('%s'%in_top)
                out_top.write(in_top)   

    # Generate/copy and write-out the restraint atom and force spec for each intermediate point
    # This is really unnecessary here since the restraint positions are not in these files so they are the same
    # for all points and chains. TODO
    for k in range(n):
        for mol in range(Nchains):
            with open('res_%d_chain_%d.itp' % (k, mol), 'w') as restraint_itp:
                if Nchains > 1:
                    with open(includes[mol]) as moltop_f:
                        moltop = moltop_f.read()
                        restraint_itp.write(moltop)

                if len(includes) > 0:
                    protein = molecule(includes[mol])
                    # replace the chain names with the chain names
                else:
                    with open('topol_%d.top' % k, 'w') as out_top:
                        protein = molecule(top)
                        with open(top, 'r') as in_itp_f:
                            in_itp = in_itp_f.read().split('; Include Position restraint file')
                            out_top.write(in_itp[0])
                            out_top.write('#include "res_%d_chain_%d.itp"\n' % (k, mol))
                            out_top.write(in_itp[1])

                # Go through the atoms in the selection index and write one row for each one with the KFAC
                # force constant placeholder

                restraint_itp.write("\n[ position_restraints ]\n")
                restraint_itp.write("; atom  type      fx      fy      fz\n")

                for a in ndx_atoms:
                    if a < 5566:  # GLIC HACK: only write one chain, and do it relative atom 1 since the .itp maps to the topology molecule.
                        restraint_itp.write("%6d     1  KFAC  KFAC  KFAC\n" % int(a))

