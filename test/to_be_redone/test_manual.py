#!/usr/bin/env python

#help scripts for manual testing of things




from test.functional.utils import *
import unittest

class ManualTest(unittest.TestCase):

    def setUp(self):
        print "iman"
        ensure_no_running_servers_or_workers()
        home = os.path.expanduser("~")
        try:
            shutil.rmtree(PROJ_DIR)
        except Exception as e:
            pass #OK

        print "%s/.copernicus/test*"%home
        shutil.rmtree("%s/.copernicus"%home)

    def testStartServers(self):
        print "vid"
        servers = ["test_server_1","test_server_2"]

        unverifiedHttpsPorts = range(14807,14807+len(servers))
        verifiedHttpsPorts = range(13807,13807+len(servers))

        for i in range(0,len(servers)):
            pass
#            create_and_start_server(servers[i],
#                unverifiedPort=unverifiedHttpsPorts[i],
#                verifiedPort=verifiedHttpsPorts[i])

        print "started  servers"

