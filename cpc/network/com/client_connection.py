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
from cpc.network.com.client_response import ClientResponse
from cpc.network.https_connection_pool import HTTPSConnectionPool
import cpc.util.log

log=logging.getLogger('cpc.client')


class ClientError(cpc.util.CpcError):
    def __init__(self, exc):
        self.str=exc.__str__()
#    def __str__(self):
#        return self.desc

class ClientConnection:
    def __init__(self):
        """Connect as a client to a server, or spawn one if neccesary"""
        self.connected=False
        self.httpsConnectionPool = HTTPSConnectionPool()        

    def connect(self,host,port,conf,https=True):
        
        self.host = host
        self.port = port
        privateKey = conf.getPrivateKey()
        keyChain = conf.getCaChainFile()
        cert = conf.getCertFile()
        
        if https:   
            log.log(cpc.util.log.TRACE,"Connecting HTTPS to host %s, port %s"%(self.host,self.port))
            self.conn = self.httpsConnectionPool.getConnection(self.host,
                                                self.port,
                                                privateKey,
                                                keyChain,
                                                cert)
            
                                                      
        else:
            log.log(cpc.util.log.TRACE,"Connecting HTTP to host %s, port %s"%(host,port))
            self.conn = httplib.HTTPConnection(self.host,self.port)
            
        self.conn.connect()
        self.connected=True
        

    def sendRequest(self,req,method="POST"):
        if not req.headers.has_key('Originating-Client') \
              and not req.headers.has_key('originating-client'):
            req.headers['originating-client']=socket.getfqdn()
        self.conn.request(method, "/copernicus",req.msg,req.headers)
                
        response=self.conn.getresponse()

        if response.status!=200:       
            errorStr = "ERROR: %d: %s"%(response.status, response.reason)
            resp_mmap = mmap.mmap(-1, int(len(errorStr)), mmap.ACCESS_WRITE)      
            resp_mmap.write(errorStr)
        
        else:
            headers=response.getheaders()
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
   
    
   

