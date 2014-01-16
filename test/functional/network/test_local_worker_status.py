from test.functional.utils import *

class TestLocalWorkerStatus():

    def setUp(self):
        ensure_no_running_servers_or_workers()
        clear_dirs()
        setup_server()
        generate_bundle()
        start_server()

    def tearDown(self):
        teardown_server()

    def testLocalWorkerStatusConnected(self):
        """
        Verifies that a worker connects to the server and that the server
        has updated the status to connected
        """

        #we should start with 0 connected workers
        login_client()
        run_client_command("status",expectstdout=".*connected to 0 local workers.*")
        w = Worker()
        w.startThread()
        w.waitForOutput(expectedOutput='Got 0 commands.')

        #the server should have updated the worker status by now
        run_client_command("status",expectstdout=".*connected to 1 local worker.*")

        w.shutdownGracefully()
        w.checkForExceptions()

        confDict = getConf()

        #if a worker has not sent a heartbeat it is no longer connected
        time.sleep(int(confDict['heartbeat_time']))

        #we should now again have no workers connected to this server
        run_client_command("status",expectstdout=".*connected to 0 local workers.*")
