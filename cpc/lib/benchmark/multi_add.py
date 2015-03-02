import logging
from cpc.dataflow import FloatValue

log=logging.getLogger(__name__)

def multi_add(inp):
    if (inp.testing()):
        return

    fo = inp.getFunctionOutput()

    values = inp.getInput('terms') or []
    s = sum([v.getValue() for v in values])

    fo.setOut('sum', FloatValue(s))

    return fo
