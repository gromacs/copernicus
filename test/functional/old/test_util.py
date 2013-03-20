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

from genericpath import isdir
import os
import shutil
import subprocess
from cpc.util import cmd_line_utils
from cpc.util.conf.server_conf import ServerConf
from cpc.util.openssl import OpenSSL

class TestUtil():

    def __init__(self):
        self.serverConfs = []
        self.baseFolder = os.path.join(os.environ["HOME"], ".cpc","test")

    #resets the configuration test folder
    def init(self):
        self.testConfPath = self.baseFolder
        if isdir(self.testConfPath):
            shutil.rmtree(self.testConfPath)


        self.serverConfs = dict()
        os.makedirs(self.testConfPath)



    def initServers(self,num):
        '''
        Server init == creating serverConfs
        '''
        for i in range(num):
            self.__createConfFolder(num)
            #initiate a server setup here perhaps


    def startupServers(self):
        '''
        Starts upp all initiated servers
        '''
        for conf in self.serverConfs.itervalues():
            self.__startServer(conf)


    def shutDownServers(self):
        for conf in self.serverConfs.itervalues():
            args = ['../../../cpc-server','-c',conf,'stop']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown
            print ' '.join(args)
            subprocess.call(args)

    def __createConfFolder(self,name):
        path = os.path.join(self.baseFolder,str(name))
        os.makedirs(path)
        self.serverConfs[name] = path
        cmd_line_utils.initiateServerSetup(os.path.join(path,"projects"),str(name),path)

    def __startServer(self,serverConf):
        cmdLine= "../../../cpc-server"

        args = [cmdLine,'-c',serverConf,'start']  #doing cpc.server.server.forkAndRun(cf, debug ) directly here will will for some strange reason mess up things when shutting down, the process wont shutdown
        print ' '.join(args)
        subprocess.call(args)