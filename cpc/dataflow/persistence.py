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



import json

class Persistence(object):
    def __init__(self, filename):
        """Initialize a controller persistence object based on a filename."""
        self.filename=filename
        try:
            fp=open(filename,"r")
            self.dict=json.load(fp)
            fp.close()
        except IOError:
            self.dict=dict()

    def write(self):
        """Write out persistence data."""
        fp=open(self.filename,"w")
        json.dump(self.dict, fp)
        fp.close()

    def set(self, name, value):
        """Set the value of entry 'name'."""
        self.dict[name] = value
    def get(self, name):
        """Get the value of entry 'name', or None if there is no such entry."""
        if self.dict.has_key(name):
            return self.dict[name] 
        else:
            return None
    def has_key(self, name):
        """Check whether the entry with 'name' exists."""
        return self.dict.has_key(name)

    
