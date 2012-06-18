#!/usr/bin/env python

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
import math
import os.path
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cpc.dataflow
from cpc.dataflow import StringValue
from cpc.dataflow import FloatValue
from cpc.dataflow import IntValue
from cpc.dataflow import RecordValue
from cpc.dataflow import ArrayValue


class FEError(cpc.dataflow.ApplicationError):
    pass

def calcAvg(name, inp, out):
    """Calculate an average of measurement values of subnet input array 
        'name'
         
         returns a tuple of (value, error, N)"""
    N=0
    sumVal=0.
    sumErr=0.
    dgArray=inp.getSubnetInput(name) 
    if dgArray is not None: 
        # we ignore 0 because that's equilibration
        for i in range(1, len(dgArray)):
            #sys.stderr.write('%s[%d]\n'%(name, i))
            subval=inp.getSubnetInput('%s[%d]'%(name,i))
            #sys.stderr.write('%s[%d]: %g/%d +/- %g/%d\n'%
            #                 (name, i, sumVal, N, sumErr, N))
            if subval is not None:
                val=inp.getSubnetInput('%s[%d].value'%(name, i))
                err=inp.getSubnetInput('%s[%d].error'%(name, i))
                if val is not None and err is not None:
                    sys.stderr.write('%s[%d]: %g +/- %g\n'%(name, i, val, err))
                    sumVal += val
                    sumErr += err*err
                    N+=1
    if N>0:
        sys.stderr.write('%s: %g +/- %g (N=%d)\n'%
                         (name, sumVal/N, math.sqrt(sumErr/N), N)) 
        return ( sumVal/N, math.sqrt(sumErr/N), N)
    else:
        sys.stderr.write('N=0\n')
        return (0., 0., 0)

def addIteration(name, i, inp, out):
    """Add one fe calc iteration."""
    iname='iter_%s_%d'%(name, i)
    prevname='iter_%s_%d'%(name, (i-1))
    out.setSubOut('priority[%d]'%i, IntValue(3-i))
    out.addInstance('%s'%iname, 'fe_iteration')
    #out.addInstance('%s'%iname, 'fe_iteration')
    # connect shared inputs
    # q
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources'%iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp'%iname)
    out.addConnection('self:sub_out.nsteps', '%s:in.nsteps'%iname)
    out.addConnection('self:sub_out.priority[%d]'%i, '%s:in.priority'%iname)
    # lj
    #out.addConnection('init_lj:out.resources', 'iter_lj_%d:in.resources'%i)
    #out.addConnection('init_lj:out.grompp', 'iter_lj_%d:in.grompp'%i)
    #out.addConnection('self:sub_out.nsteps', 'iter_lj_%d:in.nsteps'%i)
    #out.addConnection('self:sub_out.priority[%d]'%i,'iter_lj_%d:in.priority'%i)
    if i==0:
        # connect the inits
        # q
        out.addConnection('init_%s:out.path'%name, '%s:in.path'%iname )
        # lj
        #out.addConnection('init_lj:out.path', 'iter_lj_%d:in.path'%i )
    else:
        # connect the previous iteration
        # q
        out.addConnection('%s:out.path'%(prevname), '%s:in.path'%iname )
        #out.addConnection('iter_q_%d:out.lambdas'%(i-1), 
        #                  'iter_q_%d:in.lambdas'%i )
        # lj
        #out.addConnection('iter_lj_%d:out.path'%(i-1), 'iter_lj_%d:in.path'%i)
        #out.addConnection('iter_lj_%d:out.lambdas'%(i-1), 
        #                  'iter_lj_%d:in.lambdas'%i)
    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]'%(name,i))
    #out.addConnection('iter_lj_%d:out.dG'%i, 'self:sub_in.dG_lj_array[%d]'%i)

