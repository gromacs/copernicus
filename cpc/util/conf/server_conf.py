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
import uuid
import os
import sys
import shutil
import logging

from cpc.network.node import Nodes
import conf_base
import cpc.util.exception
from cpc.util.conf.conf_base import Conf, ConfError


log=logging.getLogger(__name__)

class ServerIdNotFoundException(cpc.util.exception.CpcError):
    pass

class SetupError(cpc.util.exception.CpcError):
    pass


def resolveSetupConfDir(confDir, dirname, hostConfDir,altDirName=None):
    '''
    resolves the confdir to write to when performing a server setup
    '''
    if os.path.exists(os.path.join(confDir, dirname)):
        hostConfDir = True
    if hostConfDir or altDirName:
        confDir = os.path.join(confDir, dirname)
    else:
        confDir = os.path.join(confDir, conf_base.Conf.default_dir)
    return confDir

def resolveSetupConfBaseDir(altDirName = None):
    dirname = altDirName or socket.getfqdn()
    return dirname

def initiateServerSetup(rundir, forceReset, hostConfDir,
                        altDirName=None):

    dirname = resolveSetupConfBaseDir(altDirName)
    confDir=cpc.util.conf.conf_base.findAndCreateGlobalDir()

    # now if a host-specific directory already exists, we use that
    confDir = resolveSetupConfDir(confDir, dirname, hostConfDir,altDirName=altDirName)

    checkDir = os.path.join(confDir,"server")
    confFile = os.path.join(checkDir,"server.conf")

    #Checks for conf files and option to reset kept here even though the function cmd_line_utils.checkServerConfExistAndAskToRemove
    #Is handling the same thing. In a case where we do not have user interaction it should still be this functions responsibility to check if server confs exist
    if forceReset and os.path.exists(checkDir):
        print "Overwriting configuration in %s"%confDir
        shutil.rmtree(checkDir)
    elif os.path.exists(checkDir) or os.path.exists(confFile):
        raise SetupError("A configuration already exists in %s"%
                        (confDir))

    os.makedirs(checkDir)
    print("Making server configuration in %s"%checkDir)
    outf=open(os.path.join(confFile), 'w')
    outf.close()
    cf=ServerConf(confdir=confDir)
    openssl = cpc.util.openssl.OpenSSL(dirname)
    setupCA(openssl,cf,forceReset)
    openssl.setupServer()
    cf.setRunDir(rundir)


    #write a server id
    idFile = open(cf.getServerIdFileName(),"w")
    idFile.write(str(uuid.uuid1()))
    idFile.close()
    #make file read only so that nobody accidentally rewrites a server id
    os.chmod(cf.getServerIdFileName(),0400)



def setupCA(openssl, conf, forceReset=False):
    checkDir = conf.getCADir()
    if forceReset and os.path.exists(checkDir):
        shutil.rmtree(checkDir)
    elif os.path.exists(checkDir)== True:
        raise SetupError("A CA already exists in: %s"%checkDir)
    openssl.setupCA()


