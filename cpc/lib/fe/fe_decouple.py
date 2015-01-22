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
from cpc.dataflow import BoolValue


class FEError(cpc.dataflow.ApplicationError):
    pass

class partialRes(object):
    """Holds partial results."""
    def __init__(self, name, inp, out, pers):
        """name = name of input,
           inp = the function input object"""
        self.name = name
        self.res = []
        self.pers = pers
        self.inp = inp
        self.out = out
        self.mean = None
        self.err = None
        self.dGArray = inp.getSubnetInput(name)
        self.updated = False
        if self.dGArray is not None:
            nHandled = pers.get('%s_handled' % name) or 0
            arrayLen = len(self.dGArray)
            #if nHandled < arrayLen:
                #self.updated = True

            sys.stderr.write('%s: %d entries in dGArray\n' % (name, arrayLen))

            if '_lj_' in name:
                tp = 'lj'
                last_equil = pers.get('last_equil_lj') or 0
            elif '_q_' in name:
                tp = 'q'
                last_equil = pers.get('last_equil_q') or 0
            elif '_ljq_' in name:
                tp = 'ljq'
                last_equil = pers.get('last_equil_ljq') or 0
            else:
                tp = ''
                doneReoptimization = None
                last_equil = 0


            lastAdded = last_equil
            # Add results to the results list. Only add runs
            # after which we optimize lambdas - otherwise we try
            # to keep the list of energy files and run g_bar
            # over more or them. The last value is added anyhow.
            for i in range(last_equil + 1, arrayLen):
                if tp:
                    doneReoptimization = checkOptimization(tp, i, inp)
                if doneReoptimization or i == arrayLen - 1:
                    subval = inp.getSubnetInput('%s[%d]'%(name,i))
                    #sys.stderr.write('subval: %s, i: %s, arrayLen: %s\n' % (subval, i, arrayLen))
                    if subval is not None:
                        val = inp.getSubnetInput('%s[%d].value'%(name, i))
                        err = inp.getSubnetInput('%s[%d].error'%(name, i))
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
        self.mean = None
        self.err = None
        if len(self.res) == 0:
            return
        sumVal = 0.
        sumInvErr = 0.
        for res in self.res:
            val = res[0]
            err = res[1]
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
            self.mean = sumVal/sumInvErr
            self.err = math.sqrt(1/sumInvErr)
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

        inp = self.inp
        out = self.out

        nRes = len(self.res)

        arrayLen = len(self.dGArray)

        if nRes > 0:
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

            val = self.getAvg()
            err = self.getErr()
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

    opt = inp.getSubnetInput('done_reoptimization_list_%s[%d]' % (name, index))
    #sys.stderr.write('done_reoptimization_list_%s[%d] %s\n'  % (name, index, opt))

    return opt

