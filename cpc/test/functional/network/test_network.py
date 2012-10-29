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
from cpc.util.conf.client_conf import ClientConf
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
class TestNetwork(unittest.TestCase):
 
 
    def setUp(self):
        self.testConfPath = os.path.join(os.environ["HOME"], ".cpc/test") 
        if isdir(self.testConfPath):
            shutil.rmtree(self.testConfPath)
                
        self.serverConfs = dict()                        
        os.makedirs(self.testConfPath)
       
       
       
    def test_createConf(self):
        self.createConfFolder(0)
        
        conf = ServerConf(None,self.serverConfs[0])
        
        test =conf.getServerKeyDir()
        
        self.assertTrue(os.path.isdir(conf.getServerKeyDir()))
        #assert that ca directory is created
        #assert server key dir exists
        #assert server cert dir exists
        
            
    def testStartServer(self):            
        self.createConfFolder(0)
        
        cmdLine = '../../../../cpc-server'
        
        self.assertTrue(os.path.isfile(cmdLine))
            
        args = [cmdLine,'-c',self.serverConfs[0],'start']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
        
        subprocess.call(args)
        
        clientCmd = '../../../../cpcc'
                
        args = [clientCmd,'-c',self.serverConfs[0],'server','test-server']
        
        subprocess.call(args)


    #TESTS node connection between 2 servers
    # makes a network topology call and ensures that there is 2 nodes in the topology
    # DOES NOT deeply check the network topology to ensure that a node has correct neighbouring nodes 
    def testStart2Servers(self):            

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


        #verify existense of of nodes in each conf file
        conf1 = ServerConf(confdir=self.serverConfs[0], reload=True)
        node0Nodes = conf1.getNodes()
        self.assertTrue(node0Nodes.exists(hostname,node1HttpsPort))

        conf2 = ServerConf(confdir=self.serverConfs[1],reload=True)
        node1Nodes = conf2.getNodes()
        self.assertTrue(node1Nodes.exists(hostname,node0HttpsPort))
                
        
        #do a network topology call        
        conf = ClientConf(confdir=self.serverConfs[0],reload=True)        
        client = ClientMessage()        
        topology =ProcessedResponse(client.networkTopology()).getData()
         
        self.assertEquals(topology.size() ,2)

     
    #This test is mainly to test the network topology
    #Checks the returned topology structure and ensures that each node has correct neighbors 
    def testNetworkTopology(self):        
        self.create5NodeNetwork()           
        conf = ClientConf(confdir=self.serverConfs[0],reload=True)        
        client = ClientMessage()        
        topology =ProcessedResponse(client.networkTopology()).getData()
        
         
        self.assertEquals(topology.size() ,5)
        
        #verify that the topology is correct
        
        #node 0 should have 2 connections one to node 1 and one to node 2
        node0 = "%s:%s"%(self.hostname,str(self.node0HttpsPort))
        node = topology.get(node0)
        self.assertEquals(node.nodes.size(),2)
        
        self.assertTrue(node.nodes.exists(self.hostname,self.node1HttpsPort))
        
        self.assertTrue(node.nodes.exists(self.hostname,self.node2HttpsPort))
            
        #node 1 should have 1 connection to node 2
        node1 = "%s:%s"%(self.hostname,str(self.node1HttpsPort))
        node = topology.get(node1)
        self.assertEquals(node.nodes.size(),2)
        self.assertTrue(node.nodes.exists(self.hostname,self.node2HttpsPort))
        
        #node2 should have 4 connections one to each other node
        node2 = "%s:%s"%(self.hostname,str(self.node2HttpsPort))
        node = topology.get(node2)
        self.assertEquals(node.nodes.size(),4)
        self.assertTrue(node.nodes.exists(self.hostname,self.node0HttpsPort))
        self.assertTrue(node.nodes.exists(self.hostname,self.node1HttpsPort))
        self.assertTrue(node.nodes.exists(self.hostname,self.node3HttpsPort))
        self.assertTrue(node.nodes.exists(self.hostname,self.node4HttpsPort))
                
        #node 3 should have 1 connection to node 2
        node3 = "%s:%s"%(self.hostname,str(self.node3HttpsPort))
        node = topology.get(node3)
        self.assertEquals(node.nodes.size(),1)
        self.assertTrue(node.nodes.exists(self.hostname,self.node2HttpsPort))
        
        #node 4 should have 1 connection to node 2
        node4 = "%s:%s"%(self.hostname,str(self.node4HttpsPort))
        node = topology.get(node4)
        self.assertEquals(node.nodes.size(),1)
        self.assertTrue(node.nodes.exists(self.hostname,self.node2HttpsPort))
        


    #sends test-server messages to servers in the network and ensures they reach the destination
    
    def testNetworkRoute(self):
        self.create5NodeNetwork()
        
        #send message from node 0 to 2 http
        conf = ClientConf(confdir=self.serverConfs[0],reload=True)        
        client = ClientMessage()                  
        response = ProcessedResponse(client.testServerRequest(self.hostname,self.node2HttpsPort))
        print response.pprint()
        
        #send message from node 0 to 4 https
        response = ProcessedResponse(client.testServerRequest(self.hostname,self.node4HttpsPort))
        print response.pprint()
        
        #send message from node 0 to 4 http
        #this throws an exception since we should not route with http
        response = ProcessedResponse(client.testServerRequest(self.hostname,self.node4Port))
        print response.pprint()
        
    
    #checks that message broadcasting works by sending a message to update network topologies
    #if a message has been correctly processed a node should be able to retreive a up to date
    #network topology from the cache
    def testBroadCastMessage(self):
        self.create5NodeNetwork()
        
        #this way we initialize the configs for a specific server which lets us test method calls as as specific server 
        clientConf = ClientConf(confdir=self.serverConfs[0],reload=True)
        serverConf = ServerConf(confdir=self.serverConfs[0],reload=True)
        
        broadCastMessage = BroadcastMessage()
        #logs should mention that we are setting elements to cache
        broadCastMessage.updateNetworkTopology()
                        
        
        clientConf = ClientConf(confdir=self.serverConfs[1],reload=True)
        serverConf = ServerConf(confdir=self.serverConfs[1],reload=True)
    
        #this should be brought from the cache(check in the logs)
        ServerToServerMessage.getNetworkTopology()                
        
    #tests the call method of the messaging API    
    def testCall(self):
        self.create5NodeNetwork()
        
        #this way we initialize the configs for a specific server which lets us test method calls as as specific server 
        clientConf = ClientConf(confdir=self.serverConfs[0],reload=True)
        serverConf = ServerConf(confdir=self.serverConfs[0],reload=True)
        
        #building a test server request
        
        cmdstring='test-server'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        request = ServerRequest.prepareRequest(fields,[],dict())        
                
    
        #message = Message()
        #response = message.call(request, gethostname(),13811)
        #processedResponse = ProcessedResponse(response)
        ##self.assertEquals("OK", processedResponse.getStatus())
        
        
      
                   
    def testStartServerRunProject(self):
        pass
    
    
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
        args = ['../../../../cpc-server','-c',self.serverConfs[0],'add-node',self.hostname,str(self.node1Port)] 
        subprocess.call(args) 
        
        #connect node 0 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[0],'add-node',self.hostname,str(self.node2Port)]
        subprocess.call(args) 
        
        #connect node 1 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[1],'add-node',self.hostname,str(self.node2Port)]
        subprocess.call(args)
         
        #connect node 3 to node 2
        args = ['../../../../cpc-server','-c',self.serverConfs[3],'add-node',self.hostname,str(self.node2Port)]
        subprocess.call(args) 
        
        #connect node 4 to node 2        
        args = ['../../../../cpc-server','-c',self.serverConfs[4],'add-node',self.hostname,str(self.node2Port)]
        subprocess.call(args) 

        #node1 accepts node 0
        args = ['../../../../cpc-server','-c',self.serverConfs[1],'trust-all'] 
        subprocess.call(args)
         
        #node2 accepts all nodes
        args = ['../../../../cpc-server','-c',self.serverConfs[2],'trust-all'] 
        subprocess.call(args)
    
    def createConfFolders(self,num):
        https_port = 13807
        http_port = 14807
        for i in range(num):            
            self.createConfFolder(i)
            server_conf = ServerConf(confdir=self.serverConfs[i],reload=True)
            server_conf.set('server_https_port',str(https_port))
            server_conf.set('server_http_port',str(http_port))
            server_conf.set('mode',"debug")
            client_conf  = ClientConf(confdir=self.serverConfs[i],reload=True)
            client_conf.set('client_http_port',str(http_port))
            client_conf.set('client_https_port',str(https_port))
            http_port +=1
            https_port +=1
    
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
