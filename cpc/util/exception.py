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




class CpcError(Exception):
    """The base copernicus exception class.""" 
    def __init__(self, str):
        self.str=str
    def __str__(self):
        return self.str


class CpcXMLError(CpcError):
    """Base Copernicus XML exception class."""
    def __init__(self, msg, locator):
        self.str = "line %d, column %d: %s"%(locator.getLineNumber(), \
                                             locator.getColumnNumber(), msg)

