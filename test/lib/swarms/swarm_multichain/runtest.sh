#!/bin/sh
# check whether all inputs_hemoxybond files will be available:
if [ ! -e cpc/test/lib/swarms/swarm/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc -c amd1.cnx  start test_multichain
# import the gromacs module with grompp and mdrun functions
./cpcc -c amd1.cnx  import swarms
# add the grompp and mdrun function instances
./cpcc -c amd1.cnx  instance swarms::dihedral_swarm run
# activate the function instance
./cpcc -c amd1.cnx  activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc -c amd1.cnx  commit command.
./cpcc -c amd1.cnx  transact

# set the start and end confs
./cpcc -c amd1.cnx  set-file run:in.start_conf cpc/test/lib/swarms/swarm_multichain/start.gro
./cpcc -c amd1.cnx  set-file run:in.start_xvg cpc/test/lib/swarms/swarm_multichain/start.xvg
./cpcc -c amd1.cnx  set-file run:in.end_conf cpc/test/lib/swarms/swarm_multichain/end.gro
./cpcc -c amd1.cnx  set-file run:in.end_xvg cpc/test/lib/swarms/swarm_multichain/end.xvg


# declare minimization settings
./cpcc -c amd1.cnx  set-file run:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_multichain/minim.mdp
./cpcc -c amd1.cnx  set-file run:in.minim_grompp.top cpc/test/lib/swarms/swarm_multichain/topol.top
./cpcc -c amd1.cnx  set-file run:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_multichain/index.ndx
./cpcc -c amd1.cnx  set run:in.em_tolerance 1000

./cpcc -c amd1.cnx  set-file run:in.therm_grompp.mdp cpc/test/lib/swarms/swarm_multichain/therm.mdp
./cpcc -c amd1.cnx  set-file run:in.therm_grompp.top cpc/test/lib/swarms/swarm_multichain/topol.top
# declare restrained run and swarm settings
./cpcc -c amd1.cnx  set-file run:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_multichain/grompp.mdp
./cpcc -c amd1.cnx  set-file run:in.equi_grompp.top cpc/test/lib/swarms/swarm_multichain/topol.top
./cpcc -c amd1.cnx  set-file run:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_multichain/index.ndx
./cpcc -c amd1.cnx  set run:in.restrained_steps 500
./cpcc -c amd1.cnx  set run:in.swarm_steps 10
./cpcc -c amd1.cnx  set run:in.Nswarms 10
./cpcc -c amd1.cnx  set run:in.Ninterpolants 10

# the residue index
./cpcc -c amd1.cnx  set-file run:in.res_index cpc/test/lib/swarms/swarm_multichain/res.ndx

# include a tpr file for g_rama runs
./cpcc -c amd1.cnx  set-file run:in.tpr cpc/test/lib/swarms/swarm_multichain/topol.tpr

# the topology object
./cpcc -c amd1.cnx  set-file run:in.top cpc/test/lib/swarms/swarm_multichain/topol.top
./cpcc -c amd1.cnx  set-file run:in.include[0] cpc/test/lib/swarms/swarm_multichain/topol_Protein_chain_A.itp
./cpcc -c amd1.cnx  set-file run:in.include[1] cpc/test/lib/swarms/swarm_multichain/topol_Protein_chain_B.itp
./cpcc -c amd1.cnx  set-file run:in.include[2] cpc/test/lib/swarms/swarm_multichain/topol_Protein_chain_C.itp
./cpcc -c amd1.cnx  set-file run:in.include[3] cpc/test/lib/swarms/swarm_multichain/topol_Protein_chain_D.itp
./cpcc -c amd1.cnx  set-file run:in.include[4] cpc/test/lib/swarms/swarm_multichain/topol_Other_chain_A2.itp
./cpcc -c amd1.cnx  set-file run:in.include[5] cpc/test/lib/swarms/swarm_multichain/topol_Other_chain_B2.itp
./cpcc -c amd1.cnx  set-file run:in.include[6] cpc/test/lib/swarms/swarm_multichain/topol_Other_chain_C2.itp
./cpcc -c amd1.cnx  set-file run:in.include[7] cpc/test/lib/swarms/swarm_multichain/topol_Other_chain_D2.itp


./cpcc -c amd1.cnx  set run:in.Nchains 4
./cpcc -c amd1.cnx  set run:in.Niterations 5
# and commit this set of updates
./cpcc -c amd1.cnx  commit

./cpcc -c amd1.cnx  get run:out


