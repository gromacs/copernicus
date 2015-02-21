import logging
import time
import os
import os.path
import cpc.dataflow
from cpc.dataflow import FloatValue, IntValue

log=logging.getLogger(__name__)

def multi_add(inp):
    
    if (inp.testing()):
        return

    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    
    fo = inp.getFunctionOutput()

    values = inp.getInput('terms') or []
    if values == []:
        return fo

    floatVals = [inp.getInput('terms[%d]' % i) for i in xrange(len(values))]
    if None in floatVals:
        return fo
    
    s = sum(floatVals)

    fo.setOut('sum', FloatValue(s))

    return fo

def add_benchmark(inp):

    if (inp.testing()):
        return

    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))

    fo = inp.getFunctionOutput()

    n_instances = inp.getInput('n_instances') or 1000

    prev_inst = pers.get('n_instances') or 0

    # Generate all instances first

    for i in range(prev_inst, n_instances):
        fo.addInstance('multi_add_%d' % i, 'multi_add')

    for i in range(n_instances/2, n_instances):
        for j in range(i - n_instances/2 + 1):
            fo.addConnection('multi_add_%d:out.sum' % j, 'multi_add_%d:in.terms[%d]' % (i, j))

    for i in range(n_instances/2):
        cnt = 0
        for j in range(i, i+10):
            fo.addConnection(None, 'multi_add_%d:in.terms[%d]' % (i, cnt), FloatValue(j))
            cnt += 1

    pers.set('n_instances', n_instances)
    pers.write()

    return fo
