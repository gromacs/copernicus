#!/bin/sh

#./cpcc rm  test

if [ $# -lt 1 ]; then
    echo "Usage:"
    echo "runtest projectname"
    exit 1
fi
projectname=$1


./cpcc start $projectname
./cpcc upload ./examples/dataflow/test.xml
./cpcc activate 
./cpcc list 
./cpcc list addmul
./cpcc get add:out.c
