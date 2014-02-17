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
from cpc.util.conf.connection_bundle import ConnectionBundle

log=logging.getLogger('cpc.worker.message')
class WorkerMessage(ClientBase):
    '''
    Messages not directly sent from a user of copernicus
    '''
    
    def __init__(self,host=None,port=None,conf=None):
        self.conf = conf
        if self.conf==None:
            self.conf = ConnectionBundle()
        self.host = host
        self.port = port
        if self.host == None:
            self.host = self.conf.getClientHost()
        if self.port == None:
            self.port = self.conf.getServerSecurePort()
        
        self.require_certificate_authentication=True
        self.privateKey = self.conf.getPrivateKey()
        self.keychain = self.conf.getCaChainFile()

    def workerRequest(self, workerID, archdata):
        cmdstring='worker-ready'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('worker', archdata))
        fields.append(Input('worker-id', workerID))
        headers = dict()
        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
                                                               headers))
        return response
    
    def commandFinishedRequest(self, cmdID, origServer, returncode, cputime, 
                               jobTarFileobj):
        cmdstring='command-finished'
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "2"))
        fields.append(Input('cmd_id', cmdID))
        fields.append(Input('project_server', origServer))
        if returncode is not None:
            fields.append(Input('return_code', str(returncode)))
        fields.append(Input('used_cpu_time', str(cputime)))
        jobTarFileobj.seek(0)
        files = [FileInput('run_data','cmd.tar.gz',jobTarFileobj)]
        headers = dict()
        # TODO we directly forward to the originating server. We don't have to
        # because there's active relaying, but for now this simplifies things
        headers['server-id'] = origServer
        log.debug("sending command finished for cmd id %s"%cmdID)
        response= self.putRequest(ServerRequest.prepareRequest(fields,
                                                               files, headers))
        return response
    
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
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "2"))
        fields.append(Input('worker_id', workerID))
        fields.append(Input('worker_dir', workerDir))
        fields.append(Input('iteration', iteration))
        fields.append(Input('heartbeat_items', heartbeatItemsXML))
        response= self.putRequest(ServerRequest.prepareRequest(fields, []))
        return response
