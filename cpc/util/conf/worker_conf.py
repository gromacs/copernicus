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
Created on Apr 11, 2011

@author: iman
'''
from cpc.util.conf.conf_base import Conf  
import os
class WorkerConf(Conf):
    '''
    classdocs
    '''
    __shared_state = {}
    CN_ID = "worker"  #used to distinguish common names in certs
    def __init__(self,conffile='worker.conf',confdir=None,reload=False):


        self.__dict__ = self.__shared_state                  
        if len(self.__shared_state)>0 and reload == False:             
            return;
        
        Conf.__init__(self, conffile, confdir)        
                
        self._add("conf_dir",os.path.join(self.get("conf_dir"),"worker"), 'The configuration directory',
                  userSettable=True)
        self.client_host = '0.0.0.0'
        self.client_https_port = '13807'
        self.client_http_port = '14807'
        self.initDefaults()
                
        
        self.tryRead()
        

    def initDefaults(self):
        Conf.initDefaults(self)
        self._add('client_host', self.client_host, 
                  "Hostname for the client to connect to", True)
        self._add('client_http_port', self.client_http_port, 
                  "Port number for the client to connect to http", True,None,'\d+')
        self._add('client_https_port', self.client_https_port, 
                  "Port number for the client to connect to https", True,None,'\d+')
        self._add('run_dir', os.path.join(os.environ["HOME"],
                                  "copernicus",
                                  "run"),
          "The run directory for the run client",
          True)


    def getClientHost(self):
        return self.conf['client_host'].get()

    def getClientHTTPSPort(self):
        return int(self.conf['client_https_port'].get())
    
    def getClientHTTPPort(self):
        return int(self.conf['client_http_port'].get())    
    def getRunDir(self):
        return self.getFile('run_dir')
    
