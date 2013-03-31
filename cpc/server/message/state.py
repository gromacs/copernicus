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

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from cpc.util.conf.server_conf import ServerConf, ServerIdNotFoundException
from cpc.util.version import __version__

from server_command import ServerCommand
from server_command import ServerCommandError
from cpc.server.state.user_handler import UserLevel, UserHandler, UserError
from cpc.dataflow.lib import getModulesList
log = logging.getLogger('cpc.server.message.state')

class SCStop(ServerCommand):
    """Stop server command"""

    def __init__(self):
        ServerCommand.__init__(self, "stop")

    def run(self, serverState, request, response):
        log.info("Stop request received")
        serverState.doQuit()
        response.add('Quitting.')


class SCSaveState(ServerCommand):
    """Save the server state"""

    def __init__(self):
        ServerCommand.__init__(self, "save-state")

    def run(self, serverState, request, response):
        serverState.write()
        response.add('Saved state.')
        log.info("Save-state request received")


class SCPingServer(ServerCommand):
    """Test server command"""

    def __init__(self):
        ServerCommand.__init__(self, "ping")

    def run(self, serverState, request, response):
        response.add("OK")


class SCServerInfo(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "server-info")

    def run(self, serverState, request, response):
        conf = ServerConf()

        info = dict()
        info['fqdn'] = conf.getFqdn()
        info['version'] = __version__

        try:
            conf.getServerId()
            info['serverId'] = conf.getServerId()
        except ServerIdNotFoundException as e:
            print "not found"
            info['serverId'] = "ERROR: %s"%e.str
        response.add("",info)

class SCListServerItems(ServerCommand):
    """queue/running/heartbeat list command """

    def __init__(self):
        ServerCommand.__init__(self, "list")

    def run(self, serverState, request, response):
        toList = request.getParam('type')
        retstr = ""
        if toList == "queue":
            list = serverState.getCmdQueue().list()
            queue = []
            for cmd in list:
                queue.append(cmd.toJSON())
            running = []
            cmds = serverState.getRunningCmdList().getCmdList()
            for cmd in cmds:
                running.append(cmd.toJSON())
            retstr = {"queue": queue, "running": running}
        elif toList == "running":
            running = []
            cmds = serverState.getRunningCmdList().getCmdList()
            for cmd in cmds:
                running.append(cmd.toJSON())
            retstr = running
        elif toList == "heartbeats":
            heartbeats = serverState.getRunningCmdList().toJSON() #.list()
            retstr = heartbeats
        elif toList == "users":
            retstr = UserHandler().getUsersAsList()
        elif toList == "modules":
            retstr = getModulesList()


        else:
            raise ServerCommandError("Unknown item to list: '%s'" % toList)
        response.add(retstr)
        log.info("Listed %s" % toList)



class SCReadConf(ServerCommand):
    """Update the configuration based on new settings."""

    def __init__(self):
        ServerCommand.__init__(self, "readconf")

    def run(self, serverState, request, response):
        conf = ServerConf()
        conf.reread()
        response.add("Reread configuration.")
        log.info("Reread configuration done")

