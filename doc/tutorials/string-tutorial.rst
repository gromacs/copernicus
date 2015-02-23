.. _stringtutorial:

***********************
String-of-swarms method
***********************

Introduction
^^^^^^^^^^^^

The string-of-swarms method is a method to iteratively refine an initial guess of a molecular system’s transition between two or more known configurations, in order to find the transition that minimizes the reversible work (i.e. free energy) done by the system during the transition.

This and related methods are useful especially when the timescale on which a transition takes place is much longer than the timescale you can typically simulate in a molecular dynamics simulation, thus making it improbable to directly observe a sought-for transition spontaneously.

The method as implemented in Copernicus was originally described by Pan and Roux 2009 [add citation] building on the work of Maragliano2006 [add citation] and they demonstrated it on the di-alanine peptide isomerization transition, which has been well studied and due to its low complexity but high energy barrier is a good example for illustrating the string methods.

The method describes the transition using the evolution of collective variables (CVs), which form a reduced dimensionality description of the configuration, along a one-dimensional string from a starting point to an ending point.

The CVs can theoretically consist of any mapping from the full system dimensionality, but one common choice and the one which is implemented in the Copernicus module is the peptide bond dihedral angles phi and psi for a user-selected set of protein residues. 

The method works by linearily interpolating the CVs between a given starting configuration and ending configuration guess for a selectable number of intermediate configurations, and then iteratively refining these configurations by starting a lot of unrestrained very short molecular dynamics simulations from the randomly perturbed intermediates and averaging their drift. Each iteration, the intermediates (and starting/ending points, if so desired) will move a bit down the free-energy gradient of the system’s energy landscape.

This would quickly result in all intermediates falling down onto each other into the nearest local minima, and to prevent this, each iteration ends with a so-called reparametrization step, where the CV euclidean distances between the configurations along the string are equalized. In essence, the intermediate configurations are adjusted to lie equidistant from each other along the string, thus forcing an even coverage along the transition even if the string in the initial guess crosses one or more high energy barriers.

When the intermediates stop moving, the string has converged to a lowest possible energy state. A caveat is that this might or might not represent the transition of lowest energy globally speaking, since there could be many. Depending on the complexity of the system, it might be necessary to try different initial guesses of string configurations therefore and see if they converge to the same transition or not.

Prerequisites
^^^^^^^^^^^^^

Make sure you have `GROMACS <http://www.gromacs.org>`_ installed before starting.

GROMACS needs to be installed on the system that the server is running on and all machines
where you will run workers.


Method protocol
^^^^^^^^^^^^^^^

The string module starts up by running the swarm Python script, which reads the initial string guess as input and other parameters, extracts the initial CVs and creates Copernicus functions for all iterations to be done.

Each iteration consists of the following interconnected Copernicus pipeline steps. The corresponding module Python script’s name is given in parantheses.

Restrained minimization (run_minimization)
------------------------------------------

The restraints are from the previous iterations’ updated string configuration (reparametrization step’s output) and by minimizing using them, the system will now hopefully be forced into the new state of CVs.

Restrained thermalization (thermalization)
------------------------------------------

After minimization the system will be at 0 temperature. This step brings up the system in temperature again using the selected thermostat.

Restrained equilibration (run_restrained)
-----------------------------------------

Runs the system for a while using the same parameters as the swarm step that follows, but for longer and with restraints enabled.

The output trajectory from the equilibration is written sparsely, with an interval selected so the written number of configurations equal the number of swarms to issue per string configuration below. We use the system’s natural evolution during the restrained step here to seed the swarms.

Swarm preparation (prep_swarms)
-------------------------------

The trajectories output in the previous step are converted to system configurations again, and sent to the next step.

Swarm (swarms)
--------------

Each configuration written for each equilibration trajectory above is used as starting point for a very short, unrestrained run. The runs belonging to the same string configuration are called a swarm, and the final configurations in each run in a swarm is sent as output to the next step.

CV extraction (get_cvs)
-----------------------

This step extracts the CVs from each swarm run configuration output. In the dihedral angles case for example, the peptide bond angles phi and psi are calculated for each protein residue selected to participate as CV.

Reparametrization (reparametrize)
---------------------------------

The CVs that resulted from each swarm run are read and the swarms averaged to get a proposed drift for each string configuration.

An iterative algorithm is then executed that adjusts the updated configurations so they keep their distances along the string, to avoid them all falling down into the minimas in the start and end of the string (or in between).

The result is that each configuration along the string can move orthogonally to the string but stay fixed longitudinally. The endpoints (if not fixed) can move in any direction though.


Demo running
^^^^^^^^^^^^

