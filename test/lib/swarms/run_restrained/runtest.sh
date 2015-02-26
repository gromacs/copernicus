#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/swarms/g_rama_multi/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import swarms
# add the grompp and mdrun function instances
./cpcc instance swarms::run_restrained run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# create the conf_path object
./cpcc set-file run:in.minimized_conf_path[0].conf test/lib/swarms/run_restrained/1.gro
./cpcc set-file run:in.minimized_conf_path[0].itp test/lib/swarms/run_restrained/1.itp
./cpcc set-file run:in.minimized_conf_path[1].conf test/lib/swarms/run_restrained/2.gro
./cpcc set-file run:in.minimized_conf_path[1].itp test/lib/swarms/run_restrained/2.itp
./cpcc set-file run:in.minimized_conf_path[2].conf test/lib/swarms/run_restrained/3.gro
./cpcc set-file run:in.minimized_conf_path[2].itp test/lib/swarms/run_restrained/3.itp

# create the grompp_input object
./cpcc set-file run:in.grompp.mdp test/lib/swarms/run_restrained/grompp.mdp
./cpcc set-file run:in.grompp.top test/lib/swarms/run_restrained/topol.top
./cpcc set-file run:in.grompp.ndx test/lib/swarms/run_restrained/index.ndx

./cpcc set run:in.Nswarms 100
./cpcc set run:in.restrained_steps 50000
# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get run:out
