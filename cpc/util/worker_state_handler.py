import logging
import time

from cpc.util.conf.server_conf import ServerConf

log =logging.getLogger('cpc.util.worker_state_handler')
class WorkerStateHandler(object):
    @staticmethod
    def getConnectedWorkers(workerStates):

        '''
            input:
                workerstates: dict<workerId><WorkerState>

            returns:
                array<WorkerState>
        '''

        '''
        Workers should have communicated with the server
        at least within the hearbeat interval time
        to be defined as connected.
        '''

        connectedWorkers = []
        timeLimit= ServerConf().getHeartbeatTime()
        now = time.time()
        for w in workerStates.itervalues():
            timeSinceCommmunication = int(now - w.lastCommunication)
            if (timeSinceCommmunication < timeLimit):
                connectedWorkers.append(w)

        return connectedWorkers
