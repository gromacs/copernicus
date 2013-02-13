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
import traceback
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cpc.util
import apperror
import function
import run
import network_function


log=logging.getLogger('cpc.dataflow.atomic')

class AtomicFunctionError(apperror.ApplicationError):
    pass

class AtomicFunction(network_function.NetworkedFunction):
    """A function that cannot be subdivided: i.e. a function that has a 
       controller. Abstract base class for TaskFunction and FunctionFunction
       (see atomic.py). 
       
       NOTE this is really a misnomer because it has a network.."""
    def __init__(self, name, lib=None):
        """Initializes an atomic function.

           input = list of input items
           output = list of output items
        """
        network_function.NetworkedFunction.__init__(self, name, lib)
        self.genTasks=True


class SimpleFunctionFunction(AtomicFunction):
    """A function that has a controller that is a queued python function.
       The function takes its input arguments simply as function argmuents, 
       and returns a dict of output values. 
       
       If the function has an output directory, it will be set as the input
       variabale '_outputDir'."""
    def __init__(self, name, pyFunction=None, lib=None):
        """Initializes a const function.

           type = a const type
           value = its value """
        AtomicFunction.__init__(self, name, lib)
        self.pyFunction=pyFunction
        self.pyImport=None

    def setFunction(self, pyFunctionName, importName=None):
        #log.debug("Setting function %s to %s"%(pyFunctionName, self.name))
        try:
            if self.state != function.Function.error:
                if importName is not None:
                    self.pyImport=importName
                    exec "import %s"%importName
                self.pyFunction=eval(pyFunctionName)
                self.pyFunctionName=pyFunctionName
                #self.pyFunction=pyFunction
                log.debug("Set function %s to %s"%(pyFunctionName, self.name))
        except:
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            self.stateMsg=fo.getvalue()
            self.state=function.Function.error
            log.info("Error setting function %s to %s: %s"%
                     (pyFunctionName, self.name, self.stateMsg))

    def writeXML(self, outFile, indent=0):
        """The function itself does not need to be described."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outFile.write('%s<function id="%s" type="python">\n'%(indstr,self.name))
        self._writeInputOutputXML(outFile, indent+1)
        if self.pyImport is not None:
            importstr=' import="%s"'%self.pyImport
        else:
            importstr=""
        outFile.write('%s<controller function="%s" %s/>\n'%
                      (iindstr, self.pyFunction.__name__, importstr))
        outFile.write('%s</function>\n'%indstr)

    def run(self, fnInputs):
        """run this function, based on a list of input values."""
        inp=dict()
        #for name, val in fnInputs.inputs.iteritems():
        for name in fnInputs.inputs.getSubValueIterList():
            inp[str(name)] = fnInputs.inputs.getSubValue(name).value
        if fnInputs.outputDir is not None:
            inp["_outputDir"] = fnInputs.outputDir
        log.debug(str(inp))
        ret=self.pyFunction( **inp )
        fo=fnInputs.getFunctionOutput()
        for name, val in ret.iteritems():
            if isinstance(val, float):
                fo.setOut( name, run.FloatValue(val) ) 
            elif isinstance(val, int):
                fo.setOut( name, run.IntValue(val) ) 
            elif isinstance(val, string):
                fo.setOut( name, run.StringValue(val) ) 
        #return fo


class ExtendedFunctionFunction(SimpleFunctionFunction):
    """A function that has a controller that is a queued python function,
        with extended call convention.
       
        The function is called like this: 
        def f(fnInputs )
        where 
            fn is the function object, 
            fnInputs is a FunctionRunInput object
        The function returns a run.FunctionRunOutput object. """
    def __init__(self, name, pyFunction=None, lib=None):
        """Initializes a const function.

           type = a const type
           value = its value
        """
        AtomicFunction.__init__(self, name, lib)
        self.pyFunction=pyFunction

    def writeXML(self, outFile, indent=0):
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outFile.write('%s<function id="%s" type="python">\n'%(indstr, 
                                                              self.name))
        self._writeInputOutputXML(outFile, indent+1)
        if self.pyImport is not None:
            importstr=' import="%s"'%self.pyImport
        else:
            importstr=""
        outFile.write('%s<controller function="%s" %s/>\n'%
                      (iindstr, self.pyFunction.__name__, importstr))
        outFile.write('%s</function>\n'%indstr)

    def check(self):
        """check whether function can run. If it throws an exception,
           it can't"""
        inp=run.FunctionRunInput(None, None, None, None, None, self,
                                 None, None)
        try:
            ret=self.pyFunction(inp)
            self.state=function.Function.ok
            self.stateMsg=""
        except cpc.util.CpcError as e:
            self.stateMsg=str(e)
            self.state=function.Function.error
        except:
            fo=StringIO()
            traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1],
                                      sys.exc_info()[2], file=fo)
            self.stateMsg=fo.getvalue()
            self.state=function.Function.error

    def run(self, fnInputs):
        """run this function, based on a list of input values, and the run 
            directory."""
        #log.debug("Basedir=%s"%(fnInputs.getBaseDir()))
        self.pyFunction(fnInputs)
        #return self.pyFunction(fnInputs)



