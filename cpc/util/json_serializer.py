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
helper module to serialize classes into json objects
'''
from cpc.network.node import Node
from cpc.network.node import Nodes
from cpc.network.node_connect_request import NodeConnectRequest
from cpc.util.worker_state import WorkerState
def toJson(obj):       
    if isinstance(obj,Nodes):        
        return {'class':'Nodes',
                 'nodes':obj.nodes   
               }
    
    #NodeConnectRequest inherits from node this always instance of Node. we have to have this 
    #if clause before checking if object is NODE !!!    
    if isinstance(obj,NodeConnectRequest):
        return {'class' : 'NodeConnectRequest',
                 'host' : obj.host,
                 'unverified_https_port' : obj.unverified_https_port,
                 'verified_https_port' : obj.verified_https_port,
                 'key'  : obj.key,
                 'qualified_name':obj.qualified_name
               }
    
    if isinstance(obj,Node):
        return {'class' : 'Node',
                 'host' : obj.host,                 
                 'unverified_https_port' : obj.unverified_https_port,
                 'verified_https_port' : obj.verified_https_port,
                 'nodes':obj.nodes,
                 'priority':obj.priority,
                 'workerStates':obj.workerStates,
                 'qualified_name':obj.qualified_name
               }
    
    if isinstance(obj,WorkerState):
        return {'class' : 'WorkerState',
                 'host' : obj.host,                 
                 'workerId' : obj.workerId,
                 'id':obj.id,
                 'state':obj.state
               }
    
    raise TypeError(repr(obj)+ ' is not JSON serializable')
    
    
    
def fromJson(jsonObj):
    if 'class' in jsonObj:        
        if jsonObj['class'] == 'Node':
            node = Node(jsonObj['host'],
                        int(jsonObj['unverified_https_port']),
                        int(jsonObj['verified_https_port']),
                        jsonObj['qualified_name'])            
            if "nodes" in jsonObj:
                node.nodes = jsonObj['nodes'] 
            if "priority" in jsonObj:
                node.priority = jsonObj['priority']
            if "workerStates" in jsonObj:
                node.workerStates = jsonObj['workerStates']
            return node
        
        if jsonObj['class'] == 'WorkerState':
            return WorkerState(jsonObj['host'],jsonObj['state'])
        
        if jsonObj['class'] == 'Nodes':
            nodes = Nodes()
            for node in jsonObj['nodes'].itervalues():                
                nodes.addNode(node)
            return nodes
        
        if jsonObj['class'] == 'NodeConnectRequest':
            return NodeConnectRequest(jsonObj['host'],
                                      jsonObj['unverified_https_port'],
                                      jsonObj['verified_https_port'], 
                                      jsonObj['key'],
                                      jsonObj['qualified_name'])
        
    return jsonObj
