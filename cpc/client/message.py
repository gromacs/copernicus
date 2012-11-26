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
import json
import os

from cpc.network.com.client_base import ClientBase
from cpc.network.server_request import ServerRequest

from cpc.network.com.input import Input
from cpc.network.com.file_input import FileInput
from cpc.util import json_serializer
from cpc.util.conf.connection_bundle import ConnectionBundle
from cpc.util.openssl import OpenSSL

from cpc.network.node_connect_request import NodeConnectRequest

log=logging.getLogger('cpc.client')


class ClientMessage(ClientBase):
    '''Client request class. Has methods for specific requests.
        Messages that end users should be able to call should be defined here
    '''

    def __init__(self,host=None,port=None,conf=None):
        '''
        @input String host : the hostname
        @input String port : the port to connect to
        @input Conf conf
        '''
        self.host = host
        self.port = port
        self.conf = conf
        self.use_verified_https = False #the client runs on unverified https
        if self.conf is None: 
            self.conf = ConnectionBundle()
        if self.host is None:
            self.host = self.conf.getClientHost()
        if self.port is None:
            self.port = self.conf.getClientUnverifiedHTTPSPort()


    #NOTE should not be able to perform with a post or put request 
    def stopRequest(self): 
        cmdstring="stop"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def loginRequest(self, user, password):
        cmdstring="login"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)

        fields.append(Input('user', user))
        fields.append(Input('password', password))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

    def addUser(self, user, password):
        cmdstring="add-user"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)

        fields.append(Input('user', user))
        fields.append(Input('password', password))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

    # @param endNode is the endNode we want to reach
    # @param endNodePort 
    def testServerRequest(self,endNode=None,endNodePort=None):
        cmdstring='test-server'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        headers = dict()
        if endNode != None:
            headers['end-node'] = endNode
            headers['end-node-port'] = endNodePort      
        msg = ServerRequest.prepareRequest(fields,[],headers)        
        response=self.putRequest(msg)                            
        return response

    #resides here just for development purposes
    def networkTopology(self,topology=None):
        cmdstring="network-topology"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        
        if topology != None:
            input2 = Input('topology',
                     json.dumps(topology,default = json_serializer.toJson,indent=4))  # a json structure that needs to be dumped
            fields.append(input2)
        
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)               
        return response

    #port is what port the request should be sent to not what port to communicate with later on
    def addNode(self,host,http_port,https_port=None):
        #sends an add node request to the server 
        cmdstring = "add-node"
        fields = []
                
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        
        input2 = Input('host',host)
        input3 = Input('http_port',http_port)
        if(https_port !=None):
            fields.append(Input('https_port',https_port))
          
        fields.append(input)    
        fields.append(input2)
        fields.append(input3)
        msg = ServerRequest.prepareRequest(fields, [])
        response = self.postRequest(msg)
        return response
    
    
    #shows all the nodes connected to the current server
    def listNodes(self):        
        cmdString = "list-nodes"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)
    
    
    def listSentNodeConnectionRequests(self):
        cmdString = "list-sent-node-connection-requests"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)
    # lists all connect requests
    def listNodeConnectionRequests(self):
        cmdString = "list-node-connection-requests"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)
    
    #accepts a connect request for a node
    def grantNodeConnection(self,host,port):
        cmdString = "grant-node-connection"
        input = Input('cmd',cmdString)
        fields = []
        fields.append(input)    
        fields.append(Input('version', "1"))
        fields.append(Input('host',host))
        fields.append(Input('port',port))             
        
        msg = ServerRequest.prepareRequest(fields,[])
        
        return self.postRequest(msg)
        
    def grantAllNodeConnections(self):
        cmdString = "grant-all-node-connections"
        input = Input('cmd',cmdString)
        fields = []
        fields.append(input)    
        fields.append(Input('version', "1"))
          
        msg = ServerRequest.prepareRequest(fields,[])
        
        return self.postRequest(msg)  
     
    def changeNodePriority(self,node,priority,port):
        cmdString = "change-node-priority"
        id = "%s:%s"%(node,port)
        input = Input('cmd',cmdString)
        input2 = Input("nodeId",id)
        input3 = Input("priority",priority)
        fields = []
        fields.append(input)
        fields.append(input2)
        fields.append(input3)
        fields.append(Input('version', "1"))
        
        msg = ServerRequest.prepareRequest(fields,[])
        
        return self.postRequest(msg)  

    def listRequest(self, name): 
        """An assortment of list commands: for queues, running commands, and 
           heartbeat items."""
        cmdstring='list'   
        type = name     
        fields = []
        input = Input('cmd', cmdstring)
        typeInput = Input('type',name)
        fields.append(input)     
        fields.append(Input('version', "1"))
        fields.append(typeInput)     
        response=self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def readConfRequest(self):
        """Tell the server to re-read its configuration."""
        cmdstring="readconf"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def saveStateRequest(self):
        """Tell the server to save its state now."""
        cmdstring="save-state"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def commandFailedRequest(self, cmdID, cputime):
        cmdstring='command-finished-forward'
        fields = []
        input = Input('cmd', cmdstring)
        cmdIdInput = Input('cmd_id', cmdID)
        fields.append(cmdIdInput)
        fields.append(input)
        fields.append(Input('version', "1"))
        fields.append(Input('project_server', ''))
        fields.append(Input('used_cpu_time', cputime))
        #if jobTarFileobj is not None:
        #    jobTarFileobj.seek(0)
        #    files = [FileInput('rundata','cmd.tar.gz',jobTarFileobj)]
        #else:
        files=[]
        headers = dict()
        ## TODO: can this ever be not None?
        #if origServer is not None:
        #    headers['end-node'] = origServer
        
        response=self.putRequest(ServerRequest.prepareRequest(fields, files,
                                                              headers))
        return response


      
    # dataflow application requests
    def projectsRequest(self):
        """List all projects"""
        cmdstring="projects"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectStartRequest(self, name):
        """Start a new empty project """
        cmdstring="project-start"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('name',name))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectDeleteRequest(self, project, deleteDir):
        """Start a new empty project """
        cmdstring="project-delete"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('project',project))
        if deleteDir:
            fields.append(Input('delete-dir',1))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectGetDefaultRequest(self):
        """Get the default project project name"""
        cmdstring="project-get-default"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectSetDefaultRequest(self, name):
        """Set the default project project name"""
        cmdstring="project-set-default"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('name',name))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectListRequest(self, project, item):
        """List all items in a project"""
        cmdstring="project-list"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectInfoRequest(self, project, item):
        """List descriptions of project items"""
        cmdstring="project-info"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectLogRequest(self, project, item):
        """List all items in a project"""
        cmdstring="project-log"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectGraphRequest(self, project, item):
        """Graph item's network in a project"""
        cmdstring="project-graph"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectAddInstanceRequest(self, project,  func, name):
        """Add an instance to the top-level active network"""
        cmdstring="project-add-instance"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('name', name))
        fields.append(Input('function', func))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectConnectRequest(self, project, src, dst):
        """Add a connection to the top-level active network"""
        cmdstring="project-connect"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('source', src))
        fields.append(Input('destination', dst))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectActivateRequest(self, project, item):
        """List all projects"""
        cmdstring="project-activate"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectHoldRequest(self, project, item):
        """List all projects"""
        cmdstring="project-deactivate"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectRerunRequest(self, project, item, clearError):
        """Force a rerun and optionally clear an error."""
        cmdstring="project-rerun"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('item', item))
        if clearError:
            fields.append(Input('clear-error', 1))
            fields.append(Input('recursive', 1))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response


    def projectUploadRequest(self, project, file):
        """Upload project file"""
        cmdstring="project-upload"
        fields = []
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        files = [FileInput('upload','project.xml',open(file,'r'))]  
        response=self.putRequest(ServerRequest.prepareRequest(fields,files)) 
        return response
           
    def projectImportRequest(self, project, module):
        """Import a module in a network"""
        cmdstring="project-import"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('module', module))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response


    def projectGetRequest(self, project, item,getFile=False):
        """Get a data item from a project."""
        cmdstring="project-get"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        if getFile:
            fields.append(Input('getFile',True))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectSetRequest(self, project, item, value, filename):
        """Get a data item from a project."""
        cmdstring="project-set"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        if value is not None:
            fields.append(Input('value', value))
            files = []
        if filename is not None:
            fields.append(Input('filename', os.path.basename(filename)))
            files = [FileInput('upload','upload.dat',open(filename,'r'))]  
        response=self.putRequest(ServerRequest.prepareRequest(fields,files)) 
        return response

    def projectTransactRequest(self, project):
        """Start a series of previously scheduled set&connect requests, 
           to commit atomically."""
        cmdstring="project-transact"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response

    def projectCommitRequest(self, project):
        """Commit a series of previously scheduled set&connect requests, 
           atomically."""
        cmdstring="project-commit"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response
    def projectRollbackRequest(self, project):
        """Cancel a series of previously scheduled set&connect requests."""
        cmdstring="project-rollback"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[])) 
        return response
    
    def addClientRequest(self,host,port):
        cmdstring = "add-client-request"
        fields = []
        files = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        inf=open(self.conf.getCACertFile(), "r")
        key = inf.read()   
        
        nodeConnectRequest = NodeConnectRequest(self.conf.getHostName()
                                                ,self.conf.getClientHTTPPort()
                                                ,self.conf.getClientVerifiedHTTPSPort()
                                                ,key
                                                ,self.conf.getHostName())
        input2=Input('clientConnectRequest',
                     json.dumps(nodeConnectRequest,
                                default=json_serializer.toJson,
                                indent=4))

        fields.append(input2)
        
        response=self.putRequest(ServerRequest.prepareRequest(fields,files),
                                 https=False)
                  
        return response

    def projectSaveRequest(self, project):
        """Get a data item from a project."""
        cmdstring="project-save"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        #if project is not None:
        fields.append(Input('project', project))
        response=self.putRequest(ServerRequest.prepareRequest(fields,[]))
        return response

    def projectRestoreRequest(self, projectBundle,projectName):
        """Get a data item from a project."""
        cmdstring="project-load"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        #if project is not None:

        filename = os.path.basename(projectBundle)
        fields.append(Input('project', projectName))
        files = [FileInput('projectFile',filename,open(projectBundle,'r'))]

        response=self.putRequest(ServerRequest.prepareRequest(fields,files))
        return response

    

