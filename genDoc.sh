#!/bin/sh

cd $CPC_HOME
PYTHONPATH=$CPC_HOME
sphinx-apidoc -F -H Copernicus -A 'Sander Pronk, Iman Pouya, Per Larsson, Magnus Lundborg, Erik Lindahl, Per Kasson, Patrik Falkman, Martin Andersson' -V 2.0 -o doc/api cpc
cd doc/api
make html
