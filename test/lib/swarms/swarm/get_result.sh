#!/bin/bash

# Copy out the equilibration:out.confs[] .gro array and start/end confs

# NOTE: we can get this from run:out.paths[][] too.

# swarm iterations to get data from
for ITER in {0..79}
do
    # Points to get data from (including start/end)
    # Note: check the -eq 0 and -eq 17 below too
    for MIDX in {0..15}
    do

#        if [ $MIDX -eq 0 ]; then
#            CPCVAR="run:iter$ITER:in.start_conf"
#        elif [ $MIDX -eq 17 ]; then
#            CPCVAR="run:iter$ITER:in.end_conf"
#        else
#            CPCVAR="run:iter$ITER:equilibration:out.confs[$((MIDX-1))]"
#        fi

        CPCVAR="run:iter$ITER:equilibration:out.confs[$MIDX]"

        # Get a conf from all points including start/end
        cpcc getf -f "iter${ITER}_conf$MIDX.gro" $CPCVAR

    done    
done
