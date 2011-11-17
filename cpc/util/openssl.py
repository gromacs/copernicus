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


import subprocess
import os
#from socket import gethostname
import re
import shutil
'''
Created on Oct 29, 2010

@author: iman
'''

class OpenSSL(object):
    '''
    classdocs
    '''
 
    def __init__(self,conf,cn=None):
        self.conf = conf
        if cn == None:
            self.cn = self.conf.getHostName()
        else:            
            self.cn=cn  #always used for the CA

            self.distinguished_cn = self.cn+"_"+conf.CN_ID
        
    def setupCA(self):
        '''creates keypair and certificate for the CA'''
        #create certificate env                        
        if(not os.path.isdir(self.conf.getCAKeyDir())):
            os.makedirs(self.conf.getCAKeyDir())    
                 
        if(not os.path.isdir(self.conf.getCACertDir())):
            os.makedirs(self.conf.getCACertDir()) 
        
        self._generateCA()
                
        self._generateKeyPair(self.conf.getCAPrivateKey(),self.conf.getCAPublicKey())

        self._generateRootCert()
        
        self._generateCaChainFile()
    
    
    def setupClient(self):
        self.setupServer()
    def setupServer(self):
        if(not os.path.isdir(self.conf.getKeyDir())):
            os.makedirs(self.conf.getKeyDir())    
                 
        self._generateKeyPair()   
        self._generateCertReqConf()
        self._generateCert() 

        
        
    def _generateCA(self):
        '''set up a CA configuration'''
                
        if(not os.path.isfile(self.conf.getCASerialFile())):
            f = open(self.conf.getCASerialFile(),'w')
            f.write('01')
            f.close()

        if(not os.path.isfile(self.conf.getCAIndexFile())):
            f = open(self.conf.getCAIndexFile(),'w')
            f.close()    
        
        self._generateCaConf()
          
    
    def _generateCaChainFile(self):
        file = open(self.conf.getCaChainFile(),"w")
        shutil.copyfile(self.conf.getCACertFile() ,self.conf.getCaChainFile())
    
    def _generateCert(self):
        args = [ "openssl", "req", "-outform", "PEM", "-new", "-key", \
                self.conf.getPrivateKey(),
                "-config",self.conf.getCertReqConfigFile(), 
                "-out",self.conf.getCertRequestFile() ]
        subprocess.call(args)    
        
        args = ["openssl", "ca", "-in",
               self.conf.getCertRequestFile(),"-config",
               self.conf.getCaConfigFile(), "-keyfile", \
               self.conf.getCAPrivateKey(),                
               "-out", self.conf.getCertFile()]

        
        
#        args = ["openssl", "x509", "-req", "-days", "365", "-in",\
#               self.conf.getCertRequestFile(), "-signkey", \
#               self.conf.getCAPrivateKey(), "-out", self.conf.getCertFile()]
        #CONVERT TO PEM FORMAT
        subprocess.call(args)
        os.remove(self.conf.getCertRequestFile())
    
        
        args = ["openssl", "x509" ,
                "-in", self.conf.getCertFile() ,
                "-out",self.conf.getCertFile(),
                 "-outform","PEM"] 
        subprocess.call(args)
    
    def _generateRootCert(self):
        
        ## generate config file
        #self.createOpenSSLConfigFile()    
                
        args = [ "openssl", "req", "-outform", "PEM", "-config",  \
                self.conf.getCaConfigFile(), "-new", "-key", \
                self.conf.getCAPrivateKey(), "-out", \
                self.conf.getCertRequestFile() ]
        subprocess.call(args)
    
         
        args = ["openssl", "x509", "-req", "-days", "365", "-in",\
               self.conf.getCertRequestFile(), "-signkey", \
               self.conf.getCAPrivateKey(), "-out", self.conf.getCACertFile()]
        subprocess.call(args)
        os.remove(self.conf.getCertRequestFile())

                
    def _generateCaConf(self):
        #file = open(self.conf.getCaConfTemplate())
        #template = file.read()   
        template = self.conf.getCaConfTemplate()         
        template = re.sub("COMMON_NAME",self.cn,template)            
        conf = re.sub("CA_DIR",self.conf.getCADir(),template)
        #file.close()
        confFile = open(self.conf.getCaConfigFile(),'w')
        confFile.write(conf)
        confFile.close()
        
        
    def _generateCertReqConf(self):
        template =  self.conf.getCertReqConfigTemplate()
        conf =  re.sub("COMMON_NAME",self.distinguished_cn,template)
        
        
        confFile = open(self.conf.getCertReqConfigFile(),'w')
        confFile.write(conf)
        confFile.close()  
    def _generateKeyPair(self,privKeyFile=None,pubKeyFile=None):
        
        if privKeyFile == None:
            privKeyFile = self.conf.getPrivateKey()
        if pubKeyFile == None:
            pubKeyFile = self.conf.getPublicKey()

        if(not os.path.isfile(privKeyFile)):
            args = ["openssl" , "genrsa", "-out", privKeyFile, "2048"]

            subprocess.call(args)
         
        if(not os.path.isfile(pubKeyFile)): 
            args = [ "openssl", "rsa", "-in", privKeyFile, "-pubout", \
                    "-out", pubKeyFile ]
            subprocess.call(args) 
            
         
    #@input String certfile
    def addCa(self,certfile):
        #tempFile = "tempChainFile"
        #shutil.copyfile(self.conf.getCaChainFile(),tempFile)
       
        file = open(self.conf.getCaChainFile(),"a")
                 
        file.write(certfile)
       
        #temp = open(tempFile,"r")
       
        #file.write(temp.read())
       
        #temp.close()
        file.close()
        
        #os.remove(tempFile)
       
       
   
       
                    
    
        
