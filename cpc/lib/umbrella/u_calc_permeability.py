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
import numpy

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import cpc.dataflow
from cpc.dataflow import FloatValue
from cpc.dataflow import IntValue
from cpc.dataflow import BoolValue
from cpc.dataflow import FileValue
from cpc.dataflow import RecordValue

R = 8.3144598e-3

def findXvgOffset(filename, splitAtAmpersand=False):

    with open(filename) as f:
        if not splitAtAmpersand:
            for i,line in enumerate(f):
                line = line.strip()
                if line[0] != '#' and line[0] !='@':
                    return i+1
	else:
            offset = 0
            for i,line in enumerate(f):
                line = line.strip()
                if line[0] == '#' or line[0] == '@' or line[0] =='&':
                    offset = i+1
            return offset

def writeXvg(filename, title, xaxis, yaxis, data):

    header  = '@title "%s"\r\n' % title
    header += '@xaxis label "%s"\r\n' % xaxis
    header += '@yaxis label "%s"\r\n' % yaxis
    header += '@TYPE xy\r\n'
    savedXvg = False
    #try:
    from uncertainties import Variable, AffineScalarFunc
    # Expand ufloat into two columns
    sys.stderr.write('%s %s %s\n' % (data[0,0], data[0,1], type(data[0,1])))
    if type(data[0,1]) is Variable or isinstance(data[0,1], AffineScalarFunc):
        sys.stderr.write('Writing data with stderr.\n')
        nX = data.shape[0]
        tempData = numpy.empty([nX, 3])
        tempData[:,0] = data[:,0]
        for i in range(nX):
            tempData[i,1] = data[i, 1].nominal_value
            tempData[i,2] = data[i, 1].std_dev()
        header += '@TYPE xydy\r\n'

        numpy.savetxt(fname = filename, X = tempData)
        savedXvg = True
    #except Exception as e:
        #sys.stderr.write('%s\n' % e)

    if not savedXvg:
        numpy.savetxt(fname = filename, X = data)

    with open(filename, 'r+') as f:
        contents = f.read()
        f.seek(0, 0)
        f.write(header + contents)

def calcDiffusionProfile(iactFile, temperature):

    offset = findXvgOffset(iactFile, splitAtAmpersand=True) or 0
    sys.stderr.write('Offset of file %s is %d\n' % (iactFile, offset))
    data = numpy.loadtxt(iactFile, skiprows=offset, comments='@')
    data = data[data[:, 0].argsort()]
    diffusion = numpy.empty_like(data)
    diffusion[:,0] = data[:,0]
    diffusion[:, 1] = (R * temperature) / (data[:, 1] * 1e5)
#    diffusion[:, 1] = math.pow(R * temperature, 2) / (data[:, 1] * 1e-5 ) # 1e-12 * 1e14)

    return diffusion

def calcResistivity(pmfFile, diffusion, temperature, iMinX = None, iMaxX = None, zeroPointEnergy = None, zeroPointError = None):

    offset = findXvgOffset(pmfFile)
    try:
        from uncertainties import ufloat
        canCalculateError = True
    except ImportError:
        sys.stderr.write('Python uncertainties package not installed. Errors not calculated.')
        canCalculateError = False

    data = numpy.loadtxt(pmfFile, skiprows=offset, comments='@')
    allX = numpy.append(data[:,0], diffusion[:,0])
    if iMinX:
        allX = numpy.append(allX, iMinX)
    if iMaxX:
        allX = numpy.append(allX, iMaxX)
    allX = numpy.unique(allX)
    if iMinX == None:
        iMinX = allX[0]
    if iMaxX == None:
        iMaxX = allX[-1]
    nX = allX.shape[0]

    interpPmf = numpy.interp(allX, data[:,0], data[:,1])
    interpDiffusion = numpy.interp(allX, diffusion[:,0], diffusion[:,1])

    if canCalculateError and data.shape[1] > 2:
        interpPmfWithError = numpy.empty([nX], dtype = 'object')
        interpError = numpy.interp(allX, data[:,0], data[:,2])
        # FIXME: Can this be done without a for loop?
        for i in range(nX):
            interpPmfWithError[i] = ufloat((interpPmf[i], interpError[i]))

        interpPmf = interpPmfWithError

        resistProf = numpy.empty([nX, 2], dtype = 'object')
    else:
        resistProf = numpy.empty([nX, 2])

    if zeroPointEnergy != None:
        if canCalculateError and zeroPointError != None:
            zero = ufloat((zeroPointEnergy, zeroPointError))
        else:
            zero = zeroPointEnergy

        interpPmf += zeroPointEnergy

    resistProf[:,0] = allX

    resistProf[:,1] = interpPmf
    errorCalculated = False

    if canCalculateError and data.shape[1] > 2:
        from uncertainties import umath
        for i in range(nX):
            resistProf[i, 1] = umath.exp(interpPmf[i] / (R * temperature))
    else:
        resistProf[:,1] = numpy.exp(interpPmf / (R * temperature))

    resistProf[:,1] /= interpDiffusion

    resistProfRegion = resistProf[numpy.logical_and(resistProf[:,0] >= iMinX, resistProf[:,0] <= iMaxX)]
    # Convert from nm to cm
    resistProfRegion[:,0] *= 1e-7

    resistivity = numpy.trapz(resistProfRegion[:,1], resistProfRegion[:,0])

    return resistivity, resistProf

