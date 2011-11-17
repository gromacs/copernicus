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


import unittest
from socket import gethostname
from cpc.util.conf.worker_conf import WorkerConf
import os
import shutil
import json



class TestWorkerConf(unittest.TestCase):
    
    
    def setUp(self):
        #check if the server conf dir exists 
        #remove it if it does
        self.confFile = 'worker/worker.conf'
        self.confBaseDir = ".copernicus-test"
        self.confDir = os.path.join(os.environ["HOME"],self.confBaseDir,gethostname())
         
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))
     
    
    
    '''tests to set up a default config file'''         
    def testInit(self):
        #init the server conf
        conf = WorkerConf(confdir = self.confDir)
        
        self.assertEquals(self.confFile,conf.get('conf_file'))
        self.assertEquals(self.confDir,conf.get('conf_dir'))
        

        portnr = '11111'
        conf.set("client_port",portnr)
        
        conf2 = WorkerConf(confdir = self.confDir)  #creating a new  instance reinitiates the config and reads parameters from config file  
        self.assertEquals(portnr,conf2.get('client_port'))
        
  
  
    def tearDown(self):
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))
