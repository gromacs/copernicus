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
#messages that are broadcasted to all nodes
class BroadcastMessage(ServerToServerMessage):

    
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
        node = Node(ServerConf().getHostName(),
               ServerConf().getServerHTTPPort(),
               ServerConf().getServerVerifiedHTTPSPort(),
               ServerConf.getHostName())
        
        topology.removeNode(node.getId())     
        for node in topology.nodes.itervalues():
            self.initialize(node.host,node.https_port) 
            headers['end-node'] = node.host
            headers['end-node-port'] = node.https_port                     
            msg = ServerRequest.prepareRequest(fields,[],headers)   
            resp  = self.putRequest(msg)
            print ProcessedResponse(resp).pprint()
