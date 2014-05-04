#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/swarms/g_rama_multi/topol.tpr ]; then
    echo "This test script must be iter0 from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mditer0 functions
./cpcc import swarms
# add the grompp and mditer0 function instances
./cpcc instance swarms::dihedral_swarm_iteration iter0
./cpcc instance swarms::dihedral_swarm_iteration iter1
./cpcc instance swarms::dihedral_swarm_iteration iter2
./cpcc instance swarms::dihedral_swarm_iteration iter3
./cpcc instance swarms::dihedral_swarm_iteration iter4
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

# set the start and end confs
./cpcc set-file iter0:in.start_conf cpc/test/lib/swarms/swarm_iteration/start.gro
./cpcc set-file iter0:in.start_xvg cpc/test/lib/swarms/swarm_iteration/start.xvg
./cpcc set-file iter0:in.end_conf cpc/test/lib/swarms/swarm_iteration/end.gro
./cpcc set-file iter0:in.end_xvg cpc/test/lib/swarms/swarm_iteration/end.xvg


# create the path object
./cpcc set-file iter0:in.path[0].conf cpc/test/lib/swarms/swarm_iteration/1.gro
./cpcc set-file iter0:in.path[0].top cpc/test/lib/swarms/swarm_iteration/1.top
./cpcc set-file iter0:in.path[1].conf cpc/test/lib/swarms/swarm_iteration/2.gro
./cpcc set-file iter0:in.path[1].top cpc/test/lib/swarms/swarm_iteration/2.top
./cpcc set-file iter0:in.path[2].conf cpc/test/lib/swarms/swarm_iteration/3.gro
./cpcc set-file iter0:in.path[2].top cpc/test/lib/swarms/swarm_iteration/3.top
./cpcc set-file iter0:in.path[3].conf cpc/test/lib/swarms/swarm_iteration/4.gro
./cpcc set-file iter0:in.path[3].top cpc/test/lib/swarms/swarm_iteration/4.top
./cpcc set-file iter0:in.path[4].conf cpc/test/lib/swarms/swarm_iteration/5.gro
./cpcc set-file iter0:in.path[4].top cpc/test/lib/swarms/swarm_iteration/5.top
./cpcc set-file iter0:in.path[5].conf cpc/test/lib/swarms/swarm_iteration/6.gro
./cpcc set-file iter0:in.path[5].top cpc/test/lib/swarms/swarm_iteration/6.top
./cpcc set-file iter0:in.path[6].conf cpc/test/lib/swarms/swarm_iteration/7.gro
./cpcc set-file iter0:in.path[6].top cpc/test/lib/swarms/swarm_iteration/7.top
./cpcc set-file iter0:in.path[7].conf cpc/test/lib/swarms/swarm_iteration/8.gro
./cpcc set-file iter0:in.path[7].top cpc/test/lib/swarms/swarm_iteration/8.top
./cpcc set-file iter0:in.path[8].conf cpc/test/lib/swarms/swarm_iteration/9.gro
./cpcc set-file iter0:in.path[8].top cpc/test/lib/swarms/swarm_iteration/9.top
./cpcc set-file iter0:in.path[9].conf cpc/test/lib/swarms/swarm_iteration/10.gro
./cpcc set-file iter0:in.path[9].top cpc/test/lib/swarms/swarm_iteration/10.top
./cpcc set-file iter0:in.path[10].conf cpc/test/lib/swarms/swarm_iteration/11.gro
./cpcc set-file iter0:in.path[10].top cpc/test/lib/swarms/swarm_iteration/11.top
./cpcc set-file iter0:in.path[11].conf cpc/test/lib/swarms/swarm_iteration/12.gro
./cpcc set-file iter0:in.path[11].top cpc/test/lib/swarms/swarm_iteration/12.top
./cpcc set-file iter0:in.path[12].conf cpc/test/lib/swarms/swarm_iteration/13.gro
./cpcc set-file iter0:in.path[12].top cpc/test/lib/swarms/swarm_iteration/13.top
./cpcc set-file iter0:in.path[13].conf cpc/test/lib/swarms/swarm_iteration/14.gro
./cpcc set-file iter0:in.path[13].top cpc/test/lib/swarms/swarm_iteration/14.top
./cpcc set-file iter0:in.path[14].conf cpc/test/lib/swarms/swarm_iteration/15.gro
./cpcc set-file iter0:in.path[14].top cpc/test/lib/swarms/swarm_iteration/15.top
./cpcc set-file iter0:in.path[15].conf cpc/test/lib/swarms/swarm_iteration/16.gro
./cpcc set-file iter0:in.path[15].top cpc/test/lib/swarms/swarm_iteration/16.top
./cpcc set-file iter0:in.path[16].conf cpc/test/lib/swarms/swarm_iteration/17.gro
./cpcc set-file iter0:in.path[16].top cpc/test/lib/swarms/swarm_iteration/17.top
./cpcc set-file iter0:in.path[17].conf cpc/test/lib/swarms/swarm_iteration/18.gro
./cpcc set-file iter0:in.path[17].top cpc/test/lib/swarms/swarm_iteration/18.top

# declare minimization settings
./cpcc set-file iter0:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file iter0:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter0:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter0:in.em_tolerance 60

# declare restrained iter0 and swarm settings
./cpcc set-file iter0:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file iter0:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter0:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter0:in.restrained_steps 50000
./cpcc set iter0:in.swarm_steps 20
./cpcc set iter0:in.Nswarms 250
./cpcc set iter0:in.Ninterpolants 20


# the residue index
./cpcc set-file iter0:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx

# include a tpr file
./cpcc set-file iter0:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr





