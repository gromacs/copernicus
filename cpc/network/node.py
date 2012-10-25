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
Created on Feb 2, 2011

@author: iman
'''
from operator import itemgetter
import threading
import logging

log=logging.getLogger('cpc.network.node')

selfNode=None
selfNodeLock=threading.Lock()

class Nodes(object):
    def __init__(self):
        self.nodes = dict()
    
    #adds a node and gives it the least priority            
    def addNode(self,node):
        key = node.getId()
        self.nodes[key] = node
        self.changePriority(node.getId(),None)
        

    def removeNode(self,id):
        key = id
        if key in self.nodes:
            del self.nodes[key]
     
    def exists(self,id):
        key = id
        if key in self.nodes:
            return True
        else:
            return False
        
    def existsWithId(self,id):
        key = id
        if key in self.nodes:
            return True
        else:
            return False      
    def get(self,id):
        return self.nodes[id]
    def size(self):
        return len(self.nodes)
    #@return array with Node objects in priority order
    def getNodesByPriority(self):
        return sorted(self.nodes.values(),key=lambda node:node.priority)
    
    #change the priority of a node that already exists in the dictionary
    # the inputted priority is not the number that the node will get finally it will be a 
    # value 100 on a list with 3 elems will mean last thus the priority of that node will be calculated to 4
    # inputting None will ensure the node will have least priority
    #@param id nodeId 
    def changePriority(self,id,priority = None):                
        if self.existsWithId(id):
            
            node = self.get(id)   # we get the actual node to ensure that no other params are changed
            
            self.removeNode(node.getId())
            
            list = self.getNodesByPriority()
            if priority == None:
                list.append(node)
            else:
                list.insert(priority,node)
            
            for i in range(len(list)):
                list[i].priority = i
                self.nodes[list[i].getId()] = list[i]
            
        
    
    #@param start:a Node Object
    #param end: a Node Object
    #param topology: a Nodes object     
    @staticmethod
    def findRoute(start,end,topology):
        # Dijkstras algorithm , we might need to change this once we need prioority based routing
        #log.log(cpc.util.log.TRACE,"finding route %s %s"%(start,end))
        #log.log(cpc.util.log.TRACE,"topology is %s"%topology)

        distances = dict()
        previous = dict()  #key is a node values is a node visited prior

        distances[start.getId()] = 0
        
        while topology.size()>0:                    
            #find node that has the shortest distance and exists in topology
            ds = sorted(distances.items(), key=itemgetter(1)) #returns a list of tuples (nodename,distance)
            
            for elem in ds:
                nodeId = elem[0]
                if topology.existsWithId(nodeId):
                    currentNode = topology.get(nodeId)
                    break           
            
            
            topology.removeNode(currentNode.getId())
            
            # if we have found the end node
            if currentNode.getId() == end.getId():  
                route = []
                n = end
                while n.getId() in previous:                    
                    route.append(n)
                    n = previous[n.getId()]
                route.append(start)
                route.reverse()               
                return route                   
                # we have a route
                
                
            for neighborNode in currentNode.nodes.nodes.itervalues():
                # neighbournodes have backreferences that we are not interested in
                # also they do not exist in the topology as we are removing nodes as we traverse
                if topology.exists(neighborNode.getId()):                
                    tmpDistance = distances[currentNode.getId()] + 1  # 1 is the distance between each node for now
                    if neighborNode.getId() in distances:
                        if  tmpDistance< distances[neighborNode.getId()]:
                            distances[neighborNode.getId()] = tmpDistance
                            previous[neighborNode.getId()] = currentNode
                    else:
                        distances[neighborNode.getId()] = tmpDistance;
                        previous[neighborNode.getId()] = currentNode
        
        
        return []  #no route found
        
    
#small object used in config context
class Node(object):

    def __init__(self,host,http_port,https_port,qualified_name):
        self.host = host #this name is what we use to connect to the node
        self.qualified_name = qualified_name  # this name is the unique fully qualified domain name of the server
        self.http_port = http_port
        self.https_port = https_port
        self.priority = None
        self.nodes = Nodes()
        self.workerStates = dict()  #workers connected to this node
        
    def getId(self):
        #return '%s:%s'%(self.qualified_name,self.https_port)
        return '%s'%(self.qualified_name)


def getSelfNode(conf):
    """Return the 'self' node."""
    global selfNode, selfNodeLock
    with selfNodeLock:
        if selfNode is None:
            selfNode=Node(conf.getHostName(),
                          conf.getServerHTTPPort(),
                          conf.getServerVerifiedHTTPSPort(),
                          conf.getHostName())
    return selfNode

