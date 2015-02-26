#!/bin/bash

TESTDIR="./cpc/test/lib/plumed/grompp_mdruns"

./cpcc rm plumed_test_grompp_mdruns
./cpcc start plumed_test_grompp_mdruns
./cpcc import plumed
./cpcc import gromacs
./cpcc instance plumed::grompp_mdruns grompp_mdruns
./cpcc transact
./cpcc set-file grompp_mdruns:in.conf[0] $TESTDIR/conf.gro
./cpcc set-file grompp_mdruns:in.conf[1] $TESTDIR/conf.gro
./cpcc set-file grompp_mdruns:in.conf[2] $TESTDIR/conf.gro
./cpcc set-file grompp_mdruns:in.conf[3] $TESTDIR/conf.gro
./cpcc set-file grompp_mdruns:in.conf[4] $TESTDIR/conf.gro
./cpcc set-file grompp_mdruns:in.plumed[0] $TESTDIR/plumed.dat
./cpcc set-file grompp_mdruns:in.top[0] $TESTDIR/topol.top
./cpcc set-file grompp_mdruns:in.mdp[0] $TESTDIR/grompp.mdp
./cpcc commit
./cpcc activate grompp_mdruns
