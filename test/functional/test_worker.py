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


from test.functional.utils import *
import time
class TestWorker():

    def setUp(self):
        setup_server()
        generate_bundle()
        start_server()

    def tearDown(self):
        teardown_server()

    def testWorker(self):
        """
        Verifies that a worker connects to the server
        """
        w = Worker()
        w.startWorker()
        w.waitForOutput(expectedOutput='Got 0 commands.')
        w.shutdownGracefully()
        w.waitForOutput(expectedOutput='Received shutdown signal.')

        w.checkForExceptions()
