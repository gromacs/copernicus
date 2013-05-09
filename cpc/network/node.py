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
from cpc.util import CpcError

log=logging.getLogger('cpc.network.node')

class ValueLessThanZeroException(Exception):
    pass

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

    def hostnameOrFQDNExists(self,hostname):
        for node in self.nodes.itervalues():
            if node.getHostname()==hostname or node.getQualifiedName() == hostname:
                return True

        return False

    def exists(self,id):
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
        return sorted(self.nodes.values(),key=lambda node:node.getPriority())

    #change the priority of a node that already exists in the dictionary
    # the inputted priority is not the number that the node will get finally it will be a 
    # value 100 on a list with 3 elems will mean last thus the priority of that node will be calculated to 4
    # inputting None will ensure the node will have least priority
    #@param id nodeId 
    def changePriority(self,id,priority = None):
        if self.exists(id):

            node = self.get(id)   # we get the actual node to ensure that no other params are changed

            self.removeNode(node.getId())

            list = self.getNodesByPriority()
            if priority == None:
                list.append(node)
            else:
                list.insert(priority,node)

            for i in range(len(list)):

                list[i].setPriority(i)
                self.nodes[list[i].getId()] = list[i]



    #@param start:a Node Object
    #param end: a Node Object
    #param topology: a Nodes object     
    @staticmethod
    def findRoute(start,end,topology):
        # Dijkstras algorithm , we might need to change this once we need prioority based routing

        distances = dict()
        previous = dict()  #key is a node values is a node visited prior

        distances[start.getId()] = 0

        while topology.size()>0:
        #find node that has the shortest distance and exists in topology
            #A list of tuples (nodename,distance)
            ds = sorted(distances.items(), key=itemgetter(1))

            for elem in ds:
                nodeId = elem[0]
                if topology.exists(nodeId):
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


            for neighborNode in currentNode.getNodes().nodes.itervalues():
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


