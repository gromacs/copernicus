#!/bin/sh

# check whether all input files will be available:
if [ ! -e test/lib/swarms/swarm/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc  start test_singlechain
# import the gromacs module with grompp and mdrun functions
./cpcc  import swarms
# add the grompp and mdrun function instances
./cpcc  instance swarms::swarm_string run
# activate the function instance
./cpcc  activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc  commit command.
./cpcc  transact

# set the start and end confs
./cpcc  set-file run:in.start_conf test/lib/swarms/swarm/start.gro
./cpcc  set-file run:in.start_xvg test/lib/swarms/swarm/start.xvg
./cpcc  set-file run:in.end_conf test/lib/swarms/swarm/end.gro
./cpcc  set-file run:in.end_xvg test/lib/swarms/swarm/end.xvg


# declare minimization settings
./cpcc  set-file run:in.minim_grompp.mdp test/lib/swarms/swarm/minim.mdp
./cpcc  set-file run:in.minim_grompp.top test/lib/swarms/swarm/topol.top
./cpcc  set-file run:in.minim_grompp.ndx test/lib/swarms/swarm/index.ndx
./cpcc  set run:in.em_tolerance 100

# declare the thermalization settings
./cpcc  set-file run:in.therm_grompp.mdp test/lib/swarms/swarm/grompp.mdp
./cpcc  set-file run:in.therm_grompp.top test/lib/swarms/swarm/topol.top
./cpcc  set-file run:in.therm_grompp.ndx test/lib/swarms/swarm/index.ndx

# declare restrained run and swarm settings
./cpcc  set-file run:in.equi_grompp.mdp test/lib/swarms/swarm/grompp.mdp
./cpcc  set-file run:in.equi_grompp.top test/lib/swarms/swarm/topol.top
./cpcc  set-file run:in.equi_grompp.ndx test/lib/swarms/swarm/index.ndx
./cpcc  set run:in.restrained_steps 5000
./cpcc  set run:in.swarm_steps 50
./cpcc  set run:in.Nswarms 10
./cpcc  set run:in.Ninterpolants 5

# the residue (collective variable) index
./cpcc  set-file run:in.cv_index test/lib/swarms/swarm/res.ndx

# include a tpr file for g_rama runs
./cpcc  set-file run:in.tpr test/lib/swarms/swarm/topol.tpr

# a topology for writing basic restraints
./cpcc  set-file run:in.top test/lib/swarms/swarm/topol.top

./cpcc  set run:in.Nchains 1
./cpcc  set run:in.Niterations 3
# and commit this set of updates
./cpcc  commit

#./cpcc  get tune:out.resources
./cpcc  get run:out
