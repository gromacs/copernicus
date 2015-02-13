#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/fe/conf.gro ]; then
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
./cpcc set-file fe:in.grompp_bound.top test/lib/fe/binding/bound/topol.top
./cpcc set-file fe:in.grompp_bound.include[0]  test/lib/fe/binding/bound/ana.itp
./cpcc set-file fe:in.grompp_bound.include[1]  test/lib/fe/binding/bound/ana2.itp
./cpcc set-file fe:in.grompp_bound.mdp test/lib/fe/binding/bound/grompp.mdp
./cpcc set-file fe:in.grompp_bound.ndx  test/lib/fe/binding/bound/index.ndx

./cpcc set-file fe:in.conf_bound test/lib/fe/binding/bound/conf.gro

./cpcc set fe:in.restraints_bound[0].resname ethanol2
./cpcc set fe:in.restraints_bound[0].distance 0
./cpcc set fe:in.restraints_bound[0].strength 1000

# solvated state
./cpcc set-file fe:in.grompp_solv.top test/lib/fe/binding/solv/topol.top
./cpcc set-file fe:in.grompp_solv.include[0]  test/lib/fe/binding/solv/ana.itp
./cpcc set-file fe:in.grompp_solv.mdp test/lib/fe/binding/solv/grompp.mdp

./cpcc set-file fe:in.conf_solv test/lib/fe/binding/solv/conf.gro


./cpcc set fe:in.solvation_relaxation_time 1000
./cpcc set fe:in.binding_relaxation_time 2000
./cpcc set fe:in.precision 2


# and commit this set of updates
./cpcc commit


