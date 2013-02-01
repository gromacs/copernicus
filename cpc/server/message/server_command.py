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


import copy
import logging

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from cpc.util.exception import CpcError

log = logging.getLogger('cpc.server.message')

class ServerCommandError(CpcError):
    def __init__(self, msg):
        self.str = msg


class ServerCommand(object):
    """A server command. Constructed in the server command exec class,
        and executed afterwards (possibly in multiple threads at the 
        same time!!) ."""

    def __init__(self, name):
        self.name = name

    def run(self, serverState, request, response):
        """Run the command. Responses should go to response"""
        raise ServerCommandError(
            "Don't know what to do with command '%s'" % (self.name))

    def finish(self, serverState, request):
        """Finish and cleanup the command. No response allowed. 
           Only called if run() threw no exception."""
        pass

    def getRequestString(self):
        """Get the request command string associated with the command."""
        return self.name


