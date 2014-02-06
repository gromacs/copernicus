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
import json
from cpc.util import json_serializer
import time

from test.functional.utils import *
import unittest

class ServerToServerConnectionTest(unittest.TestCase):
    def setUp(self):
        stopAndFlush()


    def tearDown(self):
        for server in self.servers:
            stop_server(server)


    def TestSendServerConnectionRequest(self):
        """
        Create 2 servers and tries to send a connection request from server
        1 to server 2
        """
        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a connect request from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],expectstdout="Connection request sent "
                                              "to %s"%serverAndPort,useCnx=True)



        """ Expect to see the address of the host in the list,
        we only have a hostname of the remote host so thats whah we display
        below  """
        run_client_command("connected-servers",name=self.servers[0],
            expectstdout="%s (\s)* %s"%('localhost',
                                         self.clientSecurePorts[1]),useCnx=True)

        """assert that server 2 has a connection request from server 2 in its
         networks list here we do expect to see the fqdn of the host since
         since we actually got it"""
        run_client_command("connected-servers",name=self.servers[1],
            expectstdout="%s (\s)* %s .*"%('localhost',
                                        self.clientSecurePorts[0]),useCnx=True)


    def TestSendServerConnectionRequestToNonExistingHost(self):
        "Tries to send a connection request to a non existing server"
        self.servers = ['test_server_1']
        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #startup 1 server
        #send a connect request to a nonexisting host
        nonExistingHost = "smurf.cpc.se"
        run_client_command("connect-server %s"%nonExistingHost,
            name=self.servers[0],expectstderr="[Errno 8]",
            returnZero=False,useCnx=True)


    def TestSendServerConnectionRequestToWrongPort(self):
        """Start 2 servers but send a connection request to a non functional
        port, make sure we get an error message back"""

        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a connect request from server 1 to server 2
        wrongPort = 9999
        serverAndPort = "%s %s"%("localhost",wrongPort)
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],expectstderr="[Errno 8]",
            returnZero=False,useCnx=True)


    def TestSendAndAcceptConnectionRequest(self):
        """ Start 2 servers, send connection request from Server 1 to Server2.
            Server2 accepts the connection request
        """

        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)


    #send a connect request from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)
        confDict = getConf(self.servers[1])
        serverToTrust =  confDict['node_connect_requests'].nodes.keys()[0]

        #server 2 accepts the request
        run_client_command("trust %s"%serverToTrust,name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)

        #check network topologies of server 2
        run_client_command("connected-servers",name=self.servers[1],
            expectstdout="0(\s)*localhost(\s)*13807\s*.*",useCnx=True)

        #read the conf json, get the connected nodes assert we only have one
        nodes = getConnectedNodesFromConf(self.servers[1])
        nodeIds = nodes.nodes.keys()
        assert len(nodeIds) == 1


        #extract the serverid
        #do a test request from server 2 to server 1
        run_client_command("ping %s"%nodeIds[0],name=self.servers[1],
            expectstdout="OK",useCnx=True)

        #check network topologies of server 1
        run_client_command("connected-servers",name=self.servers[0],
            expectstdout="0(\s)*localhost(\s)*13808\s*.*",useCnx=True)

        #do a test request from server 1 to server 2
        nodes = getConnectedNodesFromConf(self.servers[0])
        nodeIds = nodes.nodes.keys()
        assert len(nodeIds) == 1
        run_client_command("ping %s"%nodeIds[0],name=self.servers[0],
            expectstdout="OK",useCnx=True)


    def TestSendAndRevokeConnectionRequest(self):
        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a connect request from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)

        confDict = getConf(self.servers[1])
        serverIdToRevoke = confDict['node_connect_requests'].nodes.keys()[0]


        run_client_command("revoke %s"%serverIdToRevoke,name=self.servers[1],
            expectstdout="Server %s is now revoked"%serverIdToRevoke,useCnx=True)

        #assert that there is no pending requests on server2
        run_client_command("connected-servers",name=self.servers[1],
            expectstdout="",useCnx=True)


        #server 1 shuts down. and wakes up, pings server2 to see the status
        # of the request server2 responds with a revoked message
        #assert that there is no pending requests on server1

        stop_server(self.servers[0])
        start_server(self.servers[0])

        # ping to server2 should have been done and now server 1 should not
        # have an outgoing connection request in its list
        run_client_command("connected-servers",name=self.servers[0],
            expectstdout="",useCnx=True)



    def TestRevokeAlreadyEstablishedConnection(self):
        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)


    #send a 2 connect requests from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)

        #server 2 accepts the request
        run_client_command("trust -all",name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)


        #server 2 revokes
        confDict = getConf(self.servers[1])
        serverIdToRevoke = confDict['nodes'].nodes.keys()[0]


        run_client_command("revoke %s"%serverIdToRevoke,name=self.servers[1],
        expectstdout="Server %s is now revoked"%serverIdToRevoke,useCnx=True)


        #TODO ensure the public key is removed in the keychain



    def TestSendRequestToAlreadyTrustedServer(self):
        #should just give back an error message noting that the server is
        # already trusted

        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a 2 connect requests from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)


        #server 2 accepts the request
        run_client_command("trust -all",name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)


        #resend a connect request from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],expectstderr="localhost is already trusted",
            useCnx=True,returnZero=False)



    def TestSendServerConnectionToSameHostTwice(self):
        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)


    #send a 2 connect requests from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)

        #send connect requests twice from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,name=self.servers[0],useCnx=True)

        #ensure that we only have one connect request in the config list
        confDict = getConf(self.servers[0])
        assert len(confDict['sent_node_connect_requests'].nodes.keys()) == 1

        confDict = getConf(self.servers[1])
        assert len(confDict['node_connect_requests'].nodes.keys()) == 1

    def Test2ConnectedServersOneChangesConnectionParameters(self):
        #startup 2 servers
        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a connect requests from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)

        #server 2 accepts the request
        run_client_command("trust -all",name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)

        #CHANGE CONNECTION PARAMS OF SERVER 1
        ensure_no_running_servers_or_workers()
        configureServerPorts(self.servers[0],15008,15009)

        start_server(self.servers[1])
        #when server 1 starts it should send connection params to server 2
        start_server(self.servers[0])

        #give some time for the parameters to update
        time.sleep(3)
        # get the server id of server 1
        confDict = getConf(self.servers[1])
        server1Id = confDict['nodes'].nodes.keys()[0]

        #server 2 should still be able o ping server 1
        run_client_command("ping %s"%server1Id,name=self.servers[1],
            expectstdout="OK",useCnx=True)



    def testConnectionsEstablishedAfterTrust(self):
        """
        Connections are established after servers has trusted each other
        """

        self.servers = ['test_server_1','test_server_2']

        self.clientSecurePorts,self.serverSecurePorts = createServers(
            self.servers)

        #send a connect requests from server 1 to server 2
        serverAndPort = "%s %s"%("localhost",self.clientSecurePorts[1])
        run_client_command("connect-server %s"%serverAndPort,
            name=self.servers[0],useCnx=True)


        #start the logcheckers before we do trust

        self.server1LogChecker = ServerLogChecker(name=self.servers[0])
        self.server1LogChecker.startThread()

        self.server2LogChecker = ServerLogChecker(name=self.servers[1])
        self.server2LogChecker.startThread()


        #server 2 accepts the request
        run_client_command("trust -all",name=self.servers[1],
            expectstdout="localhost(\s)*14807\s*.*",useCnx=True)


        self.server2Nodes = getConnectedNodesFromConf(self.servers[1]).nodes
        self.server1Node =  self.server2Nodes.values()[0]

        self.server1Nodes = getConnectedNodesFromConf(self.servers[0]).nodes
        self.server2Node =  self.server1Nodes.values()[0]


        #server 2 should have sent a request to establish inbound connections
        self.server2LogChecker.waitForOutput("Established inbound "
                                             "connections to server "
                                             "%s"%self.server1Node.toString())

        self.server2LogChecker.shutdownGracefully()

        #server 2 should have sent a request to establish outbound connections
        self.server2LogChecker.waitForOutput("Established outgoing "
                                             "connections to server "
                                             "%s"%self.server1Node.toString())
