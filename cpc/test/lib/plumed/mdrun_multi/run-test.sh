#!/bin/bash

TESTDIR="./cpc/test/lib/plumed/mdrun_multi"

./cpcc rm plumed_test_mdrun_multi
./cpcc start plumed_test_mdrun_multi
./cpcc import plumed
./cpcc instance plumed::mdrun_multi mdrun_multi
./cpcc transact
./cpcc set-file mdrun_multi:in.tpr[0] $TESTDIR/topol.tpr
./cpcc set-file mdrun_multi:in.tpr[1] $TESTDIR/topol.tpr
./cpcc set-file mdrun_multi:in.tpr[2] $TESTDIR/topol.tpr
./cpcc set-file mdrun_multi:in.plumed[0] $TESTDIR/plumed.dat
./cpcc set-file mdrun_multi:in.plumed[1] $TESTDIR/plumed.dat
./cpcc set-file mdrun_multi:in.plumed[2] $TESTDIR/plumed.dat
./cpcc commit
./cpcc activate mdrun_multi

