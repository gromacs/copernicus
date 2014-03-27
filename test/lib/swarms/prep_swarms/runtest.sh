#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/swarms/g_rama_multi/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the trrmacs module with grompp and mdrun functions
./cpcc import swarms
# add the trrmpp and mdrun function instances
./cpcc instance swarms::prep_swarms run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# create the conf_path object
./cpcc set-file run:in.trrs[0] test/lib/swarms/prep_swarms/1.trr
./cpcc set-file run:in.trrs[1] test/lib/swarms/prep_swarms/2.trr
./cpcc set-file run:in.trrs[2] test/lib/swarms/prep_swarms/3.trr

# create the trrmpp_input object
./cpcc set-file run:in.tpr test/lib/swarms/prep_swarms/topol.tpr

# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get run:out
