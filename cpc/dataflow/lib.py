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



import logging
import threading
try:
    from collections import OrderedDict
except ImportError:
    from cpc.util.ordered_dict import OrderedDict


import cpc.util
import apperror
import description
import keywords
import vtype


log=logging.getLogger('cpc.dataflow.lib')


class ImportLibraryError(apperror.ApplicationError):
    pass

class ImportList(object):
    """A class describing a set of import libraries."""
    def __init__(self):
        self.libs=dict()
        self.lock=threading.Lock()

    def add(self, lib):
        """Add an importLibrary to the collection."""
        with self.lock:
            log.debug("Adding new lib %s"%lib.name)
            self.libs[lib.name]=lib
    def exists(self, name):
        """Check whether an importLibrary with such a name exists in 
           the collection."""
        with self.lock:
            return name in self.libs
    def get(self, name):
        """Get the named import library, or None if it doesn't exist."""
        with self.lock:
            return self.libs.get(name)

    def getLibNames(self):
        return self.libs.iterkeys()

    def getFunctionByFullName(self, name, thisImport):
        """Get a function from a full (double colon-separated) name. 
           name = the double colon-separated function name
           thisImport = the library to use for names with no colons."""
        rs=name.rsplit(keywords.ModSep,1)
        if len(rs) > 1:
            # there's a colon in the name. Search the libraries
            flib=rs[0]
            lib=self.get(flib)
            if lib is None:
                raise ImportLibraryError("Module '%s' not found"%flib)
            fname=rs[1]
        else:
            # there's a colon in the name. Search the current import
            fname=name
            lib=thisImport
            if lib is None:
                raise ImportLibraryError("Top-level module not found")
        return lib.getFunction(fname) 
    
    def getTypeByFullName(self, name, thisImport):
        """Get a type from a full (colon-separated) name. 
           name = the colon-separated function name
           thisImport = the library to use for names with no colons."""
        rs=name.rsplit(keywords.ModSep,1)
        if len(rs) > 1:
            # there's a double colon in the name. Search the libraries
            flib=rs[0]
            lib=self.get(flib)
            if lib is None:
                raise ImportLibraryError("Module '%s' not found"%flib)
            fname=rs[1]
        else:
            # there's a colon in the name. Search the defaults list
            if name in vtype.basicTypes:
                return vtype.basicTypes[name] 
            # Then search the current import
            fname=name
            lib=thisImport
            if lib is None:
                raise ImportLibraryError("Top-level module not found")
        return lib.getType(fname) 

    def getItemByFullName(self, name):
        """Get an item: a library, function, or type by its full name."""
        if self.exists(name):
            # it is a library
            return self.libs[name]
        # if it's not a library, split the library out
        rs=name.rsplit(keywords.ModSep,1)
        lib=None
        if len(rs) > 1:
            # there's a double colon in the name. Search the libraries
            lib=self.get(rs[0])
        if lib is None: 
            raise ImportLibraryError("Item %s not found"%name)
        if lib.hasFunction(rs[1]):
            return lib.getFunction(rs[1])
        if lib.hasType(rs[1]):
            return lib.getType(rs[1])
        raise ImportLibraryError("Item %s not found"%name)
        

class ImportLibrary(description.Describable):
    """The class describing an imported source file."""
    def __init__(self, name, filename, network=None):
        """Initializes an new import
    
           name = the import's full (canonical) name
           filename = the import's file name
           network = the network for top-level network descriptions.
                     Only the top-level import should have one.
        """
        self.name=name
        self.filename=filename
        self.types=OrderedDict()
        self.functions=OrderedDict()
        self.network=network
        description.Describable.__init__(self)
    def getName(self):
        """Get the full (canonical) name"""
        return self.name
    def getFilename(self):
        """Get the filename associated with the library."""
        return self.filename
    def addFunction(self, fn):
        """Add one reference to the value."""
        self.functions[fn.getName()] = fn
        fn.setLib(self)
        log.debug("Added function %s to library %s"%(fn.getName(), self.name))

    def getFunctionList(self):
        """Return a list of all function names"""
        return self.functions.keys()
    def getTypeList(self):
        """Return a list of all types"""
        return self.types.keys()

    def addType(self, tp):
        """Ad one type to the collection."""
        self.types[tp.getName()] = tp
        tp.setLib(self)
        log.debug("Added type %s to library %s"%(tp.getName(), self.name))

    def getFunction(self, name):
        try:
            return self.functions[name]
        except KeyError:
            raise ImportLibraryError("Function %s not found in library %s"%
                                     (name, self.name))

    def hasFunction(self, name):
        """Check whether the library has this function"""
        return name in self.functions

    def getType(self, name):
        try:
            return self.types[name]
        except KeyError:
            raise ImportLibraryError("Type %s not found in library %s"%
                                     (name, self.name))

    def hasType(self, name):
        """Check whether the library has this type"""
        return name in self.types

    def getNetwork(self):
        return self.network

    def writeXML(self, outf, indent=0):
        """Write the function definitions (and possibly a top-level network 
           description) in XML to outf."""
        #indstr=cpc.util.indStr*indent
        #outf.write('%s<cpc>\n'%indstr)
        for tp in self.types.itervalues():
            if not tp.isImplicit():
                tp.writeXML(outf, indent)
                outf.write('\n')
        for fn in self.functions.itervalues():
            fn.writeXML(outf, indent)
            outf.write('\n')
        if self.network is not None:
            self.network.writeXML(outf, indent)
            outf.write('\n')
        #outf.write('%s</cpc>\n'%indstr)

