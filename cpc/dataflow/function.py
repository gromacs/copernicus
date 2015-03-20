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

import logging
import subprocess
import threading
import copy
import keywords
import os

from task import Task
from msg import ActiveInstanceMsg
from cpc.util import CpcError
from value import ValueError

log=logging.getLogger(__name__)

class FunctionError(CpcError):
    """Base class for function exceptions"""
    pass

#def executeSystemCommand(cmd, inp=None):
    #""" Executes a system command and returns the output.

       #:param cmd : The command to execute. This is supplied as a list
                    #containing all arguments.
       #:type cmd  : list.
       #:inp       : Input to be directed to the command
                    #(not command-line arguments).
       #:type inp  : str.
       #:returns   : The output of the command.
    #"""

    #if not inp:
        #output = ''.join(subprocess.check_output(cmd, stderr=subprocess.STDOUT))
    #else:
        #p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             #stdout=subprocess.PIPE,
                             #stderr=subprocess.STDOUT)

        #output = ''.join(p.communicate(input=inp)[0])

    #return output

class FunctionBase(object):
    """ This class contains basic data and data management functions.
        It is inherited by Function and FunctionPrototype."""

    __slots__ = ['name', 'description', 'inputValues', 'outputValues',
                 'subnetInputValues', 'subnetOutputValues']

    def __init__(self, name):

        self.name = name
        self.inputValues = []
        self.outputValues = []
        self.subnetInputValues = []
        self.subnetOutputValues = []
        self.description = None

    def getName(self):
        """ Get the name of the function.

           :returns    : The name.
        """

        return self.name

    def getInputValueContainer(self, name):
        """ Get the (first) input Value object named as specified.

           :param name : The name of the value to retrieve.
           :type name   : str.
           :returns    : The found Value object or None
        """

        for v in self.inputValues:
            if v.name == name:
                return v

    def getSubnetInputValueContainer(self, name):
        """ Get the (first) subnet input Value object named as specified.

           :param name : The name of the value to retrieve.
           :type name   : str.
           :returns    : The found Value object or None
        """

        for v in self.subnetInputValues:
            if v.name == name:
                return v

    def getAllInputNames(self):
        """ Get the names of all inputs and subnet inputs.
           :returns    : A list of the names of all inputs.
        """

        return [v.name for v in self.inputValues + self.subnetInputValues]

    def getAllOutputNames(self):
        """ Get the names of all outputs and subnet outputs.
           :returns    : A list of the names of all outputs.
        """

        return [v.name for v in self.outputValues + self.subnetOutputValues]

    def getInputNames(self):
        """ Get the names of inputs.
           :returns    : A list of the names of inputs.
        """

        return [v.name for v in self.inputValues]

    def getOutputNames(self):
        """ Get the names of outputs.
           :returns    : A list of the names of outputs.
        """

        return [v.name for v in self.outputValues]

    def getSubnetInputNames(self):
        """ Get the names of subnet inputs.
           :returns    : A list of the names of subnet inputs.
        """

        return [v.name for v in self.subnetInputValues]

    def getSubnetOutputNames(self):
        """ Get the names of subnet outputs.
           :returns    : A list of the names of subnet outputs.
        """

        return [v.name for v in self.subnetOutputValues]

    def getOutputValueContainer(self, name):
        """ Get the (first) output Value object named as specified.

           :param name : The name of the value to retrieve.
           :type name  : str.
           :returns    : The found Value object or None
        """

        for v in self.outputValues:
            if v.name == name:
                return v

    def getSubnetOutputValueContainer(self, name):
        """ Get the (first) subnet output Value object named as specified.

           :param name : The name of the value to retrieve.
           :type name   : str.
           :returns    : The found Value object or None
        """

        for v in self.subnetOutputValues:
            if v.name == name:
                return v

    def setInputValueContents(self, name, value):
        """ Set the contents (Value.value) of the (first) input Value object
            named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :param value : The new value.
           :returns     : The found Value object or None
        """

        v = self.getInputValueContainer(name)

        if v:
            if v.value != value:
                v.hasChanged = True

            v.value = value
        else:
            raise ValueError('Value %s does not exist' % name)

    def setSubnetInputValueContents(self, name, value):
        """ Set the contents (Value.value) of the (first) subnet input
            Value object named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :param value : The new value.
           :returns     : The found Value object or None
        """

        v = self.getSubnetInputValueContainer(name)

        if v:
            if v.value != value:
                v.hasChanged = True

            v.value = value
        else:
            raise ValueError('Value %s does not exist' % name)

    def setOutputValueContents(self, name, value):
        """ Set the contents (Value.value) of the (first) output Value object
            named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :param value : The new value.
           :returns     : The found Value object or None
        """

        v = self.getOutputValueContainer(name)

        if v:
            if v.value != value:
                v.hasChanged = True

            v.value = value
        else:
            raise ValueError('Value %s does not exist' % name)

    def setSubnetOutputValueContents(self, name, value):
        """ Set the contents (Value.value) of the (first) subnet output
            Value object named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :param value : The new value.
           :returns     : The found Value object or None
        """

        v = self.getSubnetOutputValueContainer(name)

        if v:
            if v.value != value:
                v.hasChanged = True

            v.value = value
        else:
            raise ValueError('Value %s does not exist' % name)

    def getInputValueContents(self, name):
        """ Get the contents (Value.value) of the (first) input Value object
            named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :returns     : The value of the specified input value object.
        """

        v = self.getInputValueContainer(name)

        if v:
            return v.value
        else:
            raise ValueError('Value %s does not exist' % name)

    def getSubnetInputValueContents(self, name):
        """ Get the contents (Value.value) of the (first) subnet input Value
            object named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :returns     : The value of the specified input value object.
        """

        v = self.getSubnetInputValueContainer(name)

        if v:
            return v.value
        else:
            raise ValueError('Value %s does not exist' % name)

    def getOutputValueContents(self, name):
        """ Get the contents (Value.value) of the (first) output Value object
            named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :returns     : The value of the specified input value object.
        """

        v = self.getOutputValueContainer(name)

        if v:
            return v.value
        else:
            raise ValueError('Value %s does not exist' % name)

    def getSubnetOutputValueContents(self, name):
        """ Get the contents (Value.value) of the (first) subnet output Value
            object named as specified.

           :param name  : The name of the value to modify.
           :type name   : str.
           :returns     : The value of the specified input value object.
        """

        v = self.getSubnetOutputValueContainer(name)

        if v:
            return v.value
        else:
            raise ValueError('Value %s does not exist' % name)

    def getDescription(self):

        return self.description



