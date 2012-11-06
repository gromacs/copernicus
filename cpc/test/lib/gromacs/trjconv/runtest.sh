#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs/trjconv/traj.xtc ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "Usage:"
    echo "runtest projectname"
    exit 1
fi
projectname=$1

# start the project
./cpcc start $projectname
# import the gromacs module with grompp and mdrun functions
./cpcc import gromacs
# add the grompp and mdrun function instances
./cpcc instance gromacs::trjconv trjconv
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file trjconv:in.tpr cpc/test/lib/gromacs/trjconv/topol.tpr
./cpcc set-file trjconv:in.traj cpc/test/lib/gromacs/trjconv/traj.xtc
./cpcc set trjconv:in.center 'RNA'
./cpcc set trjconv:in.pbc 'mol'
./cpcc set trjconv:in.ur 'compact'
#./cpcc set trjconv:in.fit_type 'rot+trans'


# and commit this set of updates
./cpcc commit


#./cpcc get tune:out.resources
