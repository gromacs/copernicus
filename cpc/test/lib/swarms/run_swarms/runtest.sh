#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/swarms/g_rama_multi/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import swarms
# add the grompp and mdrun function instances
./cpcc instance swarms::run_swarms run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# create the conf_array_array object
./cpcc set-file run:in.conf_array_array[0][0] cpc/test/lib/swarms/run_swarms/1.gro
./cpcc set-file run:in.conf_array_array[0][1] cpc/test/lib/swarms/run_swarms/2.gro
./cpcc set-file run:in.conf_array_array[0][2] cpc/test/lib/swarms/run_swarms/3.gro

# create the grompp_input object
./cpcc set-file run:in.grompp.mdp cpc/test/lib/swarms/run_swarms/grompp.mdp
./cpcc set-file run:in.grompp.top cpc/test/lib/swarms/run_swarms/topol.top
./cpcc set-file run:in.grompp.ndx cpc/test/lib/swarms/run_swarms/index.ndx
./cpcc set-file run:in.tpr cpc/test/lib/swarms/run_swarms/topol.tpr

./cpcc set run:in.swarm_steps 1000
# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get run:out
