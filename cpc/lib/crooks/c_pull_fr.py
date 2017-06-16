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

def checkUpdated(inp, items):
    for item in items:
        if inp.getInputValue(item).isUpdated():
            return True
    return False

def genPullMdpParameters(argsList, name, n_groups, systemZDim, sysCenterAtom=0, rate=0, constraint=False, pullK=1000, nstout=1, commRemovalGroups=['system'], pull3D=False):

    if constraint:
        argsList.append(RecordValue( { 'name' : StringValue('pull'),
                                       'value' : StringValue('constraint') }))
        if len(commRemovalGroups) == 1 and commRemovalGroups[0].lower() == 'system':
            argsList.append(RecordValue( { 'name' : StringValue('comm_grps'),
                                        'value' : StringValue('NON_%s' % name) }))
        refGroup = 0
#        refGroup = 1
    else:
        argsList.append(RecordValue( { 'name' : StringValue('pull'),
                                       'value' : StringValue('umbrella') }))
        refGroup = 1
    argsList.append(RecordValue( { 'name' : StringValue('pull-nstfout'),
                                   'value' : StringValue('%d' % nstout) }))
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

    #argsList.append(RecordValue( { 'name' : StringValue('pull-start'),
                                    #'value' : StringValue('no') }))
    argsList.append(RecordValue( { 'name' : StringValue('pull-start'),
                                    'value' : StringValue('yes') }))
    if pull3D:
        argsList.append(RecordValue( { 'name' : StringValue('pcoupl'),
                                    'value' : StringValue('no') }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-dim'),
                                    'value' : StringValue('Y Y Y') }))
    else:
        argsList.append(RecordValue( { 'name' : StringValue('pull-dim'),
                                    'value' : StringValue('N N Y') }))
    for i in range(n_groups):
        argsList.append(RecordValue( { 'name' : StringValue('pull-group%d-name' % (i+2)),
                                       'value' : StringValue('%s_%d' % (name, i)) }))
    for i in range(1,n_groups+1):
        #startPos = (i-1) * systemZDim/n_groups - systemZDim/2
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-groups' % (i)),
                                       'value' : StringValue('%d %d' % (refGroup, i+1)) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-rate' % (i)),
                                       'value' : StringValue('%e' % rate) }))
        if not constraint:
            argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-k' % (i)),
                                           'value' : StringValue('%f' % pullK) }))
        if pull3D:
            argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-vec' % (i)),
                                        'value' : StringValue('1 1 1') }))
        else:
            argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-vec' % (i)),
                                        'value' : StringValue('0 0 1') }))
        #argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-init' % (i)),
                                       #'value' : StringValue('%f' % startPos) }))

def genMdrunInstances(inp, out):

    nStepsEquil = inp.getInput('n_steps_equil')
    nStepsPull = inp.getInput('n_steps_pull')
    nIndexGroups = inp.getInput('n_index_groups')
    temperature = inp.getInput('temperature')

    if temperature:
        mdpFile = inp.getInput('grompp.mdp')
        
        nTempCouplGroups = None
        commRemovalGroups = []
        
        with open(mdpFile) as f:
            for line in f:
                line = line.strip()
                if len(line) <= 0 or line[0] == ';':
                    continue
                if 'tc_grps' in line:
                    line = line.split('=')[1].split()
                    nTempCouplGroups = len(line)
                if 'comm_grps' in line:
                    line = line.split('=')[1].split()
                    for g in line:
                        if g[0] == ';':
                            break
                        commRemovalGroups.append(g)
                    
            if nTempCouplGroups == None:
                nTempCouplGroups = 1
        tempStr = ''
        for i in range(nTempCouplGroups):
            tempStr += '%.2f ' % temperature

    confList = inp.getInput('confs')
    nConfs = len(confList)
    systemCenterAtom = inp.getInput('system_center_atom') or 0
    springConstant = inp.getInput('spring_constant')
    if springConstant == None:
        springConstant = 10000

    molName = inp.getInput('molecule_name') or 'LIG'
    systemZDim = inp.getInput('system_z_dim')

    rate = systemZDim / (nStepsPull / 500) # Assume 2 fs time step.
    # FIXME: Make an option whether to pull between starting points of pulled groups or through the whole system.
    #rate = systemZDim / (nIndexGroups * nStepsPull / 500) # Assume 2 fs time step. Pull between pulled groups (halfway if 2 pulled groups)
    #if nIndexGroups > 1:
        #rate *= 1.05 # When pulling only between starting points make sure that the groups reach the starting point of the next group.

    equil_settings_array=[]
    f_settings_array=[]
    r_settings_array=[]


    equilDefineStr = inp.getInput('define_equil')
    defineStr = inp.getInput('define')

    equil_mdp=[]
    f_mdp=[]
    r_mdp=[]
    equil_mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                    'value' : StringValue('%d'%nStepsEquil) }))
    f_mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                'value' : StringValue('%d'%nStepsPull) }))
    r_mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                'value' : StringValue('%d'%nStepsPull) }))
#    equil_mdp.append(RecordValue( { 'name' : StringValue('gen_vel'),
#                                    'value' : StringValue('yes') }))
    if temperature:
#        equil_mdp.append(RecordValue( { 'name' : StringValue('gen_temp'),
#                                        'value' : StringValue('%.2f' % temperature) }))
        equil_mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                        'value' : StringValue(tempStr) }))
        f_mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                    'value' : StringValue(tempStr) }))
        r_mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                    'value' : StringValue(tempStr) }))

    if equilDefineStr:
        equil_mdp.append(RecordValue( { 'name' : StringValue('define'),
                                        'value' : StringValue(equilDefineStr) }))
    if defineStr:
        if not equilDefineStr:
            equil_mdp.append(RecordValue( { 'name' : StringValue('define'),
                                            'value' : StringValue(defineStr) }))
        f_mdp.append(RecordValue( { 'name' : StringValue('define'),
                                    'value' : StringValue(defineStr) }))
        r_mdp.append(RecordValue( { 'name' : StringValue('define'),
                                    'value' : StringValue(defineStr) }))

    if springConstant == 0:
        constraint = True
    else:
        constraint = False

    sys.stderr.write('COMM Removal groups: %s\n' % commRemovalGroups)
    # Use a weaker spring constant for equilibration to allow slightly larger movements
    genPullMdpParameters(equil_mdp, molName, nIndexGroups, systemZDim, systemCenterAtom, 0, constraint=False, pullK=500, nstout=1000, commRemovalGroups=commRemovalGroups)
    genPullMdpParameters(f_mdp, molName, nIndexGroups, systemZDim, systemCenterAtom, rate, constraint=constraint, pullK=springConstant, nstout=1, commRemovalGroups=commRemovalGroups)
    genPullMdpParameters(r_mdp, molName, nIndexGroups, systemZDim, systemCenterAtom, -rate, constraint=constraint, pullK=springConstant, nstout=1, commRemovalGroups=commRemovalGroups)

    equil_settings_array.append(ArrayValue(equil_mdp))
    f_settings_array.append(ArrayValue(f_mdp))
    r_settings_array.append(ArrayValue(r_mdp))

    for instance in ['equil', 'run_f', 'run_r']:
        out.addInstance(instance, 'gromacs::grompp_mdruns')
        if instance == 'equil':
            pri = 1
        else:
            pri = 0
        for j in xrange(nConfs):
            out.addConnection('self:ext_in.grompp.mdp', '%s:in.mdp[%d]' % (instance, j))
            out.addConnection('self:ext_in.grompp.top', '%s:in.top[%d]' % (instance, j))
            out.addConnection('self:ext_in.grompp.ndx', '%s:in.ndx[%d]' % (instance, j))
            out.addConnection('self:ext_in.grompp.include', '%s:in.include[%d]' % (instance, j))
            out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', '%s:in.cmdline_options[%d]' % (instance, j))
            out.addConnection('self:ext_in.resources', '%s:in.resources[%d]' % (instance, j))
            out.addConnection(None, '%s:in.priority[%d]' % (instance, j), IntValue(pri))
    for j in xrange(nConfs):
        out.addConnection('self:ext_in.confs[%d]' % j, 'equil:in.conf[%d]' % j)
        out.addConnection('equil:out.conf[%d]' % j, 'run_f:in.conf[%d]'   % j)
        out.addConnection('equil:out.conf[%d]' % j, 'run_r:in.conf[%d]'   % j)
        out.addConnection('run_f:out.pullx[%d]'   % j, 'self:ext_out.pullx[%d]'% (j*2))
        out.addConnection('run_f:out.pullf[%d]'   % j, 'self:ext_out.pullf[%d]'% (j*2))
        out.addConnection('run_r:out.pullx[%d]'   % j, 'self:ext_out.pullx[%d]'% (j*2 + 1))
        out.addConnection('run_r:out.pullf[%d]'   % j, 'self:ext_out.pullf[%d]'% (j*2 + 1))

    out.addConnection('self:sub_out.equil_settings_array', 'equil:in.settings')
    out.addConnection('self:sub_out.f_settings_array', 'run_f:in.settings')
    out.addConnection('self:sub_out.r_settings_array', 'run_r:in.settings')

    out.setSubOut('equil_settings_array', ArrayValue(equil_settings_array))
    out.setSubOut('f_settings_array', ArrayValue(f_settings_array))
    out.setSubOut('r_settings_array', ArrayValue(r_settings_array))


def genCalcPermInstance(inp, out):

    confList = inp.getInput('confs')
    nConfs = len(confList)
    out.addInstance('calc', 'crooks::calc_permeability')
    out.addConnection('self:ext_in.temperature', 'calc:in.temperature')
    out.addConnection('self:ext_in.zero_point_delta_f', 'calc:in.zero_point_delta_f')
    out.addConnection('self:ext_in.system_z_dim', 'calc:in.react_coord_range')
    out.addConnection('self:ext_in.n_steps_pull', 'calc:in.n_steps_pull')
    out.addConnection('self:ext_in.sym', 'calc:in.sym')
    for j in xrange(nConfs):
        out.addConnection('run_f:out.pullx[%d]'   % j, 'calc:in.pullx[%d]'% (j*2))
        out.addConnection('run_f:out.pullf[%d]'   % j, 'calc:in.pullf[%d]'% (j*2))
        out.addConnection('run_r:out.pullx[%d]'   % j, 'calc:in.pullx[%d]'% (j*2 + 1))
        out.addConnection('run_r:out.pullf[%d]'   % j, 'calc:in.pullf[%d]'% (j*2 + 1))
    out.addConnection('calc:out.p', 'self:ext_out.p')
    out.addConnection('calc:out.log_p', 'self:ext_out.log_p')

def run(inp, out):
    sys.stderr.write('Starting c_pull_fr.run\n')
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    sys.stderr.write('Init: %s\n' % init)

    if init is None:
        init=True
        genMdrunInstances(inp, out)
        genCalcPermInstance(inp, out)

    pers.set('init', init)


    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out
