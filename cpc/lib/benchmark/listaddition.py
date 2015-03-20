import logging
import os

from cpc.dataflow.persistence import Persistence
from cpc.dataflow.value import IntValue, FloatValue, ListValue
from cpc.dataflow.function import FunctionPrototype, Function

log=logging.getLogger(__name__)

class ListAdditionFunction(FunctionPrototype):

    def __init__(self, name=None):

        FunctionPrototype.__init__(self, name, useOutputDir=False,
                                   usePersistentDir=False, hasLog=False)

        self.description = 'Compute the sum of a list of float values.'

        if name == None:
            self.name = 'addition'

        self.inputValues = [ListValue(None, name='terms', ownerFunction=self,
                                      description='A list of numbers to be added',
                                      dataType=FloatValue)]
        self.outputValues = [FloatValue(None, name='sum', ownerFunction=self,
                                        description='The sum of all numbers')]

    def execute(self, function = None):

        if function:
            assert isinstance(function, Function)
            self = function

        if self.isFinished:
            return False

        terms = self.getInputValueContainer('terms')

        #log.debug('TERMS %s' % terms)

        s = self.getOutputValueContainer('sum')
        #print term1, term1.value, term2, term2.value, s, s.value

        s.value = sum([t.value for t in terms.value])
        self.isFinished = True
        return True

class MultiAdd(FunctionPrototype):

    def __init__(self, name=None):

        FunctionPrototype.__init__(self, name, useOutputDir=False,
                                   usePersistentDir=True, hasLog=False)

        self.description = 'Compute the sum of a number of addition instances.'

        if name == None:
            self.name = 'multi_add'

        log.debug('multi_add __init__')

        self.inputValues = [IntValue(0, name='n_instances', ownerFunction=self,
                                     description='The number of addition functions that should be generated')]
        self.subnetInputValues = [ListValue(None, name='terms', ownerFunction=self,
                                  description='A list of numbers to be added',
                                  dataType=FloatValue)]
        self.outputValues = [FloatValue(None, name='sum', ownerFunction=self,
                                        description='The sum of all numbers')]
        self.isFinished = False

    def execute(self, function = None):

        if function:
            assert isinstance(function, Function)
            self = function

        log.debug('multi_add execute')

        pers = Persistence(os.path.join(self.getPersistentDir(),
                           "persistent.dat"))

        prev_inst = pers.get('n_instances' or 0)

        n_instances = self.getInputValueContents('n_instances')

        for i in range(n_instances):
            inst = self.addSubnetFunction('add_%d' % i, 'benchmark::addition')

        for i in range(n_instances/2, n_instances):
            name = 'add_%d' % i
            inst = self.getSubnetFunction(name)
            inpTerms = inst.getInputValueContainer('terms')
            for j in range(i - n_instances/2 + 1):
                name = 'add_%d' % j
                inst = self.getSubnetFunction(name)
                outp = inst.getOutputValueContainer('sum')
                #log.debug('Subnetfunction: %s, self: %s.' % (inst, self))
                inp = inpTerms.getCreateSubValue(j)
                outp.addConnection(inp)

        for i in range(n_instances/2):
            name = 'add_%d' % i
            inst = self.getSubnetFunction(name)
            v = inst.getInputValueContainer('terms')
            v.value = range(i, i+10)

        pers.set('n_instances', n_instances)
        pers.write()