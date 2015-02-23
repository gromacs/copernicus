#!/bin/sh

n_instances=500

cpcc start test
cpcc import benchmark
cpcc transact
cpcc instance benchmark::add_benchmark add
cpcc set add.in.n_instances $n_instances
cpcc commit
cpcc activate
