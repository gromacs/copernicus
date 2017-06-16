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
import subprocess
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

from u_umbrella_permeability import UmbrellaError

def getSystemDimensions(groFile):

    dimensions = list()

    with open(groFile) as f:
        lines = f.readlines()

    parts = lines[-1].split()

    for i in range(3):
        dimensions.append(float(parts[i]))

    return dimensions


def genPullMdpParameters(argsList, name, pullRate, totNGroupsToPull, sysCenterAtom=0, pullK=2000, pullGroupOffset=0, nGroupsToPull=None):

    if nGroupsToPull == None:
        nGroupsToPull = totNGroupsToPull
    if pullGroupOffset == 0:
        argsList.append(RecordValue( { 'name' : StringValue('pull'),
                                    'value' : StringValue('umbrella') }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-nstfout'),
                                       'value' : StringValue('%d' % 1000) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-nstxout'),
                                       'value' : StringValue('%d' % 10000) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-ngroups'),
                                       'value' : StringValue('%d' % (totNGroupsToPull+1)) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-ncoords'),
                                       'value' : StringValue('%d' % totNGroupsToPull) }))
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
        argsList.append(RecordValue( { 'name' : StringValue('pull-dim'),
                                        'value' : StringValue('N N Y') }))
    for i in range(nGroupsToPull):
        argsList.append(RecordValue( { 'name' : StringValue('pull-group%d-name' % (i+2+pullGroupOffset)),
                                       'value' : StringValue('%s_%d' % (name, i+pullGroupOffset)) }))
    for i in range(1,nGroupsToPull+1):
        #startPos = (i-1) * systemZDim/n_groups - systemZDim/2
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-groups' % (i+pullGroupOffset)),
                                       'value' : StringValue('1 %d' % (i+1+pullGroupOffset)) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-rate' % (i+pullGroupOffset)),
                                       'value' : StringValue('%f' % pullRate) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-k' % (i+pullGroupOffset)),
                                    'value' : StringValue('%f' % pullK) }))
        argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-vec' % (i+pullGroupOffset)),
                                       'value' : StringValue('0 0 1') }))
        #argsList.append(RecordValue( { 'name' : StringValue('pull-coord%d-init' % (i)),
                                       #'value' : StringValue('%f' % startPos) }))

