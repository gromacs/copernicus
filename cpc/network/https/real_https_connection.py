'''
Created on Sep 20, 2011

@author: iman
'''
import httplib
import socket
import ssl
class RealHttpsConnection(httplib.HTTPConnection):
    '''
    Sets up httpsconnections and verifies the certificate sent from the server
    '''


    #def __init__(self,host,port,privateKeyFile,caFile,certFile): needed for verification of client
    def __init__(self,host,port,privateKeyFile,caFile,certFile):
        httplib.HTTPConnection.__init__(self, host)
        self.host = host
        self.port = int(port)
        self.privateKeyFile = privateKeyFile
        self.caFile = caFile
        self.certFile = certFile
        
    
    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #create an ssl context and load certificate verify locations
       # print open(self.caFile,'r').read()
        self.sock = ssl.wrap_socket(sock,
                                    self.privateKeyFile,
                                    self.certFile,
                                    cert_reqs = ssl.CERT_REQUIRED,
                                    ssl_version=ssl.PROTOCOL_SSLv23,
                                    ca_certs=self.caFile)
        self.sock.connect((self.host,self.port))

        
