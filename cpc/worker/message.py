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
from cpc.util import json_serializer
from cpc.util.conf.connection_bundle import ConnectionBundle
import json
from cpc.network.node_connect_request import NodeConnectRequest

log=logging.getLogger('cpc.worker.message')
class WorkerMessage(ClientBase):
    '''
    Messages not directly sent from a user of copernicus
    '''
    
    def __init__(self,host=None,port=None):
        self.conf = ConnectionBundle()
        self.host = host
        self.port = port
        if self.host == None:
            self.host = self.conf.getClientHost()
        if self.port == None:
            self.port = self.conf.getClientHTTPSPort()
        
            
        self.privateKey = self.conf.getPrivateKey()
        self.keychain = self.conf.getCaChainFile()    

    def workerRequest(self, archdata,topology=None):
        cmdstring='worker-ready'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        adata = Input('worker', archdata)
        fields.append(adata)
        if topology != None:
            topologyInput = Input('topology',
                         json.dumps(topology,default = json_serializer.toJson,indent=4))  # a json structure that needs to be dumped
            fields.append(topologyInput)
        headers = dict()
        response=self.putRequest(ServerRequest.prepareRequest(fields, [], headers))
        return response
    
    def commandFinishedRequest(self, cmdID, origServer, jobTarFileobj):
        cmdstring='command-finished'
        fields = []
        input = Input('cmd', cmdstring)
        cmdIdInput = Input('cmd_id', cmdID)
        fields.append(input)
        fields.append(cmdIdInput)
        fields.append(Input('project_server', origServer))
        jobTarFileobj.seek(0)
        files = [FileInput('rundata','cmd.tar.gz',jobTarFileobj)]
        headers = dict()
        headers['end-node'] = origServer
        log.debug("sending command finished for cmd id %s"%cmdID)
        response=self.putRequest(ServerRequest.prepareRequest(fields, files, headers))
        return response
    
    #def commandFailedRequest(self, cmdID, origServer, jobTarFileobj=None):
    #    cmdstring='command-failed'
    #    fields = []
    #    input = Input('cmd', cmdstring)
    #    cmdIdInput = Input('cmd_id', cmdID)
    #    fields.append(input)
    #    fields.append(cmdIdInput)
    #    fields.append(Input('project_server', origServer))
    #    if jobTarFileobj is not None:
    #        jobTarFileobj.seek(0)
    #        files = [FileInput('rundata','cmd.tar.gz',jobTarFileobj)]
    #    else:
    #        files=[]
    #    headers = dict()
    #    if origServer is not None:
    #        headers['end-node'] = origServer
    #        #headers['direction'] = 'up'
    #    response=self.putRequest(ServerRequest.prepareRequest(fields, files, 
    #                                                          headers))
    #    return response

    def workerHeartbeatRequest(self, workerID, workerDir, first, last, changed,
                               heartbeatItemsXML):
        cmdstring='worker-heartbeat'                   
        if first:
            iteration="first"
        elif last:
            iteration="last"
        elif changed:
            iteration="update"
        else:
            iteration="none"
        fields = []
        input = Input('cmd', cmdstring)
        workerIdInput = Input('worker_id', workerID)
        workerDirInput = Input('worker_dir', workerDir)
        iterationsInput = Input('iteration', iteration)
        workloadsData = Input('heartbeat_items', heartbeatItemsXML)
        fields.append(input)
        fields.append(workerIdInput)
        fields.append(workerDirInput)
        fields.append(iterationsInput)
        fields.append(workloadsData)
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response
    
    #FIXME duplicate in client/message.py
    def addClientRequest(self,host,port):                
        cmdstring = "add-client-request"
        fields = []
        files = []
        fields.append(Input('cmd', cmdstring))
        
        
        inf=open(self.conf.getCACertFile(), "r")
        key = inf.read()   
        
        nodeConnectRequest = NodeConnectRequest(self.conf.getHostName()
                                                ,self.conf.getClientHTTPPort()
                                                ,self.conf.getClientHTTPSPort()
                                                ,key,self.conf.getHostName())

        input2=Input('clientConnectRequest',json.dumps(nodeConnectRequest,default=json_serializer.toJson,indent=4))

        fields.append(input2)
        
        response=self.putRequest(ServerRequest.prepareRequest(fields,files),https=False)
                  
        return response          

    
