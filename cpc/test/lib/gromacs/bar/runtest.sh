#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/gromacs/bar/lambda00.edr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "Usage:"
    echo "runtest projectname"
    exit 1
fi
projectname=$1

# start the project
./cpcc start $projectname
# import the gromacs module with grompp and mdrun functions
./cpcc import gromacs
# add the grompp and mdrun function instances
./cpcc instance gromacs::g_bar bar
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact


./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda00.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda01.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda02.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda03.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda04.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda05.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda06.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda07.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda08.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda09.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda10.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/gromacs/bar/lambda11.edr



# and commit this set of updates
./cpcc commit


./cpcc get bar:out.dG
