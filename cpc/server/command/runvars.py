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
import re
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


import cpc.util


class RunVars(object):
    """The run variables are a set of variables that are expanded on the
       command line of executables. They are defined by the worker or 
       by the platform plugin.
       The worker then calls the expandStr() method to expand all the 
       variables in the string iteratively. For example:

       runvars=RunVars()
       runvars.add("NCORES", 10)
       runvars.add("RUN_DIR", "/home/bla")
       runvars.add("NTCMD", "-nt $NCORES")
       cmdstring_in="mdrun $NTCMD -multidir ${RUN_DIR}"
       cmdstirng_out=runvars.expandStr(cmdstring_in)
       
       cmdstring_out will then read:
       mdrun -nt 10 -multidir /home/bla."""
    def __init__(self):
        self.vars=dict()
    def add(self, name, value):
        """Add a variable with name and value"""
        self.vars[name]=value
    def addRunVars(self, other):
        """Add all variables from another RunVars object.
           other = a runvars object"""
        for name, value in other.vars.iteritems():
            self.vars[name]=value
    def expandStr(self, str):
        """Expand all variables in this string iteratively.
           str = the string to expand
           returns: the expanded string."""
        def replDict(matchobj):
            name=matchobj.group(0)[1:]
            if self.vars.has_key(name):
                foundMatch=True
                return self.vars[name]
            else:
                return matchobj.group(0)
        sre=re.compile("\$[a-zA-Z_][a-zA-Z0-9_]*")
        #sre2=re.compile("\${[^}]*}")
        i=0 
        nstr=""
        foundMatch=True
        while foundMatch and i<10: # we limit the amount of iterations
            foundMatch=False
            nstr=sre.sub(replDict, str)
            nstr2=sre.sub(replDict, nstr)
            str=nstr2
            i+=1
        return str


        
class RunVarReaderError(cpc.util.CpcXMLError):
    pass


class RunVarReader(xml.sax.handler.ContentHandler):
    """XML Reader for runvars."""
    def __init__(self):
        self.runvars=RunVars()

    def getRunVars(self):
        return self.runvars

    def read(self,filename):
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inf=open(filename, 'r')
        parser.parse(inf)
        inf.close()

    def readString(self, str, description):
        """Read the XML from the string str. 'description' describes the 
           source of this XML in exceptions."""
        parser=xml.sax.make_parser()
        parser.setContentHandler(self)
        inputSrc=xml.sax.InputSource()
        inputSrc.setByteStream(StringIO(str))
        inputSrc.setPublicId(description)
        inputSrc.setSystemId(description)
        parser.parse(inputSrc)

    def setDocumentLocator(self, locator):
        self.loc=locator

    def startElement(self, name, attrs):
        if name == "run-vars":
            pass
        elif name == "run-var":
            if not attrs.has_key('name'):
                raise RunVarReaderError("Run var has no name", self.loc)
            if not attrs.has_key('value'):
                raise RunVarReaderError("Run var has no value", self.loc)
            self.runvars.add(attrs.getValue('name'), attrs.getValue('value'))
        else:
            raise RunVarReaderError("Unknown tag %s"%name, self.loc)