After starting a Copernicus server and making sure you can log into it using cpcc, in the copernicus folder run:

$ test/lib/swarms/swarm/runtest.sh

and it will setup a project called “test_singlechain” where the alanine dipeptide is setup to run to optimize its isomerization transition (described in the introduction above) for 80 iterations. If you just want to try if something works, edit runtest.sh first and in the Niterations setting near the bottom, change 80 to 5 or something.

To monitor the status of the run, you can do

.. code-block:: none

   $ cpcc status

to see if there are commands queued. If there are no more commands queued, you can proceed to extract the result by using these scripts, from within the test/lib/swarms/swarm folder:

.. code-block:: none

   $ mkdir res
   $ cd res
   $ ../get_result.sh
   < this will extract the resulting string configuration from the cpc-server through cpcc >
   $ cd ..
   $ ./vis_string.sh
   < this will make an .xtc from the final string transition and extract a table of the dihedrals along the string >



Parameter reference
^^^^^^^^^^^^^^^^^^^

General settings
----------------

* run:in.fixed_endpoints (integer 0 or 1)
Option that controls whether the starting and ending point in the string should be fixed or also updated just like all the other points. If you are not completely sure that your initial starting or ending point are actually the true local minimas for the force-field used, it is recommended to try running with the endpoints not fixed.

* run:in.Ninterpolants (integer)
The number of points in the string, including the starting and ending point.

Usually 10-50 points are enough, but depends on the system and free-energy landscape. The total computational time, storage space and network bandwidth increases linearly with the number of points, and it might be good to start with a smaller number of points to evaluate the method for the system and then increase.

Since every string point that can move involves minimizing and running a system simulation, the number of moving string points should usually be correlated with the number of workers and CPU cores attached to the Copernicus server so an even fraction of the total workload can be run in parallel at every time. 

For example, if you have 16 worker nodes attached it makes sense to use 16+2 (or 32+2) stringpoints in total if the endpoints don’t move, and 16 stringpoints in total if the endpoints move.

* run:in.Niterations (integer)
The number of string iterations to run. Common numbers are from 10 to hundreds, this depends a lot on the system size and energy landscape. Note that this is correlated with the swarm simulation step count described further below - doing more steps each swarm iteration results in less iterations needed to evolve the string the same distance, but it will be less accurate and might result in the string not converging as it might “step over” the true minima.

Each iteration requires a certain amount of memory and disk resources at the Copernicus server, and for large systems, it makes sense to restrict the number of iterations scheduled in each invocation for many reasons, including giving the ability to monitor the convergence better and see if bad things happen to the evolving string point systems.

* run:in.top (.top)
The Gromacs topology file to use for simulating the string point systems.

* run:in.tpr (.tpr)
A Gromacs run-file corresponding to the topology above, which is needed by various Gromacs helper tools invoked by the module, like g_rama. It is never run, and it doesn’t matter if it corresponds to a minimization or run simulation, as long as it comes from the same topology and base system.

* run:in.Nchains (integer)
Normally 1. For polymers, this should correspond to the number of separate peptide chains in the system topology. If you use polymers, and have separate .itp files for each subunit, you need to provide them in the in.include[] array.

* run:in.include (array of .itp, optional)
See above regarding polymers

* run:in.cv_index (.ndx)
The specification of the collective variables (CVs) that monitors and controls the string evolution. For the dihedral string case, this is the set of atoms with at least one atom listed per residue whose dihedral phi/psi angles should be used. It does not matter if the index contains one atom per residue or all atoms in the residues, and it accepts the output format used by the make_ndx Gromacs helper which might be useful for generating an index for large proteins.

There should be one single index group in the file only but the name of the group is irrelevant.

An example would be:

[ CA_&_Protein ]
   7   27   46   60   74   88   94  117  129 

which is generated by make_ndx, selecting the Ca atoms from each residue in the Protein.




String specification
--------------------

* run:in.start_conf (.gro)
The system configuration corresponding to the starting point of the string. This is also used by the dihedral CV mode as base configuration for all other string points.

* run:in.end_conf (.gro)
The system configuration corresponding to the ending point of the string. In the dihedral CV mode, this is unused (see start_conf above, which is used for all stringpoints).

* run:in.start_xvg (.xvg)
The dihedral CV values corresponding to the starting configuration of the string. Together with end_xvg, these are used by the module to linearily interpolate an initial estimate of all intermediary stringpoints. The starting point will stay locked to the start_xvg CV values during all iterations.

This file can either be created manually using known desired values for the CVs, or if a starting system configuration is available, g_rama can be invoked to generate an .xvg containing all dihedral phi/psi values for all peptide bonds in the system.

