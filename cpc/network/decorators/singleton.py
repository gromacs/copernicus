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



'''
Created on Jul 19, 2011

@author: iman
'''
#decorator class
class Singleton(object):

    def __init__(self,cls):
        self.instances = {}
        self.cls = cls
        print "IMAN initializing singleton"
    def __call__(self,*args, **kw):
        print "IMAN doing call in singleton "
        if self.cls not in self.instances:
            self.instances[self.cls] = self.cls(*args,**kw)
        return self.instances[self.cls]

