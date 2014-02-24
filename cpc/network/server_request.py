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


import re
import cpc.util
import urllib
from cpc.network.http.messaging import Messaging
import logging
log=logging.getLogger(__name__)

class ServerRequest(object):
    """Server request object; contains all the fields as 'fields' (strings) or
       'files' (temporary files)."""
   
    CRLF = '\r\n'

    def __init__(self,headers,msg=None,params=None,files=None,bigFile=None):
        # NOTE only adapted for sending messages at the moment
        #msg is a file descriptor
        self.msg = msg
        self.headers = headers
        self.params = params or dict()
        self.files =  files or dict()
        self.session = None
        # handler-set flags
        self.flags = None

    def __del__(self):
        del self.files # remove the reference; files should be deleted.
 
    def getCmd(self):
        #return self.params['cmd']
        return self.getField('cmd')
    
    def getJob(self):
        return self.getField('job')
    
    def getField(self,fieldName):
        ''' gets a property based on its fieldname'''
        if self.params.has_key(fieldName):
            return self.params[fieldName]
        else: 
            return None

    def getFlag(self, name):
        """gets a request-handler-defined property - or None."""
        if self.flags is None:
            return None
        return self.flags[name]

    def setFlag(self, name, value):
        """Sets a request-handler-defined property - allocating a dict if 
           it needs to."""
        if self.flags is None:
            self.flags=dict()
        self.flags[name]=value

    def getParam(self,paramName):
        ''' gets a property based on its paramname'''
        #returns None if paramName is not found
        return self.params.get(paramName,None)  

    def hasParam(self,paramName):
        ''' Returns whether a property has been set'''
        return self.params.has_key(paramName)

    def addField(self, fieldName, msg):
        """Add a field to a request."""
        self.fields[fieldName]=msg
    def addFile(self, filename, fileObject):
        """Add an open file to a request."""
        self.files[filename] = fileObject

    def getFile(self, fileName):
        try:
            ret=self.files[fileName]
        except KeyError:
            raise cpc.util.CpcError("File '%s' not found in request"%fileName)
        return ret

    def haveFile(self, fileName):
        return self.files.has_key(fileName)

    @staticmethod
    def parseHeaders(headerString):
        headers = dict()
        headerString = headerString.strip()
        lines = headerString.split('\n')
        
        for line in lines:
            splittedStr = line.split(':')
            headers[splittedStr[0]] = splittedStr[1]
        
        return headers
        
            
    @staticmethod    
    def getFieldName(header):
        namePattern = re.compile('name="(\S+)"')
        match = namePattern.search(header)
        fieldName = match.group(1) 
        return fieldName

    @staticmethod
    def isFile(header):
        filePattern = re.compile('filename="(\S+)"')
        if(filePattern.search(header)):
            return True
        else: 
            return False

    @staticmethod 
    def getBoundary():
        return Messaging.BOUNDARY
    
    @staticmethod
    def getCRLF():
        return '\r\n' 
   
    @staticmethod
    def prepareRequest(fields=[], files=[],headers = None):
        """
        Prepares the HTTP request
        returns:
         ServerRequest
        """
        if headers is None:
            headers = {}
        
        if(len(files)==0):   #single part message         
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            #create a dict of the fields object
            inputs = dict()

            for input in fields:                
                inputs[input.name] = input.value
            ## NOTE encodes in a non standard % format but 
            # this is usually what browsers do
            msg = urllib.urlencode(inputs)   
           

        else:  #multipart message 
            headers['Content-Type'] = ( 'multipart/form-data; boundary=%s' % 
                                        Messaging.BOUNDARY )
            msg = Messaging.encode_multipart_formdata(fields,files) 
        headers['Content-Length'] = len(msg)
        headers['User-agent'] = 'copernicus-cmd-client'
        content = msg
        req = ServerRequest(headers,content)
        return req
   
    @staticmethod
    def isMultiPart(contentType):
        regexp = '^multipart/form-data;'
        return re.search(regexp,contentType)
        
    
    
    
    
    
    
