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
from cpc.util.log.format.colorformat import ColoredFormatter
from cpc.util.log.format import colorformat
# maximum log file size
from cpc.util.log.log_conf import LogConf

MAXFILESIZE=16*1024*1024
# number of logs to keep
NBACKUPS=10

#log level of for trace
TRACE = 5

MODE_DEBUG = "debug"
MODE_TRACE = "trace"
MODE_PRODUCTION = "prod"

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
    #initErrorLog()


def initServerLog(conf,log_mode=None):
    """Initialize a server log. This log outputs to the server log file 
       (usually ~/.copernicus/<hostname>/log/server.log)."""
    logger=logging.getLogger('')
    if log_mode == MODE_TRACE:
        logger.setLevel(TRACE)
    elif log_mode == MODE_DEBUG:
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
    initErrorLog(conf)


def initServerLogToStdout(log_mode=None):
    logger=logging.getLogger('')

    if log_mode == MODE_TRACE:
        logger.setLevel(TRACE)
    elif log_mode == MODE_DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    COLOR_FORMAT = colorformat.formatter_message(stdoutFormat)
        
    colorFormatter = ColoredFormatter(COLOR_FORMAT)
    streamhandler=logging.StreamHandler()
    streamhandler.setFormatter(colorFormatter)
    streamhandler.addFilter(LogFilter())
    
    logger.addHandler(streamhandler)
    #streamhandler.setFormatter(soformatter)


def initErrorLog(conf):
    """Initialize the error log. Should log all errors, client or server."""
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



class LogFilter(logging.Filter):
    def __init__(self):
        conf = LogConf()
        self.whitelist = [logging.Filter(name) for name in conf.getWhitelist()]
        self.blacklist = [logging.Filter(name) for name in conf.getBlacklist()]

    def filter(self, record):
        return any(f.filter(record) for f in self.whitelist) and not any(f.filter(record) for f in self.blacklist)
