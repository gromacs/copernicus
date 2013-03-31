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
Created on Feb 1, 2011

@author: iman
'''
from cpc.util.conf.server_conf import ServerConf
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
import unittest
import time
import subprocess
import os
from genericpath import isdir
import shutil
from cpc.util.openssl import OpenSSL
#TODO make runnable from command line


#NOT a unit test this is a regression test using the unit testing framework
class HTTPRequestTest(unittest.TestCase):
 
 
    def setUp(self):
        self.testConfPath = os.path.join(os.environ["HOME"], ".cpc/test") 
        if isdir(self.testConfPath):
            shutil.rmtree(self.testConfPath)
        
        
        self.serverConfs = dict()
            
            
        os.makedirs(self.testConfPath)
        pass
    def testStartServer(self):    
        
        self.createConfFolder(0)
            
        args = ['../../../../cpc','-c',self.serverConfs[0],'start']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
        subprocess.call(args)
           
        time.sleep(2)
        conf = ServerConf(self.serverConfs[0],True)
        
        #create a custom request message that sends a file and a parameter
        #verifty 
        
        client = ClientMessage()
        ProcessedResponse(client.pingServer()).pprint()
        client.closeClient()
             
    
    def createConfFolder(self,name):
        path = os.path.join(os.environ["HOME"], ".cpc/test",str(name))
        os.makedirs(path)        
        self.serverConfs[name] = path
        conf = ServerConf(path,True)
        OpenSSL(conf).setupServer()
         

    def tearDown(self):        
        for i in range(len(self.serverConfs)):
            args = ['../../../../cpc','-c',self.serverConfs[i],'stop']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown 
            subprocess.call(args)
    
if __name__ == "__main__":
    unittest.main()     
