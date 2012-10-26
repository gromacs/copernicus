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



import xml.sax

import cpc.util

class ResourceError(cpc.util.CpcError):
    pass

class Resource(object):
    """A resource object that contains information about a specific 
        resource (such as number of cores, amount of memory, etc.). 
       
        Commands contain a requiredResource and a reservedResource
        list, and platforms contain a list of resources. These can then
        be matched together when a worker requests a set of commands.
        
        The object's member variables are used directly. """
    def __init__(self, name, value):
        """Initialize a resource object.
           name = resource name
           min  = minimum value
           max  = maximum value
           pref = preferred value."""
        self.name=name
        self.value=value

    def add(self, other):
        """Add two resource objects together."""
        if self.name != other.name:
            raise ResourceError("Adding two un-like resources: %s and %s"%
                                (self.name, other.name))
        self.value += other.value

    def subtract(self, other):
        """Subtract other's resource from self."""
        if self.name != other.name:
            raise ResourceError("Subtracting two un-like resources: %s and %s"%
                                (self.name, other.name))
        self.value += other.value

    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outf.write('%s<resource name="%s" value="%d" />\n'%(indstr, self.name, 
                                                            self.value))

class ResourceReaderError(cpc.util.CpcXMLError):
    pass

class ResourceReader(xml.sax.handler.ContentHandler):
    """xml reader for resources."""
    def __init__(self):
        self.resources=[]
    def getResourceList(self):
        return self.resources
    def read(self, filename):
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inf=open(filename, 'r')
        parser.parse(inf)
        inf.close()
    def setDocumentLocator(self, locator):
        self.loc=locator
    def startElement(self, name, attrs):
        if name == "resource":
            if not attrs.has_key('name'):
                raise ResourceReaderError("Resource has no name", self.loc)
            if not attrs.has_key('value'):
                raise ResourceReaderError("Resource has no value", self.loc)
            rname=attrs.getValue('name')
            valst=attrs.getValue('value')
            try:
                value=int(valst)
            except:
                raise ResourceReaderError("Resource %s value '%s' not a number"%
                                          (name, value), self.loc)
            self.resources.append(Resource(rname, value))
        else:
            raise ResourceReaderError("Unknown tag %s"%name, self.loc)




