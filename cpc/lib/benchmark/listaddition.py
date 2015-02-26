from cpc.dataflow.value import FloatValue, ListValue
from cpc.dataflow.function import FunctionPrototype
from cpc.dataflow.library import Library

class BenchmarkLibrary(Library):

    name = 'benchmark'
    description = 'A benchmark library that contains a function for calculating the sum of a list of numbers.'

    def __init__(self):

        Library.__init__(self, {'additionFunction': ListAdditionFunction()})


class ListAdditionFunction(FunctionPrototype):

    description = 'Compute the sum of a list of float values.'

    def __init__(self, name=None):

        FunctionPrototype.__init__(self, name)

        if name == None:
            self.name = 'additionFunction'

        self.inputValues = [ListValue(None, name='terms', ownerFunction=self,
                                      description='A list of numbers to be added',
                                      dataType=FloatValue)]
        self.outputValues = [FloatValue(None, name='sum', ownerFunction=self,
                                        description='The sum of all numbers')]
        self.isFinished = False

    def execute(self):

        if self.isFinished:
            return False

        terms = self.getInputValueContainer('terms')

        s = self.getOutputValueContainer('sum')
        #print term1, term1.value, term2, term2.value, s, s.value

        s.value = sum([t.value for t in terms.value])
        self.isFinished = True
        return True
