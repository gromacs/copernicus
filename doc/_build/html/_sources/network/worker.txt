.. _worker:

******
Worker
******

Workers are responsible for most of the computational work in copernicus.
They act as simple programs connecting to a server and asking for work.
Workers can have very different capabilites with regard to cpu capabilites,
and what programs they can execute.
When you start a worker it will establish a secure connection to your server and
announce the programs and their versions it can execute.
The server will then match the capabilities of the worker to the available jobs
in the queue. By default a worker will try to use all available cores on a
machine however this can be configured.



Worker and Server communication
===============================

You can connect as many workers as you want to a Server.
And the only thing you need to do this is a connection bundle.
Workers and Server communication is one sided.
It is always initiated by the Worker and the Server is only able to send responses back.


Automatic partitioning
======================

Workers always try to fully utilize the maximum number of cores available to them.
Thus they able to partition themselves to run multiple jobs at
once. For example if you have a worker with 24 available cores it can run one 24
core job or one 12 core job and 12 single core jobs. As long as the worker has
free cores it will announce itself as available to the Server.
However, workers do not monitor the overall CPU usage of the computer they are
running on, but assume that the CPU is not used for other tasks.


Limiting the number of cores
============================

By default a worker tries to use all of the cores available on a machine.
However you can limit this with the flag ``-n``

.. code-block:: none

    cpc-worker smp -n 12

You can also define how the partitioning of each individual job should be
limited with the flag ``-s``.
For example to limit your worker to use only 12 cores and only 2 cores
per job you can do:

.. code-block:: none

    cpc-worker smp -n 12 -s 2

Running jobs from a specific project
====================================

A worker can be dedicated to run jobs from a specific project this is done with
the flag ``-p``

.. code-block:: none

    cpc-worker -p my-project smp


Avoiding idle workers
=====================

If you want to avoid having idle workers you can instruct them to shutdown after
an amount of idle time. This is done with the flag ``-q``

.. code-block:: none

    cpc-worker -q 10 smp

Specifying work directory
=========================

When a job is running Workers store their work information in work directory.
This work directory is by default created in the same location as where the worker
is started. If you want to specify another work directory you can do it with the flag
``-wd``

.. code-block:: none

    cpc-worker -wd my-worker-dir smp

.. _platformtypes:

Platform types
==============

Workers can be started with different platform types.
The standard platform type is ``smp``. This one should be used to run a worker on a
single node.
The platform type ``mpi`` should be used when one has binaries using OpenMPI.
Any binary that you usually start with mpirun from the command line should use
this platform type.

Executing workers in a cluster environment
==========================================

Starting workers in a cluster environment is very straightforward.
You will only need to call the worker from your job submission script.
You only need to start one worker for all the resources that you allocate.


This is the general structure to use for starting a copernicus worker.

.. code-block:: none

    ## 1.ADD specific parameters for your queuing system ##

    ## 2. starting a copernicus worker ##
    cpc-worker mpi -n NUMBER_OF_CORES


Here is a specific version for the slurm queing system

.. code-block:: none

    #!/bin/bash
    #SBATCH -N 12
    #SBATCH --exclusive
    #SBATCH --time=05:00:00
    #SBATCH --job-name=cpc

    #Assuming each node has 16 cores, 12*16=192
    cpc-worker mpi -n 192

Best practices when using 1000+ cores
=====================================

Copernicus is a very powerful tool and can start using thousands of cores at
an instant.  When starting large scale resources it is advisable to gradually
ramp up the resource usage and monitor the project to see if any critical errors
occur in the project or your cluster environment.
If everything looks fine start allocating more and more resources.
