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


import mimetypes
import mmap
import tempfile

class Messaging:
    '''
    classdocs
    '''  

    BOUNDARY = '----------COPERNICUS'
    CRLF = "\r\n"
#

    @staticmethod
    def encode_multipart_formdata(fields = [], files = [],headers = []):
        CRLF = "\r\n"
        L = []

        #create an mmap object

        BOUNDARY = Messaging.BOUNDARY
        for input in fields:
            L.append("--"+BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' %input.name)
            L.append('Content-Length: %s' %len(input.value))
            L.append('')
            L.append(input.value)
        for input in files:
            L.append('--'+BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (input.name,input.filename))
            L.append('Content-Type: %s' % Messaging.get_content_type(input.filename))
            L.append('Content-Length: %s' %len(input.value))
            L.append('')
            L.append(input.value)
        L.append("--"+BOUNDARY+"--")

        file = tempfile.TemporaryFile(mode="w+b")
        
        

        elemCount = len(L)
        for i in range(elemCount):
            file.write(L[i])
            if i!= elemCount-1:
                file.write(CRLF)

        file.write(CRLF)
        file.seek(0)
        
        #for debug during dev only
#        reqfile = open("/Users/iman/Desktop/tempreq.txt",'w+b')       
#        shutil.copyfileobj(file,reqfile)
#        reqfile.close()
        #################
        
        body = mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ)
        return body

    @staticmethod
    def get_content_type(filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'                                                     
