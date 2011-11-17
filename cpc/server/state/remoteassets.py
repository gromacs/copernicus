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


from cpc.server.state.asset import Asset

class RemoteAsset(Asset):
    def __init__(self, cmdID, dataLocation):
        self.cmdID = cmdID
        self.dataLocation = dataLocation

class RemoteAssets:
    """Maintains a dictionary of remote assets such as completed commands"""
        
    def __init__(self):
        self.assets = dict()
        
    def addAsset(self, cmdID, dataLocation):
        self.assets[cmdID] = RemoteAsset(cmdID, dataLocation)
        
    def getAsset(self, cmdID):
        return self.assets[cmdID]
    
    def removeAsset(self, cmdID):
        del self.assets[cmdID]
