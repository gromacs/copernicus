'''
Created on Nov 6, 2011

@author: iman
'''

class WorkerState(object):
    '''
    classdocs
    '''


    def __init__(self,host,status,workerId=None):        
        #host and id   
        self.workerId = workerId
        self.host= host
        #self.id = "%s:%s"%(host,workerId)
        self.id = host
        self.status = status

    
        