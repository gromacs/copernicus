'''
Created on Nov 6, 2011

@author: iman
'''
import time



class WorkerStatus():
    WORKER_STATUS_CONNECTED = 'connected'
    WORKER_STATUS_NOT_CONNECTED = 'not_connected'

class WorkerState(object):
    """
    Maintains state and information for a worker
    Only servers which workers are directly connected to maintains these state
    objects
    """


    def __init__(self,host,state,workerId):
        '''
        lastCommunication:float seconds
        '''
        self.workerId = workerId
        self.host= host
        #self.id = "%s:%s"%(host,workerId)
        self.id = self.workerId
        self.state = state
        self.lastCommunication = time.time()

    def setState(self, state):
        """Sets the state for this worker

           lastCommunication:float object
        """
        self.state = state
        self.lastCommunication = time.time()
    
        