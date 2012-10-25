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
from cpc.util.conf.connection_bundle import ConnectionBundle
import cpc.util.openssl
import os
#from socket import gethostname
import socket
import sys
import shutil

from cpc.util.conf.conf_base import Conf
import cpc.util.conf.conf_base
import cpc.util.conf.server_conf
from cpc.network.com.client_base import ClientError

class ConfError(cpc.util.exception.CpcError):
    pass


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
    except cpc.util.conf.conf_base.ConfError:
        print "Could not find a connection bundle \nPlease specify one with " \
              "with the -c flag or supply the file with the name\nclient.cnx" \
              " in your configuration folder "
        sys.exit(1)


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
    
