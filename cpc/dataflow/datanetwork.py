# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Magnus Lundborg,
# Erik Lindahl, and others.
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


import threading
import logging
from function import Function, FunctionPrototype
from apperror import ApplicationError
try:
    from collections import OrderedDict
except ImportError:
    from cpc.util.ordered_dict import OrderedDict

log = logging.getLogger(__name__)

class NetworkError(ApplicationError):
    pass

class DataNetwork(object):

    def __init__(self, project=None, name=None, taskQueue=None, dirName="",
                 containingInstance=None):

        self.project = project
        self.name = name
        self.taskQueue = taskQueue
        self.dirName = dirName
        self.lock = threading.RLock()
        self.instances = OrderedDict()
        self.containingInstance = containingInstance

    def _getActiveInstance(self, name):
        """Get the named active instance associated with this network."""
        try:
            if name == self.name:
                return self.containingInstance
            return self.instances[name]
        except KeyError:
            raise NetworkError("Active instance '%s' not found"%name)

    def _getContainingNet(self, instancePathList):
        """Return the tuple of (network, instanceName), for an
           instancePathList"""
        #log.debug("instance path list: %s"%(instancePathList))
        if len(instancePathList)==0 or instancePathList[0] == '':
            return (self, None)
        elif len(instancePathList) < 2:
            return (self, instancePathList[0])
        # otherwise, get the network of the next item in the path.
        topItem=self._getActiveInstance(instancePathList[0])
        topNet=topItem.dataNetwork
        if topNet is None:
            raise NetworkError("Active instance %s has no subnet"%
                               topItem.getName())
        rest=instancePathList[1:]
        return topNet._getContainingNet( rest )

    def addInstance(self, instance):

        assert isinstance(instance, Function)
        with self.lock:
            name = instance.name
            log.debug('Adding instance %s to network. %s' % (name, self.instances))
            if name in self.instances:
                raise NetworkError('Tried to start instance %s which already exists' % name)

            self.instances[name] = instance

    def newInstance(self, prototype, name):

        if isinstance(prototype, FunctionPrototype):
            pr = prototype
        else:
            pr = prototype()

        assert isinstance(pr, FunctionPrototype), "The function prototype of the function must be of class FunctionPrototype."

        with self.lock:
            log.debug('Adding instance %s to network. %s' % (name, self.instances))
            if name in self.instances:
                raise NetworkError('Tried to start instance %s which already exists' % name)

            f = Function(pr, name, self)

            self.instances[name] = f

            return f

    def getInstanceNameList(self):

        with self.lock:
            return self.instances.keys()

    #def getInstanceList(self):

        #with self.lock:
            #return self.instances.values()

    def getActiveInstance(self, name):
        """Get the named active instance associated with this network.
           Throws a NetworkError if not found."""
        with self.lock:
            return self._getActiveInstance(name)

    def tryGetActiveInstance(self, name):
        """Get the named active instance or return None if not found."""
        with self.lock:
            return self.instances.get(name)

    def getActiveInstanceList(self, listIO, listSelf):
        """Return a dict of instance names. If listIO is true, each instance's
           IO items are listed as well"""
        ret=dict()
        with self.lock:
            for inst in self.instances.itervalues():
                il={ "state" : str(inst.state),
                     "fn_name" : str(inst.name) }
                if listIO:
                    inps=inst.getInputNames()
                    outs=inst.getOutputNames()
                    il = { "state" : str(inst.state),
                           "fn_name" : str(inst.name),
                           "inputs": inps,
                           "outputs" : outs }
                ret[inst.name] = il
            if listSelf and (self.containingInstance is not None):
                inst=self.containingInstance
                il={ "state" : str(inst.state),
                     "fn_name" : str(inst.name) }
                if listIO:
                    inps=inst.getInputNames()
                    outs=inst.getOutputNames()
                    subnet_inps=inst.getSubnetInputNames()
                    subnet_outs=inst.getSubnetOutputNames()
                    il = { "state" : str(inst.state),
                           "fn_name" : str(inst.name),
                           "inputs": inps,
                           "outputs" : outs,
                           "subnet_inputs" : subnet_inps,
                           "subnet_outputs" : subnet_outs  }
                ret[self.name] = il
        return ret

    def getContainingNetwork(self, instancePath):
        """Get the network and instanceName that contains the item in a
           path specifier according to
           [instance]:[instance]:...

           returns a tuple (network, instanceName)
           """
        sp=instancePath.split(':')
        ( net, instanceName ) = self._getContainingNet(sp)
        return (net, instanceName)

    def getTaskQueue(self):
        """Get the task queue associated with this network."""
        return self.taskQueue

    def getInstances(self):

        with self.lock:
            return self.instances

    def getInstance(self, name):

        log.debug('In dataNetwork.getInstance. Instance: %s' % self.instances.get(name))
        with self.lock:
            i = self.instances.get(name)
            log.debug('In network.getInstance. %s' % i)
            return i

    def activateAll(self):

        with self.lock:
            for i in self.instances.values():
                i.unfreeze()

    def deactivateAll(self):

        with self.lock:
            for i in self.instances.values():
                i.freeze()
