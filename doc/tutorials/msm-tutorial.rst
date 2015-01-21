.. _msmtutorial:

************
MSM Tutorial
************

In this tutorial we will try out the MSM workflow of Copernicus. Markov State models (MSM).
This tutorial includes two examples where we fold proteins. The first one is Alanine dipeptide which
is a very small system that can be run on pretty much an modern machine within a reasonable time.
The second is fs-peptide which might take about 24 hours depending on the computing resources used.


Prerequisites
^^^^^^^^^^^^^

Make sure you have `Gromacs <http://www.gromacs.org>`_ and `MSMBuilder <http://MSMBuilder.org>`_ installed.
MSMBuilder needs to be installed on the same system that the server is running on.
For unix machines there is an already prepared instance under examples/msm/msmbuilder-known-good.tar.gz

Gromacs needs to be installed on the system that the server is running on and all machines
where you will run workers.


Learning the method
^^^^^^^^^^^^^^^^^^^

Although Copernicus automates MSM:s it will not automatically find the optimal parameters for you
That is where you the user need to have a solid understanding of the method.


Overview of the workflow
^^^^^^^^^^^^^^^^^^^^^^^^

The MSM workflow starts by spawning simulations from a set of provided starting conformations.
Simulations continue until enough data is gatehered to start building MSM:s.
The MSM building starts by first clustering all conformations using a hybrid K-means,
K-medoids algorithm[REF]. The clustering metric used Is RMSD. After this a microstate MSM is built
and then a macrostate MSM. At each MSM generation it is possible to view at the current macrostates.
This process continues as many times as specified by the user. Usually it should be run until the MSM
converges toward a state.

The MSM workflow is built using gromacs modules and MSMBuilder.
At the moment it supports gromacs 4.6,gromacs 5.0 and MSMBuilder 2.0.
To start the workflow the following input is neecessary.

Settings
^^^^^^^^

**num_microstates** (int) The number of microstates.

**num_macrostates** (int) The number of macrostates.

**lag_time** (int) The lag time of the Markov state model

**grpname** (string)  Defines what part of the system to use during clustering. Gromacs selection syntax is
used here.

**recluster** (int) The reclustering frequency. Determines how often clustering should be done.
Defined in nanoseconds. As simulation time has summed up to this amount a new generation of MSM
building will take place.

**num_generations** (int) Number of MSM generations. After the defined amount of generations the workflow
will finish.

**num_sim** (int) Number of parallel that will be run at each generation

**confs** (gro files) A set of starting conformations to use as initial seeds. If the number of
simulations are higher than the starting conformations the workflow will simply choose starting
conformation in a cyclic fashion.

**grompp** A collection of settings needed for grompp. The required parameters are the following:

        * **mdp** A gromacs mdp file
        * **top** A gromacs topology file

The optional parameters are the following

        * **include** array of additional files. For example if the top file includes other files these have to be included here.



How to determine what parameters to set?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Number of microstates, macrostates and Lag time will be very specific depending on the system that
you are analyzing.  To determine what might work for your system you need to have a good understanding
of the method. Other things that might affect the quality if the MSM is the simulation length and
output frequency.



========================================
Example 1: Alanine dipeptide
========================================

Alanine dipeptide is a very small system that is possible to run on pretty much any computer.
In this example we will build an MSM that will find the folded state of this peptide

For this tutorial we need some example files that are located under examples/msm-test in the
Copernicus source.
A set of files are prepared in this bundle. It includes the following.

1.	4 starting conformations equil0.gro,equil1.gro,equil2.gro,equil3.gro
2.	Simulation settings in the file grompp.mdp.
3.	A topology file.
4.	 The script runtest.sh. It includes a short script with all the commands necessary to get the project up and running. Each of the commands will be explained below.


We will first start a project

.. code-block:: none

    cpcc start alanine-dipeptide-msm

We then need to import the msm module, create a new instance of it and activate it.

.. code-block:: none

    cpcc import msm
    cpcc instance msm:msm_gmx_adaptive msm
    cpcc activate


Now we are going to provide all the necessary input. The workflow will start running as soon as
all necessary input is provided. Since there is no lower limit on the number of starting
conformations, it will start running as soon as it has at least one. In this case we do not want
this. We want to provide 4 starting conformations thus we need to tell the workflow to wait until
told to start.
This is done with the transact command.

.. code-block:: none

    cpcc transact

Now we provide all the necessary input

.. code-block:: none

    cpcc setf msm:in.grompp.top examples/msm-test/topol.top
    cpcc setf msm:in.grompp.mdp examples/msm-test/grompp.mdp

    cpcc setf msm:in.confs[+] examples/msm-test/equil0.gro
    cpcc setf msm:in.confs[+] examples/msm-test/equil1.gro
    cpcc setf msm:in.confs[+] examples/msm-test/equil2.gro
    cpcc setf msm:in.confs[+] examples/msm-test/equil3.gro

    cpcc set msm:in.recluster 1.0
    cpcc set msm:in.num_sim 20

    cpcc set msm:in.num_microstates 100
    cpcc set msm:in.num_macrostates 10
    cpcc set msm:in.lag_time 2

    cpcc set msm:in.grpname  Protein
    cpcc set msm:in.num_generations 6

We finally commit the transact block.

.. code-block:: none

    cpcc commit

Copernicus will now start spawning simulations and put them on the queue.

Check the status of the project with ``cpcc status``. This will inform you on the state of the project
and how many jobs are in the queue and how many are currently running. If you want to see in detail
what jobs are in the queue use the command ``cpcc queue``.

After a short while (specify time) enough simulation data has been collected and MSM building will
start

If you run the command ``cpcc ls msm`` you will see a new function instance ``build_msm_0``. Traverse it and
you will be able to fetch the macrostates and also a current max state which is the most likely end
state for the system at the moment.

After a little longer you will notice that more build_msm instances will show up.
Looking at the max states of these you will notice that after about 4 iterations  we end up in the
same state, meaning a folded state of the peptide has been found.


========================================
Example 2: fs-peptide
========================================

Fs-peptide is a little larger bit larger system that can be folded. However it might take a couple
of days depending on the computing resources you have.
For example on 4 32 core machines with 2 GPUS each it took about 24 hours to reach a folded state.

All the necessary files for fs-peptide can be found under examples/msm/msm-fs-peptide
