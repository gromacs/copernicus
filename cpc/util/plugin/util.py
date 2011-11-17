# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This file is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301   
# USA 


import shlex
import subprocess

import cpc.util

def testCommand(command):
    """Try to run the command to see whether the executable works. 
       Returns True if the command executes successfuly, or throws
       an exception if it doesn't."""
    success=False
    sp=shlex.split(command)
    try:
        proc=subprocess.Popen(sp,
                              stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, 
                              close_fds=True)
        (stdout, stderr)=proc.communicate()
        success= (proc.returncode == 0)
        if not success:
            raise cpc.util.CpcError("Couldn't run %s: %s"%(sp[0],stderr))
    except OSError as e:
        raise cpc.util.CpcError("Couldn't run %s: %s"%(sp[0], str(e)))
    return success

