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
import re
import threading

from cpc.util import CpcError
import cpc.util.json_serializer
import cpc.util.exception
import cpc.util.cert_req_conf_template
import cpc.util.ca_conf_template


class ConfError(cpc.util.exception.CpcError):
    pass


class InputError(CpcError):
    def __init__(self, exc):
        self.str = exc.__str__()


def findGlobalDir():
    """Get the global configuration directory base path for all configuration
        files. This depends on the OS"""
    if "HOME" in os.environ:
        return os.path.join(os.environ["HOME"], Conf.base_path)
    else:
        # we're probably running on Windows.
        # there we store the connection bundlein 
        # /HOME/Documents/copernicus/client.cnx
        import ctypes.wintypes

        CSIDL_PERSONAL = 5       # My Documents
        SHGFP_TYPE_CURRENT = 0   # Want current, not default value
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_PERSONAL, 0,
            SHGFP_TYPE_CURRENT, buf)
        homedir = buf.value
        return os.path.join(homedir, Conf.base_path_normal)
    raise ConfError("Could not determine global base directory")


class ConfValue:
    """Configuration value. Each configuration value has a name, and a
       default value. If the value is user settable, there can be a 
       set value."""

    def __init__(self, name, defaultValue, description, userSettable=False,
                 setValue=None, relTo=None, validation=None, allowedValues=None,
                 writable=True):
        self.name = name
        self.defaultValue = defaultValue
        self.description = description
        self.userSettable = userSettable
        self.setValue = setValue
        self.relTo = relTo
        self.validation = validation  #a regexp that validates the correct input
        self.allowedValues = allowedValues # list of allowed values for this config parameter
        self.writable = writable

    def get(self):
        """Get the current value."""
        if self.setValue is not None:
            return self.setValue
        else:
            return self.defaultValue

    def set(self, newValue):
        """Set a new value."""
        if self.validation != None:
            regexp = re.compile(self.validation)

            match = regexp.match(newValue)
            if match == None:
                raise InputError(
                    "The value %s must match %s" % (newValue, self.validation))

        if self.allowedValues != None:
            try:
                self.allowedValues.index(newValue)
            except ValueError:
                allowedValuesStr = ','.join(self.allowedValues)
                raise InputError("The value %s does not match any of %s" % (
                newValue, allowedValuesStr))  #Throw an exception with a message

        self.setValue = newValue

    def reset(self):
        """Reset the value to the default value."""
        self.setValue = None

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

    # global defaults
    base_path_normal = 'copernicus'
    base_path = '.%s' % base_path_normal
    default_dir = '_default'


    def __init__(self, name=None, confSubdirName=None, userSpecifiedPath=None):
        """Get an existing singleton, or read basic configuration stuff"""
        if self.exists():
            return

        # initialize for the first time:
        self.conf = dict()
        self.hostname = socket.getfqdn()

        self._add('hostname', self.hostname, 'hostname', userSettable=True)

        # find the location of the configuration file and associated paths
        self.findLocation(name, confSubdirName, userSpecifiedPath)



        #FIXME generalize layered solution 
        # find the base directory of the executable for plugins
        dn = os.path.dirname(sys.argv[0])
        self.execBasedir = ''
        if dn != "":
            self.execBasedir = os.path.abspath(dn)
            self._add('exec_base_dir', self.execBasedir,
                'executable base directory')

        # Initialization always happens when there's only one thread, so 
        # this should be safe:
        # TODO: make it a regular Lock() - for now this might reduce the 
        # chances of a deadlock
        self.lock = threading.RLock()
        # and read in the actual values from the configuration file.        
        #self.have_conf_file = self.tryRead() 

    def exists(self):
        """Check for and initialize pre-existing singleton object."""
        # all objects created will share the same state
        self.__dict__ = self.__shared_state
        # check whether we initialized it already and bail out if we did
        if len(self.__shared_state) > 0:
            return True
        return False


    def findLocation(self, name, confSubdirName, userSpecifiedPath=None):
        """Find the location (full path name) of an existing configuration 
            file with name 'name'. Will use 'userSpecifiedPath' if set.

            The function will set four configuration variables: 
            conf_file = the full path of the configuration file
            conf_dir = the directory name of the directory containing the 
                       configuration file
            base_dir = the directory name of the directory containing the
                       sub directory of the configuration file. This 
                       is different from conf_dir if confSubdirName is set
            global_dir = the globl configuration directory containing all
                         configurations for all hosts, etc.

            If userSpecifiedPath is not set, it will try a host-specific
            directory first, then '_default'.

            userSpecifiedPath is either a file name (if confSubdirName is not
            set), or a directory name (if confSubdirName is set). 
             
            If confSubdirName is set, the search for conf. files will happen
            with that subdir name set first"""
        # a list of directories (base_dirs) to try: 
        dirsToTry = []

        globalDir = findGlobalDir()
        # first with the hostname appended
        dirsToTry.append(os.path.join(globalDir, self.hostname))
        # then in the '_default' directory
        dirsToTry.append(os.path.join(globalDir, self.default_dir))
        # then in the .copernicus directory
        dirsToTry.append(os.path.join(globalDir))
        # and we should set this explicitly
        self._add('global_dir', globalDir, 'The global configuration directory',
            userSettable=False)

        if userSpecifiedPath is not None:
            if confSubdirName is None:
                # in this case, userSpecifiedPath must be a file
                if not os.path.isfile(userSpecifiedPath):
                    raise ConfError(
                        "File %s does not exist" % userSpecifiedPath)
                dirsToTry = [os.path.dirname(userSpecifiedPath)]
            else:
                # it must be a directory name
                if not os.path.isdir(userSpecifiedPath):
                    raise ConfError("Directory %s does not exist" %
                                    userSpecifiedPath)
                dirsToTry = [userSpecifiedPath]

        for dirname in dirsToTry:
            if confSubdirName is None:
                confdirname = dirname
            else:
                confdirname = os.path.join(dirname, confSubdirName)
            filename = os.path.join(confdirname, name)
            if os.path.exists(filename):
                self._add('conf_file', filename, 'The configuration file name')
                self._add('base_dir', dirname,
                    'The base directory containing all client+server confs',
                    userSettable=False)
                self._add('conf_dir', confdirname,
                    'The configuration directory', userSettable=False)
                return
        raise ConfError("Configuration file not found")


    def initDefaults(self):
        #config params for the Certificate authority
        self._add('ca_dir', "ca",
            "Base SSL CA directory (relative to conf_dir)",
            relTo='base_dir')
        self._add('ca_key_dir', "keys", 'CA key directory',
            relTo="ca_dir")
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
             relTo=None, validation=None, allowedValues=None, writable=True):
        """Add a configuration value with a default value, description"""
        self.conf[name] = ConfValue(name, defaultValue, desc,
            userSettable=userSettable,
            relTo=relTo, validation=validation,
            allowedValues=allowedValues,
            writable=writable)

    def _tryRead(self):
        try:
            confname = self.getFile('conf_file')
            f = open(confname, 'r')
            str = f.read()
            try:
                #print str
                nconf = json.loads(str,
                    object_hook=cpc.util.json_serializer.fromJson)
                # merge items
                for (key, val) in nconf.iteritems():
                    if self.conf.has_key(key):
                        self.conf[key].set(val)
                        # if it doesn't exist as a key, we ignore it.
            except Exception as e:
                raise ConfError("Couldn't load %s: %s" % (confname, str(e)))
            return True
        except:
            # there was no configuration file. 
            # at least try to make the directory
            try:
                dirname = os.path.dirname(confname)
                os.makedirs(dirname)
                os.chmod(dirname, stat.S_IRWXU)
            except:
                pass
            return False

    def write(self):
        """ write all conf settings that have non-default values to file."""
        with self.lock:
            self._writeLocked()

    def _writeLocked(self):
        confname = self.getFile('conf_file')
        try:
            dirname = os.path.dirname(confname)
            if os.path.isdir(dirname) == False:
                os.makedirs(dirname)
                os.chmod(dirname, stat.S_IRWXU)
        except OSError, e:
            log.error('%s %s %s' % (e.errno, e.strerror, e.filename))

        f = open(confname, "w")
        # construct a dict with only the values that have changed from 
        # the default values
        conf = dict()

        for cf in self.conf.itervalues():
            if cf.hasSetValue():
                conf[cf.name] = cf.get()
            # and write out that dict.
        f.write(json.dumps(conf,
            default=cpc.util.json_serializer.toJson,
            indent=4))
        f.close()


    def toJson(self):
        '''
        returns a json formatted string
        @return json String
        '''

        with self.lock:
            conf = dict()
            for cf in self.conf.itervalues():
                if cf.writable:
                    conf[cf.name] = cf.get()

            return json.dumps(conf,
                default=cpc.util.json_serializer.toJson,
                indent=4)

    def reread(self):
        """Update from configuration file. First reset all values, then 
           read them from disk."""
        with self.lock:
            for val in self.conf.itervalues():
                val.reset()
            self._tryRead()

    def get(self, name):
        """Get the current value associated with this configuration."""
        with self.lock:
            return self.conf[name].get()

    def getFile(self, name):
        """Get a full path name based on a configuration name.
           Expands 'relTo' names iteratively."""
        with self.lock:
            nameval = self.conf[name].get()
            if os.path.isabs(nameval):
                # in this case we're done quickly
                return nameval
            retpath = nameval
            curRel = self.conf[name].relTo
            while curRel is not None:
                # now iteratively traverse the reverse path
                retpath = os.path.join(self.conf[curRel].get(), retpath)
                curRel = self.conf[curRel].relTo
            return retpath

    def set(self, name, value):
        """Set a new value associated with this configuration."""
        with self.lock:
            try:
                self.conf[name].set(value)
                self._writeLocked()
            except KeyError:
                raise InputError("The config parameter %s do not exist" %
                                 (name))

    def userSet(self, name, value):
        """Set a new value associated with this configuration while checking
           whether that value can be set by a user."""
        with self.lock:
            if self.conf[name].isUserSettable():
                self.conf[name].set(value)
            else:
                raise ConfError("Value of '%s' is not user settable" % name)

    def isUserSettable(self, name):
        with self.lock:
            return self.conf[name].isUserSettable()

    def confFileValid(self):
        with self.lock:
            return self.have_conf_file

    def getUserSettableConfigs(self):
        with self.lock:
            configs = dict()
            for key, value in self.conf.iteritems():
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
        with self.lock:
            return self.conf['exec_base_dir'].get()

    def getPluginPaths(self):
        with self.lock:
            lst = self.conf['plugin_path'].get().split(':')
            retlist = []
            for ls in lst:
                str = ls.strip()
                if str != "":
                    retlist.append(str)
            retlist.append(os.path.join(self.execBasedir, 'cpc', 'plugins'))
            return retlist


    def getExecutablesPath(self):
        retlist = []
        with self.lock:
            lst = self.conf['executables_path'].get().split(':')
            for ls in lst:
                str = ls.strip()
                if str != "":
                    retlist.append(str)
        retlist.append(self.getFile('global_executables_dir'))
        retlist.append(self.getFile('local_executables_dir'))
        # now add the plugin path executables
        ppath = self.getPluginPaths()
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

    def getGlobalDir(self):
        return self.get("global_dir")
    
