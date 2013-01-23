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
import mmap
from cpc.util import json_serializer
class ServerResponse(object):
    '''
    data structure for the command ser ver response format.
    '''

    def __init__(self):
        #self.response = dict()
        self.headers = dict()
        self.headers['Content-Type'] = 'text/json'  #default response format 
        self.resp = []
        self.file = None
        self.mmap = None

    def add(self, message, data=None, status="OK"):
        newresp=dict()
        if message is not None:
            newresp['message'] = message
        if data is not None:
            newresp['data'] = data
        newresp['status']=status
        self.resp.append(newresp)

    def append(self, otherResponse):
        for r in otherResponse.resp:
            self.reps.append(r)

    def setFile(self, file,contentTypeStr):
        """
        The contentTypeStr is a tuple when sent from request_handler (using
        guess_type from mimetypes) and a bare string when called from commands,
        so we check the type.
        """
        if isinstance(contentTypeStr, basestring):
            self.headers['Content-Type'] = contentTypeStr
        else:
            self.headers['Content-Type'] = contentTypeStr[0]
        self.file=file

    def clearAll(self):
        del self.resp
        self.resp = []
        
    #def setStatus(self,message):
    #    self.response['status'] = message
    #    
    #def setData(self,data):
    #    self.response['data'] = data
    
    def render(self):
        #TODO set response based on contenttype
        
        """ returns the response in JSON format """        
        
        if self.file is None:
            return json.dumps(self.resp,default = json_serializer.toJson,
                              indent=4)
        else:
            self.file.seek(0)
            self.mmap= mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            return self.mmap
       
    def close(self):
        if self.mmap is not None:
            self.mmap.close()

        
