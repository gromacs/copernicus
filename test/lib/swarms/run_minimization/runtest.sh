#!/bin/sh

# check whether all input files will be available:
# NOTE: check removed in this form, since g_rama_multi does not exist among the tests.

#if [ ! -e test/lib/swarms/g_rama_multi/topol.tpr ]; then
#    echo "This test script must be run from within the copernicus base directory"
#    exit 1
#fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import swarms
# add the grompp and mdrun function instances
./cpcc instance swarms::run_minimization run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# create the conf_path object
# Note: I changed these so conf_path[].itp now is .include[0], and we include a .top in each
# conf_path[] entry as it seems it's needed there - on the other hand, the "global" grompp top
# further below is not actually used it seems.
./cpcc set-file run:in.conf_path[0].conf test/lib/swarms/run_minimization/1.gro
./cpcc set-file run:in.conf_path[0].include[0] test/lib/swarms/run_minimization/1.itp
./cpcc set-file run:in.conf_path[0].top test/lib/swarms/run_minimization/topol.top

./cpcc set-file run:in.conf_path[1].conf test/lib/swarms/run_minimization/2.gro
./cpcc set-file run:in.conf_path[1].include[0] test/lib/swarms/run_minimization/2.itp
./cpcc set-file run:in.conf_path[1].top test/lib/swarms/run_minimization/topol.top

./cpcc set-file run:in.conf_path[2].conf test/lib/swarms/run_minimization/3.gro
./cpcc set-file run:in.conf_path[2].include[0] test/lib/swarms/run_minimization/3.itp
./cpcc set-file run:in.conf_path[2].top test/lib/swarms/run_minimization/topol.top

# create the grompp_input object
./cpcc set-file run:in.grompp.mdp test/lib/swarms/run_minimization/minim.mdp
# this is not read by run_minimization..
./cpcc set-file run:in.grompp.top test/lib/swarms/run_minimization/topol.top
./cpcc set-file run:in.grompp.ndx test/lib/swarms/run_minimization/index.ndx

./cpcc set run:in.em_tolerance 1000
# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get run:out