# iteration 1 inputs
./cpcc set-file iter1:in.start_conf cpc/test/lib/swarms/swarm_iteration/start.gro
./cpcc set-file iter1:in.start_xvg cpc/test/lib/swarms/swarm_iteration/start.xvg
./cpcc set-file iter1:in.end_conf cpc/test/lib/swarms/swarm_iteration/end.gro
./cpcc set-file iter1:in.end_xvg cpc/test/lib/swarms/swarm_iteration/end.xvg
# create the path object
# declare minimization settings
./cpcc set-file iter1:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file iter1:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter1:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter1:in.em_tolerance 100
# declare restrained iter1 and swarm settings
./cpcc set-file iter1:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file iter1:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter1:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter1:in.restrained_steps 50000
./cpcc set iter1:in.swarm_steps 20
./cpcc set iter1:in.Nswarms 250
./cpcc set iter1:in.Ninterpolants 20
# the residue index
./cpcc set-file iter1:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx
# include a tpr file
./cpcc set-file iter1:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr

# iteration 1 inputs
./cpcc set-file iter2:in.start_conf cpc/test/lib/swarms/swarm_iteration/start.gro
./cpcc set-file iter2:in.start_xvg cpc/test/lib/swarms/swarm_iteration/start.xvg
./cpcc set-file iter2:in.end_conf cpc/test/lib/swarms/swarm_iteration/end.gro
./cpcc set-file iter2:in.end_xvg cpc/test/lib/swarms/swarm_iteration/end.xvg
# declare minimization settings
./cpcc set-file iter2:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file iter2:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter2:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter2:in.em_tolerance 1000
# declare restrained iter2 and swarm settings
./cpcc set-file iter2:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file iter2:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter2:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter2:in.restrained_steps 50000
./cpcc set iter2:in.swarm_steps 80
./cpcc set iter2:in.Nswarms 250
./cpcc set iter2:in.Ninterpolants 20
# the residue index
./cpcc set-file iter2:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx
# include a tpr file
./cpcc set-file iter2:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr


# iteration 1 inputs
./cpcc set-file iter3:in.start_conf cpc/test/lib/swarms/swarm_iteration/start.gro
./cpcc set-file iter3:in.start_xvg cpc/test/lib/swarms/swarm_iteration/start.xvg
./cpcc set-file iter3:in.end_conf cpc/test/lib/swarms/swarm_iteration/end.gro
./cpcc set-file iter3:in.end_xvg cpc/test/lib/swarms/swarm_iteration/end.xvg
# declare minimization settings
./cpcc set-file iter3:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file iter3:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter3:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter3:in.em_tolerance 1000
# declare restrained iter3 and swarm settings
./cpcc set-file iter3:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file iter3:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter3:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter3:in.restrained_steps 50000
./cpcc set iter3:in.swarm_steps 80
./cpcc set iter3:in.Nswarms 250
./cpcc set iter3:in.Ninterpolants 20
# the residue index
./cpcc set-file iter3:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx
# include a tpr file
./cpcc set-file iter3:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr



# iteration 1 inputs
./cpcc set-file iter4:in.start_conf cpc/test/lib/swarms/swarm_iteration/start.gro
./cpcc set-file iter4:in.start_xvg cpc/test/lib/swarms/swarm_iteration/start.xvg
./cpcc set-file iter4:in.end_conf cpc/test/lib/swarms/swarm_iteration/end.gro
./cpcc set-file iter4:in.end_xvg cpc/test/lib/swarms/swarm_iteration/end.xvg
# create the path object
# declare minimization settings
./cpcc set-file iter4:in.minim_grompp.mdp cpc/test/lib/swarms/swarm_iteration/minim.mdp
./cpcc set-file iter4:in.minim_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter4:in.minim_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter4:in.em_tolerance 1000
# declare restrained iter4 and swarm settings
./cpcc set-file iter4:in.equi_grompp.mdp cpc/test/lib/swarms/swarm_iteration/grompp.mdp
./cpcc set-file iter4:in.equi_grompp.top cpc/test/lib/swarms/swarm_iteration/topol.top
./cpcc set-file iter4:in.equi_grompp.ndx cpc/test/lib/swarms/swarm_iteration/index.ndx
./cpcc set iter4:in.restrained_steps 50000
./cpcc set iter4:in.swarm_steps 80
./cpcc set iter4:in.Nswarms 250
./cpcc set iter4:in.Ninterpolants 20
# the residue index
./cpcc set-file iter4:in.resindex cpc/test/lib/swarms/swarm_iteration/res.ndx
# include a tpr file
./cpcc set-file iter4:in.tpr cpc/test/lib/swarms/swarm_iteration/topol.tpr


./cpcc set-file iter0:in.restraint_top cpc/test/lib/swarms/swarm_iteration/restraints.top
./cpcc set-file iter1:in.restraint_top cpc/test/lib/swarms/swarm_iteration/restraints.top
./cpcc set-file iter2:in.restraint_top cpc/test/lib/swarms/swarm_iteration/restraints.top
./cpcc set-file iter3:in.restraint_top cpc/test/lib/swarms/swarm_iteration/restraints.top
./cpcc set-file iter4:in.restraint_top cpc/test/lib/swarms/swarm_iteration/restraints.top


# set topology files for restraint writing
./cpcc connect iter0:out iter1:in
./cpcc connect iter1:out iter2:in
./cpcc connect iter2:out iter3:in
./cpcc connect iter3:out iter4:in

# and commit this set of updates
./cpcc commit

#./cpcc get tune:out.resources

#./cpcc get tune:out.resources
