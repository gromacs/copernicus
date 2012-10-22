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


from cpc.util import CpcError
import httplib
import socket
import client_connection

'''
Created on Mar 10, 2011

@author: iman
'''

class ClientError(CpcError):
    def __init__(self, exc):
        self.str=exc.__str__()

class ClientBase(object):
    '''
    classdocs
    '''


    def __init__(self,host,port,conf):
        """Connect to a server opening a connection
           a privatekey and an keychain is needed if a https connection
           is established
        """        
        self.host = host
        self.port = port
        self.conf = conf
                

    def putRequest(self, req,https=True):
        self.connect(https)
        try:
            ret=self.conn.sendRequest(req,"PUT")
        except httplib.HTTPException as e:
            raise ClientError(e)
        except socket.error as e:
            raise ClientError(e)
        return ret

    def postRequest(self,req,https=True):
        self.connect(https)
        try:
            ret=self.conn.sendRequest(req)
        except httplib.HTTPException as e:
            raise ClientError(e)
        except socket.error as e:
            raise ClientError(e)
        return ret

    def closeClient(self):
        self.conn.conn.close()

    #FIXME private method
    def connect(self,https=True):
        try:
            self.conn=client_connection.ClientConnection(self.conf)
            self.conn.connect(self.host,self.port,https)
        except httplib.HTTPException as e:
            raise ClientError(e)
        except socket.error as e:
            raise ClientError(e)
