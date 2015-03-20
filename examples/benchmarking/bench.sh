#!/bin/bash -e

# check whether all input files will be available:
if [ ! -e examples/benchmarking/bench.sh  ]; then
    echo "This example script must be run from within the copernicus base directory"
    exit 1
fi

if [ $# -lt 2 ]; then
    echo "Usage:"
    echo "bench projectname numjobs"
    exit 1
fi
projectname=$1
numjobs=`expr $2 - 1`
# start the project
./cpcc start $projectname
# import the gromacs module with grompp and mdrun functions
./cpcc import benchmark
# add the grompp and mdrun function instances

./cpcc transact

./cpcc instance benchmark::result_collector results
./cpcc set results.in.num_samples $2

for i in $(eval echo {0..$numjobs})
do
	./cpcc instance benchmark::sleep sleep_$i
	./cpcc connect sleep_$i.out.exec_time.roundtrip_time results.in.sleep_time_array[$i].roundtrip_time
	./cpcc connect sleep_$i.out.exec_time.start_timestamp results.in.sleep_time_array[$i].start_timestamp
	./cpcc connect sleep_$i.out.exec_time.end_timestamp results.in.sleep_time_array[$i].end_timestamp
done


for i in $(eval echo {0..$numjobs})
do
	./cpcc set sleep_$i.in.sleep_time 1
done

./cpcc commit
# activate the function instance
./cpcc activate 
