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
./cpcc  set run:in.minim_restrforce 4000.0
./cpcc  set run:in.em_tolerance 100

# declare the thermalization settings
./cpcc  set-file run:in.therm_grompp.mdp test/lib/swarms/swarm/therm.mdp
./cpcc  set-file run:in.therm_grompp.top test/lib/swarms/swarm/topol.top
./cpcc  set run:in.therm_restrforce 4000.0

# declare restrained run and swarm settings
./cpcc  set-file run:in.equi_grompp.mdp test/lib/swarms/swarm/run.mdp
./cpcc  set-file run:in.equi_grompp.top test/lib/swarms/swarm/topol.top
./cpcc  set run:in.equil_restrforce 4000.0

./cpcc  set run:in.restrained_steps 20000
./cpcc  set run:in.swarm_steps 15

# This is the number of swarm configurations to launch for each stringpoint, so it
# amplifies the work needed quite much if increased. For a demo, 10-20 is enough here
# but to get a smooth curve as a result, it should be higher, like 50-100.

./cpcc  set run:in.Nswarms 20

# The number of stringpoints to use, 10-16 are definitely enough for the alanine dipeptide
# demo, but for more complex transitions you should probably use more.

./cpcc  set run:in.Ninterpolants 16

# the residue (collective variable) index
./cpcc  set-file run:in.cv_index test/lib/swarms/swarm/res.ndx

# include a tpr file for g_rama runs
./cpcc  set-file run:in.tpr test/lib/swarms/swarm/topol.tpr

# a topology for writing basic restraints
./cpcc  set-file run:in.top test/lib/swarms/swarm/topol.top

# Allow the start/end points to drift just like the rest of the stringpoints
./cpcc  set run:in.fix_endpoints 0

./cpcc  set run:in.Nchains 1

# Number of iterations - for quick testing, set this to a lower number
# For the complete demo, 50-80 iterations are required when using the other settings here

#./cpcc  set run:in.Niterations 10
./cpcc  set run:in.Niterations 80

# and commit this set of updates
./cpcc  commit


