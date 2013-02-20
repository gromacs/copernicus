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
import socket
import re
import shutil
from string import Template
import time
from cpc.util.conf.server_conf import ServerConf
from cpc.util.conf.connection_bundle import ConnectionBundle
import random
import string
'''
Created on Oct 29, 2010

@author: iman
'''

class OpenSSL(object):
    '''
    A class used by the server to generate CA and perform certificate signing
    '''
 
    def __init__(self, cn = None):
        self.conf = ServerConf()
        self.cn = cn or self.conf.getHostName() or socket.getfqdn()

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
        '''
        Creates a connection bundle for the Client and worker
        @returns ConnectionBundle
        '''
        connectionBundle = ConnectionBundle(create=True, fqdn=self.cn)
        serverConf = ServerConf()
        #generate random ascii string
        randstring = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
        tempDir = "%s/tmp/%s"%(self.conf.getConfDir(),randstring)
        privKeyFile = "%s/priv.pem"%tempDir
        pubKeyFile = "%s/pub.pem"%tempDir
        certReqConfigFile = "%s/cert_req.txt"%tempDir
        certFile = "%s/cert.pem"%tempDir

        os.makedirs(tempDir)  #we create a temp dir for intermediate files

        self._generateKeyPair(privKeyFile=privKeyFile,pubKeyFile=pubKeyFile)

        self._generateCertReqConf(distinguished_cn="%s_%s"%(connectionBundle.CN_ID,self.cn),
                                  certReqConfigFile=certReqConfigFile)

        self._generateCert(privKeyFile,certFile,certReqConfigFile)

        #now we need to read everything in to the connection bundle
        connectionBundle.setPrivateKey(open(privKeyFile,'r').read())
        connectionBundle.setPublicKey(open(pubKeyFile,'r').read())
        connectionBundle.setCert(open(certFile,'r').read())
        connectionBundle.setCaCert(open(self.conf.getCACertFile(),"r").read())

        shutil.rmtree(tempDir)
        connectionBundle.setClientUnverifiedHTTPSPort(
            serverConf.getServerUnverifiedHTTPSPort())
        connectionBundle.setClientVerifiedHTTPSPort(
            serverConf.getServerVerifiedHTTPSPort())
        return connectionBundle

    def setupServer(self):
        if(not os.path.isdir(self.conf.getKeyDir())):
            os.makedirs(self.conf.getKeyDir())

        self._generateKeyPair()
        self._generateCertReqConf(distinguished_cn=self.cn+"_"+self.conf.CN_ID,
                                  certReqConfigFile=self.conf.getCertReqConfigFile() )

        self._generateCert(self.conf.getPrivateKey(),
                           self.conf.getCertFile(),
                           certReqConfigFile=self.conf.getCertReqConfigFile())

        
        
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
    
    def _generateCert(self,privateKeyFile,certFile,certReqConfigFile):
        '''
        generates and cert request based on the provided private key
        writes a cert to the provided certFile path
        @input String privateKeyFile: path to the private key
        @Input String certFile: path to the cert file
        @Input String certReqConfigFile: path to the certificate configuration file
        '''

        args = [ "openssl", "req", "-outform", "PEM", "-new", "-key", \
                privateKeyFile,
                "-config",certReqConfigFile,
                "-out",self.conf.getCertRequestFile() ] #FIXME the certRequest file should just be a tem
        subprocess.call(args)
        
        args = ["openssl", "ca", "-in",
               self.conf.getCertRequestFile(),"-config",
               self.conf.getCaConfigFile(), "-keyfile", \
               self.conf.getCAPrivateKey(),                
               "-out", certFile]


        proc = subprocess.Popen(args,stdin=subprocess.PIPE)
        proc.communicate("y\ny\n")
        os.remove(self.conf.getCertRequestFile())

        #CONVERT TO PEM FORMAT
        args = ["openssl", "x509" ,
                "-in", certFile ,
                "-out",certFile,
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
        template = Template(self.conf.getCaConfTemplate())
        conf =template.safe_substitute(COMMON_NAME=self.cn,CA_DIR=self.conf.getCADir())

        confFile = open(self.conf.getCaConfigFile(),'w')
        confFile.write(conf)
        confFile.close()
        
        
    def _generateCertReqConf(self,distinguished_cn,certReqConfigFile = None):

        if certReqConfigFile==None:
            certReqConfigFile = self.conf.getCertReqConfigFile()

        template =  self.conf.getCertReqConfigTemplate()
        conf =  re.sub("COMMON_NAME","%s_%d"%(distinguished_cn,int(time.time())),template)
        
        confFile = open(certReqConfigFile,'w')
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
       
       
   
       
                    
    
        
