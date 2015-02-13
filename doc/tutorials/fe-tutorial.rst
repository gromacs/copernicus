.. _fetutorial:

********************
Free Energy Tutorial
********************

In this tutorial we will go through the Free Energy workflow of Copernicus. The tutorial includes two
separate parts, demonstrating solvation free energy and binding free energy calculations, respectively.

Prerequisites
^^^^^^^^^^^^^

Make sure you have `GROMACS <http://www.gromacs.org>`_ installed before starting.

GROMACS needs to be installed on the system that the server is running on and all machines
where you will run workers.


Learning the method
^^^^^^^^^^^^^^^^^^^

Although Copernicus automates large parts of the free energy calculation workflow, including lambda point
placement, it will not automatically set all parameters for you. The user needs to have a solid understanding
of the method, both for setting up the jobs and for critically assessing the results afterwards.


Overview of the workflow
^^^^^^^^^^^^^^^^^^^^^^^^

The free energy workflow for solvation free energy calculations consists of a stepwise decoupling of the
studied molecule in a solvent.

The binding free energy workflow consists of two parts. The first part is the decoupling of the molecule
in a pure solvent (just as in the solvation free energy workflow) and the second part is the decoupling of
the molecule bound to, e.g., a protein.

The calculations are made up of a number of iterations. The length of each iteration is based on the
relaxation time input (20 * relaxation time) to ensure proper sampling. After each iteration the current
precision (estimated error of the sampling) is compared to the requested precision. If the requested
precision is not yet reached another iteration is added.

The distribution of lambda points can be automatically determined. The GROMACS tool g_bar cannot use
input with different lambda point distributions for one calculation. If the distribution does not change,
the results from multiple simulations will be used to calculate the estimated delta G (or delta F).
Otherwise there will be separate estimations from different iterations and they will all be used to
generate an average delta G, weighted by the estimated errors of the contributing values and the error
is propagated from the terms.

The free energy workflow supports GROMACS 4.6 and GROMACS 5.0. However, the restraints arguments in the
binding free energy workflow is only compatible with GROMACS 5.0. If using GROMACS 4.6 restraints must
be specified in the mdp file instead and taken account for afterwards.

To start the workflow the following input is neecessary.

Settings
^^^^^^^^

.. _solvation-free-energy-input:

Solvation Free Energy
---------------------

* grompp
    A collection of settings needed for grompp. The required parameters are the following:

    * mdp
        A GROMACS mdp file
    * top
        A GROMACS topology file

* conf (gro file)
    A coordinate file of the solvated molecule.

* molecule_name
    The name or group number of the molecule that is studied.

* solvation_relaxation_time (int)
    The estimated relaxation time for solvation in simulation time steps.
    A value of 0.1 ns is a good guide line if the solvent is water. If the simulation time step is 2 fs, that
    means that this value should be 50000.


The optional parameters are the following:

* precision (float)
    The desired precision in kJ/mol. The simulations stop when this precision is reached. The default value is 1 kJ/mol.

* min_iterations (int)
    A minimum number of iterations to perform. Even if the desired precision is reached there will at least be this
    many iterations performed.
* optimize_lambdas (bool)
    After each iteration (and the first setup stages) a lambda distribution
    is calculated. If this optimize_lambdas is False the lambda point distribution will still be calculated,
    but not used. If this is True the calculated lambda distribution will be used for the next iteration,
    if the number of lambda points changed or if the spacing between at least two lambda points differ more
    than the optimization_tolerance. The default is True.

* lambdas_all_to_all (bool)
    If this is set to True the delta H from each lambda state to all other
    lambda states will be calculated, instead of just to its neighbors. The default is False.

* optimization_tolerance (float)
    The tolerance (percent) for deciding when the difference between
    lambda spacing in two subsequent runs is so large that the new lambda values are kept, i.e., the lambda
    point distribution is optimized. If set to 0 lambda values will be optimized every iteration. The default
    value is 20.

* stddev_spacing (float)
    The target standard deviation spacing of lambda points in kT for lambda
    point spacing optimization. A higher value will give fewer lambda points, but might require more iterations
    than a lower value. This value is not used if optimize_lambdas is False. Default value is 1 kT.

* n_lambdas_init (int)
    The number of lamba points from which to start lambda optimizations.
    If optimizations are disabled this number of lambda points will be used for all iterations (unless
    lambdas _q, lambdas_lj or lambdas_ljq are used to specify a specific lambda point distribution). The
    lambda points will be evenly distributed between lambda 0 and 1. By default 16 lambda points are used
    to start with, but if the lambda point distribution of the system is very irregular more lambda points
    might be needed from the start to make a good optimization.

