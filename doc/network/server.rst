.. _server:

.. |br| raw:: html

   <br />

******
Server
******

Servers are what manages your copernicus project. They are responsible for
generating jobs and the monitoring of these. When you work with a project you
use the ``cpcc`` command line tool to send messages to the server.
The server will process this commands and setup your project and generate jobs for it.

the command line program for the server is called ``cpc-server``


Where to run the server
=======================

Since the server is responsible for running all of your project it is advisable
to deploy it on a machine that is up and running all the time.
For example running the server on your laptop would not be a good idea for many reasons\:

* You move your laptop around : When moving your laptop between location your machine gets assigned different ip addresses. Workers connected to this server would not be able to communicate with the server once the address changes.

* Laptops are not on all the time: You close the lid on you laptop, it runs out of batteries ….

Fault tolerance of projects
===========================

The server is very fault tolerant and handles your projects with great care.
It regularly saves the state of each project. In case a server would shutdown or
crash due to software or hardware failure you can simply restart the server and
it will recover to the previous state. |br|
Jobs that are already sent out workers are also fault tolerant. The server can
handle cases where the worker goes down or if the server itself goes down.
This is done by the server heartbeat monitor. Whenever a server has sent a job
to a worker it expects a small heartbeat message from the worker once in a while
(default is every 2 minutes however
this can be configured). If the server doesn’t receive a heartbeat message it will
mark that job as failed and put it back on the queue. |br|
The same procedure is actually used when a server goes down. Whenever it starts
again it will go through its list of jobs sent out(referred to as heartbeat items).
And see which ones has gone past the heartbeat interval time. These jobs that have
timed out will then be put back on the queue.

Although the server is fault tolerant make sure to backup your project data to a
second disk regularly. The server will not be able to recover a project from disk failures.

Creating a Copernicus network with many servers
===============================================

* You want to share worker resources: If your workers are not being utilized at 100% you can share your workers by connecting to other copernicus servers. Whenever your server is out of jobs it will ask its neighbouring servers for jobs. More on this in the section worker delegation.
* You are running too many projects for one server to handle: If you have too many projects for one server to handle you can offload it by running a second server on another machine. You can then connect the second server to the first and still share resources with worker delegation.
* Your workers are running on an internal network while the server is not. In cluster environments the compute nodes can only communicate with the head nodes so you would need a server running on the head node. However as soon as you start running projects the server will consume a bit of resources on the head node which is not advisable. A better setup is to run one server on the head node and connect it to a project server outside the cluster environment. The server on the head node will only be managing connections to the workers and pass these on to the project server.


Worker delegation
^^^^^^^^^^^^^^^^^
The concept of worker delegation allows servers to share work resources between each other.
Whenever servers are connected worker delegation is enabled automatically.
The server that the workers are connected to will always have the first priority and
if there is work in its queue it will utilize its workers.
However if there is no work in the queue it will ask its connected servers for work.
This is done in a proioritized order. The order of priority can be seen with the
command ``cpcc list-nodes`` . Servers can be reprioritized with ``cpcc node-pri``.

Connecting servers
^^^^^^^^^^^^^^^^^^

To connect two copernicus servers you need to send a connection request which in
turn has to be approved by the other side.

A connection request can be sent to a server using the command
``cpcc connect-node HOSTNAME``

.. code-block:: none

     >cpcc connect-server server2.mydomain.com
    Connection request sent to server2.mydomain.com 14807

By default a request is sent using standard copernicus unsecure port 14807.
If the destination server has changed the unsecure port number you will need to
specify it.

.. code-block:: none

    cpcc connect-server server2.mydomain.com 15555


After sending a connection request you can list it with ``cpcc connected-servers``

.. code-block:: none

    >cpcc connected-servers
    Sent connection requests
    Hostname                     Port       Server Id
    server2.mydomain.com         14807      b96add9c-aff5-11e2-953a-00259018db3a


Received connection requests needs approval before a secure communication can be
established between 2 servers. To approve a connection request you use the
``cpcc trust SERVER_ID command``. Only servers that have sent connection request
to your server can be trusted. To see which servers that have requested to connect
you can use ``cpcc connected-servers``

.. code-block:: none

    >cpcc connected-servers
    Received connection requests
    Hostname                        Port       Server Id
    server1.mydomain.com            14807      dc75c998-acf1-11e2-bfe2-00259018db3a

The list above specifies that we have one incoming connection request.
The text string under the column “Server Id” is what we need to specify in the
``cpcc trust`` command.


.. code-block:: none

    >cpcc trust dc75c998-acf1-11e2-bfe2-00259018db3a

    Following nodes are now trusted:
    Hostname                        Port       Server Id
    server1.mydomain.com            14807      dc75c998-acf1-11e2-bfe2-00259018db3a

after calling ``cpcc trust`` your server will communicate with the requesting
server and establish a secure connection. To list the connected connected nodes
simply use ``cpcc connected-servers``

.. code-block:: none

    >cpcc connected-servers
    Connected nodes:
    Priority   Hostname                        Port       Server Id
    0          server1.mydomain.com            14807      dc75c998-acf1-11e2-bfe2-00259018db3a

If you change the hostname or the ports of one server it will upon restart
communicate to its connected servers and notify them on these changes.


Connecting to a server that is behind a firewall.
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If one of the servers is behind a firewall, it is not possible to send a connection
request directly. The workaround for this is to first create an ssh tunnel to
the server behind the firewall. The procedure will then be.

1. Create an ssh tunnel to the firewalled server

.. code-block:: none

    ssh -f server_behind_firewall -L 13807:server_behind_firewall:13807 -L 14807:server_behind_firewall:14807 -N


the syntax 13807:server_behind_firewall:13807 means “anything from localhost port 13807 should be sent to server_behind_firewall  port 13807″
The port numbers 13807 and 14807 are the standard copernicus server ports. in case you have changed these setting please make sure that those port numbers are provided in the tunnelling command.


2. Send a connection request using the tunnel port.

.. code-block:: none

    cpcc connect-server localhost 14807

3. Approve the connection request

.. code-block:: none

    cpcc trust SERVER_ID

where ``SERVER_ID`` is the id of the server that sent the connection request.
you can look it up with the command ``cpcc connected-servers``.
When a connection is established you no longer need the ssh tunnel.


User management
^^^^^^^^^^^^^^^

Copernicus has support for multiple users with access roles.
Regular users have either full access or no access to a project.
Super users (like cpc-admin) have access to all projects and may add other users using:

.. code-block:: none

    cpcc add-user username

A user may grant another user access to its current project by issuing

.. code-block:: none

    cpcc grant-access username



