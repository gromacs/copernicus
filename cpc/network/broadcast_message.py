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


'''
Created on May 25, 2011

@author: iman
'''

from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.server_request import ServerRequest
from cpc.network.com.input import Input
from cpc.util.conf.server_conf import ServerConf
from cpc.util import json_serializer
from cpc.network.node import Node
import json
import logging
#messages that are broadcasted to all nodes
log=logging.getLogger('cpc.network.broadcast_message')
class BroadcastMessage(ServerToServerMessage):


    def __init__(self):
        self.conf = ServerConf()


    @PendingDeprecationWarning
    def updateConnectionParameters(self):
        cmdstring="connection-parameter-update"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)

        #prepare the connection params
        conf = ServerConf()
        connectionParams = dict()
        connectionParams['serverId'] = conf.getServerId()
        connectionParams['hostname'] = conf.getHostName()
        connectionParams['fqdn'] = conf.getFqdn()
        connectionParams['client_secure_port'] = conf\
        .getClientSecurePort()
        connectionParams['server_secure_port'] = conf\
        .getServerSecurePort()


        input2 = Input('connectionParams',
            json.dumps(connectionParams,default = json_serializer.toJson,
                indent=4))  # a json structure that needs to be dumped
        fields.append(input2)
        log.info("updating")
        self.broadcastToNeighboursOnly(fields,[])

    def updateNetworkTopology(self):
        topology = ServerToServerMessage.getNetworkTopology()
        
        cmdstring="network-topology-update"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        
        if topology != None:
            input2 = Input('topology',
                     json.dumps(topology,default = json_serializer.toJson,indent=4))  # a json structure that needs to be dumped
            fields.append(input2)
        
        self.broadcast(fields,[])
        
        
    def broadcast(self,fields,files = [],headers=dict()):
        topology = ServerToServerMessage.getNetworkTopology()   
        
        #we dont want to broadcast to ourself
        node = Node.getSelfNode(ServerConf())

        
        topology.removeNode(node.getId())     
        for node in topology.nodes.itervalues():
            self._sendMessage(node,fields,files,headers)


    def broadcastToNeighboursOnly(self,fields,files = [],headers=dict()):
        conf = ServerConf()
        for node in conf.getNodes().nodes.itervalues():
            self._sendMessage(node,fields,files,headers)


    def _sendMessage(self,node,fields,files = [],headers=dict()):
        self.node = node

        #TODO find nicer way to do this
        #a bit backwards to initialize the parent object here.
        ServerToServerMessage.__init__(self,node.getId())
        #self.initialize(node.server_id)
        headers['end-node'] = node.getHostname()
        headers['end-node-port'] = node.getServerSecurePort()
        msg = ServerRequest.prepareRequest(fields,[],headers)
        resp  = self.putRequest(msg)
        #print ProcessedResponse(resp).pprint()

