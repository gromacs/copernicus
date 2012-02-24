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
from cpc.network.node_connect_request import NodeConnectRequest
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


from cpc.util.conf.server_conf import ServerConf
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.util.exception import CpcError
from cpc.network.node import Node
from cpc.network.node import Nodes
from cpc.util import json_serializer
from cpc.util.openssl import OpenSSL
from cpc.network.cache import Cache
from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.network.broadcast_message import BroadcastMessage
import cpc.server.message
from cpc.server.message.server_message import ServerMessage
import json


log=logging.getLogger('cpc.server.command')

class ServerCommandError(CpcError):
    def __init__(self, msg):
        self.str=msg

class ServerCommand(object):
    """A server command. Constructed in the server command exec class,
        and executed afterwards (possibly in multiple threads at the 
        same time!!) ."""
    def __init__(self, name):
        self.name=name

    def run(self, serverState, request, response):
        """Run the command. Responses should go to response"""
        raise ServerCommandError(
                "Don't know what to do with command '%s'"%(self.name))

    def getRequestString(self):
        """Get the request command string associated with the command."""
        return self.name
    
class SCStop(ServerCommand):
    """Stop server command"""
    def __init__(self):
        ServerCommand.__init__(self, "stop")

    def run(self, serverState, request, response):
        log.info("Stop request received")
        serverState.doQuit() 
        response.add('Quitting.')

class SCSaveState(ServerCommand):
    """Save the server state"""
    def __init__(self):
        ServerCommand.__init__(self, "save-state")

    def run(self, serverState, request, response):
        log.info("Save-state request received")
        serverState.write() 
        response.add('Saved state.')


class SCTestServer(ServerCommand):
    """Test server command"""
    def __init__(self):
        ServerCommand.__init__(self, "test-server")

    def run(self, serverState, request, response):
        conf = ServerConf()
        response.add('Server %s:%s is fine.'%(conf.getHostName(),conf.getServerHTTPSPort()))


class SCListServerItems(ServerCommand):
    """queue/running/heartbeat list command """
    def __init__(self):
        ServerCommand.__init__(self, "list")

    def run(self, serverState, request, response):
        toList=request.getParam('type')
        retstr=""
        if toList == "queue":
            list=serverState.getCmdQueue().list()
            queue = []            
            for cmd in list:
                queue.append(cmd.toJSON())
            retstr = queue
        elif toList == "running":
            running = []
            list=serverState.getRunningCmdList().list()
            for cmd in list:
                running.append(cmd.toJSON())
            retstr = running
        elif toList == "heartbeats":
            list=serverState.getHeartbeatList()
            heartbeats = list.toJSON()
            retstr = heartbeats
        else:
            raise ServerCommandError("Unknown item to list: '%s'"%toList)
        response.add(retstr)


class SCNetworkTopology(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self,"network-topology")
                
    def run(self, serverState, request, response):
        conf = ServerConf()
        topology = Nodes()         
        if request.hasParam('topology'):            
            topology = json.loads(request.getParam('topology'),object_hook = json_serializer.fromJson)
        
                    
        thisNode = Node(conf.getHostName(),conf.getServerHTTPPort(),conf.getServerHTTPSPort(),conf.getHostName())                                
        thisNode.nodes = conf.getNodes() 
        thisNode.workerStates = serverState.getWorkerStates()             
        topology.addNode(thisNode)
        
        for node in thisNode.nodes.nodes.itervalues():
            if topology.exists(node.getId()) == False:
                #connect to correct node
                clnt = ClientMessage(node.host,node.https_port,conf=conf)
                #send along the current topology
                rawresp = clnt.networkTopology(topology)
                processedResponse=ProcessedResponse(rawresp)       
                topology = processedResponse.getData()
        
                                
        response.add("", topology)                            

class SCNetworkTopologyUpdate(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "network-topology-update")

    def run(self, serverState, request, response):
        cacheKey = "network-topology"
        Cache().remove(cacheKey)
        topology = json.loads(request.getParam('topology'),object_hook = json_serializer.fromJson)
        Cache().add(cacheKey, topology)
        response.add("Updated network topology")

                

       
