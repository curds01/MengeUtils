# Function to compute difference between density fields
import IncludeHeader

import figParams
import math
import numpy as np
import os
import scipy.stats as stats
import string
import struct

from Grid import Grid
from GridFileSequence import GridFileSequence
from primitives import Vector2

# Header Size of output file for .norm file composed of:
# frame number, stdDev, rootMeanSquare, max error, frameMaxError
HEADER_SIZE = 20
TOP_DIR = r'\Users\ksuvee\Documents'

# TODO: THis needs to be updated based on new functionality

def computeLPNorm( densityFileName0, densityFileName1, outPath, outputName, LPNormType ):
    """ Compute difference between two given density fields using
    one of three types of LP-Norm: L1, L2, L-Infinity.
    The output file will be binary file under name with a format: $outputName_$TypeLPNorm.norm

    @param densityFileName0   A complete path to .density file
    @param densityFileName1   A complete path to another density file to compare with the first one
    @param outPath            A path to a directory in which output file will locate
    @param outputName         A string of output name
    @param LPNormTypeL        A string to determine which type of LP-norm to calculate
                              [lone, ltwo, linf)] """
    try:
        f0 = open( densityFileName0, "rb" )
    except:
        print "Can't open density file: %s" % ( densityFileName0 )
        exit(1)
    try:
        f1 = open( densityFileName1, "rb" )
    except:
        print "Can't open density file: %s" % ( densityFileName1 )
        exit(1)
    else:
        w0, h0, count0, minVal0, maxVal0 = struct.unpack( 'iiiff',
                                            f0.read( GridFileSequence.HEADER_SIZE ) )
        w1, h1, count1, minVal1, maxVal1 = struct.unpack( 'iiiff',
                                            f1.read( GridFileSequence.HEADER_SIZE ) )
        gridSize1 = w1 * h1 * 4
        gridSize0 = w0 * h0 * 4
        print gridSize1
        if count0 != count1:
            print "Can't calculate the norm as the files contains different frame numbers"
            exit(1)
        if gridSize0 != gridSize1:
            print "Can't calculate the norm as the files has different gridsize"
            exit(1)

        g1 = Grid( Vector2(0, 0), Vector2(10, 10), (w1, h1) )
        g0 = Grid( Vector2(0, 0), Vector2(10, 10), (w0, h0) )

        # Both files contain same number of grid and each grid has same size
        gDist = 0
        distList = []
        for i in range( count0 ):
            data0 = f0.read( gridSize0 )
            data1 = f1.read( gridSize1 )
            g1.setFromBinary( data1 )
            g0.setFromBinary( data0 )
            gDiff = g1.cells - g0.cells
            if (LPNormType == 'LOne') or (LPNormType == 'lone'):
                # Manhattan Distance
                gDist = np.sum( np.fabs( gDiff ) )
                distList.append( gDist/( w0 * h0 ) )
            elif (LPNormType == 'LTwo' ) or (LPNormType == 'ltwo'):
                # Euclidean Distance
                gDist = np.sum( gDiff * gDiff )
                distList.append( gDist/( w0 * h0 ) )
            elif (LPNormType == 'linf') or (LPNormType == 'LInf'):
                # Chebyshev distance
                gDist = np.max( np.fabs( gDiff ) )
                distList.append( gDist )
        f0.close()
        f1.close()
        xValue = np.array( range( len( distList ) ), dtype='int32' )
        yValue = np.array( distList, dtype='float32' )  # LP norm values
        
        # Compute std deviation
        mean = yValue.sum()/float(yValue.size)
        temp1 = np.sum( yValue * yValue )/float(yValue.size)
        temp2 = mean * mean
        stdDev = math.sqrt( temp1 - temp2 )
        
        # Compute root mean square
        rms = math.sqrt( np.sum( yValue * yValue )/float( yValue.size) )
        maxError = np.max( yValue )
        maxPos = (np.where( yValue==maxError ))[0]
        if len(maxPos) > 1:
            maxPos = maxPos[0]

        # Output to the .norm file which contain number of frame in the header and LPnorm data per frame
        outputName = os.path.join( outPath, "%s-%s.norm" % ( outputName, LPNormType ) )
        outFile = open( outputName,'wb')
        np.save( outFile, yValue )
        outFile.close()

def main():
    densityFileName0 = TOP_DIR + r'\Density_project\Result_personal_far\uo-050-180-180_combined_MB\uniform\radius-100\uniform.density'
    densityFileName1 = TOP_DIR + r'\Density_project\Result_personal_far\uo-050-180-180_combined_MB\gaussian\radius-100\gaussian.density'
    outPath = TOP_DIR + r'\Density_project\dump'
    outputName = 'uniform_gaussian'
    inputPlot = 'uniform_gaussian_L2.norm'
    normFile = os.path.join( outPath, inputPlot)
    plotName = 'uniform_gaussian_L1norm'
    AxisName = 'L1Norm'
    computeLPNorm( densityFileName0, densityFileName1, outPath, outputName, 'lone' )

if __name__== '__main__':
    main()