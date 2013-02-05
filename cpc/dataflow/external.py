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
import os

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import subprocess

import cpc.util
import apperror
import function
import run
import atomic


log=logging.getLogger('cpc.dataflow.external')

class ExternalFunctionError(apperror.ApplicationError):
    pass

class ExternalFunction(atomic.AtomicFunction):
    """A function that has a controller that is an external command that
       can be called directly. The communication happens through XML 
       to stdin, and reading XML from stdout."""
    def __init__(self, name, lib=None, controllerExec=None, basedir=None):
        """Initializes the function.
        """
        atomic.AtomicFunction.__init__(self, name, lib)
        self.controllerExec=controllerExec
        self.basedir=basedir
        if self.controllerExec is not None:
            self._checkControllerPath()
        self.outputDirWithoutFiles=True
        self._checkOutputDirNeeded()

    def writeXML(self, outFile, indent=0):
        """The function itself does not need to be described."""
        indstr=cpc.util.indStr*indent
        iindstr=cpc.util.indStr*(indent+1)
        outFile.write('%s<function id="%s" type="external">\n'%
                      (indstr, self.name))
        self._writeInputOutputXML(outFile, indent+1)
        outFile.write('%s<controller executable="%s"/>\n'%
                      (iindstr, self.controllerExec))
        outFile.write('%s</function>\n'%indstr)

    def setExecutable(self, controllerExec):
        """Set the controller executable for this function."""
        self.controllerExec=controllerExec
        self._checkControllerPath()

    def _checkControllerPath(self):
        if self.controllerExec is not None:
            if os.path.isabs(self.controllerExec):
                self.fullpath=self.controllerExec
            else:
                self.fullpath=os.path.join(self.basedir, self.controllerExec)
            if not os.path.exists(self.fullpath):
                raise ExternalFunctionError("Couldn't find controller %s"%
                                            self.fullpath)

    def check(self):
        """Perform a check on whether the function can run and set
           the state to reflect this. In this case, run the function 
           without inputs, and check whether the externa command runs with
           return code 0."""
        inp=run.FunctionRunInput()
        returncode, retstdout, retstderr=self._run(inp)
        if returncode != 0:
            self.stateMsg="%s, %s"%(retstdout, retstderr)
            self.state=function.Function.error
            log.error("Can't run function %s: %s, %s"%(self.name, 
                                                       retstdout, 
                                                       retstderr))
        else:
            self.stateMsg=""
            self.state=function.Function.ok


    def _run(self, inp):
        """run this function"""
        # construct the XML input
        outs=StringIO()
        inp.writeRunXML(outs,0)

        # check whether the run dir exists
        if inp.outputDir is not None:
            if not os.path.isdir(inp.getOutputDir()):
                raise ExternalFunctionError(
                                    "Output directory %s does not exist"%
                                    inp.getOutputDir())
        # construct full argument list
        nargs=[ self.fullpath ]

        log.log(cpc.util.log.TRACE,outs.getvalue())

        proc=subprocess.Popen(nargs,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd=inp.getOutputDir(),
                              close_fds=True)

        retst=proc.communicate(outs.getvalue())
        outs.close()
        return proc.returncode, retst[0], retst[1]

    def run(self, inp):
        # run
        returncode, retstdout, retstderr=self._run(inp)

        if inp.activeInstance is not None:
            logout=inp.activeInstance.getLog()
            if logout is not None:
                outf=logout.open()
                outf.write(retstderr)
                logout.close()
        # and process its output
        if returncode != 0:
            raise ExternalFunctionError("Error in %s: %s, %s"% 
                                        (self.name, 
                                         unicode(retstdout, errors='replace'), 
                                         unicode(retstderr, errors='replace')))
        #reader=run.IOReader(False)
        out=inp.getFunctionOutput()
        reader=run.IOReader(None, out)
        #log.debug(retst)
        instrio=StringIO(retstdout)
        log.debug("Reading output for function %s: %s"%(self.name, 
                                                        instrio.read()))
        instrio.reset()
        reader.read(instrio, self.fullpath)
        return out