* simultaneous_decoupling (bool)
    If this is True Coulomb and Lennard-Jones are decoupled at the same time.
    Default is False.

* lambdas_q (list of floats)
    A list of lambda values for electrostatics decoupling. If this is set there
    will be no lambda point optimization for electrostatics.

* lambdas_lj (list of floats)
    A list of lambda values for Lennard-Jones decoupling. If this is set there
    will be no lambda point optimization for Lennard-Jones.

* lambdas_ljq (list of floats)
    A list of lambda values for simultaneous electrostatics and Lennard-Jones
    decoupling. If this is set there will be no lambda point optimization.


Binding Free Energy
-------------------

* ligand_name
    The name of the ligand that will be decoupled while binding as well as free in solution.
* receptor_name
    The name of the receptor.
* grompp_bound
    Input values of the bound state for grompp, see :ref:`solvation-free-energy-input`.
* grompp_solv
    Input values of the state free in solution for grompp, see :ref:`solvation-free-energy-input`.
* conf_bound (gro file)
    A coordinate file of the bound state.
* conf_solv (gro file)
    A coordinate file of the state in solution.
* binding_relaxation_time (int)
    The estimated relaxation time for the bound configuration in simulation
    time steps. A value of 10 ns is a good guide line. If the simulation time step is 2 fs, that means that this
    value should be 50000.
* solvation_relaxation_time (int)
    See :ref:`solvation-free-energy-input`.

Most of the optional parameters are described in :ref:`solvation-free-energy-input`, but some of them are
duplicated with different names for the bound and solvated states:

* restraints_bound
    An array of restraints on a ligand. Each element in the array can contain:

    * resname
        The name of the residue to restrain to.
    * pos
        Relative location to restrain to.
    * strength
        Coupling strength (in kJ/mol/nm).

* **precision**
* **min_iterations**
* **optimize_lambdas**
* **lambdas_all_to_all**
* **optimization_tolerance**
* **stddev_spacing**
* **binding_n_lambdas_init**
* **solvation_n_lambdas_init**
* **simultaneous_decoupling**
* **solvation_lambdas_q**
* **solvation_lambdas_lj**
* **solvation_lambdas_ljq**
* **binding_lambdas_q**
* **binding_lambdas_lj**
* **binding_lambdas_ljq**

How to determine what parameters to set?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Apart from the required input, in most cases only n_lambdas_init depends on the system, but 16 or 21 initial
lambda points are enough in most cases.



Example 1: Hydration Free Energy of Ethanol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The calculation of free energy of solvation of ethanol in water is used to demonstrate how to use the
module.

For this tutorial we need some example files that are located under test/lib/fe/ in the
Copernicus source.
A set of files are prepared in this bundle. It includes the following.

1.	A starting conformation, conf.gro
2.	Simulation settings in the file grompp.mdp.
3.	A topology file, topol.top.
4.	The script runtest.sh. It includes a short script with all the commands necessary to get the project up and running. Each of the commands will be explained below.

If running the script itself it must be executed from the copernicus root directory, e.g.

.. code-block:: none

    test/lib/fe/runtest.sh <projectname>


We first start a project with the name specified by the input argument to the script.

.. code-block:: none

    cpcc start $projectname

We then need to import the fe module, create a new instance of it and activate it.

.. code-block:: none

    cpcc import fe
    cpcc instance fe::solvation fe
    cpcc activate


Now we are going to provide all the necessary input. The workflow will start running as soon as
all necessary input is provided. In order to be able to specify the input in any order we tell
the workflow to wait until told to start, otherwise it would start when all required input is
given, i.e. before fe:in.precision is set in the example below. This is done with the transact command.

.. code-block:: none

    cpcc transact

Now we provide all the necessary input, observe that solvation_relaxation_time is lower than recommended
to enable short iterations in order to make it possible to view the output sooner than what would
otherwise be possible.

.. code-block:: none

    cpcc set-file fe:in.grompp.top examples/fe/topol.top
    cpcc set-file fe:in.grompp.include[0]  examples/fe/ana.itp
    cpcc set-file fe:in.grompp.mdp examples/fe/grompp.mdp

    cpcc set-file fe:in.conf examples/fe/conf.gro

    cpcc set fe:in.molecule_name  ethanol
    cpcc set fe:in.solvation_relaxation_time 500
    cpcc set fe:in.precision 0.50

We finally commit the transact block.

.. code-block:: none

    cpcc commit

Copernicus will now start spawning simulations and put them on the queue.

Check the status of the project with ``cpcc status``. This will inform you on the state of the project
and how many jobs are in the queue and how many are currently running. If you want to see in detail
what jobs are in the queue use the command ``cpcc queue``. If no Copernicus worker is active no
simulations will start.