class ServerConf(conf_base.Conf):
    '''
    classdocs
    '''
    __shared_state = {}
    CN_ID = "server"
    def __init__(self, confdir=None):
        """Initialize with an optional configuration directory. """
        # check whether the object is already initialized
        if self.exists():
            return
        # call parent constructor with right dir name
        conf_base.Conf.__init__(self, name='server.conf', 
                                confSubdirName="server",
                                userSpecifiedPath=confdir)
        self.initDefaults()
        try:
            self.have_conf_file = self._tryRead()
        except ConfError:
            pass# this is OK, during setup we only have an empty conf file so
            # we will get a JSON parse error that we can safely ignore


    def initDefaults(self):
        conf_base.Conf.initDefaults(self)
        server_host = ''

        self._add('server_host', server_host, 
                  "Address the server listens on", True)

        self._add('server_fqdn', socket.getfqdn(),
                  "Manually specified fqdn", True)


        self._add('server_secure_port', Conf.getDefaultServerSecurePort(),
                  "Port number the server uses for communication from servers ",
                  True,None,'\d+')


        self._add('client_secure_port', Conf.getDefaultClientSecurePort(),
                  "Port number the server listens on for communication from clients",
                  True,None,'\d+')
        
        self._add( 'nodes', Nodes(), 
                  "List of nodes connected to this server", False)

        self._add('revoked_nodes',Nodes(),"List of revoked nodes",False)
        self._add('node_connect_requests',Nodes(),
                  "List of nodes requesting to connect to this server",False)
      
        self._add('sent_node_connect_requests',Nodes(),
                  "List of connect requests sent",False)
      
        self._add('project_file', "projects.xml", 
                  "Projects file name (relative to conf_dir)",
                  relTo='conf_dir')
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

        # Task exec queue size. If it exceeds this size, the dataflow 
        # propagation blocks.
        self._add('task_queue_size', 1024,
                  "Dataflow execution task queue size",
                  True, validation='\d+')
        
                #static configuration
        self._add('web_root', 'web',
                  "The directory where html,js and css files are located")

        # assets
        self._add('local_assets_dir', "local_assets",
                  "Directory containing local assets such as command output files",
                  True,
                  relTo='conf_dir')


        self._add('server_cores', -1,
                  "Number of cores to use on the server (for OpenMP tasks).",
                  userSettable=True, validation='\d+')


        self._add('num_persistent_connections',5,
            "Number of persistent connection to establish for each trusted "
            "server",
            userSettable=True)

        self._add('keep_alive_interval',60,
            "Keep alive interval of server connections,value is in minutes"
            ,userSettable=True)

        self._add('reconnect_interval',300,
            "Interval between trying to reestablish failed connections ,"
            "value is in seconds"
            ,userSettable=True)


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
        self.set('server_host',serverAddress)
        return

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


    def removeNodeConnectRequest(self,id):
        with self.lock:
            nodes=self.conf['node_connect_requests'].get()
            nodes.removeNode(id)
            self.conf['node_connect_requests'].set(nodes)
            self._writeLocked()
        return True

    def removeSentNodeConnectRequest(self,id):
        with self.lock:
            nodes=self.conf['sent_node_connect_requests'].get()
            nodes.removeNode(id)
            self.conf['sent_node_connect_requests'].set(nodes)
            self._writeLocked()
        return True

    def addRevokedNode(self,node):
        nodes = self.conf['revoked_nodes'].get()
        nodes.addNode(node)
        self.set('revoked_nodes',nodes)
        return True

    def addNode(self,node):        
        """adds a server to the list of servers that this server can connect 
           to."""    
        with self.lock:            
            nodes=self.conf['nodes'].get()
            nodes.addNode(node)
            self.conf['nodes'].set(nodes)
            self._writeLocked()
        return True 

    
    def removeNode(self,id):
        with self.lock:
            nodes=self.conf['nodes'].get()
            nodes.removeNode(id)
            self.conf['nodes'].set(nodes)
            self._writeLocked()
        return True

    def getNodes(self):
        '''
        returns dict  (key=serverId, value=Node)
        '''
        with self.lock:
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
        with self.lock:
            return int(self.conf['state_save_interval'].get())

    def getHeartbeatTime(self):
        with self.lock:
            return int(self.conf['heartbeat_time'].get())
    def getHeartbeatFile(self):
        return self.getFile('heartbeat_file')

    def getServerCores(self):
        with self.lock:
            return int(self.conf['server_cores'].get())

    def setMode(self,mode):
        with self.lock:
            self.conf['mode'].set(mode)
    
    def hasParent(self):
        with self.lock:
            return (len(self.conf['parent_nodes'].get()) > 0)
    
    def isDebug(self):
        with self.lock:
            if self.conf['mode'].get() == 'debug':
                return True
            else:
                return False
                   
    # get functions
    
    def getUserSettableConfigs(self):
        configs = dict()
        with self.lock:
            for key,value in self.conf.iteritems():
                if value.userSettable == True:
                    configs[key] = value
        return configs
             
    
    def getParent(self):
        with self.lock:
            #NOTE this should be extended so that it choses the parent 
            # with the highest prioirity
            parentNodes = self.conf['parent_nodes'].get()
            #At the moment a child can only have one parent <- still?? SP
            return parentNodes[0] 
    
    def getServerHost(self):
        return self.conf['server_host'].get()

    def getServerSecurePort(self):
        with self.lock:
            return int(self.conf['server_secure_port'].get())

    def getClientSecurePort(self):
        with self.lock:
            return int(self.conf['client_secure_port'].get())

    def getFqdn(self):
        with self.lock:
            return self.conf['server_fqdn'].get()


    def getDefaultServer(self):
        with self.lock:
            return self.conf['client_host'].get()
    
    def getMode(self):
        with self.lock:
            return self.conf['mode'].get()

    def getProjectFile(self):
        return self.getFile('project_file')

    def getRunDir(self):
        return self.getFile('run_dir')
    def setRunDir(self, rundir):
        self.set('run_dir', rundir)

    def getTaskQueueSize(self):
        with self.lock:
            return self.conf['task_queue_size'].get()
    
    def getWebRootPath(self):        
        return os.path.join(self.execBasedir,self.get('web_root'))

    def getImportPaths(self):
        retlist=[]
        with self.lock:
            lst=self.conf['import_path'].get().split(':')
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


    def getServerIdFileName(self):
        return os.path.join(self.getConfDir(),"server.id")

    def getServerId(self):
        try:
            f = open(self.getServerIdFileName(),"r")
            id = f.readline()
            f.close()
            return id
        except IOError as e:
            raise ServerIdNotFoundException("Was not able to read the server "
                                            "id from %s\n please verify that "
                                            "this file exists"%self.getServerIdFileName())

    def getKeepAliveInterval(self):
        return int(self.conf['keep_alive_interval'].get())

    def getReconnectInterval(self):
        return int(self.conf['reconnect_interval'].get())

    def getNumPersistentConnections(self):
        return int(self.conf['num_persistent_connections'].get())
