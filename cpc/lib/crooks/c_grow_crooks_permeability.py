#!/usr/bin/env python

# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2016, Sander Pronk, Iman Pouya, Magnus Lundborg, Erik Lindahl,
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
import numpy
import shutil
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
from cpc.dataflow import FileValue
from cpc.dataflow import RecordValue
from cpc.dataflow import ArrayValue

from c_pull_fr import genPullMdpParameters

def genInstances(inp, out):

    dup_x = inp.getInput('n_x_dups_in_sys') or 1
    dup_y = inp.getInput('n_y_dups_in_sys') or 1
    dup_z = inp.getInput('n_z_dups_in_sys') or 1
    nSets = inp.getInput('n_sets') or 14
    nReps = inp.getInput('n_experiment_reps') or 1

    hydrationFEOfMol = inp.getInput('hydration_mol_delta_f.value')
    zeroPointEnergy = inp.getInput('zero_point_delta_f.value')

    out.addInstance('grow', 'crooks::grow_into_system')

    out.addConnection('self:ext_in.grompp', 'grow:in.grompp')
    out.addConnection('self:ext_in.define_grow', 'grow:in.define')
    out.addConnection('self:ext_in.system_conf', 'grow:in.system_conf')
    out.addConnection('self:ext_in.molecule_conf', 'grow:in.molecule_conf')
    out.addConnection('self:ext_in.molecule_name', 'grow:in.molecule_name')
    out.addConnection('self:ext_in.n_steps_grow', 'grow:in.n_steps')
    out.addConnection('self:ext_in.n_x_dups_in_sys', 'grow:in.n_x_dups_in_sys')
    out.addConnection('self:ext_in.n_y_dups_in_sys', 'grow:in.n_y_dups_in_sys')
    out.addConnection('self:ext_in.n_z_dups_in_sys', 'grow:in.n_z_dups_in_sys')
    out.addConnection(None, 'grow:in.n_outputs', IntValue(nSets * nReps))

    if hydrationFEOfMol != None and zeroPointEnergy == None:
        sys.stderr.write('Hydration energy specified. Running bound energy calculations.\n')


        out.addConnection(None, 'grow:in.gen_bound_fe_output', BoolValue(True))
        
        out.addInstance('bound', 'fe::decouple')
        out.addConnection('grow:out.bound_conf', 'bound:in.conf')
        out.addConnection('grow:out.bound_ndx', 'bound:in.grompp.ndx')
        out.addConnection('grow:out.bound_top', 'bound:in.grompp.top')
        out.addConnection('grow:out.bound_conf', 'bound:in.grompp.rcoord')
        out.addConnection(None, 'bound:in.restraints_decoupling', BoolValue(False))
        
        out.addConnection('self:ext_in.molecule_name', 'bound:in.molecule_name')
        out.addConnection('self:ext_in.grompp.mdp', 'bound:in.grompp.mdp')
        out.addConnection('self:ext_in.grompp.include', 'bound:in.grompp.include')
        out.addConnection('self:sub_out.bound_settings_array', 'bound:in.grompp.settings')

        mdp = []
        molName = inp.getInput('molecule_name')
        mdp.append(RecordValue( { 'name' : StringValue('define'),
                                  'value' : StringValue('-DREST_LIG_FE') }))
        out.setSubOut('bound_settings_array', ArrayValue(mdp))

        out.addConnection(None, 'bound:in.relaxation_time', IntValue(75000))
        out.addConnection(None, 'bound:in.optimization_tolerance', FloatValue(0))
        out.addConnection(None, 'bound:in.precision', FloatValue(0.5))
        out.addConnection(None, 'bound:in.multiplier', FloatValue(-1))
        out.addConnection(None, 'bound:in.n_lambdas_init', IntValue(11))
        out.addConnection(None, 'bound:in.sc_alpha', FloatValue(0.5))

        out.addConnection('self:ext_in.resources', 'bound:in.resources')

        out.addConnection('bound:out.delta_f', 'self:sub_in.bound_delta_f')
    else:
        out.addConnection(None, 'grow:in.gen_bound_fe_output', BoolValue(False))


    out.addConnection('self:ext_in.resources', 'grow:in.resources')

    for rep in xrange(nReps):
        out.addInstance('fr_%d' % (rep), 'crooks::pull_fr')
        out.addConnection('self:ext_in.grompp.mdp', 'fr_%d:in.grompp.mdp' % (rep))
        out.addConnection('self:ext_in.grompp.include', 'fr_%d:in.grompp.include' % (rep))
        out.addConnection('self:ext_in.grompp.settings', 'fr_%d:in.grompp.settings' % (rep))
        out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'fr_%d:in.grompp.mdrun_cmdline_options' % (rep))
        out.addConnection('self:ext_in.define', 'fr_%d:in.define' % (rep))
        out.addConnection('self:ext_in.define_equil', 'fr_%d:in.define_equil' % (rep))

        out.addConnection('grow:out.top', 'fr_%d:in.grompp.top' % (rep))
        out.addConnection('grow:out.ndx', 'fr_%d:in.grompp.ndx' % (rep))
        out.addConnection('grow:out.system_center_atom', 'fr_%d:in.system_center_atom' % (rep))
        out.addConnection('grow:out.system_z_dim', 'fr_%d:in.system_z_dim' % (rep))

        out.addConnection('self:ext_in.molecule_name', 'fr_%d:in.molecule_name' % (rep))
        out.addConnection(None, 'fr_%d:in.n_index_groups' % (rep), IntValue(dup_x*dup_y*dup_z))

        for i in xrange(nSets):
            out.addConnection('grow:out.conf[%d]' % (nSets * rep + i), 'fr_%d:in.confs[%d]' % (rep, i))

        out.addConnection('self:ext_in.n_steps_equil', 'fr_%d:in.n_steps_equil' % (rep))
        out.addConnection('self:ext_in.n_steps_pull', 'fr_%d:in.n_steps_pull' % (rep))
        out.addConnection('self:ext_in.temperature', 'fr_%d:in.temperature' % (rep))
        out.addConnection('self:ext_in.spring_constant', 'fr_%d:in.spring_constant' % (rep))
        out.addConnection('self:ext_in.sym', 'fr_%d:in.sym' % (rep))

        out.addConnection('self:ext_in.resources', 'fr_%d:in.resources' % (rep))
        out.addConnection('fr_%d:out.p' % (rep), 'self:sub_in.p_list[%d]' % rep)

        if hydrationFEOfMol != None and zeroPointEnergy == None:
            out.addConnection('self:sub_out.zero_point_delta_f', 'fr_%d:in.zero_point_delta_f' % (rep))
        else:
            out.addConnection('self:ext_in.zero_point_delta_f', 'fr_%d:in.zero_point_delta_f' % (rep))

