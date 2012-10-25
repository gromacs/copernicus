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



import BaseHTTPServer
import socket
import mmap
import logging
import os
import uuid
import hashlib
import mimetypes
import re
import traceback
import sys

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO



from server_to_server_message import ServerToServerMessage
from server_response import ServerResponse
from cpc.util.conf.server_conf import ServerConf
from cpc.network.http.http_method_parser import HttpMethodParser
import cpc.server.message
import cpc.util.log



class handler_base(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    Base class for the request handler which handles incoming http/https
    request.
    """
    server_version="Copernicus 1.0"
    protocol_version="HTTP/1.1"
    sys_version="cpc 1.0"


    def setup(self):
        self.log=logging.getLogger('crs.server.request_handler_base')
        self.application_root = "/copernicus"
        self.connection = self.request
        self.responseCode = 200
        self.set_cookie = None
        self.regexp = '^%s[/?]?'%self.application_root  #checks if a request is referring to application root
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)



    def isApplicationRoot(self):
        if(re.search(self.regexp,self.path)):
            return True
        else:
            return False

    # With GET we can serve files and simple commands
    def do_GET(self):

        self.log.log(cpc.util.log.TRACE,'%s %s'%(self.command,self.path))
    
        # if the path starts with application root + / or ?  we have a message to process
        #otherwise we should just strip any request params and keep the resource reference

        if(self.isApplicationRoot()):
            request = HttpMethodParser.parseGET(self.headers.dict,self.path)
            self.processMessage(request)
        #take the input and put it into a request object

        else:
            if self.path == "/":
                self.path += "index.html"

            webDir = ServerConf().getWebRootPath()
            resourcePath = webDir+self.path
            if not os.path.isfile(resourcePath):
                self.responseCode = 404
                resourcePath = webDir+'/404.html'

            response = ServerResponse()    #FIXME content type and rendering is not general here
            file = open(resourcePath,'rb')
            response.setFile(file, mimetypes.guess_type(resourcePath))

            self._sendResponse(response)


    #with POST we only serve commands, post messages can also handle multipart messages
    def do_POST(self):
        self.log.log(cpc.util.log.TRACE,'%s %s'%(self.command,self.path))
        #can handle single part and multipart messages
        #take the input and put it into a request object
        #process the message
        if(self.isApplicationRoot()):
            request = HttpMethodParser.parsePOST(self.headers.dict,self.rfile)
            self.processMessage(request)

        else:
            self.processMessage() #this is not a valid command i.e we did not find the resource



    #PUT messages reserved for server to server messages, put supports message delegation
    def do_PUT(self):
        conf = ServerConf()
        self.log.log(cpc.util.log.TRACE,'%s %s'%(self.command,self.path))
        self.log.log(cpc.util.log.TRACE,"Headers are: '%s'\n"%self.headers)
        
        if self.headers.has_key('end-node') and \
            ServerToServerMessage.connectToSelf(self.headers)==False:

            # if the request contains an endnode we just delegate the
            # message forward

            endNode=None
            if self.headers.has_key('end-node'):
                endNode=self.headers['end-node']

            #endNodePort = None
            #if self.headers.has_key('end-node-port'):
            #    endNodePort=self.headers['end-node-port']

            self.log.log(cpc.util.log.TRACE,"Trying to reach end node %s"%(endNode))

            server_msg = ServerToServerMessage(endNode)
            server_msg.connect()
            retresp = server_msg.delegateMessage(self.headers.dict,
                                                 self.rfile)
            #TODO send back the response with the headers received
            self.log.log(cpc.util.log.TRACE,"Done. Delegating back reply message of length %d."%
                      len(retresp.message))
            self.send_response(200)
            # the content-length is in the message.
            self.send_header("content-length", len(retresp.message))
            for (key, val) in retresp.headers.iteritems():
                kl=key.lower()
                if kl!="content-length" and kl!="server" and kl!="date":
                    self.log.log(cpc.util.log.TRACE,"Sending header '%s'='%s'"%(kl,val))
                    self.send_header(key,val)
            self.end_headers()
            retresp.message.seek(0)
            self.wfile.write(retresp.message.read(len(retresp.message)))
            #retmmap.close()

        else:
            if(self.isApplicationRoot()):
                request = HttpMethodParser.parsePOST(self.headers.dict,self.rfile) # put message format should be handled exaclty as POST
                self.processMessage(request)

            else:
                self.processMessage()


            if self.server.getState().getQuit():
                self.log.info("shutting down")
                self.server.shutdown()

    def _generateCookie(self):
        #TODO Evaluate randomness of algorithm
        cookie = str(uuid.uuid4())
        self.set_cookie = "cpc-session=%s;"%cookie
        return cookie

    def _handleSession(self, request):
        cookie = None
        if 'user-agent' not in self.headers:
            #for now we don't require the UA
            user_agent = "noUA"
        else:
            user_agent = self.headers['user-agent']

        ip =  self.client_address[0]

        #has the client supplied a cookie?
        if 'Cookie' in self.headers and 'cpc-session' in self.headers['Cookie']:
            try:
                cookie = re.search('cpc-session=([\w-]+)',
                                   self.headers['Cookie']).group(1)
            except AttributeError as e:
                self.log.warning("Received malformed cookie: %s"
                            %self.headers['Cookie'])

        if cookie is None:
            #Generate a new session and ship it
            cookie = self._generateCookie()

        sid = hashlib.sha224(user_agent + ip + cookie).hexdigest()
        session_handler = self.server.getState().getSessionHandler()

        #We don't allow the user to define the cookie, i.e reusage
        session = session_handler.getSession(sid, auto_create=False)
        if session is None:
            cookie = self._generateCookie()
            sid = hashlib.sha224(user_agent + ip + cookie).hexdigest()
            session = session_handler.createSession(sid)
            #set the default project
            try:
                defaultProj=(self.server.getState().getProjectList().
                             defaultProjectName)
            except:
                defaultProj = None
            session['default_project_name'] = defaultProj

        request.session = session

    def processMessage(self,request = None):
        try:
            if request:
                serverCmd=None
                doFinish=False
                serverState=self.server.getState()
                response = cpc.network.server_response.ServerResponse()
                try:
                    self._handleSession(request)
                    scList=self.server.getSCList()
                    serverCmd=scList.getServerCommand(request)
                    serverCmd[0].run(serverState, request, response)
                    doFinish=True

                except cpc.util.CpcError as e:
                    response.add(("%s"%e.__str__()), status="ERROR")
                    self.log.error(e.__str__())

                except:
                    fo=StringIO()
                    traceback.print_exception(sys.exc_info()[0],
                                              sys.exc_info()[1],
                                              sys.exc_info()[2], file=fo)
                    errmsg="Server exception: %s"%(fo.getvalue())
                    response.add(errmsg, status="ERROR")
                    self.log.error(errmsg)

                # now send the response and call the finish() function on the 
                # command
                self._sendResponse(response)
                if doFinish and serverCmd is not None:
                    serverCmd[0].finish(serverState, request)
            else:
                self.send_response(405)
                self.send_header("content-length", 0)
                self.send_header("connection",  "close")
                self.end_headers()
        except cpc.util.CpcError as e:
            self.log.error(e.__str__())
        except:
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0],
                                      sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            errmsg="Server exception: %s"%(fo.getvalue())
            self.log.error(errmsg)

    def _sendResponse(self,retmsg):
        conf = ServerConf()
        rets = retmsg.render()
        self.log.log(cpc.util.log.TRACE,"Done. Reply message is: '%s'\n"%rets)

        self.send_response(self.responseCode)
        self.send_header("content-length", len(rets))
        if 'originating-server' not in retmsg.headers:
            self.send_header("originating-server", conf.getHostName())

        if self.set_cookie is not None:
            self.send_header('Set-Cookie', self.set_cookie)
        for key,value in retmsg.headers.iteritems():
            self.send_header(key, value)

        self.send_header("Connection",  "close")
        self.end_headers()
        if isinstance(rets, mmap.mmap):
            # we need this because strings don't support reads, and
            # write expects this.
            str = rets.read(len(rets))
            #print str
            self.wfile.write(str)
        else:
            self.wfile.write(rets)
        retmsg.close()

        return True


class unverified_handler(handler_base):
    """
    Handles request that comes from an HTTPS connection where no verification
    has been done
    """
    def setup(self):
        handler_base.setup(self)
        self.log=logging.getLogger('crs.server.request_handler_unverified')

class verified_handler(handler_base):
    """
    Handles request that comes from an HTTPS connection where the client is
    verified by the server and thus can be trusted.
    """
    def setup(self):
        handler_base.setup(self)
        self.log=logging.getLogger('crs.server.request_handler_verified')
    def _handleSession(self, request):
        handler_base._handleSession(self,request)
        request.session['user'] = 'root'
