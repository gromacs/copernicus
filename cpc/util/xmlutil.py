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




import cpc.util

specNamespace="http://www.gromacs.org/copernicus/project"

mdpNamespace="http://www.gromacs.org/mdp"

# indent string
indStr="  "


def getBooleanAttribute(attrs, name):
    """Get an attribute value that is boolean. Its value can either be
       "1", "true", "yes" for True or "0", "false", "no" or absent for False.
       attrs = the attributes list from startElement()
       name = the attribute name to check.
       returns: the boolean value of the attribute."""
    if not attrs.has_key(name):
        return False # if it isn't there, it's false.
    val=attrs.getValue(name).lower()
    if val=="1" or val=="yes" or val=="true":
        return True
    elif val=="0" or val=="no" or val=="false":
        return False
    raise cpc.util.CpcError("Attribute %s with value '%s' neither true nor false"%(name, val))


