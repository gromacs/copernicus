#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs_bar/lambda00.edr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the free energy module
./cpcc import fe
# add the function instance
./cpcc instance fe::binding fe
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc set fe:in.ligand_name  ethanol
./cpcc set fe:in.receptor_name  ethanol2

# bound state
./cpcc set-file fe:in.grompp_bound.top cpc/test/lib/fe_binding/bound/topol.top
./cpcc set-file fe:in.grompp_bound.include[0]  cpc/test/lib/fe_binding/bound/ana.itp
./cpcc set-file fe:in.grompp_bound.include[1]  cpc/test/lib/fe_binding/bound/ana2.itp
./cpcc set-file fe:in.grompp_bound.mdp cpc/test/lib/fe_binding/bound/grompp.mdp

./cpcc set-file fe:in.conf_bound cpc/test/lib/fe_binding/bound/conf.gro


# solvated state
./cpcc set-file fe:in.grompp_solv.top cpc/test/lib/fe_binding/solv/topol.top
./cpcc set-file fe:in.grompp_solv.include[0]  cpc/test/lib/fe_binding/solv/ana.itp
./cpcc set-file fe:in.grompp_solv.mdp cpc/test/lib/fe_binding/solv/grompp.mdp

./cpcc set-file fe:in.conf_solv cpc/test/lib/fe_binding/solv/conf.gro


./cpcc set fe:in.solvation_relaxation_time 1000
./cpcc set fe:in.binding_relaxation_time 2000
./cpcc set fe:in.precision 2


# and commit this set of updates
./cpcc commit


