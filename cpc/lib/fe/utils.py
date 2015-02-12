#!/usr/bin/env python

# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2014, Sander Pronk, Iman Pouya, Magnus Lundborg Erik Lindahl,
# and others.
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

def findClosest(path_lambdas, lam):
    """Find the index of the closest lambda value."""
    mindif=2
    mini=-1
    i=0
    for plam in path_lambdas:
        dif=(plam-lam)*(plam-lam) #math.fabs(plam-lam)
        if dif < mindif:
            mini=i
            mindif=dif
        i+=1
    return mini

