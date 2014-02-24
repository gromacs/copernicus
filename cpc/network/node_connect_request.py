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
Created on May 25, 2011

@author: iman
'''

from cpc.network.node import Node
import logging
log=logging.getLogger(__name__)
class NodeConnectRequest(Node):
    '''
    classdocs
    '''


    def __init__(self,server_id
                 ,client_secure_port,
                 server_secure_port
                 ,key
                 ,qualified_name,hostname):

        Node.__init__(self,server_id
            ,client_secure_port
            ,server_secure_port
            ,qualified_name,hostname)
        self.key = key  #the public key of the server
            
