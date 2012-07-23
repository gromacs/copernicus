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

class partialRes(object):
    """Holds partial results."""
    def __init__(self, name, inp):
        """name = name of input, 
           inp = the function input object"""
        self.name=name
        self.inp=inp
        self.res=[]
        dgArray=inp.getSubnetInput(name) 
        if dgArray is not None: 
            # we ignore 0 because that's equilibration
            for i in range(1, len(dgArray)):
                #sys.stderr.write('%s[%d]\n'%(name, i))
                subval=inp.getSubnetInput('%s[%d]'%(name,i))
                if subval is not None:
                    val=inp.getSubnetInput('%s[%d].value'%(name, i))
                    err=inp.getSubnetInput('%s[%d].error'%(name, i))
                    if val is not None and err is not None:
                        self.res.append( (val, err) )
        self._calcAvg()

    def _calcAvg(self):
        """Calculates an average of measurement values of subnet input array 
            'name' """
        self.mean=None
        self.err=None
        if len(self.res)<=0:
            return
        sumVal=0.
        sumInvErr=0.
        for res in self.res:
            val=res[0]
            err=res[1]
            sys.stderr.write('%g +/- %g\n'%(val, err))
            # add the weighted value
            sumVal += val/(err*err)
            # and keep track of the sum of weights
            sumInvErr += 1/(err*err)
        if len(self.res)>0:
            self.mean=sumVal/sumInvErr
            self.err=math.sqrt(1/sumInvErr)
            sys.stderr.write('Avg: %g +/- %g (N=%d)\n'%(self.mean, self.err, 
                                                       len(self.res))) 

    def getAvg(self):
        """Calculates the weighted average of measurement values"""
        return self.mean

    def getErr(self):
        """Calculates the error estimate on the weighted average of measurement 
            values"""
        return self.err

    def getRes(self):
        """Returns the array with partial results (tuples of value and error)"""
        return self.res

    def getN(self):
        """Returns the number of partial results."""
        return len(self.res)

    def updateOutput(self, pers, out, outputName, index, desc, pathInputName):
        """Update a partial output with results
           pers =  the persistence object
           out = the function output object
           outputName = the name of the partial results output item
           index = the main index to use.
           desc = a string describing the part of the free energy this is for
           pathInputName = the name of the fe_path subnetInput item
           returns: True if values have changed"""
        persName="%s_handled"%self.name
        Nhandled=pers.get(persName)
        if Nhandled is None:
            Nhandled=0
            out.setOut('%s[%d].desc'%(outputName, index), StringValue(desc))
        changedValues=False
        N=len(self.res)
        if N>0:
            # TODO: expand this when updated tags propagate correctly
            while Nhandled<N:
                changedValues=True
                out.setOut('%s[%d].parts[%d].value'%(outputName, index, 
                                                     Nhandled),
                           FloatValue(self.res[Nhandled][0]))
                out.setOut('%s[%d].parts[%d].error'%(outputName, index, 
                                                     Nhandled),
                           FloatValue(self.res[Nhandled][1]))
                # do this only once per loop:
                if Nhandled == N-1:
                    out.setOut('%s[%d].average.value'%(outputName, index),
                               FloatValue(self.getAvg()))
                    out.setOut('%s[%d].average.error'%(outputName, index),
                               FloatValue(self.getErr()))
                    # set the fe path
                    out.setOut('%s[%d].path'%(outputName, index),
                               self.inp.getSubnetInputValue("%s[%d]"%
                                                            (pathInputName, 
                                                             Nhandled)) )
                Nhandled+=1
        pers.set(persName, Nhandled)
        return changedValues

def addIteration(name, i, inp, out):
    """Add one fe calc iteration."""
    iname='iter_%s_%d'%(name, i)
    prevname='iter_%s_%d'%(name, (i-1))
    out.setSubOut('priority[%d]'%i, IntValue(3-i))
    out.addInstance('%s'%iname, 'fe_iteration')
    #out.addInstance('%s'%iname, 'fe_iteration')
    # connect shared inputs
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources'%iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp'%iname)
    out.addConnection('self:sub_out.nsteps', '%s:in.nsteps'%iname)
    out.addConnection('self:sub_out.priority[%d]'%i, '%s:in.priority'%iname)
    if i==0:
        # connect the inits
        out.addConnection('init_%s:out.path'%name, '%s:in.path'%iname )
    else:
        # connect the previous iteration
        out.addConnection('%s:out.path'%(prevname), '%s:in.path'%iname )
        #out.addConnection('iter_q_%d:out.lambdas'%(i-1), 
        #                  'iter_q_%d:in.lambdas'%i )
    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]'%(name,i))
    out.addConnection('%s:out.path'%iname, 'self:sub_in.path_%s[%d]'%(name,i))

def decouple(inp, out, relaxation_time, mult):
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
        out.setSubOut('n_lambdas_init', IntValue(16))
        # this is a rough guess, but shouldn't matter too much:
        out.setSubOut('nsteps', IntValue(20*relaxation_time) )
        out.setSubOut('nsteps_init', IntValue(relaxation_time) )

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

    res_q=partialRes('dG_q_array', inp)
    changed_q=res_q.updateOutput(pers, out, 'partial_results', 0, 
                                 'electrostatics decoupling', 'path_q')
    # lj next 
    res_lj=partialRes('dG_lj_array', inp)
    changed_lj=res_lj.updateOutput(pers, out, 'partial_results', 1,
                                   'Lennard-Jones decoupling', 'path_lj')

    precision=inp.getInput('precision')
    if precision is None:
        precision = 1
    if changed_q or changed_lj:
        totErr = 2*precision
        if not (res_lj.getAvg() is None or res_q.getAvg() is None):
            # update the totals
            totVal = res_lj.getAvg() + res_q.getAvg()
            totErr = math.sqrt( (res_lj.getErr()*res_lj.getErr() + 
                                 res_q.getErr()*res_q.getErr())/2. )
            out.setOut('delta_f.value', FloatValue(mult*totVal))
            out.setOut('delta_f.error', FloatValue(totErr))
        # now add iterations if the error is more than half the desired error
        # (in which case it's better to add iterations to the other half)
        if totErr > precision:
            # we may need to start new runs. We use precision/2 as a cutoff 
            # for each of the halves because after that is reached it makes
            # more sense to sample the other side more thoroughly.
            if changed_q and res_q.getErr() > precision/2:
                sys.stderr.write('Adding another q iteration\n')
                addIteration("q", nruns_q, inp, out)
                nruns_q += 1
            if changed_lj and res_lj.getErr() > precision/2:
                sys.stderr.write('Adding another q iteration\n')
                addIteration("lj", nruns_lj, inp, out)
                nruns_lj += 1
        else:
            sys.stderr.write("Desired precision reached.\n")
        
    pers.set('nruns_q', nruns_q)
    pers.set('nruns_lj', nruns_lj)
    pers.write()
        

