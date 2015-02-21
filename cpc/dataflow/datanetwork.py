import threading
from function import Function, FunctionPrototype

class DataNetwork(object):

    def __init__(self, project=None, name=None, taskQueue=None, dirName="",
                 lock=None):

        self.project = project
        self.name = name
        self.taskQueue = taskQueue
        self.dirName = dirName
        self.lock = lock or threading.RLock()
        self.instances = {}

    def addInstance(self, instance):

        assert isinstance(instance, Function)
        with self.lock:
            name = instance.name

            self.instances[name] = instance

    def newInstance(self, prototype, name):

        pr = prototype()

        assert isinstance(pr, FunctionPrototype), "The function prototype of the function must be of class FunctionPrototype."

        with self.lock:
            f = Function(pr, name, self)

            self.instances[name] = f

            return f

    def getInstanceNameList(self):

        with self.lock:
            return self.instances.keys()

    def getInstanceList(self):

        with self.lock:
            return self.instances.values()

    def getInstance(self, name):

        with self.lock:
            i = self.instances.get(name)
            return i

    def activateAll():

        with self.lock:
            for i in self.instances.values():
                i.unfreeze()

    def deactivateAll():

        with self.lock:
            for i in self.instances.values():
                i.freeze()
