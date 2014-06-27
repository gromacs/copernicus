#!/usr/bin/env python

# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2014, Sander Pronk, Iman Pouya, Magnus Lundborg Erik Lindahl,
# and others.
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
from cpc.dataflow import BoolValue


class FEError(cpc.dataflow.ApplicationError):
    pass

class partialRes(object):
    """Holds partial results."""
    def __init__(self, name, inp, out, pers, optimizeLambdas):
        """name = name of input,
           inp = the function input object"""
        self.name=name
        self.res=[]
        self.pers=pers
        self.inp=inp
        self.out=out
        self.mean=None
        self.err=None
        self.dGArray=inp.getSubnetInput(name)
        self.updated=False
        if self.dGArray is not None:
            nHandled = pers.get('%s_handled' % name) or 0
            arrayLen=len(self.dGArray)
            if nHandled < arrayLen:
                self.updated=True

            sys.stderr.write('%s: %d entries in dGArray\n' % (name, arrayLen))

            if '_lj_' in name:
                tp = 'lj'
                last_equil=pers.get('last_equil_lj') or 0
            elif '_q_' in name:
                tp = 'q'
                last_equil=pers.get('last_equil_q') or 0
            else:
                tp = ''
                doneReoptimization = None
                last_equil=0


            lastAdded = last_equil
            # Add results to the results list. Only add runs
            # after which we optimize lambdas - otherwise we try
            # to keep the list of energy files and run g_bar
            # over more or them. The last value is added anyhow.
            for i in range(last_equil + 1, arrayLen):
                if tp:
                    doneReoptimization = checkOptimization(tp, i, inp)
                    sys.stderr.write('Done reoptimization: %s\n' % doneReoptimization)
                if doneReoptimization or i == arrayLen - 1:
                    subval=inp.getSubnetInput('%s[%d]'%(name,i))
                    #sys.stderr.write('subval: %s, i: %s, arrayLen: %s\n' % (subval, i, arrayLen))
                    if subval is not None:
                        val=inp.getSubnetInput('%s[%d].value'%(name, i))
                        err=inp.getSubnetInput('%s[%d].error'%(name, i))
                        sys.stderr.write('val: %s, err: %s\n' % (val, err))
                        if val is not None and err is not None:
                            updated = inp.getSubnetInputValue('%s[%d].value'%(name, i)).isUpdated()
                            sys.stderr.write('Updated: %s\n' % updated)
                            if updated:
                                self.updated = True
                            sys.stderr.write('Appending val and err: %g, %g.\n' % (val, err))
                            self.res.append( (val, err) )
                            lastAdded = i

                        elif i == arrayLen - 1 and i > 1 and i-1 != lastAdded:
                            val=inp.getSubnetInput('%s[%d].value'%(name, i-1))
                            err=inp.getSubnetInput('%s[%d].error'%(name, i-1))
                            sys.stderr.write('i: %s val: %s, err: %s\n' % (i, val, err))
                            if val is not None and err is not None:
                                updated = inp.getSubnetInputValue('%s[%d].value'%(name, i-1)).isUpdated()
                                sys.stderr.write('Updated: %s\n' % updated)
                                if updated:
                                    self.updated = True
                                sys.stderr.write('Appending val and err: %g, %g.\n' % (val, err))
                                self.res.append( (val, err) )

        pers.set('%s_handled'%self.name, arrayLen)

        self._calcAvg()

    def _calcAvg(self):
        """Calculates an average of measurement values of subnet input array
            'name' """
        self.mean=None
        self.err=None
        if len(self.res) == 0:
            return
        sumVal=0.
        sumInvErr=0.
        for res in self.res:
            val=res[0]
            err=res[1]
            sys.stderr.write('%g +/- %g\n'%(val, err))
            try:
                # add the weighted value
                sumVal += val/(err*err)
                # and keep track of the sum of weights
                sumInvErr += 1/(err*err)
            except ZeroDivisionError:
                sumVal += val/0.00000001
                sumInvErr += 1/0.00000001

        sys.stderr.write('Results len: %d\n' % len(self.res))

        if len(self.res)>0:
            self.mean=sumVal/sumInvErr
            self.err=math.sqrt(1/sumInvErr)
            sys.stderr.write('Avg: %g +/- %g (N=%d)\n'%(self.mean, self.err,
                                                       len(self.res)))

    def getAvg(self):
        """Calculates the weighted average of measurement values"""
        return self.mean

    def getErr(self):
        """Calculates the error estimate on the of measurement values"""
        return self.err

    def getRes(self):
        """Returns the array with partial results (tuples of value and error)"""
        return self.res

    def getN(self):
        """Returns the number of partial results."""
        return len(self.res)

    def getNdGArray(self):
        """Returns the number of dG values from the simulations."""
        return len(self.dGArray)

    def getUpdated(self):
        """Returns True is the values have changed since last iteration"""
        return self.updated

    def updateOutput(self, outputName, index, desc, pathInputName):
        """Update a partial output with results
           out = the function output object
           outputName = the name of the partial results output item
           index = the main index to use.
           desc = a string describing the part of the free energy this is for
           pathInputName = the name of the fe_path subnetInput item
           returns: True if values have changed"""

        if not self.updated:
            return

        inp=self.inp
        out=self.out

        nRes=len(self.res)

        arrayLen = len(self.dGArray)

        if nRes>0:
            # TODO: expand this when updated tags propagate correctly
            for i in range(nRes):
                #oldVal=inp.getOutput('%s[%d].parts[%d].value'%(outputName, index, i))
                #oldErr=inp.getOutput('%s[%d].parts[%d].error'%(outputName, index, i))

                #if oldVal and oldVal != FloatValue(self.res[i][0]) and\
                #oldErr and oldErr != FloatValue(self.res[i][1]):
                out.setOut('%s[%d].parts[%d].value'%(outputName, index, i),
                        FloatValue(self.res[i][0]))
                out.setOut('%s[%d].parts[%d].error'%(outputName, index, i),
                        FloatValue(self.res[i][1]))

            val=self.getAvg()
            err=self.getErr()
            sys.stderr.write('%s: nRes: %d %g %g\n' % (outputName, nRes, val or 0, err or 0))
            pathInput = inp.getSubnetInputValue("%s[%d]" % (pathInputName, arrayLen-1))
            #sys.stderr.write('pathInputName: %s[%d]. pathInput: %s\n' % (pathInputName, arrayLen-1, pathInput.get()))
            out.setOut('%s[%d].average.value'%(outputName, index),
                    FloatValue(val))
            out.setOut('%s[%d].average.error'%(outputName, index),
                    FloatValue(err))
            # set the fe path
            if pathInput:
                out.setOut('%s[%d].path'%(outputName, index), pathInput)

