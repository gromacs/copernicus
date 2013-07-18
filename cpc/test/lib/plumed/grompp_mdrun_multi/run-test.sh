#!/bin/bash

TESTDIR="./cpc/test/lib/plumed/grompp_mdrun_multi"

./cpcc rm plumed_test_grompp_mdrun_multi
./cpcc start plumed_test_grompp_mdrun_multi
./cpcc import plumed
./cpcc import gromacs
./cpcc instance plumed::grompp_mdrun_multi grompp_mdrun_multi
./cpcc transact
./cpcc set-file grompp_mdrun_multi:in.conf[0] $TESTDIR/conf.gro
./cpcc set-file grompp_mdrun_multi:in.conf[1] $TESTDIR/conf.gro
./cpcc set-file grompp_mdrun_multi:in.conf[2] $TESTDIR/conf.gro
./cpcc set-file grompp_mdrun_multi:in.conf[3] $TESTDIR/conf.gro
./cpcc set-file grompp_mdrun_multi:in.conf[4] $TESTDIR/conf.gro
./cpcc set-file grompp_mdrun_multi:in.plumed[0] $TESTDIR/plumed.dat
./cpcc set-file grompp_mdrun_multi:in.top[0] $TESTDIR/topol.top
./cpcc set-file grompp_mdrun_multi:in.mdp[0] $TESTDIR/grompp.mdp
./cpcc commit
./cpcc activate grompp_mdrun_multi
