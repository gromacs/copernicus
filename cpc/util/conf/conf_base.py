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


import sys
import os.path
#from socket import gethostname
import socket
import stat
import json
from cpc.util import CpcError
import re
import cpc.util.json_serializer
import cpc.util.exception
import cpc.util.cert_req_conf_template
import cpc.util.ca_conf_template

class ConfError(cpc.util.exception.CpcError):
    pass


class InputError(CpcError):
    def __init__(self,exc):
        self.str=exc.__str__()
        
        
class ConfValue:
    """Configuration value. Each configuration value has a name, and a
       default value. If the value is user settable, there can be a 
       set value."""
    def __init__(self, name, defaultValue, description, userSettable=False, 
                 setValue=None, relTo=None,validation=None,allowedValues=None):
        self.name=name
        self.defaultValue=defaultValue
        self.description=description
        self.userSettable=userSettable
        self.setValue=setValue
        self.relTo=relTo
        self.validation = validation  #a regexp that validates the correct input
        self.allowedValues = allowedValues # list of allowed values for this config parameter        

    def get(self):
        """Get the current value."""
        if self.setValue is not None:
            return self.setValue
        else:
            return self.defaultValue
    def set(self, newValue):
        """Set a new value."""        
        if self.validation !=None:                        
            regexp = re.compile(self.validation)
            
            match = regexp.match(newValue)
            if match == None:
                raise InputError("The value %s must match %s"%(newValue,self.validation))
            
        if self.allowedValues !=None:            
            try:
                self.allowedValues.index(newValue)
            except ValueError: 
                allowedValuesStr = ','.join(self.allowedValues)                                
                raise InputError("The value %s does not match any of %s"%(newValue,allowedValuesStr))  #Throw an exception with a message
        
                      
        self.setValue=newValue

    def reset(self):
        """Reset the value to the default value."""
        self.setValue=None

    def hasSetValue(self):
        """Check whether the configuration setting has been set to something
            else than the default value."""            
        return (self.setValue is not None)

    def isUserSettable(self):
        """Check whether the 'user settable' flag has been set for this 
           value."""
        return self.userSettable

