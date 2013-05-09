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


import logging
import socket
import os
from cpc.network.com.connection_base import ConnectionBase

import cpc.util
import cpc.util.log
from cpc.util.conf.client_conf import ClientConf
from cpc.network.https_connection_pool import *

log=logging.getLogger('cpc.client')

class CookieHandler(object):
    """Keeps cookies for the client. Loads and stores in a file"""
    def __init__(self, conf):
        self.conf = conf
        #establish cookie path
        self.cookiepath = os.path.join(conf.getGlobalDir(), 'clientcookies.dat')

    def getCookie(self):
        return ClientConf().getCookie()
        #if os.path.isfile(self.cookiepath):
        #    with open(self.cookiepath, 'r') as f:
        #        return f.read()


    def setCookie(self, cookie):
        ClientConf().setCookie(cookie)
        #with open(self.cookiepath, 'w') as f:
        #    f.write(cookie)
        #os.chmod(self.cookiepath, 0600)



class ClientConnectionBase(ConnectionBase):
    """
    Abstract base class for client connections, must be extended.
    """

    def prepareHeaders(self,request):
        if not request.headers.has_key('Originating-Client')\
        and not request.headers.has_key('originating-client'):
            request.headers['originating-client']=socket.getfqdn()

        #attempt to get cookie
        if not request.headers.has_key('cookie') and self.cookieHandler is not None:
            cookie = self.cookieHandler.getCookie()
            if cookie is not None:
                request.headers['cookie'] = cookie

        request.headers["Connection"]= "close"
        return request


    def handleResponseHeaders(self,response):
        cookie = response.getheader('set-cookie', None)
        if cookie is not None and self.cookieHandler is not None:
            self.cookieHandler.setCookie(cookie)

        return response


class VerifiedClientConnection(ClientConnectionBase):
    """
    HTTPS connections are verified both client and server side
    This one is used by the worker and the client
    """
    def __init__(self, conf):
        self.connected=False
        self.conf = conf
        self.cookieHandler = None # We disallow this for now

    def connect(self,host,port):

        self.host = host
        self.port = port
        privateKey = self.conf.getPrivateKey()
        keyChain = self.conf.getCaChainFile()
        cert = self.conf.getCertFile()

        log.log(cpc.util.log.TRACE,"Connecting VerHTTPS to host %s, port %s"%(
            self.host,self.port))
        self.conn = VerifiedHttpsConnection(self.host,
                                            self.port,
                                            privateKey,
                                            keyChain,
                                            cert)
        self.conn.connect()
        self.connected=True

    def handleSocket(self):
        pass

class UnverifiedClientConnection(ClientConnectionBase):
    """
    HTTPS connections are unverified, meaning no server side or client side
    verification is performed.
    """
    def __init__(self, conf, disable_cookies=False):
        self.connected=False
        self.conf = conf
        if not disable_cookies:
            self.cookieHandler = CookieHandler(conf)
        else:
            self.cookieHandler = None
    def connect(self,host,port):

        self.host = host
        self.port = port

        log.log(cpc.util.log.TRACE,"Connecting UnverHTTPS to host %s, port %s"%(
            self.host,self.port))
        self.conn = UnverifiedHttpsConnection(self.host,self.port)
        self.conn.connect()
        self.connected=True

    def handleSocket(self):
        pass