def checkOptimization(name, index, inp):
    """ Check if run with specified index was reoptimized. """

    opt=inp.getSubnetInput('done_reoptimization_list_%s[%d]' % (name, index))
    sys.stderr.write('done_reoptimization_list_%s[%d] %s\n'  % (name, index, opt))

    return opt

def getNOutputs(out, name):

    outValues = out.outputs
    sys.stderr.write('nOutValues: %s, %s\n' % (len(outValues), outValues))
    sys.stderr.write('Searching for: %s\n' % name)
    for outValue in outValues:
        sys.stderr.write('%s, name: %s\n' % (outValue, outValue.name))
        if outValue.name == name:
            sys.stderr.write('Found %s. %s\n' % (name, outValue))
            break
    else:
        return None

    return len(outValue)

def addEquilibration(name, i, inp, out, pers, optimize):
    """Add one fe calc iteration performing only equilibration."""

    last_equil=pers.get('last_equil_%s' % name)

    iname='equil_%s_%d'%(name, i)
    if i-1 == last_equil:
        prevname='equil_%s_%d'%(name, (i-1))
    else:
        prevname='iter_%s_%d'%(name, (i-1))

    if i > 0:
        lambdas = inp.getSubnetInput('path_%s[%d].lambdas' % (name, i-1)) or []
        nLambdas = len(lambdas)

        # The previous run must be finished
        # before continuing - otherwise e.g. edr files won't be included
        # in the analyses.
        if not nLambdas:
            sys.stderr.write('%s, fail 1\n' % iname)
            return False
        for j in range(nLambdas):
            conf = inp.getSubnetInput('path_%s[%d].lambdas[%d].conf' % (name, i-1, j))
            if not conf:
                sys.stderr.write('%s, fail 2\n' % iname)
                return False
        doneReoptimization = checkOptimization(name, i-1, inp)
        if doneReoptimization == None:
            sys.stderr.write('%s, fail 3\n' % iname)
            return False

    pers.set('last_equil_%s' % name, i)

    priority = IntValue(3-i)
    out.addInstance('%s'%iname, 'fe_iteration')
    # connect shared inputs
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources'%iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp'%iname)
    out.addConnection('self:sub_out.nsteps_equil', '%s:in.nsteps'%iname)
    out.addConnection(None, '%s:in.priority'%iname, priority)
    if i==0:
        # connect the inits
        out.addConnection('init_%s:out.path'%name, '%s:in.path'%iname )
    else:
        # connect the previous iteration
        out.addConnection('%s:out.path'%(prevname), '%s:in.path'%iname )

    doOptimize=BoolValue(optimize)
    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]'%(name,i))
    out.addConnection('%s:out.path'%iname, 'self:sub_in.path_%s[%d]'%(name,i))
    out.addConnection('self:ext_in.stddev_spacing',
                      '%s:in.stddev_spacing'%iname)
    out.addConnection('self:ext_in.dl_power',
                      '%s:in.dl_power' % iname)
    out.addConnection('self:ext_in.n_blocks_min',
                      '%s:in.n_blocks_min'%iname)
    out.addConnection('self:ext_in.n_blocks_max',
                      '%s:in.n_blocks_max'%iname)
    out.addConnection(None, '%s:in.optimize_lambdas'%iname, doOptimize)
    out.addConnection('self:ext_in.optimization_tolerance', '%s:in.optimization_tolerance'%iname)
    out.addConnection('%s:out.done_reoptimization'%iname, 'self:sub_in.done_reoptimization_list_%s[%d]' % (name, i))

    return True

