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
Created on Jul 18, 2011

@author: iman
'''
import logging
from Queue import Queue,Empty,Full
import threading
import httplib
import cpc.util.log
from cpc.network.https.real_https_connection import RealHttpsConnection
#Singleton
log=logging.getLogger('cpc.server.https_connection_pool')


class HTTPSConnectionPool(object):
    __shared_state = {}    
    def __init__(self):
        self.__dict__ = self.__shared_state
        
        if len(self.__shared_state)>0:
            return
        
        log.log(cpc.util.log.TRACE,"instantiation of connectionPool")
        self.pool = {}        
        self.listlock=threading.Lock()
        
    #tries to see if there exists a connection for the host, if not it creates one and returns it
    
    def getKey(self,host,port):
        return "%s:%s"%(host,port)
        
          
    def getConnection(self,host,port,privateKeyFile,keyChain,cert):
        key = self.getKey(host, port)
        #check if we have a queue instantiated for that host
        with self.listlock:
            if key not in self.pool:
                log.log(cpc.util.log.TRACE,"instantiating connection pool for host:%s:%s"%(host,port))
                q =  Queue()
                self.pool[key] = q
            else: 
                q= self.pool[key]
        try:
            connection = q.get(False)
            log.log(cpc.util.log.TRACE,"got a connection from pool form host:%s:%s"%(host,port))
            #do we need to check if the connection dropped here?
            
        except Empty:
            log.log(cpc.util.log.TRACE,"no connections in pool for host:%s:%s creating a new one"%(host,port))
#
            connection = RealHttpsConnection(host,port,privateKeyFile,keyChain,cert)          
        return connection
    
    def putConnection(self,connection,host,port):
        key = self.getKey(host, port)
        with self.listlock:
            self.pool[key].put(connection,False)
            log.log(cpc.util.log.TRACE,"put back connection in pool for host:%s:%s"%(host,port))
        
