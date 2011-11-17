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
import cpc.util.conf.conf
import os
import shutil
import json



class TestConf(unittest.TestCase):
    
    
    def setUp(self):
        self.confFile = 'test.conf'
        self.confBaseDir = ".copernicus-test"
        self.confDir = os.path.join(os.environ["HOME"],self.confBaseDir,gethostname())
         
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))

     
    
    
    '''tests to set up a default config file'''         
    def testInit(self):

        conf = cpc.util.conf.conf.Conf()
         
        #should have a config filewith default values        
        self.assertEquals(conf.get('hostname'),gethostname())
        self.assertEquals(conf.get('global_dir'),os.path.join(os.environ["HOME"], ".copernicus"))          
        self.assertEquals(conf.get('conf_dir'), os.path.join(os.environ["HOME"], ".copernicus",gethostname()))                                  
        self.assertEquals(conf.get('conf_file'),'cpc.conf')
                                            
    '''Initiates a custom config file and changes one config parameter
       Also tries to reread the config file in order to ensure that the changes paramters are written to file
    '''                                         
    def testInitChangeConfigs(self):
        
        conf = cpc.util.conf.conf.Conf(self.confFile,self.confDir)
                
        self.assertEquals(conf.get('global_dir'),os.path.join(os.environ["HOME"], ".copernicus"))          
        self.assertEquals(conf.get('conf_dir'), self.confDir)
    
        testValue = 'testvalue'
        confParam = 'test_conf'
        conf._add(confParam, testValue,     
                  "a test configuration parameter", True)
                        
        clientHostIp = '127.0.0.10'        
        conf.set(confParam,clientHostIp)
                                        
        self.assertEquals(conf.get('conf_file'), self.confFile) 
                
        self.assertTrue(os.path.isfile(conf.getFile('conf_file')))
           
        self.assertEquals(conf.get(confParam),clientHostIp)
                 
        
        #read the file, do json_decode, ensure that the conf param exists
        f = open(conf.getFile('conf_file'))
        str = f.read()
        confs = json.loads(str)
        self.assertEquals(confs[confParam],clientHostIp) 
            
    def testInitManyDifferentFiles(self):
        conf1 = cpc.util.conf.conf.Conf('test1.conf',self.confDir) 
        conf2 = cpc.util.conf.conf.Conf('test2.conf',self.confDir)
        conf3 = cpc.util.conf.conf.Conf('test3.conf',self.confDir)
        
        self.assertEquals(conf1.get('conf_file'),'test1.conf')
        self.assertEquals(conf2.get('conf_file'),'test2.conf')
        self.assertEquals(conf3.get('conf_file'),'test3.conf')
        
        testValue = 'testvalue'
        confParam = 'test_conf'
        conf1._add(confParam, testValue,     
                  "a test configuration parameter", True)
        
        conf2._add(confParam, testValue,     
                  "a test configuration parameter", True)
        
        conf3._add(confParam, testValue,     
                  "a test configuration parameter", True)
        
        conf1.set(confParam,'conf1Val')
        conf2.set(confParam,'conf2Val')
        conf3.set(confParam,'conf3Val')
        
        self.assertTrue(os.path.isfile(conf1.getFile('conf_file')))
        self.assertTrue(os.path.isfile(conf2.getFile('conf_file')))
        self.assertTrue(os.path.isfile(conf3.getFile('conf_file')))
        
        pass                    
                             
    def tearDown(self):
        #shutil.rmtree(os.path.join(os.environ["HOME"],".copernicus/test"))
        if os.path.isdir(os.path.dirname(self.confDir)):
            shutil.rmtree(os.path.dirname(self.confDir))         
                
