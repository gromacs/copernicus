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

from cpc.network.server_to_server_message import ServerToServerMessage

'''
Created on Feb 1, 2011

@author: iman
'''
from cpc.util.conf.server_conf import ServerConf
from cpc.util.conf.connection_bundle import ConnectionBundle
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.network.broadcast_message import BroadcastMessage
import unittest
import time
import subprocess
import os
from genericpath import isdir
import shutil
from cpc.util.openssl import OpenSSL
from socket import gethostname
from cpc.network.com.input import Input
from cpc.network.com.file_input import FileInput
from cpc.network.server_request import ServerRequest
#from cpc.server.message import Message


#NOT a unit test this is a regression test using the unit testing framework
class TestRunProject(unittest.TestCase):
 
 
    def setUp(self):
        self.testConfPath = os.path.join(os.environ["HOME"], ".cpc/test") 
        self.testProjectPath = os.path.join(os.environ["HOME"],".cpc/test/test-proj") 
        
        if isdir(self.testProjectPath):
            shutil.rmtree(self.testProjectPath)
        
        if isdir(self.testConfPath):
            shutil.rmtree(self.testConfPath)
                
        self.serverConfs = dict()                        
        os.makedirs(self.testConfPath)
        os.makedirs(self.testProjectPath)
       
       
                   

    #TESTS node connection between 2 servers
    # makes a network topology call and ensures that there is 2 nodes in the topology
    # DOES NOT deeply check the network topology to ensure that a node has correct neighbouring nodes 
    def testStartProject(self):            

        numServers = 2

        self.createConfFolders(numServers)

        hostname = gethostname()
        
        node0HttpsPort = 13807
        node1HttpsPort = 13808
        node0HttpPort = 14807
        node1HttpPort = 14808

        for i in range(numServers):
            args = ['../../../../cpc-server','-c',self.serverConfs[i],'start']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
            subprocess.call(args)
        
        time.sleep(2)
        
        #connect node 0 to node 1
        args = ['../../../../cpc-server','-c',self.serverConfs[0],'add-node',hostname,str(node1HttpPort)]  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown
        subprocess.call(args)

        args = ['../../../../cpc-server','-c',self.serverConfs[1],'trust',hostname,str(node0HttpsPort)]  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown
        subprocess.call(args)


        #node 0 will be the node that workers connect to
        #TODO start up a worker
        args = ['../../../../cpc-worker','smp']
        subprocess.call(args)
         

        #verify existense of of nodes in each conf file
        conf1 = ServerConf(confdir=self.serverConfs[0], reload=True)

        
    def createConfFolders(self,num):
        verified_https_port = 13807
        unverified_https_port = 14807
        for i in range(num):            
            self.createConfFolder(i)
            server_conf = ServerConf(confdir=self.serverConfs[i],reload=True)
            server_conf.set('server_https_port',str(verified_https_port))
            server_conf.set('server_unverified_https_port',str(unverified_https_port))
            server_conf.set('mode',"debug")
            server_conf.set('run_dir',self.testProjectPath)
            
            client_conf  = ConnectionBundle(confdir=self.serverConfs[i],reload=True)
            client_conf.set('client_unverified_https_port',str(unverified_https_port))
            client_conf.set('client_https_port',str(verified_https_port))
            unverified_https_port +=1
            verified_https_port +=1
    
    def createConfFolder(self,name):
        path = os.path.join(os.environ["HOME"], ".cpc/test",str(name))
        os.makedirs(path)        
        self.serverConfs[name] = path
        conf = ServerConf(confdir=path,reload=True)
        OpenSSL(conf).setupServer()
         

    def tearDown(self):        
        for i in range(len(self.serverConfs)):
            args = ['../../../../cpcc','-c',self.serverConfs[i],'server','stop']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
            subprocess.call(args)
    
if __name__ == "__main__":
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestNetwork)
    #unittest.TextTestRunner(verbosity=2).run(suite)     