def addIteration(name, i, initStep, inp, out, pers, optimize, isOptIter=False):
    """Add one fe calc iteration."""

    last_equil=pers.get('last_equil_%s' % name)

    iname='iter_%s_%d'%(name, i)
    if i-1 == last_equil:
        prevname='equil_%s_%d'%(name, (i-1))
    else:
        prevname='iter_%s_%d'%(name, (i-1))

    lambdas = inp.getSubnetInput('path_%s[%d].lambdas' % (name, i-1)) or []
    nLambdas = len(lambdas)

    # The previous run must be finished
    # before continuing - otherwise e.g. edr files won't be included
    # in the analyses.
    if not nLambdas:
        return False
    for j in range(nLambdas):
        conf = inp.getSubnetInput('path_%s[%d].lambdas[%d].conf' % (name, i-1, j))
        if not conf:
            sys.stderr.write('conf %d not available\n' % j)
            return False
    doneReoptimization = checkOptimization(name, i-1, inp)
    if doneReoptimization == None:
        sys.stderr.write('Previous run not set done_reoptimization flag\n')
        return False

    priority = IntValue(3-i)
    #out.setSubOut('priority[%d]'%i, IntValue(3-i))
    sys.stderr.write('Adding instance %s\n' % iname)
    out.addInstance('%s'%iname, 'fe_iteration')
    # connect shared inputs
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources'%iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp'%iname)
    if isOptIter:
        out.addConnection('self:sub_out.nsteps_optiter', '%s:in.nsteps'%iname)
    else:
        out.addConnection('self:sub_out.nsteps', '%s:in.nsteps'%iname)
    out.addConnection(None, '%s:in.priority'%iname, priority)
    if i==1:
        # connect the equil
        out.addConnection('equil_%s_%d:out.path'% (name, i-1), '%s:in.path'%iname )
    else:
        # connect the previous iteration
        out.addConnection('%s:out.path'%(prevname), '%s:in.path'%iname )
    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]'%(name,i))

    out.addConnection('%s:out.path'%iname, 'self:sub_in.path_%s[%d]'%(name,i))

    out.addConnection('self:ext_in.stddev_spacing',
                      '%s:in.stddev_spacing'%iname)
    out.addConnection('self:ext_in.dl_power',
                      '%s:in.dl_power' % iname)
    out.addConnection('self:ext_in.n_blocks_min',
                      '%s:in.n_blocks_min'%iname)
    out.addConnection('self:ext_in.n_blocks_max',
                      '%s:in.n_blocks_max'%iname)
    out.addConnection(None, '%s:in.optimize_lambdas'%iname, BoolValue(optimize))
    out.addConnection('self:ext_in.lambdas_all_to_all', '%s:in.lambdas_all_to_all'%iname)
    out.addConnection('self:ext_in.optimization_tolerance', '%s:in.optimization_tolerance'%iname)
    out.addConnection('%s:out.done_reoptimization'%iname, 'self:sub_in.done_reoptimization_list_%s[%d]' % (name, i))

    out.addConnection(None, '%s:in.init_step'% iname, IntValue(initStep))

    nEdrFiles = 0
    for j in reversed(range(last_equil + 1, i)):
        # n_lambdas_X is set after additional lambda points are added. The number of lambda points with edr files are
        # determined from the run before.
        run='iter_%s_%d' % (name, j)
        doneReoptimization = checkOptimization(name, j, inp)
        if doneReoptimization:
            break
        lambdas = inp.getSubnetInput('path_%s[%d].lambdas' % (name, j)) or []
        prevNLambdas = len(lambdas)
        sys.stderr.write('%s lambdas\n' % nLambdas)
        if prevNLambdas != nLambdas:
            break
        for k in xrange(nLambdas):
            #sys.stderr.write('Adding connection: %s:out.own_edr_files[%d] to %s:in.edr_files[%d]\n' % (run, k, iname, nEdrFiles))
            out.addConnection('%s:out.own_edr_files[%d]' % (run, k), '%s:in.edr_files[%d]'%(iname, nEdrFiles))
            nEdrFiles += 1

    return True

