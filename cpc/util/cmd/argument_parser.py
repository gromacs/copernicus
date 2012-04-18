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
from cpc.util.cmd.flag import Flag

class ArgumentParser(object):

    def __init__(self):
        self.flags = []
        self.subCommands = []


    def add_flag(self,name,type,nargs=0,help=None,default=None,switch=True,alias=[]):
        self.flags.append(Flag(name=name,type=type,nargs=nargs,help=help,default=default,switch=switch,alias=alias))
        #TODO if the flag is conflicting with an alias or another flag throw an conflictingCommandException


    def add_subCommand(self,argumentParser):
        #TODO check for conflicting subcommmands
        #TODO we probably need aliases here too
        self.subCommands.append(argumentParser)

        pass

    def print_usage(self):
        pass

    def print_help(self):
        #for reach subcommand print out the subcommand name and its help
        #make sure the formatting looks nice
        pass

    def parse(self):
        #TODO check for flags or subcommands that is a must!
        pass
