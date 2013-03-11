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
import tempfile
import mimetools
import cgi
import logging
import shutil
import filecmp
import os
import cpc.util.log
'''
Created on Mar 7, 2011

@author: iman
'''
from cpc.network.server_request import ServerRequest
import urlparse


log=logging.getLogger('cpc.server.http_method_parser')
#handles parsing of the HTTP methods
class HttpMethodParser(object):
    '''
    classdocs
    '''
    
    def __init__(self):
        pass
    
    '''
    input dict headers,string path
    '''
    @staticmethod
    def parseGET(headers,path):
        #separate the request params from the path   
        splittedPath = path.split('?')   
        msg = splittedPath[1]
        parsedDict = urlparse.parse_qs(msg)  #Note values here are stored in lists, this is so one can handle many inputs with same name, for now we dont want that as our multipart parsing does not support it 
        params = dict()
        for k,v in parsedDict.iteritems():
            params[k] = v[0]
        
          
        request = ServerRequest(headers,None,params)   
        return request

    '''
    Input: dict headers, file message
    '''
    @staticmethod
    def parsePUT(headers,message):
        pass
    
   
    '''
    Input: dict headers, file message
    '''
    @staticmethod
    def parsePOST(headers,message):
          
        if ServerRequest.isMultiPart(headers['content-type']):
            request = HttpMethodParser.handleMultipart(headers,message)
        
        else:
            request = HttpMethodParser.handleSinglePart(headers, message)
       
        #after this is done the application XML parser should be adapted to handle non xml style commands
        #next step is to make the parsing more general to work with browser, NOTE done in web branch
        
        return request
    
    
    
    #handles singlepart POST messages  
    @staticmethod  
    def handleSinglePart(headers,message):
        contentLength = long(headers['content-length'])
        if headers['content-type'] == 'application/x-www-form-urlencoded' or headers['content-type'] == 'application/x-www-form-urlencoded; charset=UTF-8': #TODO generalize
            msg =  message.read(contentLength)
            log.log(cpc.util.log.TRACE,'RAW msg is %s'%msg)
            parsedDict = urlparse.parse_qs(msg)  #Note values here are stored in lists, this is so one can handle many inputs with same name, for now we dont want that as our multipart parsing does not support it
            params = dict()
            for k,v in parsedDict.iteritems():
                params[k] = v[0]

            request = ServerRequest(headers,None,params)   #FIXME Right now we are assuming messages cannot be that big

        return request
    
    
    @staticmethod
    def handleMultipart(mainHeaders,msgStream):
        files = dict()
        params = dict()

        BOUNDARY = "--"+HttpMethodParser.extractBoundary(mainHeaders)        
        stopBoundary = BOUNDARY+"--"
        terminateBoundary = ''
        
        msgStream.readline() #has an empty line at start that we want to get rid of
          
        while terminateBoundary != stopBoundary:
            headers = mimetools.Message(msgStream)
            
            terminateBoundary = ''
            log.log(cpc.util.log.TRACE,'multipart headers are %s'%headers.headers)
            
            if(ServerRequest.isFile(headers['Content-Disposition'])):
                file = tempfile.TemporaryFile(mode="w+b")
            
            name =  ServerRequest.getFieldName(headers['Content-Disposition'])            
            notused,contentDispositionParams = cgi.parse_header(headers['Content-Disposition'])                        
            name = contentDispositionParams['name']
             
            
            #if we have a content length we just read it and store the data
            
            contentLength = headers.getheader('Content-Length')
            if(contentLength):   # If a content length is sent we parse the nice way
                bytes = int(contentLength)
                if(ServerRequest.isFile(headers['Content-Disposition'])):
                    file.write(msgStream.read(bytes))
                    
                else: 
                    line  = msgStream.read(bytes)
                    log.log(cpc.util.log.TRACE,"line is "+line)
                    params[name] = line  
                    
                msgStream.readline()    ## we will have a trailin CRLF that we just want to get rid of
            
            if(ServerRequest.isFile(headers['Content-Disposition'])):
                readBytes = 0
                while(True):
                    line = msgStream.readline()                    
                    if re.search(BOUNDARY,line):
                        #time to wrap it up
                        
                        if(line[-2:] == '\r\n'):                          
                            line = line[:-2]
                        elif(line[-1:] == '\n'):                     
                            line = line[:-1]
                        
                        terminateBoundary = line                                               
                        
                        file.seek(0)
                        skipBytes = 2

                        realFile = tempfile.TemporaryFile(mode="w+b")
                        realFile.write(file.read(readBytes-skipBytes))
                        
                        file.close()                        
                        realFile.seek(0)
                        
                        #For testing during dev only!!
                        #runTest(realFile)                                                      
                        
                        files[name]= realFile
                        break
                    else:
                        readBytes +=len(line)
                        file.write(line)   
                
            else:  
                while(True):
                    line = msgStream.readline()

                    if(line[-2:] == '\r\n'):                      
                        line = line[:-2]
                    elif(line[-1:] == '\n'):                     
                        line = line[:-1]
                                            
                    if re.search(BOUNDARY,line):       
                        terminateBoundary = line   
                        break;                                 
                    
                    else:
                        if name in params:
                            params[name]+= line
                        else: 
                            params[name] = line    
            
        return ServerRequest(mainHeaders,None,params,files)

    
    @staticmethod
    #//extracts the boundary sent from the header
    def extractBoundary(headers):
        regexp = 'boundary=(.*)'

        if 'Content-Type' in headers:
            contentType = headers['Content-Type']
        else:
            contentType = headers['content-type']

        match = re.search(regexp,contentType)

        if match == None:
            raise Exception('Could not find a multipart message boundary')

        else:
            return match.group(1)


    #tests the file against a reference file 
    # this test can be run if one sees problems with the file transfer in multipart POST
    # send a file, and specify the path in the referenceFilename variable
    # will test that the received file that was parsed has same content and size as reference file
    def runTest(self,realFile):
        #                        For TESTING PURPOSES
        #referenceFilename = "/Users/iman/Desktop/snowleopard_10a432_userdvd.dmg"
        referenceFilename = "/Users/iman/Documents/workspace/copernicus/examples/single.tar.gz"
        resultFilename = "/Users/iman/Desktop/cpctemp/resfile"                        
                              
        cpfile = open(resultFilename,"w+b")
        shutil.copyfileobj(realFile,cpfile)
        cpfile.close()
        realFile.seek(0) 
        
        fileEquals = filecmp.cmp(referenceFilename,resultFilename)
        print "IMAN file match is %s"%fileEquals
        print "original file size is %d and transferred size is %d"%(os.path.getsize(referenceFilename),os.path.getsize(resultFilename))
        
        realFile.seek(0)

        
