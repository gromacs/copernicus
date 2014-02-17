from BaseHTTPServer import HTTPServer
import BaseHTTPServer
import SocketServer
import logging
import socket
import select
from cpc.network.https.real_https_connection import HttpsConnectionWithCertReq

from cpc.network.https_connection_pool import ServerConnectionPool
import cpc.server.message

from cpc.util.conf.server_conf import ServerConf


log=logging.getLogger('cpc.network.copernicius_server')

class HTTPServer__base(SocketServer.ThreadingMixIn,HTTPServer):
    """
    Provides some common methods for the HTTPx servers
    """
    def getState(self):
        return self.serverState

    def getSCList(self):
        """Get the server command list."""
        return cpc.server.message.scSecureList


class CopernicusServer(HTTPServer__base):

    def __init__(self, handler_class, conf,serverState):
        BaseHTTPServer.HTTPServer.__init__(self, (conf.getServerHost(),
                        conf.getServerSecurePort()),handler_class)

        #this informs SocketServer.ThreadingMixin that each reqeust thread
        # should be a daemon thread. If this is False threads will not
        # shutdown if we seen keep-alive in the header
        self.daemon_threads = True
        self.serverState = serverState

    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.
        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.serverState.startConnectServerThread()
        self.serverState.addReadableSocket(self.socket)


        self._BaseServer__is_shut_down.clear()
        try:
            while not self._BaseServer__shutdown_request:
                # XXX: Consider using another file descriptor or
                # connecting to the socket to wake this up instead of
                # polling. Polling reduces our responsiveness to a
                # shutdown request and wastes cpu at all other times.
                r, w, e = select.select( self.serverState.readableSockets
                                        , []
                                        , self.serverState.readableSockets
                                        , poll_interval)

                for sock in e:
                    log.error("socket %s crashed"%sock)

                for sock in r:
                    if self.socket == sock:
                        self._handle_request_noblock()
                    else:
                        #Sockets that have been reverted from write to read
                        #end up here.
                        #what happens after this section is that they end up
                        # in a request handling loop.
                        log.log(cpc.util.log.TRACE,"Preparing established "
                                                   "connection and setting it"
                                                   " to read")
                        self.serverState.removeReadableSocket(sock)
                        request = sock

                        client_address = sock.getpeername()
                        if self.verify_request(request, client_address):
                            try:
                                self.process_request(request, client_address)
                            except:
                                self.handle_error(request, client_address)
                                self.shutdown_request(request)


        finally:
            self._BaseServer__shutdown_request = False
            self._BaseServer__is_shut_down.set()


    def shutdown_request(self,request):
        if(hasattr(request,"revertSocket") and request.revertSocket==True):
            node = ServerConf().getNodes().get(request.serverId)

            request = self.wrapHttpsConnectionWithCertReq(request)
            ServerConnectionPool().putConnection(request,node)
            node.addOutboundConnection()
            log.log(cpc.util.log.TRACE,"Socket not closed, "
                                       "saved as persistent outgoing"
                                       " connection")
        else:
            #This is how we distinguish socket that comes from a server
            if(hasattr(request,"serverId")):
                node = ServerConf().getNodes().get(request.serverId)
                node.reduceInboundConnection()
                log.log(cpc.util.log.TRACE,"Closing socket for %s "%node.toString())

            SocketServer.TCPServer.shutdown_request(self,request)


    def wrapHttpsConnectionWithCertReq(self,socket):
        """
            takes a socket object and wraps it in a HttpsConnectionWithCertReq
            instance
            input:
                socket:SSLSocket

            returns:
                HttpsConnectionWithCertReq
        """
        host,port = socket.getpeername()
        wrappedSock = HttpsConnectionWithCertReq(host,port,
            socket=socket)
        wrappedSock.connected=True
        return wrappedSock
