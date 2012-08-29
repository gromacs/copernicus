#!/bin/sh

# check whether all input files will be available:
if [ ! -e cpc/test/lib/fe/calc_path/lambda00.edr ]; then
    echo "This test script must be run from within the copernicus base directory"
    exit 1
fi

# start the project
./cpcc start test
# import the gromacs module with grompp and mdrun functions
./cpcc import gromacs
./cpcc import fe
# add the grompp and mdrun function instances
./cpcc instance gromacs::g_bar bar
./cpcc instance fe::calc_path calc_path
# activate the function instance
./cpcc activate


# start a transaction: all the 'set' and 'connect' commands following this
# will be executed as one atomic operation upon the cpcc commit command.
./cpcc transact

./cpcc connect bar:out.bar_values calc_path:in.bar_values

./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda00.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda01.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda02.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda03.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda04.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda05.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda06.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda07.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda08.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda09.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda10.edr
./cpcc set-file bar:in.edr[+] cpc/test/lib/fe/calc_path/lambda11.edr



# and commit this set of updates
./cpcc commit


#./cpcc get bar:out.dG
