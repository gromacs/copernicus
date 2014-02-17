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
Created on sept 1, 2011

@author: iman
'''
from cpc.util.conf.server_conf import ServerConf
from cpc.util.conf.connection_bundle import ConnectionBundle
import unittest
import time
import subprocess
import os
from genericpath import isdir
import shutil
from cpc.util.openssl import OpenSSL
from socket import gethostname


#NOT a unit test this is a regression test using the unit testing framework
class TestNetworkSetup(unittest.TestCase):
 
 
    def setUp(self):
        self.testConfPath = os.path.join(os.environ["HOME"], ".cpc/test") 
        if isdir(self.testConfPath):
            shutil.rmtree(self.testConfPath)
                
        self.serverConfs = dict()                        
        os.makedirs(self.testConfPath)
       
       
       
    def testCreate5NodeNetwork(self):
        self.create5NodeNetwork()
    
    #creates a network of 5 nodes
    #network looks as following
#    0-------1
#    | \    /|
#    |   2   |
#    | /    \|
#    3-------4    
    def create5NodeNetwork(self):
        numServers = 5
                        
        self.createConfFolders(numServers)
        self.hostname = gethostname()
        
        self.node0Port = 14807
        self.node1Port = 14808
        self.node2Port = 14809
        self.node3Port = 14810
        self.node4Port = 14811

        self.node0HttpsPort = 13807
        self.node1HttpsPort = 13808
        self.node2HttpsPort = 13809
        self.node3HttpsPort = 13810
        self.node4HttpsPort = 13811

        
        for i in range(numServers):
            args = ['../../../../cpc-server','-c',self.serverConfs[i],'start']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
            subprocess.call(args)

        time.sleep(2)

        #connect node 0 to node 1
        args = ['../../../../cpc-server','-c',self.serverConfs[0],'connnect-server',self.hostname,str(self.node1Port)]
        subprocess.call(args) 
        
        #connect node 0 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[0],'connnect-server',self.hostname,str(self.node2Port)]
        subprocess.call(args) 
        
        #connect node 1 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[1],'connnect-server',self.hostname,str(self.node2Port)]
        subprocess.call(args)
         
        #connect node 3 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[3],'connnect-server',self.hostname,str(self.node2Port)]
        subprocess.call(args) 
        
        #connect node 4 to node 2        
        args = ['../../../../cpc-server','-c',self.serverConfs[4],'connnect-server',self.hostname,str(self.node2Port)]
        subprocess.call(args) 

#        #node1 accepts node 0
#        args = ['../../../../cpc-server','-c',self.serverConfs[1],'trust-all'] 
#        subprocess.call(args)
#         
#        #node2 accepts all nodes
#        args = ['../../../../cpc-server','-c',self.serverConfs[2],'trust-all'] 
#        subprocess.call(args)
    
    def createConfFolders(self,num):
        server_secure_port = 13807
        client_secure_port = 14807
        for i in range(num):            
            self.createConfFolder(i)
            server_conf = ServerConf(confdir=self.serverConfs[i],reload=True)
            server_conf.set('server_https_port',str(server_secure_port))
            server_conf.set('client_secure_port',str(client_secure_port))
            server_conf.set('mode',"debug")
            client_conf  = ConnectionBundle(confdir=self.serverConfs[i],reload=True)
            client_conf.set('client_secure_port',str(client_secure_port))
            client_conf.set('client_https_port',str(server_secure_port))
            client_secure_port +=1
            server_secure_port +=1
    
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
