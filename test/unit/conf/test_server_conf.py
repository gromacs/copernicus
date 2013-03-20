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
from cpc.util.conf.server_conf import ServerConf
import os
import shutil
import json



class TestServerConf(unittest.TestCase):
    
    
    def setUp(self):
        #check if the server conf dir exists 
        #remove it if it does
        self.confFile = 'server/server.conf'
        self.confBaseDir = ".copernicus-test"
        self.confDir = os.path.join(os.environ["HOME"],self.confBaseDir,gethostname())
         
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))
     
    
    
    '''tests to set up a default config file'''         
    def testInit(self):
        #init the server conf
        conf = ServerConf(confdir=self.confDir)
        
        self.assertEquals(conf.get('conf_dir'),self.confDir)
        self.assertEquals(self.confFile,conf.get('conf_file'))
        
        
        conf.getServerKeyDir()    #just to make sure it has been initiated the proper way
        conf.setServerHost("testhost")
        
        conf2 = ServerConf(confdir = self.confDir)  #creating a new  instance reinitiates the config and reads parameters from config file  
        self.assertEquals('testhost',conf2.get('server_host'))
        
    def testAddNodes(self):
        conf = ServerConf(confdir=self.confDir)
        conf.addNode('localhost1')
        conf.addNode('localhost2')
        
        nodes = conf.getNodes()
        self.assertEquals(nodes.size(),2)
        
        self.assertTrue(nodes.exists("localhost1","13807"))
        self.assertTrue(nodes.exists("localhost2","13807") )
        
        
    def testRemoveNodes(self):    
        conf = ServerConf(confdir=self.confDir)
        conf.addNode('localhost1')
        conf.addNode('localhost2')
        
        nodes = conf.getNodes()
        self.assertEquals(nodes.size(),2)
        
        self.assertTrue(nodes.exists("localhost1","13807"))
        self.assertTrue(nodes.exists("localhost2","13807") )
        
        conf.removeNode('localhost1')
        nodes = conf.getNodes()
        self.assertEquals(nodes.size(),1)
        
        self.assertFalse(nodes.exists("localhost1","13807"))
        self.assertTrue(nodes.exists("localhost2","13807") )
        
        
        
        
    def tearDown(self):
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))
