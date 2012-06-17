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
./cpcc instance fe::solvation fe
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc set-file fe:in.grompp.top cpc/test/lib/fe/topol.top
./cpcc set-file fe:in.grompp.include[0]  cpc/test/lib/fe/ana.itp
./cpcc set-file fe:in.grompp.mdp cpc/test/lib/fe/grompp.mdp

./cpcc set-file fe:in.conf cpc/test/lib/fe/conf.gro

./cpcc set fe:in.molecule_name  ethanol
./cpcc set fe:in.solvation_relaxation_time 1000
./cpcc set fe:in.precision 1

#./cpcc set fe_init:in.n_lambdas 10
#
#./cpcc set fe_init:in.a vdwq
#./cpcc set fe_init:in.b vdw
#
#./cpcc connect fe_init:out.path fe_iteration:in.path
#./cpcc connect fe_init:out.resources fe_iteration:in.resources
#./cpcc connect fe_init:out.mdp fe_iteration:in.grompp.mdp
#./cpcc set-file fe_iteration:in.grompp.top cpc/test/lib/fe_init/topol.top
#./cpcc set-file fe_iteration:in.grompp.include[0]  cpc/test/lib/fe_init/ana.itp
#./cpcc set fe_iteration:in.coupled_mol ethanol
#./cpcc set fe_iteration:in.nsteps 1000

# and commit this set of updates
./cpcc commit


