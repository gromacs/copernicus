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
import json
import logging
import copy
#Singleton
#A simple cache that stores objects infinitely
import threading
from cpc.util import json_serializer
import cpc.util.log

log=logging.getLogger(__name__)


class Cache(object):
    __shared_state = {}    
    def __init__(self):
        self.__dict__ = self.__shared_state
        
        if len(self.__shared_state)>0:
            return

        self.cacheLock = threading.Lock()
        log.log(cpc.util.log.TRACE,"instantiation of cache")
        self.cache = {}        
        
    def cleanAll(self):
        with self.cacheLock:
            self.cache={}
            log.log(cpc.util.log.TRACE,'cleaning all objects from cache')

    #removes a specific cached instance
    def remove(self,key):
        with self.cacheLock:
            if key in self.cache:
                log.log(cpc.util.log.TRACE,'removing object %s from cache'%key)
                del(self.cache[key])
    
    def getCache(self):
        with self.cacheLock:
            return self.cache
    
    def add(self,key,value):
        with self.cacheLock:
            log.log(cpc.util.log.TRACE,'adding object %s to cache'%key)
            self.cache[key] = value
    def get(self,key):
        """
        returns: the cacheobject if it exists, False otherwise
        """
        with self.cacheLock:
            val = False
            if key in self.cache:
                val = self.cache[key]
            if val == False:
                log.log(cpc.util.log.TRACE,'did not find object %s in cache'%key)
            else:
                log.log(cpc.util.log.TRACE,'getting object %s from cache'%key)
            return val
    def size(self):
        with self.cacheLock:
            return len(self.cache)


class NetworkTopologyCache(Cache):
    def __init__(self):
        Cache.__init__(self)
        self.cacheKey = "network-topology"


    def add(self,value):
        """
        inputs:
            value:Nodes
        """
        jsonStr = json.dumps(value,default = json_serializer.toJson,
            indent=4)
        Cache.add(self,self.cacheKey,jsonStr)

    def get(self):
        """
        returns:
            Nodes
        """
        jsonStr = Cache.get(self,self.cacheKey)
        if jsonStr:
            topology = json.loads(jsonStr,
                object_hook=json_serializer.fromJson)
            return topology
        else:
            return False

    def remove(self):
        Cache.remove(self,self.cacheKey)


