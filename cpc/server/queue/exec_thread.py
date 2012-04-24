# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import threading
import logging
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import sys
import os
import traceback



log=logging.getLogger('cpc.queue.exec_thread')

import cpc.util

class ExecThreadError(cpc.util.CpcError):
    pass

class TaskExecThreads(object):
    """A collection of taskexec threads."""
    def __init__(self, conf, N, taskQueue, cmdQueue):
        self.taskQueue=taskQueue
        self.cmdQueue=cmdQueue
        self.threads=[]
        for i in range(N):
            te=TaskExecThread(taskQueue, cmdQueue)
            self.threads.append(te)
        self.lock=threading.Lock()
        self.tw=None
        nc=conf.getServerCores()
        if nc>0:
            log.debug("Setting max. nr. of OpenMP cores to %d"%nc)
            os.environ['OMP_NUM_THREADS']=str(nc)

    def pause(self):
        """Pause all task exec threads. Returns when they have
           in fact paused"""
        if self.tw is not None:
            raise ExecThreadError("double pause")
        self.tw=ThreadWaiter(len(self.threads))
        for th in self.threads:
            th.doPause(self.tw)
        for th in self.threads:
            # queue a None so that each thread reaches the waiting point.
            th.queueNone()            
        self.tw.waitUntilZero()

    def cont(self):
        """continue  all task exec threads."""
        self.tw.finishWaiting()
        # object keeps existing in threads, GC takes care of the rest.
        self.tw=None 

    def acquire(self):
        """Acquire the lock to do pause/cont."""
        self.lock.acquire()
    def release(self):
        """Release the lock to do pause/cont."""
        self.lock.release()
    def stop(self):
        """stop (quit/join) all task exec threads.  """
        for th in self.threads:
            th.doStop()
        for th in self.threads:
            # queue a None so that each thread reaches the waiting point.
            th.queueNone()            
        #for th in self.threads:
        #    # queue a None so that each thread reaches the waiting point.
        #    th.thread.join()


class ThreadWaiter(object):
    """A thread waiter: waits on waitUntilZero until all n threads have
       called release().""" 
    def __init__(self, N):
        self.N=N
        self.sema=threading.Semaphore(0)
        self.cond=threading.Condition()
        self.cont=False

    def releaseAndWait(self):
        """Exec threads call this: decreease the active thread counter, and
           wait until the self.ended condition is true."""
        self.cond.acquire()
        self.N -= 1
        if self.N == 0:
            self.sema.release()
        while not self.cont:
            self.cond.wait()
        self.cond.release()

    def waitUntilZero(self):
        self.sema.acquire()

    def finishWaiting(self):
        self.cont=True
        self.cond.acquire()
        self.cond.notifyAll()
        self.cond.release()



class TaskExecThread(object):
    """A dataflow task execution thread; executes any tasks that are not 
       commands, and queues commands into a command queue."""
    def __init__(self, taskQueue, cmdQueue):
        """Start the task exec thread with a task queue and a command queue.
            taskQueue = the task queue to take tasks from
            cmdQueue = the command queue to add commands to"""
        self.taskQueue=taskQueue
        self.cmdQueue=cmdQueue
        self.lock=threading.Lock()
        # the condtion predicates
        self.stop=False
        self.pause=False
        self.thread=threading.Thread(target=taskExecThreadStarter, args=(self,))
        self.thread.start()

    def queueNone(self):
        self.taskQueue.putNone()

    def doStop(self):
        """Stop the thread at the next iteration."""
        with self.lock:
            self.stop=True

    def doPause(self, waiter):
        """Pause the thread until notified with the condition from init().
           waiter =  a thread waiter object"""
        with self.lock:
            self.pause=True
            self.waiter=waiter

    def execLoop(self):
        """The execution loop for the exec thread."""
        while True:
            try:
                with self.lock:
                    if self.stop:
                        return
                    elif self.pause:
                        # signal that we're waiting, and wait
                        log.debug("Pausing...")
                        self.waiter.releaseAndWait()
                #log.debug("Waiting for queued task..")
                task=self.taskQueue.get()
                if task is not None:
                    #log.debug("Got queued task.")
                    (newcmds, cancelcmds)=task.run()
                    if newcmds is not None:
                        for cmd in newcmds:
                            log.debug("Queuing command")
                            self.cmdQueue.add(cmd)
                    if cancelcmds is not None:
                        for cmd in cancelcmds:
                            log.debug("Canceling command")
                            self.cmdQueue.remove(cmd)
            except:
                fo=StringIO()
                traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                          sys.exc_info()[2], file=fo)
                errmsg="Exec thread exception: %s"%(fo.getvalue())
                log.error(errmsg)

def taskExecThreadStarter(taskExecThread):
    """Thread starter function for TaskExecThread object."""
    log.debug("Started task exec thread.")
    taskExecThread.execLoop()