def setOutput(inp, out, diffusionProfile, resistivity, resistivityProfile):

    outputDir = inp.getOutputDir()
    outDiffProf = os.path.join(outputDir, 'diffusion_profile.xvg')
    outResProf = os.path.join(outputDir, 'resistivity_profile.xvg')
    writeXvg(outDiffProf, 'Diffusion Profile', 'z (nm)', 'Diffusion Rate (cm2/s)', diffusionProfile)
    writeXvg(outResProf, 'Resistance to permeation', 'z (nm)', 'Permeation Resistance (s/cm2)', resistivityProfile)

    p = 3600/resistivity

    try:
        from uncertainties import umath

        out.setOut('resistivity', FloatValue(resistivity.nominal_value))
        out.setOut('resistivity_error', FloatValue(resistivity.std_dev()))
        # Convert to cm/h for logP
        logP = umath.log10(p)
        out.setOut('p', FloatValue(p.nominal_value))
        out.setOut('p_error', FloatValue(p.std_dev()))
        out.setOut('log_p', FloatValue(logP.nominal_value))
        out.setOut('log_p_error', FloatValue(logP.std_dev()))
    except Exception:
        logP = math.log10(p)
        out.setOut('resistivity', FloatValue(resistivity))
        # Convert to cm/h for logP
        out.setOut('p', FloatValue(p))
        out.setOut('log_p', FloatValue(logP))

    out.setOut('diffusion_profile', FileValue(outDiffProf))
    out.setOut('resistivity_profile', FileValue(outResProf))

def run(inp, out):

    sys.stderr.write('Starting u_calc_permeability.run\n')
    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    sys.stderr.write('Init: %s\n' % init)

    iactFile = inp.getInput('iact')
    pmfFile = inp.getInput('pmf')

    zeroPointEnergyValue = inp.getInputValue('zero_point_delta_f.value')
    iMinXValue = inp.getInputValue('integral_min_x')
    iMaxXValue = inp.getInputValue('integral_max_x')
    temperatureValue = inp.getInputValue('temperature')

    zeroPointEnergy = inp.getInput('zero_point_delta_f.value')
    zeroPointError = inp.getInput('zero_point_delta_f.error')
    iMinX =  inp.getInput('integral_min_x')
    iMaxX = inp.getInput('integral_max_x')
    temperature = inp.getInput('temperature')
    if temperature is None:
        temperature = 298

    # There is currently no check if the iact file is updated. So only calculate the diffusion profile once.
    if init is None:

        diff = calcDiffusionProfile(iactFile, temperature)

    if init is None or zeroPointEnergyValue.isUpdated() or iMinXValue.isUpdated() or iMaxXValue.isUpdated() or temperatureValue.isUpdated():
        resist, resistProf = calcResistivity(pmfFile, diff, temperature, iMinX, iMaxX, zeroPointEnergy, zeroPointError)
        setOutput(inp, out, diff, resist, resistProf)

    init=True
    pers.set('init', init)

    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out