class SCReadConf(ServerCommand):
    """Update the configuration based on new settings."""
    def __init__(self):
        ServerCommand.__init__(self, "readconf")

    def run(self, serverState, request, response):
        conf = ServerConf()
        conf.reread()
        response.add("Reread configuration.")




#Clients request a connection
#HTTP message
class ScAddClientRequest(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "add-client-request")
    
    def run(self, serverState, request, response):
                
        #TODO check so that we already havent granted access to this node
        clientConnectRequest = json.loads(request.getParam('clientConnectRequest'),
                                        object_hook=json_serializer.fromJson)
        conf = ServerConf()
#        conf.addNodeConnectRequest(clientConnectRequest)
        
        openssl = OpenSSL(conf)
        #openssl.addCa(clientConnectRequest.key)   
        
        inf=open(conf.getCACertFile(), "r")
#        nodeConnect = NodeConnectRequest(conf.getHostName(),
#                                         conf.getServerHTTPPort(),
#                                         conf.getServerHTTPSPort(),inf.read())
        response.add("",inf.read())


#sends an add node request
class ScAddNode(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "add-node")
        
    def run(self, serverState, request, response):
        conf = ServerConf()
        host = request.getParam('host')
        
          
        http_port = request.getParam('http_port')

        inf=open(conf.getCACertFile(), "r")
        key = inf.read()     
       
                
        serv = ServerMessage(host,http_port)
        resp = ProcessedResponse(serv.addNodeRequest(key,host))
        
        nodeConnectRequest = resp.getData()
        
        if(request.hasParam('https_port')):     
            https_port = request.getParam('https_port')
            nodeConnectRequest.https_port = int(https_port)
            
        nodeConnectRequest.http_port = int(http_port)  #http port should always be sent from client
        conf.addSentNodeConnectRequest(nodeConnectRequest)
        response.add('',nodeConnectRequest)    
    

#receives add node connect request from a server
#this is a message sent from a server not a client!!
#HTTP message
class ScAddNodeRequest(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "add-node-request")
    
    def run(self, serverState, request, response):
                
        #TODO check so that we already havent granted access to this node
        nodeConnectRequest = json.loads(request.getParam('nodeConnectRequest'),
                                        object_hook=json_serializer.fromJson)
        
        unqalifiedDomainName=(request.getParam('unqalifiedDomainName'))
        
        conf = ServerConf()
        conf.addNodeConnectRequest(nodeConnectRequest)
        inf=open(conf.getCACertFile(), "r")
        nodeConnect = NodeConnectRequest(unqalifiedDomainName,
                                         conf.getServerHTTPPort(),
                                         conf.getServerHTTPSPort()
                                         ,inf.read()
                                         ,conf.getHostName())
        
        response.add("",nodeConnect)
                
    
#message to send when a node has beeen accepted
class ScGrantNodeConnection(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "grant-node-connection")

    def run(self, serverState, request, response):
        host =  request.getParam('host')
        https_port = request.getParam('port')        
        conf = ServerConf()
        
        nodeKey = "%s:%s"%(host,https_port)
        if self.grant(nodeKey):
            response.add('Connection to node %s:%s established'%
                              (host,https_port))
            #recalculate the network topology and broadcast it
            Cache().remove("network-topology")
            topology = ServerToServerMessage.getNetworkTopology()
            broadCastMessage = BroadcastMessage()        
            broadCastMessage.updateNetworkTopology()
        else: 
            response.add('Node has not requested to connect')    

    @staticmethod
    def grant(key): #key is the Node key
        conf = ServerConf()
        nodes = conf.getNodeConnectRequests()        
        
        if nodes.exists(key):
            nodeToAdd = nodes.get(key) #this returns a nodeConnectRequest object

            serv = cpc.server.message.server_message.ServerMessage(nodeToAdd.host,nodeToAdd.http_port) #trying to connect to https port here
            resp = serv.addNodeAccepted()   #sending a message saying what node accepted the request 
            #TODO analyze the response, if it is an error of some sort do not continue
            conf.addNode(Node(nodeToAdd.host,
                              nodeToAdd.http_port,
                              nodeToAdd.https_port,
                              nodeToAdd.qualified_name))            
            
            #trust the key
            openssl = OpenSSL(conf)
            openssl.addCa(nodeToAdd.key)            

            
            nodes.removeNode(nodeToAdd.getId())
            conf.set('node_connect_requests',nodes)
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
        notConnected = []
        
        
        for nodeConnectRequest in nodeReqs.nodes.itervalues():
            ScGrantNodeConnection.grant(nodeConnectRequest.getId())                
