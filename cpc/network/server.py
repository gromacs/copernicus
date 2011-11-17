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

import os
import BaseHTTPServer
import SocketServer
import ssl
import logging

from threading import Thread
import request_handler
import cpc.server.state
from cpc.util.conf.server_conf import ServerConf
import cpc.util.log

import cpc.server.message

# Default daemon parameters.
# File mode creation mask of the daemon.
server_umask = 0
# Default working directory for the daemon.
server_workdir = "/"
# maximum file descriptor
server_maxfd=1024

debug=False



log=logging.getLogger('cpc.server')

class Error(Exception):
    pass


"""The server class: waits for incoming connecctions and acts on them"""
""" this is an HTTPS server """
class SecureServer(SocketServer.ThreadingMixIn,BaseHTTPServer.HTTPServer):
    def __init__(self, handler_class, conf, serverState):
        self.conf=conf
        self.serverState=serverState
        
        BaseHTTPServer.HTTPServer.__init__(self, (conf.getServerHost(), 
                                                  conf.getServerHTTPSPort()), 
                                           handler_class)
        
        #https part              
        fpem = conf.getPrivateKey()                    
        fcert = conf.getCertFile()
        ca = conf.getCaChainFile()

        print ca
        print fpem
        print fcert
        sock = socket.socket(self.address_family,self.socket_type)

        self.socket =  ssl.wrap_socket(sock, fpem, fcert, server_side=True,\
                                       #cert_reqs = ssl.CERT_REQUIRED,
                                       ssl_version=ssl.PROTOCOL_SSLv23,
                                       #ca_certs=ca
                                       )
        self.server_bind()
        self.server_activate()

    def getState(self):
        return self.serverState

    def getSCList(self):
        """Get the server command list."""
        return cpc.server.message.scSecureList


""" this is an HTTP server """
class HTTPServer(SocketServer.ThreadingMixIn,BaseHTTPServer.HTTPServer):
    def __init__(self,handler_class,conf,serverState):
        self.serverState = serverState
        self.conf = conf        
        BaseHTTPServer.HTTPServer.__init__(self, (conf.getServerHost(), 
                                                  conf.getServerHTTPPort()), 
                                           handler_class)
        
        
    def getState(self):
        return self.serverState

    def getSCList(self):
        """Get the server command list."""
        return cpc.server.message.scInsecureList

def serveHTTP(serverState):   
    httpserver = HTTPServer(request_handler.handler,ServerConf(),serverState)
    sa2 = httpserver.socket.getsockname()    
    log.info("Serving HTTP on %s port %s..."%(sa2[0], sa2[1]))
    httpserver.serve_forever()
   
    
    
def verifyCallback(conn,x509obj,errorNum,errorDepth,returnCode):
    print "in verify callback"
    return

#starts an http server in a thread.
def serverLoop(conf, serverState):
    """The main loop of the server process."""
    
    cpc.util.log.initServerLog(ServerConf().isDebug())
    th=Thread(target = serveHTTP,args=[serverState])
    th.daemon=True
    th.start()
    httpd = SecureServer(request_handler.handler, conf, serverState)        
    sa = httpd.socket.getsockname()          
    log.info("Serving HTTPS on %s port %s..."%(sa[0], sa[1]))  
    httpd.serve_forever();
    
    
    
    
def shutdownServer(self):
    log.info("shutdown complete")
    self.httpd.shutdown


def forkAndRun(conf, do_debug):
    """Fork & detach a process to run it as a daemon. Starts the server"""
    conf = ServerConf()       
    if(do_debug):
        conf.setMode('debug')
    
    # do_debug comes from the cmd line 
    # we do not want to use the config setting debug here since we want to be able to set
    # production mode server conf to debug in order to trace logs
    debug=do_debug  
    # initialize the server state before forking.
    serverState = cpc.server.state.ServerState(conf)
    serverState.read()
    #raise cpc.util.CpcError("ADFSDSF")
    
    pid=0
    try:
        # First fork so the parent can exit. 
        if not debug:
            pid=os.fork()
    except OSError, e:
        raise Error, "%s [%d]"%(e.strerror, e.errno)

    if pid==0:
        # become the session leader so that we won't have a controlling 
        # terminal.
        try:
            if not debug:
                os.setsid()
        except OSError, e:
            raise Error, "%s [%d]"%(e.strerror, e.errno)

        # now fork again to make sure init is our parent.
        try:
            if not debug:
                pid=os.fork()
        except OSError, e:
            raise Error, "%s [%d]" % (e.strerror, e.errno)
    
        if pid==0: # we're the child
            # go to the root directory to  make sure we're not interfering
            # with unmount fses etc.
            os.chdir(server_workdir)
            os.umask(server_umask)
        else:
            # we don't want to doubly flush stuff, so we use _exit().
            os._exit(0)

        # Close all file descriptors.
        if not debug:
            for fd in range(0, server_maxfd):
                try:
                    os.close(fd)
                except OSError: # we don't care about closing closed fds
                    pass

            if (hasattr(os, "devnull")):
                server_redirect = os.devnull
            else:
                server_redirect = "/dev/null"
            # open a new descriptor
            os.open(server_redirect, os.O_RDWR) # new stdin
            # Duplicate stdin to stdout and stderr .
            os.dup2(0, 1) # stdout
            os.dup2(0, 2) # stderr

        # now start the server
        serverState.startExecThreads()
        serverLoop(conf, serverState)
    return 


def JobList():
    pass
