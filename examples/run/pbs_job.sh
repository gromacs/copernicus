# The name of the script is myjob
#PBS -N cpc_runner

# Only 1 hour wall-clock time will be given to this job
#PBS -l walltime=1:00:00

# Number of cores to be allocated is 96.
#PBS -l mppwidth=96

#PBS -e error_file.e
#PBS -o output_file.o

CPCDIR=/cfs/emil/pdc/pronk/git/copernicus/src
CPCCONF=/cfs/emil/pdc/pronk/cpc

cd $PBS_O_WORKDIR

$CPCDIR/cpc -c  $CPCCONF runner cray 96 

