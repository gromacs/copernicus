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
./cpcc set-file grm:in.confs[0][0].conf cpc/test/lib/swarms/g_rama_multi/0.gro
./cpcc set-file grm:in.confs[0][0].itp cpc/test/lib/swarms/g_rama_multi/0.itp

./cpcc set-file grm:in.confs[1][0].conf cpc/test/lib/swarms/g_rama_multi/1.gro
./cpcc set-file grm:in.confs[1][0].itp cpc/test/lib/swarms/g_rama_multi/0.itp
./cpcc set-file grm:in.confs[1][1].conf cpc/test/lib/swarms/g_rama_multi/2.gro
./cpcc set-file grm:in.confs[1][1].itp cpc/test/lib/swarms/g_rama_multi/0.itp
./cpcc set-file grm:in.confs[1][2].conf cpc/test/lib/swarms/g_rama_multi/3.gro
./cpcc set-file grm:in.confs[1][2].itp cpc/test/lib/swarms/g_rama_multi/0.itp

# and commit this set of updates
./cpcc commit


#./cpcc get tune:out.resources
