## Bjorn Wesen 2014

def readxvg(xvg, rsel):
    d = {}
    with open(xvg, 'r') as xvg_f:
        # Each line has a phi and psi val and a residue number, and after looping over all
        # residues the loops can repeat if there are many chains in the protein. The array
        # we build is indexed on residue, and then there are Nchains sub-indices with a 
        # phi,psi pair each.
        for line in xvg_f:
            if line[0] != '@' and line[0] != '#':   # skip comment rows in the xvg
                parts = line.split()
                phipsi = [ float(parts[0]), float(parts[1]) ]  # phi psi
                residue = int(parts[2].split('-')[1])   # ARG-8 => 8
                if residue in rsel:
                    try:
                        d[residue].append(phipsi)  # => add one more ch
                    except KeyError:
                        d[residue] = [ phipsi ]    # => d[r][ch] = [ phi, psi ]
    #print d
    return d


# Same function but output all values into a 1-dimensional array, on residue, chain, phi/psi

def readxvg_flat(xvg, rsel):
    d = []
    with open(xvg, 'r') as xvg_f:
        for line in xvg_f:
            if line[0] != '@' and line[0] != '#':   # skip comment rows in the xvg
                parts = line.split()
                phipsi = [ float(parts[0]), float(parts[1]) ]  # phi psi
                residue = int(parts[2].split('-')[1])   # ARG-8 => 8
                if residue in rsel:
                    d += phipsi
    #print d
    return d


# Read the dihedral restraint section from an .itp file and return the angles in a flat array
# Note: usually the itp file only contains a single chain's worth of angles, so the returned
# array here won't match the chain-interleaved format of the readxvg_flat above.

def read_dihres_flat(dihfn):

    d = []

    with open(dihfn, 'r') as dih_f:

        # The [ dihedral_restraints ] delimiter marks the start of the dihedrals section
        dihsect = False

        for line in dih_f:
            if line[0] == '[' and line[2] == 'd' and line[3] == 'i' and line[4] == 'h':
                dihsect = True

            if dihsect and line[0] != ';':
                # Get the dihedral value
                #    23   25   27   34    1 -76.5315    0  KFAC
                v = float(line.split()[5])
                d += [ v ]

    return d


# Read the dihedral restraint sections from .itp files (one per chain) and return the angles in
# a format similar to the readxvg above
# dihfn_base is "../res_15_chain_" or similar, and will be extended with 0.xvg, 1.xvg etc

def read_dihres(dihfn_base, rsel, Nchains):

    d = {}

    # Prepare for chain level appends
    for r in rsel:
        d[r] = []

    for ch in range(0, Nchains):

        dihfn = '%s%d.itp' % (dihfn_base, ch)

        with open(dihfn, 'r') as dih_f:

            # The [ dihedral_restraints ] delimiter marks the start of the dihedrals section
            dihsect = False
            ridx = 0
            p = 0   # toggles 0 for phi and 1 for psi
            for line in dih_f:
                if dihsect and line[0] != ';':
                    # Get the dihedral value
                    #    23   25   27   34    1 -76.5315    0  KFAC
                    #print "Line is %s" % line
                    v = float(line.split()[5])
                    # We assume the ordering and content is the same as in rsel
                    if p == 0:
                        d[rsel[ridx]].append([v])  # start new chain with the phi val as only member
                        p = 1
                    else:
                        d[rsel[ridx]][ch] += [v]   # add the psi val to the phi
                        p = 0                        
                        ridx += 1   # ready for the next residue

                if not dihsect and line.startswith('[ dihedral_restraints ]'):
                    dihsect = True

    return d


