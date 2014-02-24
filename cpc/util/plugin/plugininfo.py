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
import logging

import plugin
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


log=logging.getLogger(__name__)

class PluginInfo(xml.sax.handler.ContentHandler):
    def __init__(self, plugin):
        """Initialize based on plugin output."""
        # default values        "
        self.OK=False
        self.protocolVersion=None
        self.name=None
        self.type=None
        self.errMsg=None
        self.capabilities={}        
        returncode, retst=plugin.call(".", "info", [])
        
        log.debug("Plugin info for %s returned %d, '%s'"%(plugin.name, 
                                                          returncode, retst))
        if returncode == 0:
            self._readString(retst, "%s plugin %s"%(plugin.type, plugin.name))
        else:
            self.errMsg=retst

    def getName(self):
        """Get the plugin's name according to the plugin info."""
        return self.name
    def getType(self):
        """Get the plugin's type according to the plugin info."""
        return self.type
    def getProtocolVersion(self):
        """Get the plugin's protocol version."""
        return self.protocolVersion    
    def getCapability(self, name):
        """Get a specific capability value, or 'False' if it wasn't listed."""
        if not self.capabilities.has_key(name):
            return False
        return self.capabilities[name]

    def _readString(self, str, description):
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
        if name == "plugin":
            if attrs.has_key("protocol_version"):
                pvs=attrs.getValue("protocol_version")
                sp=pvs.split('.')
                i=0
                self.protocolVersion=[]
                for s in sp:
                    try:
                        self.protocolVersion.append(int(s))
                    except ValueError:
                        errst=("Malformed protocol version in %s plugin %s: %s"%
                               (self.plugin.type, 
                                self.plugin.name, 
                                pvs))
                        raise plugin.PluginError(errst)
                    i+=1 
            else:
                raise plugin.PluginError("No protocol version in plugin")
            if attrs.has_key("type"):
                self.type=attrs.getValue("type")
            if attrs.has_key("name"):
                self.type=attrs.getValue("name")
            self.OK=True
        elif name == "capability":
            if not attrs.has_key("name"):
                raise plugin.PluginError("No name for capability")
            if not attrs.has_key("value"):
                raise plugin.PluginError("No value for capability")
            name=attrs.getValue('name')
            val=attrs.getValue('value')
            if val == "yes":
                val=True
            if val == "no":
                val=False
            self.capabilities[name]=val

            



