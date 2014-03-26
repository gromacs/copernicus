#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/swarms/g_rama_multi/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the xvgmacs module with grompp and mdrun functions
./cpcc import swarms
# add the xvgmpp and mdrun function instances
./cpcc instance swarms::reparametrize run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# set the start and end confs
./cpcc set-file run:in.start_conf cpc/test/lib/swarms/reparametrize/init.gro
./cpcc set-file run:in.start_xvg cpc/test/lib/swarms/swarm_iteration/0.xvg
./cpcc set-file run:in.end_conf cpc/test/lib/swarms/reparametrize/target.gro
./cpcc set-file run:in.end_xvg cpc/test/lib/swarms/swarm_iteration/20.xvg


# create the dihedrals[0] object
./cpcc set-file run:in.dihedrals[0][0] cpc/test/lib/swarms/reparametrize/1.xvg
./cpcc set-file run:in.dihedrals[0][1] cpc/test/lib/swarms/reparametrize/2.xvg
./cpcc set-file run:in.dihedrals[0][2] cpc/test/lib/swarms/reparametrize/3.xvg
./cpcc set-file run:in.dihedrals[1][0] cpc/test/lib/swarms/reparametrize/4.xvg
./cpcc set-file run:in.dihedrals[1][1] cpc/test/lib/swarms/reparametrize/5.xvg
./cpcc set-file run:in.dihedrals[1][2] cpc/test/lib/swarms/reparametrize/6.xvg
./cpcc set-file run:in.dihedrals[2][0] cpc/test/lib/swarms/reparametrize/7.xvg
./cpcc set-file run:in.dihedrals[2][1] cpc/test/lib/swarms/reparametrize/8.xvg
./cpcc set-file run:in.dihedrals[2][2] cpc/test/lib/swarms/reparametrize/9.xvg

# create the restrained-out field
./cpcc set-file run:in.restrained_out[0].conf cpc/test/lib/swarms/swarm_iteration/1.gro
./cpcc set-file run:in.restrained_out[1].conf cpc/test/lib/swarms/swarm_iteration/2.gro
./cpcc set-file run:in.restrained_out[2].conf cpc/test/lib/swarms/swarm_iteration/3.gro


./cpcc set run:in.Nswarms 3
./cpcc set-file run:in.res_index cpc/test/lib/swarms/swarm_iteration/res.ndx

# include a tpr file
./cpcc set-file run:in.init_top cpc/test/lib/swarms/swarm_iteration/topol.top

# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources
./cpcc get run:out
