#!/bin/bash

TESTDIR="./cpc/test/lib/plumed/mdrun"

./cpcc rm plumed_test_mdrun
./cpcc start plumed_test_mdrun
./cpcc import plumed
./cpcc instance plumed::mdrun mdrun
./cpcc transact
./cpcc set-file mdrun:in.tpr $TESTDIR/topol.tpr
./cpcc set-file mdrun:in.plumed $TESTDIR/plumed.dat
./cpcc commit
./cpcc activate mdrun

