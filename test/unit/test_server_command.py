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


import unittest
from cpc.server.message.server_command import SCTaskStatus
import json



class TestServerCommand(unittest.TestCase):
    
    
    def setUp(self):                
        pass
    
    
    #tests to find a route in a simple topoloy with one node on each level
    def testFindSimpleRoute(self):
        endNode = 'ferlin'
              
        json = '{"network-topology": {"data": {"host": "tcbm03.theophys.kth.se", "nodes": [{"host": "tcbm01.theophys.kth.se", "nodes": [{"host": "ferlin", "nodes": []}]}]}}}'
        
        route = self.verifyRouteCorrect(json,endNode)
        self.assertEquals(len(route),3)
    
    #tests to find a route that has one node on each level except for on the last level where it has to leaf nodes    
    def testFindAdvancedRoute(self):
        json = '{"network-topology": {"data": {"host": "tcbm03.theophys.kth.se", "nodes": [{"host": "tcbm01.theophys.kth.se", "nodes": [{"host": "ferlin", "nodes": []}, {"host": "gromacs2", "nodes": []}]}]}}}'

        #find a route to the first leaf
        route = self.verifyRouteCorrect(json, 'gromacs2')
        self.assertEquals(len(route),3)
        
        #find a route to the second leaf        
        route2 = self.verifyRouteCorrect(json, 'ferlin')
        self.assertEquals(len(route2),3)
                                        
    #helper function    
    def verifyRouteCorrect(self,topologyJSON,endNode):
        command = SCTaskStatus(endNode)
          
        data = json.loads(topologyJSON)
        topology = data['network-topology']['data']
        
        route = command.findRoute(topology,command.endNode)
        lastNode = route[len(route)-1] 
        self.assertEquals(endNode,lastNode)
        
        return route
        
        

    def tearDown(self):
        pass         
            
        
