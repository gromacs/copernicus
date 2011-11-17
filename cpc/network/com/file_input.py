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


import mmap
from cpc.network.com.input import Input

class FileInput(Input):
    '''
    classdocs
    '''


    def __init__(self,name,filename,file):
        self.name = name       
        file.seek(0)
        self.file = file                
        self.value =  mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ)
        self.filename = filename
        
        
        
#TODO destructor that closes the files i.e removes the temporary files
        
