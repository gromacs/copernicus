#!/bin/sh

#./cpcc rm  test
./cpcc start test
./cpcc upload ./examples/dataflow/test.xml
./cpcc activate 
./cpcc list 
./cpcc list addmul
./cpcc get add:out.c
