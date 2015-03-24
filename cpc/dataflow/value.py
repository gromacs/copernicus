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
import ast
import copy
from notify.all import Variable
from cpc.util import CpcError
from types import IntType, FloatType, ListType, DictType, StringType

log=logging.getLogger(__name__)

class ValueError(CpcError):
    """Base Value exception class."""
    pass

class Value(Variable):
    """ Value is a container for a generic value. It can have a name and its ownerFunction, if any,
        is the function or function prototype that it is part of. It can also have a description
        documenting what it contains. The actual value contents is stored in self.value, inheriting
        the functionality of Variable from the notify library. Values can be connected to each other
        to propagate data. """

    __slots__ = ['typeString', 'name', 'ownerFunction', 'container', 'hasChanged', 'optional',
                 'description', 'listeningTo']

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):
        """
           :param initialValue  : A value of any kind that the value container
                                  should contain from the start.
           :param name          : The name of the variable.
           :param ownerFunction : The ownerFunction of the variable.
           :type ownerFunction  : Function/FunctionPrototype.
           :param container     : A list or dict type container that contains
                                  this value.
           :type container      : ListValue
           :param description   : A description of the data and what it is used for.
           :type description    : str.
           :raises              : AssertionError.
        """

        from function import Function, FunctionPrototype

        assert ownerFunction == None or isinstance(ownerFunction,
                                                   (Function, FunctionPrototype))
        assert container == None or isinstance(container, (ListValue, DictValue))

        self.typeString = 'value'
        Variable.__init__(self, initialValue)

        self.name = name
        self.ownerFunction = ownerFunction
        self.container = container
        self.hasChanged = False # If the value changes this will be set to True.
        self.optional = optional
        self.description = description
        self.listeningTo = set()

    def _executeOwnerFunction(self):
        """ Execute the owner function of a variable if the variable is part
            of the function's input. Otherwise iterate through the chain
            of containers until an owner function is found to execute. """

        # If the value is input to a function execute the function code (if all
        # input is set).
        if self.ownerFunction:
            if self in self.ownerFunction.inputValues or \
                self in self.ownerFunction.subnetInputValues:
                #log.debug('Will execute owner function: %s' % self.ownerFunction.name)
                self.ownerFunction.execute()

        else:
            container = self.container
            while container:
                #log.debug('Modifying changed status of container: %s' % container.name)
                container.hasChanged = True
                if container.ownerFunction:
                    if container in container.ownerFunction.inputValues or \
                        container in container.ownerFunction.subnetInputValues:
                        container.ownerFunction.execute()
                    break
                container = container.container
                #log.debug('Container = %s, self.container = %s' % (container, self.container))

    def _verifyCanConnect(self, toValue):
        """ Verify that an attempted connection is valid. It is not OK to connect a value that
            is belongs to a function, but is not one of its output values. It is also not OK
            to connect a subnet output value to a value that is not input or subnet input or to
            a value belonging to a function that is not part of the function subnet.

           :raises              : ValueError if a connection is not allowed.
        """


        if self.ownerFunction:
            if self not in self.ownerFunction.outputValues and \
               self not in self.ownerFunction.subnetOutputValues:
                raise ValueError("Cannot add a connection from a value that is not an output value.")
            if self in self.ownerFunction.subnetOutputValues:
                if toValue.ownerFunction not in self.ownerFunction.subnetFunctions:
                    raise ValueError("Cannot add a connection. Connected value is not part of the function subnet.")
                if toValue not in toValue.ownerFunction.inputValues and \
                   toValue not in toValue.ownerFunction.subnetInputValues:
                    raise ValueError("Cannot add a connection. Connected value is not part of the function subnet.")

    def is_allowed_value(self, value):
        """ Verify that the variable is of an allowed type. Overrides method of
            Variable.
            The implementation in the Value base class allows all values.

           :param value : The value that should be checked if it is allowed.
           :returns     : True is the value is allowed (always) or False if it
                          is not (never).
        """
        return True

    def set(self, value):
        """ Set the value. This is also called when using the assignment operator
            (=). is_allowed_value is called to verify that the value is OK.

           :param value: The new value.
        """

        #log.debug('Setting value of %s from %s to %s' % (self.name, self.value, value))

        if self.value == value:
            return

        Variable.set(self, value)

        # If the value is changed update the hasChanged flag.
        self.hasChanged = True
        self._executeOwnerFunction()


    def addConnection(self, toValue):
        """ Add a connection from this value container to another value
            container. When this value is modified the other value will
            reflect that.

           :param toValue: The value that should be updated when this value
                           is updated.
        """

        self._verifyCanConnect(toValue)

        #log.debug('Adding connection from %s to %s.' % (self.name, toValue.name))

        #self.changed.connect_safe(toValue.setByConnection)
        self.changed.connect_safe(toValue.set)
        toValue.listeningTo.add(self)

        if self.value == toValue.value:
            return

        toValue.value = self.value

    def removeConnection(self, toValue):
        """ Remove all connections from this value to another.
            toValue will no longer reflect changes made to this value.

           :param toValue: The value to which all connections (from this value)
                           should be removed.
        """

        self.changed.disconnect_all(toValue, fromValue=self)
        toValue.listeningTo.remove(self)

    def setFromString(self, string):
        """ Set the value from a string.
           :param string; The string containing the new value.
        """

        self.set(string)

    def getTypeString(self):
        """ Return a string describing the format of the contents.
           :returns     : string.
        """

        return self.typeString

    def getLiteralContents(self):
        """ Get the contents of the variable returned as a string.
           :returns     : string.
        """

        if self.value is not None:
            return str(self.value)
        else:
            return "None"

    def getDescription(self):
        """ Get the description of the value returned as a string.
           :returns     : string.
        """

        return self.description

    def setDescription(self, desc):
        """ Set the description of the value.
           :param desc     : The new description.
           :type desc      : str.
        """

        self.description = desc

    def isUpdated(self):
        """ Check if the value has changed since its associated function
            was last executed.
           :returns     : True if it has changed. False if it has not.
        """

        return self.hasChanged

    def getBaseType(self):
        """Get the base type of this type."""
        ret=self
        while not isinstance(ret, basicTypeList):
            ret=ret.container
        return ret

    def getBaseTypeName(self):
        """Get the name of the base type of this type."""
        ret=self
        while not isinstance(ret, basicTypeList):
            ret=ret.container
        return ret.typeString

    def getSubValue(self, key):
        return self

    def getClosestSubValue(self):
        return self

    def jsonDescribe(self):
        """Get a description of a value in a JSON-serializable format."""
        return { 'name' : self.name,
                 'base-type' : self.getBaseTypeName()}

