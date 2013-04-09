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
import mmap
import logging
import socket
import cpc.util
import os
from cpc.network.com.client_response import ClientResponse
from cpc.util.conf.client_conf import ClientConf
from cpc.network.https_connection_pool import *
import cpc.util.log

log=logging.getLogger('cpc.client')


class ClientError(cpc.util.CpcError):
    def __init__(self, exc):
        self.str=exc.__str__()
#    def __str__(self):
#        return self.desc

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


class ClientConnectionBase(object):
    """
    Base class for client connections, must be extended.
    """

    def connect(self,host,port):
        raise NotImplementedError("Not implemented by subclass")
        

    def sendRequest(self,req,method="POST"):
        if not req.headers.has_key('Originating-Client') \
              and not req.headers.has_key('originating-client'):
            req.headers['originating-client']=socket.getfqdn()

        #attempt to get cookie
        if not req.headers.has_key('cookie') and self.cookieHandler is not None:
            cookie = self.cookieHandler.getCookie()
            if cookie is not None:
                req.headers['cookie'] = cookie

        self.conn.request(method, "/copernicus",req.msg,req.headers)
                
        response=self.conn.getresponse()

        if response.status!=200:       
            errorStr = "ERROR: %d: %s"%(response.status, response.reason)
            resp_mmap = mmap.mmap(-1, int(len(errorStr)), mmap.ACCESS_WRITE)      
            resp_mmap.write(errorStr)
        
        else:
            headers=response.getheaders()
            cookie = response.getheader('set-cookie', None)
            if cookie is not None and self.cookieHandler is not None:
                self.cookieHandler.setCookie(cookie)
            for (key,val) in headers:
                log.log(cpc.util.log.TRACE,"Got header '%s'='%s'"%(key,val))
            length=response.getheader('content-length', None)
            if length is None:
                length=response.getheader('Content-Length', None)
            if length is None:
                raise ClientError("response has no length")
            log.log(cpc.util.log.TRACE,"Response length is %s"%(length))

            resp_mmap = mmap.mmap(-1, int(length), access=mmap.ACCESS_WRITE)
            
            # TODO: read in chunks
            resp_mmap.write(response.read(length))
        

        resp_mmap.seek(0)
        headerTuples = response.getheaders()
        
        headers = dict()
        
        for (header,value) in headerTuples:
            headers[header] = value           
        
        #TODO put back connection in the pool
        if(self.conn.__class__.__name__ == "HTTPSConnection"):
            self.httpsConnectionPool.putConnection(self.conn,self.host,self.port)
                              
        return ClientResponse(resp_mmap,headers)




class VerifiedClientConnection(ClientConnectionBase):
    """
    HTTPS connections are verified both client and server side
    """
    def __init__(self, conf):
        self.httpsConnectionPool = VerifiedHTTPSConnectionPool()
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
        self.conn = self.httpsConnectionPool.getConnection(self.host,
                                                               self.port,
                                                               privateKey,
                                                               keyChain,
                                                               cert)

        self.conn.connect()
        self.connected=True

class UnverifiedClientConnection(ClientConnectionBase):
    """
    HTTPS connections are unverified, meaning no server side or client side
    verification is performed.
    """
    def __init__(self, conf):
        self.httpsConnectionPool = UnverifiedHTTPSConnectionPool()
        self.connected=False
        self.conf = conf
        self.cookieHandler = CookieHandler(conf)

    def connect(self,host,port):

        self.host = host
        self.port = port

        log.log(cpc.util.log.TRACE,"Connecting UnverHTTPS to host %s, port %s"%(
            self.host,self.port))
        self.conn = self.httpsConnectionPool.getConnection(self.host,
                                                               self.port)
        self.conn.connect()
        self.connected=True