class FunctionPrototype(FunctionBase):
    """ This class is inherited to describe how a function works and what input
        and output values it has. The actual function instances are of class
        Function.
    """

    __slots__ = ['useOutputDir', 'usePersistentDir', 'hasLog']

    def __init__(self, name, useOutputDir = False, usePersistentDir = False, hasLog = False):

        FunctionBase.__init__(self, name)
        self.useOutputDir = useOutputDir
        self.usePersistentDir = usePersistentDir
        self.hasLog = hasLog

    def execute(self, function = None):
        """ This function should be overloaded to contain the code that should
            be executed by a function.
        """

        return

    def executeFinished(self, function = None):
        """ This function should be overloaded to contain the code that should
            be executed when a command has been run - it can manage and/or analyze
            the outputs.
        """

        return

class Function(FunctionBase):
    """ This is an instance of a function, with its own input and output
        data.
    """

    __slots__ = ['functionPrototype', 'dataNetwork', 'project', 'frozen', 'subnetFunctions',
                 'inputListValue', 'outputListValue', 'subnetInputListValue', 'subnetOutputListValue',
                 'inputLock', 'outputLock', 'lock', 'message', 'tasks', 'state', 'isFinished',
                 'commandsToWorker', 'baseDir', 'outputDirNr', 'runLock', 'persistentDir', 'runSeqNr',
                 'cputime', 'subnet']

    def __init__(self, functionPrototype, name=None, dataNetwork=None, persistentDir=None):

        assert functionPrototype, "A function must have a function prototype."
        assert isinstance(functionPrototype, FunctionPrototype), "The function prototype of the function must be of class FunctionPrototype."

        FunctionBase.__init__(self, name)

        from value import DictValue

        self.functionPrototype = functionPrototype
        self.dataNetwork = dataNetwork
        if dataNetwork:
            self.project = dataNetwork.project
        else:
            self.project = None

        self.frozen = False
        self.subnetFunctions = dict()
        self.inputValues = copy.deepcopy(functionPrototype.inputValues)
        self.outputValues = copy.deepcopy(functionPrototype.outputValues)
        self.subnetInputValues = copy.deepcopy(functionPrototype.subnetInputValues)
        self.subnetOutputValues = copy.deepcopy(functionPrototype.subnetOutputValues)
        self.inputListValue = DictValue(self.inputValues, keywords.In, self)
        self.outputListValue = DictValue(self.outputValues, keywords.Out, self)
        self.subnetInputListValue = DictValue(self.subnetInputValues, keywords.SubIn, self)
        self.subnetOutputListValue = DictValue(self.subnetOutputValues, keywords.SubOut, self)

        self.inputLock = threading.RLock()
        self.outputLock = threading.Lock()
        self.lock = threading.Lock()
        self.message = ActiveInstanceMsg(self)
        self.tasks = []
        self.state = 'held'
        self.isFinished = False
        self.commandsToWorker = []

        if self.project:
            self.baseDir = os.path.join(self.project.getBasedir(), self.name)
        else:
            self.baseDir = self.name

        self.outputDirNr = 0

        if functionPrototype.useOutputDir or functionPrototype.usePersistentDir or functionPrototype.hasLog:
            if not os.path.exists(self.baseDir):
                os.mkdir(self.baseDir)

        if functionPrototype.usePersistentDir:
            self.runLock = threading.Lock()
            if persistentDir:
                if self.project:
                    if not os.path.isabs(persistentDir):
                        self.persistentDir = os.path.join(self.baseDir, persistentDir)
                    else:
                        self.persistentDir = persistentDir
                else:
                    #FIXME: Use a better exception.
                    raise Exception("Cannot set persistent dir when there is no project available.")
            else:
                if self.project:
                    self.persistentDir = os.path.join(self.baseDir, '_pers')
                else:
                    #FIXME: Use a better exception.
                    raise Exception("Cannot set persistent dir when there is no project available.")
            os.mkdir(self.persistentDir)
        else:
            self.runLock = None
            self.persistentDir = None

        self.runSeqNr = 0

        # counts the number of CPU seconds that this instance has used
        # on workers. Locked with outputLock
        self.cputime=0.

        for v in self.inputValues + self.outputValues + self.subnetInputValues + \
            self.subnetOutputValues:
            v.ownerFunction = self
        if name:
            self.name = name

        if self.subnetInputValues or self.subnetOutputValues:
            from datanetwork import DataNetwork
            self.subnet = DataNetwork(self.project, self.getCanonicalName(), dataNetwork.taskQueue,
                                      self.baseDir, containingInstance=self)
        else:
            self.subnet = None

        log.debug('Creating function %s, in %s, %s' % (self.name, self.project, self.dataNetwork))

    #def _getSubVal(self, itemList, staging=False):
        #"""Helper function"""

        #subval=None
        #try:
            #if itemList[0]==keywords.In:
                #with self.inputLock:
                    #if staging:
                        #subval=self.stagedInputVal
                    #else:
                        #subval=self.inputVal
            #elif itemList[0]==keywords.Out:
                #with self.outputLock:
                    #subval=self.outputVal
            #elif itemList[0]==keywords.SubIn:
                #with self.inputLock:
                    #if staging:
                        #subval=self.stagedSubnetInputVal
                    #else:
                        #subval=self.subnetInputVal
            #elif itemList[0]==keywords.SubOut:
                #with self.outputLock:
                    #subval=self.subnetOutputVal
            #elif itemList[0]==keywords.Msg:
                #with self.outputLock:
                    #subval=self.msg
            #elif self.subnet is not None:
                #subval=self.subnet.tryGetActiveInstance(itemList[0])
        #except:
            #pass
        #return subval

    def _getSubVal(self, itemList, closestValue=False, createValue=False):
        """Helper function"""

        subval=None
        #try:
        log.debug('FUNCTION: itemList[0] = %s' % itemList[0])
        if itemList[0]==keywords.In:
            log.debug('FUNCTION: Get In')
            with self.inputLock:
                subval=self.inputListValue
        elif itemList[0]==keywords.Out:
            log.debug('FUNCTION: Get Out')
            with self.outputLock:
                subval=self.outputListValue
        elif itemList[0]==keywords.SubIn:
            with self.inputLock:
                subval=self.subnetInputListValue
        elif itemList[0]==keywords.SubOut:
            with self.outputLock:
                subval=self.subnetOutputListValue
        elif itemList[0]==keywords.Msg:
            with self.outputLock:
                subval=self.message
        elif self.subnet is not None:
            log.debug('FUNCTION: Try get active instance.')
            subval=self.subnet.tryGetActiveInstance(itemList[0])
        #except:
            #pass
        #i = 1
        #while subval and len(itemList) > i:
            #log.debug('FUNCTION: SUBVAL: %s. GETTING %s. len(itemList): %s, i: %s' % (subval, itemList[i], itemList, i))
            #if createValue:
                #subval = subval.getCreateSubValue(itemList[i])
            #elif closestValue:
                #subval = subval.getClosestSubValue(itemList[i])
            #else:
                #subval = subval.getSubValue(itemList[i:])
            #i += 1

        if subval and len(itemList) > 1:
            from value import DictValue, ListValue

            log.debug('FUNCTION: SUBVAL: %s. GETTING %s. itemList: %s' % (subval, itemList[1], itemList))

            i = 1
            while i < len(itemList) and isinstance(subval, (DictValue, ListValue)):
                if createValue:
                    func = subval.getCreateSubValue
                elif closestValue:
                    func = subval.getClosestSubValue
                else:
                    func = subval.getSubValue

                log.debug('func: %s, i: %s' % (func, i))

                subval = func(itemList[i])
                i += 1
            if subval and i < len(itemList):
                if createValue:
                    func = subval.getCreateSubValue
                elif closestValue:
                    func = subval.getClosestSubValue
                else:
                    func = subval.getSubValue

                subval = func(itemList[i:])

        log.debug('FUNCTION: _getSubVal returns %s' % subval)
        return subval

    def getSubValue(self, itemList):
        """Get a specific subvalue through a list of subitems, or return None
           if not found.
           itemList = the path of the value to return"""
        log.debug('FUNCTION: GETTING SUBVAL %s' % itemList)
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList)
        return subval

    def getCreateSubValue(self, itemList):
        """Get or create a specific subvalue through a list of subitems, or
           return None if not found.
           itemList = the path of the value to return/create
           if createType == a type, a subitem will be created with the given
                            type
           if setCreateSourceTag = not None, the source tag will be set for
                                   any items that are created."""
        if len(itemList)==0:
            return self
        # staging is true because we know we want to be able to create a new
        # value.
        log.debug('GET OR CREATE %s' % itemList)
        subval=self._getSubVal(itemList, createValue=True)
        return(subval)

    def getClosestSubValue(self, itemList):
        """Get the closest relevant subvalue through a list of subitems,

           itemList = the path of the value to get the closest value for """
        log.debug('FUNCTION: itemlist %s' % itemList)
        if len(itemList)==0:
            return self
        subval=self._getSubVal(itemList, closestValue=True)
        return subval or self

    def getSubValueList(self):
        """Return a list of addressable subvalues."""
        ret=[ keywords.In, keywords.Out,
              keywords.SubIn, keywords.SubOut,
              keywords.Msg ]
        if self.subnet is not None:
            ailist=self.subnet.getActiveInstanceList(False, False)
            ret.extend( ailist.keys() )
        return ret

    def hasSubValue(self, itemList):
        """Check whether a particular subvalue exists"""
        if len(itemList) == 0:
            return True
        subval=self._getSubVal(itemList)
        if subval is not None:
            #return subval.hasSubValue(itemList[1:])
            return True
        return False

    def getLiteralContents(self):

        ret = dict()
        ret[keywords.In] = "inputs"
        ret[keywords.Out] = "outputs"
        ret[keywords.SubIn] = "subnet_inputs"
        ret[keywords.SubOut] = "subnet_outputs"
        ret[keywords.Msg] = "msg"
        return ret

    def getBaseDir(self):

        return self.baseDir

    def getPersistentDir(self):

        return self.persistentDir

    def getDescription(self):

        return self.description

    def getCanonicalName(self):
        """ Get the canonical name for this instance. """

        if self.dataNetwork and self.dataNetwork.containingInstance:
            name = '%s:' % self.dataNetwork.containingInstance.getCanonicalName()
        else:
            name = ''

        return name + self.name

    def getTasks(self):
        """ Get the task list """
        return self.tasks

    def removeTask(self, task):
        """ Remove a task from the list """
        with self.inputLock:
            self.tasks.remove(task)

    def addSubnetFunction(self, name, functionName):
        """ Add a function, called name, to the subnet of this function.
            The function will be of a type matching the functionName. """

        if not self.dataNetwork or not self.project:
            # FIXME: Change exception type.
            raise Exception('Cannot create a subnet of a function that is not part of a project')

        #name = self.getCanonicalName() + name
        name = name
        if self.subnet:
            subnet = self.subnet
        else:
            subnet = self.dataNetwork

        prototype = self.project.imports.getFunctionByFullName(functionName, self.project.topLevelImport)
        if not prototype:
            # FIXME: Change exception type. Or should this cause some other error instead of an exception?
            raise Exception('Function prototype %s not found' % functionName)
        log.debug('Adding subnet function: %s' % name)
        f = subnet.newInstance(prototype, name)

        self.subnetFunctions[name] = f
        log.debug(self.subnetFunctions)

        return f

    def getSubnetFunction(self, name):

        return self.subnetFunctions.get(name)

    def freeze(self):
        """ Make the function frozen. A frozen function does not execute
            when its input is changed.
        """

        self.frozen = True
        self.state = 'held'

    def unfreeze(self):
        """ Remove the frozen state. The function will execute if any of the
            inputs have changed during the period it was frozen.
        """

        self.frozen = False
        self.state = 'active'
        self.execute()

    def isFrozen(self):
        """ Return if the function is frozen or not.

           :returns : True if frozen, False if not frozen.
        """

        return self.frozen

    def markError(self, msg, reportAsNew=True):
        """Mark active instance as being in error state.

           If reportAsNew is True, the error will be reported as new, otherwise
           it is an existing error that is being re-read"""
        with self.lock:
            self.message.setError(msg)
            self.state='error'
            for task in self.tasks:
                task.deactivateCommands()
            if reportAsNew:
                log.error(u"Instance %s (fn %s): %s"%(self.getName(),
                                                      self.functionPrototype.getName(),
                                                      self.message.getError()))

    def setWarning(self, msg):
        """Set warning message."""
        with self.lock:
            self.message.setWarning(msg)


    def addCputime(self, cputime):
        """add used cpu time to this active instance."""
        with self.outputLock:
            self.cputime+=cputime

    def getCputime(self):
        with self.outputLock:
            return self.cputime

    def setCputime(self, cputime):
        """set used cpu time to this active instance."""
        with self.outputLock:
            self.cputime=cputime

    def getCumulativeCputime(self):
        """Get the total CPU time used by active instance and its
            internal network."""
        with self.outputLock:
            cputime = self.cputime
        cputime += self.subnet.getCumulativeCputime()
        return cputime

    def getStateStr(self):
        """Get the current state as a string."""
        with self.lock:
            ret = self.state
            #FIXME: Improve message check.
            if self.state == 'active' and self.message.hasWarning():
                ret='warning'
            if self.state == 'active' and self.message.hasError():
                ret='error'

        return ret

    def _inputHasChanged(self):
        """ Check if the input or subnet input of this function
            has changed since it was last executed.

            Assumes that self.inputLock is acquired.

           :returns : True if the input has changed, False if not.
        """

        for v in self.inputValues + self.subnetInputValues:
            if v.hasChanged:
                return True
        return False

    def _resetInputChange(self):
        """ Set the hasChanged status of all inputs and subnet inputs to False.

            Assumes that self.inputLock is acquired.

        """

        from value import ListValue, DictValue
        for v in self.inputValues + self.subnetInputValues:
            v.hasChanged = False
            if isinstance(v, ListValue):
                for entry in v.value:
                    entry.hasChanged = False
            elif isinstance(v, DictValue):
                for entry in v.value.values():
                    entry.hasChanged = False

    def addCommand(self, cmd):

        self.commandsToWorker.append(cmd)

    def execute(self):
        """ Execute the actual function executable (from the function definition
            itself). There are checks that the required input is available and
            also that the input has changed since last running the executable
            block.

            :returns : True if running the executable block, False if not
                       executing, i.e. due to missing input.
        """

        log.debug('FUNCTION EXECUTE')
        with self.inputLock and self.outputLock:
            if not self.frozen and self._inputHasChanged():
                from value import ListValue, DictValue
                # The try/except statement is mainly to avoid checking if
                # isinstance(v, Value) before checking if v.value == None.
                try:
                    for iv in self.inputValues:
                        if iv == None or (iv.optional == False and iv.value == None):
                            return False
                        if isinstance(iv, ListValue):
                            if len(iv.value) == 0:
                                return False
                            # Chances are the last value is set last, so traverse
                            # the list in reverse order.
                            for v in reversed(iv.value):
                                if v == None or v.value == None:
                                    return False
                        elif isinstance(iv, DictValue):
                            for v in iv.value.itervalues():
                                if v == None or v.value == None:
                                    return False
                except Exception:
                    return False

                #print 'Will execute', self.name
                if self.functionPrototype.useOutputDir:
                    log.debug("Creating output dir")
                    created=False
                    while not created:
                        outputDirName=os.path.join(self.baseDir,
                                                   "_run_%04d"%(self.outputDirNr))
                        fullOutputDirName=os.path.join(self.project.basedir,
                                                       outputDirName)
                        self.outputDirNr+=1
                        if not os.path.exists(fullOutputDirName):
                            os.mkdir(fullOutputDirName)
                            created=True
                else:
                    log.debug("Not creating output dir")
                    outputDirName=None


                self.state = 'active'
                if self.dataNetwork:
                    self.runSeqNr += 1
                    # FIXME: Does the task and taskQueue really work?
                    task = Task(self.dataNetwork.project, self, 0, self.runSeqNr)
                    log.debug('Putting task on queue: %s' % task)
                    self.dataNetwork.taskQueue.put(task)
                    self.tasks.append(task)
                else:
                    log.debug('Executing directly')
                    self.commandsToWorker = []
                    self.functionPrototype.execute(function = self)
                #self.functionPrototype.execute(function = self)
                self._resetInputChange()
                return True

            else:
                return False

    def executeFinished(self):

        self.functionPrototype.executeFinished(function = self)
        self.isFinished = True

        return