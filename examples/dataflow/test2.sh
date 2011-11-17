#!/bin/sh

./cpcc start test
./cpcc import file
./cpcc instance file::ext_test ext

./cpcc set ext:in.a[0] 3
./cpcc set ext:in.a[1] 4
./cpcc set ext:in.a[2] 5
./cpcc set ext:in.a[3] 6
./cpcc set ext:in.a[4] 8
./cpcc set ext:in.a[5] 9

./cpcc set ext:in.b[0] 3
./cpcc set ext:in.b[1] 4
./cpcc set ext:in.b[2] 5
./cpcc set ext:in.b[3] 6
./cpcc set ext:in.b[4] 8
./cpcc set ext:in.b[5] 9

./cpcc activate 

