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

def genInstances(inp, out):

    dup_x = inp.getInput('n_x_dups_in_sys') or 1
    dup_y = inp.getInput('n_y_dups_in_sys') or 1
    dup_z = inp.getInput('n_z_dups_in_sys') or 1
    n_x_sys = inp.getInput('n_x_systems') or 1
    n_y_sys = inp.getInput('n_y_systems') or 1
    n_z_sys = inp.getInput('n_z_systems') or 25

    hydrationFEOfMol = inp.getInput('hydration_mol_delta_f.value')
    zeroPointEnergy = inp.getInput('zero_point_delta_f.value')

    out.addInstance('grow', 'umbrella::grow_into_system')
    out.addInstance('umbrella', 'umbrella::umbrella_permeability')

    out.addConnection('self:ext_in.grompp', 'grow:in.grompp')
    out.addConnection('self:ext_in.define_grow', 'grow:in.define')
    out.addConnection('self:ext_in.system_conf', 'grow:in.system_conf')
    out.addConnection('self:ext_in.molecule_conf', 'grow:in.molecule_conf')
    out.addConnection('self:ext_in.molecule_name', 'grow:in.molecule_name')
    out.addConnection('self:ext_in.n_steps_grow', 'grow:in.n_steps')
    out.addConnection('self:ext_in.n_x_dups_in_sys', 'grow:in.n_x_dups_in_sys')
    out.addConnection('self:ext_in.n_y_dups_in_sys', 'grow:in.n_y_dups_in_sys')
    out.addConnection('self:ext_in.n_z_dups_in_sys', 'grow:in.n_z_dups_in_sys')
    out.addConnection('self:ext_in.random_xy', 'grow:in.random_xy')
    out.addConnection('self:ext_in.random_z', 'grow:in.random_z')
    out.addConnection('self:ext_in.n_x_systems', 'grow:in.n_x_systems')
    out.addConnection('self:ext_in.n_y_systems', 'grow:in.n_y_systems')
    out.addConnection('self:ext_in.n_z_systems', 'grow:in.n_z_systems')

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


    out.addConnection('self:ext_in.resources', 'grow:in.resources')

    out.addConnection('self:ext_in.grompp.mdp', 'umbrella:in.grompp.mdp')
    out.addConnection('self:ext_in.grompp.include', 'umbrella:in.grompp.include')
    out.addConnection('self:ext_in.grompp.settings', 'umbrella:in.grompp.settings')
    out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'umbrella:in.grompp.mdrun_cmdline_options')

    out.addConnection('self:ext_in.define_equil', 'umbrella:in.define_equil')
    out.addConnection('self:ext_in.define_umbrella', 'umbrella:in.define_umbrella')
    out.addConnection('grow:out.top', 'umbrella:in.grompp.top')
    out.addConnection('grow:out.ndx', 'umbrella:in.grompp.ndx')
    out.addConnection('grow:out.system_center_atom', 'umbrella:in.system_center_atom')

    out.addConnection('self:ext_in.molecule_name', 'umbrella:in.molecule_name')
    out.addConnection(None, 'umbrella:in.n_index_groups', IntValue(dup_x*dup_y*dup_z))
    out.addConnection(None, 'umbrella:in.n_umbrellas', IntValue(n_x_sys*n_y_sys*n_z_sys))

    for i in xrange(n_x_sys * n_y_sys * n_z_sys):
        out.addConnection('grow:out.conf[%d]' % i, 'umbrella:in.confs[%d]' % i)

    out.addConnection('self:ext_in.n_steps_equil', 'umbrella:in.n_steps_equil')
    out.addConnection('self:ext_in.n_steps_umbrella', 'umbrella:in.n_steps_umbrella')
    out.addConnection('self:ext_in.temperature', 'umbrella:in.temperature')
    out.addConnection('self:ext_in.dist_geom', 'umbrella:in.dist_geom')
    out.addConnection('self:ext_in.cyclic', 'umbrella:in.cyclic')
    out.addConnection('self:ext_in.sym', 'umbrella:in.sym')
    out.addConnection('self:ext_in.n_bootstraps', 'umbrella:in.n_bootstraps')
    out.addConnection('self:ext_in.ac_smooth', 'umbrella:in.ac_smooth')
    out.addConnection('self:ext_in.integral_min_x', 'umbrella:in.integral_min_x')
    out.addConnection('self:ext_in.integral_max_x', 'umbrella:in.integral_max_x')

    out.addConnection('self:ext_in.resources', 'umbrella:in.resources')
    out.addConnection('umbrella:out.pmf_profile', 'self:ext_out.pmf_profile')
    out.addConnection('umbrella:out.resistivity_profile', 'self:ext_out.resistivity_profile')
    out.addConnection('umbrella:out.resistivity', 'self:ext_out.resistivity')
    out.addConnection('umbrella:out.p', 'self:ext_out.p')
    out.addConnection('umbrella:out.p_error', 'self:ext_out.p_error')
    out.addConnection('umbrella:out.log_p', 'self:ext_out.log_p')
    out.addConnection('umbrella:out.log_p_error', 'self:ext_out.log_p_error')
    out.addConnection('umbrella:out.resistivity_error', 'self:ext_out.resistivity_error')


def run(inp, out):
    sys.stderr.write('Starting u_grow_umbrella_permeability.run\n')
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