class Conf:
    """Common configuration class. Reads from copernicus base directory"""
    __shared_state = {}   
    GLOBAL_DIR = os.path.join(os.environ["HOME"],".copernicus")
    
    def __init__(self,conffile='cpc.conf', confdir = None,reInit =False):
        """Read basic configuration stuff"""
        # all objects created will share the same state
        #self.__dict__ = self.__shared_state   
        # check whether we initialized it already and bail out if we did
        
        #if len(self.__shared_state) > 0 and reInit == False and conffile=='cpc.conf':   #FIXME proper Singleton implementation   and threadsafety
        #   return
        
        # initialize for the first time:
        self.conf = dict()
        self.hostname=socket.getfqdn()        
        
        self._add('hostname',self.hostname,'hostname',userSettable=True)
        
        # We first need to find out where our configuration files are.
        self._add('global_dir', os.path.join(os.environ["HOME"],
                                             ".copernicus"),
                  'The global configuration directory',
                  userSettable=True)
        
                  
        self._add('conf_dir', os.path.join(os.environ["HOME"],
                                           ".copernicus",
                                           self.hostname),
                  'The configuration directory',
                  userSettable=True)
        
        
        #NOTE the conf dir is actullay the confdir for the separata applications
        # the classes that inherit from Conf usually overwrite this param                
        if confdir is not None:
            self.conf['conf_dir'].set(confdir)
        # once we have the directory, we use the default filename:
        
        self._add('base_dir',self.get("conf_dir"),
                                             "the base directory for current configuration set")
        
        
        self._add('conf_file',conffile, 'The configuration file name',
                  relTo='conf_dir')



        #FIXME generalize layered solution 
        # find the base directory of the executable for plugins
        dn=os.path.dirname(sys.argv[0])
        self.execBasedir = ''
        if dn != "":
            self.execBasedir=os.path.abspath(dn)
            self._add('exec_base_dir', self.execBasedir, 
                      'executable base directory')
           
                        
        # and read in the actual values from the configuration file.        
        #self.have_conf_file = self.tryRead() 
              

    def initDefaults(self):
        
        #config params for the Certificate authority
        self._add('ca_dir', "ca", 
                  "Base SSL CA directory (relative to conf_dir)",
                  relTo='base_dir')    
        self._add('ca_key_dir',"keys",'CA key directory',relTo="ca_dir")                        
        self._add('ca_cert_dir', "certs", 
                  "Server certificate directory (relative to ca_dir)",
                  relTo="ca_dir")
        self._add('ca_priv_key_file', "priv.pem", 
                  "ca private key file (relative to ca_key_dir)",
                  relTo="ca_key_dir")
        self._add('ca_pub_key_file', "pub.pem", 
                  "CA public key file (relative to ca_key_dir)",
                   relTo="ca_key_dir")
        self._add('cachain_file', "cachain.pem", 
                  "Server CA chain file (relative to ca_dir)",
                  relTo="ca_dir")
        self._add('caconf_file', "caconf", 
                  "CA configuration file (relative to ca_dir)",
                  relTo="ca_dir")
        self._add('ca_serial_file', "serial", 
                  "CA serial file (relative to ca_dir)",
                  relTo="ca_dir")
        self._add('ca_index_file', "index.txt",
                  "CA index file (relative to ca_dir)",
                  relTo="ca_dir")  
        self._add('ca_cert_file', "cert.pem", 
                  "CA certificate file (relative to ca_dir)",
                  relTo="ca_dir")

        self._add('cert_req_conf', "cert_req_conf", 
                  "key directory",
                  relTo="conf_dir")        
        self._add('key_dir', "keys", 
                  "key directory",
                  relTo="conf_dir")        
        self._add('priv_key_file', "priv.pem", 
                  "Server private key file (relative to server_cert_dir)",
                  relTo="key_dir")
        self._add('pub_key_file', "pub.pem", 
                  "Server public key file",
                  relTo="key_dir")
        self._add('cert_file', "cert.pem", 
                  "certificate file (relative to conf_dir)",
                  relTo="conf_dir")
        self._add('cert_request_file', "req.csr", 
                  "Server certificate signing request file (relative to base_dir)",
                  relTo="base_dir")
  
    

        self._add('plugin_path', "", 
                  "Colon-separated list of directories to search for plugins",
                  True)
        
        self._add('local_executables_dir', "executables",
                  "Directory containing executables for the run client. Part of executables_path",
                  False,
                  relTo='conf_dir')
        self._add('global_executables_dir', "executables",
                  "The directory containing executables for the run client. Part of executables_path",
                  False,
                  relTo='global_dir')
        self._add('executables_path', "",
                  "Colon-separated directory list to search for executables",
                  True)

    
    def _add(self, name, defaultValue, desc, userSettable=False, 
             relTo=None,validation=None,allowedValues =None):
        """Add a configuration value with a default value, description"""
        self.conf[name] = ConfValue(name, defaultValue, desc, 
                                    userSettable=userSettable,
                                    relTo=relTo,validation=validation,
                                    allowedValues=allowedValues)
       
    def tryRead(self):
        
        try:   
            confname = self.getFile('conf_file')
            #self.conf = pickle.loads(f.read())
            f = open(confname,'r')  
            str = f.read()
            try:
                #print str
                nconf = json.loads(str,object_hook = cpc.util.json_serializer.fromJson)
                # merge items
                for (key, val) in nconf.iteritems():
                    if self.conf.has_key(key):
                        self.conf[key].set(val)
                    # if it doesn't exist as a key, we ignore it.
            except Exception as e:
                print("ERROR: %s"%e)
                    
            return True
        except:
            # there was no configuration file. 
            # at least try to make the directory
            try:
                dirname=os.path.dirname(confname)
                os.makedirs(dirname)
                os.chmod(dirname, stat.S_IRWXU)                
            except:
                pass
            return False

    def write(self):
        # write all conf settings that have non-default values to file.
        confname = self.getFile('conf_file')        
        try:
            dirname=os.path.dirname(confname)
            if os.path.isdir(dirname) == False:
                os.makedirs(dirname)
                os.chmod(dirname, stat.S_IRWXU)
        except OSError, e:
            print('ERROR: %s %s %s'%(e.errno,e.strerror,e.filename))
           
        f = open(confname,"w")
        # construct a dict with only the values that have changed from 
        # the default values
        conf=dict()
        

        for cf in self.conf.itervalues():
            if cf.hasSetValue():
                conf[cf.name] = cf.get()
        # and write out that dict.       
        f.write(json.dumps(conf,default = cpc.util.json_serializer.toJson,indent=4))               
        f.close()

    def reread(self):
        """Update from configuration file. First reset all values, then 
           read them from disk."""
        for val in self.conf.itervalues():
            val.reset()
        self.tryRead()

    def get(self, name):
        """Get the current value associated with this configuration."""
        return self.conf[name].get()

    def getFile(self, name):
        """Get a full path name based on a configuration name.
           Expands 'relTo' names iteratively."""
                        
        nameval=self.conf[name].get()
        if os.path.isabs(nameval):
            # in this case we're done quickly
            return nameval
        retpath=nameval
        curRel=self.conf[name].relTo
        while curRel is not None:
            # now iteratively traverse the reverse path
            retpath=os.path.join(self.conf[curRel].get(), retpath)
            curRel=self.conf[curRel].relTo
        return retpath

    def set(self, name, value):
        """Set a new value associated with this configuration."""
        try:
            self.conf[name].set(value)
            self.write()            
        except KeyError:
            raise InputError("The config parameter %s do not exist"%(name))    

    def userSet(self, name, value):
        """Set a new value associated with this configuration while checking
           whether that value can be set by a user."""
        if self.conf[name].isUserSettable():
            self.conf[name].set(value)
        else:
            raise ConfError("Value of '%s' is not user settable"%name)

    def isUserSettable(self, name):
        return self.conf[name].isUserSettable()

    def confFileValid(self):
        return self.have_conf_file

    def getUserSettableConfigs(self):
        configs = dict()
        for key,value in self.conf.iteritems():
            if value.userSettable == True:
                configs[key] = value
        
        return configs

    def getConfDir(self):
        return self.get('conf_dir')
    def getHostName(self):
        return self.hostname
   
    def getCaDir(self):
        return self.getFile('ca_dir')
    
    def getKeyDir(self):
        return self.getFile('key_dir')
    #DEPRECATED
    #def getServerCertDir(self):
     #   return self.getFile('server_cert_dir')
    
    def getCertFile(self):
        return self.getFile('cert_file')
    
    def getCACertFile(self):
        return self.getFile('ca_cert_file')
    
    def getCertRequestFile(self):
        return self.getFile('cert_request_file')
    
    def getCaChainFile(self):
        return self.getFile('cachain_file')
    
    def getCaConfTemplate(self):
        #a String template, no a real config parameter        
        return cpc.util.ca_conf_template.caConfTemplate   
        
    def getPublicKey(self):
        return self.getFile('pub_key_file')
        
    def getPrivateKey(self):   
        return self.getFile('priv_key_file')

    def getCAPrivateKey(self):
        return self.getFile('ca_priv_key_file')
    def getCAPublicKey(self):
        return self.getFile('ca_pub_key_file')
    def getCASerialFile(self):
        return self.getFile('ca_serial_file')

    def getCAIndexFile(self):
        return self.getFile('ca_index_file')
    
    def getCaConfigFile(self):        
        return self.getFile('caconf_file')    
    
    def getModuleBasePath(self):
        return self.conf['exec_base_dir'].get()

    def getPluginPaths(self):
        lst=self.conf['plugin_path'].get().split(':')
        retlist=[]
        for ls in lst:
            str=ls.strip()
            if str != "":
                retlist.append(str)
        retlist.append(os.path.join(self.execBasedir, 'cpc', 'plugins'))
        return retlist
    
    
    def getExecutablesPath(self):
        lst=self.conf['executables_path'].get().split(':')
        retlist=[]
        for ls in lst:
            str=ls.strip()
            if str != "":
                retlist.append(str)
        retlist.append(self.getFile('global_executables_dir'))
        retlist.append(self.getFile('local_executables_dir'))
        ppath=self.getPluginPaths()
        for p in ppath:
            retlist.append(os.path.join(p, "executables"))
        return retlist
    
    def getCAKeyDir(self):
        return self.getFile("ca_key_dir")
    
    def getCACertDir(self):
        return self.getFile("ca_cert_dir")
    
    def getCertReqConfigTemplate(self):
        return cpc.util.cert_req_conf_template.template
    def getCertReqConfigFile(self):
        return self.getFile("cert_req_conf")
    def getCADir(self):
        return self.getFile("ca_dir")
    
