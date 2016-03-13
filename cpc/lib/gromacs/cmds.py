# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2015, Sander Pronk, Iman Pouya, Peter Kasson, Erik Lindahl,
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


import logging

log = logging.getLogger(__name__)

import cpc.util

class GromacsCommands(object):
    def __init__(self):
        try:
            cpc.util.plugin.testCommand("grompp -version")
            self.mdrun = "mdrun"
            self.grompp = "grompp"
            self.eneconv = "eneconv"
            self.energy = "energy"
            self.trjconv = "trjconv"
            self.trjcat = "trjcat"
            self.gmxdump = "gmxdump"
            self.pdb2gmx = "pdb2gmx"
            self.bar = "g_bar"
            self.editconf = "editconf"
            self.gmxcheck = "gmxcheck"
            self.rama = "g_rama"
        except cpc.util.CpcError as _unused_e:
            cpc.util.plugin.testCommand("gmx -version")
            self.mdrun = "gmx mdrun"
            self.grompp = "gmx grompp"
            self.eneconv = "gmx eneconv"
            self.energy = "gmx energy"
            self.trjconv = "gmx trjconv"
            self.trjcat = "gmx trjcat"
            self.gmxdump = "gmx dump"
            self.pdb2gmx = "gmx pdb2gmx"
            self.bar = "gmx bar"
            self.editconf = "gmx editconf"
            self.gmxcheck = "gmx check"
            self.rama = "gmx rama"
        return
