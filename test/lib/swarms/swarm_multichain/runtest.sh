#!/bin/sh
# check whether all inputs_hemoxybond files will be available:
if [ ! -e test/lib/swarms/swarm/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc  start test_multichain
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
./cpcc  set-file run:in.start_conf test/lib/swarms/swarm_multichain/start.gro
./cpcc  set-file run:in.start_xvg test/lib/swarms/swarm_multichain/start.xvg
./cpcc  set-file run:in.end_conf test/lib/swarms/swarm_multichain/end.gro
./cpcc  set-file run:in.end_xvg test/lib/swarms/swarm_multichain/end.xvg


# declare minimization settings
./cpcc  set-file run:in.minim_grompp.mdp test/lib/swarms/swarm_multichain/minim.mdp
./cpcc  set-file run:in.minim_grompp.top test/lib/swarms/swarm_multichain/topol.top
#./cpcc  set-file run:in.minim_grompp.ndx test/lib/swarms/swarm_multichain/index.ndx
./cpcc  set run:in.em_tolerance 1000

./cpcc  set-file run:in.therm_grompp.mdp test/lib/swarms/swarm_multichain/therm.mdp
./cpcc  set-file run:in.therm_grompp.top test/lib/swarms/swarm_multichain/topol.top
# declare restrained run and swarm settings
./cpcc  set-file run:in.equi_grompp.mdp test/lib/swarms/swarm_multichain/grompp.mdp
./cpcc  set-file run:in.equi_grompp.top test/lib/swarms/swarm_multichain/topol.top
#./cpcc  set-file run:in.equi_grompp.ndx test/lib/swarms/swarm_multichain/index.ndx
./cpcc  set run:in.restrained_steps 500
./cpcc  set run:in.swarm_steps 10
./cpcc  set run:in.Nswarms 10
./cpcc  set run:in.Ninterpolants 10

# the residue index
./cpcc  set-file run:in.res_index test/lib/swarms/swarm_multichain/res.ndx

# include a tpr file for g_rama runs
./cpcc  set-file run:in.tpr test/lib/swarms/swarm_multichain/topol.tpr

# the topology object
./cpcc  set-file run:in.top test/lib/swarms/swarm_multichain/topol.top
./cpcc  set-file run:in.include[0] test/lib/swarms/swarm_multichain/topol_Protein_chain_A.itp
./cpcc  set-file run:in.include[1] test/lib/swarms/swarm_multichain/topol_Protein_chain_B.itp
./cpcc  set-file run:in.include[2] test/lib/swarms/swarm_multichain/topol_Protein_chain_C.itp
./cpcc  set-file run:in.include[3] test/lib/swarms/swarm_multichain/topol_Protein_chain_D.itp
./cpcc  set-file run:in.include[4] test/lib/swarms/swarm_multichain/topol_Other_chain_A2.itp
./cpcc  set-file run:in.include[5] test/lib/swarms/swarm_multichain/topol_Other_chain_B2.itp
./cpcc  set-file run:in.include[6] test/lib/swarms/swarm_multichain/topol_Other_chain_C2.itp
./cpcc  set-file run:in.include[7] test/lib/swarms/swarm_multichain/topol_Other_chain_D2.itp

./cpcc  set run:in.Nchains 4
./cpcc  set run:in.Niterations 5
# and commit this set of updates
./cpcc  commit

./cpcc  get run:out


