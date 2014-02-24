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



import logging
import json


log=logging.getLogger(__name__)

import cpc.util
import run
import cpc.command



class ResourceList:
    """A list of resources."""
    def __init__(self):
        self.rsrc=dict()
    def set(self, name, value):
        """Set a specific value."""
        self.rsrc[name]=value
    def get(self, name):
        """Get a value with a specific name."""
        return self.rsrc.get(name)
    def getValue(self):
        """Return a Value object with all settings."""
        retDict=dict()
        for name, item in self.rsrc.iteritems():
            retDict[name] = run.IntValue(item)
        return run.DictValue(retDict)

    def iteritems(self):
        return self.rsrc.iteritems()

    def empty(self):
        return len(self.rsrc) == 0

class Resources:
    """Class describing minimum, maximum, and optimal command resources.
       For use in functions that have min/max/optimal resources."""
    def __init__(self, inputValue=None):
        self.min=ResourceList()
        self.max=ResourceList()
        self.workers=dict()
        if inputValue is not None:
            self.getInputValue(inputValue)

    def getInputValue(self, inputValue):
        # read in min values
        for name, item in inputValue.value["min"].value.iteritems():
            self.min.set(name, int(item.value))

        # read in max values
        for name, item in inputValue.value["max"].value.iteritems():
            self.max.set(name, int(item.value))

        # read worker items
        for workerName, worker in inputValue.value["workers"].value.iteritems():
            if workerName not in self.workers:
                self.workers[workerName]=ResourceList()
            for name, item in worker.value.iteritems():
                self.workers[workerName].set(name, int(item))

    def setOutputValue(self):
        """Create a Value object based on the settings in this object."""
        workerDict=dict()
        for workerName, item in self.workers:
            workerDict[workerName] = item.getValue()
        return run.RecordValue( { "min": self.min.getValue(), 
                                  "max": self.max.getValue(),
                                  "workers": run.DictValue(workerDict) } )

    def updateCmd(self, cmd):
        """Set the command's resources from an input value."""
        for name, item in self.min.iteritems():
           cmd.addMinRequired(cpc.command.Resource(name, item))
        for name, item in self.max.iteritems():
           cmd.addMaxAllowed(cpc.command.Resource(name, item))

    def save(self,filename):
        svf=dict()
        svf['min']=self.min.rsrc
        svf['max']=self.max.rsrc
        wrkrs=dict()
        for name, w in self.workers.iteritems():
            wrkrs[name] = w.rsrc
        svf['workers']=wrkrs
        fout=open(filename, 'w')
        fout.write(json.dumps(svf))
        fout.write('\n')
        fout.close()

    def load(self, filename):
        fin=open(filename, 'r')
        svf=json.loads(fin.read())
        fin.close()
        for name, value in svf['min'].iteritems():
            self.min.set(name, int(value))
        for name, value in svf['max'].iteritems():
            self.max.set(name, int(value))
        for name, w in svf['workers'].iteritems():
            if name not in self.workers:
                self.workers[name] = ResourceList()
            for itemname, value in w:
                self.workers[name].set(itemname, int(value))


