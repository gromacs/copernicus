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
import tarfile
import logging

import exception

log=logging.getLogger("cpc.util.file")


class TarfileError(exception.CpcError):
    pass

def extractSafely(destdir, filename=None, fileobj=None):
    
    try:
        if filename is not None:
            tf=tarfile.open(filename, mode='r:gz')
        else:
            tf=tarfile.open(fileobj=fileobj, mode='r:gz')
        files=tf.getmembers()
             
        nfiles=[]
        for file in files:            
            if not os.path.isabs(file.name) and not \
                      os.path.normpath(file.name).startswith(".."): 
                nfiles.append(file)
        tf.extractall(destdir, nfiles)
        tf.close()
    except OSError as e:
        raise TarfileError("%s: %s"%(destdir, e.strerror))
    except tarfile.TarError:
        raise TarfileError("Couldnt read tar.gz file")
    finally:
        del(tf)


def backupFile(filename, Nmax=4):
    for i in range(Nmax-1,-1,-1):
        if i>1:
            origname="%s.bak.%02d"%(filename,i)
        elif i==1:
            origname="%s.bak"%(filename)
        else:
            origname="%s"%(filename)

        if os.path.exists(origname):
            if i>0:
                backupname="%s.bak.%02d"%(filename,i+1)
            else:
                backupname="%s.bak"%(filename)
            try:
                #log.debug("Renaming %s to %s"%(origname, backupname))
                os.rename(origname, backupname)
            except OSError:
                try:
                    # in windows, renaming on top of an existing file generates
                    # an exception
                    os.remove(backupname)
                    os.rename(origname, backupname)
                except OSError:
                    pass