def calcAvgPermeability(inp, out):

    pList = inp.getSubnetInput('p_list')
    nInp = len(pList)

    pList = []

    for i in range(nInp):
        pListVal = inp.getSubnetInput('p_list[%d]' % i)
        if pListVal is not None:
            pVal = inp.getSubnetInput('p_list[%d].value' % i)
            pErr = inp.getSubnetInput('p_list[%d].error' % i)
            if pVal is not None:
                sys.stderr.write('p[%d]: %s +- %s\n' % (i, pVal, pErr))
                pList.append(pVal)
    if pList:
        p = numpy.mean(pList)
        pStd = numpy.std(pList)
        out.setOut('p.value', FloatValue(p))
        out.setOut('p.error', FloatValue(pStd))
        try:
            from uncertainties import ufloat, umath
            tmpP = ufloat((p, pStd))
            logP = umath.log10(tmpP)
            out.setOut('log_p.value', FloatValue(logP.nominal_value))
            out.setOut('log_p.error', FloatValue(logP.std_dev()))
        except Exception:
            logP = math.log10(p)
            out.setOut('log_p.value', FloatValue(logP))


def run(inp, out):
    sys.stderr.write('Starting c_grow_crooks_permeability.run\n')
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    if init is None:
        init=True
        genInstances(inp, out)


    boundDeltaFValue = inp.getSubnetInputValue('bound_delta_f')
    hydrationDeltaFValue = inp.getInputValue('hydration_mol_delta_f')
    if boundDeltaFValue.isUpdated() or hydrationDeltaFValue.isUpdated():
        boundDeltaF = inp.getSubnetInput('bound_delta_f.value')
        boundDeltaFError = inp.getSubnetInput('bound_delta_f.error')
        solvDeltaF = inp.getInput('hydration_mol_delta_f.value')
        solvDeltaFError = inp.getInput('hydration_mol_delta_f.error')
        if boundDeltaF != None and solvDeltaF != None:
            bindingDeltaF = boundDeltaF - solvDeltaF
            out.setSubOut('zero_point_delta_f.value', FloatValue(bindingDeltaF))
            if boundDeltaFError != None and solvDeltaFError != None:
                bindingDeltaFError = math.sqrt(boundDeltaFError * boundDeltaFError + solvDeltaFError * solvDeltaFError)
                out.setSubOut('zero_point_delta_f.error', FloatValue(bindingDeltaFError))

    calcAvgPermeability(inp, out)

    pers.set('init', init)


    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out
