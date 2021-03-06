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
        purge_client_config()
        ensure_no_running_servers_or_workers()
        clear_dirs()
        setup_server()
        start_server()

    def tearDown(self):
        teardown_server()

    def test_ServerSetup_and_login(self):
        """
        Sets up and tears down a server and login
        """
        run_client_command("server-info", returnZero=False)
        login_client()
        run_client_command("server-info",expectstdout="Server id\s*:\s*(.*)")

    def test_project_start(self):
        """
        Creates, changes into, and removes projects
        """
        login_client()
        run_client_command("cd noexist", returnZero=False)
        run_client_command("start test")
        run_client_command("cd test", expectstdout='Changed to project: test')
        run_client_command("start test2")
        run_client_command("cd test2")
        run_client_command("rm test")

    def test_simple_permissions(self):
        """
        Tests that a user can't access anothers project
        """
        add_user('dev', 'dev')
        add_user('foo', 'foo')
        login_client('dev', 'dev')
        run_client_command("start test")
        login_client('foo', 'foo')
        run_client_command("cd test", returnZero=False)
        login_client('dev', 'dev')
        run_client_command("cd test")

    def test_grant_access(self):
        """
        Tests granting access to another user
        """
        add_user('dev', 'dev')
        add_user('foo', 'foo')
        login_client('dev', 'dev')
        run_client_command("start test")
        login_client('foo', 'foo')
        run_client_command("cd test", returnZero=False)
        login_client('dev', 'dev')
        run_client_command("cd test")
        run_client_command("grant-access foo")
        login_client('foo', 'foo')
        run_client_command("cd test")


    def test__simple_save_load(self):
        """
        Tests that project save / load works
        """
        login_client()
        run_client_command("start test")
        run_client_command("save test")
        run_client_command("load test.tar.gz test2")

    def test_status_one_project(self):
        """
        Tests status command with one functioning project
        """
        login_client()
        run_mdrun_example()
        run_client_command("s", expectstdout="2 in state 'active'")

    def test_status_one_faulty_project(self):
        """
        Tests status command with one faulty project
        """
        login_client()
        run_mdrun_example()
        #break mdrun
        run_client_command("set-file grompp:in.conf examples/mdrun-test/grompp.mdp")
        retry_client_command("s", expectstdout="1 in state 'error'", iterations=15, sleep=1)

    def test_get_error(self):
        """
        Tests get error command
        """
        login_client()
        run_mdrun_example()
        #break mdrun
        run_client_command("set-file grompp:in.conf examples/mdrun-test/grompp.mdp")
        retry_client_command("s", expectstdout="1 in state 'error'", iterations=15, sleep=1)
        run_client_command("get grompp.msg.error", expectstdout='File input/output error')

    def test_add_server(self):
        """
        Tests the add-server command
        """
        purge_client_config()
        try:
            login_client()
            assert False,"Login passed with no client conf"
        except AssertionError:
            pass #should fail

        run_client_command("add-server localhost")
        login_client()

        run_client_command("add-server localhost",returnZero=False,
            expectstderr="A server with name localhost already exist")

    def test_use_server(self):
        """
        Tests the use-server command
        """
        run_client_command("add-server -n failserver failhost")
        try:
            login_client()
            assert False,"Login passed with invalid server"
        except AssertionError:
            pass #should fail
        run_client_command("use-server localhost")
        login_client()

    def test_use_bundle(self):
        """
        Test connection using bundle, bypassing login procedure
        """
        purge_client_config()
        generate_bundle()
        run_client_command("users",useCnx=True)
