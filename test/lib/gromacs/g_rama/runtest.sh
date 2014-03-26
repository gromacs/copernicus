#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs/g_rama/conf.gro ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import gromacs
# add the grompp and mdrun function instances
./cpcc instance gromacs::g_rama g_rama
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file g_rama:in.tpr cpc/test/lib/gromacs/g_rama/topol.tpr
./cpcc set-file g_rama:in.traj cpc/test/lib/gromacs/g_rama/conf.gro


# and commit this set of updates
./cpcc commit


#./cpcc get tune:out.resources
