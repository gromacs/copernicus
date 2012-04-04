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
from cpc.util.conf.conf_base import Conf
import cpc.util.conf.server_conf
from cpc.network.com.client_base import ClientError

import shutil
def printSortedConfigListDescriptions(configs):
    for key in sorted(configs.keys()):
            value = configs[key] 
            spaces = ''
            for i in range(20-len(value.name)):
                spaces = spaces + " "
                
            print value.name + spaces + value.description + '\n' 
    
def printSortedConfigListValues(configs):    
    for key in sorted(configs.keys()): 
        value = configs[key]
        spaces = ''
        for i in range(20-len(value.name)):
            spaces = spaces + " "
         
        print value.name + spaces + str(value.get()) + '\n'    



def initiateConnectionBundle(conffile=None):
    '''
    Tries to fetch a connectionbundle other via the provided file or via the default conf dir
    @input String conffile : the path to a conffile
    @returns ConnectionBundle
    '''
    if(conffile == None): # no conffile is provided we try to see if a file exists in our basic directory
        cf = ConnectionBundle()
        conffile =os.path.join(cf.getGlobaDir(),"client.cnx")
        if(os.path.isfile(conffile)):
            cf = ConnectionBundle(conffile = conffile,reload=True)

    else:
        cf=ConnectionBundle(conffile=conffile)

    return cf



def initiateWorkerSetup():
    '''
       Creates a connection bundle
       @input configName String
       @return ConnectionBundle
    '''

    configName = socket.getfqdn()
    openssl = cpc.util.openssl.OpenSSL(cn = configName)
    connectionBundle = openssl.setupClient()
    return connectionBundle


def initiateServerSetup(rundir,configName =None,confDir=None):
    ''' 
       @input configName String  
    '''
    if configName ==None:
        configName = socket.getfqdn()

    if(confDir==None):
        confDir = os.path.join(Conf().getGlobaDir(),configName)
    
    checkDir = os.path.join(confDir,"server")
    if os.path.exists(checkDir)==True:
        decision = raw_input("there already is a server configuration in %s; do you want to overwrite it(y/n)?"%checkDir)
        
        if decision != 'y':
            print "No new server setup generated"
            return None
        else:
            shutil.rmtree(checkDir)
            
    cf=cpc.util.conf.server_conf.ServerConf(confdir=confDir,reload=True)
    openssl = cpc.util.openssl.OpenSSL(configName)
    setupCA(openssl,cf)
    openssl.setupServer()
    cf.setRunDir(rundir) 


def setupCA(openssl,conf):
    
    checkDir = conf.getCADir()
    if os.path.exists(checkDir)== True:
        decision = raw_input("there already is a CA in %s; do you want to overwrite it (y/n)?"%checkDir)
        
        if decision != 'y':
            print "No new ca generated"
            return None
        else:
            shutil.rmtree(checkDir)
        
    openssl.setupCA() 
    
def getArg(arglist, argnr, name):
    """Get argument, or print out argument description."""
    try: 
        ret=arglist[argnr]
    except IndexError:
        raise ClientError("Missing argument: %s"%name)
    return ret
    