def genMdrunInstances(inp, out):

    nSteps = inp.getInput('n_steps')
    nIndexGroups = inp.getInput('n_index_groups')
    temperature = inp.getInput('temperature')
    nUmbrellas = inp.getInput('n_umbrellas') or 25
    nZDups = inp.getInput('n_z_dups_in_sys') or 1
    pullBothDirections = inp.getInput('pull_both_directions') or False
    pullDifferentSpeed = inp.getInput('pull_increasing_speed') or False
    pullBetweenZDups = inp.getInput('pull_between_z_dups') or False
    groFile = inp.getInput('confs[0]')
    if not groFile:
        return False

    dims = getSystemDimensions(groFile)

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

    equil_settings_array=[]
    settings_array=[]

    sys.stderr.write('Adding mdruns instance\n')
    out.addInstance('runs', 'gromacs::grompp_mdruns')
    out.addConnection('self:sub_out.settings_array', 'runs:in.settings')

    defineStr = inp.getInput('define')

    pullRate = float(dims[2]) / nSteps
    if pullBetweenZDups:
        pullRate /= nZDups

    # Pull rate is nm/ps.
    # TODO: Check the timestep to calculate the pull rate. Currently assuming 2 ns/step.
    pullRate *= 500

    for i in range(nConfs):
        equil_mdp=[]
        mdp=[]
        out.addConnection('self:ext_in.confs[%d]' % i, 'runs:in.conf[%d]' % i)

        mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                  'value' : StringValue('%d'%nSteps) }))
        mdp.append(RecordValue( { 'name' : StringValue('nstxout'),
                                  'value' : StringValue('%d' % (nSteps/nUmbrellas)) }))
        mdp.append(RecordValue( { 'name' : StringValue('nstxout-compressed'),
                                  'value' : StringValue('0') }))
        if temperature:
            mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                      'value' : StringValue(tempStr) }))
        if defineStr:
            mdp.append(RecordValue( { 'name' : StringValue('define'),
                                      'value' : StringValue(defineStr) }))
        out.addConnection('self:ext_in.grompp.mdp', 'runs:in.mdp[%d]' % i)
        out.addConnection('self:ext_in.grompp.top', 'runs:in.top[%d]' % i)
        out.addConnection('self:ext_in.grompp.ndx', 'runs:in.ndx[%d]' % i)
        out.addConnection('self:ext_in.grompp.include', 'runs:in.include[%d]' % i)
        out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'runs:in.cmdline_options[%d]' % i)
        out.addConnection('self:ext_in.resources', 'runs:in.resources[%d]' % i)
        out.addConnection(None, 'runs:in.priority[%d]' % i, IntValue(3))
        out.addConnection('runs:out.trr[%d]' % i, 'self:sub_in.trrs[%d]' % i)
        out.addConnection('runs:out.tpr[%d]' % i, 'self:sub_in.tprs[%d]' % i)


        if pullDifferentSpeed:
            # Pull at slightly different speeds to generate different positions and thereby better overlap between umbrellas.
            for j in xrange(nIndexGroups):
                genPullMdpParameters(mdp, molName, pullRate * (1 + 0.01 * j), nIndexGroups, systemCenterAtom, 10000, j, 1)
        else:
            genPullMdpParameters(mdp, molName, pullRate, nIndexGroups, systemCenterAtom, 10000)

        settings_array.append(ArrayValue(mdp))

    if pullBothDirections:
        for i in range(nConfs):
            equil_mdp=[]
            mdp=[]
            out.addConnection('self:ext_in.confs[%d]' % (i), 'runs:in.conf[%d]' % (i+nConfs))

            mdp.append(RecordValue( { 'name' : StringValue('nsteps'),
                                      'value' : StringValue('%d'%nSteps) }))
            mdp.append(RecordValue( { 'name' : StringValue('nstxout'),
                                      'value' : StringValue('%d' % (nSteps/nUmbrellas)) }))
            mdp.append(RecordValue( { 'name' : StringValue('nstxout-compressed'),
                                      'value' : StringValue('0') }))
            if temperature:
                mdp.append(RecordValue( { 'name' : StringValue('ref_t'),
                                          'value' : StringValue(tempStr) }))
            if defineStr:
                mdp.append(RecordValue( { 'name' : StringValue('define'),
                                          'value' : StringValue(defineStr) }))
            out.addConnection('self:ext_in.grompp.mdp', 'runs:in.mdp[%d]' % (i+nConfs))
            out.addConnection('self:ext_in.grompp.top', 'runs:in.top[%d]' % (i+nConfs))
            out.addConnection('self:ext_in.grompp.ndx', 'runs:in.ndx[%d]' % (i+nConfs))
            out.addConnection('self:ext_in.grompp.include', 'runs:in.include[%d]' % (i+nConfs))
            out.addConnection('self:ext_in.grompp.mdrun_cmdline_options', 'runs:in.cmdline_options[%d]' % (i+nConfs))
            out.addConnection('self:ext_in.resources', 'runs:in.resources[%d]' % (i+nConfs))
            out.addConnection(None, 'runs:in.priority[%d]' % (i+nConfs), IntValue(3))
            out.addConnection('runs:out.trr[%d]' % (i+nConfs), 'self:sub_in.trrs[%d]' % (i+nConfs))
            out.addConnection('runs:out.tpr[%d]' % (i+nConfs), 'self:sub_in.tprs[%d]' % (i+nConfs))

            if pullDifferentSpeed:
                # Pull at slightly different speeds to generate different positions.
                for j in xrange(nIndexGroups):
                    genPullMdpParameters(mdp, molName, -pullRate * (1 + 0.01 * j), nIndexGroups, systemCenterAtom, 10000, j, 1)
            else:
                genPullMdpParameters(mdp, molName, -pullRate, nIndexGroups, systemCenterAtom, 10000)

            settings_array.append(ArrayValue(mdp))


    out.setSubOut('settings_array', ArrayValue(settings_array))

    return True

def genConfOuts(inp, out):

    confList = inp.getInput('confs')
    nConfs = len(confList)
    nUmbrellas = inp.getInput('n_umbrellas') or 25
    pullBothDirections = inp.getInput('pull_both_directions') or False
    outDir = inp.getOutputDir()

    if pullBothDirections:
        nConfs *= 2

    for i in range(nConfs):
        trr = inp.getSubnetInputValue('trrs[%d]' % i)
        if trr and trr.isUpdated():
            sys.stderr.write('trr[%d] updated!\n' % i)

            trrName=inp.getSubnetInput('trrs[%d]' % i)
            tprName=inp.getSubnetInput('tprs[%d]' % i)
            confoutname=os.path.join(outDir, 'pull_%d_.gro' % i)
            cmd=['trjconv', '-s', tprName, '-f', trrName, '-o', confoutname,
                 '-sep' ]
            proc=subprocess.Popen(cmd,
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  cwd=outDir,
                                  close_fds=True)
            (stdout, stderr) = proc.communicate('System')
            if proc.returncode != 0:
                raise UmbrellaError("ERROR: trjconv returned %s, %s"%(stdout, stderr))
            # extract the frames.
            for j in xrange(nUmbrellas):
                confname=os.path.join(outDir, "pull_%d_%d.gro" % (i, j))
                if not os.path.exists(confname):
                    raise UmbrellaError("ERROR: trjconv failed to deliver: %s" % (confname))
                out.setOut('confs[%d]' % (i * nUmbrellas + j), FileValue(confname))

def run(inp, out):
    sys.stderr.write('Starting u_pull_through_system.run\n')
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    sys.stderr.write('Init: %s\n' % init)

    if not init:
        init = genMdrunInstances(inp, out)

    pers.set('init', init)

    genConfOuts(inp, out)

    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out
