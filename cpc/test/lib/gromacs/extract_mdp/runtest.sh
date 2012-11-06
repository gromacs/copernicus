#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs/bar/lambda00.edr ]; then
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
./cpcc instance gromacs::extract_mdp exm
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file exm:in.mdp cpc/test/lib/gromacs/extract_mdp/grompp.mdp
./cpcc set exm:in.settings[0].name dt
./cpcc set exm:in.settings[0].value 0.004
./cpcc set exm:in.name dt

# and commit this set of updates
./cpcc commit


./cpcc get exm:out.value