#            
#            if ScGrantNodeConnection.grant(nodeConnectRequest.host, 
#                                           nodeConnectRequest.https_port) == False:                
#            
#                notConnected.append(Node(nodeConnectRequest.host,
#                                         nodeConnectRequest.http_port,
#                                         nodeConnectRequest.https_port))
#                
                
        ret = {}
        
        connectedNodes = conf.getNodes()
        for node in connectedNodes.nodes:            
            connected.append(node)
            
            
        ret['connected'] = connected
       # ret ['notConnected'] = notConnected
        
        response.add("",ret)            
            #find all node connect requests
            #for each node connect request do a grant

#message sent back in the requesting node
#This is a message that is sent from a server  not a client!!
#HTTP message
class ScAddNodeAccepted(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "node-connection-accepted")
    
    def run(self, serverState, request, response):
        conf = ServerConf()
        nodes = conf.getSentNodeConnectRequests()        
        node = json.loads(request.getParam('acceptedNode'),object_hook=json_serializer.fromJson)
        if(nodes.exists(node.getId())):
            nodeToAdd = nodes.get(node.getId())           
            conf.addNode(nodeToAdd)
            openssl = OpenSSL(conf)
            openssl.addCa(nodeToAdd.key)           
            nodes.removeNode(nodeToAdd.getId())
            conf.set('sent_node_connect_requests',nodes)
            # need to send back a status in the data notifying ok 
            response.add('Connection to node %s:%s established'%
                              (nodeToAdd.host,nodeToAdd.https_port))  
            
            #add it to the node list         
        else:
            response.add('No previous node request sent for host %s:%s'%
                              (node.host,node.https_port))
        

#servers can ask if they are in the nodes list of this server
# this will be performed in case ScAddNodeAccept message could not send back a message to 
#the requesting server due to firewall issues etc
class ScAddNodeIsAccepted(ServerCommand):
    pass

class ScListNodes(ServerCommand):
    def __init__(self):
            ServerCommand.__init__(self, "list-nodes")
        
    def run(self, serverState, request, response):
        conf = ServerConf()
        nodes = conf.getNodes()
        response.add("",nodes.getNodesByPriority())


class ScListSentNodeConnectionRequests(ServerCommand):
    def __init__(self):
            ServerCommand.__init__(self, "list-sent-node-connection-requests")
        
    def run(self, serverState, request, response):
        conf = ServerConf()
        response.add("",conf.getSentNodeConnectRequests())

class ScListNodeConnectionRequests(ServerCommand):
    def __init__(self):
            ServerCommand.__init__(self, "list-node-connection-requests")
        
    def run(self, serverState, request, response):
        conf = ServerConf()
        response.add("",conf.getNodeConnectRequests())


class ScChangeNodePriority(ServerCommand):
    def __init__(self):
            ServerCommand.__init__(self, "change-node-priority")
        
    def run(self, serverState, request, response):
        
        priority = int(request.getParam("priority"))    
        nodeId = request.getParam("nodeId")
        conf = ServerConf()
        nodes = conf.getNodes()
        nodes.changePriority(nodeId,priority)
        #TODO might need to set it in serverCOnf just testing references
        conf.write()
        
        response.add("",nodes.getNodesByPriority())

