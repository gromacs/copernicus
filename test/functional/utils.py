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


import os
import subprocess
import sys
import threading
import signal
import shutil
import shlex
import Queue
import time
import re

from cpc.server.state.user_handler import *
from cpc.util.conf.conf_base import Conf

PROJ_DIR = "/tmp/cpc-proj"

def getcnxFilePath(name="_default"):
    home = os.path.expanduser("~")
    fileName = "%s/.copernicus/%s/client.cnx"%(home,name)
    return fileName

def setup_server(heartbeat='20' ,name='_default',addServer=True):

    with open(os.devnull, "w") as null:
        p = subprocess.Popen(["./cpc-server", "setup","-servername",name,
                              "-stdin",
                              PROJ_DIR],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, close_fds=True)
        (stdout, stderr) = p.communicate(input='root\n')
        assert p.returncode == 0
        p = subprocess.check_call(["./cpc-server","-c",name,
                                   "config", "hostname",
                                   "localhost"], stdout=null, stderr=null)
        p = subprocess.check_call(["./cpc-server","-c",name,
                                   "config", "server_fqdn",
                                   "localhost"], stdout=null, stderr=null)
        p = subprocess.check_call(["./cpc-server","-c",name,
                                   "config", "heartbeat_time",
                                   heartbeat], stdout=null, stderr=null)
    if addServer:
        cmd_line = './cpcc add-server localhost'
        args = shlex.split(cmd_line)
        p = subprocess.check_call(args)


def generate_bundle(name="_default"):
    #generate bundle
    cmd_line = './cpc-server -c %s bundle -o %s' %(name,getcnxFilePath(name))
    args = shlex.split(cmd_line)
    try:
        with open(os.devnull, "w") as null:
            p = subprocess.Popen(args, stdout=null, stderr=null)
            p.wait()

    except Exception as e:
        sys.stderr.write("Failed to write bundle: %s\n" % str(e))
        assert False #NOT OK

def purge_client_config():
    home = os.path.expanduser("~")
    cmd_line = 'rm %s/.copernicus/clientconfig.cfg' % home
    args = shlex.split(cmd_line)
    with open(os.devnull, "w") as null:
        subprocess.call(args, stderr=null) 

def configureServerPorts(name,unverifiedHTTPS,verifiedHTTPS):

    #set unverified https
    run_server_command("config server_unverified_https_port "
                       "%s"%unverifiedHTTPS,name)

    run_server_command("config server_verified_https_port "
                       "%s"%verifiedHTTPS,name)

def setLogToTrace(name):
    run_server_command("config mode trace ",name)

def create_and_start_server(name="_default",unverifiedPort=None,
                            verifiedPort=None):

        if (unverifiedPort==None):
            unverifiedPort = Conf.getDefaultUnverifiedHttpsPort()
        if (verifiedPort==None):
            verifiedPort = Conf.getDefaultVerifiedHttpsPort()
        setup_server(name=name,addServer=False)
        configureServerPorts(name,unverifiedPort,verifiedPort)
        setLogToTrace(name)
        generate_bundle(name)
        start_server(name)


def start_server(name="_default"):
    cmd_line = './cpc-server -c %s start'%name
    args = shlex.split(cmd_line)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()
    assert p.returncode == 0,\
    "Failed to start server. stderr:%s\nstdout%s" % (stderr, stdout)


def stop_server(name="_default",useCnx=False):
    #soft stop
    try:
        run_client_command("stop-server",expectstdout="Quitting",
            useCnx=useCnx,name=name)
    except AssertionError as a:
        print "Hard stopped server due to error %s "%a.__str__()
        #hard stop
        ensure_no_running_servers_or_workers()

def ensure_no_running_servers_or_workers():
    try:
        p = subprocess.check_call(["pkill", "-9", "-f", "./cpc-server"])
    except subprocess.CalledProcessError:
        pass #we swallow this
    try:
        p = subprocess.check_call(["pkill", "-9", "-f", "./cpc-worker"])
    except subprocess.CalledProcessError:
        pass #we swallow this


def run_mdrun_example(projname='mdrun'):
    cmd_line = 'examples/mdrun-test/rungmxtest %s' % projname
    args = shlex.split(cmd_line)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()
    if p.returncode != 0:
        assert False,\
        "Failed to setup mdrun example. stdout:\n%s\n\stderr:%s\n\n" % (
            stdout, stderr)
    time.sleep(3) #we need to give the server some time to handle the project

def add_user(user, password, userlevel=UserLevel.REGULAR_USER):
    UserHandler().addUser(user, password, userlevel)

def clear_dirs():
    home = os.path.expanduser("~")
    try:
        shutil.rmtree(PROJ_DIR)
    except Exception as e:
        pass #OK
    try:
        shutil.rmtree("%s/.copernicus"%home)
    except Exception as e:
        pass #OK


def teardown_server():
    stop_server()

def getHome():
    return os.path.expanduser("~")

