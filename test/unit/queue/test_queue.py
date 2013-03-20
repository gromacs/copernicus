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
    
#    def testSingleton(self):
#        newq = Queue()
#        
#        self.assertEqual(self.queue,newq)
#        #ensure all states are identical             
   
    def testAdd(self):
                        
        task = Task()
        task.id = 1
        task.priority = 1        
        self.queue.add(task)
        
        ''' verify the size of the queue has increased by one '''
        self.assertEquals(1,self.queue.getSize())       
        
        ''' verify that the task added exists in the queue'''
        self.assertTrue(self.queue.exists(1))        
        
        ''' add a second task '''
        task2 = Task()
        task2.id = 2
        task2.priority = 2
        self.queue.add(task2)
        
        ''' verify the size of the queue has increased by one '''
        self.assertEquals(2,self.queue.getSize())  
        
        ''' verify that the task added exists in the queue'''
        self.assertTrue(self.queue.exists(2))   
                        
     
    def testAddAllPriorities(self):
        pass


    def testAddNoPriority(self):
        task = Task()
        task.id = 1                
        self.queue.add(task)
        
        ''' verify the size of the queue has increased by one '''
        self.assertEquals(0,self.queue.getSize())       
        

    def testAddSamePriority(self):

        task = Task()
        task.id = 1
        task.priority = 1        
        self.queue.add(task)
                        
        ''' create second task with same priority '''
        task2 = Task()
        task2.id = 2
        task2.priority = 1        
        self.queue.add(task2)
        
        
        ''' verify that both tasks exist in queue '''
        self.assertTrue(self.queue.exists(1))
        self.assertTrue(self.queue.exists(2))
        
        ''' verify that the second task is behind the first task in queue '''
        #TODO how to check this
        self.assertTrue(self.queue.indexOfTask(task)>self.queue.indexOfTask(task2))
 
 
    def testAddDuplicate(self):

        task = Task()
        task.id = 1
        task.priority = 1        
        self.queue.add(task)
        
        '''create a task with same id but with different content'''
        task2 = Task()
        task2.id = 1
        task2.priority = 10        
        self.queue.add(task2)
                                
        
        ''' verify that the size has not changed '''
        self.assertEquals(self.queue.getSize(),1)
        ''' verify that the new task do not exist in queue '''
        # TOOD how to test the internals of the queue?
   
     
    def testAddHundred(self):
        
        num = 100
        tasks = self.generateTasks(num)
                 
        def addToq(task):
            self.assertTrue(self.queue.add(task))    

        for i  in range(0,num):
            Thread(target=addToq,args=(tasks[i],)).start()
        
        ''' verify that they are sorted in priority order '''
        ''' verify that there exists 100 elements in the queue '''
        self.assertEquals(self.queue.getSize(),num)        
        
                  
    def testGet(self):        
        tasks = self.generateTasks(100)         
        for i in range(100):
            self.queue.add(tasks[i])
        
        current_size = self.queue.getSize()             
        task = self.queue.get()
        
        
        ''' verify that size is decreased by one '''
        self.assertTrue(self.queue.getSize(),current_size-1)
            
        ''' verify that a task object is returned '''
        self.assertTrue(isinstance(task,Task))
                        
        ''' verify that task do not exist in queue '''
        self.assertFalse(self.queue.exists(task.id))


    def testGetHundred(self):        
        num = 100
                
        tasks = self.generateTasks(num)         
        for i in range(num):
            self.queue.add(tasks[i])
         
        list = []        
        def getFromq():
            list.append(self.queue.get())
            
        
        for i  in range(0,num):
            Thread(target=getFromq,args=()).start()
                
        #create a barrier so this does not get started unless all threads are finished        
        self.assertEquals(self.queue.getSize(),0)
        # make sure that no two tasjs are indentical in the list
        
        
    def testGetEmptyQueue(self):
        self.assertEquals(self.queue.getSize(),0)
        self.assertFalse(self.queue.get())        
  
      
    def generateTasks(self,num):
        list = []        
        for i in range(num):
            task = Task()
            task.id = i
            task.priority = random.randint(Queue.PRIO_LOW_BOUND,Queue.PRIO_HIGH_BOUND)
            list.append(task)

             
                
        return list
        
  
            
            
        
