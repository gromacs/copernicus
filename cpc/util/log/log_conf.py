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

from cpc.util.conf.server_conf import ServerConf


class LogConf():

    def __init__(self):
       logConfFile = LogConf.getLogConfFile()
       file=open(logConfFile,"r")
       config = json.load(file)
       self.whitelist = config['includes']
       self.blacklist = config['excludes']


    def getWhitelist(self):
        return self.whitelist

    def getBlacklist(self):
        return self.blacklist



    @staticmethod
    def getLogConfFile():
        return  "%s/logging.conf"%ServerConf().getConfDir()

    @staticmethod
    def getDefaultConfigString():
        '''
            returns a string with default configurations
            used during server setup to write the first logging.conf
        '''
        conf = dict()
        conf["includes"]=["cpc"]
        conf["excludes"]=[]
        return json.dumps(conf,indent=4)


