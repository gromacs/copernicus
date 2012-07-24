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
./cpcc instance swarms::reparametrize rep
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

#./cpcc set-file rep:in.dihedrals[0][0] cpc/test/lib/swarms/reparametrize/start.xvg
./cpcc set-file rep:in.dihedrals[1][0] cpc/test/lib/swarms/reparametrize/swarm10.xvg
./cpcc set-file rep:in.dihedrals[1][1] cpc/test/lib/swarms/reparametrize/swarm11.xvg
./cpcc set-file rep:in.dihedrals[1][2] cpc/test/lib/swarms/reparametrize/swarm12.xvg
./cpcc set-file rep:in.dihedrals[2][0] cpc/test/lib/swarms/reparametrize/swarm20.xvg
./cpcc set-file rep:in.dihedrals[2][1] cpc/test/lib/swarms/reparametrize/swarm21.xvg
./cpcc set-file rep:in.dihedrals[2][2] cpc/test/lib/swarms/reparametrize/swarm22.xvg
#./cpcc set-file rep:in.dihedrals[3][0] cpc/test/lib/swarms/reparametrize/end.xvg



./cpcc set-file rep:in.start_conf cpc/test/lib/swarms/reparametrize/start_conf.gro
./cpcc set-file rep:in.end_conf cpc/test/lib/swarms/reparametrize/end_conf.gro
./cpcc set-file rep:in.init_top cpc/test/lib/swarms/reparametrize/topol.top
./cpcc set-file rep:in.res_index cpc/test/lib/swarms/reparametrize/index.ndx


# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get rep:out
