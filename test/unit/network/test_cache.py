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
Created on July 19, 2011

@author: iman
'''
import unittest
from cpc.util import json_serializer
import json
from cpc.network.cache import Cache
import copy
from cpc.network.node import Nodes
from cpc.network.node import Node

#NOTE this unit test i not fully finished since we need to create mock objects in order to really verify that a method is called or picked up from cache
#for now it provides a simple isolated way to run the cache and step through the code in order to verify that everything goes well
class TestCache(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        Cache().cleanAll()

    def testCacheFunction(self):
        Cache().add("doCall",doCall())
        
                
        #ensure we have a cache with 1 element in it
        self.assertEquals(1,Cache().size())
        
        oldCache = copy.copy(Cache().getCache())
        
        Cache().add("doSomethingElse",doSomethingElse())
        
        #ensure we have a cache with 2 element in it
        self.assertEquals(2,Cache().size())
        
        #ensure nothing else in the cache is modified
        for key in oldCache.iterkeys():
            self.assertEquals(Cache().cache[key],oldCache[key])
    
    def testCacheObjects(self):
        node1 = Node("testhost",8080,9090)
        node2 = Node("testhost",8081,9091)
    
        nodes = Nodes()
        nodes.addNode(node1)
        nodes.addNode(node2)
        
        Cache().add("network-topology",nodes)
        cachedNodes = Cache().get("network-topology")
        
        self.assertEquals(2,cachedNodes.size())
        
        
    
    def testCleanAll(self):
        Cache().add("doCall",doCall())
        Cache().add("doSomethingElse",doSomethingElse())
        Cache().cleanAll()
        self.assertEquals(0,Cache().size())
    
    def testCleanFunction(self):
        Cache().add("doCall",doCall())
        Cache().add("doSomethingElse",doSomethingElse())
        Cache().remove("doCall")
        self.assertEquals(1,Cache().size())  #not implemented yet
    
    
def doCall():
    return "doing call"
def doSomethingElse():
    return "Doing something else"


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