The simulations will continue until the estimated error of the calculations is equal to or lower than
the specified precision. If running only one worker this can take quite a while.

It is possible to check the output before the instance is finished. The following command will show you
the current output:

.. code-block:: none

    cpcc get fe.out

To see just the currently estimated free energy of solvation run:

.. code-block:: none

    cpcc get fe.out.delta_f

When finished the delta_f should be approximately -19 kJ/mol, which is not too far from the experimental
value of -20.93 ± 0.8 kJ/mol.

Example 2: Binding Free Energy of Ethanol to Ethanol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Binding free energies are most often calculated for a small molecule to a larger receptor. In this example
we calculate the binding free energy of one molecule of ethanol to another molecule of ethanol.

For this tutorial we need some example files that are located under test/lib/fe/binding in the
Copernicus source.
A set of files are prepared in this bundle. It includes the following.

1.      Starting conformations, solv/conf.gro and bound/conf.gro
2.      Simulation settings in the files solv/grompp.mdp and bound/grompp.mdp.
3.      Topology files, solv/topol.top and bound/topol.top.
4.      An index file for the bound state, bound/index.ndx
5.      The script runtest.sh. It includes a short script with all the commands necessary to get the project up and running. Each of the commands will be explained below.

If running the script itself it must be executed from the copernicus root directory, e.g.

    test/lib/fe/binding/runtest.sh <projectname>

We first start a project with the name specified by the input argument to the script.

.. code-block:: none

    cpcc start $projectname

We then need to import the fe module, create a new instance of it and activate it.

.. code-block:: none

    cpcc import fe
    cpcc instance fe::binding fe
    cpcc activate


Now we are going to provide all the necessary input. The workflow will start running as soon as
all necessary input is provided. In order to be able to specify the input in any order we tell
the workflow to wait until told to start, otherwise it would start when all required input is
given. This is done with the transact command.

.. code-block:: none

    cpcc transact

Now we provide all the necessary input, observe that solvation_relaxation_time is lower than recommended
to enable short iterations in order to make it possible to view the output sooner than what would
otherwise be possible.

.. code-block:: none

    cpcc set fe:in.ligand_name  ethanol
    cpcc set fe:in.receptor_name  ethanol2

    # bound state
    cpcc set-file fe:in.grompp_bound.top test/lib/fe/binding/bound/topol.top
    cpcc set-file fe:in.grompp_bound.include[0]  test/lib/fe/binding/bound/ana.itp
    cpcc set-file fe:in.grompp_bound.include[1]  test/lib/fe/binding/bound/ana2.itp
    cpcc set-file fe:in.grompp_bound.mdp test/lib/fe/binding/bound/grompp.mdp
    cpcc set-file fe:in.grompp_bound.ndx  test/lib/fe/binding/bound/index.ndx

    cpcc set-file fe:in.conf_bound test/lib/fe/binding/bound/conf.gro

    cpcc set fe:in.restraints_bound[0].resname ethanol2
    cpcc set fe:in.restraints_bound[0].pos.x 0
    cpcc set fe:in.restraints_bound[0].pos.y 0
    cpcc set fe:in.restraints_bound[0].pos.z 0
    cpcc set fe:in.restraints_bound[0].strength 1000

    # solvated state
    cpcc set-file fe:in.grompp_solv.top test/lib/fe/binding/solv/topol.top
    cpcc set-file fe:in.grompp_solv.include[0]  test/lib/fe/binding/solv/ana.itp
    cpcc set-file fe:in.grompp_solv.mdp test/lib/fe/binding/solv/grompp.mdp

    cpcc set-file fe:in.conf_solv test/lib/fe/binding/solv/conf.gro


    cpcc set fe:in.solvation_relaxation_time 1000
    cpcc set fe:in.binding_relaxation_time 2000
    cpcc set fe:in.precision 2

We finally commit the transact block.

.. code-block:: none

    cpcc commit

Copernicus will now start spawning simulations and put them on the queue.

Check the status of the project with ``cpcc status``. This will inform you on the state of the project
and how many jobs are in the queue and how many are currently running. If you want to see in detail
what jobs are in the queue use the command ``cpcc queue``. If no Copernicus worker is active no
simulations will start.

The simulations will continue until the estimated error of the calculations is equal to or lower than
the specified precision. If running only one worker this can take quite a while.

It is possible to check the output before the instance is finished. The following command will show you
the current output:

.. code-block:: none

    cpcc get fe.out

To see just the currently estimated free energy of binding run:

.. code-block:: none

    cpcc get fe.out.delta_f


