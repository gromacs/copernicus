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


import logging
import os.path

from cpc.util.conf.server_conf import ServerConf
from cpc.server.state.asset import Asset
import cpc.util

log=logging.getLogger(__name__)

class LocalAssetError(cpc.util.CpcError):
    pass

class LocalAsset(Asset):
    def __init__(self, cmdID, projectServer, data, assetType, storeData=True):
        """Constructor, takes the cmdID, project server owning data and the asset type. The assetType
        should be a method call to LocalAsset.xOutput() where x is the asset type.
        Use storeData = false if you for some reason don't want the data to be stored to a file."""
        self.cmdID = cmdID
        self.projectServer = projectServer
        self.assetType = assetType
        
        if storeData:
            self.__storeData(data)
            data.close()
        else:
            self.__data = data
        
        
    def __storeData(self, data):
        """Stores a copy of the file reference and returns a reference to the 
           new file"""
        filename=self.__getOutputFilename()
        # we checked for the existence of the asset before, so any lingering
        # file names are OK

        outputFilePath=self.__getOutputFilePath()
        if(not os.path.isdir(outputFilePath)):
            os.makedirs(outputFilePath) 

        self.__data = open(filename, "w+")
        self.__data.write(data.read())
        self.__data.flush()
        self.__data.seek(0)
        
        #TODO we need to store other relevant data? this should be improved. xml? 
        psfile = open(self.__getOutputFilename()+".ps", "w")
        psfile.write(self.projectServer)
        psfile.close()
        
    def __getOutputFilePath(self):
        return os.path.join(ServerConf().getLocalAssetsDir(), self.assetType)
    
    def __getOutputFilename(self):
        return os.path.join(self.__getOutputFilePath(), self.cmdID)
    
    def getData(self):
        self.__data.seek(0)
        return self.__data
    
    def delete(self):
        self.__data.close()
        if os.path.isfile(self.__getOutputFilename()):
            os.remove(self.__getOutputFilename())
        
        #also remove all other files associated with this asset that might exist
        if os.path.isfile(self.__getOutputFilename()+".ps"):
            os.remove(self.__getOutputFilename()+".ps")
            
    def __restore(self):
        self.__data = open(self.__getOutputFilename(), "r")
        file = open(self.__getOutputFilename()+".ps", "r")
        self.projectServer = file.read()
        file.close()

    @staticmethod
    def restore(cmdID, assetType):
        asset = LocalAsset(cmdID, None, None, assetType, False)
        if os.path.isfile(asset.__getOutputFilename()):
            asset.__restore()
            return asset
        return None

class LocalAssets(object):
    """Maintains a dictionary of local assets such as completed commands"""
        
    def __init__(self):
        self.assets = dict()
        
    def addCmdOutputAsset(self, cmdID, projectServer, fileData):
        if cmdID not in self.assets:
            self.__addAsset(cmdID, projectServer, fileData, 
                            LocalAsset.cmdOutput())
        else:
            raise LocalAssetError("Local assset %s already exists"%cmdID)
        
    def __addAsset(self, cmdID, projectServer, data, dataType):
        self.assets[cmdID] = LocalAsset(cmdID, projectServer, data, dataType)
        
    def __getAsset(self, cmdID, dataType):
        try:
            asset = self.assets[cmdID]
        except:
            #try to restore the asset from the file
            asset = LocalAsset.restore(cmdID, dataType)
            if asset != None:
                self.assets[cmdID] = asset
        
        #this will properly raise an exception if asset could not be found or restored
        return self.assets[cmdID]
        

    def getAsset(self, cmdID, dataType):
        return self.__getAsset(cmdID, dataType)
            
    def getCmdOutputAsset(self, cmdID):
        return self.__getAsset(cmdID, LocalAsset.cmdOutput())
    
    def removeAsset(self, cmdID):
        if cmdID in self.assets:
            self.assets[cmdID].delete()
            del self.assets[cmdID]
            return True
        else:
            return False
