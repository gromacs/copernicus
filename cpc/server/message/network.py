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


import copy
import logging
from cpc.server.message.untrusted_server_message import RawServerMessage
from cpc.server.state import server_state

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from server_command import ServerCommand
from cpc.util.conf.server_conf import ServerConf
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.node import Node
from cpc.network.node import Nodes
from cpc.util import json_serializer
from cpc.util.openssl import OpenSSL
from cpc.network.cache import Cache, NetworkTopologyCache
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.network.broadcast_message import BroadcastMessage

from cpc.network.node_connect_request import NodeConnectRequest
import json

log=logging.getLogger(__name__)


#FIXME not sure if this one is used
class SCNetworkTopologyClient(ServerCommand):
    """
    when a client requests a network topology
    """
    def __init__(self):
        ServerCommand.__init__(self, "network-topology-client")

    def run(self, serverState, request, response):
        """
        When a client requests a network topology.
        ServerToServerMessage.getNetworkTopology() tries to first get it from
         the cache, if it cant find it there it starts generating a topology

        """
        topology = ServerToServerMessage.getNetworkTopology()

        response.add("", topology)
        log.info("Returned network topology size %d" % topology.size())



class SCNetworkTopology(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "network-topology")

    def run(self, serverState, request, response):
        """
        Used when a server wants to generate a network topology
        """
        topology = Nodes()
        if request.hasParam('topology'):
            topology = json.loads(request.getParam('topology'),
                object_hook=json_serializer.fromJson)

        topology = ServerToServerMessage.requestNetworkTopology(topology)

        response.add("", topology)
        log.info("Returned network topology size %d" % topology.size())


class SCNetworkTopologyUpdate(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "network-topology-update")

    def run(self, serverState, request, response):
        NetworkTopologyCache().remove()
        topology = json.loads(request.getParam('topology'),
            object_hook=json_serializer.fromJson)
        NetworkTopologyCache().add(topology)
        response.add("Updated network topology")
        log.info("Update network topology done")


class SCConnectionParamUpdate(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "persist-connection")

    def run(self, serverState, request, response):
        #get the connection params for this node
        newParams =json.loads(request.getParam("connectionParams"))
        conf = ServerConf()
        nodes = conf.getNodes()
        if nodes.exists(newParams['serverId']):
            node = nodes.get(newParams['serverId'])
            node.setHostname(newParams['hostname'])
            node.setServerSecurePort(newParams['server_secure_port'])
            node.setClientSecurePort(newParams['client_secure_port'])
            node.setQualifiedName(newParams['fqdn'])

            #Needed so that we write changes to conf file
            conf.removeNode(node.server_id)
            conf.addNode(node)
            response.add("Updated connection paramters")
            log.info("Updated connection params for %s"%node.toString())

        else:
            response.add("Requested update for node %s but this node  " \
                              "is not a neigbouring node "%newParams[
                                                           'serverId'],
                                                           status="ERROR")
            log.error("Failed updating connection params for %s"%newParams
            .serverId)


class ScAddNode(ServerCommand):

    """Sends a node connection request to a server
       this message is sent from a client"""
    def __init__(self):
        ServerCommand.__init__(self, "connnect-server")

    def run(self, serverState, request, response):
        conf = ServerConf()
        host = request.getParam('host')

        client_secure_port = request.getParam('client_secure_port')
        result = dict()
        #do we have a server with this hostname or fqdn?
        connectedNodes = conf.getNodes()

        if (connectedNodes.hostnameOrFQDNExists(host) == False):
            serv = RawServerMessage(host, client_secure_port)
            resp = ProcessedResponse(serv.sendAddNodeRequest(host))

            if resp.isOK():
                result = resp.getData()
                nodeConnectRequest = NodeConnectRequest(result['serverId'],
                    int(client_secure_port),None,None,result['fqdn'],host)

                conf.addSentNodeConnectRequest(nodeConnectRequest)
                result['nodeConnectRequest']=nodeConnectRequest
                log.info("Added node %s" % host)
                response.add('', result)
            else:
                response.add("Remote server said: %s"%resp.getMessage(),
                            status="ERROR")

        else:
            errorMessage = "%s is already trusted" % host
            response.add(errorMessage, status="ERROR")
            log.info(errorMessage)

        

