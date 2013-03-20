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
from cpc.server.state.server_state import ServerState
from cpc.util.conf.server_conf import ServerConf
import cpc.util.log

import cpc.server.message

# Default daemon parameters.
# File mode creation mask of the daemon.
# server_umask = 022
# Default working directory for the daemon.
server_workdir = "/"
# maximum file descriptor
server_maxfd=1024

debug=False



log=logging.getLogger('cpc.server')

class Error(Exception):
    pass
class HTTPServer__base(SocketServer.ThreadingMixIn,BaseHTTPServer.HTTPServer):
    """
    Provides some common methods for the HTTPx servers
    """
    def getState(self):
        return self.serverState

    def getSCList(self):
        """Get the server command list."""
        return cpc.server.message.scSecureList


class VerifiedSecureServer(HTTPServer__base):
    """
    This server provides both client and server side verification
    """
    def __init__(self, handler_class, conf, serverState):
        self.conf=conf
        self.serverState=serverState
        
        BaseHTTPServer.HTTPServer.__init__(self, (conf.getServerHost(), 
                                                  conf.getServerVerifiedHTTPSPort()),
                                           handler_class)
        
        #https part              
        fpem = conf.getPrivateKey()                    
        fcert = conf.getCertFile()
        ca = conf.getCaChainFile()
        sock = socket.socket(self.address_family,self.socket_type)

        try:
            self.socket =  ssl.wrap_socket(sock, fpem, fcert, server_side=True,\
                                           cert_reqs = ssl.CERT_REQUIRED,
                                           ssl_version=ssl.PROTOCOL_SSLv23,
                                           ca_certs=ca
                                           )
            self.server_bind()
            self.server_activate()

        except Exception:
            print "HTTPS port %s already taken"%conf.getServerVerifiedHTTPSPort()
            serverState.doQuit()



class UnverifiedSecureServer(HTTPServer__base):
    """
    This server provides no verification as of now, but is scheduled to provide
    server side verification
    """
    def __init__(self, handler_class, conf, serverState):
        self.conf=conf
        self.serverState=serverState

        BaseHTTPServer.HTTPServer.__init__(self, (conf.getServerHost(),
                                           conf.getServerUnverifiedHTTPSPort()),
                                           handler_class)

        #https part
        fpem = conf.getPrivateKey()
        fcert = conf.getCertFile()
        ca = conf.getCaChainFile()
        sock = socket.socket(self.address_family,self.socket_type)

        try:
            self.socket =  ssl.wrap_socket(sock, fpem, fcert, server_side=True,\
                                           cert_reqs = ssl.CERT_NONE,
                                           ssl_version=ssl.PROTOCOL_SSLv23,
                                           ca_certs=ca
            )
            self.server_bind()
            self.server_activate()

        except Exception:
            print "HTTPS port %s already taken"%conf.getServerVerifiedHTTPSPort()
            serverState.doQuit()

   

def serveVerifiedHTTPS(serverState):
    try:
        httpd = VerifiedSecureServer(request_handler.verified_handler, ServerConf(), serverState)
        sa = httpd.socket.getsockname()
        log.info("Serving verified HTTPS on %s port %s..."%(sa[0], sa[1]))
        httpd.serve_forever();

    except KeyboardInterrupt:
        print "Interrupted"
        serverState.doQuit()
    except Exception:
        print "HTTPS port %s already taken"%ServerConf().getServerVerifiedHTTPSPort()
        serverState.doQuit()

def serveUnverifiedHTTPS(serverState):
    try:
        httpd = UnverifiedSecureServer(request_handler.unverified_handler, ServerConf(), serverState)
        sa = httpd.socket.getsockname()
        log.info("Serving unverified HTTPS on %s port %s..."%(sa[0], sa[1]))
        httpd.serve_forever()

    except KeyboardInterrupt:
        print "Interrupted"
        serverState.doQuit()
    except Exception:
        print "HTTPS port %s already taken"%ServerConf().getServerUnverifiedHTTPSPort()
        serverState.doQuit()


#starts an http server in a thread.
def serverLoop(conf, serverState):
    """The main loop of the server process."""
    cpc.util.log.initServerLog(ServerConf().getMode())
    th2=Thread(target = serveVerifiedHTTPS,args=[serverState])
    th2.daemon=True
    th2.start()

    serveUnverifiedHTTPS(serverState)

    
def shutdownServer(self):
    log.info("shutdown complete")
    #self.httpd.shutdown


def runServer(logLevel=None,doFork=True):
    """
        Starts the server process
        logLevel  prod|debug|trace   Determines the log level
        doFork                       Forks and detaches the process and runs\
                                     it as a daemon
    """
    conf = ServerConf()
    conf.setMode(logLevel)

    # initialize the server state before forking.
    serverState = ServerState(conf)
    serverState.read()

    pid=0
    try:
        # First fork so the parent can exit. 
        if doFork:
            pid=os.fork()
    except OSError, e:
        raise Error, "%s [%d]"%(e.strerror, e.errno)

    if pid==0:
        # become the session leader so that we won't have a controlling 
        # terminal.
        try:
            if doFork:
                os.setsid()
        except OSError, e:
            raise Error, "%s [%d]"%(e.strerror, e.errno)

        # now fork again to make sure init is our parent.
        try:
            if doFork:
                pid=os.fork()
        except OSError, e:
            raise Error, "%s [%d]" % (e.strerror, e.errno)
    
        if pid==0: # we're the child
            # go to the root directory to  make sure we're not interfering
            # with unmount fses etc.
            os.chdir(server_workdir)
            #os.umask(server_umask)
        else:
            # we don't want to doubly flush stuff, so we use _exit().
            os._exit(0)

        # Close all file descriptors.
        if doFork:
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
