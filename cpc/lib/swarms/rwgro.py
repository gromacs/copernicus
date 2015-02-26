## Bjorn Wesen 2014

# Read the specified gro-file and return the coordinates of the selected atoms as a 1D list of x,y,z for each atom
# atoms_ndx is a list of the atom numbers to use

def readgro_flat(grofn, atoms_ndx):
    d = []
    with open(grofn, 'r') as gro_f:
        # We can't use a whitespace split of the lines as the gro fields are column specified so
        # there might be touching fields
        # skip the first two lines, name and number of atoms, and skip the last line, the cell-size
        conf = gro_f.readlines()[2:][:-1]
        # Ugly hack (TODO)
        apos = 0
        for line in conf:
            atomnr = int(line[15:20])
            x = float(line[20:28])
            y = float(line[28:36])
            z = float(line[36:44])
            # For the selected atoms, just append their coordinates to the 1D list
            if (atomnr in atoms_ndx) and apos < 27830:
                d += [ x, y, z ]
            apos += 1

    return d

