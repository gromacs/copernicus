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

import cpc.util
import cpc.util.log
import resource


log=logging.getLogger(__name__)

class CommandWorkerMatcher(object):
    """Object that stores information about a worker for the 
       matchCommandWorker() function that is used in queue.getUntil()"""
    def __init__(self, platforms, executableList, workerReqDict):
        self.platforms=platforms
        self.executableList=executableList
        self.workerReqDict=workerReqDict
        maxPlatform=platforms[0]
        # get the platform with the biggest number of cores.
        ncores_max=0
        for platform in platforms:
            if (platform.hasMaxResource('cores')):
                ncores_now=platform.getMaxResource('cores')
                if ncores_now > ncores_max:
                    ncores_max=ncores_now
                    maxPlatform=platform
        self.usePlatform=maxPlatform
        # construct a list of all max. resources with settings for the
        # platform we use.
        self.used=dict()
        for rsrc in self.usePlatform.getMaxResources().itervalues():
            self.used[rsrc.name]=resource.Resource(rsrc.name, 0)
        self.type=None
        self.depleted=False

    def checkType(self, type):
        """Check whether the command type is the same as one used before in the
           list of commands to send back"""
        if self.type is None:
            self.type=type
            return True
        return type == self.type

    def getExecID(self, cmd):
        """Check whether the worker has the right executable."""
        # first try the usePlatform
        
        ret=self.executableList.find(cmd.executable, self.usePlatform,
                                     cmd.minVersion, cmd.maxVersion)
        if ret is not None:
            return ret.getID()
        for platform in self.platforms:
            ret=self.executableList.find(cmd.executable, platform,
                                         cmd.minVersion, cmd.maxVersion)
            if ret is not None:
                return ret.getID()
        return None

    def checkWorkerRequirements(self, cmd):
        #Check if worker is project dedicated
        if 'project' in self.workerReqDict:
            name=cmd.getTask().getProject().getName()
            reqName=self.workerReqDict['project']
            log.debug("Worker is dedicated to proj. %s, command belongs to %s"%
                      (reqName, name))
            if name != reqName:
                return False
        return True

    def checkAddResources(self, cmd):
        """Check whether a command falls within the current resource allocation
           and add its requirements to the used resources if it does.
           cmd = the command to check
           returns: True if the command fits within the capabilities is added,
                    False if the command doesn't fit."""
        for rsrc in self.used.itervalues():
            platformMax = self.usePlatform.getMaxResource(rsrc.name)
            cmdMinRsrc = cmd.getMinRequired(rsrc.name)
            rsrcLeft = platformMax - rsrc.value
            if cmdMinRsrc is not None:
                # check whether there's any left
                if rsrcLeft < cmdMinRsrc:
                    log.debug("Left: %d, max=%d, minimum resources: %d"%
                              (rsrcLeft, platformMax, cmdMinRsrc))
                    self.depleted=True
                    return False
        # now reserve the resources
        cmd.resetReserved()
        for rsrc in self.used.itervalues():
            platformMax = self.usePlatform.getMaxResource(rsrc.name)
            platformPref = self.usePlatform.getPrefResource(rsrc.name)
            cmdMinRsrc = cmd.getMinRequired(rsrc.name)
            cmdMaxRsrc = cmd.getMaxAllowed(rsrc.name)
            if cmdMinRsrc is not None:
                # the total amount of resources left on the current platform:
                rsrcLeft = platformMax - rsrc.value
                if platformPref is not None and rsrcLeft>platformPref:
                    value=platformPref
                elif cmdMaxRsrc is not None and rsrcLeft>cmdMaxRsrc:
                    value=cmdMaxRsrc
                    self.depleted=True
                else:
                    value=rsrcLeft
                # now we know how many
                log.debug("Reserving %d cores"%value)
                cmd.setReserved(rsrc.name, value)
                rsrc.value += value
        return True

    def isDepleted(self):
        """Check whether any of the resources are depleted. """ 
        return self.depleted

    def getWork(self, cmdQueue):
        """Get work from a command queue until the worker is filled or there is
           no more work."""
        return cmdQueue.getUntil(matchCommandWorker, self)


def matchCommandWorker(matcher, command):
    """Function to use in queue.getUntil() to get a number of commands from
       the queue.
       TODO: this is where performance tuning results should be used."""
    cont=True # whether to continue getting commands from the queue
    # whether to use this command: make sure we only have a single type
    use=False
    execID=matcher.getExecID(command)
    log.log(cpc.util.log.TRACE,'exec id is %s'%execID)
    if execID is not None:
        use=(matcher.checkType(command.getTask().getFunctionName()) and
             matcher.checkWorkerRequirements(command))
    if use:
        if matcher.checkAddResources(command):
            use=True
        else:
            use=False
            cont=False
    return (cont, use)


