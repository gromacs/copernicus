import httplib
import socket
import logging
import traceback

from cpc.network.com.connection_base import ConnectionBase
from cpc.network.https.real_https_connection import HttpsConnectionWithCertReq
from cpc.network.https_connection_pool import ServerConnectionPool, ConnectionPoolEmptyError
from cpc.network.node import Node
from cpc.util import CpcError, cpc


log=logging.getLogger('cpc.network.com.server_connection')
class ServerConnectionError(CpcError):
    def __init__(self, exc):
        self.str = exc.__str__()


class ServerConnection(ConnectionBase):

    def __init__(self,node, conf,createConnection=False,storeInConnectionPool =
    True):

        """
            inputs:
                node
                conf:ServerConf
                createConnection:boolean used to explicitly create a
                                         connection for example when we
                                         establish connections for the
                                         first time
                storeInConnectionPool:boolean  must be used for sockets that we
                                               listen on
            parameters:
                httpsConnectionPool:ServerConnectionPool
                connected:boolean
                conf:ServerConf
                storeInConnectionPool:boolean
                conn:HttpsConnectionWithCertReq
        """
        self.node = node
        self.httpsConnectionPool = ServerConnectionPool()
        self.connected=False
        self.conf = conf
        self.storeInConnectionPool = storeInConnectionPool
        self.createConnection = createConnection
        self.conn = None


    def getSocket(self):
        return self.conn.sock

    def connect(self):

        log.log(cpc.util.log.TRACE,"Connecting ServerConnection VerHTTPS to "
                                   "%s"%self.node.toString())

        #if we need to create a connection. Should only be used in the
        # initial case when we want to establish an inbound connection to
        # another server
        try:
            if(self.createConnection):
                self.conn = HttpsConnectionWithCertReq(self.node.getHostname(),
                    self.node.getServerSecurePort(),
                    self.conf.getCAPrivateKey()
                    ,self.conf.getCaChainFile()
                    ,self.conf.getCACertFile())
                self.conn.connect()
                self.connected=True

            else:
                self.conn = self.httpsConnectionPool.getConnection(self.node)

        except ConnectionPoolEmptyError as e:
            #Connection pool is currently empty this means that we do not
            # have any outbound connections to this node
            #It could just be that we currently are not connected or all
            # connections are simply taken!
            log.info("No connections in pool. No outbound connections of this network node.")
            raise

    def handleSocket(self):
        if self.storeInConnectionPool:
            self.httpsConnectionPool.putConnection(self.conn,self.node)
            self.conn = None


    def prepareHeaders(self,request):

        if not request.headers.has_key('originating-server-id'):
            request.headers['originating-server-id'] = self.conf.getServerId()

        #So the receiving server understands that this connection should
        #get out of the request handling loop.
        request.headers["Connection"]= "keep-alive"
        return request

    def handleResponseHeaders(self,response):
        pass #we do not need to do anything here



    def putRequest(self ,req):
        """
        inputs:
            req:ServerRequest
        returns:
            ClientResponse
        """
        try:
            log.log(cpc.util.log.TRACE,"Connecting using HTTPS with cert authentication")
            if self.conn == None:
                self.connect()
            ret=self.sendRequest(req,"PUT")
        except httplib.HTTPException as e:
            if self.createConnection==False:
                self.node.reduceOutboundConnection()
           # log.error(traceback.print_exc())
            raise ServerConnectionError(e)
        except socket.error as e:
            if self.createConnection==False:
                self.node.reduceOutboundConnection()
           # log.error(traceback.print_exc())
            raise ServerConnectionError(e)
        except Exception as e:
            if self.createConnection==False and self.node.isConnected():
                self.node.reduceOutboundConnection()
           # log.error(traceback.print_exc())
            raise ServerConnectionError(e)

        return ret



