'''
Created on Nov 6, 2011

@author: iman
'''

class WorkerState(object):
    """
    Maintains state and information for a worker
    Only servers which workers are directly connected to maintains these state
    objects
    """


    def __init__(self,host,state,workerId=None):
        #host and id
        self.workerId = workerId
        self.host= host
        #self.id = "%s:%s"%(host,workerId)
        self.id = host
        self.state = state

    def setState(self, state):
        """Sets the state for this worker"""
        self.state = state
    
        