def run_server_command(command,name="_default",returnZero=True,\
                                                        expectstdout=None
                                                        ,expectstderr=None):
    cmd_line = './cpc-server -c %s %s' %(name,command)
    args = shlex.split(cmd_line)
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()
    if returnZero:
        assert p.returncode == 0,\
        "Server returned nonzero when expecting zero."\
        " Command: \"%s\"\nstderr: %s\nstdout: %s" % (command, stderr, stdout)
    else:
        assert p.returncode != 0,\
        "Server returned zero when expecting nonzero."\
        " Command: \"%s\"\nstderr: %s\nstdout %s" % (command, stderr, stdout)

    if expectstdout is not None:
        assert re.search(expectstdout,stdout,re.MULTILINE)!=None,\
        "Expected '%s' in stdout, but got '%s'"%(expectstdout, stdout)

    if expectstderr is not None:
        assert expectstderr in stderr,\
        "Expected '%s' in stderr, but got '%s'" % (expectstderr, stderr)



def run_client_command(command,name="_default", returnZero=True, \
                                                       expectstdout=None,
                                                       expectstderr=None,
                                                       useCnx=False):
    if useCnx:
        cnxFlag = "-c %s"%(getcnxFilePath(name))
        cmd_line = './cpcc %s %s' %(cnxFlag,command)
    else:
        cmd_line = './cpcc %s' %(command)
    args = cmd_line.split(" ")
    p = subprocess.Popen(args, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = p.communicate()
    if returnZero:
        assert p.returncode == 0,\
        "Client returned nonzero when expecting zero."\
        " Command: \"%s\"\nstderr: %s\nstdout: %s" % (cmd_line, stderr, stdout)
    else:
        assert p.returncode != 0,\
        "Client returned zero when expecting nonzero."\
        " Command: \"%s\"\nstderr: %s\nstdout %s" % (cmd_line, stderr, stdout)

    if expectstdout is not None:
        assert re.search(expectstdout,stdout,re.MULTILINE)!=None,\
        "Expected '%s' in stdout, but got \n'%s'"%(expectstdout, stdout)

    if expectstderr is not None:
        assert re.search(expectstderr,stderr,re.MULTILINE)!=None,\
        "Expected '%s' in stderr, but got \n'%s'"%(expectstderr, stderr)



def retry_client_command(command, expectstdout, iterations=5, sleep=3):
    for attempt in xrange(iterations):
        try:
            run_client_command(command, expectstdout=expectstdout)
            return
        except AssertionError as a:
            print a.message
        time.sleep(sleep)
    assert False,\
    "Attempted to read '%s' from server,but gave up after %d " \
    "attempts" \
    % (expectstdout, iterations)

def login_client(username='root', password='root',name="_default",
                 useCnx=False):
    cnxFlag = ""
    if useCnx:
        cnxFlag = "-c %s"%(getcnxFilePath(name))

    cmd_line = './cpcc %s login -stdin %s'%(cnxFlag,username)

    for i in range(3):
        time.sleep(1) # we need to give the server some time to load
        args = shlex.split(cmd_line)
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate(input='%s\n'%password)
        if p.returncode == 0:
            break
    assert p.returncode == 0,\
        "Failed login: stdout: '%s', stderr: '%s'"%(stdout,stderr)

class Worker(object):
    def __init__(self):
        self.process = None
        self.thread = None
        self.lastline = None
        self.exception = None
        self.eguard = ExceptionCatcher()

    def startWorker(self):
        def workerThread():
            cmd_line = './cpc-worker -d smp'
            args = shlex.split(cmd_line)
            self.process = subprocess.Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, preexec_fn=os.setsid)

        self.thread = threading.Thread(
            target=self.eguard.wrap_function, args=(workerThread,))
        self.thread.start()

    def checkForExceptions(self):
        self.eguard.check()

    def shutdownGracefully(self):
        os.killpg(self.process.pid, signal.SIGINT)
        #self.process.send_signal(signal.SIGINT)

    def shutdownHard(self):
        self.process.terminate() #SIGTERM

    def waitForOutput(self, expectedOutput, timeout=15):
        def waiterThread():
            while True:
                line = self.process.stderr.readline()
                if line == '':
                    assert False,\
                    "Reach EOF while waiting for '%s', last line"\
                    "outputed was '%s'" % (expectedOutput, self.lastline)
                if expectedOutput in line:
                    break
                self.lastline = line


        #busy wait for in order to avoid race where waitForOutput is called
        #after startWorker(). Will deadlock if startWorker never is called.
        while self.process is None:
            pass
        waitThread = threading.Thread(
            target=self.eguard.wrap_function, args=(waiterThread,))
        waitThread.start()
        waitThread.join(timeout)

        if waitThread.is_alive():
            #Timed out
            self.process.terminate()
            waitThread.join()
            self.thread.join()
            assert False,\
            "Expected worker to output '%s', but timed out waiting for it,"\
            "last line outputed was '%s'" % (expectedOutput, self.lastline)

            #we got the expected output


class ExceptionCatcher(object):
    """
    Wraps thread targets as exceptions thrown in threads are not propagated
    back to the parent, leading to false positive tests
    """

    def __init__(self):
        self.queue = Queue.Queue()

    def wrap_function(self, target):
        try:
            target()
        except Exception as e:
            self.queue.put(sys.exc_info())

    def check(self):
        do_raise = not self.queue.empty()
        while not self.queue.empty():
            exc_type, exc_obj, exc_trace = self.queue.get()
            sys.stderr.write("%s\n%s" % (exc_type, exc_obj))
            import traceback

            traceback.print_tb(exc_trace)
        if do_raise:
            assert False,\
            "Threads had exception, see above"
