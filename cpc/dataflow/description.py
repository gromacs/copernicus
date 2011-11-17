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
import copy
import textwrap
import xml.sax
import xml.sax.saxutils

log=logging.getLogger('cpc.dataflow.description')

import cpc.util
import apperror


class Describable(object):
    """An object with a description."""
    def __init__(self):
        self.desc=None
    def setDescription(self, desc):
        self.desc=desc
    def getDescription(self):
        return self.desc

class Description(object):
    """A description of a function or an input/output type."""
    def __init__(self, desc):
        """Initialize with a description string. Normally, this would only
           happen from within a DescriptionReader."""
        self.desc=desc

    def output(self, outf):
        tw=textwrap.TextWrapper(initial_indent="   ", subsequent_indent="   ")
        outf.write(tw.wrap(desc))

    def get(self):
        return self.desc

    def writeXML(self, outf, indent=0):
        indstr=cpc.util.indStr*indent
        outf.write('%s<desc>%s</desc>\n'%(indstr, 
                                          xml.sax.saxutils.escape(self.desc)))


class DescXMLErr(apperror.ApplicationXMLError):
    def __init__(self, msg, reader):
        loc=reader.getLocator()
        if loc is not None:
            self.str = "%s (line %d, column %d): %s"%(reader.getFilename(),
                                                      loc.getLineNumber(),
                                                      loc.getColumnNumber(),
                                                      msg)
        else:
            self.str=" %s: %s"%(reader.getFilename(), msg)


class DescriptionReader(xml.sax.handler.ContentHandler):
    """XML reader for descriptions."""
    def __init__(self, describable, filename):
        """Initialize the reader object basd on a describable object."""
        self.desc=describable
        self.descStr=""
        self.filename=filename
    
    def finish(self):
        #log.debug("Setting description %s"%(self.descStr))
        self.desc.setDescription(Description(self.descStr))

    def setDocumentLocator(self, locator):
        self.loc=locator
    def getFilename(self):
        return self.filename
    def getLocator(self):
        return self.loc

    def startElement(self, name, attrs):
        if name == "desc":
            pass
        else:
            raise DescXMLError("Unknown element %s", self)
    
    def endElement(self, name):
        if name == "desc":
            pass
        else:
            raise DescXMLError("Unknown element %s", self)
    
    def characters(self, content):
        self.descStr += xml.sax.saxutils.unescape(content).strip()


