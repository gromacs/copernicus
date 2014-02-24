import json
import logging
from cpc.network.com.input import Input
from cpc.network.com.server_connection import ServerConnection
from cpc.network.server_request import ServerRequest
from cpc.util import json_serializer
from cpc.util.conf.server_conf import ServerConf

log=logging.getLogger(__name__)
class DirectServerMessage(ServerConnection):
    """
    Messages that should only between trusted neighbouring nodes.
    These messages should not need a network topology
    """

    def networkTopology(self,topology):
        """
            topology:Nodes
        """
        cmdstring="network-topology"
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))


        input2 = Input('topology',json.dumps(topology
            ,default = json_serializer.toJson,indent=4))
        fields.append(input2)
        msg = ServerRequest.prepareRequest(fields,[])

        response = self.putRequest(msg)
        return response

    def pingServer(self,serverId):
        cmdstring='ping'
        fields = []
        input = Input('cmd', cmdstring)
        fields.append(input)
        fields.append(Input('version', "1"))
        headers = dict()
        if serverId!= None:
            headers['server-id'] = serverId
        msg = ServerRequest.prepareRequest(fields,[],headers)
        response= self.putRequest(msg)
        return response

class PersistentServerMessage(ServerConnection):
    """
        The purpose of this class is to handle persistent server to server
        connections

        It contains to message types persistIncomingConnections and
        persistOutgoingconnections.

        persistIncomingConnection returns the underlying socket instead of
        putting it back to the connection pool.
        The server should be responsible for monitoring this socket for
        incoming requests

        persistOutgoingConnection is simpler. it puts back the connection to
        the pool and assumes that the receiving server will monitor this
        connection for requests.

    """

    INBOUND_CONNECTION = "IN"
    OUTBOUND_CONNECTION = "OUT"


    def __persistConnection(self,direction,headers = dict()):
        headers['persistent-connection'] = direction
        #message body is actually irrellevant and is not read on the other
        # side.
        #we just need to conform to the http protocol
        fields = []
        fields.append(Input('cmd', "persist-connection"))

        #sending along the connection parameters for this server
        conf = ServerConf()
        connectionParams = dict()
        connectionParams['serverId'] = conf.getServerId()
        connectionParams['hostname'] = conf.getHostName()
        connectionParams['fqdn'] = conf.getFqdn()
        connectionParams['client_secure_port'] = conf\
        .getClientSecurePort()
        connectionParams['server_secure_port'] = conf\
        .getServerSecurePort()


        input2 = Input('connectionParams',
            json.dumps(connectionParams,default = json_serializer.toJson,
                indent=4))  # a json structure that needs to be dumped
        fields.append(input2)


        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
            headers))

        return response

    #NOTE does not return a response,it returns the socket used for the
    # connection
    def persistIncomingConnection(self):
        self.storeInConnectionPool = False
        self.createConnection = True
        #OUTBOUND FOR THE RECEIVING END
        headers = dict()
        response = self.__persistConnection(self.OUTBOUND_CONNECTION,headers)
        return self.getSocket()

    def persistOutgoingConnection(self):
        """
        This is just a simple ping message, the keep-alive header will
        ensure that the other end wont close the connection
        """
        self.createConnection = True
        fields = []
#        fields.append(Input('cmd', "ping"))
        headers = dict()
#        response= self.putRequest(ServerRequest.prepareRequest(fields, [],
#            headers))

        #return response
        #inbound for the receiving end
        return self.__persistConnection(self.INBOUND_CONNECTION,headers)


