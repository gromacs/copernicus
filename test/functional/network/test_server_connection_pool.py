# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest
from test.functional.utils import *

class ServerToServerConnectionPoolTest(unittest.TestCase):
    """
    These tests acts as regression tests for connection establishment between
     servers. They mostly test the flow and make sure that certain events
     occur. However this is done by listening to log output.
    """


    def setUp(self):
        stopAndFlush()
        self.servers = ['test_server_1','test_server_2']
        self.clientSecurePorts,self.serverSecurePorts = createServers(self.servers)

        self.establishConnection()

        #add servers for cpcc, we need this when we call stop-server,
        # otherwise we use the connection bundle

        for i in range(0,len(self.servers)):
            server = self.servers[i]
            port = self.clientSecurePorts[i]
            run_client_command("add-server -n %s localhost %s"%(server,port))

        self.server2Nodes = getConnectedNodesFromConf(self.servers[1]).nodes
        self.server1Node =  self.server2Nodes.values()[0]
        self.server1Id = self.server1Node.getId()

        self.server1Nodes = getConnectedNodesFromConf(self.servers[0]).nodes
        self.server2Node =  self.server1Nodes.values()[0]
        self.server2Id = self.server1Nodes.values()[0].getId()

        self.server1LogChecker = ServerLogChecker(name=self.servers[0])
        self.server1LogChecker.startThread()

        self.server2LogChecker = ServerLogChecker(name=self.servers[1])
        self.server2LogChecker.startThread()

        # let's ensure both servers a connected before running tests on the
        # connection validility.
        self.server1LogChecker.waitForOutput("sent keep alive to 1 nodes")

    def tearDown(self):
        self.server1LogChecker.shutdownGracefully()
        self.server2LogChecker.shutdownGracefully()

        for server in self.servers:
            stop_server(server)


    def establishConnection(self):
        #send a 2 connect requests from Server1 to Server2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)

        #Server2 accepts the request
        run_client_command("trust -all",name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)


    def TestServerCommunicationUsesEstablishedConnection(self):
        """ Test server communication is using established connection"""

        #Server1 pings Server2

        run_client_command("ping %s"%self.server2Id,name=self.servers[0],
            expectstdout="OK",useCnx=True)

        #Ensure Server1 is using socket from connectionpool when connecting
        # to Server2
        self.server1LogChecker.waitForOutput("Got a connection from pool for "
                                        "host:%s:%s"%(self.server2Node.getHostname(),
                                                      self.server2Node.getServerSecurePort()))

        #Ensure connection is put back in pool
        self.server1LogChecker.waitForOutput("put back connection in pool for"
                                             " host:%s:%s"\
                                             %(self.server2Node.getHostname(),
                                               self.server2Node.getServerSecurePort()))


    def testConnectionsCreatedUponWakeup(self):
        """
        Test that at least one communication link exists after wakeup.
        This also reflects the case where one server cannot establish a link
        but the other can this ensuring ongoing communication
        """

        #shutdown all servers
        ensure_no_running_servers_or_workers()
        time.sleep(3)
        start_server(self.servers[1])
        start_server(self.servers[0])

        #---STEP1: Server1 establishes an inbound connection


        #Server1 should first establish inbound connections

        self.server1LogChecker.waitForOutput("Established inbound "
                                             "connections to server "
                                             "%s"%self.server2Node.toString())

        #Server2 to should have processed the persistent connection request
        # and saved the socket to its connection pool
        self.server2LogChecker.waitForOutput("Got request to persist outgoing "
                                        "connections")


        self.server2LogChecker.waitForOutput("put back connection in pool for"
                                             " host:%s:%s"\
                                             %(self.server1Node.getHostname(),
                                               self.server1Node.getServerSecurePort()))


        #---STEP2: Server1 establishes an outbound connection

         #Server1 establishes an outbound connection
        self.server1LogChecker.waitForOutput("put back connection in pool for"
                                             " host:%s:%s"\
                                             %(self.server2Node.getHostname(),
                                               self.server2Node.getServerSecurePort()))


    def testKeepAlive(self):
        """
        Ensure connections are kept alive after they are established
        """
        #reduce the send keep alive timer
        ensure_no_running_servers_or_workers()

        start_server(self.servers[1])
        start_server(self.servers[0])


        #verify keep alive sent
        self.server1LogChecker.waitForOutput("keepAlive sent to "\
                                             "%s"%self.server2Node.toString())


        #verify keep is not only sent once
        self.server1LogChecker.waitForOutput("keepAlive sent to "\
                                             "%s"%self.server2Node.toString())



    def testOneServerDownConnectionEstablishedAfterWakeup(self):
        """
        Ensure communications reestablished when server stops and starts again
        """

        #Stopping Server2
        login_client()
        run_client_command("stop-server")

        #give it some time to shutdown
        time.sleep(3)


        #Server1 should note that Server2 is down when sending keep alive
        #and should close this socket.

        start_server(self.servers[1])

        #Server2 first send connections for Server1 to write to
        self.server1LogChecker.waitForOutput("Got request to persist outgoing "
                                             "connections")



        self.server1LogChecker.waitForOutput("put back connection in pool for"
                                             " host:%s:%s"\
                                             %(self.server2Node.getHostname(),
                                               self.server2Node
                                               .getServerSecurePort()))



    def testStatusCommandShowsWhenServerIsDown(self):
        """
        Ensure that the cpcc status command is notyfing when a server is down
        """

        #Stopping Server2
        login_client()
        run_client_command("stop-server")

        #give it some time to shutdown
        time.sleep(3)


        #Server1 should note that Server2 is down when sending keep alive
        #and should close this socket.

        #cpcc s should notify that the server is down
        run_client_command("use-server test_server_1")
        login_client()
        run_client_command("status",
                           expectstdout=".*There is 1 server that currently cannot be reached.*")

        start_server(self.servers[1])

        #Server2 first send connections for Server1 to write to
        time.sleep(3) #give some time for connectios to be established

        run_client_command("status",
                           doNotExpectstdout=".*There is 1 server that currently cannot be reached.*")

    def testOneServerDownOtherServerTriesToEstablishConnection(self):
        """
        Test that we can establish a connection even if one server goes down
        and cannot establish a connection upon wakeup.
        I.e we do not have bidirectional communication
        """

        #Stopping Server2
        login_client()

        run_client_command("stop-server")


        #Server1 notices that Server2 is down when sending a keep alive
        self.server1LogChecker.waitForOutput("Connection to %s is broken"%self.server2Node.toString())

        #Ensure that Server1 tries to restablish the connection periodacally
        self.server1LogChecker.waitForOutput("Tried to reestablish a "
                                             "connection"
                                             " to %s but failed "%self.server2Node.toString())



        #mess with the connection params so that server2 cannot establish a
        # connection

        server2Conf = getConf(self.servers[1])
        server2Conf['nodes'].nodes.get(self.server1Id).setServerSecurePort(
            111111)

        writeConf(self.servers[1],server2Conf)


        #Server2 wakes up
        start_server(self.servers[1])


        #connections should be reestablished by Server1
        self.server1LogChecker.waitForOutput( "Established inbound "
                                              "connections to server "
                                              "%s" % self.server2Node.toString())

        self.server1LogChecker.waitForOutput("Established outgoing "
                                             "connections to server "
                                             "%s"%self.server2Node.toString())
