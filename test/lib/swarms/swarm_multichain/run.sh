#!/bin/sh
# check whether all inputs_hemoxybond files will be available:
if [ ! -e cpc/test/lib/swarms/swarm/topol.tpr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc -c $HOME/server.cnx  start test_multichain_topol
# import the gromacs module with grompp and mdrun functions
./cpcc -c $HOME/server.cnx  import swarms
# add the grompp and mdrun function instances
./cpcc -c $HOME/server.cnx  instance swarms::dihedral_swarm run
# activate the function instance
./cpcc -c $HOME/server.cnx  activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc -c $HOME/server.cnx  commit command.
./cpcc -c $HOME/server.cnx  transact

# set the start and end confs
./cpcc -c $HOME/server.cnx  set-file run:in.start_conf ~/oxy_to_deoxy_sd_long_inputs/start.gro
./cpcc -c $HOME/server.cnx  set-file run:in.start_xvg ~/oxy_to_deoxy_sd_long_inputs/start.xvg
./cpcc -c $HOME/server.cnx  set-file run:in.end_conf ~/oxy_to_deoxy_sd_long_inputs/end.gro
./cpcc -c $HOME/server.cnx  set-file run:in.end_xvg ~/oxy_to_deoxy_sd_long_inputs/end.xvg


# declare minimization settings
./cpcc -c $HOME/server.cnx  set-file run:in.minim_grompp.mdp ~/oxy_to_deoxy_sd_long_inputs/minim.mdp
./cpcc -c $HOME/server.cnx  set-file run:in.minim_grompp.top ~/oxy_to_deoxy_sd_long_inputs/topol.top
./cpcc -c $HOME/server.cnx  set-file run:in.minim_grompp.ndx ~/oxy_to_deoxy_sd_long_inputs/index.ndx
./cpcc -c $HOME/server.cnx  set run:in.em_tolerance 1000

# declare restrained run and swarm settings
./cpcc -c $HOME/server.cnx  set-file run:in.equi_grompp.mdp ~/oxy_to_deoxy_sd_long_inputs/grompp.mdp
./cpcc -c $HOME/server.cnx  set-file run:in.equi_grompp.top ~/oxy_to_deoxy_sd_long_inputs/topol.top
./cpcc -c $HOME/server.cnx  set-file run:in.equi_grompp.ndx ~/oxy_to_deoxy_sd_long_inputs/index.ndx
./cpcc -c $HOME/server.cnx  set run:in.restrained_steps 500000
./cpcc -c $HOME/server.cnx  set run:in.swarm_steps 1000
./cpcc -c $HOME/server.cnx  set run:in.Nswarms 10
./cpcc -c $HOME/server.cnx  set run:in.Ninterpolants 20

# the residue index
./cpcc -c $HOME/server.cnx  set-file run:in.res_index ~/oxy_to_deoxy_sd_long_inputs/res.ndx

# include a tpr file for g_rama runs
./cpcc -c $HOME/server.cnx  set-file run:in.tpr ~/oxy_to_deoxy_sd_long_inputs/topol.tpr

# the topology object
./cpcc -c $HOME/server.cnx  set-file run:in.top ~/oxy_to_deoxy_sd_long_inputs/topol.top
./cpcc -c $HOME/server.cnx  set-file run:in.include[0] ~/oxy_to_deoxy_sd_long_inputs/topol_Protein_chain_A.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[1] ~/oxy_to_deoxy_sd_long_inputs/topol_Protein_chain_B.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[2] ~/oxy_to_deoxy_sd_long_inputs/topol_Protein_chain_C.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[3] ~/oxy_to_deoxy_sd_long_inputs/topol_Protein_chain_D.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[4] ~/oxy_to_deoxy_sd_long_inputs/topol_Other_chain_A2.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[5] ~/oxy_to_deoxy_sd_long_inputs/topol_Other_chain_B2.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[6] ~/oxy_to_deoxy_sd_long_inputs/topol_Other_chain_C2.itp
./cpcc -c $HOME/server.cnx  set-file run:in.include[7] ~/oxy_to_deoxy_sd_long_inputs/topol_Other_chain_D2.itp


./cpcc -c $HOME/server.cnx  set run:in.Nchains 4
./cpcc -c $HOME/server.cnx  set run:in.Niterations 10
# and commit this set of updates
./cpcc -c $HOME/server.cnx  commit

./cpcc -c $HOME/server.cnx  get run:out


