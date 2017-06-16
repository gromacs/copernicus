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

class UmbrellaError(cpc.dataflow.ApplicationError):
    pass

def checkUpdated(inp, items):
    for item in items:
        if inp.getInputValue(item).isUpdated():
            return True
    return False

def genUmbrellaMdpParameters(argsList, name, n_groups, sysCenterAtom=0, springConstant=2000):

    argsList.append(RecordValue( { 'name' : StringValue('pull'),
                                   'value' : StringValue('umbrella') }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-nstfout'),
                                   'value' : StringValue('10') }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-nstxout'),
                                   'value' : StringValue('100000') }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-ngroups'),
                                   'value' : StringValue('%d' % (n_groups+1)) }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-ncoords'),
                                   'value' : StringValue('%d' % n_groups) }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-group1-name'),
                                   'value' : StringValue('NON_%s' % name) }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-group1-pbcatom'),
                                   'value' : StringValue('%s' % sysCenterAtom) }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-geometry'),
                                    'value' : StringValue('direction-periodic') }))

    argsList.append(RecordValue( { 'name' : StringValue('pull-start'),
                                    'value' : StringValue('yes') }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-dim'),
                                    'value' : StringValue('N N Y') }))
    for i in range(n_groups):
        argsList.append(RecordValue( { 'name' : StringValue('pull-group%d-name' % (i+2)),
                                       'value' : StringValue('%s_%d' % (name, i)) }))
    for i in range(1,n_groups+1):
        #argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-type' % (i)),
                                       #'value' : StringValue('umbrella') }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-groups' % (i)),
                                       'value' : StringValue('1 %d' % (i+1)) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-rate' % (i)),
                                       'value' : StringValue('0.0') }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-k' % (i)),
                                       'value' : StringValue('%s' % springConstant) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-vec' % (i)),
                                       'value' : StringValue('0 0 1') }))

def genMdrunInstances(inp, out):

    nSteps = inp.getInput('n_steps_umbrella')
    nIndexGroups = inp.getInput('n_index_groups')
    temperature = inp.getInput('temperature')

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

    #nUmbrellas = inp.getInput('n_umbrellas')
    confList = inp.getInput('confs')
    nConfs = len(confList)
    systemCenterAtom = inp.getInput('system_center_atom') or 0

    molName = inp.getInput('molecule_name') or 'LIG'
    springConstant = inp.getInput('spring_constant') or 2000

    settings_array=[]

    sys.stderr.write('Adding mdruns instance\n')
    out.addInstance('runs', 'gromacs::grompp_mdruns')
    out.addConnection('self:sub_out.settings_array', 'runs:in.settings')

    defineStrUmbrella = inp.getInput('define_umbrella')

    for i in range(nConfs):
        mdp=[]
        out.addConnection('self:ext_in.confs[%d]' % i, 'runs:in.conf[%d]' % i)

        mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                  'value' : StringValue('%d'%nSteps) }))
        if temperature:
            mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                      'value' : StringValue(tempStr) }))
        if defineStrUmbrella:
            mdp.append(RecordValue( { 'name' : StringValue('define'),
                                      'value' : StringValue(defineStrUmbrella) }))
        out.addConnection('self:ext_in.grompp.mdp', 'runs:in.mdp[%d]' % i)
        out.addConnection('self:ext_in.grompp.top', 'runs:in.top[%d]' % i)
        out.addConnection('self:ext_in.grompp.ndx', 'runs:in.ndx[%d]' % i)
        out.addConnection('self:ext_in.grompp.include', 'runs:in.include[%d]' % i)
        out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'runs:in.cmdline_options[%d]' % i)
        out.addConnection('self:ext_in.resources', 'runs:in.resources[%d]' % i)
        out.addConnection(None, 'runs:in.priority[%d]' % i, IntValue(-5))
        #out.addConnection('runs:out.conf[%d]' % i, 'self:ext_out.conf[%d]' % i)

        genUmbrellaMdpParameters(mdp, molName, nIndexGroups, systemCenterAtom, springConstant)

        settings_array.append(ArrayValue(mdp))

    out.setSubOut('settings_array', ArrayValue(settings_array))


def run(inp, out):
    sys.stderr.write('Starting u_umbrella_permeability.run\n')
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    sys.stderr.write('Init: %s\n' % init)

    if init is None:
        init=True

        genMdrunInstances(inp, out)

    pers.set('init', init)


    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out
