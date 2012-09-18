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

import cpc.util

class RunningCmdListError(cpc.util.CpcError):
    def __init__(self, cmdID):
        self.str="Command %s not found"%cmdID

class RunningCmdList(object):
    """Maintains a list of all running commands owned by this server."""
    def __init__(self):
        """Initialize the object with an empty list."""
        self.cmds=dict()
        self.lock=threading.Lock()

    def get(self, id):
        """Get a specific command, or throw a RunningCmdListError if the 
           command is not found.
           id = the command ID to get.
           returns a command object."""
        with self.lock:
            try:
                return self.cmds[id]
            except KeyError:
                raise RunningCmdListError(id)

    def add(self, cmd, location):
        """Add a command to the list."""
        with self.lock:
            if self.cmds.has_key(cmd.id):
                raise cpc.util.CpcError("Duplicate command ID")
            self.cmds[cmd.id] = cmd
            cmd.setRunning(True, location)
            
    def remove(self, cmd):
        """Remove a command from the list, or throw a RunningCmdListError
           if no such command.
           cmd = a command object to remove."""
        with self.lock:
            if cmd.id not in self.cmds:
                raise RunningCmdListError(cmd.id)
            del self.cmds[cmd.id]

    def handleFinished(self, cmd):
        """Handle a finished command (successful or otherwise), with optional
           runfile
           cmd = the command to remove
           runfile = None or a file handle to the tarfile containing run data
           """
        with self.lock:
            if cmd.id not in self.cmds:
                raise RunningCmdListError(cmd.id)
            del self.cmds[cmd.id]
            #FIXME persistance part
            #project.writeTasks()

    def list(self):
        """Return a list with all running items."""
        ret=[]
        with self.lock:
            for value in self.cmds.itervalues():
                ret.append(value)
        return ret