def processEdrFiles(inp, out, pers, name, nruns):

    last_equil=pers.get('last_equil_%s' % name) or 0
    n=pers.get('n_process_%s' % name) or 0
    n += 1

    out.addInstance('process_edr_%s_%d' % (name, n), 'fe_process_edr')
    #nLambdas = pers.get('n_lambdas_%s[%d]' % (name, 1)) or 0
    cnt = 0
    for i in xrange(last_equil + 1, nruns):
        # n_lambdas_X is set after additional lambda points are added. The number of lambda points with edr files are
        # determined from the run before.
        run='iter_%s_%d' % (name, i)
        #sys.stderr.write('Setting up process_edr: run: %s nLambdas: %d\n' % (run, nLambdas))
        out.addConnection('%s:out.own_edr_files' % run,
                            'process_edr_%s_%d:in.edr_files_collection[%d]' % (name, n, cnt))
        cnt += 1

    out.addConnection('process_edr_%s_%d:out.edr_files' % (name, n),
                      'self:ext_out.edr_files_%s' % name)
    pers.set('n_process_%s' % name, n)


def decouple(inp, out, relaxation_time, mult, n_lambdas_init=16):
    pers=cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                               "persistent.dat"))
    init=pers.get('init')
    iterationStep = 20*relaxation_time

    inpOptimize=inp.getInput('optimize_lambdas')
    if inpOptimize is not None:
        optimizeLambdas=inpOptimize
    else:
        optimizeLambdas=True
    lambdas_q=inp.getInput('lambdas_q')
    lambdas_lj=inp.getInput('lambdas_lj')
    if lambdas_q or lambdas_lj:
        optimizeLambdas=False

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
        out.setSubOut('n_lambdas_init', IntValue(n_lambdas_init))
        # this is a rough guess, but shouldn't matter too much:
        out.setSubOut('nsteps', IntValue(iterationStep) )
        # If we optimize lambdas we start with an equilibration with the specified
        # number of lambda points, after which we optimize the lambda distribution.
        # Then we do another equilibration with the new lambda distribution.
        # This means the equilibration length in total will be the same regardless
        # if we optimize or not.
        if optimizeLambdas:
            out.setSubOut('nsteps_equil', IntValue(5*relaxation_time) )
            out.setSubOut('nsteps_optiter', IntValue(iterationStep/5))
        else:
            out.setSubOut('nsteps_equil', IntValue(10*relaxation_time) )

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
        out.addConnection('self:ext_in.lambdas_q', 'init_q:in.lambdas')

        out.addConnection('self:ext_in.grompp', 'init_lj:in.grompp')
        out.addConnection('self:ext_in.resources', 'init_lj:in.resources')
        out.addConnection('self:sub_out.nsteps_init', 'init_lj:in.nsteps')
        out.addConnection('self:ext_in.molecule_name',
                          'init_lj:in.molecule_name')
        out.addConnection('self:sub_out.endpoint_array[1]', 'init_lj:in.a')
        out.addConnection('self:sub_out.endpoint_array[2]', 'init_lj:in.b')
        out.addConnection('self:sub_out.n_lambdas_init', 'init_lj:in.n_lambdas')
        out.addConnection('self:ext_in.lambdas_lj', 'init_lj:in.lambdas')
        pers.set('init', init)

    nruns_q=pers.get('nruns_q') or 0
    nruns_lj=pers.get('nruns_lj') or 0

    if nruns_q==0:
        if addEquilibration("q", 0, inp, out, pers, optimizeLambdas):
            nruns_q=1
    elif optimizeLambdas:
        if nruns_q==1:
            if addEquilibration("q", 1, inp, out, pers, optimizeLambdas):
                nruns_q+=1
            else:
                sys.stderr.write("Failed adding q equilibration\n")
        # Add two short iterations of optimizations. The optimization iterations
        # are short to reduce the risk of throwing away much data.
        elif nruns_q<4:
            if addIteration("q", nruns_q, (nruns_q - 2) * iterationStep/2, inp, out, pers, optimizeLambdas, isOptIter=True):
                nruns_q+=1
            else:
                sys.stderr.write("Failed adding short q optimization iteration\n")
        elif nruns_q==4:
            if addIteration("q", nruns_q, iterationStep, inp, out, pers, optimizeLambdas):
                nruns_q+=1
            else:
                sys.stderr.write("Failed adding q iteration\n")
    elif nruns_q==1:
        if addIteration("q", 1, 0, inp, out, pers, optimizeLambdas):
            nruns_q+=1
        else:
            sys.stderr.write("Failed adding q iteration\n")

    if nruns_lj==0:
        if addEquilibration("lj", 0, inp, out, pers, optimizeLambdas):
            nruns_lj=1
    elif optimizeLambdas:
        if nruns_lj==1:
            if addEquilibration("lj", 1, inp, out, pers, optimizeLambdas):
                nruns_lj+=1
            else:
                sys.stderr.write("Failed adding lj equilibration\n")
        # Add two short iterations of optimizations. The optimization iterations
        # are short to reduce the risk of throwing away much data.
        elif nruns_lj<4:
            if addIteration("lj", nruns_lj, (nruns_lj - 2) * iterationStep/2, inp, out, pers, optimizeLambdas, isOptIter=True):
                nruns_lj+=1
            else:
                sys.stderr.write("Failed adding short lj optimization iteration\n")
        elif nruns_lj==4:
            if addIteration("lj", nruns_lj, iterationStep, inp, out, pers, optimizeLambdas):
                nruns_lj+=1
            else:
                sys.stderr.write("Failed adding lj iteration\n")
    elif nruns_lj==1:
        if addIteration("lj", 1, 0, inp, out, pers, optimizeLambdas):
            nruns_lj+=1
        else:
            sys.stderr.write("Failed adding lj iteration\n")

    res_q=partialRes('dG_q_array', inp, out, pers, optimizeLambdas)
    changed_q=res_q.getUpdated()
    res_q.updateOutput('partial_results', 0,
                       'electrostatics decoupling', 'path_q')
    # lj next
    res_lj=partialRes('dG_lj_array', inp, out, pers, optimizeLambdas)
    changed_lj=res_lj.getUpdated()
    res_lj.updateOutput('partial_results', 1,
                        'Lennard-Jones decoupling', 'path_lj')

    sys.stderr.write('q: %f +- %f. lj: %f +- %f\n' % (res_q.getAvg() or 0, res_q.getErr() or -1, res_lj.getAvg() or 0, res_lj.getErr() or -1))

    sys.stderr.write('Changed Q: %s, Changed LJ: %s\n' % (changed_q, changed_lj))

    precision=inp.getInput('precision')
    minIterations=inp.getInput('min_iterations')
    if optimizeLambdas and minIterations:
        minIterations += 4
    if precision is None:
        precision = 1

    changedPrecision = inp.getInputValue('precision').isUpdated()
    changedMinIterations = inp.getInputValue('min_iterations').isUpdated()

    sys.stderr.write('precision: %s. min_iterations: %s\n' % (precision, minIterations))
    sys.stderr.write('precision updated: %s. min_iterations updated: %s\n' %(changedPrecision, changedMinIterations))

    if changed_q or changed_lj or changedPrecision or changedMinIterations:
        last_equil_q=pers.get('last_equil_q') or 0
        last_equil_lj=pers.get('last_equil_lj') or 0
        totErr = 2*precision
        qAvg = res_q.getAvg()
        ljAvg = res_lj.getAvg()
        qErr = res_q.getErr()
        ljErr = res_lj.getErr()
        sys.stderr.write('qAvg = %s, ljAvg = %s, qErr = %s, ljErr = %s\n' % (qAvg, ljAvg, qErr, ljErr))
        if not (qAvg is None or ljAvg is None):
            # update the totals
            totVal = qAvg + ljAvg
            totErr = math.sqrt(ljErr*ljErr + qErr*qErr)
            out.setOut('delta_f.value', FloatValue(mult*totVal))
            out.setOut('delta_f.error', FloatValue(totErr))
        # now add iterations if the error is more than half the desired error
        if totErr > precision or (minIterations and \
           ((nruns_lj - last_equil_lj <= minIterations) or \
            (nruns_q - last_equil_q <= minIterations))):
            sys.stderr.write('totErr > precision. nruns_q=%d nruns_lj=%d\n' % (nruns_q, nruns_lj))
            # we may need to start new runs. We use 0.4 * precision as a cutoff
            # for each of the halves because after that is reached it makes
            # more sense to sample the other side more thoroughly.
            if (changed_q or changedPrecision or changedMinIterations) and \
                ((minIterations and nruns_q - last_equil_q <= minIterations) or qErr > 0.4 * precision):
                if optimizeLambdas:
                    initStep = iterationStep * max(0, (nruns_q-(last_equil_q+3)))
                else:
                    initStep = iterationStep * max(0, (nruns_q-(last_equil_q+1)))
                if checkOptimization('q', nruns_q-1, inp):
                    sys.stderr.write('Last run had lambdas reoptimized.\n')
                sys.stderr.write('Adding another q iteration. nruns_q=%d nruns_lj=%d\n' % (nruns_q, nruns_lj))
                if addIteration('q', nruns_q, initStep, inp, out, pers, optimizeLambdas):
                    nruns_q += 1
                else:
                    sys.stderr.write("Failed adding q iteration\n")
                    nHandled = pers.get('dG_q_array_handled') or 1
                    nHandled -= 1
                    pers.set('dG_q_array_handled', nHandled)

            if (changed_lj or changedPrecision or changedMinIterations) and \
                ((minIterations and nruns_lj - last_equil_lj <= minIterations) or ljErr > 0.4 * precision):
                if optimizeLambdas:
                    initStep = iterationStep * max(0, (nruns_lj-(last_equil_lj+3)))
                else:
                    initStep = iterationStep * max(0, (nruns_lj-(last_equil_lj+1)))
                if checkOptimization('lj', nruns_lj-1, inp):
                    sys.stderr.write('Last run had lambdas reoptimized.\n')
                sys.stderr.write('Adding another lj iteration. nruns_q=%d nruns_lj=%d\n' % (nruns_q, nruns_lj))
                if addIteration('lj', nruns_lj, initStep, inp, out, pers, optimizeLambdas):
                    nruns_lj += 1
                else:
                    sys.stderr.write("Failed adding lj iteration\n")
                    nHandled = pers.get('dG_lj_array_handled') or 1
                    nHandled -= 1
                    pers.set('dG_lj_array_handled', nHandled)
        else:
            sys.stderr.write('q: %d / %d. lj: %d / %d\n' % (nruns_q, res_q.getN(), nruns_lj, res_lj.getN()))
            if res_q.getNdGArray() >= nruns_q and res_lj.getNdGArray() >= nruns_lj:
                sys.stderr.write('Desired precision reached.\n')
                # If not optimizing lambdas make a concatenated edr file of all runs.
                if not optimizeLambdas and inp.getInput('concatenate_edr_files'):
                    if changed_q:
                        processEdrFiles(inp, out, pers, 'q', nruns_q)
                    if changed_lj:
                        processEdrFiles(inp, out, pers, 'lj', nruns_lj)

    pers.set('nruns_q', nruns_q)
    pers.set('nruns_lj', nruns_lj)
    pers.write()
    sys.stderr.write('Writing persistence\n')


