#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/fe/grompp.mdp ]; then
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
./cpcc import fe
# add the grompp and mdrun function instances
./cpcc instance fe::solvation fe
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc set-file fe:in.grompp.top test/lib/fe/topol.top
./cpcc set-file fe:in.grompp.include[0]  test/lib/fe/ana.itp
./cpcc set-file fe:in.grompp.mdp test/lib/fe/grompp.mdp

./cpcc set-file fe:in.conf test/lib/fe/conf.gro

./cpcc set fe:in.molecule_name  ethanol
./cpcc set fe:in.solvation_relaxation_time 500
./cpcc set fe:in.precision 0.50


# and commit this set of updates
./cpcc commit


