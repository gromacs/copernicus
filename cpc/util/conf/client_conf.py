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
            self._loadDefaultServer();
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
                return
            servers = self.get("servers")
            default_server = servers[default_server_str]

            self.conf["client_host"].set(default_server['client_host'])
            self.conf["client_secure_port"].set(
                default_server['client_secure_port'])
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
            "Default server the client uses",userSettable=True, writable=True)
        self._add('servers', dict(),
            "Server library",userSettable=True, writable=True)
        self._add('client_host', None,
             "Hostname for the client to connect to",
             userSettable=False, writable=False)
        self._add('client_secure_port', None,
             "Port number the server listens on for communication from clients",
             userSettable=False, writable=None)

    def getClientHost(self):
        host = self.get('client_host')
        if host is None:
            raise NoServerError("No default server")
        return host

    def getClientSecurePort(self):
        port = self.get('client_secure_port')
        if port is None:
            raise NoServerError("No default server")
        return int(port)

    def addServer(self, name, host, port):
        servers = self.get('servers')
        if name in servers:
            raise ConfError("A server with name %s already exist"%name)
        servers[name] = {
            "client_secure_port" : port,
            "client_host" : host
        }
        self.set('servers', servers)
        self.set('default_server', name)
        self._loadDefaultServer()

    def setDefaultServer(self, name):
        servers = self.get('servers')
        if name not in servers:
            raise ConfError("No server named %s added"%name)
        self.set('default_server', name)
        self._loadDefaultServer()


    def getServers(self):
        servers = copy.copy(self.get('servers'))
        def_server = self.get('default_server')
        if def_server is not None:
            servers[def_server]['default'] = True
        return servers

    def getCookie(self):
        """
        Returns the cookie for the current (default) server
        """
        def_srv = self._getDefaultServer()
        if 'cookie' in def_srv:
            return def_srv['cookie']
        return None

    def setCookie(self, cookie):
        """
        Sets the cookie for the current (default) server
        """
        def_srv_str = self.get("default_server")
        if def_srv_str is None:
            raise ConfError("No default server")
        self._updateServer(def_srv_str, 'cookie', cookie)

    def _getDefaultServer(self):
        """
        Returns a the default server as a dict, safe to modify
        Throws ConfError if no such server
        """
        def_srv_str = self.get("default_server")
        if def_srv_str is None:
            raise ConfError("No default server")
        return copy.copy(self.get("servers")[def_srv_str])

    def _updateServer(self, name, key, val):
        servers = self.get('servers')
        if name not in servers:
            raise ConfError("No server named %s added"%name)
        servers[name][key] = val
        self.set('servers', servers)
        self._loadDefaultServer()   
