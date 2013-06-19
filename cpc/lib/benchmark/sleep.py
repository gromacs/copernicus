import logging
import os
import time
import math
from cpc.dataflow import IntValue, FloatValue, StringValue
import cpc.command
from cpc.lib.gromacs import iterate

log = logging.getLogger('cpc.lib.benchmark')

def sleep(inp):
    if (inp.testing()):
        return

    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
        "starttime.dat"))

    fo = inp.getFunctionOutput()
    sleepTime = inp.getInput('sleep_time')

    if inp.cmd is None:
        startTime = int(time.time())
        pers.set("startTime", startTime)
        #add the sleep command on the queue
        cmd = cpc.command.Command(inp.getPersistentDir(), "benchmark/sleep",
            [sleepTime])
        fo.addCommand(cmd)

    else:
        endTime = int(time.time())
        startTime = pers.get("startTime")

        roundtripTime = endTime - startTime

        fo.setOut("exec_time.end_timestamp", IntValue(endTime))
        fo.setOut("exec_time.start_timestamp", IntValue(pers.get("startTime")))
        fo.setOut("exec_time.roundtrip_time", IntValue(roundtripTime))

    pers.write()
    return fo


def collectResults(inp):
    if (inp.testing()):
        return

    fo = inp.getFunctionOutput()
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
        "persistent.dat"))


    init = 0
    if (pers.get("init")):
        init = pers.get("init")

    startTime = None
    log.debug("init is %s"%init)
    if (inp.getInputValue('sleep_time_array').isUpdated()):
        if(init == 0):
            log.debug("DOING INIT")
            startTime = int(time.time())
            fo.setOut('start_time', IntValue(startTime))
            pers.set('startTime', startTime)
            init= 1


    if (init ==1):
        num_samples = inp.getInput('num_samples')
        log.debug("Calculating")
        #calculating results all the time
        endTime = int(time.time())

        if startTime==None:
            startTime = pers.get('startTime')

        log.debug("start %s end %s"%(startTime,endTime))
        fo.setOut('end_time', IntValue(endTime))
        totalTime = endTime - startTime
        fo.setOut('total_time', IntValue(totalTime))
        averageTime = float(endTime - startTime) / float(num_samples)
        #averageTime = math.ceil(averageTime)
        fo.setOut("csv_result", StringValue("%s,%s,%s" % (num_samples, totalTime,
                                                          averageTime)))
        fo.setOut("average_time", FloatValue(averageTime))

    pers.set("init", init)
    pers.write()

    return fo