def addEquilibration(name, i, inp, out, pers, optimize):
    """Add one fe calc iteration performing only equilibration."""

    last_equil = pers.get('last_equil_%s' % name)

    iname = 'equil_%s_%d' % (name, i)
    if i-1 == last_equil:
        prevname = 'equil_%s_%d' % (name, (i-1))
    else:
        prevname = 'iter_%s_%d' % (name, (i-1))

    if i > 0:
        lambdas = inp.getSubnetInput('path_%s[%d].lambdas' % (name, i-1)) or []
        nLambdas = len(lambdas)

        # The previous run must be finished
        # before continuing - otherwise e.g. edr files won't be included
        # in the analyses.
        if not nLambdas:
            #sys.stderr.write('%s, fail 1\n' % iname)
            return False
        for j in range(nLambdas):
            conf = inp.getSubnetInput('path_%s[%d].lambdas[%d].conf' % (name, i-1, j))
            if not conf:
                #sys.stderr.write('%s, fail 2\n' % iname)
                return False
        doneReoptimization = checkOptimization(name, i-1, inp)
        if doneReoptimization == None:
            #sys.stderr.write('%s, fail 3\n' % iname)
            return False

    pers.set('last_equil_%s' % name, i)

    priority = IntValue(3-i)
    out.addInstance('%s' % iname, 'fe_iteration')
    # connect shared inputs
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources' % iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp' % iname)
    out.addConnection('self:sub_out.nsteps_equil', '%s:in.nsteps' % iname)
    out.addConnection(None, '%s:in.priority'%iname, priority)
    if i == 0:
        # connect the inits
        out.addConnection('init_%s:out.path'%name, '%s:in.path' % iname)
    else:
        # connect the previous iteration
        out.addConnection('%s:out.path'%(prevname), '%s:in.path' % iname)

    if name == 'q':
        out.addConnection(None, '%s:in.sc_alpha' % iname, FloatValue(0))
    else:
        out.addConnection('self:ext_in.sc_alpha', '%s:in.sc_alpha' % iname)

    doOptimize = BoolValue(optimize)
    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]'%(name, i))
    out.addConnection('%s:out.path'%iname, 'self:sub_in.path_%s[%d]'%(name, i))
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

    last_equil = pers.get('last_equil_%s' % name)

    iname = 'iter_%s_%d' % (name, i)
    if i-1 == last_equil:
        prevname = 'equil_%s_%d' % (name, (i-1))
    else:
        prevname = 'iter_%s_%d' % (name, (i-1))

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
    out.addConnection('init_%s:out.resources'%name, '%s:in.resources' % iname)
    out.addConnection('init_%s:out.grompp'%name, '%s:in.grompp' % iname)
    if isOptIter:
        out.addConnection('self:sub_out.nsteps_optiter', '%s:in.nsteps' % iname)
    else:
        out.addConnection('self:sub_out.nsteps', '%s:in.nsteps' % iname)
    out.addConnection(None, '%s:in.priority' % iname, priority)
    if i == 1:
        # connect the equil
        out.addConnection('equil_%s_%d:out.path'% (name, i-1), '%s:in.path' % iname)
    else:
        # connect the previous iteration
        out.addConnection('%s:out.path'%(prevname), '%s:in.path' % iname)

    if name == 'q':
        out.addConnection(None, '%s:in.sc_alpha' % iname, FloatValue(0))
    else:
        out.addConnection('self:ext_in.sc_alpha', '%s:in.sc_alpha' % iname)

    # connect the outputs
    out.addConnection('%s:out.dG'%iname, 'self:sub_in.dG_%s_array[%d]' % (name, i))

    out.addConnection('%s:out.path'%iname, 'self:sub_in.path_%s[%d]' % (name, i))

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
        run = 'iter_%s_%d' % (name, j)
        doneReoptimization = checkOptimization(name, j, inp)
        if doneReoptimization:
            break
        lambdas = inp.getSubnetInput('path_%s[%d].lambdas' % (name, j)) or []
        prevNLambdas = len(lambdas)
        #sys.stderr.write('%s lambdas\n' % nLambdas)
        if prevNLambdas != nLambdas:
            break
        for k in xrange(nLambdas):
            #sys.stderr.write('Adding connection: %s:out.own_edr_files[%d] to %s:in.edr_files[%d]\n' % (run, k, iname, nEdrFiles))
            out.addConnection('%s:out.own_edr_files[%d]' % (run, k), '%s:in.edr_files[%d]'%(iname, nEdrFiles))
            nEdrFiles += 1

    return True

def processEdrFiles(out, pers, name, nruns):

    last_equil = pers.get('last_equil_%s' % name) or 0
    n = pers.get('n_process_%s' % name) or 0
    n += 1

    out.addInstance('process_edr_%s_%d' % (name, n), 'fe_process_edr')
    #nLambdas = pers.get('n_lambdas_%s[%d]' % (name, 1)) or 0
    cnt = 0
    for i in xrange(last_equil + 1, nruns):
        # n_lambdas_X is set after additional lambda points are added. The number of lambda points with edr files are
        # determined from the run before.
        run = 'iter_%s_%d' % (name, i)
        #sys.stderr.write('Setting up process_edr: run: %s nLambdas: %d\n' % (run, nLambdas))
        out.addConnection('%s:out.own_edr_files' % run,
                            'process_edr_%s_%d:in.edr_files_collection[%d]' % (name, n, cnt))
        cnt += 1

    out.addConnection('process_edr_%s_%d:out.edr_files' % (name, n),
                      'self:ext_out.edr_files_%s' % name)
    pers.set('n_process_%s' % name, n)


