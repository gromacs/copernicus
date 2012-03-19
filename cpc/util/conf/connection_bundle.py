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
from ConfigParser import SafeConfigParser
import socket
import tempfile
import sys
from cpc.util.conf.conf_base import Conf  
import os
class ConnectionBundle(Conf):
    '''
    this worker conf will be transformed to a connection bundle
    '''
    __shared_state = {}
    CN_ID = "worker"  #used to distinguish common names in certs
    def __init__(self,reload=False,conffile=None):


        self.__dict__ = self.__shared_state                  
        if len(self.__shared_state)>0 and reload == False:             
            return;

        self.conf = dict()

        self.client_host = socket.getfqdn()
        self.client_https_port = '13807'
        self.client_http_port = '14807'
        self.privateKey = ''
        self.publicKey = ''
        self.cert =  ''
        self.CAcert = ''
        self.initDefaults()


        #worker specific
        dn=os.path.dirname(sys.argv[0])
        self.execBasedir = ''
        if dn != "":
            self.execBasedir=os.path.abspath(dn)

        self._add('exec_base_dir', self.execBasedir,
                'executable base directory')


        self.tempfiles = dict()
        if conffile:
            self.tryRead(conffile)
            '''
            the private key, cert and
            ca cert need to be provided as filepaths to the ssl connection object
            So we create tempfiles for them here
            '''
            privKeyTempFile = tempfile.NamedTemporaryFile(delete=False)
            privKeyTempFile.write(self.get('private_key'))
            privKeyTempFile.seek(0)
            self.tempfiles['private_key'] = privKeyTempFile
            privKeyTempFile.close()

            certTempFile =  tempfile.NamedTemporaryFile(delete=False)
            certTempFile.write(self.get('cert'))
            certTempFile.seek(0)
            self.tempfiles['cert'] = certTempFile
            certTempFile.close()

            caCertTempFile =  tempfile.NamedTemporaryFile(delete=False)
            caCertTempFile.write(self.get('ca_cert'))
            caCertTempFile.seek(0)
            self.tempfiles['ca_cert'] = caCertTempFile
            caCertTempFile.close()


    #overrrides method in ConfBase
    def initDefaults(self):
        self._add('client_host', self.client_host,
                  "Hostname for the client to connect to", True)
        self._add('client_http_port', self.client_http_port,
                  "Port number for the client to connect to http", True,None,'\d+')
        self._add('client_https_port', self.client_https_port,
                  "Port number for the client to connect to https", True,None,'\d+')

        self._add('private_key', '',
            "Port number for the client to connect to https", True,None)
        self._add('public_key', '',
            "Port number for the client to connect to https", True,None)
        self._add('cert', '',
            "Port number for the client to connect to https", True,None)

        self._add('ca_cert', '',
            "Port number for the client to connect to https", True,None)


        #Worker specific configs
        parser = SafeConfigParser()
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
        parser.read(os.path.join(base,'properties'))

        base_path = ".%s"%parser.get('default','app-name')

        self._add('global_dir', os.path.join(os.environ["HOME"],
            base_path),
            'The global configuration directory',
            userSettable=True)

        #FIXME after handling executables all this can be handled
        self._add('conf_dir', os.path.join(os.environ["HOME"],
            base_path,
            self.getHostName()),
            'The configuration directory',
            userSettable=True)

        self._add('plugin_path', "",
            "Colon-separated list of directories to search for plugins",
            True)

        self._add('local_executables_dir', "executables",
            "Directory containing executables for the run client. Part of executables_path",
            False,
            relTo='conf_dir')
        self._add('global_executables_dir', "executables",
            "The directory containing executables for the run client. Part of executables_path",
            False,
            relTo='global_dir')
        self._add('executables_path', "",
            "Colon-separated directory list to search for executables",
            True)

        self._add('run_dir', os.path.join(os.environ["HOME"],
            "worker",
            "run"),
            "The run directory for the run client",
            True)




    def getClientHost(self):
        return self.get('client_host')

    def getClientHTTPSPort(self):
        return int(self.get('client_https_port'))
    
    def getClientHTTPPort(self):
        return int(self.get('client_http_port'))

    def getPrivateKey(self):
        return self.tempfiles['private_key'].name

    def getCaChainFile(self):
        return self.tempfiles['ca_cert'].name

    def getCertFile(self):
        return self.tempfiles['cert'].name

    def getRunDir(self):
        return self.get("run_dir")

    def getHostName(self):
        ''' The fully qualified domain name of the client  '''
        return socket.getfqdn()

    def setPrivateKey(self,privateKey):
        '''
        @input privateKey String, a pem formatted string
        '''
        self.conf["private_key"].set(privateKey)

    def setPublicKey(self,publicKey):
        '''
        @input publicKey String, a pem formatted string
        '''
        self.conf["public_key"].set(publicKey)

    def setCert(self,cert):
        '''
        @input cert String, a pem formatted string
        '''
        self.conf["cert"].set(cert)

    def setCaCert(self,caCert):
        '''
        @input ca_cert String, a pem formatted string
        '''
        self.conf["ca_cert"].set(caCert)