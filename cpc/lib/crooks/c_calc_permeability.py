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

from uncertainties import ufloat, umath, unumpy

R = 8.3144598e-3

class DirectionData():

    def __init__(self, nbins, estErr = False):

        self.nbins = nbins
        #self.work = numpy.zeros(nbins)
        #self.workError = numpy.zeros(nbins)
        #self.workCounter = numpy.zeros(nbins)
        self.workList = [[] for i in range(nbins)]
        if estErr:
            self.workMean = numpy.empty(nbins, dtype=object)
        else:
            self.workMean = numpy.empty(nbins)


# bootstrap function from http://people.duke.edu/~ccc14/pcfb/analysis.html
def bootstrap(data, num_samples, statistic, alpha):
    """Returns bootstrap estimate of 100.0*(1-alpha) CI for statistic."""
    n = len(data)
    idx = numpy.random.randint(0, n, (num_samples, n))
    samples = data[idx]
    stat = numpy.sort(statistic(samples, 1))
    return (stat[int((alpha/2.0)*num_samples)],
            stat[int((1-alpha/2.0)*num_samples)])

def retrieveHeader(fileName):

    with open(fileName) as f:
        header = []
        offset = 0

        for line in f:
            if line[0] == '@':
                offset += 1
                if 'yaxis' in line:
                    line='@    yaxis label "(kJ mol\S-1\N)"\n'
                header += line
            elif line[0] == '#':
                offset += 1
                header += line
            else:
                break

    return(''.join(header).split('\n'), offset)

def writeXvg(filename, title, xaxis, yaxis, data):

    header  = '@title "%s"\n' % title
    header += '@xaxis label "%s"\n' % xaxis
    header += '@yaxis label "%s"\n' % yaxis
    header += '@TYPE xydy\n'
    header += '@ s0 errorbar on\n'
    savedXvg = False

    numpy.savetxt(fname=filename, X=data, fmt='%12e')

    with open(filename, 'r+') as f:
        contents = f.read()
        f.seek(0, 0)
        f.write(header + contents)


def isForwardData(data):

    nRows, nCols = data.shape

    if data[0, 1] < data[nRows/50, 1] and data[nRows/50, 1] < data[nRows/10, 1]:
        return True
    if data[0, 1] > data[nRows/50, 1] and data[nRows/50, 1] > data[nRows/10, 1]:
        return False

    if data[nRows/50, 1] < data[nRows/10, 1] and data[nRows/10, 1] < data[nRows/2, 1]:
        return True
    if data[nRows/50, 1] > data[nRows/10, 1] and data[nRows/10, 1] > data[nRows/2, 1]:
        return False

    else:
        print "Cannot determine if the pull is in forward or reverse direction. Skipping file."

def calcResistivity(xData, pmfData, diffusionData, beta):

    iMinX = xData[0]
    iMaxX = xData[-1]
    nX = xData.shape[0]

    if isinstance(pmfData[0], float):
        resistProf = numpy.empty(nX)
    else:
        resistProf = numpy.empty(nX, dtype=object)

    errorCalculated = False

    if isinstance(pmfData[0], float):
        resistProf = numpy.exp(pmfData*beta)
    else:
        for i in range(nX):
            resistProf[i] = umath.exp(pmfData[i]*beta)

    resistProf /= diffusionData

    # Convert xData from nm to cm
    resistivity = numpy.trapz(resistProf, xData * 1e-7)

    return resistivity, resistProf

