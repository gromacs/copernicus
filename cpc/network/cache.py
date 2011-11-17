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
import copy
#Singleton
#A simple cache that stores objects infinitely
log=logging.getLogger('cpc.server.cache')


class Cache(object):
    __shared_state = {}    
    def __init__(self):
        self.__dict__ = self.__shared_state
        
        if len(self.__shared_state)>0:
            return
        
        log.debug("instantiation of cache")
        self.cache = {}        
        
    def cleanAll(self):
        self.cache={}
        log.debug('cleaning all objects from cache')    
    #removes a specific cached instance
    def remove(self,key): 
        if key in self.cache:  
            log.debug('removing object %s from cache'%key)     
            del(self.cache[key])
    
    def getCache(self):
        return self.cache
    
    def add(self,key,value):  
        cacheVal = copy.deepcopy(value)
        log.debug('adding object %s to cache'%key)
        self.cache[key] = cacheVal    
    def get(self,key): 
        val = False
        if key in self.cache:
            val = self.cache[key]
        if val == False:
            log.debug('did not find object %s in cache'%key)
        else:
            log.debug('getting object %s from cache'%key)
        return copy.deepcopy(val)
    def size(self):
        return len(self.cache)
    
  
        
        
