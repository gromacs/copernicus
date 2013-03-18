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
class TestClientTest():

    def setUp(self):
        setup_server()
        start_server()

    def tearDown(self):
        teardown_server()

    def test_ServerSetup(self):
        """
        Sets up and tears down a server
        """
        pass

    def test_project_start(self):
        """
        Creates, changes into, and removes projects
        """
        run_client_command("cd noexist", returnZero=False)
        run_client_command("start test")
        run_client_command("cd test", expectstdout='Changed to project: test')
        run_client_command("start test2")
        run_client_command("cd test2")
        run_client_command("rm test")

    def test__simple_save_load(self):
        """
        Tests that project save / load works
        """
        run_client_command("start test")
        run_client_command("save test")
        run_client_command("load test.tar.gz test2")
