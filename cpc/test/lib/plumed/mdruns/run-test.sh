#!/bin/bash

TESTDIR="./cpc/test/lib/plumed/mdruns"

./cpcc rm plumed_test_mdruns
./cpcc start plumed_test_mdruns
./cpcc import plumed
./cpcc instance plumed::mdruns mdruns
./cpcc transact
./cpcc set-file mdruns:in.tpr[0] $TESTDIR/topol.tpr
./cpcc set-file mdruns:in.tpr[1] $TESTDIR/topol.tpr
./cpcc set-file mdruns:in.tpr[2] $TESTDIR/topol.tpr
./cpcc set-file mdruns:in.plumed[0] $TESTDIR/plumed.dat
./cpcc set-file mdruns:in.plumed[1] $TESTDIR/plumed.dat
./cpcc set-file mdruns:in.plumed[2] $TESTDIR/plumed.dat
./cpcc commit
./cpcc activate mdruns