def decouple(inp, out, relaxation_time, mult, n_lambdas_init=16):
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')
    iterationStep = 20*relaxation_time

    inpOptimize = inp.getInput('optimize_lambdas')
    if inpOptimize is not None:
        optimizeLambdas = inpOptimize
    else:
        optimizeLambdas = True

    nruns = dict()
    changed = dict()
    res = dict()
    avg = dict()
    err = dict()
    last_equil = dict()
    tooFewIterations = dict()

    inpSimDecoupl = inp.getInput('simultaneous_decoupling')
    if inpSimDecoupl is not None:
        simultaneousDecoupling = inpSimDecoupl
    else:
        simultaneousDecoupling = False

    if simultaneousDecoupling:
        lambdas_ljq = inp.getInput('lambdas_ljq')
        if lambdas_ljq:
            optimizeLambdas = False
    else:
        lambdas_q = inp.getInput('lambdas_q')
        lambdas_lj = inp.getInput('lambdas_lj')
        if lambdas_q or lambdas_lj:
            optimizeLambdas = False

    if simultaneousDecoupling:
        types = ['ljq']
    else:
        types = ['q', 'lj']

    if init is None:
        init = 1

        for tp in types:
            out.addInstance('init_%s' % tp, 'fe_init')

        if simultaneousDecoupling:
            out.setSubOut('endpoint_array[0]', StringValue('vdwq'))
            out.setSubOut('endpoint_array[1]', StringValue('none'))
        else:
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
            out.setSubOut('nsteps_optiter', IntValue(iterationStep/2))
        else:
            out.setSubOut('nsteps_equil', IntValue(10*relaxation_time) )

        out.setSubOut('nsteps_init', IntValue(relaxation_time) )

        for tp in types:
            if tp != 'lj':
                out.addConnection('self:ext_in.conf', 'init_%s:in.conf' % tp)
            out.addConnection('self:ext_in.grompp', 'init_%s:in.grompp' % tp)
            out.addConnection('self:ext_in.resources', 'init_%s:in.resources' % tp)
            out.addConnection('self:sub_out.nsteps_init', 'init_%s:in.nsteps' % tp)
            out.addConnection('self:ext_in.molecule_name', 'init_%s:in.molecule_name' % tp)
            out.addConnection('self:sub_out.n_lambdas_init', 'init_%s:in.n_lambdas' % tp)
            out.addConnection('self:ext_in.lambdas_%s' % tp, 'init_%s:in.lambdas' % tp)
            if tp == 'q':
                out.addConnection(None, 'init_%s:in.sc_alpha' % tp, FloatValue(0))
            else:
                out.addConnection('self:ext_in.sc_alpha', 'init_%s:in.sc_alpha' % tp)

        if simultaneousDecoupling:
            out.addConnection('self:sub_out.endpoint_array[0]', 'init_ljq:in.a')
            out.addConnection('self:sub_out.endpoint_array[1]', 'init_ljq:in.b')
        else:
            out.addConnection('self:sub_out.endpoint_array[0]', 'init_q:in.a')
            out.addConnection('self:sub_out.endpoint_array[1]', 'init_q:in.b')
            out.addConnection('self:sub_out.endpoint_array[1]', 'init_lj:in.a')
            out.addConnection('self:sub_out.endpoint_array[2]', 'init_lj:in.b')
        pers.set('init', init)

    for tp in types:
        nruns[tp] = pers.get('nruns_%s' % tp) or 0

        if nruns[tp] == 0:
            if addEquilibration(tp, 0, inp, out, pers, optimizeLambdas):
                nruns[tp] = 1
        # If optimizing lambdas run another equilibration with the new set
        # of lamba points before starting production runs.
        elif optimizeLambdas:
            if nruns[tp] == 1:
                if addEquilibration(tp, 1, inp, out, pers, optimizeLambdas):
                    nruns[tp] += 1
                else:
                    sys.stderr.write("Failed adding %s equilibration\n" % tp)
            # The code below was used for the free energy paper, but has been disabled now.
            ## Add two short iterations of optimizations. The optimization iterations
            ## are short to reduce the risk of throwing away much data.
            #elif nruns[tp] < 4:
                #if addIteration(tp, nruns[tp], (nruns[tp] - 2) * iterationStep/2, inp, out, pers, optimizeLambdas, isOptIter=True):
                    #nruns[tp] += 1
                #else:
                    #sys.stderr.write("Failed adding short %s optimization iteration\n" % tp)
            #elif nruns[tp] == 4:
                #if addIteration(tp, nruns[tp], iterationStep, inp, out, pers, optimizeLambdas):
                    #nruns[tp] += 1
                #else:
                    #sys.stderr.write("Failed adding %s iteration\n" % tp)
            elif nruns[tp] == 2:
                if addIteration(tp, nruns[tp], iterationStep, inp, out, pers, optimizeLambdas):
                    nruns[tp] += 1
                else:
                    sys.stderr.write("Failed adding %s iteration\n" % tp)
        elif nruns[tp] == 1:
            if addIteration(tp, 1, 0, inp, out, pers, optimizeLambdas):
                nruns[tp] += 1
            else:
                sys.stderr.write("Failed adding %s iteration\n" % tp)

    if simultaneousDecoupling:
        res['ljq'] = partialRes('dG_ljq_array', inp, out, pers)
        changed['ljq'] = res['ljq'].getUpdated()
        res['ljq'].updateOutput('partial_results', 0,
                             'Lennard-Jones and electrostatics decoupling', 'path_ljq')

        sys.stderr.write('ljq: %f +- %f.\n' % (res['ljq'].getAvg() or 0, res['ljq'].getErr() or -1))

        sys.stderr.write('Changed LJQ: %s\n' % changed['ljq'])

    else:
        res['q'] = partialRes('dG_q_array', inp, out, pers)
        changed['q'] = res['q'].getUpdated()
        res['q'].updateOutput('partial_results', 0,
                           'electrostatics decoupling', 'path_q')
        # lj next
        res['lj'] = partialRes('dG_lj_array', inp, out, pers)
        changed['lj'] = res['lj'].getUpdated()
        res['lj'].updateOutput('partial_results', 1,
                            'Lennard-Jones decoupling', 'path_lj')

        sys.stderr.write('q: %f +- %f. lj: %f +- %f\n' % (res['q'].getAvg() or 0, res['q'].getErr() or -1, res['lj'].getAvg() or 0, res['lj'].getErr() or -1))

        sys.stderr.write('Changed Q: %s, Changed LJ: %s\n' % (changed['q'], changed['lj']))

    precision = inp.getInput('precision')
    minIterations = inp.getInput('min_iterations')
    if optimizeLambdas and minIterations:
        minIterations += 1
    if precision is None:
        precision = 1

    changedPrecision = inp.getInputValue('precision').isUpdated()
    changedMinIterations = inp.getInputValue('min_iterations').isUpdated()

    sys.stderr.write('precision: %s. min_iterations: %s\n' % (precision, minIterations))
    sys.stderr.write('precision updated: %s. min_iterations updated: %s\n' %(changedPrecision, changedMinIterations))

    if not minIterations:
        tooFewIterations['ljq'] = False
        tooFewIterations['lj'] = False
        tooFewIterations['q'] = False

    if any(v == True for v in changed.itervalues()) or changedPrecision or changedMinIterations:
        last_equil['q'] = pers.get('last_equil_q') or 0
        last_equil['lj'] = pers.get('last_equil_lj') or 0
        last_equil['ljq'] = pers.get('last_equil_ljq') or 0
        totErr = 2*precision
        if simultaneousDecoupling:
            avg['ljq'] = res['ljq'].getAvg()
            err['ljq'] = res['ljq'].getErr()
            sys.stderr.write('avg_ljq = %s, err_ljq = %s\n' % (avg['ljq'], err['ljq']))
            if avg['ljq'] != None:
                # update the totals
                totVal = avg['ljq']
                totErr = err['ljq']
                out.setOut('delta_f.value', FloatValue(mult*totVal))
                out.setOut('delta_f.error', FloatValue(totErr))

            if minIterations:
                tooFewIterations['ljq'] = nruns['ljq'] - last_equil['ljq'] <= minIterations

        else:
            avg['q'] = res['q'].getAvg()
            avg['lj'] = res['lj'].getAvg()
            err['q'] = res['q'].getErr()
            err['lj'] = res['lj'].getErr()
            sys.stderr.write('avg_q = %s, avg_lj = %s, err_q = %s, err_lj = %s\n' % (avg['q'], avg['lj'], err['q'], err['lj']))
            if not (avg['q'] is None or avg['lj'] is None):
                # update the totals
                totVal = avg['q'] + avg['lj']
                totErr = math.sqrt(err['lj']*err['lj'] + err['q']*err['q'])
                out.setOut('delta_f.value', FloatValue(mult*totVal))
                out.setOut('delta_f.error', FloatValue(totErr))

            if minIterations:
                tooFewIterations['lj'] = nruns['lj'] - last_equil['lj'] <= minIterations
                tooFewIterations['q'] = nruns['q'] - last_equil['q'] <= minIterations

        # now add iterations if the error is more than the desired error
        if totErr > precision or any(v == True for v in tooFewIterations.itervalues()):
            if simultaneousDecoupling:
                sys.stderr.write('totErr (%s) > precision. nruns_ljq=%d\n' % (totErr, nruns['ljq']))
            else:
                sys.stderr.write('totErr (%s) > precision. nruns_q=%d nruns_lj=%d\n' % (totErr, nruns['q'], nruns['lj']))

            for tp in types:
                # we may need to start new runs. We use 0.4 * precision as a cutoff
                # for each of the halves because after that is reached it makes
                # more sense to sample the other side more thoroughly.
                if (changed[tp] or changedPrecision or changedMinIterations) and \
                    (tooFewIterations[tp] or err[tp] > 0.4 * precision):
                    # The code below was used for the free energy paper, but has been disabled now.
                    #if optimizeLambdas:
                        #initStep = iterationStep * max(0, (nruns[tp]-(last_equil[tp]+2)))
                    #else:
                        #initStep = iterationStep * max(0, (nruns[tp]-(last_equil[tp]+1)))

                    initStep = iterationStep * max(0, (nruns[tp]-(last_equil[tp]+1)))

                    if checkOptimization(tp, nruns[tp]-1, inp):
                        sys.stderr.write('Last run had lambdas reoptimized.\n')
                    sys.stderr.write('Adding another %s iteration. nruns_%s=%d\n' % (tp, tp, nruns[tp]))
                    if addIteration(tp, nruns[tp], initStep, inp, out, pers, optimizeLambdas):
                        nruns[tp] += 1
                    else:
                        sys.stderr.write("Failed adding %s iteration\n" % tp)
                        nHandled = pers.get('dG_%s_array_handled' % tp) or 1
                        nHandled -= 1
                        pers.set('dG_%s_array_handled' % tp, nHandled)
        else:
            if simultaneousDecoupling:
                sys.stderr.write('ljq: %d / %d\n' % (nruns['ljq'], res['ljq'].getN()))
            else:
                sys.stderr.write('q: %d / %d. lj: %d / %d\n' % (nruns['q'], res['q'].getN(), nruns['lj'], res['lj'].getN()))

            # Check that all results are incorporated
            for tp in types:
                if res[tp].getNdGArray() < nruns[tp]:
                    break
            else:
                sys.stderr.write('Desired precision reached.\n')
                # If not optimizing lambdas make a concatenated edr file of all runs.
                if not optimizeLambdas and inp.getInput('concatenate_edr_files'):
                    for tp in types:
                        if changed[tp]:
                            processEdrFiles(out, pers, tp, nruns[tp])

    for tp in types:
        pers.set('nruns_%s' % tp, nruns[tp])

    pers.write()
    sys.stderr.write('Writing persistence\n')


