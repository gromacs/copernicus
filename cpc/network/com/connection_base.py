import mmap
from cpc.network.com.client_response import ClientResponse
from cpc.util import ClientError, cpc

import logging
log=logging.getLogger(__name__)
class ConnectionBase:
    """
    Abstract class
    Responsible for sending a request and receiving a response
    """

    def connect(self,host,port):
        raise NotImplementedError("Not implemented by subclass")

    def handleSocket(self):
        raise NotImplementedError("Not implemented by subclass")

    def prepareHeaders(self,request):
        """
        Creates and adds necessary headers for this connection type

        inputs:
            request:ServerRequest
        returns:
            ServerRequest
        """
        raise NotImplementedError("not implemented by subclass")

    def handleResponseHeaders(self,response):
        raise NotImplementedError("not implemented by subclass")

    def sendRequest(self,req,method="POST"):
        req = self.prepareHeaders(req)

        self.conn.request(method, "/copernicus",req.msg,req.headers)
        response=self.conn.getresponse()
        if response.status!=200:
            errorStr = "ERROR: %d: %s"%(response.status, response.reason)
            resp_mmap = mmap.mmap(-1, int(len(errorStr)), mmap.ACCESS_WRITE)
            resp_mmap.write(errorStr)

        else:
            self.handleResponseHeaders(response)
            headers=response.getheaders()
            for (key,val) in headers:
                log.log(cpc.util.log.TRACE,"Got header '%s'='%s'"%(key,val))
            length=response.getheader('content-length', None)
            if length is None:
                length=response.getheader('Content-Length', None)
            if length is None:
                raise ClientError("response has no length")
            log.log(cpc.util.log.TRACE,"Response length is %s"%(length))


            #this covers the case where are reponse only sends back headers
            # as we cannot initialize an mmap object of length 0
            if int(length) == 0:
                length  = 1
            resp_mmap = mmap.mmap(-1, int(length), access=mmap.ACCESS_WRITE)

            resp_mmap.write(response.read(length))

        resp_mmap.seek(0)
        headerTuples = response.getheaders()

        headers = dict()

        for (header,value) in headerTuples:
            headers[header] = value


        self.handleSocket()

        return ClientResponse(resp_mmap,headers)