class FileValue(Value):
# FIXME: FileValue does not work yet.

    __slots__ = []

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'file'

    def is_allowed_value(self, value):

        # Allow both StringType and UnicodeType
        if value == None or isinstance(value, StringType):
            return True
        else:
            return False

class BoolValue(Value):

    __slots__ = []

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'bool'

    def is_allowed_value(self, value):

        if value == None or isinstance(value, bool):
            return True
        else:
            return False

    def setFromString(self, string):

        if string.lower() == 'true' or string == '1':
            self.value = True
        else:
            self.value = False

class IntValue(Value):

    __slots__ = []

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'int'

    def is_allowed_value(self, value):

        if value == None or isinstance(value, IntType):
            return True
        else:
            return False

    def setFromString(self, string):

        self.value = int(string)

class FloatValue(Value):

    __slots__ = []

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'float'

    def is_allowed_value(self, value):

        if value == None or isinstance(value, (IntType, FloatType)):
            return True
        else:
            return False

    def setFromString(self, string):

        self.value = float(string)

class StringValue(Value):

    __slots__ = []

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'string'

    def is_allowed_value(self, value):

        # Allow both StringType and UnicodeType
        if value == None or isinstance(value, StringType):
            return True
        else:
            return False

class ListValue(Value):

    __slots__ = ['dataType']

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description='', dataType=None):

        self.dataType = dataType

        if initialValue:
            assert isinstance(initialValue, ListType)
            iv = list(initialValue)
            if dataType:
                t = dataType
            else:
                t = Value

            for i, v in enumerate(iv):
                if not isinstance(v, t):
                    iv[i] = t(v)

        else:
            iv = []

        Value.__init__(self, iv, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'list'

        for v in self.value:
            v.container = self

    def is_allowed_value(self, value):
        """ Verify that the variable is of an allowed type. Overrides method of
            Value.

           :param value : The value that should be checked if it is allowed.
           :returns     : True is the value is allowed or False if it
                          is not.
        """

        if value == None:
            return True

        if isinstance(value, ListType):
            if self.dataType:
                t = self.dataType
            else:
                t = Value
            for v in value:
                if not isinstance(v, t):
                    return False
            return True
        else:
            return False

    def set(self, value):
        """ Set the value. This is also called when using the assignment operator
            (=). is_allowed_value is called to verify that the value is OK.

           :param value: The new value.
        """

        newList = []

        #log.debug('In ListValue.set().')

        t = self.dataType or Value

        # Go through the list of values and create Value objects
        # if they are not already.
        for i, v in enumerate(value):
            if len(self.value) > i:
                newV = self.value[i]
            else:
                newV = t(None, container=self)
            if isinstance(v, Value):
                newV.name = v.name
                newV.value = v.value
            else:
                newV.value = v
            newList.append(newV)

        Variable.set(self, newList)

        self.hasChanged = True
        self._executeOwnerFunction()

    def addConnection(self, toValue):
        """ Add a connection from this value container to another value
            container. When this value is modified the other value will
            reflect that.

           :param toValue: The value that should be updated when this value
                           is updated.
        """

        #log.debug('In ListValue.addConnection.')

        self._verifyCanConnect(toValue)
        self.changed.connect_safe(toValue)
        toValue.listeningTo.add(self)

        if self.value:
            for i in len(self.value):
                self.value[i].addConnection(toValue.value[i])
        else:
            self.hasChanged = True
            self._executeOwnerFunction()

    def removeConnection(self, toValue):
        """ Remove all connections from this value to another.
            toValue will no longer reflect changes made to this value.

           :param toValue: The value to which all connections (from this value)
                           should be removed.
        """


        self.changed.disconnect_all(toValue, fromValue=self)
        toValue.listeningTo.remove(self)

        for i in min(len(self.value), len(toValue.value)):
            self.value[i].removeConnection(toValue.value[i])

    def setFromString(self, string):
        """ Set the value from a string.
           :param string; The string containing the new value.
        """

        self.set(ast.literal_eval(string))

    def getLiteralContents(self):
        """ Get the contents of the variable returned as a string.
           :returns     : string.
        """

        ret = []
        for i in self.value:
            ret.append(i.getLiteralContents())

        return ret

    def getCreateSubValue(self, index):
        """ Return the value of the specified index in the list. If there is no
            value of that index create it (and all values in between).

           :param index    : The index of the value to return.
           :type index     : Int.
           :returns        : The value of the specified index in the list.
        """

        if self.value == None:
            return None
        nValues = len(self.value)
        while nValues <= index:
            newValue = self.dataType(None)
            newValue.container = self
            self.append(newValue)
            nValues += 1
        #log.debug('getCreateSubValue: %s, ownerFunction: %s, container: %s' % (self.value[index],
        #self.value[index].ownerFunction, self.value[index].container))
        return self.value[index]

    def getClosestSubValue(self, index):
        """ Return the value of the specified index in the list. If there is no
            value of that index return self.

           :param index    : The index of the value to return.
           :type index     : Int.
           :returns        : The value of the specified index in the list or self.
        """

        if not self.value:
            return self
        if index == '+':
            index = len(self.value)
        if index < len(self.value):
            return self.value[index]
        return self

    def getSubValue(self, index):
        """ Return the value of the specified index in the list. If there is no
            value of that index return None.

           :param index    : The index of the value to return.
           :type index     : Int.
           :returns        : The value of the specified index in the list or None.
        """

        if not self.value:
            return None
        if index < len(self.value):
            return self.value[index]
        return None

    def setSubValue(self, index, value):

        self.setIndex(value, index)

    def append(self, value):
        """ Add a value to the end of the list. """

        nValues = len(self.value)
        self.setIndex(value, nValues)

    def setIndex(self, value, index):
        """ Set the value of the specified index to the supplied value argument. """

        nValues = len(self.value)
        if nValues > index:
            oldValue = self.value[index]
            oldValue.value = value
            value = oldValue

        else:
            if self.dataType:
                if isinstance(value, Value):
                    assert isinstance(value, self.dataType)
                else:
                    value = self.dataType(value)
            else:
                assert isinstance(value, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."

        value.container = self
        for conn in self.listeningTo:
            if isinstance(conn, ListValue) and len(conn.value < index):
                conn.value[index].addConnection(value)

        if self.changed.has_handlers():
            # In order to emit a signal self.value must be specifically set - it is not enough to just manipulate the list.
            self.value = self.value[:index] + [value] + self.value[index + 1:]
        else:
            if nValues > index:
                self.value[index] = value
            else:
                self.value.append(value)

class DictValue(Value):

    __slots__ = ['dataType']

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description='', dataType=None):

        self.dataType = dataType

        if initialValue:
            if isinstance(initialValue, DictType):
                iv = dict(initialValue)
            elif isinstance(initialValue, ListType):
                iv = dict()
                for i in initialValue:
                    if not isinstance(i, Value):
                        raise ValueError('When setting up a DictValue object from a list the contents must be of type Value.')
                    if self.dataType and not isinstance(i, self.dataType):
                        raise ValueError('When setting up a DictValue object from a list the contents must match the data type of the DictValue.')
                    iv[i.name] = i
            else:
                raise ValueError('initialValue of a DictValue object must be a dict or list.')
        else:
            iv = dict()

        Value.__init__(self, iv, name, ownerFunction, container,
                       optional, description)
        self.typeString = 'dict'

        for v in self.value.itervalues():
            v.container = self

    def is_allowed_value(self, value):
        """ Verify that the variable is of an allowed type. Overrides method of
            Value.

           :param value : The value that should be checked if it is allowed.
           :returns     : True is the value is allowed or False if it
                          is not.
        """


        if value == None:
            return True

        if isinstance(value, DictType):
            if self.dataType:
                t = self.dataType
            else:
                t = Value
            for v in value.itervalues():
                if not isinstance(v, t):
                    return False
            return True
        else:
            return False

    def set(self, value):
        """ Set the value. This is also called when using the assignment operator
            (=). is_allowed_value is called to verify that the value is OK.

           :param value: The new value.
        """

        newDict = dict()

        #log.debug('In DictValue.set().')

        t = self.dataType or Value

        for k, v in value.iteritems():
            newV = self.value.get(k, t(None, container=self))
            if isinstance(v, Value):
                newV.name = v.name
                newV.value = v.value
            else:
                newV.value = v

            newDict[k] = newV

        Variable.set(self, newDict)

        self.hasChanged = True
        self._executeOwnerFunction()

    def addConnection(self, toValue):
        """ Add a connection from this value container to another value
            container. When this value is modified the other value will
            reflect that.

           :param toValue: The value that should be updated when this value
                           is updated.
        """

        #log.debug('In DictValue.addConnection.')

        self._verifyCanConnect(toValue)
        self.changed.connect_safe(toValue)
        toValue.listeningTo.add(self)

        for k in self.value.iterkeys():
            #log.debug('Adding connection from key: %s' % k)
            self.value[k].addConnection(toValue.value[k])

        self.hasChanged = True
        self._executeOwnerFunction()

    def removeConnection(self, toValue):
        """ Remove all connections from this value to another.
            toValue will no longer reflect changes made to this value.

           :param toValue: The value to which all connections (from this value)
                           should be removed.
        """

        self.changed.disconnect_all(toValue, fromValue=self)
        toValue.listeningTo.remove(self)

        for k in self.value.iterkeys():
            to = toValue.value.get(k)
            if to:
                self.value[k].removeConnection(to)

    def update(self, *args, **kwargs):
        """ Add items to the dictionary. The argument can be a combination of a dictionary
            and a set of keyword - value pairs. E.g.
              self.update({'a': 1, 'b': 2, 'c': 3})
              self.update({'a': 1}, b=2, c=3)
              self.update(a=1, b=2, c=3)
        """

        # If the dictionary has a specified data type all values of the new
        # dictionary must be compatible with that.
        if self.dataType:
            if args:
                d = args[0]
            else:
                d = {}
            if isinstance(d, DictType):
                for k,v in d.iteritems():
                    if isinstance(v, Value):
                        assert isinstance(v, self.dataType)
                    else:
                        v = self.dataType(v)
                        d[k] = v
                    v.container = self
                    for conn in self.listeningTo:
                        if isinstance(conn, DictValue):
                            fromValue = conn.value.get(k)
                            if fromValue:
                                fromValue.addConnection(v)
            else:
                d = {}

            for k,v in kwargs.iteritems():
                if isinstance(v, Value):
                    assert isinstance(v, self.dataType)
                else:
                    v = self.dataType(v)
                    for conn in self.listeningTo:
                        if isinstance(conn, DictValue):
                            fromValue = conn.value.get(k)
                            if fromValue:
                                fromValue.addConnection(value)
                    kwargs[k] = v
                v.container = self
                for conn in self.listeningTo:
                    if isinstance(conn, DictValue):
                        fromValue = conn.value.get(k)
                        if fromValue:
                            fromValue.addConnection(v)

        # If the values do not have to be of a specific type still check that
        # the types of the new dictionary match the types in the old dictionary
        # of entries with the same key.
        else:
            if args:
                d = args[0]
            else:
                d = {}
            if isinstance(d, DictType):
                for k,v in d.iteritems():
                    oldValue = self.value.get(k)
                    oldValueType = type(oldValue)
                    if not isinstance(v, Value):
                        v = oldValueType(v)
                    if oldValue:
                        assert isinstance(v, oldValueType), "When updating an existing item in a dictionary it may not change type."
                    else:
                        assert isinstance(v, Value), "If a dictionary does not have a data type specified values can only be appended if they are a Value object."
                    v.container = self
                    for conn in self.listeningTo:
                        if isinstance(conn, DictValue):
                            fromValue = conn.value.get(k)
                            if fromValue:
                                fromValue.addConnection(v)
            else:
                d = {}

            for k, v in kwargs.iteritems():
                oldValue = self.value.get(k)
                oldValueType = type(oldValue)
                if not isinstance(v, Value):
                    v = oldValueType(v)
                if oldValue:
                    assert isinstance(v, oldValueType), "When updating an existing item in a dictionary it may not change type."
                else:
                    assert isinstance(v, Value), "If a dictionary does not have a data type specified values can only be appended if they are a Value object."
                v.container = self
                for conn in self.listeningTo:
                    if isinstance(conn, DictValue):
                        fromValue = conn.value.get(k)
                        if fromValue:
                            fromValue.addConnection(v)

        if self.changed.has_handlers():
            # In order to emit a signal self.value must be specifically set - it is not enough to just manipulate the dictionary.
            newDict = dict(self.value.items() + d.items() + kwargs.items())
            self.value = newDict
        else:
            # If there are no listeners it is quicker to just update the existing dictionary.
            self.value.update(d.items() + kwards.items())


    def setFromString(self, string):

        self.set(ast.literal_eval(string))

    def getLiteralContents(self):

        ret = dict()
        for name, i in self.value.iteritems():
            ret[name] = i.getLiteralContents()

        return ret

    def getCreateSubValue(self, key):

        if self.value == None:
            return None
        value = self.value.get(key)
        if value is None:
            value = self.dataType(None, name = key)
            value.container = self
            self.update({key: value})
        return value

    def getClosestSubValue(self, key):
        """ Return the value of the specified key in the dictionary. If there is no
            value with that key return self.

           :param key    : The key of the value to return.
           :returns      : The value of the specified key in the dictionary or self.
        """


        if not self.value:
            return self
        return self.value.get(key, self)

    def getSubValue(self, key):
        """ Return the value of the specified key in the dictionary. If there is no
            value with that key return None.

           :param key      : The key of the value to return.
           :returns        : The value of the specified key in the dictionary or None.
        """

        if not self.value:
            return None
        if key == None or key == []:
            return self
        return self.value.get(key)

    def setSubValue(self, key, value):

        #log.debug('In dict.setSubValue(), key: %s, value: %s' % (key, value))

        valueContainer = self.value.get(key)
        if not valueContainer:
            self.update({key: value})

        else:
            if isinstance(value, Value):
                valueContainer.value = value.value
            else:
                valueContainer.value = value


basicTypeList = (BoolValue, IntValue, FloatValue, StringValue, ListValue, DictValue)
