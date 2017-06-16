#!/usr/bin/env python

# This file is part of Copernicus
# http://www.copernicus-computing.org/
#
# Copyright (C) 2011-2015, Sander Pronk, Iman Pouya, Magnus Lundborg, Erik Lindahl,
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

from u_umbrella_permeability import genUmbrellaMdpParameters

def genEquilInstance(inp, out):

    nStepsEquil = inp.getInput('n_steps_equil') or 0
    if nStepsEquil == 0:
        return

    dup_z = inp.getInput('n_z_dups_in_sys') or 1
    dup_lateral = inp.getInput('n_lateral_dups_in_sys') or 1
    nPulledMols = dup_z * dup_lateral
    growPullEven = inp.getInput('grow_pull_even') or False
    temperature = inp.getInput('temperature')
    springConstant = inp.getInput('spring_constant') or 2000
    molName = inp.getInput('molecule_name') or 'LIG'

    equil_settings_array=[]
    sys.stderr.write('Adding equilibration mdruns instance\n')
    out.addInstance('equil', 'gromacs::grompp_mdruns')
    out.addConnection('self:sub_out.equil_settings_array', 'equil:in.settings')
    defineStrEquil = inp.getInput('define_equil')

    # FIXME: Currently generating only one set of systems.
    i = 0

    if temperature:
        mdpFile = inp.getInput('grompp.mdp')
        with open(mdpFile) as f:
            for line in f:
                line = line.strip()
                if len(line) <= 0 or line[0] == ';':
                    continue
                if 'tc_grps' in line:
                    line = line.split('=')[1].split()
                    nTempCouplGroups = len(line)
                    break
            else:
                nTempCouplGroups = 1
        tempStr = ''
        for i in range(nTempCouplGroups):
            tempStr += '%.2f ' % temperature

    equil_mdp=[]
    equil_mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                    'value' : StringValue('%d'%nStepsEquil) }))
    if temperature:
        equil_mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                        'value' : StringValue(tempStr) }))

    if defineStrEquil:
        equil_mdp.append(RecordValue( { 'name' : StringValue('define'),
                                        'value' : StringValue(defineStrEquil) }))
    elif growPullEven and dup_lateral > 1:
        out.addConnection('grow:out.pull_even_conf[%d]' % i, 'equil:in.conf[%d]' % i)
    else:
        out.addConnection('grow:out.conf[%d]' % i, 'equil:in.conf[%d]' % i)
    out.addConnection('grow:out.ndx', 'equil:in.ndx[%d]' % i)
    out.addConnection('grow:out.top', 'equil:in.top[%d]' % i)
    out.addConnection('self:ext_in.grompp.mdp', 'equil:in.mdp[%d]' % i)
    out.addConnection('self:ext_in.grompp.include', 'equil:in.include[%d]' % i)
    out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'equil:in.cmdline_options[%d]' % i)
    out.addConnection('self:ext_in.resources', 'equil:in.resources[%d]' % i)
    out.addConnection(None, 'equil:in.priority[%d]' % i, IntValue(0))

    # Since we are keeping the molecules still the system center atom does not matter.
    genUmbrellaMdpParameters(equil_mdp, molName, nPulledMols, 0, springConstant)

    equil_settings_array.append(ArrayValue(equil_mdp))
    out.setSubOut('equil_settings_array', ArrayValue(equil_settings_array))


