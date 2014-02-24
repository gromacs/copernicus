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


log=logging.getLogger(__name__)


import cpc.util
import apperror
import keywords
#import value


class NetworkError(apperror.ApplicationError):
    pass



class Network(object):
    """The class describing running a function network. A function network is a 
       network of connected function instances, with a list of inputs and 
       outputs. """
    def __init__(self, inFunction=None): #inputs, outputs):
        """Initializes an empty function network.

           inFunction = a function object in which this network will be embedded
        """
        self.instances=dict() # the instance instances. 
        self.connections=[] # the connections

    def addInstance(self, instance):
        """Add a function instance to the network.
           instance = the function instance object."""
        name = instance.getName()
        if name in self.instances:
            raise NetworkError(
                  "Function instance with name '%s' already exists in network."%
                  name)
        self.instances[name]=instance

    def getInstance(self, name):
        try:
            return self.instances[name]
        except KeyError:
            raise NetworkError(
                   "Function instance with name '%s' doesn't exist in network."%
                   name)


    def findConnectionSrcDest(self, conn, affectedInputAIs, affectedOutputAIs):
        """Non-active networks have no active instances."""
        pass

    def addConnection(self, conn, source):
        """Connect a connection within the network. """
        conn.connect()
        self.connections.append(conn)

    def removeConnection(self, conn):
        """Remove a connection."""
        conn.disconnect()
        self.connections.remove(conn)

    def getInstances(self):
        return self.instances

    def writeXML(self, outFile, indent=0):
        """Write an XML description of the network."""
        indstr=cpc.util.indStr*indent
        outFile.write('%s<network>\n'%indstr)
        for inst in self.instances.itervalues():
            if inst.getName() != keywords.Self:
                inst.writeXML(outFile, indent+1)
        for conn in self.connections:
            if not conn.isImplicit():
                conn.writeXML(outFile, indent+1)
        outFile.write('%s</network>\n'%indstr)


