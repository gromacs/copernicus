#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs/tune/conf.gro ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import gromacs
# add the grompp and mdrun function instances
./cpcc instance gromacs::mdrun_tune tune
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file tune:in.conf cpc/test/lib/gromacs/tune/conf.gro
./cpcc set-file tune:in.mdp cpc/test/lib/gromacs/tune/grompp.mdp
./cpcc set-file tune:in.top cpc/test/lib/gromacs/tune/topol.top
./cpcc set-file tune:in.include[0] cpc/test/lib/gromacs/tune/topol_Other_chain_A2.itp 


# and commit this set of updates
./cpcc commit


./cpcc get tune:out.resources
