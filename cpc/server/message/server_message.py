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
Created on Mar 10, 2011

@author: iman
'''
import logging
from cpc.network.com.client_base import ClientBase
from cpc.network.com.input import Input
from cpc.network.com.file_input import FileInput
from cpc.network.server_request import ServerRequest
from cpc.util.conf.server_conf import ServerConf
from cpc.network.node import Node
from cpc.network.node_connect_request import NodeConnectRequest
import json
from cpc.util import json_serializer

log=logging.getLogger('cpc.server_to_server')

#FIXME wrong naming having conflictin classes here
class ServerMessage(ClientBase):
    """ Server-to-server messages."""
    def __init__(self,host=None,port=None):
        self.conf = ServerConf()      
        self.host = host
        self.port = port
        if self.host == None:
            self.host = self.conf.getServerHost()
        if self.port == None:
            self.port = self.conf.getServerHTTPSPort()
            
        self.privateKey = self.conf.getPrivateKey()
        self.keychain = self.conf.getCaChainFile()
            
    def commandFailedRequest(self, cmdID, origServer, jobTarFileobj=None):
        cmdstring='command-failed'
        fields = []
        input = Input('cmd', cmdstring)
        cmdIdInput = Input('cmd_id', cmdID)
        fields.append(cmdIdInput)
        fields.append(input)
        fields.append(Input('project_server', origServer))
        if jobTarFileobj is not None:
            jobTarFileobj.seek(0)
            files = [FileInput('rundata','cmd.tar.gz',jobTarFileobj)]
        else:
            files=[]
        headers = dict()
        # TODO: can this ever be not None?
        if origServer is not None:
            headers['end-node'] = origServer            
        response=self.putRequest(ServerRequest.prepareRequest(fields, files, 
                                                              headers))
        return response

    #This is a HTTP message
    def addNodeRequest(self,key,host):
        conf = ServerConf()
        cmdstring ='add-node-request'
        fields = []
        input=Input('cmd',cmdstring)
        
        nodeConnectRequest = NodeConnectRequest(conf.getHostName()
                                                ,conf.getServerHTTPPort()
                                                ,conf.getServerHTTPSPort()
                                                ,key
                                                ,conf.getHostName())

        input2=Input('nodeConnectRequest',json.dumps(nodeConnectRequest,default=json_serializer.toJson,indent=4))                
        input3=Input('unqalifiedDomainName',host)
        fields.append(input)
        fields.append(input2)  
        fields.append(input3)  
        response= self.putRequest(ServerRequest.prepareRequest(fields), https=False)        
        return response 

    #This is a HTTP message
    def addNodeAccepted(self):
        conf = ServerConf()
        node = Node(conf.getHostName(),conf.getServerHTTPPort(),conf.getServerHTTPSPort(),conf.getHostName())
        cmdstring ='node-connection-accepted'
        fields = []
        input=Input('cmd',cmdstring)
        input2=Input('acceptedNode',json.dumps(node,default=json_serializer.toJson,indent=4))
        
        
        fields.append(input)
        fields.append(input2)
        
        response= self.putRequest(ServerRequest.prepareRequest(fields), https=False)
        return response 