class ScAddNodeRequest(ServerCommand):
    """ Receives a connnection request from a server """


    def __init__(self):
        ServerCommand.__init__(self, "connect-server-request")

    def run(self, serverState, request, response):
        nodeConnectRequest = json.loads(request.getParam('nodeConnectRequest'),
            object_hook=json_serializer.fromJson)

        conf = ServerConf()
        conf.addNodeConnectRequest(nodeConnectRequest)
        result =dict()
        result['serverId'] = conf.getServerId()
        result['fqdn'] = conf.getFqdn()
        response.add("", result)
        log.info("Handled add node request")

class ScRevokeNode(ServerCommand):
    """ Receives a connnection request from a server """


    def __init__(self):
        ServerCommand.__init__(self, "revoke-node")

    def run(self, serverState, request, response):

        serverId = request.getParam('serverId')
        conf = ServerConf()
        revokedNode = None
        #it can either be an already established connection
        if serverId in conf.getNodes().nodes:
            try:
                revokedNode = conf.getNodes().get(serverId)
                conf.removeNode(serverId)
                #TODO also remove the key!
            except KeyError:
                pass

        #or an incoming request
        elif serverId in conf.getNodeConnectRequests().nodes:
            try:
                revokedNode = conf.getNodeConnectRequests().get(serverId)
                conf.removeNodeConnectRequest(serverId)
            except KeyError:
                pass

        #or an outgoing request
        elif serverId in conf.getSentNodeConnectRequests().nodes:
            try:
                revokedNode = conf.getSentNodeConnectRequests().get(serverId)
                conf.removeSentNodeConnectRequest(serverId)
            except KeyError:
                pass

        if revokedNode!=None:
            conf.addRevokedNode(revokedNode)
            log.info("Revoked node %s"%serverId)
            response.add("Server %s is now revoked"%serverId)
        else:
            response.add("Server %s was not revoked since it did not have"\
                      " an existing connection"%serverId, status="ERROR")
            log.info("Failed Revoking node")



#message to send when a node has beeen accepted
class ScGrantNodeConnection(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "grant-node-connection")

    def run(self, serverState, request, response):
        serverId = request.getParam('serverId')
        if self.grant(serverId):
            ret = {}
            connectedNode = ServerConf().getNodes().get(serverId)
            ret['connected'] = [connectedNode]
            ScGrantNodeConnection.establishConnectionsAndBroadcastTopology(
                serverState,[connectedNode])
            response.add("", ret)

            log.info("Granted node connection for %s" % (serverId))

        else:
            response.add('Node has not requested to connect')
            log.info("Did not grant node connection for %s" % (serverId))

    @staticmethod
    def grant(key): #key is server-id
        conf = ServerConf()
        nodeConnectRequests = conf.getNodeConnectRequests()

        if nodeConnectRequests.exists(key):
            nodeToAdd = nodeConnectRequests.get(key) #this returns a nodeConnectRequest object

            serv = RawServerMessage(nodeToAdd.getHostname(),
                nodeToAdd.getClientSecurePort())

            #letting the requesting node know that it is accepted
            #also sending this servers connection parameters
            resp = serv.addNodeAccepted()

            conf.addNode(Node(nodeToAdd.server_id,
                nodeToAdd.getClientSecurePort(),
                nodeToAdd.getServerSecurePort(),
                nodeToAdd.getQualifiedName(),nodeToAdd.getHostname()))

            #trust the key
            openssl = OpenSSL(conf)
            openssl.addCa(nodeToAdd.key)

            nodeConnectRequests.removeNode(nodeToAdd.getId())
            conf.set('node_connect_requests', nodeConnectRequests)
            return True
        else:
            return False

    @staticmethod
    def establishConnectionsAndBroadcastTopology(serverState,nodesArr):
        #try to establish secure connections to a server

        for node in nodesArr:
            server_state.establishInboundConnection(node,serverState)
            server_state.establishOutboundConnection(node)
        NetworkTopologyCache().remove()

        log.debug("starting broadcast!")
        topology = ServerToServerMessage.getNetworkTopology()
