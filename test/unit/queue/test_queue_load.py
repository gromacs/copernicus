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


import unittest
import random
from threading import Thread
from cpc.server.task import Task
from cpc.server.queue import Queue



class TestQueue(unittest.TestCase):
    
    
    def setUp(self):
        self.queue = Queue()
    
   
    def testAddHundredThousand(self):
        num = 1000000

        tasks = self.generateTasks(num)

        def addToq(task):
            self.queue.add(task)    

        for i  in range(num):
            Thread(target=addToq,args=(tasks[i],)).start()
        
        ''' verify that they are sorted in priority order '''
        ''' verify that there exists 100 elements in the queue '''
        self.assertEquals(self.queue.size,num)      
  
        
      
    def generateTasks(self,num):
        list = []        
        for i in range(num):
            task = Task()
            task.id = i
            task.priority = random.randint(Queue.PRIO_LOW_BOUND,Queue.PRIO_HIGH_BOUND)
            list.append(task) 
                
        return list
        
  
            
            
        
