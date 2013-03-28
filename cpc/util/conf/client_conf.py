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



import socket
import tempfile
import sys
import os
import threading
import copy

from cpc.util.conf.conf_base import Conf, ConfError, NoConfError,findAndCreateGlobalDir

class NoServerError(ConfError):
    pass

class ClientConf(Conf):
    """
    Handles client configuration such as default_server and a collection
    of added servers
    """
    __shared_state = {}
    def __init__(self, userSpecifiedPath=None):
        """
        Can_create allows for the initialization of an empty configuration file
        """
        if self.exists():
            return
                
        # call parent constructor with right file name.
        try:
            Conf.__init__(self, name="clientconfig.cfg",
                userSpecifiedPath=userSpecifiedPath)
            self.lock = threading.RLock()
            self.initDefaults()
            self._tryRead()
            #self._loadDefaultServer();
        except NoConfError as e:
            self._initClientConf()

    def _loadDefaultServer(self):
        """
        Fetches the server from the default_server pointer and sets client_host
        and unver port accordingly
        """
        try:
            default_server_str = self.get("default_server")
            if default_server_str is None:
                raise NoServerError("No default server")
            servers = self.get("servers")
            default_server = servers[default_server_str]
            self._add('client_host', None,
                 "Hostname for the client to connect to",
                 userSettable=False, writable=False)

            self._add('client_unverified_https_port', None,
                 "Port number for the client to connect to unverified https",
                 userSettable=False, writable=None)
            self.conf["client_host"].set(default_server['client_host'])
            self.conf["client_unverified_https_port"].set(
                default_server['client_unverified_https_port'])
        except KeyError as e:
            # this implies an invalid default_server pointer,
            # and should only occur upon manual user interaction with the
            # conf file
            raise ConfError("Error getting default server: %s"%e)

    def _initClientConf(self):
        """
        Creates a client config initialized with the default values
        """
        self.conf = {}
        self.lock = threading.RLock()
        self.initDefaults()
        confDir=findAndCreateGlobalDir()
        confFile = os.path.join(confDir,"clientconfig.cfg")
        outf=open(os.path.join(confFile), 'w')
        outf.close()
        self.findLocation("clientconfig.cfg", None, None)
        self.write()


    #overrrides method in ConfBase
    def initDefaults(self):
        self._add('default_server', None,
            "The default server the client uses",userSettable=True, writable=True)
        self._add('servers', dict(),
            "Server library",userSettable=True, writable=True)


    def getClientHost(self):
        try:
            return self.get('client_host')
        except KeyError:
            self._loadDefaultServer()
            return self.get('client_host')


    def getClientUnverifiedHTTPSPort(self):
        try:
            return int(self.get('client_unverified_https_port'))
        except KeyError:
            self._loadDefaultServer()
            return int(self.get('client_unverified_https_port'))

    def addServer(self, name, host, port):
        servers = self.get('servers')
        if name in servers:
            raise ConfError("A server with name %s already exist"%name)
        servers[name] = {
            "client_unverified_https_port" : port,
            "client_host" : host
        }
        self.set('servers', servers)
        self.set('default_server', name)

    def setServer(self, name):
        servers = self.get('servers')
        if name not in servers:
            raise ConfError("No server named %s added"%name)
        self.set('default_server', name)


    def getServers(self):
        servers = copy.copy(self.get('servers'))
        def_server = self.get('default_server')
        if def_server is not None:
            servers[def_server]['default'] = True
        return servers


