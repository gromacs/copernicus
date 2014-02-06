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
import logging
from cpc.network.node import Node
from cpc.network.node import Nodes
from cpc.network.node_connect_request import NodeConnectRequest
from cpc.util.worker_state import WorkerState

log=logging.getLogger(__name__)

def toJson(obj):
    if isinstance(obj,Nodes):
        return {'class':'Nodes',
                 'nodes':obj.nodes   
               }
    
    #NodeConnectRequest inherits from node this always instance of Node. we have to have this 
    #if clause before checking if object is NODE !!!
    if isinstance(obj,NodeConnectRequest):
        return {'class' : 'NodeConnectRequest',
                 'server_id' : obj.server_id,
                 'client_secure_port' : obj.getClientSecurePort(),
                 'server_secure_port' : obj.getServerSecurePort(),
                 'key'  : obj.key,
                 'qualified_name':obj.getQualifiedName(),
                 'hostname':obj.getHostname()
               }

    if isinstance(obj,Node):
        return {'class' : 'Node',
                 'server_id' : obj.server_id,
                 'client_secure_port' : obj.getClientSecurePort(),
                 'server_secure_port' : obj.getServerSecurePort(),
                 'nodes':obj.getNodes(),
                 'priority':obj.getPriority(),
                 'workerStates':obj.workerStates,
                 'qualified_name':obj.getQualifiedName(),
                 'hostname':obj.getHostname()
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
            node = Node(jsonObj['server_id'],
                        int(jsonObj['client_secure_port']),
                        int(jsonObj['server_secure_port']),
                        jsonObj['qualified_name'],
                        jsonObj['hostname'])
            if "nodes" in jsonObj:
                node.setNodes(jsonObj['nodes'])
            if "priority" in jsonObj:
                node.setPriority(jsonObj['priority'])
            if "workerStates" in jsonObj:
                node.workerStates = jsonObj['workerStates']
            return node
        
        if jsonObj['class'] == 'WorkerState':
            return WorkerState(jsonObj['host'],jsonObj['state'],jsonObj['workerId'])
        
        if jsonObj['class'] == 'Nodes':
            nodes = Nodes()
            for node in jsonObj['nodes'].itervalues():                
                nodes.addNode(node)
            return nodes
        
        if jsonObj['class'] == 'NodeConnectRequest':
            return NodeConnectRequest(jsonObj['server_id'],
                                      jsonObj['client_secure_port'],
                                      jsonObj['server_secure_port'],
                                      jsonObj['key'],
                                      jsonObj['qualified_name'],
                                      jsonObj['hostname'])
    return jsonObj
