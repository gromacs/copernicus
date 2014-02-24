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


from server_command import ServerCommand
import logging
import cpc.util.log

log=logging.getLogger(__name__)

class SCPullAsset(ServerCommand):
    """Return finished command data to requesting server"""
    def __init__(self):
        ServerCommand.__init__(self, "pull-asset")
        
    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        assetType=request.getParam('asset_type')
        try:
            runfile=serverState.getLocalAssets().getAsset(cmdID, 
                                                          assetType).getData()
        except:
            log.error("Local asset cmdid=%s not found!"%cmdID)
            response.add("Command output data from cmdID %s not found on this server (%s)."%
                         (cmdID,serverState.conf.getHostName()), 
                         status="ERROR")
        else:
            asset=serverState.getLocalAssets().getCmdOutputAsset(cmdID)
            log.log(cpc.util.log.TRACE,"Local asset cmdid=%s \nproject server=%s"%
                                       (asset.cmdID, asset.projectServer))
            response.setFile(runfile,'application/x-tar')
        log.info("Pulled asset %s/%s"%(cmdID, assetType))


class SCClearAsset(ServerCommand):
    """Clear local asset data (including associated files)"""
    def __init__(self):
        ServerCommand.__init__(self, "clear-asset")
       
    def run(self, serverState, request, response):
        cmdID=request.getParam('cmd_id')
        if serverState.getLocalAssets().removeAsset(cmdID):
            response.add("Local asset with cmdID=%s removed successfully."%
                         cmdID)
        else:
            response.add("Local asset with cmdID=%s NOT removed successfully."%
                         cmdID, status="ERROR")
        log.info("Cleared asset %s"%(cmdID))
    
