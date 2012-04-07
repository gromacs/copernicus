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
Created on Apr 11, 2011

@author: iman
'''
import socket

from cpc.network.node import Nodes
import cpc.util.conf.conf_base
import os
import sys
import logging

log=logging.getLogger('cpc.util.conf.server_conf')

class ServerConf(cpc.util.conf.conf_base.Conf):
    '''
    classdocs
    '''
    __shared_state = {}
    CN_ID = "server"
    def __init__(self,conffile = "server.conf",confdir = None,
                 reload=False):
        #initiate with specific name for conf file
        #be able to specifiy conf file of your own
        #set all server params

        self.__dict__ = self.__shared_state
                  
        if len(self.__shared_state)>0 and reload == False: 
            return;
            
        cpc.util.conf.conf_base.Conf.__init__(self, conffile, confdir)
        
        self._add("conf_dir",os.path.join(self.get("conf_dir"),"server"), 'The configuration directory',
                  userSettable=True)
        self.initDefaults()     
        self.have_conf_file = self.tryRead()
        
        '''
        Constructor
        '''
    def initDefaults(self):
        
        cpc.util.conf.conf_base.Conf.initDefaults(self)
        server_host = ''
        self.defaultHTTPSPort = 13807
        self.defaultHTTPPort = 14807
        
        self._add('server_host', server_host, 
          "Address the server listens on", True)
        self._add('server_https_port', self.defaultHTTPSPort,
                  "Port number the server listens on for https connections", True,None,'\d+')

        self._add('server_http_port', self.defaultHTTPPort,
                  "Port number the server listens on for http connections", True,None,'\d+')

        
        self._add( 'nodes', Nodes(), 
                  "List of nodes connected to this server", False)
      
        self._add('node_connect_requests',Nodes(),
                  "List of nodes requesting to connect to this server",False)
      
        self._add('sent_node_connect_requests',Nodes(),
                  "List of connect requests sent",False)
      
        self._add('project_file', "projects.xml", 
                  "Projects file name (relative to conf_dir)",
                  relTo='conf_dir')
        #self._add('task_file', "tasks.xml", 
        #          "Task queue (relative to conf_dir)",
        #          relTo='conf_dir')
        self._add('state_save_interval', 240,
                  "Time in seconds between state saves",
                  True, validation='\d+')
        
        self._add('import_path', "", 
                  "Colon-separated list of directories to search for imports, in addition to cpc/lib, .copernicus/lib and .copernicus/<hostname>/lib",
                  True)

        self._add('mode','prod',
                  "The run mode of the server",
                  True,None,None,['trace','debug','prod'])

        # run options
        self._add('run_dir', None,
                  "Base directory of all files produced by running projects.",
                  True)
        
                # log options
        self._add('log_dir', "log",
                  "Directory containing logs",
                  True,
                  relTo='conf_dir')
        self._add('server_log_file', "server.log",
                  "The server log file", False, 
                  relTo='log_dir')
        self._add('error_log_file', "error.log",
                  "The error log file", False, 
                  relTo='log_dir')
        
                # heartbeat options
        self._add('heartbeat_time', 120,
                  "Time in seconds between heartbeats",
                  True, validation='\d+')
        self._add('heartbeat_file', "heartbeatlist.xml",
                  "Heartbeat monitor list", False,
                  relTo='conf_dir')
        
                #static configuration
        self._add('web_root', 'web',
                  "The directory where html,js and css files are located")

        self._add('client_host', socket.getfqdn(),
            "For when the server needs to connect to self ", True)  #FIXME this will be obsolete once server to server messages does not connect to self
        
        # assets
        self._add('local_assets_dir', "local_assets",
                  "Directory containing local assets such as command output files",
                  True,
                  relTo='conf_dir')
        
        
        dn=os.path.dirname(sys.argv[0])
        self.execBasedir = ''
        if dn != "":
            self.execBasedir=os.path.abspath(dn)
            self._add('exec_base_dir', self.execBasedir, 
                      'executable base directory')
        # make child processes inherit our path
        if os.environ.has_key('PYTHONPATH'):
            os.environ['PYTHONPATH'] += ":%s"%self.execBasedir
        else:
            os.environ['PYTHONPATH'] = self.execBasedir

        
        
    def setServerHost(self,serverAddress):        
        return self.set('server_host',serverAddress)                
    def setClientHost(self,address):        
        return self.set('client_host',address)
                    

    def addSentNodeConnectRequest(self,nodeConnectRequest):
        nodes = self.conf['sent_node_connect_requests'].get()
        nodes.addNode(nodeConnectRequest)
        self.set('sent_node_connect_requests',nodes)
        return True
    
    def addNodeConnectRequest(self,nodeConnectRequest):
        nodes = self.conf['node_connect_requests'].get()
        nodes.addNode(nodeConnectRequest)
        self.set('node_connect_requests',nodes)
        return True

    
    def addNode(self,node):        
        """adds a server to the list of servers that this server can connect 
           to."""    
                    
        nodes=self.conf['nodes'].get()                                                      
        nodes.addNode(node)        
        self.conf['nodes'].set(nodes)
        self.write()
             
        return True 

    
    def removeNode(self,id):
               
        nodes=self.conf['nodes'].get()
        node = nodes.get(id)        
        nodes.removeNode(node.get(id))        
        self.conf['nodes'].set(nodes)
        
        self.write()
        
        return True

    def getNodes(self):
        return self.conf.get('nodes').get()

    def getNodeConnectRequests(self):
        return self.get('node_connect_requests')

    def getSentNodeConnectRequests(self):
        return self.get('sent_node_connect_requests')
    def getLogDir(self):
        return self.getFile('log_dir')
 
    def getServerLogFile(self):
        return self.getFile('server_log_file')
 
    def getErrorLogFile(self):
        return self.getFile('error_log_file')

    def getStateSaveInterval(self):
        return int(self.conf['state_save_interval'].get())

    def getHeartbeatTime(self):
        return int(self.conf['heartbeat_time'].get())
    def getHeartbeatFile(self):
        return self.getFile('heartbeat_file')
 
    def setMode(self,mode):
        self.conf['mode'].set(mode)
    
    def hasParent(self):
        return (len(self.conf['parent_nodes'].get()) > 0)
    
    def isDebug(self):
        if self.conf['mode'].get() == 'debug':
            return True
        else:
            return False
                   
    # get functions
    
    def getUserSettableConfigs(self):
        configs = dict()
        for key,value in self.conf.iteritems():
            if value.userSettable == True:
                configs[key] = value
        
        return configs
             
    
    def getParent(self):
        #NOTE this should be extended so that it choses the parent 
        # with the highest prioirity
        parentNodes = self.conf['parent_nodes'].get()
        return parentNodes[0] #At the moment a child can only have one parent
    
    def getServerHost(self):
        return self.conf['server_host'].get()
    def getServerHTTPSPort(self):
        return int(self.conf['server_https_port'].get())
    def getServerHTTPPort(self):        
        return int(self.conf['server_http_port'].get())
    def getHostName(self):
        return self.hostname

    #just a wrapper method to conform with clientConnection
    def getClientHTTPSPort(self):
        return int(self.get('server_https_port'))

    #just a wrapper method to conform with clientConnection
    def getClientHTTPPort(self):
        return int(self.get('server_http_port'))

    #just a wrapper method to conform with clientConnection
    def getClientHost(self):
        return self.conf['client_host'].get()


    def getDefaultServer(self):
        return self.conf['client_host'].get()
    
    def getMode(self):
        return self.conf['mode'].get()

    def getProjectFile(self):
        return self.getFile('project_file')
    #def getTaskFile(self):
    #    return self.getFile('task_file')

    #def getRunBasedir(self):
    #    return self.getFile('project_file')

    def getRunDir(self):
        return self.getFile('run_dir')
    def setRunDir(self, rundir):
        self.set('run_dir', rundir)


  
    
    def getWebRootPath(self):        
        return os.path.join(self.execBasedir,self.get('web_root'))
    
    
   
    #def getImportPath(self):
    #    return self.conf['import_path'].get()

    def getImportPaths(self):
        lst=self.conf['import_path'].get().split(':')
        retlist=[]
        for ls in lst:
            str=ls.strip()
            if str != "":
                retlist.append(str)
        # there are two default items in the path, .copernicus/lib, and
        retlist.append(os.path.join(self.conf['global_dir'].get(), 'lib'))
        retlist.append(os.path.join(self.conf['conf_dir'].get(), 'lib'))
        retlist.append(os.path.join(self.execBasedir, 'cpc', 'lib'))
        return retlist
 
    
    def getLocalAssetsDir(self):
        return self.getFile('local_assets_dir')
    
