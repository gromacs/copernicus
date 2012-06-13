#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs_bar/lambda00.edr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import fe
# add the grompp and mdrun function instances
./cpcc instance fe::fe_init fe_init
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc set-file fe_init:in.grompp.top cpc/test/lib/fe_init/topol.top
./cpcc set-file fe_init:in.grompp.include[0]  cpc/test/lib/fe_init/ana.itp
./cpcc set-file fe_init:in.grompp.include[0]  cpc/test/lib/fe_init/ana.itp
./cpcc set-file fe_init:in.grompp.mdp cpc/test/lib/fe_init/grompp.mdp

./cpcc set-file fe_init:in.conf cpc/test/lib/fe_init/conf.gro

./cpcc set fe_init:in.n_lambdas 10
./cpcc set fe_init:in.solvation_relaxation_time 2000
./cpcc set fe_init:in.coupled_mol ethanol




# and commit this set of updates
./cpcc commit


