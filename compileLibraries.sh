#!/bin/bash

DIR="$( cd "$( dirname "$0" )" && pwd )"

libraryDirs=(cpc/dataflow cpc/network)

for ldir in ${libraryDirs[@]}
do
    cd $DIR/$ldir
    echo "Compiling libraries in $DIR/$ldir"
    for f in *.py
    do
        if [ $f -nt ${f}x ]
        then
            cp $f ${f}x
        fi
    done
    python setup.py build_ext --inplace
done
