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
import os
import re
import os.path
import shutil
import glob
import stat
import subprocess
import logging
import time


log=logging.getLogger(__name__)

from cpc.dataflow import Value
from cpc.dataflow import FileValue
from cpc.dataflow import IntValue
from cpc.dataflow import StringValue
from cpc.dataflow import FloatValue
from cpc.dataflow import ArrayValue
from cpc.dataflow import RecordValue
import cpc.command
import cpc.util
import cmds

class GromacsError(cpc.util.CpcError):
    def __init__(self, str):
        self.str=str

class res:
    """A FE result object"""
    def __init__(self, lambda_A, lambda_B,
                 dG_kT, dG_kT_err,
                 s_A, s_A_err, s_B, s_B_err,
                 stdev, stdev_err):
        self.lambda_A=lambda_A
        self.lambda_B=lambda_B
        self.dG_kT=dG_kT
        self.dG_kT_err=dG_kT_err
        self.s_A=s_A
        self.s_A_err=s_A_err
        self.s_B=s_B
        self.s_B_err=s_B_err
        self.stdev=stdev
        self.stdev_err=stdev_err

    def setdG(self, dG, dG_err):
        self.dG=dG
        self.dG_err=dG_err

    def getValue(self):
        """Return a Value object."""
        lambda_A=FloatValue(self.lambda_A)
        lambda_B=FloatValue(self.lambda_B)
        dG=FloatValue(self.dG)
        dG_err=FloatValue(self.dG_err)
        dG_kT=FloatValue(self.dG_kT)
        dG_kT_err=FloatValue(self.dG_kT_err)
        s_A=FloatValue(self.s_A)
        s_A_err=FloatValue(self.s_A_err)
        s_B=FloatValue(self.s_B)
        s_B_err=FloatValue(self.s_B_err)
        stdev=FloatValue(self.stdev)
        stdev_err=FloatValue(self.stdev_err)

        dG_dict={}
        dG_dict["value"]=dG
        dG_dict["error"]=dG_err
        dG_kT_dict={}
        dG_kT_dict["value"]=dG_kT
        dG_kT_dict["error"]=dG_kT_err
        s_A_dict={}
        s_A_dict["value"]=s_A
        s_A_dict["error"]=s_A_err
        s_B_dict={}
        s_B_dict["value"]=s_B
        s_B_dict["error"]=s_B_err
        stdev_dict={}
        stdev_dict["value"]=stdev
        stdev_dict["error"]=stdev_err

        dG_val=RecordValue(dG_dict)
        dG_kT_val=RecordValue(dG_kT_dict)
        s_A_val=RecordValue(s_A_dict)
        s_B_val=RecordValue(s_B_dict)
        stdev_val=RecordValue(stdev_dict)

        res_dict={}
        res_dict["lambda_A"]=lambda_A
        res_dict["lambda_B"]=lambda_B
        res_dict["dG"]=dG_val
        res_dict["dG_kT"]=dG_kT_val
        res_dict["s_A"]=s_A_val
        res_dict["s_B"]=s_B_val
        res_dict["stdev"]=stdev_val
        return RecordValue(res_dict)



def g_bar(inp):
    cmdnames = cmds.GromacsCommands()
    if inp.testing():
        # if there are no inputs, we're testing wheter the command can run
        cpc.util.plugin.testCommand("%s -version" % cmdnames.bar)
        return
    fo=inp.getFunctionOutput()
    outDir=inp.getOutputDir()
    nedrfiles=len(inp.getInput('edr'))
    begin=inp.getInput('begin_time')
    end=inp.getInput('end_time')
    nBlocksMin=inp.getInput('n_blocks_min')
    nBlocksMax=inp.getInput('n_blocks_max')
    baroutname=os.path.join(outDir, "bar.xvg")
    histoutname=os.path.join(outDir, "histogram.xvg")
    #item=inp.getInput('item')
    cmdline = cmdnames.bar.split() + ["-g"]
    for i in xrange(nedrfiles):
        edrfile=inp.getInput('edr[%d]'%i)
        if edrfile is None:
            # there is an incomplete set of inputs. Return immediately
            return fo
        cmdline.append(inp.getInput('edr[%d]'%i))
    cmdline.extend( [ "-o", baroutname, "-oh", histoutname ] )
    if begin and begin > 0:
        cmdline.extend( [ "-b", "%g" % begin ] )
    if end and end > 0:
        cmdline.extend( [ "-e", "%g" % end ] )

    if nBlocksMin:
        if not nBlocksMax or nBlocksMin <= nBlocksMax:
            cmdline.extend( [ "-nbmin", "%d" % nBlocksMin ] )
    if nBlocksMax:
        if not nBlocksMin or nBlocksMin <= nBlocksMax:
            cmdline.extend( [ "-nbmax", "%d" % nBlocksMax ] )
    
    proc=subprocess.Popen(cmdline,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          cwd=inp.getOutputDir(),
                          close_fds=True)
    (stdout, stderr)=proc.communicate()
    if proc.returncode != 0:
        raise GromacsError("ERROR: %s returned %s, %s"
                           % (cmdnames.bar, stdout, stderr))
    detailedStart=re.compile(r".*lam_A[ ]*lam_B")
    finalStart=re.compile(r"Final results in kJ/mol")
    lambdaReg=re.compile(r".*lambda.*")
    pointReg=re.compile(r".*point.*")
    totalReg=re.compile(r".*total.*")
    results=[] # the array of detailed results in kT
    phases=[ "start", "detailed_results", "final" ]
    phase=0
    i=0
    #log.debug(stdout)
    for line in iter(stdout.splitlines()):
        if phase == 0:
            if detailedStart.match(line):
                phase=1
        elif phase == 1:
            if finalStart.match(line):
                phase=2
            else:
                spl=line.split()
                if len(spl) >= 9:
                    try:
                        lam_A=      float(spl[0])
                        lam_B=      float(spl[1])
                        dG=         float(spl[2])
                        dG_err=     float(spl[3])
                        s_A=        float(spl[4])
                        s_A_err=    float(spl[5])
                        s_B=        float(spl[6])
                        s_B_err=    float(spl[7])
                        stdev=      float(spl[8])
                        stdev_err=  float(spl[9])
                        rs=res(lam_A, lam_B, dG, dG_err, s_A, s_A_err, s_B,
                               s_B_err, stdev, stdev_err)
                        results.append(rs)
                    except ValueError:
                        pass
        elif phase == 2:
            spl=line.split()
            #log.debug("phase 2 line: %s, %s"%(line, spl))
            if len(spl) >= 8 and (lambdaReg.match(spl[0]) or
                                  pointReg.match(spl[0])):
                dG=float(spl[5])
                dG_err=float(spl[7])
                results[i].setdG(dG, dG_err)
                i+=1
            elif len(spl) >= 8 and totalReg.match(spl[0]):
                total_dG=float(spl[5])
                total_dG_err=float(spl[7])
    # now fill the results array
    resValArray=[]
    for rs in results:
        resValArray.append(rs.getValue())
    resVal=ArrayValue(resValArray)
    dgValDict={}
    dgValDict['value']=FloatValue(total_dG)
    dgValDict['error']=FloatValue(total_dG_err)
    dgVal=RecordValue( dgValDict )


    fo.setOut('dG', dgVal)
    fo.setOut('histogram', FileValue(histoutname))
    fo.setOut('dG_lambda', FileValue(baroutname))
    fo.setOut('bar_values', resVal)

    return fo

