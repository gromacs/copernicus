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
import os
import re
import socket
import subprocess
import cpc.util.json_serializer

from cpc.test.functional.test_util import TestUtil

__author__ = 'iman'

import unittest

class ServerTest(unittest.TestCase):
    '''
    This set consists of command line calls being performed as one runs the code from the command line
    Suitable when one wants to speed up manual testing
    '''
    def setUp(self):
        self.util = TestUtil()
        self.util.init()

    def test_setup(self):
        self.util.initServers(1)
        #TODO this should do a command line call!!


    def test_createConnectionBundle(self):
        #do a command line call
        #ensure that no errors is output
        self.util.initServers(1)  #TODO change with cpc-server setup
        args = ['../../../cpc-server','-c',self.util.serverConfs[1],'create-connection-bundle']
        print  " ".join(args)
        process = subprocess.Popen(args,stdout=subprocess.PIPE)

        ret = process.communicate()

        bundleData = json.loads(ret[0],object_hook = cpc.util.json_serializer.fromJson)

        self.assertNotEquals(bundleData['client_https_port'],None)
        self.assertNotEquals(bundleData['client_https_port'],'')

        self.assertNotEquals(bundleData['client_http_port'],None)
        self.assertNotEquals(bundleData['client_http_port'],'')

        self.assertNotEquals(bundleData['ca_cert'],None)
        self.assertNotEquals(bundleData['ca_cert'],'')

        self.assertNotEquals(bundleData['cert'],None)
        self.assertNotEquals(bundleData['cert'],'')

        self.assertNotEquals(bundleData['private_key'],None)
        self.assertNotEquals(bundleData['private_key'],'')



    def test_server(self):
        '''
        Starts up one server, then starts up a server and tries to connect to the server.
        '''
        self.util.initServers(1)
        #create a connection bundle save it in the test dir
        args = ['../../../cpc-server','-c',self.util.serverConfs[1],'create-connection-bundle']
        print  " ".join(args)
        process = subprocess.Popen(args,stdout=subprocess.PIPE)

        ret = process.communicate()

        bundleFile = os.path.join(self.util.baseFolder,"bundle.txt")
        file = open(bundleFile,"w")
        file.write(ret[0])
        file.close()

        self.util.startupServers()

        args = ['../../../cpcc','-c',bundleFile,'stop-server']
        print " ".join(args)
        subprocess.call(args)


    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
