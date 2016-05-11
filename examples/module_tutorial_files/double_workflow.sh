#!/bin/sh

cpcc start demo

cpcc import math
cpcc instance math::double_value db

cpcc activate

cpcc set db:in.integer_inputs[+] 2
cpcc set db:in.integer_inputs[+] 2

