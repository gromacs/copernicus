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

from cpc.util.conf.server_conf import ServerConf
from cpc.util.version import __version__

from server_command import ServerCommand
from server_command import ServerCommandError
from cpc.dataflow.vtype import instanceType
from cpc.network.node import Nodes, getSelfNode
from cpc.client.message import ClientMessage
from cpc.network.com.client_response import ProcessedResponse
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


class SCTestServer(ServerCommand):
    """Test server command"""

    def __init__(self):
        ServerCommand.__init__(self, "test-server")

    def run(self, serverState, request, response):
        conf = ServerConf()
        response.add('Server: %s, version:   %s' % (conf.getHostName(),
                                                    __version__))
        log.info("Server version %s" % __version__)


class SCServerInfo(ServerCommand):
    def __init__(self):
        ServerCommand.__init__(self, "server-info")

    def run(self, serverState, request, response):
        conf = ServerConf()

        info = dict()
        info['fqdn'] = conf.getHostName()
        info['version'] = __version__
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

class SCStatus(ServerCommand):
    """ Fetches general information about the server, network and projects """
    def __init__(self):
        ServerCommand.__init__(self, "status")

    def run(self, serverState, request, response):
        ret_dict = {}

        # handle project status
        ret_prj_dict = {}
        list_project = request.getParam('project')
        if list_project is not None:
            # client only want info for this project
            projects = [list_project]
        else:
            projects = serverState.getProjectList().list()
        for prj_str in projects:
            ret_prj_dict[prj_str] = dict()
            queue = {'queue' : [], 'running': []}
            state_count = {}
            err_list=[]
            warn_list=[]
            prj_obj = serverState.getProjectList().get(prj_str)
            # we iterate over the childred rather than calling _traverseInstance
            # here to avoid the project itself being counted as an instance
            for child in prj_obj.getSubValueIterList():
                self._traverseInstance(prj_obj.getSubValue([child]), 
                                       state_count, queue, err_list, 
                                       warn_list)
            ret_prj_dict[prj_str]['states'] = state_count
            ret_prj_dict[prj_str]['queue']  = queue
            ret_prj_dict[prj_str]['errors'] = err_list
            ret_prj_dict[prj_str]['warnings'] = warn_list
        ret_dict['projects'] = ret_prj_dict
        if list_project is not None:
            # client only want info for this project, return with that.
            response.add("", ret_dict)
            return

        # handle network
        topology = self._getTopology(serverState)
        num_workers = 0
        num_servers = 0
        num_local_workers = len(serverState.getWorkerStates())
        num_local_servers = len(ServerConf().getNodes().nodes)
        for name, node in topology.nodes.iteritems():
            num_workers += len(node.workerStates)
            num_servers += 1
        ret_dict['network'] = {
            'workers': num_workers,
            'servers': num_servers,
            'local_workers': num_local_workers,
            'local_servers': num_local_servers
        }

        response.add("", ret_dict)

    def _handle_instance(self, instance, state_count, queue, 
                         err_list, warn_list):
        """ Parse an instance: check for errors, state etc """
        stateStr=instance.getStateStr()
        if stateStr in state_count:
            state_count[stateStr] += 1
        else:
            state_count[stateStr] = 1
        if stateStr == "error":
            err_list.append(instance.getCanonicalName())
        elif stateStr == "warning":
            warn_list.append(instance.getCanonicalName())
        for task in instance.getTasks():
            for cmd in task.getCommands():
                if cmd.getRunning():
                    queue['running'].append(cmd.toJSON())
                else:
                    queue['queue'].append(cmd.toJSON())

    def _traverseInstance(self, instance, state_count, queue, 
                          err_list, warn_list):
        """Recursively traverse the instance tree, depth first search"""
        self._handle_instance(instance, state_count, queue, err_list, warn_list)
        for child_str in instance.getSubValueIterList():
            child_obj = instance.getSubValue([child_str])
            if child_obj is not None:
                if child_obj.getType() == instanceType:
                    self._traverseInstance(child_obj,state_count, queue, 
                                           err_list, warn_list)

    def _getTopology(self, serverState):
        """ Fetches topology information about the network """
        # TODO Caching
        conf = ServerConf()
        topology = Nodes()
        thisNode = getSelfNode(conf)
        thisNode.nodes = conf.getNodes()
        thisNode.workerStates = serverState.getWorkerStates()
        topology.addNode(thisNode)
        for node in thisNode.nodes.nodes.itervalues():
            if not topology.exists(node.getId()):
                #connect to correct node
                clnt = ClientMessage(node.host, node.https_port, conf=conf)
                #send along the current topology
                rawresp = clnt.networkTopology(topology)
                processedResponse = ProcessedResponse(rawresp)
                topology = processedResponse.getData()
        return topology
