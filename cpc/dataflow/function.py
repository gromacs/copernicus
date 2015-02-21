import subprocess

def executeSystemCommand(cmd, inp=None):
    """ Executes a system command and returns the output.

       :param cmd : The command to execute. This is supplied as a list
                    containing all arguments.
       :type cmd  : list.
       :inp       : Input to be directed to the command
                    (not command-line arguments).
       :type inp  : str.
       :returns   : The output of the command.
    """

    if not inp:
        output = ''.join(subprocess.check_output(cmd, stderr=subprocess.STDOUT))
    else:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)

        output = ''.join(p.communicate(input=inp)[0])

    return output

class FunctionBase(object):
    """ This class contains basic data and data management functions.
        It is inherited by Function and FunctionPrototype."""

    def __init__(self, name):

        self.name = name
        self.inputValues = []
        self.outputValues = []
        self.subnetInputValues = []
        self.subnetOutputValues = []

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

    def getOutputValueContainer(self, name):
        """ Get the (first) output Value object named as specified.

           :param name : The name of the value to retrieve.
           :type name   : str.
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
            print 'Value %s does not exist' % name

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
            print 'Value %s does not exist' % name

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
            print 'Value %s does not exist' % name

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
            print 'Value %s does not exist' % name

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
            print 'Value %s does not exist' % name

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
            print 'Value %s does not exist' % name

class FunctionPrototype(FunctionBase):
    """ This class is inherited to describe how a function works and what input
        and output values it has. The actual function instances are of class
        Function.
    """

    def __init__(self, name):

        FunctionBase.__init__(self, name)

    def execute(self):
        """ This function should be overloaded to contain the code that should
            be executed by a function.
        """

        return

class Function(FunctionBase):
    """ This is an instance of a function, with its own input and output
        data.
    """

    def __init__(self, functionPrototype, name=None, dataNetwork=None):

        assert functionPrototype, "A function must have a function prototype."
        assert isinstance(functionPrototype, FunctionPrototype), "The function prototype of the function must be of class FunctionPrototype."

        FunctionBase.__init__(self, name)

        self.functionInstance = functionPrototype
        self.dataNetwork = dataNetwork
        self.frozen = False
        self.subnetFunctions = []
        self.inputValues = list(functionPrototype.inputValues)
        self.outputValues = list(functionPrototype.outputValues)
        self.subnetInputValues = list(functionPrototype.subnetInputValues)
        self.subnetOutputValues = list(functionPrototype.subnetOutputValues)

        for v in self.inputValues + self.outputValues + self.subnetInputValues + \
            self.subnetOutputValues:
            v.ownerFunction = self
        if name:
            self.name = name

    def freeze(self):
        """ Make the function frozen. A frozen function does not execute
            when its input is changed.
        """

        self.frozen = True

    def unfreeze(self):
        """ Remove the frozen state. The function will execute if any of the
            inputs have changed during the period it was frozen.
        """

        self.frozen = False
        self.execute()

    def isFrozen(self):
        """ Return if the function is frozen or not.

           :returns : True if frozen, False if not frozen.
        """

        return self.frozen

    def inputHasChanged(self):
        """ Check if the input or subnet input of this function
            has changed since it was last executed.

           :returns : True if the input has changed, False if not.
        """

        for v in self.inputValues + self.subnetInputValues:
            if v.hasChanged:
                return True
        return False

    def resetInputChange(self):
        """ Set the hasChanged status of all inputs and subnet inputs to False.
        """

        for v in self.inputValues + self.subnetInputValues:
            v.hasChanged = False
        # TODO: Reset status of values in a list

    def execute(self):
        """ Execute the actual function executable (from the function definition
            itself). There are checks that the required input is available and
            also that the input has changed since last running the executable
            block.

            :returns : True if running the executable block, False if not
                       executing, i.e. due to missing input.
        """

        if not self.frozen and self.inputHasChanged():
            from value import Value, ListValue, DictValue
            for iv in self.inputValues:
                if iv == None or not isinstance(iv, Value) or \
                   (iv.optional == False and iv.value == None):
                    return False
                if isinstance(iv, ListValue):
                    if len(iv.value) == 0:
                        return False
                    # Chances are the last value is set last, so traverse
                    # the list in reverse order.
                    for v in reversed(iv.value):
                        if v == None or not isinstance(v, Value) or \
                           v.value == None:
                            return False
                elif isinstance(iv, DictValue):
                    for v in iv.value.values():
                        if v == None or not isinstance(v, Value) or \
                           v.value == None:
                            return False
            #print 'Will execute', self.name
            if self.functionInstance.execute():
                return self.resetInputChange()

        else:
            return False
