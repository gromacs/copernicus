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
Created on Jun 15, 2011

@author: iman
'''
import unittest
from cpc.util import json_serializer
import json
from cpc.network.node import Nodes
from cpc.network.node import Node

class TestNode(unittest.TestCase):


             
    def test_findRoute(self):
        # take a json topology and deserialize it
        file = open("network_topology_5_nodes.txt","r")
        #remove the 19 first license lines
        str = self.removeLicenseLines(file.read())
        resp = json.loads(str,object_hook=json_serializer.fromJson)
        topology = resp[0]['data']
        
        hostname = 'tcbm03.theophys.kth.se'
        node0Port = '13807'
        node4Port = '13811'
        start = topology.get("%s:%s"%(hostname,node0Port))
        end = topology.get("%s:%s"%(hostname,node4Port))
        
        route = Nodes.findRoute(start,end,topology)
        
        #for node in route:
            #print "%s %s"%(node.host,node.getVerifiedHttpsPort())
        
        self.assertEquals(route[0].verified_https_port,13807)
        self.assertEquals(route[len(route)-1].verified_https_port,13811)
 
        
    def test_findShortestRoute(self):
        file = open("network_topology_7_nodes.txt","r")
        str = self.removeLicenseLines(file.read())
        resp = json.loads(str,object_hook=json_serializer.fromJson)
        topology = resp[0]['data']
        
        hostname = 'tcbm03.theophys.kth.se'
        node0Port = '13808'
        node4Port = '13807'
        start = topology.get("%s:%s"%(hostname,node0Port))
        end = topology.get("%s:%s"%(hostname,node4Port))
        
        route = Nodes.findRoute(start,end,topology)
        
        for node in route:
            print "%s %s"%(node.host,node.verified_https_port)
        
        self.assertEquals(route[0].verified_https_port,13808)
        self.assertEquals(route[len(route)-1].verified_https_port,13807)
        self.assertEquals(len(route),3)
    
    #try to find a route that doesnt exist
    def test_findNoRoute(self):
        file = open("network_topology_5_nodes.txt","r")
        str = self.removeLicenseLines(file.read())
        resp = json.loads(str,object_hook=json_serializer.fromJson)
        topology = resp[0]['data']
        
        hostname = 'tcbm03.theophys.kth.se'
        node0Port = '13807'
        node4Port = '13812'  #this node do not exist
        start = topology.get("%s:%s"%(hostname,node0Port))
        end = Node(hostname,'14812',node4Port)
        
        route = Nodes.findRoute(start,end,topology)
        
        self.assertEquals(len(route),0)
    
    def test_getNodesByPriority(self):
        node1 = Node("host1",13807,14807)
        node2 = Node("host2",13807,14807)
        node3 = Node("host3",13807,14807)
        node4 = Node("host4",13807,14807)
        node5 = Node("host5",13807,14807)
    
        node4.getPriority() = 1
        node5.getPriority() = 2
        node3.getPriority() = 3
        node1.getPriority() = 4
        node2.getPriority() = 5
        #these priorities will actually be ignored since addnode will give a node the least priority
        
        nodes = Nodes()
        nodes.addNode(node1)
        nodes.addNode(node2)        
        nodes.addNode(node3)
        nodes.addNode(node4)
        nodes.addNode(node5)
        
        nodesList = nodes.getNodesByPriority()
        
        self.assertEquals(5,len(nodesList))
        self.assertEquals("host1",nodesList[0].host)
        self.assertEquals("host2",nodesList[1].host)
        self.assertEquals("host3",nodesList[2].host)
        self.assertEquals("host4",nodesList[3].host)
        self.assertEquals("host5",nodesList[4].host)    
        
    def test_setPriority(self):
        #should make sure no two nodes have same priority
        node1 = Node("host1",13807,14807)
        node2 = Node("host2",13807,14807)
        node3 = Node("host3",13807,14807)
        node4 = Node("host4",13807,14807)
        node5 = Node("host5",13807,14807)
    
        nodes = Nodes()
        nodes.addNode(node1)
        nodes.addNode(node2)        
        nodes.addNode(node3)
        nodes.addNode(node4)
        nodes.addNode(node5)
    
        #this means it should go to the end
        
        nodes.changePriority(node4.getId(),10)
        
        self.assertEquals(5,nodes.size())
        nodesList = nodes.getNodesByPriority()
        self.assertEquals("host1",nodesList[0].host)
        self.assertEquals("host2",nodesList[1].host)
        self.assertEquals("host3",nodesList[2].host)
        self.assertEquals("host5",nodesList[3].host)
        self.assertEquals("host4",nodesList[4].host)
        
        #todo ensure no nodes have same priority
        prionumbers = []
        for node in nodesList:
            prionumbers.append(node)
        uniquePrios = set(prionumbers)
        
        self.assertEquals(len(nodesList),len(uniquePrios))
        
        
        #test to move node to first index
        nodes.changePriority(node4.getId(),0)
        self.assertEquals(5,nodes.size())
        nodesList = nodes.getNodesByPriority()
        self.assertEquals("host4",nodesList[0].host)
        self.assertEquals("host1",nodesList[1].host)
        self.assertEquals("host2",nodesList[2].host)
        self.assertEquals("host3",nodesList[3].host)
        self.assertEquals("host5",nodesList[4].host)
        
        #todo ensure no nodes have same priority
        prionumbers = []
        for node in nodesList:
            prionumbers.append(node)
        uniquePrios = set(prionumbers)
        
        self.assertEquals(len(nodesList),len(uniquePrios))
        
        
        #test to set node to middle
        nodes.changePriority(node4.getId(),3)
        self.assertEquals(5,nodes.size())
        nodesList = nodes.getNodesByPriority()
        self.assertEquals("host1",nodesList[0].host)        
        self.assertEquals("host2",nodesList[1].host)        
        self.assertEquals("host3",nodesList[2].host)
        self.assertEquals("host4",nodesList[3].host)
        self.assertEquals("host5",nodesList[4].host)
        
        #todo ensure no nodes have same priority
        prionumbers = []
        for node in nodesList:
            prionumbers.append(node)
        uniquePrios = set(prionumbers)
        
        self.assertEquals(len(nodesList),len(uniquePrios))
        
    
    def test_addNodeNoPrio(self):
        #test to add a node with no priority
        node1 = Node("host1",13807,14807)
        node2 = Node("host2",13807,14807)
        node3 = Node("host3",13807,14807)
        
        nodes = Nodes()
        nodes.addNode(node1)
        nodes.addNode(node2)
        nodes.addNode(node3)
        
        nodesList = nodes.getNodesByPriority()
        self.assertEquals("host1",nodesList[0].host)
        self.assertEquals("host2",nodesList[1].host)
        self.assertEquals("host3",nodesList[2].host)
        
        self.assertEquals(0,nodesList[0].getPriority())
        self.assertEquals(1,nodesList[1].getPriority())
        self.assertEquals(2,nodesList[2].getPriority())
        
        #this should ensure that node is getting the last priority
        
        pass
      
    def removeLicenseLines(self,str):
        list = str.split('###')      
        return list[1] 
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
  #  suite = unittest.TestLoader().loadTestsFromTestCase(TestNode)
  #  unittest.TextTestRunner(verbosity=2).run(suite)
