#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/fe/init/grompp.mdp ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import fe
# add the grompp and mdrun function instances
./cpcc instance fe::fe_init fe_init
#./cpcc instance fe::fe_iteration fe_iteration
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc set-file fe_init:in.grompp.top cpc/test/lib/fe/init/topol.top
./cpcc set-file fe_init:in.grompp.include[0]  cpc/test/lib/fe/init/ana.itp
./cpcc set-file fe_init:in.grompp.mdp cpc/test/lib/fe/init/grompp.mdp

./cpcc set-file fe_init:in.conf cpc/test/lib/fe/init/conf.gro

./cpcc set fe_init:in.molecule_name ethanol

./cpcc set fe_init:in.n_lambdas 10
./cpcc set fe_init:in.nsteps 2000

./cpcc set fe_init:in.a vdwq
./cpcc set fe_init:in.b vdw

./cpcc connect fe_init:out.path fe_iteration:in.path
./cpcc connect fe_init:out.resources fe_iteration:in.resources
./cpcc connect fe_init:out.grompp fe_iteration:in.grompp


#./cpcc set fe_iteration:in.nsteps 1000

# and commit this set of updates
./cpcc commit


