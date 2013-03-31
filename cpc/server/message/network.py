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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from server_command import ServerCommand, ServerCommandError
from cpc.util.conf.server_conf import ServerConf
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.node import Node
from cpc.network.node import Nodes
from cpc.util import json_serializer
from cpc.util.openssl import OpenSSL
from cpc.network.cache import Cache
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.network.broadcast_message import BroadcastMessage
from cpc.server.message.server_message import RawServerMessage
from cpc.network.node_connect_request import NodeConnectRequest
import json

log = logging.getLogger('cpc.server.message.network')


class SCNetworkTopology(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "network-topology")

    def run(self, serverState, request, response):
        conf = ServerConf()
        topology = Nodes()
        if request.hasParam('topology'):
            topology = json.loads(request.getParam('topology'),
                object_hook=json_serializer.fromJson)

        thisNode = Node.getSelfNode(conf)
        thisNode.nodes = conf.getNodes()
        thisNode.workerStates = serverState.getWorkerStates()
        topology.addNode(thisNode)

        for node in thisNode.nodes.nodes.itervalues():
            if topology.exists(node.getId()) == False:
                #connect to correct node
                clnt = ClientMessage(node.hostname, node.verified_https_port,
                                     conf=conf, use_verified_https=True)
                #send along the current topology
                rawresp = clnt.networkTopology(topology)
                processedResponse = ProcessedResponse(rawresp)
                topology = processedResponse.getData()

        response.add("", topology)
        log.info("Returned network topology size %d" % topology.size())


class SCNetworkTopologyUpdate(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "network-topology-update")

    def run(self, serverState, request, response):
        cacheKey = "network-topology"
        Cache().remove(cacheKey)
        topology = json.loads(request.getParam('topology'),
            object_hook=json_serializer.fromJson)
        Cache().add(cacheKey, topology)
        response.add("Updated network topology")
        log.info("Update network topology done")


class SCConnectionParamUpdate(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "connection-parameter-update")

    def run(self, serverState, request, response):
        #get the connection params for this node
        newParams =json.loads(request.getParam("connectionParams"))
        conf = ServerConf()
        nodes = conf.getNodes()
        result = dict()
        if nodes.exists(newParams['serverId']):
            node = nodes.get(newParams['serverId'])
            node.hostname = newParams['hostname']
            node.verified_https_port = newParams['server_verified_https_port']
            node.unverified_https_port = newParams[
                                         'server_unverified_https_port']
            node.qualified_name = newParams['fqdn']
            conf.removeNode(node.server_id)
            conf.addNode(node)
            response.add("Updated connection paramters")
            log.info("Updated connection params for %s"%newParams['serverId'])

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

        unverified_https_port = request.getParam('unverified_https_port')
        result = dict()
        #do we have a server with this hostname or fqdn?
        connectedNodes = conf.getNodes()
        if (connectedNodes.hostnameOrFQDNExists(host) == False):
            serv = RawServerMessage(host, unverified_https_port)
            resp = ProcessedResponse(serv.sendAddNodeRequest(host))

            if resp.isOK():
                result = resp.getData()
                nodeConnectRequest = NodeConnectRequest(result['serverId'],
                    int(unverified_https_port),None,None,result['fqdn'],host)

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
        ServerCommand.__init__(self, "connnect-server-request")

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
            #recalculate the network topology and broadcast it
            Cache().remove("network-topology")
            topology = ServerToServerMessage.getNetworkTopology()
            broadCastMessage = BroadcastMessage()
            broadCastMessage.updateNetworkTopology()
            ret = {}

            ret['connected'] = [ServerConf().getNodes().get(serverId)]
            response.add("", ret)

            log.info("Granted node connection for %s" % (serverId))
        else:
            response.add('Node has not requested to connect')
            log.info("Did not grant node connection for %s" % (serverId))

    @staticmethod
    def grant(key): #key is the Node key
        conf = ServerConf()
        nodes = conf.getNodeConnectRequests()

        if nodes.exists(key):
            nodeToAdd = nodes.get(key) #this returns a nodeConnectRequest object

            serv = RawServerMessage(nodeToAdd.hostname,
                nodeToAdd.unverified_https_port)

            #letting the requesting node know that it is accepted
            #also sending this servers connection parameters
            resp = serv.addNodeAccepted()

            conf.addNode(Node(nodeToAdd.server_id,
                nodeToAdd.unverified_https_port,
                nodeToAdd.verified_https_port,
                nodeToAdd.qualified_name,nodeToAdd.hostname))

            #trust the key
            openssl = OpenSSL(conf)
            openssl.addCa(nodeToAdd.key)

            nodes.removeNode(nodeToAdd.getId())
            conf.set('node_connect_requests', nodes)
            return True
        else:
            return False


class ScGrantAllNodeConnections(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "grant-all-node-connections")

    def run(self, serverState, request, response):
        conf = ServerConf()
        nodeReqs = copy.deepcopy(conf.getNodeConnectRequests())
        connected = []

        N = 0
        for nodeConnectRequest in nodeReqs.nodes.itervalues():
            N += 1
            ScGrantNodeConnection.grant(nodeConnectRequest.getId())

        ret = {}
        connectedNodes = conf.getNodes()
        for node in connectedNodes.nodes.itervalues():
            connected.append(node)

        ret['connected'] = connected

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
                node.unverified_https_port,
                node.verified_https_port,
                node.qualified_name,nodeToAdd.hostname))
            #conf.addNode(nodeToAdd)
            openssl = OpenSSL(conf)
            openssl.addCa(node.key)
            sentConnectRequests.removeNode(node.getId())
            conf.set('sent_node_connect_requests', sentConnectRequests)
            # need to send back a status in the data notifying ok 
            response.add('Connection to node %s:%s established' %
                         (nodeToAdd.hostname, nodeToAdd.verified_https_port))
            log.info("Node connection accepted")
            #add it to the node list         
        else:
            response.add('No previous node request sent for host %s:%s' %
                         (node.host, node.verified_https_port))
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
        resp['connections'] = nodes.getNodesByPriority()
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
        #TODO might need to set it in serverCOnf just testing references
        conf.write()

        response.add("", nodes.getNodesByPriority())
        log.info("Changed %s node priority to %d" % (nodeId, priority))

