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


#try:
#    from cStringIO import StringIO
#except ImportError:
#    from StringIO import StringIO
#
#
#import sys
#import traceback
import logging


import server_command 
import trackingcmd 
import workercmd
import projectcmd
import cpc.network.server_response
import cpc.util
from cpc.server.state.user_handler import UserLevel

log=logging.getLogger('cpc.server.request_parser')


class ServerCommandError(cpc.util.CpcError):
    pass

class ServerCommandList(object):
    """An object list that takes a request and runs the right server command 
       object's request handler."""
    def __init__(self):
        self.cmds=dict()

    def add(self, cmd, userlevel=UserLevel.REGULAR_USER):
        """Add a single server command to the list."""
        name=cmd.getRequestString()
        self.cmds[name]=(cmd, userlevel)

    def getServerCommand(self, request):
        """Get the server command based on a request's command."""
        cmd=request.getCmd()
        if cmd in self.cmds:
            user_str = 'Anonymous'

            #check user level
            required_level = self.cmds[cmd][1]
            if required_level > UserLevel.ANONYMOUS:
                #it requires at least auth
                if 'user' not in request.session:
                    log.info('Unauthorized user requested command "%s"'%cmd)
                    raise cpc.util.CpcError("This command requires login")

                #match command requirement against user level
                user_obj = request.session['user']
                user_str = user_obj.getUsername()
                if required_level > user_obj.getUserlevel():
                    log.info("user '%s' requested command '%s', which is above"
                    "its user level"%(user_str, cmd))
                    raise cpc.util.CpcError(
                        "You don't have access to this command")
            log.info('[%s] Request: %s'%(user_str, cmd))
            return self.cmds[cmd]
        else:
            raise ServerCommandError("Unknown command %s"%cmd)


# these are the server commands that the secure server may run:
scSecureList=ServerCommandList()

#commands that don't require login
scSecureList.add(server_command.SCLogin(), UserLevel.ANONYMOUS)

#secure commands that require login
scSecureList.add(server_command.SCAddUser(), UserLevel.SUPERUSER)
scSecureList.add(server_command.SCDeleteUser(), UserLevel.SUPERUSER)
scSecureList.add(server_command.SCPromoteUser(), UserLevel.SUPERUSER)
scSecureList.add(server_command.SCDemoteUser(), UserLevel.SUPERUSER)
scSecureList.add(server_command.SCStop())
scSecureList.add(server_command.SCSaveState())
scSecureList.add(server_command.SCTestServer())

# worker workload requests
scSecureList.add(workercmd.SCWorkerReady())  
scSecureList.add(workercmd.SCWorkerReadyForwarded())  
scSecureList.add(workercmd.SCCommandFinished())
scSecureList.add(workercmd.SCCommandFinishedForward())  
scSecureList.add(workercmd.SCCommandFailed())

# heartbeat requests
scSecureList.add(workercmd.SCWorkerHeartbeat())
scSecureList.add(workercmd.SCHeartbeatForwarded())
scSecureList.add(workercmd.SCDeadWorkerFetch())

# overlay network topology
scSecureList.add(server_command.SCListServerItems())
scSecureList.add(server_command.SCReadConf())
scSecureList.add(server_command.ScAddNode())
scSecureList.add(server_command.ScAddNodeRequest())
scSecureList.add(server_command.ScListNodes())
scSecureList.add(server_command.ScListNodeConnectionRequests())
scSecureList.add(server_command.ScListSentNodeConnectionRequests())
scSecureList.add(server_command.ScGrantNodeConnection()) 
scSecureList.add(server_command.ScGrantAllNodeConnections())    
scSecureList.add(server_command.ScChangeNodePriority()) 
scSecureList.add(server_command.SCNetworkTopology())
scSecureList.add(server_command.SCNetworkTopologyUpdate())

# asset tracking
scSecureList.add(trackingcmd.SCPullAsset())
scSecureList.add(trackingcmd.SCClearAsset())

# requests for dataflow
scSecureList.add(projectcmd.SCProjects())
scSecureList.add(projectcmd.SCProjectStart())
scSecureList.add(projectcmd.SCProjectGrantAccess())
scSecureList.add(projectcmd.SCProjectDelete())
scSecureList.add(projectcmd.SCProjectSave())
scSecureList.add(projectcmd.SCProjectLoad())
scSecureList.add(projectcmd.SCProjectGetDefault())
scSecureList.add(projectcmd.SCProjectSetDefault())
scSecureList.add(projectcmd.SCProjectActivate())
scSecureList.add(projectcmd.SCProjectDeactivate())
scSecureList.add(projectcmd.SCProjectRerun())
scSecureList.add(projectcmd.SCProjectUpload())
scSecureList.add(projectcmd.SCProjectList())
scSecureList.add(projectcmd.SCProjectInfo())
scSecureList.add(projectcmd.SCProjectImport())
scSecureList.add(projectcmd.SCProjectAddInstance())
scSecureList.add(projectcmd.SCProjectConnect())
scSecureList.add(projectcmd.SCProjectGraph())
scSecureList.add(projectcmd.SCProjectSet())
scSecureList.add(projectcmd.SCProjectGet())
scSecureList.add(projectcmd.SCProjectTransact())
scSecureList.add(projectcmd.SCProjectCommit())
scSecureList.add(projectcmd.SCProjectRollback())
scSecureList.add(projectcmd.SCProjectLog())

# these are the server commands that may be run by the unencrypted HTTP server
scInsecureList=ServerCommandList()
scInsecureList.add(server_command.ScAddNodeRequest())
scInsecureList.add(server_command.ScAddNodeAccepted())
scInsecureList.add(server_command.ScAddClientRequest())



