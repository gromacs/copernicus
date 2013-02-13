#!/bin/sh -e

# check whether all input files will be available:
if [ $# -lt 1 ]; then
    echo "Usage:"
    echo "run.sh projectname"
    exit 1
fi
projectname=$1

# start the project
./cpcc start $projectname
# import the gromacs module with grompp and mdrun functions
./cpcc import _test



# add the grompp and mdrun function instances
./cpcc instance _test::external_err ext
./cpcc instance _test::extended_err int
# activate the function instance
./cpcc activate 

# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact
# connect the tpr output of grompp to the tpr input of mdrun
#./cpcc connect grompp:out.tpr mdrun:in.tpr

./cpcc set ext:in.a 3
./cpcc set ext:in.b 4


./cpcc set int:in.a 3
./cpcc set int:in.b 4


./cpcc commit

