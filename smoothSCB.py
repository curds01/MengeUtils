# This has functionality for smoothing the trajectories of an scb file
#   Uses a gaussian to smooth the positional trajectory
#   Has to do some clever work to smooth the orientation
#       Also correct orientation so that it starts in the direction of motion

import trajectory.scbData as scbData
import numpy as np
import pylab as plt

# special kernel.  Given the standard deviation (and assuming zero mean) it
# produces a discrete gaussian kernel a number of samples equal to:
#   max( ceil( 6 * sigma / cellSize ), kWidth )
def gaussian1D( sigma, cellSize, kWidth ):
    """Returns a discrete gaussian with standard deviation sigma and mean zero discretized
    to the given cellSize"""
    sixSigma = np.ceil( 6 * sigma / cellSize )
    kernelSize = max( sixSigma, kWidth )
    if ( kernelSize % 2 == 0 ):     # make sure the kernel size is odd numbered
        range = ( kernelSize / 2 ) * cellSize
    else:
        range = ( ( kernelSize / 2 ) - 0.5 ) * cellSize
    x = np.linspace( -range, range, kernelSize )
    k = np.exp( -(x*x)/(sigma*sigma) )
    k *= 1.0 / k.sum()
    return k

def filterPosition( frames, kernel, window ):
    """Given a filter, filters the position of all the agents"""
    print "Filter position"
    rawData = frames.fullData()
    smoothData = np.empty( rawData.shape, dtype=np.float32 )
    kFFT = np.abs( np.fft.rfft( kernel ) )
    kFFT.shape = (1,-1)
    # x position
    for i in range( 2 ):
        dataFFT = np.fft.rfft( rawData[:,i,:], axis=1 )
        smoothFFT = dataFFT * kFFT
        smoothData[ :, i, : ] = np.fft.irfft( smoothFFT, smoothData.shape[2], axis=1 )
    # orientation data
    smoothData[:, 2:, : ] = rawData[:, 2:, : ]
    
    if ( False ):
        SAMPLE = 10
        plt.figure()
        for i in range( rawData.shape[0] ):
            plt.plot( rawData[i, 0, window:-window:SAMPLE ], rawData[i, 1, window:-window:SAMPLE], 'b' )
        plt.title( 'raw trajectory' )
        plt.figure()
        for i in range( rawData.shape[0] ):
            plt.plot( smoothData[i, 0, window:-window:SAMPLE ], smoothData[i, 1, window:-window:SAMPLE],'r' )
        plt.title( 'Smoothed trajectory' )
        plt.show()
    return smoothData

def main():
    import sys
    import optparse

    parser = optparse.OptionParser()
    parser.add_option( "-s", "--scb", help="Name of the scb file to operate on (required)",
                       action="store", dest="scbName", default='' )
    parser.add_option( "-r", "--range", help="The range, in time steps, of the standard deviation - defaults to 1.0 if non specified",
                       action="store", type="float", default=1.0 )
    parser.add_option( "-o", "--outFile", help="Name of the scb file to save the filtered result - defaults to outFile.scb if none specified.",
                       action="store", dest="outName", default='outFile.scb' )

    options, args = parser.parse_args()

    if ( options.scbName == '' ):
        parser.print_help()
        sys.exit(1)

    print "Options:"
    print "\tInput:", options.scbName
    print "\tRange:", options.range
    print "\tOutput:", options.outName
    print
    
    try:
        frames = scbData.NPFrameSet( options.scbName )#, maxFrames=10 )
        frameCount = frames.totalFrames()
        print "\tFrameCount:", frameCount
        kernel = gaussian1D( options.range, 1.0, frameCount )
        window = options.range * 3
        smooth = filterPosition( frames, kernel, window )
        VERSION = 2
        scbData.writeNPSCB( options.outName, smooth[ :, :, window:-window ], frames, VERSION )
    except IOError, e:
        print "\nError trying to open %s:" % ( options.scbName ), e
        sys.exit(1)
            

if __name__ == '__main__':
    main()