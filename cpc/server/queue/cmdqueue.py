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


from collections import deque
from threading import Lock
import logging

'''
Created on Oct 26, 2010

@author: iman
'''
log=logging.getLogger('cpc.server.queue.cmdqueue')

class CmdQueue():
    PRIO_LOW_BOUND = -12 #Constant
    PRIO_HIGH_BOUND = 12 #Constant

    def __init__(self):
        self.data = [] 
        # this is a list of deques with the highest priority queue first. 
        self.queue = [ deque() for x in range(CmdQueue.PRIO_LOW_BOUND-1, 
                                              CmdQueue.PRIO_HIGH_BOUND)]
        # TODO: finer grained locks. For now we have a single global lock.
        self.lock=Lock()

    def getSize(self):
        """Count the number of elements in the queue."""
        size=0
        with self.lock:
            for dq in self.queue:
                size+=len(dq)
        return size

    def _getDeque(self, prio):
        """Low-level function that gets the deque associated with a priority
           prio = the priority (out-of-bound priorities are mapped onto maximum
                                and minimum priorities).
           returns: a deque. """
        if prio < CmdQueue.PRIO_LOW_BOUND:
            prio = CmdQueue.PRIO_LOW_BOUND 
        if prio > CmdQueue.PRIO_HIGH_BOUND:
            prio = CmdQueue.PRIO_HIGH_BOUND
        # the highest priority queue is first
        p= (CmdQueue.PRIO_HIGH_BOUND - prio) 
        return self.queue[p]

    def add(self,command):
        """
            description:  puts a command in the queue  
            required: Command:command
            result : command put in queue, queue sorted in priority order of 
                     commands, return true
        """    
        ret=False
        # an ID lives for as long as a command is queued/running
        command.tryGenID() 
        with self.lock:
            prio=command.getFullPriority()
            dq=self._getDeque(prio)
            dq.append(command)
            ret=True
        return ret


    def remove(self, cmd):
        """Remove a specific command.
           NOTE: this is an O(N) operation for N=number of items in the queue"""
        nremoved=0
        with self.lock:
            for dq in self.queue:
                n=len(dq)
                for i in range(n):
                    if dq[0] == cmd:
                        nremoved+=1
                        dq.popleft()
                    else:
                        dq.rotate(-1)
                if nremoved > 0:
                    return
       
    def get(self):
        """ description: gets a single element with the highest priority from 
            the queue
            result: return Command:command
        
            alternate result: if no commands in queue return None
            """    
        #find element with the highest priority
        with self.lock:
            for dq in self.queue:
                if len(dq)>0:
                    return dq.popleft()
            return None

    def getUntil(self, fn, parm):
        """Get a number of items from the queue, based on the output of a 
           function (given as parameter).
           fn = the function to test each item with. Should return a tuple of
                two booleans: the first decides whether to continue the function
                              and the second decides whether to remove the 
                              current item from the queue.
           parm = a parameter for the function fn. It will be called with
                    fn(parm, queueItem), where queueItem is the queued item
                    being looked at.
           returns: the list of items removed from the queue.""" 
        ret=[]
        cont=True
        with self.lock:
            for dq in self.queue:
                n=len(dq)
                nback=0
                for i in range(n):
                    cont, doPop=fn(parm, dq[0])
                    if doPop:
                        ret.append(dq.popleft())
                    else:
                        dq.rotate(-1)
                        nback+=1
                    if not cont:
                        break
                dq.rotate(nback)
                if not cont:
                    break
        return ret

    def _exists(self, commandID):
        # non-locking version of public exists()
        #NOTE could be slow 
        for value in self.queue.itervalues():
            for it in value:
                if(it.id == commandID): 
                    return True
        return False    
        
    def exists(self,commandID):
        """Check whether commandID exists in the queue. 
           NOTE: this is an O(N) operation for N=number of items in the queue"""
        with self.lock:
            return self._exists(commandID)
  
    def list(self):
        """Return a list with all queued items."""
        ret=[]
        with self.lock:
            for dq in self.queue:
                ret.extend(dq)
        return ret

    def deleteByProject(self, project):
        """Delete all commands related to a project. Returns number of commands
           deleted.
           NOTE: this is an O(N) operation for N=number of items in the queue"""
        nremoved=0
        with self.lock:
            for dq in self.queue:
                n=len(dq)
                for i in range(n):
                    if dq[0].task.project == project:
                        nremoved+=1
                        dq.popleft()
                    else:
                        dq.rotate(-1)     
        return nremoved



    #Helper function for unit tests
    def indexOfCommand(self,command):
        i=0
        with self.lock:
            for dq in self.queue:
                for item in self.dq:
                    if(item == command): 
                        return i
                    i+=1      
        return None    
        
    