class Node(object):
    STATUS_CONNECTED_OUTBOUND = "NODE_CONNECTED_OUTBOUND"
    STATUS_CONNECTED_INBOUND = "NODE_CONNECTED_INBOUND"
    STATUS_CONNECTED = "NODE_CONNECTED"
    STATUS_UNREACHABLE = "NODE_UNREACHABLE"
    STATUS_UNKNOWN = "UNKOWN"
    def __init__(self,server_id,unverified_https_port,verified_https_port,
                 qualified_name,hostname):
        """
        Node objects hold information about how to connect to each trusted
        server,
        Each server holds a collection of node objects for all servers that
        it trusts.


        inputs:
         server_id:String               The unique server id
         unverified_https_port:String   The client connection port
         verified_https_port:String     The server connection port
         qualified_name:String          qualified_name: the address of the
                                        node as known by itself.
         hostname:String                The address to this node as known by
                                        the server holding the node object.
                                        This is adress we primarily try to
                                        connect to
        """

        self.server_id = server_id
        # node
        self.__qualified_name = qualified_name
        self.__unverified_https_port = unverified_https_port
        self.__verified_https_port = verified_https_port
        self.__hostname = hostname
        self.__priority = None
        self.__nodes = Nodes()

        #transient properties. These should not be persisted to file
        self.workerStates = dict()  #workers connected to this node
        #TODO make private
        self.status = Node.STATUS_UNKNOWN
        self.__connectedInbound = False
        self.__connectedOutbound = False
        self.lock = threading.Lock()

        #Incoming connections are always alive and active in a request
        # handling loop, When that loop is initiated the first time we
        # increment this value, when that loop is closed and socket shutdown
        # we decrement this
        self.__numConnectedInbound = 0
        self.__numConnectedOutbound = 0

    def __setConnectedInbound(self,bool):
        '''
        Private method to be only called by methods that are wrapped with locks
        '''

        self.__connectedInbound = bool
        if self.__connectedInbound and self.__connectedOutbound:
            self.status = Node.STATUS_CONNECTED
        elif not (self.__connectedInbound or self.__connectedOutbound):
            self.status = Node.STATUS_UNREACHABLE
        else:
            self.status = Node.STATUS_CONNECTED_INBOUND

    def __setConnectedOutbound(self,bool):
        '''
        Private method to be only called by methods that are wrapped with locks
        '''
        self.__connectedOutbound = bool
        if self.__connectedInbound and self.__connectedOutbound:
            self.status = Node.STATUS_CONNECTED
        elif not (self.__connectedInbound or self.__connectedOutbound):
            self.status = Node.STATUS_UNREACHABLE
        else:
            self.status = Node.STATUS_CONNECTED_OUTBOUND

    def isConnectedInbound(self):
        with self.lock:
            return self.__connectedInbound

    def isConnectedOutbound(self):
        with self.lock:
            return self.__connectedOutbound

    def isConnected(self):
        """
           Checks if node status is set to STATUS_CONNECTED i.e we have both
           inbound and outbound connections
        """
        with self.lock:
            if self.status == Node.STATUS_CONNECTED:
                return True
            else:
                return False
    def getId(self):
        return self.server_id


    def setQualifiedName(self,qualifiedName):
        with self.lock:
            self.__qualified_name = qualifiedName

    def getQualifiedName(self):
        with self.lock:
            return self.__qualified_name


    def getUnverifiedHttpsPort(self):
        with self.lock:
            return self.__unverified_https_port

    def setUnverifiedHttpsPort(self,unverifiedHttpsPort):
        with self.lock:
            self.__unverified_https_port = unverifiedHttpsPort

    def getVerifiedHttpsPort(self):
        with self.lock:
            return self.__verified_https_port

    def setVerifiedHttpsPort(self, verifiedHttpsPort):
        with self.lock:
            self.__verified_https_port = verifiedHttpsPort

    def getHostname(self):
        with self.lock:
            return self.__hostname

    def setHostname(self,hostname):
        with self.lock:
            self.__hostname = hostname


    def getPriority(self):
        with self.lock:
            return self.__priority

    def setPriority(self,priority):
        with self.lock:
            self.__priority = priority

    def getNodes(self):
        with self.lock:
            return self.__nodes

    def setNodes(self,nodes):
        '''
        input:
        nodes:Nodes
        '''
        with self.lock:
            self.__nodes =nodes


    def addInboundConnection(self):
        with self.lock:
            self.__numConnectedInbound+=1
            #only need to set it the first time
            if self.__numConnectedInbound==1:
                self.__setConnectedInbound(True)

    def reduceInboundConnection(self):
        with self.lock:
            self.__numConnectedInbound-=1
            if self.__numConnectedInbound==0:
                self.__setConnectedInbound(False)

            if self.__numConnectedInbound<0:
                raise ValueLessThanZeroException("number of inbounf "
                                                 "connections is less than "
                                                 "zero")

    def addOutboundConnection(self):
        with self.lock:
            self.__numConnectedOutbound+=1
            #only need to set it the first time
            if self.__numConnectedOutbound==1:
                self.__setConnectedOutbound(True)

    def reduceOutboundConnection(self):
        with self.lock:
            self.__numConnectedOutbound-=1
            #only need to set it the first time
            if self.__numConnectedOutbound==0:
                self.__setConnectedOutbound(False)

            if self.__numConnectedOutbound<0:
                raise ValueLessThanZeroException("number of outbound "
                                                 "connections is less than "
                                                 "zero")


    def getNumInboundConnections(self):
        with self.lock:
            return self.__numConnectedOutbound

    def getNumOutboundConnections(self):
        with self.lock:
            return self.__numConnectedOutbound

    def toString(self):
        with self.lock:
            return "%s(%s:%s)"%(self.server_id,self.__hostname,
                                self.__verified_https_port)

    @staticmethod
    def getSelfNode(conf):
        """Return the 'self' node."""
        global selfNode, selfNodeLock
        with selfNodeLock:
            if selfNode is None:
                selfNode=Node(conf.getServerId(),
                    conf.getServerUnverifiedHTTPSPort(),
                    conf.getServerVerifiedHTTPSPort(),
                    conf.getFqdn(),
                    conf.getHostName())
        return selfNode

