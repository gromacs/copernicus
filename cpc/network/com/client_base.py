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


import httplib
import socket
import logging
import cpc.util.log
import client_connection
from cpc.util import CpcError
'''
Created on Mar 10, 2011

@author: iman
'''
log=logging.getLogger(__name__)

class ClientConnectionError(CpcError):
    def __init__(self, exc,host,port):
        self.host = host
        self.port = port
        #check the
        self.exceptionStr = exc.__str__()
#        self.str = exc.__str__()
        self.str="%s \n %s"%(self.exceptionStr,self.explainError())
    def explainError(self):
        return "\nThis usually means that a connection could not be " \
               "established, In this case a connection to %s on port %s " \
               "failed. Possible causes are: \n1. The hostname does not " \
               "exist.\n2. The specified port number is wrong \n3. The " \
               "remote host is not accepting a connection from you \n" \
               "4. The remote host is down." \
               %(self.host,self.port)


class ClientBase(object):
    '''
    classdocs
    '''


    def __init__(self,host,port,conf):
        """Connect to a server opening a connection
           a privatekey and an keychain is needed if a https connection
           is established

           @param self.conn ClientConnectionBase
        """        
        self.host = host
        self.port = port
        self.conf = conf
        self.require_certificate_authentication = None

    def putRequest(self, req, require_certificate_authentication=None, disable_cookies=False):
        self.__connect(require_certificate_authentication, disable_cookies)
        try:

            ret=self.conn.sendRequest(req,"PUT")
        except httplib.HTTPException as e:
            raise ClientConnectionError(e,self.host,self.port)
        except socket.error as e:
            raise ClientConnectionError(e,self.host,self.port)
        return ret

    def postRequest(self, req, require_certificate_authentication=None, disable_cookies=False):
        self.__connect(require_certificate_authentication, disable_cookies)
        try:
            ret=self.conn.sendRequest(req)
        except httplib.HTTPException as e:
            raise ClientConnectionError(e,self.host,self.port)
        except socket.error as e:
            raise ClientConnectionError(e,self.host,self.port)
        return ret

    def closeClient(self):
        self.conn.conn.close()

    # the order in which we determine whether to require certificate from server for authentication is
    # 1, overrides lower priorities : argument require_certificate_authentication
    # 2, if self.require_certificate_authentication is set
    # default to true
    def __connect(self, require_certificate_authentication=None, disable_cookies=False):

        '''
        inputs:
             require_certificate_authentication:boolean  requires a certificate from the server
        '''
        if require_certificate_authentication is not None:
            require_certificate_authentication = require_certificate_authentication
        else:
            try:
                if self.require_certificate_authentication is not None:
                    require_certificate_authentication = self.require_certificate_authentication
                else:
                    require_certificate_authentication = True
            except AttributeError:
                require_certificate_authentication = True
        try:
            if require_certificate_authentication:
                log.log(cpc.util.log.TRACE,"Connecting HTTPS with cert authentication")
                self.conn=client_connection.ClientConnectionRequireCert(self.conf)
            else:
                log.log(cpc.util.log.TRACE,"Connecting HTTPS with no cert authentication")
                self.conn=client_connection.ClientConnectionNoCertRequired(
                            self.conf, disable_cookies)
            self.conn.connect(self.host,self.port)
        except httplib.HTTPException as e:
            raise ClientConnectionError(e,self.host,self.port)
        except socket.error as e:
            raise ClientConnectionError(e,self.host,self.port)
