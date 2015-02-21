from notify.all import Variable
from types import IntType, FloatType, ListType, DictType, StringType
from function import Function, FunctionPrototype

class Value(Variable):
    """ Value is a container for a generic value. It can have a name and its ownerFunction, if any,
        is the function or function prototype that it is part of. It can also have a description
        documenting what it contains. The actual value contents is stored in self.value, inheriting
        the functionality of Variable from the notify library. Values can be connected to each other
        to propagate data. """

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
           :type                : ListValue
           :param description   : A description of the data and what it is used for.
           :type description    : str.
           :raises              : AssertionError.
        """

        assert ownerFunction == None or isinstance(ownerFunction,
                                                   (Function, FunctionPrototype))
        assert container == None or isinstance(container, (ListValue, DictValue))

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
        containerHasChanged = False
        if self.value != value:
            self.hasChanged = True
            if self.container:
                self.container.hasChanged = True
                containerHasChanged = True

        Variable.set(self, value)

        # If the value is input to a function execute the function code (if all
        # input is set).
        if self.ownerFunction and (self in self.ownerFunction.inputValues or \
            self in self.ownerFunction.subnetInputValues):
            self.ownerFunction.functionInstance.isFinished = False
            self.ownerFunction.execute()

        if containerHasChanged:
            if self.container.ownerFunction and (self.container in self.container.ownerFunction.inputValues or \
                                                 self.container in self.container.ownerFunction.subnetInputValues):
                self.container.ownerFunction.functionInstance.isFinished = False
                self.container.ownerFunction.execute()

    def setByConnection(self, value):
        """ Update self.value when it is connected to a value that has been
            changed.

           :param value     : The new value (that had been modified before
                              causing this function to be called).
        """

        if self.value != value:
            self.hasChanged = True

        self.value = value

        if self.ownerFunction:
            if self in self.ownerFunction.inputValues or self in \
                self.ownerFunction.subnetInputValues:
                self.ownerFunction.functionInstance.isFinished = False
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
                print "Cannot add a connection from a value that is not an output value."
                return
            if self in self.ownerFunction.subnetOutputValues:
                if toValue.ownerFunction not in self.ownerFunction.subnetFunctions:
                    print "Cannot add a connection. Connected value is not part of the function subnet."
                    return
                if toValue not in toValue.ownerFunction.inputValues and \
                   toValue not in toValue.ownerFunction.subnetInputValues:
                    print "Cannot add a connection. Connected value is not part of the function subnet."
                    return

        self.changed.connect_safe(toValue.setByConnection)

        if self.value != toValue.value:
            toValue.value = self.value
            toValue.hasChanged = True
            if toValue.ownerFunction:
                toValue.ownerFunction.functionInstance.isFinished = False
                toValue.ownerFunction.execute()

    def removeConnection(self, toValue):
        """ Remove all connections from this value to another.
            toValue will no longer reflect changes made to this value.

           :param toValue: The value to which all connections (from this value)
                           should be removed.
        """

        self.changed.disconnect_all(toValue, fromValue=self)

class BoolValue(Value):

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)

    def is_allowed_value(self, value):

        if value == None or isinstance(value, bool):
            return True
        else:
            return False

class IntValue(Value):

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)

    def is_allowed_value(self, value):

        if value == None or isinstance(value, IntType):
            return True
        else:
            return False

class FloatValue(Value):

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)

    def is_allowed_value(self, value):

        if value == None or isinstance(value, (IntType, FloatType)):
            return True
        else:
            return False

class StringValue(Value):

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        Value.__init__(self, initialValue, name, ownerFunction, container,
                       optional, description)

    def is_allowed_value(self, value):

        # Allow both StringType and UnicodeType
        if value == None or isinstance(value, StringType):
            return True
        else:
            return False

class ListValue(Value):

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

    def set(self, value):

        iv = list(value)
        if self.dataType:
            t = self.dataType
        else:
            t = Value
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

    def append(self, value):

        if self.dataType:
            if isinstance(value, Value):
                assert isinstance(value, self.dataType)
                self.value.append(value)
                value.container = self
            else:
                newValue = self.dataType(value, container=self)
                self.value.append(newValue)

        else:
            assert isinstance(value, Value), "If a list does not have a data type specified values can only be appended if they are a Value object."
            self.value.append(value)
            value.container = self

        # Update the hasChanged flag
        self.hasChanged = True
        # If the value is input to a function execute the function code (if all input is set).
        if self.ownerFunction and (self in self.ownerFunction.inputValues or \
                                   self in self.ownerFunction.subnetInputValues):
            self.ownerFunction.functionInstance.isFinished = False
            self.ownerFunction.execute()

class DictValue(Value):

    def __init__(self, initialValue=None, name=None, ownerFunction=None,
                 container=None, optional=False, description=''):

        if initialValue:
            assert isinstance(initialValue, DictType)
            iv = dict(initialValue)
        else:
            iv = {}

        Value.__init__(self, iv, name, ownerFunction, container,
                       optional, description)

    def is_allowed_value(self, value):

        if value == None or isinstance(value, DictType):
            return True
        else:
            return False

