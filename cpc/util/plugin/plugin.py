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


import os
import subprocess
import stat
import logging
import threading
log=logging.getLogger('cpc.plugin')
import plugininfo
import cpc.util

class PluginError(cpc.util.CpcError):
    pass

class Plugin:
    """General plugin class. Contains utility methods for calling plugins.
       Each instance is thread safe."""
    def __init__(self, type, name,conf,specificLocation=None):
        """Initialize with a plugin type (controller/task/runner) and name.
           If the plugin has a specific location, it will use that instead
           of searching the plugin path."""
        self.type=type
        self.name=name
        self.lock=threading.Lock()
        self.info=None
        self.specificLocation=specificLocation
        self.conf = conf
    def getType(self):
        """Get the plugin type."""
        return self.type
    def getName(self):
        """Get the plugin name."""
        return self.name

    def canRun(self):
        """Return whether the plugin can run, based on information returned
           from it. If not, it throws an exception."""        
        if self.info is None:            
            self._runInfo()
        if not self.info.OK:            
            raise PluginError("Can't run %s plugin %s: %s"%(self.type, 
                                                            self.name,
                                                            self.info.errMsg))
        return self.info.OK

    def getInfoType(self):
        """Return the plugin type according to the info command."""
        if self.info is None:
            self._runInfo()
        return self.info.type
    def getInfoName(self):
        """Return the plugin name according to the info command."""
        if self.info is None:
            self._runInfo()
        return self.info.name
    def getInfo(self):
        """Return the plugin info."""
        if self.info is None:
            self._runInfo()
        return self.info
    def _runInfo(self):
        """Get info about a plugin by calling its 'info' command."""        
        self.info=plugininfo.PluginInfo(self)
        

    def _callNoWait(self, dir, cmd, args, sendFile=None):
        """Run the plugin, in directory dir, with argument args, and optional
           send file. Returns the subprocess.Proc object associated with 
           the process which might still be running."""
        # check whether the directory exists
        st=os.stat(dir)
        if (st.st_mode & stat.S_IFDIR) == 0:
            raise PluginError("Plugin run directory %s does not exist"%dir)
                
        # get the plugin path
        procbasepaths=self.conf.getPluginPaths()
        # construct full argument list
                
        nargs = [ None, self.conf.getModuleBasePath(), cmd ]
        nargs.extend(args)
        success=False
        if sendFile is not None:
            stdinf=open(sendFile,"r")
        else:
            stdinf=subprocess.PIPE
        # construct a new path with possible executable names appended
        procbasenames=[]        
        if not self.specificLocation:
            for pdir in procbasepaths:
                # append each path item twice: once with the name as the 
                # executable name, and once with 'plugin' as the executable 
                # name in the directory of the same name. 
                # That allows plugin writers to either use a single file or 
                # a directory with multiple files
                procbasenames.append(os.path.join(pdir, self.type, self.name))
                procbasenames.append(os.path.join(pdir, self.type, self.name,
                                                 "plugin"))
        else:
            procbasenames.append(self.specificLocation)
            procbasenames.append(os.path.join(self.specificLocation, "plugin"))
        for pname in procbasenames:
            # try each item in the name list            
            try:
                # we have to add the conditional here
                # because python won't clean up the pipes 
                # that are left open if it fails..                             
                if (not os.path.isdir(pname)) and os.access(pname, os.X_OK):
                    nargs[0] = pname
                    proc=subprocess.Popen(nargs,
                                          stdin=stdinf,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,
                                          cwd=dir,
                                          close_fds=True)
                    success=True                    
                    break
            except OSError as e:                
                log.debug("Tried path %s: %s"%(pname, e.__repr__()))
             
                                  
        if not success:
            raise PluginError("Plugin %s not found"%self.name)
        return proc
   

    def call(self, dir, cmd, args, sendString=None, sendFile=None):
        """Run the plugin, in directory dir, with argument args, and optional
           send string or send file. Returns a tuple with the plugin 
           return code and its output. Note that sendString and sendFile
           cannot both be set."""        
        if (sendString is not None) and (sendFile is not None):
            raise PluginError("sendString and sendFile both set")
        proc=self._callNoWait(dir, cmd, args, sendFile=sendFile)        
        #if sendString is not None:
        #    proc.stdin.write(sendString)
        #proc.stdin.close()
        # TODO: we shouldn't read into memory uncondionally
        retst=proc.communicate(sendString)[0]
        #retst=proc.stdout.read()
        proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stdin is not None:
            proc.stdin.close()
        if proc.stderr is not None:
            proc.stderr.close()
        return ( proc.returncode, retst )
   

#class ControllerPlugin(Plugin):
#    """Controller plugin. 
#       This is the plugin that interprets results and schedules new tasks"""
#    def __init__(self, name):
#        Plugin.__init__(self, "controller", name)
#  
#    def run(self, dir, plog, cmd, sendString=None):
#        plog.info("Calling controller with command '%s'"%cmd)
#        if sendString is not None:
#            plog.debug("Sending string: %s"%sendString)
#        ret=self.call(dir, cmd, [], sendString=sendString)
#        plog.debug("Controller returned: %s"%ret[1])
#        return ret

#class TaskPlugin(Plugin):
#    """Task plugin type.
#       This plugin type interprets raw run output and arranges them into tasks.
#       It emits new commands to run"""
#    def __init__(self, name):
#        Plugin.__init__(self, "task", name)
#
#    def run(self, projectBasedir, dir, taskxml):
#        fulldir=os.path.join(projectBasedir,dir) #task.getDir())
#        #self.name=type
#        return self.call(fulldir, "process", [], sendString=taskxml)

class PlatformPlugin(Plugin):
    """Platform plugin.
       Platform plugins report on the specific platform's resources and 
       capabilities. The also reserve resources for runs when neccesary"""
    def __init__(self, name, runDir,conf):
        
        Plugin.__init__(self, "platform", name,conf)
        self.runDir=runDir
    
    def run(self, dir, cmd, plugin_args, sendString=None):
        #args=[cmd]
        #args=copy.copy(plugin_args)
        #args.extend(['--run-dir', self.runDir])
        log.debug("Sending platform plugin %s"%sendString)
        ret=self.call(dir, cmd, plugin_args, sendString=sendString)
        return ret


class ExecutablePlugin(Plugin):
    """Executable plugin type. Always called with specificLocation.
       Returns the location of executable binaries and how to invoke them."""
    def __init__(self, location,conf):
        Plugin.__init__(self, "executable", "",conf, specificLocation=location)

    def run(self, dir, platform):
        args=[platform]
        return self.call(dir, "executable", args)


