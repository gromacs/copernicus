.. |br| raw:: html

   <br />

Welcome to Copernicus's documentation!
======================================

Contents:

.. toctree::
   :maxdepth: 2

   getting-started.rst
   network/index.rst
   tutorials/index.rst
   developers/index.rst


Introduction
============

Copernicus is a peer to peer distributed computing platform designed for high level
parallelization of statistical problems.

Many computational problems are growing bigger and require more compute resources.
Bigger problems and more resources put other requirements such as

* effective distribution of computational work
* fault tolerance of computation
* reproducability and traceability of results
* Automatic postprocessing of data
* Automatic result consolidation

Copernicus is a platform aimed at making distributed computing easy to use. Out of the box it provides.

* Easy and effective consolidation of heterogeneous compute resources
* Automatic resource matching of jobs against compute resources
* Automatic fault tolerance of distributed work
* A workflow execution engine to easily define a problem and trace its results live
* Flexible plugin facilites allowing programs to be integrated to the workflow execution engine


This section will cover how copernicus works and what its possibilites are.
The subsequent sections will in detail cover how to use the platform.

------------------------------
The architecture of Copernicus
------------------------------

Copernicus consists of four components; the Server, the Worker,the Client and the
Workflow execution engine. The server is the backbone of the platform and manages
projects, generates jobs (computational work units) and matches these to the best
computational resource. Workers are programs residing on your computational resources.
They are responsible for executing jobs and returning the results back to the server.
Workers can reside on any type of machine, desktops, laptops, cloud instances or a
cluster environment. The client is the tool where you setup your project and monitor it.
Actually, nothing is running on the client ever. It only sends commands to the server.
This way you can run the client on your laptop, startup a project, close your laptop,
open it up some time later and see that your project has progressed.
All communication between these three components is encrypted.
And as you will see later all communication has to be authorized.

Copernicus is designed in a way so that any individual can set it up,
consolidate any type of resource available and put them to use. There is no central
server that you will communicate to. You have full control of everything.

The workflow execution engine is what allows you to define your problem in a very easy way.
Think of it as a flowchart where you define what you want to do and connect different important blocks.
The workflow resides in the server and is a key component in every copernicus project.
By just providing a workflow with input the server will automatically generate jobs
and handle the execution of those. This way you will never have to focus on what to run where.
Instead you can just focus on defining your problem.

The workflow gives also gives you the possibility to trace your work progress and
look at intermediate results. You will also be a able to alter inputs in the middle
of the run of a project in case things have gone wrong or if you want to test another approach.

Workflow components can actually be any type program. And with the plugin utilites
in copernicus you can define these programs as workflow items, also known as functions.


-------
Authors
-------

Head authors & project leaders
-------------------------------
Sander Pronk |br|
Iman Pouya (Royal Institute of Technology, Sweden) |br|
Peter Kasson (University of Virginia, USA) |br|
Erik Lindahl (Royal Institute of Technology, Sweden)


Other current developers
-------------------------
Magnus Lundborg (Royal Institute of Technology, Sweden) |br|
Björn Wesen (Royal Institute of Technology,Sweden)

Previous developers and contributors
------------------------------------
Patrik Falkman |br|
Grant Rotskoff ( University of California, Berkley, US )
