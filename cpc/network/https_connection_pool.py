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
from Queue import Queue,Empty
import threading
from cpc.util.conf.server_conf import ServerConf

import cpc.util.log
from cpc.network.https.real_https_connection import *
#Singleton
log=logging.getLogger(__name__)

class ConnectionPoolEmptyError(CpcError):
    def __init__(self, exc):
        self.str = exc.__str__()


#the only thing that differs between ServerConnectionPool and ConnectionPool
#is that ServerConnectionPool is using server-id as keys

class ConnectionPool(object):

    def __init__(self):
        log.log(cpc.util.log.TRACE,"instantiation of connectionPool")
        self.pool = {}
        self.listlock=threading.Lock()

    #tries to see if there exists a connection for the host, if not it creates one and returns it

    def getKey(self,host,port):
        return "%s:%s"%(host,port)


    def getConnection(self,host,port):

        #check if we have a queue instantiated for that host
        with self.listlock:
            q = self.getOrCreateQueue(host,port)
        try:
            #we wait to until we get hold of a connection,
            # if we do not get a connection after timeout then all available
            # connections must have died.
            connection = q.get(block=True,timeout=15)
            log.log(cpc.util.log.TRACE,"Got a connection from pool for "
                                       "host:%s:%s"%(host,port))

        except Empty as e:
            log.log(cpc.util.log.TRACE,"No connections available in pool for "
                                       "host:%s:%s"%(host,port))
            raise ConnectionPoolEmptyError(e)

        return connection

    def getAllConnections(self,host,port):
        connections = []
        #check if we have a queue instantiated for that host
        with self.listlock:
            q = self.getOrCreateQueue(host,port)

            #we try yo get all available connections from the pool
            while not q.empty():
                connections.append(q.get())

            if len(connections)==0:
                log.log(cpc.util.log.TRACE,"No connections available in pool for "
                                       "host:%s:%s"%(host,port))
                raise ConnectionPoolEmptyError("No connections available in pool for "
                                           "host:%s:%s"%(host,port))

            return connections



    def putConnection(self,connection,host,port):
        #create a queue in case we dont have one
        self.getOrCreateQueue(host,port)
        key = self.getKey(host, port)
        with self.listlock:
            self.pool[key].put(connection,False)
            log.log(cpc.util.log.TRACE,"put back connection in pool for host:%s:%s"%(host,port))


    def getOrCreateQueue(self,host,port):
        key = self.getKey(host, port)
        if key not in self.pool:
            log.log(cpc.util.log.TRACE,"Instantiating server https "
                                       "connection pool for host:%s:%s"%(host,port))
            q =  Queue()
            self.pool[key] = q
        else:
            q= self.pool[key]

        return q

class ServerConnectionPool(ConnectionPool):
    """
    Singleton that keeps a pool of https connections that does verification.
    Thea idea is that connections to a given host/port, once, established,
    can be reused.
    Only writable sockets are stored here
    """
    __shared_state = {}
    def __init__(self):
        self.__dict__ = self.__shared_state

        if len(self.__shared_state)>0:
            return

        ConnectionPool.__init__(self)
        log.log(cpc.util.log.TRACE,"instantiation of Server connection pool")


    #tries to see if there exists a connection for the host, if not it creates one and returns it

    def getConnection(self,node):
        return ConnectionPool.getConnection(self,node.getHostname()
                                            ,node.getServerSecurePort())


    def getAllConnections(self,node):
        return ConnectionPool.getAllConnections(self,node.getHostname()
            ,node.getServerSecurePort())

    def putConnection(self,connection,node):
        after_idle_sec = 1
        interval_sec = 3
        max_fails = 5

        #TODO do a getpeername
        #TODO update the socket contents with getpeername
        #TODO set sockets keep alives
         #connection.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
#        connection.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
#        connection.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
#        connection.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)
        ConnectionPool.putConnection(self,connection,node.getHostname(),
           node.getServerSecurePort())
