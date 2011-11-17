'''
Created on Jul 19, 2011

@author: iman
'''
import unittest
from cpc.network.decorators.singleton import Singleton

class TestSingleton(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testSameInstance(self):
        self.assertEquals(10,Foo().x)
        Foo().x = 20
        self.assertEquals(20, Foo().x)



@Singleton
class Foo():
    def __init__(self):
        self.x = 10

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()