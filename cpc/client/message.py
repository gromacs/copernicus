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
import os

from cpc.network.com.client_base import ClientBase
from cpc.network.server_request import ServerRequest

from cpc.network.com.input import Input
from cpc.network.com.file_input import FileInput
from cpc.util.conf.client_conf import ClientConf

log=logging.getLogger('cpc.client')


class ClientMessage(ClientBase):
    '''Client request class. Has methods for specific requests.
        Messages that end users should be able to call should be defined here
    '''

    def __init__(self,host=None,port=None,conf=None, use_verified_https=False):
        '''
        @input String host : the hostname
        @input String port : the port to connect to
        @input Conf conf
        '''

        self.host = host
        self.port = port
        self.conf = conf
        self.use_verified_https = use_verified_https
        if self.conf is None:
            #FIXME THIS IS WRONG AND TOOK HOURS TO FIND OUT WHY
            #APPERANTLY WE CANNOT INITIATE A CLIENTCONF WITHOUT SPECYFYING A
            # BUNDLE OF SOME SORT AS IS DONE IN cpcc
            self.conf = ClientConf()
        if self.host is None:
            self.host = self.conf.getClientHost()
        if self.port is None:
            if use_verified_https:
                self.port = self.conf.getClientVerifiedHTTPSPort()
            else:
                self.port = self.conf.getClientUnverifiedHTTPSPort()

    #NOTE should not be able to perform with a post or put request 
    def stopRequest(self): 
        cmdstring="stop"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        #response= self.putRequest(ServerRequest.prepareRequest(fields, []))
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

    def deleteUser(self, user):
        cmdstring="delete-user"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('user', user))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

    def promoteUser(self, user):
        cmdstring="promote-user"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)

        fields.append(Input('user', user))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

    def demoteUser(self, user):
        cmdstring="demote-user"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)

        fields.append(Input('user', user))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

    def grantAccess(self, user):
        cmdstring="grant-access"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('name', user))
        msg = ServerRequest.prepareRequest(fields,[])
        response = self.postRequest(msg)
        return response

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

    def serverInfo(self):
        cmdstring='server-info'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        response= self.postRequest(msg)
        return response


    def networkTopology(self):
        cmdstring="network-topology-client"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))

        msg = ServerRequest.prepareRequest(fields,[])

        response = self.postRequest(msg)
        return response

    #port is what port the request should be sent to not what port to communicate with later on
    def addNode(self,host,unverified_https_port):
        #sends an add node request to the server
        cmdstring = "connnect-server"
        fields = []

        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))

        input2 = Input('host',host)
        input3 = Input('unverified_https_port',unverified_https_port)

        fields.append(input)
        fields.append(input2)
        fields.append(input3)
        msg = ServerRequest.prepareRequest(fields, [])
        response = self.postRequest(msg)
        return response

    #shows all the nodes connected to the current server
    def listServers(self):
        cmdString = "list-servers"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)


    def revokeNode(self,serverId):
        cmdString = "revoke-node"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        fields.append(Input('serverId',serverId))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)


    #accepts a connect request for a node
    def grantNodeConnection(self,serverId):
        cmdString = "grant-node-connection"
        input = Input('cmd',cmdString)
        fields = []
        fields.append(input)    
        fields.append(Input('version', "1"))
        fields.append(Input('serverId',serverId))

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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def statusRequest(self, project):
        """Fetches an aggregated general information about the server and
           and its projects. The argument project is optional"""
        cmdstring="status"
        fields = []
        fields.append(Input('cmd', cmdstring))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def readConfRequest(self):
        """Tell the server to re-read its configuration."""
        cmdstring="readconf"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def saveStateRequest(self):
        """Tell the server to save its state now."""
        cmdstring="save-state"
        fields = []
        input = Input('cmd', cmdstring)   
        fields.append(input)
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, files,
                                                               headers))
        return response


      
    # dataflow application requests
    def projectsRequest(self):
        """List all projects"""
        cmdstring="projects"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectStartRequest(self, name):
        """Start a new empty project """
        cmdstring="project-start"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('name',name))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectGetDefaultRequest(self):
        """Get the default project project name"""
        cmdstring="project-get-default"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectSetDefaultRequest(self, name):
        """Set the default project project name"""
        cmdstring="project-set-default"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        fields.append(Input('name',name))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectDebugRequest(self, project, item):
        """Get debug info for project items"""
        cmdstring="project-debug"
        fields = []
        fields.append(Input('cmd', cmdstring))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('item', item))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, files))
        return response

    #list modules available on the server
    def listModules(self):
        cmdString = "list-modules"
        fields  = []
        input = Input('cmd',cmdString)
        fields.append(input)
        fields.append(Input('version', "1"))
        msg = ServerRequest.prepareRequest(fields,[])
        return self.postRequest(msg)

    def projectImportRequest(self, project, module):
        """Import a module in a network"""
        cmdstring="project-import"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        if project is not None:
            fields.append(Input('project', project))
        fields.append(Input('module', module))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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
        response= self.postRequest(ServerRequest.prepareRequest(fields, files))
        return response

    def projectTransactRequest(self, project):
        """Start a series of previously scheduled set&connect requests, 
           to commit atomically."""
        cmdstring="project-transact"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectCommitRequest(self, project):
        """Commit a series of previously scheduled set&connect requests, 
           atomically."""
        cmdstring="project-commit"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response
    def projectRollbackRequest(self, project):
        """Cancel a series of previously scheduled set&connect requests."""
        cmdstring="project-rollback"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
        return response

    def projectSaveRequest(self, project):
        """Get a data item from a project."""
        cmdstring="project-save"
        fields = []
        fields.append(Input('cmd', cmdstring))
        fields.append(Input('version', "1"))
        #if project is not None:
        fields.append(Input('project', project))
        response= self.postRequest(ServerRequest.prepareRequest(fields, []))
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

        response= self.postRequest(ServerRequest.prepareRequest(fields, files))
        return response

    

