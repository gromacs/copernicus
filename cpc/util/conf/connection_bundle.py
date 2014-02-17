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
import socket
import tempfile
import sys
import os
import threading

from cpc.util.conf.conf_base import Conf

class ConnectionBundle(Conf):
    '''
    this worker conf will be transformed to a connection bundle
    '''
    #__shared_state = {}
    CN_ID = "worker"  #used to distinguish common names in certs



    def __init__(self, userSpecifiedPath=None, create=False,
                 fqdn=socket.getfqdn()):
        # check whether the object is already initialized
        if not create:
            if self.exists():
                return
                # call parent constructor with right file name.
            Conf.__init__(self, name='client.cnx',
                userSpecifiedPath=userSpecifiedPath)
        if create:
            # create an empty conf without any values.
            self.conf = dict()

        self.client_host = fqdn
        self.server_secure_port = Conf.getDefaultServerSecurePort()
        self.client_secure_port = Conf.getDefaultClientSecurePort()
        self.privateKey = ''
        self.publicKey = ''
        self.cert = ''
        self.CAcert = ''
        self.initDefaults()


        # TODO: make it a regular Lock() - for now this might reduce the 
        # chances of a deadlock
        self.lock = threading.RLock()


        #worker specific
        dn = os.path.dirname(sys.argv[0])
        self.execBasedir = ''
        if dn != "":
            self.execBasedir = os.path.abspath(dn)

        self._add('exec_base_dir', self.execBasedir,
            'executable base directory', writable=False)

        self.tempfiles = dict()
        #if conffile:
        self._tryRead()
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

        certTempFile = tempfile.NamedTemporaryFile(delete=False)
        certTempFile.write(self.get('cert'))
        certTempFile.seek(0)
        self.tempfiles['cert'] = certTempFile
        certTempFile.close()

        caCertTempFile = tempfile.NamedTemporaryFile(delete=False)
        caCertTempFile.write(self.get('ca_cert'))
        caCertTempFile.seek(0)
        self.tempfiles['ca_cert'] = caCertTempFile
        caCertTempFile.close()


    #overrrides method in ConfBase
    def initDefaults(self):
        self._add('client_host', self.client_host,
                  "Hostname for the client to connect to", True)
        self._add('server_secure_port', Conf.getDefaultServerSecurePort(),
                   "Port number the server uses for communication from servers ",
                   True,None,'\d+')


        self._add('client_secure_port', Conf.getDefaultClientSecurePort(),
                  "Port number the server listens on for communication from clients",
                  True,None,'\d+')

        self._add('private_key', '',
            "Port number for the client to connect to https", True, None)
        self._add('public_key', '',
            "Port number for the client to connect to https", True, None)
        self._add('cert', '',
            "Port number for the client to connect to https", True, None)

        self._add('ca_cert', '',
            "Port number for the client to connect to https", True, None)

        self._add('plugin_path', "",
            "Colon-separated list of directories to search for plugins",
            True, writable=False)

        self._add('local_executables_dir', "executables",
            "Directory containing executables for the run client. Part of executables_path",
            False,
            relTo='conf_dir', writable=False)
        self._add('global_executables_dir', "executables",
            "The directory containing executables for the run client. Part of executables_path",
            False,
            relTo='global_dir', writable=False)
        self._add('executables_path', "",
            "Colon-separated directory list to search for executables",
            True, writable=False)

        # the worker's run directory should NEVER be fixed relative to
        # anything else; instead, it should just run in the current directory
        self._add('run_dir', #os.path.join(os.environ["HOME"],
            "cpc-worker-workload",
            "The run directory for the run client",
            True, writable=False)


    def getClientHost(self):
        return self.get('client_host')

    def getServerSecurePort(self):
        return int(self.get('server_secure_port'))

    def getClientSecurePort(self):
        return int(self.get('client_secure_port'))

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

    def setServerSecurePort(self, httpsPort):
        self.conf["server_secure_port"].set("%s" % httpsPort)

    def setClientSecurePort(self, httpsPort):
        self.conf["client_secure_port"].set("%s" % httpsPort)

    def setPrivateKey(self, privateKey):
        '''
        @input privateKey String, a pem formatted string
        '''
        self.conf["private_key"].set(privateKey)

    def setPublicKey(self, publicKey):
        '''
        @input publicKey String, a pem formatted string
        '''
        self.conf["public_key"].set(publicKey)

    def setCert(self, cert):
        '''
        @input cert String, a pem formatted string
        '''
        self.conf["cert"].set(cert)

    def setCaCert(self, caCert):
        '''
        @input ca_cert String, a pem formatted string
        '''
        self.conf["ca_cert"].set(caCert)

    def setHostname(self, hostname):
        self.conf["client_host"].set(hostname)



