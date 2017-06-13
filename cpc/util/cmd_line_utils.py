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


'''Very simple functions used by the command line tools'''
import os
import shutil
from cpc.util.conf import conf_base, server_conf
from cpc.util.conf.connection_bundle import ConnectionBundle
import cpc.util.openssl
import sys
import textwrap

from cpc.util.conf.conf_base import Conf
from cpc.util.conf.conf_base import NoConfError, ConfError
import cpc.util.conf.server_conf
from cpc.util.exception import ClientError
from cpc.util.conf.client_conf import ClientConf, NoServerError


def printSortedConfigListDescriptions(configs):
    for key in sorted(configs.keys()):
        value = configs[key]
        spaces = ''
        for i in range(20 - len(value.name)):
            spaces = spaces + " "

        print value.name + spaces + value.description #+ '\n'


def printSortedConfigListValues(configs):
    for key in sorted(configs.keys()):
        value = configs[key]
        spaces = ''
        for i in range(20 - len(value.name)):
            spaces = spaces + " "

        print value.name + spaces + str(value.get()) #+ '\n'    


def initiateConnectionBundle(conffile):
    cf = None

    try:
        cf = ConnectionBundle(conffile)
        return cf
    except NoConfError:
        print "Could not find a connection bundle \nPlease specify one with " \
              "with the -c flag or supply the file with the name\nclient.cnx" \
              " in your configuration folder "
        sys.exit(1)

def getClientConf():
    try:
        cfg = ClientConf()
        #make sure there is configured server
        cfg.getClientSecurePort()
        cfg.getClientHost()
    except (NoConfError, NoServerError):
        raise ClientError("No servers."\
            " Use cpcc add-server to add one.")
    except cpc.util.conf.conf_base.ConfError as e:
        raise ClientError(e)     
    return cfg

def addServer(name, host, port):
    ClientConf().addServer(name, host,port)


def useServer(name):
    ClientConf().setDefaultServer(name)

def listServer():
    return ClientConf().getServers()

def initiateWorkerSetup():
    '''
       Creates a connection bundle
       @input configName String
       @return ConnectionBundle
    '''

    openssl = cpc.util.openssl.OpenSSL()
    connectionBundle = openssl.setupClient()
    return connectionBundle


def getArg(arglist, argnr, name):
    """Get argument, or print out argument description."""
    try:
        ret = arglist[argnr]
    except IndexError:
        raise ClientError("Missing argument: %s" % name)
    return ret



terminalWidth = 80
def printLogo():
    logo =  """
   ___                                  _
  / __\ ___   _ __    ___  _ __  _ __  (_)  ___  _   _  ___
 / /   / _ \ | '_ \  / _ \| '__|| '_ \ | | / __|| | | |/ __|
/ /___| (_) || |_) ||  __/| |   | | | || || (__ | |_| |\__
\____/ \___/ | .__/  \___||_|   |_| |_||_| \___| \__,_||___/
             |_|"""

    lines = logo.splitlines()
    for line in lines:
        print "          %s"%line

def printAuthors():
    developers = ["Magnus Lundborg", "Patrik Falkman","Grant Rotskoff","Per Larsson"]
    authors = ["Sander Pronk","Iman Pouya","Erik Lindahl"]

    contributorsTxt = "Contributions from: %s"%", ".join(developers)
    authorsTxt =  ", ".join(authors)

    wrapper = textwrap.TextWrapper(width=terminalWidth)
    lines = wrapper.wrap(contributorsTxt)

    print "\n"
    for line in lines:
        print line.center(terminalWidth)

    print "\n"

    for line in wrapper.wrap(authorsTxt):
        print line.center(terminalWidth)


    print "\n\n"

def checkServerConfExistAndAskToRemove(hostConfDir,altDirName=None):
    '''
    This method checks if a server conf exists and asks if the user wants to wipe it and continue.
    if Y the folder will be wiped and the setup flow will proceed
    if N the setup flow will be aborted

    returns: boolean
    '''
    dirname = server_conf.resolveSetupConfBaseDir(altDirName)
    confDir=cpc.util.conf.conf_base.findAndCreateGlobalDir()

    # now if a host-specific directory already exists, we use that
    confDir = server_conf.resolveSetupConfDir(confDir, dirname, hostConfDir,altDirName=altDirName)

    if os.path.exists(confDir):
        answer = raw_input("A configuration already exists in %s. Overwrite? (y/N)? "%confDir)
        if(answer.lower() == 'y'):
            return True

        else:  # answer = n
            print("Server setup aborted")
            exit(0)

