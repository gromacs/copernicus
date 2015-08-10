'''
Created on Sep 20, 2011

@author: iman
'''
import httplib
import logging
import socket
import ssl
from array import array
from cpc.util import CpcError

log=logging.getLogger(__name__)
class HttpsConnectionWithCertReqCreationException(CpcError):
    def __init__(self, str):
        self.str = str


class HttpsConnectionWithCertReq(httplib.HTTPConnection):
    '''
    Provides an HTTPS connection with certificate verification
    '''
    def __init__(self,host,port,privateKeyFile=None,caFile=None,certFile=None,
                 socket=None):


        """
           Creates the object, one has to either provide privateKeyFile,
           caFile and certFile or pass in an already created SSLSocket object.
           the latter is for the case where we have an established connection
           that we want to wrap as a HttpsConnectionWithCertReq

           inputs:
            host:String             hostname of the destination
            port:String             the HTTPS port to connect to
            privateKeyFile:String   path to our private key,
                                    used to verify local side
            caFile:String           path local certificate authority file
                                    used to verify local side
            certFile:String         path to our certificate chain file
                                    used to verify the host we want to
                                    connect to

            socket:SSLSocket        a socket we want to wrap as a
                                    HttpsConnectionWithCertReq
        """
        httplib.HTTPConnection.__init__(self, host,int(port))
        self.auto_open = False
        if(socket==None):
            if(privateKeyFile==None or caFile==None or certFile==None):
                raise HttpsConnectionWithCertReqCreationException("Cannot create "
                    "instance of HttpsConnectionWithCertReq, "
                    "either provide a ready made SSLsocket or  "
                    "privateKeyfile,certFile and caFile")

            else:
                self.privateKeyFile = privateKeyFile
                self.caFile = caFile
                self.certFile = certFile


        else:
            self.sock = socket
        self.host = host
        #self.set_debuglevel(10)
        self.connected = False


    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #create an ssl context and load certificate verify locations
        try:
            self.sock = ssl.wrap_socket(sock,
                                        self.privateKeyFile,
                                        self.certFile,
                                        cert_reqs = ssl.CERT_REQUIRED,
                                        ssl_version=ssl.PROTOCOL_SSLv3,
                                        ca_certs=self.caFile)
            self.sock.connect((self.host,self.port))
            self.connected = True

        except ssl.SSLError as e:
            log.error(e)
            raise

class HttpsConnectionNoCertReq(httplib.HTTPConnection):
    '''
    Provides an HTTPS connection with no certificate verification
    '''

    #def __init__(self,host,port,privateKeyFile,caFile,certFile): needed for verification of client
    def __init__(self,host,port):
        httplib.HTTPConnection.__init__(self, host)
        #self.set_debuglevel(10)
        self.host = host
        self.port = int(port)


    def connect(self):

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            #create an ssl context and load certificate verify locations
            self.sock = ssl.wrap_socket(sock,
                                        cert_reqs = ssl.CERT_NONE,
                                        ssl_version=ssl.PROTOCOL_SSLv3)
            self.sock.connect((self.host,self.port))

        except ssl.SSLError as e:
            log.error(e)
            raise