def decouple(inp, out, relaxation_time):
    pers=cpc.dataflow.Persistence(os.path.join(inp.persistentDir,
                                               "persistent.dat"))

    init=pers.get('init')
    if init is None:
        init=1
        out.addInstance('init_q', 'fe_init')
        out.addInstance('init_lj', 'fe_init')
        # connect them together
        out.addConnection('init_q:out.conf_b', 'init_lj:in.conf')
        # set inputs
        out.setSubOut('endpoint_array[0]', StringValue('vdwq'))
        out.setSubOut('endpoint_array[1]', StringValue('vdw'))
        out.setSubOut('endpoint_array[2]', StringValue('none'))
        out.setSubOut('n_lambdas_init', IntValue(10))
        # this is a rough guess, but shouldn't matter too much:
        out.setSubOut('nsteps', IntValue(20*relaxation_time) )
        out.setSubOut('nsteps_init', IntValue(relaxation_time) )
        #           inp.getInput('relaxation_time')))

        out.addConnection('self:ext_in.conf', 'init_q:in.conf')
        out.addConnection('self:ext_in.grompp', 'init_q:in.grompp')
        out.addConnection('self:ext_in.resources', 'init_q:in.resources')
        out.addConnection('self:sub_out.nsteps_init', 'init_q:in.nsteps')
        out.addConnection('self:ext_in.molecule_name', 
                          'init_q:in.molecule_name')
        out.addConnection('self:sub_out.endpoint_array[0]', 'init_q:in.a')
        out.addConnection('self:sub_out.endpoint_array[1]', 'init_q:in.b')
        out.addConnection('self:sub_out.n_lambdas_init', 'init_q:in.n_lambdas')

        out.addConnection('self:ext_in.grompp', 'init_lj:in.grompp')
        out.addConnection('self:ext_in.resources', 'init_lj:in.resources')
        out.addConnection('self:sub_out.nsteps_init', 'init_lj:in.nsteps')
        out.addConnection('self:ext_in.molecule_name', 
                          'init_lj:in.molecule_name')
        out.addConnection('self:sub_out.endpoint_array[1]', 'init_lj:in.a')
        out.addConnection('self:sub_out.endpoint_array[2]', 'init_lj:in.b')
        out.addConnection('self:sub_out.n_lambdas_init', 'init_lj:in.n_lambdas')
        pers.set('init', init)

    nruns_q=pers.get('nruns_q')
    nruns_lj=pers.get('nruns_lj')
    if nruns_q is None or nruns_q==0:
        # make the first two. The first one is simply an equilibration run
        nruns_q=2
        addIteration("q", 0, inp, out)
        addIteration("q", 1, inp, out)
    if nruns_lj is None or nruns_lj==0:
        # make the first two. The first one is simply an equilibration run
        nruns_lj=2
        addIteration("lj", 0, inp, out)
        addIteration("lj", 1, inp, out)

    dgOutputsHandled=pers.get('dg_outputs_handled')
    # read in the dG inputs.
    changedValues=[False, False]

    totVals=[]
    totErrs=[]
    end=False
    # q first
    (val, err, N) = calcAvg('dG_q_array', inp, out)
    dg_q_handled=pers.get('dg_q_handled')
    if N>0:
        totVals.append(  ( val, err ) )
        if dg_q_handled is None or dg_q_handled<N:
            dg_q_handled=N
            changedValues[0]=True
    else:
        dg_q_handled=0
    pers.set('dg_q_handled', dg_q_handled)
    # lj next first
    (val, err, N) = calcAvg('dG_lj_array', inp, out)
    dg_l_handled=pers.get('dg_lj_handled')
    if N>0:
        totVals.append(  ( val, err ) )
        if dg_l_handled is None or dg_q_handled<N:
            dg_l_handled=N
            changedValues[1]=True
    pers.set('dg_lj_handled', dg_l_handled)

    precision=inp.getInput('precision')
    if precision is None:
        precision = 1
    if changedValues[0] or changedValues[1]:
        if len(totVals) == 2:
            totVal=0.
            totErr=0.
            for val, err in totVals:
                totVal += val
                totErr += err*err
            #totVal /= len(totVals)
            totErr = math.sqrt(totErr/len(totVals))
            out.setOut('delta_f.value', FloatValue(totVal))
            out.setOut('delta_f.error', FloatValue(totErr))
            #precision=inp.getInput('precision')
            #if totErr > precision:
                #addIteration(inp, out, nruns)
            #    nruns += 1
        # now add iterations if the error is more than half the desired error
        # (in which case it's better to add iterations to the other half)
        if changedValues[0]:
            if totVals[0][1] > precision/2:
                sys.stderr.write('Adding another q iteration\n')
                addIteration("q", nruns_q, inp, out)
                nruns_q += 1
        if changedValues[1]:
            if totVals[1][1] > precision/2:
                sys.stderr.write('Adding another lj iteration\n')
                addIteration("lj", nruns_lj, inp, out)
                nruns_lj += 1
        
    pers.set('nruns_q', nruns_q)
    pers.set('nruns_lj', nruns_lj)
    pers.write()
        

