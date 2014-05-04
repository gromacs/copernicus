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
./cpcc instance swarms::dihedral_swarm_iteration run
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# set the start and end confs
./cpcc set-file run:in.start_conf cpc/test/lib/swarms/swarm_iteration/init.gro
./cpcc set-file run:in.start_xvg cpc/test/lib/swarms/swarm_iteration/0.xvg
./cpcc set-file run:in.end_conf cpc/test/lib/swarms/swarm_iteration/target.gro
./cpcc set-file run:in.end_xvg cpc/test/lib/swarms/swarm_iteration/20.xvg


# create the path object
./cpcc set-file run:in.path[0].conf cpc/test/lib/swarms/swarm_iteration/1.gro
./cpcc set-file run:in.path[0].itp cpc/test/lib/swarms/swarm_iteration/1.itp
./cpcc set-file run:in.path[1].conf cpc/test/lib/swarms/swarm_iteration/2.gro
./cpcc set-file run:in.path[1].itp cpc/test/lib/swarms/swarm_iteration/2.itp
./cpcc set-file run:in.path[2].conf cpc/test/lib/swarms/swarm_iteration/3.gro
./cpcc set-file run:in.path[2].itp cpc/test/lib/swarms/swarm_iteration/3.itp
#./cpcc set-file run:in.path[3].conf cpc/test/lib/swarms/swarm_iteration/4.gro
#./cpcc set-file run:in.path[3].itp cpc/test/lib/swarms/swarm_iteration/4.itp
#./cpcc set-file run:in.path[4].conf cpc/test/lib/swarms/swarm_iteration/5.gro
#./cpcc set-file run:in.path[4].itp cpc/test/lib/swarms/swarm_iteration/5.itp
#./cpcc set-file run:in.path[5].conf cpc/test/lib/swarms/swarm_iteration/6.gro
#./cpcc set-file run:in.path[5].itp cpc/test/lib/swarms/swarm_iteration/6.itp
#./cpcc set-file run:in.path[6].conf cpc/test/lib/swarms/swarm_iteration/7.gro
#./cpcc set-file run:in.path[6].itp cpc/test/lib/swarms/swarm_iteration/7.itp
#./cpcc set-file run:in.path[7].conf cpc/test/lib/swarms/swarm_iteration/8.gro
#./cpcc set-file run:in.path[7].itp cpc/test/lib/swarms/swarm_iteration/8.itp
#./cpcc set-file run:in.path[8].conf cpc/test/lib/swarms/swarm_iteration/9.gro
#./cpcc set-file run:in.path[8].itp cpc/test/lib/swarms/swarm_iteration/9.itp
#./cpcc set-file run:in.path[9].conf cpc/test/lib/swarms/swarm_iteration/10.gro
#./cpcc set-file run:in.path[9].itp cpc/test/lib/swarms/swarm_iteration/10.itp
#./cpcc set-file run:in.path[10].conf cpc/test/lib/swarms/swarm_iteration/11.gro
#./cpcc set-file run:in.path[10].itp cpc/test/lib/swarms/swarm_iteration/11.itp
#./cpcc set-file run:in.path[11].conf cpc/test/lib/swarms/swarm_iteration/12.gro
#./cpcc set-file run:in.path[11].itp cpc/test/lib/swarms/swarm_iteration/12.itp
#./cpcc set-file run:in.path[12].conf cpc/test/lib/swarms/swarm_iteration/13.gro
#./cpcc set-file run:in.path[12].itp cpc/test/lib/swarms/swarm_iteration/13.itp
#./cpcc set-file run:in.path[13].conf cpc/test/lib/swarms/swarm_iteration/14.gro
#/cpcc set-file run:in.path[13].itp cpc/test/lib/swarms/swarm_iteration/14.itp
#./cpcc set-file run:in.path[14].conf cpc/test/lib/swarms/swarm_iteration/15.gro
#./cpcc set-file run:in.path[14].itp cpc/test/lib/swarms/swarm_iteration/15.itp
#./cpcc set-file run:in.path[15].conf cpc/test/lib/swarms/swarm_iteration/16.gro
#./cpcc set-file run:in.path[15].itp cpc/test/lib/swarms/swarm_iteration/16.itp
#./cpcc set-file run:in.path[16].conf cpc/test/lib/swarms/swarm_iteration/17.gro
#./cpcc set-file run:in.path[16].itp cpc/test/lib/swarms/swarm_iteration/17.itp
#./cpcc set-file run:in.path[17].conf cpc/test/lib/swarms/swarm_iteration/18.gro
#./cpcc set-file run:in.path[17].itp cpc/test/lib/swarms/swarm_iteration/18.itp
#./cpcc set-file run:in.path[18].conf cpc/test/lib/swarms/swarm_iteration/19.gro
#./cpcc set-file run:in.path[18].itp cpc/test/lib/swarms/swarm_iteration/19.itp

# declare minimization settings
./cpcc set-file run:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file run:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file run:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set run:in.em_tolerance 1000

# declare restrained run and swarm settings
./cpcc set-file run:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file run:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file run:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set run:in.restrained_steps 5000
./cpcc set run:in.swarm_steps 50
./cpcc set run:in.Nswarms 10
./cpcc set run:in.Ninterpolants 5

# the residue index
./cpcc set-file run:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx

# include a tpr file
./cpcc set-file run:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr

# and commit this set of updates
./cpcc commit


# User commits and activates when swarms finish 
./cpcc transact
./cpcc instance swarms::get_dihedrals grama
./cpcc connect run:out.swarms grama:in.confs
./cpcc connect run:out.tpr grama:in.tpr

./cpcc instance swarms::reparametrize reparam
./cpcc connect grama:out.xvgs reparam:in.dihedrals
./cpcc connect run:out.restrained_out reparam:in.restrained_out
./cpcc set reparam:in.Nswarms 10
./cpcc set reparam:in.Ninterpolants 5
./cpcc set-file reparam:in.start_conf cpc/test/lib/swarms/swarm_iteration/init.gro
./cpcc set-file reparam:in.start_xvg cpc/test/lib/swarms/swarm_iteration/0.xvg
./cpcc set-file reparam:in.end_conf cpc/test/lib/swarms/swarm_iteration/target.gro
./cpcc set-file reparam:in.end_xvg cpc/test/lib/swarms/swarm_iteration/20.xvg

./cpcc set-file reparam:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx
./cpcc set-file reparam:in.init_top cpc/test/lib/swarms/swarm_iteration/topol.top

./cpcc commit
#./cpcc get tune:out.resources
./cpcc get run:out