* run:in.end_xvg (.xvg)
The dihedral CV values corresponding to the ending configuration of the string. See start_xvg. The ending point will stay locked to the end_xvg CV values during all iterations.


Minimization stage settings
---------------------------

The minimization stage is run using the specification files below, with restraints on all CVs for the values generated by the interpolation (if this is the first iteration) or the values generated by the previous iteration’s output. In both cases, the system will be forced a the new state by the restraints as opposed to simply staying locked still as is usually done in the minimization step in a simulation. This can pose a problem if the structure is complicated and the new CV values try to change it a lot. If there are issues, tweaks to the minimization grompp input (described below) are needed to improve minimization performance, as well as possibly tweaks to the following stages as well.

* run:in.minim_grompp.mdp (.mdp)
The Gromacs configuration file to use for minimizing your system. Use settings that you know are capable of producing a good energy minimization for the system in general.

* run:in.minim_grompp.top (.top)
The Gromacs topology to use for minimization (usually the same as the other steps’ topologies)

* run:in.minim_grompp.ndx (.ndx, optional)
A Gromacs atom index file, if needed for simulations (for example if you specify atom groups in the .mdp which are specified in the .ndx file)

* run:in.em_tolerance (float)
Minimization tolerance to set during the minimization stage.

* run:in.minim_restrforce (float, optional)
The restraint k-value to use during the minimization stage for the CVs. It should be fairly large (500.0-4000.0 kJ/mol/rad^2 for the dihedral case for example) but ultimately depends on the protein and the amount of distortions of the starting string compare with the start_conf, or the amount of string point evolution per iteration. 

If no value is given, 500.0 is used.


Thermalization stage settings
-----------------------------

* run:in.therm_grompp.mdp (.mdp)
The Gromacs configuration file to use for thermalizing your system after minimization is done (system will start at 0 K). Use normal settings that work for running your system in general, including a proper thermostat. It is not recommended to use pressure coupling here as the temperature is not stabilized yet. 

The step size should be set very conservatively at 0.5 fs for example, to help with structures that are difficult to minimize into their new configurations.

The number of steps required to thermalize depends on the step size and the thermostat time coefficient, but in general 1000-2000 steps or so is enough for a step size of 0.5 fs and a tau of 1.0 ps.

* run:in.therm_grompp.top (.top)
The Gromacs topology to use for thermalization (usually the same as the other steps’ topologies)

* run:in.therm_grompp.ndx (.ndx, optional)
A Gromacs atom index file, if needed for simulations (for example if you specify atom groups in the .mdp which are specified in the .ndx file)

* run:in.therm_restrforce (float, optional)
The restraint k-value to use during the thermalization stage for the CVs. See the discussion for minim_restrforce above.

If no value is given, 750.0 is used.

Equilibration and Swarm stage settings
--------------------------------------

* run:in.equil_grompp.mdp (.mdp)
The Gromacs configuration file to use for running your system normally. Use settings that work for running your system in general, including a proper thermostat. Pressure coupling may be used for solvated systems.

This will be used for the equilibration stage together with restraints on all CVs, as well as on the swarm stage without restraints.

Note:The number of simulation steps will be set automatically by the module to use this configuration file for both equilibration and swarms.

* run:in.equil_grompp.top (.top)
The Gromacs topology to use for equilibration (usually the same as the other steps’ topologies)

* run:in.equil_grompp.ndx (.ndx, optional)
A Gromacs atom index file, if needed for simulations (for example if you specify atom groups in the .mdp which are specified in the .ndx file)

* run:in.equil_restrforce (float, optional)
The restraint k-value to use during the equilibration stage for the CVs. See the discussion for minim_restrforce above.

If no value is given, 750.0 is used.

* run:in.restrained_steps (integer)
The number of simulation steps to equilibrate for using the equil_grompp.mdp settings.

* run:in.swarm_steps (integer)
The number of simulation steps used for the swarm run. This should be very short, often between 15-300 steps depending on the system size. 

* run:in.Nswarms (integer)
The number of swarm simulations to issue for each string point during the swarm stage. They will be started from a selection of configurations extracted from the equilibration stage and their ending coordinates will be averaged to get the average drift of the string point. The averaging is needed to counteract the randomness induced by simulating a system at a non-zero temperature.

More swarm simulations per point is always better to average the thermal fluctuations, but require more simulation time, storage space and network bandwidth, which might be a concern if the system is very big. 

In general, start with small values (10-20) to verify the method and string convergence, and if the stringpoints evolve erratically or with too much noise, increase the number of swarms.

