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
                 'description']

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

        # If the value is changed update the hasChanged flag.
        if self.value == value:
            return

        self.hasChanged = True

        Variable.set(self, value)

        # If the value is input to a function execute the function code (if all
        # input is set).
        if self.ownerFunction and (self in self.ownerFunction.inputValues or \
            self in self.ownerFunction.subnetInputValues):
            self.ownerFunction.functionPrototype.isFinished = False
            self.ownerFunction.execute()

        if self.container:
            self.container.hasChanged = True
            if self.container.ownerFunction and (self.container in self.container.ownerFunction.inputValues or \
                                                 self.container in self.container.ownerFunction.subnetInputValues):
                self.container.ownerFunction.functionPrototype.isFinished = False
                self.container.ownerFunction.execute()

    def setByConnection(self, value):
        """ Update self.value when it is connected to a value that has been
            changed.

           :param value     : The new value (that had been modified before
                              causing this function to be called).
        """

        log.debug('In setByConnection. Setting %s (%s) to %s.' % (self, self.value, value))
        log.debug('self.ownerFunction: %s' % self.ownerFunction)

        if self.value == value:
            return

        self.hasChanged = True

        self.value = value

        if self.ownerFunction:
            if self in self.ownerFunction.inputValues or self in \
                self.ownerFunction.subnetInputValues:
                self.ownerFunction.functionPrototype.isFinished = False
                self.ownerFunction.execute()

    def addConnection(self, toValue):
        """ Add a connection from this value container to another value
            container. When this value is modified the other value will
            reflect that.

           :param toValue: The value that should be updated when this value
                           is updated.
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

        self.changed.connect_safe(toValue.setByConnection)

        if self.value == toValue.value:
            return

        #log.debug('value: %s, toValue: %s' % (self.value, toValue.value))
        #if isinstance(self, DictValue) and isinstance(toValue, DictValue):
            ##toValue.value = {}
            #for k, v in self.value.iteritems():
                #toValue.value[k] = copy.deepcopy(v)
        #elif isinstance(self, ListValue) and isinstance(toValue, ListValue):
            #toValue.value = []
            #for v in self.value:
                #toValue.append(copy.deepcopy(v))
        #else:
            #toValue.value = copy.deepcopy(self.value)
        log.debug('Making deepcopy of %s to overwrite %s' % (self.value, toValue.value))
        toValue.value = copy.deepcopy(self.value)
        toValue.hasChanged = True
        if toValue.ownerFunction:
            if toValue in toValue.ownerFunction.inputValues or toValue in \
                toValue.ownerFunction.subnetInputValues:
                toValue.ownerFunction.functionPrototype.isFinished = False
                toValue.ownerFunction.execute()

    def removeConnection(self, toValue):
        """ Remove all connections from this value to another.
            toValue will no longer reflect changes made to this value.

           :param toValue: The value to which all connections (from this value)
                           should be removed.
        """

        self.changed.disconnect_all(toValue, fromValue=self)

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

        return self.description

    def setDescription(self, desc):

        self.description = desc

    def isUpdated(self):

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

    def set(self, value):

        iv = list(value)

        t = self.dataType or Value

        for i, v in enumerate(iv):
            if not isinstance(v, t):
                iv[i] = t(v)

        Value.set(self, iv)


    def is_allowed_value(self, value):

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

    def setFromString(self, string):

        self.set(ast.literal_eval(string))

    def getLiteralContents(self):

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
        log.debug('ListValue getCreateSubValue. index: %s' % index)
        nValues = len(self.value)
        while nValues <= index:
            newValue = self.dataType(None, container=self)
            log.debug('newValue: %s' % newValue)
            self.append(newValue)
            nValues += 1
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

    def append(self, value):
        """ Add a value to the end of the list. """

        nValues = len(self.value)
        self.setIndex(value, nValues)

    def setIndex(self, value, index):
        """ Set the value of the specified index to the supplied value argument. """

        if self.dataType:
            if isinstance(value, Value):
                assert isinstance(value, self.dataType)
            else:
                value = self.dataType(value)
        else:
            assert isinstance(value, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."

        value.container = self

        # In order to emit a signal self.value must be specifically set - it is not enough to just manipulate the list.
        self.value = self.value[:index] + [value] + self.value[index + 1:]

        # Update the hasChanged flag
        self.hasChanged = True
        # If the value is input to a function execute the function code (if all input is set).
        if self.ownerFunction and (self in self.ownerFunction.inputValues or \
                                self in self.ownerFunction.subnetInputValues):
            self.ownerFunction.functionPrototype.isFinished = False
            self.ownerFunction.execute()

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

    def set(self, value):

        iv = dict(value)
        if self.dataType:
            t = self.dataType
        else:
            t = Value
        for k, v in iv.iteritems():
            if not isinstance(v, t):
                iv[k] = t(v)

        Value.set(self, iv)


    def is_allowed_value(self, value):

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

    def update(self, *args, **kwargs):
        """ Add items to the dictionary. The argument can be a combination of a dictionary
            and a set of keyword - value pairs. E.g.
              self.update({'a': 1, 'b': 2, 'c': 3})
              self.update({'a': 1}, b=2, c=3)
              self.update(a=1, b=2, c=3)
        """

        log.debug('DictValue update. self.dataType: %s' % self.dataType)

        if self.dataType:
            if args:
                d = args[0]
            else:
                d = {}
            if isinstance(d, DictType):
                for k,v in d.iteritems():
                    if isinstance(v, Value):
                        assert isinstance(v, self.dataType)
                        v.container = self
                    else:
                        newValue = self.dataType(v, container=self)
                        d[k] = newValue
            else:
                d = {}

            for k,v in kwargs.iteritems():
                if isinstance(v, Value):
                    assert isinstance(v, self.dataType)
                    v.container = self
                else:
                    newValue = self.dataType(v, container=self)
                    kwargs[k] = newValue

        else:
            if args:
                d = args[0]
            else:
                d = {}
            if isinstance(d, DictType):
                for k,v in d.iteritems():
                    oldValue = self.value.get(k)
                    if oldValue:
                        assert isinstance(v, type(oldValue)), "When updating an existing item in a dictionary it may not change type."
                    else:
                        assert isinstance(v, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."
                    v.container = self
            else:
                d = {}

            for k,v in kwargs.iteritems():
                oldValue = self.value.get(k)
                if oldValue:
                    assert isinstance(v, type(oldValue)), "When updating an existing item in a dictionary it may not change type."
                else:
                    assert isinstance(v, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."
                v.container = self


        # In order to emit a signal self.value must be specifically set - it is not enough to just manipulate the dictionary.
        newDict = dict(self.value.items() + d.items() + kwargs.items())
        self.value = newDict

        # Update the hasChanged flag
        self.hasChanged = True
        ## If the value is input to a function execute the function code (if all input is set).
        if self.ownerFunction and (self in self.ownerFunction.inputValues or \
                                   self in self.ownerFunction.subnetInputValues):
            self.ownerFunction.functionPrototype.isFinished = False
            self.ownerFunction.execute()

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
        log.debug('DictValue getCreateSubValue. value: %s' % value)
        if value is None:
            value = self.dataType(None, name = key, container=self)
            self.update(key = value)
        return value

    def getClosestSubValue(self, key):

        if not self.value:
            return self
        return self.value.get(key, self)

    def getSubValue(self, key):

        if not self.value:
            return None
        if key == None or key == []:
            return self
        log.debug('Getting subvalue: %s. Got: %s.' % (key, self.value.get(key)))
        return self.value.get(key)

    def setSubValue(self, key, value):

        valueContainer = self.value.get(key)
        if not valueContainer:
            if self.dataType:
                if isinstance(value, Value):
                    assert isinstance(value, self.dataType)
                else:
                    value = self.dataType(value, container=self)
            else:
                assert isinstance(value, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."

            self.value[key] = value

        else:
            if isinstance(value, Value):
                valueContainer.value = value.value
            else:
                valueContainer.value = value

basicTypeList = (BoolValue, IntValue, FloatValue, StringValue, ListValue, DictValue)