def genInstances(inp, out):

    dup_z = inp.getInput('n_z_dups_in_sys') or 1
    dup_lateral = inp.getInput('n_lateral_dups_in_sys') or 1
    nReps = inp.getInput('n_experiment_reps') or 1
    nPulledMols = dup_z * dup_lateral
    nUmbrellas = inp.getInput('n_umbrellas') or 25
    nStepsEquil = inp.getInput('n_steps_equil') or 0

    hydrationFEOfMol = inp.getInput('hydration_mol_delta_f.value')
    zeroPointEnergy = inp.getInput('zero_point_delta_f.value')
    pullBothDirections = inp.getInput('pull_both_directions') or False
    growPullEven = inp.getInput('grow_pull_even') or False

    out.addInstance('grow', 'umbrella::grow_into_system')
        #out.addConnection('self:sub_out.settings_array', 'halfway_pull_runs:in.settings')
    out.addInstance('pull', 'umbrella::pull_through_system')
    out.addInstance('umbrella', 'umbrella::umbrella_permeability')

    out.addConnection('self:ext_in.grompp', 'grow:in.grompp')
    out.addConnection('self:ext_in.define_grow', 'grow:in.define')
    out.addConnection('self:ext_in.system_conf', 'grow:in.system_conf')
    out.addConnection('self:ext_in.molecule_conf', 'grow:in.molecule_conf')
    out.addConnection('self:ext_in.molecule_name', 'grow:in.molecule_name')
    out.addConnection('self:ext_in.n_steps_grow', 'grow:in.n_steps')
    out.addConnection('self:ext_in.n_z_dups_in_sys', 'grow:in.n_z_dups_in_sys')
    out.addConnection('self:ext_in.n_lateral_dups_in_sys', 'grow:in.n_lateral_dups_in_sys')
    out.addConnection('self:ext_in.grow_pull_even', 'grow:in.pull_even')

    if hydrationFEOfMol != None and zeroPointEnergy == None:
        sys.stderr.write('Hydration energy specified. Running bound energy calculations.\n')


        out.addConnection(None, 'grow:in.gen_bound_fe_output', BoolValue(True))
        out.addInstance('bound', 'fe::decouple')
        out.addConnection('grow:out.bound_conf', 'bound:in.conf')
        out.addConnection('grow:out.bound_ndx', 'bound:in.grompp.ndx')
        out.addConnection('grow:out.bound_top', 'bound:in.grompp.top')
        out.addConnection('self:ext_in.molecule_name', 'bound:in.molecule_name')
        out.addConnection('self:ext_in.grompp.mdp', 'bound:in.grompp.mdp')
        out.addConnection('self:ext_in.grompp.include', 'bound:in.grompp.include')
        out.addConnection('self:sub_out.bound_settings_array', 'bound:in.grompp.settings')

        mdp = []
        molName = inp.getInput('molecule_name')
        # The system center atom does not matter (is set to 0 by default) for
        # calculating the bound fe. The umbrella is just there to keep it in place.
        genUmbrellaMdpParameters(mdp, molName, 1, 0)
        out.setSubOut('bound_settings_array', ArrayValue(mdp))

        out.addConnection(None, 'bound:in.relaxation_time', IntValue(50000))
        out.addConnection(None, 'bound:in.optimization_tolerance', FloatValue(0))
        out.addConnection(None, 'bound:in.precision', FloatValue(0.5))
        out.addConnection(None, 'bound:in.multiplier', FloatValue(-1))
        out.addConnection(None, 'bound:in.n_lambdas_init', IntValue(11))
        out.addConnection(None, 'bound:in.sc_alpha', FloatValue(0.5))

        out.addConnection('self:ext_in.resources', 'bound:in.resources')

        out.addConnection('bound:out.delta_f', 'self:sub_in.bound_delta_f')
        out.addConnection('self:sub_out.zero_point_delta_f', 'umbrella:in.zero_point_delta_f')
    else:
        out.addConnection(None, 'grow:in.gen_bound_fe_output', BoolValue(False))
        out.addConnection('self:ext_in.zero_point_delta_f', 'umbrella:in.zero_point_delta_f')

    genEquilInstance(inp, out)

    out.addConnection('self:ext_in.resources', 'grow:in.resources')

    out.addConnection('self:ext_in.grompp.mdp', 'pull:in.grompp.mdp')
    out.addConnection('self:ext_in.grompp.include', 'pull:in.grompp.include')
    out.addConnection('self:ext_in.grompp.settings', 'pull:in.grompp.settings')
    out.addConnection('self:ext_in.grompp.mdrun_cmdline_options',
                      'pull:in.grompp.mdrun_cmdline_options')

    out.addConnection('self:ext_in.define_pull', 'pull:in.define')

    out.addConnection('grow:out.top', 'pull:in.grompp.top')
    out.addConnection('grow:out.ndx', 'pull:in.grompp.ndx')
    out.addConnection('grow:out.system_center_atom', 'pull:in.system_center_atom')

    out.addConnection('self:ext_in.molecule_name', 'pull:in.molecule_name')
    out.addConnection(None, 'pull:in.n_index_groups', IntValue(nPulledMols))
    out.addConnection('self:ext_in.temperature', 'pull:in.temperature')
    out.addConnection(None, 'pull:in.n_umbrellas', IntValue(nUmbrellas))
    out.addConnection('self:ext_in.n_z_dups_in_sys', 'pull:in.n_z_dups_in_sys')
    out.addConnection('self:ext_in.n_lateral_dups_in_sys', 'pull:in.n_lateral_dups_in_sys')

    out.addConnection('self:ext_in.n_steps_pull', 'pull:in.n_steps')
    out.addConnection('self:ext_in.pull_both_directions', 'pull:in.pull_both_directions')
    out.addConnection('self:ext_in.pull_increasing_speed', 'pull:in.pull_increasing_speed')
    out.addConnection('self:ext_in.pull_between_z_dups', 'pull:in.pull_between_z_dups')
    out.addConnection('self:ext_in.resources', 'pull:in.resources')


    out.addConnection('self:ext_in.n_steps_umbrella', 'umbrella:in.n_steps_umbrella')
    out.addConnection('self:ext_in.temperature', 'umbrella:in.temperature')
    out.addConnection('self:ext_in.spring_constant', 'umbrella:in.spring_constant')

    out.addConnection('self:ext_in.grompp.mdp', 'umbrella:in.grompp.mdp')
    out.addConnection('self:ext_in.grompp.include', 'umbrella:in.grompp.include')
    out.addConnection('self:ext_in.grompp.settings', 'umbrella:in.grompp.settings')
    out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'umbrella:in.grompp.mdrun_cmdline_options')

    out.addConnection('self:ext_in.define_umbrella', 'umbrella:in.define_umbrella')
    out.addConnection('grow:out.top', 'umbrella:in.grompp.top')
    out.addConnection('grow:out.ndx', 'umbrella:in.grompp.ndx')
    out.addConnection('grow:out.system_center_atom', 'umbrella:in.system_center_atom')

    out.addConnection('self:ext_in.molecule_name', 'umbrella:in.molecule_name')
    out.addConnection(None, 'umbrella:in.n_index_groups', IntValue(nPulledMols))
    out.addConnection(None, 'umbrella:in.n_umbrellas', IntValue(nUmbrellas))

    # FIXME: Currently always assuming one system
    if nStepsEquil:
        out.addConnection('equil:out.conf[0]', 'pull:in.confs[0]')
    elif growPullEven and dup_lateral > 1:
        out.addConnection('grow:out.pull_even_conf[0]', 'pull:in.confs[0]')
    else:
        out.addConnection('grow:out.conf[0]', 'pull:in.confs[0]')

    for i in xrange(nUmbrellas):
        out.addConnection('pull:out.confs[%d]' % i, 'umbrella:in.confs[%d]' % i)
    if pullBothDirections:
        for i in xrange(nUmbrellas):
            out.addConnection('pull:out.confs[%d]' % (nUmbrellas+i), 'umbrella:in.confs[%d]' % (nUmbrellas+i))


    out.addConnection('self:ext_in.resources', 'umbrella:in.resources')

def run(inp, out):
    sys.stderr.write('Starting u_pull_umbrella_permeability.run\n')
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


    pers.set('init', init)


    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out
