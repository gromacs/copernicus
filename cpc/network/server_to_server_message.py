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
import cpc.util.log

from cpc.client.message import ClientMessage
from cpc.network.com.client_connection import VerifiedClientConnection
from cpc.util.exception import CpcError
from cpc.network.server_request import ServerRequest
from cpc.util.conf.server_conf import  ServerConf
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.com.client_base import ClientBase
from cpc.network.node import Nodes
from cpc.network.node import Node
from cpc.network.cache import Cache
log=logging.getLogger('cpc.server.server_to_server')

class ServerToServerMessageError(CpcError):
    def __init__(self, exc):
        self.str=exc.__str__()

class ServerToServerMessage(ClientBase):
    """Network-related server-to-server messages. 
       Only those messages related to network topology should go here, the
       rest should be in cpc.server.message.server_message."""
    #checks the network topology and finds out what node to connect to 
    #To reach the endnode. from then on it works like ClientBase
    #    
    def __init__(self, endNodeId):
        self.conf = ServerConf()    
        self.initialize(endNodeId)
        """Connect to a server opening a connection"""
        
    #@param String endNodeHostName
    #figures out what node to connect to in order to reach the end node
    def initialize(self,endNodeId):
        topology=self.getNetworkTopology()
        # this is myself:
        startNode = Node.getSelfNode(self.conf)

        self.endNode = topology.nodes.get(endNodeId)
        log.log(cpc.util.log.TRACE,"Finding route between %s(%s %s) and%s(%s "
                                   "%s"")"%(startNode.server_id,startNode.hostname,
                                    startNode.verified_https_port,
                                    self.endNode.server_id,
                                    self.endNode.hostname,self.endNode.verified_https_port))
        route = Nodes.findRoute(startNode, self.endNode,topology)

        #FIXME not sure if this is needed anymore?
        if(len(route) == 1): # the case where the current node is the endnode
            self.endNode = route[0]
            self.hostNode = route[0]
        else:
            self.hostNode = route[1]   #route[0] is the current host
            #TODO caching mechanism  
          
        self.host = self.hostNode.hostname
        self.port = self.hostNode.verified_https_port
        log.log(cpc.util.log.TRACE,"Server-to-server connecting to %s:%s"%
                (self.host,self.port))



    #NOTE might make sense to move this to requestHandler
    def delegateMessage(self,headers,messageStream):
        """Delegate the message to another server. Reads the message we get
           and requests a response from another client."""
        if not (headers.has_key('originating-server') or 
                headers.has_key('Originating-Server') ):
            headers['originating-server'] = ServerConf().getHostName()
        length = long(headers['content-length'])
        tmp = tempfile.TemporaryFile('w+b')
        tmp.write(messageStream.read(length))
        tmp.seek(0)
        content = mmap.mmap(tmp.fileno(),0,mmap.ACCESS_READ)
        request = ServerRequest(headers,content)
        ret=self.conn.sendRequest(request,method="PUT")

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
    def getNetworkTopology():
        cacheKey = 'network-topology'
        topology = Cache().get(cacheKey)
        if topology==False:
            conf = ServerConf()
            topology = Nodes()

            thisNode = Node.getSelfNode(conf)
            thisNode.nodes = conf.getNodes()
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
            Cache().add(cacheKey,topology)
        return topology