##        #recalculate the network topology and broadcast it
        broadCastMessage = BroadcastMessage()
        broadCastMessage.updateNetworkTopology()

class ScGrantAllNodeConnections(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "grant-all-node-connections")

    def run(self, serverState, request, response):
        conf = ServerConf()
        #nodeReqs = copy.deepcopy(conf.getNodeConnectRequests())
        nodeReqs = conf.getNodeConnectRequests()
        connected = []

        N = 0
        for nodeConnectRequest in nodeReqs.nodes.values():
            N += 1
            ScGrantNodeConnection.grant(nodeConnectRequest.getId())

        ret = {}
        connectedNodes = conf.getNodes()
        for node in connectedNodes.nodes.itervalues():
            connected.append(node)

        ret['connected'] = connected
        ScGrantNodeConnection.establishConnectionsAndBroadcastTopology(
            serverState,connected)
        response.add("", ret)
        log.info("Granted node connection for %d nodes" % (N))

#message sent back in the requesting node
#This is a message that is sent from a server  not a client!!
#HTTP message
class ScAddNodeAccepted(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "node-connection-accepted")

    def run(self, serverState, request, response):
        conf = ServerConf()
        sentConnectRequests = conf.getSentNodeConnectRequests()
        node = json.loads(request.getParam('connectRequest'),
            object_hook=json_serializer.fromJson)
        if(sentConnectRequests.exists(node.getId())):
            nodeToAdd = sentConnectRequests.get(node.getId())
            conf.addNode(Node(node.server_id,
                node.getClientSecurePort(),
                node.getServerSecurePort(),
                node    .getQualifiedName(),nodeToAdd.getHostname()))
            #conf.addNode(nodeToAdd)
            openssl = OpenSSL(conf)
            openssl.addCa(node.key)
            sentConnectRequests.removeNode(node.getId())
            conf.set('sent_node_connect_requests', sentConnectRequests)
            # need to send back a status in the data notifying ok 
            response.add('Connection to node %s established'%node.toString())

            log.info("Node connection accepted")
            #add it to the node list         
        else:
            response.add('No previous node request sent for host %s' %node
            .toString())

            log.info("Node connection not accepted")


#servers can ask if they are in the nodes list of this server
# this will be performed in case ScAddNodeAccept message could not send back a message to 
#the requesting server due to firewall issues etc
class ScAddNodeIsAccepted(ServerCommand):
    pass


class ScListNodes(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "list-servers")

    def run(self, serverState, request, response):
        conf = ServerConf()
        nodes = conf.getNodes()
        resp = dict()
        nodes = nodes.getNodesByPriority()
        log.debug(nodes)
        resp['connections'] = []
        resp['broken_connections']=[]
        for node in nodes:
            if node.isConnected():
                resp['connections'].append(node)
            else:
                resp['broken_connections'].append(node)

        resp['sent_connect_requests'] = conf.getSentNodeConnectRequests()
        resp['received_connect_requests']= conf.getNodeConnectRequests()

        response.add("",resp)
        log.info("Listed nodes")


class ScChangeNodePriority(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "change-node-priority")

    def run(self, serverState, request, response):
        priority = int(request.getParam("priority"))
        nodeId = request.getParam("nodeId")
        conf = ServerConf()
        nodes = conf.getNodes()
        nodes.changePriority(nodeId, priority)
        conf.write()

        response.add("", nodes.getNodesByPriority())
        log.info("Changed %s node priority to %d" % (nodeId, priority))

