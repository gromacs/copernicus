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
./cpcc instance swarms::g_rama_multi grm
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file grm:in.tpr cpc/test/lib/swarms/g_rama_multi/topol.tpr
./cpcc set-file grm:in.confs[0] cpc/test/lib/swarms/g_rama_multi/out0.gro
./cpcc set-file grm:in.confs[1] cpc/test/lib/swarms/g_rama_multi/out1.gro
./cpcc set-file grm:in.confs[2] cpc/test/lib/swarms/g_rama_multi/out2.gro
./cpcc set-file grm:in.confs[3] cpc/test/lib/swarms/g_rama_multi/out3.gro

# and commit this set of updates
./cpcc commit


#./cpcc get tune:out.resources
