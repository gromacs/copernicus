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



import logging
import tempfile
import mmap
from cpc.network.com.server_connection import ServerConnectionError, \
    ServerConnection
from cpc.server.message.direct_message import DirectServerMessage
import cpc.util.log

from cpc.util.exception import CpcError
from cpc.network.server_request import ServerRequest
from cpc.util.conf.server_conf import  ServerConf
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.node import Nodes
from cpc.network.node import Node
from cpc.network.cache import Cache, NetworkTopologyCache
from cpc.util.worker_state_handler import WorkerStateHandler

log=logging.getLogger(__name__)

class ServerToServerMessageError(CpcError):
    def __init__(self, exc):
        self.str=exc.__str__()

class ServerToServerMessage(ServerConnection):
    """Network-related server-to-server messages.
       Only those messages related to network topology should go here, the
       rest should be in cpc.server.message.server_message."""



    def __init__(self, endNodeId):

        #TODO perhaps node should be input
        node = ServerConf().getNodes().get(endNodeId)

        ServerConnection.__init__(self,node,ServerConf())

        self.initialize(endNodeId)
        """Connect to a server opening a connection"""

    #@param String endNodeHostName
    #figures out what node to connect to in order to reach the end node
    def initialize(self,endNodeId):

        topology=self.getNetworkTopology()
        # this is myself:
        startNode = Node.getSelfNode(self.conf)

        self.endNode = topology.nodes.get(endNodeId)

        log.log(cpc.util.log.TRACE,"Finding route between %s(%s %s) and %s(%s "
                                   "%s"")"%(startNode.server_id,startNode.getHostname(),
                                    startNode.getServerSecurePort(),
                                    self.endNode.server_id,
                                    self.endNode.getHostname(),self.endNode.getServerSecurePort()))
        route = Nodes.findRoute(startNode, self.endNode,topology)

        self.hostNode = route[1]   #route[0] is the current host
        self.host = self.hostNode.getHostname()
        self.port = self.hostNode.getServerSecurePort()
        self.serverId = self.hostNode.getId()
        log.log(cpc.util.log.TRACE,"Server-to-server connecting to %s(%s:%s)"%
                (self.serverId,self.host,self.port))



    #NOTE might make sense to move this to requestHandler
    def delegateMessage(self,headers,messageStream):
        """Delegate the message to another server. Reads the message we get
           and requests a response from another client."""

        if not (headers.has_key('originating-server-id')):
            headers['originating-server-id'] = ServerConf().getServerId()
        length = long(headers['content-length'])
        tmp = tempfile.TemporaryFile('w+b')
        tmp.write(messageStream.read(length))
        tmp.seek(0)
        content = mmap.mmap(tmp.fileno(),0,mmap.ACCESS_READ)
        request = ServerRequest(headers,content)

        ret=self.sendRequest(request,method="PUT")

        #strip set-cookie from neighbouring server
        ret.headers.pop('set-cookie', None)
        # we can close the files associated with sending forward the request
        # and focus on the response (that we return)
        content.close()
        tmp.close()
        return ret

    @staticmethod
    def connectToSelf(headers):
        conf = ServerConf()
        if headers['server-id']==conf.getServerId():
            return True
        else:
            return False

    @staticmethod
    def getNetworkTopology(resetCache = False):
        """
        Used when a server wants to initiate a network topology request
        Tries to first get the topology from the cache

        resetCache:boolean calls network topology and resets it to cache
        """
        topology=False
        if (resetCache ==  False):
            topology = NetworkTopologyCache().get()
        if topology==False:
            topology = Nodes()
            topology = ServerToServerMessage.requestNetworkTopology(topology)
            NetworkTopologyCache().add(topology)

        return topology


    @staticmethod
    def requestNetworkTopology(topology,serverState=None):
        """
        Asks each neigbouring node for their network topology

        inputs:
            topology:Nodes The list of the topology generated so far
            serverState:ServerState
                if provided worker states are fetched.
                since this method is called by getNetworkTopology() which in turn
                is called from places where we do not pass (and don't want) the serverState
                we provide this option. Also it is not needed as the calling server always
                knows the most up to date state of its own workers.

        """
        conf = ServerConf()
        thisNode = Node.getSelfNode(conf)
        thisNode.setNodes(conf.getNodes())
        topology.addNode(thisNode)
        if serverState:
            thisNode.workerStates = WorkerStateHandler.getConnectedWorkers(serverState.getWorkerStates())

        for node in thisNode.getNodes().nodes.itervalues():
            if topology.exists(node.getId()) == False:
                #connect to correct node
                if node.isConnected():
                    try:
                        clnt = DirectServerMessage(node,conf=conf)
                        #send along the current topology
                        rawresp = clnt.networkTopology(topology)
                        processedResponse = ProcessedResponse(rawresp)
                        topology = processedResponse.getData()
                    except ServerConnectionError as e:
                        #we cannot connect to the node,
                        # and its marked as unreachable
                        #we must still add it to the topology
                        log.error("node %s unreachable when asking for network "
                                  "topology: error was %s"%(node.getId(),e.__str__()))
                        topology.addNode(node)

                #todo notify in topology that this node is not connected?
        return topology
