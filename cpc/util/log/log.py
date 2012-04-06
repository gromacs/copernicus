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


import logging.handlers
import os
import platform
from cpc.util.conf.server_conf import ServerConf
from cpc.util.log.format.colorformat import ColoredFormatter 
from cpc.util.log.format import colorformat
# maximum log file size
MAXFILESIZE=4*1024*1024
# number of logs to keep
NBACKUPS=5

#log level of for trace
TRACE = 5

# The format for output to files
fileFormat="%(asctime)-20s - %(levelname)-7s - %(name)-15s: %(message)s"
# The format for output to stdout
stdoutFormat="%(levelname)-s, $BOLD%(name)-s$RESET: %(message)s"

logging.addLevelName(TRACE,"TRACE")

def initClientLog(debug=False):
    """Initialize a client log: in this case, a log that only displays to 
       stdout."""
    logger=logging.getLogger('cpc')
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if(platform.system()=='Windows'):
        colorformat.add_coloring_to_emit_windows()
        handler=logging.StreamHandler()
        handler.emit(handler)
        logger.addHandler(handler)
    else:
        COLOR_FORMAT = colorformat.formatter_message(stdoutFormat)
        handler=logging.StreamHandler()
        colorFormatter = ColoredFormatter(COLOR_FORMAT)
        handler.setFormatter(colorFormatter)
        logger.addHandler(handler)
    initErrorLog()


def initServerLog(debug=False,trace=False):
    """Initialize a server log. This log outputs to the server log file 
       (usually ~/.copernicus/<hostname>/log/server.log)."""
    conf=ServerConf()
    logger=logging.getLogger('')
    if trace:
        logger.setLevel(TRACE)
    elif debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    # make the normal log file
    logDir=conf.getLogDir()
    logFilename=conf.getServerLogFile()
    try:
        os.makedirs(logDir)
    except:
        pass
    fhandler=logging.handlers.RotatingFileHandler(logFilename,
                                                  maxBytes=MAXFILESIZE, 
                                                  backupCount=NBACKUPS)
    fformatter=logging.Formatter(fileFormat)
    fhandler.setFormatter(fformatter)
    logger.addHandler(fhandler)
    initErrorLog()


def initServerLogToStdout(debug=False,trace=False):
    logger=logging.getLogger('')

    if trace:
        logger.setLevel(TRACE)
    elif debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    COLOR_FORMAT = colorformat.formatter_message(stdoutFormat)
        
    colorFormatter = ColoredFormatter(COLOR_FORMAT)
    streamhandler=logging.StreamHandler()
    streamhandler.setFormatter(colorFormatter)
    
    logger.addHandler(streamhandler)
    #streamhandler.setFormatter(soformatter)


def initErrorLog():
    """Initialize the error log. Should log all errors, client or server."""
    conf=ServerConf()
    logger=logging.getLogger('')
    # make the dirs etc.
    logDir=conf.getLogDir()
    try:
        os.makedirs(logDir)
    except:
        pass
    

    # make the error log file
    logFilename=conf.getErrorLogFile()
    fhandler=logging.handlers.RotatingFileHandler(logFilename,
                                                  maxBytes=MAXFILESIZE,
                                                  backupCount=NBACKUPS)
    fhandler.setLevel(logging.ERROR)
    fformatter=logging.Formatter(fileFormat)
    fhandler.setFormatter(fformatter)
    logger.addHandler(fhandler)


def initControllerLog(dir, controllerName=""):
    """Initialize a controller logger. Returns a logger object"""
    logFilename=os.path.join(dir, "controller.log")
    logger=logging.getLogger("cpc.%s"%controllerName)
    logger.setLevel(logging.DEBUG)
    fhandler=logging.handlers.RotatingFileHandler(logFilename,
                                                  maxBytes=MAXFILESIZE,
                                                  backupCount=NBACKUPS)
    fhandler.setLevel(logging.DEBUG)
    fformatter=logging.Formatter(fileFormat)
    fhandler.setFormatter(fformatter)
    logger.addHandler(fhandler)
    return logger



