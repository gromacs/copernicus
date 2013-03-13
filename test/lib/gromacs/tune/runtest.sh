#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/gromacs/tune/conf.gro ]; then
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
./cpcc instance gromacs::mdrun_tune tune
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file tune:in.conf test/lib/gromacs/tune/conf.gro
./cpcc set-file tune:in.mdp test/lib/gromacs/tune/grompp.mdp
./cpcc set-file tune:in.top test/lib/gromacs/tune/topol.top
./cpcc set-file tune:in.include[0] test/lib/gromacs/tune/topol_Other_chain_A2.itp 


# and commit this set of updates
./cpcc commit


./cpcc get tune:out.resources
