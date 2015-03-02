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
import logging
from cpc.server.message.server_message import ServerMessage
from cpc.network.com.client_response import ProcessedResponse
from cpc.server.state.asset import Asset
from cpc.util.conf.server_conf import ServerConf
import cpc.util.log

log=logging.getLogger(__name__)

def initTracker():
    conf = ServerConf()
    dirs= Asset.getDirs()
    try:
        os.makedirs(conf.getLocalAssetsDir())
    except:
        pass
    for dir in dirs:
        try:
            os.makedirs(os.path.join(conf.getLocalAssetsDir(), dir))
        except:
            pass

class Tracker(object):
    
    @staticmethod
    def getCommandOutputData(cmdID, workerServer):
        log.log(cpc.util.log.TRACE,"Trying to pull command output from %s"%
                workerServer)
        s2smsg=ServerMessage(workerServer)  
        rundata_response = s2smsg.pullAssetRequest(cmdID, Asset.cmdOutput())
        
        if rundata_response.getType() != "application/x-tar":
            log.error("Incorrect response type: %s, should be %s"%
                      (rundata_response.getType(), 'application/x-tar'))
            if rundata_response.getType() == "text/json":
                errormsg=rundata_response.message.read(len(rundata_response.
                                                           message))
                presp=ProcessedResponse(rundata_response)
                if not presp.isOK():
                    log.error('Response from worker server not OK: %s'%
                              errormsg)
        else:
            s2smsg.clearAssetRequest(cmdID)
            log.log(cpc.util.log.TRACE,
                    "Successfully pulled command output data from %s."%
                    workerServer)
            return rundata_response
            #runfile = rundata_response.getRawData()
            #this doesnt work because the mmap closes as it is returned
        return None
    
