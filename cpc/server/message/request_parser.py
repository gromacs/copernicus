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

import state
import network
import worker
import project
import user
import tracking 
import cpc.network.server_response
import cpc.util
from cpc.server.state.user_handler import UserLevel

log=logging.getLogger(__name__)


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

        """Get the server command based on a request's command.
           inputs:
            request:ServerRequest

            returns:
                ServerCommand
        """
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


scSecureList=ServerCommandList()

# Various commands with non default access level, for easy overview
scSecureList.add(user.SCLogin(), UserLevel.ANONYMOUS)
scSecureList.add(network.ScAddNodeRequest(), UserLevel.ANONYMOUS)
scSecureList.add(network.ScAddNodeAccepted(), UserLevel.ANONYMOUS)
scSecureList.add(user.SCAddUser(), UserLevel.SUPERUSER)
scSecureList.add(user.SCDeleteUser(), UserLevel.SUPERUSER)
scSecureList.add(user.SCPromoteUser(), UserLevel.SUPERUSER)
scSecureList.add(user.SCDemoteUser(), UserLevel.SUPERUSER)

# state commands
scSecureList.add(state.SCStop())
scSecureList.add(state.SCSaveState())
scSecureList.add(state.SCPingServer())
scSecureList.add(state.SCListServerItems())
scSecureList.add(state.SCReadConf())
scSecureList.add(state.SCServerInfo())

# worker workload requests
scSecureList.add(worker.SCWorkerReady())  
scSecureList.add(worker.SCWorkerReadyForwarded())  
scSecureList.add(worker.SCCommandFinished())
scSecureList.add(worker.SCCommandFinishedForward())  
scSecureList.add(worker.SCCommandFailed())  
# heartbeat requests
scSecureList.add(worker.SCWorkerHeartbeat())
scSecureList.add(worker.SCHeartbeatForwarded())
scSecureList.add(worker.SCDeadWorkerFetch())
# overlay network topology
scSecureList.add(network.ScAddNode())
scSecureList.add(network.ScListNodes())
scSecureList.add(network.ScRevokeNode())
scSecureList.add(network.ScGrantNodeConnection()) 
scSecureList.add(network.ScGrantAllNodeConnections())    
scSecureList.add(network.ScChangeNodePriority()) 
scSecureList.add(network.SCNetworkTopology())
scSecureList.add(network.SCNetworkTopologyClient())
scSecureList.add(network.SCNetworkTopologyUpdate())
scSecureList.add(network.SCConnectionParamUpdate())

# asset tracking
scSecureList.add(tracking.SCPullAsset())
scSecureList.add(tracking.SCClearAsset())
# requests for dataflow
scSecureList.add(project.SCProjects())
scSecureList.add(project.SCProjectStart())
scSecureList.add(project.SCProjectDelete())

scSecureList.add(project.SCProjectGrantAccess())
scSecureList.add(project.SCProjectSave())
scSecureList.add(project.SCProjectLoad())
scSecureList.add(project.SCProjectGetDefault())
scSecureList.add(project.SCProjectSetDefault())
scSecureList.add(project.SCProjectActivate())
scSecureList.add(project.SCProjectDeactivate())
scSecureList.add(project.SCProjectRerun())
scSecureList.add(project.SCProjectUpload())
scSecureList.add(project.SCProjectList())
scSecureList.add(project.SCProjectInfo())
scSecureList.add(project.SCProjectDebug())
scSecureList.add(project.SCProjectImport())
scSecureList.add(project.SCProjectAddInstance())
scSecureList.add(project.SCProjectConnect())
scSecureList.add(project.SCProjectGraph())
scSecureList.add(project.SCProjectSet())
scSecureList.add(project.SCProjectGet())
scSecureList.add(project.SCProjectTransact())
scSecureList.add(project.SCProjectCommit())
scSecureList.add(project.SCProjectRollback())
scSecureList.add(project.SCProjectLog())
scSecureList.add(project.SCStatus())