def fillBins(inp, nbins, coordRange, estErr = False):

    pullxFiles = inp.getInput('pullx')
    pullfFiles = inp.getInput('pullf')

    forwardTmpWork = numpy.zeros(nbins)
    reverseTmpWork = numpy.zeros(nbins)
    forwardTmpPathLen = numpy.zeros(nbins)
    reverseTmpPathLen = numpy.zeros(nbins)

    forward = DirectionData(nbins, estErr)
    reverse = DirectionData(nbins, estErr)

    binPathLen = (coordRange) / nbins

    minCoord = -coordRange/2
    maxCoord = coordRange/2
    binEdges = numpy.linspace(minCoord, maxCoord, nbins+1)

    bar_length = 20

    for i in range(len(pullxFiles)):
        xFile = inp.getInput('pullx[%d]' % i)
        fFile = inp.getInput('pullf[%d]' % i)

        (xHeader, xOffset) = retrieveHeader(xFile)
        (fHeader, fOffset) = retrieveHeader(fFile)

        xData = numpy.loadtxt(xFile, skiprows=xOffset, comments='@')
        fData = numpy.loadtxt(fFile, skiprows=fOffset, comments='@')

        isForward = isForwardData(xData)

        if isForward == None:
            continue
        if isForward:
            results = forward
            tmpWork = forwardTmpWork
            tmpPathLen = forwardTmpPathLen
            opposite = reverse
            oppositeTmpWork = reverseTmpWork
            oppositeTmpPathLen = reverseTmpPathLen
        else:
            results = reverse
            tmpWork = reverseTmpWork
            tmpPathLen = reverseTmpPathLen
            opposite = forward
            oppositeTmpWork = forwardTmpWork
            oppositeTmpPathLen = forwardTmpPathLen

        nRows, nCols = xData.shape

        for col in range(1, nCols):
            # Ensure that the coordinates are in the allowed range (treat PBCs)
            xData[:, col] += coordRange/2
            xData[:, col] = numpy.mod(xData[:, col], coordRange)
            xData[:, col] -= coordRange/2

            colCoordBins = numpy.digitize(xData[:,col], binEdges)

            for row in range(1, nRows):
                prevCoord = xData[row-1, col]
                prevBin = colCoordBins[row-1] - 1

                coord = xData[row,col]

                currBin = colCoordBins[row] - 1
                force = fData[row,col]

                if prevBin == currBin:
                    pathLen = coord - prevCoord
                    work = pathLen * force
                    pathLen = abs(pathLen)

                    if coord > prevCoord and isForward or coord < prevCoord and not isForward:
                        thisWork = tmpWork
                        thisPathLen = tmpPathLen
                        thisResults = results
                    # If not going in the "expected" direction put the results in the opposite direction.
                    else:
                        thisWork = oppositeTmpWork
                        thisPathLen = oppositeTmpPathLen
                        thisResults = opposite

                    thisWork[currBin] += work
                    thisPathLen[currBin] += pathLen

                    if thisPathLen[currBin] >= binPathLen:
                        normalizedTmpWork = thisWork[currBin] / (thisPathLen[currBin] / binPathLen)
                        thisResults.workList[currBin].append(normalizedTmpWork)
                        thisWork[currBin] = 0
                        thisPathLen[currBin] = 0

    return forward, reverse

def estimateErrors(forward, reverse):

    for direction in [forward, reverse]:
        for i in range(direction.nbins):
            #print direction.workList[i]
            m = numpy.mean(direction.workList[i])
            low, high = bootstrap(numpy.array(direction.workList[i]), 500, numpy.mean, 0.05)
            stdev = high - m
            val = ufloat((m, stdev))
            direction.workMean[i] = val


    # Make separate PMFs in forward and reverse directions.
    dU = (forward.workMean - reverse.workMean) / 2
    dUReverse = (reverse.workMean[::-1] - forward.workMean[::-1]) / 2
    pmfForward = numpy.cumsum(dU)
    pmfReverse = numpy.cumsum(dUReverse)[::-1]

    # Make a combined PMF weighted by how far the forward and reverse PMFs are from their origin (where the
    # error is expected to be lower).
    weights = numpy.linspace(0, 1, direction.nbins)
    pmf = numpy.average([pmfForward, pmfReverse], axis=0, weights=[weights[::-1], weights])

    error = max(unumpy.std_devs(pmf))

    return pmf, dU

def symmetriseData(data):

    #print data.shape
    nRows = data.shape[0]

    #print nRows, 'rows'

    for i in range(nRows/2):
        tmpVal = (data[i] + data[-(i+1)]) / 2
        data[i] = tmpVal
        data[-(i+1)] = tmpVal


