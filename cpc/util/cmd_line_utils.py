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
import cpc.util.openssl
import os
#from socket import gethostname
import socket
from cpc.util.conf.conf_base import Conf
from cpc.util.conf.client_conf import ClientConf
from cpc.util.conf.worker_conf import WorkerConf
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


def initiateClientToolSetup(configName=None):
    ''' 
       @input configName String  
    '''
    if configName ==None:
        configName = socket.getfqdn()
        
    confdir = os.path.join(Conf.GLOBAL_DIR,configName)    
    
    checkDir = os.path.join(confdir,"client")
    if os.path.exists(checkDir)==True:
        decision = raw_input("there already exists client configurations in %s do you wish to overwrite(y/n)?"%checkDir)
        if decision !='y':
            print "No new client setup generated"
            return None
        else:
            shutil.rmtree(checkDir)#the config and ssl functions are smart they dont overwrite anything so we remove the folder explicitly
            

    cf=ClientConf(confdir=confdir,reload=True)
    openssl = cpc.util.openssl.OpenSSL(cf,configName)
    openssl.setupClient()

def initiateWorkerSetup(configName=None):
    ''' 
       @input configName String  
    '''
    if configName ==None:
        configName = socket.getfqdn()
        
    confdir = os.path.join(Conf.GLOBAL_DIR,configName)    
    
    checkDir = os.path.join(confdir,"worker")
    if os.path.exists(checkDir)==True:
        decision = raw_input("there already is a worker configuration in %s; do you want to overwrite it(y/n)?"%checkDir)
        if decision !='y':
            print "No new worker setup generated"
            return None
        else:
            shutil.rmtree(checkDir)#the config and ssl functions are smart they dont overwrite anything so we remove the folder explicitly
            

    cf=WorkerConf(confdir=confdir,reload=True)
    openssl = cpc.util.openssl.OpenSSL(cf,configName)
    openssl.setupClient()



def initiateServerSetup(rundir,configName =None):    
    ''' 
       @input configName String  
    '''
    if configName ==None:
        configName = socket.getfqdn()
    
    confdir = os.path.join(Conf.GLOBAL_DIR,configName)
    
    checkDir = os.path.join(confdir,"server")
    if os.path.exists(checkDir)==True:
        decision = raw_input("there already is a server configuration in %s; do you want to overwrite it(y/n)?"%checkDir)
        
        if decision != 'y':
            print "No new server setup generated"
            return None
        else:
            shutil.rmtree(checkDir)
            
    cf=cpc.util.conf.server_conf.ServerConf(confdir=confdir,reload=True)
    openssl = cpc.util.openssl.OpenSSL(cf,configName)
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
    
