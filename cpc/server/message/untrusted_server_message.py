import json
import logging
from cpc.network.com.client_base import ClientBase
from cpc.network.com.input import Input
from cpc.network.node_connect_request import NodeConnectRequest
from cpc.network.server_request import ServerRequest
from cpc.util import json_serializer
from cpc.util.conf.server_conf import ServerConf

log=logging.getLogger(__name__)
class RawServerMessage(ClientBase):
    """Raw named server-to-server messages for messages to servers that are not
        yet in the topology.

        These messages should all communicate on the client port
        """
    def __init__(self,host=None,port=None):
        self.conf = ServerConf()
        self.host = host
        self.port = port
        if self.host == None:
            self.host = self.conf.getServerHost()
        if self.port == None:
            self.port = self.conf.getServerSecurePort()

        self.privateKey = self.conf.getPrivateKey()
        self.keychain = self.conf.getCaChainFile()

    def sendAddNodeRequest(self,host):
        """

        """
        conf = ServerConf()
        cmdstring ='connect-server-request'
        fields = []
        input=Input('cmd',cmdstring)

        inf = open(conf.getCACertFile(), "r")
        key = inf.read()

        nodeConnectRequest = NodeConnectRequest(conf.getServerId()
            ,conf.getClientSecurePort()
            ,conf.getServerSecurePort()
            ,key
            ,conf.getFqdn()
            ,conf.getHostName())



        input2=Input('nodeConnectRequest',
            json.dumps(nodeConnectRequest,
                default=json_serializer.toJson,
                indent=4))
        input3=Input('unqalifiedDomainName',host)
        fields.append(input)
        fields.append(input2)
        fields.append(input3)
        fields.append(Input('version', "1"))
        # this goes over the client Secure Port, and we don't want the server to use
        # cookies
        response= self.postRequest(ServerRequest.prepareRequest(fields),
            require_certificate_authentication=False,
            disable_cookies=True)
        return response

    def addNodeAccepted(self):
        conf = ServerConf()

        inf = open(conf.getCACertFile(), "r")
        key = inf.read()
        #only sending fqdn the requesting should already know the unqualified
        # hostname
        node = NodeConnectRequest(conf.getServerId(),
            conf.getClientSecurePort(),
            conf.getServerSecurePort(),
            key,
            conf.getFqdn(),
            None)
        cmdstring ='node-connection-accepted'
        fields = []
        input=Input('cmd',cmdstring)


        input2=Input('connectRequest',
            json.dumps(node,default=json_serializer.toJson,indent=4))


        fields.append(input)
        fields.append(input2)
        fields.append(Input('version', "1"))

        # this goes over  client secure port , and we don't want the server to use
        # cookies 
        response= self.postRequest(ServerRequest.prepareRequest(fields),
            require_certificate_authentication=False,
            disable_cookies=True)
        return response
