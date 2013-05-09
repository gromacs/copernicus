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


import json
import sys

import cpc.util
from cpc.util import json_serializer
class ResponseError(cpc.util.CpcError):
    pass

class ProcessedResponse(object):
    def __init__(self, response): 
        """
            inputs:
                response:ClientResponse
        """
        if response.content_type == "text/json":
            try:                 
                str = response.message.read(len(response.message))
                self.resp=json.loads(str,object_hook=json_serializer.fromJson)
            except:                
                retd=dict()
                retd['status']="ERROR"
                retd['message']=response.message.read(len(response.message))
                print "error %s"%retd
                self.resp=[retd]
        else:
            raise ResponseError("Wrong message type %s for JSON response"%
                                response.content_type)
                        
    def pprint(self,renderMethod = None):
        for item in self.resp:                                     
            if item['status'] == 'OK':
                if renderMethod!=None:                    
                    sys.stdout.write(renderMethod(item))
                    sys.stdout.write("\n")
                else:    
                    sys.stdout.write("%s"%item['message'])
                    sys.stdout.write("\n")                
                    if 'data' in item:
                        str = '%s'%item['data']
                        sys.stdout.write(str)
                        sys.stdout.write("\n")                
            else:
                raise ResponseError(item['message'])


    def isOK(self):
        for item in self.resp:
            if item['status'] != 'OK':
                return False


        return True

    def getMessage(self):
        return self.resp[0]['message']        

    def getData(self):  
        return self.resp[0]['data']

    def getStatus(self):
        return self.resp[0]['status']

class ClientResponse(object):
    """Client's response object. Unpacks the json string and can print it."""
    ###
    ##  Input  HTTPResponse message, dict headers 
    def __init__(self, message,headers=dict()):  
        self.headers = headers
        self.message= message
        
        if headers.has_key('content-type'):
            self.content_type=headers['content-type']
        else:
            self.content_type="unknown"
        self.resp=dict()

    def __del__(self):
        self.message.close()
 
    def close(self):
        """Close the response if it hasn't already been closed."""
        self.message.close()

    def getType(self):
        """Get the content type string of a response."""
        return self.content_type

    def getRawData(self):
        """Get the raw data for an unprocessed response."""
        return self.message
