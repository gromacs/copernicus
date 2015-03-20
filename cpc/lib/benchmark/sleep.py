import logging
import os
import time

from cpc.dataflow.persistence import Persistence
from cpc.dataflow.value import IntValue, FloatValue, StringValue, DictValue, ListValue
from cpc.dataflow.function import FunctionPrototype, Function
import cpc.command

log=logging.getLogger(__name__)

class TimingsValue(DictValue):

    def __init__(self, initialValue=None, name='timings', ownerFunction=None, container=None, optional=False, description='Start and end timestamps', dataType=None):

        DictValue.__init__(self,
                           {'start_timestamp': IntValue(None, name='start_timestamp',
                            description='Unix timestamp for when the job starts. Is set in the initial phase before a job is put on the queue'),
                            'end_timestamp': IntValue(None, name='end_timestamp',
                            description='Unix timestamp for when the job ended. Is set once a command has been returned from a worker called'),
                            'roundtrip_time': IntValue(None, name='roundtrip_time',
                            description='end_timestamp-start_timestamp')},
                            name=name, ownerFunction=ownerFunction, container=container, optional=optional, description=description, dataType=dataType)

class Sleep(FunctionPrototype):

    def __init__(self, name=None):

        FunctionPrototype.__init__(self, name, useOutputDir=False, usePersistentDir=True, hasLog=False)

        self.description = 'send a job that sleeps for a set amount of time on the worker side.'

        if name == None:
            self.name = 'sleep'

        self.inputValues = [IntValue(None, name='sleep_time', ownerFunction=self,
                                     description='Sleep time in seconds.')]
        self.outputValues = [TimingsValue(None, name='exec_time', ownerFunction=self,
                                        description='Start and end timings for the whole roundtrip.')]

    def execute(self, function = None):

        if function:
            assert isinstance(function, Function)
            self = function

        persDir = self.getPersistentDir()

        pers = Persistence(os.path.join(persDir,
                           "starttime.dat"))

        startTime = int(time.time())
        pers.set("startTime", startTime)

        sleepTime = self.getInputValueContents('sleep_time')

        cmd = cpc.command.Command(persDir, "benchmark/sleep",
                                  [sleepTime])

        log.debug('Created command: %s' % cmd)

        self.addCommand(cmd)

        pers.write()

    def executeFinished(self, function = None):

        if function:
            assert isinstance(function, Function)
            self = function

        persDir = self.getPersistentDir()

        pers = Persistence(os.path.join(persDir,
                           "starttime.dat"))

        endTime = int(time.time())
        startTime = pers.get("startTime")

        roundtripTime = endTime - startTime

        exec_time = self.getOutputValueContainer('exec_time')
        exec_time.setSubValue('end_timestamp', endTime)
        exec_time.setSubValue('start_timestamp', startTime)
        exec_time.setSubValue('roundtrip_time', roundtripTime)

class CollectResults(FunctionPrototype):

    def __init__(self, name=None):

        FunctionPrototype.__init__(self, name, useOutputDir=False, usePersistentDir=True, hasLog=False)

        self.description = 'Collects results.'

        if name == None:
            self.name = 'result_collector'

        self.inputValues = [IntValue(None, name='num_samples', ownerFunction=self,
                                     description='Number of expected samples to average over.'),
                            ListValue(None, name='sleep_time_array', ownerFunction=self,
                                      dataType=TimingsValue,
                                      description='Sleep time in seconds.')]
        self.outputValues = [IntValue(None, name='start_time', ownerFunction=self,
                                      description='Average roundtrip time'),
                             IntValue(None, name='end_time', ownerFunction=self,
                                      description='Average roundtrip time'),
                             IntValue(None, name='total_time', ownerFunction=self,
                                      description='Average roundtrip time'),
                             FloatValue(None, name='average_time', ownerFunction=self,
                                        description='Average roundtrip time'),
                             StringValue(None, name='csv_results', ownerFunction=self,
                                         description='Returns results in csv format, format is: NUM_JOBS,AVERAGE_TIME')]

    def execute(self, function = None):

        if function:
            assert isinstance(function, Function)
            self = function

        persDir = self.getPersistentDir()

        pers = Persistence(os.path.join(persDir,
                           "persistent.dat"))

        init = pers.get("init") or 0

        startTime = None
        log.debug("init is %s"%init)
        if init == 0:
            log.debug("DOING INIT")
            startTime = int(time.time())
            self.setOutputValueContents('start_time', startTime)
            pers.set('startTime', startTime)
            init = 1


        if init == 1:
            num_samples = self.getInputValueContents('num_samples')
            log.debug("Calculating")
            #calculating results all the time
            endTime = int(time.time())

            if startTime==None:
                startTime = pers.get('startTime')

            log.debug("start %s end %s"%(startTime,endTime))
            self.setOutputValueContents('end_time', endTime)
            totalTime = endTime - startTime
            self.setOutputValueContents('total_time', totalTime)
            averageTime = float(endTime - startTime) / num_samples
            self.setOutputValueContents('csv_results', '%s,%s,%s' % (num_samples,
                                                                    totalTime,
                                                                    averageTime))
            self.setOutputValueContents('average_time', averageTime)

        pers.set('init', init)
        pers.write()


#def sleep(inp):
    #if (inp.testing()):
        #return

    #pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
        #"starttime.dat"))

    #fo = inp.getFunctionOutput()
    #sleepTime = inp.getInput('sleep_time')

    #if inp.cmd is None:
        #startTime = int(time.time())
        #pers.set("startTime", startTime)
        ##add the sleep command on the queue
        #cmd = cpc.command.Command(inp.getPersistentDir(), "benchmark/sleep",
            #[sleepTime])
        #fo.addCommand(cmd)

    #else:
        #endTime = int(time.time())
        #startTime = pers.get("startTime")

        #roundtripTime = endTime - startTime

        #fo.setOut("exec_time.end_timestamp", IntValue(endTime))
        #fo.setOut("exec_time.start_timestamp", IntValue(pers.get("startTime")))
        #fo.setOut("exec_time.roundtrip_time", IntValue(roundtripTime))

    #pers.write()
    #return fo


#def collectResults(inp):
    #if (inp.testing()):
        #return

    #fo = inp.getFunctionOutput()
    #pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
        #"persistent.dat"))


    #init = 0
    #if (pers.get("init")):
        #init = pers.get("init")

    #startTime = None
    #log.debug("init is %s"%init)
    #if (inp.getInputValue('sleep_time_array').isUpdated()):
        #if(init == 0):
            #log.debug("DOING INIT")
            #startTime = int(time.time())
            #fo.setOut('start_time', IntValue(startTime))
            #pers.set('startTime', startTime)
            #init= 1


    #if (init ==1):
        #num_samples = inp.getInput('num_samples')
        #log.debug("Calculating")
        ##calculating results all the time
        #endTime = int(time.time())

        #if startTime==None:
            #startTime = pers.get('startTime')

        #log.debug("start %s end %s"%(startTime,endTime))
        #fo.setOut('end_time', IntValue(endTime))
        #totalTime = endTime - startTime
        #fo.setOut('total_time', IntValue(totalTime))
        #averageTime = float(endTime - startTime) / float(num_samples)
        ##averageTime = math.ceil(averageTime)
        #fo.setOut("csv_result", StringValue("%s,%s,%s" % (num_samples, totalTime,
                                                          #averageTime)))
        #fo.setOut("average_time", FloatValue(averageTime))

    #pers.set("init", init)
    #pers.write()

    #return fo