#!/bin/sh

./cpcc start test
./cpcc import file
./cpcc instance file::to_file tofile

./cpcc set tofile:in.a[0] 3
./cpcc set tofile:in.a[1] 4
./cpcc set tofile:in.a[2] 5
./cpcc set tofile:in.a[3] 6
./cpcc set tofile:in.a[4] 8
./cpcc set tofile:in.a[5] 9

./cpcc activate


