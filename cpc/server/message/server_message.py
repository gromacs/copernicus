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
import json

from cpc.network.server_to_server_message import ServerToServerMessage
from cpc.network.com.input import Input
from cpc.network.server_request import ServerRequest
from cpc.util import json_serializer

log=logging.getLogger('cpc.server_to_server')

class ServerMessage(ServerToServerMessage):
    """Server-to-server messages.
       These messages can be sent to any node in the network
    """
    def pingServer(self,serverId):
        cmdstring='ping'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        headers = dict()
        if serverId!= None:
            headers['server-id'] = serverId
        msg = ServerRequest.prepareRequest(fields,[],headers)
        response= self.putRequest(msg)
        return response



    def workerReadyForwardedRequest(self, workerID, archdata, topology,
                                    originatingServer, heartbeatInterval,
                                    originatingClient=None):
        cmdstring='worker-ready-forward'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('worker', archdata))
        fields.append(Input('worker-id', workerID))
        fields.append(Input('heartbeat-interval', str(heartbeatInterval)))
        topologyInput = Input('topology',
            # a json structure that needs to be dumped
            json.dumps(topology,
                default = json_serializer.toJson,
                indent=4))
        fields.append(topologyInput)
        headers = dict()
        headers['originating-server-id'] = originatingServer
        if originatingClient is not None:
            headers['originating-client'] = originatingClient
        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
            headers))
        return response


    def commandFinishedForwardedRequest(self, cmdID, workerServer,
                                        projectServer, returncode,
                                        cputime, haveData):
        """A server-to-sever request doing command-finished. Used in
            forwarding non-local command-finished requests."""
        cmdstring='command-finished-forward'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('cmd_id', cmdID))
        fields.append(Input('version', "1"))
        fields.append(Input('worker_server', workerServer))
        fields.append(Input('project_server', projectServer))
        if returncode is not None:
            fields.append(Input('return_code', returncode))
        fields.append(Input('used_cpu_time', cputime))
        if haveData:
            fields.append(Input('run_data', 1))

        #the files are not sent in this message, instead they are pulled 
        # from the project server upon receiving this message (for now)
        files = []
        headers = dict()
        #headers['end-node'] = self.host
        #headers['end-node-port'] = self.port
        #self.connect()
        #log.debug("forwarding command finished to %s"%self.endNode)
        response= self.putRequest(ServerRequest.prepareRequest(fields, files,
            headers))
        return response


    def heartbeatForwardedRequest(self, workerID, workerDir, workerServer,
                                  iteration, heartbeatItemsXML):
        """A server-to-sever request doing heartbeat signal. Used in
           forwarding non-local heartbeat requests."""
        cmdstring='heartbeat-forward'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('worker_id', workerID))
        fields.append(Input('worker_dir', workerDir))
        fields.append(Input('iteration', iteration))
        fields.append(Input('worker_server', workerServer))
        fields.append(Input('heartbeat_items', heartbeatItemsXML))
        files = []
        headers = dict()
        #headers['end-node'] = self.host
        #headers['end-node-port'] = self.port
        #self.connect()
        #log.debug("forwarding command finished to %s"%self.endNode)
        response= self.putRequest(ServerRequest.prepareRequest(fields, files,
            headers))
        return response

    def deadWorkerFetchRequest(self, workerDir, runDir):
        """A server-to-sever request for fetching a set of run directories
           from a dead worker's output."""
        cmdstring='dead-worker-fetch'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('worker_dir', workerDir))
        fields.append(Input('run_dir', runDir))
        files = []
        headers = dict()
        #self.connect()
        response= self.putRequest(ServerRequest.prepareRequest(fields, files,
            headers))
        return response

    def pullAssetRequest(self, cmdID, assetType):
        cmdstring='pull-asset'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('cmd_id', cmdID))
        fields.append(Input('asset_type', assetType))
        headers = dict()
        headers['end-node'] = self.host
        headers['end-node-port'] = self.port

        #self.connect()
        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
            headers))
        return response

    def clearAssetRequest(self, cmdID):
        cmdstring='clear-asset'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('cmd_id', cmdID))
        headers = dict()
        headers['end-node'] = self.host
        headers['end-node-port'] = self.port
        #self.connect()
        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
            headers))
        return response

