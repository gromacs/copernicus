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
class TestLifeCycle():

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testGracefulKill(self):
        """
        Verifies that commands are put back on graceful worker kill
        """
        #long hearbeat, we want the worker to signal to the server that it's
        #terminating
        setup_server(heartbeat='120')
        start_server()
        login_client()
        #load mdrun example project
        run_mdrun_example()
        #time.sleep(3)

        #verify the command is queued
        retry_client_command(command='q', expectstdout='mdrun.1', iterations=30)
        #fire up the worker
        w = Worker()
        w.startWorker()
        w.waitForOutput(expectedOutput='Got 1 commands.')

        w.waitForOutput(expectedOutput='Run thread with cmd')
        time.sleep(1)

        #gracefully stop the worker
        w.shutdownGracefully()
        w.waitForOutput(expectedOutput='Received shutdown signal')
        #ensure that the command is back into the queue
        retry_client_command(command='q', expectstdout='Queued', iterations=10)

        #check that nothing went wrong
        w.checkForExceptions()
        teardown_server()

    def testHardKill(self):
        """
        Verifies that commands are put back on hard worker kill
        """
        #short heartbeat
        setup_server(heartbeat='2')
        start_server()
        time.sleep(1) #let's cut it some slack
        login_client()
        #load mdrun example project
        run_mdrun_example()

        retry_client_command(command='q', expectstdout='mdrun.1', iterations=30)
        #fire up the worker
        w = Worker()
        w.startWorker()
        w.waitForOutput(expectedOutput='Got 1 commands.')

        w.waitForOutput(expectedOutput='Run thread with cmd')
        time.sleep(1)

        #gracefully stop the worker
        w.shutdownHard()
        #ensure that the command is back into the queue
        retry_client_command(command='q', expectstdout='Queued', iterations=10)

        #check that nothing went wrong
        w.checkForExceptions()
        teardown_server()

    def testRestartServer(self):
        """
        Verifies commands are put back on queue on server restart
        """
        setup_server(heartbeat='120')
        start_server()
        login_client()
        #load mdrun example project
        run_mdrun_example()
        #time.sleep(3)

        #verify the command is queued
        retry_client_command(command='q', expectstdout='mdrun.1', iterations=30)

        #soft stop server and start server
        stop_server()
        time.sleep(1) #let's cut it some slack
        start_server()

        login_client()
        #ensure that the command is back into the queue
        retry_client_command(command='q', expectstdout='Queued', iterations=10)

        teardown_server()

    def testQueueIntactAfterRestart(self):
        """
        Makes sure items in queue remain there after restart
        """
        #short heartbeat
        setup_server(heartbeat='120')
        start_server()
        time.sleep(1) #let's cut it some slack
        login_client()
        #load mdrun example project
        run_mdrun_example()

        retry_client_command(command='q', expectstdout='mdrun.1', iterations=30)
        #fire up the worker
        w = Worker()
        w.startWorker()
        w.waitForOutput(expectedOutput='Got 1 commands.')

        w.waitForOutput(expectedOutput='Run thread with cmd')
        stop_server()
        time.sleep(0.2)
        w.shutdownHard()
        time.sleep(1) #let's cut it some slack
        start_server()

        login_client()

        #ensure that the command is back into the queue
        retry_client_command(command='q', expectstdout='Queued', iterations=10)

        teardown_server()