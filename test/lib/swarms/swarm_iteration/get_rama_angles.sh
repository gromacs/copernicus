#!/bin/bash

for ((i=1;i<20;i++))
do
	g_rama -f $i.gro -o $i.xvg 
done