def setOutput(inp, out, resistivity, resistivityProfile, pmf, diffusionProfile):

    outputDir = inp.getOutputDir()
    outResProf = os.path.join(outputDir, 'resistivity_profile.xvg')
    outPmf = os.path.join(outputDir, 'pmf.xvg')
    outDiffProf = os.path.join(outputDir, 'diffusion_profile.xvg')
    writeXvg(outResProf, 'Resistance to permeation', 'z (nm)', 'Permeation Resistance (s/cm2)', resistivityProfile)
    writeXvg(outPmf, 'PMF', 'z (nm)', 'kJ/mol', pmf)
    writeXvg(outDiffProf, 'Diffusion Profile', 'z (nm)', 'Diffusion Rate (cm2/s)', diffusionProfile)

    p = 3600/resistivity
    logP = umath.log10(p)
    sys.stderr.write('Resisitivity: %f +- %f, P: %f +- %f, logP: %f +- %f' % (resistivity.nominal_value, resistivity.std_dev(), p.nominal_value, p.std_dev(), logP.nominal_value, logP.std_dev()))
    out.setOut('resistivity.value', FloatValue(resistivity.nominal_value))
    out.setOut('resistivity.error', FloatValue(resistivity.std_dev()))
    out.setOut('p.value', FloatValue(p.nominal_value))
    out.setOut('p.error', FloatValue(p.std_dev()))
    out.setOut('log_p.value', FloatValue(logP.nominal_value))
    out.setOut('log_p.error', FloatValue(logP.std_dev()))

    out.setOut('resistivity_profile', FileValue(outResProf))
    out.setOut('pmf', FileValue(outPmf))
    out.setOut('diffusion_profile', FileValue(outDiffProf))

def run(inp, out):

    # Do this manually afterwards for now instead.

    sys.stderr.write('Skipping c_calc_permeability.run\n')

    return out

    sys.stderr.write('Starting c_calc_permeability.run\n')

    pers = cpc.dataflow.Persistence(os.path.join(inp.getPersistentDir(),
                                                 "persistent.dat"))
    init = pers.get('init')

    sys.stderr.write('Init: %s\n' % init)

    symValue = inp.getInputValue('sym')
    zeroPointEnergyValue = inp.getInputValue('zero_point_delta_f.value')
    nBinsValue = inp.getInputValue('n_bins')
    pullxFilesValue = inp.getInputValue('pullx')
    pullfFilesValue = inp.getInputValue('pullf')

    if init is None or zeroPointEnergyValue.isUpdated() or symValue.isUpdated() or pullxFilesValue.isUpdated():
        zeroPointEnergy = ufloat((inp.getInput('zero_point_delta_f.value'), inp.getInput('zero_point_delta_f.error')))
        temperature = inp.getInput('temperature')
        if temperature is None:
            temperature = 303.15
        coordRange = inp.getInput('react_coord_range')
        nSteps = inp.getInput('n_steps_pull')
        rate = coordRange / (nSteps / 500) # Assume 2 fs time step.
        symmetrise = inp.getInput('sym')
        if symmetrise == None:
            symmetrise = True
        nBins = inp.getInput('n_bins') or 200

        minCoord = -coordRange/2
        maxCoord = coordRange/2
        binPathLen = (coordRange) / nBins
        beta = 1/(R*temperature)

        forward, reverse = fillBins(inp, nBins, coordRange, estErr=True)

        outXVals = numpy.arange(minCoord+binPathLen/2, maxCoord, binPathLen)

        pmf, dU = estimateErrors(forward, reverse)
        dissipativeWork = (forward.workMean + reverse.workMean) / 2

        # Friction in ps/nm^2
        dissipativeWork = numpy.cumsum(abs(dissipativeWork))
        if isinstance(dissipativeWork[0], float):
            dissipativeWorkSlope = numpy.gradient(dissipativeWork, binPathLen)
        else:
            dissipativeWorkSlope = numpy.gradient(unumpy.nominal_values(dissipativeWork), binPathLen)

        frictionProfile = dissipativeWorkSlope * beta / rate

        if symmetrise:
            symmetriseData(pmf)
            symmetriseData(frictionProfile)

        # Convert friction to diffusion (in cm^2/s)
        diffusionProfile = 1/(frictionProfile*100)

        # Calibrate the first point (or a close minimum or maximum) to the given value.
        if zeroPointEnergy != None:
            calVal = pmf[0]
            diff = calVal - zeroPointEnergy
            pmf -= diff

        resistivity, resistivityProfile = calcResistivity(outXVals, pmf, diffusionProfile, beta)
        resistivityProfile = numpy.column_stack((outXVals, unumpy.nominal_values(resistivityProfile), unumpy.std_devs(resistivityProfile)))
        pmf = numpy.column_stack((outXVals, unumpy.nominal_values(pmf), unumpy.std_devs(pmf)))
        diffusionProfile = numpy.column_stack((outXVals, unumpy.nominal_values(diffusionProfile), unumpy.std_devs(diffusionProfile)))

        setOutput(inp, out, resistivity, resistivityProfile, pmf, diffusionProfile)

    init=True
    pers.set('init', init)

    pers.write()
    sys.stderr.write('Writing persistence\n')

    return out

