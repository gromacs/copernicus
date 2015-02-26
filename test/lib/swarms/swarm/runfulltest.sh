#!/bin/sh

# check whether all input files will be available:
#if [ ! -e cpc/test/lib/swarms/g_rama_multi/topol.tpr ]; then
#    echo "This test script must be run from within the copernicus base directory"
#    exit 1
#fi

# start the project
./cpcc  start alanine-dipeptide
# import the gromacs module with grompp and mdrun functions
./cpcc  import swarms
# add the grompp and mdrun function instances
./cpcc  instance swarms::dihedral_swarm run
# activate the function instance
./cpcc  activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc  commit command.
./cpcc  transact

# set the start and end confs
./cpcc  set-file run:in.start_conf cpc/test/lib/swarms/swarm/start.gro
./cpcc  set-file run:in.start_xvg cpc/test/lib/swarms/swarm/start.xvg
./cpcc  set-file run:in.end_conf cpc/test/lib/swarms/swarm/end.gro
./cpcc  set-file run:in.end_xvg cpc/test/lib/swarms/swarm/end.xvg


# declare minimization settings
./cpcc  set-file run:in.minim_grompp.mdp cpc/test/lib/swarms/swarm/minim.mdp
./cpcc  set-file run:in.minim_grompp.top cpc/test/lib/swarms/swarm/topol.top
./cpcc  set run:in.em_tolerance 100

# declare restrained run and swarm settings
./cpcc  set-file run:in.equi_grompp.mdp cpc/test/lib/swarms/swarm/grompp.mdp
./cpcc  set-file run:in.equi_grompp.top cpc/test/lib/swarms/swarm/topol.top
./cpcc  set run:in.restrained_steps 50000
./cpcc  set run:in.swarm_steps 20
./cpcc  set run:in.Nswarms 100
./cpcc  set run:in.Ninterpolants 20

# the residue index
./cpcc  set-file run:in.res_index cpc/test/lib/swarms/swarm/res.ndx

# include a tpr file for g_rama runs
./cpcc  set-file run:in.tpr cpc/test/lib/swarms/swarm/topol.tpr

# a topology for writing basic restraints
./cpcc  set-file run:in.restraint_top cpc/test/lib/swarms/swarm/restraints.top
./cpcc  set-file run:in.top cpc/test/lib/swarms/swarm/topol.top

./cpcc  set run:in.Niterations 10
# and commit this set of updates
./cpcc  commit

#./cpcc  get tune:out.resources
./cpcc  get run:out
